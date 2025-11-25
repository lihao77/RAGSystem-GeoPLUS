# -*- coding: utf-8 -*-
"""
知识图谱构建路由
支持文档处理、知识图谱构建、处理器管理等功能
"""

from flask import Blueprint, request, jsonify
import os
import json
import logging
from werkzeug.utils import secure_filename

from kg_builder import KGPipeline, ProcessorManager
from kg_builder.pipeline_config import PipelineConfig

logger = logging.getLogger(__name__)

kg_builder_bp = Blueprint('kg_builder', __name__)

# 全局实例
pipeline = None
processor_manager = None
pipeline_config_manager = None


def init_pipeline(config: dict):
    """初始化知识图谱构建流水线"""
    global pipeline, processor_manager, pipeline_config_manager
    
    try:
        # 初始化流水线
        pipeline = KGPipeline(
            neo4j_uri=config['neo4j']['uri'],
            neo4j_user=config['neo4j']['user'],
            neo4j_password=config['neo4j']['password'],
            llm_config={
                'api_key': config['llm']['apiKey'],
                'base_url': config['llm']['apiEndpoint'],
                'model': config['llm']['modelName'],
                'temperature': 0.1,
                'max_tokens': 4000,
                'chunk_size': 2000,
                'chunk_overlap': 200,
                'max_workers': config['system'].get('maxWorkers', 4),
                'enable_parallel': True
            }
        )
        
        # 连接Neo4j
        pipeline.connect_neo4j()
        
        # 初始化LLM处理器
        pipeline.init_llm_processor()
        
        # 初始化处理器管理器
        processor_manager = ProcessorManager()
        processor_manager.register_builtin_processors()
        
        # 初始化pipeline配置管理器
        pipeline_config_manager = PipelineConfig()
        
        logger.info("知识图谱构建模块初始化成功")
        return True
        
    except Exception as e:
        logger.error(f"知识图谱构建模块初始化失败: {e}")
        return False


