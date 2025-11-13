<template>
  <div class="import-container">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="import-card">
          <template #header>
            <div class="card-header">
              <h3>数据导入</h3>
            </div>
          </template>
          <div class="import-content">
            <el-tabs v-model="activeTab">
              <!-- 文件上传 -->
              <el-tab-pane label="文件上传" name="upload">
                <div class="upload-area">
                  <el-upload
                    class="upload-dragger"
                    drag
                    action="#"
                    :auto-upload="false"
                    :on-change="handleFileChange"
                    :on-remove="handleFileRemove"
                    :file-list="fileList"
                    multiple
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">
                      将文件拖到此处，或<em>点击上传</em>
                    </div>
                    <template #tip>
                      <div class="el-upload__tip">
                        支持上传Word文档（.docx格式）
                      </div>
                    </template>
                  </el-upload>
                  
                  <div class="upload-actions" v-if="fileList.length > 0">
                    <el-button type="primary" @click="processFiles">开始处理</el-button>
                    <el-button @click="clearFiles">清空文件</el-button>
                  </div>
                </div>
              </el-tab-pane>
              
              <!-- 目录选择 -->
              <el-tab-pane label="目录选择" name="directory">
                <div class="directory-select">
                  <el-form :model="directoryForm" label-width="100px">
                    <el-form-item label="数据目录">
                      <el-input v-model="directoryForm.path" placeholder="输入数据目录路径" />
                    </el-form-item>
                    <el-form-item>
                      <el-button type="primary" @click="scanDirectoryHandler">扫描目录</el-button>
                    </el-form-item>
                  </el-form>
                  
                  <div v-if="directoryFiles.length > 0" class="directory-files">
                    <h4>找到以下文件：</h4>
                    <el-table :data="directoryFiles" style="width: 100%">
                      <el-table-column prop="name" label="文件名" />
                      <el-table-column prop="path" label="路径" />
                      <el-table-column label="操作" width="120">
                        <template #default="scope">
                          <el-checkbox v-model="scope.row.selected">选择</el-checkbox>
                        </template>
                      </el-table-column>
                    </el-table>
                    
                    <div class="directory-actions">
                      <el-button type="primary" @click="processSelectedFiles">处理选中文件</el-button>
                      <el-button @click="selectAllFiles">全选</el-button>
                      <el-button @click="deselectAllFiles">取消全选</el-button>
                    </div>
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>
        
        <!-- 处理进度 -->
        <el-card class="progress-card" v-if="processingStatus.isProcessing">
          <template #header>
            <div class="card-header">
              <h3>处理进度</h3>
            </div>
          </template>
          <div class="processing-progress">
            <el-progress 
              :percentage="processingStatus.progress" 
              :status="processingStatus.progress === 100 ? 'success' : ''"
            />
            <div class="progress-info">
              <p>{{ processingStatus.currentFile }}</p>
              <p>{{ processingStatus.statusText }}</p>
            </div>
            
            <div class="progress-actions" v-if="processingStatus.progress < 100">
              <el-button type="danger" @click="cancelProcessingHandler">取消处理</el-button>
            </div>
            
            <div class="progress-complete" v-else>
              <el-result icon="success" title="处理完成" subTitle="所有文档已成功处理并导入知识图谱">
                <template #extra>
                  <el-button type="primary" @click="viewGraph">查看知识图谱</el-button>
                </template>
              </el-result>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <h3>处理选项</h3>
            </div>
          </template>
          <div class="processing-options">
            <el-form :model="processingOptions" label-width="120px">
              <el-form-item label="并行处理">
                <el-switch v-model="processingOptions.parallel" />
              </el-form-item>
              
              <el-form-item label="最大线程数" v-if="processingOptions.parallel">
                <el-input-number v-model="processingOptions.maxWorkers" :min="1" :max="8" />
              </el-form-item>
              
              <el-form-item label="数据验证">
                <el-switch v-model="processingOptions.validateData" />
              </el-form-item>
              
              <el-form-item label="导出JSON">
                <el-switch v-model="processingOptions.exportJson" />
              </el-form-item>
              
              <el-divider>模型选择</el-divider>
              
              <el-form-item label="LLM模型">
                <el-select v-model="processingOptions.modelName" style="width: 100%">
                  <el-option label="deepseek-r1t-chimera" value="tngtech/deepseek-r1t-chimera:free" />
                  <el-option label="deepseek-prover-v2" value="deepseek/deepseek-prover-v2:free" />
                  <el-option label="gemini-2.5-pro" value="google/gemini-2.5-pro-exp-03-25" />
                  <el-option label="deepseek-chat" value="deepseek-chat" />
                  <el-option label="qwen3-235b" value="qwen3-235b-a22b" />
                  <el-option label="deepseek-r1-0528" value="deepseek/deepseek-r1-0528:free" />
                </el-select>
              </el-form-item>
            </el-form>
          </div>
        </el-card>
        
        <el-card class="history-card" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <h3>处理历史</h3>
            </div>
          </template>
          <div class="processing-history">
            <el-timeline>
              <el-timeline-item
                v-for="(activity, index) in processingHistory"
                :key="index"
                :timestamp="activity.time"
                :type="activity.type"
              >
                {{ activity.content }}
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
// 仍然保留本地配置作为备用
import { llmConfig, systemConfig } from '../config';
import { scanDirectory, uploadFiles, processFiles as apiProcessFiles, getProcessingStatus, cancelProcessing, getProcessingHistory, getSystemSettings } from '../api/importService';

