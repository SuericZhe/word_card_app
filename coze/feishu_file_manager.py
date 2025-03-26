import os
import sys
import json
import sqlite3
from datetime import datetime
from feishu_file_utils import FeishuFileUtils

class FeishuFileManager:
    """飞书文件管理器，管理文件上传下载并记录到数据库"""
    
    def __init__(self, db_path=None):
        """
        初始化文件管理器
        
        Args:
            db_path: 数据库路径，默认为项目根目录下的database.db
        """
        # 设置数据库路径
        if not db_path:
            # 从当前脚本位置向上一级找到项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(project_root, "database.db")
        else:
            self.db_path = db_path
            
        # 确保数据库表存在
        self._ensure_database_table()
    
    def _ensure_database_table(self):
        """确保数据库中存在必要的表结构"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建存储文件信息的表（如果不存在）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS feishu_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_key TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                local_path TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()
            conn.close()
            print(f"已确保数据库表结构存在: {self.db_path}")
            
        except Exception as e:
            print(f"初始化数据库表时出错: {e}")
            raise
    
    def upload_file(self, file_path, file_name=None, category=None):
        """
        上传文件到飞书并记录到数据库
        
        Args:
            file_path: 要上传的文件路径
            file_name: 可选，上传后的文件名，默认使用原文件名
            category: 可选，文件分类
            
        Returns:
            成功返回文件信息字典，失败返回None
        """
        try:
            # 上传文件
            result = FeishuFileUtils.upload_file(file_path, file_name)
            
            if not result:
                return None
                
            # 准备数据库记录
            file_info = {
                "file_key": result["file_key"],
                "original_name": result["name"],
                "file_type": result["type"],
                "file_size": result["size"],
                "local_path": os.path.abspath(file_path),
                "category": category
            }
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO feishu_files 
            (file_key, original_name, file_type, file_size, local_path, category) 
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                file_info["file_key"],
                file_info["original_name"],
                file_info["file_type"],
                file_info["file_size"],
                file_info["local_path"],
                file_info["category"]
            ))
            
            # 获取插入的ID
            file_info["id"] = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            print(f"文件信息已保存到数据库，ID: {file_info['id']}")
            return file_info
            
        except Exception as e:
            print(f"上传文件并保存记录时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def download_file(self, file_key=None, db_id=None, save_path=None):
        """
        从飞书下载文件，可通过file_key或数据库ID下载
        
        Args:
            file_key: 飞书文件key，与db_id二选一
            db_id: 数据库中的记录ID，与file_key二选一
            save_path: 保存路径，默认保存到results文件夹
            
        Returns:
            成功返回保存路径，失败返回None
        """
        try:
            # 如果提供了数据库ID，查询file_key
            if db_id and not file_key:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM feishu_files WHERE id = ?", (db_id,))
                row = cursor.fetchone()
                conn.close()
                
                if not row:
                    print(f"错误: 数据库中未找到ID为 {db_id} 的记录")
                    return None
                    
                file_key = row["file_key"]
                print(f"已从数据库获取文件key: {file_key}")
            
            # 确保有文件key
            if not file_key:
                print("错误: 必须提供file_key或db_id参数")
                return None
                
            # 下载文件
            local_path = FeishuFileUtils.download_file(file_key, save_path)
            
            if local_path:
                # 如果是数据库中的记录，更新本地路径
                if db_id:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE feishu_files SET local_path = ? WHERE id = ?", 
                        (local_path, db_id)
                    )
                    conn.commit()
                    conn.close()
                    print(f"数据库记录已更新，ID: {db_id}")
                
                return local_path
            
            return None
            
        except Exception as e:
            print(f"下载文件时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_file_by_key(self, file_key):
        """从数据库查询文件记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM feishu_files WHERE file_key = ?", (file_key,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {key: row[key] for key in row.keys()}
            return None
            
        except Exception as e:
            print(f"查询数据库时出错: {e}")
            return None
    
    def get_files_by_category(self, category):
        """查询指定分类的所有文件"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM feishu_files WHERE category = ? ORDER BY created_at DESC", (category,))
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                return [{key: row[key] for key in row.keys()} for row in rows]
            return []
            
        except Exception as e:
            print(f"查询数据库时出错: {e}")
            return []


def print_usage():
    """打印使用说明"""
    print("""飞书文件管理工具
