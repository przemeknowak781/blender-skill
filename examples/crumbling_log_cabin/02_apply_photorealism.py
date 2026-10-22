import bpy
import bmesh
import math
import pathlib
import random
import addon_utils
from mathutils import Vector, Euler

random.seed(108)
scene = bpy.context.scene
ASSETS_DIR = pathlib.Path(r"c:\Users\Przemke\apps\aplikacja antigravity\assets")

col_env = bpy.data.collections.get("01_Srodowisko_Teren_Woda")
col_cabin = bpy.data.collections.get("02_Chata_Z_Bali")
col_cart = bpy.data.collections.get("03_Woz_Drewniany")
col_veg = bpy.data.collections.get("04_Roslinnosc_Paprocie_Trawa")

def link_obj(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)

# ==============================================================================
# 1. GENERATE CLEAN BOX-MAPPED UVs ON ALL CUSTOM MESHES
# ==============================================================================
def apply_box_uvs(obj, uv_scale=1.0):
    if obj is None or obj.type != 'MESH':
        return
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.verify()
    for face in bm.faces:
        n = face.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for loop in face.loops:
            co = loop.vert.co
            if ax >= ay and ax >= az:
                u, v = co.y * uv_scale, co.z * uv_scale
            elif ay >= ax and ay >= az:
                u, v = co.x * uv_scale, co.z * uv_scale
            else:
                u, v = co.x * uv_scale, co.y * uv_scale
            loop[uv_layer].uv = (u, v)
    bm.to_mesh(mesh)
    bm.free()

apply_box_uvs(bpy.data.objects.get("Teren_Ziemia"), uv_scale=0.45)
apply_box_uvs(bpy.data.objects.get("Sciany_Bale"), uv_scale=0.85)
apply_box_uvs(bpy.data.objects.get("Dach_Gont_Drewniany"), uv_scale=0.95)
apply_box_uvs(bpy.data.objects.get("Wiezba_Dachowa_Krokwie_Laty"), uv_scale=0.85)
apply_box_uvs(bpy.data.objects.get("Drzwi_I_Ganek"), uv_scale=0.90)
apply_box_uvs(bpy.data.objects.get("Stary_Plot_Drewniany"), uv_scale=0.85)
apply_box_uvs(bpy.data.objects.get("Woz_Drewniany_Konstrukcja"), uv_scale=1.10)
apply_box_uvs(bpy.data.objects.get("Woda_Kaluze"), uv_scale=0.50)

for obj in bpy.data.objects:
    if obj.name.startswith("Okno_"):
        apply_box_uvs(obj, uv_scale=1.15)

# ==============================================================================
# 2. BUILD SCANNED PBR MATERIALS (Poly Haven Textures + Normal Maps)
# ==============================================================================
def load_image(path_obj, non_color=False):
    img = bpy.data.images.load(str(path_obj), check_existing=True)
    if non_color:
        img.colorspace_settings.name = 'Non-Color'
    else:
        img.colorspace_settings.name = 'sRGB'
    return img

def find_tex_file(tex_id, suffix):
    folder = ASSETS_DIR / "textures" / tex_id
    for ext in ("jpg", "png", "exr"):
        p = folder / f"{tex_id}_{suffix}.{ext}"
        if p.exists():
            return p
    return None

def build_pbr_wood_or_plank_mat(mat_name, tex_id, uv_scale=(1.0, 1.0, 1.0), color_mult=1.0, normal_strength=1.2, add_moss=False):
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = uv_scale
    links.new(tc.outputs["UV"], mapping.inputs["Vector"])

    diff_path = find_tex_file(tex_id, "Diffuse")
    rough_path = find_tex_file(tex_id, "Rough")
    nor_path = find_tex_file(tex_id, "nor_gl")

    if diff_path:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = load_image(diff_path, non_color=False)
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])

        if color_mult != 1.0 or add_moss:
            hsv = nodes.new("ShaderNodeHueSaturation")
            hsv.inputs["Value"].default_value = color_mult
            hsv.inputs["Saturation"].default_value = 1.05
            links.new(tex_d.outputs["Color"], hsv.inputs["Color"])
            links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            links.new(tex_d.outputs["Color"], bsdf.inputs["Base Color"])

    if rough_path:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = load_image(rough_path, non_color=True)
        links.new(mapping.outputs["Vector"], tex_r.inputs["Vector"])
        links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])

    if nor_path:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = load_image(nor_path, non_color=True)
        links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nor_map = nodes.new("ShaderNodeNormalMap")
        nor_map.inputs["Strength"].default_value = normal_strength
        links.new(tex_n.outputs["Color"], nor_map.inputs["Color"])
        links.new(nor_map.outputs["Normal"], bsdf.inputs["Normal"])

    return mat

