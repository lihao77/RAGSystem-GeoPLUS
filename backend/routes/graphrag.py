# -*- coding: utf-8 -*-
"""
GraphRAG路由 - 基于知识图谱的问答系统
"""

from flask import Blueprint, request, jsonify
import logging
import json
import requests
from datetime import datetime, date, time
from db import neo4j_conn

logger = logging.getLogger(__name__)

graphrag_bp = Blueprint('graphrag', __name__)


def convert_neo4j_types(obj):
    """将Neo4j特殊类型转换为JSON可序列化的类型"""
    # 处理None
    if obj is None:
        return None
    
    # 获取对象类型名称
    type_name = type(obj).__name__
    
    # 处理Neo4j时间类型（通过类型名称判断）
    if type_name in ('DateTime', 'Date', 'Time'):
        return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
    
    # 处理Duration
    elif type_name == 'Duration':
        return str(obj)
    
    # 处理Python内置日期时间类型
    elif isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    
    # 处理字典
    elif isinstance(obj, dict):
        return {k: convert_neo4j_types(v) for k, v in obj.items()}
    
    # 处理列表
    elif isinstance(obj, list):
        return [convert_neo4j_types(item) for item in obj]
    
    # 处理元组
    elif isinstance(obj, tuple):
        return [convert_neo4j_types(item) for item in obj]
    
    # 处理集合
    elif isinstance(obj, set):
        return [convert_neo4j_types(item) for item in obj]
    
    # 其他类型尝试直接返回
    else:
        try:
            json.dumps(obj)  # 测试是否可序列化
            return obj
        except (TypeError, ValueError):
            # 不可序列化，转换为字符串
            return str(obj)


def get_graph_schema():
    """获取图谱结构信息"""
    try:
        with neo4j_conn.get_session() as session:
            # 获取所有节点标签
            labels_result = session.run("""
                CALL db.labels() YIELD label
                RETURN collect(label) as labels
            """)
            labels = labels_result.single()['labels']
            
            # 获取所有关系类型
            relationships_result = session.run("""
                CALL db.relationshipTypes() YIELD relationshipType
                RETURN collect(relationshipType) as relationships
            """)
            relationships = relationships_result.single()['relationships']
            
            # 获取节点属性示例
            node_properties = {}
            for label in labels[:5]:  # 限制查询前5个标签
                props_result = session.run(f"""
                    MATCH (n:`{label}`)
                    WITH n LIMIT 1
                    RETURN keys(n) as properties
                """)
                record = props_result.single()
                if record:
                    node_properties[label] = record['properties']
            
            # 获取关系模式
            relationship_patterns = []
            pattern_result = session.run("""
                MATCH (a)-[r]->(b)
                WITH labels(a)[0] as from_label, type(r) as rel_type, labels(b)[0] as to_label
                RETURN DISTINCT from_label, rel_type, to_label
                LIMIT 20
            """)
            for record in pattern_result:
                relationship_patterns.append({
                    'from': record['from_label'],
                    'relationship': record['rel_type'],
                    'to': record['to_label']
                })
            
            return {
                'labels': labels,
                'relationships': relationships,
                'node_properties': node_properties,
                'relationship_patterns': relationship_patterns
            }
    except Exception as e:
        logger.error(f'获取图谱结构失败: {e}')
        return None


