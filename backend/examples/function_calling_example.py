# -*- coding: utf-8 -*-
"""
Function Calling 使用示例
演示如何使用封装好的工具进行知识图谱检索
"""

import requests
import json

BASE_URL = "http://localhost:5000"

print("Function Calling 示例集合")
print("=" * 60)

# 示例1：获取工具列表
print("\n示例1：获取所有可用工具")
response = requests.get(f"{BASE_URL}/api/function-call/tools")
print(f"可用工具数量: {response.json()['data']['count']}")

# 示例2：简单搜索
print("\n示例2：搜索潘厂水库")
response = requests.post(
    f"{BASE_URL}/api/function-call/execute",
    json={
        "tool_name": "search_knowledge_graph",
        "arguments": {"keyword": "潘厂水库"}
    }
)
print(f"搜索结果: {response.json()}")

# 示例3：自然语言查询
print("\n示例3：自然语言查询")
response = requests.post(
    f"{BASE_URL}/api/function-call/chat",
    json={
        "messages": [
            {"role": "user", "content": "潘厂水库2020年的情况"}
        ]
    }
)
print(f"AI回答: {response.json()['data']['answer']}")

print("\n示例运行完成！详细文档请查看 FUNCTION_CALLING_README.md")
