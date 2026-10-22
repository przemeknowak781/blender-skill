import bpy
import bmesh
import math
import pathlib
from mathutils import Vector, Euler

ASSETS_DIR = pathlib.Path(r"c:\Users\Przemke\apps\aplikacja antigravity\assets")
scene = bpy.context.scene

# ==============================================================================
# 1. MOODY OVERCAST & GOLDEN-MIST WORLD SHADER (Soft Diffused Sky & Clouds)
# ==============================================================================
hdri_misty_path = ASSETS_DIR / "hdri" / "kloofendal_28d_misty_puresky_2k.hdr"
hdri_eve_path = ASSETS_DIR / "hdri" / "evening_road_01_puresky_2k.hdr"
img_misty = bpy.data.images.load(str(hdri_misty_path), check_existing=True)
img_eve = bpy.data.images.load(str(hdri_eve_path), check_existing=True)

world = scene.world
world.use_nodes = True
nt = world.node_tree
nodes, links = nt.nodes, nt.links
nodes.clear()

out = nodes.new("ShaderNodeOutputWorld")
bg = nodes.new("ShaderNodeBackground")
bg.inputs["Strength"].default_value = 0.48  # Subdued, moody dusk/overcast ambient intensity
links.new(bg.outputs["Background"], out.inputs["Surface"])

tc = nodes.new("ShaderNodeTexCoord")

map_hdri = nodes.new("ShaderNodeMapping")
map_hdri.inputs["Rotation"].default_value = (math.radians(4.0), 0.0, math.radians(-115.0))
links.new(tc.outputs["Generated"], map_hdri.inputs["Vector"])

env_misty = nodes.new("ShaderNodeTexEnvironment")
env_misty.image = img_misty
links.new(map_hdri.outputs["Vector"], env_misty.inputs["Vector"])

env_eve = nodes.new("ShaderNodeTexEnvironment")
env_eve.image = img_eve
links.new(map_hdri.outputs["Vector"], env_eve.inputs["Vector"])

mix_hdri = nodes.new("ShaderNodeMix")
mix_hdri.data_type = 'RGBA'
mix_hdri.inputs[0].default_value = 0.55
links.new(env_misty.outputs["Color"], mix_hdri.inputs[6])
links.new(env_eve.outputs["Color"], mix_hdri.inputs[7])

hsv_hdri = nodes.new("ShaderNodeHueSaturation")
hsv_hdri.inputs["Saturation"].default_value = 0.52
hsv_hdri.inputs["Value"].default_value = 0.55
links.new(mix_hdri.outputs[2], hsv_hdri.inputs["Color"])

# Perspective Cloud Dome Projection from Generated ray vector (dx, dy, dz)
sep_ray = nodes.new("ShaderNodeSeparateXYZ")
links.new(tc.outputs["Generated"], sep_ray.inputs["Vector"])

math_dz_add = nodes.new("ShaderNodeMath")
math_dz_add.operation = 'ADD'
links.new(sep_ray.outputs["Z"], math_dz_add.inputs[0])
math_dz_add.inputs[1].default_value = 0.05

math_dz_max = nodes.new("ShaderNodeMath")
math_dz_max.operation = 'MAXIMUM'
links.new(math_dz_add.outputs["Value"], math_dz_max.inputs[0])
math_dz_max.inputs[1].default_value = 0.065

math_u = nodes.new("ShaderNodeMath")
math_u.operation = 'DIVIDE'
links.new(sep_ray.outputs["X"], math_u.inputs[0])
links.new(math_dz_max.outputs["Value"], math_u.inputs[1])

math_v = nodes.new("ShaderNodeMath")
math_v.operation = 'DIVIDE'
links.new(sep_ray.outputs["Y"], math_v.inputs[0])
links.new(math_dz_max.outputs["Value"], math_v.inputs[1])

comb_cloud = nodes.new("ShaderNodeCombineXYZ")
links.new(math_u.outputs["Value"], comb_cloud.inputs["X"])
links.new(math_v.outputs["Value"], comb_cloud.inputs["Y"])
comb_cloud.inputs["Z"].default_value = 0.0

