# -*- coding: utf-8 -*-
"""
工具执行器 - 执行Function Calling调用的工具
"""

import logging
from flask import jsonify
from db import get_session
from routes.graphrag import (
    get_graph_schema,
    generate_cypher_with_llm,
    execute_cypher,
    generate_answer_with_llm,
    convert_neo4j_types
)

logger = logging.getLogger(__name__)


def execute_tool(tool_name, arguments):
    """
    执行指定的工具
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数（字典）
    
    Returns:
        工具执行结果
    """
    try:
        if tool_name == "search_knowledge_graph":
            return search_knowledge_graph(**arguments)
        elif tool_name == "query_knowledge_graph_with_nl":
            return query_knowledge_graph_with_nl(**arguments)
        elif tool_name == "get_entity_relations":
            return get_entity_relations(**arguments)
        elif tool_name == "execute_cypher_query":
            return execute_cypher_query(**arguments)
        elif tool_name == "get_graph_schema":
            return get_graph_schema_tool()
        elif tool_name == "analyze_temporal_pattern":
            return analyze_temporal_pattern(**arguments)
        elif tool_name == "find_causal_chain":
            return find_causal_chain(**arguments)
        elif tool_name == "compare_entities":
            return compare_entities(**arguments)
        elif tool_name == "aggregate_statistics":
            return aggregate_statistics(**arguments)
        elif tool_name == "get_spatial_neighbors":
            return get_spatial_neighbors(**arguments)
        else:
            return {
                "success": False,
                "error": f"未知的工具: {tool_name}"
            }
    except Exception as e:
        logger.error(f"执行工具 {tool_name} 失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def search_knowledge_graph(keyword="", category="", document_source="", 
                           time_range=None, location=None, advanced_query=""):
    """
    搜索知识图谱中的实体
    
    这是对原有 /api/search/entities 接口的封装
    """
    session = None
    try:
        session = get_session()
        
        # 获取匹配关键词的实体ID
        entity_ids = []
        if keyword and keyword.strip():
            entity_ids_result = session.run(
                'MATCH (n) WHERE n.name CONTAINS $keyword AND (n:地点 OR n:设施 OR n:事件) RETURN n.id AS id LIMIT 100',
                {'keyword': keyword}
            )
            entity_ids = [record['id'] for record in entity_ids_result]
        
        # 格式化时间范围
        time_range_new = {'start': '', 'end': ''}
        if time_range and len(time_range) == 2:
            time_range_new['start'] = time_range[0]
            time_range_new['end'] = time_range[1]
        
        # 动态拼接Cypher查询
        cypher = 'MATCH (n) WHERE n:State'
        params = {}
        
        # 关键词
        if keyword and keyword.strip():
            cypher += ' AND size(apoc.coll.intersection(n.entity_ids, $entityids)) > 0'
            params['entityids'] = entity_ids
        
        # 类别
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
        
        # 时间范围
        if time_range_new['start'] and time_range_new['end']:
            cypher += ''' AND (
        (n.time CONTAINS "至" AND apoc.date.parse(split(n.time, "至")[1], "ms", "yyyy-MM-dd") <= apoc.date.parse($endTime, "ms", "yyyy-MM-dd")
         AND apoc.date.parse(split(n.time, "至")[0], "ms", "yyyy-MM-dd") >= apoc.date.parse($startTime, "ms", "yyyy-MM-dd"))
        OR
        (NOT n.time CONTAINS "至" AND n.time >= $startTime AND n.time <= $endTime)
      )'''
            params['startTime'] = time_range_new['start']
            params['endTime'] = time_range_new['end']
        
        # 高级查询
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
        
        return {
            "success": True,
            "data": {
                "entities": entities,
                "count": len(entities)
            }
        }
        
    except Exception as e:
        logger.error(f'搜索知识图谱失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if session:
            session.close()


def query_knowledge_graph_with_nl(question, history=None):
    """
    使用自然语言查询知识图谱
    
    这是对原有 /api/graphrag/query 接口的封装
    """
    try:
        if not question or not question.strip():
            return {
                "success": False,
                "error": "问题不能为空"
            }
        
        # 1. 获取图谱结构
        logger.info(f'获取图谱结构...')
        graph_schema = get_graph_schema()
        if not graph_schema:
            return {
                "success": False,
                "error": "获取图谱结构失败"
            }
        
        # 2. 生成Cypher查询
        logger.info(f'生成Cypher查询: {question}')
        cypher = generate_cypher_with_llm(question, graph_schema, history)
        if not cypher:
            return {
                "success": False,
                "error": "生成查询语句失败"
            }
        
        logger.info(f'生成的Cypher: {cypher}')
        
        # 3. 执行查询（带自动重试机制）
        max_retries = 2
        retry_count = 0
        query_records = []
        graph_data = {}
        last_error = None
        
        while retry_count <= max_retries:
            try:
                logger.info(f'执行Cypher查询 (尝试 {retry_count + 1}/{max_retries + 1})...')
                query_result = execute_cypher(cypher)
                query_records = query_result.get('records', [])
                graph_data = query_result.get('graph', {})
                logger.info(f'查询结果数量: {len(query_records)}')
                
                # 如果查到结果，直接返回
                if len(query_records) > 0:
                    break
                    
                # 如果没查到结果，尝试生成更宽泛的查询
                if retry_count < max_retries:
                    logger.warning(f'查询返回0条结果，尝试生成更宽泛的查询...')
                    broader_question = f"{question}（提示：上次查询返回0条结果，请生成更宽泛的查询，去掉State类型前缀限制，使用CONTAINS代替STARTS WITH，扩大时间范围）"
                    cypher = generate_cypher_with_llm(broader_question, graph_schema, history)
                    if not cypher:
                        break
                    logger.info(f'重试Cypher: {cypher}')
                    retry_count += 1
                else:
                    logger.warning(f'达到最大重试次数，返回空结果')
                    break
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f'执行查询失败: {e}')
                
                # 如果是语法错误，尝试让LLM修正
                if retry_count < max_retries and ('Syntax' in str(e) or 'syntax' in str(e)):
                    logger.warning(f'Cypher语法错误，尝试重新生成...')
                    error_hint = f"{question}（提示：上次查询语法错误：{str(e)}，请修正Cypher语句）"
                    cypher = generate_cypher_with_llm(error_hint, graph_schema, history)
                    if not cypher:
                        break
                    logger.info(f'修正后的Cypher: {cypher}')
                    retry_count += 1
                else:
                    return {
                        "success": False,
                        "error": f"执行查询失败: {str(e)}",
                        "cypher": cypher
                    }
        
        # 4. 生成回答
        logger.info(f'生成回答...')
        if len(query_records) == 0:
            answer = f"未查询到相关数据。可能原因：\n1. 该时间段或实体没有相关记录\n2. 数据可能使用了不同的命名或时间格式\n\n执行的查询：\n{cypher}"
        else:
            answer = generate_answer_with_llm(question, query_records, cypher, history)
        
        return {
            "success": True,
            "data": {
                "answer": answer,
                "cypher": cypher,
                "query_results": query_records[:20],
                "total_results": len(query_records),
                "graph_data": graph_data
            }
        }
        
    except Exception as e:
        logger.error(f'自然语言查询失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }


def get_entity_relations(entity_id):
    """
    获取实体的关系信息
    
    这是对原有 /api/search/relations/<entity_id> 接口的封装
    """
    session = None
    try:
        session = get_session()
        
        # 查询实体的所有关系
        cypher = """
        MATCH (n)
        WHERE n.id = $entity_id OR n.id CONTAINS $entity_id
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN n, r, m
        LIMIT 100
        """
        
        result = session.run(cypher, {'entity_id': entity_id})
        
        nodes = {}
        relationships = []
        
        for record in result:
            # 处理中心节点
            if record['n']:
                node = record['n']
                node_id = str(node.id)
                if node_id not in nodes:
                    nodes[node_id] = {
                        'id': node.id,
                        'labels': list(node.labels),
                        'properties': convert_neo4j_types(dict(node))
                    }
            
            # 处理关联节点
            if record['m']:
                node = record['m']
                node_id = str(node.id)
                if node_id not in nodes:
                    nodes[node_id] = {
                        'id': node.id,
                        'labels': list(node.labels),
                        'properties': convert_neo4j_types(dict(node))
                    }
            
            # 处理关系
            if record['r']:
                rel = record['r']
                relationships.append({
                    'id': rel.id,
                    'type': rel.type,
                    'source': str(rel.start_node.id),
                    'target': str(rel.end_node.id),
                    'properties': convert_neo4j_types(dict(rel))
                })
        
        return {
            "success": True,
            "data": {
                "nodes": list(nodes.values()),
                "relationships": relationships,
                "count": len(relationships)
            }
        }
        
    except Exception as e:
        logger.error(f'获取实体关系失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if session:
            session.close()


def execute_cypher_query(cypher):
    """
    执行Cypher查询
    
    这是对原有 /api/graphrag/cypher/execute 接口的封装
    """
    try:
        if not cypher or not cypher.strip():
            return {
                "success": False,
                "error": "Cypher语句不能为空"
            }
        
        # 安全检查
        cypher_upper = cypher.upper()
        dangerous_keywords = ['CREATE', 'DELETE', 'SET', 'REMOVE', 'MERGE', 'DROP']
        for keyword in dangerous_keywords:
            if keyword in cypher_upper:
                return {
                    "success": False,
                    "error": f"不允许执行包含{keyword}操作的查询"
                }
        
        query_result = execute_cypher(cypher)
        
        return {
            "success": True,
            "data": {
                "results": query_result.get('records', []),
                "count": len(query_result.get('records', [])),
                "graph_data": query_result.get('graph', {})
            }
        }
        
    except Exception as e:
        logger.error(f'执行Cypher查询失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }


def get_graph_schema_tool():
    """
    获取图谱结构信息
    
    这是对原有 /api/graphrag/schema 接口的封装
    """
    try:
        schema = get_graph_schema()
        if schema:
            return {
                "success": True,
                "data": schema
            }
        else:
            return {
                "success": False,
                "error": "获取图谱结构失败"
            }
    except Exception as e:
        logger.error(f'获取图谱结构失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }


def analyze_temporal_pattern(entity_name, start_date, end_date, metric=None):
    """分析时序模式"""
    session = None
    try:
        session = get_session()
        
        # 构建查询
        cypher = """
        MATCH (s:State)
        WHERE s.id CONTAINS $entity_name
          AND s.start_time >= date($start_date)
          AND s.end_time <= date($end_date)
        """
        
        if metric:
            cypher += """
            OPTIONAL MATCH (s)-[ha:hasAttribute]->(attr:Attribute)
            WHERE ha.type = $metric
            RETURN s.time AS time, s.start_time AS start, s.end_time AS end, 
                   attr.value AS value, s.type AS state_type
            ORDER BY s.start_time
            """
        else:
            cypher += """
            RETURN s.time AS time, s.start_time AS start, s.end_time AS end, 
                   s.type AS state_type, count(s) AS count
            ORDER BY s.start_time
            """
        
        params = {
            'entity_name': entity_name,
            'start_date': start_date,
            'end_date': end_date
        }
        
        if metric:
            params['metric'] = metric
        
        result = session.run(cypher, params)
        records = [convert_neo4j_types(dict(record)) for record in result]
        
        # 简单的趋势分析
        if records and metric:
            values = [float(r.get('value', 0)) for r in records if r.get('value')]
            if values:
                trend_analysis = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'trend': 'increasing' if len(values) > 1 and values[-1] > values[0] else 'decreasing'
                }
            else:
                trend_analysis = None
        else:
            trend_analysis = {'count': len(records)}
        
        return {
            "success": True,
            "data": {
                "records": records,
                "analysis": trend_analysis,
                "time_range": f"{start_date} 至 {end_date}"
            }
        }
        
    except Exception as e:
        logger.error(f'时序分析失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if session:
            session.close()


def find_causal_chain(start_event, end_event=None, max_depth=3, direction="forward"):
    """查找因果链路"""
    session = None
    try:
        session = get_session()
        
        if direction == "forward":
            rel_pattern = "-[:hasRelation*1..{max_depth}]->"
        elif direction == "backward":
            rel_pattern = "<-[:hasRelation*1..{max_depth}]-"
        else:  # both
            rel_pattern = "-[:hasRelation*1..{max_depth}]-"
        
        if end_event:
            cypher = f"""
            MATCH (start:State)
            WHERE start.id CONTAINS $start_event
            MATCH (end:State)
            WHERE end.id CONTAINS $end_event
            MATCH path = (start){rel_pattern.replace('{max_depth}', str(max_depth))}(end)
            WITH path, nodes(path) AS ns, relationships(path) AS rs
            RETURN [n IN ns | {{id: n.id, type: n.type, time: n.time}}] AS nodes,
                   [r IN rs | {{type: type(r), relation_type: r.type}}] AS relationships
            LIMIT 10
            """
            params = {'start_event': start_event, 'end_event': end_event}
        else:
            cypher = f"""
            MATCH (start:State)
            WHERE start.id CONTAINS $start_event
            MATCH path = (start){rel_pattern.replace('{max_depth}', str(max_depth))}(target:State)
            WITH path, nodes(path) AS ns, relationships(path) AS rs
            WHERE length(path) > 0
            RETURN [n IN ns | {{id: n.id, type: n.type, time: n.time}}] AS nodes,
                   [r IN rs | {{type: type(r), relation_type: r.type}}] AS relationships
            ORDER BY length(path) DESC
            LIMIT 20
            """
            params = {'start_event': start_event}
        
        result = session.run(cypher, params)
        chains = [convert_neo4j_types(dict(record)) for record in result]
        
        return {
            "success": True,
            "data": {
                "chains": chains,
                "count": len(chains),
                "direction": direction
            }
        }
        
    except Exception as e:
        logger.error(f'因果链查找失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if session:
            session.close()


def compare_entities(entity_names, time_range=None, compare_attributes=None):
    """比较多个实体"""
    session = None
    try:
        session = get_session()
        
        comparisons = {}
        
        for entity_name in entity_names:
            cypher = """
            MATCH (s:State)
            WHERE s.id CONTAINS $entity_name
            """
            
            params = {'entity_name': entity_name}
            
            if time_range and len(time_range) == 2:
                cypher += """
                AND s.start_time >= date($start_date)
                AND s.end_time <= date($end_date)
                """
                params['start_date'] = time_range[0]
                params['end_date'] = time_range[1]
            
            if compare_attributes:
                cypher += """
                OPTIONAL MATCH (s)-[ha:hasAttribute]->(attr:Attribute)
                WHERE ha.type IN $attributes
                RETURN s.id AS state_id, s.time AS time, 
                       collect({attr: ha.type, value: attr.value}) AS attributes
                LIMIT 50
                """
                params['attributes'] = compare_attributes
            else:
                cypher += """
                RETURN s.id AS state_id, s.time AS time, s.type AS state_type,
                       properties(s) AS properties
                LIMIT 50
                """
            
            result = session.run(cypher, params)
            records = [convert_neo4j_types(dict(record)) for record in result]
            comparisons[entity_name] = records
        
        return {
            "success": True,
            "data": {
                "comparisons": comparisons,
                "entity_count": len(entity_names)
            }
        }
        
    except Exception as e:
        logger.error(f'实体比较失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if session:
            session.close()


def aggregate_statistics(attribute, aggregation, entity_type=None, time_range=None, group_by=None):
    """聚合统计"""
    session = None
    try:
        session = get_session()
        
        # 构建查询
        cypher = """
        MATCH (s:State)-[ha:hasAttribute]->(attr:Attribute)
        WHERE ha.type = $attribute
        """
        
        params = {'attribute': attribute}
        
        if entity_type:
            cypher += " AND s.id CONTAINS $entity_type"
            params['entity_type'] = entity_type
        
        if time_range and len(time_range) == 2:
            cypher += """
            AND s.start_time >= date($start_date)
            AND s.end_time <= date($end_date)
            """
            params['start_date'] = time_range[0]
            params['end_date'] = time_range[1]
        
        # 聚合函数
        agg_func = {
            'sum': 'sum(toFloat(attr.value))',
            'avg': 'avg(toFloat(attr.value))',
            'max': 'max(toFloat(attr.value))',
            'min': 'min(toFloat(attr.value))',
            'count': 'count(attr.value)'
        }.get(aggregation, 'count(*)')
        
        if group_by:
            cypher += f"""
            RETURN s.{group_by} AS group_key, {agg_func} AS result
            ORDER BY result DESC
            """
        else:
            cypher += f"""
            RETURN {agg_func} AS result
            """
        
        result = session.run(cypher, params)
        records = [convert_neo4j_types(dict(record)) for record in result]
        
        return {
            "success": True,
            "data": {
                "records": records,
                "aggregation": aggregation,
                "attribute": attribute
            }
        }
        
    except Exception as e:
        logger.error(f'聚合统计失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if session:
            session.close()


def get_spatial_neighbors(entity_name, radius=1, neighbor_type=None):
    """获取空间邻近实体"""
    session = None
    try:
        session = get_session()
        
        # 构建查询
        cypher = f"""
        MATCH (center)
        WHERE center.id CONTAINS $entity_name OR center.name CONTAINS $entity_name
        MATCH path = (center)-[:locatedIn|occurredAt*1..{radius}]-(neighbor)
        """
        
        params = {'entity_name': entity_name}
        
        if neighbor_type:
            cypher += f" WHERE $neighbor_type IN labels(neighbor)"
            params['neighbor_type'] = neighbor_type
        
        cypher += """
        RETURN DISTINCT neighbor.id AS id, neighbor.name AS name, 
               labels(neighbor) AS labels, length(path) AS distance
        ORDER BY distance
        LIMIT 50
        """
        
        result = session.run(cypher, params)
        neighbors = [convert_neo4j_types(dict(record)) for record in result]
        
        return {
            "success": True,
            "data": {
                "neighbors": neighbors,
                "count": len(neighbors),
                "center": entity_name,
                "radius": radius
            }
        }
        
    except Exception as e:
        logger.error(f'空间邻近查询失败: {e}')
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        if session:
            session.close()
