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

def gha_error(msg: str, file: str | None = None) -> None:
    meta = f" file={file}" if file else ""
    print(f"::error{meta}::{msg}")

def read_text_smart(p: Path) -> str:
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

def count_rows(csv_file: Path) -> int:
    with csv_file.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return 0
    header = [c.strip().lower() for c in rows[0]]
    has_header = any(k in header for k in ("quote", "text", "author", "content"))
    return max(0, len(rows) - (1 if has_header else 0))

def main() -> int:
    gha_notice("SCRIPT_VERSION=2026-01-21-v3")

    repo = os.getenv("GITHUB_REPOSITORY", "YOUR_GITHUB_NAME/bonjourr-chinese-quotes")
    branch = os.getenv("DEFAULT_BRANCH", "main")
    csv_rel = os.getenv("QUOTES_CSV", "quotes.csv")
    csv_path = Path(csv_rel)
    readme_path = Path("README.md")

    gha_group("Inputs")
    print("repo       =", repo)
    print("branch     =", branch)
    print("quotes_csv =", csv_rel)
    print("cwd        =", Path.cwd())
    gha_endgroup()

    if not csv_path.exists():
        gha_error(f"CSV not found: {csv_rel}", file=csv_rel)
        return 2

    gha_group("CSV preview (first 5 lines)")
    print(preview_file(csv_path, 5))
    gha_endgroup()

    n = count_rows(csv_path)

    now_utc = datetime.now(timezone.utc)
    now_cn = now_utc.astimezone(timezone(timedelta(hours=8)))

    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{csv_rel}"
    jsdelivr = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{csv_rel}"
    ghproxy = f"https://ghproxy.com/{raw}"

    gha_group("Computed outputs")
    print("count_rows =", n)
    print("raw        =", raw)
    print("jsdelivr   =", jsdelivr)
    print("ghproxy    =", ghproxy)
    gha_endgroup()

    lines: list[str] = []
    lines += [
        "<!-- AUTO-GENERATED: DO NOT EDIT MANUALLY -->",
        '<div align="center">',
        "",
        "# bonjourr-chinese-quotes",
        "",
        "中文语录数据集（CSV）。本仓库通过 GitHub Actions 每日自动生成并更新本 README。",
        "",
        f'<a href="{raw}">',
        '  <img alt="Download GitHub Raw" src="https://img.shields.io/badge/Download-GitHub%20Raw-2ea44f">',
        "</a>",
        f'<a href="{jsdelivr}">',
        '  <img alt="Download jsDelivr" src="https://img.shields.io/badge/Download-jsDelivr-blue">',
        "</a>",
        f'<a href="{ghproxy}">',
        '  <img alt="Download ghproxy" src="https://img.shields.io/badge/Download-ghproxy-orange">',
        "</a>",
        "",
        "</div>",
        "",
        "---",
        "",
        f"## 下载（{csv_rel}）",
        "",
        f"- **GitHub Raw（原始）**：`{raw}`",
        f"- **jsDelivr（加速/CDN）**：`{jsdelivr}`",
        f"- **ghproxy（加速/代理）**：`{ghproxy}`",
        "",
        "---",
        "",
        "## 统计",
        "",
        f"- 语录条目数（按行粗略统计）：**{n}**",
        f'- 最近生成时间：**{now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")}** / **{now_cn.strftime("%Y-%m-%d %H:%M:%S UTC+8")}**',
        "",
        "---",
        "",
        "## 命令行下载",
        "",
        "```bash",
        f"curl -L -o quotes.csv {raw}",
        "# 或（CDN 加速）",
        f"curl -L -o quotes.csv {jsdelivr}",
        "```",
        "",
    ]

    readme_path.write_text("\n".join(lines), encoding="utf-8")
    gha_notice(f"README generated: {readme_path.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
