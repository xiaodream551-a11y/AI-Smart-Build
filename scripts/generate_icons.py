"""
generate_icons.py — Generate 96x96 dual-color PNG icons for AISmartBuild pyRevit buttons.

Color scheme:
  PRIMARY (deep blue):  #1E3A5F = RGB(30, 58, 95)
  ACCENT  (orange):     #FF6D00 = RGB(255, 109, 0)
  Background: transparent RGBA

Dark mode variants use lighter colors suited for dark backgrounds.
4x supersampling: draw at 384x384, downscale to 96x96 with LANCZOS for antialiasing.
"""

import os
import math
from PIL import Image, ImageDraw

# ─── Color constants ────────────────────────────────────────────────────────
PRIMARY = (30, 58, 95, 255)    # deep blue, fully opaque
ACCENT  = (255, 109, 0, 255)   # orange, fully opaque
BG      = (0, 0, 0, 0)         # transparent background

# Dark mode variants (lighter colors for dark backgrounds)
PRIMARY_DARK = (200, 215, 235, 255)   # light blue-gray for dark backgrounds
ACCENT_DARK  = (255, 140, 40, 255)    # slightly lighter orange for dark mode

SIZE = 96  # final icon size in pixels

# ─── Supersampling constants ─────────────────────────────────────────────────
RENDER_SCALE = 4
RENDER_SIZE  = SIZE * RENDER_SCALE  # 384

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
    "Settings":      os.path.join(BASE, "Help.panel",        "Settings.pushbutton"),
}


# ─── Helper: new blank canvas at render resolution ───────────────────────────
def new_canvas():
    img = Image.new("RGBA", (RENDER_SIZE, RENDER_SIZE), BG)
    draw = ImageDraw.Draw(img)
    return img, draw


