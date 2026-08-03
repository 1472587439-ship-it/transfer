# transfer

> **两套系统共存**的混合仓库：
> - **Python 部分**：Ozon 商品爬虫 + Flask 服务（采集、查询、类目匹配）
> - **Java 部分**：Wildberries 商品管理后台（wb-admin，前端 + 后端）
>
> 两套系统通过 **`output/` 目录**的文件名约定（`w_q_web_*.json`）进行数据交换：Python 爬虫写 → Java 后端读。

---

## 1. 目录结构

```
transfer/
├── README.md                       # 本文件
├── .gitignore                      # Java + Python 合并的忽略规则
├── .gitattributes                  # 换行符规则（mvnw LF、*.cmd CRLF）
│
├── pom.xml                         # ← Java 后端（wb-backend）Maven 配置
├── mvnw / mvnw.cmd                 # Maven Wrapper（免装 Maven）
├── .mvn/                           # Maven Wrapper 配置
│
├── src/                            # ← Java 后端（Spring Boot 4.1.0，Java 17）
│   ├── main/
│   │   ├── java/com/example/wb/
│   │   │   ├── WbApplication.java
│   │   │   ├── config/WebConfig.java
│   │   │   ├── controller/        # RootController / WbApiController / OutputController
│   │   │   ├── service/           # WbApiService / WbRateLimiter / OutputScannerService
│   │   │   ├── entity/Shop.java
│   │   │   └── dto/               # ApiResult / BarcodeRequest / CardList* / ...
│   │   └── resources/
│   │       └── application.yml    # 端口 8080；output.dir = ${user.dir}/output
│   └── test/...
│
├── frontend/                       # ← wb-admin 前端（Vue 3 + Vite 6）
│   ├── package.json
│   ├── vite.config.js              # 5173，/api → 8080
│   ├── index.html
│   └── src/
│       ├── main.js / App.vue / styles.css
│       ├── api/wb.js              # 全部 /api 请求封装
│       ├── composables/           # useToast / useTaskQueue / useShop / useCards / useWarehouse / useProductCenter
│       ├── utils/cards.js
│       └── components/
│           ├── TaskStatusBar.vue
│           └── pages/             # UploadPage / ProductCenterPage / ShopPage / WarehousePage
│
├── output/                         # ← 数据交换目录（爬虫产出的 JSON 落到这里）
│   ├── w_q_web_*.json              # 爬虫产物（Java 后端扫描读取）
│   ├── index.json / latest.json    # 爬虫索引
│   └── .daemon_state.json          # 守护进程状态
│
├── cache/                          # 爬虫缓存
├── cookies/                        # 爬虫 Cookie
├── templates/                      # 爬虫使用的模板
│
├── crawler.py                # Ozon 爬虫
├── server.py                # Flask 服务（端口 5000）
├── api_config.py             # 爬虫 API 配置
├── category_matcher.py       # 类目匹配器
├── ozon_product_report.py    # Ozon 报告脚本
├── seerfar_to_wb.py          # seerfar → wb 转换脚本
├── seerfar.xlsx              # 原始数据
├── build_cache.py             # 缓存构建
├── task.py                    # 选品任务
├── main.py                    # 主入口
├── proxies.txt.example        # 代理示例
├── requirements.txt           # Python 依赖
├── all-start.bat              # 全栈一键启动 (Python + Java + 前端, 4 个窗口)
├── all-stop.bat               # 全栈一键停止
├── python-start.bat           # Python 单独启动 (Flask + 爬虫 → 端口 5000)
├── task_front.html            # 选品前端页面
└── server.log                 # Flask 运行日志
```

---

## 2. 启动方式

### 2.1 全栈一键启动（推荐）

**两套系统是一个完整的闭环**——Python 爬虫写 `output/`，Java 后端读 `output/`，前端通过后端展示并触发起飞流程。所以请用 `all-start.bat` 把全部 4 个服务一次拉起来。

```bash
all-start.bat
```

启动后会拉起 4 个独立窗口：

| 窗口标题 | 内容 | 端口 |
|---------|------|------|
| `Ozon` | Flask 服务（提供 Ozon 商品查询接口） | 5000 |
| `Crawler` | Ozon 爬虫（守护模式，产出 `output/w_q_web_*.json`） | - |
| `WB-Backend` | Spring Boot 后端（扫描 `output/` 并提供 wb-admin API） | 8080 |
| `WB-Frontend` | Vite 前端开发服务器 | 5173 |

脚本会：
1. 检查 Python / Node / Java / mvnw.cmd / 前端依赖
2. 清理被占用的端口 5000 / 8080 / 5173
3. 依次启动 4 个窗口
4. 轮询后端端口（最长 45 秒），起来后自动打开 `http://localhost:5173`

**一键停止全部**：

```bash
all-stop.bat
```

按窗口标题 + 端口两轮清理，一次性关掉所有 4 个服务。

### 2.2 Python 部分（Ozon 爬虫 + Flask 服务）

**单独跑 Python（调试用）**：

```bash
python-start.bat
```

只启动 `Ozon`（Flask 5000）+ `Crawler`（爬虫）两个窗口，**不启动 Java 后端和前端**。调试 Python 服务的入口。

**手动启动**：

```bash
# 终端 1：Flask 服务
python server.py

# 终端 2：爬虫（普通模式）
python crawler.py --folder output

# 终端 2（备选）：爬虫（守护模式）
python crawler.py --folder output --daemon
```

**依赖安装**：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2.3 Java 后端部分（wb-admin）

**手动启动**：

