import os
import sys
import json
import sqlite3
from datetime import datetime
from sentence_to_image import SentenceToImageWorkflow
from word_sentence_audio import WordToSentenceWorkflow
from add_text_to_pic import add_text_to_image, add_text_and_upload_to_feishu
from word_to_audio import WordToAudioWorkflow
from douyin_tts import DouyinTTS


class SentenceProcessor:
    """句子生成、图片生成与处理工具类，整合单词到句子、句子到图片、添加文字和音频生成功能"""
    
    def __init__(self, db_path=None):
        """
        初始化句子处理器
        
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
        self.word_to_sentence_workflow = WordToSentenceWorkflow()
        self.sentence_to_image_workflow = SentenceToImageWorkflow()
        self.tts = DouyinTTS()
        
        # 确保数据库表存在
        self._ensure_database_table()
    
    def _ensure_database_table(self):
        """确保数据库中存在必要的表结构"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查word_sentences表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='word_sentences'")
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                # 创建存储句子信息的表
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS word_sentences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    sentence TEXT NOT NULL,
                    sentence_image_url TEXT NOT NULL,
                    local_image_path TEXT NOT NULL,
                    feishu_image_key TEXT NOT NULL,
                    local_audio_path TEXT,
                    feishu_audio_key TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                print("已创建word_sentences表")
            
            conn.commit()
            conn.close()
            print(f"已确保数据库表结构存在: {self.db_path}")
            
        except Exception as e:
            print(f"初始化数据库表时出错: {e}")
            raise
    
    def generate_sentence_and_process(self, word, category=None, use_existing_sentence=None, 
                                     font_size_percentage=0.06, padding_factor=0.3, 
                                     voice_type="BV503_streaming", speed_ratio=1.0):
        """
        为单词生成句子、图片，添加文字，生成音频，并上传到飞书
        
        Args:
            word: 要处理的英文单词
            category: 单词分类，用于组织文件
            use_existing_sentence: 可选，使用已有的句子而不是生成新句子
            font_size_percentage: 字体大小百分比
            padding_factor: 文字边距系数
            voice_type: 音频音色类型
            speed_ratio: 音频语速比例
            
        Returns:
            处理结果字典，包含各种路径和状态信息
        """
        result = {
            "word": word,
            "sentence": "",
            "category": category,
            "status": "failed",
            "sentence_image_url": "",
            "local_image_path": "",
            "feishu_image_key": "",
            "local_audio_path": "",
            "feishu_audio_key": "",
            "error": None
        }
        
        try:
            print(f"\n===== 开始处理单词 '{word}' 的句子 =====")
            
            # 步骤1: 生成或使用已有的例句
            if use_existing_sentence:
                sentence = use_existing_sentence
                print(f"使用已有句子: {sentence}")
            else:
                print(f"\n[步骤1] 为单词 '{word}' 生成例句...")
                word_to_sentence_result = self.word_to_sentence_workflow.execute(word)
                
                if not word_to_sentence_result or not word_to_sentence_result.get("sentences"):
                    error_msg = "生成例句失败，未能获取有效句子"
                    print(f"错误: {error_msg}")
                    result["error"] = error_msg
                    return result
                
                # 找到对应单词的句子
                sentence = None
                for sentence_info in word_to_sentence_result.get("sentences", []):
                    if sentence_info.get("word") == word:
                        sentence = sentence_info.get("sentence")
                        break
                
                if not sentence:
                    error_msg = f"未找到单词 '{word}' 对应的例句"
                    print(f"错误: {error_msg}")
                    result["error"] = error_msg
                    return result
            
            # 保存句子到结果
            result["sentence"] = sentence
            print(f"句子: {sentence}")
            
            # 步骤2: 从句子生成图片URL
            print(f"\n[步骤2] 从句子生成图片...")
            sentence_to_image_result = self.sentence_to_image_workflow.execute(sentence)
            
            if not sentence_to_image_result or not sentence_to_image_result.get("image_url"):
                error_msg = "生成图片失败，未能获取有效图片URL"
                print(f"错误: {error_msg}")
                result["error"] = error_msg
                return result
            
            # 获取生成的图片URL
            image_url = sentence_to_image_result["image_url"]
            result["sentence_image_url"] = image_url
            print(f"成功获取图片URL: {image_url}")
            
            # 步骤3: 添加文字标注并保存到本地
            print(f"\n[步骤3] 添加文字标注到图片...")
            
            # 准备分类目录（如果有分类）
            save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sentences")
            if category:
                save_dir = os.path.join(save_dir, category)
            os.makedirs(save_dir, exist_ok=True)
                
            # 生成保存路径
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_word = "".join(c if c.isalnum() else "_" for c in word[:20])
            save_filename = f"{safe_word}_sentence_{timestamp}.png"
            save_path = os.path.join(save_dir, save_filename)
            
            # 添加文字标注到图片（仅显示前60个字符，避免文字过多）
            display_text = sentence[:60] + "..." if len(sentence) > 60 else sentence
            local_image_path = add_text_to_image(
                image_source=image_url,
                text=display_text,
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
            
            # 步骤4: 上传图片到飞书并获取image_key
            print(f"\n[步骤4] 上传标注后的图片到飞书...")
            feishu_image_key = self._upload_to_feishu_image(local_image_path)
            
            if not feishu_image_key:
                error_msg = "上传图片到飞书失败"
                print(f"错误: {error_msg}")
                result["error"] = error_msg
                return result
                
            result["feishu_image_key"] = feishu_image_key
            print(f"图片上传成功，获取image_key: {feishu_image_key}")
            
            # 步骤5: 为句子生成音频
            print(f"\n[步骤5] 为句子生成音频...")
            audio_result = self.tts.text_to_speech(
                text=sentence,
                voice_type=voice_type,
                speed_ratio=speed_ratio
            )
            
            if not audio_result:
                error_msg = "生成音频失败"
                print(f"警告: {error_msg}")
                # 不终止整个流程，继续处理
            else:
                # 获取音频信息
                local_audio_path = audio_result["filepath"]
                audio_duration = audio_result.get("duration")
                result["local_audio_path"] = local_audio_path
                
                print(f"音频生成成功: {local_audio_path}")
                if audio_duration:
                    print(f"音频时长: {audio_duration}ms")
                
                # 步骤6: 上传音频到飞书
                print(f"\n[步骤6] 上传音频到飞书...")
                feishu_audio_key = self._upload_to_feishu_audio(local_audio_path, f"{safe_word}_sentence.mp3")
                
                if not feishu_audio_key:
                    error_msg = "上传音频到飞书失败"
                    print(f"警告: {error_msg}")
                    # 不终止整个流程，继续处理
                else:
                    result["feishu_audio_key"] = feishu_audio_key
                    print(f"音频上传成功，获取file_key: {feishu_audio_key}")
            
            # 步骤7: 保存信息到数据库
            print(f"\n[步骤7] 保存数据到数据库...")
            db_result = self._save_to_database(result)
            
            if not db_result:
                error_msg = "保存到数据库失败"
                print(f"错误: {error_msg}")
                result["error"] = error_msg
                return result
                
            # 处理成功
            result["status"] = "success"
            print(f"\n✅ 单词 '{word}' 的句子处理完成!")
            print(f"句子: {result['sentence']}")
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
    
    def _upload_to_feishu_audio(self, audio_path, filename=None):
        """上传音频到飞书"""
        from feishu_file_utils import FeishuFileUtils
        
        try:
            # 上传音频文件
            file_info = FeishuFileUtils.upload_file(audio_path, filename)
            if file_info:
                return file_info["file_key"]
            return None
        except Exception as e:
            print(f"上传音频到飞书时发生错误: {e}")
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
            INSERT INTO word_sentences 
            (word, sentence, sentence_image_url, local_image_path, feishu_image_key, 
             local_audio_path, feishu_audio_key, category) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result_data["word"],
                result_data["sentence"],
                result_data["sentence_image_url"],
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
    
    def get_sentences_by_word(self, word, category=None, limit=5):
        """
        从数据库中查询单词对应的句子信息
        
        Args:
            word: 要查询的单词
            category: 可选的分类过滤条件
            limit: 最大返回条数
            
        Returns:
            查询结果列表，未找到返回空列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 启用行工厂，使结果可以通过列名访问
            cursor = conn.cursor()
            
            # 构建查询
            if category:
                cursor.execute(
                    "SELECT * FROM word_sentences WHERE word = ? AND category = ? ORDER BY created_at DESC LIMIT ?", 
                    (word, category, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM word_sentences WHERE word = ? ORDER BY created_at DESC LIMIT ?", 
                    (word, limit)
                )
            
            # 获取结果
            rows = cursor.fetchall()
            conn.close()
            
            # 转换为字典列表
            result = []
            for row in rows:
                result.append({key: row[key] for key in row.keys()})
            
            return result
            
        except Exception as e:
            print(f"查询数据库时出错: {e}")
            return []


def main():
    """命令行入口函数"""
    # 打印使用说明
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print("""单词句子图片与音频生成处理工具

用法:
    python generate_and_caption_sentence.py <单词> [句子] [分类] [音色类型] [语速比例]
    
参数:
    单词:     要处理的英文单词
    句子:     可选，现有句子。如不提供，会为单词生成新句子
    分类:     可选，单词的分类，用于组织文件
    音色类型:  可选，音频音色类型，默认女声BV503_streaming
              可选值: BV003_streaming（男声1）、BV503_streaming（女声1）
                    BV113_streaming（男声2）、BV703_streaming（女声2）
    语速比例:  可选，音频语速比例，默认1.0
    
示例:
    python generate_and_caption_sentence.py apple
    python generate_and_caption_sentence.py elephant "The elephant is the largest land animal on Earth." animal BV003_streaming 0.8
        """)
        sys.exit(0)
    
    # 获取参数
    word = sys.argv[1]
    
    # 句子是可选的，如果提供可能包含空格，需要特殊处理
    sentence = None
    category = None
    voice_type = "BV503_streaming"
    speed_ratio = 1.0
    
    if len(sys.argv) > 2:
        # 检查第二个参数是否是句子（包含空格，并且不是其他参数）
        if sys.argv[2].startswith('"') or ' ' in sys.argv[2]:
            # 可能是句子，尝试解析并获取剩余参数
            sentence_parts = []
            i = 2
            while i < len(sys.argv):
                part = sys.argv[i]
                if part.startswith('"'):
                    # 句子开始
                    part = part[1:]  # 移除开头的引号
                    if part.endswith('"'):
                        # 单引号句子
                        sentence_parts.append(part[:-1])
                        i += 1
                        break
                    else:
                        sentence_parts.append(part)
                        i += 1
                        # 继续到下一个部分
                        continue
                elif part.endswith('"'):
                    # 句子结束
                    sentence_parts.append(part[:-1])
                    i += 1
                    break
                elif sentence_parts:
                    # 句子中间部分
                    sentence_parts.append(part)
                    i += 1
                else:
                    # 不是句子，可能是其他参数
                    break
                    
            if sentence_parts:
                sentence = " ".join(sentence_parts)
                # 继续处理剩余参数
                if i < len(sys.argv):
                    category = sys.argv[i]
                    i += 1
                if i < len(sys.argv):
                    voice_type = sys.argv[i]
                    i += 1
                if i < len(sys.argv):
                    try:
                        speed_ratio = float(sys.argv[i])
                    except ValueError:
                        print(f"警告: 语速比例无效，使用默认值1.0")
            else:
                # 没有句子，其他参数直接处理
                category = sys.argv[2]
                if len(sys.argv) > 3:
                    voice_type = sys.argv[3]
                if len(sys.argv) > 4:
                    try:
                        speed_ratio = float(sys.argv[4])
                    except ValueError:
                        print(f"警告: 语速比例无效，使用默认值1.0")
        else:
            # 第二个参数不是句子，是其他参数
            category = sys.argv[2]
            if len(sys.argv) > 3:
                voice_type = sys.argv[3]
            if len(sys.argv) > 4:
                try:
                    speed_ratio = float(sys.argv[4])
                except ValueError:
                    print(f"警告: 语速比例无效，使用默认值1.0")
    
    # 创建处理器并执行
    processor = SentenceProcessor()
    result = processor.generate_sentence_and_process(
        word=word,
        category=category,
        use_existing_sentence=sentence,
        voice_type=voice_type,
        speed_ratio=speed_ratio
    )
    
    # 打印最终结果
    if result["status"] == "success":
        print("\n===== 处理结果 =====")
        print(f"单词: {result['word']}")
        print(f"句子: {result['sentence']}")
        print(f"分类: {result['category'] or '未分类'}")
        print(f"原始图片URL: {result['sentence_image_url']}")
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
        processor = SentenceProcessor()
        result = processor.generate_sentence_and_process("bird", "animal")
        print(json.dumps(result, indent=2, ensure_ascii=False)) 