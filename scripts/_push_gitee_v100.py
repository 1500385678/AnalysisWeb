"""_push_gitee_v100.py · Gitee 推送脚本(配合 _push_v100.py 同步 GitHub)

- 2026-07-25 v1.0.0 同步
- Gitee 没有 Git Data API,用 Contents API 一文件一 commit 推
- 自动建仓库 / 推文件 / 建 release

用法:
  python -X utf8 scripts/_push_gitee_v100.py
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = 'https://gitee.com/api/v5'
OWNER = 'architectzy'
REPO = 'AnalysisWeb'
BRANCH = 'master'  # Gitee 默认是 master,不是 main
GITEE_PAT = '5ed52babcbfa332404a11863bc065b00'

ROOT = r'D:\Mac\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis\_ArchiAttackAnalysisLib\AnalysisWeb'

# 推哪些文件(顺序很重要,第一个 PUT 后才有 base commit)
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

DESC = "建筑方案分析图库 · 多维标签 + 全文搜索 + 以图搜图 · 端口 8082 · v1.0.0"


def request(path, method='GET', body=None, query=None):
    """Gitee API 调用。鉴权:access_token query 参数(走 Authorization header Gitee 偶尔不稳)"""
    url = API + path
    if query is None:
        query = {}
    query['access_token'] = GITEE_PAT
    if body is not None:
        query['_method'] = method  # Gitee 偶发需 _method
    qs = urllib.parse.urlencode(query)
    full_url = f'{url}?{qs}'
    data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body else None
    req = urllib.request.Request(
        full_url, data=data, method=method,
        headers={
            'Content-Type': 'application/json;charset=UTF-8',
            'User-Agent': 'analysisweb-gitee-push',
        },
    )
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


def create_repo():
    """建仓(空仓默认 private 也行,后面推完首文件再 PATCH public)"""
    print('[1/4] 创建 Gitee 仓库...')
    s, d = request(
        '/user/repos',
        method='POST',
        body={
            'name': REPO,
            'description': DESC,
            'has_issues': True,
            'has_wiki': True,
        },
    )
    if s == 201:
        print(f'  ✅ created: {d.get("full_name")} initial_public={d.get("public")}')
    elif s == 422:
        # 已存在
        print('  ⚠️  已存在,跳过创建')
    else:
        print(f'  ❌ 创建失败: {s} {d.get("message")}')
        sys.exit(1)


def set_public():
    """推完首文件后 PATCH 改 public(Gitee 规定空仓不能改 public)"""
    print('  PATCH repo → public...')
    s, d = request(
        f'/repos/{OWNER}/{REPO}',
        method='PATCH',
        body={
            'name': REPO,
            'description': DESC,
            'private': False,
            'has_issues': True,
            'has_wiki': True,
        },
    )
    if s == 200:
        print(f'  ✅ repo → public={d.get("public")} private={d.get("private")}')
        return d
    print(f'  ❌ PATCH 失败: {s} {d.get("message")}')
    sys.exit(1)


def push_files():
    print()
    print(f'[2/4] 推 {len(FILES)} 个文件 (Contents API)...')
    for i, rel in enumerate(FILES, 1):
        full = os.path.join(ROOT, rel)
        with open(full, 'rb') as f:
            raw = f.read()
        b64 = base64.b64encode(raw).decode('ascii')

        # 第一个文件先推,推完调 set_public() 把仓改成 public(Gitee 规定空仓不能公开)
        encoded_path = urllib.parse.quote(rel, safe='/')
        s, d = request(
            f'/repos/{OWNER}/{REPO}/contents/{encoded_path}',
            method='POST',
            body={
                'content': b64,
                'message': f'v1.0.0: add {rel}',
                'branch': BRANCH,
            },
        )
        if s in (200, 201):
            print(f'  [{i:>2}/{len(FILES)}] POST {rel:<35s} ✅ ({d.get("commit", {}).get("sha", "?")[:7]})')
            if i == 1:
                print()
                set_public()
                print()
            continue
        # 已存在 → 拿 sha 后 PUT(Gitee 报错码 400/422 都有可能,看 message)
        msg = str(d.get('message', ''))
        if (s in (400, 422)) and ('已存在' in msg or 'exist' in msg.lower() or '已存在' in str(d.get('error', {}).get('base', ''))):
            s2, d2 = request(f'/repos/{OWNER}/{REPO}/contents/{encoded_path}', query={'ref': BRANCH})
            if s2 == 200:
                old_sha = d2.get('sha')
                s3, d3 = request(
                    f'/repos/{OWNER}/{REPO}/contents/{encoded_path}',
                    method='PUT',
                    body={
                        'content': b64,
                        'message': f'v1.0.0: update {rel}',
                        'branch': BRANCH,
                        'sha': old_sha,
                    },
                )
                if s3 in (200, 201):
                    print(f'  [{i:>2}/{len(FILES)}] PUT  {rel:<35s} ✅ (already existed, updated)')
                    continue
                print(f'  ❌ PUT {rel} 失败: {s3} {d3.get("message")}')
                sys.exit(1)
        print(f'  ❌ POST {rel} 失败: {s} {d.get("message")}')
        sys.exit(1)
    print(f'  ✅ {len(FILES)} 个文件推送完成')


def create_release():
    print()
    print('[3/4] 创建 v1.0.0 tag...')
    # Gitee 通过 release API 间接建 tag
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

## 仓库

- GitHub: https://github.com/1500385678/AnalysisWeb
- Gitee: https://gitee.com/architectzy/AnalysisWeb
- 前身:1500385678/PictureWeb(PictureWeb v2.x 继续在 8081 跑效果图)
- 创建时间:2026-07-24
"""
    # Gitee 创建一个 release tag
    s, d = request(
        f'/repos/{OWNER}/{REPO}/releases',
        method='POST',
        body={
            'tag_name': 'v1.0.0',
            'name': 'AnalysisWeb v1.0.0 · 初始独立版本',
            'body': body_md,
            'target_commitish': BRANCH,
            'prerelease': False,
        },
    )
    if s in (200, 201):
        print(f'  ✅ Release: {d.get("html_url")}')
        return d
    print(f'  ❌ Release 失败: {s} {d.get("message")}')
    # 已知 Gitee release API 偶尔 422 因为已存在
    if s == 422 and 'already' in str(d.get('message', '')).lower():
        print('  ⚠️  Release 已存在,跳过')
        return None
    return None


