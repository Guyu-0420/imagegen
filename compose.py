import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
PAPER = (246, 242, 232)
TEXT_MAIN = (41, 41, 41)
ACCENT_ORANGE = (235, 165, 58)
ACCENT_GREEN = (166, 198, 123)

KEEPOUTS = [
    (680, 90, 1080, 185),
    (640, 270, 1080, 560),
    (660, 530, 1080, 1140),
    (40, 1260, 780, 1720),
    (520, 1810, 1080, 1920),
]

TITLE_FONTS = [
    ("/System/Library/Fonts/Supplemental/STXingkai.ttf", 0),
    ("/Library/Fonts/华文行楷.ttf", 0),
    ("/System/Library/Fonts/Supplemental/Xingkai.ttc", 0),
    ("/System/Library/Fonts/Supplemental/HanziPen.ttc", 0),
    ("/System/Library/Fonts/HanziPen.ttc", 0),
    ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),
]
SUBTITLE_FONTS = [
    ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),
    ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),
]
BODY_FONTS = [
    ("/System/Library/Fonts/PingFang.ttc", 0),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 1),
]


def load_font(candidates, size):
    tried = []
    for path, index in candidates:
        tried.append(f"{path}#{index}")
        if not os.path.isfile(path):
            continue
        try:
            return ImageFont.truetype(path, size, index=index)
        except OSError:
            continue
    raise FileNotFoundError("未找到中文字体，已查找: " + ", ".join(tried))


def pieces(para):
    buf = ""
    for ch in para:
        if ord(ch) < 128 and not ch.isspace():
            buf += ch
            continue
        if buf:
            yield buf
            buf = ""
        yield ch
    if buf:
        yield buf


def wrap(text, font, max_width):
    lines = []
    for para in str(text).split("\n"):
        para = para.strip()
        if not para:
            continue
        line = ""
        for part in pieces(para):
            trial = line + part
            if font.getlength(trial) <= max_width:
                line = trial
                continue
            if line.strip():
                lines.append(line.rstrip())
            line = "" if part == " " else part
            while line and font.getlength(line) > max_width:
                cut = line
                while cut and font.getlength(cut) > max_width:
                    cut = cut[:-1]
                if not cut:
                    break
                lines.append(cut)
                line = line[len(cut):]
        if line.strip():
            lines.append(line.rstrip())
    return lines


def line_height(font):
    return int(font.size * 1.5)


