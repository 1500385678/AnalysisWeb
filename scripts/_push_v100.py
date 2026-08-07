"""_push_v100.py · v1.0.0 首发推送脚本

工作流:
  1) 用 Contents API 推 1 个初始 file(README.md)建初始 commit
  2) 用 Git Data API 推剩余所有文件
  3) 创建 v1.0.0 tag
  4) 创建 v1.0.0 GitHub Release

绕开 TCP 443 被拦的 git push,只走 https://api.github.com
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

API = 'https://api.github.com'
REPO = '1500385678/AnalysisWeb'
BRANCH = 'main'
TAG = 'v1.0.0'

# 2026-08-08 Verifier P0 修复:ROOT 写死 Windows 路径 → env 注入 + os.path.dirname 兜底
# 默认值用 os.path.dirname 拿脚本所在目录(AnalysisWeb/scripts/_push_v100.py → AnalysisWeb),
# 不依赖任何 env,在 Mac/Windows/Linux 都能直接跑;Windows 路径漂移用 _push_macos.py 包装
ROOT = os.environ.get('ANALYSISWEB_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2026-08-08 Verifier P0 修复:Mac 上跑这个直推脚本会带 Windows 路径,FileNotFoundError 静默,
# 加平台守卫让用户改用 _push_macos.py 包装(后者从 origin URL 读 token + 改 ROOT)
if sys.platform == 'darwin' and ROOT.startswith(r'D:'):
    raise SystemExit('❌ ROOT 是 Windows 路径(D:\\...),在 Mac 上请用 scripts/_push_macos.py 包装推送')

# 推哪些文件(相对 ROOT)
# 排除:.gitignore 是第一个(必须有);favorites.json, _AnalysisDb/*, logs/*, thumbs/* 不进 git
FILES = [
    '.gitignore',
    'README.md',
    'AGENTS.md',
    'LICENSE',
    '__version__.py',
    'server.py',
    'index.html',
    'start.bat',
    'start.sh',
    'start_hidden.vbs',
    'libraryControl.md',
    'docs/3agent-workflow.md',
    'docs/phase6-design.md',
    'scripts/build_db.py',
    'scripts/git_data_push.py',
    'scripts/tag_images.py',
    'scripts/auto_release.py',
    'scripts/auto_dispatch.py',
    'scripts/auto_fixer_architect.py',
    'scripts/auto_tester.py',
    'scripts/batch_push.py',
    'scripts/daily_pipeline.py',
    'scripts/debug_tree.py',
    'scripts/feedback.py',
    'scripts/_check_autofix.py',
    'scripts/_demo_e2e.py',
    'scripts/_push_v100.py',
    'scripts/_push_gitee_v100.py',
    'tests/smoke.py',
]


def get_token():
    tok = os.environ.get('GH_TOKEN')
    if not tok and os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as k:
                tok = winreg.QueryValueEx(k, 'GH_TOKEN')[0]
        except (OSError, FileNotFoundError):
            pass
    if not tok:
        sys.exit('GH_TOKEN 未设')
    return tok


def request(path, method='GET', body=None, token=None):
    url = API + urllib.parse.quote(path, safe='/')
    data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': 'token ' + token,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json; charset=utf-8',
        'User-Agent': 'analysisweb-push-v100',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {'message': str(e)}
    except Exception as e:
        return 0, {'message': str(e)}


def push_initial_file(rel_path, token):
    """第 1 个文件用 Contents API PUT(空仓库需要先建初始 commit)"""
    full = os.path.join(ROOT, rel_path)
    with open(full, 'rb') as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode('ascii')
    body = {
        'message': f'initial commit: add {rel_path}',
        'content': b64,
        'branch': BRANCH,
    }
    print(f'  PUT /contents/{rel_path} (Contents API, init)...')
    s, d = request(f'/repos/{REPO}/contents/{rel_path}', method='PUT', body=body, token=token)
    if s in (200, 201):
        sha = d.get('content', {}).get('sha')
        print(f'  ✅ initial commit: {d["commit"]["sha"][:7]} (blob {sha[:7] if sha else "?"})')
        return d['commit']['sha']
    print(f'  ❌ init 失败: {s} {d.get("message")}')
    sys.exit(1)


def push_via_git_data(files, commit_msg, token):
    """用 Git Data API 推多个文件(走 blobs + tree + commit + ref)"""
    # 1) base commit
    s, ref = request(f'/repos/{REPO}/git/refs/heads/{BRANCH}', token=token)
    if s != 200:
        sys.exit(f'拿 base ref 失败: {s} {ref.get("message")}')
    base_sha = ref['object']['sha']

    s, cdata = request(f'/repos/{REPO}/git/commits/{base_sha}', token=token)
    if s != 200:
        sys.exit(f'拿 base commit 失败: {s} {cdata.get("message")}')
    base_tree = cdata['tree']['sha']
    print(f'  base commit: {base_sha[:7]} (tree {base_tree[:7]})')

    # 2) blobs
    entries = []
    for rel in files:
        full = os.path.join(ROOT, rel)
        with open(full, 'rb') as f:
            raw = f.read()
        b64 = base64.b64encode(raw).decode('ascii')
        s, blob = request(f'/repos/{REPO}/git/blobs', method='POST',
                          body={'content': b64, 'encoding': 'base64'}, token=token)
        if s not in (200, 201):
            sys.exit(f'create blob 失败({rel}): {s} {blob.get("message")}')
        entries.append({
            'path': rel.replace(os.sep, '/'),
            'mode': '100644',
            'type': 'blob',
            'sha': blob['sha'],
        })
        print(f'  blob: {rel} → {blob["sha"][:7]}')

    # 3) tree
    s, t = request(f'/repos/{REPO}/git/trees', method='POST',
                   body={'base_tree': base_tree, 'tree': entries}, token=token)
    if s not in (200, 201):
        sys.exit(f'create tree 失败: {s} {t.get("message")}')
    new_tree = t['sha']
    print(f'  tree: {new_tree[:7]}')

    # 4) commit
    s, nc = request(f'/repos/{REPO}/git/commits', method='POST',
                    body={'message': commit_msg, 'tree': new_tree, 'parents': [base_sha]},
                    token=token)
    if s not in (200, 201):
        sys.exit(f'create commit 失败: {s} {nc.get("message")}')
    new_sha = nc['sha']
    print(f'  commit: {new_sha[:7]}')

    # 5) update ref
    s, r = request(f'/repos/{REPO}/git/refs/heads/{BRANCH}', method='PATCH',
                   body={'sha': new_sha}, token=token)
    if s != 200:
        sys.exit(f'update ref 失败: {s} {r.get("message")}')
    print(f'  ref: {BRANCH} → {new_sha[:7]}')
    return new_sha


def create_tag(sha, token):
    """创建 v1.0.0 tag(走 GitHub API,ref 指向新 commit)"""
    s, d = request(f'/repos/{REPO}/git/refs', method='POST',
                   body={'ref': f'refs/tags/{TAG}', 'sha': sha}, token=token)
    if s == 201:
        print(f'  ✅ tag {TAG} 创建 ({sha[:7]})')
        return sha
    if s == 422 and 'already exists' in str(d.get('message', '')):
        print(f'  ⚠️  tag {TAG} 已存在,force 更新')
        s, d = request(f'/repos/{REPO}/git/refs/tags/{TAG}', method='PATCH',
                       body={'sha': sha, 'force': True}, token=token)
        if s == 200:
            print(f'  ✅ tag {TAG} force 更新 ({sha[:7]})')
            return sha
    print(f'  ❌ tag 创建失败: {s} {d.get("message")}')
    sys.exit(1)


def create_release(sha, token):
    body_md = """# AnalysisWeb v1.0.0 · 初始独立版本

