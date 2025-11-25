# -*- coding: utf-8 -*-
"""
Pipeline配置管理模块
支持可视化配置从文本到图谱的完整流程
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class PipelineConfig:
    """Pipeline配置类"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化Pipeline配置
        
        Args:
            config_dir: 配置文件存储目录
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), 'configs')
        
        self.config_dir = config_dir
        os.makedirs(config_dir, exist_ok=True)
        
        # 默认配置结构
        self.default_config = {
            'name': 'default_pipeline',
            'description': '默认知识图谱构建流水线',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'stages': {
                'text_extraction': {
                    'enabled': True,
                    'name': '文本提取',
                    'description': '从文档中提取文本内容',
                    'params': {
                        'include_tables': True,
                        'include_images': False
                    }
                },
                'text_chunking': {
                    'enabled': True,
                    'name': '文本分块',
                    'description': '将文本分割成合适大小的块',
                    'params': {
                        'chunk_size': 2000,
                        'chunk_overlap': 200,
                        'chunker_type': 'word'
                    }
                },
                'llm_processing': {
                    'enabled': True,
                    'name': 'LLM处理',
                    'description': '使用大语言模型提取结构化信息',
                    'params': {
                        'temperature': 0.1,
                        'max_tokens': 4000,
                        'enable_parallel': True,
                        'max_workers': 4,
                        'prompt_template': 'default'
                    }
                },
                'data_validation': {
                    'enabled': True,
                    'name': '数据验证',
                    'description': '验证提取的结构化数据',
                    'params': {
                        'strict_mode': False,
                        'generate_report': True
                    }
                },
                'graph_building': {
                    'enabled': True,
                    'name': '图谱构建',
                    'description': '将JSON数据存储到图数据库',
                    'params': {
                        'batch_size': 100,
                        'create_indexes': True
                    }
                }
            },
            'processors': {
                'enabled_processors': [],
                'processor_configs': {}
            }
        }
        
        logger.info(f"Pipeline配置管理器初始化完成，配置目录: {config_dir}")
    
    def create_config(self, name: str, description: str = '', 
                     base_config: Dict = None) -> Dict[str, Any]:
        """
        创建新的pipeline配置
        
        Args:
            name: 配置名称
            description: 配置描述
            base_config: 基础配置（如果为None则使用默认配置）
            
        Returns:
            创建的配置字典
        """
        try:
            config = base_config if base_config else self.default_config.copy()
            config['name'] = name
            config['description'] = description
            config['created_at'] = datetime.now().isoformat()
            config['updated_at'] = datetime.now().isoformat()
            
            # 保存配置
            config_file = os.path.join(self.config_dir, f'{name}.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Pipeline配置已创建: {name}")
            return {
                'success': True,
                'config': config,
                'config_file': config_file
            }
            
        except Exception as e:
            logger.error(f"创建Pipeline配置失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_config(self, name: str) -> Optional[Dict[str, Any]]:
        """
        加载pipeline配置
        
        Args:
            name: 配置名称
            
        Returns:
            配置字典或None
        """
        try:
            config_file = os.path.join(self.config_dir, f'{name}.json')
            if not os.path.exists(config_file):
                logger.error(f"配置文件不存在: {config_file}")
                return None
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"Pipeline配置已加载: {name}")
            return config
            
        except Exception as e:
            logger.error(f"加载Pipeline配置失败: {e}")
            return None
    
    def update_config(self, name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新pipeline配置
        
        Args:
            name: 配置名称
            updates: 更新的内容
            
        Returns:
            更新结果
        """
        try:
            config = self.load_config(name)
            if not config:
                return {
                    'success': False,
                    'error': f'配置 {name} 不存在'
                }
            
            # 深度合并更新
            self._deep_merge(config, updates)
            config['updated_at'] = datetime.now().isoformat()
            
            # 保存配置
            config_file = os.path.join(self.config_dir, f'{name}.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Pipeline配置已更新: {name}")
            return {
                'success': True,
                'config': config
            }
            
        except Exception as e:
            logger.error(f"更新Pipeline配置失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_config(self, name: str) -> Dict[str, Any]:
        """
        删除pipeline配置
        
        Args:
            name: 配置名称
            
        Returns:
            删除结果
        """
        try:
            config_file = os.path.join(self.config_dir, f'{name}.json')
            if not os.path.exists(config_file):
                return {
                    'success': False,
                    'error': f'配置 {name} 不存在'
                }
            
            os.remove(config_file)
            logger.info(f"Pipeline配置已删除: {name}")
            return {
                'success': True,
                'message': f'配置 {name} 已删除'
            }
            
        except Exception as e:
            logger.error(f"删除Pipeline配置失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_configs(self) -> List[Dict[str, Any]]:
        """
        列出所有pipeline配置
        
        Returns:
            配置列表
        """
        configs = []
        
        try:
            for filename in os.listdir(self.config_dir):
                if filename.endswith('.json'):
                    name = filename[:-5]
                    config = self.load_config(name)
                    if config:
                        configs.append({
                            'name': name,
                            'description': config.get('description', ''),
                            'created_at': config.get('created_at', ''),
                            'updated_at': config.get('updated_at', ''),
                            'stages_count': len(config.get('stages', {})),
                            'processors_count': len(config.get('processors', {}).get('enabled_processors', []))
                        })
        
        except Exception as e:
            logger.error(f"列出Pipeline配置失败: {e}")
        
        return configs
    
    def add_processor_to_config(self, config_name: str, processor_name: str,
                               processor_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        向配置中添加processor
        
        Args:
            config_name: 配置名称
            processor_name: processor名称
            processor_config: processor配置参数
            
        Returns:
            操作结果
        """
        try:
            config = self.load_config(config_name)
            if not config:
                return {
                    'success': False,
                    'error': f'配置 {config_name} 不存在'
                }
            
            processors = config.get('processors', {})
            enabled_processors = processors.get('enabled_processors', [])
            processor_configs = processors.get('processor_configs', {})
            
            # 添加processor
            if processor_name not in enabled_processors:
                enabled_processors.append(processor_name)
            
            # 保存processor配置
            if processor_config:
                processor_configs[processor_name] = processor_config
            
            processors['enabled_processors'] = enabled_processors
            processors['processor_configs'] = processor_configs
            config['processors'] = processors
            
            # 保存配置
            return self.update_config(config_name, config)
            
        except Exception as e:
            logger.error(f"添加processor失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def remove_processor_from_config(self, config_name: str, 
                                    processor_name: str) -> Dict[str, Any]:
        """
        从配置中移除processor
        
        Args:
            config_name: 配置名称
            processor_name: processor名称
            
        Returns:
            操作结果
        """
        try:
            config = self.load_config(config_name)
            if not config:
                return {
                    'success': False,
                    'error': f'配置 {config_name} 不存在'
                }
            
            processors = config.get('processors', {})
            enabled_processors = processors.get('enabled_processors', [])
            processor_configs = processors.get('processor_configs', {})
            
            # 移除processor
            if processor_name in enabled_processors:
                enabled_processors.remove(processor_name)
            
            # 移除processor配置
            if processor_name in processor_configs:
                del processor_configs[processor_name]
            
            processors['enabled_processors'] = enabled_processors
            processors['processor_configs'] = processor_configs
            config['processors'] = processors
            
            # 保存配置
            return self.update_config(config_name, config)
            
        except Exception as e:
            logger.error(f"移除processor失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def reorder_processors(self, config_name: str, 
                          processor_order: List[str]) -> Dict[str, Any]:
        """
        调整processor的执行顺序
        
        Args:
            config_name: 配置名称
            processor_order: 新的processor顺序列表
            
        Returns:
            操作结果
        """
        try:
            config = self.load_config(config_name)
            if not config:
                return {
                    'success': False,
                    'error': f'配置 {config_name} 不存在'
                }
            
            processors = config.get('processors', {})
            processors['enabled_processors'] = processor_order
            config['processors'] = processors
            
            # 保存配置
            return self.update_config(config_name, config)
            
        except Exception as e:
            logger.error(f"调整processor顺序失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _deep_merge(self, base: Dict, updates: Dict) -> Dict:
        """深度合并两个字典"""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def export_config(self, name: str, output_path: str) -> Dict[str, Any]:
        """
        导出配置到指定路径
        
        Args:
            name: 配置名称
            output_path: 导出路径
            
        Returns:
            导出结果
        """
        try:
            config = self.load_config(name)
            if not config:
                return {
                    'success': False,
                    'error': f'配置 {name} 不存在'
                }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已导出: {name} -> {output_path}")
            return {
                'success': True,
                'message': f'配置已导出到 {output_path}'
            }
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def import_config(self, config_path: str, name: str = None) -> Dict[str, Any]:
        """
        从文件导入配置
        
        Args:
            config_path: 配置文件路径
            name: 新配置名称（如果为None则使用原名称）
            
        Returns:
            导入结果
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 使用新名称或原名称
            if name:
                config['name'] = name
            
            config_name = config.get('name', 'imported_config')
            
            # 保存配置
            config_file = os.path.join(self.config_dir, f'{config_name}.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已导入: {config_name}")
            return {
                'success': True,
                'config': config,
                'message': f'配置已导入: {config_name}'
            }
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
