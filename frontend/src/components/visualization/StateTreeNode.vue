<template>
  <div class="state-tree-node">
    <!-- 当前状态节点 -->
    <div class="state-item"
      :class="{ 
        'active': selectedStates.some(s => s.id === state.id),
        'has-children': state.children && state.children.length > 0
      }" 
      @click="handleStateClick">
      <!-- 展开/折叠图标 (仅对有子状态的节点显示) -->
      <div v-if="state.children && state.children.length > 0" 
           class="expand-icon"
           :class="{ 'expanded': isChildrenExpanded }"
           @click.stop="toggleChildren">
        {{ isChildrenExpanded ? '−' : '+' }}
      </div>
      
      <!-- 为没有展开按钮的节点添加占位 -->
      <div v-if="!(state.children && state.children.length > 0)" class="expand-placeholder"></div>
      
      <div class="state-dot" :class="{ 'expanded': isChildrenExpanded, 'contain': isChildState, 'next': isNextState }"></div>
      <div class="state-time">{{ formatTime(state.time) }}</div>
    </div>
    
    <!-- 子状态 (contain关系) -->
    <div v-if="state.children && state.children.length > 0 && isChildrenExpanded" 
         class="state-children"
         :class="{ 'expanded': isChildrenExpanded }">
      <div v-for="childState in state.children" :key="childState.id" class="state-child-branch">
        <div class="state-branch-line contain"></div>
        <StateTreeNode 
          :state="childState" 
          :selected-states="selectedStates" 
          :is-child-state="true"
          @select-state="$emit('select-state', $event)" 
        />
      </div>
    </div>
    
    <!-- 下一个状态 (nextState关系) -->
    <div v-if="state.next && state.next.length > 0" class="state-next">
      <div class="state-next-container">
        <div v-for="nextState in state.next" :key="nextState.id" class="state-next-branch">
          <div class="state-branch-line next"></div>
          <StateTreeNode 
            :state="nextState" 
            :selected-states="selectedStates" 
            :is-next-state="true"
            @select-state="$emit('select-state', $event)" 
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref } from 'vue';

const props = defineProps({
  // 当前状态节点
  state: {
    type: Object,
    required: true
  },
  // 已选择的状态列表
  selectedStates: {
    type: Array,
    default: () => []
  },
  // 是否为子状态（contain关系）
  isChildState: {
    type: Boolean,
    default: false
  },
  // 是否为下一个状态（nextState关系）
  isNextState: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['select-state']);

// 子状态展开/折叠状态 (默认折叠)
const isChildrenExpanded = ref(false);

// 切换子状态的展开/折叠
const toggleChildren = (event) => {
  isChildrenExpanded.value = !isChildrenExpanded.value;
  // 阻止事件冒泡，避免触发父元素的点击事件
  event.stopPropagation();
};

// 处理状态节点点击
const handleStateClick = () => {
  emit('select-state', props.state);
};

// 格式化时间函数
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


</script>

<style scoped>
.state-tree-node {
  position: relative;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

.state-item {
  display: inline-flex;
  align-items: center;
  padding: 5px;
  /* padding-left: 0; */
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid transparent;
  font-weight: 500;
  /* max-width: 240px; */
}

.state-item:hover {
  background-color: rgba(240, 240, 250, 0.1);
  border-color: rgba(100, 100, 255, 0.1);
  transform: translateY(-1px);
}

.state-item.active {
  background-color: rgba(0, 120, 255, 0.15);
  border-color: rgba(0, 120, 255, 0.3);
}

/* .state-item.has-children {
  max-width: 261px;
} */

.state-time {
  user-select: none;
  font-size: 12px;
  color: #2c3e50;
  white-space: nowrap;
  background-color: rgba(24, 144, 255, 0.08);
  padding: 4px 10px;
  border-radius: 6px;
  margin-left: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
  font-weight: 500;
  border: 1px solid rgba(24, 144, 255, 0.15);
}

/* 展开/折叠图标样式 */
.expand-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background-color: rgba(24, 144, 255, 0.1);
  margin-right: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 12px;
  line-height: 1;
  user-select: none;
  flex-shrink: 0;
  color: #1890ff;
  font-weight: 600;
}

.expand-icon:hover {
  background-color: rgba(24, 144, 255, 0.2);
  color: #096dd9;
  transform: scale(1.1);
}

.expand-icon.expanded {
  background-color: rgba(24, 144, 255, 0.25);
  color: #096dd9;
}

/* .icon{
    position: absolute;
    top:6.5px;
    font-size: 14px;
    line-height: 1;
} */
/* 占位元素样式，与展开图标宽度一致 */
/* .expand-placeholder {
  width: 15px;
  margin-right: 10px;
  flex-shrink: 0;
} */

.state-dot {
  user-select: none;
  width: 10px;
  height: 10px;
  margin-left: 2px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  margin-right: 10px;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(24, 144, 255, 0.4);
  border: 2px solid white;
}

/* 展开状态 */
.state-dot.expanded {
  background: linear-gradient(135deg, #722ed1 0%, #531dab 100%);
  box-shadow: 0 2px 6px rgba(114, 46, 209, 0.4);
}

/* contain 关系 */
.state-dot.contain {
  background: linear-gradient(135deg, #722ed1 0%, #531dab 100%);
  box-shadow: 0 2px 6px rgba(114, 46, 209, 0.4);
}

/* nextState 关系 */
.state-dot.next {
  background: linear-gradient(135deg, #13c2c2 0%, #08979c 100%);
  box-shadow: 0 2px 6px rgba(19, 194, 194, 0.4);
}

.state-desc {
  flex-grow: 1;
  font-size: 0.9em;
  word-break: break-word;
}

.state-children {
  margin-left: 12px;
  position: relative;
  transition: all 0.3s ease;
  overflow: hidden;
}

.state-children.indented {
  margin-left: 36px;
}

.state-next {
  position: relative;
  transition: all 0.3s ease;
  overflow: hidden;
}

.state-next-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.state-children.expanded {
  animation: slideDown 0.3s ease forwards;
}

@keyframes slideDown {
  from { max-height: 0; opacity: 0; }
  to { max-height: 1000px; opacity: 1; }
}

.state-child-branch {
  position: relative;
  padding-left: 9px;
}

.state-next-branch {
  position: relative;
  padding-left: 0;
  margin-top: 8px;
}

.state-branch-line {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background-color: #d9d9d9;
  opacity: 0.8;
}

.state-branch-line.contain {
  background: linear-gradient(135deg, #722ed1 0%, #531dab 100%);
}

.state-branch-line.next {
  background: linear-gradient(135deg, #13c2c2 0%, #08979c 100%);
  left: -18px;
}

.child-state {
  border-left: 3px solid #722ed1;
}

.next-state {
  border-left: 3px solid #13c2c2;
}
</style>