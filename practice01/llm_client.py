#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import http.client
import ssl
from urllib.parse import urlparse
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

# 调用LLM API
def call_llm(prompt):
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
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": float(os.getenv('TEMPERATURE', '0.7')),
        "max_tokens": int(os.getenv('MAX_TOKENS', '8192'))
    }
    
    # 根据协议选择连接类型
    if protocol == 'https':
        # 创建不验证证书的 SSL 上下文（与 chat_client.py 保持一致）
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
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        conn.request('POST', path, json.dumps(data), headers)
        response = conn.getresponse()
        response_data = json.loads(response.read().decode())
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        if response.status == 200:
            # 提取token使用情况
            usage = response_data.get('usage', {})
            total_tokens = usage.get('total_tokens', 0)
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            
            # 计算token速度
            token_speed = total_tokens / execution_time if execution_time > 0 else 0
            
            # 打印统计信息
            print(f"\n=== 统计信息 ===")
            print(f"执行时间: {execution_time:.2f} 秒")
            print(f"总Token: {total_tokens}")
            print(f"提示Token: {prompt_tokens}")
            print(f"完成Token: {completion_tokens}")
            print(f"Token速度: {token_speed:.2f} token/s")
            print("================")
            
            return response_data['choices'][0]['message']['content']
        else:
            print(f"API错误: {response_data.get('error', {}).get('message', '未知错误')}")
            return None
    finally:
        conn.close()

if __name__ == "__main__":
    # 加载环境变量
    load_env()
    
    # 测试调用
    prompt = "请介绍你自己"
    print("发送请求到LLM...")
    response = call_llm(prompt)
    
    if response:
        print("\nLLM响应:")
        print(response)
    else:
        print("请求失败")