#!/usr/bin/env python3
"""
搜索相关API路由
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date
import logging
import json
import os
from neo4j.time import Date, DateTime, Time

from db import get_session

logger = logging.getLogger(__name__)

# 创建蓝图
search_bp = Blueprint('search', __name__)

def convert_neo4j_types(obj):
    """将Neo4j特殊类型转换为Python原生类型，以便JSON序列化"""
    if isinstance(obj, (Date, DateTime)):
        return obj.iso_format()
    elif isinstance(obj, Time):
        return str(obj)
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_neo4j_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_neo4j_types(item) for item in obj]
    else:
        return obj

# 模拟地理位置选项
location_options = [
    {
        'value': 'guangxi',
        'label': '广西壮族自治区',
        'children': [
            {
                'value': 'nanning',
                'label': '南宁市',
                'children': [
                    {'value': 'xingning', 'label': '兴宁区'},
                    {'value': 'qingxiu', 'label': '青秀区'},
                    {'value': 'jiangnan', 'label': '江南区'},
                ]
            },
            {
                'value': 'liuzhou',
                'label': '柳州市',
                'children': [
                    {'value': 'chengzhong', 'label': '城中区'},
                    {'value': 'yufeng', 'label': '鱼峰区'},
                    {'value': 'liubei', 'label': '柳北区'},
                ]
            },
            {
                'value': 'guilin',
                'label': '桂林市',
                'children': [
                    {'value': 'xiufeng', 'label': '秀峰区'},
                    {'value': 'diecai', 'label': '叠彩区'},
                    {'value': 'xiangshan', 'label': '象山区'},
                ]
            }
        ]
    }
]

# 模拟文档来源
document_sources = [
    '2016年广西水旱灾害公报',
    '2017年广西水旱灾害公报',
    '2018年广西水旱灾害公报',
    '2019年广西水旱灾害公报',
    '2020年广西水旱灾害公报',
    '2021年广西水旱灾害公报',
    '2022年广西水旱灾害公报',
    '2023年广西水旱灾害公报'
]

@search_bp.route('/entities', methods=['POST'])
def search_entities():
    """搜索实体"""
    session = None
    try:
        data = request.get_json()
        if not data:
            data = {}
        
        session = get_session()
        
        # 获取搜索参数
        keyword = data.get('keyword', '') or ''
        category = data.get('category', '') or ''
        document_source = data.get('documentSource', '') or ''
        time_range = data.get('timeRange') or []
        location = data.get('location') or []
        
        # 首先获取匹配关键词的实体ID
        entity_ids = []
        if keyword and keyword.strip():
            entity_ids_result = session.run(
                'MATCH (n) WHERE n.name CONTAINS $keyword AND (n:地点 OR n:设施 OR n:事件) RETURN n.id AS id LIMIT 100',
                {'keyword': keyword}
            )
            entity_ids = [record['id'] for record in entity_ids_result]
        
        advanced_query = data.get('advancedQuery', '') or ''
        
        # 格式化时间范围
        def format_date(date_str):
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date.strftime('%Y-%m-%d')
        
        time_range_new = {'start': '', 'end': ''}
        if time_range and len(time_range) == 2:
            print(time_range)  # 与JS版本保持一致的调试输出
            time_range_new['start'] = format_date(time_range[0])
            time_range_new['end'] = format_date(time_range[1])
        
        # 动态拼接Cypher查询
        cypher = 'MATCH (n) WHERE n:State'
        params = {}
        
        # 关键词模糊匹配（name属性）
        if keyword and keyword.strip():
            cypher += ' AND size(apoc.coll.intersection(n.entity_ids, $entityids)) > 0'
            params['entityids'] = entity_ids
        
        # 类别（节点标签或category属性）
        if category and category.strip():
            cypher += ' AND (n.id CONTAINS $category OR $category IN labels(n))'
            params['category'] = category
        
        # 来源
        if document_source and document_source.strip():
            cypher += ' AND n.source = $source'
            params['source'] = document_source
        
        # 地理位置
        if location and len(location) > 0 and location[-1] and location[-1].strip():
            cypher += ' AND (n.id CONTAINS $location)'
            params['location'] = location[-1]
        
        # 时间范围（假设有time属性，格式为yyyy-mm-dd或yyyy-mm-dd至yyyy-mm-dd）
        if time_range_new['start'] and time_range_new['end']:
            # 支持"2021-06-27至2021-07-03"格式，需判断区间重叠
            cypher += ''' AND (
        (n.time CONTAINS "至" AND apoc.date.parse(split(n.time, "至")[1], "ms", "yyyy-MM-dd") <= apoc.date.parse($endTime, "ms", "yyyy-MM-dd")
         AND apoc.date.parse(split(n.time, "至")[0], "ms", "yyyy-MM-dd") >= apoc.date.parse($startTime, "ms", "yyyy-MM-dd"))
        OR
        (NOT n.time CONTAINS "至" AND n.time >= $startTime AND n.time <= $endTime)
      )'''
            params['startTime'] = time_range_new['start']
            params['endTime'] = time_range_new['end']
        
        # 高级查询（直接拼接到WHERE后，需注意安全性）
        if advanced_query and advanced_query.strip():
            cypher += f' AND ({advanced_query})'
        
        cypher += ' RETURN n.id AS id, n.type AS name, n.time AS category, n.source AS source, properties(n) AS properties LIMIT 100'
        
        result = session.run(cypher, params)
        entities = []
        
        for record in result:
            entity = {
                'id': record['id'],
                'name': record['name'],
                'category': record['category'],
                'source': record['source'],
                'properties': convert_neo4j_types(record['properties'])
            }
            entities.append(entity)
        
        return jsonify(entities)
        
    except Exception as e:
        logger.error(f'搜索实体失败: {e}')
        return jsonify({'success': False, 'message': '搜索实体失败'}), 500
    finally:
        if session:
            session.close()

@search_bp.route('/relations/<entity_id>', methods=['GET'])
def get_entity_relations(entity_id):
    """获取实体关系"""
    try:
        # 这里应该连接到Neo4j数据库执行查询
        # 模拟返回数据
        relations = [
            {
                'source': entity_id,
                'target': 'e003',
                'type': '发生于',
                'properties': {
                    'confidence': 0.95
                }
            },
            {
                'source': 'e004',
                'target': entity_id,
                'type': '属于',
                'properties': {
                    'confidence': 0.88
                }
            }
        ]
        
        return jsonify(relations)
        
    except Exception as e:
        logger.error(f'获取实体关系失败: {e}')
        return jsonify({'success': False, 'message': '获取实体关系失败'}), 500

@search_bp.route('/export', methods=['POST'])
def export_search_results():
    """导出搜索结果"""
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        # 这里应该实现导出逻辑，例如生成CSV或Excel文件
        # 模拟返回数据
        return jsonify({
            'success': True,
            'fileUrl': '/downloads/export_123456.xlsx'
        })
        
    except Exception as e:
        logger.error(f'导出搜索结果失败: {e}')
        return jsonify({'success': False, 'message': '导出搜索结果失败'}), 500

@search_bp.route('/location-options', methods=['GET'])
def get_location_options():
    """获取地理位置选项"""
    try:
        # 这里应该从Neo4j数据库获取所有地理位置实体
        # 模拟返回数据
        locations = [
            {'id': 'l001', 'name': '广西壮族自治区'},
            {'id': 'l002', 'name': '南宁市'},
            {'id': 'l003', 'name': '柳州市'},
            {'id': 'l004', 'name': '桂林市'},
            {'id': 'l005', 'name': '梧州市'}
        ]
        
        return jsonify(locations)
        
    except Exception as e:
        logger.error(f'获取地理位置选项失败: {e}')
        return jsonify({'success': False, 'message': '获取地理位置选项失败'}), 500

@search_bp.route('/document-sources', methods=['GET'])
def get_document_sources():
    """获取文档来源列表"""
    session = None
    try:
        session = get_session()
        
        # neo4j数据库查询语句，neo4j中的节点都包含了source属性，统计所有节点中source属性
        result = session.run(
            """MATCH (n)
               WHERE n.source IS NOT NULL
               RETURN DISTINCT n.source AS name"""
        )
        
        # 先对 result.records 进行排序
        records = list(result)
        records.sort(key=lambda record: record['name'].lower())
        
        sources = [record['name'] for record in records]
        
        return jsonify(sources)
        
    except Exception as e:
        logger.error(f'获取文档来源列表失败: {e}')
        return jsonify({'success': False, 'message': '获取文档来源列表失败'}), 500
    finally:
        if session:
            session.close()