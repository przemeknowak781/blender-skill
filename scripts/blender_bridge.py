import argparse
import json
import pathlib
import socket
import sys


def execute_blender(
    code: str,
    host: str = "127.0.0.1",
    port: int = 9876,
    strict_json: bool = False,
    timeout: float = 120.0,
) -> dict:
    req = {
        "type": "execute",
        "code": code,
        "strict_json": strict_json,
    }
    payload = (json.dumps(req) + "\0").encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((host, port))
        s.sendall(payload)
        buf = bytearray()
        while b"\0" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf.extend(chunk)
    raw = bytes(buf.split(b"\0", 1)[0]).decode("utf-8")
    return json.loads(raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", type=str, help="Path to Python script to run in Blender")
    parser.add_argument("--code", "-c", type=str, help="Inline Python code to run in Blender")
    parser.add_argument("--timeout", "-t", type=float, default=120.0)
    args = parser.parse_args()

    if args.file:
        code_str = pathlib.Path(args.file).read_text(encoding="utf-8")
    elif args.code:
        code_str = args.code
    else:
        code_str = "import bpy\nresult = {'objects': [o.name for o in bpy.data.objects]}"

    res = execute_blender(code_str, timeout=args.timeout)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if res.get("status") != "ok":
        sys.exit(1)
