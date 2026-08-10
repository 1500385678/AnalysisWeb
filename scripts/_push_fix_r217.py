"""夜间迭代批 7 · R217 Gitee 推送脚本(临时,可复用)

- Contents API 一文件一 commit 推 server.py + AGENTS.md 到 master 分支
- Gitee 没有 Git Data API,不能一次 commit 推多文件
- token 从 git remote URL 抽(本机 macOS env 没设 GITEE_PAT)
- 后续夜间迭代如遇 Gitee 单文件推送场景,改 FILES 列表复用即可
"""
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

API = 'https://gitee.com/api/v5'
OWNER = 'architectzy'
REPO = 'AnalysisWeb'
BRANCH = 'master'
ROOT = '/Users/aaron/Mac/WorkTeam/05_Space/03_Architect/Attack/03-Analysis/_ArchiAttackAnalysisLib/AnalysisWeb'

# 从 git remote URL 抽 token
remote_gitee = subprocess.check_output(
    ['git', 'remote', 'get-url', 'gitee'], cwd=ROOT
).decode().strip()
# Gitee remote: https://architectzy:TOKEN@gitee.com/architectzy/AnalysisWeb.git
parsed = urllib.parse.urlparse(remote_gitee)
token = parsed.password
if not token:
    print(f'❌ 无法从 gitee remote URL 抽 token: {remote_gitee}', file=sys.stderr)
    sys.exit(1)

FILES = [
    # 默认值:夜间迭代批 7 实际推送内容。后续夜间迭代根据需要修改这个列表即可复用。
    ('server.py', 'fix(P0 R217): server.py Mac 守卫(夜间迭代批 7)'),
    ('AGENTS.md', 'fix(P0 R217): AGENTS.md §15 批 7 变更记录(夜间迭代批 7)'),
]


def put_file(rel_path, message):
    abs_path = os.path.join(ROOT, rel_path)
    with open(abs_path, 'rb') as f:
        content = f.read()
    content_b64 = base64.b64encode(content).decode('ascii')

    # 拿当前 SHA(文件不存在 → POST 新建;存在 → PUT 更新)
    url = f'{API}/repos/{OWNER}/{REPO}/contents/{rel_path}?ref={BRANCH}&access_token={token}'
    cur_sha = None
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            cur = json.loads(r.read())
        if isinstance(cur, dict):
            cur_sha = cur['sha']
            print(f'  cur  {rel_path}: sha={cur_sha[:10]} size={cur["size"]} (PUT update)')
        else:
            print(f'  cur  {rel_path}: 不存在 (POST create)')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f'  cur  {rel_path}: 404 (POST create)')
        else:
            raise

    # POST 新建 / PUT 更新(Gitee Contents API 区分方法)
    method = 'PUT' if cur_sha else 'POST'
    put_url = f'{API}/repos/{OWNER}/{REPO}/contents/{rel_path}?access_token={token}'
    payload = {
        'access_token': token,
        'content': content_b64,
        'message': message,
        'branch': BRANCH,
    }
    if cur_sha:
        payload['sha'] = cur_sha
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        put_url, data=body, method=method,
        headers={'Content-Type': 'application/json;charset=utf-8'},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read())
        print(f'  ✅   {rel_path}: new commit {resp["commit"]["sha"][:10]}')
        return True
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())
        except Exception:
            err = {'message': e.reason}
        print(f'  ❌   {rel_path}: {e.code} {err.get("message")}')
        return False


def main():
    print(f'=== 推 {len(FILES)} 个文件到 Gitee {OWNER}/{REPO}@{BRANCH} ===')
    ok = 0
    for rel, msg in FILES:
        if put_file(rel, msg):
            ok += 1
    print()
    print(f'✅ {ok}/{len(FILES)} 成功')
    sys.exit(0 if ok == len(FILES) else 1)


if __name__ == '__main__':
    main()
