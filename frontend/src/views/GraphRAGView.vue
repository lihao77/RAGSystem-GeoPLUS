<template>
  <div class="graphrag-container">
    <div class="controls">
      <el-input 
        v-model="question" 
        placeholder="输入你的问题，例如：查询广西2020年洪水事件" 
        type="textarea" 
        :rows="3"
        @keydown.ctrl.enter="sendQuestion"
      />
      <div class="actions">
        <el-button type="primary" @click="sendQuestion" :loading="loading" :disabled="!question.trim()">
          <el-icon><Search /></el-icon>
          发送 (Ctrl+Enter)
        </el-button>
        <el-button @click="fetchSchema">
          <el-icon><DataAnalysis /></el-icon>
          图谱结构
        </el-button>
        <el-button @click="clear">
          <el-icon><Delete /></el-icon>
          清空
        </el-button>
      </div>
    </div>

    <div class="chat-and-results">
      <div class="chat-panel">
        <div class="panel-header">
          <h3><el-icon><ChatDotRound /></el-icon> 对话历史</h3>
          <el-tag v-if="messages.length > 0" size="small">{{ messages.length }} 条消息</el-tag>
        </div>
        <div class="chat-content">
          <div v-if="messages.length === 0" class="empty-state">
            <el-icon size="48"><ChatDotRound /></el-icon>
            <p>开始提问，探索知识图谱...</p>
          </div>
          <div v-for="(m, idx) in messages" :key="idx" class="message" :class="m.role">
            <div class="message-header">
              <el-avatar :size="32" :style="{ background: m.role === 'user' ? '#409eff' : '#67c23a' }">
                {{ m.role === 'user' ? '我' : 'AI' }}
              </el-avatar>
              <span class="role">{{ m.role === 'user' ? '用户' : 'AI 助手' }}</span>
            </div>
            <div class="content" v-html="formatContent(m.content)"></div>
          </div>
        </div>
      </div>

      <div class="results-panel">
        <div class="panel-header">
          <h3><el-icon><DocumentCopy /></el-icon> 技术详情</h3>
        </div>
        <div class="results-content">
          <!-- <el-collapse v-model="activeNames" accordion> -->
          <el-collapse v-model="activeNames">
            <el-collapse-item name="0">
              <template #title>
                <div class="collapse-title">
                  <el-icon><Share /></el-icon>
                  <span>知识图谱</span>
                  <el-tag v-if="graphData.nodes.length > 0" size="small" type="success">
                    {{ graphData.nodes.length }} 节点
                  </el-tag>
                </div>
              </template>
              <div v-if="graphData.nodes.length > 0" class="graph-wrapper">
                <div class="graph-debug">
                  <el-button size="small" @click="renderGraph">刷新图谱</el-button>
                  <span style="margin-left: 10px; font-size: 12px; color: #999;">
                    {{ graphData.nodes.length }} 节点, {{ graphData.links.length }} 关系
                  </span>
                </div>
                <div ref="graphContainer" class="graph-container"></div>
                <div class="graph-legend">
                  <el-tag size="small">节点: {{ graphData.nodes.length }}</el-tag>
                  <el-tag size="small" type="info">关系: {{ graphData.links.length }}</el-tag>
                </div>
              </div>
              <el-empty v-else description="暂无图谱数据" :image-size="60" />
            </el-collapse-item>
            
            <el-collapse-item name="1">
              <template #title>
                <div class="collapse-title">
                  <el-icon><Document /></el-icon>
                  <span>生成的 Cypher</span>
                  <el-tag v-if="lastCypher" size="small" type="success">已生成</el-tag>
                </div>
              </template>
              <pre v-if="lastCypher" class="cypher">{{ lastCypher }}</pre>
              <el-empty v-else description="暂无 Cypher 查询" :image-size="60" />
            </el-collapse-item>
            
            <el-collapse-item name="2">
              <template #title>
                <div class="collapse-title">
                  <el-icon><DataLine /></el-icon>
                  <span>查询结果</span>
                  <el-tag v-if="lastResults.length > 0" size="small" type="info">{{ lastResults.length }} 条</el-tag>
                </div>
              </template>
              <div v-if="lastResults.length > 0" class="results-wrapper">
                <pre class="results-json">{{ lastResultsStr }}</pre>
              </div>
              <el-empty v-else description="暂无查询结果" :image-size="60" />
            </el-collapse-item>
            
            <el-collapse-item name="3">
              <template #title>
                <div class="collapse-title">
                  <el-icon><Connection /></el-icon>
                  <span>图谱结构</span>
                  <el-tag v-if="schema" size="small" type="warning">已加载</el-tag>
                </div>
              </template>
              <div v-if="schema" class="schema-wrapper">
                <pre class="schema">{{ schemaStr }}</pre>
              </div>
              <el-empty v-else description="点击按钮获取图谱结构" :image-size="60" />
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { Search, DataAnalysis, Delete, ChatDotRound, DocumentCopy, Document, DataLine, Connection, Share } from '@element-plus/icons-vue';
import ForceGraph from 'force-graph';
import * as graphragService from '../api/graphragService';

