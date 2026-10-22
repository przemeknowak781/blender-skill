---
name: blender-photoreal-scene
description: >-
  End-to-end workflow and ruleset for generating photorealistic, moody 3D architectural
  and nature scenes in Blender 5.x via the MCP TCP bridge (port 9876) from a single prompt.
  Covers multi-part bmesh modeling, CC0 Poly Haven PBR/3D asset harvesting, PCA island
  geometry-fitted UV unwrapping, perspective cloud domes, layered forest backgrounds,
  and diffused volumetric lighting. Activate whenever the user asks to create, upgrade,
  texture, unwrap, light, or render a realistic 3D scene in Blender.
---

# Blender 5.x Photorealistic Scene & Moody Lighting Skill (`blender-photoreal-scene`)

This skill enables an AI agent to build **production-grade, photorealistic 3D environments in Blender 5.x from a single user prompt**—going all the way from empty scene to multi-part procedural `bmesh` architecture, real CC0 PBR textures and botanical 3D models (Poly Haven), geometry-fitted UV maps, perspective cloud skies, multi-layered backgrounds, and moody volumetric lighting.

---

## 1. One-Prompt Master Prompt Template (Szablon Jednego Promptu)

To reproduce the exact quality of our reference scene (or any similar complex environment) in **one single turn/prompt**, the user can give a prompt structured like this—or the agent MUST automatically expand any short scene request into all 7 stages below:

> **Przykładowy „Jeden Prompt” (PL):**
> *„Użyj skilla `blender-photoreal-scene` i stwórz w Blenderze (przez MCP na porcie 9876) kompletną, fotorealistyczną scenę: rozpadająca się chata z bali kryta gontem (z zapadniętą częścią dachu odsłaniającą krokwie i łaty), szczegółowe okna z ościeżnicami, szprosami i przekrzywionymi drewnianymi okiennicami na kutych zawiasach, a przed chatą drewniany wóz drabiniasty ze szprychowymi kołami i żelaznymi obręczami. Wykonaj od razu pełny pipeline w 7 krokach: (1) wieloczęściowa geometria bmesh z detalami konstrukcyjnymi, (2) pobranie tekstur PBR i modeli 3D roślin/skał/drzew z Poly Haven (paprocie, trawa, pokrzywy, omszałe głazy, sosny), (3) wyrzeźbienie błotnistego terenu z koleinami, odbijającymi kałużami i leśnymi skarpami w tle, (4) dopasowanie UV bezpośrednio do geometrii każdej wyspy siatki (PCA: cylindrycznie dla bali, wzdłuż włókien dla desek/gontów/szprych, obwodowo dla obręczy kół), (5) wielowarstwowe tło leśne z niskim podszytem na horyzoncie i prześwitami na niebo, (6) hybrydowe niebo HDRI z chmurami w rzucie perspektywicznym, (7) nastrojowe, miękkie, rozmyte oświetlenie (słońce o kącie 36°, rozległe dyfuzory Area, ciepła poświata z przydymionych okien chaty, trójwymiarowa mgła wolumetryczna z cieniami oraz profil AgX Medium High Contrast). Po każdym etapie zweryfikuj render podglądowy.”*

---

## 2. Mandatory 7-Stage Execution Pipeline

When activated on a scene-creation request, **DO NOT stop at a simple primitive blockout**. Execute all 7 stages sequentially and verify the final render visually:

