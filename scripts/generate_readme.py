# scripts/generate_readme.py
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

def gha_group(title: str) -> None:
    print(f"::group::{title}")

def gha_endgroup() -> None:
    print("::endgroup::")

def gha_notice(msg: str) -> None:
    print(f"::notice::{msg}")

def gha_warning(msg: str) -> None:
    print(f"::warning::{msg}")

def gha_error(
    msg: str,
    file: str | None = None,
    line: int | None = None,
    col: int | None = None,
) -> None:
    meta = []
    if file:
        meta.append(f"file={file}")
    if line is not None:
        meta.append(f"line={line}")
    if col is not None:
        meta.append(f"col={col}")
    prefix = f"::error {','.join(meta)}::" if meta else "::error::"
    print(prefix + msg)

def read_text_smart(p: Path) -> str:
    # 优先 utf-8；如遇 BOM 或编码问题再兜底
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8-sig")

def preview_file(p: Path, n: int = 5) -> str:
    lines = read_text_smart(p).splitlines()
    head = lines[:n]
    if not head:
        return "(empty)"
    return "\n".join(f"{i+1:>3}: {s}" for i, s in enumerate(head))

def list_workspace(depth: int = 2, per_dir: int = 200) -> None:
    # 简单目录列举，便于定位路径/文件名错误
    root = Path(".")
    if depth <= 0:
        return

    def walk(dir_path: Path, d: int) -> None:
        if d == 0:
            return
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except Exception:
            return
        shown = 0
        for it in items:
            print(it.as_posix())
            shown += 1
            if shown >= per_dir:
                print(f"... (truncated, showing first {per_dir} items)")
                break
            if it.is_dir():
                walk(it, d - 1)

    walk(root, depth)

def count_rows(csv_file: Path) -> int:
    # 统计 CSV 记录行数（尽量兼容带表头/不带表头）
    # 注意：对复杂 CSV（引号/逗号/换行）使用 csv.reader 更稳
    with csv_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = [r for r in reader if any(cell.strip() for cell in r)]

    if not rows:
        return 0

    header = [c.strip().lower() for c in rows[0]]
    has_header = any(k in header for k in ("quote", "text", "author", "content"))
    return max(0, len(rows) - (1 if has_header else 0))

def main() -> int:
    # 版本标记：确保你能从 Actions 日志确认跑的是新脚本
    gha_notice("SCRIPT_VERSION=2026-01-21-v2")

    repo = os.getenv("GITHUB_REPOSITORY", "YOUR_GITHUB_NAME/bonjourr-chinese-quotes")
    branch = os.getenv("DEFAULT_BRANCH", "main")
    csv_rel = os.getenv("QUOTES_CSV", "quotes.csv")  # 支持 src/quotes.csv
    csv_path = Path(csv_rel)
    readme_path = Path("README.md")

    gha_group("Inputs")
    print("repo        =", repo)
    print("branch      =", branch)
    print("quotes_csv  =", csv_rel)
    print("cwd         =", Path.cwd())
    gha_endgroup()

    if not csv_path.exists():
        gha_error(f"CSV not found: {csv_rel}", file=csv_rel)
        gha_group("Workspace files (depth=2)")
        list_workspace(depth=2)
        gha_endgroup()
        return 2

    gha_group("CSV preview (first 5 lines)")
    print(preview_file(csv_path, 5))
    gha_endgroup()

    try:
        n = count_rows(csv_path)
    except UnicodeDecodeError:
        gha_error(
            "Failed to read CSV as UTF-8. Please ensure quotes.csv is UTF-8 encoded.",
            file=csv_rel,
        )
        return 3
    except Exception as e:
        gha_error(f"Failed to parse CSV: {e}", file=csv_rel)
        return 4

    now_utc = datetime.now(timezone.utc)
    now_cn = now_utc.astimezone(timezone(timedelta(hours=8)))

    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{csv_rel}"
    jsdelivr = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{csv_rel}"
    ghproxy = f"https://ghproxy.com/{raw}"

    gha_group("Computed outputs")
    print("count_rows  =", n)
    print("raw         =", raw)
    print("jsdelivr    =", jsdelivr)
    print("ghproxy     =", ghproxy)
    gha_endgroup()

    md = f"""<!-- AUTO-GENERATED: DO NOT EDIT MANUALLY -->
<div align="center">

# bonjourr-chinese-quotes

中文语录数据集（CSV）。本仓库通过 GitHub Actions 每日自动生成并更新本 README。

<a href="{raw}">
  <img alt="Download GitHub Raw" src="https://img.shields.io/badge/Download-GitHub%20Raw-2ea44f">
</a>
<a href="{jsdelivr}">
  <img alt="Download jsDelivr" src="https://img.shields.io/badge/Download-jsDelivr-blue">
</a>
<a href="{ghproxy}">
  <img alt="Download ghproxy" src="https://img.shields.io/badge/Download-ghproxy-orange">
</a>

</div>

---

## 下载（{csv_rel}）

- **GitHub Raw（原始）**：`{raw}`
- **jsDelivr（加速/CDN）**：`{jsdelivr}`
- **ghproxy（加速/代理）**：`{ghproxy}`

---

## 统计

- 语录条目数（按行粗略统计）：**{n}**
- 最近生成时间：**{now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")}** / **{now_cn.strftime("%Y-%m-%d %H:%M:%S UTC+8")}**

---

## 命令行下载

```bash
curl -L -o quotes.csv {raw}
# 或（CDN 加速）
curl -L -o quotes.csv {jsdelivr}
readme_path.write_text(md, encoding="utf-8")
gha_notice(f"README generated: {readme_path.resolve()}")

return 0
if name == "main":
try:
raise SystemExit(main())
except Exception as e:
gha_error(f"Unhandled exception: {e}")
raise
