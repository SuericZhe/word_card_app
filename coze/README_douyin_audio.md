# 豆包语音合成API使用指南

本文档介绍如何使用豆包（抖音）语音合成API将文本转换为语音，并提供相关工具的使用方法。

## 功能特点

- 支持英文文本转语音
- 支持多种音色选择
- 支持调整语速、音量和音调
- 提供命令行工具和API接口
- 与单词到句子工作流无缝集成
- 生成MP3格式的音频文件

## 目录结构

```
coze/
  ├── douyin_tts.py         # 豆包TTS API核心类
  ├── douyin_tts_cli.py     # 命令行工具
  └── word_sentence_audio.py # 单词到句子+音频工具
```

## 前提条件

- Python 3.6+
- 必要的库：requests, base64, json, os
- 已配置的豆包API凭证（已在代码中内置）

## 使用方法

### 1. 简单的文本到语音转换

使用命令行工具快速将文本转换为语音：

```bash
python coze/douyin_tts_cli.py
```

运行后，根据提示输入文本和参数即可生成语音文件。

### 2. 从单词生成例句并转换为语音

结合单词到句子工作流，自动生成例句和作文并转换为语音：

```bash
python coze/word_sentence_audio.py apple banana
```

或者不带参数运行，根据提示输入：

```bash
python coze/word_sentence_audio.py
```

### 3. 在Python代码中使用

```python
from coze.douyin_tts import DouyinTTS

# 创建TTS实例
tts = DouyinTTS()

# 基本用法
result = tts.text_to_speech("Hello world")
if result:
    print(f"音频文件保存到: {result['filepath']}")

# 高级用法（自定义参数）
result = tts.text_to_speech(
    text="Hello world",
    voice_type="BV503_streaming",  # 女声1
    speed_ratio=1.2,               # 语速比例
    volume_ratio=1.0,              # 音量比例
    pitch_ratio=1.0                # 音调比例
)
```

## 参数说明

### text_to_speech方法参数

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| text | str | 必填 | 要转换为语音的文本 |
| voice_type | str | BV503_streaming | 音色类型，见下表 |
| speed_ratio | float | 1.0 | 语速比例，范围0.5-2.0 |
| volume_ratio | float | 1.0 | 音量比例，范围0.5-2.0 |
| pitch_ratio | float | 1.0 | 音调比例，范围0.5-2.0 |
| save_dir | str | None | 自定义保存目录，默认为static/audio |

### 支持的音色类型

| 音色ID | 说明 |
|-------|------|
| BV003_streaming | 男声1 |
| BV503_streaming | 女声1 |
| BV113_streaming | 男声2 |
| BV703_streaming | 女声2 |

## 音频文件管理

- 默认情况下，音频文件保存在`static/audio`目录下
- 文件名格式为：`douyin_tts_{随机字符串}.mp3`
- 每次生成的音频都会保存为新文件
- 元数据可选择性保存在`results/word_audio`目录下

## 工作原理

1. 构造API请求参数，包括文本内容、音色类型和各种参数
2. 发送POST请求到豆包TTS API
3. 解析返回的JSON数据，提取base64编码的音频数据
4. 解码base64数据并保存为MP3文件
5. 返回生成的音频文件路径和URL

## 常见问题

### 1. 音频质量不佳

尝试调整以下参数：
- 增大`volume_ratio`提高音量
- 调整`pitch_ratio`更改音调
- 减小`speed_ratio`使语音更清晰

### 2. API请求失败

可能的原因：
- 网络连接问题
- API凭证过期或无效
- 请求参数格式错误

### 3. 中文文本支持

当前版本主要针对英文文本优化，对中文的支持可能不完善。建议使用百度翻译API的语音合成功能处理中文文本。

## 结合单词到句子工作流

`word_sentence_audio.py`工具提供以下功能：

1. 输入英文单词
2. 自动生成例句和相关作文
3. 将生成的内容转换为语音
4. 保存音频文件和元数据

使用示例：

```bash
python coze/word_sentence_audio.py science technology
```

输出内容包括：
- 针对每个单词的例句
- 综合使用所有单词的短文
- 所有内容的对应音频文件 