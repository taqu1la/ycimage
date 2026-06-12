# YCIMAGE 上线前最终检查与待办清单

检查日期：2026-06-12
检查范围：前端开发者、后端架构师、安全工程师、UX 研究员、DevOps/数据库视角的上线前审计，以及本地编译、语法检查、安全 smoke 验证。

## 结论摘要

YCIMAGE 当前核心代码已通过 Python 编译、前端 JS 语法检查和后端安全 smoke。主要 P0/P1 风险已在本轮修复中处理，包括生产配置校验、MPAY 回调加固、静态资源边界、SQLite 备份部署脚本、前端支付文案一致性、无障碍基础交互和管理端 token fallback 收敛。

上线前仍需由运维/站点负责人在真实生产环境完成配置验收：正式 HTTPS 域名、生产密钥、MPAY 正式参数、服务器环境文件、备份恢复演练、GitHub Actions 部署结果和真实支付回调联调。

## 已完成修复

- 后端生产安全配置：新增生产模式启动校验，要求强 `YCIMAGE_SECRET_KEY`、正式 `YCIMAGE_ADMIN_PASSWORD`、HTTPS origin 等。
- MPAY 回调安全：改为 POST-only，校验 `pid`，保留旧密钥兼容窗口，日志中对敏感签名参数脱敏。
- 管理端 token：公网默认禁用 `X-Admin-Token` 远程使用，除非显式设置 `YCIMAGE_ADMIN_TOKEN_REMOTE=true`。
- 请求体保护：超大请求在返回 413 前 drain body，降低连接复用异常。
- 积分幂等：`credit_ledger` 增加订单入账唯一约束，防止重复回调重复发放积分。
- 数据库初始化：生产环境和默认数据库 reset 增加保护，提供 `--force-reset` 显式开关。
- 部署脚本：新增 ECS GitHub Actions、Linux bootstrap、systemd、Nginx、生产 env 示例、SQLite online backup/restore。
- 静态资源边界：后端和 Nginx 示例阻断源码、脚本、数据库、锁文件、支付 SDK 目录和敏感配置。
- 前端迁移：将生产前端整理到 `webapp/`，后端优先从 `webapp` 提供页面。
- 前端支付文案：支付安全、退款、账户、首页购买入口统一为 MPAY/客服处理语义，去除 Stripe/银行卡/Webhook 旧承诺。
- 前端可访问性：补齐弹窗 role、focus trap、ESC 关闭、toast live region、tabs aria、移动菜单展开状态。
- API origin：前端改为同源优先，减少生产域名请求用户本机 `127.0.0.1` 的风险。
- 本地密钥：`.env.local` 中真实形态 MPAY key 已替换为占位符，仓库忽略 `.env*`。

## 已验证通过

- `python -m py_compile backend\server.py backend\scripts\init_db.py backend\scripts\sync_templates_to_db.py backend\scripts\sync_video_templates.py backend\scripts\security_smoke_tests.py`
- `python backend\scripts\security_smoke_tests.py`
- `node --check webapp\script.js`
- `node --check webapp\account.js`
- `node --check webapp\admin.js`
- `node --check webapp\templates.js`
- `git diff --cached --check`

## 上线前服务器验收清单

- [ ] GitHub Actions `Deploy YCImage To ECS` 执行成功，远端 `/opt/ycimage/current` 已同步最新提交。
- [ ] `/etc/ycimage/ycimage.env` 已设置 `YCIMAGE_ENV=production`。
- [ ] `YCIMAGE_SECRET_KEY` 为 32 位以上强随机值。
- [ ] `YCIMAGE_ADMIN_PASSWORD` 为强密码，未使用默认开发密码。
- [ ] `YCIMAGE_ALLOWED_ORIGINS` 仅包含正式 HTTPS 域名。
- [ ] `MPAY_PID`、`MPAY_KEY`、`MPAY_BASE_URL`、`MPAY_RETURN_URL`、`MPAY_NOTIFY_URL` 均为正式生产值。
- [ ] 已轮换曾出现在本机 `.env.local` 的 MPAY 密钥，并确认旧密钥不可用。
- [ ] Nginx 443、证书、HTTP 到 HTTPS 跳转、`X-Forwarded-Proto=https` 已验证。
- [ ] `nginx -t` 通过，`systemctl status ycimage nginx` 正常。
- [ ] `tools/linux/backup_ycimage.sh backup` 成功生成 SQLite online backup。
- [ ] 至少做过一次 restore 演练，确认备份可恢复。
- [ ] 真实浏览器 smoke 完成：注册/登录、模板选择、上传图、生成、支付、订单查看、作品查看、后台登录。
- [ ] MPAY 真实回调联调完成：错误签名拒绝、金额不符拒绝、pid 不符拒绝、正确回调入账、重复回调不重复入账。
- [ ] 生产站点抽测敏感静态路径均返回 404：`.gitignore`、`backend/schema.sql`、`backend/data/app.db`、`tools/*.ps1`、`assets/awesome-gpt-image-2/package-lock.json`、`assets/awesome-gpt-image-2/data/mpay_v2_webman-master/...`。

## 后续优化

- 将生成任务流程调整为先落库 `pending_submit/queued` 并冻结积分，再提交上游，失败时自动释放积分。
- 引入版本化数据库迁移和 schema drift 检查。
- 将进程内 rate limit 迁移到 Redis/Nginx/WAF 等共享限流层。
- 配置 CSP Report-Only，逐步收敛 `style-src 'unsafe-inline'` 和过宽的媒体来源。
- 后台入口增加 IP allowlist、VPN、Basic Auth 或独立管理域。
- 模板内容建立正式审核标准、风险标签和下架流程。
- 形成正式支付/退款/事故处理 runbook。

## 角色审计来源

- 前端开发者：重点检查 JS 语法、API origin、静态资源引用、支付文案、无障碍交互和移动端行为。
- 后端架构师：重点检查生产配置、任务可靠性、SQLite 迁移/备份、支付 provider 一致性和部署脚本。
- 安全工程师：重点检查密钥、HTTPS、MPAY 验签、CSRF、权限、敏感静态资源、日志脱敏和管理端 token。
- UX 研究员：重点检查购买路径可信度、退款说明一致性、套餐权益闭环、模板风险和错误反馈可理解性。
