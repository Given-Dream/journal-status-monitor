# 期刊稿件状态监控

这是一个用于自动监控期刊投稿状态的 Python 项目。它会登录投稿系统，读取稿件标题、稿件 ID、当前状态和投稿系统链接，并在状态变化时发送中文邮件通知。

项目现在同时支持两套触发方式：

- Cloudflare Worker 外部定时器：推荐使用，稳定调用 GitHub `workflow_dispatch`
- GitHub Actions 自带 `schedule`：保留为兜底方案

## 当前功能

- 支持 IEEE ScholarOne / Manuscript Central 投稿系统
- 支持 Elsevier Editorial Manager 基础登录和表格解析
- 自动识别 ScholarOne `STATUS` 栏中最上方的当前状态
- 能处理同一篇稿件被页面拆成多条状态历史的情况
- 能按规范化论文题目合并重复记录，避免旧状态重复出现在日报中
- 能识别并归档终态稿件，例如 `Accept`、`Accepted`、`Published`、`Rejected`、`Withdrawn`
- 中文 HTML 邮件通知，论文题目、稿件 ID、原始投稿状态保持英文原文
- 支持状态变化通知和每日状态报告
- 每日状态报告当天只发送一次，多次兜底触发不会重复发
- 状态数据保存到 `data/manuscripts.json`
- 日报发送记录保存到 `data/manuscripts.meta.json`
- 解析失败时可上传调试截图和 HTML

## 工作流程

1. 定时器触发 GitHub Actions。
2. GitHub Actions 运行 `monitor.py`。
3. 程序登录已配置的投稿系统。
4. 程序读取稿件信息并和历史记录比较。
5. 如果状态变化，发送中文状态变化通知。
6. 如果是每日状态报告时段，发送当天活跃稿件报告。
7. 如果稿件进入终态，自动归档，后续不再作为活跃稿件持续提醒。

## 当前触发时间

Cloudflare Worker 和 GitHub Actions schedule 使用相同的兜底时间窗口。Cloudflare Worker 是推荐触发源。

| 北京时间 | 模式 | 说明 |
| --- | --- | --- |
| 08:17、08:27、08:37 | `daily_report` | 每日报告兜底触发，当天只会发送一次 |
| 11:17、11:27、11:37 | `normal` | 状态变化才发邮件 |
| 12:17、12:27、12:37 | `normal` | 状态变化才发邮件 |
| 14:17、14:27、14:37 | `normal` | 状态变化才发邮件 |
| 17:17、17:27、17:37 | `normal` | 状态变化才发邮件 |
| 20:17、20:27、20:37 | `normal` | 状态变化才发邮件 |
| 22:17、22:27、22:37 | `normal` | 状态变化才发邮件 |

对应 UTC cron：

```yaml
- cron: '17,27,37 0 * * *'
- cron: '17,27,37 3 * * *'
- cron: '17,27,37 4 * * *'
- cron: '17,27,37 6 * * *'
- cron: '17,27,37 9 * * *'
- cron: '17,27,37 12 * * *'
- cron: '17,27,37 14 * * *'
```

GitHub Actions 的 `schedule` 可能延迟或丢触发，所以项目已增加 Cloudflare Worker 外部定时器。Cloudflare Worker 会调用 GitHub `workflow_dispatch`，GitHub Actions 页面中的事件来源会显示为 `workflow_dispatch`。

## GitHub Secrets

进入仓库：

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

至少配置一个投稿平台账号。

### IEEE ScholarOne

| Secret | 说明 |
| --- | --- |
| `IEEE_EMAIL` | IEEE ScholarOne 登录邮箱 |
| `IEEE_PASSWORD` | IEEE ScholarOne 登录密码 |
| `IEEE_URL` | 期刊对应的 ScholarOne 投稿系统地址 |

### Elsevier Editorial Manager

| Secret | 说明 |
| --- | --- |
| `ELSEVIER_EMAIL` | Elsevier / Editorial Manager 登录邮箱 |
| `ELSEVIER_PASSWORD` | Elsevier / Editorial Manager 登录密码 |
| `ELSEVIER_URL` | 期刊对应的 Editorial Manager 地址 |

### 邮件通知

| Secret | 说明 |
| --- | --- |
| `EMAIL_SENDER` | 发件邮箱 |
| `EMAIL_PASSWORD` | SMTP 授权码或应用专用密码 |
| `EMAIL_RECEIVER` | 收件邮箱，多个收件人用英文逗号分隔 |
| `SMTP_SERVER` 或 `SMTP_HOST` | 可选，SMTP 服务器地址 |
| `SMTP_PORT` | 可选，SMTP 端口，常见为 `465` 或 `587` |

