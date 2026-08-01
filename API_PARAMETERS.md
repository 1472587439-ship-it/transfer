# Ozon 产品报告 API 参数说明

## 概述

本文档详细说明 Ozon 产品报告搜索 API 的所有参数，包括数据类型、取值范围、默认值等。

---

## 请求结构

```json
{
    "filterRemoveProduct": true,
    "tag": "",
    "reviewCount": {"min": null, "max": null},
    "drr": {"min": null, "max": null},
    "reviewRating": {"min": null, "max": null},
    "questionsAndAnswers": {"min": null, "max": null},
    "price": {"min": null, "max": null},
    "monthlyRevenue": {"min": null, "max": null},
    "monthlySales": {"min": null, "max": null},
    "monthlySalesRate": {"min": null, "max": null},
    "weight": {"min": null, "max": null},
    "volume": {"min": null, "max": null},
    "grossMargin": {"min": null, "max": null},
    "variants": {"min": null, "max": null},
    "convToCartPdp": {"min": null, "max": null},
    "returnCancellationRate": {"min": null, "max": null},
    "creationDate": null,
    "categoryIds": [],
    "fulfillment": [],
    "skus": [],
    "sellerName": [],
    "brand": {"type": 0, "brandName": []},
    "labels": [],
    "keywords": [],
    "variationsMerge": 0,
    "searchDate": "",
    "page": {
        "pageNumber": 1,
        "pageSize": 100,
        "orders": [{"field": "revenue", "direction": "DESC"}]
    }
}
```

---

## 参数详细说明

### 1. 过滤商品

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `filterRemoveProduct` | boolean | 否 | `true` | 是否过滤已下架商品 |

### 2. 标签词

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `tag` | string | 否 | `""` | 标签词筛选 |

### 3. 评论数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `reviewCount.min` | integer | 否 | `null` | 最小评论数 |
| `reviewCount.max` | integer | 否 | `null` | 最大评论数 |

### 4. 广告费用份额 (DRR)

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `drr.min` | number | 否 | `null` | 最小广告费用份额 |
| `drr.max` | number | 否 | `null` | 最大广告费用份额 |

### 5. 商品评分

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `reviewRating.min` | number | 否 | `null` | 最小评分 (1-5) |
| `reviewRating.max` | number | 否 | `null` | 最大评分 (1-5) |

### 6. 问答数量 (QA)

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `questionsAndAnswers.min` | integer | 否 | `null` | 最小问答数 |
| `questionsAndAnswers.max` | integer | 否 | `null` | 最大问答数 |

### 7. 价格

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `price.min` | number | 否 | `null` | 最小价格 (卢布) |
| `price.max` | number | 否 | `null` | 最大价格 (卢布) |

### 8. 月销售额

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `monthlyRevenue.min` | number | 否 | `null` | 最小月销售额 |
| `monthlyRevenue.max` | number | 否 | `null` | 最大月销售额 |

### 9. 月销量

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `monthlySales.min` | integer | 否 | `null` | 最小月销量 |
| `monthlySales.max` | integer | 否 | `null` | 最大月销量 |

### 10. 销量增长率

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `monthlySalesRate.min` | number | 否 | `null` | 最小销量增长率 |
| `monthlySalesRate.max` | number | 否 | `null` | 最大销量增长率 |

### 11. 重量

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `weight.min` | number | 否 | `null` | 最小重量 (克) |
| `weight.max` | number | 否 | `null` | 最大重量 (克) |

### 12. 体积

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `volume.min` | number | 否 | `null` | 最小体积 (升) |
| `volume.max` | number | 否 | `null` | 最大体积 (升) |

### 13. 毛利率

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `grossMargin.min` | number | 否 | `null` | 最小毛利率 |
| `grossMargin.max` | number | 否 | `null` | 最大毛利率 |

### 14. 变体数量

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `variants.min` | integer | 否 | `null` | 最小变体数 |
| `variants.max` | integer | 否 | `null` | 最大变体数 |

### 15. 购物车转化率

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `convToCartPdp.min` | number | 否 | `null` | 最小购物车转化率 |
| `convToCartPdp.max` | number | 否 | `null` | 最大购物车转化率 |

### 16. 退货/取消率

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `returnCancellationRate.min` | number | 否 | `null` | 最小退货取消率 |
| `returnCancellationRate.max` | number | 否 | `null` | 最大退货取消率 |

### 17. 上架时间

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `creationDate` | integer/null | 否 | `null` | 上架时间筛选 |

取值说明：
| 值 | 说明 |
|---|------|
| `null` | 不筛选 |
| `1` | 近30天 |
| `3` | 近90天 |
| `6` | 近180天 |
| `12` | 近1年 |
| `24` | 近2年 |

### 18. 类目ID

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `categoryIds` | string | 否 | `""` | 用逗号分隔的类目ID字符串 |

类目ID格式：
- 单级：`15621031`
- 多级：`15621031_200000933_115949936` (父级_子级_孙级)

> **前端支持自动匹配**：输入中文/英文/俄文或类目ID，系统会自动调用本地 `seerfar.xlsx` 对照表匹配对应的类目ID。前端只需把文字传给 `run_ozon_query(categoryQueries=[...])` 即可，匹配模块会处理一切。

### 19. 配送方式

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `fulfillment` | array | 否 | `[]` | 配送方式数组，支持多选 |