// 配置 marked
marked.setOptions({
  breaks: true, // 支持换行
  gfm: true, // 启用 GitHub Flavored Markdown
  headerIds: false,
  mangle: false
});

const question = ref('');
const loading = ref(false);
const messages = ref([]);
const lastCypher = ref('');
const lastResults = ref([]);
const schema = ref(null);
const activeNames = ref(['0', '1', '2', '3']); // 默认展开所有面板
const graphContainer = ref(null);
let graphInstance = null;

// 图谱数据
const graphData = ref({
  nodes: [],
  links: []
});

const lastResultsStr = computed(() => {
  try {
    return JSON.stringify(lastResults.value, null, 2);
  } catch (e) {
    return String(lastResults.value);
  }
});

const schemaStr = computed(() => {
  try {
    return JSON.stringify(schema.value, null, 2);
  } catch (e) {
    return '';
  }
});

// 从查询结果中提取图谱数据
function extractGraphData(graphDataFromBackend) {
  if (!graphDataFromBackend || !graphDataFromBackend.nodes) {
    return { nodes: [], links: [] };
  }
  
  const nodes = graphDataFromBackend.nodes.map(node => {
    // 构建节点显示名称，优先使用 properties 中的名称
    const name = node.properties?.名称 || 
                 node.properties?.name || 
                 node.properties?.标题 || 
                 node.properties?.id ||
                 `节点 ${node.id}`;
    
    // 构建属性信息用于显示
    let attributesText = '';
    if (node.attributes && Array.isArray(node.attributes) && node.attributes.length > 0) {
      attributesText = '\n属性:\n' + node.attributes
        .filter(attr => attr && (attr.type || attr.value))
        .map(attr => `  • ${attr.type || '未知'}: ${attr.value || ''}`)
        .join('\n');
    }
    
    return {
      id: `node_${node.id}`,
      name: name,
      label: node.labels?.[0] || '未知',
      properties: node.properties,
      attributes: node.attributes || [],
      color: getNodeColor(node.labels?.[0]),
      displayInfo: `${node.labels?.[0] || '未知'}: ${name}${attributesText}`
    };
  });
  
  const links = (graphDataFromBackend.relationships || [])
    .filter(rel => rel.source && rel.target)
    .map(rel => ({
      source: `node_${rel.source}`,
      target: `node_${rel.target}`,
      label: rel.type || '相关',
      properties: rel.properties || {},
      color: '#999'
    }));
  
  return { nodes, links };
}

// 根据标签返回颜色
function getNodeColor(label) {
  const colorMap = {
    '事件': '#ff6b6b',
    '地点': '#4ecdc4',
    '时间': '#95e1d3',
    '人物': '#f38181',
    '组织': '#aa96da',
    '灾害': '#ff9ff3',
    '统计': '#feca57',
    '措施': '#48dbfb',
    '影响': '#ff6348',
    '原因': '#a29bfe',
    'State': '#5f9ea0',
    'Attribute': '#daa520',
    'entity': '#9370db'
  };
  return colorMap[label] || '#409eff';
}

