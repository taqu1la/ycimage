from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


APIMART_BASE_URL = "https://api.apimart.ai"
APIMART_OFFICIAL_ROUTE_CODE = "gpt-image-2-official"
APIMART_OFFICIAL_MODEL = "gpt-image-2-official"
DEFAULT_IMAGE_ROUTE_CODE = "gpt-image-2-high"
APIMART_OFFICIAL_SIZES = ["auto", "1:1", "3:4", "4:3", "4:5", "5:4", "2:3", "3:2", "16:9", "9:16", "2:1", "1:2", "21:9", "9:21"]


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DB_PATH = BACKEND / "data" / "app.db"
SCHEMA_PATH = BACKEND / "schema.sql"
WEBAPP_ROOT = ROOT / "webapp"
LOCAL_DB_PATH = WEBAPP_ROOT / "assets" / "awesome-gpt-image-2" / "local-db.js"


CATEGORY_LABELS = {
    "Architecture & Spaces": ("建筑与空间", "architecture-spaces"),
    "Brand & Logos": ("品牌与标志", "brand-logos"),
    "Characters & People": ("人物与角色", "characters-people"),
    "Charts & Infographics": ("图表与信息图", "charts-infographics"),
    "Documents & Publishing": ("文档与出版", "documents-publishing"),
    "History & Classical Themes": ("历史与古典主题", "history-classical"),
    "Illustration & Art": ("插画与艺术", "illustration-art"),
    "Other Use Cases": ("其他应用场景", "other-use-cases"),
    "Photography & Realism": ("摄影与写实", "photography-realism"),
    "Posters & Typography": ("海报与字体", "posters-typography"),
    "Products & E-commerce": ("产品与电商", "products-ecommerce"),
    "Scenes & Storytelling": ("场景与叙事", "scenes-storytelling"),
    "UI & Interfaces": ("UI 与界面", "ui-interfaces"),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def iso_minutes_ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or uuid.uuid4().hex[:8]


def json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def load_local_db() -> dict:
    text = LOCAL_DB_PATH.read_text(encoding="utf-8")
    prefix = "window.AWESOME_GPT_IMAGE_2_DB = "
    if not text.startswith(prefix):
        raise RuntimeError(f"Unexpected local-db.js format: {LOCAL_DB_PATH}")
    payload = text[len(prefix):].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)


def is_production_env() -> bool:
    return os.environ.get("YCIMAGE_ENV", os.environ.get("APP_ENV", "development")).strip().lower() in {"prod", "production"}


def assert_reset_allowed(db_path: Path, reset: bool, force_reset: bool) -> None:
    if not reset or not db_path.exists():
        return
    if is_production_env() and not force_reset:
        raise RuntimeError("Refusing to reset an existing database in production; set --force-reset only after taking a backup.")
    if not force_reset and db_path.resolve() == DB_PATH.resolve():
        raise RuntimeError("Refusing to reset the default app database without --force-reset. Back up backend/data/app.db first.")


def connect(db_path: Path, reset: bool, force_reset: bool = False) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    assert_reset_allowed(db_path, reset, force_reset)
    if reset and db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
        (1, "initial_complex_schema"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
        (2, "credit_ledger_order_idempotency"),
    )


def insert_app_settings(conn: sqlite3.Connection) -> None:
    settings = [
        ("site.name", "YCImage", "string", "前台站点名称"),
        ("site.home_template_limit", "30", "number", "首页热门模板数量"),
        ("site.public_template_library", "true", "boolean", "是否开放公开模板库"),
        ("site.require_review_before_download", "false", "boolean", "下载前是否必须审核"),
        ("generation.default_quality", "medium", "string", "默认图片质量"),
        ("generation.default_model_route", DEFAULT_IMAGE_ROUTE_CODE, "string", "默认模型路由"),
        ("billing.currency", "CNY", "string", "默认结算币种"),
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO app_settings(key, value, value_type, description, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(key, value, value_type, desc, now()) for key, value, value_type, desc in settings],
    )


