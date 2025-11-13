<template>
  <div class="evaluation-container">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="evaluation-card">
          <template #header>
            <div class="card-header">
              <h3>知识图谱评估</h3>
            </div>
          </template>
          <div class="evaluation-content">
            <el-tabs v-model="activeTab">
              <!-- 评估方法 -->
              <el-tab-pane label="评估方法" name="method">
                <div class="method-selection">
                  <el-form :model="evaluationForm" label-width="120px">
                    <el-form-item label="评估类型">
                      <el-radio-group v-model="evaluationForm.evaluationType">
                        <el-radio label="accuracy">准确度评估</el-radio>
                        <el-radio label="recall">召回率评估</el-radio>
                        <el-radio label="comprehensive">综合评估</el-radio>
                      </el-radio-group>
                    </el-form-item>
                    
                    <el-form-item label="抽样方式">
                      <el-radio-group v-model="evaluationForm.samplingMethod">
                        <el-radio label="random">随机抽取</el-radio>
                        <el-radio label="document">按文档抽取</el-radio>
                        <el-radio label="entity">按实体类型抽取</el-radio>
                      </el-radio-group>
                    </el-form-item>
                    
                    <el-form-item label="样本数量" v-if="evaluationForm.samplingMethod === 'random'">
                      <el-input-number v-model="evaluationForm.sampleSize" :min="10" :max="100" />
                    </el-form-item>
                    
                    <el-form-item label="选择文档" v-if="evaluationForm.samplingMethod === 'document'">
                      <el-select v-model="evaluationForm.selectedDocuments" multiple placeholder="选择要评估的文档" style="width: 100%">
                        <el-option 
                          v-for="doc in availableDocuments" 
                          :key="doc.id" 
                          :label="doc.name" 
                          :value="doc.id" 
                        />
                      </el-select>
                    </el-form-item>
                    
                    <el-form-item label="实体类型" v-if="evaluationForm.samplingMethod === 'entity'">
                      <el-select v-model="evaluationForm.selectedEntityTypes" multiple placeholder="选择要评估的实体类型" style="width: 100%">
                        <el-option label="地点实体" value="Location" />
                        <el-option label="设施实体" value="Facility" />
                        <el-option label="事件实体" value="Event" />
                        <el-option label="状态实体" value="State" />
                      </el-select>
                    </el-form-item>
                    
                    <el-form-item>
                      <el-button type="primary" @click="generateSamples">生成评估样本</el-button>
                    </el-form-item>
                  </el-form>
                </div>
              </el-tab-pane>
              
              <!-- 样本标注 -->
              <el-tab-pane label="样本标注" name="annotation" :disabled="!hasSamples">
                <div class="annotation-area" v-if="currentSample">
                  <el-card class="sample-card">
                    <template #header>
                      <div class="sample-header">
                        <h4>样本 {{ currentSampleIndex + 1 }}/{{ evaluationSamples.length }}</h4>
                        <div class="sample-navigation">
                          <el-button-group>
                            <el-button :disabled="currentSampleIndex === 0" @click="previousSample">
                              <el-icon><ArrowLeft /></el-icon>
                            </el-button>
                            <el-button :disabled="currentSampleIndex === evaluationSamples.length - 1" @click="nextSample">
                              <el-icon><ArrowRight /></el-icon>
                            </el-button>
                          </el-button-group>
                        </div>
                      </div>
                    </template>
                    
                    <div class="sample-content">
                      <div class="text-context">
                        <h5>原文内容</h5>
                        <div class="context-text" v-html="highlightEntities(currentSample.context)"></div>
                      </div>
                      
                      <el-divider />
                      
                      <div class="entity-evaluation" v-if="evaluationForm.evaluationType !== 'recall'">
                        <h5>实体准确度评估</h5>
                        <el-table :data="currentSample.entities" style="width: 100%">
                          <el-table-column prop="name" label="实体名称" width="180" />
                          <el-table-column prop="type" label="实体类型" width="120" />
                          <el-table-column label="评估">
                            <template #default="scope">
                              <el-radio-group v-model="scope.row.evaluation">
                                <el-radio label="correct">正确</el-radio>
                                <el-radio label="incorrect">错误</el-radio>
                                <el-radio label="partial">部分正确</el-radio>
                              </el-radio-group>
                            </template>
                          </el-table-column>
                          <el-table-column label="备注">
                            <template #default="scope">
                              <el-input 
                                v-model="scope.row.comment" 
                                type="textarea" 
                                :rows="1" 
                                placeholder="添加评估备注（可选）" 
                              />
                            </template>
                          </el-table-column>
                        </el-table>
                      </div>
                      
                      <div class="relation-evaluation" v-if="evaluationForm.evaluationType !== 'recall' && currentSample.relations.length > 0">
                        <h5>关系准确度评估</h5>
                        <el-table :data="currentSample.relations" style="width: 100%">
                          <el-table-column label="源实体" width="150">
                            <template #default="scope">
                              {{ scope.row.source }}
                            </template>
                          </el-table-column>
                          <el-table-column label="关系" width="120">
                            <template #default="scope">
                              {{ scope.row.relation }}
                            </template>
                          </el-table-column>
                          <el-table-column label="目标实体" width="150">
                            <template #default="scope">
                              {{ scope.row.target }}
                            </template>
                          </el-table-column>
                          <el-table-column label="评估">
                            <template #default="scope">
                              <el-radio-group v-model="scope.row.evaluation">
                                <el-radio label="correct">正确</el-radio>
                                <el-radio label="incorrect">错误</el-radio>
                                <el-radio label="partial">部分正确</el-radio>
                              </el-radio-group>
                            </template>
                          </el-table-column>
                          <el-table-column label="备注">
                            <template #default="scope">
                              <el-input 
                                v-model="scope.row.comment" 
                                type="textarea" 
                                :rows="1" 
                                placeholder="添加评估备注（可选）" 
                              />
                            </template>
                          </el-table-column>
                        </el-table>
                      </div>
                      
                      <div class="missing-entities" v-if="evaluationForm.evaluationType !== 'accuracy'">
                        <h5>漏检实体标注（召回率评估）</h5>
                        <p class="annotation-tip">请标注文本中存在但未被系统识别的实体</p>
                        
                        <div class="missing-entity-list">
                          <div v-for="(entity, index) in missingEntities" :key="index" class="missing-entity-item">
                            <el-row :gutter="10">
                              <el-col :span="8">
                                <el-input v-model="entity.name" placeholder="实体名称" />
                              </el-col>
                              <el-col :span="6">
                                <el-select v-model="entity.type" placeholder="实体类型" style="width: 100%">
                                  <el-option label="地点实体" value="Location" />
                                  <el-option label="设施实体" value="Facility" />
                                  <el-option label="事件实体" value="Event" />
                                  <el-option label="状态实体" value="State" />
                                </el-select>
                              </el-col>
                              <el-col :span="8">
                                <el-input v-model="entity.comment" placeholder="备注（可选）" />
                              </el-col>
                              <el-col :span="2">
                                <el-button type="danger" @click="removeMissingEntity(index)">
                                  <el-icon><Delete /></el-icon>
                                </el-button>
                              </el-col>
                            </el-row>
                          </div>
                        </div>
                        
                        <el-button type="primary" plain @click="addMissingEntity" style="margin-top: 10px">
                          <el-icon><Plus /></el-icon> 添加漏检实体
                        </el-button>
                      </div>
                      
                      <div class="missing-relations" v-if="evaluationForm.evaluationType !== 'accuracy'">
                        <h5>漏检关系标注（召回率评估）</h5>
                        <p class="annotation-tip">请标注文本中存在但未被系统识别的关系</p>
                        
                        <div class="missing-relation-list">
                          <div v-for="(relation, index) in missingRelations" :key="index" class="missing-relation-item">
                            <el-row :gutter="10">
                              <el-col :span="6">
                                <el-input v-model="relation.source" placeholder="源实体" />
                              </el-col>
                              <el-col :span="5">
                                <el-input v-model="relation.relation" placeholder="关系" />
                              </el-col>
                              <el-col :span="6">
                                <el-input v-model="relation.target" placeholder="目标实体" />
                              </el-col>
                              <el-col :span="5">
                                <el-input v-model="relation.comment" placeholder="备注（可选）" />
                              </el-col>
                              <el-col :span="2">
                                <el-button type="danger" @click="removeMissingRelation(index)">
                                  <el-icon><Delete /></el-icon>
                                </el-button>
                              </el-col>
                            </el-row>
                          </div>
                        </div>
                        
                        <el-button type="primary" plain @click="addMissingRelation" style="margin-top: 10px">
                          <el-icon><Plus /></el-icon> 添加漏检关系
                        </el-button>
                      </div>
                      
                      <div class="sample-actions">
                        <el-button type="success" @click="saveSampleAnnotation">保存当前样本标注</el-button>
                      </div>
                    </div>
                  </el-card>
                </div>
                <div v-else class="no-samples">
                  <el-empty description="请先在评估方法标签页生成评估样本" />
                </div>
              </el-tab-pane>
              
              <!-- 评估结果 -->
              <el-tab-pane label="评估结果" name="results" :disabled="!hasAnnotations">
                <div class="results-area">
                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-card class="metrics-card">
                        <template #header>
                          <div class="card-header">
                            <h4>评估指标</h4>
                          </div>
                        </template>
                        <div class="metrics-content" v-loading="calculatingMetrics">
                          <el-descriptions :column="1" border>
                            <el-descriptions-item label="样本总数">{{ evaluationSamples.length }}</el-descriptions-item>
                            <el-descriptions-item label="已标注样本数">{{ completedAnnotations }}</el-descriptions-item>
                            <el-descriptions-item label="实体准确率" v-if="evaluationForm.evaluationType !== 'recall'">
                              {{ metrics.entityAccuracy }}%
                            </el-descriptions-item>
                            <el-descriptions-item label="关系准确率" v-if="evaluationForm.evaluationType !== 'recall'">
                              {{ metrics.relationAccuracy }}%
                            </el-descriptions-item>
                            <el-descriptions-item label="实体召回率" v-if="evaluationForm.evaluationType !== 'accuracy'">
                              {{ metrics.entityRecall }}%
                            </el-descriptions-item>
                            <el-descriptions-item label="关系召回率" v-if="evaluationForm.evaluationType !== 'accuracy'">
                              {{ metrics.relationRecall }}%
                            </el-descriptions-item>
                            <el-descriptions-item label="实体F1值" v-if="evaluationForm.evaluationType === 'comprehensive'">
                              {{ metrics.entityF1 }}%
                            </el-descriptions-item>
                            <el-descriptions-item label="关系F1值" v-if="evaluationForm.evaluationType === 'comprehensive'">
                              {{ metrics.relationF1 }}%
                            </el-descriptions-item>
                          </el-descriptions>
                        </div>
                      </el-card>
                    </el-col>
                    <el-col :span="12">
                      <el-card class="chart-card">
                        <template #header>
                          <div class="card-header">
                            <h4>评估图表</h4>
                          </div>
                        </template>
                        <div class="chart-content" ref="metricsChartContainer">
                          <!-- 图表将在这里渲染 -->
                        </div>
                      </el-card>
                    </el-col>
                  </el-row>
                  
                  <el-card class="detailed-results" style="margin-top: 20px">
                    <template #header>
                      <div class="card-header">
                        <h4>详细评估结果</h4>
                        <div class="export-actions">
                          <el-button type="success" @click="exportResults">
                            <el-icon><Download /></el-icon> 导出评估报告
                          </el-button>
                        </div>
                      </div>
                    </template>
                    <div class="results-content">
                      <el-tabs>
                        <el-tab-pane label="实体评估" name="entity-results">
                          <el-table :data="entityResults" style="width: 100%">
                            <el-table-column prop="entityType" label="实体类型" />
                            <el-table-column prop="totalCount" label="总数" />
                            <el-table-column prop="correctCount" label="正确数" />
                            <el-table-column prop="incorrectCount" label="错误数" />
                            <el-table-column prop="partialCount" label="部分正确数" />
                            <el-table-column prop="missingCount" label="漏检数" />
                            <el-table-column prop="accuracy" label="准确率" />
                            <el-table-column prop="recall" label="召回率" />
                            <el-table-column prop="f1" label="F1值" />
                          </el-table>
                        </el-tab-pane>
                        <el-tab-pane label="关系评估" name="relation-results">
                          <el-table :data="relationResults" style="width: 100%">
                            <el-table-column prop="relationType" label="关系类型" />
                            <el-table-column prop="totalCount" label="总数" />
                            <el-table-column prop="correctCount" label="正确数" />
                            <el-table-column prop="incorrectCount" label="错误数" />
                            <el-table-column prop="partialCount" label="部分正确数" />
                            <el-table-column prop="missingCount" label="漏检数" />
                            <el-table-column prop="accuracy" label="准确率" />
                            <el-table-column prop="recall" label="召回率" />
                            <el-table-column prop="f1" label="F1值" />
                          </el-table>
                        </el-tab-pane>
                        <el-tab-pane label="错误分析" name="error-analysis">
                          <div class="error-analysis">
                            <h5>常见错误类型</h5>
                            <div class="error-chart" ref="errorChartContainer">
                              <!-- 错误类型图表将在这里渲染 -->
                            </div>
                            
                            <h5>错误实例</h5>
                            <el-collapse>
                              <el-collapse-item v-for="(error, index) in commonErrors" :key="index" :title="error.type + ' - ' + error.count + '个实例'">
                                <div v-for="(instance, i) in error.instances" :key="i" class="error-instance">
                                  <p><strong>原文:</strong> {{ instance.context }}</p>
                                  <p><strong>错误:</strong> {{ instance.description }}</p>
                                  <p><strong>备注:</strong> {{ instance.comment }}</p>
                                  <el-divider v-if="i < error.instances.length - 1" />
                                </div>
                              </el-collapse-item>
                            </el-collapse>
                          </div>
                        </el-tab-pane>
                      </el-tabs>
                    </div>
                  </el-card>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import * as echarts from 'echarts';
