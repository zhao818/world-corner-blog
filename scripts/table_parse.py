"""
表格解析 CLI — 调用 table-parser 微服务将表格图片转为 Excel。

用法:
  python table_parse.py image.png                         # 单张 → Excel
  python table_parse.py img1.png img2.png                 # 批量 → 多 Sheet
  python table_parse.py image.png --mock                  # 模拟模式（无 API key）
  python table_parse.py image.png --url http://localhost:8000
  python table_parse.py --json data.json                  # JSON → Excel（无需服务）
  python table_parse.py --json data.json --title "报表"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("需要 requests 库: pip install requests", file=sys.stderr)
    sys.exit(1)

DEFAULT_URL = "http://localhost:8000"
SCRIPT_DIR = Path(__file__).parent


def _check_service(url: str) -> bool:
    try:
        r = requests.get(f"{url}/api/health", timeout=3)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


def upload_single(url: str, image_path: str, output: str | None = None,
                  mock: bool = False, no_header: bool = False) -> str:
    path = Path(image_path)
    if not path.exists():
        print(f"文件不存在: {image_path}", file=sys.stderr)
        sys.exit(1)

    params = {}
    if mock:
        params["use_mock"] = "true"
    if no_header:
        params["first_row_as_header"] = "false"

    with open(path, "rb") as f:
        r = requests.post(
            f"{url}/api/upload",
            params=params,
            files={"file": (path.name, f, _mime_type(path))},
            timeout=120,
        )
    r.raise_for_status()

    out = output or str(path.with_suffix(".xlsx"))
    with open(out, "wb") as f:
        f.write(r.content)
    print(f"✅ 已保存: {out}")
    return out


def upload_batch(url: str, image_paths: list[str], output: str = "batch.xlsx",
                 mock: bool = False) -> str:
    files = []
    for p in image_paths:
        path = Path(p)
        if not path.exists():
            print(f"文件不存在: {p}", file=sys.stderr)
            sys.exit(1)
        files.append(("files", (path.name, open(path, "rb"), _mime_type(path))))

    params = {"use_mock": "true"} if mock else {}

    try:
        r = requests.post(
            f"{url}/api/upload/batch",
            params=params,
            files=files,
            timeout=300,
        )
        r.raise_for_status()
    finally:
        for _, f in files:
            f[1].close()

    with open(output, "wb") as f:
        f.write(r.content)
    print(f"✅ 已保存: {output}")
    return output


def _mime_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }.get(ext, "application/octet-stream")


def json_to_excel(json_path: str, title: str | None = None,
                  sheet_name: str = "Sheet1", output: str | None = None):
    """JSON → Excel without needing the table-parser service running."""
    sys.path.insert(0, str(SCRIPT_DIR.parent / "table-parser-"))
    try:
        from app.excel_generator import generate_excel_simple
    except ImportError:
        print("错误: 找不到 app.excel_generator (需要 table-parser 仓库在相邻目录)",
              file=sys.stderr)
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    headers = data.get("headers", data.get("columns", []))
    rows = data.get("data_rows", data.get("rows", []))
    if not headers and rows:
        headers = rows[0]
        rows = rows[1:]

    buf = generate_excel_simple(
        headers=headers,
        data_rows=[[str(c) for c in row] for row in rows],
        sheet_name=sheet_name,
        title=title or data.get("title"),
    )
    out = output or str(Path(json_path).with_suffix(".xlsx"))
    with open(out, "wb") as f:
        f.write(buf.getvalue())
    print(f"✅ 已保存: {out}")
    return out


def main():
    parser = argparse.ArgumentParser(description="表格图片 → Excel")
    parser.add_argument("images", nargs="*", help="表格图片路径")
    parser.add_argument("--url", default=os.getenv("TABLE_PARSER_URL", DEFAULT_URL),
                        help=f"服务地址 (默认 {DEFAULT_URL})")
    parser.add_argument("--mock", action="store_true", help="模拟模式")
    parser.add_argument("--output", "-o", help="输出文件名")
    parser.add_argument("--no-header", action="store_true",
                        help="首行不做表头样式")
    parser.add_argument("--json", help="JSON 文件 → Excel（无需服务）")
    parser.add_argument("--title", help="JSON 模式下的表格标题")
    parser.add_argument("--sheet", default="Sheet1", help="Sheet 名称")
    args = parser.parse_args()

    # JSON mode (local, no service needed)
    if args.json:
        json_to_excel(args.json, title=args.title, sheet_name=args.sheet,
                      output=args.output)
        return

    if not args.images:
        parser.print_help()
        sys.exit(1)

    # Check service
    if not _check_service(args.url):
        print(f"⚠️  无法连接 table-parser 服务 ({args.url})", file=sys.stderr)
        print("   请先启动服务：", file=sys.stderr)
        print(f"   cd {Path(__file__).parent.parent / 'table-parser-'}", file=sys.stderr)
        print("   uvicorn app.main:app --reload --port 8000", file=sys.stderr)
        sys.exit(1)

    if len(args.images) == 1:
        upload_single(
            args.url, args.images[0],
            output=args.output,
            mock=args.mock,
            no_header=args.no_header,
        )
    else:
        upload_batch(
            args.url, args.images,
            output=args.output or "batch.xlsx",
            mock=args.mock,
        )


if __name__ == "__main__":
    main()
