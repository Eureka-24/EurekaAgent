#!/usr/bin/env python
"""AgentFrame Demo - 交互式测试脚本

此脚本用于测试AgentFrame的核心功能。

使用方法:
1. 设置环境变量或编辑config.env
2. 运行: python examples/demo_agent.py

功能测试:
- LLM对话 (支持 DeepSeek / OpenAI / Anthropic)
- 工具调用 (计算器/搜索/文件操作)
- 多轮对话
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_env():
    """加载环境变量"""
    env_file = project_root / "config.env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


async def select_llm():
    """选择LLM适配器"""
    print("\n" + "=" * 60)
    print("AgentFrame 演示程序")
    print("=" * 60)
    
    print("\n请选择LLM提供商:")
    print("1. DeepSeek (推荐，默认)")
    print("2. OpenAI")
    print("3. Anthropic (Claude)")
    print("4. 使用环境变量配置")
    
    choice = input("\n请输入选择 (1-4): ").strip()
    
    if choice == "1":
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            api_key = input("请输入 DeepSeek API Key: ").strip()
            os.environ["DEEPSEEK_API_KEY"] = api_key
        
        from agentframe.llm.deepseek import DeepSeekAdapter
        return DeepSeekAdapter(api_key=api_key)
    
    elif choice == "2":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            api_key = input("请输入 OpenAI API Key: ").strip()
            os.environ["OPENAI_API_KEY"] = api_key
        
        from agentframe.llm.openai import OpenAIAdapter
        return OpenAIAdapter(api_key=api_key)
    
    elif choice == "3":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            api_key = input("请输入 Anthropic API Key: ").strip()
            os.environ["ANTHROPIC_API_KEY"] = api_key
        
        from agentframe.llm.anthropic import AnthropicAdapter
        return AnthropicAdapter(api_key=api_key)
    
    else:
        # 自动检测
        if os.environ.get("DEEPSEEK_API_KEY"):
            from agentframe.llm.deepseek import DeepSeekAdapter
            return DeepSeekAdapter(api_key=os.environ["DEEPSEEK_API_KEY"])
        elif os.environ.get("OPENAI_API_KEY"):
            from agentframe.llm.openai import OpenAIAdapter
            return OpenAIAdapter(api_key=os.environ["OPENAI_API_KEY"])
        elif os.environ.get("ANTHROPIC_API_KEY"):
            from agentframe.llm.anthropic import AnthropicAdapter
            return AnthropicAdapter(api_key=os.environ["ANTHROPIC_API_KEY"])
        else:
            raise ValueError("请设置 LLM API Key 环境变量")


async def demo_basic_chat(agent):
    """演示基础对话"""
    print("\n" + "-" * 40)
    print("【演示1】基础对话")
    print("-" * 40)
    
    session = agent.create_session(user_id="demo_user")
    print(f"会话已创建: {session.id}")
    
    questions = [
        "你好，请介绍一下你自己",
        "你能做什么？",
        "用一句话总结今天的内容"
    ]
    
    for question in questions:
        print(f"\n用户: {question}")
        print("Agent: ", end="", flush=True)
        
        response = await agent.chat(session.id, question)
        print(response.content)


async def demo_calculator(agent):
    """演示计算器工具"""
    print("\n" + "-" * 40)
    print("【演示2】计算器工具")
    print("-" * 40)
    
    # 添加工具
    from agentframe.tools.builtins.calculator import calculator
    agent.add_tool(
        name="calculator",
        handler=calculator,
        description="执行数学计算，支持基本运算、三角函数、对数等"
    )
    
    session = agent.create_session(user_id="demo_user")
    
    questions = [
        "请计算: 2 + 3 * 4",
        "计算 sin(π/2) 的值",
        "求平方根: sqrt(144)",
        "计算 log(100)"
    ]
    
    for question in questions:
        print(f"\n用户: {question}")
        print("Agent: ", end="", flush=True)
        response = await agent.chat(session.id, question)
        print(response.content)


async def demo_file_ops(agent):
    """演示文件操作工具"""
    print("\n" + "-" * 40)
    print("【演示3】文件操作工具")
    print("-" * 40)
    
    from agentframe.tools.builtins.file_ops import file_ops
    agent.add_tool(
        name="file_ops",
        handler=file_ops,
        description="执行文件系统操作，包括读写文件、创建目录等"
    )
    
    session = agent.create_session(user_id="demo_user")
    
    # 演示对话
    questions = [
        "在当前目录下创建一个名为 test_demo.txt 的文件，内容为 'Hello from AgentFrame!'",
        "读取刚才创建的文件内容"
    ]
    
    for question in questions:
        print(f"\n用户: {question}")
        print("Agent: ", end="", flush=True)
        response = await agent.chat(session.id, question)
        print(response.content)


async def demo_web_search(agent):
    """演示网络搜索工具"""
    print("\n" + "-" * 40)
    print("【演示4】网络搜索工具")
    print("-" * 40)
    
    from agentframe.tools.builtins.web_search import web_search
    agent.add_tool(
        name="web_search",
        handler=web_search,
        description="搜索互联网获取信息"
    )
    
    session = agent.create_session(user_id="demo_user")
    
    question = input("\n请输入搜索关键词（或直接回车跳过此演示）: ").strip()
    
    if question:
        print(f"\n用户: 搜索 '{question}'")
        print("Agent: ", end="", flush=True)
        response = await agent.chat(session.id, question)
        print(response.content)
    else:
        print("跳过网络搜索演示")


async def demo_multi_turn(agent):
    """演示多轮对话"""
    print("\n" + "-" * 40)
    print("【演示5】多轮对话（上下文记忆）")
    print("-" * 40)
    
    session = agent.create_session(user_id="demo_user")
    print(f"会话ID: {session.id}")
    print("开始多轮对话 (输入 'quit' 退出):\n")
    
    while True:
        user_input = input("用户: ").strip()
        if user_input.lower() == "quit":
            break
        if not user_input:
            continue
        
        print("Agent: ", end="", flush=True)
        response = await agent.chat(session.id, user_input)
        print(response.content)
        
        print(f"  [对话轮数: {session.turn_count}]")


async def main():
    """主函数"""
    load_env()
    
    try:
        # 选择LLM
        llm = await select_llm()
        print(f"\n已连接: {llm.provider} - {llm.default_model}")
        
        # 创建Agent
        from agentframe.core.agent import Agent
        
        system_prompt = """你是一个有帮助的AI助手。你可以:
