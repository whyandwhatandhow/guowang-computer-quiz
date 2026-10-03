# -*- coding: utf-8 -*-
"""生成 README 用截图：注入种子数据 + 自动导航，用 Edge headless 截图"""
import os, subprocess, copy

BASE = r"C:\Users\陈慧\WorkBuddy\2026-10-03-19-22-27"
SRC = os.path.join(BASE, "wangdian_app", "index.html")
OUT = os.path.join(BASE, "repo", "guowang-computer-quiz", "screenshots")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

SEED = """
(function(){
  // 造一些真实的做题记录让页面有数据
  const rec = {};
  let i = 0;
  for(const q of QS){
    if(!q.answer) continue;
    if(i >= 140) break;
    const wrong = (i % 4 === 0);
    rec[q.id] = {status: wrong ? "wrong" : "right", sel: wrong ? "B" : q.answer, fav: (i % 9 === 0)};
    i++;
  }
  localStorage.setItem("wd_records", JSON.stringify(rec));
})();
"""

VARIANTS = {
    # 首页：带统计数据
    "home": SEED + "\nrenderHome();",
    # 筛选弹层
    "filter": SEED + '\ncurSubject="操作系统"; openFilter("操作系统");',
    # 答题页：答对（绿色 + 上一题/下一题按钮）
    "quiz-right": SEED + """
curSubject="操作系统"; curType="single"; startQuiz();
const rec0 = getRecords();
let q0 = quizList[quizPos];
rec0[q0.id] = {status:"right", sel:q0.answer};
setRecords(rec0);
renderQuiz();
""",
    # 答题页：答错（红色 + 解析）
    "quiz-wrong": SEED + """
curSubject="计算机网络"; curType="single"; startQuiz();
let idx = quizList.findIndex(x=>x.analysis);
if(idx < 0) idx = 0;
quizPos = idx;
const q1 = quizList[quizPos];
const rec1 = getRecords();
const keys = q1.options.map(o=>o.charAt(0));
const wrongKey = keys.find(k=>k!==q1.answer) || "B";
rec1[q1.id] = {status:"wrong", sel:wrongKey};
setRecords(rec1);
renderQuiz();
""",
    # 错题本
    "wrongbook": SEED + '\nopenList("wrong");',
}

def shoot(name, script):
    html = open(SRC, encoding="utf-8").read()
    inject = "<script>" + script + "</script>\n</body>"
    assert "</body>" in html
    tmp = os.path.join(BASE, "wangdian_app", "_shot_%s.html" % name)
    open(tmp, "w", encoding="utf-8").write(html.replace("</body>", inject, 1))
    out_png = os.path.join(OUT, name + ".png")
    url = "file:///" + tmp.replace("\\", "/")
    cmd = [EDGE, "--headless", "--disable-gpu", "--force-device-scale-factor=2",
           "--window-size=412,915", "--hide-scrollbars",
           "--screenshot=" + out_png, url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    ok = os.path.exists(out_png)
    print(("OK  " if ok else "FAIL") + " " + name, os.path.getsize(out_png) if ok else r.stderr[-200:])
    os.remove(tmp)

for name, script in VARIANTS.items():
    shoot(name, script)
print("全部截图完成")
