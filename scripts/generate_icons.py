"""
generate_icons.py — Generate 96x96 dual-color PNG icons for AISmartBuild pyRevit buttons.

Color scheme:
  PRIMARY (deep blue):  #1E3A5F = RGB(30, 58, 95)
  ACCENT  (orange):     #FF6D00 = RGB(255, 109, 0)
  Background: transparent RGBA
"""

import os
from PIL import Image, ImageDraw

# ─── Color constants ────────────────────────────────────────────────────────
PRIMARY = (30, 58, 95, 255)    # deep blue, fully opaque
ACCENT  = (255, 109, 0, 255)   # orange, fully opaque
BG      = (0, 0, 0, 0)         # transparent background

SIZE = 96  # icon canvas size in pixels

# ─── Output paths ────────────────────────────────────────────────────────────
BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "AISmartBuild.extension",
    "AISmartBuild.tab",
)

ICONS = {
    "SmartChat":     os.path.join(BASE, "AIChat.panel",      "SmartChat.pushbutton"),
    "ExcelImport":   os.path.join(BASE, "FrameModel.panel",  "ExcelImport.pushbutton"),
    "GenerateFrame": os.path.join(BASE, "FrameModel.panel",  "GenerateFrame.pushbutton"),
    "ModifyElement": os.path.join(BASE, "ElementOps.panel",  "ModifyElement.pushbutton"),
    "DeleteElement": os.path.join(BASE, "ElementOps.panel",  "DeleteElement.pushbutton"),
    "ExportModel":   os.path.join(BASE, "DataIO.panel",      "ExportModel.pushbutton"),
    "About":         os.path.join(BASE, "Help.panel",        "About.pushbutton"),
}


# ─── Helper: new blank canvas ────────────────────────────────────────────────
def new_canvas():
    img = Image.new("RGBA", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    return img, draw


# ─── 1. SmartChat — chat bubble + AI sparkle ────────────────────────────────
def draw_smart_chat():
    img, draw = new_canvas()

    # Chat bubble body (rounded rectangle, deep blue)
    bubble_box = [10, 18, 78, 68]
    draw.rounded_rectangle(bubble_box, radius=12, fill=PRIMARY)

    # Bubble tail — small triangle at bottom-left
    tail = [(18, 65), (12, 80), (32, 65)]
    draw.polygon(tail, fill=PRIMARY)

    # Three speech dots inside the bubble (white)
    DOT = (255, 255, 255, 220)
    for cx in [26, 44, 62]:
        draw.ellipse([cx - 4, 39, cx + 4, 47], fill=DOT)

    # Sparkle star (orange) — top-right corner
    # Draw a 4-point star via two overlaid polygons
    cx, cy, r_out, r_in = 72, 24, 13, 5
    import math
    points = []
    for i in range(8):
        angle = math.radians(i * 45 - 90)
        r = r_out if i % 2 == 0 else r_in
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=ACCENT)

    return img


# ─── 2. ExcelImport — spreadsheet grid + upward arrow ───────────────────────
def draw_excel_import():
    img, draw = new_canvas()

    # Spreadsheet frame (deep blue outline)
    frame = [10, 22, 70, 80]
    draw.rounded_rectangle(frame, radius=4, outline=PRIMARY, width=3, fill=(30, 58, 95, 40))

    # Horizontal lines inside the grid
    for y in [38, 52, 66]:
        draw.line([(12, y), (68, y)], fill=PRIMARY, width=2)

    # Vertical divider inside the grid
    draw.line([(35, 24), (35, 78)], fill=PRIMARY, width=2)

    # Upward arrow (orange) — right side, overlapping the grid
    ax = 80
    # Arrow shaft
    draw.line([(ax, 72), (ax, 36)], fill=ACCENT, width=4)
    # Arrowhead
    draw.polygon([(ax - 9, 42), (ax, 22), (ax + 9, 42)], fill=ACCENT)

    return img


# ─── 3. GenerateFrame — 3D cube + lightning bolt ────────────────────────────
def draw_generate_frame():
    img, draw = new_canvas()

    # 3D box — isometric-style: front face, top face, right face
    # Front face (filled deep blue)
    front = [(16, 46), (16, 80), (56, 80), (56, 46)]
    draw.polygon(front, fill=PRIMARY)

    # Top face (lighter blue tint via alpha)
    top = [(16, 46), (36, 28), (76, 28), (56, 46)]
    draw.polygon(top, fill=(30, 58, 95, 200))

    # Right face (even lighter)
    right = [(56, 46), (76, 28), (76, 62), (56, 80)]
    draw.polygon(right, fill=(30, 58, 95, 140))

    # Outline edges for crispness
    for seg in [
        [(16, 46), (16, 80)], [(16, 80), (56, 80)], [(56, 80), (56, 46)],
        [(56, 46), (76, 28)], [(76, 28), (76, 62)], [(76, 62), (56, 80)],
        [(16, 46), (36, 28)], [(36, 28), (76, 28)], [(56, 46), (36, 28)],
    ]:
        draw.line(seg, fill=PRIMARY, width=2)

    # Lightning bolt (orange) — centered on front face
    bolt = [
        (38, 48), (30, 62), (37, 62), (34, 78), (48, 60), (40, 60), (46, 48)
    ]
    draw.polygon(bolt, fill=ACCENT)

    return img


