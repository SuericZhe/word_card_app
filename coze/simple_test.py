#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单测试脚本 - 测试单词到句子和作文功能
"""

import os
import sys
import time
import json

# 添加当前目录到系统路径，确保可以导入本地模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

try:
    # 尝试导入word_to_sentence模块
    from coze.word_to_sentence import WordToSentenceWorkflow
    print("✅ 成功导入WordToSentenceWorkflow")
except Exception as e:
    print(f"❌ 导入WordToSentenceWorkflow失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def main():
    """测试单词到句子和作文功能"""
    if len(sys.argv) > 1:
        words = sys.argv[1:]
    else:
        words = ["apple", "bird"]  # 默认测试单词
    
    print(f"\n===== 测试单词到句子功能 =====")
    print(f"处理单词: {' '.join(words)}")
    
    # 创建工作流
    try:
        workflow = WordToSentenceWorkflow()
        print("✅ 成功创建WordToSentenceWorkflow实例")
    except Exception as e:
        print(f"❌ 创建WordToSentenceWorkflow实例失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行工作流
    try:
        print("\n开始执行工作流...")
        result = workflow.execute(words)
        
        if not result:
            print("❌ 工作流执行失败，未返回结果")
            return
        
        # 处理结果
        print("\n===== 工作流执行结果 =====")
        
        # 显示句子
        if "sentences" in result and result["sentences"]:
            print("\n例句:")
            for sentence in result["sentences"]:
                print(f"- {sentence.get('word')}: {sentence.get('sentence')}")
        else:
            print("❌ 未生成例句")
        
        # 显示作文
        if "essay" in result and result["essay"]:
            print("\n作文:")
            print(result["essay"])
        else:
            print("❌ 未生成作文")
        
        # 计算执行时间
        elapsed_time = time.time() - start_time
        print(f"\n总执行时间: {elapsed_time:.2f} 秒")
        
        # 尝试保存结果
        try:
            # 创建结果目录
            if not os.path.exists("results"):
                os.makedirs("results")
            
            # 生成文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            result_file = f"results/simple_test_{timestamp}.json"
            
            # 保存JSON
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 结果已保存到: {result_file}")
        except Exception as e:
            print(f"❌ 保存结果失败: {e}")
    
    except Exception as e:
        print(f"❌ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 