# 2.1 Cabin Logs: Scanned Bark/Wood (bark_brown_02)
build_pbr_wood_or_plank_mat("Mat_Bale_Drewno", "bark_brown_02", uv_scale=(1.2, 1.2, 1.2), color_mult=0.78, normal_strength=1.35)

# 2.2 Shingles (Gont): Scanned Weathered Wood Planks (brown_planks_03)
build_pbr_wood_or_plank_mat("Mat_Gont_Drewniany", "brown_planks_03", uv_scale=(1.6, 1.6, 1.6), color_mult=0.68, normal_strength=1.30)

# 2.3 Window Beams & Door: Scanned Dark Wooden Planks (dark_wooden_planks)
build_pbr_wood_or_plank_mat("Mat_Belki_Okienne", "dark_wooden_planks", uv_scale=(1.1, 1.1, 1.1), color_mult=0.82, normal_strength=1.20)

# 2.4 Wooden Cart: Scanned Dark Wooden Planks (brown_planks_03)
build_pbr_wood_or_plank_mat("Mat_Drewno_Wozu", "brown_planks_03", uv_scale=(1.3, 1.3, 1.3), color_mult=0.80, normal_strength=1.25)

# 2.5 Shutters (Okiennice): Scanned Peeling Blue Painted Planks (blue_painted_planks)
build_pbr_wood_or_plank_mat("Mat_Okiennice", "blue_painted_planks", uv_scale=(1.2, 1.2, 1.2), color_mult=0.85, normal_strength=1.25)

# 2.6 Muddy Ground with Wet Puddle Banks: Scanned brown_mud_leaves_01
def build_mud_ground_pbr():
    mat = bpy.data.materials.get("Mat_Ziemia_Bloto") or bpy.data.materials.new("Mat_Ziemia_Bloto")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    tc = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.4, 1.4, 1.4)
    links.new(tc.outputs["UV"], mapping.inputs["Vector"])

    diff_p = find_tex_file("brown_mud_leaves_01", "Diffuse")
    rough_p = find_tex_file("brown_mud_leaves_01", "Rough")
    nor_p = find_tex_file("brown_mud_leaves_01", "nor_gl")

    geom = nodes.new("ShaderNodeNewGeometry")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geom.outputs["Position"], sep.inputs["Vector"])

    # Wetness factor near Z <= 0.035 (puddle banks & wheel ruts)
    ramp_wet = nodes.new("ShaderNodeValToRGB")
    ramp_wet.color_ramp.elements[0].position = 0.005
    ramp_wet.color_ramp.elements[0].color = (0.38, 0.38, 0.38, 1.0) # dark wet mud near water
    ramp_wet.color_ramp.elements[1].position = 0.055
    ramp_wet.color_ramp.elements[1].color = (0.85, 0.85, 0.85, 1.0) # normal soil above
    links.new(sep.outputs["Z"], ramp_wet.inputs["Fac"])

    if diff_p:
        tex_d = nodes.new("ShaderNodeTexImage")
        tex_d.image = load_image(diff_p, non_color=False)
        links.new(mapping.outputs["Vector"], tex_d.inputs["Vector"])

        hsv = nodes.new("ShaderNodeHueSaturation")
        links.new(ramp_wet.outputs["Color"], hsv.inputs["Value"])
        links.new(tex_d.outputs["Color"], hsv.inputs["Color"])
        links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])

    if rough_p:
        tex_r = nodes.new("ShaderNodeTexImage")
        tex_r.image = load_image(rough_p, non_color=True)
        links.new(mapping.outputs["Vector"], tex_r.inputs["Vector"])

        # Multiply roughness by wet ramp so puddle edges are glossy wet mud
        math_r = nodes.new("ShaderNodeMath")
        math_r.operation = 'MULTIPLY'
        links.new(tex_r.outputs["Color"], math_r.inputs[0])
        links.new(ramp_wet.outputs["Color"], math_r.inputs[1])
        links.new(math_r.outputs["Value"], bsdf.inputs["Roughness"])

    if nor_p:
        tex_n = nodes.new("ShaderNodeTexImage")
        tex_n.image = load_image(nor_p, non_color=True)
        links.new(mapping.outputs["Vector"], tex_n.inputs["Vector"])
        nor_map = nodes.new("ShaderNodeNormalMap")
        nor_map.inputs["Strength"].default_value = 1.35
        links.new(tex_n.outputs["Color"], nor_map.inputs["Color"])
        links.new(nor_map.outputs["Normal"], bsdf.inputs["Normal"])

