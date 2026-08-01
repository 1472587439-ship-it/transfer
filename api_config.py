# -*- coding: utf-8 -*-
"""
Ozon 产品报告 API 配置文件
所有参数配置和调用函数都写在此文件，方便后期修改和查看

使用方式：
    1. 直接修改 DEFAULT_PARAMS 中的默认值
    2. 使用 set_param() 函数设置参数
    3. 使用 build_params() 构建完整查询参数
"""

import os
import copy

# ============================================================
# API 配置
# ============================================================
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzaWduIjoiNGI4ODY2NjhkMzYwNDk1MzkwZWU5ZTZjZGM0Nzc5YjYiLCJwYXJ0bmVyVHlwZSI6MCwicGFydG5lcklkIjo5NjU0MX0.WzYonZvPF--YQWZ4ttqoP57PXyR-0-VjRGfQ73R32ek"
API_URL = "http://api.seerfar.cn/open-api/productReport/search/ozon"

# ============================================================
# 输出目录配置
# ============================================================
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# ============================================================
# 输出目录配置
# ============================================================
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


# ============================================================
# 默认请求参数模板（单一数据源，修改默认值只需改这里）
# ============================================================
DEFAULT_PARAMS = {
    # ============================================================
    # API 请求参数
    # ============================================================
    # ---- 评论相关 ----
    "reviewCount": {"min": None, "max": None},           # 评论数量

    # ---- 评分相关 ----
    "drr": {"min": None, "max": None},                    # DRR动态评分
    "reviewRating": {"min": None, "max": None},          # 商品评分(1-5)

    # ---- 问答相关 ----
    "questionsAndAnswers": {"min": None, "max": None},   # 问答数量

    # ---- 价格相关 ----
    "price": {"min": None, "max": None},                 # 价格

    # ---- 销售相关 ----
    "monthlyRevenue": {"min": None, "max": None},         # 月收入
    "monthlySales": {"min": None, "max": None},          # 月销量
    "monthlySalesRate": {"min": None, "max": None},      # 月销售率

    # ---- 物理属性 ----
    "weight": {"min": None, "max": None},                # 重量(kg)
    "volume": {"min": None, "max": None},                # 体积

    # ---- 财务相关 ----
    "grossMargin": {"min": None, "max": None},           # 毛利率(0-1)

    # ---- 变体相关 ----
    "variants": {"min": None, "max": None},              # 变体数量

    # ---- 转化相关 ----
    "convToCartPdp": {"min": None, "max": None},        # PDP转化率

    # ---- 退货相关 ----
    "returnCancellationRate": {"min": None, "max": None},  # 退货/取消率

    # ---- 商品信息 ----
    "creationDate": None,                                # 创建日期(YYYY-MM-DD)

    # ---- 类目 ----
    "categoryIds": None,                                 # 类目ID列表

    # ---- 配送类型 ----
    "fulfillment": [],                                   # []全部, ["fbs"]FBS, ["fbo"]FBO

    # ---- SKU ----
    "skus": [],                                          # SKU列表

    # ---- 卖家 ----
    "sellerName": [],                                    # 卖家名称列表

    # ---- 品牌 ----
    "brand": {"type": 0, "brandName": []},              # type: 0包含, 1排除, 2无品牌

    # ---- 标签 ----
    "labels": [],                                        # 标签列表

    # ---- 关键词 ----
    "keywords": [],                                      # 关键词列表

    # ---- 变体合并 ----
    "variationsMerge": 0,                                # 0不合并, 1合并

    # ---- 搜索日期 ----
    "searchDate": "",                                    # 搜索日期(YYYY-MM-DD)

    # ---- 其他 ----
    "filterRemoveProduct": True,                          # 是否过滤下架产品
    "tag": "",                                           # 标签筛选

    # ---- 分页 ----
    "page": {
        "pageNumber": 1,
        "pageSize": 100,
        "orders": [{"field": "revenue", "direction": "DESC"}]
    },

    # ============================================================
    # 循环查询控制参数（单一数据来源）
    # ============================================================
    "_config": {
        "maxPages": 2,              # 最大页数，None表示查询所有页
        "stopOnEmptyPage": True,        # 遇到空页是否停止
        "stopOnPartialPage": True,      # 遇到数据不足一页是否停止
    }
}


# ============================================================
# 便捷访问函数
# ============================================================

