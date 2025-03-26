#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
独立的英文文本转图片模块
这个模块可以单独运行，不依赖项目中其他组件
"""

import os
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont


class TextToPicture:
    """
    将英文文本转换为图片
    生成白底黑字的美观排版图片，为英文文本优化
    """
    
    def __init__(self, font_path=None, font_size=None, line_spacing=None):
        """
        初始化文本转图片工具
        
        Args:
            font_path: 字体文件路径，None则使用默认字体
            font_size: 字体大小，None则自动计算最佳大小
            line_spacing: 行间距，None则使用默认行间距
        """
        # 设置默认字体路径 - 优先使用美观的英文字体
        self.default_fonts = [
            # Windows 英文字体优先
            "C:/Windows/Fonts/Calibri.ttf",       # Calibri (优雅现代)
            "C:/Windows/Fonts/georgia.ttf",       # Georgia (衬线优雅) 
            "C:/Windows/Fonts/arial.ttf",         # Arial (无衬线)
            "C:/Windows/Fonts/times.ttf",         # Times New Roman (传统衬线)
            "C:/Windows/Fonts/verdana.ttf",       # Verdana (清晰易读)
            # 后备字体
            "C:/Windows/Fonts/msyh.ttc",          # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",        # 黑体
        ]
        
        self.font_path = font_path
        # 如果没有指定字体，自动寻找可用字体
        if self.font_path is None:
            for font in self.default_fonts:
                if os.path.exists(font):
                    self.font_path = font
                    print(f"使用字体: {font}")
                    break
            
            # 如果所有默认字体都不存在，使用PIL默认字体
            if self.font_path is None:
                print("警告: 未找到任何指定字体，将使用PIL默认字体")
        
        # 图片尺寸和边距
        self.width = 1024
        self.height = 576
        self.padding = 50  # 图片边距
        self.bg_color = (255, 255, 255)  # 白色背景
        self.text_color = (0, 0, 0)      # 黑色文字
        
        # 设置默认参数
        self.font_size = font_size  # 如果为None，将在create_image中动态计算
        self.line_spacing = line_spacing or 1.3  # 英文行间距，通常比中文小
        
    def _calculate_optimal_font_size(self, text, title=None):
        """
        根据英文文本内容和图片尺寸计算最优字体大小
        
        Args:
            text: 要显示的文本
            title: 标题（如果有）
            
        Returns:
            计算出的最优字体大小
        """
        if self.font_size is not None:
            return self.font_size
            
        # 统计文本单词数
        word_count = len(text.split())
        
        # 根据文本长度估算基础字体大小
        if word_count < 30:
            # 短文本使用较大字体 
            base_font_size = 48
        elif word_count < 60:
            # 中等长度文本
            base_font_size = 36  
        elif word_count < 100:
            # 中长文本
            base_font_size = 32
        elif word_count < 200:
            # 长文本
            base_font_size = 28
        else:
            # 非常长的文本
            base_font_size = 24
            
        return base_font_size
            
    def create_image(self, text, output_path=None, title=None):
        """
        根据英文文本创建图片
        
        Args:
            text: 要转换的英文文本内容
            output_path: 输出图片路径，None则自动生成
            title: 可选的标题，将会以更大字号显示
            
        Returns:
            保存的图片路径
        """
        try:
            # 自动计算最优字体大小
            optimal_font_size = self._calculate_optimal_font_size(text, title)
            
            # 创建一个白色背景图片
            image = Image.new('RGB', (self.width, self.height), color=self.bg_color)
            draw = ImageDraw.Draw(image)
            
            # 创建字体对象
            try:
                font = ImageFont.truetype(self.font_path, optimal_font_size)
                title_font = ImageFont.truetype(self.font_path, int(optimal_font_size * 1.4))
            except Exception as e:
                # 如果找不到字体文件，使用默认字体
                print(f"警告: 无法加载指定字体: {e}")
                font = ImageFont.load_default()
                title_font = ImageFont.load_default()
            
            # 计算实际可用的宽度（考虑边距）
            available_width = self.width - (2 * self.padding)
            
            # 获取文本宽度的辅助函数
            def get_text_width(text, font):
                bbox = font.getbbox(text)
                return bbox[2] - bbox[0]
                
            # 英文文本分行处理 - 优化对英文单词的处理
            wrapped_text = []
            
            for paragraph in text.split('\n'):
                if not paragraph.strip():
                    wrapped_text.append('')  # 保留空行
                    continue
                    
                # 按单词分割段落
                words = paragraph.split()
                if not words:
                    continue
                    
                current_line = words[0]
                current_width = get_text_width(current_line, font)
                
                # 从第二个单词开始处理
                for word in words[1:]:
                    # 测试加上下一个单词和空格后的宽度
                    test_line = current_line + " " + word
                    test_width = get_text_width(test_line, font)
                    
                    if test_width <= available_width:
                        # 当前行还能容纳这个单词
                        current_line = test_line
                        current_width = test_width
                    else:
                        # 当前行已满，添加到结果并开始新行
                        wrapped_text.append(current_line)
                        current_line = word
                        current_width = get_text_width(word, font)
                
                # 添加最后一行
                if current_line:
                    wrapped_text.append(current_line)
            
            # 计算行高
            line_height = int(optimal_font_size * self.line_spacing)
            
            # 计算文本总高度
            total_text_height = len(wrapped_text) * line_height
            
            # 如果有标题，添加标题高度
            title_height = 0
            if title:
                title_height = int(optimal_font_size * 1.4 * 1.2)  # 标题字号 * 行间距
                total_text_height += title_height + int(optimal_font_size * 0.5)  # 额外空间分隔标题和正文
            
            # 计算起始Y坐标（垂直居中）
            start_y = max(self.padding, (self.height - total_text_height) // 2)
            current_y = start_y
            
            # 绘制标题（如果有）
            if title:
                # 计算标题的X坐标（水平居中）
                title_bbox = title_font.getbbox(title)
                title_width = title_bbox[2] - title_bbox[0]
                title_x = max(self.padding, (self.width - title_width) // 2)
                
                # 绘制标题
                draw.text((title_x, current_y), title, font=title_font, fill=self.text_color)
                current_y += title_height + int(optimal_font_size * 0.5)  # 标题下方额外空间
            
            # 绘制文本内容
            for line in wrapped_text:
                if not line:  # 处理空行
                    current_y += line_height // 2  # 空行高度减半
                    continue
                    
                # 左对齐文本
                draw.text((self.padding, current_y), line, font=font, fill=self.text_color)
                current_y += line_height
            
            # 确定输出路径
            if not output_path:
                # 创建output目录（如果不存在）
                output_dir = "output"
                os.makedirs(output_dir, exist_ok=True)
                
                # 生成文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_title = "text_image"
                if title:
                    # 清理标题，只保留字母数字和下划线
                    safe_title = "".join(c if c.isalnum() else "_" for c in title[:30])
                output_path = os.path.join(output_dir, f"{safe_title}_{timestamp}.png")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存图片
            image.save(output_path, "PNG")
            print(f"图片已保存: {output_path}")
            print(f"使用字体大小: {optimal_font_size}px")
            
            return output_path
            
        except Exception as e:
            import traceback
            print(f"创建图片时出错: {e}")
            traceback.print_exc()
            return None


def main():
    """命令行入口函数"""
    # 打印使用说明
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print("""英文文本转图片工具
        