- 回答问题和进行对话
- 使用计算器进行数学计算（表达式如 2+3, sqrt(16), sin(0)）
- 读写文件（操作如 write, read, list, exists）
- 搜索网络信息

请根据用户的问题，适当使用工具来帮助回答。"""
        
        agent = Agent(
            name="AgentFrame Demo",
            system_prompt=system_prompt,
            llm=llm,
        )
        
        # 显示菜单
        print("\n" + "=" * 60)
        print("功能演示菜单")
        print("=" * 60)
        print("1. 基础对话")
        print("2. 计算器工具")
        print("3. 文件操作工具")
        print("4. 网络搜索工具")
        print("5. 多轮对话（交互模式）")
        print("6. 运行所有演示")
        print("0. 退出")
        
        choice = input("\n请选择 (0-6): ").strip()
        
        if choice == "1":
            await demo_basic_chat(agent)
        elif choice == "2":
            await demo_calculator(agent)
        elif choice == "3":
            await demo_file_ops(agent)
        elif choice == "4":
            await demo_web_search(agent)
        elif choice == "5":
            await demo_multi_turn(agent)
        elif choice == "6":
            await demo_basic_chat(agent)
            await demo_calculator(agent)
            await demo_file_ops(agent)
            await demo_web_search(agent)
        else:
            print("退出")
        
        print("\n" + "=" * 60)
        print("演示结束!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n已退出")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
