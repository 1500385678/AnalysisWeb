import sqlite3, os, sys, json, base64, logging  # 2026-08-08 P1:logging 顶上导入,做 _search 失败堆栈
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
import urllib.parse
import shutil

# 2026-07-24 v1.0.0 AnalysisWeb:用 ANALYSISWEB_HOME 环境变量 + 默认值,代替硬编码绝对路径
# 默认值跟原 hardcoded 一致,向后兼容(不设环境变量时行为不变)
# 换电脑或换盘符只需: set ANALYSISWEB_HOME=E:/your/path
ANALYSISWEB_HOME = os.environ.get('ANALYSISWEB_HOME', 'D:/Mac/Mac/workteam/05_space/03_architect/Attack/03-Analysis')
# 2026-08-10 P0 修复(R217):跟 scripts/build_db.py:48 一样,Mac 上默认值仍是 D:\ 路径立即 fail
# 引导用户 export ANALYSISWEB_HOME=.../Attack/03-Analysis 根目录绝对路径
if sys.platform == 'darwin' and ANALYSISWEB_HOME.startswith('D:'):
    print('[server] ❌ ANALYSISWEB_HOME 是 Windows 路径,在 Mac 上跑不动', file=sys.stderr)
    print('   请:export ANALYSISWEB_HOME=... (你的 Attack/03-Analysis 根目录绝对路径)', file=sys.stderr)
    sys.exit(1)
# DB:本项目私有 _AnalysisDb/AnalysisDb.db(2026-07-24 v1.0.0 从 PictureDb 拆出)
DB = os.path.join(os.path.dirname(__file__), '_AnalysisDb', 'AnalysisDb.db')
FAV_FILE = os.path.join(os.path.dirname(__file__), 'favorites.json')
# 图片根目录(2026-06-28 迁移到 Mobile)
IMG_ROOT = os.path.join(ANALYSISWEB_HOME, 'Mobile', 'Style')
# 旧 Mac 路径前缀(DB 里的路径是旧的,需要映射)
OLD_IMG_ROOT = '/Users/aaron/Mac/WorkTeam/05_Space/03_Architect/Mobile'

# 权限控制(2026-06-27 增加):只有本机 IP 可以写操作,其他电脑只读
# 读:GET /, GET /img/*, GET /api/search, GET /api/facets, GET /api/favorites
# 写:POST /api/favorites, POST /api/upload_search, POST /api/ai_image
# 2026-08-09 P0 修复:不再硬编码 192.168.181.136(PictureWeb 时代 Windows LAN),
# 该 IP 在 Mac mini 实际网段不存在,且 8-6 已用 _detect_lan_ip() 探测真实 LAN。
# 现在只保留 loopback(::1 + 127.0.0.1),启动时把探测到的 LAN IP 同步并入;
# ANALYSISWEB_ADMIN_IPS env 逗号分隔支持人工加白名单(例:团队内 10.0.0.50)。
ADMIN_IPS = {'127.0.0.1', '::1'}  # 本机 loopback;启动横幅 _detect_lan_ip() 同步并入本机 LAN
_env_ips = os.environ.get('ANALYSISWEB_ADMIN_IPS', '').strip()
if _env_ips:
    ADMIN_IPS.update(ip.strip() for ip in _env_ips.split(',') if ip.strip())
WRITE_PATHS = {'/api/favorites', '/api/upload_search', '/api/ai_image', '/api/semantic_search', '/api/intent_search'}

# 并发连接数限制(2026-06-28 调整):图片缩略图并发需求高,20 个
MAX_CONCURRENT = 20
active_lock = Lock()
active_count = 0
# 2026-08-10 P0:_ai_image 串行化锁(matrix MCP 一次接 1 路)
_ai_image_lock = Lock()
# 2026-08-11 P1 修复(R220):POST body 上限 8MB,防御 ImageBomb + 内存 OOM
# SimpleHTTPRequestHandler 没 max body 配置,_upload_search 接 base64 4/3 膨胀
# 8MB base64 → 解码后约 6MB 原图,够 _compute_phash 8x8 缩略用
MAX_POST_SIZE = 8 * 1024 * 1024
MAX_UPLOAD_RAW = 6 * 1024 * 1024  # _upload_search base64 解码后图像大小上限
# 2026-08-11 P0 修复(R218):limit 上下夹
LIMIT_MIN, LIMIT_MAX = 1, 200  # 200 = _upload_search top20 + 10x 余量

