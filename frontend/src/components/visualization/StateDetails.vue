<template>
  <div v-if="state" class="state-details">
    <h4 class="state-title">状态详情</h4>
    <div class="state-time">时间: {{ formatTime(state.time) }}</div>
    <div v-if="state.entityIds" class="state-owner">
      <span class="state-owner-label">所属实体:</span>
      <div class="entity-tags">
        <span v-for="entityId in state.entityIds" :key="entityId" class="entity-tag" @click="handleEntityClick(entityId)">
          {{ entityNames[entityId] || entityId }}
        </span>
      </div>
    </div>
    <table v-if="state.description && state.description.length" class="state-table wrap">
      <thead>
        <tr>
          <th>属性名</th>
          <th>属性值</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, index) in state.description" :key="index">
          <td>{{ item.type }}</td>
          <td>{{ item.value }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue';
import { entityService } from '../../api';

const props = defineProps({
  state: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['select-entity']);

// 存储实体ID到名称的映射
const entityNames = ref({});

// 获取实体名称
const fetchEntityNames = async (entityIds) => {
  try {
    // 对每个实体ID发起请求获取名称
    const promises = entityIds.map(async (entityId) => {
      try {
        const entity = await entityService.getEntityById(entityId);
        entityNames.value[entityId] = entity.name || entity.id;
      } catch (err) {
        console.error(`获取实体 ${entityId} 名称失败:`, err);
      }
    });
    
    await Promise.all(promises);
  } catch (err) {
    console.error('获取实体名称错误:', err);
  }
};

// 监听状态变化，当状态改变时获取相关实体的名称
watch(() => props.state, async (newState) => {
  if (newState && newState.entityIds && newState.entityIds.length > 0) {
    await fetchEntityNames(newState.entityIds);
  }
}, { immediate: true });

// 处理实体标签点击
const handleEntityClick = (entityId) => {
  emit('select-entity', entityId);
};


// 格式化时间显示
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
    if (isNaN(date.getTime())) return dateString;

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
.state-details {
  background: #f8f9fb;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #e8eaf0;
  max-width: 400px;
}

.state-title {
  font-size: 16px; 
  font-weight: 600;
  color: #1a1a1a; 
  padding-bottom: 10px;
  margin-bottom: 12px;
  border-bottom: 2px solid #e3e8ef;
  display: flex;
  align-items: center;
  gap: 6px;
}

.state-title::before {
  content: '⚡';
  font-size: 16px;
}

.state-time {
  font-size: 13px;
  color: #666;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  border-left: 3px solid #1890ff;
}

.state-time::before {
  content: '🕒';
  font-size: 12px;
}

.state-owner {
  font-size: 14px;
  margin-bottom: 12px;
  color: #2c3e50;
}

.state-owner-label {
  font-weight: 600;
  font-size: 13px;
  margin-right: 8px;
  display: block;
  margin-bottom: 8px;
  color: #2c3e50;
}

.entity-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.entity-tag {
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.1) 0%, rgba(9, 109, 217, 0.1) 100%);
  border: 1px solid rgba(24, 144, 255, 0.3);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 12px;
  color: #1890ff;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 500;
}

.entity-tag:hover {
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.2) 0%, rgba(9, 109, 217, 0.15) 100%);
  border-color: #1890ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.2);
}

.state-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.state-table th,
.state-table td {
  font-size: 13px;
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #e8eaf0;
}

.state-table th {
  font-size: 13px;
  font-weight: 600;
  color: #2c3e50;
  background: #f8f9fb;
}

.state-table td {
  color: #333;
}

.state-table tbody tr:last-child td {
  border-bottom: none;
}

.state-table tbody tr:hover {
  background: #f8f9fb;
}
</style>