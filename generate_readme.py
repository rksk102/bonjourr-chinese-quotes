import os
import csv
from datetime import datetime

QUOTES_FILE = "quotes.csv"
README_FILE = "README.md"
GITHUB_USER = "rksk102"
REPO_NAME = "bonjourr-chinese-quotes"
BRANCH = "main"

LINKS = {
    "GitHub Raw": f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/{BRANCH}/quotes.csv",
    "jsDelivr CDN": f"https://cdn.jsdelivr.net/gh/{GITHUB_USER}/{REPO_NAME}@{BRANCH}/quotes.csv",
    "gh-proxy 镜像": f"https://mirror.ghproxy.com/https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/{BRANCH}/quotes.csv",
    "GitCDN": f"https://gitcdn.xyz/repo/{GITHUB_USER}/{REPO_NAME}/{BRANCH}/quotes.csv",
    "Staticaly CDN": f"https://cdn.staticaly.com/gh/{GITHUB_USER}/{REPO_NAME}/{BRANCH}/quotes.csv",
}

def get_quote_stats():
    """获取语录统计信息"""
    count = 0
    if os.path.exists(QUOTES_FILE):
        with open(QUOTES_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('text', '').strip():
                    count += 1
    return count

def generate_readme():
    """生成 README.md"""
    quote_count = get_quote_stats()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    content = f"""<!-- 
  生成时间: {current_time}
  语录总数: {quote_count}
  请勿手动编辑此文件，由 workflow 自动生成
-->

<div align="center">

# 📚 中文语录库

[![GitHub stars](https://img.shields.io/github/stars/{GITHUB_USER}/{REPO_NAME}?style=social)](https://github.com/{GITHUB_USER}/{REPO_NAME}/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/{GITHUB_USER}/{REPO_NAME}?style=social)](https://github.com/{GITHUB_USER}/{REPO_NAME}/network/members)
[![GitHub issues](https://img.shields.io/github/issues/{GITHUB_USER}/{REPO_NAME})](https://github.com/{GITHUB_USER}/{REPO_NAME}/issues)
[![License](https://img.shields.io/github/license/{GITHUB_USER}/{REPO_NAME})](https://github.com/{GITHUB_USER}/{REPO_NAME}/blob/main/LICENSE)

**每天自动更新的中文语录/诗词库，适用于 [Bonjourr](https://bonjourr.fr/) 等新标签页**

![语录数量](https://img.shields.io/badge/语录数量-{quote_count}-brightgreen)
![最后更新](https://img.shields.io/badge/最后更新-{current_time.split()[0]}-blue)

</div>

---

## 📖 项目简介

本项目通过 GitHub Actions 每日自动从多个中文语录/诗词 API 拉取数据，生成标准化的 CSV 文件，可直接用于支持自定义语录源的浏览器扩展（如 Bonjourr）。

### ✨ 特点

- 🚀 **每日自动更新**：每天自动获取 15 条新的中文语录
- 🎯 **多源轮询**：从 20+ 个 API 源获取数据，确保内容丰富多样
- 🔄 **自动去重**：智能去重，确保语录不重复
- 📊 **类型多样**：包含古诗词、名言警句、励志语录、文艺句子等
- 🌍 **多节点加速**：提供多个 CDN 加速下载链接

---

## 📥 下载 CSV 文件

### 🌐 下载链接

| 镜像源 | 下载链接 | 说明 |
|:---|:---|:---|
"""

    for name, url in LINKS.items():
        content += f"| **{name}** | [下载]({url}) | {'🇺🇳 国际加速' if 'CDN' in name or 'proxy' in name else '🇨🇳 原始链接'} |\n"
    
    content += f"""
### 📋 文件格式

CSV 文件采用标准的 UTF-8 编码，包含两列数据：