noise_c1 = nodes.new("ShaderNodeTexNoise")
noise_c1.inputs["Scale"].default_value = 0.48
noise_c1.inputs["Detail"].default_value = 8.0
noise_c1.inputs["Roughness"].default_value = 0.52
noise_c1.inputs["Distortion"].default_value = 0.30
links.new(comb_cloud.outputs["Vector"], noise_c1.inputs["Vector"])

map_c2 = nodes.new("ShaderNodeMapping")
map_c2.inputs["Location"].default_value = (0.22, -0.15, 0.0)
links.new(comb_cloud.outputs["Vector"], map_c2.inputs["Vector"])

noise_c2 = nodes.new("ShaderNodeTexNoise")
noise_c2.inputs["Scale"].default_value = 0.95
noise_c2.inputs["Detail"].default_value = 8.0
noise_c2.inputs["Roughness"].default_value = 0.50
links.new(map_c2.outputs["Vector"], noise_c2.inputs["Vector"])

ramp_density = nodes.new("ShaderNodeValToRGB")
ramp_density.color_ramp.elements[0].position = 0.32
ramp_density.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
ramp_density.color_ramp.elements[1].position = 0.72
ramp_density.color_ramp.elements[1].color = (0.92, 0.92, 0.92, 1.0)
links.new(noise_c1.outputs["Fac"], ramp_density.inputs["Fac"])

ramp_cloud_col = nodes.new("ShaderNodeValToRGB")
ramp_cloud_col.color_ramp.elements[0].position = 0.30
ramp_cloud_col.color_ramp.elements[0].color = (0.16, 0.20, 0.27, 1.0)
e_mid = ramp_cloud_col.color_ramp.elements.new(0.54)
e_mid.color = (0.38, 0.41, 0.46, 1.0)
ramp_cloud_col.color_ramp.elements[1].position = 0.78
ramp_cloud_col.color_ramp.elements[1].color = (0.82, 0.68, 0.54, 1.0)
links.new(noise_c2.outputs["Fac"], ramp_cloud_col.inputs["Fac"])

mix_sky_clouds = nodes.new("ShaderNodeMix")
mix_sky_clouds.data_type = 'RGBA'
links.new(ramp_density.outputs["Color"], mix_sky_clouds.inputs[0])
links.new(hsv_hdri.outputs["Color"], mix_sky_clouds.inputs[6])
links.new(ramp_cloud_col.outputs["Color"], mix_sky_clouds.inputs[7])

ramp_mist_band = nodes.new("ShaderNodeValToRGB")
ramp_mist_band.color_ramp.elements[0].position = 0.00
ramp_mist_band.color_ramp.elements[0].color = (0.82, 0.82, 0.82, 1.0)
ramp_mist_band.color_ramp.elements[1].position = 0.19
ramp_mist_band.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
links.new(sep_ray.outputs["Z"], ramp_mist_band.inputs["Fac"])

mix_horizon_mist = nodes.new("ShaderNodeMix")
mix_horizon_mist.data_type = 'RGBA'
links.new(ramp_mist_band.outputs["Color"], mix_horizon_mist.inputs[0])
links.new(mix_sky_clouds.outputs[2], mix_horizon_mist.inputs[6])
mix_horizon_mist.inputs[7].default_value = (0.48, 0.42, 0.38, 1.0)
links.new(mix_horizon_mist.outputs[2], bg.inputs["Color"])


# ==============================================================================
# 2. DIFFUSED, MOODY LIGHTING SETUP (36° Soft Sun + Area Diffusers + Window Glow)
# ==============================================================================
col_lights = bpy.data.collections.get("05_Kamera_I_Oswietlenie") or scene.collection

for obj in list(bpy.data.objects):
    if obj.type == 'LIGHT' and obj.name not in ("Slonce_Glowne", "Swiatlo_Dopelniajace_Niebo", "Swiatlo_Wnetrze_Chaty"):
        bpy.data.objects.remove(obj, do_unlink=True)