用法:
    python standalone_text_to_pic.py <文本文件路径> [标题] [字体文件路径] [字体大小]
    或者直接输入内容:
    python standalone_text_to_pic.py --text "English text content" [标题] [字体文件路径] [字体大小]
    
参数:
    文本文件路径: 包含文本内容的文件
    --text: 直接在命令行提供文本内容
    标题: 可选，文本标题
    字体文件路径: 可选，指定使用的字体文件
    字体大小: 可选，指定字体大小，默认自动计算
    
示例:
    python standalone_text_to_pic.py essay.txt "My Essay"
    python standalone_text_to_pic.py --text "This is a sample text." "Sample" "C:/Windows/Fonts/arial.ttf" 36
        """)
        sys.exit(0)
        
    # 测试函数 - 增加一个简单的测试选项避免命令行参数问题
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("运行内置测试...")
        test_text = "This is a simple test of the text to image conversion functionality. This should generate a nicely formatted image with proper English text layout."
        test_title = "Testing Text to Image"
        processor = TextToPicture()
        output_path = processor.create_image(text=test_text, title=test_title)
        if output_path:
            print("✅ 测试成功，图片生成成功!")
        return
    
    # 解析参数
    font_path = None
    font_size = None
    title = None
    text = None
    
    if sys.argv[1] == "--text":
        # 直接从命令行获取文本
        if len(sys.argv) > 2:
            text = sys.argv[2]
            if len(sys.argv) > 3:
                title = sys.argv[3]
                if len(sys.argv) > 4:
                    font_path = sys.argv[4]
                    if len(sys.argv) > 5:
                        try:
                            font_size = int(sys.argv[5])
                        except ValueError:
                            print(f"警告: 无效的字体大小 '{sys.argv[5]}'，将自动计算最佳大小")
    else:
        # 从文件读取文本
        file_path = sys.argv[1]
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"读取文件时出错: {e}")
            sys.exit(1)
            
        if len(sys.argv) > 2:
            title = sys.argv[2]
            if len(sys.argv) > 3:
                font_path = sys.argv[3]
                if len(sys.argv) > 4:
                    try:
                        font_size = int(sys.argv[4])
                    except ValueError:
                        print(f"警告: 无效的字体大小 '{sys.argv[4]}'，将自动计算最佳大小")
    
    # 创建处理器并执行
    processor = TextToPicture(font_path=font_path, font_size=font_size)
    output_path = processor.create_image(text=text, title=title)
    
    if output_path:
        print("✅ 图片生成成功!")


if __name__ == "__main__":
    main() 