const router = useRouter();
const activeTab = ref('upload');
const fileList = ref([]);
const directoryForm = reactive({
  path: systemConfig.dataDir
});
const directoryFiles = ref([]);

// 处理选项
const processingOptions = reactive({
  parallel: true,
  maxWorkers: systemConfig.maxWorkers,
  validateData: true,
  exportJson: true,
  modelName: llmConfig.modelName
});

// 系统配置状态
const configStatus = reactive({
  isLoading: true,
  isComplete: false,
  missingConfigs: []
});

// 从后端加载系统配置
const loadSystemSettings = async () => {
  configStatus.isLoading = true;
  try {
    const settings = await getSystemSettings();
    
    // 更新处理选项
    processingOptions.maxWorkers = settings.system.maxWorkers || systemConfig.maxWorkers;
    processingOptions.modelName = settings.llm.modelName || llmConfig.modelName;
    
    // 更新目录路径
    directoryForm.path = settings.system.dataDir || systemConfig.dataDir;
    
    // 检查必要配置是否完整
    const missingConfigs = [];
    
    if (!settings.llm.apiKey) {
      missingConfigs.push('LLM API密钥');
    }
    
    if (!settings.geocoding.apiKey) {
      missingConfigs.push('地理编码API密钥');
    }
    
    if (!settings.neo4j.uri || !settings.neo4j.user || !settings.neo4j.password) {
      missingConfigs.push('Neo4j数据库连接信息');
    }
    
    configStatus.missingConfigs = missingConfigs;
    configStatus.isComplete = missingConfigs.length === 0;
    
    if (!configStatus.isComplete) {
      ElMessage.warning('系统配置不完整，请先在参数配置页面完成设置');
    }
  } catch (error) {
    console.error('加载系统配置失败:', error);
    ElMessage.error('加载系统配置失败，将使用默认配置');
  } finally {
    configStatus.isLoading = false;
  }
};

// 组件挂载时加载配置和历史记录
onMounted(() => {
  loadSystemSettings();
  loadProcessingHistory();
});

// 处理状态
const processingStatus = reactive({
  isProcessing: false,
  progress: 0,
  currentFile: '',
  statusText: '',
  totalFiles: 0,
  processedFiles: 0
});

// 处理历史
const processingHistory = ref([]);

// 加载处理历史记录
const loadProcessingHistory = async () => {
  try {
    const history = await getProcessingHistory();
    processingHistory.value = history;
  } catch (error) {
    console.error('加载处理历史失败:', error);
    ElMessage.error('加载处理历史失败');
  }
};

// 文件变更处理
const handleFileChange = (file) => {
  // 检查文件类型
  if (!file.name.endsWith('.docx')) {
    ElMessage.error('只支持上传.docx格式的Word文档');
    return;
  }
  fileList.value.push(file);
};

const handleFileRemove = (file) => {
  fileList.value = fileList.value.filter(f => f.uid !== file.uid);
};

const clearFiles = () => {
  fileList.value = [];
};

// 处理上传的文件
const processFiles = () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择要处理的文件');
    return;
  }
  if (!configStatus.isComplete) {
    ElMessageBox.confirm(
      `系统配置不完整，缺少以下配置：${configStatus.missingConfigs.join('、')}。\n是否前往参数配置页面进行设置？`,
      '配置不完整',
      {
        confirmButtonText: '前往设置',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      router.push('/settings');
    }).catch(() => {});
    return;
  }
  ElMessageBox.confirm(
    `确定要处理选中的${fileList.value.length}个文件吗？`,
    '确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    // 准备上传文件
    const formData = new FormData();

    fileList.value.forEach(file => {
      formData.append('files', file.raw);
    });
    try {
      const response = await uploadFiles(formData);
      const uploadedFiles = response.files;
      startProcessing(uploadedFiles);
    } catch (error) {
      console.error('上传文件失败:', error);
      ElMessage.error('上传文件失败: ' + (error.response?.data?.message || error.message));
    }
  }).catch(() => {
    // 用户取消操作
  });
};

