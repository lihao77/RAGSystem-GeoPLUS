import os
import json
import random
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
import logging

from db import get_session

logger = logging.getLogger(__name__)

# 创建蓝图
evaluation_bp = Blueprint('evaluation', __name__)

def ensure_evaluation_directory():
    """确保评估目录存在"""
    evaluation_dir = os.path.join(os.getcwd(), 'evaluation_samples')
    if not os.path.exists(evaluation_dir):
        os.makedirs(evaluation_dir)
    return evaluation_dir

@evaluation_bp.route('/documents', methods=['GET'])
def get_documents():
    """获取可用于评估的文档列表"""
    session = None
    try:
        session = get_session()
        
        # 查询所有不同的文档来源
        query = """
        MATCH (n)
        WHERE n.source IS NOT NULL
        RETURN DISTINCT n.source as source
        ORDER BY source
        """
        
        result = session.run(query)
        
        documents = []
        for i, record in enumerate(result):
            if record['source']:
                documents.append({
                    'id': f'doc-{i + 1}',
                    'name': record['source'],
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
        
        return jsonify(documents)
        
    except Exception as e:
        logger.error(f'获取文档列表失败: {e}')
        return jsonify({'error': '获取可用文档失败', 'details': str(e)}), 500
    finally:
        if session:
            session.close()

@evaluation_bp.route('/generate-samples', methods=['POST'])
def generate_samples():
    """生成评估样本"""
    session = None
    try:
        data = request.get_json()
        
        evaluation_type = data.get('evaluationType')
        sampling_method = data.get('samplingMethod')
        sample_size = int(data.get('sampleSize', 10))
        document_ids = data.get('documentIds', [])
        entity_types = data.get('entityTypes', [])
        
        session = get_session()
        
        cypher = ''
        params = {}
        
        # 根据不同的抽样方法构建查询
        if sampling_method == 'random':
            # 随机抽取样本
            cypher = """
            MATCH (n:State)
            RETURN n.id AS id, n.type AS type, n.time AS time, n.source AS source, 
                   n.entity_ids AS entityIds, n.text AS text
            ORDER BY rand()
            LIMIT $sampleSize
            """
            params['sampleSize'] = sample_size
        elif sampling_method == 'document':
            # 按文档抽取样本
            cypher = """
            MATCH (n:State)
            WHERE n.source IN $documentIds
            RETURN n.id AS id, n.type AS type, n.time AS time, n.source AS source, 
                   n.entity_ids AS entityIds, n.text AS text
            ORDER BY rand()
            LIMIT $sampleSize
            """
            params['documentIds'] = document_ids
            params['sampleSize'] = sample_size
        elif sampling_method == 'entity':
            # 按实体类型抽取样本
            cypher = """
            MATCH (n:State)
            WHERE any(type IN $entityTypes WHERE n.type CONTAINS type)
            RETURN n.id AS id, n.type AS type, n.time AS time, n.source AS source, 
                   n.entity_ids AS entityIds, n.text AS text
            ORDER BY rand()
            LIMIT $sampleSize
            """
            params['entityTypes'] = entity_types
            params['sampleSize'] = sample_size
        
        result = session.run(cypher, params)
        
        # 处理样本数据
        samples = []
        for record in result:
            state_id = record['id']
            entity_ids = record['entityIds'] or []
            
            # 获取相关实体信息
            entities_result = session.run("""
            MATCH (e)
            WHERE e.id IN $entityIds
            RETURN e.id AS id, e.name AS name, labels(e)[0] AS type, properties(e) AS properties
            """, {'entityIds': entity_ids})
            
            entities = []
            for entity_record in entities_result:
                entities.append({
                    'id': entity_record['id'],
                    'name': entity_record['name'],
                    'type': entity_record['type'],
                    'properties': dict(entity_record['properties']) if entity_record['properties'] else {}
                })
            
            # 获取相关关系信息
            relations_result = session.run("""
            MATCH (e1)-[r]->(e2)
            WHERE e1.id IN $entityIds AND e2.id IN $entityIds
            RETURN e1.id AS source, e2.id AS target, type(r) AS type, properties(r) AS properties
            """, {'entityIds': entity_ids})
            
            relations = []
            for rel_record in relations_result:
                relations.append({
                    'source': rel_record['source'],
                    'target': rel_record['target'],
                    'type': rel_record['type'],
                    'properties': dict(rel_record['properties']) if rel_record['properties'] else {}
                })
            
            samples.append({
                'id': f'sample-{state_id}',
                'stateId': state_id,
                'type': record['type'],
                'time': record['time'],
                'source': record['source'],
                'text': record['text'] or '无文本内容',
                'entities': entities,
                'relations': relations,
                # 用于标注的字段
                'missingEntities': [],
                'missingRelations': [],
                'annotated': False
            })
        
        # 保存样本到文件
        evaluation_dir = ensure_evaluation_directory()
        timestamp = int(datetime.now().timestamp() * 1000)
        samples_file = os.path.join(evaluation_dir, f'samples-{timestamp}.json')
        
        with open(samples_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
        
        return jsonify(samples)
        
    except Exception as e:
        logger.error(f'生成评估样本失败: {e}')
        return jsonify({'error': '生成评估样本失败', 'details': str(e)}), 500
    finally:
        if session:
            session.close()

@evaluation_bp.route('/samples', methods=['GET'])
def get_sample_files():
    """获取已生成的样本文件列表"""
    try:
        evaluation_dir = ensure_evaluation_directory()
        
        files = []
        for filename in os.listdir(evaluation_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(evaluation_dir, filename)
                stat = os.stat(filepath)
                
                # 尝试读取文件元数据
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        metadata = data.get('metadata', {})
                except Exception as e:
                    logger.warning(f'读取样本文件元数据失败 {filename}: {e}')
                    metadata = {}
                
                files.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'metadata': metadata
                })
        
        # 按修改时间倒序排列
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify(files)
        
    except Exception as e:
        logger.error(f'获取样本文件列表失败: {e}')
        return jsonify({'success': False, 'message': '获取样本文件列表失败'}), 500

@evaluation_bp.route('/samples/<filename>', methods=['GET'])
def get_sample_file(filename):
    """获取指定样本文件的内容"""
    try:
        evaluation_dir = ensure_evaluation_directory()
        filepath = os.path.join(evaluation_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f'获取样本文件内容失败: {e}')
        return jsonify({'success': False, 'message': '获取样本文件内容失败'}), 500

@evaluation_bp.route('/samples/<filename>', methods=['DELETE'])
def delete_sample_file(filename):
    """删除指定样本文件"""
    try:
        evaluation_dir = ensure_evaluation_directory()
        filepath = os.path.join(evaluation_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        os.remove(filepath)
        
        return jsonify({'message': '文件删除成功'})
        
    except Exception as e:
        logger.error(f'删除样本文件失败: {e}')
        return jsonify({'success': False, 'message': '删除样本文件失败'}), 500

@evaluation_bp.route('/save-annotation', methods=['POST'])
def save_annotation():
    """保存样本标注"""
    try:
        data = request.get_json()
        sample_id = data.get('sampleId')
        entities = data.get('entities', [])
        relations = data.get('relations', [])
        missing_entities = data.get('missingEntities', [])
        missing_relations = data.get('missingRelations', [])
        
        evaluation_dir = ensure_evaluation_directory()
        
        # 读取现有样本文件列表
        sample_files = [f for f in os.listdir(evaluation_dir) 
                       if f.startswith('samples-') and f.endswith('.json')]
        
        # 查找包含该样本的文件并更新
        updated = False
        for file in sample_files:
            filepath = os.path.join(evaluation_dir, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    samples = json.load(f)
                
                sample_index = next((i for i, sample in enumerate(samples) 
                                   if sample.get('id') == sample_id), -1)
                
                if sample_index != -1:
                    # 更新样本标注
                    samples[sample_index]['entities'] = entities
                    samples[sample_index]['relations'] = relations
                    samples[sample_index]['missingEntities'] = missing_entities
                    samples[sample_index]['missingRelations'] = missing_relations
                    samples[sample_index]['annotated'] = True
                    
                    # 保存更新后的样本
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(samples, f, ensure_ascii=False, indent=2)
                    updated = True
                    break
            except Exception as e:
                logger.warning(f'处理样本文件失败 {file}: {e}')
                continue
        
        if updated:
            return jsonify({'success': True, 'message': '样本标注已保存'})
        else:
            return jsonify({'error': '未找到指定样本'}), 404
            
    except Exception as e:
        logger.error(f'保存样本标注失败: {e}')
        return jsonify({'error': '保存样本标注失败', 'details': str(e)}), 500

@evaluation_bp.route('/calculate-metrics', methods=['POST'])
def calculate_metrics():
    """计算评估指标"""
    try:
        data = request.get_json()
        task_type = data.get('taskType')  # 'entity' 或 'relation'
        
        evaluation_dir = ensure_evaluation_directory()
        
        # 读取样本文件
        sample_files = [f for f in os.listdir(evaluation_dir) 
                       if f.startswith('samples-') and f.endswith('.json')]
        
        samples = []
        for file in sample_files:
            filepath = os.path.join(evaluation_dir, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_samples = json.load(f)
                samples.extend(file_samples)
            except Exception as e:
                logger.warning(f'读取样本文件失败 {file}: {e}')
                continue
        
        if not samples:
            return jsonify({'error': '未找到样本数据'}), 404
        
        # 过滤已标注的样本
        annotated_samples = [s for s in samples if s.get('annotated', False)]
        
        if not annotated_samples:
            return jsonify({'error': '未找到已标注的样本'}), 404
        
        # 计算指标
        metrics = calculate_evaluation_metrics(annotated_samples, task_type)
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f'计算评估指标失败: {e}')
        return jsonify({'error': '计算评估指标失败', 'details': str(e)}), 500

@evaluation_bp.route('/export-report', methods=['POST'])
def export_report():
    """导出评估报告"""
    try:
        data = request.get_json()
        metrics = data.get('metrics', {})
        format_type = data.get('format', 'json')  # 'json' 或 'csv'
        
        evaluation_dir = ensure_evaluation_directory()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'csv':
            # 导出CSV格式
            filename = f'evaluation-report-{timestamp}.csv'
            filepath = os.path.join(evaluation_dir, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Metric', 'Precision', 'Recall', 'F1-Score'])
                
                # 写入实体指标
                if 'entity' in metrics:
                    em = metrics['entity']
                    writer.writerow(['Entity', em.get('precision', 0), 
                                   em.get('recall', 0), em.get('f1', 0)])
                
                # 写入关系指标
                if 'relation' in metrics:
                    rm = metrics['relation']
                    writer.writerow(['Relation', rm.get('precision', 0), 
                                   rm.get('recall', 0), rm.get('f1', 0)])
        else:
            # 导出JSON格式
            filename = f'evaluation-report-{timestamp}.json'
            filepath = os.path.join(evaluation_dir, filename)
            
            report_data = {
                'timestamp': timestamp,
                'metrics': metrics
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': '评估报告导出成功',
            'filename': filename,
            'filepath': filepath
        })
        
    except Exception as e:
        logger.error(f'导出评估报告失败: {e}')
        return jsonify({'error': '导出评估报告失败', 'details': str(e)}), 500

@evaluation_bp.route('/download-report/<filename>', methods=['GET'])
def download_report(filename):
    """下载报告"""
    try:
        evaluation_dir = ensure_evaluation_directory()
        filepath = os.path.join(evaluation_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': '报告文件不存在'}), 404
        
        from flask import send_file
        return send_file(filepath, as_attachment=True)
            
    except Exception as e:
        logger.error(f'下载报告失败: {e}')
        return jsonify({'error': '下载报告失败', 'details': str(e)}), 500

def calculate_evaluation_metrics(samples, task_type):
    """计算评估指标"""
    if task_type == 'entity':
        return calculate_entity_metrics(samples)
    elif task_type == 'relation':
        return calculate_relation_metrics(samples)
    else:
        # 计算综合指标
        entity_metrics = calculate_entity_metrics(samples)
        relation_metrics = calculate_relation_metrics(samples)
        
        return {
            'entity': entity_metrics,
            'relation': relation_metrics,
            'overall': {
                'precision': (entity_metrics['precision'] + relation_metrics['precision']) / 2,
                'recall': (entity_metrics['recall'] + relation_metrics['recall']) / 2,
                'f1': (entity_metrics['f1Score'] + relation_metrics['f1Score']) / 2
            }
        }

def calculate_entity_metrics(samples):
    """计算实体识别指标"""
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    
    for sample in samples:
        # 真阳性：正确识别的实体数量
        true_positives += len(sample.get('entities', []))
        
        # 假阴性：漏检的实体数量
        false_negatives += len(sample.get('missingEntities', []))
        
        # 假阳性：错误识别的实体数量（简化处理）
        false_positives += 0
    
    # 计算指标
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = true_positives / (true_positives + false_positives + false_negatives) if (true_positives + false_positives + false_negatives) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1Score': f1_score,
        'accuracy': accuracy,
        'truePositives': true_positives,
        'falsePositives': false_positives,
        'falseNegatives': false_negatives
    }

def calculate_relation_metrics(samples):
    """计算关系抽取指标"""
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    
    for sample in samples:
        # 真阳性：正确识别的关系数量
        true_positives += len(sample.get('relations', []))
        
        # 假阴性：漏检的关系数量
        false_negatives += len(sample.get('missingRelations', []))
        
        # 假阳性：错误识别的关系数量（简化处理）
        false_positives += 0
    
    # 计算指标
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = true_positives / (true_positives + false_positives + false_negatives) if (true_positives + false_positives + false_negatives) > 0 else 0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1Score': f1_score,
        'accuracy': accuracy,
        'truePositives': true_positives,
        'falsePositives': false_positives,
        'falseNegatives': false_negatives
    }

def analyze_common_errors(samples):
    """分析常见错误"""
    # 统计漏检实体类型
    missing_entity_types = {}
    for sample in samples:
        for entity in sample.get('missingEntities', []):
            entity_type = entity.get('type', '未知类型')
            missing_entity_types[entity_type] = missing_entity_types.get(entity_type, 0) + 1
    
    # 统计漏检关系类型
    missing_relation_types = {}
    for sample in samples:
        for relation in sample.get('missingRelations', []):
            relation_type = relation.get('type', '未知类型')
            missing_relation_types[relation_type] = missing_relation_types.get(relation_type, 0) + 1
    
    # 转换为数组格式
    missing_entity_types_array = [
        {'type': entity_type, 'count': count}
        for entity_type, count in sorted(missing_entity_types.items(), key=lambda x: x[1], reverse=True)
    ]
    
    missing_relation_types_array = [
        {'type': relation_type, 'count': count}
        for relation_type, count in sorted(missing_relation_types.items(), key=lambda x: x[1], reverse=True)
    ]
    
    return {
        'missingEntityTypes': missing_entity_types_array,
        'missingRelationTypes': missing_relation_types_array
    }