def get_default(key, sub_key=None):
    """
    获取 DEFAULT_PARAMS 中的默认值

    Args:
        key: 参数名 (如 "price", "monthlySales")
        sub_key: 子参数 (如 "min", "max")，仅范围参数需要

    Returns:
        参数的默认值

    示例:
        get_default("price")           # 返回 {"min": None, "max": None}
        get_default("price", "min")    # 返回 None
        get_default("pageSize")        # 返回 100
    """
    val = DEFAULT_PARAMS.get(key)
    if sub_key is not None and isinstance(val, dict):
        return val.get(sub_key)
    return val


def set_default(key, value, sub_key=None):
    """
    设置 DEFAULT_PARAMS 中的默认值

    示例:
        set_default("pageSize", 50)
        set_default("price", 100, "min")   # 设置 price.min = 100
        set_default("price", {"min": 50, "max": 200})
    """
    if sub_key is not None:
        if key not in DEFAULT_PARAMS:
            DEFAULT_PARAMS[key] = {}
        if isinstance(DEFAULT_PARAMS[key], dict):
            DEFAULT_PARAMS[key][sub_key] = value
    else:
        DEFAULT_PARAMS[key] = value


# ============================================================
# 简单参数设置函数
# ============================================================

def set_range(key, min_val=None, max_val=None):
    """
    设置范围参数

    Args:
        key: 参数名 (如 "price", "monthlySales")
        min_val: 最小值
        max_val: 最大值

    示例:
        set_range("price", 50, 200)           # 价格 50-200
        set_range("monthly_sales", 100, None) # 月销量 100+
    """
    return {key: {"min": min_val, "max": max_val}}


def set_single(key, value):
    """设置单值参数"""
    return {key: value}


def set_brand(brand_names, include=True):
    """
    设置品牌筛选

    Args:
        brand_names: 品牌名称列表
        include: True=包含, False=排除
    """
    return {"brand": {"type": 0 if include else 1, "brandName": brand_names}}


# ============================================================
# 构建参数 - 简化版
# ============================================================

def build_params(**kwargs):
    """
    构建完整查询参数（简化接口）

    用法:
        # 方式1：使用关键字参数（推荐）
        params = build_params(
            price=(50, 200),              # 范围参数：元组形式 (min, max)
            monthly_sales=100,            # 单值参数：直接传值
            brand=["Apple"],              # 品牌：列表形式（包含）
            page={"pageNumber": 1, "pageSize": 50},  # 分页：字典形式
        )

        # 方式2：使用字典
        params = build_params(**{
            "price": {"min": 50, "max": 200},
            "monthlySales": 100,
        })

    参数说明:
        范围参数 (支持元组或字典):
            reviewCount, drr, reviewRating, questionsAndAnswers, price,
            monthlyRevenue, monthlySales, monthlySalesRate, weight, volume,
            grossMargin, variants, convToCartPdp, returnCancellationRate

        单值参数:
            creationDate, categoryIds, fulfillment, skus, sellerName,
            labels, keywords, variationsMerge, searchDate, filterRemoveProduct, tag

        品牌参数:
            brand_include=[] 或 brand_exclude=[]

        分页参数:
            page=(pageNumber,) 或 (pageNumber, pageSize) 或 (pageNumber, pageSize, field, direction)
    """
    params = copy.deepcopy(DEFAULT_PARAMS)

    # 范围参数映射 (API参数名 -> 是否为范围参数)
    range_keys = {
        "reviewCount", "drr", "reviewRating", "questionsAndAnswers", "price",
        "monthlyRevenue", "monthlySales", "monthlySalesRate", "weight", "volume",
        "grossMargin", "variants", "convToCartPdp", "returnCancellationRate",
    }

    # 处理范围参数（支持函数名和API参数名）
    for func_key, api_key in [
        ("review_count", "reviewCount"), ("drr", "drr"), ("review_rating", "reviewRating"),
        ("questions_and_answers", "questionsAndAnswers"), ("price", "price"),
        ("monthly_revenue", "monthlyRevenue"), ("monthly_sales", "monthlySales"),
        ("monthly_sales_rate", "monthlySalesRate"), ("weight", "weight"), ("volume", "volume"),
        ("gross_margin", "grossMargin"), ("variants", "variants"),
        ("conv_to_cart_pdp", "convToCartPdp"), ("return_cancellation_rate", "returnCancellationRate"),
    ]:
        if func_key in kwargs:
            val = kwargs[func_key]
            if isinstance(val, tuple):
                params[api_key] = {"min": val[0], "max": val[1]}
            elif isinstance(val, dict):
                params[api_key] = val
            else:
                params[api_key] = {"min": val, "max": None}

    # 处理直接传入 API 参数名的情况（如 {"price": {"min": 10, "max": 100}}）
    # 注意：只覆盖有具体值的参数
    for key in range_keys:
        if key in kwargs:
            val = kwargs[key]
            if isinstance(val, dict):
                # 只有当传入的是有效的范围值时才覆盖
                if "min" in val or "max" in val:
                    params[key] = {"min": val.get("min"), "max": val.get("max")}
            elif isinstance(val, (int, float)):
                params[key] = {"min": val, "max": None}
            elif isinstance(val, tuple):
                params[key] = {"min": val[0], "max": val[1]}

    # 单值参数映射
    single_keys = {
        "creation_date": "creationDate",
        "category_ids": "categoryIds",
        "fulfillment": "fulfillment",
        "skus": "skus",
        "seller_name": "sellerName",
        "labels": "labels",
        "keywords": "keywords",
        "variations_merge": "variationsMerge",
        "search_date": "searchDate",
        "filter_remove_product": "filterRemoveProduct",
        "tag": "tag",
    }

    # 处理单值参数
    for func_key, api_key in single_keys.items():
        if func_key in kwargs:
            params[api_key] = kwargs[func_key]

    # 品牌参数
    if "brand_include" in kwargs:
        params["brand"] = {"type": 0, "brandName": kwargs["brand_include"]}
    if "brand_exclude" in kwargs:
        params["brand"] = {"type": 1, "brandName": kwargs["brand_exclude"]}

    # 分页参数
    if "page" in kwargs:
        page_val = kwargs["page"]
        if isinstance(page_val, dict):
            params["page"].update(page_val)
        elif isinstance(page_val, (tuple, list)):
            page_list = list(page_val)
            if len(page_list) >= 1:
                params["page"]["pageNumber"] = page_list[0]
            if len(page_list) >= 2:
                params["page"]["pageSize"] = min(page_list[1], 100)
            if len(page_list) >= 3:
                direction = page_list[3] if len(page_list) >= 4 else params["page"]["orders"][0]["direction"]
                params["page"]["orders"] = [{"field": page_list[2], "direction": direction}]

    return params