build_mud_ground_pbr()

# ==============================================================================
# 3. IMPORT & SCATTER PHOTOGRAMMETRY 3D MODELS FROM POLY HAVEN
# ==============================================================================
# Remove old synthetic vegetation & yard stones so we replace them with real photogrammetry models
for old_name in ["Paprocie_Kepy", "Trawa_I_Roslinki"]:
    old_obj = bpy.data.objects.get(old_name)
    if old_obj:
        bpy.data.objects.remove(old_obj, do_unlink=True)
for obj in list(bpy.data.objects):
    if obj.name.startswith("Kamien_Podworze_") or obj.name.startswith("PH_"):
        bpy.data.objects.remove(obj, do_unlink=True)

# Create a hidden template collection for loaded source assets
col_templates = bpy.data.collections.get("00_PolyHaven_Templates")
if col_templates:
    for o in list(col_templates.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    col_templates = bpy.data.collections.new("00_PolyHaven_Templates")
    scene.collection.children.link(col_templates)
col_templates.hide_viewport = True
col_templates.hide_render = True

def append_model_objects(mod_id, obj_names):
    blend_path = str(ASSETS_DIR / "models" / mod_id / f"{mod_id}.blend")
    loaded = []
    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        avail = set(data_from.objects)
        to_load = [n for n in obj_names if n in avail]
        data_to.objects = to_load
    for obj in data_to.objects:
        if obj is not None:
            col_templates.objects.link(obj)
            loaded.append(obj)
    return loaded

ferns_src = append_model_objects("fern_02", ["fern_02_a", "fern_02_b", "fern_02_c", "fern_02_d"])
grass_src = append_model_objects("grass_medium_01", [
    "grass_medium_01_large_a_LOD0",
    "grass_medium_01_large_b_LOD0",
    "grass_medium_01_large_c_LOD0",
    "grass_medium_01_mid_a_LOD0",
    "grass_medium_01_mid_b_LOD0",
    "grass_medium_01_tall_a_LOD0",
    "grass_medium_01_tall_b_LOD0",
])
weeds_src = append_model_objects("weed_plant_02", [
    "weed_plant_02_a_LOD0",
    "weed_plant_02_b_LOD0",
    "weed_plant_02_c_LOD0",
])
nettles_src = append_model_objects("nettle_plant", [
    "nettle_plant_tall_a_LOD0",
    "nettle_plant_medium_a_LOD0",
    "nettle_plant_small_a_LOD0",
])
rocks_src = append_model_objects("rock_moss_set_01", [
    "rock_moss_set_01_rock01",
    "rock_moss_set_01_rock02",
    "rock_moss_set_01_rock03",
    "rock_moss_set_01_rock04",
    "rock_moss_set_01_rock05",
    "rock_moss_set_01_rock06",
])
stump_src = append_model_objects("tree_stump_01", ["tree_stump_01"])
pines_src = append_model_objects("pine_sapling_medium", [
    "pine_sapling_medium_a_LOD1",
    "pine_sapling_medium_b_LOD1",
    "pine_sapling_medium_c_LOD1",
])

# Helper to query exact terrain height from Teren_Ziemia via ray_cast
terrain_obj = bpy.data.objects.get("Teren_Ziemia")

PUDDLES = [
    (-0.15, -4.45, 1.65, 1.05, 0.15, 0.11),
    (-2.25, -5.35, 1.15, 0.72, -0.22, 0.09),
    (1.95, -5.25, 1.10, 0.70, 0.28, 0.09),
    (1.05, -2.55, 0.85, 0.55, -0.12, 0.08),
]

def puddle_factor(x, y):
    best = 0.0
    for cx, cy, rx, ry, ang, depth in PUDDLES:
        dx, dy = x - cx, y - cy
        ca, sa = math.cos(-ang), math.sin(-ang)
        lx = (dx * ca - dy * sa) / rx
        ly = (dx * sa + dy * ca) / ry
        r2 = lx * lx + ly * ly
        shore_warp = 0.14 * math.sin(x * 4.1 + y * 3.3) + 0.09 * math.cos(x * 6.7 - y * 5.9)
        r_eff = r2 + shore_warp * 0.22
        if r_eff < 1.0:
            val = (1.0 - r_eff) ** 1.5
            if val > best:
                best = val
    return best

def sample_z(x, y):
    if terrain_obj:
        hit, loc, norm, idx = terrain_obj.ray_cast(Vector((x, y, 10.0)), Vector((0.0, 0.0, -1.0)))
        if hit:
            return loc.z
    return 0.05

def place_instance(src_obj, name, loc, scale_xyz, rot_euler, target_col):
    inst = src_obj.copy()
    inst.name = name
    inst.location = loc
    inst.scale = scale_xyz
    inst.rotation_euler = rot_euler
    target_col.objects.link(inst)
    return inst

# 3.1 Scatter 48 Photogrammetry Ferns (fern_02)
fern_coords = [
    # Along cabin front wall & windows
    (-2.35, -1.52, 1.25), (-1.95, -1.62, 1.10), (-1.50, -1.58, 1.20), (-1.05, -1.60, 0.98),
    (-0.72, -1.95, 1.15), (-0.58, -1.58, 1.05),
    (0.65, -1.92, 1.20), (0.98, -1.62, 1.08), (1.42, -1.65, 1.30), (1.88, -1.60, 1.15), (2.30, -1.55, 1.22),
    # Around fallen logs & right corner
    (2.75, -1.35, 1.35), (3.05, -0.65, 1.20), (2.55, -2.35, 1.05), (3.25, -1.85, 1.15),
    # Around puddles & foreground banks
    (-1.72, -3.55, 1.18), (-1.25, -3.22, 1.00), (-2.15, -4.18, 1.25), (-2.65, -4.55, 1.10),
    (0.78, -4.82, 1.05), (0.48, -3.18, 0.98), (-0.95, -5.25, 1.12), (-1.55, -5.65, 1.05),
    # Near wooden cart wheels & fence
    (2.65, -3.85, 1.18), (2.35, -4.35, 0.98), (0.85, -2.75, 0.95), (2.95, -3.15, 1.12),
    (-2.90, -0.85, 1.25), (-2.85, 0.15, 1.15), (-2.95, 1.20, 1.30), (-3.45, -1.95, 1.20),
    # Foreground left & right framing
    (-3.15, -5.75, 1.25), (-2.55, -6.15, 1.05), (1.48, -6.05, 1.15), (2.18, -5.85, 1.02),
    (-0.25, -6.10, 0.95), (0.35, -5.95, 1.05), (-1.85, -2.55, 1.10), (1.75, -2.25, 1.08),
]
if ferns_src:
    for i, (fx, fy, fsc) in enumerate(fern_coords):
        src = ferns_src[i % len(ferns_src)]
        fz = sample_z(fx, fy)
        s_val = fsc * random.uniform(0.92, 1.15)
        place_instance(
            src,
            f"PH_Paproc_{i:02d}",
            Vector((fx, fy, fz - 0.01)),
            (s_val, s_val, s_val),
            (random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08), random.uniform(0.0, math.pi * 2.0)),
            col_veg,
        )

