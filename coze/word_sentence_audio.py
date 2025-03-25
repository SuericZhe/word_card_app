#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
结合单词到句子工作流和豆包语音合成API
为生成的例句和作文提供音频
"""

import sys
import time
import json
import os
from word_to_sentence import WordToSentenceWorkflow
from douyin_tts import DouyinTTS

def main():
    print("=" * 50)
    print("英语单词 -> 例句+作文 -> 语音合成工具")
    print("=" * 50)
    print("输入英文单词，自动生成例句和作文，并提供音频")
    print("=" * 50)
    
    # 获取用户输入
    if len(sys.argv) > 1:
        # 从命令行参数获取单词
        words = " ".join(sys.argv[1:])
    else:
        # 从用户输入获取单词
        words = input("请输入英文单词(多个单词用空格分隔): ")
    
    if not words.strip():
        print("未输入单词，程序退出")
        return
    
    # 初始化工作流和TTS
    word_flow = WordToSentenceWorkflow()
    tts = DouyinTTS()
    
    # 步骤1: 生成例句和作文
    print("\n=== 步骤1: 生成单词的例句和作文 ===")
    start_time = time.time()
    sentence_result = word_flow.execute(words)
    step1_time = time.time() - start_time
    
    if not sentence_result:
        print("❌ 生成例句和作文失败，程序退出")
        return
        
    # 显示生成的例句
    print(f"\n--- 生成的例句 (用时: {step1_time:.2f}秒) ---")
    for sentence in sentence_result.get("sentences", []):
        print(f"- {sentence.get('word')}: {sentence.get('sentence')}")
        
    # 显示生成的作文
    print("\n--- 生成的作文 ---")
    essay_text = sentence_result.get("essay", "无作文")
    print(essay_text)
    
    # 询问是否要继续生成音频
    continue_audio = input("\n是否为例句和作文生成音频？(y/n，默认y): ").strip().lower() != 'n'
    if not continue_audio:
        print("\n程序结束，感谢使用！")
        return
    
    # 询问生成的内容类型
    print("\n要为哪些内容生成音频？")
    print("1. 单词音频")
    print("2. 例句音频")
    print("3. 作文音频")
    print("4. 全部")
    content_choice = input("请选择 [1-4，默认4]: ").strip() or "4"
    
    # 音色选择
    print("\n请选择音色:")
    print("1. 男声1 (BV003_streaming)")
    print("2. 女声1 (BV503_streaming)")
    print("3. 男声2 (BV113_streaming)")
    print("4. 女声2 (BV703_streaming)")
    voice_choice = input("请选择 [1-4，默认2]: ").strip() or "2"
    
    # 获取音色ID
    voice_mapping = {
        "1": "BV003_streaming",
        "2": "BV503_streaming",
        "3": "BV113_streaming",
        "4": "BV703_streaming"
    }
    voice_type = voice_mapping.get(voice_choice, "BV503_streaming")
    
    # 语速选择
    speed_input = input("\n请输入语速比例 [0.5-2.0，默认1.0]: ").strip() or "1.0"
    try:
        speed_ratio = float(speed_input)
        speed_ratio = max(0.5, min(2.0, speed_ratio))
    except:
        speed_ratio = 1.0
        print("输入的语速无效，将使用默认值1.0")
    
    # 收集结果
    audio_results = {
        "words": [],
        "sentences": [],
        "essay": None,
        "timestamp": time.strftime("%Y%m%d%H%M%S")
    }
    
    # 步骤2: 为选择的内容生成音频
    if content_choice in ["1", "4"]:  # 单词音频
        print("\n=== 步骤2.1: 为单词生成音频 ===")
        words_list = sentence_result.get("input_words", [])
        if isinstance(words_list, str):
            words_list = words_list.split()
            
        for i, word in enumerate(words_list):
            print(f"\n处理单词 {i+1}/{len(words_list)}: {word}")
            
            # 生成音频
            result = tts.text_to_speech(
                text=word,
                voice_type=voice_type,
                speed_ratio=speed_ratio
            )
            
            if result:
                audio_results["words"].append({
                    "word": word,
                    "audio_file": result["filepath"],
                    "audio_url": result["url"]
                })
                print(f"✅ 音频生成成功: {result['filepath']}")
            else:
                print(f"❌ 音频生成失败: {word}")
    
    if content_choice in ["2", "4"]:  # 例句音频
        print("\n=== 步骤2.2: 为例句生成音频 ===")
        
        for i, sentence_info in enumerate(sentence_result.get("sentences", [])):
            word = sentence_info.get("word", "")
            sentence = sentence_info.get("sentence", "")
            
            if not sentence:
                continue
                
            print(f"\n处理例句 {i+1}/{len(sentence_result.get('sentences', []))}: {word}")
            
            # 生成音频
            result = tts.text_to_speech(
                text=sentence,
                voice_type=voice_type,
                speed_ratio=speed_ratio
            )
            
            if result:
                audio_results["sentences"].append({
                    "word": word,
                    "sentence": sentence,
                    "audio_file": result["filepath"],
                    "audio_url": result["url"]
                })
                print(f"✅ 音频生成成功: {result['filepath']}")
            else:
                print(f"❌ 音频生成失败: {sentence}")
    
    if content_choice in ["3", "4"] and essay_text and essay_text != "无作文":  # 作文音频
        print("\n=== 步骤2.3: 为作文生成音频 ===")
        
        # 生成音频
        result = tts.text_to_speech(
            text=essay_text,
            voice_type=voice_type,
            speed_ratio=speed_ratio
        )
        
        if result:
            audio_results["essay"] = {
                "essay": essay_text,
                "audio_file": result["filepath"],
                "audio_url": result["url"]
            }
            print(f"✅ 作文音频生成成功: {result['filepath']}")
        else:
            print("❌ 作文音频生成失败")
    
    # 步骤3: 保存结果元数据
    print("\n=== 步骤3: 保存结果元数据 ===")
    
    save_meta = input("是否保存结果元数据？(y/n，默认y): ").strip().lower() != 'n'
    if save_meta:
        try:
            # 创建结果目录
            results_dir = os.path.join(os.getcwd(), "results", "word_audio")
            os.makedirs(results_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = time.strftime("%Y%m%d%H%M%S")
            filename = f"word_audio_result_{timestamp}.json"
            filepath = os.path.join(results_dir, filename)
            
            # 合并结果
            full_result = {
                "input_words": sentence_result.get("input_words", []),
                "audio_results": audio_results,
                "timestamp": timestamp
            }
            
            # 保存JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(full_result, f, ensure_ascii=False, indent=2)
                
            print(f"✅ 元数据已保存: {filepath}")
        except Exception as e:
            print(f"❌ 保存元数据时出错: {str(e)}")
    
    # 总结
    word_count = len(audio_results["words"])
    sentence_count = len(audio_results["sentences"])
    essay_count = 1 if audio_results["essay"] else 0
    total_count = word_count + sentence_count + essay_count
    
    print("\n=== 处理完成 ===")
    print(f"生成了 {total_count} 个音频文件:")
    print(f"- 单词音频: {word_count} 个")
    print(f"- 例句音频: {sentence_count} 个")
    print(f"- 作文音频: {essay_count} 个")
    print("音频文件保存在 static/audio 目录下")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已中断程序")
    except Exception as e:
        print(f"\n程序出错: {str(e)}") 