from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

def notice(msg: str) -> None:
    print(f"::notice::{msg}")

def group(title: str) -> None:
    print(f"::group::{title}")

def endgroup() -> None:
    print("::endgroup::")

def error(msg: str, file: str | None = None) -> None:
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

def append_step_summary(md: str) -> None:
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    Path(summary).write_text(md, encoding="utf-8")

def build_readme(repo: str, branch: str, csv_rel: str, rows: int, utc_str: str, cn_str: str) -> str:
    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{csv_rel}"
    jsdelivr = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{csv_rel}"
    ghproxy = f"https://ghproxy.com/{raw}"

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
        '  <img alt="GitHub Raw" src="https://img.shields.io/badge/Download-GitHub%20Raw-2ea44f">',
        "</a>",
        f'<a href="{jsdelivr}">',
        '  <img alt="jsDelivr" src="https://img.shields.io/badge/Download-jsDelivr-blue">',
        "</a>",
        f'<a href="{ghproxy}">',
        '  <img alt="ghproxy" src="https://img.shields.io/badge/Download-ghproxy-orange">',
        "</a>",
        "",
        "</div>",
        "",
        "---",
        "",
        "## 下载（quotes.csv）",
        "",
        f"- GitHub Raw：`{raw}`",
        f"- jsDelivr：`{jsdelivr}`",
        f"- ghproxy：`{ghproxy}`",
        "",
        "---",
        "",
        "## 数据概览",
        "",
        f"- 条目数（按行粗略统计）：**{rows}**",
        f"- 最近生成时间：**{utc_str}** / **{cn_str}**",
        "",
    ]
    return "\n".join(lines) + "\n"

def build_summary(repo: str, branch: str, csv_rel: str, rows: int, utc_str: str, cn_str: str) -> str:
    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{csv_rel}"
    jsdelivr = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{csv_rel}"
    ghproxy = f"https://ghproxy.com/{raw}"

    return "\n".join(
        [
            "## README 生成报告",
            "",
            f"- Repo: `{repo}`",
            f"- Branch: `{branch}`",
            f"- CSV: `{csv_rel}`",
            f"- Rows: **{rows}**",
            f"- Generated: **{utc_str}** / **{cn_str}**",
            "",
            "### 下载链接",
            f"- GitHub Raw: `{raw}`",
            f"- jsDelivr: `{jsdelivr}`",
            f"- ghproxy: `{ghproxy}`",
            "",
            "> 如果本次未提交，通常意味着 README 内容与上次一致（幂等更新）。",
            "",
        ]
    )

def main() -> int:
    notice("SCRIPT_VERSION=2026-01-21-v4")

    repo = os.getenv("GITHUB_REPOSITORY", "YOUR_GITHUB_NAME/bonjourr-chinese-quotes")
    branch = os.getenv("DEFAULT_BRANCH", "main")
    csv_rel = os.getenv("QUOTES_CSV", "quotes.csv")

    csv_path = Path(csv_rel)
    readme_path = Path("README.md")

    group("Inputs")
    print("repo       =", repo)
    print("branch     =", branch)
    print("quotes_csv =", csv_rel)
    print("cwd        =", Path.cwd())
    endgroup()

    if not csv_path.exists():
        error(f"CSV not found: {csv_rel}", file=csv_rel)
        append_step_summary("\n".join(["## README 生成失败", "", f"- 找不到 CSV：`{csv_rel}`", ""]))
        return 2

    group("CSV preview (first 5 lines)")
    print(preview_file(csv_path, 5))
    endgroup()

    rows = count_rows(csv_path)

    now_utc = datetime.now(timezone.utc)
    now_cn = now_utc.astimezone(timezone(timedelta(hours=8)))
    utc_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    cn_str = now_cn.strftime("%Y-%m-%d %H:%M:%S UTC+8")

    readme = build_readme(repo, branch, csv_rel, rows, utc_str, cn_str)
    readme_path.write_text(readme, encoding="utf-8")

    append_step_summary(build_summary(repo, branch, csv_rel, rows, utc_str, cn_str))
    notice(f"README generated: {readme_path.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
