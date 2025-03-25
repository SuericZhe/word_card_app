import requests
import json
import time
import os
from datetime import datetime
import traceback

class CozeAPI:
    """Coze平台API客户端，提供与工作流交互的基础功能"""
    
    def __init__(self, personal_token, space_id=None):
        """
        初始化Coze API客户端
        :param personal_token: 个人访问令牌
        :param space_id: 空间ID（可选，也可以在调用时指定）
        """
        self.personal_token = personal_token
        self.space_id = space_id
        self.headers = {
            "Authorization": f"Bearer {personal_token}",
            "Content-Type": "application/json"
        }
        
    def execute_workflow(self, workflow_id, parameters=None, space_id=None, is_async=True):
        """
        执行工作流
        
        :param workflow_id: 工作流ID
        :param parameters: 工作流输入参数，默认为None
        :param space_id: 空间ID，默认使用实例化时设置的空间ID
        :param is_async: 是否异步执行，默认为True
        :return: 工作流执行结果或启动信息
        """
        space_id = space_id or self.space_id
        parameters = parameters or {}
        
        print(f"\n=== 执行工作流 ===")
        print(f"工作流ID: {workflow_id}")
        print(f"空间ID: {space_id}")
        print(f"执行模式: {'异步' if is_async else '同步'}")
        print(f"请求参数: {json.dumps(parameters, ensure_ascii=False)}")
        
        # 构建请求
        url = "https://api.coze.cn/v1/workflow/run"
        payload = {
            "workflow_id": workflow_id,
            "space_id": space_id,
            "is_async": is_async
        }
        
        # 添加参数
        if parameters:
            payload["parameters"] = parameters
        
        try:
            # 发送请求
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()  # 检查请求是否成功
            
            # 解析响应
            result = response.json()
            
            if result.get("code") == 0:
                # 请求成功
                if is_async and "data" in result and "execute_id" in result["data"]:
                    # 异步执行启动成功
                    execute_id = result["data"]["execute_id"]
                    print(f"\n✅ 异步执行已启动")
                    print(f"执行ID: {execute_id}")
                    
                    # 添加调试URL
                    debug_url = f"https://www.coze.cn/work_flow?execute_id={execute_id}&space_id={space_id}&workflow_id={workflow_id}&execute_mode=2"
                    print(f"调试URL: {debug_url}")
                    
                    # 添加额外信息到结果中
                    result["execute_id"] = execute_id
                    result["debug_url"] = debug_url
            else:
                # API返回错误
                print(f"\n❌ API返回错误")
                print(f"错误码: {result.get('code')}")
                print(f"错误信息: {result.get('msg', '未知错误')}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            # 处理请求异常
            print(f"\n❌ API请求失败: {e}")
            return {"code": -1, "msg": f"API请求失败: {str(e)}"}
    
    def poll_workflow_result(self, workflow_id, execute_id, space_id=None, max_attempts=20, poll_interval=5):
        """
        轮询工作流执行结果
        
        :param workflow_id: 工作流ID
        :param execute_id: 执行ID
        :param space_id: 空间ID，默认使用实例化时设置的空间ID
        :param max_attempts: 最大轮询次数，默认20次
        :param poll_interval: 轮询间隔（秒），默认5秒
        :return: 工作流执行结果
        """
        space_id = space_id or self.space_id
        interrupted = False
        
        print(f"\n=== 开始轮询工作流执行结果 ===")
        print(f"工作流ID: {workflow_id}")
        print(f"执行ID: {execute_id}")
        print(f"最多轮询 {max_attempts} 次，每次间隔 {poll_interval} 秒")
        
        for attempt in range(1, max_attempts + 1):
            if interrupted:
                print("\n🛑 轮询被用户中断")
                break
                
            print(f"\n轮询尝试 {attempt}/{max_attempts}")
            
            try:
                # 请求执行结果
                url = f"https://api.coze.cn/v1/workflows/{workflow_id}/run_histories/{execute_id}"
                
                # 使用GET请求获取结果
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                result = response.json()
                
                # 添加调试信息
                print(f"API响应: {json.dumps(result, ensure_ascii=False)[:200]}...")
                
                if result.get("code") == 0:
                    # 检查执行状态
                    if "data" in result:
                        data = result["data"]
                        
                        # 如果data是数组，获取第一个元素
                        if isinstance(data, list) and data:
                            item = data[0]
                            
                            # 检查execute_status字段
                            if "execute_status" in item:
                                status = item.get("execute_status")
                                
                                if status == "Success" or status == "Completed":
                                    print("✅ 工作流执行成功")
                                    # 检查是否有输出
                                    if "output" in item:
                                        print("✅ 成功获取输出数据")
                                        result["output"] = item["output"]
                                    return result
                                elif status == "Failed":
                                    print("❌ 工作流执行失败")
                                    error_msg = item.get("error_message", "未知错误")
                                    print(f"错误信息: {error_msg}")
                                    return result
                                elif status == "Running" or status == "InProgress":
                                    print("⏳ 工作流仍在执行中...")
                                else:
                                    print(f"⚠️ 未知状态: {status}")
                                    
                                    # 特殊处理：如果状态未知但有输出数据，则认为已完成
                                    if "output" in item and item["output"]:
                                        print("✅ 检测到输出数据，视为执行成功")
                                        result["output"] = item["output"]
                                        return result
                            # 如果没有execute_status但有output，认为已完成
                            elif "output" in item and item["output"]:
                                print("✅ 工作流执行成功，检测到输出数据")
                                result["output"] = item["output"]
                                return result
                        # 处理非数组格式的data
                        else:
                            # 新的API可能有不同的响应结构
                            # 尝试识别运行状态和输出
                            if "status" in data:
                                status = data.get("status")
                                
                                if status == "Success" or status == "Completed":
                                    print("✅ 工作流执行成功")
                                    
                                    # 检查是否有输出
                                    if "output" in data:
                                        print("✅ 成功获取输出数据")
                                        # 确保结果中包含output字段
                                        if isinstance(data["output"], str):
                                            result["output"] = data["output"]
                                        
                                    return result
                                elif status == "Failed":
                                    print("❌ 工作流执行失败")
                                    error_msg = data.get("error_message", "未知错误")
                                    print(f"错误信息: {error_msg}")
                                    return result
                                elif status == "Running" or status == "InProgress":
                                    print("⏳ 工作流仍在执行中...")
                                else:
                                    print(f"⚠️ 未知状态: {status}")
                                    
                                    # 特殊处理：如果状态未知但有输出数据，则认为已完成
                                    if "output" in data and data["output"]:
                                        print("✅ 检测到输出数据，视为执行成功")
                                        return result
                        
                            # 如果没有标准状态字段，但有输出，也视为成功
                            elif "output" in data or "result" in data:
                                output = data.get("output") or data.get("result")
                                print("✅ 工作流执行成功，检测到输出数据")
                                result["output"] = output
                                return result
                        
                            # 处理其他可能的数据结构
                            elif isinstance(data, list) and data:
                                # 有些API可能返回列表结果
                                item = data[0]
                                if "status" in item and item["status"] in ["Success", "Completed"]:
                                    print("✅ 工作流执行成功")
                                    return result
                                elif "output" in item or "result" in item:
                                    print("✅ 工作流执行成功，检测到输出数据")
                                    return result
                elif result.get("status") in ["Success", "Completed"]:
                    # 有些API可能直接在根级别返回状态
                    print("✅ 工作流执行成功")
                    return result
                elif "output" in result or "result" in result:
                    # 有些API可能直接在根级别返回输出
                    print("✅ 工作流执行成功，检测到输出数据")
                    return result
                
            except requests.exceptions.RequestException as e:
                print(f"❌ 请求失败: {e}")
            
            # 如果未完成且未达到最大尝试次数，等待后继续
            if attempt < max_attempts and not interrupted:
                print(f"等待 {poll_interval} 秒后继续轮询...")
                
                try:
                    time.sleep(poll_interval)
                except KeyboardInterrupt:
                    print("\n收到用户中断信号")
                    interrupted = True
        
        if interrupted:
            print("\n🛑 轮询被用户中断")
        else:
            print(f"\n⚠️ 达到最大轮询次数 {max_attempts}，停止轮询")
        
        return {"code": -1, "msg": f"轮询结束，可能原因: {'用户中断' if interrupted else f'达到最大尝试次数 {max_attempts}'}", "execute_id": execute_id}

    def save_raw_result(self, result, filename_prefix="workflow_result"):
        """
        保存原始结果到文件
        :param result: API响应结果
        :param filename_prefix: 文件名前缀
        :return: 保存的文件路径
        """
        # 创建results目录（如果不存在）
        if not os.path.exists('results'):
            os.makedirs('results')
        
        # 生成文件名（使用时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        raw_filename = f'results/{filename_prefix}_raw_{timestamp}.json'
        
        # 保存原始响应
        with open(raw_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"原始结果已保存到: {raw_filename}")
        return raw_filename

def parse_workflow_output(output_str, input_words):
    """
    解析工作流输出，提取句子和作文
    
    :param output_str: 原始输出字符串
    :param input_words: 输入的单词列表
    :return: 字典，包含句子和作文
    """
    # 确保input_words是列表形式
    input_word_list = input_words.split() if isinstance(input_words, str) else input_words
    
    result = {
        "sentences": [],
        "essay": "",
        "input_words": input_word_list,
        "raw_output": output_str
    }
    
    try:
        # 尝试解析JSON或直接处理文本
        content = ""
        
        # 尝试解析JSON格式
        try:
            # 解析JSON字符串
            output_data = json.loads(output_str)
            
            # 尝试获取内容
            if "Output" in output_data:
                content = output_data["Output"]
            elif "output" in output_data:
                content = output_data["output"]
        except:
            # 如果JSON解析失败，直接使用原始字符串
            content = output_str
        
        # 尝试清理内容中的转义字符
        content = content.replace('\\n', '\n').replace('\\"', '"')
        
        # 处理Markdown格式的输出 (**Sentences:** 和 **Short Story:**)
        sentences_marker = "**Sentences:**"
        short_story_marker = "**Short Story:**"
        
        # 查找标记位置
        sentences_pos = content.find(sentences_marker)
        short_story_pos = content.find(short_story_marker)
        
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
                if i < len(input_word_list):
                    # 尝试去除行号和点（如"1. "）
                    parts = line.split('. ', 1)
                    if len(parts) > 1 and parts[0].isdigit():
                        sentence = parts[1]
                    else:
                        sentence = line
                    
                    result["sentences"].append({
                        "word": input_word_list[i],
                        "sentence": sentence
                    })
            
            # 设置作文
            result["essay"] = essay_text
            return result
            
        # 如果没有找到Markdown标记，尝试按行分析
        lines = content.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        # 尝试匹配每个单词的句子
        for i, word in enumerate(input_word_list):
            for line in lines:
                if word.lower() in line.lower():
                    result["sentences"].append({
                        "word": word,
                        "sentence": line
                    })
                    break
        
        # 尝试找到最长的段落作为作文
        if lines and not result["essay"]:
            longest_line = max(lines, key=len)
            if len(longest_line) > 100:  # 假设作文至少100个字符
                result["essay"] = longest_line
        
        return result
        
    except Exception as e:
        return {
            "sentences": [],
            "essay": "",
            "input_words": input_word_list,
            "raw_output": output_str,
            "error": str(e)
        }

def execute_workflow(workflow_id, personal_token, space_id=None, parameters=None, is_async=True):
    """
    执行工作流（便捷函数）
    
    :param workflow_id: 工作流ID
    :param personal_token: 个人令牌
    :param space_id: 空间ID
    :param parameters: 执行参数
    :param is_async: 是否异步执行
    :return: 执行结果
    """
    api = CozeAPI(personal_token, space_id)
    return api.execute_workflow(workflow_id, parameters, space_id, is_async)

def poll_workflow_result(workflow_id, execute_id, personal_token, space_id=None, max_attempts=20, poll_interval=5):
    """
    轮询工作流执行结果（便捷函数）
    
    :param workflow_id: 工作流ID
    :param execute_id: 执行ID
    :param personal_token: 个人令牌
    :param space_id: 空间ID
    :param max_attempts: 最大轮询次数
    :param poll_interval: 轮询间隔
    :return: 执行结果
    """
    api = CozeAPI(personal_token, space_id)
    return api.poll_workflow_result(workflow_id, execute_id, space_id, max_attempts, poll_interval) 