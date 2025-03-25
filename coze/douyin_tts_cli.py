#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单的豆包文本转语音命令行工具
支持多种语音风格和调整参数
"""

import sys
from douyin_tts import DouyinTTS

# 音色类型列表
VOICE_TYPES = {
    "1": {"id": "BV003_streaming", "desc": "男声1"},
    "2": {"id": "BV503_streaming", "desc": "女声1"},
    "3": {"id": "BV113_streaming", "desc": "男声2"},
    "4": {"id": "BV703_streaming", "desc": "女声2"},
}

def main():
    print("=" * 50)
    print("豆包(字节跳动)文本转语音工具")
    print("=" * 50)
    print("将文本转换为高质量的语音文件")
    print("=" * 50)
    
    # 创建TTS实例
    tts = DouyinTTS()
    
    # 从命令行获取文本
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        print(f"从命令行获取文本: {text}")
        interactive_mode = False
    else:
        interactive_mode = True
    
    while True:
        if interactive_mode:
            # 获取用户输入
            text = input("\n请输入要转换的文本 (输入'exit'退出): ")
            
            # 检查是否退出
            if text.lower() == 'exit':
                print("\n感谢使用，再见！")
                break
                
            if not text.strip():
                print("文本不能为空，请重新输入")
                continue
                
            # 选择音色
            print("\n请选择音色:")
            for key, voice in VOICE_TYPES.items():
                print(f"{key}. {voice['desc']}")
            voice_choice = input("请选择 [1-4，默认2]: ").strip() or "2"
            
            # 获取音色ID
            voice_type = VOICE_TYPES.get(voice_choice, VOICE_TYPES["2"])["id"]
            
            # 选择语速
            speed_input = input("\n请输入语速比例 [0.5-2.0，默认1.0]: ").strip() or "1.0"
            try:
                speed_ratio = float(speed_input)
                speed_ratio = max(0.5, min(2.0, speed_ratio))  # 限制在0.5-2.0之间
            except:
                speed_ratio = 1.0
                print("输入的语速无效，将使用默认值1.0")
            
            # 选择音量
            volume_input = input("\n请输入音量比例 [0.5-2.0，默认1.0]: ").strip() or "1.0"
            try:
                volume_ratio = float(volume_input)
                volume_ratio = max(0.5, min(2.0, volume_ratio))  # 限制在0.5-2.0之间
            except:
                volume_ratio = 1.0
                print("输入的音量无效，将使用默认值1.0")
                
            # 选择音调
            pitch_input = input("\n请输入音调比例 [0.5-2.0，默认1.0]: ").strip() or "1.0"
            try:
                pitch_ratio = float(pitch_input)
                pitch_ratio = max(0.5, min(2.0, pitch_ratio))  # 限制在0.5-2.0之间
            except:
                pitch_ratio = 1.0
                print("输入的音调无效，将使用默认值1.0")
        else:
            # 命令行模式使用默认值
            voice_type = "BV503_streaming"  # 默认女声
            speed_ratio = 1.0
            volume_ratio = 1.0
            pitch_ratio = 1.0
        
        # 显示处理信息
        print("\n正在处理，请稍候...")
        
        # 调用TTS API
        result = tts.text_to_speech(
            text=text,
            voice_type=voice_type,
            speed_ratio=speed_ratio,
            volume_ratio=volume_ratio,
            pitch_ratio=pitch_ratio
        )
        
        # 显示结果
        if result:
            print("\n✅ 音频生成成功!")
            print(f"文件路径: {result['filepath']}")
            
            # 询问是否保存元数据
            if interactive_mode:
                save_meta = input("\n是否保存元数据？(y/n，默认n): ").strip().lower() == 'y'
                if save_meta:
                    meta_path = tts.save_metadata(result)
                    if meta_path:
                        print(f"元数据已保存: {meta_path}")
        else:
            print("\n❌ 音频生成失败，请检查输入或网络连接")
        
        # 如果是命令行模式，处理一次后退出
        if not interactive_mode:
            break
            
        print("\n" + "=" * 50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已中断")
    except Exception as e:
        print(f"\n程序出错: {str(e)}") 