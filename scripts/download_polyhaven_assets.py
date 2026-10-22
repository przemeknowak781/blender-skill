import concurrent.futures
import json
import pathlib
import urllib.request

BASE_DIR = pathlib.Path(r"c:\Users\Przemke\apps\aplikacja antigravity\assets")
BASE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url: str, dest: pathlib.Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1024:
        return f"SKIP {dest.name}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return f"OK {dest.name} ({len(data) // 1024} KB)"


tasks = []

# 1. HDRI Sky: autumn_field_puresky (2k hdr) + kloofendal_28d_misty_puresky (2k hdr)
for hdri_id in ["autumn_field_puresky", "kloofendal_28d_misty_puresky"]:
    info = get_json(f"https://api.polyhaven.com/files/{hdri_id}")
    res_block = info.get("hdri", {}).get("2k", {})
    fmt = "hdr" if "hdr" in res_block else next(iter(res_block.keys()))
    url = res_block[fmt]["url"]
    dest = BASE_DIR / "hdri" / f"{hdri_id}_2k.{fmt}"
    tasks.append((url, dest))

# 2. PBR Textures (1k diffuse, rough, nor_gl)
TEXTURE_IDS = [
    "brown_mud_leaves_01",
    "bark_brown_02",
    "brown_planks_03",
    "blue_painted_planks",
    "dark_wooden_planks",
]

for tex_id in TEXTURE_IDS:
    info = get_json(f"https://api.polyhaven.com/files/{tex_id}")
    tex_dir = BASE_DIR / "textures" / tex_id
    for map_type in ["Diffuse", "Rough", "nor_gl"]:
        if map_type in info:
            res_map = info[map_type].get("1k") or info[map_type].get("2k")
            if res_map:
                fmt = "jpg" if "jpg" in res_map else ("png" if "png" in res_map else next(iter(res_map.keys())))
                url = res_map[fmt]["url"]
                dest = tex_dir / f"{tex_id}_{map_type}.{fmt}"
                tasks.append((url, dest))

# 3. 3D Models (.blend 1k + included textures)
MODEL_IDS = [
    "fern_02",
    "grass_medium_01",
    "weed_plant_02",
    "nettle_plant",
    "rock_moss_set_01",
    "tree_stump_01",
    "pine_sapling_medium",
    "fir_tree_01",
]

for mod_id in MODEL_IDS:
    info = get_json(f"https://api.polyhaven.com/files/{mod_id}")
    blend_info = info.get("blend", {}).get("1k", {}).get("blend")
    if not blend_info:
        blend_info = info.get("blend", {}).get("2k", {}).get("blend")
    if blend_info:
        mod_dir = BASE_DIR / "models" / mod_id
        tasks.append((blend_info["url"], mod_dir / f"{mod_id}.blend"))
        for rel_path, inc_meta in blend_info.get("include", {}).items():
            tasks.append((inc_meta["url"], mod_dir / rel_path))

print(f"Total files queued: {len(tasks)}")
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    futures = [ex.submit(download_file, u, d) for u, d in tasks]
    for fut in concurrent.futures.as_completed(futures):
        try:
            print(fut.result())
        except Exception as e:
            print("ERR:", e)
print("ALL DOWNLOADS COMPLETE")
