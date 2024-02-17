import shutil
import struct
from pathlib import Path
import zlib

IS_DIR_FLAG = 0x1
IS_COMPRESSED_FLAG = 0x2

ROF_PATH = r"C:\Program Files (x86)\Microsoft Games\Crimson Skies\GOSDATA\ASSETS\crimson.rof"

def unpack(format, f):
    res = struct.unpack(format, f.read(struct.calcsize(format)))
    return res[0] if len(res) == 1 else res

def parse_entry(entry, f):
    if not entry["is_dir"]: return
    f.seek(entry["start"])
    num_entries = unpack("<I", f)
    nameslength = unpack("<I", f)

    entry["children"] = []
    for i in range(num_entries):
        t = unpack("<IIIIII", f)
        child = {}
        child["start"] = t[0]
        child["length"] = t[1]
        child["length_on_disk"] = t[2]
        child["is_dir"] = bool(t[3] & IS_DIR_FLAG)
        child["is_compressed"] = bool(t[3] & IS_COMPRESSED_FLAG)
        child["namelength"] = t[4]
        child["id"] = t[5]

        entry["children"].append(child)
    
    names_bs = b""
    for _ in range(nameslength):
        names_bs += unpack("c", f)
    names = names_bs.split(b"\x00")[:-1]
    for i, n in enumerate(names):
        entry["children"][i]["name"] = n.decode()
    
    for child in entry["children"]:
        parse_entry(child, f)

def write_tree_to_disk(entry, cwd, f):
    path = cwd / entry["name"]

    if entry["is_dir"]:
        path.mkdir()
        for child in entry["children"]:
            write_tree_to_disk(child, path, f)

    elif entry["is_compressed"]:
        with open(path, "wb") as new_file:
            f.seek(entry["start"])
            decompressed = zlib.decompress(f.read(entry["length"]))
            new_file.write(decompressed)
    else:
        with open(path, "wb") as new_file:
            f.seek(entry["start"])
            new_file.write(f.read(entry["length"]))

with open(ROF_PATH, mode='rb') as f:
    root = {"start": 0, "name": "rof_output", "is_dir": True}
    parse_entry(root, f)
    out_path = Path(root["name"])
    if out_path.is_dir(): shutil.rmtree(out_path)
    write_tree_to_disk(root, Path(), f)