用法:
    python feishu_file_manager.py upload <文件路径> [文件名] [分类]
    python feishu_file_manager.py download <文件key或ID> [保存路径]
    python feishu_file_manager.py list [分类]
    
参数:
    upload       上传文件并记录到数据库
    download     下载文件，可使用文件key或数据库ID
    list         列出所有文件或指定分类的文件
    
选项:
    --help       显示此帮助信息
    --id         表示下载参数是数据库ID而非文件key
    
示例:
    python feishu_file_manager.py upload C:/Users/Admin/Desktop/giraffe.mp3 长颈鹿叫声.mp3 animal
    python feishu_file_manager.py download file_v3_00ko_xxxxxxxx
    python feishu_file_manager.py download 5 --id
    python feishu_file_manager.py list animal
    """)

def main():
    """命令行入口函数"""
    # 打印使用说明
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
        sys.exit(0)
    
    # 创建管理器
    manager = FeishuFileManager()
    
    # 解析命令
    command = sys.argv[1].lower()
    
    # 执行上传
    if command == "upload":
        if len(sys.argv) < 3:
            print("错误: 缺少文件路径参数")
            print_usage()
            return
            
        file_path = sys.argv[2]
        file_name = sys.argv[3] if len(sys.argv) > 3 else None
        category = sys.argv[4] if len(sys.argv) > 4 else None
        
        result = manager.upload_file(file_path, file_name, category)
        if result:
            print("\n===== 上传成功 =====")
            print(f"ID: {result['id']}")
            print(f"文件名: {result['original_name']}")
            print(f"文件类型: {result['file_type']}")
            print(f"文件大小: {result['file_size']} 字节")
            print(f"文件key: {result['file_key']}")
            print(f"分类: {result['category'] or '未分类'}")
        else:
            print("\n❌ 上传失败")
    
    # 执行下载
    elif command == "download":
        if len(sys.argv) < 3:
            print("错误: 缺少文件key或ID参数")
            print_usage()
            return
            
        # 检查是否是ID
        is_id = "--id" in sys.argv
        if is_id:
            sys.argv.remove("--id")
            
        key_or_id = sys.argv[2]
        save_path = sys.argv[3] if len(sys.argv) > 3 else None
        
        # 执行下载
        if is_id:
            try:
                db_id = int(key_or_id)
                result_path = manager.download_file(db_id=db_id, save_path=save_path)
            except ValueError:
                print(f"错误: ID必须是整数，收到: {key_or_id}")
                return
        else:
            result_path = manager.download_file(file_key=key_or_id, save_path=save_path)
            
        # 打印结果
        if result_path:
            print("\n===== 下载成功 =====")
            print(f"文件已保存到: {result_path}")
        else:
            print("\n❌ 下载失败")
    
    # 列出文件
    elif command == "list":
        category = sys.argv[2] if len(sys.argv) > 2 else None
        
        if category:
            files = manager.get_files_by_category(category)
            print(f"\n=== 分类 '{category}' 的文件 ({len(files)}) ===")
        else:
            conn = sqlite3.connect(manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feishu_files ORDER BY created_at DESC")
            files = [{key: row[key] for key in row.keys()} for row in cursor.fetchall()]
            conn.close()
            print(f"\n=== 所有文件 ({len(files)}) ===")
        
        # 打印结果
        if files:
            for i, file in enumerate(files):
                print(f"\n[{i+1}] ID: {file['id']}")
                print(f"    文件名: {file['original_name']}")
                print(f"    类型: {file['file_type']}")
                print(f"    大小: {file['file_size']} 字节")
                print(f"    Key: {file['file_key']}")
                print(f"    分类: {file['category'] or '未分类'}")
                print(f"    创建时间: {file['created_at']}")
        else:
            print("未找到文件记录")
    
    # 未知命令
    else:
        print(f"未知命令: {command}")
        print_usage()


if __name__ == "__main__":
    main() 