def generate_cypher_with_llm(user_question, graph_schema, conversation_history=None):
    """使用LLM生成Cypher查询语句"""
    try:
        # 读取配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        llm_config = config.get('llm', {})
        api_endpoint = llm_config.get('apiEndpoint', 'https://openrouter.ai/api/v1')
        api_key = llm_config.get('apiKey', '')
        model_name = llm_config.get('modelName', 'deepseek/deepseek-chat')
        
        # 构建提示词
        schema_desc = f"""
知识图谱结构信息：
- 节点标签: {', '.join(graph_schema['labels'])}
- 关系类型: {', '.join(graph_schema['relationships'])}
- 节点属性示例: {json.dumps(graph_schema['node_properties'], ensure_ascii=False)}
- 关系模式示例: {json.dumps(graph_schema['relationship_patterns'], ensure_ascii=False)}
- entity-[hasState]->state, 一个entity有且仅有一个state会以此关系相连，后续关系通过nextState以及contain关系形成该entity的状态数
- 如果仅想得到一个entity的状态数需要约束nextState以及contain关系的属性entity，其值为列表，包含该entity的id
- state-[hasRelation]->state, state之间通过hasRelation关系连接，表示状态之间的关联,关系包含属性type，其值有：触发、间接导致、导致
"""
        
        system_prompt = f"""你是一个Neo4j Cypher查询专家。根据用户的问题和知识图谱结构，生成准确的Cypher查询语句。

{schema_desc}

要求：
1. 只返回Cypher查询语句，不要包含任何解释
2. 查询语句要考虑图谱的实际结构
3. 使用LIMIT限制返回结果数量（建议50条以内）
4. 对于模糊查询，使用CONTAINS或正则表达式
5. 返回的结果要包含足够的信息用于回答问题

示例：
用户问题：查找所有洪水灾害事件
Cypher: MATCH (e:事件) WHERE e.类型 CONTAINS '洪水' RETURN e LIMIT 20

用户问题：广西南宁市的灾害情况
Cypher: MATCH (l:地点)-[r]-(e:事件) WHERE l.名称 CONTAINS '南宁' RETURN l, r, e LIMIT 30
"""
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 添加对话历史（如果有）
        if conversation_history:
            for msg in conversation_history[-4:]:  # 只保留最近4轮对话
                messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
        
        messages.append({
            "role": "user",
            "content": f"用户问题：{user_question}\n\n请生成对应的Cypher查询语句："
        })
        
        # 调用LLM API
        response = requests.post(
            f"{api_endpoint}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_name,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            cypher = result['choices'][0]['message']['content'].strip()
            
            # 清理Cypher语句（移除markdown代码块标记）
            if cypher.startswith('```'):
                lines = cypher.split('\n')
                cypher = '\n'.join([line for line in lines if not line.startswith('```')])
                cypher = cypher.strip()
            
            # 移除可能的cypher关键字前缀
            if cypher.lower().startswith('cypher'):
                cypher = cypher[6:].strip()
                if cypher.startswith(':'):
                    cypher = cypher[1:].strip()
            
            return cypher
        else:
            logger.error(f'LLM API调用失败: {response.status_code} - {response.text}')
            return None
            
    except Exception as e:
        logger.error(f'生成Cypher语句失败: {e}')
        return None


def execute_cypher(cypher):
    """执行Cypher查询"""
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(cypher)
            
            # 将结果转换为JSON可序列化的格式
            records = []
            nodes_dict = {}  # 用于去重节点
            relationships = []  # 存储关系
            node_attributes = {}  # 存储节点的属性信息
            
            for record in result:
                record_dict = {}
                
                for key in record.keys():
                    value = record[key]
                    
                    # 处理路径类型
                    if hasattr(value, 'nodes') and hasattr(value, 'relationships'):
                        # 这是一个路径对象
                        path_nodes = []
                        path_rels = []
                        
                        for node in value.nodes:
                            node_id = str(node.id)
                            node_data = {
                                'id': node.id,
                                'labels': list(node.labels),
                                'properties': convert_neo4j_types(dict(node))
                            }
                            if node_id not in nodes_dict:
                                nodes_dict[node_id] = node_data
                            path_nodes.append(node_data)
                        
                        for rel in value.relationships:
                            rel_data = {
                                'id': rel.id,
                                'type': rel.type,
                                'source': str(rel.start_node.id),
                                'target': str(rel.end_node.id),
                                'properties': convert_neo4j_types(dict(rel))
                            }
                            relationships.append(rel_data)
                            path_rels.append(rel_data)
                        
                        record_dict[key] = {
                            'nodes': path_nodes,
                            'relationships': path_rels
                        }
                    
                    # 处理Neo4j节点
                    elif hasattr(value, 'labels'):
                        node_data = {
                            'id': value.id,
                            'labels': list(value.labels),
                            'properties': convert_neo4j_types(dict(value))
                        }
                        record_dict[key] = node_data
                        
                        # 收集节点用于图谱可视化
                        node_id = str(value.id)
                        if node_id not in nodes_dict:
                            nodes_dict[node_id] = node_data
                        
                    # 处理Neo4j关系
                    elif hasattr(value, 'type') and hasattr(value, 'start_node') and hasattr(value, 'end_node'):
                        # 确保起点和终点节点也被收集
                        start_id = str(value.start_node.id)
                        end_id = str(value.end_node.id)
                        
                        if start_id not in nodes_dict:
                            nodes_dict[start_id] = {
                                'id': value.start_node.id,
                                'labels': list(value.start_node.labels),
                                'properties': convert_neo4j_types(dict(value.start_node))
                            }
                        
                        if end_id not in nodes_dict:
                            nodes_dict[end_id] = {
                                'id': value.end_node.id,
                                'labels': list(value.end_node.labels),
                                'properties': convert_neo4j_types(dict(value.end_node))
                            }
                        
                        rel_data = {
                            'id': value.id,
                            'type': value.type,
                            'source': start_id,
                            'target': end_id,
                            'properties': convert_neo4j_types(dict(value))
                        }
                        record_dict[key] = rel_data
                        relationships.append(rel_data)
                    
                    # 处理列表（可能包含节点、关系或自定义对象）
                    elif isinstance(value, list):
                        converted_list = []
                        for item in value:
                            if hasattr(item, 'labels'):  # 节点
                                node_id = str(item.id)
                                node_data = {
                                    'id': item.id,
                                    'labels': list(item.labels),
                                    'properties': convert_neo4j_types(dict(item))
                                }
                                if node_id not in nodes_dict:
                                    nodes_dict[node_id] = node_data
                                converted_list.append(node_data)
                            elif hasattr(item, 'type') and hasattr(item, 'start_node'):  # 关系
                                start_id = str(item.start_node.id)
                                end_id = str(item.end_node.id)
                                rel_data = {
                                    'id': item.id,
                                    'type': item.type,
                                    'source': start_id,
                                    'target': end_id,
                                    'properties': convert_neo4j_types(dict(item))
                                }
                                relationships.append(rel_data)
                                converted_list.append(rel_data)
                            elif isinstance(item, dict):
                                # 处理自定义字典（可能包含 attributes）
                                converted_item = convert_neo4j_types(item)
                                converted_list.append(converted_item)
                                
                                # 检查是否是节点信息字典（包含 id 和 attributes）
                                if 'id' in converted_item and 'attributes' in converted_item:
                                    node_id = str(converted_item['id'])
                                    if node_id not in node_attributes:
                                        node_attributes[node_id] = []
                                    node_attributes[node_id] = converted_item['attributes']
                            else:
                                converted_list.append(convert_neo4j_types(item))
                        record_dict[key] = converted_list
                        
                    # 处理基本类型和特殊类型
                    else:
                        record_dict[key] = convert_neo4j_types(value)
                
                records.append(record_dict)
            
            # 为收集到的节点附加属性信息
            for node_id, node_data in nodes_dict.items():
                if node_id in node_attributes:
                    node_data['attributes'] = node_attributes[node_id]
            
            # 如果查询返回了自定义的 nodes 字段，也尝试整合到 nodes_dict
            for record in records:
                if 'nodes' in record and isinstance(record['nodes'], list):
                    for node_info in record['nodes']:
                        if isinstance(node_info, dict) and 'id' in node_info:
                            node_id = str(node_info['id'])
                            # 如果已有该节点，添加属性信息
                            if node_id in nodes_dict and 'attributes' in node_info:
                                nodes_dict[node_id]['attributes'] = node_info.get('attributes', [])
                            # 如果没有该节点，添加到字典
                            elif node_id not in nodes_dict:
                                nodes_dict[node_id] = {
                                    'id': node_info['id'],
                                    'labels': node_info.get('label', node_info.get('labels', [])),
                                    'properties': node_info.get('props', {}),
                                    'attributes': node_info.get('attributes', [])
                                }
                
                # 如果返回了 relationships 字段
                if 'relationships' in record and isinstance(record['relationships'], list):
                    for rel_info in record['relationships']:
                        if isinstance(rel_info, dict) and 'start' in rel_info and 'end' in rel_info:
                            # 检查是否已经在 relationships 中
                            rel_exists = any(
                                r['source'] == str(rel_info['start']) and 
                                r['target'] == str(rel_info['end']) and 
                                r['type'] == rel_info.get('type')
                                for r in relationships
                            )
                            if not rel_exists:
                                relationships.append({
                                    'id': rel_info.get('id', f"{rel_info['start']}_{rel_info['end']}"),
                                    'type': rel_info.get('type', 'RELATED'),
                                    'source': str(rel_info['start']),
                                    'target': str(rel_info['end']),
                                    'properties': rel_info.get('props', {})
                                })
            
            # 返回结果和图谱数据
            return {
                'records': records,
                'graph': {
                    'nodes': list(nodes_dict.values()),
                    'relationships': relationships
                }
            }
    except Exception as e:
        logger.error(f'执行Cypher查询失败: {e}')
        raise


def generate_answer_with_llm(user_question, query_results, cypher, conversation_history=None):
    """使用LLM基于查询结果生成回答"""
    try:
        # 读取配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        llm_config = config.get('llm', {})
        api_endpoint = llm_config.get('apiEndpoint', 'https://openrouter.ai/api/v1')
        api_key = llm_config.get('apiKey', '')
        model_name = llm_config.get('modelName', 'deepseek/deepseek-chat')
        
        # 构建提示词
        system_prompt = """你是一个知识图谱问答助手。根据用户的问题和从知识图谱中查询到的结果，生成准确、详细的回答。

要求：
1. 回答要基于查询结果，不要编造信息
2. 如果查询结果为空，礼貌地告诉用户没有找到相关信息
3. 组织好回答的结构，使用markdown格式
4. 对于数字统计，要给出具体数值
5. 如果结果很多，可以总结要点
"""
        
        # 限制查询结果大小（避免token过多）
        results_str = json.dumps(query_results[:10], ensure_ascii=False)
        if len(results_str) > 3000:
            results_str = results_str[:3000] + '...(结果已截断)'
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 添加对话历史（如果有）
        if conversation_history:
            for msg in conversation_history[-4:]:
                if msg.get('role') in ['user', 'assistant']:
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
        
        messages.append({
            "role": "user",
            "content": f"""用户问题：{user_question}

执行的Cypher查询：
```cypher
{cypher}
```

查询结果：
```json
{results_str}
```

请基于以上查询结果，生成对用户问题的回答："""
        })
        
        # 调用LLM API
        response = requests.post(
            f"{api_endpoint}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            return answer
        else:
            logger.error(f'LLM API调用失败: {response.status_code} - {response.text}')
            return "抱歉，生成回答时出现错误。"
            
    except Exception as e:
        logger.error(f'生成回答失败: {e}')
        return "抱歉，生成回答时出现错误。"


@graphrag_bp.route('/schema', methods=['GET'])
def get_schema():
    """获取图谱结构"""
    try:
        schema = get_graph_schema()
        if schema:
            return jsonify({
                'success': True,
                'data': schema
            })
        else:
            return jsonify({
                'success': False,
                'message': '获取图谱结构失败'
            }), 500
    except Exception as e:
        logger.error(f'获取图谱结构API错误: {e}')
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@graphrag_bp.route('/query', methods=['POST'])
def query():
    """处理用户问题并返回回答"""
    try:
        data = request.get_json()
        user_question = data.get('question', '').strip()
        conversation_history = data.get('history', [])
        
        if not user_question:
            return jsonify({
                'success': False,
                'message': '问题不能为空'
            }), 400
        
        # 1. 获取图谱结构
        logger.info(f'获取图谱结构...')
        graph_schema = get_graph_schema()
        if not graph_schema:
            return jsonify({
                'success': False,
                'message': '获取图谱结构失败'
            }), 500
        
        # 2. 生成Cypher查询
        logger.info(f'生成Cypher查询: {user_question}')
        # cypher = generate_cypher_with_llm(user_question, graph_schema, conversation_history)
        # if not cypher:
        #     return jsonify({
        #         'success': False,
        #         'message': '生成查询语句失败'
        #     }), 500
        
        # 临时硬编码Cypher用于测试(可用)
        cypher = '''
MATCH (target:entity)
WHERE target.id CONTAINS '潘厂水库'
WITH collect(target.id) AS target_ids

MATCH (targetState:State)
WHERE ANY(i IN targetState.entity_ids WHERE i IN target_ids)
  AND targetState.start_time >= date('2020-01-01')
  AND targetState.end_time <= date('2020-12-31')
  AND EXISTS {
    MATCH (targetState)-[ha:hasAttribute]->(a:Attribute)
    WHERE a.value =~ '.*应急.*' OR ha.type =~ '.*应急.*'
  }

MATCH p = (startState:State)-[:hasRelation*0..]->(targetState)
WHERE startState.id CONTAINS 'ES'
WITH p, nodes(p) AS ns, relationships(p) AS rs

CALL {
  WITH ns
  UNWIND ns AS n
  OPTIONAL MATCH (n)-[ha:hasAttribute]->(a:Attribute)
  WITH n, collect(DISTINCT {type: ha.type, value: a.value}) AS attrs
  RETURN collect({
    id: n.id,
    label: labels(n),
    props: properties(n),
    attributes: attrs
  }) AS node_infos
}

WITH p, node_infos,
     [r IN relationships(p) |
       {
         start: startNode(r).id,
         end: endNode(r).id,
         type: type(r),
         props: properties(r)
       }
     ] AS rel_infos

WITH collect({path: p, nodes: node_infos, rels: rel_infos}) AS paths
UNWIND paths AS p1
WITH p1, [p2 IN paths WHERE p1 <> p2 AND apoc.coll.containsAll([n IN p1.nodes | n.id], [n IN p2.nodes | n.id])] AS supersets
WHERE size(supersets) = 0

RETURN p1.nodes AS nodes, p1.rels AS relationships
        '''
        logger.info(f'生成的Cypher: {cypher}')
        
        # 3. 执行查询
        try:
            logger.info(f'执行Cypher查询...')
            query_result = execute_cypher(cypher)
            query_records = query_result.get('records', [])
            graph_data = query_result.get('graph', {})
            logger.info(f'查询结果数量: {len(query_records)}, 节点: {len(graph_data.get("nodes", []))}, 关系: {len(graph_data.get("relationships", []))}')
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'执行查询失败: {str(e)}',
                'cypher': cypher,
                'query_results': [],
                'graph_data': {'nodes': [], 'relationships': []}
            }), 500
        
        # 4. 生成回答
        logger.info(f'生成回答...')
        answer = generate_answer_with_llm(user_question, query_records, cypher, conversation_history)
        
        return jsonify({
            'success': True,
            'data': {
                'answer': answer,
                'cypher': cypher,
                'query_results': query_records[:20],  # 限制返回结果数量
                'total_results': len(query_records),
                'graph_data': graph_data  # 添加图谱数据
            }
        })
        
    except Exception as e:
        logger.error(f'GraphRAG查询错误: {e}')
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@graphrag_bp.route('/cypher/execute', methods=['POST'])
def execute_custom_cypher():
    """执行自定义Cypher查询（供高级用户使用）"""
    try:
        data = request.get_json()
        cypher = data.get('cypher', '').strip()
        
        if not cypher:
            return jsonify({
                'success': False,
                'message': 'Cypher语句不能为空'
            }), 400
        
        # 安全检查：禁止修改操作
        cypher_upper = cypher.upper()
        dangerous_keywords = ['CREATE', 'DELETE', 'SET', 'REMOVE', 'MERGE', 'DROP']
        for keyword in dangerous_keywords:
            if keyword in cypher_upper:
                return jsonify({
                    'success': False,
                    'message': f'不允许执行包含{keyword}操作的查询'
                }), 403
        
        
#         cypher = '''
# MATCH (s:State)
# WHERE s.id = 'FS-F-450381-潘厂水库-20200607_20200607'
# MATCH (s)<-[:hasRelation*0..]-(es)
# WHERE es.id contains 'ES-'
# MATCH (e:`事件`) WHERE e.id in es.entity_ids
# RETURN e.name as name, e.geo_description as geo_description
#         '''
        query_result = execute_cypher(cypher)
        
        return jsonify({
            'success': True,
            'data': {
                'results': query_result.get('records', []),
                'count': len(query_result.get('records', [])),
                'graph_data': query_result.get('graph', {})
            }
        })
        
    except Exception as e:
        logger.error(f'执行自定义Cypher错误: {e}')
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
