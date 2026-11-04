# -*- coding: utf-8 -*-
"""生成《上手操作手册 + GitHub 上传指南》Word 文档。"""

import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "小微评测工具包-上手手册与GitHub指南.docx")

doc = Document()
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


def P(text, bold=False, size=10.5, indent=0):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
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
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(9.5)
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    r.font.color.rgb = RGBColor(0x0F, 0x4C, 0x81)
    return p


def BULLET(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.line_spacing = 1.4
    if bold_prefix:
        r1 = p.add_run(bold_prefix)
        r1.bold = True
        r1.font.size = Pt(10.5)
        r1.font.name = "宋体"
        r1._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    r.font.name = "宋体"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    return p


def NUM(n, text, bold_prefix=None):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.75)
    p.paragraph_format.line_spacing = 1.4
    r0 = p.add_run(f"{n}. ")
    r0.bold = True
    r0.font.size = Pt(10.5)
    r0.font.name = "宋体"
    if bold_prefix:
        r1 = p.add_run(bold_prefix)
        r1.bold = True
        r1.font.size = Pt(10.5)
        r1.font.name = "宋体"
        r1._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    r.font.name = "宋体"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    return p


def TABLE(headers, rows):
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
tr = tp.add_run("小微评测工具包")
tr.bold = True
tr.font.size = Pt(22)
tr.font.name = "微软雅黑"
tr._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

sp = doc.add_paragraph()
sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
sr = sp.add_run("上手操作手册 与 GitHub 上传指南")
sr.bold = True
sr.font.size = Pt(15)
sr.font.name = "微软雅黑"
sr._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")

mp = doc.add_paragraph()
mp.alignment = WD_ALIGN_PARAGRAPH.CENTER
mr = mp.add_run("2026 全国大学生软件测试大赛 · 微信小微 AI 助手评测专项赛")
mr.font.size = Pt(11)
mr.font.name = "宋体"
mr._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

ip = doc.add_paragraph()
ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
ir = ip.add_run("2026 全国大学生软件测试大赛 · 微信小微 AI 助手评测专项赛\n"
                "仓库：github.com/zhu2136161773zhu-oss/xiaowei-eval-toolkit\n"
                "生成日期：2026-11-04")
ir.font.size = Pt(10)
ir.font.name = "宋体"
ir._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
doc.add_paragraph()

P("说明：本文档讲两件事——上半部分教你「怎么把这个工具用起来」，"
  "下半部分教你「怎么把成果传到 GitHub 仓库并持续维护」。"
  "你手上的仓库已经传上去了，第二部分主要是教你怎么在后续持续更新它。", bold=True)

# ================================================================ 第一部分
H("第一部分　怎么用起来", 1)

H("一、开工前的 5 分钟准备", 2)
NUM(1, "打开命令行。推荐用 Git Bash（在文件夹里右键 → Open Git Bash here），"
       "路径带中文时不会出问题。Windows 的 PowerShell 也行，但个别命令行为略有差异。")
NUM(2, "进入工具包目录：")
CODE('cd "C:\\Users\\Jerry\\OneDrive\\Desktop\\我的文件\\特殊资料与一些文件\\小微评测工具包"')
NUM(3, "确认环境正常（会打印四项自检结果，最后一行是 all checks passed）：")
CODE("python selftest.py")
P("如果这一行没出现，说明环境有问题，把报错发我，我帮你看。", bold=True)
NUM(4, "在手机上准备好：微信升级到最新版、确认左上角能看到小微入口、"
       "设置 → 记忆与隐私里确认记忆开关状态（做对照实验时要切换）。")
P("官方提醒：PC 端功能残缺，务必用手机测。鸿蒙需要升到微信 2.3 才能测全功能。", bold=True)

H("二、三步走完一轮评测", 2)

H("第 1 步：生成用例", 3)
CODE("python pipeline.py gen --suite A")
P("场景代号：A 复合指令与任务编排 / B 约束保持与数值理解 / "
  "C 内容理解与图表生成 / D 能力边界与拒答合理性 / "
  "E 评测方法与长文本处理 / F 社交与内容生态 / all 全部 129 条。")
P("建议顺序：A → B → C → D。E 套是给「创新与方法论」评分项用的，"
  "F 套是配菜，不要在这两套上花太多时间。", bold=True)
