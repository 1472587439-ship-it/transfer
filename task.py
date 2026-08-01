# -*- coding: utf-8 -*-
"""
Ozon 产品查询任务 - 使用者入口文件

此文件是唯一需要使用者操作的文件
"""

from ozon_product_report import run_ozon_query, save_response


def main():
    """
    主任务入口
    使用者在此修改筛选条件和参数
    """

    # ============================================================
    # 使用者配置区域
    # ============================================================

    # 筛选条件（根据需要修改）
    custom_filter = {
        # 价格范围
        # 'price': {'min': 100, 'max': 500},

        # 评论数量
        # 'reviewCount': {'min': 100},

        # 评分
        # 'reviewRating': {'min': 4.0},

        # 类目ID
        # 'categoryIds': 'xxx',

        # 关键词
        # 'keywords': ['游戏', '电子产品'],

        # 品牌
        # 'brand': {'type': 0, 'brandName': ['Sony', 'Samsung']},

        # 配送方式
        'fulfillment': ['FBS'],
    }

    # 最大拉取页数
    max_fetch_page = 1

    # ============================================================
    # 执行查询
    # ============================================================

    print("开始查询...")
    products = run_ozon_query(
        custom_filter=custom_filter,
        max_fetch_page=max_fetch_page
    )

    print(f"查询完成，共获取 {len(products)} 条商品")

    if products:
        # 保存结果
        save_response({'data': products})

    return products


if __name__ == '__main__':
    main()