// 渲染图谱
function renderGraph() {
  if (!graphContainer.value || graphData.value.nodes.length === 0) return;
  
  // 销毁旧实例
  if (graphInstance) {
    graphContainer.value.innerHTML = '';
    graphInstance = null;
  }
  
  // 确保容器有尺寸
  const containerWidth = graphContainer.value.clientWidth || 360;
  const containerHeight = 350;
  
  console.log('渲染图谱:', {
    nodes: graphData.value.nodes.length,
    links: graphData.value.links.length,
    containerWidth,
    containerHeight
  });
  
  // 创建新实例
  graphInstance = ForceGraph()(graphContainer.value)
    .width(containerWidth)
    .height(containerHeight)
    .graphData(graphData.value)
    .nodeId('id')
    .nodeLabel(node => node.displayInfo || `${node.label}: ${node.name}`)
    .nodeColor(node => node.color)
    .nodeRelSize(6)
    .nodeCanvasObject((node, ctx, globalScale) => {
      // 绘制节点
      const label = node.name || 'Node';
      const fontSize = 12 / globalScale;
      ctx.font = `${fontSize}px Sans-Serif`;
      const textWidth = ctx.measureText(label).width;
      const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

      // 绘制圆形节点
      ctx.fillStyle = node.color;
      ctx.beginPath();
      ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
      ctx.fill();

      // 绘制文字背景
      ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y + 7, ...bckgDimensions);

      // 绘制文字
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#333';
      ctx.fillText(label, node.x, node.y + 8);
    })
    .linkLabel(link => {
      let label = link.label;
      if (link.properties && Object.keys(link.properties).length > 0) {
        const propsText = Object.entries(link.properties)
          .map(([k, v]) => `${k}: ${v}`)
          .join(', ');
        label += `\n${propsText}`;
      }
      return label;
    })
    .linkColor(() => '#999')
    .linkWidth(2)
    .linkDirectionalArrowLength(6)
    .linkDirectionalArrowRelPos(1)
    .backgroundColor('#fafafa')
    .onNodeClick(node => {
      console.log('节点详情:', node);
      if (node.attributes && node.attributes.length > 0) {
        console.log('节点属性:', node.attributes);
      }
    })
    .d3Force('charge').strength(-300)
    .d3Force('link').distance(100);
  
  // 缩放到适合大小
  setTimeout(() => {
    if (graphInstance) {
      graphInstance.zoomToFit(400, 20);
    }
  }, 500);
}

// 监听图谱数据变化
watch(() => graphData.value.nodes.length, () => {
  if (graphData.value.nodes.length > 0 && activeNames.value.includes('0')) {
    nextTick(() => {
      renderGraph();
    });
  }
});

// 监听面板展开
watch(activeNames, (newVal) => {
  if (newVal.includes('0') && graphData.value.nodes.length > 0) {
    nextTick(() => {
      renderGraph();
    });
  }
});

async function sendQuestion() {
  if (!question.value || loading.value) return;
  messages.value.push({ role: 'user', content: question.value });
  loading.value = true;
  try {
    const resp = await graphragService.queryGraphRAG(question.value, messages.value);
    console.log('API 响应:', resp);
    
    if (resp && resp.data && resp.success) {
      const d = resp.data;
      messages.value.push({ role: 'assistant', content: d.answer });
      lastCypher.value = d.cypher || '';
      lastResults.value = d.query_results || [];
      
      // 使用后端返回的图谱数据
      console.log('图谱原始数据:', d.graph_data);
      if (d.graph_data) {
        graphData.value = extractGraphData(d.graph_data);
        console.log('提取后的图谱数据:', graphData.value);
        
        if (graphData.value.nodes.length > 0) {
          activeNames.value = ['0'];
          // 等待 DOM 更新后再渲染
          nextTick(() => {
            setTimeout(() => {
              renderGraph();
            }, 100);
          });
        }
      }
    } else {
      messages.value.push({ role: 'assistant', content: '请求失败：' + (resp.data && resp.data.message ? resp.data.message : '未知错误') });
    }
  } catch (e) {
    console.error('请求错误:', e);
    messages.value.push({ role: 'assistant', content: '请求出错：' + String(e) });
  } finally {
    loading.value = false;
    question.value = '';
  }
}

async function fetchSchema() {
  try {
    const resp = await graphragService.getGraphSchema();
    if (resp && resp.data && resp.data.success) {
      schema.value = resp.data.data;
      activeNames.value = ['3'];
    } else {
      schema.value = { error: (resp.data && resp.data.message) || '获取失败' };
    }
  } catch (e) {
    schema.value = { error: String(e) };
  }
}

function clear() {
  question.value = '';
  messages.value = [];
  lastCypher.value = '';
  lastResults.value = [];
  schema.value = null;
  graphData.value = { nodes: [], links: [] };
  if (graphInstance && graphContainer.value) {
    graphContainer.value.innerHTML = '';
    graphInstance = null;
  }
}

function formatContent(text) {
  if (!text) return '';
  
  try {
    // 使用 marked 解析 Markdown
    const rawHtml = marked.parse(text);
    // 使用 DOMPurify 清理 HTML，防止 XSS 攻击
    const cleanHtml = DOMPurify.sanitize(rawHtml, {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
      ALLOWED_ATTR: ['href', 'target', 'rel']
    });
    return cleanHtml;
  } catch (e) {
    // 如果解析失败，使用简单的文本处理
    return text.replace(/\n/g, '<br/>');
  }
}
</script>

<style scoped>
.graphrag-container { 
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  /* background: #f5f7fa; */
}

