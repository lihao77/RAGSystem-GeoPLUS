<template>
  <div class="search-container">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="search-card">
          <template #header>
            <div class="card-header">
              <h3>实体状态查询</h3>
            </div>
          </template>
          <div class="search-form">
            <el-form :model="searchForm" label-width="100px">
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="实体类型">
                    <el-select v-model="searchForm.entityType" placeholder="选择实体类型" style="width: 100%">
                      <el-option label="全部" value="S-" />
                      <el-option label="地点实体" value="S-L-" />
                      <el-option label="设施实体" value="S-F-" />
                      <el-option label="事件实体" value="S-E-" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="关键词">
                    <el-input v-model="searchForm.keyword" placeholder="输入实体名称关键词" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="时间范围">
                    <el-date-picker v-model="searchForm.timeRange" type="daterange" range-separator="至"
                      start-placeholder="开始日期" end-placeholder="结束日期" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="地理位置">
                    <el-cascader v-model="searchForm.location" :options="locationOptions" placeholder="选择地理位置"
                      :props="{ checkStrictly: true }" style="width: 100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="文档来源">
                    <el-select v-model="searchForm.documentSource" placeholder="选择文档来源" style="width: 100%">
                      <el-option label="全部" value="" />
                      <el-option v-for="doc in documentSources" :key="doc" :label="doc" :value="doc" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="高级选项">
                    <el-switch v-model="searchForm.advancedOptions" active-text="启用" inactive-text="禁用" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row v-if="searchForm.advancedOptions">
                <el-col :span="24">
                  <el-form-item label="Cypher查询">
                    <el-input v-model="searchForm.cypherQuery" type="textarea" :rows="3" placeholder="输入Cypher查询语句" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item>
                <el-button type="primary" @click="searchEntities">查询</el-button>
                <el-button @click="resetForm">重置</el-button>
                <el-button type="success" @click="exportResults" :disabled="!searchResults.length">
                  导出结果
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card class="results-card" v-loading="loading">
          <template #header>
            <div class="card-header">
              <h3>查询结果</h3>
              <span>共找到 {{ searchResults.length }} 条结果</span>
            </div>
          </template>
          <div class="search-results">
            <el-tabs v-model="activeTab">
              <el-tab-pane label="表格视图" name="table">
                <el-table :data="searchResults" style="width: 100%" border @row-click="selectEntity">
                  <el-table-column prop="name" label="实体名称" width="180" />
                  <el-table-column prop="category" label="类型" width="120" />
                  <el-table-column prop="source" label="来源" width="180" />
                  <el-table-column label="属性">
                    <template #default="scope">
                      <div v-for="(value, key) in scope.row.properties" :key="key" class="property-item">
                        <span class="property-key">{{ key }}:</span>
                        <span class="property-value">{{ value }}</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="150">
                    <template #default="scope">
                      <el-button type="text" @click.stop="viewInGraph(scope.row)">
                        在图谱中查看
                      </el-button>
                      <el-button type="text" @click.stop="viewOnMap(scope.row)" v-if="hasLocation(scope.row)">
                        在地图中查看
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="pagination-container">
                  <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize"
                    :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper"
                    :total="searchResults.length" />
                </div>
              </el-tab-pane>
              <el-tab-pane label="关系视图" name="relations">
                <div class="relations-view">
                  <div v-if="selectedEntity" class="entity-relations">
                    <h4>{{ selectedEntity.name }} 的关系</h4>
                    <el-divider />
                    <div v-if="entityRelations.length > 0">
                      <div v-for="(relation, index) in entityRelations" :key="index" class="relation-item">
                        <div class="relation-direction">
                          <span v-if="relation.direction === 'outgoing'">
                            <el-tag size="small" type="primary">从</el-tag>
                            {{ selectedEntity.name }}
                            <el-icon>
                              <ArrowRight />
                            </el-icon>
                            <el-tag size="small" type="success">{{ relation.name }}</el-tag>
                            <el-icon>
                              <ArrowRight />
                            </el-icon>
                            {{ relation.target }}
                          </span>
                          <span v-else>
                            <el-tag size="small" type="warning">从</el-tag>
                            {{ relation.source }}
                            <el-icon>
                              <ArrowRight />
                            </el-icon>
                            <el-tag size="small" type="success">{{ relation.name }}</el-tag>
                            <el-icon>
                              <ArrowRight />
                            </el-icon>
                            {{ selectedEntity.name }}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div v-else class="no-relations">
                      没有找到相关的关系
                    </div>
                  </div>
                  <div v-else class="no-selection">
                    <el-empty description="请选择一个实体以查看其关系" />
                  </div>
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
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { searchService } from '../api';

