import argparse
import base64
import os
import sys
from io import BytesIO
from pathlib import Path

import requests
import yaml
from PIL import Image

from compose import compose

ROOT = Path(__file__).resolve().parent
SIZES = ("1024x1536", "1024x1024")
REQUIRED = (
    "title",
    "subtitle",
    "intro",
    "sections",
    "catalog_title",
    "catalog",
    "illustrations",
)


def load_env(path):
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def build_prompt(content):
    objects = ", ".join(str(item) for item in content["illustrations"])
    return (
        "Keep the reference warm ivory watercolor paper, muted colors, "
        "hand-painted watercolor with colored pencil, imperfect handmade outlines, "
        "natural pigment bleeding, airy personal journal illustration. "
        "Keep the same composition slots. "
        f"Replace the drawn objects with only these: {objects}. "
        "Drink or cup stays in the upper right. Stars stay down the right side. "
        "Fruit basket stays in the lower left. Small plants stay at the bottom right. "
        "Leave the left column and the catalog band as blank paper. "
        "no typography, no letters, no Chinese characters, no Latin letters, no numbers, "
        "no watermark, no signature, no wechat, no account name, no QR code, "
        "no UI, no vector, no 3D, no photorealism."
    )


def load_content(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.exit("内容文件格式不对")
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        sys.exit("缺少字段: " + ", ".join(missing))
    for key in ("sections", "catalog", "illustrations"):
        if not isinstance(data[key], list) or not data[key]:
            sys.exit(f"{key} 需要非空列表")
    return data


def api_settings():
    key = os.environ.get("IMAGE_API_KEY", "").strip()
    base = os.environ.get("IMAGE_API_BASE", "").strip().rstrip("/")
    model = os.environ.get("IMAGE_MODEL", "").strip() or "gpt-image-1"
    ref_url = os.environ.get("IMAGE_REFERENCE_URL", "").strip() or os.environ.get("REFERENCE_IMAGE_URL", "").strip()
    if not key or not base:
        sys.exit("未设置 IMAGE_API_BASE 和 IMAGE_API_KEY")
    return key, base, model, ref_url


def image_from_body(body):
    if body.get("status") not in (None, "", "completed"):
        sys.exit(f"接口未完成: status={body.get('status')}")
    data = body.get("data") or []
    if not data or not isinstance(data[0], dict):
        sys.exit("接口没有返回图片")
    item = data[0]
    if item.get("b64_json"):
        return Image.open(BytesIO(base64.b64decode(item["b64_json"]))).convert("RGB")
    if item.get("url"):
        downloaded = requests.get(item["url"], timeout=120)
        downloaded.raise_for_status()
        return Image.open(BytesIO(downloaded.content)).convert("RGB")
    sys.exit("接口没有返回图片")


def fetch_plate(prompt, reference_file):
    key, base, model, ref_url = api_settings()
    endpoint = f"{base}/images/edits"
    last = None
    for size in SIZES:
        if ref_url:
            resp = requests.post(
                endpoint,
                headers={"Accept": "*/*", "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "prompt": prompt, "size": size, "images": [{"image_url": ref_url}]},
                timeout=300,
            )
        else:
            with reference_file.open("rb") as handle:
                resp = requests.post(
                    endpoint,
                    headers={"Accept": "*/*", "Authorization": f"Bearer {key}"},
                    data={"model": model, "prompt": prompt, "size": size},
                    files={"image": (reference_file.name, handle, "image/png")},
                    timeout=300,
                )
        last = resp
        if not resp.ok:
            continue
        return image_from_body(resp.json())
    detail = (last.text or "")[:400] if last is not None else ""
    sys.exit(f"接口失败: {detail}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("content")
    parser.add_argument("--plate", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    load_env(ROOT / ".env")
    content_path = Path(args.content)
    content = load_content(content_path)
    if args.dry_run or args.plate:
        plate_path = Path(args.plate) if args.plate else ROOT / "refs" / "style.png"
        if not plate_path.is_file():
            sys.exit(f"缺少参考图: {plate_path}")
        plate = Image.open(plate_path).convert("RGB")
    else:
        plate = fetch_plate(build_prompt(content), ROOT / "refs" / "style.png")
    out = Path(args.out) if args.out else ROOT / "output" / f"{content_path.stem}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    compose(plate, content, out)
    print(out)


if __name__ == "__main__":
    main()
