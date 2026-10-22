import bpy
import bmesh
import math
import random
import numpy as np
from mathutils import Vector

random.seed(2026)

# ==============================================================================
# 1. CONNECTED MESH ISLAND EXTRACTION & PCA ORIENTATION HELPERS
# ==============================================================================
def get_connected_islands(bm):
    """Returns a list of (verts_list, faces_list) for each connected component in `bm`."""
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    visited_v = set()
    islands = []

    for v_start in bm.verts:
        if v_start.index in visited_v:
            continue
        comp_verts = []
        comp_faces = set()
        stack = [v_start]
        visited_v.add(v_start.index)
        while stack:
            v = stack.pop()
            comp_verts.append(v)
            for f in v.link_faces:
                comp_faces.add(f)
            for e in v.link_edges:
                v_other = e.other_vert(v)
                if v_other.index not in visited_v:
                    visited_v.add(v_other.index)
                    stack.append(v_other)
        if comp_faces:
            islands.append((comp_verts, list(comp_faces)))
    return islands

def compute_island_axes(verts, faces):
    """
    Computes centroid and 3 orthonormal principal axes (e_long, e_mid, e_thin)
    plus eigenvalues (lam0 >= lam1 >= lam2) for a mesh island.
    Uses longest edge & dominant face normal refinement for box/plank islands so
    axes align with 0.00 degree precision to tilted planks, shutters, spokes, and shingles.
    """
    pts = np.array([[v.co.x, v.co.y, v.co.z] for v in verts], dtype=np.float64)
    center_np = pts.mean(axis=0)
    centered = pts - center_np
    cov = np.dot(centered.T, centered) / max(len(pts), 1)
    eigvals, eigvecs = np.linalg.eigh(cov)
    # Sort descending: idx 2 is largest, idx 0 is smallest
    order = np.argsort(eigvals)[::-1]
    lams = eigvals[order]
    vecs = eigvecs[:, order]

    e_long = Vector(vecs[:, 0]).normalized()
    e_mid = Vector(vecs[:, 1]).normalized()
    e_thin = e_long.cross(e_mid).normalized()
    e_mid = e_thin.cross(e_long).normalized()

    # If this is a plank/box/shingle island (few faces), refine using actual face normals & longest edges
    if len(faces) <= 40:
        # Find face with largest area to get exact plank normal
        best_f = max(faces, key=lambda f: f.calc_area())
        n_dom = best_f.normal.copy()
        if n_dom.length > 0.001:
            # Find longest edge perpendicular to n_dom (or longest edge overall)
            edges_set = {e for f in faces for e in f.edges}
            best_dir = None
            best_len = -1.0
            for e in edges_set:
                d = e.verts[1].co - e.verts[0].co
                d_len = d.length
                if d_len > best_len:
                    best_len = d_len
                    best_dir = d.normalized()
            if best_dir is not None:
                e_long = best_dir
                # Make e_thin orthogonal to e_long, closest to n_dom or smallest PCA axis
                thin_cand = Vector(vecs[:, 2]).normalized()
                if abs(thin_cand.dot(e_long)) > 0.85:
                    thin_cand = n_dom
                e_thin = (thin_cand - e_long * thin_cand.dot(e_long)).normalized()
                e_mid = e_thin.cross(e_long).normalized()

    return Vector(center_np), e_long, e_mid, e_thin, lams

# ==============================================================================
# 2. CYLINDRICAL LOG & RAFTER UNWRAPPING (True Seam-Free Cylindrical + Caps)
# ==============================================================================
def unwrap_cylindrical_island(verts, faces, uv_layer, grain_axis='V', len_scale=0.65, rad_scale=0.85, seed=0):
    rng = random.Random(seed)
    u_off = rng.uniform(0.0, 1.0)
    v_off = rng.uniform(0.0, 1.0)

    center, e_long, e_r1, e_r2, _lams = compute_island_axes(verts, faces)

    # Estimate mean radius around e_long
    radii = []
    for v in verts:
        rel = v.co - center
        rx = rel.dot(e_r1)
        ry = rel.dot(e_r2)
        radii.append(math.hypot(rx, ry))
    r_avg = max(sum(radii) / max(len(radii), 1), 0.03)

    for f in faces:
        # Check if end cap face (normal aligned with log axis e_long)
        if abs(f.normal.dot(e_long)) > 0.72:
            f_center = f.calc_center_median()
            for loop in f.loops:
                rel = loop.vert.co - f_center
                cu = rel.dot(e_r1) * rad_scale + u_off
                cv = rel.dot(e_r2) * rad_scale + v_off
                loop[uv_layer].uv = (cu, cv)
        else:
            # Cylindrical side face: keep angle continuous across all vertices of this face
            ref_ang = None
            for loop in f.loops:
                rel = loop.vert.co - center
                s_along = rel.dot(e_long)
                rx = rel.dot(e_r1)
                ry = rel.dot(e_r2)
                ang = math.atan2(ry, rx)
                if ref_ang is None:
                    ref_ang = ang
                else:
                    while ang - ref_ang > math.pi:
                        ang -= 2.0 * math.pi
                    while ang - ref_ang < -math.pi:
                        ang += 2.0 * math.pi
                arc = (ang / math.pi) * (r_avg * math.pi) * rad_scale
                along = s_along * len_scale
                if grain_axis == 'V':
                    loop[uv_layer].uv = (arc + u_off, along + v_off)
                else:
                    loop[uv_layer].uv = (along + u_off, arc + v_off)

