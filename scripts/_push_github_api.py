"""_push_github_api.py · 2026-08-08 批 1 GitHub API 推送(绕开 TCP 443 拦)

场景:本机 git+https 协议被拦(已知坑,见 AGENTS.md §5),但 api.github.com 通。
用法:本地 main 领先 origin/main N 个 commit,本脚本通过 Git Data API:
  1) 拿 origin/main 当前 SHA
  2) 把本地每个 commit 重放:blobs + tree + commit + ref
  3) 不动 token(token 在 origin URL 里,免明文写盘)

为什么不用 _push_v100.py:它推整个 FILES 列表一个 mega commit,
本场景要保留我 6 个独立 commit 历史,只能逐个重放。
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = '1500385678/AnalysisWeb'
BRANCH = 'main'
API = 'https://api.github.com'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 2026-08-08 批 1:本地 origin/main 缓存过期(GitHub 已领先),强制从 API 拿
OVERRIDE_REMOTE_HEAD = os.environ.get('OVERRIDE_REMOTE_HEAD')  # 留口子,默认走 API
# 待推 commit 列表(本地 origin/main 缓存过期时手动指定,避免 rev-list 漏推)
OVERRIDE_COMMITS = os.environ.get('OVERRIDE_COMMITS', '').split(',') if os.environ.get('OVERRIDE_COMMITS') else []


def get_token():
    """从 git config origin URL 提 token(避免明文写盘)"""
    out = subprocess.run(
        ['git', 'config', '--get', 'remote.origin.url'],
        cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    m = re.search(r'https://([^@]+)@', out)
    if m:
        return m.group(1)
    return os.environ.get('GH_TOKEN')


def request(path, method='GET', body=None, token=None):
    url = API + urllib.parse.quote(path, safe='/')
    data = json.dumps(body, ensure_ascii=False).encode('utf-8') if body else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': 'token ' + token,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json; charset=utf-8',
        'User-Agent': 'analysisweb-api-push',
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


def get_diff_for_commit(commit_sha):
    """用 git show 拿 commit 的 file diff(file path + base64 content)"""
    out = subprocess.run(
        ['git', 'show', '--format=', '--name-only', commit_sha],
        cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    files = [f for f in out.split('\n') if f]
    return files


def read_file_content(rel_path, commit_sha):
    """从指定 commit 拿文件原内容(utf-8)"""
    out = subprocess.run(
        ['git', 'show', f'{commit_sha}:{rel_path}'],
        cwd=ROOT, capture_output=True
    )
    return out.stdout  # bytes


def get_commit_info(commit_sha):
    """拿 commit 元信息(message, parents, tree)"""
    out = subprocess.run(
        ['git', 'log', '-1', '--format=%P%n%s', commit_sha],
        cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    parts = out.split('\n', 1)
    parents = [p for p in parts[0].split() if p]
    message = parts[1] if len(parts) > 1 else ''
    return parents, message


def push_blob(content_bytes, token):
    b64 = base64.b64encode(content_bytes).decode('ascii')
    s, d = request(f'/repos/{REPO}/git/blobs', method='POST',
                   body={'content': b64, 'encoding': 'base64'}, token=token)
    if s not in (200, 201):
        sys.exit(f'create blob 失败: {s} {d.get("message")}')
    return d['sha']


def push_tree(entries, base_tree_sha, token):
    s, d = request(f'/repos/{REPO}/git/trees', method='POST',
                   body={'base_tree': base_tree_sha, 'tree': entries}, token=token)
    if s not in (200, 201):
        sys.exit(f'create tree 失败: {s} {d.get("message")}')
    return d['sha']


def push_commit(message, tree_sha, parents, token):
    s, d = request(f'/repos/{REPO}/git/commits', method='POST',
                   body={'message': message, 'tree': tree_sha, 'parents': parents},
                   token=token)
    if s not in (200, 201):
        sys.exit(f'create commit 失败: {s} {d.get("message")}')
    return d['sha']


def update_ref(new_sha, token):
    s, d = request(f'/repos/{REPO}/git/refs/heads/{BRANCH}', method='PATCH',
                   body={'sha': new_sha}, token=token)
    if s != 200:
        sys.exit(f'update ref 失败: {s} {d.get("message")}')
    return d


def get_remote_head(token):
    s, d = request(f'/repos/{REPO}/git/refs/heads/{BRANCH}', token=token)
    if s == 200:
        return d['object']['sha']
    if s == 404:
        return None
    sys.exit(f'拿 remote head 失败: {s} {d.get("message")}')


def get_commit_tree(sha, token):
    # 2026-08-08 批 1:/git/commits/{sha} 对刚通过 Git Data API 创建的 commit 偶发 404,
    # 改用 /commits/{sha}(REST)拿 tree,语义等价
    s, d = request(f'/repos/{REPO}/commits/{sha}', token=token)
    if s != 200:
        sys.exit(f'拿 commit tree 失败(/commits): {s} {d.get("message")}')
    return d['commit']['tree']['sha']


def replay_commit(commit_sha, parent_sha, parent_tree_sha, token):
    """把一个 git commit 重放到 GitHub 上(用父 tree 作 base,只覆盖本 commit 改的文件)"""
    files = get_diff_for_commit(commit_sha)
    parents, message = get_commit_info(commit_sha)
    print(f'  → commit {commit_sha[:7]} "{message[:60]}" files={len(files)}')

    # 1) blobs
    entries = []
    for rel in files:
        try:
            content = read_file_content(rel, commit_sha)
        except subprocess.CalledProcessError:
            # 文件删除(本批没有这种情况)
            entries.append({
                'path': rel.replace(os.sep, '/'),
                'mode': '100644',
                'type': 'blob',
                'sha': None,  # GitHub 用 null sha 删
            })
            continue
        blob_sha = push_blob(content, token)
        entries.append({
            'path': rel.replace(os.sep, '/'),
            'mode': '100644',
            'type': 'blob',
            'sha': blob_sha,
        })

    # 2) tree
    new_tree = push_tree(entries, parent_tree_sha, token)

    # 3) commit
    new_sha = push_commit(message, new_tree, [parent_sha], token)
    return new_sha, new_tree


def main():
    token = get_token()
    if not token:
        sys.exit('GH_TOKEN / origin token 都没找到')

    # 1) 拿 remote head(允许 env 覆盖,本地缓存可能过期)
    remote_head = OVERRIDE_REMOTE_HEAD or get_remote_head(token)
    print(f'remote {BRANCH}: {remote_head[:7] if remote_head else "(空)"}')

    # 2) 拿本地领先 remote 多少 commit(优先 OVERRIDE_COMMITS,本地缓存过期时用)
    if OVERRIDE_COMMITS:
        commits_to_push = [c for c in OVERRIDE_COMMITS if c]
        print(f'使用 OVERRIDE_COMMITS 列表,共 {len(commits_to_push)} 个')
    elif remote_head:
        out = subprocess.run(
            ['git', 'rev-list', '--reverse', f'{remote_head}..HEAD'],
            cwd=ROOT, capture_output=True, text=True
        ).stdout.strip()
        commits_to_push = [c for c in out.split('\n') if c]
    else:
        out = subprocess.run(
            ['git', 'rev-list', '--reverse', 'HEAD'],
            cwd=ROOT, capture_output=True, text=True
        ).stdout.strip()
        commits_to_push = [c for c in out.split('\n') if c]
    print(f'待推 {len(commits_to_push)} 个 commit')
    if not commits_to_push:
        print('已同步,无需 push')
        return

    # 3) 重放每个 commit
    current_sha = remote_head
    if current_sha:
        current_tree = get_commit_tree(current_sha, token)
    else:
        current_tree = None

    for i, c in enumerate(commits_to_push, 1):
        print(f'\n[{i}/{len(commits_to_push)}] replaying {c[:7]}...')
        new_sha, current_tree = replay_commit(c, current_sha, current_tree, token)
        print(f'  ✅ new: {new_sha[:7]}')
        # update remote ref
        update_ref(new_sha, token)
        current_sha = new_sha

    print()
    print(f'✅ DONE: {len(commits_to_push)} commits pushed to {REPO}@{BRANCH}')


if __name__ == '__main__':
    main()
