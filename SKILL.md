---
name: watercolor-journal
description: >-
  Build a watercolor journal poster by splitting paint and Chinese text. The
  image API paints a text-free plate from refs/style.png; local fonts composite
  the copy. Use when the user asks for 水彩手账, 水彩出图, imagegen, a journal
  poster, or to change fruits, drinks, fonts, font sizes, or layout templates.
---

# Watercolor journal poster

Paint and type are separate. `pipeline.py` sends `refs/style.png` and the `illustrations` list to `{IMAGE_API_BASE}/images/edits` and keeps a text-free plate. `compose.py` draws the Chinese from the YAML with the bundled font. Do not draw the final poster with the chat image model.

## Edit the YAML, then run

Content file fields: `title`, `subtitle`, `intro`, `sections`, `catalog_title`, `catalog`, `illustrations`, optional `template` and `fonts`.

- Change objects only in `illustrations`. Keep one drink, one fruit basket, stars, and a small plant so the slots stay put.
- Set `template` to `journal`, `steps`, or `note`. Do not invent a new layout in the image prompt.
- Fonts default to `fonts/LXGWWenKai-Regular.ttf`. Each of `title`, `subtitle`, `body`, `catalog`, `caption` accepts `file`, `index`, `size`, `color`.

```bash
python pipeline.py imagegen.yaml --dry-run
python pipeline.py imagegen.yaml
python pipeline.py imagegen.yaml --plate plate.png --out output/poster.png
```

Run commands from the project directory. `--dry-run` and `--plate` skip the API and only composite text. A real run needs `IMAGE_API_BASE` and `IMAGE_API_KEY` in `.env`.

## API

`IMAGE_REFERENCE_URL` empty: upload `refs/style.png` as multipart to `{IMAGE_API_BASE}/images/edits`.

`IMAGE_REFERENCE_URL` set: JSON body `images: [{image_url}]`.

Never write API keys into the repo. Never commit `.env`. Never put a private gateway host or internal model name in source files.

## Style lock

The reference image decides paper, brush, and placement. The prompt may replace objects inside the existing slots. It must not add text, a watermark, or a new layout.
