from __future__ import annotations
import csv
import hashlib
import os
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

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

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def file_size_kb(p: Path) -> int:
    return int((p.stat().st_size + 1023) // 1024)

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
    has_header = any(k in header_l for k in ("quote", "text", "content", "author", "from", "source", "出处"))
    return has_header, header

def safe_md_inline(s: str, limit: int = 240) -> str:
    x = (s or "").replace("\r", " ").replace("\n", " ").strip()
    x = x.replace("|", "\\|")
    if len(x) > limit:
        x = x[: limit - 1].rstrip() + "…"
    return x

def build_links(repo: str, branch: str, csv_rel: str) -> dict[str, str]:
    raw = f"https://raw.githubusercontent.com/{repo}/{branch}/{csv_rel}"
    jsdelivr = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{csv_rel}"
    ghproxy = f"https://ghproxy.com/{raw}"
    blob = f"https://github.com/{repo}/blob/{branch}/{csv_rel}"
    return {"raw": raw, "jsdelivr": jsdelivr, "ghproxy": ghproxy, "blob": blob}

def pick_sample(rows: list[list[str]], prefer_daily: bool = True) -> tuple[str, str]:
    if not rows:
        return "", ""
    has_header, header = detect_header(rows)
    data = rows[1:] if has_header and len(rows) >= 2 else rows
    if not data:
        return "", ""

    seed = datetime.now(timezone.utc).strftime("%Y-%m-%d") if prefer_daily else "static"
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
        return row[i].strip() if 0 <= i < len(row) else ""

    quote = get(quote_idx) if quote_idx != -1 else get(0)
    author = get(author_idx) if author_idx != -1 else (get(1) if len(row) > 1 else "")
    return quote, author

def write_step_summary(md: str) -> None:
    p = os.getenv("GITHUB_STEP_SUMMARY")
    if not p:
        return
    Path(p).write_text(md, encoding="utf-8")

def append_step_summary(md: str) -> None:
    p = os.getenv("GITHUB_STEP_SUMMARY")
    if not p:
        return
    Path(p).write_text(Path(p).read_text(encoding="utf-8") + md, encoding="utf-8")

def build_readme(
    repo: str,
    branch: str,
    csv_rel: str,
    links: dict[str, str],
    rows_count: int,
    size_kb: int,
    csv_sha: str,
    gen_utc: str,
    gen_cn: str,
    sample_quote: str,
    sample_author: str,
) -> str:
    raw = links["raw"]
    jsd = links["jsdelivr"]
    ghp = links["ghproxy"]
    blob = links["blob"]
    badges = [
        f"https://img.shields.io/badge/quotes-{rows_count}-111827?logo=files&logoColor=white",
        f"https://img.shields.io/badge/size~{size_kb}%20KB-374151",
        "https://img.shields.io/badge/format-CSV-0ea5e9",
        f"https://img.shields.io/badge/updated-{gen_utc.replace(' ', '%20')}-10b981",
    ]

    lines: list[str] = []
    lines += [
        "<!-- AUTO-GENERATED: DO NOT EDIT MANUALLY -->",
        '<div align="center">',
        "",
        "# bonjourr-chinese-quotes",
        "",
        "<p><b>中文语录数据集（CSV）</b> · 适用于 Bonjourr / 新标签页扩展 / 个人项目</p>",
        "",
        "<p>",
        "  " + " ".join([f'<img alt="badge" src="{u}">' for u in badges]),
        "</p>",
        "",
        "<p>",
        f'  <a href="{raw}"><img alt="GitHub Raw" src="https://img.shields.io/badge/Download-GitHub%20Raw-2ea44f"></a>',
        f'  <a href="{jsd}"><img alt="jsDelivr" src="https://img.shields.io/badge/Download-jsDelivr-2563eb"></a>',
        f'  <a href="{ghp}"><img alt="ghproxy" src="https://img.shields.io/badge/Download-ghproxy-f97316"></a>',
        "</p>",
        "",
        "</div>",
        "",
        "---",
        "",
        "## 快速入口",
        "",
        f"- **CSV 文件（浏览）**：`{blob}`",
        f"- **CSV 文件（Raw）**：`{raw}`",
        "",
        "---",
        "",
        "## 下载（quotes.csv）",
        "",
        "<table>",
        "  <thead><tr><th>渠道</th><th>链接</th><th>推荐场景</th></tr></thead>",
        "  <tbody>",
        f"    <tr><td><b>GitHub Raw</b></td><td><code>{raw}</code></td><td>默认首选：稳定、权威</td></tr>",
        f"    <tr><td><b>jsDelivr</b></td><td><code>{jsd}</code></td><td>CDN：更快、可缓存</td></tr>",
        f"    <tr><td><b>ghproxy</b></td><td><code>{ghp}</code></td><td>代理：网络受限时尝试</td></tr>",
        "  </tbody>",
        "</table>",
        "",
        "> 小提示：如果你在代码里引用链接，建议保留“主链接 + 备用链接”以提升可用性。",
        "",
        "---",
        "",
        "## 数据概览",
        "",
        "<table>",
        "  <tbody>",
        f"    <tr><td>条目数</td><td><b>{rows_count}</b></td></tr>",
        f"    <tr><td>文件大小</td><td><b>~{size_kb} KB</b></td></tr>",
        f"    <tr><td>校验（SHA-256）</td><td><code>{csv_sha[:20]}…</code></td></tr>",
        f"    <tr><td>最近生成</td><td><b>{gen_utc}</b> / <b>{gen_cn}</b></td></tr>",
        "  </tbody>",
        "</table>",
        "",
    ]

    if sample_quote.strip():
        lines += [
            "## 今日精选",
            "",
            f"> {safe_md_inline(sample_quote, 260)}",
            "",
        ]
        if sample_author.strip():
            lines += [f"- — {safe_md_inline(sample_author, 120)}", ""]

    lines += [
        "---",
        "",
        "## 自动更新",
        "",
        "- README 由 GitHub Actions 定时生成；当内容无变化时不会提交（避免噪音提交）。",
        "- 需要修改样式/统计：编辑 `scripts/generate_readme.py`。",
        "",
    ]
    return "\n".join(lines) + "\n"

def build_summary(
    repo: str,
    branch: str,
    csv_rel: str,
    links: dict[str, str],
    rows_count: int,
    size_kb: int,
    csv_sha: str,
    gen_utc: str,
    gen_cn: str,
    readme_changed: bool | None,
    csv_preview: str,
) -> str:
    raw = links["raw"]
    jsd = links["jsdelivr"]
    ghp = links["ghproxy"]
    blob = links["blob"]

    if readme_changed is True:
        status = "✅ README 有变化：将提交"
    elif readme_changed is False:
        status = "🟦 README 无变化：跳过提交（正常）"
    else:
        status = "ℹ️ 首次生成或无法比较：以 workflow 的 diff 为准"

    return "\n".join(
        [
            "## ✅ README 自动生成报告",
            "",
            f"**状态**：{status}",
            "",
            "### 关键指标",
            "",
            f"- Repo：`{repo}`",
            f"- Branch：`{branch}`",
            f"- CSV：`{csv_rel}`",
            f"- Rows：**{rows_count}**",
            f"- Size：**~{size_kb} KB**",
            f"- CSV SHA-256：`{csv_sha}`",
            f"- Generated：**{gen_utc}** / **{gen_cn}**",
            "",
            "### 下载链接（可直接复制）",
            "",
            f"- 浏览：`{blob}`",
            f"- GitHub Raw：`{raw}`",
            f"- jsDelivr：`{jsd}`",
            f"- ghproxy：`{ghp}`",
            "",
            "<details><summary>排错：CSV 预览（前 3 行）</summary>",
            "",
            "```text",
            csv_preview.strip() or "(empty)",
            "```",
            "",
            "</details>",
            "",
            "<details><summary>排错：常见原因</summary>",
            "",
            "- 一直“无变化”：说明生成结果稳定一致（正常）。你可以改 README 模板/统计项来制造可见变化。",
            "- 找不到 CSV：检查 `QUOTES_CSV` 路径、大小写、是否在默认分支。",
            "- 镜像链接不可用：可在脚本里增加/替换镜像域名。",
            "",
            "</details>",
            "",
        ]
    )

def main() -> int:
    notice("SCRIPT_VERSION=2026-01-21-v6")
    repo = os.getenv("GITHUB_REPOSITORY", "YOUR_GITHUB_NAME/bonjourr-chinese-quotes")
    branch = os.getenv("DEFAULT_BRANCH", "main")
    csv_rel = os.getenv("QUOTES_CSV", "quotes.csv")
    csv_path = Path(csv_rel)
    readme_path = Path("README.md")

    if not csv_path.exists():
        error(f"CSV not found: {csv_rel}", file=csv_rel)
        write_step_summary("\n".join(["## ❌ 生成失败", "", f"- 找不到 CSV：`{csv_rel}`", ""]))
        return 2

    rows_all = csv_rows(csv_path)
    has_header, _ = detect_header(rows_all)
    data_rows = rows_all[1:] if has_header and len(rows_all) >= 2 else rows_all
    rows_count = len(data_rows)
    size_kb = file_size_kb(csv_path)
    csv_sha = sha256_file(csv_path)
    now_utc = datetime.now(timezone.utc)
    now_cn = now_utc.astimezone(timezone(timedelta(hours=8)))
    gen_utc = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    gen_cn = now_cn.strftime("%Y-%m-%d %H:%M:%S UTC+8")
    links = build_links(repo, branch, csv_rel)
    quote, author = pick_sample(rows_all, prefer_daily=True)
    old = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    new = build_readme(repo, branch, csv_rel, links, rows_count, size_kb, csv_sha, gen_utc, gen_cn, quote, author)
    readme_path.write_text(new, encoding="utf-8")
    readme_changed = (old != new) if old else None
    csv_preview = "\n".join(read_text_smart(csv_path).splitlines()[:3])
    write_step_summary(
        build_summary(
            repo=repo,
            branch=branch,
            csv_rel=csv_rel,
            links=links,
            rows_count=rows_count,
            size_kb=size_kb,
            csv_sha=csv_sha,
            gen_utc=gen_utc,
            gen_cn=gen_cn,
            readme_changed=readme_changed,
            csv_preview=csv_preview,
        )
    )

    group("Inputs")
    print("repo       =", repo)
    print("branch     =", branch)
    print("quotes_csv =", csv_rel)
    endgroup()
    group("Computed")
    print("rows_count =", rows_count)
    print("size_kb    =", size_kb)
    print("csv_sha    =", csv_sha)
    endgroup()

    notice(f"README generated: {readme_path.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
