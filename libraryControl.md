---
aliases:
  - library
  - AnalysisWeb
tags:
  - control
  - 排长
  - AnalysisWeb
  - 建筑师助手
created: 2026-06-27
updated: 2026-08-08
role: AnalysisWeb 索引员/排长
上级: "[[Attack/03-Analysis/_ArchiAttackAnalysisLib/AnalysisWeb/AGENTS.md]]"  # AnalysisWeb 项目真值源
下属: []
资源: []
---

# 🎖️ 排长 · AnalysisWeb 索引员

> **军衔**:排长(Mac → 军长 → 师长 → 旅长 → 团长 → 营长 → 排长)
> **路径**:`Attack/03-Analysis/_ArchiAttackAnalysisLib/AnalysisWeb/`
> **职责**:AnalysisWeb(8082 建筑方案分析图库)索引与运营

## 上级

- 营长:[[Attack/03-Analysis/ArchiAttackAnalysisControl.md]]
- 项目真值源:**AGENTS.md**(本项目根目录)——所有变更、推送规范、避坑指南以 AGENTS.md 为准

## 平级

- PictureWeb(8081 效果图/参考图库)——兄弟项目,共用检索壳
- 03-Analysis 其他项目

## 下属

_(暂无 — AnalysisWeb 是单仓单服务结构)_

## 资源

- `AGENTS.md` · 项目真值源(必读)
- `README.md` · 用户档
- `server.py` · 后端(单文件,~811 行 · 8-10 P0/P1 后)
- `index.html` · 搜索主页(单文件,~1320 行 · 8-10 P0 XSS 改 createElement 后)
- `scripts/` · 推送 / 打标 / 巡检工具(17 个 .py · 8-10 P2 build_db 备份后)
- `thumbs/` · 缩略图缓存(运行时,gitignore)
- `_AnalysisDb/AnalysisDb.db` · SQLite 数据库(运行时,gitignore)

---

> 变更记录
> - 2026-06-27 · 创建 control 文件(军衔:营长) · Macmini
> - 2026-07-24 · 从 PictureWeb 拆出 v1.0.0 独立运营 · 端口 8081 → 8082
> - 2026-08-02 · frontmatter 调整
> - 2026-08-08 · Verifier P2 修复(方案A):Defense 死链 wikilink 整段删,正文改写为 AnalysisWeb 当前 v1.0.0 + 8082 + 9 维标签,真值源走 AGENTS.md · 排长
> - 2026-08-10 · 批 3 P2 修复(R146):server.py 729 → 811 / index.html 1218 → 1320 / scripts/ 8 → 17 个 .py 行数同步

---

# AnalysisWeb · 建筑方案分析图库

## 这是什么

AnalysisWeb 是独立的**建筑方案分析图库**检索系统。多维标签 + 全文搜索 + 以图搜图。
端口 **8082** · Python 标准库 + Pillow · 零 npm 依赖。

**前身**: 从 `PictureWeb` (1500385678/PictureWeb,端口 8081) 拆出,2026-07-24 **v1.0.0** 独立运营。
PictureWeb 收效果图 / 参考图,AnalysisWeb 专门收**方案分析图**(轴测、平面、剖面、动线、视线、业态、爆炸等)。

**定位**: 不是"找好看的图",是"做方案时找同类型分析方法、找同尺度同主题的参考"。

## 关键能力

- 端口 **8082**(兄弟 PictureWeb 是 8081)
- **9 维标签检索**:`analysis_type` / `drawing_method` / `subject` / `scale` / `render_style` / `view_type` / `color_palette` / `mood` / `keywords`
- 全文搜索(SQLite FTS5)
- 以图搜图(PIL pHash)
- 收藏夹
- AI 语义搜索(可选,需 `ANALYSISWEB_EMBEDDING_DIR`)

## 启动

```bash
# Mac
python3 -X utf8 server.py
# 打开 http://127.0.0.1:8082/

# Windows
双击 start.bat
# 或 python -X utf8 server.py
```

## 环境变量

- `ANALYSISWEB_HOME` · 图片根父目录(默认脚本推断)
- `ANALYSISWEB_TEST_PORT` · 端口覆盖(默认 8082)
- `ANALYSISWEB_EMBEDDING_DIR` · AI 语义搜 embedding.py 目录(缺则 501)
- `GH_TOKEN` · GitHub 推送 token(secret scanning 必须走 env)
- `GITEE_PAT` · Gitee 推送 PAT(secret scanning 必须走 env)

## 仓库

- GitHub: https://github.com/1500385678/AnalysisWeb
- Gitee: https://gitee.com/architectzy/AnalysisWeb

## API 速览

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/search` | 9 维搜索 + 全文 + favs_only + limit |
| GET | `/api/facets` | 9 维 DISTINCT 值供前端 chips |
| GET | `/api/favorites` | 收藏列表 |
| POST | `/api/favorites` | 切换收藏(本机权限) |
| GET/POST | `/api/upload_search` | 以图搜图(本机权限) |
| GET/POST | `/api/semantic_search` | AI 语义搜(需 embedding) |
| GET/POST | `/api/intent_search` | 设计意图找参考 |
| GET/POST | `/api/ai_image` | AI 看图(本机权限) |

## 目录

```
AnalysisWeb/
├── server.py             # 后端(单文件,~811 行 · 8-10 P0/P1 后)
├── index.html            # 搜索主页(单文件,~1320 行 · 8-10 P0 XSS 改 createElement 后)
├── start.bat / start.sh  # 启动脚本(均带 -X utf8 · 跨平台镜像)
├── start_hidden.vbs      # 无窗口启动(Windows)
├── libraryControl.md     # 本文件 · AnalysisWeb 索引员/排长
├── AGENTS.md             # 项目真值源(必读)
├── README.md             # 用户档
├── LICENSE               # 许可证
├── __version__.py        # 版本号源
├── _AnalysisDb/
│   └── AnalysisDb.db     # SQLite 数据库(gitignore)
├── thumbs/               # 缩略图缓存(gitignore)
├── logs/                 # 重要事件日志(gitignore)
├── docs/
│   ├── 3agent-workflow.md
│   └── phase6-design.md
├── scripts/              # 17 个 .py · ls -la 实际顺序
│   ├── _check_autofix.py       # (从 PictureWeb 继承,模板用)
│   ├── _demo_e2e.py            # (从 PictureWeb 继承,模板用)
│   ├── _push_gitee_v100.py     # Gitee 首发(Contents API)
│   ├── _push_github_api.py     # GitHub API 通用推 ref 工具
│   ├── _push_macos.py          # macOS 包装(从 origin URL 读 token + 改 ROOT)
│   ├── _push_v100.py           # GitHub 首发(Contents API)
│   ├── auto_dispatch.py        # (从 PictureWeb 继承,模板用)
│   ├── auto_fixer_architect.py # (从 PictureWeb 继承,模板用)
│   ├── auto_release.py         # release + bump + tag
│   ├── auto_tester.py          # (从 PictureWeb 继承,模板用)
│   ├── batch_push.py           # (从 PictureWeb 继承,模板用)
│   ├── build_db.py             # 扫 IMG_ROOT → 建库(8-10 P2 加 --force + 备份)
│   ├── daily_pipeline.py       # (从 PictureWeb 继承,模板用)
│   ├── debug_tree.py           # (从 PictureWeb 继承,模板用)
│   ├── feedback.py             # (从 PictureWeb 继承,模板用)
│   ├── git_data_push.py        # Git Data API 推送
│   ├── tag_images.py           # LLM 打标 9 维
│   └── __pycache__/            # (运行时)
└── tests/
    └── smoke.py
```