# ─── 1. SmartChat — chat bubble + AI sparkle ────────────────────────────────
def draw_smart_chat(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK  if dark else ACCENT
    S = RENDER_SCALE

    # Chat bubble body (rounded rectangle)
    bubble_box = [10*S, 18*S, 78*S, 68*S]
    draw.rounded_rectangle(bubble_box, radius=12*S, fill=p)

    # Bubble tail — small triangle at bottom-left
    tail = [(18*S, 65*S), (12*S, 80*S), (32*S, 65*S)]
    draw.polygon(tail, fill=p)

    # Three speech dots inside the bubble
    dot_color = (60, 60, 80, 220) if dark else (255, 255, 255, 220)
    for cx in [26*S, 44*S, 62*S]:
        draw.ellipse([cx - 4*S, 39*S, cx + 4*S, 47*S], fill=dot_color)

    # Sparkle star (accent) — top-right corner
    # Draw a 4-point star via two overlaid polygons
    scx, scy, r_out, r_in = 72*S, 24*S, 13*S, 5*S
    points = []
    for i in range(8):
        angle = math.radians(i * 45 - 90)
        r = r_out if i % 2 == 0 else r_in
        points.append((scx + r * math.cos(angle), scy + r * math.sin(angle)))
    draw.polygon(points, fill=a)

    return img


# ─── 2. ExcelImport — spreadsheet grid + upward arrow ───────────────────────
def draw_excel_import(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK  if dark else ACCENT
    S = RENDER_SCALE

    # Spreadsheet frame (outline)
    frame = [10*S, 22*S, 70*S, 80*S]
    draw.rounded_rectangle(frame, radius=4*S, outline=p, width=3*S,
                            fill=(30, 58, 95, 40))

    # Horizontal lines inside the grid
    for y in [38*S, 52*S, 66*S]:
        draw.line([(12*S, y), (68*S, y)], fill=p, width=2*S)

    # Vertical divider inside the grid
    draw.line([(35*S, 24*S), (35*S, 78*S)], fill=p, width=2*S)

    # Upward arrow (accent) — right side, overlapping the grid
    ax = 80*S
    # Arrow shaft
    draw.line([(ax, 72*S), (ax, 36*S)], fill=a, width=4*S)
    # Arrowhead
    draw.polygon([(ax - 9*S, 42*S), (ax, 22*S), (ax + 9*S, 42*S)], fill=a)

    return img


# ─── 3. GenerateFrame — 3D cube + lightning bolt ────────────────────────────
def draw_generate_frame(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK  if dark else ACCENT
    S = RENDER_SCALE

    # Front face
    pr, pg, pb, _ = p
    front = [(16*S, 46*S), (16*S, 80*S), (56*S, 80*S), (56*S, 46*S)]
    draw.polygon(front, fill=p)

    # Top face (lighter alpha)
    top = [(16*S, 46*S), (36*S, 28*S), (76*S, 28*S), (56*S, 46*S)]
    draw.polygon(top, fill=(pr, pg, pb, 200))

    # Right face (even lighter)
    right = [(56*S, 46*S), (76*S, 28*S), (76*S, 62*S), (56*S, 80*S)]
    draw.polygon(right, fill=(pr, pg, pb, 140))

    # Outline edges for crispness
    for seg in [
        [(16*S, 46*S), (16*S, 80*S)], [(16*S, 80*S), (56*S, 80*S)], [(56*S, 80*S), (56*S, 46*S)],
        [(56*S, 46*S), (76*S, 28*S)], [(76*S, 28*S), (76*S, 62*S)], [(76*S, 62*S), (56*S, 80*S)],
        [(16*S, 46*S), (36*S, 28*S)], [(36*S, 28*S), (76*S, 28*S)], [(56*S, 46*S), (36*S, 28*S)],
    ]:
        draw.line(seg, fill=p, width=2*S)

    # Lightning bolt (accent) — centered on front face
    bolt = [
        (38*S, 48*S), (30*S, 62*S), (37*S, 62*S), (34*S, 78*S),
        (48*S, 60*S), (40*S, 60*S), (46*S, 48*S)
    ]
    draw.polygon(bolt, fill=a)

    return img


# ─── 4. ModifyElement — pencil diagonal + orange tip ────────────────────────
def draw_modify_element(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK  if dark else ACCENT
    S = RENDER_SCALE

    # Pencil body — a thick parallelogram drawn as polygon
    body = [
        (20*S, 72*S), (26*S, 78*S),   # bottom of pencil (eraser end)
        (72*S, 26*S), (66*S, 20*S),   # top of pencil (tip direction)
    ]
    draw.polygon(body, fill=p)

    # Tip triangle (accent) at top-right
    tip = [(66*S, 20*S), (72*S, 26*S), (82*S, 10*S)]
    draw.polygon(tip, fill=a)

    # Eraser band (light stripe near bottom)
    eraser_band = [(20*S, 72*S), (26*S, 78*S), (30*S, 74*S), (24*S, 68*S)]
    draw.polygon(eraser_band, fill=(200, 200, 200, 220))

    # Pencil edge highlight line — white in light mode, transparent in dark mode
    highlight_color = (255, 255, 255, 0) if dark else (255, 255, 255, 80)
    draw.line([(20*S, 72*S), (72*S, 26*S)], fill=highlight_color, width=2*S)

    # Small edit lines below-left of pencil (accent, suggest writing)
    for x1, y1, x2, y2 in [
        (8, 80, 28, 80),
        (8, 86, 22, 86),
    ]:
        draw.line([(x1*S, y1*S), (x2*S, y2*S)], fill=a, width=3*S)

    return img


# ─── 5. DeleteElement — trash can + X mark ──────────────────────────────────
def draw_delete_element(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK  if dark else ACCENT
    S = RENDER_SCALE

    # Trash can body (rounded rectangle outline)
    body_fill = (200, 215, 235, 30) if dark else (30, 58, 95, 30)
    body = [22*S, 36*S, 74*S, 84*S]
    draw.rounded_rectangle(body, radius=5*S, outline=p, width=3*S, fill=body_fill)

    # Vertical lines inside body (recycle lines)
    for x in [36*S, 48*S, 60*S]:
        draw.line([(x, 44*S), (x, 76*S)], fill=p, width=2*S)

    # Lid (horizontal bar across top)
    draw.rounded_rectangle([16*S, 28*S, 80*S, 38*S], radius=4*S, fill=p)

    # Handle on lid
    draw.rounded_rectangle([38*S, 18*S, 58*S, 30*S], radius=4*S, outline=p, width=3*S)

    # X mark inside the body (accent)
    draw.line([(32*S, 48*S), (64*S, 76*S)], fill=a, width=4*S)
    draw.line([(64*S, 48*S), (32*S, 76*S)], fill=a, width=4*S)

    return img


# ─── 6. ExportModel — document + download arrow ─────────────────────────────
def draw_export_model(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK  if dark else ACCENT
    S = RENDER_SCALE

    # Document body (rounded rectangle, light fill)
    doc = [14*S, 10*S, 68*S, 84*S]
    draw.rounded_rectangle(doc, radius=5*S, outline=p, width=3*S,
                            fill=(30, 58, 95, 40))

    # Folded corner (top-right) — light triangle to simulate fold
    fold_size = 16*S
    fold = [(68*S - fold_size, 10*S), (68*S, 10*S + fold_size),
            (68*S - fold_size, 10*S + fold_size)]
    draw.polygon(fold, fill=(240, 240, 240, 220))
    # fold crease line
    draw.line([(68*S - fold_size, 10*S), (68*S, 10*S + fold_size)], fill=p, width=2*S)

    # Horizontal lines on document (text lines)
    for y in [36*S, 46*S, 56*S]:
        draw.line([(22*S, y), (60*S, y)], fill=p, width=2*S)

    # Download arrow (accent) — bottom-right, pointing downward
    ax, ay = 78*S, 54*S
    # Arrow shaft going down
    draw.line([(ax, ay - 16*S), (ax, ay + 4*S)], fill=a, width=4*S)
    # Arrowhead pointing down
    draw.polygon([(ax - 9*S, ay), (ax, ay + 16*S), (ax + 9*S, ay)], fill=a)
    # Horizontal base line
    draw.line([(ax - 12*S, ay + 18*S), (ax + 12*S, ay + 18*S)], fill=a, width=3*S)

    return img


# ─── 7. About — circle with "i" ─────────────────────────────────────────────
def draw_about(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK  if dark else ACCENT
    S = RENDER_SCALE

    # Circle outline
    draw.ellipse([10*S, 10*S, 86*S, 86*S], outline=p, width=4*S)

    # "i" dot (accent, upper part)
    draw.ellipse([42*S, 24*S, 54*S, 36*S], fill=a)

    # "i" stem (accent, lower part)
    draw.rounded_rectangle([42*S, 42*S, 54*S, 72*S], radius=4*S, fill=a)

    return img


# ─── 8. Settings — gear icon with orange accent ─────────────────────────────
def draw_settings(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK if dark else ACCENT
    S = RENDER_SCALE
    # Outer gear: circle with teeth
    cx, cy = 48*S, 48*S
    # Gear body
    draw.ellipse([28*S, 28*S, 68*S, 68*S], fill=p)
    # Inner circle (cut-out effect — use background or lighter color)
    inner_color = (240, 240, 240, 255) if not dark else (60, 60, 80, 255)
    draw.ellipse([36*S, 36*S, 60*S, 60*S], fill=inner_color)
    # Gear teeth (8 rectangles around the circle)
    for i in range(8):
        angle = math.radians(i * 45)
        tx = cx + int(22*S * math.cos(angle))
        ty = cy + int(22*S * math.sin(angle))
        draw.ellipse([tx-5*S, ty-5*S, tx+5*S, ty+5*S], fill=p)
    # Orange center dot
    draw.ellipse([44*S, 44*S, 52*S, 52*S], fill=a)
    # Small orange slider lines at bottom-right
    for y_offset in [0, 8]:
        y = (72 + y_offset) * S
        draw.line([(58*S, y), (86*S, y)], fill=a, width=3*S)
        draw.ellipse([(68-3)*S, y-3*S, (68+3)*S, y+3*S], fill=a)
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
    "Settings":      draw_settings,
}


def main():
    generated = []
    errors = []

    for name, folder in ICONS.items():
        try:
            draw_fn = DRAW_FUNCS[name]
            # Normal icon
            img = draw_fn(dark=False)
            img = img.resize((SIZE, SIZE), Image.LANCZOS)
            assert img.size == (SIZE, SIZE)
            out_path = os.path.join(folder, "icon.png")
            img.save(out_path, "PNG")
            # Dark icon
            img_dark = draw_fn(dark=True)
            img_dark = img_dark.resize((SIZE, SIZE), Image.LANCZOS)
            dark_path = os.path.join(folder, "icon_dark.png")
            img_dark.save(dark_path, "PNG")
            generated.append(name)
            print(f"  [OK] {name}")
        except Exception as exc:
            errors.append((name, str(exc)))
            print(f"  [ERR] {name}: {exc}")

    print(f"\nGenerated {len(generated)}/{len(ICONS)} icon pairs (normal + dark).")
    if errors:
        print("Errors:")
        for n, e in errors:
            print(f"  {n}: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
