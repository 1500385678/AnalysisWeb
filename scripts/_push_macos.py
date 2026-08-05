"""_push_macos.py · 2026-08-06 批 3 macOS 包装

复用 _push_v100.py 的 Contents/Git Data API 逻辑,只覆盖两件事:
1) ROOT 改 macOS 路径
2) GH_TOKEN 从 `git config --get remote.origin.url` 提取(避免明文写盘)
"""
import os
import re
import sys

# 覆盖 ROOT(原始脚本是 Windows 路径)
sys.path.insert(0, os.path.dirname(__file__))
import _push_v100 as base  # noqa: E402

base.ROOT = '/Users/aaron/Mac/WorkTeam/05_Space/03_Architect/Attack/03-Analysis/_ArchiAttackAnalysisLib/AnalysisWeb'

# 提取 origin URL 里的 token
def _extract_token():
    import subprocess
    out = subprocess.run(
        ['git', 'config', '--get', 'remote.origin.url'],
        cwd=base.ROOT, capture_output=True, text=True
    ).stdout.strip()
    m = re.search(r'https://([^@]+)@', out)
    if m:
        return m.group(1)
    return os.environ.get('GH_TOKEN')

# 覆盖 get_token,优先 origin URL 里的 token
def get_token_override():
    tok = _extract_token()
    if tok:
        return tok
    sys.exit('GH_TOKEN / origin token 都没找到')
base.get_token = get_token_override

# 跑
if __name__ == '__main__':
    base.main()
