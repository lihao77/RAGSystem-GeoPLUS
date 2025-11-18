# -*- coding: utf-8 -*-
"""
Function Calling 工具定义
用于LLM直接调用知识图谱检索功能
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_knowledge_graph_with_nl",
            "description": "使用自然语言查询知识图谱。系统会自动将自然语言问题转换为Cypher查询，执行并返回结构化结果。这是最强大的工具，适用于复杂的关联查询、因果分析、时序分析等场景。推荐优先使用此工具。\n\n⚠️重要：损失数据可能存储在事件状态(ES-E-)、地点状态(LS-L-)或联合状态(JS-)中，查询时需要覆盖所有State类型！",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "自然语言问题，例如：'潘厂水库在2020年6月7日的情况'、'南宁市2023年的洪涝灾害导致了什么影响'"
                    },
                    "history": {
                        "type": "array",
                        "description": "对话历史，用于上下文理解。每个元素包含role和content",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["user", "assistant"]
                                },
                                "content": {
                                    "type": "string"
                                }
                            }
                        }
                    }
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_graph",
            "description": "搜索知识图谱中的实体、事件和状态信息。支持关键词、类别、时间范围、地理位置等多维度检索。适用于简单的筛选和查找任务。\n\n⚠️重要：查询损失数据时，不要只查'事件'类别！损失信息可能在State节点中（包括事件状态、地点状态、联合状态）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，用于模糊匹配实体名称，例如：'潘厂水库'、'南宁市'、'洪涝'"
                    },
                    "category": {
                        "type": "string",
                        "description": "实体类别，可选值：'地点'、'设施'、'事件'、'State'（状态节点）",
                        "enum": ["地点", "设施", "事件", "State", ""]
                    },
                    "document_source": {
                        "type": "string",
                        "description": "文档来源，例如：'2023年广西水旱灾害公报'、'2020年广西水旱灾害公报'"
                    },
                    "time_range": {
                        "type": "array",
                        "description": "时间范围，格式为 [开始时间, 结束时间]，例如：['2023-01-01', '2023-12-31']",
                        "items": {
                            "type": "string",
                            "format": "date"
                        },
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "location": {
                        "type": "array",
                        "description": "地理位置层级，例如：['guangxi', 'nanning', 'qingxiu'] 表示广西>南宁>青秀区",
                        "items": {
                            "type": "string"
                        }
                    },
                    "advanced_query": {
                        "type": "string",
                        "description": "高级查询条件，使用Cypher WHERE子句语法，例如：'n.type = \"洪涝\"'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_relations",
            "description": "获取指定实体的关系信息，包括该实体的所有连接关系、关联实体等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "实体ID，例如：'L-450100'（南宁市）、'F-450381-潘厂水库'"
                    }
                },
                "required": ["entity_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_cypher_query",
            "description": "直接执行Cypher查询语句。仅限只读查询（MATCH、RETURN等），不允许修改操作。适用于需要精确控制查询逻辑的高级场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "cypher": {
                        "type": "string",
                        "description": "Cypher查询语句，例如：'MATCH (n:State) WHERE n.id CONTAINS \"潘厂水库\" RETURN n LIMIT 10'"
                    }
                },
                "required": ["cypher"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_graph_schema",
            "description": "获取知识图谱的结构信息，包括节点类型、关系类型、属性等元数据。用于了解图谱的整体结构。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_temporal_pattern",
            "description": "分析时序模式和趋势。统计指定时间范围内的事件频率、强度变化等。适用于趋势分析、周期性分析等场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "实体名称，例如：'潘厂水库'、'南宁市'"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "开始日期，格式：YYYY-MM-DD"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期，格式：YYYY-MM-DD"
                    },
                    "metric": {
                        "type": "string",
                        "description": "分析指标，例如：'降雨量'、'受灾人口'、'经济损失'",
                    }
                },
                "required": ["entity_name", "start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_causal_chain",
            "description": "查找因果链路。追踪事件的前因后果，分析影响传播路径。适用于影响分析、溯源分析等场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_event": {
                        "type": "string",
                        "description": "起始事件或实体名称"
                    },
                    "end_event": {
                        "type": "string",
                        "description": "目标事件或实体名称（可选）"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "最大追踪深度，默认为3",
                        "default": 3
                    },
                    "direction": {
                        "type": "string",
                        "description": "追踪方向：'forward'（向前追踪影响）、'backward'（向后追溯原因）、'both'（双向）",
                        "enum": ["forward", "backward", "both"],
                        "default": "forward"
                    }
                },
                "required": ["start_event"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_entities",
            "description": "比较多个实体的状态和属性。适用于对比分析、异同点识别等场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_names": {
                        "type": "array",
                        "description": "要比较的实体名称列表",
                        "items": {
                            "type": "string"
                        },
                        "minItems": 2
                    },
                    "time_range": {
                        "type": "array",
                        "description": "时间范围 [开始日期, 结束日期]",
                        "items": {
                            "type": "string"
                        },
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "compare_attributes": {
                        "type": "array",
                        "description": "要比较的属性列表，例如：['降雨量', '受灾人口']",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["entity_names"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate_statistics",
            "description": "聚合统计分析。计算总和、平均值、最大值、最小值等统计指标。适用于数据汇总、统计分析等场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "实体类型：'地点'、'设施'、'事件'",
                        "enum": ["地点", "设施", "事件"]
                    },
                    "attribute": {
                        "type": "string",
                        "description": "要统计的属性，例如：'降雨量'、'受灾人口'"
                    },
                    "aggregation": {
                        "type": "string",
                        "description": "聚合方式：sum（总和）、avg（平均）、max（最大）、min（最小）、count（计数）",
                        "enum": ["sum", "avg", "max", "min", "count"]
                    },
                    "time_range": {
                        "type": "array",
                        "description": "时间范围 [开始日期, 结束日期]",
                        "items": {
                            "type": "string"
                        }
                    },
                    "group_by": {
                        "type": "string",
                        "description": "分组字段，例如：'source'（按来源分组）、'time'（按时间分组）"
                    }
                },
                "required": ["attribute", "aggregation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_spatial_neighbors",
            "description": "获取空间邻近实体。查找指定实体周边的地理位置、设施等。适用于空间关系分析、影响范围评估等场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "中心实体名称"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "邻近层级，1表示直接相邻，2表示二级邻居，以此类推",
                        "default": 1
                    },
                    "neighbor_type": {
                        "type": "string",
                        "description": "邻居类型过滤：'地点'、'设施'、'事件'，不指定则返回所有类型"
                    }
                },
                "required": ["entity_name"]
            }
        }
    }
]


def get_tool_definitions():
    """获取所有工具定义"""
    return TOOLS


def get_tool_by_name(name):
    """根据名称获取工具定义"""
    for tool in TOOLS:
        if tool["function"]["name"] == name:
            return tool
    return None
