#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
coze 模块初始化
提供了一系列处理英文学习内容的工具和接口
"""

# 文本转音频功能
from .text_to_audio import TextToAudio

# 单词到句子工作流
from .word_to_sentence import WordToSentenceWorkflow

# API 客户端
from .coze_api import CozeAPI

# 导出版本信息
__version__ = "0.1.0" 