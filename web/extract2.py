# -*- coding: utf-8 -*-
"""
完整抽取脚本 v2：覆盖所有有答案的高质量题源。
输出统一 questions.json
"""
import os, re, json, sys
import pymupdf

ROOT = r"D:\BaiduNetdiskDownload\电网试卷\2-练习题"
OUT = r"C:\Users\陈慧\WorkBuddy\2026-10-03-19-22-27\wangdian_app\data"

questions = []
_qid = [0]

def new_q(subject, qtype, stem, options, answer, analysis="", source=""):
    _qid[0] += 1
    questions.append({
        "id": _qid[0], "subject": subject, "type": qtype,
        "stem": stem, "options": options, "answer": answer,
        "analysis": analysis, "source": source,
    })

def pdf_text(path):
    d = pymupdf.open(path)
    txt = "\n".join((p.get_text() or "") for p in d)
    d.close()
    return txt

def norm(s):
    return re.sub(r'\s+', ' ', s).strip()

def lines_of(txt):
    return [l.strip() for l in txt.split('\n')]

# ------------------------------------------------------------------
# 通用：从答案文本提取 {题号: (答案, 解析)}
# 支持 "1.【答案】D。解析：xxx" 和 "1、答案：D"
# ------------------------------------------------------------------
def build_ans_map(ans_text):
    m = {}
    # 主格式：数字.【答案】X。解析：...
    for mm in re.finditer(r'(\d{1,3})\s*[\.、．]?\s*【答案】\s*([A-Z]+|正确|错误)\s*[。．]?\s*解析[:：]?\s*([^\d]*?)(?=\s*\d{1,3}\s*[\.、．]?\s*【答案】|\Z)', ans_text, re.S):
        num, a, e = int(mm.group(1)), mm.group(2).strip(), norm(mm.group(3))
        m[num] = (a, e[:200])
    if not m:
        # 备选：数字、答案：X
        for mm in re.finditer(r'(\d{1,3})\s*[、．]\s*(?:【答案】|答案[:：])?\s*([A-Z]+|正确|错误)', ans_text):
            num, a = int(mm.group(1)), mm.group(2).strip()
            if num not in m:
                m[num] = (a, "")
    return m

# ------------------------------------------------------------------
# 通用：从题目文本解析题目（题号 + 题干 + 选项），返回题目列表
# 参数 is_judge_ab: 判断题答案 A/B 表示 正确/错误
# ------------------------------------------------------------------
def parse_questions(qtext, ans_map, subject, source, judge_ab=False):
    lines = lines_of(qtext)
    i, n = 0, len(lines)
    result = []
    while i < n:
        l = lines[i]
        m = re.match(r'^(\d{1,3})[\.、．]\s*(.+)$', l)
        if m and not re.match(r'^[A-F][\.、．]', l):
            num = int(m.group(1)); stem = m.group(2)
            opts = []
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
                    # 判断是否答案标记（避免吞入答案行）
                    if re.match(r'^(答|【答案】|答案)', line):
                        i += 1
                        continue
                    stem += " " + norm(line)
                    i += 1
            ans, exp = ans_map.get(num, ("", ""))
            # 清理判断题标记
            is_judge = "【判断题】" in stem or "（多选）" not in stem and False
            if "【判断题】" in stem:
                is_judge = True
                stem = stem.replace("【判断题】", "")
            stem = norm(stem)
            # 题型判定
            if is_judge:
                qtype = "judge"
                if judge_ab:
                    ans = "正确" if ans == "A" else ("错误" if ans == "B" else ans)
                opts = ["A. 正确", "B. 错误"]
            elif len(ans) > 1:
                qtype = "multi"
            else:
                qtype = "single"
            result.append((subject, qtype, stem, opts, ans, exp, source))
            continue
        i += 1
    return result

# ------------------------------------------------------------------
# 解析器 A：中公刷题班（题目+答案分离，题号连续，判断题答案A/B）
# ------------------------------------------------------------------
def parse_zhonggong(qpath, apath, subject, source_base):
    qt = pdf_text(qpath); at = pdf_text(apath)
    ans_map = build_ans_map(at)
    for r in parse_questions(qt, ans_map, subject, source_base, judge_ab=True):
        new_q(*r)

