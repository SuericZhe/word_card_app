#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime

# 确保可以导入同级目录模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from standalone_text_to_pic import TextToPicture

def main():
    """测试作文生成图片功能"""
    # 创建一个更长的10句话英文作文，句子长短不一
    essay = """Animals are our friends on this planet. Dogs are loyal companions who love to play and protect us. Cats are independent but still enjoy cuddles and attention. Birds bring beautiful songs to our gardens and parks. Fish swim gracefully in rivers, lakes and oceans all around the world. Elephants are the largest land animals and have amazing memories. Monkeys are playful and very intelligent creatures. Rabbits hop quickly and have soft fur that feels nice to touch. Bears hibernate during cold winter months. All animals deserve our respect and protection."""
    
    # 设置标题
    title = "Our Animal Friends"
    
    # 创建输出目录
    output_dir = os.path.join(current_dir, "test_output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置输出文件路径
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(output_dir, f"test_essay_{timestamp}.png")
    
    print("===== 测试作文生成图片 =====")
    print(f"作文内容：\n{essay}")
    print(f"标题：{title}")
    print(f"输出路径：{output_path}")
    
    # 创建TextToPicture实例并生成图片
    text_to_pic = TextToPicture()
    result_path = text_to_pic.create_image(
        text=essay,
        output_path=output_path,
        title=title
    )
    
    if result_path:
        print(f"\n✅ 成功生成图片: {result_path}")
        print("请检查生成的图片，确认：")
        print("1. 每句话是否都换行")
        print("2. 行间距是否明显区分每个句子")
    else:
        print("\n❌ 图片生成失败")

if __name__ == "__main__":
    main() 