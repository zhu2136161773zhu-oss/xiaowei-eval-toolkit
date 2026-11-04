# -*- coding: utf-8 -*-
"""生成工具包使用手册（Word）。"""

import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "小微评测工具包-使用手册.docx")

doc = Document()

# 全局字体
st = doc.styles["Normal"]
st.font.name = "宋体"
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
st.paragraph_format.line_spacing = 1.5
st.paragraph_format.space_after = Pt(4)


def H(text, level=1):
    p = doc.add_heading(text, level=level)
    for r in p.runs:
        r.font.name = "微软雅黑"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        r.font.color.rgb = RGBColor(0x1F, 0x1F, 0x1F)
    return p


def P(text, bold=False, size=10.5):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.name = "宋体"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    return p


def CODE(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.75)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(9.5)
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    r.font.color.rgb = RGBColor(0x0F, 0x4C, 0x81)
    return p


def BULLET(text):
    p = doc.add_paragraph(text, style="List Bullet")
    p.paragraph_format.line_spacing = 1.4
    for r in p.runs:
        r.font.size = Pt(10.5)
        r.font.name = "宋体"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    return p


def TABLE(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        r = hdr[i].paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(10)
        r.font.name = "宋体"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(9.5)
            r.font.name = "宋体"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    doc.add_paragraph()
    return t


# ================================================================ 封面
tp = doc.add_paragraph()
tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
tr = tp.add_run("小微 AI 助手评测工具包")
tr.bold = True
tr.font.size = Pt(22)
tr.font.name = "微软雅黑"
tr._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

sp = doc.add_paragraph()
sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
sr = sp.add_run("使用手册")
sr.bold = True
sr.font.size = Pt(16)
sr.font.name = "微软雅黑"
sr._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

mp = doc.add_paragraph()
mp.alignment = WD_ALIGN_PARAGRAPH.CENTER
mr = mp.add_run("2026 全国大学生软件测试大赛 · 微信小微 AI 助手评测专项赛")
mr.font.size = Pt(11)
mr.font.name = "宋体"
mr._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
ir = info.add_run("制作者：xiaowei-eval-toolkit contributors　｜　广东医科大学 电子信息工程与智能医学工程\n"
                   "版本：v1.0　｜　生成日期：2026-11-04")
ir.font.size = Pt(10)
ir.font.name = "宋体"
ir._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

doc.add_paragraph()

# ================================================================ 一、为什么做这个
H("一、这个工具包解决什么问题", 1)
P("官方培训明确了两条对参赛者极其有利的规则：")
BULLET("「用自动化框架生成上万条输入、只挑异常案例提交」——允许；")
BULLET("「在报告中展示技术实现与实际效果」——允许，且可直接提升「创新与方法论」评分。")
P("同时也划了红线：外部工具打线上 QPM 不得超过 16；不得注入违规内容。")
P("本工具包就是围绕这两条规则设计的：把「人工一条条手测」变成「批量生成 → 自动筛查 → 人工复核」，"
  "让有限的体验时间（11 月 1 日至 5 日）产出尽可能多的有效案例，同时保证不越线。")
P("关键前提：小微没有对外的对话 API。微信开放社区的「小微开放接口」是给智能音箱与技能平台用的，"
  "不是微信内嵌的这位小微助手。因此采集只能走 UI 自动化或半自动粘贴，本工具包两条路都提供了。")

# ================================================================ 二、文件清单
H("二、文件清单", 1)
TABLE(
    ["文件", "作用"],
    [
        ["config.json", "全局配置：限速（QPM）、检测阈值、驱动方式、报告字段"],
        ["gen_cases.py", "用例生成器：按官方四条打法批量生成测试用例"],
        ["run.py", "采集驱动器：manual 半自动粘贴 / uia2 安卓全自动化"],
        ["analyze.py", "自动异常检测器：八类检测规则，只把可疑样本推给人看"],
        ["report.py", "报告生成器：转成官方六要素报告 + 赛事表单字段"],
        ["pipeline.py", "一键流水线：串起生成→采集→筛查→出报告"],
        ["cases/", "生成好的用例 JSON"],
        ["data/", "采集结果 raw_*.jsonl、筛查结果 flagged_*.json、报告、截图"],
    ],
)

# ================================================================ 三、快速开始
H("三、快速开始（今天就能跑）", 1)

H("3.1 第一步：生成用例", 2)
CODE("cd 小微评测工具包")
CODE("python pipeline.py gen --suite A")
P("suite 可选 A（高数错题打卡）/ B（团务台账）/ C（实验数据转报告）/ D（生理体征随访）/ "
  "E（评测自动化）/ F（本地 AI 速查）/ all（全 80 条）。")

H("3.2 第二步：采集（半自动，无需任何配置）", 2)
CODE("python pipeline.py run --suite A --mode manual")
P("脚本会把每一条指令写进剪贴板，你只要：")
BULLET("切到手机微信 → 点开小微 → 粘贴 → 发送")
BULLET("等它答完 → 复制回复 → 切回终端 → 粘贴 → 回车")
BULLET("想跳过就输入 SKIP，想收工就输入 QUIT")
P("脚本会自动限速（默认 QPM 8，硬上限 16）并把每轮对话落盘成 JSONL。")

H("3.3 第三步：自动筛查 + 出报告", 2)
CODE("python pipeline.py report --raw data/raw_A.jsonl --suite A")
CODE("python pipeline.py report --raw data/raw_A.jsonl --suite A --docx")
P("第一条命令出 Markdown，第二条出 Word。报告里每条案例都已按官方六要素写好：")
P("场景描述 → 复现步骤 → 期望小微回复的内容 → 实际结果 → 原因分析 → 改进建议", bold=True)
P("同时附一张赛事表单字段对照表，逐项填好，你只需要复核和补截图。")

# ================================================================ 四、四条打法
H("四、用例设计覆盖的官方四条打法", 1)
TABLE(
    ["打法", "对应参数", "用例数量", "设计要点"],
    [
        ["复合需求", "compound", "11 条",
         "多能力串联，一次说完。对应官方示例「找文章→总结→PDF→打卡→提醒」的同类结构"],
        ["变参测试", "param", "51 条",
         "时间、人数、预算、城市、图表类型、量化方式等逐项替换，检验意图理解的一致性"],
        ["多轮改条件", "multi_turn", "6 条",
         "模拟真实人类改方案：改人数→改预算→改偏好→改口径，看它能否像助理一样吸收"],
        ["边界探测", "boundary", "12 条",
         "逼近官方明示的不支持清单，区分「Bad Case」与「有价值的能力边界洞察」"],
    ],
)
P("注意：A–F 六个场景共 80 条用例，但不要一次全跑完。按官方提示，"
  "初赛更看「问题发现 + 场景设计 + 逻辑分析 + 报告质量」，"
  "宁可把 A 套 20 条跑透、报告写扎实，也不要 80 条都测得浅。")

# ================================================================ 五、检测器
H("五、自动异常检测器能抓什么", 1)
P("这是本工具包的核心技术实现。八类检测规则，全部基于小微实测暴露的真实缺陷模式设计：")
TABLE(
    ["检测类型", "抓什么", "严重度"],
    [
        ["上下文污染", "本轮回复出现前序任务的文本片段（n-gram 交叉比对）", "高 / 中"],
        ["品类串台", "本轮任务不涉及该品类，回复却带着前序品类的结果（语义级）", "高"],
        ["状态隔离失效", "本轮回复与历史用例的回复高度重合，草稿/上下文未隔离", "高"],
        ["约束丢失", "指令给了预算、人数、附近、时间，回复里完全没体现", "中 / 低"],
        ["模糊失败话术", "把失败归给「接口/系统/检索结果」，而非坦承能力不足", "中"],
        ["数值幻觉", "回复出现指令里根本不存在的具体数值", "中"],
        ["答案翻转", "先给出正确答案，被用户错误质疑后改口（官方认定为 Bad Case）", "高"],
        ["越界宣称", "对官方明示不支持的能力却说「可以/支持」", "高"],
    ],
)
P("两个设计细节值得在报告里写出来，它们本身就是加分点：", bold=True)
BULLET("跨会话滚动语料：状态串台常常来自「上一次测试」而非同一条用例内部，"
       "所以检测器维护一份跨会话滚动语料库，比对范围覆盖全部历史用例。")
BULLET("品类同义词映射：前一轮点的是「瑞幸生椰拿铁」，本轮搜「火锅」却返回「咖啡相关的小程序」——"
       "字面比对抓不到，只有在品类层面才能识别出这是上下文污染。")
P("检测器输出的是「可疑」，不是「结论」。每条都附了初步归因建议，最终定性仍由你人工把关。")

# ================================================================ 六、实验设计
H("六、必须做的对照实验", 1)
P("官方答疑里明确认可控制变量与差分测试的因果推断证据。以下三组对照是报告里最有说服力的部分：")
P("对照一：单发 vs 复合下发", bold=True)
BULLET("同一条指令单独发给小微，记录结果")
BULLET("再把它放进复合指令里发给小微，记录结果")
BULLET("若单发正常、复合失败 → 问题定位在任务编排层，而非该能力本身。这是归因的关键一步。")
P("对照二：开记忆 vs 关记忆", bold=True)
BULLET("用两个微信号：A 开记忆、B 关记忆")
BULLET("每次测完立即长按删除对话，清空记忆库、RAG 库与上下文，避免污染后续实验")
BULLET("同一用例在两个账号各跑一次，差异即为记忆带来的影响")
P("对照三：清空上下文 vs 保留上下文", bold=True)
BULLET("测完立即长按删除对话 → 重发同一条指令")
BULLET("若结果不同，说明该问题的成因与上下文状态强相关")
P("以上三组对照的结论，都可以作为报告「原因分析」一节的直接证据，"
  "而不是停留在「可能是上下文问题」的猜测层面。", bold=True)

# ================================================================ 七、报告怎么写
H("七、报告怎么写才拿分", 1)
P("官方评审关注四件事：问题发现、场景设计、逻辑分析、报告质量。以下几条是踩过坑的提醒：")
BULLET("Good Case 也要写。官方明说只写坏的反而扣分，Good Case 是加分项。大部分人只会交 Bad Case，"
       "这正是拉开差距的地方。")
BULLET("Bad Case、Good Case、能力边界洞察，三类分开提交，别混在一起。")
BULLET("多个问题合并成一个报告提交更被鼓励——说明你看出的是一类系统性问题，而不是零散 bug。")
BULLET("截图别截长屏。小微本身不支持长屏截图，拆开截重点部分。马赛克处理过的可以用。")
BULLET("偶现的问题也算，但要明确标注「偶现」并写明复现次数，不要混在必现里。")
BULLET("复现步骤要写到别人能照着做，包括附加条件（哪个入口、记忆开关状态、清理过没有）。")
P("报告六要素的「原因分析」一栏，官方给的归因示例值得模仿——"
  "不要只写「小微表现不佳」，而要给出具体的机制推测（如可能是 OCR 或多模态识别能力不足、"
  "人脸匹配不精准；也可能模型抗干扰能力弱，图文信息过多导致幻觉），并说明还需要什么证据来验证。")

# ================================================================ 八、红线
H("八、红线与注意事项", 1)
TABLE(
    ["事项", "要求"],
    [
        ["QPM", "不得超过 16。工具默认 8，超 16 会强制降速并告警"],
        ["违规内容", "严禁注入黄反暴政等内容，有封号风险"],
        ["环境", "优先用移动端评测。PC 端功能残缺，落后移动端 1–2 个版本"],
        ["微信版本", "鸿蒙需升到 2.3 才能稳定测全功能"],
        ["双端同步", "跨端聊天记录互通需在「设置 → 记忆与隐私」开启「自动同步」"],
        ["清记忆", "关闭记忆功能并长按删除对话，可完全清空（记忆库、RAG 库、上下文）"],
        ["预选赛证书", "预选赛不发证书，进入决赛才有"],
        ["提交", "趁早提交。练习仓库与正式仓库不是同一个，正式仓库开赛后开放"],
    ],
)
P("时间节点：11 月 5 日产品熟悉期结束，11 月 6 日初赛开始，11 月 13 日提交截止，"
  "12 月 5–6 日总决赛（广东拓思软件科学园，现场赛）。", bold=True)

# ================================================================ 九、进阶
H("九、进阶玩法（拿「创新与方法论」高分）", 1)
P("以下三件事是本工具包的延伸方向，做了就能在报告里写「创新与方法论」：")
P("一、批量变参扫描", bold=True)
BULLET("把某个变量在 20 种取值上跑一遍，找出「在哪个取值上开始出错」的临界点")
BULLET("这类「失效边界定位」是普通参赛者很难交付的东西")
P("二、差分测试与因果归因", bold=True)
BULLET("固定其他条件，只变一个因子，观察输出差异")
BULLET("官方答疑明确认可控制变量与差分测试形成的因果推断证据")
P("三、自动化评分器的一致性检验", bold=True)
BULLET("官方在答疑中透露，他们自己就用多个不同大模型作为评审器，"
       "通过多评审一致性检验（IAA、卡帕值 Kappa）压制系统性偏差")
BULLET("你可以把自己的自动检测器用同样的方法做一次一致性验证，"
       "比如让两个不同模型各自独立判断一批样本，报告 Kappa 值")
BULLET("这一节写进报告，是「创新与方法论」评分项里最有说服力的内容")

# ================================================================ 附：待办
H("附：给你的行动清单", 1)
TABLE(
    ["优先级", "动作", "预计耗时"],
    [
        ["P0", "确认小微权限已开通（11 月 1 日统一开通），在手机上把四类入口都点一遍", "20 分钟"],
        ["P0", "跑通 A 套 manual 模式的前 5 条用例，确认采集链路无误", "40 分钟"],
        ["P0", "开一个 Good Case 记录本——这是大部分人不会做但能加分的地方", "持续"],
        ["P1", "A/B/C 三套各做一次「单发 vs 复合下发」对照，拿到归因证据", "2 小时"],
        ["P1", "跑满 A 套 20 条 + B 套 20 条，筛查后人工复核", "3 小时"],
        ["P2", "做一次跨会话记忆对照（开记忆 vs 关记忆）", "1 小时"],
        ["P2", "写变参扫描脚本，定位失效临界点", "2 小时"],
        ["P3", "出报告（Word），逐条补截图与复现步骤", "2 小时"],
    ],
)
P("时间提醒：11 月 5 日是产品熟悉期最后一天，11 月 6 日初赛开跑，11 月 13 日提交截止。"
  "别把时间全花在打磨工具上——先按 A 套跑出案例占住坑，再回头精修。", bold=True)

doc.save(OUT)
print("[OK] 已生成:", OUT)
