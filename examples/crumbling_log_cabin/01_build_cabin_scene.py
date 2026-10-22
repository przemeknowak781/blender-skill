import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix, Euler

# ==============================================================================
# 0. SCENE RESET & COLLECTION HELPERS
# ==============================================================================
random.seed(42)

def reset_scene():
    scene = bpy.context.scene
    scene.name = "Scena_Chata_Z_Bali"
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)
    for cam in list(bpy.data.cameras):
        bpy.data.cameras.remove(cam)
    return scene

scene = reset_scene()

def make_collection(name, parent=None):
    col = bpy.data.collections.new(name)
    if parent is None:
        scene.collection.children.link(col)
    else:
        parent.children.link(col)
    return col

col_env = make_collection("01_Srodowisko_Teren_Woda")
col_cabin = make_collection("02_Chata_Z_Bali")
col_cart = make_collection("03_Woz_Drewniany")
col_veg = make_collection("04_Roslinnosc_Paprocie_Trawa")

def link_obj(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)

def set_smooth(obj, auto_angle_deg=35.0):
    if obj.type != 'MESH':
        return
    mesh = obj.data
    for poly in mesh.polygons:
        poly.use_smooth = True

def safe_set_input(node, names, value):
    if isinstance(names, int):
        node.inputs[names].default_value = value
        return node.inputs[names]
    if isinstance(names, str):
        names = [names]
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return node.inputs[n]
    return None

def get_input(node, names):
    if isinstance(names, str):
        names = [names]
    for n in names:
        if n in node.inputs:
            return node.inputs[n]
    return None

