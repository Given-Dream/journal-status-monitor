# Cloudflare 外部定时器

这个 Worker 用 Cloudflare Cron Triggers 调用 GitHub `workflow_dispatch`，用于替代或兜底 GitHub Actions 自带的 `schedule`。

## 触发时间

Cloudflare cron 使用 UTC 时间。本项目 Worker 会换算成北京时间，并只在以下时间触发 GitHub workflow：

| 北京时间 | 触发模式 |
| --- | --- |
| 08:17、08:27、08:37 | `daily_report` |
| 11:17、11:27、11:37 | `normal` |
| 12:17、12:27、12:37 | `normal` |
| 14:17、14:27、14:37 | `normal` |
| 17:17、17:27、17:37 | `normal` |
| 20:17、20:27、20:37 | `normal` |
| 22:17、22:27、22:37 | `normal` |

项目本身已经有“当天日报只发一次”的逻辑，所以早上三次兜底不会重复发送日报。

## GitHub Token 权限

建议新建一个专用 fine-grained GitHub token，只给这个仓库授权：

- Repository access: `Xuecheng377/journal-status-monitor`
- Permissions: `Actions: Read and write`
- 如果 GitHub 页面要求 Metadata 权限，保持默认只读即可

不要使用已经公开到聊天记录里的旧 token。

## 部署步骤

安装 Wrangler：

```bash
npm install -g wrangler
```

登录 Cloudflare：

```bash
wrangler login
```

进入本目录：

```bash
cd cloudflare-scheduler
```

设置 GitHub token 为 Cloudflare secret：

```bash
wrangler secret put GITHUB_TOKEN
```

部署：

```bash
wrangler deploy
```

部署后，Cloudflare 会按照 `wrangler.toml` 中的 cron 自动触发 Worker。

## 验证

部署完成后，可以打开 Worker 的访问地址。它会返回当前北京时间、如果此刻是定时窗口会触发的模式，以及目标仓库信息。

也可以在 Cloudflare Dashboard 的 Worker 日志里查看：

- `Triggered GitHub workflow_dispatch with mode=daily_report.`
- `Triggered GitHub workflow_dispatch with mode=normal.`

GitHub Actions 页面中，对应运行的 `event` 会显示为 `workflow_dispatch`。