# ------------------------------------------------------------------
# 解析器 B：师说（答案印题干 "答：C"/"答，C"）
# ------------------------------------------------------------------
def parse_shishuo(path, subject, source_base):
    txt = pdf_text(path); lines = lines_of(txt)
    i, n = 0, len(lines)
    while i < n:
        l = lines[i]
        m = re.match(r'^(\d{1,3})[\.、．]\s*(.+)$', l)
        if m and not re.match(r'^[A-F][\.、．]', l):
            num = int(m.group(1)); stem = m.group(2)
            opts = []; ans = ""
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
                    am = re.search(r'答[,：:]\s*([A-Z]+|正确|错误)', line)
                    if am: ans = am.group(1).strip()
                    i += 1
            qtype = "single"
            if ans in ("正确","错误"): qtype = "judge"
            elif len(ans) > 1: qtype = "multi"
            if len(opts)==2 and (("正确" in opts[0] and "错误" in opts[1]) or ("正确" in opts[1] and "错误" in opts[0])):
                qtype = "judge"
            if stem:
                new_q(subject, qtype, norm(stem), opts, ans, "", source_base)
            continue
        i += 1

# ------------------------------------------------------------------
# 解析器 C：docx（题+答案同文件）
# ------------------------------------------------------------------
def parse_docx(path, subject, source_base):
    import docx
    d = docx.Document(path)
    paras = [p.text.strip() for p in d.paragraphs]
    i, n = 0, len(paras)
    cur_type = "single"
    while i < n:
        t = paras[i]
        if re.match(r'^(单选|多项|不定项|判断)', t):
            cur_type = "single" if "单选" in t else ("multi" if ("多选" in t or "不定" in t) else "judge")
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
                    opts.append(f"{om.group(1)}. {norm(om.group(2))}"); i += 1
                elif re.search(r'【答案】|^答案', tt):
                    am = re.search(r'【答案】\s*([A-Z]+|正确|错误)|答案[:：]?\s*([A-Z]+|正确|错误)', tt)
                    if am: ans = (am.group(1) or am.group(2) or "").strip()
                    rest = re.sub(r'^.*?(【答案】|答案[:：]?)\s*[A-Z]+\s*', '', tt).strip()
                    if rest: exp = rest[:200]
                    i += 1
                elif re.match(r'^(\d{1,3})[、\.．]\s*', tt) and tt[0].isdigit():
                    break
                else:
                    i += 1
            qtype = cur_type
            if len(ans) > 1: qtype = "multi"
            if ans in ("正确","错误"): qtype = "judge"
            if qtype=="single" and len(opts)==2 and re.search(r'正确|错误', stem): qtype="judge"
            if stem:
                new_q(subject, qtype, norm(stem), opts, ans, exp, source_base)
            continue
        i += 1

# ------------------------------------------------------------------
# 解析器 D：中公-计算机类习题（按科目分章 + 答案分章）
# ------------------------------------------------------------------
def parse_zhonggong_chaptered(qpath, apath, source_base):
    """中公-计算机类习题.pdf 与 习题答案.pdf，按科目分章"""
    qt = pdf_text(qpath); at = pdf_text(apath)
    # 科目关键词
    subjects_kw = ["数据结构与算法","数据库系统","计算机网络","操作系统","计算机组成与体系结构","信息新技术"]
    # 按科目切分答案
    ans_by_subject = {}
    q_by_subject = {}
    # 找每个科目在答案/题目文本中的位置
    def split_by_subject(txt):
        positions = []
        for s in subjects_kw:
            p = txt.find(s)
            if p >= 0: positions.append((p, s))
        positions.sort()
        # 只保留作为"章标题"出现的位置（后面跟"一、单选题"或换行）
        res = {}
        for idx,(p,s) in enumerate(positions):
            end = positions[idx+1][0] if idx+1 < len(positions) else len(txt)
            res[s] = txt[p:end]
        return res
    q_ch = split_by_subject(qt)
    a_ch = split_by_subject(at)
    for s in subjects_kw:
        if s in q_ch and s in a_ch:
            ans_map = build_ans_map(a_ch[s])
            for r in parse_questions(q_ch[s], ans_map, s, source_base, judge_ab=True):
                new_q(*r)

