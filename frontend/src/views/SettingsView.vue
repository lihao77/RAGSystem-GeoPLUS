<template>
  <div class="settings-container">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <h3>系统参数配置</h3>
              <el-button type="primary" @click="saveSettings">保存配置</el-button>
            </div>
          </template>
          <div class="settings-form">
            <el-form :model="settingsForm" label-width="120px" :rules="rules" ref="settingsFormRef">
              <!-- Neo4j数据库配置 -->
              <el-divider content-position="left">Neo4j数据库配置</el-divider>
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="数据库URI" prop="neo4j.uri">
                    <el-input v-model="settingsForm.neo4j.uri" placeholder="例如: bolt://localhost:7687" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="用户名" prop="neo4j.user">
                    <el-input v-model="settingsForm.neo4j.user" placeholder="Neo4j用户名" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="密码" prop="neo4j.password">
                    <el-input v-model="settingsForm.neo4j.password" type="password" placeholder="Neo4j密码" show-password />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row>
                <el-col :span="24">
                  <el-form-item>
                    <el-button type="primary" @click="testNeo4jConnection">测试连接</el-button>
                    <el-tag v-if="connectionStatus.neo4j" :type="connectionStatus.neo4j.success ? 'success' : 'danger'" style="margin-left: 10px;">
                      {{ connectionStatus.neo4j.message }}
                    </el-tag>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <!-- LLM服务配置 -->
              <el-divider content-position="left">LLM服务配置</el-divider>
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="API端点" prop="llm.apiEndpoint">
                    <el-input v-model="settingsForm.llm.apiEndpoint" placeholder="例如: https://openrouter.ai/api/v1" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="API密钥" prop="llm.apiKey">
                    <el-input v-model="settingsForm.llm.apiKey" type="password" placeholder="LLM API密钥" show-password />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="模型名称" prop="llm.modelName">
                    <el-select v-model="settingsForm.llm.modelName" placeholder="选择模型或输入自定义模型名称" style="width: 100%" filterable allow-create default-first-option>
                      <el-option label="deepseek-r1t-chimera" value="tngtech/deepseek-r1t-chimera:free" />
                      <el-option label="deepseek-prover-v2" value="deepseek/deepseek-prover-v2:free" />
                      <el-option label="gemini-2.5-pro" value="google/gemini-2.5-pro-exp-03-25" />
                      <el-option label="deepseek-chat" value="deepseek-chat" />
                      <el-option label="qwen3-235b" value="qwen3-235b-a22b" />
                      <el-option label="deepseek-r1-0528" value="deepseek/deepseek-r1-0528:free" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row>
                <el-col :span="24">
                  <el-form-item>
                    <el-button type="primary" @click="testLLMConnection">测试连接</el-button>
                    <el-tag v-if="connectionStatus.llm" :type="connectionStatus.llm.success ? 'success' : 'danger'" style="margin-left: 10px;">
                      {{ connectionStatus.llm.message }}
                    </el-tag>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <!-- 地理编码服务配置 -->
              <el-divider content-position="left">地理编码服务配置</el-divider>
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="服务提供商" prop="geocoding.service">
                    <el-select v-model="settingsForm.geocoding.service" placeholder="选择服务提供商" style="width: 100%">
                      <el-option label="百度地图" value="baidu" />
                      <el-option label="高德地图" value="amap" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="API密钥" prop="geocoding.apiKey">
                    <el-input v-model="settingsForm.geocoding.apiKey" placeholder="地理编码API密钥" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row>
                <el-col :span="24">
                  <el-form-item>
                    <el-button type="primary" @click="testGeocodingConnection">测试连接</el-button>
                    <el-tag v-if="connectionStatus.geocoding" :type="connectionStatus.geocoding.success ? 'success' : 'danger'" style="margin-left: 10px;">
                      {{ connectionStatus.geocoding.message }}
                    </el-tag>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <!-- 系统配置 -->
              <el-divider content-position="left">系统配置</el-divider>
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="最大并行线程数" prop="system.maxWorkers">
                    <el-input-number v-model="settingsForm.system.maxWorkers" :min="1" :max="8" />
                  </el-form-item>
                </el-col>
                <el-col :span="16">
                  <el-form-item label="数据目录" prop="system.dataDir">
                    <el-input v-model="settingsForm.system.dataDir" placeholder="数据文件目录路径" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row>
                <el-col :span="24">
                  <el-form-item label="Python解释器路径" prop="system.pythonPath">
                    <el-input v-model="settingsForm.system.pythonPath" placeholder="Python解释器的完整路径，例如：python 或 D:/anaconda3/envs/myenv/python.exe" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row>
                <el-col :span="24">
                  <el-form-item label="启用数据验证">
                    <el-switch v-model="settingsForm.system.validateData" />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { getSettings, saveSettings as apiSaveSettings, testNeo4jConnection as apiTestNeo4j, testLLMConnection as apiTestLLM, testGeocodingConnection as apiTestGeocoding } from '../api/settingsService';

const settingsFormRef = ref(null);