def verify():
    print()
    print('[4/4] 验证...')
    s, d = request(f'/repos/{OWNER}/{REPO}')
    if s != 200:
        print(f'  ❌ 验证失败: {s}')
        return
    print(f'  repo:     {d.get("full_name")}')
    print(f'  url:      {d.get("html_url")}')
    print(f'  public:   {d.get("public")}')
    print(f'  default:  {d.get("default_branch")}')
    print(f'  size:     {d.get("size")}KB')
    print(f'  stars:    {d.get("watchers_count", 0)}')
    s2, d2 = request(f'/repos/{OWNER}/{REPO}/contents/')
    if s2 == 200 and isinstance(d2, list):
        print(f'  files:    {len(d2)} 个顶层条目')


def main():
    print('=== AnalysisWeb v1.0.0 · Gitee 推送 ===')
    print(f'  owner: {OWNER}')
    print(f'  repo:  {REPO}')
    print(f'  branch: {BRANCH}')
    print(f'  files: {len(FILES)}')
    print()

    create_repo()
    push_files()
    create_release()
    verify()

    print()
    print('NOTE: Gitee 推 28 个文件一个一个 POST/PUT,后续若要同步 GitHub 改的文件,')
    print('      跑本脚本即可(Gitee 已存在就走 PUT 更新),无需手动删仓')

    print()
    print(f'✅ DONE: https://gitee.com/{OWNER}/{REPO}')


if __name__ == '__main__':
    main()