def merge_custom_params(default_params, custom_params):
    """
    合并默认参数和自定义参数

    示例:
        params = merge_custom_params(
            DEFAULT_PARAMS,
            {"price": {"min": 50, "max": 200}}
        )
    """
    result = copy.deepcopy(default_params)

    if custom_params:
        for key, value in custom_params.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    for sub_key, sub_value in value.items():
                        if sub_value is not None:
                            result[key][sub_key] = sub_value
                elif value is not None:
                    result[key] = value

    return result


# ============================================================
# 配置访问函数（从 DEFAULT_PARAMS["_config"] 读取）
# ============================================================

def get_config(key=None):
    """
    获取循环查询配置

    示例:
        get_config()                    # 返回整个 _config 字典
        get_config("maxPages")          # 返回 maxPages 的值
        get_config("stopOnEmptyPage")   # 返回 stopOnEmptyPage 的值
    """
    if key is None:
        return DEFAULT_PARAMS["_config"]
    return DEFAULT_PARAMS["_config"].get(key)

def set_config(key, value):
    """
    设置循环查询配置

    示例:
        set_config("maxPages", 10)
        set_config("stopOnEmptyPage", False)
    """
    DEFAULT_PARAMS["_config"][key] = value


# ============================================================
# 停止条件
# ============================================================

def stop_conditions(stop_page=None, stop_on_empty=None, stop_on_partial=None):
    """创建停止条件（从 DEFAULT_PARAMS['_config'] 读取默认值）"""
    config = DEFAULT_PARAMS["_config"]
    return {
        "stop_page": stop_page,
        "stop_on_empty": stop_on_empty if stop_on_empty is not None else config["stopOnEmptyPage"],
        "stop_on_partial": stop_on_partial if stop_on_partial is not None else config["stopOnPartialPage"],
    }


# ============================================================
# 便捷访问函数（兼容旧代码）
# ============================================================

def get_default_page_size():
    """获取默认每页数量"""
    return DEFAULT_PARAMS["page"]["pageSize"]

def get_default_sort_field():
    """获取默认排序字段"""
    return DEFAULT_PARAMS["page"]["orders"][0]["field"]

def get_default_sort_direction():
    """获取默认排序方向"""
    return DEFAULT_PARAMS["page"]["orders"][0]["direction"]


# ============================================================
# 兼容旧版本的参数辅助函数
# ============================================================

