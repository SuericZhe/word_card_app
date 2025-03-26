from feishu_image_utils import FeishuImageUtils
import os
import sys

def print_usage():
    """打印使用说明"""
    print("""飞书图片工具使用说明：
    上传图片：python feishu_image_example.py upload <图片路径>
    下载图片：python feishu_image_example.py download <image_key> [保存路径]
    
示例：
    python feishu_image_example.py upload C:/Users/Admin/Desktop/ant.png
    python feishu_image_example.py download img_v3_02ko_1234abcd C:/Users/Admin/Desktop/saved.png
    """)

def main():
    """主函数"""
    # 参数不足，显示使用说明
    if len(sys.argv) < 3:
        print_usage()
        return
    
    action = sys.argv[1].lower()
    
    # 上传图片
    if action == "upload":
        image_path = sys.argv[2]
        image_key = FeishuImageUtils.upload_image(image_path)
        if image_key:
            print(f"\n上传成功！图片Key: {image_key}\n")
            print(f"您可以使用以下命令下载此图片：")
            print(f"python feishu_image_example.py download {image_key}")
    
    # 下载图片
    elif action == "download":
        image_key = sys.argv[2]
        save_path = sys.argv[3] if len(sys.argv) > 3 else None
        
        result_path = FeishuImageUtils.download_image(image_key, save_path)
        if result_path:
            print(f"\n下载成功！已保存到: {result_path}\n")
    
    # 未知命令
    else:
        print(f"未知命令: {action}")
        print_usage()

if __name__ == "__main__":
    main() 