```bash
# 后端（Spring Boot，端口 8080）
mvnw.cmd spring-boot:run

# 前端（Vite dev server，端口 5173）—— 另开终端
cd frontend
npm install
npm run dev
```

浏览器访问 `http://localhost:5173`，前端会自动通过 Vite 代理把 `/api/*` 转发到 `http://localhost:8080`。

**生产构建**：

```bash
# 1. 构建后端 jar
mvnw.cmd clean package

# 2. 构建前端
cd frontend
npm run build
# 产物在 frontend/dist/

# 3. 单独运行后端
java -jar target/wb-backend-0.0.1-SNAPSHOT.jar
```

---

## 3. 两套系统如何衔接

```
┌─────────────────┐                 ┌──────────────────┐
│  Python 爬虫    │  写 JSON 文件   │  Java 后端       │
│  (crawler.py)   │ ───────────────▶│  OutputScanner   │
│                 │  output/        │  Service         │
│  Ozon 商品采集  │  w_q_web_*.json │  扫描 + 解析     │
└─────────────────┘                 │  + markHit 回写  │
                                    └──────────┬───────┘
                                               │
                                               ▼
                                    ┌──────────────────┐
                                    │  Vue 前端        │
                                    │  ProductCenterPage│
                                    │  展示未上架商品   │
                                    └──────────────────┘
```

**关键约定**：

1. **文件名格式**：`w_q_web_<YYYYMMDD>_<HHMMSS>.json`
2. **JSON 结构**（两种都支持）：
   - **Ozon 平铺**：`{vendorCode, title, skus, ...}`
   - **嵌套变体**：`{entries: [{variants: [...]}]}`
3. **hit 标记**：Java 后端在商品上架成功后会在 JSON 内的 `hit` 数组追加店铺名；爬虫重跑会**重新生成 JSON**，**hit 标记会丢**（这是设计上可接受的：跑了新数据，旧标记就废了）

---

## 4. 关键配置

### 4.1 `src/main/resources/application.yml`

```yaml
spring:
  application:
    name: wb-admin

server:
  port: 8080

wb:
  api:
    base-url: "https://content-api.wildberries.ru"
    price-url: "https://discounts-prices-api.wildberries.ru/api/v2/upload/task"

output:
  dir: ${user.dir}/output             # 扫描产物目录
```

### 4.2 端口分配与一键启动

| 端口 | 服务 | 启动方式 |
|------|------|---------|
| 5000 | Flask 服务（Python） | `all-start.bat` 或 `python-start.bat` |
| 8080 | Spring Boot 后端（Java） | `all-start.bat` 或 `mvnw.cmd spring-boot:run` |
| 5173 | Vite dev server（前端） | `all-start.bat` 或 `cd frontend && npm run dev` |

**一键启动 / 停止脚本**：

| 脚本 | 用途 | 启动的服务 |
|------|------|----------|
| `all-start.bat` | **全栈启动**（推荐） | Ozon + Crawler + WB-Backend + WB-Frontend |
| `all-stop.bat` | 全栈停止 | 关闭上面 4 个服务的窗口 |
| `python-start.bat` | 仅调试 Python | Ozon + Crawler |

> **建议**：除非只调试 Python，否则都用 `all-start.bat` —— 两套系统是数据闭环，缺一会导致 wb-admin 商品中心一直空。

---

## 5. 常见操作

### 5.1 重置商品中心（清空所有 hit 标记）

```bash
# 删掉所有 output/w_q_web_*.json
# 爬虫会自动重新生成
rm output/w_q_web_*.json
```

### 5.2 重置前端店铺 token

浏览器 DevTools → Application → Local Storage → 删除 `wb-admin-shops`

### 5.3 查看后端日志

```bash
# 实时日志（如果用 mvnw.cmd spring-boot:run 启动）
# 直接在跑命令的终端看

# 或者用 java -jar 启动后，日志写在哪看 application.yml 是否配了 logging.file
```

### 5.4 WB 接口是否被限流

后端日志里 grep `429`：

```bash
# Windows PowerShell
Select-String -Path backend.log -Pattern "429"
```

---

## 6. 已知风险 / 遗留 TODO

1. **Spring Boot 4.1.0 / `starter-webmvc`**：官方 starter 名是 `spring-boot-starter-web`，4.x 是不是改名字了？需要核实（见 `pom.xml`）。
2. **Java 后端无鉴权**：`/api/**` 全部裸奔，Token 由前端持有透传。如果公网部署必须加 JWT / OAuth / API Key。
3. **`/api/output/mark` 写文件无锁**：多实例部署会写坏 JSON。
4. **孤儿代码未清理**：`entity/Shop.java`、`dto/ShopCreateRequest.java`、`dto/ShopUpdateRequest.java` 没有引用。
5. **前端无路由**：5 个页面通过 `App.vue` 的 `v-show` 切换。
6. **店铺数据无后端**：只存浏览器 localStorage，换浏览器就丢。

---

## 7. 变更记录

- **2026-08-03**：合并 `upload/` 进 `transfer/` 根目录
  - `upload/src/` → `transfer/src/`
  - `upload/pom.xml` → `transfer/pom.xml`（artifactId 改为 `wb-backend`，name 改为 `wb-backend`）
  - `upload/frontend/` → `transfer/frontend/`
  - `application.yml` 中 `output.dir` 从 `${user.dir}/wb-output` 改为 `${user.dir}/output`
  - 删除 `upload/.git/`、`upload/.idea/`、`upload/target/`、`upload/wb-output/` 等中间产物
  - 合并 `upload/.gitignore` 与 Python 项目的 `.gitignore` 规则