def insert_roles_orgs_users(conn: sqlite3.Connection) -> dict[str, str]:
    roles = [
        ("role_owner", "owner", "系统所有者", ["*"]),
        (
            "role_admin",
            "admin",
            "运营管理员",
            [
                "admin:*",
                "templates:*",
                "templates:sync",
                "users:*",
                "orders:read",
                "jobs:*",
                "models:*",
                "credits:grant",
                "reviews:write",
                "settings:write",
                "payments:config",
            ],
        ),
        ("role_user", "user", "普通用户", ["generate:create", "assets:read"]),
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO roles(id, name, description, permissions_json) VALUES (?, ?, ?, ?)",
        [(rid, name, desc, json_dumps(perms)) for rid, name, desc, perms in roles],
    )

    orgs = [
        ("org_default", "YCImage", "ycimage", "enterprise", "ops@example.com", "active"),
        ("org_nanxiang", "南巷咖啡", "nanxiang-cafe", "studio", "owner@nanxiang.example", "active"),
        ("org_xingye", "星野设计", "xingye-design", "creator", "studio@xingye.example", "active"),
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO organizations(id, name, slug, plan_code, billing_email, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [(oid, name, slug, plan, email, status, now(), now()) for oid, name, slug, plan, email, status in orgs],
    )

    users = [
        ("user_admin", "org_default", "运营管理员", "18800000000", "admin@example.com", "wx_admin", "role_admin", "enterprise", "active", 8),
        ("user_lijie", "org_default", "李姐服装店", "18800000001", "lijie@example.com", "wx_lijie", "role_user", "monthly", "active", 18),
        ("user_xingye", "org_xingye", "星野设计", "18800000002", "xingye@example.com", "wx_xingye", "role_user", "creator", "active", 32),
        ("user_zhou", "org_default", "小周微商", "18800000003", "zhou@example.com", "wx_zhou", "role_user", "free", "active", 66),
        ("user_cafe", "org_nanxiang", "南巷咖啡", "18800000004", "cafe@example.com", "wx_cafe", "role_user", "studio", "active", 5),
        ("user_orange", "org_default", "橙子童装", "18800000005", "orange@example.com", "wx_orange", "role_user", "credit_pack", "active", 120),
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO users(
            id, organization_id, display_name, mobile, email, wechat_openid, role_id,
            membership_level, status, locale, last_login_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'zh-CN', ?, ?, ?)
        """,
        [
            (uid_, org, name, mobile, email, openid, role, level, status, iso_minutes_ago(minutes), now(), now())
            for uid_, org, name, mobile, email, openid, role, level, status, minutes in users
        ],
    )

    profiles = [
        ("user_lijie", "李姐服装店", "服装零售", "杭州", "小红书穿搭图"),
        ("user_xingye", "星野设计", "设计服务", "上海", "商业海报与提案图"),
        ("user_zhou", "小周微商", "私域电商", "广州", "朋友圈产品图"),
        ("user_cafe", "南巷咖啡", "本地生活", "成都", "门店活动海报"),
        ("user_orange", "橙子童装", "童装零售", "温州", "童装上新图"),
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO user_profiles(user_id, company_name, industry, city, use_case, designer_level, preferences_json)
        VALUES (?, ?, ?, ?, ?, 'non_designer', '{}')
        """,
        profiles,
    )

    balances = {
        "user_admin": 99999,
        "user_lijie": 186,
        "user_xingye": 942,
        "user_zhou": 9,
        "user_cafe": 4210,
        "user_orange": 68,
    }
    for user_id, balance in balances.items():
        account_id = f"ca_{user_id}"
        conn.execute(
            """
            INSERT OR REPLACE INTO credit_accounts(
                id, user_id, balance, frozen_balance, lifetime_purchased, lifetime_granted, lifetime_spent, updated_at
            )
            VALUES (?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (account_id, user_id, balance, max(0, balance - 100), 100, random.randint(20, 600), now()),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO credit_ledger(
                id, account_id, user_id, direction, amount, balance_after, reason,
                reference_type, reference_id, operator_user_id, metadata_json, created_at
            )
            VALUES (?, ?, ?, 'credit', ?, ?, 'initial_seed', 'system', 'seed', 'user_admin', '{}', ?)
            """,
            (uid("ledger"), account_id, user_id, balance, balance, now()),
        )
    return {row[0]: row[0] for row in users}


def insert_pricing_orders(conn: sqlite3.Connection) -> None:
    plans = [
        ("plan_free", "free", "免费体验", "free", 0, 20, None, ["每日少量体验", "基础模板"]),
        ("plan_monthly", "monthly", "月卡", "subscription", 2900, 300, 30, ["高清生成", "商用模板"]),
        ("plan_creator", "creator", "创作者版", "subscription", 19900, 1500, 30, ["批量生成", "优先队列"]),
        ("plan_studio", "studio", "工作室版", "subscription", 49900, 6000, 30, ["多人协作", "更高并发"]),
        ("plan_pack_200", "pack_200", "200 积分包", "credit_pack", 2900, 200, None, ["一次性积分"]),
        ("plan_pack_600", "pack_600", "600 积分包", "credit_pack", 7900, 600, None, ["一次性积分", "更适合连续出图"]),
        ("plan_pack_1500", "pack_1500", "1500 积分包", "credit_pack", 19900, 1500, None, ["大额积分"]),
        ("plan_pack_6000", "pack_6000", "6000 积分包", "credit_pack", 59900, 6000, None, ["团队批量生成"]),
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO pricing_plans(
            id, code, name, plan_type, price_cents, currency, credits, period_days, features_json, status, sort_order
        )
        VALUES (?, ?, ?, ?, ?, 'CNY', ?, ?, ?, 'active', ?)
        """,
        [(pid, code, name, typ, price, credits, days, json_dumps(features), i) for i, (pid, code, name, typ, price, credits, days, features) in enumerate(plans)],
    )

    orders = [
        ("order_9201", "ORD-9201", "user_cafe", "org_nanxiang", "plan_studio", 49900, "wechat", "paid", 44),
        ("order_9200", "ORD-9200", "user_xingye", "org_xingye", "plan_creator", 19900, "alipay", "paid", 92),
        ("order_9198", "ORD-9198", "user_zhou", "org_default", "plan_pack_200", 2900, "service", "pending", 1220),
        ("order_9192", "ORD-9192", "user_lijie", "org_default", "plan_monthly", 2900, "wechat", "paid", 1680),
        ("order_9188", "ORD-9188", "user_orange", "org_default", "plan_pack_1500", 19900, "wechat", "paid", 2440),
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO orders(
            id, order_no, user_id, organization_id, plan_id, amount_cents, currency,
            payment_channel, payment_provider_order_id, status, paid_at, notes, metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'CNY', ?, ?, ?, ?, '', '{}', ?, ?)
        """,
        [
            (
                oid, no, user, org, plan, amount, channel, f"pay_{no.lower()}",
                status, None if status != "paid" else iso_minutes_ago(minutes),
                iso_minutes_ago(minutes), now()
            )
            for oid, no, user, org, plan, amount, channel, status, minutes in orders
        ],
    )


def insert_template_taxonomy(conn: sqlite3.Connection, db: dict) -> dict[str, str]:
    source_id = "src_awesome_gpt_image_2"
    conn.execute(
        """
        INSERT INTO template_sources(id, name, source_type, repository_url, license, synced_at, metadata_json)
        VALUES (?, ?, 'repo', ?, 'MIT', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            source_type = excluded.source_type,
            repository_url = excluded.repository_url,
            license = excluded.license,
            synced_at = excluded.synced_at,
            metadata_json = excluded.metadata_json
        """,
        (
            source_id,
            "freestylefly/awesome-gpt-image-2",
            db.get("repository"),
            now(),
            json_dumps({
                "updatedFrom": db.get("updatedFrom"),
                "totalCases": db.get("totalCases"),
                "imageFiles": db.get("imageFiles"),
            }),
        ),
    )

    category_ids: dict[str, str] = {}
    for index, source_value in enumerate(db.get("categories", [])):
        zh, slug = CATEGORY_LABELS.get(source_value, (source_value, slugify(source_value)))
        category_id = f"cat_{slug.replace('-', '_')}"
        category_ids[source_value] = category_id
        conn.execute(
            """
            INSERT INTO template_categories(
                id, source_value, name_zh, name_en, slug, description, sort_order, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET
                source_value = excluded.source_value,
                name_zh = excluded.name_zh,
                name_en = excluded.name_en,
                slug = excluded.slug,
                description = excluded.description,
                sort_order = excluded.sort_order,
                is_active = excluded.is_active
            """,
            (category_id, source_value, zh, source_value, slug, f"{zh}相关模板", index),
        )
    return category_ids


def insert_model_routes(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO model_providers(
            id, name, provider_type, base_url, status, server_key_status, health_status, last_checked_at, metadata_json
        )
        VALUES ('provider_openai_compatible', 'OpenAI Compatible Gateway', 'openai-compatible',
                '/api', 'active', 'not_configured', 'unknown', ?, '{}')
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            provider_type = excluded.provider_type,
            base_url = excluded.base_url,
            status = excluded.status,
            server_key_status = excluded.server_key_status,
            health_status = excluded.health_status,
            last_checked_at = excluded.last_checked_at,
            metadata_json = excluded.metadata_json
        """,
        (now(),),
    )
    existing_apimart = conn.execute("SELECT metadata_json FROM model_providers WHERE id = 'provider_apimart'").fetchone()
    try:
        apimart_metadata = json.loads(existing_apimart["metadata_json"] or "{}") if existing_apimart else {}
    except (TypeError, json.JSONDecodeError):
        apimart_metadata = {}
    apimart_metadata.update({
        "imageEndpoint": "/v1/images/generations",
        "videoEndpoint": "/v1/videos/generations",
        "taskEndpoint": "/v1/tasks/{task_id}",
        "imageUploadEndpoint": "/v1/uploads/images",
        "officialImageModel": APIMART_OFFICIAL_MODEL,
        "docsUrl": "https://docs.apimart.ai/cn/api-reference/images/gpt-image-2/official",
        "auth": "Authorization: Bearer APIMART_API_KEY",
    })
    conn.execute(
        """
        INSERT INTO model_providers(
            id, name, provider_type, base_url, status, server_key_status, health_status, last_checked_at, metadata_json
        )
        VALUES ('provider_apimart', 'APIMart', 'apimart', ?, 'active', 'env_required', 'unknown', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            provider_type = excluded.provider_type,
            base_url = excluded.base_url,
            status = excluded.status,
            server_key_status = model_providers.server_key_status,
            health_status = model_providers.health_status,
            last_checked_at = COALESCE(model_providers.last_checked_at, excluded.last_checked_at),
            metadata_json = excluded.metadata_json
        """,
        (
            APIMART_BASE_URL,
            now(),
            json_dumps(apimart_metadata),
        ),
    )
    routes = [
        {
            "id": "route_gpt_image_2_official",
            "provider": "provider_apimart",
            "code": APIMART_OFFICIAL_ROUTE_CODE,
            "display": "GPT Image 2 Official",
            "model": APIMART_OFFICIAL_MODEL,
            "modality": "image",
            "quality": "high",
            "cost": 15,
            "priority": 70,
            "success": 97.8,
            "latency": 18600,
            "sizes": APIMART_OFFICIAL_SIZES,
            "ratios": APIMART_OFFICIAL_SIZES,
            "default_size": "1:1",
            "default_ratio": "1:1",
            "timeout": 120,
            "metadata": {
                "source": "apimart_docs",
                "docsUrl": "https://docs.apimart.ai/cn/api-reference/images/gpt-image-2/official",
            },
        },
        {
            "id": "route_gpt_image_2_high",
            "provider": "provider_openai_compatible",
            "code": "gpt-image-2-high",
            "display": "GPT-Image2 高清",
            "model": "gpt-image-2",
            "modality": "image",
            "quality": "high",
            "cost": 8,
            "priority": 100,
            "success": 97.8,
            "latency": 18600,
            "sizes": ["1024x1024", "1024x1536", "1536x1024", "1536x1536"],
            "ratios": ["1:1", "3:4", "4:3", "9:16", "16:9"],
            "default_size": "1024x1024",
            "default_ratio": "1:1",
            "timeout": 90,
        },
        {
            "id": "route_gpt_image_2_fast",
            "provider": "provider_openai_compatible",
            "code": "gpt-image-2-fast",
            "display": "GPT-Image2 快速",
            "model": "gpt-image-2",
            "modality": "image",
            "quality": "standard",
            "cost": 5,
            "priority": 90,
            "success": 96.4,
            "latency": 9800,
            "sizes": ["1024x1024", "1024x1536", "1536x1024", "1536x1536"],
            "ratios": ["1:1", "3:4", "4:3", "9:16", "16:9"],
            "default_size": "1024x1024",
            "default_ratio": "1:1",
            "timeout": 90,
        },
        {
            "id": "route_gpt_image_2_ultra",
            "provider": "provider_openai_compatible",
            "code": "gpt-image-2-ultra",
            "display": "GPT-Image2 超清",
            "model": "gpt-image-2",
            "modality": "image",
            "quality": "ultra",
            "cost": 13,
            "priority": 80,
            "success": 94.2,
            "latency": 31400,
            "sizes": ["1024x1024", "1024x1536", "1536x1024", "1536x1536"],
            "ratios": ["1:1", "3:4", "4:3", "9:16", "16:9"],
            "default_size": "1024x1024",
            "default_ratio": "1:1",
            "timeout": 90,
        },
        {
            "id": "route_wan26_i2v_flash",
            "provider": "provider_apimart",
            "code": "wan2.6-i2v-flash",
            "display": "Wan2.6 图生视频快速",
            "model": "wan2.6-i2v-flash",
            "modality": "video",
            "quality": "720p",
            "cost": 18,
            "priority": 130,
            "success": 92.8,
            "latency": 185000,
            "sizes": ["720p", "1080p"],
            "ratios": ["16:9", "9:16", "1:1"],
            "default_size": "720p",
            "default_ratio": "16:9",
            "timeout": 600,
        },
        {
            "id": "route_sora_2",
            "provider": "provider_apimart",
            "code": "sora-2",
            "display": "Sora 2 视频",
            "model": "sora-2",
            "modality": "video",
            "quality": "720p",
            "cost": 35,
            "priority": 120,
            "success": 91.4,
            "latency": 260000,
            "sizes": ["720p", "1080p"],
            "ratios": ["16:9", "9:16", "1:1"],
            "default_size": "720p",
            "default_ratio": "16:9",
            "timeout": 600,
        },
        {
            "id": "route_grok_imagine_video",
            "provider": "provider_apimart",
            "code": "grok-imagine-1.0-video-apimart",
            "display": "Grok Imagine 视频",
            "model": "grok-imagine-1.0-video-apimart",
            "modality": "video",
            "quality": "720p",
            "cost": 20,
            "priority": 110,
            "success": 90.6,
            "latency": 210000,
            "sizes": ["720p"],
            "ratios": ["16:9", "9:16", "1:1"],
            "default_size": "720p",
            "default_ratio": "16:9",
            "timeout": 600,
        },
    ]
    for route in routes:
        conn.execute(
            """
            INSERT INTO model_routes(
                id, provider_id, route_code, display_name, model_name, modality, quality,
                supported_sizes_json, supported_ratios_json, default_size, default_ratio,
                credit_cost, priority, timeout_seconds, retry_limit, success_rate, avg_latency_ms, status, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, 2, ?, ?, 'active', ?)
            ON CONFLICT(id) DO UPDATE SET
                provider_id = excluded.provider_id,
                route_code = excluded.route_code,
                display_name = excluded.display_name,
                model_name = excluded.model_name,
                modality = excluded.modality,
                quality = excluded.quality,
                supported_sizes_json = excluded.supported_sizes_json,
                supported_ratios_json = excluded.supported_ratios_json,
                default_size = excluded.default_size,
                default_ratio = excluded.default_ratio,
                credit_cost = excluded.credit_cost,
                priority = excluded.priority,
                timeout_seconds = excluded.timeout_seconds,
                retry_limit = excluded.retry_limit,
                success_rate = excluded.success_rate,
                avg_latency_ms = excluded.avg_latency_ms,
                status = excluded.status,
                metadata_json = excluded.metadata_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                route["id"],
                route["provider"],
                route["code"],
                route["display"],
                route["model"],
                route["modality"],
                route["quality"],
                json_dumps(route["sizes"]),
                json_dumps(route["ratios"]),
                route["default_size"],
                route["default_ratio"],
                route["cost"],
                route["priority"],
                route["timeout"],
                route["success"],
                route["latency"],
                json_dumps({**{"source": "seed", "provider": route["provider"]}, **route.get("metadata", {})}),
            ),
        )


def insert_asset(conn: sqlite3.Connection, asset_id: str, asset_type: str, path: str, owner: str | None = None, org: str | None = None) -> None:
    suffix = Path(path).suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
    }.get(suffix, "application/octet-stream")
    normalized = str(path).replace("\\", "/").lstrip("/")
    candidates = [ROOT / normalized]
    if normalized.startswith("assets/"):
        candidates.append(WEBAPP_ROOT / normalized)
    full_path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    byte_size = full_path.stat().st_size if full_path.exists() else None
    checksum = None
    content = None
    if full_path.exists() and byte_size and byte_size < 10_000_000:
        content = full_path.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
    conn.execute(
        """
        INSERT INTO assets(
            id, owner_user_id, organization_id, asset_type, storage_provider, storage_path,
            public_url, mime_type, byte_size, checksum, status, moderation_status, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, 'local', ?, ?, ?, ?, ?, 'active', 'approved', '{}', ?)
        ON CONFLICT(id) DO UPDATE SET
            owner_user_id = excluded.owner_user_id,
            organization_id = excluded.organization_id,
            asset_type = excluded.asset_type,
            storage_provider = excluded.storage_provider,
            storage_path = excluded.storage_path,
            public_url = excluded.public_url,
            mime_type = excluded.mime_type,
            byte_size = excluded.byte_size,
            checksum = excluded.checksum,
            status = excluded.status,
            moderation_status = excluded.moderation_status,
            metadata_json = excluded.metadata_json
        """,
        (asset_id, owner, org, asset_type, normalized, normalized, mime, byte_size, checksum, now()),
    )
    if content is not None:
        conn.execute(
            """
            INSERT OR REPLACE INTO asset_blobs(asset_id, content, byte_size, sha256, embedded_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (asset_id, sqlite3.Binary(content), byte_size, checksum, now()),
        )


def insert_templates(conn: sqlite3.Connection, db: dict, category_ids: dict[str, str]) -> list[str]:
    source_id = "src_awesome_gpt_image_2"
    route_ids = ["route_gpt_image_2_high"]
    template_ids: list[str] = []

    for index, template in enumerate(db.get("templates", [])):
        tid = f"tpl_{template['id'].replace('-', '_')}"
        template_ids.append(tid)
        cover = template.get("cover") or template.get("sourceCase", {}).get("image")
        asset_id = None
        if cover:
            asset_id = f"asset_cover_{template['id'].replace('-', '_')}"
            insert_asset(conn, asset_id, "template_cover", cover)

        param_count = len(template.get("params") or [])
        route_id = route_ids[index % len(route_ids)]
        usage = max(0, 96 - (index % 30) * 3) if index < 80 else random.randint(0, 28)
        conversion = max(2.0, 19.5 - (index % 18) * 0.6)

        conn.execute(
            """
            INSERT INTO templates(
                id, source_id, source_template_id, case_id, category_id, title, description,
                prompt_template, negative_prompt, cover_asset_id, cover_url, image_alt,
                source_label, source_url, original_url, status, featured, credit_cost,
                default_model_route_id, default_quality, default_aspect_ratio, default_size,
                allow_reference_image, sort_score, usage_count, conversion_rate, metadata_json,
                created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, 'enabled', ?, ?, ?, 'high', ?, ?,
                    1, ?, ?, ?, ?, 'user_admin', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source_id = excluded.source_id,
                source_template_id = excluded.source_template_id,
                case_id = excluded.case_id,
                category_id = excluded.category_id,
                title = excluded.title,
                description = excluded.description,
                prompt_template = excluded.prompt_template,
                cover_asset_id = excluded.cover_asset_id,
                cover_url = excluded.cover_url,
                image_alt = excluded.image_alt,
                source_label = excluded.source_label,
                source_url = excluded.source_url,
                original_url = excluded.original_url,
                status = excluded.status,
                featured = excluded.featured,
                credit_cost = excluded.credit_cost,
                default_model_route_id = excluded.default_model_route_id,
                default_quality = excluded.default_quality,
                default_aspect_ratio = excluded.default_aspect_ratio,
                default_size = excluded.default_size,
                allow_reference_image = excluded.allow_reference_image,
                sort_score = excluded.sort_score,
                usage_count = excluded.usage_count,
                conversion_rate = excluded.conversion_rate,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (
                tid,
                source_id,
                template.get("id"),
                template.get("caseId"),
                category_ids.get(template.get("category")),
                template.get("title") or "未命名模板",
                template.get("description") or "",
                template.get("promptTemplate") or template.get("description") or "",
                asset_id,
                cover,
                template.get("imageAlt"),
                template.get("sourceLabel"),
                template.get("sourceUrl"),
                template.get("githubUrl"),
                1 if template.get("featured") or index < 30 else 0,
                8 if param_count >= 4 else 5,
                route_id,
                infer_aspect_ratio(template),
                infer_size(template),
                1000 - index,
                usage,
                conversion,
                json_dumps({
                    "tags": template.get("tags") or [],
                    "scenes": template.get("scenes") or [],
                    "sourceCase": template.get("sourceCase") or {},
                }),
                now(),
                now(),
            ),
        )

        for p_index, param in enumerate(template.get("params") or []):
            conn.execute(
                """
                INSERT OR REPLACE INTO template_params(
                    id, template_id, param_key, label, token, default_value, param_type, required, options_json, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]', ?)
                """,
                (
                    f"tparam_{template['id'].replace('-', '_')}_{p_index+1}",
                    tid,
                    param.get("key") or f"param_{p_index+1}",
                    param.get("label") or param.get("key") or f"参数 {p_index+1}",
                    param.get("token"),
                    param.get("default") or "",
                    param.get("type") or "text",
                    1,
                    p_index,
                ),
            )

        for tag in template.get("tags") or []:
            tag_id = f"tag_{slugify(tag).replace('-', '_')}"
            conn.execute("INSERT OR IGNORE INTO template_tags(id, name, slug) VALUES (?, ?, ?)", (tag_id, tag, slugify(tag)))
            conn.execute("INSERT OR IGNORE INTO template_tag_map(template_id, tag_id) VALUES (?, ?)", (tid, tag_id))

        for scene in template.get("scenes") or []:
            conn.execute("INSERT OR IGNORE INTO template_scene_map(template_id, scene) VALUES (?, ?)", (tid, scene))

        conn.execute(
            """
            INSERT OR REPLACE INTO prompt_versions(
                id, template_id, version_no, title, prompt_template, params_json, change_note, created_by, created_at
            )
            VALUES (?, ?, 1, ?, ?, ?, 'initial import from local template database', 'user_admin', ?)
            """,
            (
                f"pv_{template['id'].replace('-', '_')}_1",
                tid,
                template.get("title") or "",
                template.get("promptTemplate") or "",
                json_dumps(template.get("params") or []),
                now(),
            ),
        )

    return template_ids


def insert_all_case_images(conn: sqlite3.Connection) -> None:
    images_dir = WEBAPP_ROOT / "assets" / "awesome-gpt-image-2" / "data" / "images"
    if not images_dir.exists():
        return
    for file in images_dir.rglob("*"):
        if not file.is_file():
            continue
        rel_path = file.relative_to(WEBAPP_ROOT).as_posix()
        existing = conn.execute(
            "SELECT id FROM assets WHERE storage_path = ? LIMIT 1",
            (rel_path,),
        ).fetchone()
        if existing:
            continue
        stem = re.sub(r"[^a-zA-Z0-9]+", "_", file.stem).strip("_").lower()
        asset_id = f"asset_case_image_{stem}"
        insert_asset(conn, asset_id, "case_image", rel_path)


def infer_aspect_ratio(template: dict) -> str:
    text = f"{template.get('promptTemplate','')} {template.get('description','')}".lower()
    if "9:16" in text or "vertical" in text or "竖版" in text:
        return "9:16"
    if "3:4" in text:
        return "3:4"
    if "16:9" in text or "landscape" in text or "横版" in text:
        return "16:9"
    return "1:1"


def infer_size(template: dict) -> str:
    ratio = infer_aspect_ratio(template)
    return {
        "9:16": "1024x1792",
        "3:4": "1024x1536",
        "16:9": "1792x1024",
    }.get(ratio, "1024x1024")


def insert_style_templates(conn: sqlite3.Connection, db: dict, category_ids: dict[str, str]) -> None:
    for index, item in enumerate(db.get("styleTemplates") or []):
        title = item.get("title") or {}
        desc = item.get("description") or {}
        conn.execute(
            """
            INSERT OR REPLACE INTO style_templates(
                id, source_id, category_id, title_zh, title_en, description_zh, description_en,
                cover_url, prompt_template, tags_json, guidance_json, pitfalls_json,
                example_cases_json, status, sort_order
            )
            VALUES (?, 'src_awesome_gpt_image_2', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'enabled', ?)
            """,
            (
                f"style_{item.get('id')}",
                category_ids.get(item.get("category")),
                title.get("zh") or title.get("en") or item.get("id"),
                title.get("en"),
                desc.get("zh"),
                desc.get("en"),
                item.get("cover"),
                item.get("promptTemplate") or "",
                json_dumps(item.get("tags") or []),
                json_dumps(item.get("guidance") or {}),
                json_dumps(item.get("pitfalls") or {}),
                json_dumps(item.get("exampleCases") or []),
                index,
            ),
        )


def insert_generation_assets_reviews(conn: sqlite3.Connection, template_ids: list[str]) -> None:
    users = ["user_lijie", "user_xingye", "user_zhou", "user_cafe", "user_orange"]
    orgs = {
        "user_lijie": "org_default",
        "user_xingye": "org_xingye",
        "user_zhou": "org_default",
        "user_cafe": "org_nanxiang",
        "user_orange": "org_default",
    }
    routes = ["route_gpt_image_2_official", "route_gpt_image_2_high", "route_gpt_image_2_fast", "route_gpt_image_2_ultra"]
    statuses = ["success", "running", "failed", "review", "queued", "success", "success", "review", "success", "failed"]

    for index in range(120):
        user_id = users[index % len(users)]
        template_id = template_ids[index % len(template_ids)]
        status = statuses[index % len(statuses)]
        job_id = f"job_seed_{index+1:03d}"
        created_at = iso_minutes_ago(12 + index * 17)
        started = None if status == "queued" else iso_minutes_ago(10 + index * 17)
        finished = iso_minutes_ago(8 + index * 17) if status in {"success", "failed", "review"} else None
        latency = None if not finished else random.randint(8000, 42000)
        conn.execute(
            """
            INSERT OR REPLACE INTO generation_jobs(
                id, job_no, user_id, organization_id, template_id, model_route_id, status,
                prompt_final, prompt_params_json, negative_prompt, quality, aspect_ratio, size,
                output_count, reference_mode, credit_cost, request_payload_json, provider_response_json,
                error_code, error_message, queued_at, started_at, finished_at, latency_ms, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', NULL, ?, ?, ?, 1, 'optional', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                f"JOB-{28000+index}",
                user_id,
                orgs[user_id],
                template_id,
                routes[index % len(routes)],
                status,
                f"基于模板 {template_id} 的用户最终 Prompt",
                "high" if index % 3 else "ultra",
                "3:4" if index % 4 == 0 else "1:1",
                "1024x1536" if index % 4 == 0 else "1024x1024",
                12 if index % 3 == 0 else 5,
                json_dumps({"templateId": template_id}),
                json_dumps({"providerJobId": f"provider_{index}"}),
                "UPSTREAM_TIMEOUT" if status == "failed" else None,
                "上游接口超时，等待重试" if status == "failed" else None,
                created_at,
                started,
                finished,
                latency,
                created_at,
                now(),
            ),
        )
        if status in {"success", "review"}:
            asset_path = f"backend/uploads/generated/job_{index+1:03d}.png"
            asset_id = f"asset_output_{index+1:03d}"
            conn.execute(
                """
                INSERT OR IGNORE INTO assets(
                    id, owner_user_id, organization_id, asset_type, storage_provider, storage_path,
                    public_url, mime_type, status, moderation_status, metadata_json, created_at
                )
                VALUES (?, ?, ?, 'generated_image', 'local', ?, ?, 'image/png', 'active', ?, '{}', ?)
                """,
                (asset_id, user_id, orgs[user_id], asset_path, asset_path, "pending" if status == "review" else "approved", now()),
            )
            conn.execute(
                "INSERT OR IGNORE INTO generation_job_assets(job_id, asset_id, role, sort_order) VALUES (?, ?, 'output', 0)",
                (job_id, asset_id),
            )
            if status == "review" or index % 7 == 0:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO review_items(
                        id, subject_type, subject_id, user_id, risk_level, reason, status,
                        reviewer_user_id, reviewed_at, decision_note, metadata_json, created_at
                    )
                    VALUES (?, 'generation_job', ?, ?, ?, ?, 'pending', NULL, NULL, NULL, '{}', ?)
                    """,
                    (
                        f"review_{index+1:03d}",
                        job_id,
                        user_id,
                        "medium" if index % 2 else "low",
                        "生成结果需要确认版权、真人授权或品牌词使用",
                        now(),
                    ),
                )

        if status in {"success", "failed"}:
            account_id = f"ca_{user_id}"
            amount = 12 if index % 3 == 0 else 5
            balance_row = conn.execute("SELECT balance FROM credit_accounts WHERE id = ?", (account_id,)).fetchone()
            current_balance = balance_row[0] if balance_row else 0
            new_balance = max(0, current_balance - amount)
            conn.execute(
                """
                UPDATE credit_accounts
                SET balance = ?, lifetime_spent = lifetime_spent + ?, updated_at = ?
                WHERE id = ?
                """,
                (new_balance, amount, now(), account_id),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO credit_ledger(
                    id, account_id, user_id, direction, amount, balance_after, reason,
                    reference_type, reference_id, operator_user_id, metadata_json, created_at
                )
                VALUES (?, ?, ?, 'debit', ?, ?, 'generation_cost', 'generation_job', ?, NULL, '{}', ?)
                """,
                (f"ledger_job_{index+1:03d}", account_id, user_id, amount, new_balance, job_id, created_at),
            )
            if status == "failed":
                refund_balance = new_balance + amount
                conn.execute(
                    """
                    UPDATE credit_accounts
                    SET balance = ?, lifetime_spent = MAX(lifetime_spent - ?, 0), updated_at = ?
                    WHERE id = ?
                    """,
                    (refund_balance, amount, now(), account_id),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO credit_ledger(
                        id, account_id, user_id, direction, amount, balance_after, reason,
                        reference_type, reference_id, operator_user_id, metadata_json, created_at
                    )
                    VALUES (?, ?, ?, 'refund', ?, ?, 'generation_failed_refund', 'generation_job', ?, 'user_admin', '{}', ?)
                    """,
                    (f"ledger_refund_job_{index+1:03d}", account_id, user_id, amount, refund_balance, job_id, created_at),
                )


def insert_rules_collections_logs_stats(conn: sqlite3.Connection, template_ids: list[str]) -> None:
    rules = [
        ("rule_brand", "品牌词人工复核", "keyword", "logo|品牌|商标", "review", "medium"),
        ("rule_face", "真人照片复核", "keyword", "真人|人像|证件照", "review", "medium"),
        ("rule_sensitive", "高风险敏感内容拦截", "keyword", "暴力|色情|仇恨", "block", "critical"),
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO moderation_rules(id, name, rule_type, pattern, action, risk_level, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """,
        [(rid, name, typ, pattern, action, risk, now()) for rid, name, typ, pattern, action, risk in rules],
    )

    conn.execute(
        "INSERT OR REPLACE INTO collections(id, user_id, name, description, visibility, created_at) VALUES ('col_lijie_favorites', 'user_lijie', '常用商品图模板', '李姐服装店收藏', 'private', ?)",
        (now(),),
    )
    for order, tid in enumerate(template_ids[:8]):
        conn.execute(
            """
            INSERT OR REPLACE INTO collection_items(collection_id, template_id, item_type, sort_order, created_at)
            VALUES ('col_lijie_favorites', ?, 'template', ?, ?)
            """,
            (tid, order, now()),
        )

    for index, tid in enumerate(template_ids[:24]):
        stat_date = (datetime.now(timezone.utc) - timedelta(days=index % 7)).date().isoformat()
        views = random.randint(80, 1800)
        opens = int(views * random.uniform(0.18, 0.38))
        generations = int(opens * random.uniform(0.18, 0.48))
        successes = int(generations * random.uniform(0.88, 0.99))
        downloads = int(successes * random.uniform(0.52, 0.84))
        paid = int(downloads * random.uniform(0.06, 0.22))
        conn.execute(
            """
            INSERT OR REPLACE INTO template_daily_stats(
                stat_date, template_id, views, opens, generations, successes, downloads, paid_conversions, revenue_cents
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (stat_date, tid, views, opens, generations, successes, downloads, paid, paid * random.choice([1900, 2900, 9900])),
        )

    for route in ["route_gpt_image_2_official", "route_gpt_image_2_high", "route_gpt_image_2_fast", "route_gpt_image_2_ultra"]:
        for days in range(7):
            requests = random.randint(120, 880)
            successes = int(requests * random.uniform(0.92, 0.985))
            conn.execute(
                """
                INSERT OR REPLACE INTO model_daily_stats(
                    stat_date, model_route_id, requests, successes, failures, avg_latency_ms, credits_spent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat(),
                    route,
                    requests,
                    successes,
                    requests - successes,
                    random.randint(9000, 36000),
                    requests * random.choice([3, 5, 12]),
                ),
            )

    audit_logs = [
        ("audit_001", "user_admin", "template.sync", "template_source", "src_awesome_gpt_image_2", None, {"count": len(template_ids)}),
        ("audit_002", "user_admin", "model_route.update", "model_route", "route_gpt_image_2_high", {"credit_cost": 6}, {"credit_cost": 5}),
        ("audit_003", "user_admin", "credit.grant", "user", "user_lijie", None, {"amount": 100}),
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO admin_audit_logs(
            id, actor_user_id, action, entity_type, entity_id, before_json, after_json, ip_address, user_agent, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, '127.0.0.1', 'seed-script', ?)
        """,
        [(aid, actor, action, etype, eid, json_dumps(before) if before else None, json_dumps(after), now()) for aid, actor, action, etype, eid, before, after in audit_logs],
    )

    events = []
    event_names = ["page_view", "template_open", "generate_submit", "download_click", "pay_click"]
    for index in range(160):
        events.append((
            f"evt_{index+1:04d}",
            random.choice(["user_lijie", "user_xingye", "user_zhou", "user_cafe", "user_orange", None]),
            f"anon_{random.randint(1000, 9999)}",
            random.choice(event_names),
            random.choice(["/", "/templates.html", "/index.html#template-editor"]),
            "template",
            random.choice(template_ids[:80]),
            json_dumps({"source": "seed", "device": random.choice(["desktop", "mobile"])}),
            iso_minutes_ago(random.randint(1, 3000)),
        ))
    conn.executemany(
        """
        INSERT OR REPLACE INTO analytics_events(
            id, user_id, anonymous_id, event_name, page, entity_type, entity_id, properties_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        events,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize AI Workshop SQLite database.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--force-reset", action="store_true", help="Allow deleting an existing database after an external backup is confirmed.")
    args = parser.parse_args()

    db = load_local_db()
    conn = connect(args.db, args.reset, args.force_reset)
    try:
        with conn:
            apply_schema(conn)
            insert_app_settings(conn)
            insert_roles_orgs_users(conn)
            insert_pricing_orders(conn)
            category_ids = insert_template_taxonomy(conn, db)
            insert_model_routes(conn)
            template_ids = insert_templates(conn, db, category_ids)
            insert_all_case_images(conn)
            insert_style_templates(conn, db, category_ids)
            insert_generation_assets_reviews(conn, template_ids)
            insert_rules_collections_logs_stats(conn, template_ids)
    finally:
        conn.close()

    print(f"Database initialized: {args.db}")
    print(f"Imported templates: {len(db.get('templates', []))}")
    print(f"Imported style templates: {len(db.get('styleTemplates', []))}")


if __name__ == "__main__":
    main()