# ==============================================================================
# 1. PROCEDURAL PBR MATERIALS (Blender 5.2 Compatible)
# ==============================================================================
def create_materials():
    mats = {}

    # --- 1.1 Aged Log Wood (Stare Bale Drewniane z Mchem) ---
    mat_log = bpy.data.materials.new("Mat_Bale_Drewno")
    mat_log.use_nodes = True
    nt = mat_log.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    safe_set_input(mapping, "Scale", (1.5, 10.0, 10.0))
    links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    noise_grain = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise_grain, "Scale", 14.0)
    safe_set_input(noise_grain, "Detail", 12.0)
    safe_set_input(noise_grain, "Roughness", 0.72)
    links.new(mapping.outputs["Vector"], noise_grain.inputs["Vector"])

    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Y'
    safe_set_input(wave, "Scale", 4.5)
    safe_set_input(wave, "Distortion", 6.5)
    safe_set_input(wave, "Detail", 8.0)
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])

    ramp_wood = nodes.new("ShaderNodeValToRGB")
    ramp_wood.color_ramp.elements[0].position = 0.22
    ramp_wood.color_ramp.elements[0].color = (0.045, 0.028, 0.016, 1.0)
    ramp_wood.color_ramp.elements[1].position = 0.78
    ramp_wood.color_ramp.elements[1].color = (0.19, 0.125, 0.075, 1.0)
    e_mid = ramp_wood.color_ramp.elements.new(0.5)
    e_mid.color = (0.11, 0.075, 0.045, 1.0)
    links.new(noise_grain.outputs["Fac"], ramp_wood.inputs["Fac"])

    # Moss mask on top/north surfaces
    geom = nodes.new("ShaderNodeNewGeometry")
    sep_xyz = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geom.outputs["Normal"], sep_xyz.inputs["Vector"])

    noise_moss = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise_moss, "Scale", 6.0)
    safe_set_input(noise_moss, "Detail", 8.0)
    links.new(tex_coord.outputs["Object"], noise_moss.inputs["Vector"])

    math_moss = nodes.new("ShaderNodeMath")
    math_moss.operation = 'MULTIPLY'
    links.new(sep_xyz.outputs["Z"], math_moss.inputs[0])
    links.new(noise_moss.outputs["Fac"], math_moss.inputs[1])

    ramp_moss = nodes.new("ShaderNodeValToRGB")
    ramp_moss.color_ramp.elements[0].position = 0.38
    ramp_moss.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_moss.color_ramp.elements[1].position = 0.62
    ramp_moss.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    links.new(math_moss.outputs["Value"], ramp_moss.inputs["Fac"])

    mix_col = nodes.new("ShaderNodeMix")
    mix_col.data_type = 'RGBA'
    links.new(ramp_moss.outputs["Color"], get_input(mix_col, ["Factor", "Fac"]))
    links.new(ramp_wood.outputs["Color"], get_input(mix_col, ["A", "Color1"]))
    safe_set_input(mix_col, ["B", "Color2"], (0.06, 0.13, 0.035, 1.0))

    links.new(mix_col.outputs[0], bsdf.inputs["Base Color"])
    safe_set_input(bsdf, "Roughness", 0.84)

    bump = nodes.new("ShaderNodeBump")
    safe_set_input(bump, "Strength", 0.45)
    safe_set_input(bump, "Distance", 0.02)
    links.new(wave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mats["log"] = mat_log

    # --- 1.2 Weathered Shingles (Gont Drewniany z Mchem) ---
    mat_shingle = bpy.data.materials.new("Mat_Gont_Drewniany")
    mat_shingle.use_nodes = True
    nt = mat_shingle.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    obj_info = nodes.new("ShaderNodeObjectInfo")
    tex_coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise, "Scale", 18.0)
    safe_set_input(noise, "Detail", 10.0)
    links.new(tex_coord.outputs["Generated"], noise.inputs["Vector"])

    math_add = nodes.new("ShaderNodeMath")
    math_add.operation = 'PINGPONG'
    safe_set_input(math_add, 1, 1.0)
    math_mix = nodes.new("ShaderNodeMath")
    math_mix.operation = 'ADD'
    links.new(noise.outputs["Fac"], math_mix.inputs[0])
    links.new(obj_info.outputs["Random"], math_mix.inputs[1])
    links.new(math_mix.outputs["Value"], math_add.inputs[0])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[0].color = (0.05, 0.045, 0.04, 1.0) # charred/rotted dark grey-brown
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.22, 0.18, 0.14, 1.0) # silvered cedar shingle
    e1 = ramp.color_ramp.elements.new(0.48)
    e1.color = (0.12, 0.095, 0.07, 1.0)
    e2 = ramp.color_ramp.elements.new(0.72)
    e2.color = (0.07, 0.14, 0.04, 1.0) # mossy patch
    links.new(math_add.outputs["Value"], ramp.inputs["Fac"])

    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    safe_set_input(bsdf, "Roughness", 0.86)

    bump = nodes.new("ShaderNodeBump")
    safe_set_input(bump, "Strength", 0.35)
    safe_set_input(bump, "Distance", 0.015)
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mats["shingle"] = mat_shingle

    # --- 1.3 Hewn Window Beams & Door Timber (Belki Okienne i Drzwiowe) ---
    mat_beam = bpy.data.materials.new("Mat_Belki_Okienne")
    mat_beam.use_nodes = True
    nt = mat_beam.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise, "Scale", 12.0)
    safe_set_input(noise, "Detail", 10.0)
    links.new(tc.outputs["Object"], noise.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.2
    ramp.color_ramp.elements[0].color = (0.07, 0.042, 0.022, 1.0)
    ramp.color_ramp.elements[1].position = 0.8
    ramp.color_ramp.elements[1].color = (0.24, 0.15, 0.085, 1.0)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    safe_set_input(bsdf, "Roughness", 0.78)

    bump = nodes.new("ShaderNodeBump")
    safe_set_input(bump, "Strength", 0.3)
    safe_set_input(bump, "Distance", 0.01)
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mats["beam"] = mat_beam

    # --- 1.4 Weathered Painted Shutters (Okiennice z Łuszczącą się Farbą) ---
    mat_shutter = bpy.data.materials.new("Mat_Okiennice")
    mat_shutter.use_nodes = True
    nt = mat_shutter.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    noise_peel = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise_peel, "Scale", 7.5)
    safe_set_input(noise_peel, "Detail", 12.0)
    safe_set_input(noise_peel, "Roughness", 0.68)
    links.new(tc.outputs["Object"], noise_peel.inputs["Vector"])

    ramp_peel = nodes.new("ShaderNodeValToRGB")
    ramp_peel.color_ramp.elements[0].position = 0.43
    ramp_peel.color_ramp.elements[0].color = (0.11, 0.07, 0.04, 1.0) # bare aged wood
    ramp_peel.color_ramp.elements[1].position = 0.56
    ramp_peel.color_ramp.elements[1].color = (0.12, 0.28, 0.30, 1.0) # faded cottage teal-blue paint
    links.new(noise_peel.outputs["Fac"], ramp_peel.inputs["Fac"])
    links.new(ramp_peel.outputs["Color"], bsdf.inputs["Base Color"])
    safe_set_input(bsdf, "Roughness", 0.76)

    bump = nodes.new("ShaderNodeBump")
    safe_set_input(bump, "Strength", 0.35)
    safe_set_input(bump, "Distance", 0.01)
    links.new(noise_peel.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mats["shutter"] = mat_shutter

    # --- 1.5 Dirty Window Glass (Stare Brudne Szkło Okienne) ---
    mat_glass = bpy.data.materials.new("Mat_Szklo_Okienne")
    mat_glass.use_nodes = True
    nt = mat_glass.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    safe_set_input(bsdf, "Base Color", (0.18, 0.24, 0.22, 1.0))
    safe_set_input(bsdf, "Roughness", 0.18)
    safe_set_input(bsdf, "IOR", 1.52)
    safe_set_input(bsdf, ["Transmission Weight", "Transmission"], 0.65)
    mats["glass"] = mat_glass

    # --- 1.6 Rusted Iron (Zardzewiałe Okucia, Zawiasy i Obręcze Kół) ---
    mat_iron = bpy.data.materials.new("Mat_Zardzewiale_Zelazo")
    mat_iron.use_nodes = True
    nt = mat_iron.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    safe_set_input(bsdf, "Base Color", (0.14, 0.065, 0.035, 1.0))
    safe_set_input(bsdf, "Metallic", 0.78)
    safe_set_input(bsdf, "Roughness", 0.68)
    mats["iron"] = mat_iron

    # --- 1.7 Mossy Field Stones (Kamienie Fundamentu i Komina) ---
    mat_stone = bpy.data.materials.new("Mat_Kamien_Polny")
    mat_stone.use_nodes = True
    nt = mat_stone.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise, "Scale", 6.0)
    safe_set_input(noise, "Detail", 10.0)
    links.new(tc.outputs["Object"], noise.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.09, 0.095, 0.085, 1.0)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (0.28, 0.27, 0.25, 1.0)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    safe_set_input(bsdf, "Roughness", 0.82)

    bump = nodes.new("ShaderNodeBump")
    safe_set_input(bump, "Strength", 0.5)
    safe_set_input(bump, "Distance", 0.025)
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mats["stone"] = mat_stone

    # --- 1.8 Chinking / Moss Between Logs (Mszenie Między Balami) ---
    mat_chink = bpy.data.materials.new("Mat_Mszenie")
    mat_chink.use_nodes = True
    nt = mat_chink.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    safe_set_input(bsdf, "Base Color", (0.14, 0.16, 0.07, 1.0))
    safe_set_input(bsdf, "Roughness", 0.95)
    mats["chink"] = mat_chink

    # --- 1.9 Realistic Muddy & Mossy Ground (Realistyczna Ziemia i Błoto) ---
    mat_ground = bpy.data.materials.new("Mat_Ziemia_Bloto")
    mat_ground.use_nodes = True
    nt = mat_ground.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    geom = nodes.new("ShaderNodeNewGeometry")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geom.outputs["Position"], sep.inputs["Vector"])

    noise_soil = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise_soil, "Scale", 4.5)
    safe_set_input(noise_soil, "Detail", 14.0)
    safe_set_input(noise_soil, "Roughness", 0.75)
    links.new(tc.outputs["Object"], noise_soil.inputs["Vector"])

    noise_micro = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise_micro, "Scale", 32.0)
    safe_set_input(noise_micro, "Detail", 10.0)
    links.new(tc.outputs["Object"], noise_micro.inputs["Vector"])

    # Combine height Z and noise so low areas near puddles look dark & wet
    math_wet = nodes.new("ShaderNodeMath")
    math_wet.operation = 'ADD'
    links.new(sep.outputs["Z"], math_wet.inputs[0])

    math_scale_n = nodes.new("ShaderNodeMath")
    math_scale_n.operation = 'MULTIPLY'
    links.new(noise_soil.outputs["Fac"], math_scale_n.inputs[0])
    safe_set_input(math_scale_n, 1, 0.18)
    links.new(math_scale_n.outputs["Value"], math_wet.inputs[1])

    ramp_col = nodes.new("ShaderNodeValToRGB")
    ramp_col.color_ramp.elements[0].position = 0.02
    ramp_col.color_ramp.elements[0].color = (0.022, 0.016, 0.011, 1.0) # wet dark mud near puddles
    e_mud = ramp_col.color_ramp.elements.new(0.09)
    e_mud.color = (0.055, 0.038, 0.024, 1.0) # damp soil
    e_humus = ramp_col.color_ramp.elements.new(0.18)
    e_humus.color = (0.09, 0.068, 0.042, 1.0) # forest earth
    ramp_col.color_ramp.elements[1].position = 0.30
    ramp_col.color_ramp.elements[1].color = (0.055, 0.095, 0.032, 1.0) # mossy grassy earth
    links.new(math_wet.outputs["Value"], ramp_col.inputs["Fac"])
    links.new(ramp_col.outputs["Color"], bsdf.inputs["Base Color"])

    # Wetness roughness map: low Z = glossy wet mud (0.14), higher Z = matte soil (0.88)
    ramp_rough = nodes.new("ShaderNodeValToRGB")
    ramp_rough.color_ramp.elements[0].position = 0.03
    ramp_rough.color_ramp.elements[0].color = (0.14, 0.14, 0.14, 1.0)
    ramp_rough.color_ramp.elements[1].position = 0.14
    ramp_rough.color_ramp.elements[1].color = (0.88, 0.88, 0.88, 1.0)
    links.new(math_wet.outputs["Value"], ramp_rough.inputs["Fac"])
    links.new(ramp_rough.outputs["Color"], bsdf.inputs["Roughness"])

    bump = nodes.new("ShaderNodeBump")
    safe_set_input(bump, "Strength", 0.55)
    safe_set_input(bump, "Distance", 0.025)
    links.new(noise_micro.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mats["ground"] = mat_ground

    # --- 1.10 Reflective Puddle Water (Kałuże z Odbijającą Wodą) ---
    mat_water = bpy.data.materials.new("Mat_Woda_Kaluza")
    mat_water.use_nodes = True
    nt = mat_water.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Dark muddy water base with crisp mirror reflection on top
    safe_set_input(bsdf, "Base Color", (0.015, 0.018, 0.014, 1.0))
    safe_set_input(bsdf, "Roughness", 0.015)
    safe_set_input(bsdf, "IOR", 1.333)
    safe_set_input(bsdf, ["Specular IOR Level", "Specular"], 0.85)
    safe_set_input(bsdf, ["Coat Weight", "Clearcoat"], 1.0)
    safe_set_input(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.01)

    tc = nodes.new("ShaderNodeTexCoord")
    noise_ripple = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise_ripple, "Scale", 14.0)
    safe_set_input(noise_ripple, "Detail", 4.0)
    links.new(tc.outputs["Object"], noise_ripple.inputs["Vector"])

    bump = nodes.new("ShaderNodeBump")
    safe_set_input(bump, "Strength", 0.025)
    safe_set_input(bump, "Distance", 0.003)
    links.new(noise_ripple.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mats["water"] = mat_water

    # --- 1.11 Wooden Cart Material (Drewno Wozu) ---
    mat_cart = bpy.data.materials.new("Mat_Drewno_Wozu")
    mat_cart.use_nodes = True
    nt = mat_cart.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    safe_set_input(noise, "Scale", 16.0)
    safe_set_input(noise, "Detail", 10.0)
    links.new(tc.outputs["Object"], noise.inputs["Vector"])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.2
    ramp.color_ramp.elements[0].color = (0.08, 0.05, 0.028, 1.0)
    ramp.color_ramp.elements[1].position = 0.8
    ramp.color_ramp.elements[1].color = (0.23, 0.155, 0.095, 1.0)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    safe_set_input(bsdf, "Roughness", 0.78)

    bump = nodes.new("ShaderNodeBump")
    safe_set_input(bump, "Strength", 0.35)
    safe_set_input(bump, "Distance", 0.012)
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mats["cart"] = mat_cart

    # --- 1.12 Lush Ferns (Paprocie) ---
    mat_fern = bpy.data.materials.new("Mat_Paprocie")
    mat_fern.use_nodes = True
    nt = mat_fern.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    obj_info = nodes.new("ShaderNodeObjectInfo")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.045, 0.14, 0.025, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.13, 0.28, 0.045, 1.0)
    links.new(obj_info.outputs["Random"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    safe_set_input(bsdf, "Roughness", 0.48)
    safe_set_input(bsdf, ["Subsurface Weight", "Subsurface"], 0.25)
    mats["fern"] = mat_fern

    # --- 1.13 Realistic Grass & Weeds (Trawa i Roślinki) ---
    mat_grass = bpy.data.materials.new("Mat_Trawa")
    mat_grass.use_nodes = True
    nt = mat_grass.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    obj_info = nodes.new("ShaderNodeObjectInfo")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.05, 0.12, 0.022, 1.0)
    e_mid = ramp.color_ramp.elements.new(0.55)
    e_mid.color = (0.09, 0.21, 0.038, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.18, 0.24, 0.055, 1.0)
    links.new(obj_info.outputs["Random"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    safe_set_input(bsdf, "Roughness", 0.52)
    safe_set_input(bsdf, ["Subsurface Weight", "Subsurface"], 0.2)
    mats["grass"] = mat_grass

    return mats

mats = create_materials()

# ==============================================================================
# 2. TERRAIN HEIGHTFIELD & REFLECTIVE PUDDLES
# ==============================================================================
PUDDLES = [
    # (cx, cy, rx, ry, angle_rad, depth)
    (-0.25, -4.25, 1.85, 1.15, 0.18, 0.13),  # Main foreground puddle reflecting cabin & cart
    (-2.35, -5.20, 1.35, 0.85, -0.25, 0.11), # Left track puddle
    (2.15, -5.10, 1.25, 0.80, 0.30, 0.11),   # Right foreground puddle in front of cart
    (2.55, -2.25, 0.95, 0.70, -0.15, 0.10),  # Side puddle near cabin right corner
]

WATER_LEVEL = -0.022

def puddle_factor(x, y):
    """Returns 0.0 outside puddles, >0 inside puddle basins (1.0 at center)."""
    best = 0.0
    for cx, cy, rx, ry, ang, depth in PUDDLES:
        dx, dy = x - cx, y - cy
        ca, sa = math.cos(-ang), math.sin(-ang)
        lx = (dx * ca - dy * sa) / rx
        ly = (dx * sa + dy * ca) / ry
        r2 = lx * lx + ly * ly
        # Add organic shoreline distortion
        shore_warp = 0.18 * math.sin(x * 3.7 + y * 2.9) + 0.12 * math.cos(x * 6.1 - y * 5.3)
        r_eff = r2 + shore_warp * 0.25
        if r_eff < 1.0:
            val = (1.0 - r_eff) ** 1.6
            if val > best:
                best = val
    return best

def ground_height(x, y):
    # Base gentle rolling forest floor
    h = (
        0.06 * math.sin(x * 0.35 + 0.4) * math.cos(y * 0.32 - 0.2)
        + 0.035 * math.sin(x * 1.1 - y * 0.9)
        + 0.018 * math.cos(x * 2.7 + y * 2.3)
        + 0.008 * math.sin(x * 6.5 - y * 7.1)
    )
    # Keep cabin footprint relatively level around Z = 0.02
    if -3.0 < x < 3.0 and -1.8 < y < 3.4:
        blend = max(0.0, min(1.0, min(3.0 - abs(x), 2.6 - abs(y - 0.8)) / 1.2))
        h = h * (1.0 - 0.75 * blend) + 0.02 * (0.75 * blend)

    # Slight rise in background behind cabin
    if y > 3.5:
        h += 0.08 * min(4.0, y - 3.5)

    # Carve muddy wagon ruts curving from (-4.5, -6.8) through (1.5, -3.5) to (5.5, -2.0)
    track_y_center = -4.2 + 0.38 * x - 0.035 * (x ** 2)
    for offset in (-0.62, 0.62):
        dist_rut = abs(y - (track_y_center + offset))
        if dist_rut < 0.45 and -5.5 < x < 5.5:
            rut_t = (1.0 - dist_rut / 0.45) ** 2
            h -= 0.055 * rut_t

    # Carve puddle basins below WATER_LEVEL
    pf = puddle_factor(x, y)
    if pf > 0.0:
        h = h * (1.0 - pf) + (-0.095) * pf

    return h

def build_terrain_and_puddles():
    # High-resolution terrain mesh around foreground & cabin
    bm = bmesh.new()
    nx, ny = 140, 140
    size_x, size_y = 22.0, 22.0
    grid_verts = []
    for iy in range(ny + 1):
        row = []
        y = -10.5 + (iy / ny) * size_y
        for ix in range(nx + 1):
            x = -11.0 + (ix / nx) * size_x
            z = ground_height(x, y)
            v = bm.verts.new((x, y, z))
            row.append(v)
        grid_verts.append(row)

    for iy in range(ny):
        for ix in range(nx):
            bm.faces.new((
                grid_verts[iy][ix],
                grid_verts[iy][ix + 1],
                grid_verts[iy + 1][ix + 1],
                grid_verts[iy + 1][ix],
            ))

    mesh = bpy.data.meshes.new("Teren_Ziemia")
    bm.to_mesh(mesh)
    bm.free()
    obj_ground = bpy.data.objects.new("Teren_Ziemia", mesh)
    obj_ground.data.materials.append(mats["ground"])
    set_smooth(obj_ground)
    link_obj(obj_ground, col_env)

    # Reflective water sheet covering puddle basins
    bm_w = bmesh.new()
    wnx, wny = 90, 70
    w_verts = []
    for iy in range(wny + 1):
        row = []
        y = -7.2 + (iy / wny) * 6.5
        for ix in range(wnx + 1):
            x = -4.8 + (ix / wnx) * 9.6
            ripple = 0.0012 * math.sin(x * 14.0 + y * 11.0) * math.cos(x * 9.0 - y * 15.0)
            v = bm_w.verts.new((x, y, WATER_LEVEL + ripple))
            row.append(v)
        w_verts.append(row)

    for iy in range(wny):
        for ix in range(wnx):
            bm_w.faces.new((
                w_verts[iy][ix],
                w_verts[iy][ix + 1],
                w_verts[iy + 1][ix + 1],
                w_verts[iy + 1][ix],
            ))

    mesh_w = bpy.data.meshes.new("Woda_Kaluze")
    bm_w.to_mesh(mesh_w)
    bm_w.free()
    obj_water = bpy.data.objects.new("Woda_Kaluze", mesh_w)
    obj_water.data.materials.append(mats["water"])
    set_smooth(obj_water)
    link_obj(obj_water, col_env)

build_terrain_and_puddles()

# ==============================================================================
# 3. CRUMBLING LOG CABIN WITH DETAILED WINDOWS, SHUTTERS & SHINGLE ROOF
# ==============================================================================
CABIN_CENTER = Vector((0.0, 0.70, 0.0))

def cabin_sag_offset(x, y, z):
    """
    Applies realistic structural settling and decay to the cabin:
    - The right side (x > 0.3) sags downward and leans slightly outward (+X, -Y).
    - The roof ridge sags in the middle-right section (around x = 1.1).
    """
    right_factor = max(0.0, (x + 0.4) / 3.0)
    front_factor = max(0.0, (1.5 - y) / 3.0)
    dz = -0.14 * (right_factor ** 1.7) * (0.3 + 0.7 * front_factor)
    # Extra roof sag near the collapsed section (x ~ 1.15)
    if z > 2.1:
        roof_collapse = math.exp(-((x - 1.15) ** 2) / 0.95) * ((z - 2.1) / 1.7)
        dz -= 0.22 * roof_collapse
    dx = 0.07 * (right_factor ** 1.5) * max(0.0, (z - 0.3) / 2.5)
    dy = -0.05 * (right_factor ** 1.4) * max(0.0, (z - 0.3) / 2.5)
    return Vector((dx, dy, dz))

def make_deformed_stone(name, loc, scale, rot_euler=(0.0, 0.0, 0.0), seed=0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    rng = random.Random(seed)
    for v in bm.verts:
        n = v.co.normalized()
        disp = 1.0 + 0.22 * math.sin(n.x * 4.3 + seed) * math.cos(n.y * 3.9 - seed) + rng.uniform(-0.08, 0.08)
        v.co.x *= scale[0] * disp
        v.co.y *= scale[1] * disp
        v.co.z *= scale[2] * disp
        if v.co.z < -scale[2] * 0.45:
            v.co.z = -scale[2] * 0.48
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = rot_euler
    obj.data.materials.append(mats["stone"])
    set_smooth(obj)
    return obj

def create_log_segment_bm(bm, p1, p2, radius=0.125, segs_len=14, segs_circ=14, notch_ends=True, seed=0):
    """Adds a realistic round/hewn log between p1 and p2 into bmesh `bm`, applying cabin_sag_offset."""
    rng = random.Random(seed)
    vec = p2 - p1
    length = vec.length
    if length < 0.08:
        return
    tangent = vec.normalized()
    up = Vector((0.0, 0.0, 1.0))
    if abs(tangent.dot(up)) > 0.95:
        up = Vector((1.0, 0.0, 0.0))
    side = tangent.cross(up).normalized()
    up_ortho = side.cross(tangent).normalized()

    bow_side = rng.uniform(-0.018, 0.018)
    bow_up = rng.uniform(-0.015, 0.012)
    rings = []

    for i in range(segs_len + 1):
        t = i / segs_len
        base_pt = p1.lerp(p2, t)
        arch = math.sin(t * math.pi)
        base_pt = base_pt + side * (bow_side * arch) + up_ortho * (bow_up * arch)

        # Taper/bevel at very ends and saddle notches near corners
        dist_end = min(t * length, (1.0 - t) * length)
        r_scale_side = 1.0
        r_scale_up = 1.0
        if dist_end < 0.04:
            bevel = 0.78 + 0.22 * (dist_end / 0.04)
            r_scale_side *= bevel
            r_scale_up *= bevel
        elif notch_ends and 0.24 < dist_end < 0.46:
            notch_t = math.sin(((dist_end - 0.24) / 0.22) * math.pi)
            r_scale_up *= (1.0 - 0.28 * notch_t)

        sag = cabin_sag_offset(base_pt.x, base_pt.y, base_pt.z)
        center = base_pt + sag

        ring = []
        for j in range(segs_circ):
            ang = (j / segs_circ) * 2.0 * math.pi
            bark = 1.0 + 0.045 * math.sin(ang * 5.0 + seed + t * 4.0) + 0.025 * math.cos(ang * 3.0 - t * 6.0)
            rx = radius * r_scale_side * bark
            rz = radius * r_scale_up * bark * 1.04
            offset = side * (math.cos(ang) * rx) + up_ortho * (math.sin(ang) * rz)
            v = bm.verts.new(center + offset)
            ring.append(v)
        rings.append(ring)

    for i in range(segs_len):
        r0 = rings[i]
        r1 = rings[i + 1]
        for j in range(segs_circ):
            jn = (j + 1) % segs_circ
            bm.faces.new((r0[j], r1[j], r1[jn], r0[jn]))

    # End caps
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])

def add_box_to_bm(bm, center, size_xyz, rot_euler=(0.0, 0.0, 0.0), apply_sag=True, bevel_edges=True):
    """Creates a 3D timber beam/plank box inside `bm` with optional cabin sag."""
    sx, sy, sz = size_xyz[0] * 0.5, size_xyz[1] * 0.5, size_xyz[2] * 0.5
    rot_mat = Euler(rot_euler, 'XYZ').to_matrix().to_4x4()
    nx, ny, nz = 4, 2, 2
    verts_grid = []
    for ix in range(nx + 1):
        tx = -sx + (ix / nx) * (2.0 * sx)
        plane = []
        for iy in range(ny + 1):
            ty = -sy + (iy / ny) * (2.0 * sy)
            col = []
            for iz in range(nz + 1):
                tz = -sz + (iz / nz) * (2.0 * sz)
                # Slight chamfer on outer edges
                local = Vector((tx, ty, tz))
                world = center + (rot_mat @ local)
                if apply_sag:
                    world = world + cabin_sag_offset(world.x, world.y, world.z)
                col.append(bm.verts.new(world))
            plane.append(col)
        verts_grid.append(plane)

    # 6 outer faces of the subdivided box
    # -Z and +Z
    for ix in range(nx):
        for iy in range(ny):
            bm.faces.new((verts_grid[ix][iy][0], verts_grid[ix][iy+1][0], verts_grid[ix+1][iy+1][0], verts_grid[ix+1][iy][0]))
            bm.faces.new((verts_grid[ix][iy][nz], verts_grid[ix+1][iy][nz], verts_grid[ix+1][iy+1][nz], verts_grid[ix][iy+1][nz]))
    # -Y and +Y
    for ix in range(nx):
        for iz in range(nz):
            bm.faces.new((verts_grid[ix][0][iz], verts_grid[ix+1][0][iz], verts_grid[ix+1][0][iz+1], verts_grid[ix][0][iz+1]))
            bm.faces.new((verts_grid[ix][ny][iz], verts_grid[ix][ny][iz+1], verts_grid[ix+1][ny][iz+1], verts_grid[ix+1][ny][iz]))
    # -X and +X
    for iy in range(ny):
        for iz in range(nz):
            bm.faces.new((verts_grid[0][iy][iz], verts_grid[0][iy][iz+1], verts_grid[0][iy+1][iz+1], verts_grid[0][iy+1][iz]))
            bm.faces.new((verts_grid[nx][iy][iz], verts_grid[nx][iy+1][iz], verts_grid[nx][iy+1][iz+1], verts_grid[nx][iy][iz+1]))

def build_window_and_shutters(
    name_prefix,
    wall_center,
    wall_normal_angle_z,
    win_w=0.92,
    win_h=0.98,
    shutter_left_angle=-138.0,
    shutter_right_angle=-38.0,
    left_shutter_droop_deg=14.0,
    right_shutter_droop_deg=-5.0,
    broken_glass=False,
):
    """
    Builds a highly detailed window with heavy hewn timber casing beams (parapet, węgarki, nadproże),
    inner window sash with muntins (szprosy), glass panes, wrought-iron hinges, and plank shutters (okiennice).
    """
    bm_beams = bmesh.new()
    bm_shutter = bmesh.new()
    bm_iron = bmesh.new()
    bm_glass = bmesh.new()

    base_rot = Euler((0.0, 0.0, wall_normal_angle_z), 'XYZ').to_matrix().to_4x4()

    def to_world(local_pos):
        p = wall_center + (base_rot @ local_pos)
        return p + cabin_sag_offset(p.x, p.y, p.z)

    def add_local_box(target_bm, local_pos, size_xyz, local_euler=(0.0, 0.0, 0.0)):
        sx, sy, sz = size_xyz[0] * 0.5, size_xyz[1] * 0.5, size_xyz[2] * 0.5
        rmat = Euler(local_euler, 'XYZ').to_matrix().to_4x4()
        corners = [
            Vector((-sx, -sy, -sz)), Vector((sx, -sy, -sz)),
            Vector((sx, sy, -sz)), Vector((-sx, sy, -sz)),
            Vector((-sx, -sy, sz)), Vector((sx, -sy, sz)),
            Vector((sx, sy, sz)), Vector((-sx, sy, sz)),
        ]
        v_list = [target_bm.verts.new(to_world(local_pos + (rmat @ c))) for c in corners]
        faces = [
            (0, 3, 2, 1), (4, 5, 6, 7),
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 4, 7, 3), (1, 2, 6, 5),
        ]
        for f in faces:
            target_bm.faces.new([v_list[idx] for idx in f])

    beam_thick = 0.13
    beam_depth = 0.30

    # 1. Heavy Sill Beam (Parapet z grubej ciosanej belki, wystający przed lico ściany)
    add_local_box(bm_beams, Vector((0.0, -0.04, -win_h * 0.5 - beam_thick * 0.45)), (win_w + 0.34, beam_depth + 0.08, beam_thick))
    # Decorative under-sill trim beam
    add_local_box(bm_beams, Vector((0.0, -0.08, -win_h * 0.5 - beam_thick * 0.95)), (win_w + 0.22, 0.08, 0.055))

    # 2. Heavy Left & Right Jamb Beams (Węgarki / Pionowe belki ościeżnicy)
    add_local_box(bm_beams, Vector((-win_w * 0.5 - beam_thick * 0.42, 0.0, 0.0)), (beam_thick, beam_depth, win_h + 0.04))
    add_local_box(bm_beams, Vector((+win_w * 0.5 + beam_thick * 0.42, 0.0, 0.0)), (beam_thick, beam_depth, win_h + 0.04))

    # 3. Carved Header Lintel Beam (Nadproże z grubej belki z okapnikiem)
    add_local_box(bm_beams, Vector((0.0, -0.03, +win_h * 0.5 + beam_thick * 0.48)), (win_w + 0.38, beam_depth + 0.06, beam_thick * 1.1))
    add_local_box(bm_beams, Vector((0.0, -0.09, +win_h * 0.5 + beam_thick * 1.05)), (win_w + 0.44, 0.12, 0.045), local_euler=(0.22, 0.0, 0.0))

    # 4. Inner Window Sash & Muntins (Rama okienna i szprosy)
    sash_w = win_w - 0.04
    sash_h = win_h - 0.04
    frame_t = 0.045
    add_local_box(bm_beams, Vector((0.0, 0.02, -sash_h * 0.5 + frame_t * 0.5)), (sash_w, 0.06, frame_t))
    add_local_box(bm_beams, Vector((0.0, 0.02, +sash_h * 0.5 - frame_t * 0.5)), (sash_w, 0.06, frame_t))
    add_local_box(bm_beams, Vector((-sash_w * 0.5 + frame_t * 0.5, 0.02, 0.0)), (frame_t, 0.06, sash_h))
    add_local_box(bm_beams, Vector((+sash_w * 0.5 - frame_t * 0.5, 0.02, 0.0)), (frame_t, 0.06, sash_h))

    # Central vertical mullion (Słupek środkowy) & 2 horizontal muntins (Szprosy poziome)
    add_local_box(bm_beams, Vector((0.0, 0.02, 0.0)), (0.038, 0.055, sash_h - frame_t))
    for z_muntin in (-sash_h * 0.16, +sash_h * 0.18):
        add_local_box(bm_beams, Vector((0.0, 0.02, z_muntin)), (sash_w - frame_t, 0.04, 0.026))

    # 5. Glass Panes (Szyby - częściowo potłuczone)
    if not broken_glass:
        add_local_box(bm_glass, Vector((0.0, 0.025, 0.0)), (sash_w - 0.06, 0.008, sash_h - 0.06))
    else:
        # Left half glass intact, right top missing, right bottom crooked shard
        add_local_box(bm_glass, Vector((-sash_w * 0.25, 0.025, 0.0)), (sash_w * 0.45, 0.008, sash_h - 0.06))
        add_local_box(bm_glass, Vector((+sash_w * 0.24, 0.025, -sash_h * 0.28)), (sash_w * 0.42, 0.008, sash_h * 0.32), local_euler=(0.0, 0.08, 0.0))

    # 6. Detailed Wooden Shutters (Okiennice z desek ze szpongami, zastrzałem i kutymi zawiasami)
    leaf_w = win_w * 0.50
    leaf_h = win_h - 0.02
    num_planks = 4
    plank_w = (leaf_w - 0.015) / num_planks

    for side_sign, open_deg, droop_deg in [
        (-1.0, shutter_left_angle, left_shutter_droop_deg),
        (+1.0, shutter_right_angle, right_shutter_droop_deg),
    ]:
        hinge_pivot = Vector((side_sign * (win_w * 0.5 + 0.03), -0.145, 0.0))
        open_rad = math.radians(open_deg if side_sign < 0 else -open_deg)
        droop_rad = math.radians(droop_deg)
        shutter_rot = Euler((0.0, droop_rad, open_rad), 'XYZ').to_matrix().to_4x4()

        def add_shutter_part(target_bm, rel_pos, size_xyz, part_euler=(0.0, 0.0, 0.0)):
            sx, sy, sz = size_xyz[0] * 0.5, size_xyz[1] * 0.5, size_xyz[2] * 0.5
            pmat = Euler(part_euler, 'XYZ').to_matrix().to_4x4()
            corners = [
                Vector((-sx, -sy, -sz)), Vector((sx, -sy, -sz)),
                Vector((sx, sy, -sz)), Vector((-sx, sy, -sz)),
                Vector((-sx, -sy, sz)), Vector((sx, -sy, sz)),
                Vector((sx, sy, sz)), Vector((-sx, sy, sz)),
            ]
            v_list = [
                target_bm.verts.new(to_world(hinge_pivot + (shutter_rot @ (rel_pos + (pmat @ c)))))
                for c in corners
            ]
            faces = [
                (0, 3, 2, 1), (4, 5, 6, 7),
                (0, 1, 5, 4), (2, 3, 7, 6),
                (0, 4, 7, 3), (1, 2, 6, 5),
            ]
            for f in faces:
                target_bm.faces.new([v_list[idx] for idx in f])

        # Vertical shutter planks (Deski okiennicy)
        for ip in range(num_planks):
            px = -side_sign * ((ip + 0.5) * (leaf_w / num_planks))
            p_h = leaf_h + random.uniform(-0.015, 0.015)
            add_shutter_part(bm_shutter, Vector((px, 0.0, 0.0)), (plank_w * 0.94, 0.028, p_h))

        # Outer frame trim on shutter leaf
        mid_x = -side_sign * (leaf_w * 0.5)
        # Upper and lower horizontal battens (Szpongi poprzeczne)
        for bz in (-leaf_h * 0.34, +leaf_h * 0.34):
            add_shutter_part(bm_shutter, Vector((mid_x, -0.022, bz)), (leaf_w * 0.92, 0.024, 0.065))

        # Diagonal Z-brace (Zastrzał ukośny)
        diag_angle = side_sign * 0.62
        add_shutter_part(
            bm_shutter,
            Vector((mid_x, -0.022, 0.0)),
            (leaf_w * 0.82, 0.022, 0.052),
            part_euler=(0.0, diag_angle, 0.0),
        )

        # Wrought-iron strap hinges (Kute zawiasy pasowe i czopy w belce)
        for hz in (-leaf_h * 0.34, +leaf_h * 0.34):
            # Iron strap on the shutter
            add_shutter_part(
                bm_iron,
                Vector((-side_sign * (leaf_w * 0.36), -0.036, hz)),
                (leaf_w * 0.68, 0.008, 0.032),
            )
            # Iron pintle pin anchored in the timber jamb
            add_local_box(
                bm_iron,
                Vector((side_sign * (win_w * 0.5 + 0.035), -0.145, hz)),
                (0.028, 0.045, 0.055),
            )

    def finalize_bm(bm_src, sub_name, mat_key):
        mesh = bpy.data.meshes.new(f"{name_prefix}_{sub_name}")
        bm_src.to_mesh(mesh)
        bm_src.free()
        obj = bpy.data.objects.new(f"{name_prefix}_{sub_name}", mesh)
        obj.data.materials.append(mats[mat_key])
        set_smooth(obj)
        link_obj(obj, col_cabin)
        return obj

    finalize_bm(bm_beams, "Belki_Oscieznica", "beam")
    finalize_bm(bm_shutter, "Okiennice", "shutter")
    finalize_bm(bm_iron, "Zawiasy_Kute", "iron")
    finalize_bm(bm_glass, "Szyby", "glass")

def build_cabin():
    x_min, x_max = -2.55, 2.55
    y_front, y_back = -1.30, 2.70
    log_r = 0.125
    step_z = 0.215
    base_z = 0.24
    num_courses = 11
    overhang = 0.38 # Ostatki wystające na węgłach

    # --- 3.1 Stone Foundation (Fundament z kamieni polnych) ---
    stone_idx = 0
    # Perimeter stones along Front, Back, Left, Right walls
    for x in [x_min + i * 0.42 for i in range(13)]:
        for y in (y_front, y_back):
            stone_idx += 1
            gz = ground_height(x, y)
            sag = cabin_sag_offset(x, y, 0.1)
            st = make_deformed_stone(
                f"Kamien_Fundament_{stone_idx:02d}",
                Vector((x, y, gz + 0.10)) + sag,
                (0.26, 0.22, 0.16),
                rot_euler=(0.0, 0.0, random.uniform(-0.4, 0.4)),
                seed=stone_idx * 17,
            )
            link_obj(st, col_cabin)

    for y in [y_front + 0.42 + i * 0.42 for i in range(9)]:
        for x in (x_min, x_max):
            stone_idx += 1
            gz = ground_height(x, y)
            sag = cabin_sag_offset(x, y, 0.1)
            st = make_deformed_stone(
                f"Kamien_Fundament_{stone_idx:02d}",
                Vector((x, y, gz + 0.10)) + sag,
                (0.22, 0.26, 0.16),
                rot_euler=(0.0, 0.0, random.uniform(-0.4, 0.4)),
                seed=stone_idx * 23,
            )
            link_obj(st, col_cabin)

    # --- 3.2 Log Walls & Chinking (Ściany z bali z zamkami węgłowymi i mszeniem) ---
    bm_logs = bmesh.new()
    bm_chink = bmesh.new()

    # Openings on Front Wall (Y = y_front):
    # Left Window: X in [-1.72, -0.80], courses 3..7
    # Front Door:  X in [-0.42, +0.44], courses 0..8
    # Right Window: X in [+0.88, +1.80], courses 3..7
    def split_intervals(full_min, full_max, holes):
        segs = [(full_min, full_max)]
        for h_min, h_max in holes:
            next_segs = []
            for a, b in segs:
                if h_max <= a or h_min >= b:
                    next_segs.append((a, b))
                else:
                    if a < h_min:
                        next_segs.append((a, h_min))
                    if h_max < b:
                        next_segs.append((h_max, b))
            segs = next_segs
        return segs

    seed_counter = 100
    for c in range(num_courses):
        zc_front_back = base_z + c * step_z
        zc_left_right = base_z + (c + 0.5) * step_z

        # Front wall openings
        front_holes = []
        if 0 <= c <= 7:
            front_holes.append((-0.42, 0.44)) # Doorway
        if 3 <= c <= 6:
            front_holes.append((-1.72, -0.80)) # Left window
            front_holes.append((0.88, 1.80))   # Right window

        front_segs = split_intervals(x_min - overhang, x_max + overhang, front_holes)
        for a, b in front_segs:
            seed_counter += 1
            notch = (a <= x_min + 0.01) or (b >= x_max - 0.01)
            # On upper courses of crumbling right corner, shift logs slightly loose
            extra_p2 = Vector((0.0, 0.0, 0.0))
            if c >= 8 and b > x_max:
                extra_p2 = Vector((0.04 * (c - 7), -0.05 * (c - 7), -0.03 * (c - 7)))
            create_log_segment_bm(
                bm_logs,
                Vector((a, y_front, zc_front_back)),
                Vector((b, y_front, zc_front_back)) + extra_p2,
                radius=log_r,
                notch_ends=notch,
                seed=seed_counter,
            )
            if c > 0 and (b - a) > 0.35:
                add_box_to_bm(
                    bm_chink,
                    Vector(((a + b) * 0.5, y_front, zc_front_back - step_z * 0.5)),
                    (b - a - 0.18, 0.16, 0.045),
                )

        # Back wall (solid logs)
        seed_counter += 1
        create_log_segment_bm(
            bm_logs,
            Vector((x_min - overhang, y_back, zc_front_back)),
            Vector((x_max + overhang, y_back, zc_front_back)),
            radius=log_r,
            notch_ends=True,
            seed=seed_counter,
        )

        # Left wall (with side window at Y in [0.24, 1.16] on courses 3..6)
        left_holes = [(0.24, 1.16)] if (3 <= c <= 6) else []
        for a, b in split_intervals(y_front - overhang, y_back + overhang, left_holes):
            seed_counter += 1
            create_log_segment_bm(
                bm_logs,
                Vector((x_min, a, zc_left_right)),
                Vector((x_min, b, zc_left_right)),
                radius=log_r,
                notch_ends=True,
                seed=seed_counter,
            )

        # Right wall (partially collapsed at top courses c >= 9)
        if c < 9:
            seed_counter += 1
            create_log_segment_bm(
                bm_logs,
                Vector((x_max, y_front - overhang, zc_left_right)),
                Vector((x_max, y_back + overhang, zc_left_right)),
                radius=log_r,
                notch_ends=True,
                seed=seed_counter,
            )
        elif c == 9:
            # Half broken log hanging on right wall
            seed_counter += 1
            create_log_segment_bm(
                bm_logs,
                Vector((x_max + 0.05, y_front + 0.5, zc_left_right - 0.12)),
                Vector((x_max, y_back + overhang, zc_left_right)),
                radius=log_r,
                notch_ends=True,
                seed=seed_counter,
            )

    # --- 3.3 Gable Wall Logs (Szczyty dachu z bali) ---
    eave_z = base_z + num_courses * step_z
    ridge_z = eave_z + 1.85
    y_mid = (y_front + y_back) * 0.5
    half_span_y = (y_back - y_front) * 0.5 + 0.25

    for gc in range(8):
        gz = eave_z + (gc + 0.5) * step_z
        frac = (gz - eave_z) / (ridge_z - eave_z)
        if frac >= 0.96:
            continue
        span = half_span_y * (1.0 - frac)
        # Left gable intact
        seed_counter += 1
        create_log_segment_bm(
            bm_logs,
            Vector((x_min, y_mid - span, gz)),
            Vector((x_min, y_mid + span, gz)),
            radius=log_r * 0.92,
            notch_ends=False,
            seed=seed_counter,
        )
        # Right gable crumbling (missing upper gable logs, tilted middle ones)
        if gc <= 4:
            seed_counter += 1
            tilt_z = -0.06 * gc
            create_log_segment_bm(
                bm_logs,
                Vector((x_max + 0.04 * gc, y_mid - span, gz + tilt_z)),
                Vector((x_max + 0.02 * gc, y_mid + span, gz)),
                radius=log_r * 0.92,
                notch_ends=False,
                seed=seed_counter,
            )

    # Fallen/rotten logs lying on the ground beside the right wall & front corner
    for f_idx, (p_a, p_b) in enumerate([
        (Vector((2.75, -1.75, ground_height(2.75, -1.75) + 0.11)), Vector((3.85, -0.35, ground_height(3.85, -0.35) + 0.11))),
        (Vector((2.95, -0.80, ground_height(2.95, -0.80) + 0.12)), Vector((4.10, 1.40, ground_height(4.10, 1.40) + 0.11))),
        (Vector((1.35, -2.05, ground_height(1.35, -2.05) + 0.09)), Vector((2.50, -2.45, ground_height(2.50, -2.45) + 0.09))),
    ]):
        create_log_segment_bm(bm_logs, p_a, p_b, radius=0.115, notch_ends=True, seed=900 + f_idx)

    mesh_logs = bpy.data.meshes.new("Sciany_Bale")
    bm_logs.to_mesh(mesh_logs)
    bm_logs.free()
    obj_logs = bpy.data.objects.new("Sciany_Bale", mesh_logs)
    obj_logs.data.materials.append(mats["log"])
    set_smooth(obj_logs)
    link_obj(obj_logs, col_cabin)

    mesh_chink = bpy.data.meshes.new("Mszenie_Miedzy_Balami")
    bm_chink.to_mesh(mesh_chink)
    bm_chink.free()
    obj_chink = bpy.data.objects.new("Mszenie_Miedzy_Balami", mesh_chink)
    obj_chink.data.materials.append(mats["chink"])
    set_smooth(obj_chink)
    link_obj(obj_chink, col_cabin)

    # --- 3.4 Detailed Windows & Shutters (Szczegółowe Okna i Okiennice) ---
    # Front Left Window
    build_window_and_shutters(
        "Okno_Front_Lewe",
        wall_center=Vector((-1.26, y_front, base_z + 4.5 * step_z)),
        wall_normal_angle_z=0.0,
        win_w=0.90,
        win_h=0.92,
        shutter_left_angle=-145.0,
        shutter_right_angle=-36.0,
        left_shutter_droop_deg=15.0,  # Hanging crookedly on one hinge!
        right_shutter_droop_deg=-3.0,
        broken_glass=False,
    )
    # Front Right Window (in the sagging wall section, broken glass, hanging shutter)
    build_window_and_shutters(
        "Okno_Front_Prawe",
        wall_center=Vector((1.34, y_front, base_z + 4.5 * step_z)),
        wall_normal_angle_z=0.0,
        win_w=0.90,
        win_h=0.92,
        shutter_left_angle=-52.0,
        shutter_right_angle=-152.0,
        left_shutter_droop_deg=-8.0,
        right_shutter_droop_deg=19.0, # Severely tilted shutter!
        broken_glass=True,
    )
    # Side Left Window
    build_window_and_shutters(
        "Okno_Boczne_Lewe",
        wall_center=Vector((x_min, 0.70, base_z + 4.8 * step_z)),
        wall_normal_angle_z=-math.pi * 0.5,
        win_w=0.88,
        win_h=0.90,
        shutter_left_angle=-130.0,
        shutter_right_angle=-120.0,
        left_shutter_droop_deg=6.0,
        right_shutter_droop_deg=-9.0,
        broken_glass=False,
    )

    # --- 3.5 Heavy Plank Door & Sagging Porch (Drzwi z desek i ganek) ---
    bm_door = bmesh.new()
    bm_door_iron = bmesh.new()
    door_center = Vector((0.01, y_front, base_z + 3.5 * step_z))
    door_w, door_h = 0.86, 1.72
    # Heavy door jambs & carved lintel beam
    add_box_to_bm(bm_door, door_center + Vector((-door_w * 0.5 - 0.065, 0.0, 0.0)), (0.13, 0.30, door_h + 0.08))
    add_box_to_bm(bm_door, door_center + Vector((+door_w * 0.5 + 0.065, 0.0, 0.0)), (0.13, 0.30, door_h + 0.08))
    add_box_to_bm(bm_door, door_center + Vector((0.0, -0.02, door_h * 0.5 + 0.075)), (door_w + 0.34, 0.32, 0.15))
    add_box_to_bm(bm_door, door_center + Vector((0.0, -0.04, -door_h * 0.5 - 0.05)), (door_w + 0.28, 0.34, 0.11))

    # Door leaf ajar (uchylone i lekko opadnięte drzwi z desek)
    hinge_pos = door_center + Vector((-door_w * 0.5 + 0.02, -0.08, 0.0))
    ajar_rot = Euler((0.04, 0.05, math.radians(-32.0)), 'XYZ')
    for ip in range(5):
        px = (ip + 0.5) * (door_w / 5.0)
        rel = Euler(ajar_rot).to_matrix() @ Vector((px, 0.0, 0.0))
        add_box_to_bm(bm_door, hinge_pos + rel, (door_w / 5.0 * 0.94, 0.042, door_h - 0.04), rot_euler=ajar_rot)

    # Cross battens & diagonal Z-brace on door
    for bz in (-0.55, 0.55):
        rel = Euler(ajar_rot).to_matrix() @ Vector((door_w * 0.5, -0.03, bz))
        add_box_to_bm(bm_door, hinge_pos + rel, (door_w * 0.92, 0.032, 0.09), rot_euler=ajar_rot)
        rel_iron = Euler(ajar_rot).to_matrix() @ Vector((door_w * 0.35, -0.048, bz))
        add_box_to_bm(bm_door_iron, hinge_pos + rel_iron, (door_w * 0.65, 0.01, 0.04), rot_euler=ajar_rot)

    # Wooden Porch Deck & Steps (Rozpadające się schodki przed wejściem)
    for step_i in range(3):
        sy = y_front - 0.32 - step_i * 0.30
        sz = ground_height(0.0, sy) + (2 - step_i) * 0.085 + 0.05
        tilt = 0.035 if step_i == 1 else -0.02
        add_box_to_bm(bm_door, Vector((0.02, sy, sz)), (1.28, 0.27, 0.065), rot_euler=(0.0, tilt, 0.02 * step_i))

    mesh_door = bpy.data.meshes.new("Drzwi_I_Ganek")
    bm_door.to_mesh(mesh_door)
    bm_door.free()
    obj_door = bpy.data.objects.new("Drzwi_I_Ganek", mesh_door)
    obj_door.data.materials.append(mats["beam"])
    set_smooth(obj_door)
    link_obj(obj_door, col_cabin)

    mesh_d_iron = bpy.data.meshes.new("Okucia_Drzwi")
    bm_door_iron.to_mesh(mesh_d_iron)
    bm_door_iron.free()
    obj_d_iron = bpy.data.objects.new("Okucia_Drzwi", mesh_d_iron)
    obj_d_iron.data.materials.append(mats["iron"])
    link_obj(obj_d_iron, col_cabin)

    # --- 3.6 Roof Structure (Więźba dachowa: Kalenica, Krokwie, Łaty) ---
    bm_roof_frame = bmesh.new()
    roof_x_min, roof_x_max = x_min - 0.52, x_max + 0.52
    eave_y_front = y_front - 0.55
    eave_y_back = y_back + 0.55
    eave_z_low = eave_z - 0.18

    # Ridge beam (Kalenica)
    create_log_segment_bm(
        bm_roof_frame,
        Vector((roof_x_min, y_mid, ridge_z)),
        Vector((roof_x_max, y_mid, ridge_z)),
        radius=0.095,
        segs_len=20,
        segs_circ=10,
        notch_ends=False,
        seed=501,
    )

    # Rafter pairs (Krokwie)
    num_rafters = 11
    for ir in range(num_rafters):
        rx = roof_x_min + 0.12 + (ir / (num_rafters - 1)) * (roof_x_max - roof_x_min - 0.24)
        top_pt = Vector((rx, y_mid, ridge_z))
        front_pt = Vector((rx, eave_y_front, eave_z_low))
        back_pt = Vector((rx, eave_y_back, eave_z_low))
        create_log_segment_bm(bm_roof_frame, top_pt, front_pt, radius=0.055, segs_len=8, segs_circ=8, notch_ends=False, seed=600 + ir)
        create_log_segment_bm(bm_roof_frame, top_pt, back_pt, radius=0.055, segs_len=8, segs_circ=8, notch_ends=False, seed=650 + ir)

    # Roof battens (Łaty pod gont) — visible through the collapsed roof hole!
    num_battens = 9
    for side_s, y_eave in [(-1.0, eave_y_front), (1.0, eave_y_back)]:
        for ib in range(num_battens):
            t = (ib + 0.5) / num_battens
            by = y_eave + (y_mid - y_eave) * t
            bz = eave_z_low + (ridge_z - eave_z_low) * t + 0.045
            slope_ang = math.atan2(ridge_z - eave_z_low, abs(y_mid - y_eave)) * (-side_s)
            # In the collapsed hole area on the front slope, break 2 battens
            if side_s < 0 and 4 <= ib <= 6:
                add_box_to_bm(bm_roof_frame, Vector(((roof_x_min + 0.75) * 0.5, by, bz)), (0.75 - roof_x_min, 0.05, 0.03), rot_euler=(slope_ang, 0.0, 0.0))
                add_box_to_bm(bm_roof_frame, Vector(((1.95 + roof_x_max) * 0.5, by, bz)), (roof_x_max - 1.95, 0.05, 0.03), rot_euler=(slope_ang, 0.0, 0.0))
            else:
                add_box_to_bm(bm_roof_frame, Vector((0.0, by, bz)), (roof_x_max - roof_x_min, 0.05, 0.03), rot_euler=(slope_ang, 0.0, 0.0))

    mesh_rf = bpy.data.meshes.new("Wiezba_Dachowa_Krokwie_Laty")
    bm_roof_frame.to_mesh(mesh_rf)
    bm_roof_frame.free()
    obj_rf = bpy.data.objects.new("Wiezba_Dachowa_Krokwie_Laty", mesh_rf)
    obj_rf.data.materials.append(mats["beam"])
    set_smooth(obj_rf)
    link_obj(obj_rf, col_cabin)

    # --- 3.7 Individual Wooden Shingles (Gont Drewniany - Rozwalający się Dach) ---
    bm_shingles = bmesh.new()
    rng_s = random.Random(777)

    def add_shingle_to_bm(bm_target, pos, length_y, width_x, thick_z, rot_euler):
        sx = width_x * 0.5
        sy = length_y * 0.5
        sz = thick_z * 0.5
        rmat = Euler(rot_euler, 'XYZ').to_matrix().to_4x4()
        # Wedge-shaped split shingle (thicker at butt end, thinner at top)
        corners = [
            Vector((-sx, -sy, -sz * 1.3)), Vector((sx, -sy, -sz * 1.3)),
            Vector((sx * 0.94, sy, -sz * 0.6)), Vector((-sx * 0.94, sy, -sz * 0.6)),
            Vector((-sx, -sy, sz * 1.3)), Vector((sx, -sy, sz * 1.3)),
            Vector((sx * 0.94, sy, sz * 0.6)), Vector((-sx * 0.94, sy, sz * 0.6)),
        ]
        v_list = [bm_target.verts.new(pos + (rmat @ c)) for c in corners]
        faces = [
            (0, 3, 2, 1), (4, 5, 6, 7),
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 4, 7, 3), (1, 2, 6, 5),
        ]
        for f in faces:
            bm_target.faces.new([v_list[idx] for idx in f])

    num_rows = 11
    shingle_w_nom = 0.145
    for side_s, y_eave in [(-1.0, eave_y_front), (1.0, eave_y_back)]:
        slope_vec = Vector((0.0, y_mid - y_eave, ridge_z - eave_z_low))
        slope_len = slope_vec.length
        slope_pitch = math.atan2(ridge_z - eave_z_low, abs(y_mid - y_eave)) * (-side_s)
        shingle_len = (slope_len / num_rows) * 1.32

        for r in range(num_rows):
            t = (r + 0.45) / num_rows
            row_y = y_eave + (y_mid - y_eave) * t
            row_z = eave_z_low + (ridge_z - eave_z_low) * t + 0.075 + (r % 2) * 0.006
            x_cursor = roof_x_min + rng_s.uniform(0.0, 0.04)

            while x_cursor < roof_x_max - 0.05:
                sw = shingle_w_nom * rng_s.uniform(0.82, 1.22)
                sx_center = x_cursor + sw * 0.5
                x_cursor += sw + rng_s.uniform(0.003, 0.012)

                # Check if inside collapsed hole on front-right slope or ragged eave
                hole_dist = math.hypot((sx_center - 1.32) / 0.72, (t - 0.58) / 0.28) if side_s < 0 else 99.0
                eave_rot_hole = math.hypot((sx_center - 2.25) / 0.65, (t - 0.12) / 0.22) if side_s < 0 else 99.0

                if hole_dist < 0.78 or eave_rot_hole < 0.72:
                    # Missing shingle exposing rafters and battens!
                    continue

                # Border of hole: loose, slipped, or crookedly hanging shingles!
                slipped_y = 0.0
                slipped_z = 0.0
                extra_yaw = rng_s.uniform(-0.045, 0.045)
                extra_roll = rng_s.uniform(-0.05, 0.05)
                extra_pitch = rng_s.uniform(-0.04, 0.04)

                if hole_dist < 1.18 or eave_rot_hole < 1.12:
                    if rng_s.random() < 0.35:
                        continue
                    slipped_y = side_s * rng_s.uniform(0.04, 0.16)
                    slipped_z = -rng_s.uniform(0.02, 0.09)
                    extra_yaw = rng_s.uniform(-0.38, 0.38)
                    extra_roll = rng_s.uniform(-0.22, 0.22)

                # Random aging jitter across entire roof
                elif rng_s.random() < 0.045:
                    continue

                base_pos = Vector((sx_center, row_y + slipped_y, row_z + slipped_z))
                pos_sagged = base_pos + cabin_sag_offset(base_pos.x, base_pos.y, base_pos.z)

                rot = (
                    slope_pitch + extra_pitch,
                    extra_roll - 0.06 * max(0.0, (sx_center - 0.2) / 2.5),
                    (0.0 if side_s < 0 else math.pi) + extra_yaw,
                )
                add_shingle_to_bm(bm_shingles, pos_sagged, shingle_len, sw, 0.018, rot)

    # Ridge cap shingles (Gąsiory / Gont kalenicowy)
    for rx_i in range(32):
        rx = roof_x_min + 0.08 + rx_i * 0.19
        if 0.95 < rx < 1.65 and rng_s.random() < 0.55:
            continue
        p_ridge = Vector((rx, y_mid, ridge_z + 0.11))
        p_ridge += cabin_sag_offset(p_ridge.x, p_ridge.y, p_ridge.z)
        add_shingle_to_bm(bm_shingles, p_ridge + Vector((0.0, -0.09, -0.02)), 0.26, 0.17, 0.022, (0.65, rng_s.uniform(-0.08, 0.08), 0.0))
        add_shingle_to_bm(bm_shingles, p_ridge + Vector((0.0, +0.09, -0.02)), 0.26, 0.17, 0.022, (-0.65, rng_s.uniform(-0.08, 0.08), math.pi))

    # Fallen shingles scattered on the ground in front of the collapsed roof section
    for fs in range(28):
        fx = rng_s.uniform(0.3, 2.8)
        fy = rng_s.uniform(-2.7, -1.45)
        fz = ground_height(fx, fy) + 0.018
        add_shingle_to_bm(
            bm_shingles,
            Vector((fx, fy, fz)),
            0.34,
            rng_s.uniform(0.11, 0.17),
            0.018,
            (rng_s.uniform(-0.18, 0.18), rng_s.uniform(-0.18, 0.18), rng_s.uniform(0.0, math.pi * 2.0)),
        )

    mesh_shingles = bpy.data.meshes.new("Dach_Gont_Drewniany")
    bm_shingles.to_mesh(mesh_shingles)
    bm_shingles.free()
    obj_shingles = bpy.data.objects.new("Dach_Gont_Drewniany", mesh_shingles)
    obj_shingles.data.materials.append(mats["shingle"])
    link_obj(obj_shingles, col_cabin)

    # --- 3.8 Crumbling Stone Chimney (Rozpadający się kamienny komin) ---
    chim_x, chim_y = -1.45, 1.35
    for cz_i in range(7):
        for ang_i in range(6):
            ang = (ang_i / 6.0) * math.pi * 2.0 + (cz_i % 2) * 0.5
            cx = chim_x + math.cos(ang) * 0.26
            cy = chim_y + math.sin(ang) * 0.24
            cz = ridge_z - 0.45 + cz_i * 0.14
            if cz_i == 6 and ang_i in (1, 2):
                continue # Tumbled top stones
            st = make_deformed_stone(
                f"Kamien_Komin_{cz_i}_{ang_i}",
                Vector((cx, cy, cz)) + cabin_sag_offset(cx, cy, cz),
                (0.17, 0.15, 0.10),
                seed=1200 + cz_i * 10 + ang_i,
            )
            link_obj(st, col_cabin)

