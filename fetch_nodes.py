#!/usr/bin/env python3
"""
多源节点订阅抓取工具
从多个来源获取最新订阅链接，为每个来源生成独立的 Clash Meta 配置。

来源:
  1. FProxies   (Telegram @FProxies)
  2. datiya     (free.datiya.com)
  3. osbooting  (freenode.osbooting.com)
  4. mlfenx     (www.mlfenx.com/freenode)
  5. clashfree  (github.com/free-nodes/clashfree)
  6. bestclash  (github.com/PuddinCat/BestClash)
  7. au1rxx     (github.com/Au1rxx/free-vpn-subscriptions)
  8. v2rayfree  (github.com/free-nodes/v2rayfree)
  9. ruk1ng     (github.com/Ruk1ng001/freeSub, clash)
 10. ruk1ng_v2ray (github.com/Ruk1ng001/freeSub, v2ray/ss)
 11. ovmvo      (github.com/ovmvo/FreeSub)
 12. v2raynnodes_clash (github.com/v2raynnodes/v2rayfree, clashmeta)
 13. v2raynnodes_v2ray (github.com/v2raynnodes/v2rayfree, mihomo)
 14. ts_sf_fly  (github.com/ts-sf/fly, Clash)
 15. free18     (github.com/free18/v2ray, Clash)
 16. automerge  (github.com/chengaopan/AutoMergePublicNodes, Clash)
 17. nomorewalls (github.com/peasoft/NoMoreWalls, v2ray/ss)
 18. pawdroid   (github.com/Pawdroid/Free-servers, v2ray)
 19. barabama_* (github.com/Barabama/FreeNodes, v2ray, 7子站)
 20. flikify    (github.com/Flikify/Free-Node, Clash)
 21. shaoyouvip (github.com/shaoyouvip/free, Clash)

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
from urllib.parse import quote, unquote

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

# ── 来源 12/13: v2raynnodes/v2rayfree (聚合多站点的完整配置) ──
V2RAYN_CLASH_RAW  = "https://raw.githubusercontent.com/v2raynnodes/v2rayfree/main/nodes/clashmeta.yaml"
V2RAYN_V2RAY_RAW = "https://raw.githubusercontent.com/v2raynnodes/v2rayfree/main/nodes/nodev2ray.yaml"

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


def v2raynnodes_clash_fetch():
    """来源 12: v2raynnodes/v2rayfree 的 nodes/clashmeta.yaml — 完整 Clash 配置。"""
    return [{
        "date": "latest",
        "sort_key": "99999994",
        "raw_clash": True,
        "clash_url": V2RAYN_CLASH_RAW,
        "urls": {"clash": V2RAYN_CLASH_RAW},
        "extra": "v2raynnodes/v2rayfree 完整 Clash 配置",
    }]


def v2raynnodes_v2ray_fetch():
    """来源 13: v2raynnodes/v2rayfree 的 nodes/nodev2ray.yaml — 完整 Clash 配置 (yaml 格式, 非 base64)。"""
    return [{
        "date": "latest",
        "sort_key": "99999993",
        "raw_clash": True,
        "clash_url": V2RAYN_V2RAY_RAW,
        "urls": {"clash": V2RAYN_V2RAY_RAW},
        "extra": "v2raynnodes/v2rayfree 完整 Clash 配置",
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



# ──────────────────────────────────────────────
# Clash YAML ↔ V2Ray/SS/Trojan URI 相互转化
# ──────────────────────────────────────────────

def _parse_clash_node_to_dict(line: str) -> dict:
    """解析单行 Clash 节点 (- {name: ...} 或正常缩进形式) 为 dict。"""
    line = line.strip()
    if not line.startswith("-"):
        return {}
    inner = line[1:].strip()
    if inner.startswith("{"):
        try:
            import yaml
            return yaml.safe_load(inner) or {}
        except Exception:
            return {}
    # 多行形式 - name: xxx (后续行在调用处拼装)
    return {}

def clash_node_to_uri(node: dict) -> str:
    """将单个 Clash 节点 dict 转化为 V2Ray/SS/Trojan URI。"""
    import base64
    ntype = (node.get("type") or "").lower()
    name = node.get("name", "node")
    server = node.get("server", "")
    port = node.get("port", 0)
    if ntype == "ss" or ntype == "shadowsocks":
        method = node.get("cipher", "aes-256-gcm")
        password = node.get("password", "")
        userinfo = f"{method}:{password}"
        raw = base64.b64encode(userinfo.encode()).decode()
        uri = f"ss://{raw}@{server}:{port}#"
    elif ntype == "trojan":
        password = node.get("password", "")
        query = _build_query(node, ["sni", "alpn", "allowInsecure", "skip-cert-verify"])
        uri = f"trojan://{password}@{server}:{port}?{query}#"
    elif ntype == "vmess":
        cfg = {
            "v": "2",
            "ps": name,
            "add": server,
            "port": port,
            "id": node.get("uuid", ""),
            "aid": node.get("alterId", 0),
            "net": node.get("network", "tcp"),
            "type": "none",
            "host": "",
            "path": "",
            "tls": "tls" if node.get("tls") else "",
            "sni": node.get("servername", ""),
        }
        if node.get("network") == "ws":
            ws = node.get("ws-opts", {})
            cfg["host"] = ws.get("headers", {}).get("Host", "")
            cfg["path"] = ws.get("path", "")
        raw = base64.b64encode(json.dumps(cfg, ensure_ascii=False).encode()).decode()
        uri = f"vmess://{raw}#"
    elif ntype == "vless":
        uuid = node.get("uuid", "")
        flow = node.get("flow", "")
        query = f"encryption=none&security={'tls' if node.get('tls') else 'none'}"
        if flow:
            query += f"&flow={flow}"
        net = node.get("network", "tcp")
        if net:
            query += f"&type={net}"
        if net == "ws":
            ws = node.get("ws-opts", {})
            query += f"&path={ws.get('path', '')}"
            query += f"&host={ws.get('headers', {}).get('Host', '')}"
        if node.get("servername"):
            query += f"&sni={node.get('servername')}"
        if node.get("skip-cert-verify"):
            query += "&allowInsecure=1"
        uri = f"vless://{uuid}@{server}:{port}?{query}#"
    else:
        return ""  # 不支持的类型 (hysteria2 anytls 等暂不转)
    return uri + quote(name, safe="")

def _build_query(node: dict, keys: list) -> str:
    params = []
    for k in keys:
        v = node.get(k)
        if v is None:
            continue
        if isinstance(v, bool):
            v = "1" if v else "0"
        params.append(f"{k}={v}")
    return "&".join(params)

def clash_block_to_uris(block: str) -> list:
    """将 Clash proxies 块转化为 URI 列表 (仅支持 ss/trojan/vmess/vless)。"""
    import yaml
    try:
        data = yaml.safe_load(block)
        proxies = data.get("proxies", []) if isinstance(data, dict) else []
    except Exception:
        return []
    uris = []
    for node in proxies:
        if not isinstance(node, dict):
            continue
        uri = clash_node_to_uri(node)
        if uri:
            uris.append(uri)
    return uris

def uri_to_clash_node(uri: str) -> dict:
    """将 V2Ray/SS/Trojan URI 转化为 Clash 节点 dict。"""
    import base64
    uri = uri.strip()
    if "://" not in uri:
        return {}
    scheme, rest = uri.split("://", 1)
    scheme = scheme.lower()
    # 去掉 fragment (#name)
    if "#" in rest:
        body, frag = rest.rsplit("#", 1)
        name = unquote(frag)
    else:
        body, name = rest, ""
    if "@" in body:
        userinfo, serverpart = body.rsplit("@", 1)
    else:
        userinfo, serverpart = "", body
    # 去掉 query string (?key=val...) 后再析出 server:port
    clean = serverpart.split("?")[0]
    if ":" in clean:
        server, port_str = clean.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            port = 0
        server = server.strip("[]")
    else:
        server, port = clean, 0
    if "?" in userinfo:
        userinfo, _ = userinfo.split("?", 1)
    if scheme == "ss":
        # userinfo 可能是 base64(method:pass)
        try:
            decoded = base64.b64decode(userinfo + "=" * (-len(userinfo) % 4)).decode()
            method, password = decoded.split(":", 1)
        except Exception:
            method, password = "aes-256-gcm", userinfo
        return {"name": name or server, "type": "ss", "server": server,
                "port": port, "cipher": method, "password": password, "udp": True}
    if scheme == "trojan":
        q = _parse_query(body)
        node = {"name": name or server, "type": "trojan", "server": server,
                "port": port, "password": userinfo, "udp": True}
        _apply_query(node, q)
        return node
    if scheme == "vmess":
        try:
            cfg = json.loads(base64.b64decode(userinfo + "=" * (-len(userinfo) % 4)).decode())
        except Exception:
            return {}
        node = {"name": cfg.get("ps", name or server), "type": "vmess",
                "server": cfg.get("add", server), "port": int(cfg.get("port", port)),
                "uuid": cfg.get("id", ""), "alterId": cfg.get("aid", 0),
                "cipher": "auto", "udp": True}
        net = cfg.get("net", "tcp")
        if net == "ws":
            node["network"] = "ws"
            node["ws-opts"] = {"path": cfg.get("path", ""),
                               "headers": {"Host": cfg.get("host", "")}}
        if cfg.get("tls"):
            node["tls"] = True
        if cfg.get("sni"):
            node["servername"] = cfg.get("sni")
        return node
    if scheme == "vless":
        q = _parse_query(body)
        node = {"name": name or server, "type": "vless", "server": server,
                "port": port, "uuid": userinfo, "udp": True}
        if q.get("flow"):
            node["flow"] = q["flow"]
        if q.get("type") and q["type"] != "tcp":
            node["network"] = q["type"]
        if q.get("type") == "ws":
            node["ws-opts"] = {"path": q.get("path", ""),
                               "headers": {"Host": q.get("host", "")}}
        if q.get("security") == "tls" or q.get("sni"):
            node["tls"] = True
        if q.get("sni"):
            node["servername"] = q["sni"]
        if q.get("allowInsecure") == "1":
            node["skip-cert-verify"] = True
        return node
    return {}

def _parse_query(body: str) -> dict:
    if "?" not in body:
        return {}
    q = body.rsplit("?", 1)[1]
    out = {}
    for pair in q.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            out[k] = unquote(v)
    return out

def _apply_query(node: dict, q: dict):
    if q.get("sni"):
        node["servername"] = q["sni"]
    if q.get("alpn"):
        node["alpn"] = q["alpn"].split(",")
    if q.get("allowInsecure") == "1" or q.get("allowInsecure") == "true":
        node["skip-cert-verify"] = True
    if q.get("peer"):
        node["servername"] = q["peer"]

def uri_block_to_clash(uris: list) -> str:
    """将 URI 列表转化为 Clash proxies 块 (YAML)。"""
    nodes = []
    for uri in uris:
        node = uri_to_clash_node(uri)
        if node:
            nodes.append(node)
    if not nodes:
        return ""
    return yaml.safe_dump({"proxies": nodes}, allow_unicode=True, sort_keys=False)

# ──────────────────────────────────────────────
# 跨源合并 & 健康度监控
# ──────────────────────────────────────────────

# 所有来源的配置 (name → {clash_url, decode_v2ray_url})
# 由各 fetch 函数的返回值自动填充
ALL_SOURCES = {}  # name → {"clash_url": str|None, "decode_v2ray_url": str|None, "label": str}

def _register_source(name: str, clash_url=None, decode_v2ray_url=None, label=""):
    """注册一个来源，供后续合并和健康监控使用"""
    ALL_SOURCES[name] = {
        "clash_url": clash_url,
        "decode_v2ray_url": decode_v2ray_url,
        "label": label,
    }

def write_source_output(source: str, latest: dict, all_subs: list, label: str):

    """为单个来源写入全部输出文件"""
    outdir = f"{OUTPUT_DIR}/{source}"
    os.makedirs(outdir, exist_ok=True)

    urls = latest["urls"]

    # 注册来源到全局表 (供合并和健康监控)
    _register_source(
        source,
        clash_url=latest.get("clash_url"),
        decode_v2ray_url=latest.get("urls", {}).get("v2ray"),
        label=label,
    )

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
# 功能 1: 跨源合并去重输出
# ──────────────────────────────────────────────

def _merge_clash_proxies(proxy_blocks: list) -> str:
    """合并所有来源的 proxies 块，按节点名称去重，返回 YAML proxies: 段文本。"""
    seen = {}
    order = []
    for block in proxy_blocks:
        for line in block.splitlines():
            line = line.rstrip()
            # 匹配 "- name: xxx" 或 "- {name: xxx" 形式
            m = re.match(r'^\s*-\s+(?:\{\s*)?name:\s*"?([^"\n]+?)"?(?:\s|,|$)', line)

            if m:
                name = m.group(1).strip()
                if name not in seen:
                    seen[name] = True
                    order.append(name)
    # 重新解析每个 block 找到对应节点完整定义
    merged = {}
    for block in proxy_blocks:
        lines = block.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            m = re.match(r'^\s*-\s+(?:\{\s*)?name:\s*"?([^"\n]+?)"?(?:\s|,|$)', line)

            if m:
                name = m.group(1).strip()
                if name in seen and name not in merged:
                    # 收集从本行到下一个同级 "-" 或顶级 key 的所有行
                    node_lines = []
                    indent = len(line) - len(line.lstrip())
                    j = i
                    while j < len(lines):
                        cur = lines[j]
                        if j > i:
                            cur_indent = len(cur) - len(cur.lstrip()) if cur.strip() else 999
                            # 遇到下一个列表项 (同级 "- ") 或更深缩进的顶级键则停止
                            if cur.strip().startswith("- ") and cur_indent <= indent:
                                break
                            if not cur.strip().startswith("- ") and cur_indent <= indent and cur.strip():
                                break
                        node_lines.append(cur)
                        j += 1
                    merged[name] = "\n".join(node_lines)
                    i = j
                    continue
            i += 1
    if not merged:
        return ""
    out = ["proxies:"]
    for name in order:
        if name in merged:
            out.append(merged[name])
    return "\n".join(out) + "\n"


def _merge_v2ray_links(link_blocks: list) -> str:
    """合并所有 v2ray 解码后的链接，按链接去重。"""
    seen = set()
    merged = []
    for block in link_blocks:
        for raw in block.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            if raw not in seen:
                seen.add(raw)
                merged.append(raw)
    return "\n".join(merged) + "\n"



def build_merged_output():
    """生成 output/all_nodes/ — 跨源去重，Clash YAML ↔ URI 双向融合。

    统一中间格式: URI (ss:// / vmess:// / trojan:// / vless://)
    所有来源的 clash/v2ray 全部转为 URI → 去重 → 双向输出
      - merged.yaml       Clash YAML 格式 (即取即用)
      - merged_uris.txt   URI 链接格式 (ss:// / vmess:// / ...)
      - latest_nodes.txt  两者兼有 (分区块展示)
      - latest.txt        订阅 URL 汇总
    """
    outdir = f"{OUTPUT_DIR}/all_nodes"
    os.makedirs(outdir, exist_ok=True)

    all_uris = {}      # uri_normalized → uri_original  (去重)
    all_urls = set()   # 订阅 URL 列表
    failed = []

    for name, cfg in ALL_SOURCES.items():
        clash_url = cfg.get("clash_url")
        v2ray_url = cfg.get("decode_v2ray_url")

        # ── Clash 源: YAML → URI ──
        if clash_url:
            all_urls.add(clash_url)
            try:
                raw = download_subscription_content(clash_url)
                text = raw.decode("utf-8", "replace")
                # 先尝试提取 proxies 块 → 转 URI
                block = extract_clash_proxies(text)
                if block.strip():
                    for uri in clash_block_to_uris(block):
                        if uri:
                            key = _normalize_uri_key(uri)
                            all_uris[key] = uri
                # 如果 block 为空 (纯 v2ray 链接文件)，直接解码 base64 行
                else:
                    for uri in decode_v2ray_links(raw).splitlines():
                        uri = uri.strip()
                        if uri and "://" in uri:
                            key = _normalize_uri_key(uri)
                            all_uris[key] = uri
            except Exception as e:
                failed.append((name, "clash", str(e)))

        # ── V2Ray 源: 链接 → URI ──
        if v2ray_url:
            all_urls.add(v2ray_url)
            try:
                raw = download_subscription_content(v2ray_url)
                for uri in decode_v2ray_links(raw).splitlines():
                    uri = uri.strip()
                    if uri and "://" in uri:
                        key = _normalize_uri_key(uri)
                        all_uris[key] = uri
            except Exception as e:
                failed.append((name, "v2ray", str(e)))

    unique_uris = list(all_uris.values())
    clash_count = sum(1 for u in unique_uris if not u.startswith("ss://"))
    ss_count     = sum(1 for u in unique_uris if u.startswith("ss://"))

    # ── 输出 1: merged_uris.txt (纯 URI 列表) ──
    with open(f"{outdir}/merged_uris.txt", "w") as f:
        f.write(f"# 跨源合并去重 URI ({len(unique_uris)} 个节点)\n")
        for uri in unique_uris:
            f.write(uri + "\n")

    # ── 输出 2: merged.yaml (Clash YAML) ──
    proxies_out = []
    for uri in unique_uris:
        node = uri_to_clash_node(uri)
        if node:
            proxies_out.append(node)

    # 生成 YAML (支持内联 {name: ..., ...} 格式)
    import yaml
    with open(f"{outdir}/merged.yaml", "w") as f:
        f.write("proxies:\n")
        for node in proxies_out:
            # 用 inline dict 格式: - {name: xxx, server: ..., port: ..., type: ...}
            compact = {"name": node.get("name", ""),
                       "type": node.get("type", ""),
                       "server": node.get("server", ""),
                       "port": node.get("port", 0)}
            # 添加类型特有字段
            if node.get("type") == "ss":
                compact["cipher"] = node.get("cipher", "aes-256-gcm")
                compact["password"] = node.get("password", "")
            elif node.get("type") == "trojan":
                compact["password"] = node.get("password", "")
            elif node.get("type") == "vmess":
                compact["uuid"] = node.get("uuid", "")
                compact["alterId"] = node.get("alterId", 0)
                compact["cipher"] = "auto"
            elif node.get("type") == "vless":
                compact["uuid"] = node.get("uuid", "")
            if node.get("network") in ("ws", "grpc"):
                compact["network"] = node["network"]
            if node.get("network") == "ws":
                compact["ws-opts"] = {
                    "path": node.get("ws-opts", {}).get("path", ""),
                    "headers": {"Host": node.get("ws-opts", {}).get("headers", {}).get("Host", "")}
                }
            if node.get("tls"):
                compact["tls"] = True
            if node.get("servername"):
                compact["servername"] = node["servername"]
            compact["udp"] = True
            f.write(f"  - {compact}\n")

    # ── 输出 3: latest.txt (订阅 URL 汇总) ──
    with open(f"{outdir}/latest.txt", "w") as f:
        f.write(f"# 跨源合并 ({len(all_urls)} 个订阅链接)\n")
        for url in sorted(all_urls):
            f.write(url + "\n")

    # ── 输出 4: latest_nodes.txt (URI + YAML 双重展示) ──
    with open(f"{outdir}/latest_nodes.txt", "w") as f:
        f.write(f"# ═══ URI 格式 ({len(unique_uris)} 个，去重后) ═══\n")
        for uri in unique_uris:
            f.write(uri + "\n")
        f.write("\n")
        f.write(f"# ═══ Clash YAML 格式 (merged.yaml 等效) ═══\n")
        with open(f"{outdir}/merged.yaml") as mf:
            f.write(mf.read())

    if failed:
        for name, src, err in failed:
            print(f"   ⚠️ [{name}] 合并失败 ({src}): {err}", file=sys.stderr)

    print(f"   📦 融合节点: {len(unique_uris)} | 订阅: {len(all_urls)}", file=sys.stderr)


def _normalize_uri_key(uri: str) -> str:
    """生成 URI 标准化 key 用于去重 (去掉 fragment 中的 name 部分)。"""
    if "://" not in uri:
        return uri
    scheme, rest = uri.split("://", 1)
    # 去掉 #name fragment
    if "#" in rest:
        rest = rest.rsplit("#", 1)[0]
    # ss:// 的 userinfo 里可能含 base64，截取前64字符足够区分
    if "@" in rest:
        body, serverpart = rest.rsplit("@", 1)
        body_short = body[:64]
        return f"{scheme}://{body_short}@{serverpart}"
    return f"{scheme}://{rest[:120]}"


def build_health_report():
    """生成 output/health.json: 各来源的状态、节点数、大小。"""
    from datetime import datetime, timezone

    report = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {},
        "summary": {"total": len(ALL_SOURCES), "ok": 0, "failed": 0},
    }

    for name, cfg in ALL_SOURCES.items():
        entry = {"status": "unknown", "nodes": 0, "size_kb": 0, "error": ""}
        urls = [u for u in [cfg.get("clash_url"), cfg.get("decode_v2ray_url")] if u]
        if not urls:
            entry["status"] = "no_url"
            entry["error"] = "无可用 URL"
            report["sources"][name] = entry
            report["summary"]["failed"] += 1
            continue

        # 尝试获取第一个可用 URL
        content = None
        for url in urls:
            try:
                raw = download_subscription_content(url)
                if not is_cloudflare_block(raw):
                    content = raw
                    break
            except Exception as e:
                entry["error"] = str(e)[:200]
                continue

        if content is None:
            entry["status"] = "failed"
            report["summary"]["failed"] += 1
            report["sources"][name] = entry
            continue

        # 统计节点数和大小
        text = content.decode("utf-8", "replace")
        entry["size_kb"] = round(len(content) / 1024, 1)
        if cfg.get("clash_url"):
            block = extract_clash_proxies(text)
            entry["nodes"] = len([l for l in block.splitlines()
                                  if l.strip().startswith("- name:") or l.strip().startswith("- {name:")])
        else:
            # v2ray 源: 统计解码后的链接数
            decoded = decode_v2ray_links(content)
            entry["nodes"] = len([l for l in decoded.splitlines() if "://" in l])

        entry["status"] = "ok"
        report["summary"]["ok"] += 1
        report["sources"][name] = entry

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(f"{OUTPUT_DIR}/health.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"   📈 健康: {report['summary']['ok']} OK / {report['summary']['failed']} 失败 "
          f"/ {report['summary']['total']} 总计", file=sys.stderr)


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

    # ── v2raynnodes_clash (完整 Clash 配置) ──
    print("📡 [v2raynnodes] 获取 v2raynnodes/v2rayfree (clash)...", file=sys.stderr)
    try:
        vn_subs = v2raynnodes_clash_fetch()
        if vn_subs:
            vn_latest = vn_subs[-1]
            vn_dir = write_source_output("v2raynnodes_clash", vn_latest, vn_subs, "v2raynnodes-clash (v2raynnodes/v2rayfree)")
            print(f"✅ [v2raynnodes] 完整 Clash 配置已保存")
            print(f"   clash: {vn_latest['urls']['clash']}")
            print(f"   → {vn_dir}/")
        else:
            print("⚠️ [v2raynnodes] 未获取到配置")
    except Exception as e:
        print(f"❌ [v2raynnodes] {e}", file=sys.stderr)

    print()

    # ── v2raynnodes_v2ray (完整 Clash 配置) ──
    print("📡 [v2raynnodes_v2ray] 获取 v2raynnodes/v2rayfree (clash)...", file=sys.stderr)
    try:
        vv_subs = v2raynnodes_v2ray_fetch()
        if vv_subs:
            vv_latest = vv_subs[-1]
            vv_dir = write_source_output("v2raynnodes_v2ray", vv_latest, vv_subs, "v2raynnodes-clash (v2raynnodes/v2rayfree)")
            print(f"✅ [v2raynnodes_v2ray] 完整 Clash 配置已保存")
            print(f"   clash: {vv_latest['urls']['clash']}")
            print(f"   → {vv_dir}/")
        else:
            print("⚠️ [v2raynnodes_v2ray] 未获取到节点")
    except Exception as e:
        print(f"❌ [v2raynnodes_v2ray] {e}", file=sys.stderr)

    print()

    print()
    print(f"💾 全部结果已写入 {OUTPUT_DIR}/")



    # ── ts-sf/fly (clash 完整配置) ──
    print("📡 [ts_sf_fly] 获取 ts-sf/fly...", file=sys.stderr)
    try:
        ts_subs = ts_sf_fly_fetch()
        if ts_subs:
            ts_latest = ts_subs[-1]
            ts_dir = write_source_output("ts_sf_fly", ts_latest, ts_subs, "ts-sf/fly")
            print(f"✅ [ts_sf_fly] 完整 Clash 配置已保存")
            print(f"   clash: {ts_latest['urls']['clash']}")
            print(f"   → {ts_dir}/")
        else:
            print("⚠️ [ts_sf_fly] 未获取到配置")
    except Exception as e:
        print(f"❌ [ts_sf_fly] {e}", file=sys.stderr)

    print()

    # ── free18/v2ray (clash 完整配置) ──
    print("📡 [free18] 获取 free18/v2ray...", file=sys.stderr)
    try:
        f18_subs = free18_fetch()
        if f18_subs:
            f18_latest = f18_subs[-1]
            f18_dir = write_source_output("free18", f18_latest, f18_subs, "free18/v2ray")
            print(f"✅ [free18] 完整 Clash 配置已保存")
            print(f"   clash: {f18_latest['urls']['clash']}")
            print(f"   → {f18_dir}/")
        else:
            print("⚠️ [free18] 未获取到配置")
    except Exception as e:
        print(f"❌ [free18] {e}", file=sys.stderr)

    print()

    # ── chengaopan/AutoMergePublicNodes (clash 完整配置) ──
    print("📡 [automerge] 获取 chengaopan/AutoMergePublicNodes...", file=sys.stderr)
    try:
        am_subs = automerge_fetch()
        if am_subs:
            am_latest = am_subs[-1]
            am_dir = write_source_output("automerge", am_latest, am_subs, "AutoMergePublicNodes")
            print(f"✅ [automerge] 完整 Clash 配置已保存")
            print(f"   clash: {am_latest['urls']['clash']}")
            print(f"   → {am_dir}/")
        else:
            print("⚠️ [automerge] 未获取到配置")
    except Exception as e:
        print(f"❌ [automerge] {e}", file=sys.stderr)

    print()

    # ── peasoft/NoMoreWalls (v2ray 链接) ──
    print("📡 [nomorewalls] 获取 peasoft/NoMoreWalls...", file=sys.stderr)
    try:
        nmw_subs = nomorewalls_fetch()
        if nmw_subs:
            nmw_latest = nmw_subs[-1]
            nmw_dir = write_source_output("nomorewalls", nmw_latest, nmw_subs, "NoMoreWalls")
            print(f"✅ [nomorewalls] v2ray 链接已保存")
            print(f"   v2ray: {nmw_latest['urls']['v2ray']}")
            print(f"   → {nmw_dir}/")
        else:
            print("⚠️ [nomorewalls] 未获取到链接")
    except Exception as e:
        print(f"❌ [nomorewalls] {e}", file=sys.stderr)

    print()

    # ── Pawdroid/Free-servers (v2ray 链接) ──
    print("📡 [pawdroid] 获取 Pawdroid/Free-servers...", file=sys.stderr)
    try:
        pd_subs = pawdroid_fetch()
        if pd_subs:
            pd_latest = pd_subs[-1]
            pd_dir = write_source_output("pawdroid", pd_latest, pd_subs, "Pawdroid/Free-servers")
            print(f"✅ [pawdroid] v2ray 链接已保存")
            print(f"   v2ray: {pd_latest['urls']['v2ray']}")
            print(f"   → {pd_dir}/")
        else:
            print("⚠️ [pawdroid] 未获取到链接")
    except Exception as e:
        print(f"❌ [pawdroid] {e}", file=sys.stderr)

    print()

    # ── Barabama/FreeNodes (多个子站, v2ray 链接) ──
    print("📡 [barabama] 获取 Barabama/FreeNodes (子站集合)...", file=sys.stderr)
    try:
        for b_sub in barabama_fetch():
            b_name = b_sub['extra'].split('→')[-1].strip()
            b_dir = write_source_output(f"barabama_{b_name}", b_sub, [b_sub], f"Barabama/{b_name}")
            print(f"✅ [barabama_{b_name}] v2ray 链接已保存 → {b_dir}/")
    except Exception as e:
        print(f"❌ [barabama] {e}", file=sys.stderr)

    print()

    # ── Flikify/Free-Node (clash 完整配置) ──
    print("📡 [flikify] 获取 Flikify/Free-Node...", file=sys.stderr)
    try:
        fl_subs = flikify_fetch()
        if fl_subs:
            fl_latest = fl_subs[-1]
            fl_dir = write_source_output("flikify", fl_latest, fl_subs, "Flikify/Free-Node")
            print(f"✅ [flikify] 完整 Clash 配置已保存")
            print(f"   clash: {fl_latest['urls']['clash']}")
            print(f"   → {fl_dir}/")
        else:
            print("⚠️ [flikify] 未获取到配置")
    except Exception as e:
        print(f"❌ [flikify] {e}", file=sys.stderr)

    print()

    # ── shaoyouvip/free (clash 完整配置) ──
    print("📡 [shaoyouvip] 获取 shaoyouvip/free...", file=sys.stderr)
    try:
        sy_subs = shaoyouvip_fetch()
        if sy_subs:
            sy_latest = sy_subs[-1]
            sy_dir = write_source_output("shaoyouvip", sy_latest, sy_subs, "shaoyouvip/free")
            print(f"✅ [shaoyouvip] 完整 Clash 配置已保存")
            print(f"   clash: {sy_latest['urls']['clash']}")
            print(f"   → {sy_dir}/")
        else:
            print("⚠️ [shaoyouvip] 未获取到配置")
    except Exception as e:
        print(f"❌ [shaoyouvip] {e}", file=sys.stderr)

    print()

    # ══════════════════════════════════════════════
    # 功能 1: 跨源合并 (all_nodes/) — 去重 + 统一配置
    # ══════════════════════════════════════════════
    print("🔀 [合并] 生成跨源去重合并输出...", file=sys.stderr)
    try:
        build_merged_output()
        print("✅ [合并] output/all_nodes/ 已生成")
    except Exception as e:
        print(f"❌ [合并] {e}", file=sys.stderr)

    print()

    # ══════════════════════════════════════════════
    # 功能 2: 健康度监控 (health.json)
    # ══════════════════════════════════════════════
    print("📊 [健康] 生成来源健康度报告...", file=sys.stderr)
    try:
        build_health_report()
        print("✅ [健康] output/health.json 已生成")
    except Exception as e:
        print(f"❌ [健康] {e}", file=sys.stderr)

    print()

# ── 来源 14: ts-sf/fly (Clash 格式, 每小时更新) ──
TS_SF_FLY_RAW = "https://raw.githubusercontent.com/ts-sf/fly/main/clash"

def ts_sf_fly_fetch():
    """来源 14: ts-sf/fly 的 clash — 完整 Clash 配置 (即取即用)。"""
    _register_source("ts_sf_fly", clash_url='https://raw.githubusercontent.com/ts-sf/fly/main/clash', label="来源 14 ts-sf/fly clash完整Clash配置")
    return [{
        "date": "latest",
        "sort_key": "99999992",
        "raw_clash": True,
        "clash_url": TS_SF_FLY_RAW,
        "urls": {"clash": TS_SF_FLY_RAW},
        "extra": "ts-sf/fly 完整 Clash 配置 (每小时更新)",
    }]


# ── 来源 15: free18/v2ray (Clash yaml 格式, 每日更新) ──
FREE18_RAW = "https://raw.githubusercontent.com/free18/v2ray/main/c.yaml"

def free18_fetch():
    """来源 15: free18/v2ray 的 c.yaml — 完整 Clash 配置 (即取即用)。"""
    _register_source("free18", clash_url='https://raw.githubusercontent.com/free18/v2ray/main/c.yaml', label="来源 15 free18/v2ray 每小时更新含VLESS Reality")
    return [{
        "date": "latest",
        "sort_key": "99999991",
        "raw_clash": True,
        "clash_url": FREE18_RAW,
        "urls": {"clash": FREE18_RAW},
        "extra": "free18/v2ray 完整 Clash 配置 (含 VLESS Reality)",
    }]


# ── 来源 16: chengaopan/AutoMergePublicNodes (Clash yaml, 协议多样) ──
AUTOMERGE_RAW = "https://raw.githubusercontent.com/chengaopan/AutoMergePublicNodes/master/list.meta.yml"

def automerge_fetch():
    """来源 16: chengaopan/AutoMergePublicNodes 的 list.meta.yml — 完整 Clash 配置。"""
    _register_source("automerge", clash_url='https://raw.githubusercontent.com/chengaopan/AutoMergePublicNodes/master/list.meta.yml', label="来源 16 chengaopan/AutoMergePublicNodes Hysteria2最全")
    return [{
        "date": "latest",
        "sort_key": "99999990",
        "raw_clash": True,
        "clash_url": AUTOMERGE_RAW,
        "urls": {"clash": AUTOMERGE_RAW},
        "extra": "AutoMergePublicNodes 完整 Clash 配置 (含 Hysteria2/VMess/Trojan)",
    }]


# ── 来源 17: peasoft/NoMoreWalls (base64 编码链接集合) ──
NOMOREWALLS_RAW = "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt"

def nomorewalls_fetch():
    """来源 17: peasoft/NoMoreWalls 的 list.txt — base64 编码的 ss/vmess/vless/trojan/hysteria2 链接。"""
    _register_source("nomorewalls", clash_url='https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt', label="来源 17 peasoft/NoMoreWalls 超大规模节点集合")
    return [{
        "date": "latest",
        "sort_key": "99999989",
        "clash_url": None,
        "urls": {"v2ray": NOMOREWALLS_RAW},
        "extra": "NoMoreWalls 超大规模节点集合",
    }]


# ── 来源 18: Pawdroid/Free-servers (base64 编码链接) ──
PAWDROID_RAW = "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub"

def pawdroid_fetch():
    """来源 18: Pawdroid/Free-servers 的 sub — base64 编码的 vless/trojan 链接。"""
    _register_source("pawdroid", clash_url='https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub', label="来源 18 Pawdroid/Free-servers 精炼高质节点")
    return [{
        "date": "latest",
        "sort_key": "99999988",
        "clash_url": None,
        "urls": {"v2ray": PAWDROID_RAW},
        "extra": "Pawdroid/Free-servers 精炼节点",
    }]


# ── 来源 19: Barabama/FreeNodes (聚合多站点的 base64 链接, 按子站拆分) ──
BARABAMA_BASE = "https://raw.githubusercontent.com/Barabama/FreeNodes/main/nodes"

BARABAMA_SUBS = [
    ("yudou66", "yudou66", "玉豆免费节点"),
    ("blues", "blues", "Blues 免费节点"),
    ("nodev2ray", "nodev2ray", "nodev2ray.com"),
    ("ndnode", "ndnode", "naidounode.com"),
    ("wenode", "wenode", "wenode.cc"),
    ("v2rayshare", "v2rayshare", "v2rayshare.com"),
    ("nodefree", "nodefree", "nodefree.org"),
]

def barabama_fetch():
    """来源 19: Barabama/FreeNodes 聚合的多个子站 — 每个子站 base64 链接。"""
    _register_source("barabama", clash_url=None, label="来源 19 Barabama/FreeNodes 7个子站集合")
    subs = []
    for idx, (name, sort_key_suffix, desc) in enumerate(BARABAMA_SUBS):
        url = f"{BARABAMA_BASE}/{name}.txt"
        subs.append({
            "date": "latest",
            "sort_key": f"9999998{idx}",
            "clash_url": None,
            "urls": {"v2ray": url},
            "extra": f"Barabama/FreeNodes → {desc}",
        })
    return subs


# ── 来源 20: Flikify/Free-Node (Clash yaml, 每小时更新, 质量波动) ──
FLIKIFY_GETNODE_RAW = "https://raw.githubusercontent.com/a2470982985/getNode/main/clash.yaml"

def flikify_fetch():
    """来源 20: Flikify/Free-Node 的 getNode/main/clash.yaml — 完整 Clash 配置。"""
    _register_source("flikify", clash_url=None, label="来源 20 Flikify/Free-Node 每小时更新")
    return [{
        "date": "latest",
        "sort_key": "99999979",
        "raw_clash": True,
        "clash_url": FLIKIFY_GETNODE_RAW,
        "urls": {"clash": FLIKIFY_GETNODE_RAW},
        "extra": "Flikify/Free-Node (a2470982985/getNode) 完整 Clash 配置",
    }]


# ── 来源 21: shaoyouvip/free (Clash yaml, 需验证) ──
SHAOYOUVIP_RAW = "https://raw.githubusercontent.com/shaoyouvip/free/refs/heads/main/all.yaml"

def shaoyouvip_fetch():
    """来源 21: shaoyouvip/free 的 all.yaml — 完整 Clash 配置 (即取即用)。"""
    _register_source("shaoyouvip", clash_url='https://raw.githubusercontent.com/shaoyouvip/free/refs/heads/main/all.yaml', label="来源 21 shaoyouvip/free 完整Clash配置")
    return [{
        "date": "latest",
        "sort_key": "99999978",
        "raw_clash": True,
        "clash_url": SHAOYOUVIP_RAW,
        "urls": {"clash": SHAOYOUVIP_RAW},
        "extra": "shaoyouvip/free 完整 Clash 配置",
    }]


if __name__ == "__main__":
    main()
