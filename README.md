# Playwright 网页爬虫

基于 Playwright 的自动化网页爬虫工具，可以爬取任意网址的页面信息。

## 功能特点

- 使用 Playwright 模拟真实浏览器访问
- 自动提取页面标题、元数据、标题标签
- 提取所有链接和图片信息
- 提取列表和表格数据
- 数据保存为 JSON 格式到 output 文件夹
- 支持交互式多次爬取
- **文件夹监控模式**：持续监控文件夹，新文件自动爬取
- **WB ID 映射**：自动根据分类 ID 查询对应的 WB subjectID

## 安装

1. 安装 Python 依赖：

```bash
pip install -r requirements.txt
```

2. 安装 Playwright 浏览器驱动：

```bash
playwright install chromium
```

3. 生成 WB 分类映射缓存（首次使用）：

```bash
python build_cache.py
```

## 使用方法

### 交互模式

```bash
python crawler.py
```

运行后输入要爬取的网址，程序会自动爬取页面信息并保存到 output 文件夹。

按 `Ctrl+C` 或直接回车可退出程序。

### 单文件批量模式

```bash
python crawler.py --batch urls.json
```

### 文件夹批量模式

```bash
python crawler.py --folder test
```

处理 `test` 文件夹下所有 JSON 文件。

### 守护进程模式（持续监控）

```bash
python crawler.py --folder test --daemon
# 或简写
python crawler.py --folder test -d
```

- 爬取完当前文件后不退出
- 每 10 秒检查一次文件夹
- 发现新 JSON 文件自动爬取
- 按 `Ctrl+C` 安全退出

### 断点续传

```bash
python crawler.py --folder test --resume
```

从上次中断的位置继续爬取。

### 强制覆盖

```bash
python crawler.py --folder test --force
```

强制重新爬取所有商品，忽略已有结果。

## 爬取内容

爬取的数据包括：

- **标题 (title)**: 页面标题
- **元数据 (metadata)**: meta 标签内容（description, keywords 等）
- **标题标签 (headings)**: h1-h6 标题内容
- **链接 (links)**: 页面中的链接（最多 100 条）
- **图片 (images)**: 图片信息（alt、src、尺寸）
- **列表 (lists)**: 有序和无序列表
- **表格 (tables)**: 表格数据（表头和行）
- **WB ID (wbId)**: 根据 Seerfar 分类 ID 映射的 WB subjectID

## 输出文件

爬取的数据保存在 `output/` 文件夹中，文件名格式为：

```
{域名}_{时间戳}.json
```

例如：`example_com_2026-07-30T15-48-00-000.json`

### 文件夹模式输出

处理完成的文件会自动重命名：
- `1.json` → `w_1.json`（全部成功）
- `1.json` 保持原名（部分失败）

## WB ID 映射模块

### seerfar_to_wb.py

根据 Seerfar 商品分类 ID 查询对应的 WB subjectID。

**用法：**

```python
from seerfar_to_wb import lookup_wb_subjectid

# 查询
wb_id = lookup_wb_subjectid("15621031_200000933_115949936")
# 返回: int 或 None
```

**特点：**
- 懒加载：首次调用时读入内存
- 线程安全
- 重复调用零开销

### build_cache.py

从 Excel 映射表生成本地缓存。

```bash
python build_cache.py
```

输出：`cache/seerfar_to_wb_cache.json`

## 项目结构

```
crawler/
├── crawler.py              # 爬虫主程序
├── build_cache.py          # WB 分类映射缓存构建脚本
├── seerfar_to_wb.py        # WB ID 查询模块
├── requirements.txt        # Python 依赖
├── cache/                  # 缓存目录
│   └── seerfar_to_wb_cache.json
├── cookies/                # Cookie 存储目录
├── output/                 # 爬取结果存放目录
└── README.md               # 使用说明
```

## 依赖

- [playwright](https://playwright.dev/python/) - 浏览器自动化工具
- [pandas](https://pandas.pydata.org/) - 数据处理（build_cache.py 需要）
