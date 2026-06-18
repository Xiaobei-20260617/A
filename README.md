# 多源节点订阅抓取

自动从多个来源获取免费节点订阅链接，每日两更。

## 订阅来源

| 来源 | URL | 输出目录 |
|------|-----|----------|
| FProxies | [t.me/FProxies](https://t.me/FProxies) | `output/fproxies/` |
| datiya | [free.datiya.com](https://free.datiya.com/) | `output/datiya/` |
| osbooting | [freenode.osbooting.com](https://freenode.osbooting.com/) | `output/osbooting/` |
| mlfenx | [www.mlfenx.com](https://www.mlfenx.com/freenode) | `output/mlfenx/` |
| clashfree | [free-nodes/clashfree](https://github.com/free-nodes/clashfree) | `output/clashfree/` |

## 快速使用

每个来源独立的 `config.yaml`，直接导入 Clash Meta 即可：

- `output/fproxies/config.yaml`
- `output/datiya/config.yaml`
- `output/osbooting/config.yaml`
- `output/mlfenx/config.yaml`
- `output/clashfree/config.yaml`

## 输出结构

```
output/
├── fproxies/      ← Telegram @FProxies (clash/base64/quanx/urls)
├── datiya/        ← OpenRunner/clash-freenode (clash/v2ray)
├── osbooting/     ← freenode.osbooting.com (clash/v2ray)
├── mlfenx/        ← mlfenx.cczzuu.top (clash/v2ray)
└── clashfree/     ← GitHub free-nodes (clash)
```

## 自动更新

GitHub Actions 每天 UTC 01:00 / 13:00（北京时间 09:00 / 21:00）自动抓取。

## 免责声明

本项目仅抓取公开来源的订阅链接，不提供任何代理服务。请遵守当地法律法规。
