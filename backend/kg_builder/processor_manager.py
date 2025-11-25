# -*- coding: utf-8 -*-
"""
处理器管理模块
支持动态加载、配置、保存和执行自定义处理器
"""

import os
import json
import importlib.util
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from json2graph import IProcessor, EntityType, ProcessorResult

logger = logging.getLogger(__name__)


class ProcessorManager:
    """处理器管理器"""
    
    def __init__(self, storage_dir: str = None):
        """
        初始化处理器管理器
        
        Args:
            storage_dir: 处理器存储目录
        """
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(__file__), 'processors')
        
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        # 处理器配置文件
        self.config_file = os.path.join(storage_dir, 'processors_config.json')
        
        # 加载已保存的处理器配置
        self.processors_config = self._load_config()
        
        logger.info(f"处理器管理器初始化完成，存储目录: {storage_dir}")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载处理器配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载处理器配置失败: {e}")
        return {}
    
    def _save_config(self):
        """保存处理器配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.processors_config, f, indent=2, ensure_ascii=False)
            logger.info("处理器配置已保存")
        except Exception as e:
            logger.error(f"保存处理器配置失败: {e}")
    
    def list_processors(self) -> List[Dict[str, Any]]:
        """
        列出所有处理器
        
        Returns:
            处理器信息列表
        """
        processors = []
        
        for name, config in self.processors_config.items():
            processors.append({
                'name': name,
                'description': config.get('description', ''),
                'entity_types': config.get('entity_types', []),
                'enabled': config.get('enabled', True),
                'is_builtin': config.get('is_builtin', False),
                'code_path': config.get('code_path', '')
            })
        
        return processors
    
    def get_processor_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取处理器详细信息
        
        Args:
            name: 处理器名称
            
        Returns:
            处理器信息字典
        """
        return self.processors_config.get(name)
    
    def save_processor(self, name: str, code: str, description: str = '',
                      entity_types: List[str] = None) -> Dict[str, Any]:
        """
        保存自定义处理器代码
        
        Args:
            name: 处理器名称
            code: 处理器Python代码
            description: 处理器描述
            entity_types: 支持的实体类型列表
            
        Returns:
            保存结果
        """
        try:
            # 验证处理器代码
            validation_result = self._validate_processor_code(code)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error']
                }
            
            # 保存处理器代码
            code_path = os.path.join(self.storage_dir, f'{name}.py')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # 保存配置
            self.processors_config[name] = {
                'description': description,
                'entity_types': entity_types or ['BASE_ENTITY'],
                'enabled': True,
                'is_builtin': False,
                'code_path': code_path
            }
            self._save_config()
            
            return {
                'success': True,
                'message': f'处理器 {name} 保存成功',
                'processor': self.processors_config[name]
            }
            
        except Exception as e:
            logger.error(f"保存处理器失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_processor(self, name: str):
        """
        动态加载处理器
        
        Args:
            name: 处理器名称
            
        Returns:
            处理器实例或None
        """
        try:
            config = self.processors_config.get(name)
            if not config:
                logger.error(f"处理器 {name} 不存在")
                return None
            
            if not config.get('enabled'):
                logger.warning(f"处理器 {name} 未启用")
                return None
            
            # 内置处理器
            if config.get('is_builtin'):
                return self._load_builtin_processor(name)
            
            # 自定义处理器
            code_path = config.get('code_path')
            if not code_path or not os.path.exists(code_path):
                logger.error(f"处理器代码文件不存在: {code_path}")
                return None
            
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(name, code_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找处理器类
            processor_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, IProcessor) and 
                    attr != IProcessor):
                    processor_class = attr
                    break
            
            if not processor_class:
                logger.error(f"未找到处理器类: {name}")
                return None
            
            return processor_class()
            
        except Exception as e:
            logger.error(f"加载处理器失败: {e}")
            return None
    
    def _load_builtin_processor(self, name: str):
        """加载内置处理器"""
        try:
            if name == 'SpatialProcessor':
                from json2graph.processor import SpatialProcessor
                return SpatialProcessor()
            elif name == 'SpatialRelationshipProcessor':
                from json2graph.processor import SpatialRelationshipProcessor
                return SpatialRelationshipProcessor()
            else:
                logger.error(f"未知的内置处理器: {name}")
                return None
        except ImportError as e:
            logger.error(f"导入内置处理器失败: {e}")
            return None
    
    def delete_processor(self, name: str) -> Dict[str, Any]:
        """
        删除处理器
        
        Args:
            name: 处理器名称
            
        Returns:
            删除结果
        """
        try:
            config = self.processors_config.get(name)
            if not config:
                return {
                    'success': False,
                    'error': f'处理器 {name} 不存在'
                }
            
            if config.get('is_builtin'):
                return {
                    'success': False,
                    'error': '无法删除内置处理器'
                }
            
            # 删除代码文件
            code_path = config.get('code_path')
            if code_path and os.path.exists(code_path):
                os.remove(code_path)
            
            # 删除配置
            del self.processors_config[name]
            self._save_config()
            
            return {
                'success': True,
                'message': f'处理器 {name} 已删除'
            }
            
        except Exception as e:
            logger.error(f"删除处理器失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def toggle_processor(self, name: str, enabled: bool) -> Dict[str, Any]:
        """
        启用/禁用处理器
        
        Args:
            name: 处理器名称
            enabled: 是否启用
            
        Returns:
            操作结果
        """
        try:
            if name not in self.processors_config:
                return {
                    'success': False,
                    'error': f'处理器 {name} 不存在'
                }
            
            self.processors_config[name]['enabled'] = enabled
            self._save_config()
            
            return {
                'success': True,
                'message': f'处理器 {name} 已{"启用" if enabled else "禁用"}'
            }
            
        except Exception as e:
            logger.error(f"切换处理器状态失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_processor_code(self, name: str) -> Optional[str]:
        """
        获取处理器代码
        
        Args:
            name: 处理器名称
            
        Returns:
            处理器代码字符串
        """
        try:
            config = self.processors_config.get(name)
            if not config:
                return None
            
            code_path = config.get('code_path')
            if not code_path or not os.path.exists(code_path):
                return None
            
            with open(code_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"读取处理器代码失败: {e}")
            return None
    
    def _validate_processor_code(self, code: str) -> Dict[str, Any]:
        """
        验证处理器代码
        
        Args:
            code: 处理器代码
            
        Returns:
            验证结果
        """
        try:
            # 语法检查
            compile(code, '<string>', 'exec')
            
            # 检查必要的导入和类定义
            if 'IProcessor' not in code:
                return {
                    'valid': False,
                    'error': '处理器必须继承自 IProcessor'
                }
            
            if 'def get_name(self)' not in code:
                return {
                    'valid': False,
                    'error': '处理器必须实现 get_name() 方法'
                }
            
            if 'def process(self' not in code:
                return {
                    'valid': False,
                    'error': '处理器必须实现 process() 方法'
                }
            
            return {'valid': True}
            
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f'语法错误: {e}'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def register_builtin_processors(self):
        """注册内置处理器"""
        builtin_processors = [
            {
                'name': 'SpatialProcessor',
                'description': '处理地点实体的空间属性和地理编码',
                'entity_types': ['BASE_ENTITY'],
                'is_builtin': True
            },
            {
                'name': 'SpatialRelationshipProcessor',
                'description': '构建地点间的层级关系和地点-设施的关联关系',
                'entity_types': ['BASE_ENTITY'],
                'is_builtin': True
            }
        ]
        
        for processor in builtin_processors:
            name = processor['name']
            if name not in self.processors_config:
                self.processors_config[name] = processor
        
        self._save_config()
        logger.info("内置处理器已注册")
    
    def get_processor_template(self) -> str:
        """
        获取处理器代码模板
        
        Returns:
            处理器模板代码
        """
        return '''# -*- coding: utf-8 -*-
"""
自定义处理器模板
"""

from json2graph import IProcessor, EntityType, ProcessorResult


class CustomProcessor(IProcessor):
    """自定义处理器"""
    
    def get_name(self) -> str:
        """返回处理器名称"""
        return "custom_processor"
    
    def get_supported_entity_types(self) -> list:
        """返回支持的实体类型"""
        return [EntityType.BASE_ENTITY]
    
    def process(self, entity_type, data, context=None):
        """
        处理实体数据
        
        Args:
            entity_type: 实体类型
            data: 实体数据字典
            context: 上下文数据（前面处理器传递的）
            
        Returns:
            ProcessorResult对象
        """
        result = ProcessorResult()
        
        # 添加属性
        result.add_property("processed", True)
        result.add_property("processor", self.get_name())
        
        # 添加标签
        # result.add_label("CustomLabel")
        
        # 创建关联节点
        # result.create_node(
        #     node_type="Metadata",
        #     properties={"source": "custom"},
        #     relationship_type="HAS_METADATA"
        # )
        
        # 传递上下文给后续处理器
        result.processor_context = {
            "custom_data": "some_value"
        }
        
        return result
'''
