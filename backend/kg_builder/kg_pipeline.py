# -*- coding: utf-8 -*-
"""
知识图谱构建流水线
整合 llmjson 和 json2graph 的完整流程
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from llmjson import (
    LLMProcessor,
    ConfigManager,
    DocumentProcessor,
    DataValidator,
    WordChunker
)
from json2graph import Neo4jConnection, SKGStore

logger = logging.getLogger(__name__)


class KGPipeline:
    """知识图谱构建流水线"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
                 llm_config: Dict[str, Any]):
        """
        初始化知识图谱构建流水线
        
        Args:
            neo4j_uri: Neo4j数据库URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
            llm_config: LLM配置（包含api_key, base_url, model等）
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.llm_config = llm_config
        
        # Neo4j连接
        self.neo4j_conn = None
        self.graph_store = None
        
        # LLM处理器
        self.llm_processor = None
        self.doc_processor = None
        
        # 数据验证器
        self.validator = DataValidator()
        
        logger.info("知识图谱构建流水线初始化完成")
    
    def connect_neo4j(self):
        """连接Neo4j数据库"""
        try:
            self.neo4j_conn = Neo4jConnection(
                uri=self.neo4j_uri,
                user=self.neo4j_user,
                password=self.neo4j_password
            )
            self.neo4j_conn.connect()
            
            # 创建基础存储实例
            self.graph_store = SKGStore(self.neo4j_conn)
            
            logger.info("Neo4j连接成功")
            return True
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            return False
    
    def init_llm_processor(self):
        """初始化LLM处理器"""
        try:
            self.llm_processor = LLMProcessor(**self.llm_config)
            logger.info("LLM处理器初始化成功")
            return True
        except Exception as e:
            logger.error(f"LLM处理器初始化失败: {e}")
            return False
    
    def add_processor(self, processor):
        """
        添加自定义处理器到图存储
        
        Args:
            processor: 实现IProcessor接口的处理器实例
        """
        if self.graph_store:
            self.graph_store.add_processor(processor)
            logger.info(f"处理器 {processor.get_name()} 已添加")
        else:
            logger.error("图存储未初始化，无法添加处理器")
    
    def remove_processor(self, processor_name: str):
        """
        移除处理器
        
        Args:
            processor_name: 处理器名称
        """
        if self.graph_store:
            self.graph_store.remove_processor(processor_name)
            logger.info(f"处理器 {processor_name} 已移除")
    
    def list_processors(self) -> List[str]:
        """
        列出所有已注册的处理器
        
        Returns:
            处理器名称列表
        """
        if self.graph_store and hasattr(self.graph_store, 'processors'):
            return list(self.graph_store.processors.keys())
        return []
    
    def process_document(self, document_path: str, output_dir: str = None,
                        include_tables: bool = True,
                        validate_data: bool = True) -> Dict[str, Any]:
        """
        处理单个文档，提取JSON数据
        
        Args:
            document_path: 文档路径
            output_dir: 输出目录
            include_tables: 是否包含表格
            validate_data: 是否验证数据
            
        Returns:
            处理结果字典
        """
        try:
            # 使用临时配置文件
            temp_config = self._create_temp_config()
            
            doc_processor = DocumentProcessor(
                config_path=temp_config,
                template_file=None
            )
            
            if output_dir is None:
                output_dir = os.path.join(os.path.dirname(document_path), 'kg_output')
            
            result = doc_processor.process_single_document(
                document_path=document_path,
                base_output_dir=output_dir,
                include_tables=include_tables,
                generate_validation_report=validate_data
            )
            
            # 清理临时配置
            if os.path.exists(temp_config):
                os.remove(temp_config)
            
            return result
            
        except Exception as e:
            logger.error(f"文档处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def build_knowledge_graph(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从JSON数据构建知识图谱
        
        Args:
            json_data: 符合格式要求的JSON数据
            
        Returns:
            构建结果
        """
        try:
            if not self.graph_store:
                self.connect_neo4j()
            
            # 验证数据
            if self.validator:
                summary, report = self.validator.validate_data(json_data)
                logger.info(f"数据验证完成: {summary}")
                
                if report['error_count'] > 0:
                    logger.warning(f"发现 {report['error_count']} 个错误")
            
            # 存储到知识图谱
            self.graph_store.store_knowledge_graph(json_data)
            
            return {
                'success': True,
                'message': '知识图谱构建成功',
                'processors': self.list_processors()
            }
            
        except Exception as e:
            logger.error(f"知识图谱构建失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_and_build(self, document_path: str,
                         include_tables: bool = True,
                         validate_data: bool = True) -> Dict[str, Any]:
        """
        完整流程：文档处理 → JSON提取 → 知识图谱构建
        
        Args:
            document_path: 文档路径
            include_tables: 是否包含表格
            validate_data: 是否验证数据
            
        Returns:
            完整处理结果
        """
        result = {
            'document_processing': None,
            'graph_building': None,
            'success': False
        }
        
        try:
            # 步骤1: 处理文档
            logger.info(f"开始处理文档: {document_path}")
            doc_result = self.process_document(
                document_path=document_path,
                include_tables=include_tables,
                validate_data=validate_data
            )
            result['document_processing'] = doc_result
            
            if not doc_result.get('success'):
                return result
            
            # 步骤2: 加载生成的JSON
            output_path = doc_result.get('output_path')
            if not output_path or not os.path.exists(output_path):
                result['document_processing']['error'] = 'JSON文件未生成'
                return result
            
            with open(output_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # 步骤3: 构建知识图谱
            logger.info("开始构建知识图谱")
            graph_result = self.build_knowledge_graph(json_data)
            result['graph_building'] = graph_result
            
            result['success'] = graph_result.get('success', False)
            
            return result
            
        except Exception as e:
            logger.error(f"完整流程执行失败: {e}")
            result['error'] = str(e)
            return result
    
    def _create_temp_config(self) -> str:
        """创建临时LLM配置文件"""
        config = {
            'llm': {
                'api_key': self.llm_config.get('api_key'),
                'base_url': self.llm_config.get('base_url'),
                'model': self.llm_config.get('model', 'gpt-4o-mini'),
                'temperature': self.llm_config.get('temperature', 0.1),
                'max_tokens': self.llm_config.get('max_tokens', 4000),
            },
            'processing': {
                'chunk_size': self.llm_config.get('chunk_size', 2000),
                'chunk_overlap': self.llm_config.get('chunk_overlap', 200),
                'max_workers': self.llm_config.get('max_workers', 4),
                'enable_parallel': self.llm_config.get('enable_parallel', True)
            }
        }
        
        temp_path = os.path.join(os.path.dirname(__file__), 'temp_llm_config.json')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return temp_path
    
    def close(self):
        """关闭连接"""
        if self.neo4j_conn:
            self.neo4j_conn.close()
            logger.info("Neo4j连接已关闭")
