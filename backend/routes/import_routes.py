# -*- coding: utf-8 -*-
"""
数据导入相关路由
"""

import os
import json
import subprocess
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
import_bp = Blueprint('import', __name__)

# 全局变量
processing_tasks = {}
current_task_id = None
kg_process = None
processing_history = []

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_directory_exists(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_processing_history():
    """加载处理历史"""
    history_file = os.path.join(current_app.config['DATA_DIR'], 'processing_history.json')
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f'加载处理历史失败: {e}')
    return []

def save_processing_history(history):
    """保存处理历史"""
    data_dir = current_app.config['DATA_DIR']
    ensure_directory_exists(data_dir)
    history_file = os.path.join(data_dir, 'processing_history.json')
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f'保存处理历史失败: {e}')
        return False

@import_bp.route('/upload', methods=['POST'])
def upload_file():
    """文件上传"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有文件被上传'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        if file and allowed_file(file.filename):
            # 确保上传目录存在
            upload_folder = current_app.config['UPLOAD_FOLDER']
            ensure_directory_exists(upload_folder)
            
            # 生成安全的文件名
            filename = secure_filename(file.filename)
            
            # 如果文件名为空（可能包含非ASCII字符），使用时间戳
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'txt'
                filename = f'upload_{timestamp}.{ext}'
            
            file_path = os.path.join(upload_folder, filename)
            
            # 如果文件已存在，添加时间戳
            if os.path.exists(file_path):
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'{name}_{timestamp}{ext}'
                file_path = os.path.join(upload_folder, filename)
            
            file.save(file_path)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'path': file_path,
                'message': '文件上传成功'
            })
        else:
            return jsonify({'success': False, 'message': '不支持的文件类型'}), 400
            
    except Exception as e:
        logger.error(f'文件上传失败: {e}')
        return jsonify({'success': False, 'message': f'文件上传失败: {str(e)}'}), 500

@import_bp.route('/process', methods=['POST'])
def process_files():
    """处理文件，生成知识图谱"""
    global processing_tasks, current_task_id, kg_process
    
    try:
        data = request.get_json()
        files = data.get('files', [])
        options = data.get('options', {})
        
        if not files:
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        # 检查是否有正在进行的任务
        if current_task_id and kg_process and kg_process.poll() is None:
            return jsonify({'success': False, 'message': '已有任务正在进行中，请等待完成或取消当前任务'})
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        current_task_id = task_id
        
        # 初始化任务状态
        processing_tasks[task_id] = {
            'isProcessing': True,
            'progress': 0,
            'currentFile': '准备开始处理...',
            'statusText': '初始化中...',
            'files': files,
            'totalFiles': len(files),
            'processedFiles': 0,
            'newHistoryItems': []
        }
        
        # 启动处理进程
        start_kg_process(task_id, files, options)
        
        return jsonify({'success': True, 'taskId': task_id})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动处理失败: {str(e)}'})

def start_kg_process(task_id, files, options):
    """启动知识图谱生成进程"""
    global kg_process
    
    try:
        task = processing_tasks.get(task_id)
        if not task:
            return
        
        # 加载系统配置
        config_path = os.path.join(current_app.root_path, '..', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except:
            settings = {
                'neo4j': {'uri': 'bolt://localhost:7687', 'username': 'neo4j', 'password': 'password'},
                'llm': {'apiKey': '', 'endpoint': '', 'modelName': 'gpt-3.5-turbo'},
                'geocoding': {'apiKey': '', 'service': 'baidu'},
                'system': {'pythonPath': 'python', 'maxWorkers': 4}
            }
        
        # 构建命令参数
        script_path = os.path.join(current_app.root_path, '..', 'kg_generation.py')
        
        args = [
            settings['system'].get('pythonPath', 'python'),
            script_path,
            '--files'
        ]
        
        # 添加文件路径
        for file_info in files:
            args.append(file_info['path'])
        
        # 添加数据库配置
        args.extend([
            '--neo4j-uri', settings['neo4j']['uri'],
            '--neo4j-username', settings['neo4j']['username'],
            '--neo4j-password', settings['neo4j']['password']
        ])
        
        # 添加LLM配置
        args.extend([
            '--llm-api-key', settings['llm']['apiKey'],
            '--llm-endpoint', settings['llm']['endpoint'],
            '--model-name', options.get('modelName') or settings['llm']['modelName']
        ])
        
        # 添加地理编码配置
        args.extend([
            '--geocoding-api-key', settings['geocoding']['apiKey'],
            '--geocoding-service', settings['geocoding']['service']
        ])
        
        # 添加其他选项
        args.extend([
            '--max-workers', str(options.get('maxWorkers') or settings['system']['maxWorkers']) if options.get('parallel') else '1',
            '--validate-data', 'true' if options.get('validateData') else 'false',
            '--export-json', 'true' if options.get('exportJson') else 'false'
        ])
        
        # 启动进程
        kg_process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            bufsize=1,
            universal_newlines=True
        )
        
        # 在实际应用中，这里应该启动后台线程来监控进程输出
        # 这里简化处理
        
    except Exception as e:
        print(f"启动KG进程失败: {e}")
        if task_id in processing_tasks:
            processing_tasks[task_id]['isProcessing'] = False
            processing_tasks[task_id]['statusText'] = f'启动失败: {str(e)}'

@import_bp.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    global kg_process, current_task_id, processing_history
    
    task = processing_tasks.get(task_id)
    
    if not task:
        return jsonify({'success': False, 'message': '任务不存在'})
    
    # 检查进程状态
    if kg_process and task_id == current_task_id:
        poll_result = kg_process.poll()
        if poll_result is not None:
            # 进程已结束
            task['isProcessing'] = False
            if poll_result == 0:
                task['progress'] = 100
                task['statusText'] = '处理完成'
                task['currentFile'] = '所有文件处理完成'
                
                # 添加到处理历史
                now = datetime.now()
                time_str = now.strftime('%Y-%m-%d %H:%M')
                
                history_item = {
                    'id': str(int(now.timestamp() * 1000)),
                    'content': f'批量处理完成：{len(task["files"])}个文件',
                    'type': 'success',
                    'time': time_str
                }
                
                processing_history.insert(0, history_item)
                task['newHistoryItems'].append(history_item)
                save_processing_history(processing_history)
            else:
                # 处理失败
                now = datetime.now()
                time_str = now.strftime('%Y-%m-%d %H:%M')
                
                history_item = {
                    'id': str(int(now.timestamp() * 1000)),
                    'content': f'处理失败：退出码 {poll_result}',
                    'type': 'danger',
                    'time': time_str
                }
                
                processing_history.insert(0, history_item)
                task['newHistoryItems'].append(history_item)
                save_processing_history(processing_history)
                
                task['statusText'] = f'处理失败，退出码: {poll_result}'
            
            # 清理进程引用
            kg_process = None
            current_task_id = None
    
    # 提取需要返回的任务状态信息
    task_status = {
        'isProcessing': task['isProcessing'],
        'progress': task['progress'],
        'currentFile': task['currentFile'],
        'statusText': task['statusText'],
        'totalFiles': task['totalFiles'],
        'processedFiles': task['processedFiles'],
        'newHistoryItems': task.get('newHistoryItems', [])
    }
    
    # 清空已发送的历史记录，避免重复发送
    task['newHistoryItems'] = []
    
    return jsonify(task_status)

@import_bp.route('/history', methods=['GET'])
def get_processing_history():
    """获取处理历史"""
    global processing_history
    try:
        # 确保返回最新的处理历史
        processing_history = load_processing_history()
        return jsonify(processing_history)
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取历史记录失败: {str(e)}'})

@import_bp.route('/history', methods=['DELETE'])
def clear_processing_history():
    """清空处理历史"""
    global processing_history
    try:
        processing_history = []
        save_processing_history(processing_history)
        return jsonify({'success': True, 'message': '处理历史已清空'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空历史记录失败: {str(e)}'})

@import_bp.route('/scan-directory', methods=['POST'])
def scan_directory():
    """扫描目录"""
    try:
        data = request.get_json()
        directory_path = data.get('path', '')
        
        if not directory_path:
            return jsonify({'success': False, 'message': '目录路径不能为空'}), 400
        
        if not os.path.exists(directory_path):
            return jsonify({'success': False, 'message': '目录不存在'}), 404
        
        if not os.path.isdir(directory_path):
            return jsonify({'success': False, 'message': '路径不是目录'}), 400
        
        files = []
        try:
            for item in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item)
                if os.path.isfile(item_path) and allowed_file(item):
                    stat = os.stat(item_path)
                    files.append({
                        'name': item,
                        'path': item_path,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        except PermissionError:
            return jsonify({'success': False, 'message': '没有权限访问该目录'}), 403
        
        return jsonify({
            'success': True,
            'files': files,
            'directory': directory_path
        })
        
    except Exception as e:
        logger.error(f'扫描目录失败: {e}')
        return jsonify({'success': False, 'message': f'扫描目录失败: {str(e)}'}), 500

@import_bp.route('/cancel-task', methods=['POST'])
def cancel_task():
    """取消任务"""
    global kg_process, current_task_id, processing_history
    
    try:
        if not current_task_id or not kg_process:
            return jsonify({'success': False, 'message': '没有正在进行的任务'})
        
        # 终止进程
        kg_process.terminate()
        try:
            kg_process.wait(timeout=5)  # 等待5秒
        except subprocess.TimeoutExpired:
            kg_process.kill()  # 强制终止
        
        # 更新任务状态
        task = processing_tasks.get(current_task_id)
        if task:
            task['isProcessing'] = False
            task['statusText'] = '任务已取消'
            
            # 添加到处理历史
            now = datetime.now()
            time_str = now.strftime('%Y-%m-%d %H:%M')
            
            history_item = {
                'id': str(int(now.timestamp() * 1000)),
                'content': '任务已取消',
                'type': 'warning',
                'time': time_str
            }
            
            processing_history.insert(0, history_item)
            task['newHistoryItems'].append(history_item)
            save_processing_history(processing_history)
        
        kg_process = None
        current_task_id = None
        
        return jsonify({'success': True, 'message': '任务已取消'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'取消任务失败: {str(e)}'})