def load_favs():
    if not os.path.exists(FAV_FILE):
        return []
    try:
        with open(FAV_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

def save_favs(favs):
    with open(FAV_FILE, 'w', encoding='utf-8') as f:
        json.dump(favs, f, ensure_ascii=False, indent=2)

def to_img_url(abs_path):
    """将绝对路径转为 /img/ 相对 URL（兼容旧 Mac 路径）"""
    # 旧 Mac 路径 -> 新路径映射
    if abs_path.startswith(OLD_IMG_ROOT):
        abs_path = abs_path.replace(OLD_IMG_ROOT, IMG_ROOT)
    # 取相对于 IMG_ROOT 的路径
    try:
        rel = os.path.relpath(abs_path, IMG_ROOT).replace(os.sep, '/')
    except ValueError:
        rel = abs_path
    return '/img/' + rel

def cosine_sim(a, b):
    if not a or not b: return 0
    import math
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return dot / (na*nb) if na and nb else 0

class Handler(SimpleHTTPRequestHandler):
    def finish(self):
        """请求结束时减少并发计数"""
        global active_count
        with active_lock:
            active_count = max(0, active_count - 1)
        super().finish()

    def end_headers(self):
        # 2026-07-01: 强制 HTML 不缓存,避免浏览器用旧版
        # 仅对 HTML 生效,图片仍可缓存
        if self.path.endswith('.html') or self.path == '/' or self.path.endswith('/index.html'):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # /img/* 直接从 IMG_ROOT 提供静态文件
        if parsed.path.startswith('/img/'):
            rel = parsed.path[5:]
            # URL 解码
            rel = urllib.parse.unquote(rel)
            # 安全检查：不允许 .. 跳出
            rel_clean = os.path.normpath(rel).replace('\\', '/')
            if rel_clean.startswith('..') or os.path.isabs(rel_clean):
                self.send_error(403, 'Forbidden')
                return
            full = os.path.join(IMG_ROOT, rel_clean)
            if os.path.isfile(full):
                ext = full.rsplit('.', 1)[-1].lower()
                mime = {
                    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                    'png': 'image/png', 'gif': 'image/gif',
                    'webp': 'image/webp',
                }.get(ext, 'application/octet-stream')
                try:
                    sz = os.path.getsize(full)
                    self.send_response(200)
                    self.send_header('Content-Type', mime)
                    self.send_header('Content-Length', str(sz))
                    self.send_header('Cache-Control', 'public, max-age=3600')
                    self.end_headers()
                    with open(full, 'rb') as f:
                        # 流式传输 64KB chunk,避免大图(50MB+)wfile.write(f.read()) 一次性 OOM
                        shutil.copyfileobj(f, self.wfile, 64 * 1024)
                except Exception as e:
                    self.send_error(500, str(e))
            else:
                self.send_error(404, f'Not found: {rel_clean}')
            return

        if parsed.path == '/api/search':
            qs = urllib.parse.parse_qs(parsed.query)
            q = (qs.get('q', [''])[0] or '').strip()
            keywords = [k.strip() for k in (qs.get('keywords', [''])[0] or '').split(',') if k.strip()]
            project = (qs.get('project', [''])[0] or '').strip()
            scene = (qs.get('scene', [''])[0] or '').strip()
            light = (qs.get('light', [''])[0] or '').strip()
            mood = (qs.get('mood', [''])[0] or '').strip()
            arch = (qs.get('arch', [''])[0] or '').strip()
            company = (qs.get('company', [''])[0] or '').strip()
            view_type = (qs.get('view', [''])[0] or '').strip()
            # 2026-08-06 P1:6 个新维度查询参数
            analysis_type = (qs.get('analysis_type', [''])[0] or '').strip()
            drawing_method = (qs.get('drawing_method', [''])[0] or '').strip()
            subject = (qs.get('subject', [''])[0] or '').strip()
            scale = (qs.get('scale', [''])[0] or '').strip()
            render_style = (qs.get('render_style', [''])[0] or '').strip()
            color_palette = (qs.get('color_palette', [''])[0] or '').strip()
            favs_only = qs.get('favs_only', ['0'])[0] == '1'
            # 2026-08-11 P0 修复(R218):limit 解析 try/except + 上下夹 + SQL ? 参数化
            # 之前:limit = int(...) 无 try/except,?limit=abc 直接 ValueError → 500;
            # ?limit=9999999 让 SQL 全表扫+内存爆;f-string 拼 LIMIT 纵深防御缺失
            try:
                limit = int(qs.get('limit', ['60'])[0])
            except (ValueError, TypeError):
                limit = 60
            limit = max(LIMIT_MIN, min(limit, LIMIT_MAX))  # 上下夹,SQL ? 拼合法 int
            try:
                items = self._search(q, keywords, project, scene, light, mood, arch, company, view_type,
                                      analysis_type, drawing_method, subject, scale, render_style, color_palette,
                                      favs_only, limit)
                # 转换 path -> url
                for it in items:
                    it['url'] = to_img_url(it['path'])
                self._json({'count': len(items), 'items': items})
            except Exception as e:
                # 2026-08-08 Verifier P1 修复:不再 silent 200+error,跟其他 endpoint 对齐走 500
                # 同时 logging.exception 把堆栈写进 logs/,夜间 cron 巡检可定位
                logging.exception('_search 失败: q=%r project=%r view_type=%r', q, project, view_type)
                self._json({'error': str(e), 'count': 0, 'items': []}, status=500)
        elif parsed.path == '/api/facets':
            self._json(self._facets())
        elif parsed.path == '/api/favorites':
            self._json({'favorites': load_favs()})
        else:
            # 其它走父类（HTML/CSS/JS 静态文件）
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        # Issue #8:统一权限检查(WRITE_PATHS 之前是死列表)
        if parsed.path not in WRITE_PATHS:
            self.send_response(404); self.end_headers(); return
        # 权限检查(2026-06-27):非 ADMIN_IPS 内 IP 拒绝所有写操作
        if not self._is_admin():
            self._json({
                'error': f'权限不足:此操作仅限本机({" / ".join(ADMIN_IPS)})',
            }, status=403)
            return
        # 2026-08-11 P1 修复(R220):Content-Length 解析 try/except + MAX_POST_SIZE 8MB 守卫
        # 之前:int(...) 无 try/except,恶意 client 发 Content-Length: abc → ValueError → 500 堆栈泄露;
        # rfile.read(length) 无上限,POST body 可塞 GB 级(_upload_search base64 4/3 膨胀,SimpleHTTP 没 max body 配置 → 内存 OOM 风险)
        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
        except (ValueError, TypeError):
            self._json({'error': 'Content-Length 解析失败'}, status=400)
            return
        if length > MAX_POST_SIZE:
            self._json({'error': f'body 超过 {MAX_POST_SIZE // 1024 // 1024}MB 上限'}, status=413)
            return
        body = self.rfile.read(length) if length else b''
        try:
            data = json.loads(body or b'{}')
        except: data = {}
        if parsed.path == '/api/favorites':
            favs = load_favs()
            item_id = data.get('id')
            if item_id in favs:
                favs.remove(item_id)
            else:
                favs.append(item_id)
            save_favs(favs)
            self._json({'favorites': favs})
        elif parsed.path == '/api/upload_search':
            self._upload_search(data)
        elif parsed.path == '/api/ai_image':
            self._ai_image(data)
        elif parsed.path == '/api/semantic_search':
            text = data.get('q', '') or (urllib.parse.parse_qs(parsed.query).get('q', [''])[0] or '')
            self._semantic_search(text)
        elif parsed.path == '/api/intent_search':
            self._intent_search(data)
        else:
            self.send_response(404)
            self.end_headers()

    def _is_admin(self):
        """检查请求是否来自 ADMIN_IPS(自动从 config 同步,避免硬编码不一致)"""
        client_ip = self.client_address[0]
        return client_ip in ADMIN_IPS

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # 静默日志（写文件用 logging）
        pass

    def _search(self, q, keywords, project, scene, light, mood, arch, company, view_type,
                analysis_type, drawing_method, subject, scale, render_style, color_palette,
                favs_only, limit):
        import re as _re
        def tokenize(t):
            if not t: return ''
            t = t.lower()
            en = _re.findall(r'[a-z0-9]+', t)
            zh = _re.findall(r'[\u4e00-\u9fff]+', t)
            tokens = list(en)
            for w in zh:
                for i in range(len(w)):
                    if i+1 < len(w): tokens.append(w[i:i+2])
                    tokens.append(w[i])
            return ' '.join(set(tokens))

        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        use_fts = False
        fts_terms = []
        if q.strip():
            use_fts = True
            fts_terms.append(tokenize(q))
        if keywords:
            use_fts = True
            fts_terms.append(' AND '.join([tokenize(k) for k in keywords]))
        # 2026-08-06 P1 修复:9 维承诺不再空头。SELECT 拉满 9 维 + 6 维参数过滤
        select_cols = ('id, project, filename, abs_path, scene, light, space, material, mood, caption, phash, '
                       'arch_type, render_company, view_type, '
                       'analysis_type, drawing_method, subject, scale, render_style, color_palette')
        if use_fts:
            # 2026-08-06 P0 修复:replace 必须按 ', ' (带空格) 替换,否则生成 'i. project' 带空格的非法列名
            # 2026-08-08 Verifier P0 修复(R82):fts_q 未定义 → NameError;FTS5 MATCH 必须参数化;
            # tokenize 完剥单/双引号兜底,防 LIKE/MATCH 注入(O'Brien / L'église 等)
            def _sanitise_fts(s):
                if not s: return ''
                # FTS5 关键字预留引号,剥掉防语法错;反引号 / 退格 / 斜杠 / NUL 也清
                return _re.sub(r"[\"'`\\\x00\n\r\t]", ' ', s)
            fts_q = " ".join(_sanitise_fts(t) for t in fts_terms if t) or "*"
            sql = (f"SELECT DISTINCT i.{select_cols.replace(', ', ', i.')} "
                   f"FROM images_fts f JOIN images i ON i.id = f.id WHERE images_fts MATCH ?")
            params = [fts_q]
        else:
            sql = f"SELECT {select_cols} FROM images WHERE 1=1"
            params = []
        if project:
            sql += " AND i.project = ?" if use_fts else " AND project = ?"
            params.append(project)
        if scene:
            sql += " AND i.scene LIKE ?" if use_fts else " AND scene LIKE ?"
            params.append(f"%{scene}%")
        if light:
            sql += " AND i.light LIKE ?" if use_fts else " AND light LIKE ?"
            params.append(f"%{light}%")
        if mood:
            sql += " AND i.mood LIKE ?" if use_fts else " AND mood LIKE ?"
            params.append(f"%{mood}%")
        if arch:
            sql += " AND i.arch_type = ?" if use_fts else " AND arch_type = ?"
            params.append(arch)
        if company:
            sql += " AND i.render_company = ?" if use_fts else " AND render_company = ?"
            params.append(company)
        if view_type:
            sql += " AND i.view_type = ?" if use_fts else " AND view_type = ?"
            params.append(view_type)
        # 2026-08-06 P1:6 个新维度参数
        if analysis_type:
            sql += " AND i.analysis_type = ?" if use_fts else " AND analysis_type = ?"
            params.append(analysis_type)
        if drawing_method:
            sql += " AND i.drawing_method = ?" if use_fts else " AND drawing_method = ?"
            params.append(drawing_method)
        if subject:
            sql += " AND i.subject = ?" if use_fts else " AND subject = ?"
            params.append(subject)
        if scale:
            sql += " AND i.scale = ?" if use_fts else " AND scale = ?"
            params.append(scale)
        if render_style:
            sql += " AND i.render_style = ?" if use_fts else " AND render_style = ?"
            params.append(render_style)
        if color_palette:
            sql += " AND i.color_palette = ?" if use_fts else " AND color_palette = ?"
            params.append(color_palette)
        if favs_only:
            favs = load_favs()
            if not favs:
                return []
            sql += f" AND i.id IN ({','.join(['?']*len(favs))})" if use_fts else f" AND id IN ({','.join(['?']*len(favs))})"
            params += favs
        # 2026-08-11 P0 修复(R218):LIMIT 改 ? 参数化(已上下夹 max(LIMIT_MIN,min(LIMIT_MAX)),值是合法 int)
        sql += " ORDER BY i.id DESC LIMIT ?" if use_fts else " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        out = []
        for r in rows:
            out.append({
                'id': r['id'], 'project': r['project'], 'filename': r['filename'],
                'path': r['abs_path'], 'url': to_img_url(r['abs_path']),
                'scene': r['scene'] or '', 'light': r['light'] or '',
                'space': r['space'] or '', 'material': r['material'] or '',
                'mood': r['mood'] or '', 'caption': r['caption'] or '',
                'phash': r['phash'] or '',
                'arch_type': r['arch_type'] or '', 'render_company': r['render_company'] or '',
                'view_type': (r['view_type'] if 'view_type' in r.keys() else '') or '',
                # 2026-08-06 P1:6 个新维度回显
                'analysis_type': (r['analysis_type'] if 'analysis_type' in r.keys() else '') or '',
                'drawing_method': (r['drawing_method'] if 'drawing_method' in r.keys() else '') or '',
                'subject': (r['subject'] if 'subject' in r.keys() else '') or '',
                'scale': (r['scale'] if 'scale' in r.keys() else '') or '',
                'render_style': (r['render_style'] if 'render_style' in r.keys() else '') or '',
                'color_palette': (r['color_palette'] if 'color_palette' in r.keys() else '') or '',
            })
        conn.close()
        return out

    def _facets(self):
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        projects = [r[0] for r in conn.execute('SELECT DISTINCT project FROM images ORDER BY project').fetchall() if r[0]]
        scenes = sorted(set([s for r in conn.execute("SELECT scene FROM images WHERE scene IS NOT NULL AND scene != ''").fetchall() for s in (r[0] or '').split(';') if s.strip()]))
        lights = sorted(set([l for r in conn.execute("SELECT light FROM images WHERE light IS NOT NULL AND light != ''").fetchall() for l in (r[0] or '').split(';') if l.strip()]))
        moods = sorted(set([m for r in conn.execute("SELECT mood FROM images WHERE mood IS NOT NULL AND mood != ''").fetchall() for m in (r[0] or '').split(';') if m.strip()]))
        archs = sorted(set([a for a, in conn.execute("SELECT DISTINCT arch_type FROM images WHERE arch_type IS NOT NULL AND arch_type != ''").fetchall()]))
        companies = sorted(set([c for c, in conn.execute("SELECT DISTINCT render_company FROM images WHERE render_company IS NOT NULL AND render_company != ''").fetchall()]))
        # 2026-08-06 P1 修复:9 维承诺不再空头。6 维 DISTINCT 全给前端 chips
        def _distinct(col, split=False):
            sql = f"SELECT {col} FROM images WHERE {col} IS NOT NULL AND {col} != ''"
            rows = conn.execute(sql).fetchall()
            if not split:
                return sorted({r[0] for r in rows if r[0]})
            out = set()
            for r in rows:
                for v in (r[0] or '').split(';'):
                    if v.strip():
                        out.add(v.strip())
            return sorted(out)
        analysis_types = _distinct('analysis_type')
        drawing_methods = _distinct('drawing_method')
        subjects = _distinct('subject')
        scales = _distinct('scale')
        render_styles = _distinct('render_style')
        color_palettes = _distinct('color_palette')
        # 2026-08-08 Verifier P1 修复:view_types 不再硬编码 3 英文,改从 DB 实时 DISTINCT
        # 跟 analysis_types/drawing_methods 等保持一致:空列返 [],前端空 chip 无副作用
        view_types = _distinct('view_type')
        conn.close()
        return {
            'projects': projects, 'scenes': scenes, 'lights': lights, 'moods': moods,
            'archs': archs, 'companies': companies,
            'view_types': view_types,
            # 2026-08-06 P1:6 个新维度 facets(空列也会返 [],前端空 chip 也无副作用)
            'analysis_types': analysis_types,
            'drawing_methods': drawing_methods,
            'subjects': subjects,
            'scales': scales,
            'render_styles': render_styles,
            'color_palettes': color_palettes,
        }

    def _semantic_search(self, text):
        if not text:
            self._json({'error': 'q 不能为空', 'items': []})
            return
        # 2026-08-06 P1 修复:不再硬把父目录塞 sys.path(那强制 AnalysisWeb 必须
        # 部署在 _ArchiAttackAnalysisLib/ 下,违反 v1.0.0 独立运营 + GitHub 公开仓库承诺)
        # 改为读 ANALYSISWEB_EMBEDDING_DIR 环境变量,缺则返 501 友好错误
        embedding_dir = os.environ.get('ANALYSISWEB_EMBEDDING_DIR')
        if embedding_dir and os.path.isdir(embedding_dir):
            sys.path.insert(0, embedding_dir)
        try:
            import embedding  # noqa: E402
        except ImportError as e:
            self._json({
                'error': f'AI 语义搜索未配置:{e}。请设 ANALYSISWEB_EMBEDDING_DIR 环境变量指向含 embedding.py 的目录,或在父目录 _ArchiAttackAnalysisLib/ 下放 embedding.py',
                'items': []
            }, status=501)
            return
        try:
            results = embedding.search_by_text(text, 30)
            out = []
            for s, r in results:
                out.append({
                    'id': r['img_id'], 'project': r['project'], 'filename': r['filename'],
                    'path': r['abs_path'], 'url': to_img_url(r['abs_path']),
                    'scene': r['scene'] or '', 'light': '',
                    'space': '', 'material': '', 'mood': r['mood'] or '',
                    'caption': '', 'similarity': round(s*100, 1),
                })
            self._json({'count': len(out), 'items': out, 'query': text})
        except Exception as e:
            self._json({'error': '语义搜索失败: ' + str(e), 'items': []})

    def _intent_search(self, data):
        """设计意图找参考(2026-07-24 v2.0.6):
        用户输入自然语言描述(场地/体量/风格/材料...),返回 top 5 匹配案例 +
        每个案例的"为什么像" reasons(基于 metadata 匹配)
        不依赖外部 LLM,纯 FTS5 + metadata 模板生成。"""
        intent = (data.get('intent') or '').strip()
        if not intent:
            self._json({'error': 'intent 不能为空', 'items': []})
            return
        import re as _re
        def tokenize(t):
            t = t.lower()
            en = _re.findall(r'[a-z0-9]+', t)
            zh = _re.findall(r'[\u4e00-\u9fff]+', t)
            tokens = list(en)
            for w in zh:
                for i in range(len(w)):
                    if i+1 < len(w): tokens.append(w[i:i+2])
                    tokens.append(w[i])
            return tokens

        intent_tokens = tokenize(intent)
        if not intent_tokens:
            self._json({'error': 'intent 拆不出有效关键词', 'items': []})
            return

        # 中文 → metadata 关键词映射(让用户的口语描述能跟 metadata 对上)
        KEYWORD_MAP = {
            '混凝土': ['concrete', '混凝土'],
            '山地': ['mountain', 'slope', 'hillside', 'mountainous', '山', '坡'],
            '夜景': ['night', '夜景'],
            '日落': ['sunset', 'golden-hour', '黄昏', '夕'],
            '鸟瞰': ['bird-eye', 'bird', '鸟瞰'],
            '人视': ['eye-level', 'eye', '人视'],
            '轻盈': ['light', 'airy', 'slim', 'thin', '轻'],
            '大体量': ['large', 'monumental', 'huge', 'big', '大'],
            '小尺度': ['small', 'intimate', 'tiny', '小'],
            '文化': ['cultural', '文化'],
            '住宅': ['residential', 'residence', 'house', 'housing', '住宅'],
            '商业': ['commercial', 'commerce', '商业'],
            '学校': ['school', 'education', '学校', '教育'],
            '教堂': ['church', 'chapel', 'cathedral', '教堂'],
            '博物': ['museum', 'gallery', '博物'],
            '办公': ['office', 'workplace', '办公'],
            '酒店': ['hotel', 'hospitality', '酒店'],
            '木质': ['wood', 'timber', '木'],
            '钢': ['steel', 'metal', '钢'],
            '玻璃': ['glass', '玻璃'],
            '砖': ['brick', 'masonry', '砖'],
            '石': ['stone', 'rock', '石'],
            '绿色': ['green', 'landscape', '绿'],
            '水': ['water', 'pool', '水'],
            '光': ['light', 'daylight', '光'],
            '禅': ['zen', 'contemplative', 'meditation', '禅'],
            '神': ['sacred', 'spiritual', 'sacred', '神'],
        }
        meta_keywords = set()
        for k, vlist in KEYWORD_MAP.items():
            if k in intent:
                meta_keywords.update(vlist)
        # 也加 intent 自身 token(让 "教堂" 之类直接命中)
        for tok in intent_tokens:
            if len(tok) >= 2:
                meta_keywords.add(tok)

        # 2026-07-24 v2.0.6:images_fts 用 unicode61 tokenize 不支持中文,改用 LIKE
        # 取 intent_tokens + meta_keywords 并集,每个都 OR 一个 LIKE
        all_keywords = list(set(intent_tokens) | meta_keywords)
        all_keywords = [k for k in all_keywords if len(k) >= 2][:10]  # 限 10 个

        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        if all_keywords:
            conditions = []
            params = []
            for kw in all_keywords:
                conditions.append('(caption LIKE ? OR project LIKE ? OR scene LIKE ? OR material LIKE ? OR mood LIKE ? OR light LIKE ? OR arch_type LIKE ? OR space LIKE ? OR render_company LIKE ? OR filename LIKE ?)')
                params.extend([f'%{kw}%'] * 10)
            sql = (
                "SELECT id, project, filename, abs_path, scene, light, space, material, mood, caption, arch_type, view_type, render_company "
                "FROM images WHERE " + ' OR '.join(conditions) +
                " ORDER BY id DESC LIMIT 30"
            )
            rows = conn.execute(sql, params).fetchall()
        else:
            rows = []
        conn.close()

        # metadata 字段匹配打分
        def score(r):
            s = 0
            fields = {
                'project': (r['project'] or '').lower(),
                'caption': (r['caption'] or '').lower(),
                'scene': (r['scene'] or '').lower(),
                'light': (r['light'] or '').lower(),
                'material': (r['material'] or '').lower(),
                'space': (r['space'] or '').lower(),
                'mood': (r['mood'] or '').lower(),
                'arch_type': (r['arch_type'] or '').lower(),
            }
            for mk in meta_keywords:
                mk_l = mk.lower()
                for fname, fval in fields.items():
                    if mk_l in fval:
                        # material/mood/scene 字段命中权重高
                        s += 2 if fname in ('material', 'mood', 'arch_type', 'scene') else 1
            return s

        scored = [(score(r), r) for r in rows]
        scored.sort(key=lambda x: (-x[0], -x[1]['id']))
        # 取 score > 0 的前 5,不够则按 rank 补
        top = [r for s, r in scored if s > 0][:5]
        if len(top) < 5:
            for s, r in scored:
                if r not in top and s >= 0:
                    top.append(r)
                    if len(top) >= 5:
                        break

        # 生成 items + reasons
        items = []
        for idx, r in enumerate(top, 1):
            reasons = []
            # 头部 reason:项目 + 类型
            if r['project']: reasons.append(f"项目:{r['project']}")
            if r['arch_type']: reasons.append(f"类型:{r['arch_type']}")
            if r['scene']: reasons.append(f"场景:{r['scene']}")
            if r['view_type']: reasons.append(f"视角:{r['view_type']}")
            if r['light']: reasons.append(f"光线:{r['light']}")
            if r['material']: reasons.append(f"材质:{r['material']}")
            if r['space']: reasons.append(f"空间:{r['space']}")
            if r['mood']: reasons.append(f"氛围:{r['mood']}")
            if r['caption']: reasons.append(f"标题:{r['caption']}")
            if r['render_company']: reasons.append(f"渲染:{r['render_company']}")

            items.append({
                'id': r['id'],
                'rank': idx,
                'project': r['project'] or '',
                'filename': r['filename'] or '',
                'url': to_img_url(r['abs_path']),
                'path': r['abs_path'],
                'caption': r['caption'] or '',
                'scene': r['scene'] or '',
                'light': r['light'] or '',
                'material': r['material'] or '',
                'mood': r['mood'] or '',
                'arch_type': r['arch_type'] or '',
                'view_type': r['view_type'] or '',
                'reasons': reasons[:7],
                # 生图用 prompt 摘要(前端可一键带过去给 MCP)
                'prompt_hint': ' '.join([
                    (r['caption'] or ''),
                    (r['scene'] or ''),
                    (r['material'] or ''),
                    (r['light'] or ''),
                    (r['mood'] or ''),
                ]).strip(),
            })

        self._json({'intent': intent, 'count': len(items), 'items': items})

    def _upload_search(self, data):
        b64 = data.get('image', '')
        if not b64.startswith('data:image'):
            self._json({'error': '需要 image base64'})
            return
        try:
            raw = base64.b64decode(b64.split(',', 1)[1])
        except Exception as e:
            self._json({'error': 'base64 解码失败: ' + str(e)})
            return
        # 2026-08-11 P1 修复(R220):raw 解码后再 assert < 6MB,防御客户端送 base64 后压缩/重复填
        if len(raw) > MAX_UPLOAD_RAW:
            self._json({'error': f'解码后图像超过 {MAX_UPLOAD_RAW // 1024 // 1024}MB'}, status=413)
            return
        up_phash = self._compute_phash(raw)
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        # 2026-08-10 P1 修复(R144):pHash 全表扫改 SQL LIMIT 200 候选 + Python top20 early-break
        # 之前 1000+ 张时肉眼可感延迟;DB 增长 10k+ 会拖 100MB 内存
        # 简化策略:SQL 加 LIMIT 200(粗筛 200 候选),Python 端 heapq top20 早停
        # (未来 R 上 SQLite 表达式索引 (pHash ^ ?) BIT-AND 可做精确 ORDER BY,见 R144 改法 2)
        rows = conn.execute('SELECT id, project, filename, abs_path, scene, light, space, material, mood, caption, phash FROM images WHERE phash IS NOT NULL AND phash != "" LIMIT 200').fetchall()
        import heapq
        top = []  # (-dist, r) max-heap via neg key;top20 用 d 升序
        for r in rows:
            if not r['phash']: continue
            d = self._hamming(up_phash, r['phash'])
            if len(top) < 20:
                heapq.heappush(top, (-d, r))
            elif -top[0][0] > d:  # 当前最差 > 新 d → 替换
                heapq.heapreplace(top, (-d, r))
        # 排序输出:neg_d 降序 → d 升序(最近优先)
        out = []
        for neg_d, r in sorted(top, key=lambda x: -x[0]):
            d = -neg_d
            out.append({
                'id': r['id'], 'project': r['project'], 'filename': r['filename'],
                'path': r['abs_path'], 'url': to_img_url(r['abs_path']),
                'scene': r['scene'] or '', 'light': r['light'] or '',
                'space': r['space'] or '', 'material': r['material'] or '',
                'mood': r['mood'] or '', 'caption': r['caption'] or '',
                'similarity': round((64 - d) / 64 * 100, 1),
            })
        conn.close()
        self._json({'count': len(out), 'items': out})

    def _compute_phash(self, raw):
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(raw)).convert('L').resize((8, 8))
            px = list(img.getdata())
            avg = sum(px) / len(px)
            bits = ''.join('1' if p > avg else '0' for p in px)
            return bits
        except Exception:
            return '0' * 64

    def _ai_image(self, data):
        # 2026-08-10 P0 修复(R84/R143):并发 + 残留垃圾
        # 1) 每个请求用独立 tempfile(避免并发覆盖);
        # 2) 进程级 _ai_image_lock 串行化 mavis 调用(matrix MCP 同时只接 1 路);
        # 3) try/finally 兜底删临时文件,120s 超时/异常也不会残留磁盘。
        prompt = data.get('prompt', '').strip()
        if not prompt:
            self._json({'error': 'prompt 不能为空'})
            return
        import subprocess, re, tempfile
        req_fd, req_path = tempfile.mkstemp(prefix='_ai_prompt_', suffix='.json', dir=os.path.dirname(__file__))
        os.close(req_fd)
        try:
            with open(req_path, 'w', encoding='utf-8') as fp:
                json.dump({'prompt': prompt, 'aspect_ratio': '3:2', 'resolution': '2K'}, fp, ensure_ascii=False)
            cmd = ['mavis', 'mcp', 'call', 'matrix', 'matrix_generate_image', '--file', req_path]
            with _ai_image_lock:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            m = re.search(r'"output_url":\s*"([^"]+)"', r.stdout)
            if m:
                self._json({'path': m.group(1)})
            else:
                self._json({'error': (r.stdout or r.stderr)[:500]})
        except Exception as e:
            self._json({'error': str(e)})
        finally:
            try:
                os.unlink(req_path)
            except OSError:
                pass

    def _hamming(self, a, b):
        if not a or not b or len(a) != len(b): return 64
        return sum(1 for x, y in zip(a, b) if x != y)


