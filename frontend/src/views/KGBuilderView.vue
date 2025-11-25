<template>
  <div class="kg-builder-view">
    <el-card class="header-card">
      <div class="header-content">
        <h2>知识图谱构建器</h2>
        <p>可视化配置从文本到图谱的完整流程</p>
      </div>
    </el-card>

    <el-tabs v-model="activeTab" class="kg-tabs">
      <!-- Pipeline配置管理 -->
      <el-tab-pane label="Pipeline配置" name="pipeline">
        <pipeline-config-panel
          :configs="pipelineConfigs"
          :current-config="currentConfig"
          @create="handleCreateConfig"
          @select="handleSelectConfig"
          @update="handleUpdateConfig"
          @delete="handleDeleteConfig"
          @export="handleExportConfig"
          @import="handleImportConfig"
        />
      </el-tab-pane>

      <!-- Processor管理 -->
      <el-tab-pane label="Processor管理" name="processors">
        <processor-manager-panel
          :processors="processors"
          :current-config="currentConfig"
          @add="handleAddProcessor"
          @remove="handleRemoveProcessor"
          @edit="handleEditProcessor"
          @toggle="handleToggleProcessor"
          @reorder="handleReorderProcessors"
        />
      </el-tab-pane>

      <!-- 流程可视化 -->
      <el-tab-pane label="流程可视化" name="visualization">
        <pipeline-visualization
          :config="currentConfig"
          :processors="enabledProcessors"
          @update-stage="handleUpdateStage"
        />
      </el-tab-pane>

      <!-- 执行与监控 -->
      <el-tab-pane label="执行与监控" name="execution">
        <pipeline-execution-panel
          :config="currentConfig"
          @execute="handleExecutePipeline"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- Processor编辑对话框 -->
    <el-dialog
      v-model="processorDialogVisible"
      :title="isEditingProcessor ? '编辑Processor' : '创建Processor'"
      width="70%"
      @close="handleCloseProcessorDialog"
    >
      <processor-editor
        :processor="editingProcessor"
        :is-new="!isEditingProcessor"
        @save="handleSaveProcessor"
        @cancel="processorDialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import PipelineConfigPanel from '@/components/kg-builder/PipelineConfigPanel.vue'
import ProcessorManagerPanel from '@/components/kg-builder/ProcessorManagerPanel.vue'
import PipelineVisualization from '@/components/kg-builder/PipelineVisualization.vue'
import PipelineExecutionPanel from '@/components/kg-builder/PipelineExecutionPanel.vue'
import ProcessorEditor from '@/components/kg-builder/ProcessorEditor.vue'
import { kgBuilderApi } from '@/api/kg-builder'

const activeTab = ref('pipeline')
const pipelineConfigs = ref([])
const currentConfig = ref(null)
const processors = ref([])
const processorDialogVisible = ref(false)
const editingProcessor = ref(null)
const isEditingProcessor = ref(false)

// 计算启用的processors
const enabledProcessors = computed(() => {
  if (!currentConfig.value) return []
  const enabled = currentConfig.value.processors?.enabled_processors || []
  return processors.value.filter(p => enabled.includes(p.name))
})

// 加载Pipeline配置列表
const loadPipelineConfigs = async () => {
  try {
    const response = await kgBuilderApi.listPipelineConfigs()
    if (response.success) {
      pipelineConfigs.value = response.configs
      // 如果有配置，默认选择第一个
      if (pipelineConfigs.value.length > 0 && !currentConfig.value) {
        await handleSelectConfig(pipelineConfigs.value[0].name)
      }
    }
  } catch (error) {
    ElMessage.error('加载Pipeline配置失败: ' + error.message)
  }
}

// 加载Processors列表
const loadProcessors = async () => {
  try {
    const response = await kgBuilderApi.listProcessors()
    if (response.success) {
      processors.value = response.processors
    }
  } catch (error) {
    ElMessage.error('加载Processors失败: ' + error.message)
  }
}