# ==============================================================================
# 3. CIRCULAR WHEEL RIM UNWRAPPING (Grain curves around the wheel rim!)
# ==============================================================================
def unwrap_wheel_ring_island(verts, faces, uv_layer, grain_axis='V', circum_scale=0.85, cross_scale=1.2, seed=0):
    rng = random.Random(seed)
    u_off = rng.uniform(0.0, 1.0)
    v_off = rng.uniform(0.0, 1.0)

    center, e_r1, e_r2, e_axis, _lams = compute_island_axes(verts, faces)
    radii = [math.hypot((v.co - center).dot(e_r1), (v.co - center).dot(e_r2)) for v in verts]
    r_avg = max(sum(radii) / max(len(radii), 1), 0.15)

    for f in faces:
        ref_ang = None
        # Determine whether face normal is axial (side of wheel) or radial (inner/outer tire surface)
        is_axial = abs(f.normal.dot(e_axis)) > 0.5
        for loop in f.loops:
            rel = loop.vert.co - center
            rx = rel.dot(e_r1)
            ry = rel.dot(e_r2)
            axial = rel.dot(e_axis)
            r_cur = math.hypot(rx, ry)
            ang = math.atan2(ry, rx)
            if ref_ang is None:
                ref_ang = ang
            else:
                while ang - ref_ang > math.pi:
                    ang -= 2.0 * math.pi
                while ang - ref_ang < -math.pi:
                    ang += 2.0 * math.pi

            along_circum = ang * r_avg * circum_scale
            across = (r_cur - r_avg) * cross_scale if is_axial else axial * cross_scale

            if grain_axis == 'V':
                loop[uv_layer].uv = (across + u_off, along_circum + v_off)
            else:
                loop[uv_layer].uv = (along_circum + u_off, across + v_off)

# ==============================================================================
# 4. ORIENTED PLANK / BEAM / SHINGLE / SPOKE ISLAND UNWRAPPING
# ==============================================================================
def unwrap_plank_island(verts, faces, uv_layer, grain_axis='U', len_scale=0.75, cross_scale=0.65, seed=0):
    """
    Unwraps a single plank, beam, shingle, muntin, spoke, or rung in its own local
    3D coordinate system (e_long, e_mid, e_thin), unfolding its 6 box faces continuously
    around the front face and aligning `e_long` strictly with the texture's wood grain axis.
    """
    rng = random.Random(seed)
    along_off = rng.uniform(0.0, 1.0)
    # Offset cross-grain slightly within a single board strip so plank seams don't cut inside a board
    cross_off = rng.uniform(0.05, 0.85)

    center, e_long, e_mid, e_thin, _lams = compute_island_axes(verts, faces)

    # Measure half-width and half-thickness in local frame for continuous edge wrap
    w_vals = [(v.co - center).dot(e_mid) for v in verts]
    t_vals = [(v.co - center).dot(e_thin) for v in verts]
    l_vals = [(v.co - center).dot(e_long) for v in verts]
    half_w = max((max(w_vals) - min(w_vals)) * 0.5, 0.01)
    half_t = max((max(t_vals) - min(t_vals)) * 0.5, 0.005)
    half_l = max((max(l_vals) - min(l_vals)) * 0.5, 0.01)

    for f in faces:
        n = f.normal
        nl = n.dot(e_long)
        nm = n.dot(e_mid)
        nt = n.dot(e_thin)

        for loop in f.loops:
            rel = loop.vert.co - center
            l = rel.dot(e_long)
            w = rel.dot(e_mid)
            t = rel.dot(e_thin)

            # Unfold box sides continuously relative to the main plank face (e_thin)
            if abs(nt) >= abs(nm) and abs(nt) >= abs(nl):
                # Front or back main face of plank/shingle
                c_along = l
                c_cross = w if nt >= 0.0 else -w
            elif abs(nm) >= abs(nl):
                # Left or right narrow edge of plank (wrap t outward from ±half_w)
                c_along = l
                sign_m = 1.0 if nm >= 0.0 else -1.0
                c_cross = sign_m * (half_w + (half_t - t))
            else:
                # Top or bottom end-grain cap of plank (wrap t outward from ±half_l)
                sign_l = 1.0 if nl >= 0.0 else -1.0
                c_along = sign_l * (half_l + (half_t - t))
                c_cross = w

            coord_along = c_along * len_scale + along_off
            coord_cross = c_cross * cross_scale + cross_off

            if grain_axis == 'U':
                loop[uv_layer].uv = (coord_along, coord_cross)
            else:
                loop[uv_layer].uv = (coord_cross, coord_along)

