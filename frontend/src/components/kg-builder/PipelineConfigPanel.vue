<template>
  <div class="pipeline-config-panel">
    <div class="toolbar">
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>
        创建配置
      </el-button>
      <el-button @click="showImportDialog">
        <el-icon><Upload /></el-icon>
        导入配置
      </el-button>
    </div>

    <el-table
      :data="configs"
      stripe
      highlight-current-row
      @current-change="handleSelectConfig"
      class="config-table"
    >
      <el-table-column prop="name" label="配置名称" width="200" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="stages_count" label="阶段数" width="100" align="center" />
      <el-table-column prop="processors_count" label="Processor数" width="120" align="center" />
      <el-table-column prop="updated_at" label="更新时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.updated_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" @click="handleExport(row)">导出</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建配置对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="创建Pipeline配置"
      width="500px"
    >
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="配置名称" required>
          <el-input v-model="createForm.name" placeholder="请输入配置名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入配置描述"
          />
        </el-form-item>
        <el-form-item label="基于模板">
          <el-select v-model="createForm.baseTemplate" placeholder="选择模板">
            <el-option label="默认配置" value="default" />
            <el-option label="空配置" value="empty" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 导入配置对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入Pipeline配置"
      width="500px"
    >
      <el-form :model="importForm" label-width="100px">
        <el-form-item label="配置文件">
          <el-input v-model="importForm.configPath" placeholder="配置文件路径" />
        </el-form-item>
        <el-form-item label="配置名称">
          <el-input v-model="importForm.name" placeholder="留空使用原名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>

    <!-- 编辑配置对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑Pipeline配置"
      width="600px"
    >
      <el-form v-if="editingConfig" :model="editingConfig" label-width="100px">
        <el-form-item label="配置名称">
          <el-input v-model="editingConfig.name" disabled />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="editingConfig.description"
            type="textarea"
            :rows="3"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导出配置对话框 -->
    <el-dialog
      v-model="exportDialogVisible"
      title="导出Pipeline配置"
      width="500px"
    >
      <el-form :model="exportForm" label-width="100px">
        <el-form-item label="导出路径">
          <el-input v-model="exportForm.outputPath" placeholder="导出文件路径" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmExport">导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload } from '@element-plus/icons-vue'

const props = defineProps({
  configs: {
    type: Array,
    default: () => []
  },
  currentConfig: {
    type: Object,
    default: null
  }
})

const emit = defineEmits([
  'create',
  'select',
  'update',
  'delete',
  'export',
  'import'
])

const createDialogVisible = ref(false)
const importDialogVisible = ref(false)
const editDialogVisible = ref(false)
const exportDialogVisible = ref(false)
const editingConfig = ref(null)
const exportingConfigName = ref('')

const createForm = ref({
  name: '',
  description: '',
  baseTemplate: 'default'
})

const importForm = ref({
  configPath: '',
  name: ''
})

const exportForm = ref({
  outputPath: ''
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const showCreateDialog = () => {
  createForm.value = {
    name: '',
    description: '',
    baseTemplate: 'default'
  }
  createDialogVisible.value = true
}

const showImportDialog = () => {
  importForm.value = {
    configPath: '',
    name: ''
  }
  importDialogVisible.value = true
}

const handleSelectConfig = (row) => {
  if (row) {
    emit('select', row.name)
  }
}

const handleCreate = () => {
  if (!createForm.value.name) {
    ElMessage.warning('请输入配置名称')
    return
  }

  emit('create', {
    name: createForm.value.name,
    description: createForm.value.description,
    base_config: createForm.value.baseTemplate === 'empty' ? {} : null
  })

  createDialogVisible.value = false
}

const handleImport = () => {
  if (!importForm.value.configPath) {
    ElMessage.warning('请输入配置文件路径')
    return
  }

  emit('import', importForm.value.configPath, importForm.value.name || null)
  importDialogVisible.value = false
}

const handleEdit = async (row) => {
  emit('select', row.name)
  setTimeout(() => {
    if (props.currentConfig) {
      editingConfig.value = { ...props.currentConfig }
      editDialogVisible.value = true
    }
  }, 300)
}

const handleSaveEdit = () => {
  if (!editingConfig.value) return

  const updates = {
    description: editingConfig.value.description
  }

  emit('update', editingConfig.value.name, updates)
  editDialogVisible.value = false
}

const handleExport = (row) => {
  exportingConfigName.value = row.name
  exportForm.value.outputPath = `${row.name}_export.json`
  exportDialogVisible.value = true
}

const handleConfirmExport = () => {
  if (!exportForm.value.outputPath) {
    ElMessage.warning('请输入导出路径')
    return
  }

  emit('export', exportingConfigName.value, exportForm.value.outputPath)
  exportDialogVisible.value = false
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除配置 "${row.name}" 吗？此操作不可撤销。`,
      '删除确认',
      {
        type: 'warning'
      }
    )
    emit('delete', row.name)
  } catch {
    // 取消删除
  }
}
</script>

<style scoped lang="scss">
.pipeline-config-panel {
  .toolbar {
    margin-bottom: 20px;
    display: flex;
    gap: 10px;
  }

  .config-table {
    width: 100%;
  }
}
</style>
