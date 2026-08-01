# -*- coding: utf-8 -*-
"""
前端查询服务 - 调用 ozon_product_report.py 的核心功能
"""

import json
import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from ozon_product_report import query, run_ozon_query
from category_matcher import (
    search_categories, match_category, match_categories,
    build_category_ids_param, load_categories, rebuild_cache,
    get_category_tree
)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route('/')
def index():
    return send_from_directory('.', 'task_front.html')

@app.route('/api/query', methods=['POST', 'OPTIONS'])
def api_query():
    """接收查询请求，调用核心API"""
    try:
        params = request.json if request.json else {}

        logger.info(f"[API_QUERY] === 收到前端请求 ===")
        logger.info(f"[API_QUERY] 请求方法: {request.method}")
        logger.info(f"[API_QUERY] Content-Type: {request.content_type}")
        logger.info(f"[API_QUERY] 请求体: {request.get_data(as_text=True)}")
        logger.info(f"[API_QUERY] 解析后 params keys: {list(params.keys())}")
        logger.info(f"[API_QUERY] params 内容: {params}")

        # 提取分页配置
        max_pages = params.pop('_config', {}).get('maxPages', 2)
        page_config = params.pop('page', None)
        logger.info(f"[API_QUERY] max_pages={max_pages}")

        # 类目作为独立参数 (categoryQueries), 不在 params 中
        category_queries = params.pop('categoryQueries', None)
        logger.info(f"[API_QUERY] 类目查询词 category_queries={category_queries}")

        # 调用真实API (类目独立处理: 匹配后才放入API请求体)
        result = run_ozon_query(
            custom_filter=params,
            max_fetch_page=max_pages,
            category_queries=category_queries
        )
        logger.info(f"[API_QUERY] 返回商品数: {len(result) if isinstance(result, list) else 'N/A'}")

        # 保存到 latest.json 供 /api/results 读取 + 持久化
        try:
            os.makedirs('output', exist_ok=True)
            payload = {
                "data": result if isinstance(result, list) else [],
                "total_records": len(result) if isinstance(result, list) else 0,
                "queried_at": __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "params": {k: v for k, v in params.items() if k not in ('categoryQueries',)},
                "category_queries": category_queries,
            }
            with open(os.path.join('output', 'latest.json'), 'w', encoding='utf-8') as f:
                import json
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as save_err:
            logger.error(f"[API_QUERY] 保存 latest.json 失败: {save_err}")

        return jsonify({
            'code': 200,
            'msg': 'SUCCESS',
            'data': result
        })
    except Exception as e:
        logger.error(f"[API_QUERY] 错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e), 'data': None}), 200

@app.route('/api/results')
def api_results():
    """读取最新查询结果"""
    try:
        latest = os.path.join('output', 'latest.json')
        if os.path.exists(latest):
            with open(latest, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({'code': 200, 'data': data.get('data', [])})
        else:
            return jsonify({'code': 404, 'msg': '暂无查询结果', 'data': None}), 200
    except Exception as e:
        return jsonify({'code': -1, 'msg': str(e), 'data': None}), 200


@app.route('/api/category/search', methods=['GET', 'POST', 'OPTIONS'])
def api_category_search():
    """
    类目搜索接口
    GET  /api/category/search?keyword=服装
    POST /api/category/search  body={"keyword": "...", "lang": "auto", "limit": 50}
    """
    try:
        if request.method == 'GET':
            keyword = request.args.get('keyword', '').strip()
            lang = request.args.get('lang', 'auto')
            limit = int(request.args.get('limit', 50))
        else:
            body = request.json or {}
            keyword = body.get('keyword', '').strip()
            lang = body.get('lang', 'auto')
            limit = int(body.get('limit', 50))

        results = search_categories(keyword, limit=limit, lang=lang)
        # 转换为前端友好的格式
        items = [{
            'id': c['id'],
            'name_zh': c['zh'],
            'name_en': c['en'],
            'name_ru': c['ru'],
            'parent_id': c['parent_id'],
            'level': c['level'],
        } for c in results]

        return jsonify({
            'code': 200,
            'msg': 'SUCCESS',
            'data': {
                'keyword': keyword,
                'count': len(items),
                'items': items,
            }
        })
    except Exception as e:
        logger.error(f"[CATEGORY_SEARCH] 错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e), 'data': None}), 200


@app.route('/api/category/tree')
def api_category_tree():
    """
    返回 3 级类目树形结构
    GET /api/category/tree
    """
    try:
        tree = get_category_tree()
        return jsonify({'code': 200, 'msg': 'SUCCESS', 'data': tree})
    except Exception as e:
        logger.error(f"[CATEGORY_TREE] 错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e), 'data': None}), 200


@app.route('/api/category/match', methods=['POST', 'OPTIONS'])
def api_category_match():
    """
    类目匹配接口 (支持中/英/俄/ID 混合)
    POST /api/category/match  body={"queries": ["服装", "Rashguard", "15621031"], "lang": "auto"}
    """
    try:
        body = request.json or {}
        queries = body.get('queries', [])
        lang = body.get('lang', 'auto')
        threshold = float(body.get('threshold', 0.6))

        if isinstance(queries, str):
            queries = [q.strip() for q in queries.split(',') if q.strip()]

        if not queries:
            return jsonify({'code': 400, 'msg': 'queries 不能为空', 'data': None}), 200

        result = match_categories(queries, threshold=threshold, lang=lang)
        ids, _ = build_category_ids_param(queries, threshold=threshold, lang=lang)

        return jsonify({
            'code': 200,
            'msg': 'SUCCESS',
            'data': {
                'matched': result['matched'],
                'unmatched': result['unmatched'],
                'categoryIds': ids,
            }
        })
    except Exception as e:
        logger.error(f"[CATEGORY_MATCH] 错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': -1, 'msg': str(e), 'data': None}), 200


@app.route('/api/category/rebuild', methods=['POST', 'OPTIONS'])
def api_category_rebuild():
    """强制从 Excel 重建缓存"""
    try:
        categories = rebuild_cache()
        return jsonify({
            'code': 200,
            'msg': 'SUCCESS',
            'data': {'count': len(categories)}
        })
    except Exception as e:
        logger.error(f"[CATEGORY_REBUILD] 错误: {e}")
        return jsonify({'code': -1, 'msg': str(e), 'data': None}), 200

if __name__ == '__main__':
    print("=" * 50)
    print("Ozon 产品查询服务")
    print("访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
