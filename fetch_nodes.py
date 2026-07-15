#!/usr/bin/env python3
"""
多源节点订阅抓取工具
从多个来源获取最新订阅链接，为每个来源生成独立的 Clash Meta 配置。

来源:
  1. FProxies (Telegram @FProxies)
  2. datiya    (free.datiya.com / OpenRunner/clash-freenode)
  3. osbooting (freenode.osbooting.com)
  4. mlfenx    (www.mlfenx.com/freenode)
  5. clashfree (github.com/free-nodes/clashfree)
  6. bestclash (github.com/PuddinCat/BestClash, 完整 Clash 配置)
  7. au1rxx    (github.com/Au1rxx/free-vpn-subscriptions, 完整 Clash 配置)
  8. v2rayfree (github.com/free-nodes/v2rayfree, v2ray/ss 链接)

输出: output/<source>/ 目录下独立文件
"""

import re
import os
import json
import sys
import html as htmlmod
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
TIMEOUT = 20
OUTPUT_DIR = "output"

# curl_cffi 可选依赖：CI 中用于伪 Chrome 指纹绕过 Cloudflare。
# 本地无 curl_cffi 时自动回退到标准库 urllib。
try:
    from curl_cffi import requests as cffi_requests
    _HAS_CFFI = True
except ImportError:
    _HAS_CFFI = False


def download_subscription_content(url: str) -> bytes:
    """下载订阅原始字节内容（不做任何解码/解压）。

    优先使用 curl_cffi impersonate='chrome' 绕过 Cloudflare 指纹校验；
    未安装 curl_cffi 时回退到标准库 urllib。
    """
    if _HAS_CFFI:
        resp = cffi_requests.get(url, impersonate="chrome", timeout=TIMEOUT)
        return resp.content
    req = Request(url, headers={"User-Agent": USER_AGENT})
    return urlopen(req, timeout=TIMEOUT).read()


def is_cloudflare_block(data: bytes) -> bool:
    """粗略判断下载内容是否为 Cloudflare 验证页（HTML）"""
    head = data[:2048].lower()
    return b"<html" in head or b"<title>just a moment" in head


def write_proxies_txt(clash_url: str) -> str:
    """下载 fproxies 最新 clash 订阅的完整内容并写入根目录 proxies.txt。

    返回写入路径；遇到 Cloudflare 拦截或下载失败时抛 RuntimeError。
    """
    print("📥 [proxies.txt] 下载 clash 订阅内容...", file=sys.stderr)
    content = download_subscription_content(clash_url)
    if is_cloudflare_block(content):
        raise RuntimeError("疑似 Cloudflare 验证页，未写入 proxies.txt")
    path = "proxies.txt"
    with open(path, "wb") as f:
        f.write(content)
    lines = content.count(b"\n") + (0 if content.endswith(b"\n") else 1)
    print(f"✅ [proxies.txt] 已写入 {len(content)} 字节 / {lines} 行")
    return path



