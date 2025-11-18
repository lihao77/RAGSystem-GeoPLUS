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
        
        # 构建详细的图谱结构说明
        schema_desc = """
## 知识图谱结构说明

### 一、节点类型与ID规范

#### 1. 基础实体节点（标签带 :entity）
   - **事件节点** (:事件:entity)
     - ID格式: `E-<行政区划码>-<日期>-<事件类型>`
     - 示例: `E-450000-20231001-TYPHOON`
     - 属性: id, name, geo_description, source
   
   - **地点节点** (:地点:entity)
     - ID格式: `L-<行政区划码>[>子区域]` 或 `L-RIVER-<名称>`
     - 示例: `L-450100`（南宁市）, `L-450103>新竹街道`, `L-RIVER-长江`
     - 属性: id, name, geo_description, admin_level
   
   - **设施节点** (:设施:entity)
     - ID格式: `F-<行政区划码>-<设施名称>`
     - 示例: `F-420500-三峡大坝`, `F-450381-潘厂水库`
     - 属性: id, name, geo_description, facility_type

#### 2. 状态节点 (:State) - **状态ID包含实体ID信息**
   - **事件状态** (ES-*)
     - ID格式: `ES-E-<事件ID>-<开始日期YYYYMMDD>_<结束日期YYYYMMDD>`
     - 示例: `ES-E-450000-20231001-TYPHOON-20231001_20231010`
     - **注意**: 状态ID中包含完整的事件ID (`E-450000-20231001-TYPHOON`)
   
   - **地点状态** (LS-*)
     - ID格式: `LS-L-<地点ID>-<开始日期>_<结束日期>`
     - 示例: `LS-L-450100-20231001_20231001`
     - **注意**: 状态ID中包含地点ID (`L-450100`)
   
   - **设施状态** (FS-*)
     - ID格式: `FS-F-<设施ID>-<开始日期>_<结束日期>`
     - 示例: `FS-F-450381-潘厂水库-20200607_20200607`
     - **注意**: 状态ID中包含设施ID (`F-450381-潘厂水库`)
   
   - **联合状态** (JS-*)
     - ID格式: `JS-<实体ID1>-<实体ID2>-...-<日期>`
     - 示例: `JS-L-450100-L-450500-20231001_20231010`
   
   - **关键属性**: id, state_type, time, start_time, end_time, entity_ids

#### 3. 属性节点 (:Attribute)
   - 存储状态的具体属性值
   - 属性: id, value

### 二、关系类型
1. **空间关系**
   - :locatedIn - 地点之间的层级关系，设施到地点的归属关系
   - :occurredAt - 事件发生在某地点

2. **状态链关系**
   - :hasState - 基础实体到其首个状态
   - :nextState - 同一实体的时间序列状态（关系属性entity记录实体ID列表）
   - :contain - 状态之间的时间包含关系

3. **因果关系**
   - :hasRelation - 状态之间的因果关系（关系属性type值为：导致、间接导致、隐含导致、触发）

4. **属性关系**
   - :hasAttribute - 状态到属性节点（关系属性type记录属性名称，如"降雨量"、"受灾人口"）

### 三、查询优化策略 - **利用ID进行高效过滤**

**核心原则：状态ID包含实体信息，可直接过滤，无需从基础实体查起！**

#### ID过滤优化规则：
1. **已知实体名称时**：优先使用状态ID的CONTAINS过滤，避免先查基础实体
   - ❌ 低效: `MATCH (e:entity {name:'潘厂水库'})-[:hasState]->(s)`
   - ✅ 高效: `MATCH (s:State) WHERE s.id CONTAINS '潘厂水库'`
   
2. **已知行政区划时**：直接用区划码过滤状态ID
   - ✅ `MATCH (s:State) WHERE s.id CONTAINS 'L-450100'` (南宁市的所有状态)
   - ✅ `MATCH (s:State) WHERE s.id STARTS WITH 'LS-L-4501'` (南宁市地点状态)

3. **已知时间范围时**：结合ID前缀和时间属性双重过滤
   - ✅ `MATCH (s:State) WHERE s.id STARTS WITH 'FS-F-450381-潘厂水库' AND s.start_time >= date('2020-01-01')`

4. **多实体查询时**：使用entity_ids数组过滤
   - ✅ `MATCH (s:State) WHERE ANY(id IN s.entity_ids WHERE id CONTAINS '潘厂水库')`

#### 何时需要从基础实体开始：
- 需要基础实体的属性（如geo_description, admin_level）
- 需要利用空间层级关系（locatedIn, occurredAt）
- 实体名称模糊，需要先确定实体ID

**重要规则：**
1. 状态节点通过hasAttribute关系连接到Attribute节点，属性名在关系的type字段，属性值在Attribute节点的value字段
2. 基础实体通过hasState关系连接到首个状态，后续状态通过nextState链接
3. 状态之间的因果关系只在State节点之间通过hasRelation建立，type属性记录关系类型
4. **优先使用状态ID过滤，只有必要时才从基础实体查起**

**查询模板（按优先级排序）：**

1. **直接通过状态ID过滤**（最高效）：
```cypher
// 查询潘厂水库2020年的状态
MATCH (s:State)
WHERE s.id CONTAINS '潘厂水库' 
  AND s.start_time >= date('2020-01-01') 
  AND s.end_time <= date('2020-12-31')
OPTIONAL MATCH (s)-[ha:hasAttribute]->(attr:Attribute)
RETURN s.id, s.time, ha.type AS attr_name, attr.value
LIMIT 50
```

2. **通过状态ID前缀+实体名过滤**：
```cypher
// 查询南宁市2023年10月的地点状态
MATCH (s:State)
WHERE s.id STARTS WITH 'LS-L-450100'  // 南宁市区划码
  AND s.time CONTAINS '2023-10'
OPTIONAL MATCH (s)-[ha:hasAttribute]->(attr:Attribute)
WHERE ha.type IN ['降雨量', '受灾人口']
RETURN s.id, s.time, ha.type, attr.value
LIMIT 50
```

3. **通过entity_ids数组过滤**：
```cypher
// 查询涉及多个实体的状态
MATCH (s:State)
WHERE ANY(eid IN s.entity_ids WHERE eid CONTAINS '潘厂水库' OR eid CONTAINS 'L-450100')
  AND s.start_time >= date('2020-01-01')
OPTIONAL MATCH (s)-[ha:hasAttribute]->(attr:Attribute)
RETURN s.id, s.entity_ids, ha.type, attr.value
LIMIT 50
```

4. **因果链查询（直接从状态开始）**：
```cypher
// 查询某设施状态导致的下游影响
MATCH (targetState:State)
WHERE targetState.id CONTAINS '潘厂水库'
  AND targetState.start_time >= date('2020-01-01')
MATCH p = (startState:State)-[:hasRelation*0..3]->(targetState)
WHERE startState.id CONTAINS 'ES-'
WITH p, nodes(p) AS ns, relationships(p) AS rs
CALL (ns) {
  WITH ns
  UNWIND ns AS n
  OPTIONAL MATCH (n)-[ha:hasAttribute]->(a:Attribute)
  RETURN collect({{id: n.id, attrs: collect({{type: ha.type, value: a.value}})}}) AS node_infos
}
RETURN node_infos, [r IN rs | {{start: startNode(r).id, end: endNode(r).id, type: type(r)}}] AS rels
LIMIT 20
```

5. **需要基础实体信息时才从实体查起**：
```cypher
// 需要实体的geo_description或admin_level等属性时
MATCH (entity:entity {name: '南宁市'})-[:hasState]->(s0:State)
OPTIONAL MATCH (s0)-[:nextState*0..]->(s:State)
WHERE s.start_time >= date('2023-10-01')
OPTIONAL MATCH (s)-[ha:hasAttribute]->(attr:Attribute)
RETURN entity.name, entity.admin_level, s.id, s.time, ha.type, attr.value
LIMIT 50
```

4. 提取完整子图（包含属性）：
**注意：Neo4j 5.x使用新的CALL语法，必须指定变量作用域**
```cypher
MATCH p = (...)...
WITH p, nodes(p) AS ns, relationships(p) AS rs
CALL (ns) {{
  WITH ns
  UNWIND ns AS n
  OPTIONAL MATCH (n)-[ha:hasAttribute]->(a:Attribute)
  WITH n, collect(DISTINCT {{type: ha.type, value: a.value}}) AS attrs
  RETURN collect({{
    id: n.id,
    label: labels(n),
    props: properties(n),
    attributes: attrs
  }}) AS node_infos
}}
WITH p, node_infos,
     [r IN rs | {{start: startNode(r).id, end: endNode(r).id, type: type(r), props: properties(r)}}] AS rel_infos
RETURN node_infos AS nodes, rel_infos AS relationships
```
"""
        
        system_prompt = """你是一个Neo4j Cypher查询专家，专门处理广西洪涝灾害知识图谱查询。

""" + schema_desc + """

## 🎯 核心原则：自适应查询策略（从宽到精）

**查询失败的根本原因：过早地限制了搜索范围！**

### ⚠️ 查询范围控制原则

**初次查询：尽可能宽泛**
- ❌ 不要过早限定State类型前缀（ES-、LS-、JS-）
- ❌ 不要过早限定具体实体ID
- ❌ 不要在WHERE中堆砌太多AND条件
- ✅ 优先用宽泛条件，通过OPTIONAL MATCH扩展数据
- ✅ 让数据库返回更多结果，由LLM后续筛选

**渐进式缩小策略（仅在初次查询结果过多时）：**
1. 第一次：只用时间范围 + 属性值模糊匹配
2. 第二次：如果结果>100条，添加地域限制
3. 第三次：如果仍>100条，限定State类型

### 📝 查询模板（按优先级）

#### 模板1：查询某时间段的统计数据（如损失、受灾人口）
```cypher
// ✅ 正确：宽泛查询所有相关State
MATCH (s:State)
WHERE s.start_time >= date('2017-07-01') 
  AND s.start_time <= date('2017-07-31')
OPTIONAL MATCH (s)-[:hasAttribute]->(attr:Attribute)
WHERE attr.value CONTAINS '亿元' 
   OR attr.value CONTAINS '万人'
   OR attr.value CONTAINS '损失'
RETURN s.id, s.state_type, s.start_time, 
       collect({attr: attr.value}) as attributes
LIMIT 100

// ❌ 错误：过早限定范围
WHERE s.id STARTS WITH 'ES-E-45'  // 只查事件状态，遗漏地点/联合状态
WHERE s.id CONTAINS 'E-450000'     // 过于具体，遗漏其他地区
```

#### 模板2：查询特定实体的情况
```cypher
// ✅ 正确：用CONTAINS宽泛匹配
MATCH (s:State)
WHERE s.id CONTAINS '潘厂水库'
  AND s.start_time >= date('2020-01-01')
OPTIONAL MATCH (s)-[:hasAttribute]->(attr:Attribute)
RETURN s, collect(attr) as attributes
LIMIT 50

// ❌ 错误：限定前缀
WHERE s.id STARTS WITH 'FS-F-450381-潘厂水库'  // 太具体
```

#### 模板3：属性值模糊搜索
```cypher
// ✅ 当不确定数据在哪里时，直接从属性反向查
MATCH (attr:Attribute)
WHERE attr.value CONTAINS '2017' 
  AND (attr.value CONTAINS '亿元' OR attr.value CONTAINS '损失')
MATCH (s:State)-[:hasAttribute]->(attr)
WHERE s.start_time >= date('2017-07-01')
  AND s.start_time <= date('2017-07-31')
RETURN s.id, s.state_type, collect(attr.value) as losses
LIMIT 100
```

## 生成要求：
1. **只返回Cypher查询语句**，不要任何解释或markdown标记
2. **第一次查询必须宽泛**，不限定State类型前缀（ES-/LS-/JS-）
3. 优先使用CONTAINS而非STARTS WITH或精确匹配
4. 时间过滤使用date()函数：`date('2020-01-01')`
5. 使用OPTIONAL MATCH扩展属性，避免漏数据
6. **CALL子查询必须使用Neo4j 5.x新语法**：`CALL (变量) {{ WITH 变量 ... }}`
7. LIMIT设为100（宽查询）或50（精确查询）
8. ⚠️ **禁止在初次查询时同时使用多个严格限制条件**
"""
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 添加对话历史（如果有）
        if conversation_history:
            for msg in conversation_history[-4:]:
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
                "max_tokens": 1500
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            cypher = result['choices'][0]['message']['content'].strip()
            
            # 清理Cypher语句（移除markdown代码块标记）
            if '```' in cypher:
                # 提取代码块中的内容
                lines = cypher.split('\n')
                in_code_block = False
                code_lines = []
                for line in lines:
                    if line.strip().startswith('```'):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block or not any(line.strip().startswith(x) for x in ['```', '#', '//']):
                        if line.strip():
                            code_lines.append(line)
                cypher = '\n'.join(code_lines).strip()
            
            # 移除可能的cypher关键字前缀
            if cypher.lower().startswith('cypher'):
                cypher = cypher[6:].strip()
                if cypher.startswith(':'):
                    cypher = cypher[1:].strip()
            
            logger.info(f'LLM生成的Cypher: {cypher}')
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
        # 1. 先限制记录数
        limited_results = query_results[:10]
        
        # 2. 简化结果结构，只保留关键信息
        simplified_results = []
        for record in limited_results:
            simplified = {}
            for key, value in record.items():
                # 跳过过大的嵌套结构
                if isinstance(value, (str, int, float, bool)) or value is None:
                    simplified[key] = value
                elif isinstance(value, list) and len(value) < 50:  # 限制列表大小
                    simplified[key] = value[:20]  # 只取前20项
                elif isinstance(value, dict) and len(str(value)) < 500:  # 限制字典大小
                    simplified[key] = value
                else:
                    simplified[key] = f"<数据过大，已省略，类型:{type(value).__name__}>"
            simplified_results.append(simplified)
        
        results_str = json.dumps(simplified_results, ensure_ascii=False)
        
        # 3. 最终长度限制
        if len(results_str) > 4000:
            results_str = results_str[:4000] + '...(结果已截断)'
        
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
                "max_tokens": 8192
            },
            timeout=90  # 增加超时时间到90秒
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            return answer
        else:
            logger.error(f'LLM API调用失败: {response.status_code} - {response.text}')
            return "抱歉，生成回答时出现错误。"
            
    except requests.exceptions.Timeout:
        logger.error(f'生成回答超时（90秒）')
        return "抱歉，生成回答时超时。查询已完成，但AI回答生成较慢，请稍后重试或查看原始查询结果。"
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
    """
    基于 Function Calling 的 GraphRAG 问答
    LLM 自主选择工具，支持多步推理和工具组合
    """
    try:
        data = request.get_json()
        user_question = data.get('question', '').strip()
        conversation_history = data.get('history', [])
        
        if not user_question:
            return jsonify({
                'success': False,
                'message': '问题不能为空'
            }), 400
        
        # 使用 Function Calling 模块处理
        logger.info(f'使用 Function Calling 处理问题: {user_question}')
        
        # 导入工具模块
        from tools.function_definitions import get_tool_definitions
        from tools.tool_executor import execute_tool
        
        # 读取 LLM 配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        llm_config = config.get('llm', {})
        api_endpoint = llm_config.get('apiEndpoint', 'https://openrouter.ai/api/v1')
        api_key = llm_config.get('apiKey', '')
        model_name = llm_config.get('modelName', 'deepseek/deepseek-chat')
        
        # 获取所有可用工具
        tools = get_tool_definitions()
        
        # 构建系统提示词
        system_prompt = """你是一个知识图谱问答助手，专门回答关于广西水旱灾害的问题。

**核心原则：循序渐进、分步推理**

⚠️ **关键图谱知识：损失数据的存储位置**
- 经济损失、受灾人口等数据**不仅仅存储在事件状态(ES-E-)中**！
- 损失数据可能分散在：
  1. **事件状态节点** (ES-E-*) - 灾害事件的整体统计
  2. **地点状态节点** (LS-L-*) - 各市县的受灾情况
  3. **联合状态节点** (JS-*) - 多个地区的汇总统计（如"南宁、北海两市总受灾52.88万人，损失3.90亿元"）
- ⚠️ 查询损失时，必须同时考虑所有State类型，不能只查事件！
- ⚠️ Cypher查询应使用 `MATCH (s:State)` 而非 `MATCH (e:Event)` 或限定ID前缀

你拥有以下工具：

📊 **基础检索工具**
1. search_knowledge_graph - 简单筛选（按关键词、时间、地点）
2. query_knowledge_graph_with_nl - 复杂自然语言查询（自动生成Cypher）
3. get_entity_relations - 探索实体关系网络
4. get_graph_schema - 了解图谱结构

🔍 **高级分析工具**
5. analyze_temporal_pattern - 时序趋势分析（统计某时间段内的变化）
6. find_causal_chain - 因果链追踪（追踪事件的前因后果）
7. compare_entities - 多实体对比
8. aggregate_statistics - 聚合统计（sum/avg/max/min）
9. get_spatial_neighbors - 空间邻近查询

**查询示例**

🔹 简单查询："2017年7月广西因灾害导致的损失有多少？"
→ query_knowledge_graph_with_nl("2017年7月广西的灾害损失统计")
  系统会自动生成宽泛查询，覆盖所有State类型，如果没结果会自动重试

🔹 因果查询："潘厂水库2020年泄洪造成了什么影响？"
→ find_causal_chain(start_event="潘厂水库", time_range=["2020-01-01", "2020-12-31"], direction="forward")
  直接追踪因果链

🔹 对比查询："比较2018和2019年南宁市的受灾情况"
→ compare_entities(entity_names=["南宁市"], time_range=["2018-01-01", "2019-12-31"], compare_attributes=["受灾人口", "经济损失"])

**工具选择指南**

| 问题类型 | 推荐工具 | 原因 |
|---------|---------|------|
| "XX的损失/影响" | 先search → 再find_causal_chain → 最后aggregate | 分步获取完整信息 |
| "XX导致了什么" | find_causal_chain(direction="forward") | 直接追踪影响 |
| "什么导致了XX" | find_causal_chain(direction="backward") | 溯源分析 |
| "XX的趋势" | analyze_temporal_pattern | 时序分析 |
| "对比A和B" | compare_entities | 多实体对比 |
| "总共/平均/最大" | aggregate_statistics | 统计汇总 |
| "XX周边/附近" | get_spatial_neighbors | 空间查询 |
| 复杂查询 | query_knowledge_graph_with_nl | 自动生成Cypher |

**智能查询策略**
1. ✅ **支持多步推理**：可以先查询基础数据，再追踪关系，最后汇总统计（2-4步）
2. ✅ **工具内置自适应**：query_knowledge_graph_with_nl 会自动扩大搜索范围，无需手动重试
3. ✅ **利用上一步结果**：基于前一个工具的结果（如实体ID、状态ID）继续深入查询
4. ⚠️ **避免无效重复**：如果某个工具返回0条，不要用相同参数再调用一次
5. ⚠️ **及时决策**：获取到足够数据后，判断是继续深入还是直接回答
6. ❌ **禁止循环**：不要连续3次调用同一个工具

**多步推理示例**：
- "2017年广西损失" → ① query_nl查事件 → ② aggregate统计 → 生成答案
- "潘厂水库影响" → ① query_nl查水库状态 → ② find_causal_chain追踪 → 生成答案

**关键：每一步要有明确目的，不是为了查询而查询！**

现在开始回答用户问题！"""

        # 构建消息
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加对话历史
        if conversation_history:
            for msg in conversation_history[-4:]:
                if msg.get('role') in ['user', 'assistant']:
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
        
        # 添加当前问题
        messages.append({"role": "user", "content": user_question})
        
        # 记录所有工具调用
        all_tool_calls = []
        max_iterations = 10  # 最多迭代5次，防止无限循环
        iteration = 0
        total_valid_results = 0  # 累积有效结果的工具调用数
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f'迭代 {iteration}: 调用 LLM')
            
            # 调用 LLM
            response = requests.post(
                f"{api_endpoint}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0.3
                },
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f'LLM API 调用失败: {response.text}')
                return jsonify({
                    'success': False,
                    'message': f'LLM API 调用失败: {response.text}'
                }), 500
            
            result = response.json()
            assistant_message = result['choices'][0]['message']
            
            # 检查是否有工具调用
            tool_calls = assistant_message.get('tool_calls', [])
            
            if not tool_calls:
                # 没有工具调用，说明 LLM 已经生成了最终答案
                final_answer = assistant_message.get('content', '')
                logger.info(f'LLM 生成最终答案（共使用 {len(all_tool_calls)} 个工具）')
                
                return jsonify({
                    'success': True,
                    'data': {
                        'answer': final_answer,
                        'tool_calls': all_tool_calls,
                        'iterations': iteration
                    }
                })
            
            # 添加助手消息到历史
            messages.append(assistant_message)
            
            # 执行所有工具调用
            logger.info(f'执行 {len(tool_calls)} 个工具调用（累计有效结果: {total_valid_results}）')
            
            current_iteration_has_result = False  # 本次迭代是否有有效结果
            
            for tool_call in tool_calls:
                tool_name = tool_call['function']['name']
                arguments = json.loads(tool_call['function']['arguments'])
                tool_call_id = tool_call['id']
                
                logger.info(f'  - 工具: {tool_name}, 参数: {json.dumps(arguments, ensure_ascii=False)[:100]}...')
                
                # 执行工具
                tool_result = execute_tool(tool_name, arguments)
                
                # 检查工具是否返回了有效数据
                tool_has_data = False
                result_count = 0
                if tool_result.get('success') and tool_result.get('data'):
                    # 检查数据是否非空
                    data = tool_result.get('data', {})
                    if isinstance(data, dict):
                        # 检查是否有实质性内容
                        if (data.get('entities') or data.get('query_results') or 
                            data.get('nodes') or data.get('records') or
                            data.get('total_results', 0) > 0):
                            tool_has_data = True
                            current_iteration_has_result = True
                            total_valid_results += 1
                            result_count = data.get('total_results', len(data.get('entities') or data.get('query_results') or data.get('nodes') or data.get('records') or []))
                    elif isinstance(data, list) and len(data) > 0:
                        tool_has_data = True
                        current_iteration_has_result = True
                        total_valid_results += 1
                        result_count = len(data)
                
                logger.info(f'    结果: {"✅ 有效" if tool_has_data else "❌ 空"} ({result_count}条记录)')
                
                # 记录工具调用
                all_tool_calls.append({
                    'name': tool_name,
                    'arguments': arguments,
                    'result': tool_result
                })
                
                # 将工具结果添加到消息历史（带提示）
                result_content = json.dumps(tool_result, ensure_ascii=False)
                
                # 根据工具执行情况添加不同的提示
                if tool_has_data:
                    # 有数据：提供信息但不限制后续调用
                    result_content += f"\n\n[系统提示] ✅ 成功获取{result_count}条记录。你可以：\n1. 如果数据足够回答问题，直接生成答案\n2. 如果需要进一步分析（如追踪因果链、统计汇总），继续调用相关工具"
                else:
                    # 无数据：根据情况给出建议
                    if total_valid_results > 0:
                        result_content += f"\n\n[系统提示] ⚠️ 此工具未返回数据，但之前已有{total_valid_results}个工具返回了有效结果。建议：\n1. 优先基于已有数据回答\n2. 如果确实需要，可以尝试不同的查询角度（但避免重复相同查询）"
                    else:
                        result_content += "\n\n[系统提示] ❌ 此工具未返回有效数据。建议：\n1. 如果尝试次数已多，直接告知用户数据不存在\n2. 如果还有其他查询角度，可以尝试一次"
                
                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call_id,
                    'name': tool_name,
                    'content': result_content
                })
            
            # 智能停止策略：区分"多步推理"和"无效重复"
            should_force_stop = False
            stop_reason = ""
            
            # 情况1: 前3次迭代完全无结果 → 可能数据不存在
            if iteration >= 3 and total_valid_results == 0:
                should_force_stop = True
                stop_reason = "前3次查询均无结果，数据可能不存在"
            
            # 情况2: 已有结果，但LLM连续2次调用相同工具 → 可能陷入循环
            elif len(all_tool_calls) >= 5 and total_valid_results > 0:
                # 检查最近3次工具调用是否重复
                recent_tools = [tc['name'] for tc in all_tool_calls[-3:]]
                if len(set(recent_tools)) <= 1:  # 连续调用同一工具
                    should_force_stop = True
                    stop_reason = f"连续调用{recent_tools[0]}工具，可能陷入循环"
            
            # 情况3: 已经调用了5个以上工具 → 防止过度查询
            elif len(all_tool_calls) >= 6:
                should_force_stop = True
                stop_reason = f"已调用{len(all_tool_calls)}个工具（含{total_valid_results}个有效），应该足够回答"
            
            if should_force_stop:
                logger.warning(f'智能停止触发: {stop_reason}')
                messages.append({
                    'role': 'user',
                    'content': f'[系统] {stop_reason}。请基于已有信息（{total_valid_results}个工具返回了数据）直接回答用户问题。不要再调用工具。'
                })
        
        # 达到最大迭代次数
        logger.warning(f'达到最大迭代次数 {max_iterations}')
        return jsonify({
            'success': False,
            'message': f'处理超时：达到最大迭代次数 {max_iterations}',
            'tool_calls': all_tool_calls
        }), 500
        
    except Exception as e:
        logger.error(f'GraphRAG查询错误: {e}')
        import traceback
        traceback.print_exc()
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
