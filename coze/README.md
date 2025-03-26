# 单词卡片应用 - Coze 模块说明

本目录包含单词卡片应用的核心功能模块，基于Coze API、飞书API和豆包TTS等服务实现。各模块相互独立，可以单独使用或组合使用。

## 核心工作流模块

### 1. 单词处理工作流

- **word_to_sentence.py**: 将单词转换为例句和短文
  - 输入英文单词，生成每个单词的例句和相关短文
  - 使用Coze AI平台进行句子生成

- **word_to_image.py**: 将单词转换为图片
  - 输入英文单词，生成描述该单词的图片URL
  - 通过Coze AI平台调用图像生成服务

- **word_to_audio.py**: 将单词转换为音频
  - 输入英文单词，生成单词的音频文件
  - 基于豆包TTS API实现语音合成
  - 自动上传音频到飞书获取file_key

- **sentence_to_image.py**: 将句子转换为图片
  - 输入英文句子，生成与句子相关的图片URL
  - 与word_to_image类似，但接受句子作为输入

### 2. 集成与处理模块

- **generate_and_caption_image.py**: 单词图像生成与处理工具
  - 集成了图片生成、文字标注、音频生成和文件上传功能
  - 管理单词的多媒体资源（图片和音频）
  - 处理后的数据存储到SQLite数据库

- **word_sentence_audio.py**: 单词句子音频处理工具
  - 结合单词到句子工作流和豆包语音合成API
  - 为生成的例句和作文提供音频

### 3. 音频处理模块

- **douyin_tts.py**: 豆包(字节跳动)语音合成API封装
  - 实现文本到音频的转换功能
  - 支持不同的音色、语速和音量配置

- **douyin_tts_cli.py**: 豆包TTS命令行工具
  - 提供命令行接口访问TTS功能

### 4. 图像处理模块

- **add_text_to_pic.py**: 图片添加文字工具
  - 在图片底部添加字幕样式的文字
  - 支持本地图片或URL图片处理
  - 可选自动上传到飞书

## 飞书集成模块

### 1. 图片工具

- **feishu_image_utils.py**: 飞书图片工具类
  - 提供上传/下载图片到飞书的功能
  - 通过飞书开放API实现

- **feishu_image_example.py**: 飞书图片工具示例
  - 演示如何使用飞书图片工具上传下载图片

### 2. 文件工具

- **feishu_file_utils.py**: 飞书文件工具类
  - 提供上传/下载各种类型文件到飞书的功能
  - 支持音频、图片、文档等多种文件类型

- **feishu_file_up.py**: 飞书文件上传工具
  - 简化的文件上传命令行工具

- **feishu_file_down.py**: 飞书文件下载工具
  - 简化的文件下载命令行工具

- **feishu_file_manager.py**: 飞书文件管理器
  - 提供完整的文件管理功能，包括上传、下载、删除等

## 基础设施模块

- **coze_api.py**: Coze API客户端
  - 封装了与Coze平台交互的核心功能
  - 支持执行工作流、轮询结果和保存结果

- **config.py**: 配置文件
  - 存储API密钥、工作流ID和其他配置参数
  - 用于所有需要API访问的模块

- **__init__.py**: 模块初始化文件
  - 定义模块导出内容
  - 提供版本信息

## 文档

- **README_douyin_audio.md**: 豆包语音API使用说明
  - 详细介绍豆包TTS API的使用方法和示例

## 使用示例

### 单词到图片+音频处理流程

```python
from coze.generate_and_caption_image import ImageProcessor

# 创建处理器
processor = ImageProcessor()

# 处理单词，生成图片和音频并上传到飞书
result = processor.generate_and_process_image(
    word="elephant",      # 要处理的单词
    category="animal",    # 可选分类
    voice_type="BV503_streaming",  # 音频音色
    speed_ratio=1.0       # 语速比例
)

# 查看处理结果
if result["status"] == "success":
    print(f"本地图片路径: {result['local_image_path']}")
    print(f"飞书图片Key: {result['feishu_image_key']}")
    print(f"本地音频路径: {result['local_audio_path']}")
    print(f"飞书音频Key: {result['feishu_audio_key']}")
```

### 单词生成音频示例

```python
from coze.word_to_audio import WordToAudioWorkflow

# 创建工作流
workflow = WordToAudioWorkflow()

# 执行单词到音频转换
result = workflow.execute(
    input_word="hello",
    voice_type="BV503_streaming",  # 女声
    speed_ratio=1.0
)

# 输出结果
print(f"本地音频路径: {result['local_audio_path']}")
print(f"飞书文件Key: {result['feishu_file_key']}")
```

### 图片添加文字示例

```python
from coze.add_text_to_pic import add_text_and_upload_to_feishu

# 处理图片并上传到飞书
image_key = add_text_and_upload_to_feishu(
    image_source="https://example.com/image.jpg",  # 图片URL或本地路径
    text="Hello World",  # 要添加的文字
    font_size_percentage=0.06  # 字体大小百分比
)

print(f"飞书图片Key: {image_key}")
```