build_cabin()

# ==============================================================================
# 4. DETAILED WOODEN FARM CART (WÓZ DREWNIANY DRABINIASTY)
# ==============================================================================
def build_wooden_cart():
    bm_wood = bmesh.new()
    bm_iron = bmesh.new()

    cart_origin = Vector((1.75, -3.45, ground_height(1.75, -3.45) + 0.01))
    cart_yaw = math.radians(-148.0) # Facing forward-left towards the foreground puddle
    cart_roll = math.radians(4.2)   # Slightly tilted into the muddy wheel rut
    cart_pitch = math.radians(-1.8)
    cart_mat = Matrix.Translation(cart_origin) @ Euler((cart_pitch, cart_roll, cart_yaw), 'XYZ').to_matrix().to_4x4()

    def add_cart_box(target_bm, local_pos, size_xyz, local_euler=(0.0, 0.0, 0.0)):
        sx, sy, sz = size_xyz[0] * 0.5, size_xyz[1] * 0.5, size_xyz[2] * 0.5
        rmat = Euler(local_euler, 'XYZ').to_matrix().to_4x4()
        corners = [
            Vector((-sx, -sy, -sz)), Vector((sx, -sy, -sz)),
            Vector((sx, sy, -sz)), Vector((-sx, sy, -sz)),
            Vector((-sx, -sy, sz)), Vector((sx, -sy, sz)),
            Vector((sx, sy, sz)), Vector((-sx, sy, sz)),
        ]
        v_list = [target_bm.verts.new(cart_mat @ (local_pos + (rmat @ c))) for c in corners]
        faces = [
            (0, 3, 2, 1), (4, 5, 6, 7),
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 4, 7, 3), (1, 2, 6, 5),
        ]
        for f in faces:
            target_bm.faces.new([v_list[idx] for idx in f])

    def add_spoked_wheel(center_local, radius, width, num_spokes=10, steer_yaw=0.0, camber_roll=0.0):
        w_rot = Euler((0.0, camber_roll, steer_yaw), 'XYZ').to_matrix().to_4x4()

        def w_pt(pt):
            return cart_mat @ (center_local + (w_rot @ pt))

        # 1. Outer Wooden Rim (Dzwona koła) + Iron Tire Band (Obręcz żelazna)
        segs = 28
        r_outer_iron = radius
        r_outer_wood = radius - 0.012
        r_inner_wood = radius - 0.062
        half_w = width * 0.5

        for target_bm, r_in, r_out, hw in [
            (bm_wood, r_inner_wood, r_outer_wood, half_w),
            (bm_iron, r_outer_wood, r_outer_iron, half_w * 1.03),
        ]:
            ring_verts = []
            for i in range(segs):
                ang = (i / segs) * 2.0 * math.pi
                ca, sa = math.cos(ang), math.sin(ang)
                v0 = target_bm.verts.new(w_pt(Vector((-hw, ca * r_in, sa * r_in))))
                v1 = target_bm.verts.new(w_pt(Vector((+hw, ca * r_in, sa * r_in))))
                v2 = target_bm.verts.new(w_pt(Vector((+hw, ca * r_out, sa * r_out))))
                v3 = target_bm.verts.new(w_pt(Vector((-hw, ca * r_out, sa * r_out))))
                ring_verts.append((v0, v1, v2, v3))
            for i in range(segs):
                ni = (i + 1) % segs
                a0, a1, a2, a3 = ring_verts[i]
                b0, b1, b2, b3 = ring_verts[ni]
                target_bm.faces.new((a0, b0, b1, a1))
                target_bm.faces.new((a2, b2, b3, a3))
                target_bm.faces.new((a1, b1, b2, a2))
                target_bm.faces.new((a3, b3, b0, a0))

        # 2. Wooden Hub (Piasta) + Iron Hub Rings
        hub_r = 0.085
        hub_len = width * 2.5
        for i in range(16):
            ang0 = (i / 16) * 2.0 * math.pi
            ang1 = ((i + 1) / 16) * 2.0 * math.pi
            for target_bm, x0, x1, hr in [
                (bm_wood, -hub_len * 0.5, hub_len * 0.5, hub_r),
                (bm_iron, -hub_len * 0.46, -hub_len * 0.30, hub_r * 1.06),
                (bm_iron, +hub_len * 0.30, +hub_len * 0.46, hub_r * 1.06),
            ]:
                p00 = target_bm.verts.new(w_pt(Vector((x0, math.cos(ang0) * hr, math.sin(ang0) * hr))))
                p01 = target_bm.verts.new(w_pt(Vector((x1, math.cos(ang0) * hr, math.sin(ang0) * hr))))
                p11 = target_bm.verts.new(w_pt(Vector((x1, math.cos(ang1) * hr, math.sin(ang1) * hr))))
                p10 = target_bm.verts.new(w_pt(Vector((x0, math.cos(ang1) * hr, math.sin(ang1) * hr))))
                target_bm.faces.new((p00, p01, p11, p10))

        # 3. Radial Wooden Spokes (Szprychy)
        for s_i in range(num_spokes):
            ang = (s_i / num_spokes) * 2.0 * math.pi
            mid_r = (hub_r + r_inner_wood) * 0.5
            spk_len = (r_inner_wood - hub_r) + 0.02
            pos_local = Vector((0.0, math.cos(ang) * mid_r, math.sin(ang) * mid_r))
            spk_rot = Euler((ang, 0.0, 0.0), 'XYZ')
            sx, sy, sz = 0.016, 0.018, spk_len * 0.5
            smat = spk_rot.to_matrix().to_4x4()
            corners = [
                Vector((-sx, -sy, -sz)), Vector((sx, -sy, -sz)),
                Vector((sx, sy, -sz)), Vector((-sx, sy, -sz)),
                Vector((-sx, -sy, sz)), Vector((sx, -sy, sz)),
                Vector((sx, sy, sz)), Vector((-sx, sy, sz)),
            ]
            v_list = [bm_wood.verts.new(w_pt(pos_local + (smat @ c))) for c in corners]
            for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(2,3,7,6),(0,4,7,3),(1,2,6,5)]:
                bm_wood.faces.new([v_list[idx] for idx in f])

    # Wheel positions (local Y = forward, local X = right)
    front_y = 0.88
    rear_y = -0.88
    track_half_x = 0.64
    r_front = 0.40
    r_rear = 0.49
    steer_ang = math.radians(14.0)

    add_spoked_wheel(Vector((-track_half_x, front_y, r_front)), r_front, 0.065, num_spokes=10, steer_yaw=steer_ang, camber_roll=-0.04)
    add_spoked_wheel(Vector((+track_half_x, front_y, r_front)), r_front, 0.065, num_spokes=10, steer_yaw=steer_ang, camber_roll=0.04)
    add_spoked_wheel(Vector((-track_half_x, rear_y, r_rear)), r_rear, 0.070, num_spokes=12, steer_yaw=0.0, camber_roll=-0.03)
    add_spoked_wheel(Vector((+track_half_x, rear_y, r_rear)), r_rear, 0.070, num_spokes=12, steer_yaw=0.0, camber_roll=0.05)

    # Axles & Bolsters (Osie i nasady)
    add_cart_box(bm_wood, Vector((0.0, front_y, r_front)), (track_half_x * 2.25, 0.09, 0.09), local_euler=(0.0, 0.0, steer_ang))
    add_cart_box(bm_wood, Vector((0.0, rear_y, r_rear)), (track_half_x * 2.25, 0.10, 0.10))
    # Central reach pole (Rozwora)
    add_cart_box(bm_wood, Vector((0.0, -0.10, (r_front + r_rear) * 0.5)), (0.08, 2.35, 0.08), local_euler=(0.04, 0.0, 0.0))

    # Floor bed planks (Dennica wozu)
    bed_z = r_rear + 0.09
    for px in (-0.32, -0.11, 0.11, 0.32):
        add_cart_box(bm_wood, Vector((px, 0.0, bed_z)), (0.19, 2.35, 0.035))

    # Slanted Ladder Sides (Drabiny boczne wozu - drągi i szczebliny)
    for side_s in (-1.0, 1.0):
        flare_roll = side_s * math.radians(22.0)
        base_x = side_s * 0.44
        top_x = side_s * 0.67
        # Bottom and top ladder rails (Drągi drabin)
        add_cart_box(bm_wood, Vector((base_x, 0.0, bed_z + 0.06)), (0.055, 2.48, 0.065), local_euler=(0.0, flare_roll, 0.0))
        add_cart_box(bm_wood, Vector((top_x, 0.0, bed_z + 0.58)), (0.060, 2.62, 0.070), local_euler=(0.0, flare_roll, 0.0))
        # Ladder rungs (Szczebliny)
        num_rungs = 11
        for ir in range(num_rungs):
            if side_s > 0 and ir == 7:
                continue # One broken/missing rung for authentic wear
            ry = -1.12 + (ir / (num_rungs - 1)) * 2.24
            mid_x = (base_x + top_x) * 0.5
            mid_z = bed_z + 0.32
            tilt_pitch = 0.08 if (ir == 3 and side_s < 0) else 0.0
            add_cart_box(
                bm_wood,
                Vector((mid_x, ry, mid_z)),
                (0.032, 0.042, 0.58),
                local_euler=(tilt_pitch, flare_roll, 0.0),
            )
        # External bolster stakes (Kłonice podtrzymujące drabiny)
        for ky in (front_y, rear_y):
            add_cart_box(
                bm_wood,
                Vector((side_s * 0.58, ky, bed_z + 0.28)),
                (0.055, 0.065, 0.68),
                local_euler=(0.0, side_s * math.radians(24.0), 0.0),
            )
            add_cart_box(bm_iron, Vector((side_s * 0.58, ky, bed_z + 0.02)), (0.07, 0.08, 0.04))

    # Front Drawbar / Shaft (Dyszel oparty o błotnistą drogę z przodu)
    shaft_len = 1.85
    shaft_pitch = math.radians(-11.5)
    add_cart_box(
        bm_wood,
        Vector((0.18, front_y + shaft_len * 0.48, r_front - 0.16)),
        (0.065, shaft_len, 0.065),
        local_euler=(shaft_pitch, 0.0, steer_ang),
    )
    # Swingle-tree / Orчик at front of axle
    add_cart_box(
        bm_wood,
        Vector((0.05, front_y + 0.28, r_front - 0.02)),
        (0.78, 0.055, 0.055),
        local_euler=(0.0, 0.0, steer_ang + 0.12),
    )
    add_cart_box(
        bm_iron,
        Vector((0.05, front_y + 0.28, r_front - 0.02)),
        (0.09, 0.07, 0.07),
        local_euler=(0.0, 0.0, steer_ang),
    )

    # Stacked cut firewood logs inside the cart bed
    for lx, ly, lz, l_yaw in [
        (-0.12, -0.25, bed_z + 0.10, 0.08),
        (+0.14, -0.20, bed_z + 0.10, -0.05),
        (0.02, -0.22, bed_z + 0.24, 0.14),
    ]:
        add_cart_box(bm_wood, Vector((lx, ly, lz)), (0.15, 1.05, 0.15), local_euler=(0.0, 0.0, l_yaw))

    mesh_cw = bpy.data.meshes.new("Woz_Drewniany_Konstrukcja")
    bm_wood.to_mesh(mesh_cw)
    bm_wood.free()
    obj_cw = bpy.data.objects.new("Woz_Drewniany_Konstrukcja", mesh_cw)
    obj_cw.data.materials.append(mats["cart"])
    set_smooth(obj_cw)
    link_obj(obj_cw, col_cart)

    mesh_ci = bpy.data.meshes.new("Woz_Drewniany_Okucia_Obrecze")
    bm_iron.to_mesh(mesh_ci)
    bm_iron.free()
    obj_ci = bpy.data.objects.new("Woz_Drewniany_Okucia_Obrecze", mesh_ci)
    obj_ci.data.materials.append(mats["iron"])
    set_smooth(obj_ci)
    link_obj(obj_ci, col_cart)

