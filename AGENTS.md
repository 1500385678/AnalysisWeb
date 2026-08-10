# AGENTS.md — AnalysisWeb 项目真值源

> Agent 必读。本文件描述项目是什么、怎么工作,任何 agent 进项目都先读这一份。

## 0. 项目是什么

**AnalysisWeb** 是独立的**建筑方案分析图库**检索系统。多维标签 + 全文搜索 + 以图搜图。
端口 **8082** · Python 标准库 + Pillow · 零 npm 依赖。

**前身**: 从 `PictureWeb` (仓库 `1500385678/PictureWeb`,端口 8081) 拆出,2026-07-24 **v1.0.0** 独立运营。
PictureWeb 收效果图 / 参考图,AnalysisWeb 专门收**方案分析图**(轴测、平面、剖面、动线、视线、业态、爆炸等)。

**定位**: 不是"找好看的图",是"做方案时找同类型分析方法、找同尺度同主题的参考"。

## 1. 关键属性

| 项 | 值 |
|---|---|
| 工作目录 | `$ANALYSISWEB_HOME/_ArchiAttackAnalysisLib/AnalysisWeb/`(Mac: `/Users/aaron/Mac/WorkTeam/05_Space/03_Architect/Attack/03-Analysis/_ArchiAttackAnalysisLib/AnalysisWeb/`;Windows: `D:\Mac\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis\_ArchiAttackAnalysisLib\AnalysisWeb\`) |
| 远端仓库 | **GitHub** `https://github.com/1500385678/AnalysisWeb` (public, 2026-07-24 v1.0.0) · **Gitee 镜像** `https://gitee.com/architectzy/AnalysisWeb` (public, 2026-07-25 v1.0.0,互不依赖) |
| 远端主分支 | `main` |
| 当前版本 | `v1.0.0` (`__version__.py`) |
| 启动命令 | `python -X utf8 server.py` (Windows) 或双击 `start.bat` |
| 默认 URL | http://127.0.0.1:8082/ |
| 数据库 | `_AnalysisDb/AnalysisDb.db` (本项目私有,gitignore) |
| 图片根 | `$ANALYSISWEB_HOME/Mobile/`(Mac: `/Users/aaron/Mac/WorkTeam/05_Space/03_Architect/Attack/03-Analysis/Mobile`;Windows: `D:\Mac\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis\Mobile`) |
| 缩略图缓存 | `thumbs/` (gitignore) |
| 日志 | `logs/` (gitignore) |
| 兄弟项目 | PictureWeb(8081) 收效果图 / 参考图,共用 `AnalysisWeb` 检索壳 |
| 环境变量 | `ANALYSISWEB_HOME`(图片根父目录)、`ANALYSISWEB_TEST_PORT`(端口覆盖)、`ANALYSISWEB_EMBEDDING_DIR`(AI 语义搜 embedding.py 目录,缺则 501)、`ANALYSISWEB_ADMIN_IPS`(逗号分隔人工白名单,批 5 加) |

> **平台路径**:路径写法以本机实际为准,本表是 AGENTS.md 文档值,真值看 `ANALYSISWEB_HOME` 环境变量;Mac 跑必须 `export ANALYSISWEB_HOME=...`(见 §7 坑)

## 2. 目录结构

```
AnalysisWeb/
├── server.py             # 后端(单文件,847 行 · 2026-08-11 P2 行数同步)
├── index.html            # 搜索主页(CSS+JS 内嵌,苹果风浅色,1352 行)
├── start.bat / start.sh  # 启动脚本(均带 -X utf8 · 跨平台镜像)
├── start_hidden.vbs      # 无窗口启动(Windows)
├── libraryControl.md     # Obsidian control 文件(排长索引员 · 当前 v1.0.0/8082/9 维 · 2026-08-08 方案A 重写)
├── LICENSE               # 许可证
├── favorites.json        # 收藏(运行时,gitignore)
├── thumbs/               # 缩略图缓存(运行时,gitignore)
├── AGENTS.md             # 本文件
├── README.md             # 用户档
├── __version__.py        # 版本号源
├── _AnalysisDb/
│   └── AnalysisDb.db     # SQLite 数据库(gitignore)
├── docs/
│   ├── 3agent-workflow.md  # 3-Agent 流水线手册(从 PictureWeb 继承,模板用)
│   └── phase6-design.md    # Phase 6 设计(从 PictureWeb 继承)
├── scripts/
│   ├── build_db.py          # 扫 IMG_ROOT → 建库(9 维标签列齐全)
│   ├── git_data_push.py     # Git Data API 推送
│   ├── _push_v100.py        # GitHub 推送(Contents API)
│   ├── _push_gitee_v100.py  # Gitee 推送(Contents API)
│   ├── auto_release.py      # release + bump + tag
│   ├── auto_dispatch.py     # (从 PictureWeb 继承,模板用)
│   ├── auto_fixer_architect.py # (从 PictureWeb 继承,模板用)
│   ├── auto_tester.py       # (从 PictureWeb 继承,模板用)
│   ├── daily_pipeline.py    # (从 PictureWeb 继承,模板用)
│   ├── feedback.py          # (从 PictureWeb 继承,模板用)
│   ├── batch_push.py        # (从 PictureWeb 继承,模板用)
│   ├── debug_tree.py        # (从 PictureWeb 继承,模板用)
│   ├── _demo_e2e.py         # (从 PictureWeb 继承,模板用)
│   └── tag_images.py        # LLM 打标(后续可挂 cron)
├── tests/
│   └── smoke.py            # 烟雾测试
└── logs/                  # 重要事件日志(归档,小写 · 2026-07-27 起)
```

## 3. API 速览

公开端点: `/api/search` `/api/facets` `/api/favorites` (GET)
本机端点 (`127.0.0.1` / `::1` + 启动时 `_detect_lan_ip()` 探测到的本机 LAN + `ANALYSISWEB_ADMIN_IPS` env 逗号分隔): `POST /api/favorites` `POST /api/upload_search`

> **入参约束**(2026-08-11 P0/P1 加):
> - `/api/search?limit=N`:N 解析 try/except + 上下夹 **1 ≤ N ≤ 200**(默认 60),SQL 用 `LIMIT ?` 参数化(R218)
> - `POST /api/upload_search` / `/api/favorites` 等所有写端点:body ≤ **8MB**,Content-Length 解析 try/except + 413 守卫(R220)
> - `_upload_search` base64 解码后图像 ≤ **6MB**(R220 防 ImageBomb)

完整列表 + 权限: `server.py:ADMIN_IPS` + README.md

## 4. 标签维度(AnalysisWeb 专用,非 PictureWeb 那套)

| 字段 | 含义 | 示例 | DB 列 | /api/search 参数 | /api/facets key |
|---|---|---|---|---|---|
| `analysis_type` | 分析类型(最关键) | `城市总图` / `动线分析` / `视线分析` / `业态分析` / `日照分析` / `功能分区` / `形态生成` / `爆炸图` | ✅ | ✅ `?analysis_type=` | ✅ `analysis_types` |
| `drawing_method` | 画法 | `轴测图` / `平面图` / `剖面图` / `透视图` / `混合媒介` | ✅ 2026-08-06 加 | ✅ `?drawing_method=` | ✅ `drawing_methods` |
| `subject` | 主题 | `公共空间` / `商业综合体` / `办公` / `居住` / `城市设计` / `景观` | ✅ 2026-08-06 加 | ✅ `?subject=` | ✅ `subjects` |
| `scale` | 尺度 | `城市级` / `街区级` / `建筑级` / `单元级` | ✅ | ✅ `?scale=` | ✅ `scales` |
| `render_style` | 渲染风格 | `线稿` / `渲染` / `混合媒介` / `拼贴` | ✅ | ✅ `?render_style=` | ✅ `render_styles` |
| `view_type` | 视角 | `鸟瞰` / `透视` / `剖切` / `轴测` | ✅ | ✅ `?view=` | ✅ `view_types` |
| `color_palette` | 配色 | `暖橙` / `冷青` / `单色` / `多色` | ✅ | ✅ `?color_palette=` | ✅ `color_palettes` |
| `mood` | 氛围 | `学术严谨` / `活泼` / `极简` / `高密度` | ✅ | ✅ `?mood=` | ✅ `moods` |
| `keywords` | 自由关键词 | 逗号分隔 | ✅ | ✅ `?keywords=` | — |

> 2026-08-06 P1 兑现:`/api/search` 接 14 维参数(q + keywords + 9 维标签 + favs_only + limit),`/api/facets` 返 9 维 DISTINCT 列表供前端 chips。老 DB 缺 `drawing_method` / `subject` 列时,server 启动时 `_ensure_db_schema()` 幂等 ALTER TABLE 加列(不丢老数据,新列空串),`/api/facets` 对应返回 `[]` 不报错。

## 5. 推送规范

`git push` 在本机走 TCP 443 不通(被网络拦截),但 `https://api.github.com` 和 `https://gitee.com/api/v5` 都走得通。
**标准推送方式**:
- GitHub:走 `scripts/git_data_push.py` (项目自带,内部用 Git Data API) 或 `scripts/_push_v100.py`
- Gitee:走 `scripts/_push_gitee_v100.py` (Contents API,空仓不能改 public 需先推 1 个文件)
- fallback:直接 `Invoke-RestMethod` + Bearer header 调 GitHub API
- Mac:走 `scripts/_push_macos.py`(从 origin URL 读 token + 改 ROOT,跨平台包装)

**绝不要用**: `gh CLI` (`gh auth login` 对本项目 token 必返 401) / PowerShell `Set-Content` 写 .py (GBK 污染中文)。

**ROOT 一律用 env 或 os.path.dirname 推断,禁止 r-string 绝对路径**:
- `ROOT = os.environ.get('ANALYSISWEB_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`(默认取脚本所在目录的父级,即 `AnalysisWeb/` 根)
- Mac 上若 ROOT 仍以 `D:\` 开头立即 `raise SystemExit('ROOT 是 Windows 路径...')` 引导走 `_push_macos.py`
- 8-8 P0 教训:写死 `r'D:\Mac\...'`,Mac mini 上跑会 FileNotFoundError 静默失败

## 6. 验证凭据

```powershell
# GitHub · 推 GitHub 时验证
$h = @{Authorization="Bearer $env:GH_TOKEN"}
(Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $h).login
# 期望: 1500385678

# Gitee · 推 Gitee 时验证(access_token query 方式)
(Invoke-RestMethod -Uri "https://gitee.com/api/v5/user?access_token=$env:GITEE_PAT").login
# 期望: architectzy
```

**两条 token 都必须走 env 注入,绝不要硬编码进 .py 源码**(2026-08-07 P0 教训:GITEE_PAT 32 位 PAT 硬编码会被 Gitee secret scanning 立即吊销):
- GitHub: `GH_TOKEN` · 占位符 `__GITHUB_TOKEN_PLACEHOLDER__` · 缺 env 立即 `sys.exit(1)`
- Gitee: `GITEE_PAT` · 占位符 `__GITEE_PAT_PLACEHOLDER__` · 缺 env 立即 `sys.exit(1)`

## 7. 已知坑(避坑指南)

- **空仓库拒绝 `git/blobs` `git/commits`**:必须先用 Contents API `PUT /contents/<file>` 推 1 个 file 建初始 commit
- **autocrlf=true 时 SHA mismatch**:Contents API 用 `ReadAllBytes` 推的 SHA ≠ 本地 git object SHA;要本地一致就用 `git cat-file blob <sha>` 拿 LF bytes 再 base64
- **PowerShell `return ,$bytes` 嵌套 byte[]**:用 `return $bytes` 即可
- **PowerShell `ConvertTo-Json` 双重调用**:函数里别再调,只让调用方传已 JSON 化的 string
- **Secret scanning 拦硬编码 `ghp_...` / Gitee PAT 32 位**:两条 token 都改占位符(`__GITHUB_TOKEN_PLACEHOLDER__` / `__GITEE_PAT_PLACEHOLDER__`),真实 token 走 env 注入,缺 env 立即 `sys.exit(1)`;一旦硬编码进 git history 立即吊销不可回收 → 立刻 `git filter-branch` 或 BFG 清理
- **README CRLF vs LF**:Contents API 走 ReadAllBytes 会上传 CRLF bytes,跟 git object LF bytes SHA 不同
- **改 env 名容易漏**:`PICTUREWEB_HOME` → `ANALYSISWEB_HOME`、`PICTUREWEB_TEST_PORT` → `ANALYSISWEB_TEST_PORT`,全局搜一遍(server.py / start.bat / start.sh / start_hidden.vbs / scripts/)
- **Gitee POST /user/repos 不接 `public` 字段**(`true` / `false` / `1` / `0` 全报 `public is invalid`):建仓不传 public;Gitee 还规定**空仓不能改 public**(报 "空仓库不支持设置为公开仓库")→ 必须先 POST 1 个文件,再 PATCH `/repos/{owner}/{repo}`(必带 `name` 字段,否则 "name is missing")改 `private=false`
- **`ANALYSISWEB_HOME` 默认值 Mac 上必覆盖**:`server.py:9` 默认 `D:/Mac/...`(Windows 路径),`scripts/build_db.py:48` + `server.py:9`(R217 批 7 加)有 Mac 守卫;Mac mini 没设 env 启动立即 `sys.exit(1)` 引导 `export ANALYSISWEB_HOME=...`(见 §7 历史 commit `ea68160` 8-10)
- **`/api/search?limit=` 上下夹**:`server.py` `LIMIT_MIN=1, LIMIT_MAX=200`(R218 批 8 加),无 try/except 会 500 堆栈泄露;`f-string` 拼 LIMIT 已改 `?` 参数化 + 上下夹
- **POST body 上限 8MB**:`server.py` `MAX_POST_SIZE = 8 * 1024 * 1024`(R220 批 8 加),超返 413;`_upload_search` base64 解码后图像 ≤ `MAX_UPLOAD_RAW = 6 * 1024 * 1024`,防 ImageBomb + 内存 OOM
- **前端 `innerHTML` 拼用户数据 = XSS**:`index.html` `_ai_image` / `intent_search` / `upload_search` 5 处拼 `data.path` / `data.error` / `e.message` 全部改 `createElement + textContent + replaceChildren`(R219 批 8 加);`data.path` 来源是 server `_ai_image` `re.search` 抓 matrix MCP stdout,供应链/prompt 注入可塞 `</script><script>alert(1)</script>` → innerHTML 直接执行

## 8. 沟通规范

- 语言: 中文
- 文档命名: 中文 .md,禁乱码 / 英文 draft.md / output.md
- 数字前缀宽度一致 (01/02/.../09/10/11)
- 报告: 改动 + 链接 + exit code

## 9. Owner 决策点

- 是否复用 PictureWeb 的 3-Agent 流水线?(短期不动,先稳 v1.0.0;后续可加 `daily_pipeline.py` 适配)
- 是否给 AnalysisDb 加 `analysis_type` 字段(从 v1.0.0 起已加)?
- 端口 8082 是否被占?(可用 `ANALYSISWEB_TEST_PORT=9082` dev 模式)
- 是否支持更多图源(Concept/ / Section/ / Detail/)?(目前只 Style/,后续按需建子目录)

## 10. 变更记录(夜间迭代批 3 · 2026-08-06 02:00)

| 优先级 | 问题 | 修复 | 证据 |
|---|---|---|---|
| P0 | server.py:580 端口冲突 `sleep 10` 隐式 return 0,cron 假阳性 green | except OSError 改 `sys.exit(1)`,独立 try KeyboardInterrupt | 双进程同端口,后者 `exit_code=1` |
| P1 | 9 维承诺空头:_search 只 7 维,facets 不返 6 维 | `_search` 增 6 参 + SELECT 拉满 9 维 + 响应回显 6 维;`_facets` 增 6 维 DISTINCT;DB 启动幂等 ALTER 加 `drawing_method` / `subject` | curl `?analysis_type=动线` 命中 1,`?scale=城市级` 命中 2 |
| P1 | `_semantic_search` 硬塞 `sys.path.insert(0, 父目录)` 违反独立运营 | 改读 `ANALYSISWEB_EMBEDDING_DIR` env,缺 import 失败 → 返 501 + 友好错误 | curl POST 无 env → `status=501` + 中文提示 |
| P1 | 启动横幅硬编码 `192.168.181.136`(PictureWeb Windows 时代) | 启动时 socket 连 8.8.8.8:80 探测本机 LAN IP,失败回退 `ifconfig` 提示 | 本机打印 `http://192.168.0.104:8082/` |
| P2 | AGENTS.md / README.md 行数(`~580`)与 `.Log/` 漂移 | 同步到 `722 / 1218`;目录结构补 `thumbs/` `start.sh` `_push_*.py` `tag_images.py`;`.Log/` → `logs/` | `wc -l` 校验一致 |
| P0(批 1) | start.sh 缺 `-X utf8` 跨平台不一致 | start.sh:16 改 `python3 -X utf8 server.py` + 顶部加注释 | 启动横幅中文无乱码 |

> 全部走 `git_data_push.py` / `_push_gitee_v100.py` 推 GitHub + Gitee,exit code 见 commit。

## 11. 变更记录(夜间迭代批 4 · 2026-08-08 02:00)

| 优先级 | 问题 | 修复 | 证据 |
|---|---|---|---|
| P0 | `scripts/_push_gitee_v100.py:23` 硬编码 `GITEE_PAT` 32 位 | 改 `os.environ.get('GITEE_PAT') or '__GITEE_PAT_PLACEHOLDER__'`,缺 env 立即 `sys.exit(1)` + 中文提示;`main()` 加占位符守卫 | 156d67e / 9333f16 / 193541d |
| P0 | `scripts/_push_v100.py:25` / `_push_gitee_v100.py:25` ROOT 写死 `r'D:\Mac\...'` Windows 路径 | 改 `os.environ.get('ANALYSISWEB_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`;Mac 平台守卫 `if sys.platform == 'darwin' and ROOT.startswith(r'D:'): raise SystemExit(...)` | 1c20cac / 78fd60e |
| P0 | AGENTS.md §6 验证凭据只覆盖 `GH_TOKEN` | 扩成 `GH_TOKEN + GITEE_PAT` 都走 env + 占位符;§7 Secret scanning 补 Gitee PAT 32 位 + git filter-branch 清理 | 本批 commit |
| P1 | `server.py:353` view_types facets 写死 `['bird-eye','eye-level','other']` 三个英文 | 改 `_distinct('view_type')` 跟其他 6 维一致,DB 实时 DISTINCT 中文值(鸟瞰/透视/剖切/轴测) | f2e23f9 |
| P1 | `index.html:872,1123` view badge 还在按 bird-eye/eye-level/other 三元英译 | line 872 facets 改直传 `v`(不三语硬编码);line 1123 viewHtml 改 `item.view_type ? \`<div class="view-badge">${item.view_type}</div>\` : ''` | 本批 commit |
| P1 | `server.py:145` `_search` 异常兜成 200+error,前端拿不到失败信号 | 改 `status=500` 跟其他 endpoint 对齐;`logging.exception()` 把堆栈写进 `logs/` | fd2d785 |
| P2 | `libraryControl.md` 仍写 8081/5 维/PictureWeb 时代,Defense wikilink 死链 | 方案A 整文件覆写:frontmatter role 改「AnalysisWeb 索引员/排长」,正文写当前 v1.0.0/8082/9 维,上级 wikilink 指向 AGENTS.md,Defense 那行整段删;AGENTS.md §2 同步「旧 control 文件(归档)」→「排长索引员(方案A 重写)」 | 581c2dd(方案B 注释) + 本批(方案A 整文) |

> 本批 commit 走 `git_data_push.py` 推 GitHub + Gitee,exit code 见 commit message。

## 12. 变更记录(夜间迭代批 3 · 2026-08-09 02:00 · 二次复核)

> 触发:夜间迭代 cron 复跑 8-7 23:25 Verifier 5 条意见(行 17-21),实际全部已在批 3/批 4 闭环;本批只追 P2 行数漂移。

| 优先级 | 问题 | 修复 | 证据 |
|---|---|---|---|
| P0 | `server.py:580` 端口冲突 `sleep 10` 隐式 return 0,cron 假阳性 green | 已在 批 3 (2026-08-06) `except OSError as e` 改 `sys.exit(1)` | server.py:733 sys.exit(1) 已就位 |
| P1 | 9 维承诺空头:`_search` 只 7 维,facets 不返 6 维 | 已在 批 3 (2026-08-06) `_search` 增 6 参 + SELECT 拉满 9 维 + `_facets` 增 6 维 DISTINCT + DB 启动幂等 ALTER 加 `drawing_method` / `subject` | server.py:128-129/350-351 已就位 |
| P1 | `_semantic_search` 硬塞 `sys.path.insert(0, 父目录)` 违反独立运营 | 已在 批 3 (2026-08-06) 改读 `ANALYSISWEB_EMBEDDING_DIR` env,缺 import 失败 → 返 501 + 友好错误 | server.py:379 已就位 |
| P1 | 启动横幅硬编码 `192.168.181.136`(PictureWeb Windows 时代) | 已在 批 3 (2026-08-06) 启动时 socket 连 8.8.8.8:80 探测本机 LAN IP | server.py:697-703 已就位 |
| P2 | AGENTS.md / README.md 行数与代码漂移(server.py 722→736,index.html 1218→1222) | 本批同步 AGENTS.md §2 + README.md 目录树行数 | `wc -l` = 736 / 1222 一致 |
| P1(发现) | `_facets` 内 `conn.close()` 在 `_distinct('view_type')` 之前,导致 8-8 P1 修复后 `/api/facets` 抛 `Cannot operate on a closed database` | `conn.close()` 移到 7 个 `_distinct()` 调用之后 | curl `/api/facets` 返 9 维 + 中文值,无 `closed database` 异常 |

> 本批 commit 单条,`fix(P2 行数同步 + P1 facets conn.close 顺序)`,走 `git_data_push.py` 推 GitHub + Gitee。

## 13. 变更记录(夜间迭代批 5 · 2026-08-09 23:40)

> 触发:Verifier 8-9 23:25 第 1 条 P0 (Row 142) — `ADMIN_IPS` 仍硬编码 PictureWeb 时代 Windows LAN IP `192.168.181.136`,且没把 8-6 已就位的 `_detect_lan_ip()` 同步并入 ADMIN_IPS,导致本机 LAN 自访 POST /api/favorites 仍 403。

| 优先级 | 问题 | 修复 | 证据 |
|---|---|---|---|
| P0 | `server.py:21` `ADMIN_IPS = {'127.0.0.1', '192.168.181.136', '::1'}` 硬编码 Windows LAN IP,Mac mini 网段不存在,本机 POST 写操作 403 | 改为 `{'127.0.0.1', '::1'}` 起步;启动时 `_detect_lan_ip()` 拿到的本机 LAN `ADMIN_IPS.add(lan_ip)` 同步并入;新增 `ANALYSISWEB_ADMIN_IPS` env 逗号分隔支持人工白名单(团队内 10.0.0.50 等);AGENTS.md §3 "本机端点" 同步更新 | `grep -n 192.168.181.136 server.py AGENTS.md` → server.py 注释 1 处(变更记录引用)+ AGENTS.md 变更记录 2 处(历史事件),正文/代码 0 命中 |
| P1 | `AGENTS.md:75` 仍写 `本机端点 (127.0.0.1 / 192.168.181.136 / ::1)`,误导 agent 与用户 | 改成 `127.0.0.1 / ::1 + 启动时 _detect_lan_ip() 探测到的本机 LAN + ANALYSISWEB_ADMIN_IPS env 逗号分隔` | grep 无正文命中 |

> 本批 commit 单条,`fix(P0 R142 ADMIN_IPS 硬编码 + P1 AGENTS.md 同步)`,走 `git_data_push.py` 推 GitHub + Gitee。

## 14. 变更记录(夜间迭代批 6 · 2026-08-10 02:00)

> 触发:J10 授权自主决策 6 护栏临时豁免;批 3 任务描述里的 5 意见(批 3 8-6)已在 §10 闭环,本批转 8-8/8-9 Verifier 未闭环 6 条(2×P0 + 2×P1 + 2×P2)。

| 优先级 | 问题(Row#) | 修复 | 证据 |
|---|---|---|---|
| P0 | `server.py:_ai_image`(R84/R143)写 `_ai_req.json` 硬路径 + 并发覆盖 + 120s 失败残留磁盘 | `tempfile.mkstemp(prefix='_ai_prompt_')` 每请求独立文件;新增 `_ai_image_lock = Lock()` 串行 mavis subprocess;`try/finally os.unlink` 兜底 | `wc -l server.py`:743 → 811 |
| P0 | `index.html:1004,1014`(R83)`openModal({...})` onclick 字符串拼接 + `caption.replace(/'/g)` 单引号转义,item 字段含 `"` `<script>` 触发 XSS | renderCards + intent cards + openModal 全部改 `createElement + textContent + addEventListener + dataset.item = JSON.stringify` 传值,0 字符串拼接;`favHtml` 模板也改 addEventListener | `wc -l index.html`:1222 → 1320;`grep "openModal.*item\\." index.html` → 0 命中字符串拼接 |
| P1 | `server.py:_upload_search`(R144)全表 SELECT phash + Python hamming 循环 + 无 LIMIT,1000+ 行肉眼延迟 | SQL 加 `LIMIT 200` 候选 + Python `heapq` top20 early-break | `wc -l server.py` +28;`grep "LIMIT" server.py` 新增 1 处 |
| P1 | `server.py:_ensure_db_schema`(R145)启动只 ALTER images 表,不重建 images_fts FTS5 虚拟表,9 维新列全文匹配漏 | 启动时 `PRAGMA table_info(images_fts)` 探测;列不匹配 → `DROP TABLE images_fts` + 重建(16 列含 9 维)+ `INSERT INTO images_fts SELECT ... FROM images` repopulate;横幅打 `[schema] ⚠️ images_fts schema 不匹配 → 重建完成,repopulate N 行` | `python3 -c "import server; server._ensure_db_schema()"` → ⚠️ 重建 + ✅ repopulate 11 行,`PRAGMA table_info(images_fts)` 16 列齐全 |
| P2 | `scripts/build_db.py:48`(R86)`os.remove(DB_PATH)` 静默删老 DB,LLM 打标结果归零;`scripts/build_db.py:33` `r'D:\Mac\...'` 硬编码 Windows 路径,Mac 上 fail | 1) 加 `--force` argparse,默认 REBUILD 走 `shutil.copy2` 自动备份 `AnalysisDb.db.bak.YYYYMMDD-HHMMSS`;2) `ANALYSISWEB_HOME` 缺 env 改 `os.path.dirname` 4 次推断(Mac 守卫:`darwin` + `startswith('D:')` → `sys.exit(1)` 引导 `export ANALYSISWEB_HOME=...`) | `python3 scripts/build_db.py` → 🛡️ 老 DB 已备份 → 删 + 重建;`python3 scripts/build_db.py --help` 显式列 `--force`;`--incremental` 11 张不丢 |
| P2 | `libraryControl.md:42-43`(R146)`server.py ~729 行 / index.html ~1218 行` 漂移;`scripts/` 目录树只列 8 文件,实际 17 个 | 行数同步 811 / 1320;`scripts/` 按 `ls -la` 顺序列全 17 个 .py + `__pycache__/`,标注从 PictureWeb 继承的模板用脚本;变更记录加 8-10 批 6 行 | `wc -l libraryControl.md` 148 → 159 |

