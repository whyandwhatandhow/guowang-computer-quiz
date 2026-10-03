# -*- coding: utf-8 -*-
"""
数据清洗：合并文字层题目 + OCR 题目，去重、规范化，输出最终 questions.json
- 有答案的题：正常进刷题（判对错）
- 无答案的题：答案留空，进 App 后标记"暂无答案"
"""
import json, re, os
from collections import Counter

DATA = r"C:\Users\陈慧\WorkBuddy\2026-10-03-19-22-27\wangdian_app\data"
SRC_TEXT = os.path.join(DATA, "questions_text.json")
SRC_OCR = os.path.join(DATA, "questions_ocr.json")
OUT = os.path.join(DATA, "questions.json")

all_q = []

# 1. 文字层题目
if os.path.exists(SRC_TEXT):
    d = json.load(open(SRC_TEXT, encoding="utf-8"))
    print("文字层题目:", len(d))
    all_q.extend(d)

# 2. OCR 题目
if os.path.exists(SRC_OCR):
    d = json.load(open(SRC_OCR, encoding="utf-8"))
    print("OCR 题目:", len(d))
    all_q.extend(d)

print("合并后原始:", len(all_q))

# 3. 规范化答案与题型
valid = []
for q in all_q:
    stem = (q.get("stem") or "").strip()
    opts = q.get("options") or []
    # 必须至少有题干和 2 个选项才是有效选择题
    if not stem or len(opts) < 2:
        continue
    a = (q.get("answer") or "").strip()
    # 答案规范化：只保留 A-F 字母组合 或 正确/错误
    if a and a not in ("正确", "错误"):
        m = re.search(r'[A-F]+', a)
        if m:
            a = m.group(0)
        else:
            a = ""  # 无法识别的答案 → 无答案
    q["answer"] = a

    # 题型规范化
    t = q.get("type", "single")
    if a in ("正确", "错误"):
        q["type"] = "judge"
    elif a and len(a) > 1:
        q["type"] = "multi"
    elif t == "multi" and a and len(a) == 1:
        q["type"] = "single"
    # 无答案时保留原题型，但若无答案且原题型是 judge（错误/正确选项）保持 judge
    if not a and t in ("single", "multi", "judge"):
        q["type"] = t
    valid.append(q)
print("有有效题干选项:", len(valid))

# 4. 去重：按 (题干归一化, 答案) 去重
seen = {}
dedup = []
for q in valid:
    key = (re.sub(r'\s+', '', q["stem"]), q["answer"])
    if key in seen:
        continue
    seen[key] = 1
    dedup.append(q)
print("去重后:", len(dedup))

# 5. 板块规范化
SUBJECTS = ["行测","公共与行业知识","数据结构与算法","操作系统","数据库系统","计算机网络","计算机组成与体系结构","信息新技术","软件设计与开发","综合题库"]
for q in dedup:
    if q["subject"] not in SUBJECTS:
        q["subject"] = "综合题库"

# 6. 重新编号
for i, q in enumerate(dedup):
    q["id"] = i + 1

json.dump(dedup, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n最终:", len(dedup))
print("有答案:", sum(1 for q in dedup if q["answer"]))
print("无答案:", sum(1 for q in dedup if not q["answer"]))
print("按板块:", dict(Counter(q['subject'] for q in dedup)))
print("按题型:", dict(Counter(q['type'] for q in dedup)))
