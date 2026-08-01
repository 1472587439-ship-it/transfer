"""
Playwright 网页爬虫
基于 Playwright + stealth + Cookie 的反检测爬虫工具
"""

import os
import sys
import json
import re
import time
import random
import threading
import signal
from datetime import datetime
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth

# 导入 WB ID 映射查询模块
from seerfar_to_wb import lookup_wb_subjectid


def remove_urls_from_text(text):
    """移除文本中的链接"""
    if not text:
        return text
    # 匹配常见 URL 格式
    text = re.sub(r'https?://\S+', '', text)
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    return text


OUTPUT_DIR = os.path.join(os.getcwd(), 'output')
COOKIE_FILE = os.path.join(os.getcwd(), 'cookies.json')
COOKIES_DIR = os.path.join(os.getcwd(), 'cookies')
PROXIES_FILE = os.path.join(os.getcwd(), 'proxies.txt')  # 代理列表文件
SWITCH_INTERVAL = 10  # 每爬取10个商品切换一次Cookie
COOKIE_SWITCH_THRESHOLD = 3  # 连续3个403就切换Cookie
STATE_FILE = os.path.join(os.getcwd(), '.crawler_state.json')  # 暂停状态保存文件

# 频率控制（避免被反爬检测）
REQUEST_DELAY_MIN = 5  # 请求最小间隔（秒）
REQUEST_DELAY_MAX = 15  # 请求最大间隔（秒）
PAGE_READ_TIME_MIN = 3  # 页面打开后最小停留时间（秒）
PAGE_READ_TIME_MAX = 8  # 页面打开后最大停留时间（秒）
SCROLL_COUNT_MIN = 2  # 模拟浏览的滚动次数（最少）
SCROLL_COUNT_MAX = 5  # 模拟浏览的滚动次数（最多）

# 随机 User-Agent 列表（模拟不同真实 Chrome 用户）
REALISTIC_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    # 带 OPR 的
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 OPR/113.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 OPR/114.0.0.0',
]

def get_random_user_agent():
    """每次随机返回一个真实 User-Agent"""
    return random.choice(REALISTIC_USER_AGENTS)

# 代理失败重试
PROXY_MAX_FAILS = 3  # 同一个代理失败次数达到这个就跳过


class CrawlerStateManager:
    """爬虫状态管理器 - 支持暂停/恢复功能"""

    def __init__(self, state_file=STATE_FILE):
        self.state_file = state_file
        self.is_paused = False
        self.is_interrupted = False
        self.current_index = 0  # 当前爬取到第几个商品
        self.total_count = 0   # 总共要爬取的数量
        self.batch_file = None  # 当前批次文件
        self.crawled_urls = set()  # 已爬取的URL集合
        self.failed_urls = []  # 失败的URL列表
        self._lock = threading.Lock()

    def save_state(self, batch_file, current_index, total_count, crawled_urls, failed_urls=None):
        """保存当前爬取状态到文件"""
        with self._lock:
            state = {
                'batch_file': batch_file,
                'current_index': current_index,
                'total_count': total_count,
                'crawled_urls': list(crawled_urls),
                'failed_urls': failed_urls or [],
                'timestamp': datetime.now().isoformat()
            }
            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                print(f'\n✅ 状态已保存: {self.state_file}')
            except Exception as e:
                print(f'保存状态失败: {e}')

    def load_state(self):
        """从文件加载之前保存的状态"""
        if not os.path.exists(self.state_file):
            return None
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            print(f'\n📂 找到已保存的状态文件:')
            print(f'   文件: {os.path.basename(state.get("batch_file", "unknown"))}')
            print(f'   进度: {state.get("current_index", 0)}/{state.get("total_count", 0)}')
            print(f'   已爬取: {len(state.get("crawled_urls", []))} 个商品')
            print(f'   失败: {len(state.get("failed_urls", []))} 个')
            print(f'   保存时间: {state.get("timestamp", "unknown")}')
            return state
        except Exception as e:
            print(f'加载状态失败: {e}')
            return None

    def clear_state(self):
        """清除保存的状态"""
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
                print('状态文件已清除')
            except Exception as e:
                print(f'清除状态失败: {e}')

    def pause(self):
        """暂停爬取"""
        with self._lock:
            self.is_paused = True
            print('\n⏸️  爬虫已暂停（按 Ctrl+C 两次可完全退出）')

    def resume(self):
        """恢复爬取"""
        with self._lock:
            self.is_paused = False
            self.is_interrupted = False
            print('\n▶️  爬虫已恢复')

    def wait_if_paused(self):
        """如果处于暂停状态，等待恢复"""
        while True:
            with self._lock:
                if not self.is_paused:
                    return True
            time.sleep(0.5)


class ProxyManager:
    """代理池管理器 - 支持 HTTP/HTTPS/SOCKS5"""

    def __init__(self, proxies_file=PROXIES_FILE):
        self.proxies_file = proxies_file
        self.proxies = []  # [{'server': 'ip:port', 'username': '...', 'password': '...', 'protocol': 'socks5'}, ...]
        self.current_index = 0
        self.fail_count = {}  # 每个代理的失败次数
        self.load_proxies()

    def load_proxies(self):
        """加载代理列表，每行一个，支持格式：
        - socks5://user:pass@ip:port
        - http://user:pass@ip:port
        - ip:port:user:pass
        - ip:port
        """
        self.proxies = []
        if not os.path.exists(self.proxies_file):
            print(f'ℹ️  未找到 {self.proxies_file}，不使用代理')
            return

        try:
            with open(self.proxies_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    proxy = self._parse_proxy(line)
                    if proxy:
                        self.proxies.append(proxy)
                    else:
                        print(f'⚠️  第 {line_num} 行代理格式错误: {line}')

            print(f'🔌 加载了 {len(self.proxies)} 个代理')
        except Exception as e:
            print(f'加载代理文件失败: {e}')

    def _parse_proxy(self, line):
        """解析代理字符串"""
        try:
            from urllib.parse import urlparse

            # 格式1: protocol://user:pass@ip:port
            if '://' in line:
                parsed = urlparse(line)
                protocol = parsed.scheme.lower()
                if protocol not in ('http', 'https', 'socks4', 'socks5'):
                    return None
                server = f'{parsed.hostname}:{parsed.port}'
                proxy = {
                    'server': server,
                    'username': parsed.username,
                    'password': parsed.password,
                    'protocol': protocol,
                    'raw': line
                }
            # 格式2: ip:port:user:pass
            elif line.count(':') >= 3:
                parts = line.split(':')
                proxy = {
                    'server': f'{parts[0]}:{parts[1]}',
                    'username': parts[2],
                    'password': parts[3],
                    'protocol': 'http',
                    'raw': line
                }
            # 格式3: ip:port
            else:
                parts = line.split(':')
                proxy = {
                    'server': f'{parts[0]}:{parts[1]}',
                    'username': None,
                    'password': None,
                    'protocol': 'http',
                    'raw': line
                }
            return proxy
        except Exception:
            return None

    def get_current(self):
        """获取当前代理（Playwright 格式）"""
        if not self.proxies:
            return None
        return self.proxies[self.current_index % len(self.proxies)]

    def get_playwright_proxy(self):
        """转换为 Playwright launch kwargs 格式"""
        proxy = self.get_current()
        if not proxy:
            return None

        # Playwright 格式: {'server': 'protocol://ip:port', 'username': '...', 'password': '...'}
        pw_proxy = {
            'server': f"{proxy['protocol']}://{proxy['server']}",
        }
        if proxy.get('username'):
            pw_proxy['username'] = proxy['username']
            pw_proxy['password'] = proxy['password']
        return pw_proxy

    def report_failure(self):
        """报告代理失败，失败次数过多就跳过"""
        if not self.proxies:
            return None

        proxy = self.proxies[self.current_index % len(self.proxies)]
        key = proxy['raw']
        self.fail_count[key] = self.fail_count.get(key, 0) + 1

        if self.fail_count[key] >= PROXY_MAX_FAILS:
            print(f'⚠️ 代理 {proxy["raw"]} 连续失败 {self.fail_count[key]} 次，切换到下一个')
            return self.rotate()
        return None

    def report_success(self):
        """请求成功，重置当前代理的失败计数"""
        if not self.proxies:
            return
        proxy = self.proxies[self.current_index % len(self.proxies)]
        key = proxy['raw']
        if key in self.fail_count:
            self.fail_count[key] = 0

    def rotate(self):
        """轮换到下一个代理"""
        if not self.proxies:
            return None
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.proxies)
        if old_index != self.current_index:
            proxy = self.proxies[self.current_index]
            print(f'🔄 切换代理: {proxy["raw"]}')
            return proxy
        return None


