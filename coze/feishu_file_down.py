import os
import sys
from feishu_file_utils import FeishuFileUtils

def print_usage():
    """打印使用说明"""
    print("""飞书文件下载工具
用法:
    python feishu_file_down.py <文件key> [保存路径]
    
参数:
    文件key:   要下载的飞书文件key
    保存路径:     可选，文件保存路径，默认保存到results文件夹
    
选项:
    --help    显示此帮助信息
    
示例:
    python feishu_file_down.py msg_xxxxxxxxx
    python feishu_file_down.py msg_xxxxxxxxx C:/Users/Admin/Desktop/下载文件.mp3
    """)

def main():
    """命令行入口函数"""
    # 打印使用说明
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
        sys.exit(0)
    
    # 获取参数
    file_key = sys.argv[1]
    save_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 下载文件
    result_path = FeishuFileUtils.download_file(file_key, save_path)
    
    # 打印结果
    if result_path:
        print("\n===== 下载成功 =====")
        print(f"文件已保存到: {result_path}")
    else:
        print("\n❌ 下载失败")

if __name__ == "__main__":
    main()