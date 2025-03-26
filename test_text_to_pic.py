#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试文本转图片功能的简单脚本
"""

from coze.standalone_text_to_pic import TextToPicture

def main():
    """测试TextToPicture功能的主函数"""
    
    print("开始测试文本转图片功能...")
    
    # 创建文本转图片处理器
    processor = TextToPicture()
    
    # 测试文本
    test_text = """
    This is a test of the standalone text to image conversion functionality.
    
    The text should be properly formatted with correct line breaks and spacing.
    This module has been designed to work independently without relying on other components.
    
    Font size should be automatically calculated based on the text length.
    """
    
    # 测试标题
    test_title = "Text to Image Test"
    
    # 生成图片
    output_path = processor.create_image(
        text=test_text, 
        title=test_title,
        output_path="output/test_result.png"
    )
    
    if output_path:
        print(f"✅ 测试成功! 图片已保存至: {output_path}")
    else:
        print("❌ 测试失败!")

if __name__ == "__main__":
    main() 