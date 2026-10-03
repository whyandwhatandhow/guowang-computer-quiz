# -*- coding: utf-8 -*-
"""
电网计算机类练习题抽取引擎
将 2-练习题/ 下的 PDF/docx/xls 抽取为统一题目数据结构。

题目数据模型：
{
  "id": 全局唯一自增,
  "subject": "板块" (数据结构与算法/操作系统/数据库系统/计算机网络/计算机组成与体系结构/信息新技术/软件设计与开发/行测/公共与行业知识),
  "type": "single"|"multi"|"judge",
  "stem": "题干",
  "options": ["A.xxx", "B.xxx", ...],
  "answer": "A" 或 "ABD" 或 "正确"/"错误",
  "analysis": "解析(可选)",
  "source": "来源文件名",
  "difficulty": 可选
}
"""
import os, re, json, sys
import pymupdf

ROOT = r"D:\BaiduNetdiskDownload\电网试卷\2-练习题"
OUT = r"C:\Users\陈慧\WorkBuddy\2026-10-03-19-22-27\wangdian_app\data"

SUBJECT_MAP = {
    "数据结构与算法": "数据结构与算法",
    "操作系统": "操作系统",
    "数据库系统": "数据库系统",
    "计算机网络": "计算机网络",
    "计算机组成与体系结构": "计算机组成与体系结构",
    "信息新技术": "信息新技术",
    "软件设计与开发": "软件设计与开发",
    "行测": "行测",
    "公共与行业知识": "公共与行业知识",
    "综合题库": "综合题库",
}

questions = []
_qid = [0]

def new_q(subject, qtype, stem, options, answer, analysis="", source=""):
    _qid[0] += 1
    questions.append({
        "id": _qid[0],
        "subject": subject,
        "type": qtype,
        "stem": stem,
        "options": options,
        "answer": answer,
        "analysis": analysis,
        "source": source,
    })

def pdf_text(path):
    d = pymupdf.open(path)
    txt = "\n".join((p.get_text() or "") for p in d)
    d.close()
    return txt

# ---------- 通用工具 ----------
def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

def strip_answer_prefix(s):
    # 去掉 "【答案】" 等
    return re.sub(r'^(【答案】|答案[:：]?|参考答案[:：]?|正确答案[:：]?)\s*', '', s).strip()

def option_lines_to_list(opts):
    """把 A.xxx B.xxx 一行/多行 解析成列表"""
    # 合并所有
    return opts

# =================================================================
# 解析器 1：中公刷题班（题目文件 + 答案文件分离）
#   题目：1.xxx  A.xxx B.xxx C.xxx D.xxx
#   答案：1.【答案】D。解析：xxx
# =================================================================
def parse_zhonggong(qpath, apath, subject, source_base):
    qt = pdf_text(qpath)
    at = pdf_text(apath)
    # 提取答案映射 {题号: (答案, 解析)}
    ans_map = {}
    # 答案文件里：数字.【答案】X。解析：...
    for m in re.finditer(r'(\d{1,3})\.\s*【答案】\s*([A-Z]+)\s*。?\s*解析[:：]?\s*([^\d]*?)(?=\n\s*\d{1,3}\.\s*【答案】|\Z)', at, re.S):
        num, ans, exp = m.group(1), m.group(2), norm(m.group(3))
        ans_map[int(num)] = (ans, exp[:200])
    # 题目：数字.题干 A.xxx B.xxx...
    # 逐行扫描
    lines = [l.strip() for l in qt.split('\n')]
    i = 0
    n = len(lines)
    cur = None
    while i < n:
        l = lines[i]
        m = re.match(r'^(\d{1,3})[\.、．]\s*(.+)$', l)
        if m and not re.match(r'^[A-F][\.、．]', l):
            # 新题开始
            num = int(m.group(1))
            stem = m.group(2)
            opts = []
            i += 1
            # 收集选项
            while i < n:
                om = re.match(r'^([A-F])[\.、．]\s*(.+)$', lines[i])
                if om:
                    opts.append(f"{om.group(1)}. {norm(om.group(2))}")
                    i += 1
                elif re.match(r'^(\d{1,3})[\.、．]\s*', lines[i]) and lines[i][0].isdigit():
                    break
                else:
                    # 可能是题干续行（多行题干）
                    stem += " " + norm(lines[i])
                    i += 1
            ans, exp = ans_map.get(num, ("", ""))
            # 判定题型
            is_judge = "【判断题】" in stem or re.search(r'[（(]\s*[）)]\s*【判断题】', stem)
            # 清理判断题标记
            if is_judge:
                stem = re.sub(r'【判断题】', '', stem).strip()
            if is_judge:
                qtype = "judge"
                if ans == "A": ans = "正确"
                elif ans == "B": ans = "错误"
                opts = ["A. 正确", "B. 错误"]
            elif len(ans) > 1:
                qtype = "multi"
            else:
                qtype = "single"
            if stem:
                new_q(subject, qtype, norm(stem), opts, ans, exp, source_base)
            continue
        i += 1

