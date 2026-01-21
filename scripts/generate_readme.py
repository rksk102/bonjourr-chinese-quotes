from __future__ import annotations
import csv
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

def count_rows(csv_file: Path) -> int:
    with csv_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return 0

    header = [c.strip().lower() for c in rows[0]]
    has_header = any(k in header for k in ("quote", "text", "author", "content"))
    return max(0, len(rows) - (1 if has_header else 0))

def main() -> None:
    repo = os.getenv("GITHUB_REPOSITORY", "YOUR_GITHUB_NAME/bonjourr-chinese-quotes")
    branch = os.getenv("DEFAULT_BRANCH", "main")

    csv_rel = os.getenv("QUOTES_CSV", "quotes.csv")
    csv_path = Path(csv_rel)
    readme_path = Path("README.md")

    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{csv_rel}"
    jsdelivr = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{csv_rel}"
    ghproxy = f"https://ghproxy.com/{raw}"

    n = count_rows(csv_path)

    now_utc = datetime.now(timezone.utc)
    now_cn = now_utc.astimezone(timezone(timedelta(hours=8)))

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
