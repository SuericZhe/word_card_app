#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
将英文文本转换为图片的模块
生成一张1024*576的白底黑字图片，适合短小的英文文本或段落
"""

import os
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap


class TextToPicture:
    """
    将英文文本转换为图片
    生成白底黑字的美观排版图片，优化了对英文文本的处理
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
            "C:/Windows/Fonts/calibrib.ttf",      # Calibri Bold
            "C:/Windows/Fonts/georgia.ttf",       # Georgia (衬线优雅)
            "C:/Windows/Fonts/georgiab.ttf",      # Georgia Bold
            "C:/Windows/Fonts/arial.ttf",         # Arial (无衬线)
            "C:/Windows/Fonts/arialbd.ttf",       # Arial Bold
            "C:/Windows/Fonts/segoeui.ttf",       # Segoe UI (现代UI)
            "C:/Windows/Fonts/segoeuib.ttf",      # Segoe UI Bold
            "C:/Windows/Fonts/times.ttf",         # Times New Roman (传统衬线)
            "C:/Windows/Fonts/timesbd.ttf",       # Times New Roman Bold
            "C:/Windows/Fonts/verdana.ttf",       # Verdana (清晰易读)
            "C:/Windows/Fonts/verdanab.ttf",      # Verdana Bold
            # Mac 英文字体
            "/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Georgia.ttf", 
            "/Library/Fonts/Times New Roman.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            # 项目内字体（如果存在）
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts/OpenSans-Regular.ttf"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts/OpenSans-Bold.ttf"),
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
            
        # 统计文本行数和单词数
        lines = text.split('\n')
        line_count = len(lines)
        word_count = sum(len(line.split()) for line in lines)
        
        # 计算平均每行单词数
        avg_words_per_line = word_count / max(1, line_count)
        
        # 估算文本可能的行数 (考虑单词长度和文本折行)
        # 假设每个单词平均6个字符，每个字符平均8像素宽
        avg_chars_per_word = 6
        avg_pixel_per_char = 8  # 大字体时可能更大
        
        # 计算预估总行数
        estimated_total_lines = 0
        for line in lines:
            chars_in_line = len(line)
            line_pixel_width = chars_in_line * avg_pixel_per_char
            line_rows = max(1, line_pixel_width / (self.width - 2 * self.padding))
            estimated_total_lines += line_rows
            
        # 如果有标题，再加上标题可能占用的行数
        if title:
            title_chars = len(title)
            title_pixel_width = title_chars * avg_pixel_per_char * 1.5  # 标题字符通常更大
            title_rows = max(1, title_pixel_width / (self.width - 2 * self.padding))
            estimated_total_lines += title_rows + 0.5  # 标题上下间距
        
        # 根据总行数和图片高度计算字体大小    
        available_height = self.height - 2 * self.padding
        
        # 对于英文，我们使用较大的基础字体大小，因为英文通常比中文需要更大的字体才清晰
        # 调整系数以获得更大的字体
        base_font_size = int(available_height / (max(estimated_total_lines, 3) * self.line_spacing))
        
        # 文字较少时，使用更大的字体
        if word_count < 50:
            base_font_size = int(base_font_size * 1.3)
        elif word_count < 100:
            base_font_size = int(base_font_size * 1.2)
            
        # 处理极端情况
        if base_font_size < 24:
            # 内容太多，使用最小可读字体 (英文较大)
            return 24
        elif base_font_size > 72:
            # 内容太少，限制最大字体大小
            return 72
        else:
            # 对于绝大多数情况，取较大的偶数
            return 2 * ((base_font_size + 1) // 2)
            
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
                
                # 标题底部装饰线（可选）
                # draw.line([(self.width//4, current_y + title_height - 5), 
                #            (self.width*3//4, current_y + title_height - 5)], 
                #            fill=(0, 0, 0), width=2)
                
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
                # 创建results目录（如果不存在）
                results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "essays")
                os.makedirs(results_dir, exist_ok=True)
                
                # 生成文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_title = "essay"
                if title:
                    # 清理标题，只保留字母数字和下划线
                    safe_title = "".join(c if c.isalnum() else "_" for c in title[:30])
                output_path = os.path.join(results_dir, f"{safe_title}_{timestamp}.png")
            
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
    
    @staticmethod
    def find_available_fonts():
        """
        查找系统中可用的字体
        
        Returns:
            可用字体的列表
        """
        common_font_dirs = [
            # Windows 字体目录
            "C:/Windows/Fonts",
            # Mac 字体目录
            "/Library/Fonts",
            "/System/Library/Fonts",
            # Linux 字体目录
            "/usr/share/fonts",
            "/usr/local/share/fonts",
        ]
        
        available_fonts = []
        
        for font_dir in common_font_dirs:
            if os.path.exists(font_dir):
                print(f"检查字体目录: {font_dir}")
                for root, dirs, files in os.walk(font_dir):
                    for file in files:
                        if file.lower().endswith((".ttf", ".ttc", ".otf")):
                            font_path = os.path.join(root, file)
                            available_fonts.append(font_path)
        
        return available_fonts


def main():
    """命令行入口函数"""
    # 打印使用说明
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print("""英文文本转图片工具
        
用法:
    python text_to_pic.py <文本文件路径> [标题] [字体文件路径] [字体大小]
    或者直接输入内容:
    python text_to_pic.py --text "English text content" [标题] [字体文件路径] [字体大小]
    
参数:
    文本文件路径: 包含文本内容的文件
    --text: 直接在命令行提供文本内容
    标题: 可选，文本标题
    字体文件路径: 可选，指定使用的字体文件
    字体大小: 可选，指定字体大小，默认自动计算
    
示例:
    python text_to_pic.py essay.txt "My Dream"
    python text_to_pic.py --text "This is a sample text content." "My Day" "C:/Windows/Fonts/calibri.ttf" 48
        """)
        sys.exit(0)
        
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