## 这是什么

建筑方案分析图库,跟 8081 的 **PictureWeb** 是兄弟模块。PictureWeb 收效果图 / 参考图,AnalysisWeb 专门收**方案分析图**(轴测、平面、剖面、动线、视线、业态、爆炸图等)。

## 关键能力

- 端口 **8082**(兄弟 PictureWeb 是 8081)
- 多维标签检索:`analysis_type` / `drawing_method` / `subject` / `scale` / `render_style` / `view_type` / `color_palette` / `mood` 8 维
- 全文搜索 + 以图搜图(PIL pHash)
- 收藏夹
- 项目子目录隔离

## v1.0.0 变更

- 从 `PictureWeb` 拆出,作为方案分析图专用图库独立运营
- 端口 8081 → **8082**
- 环境变量 `PICTUREWEB_HOME` → `ANALYSISWEB_HOME`、`PICTUREWEB_TEST_PORT` → `ANALYSISWEB_TEST_PORT`
- `README.md` / `AGENTS.md` 改写为 AnalysisWeb 专属(9 维标签说明)
- DB schema 加 `analysis_type` 字段(方案分析图最关键的分类维度)
- `Style/` 11 张分析图大模型看图打标入库(全字段填充)
- 启动脚本 / gitignore / smoke 测试 / auto_release / git_data_push 全部同步重命名