import { evaluationService } from '../api/evaluationService';

const router = useRouter();
const activeTab = ref('method');
const metricsChartContainer = ref(null);
const errorChartContainer = ref(null);
const metricsChart = ref(null);
const errorChart = ref(null);
const calculatingMetrics = ref(false);

// 评估表单
const evaluationForm = reactive({
  evaluationType: 'comprehensive',
  samplingMethod: 'random',
  sampleSize: 30,
  selectedDocuments: [],
  selectedEntityTypes: []
});

// 可用文档列表
const availableDocuments = ref([]);

// 评估样本
const evaluationSamples = ref([]);
const currentSampleIndex = ref(0);
const currentSample = computed(() => {
  if (evaluationSamples.value.length === 0) return null;
  return evaluationSamples.value[currentSampleIndex.value];
});

// 漏检实体和关系
const missingEntities = ref([]);
const missingRelations = ref([]);

// 评估指标
const metrics = reactive({
  entityAccuracy: 0,
  relationAccuracy: 0,
  entityRecall: 0,
  relationRecall: 0,
  entityF1: 0,
  relationF1: 0
});

// 详细结果
const entityResults = ref([]);
const relationResults = ref([]);
const commonErrors = ref([]);

// 计算属性
const hasSamples = computed(() => evaluationSamples.value.length > 0);
const hasAnnotations = computed(() => {
  return evaluationSamples.value.some(sample => sample.annotated);
});
const completedAnnotations = computed(() => {
  return evaluationSamples.value.filter(sample => sample.annotated).length;
});

