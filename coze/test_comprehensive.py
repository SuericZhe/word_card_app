#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试综合工作流模块
包括单词->句子->作文->图片->音频的完整过程
"""

import os
import sys
import logging
import json
from datetime import datetime

# 确保可以导入当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from comprehensive_workflow import ComprehensiveWorkflow

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def progress_callback(stage, message, progress, word=None):
    """进度回调函数"""
    progress_data = {
        "stage": stage,
        "message": message,
        "progress": progress,
        "word": word
    }
    logger.info(f"进度更新: {json.dumps(progress_data, ensure_ascii=False)}")

def main():
    """测试综合工作流处理'bus'和'car'两个单词"""
    # 创建测试目录
    test_dir = os.path.join(current_dir, "test_output")
    os.makedirs(test_dir, exist_ok=True)
    
    # 测试单词
    words = ["bus", "car"]
    category = "vehicles"
    learn_date = datetime.now().strftime("%Y-%m-%d")
    voice_type = "BV503_streaming"  # 女声1
    speed_ratio = 1.0
    is_async = True
    
    # 初始化工作流
    logger.info(f"开始测试处理单词: {', '.join(words)}")
    workflow = ComprehensiveWorkflow()
    
    # 设置进度回调
    workflow.set_progress_callback(progress_callback)
    
    # 执行工作流
    result = workflow.execute(
        input_words=words,
        category=category,
        learn_date=learn_date,
        voice_type=voice_type,
        speed_ratio=speed_ratio,
        is_async=is_async
    )
    
    # 输出结果
    logger.info(f"处理完成，结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 保存结果到文件
    result_file = os.path.join(test_dir, "test_result.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已保存到: {result_file}")
    
    return result

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"测试过程中发生错误: {e}") 