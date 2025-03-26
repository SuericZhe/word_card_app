import os
import sys
import json
import sqlite3
from datetime import datetime
from word_to_image import WordToImageWorkflow
from word_to_audio import WordToAudioWorkflow
from add_text_to_pic import add_text_to_image, add_text_and_upload_to_feishu


class ImageProcessor:
    """图片生成与处理工具类，整合单词到图片生成和添加文字字幕功能"""
    
    def __init__(self, db_path=None):
        """
        初始化图片处理器
        
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
            
        # 初始化工作流
        self.word_to_image_workflow = WordToImageWorkflow()
        self.word_to_audio_workflow = WordToAudioWorkflow()
        
        # 确保数据库表存在
        self._ensure_database_table()
    
    def _ensure_database_table(self):
        """确保数据库中存在必要的表结构"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查word_images表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='word_images'")
            table_exists = cursor.fetchone() is not None
            
            if table_exists:
                # 检查是否需要添加新列
                cursor.execute("PRAGMA table_info(word_images)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # 如果需要，添加音频相关列
                if "local_audio_path" not in columns:
                    print("正在更新word_images表结构，添加音频字段...")
                    cursor.execute("ALTER TABLE word_images ADD COLUMN local_audio_path TEXT")
                if "feishu_audio_key" not in columns:
                    cursor.execute("ALTER TABLE word_images ADD COLUMN feishu_audio_key TEXT")
            else:
                # 创建新表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS word_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    original_image_url TEXT NOT NULL,
                    local_image_path TEXT NOT NULL,
                    feishu_image_key TEXT NOT NULL,
                    local_audio_path TEXT,
                    feishu_audio_key TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                print("已创建word_images表")
            
            conn.commit()
            conn.close()
            print(f"已确保数据库表结构存在: {self.db_path}")
            
        except Exception as e:
            print(f"初始化数据库表时出错: {e}")
            raise
    
    def generate_and_process_image(self, word, category=None, font_size_percentage=0.06, padding_factor=0.3, 
                                  voice_type="BV503_streaming", speed_ratio=1.0):
        """
        生成单词图片，添加文字标注，生成单词音频，并上传到飞书
        
        Args:
            word: 要处理的英文单词
            category: 单词分类，用于组织图片
            font_size_percentage: 字体大小百分比
            padding_factor: 文字边距系数
            voice_type: 音频音色类型
            speed_ratio: 音频语速比例
            
        Returns:
            处理结果字典，包含各种路径和状态信息
        """
        result = {
            "word": word,
            "category": category,
            "status": "failed",
            "original_image_url": "",
            "local_image_path": "",
            "feishu_image_key": "",
            "local_audio_path": "",
            "feishu_audio_key": "",
            "error": None
        }
        
        try:
            print(f"\n===== 开始处理单词: {word} =====")
            
            # 步骤1: 从单词生成图片URL
            print(f"\n[步骤1] 从单词 '{word}' 生成图片...")
            word_to_image_result = self.word_to_image_workflow.execute(word)
            
            if not word_to_image_result or not word_to_image_result.get("image_url"):
                error_msg = "生成图片失败，未能获取有效图片URL"
                print(f"错误: {error_msg}")
                result["error"] = error_msg
                return result
            
            # 获取生成的图片URL
            image_url = word_to_image_result["image_url"]
            result["original_image_url"] = image_url
            print(f"成功获取图片URL: {image_url}")
            
            # 步骤2: 添加文字标注并保存到本地
            print(f"\n[步骤2] 添加文字标注 '{word}' 到图片...")
            
            # 准备分类目录（如果有分类）
            save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
            if category:
                save_dir = os.path.join(save_dir, category)
                os.makedirs(save_dir, exist_ok=True)
                
            # 生成保存路径
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_filename = f"{word}_{timestamp}.png"
            save_path = os.path.join(save_dir, save_filename)
            
            # 添加文字标注到图片
            local_image_path = add_text_to_image(
                image_source=image_url,
                text=word,
                save_path=save_path,
                font_size_percentage=font_size_percentage,
                padding_factor=padding_factor
            )
            
            if not local_image_path:
                error_msg = "添加文字标注失败"
                print(f"错误: {error_msg}")
                result["error"] = error_msg
                return result
                
            result["local_image_path"] = local_image_path
            print(f"图片已保存到: {local_image_path}")
            
            # 步骤3: 上传到飞书并获取image_key
            print(f"\n[步骤3] 上传标注后的图片到飞书...")
            feishu_image_key = self._upload_to_feishu_image(local_image_path)
            
            if not feishu_image_key:
                error_msg = "上传图片到飞书失败"
                print(f"错误: {error_msg}")
                result["error"] = error_msg
                return result
                
            result["feishu_image_key"] = feishu_image_key
            print(f"图片上传成功，获取image_key: {feishu_image_key}")
            
            # 步骤4: 生成单词音频
            print(f"\n[步骤4] 为单词 '{word}' 生成音频...")
            audio_result = self.word_to_audio_workflow.execute(
                input_word=word, 
                voice_type=voice_type, 
                speed_ratio=speed_ratio
            )
            
            if not audio_result or audio_result["status"] != "success":
                error_msg = f"生成音频失败: {audio_result.get('error', '未知错误')}" if audio_result else "生成音频失败"
                print(f"警告: {error_msg}")
                # 不终止整个流程，继续处理
            else:
                # 获取音频信息
                result["local_audio_path"] = audio_result["local_audio_path"]
                result["feishu_audio_key"] = audio_result["feishu_file_key"]
                print(f"音频生成成功: {result['local_audio_path']}")
                print(f"音频上传成功，获取file_key: {result['feishu_audio_key']}")
            
            # 步骤5: 保存信息到数据库
            print(f"\n[步骤5] 保存数据到数据库...")
            db_result = self._save_to_database(result)
            
            if not db_result:
                error_msg = "保存到数据库失败"
                print(f"错误: {error_msg}")
                result["error"] = error_msg
                return result
                
            # 处理成功
            result["status"] = "success"
            print(f"\n✅ 单词 '{word}' 处理完成!")
            print(f"图片已保存到: {local_image_path}")
            print(f"飞书图片key: {feishu_image_key}")
            if result["local_audio_path"]:
                print(f"本地音频路径: {result['local_audio_path']}")
                print(f"飞书音频Key: {result['feishu_audio_key']}")
            
            return result
            
        except Exception as e:
            import traceback
            print(f"\n❌ 处理过程中发生错误: {str(e)}")
            traceback.print_exc()
            result["error"] = str(e)
            return result
    
    def _upload_to_feishu_image(self, image_path):
        """上传图片到飞书"""
        from feishu_image_utils import FeishuImageUtils
        
        try:
            # 上传图片
            image_key = FeishuImageUtils.upload_image(image_path)
            return image_key
        except Exception as e:
            print(f"上传图片到飞书时发生错误: {e}")
            return None
    
    def _save_to_database(self, result_data):
        """
        将处理结果保存到数据库
        
        Args:
            result_data: 处理结果数据字典
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 插入记录
            cursor.execute('''
            INSERT INTO word_images 
            (word, original_image_url, local_image_path, feishu_image_key, 
             local_audio_path, feishu_audio_key, category) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_data["word"],
                result_data["original_image_url"],
                result_data["local_image_path"],
                result_data["feishu_image_key"],
                result_data.get("local_audio_path", ""),
                result_data.get("feishu_audio_key", ""),
                result_data["category"]
            ))
            
            # 获取插入的ID
            last_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            print(f"记录已保存到数据库，ID: {last_id}")
            return True
            
        except Exception as e:
            print(f"保存到数据库时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_image_by_word(self, word, category=None):
        """
        从数据库中查询单词对应的图片信息
        
        Args:
            word: 要查询的单词
            category: 可选的分类过滤条件
            
        Returns:
            查询结果字典，未找到返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 启用行工厂，使结果可以通过列名访问
            cursor = conn.cursor()
            
            # 构建查询
            if category:
                cursor.execute(
                    "SELECT * FROM word_images WHERE word = ? AND category = ? ORDER BY created_at DESC LIMIT 1", 
                    (word, category)
                )
            else:
                cursor.execute(
                    "SELECT * FROM word_images WHERE word = ? ORDER BY created_at DESC LIMIT 1", 
                    (word,)
                )
            
            # 获取结果
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # 转换为字典
                return {key: row[key] for key in row.keys()}
            else:
                return None
                
        except Exception as e:
            print(f"查询数据库时出错: {e}")
            return None


def main():
    """命令行入口函数"""
    # 打印使用说明
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print("""单词图片与音频生成处理工具

用法:
    python generate_and_caption_image.py <单词> [分类] [音色类型] [语速比例]
    
参数:
    单词:     要处理的英文单词
    分类:     可选，单词的分类，用于组织图片
    音色类型:  可选，音频音色类型，默认女声BV503_streaming
              可选值: BV003_streaming（男声1）、BV503_streaming（女声1）
                    BV113_streaming（男声2）、BV703_streaming（女声2）
    语速比例:  可选，音频语速比例，默认1.0
    
示例:
    python generate_and_caption_image.py bird
    python generate_and_caption_image.py elephant animal BV003_streaming 0.8
        """)
        sys.exit(0)
    
    # 获取参数
    word = sys.argv[1]
    category = sys.argv[2] if len(sys.argv) > 2 else None
    voice_type = sys.argv[3] if len(sys.argv) > 3 else "BV503_streaming"
    
    try:
        speed_ratio = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    except ValueError:
        print(f"警告: 语速比例无效，使用默认值1.0")
        speed_ratio = 1.0
    
    # 创建处理器并执行
    processor = ImageProcessor()
    result = processor.generate_and_process_image(
        word=word, 
        category=category,
        voice_type=voice_type,
        speed_ratio=speed_ratio
    )
    
    # 打印最终结果
    if result["status"] == "success":
        print("\n===== 处理结果 =====")
        print(f"单词: {result['word']}")
        print(f"分类: {result['category'] or '未分类'}")
        print(f"原始图片URL: {result['original_image_url']}")
        print(f"本地图片路径: {result['local_image_path']}")
        print(f"飞书图片Key: {result['feishu_image_key']}")
        if result["local_audio_path"]:
            print(f"本地音频路径: {result['local_audio_path']}")
            print(f"飞书音频Key: {result['feishu_audio_key']}")
    else:
        print(f"\n❌ 处理失败: {result['error']}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        # 直接运行脚本时的示例
        processor = ImageProcessor()
        result = processor.generate_and_process_image("bird", "animal")
        print(json.dumps(result, indent=2, ensure_ascii=False)) 