import os
import sys
import json
from feishu_file_utils import FeishuFileUtils

def print_usage():
    """打印使用说明"""
    print("""飞书文件上传工具
用法:
    python feishu_file_up.py <文件路径> [文件名]
    
参数:
    文件路径:   要上传的文件路径
    文件名:     可选，上传后的文件名，默认使用原文件名
    
选项:
    --help    显示此帮助信息
    
示例:
    python feishu_file_up.py C:/Users/Admin/Desktop/giraffe.mp3
    python feishu_file_up.py C:/Users/Admin/Desktop/giraffe.mp3 动物声音.mp3
    """)

def main():
    """命令行入口函数"""
    # 打印使用说明
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
        sys.exit(0)
    
    # 获取参数
    file_path = sys.argv[1]
    file_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 上传文件
    result = FeishuFileUtils.upload_file(file_path, file_name)
    
    # 打印结果
    if result:
        print("\n===== 上传成功 =====")
        print(f"文件名: {result['name']}")
        print(f"文件类型: {result['type']}")
        print(f"文件大小: {result['size']} 字节")
        print(f"文件key: {result['file_key']}")
        print("\n可以使用以下命令下载此文件:")
        print(f"python feishu_file_down.py {result['file_key']}")
    else:
        print("\n❌ 上传失败")

if __name__ == "__main__":
    main()