sun_obj = bpy.data.objects.get("Slonce_Glowne")
if sun_obj and sun_obj.type == 'LIGHT':
    sun_obj.location = Vector((-7.5, -4.5, 6.5))
    sun_obj.rotation_euler = Euler((math.radians(70.0), math.radians(12.0), math.radians(-52.0)), 'XYZ')
    sun_obj.data.energy = 1.35
    sun_obj.data.color = (1.0, 0.68, 0.38)
    sun_obj.data.angle = math.radians(36.0)
    if hasattr(sun_obj.data, "specular_factor"):
        sun_obj.data.specular_factor = 0.28
    if hasattr(sun_obj.data, "volume_factor"):
        sun_obj.data.volume_factor = 1.5

fill_obj = bpy.data.objects.get("Swiatlo_Dopelniajace_Niebo")
if fill_obj and fill_obj.type == 'LIGHT':
    fill_obj.location = Vector((4.5, -6.5, 6.0))
    fill_obj.rotation_euler = Euler((math.radians(52.0), 0.0, math.radians(28.0)), 'XYZ')
    fill_obj.data.type = 'AREA'
    fill_obj.data.shape = 'DISK'
    fill_obj.data.size = 14.0
    fill_obj.data.energy = 32.0
    fill_obj.data.color = (0.42, 0.58, 0.86)
    if hasattr(fill_obj.data, "specular_factor"):
        fill_obj.data.specular_factor = 0.12
    if hasattr(fill_obj.data, "volume_factor"):
        fill_obj.data.volume_factor = 0.35

rim_data = bpy.data.lights.new(name="Swiatlo_Mgla_Tyl", type='AREA')
rim_data.shape = 'RECTANGLE'
rim_data.size = 14.0
rim_data.size_y = 6.0
rim_data.energy = 115.0
rim_data.color = (1.0, 0.64, 0.32)
if hasattr(rim_data, "specular_factor"):
    rim_data.specular_factor = 0.25
if hasattr(rim_data, "volume_factor"):
    rim_data.volume_factor = 1.8
rim_obj = bpy.data.objects.new(name="Swiatlo_Mgla_Tyl", object_data=rim_data)
rim_obj.location = Vector((0.8, 4.8, 4.2))
rim_obj.rotation_euler = Euler((math.radians(-112.0), 0.0, math.radians(8.0)), 'XYZ')
col_lights.objects.link(rim_obj)

int_obj = bpy.data.objects.get("Swiatlo_Wnetrze_Chaty")
if int_obj and int_obj.type == 'LIGHT':
    int_obj.location = Vector((0.8, 0.8, 2.35))
    int_obj.data.type = 'POINT'
    int_obj.data.energy = 65.0
    int_obj.data.color = (1.0, 0.50, 0.16)
    int_obj.data.shadow_soft_size = 1.25
    if hasattr(int_obj.data, "specular_factor"):
        int_obj.data.specular_factor = 0.10
    if hasattr(int_obj.data, "volume_factor"):
        int_obj.data.volume_factor = 1.8

for w_name, wx in [("Swiatlo_Okno_Lewe", -1.15), ("Swiatlo_Okno_Prawe", 1.35)]:
    w_data = bpy.data.lights.new(name=w_name, type='AREA')
    w_data.shape = 'RECTANGLE'
    w_data.size = 0.75
    w_data.size_y = 0.85
    w_data.energy = 24.0
    w_data.color = (1.0, 0.46, 0.12)
    if hasattr(w_data, "specular_factor"):
        w_data.specular_factor = 0.10
    if hasattr(w_data, "volume_factor"):
        w_data.volume_factor = 3.2
    w_obj = bpy.data.objects.new(name=w_name, object_data=w_data)
    w_obj.location = Vector((wx, -1.86, 1.38))
    w_obj.rotation_euler = Euler((math.radians(78.0), 0.0, 0.0), 'XYZ')
    col_lights.objects.link(w_obj)

cg_data = bpy.data.lights.new(name="Swiatlo_Blask_Woz", type='AREA')
cg_data.shape = 'DISK'
cg_data.size = 4.5
cg_data.energy = 22.0
cg_data.color = (1.0, 0.58, 0.24)
if hasattr(cg_data, "specular_factor"):
    cg_data.specular_factor = 0.22