# 3.2 Scatter 55 Wild Plants & Nettles (weed_plant_02 & nettle_plant)
wild_plants_src = weeds_src + nettles_src
if wild_plants_src:
    for i in range(60):
        wx = random.uniform(-5.2, 5.2)
        wy = random.uniform(-7.0, 2.5)
        if -2.65 < wx < 2.65 and -1.45 < wy < 2.80:
            continue
        if puddle_factor(wx, wy) > 0.08:
            continue
        wz = sample_z(wx, wy)
        if wz < 0.005:
            continue
        src = wild_plants_src[i % len(wild_plants_src)]
        sc = random.uniform(0.85, 1.45)
        place_instance(
            src,
            f"PH_Roslinka_{i:02d}",
            Vector((wx, wy, wz - 0.01)),
            (sc, sc, sc),
            (random.uniform(-0.06, 0.06), random.uniform(-0.06, 0.06), random.uniform(0.0, math.pi * 2.0)),
            col_veg,
        )

# 3.3 Scatter 340 Real PBR Grass Clumps (grass_medium_01)
if grass_src:
    for i in range(340):
        gx = random.uniform(-6.2, 6.2)
        gy = random.uniform(-7.8, 3.5)
        if -2.60 < gx < 2.60 and -1.38 < gy < 2.75:
            continue
        pf = puddle_factor(gx, gy)
        if pf > 0.10:
            continue
        gz = sample_z(gx, gy)
        if gz < 0.004:
            continue
        src = grass_src[i % len(grass_src)]
        sc = random.uniform(1.1, 1.85)
        place_instance(
            src,
            f"PH_Trawa_{i:03d}",
            Vector((gx, gy, gz - 0.015)),
            (sc, sc, sc * random.uniform(0.9, 1.25)),
            (random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08), random.uniform(0.0, math.pi * 2.0)),
            col_veg,
        )

