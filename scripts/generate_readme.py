from __future__ import annotations
import csv
import hashlib
import os
import sys
import time
import random
import traceback
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Logger:
    @staticmethod
    def banner(msg: str):
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
        print(f" {msg}")
        print(f"{'='*60}{Colors.ENDC}\n")
    @staticmethod
    def section(msg: str):
        print(f"\n{Colors.CYAN}➤ {Colors.BOLD}{msg}{Colors.ENDC}")
    @staticmethod
    def info(msg: str, label: str = "INFO"):
        print(f"{Colors.BLUE}[{label}]{Colors.ENDC} {msg}")
    @staticmethod
    def success(msg: str):
        print(f"{Colors.GREEN}[SUCCESS]{Colors.ENDC} {msg}")
    @staticmethod
    def warning(msg: str):
        print(f"::warning::{msg}")
        print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {msg}")
    @staticmethod
    def error(msg: str):
        print(f"::error::{msg}")
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")
    @staticmethod
    def group(title: str):
        print(f"::group::{title}")
    @staticmethod
    def endgroup():
        print("::endgroup::")

def read_text_smart(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        Logger.info(f"UTF-8 failed, trying UTF-8-SIG for {p.name}", "ENCODING")
        return p.read_text(encoding="utf-8-sig")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def extract_old_stats(readme_content: str) -> int:
    """尝试从旧的 README 中提取之前的行数，用于对比"""
    match = re.search(r'badge/quotes-(\d+)-', readme_content)
    return int(match.group(1)) if match else 0

def load_data(csv_path: Path) -> tuple[list[list[str]], dict]:
    stats = {"total_rows": 0, "valid_data_rows": 0, "malformed_rows": 0}
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found at: {csv_path.resolve()}")
    Logger.info(f"Reading file: {csv_path}", "IO")
    raw_content = read_text_smart(csv_path)
    lines = [line for line in raw_content.splitlines() if line.strip()]
    stats["total_rows"] = len(lines)
    rows = []
    reader = csv.reader(lines)
    for i, row in enumerate(reader):
        clean_row = [cell.strip() for cell in row]
        if any(clean_row):
            rows.append(clean_row)
    
    return rows, stats

def build_readme_content(ctx: dict, sample: dict) -> str:
    repo = ctx['repo']
    branch = os.getenv('DEFAULT_BRANCH', 'main')
    link_raw = ctx['links']['raw']
    link_cdn = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/quotes.csv"
    b_quotes = make_badge("QUOTES", ctx['rows_count'], "4F46E5", "googledocs") 
    b_size   = make_badge("SIZE", f"{ctx['size_kb']} KB", "059669", "database")
    b_time   = make_badge("UPDATE", "TODAY", "BE185D", "clock")

    md = [
        "<!-- AUTO-GENERATED -->",
        '<div align="center">',
        "",
        "# 📜 Bonjourr Chinese Quotes",
        "<h3>精选中文语录数据集 · 每日自动更新</h3>",
        "",
        f'<img src="{b_quotes}" height="28"> <img src="{b_size}" height="28"> <img src="{b_time}" height="28">',
        "",
        "<br/>",
        "",

        '<table width="800">',
        '<tr><td align="center">',
        "",
        "### ☕️ 今日一言 (Daily Quote)",
        "",
        f"<h2>❝ {sample['quote']} ❞</h2>",
        f'<p align="right">—— <b>{sample["author"] or "佚名"}</b></p>',
        "",
        "</td></tr>',
        "</table>",
        "",
        "</div>",
        "",
        "<br/>",
        "",

        "## ⚡️ 快速接入 / Quick Access",
        "",
        "请根据你的使用场景选择最佳的数据源：",
        "",
        '<table width="100%">',
        "  <tr>",
        '    <th width="50%"><div align="center">📦 Source (开发/备份)</div></th>',
        '    <th width="50%"><div align="center">🚀 CDN (生产/Web)</div></th>',
        "  </tr>",
        "  <tr>",
        '    <td valign="top">',
        "",
        '<div align="center">',
        "**适合：Python 脚本、数据分析、后端同步**",
        "<br/>",
        f'<a href="{link_raw}"><img src="https://img.shields.io/badge/GitHub_Raw-Download-2ea44f?style=flat-square&logo=github" height="25"></a>',
        "</div>",
        "",
        "```url",
        link_raw,
        "```",
        "",
        "    </td>",
        '    <td valign="top">',
        "",
        '<div align="center">',
        "**适合：网页引用、前端应用、Bonjourr**",
        "<br/>",
        f'<a href="{link_cdn}"><img src="https://img.shields.io/badge/jsDelivr-Accelerated-ff5627?style=flat-square&logo=jsdelivr" height="25"></a>',
        "</div>",
        "",
        "```url",
        link_cdn,
        "```",
        "",
        "    </td>",
        "  </tr>",
        "</table>",
        "",
        "<details>",
        "<summary><strong>🛠 查看 Python 读取示例 (Click to expand)</strong></summary>",
        "",
        "```python",
        "import pandas as pd",
        "",
        f'url = "{link_raw}"',
        "df = pd.read_csv(url)",
        "print(df.sample(1))",
        "```",
        "</details>",
        "",
        "<br/>",
        "",

        "## 📊 数据看板 / Dashboard",
        "",
        f"> **更新日志**: {ctx['gen_cn']} (UTC+8)",
        "",
        "| 指标 | 当前数值 | 较昨日变化 |",
        "| :--- | :--- | :--- |",
        f"| **总语录数** | `{ctx['rows_count']}` | {f'**+{ctx['diff_count']}**' if ctx['diff_count'] > 0 else ctx['diff_count']} |",
        f"| **文件完整性** | `{ctx['csv_sha'][:12]}...` | SHA-256 Checksum |",
        "",
        "---",
        "<div align="center">",
        "<sub>🤖 Generated by GitHub Actions | <a href='https://github.com/'>Star this repository</a></sub>",
        "</div>"
    ]
    
    return "\n".join(md)

def make_badge(label: str, message: str, color: str, icon: str = "") -> str:
    """生成 Shields.io 'for-the-badge' 风格的精美徽章"""
    label = label.replace(" ", "%20")
    message = str(message).replace(" ", "%20")
    url = f"https://img.shields.io/badge/{label}-{message}-{color}?style=for-the-badge&labelColor=24292e"
    if icon:
        url += f"&logo={icon}&logoColor=white"
    return url

def generate_step_summary(ctx: dict, diagnositcs: list[str]):
    """生成 GitHub Actions 漂亮的 Summary"""
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    icon = "✅" if ctx['diff_count'] >= 0 else "⚠️"
    md = [
        f"## {icon} Generator Execution Report",
        "",
        "### 📊 Statistics Snapshot",
        "",
        "| Metric | Value | Change |",
        "| :--- | :--- | :--- |",
        f"| **Total Quotes** | **{ctx['rows_count']}** | {ctx['diff_count']:+d} |",
        f"| **File Size** | {ctx['size_kb']} KB | - |",
        f"| **Execution Time** | {ctx['exec_time']:.2f}s | - |",
        "",
        "### 🔍 Diagnostics",
        ""
    ]
    if diagnositcs:
        md.append("```text")
        md.extend(diagnositcs)
        md.append("```")
    else:
        md.append("No warnings or errors detected. CSV structure looks good.")
    Path(summary_path).write_text("\n".join(md), encoding="utf-8")


def main():
    start_time = time.time()
    Logger.banner("STARTING README GENERATION JOB")
    Logger.section("Checking Environment")
    repo = os.getenv("GITHUB_REPOSITORY", "local/test")
    branch = os.getenv("DEFAULT_BRANCH", "main")
    csv_rel = os.getenv("QUOTES_CSV", "quotes.csv")
    csv_path = Path(csv_rel)
    readme_path = Path("README.md")
    Logger.info(f"Repo: {repo} | Branch: {branch}")
    old_row_count = 0
    if readme_path.exists():
        Logger.info("Reading existing README for history comparison...", "HISTORY")
        old_content = read_text_smart(readme_path)
        old_row_count = extract_old_stats(old_content)
        Logger.info(f"Previous count: {old_row_count}")
    Logger.section("Processing CSV Data")
    try:
        rows, load_stats = load_data(csv_path)
    except Exception as e:
        Logger.error(f"Failed to load CSV: {e}")
        return 1

    has_header = False
    header = []
    if len(rows) > 0:
        first = [c.lower() for c in rows[0]]
        if "quote" in first or "content" in first or "text" in first:
            has_header = True
            header = rows[0]
            Logger.info(f"Detected Header: {header}", "CSV")
    data_rows = rows[1:] if has_header else rows
    rows_count = len(data_rows)
    
    if rows_count == 0:
        Logger.error("CSV has no data rows!")
        return 1
    Logger.success(f"Parsed {rows_count} valid data rows.")

    Logger.section("Picking Daily Sample")
    seed_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rnd = random.Random(seed_date)
    sample_row = rnd.choice(data_rows)

    q_idx, a_idx = 0, 1
    if has_header:
        for i, h in enumerate([x.lower() for x in header]):
            if h in ["quote", "text", "content"]: q_idx = i
            if h in ["author", "source", "from"]: a_idx = i
    s_quote = sample_row[q_idx] if len(sample_row) > q_idx else "Unknown"
    s_author = sample_row[a_idx] if len(sample_row) > a_idx else ""
    
    Logger.info(f"Selected: {s_quote[:30]}...", "DAILY")
    ctx = {
        "repo": repo,
        "rows_count": rows_count,
        "diff_count": rows_count - old_row_count,
        "size_kb": int(csv_path.stat().st_size / 1024) + 1,
        "csv_sha": sha256_file(csv_path),
        "gen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "gen_cn": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
        "links": {
            "raw": f"https://raw.githubusercontent.com/{repo}/{branch}/{csv_rel}",
        }
    }
    Logger.section("Writing Content")
    new_readme = build_readme_content(ctx, {"quote": s_quote, "author": s_author})
    readme_path.write_text(new_readme, encoding="utf-8")
    Logger.success(f"README.md updated ({len(new_readme)} bytes written)")
    ctx['exec_time'] = time.time() - start_time
    generate_step_summary(ctx, [])
    Logger.banner(f"JOB COMPLETED IN {ctx['exec_time']:.2f}s")
    Logger.info(f"Final Count: {rows_count} (Change: {ctx['diff_count']:+d})", "RESULT")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        Logger.error("Unhandled Exception detected!")
        traceback.print_exc()
        sys.exit(1)