## 启动

```bash
python -X utf8 server.py
# 打开 http://127.0.0.1:8082/
```

## 依赖

- Python 3.10+ 标准库
- `Pillow`(`pip install Pillow`)
- 图片根 `Mobile/`(仓库外,gitignore)

## 仓库

- 主仓库:https://github.com/1500385678/AnalysisWeb
- 前身:1500385678/PictureWeb(PictureWeb v2.x 继续在 8081 跑效果图)
- 创建时间:2026-07-24
"""
    s, d = request(f'/repos/{REPO}/releases', method='POST', body={
        'tag_name': TAG,
        'name': f'AnalysisWeb {TAG} · 初始独立版本',
        'body': body_md,
        'target_commitish': BRANCH,
        'draft': False,
        'prerelease': False,
    }, token=token)
    if s == 201:
        print(f'  ✅ Release: {d["html_url"]}')
        return d
    print(f'  ❌ Release 失败: {s} {d.get("message")}')
    sys.exit(1)


def main():
    print('=== AnalysisWeb v1.0.0 推送 ===')
    print(f'  repo: {REPO}')
    print(f'  branch: {BRANCH}')
    print(f'  files: {len(FILES)}')
    print()

    token = get_token()

    # 探测:仓库是否已经有 base commit?
    s, ref = request(f'/repos/{REPO}/git/refs/heads/{BRANCH}', token=token)
    if s == 200:
        # 已存在 base,直接走 Git Data API(可同时 add + modify)
        print(f'[!] 仓库已存在 base commit,跳过初始 commit,走 Git Data API 增量推送')
        sha = push_via_git_data(FILES, f'v1.0.0: sync to Gitee + add push scripts', token)
    else:
        # 1) 初始 commit
        print('[1/4] 初始 commit (Contents API)...')
        initial = FILES[0]
        rest = FILES[1:]
        push_initial_file(initial, token)

        # 2) 推剩余
        print()
        print(f'[2/4] 推剩余 {len(rest)} 个文件 (Git Data API)...')
        sha = push_via_git_data(rest, f'v1.0.0: initial AnalysisWeb release ({len(FILES)} files)', token)

    # 3) tag(只在首次或显式 force 时;已存在会报 422 → 自动 force)
    print()
    print(f'[3/4] 创建/更新 tag {TAG}...')
    create_tag(sha, token)

    # 4) release(已存在时 GitHub 会返 422,这里不强求成功)
    print()
    print('[4/4] 创建 GitHub Release...')
    rel = create_release(sha, token)
    if rel:
        print(f'✅ DONE: {rel["html_url"]}')
    else:
        print(f'✅ DONE: tag {TAG} → {sha[:7]} (release 已存在,跳过)')


if __name__ == '__main__':
    main()
