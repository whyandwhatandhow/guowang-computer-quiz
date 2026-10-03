# -*- coding: utf-8 -*-
"""
OCR 扫描件题目抽取管线
- 全量 OCR 23 个扫描 PDF
- 有答案的（1000题试题+答案）配对解析
- 无答案的抽取题目+选项，答案留空标记
- 断点续跑：每处理完一页就保存，中断后可继续
"""
import os, sys, json, re, time, hashlib

BASE = r"D:\BaiduNetdiskDownload\电网试卷\2-练习题"
OUTDIR = r"C:\Users\陈慧\WorkBuddy\2026-10-03-19-22-27\wangdian_app\data"
CACHE = os.path.join(OUTDIR, "ocr_cache.json")

import pymupdf
from rapidocr_onnxruntime import RapidOCR

# 板块映射（根据文件所在目录）
SUBJECT_MAP = {
    "操作系统": "操作系统",
    "数据库系统": "数据库系统",
    "数据结构与算法": "数据结构与算法",
    "计算机网络": "计算机网络",
    "计算机组成与体系结构": "计算机组成与体系结构",
    "信息新技术": "信息新技术",
    "软件设计与开发": "软件设计与开发",
    "行测": "行测",
    "综合题库": "综合题库",
}

# 扫描 PDF 清单（相对路径, 板块, 是否有配套答案文件）
SCAN_FILES = [
    ("信息新技术/2026题库-信息新技术.pdf", "信息新技术", None),
    ("信息新技术/创享题库-信息新技术.pdf", "信息新技术", None),
    ("操作系统/2026题库-操作系统.pdf", "操作系统", None),
    ("操作系统/创享题库-操作系统.pdf", "操作系统", None),
    ("操作系统/题库-操作系统.pdf", "操作系统", None),
    ("数据库系统/2026题库-数据库.pdf", "数据库系统", None),
    ("数据库系统/创享题库-数据库系统.pdf", "数据库系统", None),
    ("数据库系统/题库-数据库系统.pdf", "数据库系统", None),
    ("数据结构与算法/2026题库-数据结构.pdf", "数据结构与算法", None),
    ("数据结构与算法/创享题库-数据结构与算法.pdf", "数据结构与算法", None),
    ("计算机网络/2026题库-计算机网络.pdf", "计算机网络", None),
    ("计算机网络/创享题库-计算机网络.pdf", "计算机网络", None),
    ("计算机网络/题库-计算机网络.pdf", "计算机网络", None),
    ("计算机组成与体系结构/2026题库-计算机组成原理.pdf", "计算机组成与体系结构", None),
    ("计算机组成与体系结构/创享题库-计算机组成原理.pdf", "计算机组成与体系结构", None),
    ("计算机组成与体系结构/题库-计算机组成原理.pdf", "计算机组成与体系结构", None),
    ("软件设计与开发/2026题库-软件工程-答案.pdf", "软件设计与开发", None),
    ("综合题库/创享题库-新增题库.pdf", "综合题库", None),
    ("综合题库/衡真题库-信息新技术+数据结构.pdf", "综合题库", None),
    ("综合题库/衡真题库-操作系统+计算机组成原理.pdf", "综合题库", None),
    ("综合题库/衡真题库-计算机网络+数据库.pdf", "综合题库", None),
    ("综合题库/计算机类培训配套习题.pdf", "综合题库", None),
    ("行测/创享题库-行测.pdf", "行测", None),
    ("行测/衡真题库-行测数量.pdf", "行测", None),
    ("行测/衡真题库-行测言语.pdf", "行测", None),
    # 1000题：试题+答案配套
    ("综合题库/1000题题本-计算机类-试题.pdf", "综合题库", "综合题库/1000题题本-计算机类-答案.pdf"),
]

ocr = None

def get_ocr():
    global ocr
    if ocr is None:
        ocr = RapidOCR()
    return ocr

def ocr_page(doc, page_idx, dpi=150):
    """对某一页做 OCR，返回文本行列表"""
    pix = doc[page_idx].get_pixmap(dpi=dpi)
    img = pix.tobytes("png")
    result, _ = get_ocr()(img)
    if not result:
        return []
    return [r[1] for r in result]

