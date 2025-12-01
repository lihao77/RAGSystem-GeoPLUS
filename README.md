# RAGSystem - 时空知识图谱问答系统

基于知识图谱的智能问答系统，整合时序推理、空间分析和因果追踪功能。

## 快速启动

### 环境准备

1. **安装 Neo4j 数据库**
   - 下载并安装 [Neo4j Desktop](https://neo4j.com/download/)
   - 创建数据库实例并启动

2. **安装依赖**
   ```bash
   # 后端依赖
   cd backend
   pip install -r requirements.txt

   # 前端依赖
   cd frontend
   npm install
   ```

3. **配置文件**

   后端配置：
   ```bash
   cd backend
   cp config.example.json config.json
   ```

   编辑 `backend/config.json`，填写API密钥：
   ```json
   {
     "neo4j": {
       "uri": "bolt://localhost:7687",
       "user": "neo4j",
       "password": "your_password"
     },
     "llm": {
       "apiKey": "your_deepseek_api_key"
     }
   }
   ```

   前端配置：
   ```bash
   cd frontend/src
   cp config.example.js config.js
   ```

### 启动服务

**方式一：分别启动**

启动后端：
```bash
cd backend
python app.py
# 后端运行在 http://localhost:5000
```

启动前端：
```bash
cd frontend
npm run dev
# 前端运行在 http://localhost:5173
```

**方式二：一键启动（Windows）**

```bash
start_server.bat
```

### 获取API密钥

- **DeepSeek API Key**: [https://platform.deepseek.com](https://platform.deepseek.com)
- **百度地图API Key**（可选）: [https://lbsyun.baidu.com](https://lbsyun.baidu.com)

## 目录结构

```
RAGSystem/
├── backend/           # 后端服务
│   ├── app.py        # Flask入口
│   ├── config.json   # 配置文件
│   └── requirements.txt
├── frontend/          # 前端应用
│   ├── src/
│   │   └── config.js # 配置文件
│   └── package.json
└── start_server.bat  # 一键启动脚本
```

## 安全说明

⚠️ 配置文件包含敏感信息，已添加到 `.gitignore`，请勿提交到版本控制。