可选值：
| 值 | 说明 | 类型 |
|---|------|------|
| `["OZON"]` | OZON 自配送 | 本土 |
| `["FBO"]` | FBO (仓储) | 本土 |
| `["FBS"]` | FBS (卖家仓库) | 本土 |
| `["RFBS"]` | RFBS | 跨境 |
| `["FBP"]` | FBP | 跨境 |

> 注意：可多选，例如 `["FBO", "FBS"]` 查询同时支持 FBO 和 FBS 的商品

### 20. SKU列表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `skus` | array | 否 | `[]` | SKU数组，最多10个 |

### 21. 卖家名称

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `sellerName` | array | 否 | `[]` | 卖家名称数组 |

### 22. 品牌

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `brand.type` | number | 否 | `0` | 品牌筛选类型 |
| `brand.brandName` | array | 否 | `[]` | 品牌名称数组 |

`brand.type` 取值：
| 值 | 说明 |
|---|------|
| `0` | 包含品牌 |
| `1` | 排除品牌 |
| `2` | 无品牌 |

### 23. 标签

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `labels` | array | 否 | `[]` | 标签数组 (整数) |

可选值：
| 值 | 说明 |
|---|------|
| `0` | 新品 |
| `1` | 正品 |
| `2` | 畅销品 |

### 24. 关键词

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `keywords` | array | 否 | `[]` | 关键词数组 |

### 25. 变体合并

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `variationsMerge` | number | 否 | `0` | 是否合并变体 |

取值：
| 值 | 说明 |
|---|------|
| `0` | 不合并 |
| `1` | 合并 |

### 26. 搜索日期

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `searchDate` | string | 否 | `""` | 日期范围，格式：YYYY-MM-DD |

说明：
- 不传：默认查近30天数据
- 传值：例如 `2026-04-01` 查2026年3月数据
- 仅能查近1年的数据

---

## 分页参数

### page

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page.pageNumber` | number | 是 | `1` | 分页页码 |
| `page.pageSize` | number | 是 | `100` | 每页条数，最大100 |
| `page.orders` | array | 是 | - | 排序规则 |

### orders 排序规则

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `orders[].field` | string | 是 | `revenue` | 排序字段 |
| `orders[].direction` | string | 是 | `DESC` | 排序方向 |

#### 支持的排序字段 (field)

| 值 | 说明 |
|---|------|
| `revenue` | 销售额 |
| `price` | 价格 |
| `sales` | 销量 |
| `grossMargin` | 毛利率 |
| `views` | 浏览量 |
| `sessionCountSearch` | 搜索会话数 |
| `sessionCount` | 会话数 |
| `convToCartPdp` | 购物车转化率 |
| `orderConversionRate` | 订单转化率 |
| `drr` | 广告费用份额 |
| `returnCancellationRate` | 退货取消率 |
| `missedRevenue` | 错过收入 |
| `variants` | 变体数 |
| `reviewCount` | 评论数 |
| `reviewRating` | 评分 |
| `upTime` | 上架时间 |
| `weight` | 重量 |
| `volume` | 体积 |
| `questionsAndAnswers` | 问答数 |

#### 排序方向 (direction)

| 值 | 说明 |
|---|------|
| `DESC` | 倒序 (从大到小) |
| `ASC` | 正序 (从小到大) |

---

## 代码示例

### Python 使用示例

```python
from ozon_product_report import query, save_response

# 方式1：直接传字典
params = {
    "price": {"min": 100, "max": 500},
    "monthlySales": {"min": 100},
    "fulfillment": ["FBS"],
    "labels": [0, 2],  # 新品 + 畅销品
    "brand": {"type": 0, "brandName": ["Apple"]},
    "page": {
        "pageNumber": 1,
        "pageSize": 100,
        "orders": [{"field": "sales", "direction": "DESC"}]
    }
}

result = query(custom_params=params, max_pages=5)
save_response(result)
```

### 前端参数示例

```javascript
// 前端发送的 JSON 格式
{
    "filterRemoveProduct": true,
    "tag": "",
    "price": {"min": 100, "max": 500},
    "monthlySales": {"min": 100, "max": null},
    "fulfillment": ["FBS"],
    "labels": [0, 2],
    "brand": {"type": 0, "brandName": ["Apple"]},
    "skus": [],
    "sellerName": [],
    "keywords": ["游戏"],
    "categoryIds": [],
    "creationDate": null,
    "searchDate": "",
    "variationsMerge": 0,
    "page": {
        "pageNumber": 1,
        "pageSize": 100,
        "orders": [{"field": "revenue", "direction": "DESC"}]
    },
    "_config": {
        "maxPages": 2
    }
}
```

---

## 注意事项

1. **数组参数**：所有数组参数（`categoryIds`, `skus`, `sellerName`, `keywords`, `labels`, `fulfillment`）即使为空也要发送 `[]`
2. **creationDate**：必须是整数 `1/3/6/12/24`，不是日期字符串
3. **labels**：必须是整数数组 `[0, 1, 2]`，不是字符串
4. **fulfillment**：必须是大写字符串 `["FBS", "FBO"]`
5. **brand.type**：可取值 `0`(包含)、`1`(排除)、`2`(无品牌)
6. **pageSize**：最大值为 100
7. **searchDate**：格式为 `YYYY-MM-DD`，仅能查近1年数据