# ------------------------------------------------------------------
# 解析器 E：VIVI 配套习题 + 答案.xls（按考点）
# ------------------------------------------------------------------
def parse_vivi(qpath, apath, source_base):
    """VIVI计算机配套习题.pdf（题目，按考点）+ 计算机类培训配套习题-答案.xls"""
    # 答案xls：考点1：1.ABD 2.A 3.A...
    import xlrd
    wb = xlrd.open_workbook(apath)
    # 答案映射 {科目: {考点: {题号: 答案}}}
    ans_db = {}
    for sh in wb.sheets():
        # sheet名如"数据库""组成原理""数据结构""操作系统"
        cur_kw = ""
        for r in range(sh.nrows):
            cell = str(sh.cell_value(r, 0)).strip()
            mkw = re.match(r'^考点(\d+)', cell)
            if mkw:
                cur_kw = mkw.group(0)
                # 解析 "考点1：1.ABD 2.A 3.A"
                body = cell.split('：',1)[-1] if '：' in cell else cell.split(':',1)[-1]
                ans_db.setdefault(sh.name, {})[cur_kw] = {}
                for mm in re.finditer(r'(\d+)\.([A-Z]+)', body):
                    ans_db[sh.name][cur_kw][int(mm.group(1))] = mm.group(2)
    # 题目PDF：扫描图，无文字层 → 暂无法解析，留待OCR
    print(f"  [VIVI] 答案表已解析(sheets={len(wb.sheets())})，题目为扫描图需OCR")

