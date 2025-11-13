# -*- coding: utf-8 -*-
"""
首页相关路由
"""

from flask import Blueprint, jsonify
import logging

from db import get_session

logger = logging.getLogger(__name__)

# 创建蓝图
home_bp = Blueprint('home', __name__)

# 模拟文档数据
documents = [
    {'id': '1', 'name': '2023年广西水旱灾害公报.docx', 'date': '2023-12-15'},
    {'id': '2', 'name': '2022年广西水旱灾害公报.docx', 'date': '2023-12-14'},
    {'id': '3', 'name': '2021年广西水旱灾害公报.docx', 'date': '2023-12-13'},
    {'id': '4', 'name': '2020年广西水旱灾害公报.docx', 'date': '2023-12-12'}
]

@home_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取知识图谱统计数据"""
    session = None
    try:
        session = get_session()
        
        # 使用OPTIONAL MATCH和统一的查询方式，避免不存在的类型导致查询失败
        node_query = """
        // 使用多个OPTIONAL MATCH语句，即使某些节点类型不存在也不会导致查询失败
        OPTIONAL MATCH (a:Attribute)
        WITH count(a) AS Attribute
        OPTIONAL MATCH (s:State)
        WITH Attribute, count(s) AS State
        OPTIONAL MATCH (e:事件)
        WITH Attribute, State, count(e) AS Event
        OPTIONAL MATCH (l:地点)
        WITH Attribute, State, Event, count(l) AS Location
        OPTIONAL MATCH (f:设施)
        RETURN Attribute, State, Event, Location, count(f) AS Facility
        """
        
        node_result = session.run(node_query)
        
        # 同样使用OPTIONAL MATCH处理可能不存在的关系类型
        relation_query = """
        OPTIONAL MATCH ()-[r:contain]->()
        WITH count(r) AS contain
        OPTIONAL MATCH ()-[r:hasAttribute]->()
        WITH contain, count(r) AS hasAttribute
        OPTIONAL MATCH ()-[r:hasRelation]->()
        WITH contain, hasAttribute, count(r) AS hasRelation
        OPTIONAL MATCH ()-[r:hasState]->()
        WITH contain, hasAttribute, hasRelation, count(r) AS hasState
        OPTIONAL MATCH ()-[r:locatedIn]->()
        WITH contain, hasAttribute, hasRelation, hasState, count(r) AS locatedIn
        OPTIONAL MATCH ()-[r:nextState]->()
        WITH contain, hasAttribute, hasRelation, hasState, locatedIn, count(r) AS nextState
        OPTIONAL MATCH ()-[r:occurredAt]->()
        RETURN contain, hasAttribute, hasRelation, hasState, locatedIn, nextState, count(r) AS occurredAt
        """
        
        relation_result = session.run(relation_query)
        # 安全地获取数据，添加默认值处理
        def get_node_count(records, key):
            try:
                if records and len(records) > 0:
                    record = records[0]
                    # 尝试通过键访问
                    if key in record.keys():
                        value = record[key]
                        return int(value) if value is not None else 0
                return 0
            except Exception as e:
                logger.error(f'获取节点计数失败 {key}: {e}')
                return 0
        
        # 获取节点统计
        node_records = list(node_result)
        node_state = {
            'Attribute': get_node_count(node_records, 'Attribute'),
            'State': get_node_count(node_records, 'State'),
            'Event': get_node_count(node_records, 'Event'),
            'Location': get_node_count(node_records, 'Location'),
            'Facility': get_node_count(node_records, 'Facility')
        }
        
        # 获取关系统计
        relation_records = list(relation_result)
        relation_state = {
            'contain': get_node_count(relation_records, 'contain'),
            'hasAttribute': get_node_count(relation_records, 'hasAttribute'),
            'hasRelation': get_node_count(relation_records, 'hasRelation'),
            'hasState': get_node_count(relation_records, 'hasState'),
            'locatedIn': get_node_count(relation_records, 'locatedIn'),
            'nextState': get_node_count(relation_records, 'nextState'),
            'occurredAt': get_node_count(relation_records, 'occurredAt')
        }
        
        # 构建响应对象
        response = {
            'nodeState': node_state,
            'relationState': relation_state
        }
        
        logger.info(f'获取知识图谱统计数据成功: {response}')
        return jsonify(response)
        
    except Exception as e:
        logger.error(f'获取知识图谱统计数据失败: {e}')
        return jsonify({
            'error': '获取知识图谱统计数据失败',
            'details': str(e)
        }), 500
    finally:
        if session:
            session.close()

@home_bp.route('/recent-documents', methods=['GET'])
def get_recent_documents():
    """获取最近处理的文档列表"""
    return jsonify(documents)

@home_bp.route('/document/<document_id>', methods=['GET'])
def get_document(document_id):
    """获取文档详情"""
    document = next((doc for doc in documents if doc['id'] == document_id), None)
    if document:
        return jsonify(document)
    else:
        return jsonify({'success': False, 'message': '文档不存在'}), 404