// 扫描目录
const scanDirectoryHandler = async () => {
  if (!directoryForm.path) {
    ElMessage.warning('请输入数据目录路径');
    return;
  }
  try {
    const files = await scanDirectory(directoryForm.path);
    directoryFiles.value = files;
    ElMessage.success(`找到${directoryFiles.value.length}个文档文件`);
  } catch (error) {
    console.error('扫描目录失败:', error);
    ElMessage.error('扫描目录失败: ' + (error.response?.data?.message || error.message));
  }
};

// 全选/取消全选
const selectAllFiles = () => {
  directoryFiles.value.forEach(file => file.selected = true);
};
const deselectAllFiles = () => {
  directoryFiles.value.forEach(file => file.selected = false);
};

// 处理选中的文件
const processSelectedFiles = () => {
  const selectedFiles = directoryFiles.value.filter(file => file.selected);
  if (selectedFiles.length === 0) {
    ElMessage.warning('请先选择要处理的文件');
    return;
  }
  if (!configStatus.isComplete) {
    ElMessageBox.confirm(
      `系统配置不完整，缺少以下配置：${configStatus.missingConfigs.join('、')}。\n是否前往参数配置页面进行设置？`,
      '配置不完整',
      {
        confirmButtonText: '前往设置',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      router.push('/settings');
    }).catch(() => {});
    return;
  }
  ElMessageBox.confirm(
    `确定要处理选中的${selectedFiles.length}个文件吗？`,
    '确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    startProcessing(selectedFiles);
  }).catch(() => {
    // 用户取消操作
  });
};

// 开始处理文件
const startProcessing = (files) => {
  processingStatus.isProcessing = true;
  processingStatus.progress = 0;
  processingStatus.currentFile = '准备处理...';
  processingStatus.statusText = '初始化中';
  processingStatus.totalFiles = files.length;
  processingStatus.processedFiles = 0;
  processingStatus.taskId = null; // 初始化任务ID
  apiProcessFiles(files, processingOptions)
    .then(response => {
      const taskId = response.taskId;
      processingStatus.taskId = taskId; // 保存任务ID
      pollTaskStatus(taskId);
    })
    .catch(error => {
      console.error('启动处理任务失败:', error);
      ElMessage.error('启动处理任务失败: ' + (error.response?.data?.message || error.message));
      processingStatus.isProcessing = false;
    });
};

// 轮询任务状态
const pollTaskStatus = (taskId) => {
  const checkStatus = async () => {
    try {
      const taskStatus = await getProcessingStatus(taskId);
      processingStatus.progress = taskStatus.progress;
      processingStatus.currentFile = taskStatus.currentFile;
      processingStatus.statusText = taskStatus.statusText;
      processingStatus.processedFiles = taskStatus.processedFiles;
      if (taskStatus.newHistoryItems && taskStatus.newHistoryItems.length > 0) {
        taskStatus.newHistoryItems.forEach(item => {
          processingHistory.value.unshift(item);
        });
      }
      if (taskStatus.isProcessing) {
        setTimeout(checkStatus, 1000);
      }
    } catch (error) {
      console.error('获取任务状态失败:', error);
      ElMessage.error('获取任务状态失败，将在3秒后重试');
      setTimeout(checkStatus, 3000);
    }
  };
  checkStatus();
};

// 取消处理
const cancelProcessingHandler = async () => {
  ElMessageBox.confirm(
    '确定要取消当前处理任务吗？',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await cancelProcessing(processingStatus.taskId);
      processingStatus.isProcessing = false;
      ElMessage.info('已取消处理任务');
    } catch (error) {
      console.error('取消任务失败:', error);
      ElMessage.error('取消任务失败: ' + (error.response?.data?.message || error.message));
    }
  }).catch(() => {
    // 用户取消操作
  });
};

// 查看知识图谱
const viewGraph = () => {
  router.push('/graph');
};
</script>

<style scoped>
.import-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.import-content {
  min-height: 300px;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-dragger {
  width: 100%;
  margin-bottom: 20px;
}

.upload-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.directory-select {
  margin-bottom: 20px;
}

.directory-files {
  margin-top: 20px;
}

.directory-actions {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.progress-card {
  margin-top: 20px;
}

.processing-progress {
  padding: 20px 0;
}

.progress-info {
  margin-top: 10px;
  text-align: center;
}

.progress-actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.progress-complete {
  margin-top: 20px;
}

.processing-options {
  padding: 10px 0;
}

.processing-history {
  max-height: 300px;
  overflow-y: auto;
}
</style>