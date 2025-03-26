#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
综合工作流模块 - 整合单词处理全流程

这个模块将整合以下功能：
1. 将单词转换为例句和作文
2. 为每个单词生成单词图片、句子图片和作文图片
3. 为单词、句子和作文生成音频
4. 将所有资源保存到数据库，建立关联
"""

import os
import sys
import json
import time
import sqlite3
import shutil
from datetime import datetime
import logging
import uuid

# 导入所需的工作流模块
from coze.word_to_sentence import WordToSentenceWorkflow
from coze.word_to_image import WordToImageWorkflow
from coze.sentence_to_image import SentenceToImageWorkflow
from coze.word_to_audio import WordToAudioWorkflow
from coze.add_text_to_pic import add_text_to_image, add_text_and_upload_to_feishu
from coze.douyin_tts import DouyinTTS
from coze.feishu_file_utils import FeishuFileUtils
from coze.standalone_text_to_pic import TextToPicture

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('comprehensive_workflow.log')
    ]
)
logger = logging.getLogger('ComprehensiveWorkflow')

class ComprehensiveWorkflow:
    """
    综合工作流类，整合单词处理的所有步骤
    
    功能：
    1. 批量处理单词列表
    2. 为每个单词生成单词图片、句子图片和作文图片
    3. 为所有内容生成音频
    4. 保存所有资源并记录到数据库
    """
    
    def __init__(self, db_path=None, results_dir=None, save_results=True):
        """
        初始化综合工作流
        
        参数:
            db_path: 数据库路径，默认为项目根目录下的database.db
            results_dir: 结果保存目录，默认为项目根目录下的results
            save_results: 是否保存中间结果，默认为True
        """
        # 设置数据库路径
        if not db_path:
            # 从当前脚本位置向上一级找到项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(project_root, "database.db")
        else:
            self.db_path = db_path
            
        # 设置结果保存目录
        if not results_dir:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.results_dir = os.path.join(project_root, "results")
        else:
            self.results_dir = results_dir
            
        # 创建结果目录（如果不存在）
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 保存中间结果的设置
        self.save_results = save_results
        
        # 初始化各个工作流组件
        self.word_to_sentence_workflow = WordToSentenceWorkflow(save_results=save_results)
        self.word_to_image_workflow = WordToImageWorkflow(save_results=save_results)
        self.sentence_to_image_workflow = SentenceToImageWorkflow(save_results=save_results)
        self.word_to_audio_workflow = WordToAudioWorkflow(save_results=save_results)
        self.text_to_pic = TextToPicture()
        self.tts = DouyinTTS()
        
        # 确保数据库表存在
        self._ensure_database_tables()
        
        # 进度回调函数
        self.progress_callback = None
        
    def _ensure_database_tables(self):
        """确保数据库中存在必要的表结构"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建词汇表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                chinese_name TEXT,
                pinyin TEXT,
                english_name TEXT,
                image_path TEXT,
                learn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                review_date TIMESTAMP,
                review_count INTEGER DEFAULT 0
            )
            ''')
            
            # 创建内容表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS contents (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                content_image TEXT,
                content_audio TEXT,
                example_image TEXT,
                example_audio TEXT,
                essay_image TEXT,
                essay_audio TEXT,
                learn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                next_review_date TIMESTAMP,
                review_count INTEGER DEFAULT 0
            )
            ''')
            
            # 创建单词图片表
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
            
            # 创建单词句子表
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
            
            # 创建作文表（新增）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_essays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                words TEXT NOT NULL,  -- 以逗号分隔的单词列表
                essay TEXT NOT NULL,
                essay_image_url TEXT,
                local_image_path TEXT NOT NULL,
                feishu_image_key TEXT NOT NULL,
                local_audio_path TEXT,
                feishu_audio_key TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"已确保数据库表结构存在: {self.db_path}")
            
        except Exception as e:
            logger.error(f"初始化数据库表时出错: {e}")
            raise
        
    def set_progress_callback(self, callback):
        """
        设置进度回调函数
        
        参数:
            callback: 回调函数，接受(stage, message, progress, word)参数
                     stage: 处理阶段
                     message: 描述信息
                     progress: 进度百分比(0-100)
                     word: 当前处理的单词
        """
        self.progress_callback = callback
        
    def _report_progress(self, stage, message, progress=0, word=None):
        """报告处理进度"""
        logger.info(f"[{stage}] {message} - 进度: {progress}%")
        if self.progress_callback:
            self.progress_callback(stage, message, progress, word)
    
    def execute(self, input_words, category=None, learn_date=None, voice_type="BV503_streaming", 
               speed_ratio=1.0, is_async=True):
        """
        执行完整的工作流，处理输入的单词列表
        
        参数:
            input_words: 输入的单词列表或空格分隔的单词字符串
            category: 分类，用于组织文件和数据库记录
            learn_date: 学习日期，默认为当前日期
            voice_type: 音频音色类型
            speed_ratio: 音频语速比例
            is_async: 是否异步执行Coze工作流，默认为True
            
        返回:
            处理结果字典，包含处理状态和各个单词的结果
        """
        # 初始化结果
        result = {
            "status": "success",
            "words": [],
            "essay": None,
            "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S'),
            "category": category,
            "error": None
        }
        
        # 确保单词列表格式正确
        if isinstance(input_words, str):
            input_words = input_words.strip().split()
        
        # 如果没有单词，返回错误
        if not input_words:
            error_msg = "输入的单词列表为空"
            logger.error(error_msg)
            result["status"] = "failed"
            result["error"] = error_msg
            return result
        
        # 设置学习日期
        if not learn_date:
            learn_date = datetime.now().strftime('%Y-%m-%d')
        
        # 创建分类目录
        if category:
            category_dir = os.path.join(self.results_dir, category)
            os.makedirs(category_dir, exist_ok=True)
        
        try:
            # 开始时间
            start_time = time.time()
            total_words = len(input_words)
            
            # 步骤1: 生成例句和作文
            self._report_progress("sentences", f"为 {len(input_words)} 个单词生成例句和作文", 0)
            word_to_sentence_result = self.word_to_sentence_workflow.execute(
                input_words, 
                is_async=is_async
            )
            
            if not word_to_sentence_result or not word_to_sentence_result.get("sentences"):
                error_msg = "生成例句和作文失败，未能获取有效结果"
                logger.error(error_msg)
                result["status"] = "failed"
                result["error"] = error_msg
                return result
            
            # 提取句子和作文
            sentences = word_to_sentence_result.get("sentences", [])
            essay = word_to_sentence_result.get("essay", "")
            
            # 检查是否每个单词都有例句
            word_to_sentence_map = {s.get("word"): s.get("sentence") for s in sentences if s.get("word") and s.get("sentence")}
            missing_words = [word for word in input_words if word not in word_to_sentence_map]
            
            if missing_words:
                logger.warning(f"以下单词未生成例句: {', '.join(missing_words)}")
            
            # 处理作文
            if essay:
                self._report_progress("essay", "处理作文", 20)
                essay_result = self._process_essay(essay, input_words, category, voice_type, speed_ratio)
                result["essay"] = essay_result
                self._report_progress("essay", "作文处理完成", 30)
            else:
                logger.warning("未能生成有效的作文")
            
            # 逐个处理单词
            for i, word in enumerate(input_words):
                word_progress = int(30 + (i / total_words) * 70)
                self._report_progress("word", f"处理单词 {i+1}/{total_words}: {word}", word_progress, word)
                
                # 查找该单词的例句
                sentence = word_to_sentence_map.get(word)
                
                # 处理单个单词的所有资源
                word_result = self._process_word(
                    word, 
                    sentence, 
                    category, 
                    voice_type, 
                    speed_ratio
                )
                
                # 添加到结果
                result["words"].append(word_result)
                
                # 报告进度
                self._report_progress("word", f"单词 {word} 处理完成", word_progress, word)
            
            # 处理完成
            elapsed_time = time.time() - start_time
            logger.info(f"全部 {len(input_words)} 个单词处理完成，耗时：{elapsed_time:.2f}秒")
            self._report_progress("complete", f"全部 {len(input_words)} 个单词处理完成", 100)
            
            # 添加一些统计信息
            result["stats"] = {
                "total_words": len(input_words),
                "processed_words": len(result["words"]),
                "elapsed_time": elapsed_time,
                "success_count": sum(1 for w in result["words"] if w.get("status") == "success"),
                "failed_count": sum(1 for w in result["words"] if w.get("status") == "failed")
            }
            
            # 保存综合结果
            if self.save_results:
                self._save_comprehensive_result(result)
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            logger.error(f"处理过程中发生错误: {error_msg}")
            logger.error(traceback.format_exc())
            result["status"] = "failed"
            result["error"] = error_msg
            self._report_progress("error", f"处理出错: {error_msg}", 0)
            return result
    
    def _process_word(self, word, sentence, category, voice_type, speed_ratio):
        """
        处理单个单词的所有资源（单词图片、单词音频、句子图片、句子音频）
        
        参数:
            word: 单词
            sentence: 例句
            category: 分类
            voice_type: 音频音色
            speed_ratio: 语速比例
            
        返回:
            单词处理结果字典
        """
        result = {
            "word": word,
            "sentence": sentence,
            "status": "success",
            "category": category,
            "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S'),
            "word_image": None,
            "sentence_image": None,
            "error": None
        }
        
        try:
            # 1. 处理单词图片
            logger.info(f"为单词 '{word}' 生成图片")
            word_image_result = self._process_word_image(word, category, voice_type, speed_ratio)
            result["word_image"] = word_image_result
            
            # 如果单词图片处理失败，继续处理其他资源，不要完全终止
            if word_image_result.get("status") == "failed":
                logger.warning(f"单词 '{word}' 图片处理失败: {word_image_result.get('error')}")
            
            # 2. 如果有例句，处理句子图片
            if sentence:
                logger.info(f"为单词 '{word}' 的例句生成图片")
                sentence_image_result = self._process_sentence_image(word, sentence, category, voice_type, speed_ratio)
                result["sentence_image"] = sentence_image_result
                
                if sentence_image_result.get("status") == "failed":
                    logger.warning(f"单词 '{word}' 的例句图片处理失败: {sentence_image_result.get('error')}")
            else:
                logger.warning(f"单词 '{word}' 没有例句，跳过句子图片生成")
            
            # 保存到数据库
            self._save_word_to_database(result)
            
            return result
            
        except Exception as e:
            logger.error(f"处理单词 '{word}' 时出错: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
            return result
    
    def _process_word_image(self, word, category, voice_type, speed_ratio):
        """处理单词图片和音频"""
        result = {
            "word": word,
            "status": "failed",
            "original_image_url": "",
            "local_image_path": "",
            "feishu_image_key": "",
            "local_audio_path": "",
            "feishu_audio_key": "",
            "error": None
        }
        
        try:
            # 生成单词图片
            word_to_image_result = self.word_to_image_workflow.execute(word)
            
            if not word_to_image_result or not word_to_image_result.get("image_url"):
                error_msg = "生成单词图片失败，未能获取有效图片URL"
                logger.error(error_msg)
                result["error"] = error_msg
                return result
            
            # 获取图片URL
            image_url = word_to_image_result["image_url"]
            result["original_image_url"] = image_url
            
            # 添加文字并保存图片
            save_dir = os.path.join(self.results_dir, "word_images")
            if category:
                save_dir = os.path.join(save_dir, category)
            os.makedirs(save_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_filename = f"{word}_{timestamp}.png"
            save_path = os.path.join(save_dir, save_filename)
            
            # 添加文字
            local_image_path = add_text_to_image(
                image_source=image_url,
                text=word,
                save_path=save_path,
                font_size_percentage=0.06
            )
            
            if not local_image_path:
                error_msg = "添加文字到图片失败"
                logger.error(error_msg)
                result["error"] = error_msg
                return result
            
            result["local_image_path"] = local_image_path
            
            # 上传到飞书
            feishu_image_key = add_text_and_upload_to_feishu(
                image_source=image_url,
                text=word,
                font_size_percentage=0.06
            )
            
            if not feishu_image_key:
                error_msg = "上传图片到飞书失败"
                logger.warning(error_msg)
                result["error"] = error_msg
                # 继续执行，不要因为上传失败而终止
            
            result["feishu_image_key"] = feishu_image_key or ""
            
            # 生成单词音频
            audio_result = self.word_to_audio_workflow.execute(
                input_word=word, 
                voice_type=voice_type, 
                speed_ratio=speed_ratio
            )
            
            if audio_result and audio_result["status"] == "success":
                result["local_audio_path"] = audio_result["local_audio_path"]
                result["feishu_audio_key"] = audio_result["feishu_file_key"]
            else:
                logger.warning(f"生成单词音频失败: {audio_result.get('error') if audio_result else '未知错误'}")
            
            # 更新状态
            result["status"] = "success"
            return result
            
        except Exception as e:
            logger.error(f"处理单词图片时出错: {e}")
            result["error"] = str(e)
            return result
    
    def _process_sentence_image(self, word, sentence, category, voice_type, speed_ratio):
        """处理句子图片和音频"""
        result = {
            "word": word,
            "sentence": sentence,
            "status": "failed",
            "sentence_image_url": "",
            "local_image_path": "",
            "feishu_image_key": "",
            "local_audio_path": "",
            "feishu_audio_key": "",
            "error": None
        }
        
        try:
            # 生成句子图片
            sentence_to_image_result = self.sentence_to_image_workflow.execute(sentence)
            
            if not sentence_to_image_result or not sentence_to_image_result.get("image_url"):
                error_msg = "生成句子图片失败，未能获取有效图片URL"
                logger.error(error_msg)
                result["error"] = error_msg
                return result
            
            # 获取图片URL
            image_url = sentence_to_image_result["image_url"]
            result["sentence_image_url"] = image_url
            
            # 添加文字并保存图片
            save_dir = os.path.join(self.results_dir, "sentence_images")
            if category:
                save_dir = os.path.join(save_dir, category)
            os.makedirs(save_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_word = "".join(c if c.isalnum() else "_" for c in word[:20])
            save_filename = f"{safe_word}_sentence_{timestamp}.png"
            save_path = os.path.join(save_dir, save_filename)
            
            # 只显示句子的前60个字符
            display_text = sentence[:60] + "..." if len(sentence) > 60 else sentence
            
            # 添加文字
            local_image_path = add_text_to_image(
                image_source=image_url,
                text=display_text,
                save_path=save_path,
                font_size_percentage=0.05
            )
            
            if not local_image_path:
                error_msg = "添加文字到句子图片失败"
                logger.error(error_msg)
                result["error"] = error_msg
                return result
            
            result["local_image_path"] = local_image_path
            
            # 上传到飞书
            feishu_image_key = add_text_and_upload_to_feishu(
                image_source=image_url,
                text=display_text,
                font_size_percentage=0.05
            )
            
            if not feishu_image_key:
                error_msg = "上传句子图片到飞书失败"
                logger.warning(error_msg)
                result["error"] = error_msg
                # 继续执行，不要因为上传失败而终止
            
            result["feishu_image_key"] = feishu_image_key or ""
            
            # 生成句子音频
            audio_result = self.tts.text_to_speech(
                text=sentence,
                voice_type=voice_type,
                speed_ratio=speed_ratio
            )
            
            if audio_result:
                result["local_audio_path"] = audio_result["filepath"]
                
                # 上传到飞书
                file_name = f"{safe_word}_sentence_{uuid.uuid4().hex[:8]}.mp3"
                file_info = FeishuFileUtils.upload_file(audio_result["filepath"], file_name)
                
                if file_info:
                    result["feishu_audio_key"] = file_info["file_key"]
                else:
                    logger.warning("上传句子音频到飞书失败")
            else:
                logger.warning("生成句子音频失败")
            
            # 更新状态
            result["status"] = "success"
            return result
            
        except Exception as e:
            logger.error(f"处理句子图片时出错: {e}")
            result["error"] = str(e)
            return result
    
    def _process_essay(self, essay, words, category, voice_type, speed_ratio):
        """处理作文图片和音频"""
        result = {
            "words": words,
            "essay": essay,
            "status": "failed",
            "local_image_path": "",
            "feishu_image_key": "",
            "local_audio_path": "",
            "feishu_audio_key": "",
            "error": None
        }
        
        try:
            # 使用text_to_pic生成作文图片
            save_dir = os.path.join(self.results_dir, "essays")
            if category:
                save_dir = os.path.join(save_dir, category)
            os.makedirs(save_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            words_str = "_".join(words[:3]) + ("_etc" if len(words) > 3 else "")
            safe_words = "".join(c if c.isalnum() else "_" for c in words_str[:30])
            save_filename = f"essay_{safe_words}_{timestamp}.png"
            save_path = os.path.join(save_dir, save_filename)
            
            # 生成标题
            title = f"Essay about: {', '.join(words)}"
            
            # 创建图片
            local_image_path = self.text_to_pic.create_image(
                text=essay,
                title=title,
                output_path=save_path
            )
            
            if not local_image_path:
                error_msg = "生成作文图片失败"
                logger.error(error_msg)
                result["error"] = error_msg
                return result
            
            result["local_image_path"] = local_image_path
            
            # 上传到飞书
            with open(local_image_path, 'rb') as f:
                file_info = FeishuFileUtils.upload_image(f.read(), f"{safe_words}_essay.png")
                
            if file_info and file_info.get("image_key"):
                result["feishu_image_key"] = file_info["image_key"]
            else:
                logger.warning("上传作文图片到飞书失败")
            
            # 生成作文音频
            audio_result = self.tts.text_to_speech(
                text=essay,
                voice_type=voice_type,
                speed_ratio=speed_ratio
            )
            
            if audio_result:
                result["local_audio_path"] = audio_result["filepath"]
                
                # 上传到飞书
                file_name = f"essay_{safe_words}_{uuid.uuid4().hex[:8]}.mp3"
                file_info = FeishuFileUtils.upload_file(audio_result["filepath"], file_name)
                
                if file_info:
                    result["feishu_audio_key"] = file_info["file_key"]
                else:
                    logger.warning("上传作文音频到飞书失败")
            else:
                logger.warning("生成作文音频失败")
            
            # 保存到数据库
            self._save_essay_to_database(result)
            
            # 更新状态
            result["status"] = "success"
            return result
            
        except Exception as e:
            logger.error(f"处理作文时出错: {e}")
            result["error"] = str(e)
            return result
    
    def _save_comprehensive_result(self, result):
        """保存综合处理结果到JSON文件"""
        try:
            # 创建results/comprehensive目录
            save_dir = os.path.join(self.results_dir, "comprehensive")
            os.makedirs(save_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = result.get("timestamp", datetime.now().strftime('%Y%m%d_%H%M%S'))
            category = result.get("category", "default")
            filename = f"comprehensive_{category}_{timestamp}.json"
            filepath = os.path.join(save_dir, filename)
            
            # 保存JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            logger.info(f"综合处理结果已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存综合处理结果时出错: {e}")
            return None
    
    def _save_word_to_database(self, word_result):
        """保存单词处理结果到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            word = word_result["word"]
            category = word_result.get("category")
            
            # 1. 保存单词图片信息
            word_image = word_result.get("word_image", {})
            if word_image and word_image.get("status") == "success":
                cursor.execute('''
                INSERT INTO word_images (
                    word, original_image_url, local_image_path, feishu_image_key, 
                    local_audio_path, feishu_audio_key, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    word,
                    word_image.get("original_image_url", ""),
                    word_image.get("local_image_path", ""),
                    word_image.get("feishu_image_key", ""),
                    word_image.get("local_audio_path", ""),
                    word_image.get("feishu_audio_key", ""),
                    category
                ))
                
                logger.info(f"保存单词图片信息到数据库: {word}")
            
            # 2. 保存句子信息
            sentence_image = word_result.get("sentence_image", {})
            if sentence_image and sentence_image.get("status") == "success":
                cursor.execute('''
                INSERT INTO word_sentences (
                    word, sentence, sentence_image_url, local_image_path, 
                    feishu_image_key, local_audio_path, feishu_audio_key, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    word,
                    sentence_image.get("sentence", ""),
                    sentence_image.get("sentence_image_url", ""),
                    sentence_image.get("local_image_path", ""),
                    sentence_image.get("feishu_image_key", ""),
                    sentence_image.get("local_audio_path", ""),
                    sentence_image.get("feishu_audio_key", ""),
                    category
                ))
                
                logger.info(f"保存句子信息到数据库: {word}")
            
            # 3. 更新内容表
            if (word_image and word_image.get("status") == "success") or \
               (sentence_image and sentence_image.get("status") == "success"):
                
                # 检查是否已有记录
                cursor.execute("SELECT id FROM contents WHERE category = ?", (category,))
                existing = cursor.fetchone()
                
                if existing:
                    # 更新现有记录
                    update_fields = []
                    params = []
                    
                    if word_image and word_image.get("status") == "success":
                        update_fields.extend(["content_image = ?", "content_audio = ?"])
                        params.extend([
                            word_image.get("feishu_image_key", ""),
                            word_image.get("feishu_audio_key", "")
                        ])
                    
                    if sentence_image and sentence_image.get("status") == "success":
                        update_fields.extend(["example_image = ?", "example_audio = ?"])
                        params.extend([
                            sentence_image.get("feishu_image_key", ""),
                            sentence_image.get("feishu_audio_key", "")
                        ])
                    
                    if update_fields:
                        params.append(category)
                        sql = f"UPDATE contents SET {', '.join(update_fields)} WHERE category = ?"
                        cursor.execute(sql, tuple(params))
                        logger.info(f"更新内容表: {category}")
                else:
                    # 插入新记录
                    cursor.execute('''
                    INSERT INTO contents (
                        category, content_image, content_audio, example_image, example_audio
                    ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        category,
                        word_image.get("feishu_image_key", "") if word_image and word_image.get("status") == "success" else "",
                        word_image.get("feishu_audio_key", "") if word_image and word_image.get("status") == "success" else "",
                        sentence_image.get("feishu_image_key", "") if sentence_image and sentence_image.get("status") == "success" else "",
                        sentence_image.get("feishu_audio_key", "") if sentence_image and sentence_image.get("status") == "success" else ""
                    ))
                    logger.info(f"插入内容表: {category}")
            
            conn.commit()
            conn.close()
            logger.info(f"单词 {word} 的处理结果已保存到数据库")
            return True
            
        except Exception as e:
            logger.error(f"保存单词处理结果到数据库时出错: {e}")
            return False
    
    def _save_essay_to_database(self, essay_result):
        """保存作文处理结果到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if essay_result and essay_result.get("status") == "success":
                # 保存作文信息
                cursor.execute('''
                INSERT INTO word_essays (
                    words, essay, local_image_path, feishu_image_key, 
                    local_audio_path, feishu_audio_key, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ",".join(essay_result.get("words", [])),
                    essay_result.get("essay", ""),
                    essay_result.get("local_image_path", ""),
                    essay_result.get("feishu_image_key", ""),
                    essay_result.get("local_audio_path", ""),
                    essay_result.get("feishu_audio_key", ""),
                    essay_result.get("category")
                ))
                
                logger.info(f"保存作文信息到数据库")
                
                # 获取essay_id
                cursor.execute("SELECT last_insert_rowid()")
                essay_id = cursor.fetchone()[0]
                
                # 更新内容表
                category = essay_result.get("category")
                if category:
                    # 检查是否已有记录
                    cursor.execute("SELECT id FROM contents WHERE category = ?", (category,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 更新现有记录
                        cursor.execute('''
                        UPDATE contents 
                        SET essay_image = ?, essay_audio = ?
                        WHERE category = ?
                        ''', (
                            essay_result.get("feishu_image_key", ""),
                            essay_result.get("feishu_audio_key", ""),
                            category
                        ))
                        logger.info(f"更新内容表作文字段: {category}")
                    else:
                        # 插入新记录
                        cursor.execute('''
                        INSERT INTO contents (
                            category, essay_image, essay_audio
                        ) VALUES (?, ?, ?)
                        ''', (
                            category,
                            essay_result.get("feishu_image_key", ""),
                            essay_result.get("feishu_audio_key", "")
                        ))
                        logger.info(f"插入内容表作文字段: {category}")
            
            conn.commit()
            conn.close()
            logger.info("作文处理结果已保存到数据库")
            return True
            
        except Exception as e:
            logger.error(f"保存作文处理结果到数据库时出错: {e}")
            return False


def main():
    """命令行入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="单词综合处理工作流")
    parser.add_argument("words", nargs="+", help="要处理的单词（多个单词用空格分隔）")
    parser.add_argument("--category", "-c", help="单词分类", default="general")
    parser.add_argument("--voice", "-v", choices=["male1", "female1", "male2", "female2"], 
                        help="音频音色", default="female1")
    parser.add_argument("--speed", "-s", type=float, help="语速比例", default=1.0)
    parser.add_argument("--async_mode", "-a", action="store_true", help="是否异步执行Coze工作流")
    
    args = parser.parse_args()
    
    # 音色映射
    voice_mapping = {
        "male1": "BV003_streaming",
        "female1": "BV503_streaming",
        "male2": "BV113_streaming",
        "female2": "BV703_streaming"
    }
    
    voice_type = voice_mapping.get(args.voice, "BV503_streaming")
    
    # 进度回调函数
    def progress_callback(stage, message, progress, word=None):
        if word:
            print(f"[{progress:3d}%] [{stage}] {message} - 当前单词: {word}")
        else:
            print(f"[{progress:3d}%] [{stage}] {message}")
    
    # 创建工作流并执行
    workflow = ComprehensiveWorkflow()
    workflow.set_progress_callback(progress_callback)
    
    print(f"\n===== 开始处理单词: {' '.join(args.words)} =====")
    print(f"分类: {args.category}")
    print(f"音色: {args.voice} ({voice_type})")
    print(f"语速: {args.speed}")
    print(f"执行模式: {'异步' if args.async_mode else '同步'}")
    
    result = workflow.execute(
        input_words=args.words,
        category=args.category,
        voice_type=voice_type,
        speed_ratio=args.speed,
        is_async=args.async_mode
    )
    
    # 打印最终结果
    if result["status"] == "success":
        print("\n===== 处理完成 =====")
        print(f"共处理 {len(result['words'])} 个单词")
        print(f"成功: {result['stats']['success_count']} 个")
        print(f"失败: {result['stats']['failed_count']} 个")
        print(f"总耗时: {result['stats']['elapsed_time']:.2f}秒")
        
        if result.get("essay"):
            print("\n已生成作文图片和音频")
    else:
        print(f"\n===== 处理失败 =====")
        print(f"错误: {result.get('error', '未知错误')}")


if __name__ == "__main__":
    main() 