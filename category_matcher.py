# -*- coding: utf-8 -*-
"""
类目匹配模块 - 基于 seerfar.xlsx 的本地类目对照表
支持中文/英文/俄文/类目ID 任意一种方式匹配到对应类目ID
"""

import os
import re
import json
from difflib import SequenceMatcher


# ============================================================
# 路径配置
# ============================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(CURRENT_DIR, "seerfar.xlsx")
CACHE_DIR = os.path.join(CURRENT_DIR, "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "category_cache.json")


# ============================================================
# 加载类目数据
# ============================================================

def load_categories_from_excel(excel_path=None):
    """
    从 Excel 文件加载类目数据

    Returns:
        list: [{'id': '...', 'en': '...', 'ru': '...', 'zh': '...', 'parent_id': '...', 'level': int}, ...]
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("请先安装 openpyxl: pip install openpyxl")

    excel_path = excel_path or EXCEL_FILE
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.active

    categories = []
    headers = None
    for row in ws.iter_rows(values_only=True):
        if headers is None:
            headers = row
            continue
        if not row or not row[0]:
            continue

        cat_id = str(row[0]).strip() if row[0] is not None else ""
        en_name = str(row[1]).strip() if row[1] is not None else ""
        ru_name = str(row[2]).strip() if row[2] is not None else ""
        zh_name = str(row[3]).strip() if row[3] is not None else ""
        parent_id = str(row[4]).strip() if row[4] is not None else ""
        level = int(row[5]) if row[5] is not None and str(row[5]).isdigit() else 0

        categories.append({
            "id": cat_id,
            "en": en_name,
            "ru": ru_name,
            "zh": zh_name,
            "parent_id": parent_id,
            "level": level,
        })

    wb.close()
    return categories


def save_to_cache(categories, cache_path=None):
    """保存类目数据到 JSON 缓存"""
    cache_path = cache_path or CACHE_FILE
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)


def load_from_cache(cache_path=None):
    """从 JSON 缓存加载"""
    cache_path = cache_path or CACHE_FILE
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_category_tree(categories=None):
    """
    把扁平的类目列表组装成 3 级树状结构, 只保留有子级的中间层

    Returns:
        {
          "levels": {1: [...], 2: [...], 3: [...]},
          "tree": [
              {
                  "id": "...", "zh": "...", "en": "...", "ru": "...",
                  "children": [
                      {
                          "id": "...", "zh": "...", ...,
                          "children": [
                              {"id": "...", "zh": "...", ...}
                          ]
                      }
                  ]
              }
          ]
        }
    """
    cats = categories if categories is not None else load_categories()
    if not cats:
        return {"levels": {"1": [], "2": [], "3": []}, "tree": []}

    levels = {"1": [], "2": [], "3": []}
    by_parent = {}
    by_id = {}
    for c in cats:
        by_id[c["id"]] = c
        lk = str(c.get("level", 3))
        if lk not in levels:
            lk = "3"
        levels[lk].append(c)
        by_parent.setdefault(c.get("parent_id", "0"), []).append(c)

    def build_node(cat):
        node = {
            "id": cat["id"],
            "zh": cat.get("zh", ""),
            "en": cat.get("en", ""),
            "ru": cat.get("ru", ""),
            "parent_id": cat.get("parent_id", "0"),
            "level": cat.get("level", 0),
            "has_children": False,
            "children": [],
        }
        children = by_parent.get(cat["id"], [])
        for child in children:
            node["children"].append(build_node(child))
            node["has_children"] = True
        return node

    tree = []
    for c in levels["1"]:
        tree.append(build_node(c))

    return {"levels": levels, "tree": tree}


def load_categories():
    """
    加载类目数据 (优先使用缓存)

    Returns:
        list: 类目列表
    """
    categories = load_from_cache()
    if categories:
        return categories

    categories = load_categories_from_excel()
    save_to_cache(categories)
    return categories


def rebuild_cache():
    """强制从 Excel 重建缓存"""
    categories = load_categories_from_excel()
    save_to_cache(categories)
    return categories


# ============================================================
# 构建索引
# ============================================================

def _build_index(categories):
    """
    构建多语言索引:
        - exact_index: key(原文小写) -> [cat_id, ...]
        - id_index: id -> category dict
        - name_index: 中/英/俄文小写 -> category dict
    """
    exact_index = {}   # 多语种原文 -> 类目对象
    id_index = {}

    for cat in categories:
        cid = cat["id"]
        id_index[cid] = cat

        for key in (cat["zh"], cat["en"], cat["ru"]):
            if not key:
                continue
            k = key.lower()
            # 同一原文可能对应多个类目(如 Clothing 在多个层级)
            exact_index.setdefault(k, []).append(cat)

    return exact_index, id_index


# ============================================================
# 匹配函数
# ============================================================

def _normalize(text):
    """去除多余空白并转小写"""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def _similarity(a, b):
    """计算两个字符串的相似度 0~1"""
    return SequenceMatcher(None, a, b).ratio()


def match_category(query_text, categories=None, threshold=0.6, lang="auto"):
    """
    匹配单个类目

    Args:
        query_text: 查询字符串 (中文/英文/俄文/类目ID)
        categories: 类目列表 (None 则自动加载)
        threshold: 模糊匹配相似度阈值 (0~1)
        lang: 限定语言 "zh" / "en" / "ru" / "auto"

    Returns:
        list: 匹配的类目字典列表 (按相似度降序)
              [] 表示未匹配到
    """
    if not query_text:
        return []

    if categories is None:
        categories = load_categories()

    exact_index, id_index = _build_index(categories)
    query_norm = _normalize(query_text)

    # 1) 精确按类目ID匹配
    if query_text in id_index:
        return [id_index[query_text]]

    # 2) 精确按名称匹配 (中/英/俄)
    if query_norm in exact_index:
        matches = exact_index[query_norm]
        # 如果限定语言, 优先该语言
        if lang != "auto":
            lang_key = {"zh": "zh", "en": "en", "ru": "ru"}[lang]
            same_lang = [m for m in matches if m.get(lang_key, "").lower() == query_norm]
            if same_lang:
                return same_lang
        return matches

    # 3) 模糊匹配
    scored = []
    lang_key = None if lang == "auto" else {"zh": "zh", "en": "en", "ru": "ru"}[lang]
    for cat in categories:
        candidates = []
        if lang_key:
            candidates.append((cat.get(lang_key, ""), lang_key))
        else:
            candidates.extend([(cat["zh"], "zh"), (cat["en"], "en"), (cat["ru"], "ru")])

        best = 0.0
        best_field = ""
        for name, field in candidates:
            if not name:
                continue
            score = _similarity(query_norm, name.lower())
            if score > best:
                best = score
                best_field = field

        if best >= threshold:
            scored.append((best, best_field, cat))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, _, c in scored]


def match_categories(queries, categories=None, threshold=0.6, lang="auto"):
    """
    批量匹配类目

    Args:
        queries: 字符串列表 (可以是中/英/俄文/类目ID 混合)
        categories: 类目列表
        threshold: 模糊匹配阈值
        lang: 限定语言

    Returns:
        dict: {
            "matched":   [{"query": "...", "id": "...", "name_zh": "...", "name_en": "...", "name_ru": "..."}, ...],
            "unmatched": ["..."]
        }
    """
    if categories is None:
        categories = load_categories()

    matched = []
    unmatched = []
    seen_ids = set()  # 去重

    for q in queries:
        if not q or not str(q).strip():
            continue
        q_str = str(q).strip()
        results = match_category(q_str, categories=categories, threshold=threshold, lang=lang)
        if results:
            # 默认取第一个最佳匹配
            cat = results[0]
            if cat["id"] not in seen_ids:
                seen_ids.add(cat["id"])
                matched.append({
                    "query": q_str,
                    "id": cat["id"],
                    "name_zh": cat["zh"],
                    "name_en": cat["en"],
                    "name_ru": cat["ru"],
                    "level": cat["level"],
                    "parent_id": cat["parent_id"],
                    "score": 1.0 if len(results) == 1 else None,
                    "candidates": len(results),
                })
        else:
            unmatched.append(q_str)

    return {
        "matched": matched,
        "unmatched": unmatched,
    }


# ============================================================
# 高层接口 - 把匹配结果转成 API 请求需要的格式
# ============================================================

def build_category_ids_param(queries, categories=None, threshold=0.6, lang="auto"):
    """
    把用户输入的类目查询 (中/英/俄/ID) 转成 API 需要的 categoryIds

    Ozon API 的 categoryIds 是字符串数组:
    [
      "15621031",
      "15621031_200000933_115949936"
    ]

    Returns:
        tuple: (ids_list, detail)
            ids_list: list[str]  类目ID数组, 例如 ["15621031", "15621031_200000933"]
            detail:    dict       {"matched": [...], "unmatched": [...]}
    """
    result = match_categories(queries, categories=categories, threshold=threshold, lang=lang)
    ids = [m["id"] for m in result["matched"]]
    return ids, result


# ============================================================
# 搜索接口 (前端下拉选择)
# ============================================================

def search_categories(keyword, categories=None, limit=50, lang="auto"):
    """
    模糊搜索类目 (用于前端下拉搜索)

    Args:
        keyword: 关键词 (任意语言)
        limit: 返回数量
        lang: 限定语言

    Returns:
        list: 匹配的类目列表
    """
    if categories is None:
        categories = load_categories()
    if not keyword or not str(keyword).strip():
        return []

    results = match_category(str(keyword).strip(), categories=categories, threshold=0.3, lang=lang)
    # 去重 (按 id)
    seen = set()
    unique = []
    for cat in results:
        if cat["id"] in seen:
            continue
        seen.add(cat["id"])
        unique.append(cat)
        if len(unique) >= limit:
            break
    return unique


def get_all_categories(categories=None):
    """获取所有类目 (用于前端下拉)"""
    if categories is None:
        categories = load_categories()
    return categories


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    print("=== 重建缓存 ===")
    cats = rebuild_cache()
    print(f"已加载 {len(cats)} 个类目")

    print("\n=== 中文匹配 ===")
    print(match_categories(["服装", "防磨衣", "压缩紧身衣"]))

    print("\n=== 英文匹配 ===")
    print(match_categories(["Clothing", "Rashguard"], lang="en"))

    print("\n=== 俄文匹配 ===")
    print(match_categories(["Одежда"], lang="ru"))

    print("\n=== 类目ID匹配 ===")
    print(match_categories(["15621031", "15621031_200000933_115949936"]))

    print("\n=== 模糊匹配 ===")
    print(match_categories(["服裝"]))  # 繁简体差异

    print("\n=== 生成 categoryIds 参数 ===")
    ids, detail = build_category_ids_param(["服装", "Rashguard"])
    print(f"categoryIds = '{ids}'")
    print(f"详情: {json.dumps(detail, ensure_ascii=False, indent=2)}")
