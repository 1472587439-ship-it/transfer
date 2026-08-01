# -*- coding: utf-8 -*-
"""
Ozon 产品报告 API 调用程序
支持循环查询，获取所有符合条件的数据
"""

import requests
import json
import os
import time
import logging
from datetime import datetime
from api_config import (
    API_KEY, API_URL, OUTPUT_DIR,
    DEFAULT_PARAMS,
    get_default_page_size, get_default_sort_field, get_default_sort_direction,
    get_config, build_params, merge_custom_params, stop_conditions
)

LATEST_FILE = os.path.join(OUTPUT_DIR, "latest.json")
INDEX_FILE = os.path.join(OUTPUT_DIR, "index.json")


def call_api(params=None, custom_params=None):
    """
    调用产品报告API

    Args:
        params: 直接传入完整参数
        custom_params: 传入自定义参数（会与默认参数合并）

    Returns:
        dict: API响应数据
    """
    if params is not None:
        request_data = params
    else:
        request_data = custom_params if custom_params else build_params()

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 打印最终发给 API 的完整 payload
    print(f"\n{'='*60}")
    print("最终发给 Seerfar 的完整请求 JSON:")
    print(json.dumps(request_data, ensure_ascii=False, indent=2))
    print(f"{'='*60}\n")

    try:
        print(f"正在请求 API...")
        response = requests.post(API_URL, json=request_data, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求异常: {e}")
        return None


def get_page_data(data):
    """从响应数据中提取列表数据"""
    print(f"[DEBUG] get_page_data 输入: type={type(data)}, keys={data.keys() if isinstance(data, dict) else 'N/A'}")
    if not isinstance(data, dict):
        return [], 0, 0

    if "data" in data:
        inner = data["data"]
        print(f"[DEBUG] inner: type={type(inner)}")
        if isinstance(inner, dict):
            if "records" in inner:
                records = inner["records"]
                if isinstance(records, list):
                    total = inner.get("total", len(records))
                    page_size = inner.get("pageSize", get_default_page_size())
                    total_pages = (total + page_size - 1) // page_size if total > 0 and page_size > 0 else 1
                    return records, total, total_pages
            if "list" in inner:
                return inner["list"], len(inner.get("list", [])), inner.get("totalPages", 1)
        elif isinstance(inner, list):
            print(f"[DEBUG] inner 是 list，长度={len(inner)}")
            return inner, len(inner), 1

    if "list" in data and isinstance(data["list"], list):
        return data["list"], len(data["list"]), 1

    print("[DEBUG] get_page_data 返回空")
    return [], 0, 0


def loop_call_api(custom_params=None, max_pages=None, stop_cond=None):
    """
    循环调用API获取所有数据

    Args:
        custom_params: 自定义查询参数（字典格式）
        max_pages: 最大查询页数，None表示查询所有页
        stop_cond: 停止条件字典:
            - stop_page: 到达指定页数停止
            - stop_on_empty: 遇到空页停止
            - stop_on_partial: 遇到数据不足停止

    Returns:
        dict: 包含所有结果的字典
    """
    # 合并停止条件
    if stop_cond is None:
        stop_cond = stop_conditions()

    config = DEFAULT_PARAMS["_config"]
    stop_on_empty = stop_cond.get("stop_on_empty", config["stopOnEmptyPage"])
    stop_on_partial = stop_cond.get("stop_on_partial", config["stopOnPartialPage"])
    stop_page = stop_cond.get("stop_page", None)

    final_max_pages = max_pages if max_pages is not None else config["maxPages"]

    all_data = []
    page_size = custom_params.get("page", {}).get("pageSize", get_default_page_size()) if custom_params else get_default_page_size()
    current_page = 1
    total_pages = 999999
    has_more = True

    print("=" * 60)
    print("开始循环查询...")
    print(f"最大页数限制: {final_max_pages if final_max_pages else '无限制'}")
    print(f"停止页数: {stop_page if stop_page else '无'}")
    print(f"空页停止: {stop_on_empty}, 部分页停止: {stop_on_partial}")
    print("=" * 60)

    while has_more:
        if final_max_pages is not None and current_page > final_max_pages:
            print(f"\n到达最大页数 {final_max_pages}，查询完成")
            break

        # 构建当前页参数
        if custom_params:
            current_params = merge_custom_params(custom_params, {})
            if "page" in current_params:
                current_params["page"]["pageNumber"] = current_page
            else:
                current_params["page"] = {
                    "pageNumber": current_page,
                    "pageSize": get_default_page_size(),
                    "orders": [{"field": get_default_sort_field(), "direction": get_default_sort_direction()}]
                }
        else:
            current_params = build_params()
            current_params["page"]["pageNumber"] = current_page

        print(f"\n查询第 {current_page} 页...", end=" ", flush=True)

        result = call_api(params=current_params)

        if result is None:
            print("失败")
            break

        page_data, total, api_total_pages = get_page_data(result)

        if api_total_pages > 0:
            total_pages = api_total_pages
        elif total > 0:
            total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1

        print(f"获取 {len(page_data)} 条数据 (共 {total_pages} 页)")

        if page_data:
            all_data.extend(page_data)
        else:
            print(f"  [第 {current_page} 页为空]")

        # 检查停止条件
        should_stop = False
        stop_reason = ""

        if stop_on_empty and not page_data:
            should_stop = True
            stop_reason = "遇到空页"
        elif stop_on_partial and page_data and len(page_data) < page_size:
            should_stop = True
            stop_reason = f"数据不足一页 ({len(page_data)}/{page_size})"

        # 检查是否到达最后一页
        if current_page >= total_pages:
            has_more = False
            if not should_stop:
                print(f"\n已到达最后一页 (第 {total_pages} 页)，查询完成")

        # 检查是否到达指定停止页（在最后一页之前）
        if stop_page is not None and current_page >= stop_page and has_more:
            should_stop = True
            stop_reason = f"到达指定停止页 {stop_page}"

        if should_stop:
            print(f"\n[停止原因] {stop_reason}")
            print(f"已查询 {current_page} 页，共获取 {len(all_data)} 条数据")
            break

        current_page += 1
        time.sleep(2)

    print("=" * 60)
    print(f"查询完成！共 {current_page} 页，{len(all_data)} 条数据")
    print("=" * 60)

    return {
        "data": all_data,
        "total_pages": current_page,
        "total_records": len(all_data),
        "last_page": current_page
    }


def save_response(data, auto_index=True, custom_filename=None):
    """保存响应数据"""
    if data is None:
        return None

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if custom_filename:
        filename = f"{custom_filename}_{timestamp}.json"
    else:
        filename = f"response_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到: {filepath}")

        with open(LATEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except IOError as e:
        print(f"保存数据失败: {e}")
        return None

    if auto_index:
        update_index(filepath, data)

    return {"filepath": filepath, "timestamp": timestamp, "filename": filename}


def update_index(filepath, data):
    """更新索引文件"""
    index_data = {"responses": []}
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        except:
            pass

    record = {
        "timestamp": datetime.now().isoformat(),
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "record_count": len(data.get("data", [])) if isinstance(data, dict) else 0
    }
    index_data["responses"].insert(0, record)
    index_data["responses"] = index_data["responses"][:100]

    try:
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    except:
        pass


def load_latest():
    """加载最新数据"""
    if not os.path.exists(LATEST_FILE):
        return None
    try:
        with open(LATEST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def load_by_filename(filename):
    """根据文件名加载数据"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def get_index_list():
    """获取响应索引列表"""
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get("responses", [])
    except:
        return []


# ============================================================
# 便捷查询函数
# ============================================================

def query(custom_params=None, max_pages=None, stop_page=None):
    """
    通用查询函数

    Args:
        custom_params: 查询参数（字典格式）
        max_pages: 最大页数限制
        stop_page: 指定停止页

    Returns:
        dict: 查询结果
    """
    cond = stop_conditions(stop_page=stop_page) if stop_page else stop_conditions()
    return loop_call_api(custom_params=custom_params, max_pages=max_pages, stop_cond=cond)


def query_all(custom_params=None):
    """查询所有符合条件的数据"""
    return loop_call_api(custom_params=custom_params)


def query_limit(custom_params=None, max_pages=10):
    """查询指定页数"""
    return loop_call_api(custom_params=custom_params, max_pages=max_pages)


def run_ozon_query(custom_filter=None, max_fetch_page=10, category_queries=None):
    """
    对外入口函数 - 唯一对外暴露的方法

    Args:
        custom_filter: 用户自定义可变筛选参数（价格、关键词、排序等）
                      注意: 不包含 categoryIds, 类目通过 category_queries 独立传入
        max_fetch_page: 最大拉取页数，默认10页
        category_queries: 类目查询词列表 (中/英/俄/ID 任意一种均可)
                         这是独立参数, 不混入 custom_filter
                         匹配完成后才把得到的 ID 放入 API 请求体

    Returns:
        list: 全部商品列表

    使用示例:
        # 仅查商品
        run_ozon_query({'price': {'min': 100, 'max': 500}})

        # 带类目筛选 (类目作为独立参数, 不是 custom_filter 的一部分)
        run_ozon_query(
            custom_filter={'price': {'min': 100, 'max': 500}},
            category_queries=['服装', 'Rashguard', '15621031']
        )

        # 也可以直接传已匹配好的 categoryIds (跳过自动匹配)
        run_ozon_query(
            custom_filter={'categoryIds': '15621031,15621031_200000933'},
        )
    """
    if custom_filter is None:
        custom_filter = {}

    # 类目匹配 - 独立参数处理
    if category_queries:
        try:
            from category_matcher import build_category_ids_param
            queries = category_queries
            if isinstance(queries, str):
                queries = [q.strip() for q in queries.split(',') if q.strip()]

            ids, detail = build_category_ids_param(queries)
            print(f"[类目匹配] 输入: {queries}")
            print(f"[类目匹配] 匹配成功: {len(detail['matched'])} 个, 未匹配: {detail['unmatched']}")
            if ids:
                print(f"[类目匹配] categoryIds = {ids}")
                custom_filter['categoryIds'] = ids
            else:
                print(f"[类目匹配] 全部未匹配, 不应用类目筛选")
        except ImportError:
            print("[类目匹配] category_matcher 模块未找到, 跳过自动匹配")
        except Exception as e:
            print(f"[类目匹配] 匹配出错: {e}")

    result = query(custom_params=custom_filter, max_pages=max_fetch_page)

    if isinstance(result, dict) and 'data' in result:
        return result['data']

    return []


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数 - 使用默认值查询"""
    print("=" * 60)
    print("Ozon 产品报告 API 查询")
    print("=" * 60)

    # 使用默认值（不传任何参数）
    result = query()
    save_response(result)

    print("\n完成！")


if __name__ == "__main__":
    main()