def review_count(min_val=None, max_val=None):
    """评论数量范围"""
    return {"reviewCount": {"min": min_val, "max": max_val}}

def drr(min_val=None, max_val=None):
    """DRR 动态评分范围"""
    return {"drr": {"min": min_val, "max": max_val}}

def review_rating(min_val=None, max_val=None):
    """商品评分范围"""
    return {"reviewRating": {"min": min_val, "max": max_val}}

def questions_and_answers(min_val=None, max_val=None):
    """问答数量范围"""
    return {"questionsAndAnswers": {"min": min_val, "max": max_val}}

def price(min_val=None, max_val=None):
    """价格范围"""
    return {"price": {"min": min_val, "max": max_val}}

def monthly_revenue(min_val=None, max_val=None):
    """月收入范围"""
    return {"monthlyRevenue": {"min": min_val, "max": max_val}}

def monthly_sales(min_val=None, max_val=None):
    """月销量范围"""
    return {"monthlySales": {"min": min_val, "max": max_val}}

def monthly_sales_rate(min_val=None, max_val=None):
    """月销售率范围"""
    return {"monthlySalesRate": {"min": min_val, "max": max_val}}

def weight(min_val=None, max_val=None):
    """重量范围(kg)"""
    return {"weight": {"min": min_val, "max": max_val}}

def volume(min_val=None, max_val=None):
    """体积范围"""
    return {"volume": {"min": min_val, "max": max_val}}

def gross_margin(min_val=None, max_val=None):
    """毛利率范围"""
    return {"grossMargin": {"min": min_val, "max": max_val}}

def variants(min_val=None, max_val=None):
    """变体数量范围"""
    return {"variants": {"min": min_val, "max": max_val}}

def conv_to_cart_pdp(min_val=None, max_val=None):
    """PDP转化率"""
    return {"convToCartPdp": {"min": min_val, "max": max_val}}

def return_cancellation_rate(min_val=None, max_val=None):
    """退货/取消率"""
    return {"returnCancellationRate": {"min": min_val, "max": max_val}}

def creation_date(date_str=None):
    """创建日期"""
    return {"creationDate": date_str}

def category_ids(category_ids_list=None):
    """类目ID列表"""
    return {"categoryIds": category_ids_list}

def fulfillment(fulfillment_list=None):
    """配送类型"""
    return {"fulfillment": fulfillment_list if fulfillment_list else []}

def skus(sku_list=None):
    """SKU列表"""
    return {"skus": sku_list if sku_list else []}

def seller_name(seller_list=None):
    """卖家名称"""
    return {"sellerName": seller_list if seller_list else []}

def brand_include(brand_names=None):
    """品牌-包含"""
    return {"brand": {"type": 0, "brandName": brand_names if brand_names else []}}

def brand_exclude(brand_names=None):
    """品牌-排除"""
    return {"brand": {"type": 1, "brandName": brand_names if brand_names else []}}

def labels(label_list=None):
    """标签列表"""
    return {"labels": label_list if label_list else []}

def keywords(keyword_list=None):
    """关键词列表"""
    return {"keywords": keyword_list if keyword_list else []}

def variations_merge(merge=0):
    """变体合并"""
    return {"variationsMerge": merge}

def search_date(date_str=None):
    """搜索日期"""
    return {"searchDate": date_str if date_str else ""}

def filter_remove_product(filter_remove=True):
    """过滤下架产品"""
    return {"filterRemoveProduct": filter_remove}

def tag(tag_str=None):
    """标签筛选"""
    return {"tag": tag_str if tag_str else ""}

def pagination(page_number=1, page_size=None, sort_field=None, sort_direction=None):
    """分页参数"""
    if page_size is None:
        page_size = get_default_page_size()
    if sort_field is None:
        sort_field = get_default_sort_field()
    if sort_direction is None:
        sort_direction = get_default_sort_direction()

    return {"page": {
        "pageNumber": page_number,
        "pageSize": min(page_size, 100),
        "orders": [{"field": sort_field, "direction": sort_direction}]
    }}

def sort_by(field, direction=None):
    """排序参数"""
    if direction is None:
        direction = get_default_sort_direction()
    return {"page": {
        "pageNumber": 1,
        "pageSize": get_default_page_size(),
        "orders": [{"field": field, "direction": direction}]
    }}

def multi_sort(orders):
    """多字段排序"""
    return {"page": {
        "pageNumber": 1,
        "pageSize": get_default_page_size(),
        "orders": orders
    }}