class CookieManager:
    """多Cookie管理器"""
    
    def __init__(self, cookies_dir=COOKIES_DIR):
        self.cookies_dir = cookies_dir
        self.cookie_files = []
        self.current_index = 0
        self.request_count = 0
        self.consecutive_403 = 0
        self.load_cookie_files()
    
    def load_cookie_files(self):
        """加载所有Cookie文件"""
        if not os.path.exists(self.cookies_dir):
            os.makedirs(self.cookies_dir, exist_ok=True)
        
        self.cookie_files = []
        # 查找所有 cookies/*.json 文件
        if os.path.exists(self.cookies_dir):
            for f in os.listdir(self.cookies_dir):
                if f.endswith('.json'):
                    self.cookie_files.append(os.path.join(self.cookies_dir, f))
        
        # 如果cookies目录为空但有主cookies.json，复制一份
        if not self.cookie_files and os.path.exists(COOKIE_FILE):
            self._migrate_main_cookie()
        
        print(f'找到 {len(self.cookie_files)} 个Cookie文件')
    
    def _migrate_main_cookie(self):
        """将主cookies.json迁移到cookies目录"""
        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            # 创建第一个账号的Cookie
            first_file = os.path.join(self.cookies_dir, 'cookie_1.json')
            with open(first_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            self.cookie_files.append(first_file)
            print(f'已将 cookies.json 迁移到 {first_file}')
        except Exception as e:
            print(f'迁移Cookie失败: {e}')
    
    def get_current_cookie_file(self):
        """获取当前Cookie文件路径"""
        if not self.cookie_files:
            return None
        return self.cookie_files[self.current_index % len(self.cookie_files)]
    
    def switch_cookie(self):
        """切换到下一个Cookie"""
        if len(self.cookie_files) > 1:
            self.current_index = (self.current_index + 1) % len(self.cookie_files)
            self.consecutive_403 = 0
            cookie_file = self.get_current_cookie_file()
            print(f'\n🔄 切换到下一个Cookie: {os.path.basename(cookie_file)}')
            return cookie_file
        return None
    
    def report_403(self):
        """报告遇到403错误"""
        self.consecutive_403 += 1
        if self.consecutive_403 >= COOKIE_SWITCH_THRESHOLD:
            print(f'⚠️ 连续遇到 {self.consecutive_403} 次403，尝试切换Cookie...')
            return self.switch_cookie()
        return None
    
    def should_switch(self):
        """检查是否需要切换Cookie"""
        self.request_count += 1
        if self.request_count >= SWITCH_INTERVAL and len(self.cookie_files) > 1:
            self.request_count = 0
            old_index = self.current_index
            self.current_index = (self.current_index + 1) % len(self.cookie_files)
            if old_index != self.current_index:
                cookie_file = self.get_current_cookie_file()
                print(f'\n⏳ 定期切换Cookie: {os.path.basename(cookie_file)}')
                return cookie_file
        return None
    
    def load_cookies(self):
        """加载当前Cookie文件"""
        cookie_file = self.get_current_cookie_file()
        if cookie_file and os.path.exists(cookie_file):
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f'加载Cookie失败: {e}')
        return None