# ─── 4. ModifyElement — pencil diagonal + orange tip ────────────────────────
def draw_modify_element():
    img, draw = new_canvas()

    # Pencil body — a thick parallelogram drawn as polygon
    # Pencil oriented diagonally (bottom-left to top-right)
    # Body rectangle
    body = [
        (20, 72), (26, 78),   # bottom of pencil (eraser end)
        (72, 26), (66, 20),   # top of pencil (tip direction)
    ]
    draw.polygon(body, fill=PRIMARY)

    # Tip triangle (orange) at top-right
    tip = [(66, 20), (72, 26), (82, 10)]
    draw.polygon(tip, fill=ACCENT)

    # Eraser band (white stripe near bottom)
    eraser_band = [(20, 72), (26, 78), (30, 74), (24, 68)]
    draw.polygon(eraser_band, fill=(200, 200, 200, 220))

    # Pencil edge highlight lines
    draw.line([(20, 72), (72, 26)], fill=(255, 255, 255, 80), width=2)

    # Small edit lines below-left of pencil (orange, suggest writing)
    for i, (x1, y1, x2, y2) in enumerate([
        (8, 80, 28, 80),
        (8, 86, 22, 86),
    ]):
        draw.line([(x1, y1), (x2, y2)], fill=ACCENT, width=3)

    return img


# ─── 5. DeleteElement — trash can + X mark ──────────────────────────────────
def draw_delete_element():
    img, draw = new_canvas()

    # Trash can body (rounded rectangle outline, deep blue)
    body = [22, 36, 74, 84]
    draw.rounded_rectangle(body, radius=5, outline=PRIMARY, width=3,
                            fill=(30, 58, 95, 30))

    # Vertical lines inside body (recycle lines)
    for x in [36, 48, 60]:
        draw.line([(x, 44), (x, 76)], fill=PRIMARY, width=2)

    # Lid (horizontal bar across top)
    draw.rounded_rectangle([16, 28, 80, 38], radius=4, fill=PRIMARY)

    # Handle on lid
    draw.rounded_rectangle([38, 18, 58, 30], radius=4, outline=PRIMARY, width=3)

    # X mark inside the body (orange)
    draw.line([(32, 48), (64, 76)], fill=ACCENT, width=4)
    draw.line([(64, 48), (32, 76)], fill=ACCENT, width=4)

    return img


# ─── 6. ExportModel — document + download arrow ─────────────────────────────
def draw_export_model():
    img, draw = new_canvas()

    # Document body (rounded rectangle, deep blue fill light)
    doc = [14, 10, 68, 84]
    draw.rounded_rectangle(doc, radius=5, outline=PRIMARY, width=3,
                            fill=(30, 58, 95, 40))

    # Folded corner (top-right) — white triangle to simulate fold
    fold_size = 16
    fold = [(68 - fold_size, 10), (68, 10 + fold_size), (68 - fold_size, 10 + fold_size)]
    draw.polygon(fold, fill=(240, 240, 240, 220))
    # fold crease line
    draw.line([(68 - fold_size, 10), (68, 10 + fold_size)], fill=PRIMARY, width=2)

    # Horizontal lines on document (text lines, primary)
    for y in [36, 46, 56]:
        draw.line([(22, y), (60, y)], fill=PRIMARY, width=2)

    # Download arrow (orange) — bottom-right, pointing downward
    ax, ay = 78, 54
    # Arrow shaft going down
    draw.line([(ax, ay - 16), (ax, ay + 4)], fill=ACCENT, width=4)
    # Arrowhead pointing down
    draw.polygon([(ax - 9, ay), (ax, ay + 16), (ax + 9, ay)], fill=ACCENT)
    # Horizontal base line
    draw.line([(ax - 12, ay + 18), (ax + 12, ay + 18)], fill=ACCENT, width=3)

    return img


# ─── 7. About — circle with "i" ─────────────────────────────────────────────
def draw_about():
    img, draw = new_canvas()

    # Circle outline (deep blue)
    circle_box = [10, 10, 86, 86]
    draw.ellipse(circle_box, outline=PRIMARY, width=4)

    # "i" dot (orange, upper part)
    dot_box = [42, 24, 54, 36]
    draw.ellipse(dot_box, fill=ACCENT)

    # "i" stem (orange, lower part)
    draw.rounded_rectangle([42, 42, 54, 72], radius=4, fill=ACCENT)

    return img


# ─── Main: generate and save all icons ──────────────────────────────────────
DRAW_FUNCS = {
    "SmartChat":     draw_smart_chat,
    "ExcelImport":   draw_excel_import,
    "GenerateFrame": draw_generate_frame,
    "ModifyElement": draw_modify_element,
    "DeleteElement": draw_delete_element,
    "ExportModel":   draw_export_model,
    "About":         draw_about,
}


def main():
    generated = []
    errors = []

    for name, folder in ICONS.items():
        try:
            img = DRAW_FUNCS[name]()
            assert img.size == (SIZE, SIZE), f"Wrong size: {img.size}"
            assert img.mode == "RGBA", f"Wrong mode: {img.mode}"
            out_path = os.path.join(folder, "icon.png")
            img.save(out_path, "PNG")
            generated.append((name, out_path))
            print(f"  [OK] {name:20s} -> {out_path}")
        except Exception as exc:
            errors.append((name, str(exc)))
            print(f"  [ERR] {name}: {exc}")

    print(f"\nGenerated {len(generated)}/{len(ICONS)} icons.")
    if errors:
        print("Errors:")
        for n, e in errors:
            print(f"  {n}: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