// 初始化
onMounted(async () => {
  try {
    // 获取可用文档列表
    const docs = await evaluationService.getAvailableDocuments();
    availableDocuments.value = docs;
    console.log('可用文档列表:', docs);
    // 初始化图表
    initCharts();
  } catch (error) {
    ElMessage.error('初始化评估页面失败: ' + error.message);
    console.error('初始化评估页面失败:', error);
  }
});

// 监听标签页切换
watch(activeTab, (newTab) => {
  if (newTab === 'results' && hasAnnotations.value) {
    calculateMetrics();
  }
});

// 生成评估样本
async function generateSamples() {
  try {
    const params = {
      evaluationType: evaluationForm.evaluationType,
      samplingMethod: evaluationForm.samplingMethod,
      sampleSize: evaluationForm.sampleSize
    };
    
    if (evaluationForm.samplingMethod === 'document') {
      params.documentIds = evaluationForm.selectedDocuments;
    } else if (evaluationForm.samplingMethod === 'entity') {
      params.entityTypes = evaluationForm.selectedEntityTypes;
    }
    
    // 调用API生成样本
    const samples = await evaluationService.generateSamples(params);
    
    // 初始化样本数据
    evaluationSamples.value = samples.map(sample => ({
      ...sample,
      annotated: false,
      entities: sample.entities.map(entity => ({
        ...entity,
        evaluation: null,
        comment: ''
      })),
      relations: sample.relations.map(relation => ({
        ...relation,
        evaluation: null,
        comment: ''
      }))
    }));
    
    // 重置当前样本索引
    currentSampleIndex.value = 0;
    
    // 清空漏检实体和关系
    resetMissingItems();
    
    // 切换到标注标签页
    activeTab.value = 'annotation';
    
    ElMessage.success(`成功生成 ${samples.length} 个评估样本`);
  } catch (error) {
    ElMessage.error('生成评估样本失败: ' + error.message);
    console.error('生成评估样本失败:', error);
  }
}