@kg_builder_bp.route('/status', methods=['GET'])
def get_status():
    """获取知识图谱构建模块状态"""
    try:
        return jsonify({
            'success': True,
            'initialized': pipeline is not None,
            'neo4j_connected': pipeline.neo4j_conn is not None if pipeline else False,
            'llm_initialized': pipeline.llm_processor is not None if pipeline else False
        })
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/init', methods=['POST'])
def init_module():
    """初始化知识图谱构建模块"""
    try:
        data = request.get_json()
        config = data.get('config')
        
        if not config:
            return jsonify({'success': False, 'error': '缺少配置信息'})
        
        success = init_pipeline(config)
        
        return jsonify({
            'success': success,
            'message': '初始化成功' if success else '初始化失败'
        })
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/process-document', methods=['POST'])
def process_document():
    """处理文档，提取JSON数据"""
    try:
        if not pipeline:
            return jsonify({'success': False, 'error': '模块未初始化'})
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '未上传文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'})
        
        # 保存文件
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'kg_documents')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # 获取参数
        include_tables = request.form.get('include_tables', 'true').lower() == 'true'
        validate_data = request.form.get('validate_data', 'true').lower() == 'true'
        
        # 处理文档
        result = pipeline.process_document(
            document_path=file_path,
            include_tables=include_tables,
            validate_data=validate_data
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"文档处理失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/build-graph', methods=['POST'])
def build_graph():
    """从JSON数据构建知识图谱"""
    try:
        if not pipeline:
            return jsonify({'success': False, 'error': '模块未初始化'})
        
        data = request.get_json()
        json_data = data.get('json_data')
        
        if not json_data:
            return jsonify({'success': False, 'error': '缺少JSON数据'})
        
        result = pipeline.build_knowledge_graph(json_data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"知识图谱构建失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/process-and-build', methods=['POST'])
def process_and_build():
    """完整流程：文档处理 + 知识图谱构建"""
    try:
        if not pipeline:
            return jsonify({'success': False, 'error': '模块未初始化'})
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '未上传文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'})
        
        # 保存文件
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'kg_documents')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # 获取参数
        include_tables = request.form.get('include_tables', 'true').lower() == 'true'
        validate_data = request.form.get('validate_data', 'true').lower() == 'true'
        
        # 执行完整流程
        result = pipeline.process_and_build(
            document_path=file_path,
            include_tables=include_tables,
            validate_data=validate_data
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"完整流程执行失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ==================== 处理器管理接口 ====================

@kg_builder_bp.route('/processors', methods=['GET'])
def list_processors():
    """获取所有处理器列表"""
    try:
        if not processor_manager:
            return jsonify({'success': False, 'error': '处理器管理器未初始化'})
        
        processors = processor_manager.list_processors()
        
        return jsonify({
            'success': True,
            'processors': processors
        })
        
    except Exception as e:
        logger.error(f"获取处理器列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/processors/<name>', methods=['GET'])
def get_processor(name):
    """获取处理器详细信息"""
    try:
        if not processor_manager:
            return jsonify({'success': False, 'error': '处理器管理器未初始化'})
        
        info = processor_manager.get_processor_info(name)
        
        if not info:
            return jsonify({'success': False, 'error': f'处理器 {name} 不存在'})
        
        # 获取代码
        code = processor_manager.get_processor_code(name)
        
        return jsonify({
            'success': True,
            'processor': {
                **info,
                'code': code
            }
        })
        
    except Exception as e:
        logger.error(f"获取处理器信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/processors', methods=['POST'])
def save_processor():
    """保存自定义处理器"""
    try:
        if not processor_manager:
            return jsonify({'success': False, 'error': '处理器管理器未初始化'})
        
        data = request.get_json()
        name = data.get('name')
        code = data.get('code')
        description = data.get('description', '')
        entity_types = data.get('entity_types', ['BASE_ENTITY'])
        
        if not name or not code:
            return jsonify({'success': False, 'error': '缺少必要参数'})
        
        result = processor_manager.save_processor(
            name=name,
            code=code,
            description=description,
            entity_types=entity_types
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"保存处理器失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/processors/<name>', methods=['DELETE'])
def delete_processor(name):
    """删除处理器"""
    try:
        if not processor_manager:
            return jsonify({'success': False, 'error': '处理器管理器未初始化'})
        
        result = processor_manager.delete_processor(name)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"删除处理器失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/processors/<name>/toggle', methods=['PUT'])
def toggle_processor(name):
    """启用/禁用处理器"""
    try:
        if not processor_manager:
            return jsonify({'success': False, 'error': '处理器管理器未初始化'})
        
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        result = processor_manager.toggle_processor(name, enabled)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"切换处理器状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/processors/template', methods=['GET'])
def get_processor_template():
    """获取处理器代码模板"""
    try:
        if not processor_manager:
            return jsonify({'success': False, 'error': '处理器管理器未初始化'})
        
        template = processor_manager.get_processor_template()
        
        return jsonify({
            'success': True,
            'template': template
        })
        
    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/processors/load', methods=['POST'])
def load_processors():
    """加载并应用处理器到流水线"""
    try:
        if not pipeline or not processor_manager:
            return jsonify({'success': False, 'error': '模块未初始化'})
        
        data = request.get_json()
        processor_names = data.get('processors', [])
        
        if not processor_names:
            # 加载所有启用的处理器
            all_processors = processor_manager.list_processors()
            processor_names = [p['name'] for p in all_processors if p['enabled']]
        
        loaded = []
        failed = []
        
        for name in processor_names:
            processor = processor_manager.load_processor(name)
            if processor:
                pipeline.add_processor(processor)
                loaded.append(name)
            else:
                failed.append(name)
        
        return jsonify({
            'success': True,
            'loaded': loaded,
            'failed': failed,
            'message': f'成功加载 {len(loaded)} 个处理器'
        })
        
    except Exception as e:
        logger.error(f"加载处理器失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ==================== Pipeline配置管理接口 ====================

@kg_builder_bp.route('/pipeline/configs', methods=['GET'])
def list_pipeline_configs():
    """获取所有pipeline配置列表"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        configs = pipeline_config_manager.list_configs()
        
        return jsonify({
            'success': True,
            'configs': configs
        })
        
    except Exception as e:
        logger.error(f"获取pipeline配置列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs', methods=['POST'])
def create_pipeline_config():
    """创建新的pipeline配置"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        base_config = data.get('base_config')
        
        if not name:
            return jsonify({'success': False, 'error': '缺少配置名称'})
        
        result = pipeline_config_manager.create_config(name, description, base_config)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"创建pipeline配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs/<name>', methods=['GET'])
def get_pipeline_config(name):
    """获取指定pipeline配置"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        config = pipeline_config_manager.load_config(name)
        
        if not config:
            return jsonify({'success': False, 'error': f'配置 {name} 不存在'})
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        logger.error(f"获取pipeline配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs/<name>', methods=['PUT'])
def update_pipeline_config(name):
    """更新pipeline配置"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        data = request.get_json()
        updates = data.get('updates')
        
        if not updates:
            return jsonify({'success': False, 'error': '缺少更新内容'})
        
        result = pipeline_config_manager.update_config(name, updates)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"更新pipeline配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs/<name>', methods=['DELETE'])
def delete_pipeline_config(name):
    """删除pipeline配置"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        result = pipeline_config_manager.delete_config(name)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"删除pipeline配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs/<config_name>/processors', methods=['POST'])
def add_processor_to_pipeline_config(config_name):
    """向pipeline配置添加processor"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        data = request.get_json()
        processor_name = data.get('processor_name')
        processor_config = data.get('processor_config')
        
        if not processor_name:
            return jsonify({'success': False, 'error': '缺少processor名称'})
        
        result = pipeline_config_manager.add_processor_to_config(
            config_name, processor_name, processor_config
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"添加processor失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs/<config_name>/processors/<processor_name>', methods=['DELETE'])
def remove_processor_from_pipeline_config(config_name, processor_name):
    """从pipeline配置移除processor"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        result = pipeline_config_manager.remove_processor_from_config(
            config_name, processor_name
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"移除processor失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs/<config_name>/processors/reorder', methods=['PUT'])
def reorder_processors_in_config(config_name):
    """调整pipeline配置中processor的顺序"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        data = request.get_json()
        processor_order = data.get('processor_order')
        
        if not processor_order:
            return jsonify({'success': False, 'error': '缺少processor顺序列表'})
        
        result = pipeline_config_manager.reorder_processors(
            config_name, processor_order
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"调整processor顺序失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs/<name>/export', methods=['POST'])
def export_pipeline_config(name):
    """导出pipeline配置"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        data = request.get_json()
        output_path = data.get('output_path')
        
        if not output_path:
            return jsonify({'success': False, 'error': '缺少输出路径'})
        
        result = pipeline_config_manager.export_config(name, output_path)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"导出pipeline配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs/import', methods=['POST'])
def import_pipeline_config():
    """导入pipeline配置"""
    try:
        if not pipeline_config_manager:
            return jsonify({'success': False, 'error': 'Pipeline配置管理器未初始化'})
        
        data = request.get_json()
        config_path = data.get('config_path')
        name = data.get('name')
        
        if not config_path:
            return jsonify({'success': False, 'error': '缺少配置文件路径'})
        
        result = pipeline_config_manager.import_config(config_path, name)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"导入pipeline配置失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@kg_builder_bp.route('/pipeline/configs/<config_name>/execute', methods=['POST'])
def execute_pipeline_with_config(config_name):
    """使用指定配置执行pipeline"""
    try:
        if not pipeline or not pipeline_config_manager:
            return jsonify({'success': False, 'error': '模块未初始化'})
        
        # 加载配置
        config = pipeline_config_manager.load_config(config_name)
        if not config:
            return jsonify({'success': False, 'error': f'配置 {config_name} 不存在'})
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '未上传文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'})
        
        # 保存文件
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'kg_documents')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # 应用配置中的processors
        enabled_processors = config.get('processors', {}).get('enabled_processors', [])
        for proc_name in enabled_processors:
            processor = processor_manager.load_processor(proc_name)
            if processor:
                pipeline.add_processor(processor)
        
        # 获取配置参数
        stages = config.get('stages', {})
        text_extraction = stages.get('text_extraction', {}).get('params', {})
        graph_building = stages.get('graph_building', {}).get('params', {})
        
        include_tables = text_extraction.get('include_tables', True)
        validate_data = stages.get('data_validation', {}).get('enabled', True)
        
        # 执行完整流程
        result = pipeline.process_and_build(
            document_path=file_path,
            include_tables=include_tables,
            validate_data=validate_data
        )
        
        result['config_used'] = config_name
        result['processors_used'] = enabled_processors
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"执行pipeline失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
