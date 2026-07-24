"""AnalysisWeb tag_images.py · 大模型(本 agent)看图打标 + 入库
- 2026-07-24 v1.0.0 初版
- 给 _AnalysisDb/AnalysisDb.db 加 analysis_type 列,给 Style/ 11 张分析图打标
- 标签维度详见 AGENTS.md §4
"""
import os
import sqlite3
from datetime import datetime

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_AnalysisDb', 'AnalysisDb.db')

# 大模型看图判断的标签(11 张图)
# analysis_type: 城市总图/动线分析/视线分析/业态分析/日照分析/功能分区/形态生成/爆炸图/透视/社交分析
# drawing_method (复用 arch_type): 轴测/平面/剖面/透视/混合媒介
# subject (复用 scene): 公共空间/商业/居住/城市设计/景观/文化
# scale: 城市级/街区级/建筑级/单元级
# render_style: 线稿/渲染/混合媒介/拼贴
# view_type: 鸟瞰/透视/剖切/轴测
# color_palette: 暖橙/冷青/单色/多色
# mood: 学术严谨/活泼/极简/高密度/梦幻/插画风
# 用 filename 作 key,而不是 db id(因为 DB 的 id 是 build_db.py 扫目录时给的,顺序跟文件名不对应)
TAGS = {
    'Analysis (1).jpg': {  # 城市广场轴测, 橙红多色线稿
        'analysis_type': '城市总图',
        'arch_type': '轴测图',
        'scene': '公共空间',
        'scale': '街区级',
        'render_style': '线稿',
        'view_type': '轴测',
        'color_palette': '暖橙',
        'mood': '高密度',
        'caption': '城市广场轴测分析 · 多层建筑围合 + 红色活动装置',
        'description': '典型欧洲城市广场的轴测分析图,周边多层住宅围合,中央布置红色构筑物(市集、廊架、剧场),底层有林荫步道和运动场地。线条+暖橙单色叠加,信息量大但不乱。',
        'keywords': '城市广场,轴测,围合空间,市集,公共活动,街道家具,林荫道',
    },
    'Analysis (2).jpg': {  # 冷蓝紫 4 层分功能建筑 · 动线+功能分析
        'analysis_type': '动线分析',
        'arch_type': '轴测图',
        'scene': '文化',
        'scale': '建筑级',
        'render_style': '渲染',
        'view_type': '轴测',
        'color_palette': '冷青',
        'mood': '梦幻',
        'caption': '博物馆/教育建筑分层功能分析 · MOTOR/EXPLORE/EXPERIMENT/ENGAGE',
        'description': '四层分体量文化/教育建筑,每层标一个动词(MOTOR 引擎、EXPLORE 探索、EXPERIMENT 实验、ENGAGE 互动),有红色动线箭头穿越四层,说明功能递进和参观流线。冷蓝紫渐变+小粉人尺度感。',
        'keywords': '功能分析,动线,博物馆,教育,分层,展览,渐进式体验',
    },
    'Analysis (3).jpg': {  # NIMBY vs YIMBY 城市演变 · 蓝粉对比 · 带年份
        'analysis_type': '城市总图',
        'arch_type': '轴测图',
        'scene': '城市设计',
        'scale': '城市级',
        'render_style': '线稿',
        'view_type': '轴测',
        'color_palette': '多色',
        'mood': '学术严谨',
        'caption': '城市扩张与抵抗分析 · NIMBY vs YIMBY 2000-2020 演变',
        'description': '对比性城市分析:左下角蓝色 NIMBY(反对开发)圈出空白地,右上方粉色 YIMBY(拥抱开发)展示新住宅和街道,中间是车流主干道。带 2000/2010/2015/2020 四个时间窗。典型的社会议题可视化分析图。',
        'keywords': 'NIMBY,YIMBY,城市更新,住房政策,社会分析,时间演变,批判性',
    },
    'Analysis (4).jpg': {  # 热带滨海建筑 · 渲染+线稿混合 · 粉屋顶
        'analysis_type': '建筑总图',
        'arch_type': '轴测图',
        'scene': '公共空间',
        'scale': '建筑级',
        'render_style': '混合媒介',
        'view_type': '轴测',
        'color_palette': '暖橙',
        'mood': '活泼',
        'caption': '热带滨海建筑组群分析 · 坡屋顶 + 棕榈 + 海堤',
        'description': '热带风情建筑组群的轴测渲染分析,粉红坡屋顶+黄色墙体,棕榈树点缀,临海有堤岸和快艇。混合媒介(实景+渲染+手绘),氛围感强。',
        'keywords': '热带,滨海,坡屋顶,棕榈,文旅,度假区,综合建筑群',
    },
    'Analysis (5).jpg': {  # 圆形水塔社区 · 粉黄蓝绿 · 拉丁美洲风
        'analysis_type': '城市总图',
        'arch_type': '轴测图',
        'scene': '公共空间',
        'scale': '街区级',
        'render_style': '渲染',
        'view_type': '轴测',
        'color_palette': '多色',
        'mood': '活泼',
        'caption': '拉丁美洲式社区总图 · 圆形水塔 + 低层住宅 + 街市',
        'description': 'Site Center 社区总图,核心是一个粉色圆形水塔(兼作社区中心),围绕低层粉黄住宅,街角有市集摊位和棕榈树。色彩活泼、人物众多、地面铺装清晰。',
        'keywords': '社区中心,水塔,拉丁美洲,低层高密度,街市,公共空间',
    },
    'Analysis (6).jpg': {  # 竹林+中式建筑+熊猫+鸟 · 剖切
        'analysis_type': '剖切分析',
        'arch_type': '剖面图',
        'scene': '景观',
        'scale': '建筑级',
        'render_style': '插画风',
        'view_type': '剖切',
        'color_palette': '多色',
        'mood': '活泼',
        'caption': '竹林生态建筑剖切 · 中式屋檐 + 熊猫栖息 + 飞鸟',
        'description': '竹林生态建筑剖切分析,曲线屋檐层层退台,白鹤/熊猫/橙色鸟点缀其中,地面有石板小径和游人。中式现代风,画面叙事感很强。',
        'keywords': '生态建筑,竹林,中式,剖切,动物栖息,展览建筑,文旅',
    },
    'Analysis (7).jpg': {  # 透视 · 城市广场 · 青色调 · 红色人影
        'analysis_type': '透视分析',
        'arch_type': '透视图',
        'scene': '公共空间',
        'scale': '建筑级',
        'render_style': '渲染',
        'view_type': '透视',
        'color_palette': '冷青',
        'mood': '梦幻',
        'caption': '城市下沉广场透视 · 阶梯看台 + 月夜氛围',
        'description': '城市下沉广场的人视点透视,前景是坐在台阶上看演出的人(剪影+红色块),中景是表演场地,背景是城市建筑。冷青底色+粉红人剪影,氛围梦幻。',
        'keywords': '下沉广场,表演空间,公共生活,夜景,城市看台',
    },
    'Analysis (8).jpg': {  # 紫粉高密度市场街区 · RENDER ZOO
        'analysis_type': '功能分区',
        'arch_type': '轴测图',
        'scene': '商业',
        'scale': '街区级',
        'render_style': '渲染',
        'view_type': '轴测',
        'color_palette': '多色',
        'mood': '高密度',
        'caption': '高密度市场街区功能分区 · 紫粉色调 + RENDER ZOO 出品',
        'description': '热带高密度市场街区的轴测分析,紫粉色建筑外墙、悬挑廊桥、底层市集,街道上有车、手推车、行人,信息密集。RENDER ZOO 工作室作品风格。',
        'keywords': '市场,商业街区,高密度,廊桥,热带,功能混合',
    },
    'Analysis (9).jpg': {  # MERCADONA 超市 + 农贸市场 + 红穹顶
        'analysis_type': '业态分析',
        'arch_type': '轴测图',
        'scene': '商业',
        'scale': '建筑级',
        'render_style': '线稿',
        'view_type': '轴测',
        'color_palette': '暖橙',
        'mood': '活泼',
        'caption': '超市 + 农贸市集业态分析 · MERCADONA 主店 + 红穹顶集市',
        'description': 'MERCADONA 超市主导的混合业态分析:主店+绿色屋顶停车场,旁边是粉色农贸摊位区+红色穹顶市集广场。轴测线稿+暖橙单色,信息层次清晰。',
        'keywords': '超市,农贸市场,穹顶,商业综合体,混合业态,绿色屋顶',
    },
    'Analysis (10).jpg': {  # THE LIVING SCAFFOLD · 红色+蓝色 · 数据+图解
        'analysis_type': '社会分析',
        'arch_type': '混合媒介',
        'scene': '城市设计',
        'scale': '城市级',
        'render_style': '线稿',
        'view_type': '轴测',
        'color_palette': '多色',
        'mood': '学术严谨',
        'caption': '活脚手架系统 · 纽约步行道沿线临时庇护所方案',
        'description': '纽约市 1980 年以来建造了 8000 处临时庇护所+378 英里步行道,平均使用 1.5 年。提案"活脚手架"系统:可回收的脚手架+互动投影+绿色屋顶,提供模块化庇护、社区互动、再生材料。典型的图解+数据+轴测混合分析。',
        'keywords': '社会设计,临时庇护,脚手架,模块化,城市更新,数据可视化,案例研究',
    },
    'Analysis (11).jpg': {  # 高架曲线桥 · 橙红+蓝渐变 · 透视
        'analysis_type': '形态生成',
        'arch_type': '透视图',
        'scene': '城市设计',
        'scale': '建筑级',
        'render_style': '混合媒介',
        'view_type': '透视',
        'color_palette': '暖橙',
        'mood': '极简',
        'caption': '高架曲线桥形态生成 · 橙红结构线 + 蓝渐变海面 + 飞机',
        'description': '极简形态分析:一条蛇形高架桥用橙红结构线勾勒,下方是深蓝渐变海水,天空中一架客机飞过,前景有一人划皮划艇。极简但张力强。',
        'keywords': '高架桥,曲线,基础设施,极简,结构表现,海洋',
    },
}


