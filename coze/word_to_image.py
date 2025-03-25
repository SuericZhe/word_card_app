import os
import json
from datetime import datetime
import time
import signal
from coze_api import CozeAPI
import config
import re

class WordToImageWorkflow:
    """
    实现单词到图片的Coze工作流处理
    
    这个工作流接收单词作为输入，然后返回:
    1. 根据单词生成的图片URL
    """
    
    def __init__(self, personal_token=None, workflow_id=None, space_id=None, save_results=True):
        """
        初始化单词到图片工作流处理器
        
        :param personal_token: Coze API的个人访问令牌
        :param workflow_id: 工作流ID
        :param space_id: 空间ID
        :param save_results: 是否保存中间结果，默认为True
        """
        self.space_id = space_id or config.SPACE_ID
        self.api = CozeAPI(personal_token or config.PERSONAL_TOKEN, self.space_id)
        self.workflow_id = workflow_id or config.WORKFLOW_IDS["word_to_image"]
        self.save_results = save_results
        # 中断标志
        self.interrupted = False
        
    def signal_handler(self, sig, frame):
        """处理中断信号"""
        print("\n⚠️ 检测到中断信号，准备结束轮询...")
        self.interrupted = True
        
    def execute(self, input_word, is_async=None, use_existing_id=None, 
                max_attempts=None, poll_interval=None):
        """
        执行工作流
        
        :param input_word: 输入的英文单词
        :param is_async: 是否异步执行，默认使用配置文件中的设置
        :param use_existing_id: 使用已有的执行ID查询结果，而不是重新执行工作流
        :param max_attempts: 轮询最大尝试次数，默认使用配置文件中的设置
        :param poll_interval: 轮询间隔（秒），默认使用配置文件中的设置
        :return: 解析后的工作流执行结果，包含图片URL
        """
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
            # 确保输入为字符串
            if not isinstance(input_word, str):
                input_word = str(input_word)
                
            print(f"\n=== 执行单词到图片工作流 ===")
            print(f"工作流ID: {self.workflow_id}")
            print(f"空间ID: {self.space_id}")
            print(f"输入单词: {input_word}")
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
                    return self._process_result(result, input_word)
                else:
                    print(f"❌ 使用执行ID {use_existing_id} 查询结果失败")
                    return None
            
            # 构建工作流输入参数
            parameters = {"input": input_word}
            
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
                
                final_result = self.api.poll_workflow_result(
                    workflow_id=self.workflow_id,
                    execute_id=execute_id,
                    space_id=self.space_id,
                    max_attempts=max_attempts,
                    poll_interval=poll_interval
                )
                
                # 如果轮询成功
                if final_result:
                    return self._process_result(final_result, input_word)
                else:
                    print(f"❌ 工作流执行失败或轮询超时")
                    return None
            # 同步执行，直接处理结果
            else:
                return self._process_result(result, input_word)
        except KeyboardInterrupt:
            print("\n🛑 用户中断了执行")
            return {"error": "用户中断了执行", "interrupted": True}
        finally:
            # 恢复原来的信号处理程序
            signal.signal(signal.SIGINT, old_handler)
    
    def _process_result(self, result, input_word):
        """
        处理工作流执行结果
        
        :param result: API响应结果
        :param input_word: 输入的单词
        :return: 解析后的内容
        """
        # 保存原始结果
        if self.save_results:
            self.api.save_raw_result(result, filename_prefix="word_to_image")
        
        # 解析结果
        parsed_content = self._parse_output(result, input_word)
        
        # 保存解析后的结果到文件
        if parsed_content and self.save_results:
            self._save_parsed_result(parsed_content)
        
        # 显示解析后的结果
        if parsed_content:
            print("\n=== 解析后的内容 ===")
            
            if parsed_content.get("image_url"):
                print(f"生成图片URL: {parsed_content['image_url']}")
            else:
                print("⚠️ 未能解析出图片URL")
            
            if parsed_content.get("caption"):
                print(f"图片描述: {parsed_content['caption']}")
        
        return parsed_content

    def _parse_output(self, result, input_word):
        """
        解析工作流输出
        
        :param result: API响应结果
        :param input_word: 输入的单词
        :return: 解析后的内容
        """
        # 初始化结果结构
        parsed_result = {
            "image_url": "",
            "caption": "",
            "input_word": input_word,
            "raw_output": ""
        }
        
        # 提取输出字符串
        output_str = None
        
        # 尝试从parsed_output字段获取
        if "parsed_output" in result:
            output_data = result["parsed_output"]
            if "Output" in output_data:
                output_str = output_data["Output"]
        
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
            # 打印原始输出以便调试
            print(f"\n调试 - 原始输出: {output_str}")
            
            # 尝试直接使用输出作为URL（针对简单直接返回URL的情况）
            clean_output = output_str.strip().strip('"').strip()
            if clean_output.startswith("http"):
                parsed_result["image_url"] = clean_output
                return parsed_result
                
            # 尝试解析JSON格式
            try:
                # 解析JSON字符串
                output_data = json.loads(output_str)
                
                # 检查直接返回的URL字符串
                if isinstance(output_data, str) and output_data.startswith("http"):
                    parsed_result["image_url"] = output_data
                    return parsed_result
                
                # 尝试获取内容
                if "Output" in output_data:
                    inner_output = output_data["Output"]
                    # 检查是否直接是URL
                    if isinstance(inner_output, str) and inner_output.startswith("http"):
                        parsed_result["image_url"] = inner_output
                        return parsed_result
                        
                    try:
                        # 尝试解析嵌套JSON
                        inner_data = json.loads(inner_output)
                        if "image_url" in inner_data:
                            parsed_result["image_url"] = inner_data["image_url"]
                            return parsed_result
                        elif "data" in inner_data:
                            content = inner_data["data"]
                            # 检查data是否是URL
                            if isinstance(content, str) and content.startswith("http"):
                                parsed_result["image_url"] = content
                                return parsed_result
                    except:
                        # 尝试直接提取URL
                        if isinstance(inner_output, str):
                            # 清除引号和空格
                            inner_output = inner_output.strip().strip('"').strip()
                            if inner_output.startswith("http"):
                                parsed_result["image_url"] = inner_output
                                return parsed_result
                
                # 检查output字段
                elif "output" in output_data:
                    output_content = output_data["output"]
                    if isinstance(output_content, str) and output_content.startswith("http"):
                        parsed_result["image_url"] = output_content
                        return parsed_result
                    
                # 直接检查顶层是否有image_url
                if "image_url" in output_data:
                    parsed_result["image_url"] = output_data["image_url"]
                    if "caption" in output_data:
                        parsed_result["caption"] = output_data["caption"]
                    return parsed_result
            except Exception as e:
                print(f"JSON解析尝试失败: {e}")
                # 失败时继续使用正则表达式方法
            
            # 使用正则表达式查找URL
            # 查找URL模式 (支持http和https)
            url_pattern = r'https?://\S+'
            urls = re.findall(url_pattern, output_str)
            
            if urls:
                # 清理URL末尾可能的标点符号
                url = urls[0].rstrip(',.;:"\'])}>')
                parsed_result["image_url"] = url
                
                # 尝试提取图片描述
                lines = output_str.split('\n')
                for line in lines:
                    # 如果行不包含URL但包含关键词，可能是描述
                    if url not in line and any(word in line.lower() for word in ['description', 'caption', 'depicts', 'showing', 'image of']):
                        if len(line) > 10:  # 确保描述有足够长度
                            parsed_result["caption"] = line.strip()
                            break
            
            return parsed_result
            
        except Exception as e:
            print(f"解析输出时发生错误: {e}")
            import traceback
            traceback_info = traceback.format_exc()
            print(f"错误详情:\n{traceback_info}")
            return {
                "image_url": "",
                "caption": "",
                "input_word": input_word,
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
        filename = f'results/word_to_image_{timestamp}.txt'
        json_filename = f'results/word_to_image_{timestamp}.json'
        
        # 保存文本格式结果
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== 单词到图片工作流结果 ===\n\n")
            f.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"输入单词: {parsed_content['input_word']}\n\n")
            
            if parsed_content["image_url"]:
                f.write("=== 图片URL ===\n")
                f.write(f"{parsed_content['image_url']}\n\n")
            else:
                f.write("⚠️ 未能解析出图片URL\n\n")
                f.write("=== 原始输出 ===\n")
                f.write(f"{parsed_content['raw_output'][:500]}...\n\n")
            
            if parsed_content.get("caption"):
                f.write("=== 图片描述 ===\n")
                f.write(f"{parsed_content['caption']}\n\n")
        
        # 保存JSON格式结果
        with open(json_filename, 'w', encoding='utf-8') as f:
            json_result = {
                "execution_info": {
                    "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "input_word": parsed_content['input_word']
                },
                "content": {
                    "image_url": parsed_content["image_url"],
                    "caption": parsed_content.get("caption", "")
                }
            }
            
            json.dump(json_result, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到文件:")
        print(f"- 文本格式: {filename}")
        print(f"- JSON格式: {json_filename}")
        
        return filename

def main():
    # 创建工作流处理器
    workflow = WordToImageWorkflow()
    
    # 输入单词
    input_word = "cat"  # 可以根据需要修改
    
    # 是否使用已有的execute_id（用于重新获取结果）
    USE_EXISTING_EXECUTE_ID = False
    EXISTING_EXECUTE_ID = ""  # 如果需要，替换为您的execute_id
    
    # 执行工作流
    if USE_EXISTING_EXECUTE_ID and EXISTING_EXECUTE_ID:
        result = workflow.execute(
            input_word=input_word,
            use_existing_id=EXISTING_EXECUTE_ID
        )
    else:
        result = workflow.execute(
            input_word=input_word
        )
    
    # 检查结果
    if not result:
        print("❌ 工作流执行未返回有效结果")
    elif not result.get("image_url"):
        print("⚠️ 工作流执行成功但未返回图片URL")

if __name__ == "__main__":
    main() 