# =================================================================
# 解析器 2：师说模拟题库（答案直接印在题干后）
#   格式：1．xxx A.xxx B.xxx C.xxx D.xxx 答：C / 答，C
#   判断题：答案直接写"正确"/"错误"
# =================================================================
def parse_shishuo(path, subject, source_base):
    txt = pdf_text(path)
    lines = [l.strip() for l in txt.split('\n')]
    i = 0; n = len(lines)
    # 识别题型标题段
    while i < n:
        l = lines[i]
        m = re.match(r'^(\d{1,3})[\.、．]\s*(.+)$', l)
        if m and not re.match(r'^[A-F][\.、．]', l):
            num = int(m.group(1)); stem = m.group(2)
            opts = []; ans = ""; exp = ""
            i += 1
            while i < n:
                line = lines[i]
                om = re.match(r'^([A-F])[\.、．]\s*(.+)$', line)
                if om:
                    opts.append(f"{om.group(1)}. {norm(om.group(2))}")
                    i += 1
                elif re.match(r'^(\d{1,3})[\.、．]\s*', line) and line[0].isdigit():
                    break
                else:
                    # 答案标记：答：C / 答，C / 答:C / 参考答案：C
                    am = re.search(r'^答[,：:\s]*([A-Z]+|正确|错误)|^【答案】\s*([A-Z]+|正确|错误)|^答案[,：:]\s*([A-Z]+|正确|错误)', line)
                    if am:
                        g = next((x for x in am.groups() if x), "")
                        ans = g.strip()
                    # 也匹配行中的 "答：C"
                    am2 = re.search(r'答[,：:]\s*([A-Z]+|正确|错误)', line)
                    if am2 and not ans:
                        ans = am2.group(1).strip()
                    i += 1
            qtype = "single"
            if ans in ("正确","错误"):
                qtype = "judge"
            elif len(ans) > 1:
                qtype = "multi"
            # 判断题：选项是"正确/错误"两个
            if len(opts) == 2 and (("正确" in opts[0] and "错误" in opts[1]) or ("正确" in opts[1] and "错误" in opts[0])):
                qtype = "judge"
                if not ans:
                    ans = "正确" if "正确" in opts[0] else "错误"
            if stem:
                new_q(subject, qtype, norm(stem), opts, ans, exp, source_base)
            continue
        i += 1

