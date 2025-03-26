#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
实现单词到音频的工作流处理
为单词生成音频文件，并上传到飞书
"""

import os
import sys
import json
from datetime import datetime
import time
import uuid
from coze.douyin_tts import DouyinTTS
from coze.feishu_file_utils import FeishuFileUtils

class WordToAudioWorkflow:
    """
    实现单词到音频的工作流处理
    
    这个工作流接收单词作为输入，然后返回:
    1. 单词的音频文件本地路径
    2. 单词的音频文件飞书file_key
    """
    
    def __init__(self, save_results=True):
        """
        初始化单词到音频工作流处理器
        
        :param save_results: 是否保存结果，默认为True
        """
        self.tts = DouyinTTS()
        self.save_results = save_results
        
    def execute(self, input_word, voice_type="BV503_streaming", 
                speed_ratio=1.0, volume_ratio=1.0, pitch_ratio=1.0):
        """
        执行工作流，将单词转换为音频
        
        :param input_word: 输入的英文单词
        :param voice_type: 音色类型，默认BV503_streaming（女声）
        :param speed_ratio: 语速比例，默认1.0
        :param volume_ratio: 音量比例，默认1.0
        :param pitch_ratio: 音调比例，默认1.0
        :return: 处理结果，包含本地音频路径和飞书file_key
        """
        # 初始化结果
        result = {
            "word": input_word,
            "status": "failed",
            "local_audio_path": "",
            "feishu_file_key": "",
            "audio_duration": None,
            "voice_type": voice_type,
            "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S'),
            "error": None
        }
        
        try:
            # 确保输入为字符串
            if not isinstance(input_word, str):
                input_word = str(input_word)
                
            print(f"\n=== 执行单词到音频工作流 ===")
            print(f"输入单词: {input_word}")
            print(f"音色类型: {voice_type}")
            print(f"语速比例: {speed_ratio}")
            
            # 步骤1: 将单词转换为音频
            print(f"\n[步骤1] 将单词 '{input_word}' 转换为音频...")
            audio_result = self.tts.text_to_speech(
                text=input_word,
                voice_type=voice_type,
                speed_ratio=speed_ratio,
                volume_ratio=volume_ratio,
                pitch_ratio=pitch_ratio
            )
            
            if not audio_result:
                error_msg = "生成音频失败"
                print(f"错误: {error_msg}")
                result["error"] = error_msg
                return result
                
            # 提取音频信息
            local_audio_path = audio_result["filepath"]
            audio_duration = audio_result.get("duration")
            
            result["local_audio_path"] = local_audio_path
            result["audio_duration"] = audio_duration
            
            print(f"音频生成成功: {local_audio_path}")
            if audio_duration:
                print(f"音频时长: {audio_duration}ms")
                
            # 步骤2: 上传音频到飞书
            print(f"\n[步骤2] 上传音频到飞书...")
            
            file_name = f"{input_word}_{uuid.uuid4().hex[:8]}.mp3"
            file_info = FeishuFileUtils.upload_file(local_audio_path, file_name)
            
            if not file_info:
                error_msg = "上传音频到飞书失败"
                print(f"错误: {error_msg}")
                result["error"] = error_msg
                return result
                
            result["feishu_file_key"] = file_info["file_key"]
            print(f"上传成功，file_key: {file_info['file_key']}")
            
            # 处理成功
            result["status"] = "success"
            
            # 保存结果
            if self.save_results:
                self._save_result(result)
                
            print(f"\n✅ 单词 '{input_word}' 处理完成!")
            print(f"本地音频路径: {local_audio_path}")
            print(f"飞书文件key: {result['feishu_file_key']}")
            
            return result
            
        except Exception as e:
            import traceback
            print(f"\n❌ 处理过程中发生错误: {str(e)}")
            traceback.print_exc()
            result["error"] = str(e)
            return result
    
    def _save_result(self, result):
        """
        保存处理结果到JSON文件
        :param result: 处理结果
        :return: 保存的文件路径
        """
        try:
            # 创建results目录（如果不存在）
            results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "word_audio")
            os.makedirs(results_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = result["timestamp"]
            word = result["word"]
            filename = f"word_audio_{word}_{timestamp}.json"
            filepath = os.path.join(results_dir, filename)
            
            # 保存JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
            print(f"\n结果已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"保存结果时出错: {e}")
            return None


def main():
    """命令行入口函数"""
    import sys
    
    # 打印使用说明
    if len(sys.argv) < 2 or "--help" in sys.argv or "-h" in sys.argv:
        print("""单词到音频转换工具

用法:
    python word_to_audio.py <单词> [音色类型] [语速比例]
    
参数:
    单词:     要转换的英文单词
    音色类型:  可选，音色类型，默认女声BV503_streaming
              可选值: BV003_streaming（男声1）、BV503_streaming（女声1）
                    BV113_streaming（男声2）、BV703_streaming（女声2）
    语速比例:  可选，语速比例，默认1.0
    
示例:
    python word_to_audio.py apple
    python word_to_audio.py elephant BV003_streaming 0.8
        """)
        sys.exit(0)
    
    # 获取参数
    word = sys.argv[1]
    voice_type = sys.argv[2] if len(sys.argv) > 2 else "BV503_streaming"
    speed_ratio = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    
    # 创建工作流并执行
    workflow = WordToAudioWorkflow()
    result = workflow.execute(word, voice_type, speed_ratio)
    
    # 打印最终结果
    if result["status"] == "success":
        print("\n===== 处理结果 =====")
        print(f"单词: {result['word']}")
        print(f"本地音频路径: {result['local_audio_path']}")
        print(f"飞书文件Key: {result['feishu_file_key']}")
        if result["audio_duration"]:
            print(f"音频时长: {result['audio_duration']}ms")
    else:
        print(f"\n❌ 处理失败: {result['error']}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        # 直接运行脚本时的示例
        workflow = WordToAudioWorkflow()
        result = workflow.execute("hello")
        print(json.dumps(result, indent=2, ensure_ascii=False)) 