P("注意：小微在「生成小工具」时会跳转到独立页面，对话被打断、回复无法采集。"
  "因此所有用例都不要求它实际生成工具；工具类能力只问说明，归入 D 套边界洞察。", bold=True)

H("第 2 步：采集对话（半自动，最关键的一步）", 3)
CODE("python pipeline.py run --suite A --mode manual")
P("然后按这个节奏操作，每条指令重复四步：")
NUM(1, "终端里会显示一条指令，例如「帮我找一下之前收藏的几篇关于费曼学习法的公众号文章，"
       "总结一下主要观点。」此时脚本已把它放进剪贴板。", bold_prefix="")
NUM(2, "切到手机微信 → 点开左上角小微 → 长按输入框 → 粘贴 → 发送。", bold_prefix="")
NUM(3, "等小微答完。**这一步是你的观察窗口**，官方要求的观察点脚本会提前打印给你，"
       "对照着看：工具生成成功率、图表数据是否与输入一致、提醒是否按纯时间触发……", bold_prefix="")
NUM(4, "长按小微的回复 → 复制 → 切回终端 → 按 Ctrl+V → 回车。"
       "脚本会自动读走剪贴板内容并落盘。", bold_prefix="")
P("小技巧：")
BULLET("回车前如果粘贴没生效，直接在终端输入框里 Ctrl+V 再回车也一样")
BULLET("这条不想测就输入 SKIP 跳过；想收工就输入 QUIT 结束，已采集的内容会自动保存")
BULLET("终端不会闪退，它会一直等你的输入")
BULLET("每条指令之间脚本会自动等 5–15 秒，这是官方红线要求（QPM ≤ 16），别去改它")

H("第 3 步：自动筛查 + 出报告", 3)
CODE("python pipeline.py report --raw data/raw_A.jsonl --suite A")
P("这会做两件事：")
BULLET("八类检测器自动筛查，把可疑样本标出来（上下文污染、品类串台、状态隔离失效、"
       "约束丢失、模糊失败话术、数值幻觉、答案翻转、越界宣称）")
BULLET("生成 Markdown 报告，每条案例已按官方六要素写好，并附赛事表单字段对照表")
P("要 Word 版就在末尾加 --docx：")
CODE("python pipeline.py report --raw data/raw_A.jsonl --suite A --docx")
P("输出在 data\\reports\\ 目录下。")

H("三、四种采集模式怎么选", 2)
TABLE(
    ["模式", "命令", "什么时候用"],
    [
        ["半自动", "--mode manual", "默认选它。零配置，今晚就能跑，人在回路里判断最准"],
        ["持续循环", "--mode loop --rounds 5",
         "同一条指令反复问，验证官方第五条「能稳定复现」，也能抓出偶现问题的出现频率"],
        ["安卓自动化", "--mode uia2 --serial <设备号>",
         "手机开 USB 调试 + pip install uiautomator2。适合夜里挂着跑变参扫描"],
        ["PC 微信", "--mode pc", "别用。官方明示 PC 端功能残缺，落后移动端 1–2 个版本"],
    ],
)

H("四、测试时必须做的三组对照实验", 2)
P("这是报告里最有说服力的部分。官方答疑明确认可控制变量与差分测试的因果推断证据。", bold=True)
P("对照一：单发 vs 复合下发", bold=True)
BULLET("同一条指令单独发给小微，记一次结果")
BULLET("再把它放进复合指令里发给小微，记一次结果")
BULLET("结论：若单发正常、复合失败 → 问题在任务编排层，不在这个能力本身。"
       "这一步把「小微表现不佳」升级成「可修复的具体环节」。")
P("对照二：开记忆 vs 关记忆", bold=True)
BULLET("用两个微信号：A 开记忆、B 关记忆")
BULLET("每次测完立即长按删除对话，清空记忆库、RAG 库与上下文")
BULLET("同一用例在两个账号各跑一次，差异即记忆的影响")
P("对照三：清空上下文 vs 保留上下文", bold=True)
BULLET("测完立即长按删对话 → 重发同一条指令")
BULLET("结果不同 → 该问题成因与上下文状态强相关")