# =================================================================
# 解析器 3：docx（题+答案同文件）
# =================================================================
def parse_docx(path, subject, source_base):
    import docx
    d = docx.Document(path)
    paras = [p.text.strip() for p in d.paragraphs]
    i = 0; n = len(paras)
    cur_type = "single"
    while i < n:
        t = paras[i]
        # 题型标题
        if re.match(r'^(单选|多项|不定项|判断)', t):
            cur_type = "single" if "单选" in t else ("multi" if "多选" in t or "不定" in t else "judge")
            i += 1; continue
        m = re.match(r'^(\d{1,3})[、\.．]\s*(.+)$', t)
        if m and not re.match(r'^[A-F][、\.．]', t):
            num = int(m.group(1)); stem = m.group(2)
            opts = []; ans = ""; exp = ""
            i += 1
            while i < n:
                tt = paras[i]
                om = re.match(r'^([A-F])[、\.．]\s*(.+)$', tt)
                if om:
                    opts.append(f"{om.group(1)}. {norm(om.group(2))}")
                    i += 1
                elif re.search(r'【答案】|^答案', tt):
                    am = re.search(r'【答案】\s*([A-Z]+)|答案[:：]?\s*([A-Z]+)', tt)
                    if am:
                        ans = (am.group(1) or am.group(2) or "").strip()
                    # 可能有解析
                    rest = re.sub(r'^.*?(【答案】|答案[:：]?)\s*[A-Z]+\s*', '', tt).strip()
                    if rest: exp = rest[:200]
                    i += 1
                elif re.match(r'^(\d{1,3})[、\.．]\s*', tt) and tt[0].isdigit():
                    break
                else:
                    i += 1
            qtype = cur_type
            if len(ans) > 1: qtype = "multi"
            if qtype == "single" and len(opts)==2 and re.search(r'正确|错误', stem):
                qtype = "judge"
            if stem:
                new_q(subject, qtype, norm(stem), opts, ans, exp, source_base)
            continue
        i += 1

# =================================================================
# 主流程
# =================================================================
def run():
    # 中公刷题班：题目+答案成对
    zhonggong_subjects = ["数据结构与算法","操作系统","数据库系统","计算机网络","计算机组成与体系结构","信息新技术"]
    for subj in zhonggong_subjects:
        d = os.path.join(ROOT, subj)
        q = os.path.join(d, f"中公刷题班-{subj}.pdf")
        a = os.path.join(d, f"中公刷题班-{subj}-答案.pdf")
        if os.path.exists(q) and os.path.exists(a):
            parse_zhonggong(q, a, subj, f"中公刷题班-{subj}")
            print(f"[中公] {subj}: 已解析")
    # 师说模拟题库
    for subj in zhonggong_subjects:
        d = os.path.join(ROOT, subj)
        for f in sorted(os.listdir(d)):
            if f.startswith("师说-") and f.endswith(".pdf") and "答案" not in f:
                parse_shishuo(os.path.join(d,f), subj, f)
    # 行测：中公刷题班
    xc_d = os.path.join(ROOT, "行测")
    for name in ["判断推理","数量关系","言语理解","资料分析"]:
        q = os.path.join(xc_d, f"中公刷题班-{name}.pdf")
        a = os.path.join(xc_d, f"中公刷题班-{name}-答案.pdf")
        if os.path.exists(q) and os.path.exists(a):
            parse_zhonggong(q, a, "行测", f"中公刷题班-{name}")
    # 师说行测
    for f in sorted(os.listdir(xc_d)):
        if f.startswith("师说-") and f.endswith(".pdf"):
            parse_shishuo(os.path.join(xc_d,f), "行测", f)
    # docx
    for f, subj in [
        ("2023电网计算机题库与答案.docx", "综合题库"),
        ("中公一批习题集-计算机类-学生版.docx", "综合题库"),
    ]:
        p = os.path.join(ROOT, "综合题库", f)
        if os.path.exists(p):
            parse_docx(p, subj, f)

    # 输出
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, "questions_text.json")
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(questions, fp, ensure_ascii=False, indent=1)
    print(f"\n共抽取 {len(questions)} 题 -> {out}")
    # 统计
    from collections import Counter
    c = Counter(q["subject"] for q in questions)
    t = Counter(q["type"] for q in questions)
    print("按板块:", dict(c))
    print("按题型:", dict(t))

if __name__ == "__main__":
    run()
