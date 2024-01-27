import argparse
import json
import os
from pathlib import Path
import subprocess as sub
from tempfile import TemporaryDirectory
import time
from zipfile import ZipFile

try:
    import PIL
except ImportError:
    print("This script requires pillow to work. Run pip install pillow!")

BLENDER_ARGS = ["--background", "--factory-startup", "--python-use-system-env", "--python"]
CHAPTERS = ["c1", "c1b", "c1c", "c2", "c2b", "c3", "c4", "c5"]

parser = argparse.ArgumentParser(description="Convert dumped Crimson Skies plane model data to blender files.")
parser.add_argument(
    "blender_exe",
    type=lambda value: Path(value).resolve(strict=True),
    help="Path to your Blender executable")
parser.add_argument(
    "data_folder",
    type=lambda value: Path(value).resolve(strict=True),
    help="Folder containing planes.zip and textures.zip")
parser.add_argument(
    "--unzbd",
    metavar="EXE",
    dest="unzbd",
    type=lambda value: Path(value).resolve(strict=True),
    help="Path to unzbd executable (will automate extraction if supplied). Requires --zbd")
parser.add_argument(
    "--zbd",
    metavar="FOLDER",
    dest="zbd",
    type=lambda value: Path(value).resolve(strict=True),
    help="Path to ZBD folder in game files")
parser.add_argument(
    "--out",
    metavar="FOLDER",
    dest="out_folder",
    default=".",
    type=lambda value: Path(value).resolve(strict=True),
    help="Folder to save .blend files")
parser.add_argument(
    "--skip-planes",
    action="store_true",
    help="Don't generate .blends for planes")
parser.add_argument(
    "--skip-levels",
    action="store_true",
    help="Don't generate .blends for levels")

try:
    args = parser.parse_args()
except FileNotFoundError as e:
    print(e)
    exit(1)

if args.unzbd:
    if not args.zbd:
        print("ZBD folder must be specified when using --unzbd")
        exit(1)

    print("Extracting .cab files...")
    with TemporaryDirectory(dir=".") as tempdir:
        tempdir = Path(tempdir)
        for c in CHAPTERS:
            try:
                (tempdir / c).mkdir()
                sub.Popen(["expand.exe", "-F:*", str(args.zbd / f"{c}.CAB"), str(tempdir / c)], stdout=sub.PIPE, stderr=sub.PIPE)
            except:
                print("Couldn't extract .CABs with expand.exe")
                exit(1)
        
        time.sleep(1) # expand.exe is so fucked

        print("Extracting .zbd files...")
        for c in CHAPTERS:
            gamez_path = next((tempdir / c).rglob("gamez.zbd"))
            sub.Popen([args.unzbd, "cs", "gamez", str(gamez_path), str(args.data_folder / f"{c}.zip")]).communicate()

        # dump all textures in same .zip
        (tempdir / "textures").mkdir()
        for f in tempdir.rglob("*textu*.zbd"):
            sub.Popen([args.unzbd, "cs", "textures", f, str(tempdir / "temp.zip")]).communicate()
            with ZipFile(tempdir / "temp.zip") as z:
                z.extractall(tempdir / "textures")
            (tempdir / "temp.zip").unlink()

        with ZipFile(args.data_folder / "textures.zip", "w") as z:
            for f in (tempdir / "textures").glob("*.png"):
                z.write(f, arcname = f.name)
    
    sub.Popen([args.unzbd, "cs", "gamez", str(args.zbd / "PLANES.ZBD"), str(args.data_folder / "planes.zip")]).communicate()

if not args.skip_planes:
    print("Generating plane .blends...")
    print("Searching for root nodes...")

    with ZipFile(str(args.data_folder / "planes.zip")) as level:
        with level.open("nodes.json") as f:
            nodes_json = json.load(f)

    roots = []
    for i, n in enumerate(nodes_json):
        v = next(iter(n.values()))
        if v["parent"] is None:
            print(f"Found root node with name {v['name']} at index {i}")
            roots.append((i, v["name"]))

    for i, name in roots:
        print(f"Generating {name}.blend...")
        sub.Popen([args.blender_exe] + BLENDER_ARGS + ["plane2blend.py", "--", str(args.data_folder), str(args.out_folder), str(i)]).communicate()

if not args.skip_levels:
    print("Generating level .blends...")

    for c in CHAPTERS:
        print(f"Generating {c}.blend...")
        sub.Popen([args.blender_exe] + BLENDER_ARGS + ["world2blend.py", "--", str(args.data_folder), str(args.out_folder), c]).communicate()
