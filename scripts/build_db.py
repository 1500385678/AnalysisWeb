"""AnalysisWeb build_db.py · 扫 IMG_ROOT 目录建新 AnalysisDb
用法:
  python scripts/build_db.py                # 默认 IMG_ROOT = Mobile/Style
  ANALYSISWEB_HOME=/path python scripts/build_db.py
"""
import os
import sys
import sqlite3
import hashlib
from datetime import datetime

# 1. 解析路径
ANALYSISWEB_HOME = os.environ.get(
    'ANALYSISWEB_HOME',
    r'D:\Mac\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis'
)
IMG_ROOT = os.path.normpath(os.path.join(ANALYSISWEB_HOME, 'Mobile', 'Style'))
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_AnalysisDb', 'AnalysisDb.db')

# 2. 准备 DB
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
print(f'[build_db] IMG_ROOT = {IMG_ROOT}')
print(f'[build_db] DB_PATH  = {DB_PATH}')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 3. 建表 (跟 PictureDb schema 对齐,精简版)
c.execute('''
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT,
    filename TEXT,
    rel_path TEXT,
    abs_path TEXT,
    ext TEXT,
    size_bytes INTEGER,
    scene TEXT,
    light TEXT,
    space TEXT,
    material TEXT,
    mood TEXT,
    caption TEXT,
    description TEXT,
    keywords TEXT,
    md_path TEXT,
    file_hash TEXT,
    phash TEXT,
    source TEXT,
    created_at TEXT,
    updated_at TEXT,
    arch_type TEXT,
    render_style TEXT,
    render_company TEXT,
    view_type TEXT,
    color_palette TEXT,
    scale TEXT,
    analysis_type TEXT,
    drawing_method TEXT,
    subject TEXT
)
''')

# 4. 扫目录
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
count = 0
for root, dirs, files in os.walk(IMG_ROOT):
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext not in IMAGE_EXTS:
            continue
        abs_path = os.path.join(root, f)
        try:
            size = os.path.getsize(abs_path)
        except OSError:
            continue
        rel_path = os.path.relpath(abs_path, IMG_ROOT).replace(os.sep, '/')
        # project 推断:父目录名(平铺时是 "Style")
        project = os.path.basename(root) if os.path.basename(root) != os.path.basename(IMG_ROOT) else 'Style'
        # file hash
        with open(abs_path, 'rb') as fp:
            h = hashlib.md5(fp.read()).hexdigest()
        now = datetime.now().isoformat(timespec='seconds')
        # phash: 简单实现 - 8x8 resize + 64-bit 灰度比较
        phash = None
        try:
            from PIL import Image
            img = Image.open(abs_path).convert('L').resize((8, 8))
            px = list(img.getdata())
            avg = sum(px) / len(px)
            phash = ''.join('1' if p > avg else '0' for p in px)
        except Exception:
            phash = '0' * 64
        c.execute('''
            INSERT INTO images (
                project, filename, rel_path, abs_path, ext, size_bytes,
                file_hash, phash, source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project, f, rel_path, abs_path, ext.lstrip('.'), size,
            h, phash, 'build_db', now, now
        ))
        count += 1
        print(f'  [{count}] {rel_path}  ({size} bytes)')

conn.commit()
conn.close()
print(f'\n[build_db] done. {count} images indexed in {DB_PATH}')
