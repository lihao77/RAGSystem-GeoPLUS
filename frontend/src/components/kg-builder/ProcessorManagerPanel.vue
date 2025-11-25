<template>
  <div class="processor-manager-panel">
    <div class="panel-header">
      <h3>Processor列表</h3>
      <el-button type="primary" @click="$emit('add', {})">
        <el-icon><Plus /></el-icon>
        创建Processor
      </el-button>
    </div>

    <el-row :gutter="20">
      <!-- 可用Processors -->
      <el-col :span="12">
        <el-card class="processor-list-card">
          <template #header>
            <span>可用Processors</span>
          </template>
          <el-table :data="processors" stripe max-height="500">
            <el-table-column prop="name" label="名称" width="150" />
            <el-table-column prop="description" label="描述" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_builtin ? 'success' : 'info'" size="small">
                  {{ row.is_builtin ? '内置' : '自定义' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-switch
                  :model-value="row.enabled"
                  @change="(val) => $emit('toggle', row.name, val)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="$emit('edit', row)">编辑</el-button>
                <el-button
                  v-if="!row.is_builtin"
                  size="small"
                  type="danger"
                  @click="handleDelete(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 当前配置中的Processors -->
      <el-col :span="12">
        <el-card class="processor-list-card">
          <template #header>
            <span>当前配置的Processors</span>
          </template>
          <div v-if="!currentConfig" class="empty-state">
            <el-empty description="请先选择一个配置" />
          </div>
          <div v-else>
            <draggable
              v-model="configProcessors"
              item-key="name"
              @end="handleReorder"
              class="processor-drag-list"
            >
              <template #item="{ element, index }">
                <div class="processor-item">
                  <div class="processor-order">{{ index + 1 }}</div>
                  <div class="processor-info">
                    <div class="processor-name">{{ element.name }}</div>
                    <div class="processor-desc">{{ element.description }}</div>
                  </div>
                  <el-button
                    size="small"
                    type="danger"
                    circle
                    @click="$emit('remove', element.name)"
                  >
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </template>
            </draggable>
            <el-button
              class="add-processor-btn"
              type="primary"
              plain
              @click="showAddProcessorDialog"
            >
              <el-icon><Plus /></el-icon>
              添加Processor
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加Processor对话框 -->
    <el-dialog v-model="addProcessorDialogVisible" title="添加Processor" width="500px">
      <el-select
        v-model="selectedProcessor"
        placeholder="选择要添加的Processor"
        style="width: 100%"
      >
        <el-option
          v-for="proc in availableProcessors"
          :key="proc.name"
          :label="`${proc.name} - ${proc.description}`"
          :value="proc.name"
        />
      </el-select>
      <template #footer>
        <el-button @click="addProcessorDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddProcessor">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Close } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'

const props = defineProps({
  processors: {
    type: Array,
    default: () => []
  },
  currentConfig: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['add', 'remove', 'edit', 'toggle', 'reorder'])

const addProcessorDialogVisible = ref(false)
const selectedProcessor = ref('')

const configProcessors = computed({
  get: () => {
    if (!props.currentConfig) return []
    const enabled = props.currentConfig.processors?.enabled_processors || []
    return enabled.map(name => 
      props.processors.find(p => p.name === name)
    ).filter(Boolean)
  },
  set: () => {}
})

const availableProcessors = computed(() => {
  const enabled = props.currentConfig?.processors?.enabled_processors || []
  return props.processors.filter(p => !enabled.includes(p.name) && p.enabled)
})

const showAddProcessorDialog = () => {
  selectedProcessor.value = ''
  addProcessorDialogVisible.value = true
}

const handleAddProcessor = () => {
  if (!selectedProcessor.value) {
    ElMessage.warning('请选择要添加的Processor')
    return
  }

  emit('add', {
    processor_name: selectedProcessor.value
  })
  addProcessorDialogVisible.value = false
}

const handleReorder = () => {
  const newOrder = configProcessors.value.map(p => p.name)
  emit('reorder', newOrder)
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除Processor "${row.name}" 吗？`,
      '删除确认',
      { type: 'warning' }
    )
    // 删除processor的API调用在父组件处理
  } catch {}
}
</script>

<style scoped lang="scss">
.processor-manager-panel {
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h3 {
      margin: 0;
    }
  }

  .processor-list-card {
    height: 600px;

    .empty-state {
      height: 400px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }

  .processor-drag-list {
    min-height: 400px;
    margin-bottom: 10px;
  }

  .processor-item {
    display: flex;
    align-items: center;
    padding: 12px;
    margin-bottom: 8px;
    background: #f5f7fa;
    border-radius: 4px;
    cursor: move;
    transition: all 0.3s;

    &:hover {
      background: #e4e7ed;
    }

    .processor-order {
      width: 30px;
      height: 30px;
      line-height: 30px;
      text-align: center;
      background: #409eff;
      color: white;
      border-radius: 50%;
      margin-right: 12px;
      font-weight: bold;
    }

    .processor-info {
      flex: 1;

      .processor-name {
        font-weight: bold;
        margin-bottom: 4px;
      }

      .processor-desc {
        font-size: 12px;
        color: #909399;
      }
    }
  }

  .add-processor-btn {
    width: 100%;
  }
}
</style>