# ==============================================================================
# 5. APPLY GEOMETRY-FITTED UVs TO ALL SCENE OBJECTS
# ==============================================================================
def unwrap_mesh_by_islands(obj_name, mode="plank", grain_axis='U', len_scale=0.75, cross_scale=0.65):
    obj = bpy.data.objects.get(obj_name)
    if obj is None or obj.type != 'MESH':
        return 0
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.verify()

    islands = get_connected_islands(bm)
    for idx, (verts, faces) in enumerate(islands):
        isl_seed = hash((obj_name, idx)) & 0xFFFFFFFF
        if mode == "cylindrical":
            unwrap_cylindrical_island(verts, faces, uv_layer, grain_axis=grain_axis, len_scale=len_scale, rad_scale=cross_scale, seed=isl_seed)
        elif mode == "mixed_roof":
            # In Wiezba_Dachowa_Krokwie_Laty: round logs have >60 verts, rectangular battens have <=50 verts
            if len(verts) > 60:
                unwrap_cylindrical_island(verts, faces, uv_layer, grain_axis=grain_axis, len_scale=len_scale, rad_scale=cross_scale, seed=isl_seed)
            else:
                unwrap_plank_island(verts, faces, uv_layer, grain_axis=grain_axis, len_scale=len_scale, cross_scale=cross_scale, seed=isl_seed)
        elif mode == "cart":
            # In Woz_Drewniany_Konstrukcja: wheel rims have >80 verts & circular PCA (lam1/lam0 > 0.75), hubs have ~32-64 verts
            _c, _e1, _e2, _e3, lams = compute_island_axes(verts, faces)
            if len(verts) >= 80 and lams[0] > 0.001 and (lams[1] / lams[0]) > 0.70:
                unwrap_wheel_ring_island(verts, faces, uv_layer, grain_axis=grain_axis, circum_scale=len_scale, cross_scale=cross_scale, seed=isl_seed)
            elif len(verts) == 64:
                unwrap_cylindrical_island(verts, faces, uv_layer, grain_axis=grain_axis, len_scale=len_scale, rad_scale=cross_scale, seed=isl_seed)
            else:
                unwrap_plank_island(verts, faces, uv_layer, grain_axis=grain_axis, len_scale=len_scale, cross_scale=cross_scale, seed=isl_seed)
        else:
            unwrap_plank_island(verts, faces, uv_layer, grain_axis=grain_axis, len_scale=len_scale, cross_scale=cross_scale, seed=isl_seed)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return len(islands)

counts = {}

# 5.1 Wall Logs (Sciany_Bale) -> Mat_Bale_Drewno (bark_brown_02: grain_axis = 'V')
counts["Sciany_Bale"] = unwrap_mesh_by_islands("Sciany_Bale", mode="cylindrical", grain_axis='V', len_scale=0.55, cross_scale=0.95)

# 5.2 Wooden Shingles (Dach_Gont_Drewniany) -> Mat_Gont_Drewniany (brown_planks_03: grain_axis = 'V')
# cross_scale=0.45 ensures each shingle fits inside a single wooden board strip without plank seams cutting across it!
counts["Dach_Gont_Drewniany"] = unwrap_mesh_by_islands("Dach_Gont_Drewniany", mode="plank", grain_axis='V', len_scale=0.85, cross_scale=0.42)

# 5.3 Roof Rafters & Battens (Wiezba_Dachowa_Krokwie_Laty) -> Mat_Belki_Okienne (dark_wooden_planks: grain_axis = 'U')
counts["Wiezba_Dachowa_Krokwie_Laty"] = unwrap_mesh_by_islands("Wiezba_Dachowa_Krokwie_Laty", mode="mixed_roof", grain_axis='U', len_scale=0.65, cross_scale=0.45)

