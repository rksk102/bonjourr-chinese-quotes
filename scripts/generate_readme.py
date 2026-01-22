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

def build_readme_content(
    ctx: dict,
    sample: dict
) -> str:
    badges = [
        f"https://img.shields.io/badge/quotes-{ctx['rows_count']}-111827?logo=files&logoColor=white",
        f"https://img.shields.io/badge/size~{ctx['size_kb']}%20KB-374151",
        f"https://img.shields.io/badge/updated-{ctx['gen_utc'].split()[0]}-10b981",
    ]
   
    md = [
        "<!-- AUTO-GENERATED: DO NOT EDIT MANUALLY -->",
        '<div align="center">',
        "",
        "# bonjourr-chinese-quotes",
        "",
        "<p><b>中文语录数据集（CSV）</b></p>",
        "<p>" + " ".join([f'<img src="{b}">' for b in badges]) + "</p>",
        f'<p><a href="{ctx["links"]["raw"]}">Download Raw CSV</a></p>',
        "</div>",
        "",
        "---",
        "## 今日精选",
        "",
        f"> {sample['quote']}",
        "",
        f"- — *{sample['author']}*" if sample['author'] else "",
        "",
        "---",
        "## 数据概览",
        "",
        "| 指标 | 数值 | 备注 |",
        "| :--- | :--- | :--- |",
        f"| **条目数** | `{ctx['rows_count']}` | 较昨日 {'+' if ctx['diff_count'] >=0 else ''}{ctx['diff_count']} |",
        f"| **文件大小** | `{ctx['size_kb']} KB` | - |",
        f"| **SHA-256** | `{ctx['csv_sha'][:16]}...` | 前16位 |",
        f"| **更新时间** | `{ctx['gen_cn']}` | 北京时间 |",
        "",
        "---",
        "## 自动更新说明",
        "- 本文件由 GitHub Actions 每日自动生成。",
        ""
    ]
    return "\n".join(md)

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
