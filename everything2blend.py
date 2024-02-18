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
    type=lambda value: Path(value),
    help="Path to unzbd executable")
parser.add_argument(
    "--blender",
    metavar="EXE",
    dest="blender",
    default=DEFAULT_BLENDER_LOCATION,
    type=lambda value: Path(value).resolve(),
    help="Path to your Blender executable")
parser.add_argument(
    "--cs",
    metavar="FOLDER",
    dest="cs",
    default=DEFAULT_CS_LOCATION,
    type=lambda value: Path(value),
    help="Path to CS install folder")
parser.add_argument(
    "--data",
    metavar="FOLDER",
    dest="data_dir",
    default=Path("data"),
    type=lambda value: Path(value),
    help="Folder for intermediate data. Defaults to ./data")
parser.add_argument(
    "--out",
    metavar="FOLDER",
    dest="blend_dir",
    default=Path("blend_output").resolve(),
    type=lambda value: Path(value).resolve(),
    help="Folder to save .blend files. Defaults to ./blend_output")
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

args.data_dir.mkdir(exist_ok=True)
args.blend_dir.mkdir(exist_ok=True)
unzbd_dir = args.data_dir / "unzbd_output"
unzbd_dir.mkdir(exist_ok=True)

if not args.cs.is_dir():
    print(f"ERROR: No CS installation directory present at {args.cs.resolve()}. Install the game or specify another location with --cs")

if not args.blender.is_file():
    print(f"ERROR: No blender executable present at {args.blender}. Install blender or specify another location with --blender")
    exit(1)

if not args.skip_unzbd:
    if args.unzbd:
        unzbd_exe = args.unzbd
        if not unzbd_exe.is_file():
            print("ERROR: No file at specified unzbd.exe path. Omit argument to download automatically")
            exit(1)
    else:
        unzbd_exe = next(args.data_dir.rglob("unzbd.exe"), Path())
        if not unzbd_exe.is_file():
            print("Downloading unzbd.exe from GitHub...")
            urllib.request.urlretrieve(MECH3AX_URL, args.data_dir / "mech3ax.zip")
            with ZipFile(args.data_dir / "mech3ax.zip") as z:
                z.extractall(args.data_dir)
            unzbd_exe = next(args.data_dir.rglob("unzbd.exe"))
    print(f"Using unzbd executable located at {unzbd_exe.resolve()}")

    print("Extracting planes.zbd...")
    sub.Popen([unzbd_exe, "cs", "gamez", str(args.cs / "ZBD" / "PLANES.ZBD"), str(unzbd_dir / "planes.zip")]).communicate()

    print("Extracting gamez.zbd...")
    for c in CHAPTERS:
        gamez_path = args.cs / "ZBD" / c / "gamez.zbd"
        sub.Popen([unzbd_exe, "cs", "gamez", str(gamez_path), str(unzbd_dir / f"{c}.zip")]).communicate()

    print("Extracting texture.zbd...")
    with ZipFile(unzbd_dir / "textures.zip", "w") as agg_zip:
        for f in args.cs.rglob("texture.zbd"):
            zip_path = unzbd_dir / f"{f.parent.name}_textures.zip"
            sub.Popen([unzbd_exe, "cs", "textures", f, str(zip_path)]).communicate()
            with ZipFile(zip_path) as chapter_zip:
                for texture_name in chapter_zip.namelist():
                    if texture_name not in agg_zip.namelist():
                        agg_zip.writestr(texture_name, chapter_zip.read(texture_name))
    

if not args.skip_planes:
    print("Generating plane .blends...")
    print(f"Using blender executable located at {args.blender}")

    with ZipFile(str(unzbd_dir / "planes.zip")) as level:
        with level.open("nodes.json") as f:
            nodes_json = json.load(f)

    roots = []
    for i, n in enumerate(nodes_json):
        v = next(iter(n.values()))
        if v["parent"] is None:
            roots.append((i, v["name"]))

    for i, name in roots:
        print(f"Generating {name}.blend...")
        sub.Popen([args.blender] + BLENDER_ARGS + ["plane2blend.py", "--", str(unzbd_dir), str(args.blend_dir), str(i)]).communicate()

if not args.skip_levels:
    print("Generating level .blends...")

    for c in CHAPTERS:
        print(f"Generating {c}.blend...")
        sub.Popen([args.blender] + BLENDER_ARGS + ["world2blend.py", "--", str(unzbd_dir), str(args.blend_dir), c]).communicate()
