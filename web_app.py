"""
Ozon 商品图片爬虫 - Web 版本
上传 JSON 文件批量爬取商品图片
"""

import os
import json
import uuid
import shutil
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# 导入爬虫模块
from crawler import WebCrawler

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

# 确保目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# 存储爬取进度
tasks = {}


def extract_product_urls(data):
    """从 JSON 数据中提取所有 productUrl"""
    urls = []
    
    # 处理 data 数组格式 {"data": [...]}
    if isinstance(data, dict) and 'data' in data:
        items = data['data']
    elif isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = [data]
    else:
        return urls
    
    for item in items:
        if isinstance(item, dict) and 'productUrl' in item:
            url = item['productUrl']
            if url:
                if not url.startswith('http'):
                    url = 'https://www.ozon.ru' + url
                urls.append(url)
    
    return urls


def crawl_task(task_id, json_content):
    """后台爬取任务"""
    crawler = None
    try:
        tasks[task_id]['status'] = 'parsing'
        tasks[task_id]['message'] = '正在解析 JSON 文件...'
        
        data = json.loads(json_content)
        urls = extract_product_urls(data)
        
        if not urls:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['message'] = '未找到 productUrl 字段'
            return
        
        tasks[task_id]['total'] = len(urls)
        tasks[task_id]['status'] = 'crawling'
        tasks[task_id]['message'] = f'准备爬取 {len(urls)} 个商品...'
        
        crawler = WebCrawler()
        crawler.initialize(use_cookies=True)
        
        results = []
        
        for i, url in enumerate(urls, 1):
            tasks[task_id]['current'] = i
            tasks[task_id]['message'] = f'正在爬取 [{i}/{len(urls)}]'
            tasks[task_id]['current_url'] = url
            
            try:
                result = crawler.crawl(url, show_output=False)
                results.append(result)
            except Exception as e:
                results.append({'url': url, 'error': str(e)})
            
            time.sleep(1)
        
        # 保存结果
        result_file = f"{app.config['OUTPUT_FOLDER']}/batch_{task_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['message'] = f'爬取完成! 共 {len(urls)} 个商品'
        tasks[task_id]['result_file'] = result_file
        
    except json.JSONDecodeError as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['message'] = f'JSON 格式错误: {e}'
    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['message'] = f'爬取失败: {e}'
    finally:
        if crawler:
            crawler.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    if not file.filename.endswith('.json'):
        return jsonify({'success': False, 'message': '请上传 JSON 文件'})
    
    # 保存文件
    task_id = str(uuid.uuid4())[:8]
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
    file.save(filepath)
    
    # 读取内容
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析并获取 URL 数量
    try:
        data = json.loads(content)
        urls = extract_product_urls(data)
    except:
        os.remove(filepath)
        return jsonify({'success': False, 'message': 'JSON 格式错误'})
    
    if not urls:
        os.remove(filepath)
        return jsonify({'success': False, 'message': '未找到 productUrl 字段'})
    
    # 初始化任务
    tasks[task_id] = {
        'status': 'pending',
        'message': '等待开始...',
        'total': len(urls),
        'current': 0,
        'current_url': '',
        'result_file': None,
        'filename': filename
    }
    
    # 启动后台爬取
    thread = threading.Thread(target=crawl_task, args=(task_id, content))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'url_count': len(urls),
        'filename': filename
    })


@app.route('/status/<task_id>')
def status(task_id):
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'})
    return jsonify(tasks[task_id])


@app.route('/download/<task_id>')
def download(task_id):
    if task_id not in tasks:
        return '任务不存在', 404
    
    task = tasks[task_id]
    if task['status'] != 'completed' or not task.get('result_file'):
        return '结果文件不存在', 404
    
    return send_file(
        task['result_file'],
        as_attachment=True,
        download_name=f"crawl_results_{task_id}.json"
    )


if __name__ == '__main__':
    print('╔════════════════════════════════════════════╗')
    print('║    Ozon 商品图片爬虫 - Web 版本             ║')
    print('╚════════════════════════════════════════════╝')
    print('\n请在浏览器打开: http://127.0.0.1:5000\n')
    app.run(host='0.0.0.0', port=5000, debug=False)
