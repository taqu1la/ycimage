# YCImage 后端数据库

这个目录包含上线用的本地后端、SQLite 数据库和同步工具。前台和后台不再在浏览器里加载 `local-db.js`，模板、参数、图片、用户、订单、积分、生成任务和审核记录都从后端 API 读取。

## 启动独立站点

```powershell
python backend\server.py --port 4178
```

访问地址：

- 前台：`http://127.0.0.1:4178/index.html`
- 全部模板：`http://127.0.0.1:4178/templates.html`
- 后台：`http://127.0.0.1:4178/admin.html`

## 本地数据库维护

```powershell
python backend\scripts\init_db.py --reset
python backend\scripts\verify_db.py
```

`init_db.py --reset` 只允许在本地开发或一次性重建测试库时使用。生产环境禁止执行 `--reset`，避免清空用户、订单、积分、任务和资产记录。

## 生产部署边界

生产环境只从受控环境文件读取配置，推荐路径为 `/etc/ycimage/ycimage.env`，权限设置为 `600`。至少确认：

- `YCIMAGE_ENV=production`
- `YCIMAGE_SECRET_KEY` 为 32 位以上随机强密钥
- `YCIMAGE_ADMIN_PASSWORD` 为强密码，不使用 `YCIMAGE_DEFAULT_ADMIN_PASSWORD`
- `YCIMAGE_ALLOWED_ORIGINS` 只包含正式 HTTPS 域名
- `MPAY_BASE_URL`、`MPAY_NOTIFY_URL`、`MPAY_RETURN_URL` 使用正式公网 HTTPS

`tools/linux/apply_release.sh` 不会默认复制仓库内的 `backend/data/app.db` 到生产库。首次生产部署会初始化 `YCIMAGE_DB_PATH`；如需导入正式种子库，显式设置 `YCIMAGE_SEED_DB_PATH=/path/to/approved-seed.db`。

Nginx 生产配置必须终止 TLS 或位于可信 TLS 网关之后，并传递 `X-Forwarded-Proto=https`。不要直接放行整个 `webapp/assets`；公开静态资源只能允许图片、视频、音频等媒体文件，源码、脚本、锁文件、数据库、证书、压缩包和支付 SDK 目录必须返回 404。

## 生产备份与恢复

SQLite 启用 WAL 时不能只复制主 `.db` 文件。使用 `tools/linux/backup_ycimage.sh` 通过 SQLite online backup 生成一致性快照：

```bash
YCIMAGE_ENV_FILE=/etc/ycimage/ycimage.env tools/linux/backup_ycimage.sh backup
```

恢复演练使用同一脚本，并在停服务或维护窗口执行：

```bash
systemctl stop ycimage
YCIMAGE_ENV_FILE=/etc/ycimage/ycimage.env tools/linux/backup_ycimage.sh restore /opt/ycimage/backups/db-YYYYmmdd-HHMMSS.tar.gz
systemctl start ycimage
python backend/scripts/verify_db.py --db /var/lib/ycimage/app.db
```

当前核心数据：

- 479 个模板，其中 473 个图片案例模板、6 个视频模板
- 716 个模板参数
- 22 套风格模板
- 578 条资产记录，包含 GitHub 图片和 APIMart 宣传视频/封面
- 6 个用户、5 个订单、122 条生成任务、31 条审核记录
- 首页模板数量配置：30

## 同步 GitHub 模板库

后台“同步 GitHub 模板库”按钮会执行：

```powershell
tools\sync-awesome-gpt-image-2.ps1
python backend\scripts\sync_templates_to_db.py
```

`sync_templates_to_db.py` 只更新 GitHub 模板、分类、风格模板和图片资产，不会清空用户、订单、积分、生成任务、审核记录或后台手动模板。

## 同步视频模板和宣传素材

后台“同步视频模板/宣传素材”按钮会执行：

```powershell
python backend\scripts\sync_video_templates.py
```

该脚本会维护 APIMart 视频模型路由、6 个视频模板，以及 `assets/apimart-video-promos` 下的宣传视频/封面资产。

## 关键 API

- `GET /api/settings/public`
- `GET /api/categories`
- `GET /api/templates?featured=1&page_size=30`
- `GET /api/templates/{id}`
- `GET /api/assets/{asset_id}`
- `POST /api/generate-image`
- `POST /api/generate-video`
- `GET /api/jobs/{id}`
- `GET /api/admin/state`
- `POST /api/admin/sync-github`
- `POST /api/admin/sync-video-templates`
- `POST /api/admin/templates`
- `PATCH /api/admin/templates/{id}`
- `DELETE /api/admin/templates/{id}`
