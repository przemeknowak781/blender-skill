import bpy
import bmesh
import math
import pathlib
import random
from mathutils import Vector, Euler

random.seed(707)
ASSETS_DIR = pathlib.Path(r"c:\Users\Przemke\apps\aplikacja antigravity\assets")
scene = bpy.context.scene

col_env = bpy.data.collections.get("01_Srodowisko_Teren_Woda")
col_veg = bpy.data.collections.get("04_Roslinnosc_Paprocie_Trawa")
col_templates = bpy.data.collections.get("00_PolyHaven_Templates")

# ==============================================================================
# 1. FIX DISTANT TERRAIN MATERIAL (Dark Mossy Forest Floor Instead of Pale Dirt)
# ==============================================================================
mat_ground = bpy.data.materials.get("Mat_Ziemia_Bloto")
if mat_ground and mat_ground.use_nodes:
    nt = mat_ground.node_tree
    nodes, links = nt.nodes, nt.links
    # Darken overall value and tint distant/higher ground toward deep mossy forest green-brown
    for n in nodes:
        if n.type == 'VALTORGB':
            n.color_ramp.elements[0].position = 0.005
            n.color_ramp.elements[0].color = (0.22, 0.20, 0.18, 1.0) # dark wet mud near puddles
            n.color_ramp.elements[1].position = 0.065
            n.color_ramp.elements[1].color = (0.42, 0.45, 0.36, 1.0) # dark mossy forest soil on hills
        elif n.type == 'HUE_SAT':
            n.inputs["Saturation"].default_value = 1.15

# Sculpt background terrain hills on left & right so they form natural woodland mounds
terrain_obj = bpy.data.objects.get("Teren_Ziemia")
if terrain_obj and terrain_obj.type == 'MESH':
    bm = bmesh.new()
    bm.from_mesh(terrain_obj.data)
    for v in bm.verts:
        x, y = v.co.x, v.co.y
        # Raise gentle forest berms on far left (x < -3.2) and far right (x > 3.2) and behind cabin (y > 2.2)
        side_dist = max(0.0, abs(x) - 3.0)
        back_dist = max(0.0, y + 1.5)
        if side_dist > 0.0 and y > -3.5:
            mound = 0.12 * (side_dist ** 1.15) * min(1.0, (y + 3.5) / 4.0)
            noise_m = 0.08 * math.sin(x * 0.9 + y * 0.7) + 0.05 * math.cos(x * 1.8 - y * 1.4)
            v.co.z += mound + max(0.0, noise_m)
    bm.normal_update()
    bm.to_mesh(terrain_obj.data)
    bm.free()
    terrain_obj.data.update()

def sample_z(x, y):
    if terrain_obj:
        hit, loc, norm, idx = terrain_obj.ray_cast(Vector((x, y, 20.0)), Vector((0.0, 0.0, -1.0)))
        if hit:
            return loc.z
    return 0.1

# ==============================================================================
# 2. LOAD LIGHTWEIGHT LOD2 PINE TREES & SHRUBS FOR FULL HORIZON TREELINE
# ==============================================================================
def get_or_append_template(mod_id, obj_names):
    blend_path = str(ASSETS_DIR / "models" / mod_id / f"{mod_id}.blend")
    existing = {o.name: o for o in bpy.data.objects}
    missing = [n for n in obj_names if n not in existing]
    if missing:
        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            avail = set(data_from.objects)
            data_to.objects = [n for n in missing if n in avail]
        for obj in data_to.objects:
            if obj is not None:
                col_templates.objects.link(obj)
    # Resolve any relative texture paths on newly loaded materials
    tex_lookup = {p.name.lower(): p for p in (ASSETS_DIR / "models").rglob("*") if p.is_file()}
    for img in bpy.data.images:
        if img.filepath and img.filepath.startswith("//"):
            fname = pathlib.Path(img.filepath.replace("//", "")).name.lower()
            if fname in tex_lookup:
                img.filepath = str(tex_lookup[fname])
                img.reload()
    return [bpy.data.objects[n] for n in obj_names if n in bpy.data.objects]