build_wooden_cart()

# ==============================================================================
# 5. REALISTIC VEGETATION: MULTI-FROND FERNS (PAPROCIE), GRASS & PLANTS
# ==============================================================================
def add_fern_plant(bm_fern, pos, scale=1.0, seed=0):
    """Generates a lush multi-frond forest fern with arching stems and individual pinnules/leaflets."""
    rng = random.Random(seed)
    num_fronds = rng.randint(11, 16)
    for fi in range(num_fronds):
        base_az = (fi / num_fronds) * 2.0 * math.pi + rng.uniform(-0.18, 0.18)
        frond_len = rng.uniform(0.42, 0.72) * scale
        arch_height = rng.uniform(0.20, 0.38) * scale
        droop = rng.uniform(0.08, 0.20) * scale

        dir_xy = Vector((math.cos(base_az), math.sin(base_az), 0.0))
        side_xy = Vector((-dir_xy.y, dir_xy.x, 0.0))

        # Build central stem (rachis) + pairs of leaflets (pinnules)
        num_pairs = 12
        prev_pt = pos + Vector((0.0, 0.0, 0.02 * scale))
        for ip in range(1, num_pairs + 1):
            t = ip / num_pairs
            # Arching curve
            reach = frond_len * t
            z_off = arch_height * math.sin(t * math.pi * 0.82) - droop * (t ** 2.2)
            cur_pt = pos + dir_xy * reach + Vector((0.0, 0.0, max(0.015, z_off)))

            # Thin central stem segment
            s0 = bm_fern.verts.new(prev_pt - side_xy * 0.004 * scale)
            s1 = bm_fern.verts.new(prev_pt + side_xy * 0.004 * scale)
            s2 = bm_fern.verts.new(cur_pt + side_xy * 0.003 * scale)
            s3 = bm_fern.verts.new(cur_pt - side_xy * 0.003 * scale)
            bm_fern.faces.new((s0, s1, s2, s3))

            # Leaflet width envelope (widest around t=0.35, tapering to tip)
            env = math.sin((t ** 0.75) * math.pi)
            pin_len = 0.145 * scale * env
            pin_w = 0.024 * scale * (0.4 + 0.6 * env)

            if pin_len > 0.012:
                tangent = (cur_pt - prev_pt).normalized()
                for lr_sign in (-1.0, 1.0):
                    base_pin = prev_pt.lerp(cur_pt, 0.5)
                    pin_dir = (side_xy * lr_sign + tangent * 0.38 + Vector((0.0, 0.0, 0.12 * (1.0 - t)))).normalized()
                    mid_pin = base_pin + pin_dir * (pin_len * 0.55) + Vector((0.0, 0.0, 0.008 * scale))
                    tip_pin = base_pin + pin_dir * pin_len - Vector((0.0, 0.0, 0.006 * scale))

                    v_b0 = bm_fern.verts.new(base_pin - tangent * (pin_w * 0.5))
                    v_b1 = bm_fern.verts.new(base_pin + tangent * (pin_w * 0.5))
                    v_m0 = bm_fern.verts.new(mid_pin - tangent * (pin_w * 0.38))
                    v_m1 = bm_fern.verts.new(mid_pin + tangent * (pin_w * 0.38))
                    v_tip = bm_fern.verts.new(tip_pin)

                    bm_fern.faces.new((v_b0, v_b1, v_m1, v_m0))
                    bm_fern.faces.new((v_m0, v_m1, v_tip))

            prev_pt = cur_pt