def norm(s):
    s = s.replace("\u3000", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s

# ---------- 答案文件解析（中公格式：1.【答案】D。解析：...）----------
def parse_answer_text(full_text):
    """从答案文件全文解析 题号 -> (答案, 解析)"""
    ans_map = {}
    # 答案行形如：1.【答案】D。解析：xxxx
    # 可能跨行，先按行处理
    lines = full_text.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^(\d{1,3})\s*[.、．]\s*【答案】\s*([A-F]+|正确|错误)", lines[i])
        if m:
            num = int(m.group(1))
            ans = m.group(2)
            # 解析可能是本行剩余部分 + 后续行
            exp = lines[i][m.end():]
            # 继续收集后续行直到下一个题号
            j = i + 1
            exp_parts = [exp]
            while j < len(lines):
                if re.match(r"^\d{1,3}\s*[.、．]\s*【答案】", lines[j]):
                    break
                exp_parts.append(lines[j])
                j += 1
            ans_map[num] = (ans, norm(" ".join(exp_parts)))
            i = j
        else:
            i += 1
    return ans_map

def classify_type(stem, opts, ans):
    """判定题型"""
    # 判断：选项只有 A/B 且题干含正确/错误，或答案=正确/错误
    if ans in ("正确", "错误"):
        return "judge"
    if len(opts) == 2 and all(o.startswith(x) for x, o in [("A", opts[0]), ("B", opts[1])]):
        if re.search(r"正确|错误|对错|是否|说法", stem):
            return "judge"
    # 多选：答案长度>1 或题干含"多选"
    if "多选" in stem or (ans and len(ans) > 1 and ans not in ("正确", "错误")):
        return "multi"
    return "single"

def parse_questions_from_lines(lines, subject, source, ans_map=None, has_answer_marker=False):
    """
    从 OCR 文本行抽取题目。
    ans_map: 题号->(答案,解析) 的映射（答案分离时）
    has_answer_marker: 答案是否直接印在题目里（如"答案：C"）
    """
    questions = []
    lines = [norm(l) for l in lines if l.strip()]
    i = 0
    n = len(lines)
    while i < n:
        l = lines[i]
        # 题号匹配：支持 "1." "1、" "1．" "1、（单选）" 等
        m = re.match(r"^(\d{1,3})\s*[.、．]\s*(.*)$", l)
        if m and not re.match(r"^[A-F][.、．\s]", l):
            num = int(m.group(1))
            stem = m.group(2)
            opts = []
            inline_ans = ""
            i += 1
            # 收集选项和题干续行
            while i < n:
                line = lines[i]
                om = re.match(r"^([A-F])[.、．]\s*(.+)$", line)
                if om and len(line) < 200:  # 选项行一般较短
                    opts.append(f"{om.group(1)}. {norm(om.group(2))}")
                    i += 1
                    continue
                # 检查是否下一题
                if re.match(r"^(\d{1,3})\s*[.、．]\s*", line) and line[0].isdigit():
                    # 但需排除题干续行以数字开头的情况（少见，保守处理：如果上一行已收集到选项则视为新题）
                    if opts or len(stem) > 15:
                        break
                # 检查行内答案标记
                am = re.search(r"【答案】\s*([A-F]+|正确|错误)|答案[:：]\s*([A-F]+|正确|错误)|答[:：]\s*([A-F]+|正确|错误)", line)
                if am:
                    inline_ans = am.group(1) or am.group(2) or am.group(3)
                # 题干续行（选项还没出现时，追加到题干）
                if not opts and not re.match(r"^[A-F][.、．]", line):
                    stem += " " + line
                i += 1
            # 组装答案
            ans = ""
            exp = ""
            if ans_map and num in ans_map:
                ans, exp = ans_map[num]
            elif inline_ans:
                ans = inline_ans
            qtype = classify_type(stem, opts, ans)
            if stem and opts:  # 有题干且有选项才算有效题目
                questions.append({
                    "num": num,
                    "subject": subject,
                    "type": qtype,
                    "stem": norm(stem),
                    "options": opts,
                    "answer": ans,
                    "analysis": exp,
                    "source": source,
                })
            continue
        i += 1
    return questions

def _process_one(rel, subject, ans_rel, cache, all_questions):
    pdf_path = os.path.join(BASE, rel)
    if not os.path.exists(pdf_path):
        print(f"[跳过] 不存在: {rel}", flush=True)
        return
    cache_key = rel
    if cache_key in cache and cache[cache_key].get("done"):
        print(f"[缓存] {rel} 已处理，跳过", flush=True)
        all_questions.extend(cache[cache_key].get("questions", []))
        return

    print(f"\n[OCR] {rel} ({subject})", flush=True)
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    all_lines = []
    for p in range(total_pages):
        try:
            lines = ocr_page(doc, p)
            all_lines.extend(lines)
            all_lines.append("")  # 页分隔
            if (p + 1) % 10 == 0:
                print(f"  {p+1}/{total_pages} 页完成", flush=True)
        except Exception as e:
            print(f"  [警告] 第{p+1}页 OCR 失败: {e}", flush=True)
    doc.close()

    # 解析答案（如有配套答案文件）
    ans_map = None
    if ans_rel:
        ans_path = os.path.join(BASE, ans_rel)
        if os.path.exists(ans_path):
            ans_doc = pymupdf.open(ans_path)
            ans_lines = []
            for p in range(len(ans_doc)):
                try:
                    ans_lines.extend(ocr_page(ans_doc, p))
                except Exception as e:
                    print(f"  [警告] 答案第{p+1}页 OCR 失败: {e}", flush=True)
            ans_doc.close()
            ans_map = parse_answer_text("\n".join(ans_lines))
            print(f"  解析到 {len(ans_map)} 条答案", flush=True)
        else:
            print(f"  [警告] 答案文件不存在: {ans_rel}", flush=True)

    # 抽取题目
    qs = parse_questions_from_lines(all_lines, subject, os.path.basename(rel), ans_map)
    print(f"  抽取题目: {len(qs)} 条", flush=True)

    # 保存到缓存
    cache[cache_key] = {"done": True, "questions": qs}
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    all_questions.extend(qs)

def main():
    # 支持命令行参数：只处理包含某关键词的文件（如 "1000"）
    filter_kw = sys.argv[1] if len(sys.argv) > 1 else None
    files = SCAN_FILES
    if filter_kw:
        files = [f for f in SCAN_FILES if filter_kw in f[0]]
        print(f"[过滤] 只处理含 '{filter_kw}' 的文件，共 {len(files)} 个")

    # 读取缓存
    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE, "r", encoding="utf-8") as f:
            cache = json.load(f)

    all_questions = []
    for rel, subject, ans_rel in files:
        try:
            _process_one(rel, subject, ans_rel, cache, all_questions)
        except Exception as e:
            print(f"[错误] 处理 {rel} 失败: {e!r}", flush=True)
            import traceback; traceback.print_exc()

    # 输出合并结果
    out_path = os.path.join(OUTDIR, "questions_ocr.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=1)
    print(f"\n===== OCR 抽取完成，共 {len(all_questions)} 题 =====")
    print(f"已保存: {out_path}")

if __name__ == "__main__":
    main()