pines_lod2 = get_or_append_template("pine_sapling_medium", [
    "pine_sapling_medium_a_LOD2",
    "pine_sapling_medium_b_LOD2",
    "pine_sapling_medium_c_LOD2",
])
ferns_src = [o for o in bpy.data.objects if o.name in ("fern_02_a", "fern_02_b", "fern_02_c", "fern_02_d")]
grass_src = get_or_append_template("grass_medium_01", [
    "grass_medium_01_large_a_LOD1",
    "grass_medium_01_large_b_LOD1",
    "grass_medium_01_tall_a_LOD1",
    "grass_medium_01_tall_b_LOD1",
])
nettles_src = get_or_append_template("nettle_plant", [
    "nettle_plant_tall_a_LOD1",
    "nettle_plant_medium_a_LOD1",
])
weeds_src = get_or_append_template("weed_plant_02", [
    "weed_plant_02_a_LOD1",
    "weed_plant_02_b_LOD1",
])
rocks_src = [o for o in bpy.data.objects if o.name.startswith("rock_moss_set_01_rock")]

# Clear previous background pines & add a complete, well-composed multi-layer forest treeline + undergrowth
for obj in list(bpy.data.objects):
    if obj.name.startswith("PH_Sosna_Tlo_") or obj.name.startswith("PH_Krzew_Tlo_") or obj.name.startswith("PH_Tlo_"):
        bpy.data.objects.remove(obj, do_unlink=True)

def place_inst(src, name, loc, scale_xyz, rot_euler, col):
    inst = src.copy()
    inst.name = name
    inst.location = loc
    inst.scale = scale_xyz
    inst.rotation_euler = rot_euler
    col.objects.link(inst)
    return inst

# 2.1 Tall & Medium Forest Treeline spanning Left, Behind Cabin, and Right (framing sky gaps!)
treeline_coords = [
    # Left forest wing (behind wooden fence)
    (-8.8, 2.2, 2.4), (-7.4, 1.2, 2.1), (-6.4, 2.8, 2.5), (-5.2, 1.8, 2.2),
    (-4.2, 3.2, 2.4), (-3.4, 4.2, 2.6), (-5.8, 4.8, 2.8), (-7.8, 4.5, 2.7),
    # Central backdrop behind cabin
    (-2.2, 4.8, 2.6), (-0.6, 5.2, 2.5), (1.1, 5.0, 2.6), (2.5, 4.5, 2.4),
    # Right forest wing (behind wooden cart, leaving a nice sky window above the cart for the clouds!)
    (3.6, 3.6, 2.3), (4.8, 4.2, 2.5), (6.2, 3.2, 2.2), (7.6, 2.4, 2.4),
    (5.4, 1.5, 1.85), (6.8, 0.8, 1.95), (8.5, 1.2, 2.2), (9.2, 3.5, 2.6),
]
if pines_lod2:
    for i, (tx, ty, tsc) in enumerate(treeline_coords):
        src = pines_lod2[i % len(pines_lod2)]
        tz = sample_z(tx, ty)
        place_inst(
            src,
            f"PH_Sosna_Tlo_{i:02d}",
            Vector((tx, ty, tz - 0.08)),
            (tsc * random.uniform(0.92, 1.08), tsc * random.uniform(0.92, 1.08), tsc * random.uniform(0.90, 1.12)),
            (random.uniform(-0.04, 0.04), random.uniform(-0.04, 0.04), random.uniform(0.0, math.pi * 2.0)),
            col_veg,
        )

    # 2.2 Low Bushy Undergrowth / Dwarf Pines along the horizon line on Left & Right (hiding the terrain edge completely!)
    bush_coords = [
        # Left horizon behind & along the fence
        (-7.2, -1.2, 0.85), (-6.2, -0.5, 0.95), (-5.2, -0.2, 0.80), (-4.3, 0.4, 0.90),
        (-3.5, 0.8, 0.85), (-6.8, 0.6, 1.05), (-4.8, 1.2, 1.00), (-3.8, -1.2, 0.72),
        # Right horizon behind the wooden cart & fence
        (3.4, -0.4, 0.78), (4.2, -0.8, 0.85), (5.0, -0.3, 0.92), (5.8, -1.0, 0.88),
        (6.6, -0.4, 0.95), (7.5, -1.2, 0.90), (4.5, 0.8, 1.00), (6.0, 0.6, 1.05),
        (3.8, 1.4, 0.95), (5.2, 2.0, 1.10), (7.2, 1.5, 1.05), (8.2, -0.2, 0.95),
    ]
    for i, (bx, by, bsc) in enumerate(bush_coords):
        src = pines_lod2[(i + 1) % len(pines_lod2)]
        bz = sample_z(bx, by)
        # Sink trunk base (-0.38m) so the dense green branches sit right on the ground like forest bushes/shrubs!
        place_inst(
            src,
            f"PH_Krzew_Tlo_{i:02d}",
            Vector((bx, by, bz - 0.38 * bsc)),
            (bsc * 1.25, bsc * 1.25, bsc * 0.85),
            (random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08), random.uniform(0.0, math.pi * 2.0)),
            col_veg,
        )