def add_grass_tuft(bm_grass, pos, scale=1.0, seed=0):
    """Generates a realistic multi-blade grass & wild herb clump."""
    rng = random.Random(seed)
    num_blades = rng.randint(10, 18)
    for bi in range(num_blades):
        az = rng.uniform(0.0, 2.0 * math.pi)
        r_off = rng.uniform(0.0, 0.08) * scale
        bx = pos.x + math.cos(az) * r_off
        by = pos.y + math.sin(az) * r_off
        bz = pos.z

        b_dir = Vector((math.cos(az), math.sin(az), 0.0))
        b_side = Vector((-b_dir.y, b_dir.x, 0.0))

        h = rng.uniform(0.14, 0.36) * scale
        bend = rng.uniform(0.05, 0.18) * scale
        w0 = rng.uniform(0.008, 0.015) * scale

        p0 = Vector((bx, by, bz))
        p1 = p0 + b_dir * (bend * 0.35) + Vector((0.0, 0.0, h * 0.55))
        p2 = p0 + b_dir * bend + Vector((0.0, 0.0, h))

        v0 = bm_grass.verts.new(p0 - b_side * w0)
        v1 = bm_grass.verts.new(p0 + b_side * w0)
        v2 = bm_grass.verts.new(p1 + b_side * (w0 * 0.65))
        v3 = bm_grass.verts.new(p1 - b_side * (w0 * 0.65))
        v4 = bm_grass.verts.new(p2)

        bm_grass.faces.new((v0, v1, v2, v3))
        bm_grass.faces.new((v3, v2, v4))