if hasattr(cg_data, "volume_factor"):
    cg_data.volume_factor = 1.2
cg_obj = bpy.data.objects.new(name="Swiatlo_Blask_Woz", object_data=cg_data)
cg_obj.location = Vector((-1.2, -3.2, 2.2))
cg_obj.rotation_euler = Euler((math.radians(62.0), 0.0, math.radians(-38.0)), 'XYZ')
col_lights.objects.link(cg_obj)


# ==============================================================================
# 3. FROSTED / DUSTY WINDOW GLASS WITH WARM DIFFUSED LANTERN GLOW
# ==============================================================================
mat_glass = bpy.data.materials.get("Mat_Szklo_Okienne")
if mat_glass:
    mat_glass.use_nodes = True
    g_nt = mat_glass.node_tree
    g_nodes, g_links = g_nt.nodes, g_nt.links
    g_nodes.clear()

    g_out = g_nodes.new("ShaderNodeOutputMaterial")
    g_bsdf = g_nodes.new("ShaderNodeBsdfPrincipled")
    g_bsdf.inputs["Base Color"].default_value = (0.18, 0.14, 0.10, 1.0)
    g_bsdf.inputs["Roughness"].default_value = 0.42
    g_bsdf.inputs["Specular IOR Level"].default_value = 0.15
    g_bsdf.inputs["Transmission Weight"].default_value = 0.0
    g_bsdf.inputs["Emission Strength"].default_value = 2.4
    g_links.new(g_bsdf.outputs["BSDF"], g_out.inputs["Surface"])

    g_tc = g_nodes.new("ShaderNodeTexCoord")
    g_noise = g_nodes.new("ShaderNodeTexNoise")
    g_noise.inputs["Scale"].default_value = 4.5
    g_noise.inputs["Detail"].default_value = 6.0
    g_noise.inputs["Roughness"].default_value = 0.65
    g_links.new(g_tc.outputs["Object"], g_noise.inputs["Vector"])

    g_ramp = g_nodes.new("ShaderNodeValToRGB")
    g_ramp.color_ramp.elements[0].position = 0.28
    g_ramp.color_ramp.elements[0].color = (0.28, 0.11, 0.03, 1.0)
    e_gmid = g_ramp.color_ramp.elements.new(0.55)
    e_gmid.color = (0.85, 0.38, 0.10, 1.0)
    g_ramp.color_ramp.elements[1].position = 0.82
    g_ramp.color_ramp.elements[1].color = (1.0, 0.62, 0.22, 1.0)
    g_links.new(g_noise.outputs["Fac"], g_ramp.inputs["Fac"])
    g_links.new(g_ramp.outputs["Color"], g_bsdf.inputs["Emission Color"])


# ==============================================================================
# 4. 3D VOLUMETRIC MIST / GROUND HAZE (Height + Depth + 3D Noise Falloff)
# ==============================================================================
col_env = bpy.data.collections.get("01_Srodowisko_Teren_Woda") or scene.collection

for obj in list(bpy.data.objects):
    if obj.name.startswith("Mgla_Wolumetryczna"):
        bpy.data.objects.remove(obj, do_unlink=True)

bm_fog = bmesh.new()
bmesh.ops.create_cube(bm_fog, size=1.0)
fog_mesh = bpy.data.meshes.new("Mesh_Mgla_Wolumetryczna")
bm_fog.to_mesh(fog_mesh)
bm_fog.free()

fog_obj = bpy.data.objects.new("Mgla_Wolumetryczna", fog_mesh)
fog_obj.location = Vector((0.0, 2.2, 2.5))
fog_obj.scale = Vector((22.0, 16.5, 5.8))
col_env.objects.link(fog_obj)

mat_fog = bpy.data.materials.get("Mat_Mgla_Wolumetryczna") or bpy.data.materials.new("Mat_Mgla_Wolumetryczna")
mat_fog.use_nodes = True
f_nt = mat_fog.node_tree
f_nodes, f_links = f_nt.nodes, f_nt.links
f_nodes.clear()

