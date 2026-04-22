# database_sqlite.py
# InStock SQLite 数据库适配层

import logging
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

__author__ = 'myh '
__date__ = '2023/3/10 '

# SQLite 数据库文件路径
db_path = Path(__file__).parent.parent / "instock.db"

# 初始化 SQLite 数据库
def init_sqlite_db():
    if not db_path.exists():
        logging.info(f"SQLite DB 初始化: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # 创建基础表（示例）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_basic (
                code TEXT PRIMARY KEY,
                name TEXT,
                industry TEXT,
                market TEXT
            )
        ''')
        conn.commit()
        conn.close()
    else:
        logging.info(f"SQLite DB 已存在: {db_path}")

# 获取 SQLite 连接（上下文管理）
@contextmanager
def get_connection():
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        logging.error(f"SQLite connection error: {e}")
        raise
    finally:
        conn.close()

# 执行查询
def executeSqlFetch(sql, params=()):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        except Exception as e:
            logging.error(f"SQLite executeSqlFetch error: {sql} {e}")
            return None

# 执行增删改
def executeSql(sql, params=()):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logging.error(f"SQLite executeSql error: {sql} {e}")
            raise

# 查询数量
def executeSqlCount(sql, params=()):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logging.error(f"SQLite executeSqlCount error: {sql} {e}")
            return 0

# 检查表是否存在
def checkTableIsExist(tableName):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (tableName,))
            return cursor.fetchone() is not None
        except Exception as e:
            logging.error(f"SQLite checkTableIsExist error: {tableName} {e}")
            return False

# 初始化数据库
init_sqlite_db()

# 兼容 Tornado DB 配置（SQLite 不需要）
MYSQL_CONN_TORNDB = {}