1. **Stage 1 — Blender 5.x MCP Bridge & Sandbox-Safe Scene Reset**
   - Connect to `127.0.0.1:9876` using [scripts/blender_bridge.py](./scripts/blender_bridge.py) (null-byte `\0` delimited JSON `{"type": "execute", "code": ..., "strict_json": false}`).
   - **Never call `bpy.ops.wm.read_factory_settings()`** (blocked by Blender 5.2's `weak_sandbox.py`). Instead, clear objects, meshes, materials, lights, cameras, and collections directly via `bpy.data`.
2. **Stage 2 — Anatomical Multi-Part `bmesh` Modeling**
   - Build every structure from individual physical sub-elements (logs, rafters, battens, individual shingles, window casings, muntins, shutter planks, iron hinges, wheel hubs, spokes, felloes, iron tires) as separate connected mesh islands so both lighting and UV unwrapping work on real geometry.
3. **Stage 3 — Poly Haven CC0 PBR & 3D Asset Harvesting**
   - Run [scripts/download_polyhaven_assets.py](./scripts/download_polyhaven_assets.py) to fetch 2K HDRIs, 1K/2K PBR texture maps (`Diffuse`, `Rough`, `nor_gl`), and 3D `.blend` botanical/rock assets (`fern_02`, `grass_medium_01`, `weed_plant_02`, `nettle_plant`, `rock_moss_set_01`, `pine_sapling_medium`, `fir_tree_01`).
   - Append template meshes into a hidden collection (`00_PolyHaven_Templates`, `hide_viewport=True`, `hide_render=True`) and resolve relative `//` image paths against the downloaded `assets/models/` directory.
4. **Stage 4 — Geometry-Fitted PCA UV Unwrapping (`Dopasowanie UV do Geometrii`)**
   - Run [scripts/fit_uv_to_geometry.py](./scripts/fit_uv_to_geometry.py) to decompose every architectural and prop mesh into connected `bmesh` islands (`get_connected_islands`) and unwrap each island in its own local 3D principal coordinate frame (`compute_island_axes`).
5. **Stage 5 — Sculpted Terrain, Reflective Puddles & Layered Forest Background**
   - Sculpt wheel ruts (`koleiny`), puddle basins (`kałuże`), and side/rear woodland mounds (`skarpy leśne`).
   - Place distant `LOD2` trees (`Y >= 6.8` behind main subject, `|X| >= 5.2` on sides so zero branches clip through roofs/walls) and low horizon bushes (`scale_z ~ 0.40`) to mask the ground-to-sky horizon seam while leaving upper sky windows open for clouds.
6. **Stage 6 — Hybrid HDRI + Perspective Cloud Sky Dome**
   - Project world ray `(dx, dy, dz)` onto a horizontal cloud ceiling `(dx / max(dz + 0.05, 0.065), dy / max(dz + 0.05, 0.065))` so procedural cumulus/stratus clouds foreshorten toward the horizon naturally.
7. **Stage 7 — Moody Diffused Lighting, Warm Window Glow & 3D Volumetric Mist**
   - Run [scripts/setup_moody_lighting_and_mist.py](./scripts/setup_moody_lighting_and_mist.py) to configure a `36°` soft-angle Sun, large cool/warm Area diffusers, frosted glowing window glass (`Roughness = 0.42`, `Specular IOR Level = 0.15`), a 3D height/depth-modulated `Principled Volume` mist domain (`Anisotropy = 0.58`, `use_volumetric_shadows = True`), Camera Depth of Field (`f/4.2`), and `AgX - Medium High Contrast`.

---

## 3. Core Technical Rules & Lessons Learned

### Rule 1: Blender 5.x Node & API Compatibility
- **`ShaderNodeMix` (`data_type = 'RGBA'`)**: Never connect color sockets by ambiguous name (`"A"` / `"B"`). Always use explicit socket indices:
  - `mix_node.inputs[0]` → Factor (`float`)
  - `mix_node.inputs[6]` → Color A (`RGBA`)
  - `mix_node.inputs[7]` → Color B (`RGBA`)
  - `mix_node.outputs[2]` → Result (`RGBA`)
- **`ShaderNodeBsdfPrincipled`**: Use Blender 4.0+/5.x socket names:
  - `"Specular IOR Level"` (not `"Specular"`),
  - `"Transmission Weight"` (not `"Transmission"`),
  - `"Coat Weight"` / `"Coat Roughness"` (not `"Clearcoat"`),
  - `"Emission Color"` and `"Emission Strength"`.
- **Render Engine Performance**:
  - Use `scene.render.engine = 'BLENDER_EEVEE'` (EEVEE Next) with `scene.eevee.use_raytracing = True`, `scene.eevee.taa_render_samples = 28..32`, `shadow_ray_count = 2`, `shadow_step_count = 8`. It delivers raytraced puddle reflections and volumetric shadows in ~35–45 seconds (compared to >3 minutes per frame on CPU Cycles).

### Rule 2: Anatomical Multi-Part Procedural Modeling (`bmesh`)
- **Never model wooden structures as single solid blocks**:
  - **Log Walls (`Sciany_Bale`)**: Generate each log as a separate horizontal cylinder (`12–16` segments) with corner saddle notches (`ostatki` overhanging by `0.22–0.32 m`), slight vertex noise, and progressive vertical sag (`Z` drop toward the collapsing corner).
  - **Shingle Roof (`Dach_Wiezba` + `Dach_Gont_Drewniany`)**: First build the structural timber frame (rafters `krokwie`, horizontal battens `łaty`, ridge beam `kalenica`), then populate rows of individual overlapping wedge-shaped shingles (`gonty`). In the collapsing roof zone, probabilistically omit shingles and tilt/slide adjacent shingles so the underlying rafters and battens are visibly exposed against the sky and backlight.
  - **Windows & Shutters (`Okno_*`)**: Build separate connected islands for outer casing beams (`ościeżnice`), sill (`parapet`), lintel (`nadproże`), inner frame, muntin bars (`szprosy`), glass panes (`szyby`), iron hinges (`zawiasy`), and individual vertical planks + Z-braces (`zetki`) for the crooked shutters (`okiennice`).
  - **Wooden Farm Cart (`Woz_Drewniany_*`)**: Build separate connected islands for chassis beams, axles, ladder rails/rungs (`drabinki`), wheel hubs (`piasty`), radial spokes (`szprychy`), curved wooden rims (`obwody kół`), and iron tire bands (`obręcze żelazne`).

### Rule 3: Geometry-Fitted UV Mapping (`fit_uv_to_geometry.py`)
Global `Generated` or `Box` mapping causes wood grain to run sideways across tilted shutters, diagonal spokes, and curved wheel rims. Always run PCA + edge-aligned island unwrapping ([scripts/fit_uv_to_geometry.py](./scripts/fit_uv_to_geometry.py)):
1. **Connected Component Decomposition**: Split each mesh into topological islands (`get_connected_islands(bm)`).
2. **Exact Local Frame (`compute_island_axes`)**:
   - Compute the covariance matrix eigenvalues/eigenvectors (`np.linalg.eigh(cov)`).
   - For plank/box/shingle islands (`len(faces) <= 40`), refine the primary axis `e_long` using the island's longest physical edge and `e_thin` using the largest-area face normal. This guarantees **0.00° grain alignment** even on crooked shutters, tilted cart staves, and radial wheel spokes.
3. **Topology-Specific UV Projection**:
   - **Cylindrical Logs & Rafters (`unwrap_cylindrical_island`)**: Unwrap side faces continuously via `atan2(ry, rx)` around `e_long` (unwrapping angle jumps across `±pi` per face so no seam wraps across a single polygon) and planar-project end caps (`|normal · e_long| > 0.72`) as circular cross-sections.
   - **Planks, Beams, Shingles & Spokes (`unwrap_plank_island`)**: Unfold front, back, left, right, top, and bottom faces continuously around `e_long` and `e_mid`, with random per-island UV offsets (`seed = island_idx`) so adjacent boards never show identical texture patterns.
   - **Wheel Rims & Iron Tires (`unwrap_wheel_ring_island`)**: Map the circumferential tangent angle `atan2(ry, rx) * r_avg` along the wood grain axis so the wood grain bends continuously around the circle of the wheel.
4. **Match Texture Grain Orientation**:
   - Verify whether each PBR texture has grain along `V` (e.g., Poly Haven `bark_brown_02`, `brown_planks_03`) or along `U` (e.g., `dark_wooden_planks`, `blue_painted_planks`) and pass `grain_axis='V'` or `'U'` accordingly.

### Rule 4: Background Composition & Horizon Discipline
- **Never leave a flat terrain edge visible against the sky**:
  - Sculpt gentle woodland mounds (`skarpy`) on the left (`|X| > 3.0`), right, and behind the building.
  - Blend the ground material (`Mat_Ziemia_Bloto`) by distance/height from glossy wet mud (`Roughness = 0.08`) near foreground puddles to dark, matte, mossy forest soil (`(0.22, 0.25, 0.18)`, `Roughness = 0.85`) on distant hills.
  - **Two-tier vegetation horizon**:
    1. **Tall framing trees (`PH_Sosna_Tlo_*`)**: Keep strictly behind the building (`Y >= 6.8`) and on the outer flanks (`|X| >= 5.2`) so branches never intersect the roof or walls, and leave wide sky windows above the side horizon so clouds are visible.
    2. **Low horizon shrubs (`PH_Krzew_Tlo_*`)**: Place scaled-down, vertically compressed evergreen/bush instances (`scale_z = 0.36..0.48`, sunk `-0.25 m` into the ground) along the left and right horizon (`|X| in [3.8, 8.5]`). They completely hide the bare terrain horizon line while keeping the upper 70% of the sky open.

### Rule 5: Moody, Diffused Lighting & Volumetric Mist ("Nastrojowe Rozmyte Oświetlenie")
To achieve a cinematic, atmospheric, softly diffused look instead of harsh CG daylight:
1. **Heavily Diffused Key Sun (`Slonce_Glowne`)**:
   - Set `sun.data.angle = math.radians(36.0)` (`36°–38°` angular diameter) so all cast shadows have wide, painterly penumbras.
   - Use a low grazing angle (`~20°` above horizon), warm golden-amber color `(1.0, 0.68, 0.38)`, moderate energy (`1.05–1.35`), and reduced `specular_factor = 0.28` to eliminate plastic white highlights on foliage and wood.
2. **Large Soft Area Diffusers**:
   - **Sky Canopy Fill (`Swiatlo_Dopelniajace_Niebo`)**: `DISK` Area light, `size = 14.0 m`, cool slate-blue `(0.42, 0.58, 0.86)`, `specular_factor = 0.12`.
   - **Back/Rim Mist Light (`Swiatlo_Mgla_Tyl`)**: `RECTANGLE` Area light (`14 m × 6 m`) placed behind the cabin/trees (`Y = 4.8, Z = 4.2`) pointing toward the camera with warm amber color `(1.0, 0.64, 0.32)` and `volume_factor = 1.8` to rim-light the broken roof rafters, shingles, and mist.
3. **Warm Frosted Window Lantern Glow (No Mirror Hotspot Dots!)**:
   - Never put an unshielded `POINT` light in front of or behind low-roughness glass—it creates a fake white specular dot on the window pane.
   - Set window glass (`Mat_Szklo_Okienne`) to `Roughness = 0.42`, `Specular IOR Level = 0.15`, `Transmission Weight = 0.0`, and drive `Emission Color` (`Emission Strength = 2.4`) with a 3D `Noise Texture` + warm amber-orange `ColorRamp` `((0.28, 0.11, 0.03) -> (0.85, 0.38, 0.10) -> (1.0, 0.62, 0.22))`.
   - Place soft outward-facing `RECTANGLE` Area lights (`Swiatlo_Okno_Lewe`, `Swiatlo_Okno_Prawe`, `size = 0.75 × 0.85 m`, `energy = 24.0`, `specular_factor = 0.10`, `volume_factor = 3.2`) just outside the window panes so warm golden hearth light spills naturally onto the crooked shutters, window sills, and mist.
4. **3D Volumetric Mist Domain (`Mgla_Wolumetryczna`)**:
   - Create a volume box covering the scene starting ~`2 m` in front of the camera (`Y = -6.2` to `10.5`, `Z = -0.3` to `5.5`).
   - Use `Principled Volume` with **zero flat self-emission** (`Emission Strength = 0.0`—flat emission washes out black levels!), cool forest scattering color `(0.62, 0.70, 0.82)`, and high forward scattering (`Anisotropy = 0.58`).
   - Multiply 3 density gradients:
     - **Vertical (`Z`)**: Dense near ground/puddles (`0.0 -> 1.0`), medium around walls (`0.30 -> 0.32`), zero above roof ridge (`0.62 -> 0.0`) so upper sky clouds remain crisp.
     - **Depth (`Y`)**: Light in foreground (`0.18`), medium at cabin (`0.55`), dense in deep background forest (`1.0`).
     - **3D Noise**: Wispy breakup (`Scale = 2.8`, `Detail = 5.0`).
   - Enable `scene.eevee.use_volumetric_shadows = True`.
5. **Camera Depth of Field & AgX Grading**:
   - Enable `cam.data.dof.use_dof = True`, `focus_distance` on the main subject (`~7.2 m`), `aperture_fstop = 4.2`.
   - Use `view_transform = 'AgX'` and `look = 'AgX - Medium High Contrast'`.

---

## 4. Bundled Scripts & Reference Implementation

- **[scripts/blender_bridge.py](./scripts/blender_bridge.py)** — Standalone TCP client for executing Python files or inline snippets inside Blender 5.x via MCP port `9876`.
- **[scripts/download_polyhaven_assets.py](./scripts/download_polyhaven_assets.py)** — Multi-threaded downloader for Poly Haven HDRIs, PBR texture maps, and 3D `.blend` models.
- **[scripts/fit_uv_to_geometry.py](./scripts/fit_uv_to_geometry.py)** — Connected-island PCA UV unwrapper for cylindrical logs, planks/shingles/spokes, and circular wheel rims.
- **[scripts/setup_moody_lighting_and_mist.py](./scripts/setup_moody_lighting_and_mist.py)** — Complete moody diffused sky, perspective clouds, 36° soft sun, warm window glow, and 3D volumetric mist setup.
- **[examples/crumbling_log_cabin/](./examples/crumbling_log_cabin/)** — Full 5-step reproducible scripts that build the complete crumbling log cabin, farm cart, puddles, forest background, and moody lighting from scratch.