def build_vegetation_and_stones():
    bm_ferns = bmesh.new()
    bm_grass = bmesh.new()
    rng = random.Random(2026)

    # 1. Strategic Hero Fern Clusters (Paprocie przed chatą, przy kamieniach, ganku, wozie i kałużach)
    fern_spots = [
        # Along front cabin foundation & under windows
        (-2.25, -1.55, 1.15), (-1.85, -1.70, 0.95), (-1.40, -1.62, 1.10), (-0.95, -1.65, 0.85),
        (-0.68, -2.05, 1.05), # Left of porch steps
        (0.68, -1.95, 1.15), (1.05, -1.68, 0.95), (1.55, -1.72, 1.20), (2.15, -1.65, 1.05),
        # Around fallen logs on the right
        (2.85, -1.35, 1.25), (3.15, -0.55, 1.10), (2.60, -2.65, 0.90),
        # Around puddle banks in the foreground
        (-1.65, -3.55, 1.05), (-1.20, -3.20, 0.88), (-2.15, -4.15, 1.12),
        (0.85, -4.75, 0.95), (0.45, -3.15, 0.90), (-0.95, -5.25, 1.00),
        # Near the wooden cart & left side of cabin
        (2.75, -3.85, 1.08), (2.45, -4.35, 0.85), (0.85, -2.75, 0.85),
        (-2.90, -0.80, 1.15), (-2.85, 0.15, 1.05), (-2.95, 1.25, 1.20),
        # Foreground framing ferns near camera left & right
        (-3.35, -6.10, 1.20), (-2.85, -6.45, 0.95), (1.65, -6.15, 1.10), (2.35, -5.95, 0.95),
    ]
    for idx, (fx, fy, fscale) in enumerate(fern_spots):
        fz = ground_height(fx, fy)
        add_fern_plant(bm_ferns, Vector((fx, fy, fz)), scale=fscale, seed=3000 + idx)

    mesh_ferns = bpy.data.meshes.new("Paprocie_Kepy")
    bm_ferns.to_mesh(mesh_ferns)
    bm_ferns.free()
    obj_ferns = bpy.data.objects.new("Paprocie_Kepy", mesh_ferns)
    obj_ferns.data.materials.append(mats["fern"])
    set_smooth(obj_ferns)
    link_obj(obj_ferns, col_veg)

    # 2. Rich Grass Clumps & Wild Plants across the yard (avoiding cabin interior & deep puddle centers)
    tuft_count = 0
    for i in range(420):
        gx = rng.uniform(-5.8, 5.8)
        gy = rng.uniform(-7.8, 3.8)
        # Skip inside cabin footprint
        if -2.55 < gx < 2.55 and -1.35 < gy < 2.75:
            continue
        # Skip deep puddle water so reflections stay clean
        pf = puddle_factor(gx, gy)
        if pf > 0.18:
            continue
        gz = ground_height(gx, gy)
        if gz < WATER_LEVEL + 0.004:
            continue

        # Taller lush grass near puddle shores & cabin walls
        near_wall = (-2.9 < gx < 2.9 and -2.1 < gy < -1.2)
        near_puddle = (0.01 < pf <= 0.18)
        g_scale = rng.uniform(0.95, 1.45) if (near_wall or near_puddle) else rng.uniform(0.65, 1.15)
        tuft_count += 1
        add_grass_tuft(bm_grass, Vector((gx, gy, gz - 0.01)), scale=g_scale, seed=5000 + i)

    mesh_grass = bpy.data.meshes.new("Trawa_I_Roslinki")
    bm_grass.to_mesh(mesh_grass)
    bm_grass.free()
    obj_grass = bpy.data.objects.new("Trawa_I_Roslinki", mesh_grass)
    obj_grass.data.materials.append(mats["grass"])
    set_smooth(obj_grass)
    link_obj(obj_grass, col_veg)

    # 3. Scattered Mossy Stones around puddles & yard
    yard_stones = [
        (-1.45, -3.75, (0.22, 0.18, 0.12)),
        (0.72, -3.52, (0.18, 0.15, 0.10)),
        (-0.85, -4.95, (0.25, 0.19, 0.13)),
        (2.45, -2.85, (0.20, 0.16, 0.11)),
        (-2.65, -2.15, (0.28, 0.22, 0.15)),
        (1.15, -5.35, (0.19, 0.15, 0.10)),
    ]
    for s_i, (sx, sy, s_scale) in enumerate(yard_stones):
        sz = ground_height(sx, sy)
        st = make_deformed_stone(f"Kamien_Podworze_{s_i:02d}", Vector((sx, sy, sz + 0.04)), s_scale, seed=8000 + s_i)
        link_obj(st, col_env)