// 高亮显示实体
function highlightEntities(text) {
  if (!text || !currentSample.value) return text;
  
  let highlightedText = text;
  const entities = currentSample.value.entities;
  
  // 简单的高亮处理，实际项目中可能需要更复杂的处理
  entities.forEach(entity => {
    const regex = new RegExp(entity.name, 'g');
    const color = getEntityColor(entity.type);
    highlightedText = highlightedText.replace(regex, `<span style="background-color: ${color}; padding: 0 2px;">${entity.name}</span>`);
  });
  
  return highlightedText;
}

// 根据实体类型获取高亮颜色
function getEntityColor(type) {
  const colorMap = {
    'Location': '#91d5ff',
    'Facility': '#b7eb8f',
    'Event': '#ffccc7',
    'State': '#d3adf7'
  };
  
  return colorMap[type] || '#e6f7ff';
}

// 添加漏检实体
function addMissingEntity() {
  missingEntities.value.push({
    name: '',
    type: '',
    comment: ''
  });
}

// 移除漏检实体
function removeMissingEntity(index) {
  missingEntities.value.splice(index, 1);
}

// 添加漏检关系
function addMissingRelation() {
  missingRelations.value.push({
    source: '',
    relation: '',
    target: '',
    comment: ''
  });
}

// 移除漏检关系
function removeMissingRelation(index) {
  missingRelations.value.splice(index, 1);
}

