# RAGSystem - 时空知识图谱问答系统

基于广西水旱灾害的智能问答助手，整合时序推理、空间分析和因果追踪功能。

## 系统特性

- 🔍 **智能问答**：基于知识图谱的自然语言查询
- ⏱️ **时序推理**：追踪事件的时间演化过程
- 🗺️ **空间分析**：地理位置关联和空间邻近查询
- 🔗 **因果追踪**：发现和分析事件之间的因果关系
- 📊 **可视化展示**：知识图谱可视化、地图展示、状态树展示

## 技术栈

### 后端
- Python 3.8+
- Flask
- Neo4j 图数据库
- DeepSeek API (LLM服务)
- 百度地图API (地理编码服务)

### 前端
- Vue 3
- Element Plus
- ECharts
- Cesium (3D地图)
- Force-Graph (图谱可视化)
- OpenRouter API (前端LLM调用，可选)

## 快速开始

### 1. 环境准备

#### 安装 Neo4j 数据库

1. 下载并安装 [Neo4j Desktop](https://neo4j.com/download/)
2. 创建一个新的数据库实例
3. 设置用户名和密码（默认：neo4j / neo4j）
4. 启动数据库服务

#### 安装 Python 环境

确保已安装 Python 3.8 或更高版本：

```bash
python --version
```

#### 安装 Node.js 环境

确保已安装 Node.js 14 或更高版本：

```bash
node --version
npm --version
```

### 2. 后端配置

#### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 配置文件

复制配置模板并修改：

```bash
cd backend
cp config.example.json config.json
```

编辑 `backend/config.json` 文件：

```json
{
  "neo4j": {
    "uri": "bolt://localhost:7687",
    "user": "neo4j",
    "password": "your_neo4j_password"
  },
  "llm": {
    "apiEndpoint": "https://api.deepseek.com/v1",
    "apiKey": "your_deepseek_api_key",
    "modelName": "deepseek-chat"
  },
  "geocoding": {
    "service": "baidu",
    "apiKey": "your_baidu_map_api_key"
  },
  "system": {
    "maxWorkers": 4,
    "dataDir": "/path/to/your/data",
    "validateData": true,
    "pythonPath": "/path/to/python"
  }
}
```

**获取 DeepSeek API Key:**
1. 访问 [DeepSeek](https://platform.deepseek.com/)
2. 注册账号并创建 API Key
3. 将 Key 填入配置文件的 `llm.apiKey`

**获取百度地图 API Key（可选）:**
1. 访问 [百度地图开放平台](https://lbsyun.baidu.com/)
2. 注册并创建应用
3. 将 Key 填入配置文件的 `geocoding.apiKey`

#### 启动后端服务

```bash
cd backend
python app.py
```

后端服务将在 http://localhost:5000 启动

### 3. 前端配置

#### 安装依赖

```bash
cd frontend
npm install
```

#### 配置文件

复制配置模板并修改：

```bash
cd frontend/src
cp config.example.js config.js
```

编辑 `frontend/src/config.js`，填入您的配置信息：

```javascript
// Neo4j数据库连接配置
export const neo4jConfig = {
  uri: "bolt://localhost:7687",
  user: "neo4j",
  password: "your_neo4j_password"
};

// 地理编码服务配置
export const geocodingConfig = {
  service: "baidu", // 可选: "baidu" 或 "amap"
  apiKey: "your_baidu_map_api_key" // 请填入您的百度地图API密钥
};

// LLM服务配置（前端可选，用于某些前端功能）
export const llmConfig = {
  apiEndpoint: "https://openrouter.ai/api/v1",
  apiKey: "", // 请填入您的OpenRouter API Key (可选)
  modelName: "tngtech/deepseek-r1t-chimera:free"
};

// 系统配置
export const systemConfig = {
  maxWorkers: 4,
  dataDir: "path/to/your/data",
  outputDir: "path/to/your/output"
};

// Cesium地图配置（可选）
export const cesiumConfig = {
  accessToken: "your_cesium_token" // 从 https://cesium.com/ion/tokens 获取
};
```

**API Key 获取说明：**

1. **OpenRouter API Key（前端可选）:**
   - 访问 [OpenRouter](https://openrouter.ai/keys)
   - 注册账号并创建 API Key
   - 某些前端功能可能需要此配置

2. **Cesium Token（可选）:**
   - 访问 [Cesium Ion](https://cesium.com/ion/tokens)
   - 注册账号并创建访问令牌
   - 用于3D地图展示功能

3. **百度地图API Key（可选）:**
   - 访问 [百度地图开放平台](https://lbsyun.baidu.com/)
   - 注册并创建应用获取API Key
   - 用于地理编码服务
```

#### 启动前端服务

```bash
cd frontend
npm run dev
```

前端服务将在 http://localhost:5173 启动

### 4. 一键启动（Windows）

如果您在 Windows 系统上，可以直接运行：

```bash
start_server.bat
```

这将自动启动后端和前端服务。

## 使用指南

### 导入数据

1. 访问系统的"数据导入"页面
2. 上传您的数据文件（支持CSV、JSON等格式）
3. 配置字段映射
4. 开始导入

### 提问示例

系统支持多种类型的智能问答：

#### 时序分析
```
2020年潘厂水库发生了什么，请展示完整的时序演化过程
```

#### 统计分析
```
2017年7月广西因灾害导致的经济损失和人员伤亡情况
```

#### 因果追踪
```
潘厂水库2020年泄洪造成了什么影响？追踪完整的因果链
```

#### 空间关联
```
查询南宁市及其周边地区在2023年的灾害关联关系
```

### 可视化功能

- **知识图谱视图**：展示实体和关系的网络结构
- **地图视图**：在地图上显示地理位置相关的实体
- **状态树视图**：展示实体的状态演化树
- **分屏视图**：同时查看多个视角

## 目录结构

```
RAGSystem/
├── backend/                 # 后端服务
│   ├── app.py              # Flask 应用入口
│   ├── routes/             # API 路由
│   ├── utils/              # 工具函数
│   ├── config.json         # 配置文件（需自行创建）
│   └── requirements.txt    # Python 依赖
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   ├── components/    # 可复用组件
│   │   ├── api/          # API 接口
│   │   └── config.js     # 配置文件（需自行创建）
│   ├── package.json       # Node 依赖
│   └── vite.config.js     # Vite 配置
├── start_server.bat       # Windows 一键启动脚本
└── README.md             # 本文档
```

## API 文档

### GraphRAG 问答接口

**POST** `/api/graphrag/query`

请求体：
```json
{
  "question": "您的问题",
  "history": []
}
```

响应：
```json
{
  "success": true,
  "data": {
    "answer": "AI回答",
    "tool_calls": [...],
    "graph_data": {...}
  }
}
```

### 更多接口

详见 `backend/routes/` 目录下的路由文件。

## 常见问题

### 1. Neo4j 连接失败

- 确保 Neo4j 数据库已启动
- 检查配置文件中的连接信息是否正确
- 验证用户名和密码

### 2. DeepSeek API 调用失败

- 检查后端 `config.json` 中的 API Key 是否正确
- 确认账户有足够的余额或配额
- 检查网络连接是否正常
- 查看后端日志获取详细错误信息

**注意：** 后端使用 DeepSeek API，前端可选配置 OpenRouter API

### 3. 前端无法连接后端

- 确保后端服务已启动
- 检查后端端口是否被占用
- 确认防火墙设置

### 4. 数据导入失败

- 检查数据格式是否正确
- 确认 Neo4j 数据库有足够的存储空间
- 查看后端日志获取详细错误信息

## 安全说明

⚠️ **重要提示**：

1. **切勿将配置文件提交到版本控制**
   - `frontend/src/config.js` 和 `backend/config.json` 已在 `.gitignore` 中
   - 这些文件包含敏感的 API 密钥和密码

2. **定期更换 API 密钥**
   - 如果密钥泄露，立即在服务提供商处撤销

3. **使用环境变量**（推荐）
   - 在生产环境中，建议使用环境变量管理敏感信息

## 开发计划

- [ ] 支持更多 LLM 模型
- [ ] 增强时序推理能力
- [ ] 添加用户权限管理
- [ ] 支持多语言
- [ ] 优化图谱可视化性能

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [GitHub Issue](https://github.com/lihao77/RAGSystem/issues)

---

**⚠️ 数据隐私声明**：本系统处理的数据可能包含敏感信息，请确保遵守相关数据保护法规。
