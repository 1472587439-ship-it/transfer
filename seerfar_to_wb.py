"""
seerfar_to_wb.py
================
对外唯一函数:
    lookup_wb_subjectid(seerfar_id) -> Optional[int]

用法:
    from seerfar_to_wb import lookup_wb_subjectid
    wb_id = lookup_wb_subjectid("15621031_200000933_115949936")
    # wb_id 是 int (e.g. 2546)，没匹配上返回 None。

行为:
    - 懒加载: 第一次调用时从 cache/seerfar_to_wb_cache.json 读入内存，之后走纯 dict 查询，无文件 I/O。
    - 缓存进程内单例，重复调用零成本。
    - 入参兼容 str / int / 带前后空白的字符串。
    - 没找到或 wb_subjectID 为空，返回 None（不抛异常）。
    - 如果缓存文件不存在，抛 FileNotFoundError，并提示先运行 build_cache.py。
"""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Optional, Union

_CACHE_FILE = Path(__file__).resolve().parent / "cache" / "seerfar_to_wb_cache.json"

_lock = Lock()
_entries: dict[str, Optional[int]] | None = None


def _ensure_loaded() -> dict[str, Optional[int]]:
    """线程安全地懒加载缓存，返回 {seerfar_id: wb_subjectID 或 None} 的精简字典。"""
    global _entries
    if _entries is not None:
        return _entries

    with _lock:
        if _entries is not None:
            return _entries

        if not _CACHE_FILE.exists():
            raise FileNotFoundError(
                f"缓存文件不存在: {_CACHE_FILE}\n"
                f"请先在同一目录下运行: python build_cache.py"
            )

        with _CACHE_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        entries = raw.get("entries", {})

        # 投影: 只保留查找需要的字段，内存更小
        _entries = {sid: (rec.get("wb_subjectID") if isinstance(rec, dict) else None)
                    for sid, rec in entries.items()}
        return _entries


def lookup_wb_subjectid(seerfar_id: Union[str, int]) -> Optional[int]:
    """
    根据 seerfar_id 查找对应的 wb_subjectID。

    参数:
        seerfar_id: 例如 "15621031" / "15621031_200000933" / "15621031_200000933_115949936"

    返回:
        int  - 匹配到的 wb_subjectID（已从 float 规范化为 int）
        None - 未匹配，或该条目本身就是 parent-only（无 subjectID）
    """
    if seerfar_id is None:
        return None
    sid = str(seerfar_id).strip()
    if not sid:
        return None
    return _ensure_loaded().get(sid)


def reload_cache() -> None:
    """强制重新读盘。当外部更新了缓存文件时调用。"""
    global _entries
    with _lock:
        _entries = None
