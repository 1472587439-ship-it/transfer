# Playwright 网页爬虫

基于 Playwright 的自动化网页爬虫工具，可以爬取任意网址的页面信息。

## 功能特点

- 使用 Playwright 模拟真实浏览器访问
- 自动提取页面标题、元数据、标题标签
- 提取所有链接和图片信息
- 提取列表和表格数据
- 数据保存为 JSON 格式到 output 文件夹
- 支持交互式多次爬取

## 安装

1. 安装 Python 依赖：

```bash
pip install -r requirements.txt
```

2. 安装 Playwright 浏览器驱动：

```bash
playwright install chromium
```

## 使用方法

```bash
python crawler.py
```

运行后输入要爬取的网址，程序会自动爬取页面信息并保存到 output 文件夹。

按 `Ctrl+C` 或直接回车可退出程序。

## 爬取内容

爬取的数据包括：

- **标题 (title)**: 页面标题
- **元数据 (metadata)**: meta 标签内容（description, keywords 等）
- **标题标签 (headings)**: h1-h6 标题内容
- **链接 (links)**: 页面中的链接（最多 100 条）
- **图片 (images)**: 图片信息（alt、src、尺寸）
- **列表 (lists)**: 有序和无序列表
- **表格 (tables)**: 表格数据（表头和行）

## 输出文件

爬取的数据保存在 `output/` 文件夹中，文件名格式为：

```
{域名}_{时间戳}.json
```

例如：`example_com_2026-07-30T15-48-00-000.json`

## 项目结构

```
crawler/
├── crawler.py        # 爬虫主程序
├── requirements.txt  # Python 依赖
├── output/          # 爬取结果存放目录
└── README.md        # 使用说明
```

## 依赖

- [playwright](https://playwright.dev/python/) - 浏览器自动化工具