# 3.4 Place Photogrammetry Mossy Rocks (rock_moss_set_01) & Tree Stumps (tree_stump_01)
rock_spots = [
    (-1.45, -3.75, 1.15), (0.72, -3.52, 0.95), (-0.85, -4.95, 1.25),
    (2.45, -2.85, 1.10), (-2.65, -2.15, 1.35), (1.15, -5.35, 1.00),
    (-1.95, -4.85, 0.90), (0.25, -3.45, 0.85), (1.85, -4.55, 1.10),
    (-2.55, -1.42, 1.30), (2.55, -1.42, 1.35), (-0.62, -2.15, 0.95), (0.65, -2.15, 1.00),
]
if rocks_src:
    for i, (rx, ry, rsc) in enumerate(rock_spots):
        src = rocks_src[i % len(rocks_src)]
        rz = sample_z(rx, ry)
        place_instance(
            src,
            f"PH_Kamien_Omszaly_{i:02d}",
            Vector((rx, ry, rz - 0.02)),
            (rsc, rsc, rsc),
            (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(0.0, math.pi * 2.0)),
            col_env,
        )

if stump_src:
    for i, (sx, sy, ssc) in enumerate([(-3.05, -3.35, 0.95), (3.45, -2.35, 1.05)]):
        sz = sample_z(sx, sy)
        place_instance(
            stump_src[0],
            f"PH_Pniak_{i:02d}",
            Vector((sx, sy, sz - 0.02)),
            (ssc, ssc, ssc),
            (0.0, 0.0, random.uniform(0.0, math.pi * 2.0)),
            col_env,
        )

