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
| 远端仓库 | `https://github.com/1500385678/AnalysisWeb` (public, 2026-07-24 v1.0.0) |
| 远端主分支 | `main` |
| 当前版本 | `v1.0.0` (`__version__.py`) |
| 启动命令 | `python -X utf8 server.py` (Windows) 或双击 `start.bat` |
| 默认 URL | http://127.0.0.1:8082/ |
| 数据库 | `_AnalysisDb/AnalysisDb.db` (本项目私有,gitignore) |
| 图片根 | `D:\Mac\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis\Mobile` |
| 缩略图缓存 | `thumbs/` (gitignore) |
| 日志 | `logs/` (gitignore) |
| 兄弟项目 | PictureWeb(8081) 收效果图 / 参考图,共用 `AnalysisWeb` 检索壳 |
| 环境变量 | `ANALYSISWEB_HOME`(图片根父目录)、`ANALYSISWEB_TEST_PORT`(端口覆盖) |

## 2. 目录结构

```
AnalysisWeb/
├── server.py             # 后端(单文件,~580 行)
├── index.html            # 搜索主页(CSS+JS 内嵌,苹果风浅色)
├── start.bat / start.sh  # 启动脚本
├── start_hidden.vbs      # 无窗口启动(Windows)
├── libraryControl.md     # 旧 control 文件(归档)
├── LICENSE               # 许可证
├── favorites.json        # 收藏(运行时,gitignore)
├── AGENTS.md             # 本文件
├── README.md             # 用户档
├── __version__.py        # 版本号源
├── _AnalysisDb/
│   └── AnalysisDb.db     # SQLite 数据库(gitignore)
├── docs/
│   ├── 3agent-workflow.md  # 3-Agent 流水线手册(从 PictureWeb 继承,模板用)
│   └── phase6-design.md    # Phase 6 设计(从 PictureWeb 继承)
├── scripts/
│   ├── build_db.py          # 扫 IMG_ROOT → 建库
│   ├── git_data_push.py     # Git Data API 推送
│   ├── auto_release.py      # release + bump + tag
│   ├── auto_dispatch.py     # (从 PictureWeb 继承,模板用)
│   ├── auto_fixer_architect.py # (从 PictureWeb 继承,模板用)
│   ├── auto_tester.py       # (从 PictureWeb 继承,模板用)
│   ├── daily_pipeline.py    # (从 PictureWeb 继承,模板用)
│   ├── feedback.py          # (从 PictureWeb 继承,模板用)
│   ├── batch_push.py        # (从 PictureWeb 继承,模板用)
│   ├── debug_tree.py        # (从 PictureWeb 继承,模板用)
│   └── _demo_e2e.py         # (从 PictureWeb 继承,模板用)
├── tests/
│   └── smoke.py            # 烟雾测试
└── .Log/                   # 重要事件日志(归档)
```

## 3. API 速览

公开端点: `/api/search` `/api/facets` `/api/favorites` (GET)
本机端点 (`127.0.0.1` / `192.168.181.136` / `::1`): `POST /api/favorites` `POST /api/upload_search`

完整列表 + 权限: `server.py:ADMIN_IPS` + README.md

## 4. 标签维度(AnalysisWeb 专用,非 PictureWeb 那套)

| 字段 | 含义 | 示例 |
|---|---|---|
| `analysis_type` | 分析类型(最关键) | `城市总图` / `动线分析` / `视线分析` / `业态分析` / `日照分析` / `功能分区` / `形态生成` / `爆炸图` |
| `drawing_method` | 画法 | `轴测图` / `平面图` / `剖面图` / `透视图` / `混合媒介` |
| `subject` | 主题 | `公共空间` / `商业综合体` / `办公` / `居住` / `城市设计` / `景观` |
| `scale` | 尺度 | `城市级` / `街区级` / `建筑级` / `单元级` |
| `render_style` | 渲染风格 | `线稿` / `渲染` / `混合媒介` / `拼贴` |
| `view_type` | 视角 | `鸟瞰` / `透视` / `剖切` / `轴测` |
| `color_palette` | 配色 | `暖橙` / `冷青` / `单色` / `多色` |
| `mood` | 氛围 | `学术严谨` / `活泼` / `极简` / `高密度` |
| `keywords` | 自由关键词 | 逗号分隔 |

## 5. 推送规范

`git push` 在本机走 TCP 443 不通(被网络拦截),但 `https://api.github.com` 走得通。
**标准推送方式**:
- 走 `scripts/git_data_push.py` (项目自带,内部用 Git Data API)
- fallback:直接 `Invoke-RestMethod` + Bearer header 调 GitHub API

**绝不要用**: `gh CLI` (`gh auth login` 对本项目 token 必返 401) / PowerShell `Set-Content` 写 .py (GBK 污染中文)。

## 6. 验证凭据

```powershell
$h = @{Authorization="Bearer $env:GH_TOKEN"}
(Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $h).login
# 期望: 1500385678
```

## 7. 已知坑(避坑指南)

- **空仓库拒绝 `git/blobs` `git/commits`**:必须先用 Contents API `PUT /contents/<file>` 推 1 个 file 建初始 commit
- **autocrlf=true 时 SHA mismatch**:Contents API 用 `ReadAllBytes` 推的 SHA ≠ 本地 git object SHA;要本地一致就用 `git cat-file blob <sha>` 拿 LF bytes 再 base64
- **PowerShell `return ,$bytes` 嵌套 byte[]**:用 `return $bytes` 即可
- **PowerShell `ConvertTo-Json` 双重调用**:函数里别再调,只让调用方传已 JSON 化的 string
- **Secret scanning 拦硬编码 `ghp_...`**:改占位符 `__GITHUB_TOKEN_PLACEHOLDER__`,真实 token 走 env 注入
- **README CRLF vs LF**:Contents API 走 ReadAllBytes 会上传 CRLF bytes,跟 git object LF bytes SHA 不同
- **改 env 名容易漏**:`PICTUREWEB_HOME` → `ANALYSISWEB_HOME`、`PICTUREWEB_TEST_PORT` → `ANALYSISWEB_TEST_PORT`,全局搜一遍(server.py / start.bat / start.sh / start_hidden.vbs / scripts/)

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
