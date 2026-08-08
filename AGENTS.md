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
| 工作目录 | `D:\Mac\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis\_ArchiAttackAnalysisLib\AnalysisWeb\` |
| 远端仓库 | **GitHub** `https://github.com/1500385678/AnalysisWeb` (public, 2026-07-24 v1.0.0) · **Gitee 镜像** `https://gitee.com/architectzy/AnalysisWeb` (public, 2026-07-25 v1.0.0,互不依赖) |
| 远端主分支 | `main` |
| 当前版本 | `v1.0.0` (`__version__.py`) |
| 启动命令 | `python -X utf8 server.py` (Windows) 或双击 `start.bat` |
| 默认 URL | http://127.0.0.1:8082/ |
| 数据库 | `_AnalysisDb/AnalysisDb.db` (本项目私有,gitignore) |
| 图片根 | `D:\Mac\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis\Mobile` |
| 缩略图缓存 | `thumbs/` (gitignore) |
| 日志 | `logs/` (gitignore) |
| 兄弟项目 | PictureWeb(8081) 收效果图 / 参考图,共用 `AnalysisWeb` 检索壳 |
| 环境变量 | `ANALYSISWEB_HOME`(图片根父目录)、`ANALYSISWEB_TEST_PORT`(端口覆盖)、`ANALYSISWEB_EMBEDDING_DIR`(AI 语义搜 embedding.py 目录,缺则 501) |

## 2. 目录结构

```
AnalysisWeb/
├── server.py             # 后端(单文件,736 行 · 2026-08-09 P2 行数同步)
├── index.html            # 搜索主页(CSS+JS 内嵌,苹果风浅色,1222 行)
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
本机端点 (`127.0.0.1` / `192.168.181.136` / `::1`): `POST /api/favorites` `POST /api/upload_search`

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
