# -*- coding: utf-8 -*-
"""
系统设置相关路由
"""

from flask import Blueprint, request, jsonify
import requests
from neo4j import GraphDatabase
import logging

from utils.settings import load_system_settings, save_system_settings, check_config_complete

logger = logging.getLogger(__name__)

# 创建蓝图
settings_bp = Blueprint('settings', __name__)

# 加载系统设置
system_settings = load_system_settings()

@settings_bp.route('', methods=['GET'])
@settings_bp.route('/', methods=['GET'])
def get_settings():
    """获取系统配置"""
    return jsonify(system_settings)

@settings_bp.route('', methods=['POST', 'OPTIONS'])
@settings_bp.route('/', methods=['POST', 'OPTIONS'])
def save_settings():
    """保存系统配置"""
    if request.method == 'OPTIONS':
        # 处理预检请求
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    global system_settings
    try:
        system_settings = request.get_json()
        saved = save_system_settings(system_settings)
        if saved:
            return jsonify({'success': True, 'message': '配置已保存'})
        else:
            return jsonify({'success': False, 'message': '保存配置失败'}), 500
    except Exception as e:
        logger.error(f'保存系统配置失败: {e}')
        return jsonify({'success': False, 'message': f'保存配置失败: {str(e)}'}), 500

@settings_bp.route('/test-neo4j', methods=['POST'])
def test_neo4j():
    """测试Neo4j连接"""
    config = request.get_json()
    test_driver = None
    
    try:
        # 创建临时驱动实例进行测试
        test_driver = GraphDatabase.driver(
            config['uri'],
            auth=(config['user'], config['password']),
            max_connection_lifetime=3000  # 设置较短的连接超时时间
        )
        
        # 测试连接
        with test_driver.session() as session:
            result = session.run('RETURN 1 as n')
            record = result.single()
            
        return jsonify({
            'success': True,
            'message': '连接成功'
        })
    except Exception as e:
        logger.error(f'Neo4j连接测试失败: {e}')
        return jsonify({
            'success': False,
            'message': f'连接失败: {str(e)}'
        })
    finally:
        # 关闭测试驱动
        if test_driver:
            try:
                test_driver.close()
            except Exception as e:
                logger.error(f'关闭Neo4j测试连接失败: {e}')

@settings_bp.route('/test-llm', methods=['POST'])
def test_llm():
    """测试LLM服务连接"""
    config = request.get_json()
    
    try:
        # 验证API密钥格式
        if not config.get('apiKey') or not config['apiKey'].startswith('sk-'):
            return jsonify({
                'success': False,
                'message': '连接失败: API密钥格式不正确'
            })
        
        # 验证API端点
        if not config.get('apiEndpoint'):
            return jsonify({
                'success': False,
                'message': '连接失败: 缺少API端点URL'
            })
        
        # 尝试发送简单请求到LLM服务
        response = requests.post(
            f"{config['apiEndpoint']}/chat/completions",
            json={
                'model': config['modelName'],
                'messages': [{'role': 'user', 'content': 'Hello'}],
                'max_tokens': 5
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {config['apiKey']}"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': '连接成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'连接失败: 服务返回状态码 {response.status_code}'
            })
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'message': '连接失败: 请求超时'
        })
    except requests.exceptions.RequestException as e:
        logger.error(f'LLM服务连接测试失败: {e}')
        return jsonify({
            'success': False,
            'message': f'连接失败: {getattr(e.response, "json", lambda: {"error": {"message": str(e)}})().get("error", {}).get("message", str(e)) if hasattr(e, "response") and e.response else str(e)}'
        })
    except Exception as e:
        logger.error(f'LLM服务连接测试失败: {e}')
        return jsonify({
            'success': False,
            'message': f'连接失败: {str(e)}'
        })

@settings_bp.route('/test-geocoding', methods=['POST'])
def test_geocoding():
    """测试地理编码服务连接"""
    config = request.get_json()
    
    try:
        if not config.get('apiKey'):
            return jsonify({
                'success': False,
                'message': '连接失败: 缺少API密钥'
            })
        
        service = config.get('service')
        if service == 'baidu':
            # 百度地图API测试
            url = f"http://api.map.baidu.com/geocoding/v3/?address=北京市&output=json&ak={config['apiKey']}"
        elif service == 'amap':
            # 高德地图API测试
            url = f"https://restapi.amap.com/v3/geocode/geo?address=北京市&key={config['apiKey']}"
        else:
            return jsonify({
                'success': False,
                'message': f'连接失败: 不支持的地理编码服务 {service}'
            })
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': '连接成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'连接失败: 服务返回状态码 {response.status_code}'
            })
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'message': '连接失败: 请求超时'
        })
    except requests.exceptions.RequestException as e:
        logger.error(f'地理编码服务连接测试失败: {e}')
        return jsonify({
            'success': False,
            'message': f'连接失败: {getattr(e.response, "json", lambda: {"message": str(e)})().get("message", str(e)) if hasattr(e, "response") and e.response else str(e)}'
        })
    except Exception as e:
        logger.error(f'地理编码服务连接测试失败: {e}')
        return jsonify({
            'success': False,
            'message': f'连接失败: {str(e)}'
        })