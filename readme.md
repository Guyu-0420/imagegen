水彩手账长图。图片接口只画无字底图，中文用本地字体叠上。

风格由 `refs/style.png` 锁住。换物体只改 `illustrations`。版式用 `template`：`journal`、`steps`、`note`。字体默认是仓库里的霞鹜文楷，也可在 `fonts` 里改 `file` 和 `size`。

```bash
pip install -r requirements.txt
cp .env.example .env
python pipeline.py imagegen.yaml --dry-run
python pipeline.py imagegen.yaml
```

`IMAGE_REFERENCE_URL` 为空时，把本地参考图以文件上传到 `IMAGE_API_BASE/images/edits`。有公网地址时改走 JSON `images[].image_url`。

已有底图、只改字：

```bash
python pipeline.py imagegen.yaml --plate plate.png
```

`fonts` 每一项可以写 `file`、`index`、`size`、`color`。不写 `file` 时用仓库里的霞鹜文楷。
