from __future__ import annotations

import csv
import hashlib
import os
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable

def notice(msg: str) -> None:
    print(f"::notice::{msg}")

def warn(msg: str) -> None:
    print(f"::warning::{msg}")

def error(msg: str, file: str | None = None) -> None:
    meta = f" file={file}" if file else ""
    print(f"::error{meta}::{msg}")

def group(title: str) -> None:
    print(f"::group::{title}")

def endgroup() -> None:
    print("::endgroup::")

def read_text_smart(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8-sig")

def append_step_summary(md: str) -> None:
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    Path(summary).write_text(md, encoding="utf-8")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def csv_rows(csv_path: Path) -> list[list[str]]:
    try:
        f = csv_path.open("r", encoding="utf-8", newline="")
    except UnicodeDecodeError:
        f = csv_path.open("r", encoding="utf-8-sig", newline="")
    with f:
        reader = csv.reader(f)
        return [r for r in reader if any(cell.strip() for cell in r)]

def detect_header(rows: list[list[str]]) -> tuple[bool, list[str]]:
    if not rows:
        return False, []
    header = [c.strip() for c in rows[0]]
    header_l = [c.strip().lower() for c in header]
    has_header = any(k in header_l for k in ("quote", "text", "author", "content", "from", "source", "出处"))
    return has_header, header

def safe_md_inline(s: str, limit: int = 180) -> str:
    x = (s or "").replace("\r", " ").replace("\n", " ").strip()
    if len(x) > limit:
        x = x[: limit - 1].rstrip() + "…"
    x = x.replace("|", "\\|")
    return x

def pick_sample_quote(rows: list[list[str]]) -> tuple[str, str]:
    if not rows:
        return "", ""
    has_header, header = detect_header(rows)
    data = rows[1:] if has_header and len(rows) >= 2 else rows[:]
    if not data:
        return "", ""

    seed = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rnd = random.Random(seed)
    row = rnd.choice(data)

    header_l = [h.strip().lower() for h in header] if has_header else []
    quote_idx = -1
    author_idx = -1
    if has_header:
        for i, h in enumerate(header_l):
            if h in ("quote", "text", "content", "语录", "句子"):
                quote_idx = i
            if h in ("author", "from", "source", "出处", "来源"):
                author_idx = i

    def get(i: int) -> str:
        if 0 <= i < len(row):
            return row[i].strip()
        return ""

    quote = get(quote_idx) if quote_idx != -1 else get(0)
    author = get(author_idx) if author_idx != -1 else (get(1) if len(row) > 1 else "")
    return quote, author

def build_links(repo: str, branch: str, csv_rel: str) -> dict[str, str]:
    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{csv_rel}"
    jsdelivr = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{csv_rel}"
    ghproxy = f"https://ghproxy.com/{raw}"
    return {"raw": raw, "jsdelivr": jsdelivr, "ghproxy": ghproxy}

def build_readme(
    repo: str,
    branch: str,
    csv_rel: str,
    rows_count: int,
    utc_str: str,
    cn_str: str,
    csv_sha: str,
    quote: str,
    author: str,
    links: dict[str, str],
) -> str:
    raw = links["raw"]
    jsd = links["jsdelivr"]
    ghp = links["ghproxy"]
    lines: list[str] = []
    lines += [
        "<!-- AUTO-GENERATED: DO NOT EDIT MANUALLY -->",
        '<div align="center">',
        "",
        "# bonjourr-chinese-quotes",
        "",
        "<p>中文语录数据集（CSV）。用于 Bonjourr/扩展等场景。</p>",
        "",
        # 下载按钮区
        '<p>',
        f'  <a href="{raw}"><img alt="GitHub Raw" src="https://img.shields.io/badge/Download-GitHub%20Raw-2ea44f"></a>',
        f'  <a href="{jsd}"><img alt="jsDelivr" src="https://img.shields.io/badge/Download-jsDelivr-2563eb"></a>',
        f'  <a href="{ghp}"><img alt="ghproxy" src="https://img.shields.io/badge/Download-ghproxy-f97316"></a>',
        "</p>",
        "",
        "</div>",
        "",
        "---",
        "",
        "## 下载（quotes.csv）",
        "",
        "<table>",
        "  <thead>",
        "    <tr><th>渠道</th><th>链接</th><th>说明</th></tr>",
        "  </thead>",
        "  <tbody>",
        f"    <tr><td><b>GitHub Raw</b></td><td><code>{raw}</code></td><td>官方原始链接，最稳定</td></tr>",
        f"    <tr><td><b>jsDelivr</b></td><td><code>{jsd}</code></td><td>CDN 加速，适合直连读取</td></tr>",
        f"    <tr><td><b>ghproxy</b></td><td><code>{ghp}</code></td><td>代理加速（可用性随部署波动）</td></tr>",
        "  </tbody>",
        "</table>",
        "",
        "> 建议：程序默认使用 **GitHub Raw**；访问受限时再切换至镜像。",
        "",
        "---",
        "",
        "## 数据概览",
        "",
        "<table>",
        "  <tbody>",
        f"    <tr><td>条目数（粗略）</td><td><b>{rows_count}</b></td></tr>",
        f"    <tr><td>最近生成</td><td><b>{utc_str}</b> / <b>{cn_str}</b></td></tr>",
        f"    <tr><td>CSV SHA-256</td><td><code>{csv_sha[:16]}…</code></td></tr>",
        "  </tbody>",
        "</table>",
        "",
    ]

    if quote.strip():
        lines += [
            "## 今日示例",
            "",
            "> " + safe_md_inline(quote, 240),
            "",
        ]
        if author.strip():
            lines += [f"- — {safe_md_inline(author, 80)}", ""]

    lines += [
        "---",
        "",
        "## 维护说明",
        "",
        "- README 由 GitHub Actions 每日自动生成；如内容无变化则不会产生提交。",
        "- 如需调整样式/统计项：修改 `scripts/generate_readme.py`。",
        "",
    ]
    return "\n".join(lines) + "\n"

def build_summary(
    repo: str,
    branch: str,
    csv_rel: str,
    rows_count: int,
    utc_str: str,
    cn_str: str,
    csv_sha: str,
    links: dict[str, str],
    changed: bool | None,
) -> str:
    raw = links["raw"]
    jsd = links["jsdelivr"]
    ghp = links["ghproxy"]

    badge = "✅" if changed else "🟦" if changed is False else "ℹ️"
    changed_text = "README 有变化，将提交" if changed else "README 无变化，跳过提交" if changed is False else "未检测变更"

    return "\n".join(
        [
            "## 生成报告（README 自动更新）",
            "",
            f"- 状态：{badge} {changed_text}",
            f"- Repo：`{repo}`",
            f"- Branch：`{branch}`",
            f"- CSV：`{csv_rel}`",
            f"- Rows：**{rows_count}**",
            f"- Generated：**{utc_str}** / **{cn_str}**",
            f"- CSV SHA-256：`{csv_sha}`",
            "",
            "### 下载链接",
            f"- GitHub Raw：`{raw}`",
            f"- jsDelivr：`{jsd}`",
            f"- ghproxy：`{ghp}`",
            "",
            "### 排错提示",
            "- 若一直显示“无变化”：说明生成出来的 README 与上次完全一致（正常）。",
            "- 若找不到 CSV：检查 `QUOTES_CSV` 路径/文件名大小写。",
            "",
        ]
    )

def main() -> int:
    notice("SCRIPT_VERSION=2026-01-21-v5")

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
        append_step_summary("\n".join(["## 生成失败", "", f"- 找不到 CSV：`{csv_rel}`", ""]))
        return 2

    rows = csv_rows(csv_path)
    has_header, header = detect_header(rows)
    data_rows = rows[1:] if has_header and len(rows) >= 2 else rows
    rows_count = len(data_rows)
    quote, author = pick_sample_quote(rows)
    now_utc = datetime.now(timezone.utc)
    now_cn = now_utc.astimezone(timezone(timedelta(hours=8)))
    utc_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    cn_str = now_cn.strftime("%Y-%m-%d %H:%M:%S UTC+8")
    csv_sha = sha256_file(csv_path)
    links = build_links(repo, branch, csv_rel)
    old = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    new = build_readme(repo, branch, csv_rel, rows_count, utc_str, cn_str, csv_sha, quote, author, links)
    readme_path.write_text(new, encoding="utf-8")
    changed = (old != new) if old else None
    append_step_summary(build_summary(repo, branch, csv_rel, rows_count, utc_str, cn_str, csv_sha, links, changed))

    group("CSV preview (first 3 lines)")
    print("\n".join(read_text_smart(csv_path).splitlines()[:3]) or "(empty)")
    endgroup()

    notice(f"README generated: {readme_path.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