# 5.4 Door, Frame & Porch Steps (Drzwi_I_Ganek) -> Mat_Belki_Okienne (dark_wooden_planks: grain_axis = 'U')
counts["Drzwi_I_Ganek"] = unwrap_mesh_by_islands("Drzwi_I_Ganek", mode="plank", grain_axis='U', len_scale=0.62, cross_scale=0.38)

# 5.5 Rustic Wooden Fence (Stary_Plot_Drewniany) -> Mat_Belki_Okienne (dark_wooden_planks: grain_axis = 'U')
counts["Stary_Plot_Drewniany"] = unwrap_mesh_by_islands("Stary_Plot_Drewniany", mode="mixed_roof", grain_axis='U', len_scale=0.65, cross_scale=0.45)

# 5.6 Windows (Belki_Oscieznica -> dark_wooden_planks 'U', Okiennice -> blue_painted_planks 'U')
for win_prefix in ("Okno_Front_Lewe", "Okno_Front_Prawe", "Okno_Boczne_Lewe"):
    counts[f"{win_prefix}_Belki"] = unwrap_mesh_by_islands(f"{win_prefix}_Belki_Oscieznica", mode="plank", grain_axis='U', len_scale=0.70, cross_scale=0.38)
    counts[f"{win_prefix}_Okiennice"] = unwrap_mesh_by_islands(f"{win_prefix}_Okiennice", mode="plank", grain_axis='U', len_scale=0.80, cross_scale=0.35)
    unwrap_mesh_by_islands(f"{win_prefix}_Zawiasy_Kute", mode="plank", grain_axis='U', len_scale=1.0, cross_scale=1.0)
    unwrap_mesh_by_islands(f"{win_prefix}_Szyby", mode="plank", grain_axis='U', len_scale=1.0, cross_scale=1.0)

# 5.7 Wooden Cart (Woz_Drewniany_Konstrukcja) -> Mat_Drewno_Wozu (brown_planks_03: grain_axis = 'V')
counts["Woz_Drewniany_Konstrukcja"] = unwrap_mesh_by_islands("Woz_Drewniany_Konstrukcja", mode="cart", grain_axis='V', len_scale=0.75, cross_scale=0.42)
counts["Woz_Drewniany_Okucia"] = unwrap_mesh_by_islands("Woz_Drewniany_Okucia_Obrecze", mode="cart", grain_axis='V', len_scale=0.75, cross_scale=0.50)

# 5.8 Smooth Conformal Surface UV for Terrain (Teren_Ziemia) & Water (Woda_Kaluze)
for ground_name, g_scale in [("Teren_Ziemia", 0.52), ("Woda_Kaluze", 0.50)]:
    g_obj = bpy.data.objects.get(ground_name)
    if g_obj and g_obj.type == 'MESH':
        bm = bmesh.new()
        bm.from_mesh(g_obj.data)
        uv_l = bm.loops.layers.uv.verify()
        for f in bm.faces:
            for loop in f.loops:
                co = loop.vert.co
                loop[uv_l].uv = (co.x * g_scale, co.y * g_scale)
        bm.to_mesh(g_obj.data)
        bm.free()
        g_obj.data.update()

# 5.9 Foundation & Chimney Stones -> Spherical / Local Box UV
for obj in bpy.data.objects:
    if obj.name.startswith("Kamien_Fundament_") or obj.name.startswith("Kamien_Komin_"):
        unwrap_mesh_by_islands(obj.name, mode="plank", grain_axis='U', len_scale=1.2, cross_scale=1.2)

# ==============================================================================
# 6. RESET MATERIAL MAPPING NODES TO IDENTITY (Let Geometry-Fitted UVs Drive!)
# ==============================================================================
for mat_name in ["Mat_Bale_Drewno", "Mat_Gont_Drewniany", "Mat_Belki_Okienne", "Mat_Drewno_Wozu", "Mat_Okiennice", "Mat_Ziemia_Bloto"]:
    mat = bpy.data.materials.get(mat_name)
    if mat and mat.use_nodes:
        for n in mat.node_tree.nodes:
            if n.type == 'MAPPING':
                n.inputs["Rotation"].default_value = (0.0, 0.0, 0.0)
                n.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
                n.inputs["Location"].default_value = (0.0, 0.0, 0.0)

# Render updated preview
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
final_uv_path = r"C:\Users\Przemke\.gemini\antigravity\brain\0cf18e8a-e024-4b6e-83b7-e73c5ff60dab\cabin_scene_uv_fitted.png"
scene.render.filepath = final_uv_path
bpy.ops.render.render(write_still=True)

result = {
    "status": "uv_fitted_and_rendered",
    "island_counts": counts,
    "preview_path": final_uv_path,
}