.controls { 
  margin-bottom: 16px;
  background: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.actions { 
  margin-top: 12px;
  display: flex;
  gap: 10px;
}

.chat-and-results { 
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.chat-panel,
.results-panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-panel { 
  flex: 1;
  min-width: 0;
}

.results-panel { 
  width: 450px;
  max-width: 450px;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(to right, #f8f9fa, #ffffff);
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.results-content {
  flex: 1;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  gap: 12px;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.message { 
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.message .role { 
  font-weight: 600;
  font-size: 14px;
  color: #606266;
}

.message.user .content { 
  background: #ecf5ff;
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 3px solid #409eff;
  margin-left: 42px;
}

.message.assistant .content { 
  background: #f0f9ff;
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 3px solid #67c23a;
  margin-left: 42px;
}

.collapse-title {
    padding-left: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.results-wrapper,
.schema-wrapper {
  max-height: 300px;
  overflow-y: auto;
}

.graph-wrapper {
  position: relative;
  padding: 8px;
}

.graph-debug {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.graph-container {
  width: 100%;
  height: 350px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fafafa;
  overflow: hidden;
  position: relative;
}

.graph-container canvas {
  display: block;
}

.graph-legend {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  justify-content: center;
}

.cypher, 
.results-json, 
.schema {
  white-space: pre-wrap;
  word-break: break-word;
  background: #fafafa;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

/* Markdown 样式 */
.message.assistant .content :deep(h1),
.message.assistant .content :deep(h2),
.message.assistant .content :deep(h3),
.message.assistant .content :deep(h4) {
  margin: 16px 0 10px 0;
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
}

.message.assistant .content :deep(h1) { font-size: 1.5em; border-bottom: 2px solid #e4e7ed; padding-bottom: 8px; }
.message.assistant .content :deep(h2) { font-size: 1.3em; border-bottom: 1px solid #ebeef5; padding-bottom: 6px; }
.message.assistant .content :deep(h3) { font-size: 1.15em; }
.message.assistant .content :deep(h4) { font-size: 1.05em; }

.message.assistant .content :deep(p) {
  margin: 8px 0;
  line-height: 1.8;
  color: #606266;
}

.message.assistant .content :deep(code) {
  background: #f4f4f5;
  padding: 3px 8px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
  color: #e6a23c;
  border: 1px solid #ebeef5;
}

.message.assistant .content :deep(pre) {
  background: #282c34;
  color: #abb2bf;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.message.assistant .content :deep(pre code) {
  background: none;
  padding: 0;
  color: #abb2bf;
  border: none;
}

.message.assistant .content :deep(ul),
.message.assistant .content :deep(ol) {
  margin: 10px 0;
  padding-left: 28px;
}

.message.assistant .content :deep(li) {
  margin: 6px 0;
  line-height: 1.8;
  color: #606266;
}

.message.assistant .content :deep(blockquote) {
  border-left: 4px solid #409eff;
  margin: 12px 0;
  padding: 10px 16px;
  background: #f4f4f5;
  color: #606266;
  border-radius: 4px;
}

.message.assistant .content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.message.assistant .content :deep(th),
.message.assistant .content :deep(td) {
  border: 1px solid #e4e7ed;
  padding: 10px 12px;
  text-align: left;
}

.message.assistant .content :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
  color: #303133;
}

.message.assistant .content :deep(td) {
  color: #606266;
}

.message.assistant .content :deep(a) {
  color: #409eff;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 0.3s;
}

.message.assistant .content :deep(a:hover) {
  border-bottom-color: #409eff;
}

.message.assistant .content :deep(strong) {
  font-weight: 600;
  color: #303133;
}

.message.assistant .content :deep(em) {
  font-style: italic;
  color: #606266;
}

/* 滚动条样式 */
.chat-content::-webkit-scrollbar,
.results-content::-webkit-scrollbar,
.results-wrapper::-webkit-scrollbar,
.schema-wrapper::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.chat-content::-webkit-scrollbar-thumb,
.results-content::-webkit-scrollbar-thumb,
.results-wrapper::-webkit-scrollbar-thumb,
.schema-wrapper::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 3px;
}

.chat-content::-webkit-scrollbar-thumb:hover,
.results-content::-webkit-scrollbar-thumb:hover,
.results-wrapper::-webkit-scrollbar-thumb:hover,
.schema-wrapper::-webkit-scrollbar-thumb:hover {
  background: #c0c4cc;
}

:deep(.el-collapse-item__content){
    padding-bottom: 0 !important;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .results-panel {
    width: 350px;
    max-width: 350px;
  }
}

@media (max-width: 992px) {
  .chat-and-results {
    flex-direction: column;
  }
  
  .results-panel {
    width: 100%;
    max-width: 100%;
    height: 400px;
  }
}
</style>