// 重置漏检项
function resetMissingItems() {
  missingEntities.value = [];
  missingRelations.value = [];
}

// 保存当前样本标注
async function saveSampleAnnotation() {
  try {
    // 验证必填项
    if (evaluationForm.evaluationType !== 'recall') {
      const hasUnratedEntities = currentSample.value.entities.some(entity => entity.evaluation === null);
      const hasUnratedRelations = currentSample.value.relations.some(relation => relation.evaluation === null);
      
      if (hasUnratedEntities || hasUnratedRelations) {
        ElMessage.warning('请完成所有实体和关系的评估');
        return;
      }
    }
    
    if (evaluationForm.evaluationType !== 'accuracy') {
      // 验证漏检实体
      const invalidMissingEntities = missingEntities.value.some(entity => !entity.name || !entity.type);
      if (invalidMissingEntities && missingEntities.value.length > 0) {
        ElMessage.warning('请完善漏检实体的名称和类型');
        return;
      }
      
      // 验证漏检关系
      const invalidMissingRelations = missingRelations.value.some(relation => !relation.source || !relation.relation || !relation.target);
      if (invalidMissingRelations && missingRelations.value.length > 0) {
        ElMessage.warning('请完善漏检关系的源实体、关系和目标实体');
        return;
      }
    }
    
    // 更新当前样本的标注状态
    const currentSampleData = evaluationSamples.value[currentSampleIndex.value];
    currentSampleData.annotated = true;
    
    // 添加漏检实体和关系
    currentSampleData.missingEntities = [...missingEntities.value];
    currentSampleData.missingRelations = [...missingRelations.value];
    
    // 保存到后端
    await evaluationService.saveSampleAnnotation({
      sampleId: currentSampleData.id,
      entities: currentSampleData.entities,
      relations: currentSampleData.relations,
      missingEntities: currentSampleData.missingEntities,
      missingRelations: currentSampleData.missingRelations
    });
    
    ElMessage.success('样本标注已保存');
    
    // 自动前进到下一个样本
    if (currentSampleIndex.value < evaluationSamples.value.length - 1) {
      nextSample();
    } else {
      // 如果是最后一个样本，询问是否查看结果
      if (completedAnnotations.value === evaluationSamples.value.length) {
        ElMessageBox.confirm('所有样本已标注完成，是否查看评估结果？', '标注完成', {
          confirmButtonText: '查看结果',
          cancelButtonText: '继续编辑',
          type: 'success'
        }).then(() => {
          activeTab.value = 'results';
        }).catch(() => {});
      }
    }
  } catch (error) {
    ElMessage.error('保存样本标注失败: ' + error.message);
    console.error('保存样本标注失败:', error);
  }
}

// 前一个样本
function previousSample() {
  if (currentSampleIndex.value > 0) {
    currentSampleIndex.value--;
    loadCurrentSampleMissingItems();
  }
}

// 下一个样本
function nextSample() {
  if (currentSampleIndex.value < evaluationSamples.value.length - 1) {
    currentSampleIndex.value++;
    loadCurrentSampleMissingItems();
  }
}

