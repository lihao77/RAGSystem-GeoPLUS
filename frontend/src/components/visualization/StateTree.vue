<template>
  <div class="related-section">
    <h4>状态树</h4>
    <div class="state-tree">
      <div v-for="rootState in stateTreeData.rootStates" :key="rootState.id" class="state-tree-root">
        <StateTreeNode 
          :state="rootState" 
          :selected-states="selectedStates" 
          @select-state="selectState" 
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';
import StateTreeNode from './StateTreeNode.vue';

const props = defineProps({
  // 状态树数据
  stateTreeData: {
    type: Object,
    required: true
  },
  // 已选择的状态列表
  selectedStates: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['select-state']);

// 选择状态
const selectState = (state) => {
  emit('select-state', state);
};

// 格式化时间函数，从父组件传递给子组件
const formatTime = (timeString) => {
  if (!timeString) return '未知时间';

  // 处理时间范围格式 (2023-10-01至2023-10-10)
  if (timeString.includes('至')) {
    const [start, end] = timeString.split('至');
    return `${formatDate(start)} 至 ${formatDate(end)}`;
  }

  return formatDate(timeString);
};

// 格式化日期
const formatDate = (dateString) => {
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString; // 如果无法解析，返回原始字符串

    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch (e) {
    return dateString;
  }
};

// 获取状态描述
const getStateDescription = (state) => {
  if (!state) return '';

  // 尝试从状态数据中提取描述信息
  if (state.description) return state.description;
  
  // 如果有name属性，优先使用name
  if (state.name) return state.name;
  
  // 否则使用ID
  return state.id || '';
};
</script>

<style scoped>
.related-section {
  /* margin-top: 20px; */
  padding: 16px;
  background: #f8f9fb;
  border-radius: 12px;
  border: 1px solid #e8eaf0;
}

.related-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.related-section h4::before {
  content: '';
  width: 4px;
  height: 16px;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border-radius: 2px;
}

.state-tree {
  margin-top: 12px;
  max-height: 320px;
  overflow-y: auto;
  padding: 4px;
}

.state-tree::-webkit-scrollbar {
  width: 6px;
}

.state-tree::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
}

.state-tree::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.state-tree::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

.state-tree-root {
  margin-bottom: 16px;
}

.state-tree-root:last-child {
  margin-bottom: 0;
}
</style>