// 表单数据
const settingsForm = reactive({
  neo4j: {
    uri: '',
    user: '',
    password: ''
  },
  llm: {
    apiEndpoint: '',
    apiKey: '',
    modelName: ''
  },
  geocoding: {
    service: 'baidu',
    apiKey: ''
  },
  system: {
    maxWorkers: 4,
    dataDir: '',
    validateData: true,
    pythonPath: 'python'
  }
});

// 从后端加载配置
const loadSettings = async () => {
  try {
    const response = await getSettings();
    if (response) {
      Object.keys(response).forEach(key => {
        if (settingsForm[key]) {
          Object.assign(settingsForm[key], response[key]);
        }
      });
    }
  } catch (error) {
    ElMessage.error('加载配置失败: ' + error.message);
  }
};

// 表单验证规则
const rules = {
  'neo4j.uri': [
    { required: true, message: '请输入Neo4j数据库URI', trigger: 'blur' },
    { pattern: /^bolt:\/\//, message: 'URI格式应为bolt://...', trigger: 'blur' }
  ],
  'neo4j.user': [
    { required: true, message: '请输入Neo4j用户名', trigger: 'blur' }
  ],
  'neo4j.password': [
    { required: true, message: '请输入Neo4j密码', trigger: 'blur' }
  ],
  'llm.apiEndpoint': [
    { required: true, message: '请输入LLM API端点', trigger: 'blur' },
    { pattern: /^https?:\/\//, message: 'API端点应以http://或https://开头', trigger: 'blur' }
  ],
  'llm.apiKey': [
    { required: true, message: '请输入LLM API密钥', trigger: 'blur' }
  ],
  'llm.modelName': [
    { required: true, message: '请选择或输入模型名称', trigger: 'change' }
  ],
  'geocoding.service': [
    { required: true, message: '请选择地理编码服务提供商', trigger: 'change' }
  ],
  'geocoding.apiKey': [
    { required: true, message: '请输入地理编码API密钥', trigger: 'blur' }
  ],
  'system.maxWorkers': [
    { required: true, message: '请设置最大并行线程数', trigger: 'blur' },
    { type: 'number', min: 1, max: 8, message: '线程数应在1-8之间', trigger: 'blur' }
  ],
  'system.dataDir': [
    { required: true, message: '请输入数据目录路径', trigger: 'blur' }
  ],
  'system.pythonPath': [
    { required: true, message: '请输入Python解释器路径', trigger: 'blur' }
  ]
};

// 连接状态
const connectionStatus = reactive({
  neo4j: null,
  llm: null,
  geocoding: null
});

// 测试Neo4j连接
const testNeo4jConnection = async () => {
  try {
    const result = await apiTestNeo4j(settingsForm.neo4j);
    connectionStatus.neo4j = { 
      success: result.success, 
      message: result.message 
    };
    
    ElMessage({
      type: connectionStatus.neo4j.success ? 'success' : 'error',
      message: connectionStatus.neo4j.message
    });
  } catch (error) {
    connectionStatus.neo4j = { 
      success: false, 
      message: '连接测试失败: ' + error.message 
    };
    
    ElMessage({
      type: 'error',
      message: connectionStatus.neo4j.message
    });
  }
};

// 测试LLM连接
const testLLMConnection = async () => {
  try {
    const result = await apiTestLLM(settingsForm.llm);
    connectionStatus.llm = { 
      success: result.success, 
      message: result.message 
    };
    
    ElMessage({
      type: connectionStatus.llm.success ? 'success' : 'error',
      message: connectionStatus.llm.message
    });
  } catch (error) {
    connectionStatus.llm = { 
      success: false, 
      message: '连接测试失败: ' + error.message 
    };
    
    ElMessage({
      type: 'error',
      message: connectionStatus.llm.message
    });
  }
};

// 测试地理编码服务连接
const testGeocodingConnection = async () => {
  try {
    const result = await apiTestGeocoding(settingsForm.geocoding);
    connectionStatus.geocoding = { 
      success: result.success, 
      message: result.message 
    };
    
    ElMessage({
      type: connectionStatus.geocoding.success ? 'success' : 'error',
      message: connectionStatus.geocoding.message
    });
  } catch (error) {
    connectionStatus.geocoding = { 
      success: false, 
      message: '连接测试失败: ' + error.message 
    };
    
    ElMessage({
      type: 'error',
      message: connectionStatus.geocoding.message
    });
  }
};

// 保存设置
const saveSettings = () => {
  settingsFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const result = await apiSaveSettings(settingsForm);
        ElMessage({
          type: 'success',
          message: result.message || '配置已保存'
        });
      } catch (error) {
        ElMessage({
          type: 'error',
          message: '保存配置失败: ' + error.message
        });
      }
    } else {
      ElMessage({
        type: 'error',
        message: '请检查表单填写是否正确'
      });
      return false;
    }
  });
};

onMounted(() => {
  // 初始化时从后端加载配置
  loadSettings();
})
</script>

<style scoped>
.settings-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.settings-form {
  padding: 20px 0;
}

.el-divider {
  margin: 20px 0;
}

.el-divider__text {
  font-weight: bold;
  color: #409EFF;
}
</style>