H("五、容易被忽略但会扣分的地方", 2)
BULLET("测完立刻长按删除对话。不清记忆，下一条用例就是脏的，"
       "「变参测试」和「多轮改条件」根本不成立。")
BULLET("Good Case 也要写。官方明说只写坏的反而扣分，Good Case 是加分项。"
       "大部分人只会交 Bad Case，这正是你能拉开差距的地方。")
BULLET("Bad Case、Good Case、能力边界洞察，三类分开提交。")
BULLET("多个问题合并成一个报告更被鼓励——说明你看的是一类系统性问题，不是零散 bug。")
BULLET("截图别截长屏。小微本身不支持长屏截图，拆开截重点部分。马赛克可以用。")
BULLET("偶现的问题也算，但要标注「偶现」并写清复现次数，别混在必现里。")
BULLET("四种入口都试一遍：负一屏左上角绿眼睛、聊天框「+」号第 8 个位置、"
       "长按聊天消息、公众号/视频号页面。不同入口的能力差异本身就是发现。")

H("六、常见问题速查", 2)
TABLE(
    ["现象", "原因与解法"],
    [
        ["终端没反应 / 闪退", "没在工具包目录下运行。先 cd 过去，或直接用完整路径调用 python 脚本"],
        ["剪贴板写入失败", "剪贴板被其他程序占用，等两秒重试；或先用记事本复制一次让剪贴板有内容"],
        ["报告里全是「检测器自测」失败", "raw 文件路径不对。确认在 data\\ 目录下且文件名是 raw_A.jsonl"],
        ["中文显示成乱码", "终端编码问题。执行 chcp 65001 再运行"],
        ["小微说「我暂时还没有这个功能」", "这多半是官方明示的能力边界（群红包、批量发送、查群成员等），"
         "属于「有价值的洞察」不是 Bad Case。写进洞察那一类，别当 bug 交"],
        ["想重新测某条但上下文已脏", "长按删除对话清空，再从 pipeline.py run 重新开始"],
    ],
)

# ================================================================ 第二部分
doc.add_page_break()
H("第二部分　怎么传到 GitHub 与持续维护", 1)

H("七、你的仓库现状", 2)
P("仓库其实已经在 GitHub 上了，上一轮就建好并推送完毕。当前状态：", bold=True)
TABLE(
    ["项目", "状态"],
    [
        ["仓库地址", "https://github.com/zhu2136161773zhu-oss/xiaowei-eval-toolkit"],
        ["可见性", "Public 公开（评委、组委会老师、乃至腾讯面试官都能直接看）"],
        ["许可证", "MIT"],
        ["分支", "main（本地与远端已同步）"],
        ["提交数", "4 次（初始版 → 修 README 链接 → 修 CI 两处失败 → 修清理步骤 shell）"],
        ["CI 状态", "6/6 全绿（ubuntu / macos / windows × Python 3.8 / 3.11）"],
        ["自检徽章", "README 右上角有个绿色「自检」徽章，是活的 CI 状态"],
    ],
)
P("本地路径：C:\\Users\\Jerry\\OneDrive\\Desktop\\我的文件\\特殊资料与一些文件\\小微评测工具包", bold=True)

H("八、日常更新：改了代码怎么传上去", 2)
P("这是你以后最常用的操作。四条命令，30 秒搞定。")
P("第一步：进目录并看看改了啥", bold=True)
CODE('cd "C:\\Users\\Jerry\\OneDrive\\Desktop\\我的文件\\特殊资料与一些文件\\小微评测工具包"')
CODE("git status")
P("会列出改过的文件。git status 显示红色（modified）就是有改动。", indent=0.5)
P("第二步：本地自检（很重要，别跳过）", bold=True)
CODE("python selftest.py")
P("必须看到 all checks passed 才提交。这套检查和 GitHub 上跑的是同一套逻辑，"
  "本地过了远程基本不会挂。", indent=0.5)
P("第三步：提交", bold=True)
CODE("git add -A")
CODE('git commit -m "feat: 新增 XX 功能的检测规则"')
P("commit -m 后面用英文或中文都行，但写成「做了什么」而不是「改了点东西」。"
  "比如 feat: 新增答案翻转检测规则、fix: 修正泛词过滤误报、docs: 补充对照实验说明。", indent=0.5)
