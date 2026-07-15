# fetch-nodes

Automatically fetch and aggregate free VPN/Proxy subscriptions from 13 public sources daily.

## 📦 Output Files

All outputs are generated in the `output/` directory:

- `latest.txt` — All subscription URLs
- `latest_{clash,base64,quanx,urls}.txt` — Formatted per source
- `config.yaml` — Clash Meta config with proxy-provider + rules (for non-raw sources)
- `latest_nodes.txt` — Raw node content snapshot (proxies block or decoded links)
- `subscriptions.json` — Deduplicated, sorted list of all subscriptions (persisted)

## 🌐 Sources (13 Total)

| ID | Source | Type | Notes |
|----|--------|------|-------|
| 1 | `fproxies` | Telegram @FProxies | Only source writing `proxies.txt` to root |
| 2 | `datiya` | free.datiya.com | Parses latest /post/YYYYMMDD/ pages |
| 3 | `osbooting` | freenode.osbooting.com | Scrapes last 3 /freenode/YYYYMMDD/ |
| 4 | `mlfenx` | mlfenx.cczzuu.top | Scrapes last 3 /archives/N |
| 5 | `clashfree` | GitHub free-nodes/clashfree | Fetches clashYYYYMMDD.yml |
| 6 | `bestclash` | PuddinCat/BestClash | Raw Clash config (no parsing) |
| 7 | `au1rxx` | Au1rxx/free-vpn-subscriptions | Raw Clash config |
| 8 | `v2rayfree` | GitHub free-nodes/v2rayfree | Base64 v2ray links only |
| 9 | `ruk1ng` | Ruk1ng001/freeSub | Raw Clash config |
| 10 | `ruk1ng_v2ray` | Ruk1ng001/freeSub | Base64 v2ray links |
| 11 | `ovmvo` | ovmvo/FreeSub | Raw Clash config |
| 12 | `v2raynnodes_clash` | v2raynnodes/v2rayfree | Raw Clash config |
| 13 | `v2raynnodes_v2ray` | v2raynnodes/v2rayfree | Raw Clash config |

## ⚙️ CI Automation

- Runs daily at **UTC 01:00 and 13:00** (Beijing: 09:00 & 21:00)
- Uses GitHub Actions: `.github/workflows/update.yml`
- Automatically: `pip install curl_cffi` → `python3 fetch_nodes.py` → `git add -A` → commit `output/`

## 📌 Notes

- `output/` is tracked in Git — do not ignore locally.
- `proxies.txt` is written only by `fproxies` and is a full concatenation of all URLs.
- `config.yaml` is generated only for sources that are **not** raw_clash.
- Use `subscriptions.json` to build your own persistent node list.

> 💡 Tip: Import `config.yaml` directly into Clash Meta for immediate use.
