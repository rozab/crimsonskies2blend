import argparse
from pathlib import Path
import shutil
from zipfile import ZipFile

from PIL import Image, ImageChops, ImageColor

PLANE_PREFIXES = {
    "HOPLITE": "AGYRO",
    "BALMORAL": "BAL",
    "BLOODHAWK": "BLO",
    "BRIGAND": "BRI",
    "DEVASTATOR": "DEV",
    "FIREBRAND": "FIR",
    "FURY": "FUR",
    "HELLHOUND": "HEL",
    "KESTREL": "KES",
    "PEACEMAKER": "PEA",
    "WARHAWK": "WAR"
}

FACTION_COLORS = {
    "BLACKHAT": ("#B18242", "#774A2B", "#42270F"),
    "BLAKE": ("#95A3C3", "#59729F", "#E9E4F0"),
    "BLCKSWAN": ("#171715", "#302F27", "#C4C1BA"),
    "BRITISH": ("#B18242", "#302F27", "#FFFFFF"),
    "BROADWAY": ("#462884", "#191919", "#EEEA00"),
    "CCCP": ("#394044", "#DF0029", "#F3C200"),
    "FORTUNE": ("#DF0029", "#191919", "#FFFFFF"),
    "GERMAN": ("#60737E", "#191919", "#302F27"),
    "HOLLYWD": ("#6C66A9", "#462884", "#D4CAE1"),
    "HUGHES": ("#F3C200", "#191919", "#FFFFFF"),
    "ITSTAXI": ("#F9F400", "#FFFFFF", "#191919"),
    "MEDUSAS": ("#5F7D8F", "#290E15", "#8D895D"),
    "SACTRUST": ("#34266B", "#F3C200", "#171715"),
    "STUDIO": ("#205AA7", "#FFFFFF", "#191919")
}

def apply_color_mask(base, mask, color):
    color_fill = Image.new("RGB", mask.size, color)
    white_fill = Image.new("RGB", mask.size, "#ffffff")
    color_overlay = Image.composite(white_fill, color_fill, ImageChops.invert(mask))
    
    return ImageChops.multiply(base, color_overlay)

parser = argparse.ArgumentParser(description="Rewrite plane textures to a different faction")
parser.add_argument(
    "plane",
    type=lambda value: value.upper(),
    help=", ".join(PLANE_PREFIXES.keys()))
parser.add_argument(
    "faction",
    type=lambda value: value.upper(),
    help=", ".join(FACTION_COLORS.keys()))
parser.add_argument(
    "--data",
    metavar="FOLDER",
    dest="data_folder",
    default=Path("data"),
    type=lambda value: Path(value).resolve(strict=True),
    help="Folder with intermediate data")
parser.add_argument(
    "--colors",
    nargs=3,
    metavar='"#RRGGBB"',
    help="Override default faction colors")

args = parser.parse_args()

if args.plane not in PLANE_PREFIXES:
    print(f"ERROR: Plane must be one of {', '.join(PLANE_PREFIXES.keys())}")
    exit(1)

if args.faction not in FACTION_COLORS:
    print(f"ERROR: Faction must be one of {', '.join(FACTION_COLORS.keys())}")
    exit(1)

faction_dir = args.data_folder / "rof_output/ASSETS/GRAPHICS" / args.faction
if not faction_dir.is_dir():
    print(f"ERROR: Valid .rof output not found")
    exit(1)

if args.colors:
    try:
        args.colors = list(map(ImageColor.getrgb, args.colors))
    except ValueError:
        print("ERROR: Invalid custom colors")
        exit(1)

plane_prefix = PLANE_PREFIXES[args.plane]

textures = list(faction_dir.rglob(f"{plane_prefix}_*.bm"))

if not textures:
    print(f"ERROR: Invalid combination of plane and faction")
    exit(1)

with ZipFile(args.data_folder / "textures.zip") as z:
        z.extractall(args.data_folder / "textures")

for t in textures:
    base = Image.open(t.parent / (t.stem + "-base.png"))
    color1_mask = Image.open(t.parent / (t.stem + "-color1.png"))
    color2_mask = Image.open(t.parent / (t.stem + "-color2.png"))
    color3_mask = Image.open(t.parent / (t.stem + "-color3.png"))
    specular = Image.open(t.parent / (t.stem + "-specular.png"))

    if args.colors:
        colors = args.colors
    else:
        colors = FACTION_COLORS[args.faction]

    output = apply_color_mask(base, color1_mask, colors[0])
    output = apply_color_mask(output, color2_mask, colors[1])
    output = apply_color_mask(output, color3_mask, colors[2])
    output = output.convert("RGBA")
    output = Image.alpha_composite(output, specular)
    output = output.convert("RGB")

    with open(args.data_folder / "textures" / f"{t.stem.lower()}.png", "wb") as f:
        print(f"Saving {t.stem.lower()}.png")
        output.save(f, format="png")

shutil.make_archive(args.data_folder / "textures", "zip", args.data_folder / "textures")