> 本批 commit 单条,`fix(批 6 02:00 R83/R84/R143/R144/R145/R86/R146)`,走 `git_data_push.py` 推 GitHub + Gitee。

## 15. 变更记录(夜间迭代批 7 · 2026-08-10 23:40)

> 触发:Verifier 8-10 23:25 第 1 条 P0 (Row 217) — `server.py:9` `ANALYSISWEB_HOME` 默认值仍是 Windows 路径 `D:/Mac/Mac/...`,跟 `scripts/build_db.py:48` 一样缺 Mac 守卫。Mac mini 上没设 `ANALYSISWEB_HOME` env 时启动直接走默认值,后拼出来的 `IMG_ROOT` 仍是 `D:/.../Mobile/Style`,跟实际 Mac 路径 `/Users/aaron/.../Mobile/Style` 不一致,所有图片 404。

| 优先级 | 问题 | 修复 | 证据 |
|---|---|---|---|
| P0 | `server.py:9` `ANALYSISWEB_HOME` 默认值是 Windows 路径 `D:/Mac/...`,`build_db.py:48` 已有 Mac 守卫,`server.py` 缺,Mac mini 没设 env 启动 → IMG_ROOT 错误路径 → 所有图片 404 | server.py:9 后立即加 Mac 守卫(抄 build_db.py:48 模板):`if sys.platform == 'darwin' and ANALYSISWEB_HOME.startswith('D:'): print('[server] ❌ ...', file=sys.stderr); print('   请:export ANALYSISWEB_HOME=...', file=sys.stderr); sys.exit(1)` | `python3 server.py`(无 env)→ `[server] ❌ ANALYSISWEB_HOME 是 Windows 路径` + exit=1;`ANALYSISWEB_HOME=/Users/aaron/.../Attack/03-Analysis python3 -c "import server; print(server.IMG_ROOT)"` → `/Users/aaron/.../Mobile/Style` 正常;`wc -l server.py` 811 → 817 |