class LimitedServer(ThreadingHTTPServer):
    """并发连接数限制(2026-06-27):
    - 最多 MAX_CONCURRENT 个并发连接
    - 超出返回 503 + '服务器忙'提示
    - 私人网站保护,避免被滥用
    """
    def process_request(self, request, client_address):
        global active_count
        with active_lock:
            if active_count >= MAX_CONCURRENT:
                # 主动拒绝(503)
                try:
                    request.sendall(b'HTTP/1.1 503 Service Unavailable\r\n')
                    request.sendall(b'Content-Type: text/plain; charset=utf-8\r\n')
                    request.sendall(b'Connection: close\r\n\r\n')
                    msg = f'服务器忙:同时连接已达上限 {MAX_CONCURRENT},请稍后重试'.encode('utf-8')
                    request.sendall(msg)
                except Exception:
                    pass
                finally:
                    request.close()
                return
            active_count += 1
        super().process_request(request, client_address)


def _ensure_db_schema():
    """2026-08-06 P1:启动时确保 9 维标签列齐全。
    DB 是 gitignore 的本地文件,可能来自老 build_db.py(只 26 列,缺
    analysis_type / drawing_method / subject)。每次启动幂等检查,缺则 ALTER TABLE。
    不丢老数据,新列默认 NULL,search 返空字符串。

    2026-08-10 P1(R145):同步 images_fts FTS5 虚拟表,确保 9 维列都在索引里。
    FTS5 schema 在 CREATE 时固定,老 DB images_fts 仍只 6 维,新 9 维全文匹配
    退化为 LIKE 全表扫;探测 images_fts 缺列 → DROP+重建+repopulate。"""
    if not os.path.exists(DB):
        return
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    existing = {row[1] for row in cur.execute('PRAGMA table_info(images)').fetchall()}
    needed = {
        'analysis_type': 'TEXT',
        'drawing_method': 'TEXT',
        'subject': 'TEXT',
        'scale': 'TEXT',
        'render_style': 'TEXT',
        'color_palette': 'TEXT',
        'view_type': 'TEXT',
    }
    added = []
    for col, typ in needed.items():
        if col not in existing:
            try:
                cur.execute(f'ALTER TABLE images ADD COLUMN {col} {typ}')
                added.append(col)
            except sqlite3.OperationalError as e:
                print(f'[schema] 加列 {col} 失败: {e}', flush=True)
    conn.commit()
    if added:
        print(f'[schema] 自动加列: {", ".join(added)} (老数据这些列会空,需重跑 build_db 重新打标)', flush=True)

    # 2026-08-10 P1 修复(R145):FTS5 虚拟表补 9 维列
    # 期望 images_fts schema 包含 16 列(id+9 维+6 老列),不匹配就重建
    fts_expected_cols = {'id', 'project', 'filename', 'caption', 'scene', 'material', 'mood',
                         'space', 'light', 'analysis_type', 'drawing_method', 'subject',
                         'scale', 'render_style', 'color_palette', 'view_type'}
    fts_actual_cols = set()
    try:
        fts_actual_cols = {row[1] for row in cur.execute('PRAGMA table_info(images_fts)').fetchall()}
    except sqlite3.OperationalError:
        # images_fts 完全不存在,跳到重建分支
        pass
    if fts_actual_cols != fts_expected_cols:
        print(f'[schema] ⚠️  images_fts schema 不匹配(实际 {len(fts_actual_cols)} 列,期望 {len(fts_expected_cols)} 列),重建中...', flush=True)
        # 老 DB 可能没 images_fts(完全没创建);或只有 6 列;都走 DROP+重建
        cur.execute('DROP TABLE IF EXISTS images_fts')
        cur.execute("""
            CREATE VIRTUAL TABLE images_fts USING fts5(
                id UNINDEXED, project, filename, caption, scene, material, mood,
                space, light, analysis_type, drawing_method, subject,
                scale, render_style, color_palette, view_type,
                content='', tokenize='unicode61'
            )
        """)
        # 从 images 表 repopulate
        cur.execute("""
            INSERT INTO images_fts (id, project, filename, caption, scene, material, mood,
                                    space, light, analysis_type, drawing_method, subject,
                                    scale, render_style, color_palette, view_type)
            SELECT id, project, filename, caption, scene, material, mood,
                   space, light, analysis_type, drawing_method, subject,
                   scale, render_style, color_palette, view_type
            FROM images
        """)
        n_repop = cur.rowcount
        conn.commit()
        print(f'[schema] ✅ images_fts 重建完成,repopulate {n_repop} 行 (含 9 维标签)', flush=True)

    conn.close()