const router = useRouter();
const loading = ref(false);
const activeTab = ref('table');
const currentPage = ref(1);
const pageSize = ref(10);
const selectedEntity = ref(null);
const entityRelations = ref([]);
const locationOptions = ref([]);
// 搜索表单
const searchForm = reactive({
  entityType: '',
  keyword: '',
  timeRange: [],
  location: [],
  documentSource: '',
  advancedOptions: false,
  cypherQuery: ''
});


// 模拟文档来源
const documentSources = ref([]);

// 模拟搜索结果
const allSearchResults = ref([]);

// 分页后的搜索结果
const searchResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return allSearchResults.value.slice(start, end);
});

// 搜索实体
const searchEntities = async () => {
  loading.value = true;
  try {
    const params = {
      entityType: searchForm.entityType,
      keyword: searchForm.keyword,
      timeRange: searchForm.timeRange,
      location: searchForm.location,
      documentSource: searchForm.documentSource,
      advancedOptions: searchForm.advancedOptions,
      cypherQuery: searchForm.cypherQuery
    };
    const results = await searchService.searchEntities(params);
    allSearchResults.value = results;
    currentPage.value = 1;
  } catch (error) {
    allSearchResults.value = [];
    console.error('实体搜索失败:', error);
  } finally {
    loading.value = false;
  }
}

// 重置表单
const resetForm = () => {
  searchForm.entityType = '';
  searchForm.keyword = '';
  searchForm.timeRange = [];
  searchForm.location = [];
  searchForm.documentSource = '';
  searchForm.advancedOptions = false;
  searchForm.cypherQuery = '';
};

// 导出结果
const exportResults = () => {
  // 实现导出功能
  console.log('导出结果', allSearchResults.value);

  // 创建CSV内容
  let csvContent = '实体ID,实体名称,类型,来源\n';
  allSearchResults.value.forEach(item => {
    csvContent += `${item.id},${item.name},${item.category},${item.source}\n`;
  });

  // 创建下载链接
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', '知识图谱查询结果.csv');
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// 选择实体
const selectEntity = (entity) => {
  selectedEntity.value = entity;
  activeTab.value = 'relations';

  // 模拟获取实体关系
  loading.value = true;
  setTimeout(() => {
    // 模拟关系数据
    entityRelations.value = [
      { direction: 'outgoing', name: '包含', target: '南宁市', properties: {} },
      { direction: 'outgoing', name: '包含', target: '柳州市', properties: {} },
      { direction: 'outgoing', name: '包含', target: '桂林市', properties: {} },
      { direction: 'outgoing', name: '发生', target: '洪涝灾害', properties: { '时间': '2020年' } },
      { direction: 'incoming', source: '2020年', name: '年份', properties: {} },
    ];
    loading.value = false;
  }, 500);
};

// 在图谱中查看
const viewInGraph = (entity) => {
  router.push({
    path: '/graph',
    query: {
      entityId: entity.id,
      highlight: 'true'
    }
  });
};

// 在地图中查看
const viewOnMap = (entity) => {
  router.push({
    path: '/map',
    query: {
      entityId: entity.id,
      lat: entity.properties.纬度,
      lng: entity.properties.经度,
      name: entity.name
    }
  });
};

// 检查实体是否有地理位置信息
const hasLocation = (entity) => {
  return entity.properties &&
    entity.properties.hasOwnProperty('经度') &&
    entity.properties.hasOwnProperty('纬度');
};

onMounted(() => {
  searchService.getGeoCode().then(res => {
    locationOptions.value = res;
    console.log("locationOptions.value", locationOptions.value);
    // 初始化时执行一次搜索
    searchEntities();
  });
  searchService.getDocumentSources().then(res => {
    console.log("res", res);
    documentSources.value = res;
  });
});
</script>

<style scoped>
.search-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  padding: 10px 0;
}

.search-results {
  min-height: 300px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.property-item {
  margin-bottom: 5px;
  display: flex;
}

.property-key {
  font-weight: bold;
  margin-right: 5px;
  min-width: 60px;
}

.property-value {
  flex: 1;
  word-break: break-all;
}

.entity-relations {
  padding: 10px;
}

.relation-item {
  margin-bottom: 15px;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.relation-direction {
  display: flex;
  align-items: center;
  gap: 5px;
}

.no-relations,
.no-selection {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  color: #909399;
}
</style>