"""Draw the Lunae brand icons (custom_components/lunae/brand/icon.png, icon@2x.png).

Glyph: Material Design Icons `weather-moonset` by Pictogrammers
(Apache-2.0, see NOTICE), https://pictogrammers.com/library/mdi/icon/weather-moonset/ — redrawn from its
24x24 path geometry: a half disc (centre 12,12, r 5) over three bars with
round ends (x 2-22 / 4-20 / 6-18, each 2 units tall at y 12, 16, 20).
Dark-blue-to-black rounded square, ghostly white glyph with a soft glow.

    pip install pillow && python tools/make_brand.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).parents[1] / "custom_components" / "lunae" / "brand"
SS = 4  # supersampling factor

BG_TOP = (18, 30, 66)      # dark blue
BG_BOTTOM = (2, 3, 10)     # near black
GLYPH = (232, 238, 252)    # ghostly white
GLOW = (150, 175, 255)     # pale blue halo


def glyph_mask(size: int) -> Image.Image:
    scale = size * 0.80 / 24          # glyph is 20 units wide → ~67% of the icon
    ox = size / 2 - 12 * scale        # glyph bbox x 2..22 → centre 12
    oy = size / 2 - 14.5 * scale      # glyph bbox y 7..22 → centre 14.5

    def p(x: float, y: float) -> tuple[float, float]:
        return ox + x * scale, oy + y * scale

    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.pieslice([p(7, 7), p(17, 17)], 180, 360, fill=255)
    for x0, x1, y in ((2, 22, 12), (4, 20, 16), (6, 18, 20)):
        d.rounded_rectangle([p(x0, y), p(x1, y + 2)], radius=scale, fill=255)
    return mask


def render(px: int) -> Image.Image:
    size = px * SS
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        grad.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))
    bg = grad.resize((size, size))

    shape = Image.new("L", (size, size), 0)
    ImageDraw.Draw(shape).rounded_rectangle([0, 0, size - 1, size - 1], radius=size * 0.22, fill=255)

    mask = glyph_mask(size)
    halo = mask.filter(ImageFilter.GaussianBlur(size * 0.035)).point(lambda v: int(v * 0.75))
    img = Image.composite(Image.new("RGB", (size, size), GLOW), bg, halo)
    img = Image.composite(Image.new("RGB", (size, size), GLYPH), img, mask.point(lambda v: int(v * 0.92)))

    out = img.convert("RGBA")
    out.putalpha(shape)
    return out.resize((px, px), Image.LANCZOS)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, px in (("icon.png", 256), ("icon@2x.png", 512)):
        render(px).save(OUT / name, optimize=True)
        print(OUT / name)