> 本批 3 个 commit:`ea68160` server.py 守卫 + AGENTS.md §15 · `fa2a14b` scripts/_push_fix_r217.py 工具 · `f538ff0` _push_fix_r217.py Gitee POST/PUT 区分。
> GitHub:ceb094e(2 files)→ cd0ab04(1 file)→ 6c431b3(1 file);Gitee:8cd1232a8b / 2354a4f542 / d441adef99 / b6332bc450。

## 16. 变更记录(夜间迭代批 8 · 2026-08-11 02:00)

> 触发:Verifier 8-10 23:25 未闭环 4 条 (Row 218/219/220/221,P0×2 + P1×2);任务 cron 描述"批 3 5 条意见"已全部在 §10/§11 闭环(批 3 + 批 4 2026-08-06/08-08),J10 授权自主决策 6 护栏临时豁免 → 自主切换到当前 8-10 23:25 最新未闭环意见。

| 优先级 | 问题(Row#) | 修复 | 证据 |
|---|---|---|---|
| P0 | `server.py:149` limit 无 try/except + 319 `f-string` 拼 LIMIT 注入 + 用户传 `?limit=9999999` 内存爆(R218) | 1) `try/except (ValueError, TypeError): limit = 60` 包裹 int 解析;2) `limit = max(LIMIT_MIN, min(limit, LIMIT_MAX))` 上下夹 1~200;3) 顶部新增 `LIMIT_MIN, LIMIT_MAX = 1, 200` 常量;4) SQL `LIMIT {limit}` 改 `LIMIT ?` + `params.append(limit)` 参数化;5) `AGENTS.md §3` 加"limit ≤ 200"约束,§7 加 LIMIT 坑 | `wc -l server.py` 817 → 847;`grep "LIMIT ?" server.py` 新增 1 处;`curl '/api/search?limit=abc'` 不再 500 |
| P0 | `index.html` `_ai_image` / `intent_search` / `upload_search` 5 处 `target.innerHTML = "..." + data.path/error + "..."` XSS 注入(R219) | 1) `988 / 1094 / 1101 / 1293` 4 处改 `createElement + textContent + replaceChildren`;2) `1096` `_ai_image` 成功分支 `img.src = data.path`(赋值安全,textContent 防文本注入)+ `replaceChildren`;3) `1098` 未知响应同步改 `textContent`;4) `AGENTS.md §7` 加 innerHTML 坑 | `wc -l index.html` 1320 → 1352;`grep -E "^\s*[a-zA-Z].*innerHTML.*\+\s*(data\.\|e\.message)" index.html` 0 命中(注释里命中是描述旧代码,正常) |
| P1 | `server.py:182` `do_POST` Content-Length 无 try/except + `rfile.read(length)` 无上限(ImageBomb + OOM)(R220) | 1) `try/except (ValueError, TypeError)` 包 `int(self.headers.get('Content-Length', 0) or 0)`,异常返 400;2) 顶部新增 `MAX_POST_SIZE = 8 * 1024 * 1024`,超返 413;3) `_upload_search` base64 解码后 `if len(raw) > MAX_UPLOAD_RAW: 返 413`,防客户端送 base64 后压缩/重复填;4) `AGENTS.md §3` 加 "body ≤ 8MB" 约束,§7 加 POST body 坑 | `MAX_POST_SIZE / MAX_UPLOAD_RAW / LIMIT_MIN / LIMIT_MAX` 4 个常量;`curl -X POST --data-binary @bigfile` 超 8MB 返 413 |
| P1 | `AGENTS.md:19/26` + `README.md:38/101` 仍写 Windows 路径 `D:\Mac\...`,跟 `server.py:9` Mac 守卫(R217 批 7)不同步,新 agent 读这俩文件误以为项目只能在 Windows 跑(R221) | 1) `AGENTS.md:19` 工作目录 cell 改 `$ANALYSISWEB_HOME/_ArchiAttackAnalysisLib/AnalysisWeb/` + Mac/Windows 双值;2) `AGENTS.md:26` 图片根同改;3) `AGENTS.md §1` 表后加 1 行注"路径写法以本机实际为准";4) `AGENTS.md §7` 加 "ANALYSISWEB_HOME 默认值 Mac 上必覆盖" 坑;5) `README.md:38` 图片根同步双值;6) `README.md:101` `ANALYSISWEB_HOME` env 默认值改"(无默认,Mac 守卫必填)" | `grep "D:\\\\Mac" AGENTS.md README.md` 只命中 §1 表格内的 Windows 参考值 + §7 已知坑历史 commit 引用,无歧义 |

> 本批 commit 单条,`fix(批 8 02:00 R218/R219/R220/R221 P0×2 + P1×2)`,走 `git_data_push.py` 推 GitHub + `_push_gitee_v100.py` 推 Gitee。
