import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coze.feishu_image_utils import FeishuImageUtils

def upload_category_images():
    """上传分类图片到飞书"""
    # 图片路径
    image_paths = {
        "单词": "static/main_pic/单词.jpeg",
        "大学之道": "static/main_pic/大学之道.png",
        "音律启蒙": "static/main_pic/音律启蒙.jpeg",
        "甲骨文": "static/main_pic/甲骨文.png"
    }
    
    # 存储上传结果的字典
    image_keys = {}
    
    # 上传每个图片
    for category, path in image_paths.items():
        print(f"\n正在上传 {category} 的图片...")
        if os.path.exists(path):
            image_key = FeishuImageUtils.upload_image(path)
            if image_key:
                image_keys[category] = image_key
                print(f"上传成功！image_key: {image_key}")
            else:
                print(f"上传失败：{category}")
        else:
            print(f"错误：找不到图片文件 {path}")
    
    # 保存结果到文件
    if image_keys:
        with open("static/main_pic/feishu_image_keys.json", "w", encoding="utf-8") as f:
            import json
            json.dump(image_keys, f, ensure_ascii=False, indent=2)
        print("\n图片key已保存到 static/main_pic/feishu_image_keys.json")
    else:
        print("\n没有成功上传任何图片")

if __name__ == "__main__":
    upload_category_images() 