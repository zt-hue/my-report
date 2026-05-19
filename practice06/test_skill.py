# test_skill.py
# 测试 practice06 的技能调用功能

import os
import sys
import json
import io

# 设置标准输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加上级目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入工具函数
from practice06.tool_client import list_available_skills, load_skill_content, load_env, call_llm

def test_list_available_skills():
    print("[TEST] 测试 list_available_skills")
    result = list_available_skills()
    print("技能列表:", result)
    
    data = json.loads(result)
    assert data.get('status') == 'success', "技能列表获取失败"
    assert len(data.get('skills', [])) >= 1, "未找到技能"
    
    skills = data.get('skills', [])
    notice_skill = next((s for s in skills if s['name'] == 'notice'), None)
    assert notice_skill is not None, "未找到 notice 技能"
    assert '通知' in notice_skill['description'], "技能描述不正确"
    
    print("[OK] list_available_skills 测试通过")
    return skills

def test_load_skill_content():
    print("\n[TEST] 测试 load_skill_content")
    result = load_skill_content('notice')
    print("技能内容获取成功")
    
    data = json.loads(result)
    assert data.get('status') == 'success', "技能内容加载失败"
    assert len(data.get('data', '')) > 0, "技能内容为空"
    
    content = data.get('data', '')
    assert '标题格式' in content, "技能内容不完整"
    
    print("[OK] load_skill_content 测试通过")
    return content

def test_llm_with_skill():
    print("\n[TEST] 测试 LLM 使用技能")
    
    load_env()
    
    skills_result = list_available_skills()
    skills_data = json.loads(skills_result)
    skills_list = skills_data.get('skills', [])
    skills_json = json.dumps({"skills": skills_list}, ensure_ascii=False)
    
    content_result = load_skill_content('notice')
    content_data = json.loads(content_result)
    skill_content = content_data.get('data', '')
    
    print("\n--- 场景1：用户不指定部门 ---")
    system_prompt = "你是一个具有技能调用能力的AI助手。\n\n可用技能列表:\n" + skills_json + "\n\n技能内容（notice）:\n" + skill_content + "\n\n请根据 notice 技能的要求撰写通知，注意通知格式要求。"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "帮我撰写关于五一节放假的通知"}
    ]
    
    response = call_llm(messages)
    if response and isinstance(response, dict):
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
        print("LLM响应开头:", content[:50])
        
        if content.startswith('xx部通知'):
            print("[OK] 场景1 测试通过：通知以xx部通知开头")
        else:
            print("[FAIL] 场景1 测试失败：通知未以xx部通知开头")
    
    print("\n--- 场景2：用户指定部门为销售部 ---")
    messages2 = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "我是销售部的，帮我撰写关于五一节放假的通知"}
    ]
    
    response2 = call_llm(messages2)
    if response2 and isinstance(response2, dict):
        content2 = response2.get('choices', [{}])[0].get('message', {}).get('content', '')
        print("LLM响应开头:", content2[:50])
        
        if content2.startswith('销售部通知'):
            print("[OK] 场景2 测试通过：通知以销售部通知开头")
        else:
            print("[FAIL] 场景2 测试失败：通知未以销售部通知开头")

def main():
    print("=== practice06 技能功能测试 ===")
    
    skills = test_list_available_skills()
    
    content = test_load_skill_content()
    
    test_llm_with_skill()
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
