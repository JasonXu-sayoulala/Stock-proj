# newsHandler.py
# 新闻舆情 Web 处理器

import tornado.web
import sqlite3
from pathlib import Path
from instock.lib.database_sqlite import db_path


class GetNewsHandler(tornado.web.RequestHandler):
    def get(self):
        # 获取查询参数
        code = self.get_argument("code", "")
        keyword = self.get_argument("keyword", "")
        limit = int(self.get_argument("limit", "20"))
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if code:
            cursor.execute('''
                SELECT * FROM stock_news 
                WHERE code = ? 
                ORDER BY published_at DESC 
                LIMIT ?
            ''', (code, limit))
        elif keyword:
            cursor.execute('''
                SELECT * FROM stock_news 
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY published_at DESC 
                LIMIT ?
            ''', (f'%{keyword}%', f'%{keyword}%', limit))
        else:
            cursor.execute('''
                SELECT * FROM stock_news 
                ORDER BY published_at DESC 
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        news_list = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        self.render("news.html", 
                    news_list=news_list,
                    code=code,
                    keyword=keyword)
