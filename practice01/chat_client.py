import os
import json
import http.client
import ssl
from urllib.parse import urlparse
import sys
import threading
import time

# 读取.env文件
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(env_path):
        print(f"错误：{env_path} 文件不存在，请从 env.example 复制并填写正确参数")
        exit(1)
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value

# 流式调用LLM API
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
        first_content = True
        
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
                        if 'content' in delta and delta['content'] is not None:
                            content = delta['content']
                            # 在新的一行输出内容
                            if first_content:
                                print()
                                print(content, end='', flush=True)
                                first_content = False
                            else:
                                print(content, end='', flush=True)
                            full_response += content
                except json.JSONDecodeError:
                    pass
        print()  # 换行
        return full_response
    finally:
        conn.close()

def main():
    # 加载环境变量
    load_env()
    
    # 初始化聊天历史
    chat_history = []
    
    print("=== LLM 聊天客户端 ===")
    print("输入消息开始聊天，按 Ctrl+C 退出")
    print("====================\n")
    
    try:
        while True:
            # 获取用户输入（不显示加载动画）
            user_input = input("你: ")
            
            # 添加用户消息到历史
            chat_history.append({"role": "user", "content": user_input})
            
            # 显示助手回复冒号
            print("助手:", end='', flush=True)
            
            # 启动加载动画：每0.5秒显示一个点
            loading_stop_event = threading.Event()
            
            def show_loading():
                """每0.5秒显示一个点"""
                while not loading_stop_event.is_set():
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    loading_stop_event.wait(0.5)
            
            loading_thread = threading.Thread(target=show_loading, daemon=True)
            loading_thread.start()
            
            # 调用LLM并流式输出
            assistant_response = stream_llm(chat_history)
            
            # 停止加载动画
            loading_stop_event.set()
            loading_thread.join(timeout=0.5)
            
            print()  # 换行
            
            if assistant_response is None:
                print("请求失败")
            elif assistant_response:
                # 添加助手回复到历史
                chat_history.append({"role": "assistant", "content": assistant_response})
            
            print()  # 空行分隔
    except KeyboardInterrupt:
        print("\n退出聊天客户端")
        sys.exit(0)
    except EOFError:
        print("\n输入流结束，退出聊天客户端")
        sys.exit(0)

if __name__ == "__main__":
    main()