P("第四步：推送", bold=True)
CODE("git push")
P("看到类似 To https://github.com/... main -> main 就成功了。", indent=0.5)

H("九、完整的操作示例", 2)
P("场景：你觉得检测器漏了「小微把预算理解成上限」这种情况，想加一条新规则。")
CODE("""# 1. 改代码
#    打开 analyze.py，在 DETECTORS 字典里加一项，再写对应的检测函数

# 2. 本地验证
python selftest.py

# 3. 提交并推送
git add -A
git commit -m "feat: 新增预算上下界混淆检测"
git push

# 4. 打开仓库网页，看右上角「自检」徽章从黄色转绿色""")

H("十、推送时可能遇到的问题", 2)
TABLE(
    ["提示", "原因", "解法"],
    [
        ["Updates were rejected", "远端有你本地没有的提交", "git pull --rebase origin main 然后 git push"],
        ["could not read Username", "凭据没记住", "重新执行 git push，会弹出浏览器让你登录 GitHub"],
        ["nothing to commit", "没有改动或改动已被提交", "git status 确认状态；已有改动用 git add -A"],
        ["fatal: not a git repository", "不在工具包目录下", "先 cd 到正确目录"],
        ["CI 徽章是红的", "代码在某些平台跑不通", "点进徽章看失败步骤的日志，把报错发我"],
    ],
)
P("最常见的是第一条。如果推送被拒，执行这两句就好：", bold=True)
CODE("git pull --rebase origin main")
CODE("git push")

H("十一、想改提交里的邮箱", 2)
P("现在提交记录里的邮箱是占位地址 your-email@example.com。"
  "如果你想换成自己常用的邮箱（比如和 GitHub 账号绑定的那个），执行：")
CODE("""git config user.email "你的真实邮箱"
git config user.name "你的名字"
git commit --amend --reset-author --no-edit
git push -f""")
P("注意最后的 -f 是强制推送。如果这个仓库只有你一个人在用（现在就是），"
  "强制推送是安全的；如果以后有别人参与，就别用 -f，改用下面这个方式：", bold=True)
CODE("""git commit --amend --reset-author --no-edit
git push --force-with-lease""")

H("十二、GitHub 页面上的几个实用功能", 2)
BULLET("右上角绿色「自检」徽章：点进去能看到 CI 跑到哪一步了，"
       "这是给评委看的「工程化程度」信号。")
BULLET("Actions 标签页：所有历史构建记录，出问题时先看这里。")
BULLET("Issues 标签页：已内置报告模板，注意模板里有一项「隐私确认」勾选——"
       "提交 issue 前记得删掉任何真实聊天记录和好友信息。")
BULLET("Discussions：已开启。可以在里面写「评测方法论讨论」，"
       "比如「复合指令的三种失败形态」，这类内容对作品集很有加分。")
BULLET("Insights → Traffic：能看到有多少人访问过你的仓库，"
       "如果之后投腾讯实习，这是个能写进简历的量化数字。")

H("十三、给你的建议", 2)
P("仓库本身已经是一个能进简历的作品了。但让它更有杀伤力的，是把评测数据和结论也放上去。", bold=True)
BULLET("跑完 A 套后，把筛查出的典型案例整理成一份「小微评测观察」文档放仓库里。"
       "但注意：真实对话记录绝不能上传（.gitignore 已经挡住了 raw_*.jsonl），"
       "只放你重写过的、脱敏的案例。")
BULLET("在 README 里加一段「实测发现摘要」，用列表写清楚你发现了哪几类问题。"
       "这一段比代码本身更能证明你真的测过。")
BULLET("把「单发 vs 复合下发」的对照数据做成一张对比表，"
       "这是官方答疑里明确认可的因果推断证据，含金量最高。")
BULLET("每个 commit 写清楚改了什么，git 历史本身就是一份工作日志——"
       "面试官会看的。")
P("最后提醒：官方明说「评测报告禁止由 AI 全权代写」。"
  "仓库里放方法和工具是加分项，但最终报告里的判断、归因和结论必须是你自己判断的。", bold=True)

doc.save(OUT)
print("[OK] 已生成:", OUT)