def fetch_page(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    resp = urlopen(req, timeout=TIMEOUT)
    return resp.read().decode("utf-8")


# ──────────────────────────────────────────────
# 来源 1: FProxies
# ──────────────────────────────────────────────

FPROXIES_CHANNEL = "https://t.me/s/FProxies"
FPROXIES_FORMATS = ["clash", "base64", "quanx", "urls"]


def fproxies_fetch():
    """解析 FProxies 频道页面，返回订阅列表"""
    html_text = fetch_page(FPROXIES_CHANNEL)
    subs = []
    msg_blocks = re.findall(
        r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
        html_text, re.DOTALL,
    )
    for block in msg_blocks:
        clean = re.sub(r"<br\s*/?>", "\n", block)
        clean = re.sub(r"<[^>]+>", "", clean)
        clean = htmlmod.unescape(clean).strip()

        m = re.search(r"节点订阅[-\s]*(\d{4})", clean)
        if not m:
            continue
        date_str = m.group(1)

        domain_m = re.search(r"(https?://sub\.danhu\.[a-z.]+/)", clean)
        if not domain_m:
            continue
        base_url = domain_m.group(1).rstrip("/")

        paste_m = re.search(r"paste/([A-Za-z0-9_\-@.]+)/", clean)
        if not paste_m:
            continue
        paste_id = paste_m.group(1)

        if paste_id.startswith(("B25", "A25")):
            year = "25"
        elif paste_id.startswith("26"):
            year = "26"
        else:
            year = "26" if "dpdns" in base_url else "25"

        extra_m = re.search(
            r"节点订阅[-\s]*\d{4}[.\s]*\n*(.*?)\n*基础域名", clean, re.DOTALL
        )
        extra = extra_m.group(1).strip() if extra_m else ""

        urls = {fmt: f"{base_url}/paste/{paste_id}/{fmt}" for fmt in FPROXIES_FORMATS}
        subs.append({
            "date": date_str,
            "sort_key": year + date_str,
            "base_url": base_url,
            "paste_id": paste_id,
            "extra": extra,
            "urls": urls,
            "clash_url": urls["clash"],
        })

    subs.sort(key=lambda x: x["sort_key"])
    return subs


# ──────────────────────────────────────────────
# 来源 2: datiya.com (OpenRunner/clash-freenode)
# ──────────────────────────────────────────────

DATIYA_BASE = "https://free.datiya.com"


def datiya_fetch():
    """解析 free.datiya.com 首页，获取最新订阅"""
    html_text = fetch_page(DATIYA_BASE)

    # 提取最新文章日期 YYYYMMDD
    dates = re.findall(r"/post/(\d{8})/", html_text)
    if not dates:
        return []
    dates = sorted(set(dates))

    subs = []
    for date_str in dates:
        # 日期格式: 20260618 → 0618, sort_key 用完整日期
        mmdd = date_str[4:]
        clash_url = f"{DATIYA_BASE}/uploads/{date_str}-clash.yaml"
        v2ray_url = f"{DATIYA_BASE}/uploads/{date_str}-v2ray.txt"

        subs.append({
            "date": mmdd,
            "sort_key": date_str,
            "date_full": date_str,
            "clash_url": clash_url,
            "v2ray_url": v2ray_url,
            "urls": {
                "clash": clash_url,
                "v2ray": v2ray_url,
            },
            "extra": "",
        })

    return subs


# ──────────────────────────────────────────────
# 配置模板
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# 来源 3: osbooting (freenode.osbooting.com)
# ──────────────────────────────────────────────

OSBOOTING_BASE = "https://freenode.osbooting.com"


def osbooting_fetch():
    """解析 freenode.osbooting.com 文章页，获取最新订阅"""
    html_text = fetch_page(OSBOOTING_BASE)

    # 提取文章链接 /freenodes/20260618
    article_dates = re.findall(r'/freenodes/(\d{8})', html_text)
    if not article_dates:
        return []
    article_dates = sorted(set(article_dates))[-3:]

    subs = []
    for date_str in article_dates:
        # 进入文章页找订阅文件
        try:
            article_html = fetch_page(f"{OSBOOTING_BASE}/freenodes/{date_str}")
        except Exception:
            continue

        # 匹配: /nodefiles/20260618MDTF.yaml  /nodefiles/20260618PQRJ.txt
        files = re.findall(
            rf'/nodefiles/{date_str}([A-Za-z]+)\.(yaml|txt)', article_html
        )
        if not files:
            continue

        clash_url = ""
        v2ray_url = ""
        for suffix, ext in files:
            url = f"{OSBOOTING_BASE}/nodefiles/{date_str}{suffix}.{ext}"
            if ext == "yaml":
                clash_url = url
            elif ext == "txt":
                v2ray_url = url

        if not clash_url and not v2ray_url:
            continue

        mmdd = date_str[4:]
        urls = {}
        if clash_url:
            urls["clash"] = clash_url
        if v2ray_url:
            urls["v2ray"] = v2ray_url

        subs.append({
            "date": mmdd,
            "sort_key": date_str,
            "date_full": date_str,
            "clash_url": clash_url,
            "v2ray_url": v2ray_url,
            "urls": urls,
            "extra": "",
        })

    return subs


# ──────────────────────────────────────────────
# 来源 4: mlfenx (www.mlfenx.com/freenode)
# ──────────────────────────────────────────────

MLFENX_BASE = "https://www.mlfenx.com"


def mlfenx_fetch():
    """解析 mlfenx 文章页，获取最新订阅"""
    html_text = fetch_page(f"{MLFENX_BASE}/freenode")

    # 提取文章链接 /archives/960
    article_ids = re.findall(r'/archives/(\d+)', html_text)
    if not article_ids:
        return []
    article_ids = sorted(set(article_ids), key=int)[-3:]

    subs = []
    for aid in article_ids:
        try:
            article_html = fetch_page(f"{MLFENX_BASE}/archives/{aid}")
        except Exception:
            continue

        # 匹配订阅链接: mlfenx.cczzuu.top/node/20260618.yaml
        dates_found = re.findall(
            r'(https?://mlfenx\.[^/]+/node/(\d{8})\.(yaml|txt))', article_html
        )
        if not dates_found:
            continue

        clash_url = ""
        v2ray_url = ""
        date_str = ""
        for full_url, d, ext in dates_found:
            date_str = d
            if ext == "yaml":
                clash_url = full_url
            elif ext == "txt":
                v2ray_url = full_url

        if not clash_url and not v2ray_url:
            continue

        mmdd = date_str[4:]
        urls = {}
        if clash_url:
            urls["clash"] = clash_url
        if v2ray_url:
            urls["v2ray"] = v2ray_url

        subs.append({
            "date": mmdd,
            "sort_key": date_str,
            "date_full": date_str,
            "clash_url": clash_url,
            "v2ray_url": v2ray_url,
            "urls": urls,
            "extra": "",
        })

    return subs


# ──────────────────────────────────────────────
# 来源 5: clashfree (github.com/free-nodes/clashfree)
# ──────────────────────────────────────────────

CLASHFREE_API = "https://api.github.com/repos/free-nodes/clashfree/git/trees/main"
CLASHFREE_RAW = "https://raw.githubusercontent.com/free-nodes/clashfree/main/"

# ── 来源 6/7: 完整 Clash 配置型 (即取即用, 无需 proxy-provider 包裹) ──
BESTCLASH_RAW = "https://raw.githubusercontent.com/PuddinCat/BestClash/main/"
AU1RXX_RAW   = "https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/main/"

# ── 来源 9/10: Ruk1ng001/freeSub (clash.yaml 完整配置 + v2ray 链接) ──
RUK1NG_CLASH_RAW = "https://raw.githubusercontent.com/Ruk1ng001/freeSub/main/clash.yaml"
RUK1NG_V2RAY_RAW = "https://raw.githubusercontent.com/Ruk1ng001/freeSub/main/v2ray"
# ── 来源 11: ovmvo/FreeSub (sub/permanent/mihomo.yaml 完整配置) ──
OVMVO_RAW = "https://raw.githubusercontent.com/ovmvo/FreeSub/main/sub/permanent/mihomo.yaml"

# ── 来源 8: v2rayfree (github.com/free-nodes/v2rayfree) ──
V2RAYFREE_API = "https://api.github.com/repos/free-nodes/v2rayfree/git/trees/main"
V2RAYFREE_RAW = "https://raw.githubusercontent.com/free-nodes/v2rayfree/main/"


def clashfree_fetch():
    """从 GitHub 仓库获取最新 clash 文件"""
    data = fetch_page(CLASHFREE_API)
    tree = json.loads(data).get("tree", [])

    # 找出所有 clash*.yml 文件
    files = []
    for item in tree:
        m = re.match(r"clash(\d{8})\.yml", item.get("path", ""))
        if m:
            files.append(m.group(1))

    if not files:
        return []

    files.sort()
    subs = []
    for date_str in files:
        mmdd = date_str[4:]
        url = f"{CLASHFREE_RAW}clash{date_str}.yml"
        subs.append({
            "date": mmdd,
            "sort_key": date_str,
            "date_full": date_str,
            "clash_url": url,
            "urls": {"clash": url},
            "extra": "",
        })

    return subs


def bestclash_fetch():
    """来源 6: PuddinCat/BestClash — 每30分钟更新的完整 Clash 配置。

    仓库根目录 proxies.yaml 即为即用型 Clash Meta 配置 (proxies+groups+rules)。
    标记 raw_clash=True, write_source_output 直接保存原始内容而不包 proxy-provider。
    """
    url = BESTCLASH_RAW + "proxies.yaml"
    return [{
        "date": "latest",
        "sort_key": "99999999",          # 永为最新
        "raw_clash": True,
        "clash_url": url,
        "urls": {"clash": url},
        "extra": "BestClash 完整 Clash 配置 (PuddinCat/BestClash)",
    }]


def au1rxx_fetch():
    """来源 7: Au1rxx/free-vpn-subscriptions — 每小时刷新的完整 Clash 配置。

    output/clash.yaml 为即用型 Clash Meta 配置 (proxies+groups+rules)。
    标记 raw_clash=True, 直接保存原始内容。
    """
    url = AU1RXX_RAW + "output/clash.yaml"
    return [{
        "date": "latest",
        "sort_key": "99999998",
        "raw_clash": True,
        "clash_url": url,
        "urls": {"clash": url},
        "extra": "Au1rxx 完整 Clash 配置 (Au1rxx/free-vpn-subscriptions)",
    }]


def v2rayfree_fetch():
    """来源 8: free-nodes/v2rayfree — 每日多更的 v2ray/ss 链接 (base64 行)。

    仓库文件形如 vYYYYMMDD[1-2], 内容为 base64 编码的 ss:///vmess:// 等链接。
    无原生 clash 文件, 故 clash_url 留空, 仅输出 latest_v2ray.txt (原始内容)。
    """
    data = fetch_page(V2RAYFREE_API)
    tree = json.loads(data).get("tree", [])
    files = []
    for item in tree:
        m = re.match(r"v(\d{8})(\d?)\.?", item.get("path", ""))
        if m:
            date_full = m.group(1)
            suffix = m.group(2) or "1"
            files.append((date_full + suffix, date_full, suffix))
    if not files:
        return []
    files.sort()
    subs = []
    for sort_key, date_full, suffix in files:
        url = f"{V2RAYFREE_RAW}v{date_full}{suffix}"
        mmdd = date_full[4:]
        subs.append({
            "date": mmdd,
            "sort_key": sort_key,
            "clash_url": None,           # 无 clash 格式, 跳过 config.yaml
            "urls": {"v2ray": url},
            "extra": f"v2rayfree 链接 ({date_full}{suffix})",
        })
    return subs


def generate_config(clash_url: str, source_name: str) -> str:
    """生成 Clash Meta 主配置"""
    return f'''# ============================================================
# Clash Meta 配置 — {source_name}
# 自动生成，请勿手动编辑
# ============================================================

mixed-port: 7890
allow-lan: true
bind-address: "*"
mode: rule
log-level: info
ipv6: false
external-controller: 127.0.0.1:9090
global-client-fingerprint: chrome

sniffer:
  enable: true
  sniff:
    HTTP:
      ports: [80, 8080-8880]
      override-destination: true
    TLS:
      ports: [443, 8443]
    QUIC:
      ports: [443, 8443]
  skip-domain:
    - "Mijia Cloud"
    - "+.push.apple.com"

dns:
  enable: true
  listen: "0.0.0.0:1053"
  ipv6: false
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - "*.lan"
    - "*.local"
    - "+.msftconnecttest.com"
    - "+.msftncsi.com"
    - "localhost.ptlogin2.qq.com"
  default-nameserver:
    - 223.5.5.5
    - 119.29.29.29
  nameserver:
    - "https://dns.alidns.com/dns-query"
    - "https://doh.pub/dns-query"
  fallback:
    - "https://dns.cloudflare.com/dns-query"
    - "https://dns.google/dns-query"
  fallback-filter:
    geoip: true
    geoip-code: CN
    ipcidr:
      - 240.0.0.0/4

proxy-providers:
  provider:
    type: http
    url: "{clash_url}"
    interval: 3600
    path: ./proxy_providers/{source_name}.yaml
    health-check:
      enable: true
      url: https://www.gstatic.com/generate_204
      interval: 300
      lazy: true

proxy-groups:
  - name: "🚀 节点选择"
    type: select
    proxies:
      - "♻️ 自动选择"
      - "🇭🇰 香港节点"
      - "🇯🇵 日本节点"
      - "🇸🇬 新加坡节点"
      - "🇺🇸 美国节点"
      - "🧿 其它地区"
      - "DIRECT"
    use:
      - provider

  - name: "♻️ 自动选择"
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    lazy: true
    use:
      - provider

  - name: "🇭🇰 香港节点"
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    lazy: true
    use:
      - provider
    filter: "(?i)🇭🇰|HK|Hong.?Kong"

  - name: "🇯🇵 日本节点"
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    lazy: true
    use:
      - provider
    filter: "(?i)🇯🇵|JP|Japan"

  - name: "🇸🇬 新加坡节点"
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    lazy: true
    use:
      - provider
    filter: "(?i)🇸🇬|SG|Singapore"

  - name: "🇺🇸 美国节点"
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    lazy: true
    use:
      - provider
    filter: "(?i)🇺🇸|US|United.?States"

  - name: "🧿 其它地区"
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
    lazy: true
    use:
      - provider
    filter: "(?i)CA|AU|FR|DE|GB|KR|TW|IN|BR"

  - name: "🐟 漏网之鱼"
    type: select
    proxies:
      - "🚀 节点选择"
      - "DIRECT"

rules:
  - GEOIP,LAN,DIRECT
  - DOMAIN-SUFFIX,local,DIRECT
  - GEOSITE,cn,DIRECT
  - GEOIP,cn,DIRECT
  - GEOSITE,google,🚀 节点选择
  - GEOSITE,github,🚀 节点选择
  - GEOSITE,telegram,🚀 节点选择
  - GEOSITE,twitter,🚀 节点选择
  - GEOSITE,youtube,🚀 节点选择
  - GEOSITE,netflix,🚀 节点选择
  - GEOSITE,openai,🚀 节点选择
  - MATCH,🐟 漏网之鱼
'''


# ──────────────────────────────────────────────
# 输出
# ──────────────────────────────────────────────

def ruk1ng_clash_fetch():
    """来源 9: Ruk1ng001/freeSub 的 clash.yaml — 完整 Clash 配置 (即取即用)。"""
    return [{
        "date": "latest",
        "sort_key": "99999997",
        "raw_clash": True,
        "clash_url": RUK1NG_CLASH_RAW,
        "urls": {"clash": RUK1NG_CLASH_RAW},
        "extra": "Ruk1ng001/freeSub 完整 Clash 配置",
    }]


def ruk1ng_v2ray_fetch():
    """来源 10: Ruk1ng001/freeSub 的 v2ray 文件 — base64 编码的 ss/vmess/vless/trojan 链接。"""
    return [{
        "date": "latest",
        "sort_key": "99999996",
        "clash_url": None,
        "urls": {"v2ray": RUK1NG_V2RAY_RAW},
        "extra": "Ruk1ng001/freeSub v2ray 链接",
    }]


def ovmvo_fetch():
    """来源 11: ovmvo/FreeSub 的 sub/permanent/mihomo.yaml — 完整 Clash 配置 (即取即用)。"""
    return [{
        "date": "latest",
        "sort_key": "99999995",
        "raw_clash": True,
        "clash_url": OVMVO_RAW,
        "urls": {"clash": OVMVO_RAW},
        "extra": "ovmvo/FreeSub 完整 Clash 配置",
    }]


def extract_clash_proxies(content: str) -> str:
    """从完整 Clash 配置文本中提取 proxies: 节点块 (解码后的节点清单)。"""
    lines = content.splitlines()
    out = []
    capture = False
    for line in lines:
        if not capture:
            if re.match(r"^proxies:\s*$", line):
                capture = True
                out.append(line)
            continue
        if line.strip() == "":
            out.append(line)
            continue
        # 遇到下一个顶级 key (行首非缩进且非列表项) 即结束
        if not line[0].isspace() and not line.startswith("- "):
            break
        out.append(line)
    return "\n".join(out).strip() + "\n"


def decode_v2ray_links(content: bytes) -> str:
    """将 v2ray 源 (base64 编码的 ss:///vmess:// 链接) 解码为可读链接行。"""
    import base64
    text = content.decode("utf-8", "replace").strip()
    rows = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            padded = raw + "=" * (-len(raw) % 4)
            decoded = base64.b64decode(padded).decode("utf-8", "replace")
            if "://" in decoded:
                rows.append(decoded.strip())
                continue
        except Exception:
            pass
        rows.append(raw)
    return "\n".join(rows) + "\n"


def write_source_output(source: str, latest: dict, all_subs: list, label: str):
    """为单个来源写入全部输出文件"""
    outdir = f"{OUTPUT_DIR}/{source}"
    os.makedirs(outdir, exist_ok=True)

    urls = latest["urls"]

    # latest.txt
    with open(f"{outdir}/latest.txt", "w") as f:
        f.write(f"# {label} 最新订阅 ({latest['date']})\n")
        for fmt, url in urls.items():
            f.write(url + "\n")

    # latest_*.txt
    for fmt, url in urls.items():
        with open(f"{outdir}/latest_{fmt}.txt", "w") as f:
            f.write(url + "\n")

    # subscriptions.json (去重累积)
    json_path = f"{outdir}/subscriptions.json"
    existing = {}
    if os.path.exists(json_path):
        try:
            with open(json_path) as f:
                for item in json.load(f):
                    existing[item["sort_key"]] = item
        except (json.JSONDecodeError, KeyError):
            pass

    for sub in all_subs:
        existing[sub["sort_key"]] = {
            "date": sub["date"],
            "sort_key": sub["sort_key"],
            "extra": sub.get("extra", ""),
            "urls": sub["urls"],
        }

    merged = sorted(existing.values(), key=lambda x: x["sort_key"])
    with open(json_path, "w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # config.yaml
    clash_url = latest.get("clash_url")
    if latest.get("raw_clash") and clash_url:
        # 完整 Clash 配置型源: 直接保存原始内容 (即取即用)
        raw = download_subscription_content(clash_url).decode("utf-8", "replace")
        with open(f"{outdir}/config.yaml", "w") as f:
            f.write(raw)
    elif clash_url:
        config = generate_config(clash_url, source)
        with open(f"{outdir}/config.yaml", "w") as f:
            f.write(config)
    # 否则 (clash_url 为 None, 仅 v2ray/ss 等): 跳过 config.yaml

    # latest_nodes.txt — 节点内容快照 (clash 源提取 proxies 块, v2ray 源解码链接)
    try:
        nodes_url = latest.get("clash_url")
        if nodes_url:
            raw = download_subscription_content(nodes_url)
            nodes_text = extract_clash_proxies(raw.decode("utf-8", "replace"))
        elif latest.get("urls", {}).get("v2ray"):
            raw = download_subscription_content(latest["urls"]["v2ray"])
            nodes_text = decode_v2ray_links(raw)
        else:
            nodes_text = ""
        if nodes_text.strip():
            with open(f"{outdir}/latest_nodes.txt", "w") as f:
                f.write(nodes_text)
    except Exception as e:
        print(f"❌ [{source}] latest_nodes.txt: {e}", file=sys.stderr)

    return outdir


# ──────────────────────────────────────────────
# 主函数
# ──────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── FProxies ──
    print("📡 [FProxies] 获取 Telegram 频道...", file=sys.stderr)
    try:
        fp_subs = fproxies_fetch()
        if fp_subs:
            fp_latest = fp_subs[-1]
            fp_dir = write_source_output("fproxies", fp_latest, fp_subs, "FProxies")
            print(f"✅ [FProxies] {len(fp_subs)} 次订阅, 最新: {fp_latest['date']}")
            print(f"   clash: {fp_latest['urls']['clash']}")
            print(f"   → {fp_dir}/")

            # 下载完整订阅内容到根目录 proxies.txt
            try:
                write_proxies_txt(fp_latest["urls"]["clash"])
            except Exception as e:
                print(f"❌ [proxies.txt] {e}", file=sys.stderr)

        else:
            print("⚠️ [FProxies] 未找到订阅")
    except Exception as e:
        print(f"❌ [FProxies] {e}", file=sys.stderr)

    print()

    # ── datiya / OpenRunner ──
    print("📡 [datiya] 获取 free.datiya.com...", file=sys.stderr)
    try:
        dt_subs = datiya_fetch()
        if dt_subs:
            dt_latest = dt_subs[-1]
            dt_dir = write_source_output("datiya", dt_latest, dt_subs, "datiya (OpenRunner/clash-freenode)")
            print(f"✅ [datiya] {len(dt_subs)} 次订阅, 最新: {dt_latest['date']}")
            print(f"   clash:  {dt_latest['urls']['clash']}")
            print(f"   v2ray:  {dt_latest['urls']['v2ray']}")
            print(f"   → {dt_dir}/")
        else:
            print("⚠️ [datiya] 未找到订阅")
    except Exception as e:
        print(f"❌ [datiya] {e}", file=sys.stderr)

    print()

    # ── osbooting ──
    print("📡 [osbooting] 获取 freenode.osbooting.com...", file=sys.stderr)
    try:
        ob_subs = osbooting_fetch()
        if ob_subs:
            ob_latest = ob_subs[-1]
            ob_dir = write_source_output("osbooting", ob_latest, ob_subs, "osbooting (freenode.osbooting.com)")
            print(f"✅ [osbooting] {len(ob_subs)} 次订阅, 最新: {ob_latest['date']}")
            if ob_latest.get("clash_url"):
                print(f"   clash: {ob_latest['clash_url']}")
            if ob_latest.get("v2ray_url"):
                print(f"   v2ray: {ob_latest['v2ray_url']}")
            print(f"   → {ob_dir}/")
        else:
            print("⚠️ [osbooting] 未找到订阅")
    except Exception as e:
        print(f"❌ [osbooting] {e}", file=sys.stderr)

    print()

    # ── mlfenx ──
    print("📡 [mlfenx] 获取 www.mlfenx.com...", file=sys.stderr)
    try:
        ml_subs = mlfenx_fetch()
        if ml_subs:
            ml_latest = ml_subs[-1]
            ml_dir = write_source_output("mlfenx", ml_latest, ml_subs, "mlfenx (www.mlfenx.com)")
            print(f"✅ [mlfenx] {len(ml_subs)} 次订阅, 最新: {ml_latest['date']}")
            if ml_latest.get("clash_url"):
                print(f"   clash: {ml_latest['clash_url']}")
            if ml_latest.get("v2ray_url"):
                print(f"   v2ray: {ml_latest['v2ray_url']}")
            print(f"   → {ml_dir}/")
        else:
            print("⚠️ [mlfenx] 未找到订阅")
    except Exception as e:
        print(f"❌ [mlfenx] {e}", file=sys.stderr)

    print()

    # ── clashfree ──
    print("📡 [clashfree] 获取 GitHub 仓库...", file=sys.stderr)
    try:
        cf_subs = clashfree_fetch()
        if cf_subs:
            cf_latest = cf_subs[-1]
            cf_dir = write_source_output("clashfree", cf_latest, cf_subs, "clashfree (free-nodes/clashfree)")
            print(f"✅ [clashfree] {len(cf_subs)} 次订阅, 最新: {cf_latest['date']}")
            print(f"   clash: {cf_latest['clash_url']}")
            print(f"   → {cf_dir}/")
        else:
            print("⚠️ [clashfree] 未找到订阅")
    except Exception as e:
        print(f"❌ [clashfree] {e}", file=sys.stderr)

    print()

    # ── bestclash (完整 Clash 配置) ──
    print("📡 [bestclash] 获取 PuddinCat/BestClash...", file=sys.stderr)
    try:
        bc_subs = bestclash_fetch()
        if bc_subs:
            bc_latest = bc_subs[-1]
            bc_dir = write_source_output("bestclash", bc_latest, bc_subs, "bestclash (PuddinCat/BestClash)")
            print(f"✅ [bestclash] 完整 Clash 配置已保存")
            print(f"   clash: {bc_latest['urls']['clash']}")
            print(f"   → {bc_dir}/")
        else:
            print("⚠️ [bestclash] 未获取到配置")
    except Exception as e:
        print(f"❌ [bestclash] {e}", file=sys.stderr)

    print()

    # ── au1rxx (完整 Clash 配置) ──
    print("📡 [au1rxx] 获取 Au1rxx/free-vpn-subscriptions...", file=sys.stderr)
    try:
        ax_subs = au1rxx_fetch()
        if ax_subs:
            ax_latest = ax_subs[-1]
            ax_dir = write_source_output("au1rxx", ax_latest, ax_subs, "au1rxx (free-vpn-subscriptions)")
            print(f"✅ [au1rxx] 完整 Clash 配置已保存")
            print(f"   clash: {ax_latest['urls']['clash']}")
            print(f"   → {ax_dir}/")
        else:
            print("⚠️ [au1rxx] 未获取到配置")
    except Exception as e:
        print(f"❌ [au1rxx] {e}", file=sys.stderr)

    print()

    # ── v2rayfree (v2ray/ss 链接) ──
    print("📡 [v2rayfree] 获取 free-nodes/v2rayfree...", file=sys.stderr)
    try:
        vf_subs = v2rayfree_fetch()
        if vf_subs:
            vf_latest = vf_subs[-1]
            vf_dir = write_source_output("v2rayfree", vf_latest, vf_subs, "v2rayfree (free-nodes/v2rayfree)")
            print(f"✅ [v2rayfree] {len(vf_subs)} 份链接, 最新: {vf_latest['date']}")
            print(f"   v2ray: {vf_latest['urls']['v2ray']}")
            print(f"   → {vf_dir}/")
        else:
            print("⚠️ [v2rayfree] 未找到链接")
    except Exception as e:
        print(f"❌ [v2rayfree] {e}", file=sys.stderr)

    print()

    print()

    # ── ruk1ng (clash 完整配置) ──
    print("📡 [ruk1ng] 获取 Ruk1ng001/freeSub (clash)...", file=sys.stderr)
    try:
        rk_subs = ruk1ng_clash_fetch()
        if rk_subs:
            rk_latest = rk_subs[-1]
            rk_dir = write_source_output("ruk1ng", rk_latest, rk_subs, "ruk1ng-clash (Ruk1ng001/freeSub)")
            print(f"✅ [ruk1ng] 完整 Clash 配置已保存")
            print(f"   clash: {rk_latest['urls']['clash']}")
            print(f"   → {rk_dir}/")
        else:
            print("⚠️ [ruk1ng] 未获取到配置")
    except Exception as e:
        print(f"❌ [ruk1ng] {e}", file=sys.stderr)

    print()

    # ── ruk1ng_v2ray (base64 链接) ──
    print("📡 [ruk1ng_v2ray] 获取 Ruk1ng001/freeSub (v2ray)...", file=sys.stderr)
    try:
        rkv_subs = ruk1ng_v2ray_fetch()
        if rkv_subs:
            rkv_latest = rkv_subs[-1]
            rkv_dir = write_source_output("ruk1ng_v2ray", rkv_latest, rkv_subs, "ruk1ng-v2ray (Ruk1ng001/freeSub)")
            print(f"✅ [ruk1ng_v2ray] v2ray 链接已保存")
            print(f"   v2ray: {rkv_latest['urls']['v2ray']}")
            print(f"   → {rkv_dir}/")
        else:
            print("⚠️ [ruk1ng_v2ray] 未获取到链接")
    except Exception as e:
        print(f"❌ [ruk1ng_v2ray] {e}", file=sys.stderr)

    print()

    # ── ovmvo (clash 完整配置) ──
    print("📡 [ovmvo] 获取 ovmvo/FreeSub...", file=sys.stderr)
    try:
        ov_subs = ovmvo_fetch()
        if ov_subs:
            ov_latest = ov_subs[-1]
            ov_dir = write_source_output("ovmvo", ov_latest, ov_subs, "ovmvo (ovmvo/FreeSub)")
            print(f"✅ [ovmvo] 完整 Clash 配置已保存")
            print(f"   clash: {ov_latest['urls']['clash']}")
            print(f"   → {ov_dir}/")
        else:
            print("⚠️ [ovmvo] 未获取到配置")
    except Exception as e:
        print(f"❌ [ovmvo] {e}", file=sys.stderr)

    print()

    print()
    print(f"💾 全部结果已写入 {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