def main():
    if not os.path.exists(DB):
        sys.exit(f'DB not found: {DB}')

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # 1. 加 analysis_type 列(若不存在)
    cur.execute("PRAGMA table_info(images)")
    cols = {r[1] for r in cur.fetchall()}
    if 'analysis_type' not in cols:
        cur.execute("ALTER TABLE images ADD COLUMN analysis_type TEXT")
        print('[+] ALTER TABLE: add analysis_type column')
    else:
        print('[=] analysis_type column exists')

    # 2. 打标入库
    now = datetime.now().isoformat(timespec='seconds')
    updated = 0
    for filename, tag in TAGS.items():
        # 通过 filename 查 db id
        cur.execute("SELECT id FROM images WHERE filename=?", (filename,))
        row = cur.fetchone()
        if not row:
            print(f'[!] filename={filename} 在 DB 中不存在,跳过')
            continue
        img_id = row[0]
        cur.execute('''
            UPDATE images SET
                analysis_type = ?,
                arch_type = ?,
                scene = ?,
                scale = ?,
                render_style = ?,
                view_type = ?,
                color_palette = ?,
                mood = ?,
                caption = ?,
                description = ?,
                keywords = ?,
                updated_at = ?
            WHERE id = ?
        ''', (
            tag['analysis_type'], tag['arch_type'], tag['scene'], tag['scale'],
            tag['render_style'], tag['view_type'], tag['color_palette'], tag['mood'],
            tag['caption'], tag['description'], tag['keywords'],
            now, img_id,
        ))
        updated += cur.rowcount
        print(f'  [id={img_id:>2}] {filename:<20s} {tag["analysis_type"]:8s} | {tag["arch_type"]:8s} | {tag["scene"]:8s} | {tag["mood"]}')

    conn.commit()
    print(f'\n[done] {updated} 张图打标入库 ({now})')
    conn.close()


if __name__ == '__main__':
    import sys
    main()
