# -*- coding: utf-8 -*-
"""一键：清洗 + 合并文字层/OCR 题目 -> 生成 questions.json，并把数据内嵌进 index.html（单文件应用）"""
import subprocess, sys, json, os, re

PY = r"C:\Users\陈慧\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
APP = r"C:\Users\陈慧\WorkBuddy\2026-10-03-19-22-27\wangdian_app"
DATA = os.path.join(APP, "data")
TEMPLATE = os.path.join(APP, "index_template.html")
OUT_HTML = os.path.join(APP, "index.html")

# 1. 清洗合并
subprocess.run([PY, os.path.join(APP, "clean.py")], check=True)

# 2. 生成 questions.json / questions.js
qjson = os.path.join(DATA, "questions.json")
d = json.load(open(qjson, encoding="utf-8"))
with open(os.path.join(DATA, "questions.js"), "w", encoding="utf-8") as f:
    f.write("window.__QUESTIONS__ = ")
    json.dump(d, f, ensure_ascii=False)
    f.write(";")

# 3. 内嵌数据到 index.html（单文件，任何环境都能直接打开）
tpl = open(TEMPLATE, encoding="utf-8").read()
inline = "<script>window.__QUESTIONS__ = " + json.dumps(d, ensure_ascii=False) + ";</script>"
marker = '<script src="questions.js"></script>'
if marker in tpl:
    html = tpl.replace(marker, inline)
else:
    # 已经内嵌过：替换掉旧的内联数据块
    html = re.sub(
        r'<script>window\.__QUESTIONS__ = \[[\s\S]*?\];</script>',
        lambda m: inline,
        tpl, count=1)
    if html == tpl:
        raise SystemExit("未找到数据注入点，请检查模板")
with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

size = os.path.getsize(OUT_HTML) / 1024 / 1024
print(f"已生成 index.html（单文件版），共 {len(d)} 题，{size:.2f} MB")