def _detect_lan_ip():
    """自动探测本机 LAN IP(连 8.8.8.8:80 不发包,只读 socket 本端地址)
    2026-08-06 P1 修复:启动横幅不再硬编码 192.168.181.136(那是 PictureWeb 时代
    Windows LAN IP,现在 Mac mini 上的 LAN 网段不固定);探测失败时只打 loopback,
    让用户自己 `ifconfig | grep inet` 查。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


if __name__ == '__main__':
    # 2026-07-24 v1.0.0 AnalysisWeb:默认端口 8082,dev 用 9082 设环境变量
    import socket  # _detect_lan_ip 用
    _ensure_db_schema()  # 2026-08-06 P1:启动加 9 维列,缺则 ALTER
    port = int(os.environ.get('ANALYSISWEB_TEST_PORT', '8082'))
    host = '0.0.0.0'  # 监听所有接口
    os.chdir(os.path.dirname(__file__))
    print(f'AnalysisWeb 启动: http://127.0.0.1:{port}/', flush=True)
    lan_ip = _detect_lan_ip()
    if lan_ip:
        ADMIN_IPS.add(lan_ip)  # 2026-08-09 P0:本机 LAN IP 同步并入写白名单(只本进程)
        print(f'           局域网: http://{lan_ip}:{port}/  (需同网段)', flush=True)
    else:
        print(f'           (LAN IP 探测失败,同网段访问请用 `ifconfig | grep inet` 查看)', flush=True)
    if _env_ips:
        print(f'           ADMIN_IPS env 追加白名单: {_env_ips}', flush=True)
    print(f'DB: {DB}', flush=True)
    print(f'IMG_ROOT: {IMG_ROOT}', flush=True)
    print(f'并发上限: {MAX_CONCURRENT} 个连接', flush=True)
    try:
        LimitedServer((host, port), Handler).serve_forever()
    except OSError as e:
        # 2026-08-06 P0 修复:端口占用必须 sys.exit(1) 而非 sleep 10 后隐式 return 0
        # 之前 start.sh / launchctl / cron 都把端口冲突判为『成功』,夜间 cron 假阳性 green
        print(f'端口 {port} 占用: {e}', flush=True)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\n已关闭', flush=True)
        sys.exit(0)
