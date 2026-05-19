import os
import json
import http.client
import ssl
from urllib.parse import urlparse
import sys
import stat

# 读取.env文件
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

# 工具函数1：列出某个目录下的文件（包括基本属性、大小等信息）
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

# 工具函数2：修改某个目录下某个文件的名字
def rename_file(directory, old_name, new_name):
    try:
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)
        os.rename(old_path, new_path)
        return json.dumps({"status": "success", "message": f"文件已重命名为 {new_name}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

# 工具函数3：删除某个目录下的某个文件
def delete_file(directory, file_name):
    try:
        file_path = os.path.join(directory, file_name)
        os.remove(file_path)
        return json.dumps({"status": "success", "message": "文件已删除"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

# 工具函数4：在某个目录下新建1个文件，并且写入内容
def create_file(directory, file_name, content):
    try:
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return json.dumps({"status": "success", "message": "文件已创建"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

# 工具函数5：读取某个目录下的某个文件的内容
def read_file(directory, file_name):
    try:
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return json.dumps({"status": "success", "data": content}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

# 调用LLM API（非流式，用于工具调用）
def call_llm(messages, tools=None):
    # 获取配置
    base_url = os.getenv('BASE_URL')
    model = os.getenv('MODEL')
    api_key = os.getenv('API_KEY')
    
    if not all([base_url, model, api_key]):
        print("错误：请在.env文件中配置BASE_URL、MODEL和API_KEY")
        exit(1)
    
    # 解析URL
    parsed_url = urlparse(base_url)
    host = parsed_url.netloc
    path = parsed_url.path.rstrip('/') + '/chat/completions'
    protocol = parsed_url.scheme
    
    # 准备请求数据
    data = {
        "model": model,
        "messages": messages,
        "temperature": float(os.getenv('TEMPERATURE', '0.7')),
        "max_tokens": int(os.getenv('MAX_TOKENS', '8192'))
    }
    
    # 如果提供了工具，添加到请求中
    if tools:
        data["tools"] = tools
        data["tool_choice"] = "auto"
    
    # 根据协议选择连接类型
    if protocol == 'https':
        # 创建不验证证书的 SSL 上下文
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
        response_data = json.loads(response.read().decode())
        
        if response.status == 200:
            return response_data
        else:
            print(f"API错误: {response_data.get('error', {}).get('message', '未知错误')}")
            return None
    finally:
        conn.close()

# 流式调用LLM API（用于普通对话）
def stream_llm(messages):
    # 获取配置
    base_url = os.getenv('BASE_URL')
    model = os.getenv('MODEL')
    api_key = os.getenv('API_KEY')
    
    if not all([base_url, model, api_key]):
        print("错误：请在.env文件中配置BASE_URL、MODEL和API_KEY")
        exit(1)
    
    # 解析URL
    parsed_url = urlparse(base_url)
    host = parsed_url.netloc
    path = parsed_url.path.rstrip('/') + '/chat/completions'
    protocol = parsed_url.scheme
    
    # 准备请求数据
    data = {
        "model": model,
        "messages": messages,
        "temperature": float(os.getenv('TEMPERATURE', '0.7')),
        "max_tokens": int(os.getenv('MAX_TOKENS', '8192')),
        "stream": True
    }
    
    # 根据协议选择连接类型
    if protocol == 'https':
        # 创建不验证证书的 SSL 上下文
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
        
        if response.status != 200:
            error_data = json.loads(response.read().decode())
            print(f"API错误: {error_data.get('error', {}).get('message', '未知错误')}")
            return None
        
        # 处理流式响应
        full_response = ""
        for line in response:
            line = line.decode().strip()
            if not line:
                continue
            if line.startswith('data: '):
                line = line[6:]
                if line == '[DONE]':
                    break
                try:
                    chunk = json.loads(line)
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        delta = chunk['choices'][0].get('delta', {})
                        if 'content' in delta:
                            content = delta['content']
                            if content is not None:
                                print(content, end='', flush=True)
                                full_response += content
                except json.JSONDecodeError:
                    pass
        print()  # 换行
        return full_response
    finally:
        conn.close()

# 执行工具调用
def execute_tool_call(tool_call):
    # 解析OpenAI格式的工具调用
    if tool_call.get('type') == 'function':
        function = tool_call.get('function', {})
        tool_name = function.get('name')
        # 解析arguments（可能是字符串或对象）
        arguments = function.get('arguments', {})
        if isinstance(arguments, str):
            try:
                tool_args = json.loads(arguments)
            except json.JSONDecodeError:
                tool_args = {}
        else:
            tool_args = arguments
    else:
        # 兼容其他格式
        tool_name = tool_call.get('name')
        tool_args = tool_call.get('arguments', {})
    
    print(f"执行工具: {tool_name}")
    print(f"参数: {tool_args}")
    
    if tool_name == "list_directory":
        path = tool_args.get('path')
        result = list_files(path)
    elif tool_name == "rename_file":
        directory = tool_args.get('directory')
        old_name = tool_args.get('old_name')
        new_name = tool_args.get('new_name')
        result = rename_file(directory, old_name, new_name)
    elif tool_name == "delete_file":
        directory = tool_args.get('directory')
        file_name = tool_args.get('file_name')
        result = delete_file(directory, file_name)
    elif tool_name == "create_file":
        directory = tool_args.get('directory')
        file_name = tool_args.get('file_name')
        content = tool_args.get('content')
        result = create_file(directory, file_name, content)
    elif tool_name == "read_file":
        directory = tool_args.get('directory')
        file_name = tool_args.get('file_name')
        result = read_file(directory, file_name)
    else:
        result = f"错误：未知的工具 {tool_name}"
    
    print(f"工具执行结果: {result}")
    return result

def main():
    # 加载环境变量
    load_env()
    
    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "列出指定目录下的所有文件和目录，包括基本属性",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "目录路径"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "rename_file",
                "description": "修改指定目录下的文件名称",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "old_name": {
                            "type": "string",
                            "description": "原文件名"
                        },
                        "new_name": {
                            "type": "string",
                            "description": "新文件名"
                        }
                    },
                    "required": ["directory", "old_name", "new_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_file",
                "description": "删除指定目录下的文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "file_name": {
                            "type": "string",
                            "description": "文件名"
                        }
                    },
                    "required": ["directory", "file_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_file",
                "description": "在指定目录下创建新文件并写入内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "file_name": {
                            "type": "string",
                            "description": "文件名"
                        },
                        "content": {
                            "type": "string",
                            "description": "文件内容"
                        }
                    },
                    "required": ["directory", "file_name", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取指定目录下的文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "file_name": {
                            "type": "string",
                            "description": "文件名"
                        }
                    },
                    "required": ["directory", "file_name"]
                }
            }
        }
    ]
    
    # 系统提示词
    system_prompt = """你是一个具有文件操作能力的AI助手，能够执行以下操作：

1. 列出目录内容：使用 list_directory 工具查看指定目录下的文件和目录
2. 重命名文件：使用 rename_file 工具修改文件名称
3. 删除文件：使用 delete_file 工具删除指定文件
4. 创建文件：使用 create_file 工具创建新文件并写入内容
5. 读取文件：使用 read_file 工具读取指定文件的内容

当用户请求涉及文件操作时，请使用相应的工具进行操作，不要自行猜测或模拟结果。

工具使用格式：
- 思考：分析用户需求，确定需要使用的工具
- 工具调用：使用指定的工具函数和参数
- 结果处理：根据工具执行结果向用户提供反馈"""
    
    # 初始化聊天历史
    chat_history = [
        {"role": "system", "content": system_prompt}
    ]
    
    print("=== LLM 工具调用客户端 ===")
    print("输入消息开始聊天，按 Ctrl+C 退出")
    print("========================")
    print("可用工具：list_files, rename_file, delete_file, create_file, read_file")
    print()
    
    try:
        while True:
            # 获取用户输入
            user_input = input("你: ")
            
            # 添加用户消息到历史
            chat_history.append({"role": "user", "content": user_input})
            
            # 显示助手回复
            print("助手: ", end='', flush=True)
            
            # 调用LLM（带工具）
            response = call_llm(chat_history, tools)
            
            if not response:
                print("请求失败")
                continue
            
            # 处理响应
            choice = response.get('choices', [{}])[0]
            message = choice.get('message', {})
            
            # 检查是否有工具调用
            if message.get('tool_calls'):
                # 处理工具调用
                for tool_call in message.get('tool_calls', []):
                    # 执行工具
                    tool_result = execute_tool_call(tool_call)
                    
                    # 添加助手消息（工具调用）到历史
                    chat_history.append(message)
                    
                    # 添加工具执行结果到历史
                    chat_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get('id'),
                        "name": tool_call.get('function', {}).get('name'),
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
                
                # 再次调用LLM获取最终响应
                final_response = stream_llm(chat_history)
                if final_response:
                    # 添加最终回复到历史
                    chat_history.append({"role": "assistant", "content": final_response})
            else:
                # 普通响应
                content = message.get('content', '')
                print(content)
                # 添加助手回复到历史
                chat_history.append(message)
            
            print()  # 空行分隔
    except KeyboardInterrupt:
        print("\n退出工具调用客户端")
        sys.exit(0)

if __name__ == "__main__":
    main()