def make_paper(size, base):
    noise = Image.effect_noise(size, 6).convert("L")
    channels = []
    for channel in base:
        channels.append(
            noise.point(lambda p, c=channel: max(0, min(255, c + (p - 128) // 12)))
        )
    return Image.merge("RGB", tuple(channels))


def sample_paper(plate):
    crop = plate.convert("RGB").crop((2, 2, 40, 40))
    pixels = [p for p in crop.getdata() if p[0] > 220]
    if not pixels:
        pixels = list(crop.getdata())
    mid = len(pixels) // 2
    sampled = tuple(sorted(p[i] for p in pixels)[mid] for i in range(3))
    if sampled[0] < 230:
        return PAPER
    return sampled


def erase_ink(image, box, paper_color, chroma_max=26, lum_max=170):
    x0, y0, x1, y1 = box
    pix = image.load()
    x1 = min(x1, image.width)
    y1 = min(y1, image.height)
    for y in range(max(0, y0), y1):
        for x in range(max(0, x0), x1):
            r, g, b = pix[x, y]
            chroma = max(r, g, b) - min(r, g, b)
            if chroma < chroma_max and (r + g + b) / 3 < lum_max:
                pix[x, y] = paper_color


def paste_plate(canvas, plate):
    scale = min(W / plate.width, H / plate.height)
    nw = max(1, round(plate.width * scale))
    nh = max(1, round(plate.height * scale))
    resized = plate.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas.paste(resized, ((W - nw) // 2, 0))


def cover(canvas, rects, paper):
    mask = Image.new("L", canvas.size, 0)
    draw = ImageDraw.Draw(mask)
    for x, y, w, h in rects:
        draw.rectangle((x, y, x + w, y + h), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(5))
    punch = ImageDraw.Draw(mask)
    for box in KEEPOUTS:
        punch.rectangle(box, fill=0)
    canvas.paste(paper, (0, 0), mask)


def draw_text(draw, text, font, color, box, align):
    x, y, w, h = box
    lines = wrap(text, font, w)
    lh = line_height(font)
    if lh * len(lines) > h:
        raise SystemExit(f"文字超出版心: {str(text).strip()[:12]}")
    for i, line in enumerate(lines):
        tw = font.getlength(line)
        tx = x if align == "left" else x + (w - tw) / 2
        draw.text((tx, y + i * lh), line, font=font, fill=color)


def hex_color(value, fallback):
    text = str(value or "").strip().lstrip("#")
    if len(text) != 6:
        return fallback
    try:
        return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return fallback


def font_spec(content):
    raw = content.get("fonts") or {}
    return raw if isinstance(raw, dict) else {}


BUNDLED_FONT = os.path.join(os.path.dirname(__file__), "fonts", "LXGWWenKai-Regular.ttf")


def resolve_fonts(content):
    spec = font_spec(content)
    defaults = {
        "title": (TITLE_FONTS, 52, ACCENT_ORANGE),
        "subtitle": (SUBTITLE_FONTS, 32, ACCENT_GREEN),
        "body": (BODY_FONTS, 24, TEXT_MAIN),
        "catalog": (TITLE_FONTS, 44, ACCENT_ORANGE),
        "caption": (BODY_FONTS, 20, TEXT_MAIN),
    }
    fonts = {}
    colors = {}
    for name, (candidates, size, color) in defaults.items():
        item = spec.get(name) or {}
        if not isinstance(item, dict):
            item = {}
        use_size = int(item.get("size") or size)
        if item.get("file"):
            fonts[name] = ImageFont.truetype(item["file"], use_size, index=int(item.get("index") or 0))
        elif os.path.isfile(BUNDLED_FONT):
            fonts[name] = ImageFont.truetype(BUNDLED_FONT, use_size)
        else:
            fonts[name] = load_font(candidates, use_size)
        colors[name] = hex_color(item.get("color"), color)
    return fonts, colors


def flow_sections(content, fonts, colors, blocks, y, bottom, width, x=206):
    for section in content["sections"]:
        text = str(section).strip()
        lh = line_height(fonts["body"])
        h = lh * max(1, len(wrap(text, fonts["body"], width)))
        if y + h > bottom:
            raise SystemExit("正文超出版心，请缩短 sections")
        blocks.append((text, fonts["body"], colors["body"], (x, y, width, h), "left"))
        y += h + 20
    return y


def flow_catalog(content, fonts, colors, blocks, title_box, y, bottom, width, x=200):
    blocks.append((content["catalog_title"], fonts["catalog"], colors["catalog"], title_box, "center"))
    for item in content["catalog"]:
        text = str(item).strip()
        lh = line_height(fonts["caption"])
        h = lh * max(1, len(wrap(text, fonts["caption"], width)))
        if y + h > bottom:
            raise SystemExit("目录超出版心，请缩短 catalog")
        blocks.append((text, fonts["caption"], colors["caption"], (x, y, width, h), "left"))
        y += h + 4
    return y


def layout(content, fonts, colors):
    name = str(content.get("template") or "journal")
    blocks = []
    if name == "journal":
        blocks.extend([
            (content["title"], fonts["title"], colors["title"], (248, 104, 360, 84), "left"),
            (content["subtitle"], fonts["subtitle"], colors["subtitle"], (214, 196, 380, 64), "left"),
            (content["intro"].strip(), fonts["body"], colors["body"], (206, 332, 360, 190), "left"),
        ])
        flow_sections(content, fonts, colors, blocks, 708, 900, 340)
        flow_catalog(content, fonts, colors, blocks, (190, 1008, 460, 72), 1092, 1240, 470)
    elif name == "steps":
        blocks.extend([
            (content["title"], fonts["title"], colors["title"], (206, 96, 420, 80), "left"),
            (content["subtitle"], fonts["subtitle"], colors["subtitle"], (206, 184, 420, 56), "left"),
        ])
        flow_sections(content, fonts, colors, blocks, 280, 980, 400)
        flow_catalog(content, fonts, colors, blocks, (190, 1000, 460, 72), 1084, 1240, 470)
    elif name == "note":
        blocks.extend([
            (content["title"], fonts["title"], colors["title"], (206, 110, 460, 96), "left"),
            (content["subtitle"], fonts["subtitle"], colors["subtitle"], (206, 214, 420, 60), "left"),
            (content["intro"].strip(), fonts["body"], colors["body"], (206, 300, 420, 360), "left"),
        ])
        flow_sections(content, fonts, colors, blocks, 700, 960, 400)
        flow_catalog(content, fonts, colors, blocks, (190, 992, 460, 72), 1076, 1240, 470)
    else:
        raise SystemExit("未知模板: " + name + "（可用 journal、steps、note）")
    return blocks


COVERS = {
    "journal": [
        (230, 96, 390, 90),
        (198, 184, 400, 78),
        (598, 190, 180, 62),
        (188, 310, 430, 220),
        (188, 688, 460, 200),
        (176, 990, 520, 250),
    ],
    "steps": [
        (188, 80, 460, 180),
        (188, 270, 460, 720),
        (176, 990, 520, 250),
    ],
    "note": [
        (188, 90, 500, 200),
        (188, 290, 480, 680),
        (176, 990, 520, 250),
    ],
}


def compose(plate, content, out_path):
    plate = plate.convert("RGB")
    base = sample_paper(plate)
    canvas = make_paper((W, H), base)
    paste_plate(canvas, plate)
    paper = make_paper((W, H), base)
    name = str(content.get("template") or "journal")
    if name not in COVERS:
        raise SystemExit("未知模板: " + name + "（可用 journal、steps、note）")
    cover(canvas, COVERS[name], paper)
    erase_ink(canvas, (600, 300, 820, 530), base)
    erase_ink(canvas, (530, 680, 660, 800), base)
    erase_ink(canvas, (520, 1816, W, H), base, chroma_max=18, lum_max=243)
    fonts, colors = resolve_fonts(content)
    draw = ImageDraw.Draw(canvas)
    for text, font, color, box, align in layout(content, fonts, colors):
        draw_text(draw, text, font, color, box, align)
    canvas.save(out_path, "PNG")
