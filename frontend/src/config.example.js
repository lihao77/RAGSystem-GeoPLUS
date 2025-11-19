/**
 * 系统配置文件模板
 * 使用说明：
 * 1. 复制此文件并重命名为 config.js
 * 2. 填入您自己的API密钥和配置信息
 * 3. config.js 已在 .gitignore 中，不会被提交到版本控制
 */

// Neo4j数据库连接配置
export const neo4jConfig = {
  uri: "bolt://localhost:7687",
  user: "neo4j",
  password: "your_neo4j_password" // 请修改为您的Neo4j密码
};

// 地理编码服务配置
export const geocodingConfig = {
  service: "baidu", // 可选: "baidu" 或 "amap"
  apiKey: "your_baidu_map_api_key" // 请填入您的百度地图API密钥
};

// LLM服务配置
export const llmConfig = {
  apiEndpoint: "https://openrouter.ai/api/v1",
  apiKey: "", // 请填入您的OpenRouter API Key (获取地址: https://openrouter.ai/keys)
  modelName: "tngtech/deepseek-r1t-chimera:free" // 可根据需要修改模型
};

// 系统配置
export const systemConfig = {
  maxWorkers: 4, // 最大并行工作线程数
  dataDir: "path/to/your/data", // 数据目录
  outputDir: "path/to/your/output" // 输出目录
};

// 图谱可视化配置
export const graphConfig = {
  nodeCategories: {
    "基础实体": "#409EFF",
    "状态实体": "#67C23A",
    "地理位置": "#E6A23C",
    "时间": "#F56C6C"
  },
  relationCategories: {
    "状态关系": "#909399",
    "地理关系": "#6B8E23",
    "时间关系": "#8A2BE2"
  }
};

// Cesium配置
export const cesiumConfig = {
  accessToken: "your_cesium_access_token" // 请填入您的Cesium Token (获取地址: https://cesium.com/ion/tokens)
};

// 可视化组件配置
export const visualizationConfig = {
  entityTypes: {
    "地点": "#ff5722",
    "设施": "#4caf50",
    "状态": "#2196f3",
    "事件": "#ffc107"
  },
  defaultViewMode: "split" // 'map', 'graph', 'split'
};
