from pathlib import Path
from PIL import Image, ImageDraw

p = Path(__file__).resolve().parent
for kind, suffix in [("BUILDINGS", "building"), ("SITES", "site")]:
    files = sorted(p.glob(f"*-{suffix}.png"))
    for n in range(0, len(files), 4):
        sheet = Image.new("RGB", (1800, 1400), "#f5f3ec")
        d = ImageDraw.Draw(sheet)
        for j, f in enumerate(files[n : n + 4]):
            im = Image.open(f)
            im.thumbnail((890, 650))
            x = (j % 2) * 900
            y = (j // 2) * 700
            d.text((x + 15, y + 8), f.stem, fill="#243b45")
            sheet.paste(im, (x, y + 30))
        sheet.save(p / f"{kind}_{n // 4 + 1:02}.png")