// 创建新配置
const handleCreateConfig = async (configData) => {
  try {
    const response = await kgBuilderApi.createPipelineConfig(configData)
    if (response.success) {
      ElMessage.success('配置创建成功')
      await loadPipelineConfigs()
      await handleSelectConfig(configData.name)
    } else {
      ElMessage.error('配置创建失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('配置创建失败: ' + error.message)
  }
}

// 选择配置
const handleSelectConfig = async (configName) => {
  try {
    const response = await kgBuilderApi.getPipelineConfig(configName)
    if (response.success) {
      currentConfig.value = response.config
    } else {
      ElMessage.error('加载配置失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('加载配置失败: ' + error.message)
  }
}

// 更新配置
const handleUpdateConfig = async (configName, updates) => {
  try {
    const response = await kgBuilderApi.updatePipelineConfig(configName, updates)
    if (response.success) {
      ElMessage.success('配置更新成功')
      currentConfig.value = response.config
      await loadPipelineConfigs()
    } else {
      ElMessage.error('配置更新失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('配置更新失败: ' + error.message)
  }
}

// 删除配置
const handleDeleteConfig = async (configName) => {
  try {
    const response = await kgBuilderApi.deletePipelineConfig(configName)
    if (response.success) {
      ElMessage.success('配置删除成功')
      if (currentConfig.value?.name === configName) {
        currentConfig.value = null
      }
      await loadPipelineConfigs()
    } else {
      ElMessage.error('配置删除失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('配置删除失败: ' + error.message)
  }
}

// 导出配置
const handleExportConfig = async (configName, outputPath) => {
  try {
    const response = await kgBuilderApi.exportPipelineConfig(configName, outputPath)
    if (response.success) {
      ElMessage.success('配置导出成功')
    } else {
      ElMessage.error('配置导出失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('配置导出失败: ' + error.message)
  }
}

// 导入配置
const handleImportConfig = async (configPath, name) => {
  try {
    const response = await kgBuilderApi.importPipelineConfig(configPath, name)
    if (response.success) {
      ElMessage.success('配置导入成功')
      await loadPipelineConfigs()
    } else {
      ElMessage.error('配置导入失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('配置导入失败: ' + error.message)
  }
}

// 添加Processor到配置
const handleAddProcessor = async (processorData) => {
  if (!currentConfig.value) {
    ElMessage.warning('请先选择一个配置')
    return
  }

  try {
    const response = await kgBuilderApi.addProcessorToConfig(
      currentConfig.value.name,
      processorData.processor_name,
      processorData.processor_config
    )
    if (response.success) {
      ElMessage.success('Processor添加成功')
      await handleSelectConfig(currentConfig.value.name)
    } else {
      ElMessage.error('Processor添加失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('Processor添加失败: ' + error.message)
  }
}

// 从配置移除Processor
const handleRemoveProcessor = async (processorName) => {
  if (!currentConfig.value) return

  try {
    const response = await kgBuilderApi.removeProcessorFromConfig(
      currentConfig.value.name,
      processorName
    )
    if (response.success) {
      ElMessage.success('Processor移除成功')
      await handleSelectConfig(currentConfig.value.name)
    } else {
      ElMessage.error('Processor移除失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('Processor移除失败: ' + error.message)
  }
}

// 编辑Processor
const handleEditProcessor = (processor) => {
  editingProcessor.value = { ...processor }
  isEditingProcessor.value = true
  processorDialogVisible.value = true
}

// 保存Processor
const handleSaveProcessor = async (processorData) => {
  try {
    const response = await kgBuilderApi.saveProcessor(processorData)
    if (response.success) {
      ElMessage.success('Processor保存成功')
      processorDialogVisible.value = false
      await loadProcessors()
    } else {
      ElMessage.error('Processor保存失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('Processor保存失败: ' + error.message)
  }
}

// 切换Processor启用状态
const handleToggleProcessor = async (processorName, enabled) => {
  try {
    const response = await kgBuilderApi.toggleProcessor(processorName, enabled)
    if (response.success) {
      ElMessage.success(`Processor已${enabled ? '启用' : '禁用'}`)
      await loadProcessors()
    } else {
      ElMessage.error('切换Processor状态失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('切换Processor状态失败: ' + error.message)
  }
}

// 调整Processor顺序
const handleReorderProcessors = async (processorOrder) => {
  if (!currentConfig.value) return

  try {
    const response = await kgBuilderApi.reorderProcessors(
      currentConfig.value.name,
      processorOrder
    )
    if (response.success) {
      ElMessage.success('Processor顺序已更新')
      await handleSelectConfig(currentConfig.value.name)
    } else {
      ElMessage.error('更新Processor顺序失败: ' + response.error)
    }
  } catch (error) {
    ElMessage.error('更新Processor顺序失败: ' + error.message)
  }
}

// 更新阶段配置
const handleUpdateStage = async (stageName, stageConfig) => {
  if (!currentConfig.value) return

  const updates = {
    stages: {
      [stageName]: stageConfig
    }
  }

  await handleUpdateConfig(currentConfig.value.name, updates)
}

// 执行Pipeline
const handleExecutePipeline = async (executionData) => {
  if (!currentConfig.value) {
    ElMessage.warning('请先选择一个配置')
    return
  }

  try {
    const formData = new FormData()
    formData.append('file', executionData.file)

    const response = await kgBuilderApi.executePipelineWithConfig(
      currentConfig.value.name,
      formData
    )

    if (response.success) {
      ElMessage.success('Pipeline执行成功')
      return response
    } else {
      ElMessage.error('Pipeline执行失败: ' + response.error)
      return null
    }
  } catch (error) {
    ElMessage.error('Pipeline执行失败: ' + error.message)
    return null
  }
}

// 关闭Processor对话框
const handleCloseProcessorDialog = () => {
  editingProcessor.value = null
  isEditingProcessor.value = false
}

// 初始化
onMounted(async () => {
  await Promise.all([
    loadPipelineConfigs(),
    loadProcessors()
  ])
})
</script>

<style scoped lang="scss">
.kg-builder-view {
  padding: 20px;
  height: calc(100vh - 60px);
  overflow: auto;

  .header-card {
    margin-bottom: 20px;

    .header-content {
      h2 {
        margin: 0 0 10px 0;
        color: #303133;
      }

      p {
        margin: 0;
        color: #909399;
        font-size: 14px;
      }
    }
  }

  .kg-tabs {
    background: white;
    padding: 20px;
    border-radius: 4px;
    min-height: 600px;

    :deep(.el-tabs__content) {
      height: calc(100vh - 250px);
      overflow: auto;
    }
  }
}
</style>