常见邮箱会自动推断 SMTP 服务器，例如 QQ 邮箱、163 邮箱、Gmail、Outlook 等。

## Cloudflare 外部定时器

外部定时器代码位于：

`cloudflare-scheduler/`

已包含：

| 文件 | 说明 |
| --- | --- |
| `cloudflare-scheduler/worker.js` | Cloudflare Worker 代码 |
| `cloudflare-scheduler/wrangler.toml` | Worker 名称、变量和 cron 配置 |
| `cloudflare-scheduler/README.md` | Cloudflare 部署说明 |

Cloudflare Worker 需要一个 GitHub token，保存在 Cloudflare Secret：

```text
GITHUB_TOKEN
```

该 token 至少需要对本仓库具备：

- `Actions: Read and write`

如果要更新仓库文件，还需要 `Contents: Read and write`，但 Worker 触发 workflow 只需要 Actions 权限。

部署命令：

```bash
cd cloudflare-scheduler
wrangler secret put GITHUB_TOKEN
wrangler deploy
```

当前 Worker 名称：

```text
journal-status-monitor-scheduler
```

## 运行模式

| 模式 | 作用 |
| --- | --- |
| `test` | 只发送测试邮件，用于确认邮箱配置 |
| `normal` | 正常监控，只有状态变化时发邮件 |
| `daily_report` | 发送当前活跃稿件每日状态报告 |

手动运行：

1. 打开仓库的 `Actions` 页面。
2. 选择 `Journal Status Monitor`。
3. 点击 `Run workflow`。
4. 选择 `test`、`normal` 或 `daily_report`。

第一次配置完成后，建议先运行 `test`。

## 本地运行

安装依赖：

```bash
pip install -r requirements.txt
```

运行测试邮件：

```bash
python monitor.py --mode test
```

正常监控：

```bash
python monitor.py --mode normal
```

每日状态报告：

```bash
python monitor.py --mode daily_report
```

## 终态归档和日报防重复

默认情况下，稿件达到终态后会自动归档。归档稿件仍保存在 `data/manuscripts.json`，但不会继续出现在活跃稿件日报中。

每日状态报告发送成功后，会在 `data/manuscripts.meta.json` 记录当天已发送。当天后续兜底触发会跳过日报，避免重复发送。

相关环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `ARCHIVE_TERMINAL` | `true` | 是否自动归档终态稿件 |
| `INCLUDE_ARCHIVED_IN_REPORT` | `false` | 每日报告是否包含已归档稿件 |
| `TERMINAL_STATUS_KEYWORDS` | 内置列表 | 自定义终态关键词，英文逗号分隔 |

## 数据和隐私

`data/manuscripts.json` 可能包含论文题目、稿件 ID、投稿状态和投稿系统链接。真实投稿建议使用私有仓库。

不要把以下内容写进代码或 README：

- 投稿系统密码
- 邮箱授权码
- GitHub Personal Access Token
- Cloudflare API Token
- 任何个人隐私或稿件隐私信息

这些内容应放在 GitHub Secrets 或 Cloudflare Secrets 中。

## 常见问题

### 为什么 GitHub schedule 没按时运行？

GitHub Actions 的 `schedule` 不保证准点，可能延迟，也可能在高负载时丢触发。项目保留 GitHub schedule 作为兜底，同时使用 Cloudflare Worker 外部定时器触发 `workflow_dispatch`，可靠性更高。

### 为什么早上有三次 daily_report 触发但只收到一封？

这是正常行为。项目会记录当天日报已发送，后续兜底触发会跳过。

### 为什么稿件接收后不再出现在日报？

`Accept` 属于终态。程序会自动归档终态稿件，默认不再把它列入活跃稿件日报。

### 稿件状态识别不正确怎么办？

投稿系统页面结构可能变化。GitHub Actions 会上传 `monitor-debug` 调试文件，其中包含截图和 HTML，可用于排查。

## 项目文件说明

| 文件 | 说明 |
| --- | --- |
| `monitor.py` | 登录投稿系统、抓取和解析稿件状态 |
| `notification.py` | 生成并发送中文邮件 |
| `storage.py` | 保存状态、比较变化、归档和日报防重复 |
| `config.py` | 读取配置和环境变量 |
| `.github/workflows/monitor.yml` | GitHub Actions 工作流 |
| `cloudflare-scheduler/` | Cloudflare 外部定时器 |
| `.env.example` | 本地环境变量示例 |
| `DEPLOYMENT_GUIDE.md` | 早期部署说明 |

