# instock/core/news/news_fetch.py
# 新闻舆情抓取器（NewsAPI.org 免费版）

import logging
import requests
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

from instock.lib.database_sqlite import db_path

__author__ = 'myh '
__date__ = '2026/4/22 '

# 配置（你注册后填入）
NEWS_API_KEY = "YOUR_NEWS_API_KEY"  # ← 替换为你自己的 key
NEWS_API_URL = "https://newsapi.org/v2/everything"

# 初始化日志
logging.basicConfig(
    format='%(asctime)s %(message)s',
    filename=Path(__file__).parent.parent.parent / "log" / "stock_news.log",
    level=logging.INFO
)

def init_news_table():
    """创建 stock_news 表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT,
            title TEXT NOT NULL,
            description TEXT,
            url TEXT NOT NULL,
            published_at TIMESTAMP NOT NULL,
            source TEXT,
            sentiment_score REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("✅ stock_news 表初始化完成")

def fetch_news_by_keyword(keyword: str, from_date: str = None) -> list:
    """
    按关键词抓取新闻（支持 A 股代码或概念词）
    示例 keyword: "000001", "AI芯片", "新能源车"
    """
    if not from_date:
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    params = {
        "q": keyword,
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "zh",
        "pageSize": 50,
        "apiKey": NEWS_API_KEY
    }
    
    try:
        logging.info(f"🔍 正在抓取新闻：{keyword}（{from_date}起）")
        response = requests.get(NEWS_API_URL, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        
        results = []
        for a in articles:
            # 清洗字段
            title = a.get("title", "")[:200] or "无标题"
            desc = a.get("description", "")[:500] or ""
            url = a.get("url", "")
            published = a.get("publishedAt", "")
            source = a.get("source", {}).get("name", "未知来源")
            
            if not url or not published:
                continue
                
            results.append({
                "code": keyword,  # 简化：按关键词存，后续可扩展为股票代码映射
                "name": "",
                "title": title,
                "description": desc,
                "url": url,
                "published_at": published,
                "source": source,
                "sentiment_score": 0.0  # 后续可用 TextBlob 做情感分析
            })
        
        logging.info(f"✅ 抓取到 {len(results)} 条新闻：{keyword}")
        return results
        
    except Exception as e:
        logging.error(f"❌ 新闻抓取失败 {keyword}：{e}")
        return []

def save_news_to_db(news_list: list):
    """保存新闻到 SQLite"""
    if not news_list:
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for n in news_list:
        cursor.execute('''
            INSERT INTO stock_news 
            (code, name, title, description, url, published_at, source, sentiment_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            n["code"],
            n["name"],
            n["title"],
            n["description"],
            n["url"],
            n["published_at"],
            n["source"],
            n["sentiment_score"]
        ))
    
    conn.commit()
    conn.close()
    logging.info(f"✅ {len(news_list)} 条新闻已存入 stock_news 表")

def main():
    """主入口：抓取 A 股核心概念词"""
    init_news_table()
    
    # 核心概念词（可扩展）
    keywords = [
        "AI芯片", "新能源车", "光伏", "锂电池", "CPO", 
        "算力", "低空经济", "机器人", "半导体", "创新药"
    ]
    
    for kw in keywords:
        time.sleep(1)  # 避免 API 限流
        news = fetch_news_by_keyword(kw)
        save_news_to_db(news)
    
    logging.info("🎉 新闻舆情抓取任务完成")

if __name__ == "__main__":
    main()