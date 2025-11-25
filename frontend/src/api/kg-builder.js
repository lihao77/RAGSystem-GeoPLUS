/**
 * KG Builder API客户端
 * 知识图谱构建器相关API接口
 */

import axios from 'axios'

const API_BASE = '/api/kg-builder'

export const kgBuilderApi = {
  // ==================== 状态管理 ====================
  
  /**
   * 获取KG Builder模块状态
   */
  async getStatus() {
    const response = await axios.get(`${API_BASE}/status`)
    return response.data
  },

  /**
   * 初始化KG Builder模块
   */
  async initModule(config) {
    const response = await axios.post(`${API_BASE}/init`, { config })
    return response.data
  },

  // ==================== Pipeline配置管理 ====================
  
  /**
   * 获取所有Pipeline配置列表
   */
  async listPipelineConfigs() {
    const response = await axios.get(`${API_BASE}/pipeline/configs`)
    return response.data
  },

  /**
   * 创建新的Pipeline配置
   */
  async createPipelineConfig({ name, description, base_config }) {
    const response = await axios.post(`${API_BASE}/pipeline/configs`, {
      name,
      description,
      base_config
    })
    return response.data
  },

  /**
   * 获取指定Pipeline配置
   */
  async getPipelineConfig(name) {
    const response = await axios.get(`${API_BASE}/pipeline/configs/${name}`)
    return response.data
  },

  /**
   * 更新Pipeline配置
   */
  async updatePipelineConfig(name, updates) {
    const response = await axios.put(`${API_BASE}/pipeline/configs/${name}`, {
      updates
    })
    return response.data
  },

  /**
   * 删除Pipeline配置
   */
  async deletePipelineConfig(name) {
    const response = await axios.delete(`${API_BASE}/pipeline/configs/${name}`)
    return response.data
  },

  /**
   * 导出Pipeline配置
   */
  async exportPipelineConfig(name, outputPath) {
    const response = await axios.post(`${API_BASE}/pipeline/configs/${name}/export`, {
      output_path: outputPath
    })
    return response.data
  },

  /**
   * 导入Pipeline配置
   */
  async importPipelineConfig(configPath, name = null) {
    const response = await axios.post(`${API_BASE}/pipeline/configs/import`, {
      config_path: configPath,
      name
    })
    return response.data
  },

  /**
   * 向Pipeline配置添加Processor
   */
  async addProcessorToConfig(configName, processorName, processorConfig = null) {
    const response = await axios.post(
      `${API_BASE}/pipeline/configs/${configName}/processors`,
      {
        processor_name: processorName,
        processor_config: processorConfig
      }
    )
    return response.data
  },

  /**
   * 从Pipeline配置移除Processor
   */
  async removeProcessorFromConfig(configName, processorName) {
    const response = await axios.delete(
      `${API_BASE}/pipeline/configs/${configName}/processors/${processorName}`
    )
    return response.data
  },

  /**
   * 调整Pipeline配置中Processor的顺序
   */
  async reorderProcessors(configName, processorOrder) {
    const response = await axios.put(
      `${API_BASE}/pipeline/configs/${configName}/processors/reorder`,
      {
        processor_order: processorOrder
      }
    )
    return response.data
  },

  /**
   * 使用指定配置执行Pipeline
   */
  async executePipelineWithConfig(configName, formData) {
    const response = await axios.post(
      `${API_BASE}/pipeline/configs/${configName}/execute`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    return response.data
  },

  // ==================== Processor管理 ====================
  
  /**
   * 获取所有Processor列表
   */
  async listProcessors() {
    const response = await axios.get(`${API_BASE}/processors`)
    return response.data
  },

  /**
   * 获取指定Processor详细信息
   */
  async getProcessor(name) {
    const response = await axios.get(`${API_BASE}/processors/${name}`)
    return response.data
  },

  /**
   * 保存自定义Processor
   */
  async saveProcessor({ name, code, description, entity_types }) {
    const response = await axios.post(`${API_BASE}/processors`, {
      name,
      code,
      description,
      entity_types
    })
    return response.data
  },

  /**
   * 删除Processor
   */
  async deleteProcessor(name) {
    const response = await axios.delete(`${API_BASE}/processors/${name}`)
    return response.data
  },

  /**
   * 切换Processor启用状态
   */
  async toggleProcessor(name, enabled) {
    const response = await axios.put(`${API_BASE}/processors/${name}/toggle`, {
      enabled
    })
    return response.data
  },

  /**
   * 获取Processor代码模板
   */
  async getProcessorTemplate() {
    const response = await axios.get(`${API_BASE}/processors/template`)
    return response.data
  },

  /**
   * 加载并应用Processors到Pipeline
   */
  async loadProcessors(processorNames = []) {
    const response = await axios.post(`${API_BASE}/processors/load`, {
      processors: processorNames
    })
    return response.data
  },

  // ==================== 文档处理 ====================
  
  /**
   * 处理文档，提取JSON数据
   */
  async processDocument(formData) {
    const response = await axios.post(`${API_BASE}/process-document`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  /**
   * 从JSON数据构建知识图谱
   */
  async buildGraph(jsonData) {
    const response = await axios.post(`${API_BASE}/build-graph`, {
      json_data: jsonData
    })
    return response.data
  },

  /**
   * 完整流程：文档处理 + 知识图谱构建
   */
  async processAndBuild(formData) {
    const response = await axios.post(`${API_BASE}/process-and-build`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  }
}

export default kgBuilderApi
