"""API Service - API服务入口

启动FastAPI服务的入口点。
"""

import argparse
import os
import sys
from pathlib import Path

import structlog

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def load_config():
    """加载配置"""
    from dotenv import load_dotenv
    
    env_file = project_root / "config.env"
    if env_file.exists():
        load_dotenv(env_file)


def create_agent_from_config():
    """从配置创建Agent"""
    from agentframe.core.agent import Agent
    from agentframe.tools.builtins.calculator import calculator
    from agentframe.tools.builtins.web_search import web_search
    from agentframe.tools.builtins.file_ops import file_ops
    
    # 根据环境变量选择LLM
    llm = None
    
    if os.getenv("DEEPSEEK_API_KEY"):
        from agentframe.llm.deepseek import DeepSeekAdapter
        llm = DeepSeekAdapter(api_key=os.getenv("DEEPSEEK_API_KEY"))
    elif os.getenv("OPENAI_API_KEY"):
        from agentframe.llm.openai import OpenAIAdapter
        llm = OpenAIAdapter(api_key=os.getenv("OPENAI_API_KEY"))
    elif os.getenv("ANTHROPIC_API_KEY"):
        from agentframe.llm.anthropic import AnthropicAdapter
        llm = AnthropicAdapter(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # 创建Agent
    agent = Agent(
        name="AgentFrame API",
        system_prompt="你是一个有帮助的AI助手。",
        llm=llm,
    )
    
    # 注册内置工具
    from agentframe.tools.registry import register_tool
    register_tool(
        name="calculator",
        description="执行数学计算，支持基本运算、三角函数、对数等",
        handler=calculator
    )
    register_tool(
        name="web_search",
        description="搜索互联网获取信息",
        handler=web_search
    )
    register_tool(
        name="file_ops",
        description="执行文件系统操作",
        handler=file_ops
    )
    
    return agent


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AgentFrame API Server")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="启用热重载")
    parser.add_argument("--log-level", default="info", help="日志级别")
    
    args = parser.parse_args()
    
    # 加载配置
    load_config()
    
    # 配置日志
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog.stdlib, args.log_level.upper(), structlog.stdlib.INFO)
        )
    )
    
    # 创建Agent
    logger = structlog.get_logger()
    logger.info("starting_agentframe_api", host=args.host, port=args.port)
    
    agent = create_agent_from_config()
    
    # 创建并启动API
    from agentframe.api.routes import create_app
    
    app = create_app(agent=agent)
    
    logger.info("agentframe_api_started", 
                host=args.host, 
                port=args.port,
                docs_url="/docs")
    
    import uvicorn
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
