# FProxies 节点订阅

自动从多个来源获取免费节点订阅链接，每日两更。

## 订阅来源

| 来源 | 说明 | 输出目录 |
|------|------|----------|
| [FProxies](https://t.me/FProxies) | Telegram 频道 @FProxies | `output/fproxies/` |
| [datiya](https://free.datiya.com/) | OpenRunner/clash-freenode | `output/datiya/` |

## 快速使用

### Clash Meta 直接导入

每个来源都有独立的 `config.yaml`，直接导入即可：

- `output/fproxies/config.yaml` — FProxies 源
- `output/datiya/config.yaml` — datiya 源

### 手动添加订阅

复制 `latest_clash.txt` 或 `latest_base64.txt` 中的链接到代理软件。

## 输出结构

```
output/
├── fproxies/                 ← FProxies (Telegram)
│   ├── config.yaml           ← Clash Meta 配置
│   ├── latest.txt            ← 全部格式链接
│   ├── latest_clash.txt      ← Clash 订阅
│   ├── latest_base64.txt     ← Base64 订阅
│   ├── latest_quanx.txt      ← Quantumult X
│   ├── latest_urls.txt       ← URLs
│   └── subscriptions.json    ← 历史记录
└── datiya/                   ← datiya (OpenRunner)
    ├── config.yaml           ← Clash Meta 配置
    ├── latest.txt            ← 全部格式链接
    ├── latest_clash.txt      ← Clash 订阅
    ├── latest_v2ray.txt      ← V2Ray 订阅
    └── subscriptions.json    ← 历史记录
```

## 自动更新

GitHub Actions 每天 UTC 01:00 / 13:00（北京时间 09:00 / 21:00）自动抓取。

## 免责声明

本项目仅抓取公开来源的订阅链接，不提供任何代理服务。请遵守当地法律法规。