# =================================================================
# 主流程
# =================================================================
def run():
    # 1. 中公刷题班（6科目 + 行测4类）
    zhonggong_subjects = ["数据结构与算法","操作系统","数据库系统","计算机网络","计算机组成与体系结构","信息新技术"]
    for subj in zhonggong_subjects:
        d = os.path.join(ROOT, subj)
        q = os.path.join(d, f"中公刷题班-{subj}.pdf")
        a = os.path.join(d, f"中公刷题班-{subj}-答案.pdf")
        if os.path.exists(q) and os.path.exists(a):
            parse_zhonggong(q, a, subj, f"中公刷题班-{subj}")
    xc_d = os.path.join(ROOT, "行测")
    for name in ["判断推理","数量关系","言语理解","资料分析"]:
        q = os.path.join(xc_d, f"中公刷题班-{name}.pdf")
        a = os.path.join(xc_d, f"中公刷题班-{name}-答案.pdf")
        if os.path.exists(q) and os.path.exists(a):
            parse_zhonggong(q, a, "行测", f"中公刷题班-{name}")

    # 2. 师说模拟题库（6科目）
    for subj in zhonggong_subjects:
        d = os.path.join(ROOT, subj)
        for f in sorted(os.listdir(d)):
            if f.startswith("师说-") and f.endswith(".pdf") and "答案" not in f and "模拟题库" in f:
                parse_shishuo(os.path.join(d,f), subj, f)

    # 3. 2023 docx
    p = os.path.join(ROOT, "综合题库", "2023电网计算机题库与答案.docx")
    if os.path.exists(p):
        parse_docx(p, "综合题库", "2023电网计算机题库与答案.docx")

    # 4. 计算机类试题 + 答案（多选标记）
    q = os.path.join(ROOT, "综合题库", "计算机类试题.pdf")
    a = os.path.join(ROOT, "综合题库", "计算机类试题-答案.pdf")
    if os.path.exists(q) and os.path.exists(a):
        # 这个题源"（多选）"标记在题干，单独处理
        qt = pdf_text(q); at = pdf_text(a)
        ans_map = build_ans_map(at)
        # 分"试题一""试题二"多套，但题号会重置，直接用全局序号匹配会错。
        # 这里简化为按顺序提取题目+按顺序取答案
        # 逐题提取
        lines = lines_of(qt)
        i, n = 0, len(lines); seq = 0; qlist = []
        while i < n:
            l = lines[i]
            m = re.match(r'^(\d{1,3})[\.、．]\s*(.+)$', l)
            if m and not re.match(r'^[A-F][\.、．]', l):
                seq += 1
                stem = m.group(2); opts = []; is_multi = False
                i += 1
                while i < n:
                    line = lines[i]
                    if line.strip() == "（多选）" or line.strip() == "（多 选）":
                        is_multi = True; i += 1; continue
                    om = re.match(r'^([A-F])[\.、．]\s*(.+)$', line)
                    if om:
                        opts.append(f"{om.group(1)}. {norm(om.group(2))}"); i += 1
                    elif re.match(r'^(\d{1,3})[\.、．]\s*', line) and line[0].isdigit():
                        break
                    elif re.match(r'^(国家电网考试|第一考试网|www\.)', line):
                        i += 1; continue
                    else:
                        stem += " " + norm(line); i += 1
                qlist.append((seq, norm(stem), opts, is_multi))
                continue
            i += 1
        # 答案按顺序匹配
        ans_list = []
        for mm in re.finditer(r'(\d{1,3})[\.、．]?\s*【答案】\s*([A-Z]+)', at):
            ans_list.append(mm.group(2))
        for idx, (seq, stem, opts, is_multi) in enumerate(qlist):
            ans = ans_list[idx] if idx < len(ans_list) else ""
            qtype = "multi" if (is_multi or len(ans) > 1) else "single"
            new_q("综合题库", qtype, stem, opts, ans, "", "计算机类试题")

    # 5. 中公-计算机类习题（按科目分章）
    q = os.path.join(ROOT, "综合题库", "中公-计算机类习题.pdf")
    a = os.path.join(ROOT, "综合题库", "中公-计算机类习题答案.pdf")
    if os.path.exists(q) and os.path.exists(a):
        parse_zhonggong_chaptered(q, a, "中公-计算机类习题")

    # 6. 中公一批习题集 docx 学生版 + 答案 docx
    qd = os.path.join(ROOT, "综合题库", "中公一批习题集-计算机类-学生版.docx")
    ad = os.path.join(ROOT, "综合题库", "中公一批习题集-计算机类-答案.docx")
    if os.path.exists(qd) and os.path.exists(ad):
        # 学生版是题目，答案版是答案，复用中公分离逻辑但基于docx
        import docx
        qdoc = docx.Document(qd); qparas = [p.text.strip() for p in qdoc.paragraphs]
        adoc = docx.Document(ad); aparas = [p.text.strip() for p in adoc.paragraphs]
        # 答案：按科目分节，1.【答案】B。解析：
        ans_text = "\n".join(aparas)
        ans_map = build_ans_map(ans_text)
        # 题目：按"数量关系""资料分析"等子类，题号会重置。简化：全部归"综合题库"或"行测"
        # 这里把行测类题目归入"行测"
        # 逐题解析，判断题型
        i, n = 0, len(qparas); cur_subj = "综合题库"
        while i < n:
            t = qparas[i]
            if re.match(r'^(公共及行业知识|数量关系|言语理解|判断推理|资料分析)', t):
                cur_subj = "行测"
                i += 1; continue
            if re.match(r'^(数据结构|数据库|计算机网络|操作系统|计算机组成|信息新)', t):
                cur_subj = "综合题库"; i += 1; continue
            m = re.match(r'^(\d{1,3})[\.、．]\s*(.+)$', t)
            if m and not re.match(r'^[A-F][\.、．]', t):
                num = int(m.group(1)); stem = m.group(2); opts = []
                i += 1
                while i < n:
                    tt = qparas[i]
                    # 选项可能在同一行 "A.xx B.xx C.xx D.xx"
                    if re.match(r'^[A-F][\.、．]', tt):
                        # 拆分同行多选项
                        parts = re.split(r'\s+(?=[A-F][\.、．])', tt)
                        for pp in parts:
                            om = re.match(r'^([A-F])[\.、．]\s*(.+)$', pp.strip())
                            if om: opts.append(f"{om.group(1)}. {norm(om.group(2))}")
                        i += 1
                    elif re.match(r'^(\d{1,3})[\.、．]\s*', tt) and tt[0].isdigit():
                        break
                    else:
                        i += 1
                ans, exp = ans_map.get(num, ("", ""))
                qtype = "multi" if len(ans)>1 else "single"
                if stem:
                    new_q(cur_subj, qtype, norm(stem), opts, ans, exp, "中公一批习题集")
                continue
            i += 1

    # 7. VIVI 答案表（题目为扫描图，暂只登记）
    parse_vivi(
        os.path.join(ROOT,"综合题库","VIVI计算机配套习题.pdf"),
        os.path.join(ROOT,"综合题库","计算机类培训配套习题-答案.xls"),
        "VIVI配套习题"
    )

    # 输出
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, "questions_text.json")
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(questions, fp, ensure_ascii=False, indent=1)
    from collections import Counter
    print(f"\n共抽取 {len(questions)} 题 -> {out}")
    print("按板块:", dict(Counter(q['subject'] for q in questions)))
    print("按题型:", dict(Counter(q['type'] for q in questions)))
    empty = sum(1 for q in questions if not q['answer'])
    print("空答案:", empty)

if __name__ == "__main__":
    run()
