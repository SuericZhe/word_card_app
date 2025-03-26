import os
import sys
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
from feishu_image_utils import FeishuImageUtils

def add_text_to_image(image_source, text, save_path=None, font_path=None, font_size_percentage=0.06, padding_factor=0.3, bottom_margin_factor=0.08):
    """
    在图片底部添加字幕样式的文字
    
    Args:
        image_source: 图片路径或URL
        text: 要添加的文字
        save_path: 保存路径，默认保存到results文件夹
        font_path: 字体路径，默认使用系统默认字体
        font_size_percentage: 字体大小占图片高度的百分比
        padding_factor: 文字周围的填充系数
        bottom_margin_factor: 底部边距系数，控制文字距底部的距离
        
    Returns:
        保存后的图片路径
    """
    try:
        # 处理图片来源（本地路径或URL）
        if image_source.startswith(('http://', 'https://')):
            # 下载在线图片
            print(f"正在下载图片: {image_source}")
            response = requests.get(image_source, stream=True)
            response.raise_for_status() # 确保请求成功
            img = Image.open(BytesIO(response.content))
        else:
            # 打开本地图片
            if not os.path.exists(image_source):
                raise FileNotFoundError(f"找不到图片文件: {image_source}")
            img = Image.open(image_source)
        
        # 获取图片尺寸
        width, height = img.size
        
        # 计算字体大小
        font_size = int(height * font_size_percentage)
        if font_size < 16:  # 确保最小字体大小
            font_size = 16
        
        # 加载字体
        try:
            if not font_path:
                # 使用默认字体，针对不同系统设置合适的默认字体
                if os.name == 'nt':  # Windows
                    font_path = "arial.ttf"
                else:  # macOS/Linux
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            
            font = ImageFont.truetype(font_path, font_size)
        except OSError:
            # 如果找不到字体文件，使用PIL的默认字体
            print(f"警告: 找不到字体 {font_path}，使用默认字体")
            font = ImageFont.load_default()
        
        # 创建绘图对象
        draw = ImageDraw.Draw(img)
        
        # 计算文本大小（PIL新版本使用textbbox或textsize）
        try:
            # 尝试使用新版API
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            # 回退到旧版API
            text_width, text_height = draw.textsize(text, font=font)
        
        # 定义填充
        padding = font_size * padding_factor
        
        # 计算背景大小
        background_width = text_width + 2 * padding
        background_height = text_height + 2 * padding
        
        # 计算底部距离
        bottom_margin = height * bottom_margin_factor
        
        # 计算粘贴位置（居中，并且离底部有一定距离）
        paste_x = (width - background_width) / 2
        paste_y = height - background_height - bottom_margin
        
        # 创建一个透明背景的图像用于绘制圆角矩形
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # 绘制带有圆角的白色背景（使用多个矩形和圆形组合）
        radius = font_size * 0.3  # 圆角半径
        
        # 绘制圆角矩形
        # 绘制主矩形
        overlay_draw.rectangle(
            (
                int(paste_x + radius), 
                int(paste_y), 
                int(paste_x + background_width - radius), 
                int(paste_y + background_height)
            ), 
            fill=(255, 255, 255, 230)
        )
        
        # 绘制左右两侧的矩形
        overlay_draw.rectangle(
            (
                int(paste_x), 
                int(paste_y + radius), 
                int(paste_x + background_width), 
                int(paste_y + background_height - radius)
            ), 
            fill=(255, 255, 255, 230)
        )
        
        # 绘制四个角的圆形
        overlay_draw.ellipse(
            (
                int(paste_x), 
                int(paste_y), 
                int(paste_x + 2 * radius), 
                int(paste_y + 2 * radius)
            ), 
            fill=(255, 255, 255, 230)
        )
        overlay_draw.ellipse(
            (
                int(paste_x + background_width - 2 * radius), 
                int(paste_y), 
                int(paste_x + background_width), 
                int(paste_y + 2 * radius)
            ), 
            fill=(255, 255, 255, 230)
        )
        overlay_draw.ellipse(
            (
                int(paste_x), 
                int(paste_y + background_height - 2 * radius), 
                int(paste_x + 2 * radius), 
                int(paste_y + background_height)
            ), 
            fill=(255, 255, 255, 230)
        )
        overlay_draw.ellipse(
            (
                int(paste_x + background_width - 2 * radius), 
                int(paste_y + background_height - 2 * radius), 
                int(paste_x + background_width), 
                int(paste_y + background_height)
            ), 
            fill=(255, 255, 255, 230)
        )
        
        # 添加轻微模糊以创建柔和效果
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=1))
        
        # 将圆角矩形叠加到原图上
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        
        # 计算文本位置（居中对齐）
        text_x = paste_x + padding
        text_y = paste_y + padding
        
        # 在新的图像上创建绘图对象
        draw = ImageDraw.Draw(img)
        
        # 绘制文本
        draw.text((int(text_x), int(text_y)), text, font=font, fill=(0, 0, 0, 255))
        
        # 准备保存路径
        if not save_path:
            # 默认保存到results文件夹
            results_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
            os.makedirs(results_path, exist_ok=True)
            
            # 从原始文件名或URL中提取文件名
            if image_source.startswith(('http://', 'https://')):
                file_name = f"captioned_{text.lower().replace(' ', '_')}.png"
            else:
                base_name = os.path.basename(image_source)
                name, ext = os.path.splitext(base_name)
                file_name = f"{name}_captioned{ext}"
            
            save_path = os.path.join(results_path, file_name)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        
        # 保存修改后的图片
        img = img.convert('RGB')  # 转回RGB模式以支持所有格式
        img.save(save_path)
        print(f"图片已保存到: {save_path}")
        
        return save_path
    
    except Exception as e:
        print(f"处理图片时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def add_text_and_upload_to_feishu(image_source, text, save_path=None, **kwargs):
    """
    在图片上添加文字并上传到飞书
    
    Args:
        image_source: 图片路径或URL
        text: 要添加的文字
        save_path: 本地保存路径，默认保存到results文件夹
        **kwargs: 传递给add_text_to_image的额外参数
        
    Returns:
        飞书image_key
    """
    # 先添加文字
    processed_image_path = add_text_to_image(image_source, text, save_path, **kwargs)
    
    if processed_image_path:
        # 上传到飞书
        image_key = FeishuImageUtils.upload_image(processed_image_path)
        return image_key
    
    return None


def print_usage():
    """打印使用说明"""
    print("""在图片上添加字幕样式文字工具
用法:
    python add_text_to_pic.py <图片路径或URL> <要添加的文字> [保存路径] [字体大小百分比] [填充系数]
    
参数:
    图片路径或URL:    本地图片路径或在线图片URL
    要添加的文字:     要添加到图片底部的文字
    保存路径:         可选，保存处理后图片的路径，默认保存到results文件夹
    字体大小百分比:   可选，字体大小占图片高度的百分比，默认0.06
    填充系数:         可选，文字周围的填充系数，默认0.3
    
选项:
    --upload         处理后自动上传到飞书并返回image_key
    --help           显示此帮助信息
    
示例:
    python add_text_to_pic.py https://s.coze.cn/t/RLo5G8HWLsM ant
    python add_text_to_pic.py C:/Users/Admin/Desktop/image.jpg "Hello World" C:/Users/Admin/Desktop/output.png 0.07 0.3
    python add_text_to_pic.py https://s.coze.cn/t/RLo5G8HWLsM ant --upload
    """)


# 命令行入口
def main():
    # 检查是否需要显示帮助
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
        sys.exit(0)  # 确保退出程序
    
    # 解析参数
    image_source = sys.argv[1]
    
    if len(sys.argv) < 3:
        print("错误: 缺少要添加的文字参数")
        print_usage()
        return
    
    text = sys.argv[2]
    
    # 检查是否需要上传到飞书
    should_upload = "--upload" in sys.argv
    if should_upload:
        sys.argv.remove("--upload")
    
    # 可选参数
    save_path = sys.argv[3] if len(sys.argv) > 3 else None
    font_size_percentage = float(sys.argv[4]) if len(sys.argv) > 4 else 0.06
    padding_factor = float(sys.argv[5]) if len(sys.argv) > 5 else 0.3
    
    # 处理图片
    if should_upload:
        result = add_text_and_upload_to_feishu(
            image_source, 
            text, 
            save_path, 
            font_size_percentage=font_size_percentage, 
            padding_factor=padding_factor
        )
        if result:
            print(f"\n已上传到飞书，image_key: {result}")
    else:
        add_text_to_image(
            image_source, 
            text, 
            save_path, 
            font_size_percentage=font_size_percentage, 
            padding_factor=padding_factor
        )


# 示例使用
if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        # 直接运行脚本时的示例
        online_image = "https://s.coze.cn/t/RLo5G8HWLsM"
        add_text_to_image(online_image, "ant")