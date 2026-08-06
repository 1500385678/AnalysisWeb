"""AnalysisWeb build_db.py · 扫 IMG_ROOT 目录建新 AnalysisDb

用法:
  python scripts/build_db.py                 # 默认 IMG_ROOT = Mobile/Style
                                              # 行为: 删旧 DB,重建空表,只插文件元数据(无标签)
  python scripts/build_db.py --incremental   # 增量模式: 保留旧 DB,只插新文件,已存在跳过
  python scripts/build_db.py --keep          # 同 --incremental (别名,语义更清晰)
  ANALYSISWEB_HOME=/path python scripts/build_db.py

⚠️ 默认模式会清空所有 9 维标签(AnalysisDb.db 是 gitignore 私有数据,build_db 不打标):
  流程必须两步:
    1. python scripts/build_db.py --incremental  # 建库
    2. python scripts/tag_images.py              # 调 LLM 看图打标 9 维标签(已存在)
  单独跑 build_db 不打标 → 标签全 NULL → /api/search 9 维 facet 永远空
"""
import os
import sys
import sqlite3
import hashlib
import argparse
from datetime import datetime

# 1. 解析参数
parser = argparse.ArgumentParser(description='AnalysisWeb build_db · 扫 IMG_ROOT 建库')
parser.add_argument('--incremental', '--keep', dest='incremental', action='store_true',
                    help='增量模式: 保留旧 DB,按 file_hash 跳过已存在文件,新文件追加')
args = parser.parse_args()
INCREMENTAL = args.incremental

# 2. 解析路径
ANALYSISWEB_HOME = os.environ.get(
    'ANALYSISWEB_HOME',
    r'D:\Mac\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis'
)
IMG_ROOT = os.path.normpath(os.path.join(ANALYSISWEB_HOME, 'Mobile', 'Style'))
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_AnalysisDb', 'AnalysisDb.db')

# 3. 准备 DB
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
print(f'[build_db] mode      = {"INCREMENTAL" if INCREMENTAL else "REBUILD (会清空旧 DB)"}')
print(f'[build_db] IMG_ROOT  = {IMG_ROOT}')
print(f'[build_db] DB_PATH   = {DB_PATH}')

is_new_db = not os.path.exists(DB_PATH)
if not INCREMENTAL and not is_new_db:
    print(f'[build_db] ⚠️  默认模式: 删除旧 DB (所有 9 维标签会丢失)')
    print(f'[build_db] 💡 若要保留标签: 改用 --incremental')
    os.remove(DB_PATH)
elif INCREMENTAL and not is_new_db:
    print(f'[build_db] 增量模式: 保留旧 DB,跳过已存在 file_hash')
else:
    print(f'[build_db] 新建 DB: {DB_PATH}')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 4. 建表(只在 DB 不存在或被清空时执行)
# 跟 PictureDb schema 对齐,精简版
c.execute('''
CREATE TABLE IF NOT EXISTS images (
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

# 5. 增量模式: 预读已存在 file_hash 集合,跳过重复
existing_hashes = set()
if INCREMENTAL and not is_new_db:
    c.execute("SELECT file_hash FROM images WHERE file_hash IS NOT NULL")
    existing_hashes = {r[0] for r in c.fetchall() if r[0]}
    print(f'[build_db] 已存在 {len(existing_hashes)} 个 file_hash,增量比对中...')

# 6. 扫目录
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
count = 0
skipped = 0
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
        # 增量模式: 已存在跳过
        if INCREMENTAL and h in existing_hashes:
            skipped += 1
            continue
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
mode_note = '增量' if INCREMENTAL else '全量重建'
print(f'\n[build_db] done. {mode_note}入库 {count} 张,跳过 {skipped} 张已存在 → {DB_PATH}')
if not INCREMENTAL:
    print(f'[build_db] ⚠️  下一步必须跑打标: python scripts/tag_images.py  (否则 9 维标签全 NULL)')
elif count > 0:
    print(f'[build_db] 新增 {count} 张,若要打标: python scripts/tag_images.py')
else:
    print(f'[build_db] 无新增,无需打标')
