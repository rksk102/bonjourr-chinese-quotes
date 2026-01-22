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
    diff_val = ctx['diff_count']
    if diff_val > 0:
        diff_display = f"**+{diff_val}**"
    elif diff_val < 0:
        diff_display = str(diff_val)
    else:
        diff_display = "-" 

    checksum_short = ctx['csv_sha'][:12] + "..."
    link_raw = ctx['links']['raw']
    link_jsd = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/quotes.csv"
    link_stat = f"https://cdn.statically.io/gh/{repo}/{branch}/quotes.csv"
    link_ghp = f"https://mirror.ghproxy.com/{link_raw}"
    b_quotes = make_badge("QUOTES", ctx['rows_count'], "4F46E5", "googledocs") 
    b_size   = make_badge("SIZE", f"{ctx['size_kb']} KB", "059669", "database")
    b_time   = make_badge("UPDATE", "TODAY", "BE185D", "clock")
    btn_raw_img = f"https://img.shields.io/badge/GitHub_Raw-Source_File-2ea44f?style=for-the-badge&logo=github&logoColor=white"
    btn_jsd_img = f"https://img.shields.io/badge/jsDelivr-Global_CDN-ff5627?style=for-the-badge&logo=jsdelivr&logoColor=white"
    btn_stat_img = f"https://img.shields.io/badge/Statically-Multi_CDN-7c3aed?style=for-the-badge&logo=serverless&logoColor=white"
    btn_ghp_img = f"https://img.shields.io/badge/ghproxy-Mirror_Proxy-f97316?style=for-the-badge&logo=googlecloud&logoColor=white"


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
        "</td></tr>",
        "</table>",
        "",
        "</div>", 
        "",
        "<br/>",
        "",

        "## ⚡️ 快速接入 / Quick Access",
        "",
        "### 🟢 官方源 (Stable)",
        f"[![Raw]({btn_raw_img})]({link_raw})",
        "```url",
        link_raw,
        "```",
        "",
        "### 🚀 全球加速 (Global CDNs)",
        "> 推荐生产环境使用。如果其中一个访问慢，可切换另一个。",
        "",
        "**1. jsDelivr** (推荐：快速、缓存强)",
        f"[![jsd]({btn_jsd_img})]({link_jsd})",
        "```url",
        link_jsd,
        "```",
        "",
        "**2. Statically** (备选：基于 Cloudflare/Fastly 多云分发)",
        f"[![stat]({btn_stat_img})]({link_stat})",
        "```url",
        link_stat,
        "```",
        "",
        "### 🌏 区域镜像 (Mirrors)",
        "> 针对特定受限网络环境优化",
        "",
        "**ghproxy**",
        f"[![ghp]({btn_ghp_img})]({link_ghp})",
        "```url",
        link_ghp,
        "```",
        "",

        "<details>",
        "<summary><strong>🐍 Python 读取数据示例代码 (Click to expand)</strong></summary>",
        "",
        "```python",
        "import pandas as pd",
        "",
        "# 定义加速源列表",
        f'urls = [',
        f'    "{link_jsd}",      # 首选',
        f'    "{link_stat}",     # 备选',
        f'    "{link_raw}"       # 兜底',
        "]",
        "",
        "df = None",
        "for url in urls:",
        "    try:",
        "        print(f'正在尝试: {url} ...')",
        "        df = pd.read_csv(url)",
        "        print('✅ 加载成功！')",
        "        break",
        "    except Exception:",
        "        continue",
        "",
        "if df is not None:",
        "    print(df.sample(1))",
        "else:",
        "    print('❌ 所有源均无法连接')",
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
        f"| **总语录数** | `{ctx['rows_count']}` | {diff_display} |",
        f"| **文件完整性** | `{checksum_short}` | SHA-256 Checksum |",
        "",
        "---",
        '<div align="center">',
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
        try:
            old_content = read_text_smart(readme_path)
            old_row_count = extract_old_stats(old_content)
        except:
            pass 
            
    Logger.section("Processing CSV Data")
    try:
        rows, load_stats = load_data(csv_path)
    except Exception as e:
        Logger.error(f"Failed to load CSV: {e}")
        return 1

    has_header = False
    header = []
    q_idx, a_idx = 1, 0 
    
    if len(rows) > 0:
        first_row = [c.lower().strip() for c in rows[0]]
        valid_quote_keys = ["quote", "text", "content", "语录", "句子", "内容", "名言"]
        valid_author_keys = ["author", "source", "from", "writer", "作者", "出处", "来源"]

        if any(k in first_row for k in valid_quote_keys + valid_author_keys):
            has_header = True
            header = rows[0]
            Logger.info(f"Detected Header: {header}", "CSV")

            for i, h in enumerate(first_row):
                if h in valid_quote_keys: 
                    q_idx = i
                elif h in valid_author_keys: 
                    a_idx = i
        else:
            Logger.info("No header detected, strictly using: Col 0=Author, Col 1=Quote", "CSV")

    data_rows = rows[1:] if has_header else rows
    rows_count = len(data_rows)
    
    if rows_count == 0:
        Logger.error("CSV has no data rows!")
        return 1
    Logger.success(f"Parsed {rows_count} valid data rows.")
    Logger.section("Picking Daily Sample")
    seed_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rnd = random.Random(seed_date)
    
    if not data_rows:
        s_quote, s_author = "No data available", "System"
    else:
        sample_row = rnd.choice(data_rows)
        s_quote = sample_row[q_idx] if len(sample_row) > q_idx else "Unknown"
        s_author = sample_row[a_idx] if len(sample_row) > a_idx else "佚名"
    Logger.info(f"Selected: {s_quote[:20]}... -- {s_author}", "DAILY")

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
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        Logger.error("Unhandled Exception detected!")
        traceback.print_exc()
        sys.exit(1)