class WebCrawler:
    def __init__(self, cookie_manager=None, proxy_manager=None):
        self.browser = None
        self.context = None
        self.page = None
        self.pw = None
        self.cookie_manager = cookie_manager
        self.proxy_manager = proxy_manager
        self.use_multi_cookies = cookie_manager is not None and len(cookie_manager.cookie_files) > 1
        self.use_proxy = proxy_manager is not None and len(proxy_manager.proxies) > 0
        self._current_proxy = None  # 当前浏览器实例使用的代理
        # CDP 模式下缓存的 OZON description API 响应
        self._captured_responses = []

    def _find_real_chrome(self):
        """查找系统已安装的真实 Chrome 浏览器路径"""
        import platform
        import glob

        system = platform.system()
        candidates = []

        if system == 'Windows':
            # Windows 常见安装路径
            candidates = [
                os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
                os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
                os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            ]
            # 注册表查找
            try:
                import winreg
                for reg_path in [
                    r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe',
                    r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe',
                ]:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                            path, _ = winreg.QueryValueEx(key, '')
                            if path and os.path.exists(path):
                                candidates.insert(0, path)
                    except Exception:
                        pass
            except Exception:
                pass
        elif system == 'Darwin':
            candidates = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                os.path.expanduser('~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            ]
        else:
            # Linux
            candidates = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/snap/bin/chromium',
            ]
            candidates = [c for c in candidates if os.path.exists(c)]
            # which 兜底
            for cmd in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']:
                found = glob.glob(f'/usr/bin/{cmd}*')
                candidates.extend(found)

        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def _initialize_cdp(self, cdp_url='http://localhost:9222', use_cookies=True):
        """CDP 模式：连接到一个已经在跑的 Chrome（带 --remote-debugging-port 启动的）

        优点：
        - 复用用户的真实登录态（不需要再走 --login / --import）
        - 复用真实 Chrome 浏览历史 / Cookie / 缓存 -> 防检测最强
        - 爬完不关 Chrome，下一次直接用

        使用方式：
        1. 手动启动 Chrome 并打开调试端口：
           start chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\\chrome-debug-profile
        2. 跑爬虫：
           python crawler.py --cdp 1.json
        """
        import urllib.request
        import json as _json

        print(f'🔌 CDP 模式：尝试连接 {cdp_url}')

        # 探测 Chrome 是否在跑
        try:
            with urllib.request.urlopen(f'{cdp_url}/json/version', timeout=3) as resp:
                browser_info = _json.loads(resp.read())
                print(f'✅ 已连接 Chrome: {browser_info.get("Browser", "未知版本")}')
        except Exception as e:
            print(f'❌ 无法连接 {cdp_url}')
            print(f'\n请先手动启动 Chrome（带调试端口）：')
            print(f'  Windows:')
            print(f'    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ^')
            print(f'      --remote-debugging-port=9222 ^')
            print(f'      --user-data-dir="C:\\chrome-crawler-profile"')
            print(f'\n⚠️  注意：--user-data-dir 必须是你平时登录过 OZON 的用户目录')
            print(f'   或者：用 Chrome 已经打开着的状态直接跑，CDP 会复用它的页面')
            raise

        # 启动 Playwright 并连上去
        self.pw = sync_playwright().start()
        try:
            self.browser = self.pw.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            print(f'❌ Playwright 连接 CDP 失败: {e}')
            self.pw.stop()
            self.pw = None
            raise

        # CDP 模式：Chrome 已经在跑，直接用它的 context（用户当前的登录态！）
        if self.browser.contexts:
            self.context = self.browser.contexts[0]
            print(f'🔗 复用 Chrome 现有 context（包含你的登录态）')
        else:
            # 没有任何 context（可能用户 Chrome 是无痕启动）
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='ru-RU',
                timezone_id='Europe/Moscow',
            )
            print('🆕 新建 context')

        # 找一个能用的页面；没有就开一个
        if self.context.pages:
            self.page = self.context.pages[0]
            print(f'📄 复用现有页面: {self.page.url[:80]}')
            # 如果当前不是 OZON，跳过去
            if 'ozon.ru' not in self.page.url:
                try:
                    self.page.goto('https://www.ozon.ru', wait_until='domcontentloaded', timeout=15000)
                except:
                    pass
        else:
            self.page = self.context.new_page()
            try:
                self.page.goto('https://www.ozon.ru', wait_until='domcontentloaded', timeout=15000)
            except Exception as e:
                print(f'⚠️ 打开 OZON 失败: {e}')

        print('✅ CDP 模式初始化完成')

    def initialize(self, use_cookies=True, use_real_chrome=False, cdp_mode=False, cdp_url='http://localhost:9222'):
        # CDP 模式：连接到一个已经在跑的 Chrome（连你手动开的那个）
        if cdp_mode:
            self._initialize_cdp(cdp_url=cdp_url, use_cookies=use_cookies)
            return

        print('正在启动浏览器...')
        self.pw = sync_playwright().start()

        # 应用 stealth 钩子 - 更强伪装（移除可疑的覆盖，使用真实值）
        try:
            stealth_obj = stealth.Stealth(
                navigator_languages_override=('ru-RU', 'ru', 'en-US', 'en'),
                navigator_platform_override='Win32',
                webgl_vendor_override='Google Inc. (Intel)',
                webgl_renderer_override='ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)',
                # 不覆盖 navigator.user_agent、screen、hardware 等（用真实值）
            )
            stealth_obj.hook_playwright_context(self.pw)
        except Exception as e:
            print(f'stealth 初始化失败，使用默认配置: {e}')

        # 浏览器启动参数 - 模拟真实用户
        launch_kwargs = dict(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-background-networking',
                '--disable-sync',
                '--metrics-recording-only',
                '--mute-audio',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--ignore-certificate-errors',
                '--ignore-ssl-errors',
                '--enable-features=NetworkService,NetworkServiceInProcess',
                '--enable-automation=false',
                '--enable-webgl',
                '--use-gl=desktop',
                # 无头模式增强
                '--headless=new',
                '--disable-gpu',
                '--disable-software-rasterizer',
                # 移除无头特征
                '--disable-hang-monitor',
                '--disable-ipc-flooding-protection',
                '--disable-renderer-backgrounding',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
            ]
        )

        # 真实 Chrome 模式：用系统已安装的 Chrome（强烈推荐，能通过滑动验证）
        if use_real_chrome:
            chrome_path = self._find_real_chrome()
            if chrome_path:
                print(f'使用真实 Chrome 浏览器: {chrome_path}')
                launch_kwargs['executable_path'] = chrome_path
                # 真实 Chrome 不要传 channel
            else:
                print('⚠️ 未找到真实 Chrome，回退到 Playwright 内置 Chromium')

        # 代理模式
        if self.use_proxy and self.proxy_manager:
            pw_proxy = self.proxy_manager.get_playwright_proxy()
            if pw_proxy:
                launch_kwargs['proxy'] = pw_proxy
                self._current_proxy = self.proxy_manager.get_current()
                print(f'🌐 使用代理: {self._current_proxy["raw"]}')

        self.browser = self.pw.chromium.launch(**launch_kwargs)

        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=get_random_user_agent(),
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            permissions=['geolocation'],
            ignore_https_errors=True,
            color_scheme='light',
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            # 模拟真实屏幕
            screen={'width': 1920, 'height': 1080},
            # 启用 JavaScript
            java_script_enabled=True,
            # 真实用户行为参数
            extra_http_headers={
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Sec-Ch-Ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Opera GX";v="112"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            },
        )

        # 拦截自动化检测脚本（不拦截过多，避免被反检测）
        self.context.route("**/captcha/**", lambda route: route.abort())
        self.context.route("**/antibot/**", lambda route: route.abort())
        
        # 尝试加载 Cookie
        if use_cookies:
            if self.use_multi_cookies:
                # 多Cookie模式
                cookies = self.cookie_manager.load_cookies()
                if cookies:
                    print('正在加载多Cookie模式...')
                    self._add_cookies(cookies)
            elif os.path.exists(COOKIE_FILE):
                print('正在加载保存的登录状态...')
                try:
                    with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                        cookies = json.load(f)
                    self._add_cookies(cookies)
                    print('登录状态加载成功!')
                except Exception as e:
                    print(f'加载登录状态失败: {e}')
        
        self.page = self.context.new_page()

        # 额外注入脚本隐藏自动化特征 - 更完善
        self.page.add_init_script("""
            // 隐藏 webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => false });

            // 删除 webdriver 属性痕迹
            delete navigator.__proto__.webdriver;

            // 模拟真实 Chrome 插件
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
                ]
            });

            // 真实 languages
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US', 'en'] });

            // Chrome runtime
            window.chrome = {
                runtime: {
                    onInstalled: { addListener: () => {} },
                    sendMessage: () => {},
                    connect: () => {}
                },
                app: { isInstalled: false },
                csi: () => {},
                loadTimes: () => {}
            };

            // 权限
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // 隐藏 Playwright/自动化痕迹
            const elementDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
            Object.defineProperty(HTMLDivElement.prototype, 'offsetHeight', {
                ...elementDescriptor,
                get: function () { return elementDescriptor.get.apply(this); }
            });

            // WebGL 参数
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel(R) UHD Graphics';
                return getParameter.call(this, parameter);
            };

            // Connection 信息
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10,
                    saveData: false
                })
            });

            // 真实插件长度
            Object.defineProperty(navigator, 'mimeTypes', {
                get: () => [
                    { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                    { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' }
                ]
            });
        """)

        print('浏览器已启动!')

        # 注册 response 监听器：拦截 OZON 的 entrypoint API 拿到原始描述数据
        self._register_response_interceptor()

    def _register_response_interceptor(self):
        """拦截 OZON 的 API 响应，把可能的描述数据缓存起来

        策略：只收集 URL（同步，零开销），等页面加载完毕后再用
        context.request 重新发请求拿 body（复用 context 的 cookie，无需跨线程）。
        """
        if not self.page:
            return
        self._captured_api_urls = []  # [{'url': str, 'kind': str}, ...]

        def on_response(response):
            try:
                url = response.url
                if 'ozon.ru' not in url:
                    return
                kind = None
                if 'entrypoint-api' in url:
                    kind = 'entrypoint'
                elif 'web-product' in url or 'web/product' in url or 'product/v2' in url:
                    kind = 'product'
                if kind:
                    self._captured_api_urls.append({'url': url, 'kind': kind})
            except Exception:
                pass

        try:
            self.page.on('response', on_response)
        except Exception as e:
            print(f'response 拦截器注册失败: {e}')

    def _fetch_api_responses(self):
        """等页面加载完成后，把拦截到的 API URL 重新发一遍，拿 body

        必须在这里（而非 on_response 里）读取 body，因为：
        - 同步 API 回调里直接 response.text() 会死锁
        - 用 context.request 走同一 context 的 cookie/header，更真实
        """
        if not getattr(self, '_captured_api_urls', None):
            return
        self._captured_responses = []
        for item in self._captured_api_urls:
            url = item['url']
            try:
                # 走 browser context 的 cookie，发 GET 请求
                resp = self.context.request.get(url, timeout=10)
                if resp.ok and len(resp.body()) > 200:
                    self._captured_responses.append((url, resp.text()))
            except Exception:
                pass
    
    def _add_cookies(self, cookies):
        """添加Cookie到context"""
        # 修正 sameSite 字段
        for cookie in cookies:
            if 'sameSite' in cookie:
                if cookie['sameSite'] not in ('Strict', 'Lax', 'None'):
                    cookie['sameSite'] = 'Lax'
        self.context.add_cookies(cookies)

    def _simulate_human_browsing(self, page=None):
        """模拟真实用户的浏览行为：滚动 + 停顿
        重要：OZON 商品页很长，需要一直滚到底才能触发懒加载（描述/图片/规格）
        """
        target = page or self.page
        if not target:
            return

        try:
            # 1. 滚动浏览：每次滚一段，停顿一会，模拟用户阅读
            scroll_count = random.randint(SCROLL_COUNT_MIN, SCROLL_COUNT_MAX)
            for i in range(scroll_count):
                # 随机滚动距离（模拟用户慢慢看商品）
                scroll_distance = random.randint(300, 800)
                target.evaluate(f'window.scrollBy({{ top: {scroll_distance}, behavior: "smooth" }})')
                # 每次滚动后停留一下（模拟用户在阅读）
                pause = random.uniform(0.8, 2.5)
                time.sleep(pause)

            # 2. 滚到底（关键！触发 OZON 的懒加载）
            try:
                target.evaluate('''
                    async () => {
                        return new Promise(resolve => {
                            let totalHeight = 0;
                            const distance = 500;
                            const timer = setInterval(() => {
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if (totalHeight >= document.body.scrollHeight) {
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 200);
                        });
                    }
                ''')
                # 等最后的网络请求完成
                time.sleep(2)
                # 再触发一次滚到底，确保动态加载的内容也能出来
                target.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(2)
                # 滚回一半（很多 lazy-load 是基于 viewport 触发的，再多看一眼）
                target.evaluate('window.scrollBy(0, -1000)')
                time.sleep(1)
            except Exception as e:
                print(f'  滚动到底时出错: {e}')

            # 3. 偶尔滚回顶部（模拟用户比对商品信息）
            if random.random() < 0.3:  # 30% 概率
                target.evaluate('window.scrollTo({ top: 0, behavior: "smooth" })')
                time.sleep(random.uniform(0.5, 1.5))

            # 3. 鼠标随机移动（模拟真实鼠标）
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, 1800)
                y = random.randint(200, 900)
                try:
                    target.mouse.move(x, y)
                    time.sleep(random.uniform(0.2, 0.8))
                except Exception:
                    pass
        except Exception as e:
            print(f'模拟浏览行为失败（继续）: {e}')

    def _human_read_pause(self):
        """模拟用户打开页面后的阅读停留"""
        pause = random.uniform(PAGE_READ_TIME_MIN, PAGE_READ_TIME_MAX)
        print(f'  📖 模拟用户阅读 {pause:.1f} 秒...')
        time.sleep(pause)

    def _random_request_delay(self):
        """请求之间的随机延迟（避免被识别为机器人）"""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        print(f'  ⏱️  等待 {delay:.1f} 秒后继续...')
        time.sleep(delay)

    def restart_with_new_proxy(self):
        """换代理后重启浏览器（代理是浏览器级别的，必须重启）"""
        if not self.use_proxy or not self.proxy_manager:
            return False

        # CDP 模式：Chrome 是外部启动的，不能 close() 整个 browser
        if getattr(self, '_cdp_mode', False):
            print('⚠️ CDP 模式下不能重启浏览器，跳过代理切换')
            return False

        # 标记旧代理失败
        self.proxy_manager.report_failure()

        # 关闭当前浏览器
        try:
            if self.page:
                self.page.close()
        except:
            pass
        try:
            if self.context:
                self.context.close()
        except:
            pass
        try:
            if self.browser:
                self.browser.close()
        except:
            pass
        try:
            if self.pw:
                self.pw.stop()
        except:
            pass

        # 用新代理重启
        print('🔄 因代理问题，重启浏览器...')
        self.initialize(use_cookies=True, use_real_chrome=False)
        return True
    
    def switch_to_next_cookie(self, cookie_file=None):
        """切换到下一个Cookie并重建context"""
        if not self.use_multi_cookies:
            return
        
        if cookie_file is None:
            cookie_file = self.cookie_manager.get_current_cookie_file()
        
        print(f'正在切换Cookie: {os.path.basename(cookie_file)}')
        
        # 关闭旧页面和context
        if self.page:
            try:
                self.page.close()
            except:
                pass
        if self.context:
            try:
                self.context.close()
            except:
                pass
        
        # 创建新context
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=get_random_user_agent(),
            locale='ru-RU',
            timezone_id='Europe/Moscow',
            permissions=['geolocation'],
            ignore_https_errors=True,
            extra_http_headers={
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            },
        )
        
        # 加载新Cookie
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            self._add_cookies(cookies)
        except Exception as e:
            print(f'切换Cookie失败: {e}')
        
        # 创建新页面
        self.page = self.context.new_page()
        
        # 注入脚本
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'en-US', 'en'] });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'permissions', { get: () => Promise.resolve({ state: 'granted' }) });
        """)
        
        print('Cookie切换完成!')

    def import_cookies(self):
        """导入 Cookie"""
        print('\n╔══════════════════════════════════════════════════════════════╗')
        print('║                      Cookie 导入向导                          ║')
        print('╚══════════════════════════════════════════════════════════════╝')
        print('''
请按以下步骤操作：

1. 在浏览器中打开 Ozon 网站: https://www.ozon.ru
2. 登录你的账号
3. 安装浏览器扩展 "EditThisCookie" 或类似工具
4. 点击扩展图标，导出 Cookie (JSON 格式)
5. 将导出的 JSON 内容粘贴到下面

完成后按 Ctrl+Z (Windows) 回车结束输入
        ''')
        
        print('请粘贴 Cookie JSON (输入完成后按回车):')
        lines = []
        try:
            while True:
                line = input()
                if line.strip() == '':
                    break
                lines.append(line)
        except EOFError:
            pass
        
        if not lines:
            print('未输入 Cookie，取消导入')
            return False
        
        try:
            cookie_text = '\n'.join(lines)
            cookies = json.loads(cookie_text)
            
            if not isinstance(cookies, list):
                cookies = [cookies]
            
            with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            print(f'Cookie 已导入到: {COOKIE_FILE}')
            return True
        except json.JSONDecodeError as e:
            print(f'JSON 格式错误: {e}')
            return False
        except Exception as e:
            print(f'保存失败: {e}')
            return False

    def login_and_save_cookies(self, save_to=None):
        """手动登录并保存 Cookie"""
        save_path = save_to or COOKIE_FILE
        
        print('\n╔══════════════════════════════════════════════════════════════╗')
        print('║                      登录方式选择                             ║')
        print('╚══════════════════════════════════════════════════════════════╝')
        print(f'''
保存路径: {save_path}

请选择登录方式：

1. 浏览器自动登录 (推荐)
   - 程序会打开浏览器
   - 你在浏览器中登录 Ozon
   - 按回车保存 Cookie

2. 手动导入 Cookie (如果浏览器方式不行)
   - 你自己打开浏览器登录
   - 用 EditThisCookie 等工具导出 Cookie
   - 粘贴到程序中
        ''')
        
        choice = input('请选择 (1 或 2): ').strip()
        
        if choice == '2':
            return self.import_cookies()
        
        # 方式 1：浏览器自动登录
        print('\n正在打开浏览器，请在新窗口中登录 Ozon...')
        self.page.goto('https://www.ozon.ru', wait_until='domcontentloaded')
        print('登录完成后，按回车键继续...')
        input()
        
        # 保存 Cookie
        cookies = self.context.cookies()
        
        # 确定保存路径
        if save_to and save_to != COOKIE_FILE:
            # 保存到 cookies 目录，自动编号
            existing = [f for f in os.listdir(os.path.dirname(save_to)) if f.endswith('.json')]
            next_num = len(existing) + 1
            save_path = os.path.join(os.path.dirname(save_to), f'cookie_{next_num}.json')
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f'登录状态已保存到: {save_path}')

    def crawl(self, url, retries=5, show_output=True, overwrite=False, save_to_output=True):
        for attempt in range(retries):
            try:
                if show_output:
                    print(f'\n正在访问: {url} (尝试 {attempt + 1}/{retries})')

                # 检查是否需要切换Cookie（定时切换）
                if self.use_multi_cookies:
                    next_cookie = self.cookie_manager.should_switch()
                    if next_cookie:
                        self.switch_to_next_cookie(next_cookie)
                        self._random_request_delay()

                # 检查页面是否有效，无效则重新创建
                try:
                    self.page.goto('about:blank', timeout=5000)
                except Exception as page_err:
                    # 页面已失效
                    err_msg = str(page_err).lower()

                    # 代理相关错误，切换代理重启浏览器
                    is_proxy_error = any(kw in err_msg for kw in [
                        'proxy', 'net::err_proxy', 'tunnel', '407', '502', '503', '504'
                    ])

                    if is_proxy_error and self.use_proxy and attempt < retries - 1:
                        print(f'⚠️ 检测到代理错误: {page_err}')
                        self.restart_with_new_proxy()
                        time.sleep(3)
                        continue

                    # 其他错误：清理后重新初始化
                    try:
                        self.browser.close()
                    except:
                        pass
                    try:
                        self.pw.stop()
                    except:
                        pass

                    self.initialize(use_cookies=True)
                    self._random_request_delay()

                # 导航到目标页面
                response = self.page.goto(url, wait_until='domcontentloaded', timeout=30000)

                # 报告代理成功
                if self.use_proxy:
                    self.proxy_manager.report_success()

                if response and response.status >= 400:
                    if show_output:
                        print(f'网站返回状态码: {response.status}')

                    # 检查是否是验证码页面
                    title = self.page.title()
                    if 'challenge' in title.lower() or 'captcha' in title.lower() or 'antibot' in title.lower():
                        if show_output:
                            print('⚠️ 检测到反爬验证页面，等待更长时间后重试...')

                    # 403/429 错误：优先尝试换代理，再换 Cookie
                    if response.status in (403, 429):
                        # 1) 换代理
                        if self.use_proxy and attempt < retries - 1:
                            self.restart_with_new_proxy()
                            time.sleep(3)
                            continue

                        # 2) 换 Cookie
                        if response.status == 403 and self.use_multi_cookies:
                            next_cookie = self.cookie_manager.report_403()
                            if next_cookie:
                                if attempt < retries - 1:
                                    self.switch_to_next_cookie(next_cookie)
                                    time.sleep(5)
                                    continue

                    if attempt < retries - 1:
                        # 失败后等待更久（线性递增）
                        wait_time = 10 + attempt * 5
                        if show_output:
                            print(f'等待 {wait_time} 秒后重试...')
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f'访问失败，HTTP状态码: {response.status}')

                if show_output:
                    print('页面加载完成，等待内容渲染...')

                # 模拟用户阅读停留（防反爬关键）
                self._human_read_pause()

                # 尝试等待页面稳定
                try:
                    self.page.wait_for_load_state('networkidle', timeout=10000)
                except:
                    pass

                # 模拟用户浏览行为（滚动+鼠标移动）
                self._simulate_human_browsing()
                
                data = self.extract_page_data()

                if save_to_output:
                    filename = self.generate_filename(url, overwrite)
                    self.save_to_file(data, filename, overwrite)
                    if show_output:
                        print(f'\n爬取完成!')
                        print(f'文件已保存至: output/{filename}')

                return data
                
            except Exception as e:
                if show_output:
                    print(f'爬取失败: {e}')
                if attempt < retries - 1:
                    if show_output:
                        print('等待后重试...')
                    time.sleep(3)
                else:
                    raise

    def extract_page_data(self):
        """只提取图片链接和描述"""
        current_url = self.page.url
        images = self.extract_images()
        # 先把拦截到的 API URL 重新发一遍，拿 body
        self._fetch_api_responses()
        description = self.extract_description()

        data = {
            'url': current_url,
            'timestamp': datetime.now().isoformat(),
            'title': self.page.title(),
            'description': description,
            'image_count': len(images),
            'images': images
        }

        return data

    def extract_title(self):
        try:
            return self.page.title()
        except:
            return None

    def extract_metadata(self):
        metadata = {}
        try:
            metas = self.page.query_selector_all('meta')
            for meta in metas:
                name = meta.get_attribute('name') or meta.get_attribute('property')
                content = meta.get_attribute('content')
                if name and content:
                    metadata[name] = content
        except:
            pass
        return metadata

    def extract_headings(self):
        headings = {'h1': [], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': []}
        try:
            for i in range(1, 7):
                elements = self.page.query_selector_all(f'h{i}')
                headings[f'h{i}'] = [
                    el.inner_text().strip() 
                    for el in elements 
                    if el.inner_text().strip()
                ]
        except:
            pass
        return headings

    def extract_links(self):
        links = []
        try:
            elements = self.page.query_selector_all('a[href]')[:100]
            for el in elements:
                text = el.inner_text().strip()
                href = el.get_attribute('href')
                if text or href:
                    links.append({'text': text, 'href': href})
        except:
            pass
        return links

    def extract_images(self):
        """只提取商品图片画廊的图片"""
        images = []
        seen = set()
        
        try:
            # 方法1: 查找图片画廊区域
            gallery = self.page.query_selector('.pdp_r4a')
            if gallery:
                imgs = gallery.query_selector_all('img')
                for img in imgs:
                    src = img.get_attribute('src') or img.get_attribute('data-src')
                    if src and 'ozon' in src and src not in seen:
                        # 转换为高清URL
                        src = src.replace('/wc50/', '/wc1000/').replace('/wc150/', '/wc1000/')
                        seen.add(src)
                        images.append(src)
            
            # 方法2: 缩略图
            thumbnails = self.page.query_selector_all('.pdp_ra3 img, .thumb img, [class*="thumbnail"] img')
            for img in thumbnails:
                src = img.get_attribute('src') or img.get_attribute('data-src')
                if src and 'ozon' in src and src not in seen:
                    src = src.replace('/wc50/', '/wc1000/').replace('/wc150/', '/wc1000/')
                    seen.add(src)
                    images.append(src)
            
            # 方法3: data-widget 图片
            widget_imgs = self.page.query_selector_all('[data-widget*="gallery"] img, [data-widget*="media"] img')
            for img in widget_imgs:
                src = img.get_attribute('src') or img.get_attribute('data-src')
                if src and 'ozon' in src and src not in seen:
                    src = src.replace('/wc50/', '/wc1000/').replace('/wc150/', '/wc1000/')
                    seen.add(src)
                    images.append(src)
        except:
            pass
        
        return list(seen) if seen else images

    def extract_description(self):
        """提取商品描述

        优先级：
        1. 拦截到的 OZON entrypoint API（最稳，不受前端渲染影响）
        2. 页面 DOM（兜底）
        """
        # 1) 拦截 API：OZON 描述在 entrypoint-api 的 rich 字段里
        api_desc = self._extract_description_from_api()
        if api_desc:
            return api_desc

        # 2) 兜底：DOM 选择器
        selectors = [
            '.RA-a1',           # 原选择器
            '[data-widget="webProductDescription"]',
            '[data-widget="webSpecifications"]',
            '.description',
            '.product-description',
            '[data-widget="webProductHeading"]',
            'section[data-widget*="description"]',
            '.css-1yuhvqj',
            '.app-0-38-0',
        ]

        for selector in selectors:
            try:
                el = self.page.query_selector(selector)
                if el:
                    text = el.inner_text().strip()
                    if text and len(text) > 10:
                        return text
            except:
                continue

        # 3) 备选：meta description
        try:
            meta = self.page.query_selector('meta[name="description"]')
            if meta:
                content = meta.get_attribute('content')
                if content:
                    return content.strip()
        except:
            pass

        return None

    def _extract_description_from_api(self):
        """从拦截到的 entrypoint API 响应里提取描述

        OZON 的商品描述是后端返回的 rich content，前端不渲染就是空的。
        但 API 本身对自动化浏览器是开放的（被屏蔽的只是渲染）。
        """
        if not self._captured_responses:
            return None

        for url, body_text in self._captured_responses:
            try:
                if 'entrypoint-api' not in url and 'web-product' not in url and 'product' not in url:
                    continue
                data = json.loads(body_text)
            except Exception:
                continue

            # 描述文本可能在多处，挨个找
            def find_rich(obj, depth=0):
                if depth > 6 or obj is None:
                    return None
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == 'rich' and isinstance(v, list) and v:
                            # rich 是 HTML 片段列表，取第一个的 text
                            return v
                        if k == 'description' and isinstance(v, str) and len(v) > 20:
                            return v
                        if k == 'text' and isinstance(v, str) and len(v) > 50:
                            return v
                        r = find_rich(v, depth + 1)
                        if r:
                            return r
                elif isinstance(obj, list):
                    for item in obj:
                        r = find_rich(item, depth + 1)
                        if r:
                            return r
                return None

            result = find_rich(data)
            if result:
                if isinstance(result, list):
                    # rich HTML 片段
                    text = self._html_rich_to_text(result)
                    if text and len(text) > 20:
                        return text
                else:
                    return result

        return None

    @staticmethod
    def _html_rich_to_text(rich_list):
        """把 OZON 的 rich HTML 片段列表转成纯文本"""
        out = []
        for item in rich_list:
            if isinstance(item, str):
                # 简单去 HTML 标签
                text = re.sub(r'<[^>]+>', ' ', item)
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    out.append(text)
        return '\n'.join(out)

    def extract_lists(self):
        lists = []
        try:
            list_elements = self.page.query_selector_all('ul, ol')[:20]
            for lst in list_elements:
                items = [li.inner_text().strip() for li in lst.query_selector_all('li') if li.inner_text().strip()]
                if items:
                    lists.append({
                        'type': lst.evaluate('el => el.tagName.toLowerCase()'),
                        'items': items
                    })
        except:
            pass
        return lists

    def extract_tables(self):
        tables = []
        try:
            table_elements = self.page.query_selector_all('table')[:10]
            for table in table_elements:
                headers = [th.inner_text().strip() for th in table.query_selector_all('th')]
                rows = []
                tr_elements = table.query_selector_all('tr')[:20]
                for tr in tr_elements:
                    tds = [td.inner_text().strip() for td in tr.query_selector_all('td')]
                    if tds:
                        rows.append(tds)
                if rows:
                    tables.append({'headers': headers, 'rows': rows})
        except:
            pass
        return tables

    def extract_product_info(self):
        """提取商品特有信息"""
        info = {}
        try:
            # 价格
            price_selectors = [
                '[data-widget="webPrice"] span',
                '.price span',
                '.product-price span',
                '[class*="price"] span',
                '[class*="Price"]',
            ]
            for selector in price_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        info['price'] = el.inner_text().strip()
                        break
                except:
                    pass
            
            # 描述
            desc_selectors = [
                '[data-widget="webDescription"]',
                '.description',
                '.product-description',
                '[class*="description"]',
            ]
            for selector in desc_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        info['description'] = el.inner_text().strip()[:2000]
                        break
                except:
                    pass
            
            # 评分
            rating_selectors = [
                '[data-widget="webRating"]',
                '.rating',
                '[class*="rating"]',
            ]
            for selector in rating_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        info['rating'] = el.inner_text().strip()
                        break
                except:
                    pass
            
            # 详情
            detail_selectors = [
                '[data-widget="webCharacteristics"]',
                '.characteristics',
                '.specs',
            ]
            for selector in detail_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        info['details'] = el.inner_text().strip()[:2000]
                        break
                except:
                    pass
                        
        except:
            pass
        return info

    def generate_filename(self, url, overwrite=False):
        """生成文件名，优先使用商品ID"""
        # 尝试从URL中提取商品ID
        match = re.search(r'/product/[^/]+-(\d+)/', url)
        if match:
            product_id = match.group(1)
            filename = f'product_{product_id}.json'
            if overwrite:
                return filename
            # 如果文件不存在就用商品ID，否则用时间戳
            filepath = os.path.join(OUTPUT_DIR, filename)
            if not os.path.exists(filepath):
                return filename
        
        # 回退到时间戳命名
        parsed = urlparse(url)
        domain = re.sub(r'[^a-zA-Z0-9]', '_', parsed.hostname)
        timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
        return f'{domain}_{timestamp}.json'

    def save_to_file(self, data, filename, overwrite=False):
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(OUTPUT_DIR, filename)
        # 如果覆盖模式且文件存在，先删除
        if overwrite and os.path.exists(filepath):
            os.remove(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def close(self):
        if self.browser:
            self.browser.close()
            print('浏览器已关闭')


def extract_product_urls_from_json(json_file):
    """从 JSON 文件中提取所有 productUrl"""
    urls = []
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 处理 data 数组格式 {"data": [...]}
        if isinstance(data, dict) and 'data' in data:
            items = data['data']
        elif isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = [data]
        else:
            return urls
        
        for item in items:
            if isinstance(item, dict) and 'productUrl' in item:
                url = item['productUrl']
                if url.startswith('http'):
                    urls.append(url)
                else:
                    urls.append('https://www.ozon.ru' + url)
    except Exception as e:
        print(f'读取文件失败: {e}')
    return urls


def main():
    print('╔════════════════════════════════════════╗')
    print('║       Playwright 网页爬虫 v2.0          ║')
    print('║       (stealth + 多Cookie版本)        ║')
    print('╚════════════════════════════════════════╝\n')

    # 检查命令行参数
    url_from_arg = None
    batch_file = None
    login_mode = False
    import_mode = False
    overwrite = False
    use_multi_cookies = True  # 默认使用多Cookie模式
    use_real_chrome = '--real-chrome' in sys.argv  # 使用系统已安装的真实 Chrome
    cdp_mode = '--cdp' in sys.argv  # CDP 模式：连接到你手动开的 Chrome
    resume_mode = '--resume' in sys.argv  # 从上次暂停处恢复
    clear_state_mode = '--clear-state' in sys.argv  # 清除保存的状态
    folder_mode = False  # 文件夹批量模式

    if use_real_chrome:
        print('🔵 已启用真实 Chrome 模式（强烈推荐，能通过滑动验证）\n')

    if cdp_mode:
        print('🔌 已启用 CDP 模式（连接本地 Chrome 9222 端口，复用你的登录态）\n')

    if resume_mode:
        print('📤 已启用恢复模式，将从上次暂停处继续\n')

    # 初始化状态管理器
    state_manager = CrawlerStateManager()

    # 清除状态模式
    if clear_state_mode:
        state_manager.clear_state()
        print('状态已清除，开始新的爬取任务\n')

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # 过滤掉 --real-chrome 再判断
        if arg == '--login':
            login_mode = True
        elif arg == '--import':
            import_mode = True
        elif arg == '--folder':
            folder_mode = True
            folder_path = sys.argv[2] if len(sys.argv) > 2 else '.'
            if '--force' in sys.argv:
                overwrite = True
        elif arg == '--batch':
            batch_file = sys.argv[2] if len(sys.argv) > 2 else None
            if '--force' in sys.argv:
                overwrite = True
        elif arg == '--force':
            overwrite = True
            if len(sys.argv) > 2 and sys.argv[2].endswith('.json'):
                batch_file = sys.argv[2]
            elif len(sys.argv) > 2:
                url_from_arg = sys.argv[2]
        elif arg.endswith('.json'):
            batch_file = arg
            if '--force' in sys.argv:
                overwrite = True
        else:
            url_from_arg = arg

    # 初始化Cookie管理器
    cookie_manager = CookieManager() if use_multi_cookies else None

    # 初始化代理管理器（如果存在 proxies.txt）
    proxy_manager = ProxyManager() if os.path.exists(PROXIES_FILE) else None

    # 创建爬虫实例
    crawler = WebCrawler(cookie_manager=cookie_manager, proxy_manager=proxy_manager)
    crawler._cdp_mode = cdp_mode  # 用于保护某些不能在 CDP 下调用的方法

    try:
        # 登录模式 - 强烈建议用真实 Chrome（不要用代理，不然出口 IP 变化 Cookie 关联性会出问题）
        if login_mode:
            crawler.initialize(use_cookies=False, use_real_chrome=use_real_chrome or True)
            save_to = cookie_manager.cookies_dir if use_multi_cookies else COOKIE_FILE
            print(f'\n登录后Cookie将保存到: {save_to}')
            if proxy_manager and proxy_manager.proxies:
                print('⚠️ 登录时不建议用代理（Cookie 会绑定到代理 IP）')
            crawler.login_and_save_cookies(save_to=save_to)
            return

        # 导入 Cookie 模式
        if import_mode:
            crawler.initialize(use_cookies=False, use_real_chrome=use_real_chrome)
            crawler.import_cookies()
            return

        # 检查是否有Cookie可用
        has_cookies = (use_multi_cookies and cookie_manager and cookie_manager.cookie_files) or os.path.exists(COOKIE_FILE)
        if not has_cookies:
            print('未找到登录状态，请先运行以下命令登录:')
            print('  python crawler.py --login --real-chrome   ← 推荐！')
            print('  或手动导入 Cookie: python crawler.py --import\n')
            return

        # 初始化爬虫（使用真实 Chrome + 代理，可选 CDP 模式）
        crawler.initialize(use_cookies=True, use_real_chrome=use_real_chrome, cdp_mode=cdp_mode)

        # 守护进程模式 - 持续监控文件夹
        if folder_mode:
            import glob as glob_module
            import threading

            # 检查是否启用了守护模式
            daemon_mode = '--daemon' in sys.argv or '-d' in sys.argv
            check_interval = 10  # 文件夹检查间隔（秒）

            def get_pending_files(folder):
                """获取待处理的文件列表"""
                json_files = glob_module.glob(os.path.join(folder, '*.json'))
                json_files = [f for f in json_files if not f.endswith('_state.json') 
                             and '/output/' not in f and not os.path.basename(f).startswith('w_')]
                return json_files

            def process_single_file(json_file, crawler, overwrite, resume_mode):
                """处理单个文件，返回是否全部完成"""
                print(f'\n{"="*60}')
                print(f'📁 处理文件: {json_file}')
                print(f'{"="*60}')

                with open(json_file, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)

                if isinstance(original_data, dict) and 'data' in original_data:
                    items = original_data['data']
                elif isinstance(original_data, list):
                    items = original_data
                else:
                    print('不支持的数据格式，跳过')
                    return True

                urls = []
                for item in items:
                    if isinstance(item, dict) and 'productUrl' in item:
                        url = item['productUrl']
                        if url:
                            if not url.startswith('http'):
                                url = 'https://www.ozon.ru' + url
                            urls.append(url)

                if not urls:
                    print('未找到 productUrl，跳过')
                    return True

                # 从状态恢复
                crawled_urls = set()
                state_file = json_file + '_state.json'
                if resume_mode and os.path.exists(state_file):
                    try:
                        with open(state_file, 'r', encoding='utf-8') as f:
                            saved_state = json.load(f)
                        crawled_urls = set(saved_state.get('crawled_urls', []))
                        print(f'从状态恢复: 已爬取 {len(crawled_urls)} 个')
                    except:
                        pass

                # 计算未爬取的URL
                pending_urls = []
                for i, url in enumerate(urls):
                    if url in crawled_urls:
                        continue
                    item_has_result = False
                    for item in items:
                        item_url = item.get('productUrl', '')
                        if not item_url.startswith('http'):
                            item_url = 'https://www.ozon.ru' + item_url
                        if item_url == url:
                            if item.get('crawledImages') or item.get('crawledDescription'):
                                item_has_result = True
                                crawled_urls.add(url)
                            break
                    if not item_has_result:
                        pending_urls.append((i, url))

                if not pending_urls:
                    print(f'所有 {len(urls)} 个商品已爬取完成，跳过')
                    return True

                print(f'待爬取: {len(pending_urls)}/{len(urls)} 个商品')

                success_count = 0
                file_failed_urls = []

                for idx_in_list, (original_idx, url) in enumerate(pending_urls):
                    try:
                        print(f'\n[{idx_in_list + 1}/{len(pending_urls)}] 正在爬取: {url}')
                        data = crawler.crawl(url, overwrite=overwrite, save_to_output=False)
                        if data:
                            for item in items:
                                item_url = item.get('productUrl', '')
                                if not item_url.startswith('http'):
                                    item_url = 'https://www.ozon.ru' + item_url
                                if item_url == url:
                                    item['crawledImages'] = data.get('images', [])
                                    item['crawledDescription'] = remove_urls_from_text(data.get('description', ''))
                                    # 查找并保存 wbId
                                    seerfar_id = item.get('categoryInfo', {}).get('category', {}).get('id')
                                    if seerfar_id:
                                        item['wbId'] = lookup_wb_subjectid(seerfar_id)
                                    success_count += 1
                                    crawled_urls.add(url)
                                    break
                            with open(json_file, 'w', encoding='utf-8') as f:
                                json.dump(original_data, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f'爬取出错: {e}')
                        file_failed_urls.append(url)

                    # 爬取间隔
                    if idx_in_list < len(pending_urls) - 1:
                        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
                        print(f'⏸️ 等待 {delay:.1f} 秒...')
                        time.sleep(delay)

                # 删除状态文件
                if os.path.exists(state_file):
                    os.remove(state_file)

                # 判断是否完成并重命名
                all_success = (success_count == len(pending_urls))
                if all_success:
                    new_name = os.path.join(os.path.dirname(json_file), 'w_' + os.path.basename(json_file))
                    if not os.path.exists(new_name):
                        os.rename(json_file, new_name)
                        print(f'📁 已重命名为: w_{os.path.basename(json_file)}')
                    return True
                elif file_failed_urls:
                    print(f'⚠️ 有 {len(file_failed_urls)} 个商品爬取失败')
                    return False

                print(f'\n📁 {os.path.basename(json_file)} 完成: 成功 {success_count}/{len(pending_urls)} 个')
                return True

            # ========== 守护进程主循环 ==========
            if daemon_mode:
                print(f'🚀 守护进程模式已启动')
                print(f'📂 监控文件夹: {folder_path}')
                print(f'⏰ 检查间隔: {check_interval} 秒')
                print(f'💡 按 Ctrl+C 安全退出\n')

                processed_files = set()  # 记录已处理过的文件

                while True:
                    try:
                        json_files = get_pending_files(folder_path)

                        # 找出新增的文件（排除已处理过的）
                        new_files = [f for f in json_files if f not in processed_files]

                        if new_files:
                            print(f'\n🔍 发现 {len(new_files)} 个新文件')
                            for json_file in new_files:
                                process_single_file(json_file, crawler, overwrite, resume_mode)
                                processed_files.add(json_file)
                                # 文件之间等待
                                delay = random.uniform(3, 8)
                                print(f'⏸️ 等待 {delay:.1f} 秒...\n')
                                time.sleep(delay)
                        else:
                            current_count = len(json_files)
                            print(f'\r⏳ [{datetime.now().strftime("%H:%M:%S")}] 监控中... {current_count} 个待处理文件', end='', flush=True)

                        time.sleep(check_interval)

                    except KeyboardInterrupt:
                        print('\n\n🛑 守护进程已停止')
                        return

            # ========== 普通批量模式（原有逻辑） ==========
            else:
                json_files = get_pending_files(folder_path)

                if not json_files:
                    print(f'在 {folder_path} 中没有找到 JSON 文件')
                    return

                print(f'找到 {len(json_files)} 个 JSON 文件')
                print(f'文件列表: {[os.path.basename(f) for f in json_files]}\n')

                total_success = 0
                total_failed = 0

                for json_file in json_files:
                    if process_single_file(json_file, crawler, overwrite, resume_mode):
                        total_success += 1
                    else:
                        total_failed += 1

                    # 文件之间等待
                    delay = random.uniform(3, 8)
                    print(f'⏸️ 切换到下一个文件前等待 {delay:.1f} 秒...\n')
                    time.sleep(delay)

                print(f'\n\n{"="*60}')
                print(f'✅ 所有文件处理完成!')
                print(f'完成: {total_success} 个, 有失败: {total_failed} 个')
                print(f'{"="*60}')
                return

        # 批量模式
        if batch_file:
            # 检查是否有保存的状态可以恢复
            saved_state = state_manager.load_state() if resume_mode else None

            with open(batch_file, 'r', encoding='utf-8') as f:
                original_data = json.load(f)

            # 获取原始数据列表
            if isinstance(original_data, dict) and 'data' in original_data:
                items = original_data['data']
            elif isinstance(original_data, list):
                items = original_data
            else:
                print('不支持的数据格式')
                return

            # 提取所有 productUrl
            urls = []
            for item in items:
                if isinstance(item, dict) and 'productUrl' in item:
                    url = item['productUrl']
                    if url:
                        if not url.startswith('http'):
                            url = 'https://www.ozon.ru' + url
                        urls.append(url)

            if not urls:
                print('未找到 productUrl')
                return

            # 从保存的状态恢复
            start_index = 0
            crawled_urls = set()
            failed_urls = []

            if saved_state and saved_state.get('batch_file') == batch_file:
                start_index = saved_state.get('current_index', 0)
                crawled_urls = set(saved_state.get('crawled_urls', []))
                failed_urls = saved_state.get('failed_urls', [])
                # 恢复已爬取的数据到 original_data（检查是否已有爬取结果）
                for item in items:
                    item_url = item.get('productUrl', '')
                    if not item_url.startswith('http'):
                        item_url = 'https://www.ozon.ru' + item_url
                    if item_url in crawled_urls:
                        # 检查是否已有爬取结果
                        if not item.get('crawledImages') and not item.get('crawledDescription'):
                            # 如果状态文件中记录已爬取但原文件没有结果，尝试恢复
                            pass

            # 计算未爬取的URL（同时检查原文件中是否已有爬取结果）
            pending_urls = []
            for i, url in enumerate(urls):
                if url in crawled_urls:
                    continue
                # 检查原文件中是否已有爬取结果
                item_has_result = False
                for item in items:
                    item_url = item.get('productUrl', '')
                    if not item_url.startswith('http'):
                        item_url = 'https://www.ozon.ru' + item_url
                    if item_url == url:
                        if item.get('crawledImages') or item.get('crawledDescription'):
                            item_has_result = True
                            crawled_urls.add(url)
                            break
                if not item_has_result:
                    pending_urls.append((i, url))

            mode_str = "强制覆盖" if overwrite else "跳过已有"
            print(f'找到 {len(urls)} 个商品链接 (模式: {mode_str})')
            if start_index > 0 or crawled_urls:
                print(f'📊 当前进度: {start_index}/{len(urls)}, 剩余: {len(pending_urls)} 个待爬取\n')
            else:
                print()

            success_count = 0
            total_crawled = len(crawled_urls)

            # 设置信号处理器
            original_sigint_handler = signal.getsignal(signal.SIGINT)
            pause_requested = [False]  # 用列表包装以便在嵌套函数中修改

            def handle_interrupt(signum, frame):
                if pause_requested[0]:
                    # 第二次 Ctrl+C，直接退出
                    print('\n\n⚠️  强制退出...')
                    signal.signal(signal.SIGINT, original_sigint_handler)
                    raise KeyboardInterrupt
                else:
                    # 第一次 Ctrl+C，暂停
                    pause_requested[0] = True
                    state_manager.pause()
                    print('\n💡 输入 "resume" 并回车可恢复，或按 Ctrl+C 两次完全退出')

            signal.signal(signal.SIGINT, handle_interrupt)

            for i, url in pending_urls:
                # 检查是否需要暂停
                while state_manager.is_paused:
                    try:
                        user_input = input('\n> 输入 "resume" 恢复爬取: ').strip().lower()
                        if user_input == 'resume':
                            state_manager.resume()
                            pause_requested[0] = False
                            break
                    except EOFError:
                        time.sleep(1)
                        continue
                    except Exception:
                        time.sleep(1)
                        continue

                # 按 Ctrl+C 暂停
                if pause_requested[0]:
                    # 保存当前状态
                    state_manager.save_state(batch_file, i + start_index, len(urls), crawled_urls, failed_urls)
                    print(f'\n⏸️  已暂停。可用以下命令恢复：')
                    print(f'   python crawler.py --resume --real-chrome {os.path.basename(batch_file)}')
                    signal.signal(signal.SIGINT, original_sigint_handler)
                    return

                actual_index = i + 1
                print(f'\n[{actual_index}/{len(urls)}] 正在爬取: {url[:80]}...')
                try:
                    data = crawler.crawl(url, overwrite=overwrite, save_to_output=False)
                    if data:
                        # 找到对应的商品，添加图片和描述
                        for item in items:
                            item_url = item.get('productUrl', '')
                            if not item_url.startswith('http'):
                                item_url = 'https://www.ozon.ru' + item_url
                            if item_url == url:
                                item['crawledImages'] = data.get('images', [])
                                item['crawledDescription'] = remove_urls_from_text(data.get('description', ''))
                                # 查找并保存 wbId
                                seerfar_id = item.get('categoryInfo', {}).get('category', {}).get('id')
                                if seerfar_id:
                                    item['wbId'] = lookup_wb_subjectid(seerfar_id)
                                success_count += 1
                                total_crawled += 1
                                crawled_urls.add(url)
                                break

                        # 每爬取一个就立即保存到原文件（防止中断丢失数据）
                        with open(batch_file, 'w', encoding='utf-8') as f:
                            json.dump(original_data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f'爬取出错: {e}')
                    failed_urls.append(url)

                # 定期保存状态（每爬取10个保存一次）
                if actual_index % 10 == 0:
                    state_manager.save_state(batch_file, actual_index, len(urls), crawled_urls, failed_urls)

                # 爬取间隔（防反爬）
                if actual_index < len(urls):
                    # 每个商品之间随机等待（更真实）
                    delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
                    print(f'\n⏸️  下一个商品前等待 {delay:.1f} 秒（防反爬）...')
                    time.sleep(delay)

            # 恢复原始信号处理器
            signal.signal(signal.SIGINT, original_sigint_handler)

            # 完成时清除状态
            state_manager.clear_state()

            # 保存回原文件
            with open(batch_file, 'w', encoding='utf-8') as f:
                json.dump(original_data, f, ensure_ascii=False, indent=2)

            print(f'\n✅ 批量爬取完成! 成功 {success_count}/{len(pending_urls)} 个')
            print(f'总进度: {total_crawled}/{len(urls)} 个商品')
            print(f'失败: {len(failed_urls)} 个')
            if failed_urls:
                print(f'失败链接: {failed_urls[:5]}...' if len(failed_urls) > 5 else f'失败链接: {failed_urls}')
            print(f'结果已直接更新到: {batch_file}')
            return

        while True:
            url = url_from_arg or input('请输入要爬取的网址 (直接回车退出): ').strip()

            if not url:
                print('\n已退出程序')
                break

            if not url.startswith(('http://', 'https://')):
                print('请输入有效的网址 (以 http:// 或 https:// 开头)')
                if url_from_arg:
                    break
                continue

            try:
                crawler.crawl(url)
            except Exception as e:
                print(f'爬取出错: {e}')

            if url_from_arg:
                break

            again = input('\n是否继续爬取其他网址? (y/n): ').strip().lower()
            if again != 'y':
                print('\n已退出程序')
                break

    except KeyboardInterrupt:
        print('\n\n程序被中断')
        # 批量模式下的中断会在循环中处理，这里只处理其他情况的中断
    except Exception as e:
        print(f'程序出错: {e}')
    finally:
        crawler.close()


if __name__ == '__main__':
    print('提示:')
    print('  登录:          python crawler.py --login --real-chrome  (推荐)')
    print('  导入Cookie:    python crawler.py --import --real-chrome')
    print('  爬取单个网页:  python crawler.py [--real-chrome] <网址>')
    print('  批量爬取:      python crawler.py [--real-chrome] <json文件>')
    print('  文件夹批量:     python crawler.py --folder <文件夹路径>')
    print('  强制覆盖:      python crawler.py --force <json文件或网址>')
    print('  --real-chrome  使用系统真实 Chrome（能过滑动验证）')
    print('  --cdp          复用你已经开着的 Chrome（最强防检测，需要先开调试端口）')
    print('  --resume       从上次暂停处恢复继续爬取')
    print('  --clear-state  清除保存的暂停状态，开始新任务')
    print('')
    print('  ⏸️ 暂停功能: 爬取过程中按 Ctrl+C 暂停，输入 "resume" 恢复')
    print('')
    print('  默认已加入人类浏览行为模拟：滚动+随机延迟 5-15秒/页面')
    print('  代理池：在 proxies.txt 里每行一个代理，自动加载并轮换\n')
    print('  【CDP 模式启动步骤】')
    print('  1. 手动启动 Chrome（已经在跑的也行）：')
    print('     "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" \\')
    print('       --remote-debugging-port=9222 \\')
    print('       --user-data-dir="C:\\chrome-crawler-profile"')
    print('  2. 跑爬虫：  python crawler.py --cdp 1.json\n')
    print('  【文件夹批量模式】')
    print('  python crawler.py --folder .           # 当前目录')
    print('  python crawler.py --folder ./data     # 指定目录\n')
    main()
