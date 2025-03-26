#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试综合工作流模块
包括单词->句子->作文->图片->音频的完整过程
"""

import os
import sys
import time
import json

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

try:
    # 导入综合工作流模块
    from coze.comprehensive_workflow import ComprehensiveWorkflow
    print("✅ 成功导入ComprehensiveWorkflow")
except Exception as e:
    print(f"❌ 导入ComprehensiveWorkflow失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def progress_callback(stage, message, progress, word=None):
    """进度回调函数"""
    if word:
        print(f"[进度: {progress:3d}%] [{stage}] {message} - 当前单词: {word}")
    else:
        print(f"[进度: {progress:3d}%] [{stage}] {message}")

def main():
    """测试综合工作流功能"""
    if len(sys.argv) > 1:
        words = sys.argv[1:]
    else:
        words = ["apple", "bird"]  # 默认测试单词
    
    print(f"\n===== 测试综合工作流 =====")
    print(f"处理单词: {' '.join(words)}")
    
    # 设置参数
    category = "test_comprehensive"
    voice_type = "BV503_streaming"  # 女声1
    speed_ratio = 1.0
    is_async = True
    
    print(f"分类: {category}")
    print(f"音色: 女声1 (BV503_streaming)")
    print(f"语速: {speed_ratio}")
    print(f"执行模式: {'异步' if is_async else '同步'}")
    
    # 创建工作流
    try:
        workflow = ComprehensiveWorkflow()
        workflow.set_progress_callback(progress_callback)
        print("✅ 成功创建ComprehensiveWorkflow实例")
    except Exception as e:
        print(f"❌ 创建ComprehensiveWorkflow实例失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行工作流
    try:
        print("\n开始执行综合工作流...")
        result = workflow.execute(
            input_words=words,
            category=category,
            voice_type=voice_type,
            speed_ratio=speed_ratio,
            is_async=is_async
        )
        
        if not result:
            print("❌ 工作流执行失败，未返回结果")
            return
        
        # 处理结果
        print("\n===== 工作流执行结果 =====")
        print(f"处理状态: {'成功' if result['status'] == 'success' else '失败'}")
        
        if result["status"] == "success":
            print(f"处理单词数量: {len(result['words'])}")
            print(f"成功: {result['stats']['success_count']} 个")
            print(f"失败: {result['stats']['failed_count']} 个")
            
            # 打印作文信息
            if result.get("essay"):
                print("\n已生成作文资源:")
                print(f"本地图片路径: {result['essay'].get('local_image_path', '无')}")
                print(f"本地音频路径: {result['essay'].get('local_audio_path', '无')}")
                print(f"飞书图片key: {result['essay'].get('feishu_image_key', '无')}")
                print(f"飞书音频key: {result['essay'].get('feishu_audio_key', '无')}")
            
            # 打印单词处理结果
            print("\n单词资源生成详情:")
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
        
        # 计算执行时间
        elapsed_time = time.time() - start_time
        print(f"\n总执行时间: {elapsed_time:.2f} 秒")
        
    except Exception as e:
        print(f"❌ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 