#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
豆包(字节跳动)语音合成API封装
实现英文文本转为音频文件
"""

import os
import base64
import json
import uuid
import time
import requests
from datetime import datetime

class DouyinTTS:
    """
    豆包(字节跳动)语音合成API封装类
    将文本转换为音频文件
    """
    
    def __init__(self, appid=None, access_token=None, cluster=None, save_dir=None):
        """
        初始化豆包语音合成API客户端
        
        :param appid: 平台申请的appid
        :param access_token: 平台申请的access_token
        :param cluster: 集群名称
        :param save_dir: 音频文件保存目录，默认为 static/audio
        """
        # API配置
        self.appid = appid or "1731405750"
        self.access_token = access_token or "suhgJ_tD_S3Uc2kVW2q1CU0DlwJt1pkt"
        self.cluster = cluster or "volcano_tts"
        self.host = "openspeech.bytedance.com"
        self.api_url = f"https://{self.host}/api/v1/tts"
        
        # 音频保存目录
        self.save_dir = save_dir or os.path.join(os.getcwd(), "static", "audio")
        os.makedirs(self.save_dir, exist_ok=True)
        
    def text_to_speech(self, text, voice_type="BV503_streaming", text_type="plain", 
                      speed_ratio=1.0, volume_ratio=1.0, pitch_ratio=1.0, 
                      encoding="mp3", with_frontend=1):
        """
        将文本转换为音频
        
        :param text: 要转换的文本内容
        :param voice_type: 音色类型，默认BV503_streaming
        :param text_type: 文本类型，默认plain
        :param speed_ratio: 语速比例，默认1.0
        :param volume_ratio: 音量比例，默认1.0
        :param pitch_ratio: 音调比例，默认1.0
        :param encoding: 音频编码格式，默认mp3
        :param with_frontend: 是否使用前端处理，默认1
        :return: 音频文件信息字典
        """
        if not text or not isinstance(text, str):
            print("❌ 文本为空或格式不正确")
            return None
            
        try:
            # 创建安全的文件名
            safe_text = "".join(c if c.isalnum() else "_" for c in text[:20])
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"tts_{safe_text}_{timestamp}_{unique_id}.{encoding}"
            filepath = os.path.join(self.save_dir, filename)
            
            # 请求头
            header = {"Authorization": f"Bearer;{self.access_token}"}
            
            # 构建请求JSON
            request_json = {
                "app": {
                    "appid": self.appid,
                    "token": "access_token",
                    "cluster": self.cluster
                },
                "user": {
                    "uid": "388808087185088"
                },
                "audio": {
                    "voice_type": voice_type,
                    "encoding": encoding,
                    "speed_ratio": speed_ratio,
                    "volume_ratio": volume_ratio,
                    "pitch_ratio": pitch_ratio,
                },
                "request": {
                    "reqid": str(uuid.uuid4()),
                    "text": text,
                    "text_type": text_type,
                    "operation": "query",
                    "with_frontend": with_frontend,
                    "frontend_type": "unitTson"
                }
            }
            
            print(f"\n=== 文本转音频 ===")
            print(f"文本内容: {text[:100]}..." if len(text) > 100 else f"文本内容: {text}")
            print(f"音色类型: {voice_type}")
            print(f"语速比例: {speed_ratio}")
            
            # 发送请求
            start_time = time.time()
            resp = requests.post(self.api_url, json.dumps(request_json), headers=header)
            result = resp.json()
            end_time = time.time()
            
            # 检查请求是否成功
            if resp.status_code != 200:
                print(f"❌ 请求失败，状态码: {resp.status_code}")
                return None
                
            # 处理响应
            if "data" in result:
                # 从响应中提取音频数据
                audio_data = result["data"]
                
                # 解码Base64音频数据并保存
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(audio_data))
                
                print(f"✅ 音频文件已生成: {filepath}")
                print(f"耗时: {end_time - start_time:.2f} 秒")
                
                # 添加时长信息（如果有）
                duration = None
                if "addition" in result and "duration" in result["addition"]:
                    duration = result["addition"]["duration"]
                    print(f"音频时长: {duration}ms")
                
                # 返回相对路径（用于Web访问）
                rel_path = os.path.join("static", "audio", filename)
                return {
                    "text": text,
                    "filename": filename,
                    "filepath": filepath,
                    "url": f"/{rel_path.replace(os.sep, '/')}",
                    "timestamp": timestamp,
                    "voice_type": voice_type,
                    "duration": duration,
                    "speed_ratio": speed_ratio,
                    "volume_ratio": volume_ratio,
                    "pitch_ratio": pitch_ratio
                }
            else:
                # 提取错误信息
                code = result.get("code", -1)
                message = result.get("message", "未知错误")
                print(f"❌ 语音合成失败: 错误码={code}, 错误信息={message}")
                return None
                
        except Exception as e:
            print(f"❌ 转换音频时出错: {str(e)}")
            return None
            
    def save_metadata(self, audio_info):
        """
        保存音频元数据到JSON文件
        
        :param audio_info: 音频文件信息
        :return: 保存的JSON文件路径
        """
        try:
            # 创建结果目录
            results_dir = os.path.join(os.getcwd(), "results", "audio")
            os.makedirs(results_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"tts_meta_{timestamp}.json"
            filepath = os.path.join(results_dir, filename)
            
            # 保存JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(audio_info, f, ensure_ascii=False, indent=2)
                
            print(f"✅ 元数据已保存: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ 保存元数据时出错: {str(e)}")
            return None
            
    def batch_convert(self, text_list, **kwargs):
        """
        批量转换文本到音频
        
        :param text_list: 文本列表
        :param kwargs: 其他参数，与text_to_speech相同
        :return: 结果列表
        """
        results = []
        
        for i, text in enumerate(text_list):
            print(f"\n处理 [{i+1}/{len(text_list)}]: {text[:50]}..." if len(text) > 50 else f"\n处理 [{i+1}/{len(text_list)}]: {text}")
            
            result = self.text_to_speech(text=text, **kwargs)
            
            if result:
                results.append(result)
                
        return results

# 使用示例
def test_douyin_tts():
    # 创建TTS实例
    tts = DouyinTTS()
    
    # 测试英文转音频
    result = tts.text_to_speech(
        text="Hello, this is a test for text to speech conversion using Douyin API.",
        voice_type="BV503_streaming",  # 英文女声
        speed_ratio=1.0
    )
    
    if result:
        print(f"生成的音频文件: {result['filepath']}")
    
if __name__ == "__main__":
    test_douyin_tts() 