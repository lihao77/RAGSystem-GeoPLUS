# -*- coding: utf-8 -*-
"""
系统设置工具函数
"""

import os
import json
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), '../config.json')

def load_system_settings():
    """
    从配置文件或环境变量加载系统设置
    """
    try:
        # 尝试从配置文件读取
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                logger.info('从配置文件加载设置成功')
                return config_data
    except Exception as e:
        logger.error(f'读取配置文件失败: {e}')
    
    # 如果配置文件不存在或读取失败，使用环境变量或默认值
    default_config = {
        'neo4j': {
            'uri': os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            'user': os.getenv('NEO4J_USER', 'neo4j'),
            'password': os.getenv('NEO4J_PASSWORD', 'admin123456')
        },
        'llm': {
            'apiEndpoint': os.getenv('LLM_API_ENDPOINT', 'https://openrouter.ai/api/v1'),
            'apiKey': os.getenv('LLM_API_KEY', ''),
            'modelName': os.getenv('LLM_MODEL_NAME', 'tngtech/deepseek-r1t-chimera:free')
        },
        'geocoding': {
            'service': os.getenv('GEOCODING_SERVICE', 'baidu'),
            'apiKey': os.getenv('GEOCODING_API_KEY', '')
        },
        'system': {
            'maxWorkers': int(os.getenv('MAX_WORKERS', '4'))
        }
    }
    
    logger.info('使用默认配置')
    return default_config

def save_system_settings(settings):
    """
    保存系统设置到配置文件
    """
    try:
        # 确保配置目录存在
        config_dir = os.path.dirname(CONFIG_FILE_PATH)
        os.makedirs(config_dir, exist_ok=True)
        
        # 写入配置文件
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        logger.info('配置文件保存成功')
        return True
    except Exception as e:
        logger.error(f'保存配置文件失败: {e}')
        return False

def check_config_complete(settings):
    """
    检查配置是否完整
    """
    missing_configs = []

    if not settings.get('llm', {}).get('apiKey'):
        missing_configs.append('LLM API密钥')

    if not settings.get('geocoding', {}).get('apiKey'):
        missing_configs.append('地理编码API密钥')

    neo4j_config = settings.get('neo4j', {})
    if not all([neo4j_config.get('uri'), neo4j_config.get('user'), neo4j_config.get('password')]):
        missing_configs.append('Neo4j数据库连接信息')

    return {
        'isComplete': len(missing_configs) == 0,
        'missingConfigs': missing_configs
    }