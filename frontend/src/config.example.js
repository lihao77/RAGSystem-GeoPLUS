/**
 * 系统配置文件模板
 * 使用说明：
 * 1. 复制此文件并重命名为 config.js
 * 2. 填入您自己的配置信息
 * 3. config.js 已在 .gitignore 中，不会被提交到版本控制
 */

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
