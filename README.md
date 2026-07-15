# fetch-nodes

Automatically fetch and aggregate free VPN/Proxy subscriptions from 21 public sources daily.

## 📦 Output Files

All outputs are generated in the `output/` directory:

- `latest.txt` — All subscription URLs
- `latest_{clash,v2ray}.txt` — Formatted per source
- `config.yaml` — Clash Meta config with proxy-provider + rules (for non-raw sources)
- `latest_nodes.txt` — Raw node content snapshot (proxies block or decoded links)
- `subscriptions.json` — Deduplicated, sorted list of all subscriptions (persisted)

## 🌐 Sources (21 Total)

### 🏆 Tier 1 — High Quality, Stable

| ID | Source | Type | Notes |
|----|--------|------|-------|
| 1 | `fproxies` | Telegram @FProxies | Only source writing `proxies.txt` to root |
| 6 | `bestclash` | PuddinCat/BestClash | Updates every 30 min |
| 7 | `au1rxx` | Au1rxx/free-vpn-subscriptions | Updates hourly, ~150 nodes |
| 11 | `ovmvo` | ovmvo/FreeSub | Raw mihomo config |
| 12 | `v2raynnodes_clash` | v2raynnodes/v2rayfree | Raw clashmeta config |
| 13 | `v2raynnodes_v2ray` | v2raynnodes/v2rayfree | Raw mihomo config |
| 14 | `ts_sf_fly` | ts-sf/fly | Updates hourly, speed-tagged nodes |
| 15 | `free18` | free18/v2ray | 440+ nodes, VLESS Reality heavy |
| 16 | `automerge` | chengaopan/AutoMergePublicNodes | Hysteria2/VMess/Trojan/SSR diversity |

### 🥈 Tier 2 — Good Quality

| ID | Source | Type | Notes |
|----|--------|------|-------|
| 2 | `datiya` | free.datiya.com | Daily updates |
| 3 | `osbooting` | freenode.osbooting.com | Last 3 daily posts |
| 4 | `mlfenx` | mlfenx.cczzuu.top | Last 3 articles |
| 5 | `clashfree` | free-nodes/clashfree | Dated clash files |
| 9 | `ruk1ng` | Ruk1ng001/freeSub | Raw clash config |
| 17 | `nomorewalls` | peasoft/NoMoreWalls | ~1000+ nodes, very large |
| 18 | `pawdroid` | Pawdroid/Free-servers | Curated, high quality |

### 🥉 Tier 3 — Aggregated / Experimental

| ID | Source | Type | Notes |
|----|--------|------|-------|
| 8 | `v2rayfree` | free-nodes/v2rayfree | Base64 v2ray links |
| 10 | `ruk1ng_v2ray` | Ruk1ng001/freeSub | Base64 v2ray links |
| 19 | `barabama_*` | Barabama/FreeNodes | 7 sub-sources (yudou66/blues/nodev2ray/ndnode/wenode/v2rayshare/nodefree) |
| 20 | `flikify` | Flikify/Free-Node | Hourly updates, quality varies |
| 21 | `shaoyouvip` | shaoyouvip/free | Needs validation |

## ⚙️ CI Automation

- Runs daily at **UTC 01:00 and 13:00** (Beijing: 09:00 & 21:00)
- Uses GitHub Actions: `.github/workflows/update.yml`
- Automatically: `pip install curl_cffi` → `python3 fetch_nodes.py` → `git add -A` → commit `output/`

## 📌 Notes

- `output/` is tracked in Git — do not ignore locally.
- `proxies.txt` is written only by `fproxies` and is a full concatenation of all URLs.
- `config.yaml` is generated only for sources that are **not** raw_clash.
- Barabama sources are split into 7 independent sub-sources (one per scraped site).

> 💡 Tip: Import `config.yaml` directly into Clash Meta for immediate use.
