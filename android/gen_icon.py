# -*- coding: utf-8 -*-
"""生成应用图标：蓝色圆角背景 + 白色书本图案，输出各 mipmap 尺寸"""
from PIL import Image, ImageDraw, ImageFont
import os, math

APP = r"C:\Users\陈慧\WorkBuddy\2026-10-03-19-22-27\wangdian_apk\app\src\main\res"

def draw_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 圆角蓝色背景
    r = int(size * 0.22)
    d.rounded_rectangle([0, 0, size-1, size-1], radius=r, fill=(43, 109, 232, 255))
    # 白色书本：两页 + 中间书脊
    w = size
    cx = w / 2
    page_w = w * 0.22
    page_h = w * 0.46
    top = w * 0.22
    # 左页
    d.polygon([(cx, top), (cx - page_w, top), (cx - page_w, top + page_h), (cx, top + page_h)],
              fill=(255, 255, 255, 255))
    # 右页
    d.polygon([(cx, top), (cx + page_w, top), (cx + page_w, top + page_h), (cx, top + page_h)],
              fill=(235, 242, 255, 255))
    # 书脊中线
    d.line([(cx, top), (cx, top + page_h)], fill=(43, 109, 232, 255), width=max(2, size//60))
    # 左页上的"电网"折线（象征电路/电）
    lx = cx - page_w * 0.6
    ry = top + page_h * 0.35
    d.line([(lx - page_w*0.2, ry), (lx, ry), (lx, ry - page_h*0.2), (lx + page_w*0.25, ry - page_h*0.2), (lx + page_w*0.25, ry + page_h*0.1)],
           fill=(43, 109, 232, 255), width=max(2, size//40))
    return img

sizes = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}
for folder, s in sizes.items():
    p = os.path.join(APP, folder)
    os.makedirs(p, exist_ok=True)
    draw_icon(s).save(os.path.join(p, "ic_launcher.png"))
    print(f"{folder}: {s}px 生成完成")

print("图标全部生成")