# 2.3 Populate Mid-Ground Left (around fence) & Right (behind cart) with Ferns, Nettles, Grass & Mossy Boulders
bg_fern_spots = [
    (-3.6, -2.2, 1.45), (-4.2, -2.6, 1.55), (-4.8, -1.8, 1.50), (-5.5, -2.4, 1.60),
    (-3.3, -0.5, 1.40), (-4.0, -0.8, 1.50), (-4.8, -0.6, 1.45),
    (3.2, -1.8, 1.45), (3.8, -2.2, 1.50), (4.5, -1.6, 1.55), (5.2, -2.1, 1.45),
    (3.5, -0.8, 1.40), (4.3, -1.1, 1.50), (5.0, -1.2, 1.55), (5.8, -1.8, 1.45),
]
if ferns_src:
    for i, (fx, fy, fsc) in enumerate(bg_fern_spots):
        fz = sample_z(fx, fy)
        place_inst(
            ferns_src[i % len(ferns_src)],
            f"PH_Tlo_Paproc_{i:02d}",
            Vector((fx, fy, fz - 0.02)),
            (fsc, fsc, fsc),
            (0.0, 0.0, random.uniform(0.0, math.pi * 2.0)),
            col_veg,
        )

# Dense grass & nettles across the left and right background hills (x in [-8..-2.6] and [2.6..8], y in [-4..3])
bg_plants = grass_src + nettles_src + weeds_src
if bg_plants:
    for i in range(220):
        side = -1.0 if (i % 2 == 0) else 1.0
        gx = side * random.uniform(2.6, 7.8)
        gy = random.uniform(-4.2, 2.8)
        gz = sample_z(gx, gy)
        src = bg_plants[i % len(bg_plants)]
        sc = random.uniform(1.5, 2.4)
        place_inst(
            src,
            f"PH_Tlo_Roslina_{i:03d}",
            Vector((gx, gy, gz - 0.02)),
            (sc, sc, sc),
            (random.uniform(-0.06, 0.06), random.uniform(-0.06, 0.06), random.uniform(0.0, math.pi * 2.0)),
            col_veg,
        )

# Medium mossy boulders along the left fence and right forest edge
bg_boulders = [
    (-4.2, -1.6, 0.28), (-5.4, -1.2, 0.35), (-3.6, 0.2, 0.32),
    (3.8, -1.2, 0.26), (4.8, -1.5, 0.34), (5.6, -0.8, 0.30),
]
if rocks_src:
    for i, (rx, ry, rsc) in enumerate(bg_boulders):
        rz = sample_z(rx, ry)
        place_inst(
            rocks_src[i % len(rocks_src)],
            f"PH_Tlo_Glaz_{i:02d}",
            Vector((rx, ry, rz - 0.04)),
            (rsc, rsc, rsc * 0.85),
            (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1), random.uniform(0.0, math.pi * 2.0)),
            col_env,
        )

# Render updated scene
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 32
bg_preview = r"C:\Users\Przemke\.gemini\antigravity\brain\0cf18e8a-e024-4b6e-83b7-e73c5ff60dab\cabin_scene_bg_complete.png"
scene.render.filepath = bg_preview
bpy.ops.render.render(write_still=True)

result = {"status": "background_complete", "preview_path": bg_preview}
