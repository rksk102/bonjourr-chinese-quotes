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

class Logger:
    @staticmethod
    def banner(msg: str):
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}\n {msg}\n{'='*60}{Colors.ENDC}\n")
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
    def error(msg: str):
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")

def read_text_smart(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except:
        return p.read_text(encoding="utf-8-sig")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def extract_old_stats(readme_content: str) -> int:
    """从旧 README 的 QUOTES 徽标链接中提取数字 (适配 Shields.io 格式)"""
    match = re.search(r'badge/QUOTES-(\d+)-', readme_content, re.IGNORECASE)
    return int(match.group(1)) if match else 0

def load_data(csv_path: Path) -> list:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found at: {csv_path}")
    raw_content = read_text_smart(csv_path)
    lines = [line for line in raw_content.splitlines() if line.strip()]
    rows = []
    reader = csv.reader(lines)
    for row in reader:
        if row: rows.append([cell.strip() for cell in row])
    return rows

def make_badge(label: str, message: str, color: str, icon: str = "") -> str:
    label = label.replace(" ", "%20")
    message = str(message).replace(" ", "%20")
    url = f"https://img.shields.io/badge/{label}-{message}-{color}?style=for-the-badge&labelColor=24292e"
    if icon: url += f"&logo={icon}&logoColor=white"
    return url

def build_readme_content(ctx: dict, sample: dict) -> str:
    repo = ctx['repo']
    branch = os.getenv('DEFAULT_BRANCH', 'main')
    
    diff_val = ctx['diff_count']
    if diff_val > 0:
        diff_display = f"**↑ +{diff_val}**"
    elif diff_val < 0:
        diff_display = f"**↓ {diff_val}**"
    else:
        diff_display = "±0 (保持平衡)" 

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
        "**1. jsDelivr**",
        f"[![jsd]({btn_jsd_img})]({link_jsd})",
        "```url",
        link_jsd,
        "```",
        "",
        "**2. Statically**",
        f"[![stat]({btn_stat_img})]({link_stat})",
        "```url",
        link_stat,
        "```",
        "",
        "### 🌏 区域镜像 (Mirrors)",
        "**ghproxy**",
        f"[![ghp]({btn_ghp_img})]({link_ghp})",
        "```url",
        link_ghp,
        "```",
        "",
        "<details>",
        "<summary><strong>🐍 Python 读取数据示例代码 (点击展开)</strong></summary>",
        "",
        "```python",
        "import pandas as pd",
        f'url = "{link_jsd}"',
        "df = pd.read_csv(url, names=['author', 'text'])",
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
        f"| **总语录数** | `{ctx['rows_count']}` | {diff_display} |",
        f"| **文件完整性** | `{checksum_short}` | SHA-256 Checksum |",
        "",
        "---",
        '<div align="center">',
        "<sub>🤖 Generated by GitHub Actions | <a href='https://github.com/'>Star this repository</a></sub>",
        "</div>"
    ]
    return "\n".join(md)

def main():
    start_time = time.time()
    Logger.banner("STARTING README GENERATION JOB")
    repo = os.getenv("GITHUB_REPOSITORY", "local/test")
    branch = os.getenv("DEFAULT_BRANCH", "main")
    csv_path = Path(os.getenv("QUOTES_CSV", "quotes.csv"))
    readme_path = Path("README.md")

    old_row_count = 0
    if readme_path.exists():
        try:
            old_content = read_text_smart(readme_path)
            old_row_count = extract_old_stats(old_content)
        except: pass 
            
    try:
        rows = load_data(csv_path)
    except Exception as e:
        Logger.error(f"Failed to load CSV: {e}")
        return 1

    a_idx, q_idx = 0, 1

    data_rows = rows
    if rows and rows[0][0].lower() in ['author', '作者']:
        data_rows = rows[1:]

    rows_count = len(data_rows)
    if rows_count == 0:
        Logger.error("No data rows!")
        return 1

    seed_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rnd = random.Random(seed_date)
    sample_row = rnd.choice(data_rows)
    s_author = sample_row[a_idx] if len(sample_row) > a_idx else "佚名"
    s_quote = sample_row[q_idx] if len(sample_row) > q_idx else "Unknown"

    ctx = {
        "repo": repo,
        "rows_count": rows_count,
        "diff_count": rows_count - old_row_count,
        "size_kb": int(csv_path.stat().st_size / 1024) + 1,
        "csv_sha": sha256_file(csv_path),
        "gen_cn": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
        "links": {"raw": f"https://raw.githubusercontent.com/{repo}/{branch}/quotes.csv"}
    }

    new_readme = build_readme_content(ctx, {"quote": s_quote, "author": s_author})
    readme_path.write_text(new_readme, encoding="utf-8")
    
    Logger.success(f"README.md updated. (Current: {rows_count}, Diff: {ctx['diff_count']})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
