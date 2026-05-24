# 期刊稿件状态监控

这是一个基于 Python 和 GitHub Actions 的期刊投稿状态自动监控工具。它会定时登录投稿系统，读取稿件当前状态，并在状态发生变化时发送中文邮件提醒。

目前主要支持：

- IEEE ScholarOne / Manuscript Central 投稿系统
- Elsevier Editorial Manager 投稿系统
- GitHub Actions 自动定时运行
- 手动运行测试邮件、正常监控、每日状态报告
- 中文邮件通知，保留论文题目、稿件 ID、原始状态文本
- 多收件人邮件通知
- 稿件状态持久化保存到 `data/manuscripts.json`
- 接收、发表、拒稿、撤稿等终态稿件自动归档，避免持续重复监控和提醒
- 解析失败时保存调试截图和 HTML，便于排查页面结构变化

## 工作方式

项目每次运行时会：

1. 根据配置登录投稿系统。
2. 读取稿件列表中的标题、稿件 ID、当前状态和投稿系统链接。
3. 与上一次保存在 `data/manuscripts.json` 中的状态进行比较。
4. 如果状态发生变化，发送中文状态更新邮件。
5. 如果稿件进入终态，例如 `Accept`、`Accepted`、`Published`、`Rejected` 或 `Withdrawn`，后续默认不再把它作为活跃稿件持续提醒。

对于 ScholarOne 状态栏中同时显示多条历史状态的情况，程序会识别最上面一条有效状态作为当前状态。下面的历史状态不会覆盖当前状态。

## GitHub Secrets 配置

进入仓库页面：

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

至少配置一个投稿平台账号。

### IEEE ScholarOne

| Secret | 说明 |
| --- | --- |
| `IEEE_EMAIL` | IEEE ScholarOne 登录邮箱 |
| `IEEE_PASSWORD` | IEEE ScholarOne 登录密码 |
| `IEEE_URL` | 期刊对应的 ScholarOne 投稿系统地址 |

如果不用 IEEE，可以不填这三项。

### Elsevier Editorial Manager

| Secret | 说明 |
| --- | --- |
| `ELSEVIER_EMAIL` | Elsevier / Editorial Manager 登录邮箱 |
| `ELSEVIER_PASSWORD` | Elsevier / Editorial Manager 登录密码 |
| `ELSEVIER_URL` | 期刊对应的 Editorial Manager 地址 |

如果不用 Elsevier，可以不填这三项。

### 邮件通知

| Secret | 说明 |
| --- | --- |
| `EMAIL_SENDER` | 发件邮箱 |
| `EMAIL_PASSWORD` | 邮箱 SMTP 授权码或应用专用密码，不是普通登录密码 |
| `EMAIL_RECEIVER` | 收件邮箱，多个收件人用英文逗号分隔 |
| `SMTP_SERVER` 或 `SMTP_HOST` | 可选，SMTP 服务器地址 |
| `SMTP_PORT` | 可选，SMTP 端口，常见为 `465` 或 `587` |

常见邮箱会自动推断 SMTP 服务器，例如 QQ 邮箱、163 邮箱、Gmail、Outlook 等。如果自动推断失败，再手动配置 `SMTP_SERVER` 和 `SMTP_PORT`。

## GitHub Actions 运行方式

工作流文件位于 `.github/workflows/monitor.yml`。

当前定时任务为每天运行三次：

- 北京时间 09:00：发送每日状态报告
- 北京时间 13:00：正常监控，仅状态变化时提醒
- 北京时间 22:00：正常监控，仅状态变化时提醒

也可以手动运行：

1. 打开仓库的 `Actions` 页面。
2. 选择 `Journal Status Monitor`。
3. 点击 `Run workflow`。
4. 选择运行模式。

可选运行模式：

| 模式 | 作用 |
| --- | --- |
| `test` | 只发送测试邮件，用于确认邮箱配置是否正确 |
| `normal` | 正常监控，只有状态变化时发送提醒 |
| `daily_report` | 发送当前活跃稿件的每日状态报告 |

第一次配置完成后，建议先手动运行 `test`，确认能收到邮件后再运行 `normal`。

## 本地运行

如果需要在本地调试，可以先安装依赖：

```bash
pip install -r requirements.txt
```

然后配置环境变量，或参考 `.env.example` 创建本地配置。

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

## 终态稿件归档

默认情况下，稿件达到终态后会自动归档。归档后的稿件仍保存在 `data/manuscripts.json`，但不会继续出现在正常监控提醒和每日报告中。

可通过环境变量调整：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `ARCHIVE_TERMINAL` | `true` | 是否自动归档终态稿件 |
| `INCLUDE_ARCHIVED_IN_REPORT` | `false` | 每日报告是否包含已归档稿件 |
| `TERMINAL_STATUS_KEYWORDS` | 内置列表 | 自定义终态关键词，多个关键词用英文逗号分隔 |

默认终态关键词包括接收、发表、拒稿、撤稿等状态。

## 数据和隐私

`data/manuscripts.json` 可能包含论文题目、稿件 ID、投稿状态和投稿系统链接。真实投稿项目建议使用私有仓库。

不要把以下内容直接写进代码或 README：

- 投稿系统密码
- 邮箱授权码
- GitHub Personal Access Token
- 任何包含个人隐私或稿件隐私的信息

这些内容都应放在 GitHub Secrets 中。

## 常见问题

### 收不到邮件

先手动运行 `test` 模式。确认以下配置是否正确：

- `EMAIL_SENDER`
- `EMAIL_PASSWORD`
- `EMAIL_RECEIVER`
- `SMTP_SERVER` / `SMTP_HOST`
- `SMTP_PORT`

很多邮箱需要单独开启 SMTP，并使用授权码或应用专用密码。

### 稿件状态识别不正确

投稿系统页面结构可能会变化。运行失败或解析异常时，GitHub Actions 会上传 `monitor-debug` 调试文件，其中包含截图和 HTML，可以用于判断页面结构是否改变。

### 稿件已经接收，但还在反复提醒

程序默认会在识别到终态后归档稿件。如果不希望终态稿件继续出现在报告中，保持：

```bash
ARCHIVE_TERMINAL=true
INCLUDE_ARCHIVED_IN_REPORT=false
```

### Actions 运行失败但本地正常

GitHub Actions 使用 Python 3.11 和 Ubuntu 环境。若修改代码后出现语法或编码问题，应优先按 Python 3.11 环境检查。

## 项目文件说明

| 文件 | 说明 |
| --- | --- |
| `monitor.py` | 登录投稿系统、抓取稿件列表和状态 |
| `notification.py` | 生成并发送中文邮件通知 |
| `storage.py` | 保存历史状态、比较状态变化、处理归档 |
| `config.py` | 读取环境变量和运行配置 |
| `.github/workflows/monitor.yml` | GitHub Actions 自动运行配置 |
| `.env.example` | 本地环境变量示例 |
| `DEPLOYMENT_GUIDE.md` | 更详细的部署说明 |

