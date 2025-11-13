# 知识图谱可视化系统

这是一个基于Vue.js的知识图谱可视化前端系统，用于展示、查询和管理知识图谱数据。

## 功能特点

- 知识图谱可视化展示
- 实体关系查询
- 地理位置信息展示
- 参数配置管理
- 数据导入导出

## 技术栈

- Vue 3 + Vite
- Element Plus UI组件库
- ECharts 图表可视化
- Neo4j Driver 数据库连接
- Leaflet 地图展示

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 项目结构

- `src/components`: 组件目录
- `src/views`: 页面视图
- `src/api`: API接口
- `src/utils`: 工具函数
- `src/assets`: 静态资源
- `src/router`: 路由配置

## 配置说明

系统配置位于`src/config.js`文件中，包括Neo4j数据库连接信息、API端点等。