f_out = f_nodes.new("ShaderNodeOutputMaterial")
f_vol = f_nodes.new("ShaderNodeVolumePrincipled")
f_vol.inputs["Color"].default_value = (0.62, 0.70, 0.82, 1.0)
f_vol.inputs["Anisotropy"].default_value = 0.58
f_vol.inputs["Emission Strength"].default_value = 0.0
f_links.new(f_vol.outputs["Volume"], f_out.inputs["Volume"])

f_tc = f_nodes.new("ShaderNodeTexCoord")
f_sep = f_nodes.new("ShaderNodeSeparateXYZ")
f_links.new(f_tc.outputs["Generated"], f_sep.inputs["Vector"])

f_ramp_z = f_nodes.new("ShaderNodeValToRGB")
f_ramp_z.color_ramp.elements[0].position = 0.0
f_ramp_z.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
e_fz = f_ramp_z.color_ramp.elements.new(0.30)
e_fz.color = (0.32, 0.32, 0.32, 1.0)
f_ramp_z.color_ramp.elements[1].position = 0.62
f_ramp_z.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
f_links.new(f_sep.outputs["Z"], f_ramp_z.inputs["Fac"])

f_ramp_y = f_nodes.new("ShaderNodeValToRGB")
f_ramp_y.color_ramp.elements[0].position = 0.02
f_ramp_y.color_ramp.elements[0].color = (0.18, 0.18, 0.18, 1.0)
e_fy = f_ramp_y.color_ramp.elements.new(0.35)
e_fy.color = (0.55, 0.55, 0.55, 1.0)
f_ramp_y.color_ramp.elements[1].position = 0.85
f_ramp_y.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
f_links.new(f_sep.outputs["Y"], f_ramp_y.inputs["Fac"])

f_noise = f_nodes.new("ShaderNodeTexNoise")
f_noise.inputs["Scale"].default_value = 2.8
f_noise.inputs["Detail"].default_value = 5.0
f_noise.inputs["Roughness"].default_value = 0.55
f_links.new(f_tc.outputs["Object"], f_noise.inputs["Vector"])

f_ramp_n = f_nodes.new("ShaderNodeValToRGB")
f_ramp_n.color_ramp.elements[0].position = 0.30
f_ramp_n.color_ramp.elements[0].color = (0.45, 0.45, 0.45, 1.0)
f_ramp_n.color_ramp.elements[1].position = 0.75
f_ramp_n.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
f_links.new(f_noise.outputs["Fac"], f_ramp_n.inputs["Fac"])

f_mul1 = f_nodes.new("ShaderNodeMath")
f_mul1.operation = 'MULTIPLY'
f_links.new(f_ramp_z.outputs["Color"], f_mul1.inputs[0])
f_links.new(f_ramp_y.outputs["Color"], f_mul1.inputs[1])

f_mul2 = f_nodes.new("ShaderNodeMath")
f_mul2.operation = 'MULTIPLY'
f_links.new(f_mul1.outputs["Value"], f_mul2.inputs[0])
f_links.new(f_ramp_n.outputs["Color"], f_mul2.inputs[1])

f_mul_dens = f_nodes.new("ShaderNodeMath")
f_mul_dens.operation = 'MULTIPLY'
f_links.new(f_mul2.outputs["Value"], f_mul_dens.inputs[0])
f_mul_dens.inputs[1].default_value = 0.045
f_links.new(f_mul_dens.outputs["Value"], f_vol.inputs["Density"])

fog_obj.data.materials.append(mat_fog)


# ==============================================================================
# 5. EEVEE VOLUMETRICS, SOFT SHADOWS, CAMERA DOF & AGX COLOR GRADING
# ==============================================================================
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 28
scene.eevee.use_volumetric_shadows = True
scene.eevee.volumetric_samples = 64
scene.eevee.volumetric_start = 0.4
scene.eevee.volumetric_end = 24.0
scene.eevee.shadow_ray_count = 2
scene.eevee.shadow_step_count = 8

cam = scene.camera
if cam:
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 7.2
    cam.data.dof.aperture_fstop = 4.2

scene.view_settings.view_transform = 'AgX'
try:
    scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    scene.view_settings.look = 'None'
scene.view_settings.exposure = -0.05
scene.view_settings.gamma = 1.0
