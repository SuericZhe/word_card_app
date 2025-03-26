#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试综合工作流模块
"""

import sys
import os
import time

# 添加项目根目录到python路径，确保能够正确导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 使用绝对导入
from coze.comprehensive_workflow import ComprehensiveWorkflow

def test_progress_callback(stage, message, progress, word=None):
    """测试进度回调函数"""
    if word:
        print(f"[进度: {progress:3d}%] [{stage}] {message} - 当前单词: {word}")
    else:
        print(f"[进度: {progress:3d}%] [{stage}] {message}")

def main():
    """主测试函数"""
    if len(sys.argv) < 2:
        print("用法: python test_comprehensive_workflow.py <单词1> [单词2 单词3 ...]")
        print("例如: python test_comprehensive_workflow.py apple banana cat")
        return

    # 获取单词列表
    words = sys.argv[1:]
    
    # 设置分类
    category = "test_category"
    
    # 设置音色
    voice_type = "BV503_streaming"  # 女声1
    
    # 设置语速
    speed_ratio = 1.0
    
    # 是否异步执行
    is_async = True
    
    # 打印测试参数
    print("\n===== 测试综合工作流模块 =====")
    print(f"处理单词: {' '.join(words)}")
    print(f"分类: {category}")
    print(f"音色: 女声1 (BV503_streaming)")
    print(f"语速: {speed_ratio}")
    print(f"执行模式: {'异步' if is_async else '同步'}")
    
    # 创建工作流并设置进度回调
    workflow = ComprehensiveWorkflow()
    workflow.set_progress_callback(test_progress_callback)
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行工作流
    result = workflow.execute(
        input_words=words,
        category=category,
        voice_type=voice_type,
        speed_ratio=speed_ratio,
        is_async=is_async
    )
    
    # 记录结束时间
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # 打印结果
    print("\n===== 测试结果 =====")
    print(f"处理状态: {'成功' if result['status'] == 'success' else '失败'}")
    if result["status"] == "success":
        print(f"处理单词数量: {len(result['words'])}")
        print(f"成功: {result['stats']['success_count']} 个")
        print(f"失败: {result['stats']['failed_count']} 个")
        print(f"总耗时: {elapsed_time:.2f}秒")
        
        if result.get("essay"):
            print("\n已生成作文图片和音频:")
            print(f"本地图片路径: {result['essay'].get('local_image_path', '无')}")
            print(f"本地音频路径: {result['essay'].get('local_audio_path', '无')}")
            print(f"飞书图片key: {result['essay'].get('feishu_image_key', '无')}")
            print(f"飞书音频key: {result['essay'].get('feishu_audio_key', '无')}")
            
        # 打印每个单词的处理结果
        print("\n单词处理详情:")
        for i, word_result in enumerate(result["words"]):
            word = word_result["word"]
            status = word_result["status"]
            print(f"\n[{i+1}] 单词: {word} - 状态: {status}")
            
            if status == "success":
                # 单词图片信息
                word_image = word_result.get("word_image", {})
                if word_image and word_image.get("status") == "success":
                    print(f"  单词图片: {word_image.get('local_image_path', '无')}")
                    print(f"  单词音频: {word_image.get('local_audio_path', '无')}")
                
                # 句子图片信息
                sentence_image = word_result.get("sentence_image", {})
                if sentence_image and sentence_image.get("status") == "success":
                    print(f"  例句: {sentence_image.get('sentence', '无')[:50]}...")
                    print(f"  句子图片: {sentence_image.get('local_image_path', '无')}")
                    print(f"  句子音频: {sentence_image.get('local_audio_path', '无')}")
            else:
                print(f"  错误: {word_result.get('error', '未知错误')}")
    else:
        print(f"错误: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    main() 