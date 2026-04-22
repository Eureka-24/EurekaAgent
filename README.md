# AgentFrame

企业级AI Agent开发框架 - 灵活、可扩展的Agent基础设施

## 快速开始

### 1. 环境准备

```bash
# 激活conda环境
conda activate agentframe

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
# 复制配置示例
cp .env.example .env

# 编辑 .env 填写API密钥
```

### 3. 运行

```bash
# 启动API服务
uvicorn agentframe.api.main:app --reload

# 访问文档
# http://localhost:8000/docs
```

## 项目结构

```
agentframe/
├── core/           # 核心模块
├── llm/            # LLM适配层
├── tools/          # 工具系统
├── memory/         # 记忆管理
├── rag/            # RAG模块
├── storage/        # 存储层
└── api/            # API层
```

## 文档

- [PRD文档](./AgentFrame-PRD.md)
- [技术规格](./SPEC.md)
- [开发任务](./todo_list.md)

## 许可证

Apache-2.0
