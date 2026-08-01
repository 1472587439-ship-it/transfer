"""
build_cache.py
================
读取 seerfar_to_wb_map_v3.xlsx，在 cache/ 下生成本地匹配表。

输出: cache/seerfar_to_wb_cache.json
        {
          "_meta": { source_file, built_at, row_count, ... },
          "entries": { "<seerfar_id>": { ...全列... }, ... }
        }

设计要点
--------
- xlsx 中尾部带非数据行(空行 / 中文说明)，先过滤。
- seerfar_id 唯一: 9773 行 -> 9773 个唯一键，零冲突，可直接做 dict key。
- wb_subjectID 在源文件里是 float（如 2546.0），本程序统一存为 int 或 null，
  使用方直接拿到整数或 None。
- wb_subjectName / wb_parentName 等 string 字段统一 str；NaN -> null。
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE / "seerfar_to_wb_map_v3.xlsx"
CACHE_DIR = HERE / "cache"
OUT = CACHE_DIR / "seerfar_to_wb_cache.json"

ID_PATTERN = re.compile(r"^\d+(_\d+)*$")


def _clean_value(v):
    """把 pandas/numpy 标量转成可 JSON 序列化的 Python 原生类型。"""
    if v is None:
        return None
    if isinstance(v, float):
        if pd.isna(v):
            return None
        return int(v) if v.is_integer() else v
    if isinstance(v, (int,)):
        if pd.isna(v):
            return None
        return v
    if isinstance(v, str):
        return v
    # numpy scalar -> 原生
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    return str(v)


def build():
    CACHE_DIR.mkdir(exist_ok=True)
    df = pd.read_excel(SRC)

    valid_ids = df["seerfar_id"].astype(str).str.match(ID_PATTERN, na=False)
    df = df[valid_ids].copy()

    # wb_subjectID 浮点 -> 整数（可空）
    rows: dict[str, dict] = {}
    for _, r in df.iterrows():
        sid = str(r["seerfar_id"]).strip()
        rows[sid] = {col: _clean_value(r[col]) for col in df.columns}

    payload = {
        "_meta": {
            "source_file": SRC.name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "row_count": len(rows),
            "schema": list(df.columns),
            "key": "seerfar_id",
            "note": "wb_subjectID 为 int 或 null；其余字段按源表保留。",
        },
        "entries": rows,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}  ({len(rows)} entries, {OUT.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    build()