// 加载当前样本的漏检项
function loadCurrentSampleMissingItems() {
  const sample = evaluationSamples.value[currentSampleIndex.value];
  if (sample.missingEntities) {
    missingEntities.value = [...sample.missingEntities];
  } else {
    missingEntities.value = [];
  }
  
  if (sample.missingRelations) {
    missingRelations.value = [...sample.missingRelations];
  } else {
    missingRelations.value = [];
  }
}

// 计算评估指标
async function calculateMetrics() {
  calculatingMetrics.value = true;
  try {
    // 调用API计算指标
    const results = await evaluationService.calculateMetrics({
      samples: evaluationSamples.value.filter(sample => sample.annotated),
      evaluationType: evaluationForm.evaluationType
    });
    
    // 更新指标
    Object.assign(metrics, results.metrics);
    
    // 更新详细结果
    entityResults.value = results.entityResults;
    relationResults.value = results.relationResults;
    commonErrors.value = results.commonErrors;
    
    // 更新图表
    updateCharts();
  } catch (error) {
    ElMessage.error('计算评估指标失败: ' + error.message);
    console.error('计算评估指标失败:', error);
  } finally {
    calculatingMetrics.value = false;
  }
}

// 初始化图表
function initCharts() {
  // 指标图表
  if (metricsChartContainer.value) {
    metricsChart.value = echarts.init(metricsChartContainer.value);
  }
  
  // 错误分析图表
  if (errorChartContainer.value) {
    errorChart.value = echarts.init(errorChartContainer.value);
  }
}

// 更新图表
function updateCharts() {
  // 更新指标图表
  if (metricsChart.value) {
    const option = {
      title: {
        text: '评估指标对比',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        data: ['准确率', '召回率', 'F1值'],
        bottom: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: ['实体', '关系']
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: {
          formatter: '{value}%'
        }
      },
      series: [
        {
          name: '准确率',
          type: 'bar',
          data: [metrics.entityAccuracy, metrics.relationAccuracy]
        },
        {
          name: '召回率',
          type: 'bar',
          data: [metrics.entityRecall, metrics.relationRecall]
        },
        {
          name: 'F1值',
          type: 'bar',
          data: [metrics.entityF1, metrics.relationF1]
        }
      ]
    };
    
    metricsChart.value.setOption(option);
  }
  
  // 更新错误分析图表
  if (errorChart.value && commonErrors.value.length > 0) {
    const errorTypes = commonErrors.value.map(error => error.type);
    const errorCounts = commonErrors.value.map(error => error.count);
    
    const option = {
      title: {
        text: '错误类型分布',
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        data: errorTypes
      },
      series: [
        {
          type: 'pie',
          radius: '60%',
          center: ['50%', '50%'],
          data: errorTypes.map((type, index) => ({
            name: type,
            value: errorCounts[index]
          })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    };
    
    errorChart.value.setOption(option);
  }
}

// 导出评估报告
async function exportResults() {
  try {
    // 调用API导出报告
    const reportUrl = await evaluationService.exportEvaluationReport({
      samples: evaluationSamples.value.filter(sample => sample.annotated),
      metrics,
      entityResults: entityResults.value,
      relationResults: relationResults.value,
      commonErrors: commonErrors.value
    });
    
    // 下载报告
    const link = document.createElement('a');
    link.href = reportUrl;
    link.download = '知识图谱评估报告.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    ElMessage.success('评估报告已导出');
  } catch (error) {
    ElMessage.error('导出评估报告失败: ' + error.message);
    console.error('导出评估报告失败:', error);
  }
}

// 监听窗口大小变化，调整图表大小
window.addEventListener('resize', () => {
  if (metricsChart.value) {
    metricsChart.value.resize();
  }
  if (errorChart.value) {
    errorChart.value.resize();
  }
});
</script>

<style scoped>
.evaluation-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sample-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.context-text {
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 15px;
  line-height: 1.6;
  max-height: 200px;
  overflow-y: auto;
}

.entity-evaluation,
.relation-evaluation,
.missing-entities,
.missing-relations {
  margin-top: 20px;
  margin-bottom: 20px;
}

.annotation-tip {
  color: #909399;
  font-size: 14px;
  margin-bottom: 10px;
}

.missing-entity-item,
.missing-relation-item {
  margin-bottom: 10px;
}

.sample-actions {
  margin-top: 30px;
  display: flex;
  justify-content: center;
}

.metrics-content,
.chart-content {
  height: 300px;
}

.error-chart {
  height: 300px;
  margin-bottom: 20px;
}

.error-instance {
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.export-actions {
  display: flex;
  align-items: center;
}
</style>
