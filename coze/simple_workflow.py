#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简化版综合工作流测试
仅测试单词到句子和作文部分
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger('SimpleWorkflow')

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

# 直接导入word_to_sentence模块
from coze.word_to_sentence import WordToSentenceWorkflow

class SimpleWorkflow:
    """
    简化版的综合工作流，仅包含单词到句子和作文的部分
    """
    
    def __init__(self, save_results=True):
        self.save_results = save_results
        self.word_to_sentence_workflow = WordToSentenceWorkflow(save_results=save_results)
        
    def execute(self, input_words, is_async=True):
        """
        执行工作流
        
        参数:
            input_words: 输入的单词列表或空格分隔的单词字符串
            is_async: 是否异步执行Coze工作流，默认为True
            
        返回:
            处理结果字典
        """
        # 初始化结果
        result = {
            "status": "success",
            "sentences": [],
            "essay": "",
            "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S'),
            "error": None
        }
        
        # 确保单词列表格式正确
        if isinstance(input_words, str):
            input_words = input_words.strip().split()
        
        try:
            # 步骤1: 生成例句和作文
            logger.info(f"为 {len(input_words)} 个单词生成例句和作文")
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
            result["sentences"] = word_to_sentence_result.get("sentences", [])
            result["essay"] = word_to_sentence_result.get("essay", "")
            
            # 保存结果
            if self.save_results:
                self._save_result(result)
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            logger.error(f"处理过程中发生错误: {error_msg}")
            logger.error(traceback.format_exc())
            result["status"] = "failed"
            result["error"] = error_msg
            return result
    
    def _save_result(self, result):
        """保存结果到文件"""
        try:
            # 创建results目录
            if not os.path.exists("results"):
                os.makedirs("results")
            
            # 生成文件名
            timestamp = result.get("timestamp", datetime.now().strftime('%Y%m%d_%H%M%S'))
            filename = f"results/simple_workflow_{timestamp}.json"
            
            # 保存JSON
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            logger.info(f"结果已保存到: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"保存结果时出错: {e}")
            return None

def main():
    """主函数"""
    if len(sys.argv) > 1:
        words = sys.argv[1:]
    else:
        words = ["apple", "bird"]  # 默认测试单词
    
    print(f"\n===== 简化版工作流测试 =====")
    print(f"处理单词: {' '.join(words)}")
    
    # 创建工作流
    workflow = SimpleWorkflow()
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行工作流
    print("\n开始执行工作流...")
    result = workflow.execute(words)
    
    # 计算执行时间
    elapsed_time = time.time() - start_time
    
    # 打印结果
    print(f"\n===== 工作流执行结果 =====")
    print(f"状态: {'成功' if result['status'] == 'success' else '失败'}")
    
    if result["status"] == "success":
        print("\n例句:")
        for item in result["sentences"]:
            print(f"- {item.get('word')}: {item.get('sentence')}")
        
        print("\n作文:")
        print(result["essay"])
    else:
        print(f"错误: {result.get('error', '未知错误')}")
    
    print(f"\n总执行时间: {elapsed_time:.2f} 秒")

if __name__ == "__main__":
    main() 