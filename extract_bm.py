from pathlib import Path
import struct

from PIL import Image

def save_image(fmt, size, bytes, filename):
    im = Image.frombytes(fmt, size, bytes)
    im.transpose(method=Image.Transpose.FLIP_TOP_BOTTOM).save(filename)

for path in Path().rglob("*.bm"):
    with open(path, "rb") as bm:
        (height, width) = struct.unpack("<HH", bm.read(4))
        num_pixels = width * height
        size = (width, height)

        save_image("RGB", size, bm.read(num_pixels*3), path.parent / (path.stem + "-base.png"))
        save_image("L", size, bm.read(num_pixels), path.parent / (path.stem + "-color1.png"))
        save_image("L", size, bm.read(num_pixels), path.parent / (path.stem + "-color2.png"))
        save_image("L", size, bm.read(num_pixels), path.parent / (path.stem + "-color3.png"))
        save_image("RGBA", size, bm.read(num_pixels*4), path.parent / (path.stem + "-specular.png"))
