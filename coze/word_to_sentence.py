#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
from datetime import datetime
import time
import signal

# 确保能够导入同级目录模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from coze_api import CozeAPI
import config as config

class WordToSentenceWorkflow:
    """
    实现单词到句子和作文的Coze工作流处理
    
    这个工作流接收单词列表作为输入，然后返回:
    1. 每个单词的例句
    2. 使用这些单词的英文作文
    """
    
    def __init__(self, personal_token=None, workflow_id=None, space_id=None, save_results=True):
        """
        初始化单词到句子工作流处理器
        
        :param personal_token: Coze API的个人访问令牌
        :param workflow_id: 工作流ID
        :param space_id: 空间ID
        :param save_results: 是否保存中间结果，默认为True
        """
        self.space_id = space_id or config.SPACE_ID
        self.api = CozeAPI(personal_token or config.PERSONAL_TOKEN, self.space_id)
        self.workflow_id = workflow_id or config.WORKFLOW_IDS["word_to_sentence"]
        self.save_results = save_results
        # 中断标志
        self.interrupted = False
        
    def signal_handler(self, sig, frame):
        """处理中断信号"""
        print("\n⚠️ 检测到中断信号，准备结束轮询...")
        self.interrupted = True
        
    def execute(self, input_words, is_async=None, use_existing_id=None, 
                max_attempts=None, poll_interval=None):
        """
        执行工作流
        
        :param input_words: 输入的单词列表或空格分隔的单词字符串
        :param is_async: 是否异步执行，默认使用配置文件中的设置
        :param use_existing_id: 使用已有的执行ID查询结果，而不是重新执行工作流
        :param max_attempts: 轮询最大尝试次数，默认使用配置文件中的设置
        :param poll_interval: 轮询间隔（秒），默认使用配置文件中的设置
        :return: 解析后的工作流执行结果，包含句子列表和作文
        """
        # 确保单词列表格式正确
        if isinstance(input_words, list):
            input_words = ' '.join(input_words)
            
        # 设置默认值
        if is_async is None:
            is_async = config.DEFAULT_ASYNC
        if max_attempts is None:
            max_attempts = 20  # 改为20次
        if poll_interval is None:
            poll_interval = config.DEFAULT_POLL_INTERVAL
            
        # 重置中断标志
        self.interrupted = False
            
        # 设置信号处理程序，捕获Ctrl+C
        old_handler = signal.signal(signal.SIGINT, self.signal_handler)
            
        try:
            print(f"\n=== 执行单词到句子工作流 ===")
            print(f"输入单词: {input_words}")
            print(f"执行模式: {'异步' if is_async else '同步'}")
            print(f"轮询设置: 最多 {max_attempts} 次，间隔 {poll_interval} 秒")
            print(f"提示: 按下 Ctrl+C 可随时中断轮询")
            
            # 如果提供了已有的执行ID，直接查询结果
            if use_existing_id:
                print(f"\n=== 使用已有执行ID查询结果 ===")
                print(f"执行ID: {use_existing_id}")
                
                result = self.api.poll_workflow_result(
                    workflow_id=self.workflow_id,
                    execute_id=use_existing_id,
                    space_id=self.space_id,
                    max_attempts=max_attempts,
                    poll_interval=poll_interval
                )
                
                if result:
                    return self._process_result(result, input_words)
                else:
                    print(f"❌ 使用执行ID {use_existing_id} 查询结果失败")
                    return None
            
            # 构建工作流输入参数
            parameters = {"input": input_words}
            
            # 执行工作流
            result = self.api.execute_workflow(
                workflow_id=self.workflow_id,
                parameters=parameters,
                space_id=self.space_id,
                is_async=is_async
            )
            
            # 如果执行失败
            if not result:
                print(f"❌ 工作流执行失败")
                return None
            
            # 如果是异步执行，需要轮询结果
            if is_async and result and result.get("execute_id"):
                execute_id = result["execute_id"]
                print(f"✅ 工作流异步执行已启动")
                print(f"执行ID: {execute_id}")
                
                # 打印调试URL（如果有）
                if "debug_url" in result:
                    print(f"调试URL: {result['debug_url']}")
                
                # 如果需要，等待轮询
                final_result = self.api.poll_workflow_result(
                    workflow_id=self.workflow_id,
                    execute_id=execute_id,
                    space_id=self.space_id,
                    max_attempts=max_attempts,
                    poll_interval=poll_interval
                )
                
                # 如果轮询成功
                if final_result:
                    return self._process_result(final_result, input_words)
                else:
                    print(f"❌ 工作流执行失败或轮询超时")
                    return None
            # 同步执行，直接处理结果
            else:
                return self._process_result(result, input_words)
        except KeyboardInterrupt:
            print("\n🛑 用户中断了执行")
            return {"error": "用户中断了执行", "interrupted": True}
        finally:
            # 恢复原来的信号处理程序
            signal.signal(signal.SIGINT, old_handler)
        
    def _process_result(self, result, input_words):
        """
        处理工作流执行结果
        
        :param result: 工作流执行结果
        :param input_words: 输入的单词
        :return: 解析后的结果
        """
        # 保存原始结果
        if self.save_results:
            self.api.save_raw_result(result, filename_prefix="word_to_sentence")
        
        # 解析输出
        parsed_content = self._parse_output(result, input_words)
        
        # 保存解析后的结果
        if parsed_content and self.save_results:
            self._save_parsed_result(parsed_content)
            
        return parsed_content

    def _parse_output(self, result, input_words):
        """
        解析工作流输出
        
        :param result: API响应结果
        :param input_words: 输入的单词列表
        :return: 解析后的内容
        """
        # 初始化结果结构
        parsed_result = {
            "sentences": [],
            "essay": "",
            "input_words": input_words,
            "raw_output": ""
        }
        
        # 确保input_words是列表
        if isinstance(input_words, str):
            input_words = input_words.split()
        
        # 提取输出字符串
        output_str = None
        
        # 尝试从result的output字段获取
        if "output" in result:
            output_str = result["output"]
        
        # 尝试从data列表中获取
        if not output_str and "data" in result and isinstance(result["data"], list) and result["data"]:
            execution_data = result["data"][0]
            if "output" in execution_data:
                output_str = execution_data["output"]
        
        # 如果没有找到输出，尝试使用整个结果
        if not output_str:
            output_str = json.dumps(result, ensure_ascii=False)
        
        # 保存原始输出
        parsed_result["raw_output"] = output_str
        
        try:
            # 打印调试信息
            print(f"\n调试 - 原始输出: {output_str[:200]}...")  # 只显示前200个字符
            
            # 尝试处理多层嵌套的JSON
            content = ""
            
            # 尝试解析第一层
            try:
                data1 = json.loads(output_str)
                if "Output" in data1:
                    # 尝试解析第二层
                    try:
                        data2 = json.loads(data1["Output"])
                        if "output" in data2:
                            # 尝试解析第三层（如果有）
                            try:
                                content = json.loads(data2["output"])
                            except:
                                # 如果不是JSON，直接使用
                                content = data2["output"]
                    except:
                        # 如果第二层不是JSON，直接使用
                        content = data1["Output"]
            except:
                # 如果第一层不是JSON，直接使用
                content = output_str
            
            # 处理内容（去除转义字符）
            if isinstance(content, str):
                content = content.replace('\\n', '\n').replace('\\"', '"')
            
            # 处理Markdown格式的输出 (**Sentences:** 和 **Short Story:**/**Story:**)
            sentences_marker = "**Sentences:**"
            short_story_markers = ["**Short Story:**", "**Story:**"]
            
            # 查找句子标记位置
            sentences_pos = content.find(sentences_marker)
            
            # 查找故事标记位置
            short_story_pos = -1
            for marker in short_story_markers:
                pos = content.find(marker)
                if pos >= 0:
                    short_story_pos = pos
                    short_story_marker = marker
                    break
            
            if sentences_pos >= 0 and short_story_pos >= 0:
                # 提取句子部分（从sentences_marker后到short_story_marker前）
                sentences_text = content[sentences_pos + len(sentences_marker):short_story_pos].strip()
                
                # 提取作文部分（从short_story_marker后到结尾）
                essay_text = content[short_story_pos + len(short_story_marker):].strip()
                
                # 解析句子（通常是数字列表格式）
                sentence_lines = sentences_text.split('\n')
                sentence_lines = [line.strip() for line in sentence_lines if line.strip()]
                
                # 处理每个句子行
                for i, line in enumerate(sentence_lines):
                    if i < len(input_words):
                        # 尝试去除行号和点（如"1. "）
                        parts = line.split('. ', 1)
                        if len(parts) > 1 and parts[0].isdigit():
                            sentence = parts[1]
                        else:
                            sentence = line
                        
                        parsed_result["sentences"].append({
                            "word": input_words[i],
                            "sentence": sentence
                        })
                
                # 设置作文
                parsed_result["essay"] = essay_text
                return parsed_result
            
            # 如果没有找到Markdown标记，尝试其他方法
            
            # 按行分割内容
            lines = content.split('\n')
            lines = [line.strip() for line in lines if line.strip()]
            
            # 查找句子和作文
            essay_content = []
            essay_started = False
            
            for line in lines:
                # 检查是否是作文开始标记
                if "Short Story" in line or "Essay" in line:
                    essay_started = True
                    continue
                
                # 如果已经开始作文部分，收集内容
                if essay_started:
                    essay_content.append(line)
                    continue
                
                # 检查是否是带编号的句子 (n1, n2, n3 等)
                sentence_matched = False
                for i, word in enumerate(input_words):
                    prefix = f"n{i+1}"
                    
                    if line.startswith(prefix) or line.lower().startswith(prefix):
                        # 找到了一个句子
                        sentence = line[len(prefix):].strip()
                        # 去掉可能的前导冒号或其他标点
                        if sentence and sentence[0] in [':', '.', '-', '：']:
                            sentence = sentence[1:].strip()
                        
                        parsed_result["sentences"].append({
                            "word": word,
                            "sentence": sentence
                        })
                        sentence_matched = True
                        break
                    
                    # 尝试匹配数字格式（如"1. 句子"）
                    num_prefix = f"{i+1}. "
                    if line.startswith(num_prefix):
                        sentence = line[len(num_prefix):].strip()
                        parsed_result["sentences"].append({
                            "word": word,
                            "sentence": sentence
                        })
                        sentence_matched = True
                        break
                
                # 如果这行没有被识别为句子且没有作文标记，可能是作文的一部分
                if not sentence_matched and not any(marker in line for marker in ["Short Story", "Essay", "Sentences"]):
                    essay_content.append(line)
            
            # 合并作文内容
            if essay_content:
                parsed_result["essay"] = '\n'.join(essay_content)
            
            # 如果没有找到句子，尝试使用位置匹配
            if not parsed_result["sentences"] and lines:
                # 查找不含特殊标记的行数
                non_essay_lines = []
                for i, line in enumerate(lines):
                    if any(marker in line for marker in ["Short Story", "Essay", "Sentences"]):
                        break
                    non_essay_lines.append(line)
                
                # 将非作文行匹配到单词
                for i, word in enumerate(input_words):
                    if i < len(non_essay_lines):
                        # 尝试去除行号和点（如"1. "）
                        line = non_essay_lines[i]
                        parts = line.split('. ', 1)
                        if len(parts) > 1 and parts[0].isdigit():
                            sentence = parts[1]
                        else:
                            sentence = line
                            
                        parsed_result["sentences"].append({
                            "word": word,
                            "sentence": sentence
                        })
            
            # 如果没有找到作文，检查是否有一个明显较长的段落
            if not parsed_result["essay"] and lines:
                # 找到最长的行
                longest_line = max(lines, key=len)
                if len(longest_line) > 100:  # 假设作文至少100个字符
                    parsed_result["essay"] = longest_line
            
            return parsed_result
            
        except Exception as e:
            print(f"解析输出时发生错误: {e}")
            import traceback
            traceback_info = traceback.format_exc()
            print(f"错误详情:\n{traceback_info}")
            return {
                "sentences": [],
                "essay": "",
                "input_words": input_words,
                "raw_output": output_str,
                "error": str(e)
            }
    
    def _save_parsed_result(self, parsed_content):
        """
        将解析后的结果保存到文件
        :param parsed_content: 解析后的内容
        :return: 保存的文件路径
        """
        if not parsed_content:
            return None
            
        # 创建results目录（如果不存在）
        if not os.path.exists('results'):
            os.makedirs('results')
        
        # 生成文件名（使用时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'results/word_to_sentence_{timestamp}.txt'
        json_filename = f'results/word_to_sentence_{timestamp}.json'
        
        # 保存文本格式结果
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== 单词到句子工作流结果 ===\n\n")
            f.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"输入单词: {' '.join(parsed_content['input_words'])}\n\n")
            
            if parsed_content["sentences"]:
                f.write("=== 句子 ===\n")
                for item in parsed_content["sentences"]:
                    f.write(f"单词 '{item['word']}': {item['sentence']}\n")
            
            if parsed_content["essay"]:
                f.write("\n=== 作文 ===\n")
                f.write(parsed_content["essay"])
                f.write("\n\n")
        
        # 保存JSON格式结果
        with open(json_filename, 'w', encoding='utf-8') as f:
            json_result = {
                "execution_info": {
                    "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "input_words": parsed_content['input_words']
                },
                "content": {
                    "sentences": parsed_content["sentences"],
                    "essay": parsed_content["essay"]
                }
            }
            
            json.dump(json_result, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到文件:")
        print(f"- 文本格式: {filename}")
        print(f"- JSON格式: {json_filename}")
        
        return filename

def main():
    # 创建工作流处理器
    workflow = WordToSentenceWorkflow()
    
    # 输入英文单词
    input_words = "ant bird cat"  # 可以根据需要修改
    
    # 是否使用已有的execute_id（用于重新获取结果）
    USE_EXISTING_EXECUTE_ID = False
    EXISTING_EXECUTE_ID = ""  # 如果需要，替换为您的execute_id
    
    # 执行工作流
    if USE_EXISTING_EXECUTE_ID and EXISTING_EXECUTE_ID:
        result = workflow.execute(
            input_words=input_words,
            use_existing_id=EXISTING_EXECUTE_ID
        )
    else:
        result = workflow.execute(
            input_words=input_words
        )
    
    # 检查结果
    if not result:
        print("❌ 工作流执行未返回有效结果")

if __name__ == "__main__":
    main() 