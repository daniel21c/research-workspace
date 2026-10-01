# -*- coding: utf-8 -*-
"""PDF 쪽을 PNG 대조용 시트(2쪽씩)로 렌더링한다. 조판 확인용이며 audit/render/ 에 저장한다."""
from pathlib import Path
import fitz
from PIL import Image
PKG = Path(__file__).resolve().parents[1]
pdf = next((PKG / "manuscript").glob("*.pdf"))
out = PKG / "audit" / "render"; out.mkdir(exist_ok=True)
for f in out.glob("*.png"): f.unlink()
d = fitz.open(pdf); imgs = []
for pg in d:
    pm = pg.get_pixmap(dpi=85); imgs.append(Image.frombytes("RGB", (pm.width, pm.height), pm.samples))
for k in range(0, len(imgs), 2):
    pair = imgs[k:k + 2]; sheet = Image.new("RGB", (sum(i.width for i in pair), max(i.height for i in pair)), "white"); x = 0
    for im in pair: sheet.paste(im, (x, 0)); x += im.width
    sheet.save(out / f"sheet_{k // 2 + 1}.png")
print("pages", len(imgs), "sheets", (len(imgs) + 1) // 2)
