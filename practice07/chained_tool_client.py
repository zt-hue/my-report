import os
import json
import http.client
import ssl
import re
from urllib.parse import urlparse
import sys
import stat
import time
import subprocess
from typing import Dict, List, Any, Optional


def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(env_path):
        print(f"错误：{env_path} 文件不存在，请从 env.example 复制并填写正确参数")
        exit(1)
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value


def list_files(directory):
    try:
        files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            stat_info = os.stat(item_path)
            files.append({
                "name": item,
                "path": item_path,
                "size": stat_info.st_size,
                "mode": stat.filemode(stat_info.st_mode),
                "mtime": stat_info.st_mtime
            })
        return json.dumps({"status": "success", "data": files}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


def rename_file(directory, old_name, new_name):
    try:
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)
        os.rename(old_path, new_path)
        return json.dumps({"status": "success", "message": f"文件已重命名为 {new_name}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


def delete_file(directory, file_name):
    try:
        file_path = os.path.join(directory, file_name)
        os.remove(file_path)
        return json.dumps({"status": "success", "message": "文件已删除"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


def create_file(directory, file_name, content):
    try:
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return json.dumps({"status": "success", "message": "文件已创建"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


def read_file(directory, file_name):
    try:
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return json.dumps({"status": "success", "data": content}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


def fetch_webpage(url):
    try:
        url = url.strip('`')
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        from urllib.parse import quote
        path = parsed_url.path if parsed_url.path else '/'
        path = quote(path, safe='/')
        if parsed_url.query:
            path += '?' + quote(parsed_url.query, safe='=&%+')
        protocol = parsed_url.scheme
        
        if protocol == 'https':
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(host, context=context)
        else:
            conn = http.client.HTTPConnection(host)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        conn.request('GET', path, headers=headers)
        response = conn.getresponse()
        content = response.read().decode('utf-8', errors='replace')
        
        max_content_length = 100000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n... (内容已截断)"
        
        return json.dumps({"status": "success", "data": content}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


def search_files_by_keyword(directory: str, keyword: str) -> str:
    try:
        matching_files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                try:
                    with open(item_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if keyword.lower() in content.lower():
                            stat_info = os.stat(item_path)
                            matching_files.append({
                                "name": item,
                                "path": item_path,
                                "size": stat_info.st_size,
                                "mode": stat.filemode(stat_info.st_mode)
                            })
                except Exception:
                    pass
        
        return json.dumps({"status": "success", "data": matching_files}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


class ChainedCallContext:
    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations
        self.steps: List[Dict[str, Any]] = []
        self.variables: Dict[str, Any] = {}
        self.current_iteration = 0
    
    def add_step(self, tool_name: str, arguments: Dict[str, Any], result: Any) -> None:
        step = {
            "step_number": len(self.steps) + 1,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
            "result_summary": self._summarize_result(result)
        }
        self.steps.append(step)
        
        self._extract_variables(tool_name, arguments, result)
    
    def _summarize_result(self, result: Any) -> str:
        if isinstance(result, str):
            try:
                result_data = json.loads(result)
                if result_data.get('status') == 'success':
                    data = result_data.get('data')
                    if isinstance(data, list):
                        return f"成功返回 {len(data)} 个条目"
                    elif isinstance(data, str) and len(data) > 200:
                        return data[:200] + "..."
                    elif data is not None:
                        return str(data)[:200]
                    elif result_data.get('message'):
                        return result_data.get('message')
                elif result_data.get('status') == 'error':
                    return f"错误: {result_data.get('message', '未知错误')}"
            except json.JSONDecodeError:
                if len(result) > 200:
                    return result[:200] + "..."
                return result
        return str(result)
    
    def _extract_variables(self, tool_name: str, arguments: Dict[str, Any], result: Any) -> None:
        try:
            if isinstance(result, str):
                result_data = json.loads(result)
                if result_data.get('status') == 'success':
                    data = result_data.get('data')
                    
                    if tool_name == "read_file" and isinstance(data, str):
                        self.variables['last_read_content'] = data
                    elif tool_name == "list_directory" and isinstance(data, list):
                        self.variables['last_directory_list'] = data
                    elif tool_name == "fetch_webpage" and isinstance(data, str):
                        self.variables['last_webpage_content'] = data
                    elif tool_name == "search_files_by_keyword" and isinstance(data, list):
                        self.variables['matching_files'] = data
        except (json.JSONDecodeError, TypeError):
            pass
    
    def increment_iteration(self) -> bool:
        self.current_iteration += 1
        return self.current_iteration <= self.max_iterations
    
    def get_steps_history(self) -> List[Dict[str, Any]]:
        return self.steps
    
    def get_variables(self) -> Dict[str, Any]:
        return self.variables
    
    def is_complete(self) -> bool:
        return self.current_iteration >= self.max_iterations
    
    def reset(self) -> None:
        self.steps = []
        self.variables = {}
        self.current_iteration = 0


def build_analysis_prompt(user_request: str, context: ChainedCallContext) -> str:
    steps_history = context.get_steps_history()
    variables = context.get_variables()
    
    prompt_parts = []
    prompt_parts.append("你是一个任务规划助手，负责分析用户请求并决定下一步操作。\n")
    prompt_parts.append("=" * 60 + "\n")
    prompt_parts.append(f"【用户原始请求】\n{user_request}\n\n")
    
    if steps_history:
        prompt_parts.append("【已执行的工具调用历史】\n")
        prompt_parts.append("-" * 60 + "\n")
        for step in steps_history:
            prompt_parts.append(f"步骤 {step['step_number']}:\n")
            prompt_parts.append(f"  工具: {step['tool_name']}\n")
            prompt_parts.append(f"  参数: {json.dumps(step['arguments'], ensure_ascii=False)}\n")
            prompt_parts.append(f"  结果摘要: {step['result_summary']}\n")
            prompt_parts.append("-" * 60 + "\n")
        prompt_parts.append("\n")
    
    if variables:
        prompt_parts.append("【可用的上下文变量】（可在上一步结果中引用）\n")
        prompt_parts.append("-" * 60 + "\n")
        for key, value in variables.items():
            if isinstance(value, list):
                prompt_parts.append(f"  {key}: 列表，包含 {len(value)} 个元素\n")
                if value and isinstance(value[0], dict):
                    prompt_parts.append(f"    示例: {json.dumps(value[0], ensure_ascii=False)[:100]}...\n")
            elif isinstance(value, str) and len(value) > 100:
                prompt_parts.append(f"  {key}: \"{value[:100]}...\"\n")
            else:
                prompt_parts.append(f"  {key}: {value}\n")
        prompt_parts.append("-" * 60 + "\n\n")
    
    prompt_parts.append("【决策规则】\n")
    prompt_parts.append("1. 分析用户请求和已执行步骤，判断任务是否完成\n")
    prompt_parts.append("2. 如果任务需要多步操作，根据上一步结果决定下一步\n")
    prompt_parts.append("3. 可以利用上下文变量中的数据作为工具参数\n")
    prompt_parts.append("4. 链式调用示例：\n")
    prompt_parts.append("   - 先搜索文件 -> 获取文件列表\n")
    prompt_parts.append("   - 读取某个文件 -> 获取文件内容\n")
    prompt_parts.append("   - 写入结果 -> 保存到新文件\n\n")
    
    prompt_parts.append("【输出格式要求】\n")
    prompt_parts.append("完成任务时，返回以下JSON格式：\n")
    prompt_parts.append('{"done": true, "answer": "最终回答内容"}\n\n')
    prompt_parts.append("继续调用工具时，返回以下JSON格式：\n")
    prompt_parts.append('{"done": false, "tool_call": {"name": "工具名称", "arguments": {"参数名": "参数值"}}}\n\n')
    
    prompt_parts.append("【可用工具列表】\n")
    prompt_parts.append("1. list_files(path) - 列出目录下的文件\n")
    prompt_parts.append("2. search_files_by_keyword(directory, keyword) - 搜索包含关键词的文件\n")
    prompt_parts.append("3. read_file(directory, file_name) - 读取文件内容\n")
    prompt_parts.append("4. create_file(directory, file_name, content) - 创建文件\n")
    prompt_parts.append("5. delete_file(directory, file_name) - 删除文件\n")
    prompt_parts.append("6. rename_file(directory, old_name, new_name) - 重命名文件\n")
    prompt_parts.append("7. fetch_webpage(url) - 访问网页\n")
    prompt_parts.append("8. summarize_text(text) - 总结文本内容\n")
    
    prompt_parts.append("\n" + "=" * 60 + "\n")
    prompt_parts.append("请根据以上信息，决定下一步操作：\n")
    
    return "".join(prompt_parts)


def get_chained_system_prompt() -> str:
    return """你是一个具有链式工具调用能力的AI助手。

## 核心能力
你能够进行链式工具调用，即前一个工具的输出可以作为后一个工具的输入参数，根据中间结果自主决定下一步操作。

## 链式调用规则

### 1. 顺序依赖关系
- 每个工具的输出都可能成为下一个工具的输入
- 必须等待前一个工具执行完成，才能根据结果决定下一步
- 工具之间存在数据依赖时，需要串行执行

### 2. 决策机制
- 每一步执行后，分析当前结果是否满足用户需求
- 如果不满足，根据结果类型决定下一步操作：
  * 获得文件列表 -> 选择文件进行读取
  * 获得文件内容 -> 提取信息或进行总结
  * 获得网页内容 -> 提取关键信息或保存
  * 获得数值结果 -> 进行计算或写入文件

### 3. 上下文变量使用
系统会自动提取并存储关键中间结果：
- `last_read_content`: 最近一次读取的文件内容
- `last_directory_list`: 最近一次列出的目录内容
- `last_webpage_content`: 最近一次获取的网页内容
- `matching_files`: 搜索结果匹配的文件列表
- 可以在后续工具调用中引用这些变量

### 4. 链式调用示例

示例1：文件搜索链式调用
用户请求："查找 practice06 目录下所有包含 'def' 关键词的文件"
执行流程：
1. search_files_by_keyword(directory="practice06路径", keyword="def")
2. 分析搜索结果，获取匹配文件列表
3. 汇总结果返回给用户

示例2：多文件操作链式调用
用户请求："读取 1.txt 和 2.txt，计算两数之和并写入 result.txt"
执行流程：
1. read_file(directory="当前目录", file_name="1.txt") -> 获取数字A
2. read_file(directory="当前目录", file_name="2.txt") -> 获取数字B
3. 计算 A + B
4. create_file(directory="当前目录", file_name="result.txt", content=str(A+B))

示例3：网页处理链式调用
用户请求："访问网页并总结内容保存到文件"
执行流程：
1. fetch_webpage(url="目标URL") -> 获取网页内容
2. summarize_text(text="网页内容") -> 获取总结
3. create_file(directory="当前目录", file_name="summary.txt", content="总结内容")

## 注意事项
- 设置最大迭代次数（默认10次）防止无限循环
- 每一步都要检查结果是否有效
- JSON解析失败时，提供有意义的错误信息
"""


def call_llm(messages, tools=None):
    base_url = os.getenv('LLM_BASE_URL') or os.getenv('BASE_URL')
    model = os.getenv('LLM_MODEL') or os.getenv('MODEL')
    api_key = os.getenv('LLM_API_KEY') or os.getenv('API_KEY')
    
    if not all([base_url, model, api_key]):
        print("错误：请在.env文件中配置 LLM_BASE_URL、LLM_MODEL 和 LLM_API_KEY")
        return None
    
    parsed_url = urlparse(base_url)
    host = parsed_url.netloc
    path = parsed_url.path.rstrip('/') + '/chat/completions'
    protocol = parsed_url.scheme
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": float(os.getenv('LLM_TEMPERATURE', os.getenv('TEMPERATURE', '0.7'))),
        "max_tokens": int(os.getenv('LLM_MAX_TOKENS', os.getenv('MAX_TOKENS', '8192')))
    }
    
    if tools:
        data["tools"] = tools
        data["tool_choice"] = "auto"
    
    if protocol == 'https':
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        conn = http.client.HTTPSConnection(host, context=context)
    else:
        conn = http.client.HTTPConnection(host)
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    try:
        conn.request('POST', path, json.dumps(data), headers)
        response = conn.getresponse()
        response_content = response.read().decode()
        
        try:
            response_data = json.loads(response_content)
        except json.JSONDecodeError:
            if response.status == 200:
                return response_content
            else:
                print(f"API错误: {response_content}")
                return None
        
        if response.status == 200:
            return response_data
        else:
            if isinstance(response_data, dict):
                error_info = response_data.get('error', {})
                if isinstance(error_info, dict):
                    error_message = error_info.get('message', '未知错误')
                else:
                    error_message = str(error_info)
            else:
                error_message = str(response_data)
            print(f"API错误: {error_message}")
            return None
    finally:
        conn.close()


def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    print(f"执行工具: {tool_name}")
    print(f"参数: {arguments}")
    
    try:
        if tool_name == "list_files":
            path = arguments.get('path')
            result = list_files(path)
        elif tool_name == "search_files_by_keyword":
            directory = arguments.get('directory')
            keyword = arguments.get('keyword')
            result = search_files_by_keyword(directory, keyword)
        elif tool_name == "read_file":
            directory = arguments.get('directory')
            file_name = arguments.get('file_name')
            result = read_file(directory, file_name)
        elif tool_name == "create_file":
            directory = arguments.get('directory')
            file_name = arguments.get('file_name')
            content = arguments.get('content')
            result = create_file(directory, file_name, content)
        elif tool_name == "delete_file":
            directory = arguments.get('directory')
            file_name = arguments.get('file_name')
            result = delete_file(directory, file_name)
        elif tool_name == "rename_file":
            directory = arguments.get('directory')
            old_name = arguments.get('old_name')
            new_name = arguments.get('new_name')
            result = rename_file(directory, old_name, new_name)
        elif tool_name == "fetch_webpage":
            url = arguments.get('url')
            result = fetch_webpage(url)
        elif tool_name == "summarize_text":
            text = arguments.get('text')
            messages = [
                {"role": "system", "content": "你是一个文本总结助手，请简洁地总结以下内容："},
                {"role": "user", "content": text}
            ]
            response = call_llm(messages)
            if response and isinstance(response, dict):
                summary = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                result = json.dumps({"status": "success", "data": summary}, ensure_ascii=False)
            else:
                result = json.dumps({"status": "error", "message": "总结失败"}, ensure_ascii=False)
        else:
            result = json.dumps({"status": "error", "message": f"未知的工具: {tool_name}"}, ensure_ascii=False)
    except Exception as e:
        result = json.dumps({"status": "error", "message": f"工具执行异常: {str(e)}"}, ensure_ascii=False)
    
    print(f"工具执行结果: {result[:200]}...")
    return result


def parse_llm_response(response: Any) -> Optional[Dict[str, Any]]:
    if response is None:
        return None
    
    if isinstance(response, dict):
        choices = response.get('choices', [{}])
        if not choices:
            return None
        
        message = choices[0].get('message', {})
        
        if message.get('tool_calls'):
            tool_call = message.get('tool_calls', [{}])[0]
            function = tool_call.get('function', {})
            name = function.get('name')
            arguments_str = function.get('arguments', '{}')
            if isinstance(arguments_str, str):
                try:
                    arguments = json.loads(arguments_str)
                except json.JSONDecodeError:
                    arguments = {}
            else:
                arguments = arguments_str
            
            return {
                "done": False,
                "tool_call": {
                    "name": name,
                    "arguments": arguments
                }
            }
        
        content = message.get('content', '')
        if content:
            return _parse_json_content(content)
    
    if isinstance(response, str):
        return _parse_json_content(response)
    
    return None


def _parse_json_content(content: str) -> Optional[Dict[str, Any]]:
    content = content.strip()
    
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        content = json_match.group(1)
    else:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"JSON解析失败，原始内容: {content[:200]}...")
        return None


def execute_chained_tool_call(user_request: str, max_iterations: int = 10) -> str:
    context = ChainedCallContext(max_iterations=max_iterations)
    
    system_prompt = get_chained_system_prompt()
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    print("\n" + "=" * 60)
    print("开始链式工具调用")
    print(f"用户请求: {user_request}")
    print("=" * 60)
    
    while context.increment_iteration():
        print(f"\n--- 第 {context.current_iteration} 轮 ---")
        
        analysis_prompt = build_analysis_prompt(user_request, context)
        
        current_messages = messages + [
            {"role": "user", "content": analysis_prompt}
        ]
        
        print("正在调用LLM分析下一步操作...")
        response = call_llm(current_messages)
        
        if response is None:
            return "错误：LLM调用失败"
        
        decision = parse_llm_response(response)
        
        if decision is None:
            return f"错误：无法解析LLM响应"
        
        if decision.get('done'):
            answer = decision.get('answer', '')
            print(f"\n任务完成！\n最终回答: {answer}")
            return answer
        
        tool_call = decision.get('tool_call')
        if not tool_call:
            return "错误：LLM响应中缺少tool_call信息"
        
        tool_name = tool_call.get('name')
        tool_args = tool_call.get('arguments', {})
        
        if not tool_name:
            return "错误：tool_call中缺少工具名称"
        
        result = execute_tool_call(tool_name, tool_args)
        
        context.add_step(tool_name, tool_args, result)
        
        messages.append({"role": "user", "content": analysis_prompt})
        
        if isinstance(response, dict):
            choices = response.get('choices', [{}])
            if choices:
                assistant_message = choices[0].get('message', {})
                if assistant_message.get('content'):
                    messages.append({"role": "assistant", "content": assistant_message['content']})
        
        messages.append({
            "role": "assistant",
            "content": f"工具执行结果: {result[:500]}..."
        })
    
    return f"错误：达到最大迭代次数（{max_iterations}），任务未能完成"


def run_test_1():
    print("\n" + "=" * 70)
    print("测试1：文件搜索链式调用")
    print("=" * 70)
    print("任务：请查找 practice06 目录下所有包含'def'关键词的文件，并总结这些文件的主要内容\n")
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    practice06_path = os.path.join(project_root, 'practice06')
    
    user_request = f"请查找 {practice06_path} 目录下所有包含'def'关键词的文件，并总结这些文件的主要内容"
    
    result = execute_chained_tool_call(user_request, max_iterations=10)
    
    print(f"\n测试1完成！\n结果: {result}")
    return result


def run_test_2():
    print("\n" + "=" * 70)
    print("测试2：多文件操作")
    print("=" * 70)
    print("任务：读取 1.txt 和 2.txt 两个文件，文件内容的都是正整数，把两个数相加的和写入 result.txt 文件\n")
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    test_dir = project_root
    
    user_request = f"读取 {test_dir}\\1.txt 和 {test_dir}\\2.txt 两个文件，文件内容的都是正整数，把两个数相加的和写入 result.txt 文件"
    
    result = execute_chained_tool_call(user_request, max_iterations=10)
    
    print(f"\n测试2完成！\n结果: {result}")
    return result


def run_test_3():
    print("\n" + "=" * 70)
    print("测试3：网页处理链式调用")
    print("=" * 70)
    print("任务：访问 https://www.nsu.edu.cn/HTML/news/2024/06/article_3974.html 并总结页面内容，保存到 practice07/summary.txt\n")
    
    project_root = os.path.dirname(os.path.dirname(__file__))
    save_dir = os.path.join(project_root, 'practice07')
    
    user_request = f"访问 https://www.nsu.edu.cn/HTML/news/2024/06/article_3974.html 并总结页面内容，保存到 {save_dir}\\summary.txt"
    
    result = execute_chained_tool_call(user_request, max_iterations=10)
    
    print(f"\n测试3完成！\n结果: {result}")
    return result


def main():
    load_env()
    
    print("\n" + "=" * 70)
    print("     链式工具调用客户端 (practice07)")
    print("=" * 70)
    print("\n功能说明：")
    print("本客户端支持链式工具调用（Chained Tool Calls）")
    print("前一个工具的输出可以作为后一个工具的输入参数")
    print("LLM能够根据中间结果自主决定下一步操作\n")
    
    print("-" * 70)
    print("运行测试请选择：")
    print("  1 - 测试1：文件搜索链式调用")
    print("  2 - 测试2：多文件操作")
    print("  3 - 测试3：网页处理链式调用")
    print("  4 - 运行所有测试")
    print("  5 - 自定义请求")
    print("-" * 70)
    
    choice = input("\n请输入选项 (1/2/3/4/5): ").strip()
    
    if choice == '1':
        run_test_1()
    elif choice == '2':
        run_test_2()
    elif choice == '3':
        run_test_3()
    elif choice == '4':
        run_test_1()
        run_test_2()
        run_test_3()
        print("\n所有测试完成！")
    elif choice == '5':
        user_request = input("请输入您的请求: ").strip()
        if user_request:
            result = execute_chained_tool_call(user_request, max_iterations=10)
            print(f"\n结果: {result}")
    else:
        print("无效选项")


if __name__ == "__main__":
    main()