# 3.5 Place Real 3D Pine Trees in Background Forest Edge (pine_sapling_medium)
pine_spots = [
    (-6.2, 3.2, 2.2), (-4.6, 4.5, 2.6), (-2.8, 5.2, 2.8), (-0.8, 5.6, 2.5),
    (1.2, 5.5, 2.7), (3.2, 4.8, 2.4), (4.8, 4.0, 2.6), (6.2, 2.8, 2.1),
    (-5.5, 0.5, 1.8), (5.4, 0.6, 1.9), (-4.2, 3.5, 1.6), (4.0, 3.4, 1.7),
]
if pines_src:
    for i, (px, py, psc) in enumerate(pine_spots):
        src = pines_src[i % len(pines_src)]
        pz = sample_z(px, py)
        place_instance(
            src,
            f"PH_Sosna_Tlo_{i:02d}",
            Vector((px, py, pz - 0.05)),
            (psc, psc, psc * random.uniform(0.95, 1.12)),
            (random.uniform(-0.04, 0.04), random.uniform(-0.04, 0.04), random.uniform(0.0, math.pi * 2.0)),
            col_veg,
        )

# ==============================================================================
# 4. REAL 2K HDRI SKY & CYCLES GPU RENDERING
# ==============================================================================
hdri_path = ASSETS_DIR / "hdri" / "kloofendal_28d_misty_puresky_2k.hdr"
if not hdri_path.exists():
    hdri_path = ASSETS_DIR / "hdri" / "autumn_field_puresky_2k.hdr"

world = bpy.data.worlds.get("Swiat_Niebo_Po_Deszczu") or bpy.data.worlds.new("Swiat_Niebo_Po_Deszczu")
scene.world = world
world.use_nodes = True
nt = world.node_tree
nodes, links = nt.nodes, nt.links
nodes.clear()

out = nodes.new("ShaderNodeOutputWorld")
bg = nodes.new("ShaderNodeBackground")
bg.inputs["Strength"].default_value = 1.05
links.new(bg.outputs["Background"], out.inputs["Surface"])

tc = nodes.new("ShaderNodeTexCoord")
mapping = nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(-115.0))
links.new(tc.outputs["Generated"], mapping.inputs["Vector"])

env_tex = nodes.new("ShaderNodeTexEnvironment")
env_tex.image = bpy.data.images.load(str(hdri_path), check_existing=True)
links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])
links.new(env_tex.outputs["Color"], bg.inputs["Color"])

# Tune Sun Light & Interior Warm Glow to harmonize with the HDRI
sun_obj = bpy.data.objects.get("Slonce_Glowne")
if sun_obj and sun_obj.data:
    sun_obj.data.energy = 2.2
    sun_obj.data.color = (1.0, 0.85, 0.66)
    sun_obj.data.angle = math.radians(2.2)

fill_obj = bpy.data.objects.get("Swiatlo_Dopelniajace_Niebo")
if fill_obj and fill_obj.data:
    fill_obj.data.energy = 35.0

int_obj = bpy.data.objects.get("Swiatlo_Wnetrze_Chaty")
if int_obj and int_obj.data:
    int_obj.data.energy = 85.0
    int_obj.data.color = (1.0, 0.52, 0.16)

# Enable Cycles GPU Path-Tracing for Photorealistic Reflections, GI & Foliage Translucency
addon_utils.enable("cycles")
scene.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
for dev_type in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
    try:
        prefs.compute_device_type = dev_type
        prefs.get_devices()
        gpu_devs = [d for d in prefs.devices if d.type != 'CPU']
        if gpu_devs:
            for d in prefs.devices:
                d.use = True
            scene.cycles.device = 'GPU'
            break
    except Exception:
        pass

scene.cycles.samples = 64
if hasattr(scene.cycles, "use_denoising"):
    scene.cycles.use_denoising = True
if hasattr(scene.cycles, "use_adaptive_sampling"):
    scene.cycles.use_adaptive_sampling = True

scene.render.resolution_x = 1440
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100

preview_path = r"C:\Users\Przemke\.gemini\antigravity\brain\0cf18e8a-e024-4b6e-83b7-e73c5ff60dab\cabin_scene_pbr_preview.png"
scene.render.filepath = preview_path
bpy.ops.render.render(write_still=True)

result = {
    "status": "pbr_rendered",
    "engine": scene.render.engine,
    "device": scene.cycles.device,
    "objects_count": len(bpy.data.objects),
    "preview_path": preview_path,
}
