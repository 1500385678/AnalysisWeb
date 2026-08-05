# AnalysisWeb

> 建筑方案分析图库。轴测、平面、剖面、爆炸、动线、视线、业态……做方案时反复画反复找的那套。
> 端口 **8082** · Python 标准库 + Pillow · 零 npm 依赖。

跟 8081 的 **PictureWeb** 是兄弟模块——那边收效果图 / 参考图,这边专门收**方案分析图**。
共用一套 `AnalysisDb` 检索壳,标签维度针对分析图重设。

## 启动

```bash
# Windows
python -X utf8 server.py
# 或
双击 start.bat
```

打开 **http://127.0.0.1:8082/**

## 功能

- 🔍 多维标签检索(`analysis_type` / `drawing_method` / `subject` / `scale` / `mood` 等 9 维)
- ⚡ FTS5 全文搜索(中文 2-gram 分词)
- 🖼️ 以图搜图(PIL pHash)
- ⭐ 收藏夹
- 🗂️ 项目子目录隔离(`Style/` / `Concept/` / 后续可加)

## 依赖

- Python 3.10+ 标准库
- `Pillow`(pHash 计算 + 缩略图)· `pip install Pillow`
- 共用 `_AnalysisDb/AnalysisDb.db`(本项目私有)
- 图片根 `D:\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis\Mobile`

## 标签维度(AnalysisWeb 专用)

| 字段 | 含义 | 示例 |
|---|---|---|
| `analysis_type` | 分析类型 | `城市总图` / `动线分析` / `视线分析` / `业态分析` / `日照分析` / `功能分区` / `形态生成` / `爆炸图` |
| `drawing_method` | 画法 | `轴测图` / `平面图` / `剖面图` / `透视图` / `混合媒介` |
| `subject` | 主题 | `公共空间` / `商业综合体` / `办公` / `居住` / `城市设计` / `景观` |
| `scale` | 尺度 | `城市级` / `街区级` / `建筑级` / `单元级` |
| `render_style` | 渲染风格 | `线稿` / `渲染` / `混合媒介` / `拼贴` |
| `view_type` | 视角 | `鸟瞰` / `透视` / `剖切` / `轴测` |
| `color_palette` | 配色 | `暖橙` / `冷青` / `单色` / `多色` |
| `mood` | 氛围 | `学术严谨` / `活泼` / `极简` / `高密度` |
| `keywords` | 自由关键词 | 逗号分隔 |

> 9 维标签 + caption + description + keywords,跟 PictureWeb 同套检索体验,字段语义按分析图重设。

## API

| Method | Path | 权限 | 说明 |
|--------|------|------|------|
| GET | `/api/search?` | 公开 | 多维搜索 |
| GET | `/api/facets` | 公开 | 9 维标签去重值 |
| GET | `/api/favorites` | 公开 | 收藏列表 |
| POST | `/api/favorites` | 本机 | 切换收藏 |
| POST | `/api/upload_search` | 本机 | 以图搜图 |
| GET | `/img/<相对路径>` | 公开 | 图片直出 |

> 权限"本机"=`127.0.0.1` / `192.168.181.136` / `::1`,见 `server.py:ADMIN_IPS`

## 目录

```
AnalysisWeb/
├── server.py            # 后端(单文件,722 行 · 2026-08-06 9 维承诺+端口冲突修后)
├── index.html           # 搜索主页(CSS+JS 内嵌,苹果风浅色)
├── start.bat            # Windows 启动
├── start.sh             # macOS/Linux 启动
├── start_hidden.vbs     # 无窗口启动(Win 开机自启)
├── libraryControl.md    # 旧 control 文件(归档)
├── LICENSE              # 许可证
├── favorites.json       # 收藏(运行时,gitignore)
├── thumbs/              # 缩略图(运行时,gitignore)
├── _AnalysisDb/
│   └── AnalysisDb.db    # SQLite(本项目私有,gitignore)
├── docs/
│   ├── 3agent-workflow.md  # (从 PictureWeb 继承的 3-Agent 流水线手册)
│   └── phase6-design.md    # (从 PictureWeb 继承)
├── scripts/
│   ├── build_db.py          # 扫 IMG_ROOT → 建库
│   ├── git_data_push.py     # Git Data API 推送
│   ├── auto_release.py      # release + bump + tag
│   └── ... (辅助)
└── tests/
    └── smoke.py            # 烟雾测试
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ANALYSISWEB_HOME` | `D:\Mac\Mac\Mac\workteam\05_space\03_architect\Attack\03-Analysis` | 图片根的父目录 |
| `ANALYSISWEB_TEST_PORT` | `8082` | dev 用端口(默认即 8082,设了则覆盖) |

## 变更记录

| 日期 | 变更 | 触发 |
|------|------|------|
| 2026-07-24 | **v1.0.0** 初始独立版本 · README/AGENTS 改 AnalysisWeb 专属 · 端口 8081→8082 · env 重命名 PICTUREWEB_*→ANALYSISWEB_* · Style/ 11 张分析图 LLM 打标入库 · 仓库 1500385678/AnalysisWeb 公开 | 从 PictureWeb 拆出,作为方案分析图专用图库 |
| 2026-08-06 | **夜间迭代批 3** P0 端口冲突退出码 1 + 启动 LAN IP 自动探测 + 9 维承诺兑现(6 维搜索 + 6 维 facets + 缺列自动 ALTER) + embedding 软化为 env 变量 + AGENTS/README 行数 / 目录结构同步 | Verifier 6 条意见(P0=2 / P1=3 / P2=1) |

## 验收日志

- 2026-07-24 · v1.0.0 · 初始独立版本:端口 8081→8082;环境变量 PICTUREWEB_HOME→ANALYSISWEB_HOME、PICTUREWEB_TEST_PORT→ANALYSISWEB_TEST_PORT;README/AGENTS/server.py/start.* 全部重命名;Style/ 11 张分析图大模型打标入库(analysis_type / drawing_method / subject / scale / render_style / view_type / color_palette / mood / keywords 9 维);GitHub 仓库 1500385678/AnalysisWeb 公开
