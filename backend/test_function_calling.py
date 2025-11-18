# -*- coding: utf-8 -*-
"""
Function Calling 快速测试脚本
用于验证功能是否正常工作
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from tools.function_definitions import get_tool_definitions

def test_tool_definitions():
    """测试工具定义"""
    print("测试1: 获取工具定义")
    print("-" * 60)
    
    tools = get_tool_definitions()
    print(f"✓ 成功获取 {len(tools)} 个工具定义")
    
    for tool in tools:
        name = tool['function']['name']
        desc = tool['function']['description'][:50]
        print(f"  - {name}: {desc}...")
    
    print()


def test_search_tool():
    """测试工具定义完整性"""
    print("测试2: 工具参数验证")
    print("-" * 60)
    
    tools = get_tool_definitions()
    
    # 检查每个工具的参数定义
    for tool in tools:
        func = tool['function']
        params = func['parameters']
        
        assert 'type' in params, f"{func['name']}: 缺少参数 type"
        assert 'properties' in params, f"{func['name']}: 缺少 properties"
        
        print(f"✓ {func['name']} 参数定义完整")
    
    print()


def test_tool_schema():
    """测试工具定义的格式"""
    print("测试3: 工具定义格式验证")
    print("-" * 60)
    
    tools = get_tool_definitions()
    
    for tool in tools:
        # 验证必需字段
        assert 'type' in tool, "缺少 type 字段"
        assert tool['type'] == 'function', "type 必须是 function"
        assert 'function' in tool, "缺少 function 字段"
        
        func = tool['function']
        assert 'name' in func, "缺少 name 字段"
        assert 'description' in func, "缺少 description 字段"
        assert 'parameters' in func, "缺少 parameters 字段"
        
        print(f"✓ {func['name']} 格式正确")
    
    print()


def print_tool_summary():
    """打印工具摘要"""
    print("=" * 60)
    print("Function Calling 工具摘要")
    print("=" * 60)
    
    tools = get_tool_definitions()
    
    print(f"\n共有 {len(tools)} 个工具可用：\n")
    
    for i, tool in enumerate(tools, 1):
        func = tool['function']
        print(f"{i}. {func['name']}")
        print(f"   描述: {func['description']}")
        
        params = func['parameters']['properties']
        required = func['parameters'].get('required', [])
        
        if params:
            print(f"   参数:")
            for param_name, param_info in params.items():
                req_mark = "* " if param_name in required else "  "
                print(f"     {req_mark}{param_name}: {param_info.get('description', 'N/A')[:60]}")
        print()
    
    print("=" * 60)
    print("\n使用方式：")
    print("1. 启动后端服务: python app.py")
    print("2. 获取工具: GET /api/function-call/tools")
    print("3. 执行工具: POST /api/function-call/execute")
    print("4. 完整对话: POST /api/function-call/chat")
    print("\n详细文档: FUNCTION_CALLING_README.md")
    print("示例代码: examples/function_calling_example.py")
    print()


if __name__ == "__main__":
    print("\n")
    print("*" * 60)
    print(" Function Calling 功能测试")
    print("*" * 60)
    print()
    
    try:
        test_tool_definitions()
        test_search_tool()
        test_tool_schema()
        print_tool_summary()
        
        print("✓ 所有测试通过！")
        print("\n下一步：启动服务器并测试 API 接口")
        print("  python app.py")
        print()
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
