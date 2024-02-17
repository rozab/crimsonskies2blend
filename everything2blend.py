import argparse
import json
from pathlib import Path
import subprocess as sub
import urllib.request
from zipfile import ZipFile

try:
    import PIL
except ImportError:
    print("This script requires pillow to work. Run pip install pillow!")

DEFAULT_BLENDER_LOCATION = r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe"
DEFAULT_CS_LOCATION = r"C:\Program Files (x86)\Microsoft Games\Crimson Skies"
MECH3AX_URL = "https://github.com/TerranMechworks/mech3ax/releases/download/v0.6.0/mech3ax-v0.6.0-x86_64-pc-windows-msvc.zip"

BLENDER_ARGS = ["--background", "--factory-startup", "--python-use-system-env", "--python"]
CHAPTERS = ["c1", "c1b", "c1c", "c2", "c2b", "c3", "c4", "c5"]

parser = argparse.ArgumentParser(description="Convert dumped Crimson Skies plane model data to blender files.")
parser.add_argument(
    "--unzbd",
    metavar="EXE",
    dest="unzbd",
    type=lambda value: Path(value).resolve(strict=True),
    help="Path to unzbd executable")
parser.add_argument(
    "--blender",
    metavar="EXE",
    dest="blender",
    default=DEFAULT_BLENDER_LOCATION,
    type=lambda value: Path(value).resolve(strict=True),
    help="Path to your Blender executable")
parser.add_argument(
    "--cs",
    metavar="FOLDER",
    dest="cs",
    default=DEFAULT_CS_LOCATION,
    type=lambda value: Path(value).resolve(strict=True),
    help="Path to CS install folder")
parser.add_argument(
    "--data",
    metavar="FOLDER",
    dest="data_folder",
    default=Path("data"),
    type=lambda value: Path(value).resolve(strict=True),
    help="Folder for intermediate data")
parser.add_argument(
    "--out",
    metavar="FOLDER",
    dest="blend_folder",
    default=Path("blend_output"),
    type=lambda value: Path(value).resolve(strict=True),
    help="Folder to save .blend files")
parser.add_argument(
    "--skip-unzbd",
    action="store_true",
    help="Use existing unzbd output")
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

args.data_folder.mkdir(exist_ok=True)
args.blend_folder.mkdir(exist_ok=True)

if not args.unzbd: args.unzbd = next(args.data_folder.rglob("unzbd.exe"), Path("unzbd.exe"))
if not args.unzbd.is_file():
    print("Downloading unzbd.exe from GitHub...")
    urllib.request.urlretrieve(MECH3AX_URL, args.data_folder / "mech3ax.zip")
    with ZipFile(args.data_folder / "mech3ax.zip") as z:
        z.extractall(args.data_folder)
    args.unzbd = next(args.data_folder.rglob("unzbd.exe"))

if not args.unzbd:
    print("Must specify unzbd.exe location with --unzbd")
    exit(1)

if not args.skip_unzbd:
    print("Extracting planes.zbd...")
    sub.Popen([args.unzbd, "cs", "gamez", str(args.cs / "ZBD" / "PLANES.ZBD"), str(args.data_folder / "planes.zip")]).communicate()

    print("Extracting gamez.zbd...")
    for c in CHAPTERS:
        gamez_path = args.cs / "ZBD" / c / "gamez.zbd"
        sub.Popen([args.unzbd, "cs", "gamez", str(gamez_path), str(args.data_folder / f"{c}.zip")]).communicate()

    print("Extracting texture.zbd...")
    with ZipFile(args.data_folder / "textures.zip", "w") as agg_zip:
        for f in args.cs.rglob("texture.zbd"):
            zip_path = args.data_folder / f"{f.parent.name}_textures.zip"
            sub.Popen([args.unzbd, "cs", "textures", f, str(zip_path)]).communicate()
            with ZipFile(zip_path) as chapter_zip:
                for texture_name in chapter_zip.namelist():
                    if texture_name not in agg_zip.namelist():
                        agg_zip.writestr(texture_name, chapter_zip.read(texture_name))
    

if not args.skip_planes:
    print("Generating plane .blends...")

    with ZipFile(str(args.data_folder / "planes.zip")) as level:
        with level.open("nodes.json") as f:
            nodes_json = json.load(f)

    roots = []
    for i, n in enumerate(nodes_json):
        v = next(iter(n.values()))
        if v["parent"] is None:
            roots.append((i, v["name"]))

    for i, name in roots:
        print(f"Generating {name}.blend...")
        sub.Popen([args.blender] + BLENDER_ARGS + ["plane2blend.py", "--", str(args.data_folder), str(args.blend_folder.resolve()), str(i)]).communicate()

if not args.skip_levels:
    print("Generating level .blends...")

    for c in CHAPTERS:
        print(f"Generating {c}.blend...")
        sub.Popen([args.blender] + BLENDER_ARGS + ["world2blend.py", "--", str(args.data_folder), str(args.blend_folder.resolve()), c]).communicate()