build_vegetation_and_stones()

# ==============================================================================
# 6. LIGHTING, SKY ATMOSPHERE, EEVEE RAYTRACING & CAMERA
# ==============================================================================
def setup_lighting_and_camera():
    # World Shader: Golden Post-Rain Sky (Nishita Sky + Warm Horizon)
    world = bpy.data.worlds.new("Swiat_Niebo_Po_Deszczu")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    safe_set_input(bg, "Strength", 1.15)
    links.new(bg.outputs["Background"], out.inputs["Surface"])

    sky = nodes.new("ShaderNodeTexSky")
    if hasattr(sky, "sky_type"):
        sky.sky_type = 'MULTIPLE_SCATTERING'
    if hasattr(sky, "sun_elevation"):
        sky.sun_elevation = math.radians(18.5)
    if hasattr(sky, "sun_rotation"):
        sky.sun_rotation = math.radians(42.0)
    if hasattr(sky, "air_density"):
        sky.air_density = 1.3
    if hasattr(sky, "dust_density"):
        sky.dust_density = 1.8
    links.new(sky.outputs["Color"], bg.inputs["Color"])

    # Key Sun Light (Low Golden Sun casting warm light across cabin, shutters & cart)
    sun_data = bpy.data.lights.new("Slonce_Glowne", type='SUN')
    sun_data.energy = 4.2
    sun_data.color = (1.0, 0.86, 0.68)
    sun_data.angle = math.radians(1.8)
    sun_obj = bpy.data.objects.new("Slonce_Glowne", sun_data)
    sun_obj.location = (-6.0, -7.0, 8.0)
    sun_obj.rotation_euler = (math.radians(66.0), math.radians(12.0), math.radians(-38.0))
    link_obj(sun_obj, col_env)

    # Sky Fill Area Light from behind camera to illuminate detailed window beams & shutters
    fill_data = bpy.data.lights.new("Swiatlo_Dopelniajace_Niebo", type='AREA')
    fill_data.energy = 180.0
    fill_data.color = (0.76, 0.86, 1.0)
    fill_data.size = 6.0
    fill_obj = bpy.data.objects.new("Swiatlo_Dopelniajace_Niebo", fill_data)
    fill_obj.location = (-2.5, -6.5, 4.5)
    fill_obj.rotation_euler = (math.radians(55.0), 0.0, math.radians(-18.0))
    link_obj(fill_obj, col_env)

    # Subtle warm interior glow inside cabin so windows have depth
    int_data = bpy.data.lights.new("Swiatlo_Wnetrze_Chaty", type='POINT')
    int_data.energy = 35.0
    int_data.color = (1.0, 0.62, 0.28)
    int_data.shadow_soft_size = 0.6
    int_obj = bpy.data.objects.new("Swiatlo_Wnetrze_Chaty", int_data)
    int_obj.location = (-0.2, 0.6, 1.45)
    link_obj(int_obj, col_env)

    # Camera framing cabin, windows/shutters, wooden cart, ferns, and foreground puddles
    cam_data = bpy.data.cameras.new("Kamera_Glowna")
    cam_data.lens = 32.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 200.0
    cam_obj = bpy.data.objects.new("Kamera_Glowna", cam_data)
    cam_obj.location = Vector((-1.85, -7.65, 1.42))
    target = Vector((0.35, -0.85, 1.32))
    direction = target - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    link_obj(cam_obj, col_env)
    scene.camera = cam_obj

    # Configure Render & EEVEE Raytracing for realistic puddle reflections
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100

    eevee = scene.eevee
    if hasattr(eevee, "use_raytracing"):
        eevee.use_raytracing = True
    if hasattr(eevee, "use_shadows"):
        eevee.use_shadows = True
    if hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = 64

    # Frame 3D Viewports to Camera or perspective view with Material Preview
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
                        space.shading.use_scene_lights_render = True
                        space.shading.use_scene_world_render = True
                        if space.region_3d is not None:
                            space.region_3d.view_perspective = 'CAMERA'

setup_lighting_and_camera()

# Render preview so we can inspect the visual result
preview_path = r"C:\Users\Przemke\.gemini\antigravity\brain\0cf18e8a-e024-4b6e-83b7-e73c5ff60dab\cabin_scene_preview.png"
scene.render.filepath = preview_path
bpy.ops.render.render(write_still=True)

result = {
    "scene": scene.name,
    "objects_count": len(bpy.data.objects),
    "collections": [c.name for c in bpy.data.collections],
    "preview_path": preview_path,
}
