from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import ipaddress
import json
import math
import mimetypes
import os
import re
import secrets
import sqlite3
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urlencode, urljoin, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
WEBAPP_ROOT = ROOT / "webapp"
DB_PATH = ROOT / "backend" / "data" / "app.db"
SYNC_SCRIPT = ROOT / "backend" / "scripts" / "sync_templates_to_db.py"
VIDEO_SYNC_SCRIPT = ROOT / "backend" / "scripts" / "sync_video_templates.py"
REPO_SYNC_SCRIPT = ROOT / "tools" / "sync-awesome-gpt-image-2.ps1"
if not SYNC_SCRIPT.exists():
    sync_db_candidates = sorted((ROOT / "backend" / "scripts").glob("sync_templates_to_db*.py"), key=lambda path: path.stat().st_mtime, reverse=True)
    if sync_db_candidates:
        SYNC_SCRIPT = sync_db_candidates[0]
if not REPO_SYNC_SCRIPT.exists():
    sync_candidates = sorted((ROOT / "tools").glob("sync-awesome-gpt-image-2*.ps1"))
    if sync_candidates:
        REPO_SYNC_SCRIPT = sync_candidates[0]
APIMART_BASE_URL_ENV = os.environ.get("APIMART_BASE_URL")
APIMART_BASE_URL = (APIMART_BASE_URL_ENV or "https://api.apimart.ai").rstrip("/")
APIMART_API_KEY = os.environ.get("APIMART_API_KEY", "")
JEEPAY_BASE_URL = os.environ.get("JEEPAY_BASE_URL", "").rstrip("/")
JEEPAY_MCH_NO = os.environ.get("JEEPAY_MCH_NO", "").strip()
JEEPAY_APP_ID = os.environ.get("JEEPAY_APP_ID", "").strip()
JEEPAY_API_KEY = os.environ.get("JEEPAY_API_KEY", "").strip()
JEEPAY_NOTIFY_SECRET = os.environ.get("JEEPAY_NOTIFY_SECRET", "").strip()
PAYMENT_PROVIDER_ENV = os.environ.get("YCIMAGE_PAYMENT_PROVIDER", "").strip().lower()
MPAY_BASE_URL = os.environ.get("MPAY_BASE_URL", "").strip().rstrip("/")
MPAY_PID = os.environ.get("MPAY_PID", "").strip()
MPAY_KEY = os.environ.get("MPAY_KEY", "").strip()
MPAY_SUBMIT_PATH = os.environ.get("MPAY_SUBMIT_PATH", "/submit.php").strip() or "/submit.php"
MPAY_MAPI_PATH = os.environ.get("MPAY_MAPI_PATH", "/mapi.php").strip() or "/mapi.php"
MPAY_NOTIFY_URL = os.environ.get("MPAY_NOTIFY_URL", "").strip()
MPAY_RETURN_URL = os.environ.get("MPAY_RETURN_URL", "").strip()
MPAY_OLD_KEYS = [item.strip() for item in os.environ.get("MPAY_OLD_KEYS", "").split(",") if item.strip()]
YCIMAGE_ENV = os.environ.get("YCIMAGE_ENV", os.environ.get("APP_ENV", "development")).strip().lower()
IS_PRODUCTION = YCIMAGE_ENV in {"prod", "production"}
YCIMAGE_SECRET_KEY = os.environ.get("YCIMAGE_SECRET_KEY", "").strip()
YCIMAGE_ADMIN_TOKEN = os.environ.get("YCIMAGE_ADMIN_TOKEN", "").strip()
YCIMAGE_ADMIN_TOKEN_REMOTE = os.environ.get("YCIMAGE_ADMIN_TOKEN_REMOTE", "").lower() in {"1", "true", "yes", "on"}
YCIMAGE_ADMIN_PASSWORD = os.environ.get("YCIMAGE_ADMIN_PASSWORD", "")
DEFAULT_ADMIN_PASSWORD = os.environ.get("YCIMAGE_DEFAULT_ADMIN_PASSWORD", "Admin123456")
ENABLE_MOBILE_AUTH = os.environ.get("YCIMAGE_ENABLE_MOBILE_AUTH", "").lower() in {"1", "true", "yes", "on"}
DEBUG_AUTH_CODES = (not IS_PRODUCTION) and os.environ.get("YCIMAGE_DEBUG_AUTH_CODES", "").lower() in {"1", "true", "yes", "on"}
ENABLE_WECHAT_MOCK_LOGIN = (not IS_PRODUCTION) and os.environ.get("YCIMAGE_ENABLE_WECHAT_MOCK_LOGIN", "").lower() in {"1", "true", "yes", "on"}
ADMIN_CONSOLE_PERMISSIONS = {
    "templates:read",
    "templates:write",
    "templates:sync",
    "jobs:read",
    "jobs:write",
    "models:read",
    "models:write",
    "users:read",
    "users:write",
    "credits:grant",
    "reviews:write",
    "settings:write",
    "payments:config",
}
ALLOWED_CORS_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.environ.get(
        "YCIMAGE_ALLOWED_ORIGINS",
        "http://127.0.0.1:4178,http://localhost:4178",
    ).split(",")
    if origin.strip()
}
PUBLIC_ROOT_FILES = {
    "index.html",
    "templates.html",
    "account.html",
    "admin.html",
    "legal.html",
    "privacy.html",
    "terms.html",
    "refund.html",
    "content-policy.html",
    "payment-security.html",
    "styles.css",
    "script.js",
    "templates.js",
    "account.css",
    "account.js",
    "admin.css",
    "admin.js",
    "legal.css",
}
PUBLIC_ASSET_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".ico", ".mp4", ".webm"}
PUBLIC_ASSET_JS_FILES = {"assets/vendor/qrcode.min.js", "webapp/assets/vendor/qrcode.min.js"}
BLOCKED_STATIC_DIRS = {"backend", "tools", ".git", ".external", ".playwright-cli", "node_modules", "__pycache__"}
BLOCKED_STATIC_PARTS = {
    "mpay_v2_webman-master",
    "config",
    "database",
    "support",
}
BLOCKED_STATIC_FILENAMES = {
    ".env",
    ".env.example",
    "composer.json",
    "composer.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "windows.bat",
    "start.php",
}
BLOCKED_STATIC_SUFFIXES = {".php", ".py", ".ps1", ".bat", ".cmd", ".sh", ".sql", ".toml", ".ini", ".log", ".db", ".sqlite"}
PLAN_CODE_ALIASES = {
    "basic": "monthly",
    "pro": "creator",
    "pack200": "pack_200",
    "pack600": "pack_600",
    "pack1500": "pack_1500",
    "pack6000": "pack_6000",
}
SUBSCRIPTION_PLAN_RANK = {
    "monthly": 1,
    "creator": 2,
    "studio": 3,
}
ALLOWED_MEMBERSHIP_LEVELS = {"free", "monthly", "creator", "studio", "enterprise"}


def effective_apimart_api_key(conn: sqlite3.Connection | None = None) -> str:
    if APIMART_API_KEY:
        return APIMART_API_KEY
    if not conn:
        return ""
    row = conn.execute("SELECT metadata_json FROM model_providers WHERE id = 'provider_apimart' LIMIT 1").fetchone()
    if not row:
        row = conn.execute("SELECT metadata_json FROM model_providers WHERE id = 'provider_openai_compatible' LIMIT 1").fetchone()
    metadata = json_loads(row["metadata_json"], {}) if row else {}
    return metadata_secret_value(metadata, "apiKey")


def effective_apimart_base_url(conn: sqlite3.Connection | None = None) -> str:
    if APIMART_BASE_URL_ENV:
        return APIMART_BASE_URL
    if not conn:
        return APIMART_BASE_URL
    row = conn.execute("SELECT base_url FROM model_providers WHERE id = 'provider_apimart' LIMIT 1").fetchone()
    if not row:
        row = conn.execute("SELECT base_url FROM model_providers WHERE id = 'provider_openai_compatible' LIMIT 1").fetchone()
    return str((row["base_url"] if row else "") or APIMART_BASE_URL).rstrip("/")

APIMART_OFFICIAL_ROUTE_CODE = "gpt-image-2-official"
APIMART_OFFICIAL_MODEL = "gpt-image-2-official"
DEFAULT_IMAGE_ROUTE_CODE = "gpt-image-2-high"
APIMART_OFFICIAL_SIZES = ["auto", "1:1", "3:4", "4:3", "4:5", "5:4", "2:3", "3:2", "16:9", "9:16", "2:1", "1:2", "21:9", "9:21"]
APIMART_PIXEL_SIZE_TO_RATIO = {
    "1024x1024": "1:1",
    "1536x1536": "1:1",
    "2048x2048": "1:1",
    "1024x1280": "4:5",
    "1280x1024": "5:4",
    "1024x1536": "2:3",
    "1536x1024": "3:2",
    "1024x1792": "9:16",
    "1792x1024": "16:9",
}
APIMART_PIXEL_SIZE_TO_RESOLUTION = {
    "1024x1024": "1k",
    "1536x1024": "1k",
    "1024x1536": "1k",
    "1024x768": "1k",
    "768x1024": "1k",
    "1280x1024": "1k",
    "1024x1280": "1k",
    "1536x864": "1k",
    "864x1536": "1k",
    "2048x1024": "1k",
    "1024x2048": "1k",
    "1536x512": "1k",
    "512x1536": "1k",
    "2016x864": "1k",
    "864x2016": "1k",
    "2048x2048": "2k",
    "2048x1360": "2k",
    "1360x2048": "2k",
    "2048x1536": "2k",
    "1536x2048": "2k",
    "2560x2048": "2k",
    "2048x2560": "2k",
    "2048x1152": "2k",
    "1152x2048": "2k",
    "2688x1344": "2k",
    "1344x2688": "2k",
    "3072x1024": "2k",
    "1024x3072": "2k",
    "2688x1152": "2k",
    "1152x2688": "2k",
    "2880x2880": "4k",
    "3520x2336": "4k",
    "2336x3520": "4k",
    "3312x2480": "4k",
    "2480x3312": "4k",
    "3216x2576": "4k",
    "2576x3216": "4k",
    "3840x2160": "4k",
    "2160x3840": "4k",
    "3840x1920": "4k",
    "1920x3840": "4k",
    "3840x1280": "4k",
    "1280x3840": "4k",
    "3840x1648": "4k",
    "1648x3840": "4k",
}

QUALITY_ALIASES = {
    "draft": "low",
    "standard": "medium",
    "ultra": "high",
}

QUALITY_CREDIT_RULES = {
    "auto": {"label": "Auto", "factor": 1},
    "low": {"label": "Low", "factor": 0.7},
    "medium": {"label": "Medium", "factor": 1},
    "high": {"label": "High", "factor": 1.35},
}

SIZE_CREDIT_RULES = {
    "auto": {"label": "Auto", "factor": 1},
    "1:1": {"label": "1:1", "factor": 1},
    "3:4": {"label": "3:4", "factor": 1.2},
    "4:3": {"label": "4:3", "factor": 1.2},
    "4:5": {"label": "4:5", "factor": 1.2},
    "5:4": {"label": "5:4", "factor": 1.2},
    "2:3": {"label": "2:3", "factor": 1.3},
    "3:2": {"label": "3:2", "factor": 1.3},
    "16:9": {"label": "16:9", "factor": 1.3},
    "9:16": {"label": "9:16", "factor": 1.3},
    "2:1": {"label": "2:1", "factor": 1.6},
    "1:2": {"label": "1:2", "factor": 1.6},
    "21:9": {"label": "21:9", "factor": 1.8},
    "9:21": {"label": "9:21", "factor": 1.8},
    "1024x1024": {"label": "1024 x 1024", "factor": 1},
    "1024x1536": {"label": "1024 x 1536", "factor": 1.3},
    "1536x1024": {"label": "1536 x 1024", "factor": 1.3},
    "1536x1536": {"label": "1536 x 1536", "factor": 1.8},
    "2048x2048": {"label": "2048 x 2048", "factor": 2.6},
}

VIDEO_RESOLUTION_CREDIT_RULES = {
    "480p": {"label": "480p", "factor": 0.75},
    "720p": {"label": "720p", "factor": 1},
    "1080p": {"label": "1080p", "factor": 1.7},
}
ALLOWED_MODEL_MODALITIES = {"image", "video"}
ALLOWED_MODEL_QUALITIES = {"auto", "low", "medium", "high"}

ACCOUNT_JOB_HISTORY_LIMIT = 10
ACCOUNT_CUSTOM_TEMPLATE_LIMIT = 10
CUSTOM_TEMPLATE_METADATA_MARKER = '"savedFrom":"custom-image-workbench"'
RESULT_DOWNLOAD_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
IMAGE_GENERATION_TIMEOUT_FLOOR = 180
IMAGE_REFERENCE_UPLOAD_TIMEOUT = 180
IMAGE_REFERENCE_UPLOAD_RETRY_LIMIT = 1
RESULT_DOWNLOAD_TIMEOUT_SECONDS = 120
IMAGE_JOB_STALE_MINUTES = 8
VIDEO_JOB_STALE_MINUTES = 15
MAX_JSON_BODY_BYTES = int(os.environ.get("YCIMAGE_MAX_JSON_BODY_BYTES", str(10 * 1024 * 1024)))
MAX_FORM_BODY_BYTES = int(os.environ.get("YCIMAGE_MAX_FORM_BODY_BYTES", str(64 * 1024)))
MAX_REFERENCE_IMAGE_BYTES = int(os.environ.get("YCIMAGE_MAX_REFERENCE_IMAGE_BYTES", str(5 * 1024 * 1024)))
MAX_REFERENCE_IMAGE_COUNT = int(os.environ.get("YCIMAGE_MAX_REFERENCE_IMAGE_COUNT", "10"))
MAX_PROMPT_LENGTH = int(os.environ.get("YCIMAGE_MAX_PROMPT_LENGTH", "8000"))
MAX_REMOTE_DOWNLOAD_BYTES = int(os.environ.get("YCIMAGE_MAX_REMOTE_DOWNLOAD_BYTES", str(25 * 1024 * 1024)))
SESSION_TTL_SECONDS = int(os.environ.get("YCIMAGE_SESSION_TTL_SECONDS", str(60 * 60 * 24 * 14)))
SECURE_COOKIES = IS_PRODUCTION or os.environ.get("YCIMAGE_SECURE_COOKIES", "").lower() in {"1", "true", "yes", "on"}
MAX_ADMIN_CREDIT_GRANT = int(os.environ.get("YCIMAGE_MAX_ADMIN_CREDIT_GRANT", "10000"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("YCIMAGE_RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_RULES = {
    "/api/auth/password-login": (8, 60),
    "/api/auth/register": (5, 60),
    "/api/auth/mobile-code": (5, 60),
    "/api/auth/logout-all": (4, 60),
    "/api/pay/orders": (10, 60),
    "/api/generate-image": (12, 60),
    "/api/generate-video": (8, 60),
}
DEFAULT_WRITE_RATE_LIMIT = (120, 60)
RATE_LIMIT_BUCKETS: dict[tuple[str, str], list[float]] = {}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def session_token() -> str:
    return secrets.token_urlsafe(48)


def slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_loads(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


SECRET_PREFIX = "enc:v1:"
ENCRYPTED_SECRET_FIELDS = {
    "apiKey": "apiKeyEncrypted",
    "mpayKey": "mpayKeyEncrypted",
    "notifySecret": "notifySecretEncrypted",
}
SECRET_SETTING_KEYS = {
    "payment.mpay_key",
    "payment.notify_secret",
    "payment.jeepay_api_key",
}


def secret_key_material() -> str:
    material = YCIMAGE_SECRET_KEY or YCIMAGE_ADMIN_TOKEN or MPAY_KEY or APIMART_API_KEY or DEFAULT_ADMIN_PASSWORD
    if IS_PRODUCTION and not YCIMAGE_SECRET_KEY:
        raise RuntimeError("YCIMAGE_SECRET_KEY is required before storing encrypted secrets in production")
    return material or "ycimage-local-secret"


def validate_runtime_security_config() -> None:
    if not IS_PRODUCTION:
        return
    problems: list[str] = []
    if len(YCIMAGE_SECRET_KEY) < 32:
        problems.append("YCIMAGE_SECRET_KEY must be at least 32 characters in production")
    if not SECURE_COOKIES:
        problems.append("Secure cookies must be enabled in production")
    if not YCIMAGE_ADMIN_PASSWORD:
        problems.append("YCIMAGE_ADMIN_PASSWORD must be set in production; the bootstrap default is not allowed")
    else:
        try:
            validate_password(YCIMAGE_ADMIN_PASSWORD)
        except ValueError as error:
            problems.append(f"YCIMAGE_ADMIN_PASSWORD is too weak: {error}")
    if YCIMAGE_ADMIN_TOKEN and len(YCIMAGE_ADMIN_TOKEN) < 32:
        problems.append("YCIMAGE_ADMIN_TOKEN must be at least 32 characters when enabled in production")
    if "*" in ALLOWED_CORS_ORIGINS:
        problems.append("YCIMAGE_ALLOWED_ORIGINS cannot contain * in production")
    if any(origin.startswith(("http://localhost", "http://127.0.0.1")) for origin in ALLOWED_CORS_ORIGINS):
        problems.append("YCIMAGE_ALLOWED_ORIGINS cannot contain localhost origins in production")
    if any(origin.startswith("http://") for origin in ALLOWED_CORS_ORIGINS):
        problems.append("YCIMAGE_ALLOWED_ORIGINS must use HTTPS in production")
    if PAYMENT_PROVIDER_ENV == "mpay":
        if not MPAY_PID or not MPAY_KEY:
            problems.append("MPAY_PID and MPAY_KEY are required when MPAY is enabled in production")
        if MPAY_NOTIFY_URL and not is_https_url(MPAY_NOTIFY_URL):
            problems.append("MPAY_NOTIFY_URL must use HTTPS in production")
        if MPAY_RETURN_URL and not is_https_url(MPAY_RETURN_URL):
            problems.append("MPAY_RETURN_URL must use HTTPS in production")
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


def secret_fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError as error:  # pragma: no cover - dependency is present in the bundled runtime
        raise RuntimeError("cryptography is required for encrypted secret storage") from error
    key = base64.urlsafe_b64encode(hashlib.sha256(secret_key_material().encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith(SECRET_PREFIX):
        return text
    token = secret_fernet().encrypt(text.encode("utf-8")).decode("ascii")
    return f"{SECRET_PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not text.startswith(SECRET_PREFIX):
        return text
    token = text[len(SECRET_PREFIX):]
    try:
        return secret_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except Exception as error:  # noqa: BLE001
        raise RuntimeError("Stored secret could not be decrypted; check YCIMAGE_SECRET_KEY") from error


def metadata_secret_value(metadata: dict, field: str) -> str:
    encrypted_field = ENCRYPTED_SECRET_FIELDS.get(field, f"{field}Encrypted")
    if isinstance(metadata, dict) and metadata.get(encrypted_field):
        return decrypt_secret(str(metadata.get(encrypted_field) or ""))
    if isinstance(metadata, dict):
        return str(metadata.get(field) or "")
    return ""


def set_metadata_secret(metadata: dict, field: str, value: str) -> None:
    encrypted_field = ENCRYPTED_SECRET_FIELDS.get(field, f"{field}Encrypted")
    for key in (field, encrypted_field):
        metadata.pop(key, None)
    secret = str(value or "").strip()
    if secret:
        metadata[encrypted_field] = encrypt_secret(secret)


def metadata_secret_configured(metadata: dict, field: str) -> bool:
    encrypted_field = ENCRYPTED_SECRET_FIELDS.get(field, f"{field}Encrypted")
    return bool(isinstance(metadata, dict) and (metadata.get(encrypted_field) or metadata.get(field)))


def app_setting_secret_value(row: sqlite3.Row | None, env_value: str = "") -> str:
    if row and row["value"]:
        return decrypt_secret(str(row["value"]))
    return env_value


def public_safe_error(message: str = "Request failed") -> dict:
    return {"error": message, "message": message, "requestId": uid("req")}


SAFE_CLIENT_ERROR_PATTERNS = (
    re.compile(r"^[A-Za-z0-9 ,.:;_()'\"/@!?+\-\[\]{}#=&]{1,240}$"),
)

SAFE_CLIENT_ERROR_EXACT = {
    "Admin authentication required",
    "Admin password confirmation failed",
    "Admin password change required",
    "Current admin password is incorrect",
    "Current password is incorrect",
    "Email and password are required",
    "Grant reason is required and must be 200 characters or less",
    "Invalid email address",
    "Invalid email or password",
    "Invalid mobile number",
    "Invalid review risk level",
    "Invalid review status",
    "Invalid template status",
    "Missing callback signature",
    "Mobile authentication is disabled",
    "Mobile registration is disabled; please use email registration",
    "New password must differ from current password",
    "New passwords do not match",
    "Only email/password login is enabled",
    "Order is not payable",
    "Order pricing plan does not exist",
    "Password must be at least 8 characters",
    "Password must include at least one digit",
    "Password must include at least one lowercase letter",
    "Password must include at least one uppercase letter",
    "Prompt is required before saving a custom template",
    "Prompt is required before updating a custom template",
    "Prompt is too long",
    "Reference file must be an image",
    "Reference image is too large",
    "Reference image required",
    "Target user does not exist",
    "Target user is required",
    "Template cover is too large",
    "Template cover must be 10MB or smaller",
    "Template cover must be an image",
    "Template cover must be an uploaded image or a public image asset",
    "Template cover path is not allowed",
    "Template not found or already deleted",
    "Too many reference images; max 10",
    "Unsupported reference image type",
    "Verification code has expired",
    "Verification code is incorrect",
    "Verification code is required",
}


def safe_client_error_message(error, fallback: str = "Request failed") -> str:
    message = str(error or "").strip()
    if not message:
        return fallback
    if message in SAFE_CLIENT_ERROR_EXACT:
        return message
    if message.startswith("Insufficient credits: current ") and " required " in message:
        return message[:240]
    if message.startswith("Credit amount must be between "):
        return message[:240]
    if message.startswith("Current account can save at most "):
        return message[:240]
    if message.startswith("Too many reference images; max "):
        return message[:240]
    if message.startswith("Template ") and " not found" in message:
        return message[:240]
    if message == "Admin permission required":
        return "Access denied"
    if message.startswith("Admin password confirmation is required for "):
        return "Admin password confirmation is required"
    if message.startswith("Admin permission required: "):
        return "Access denied"
    if message.startswith("Invalid job status transition: "):
        return "Invalid job status transition"
    if any(pattern.fullmatch(message) for pattern in SAFE_CLIENT_ERROR_PATTERNS):
        lowered = message.lower()
        blocked_markers = ("traceback", "select ", "insert ", "update ", "delete ", " from ", ".py", "http://", "https://", "exception")
        if not any(marker in lowered for marker in blocked_markers):
            return message[:240]
    return fallback


def client_error_payload(error, status: int = 400, fallback: str = "Request failed", extra: dict | None = None) -> dict:
    message = safe_client_error_message(error, fallback)
    payload = {"error": message, "message": message}
    if status >= 500:
        payload["requestId"] = uid("req")
    if extra:
        payload.update(extra)
    return payload


def is_custom_template_metadata(value) -> bool:
    metadata = value if isinstance(value, dict) else json_loads(value, {})
    return isinstance(metadata, dict) and metadata.get("savedFrom") == "custom-image-workbench"


SENSITIVE_FIELD_MARKERS = (
    "key",
    "secret",
    "token",
    "password",
    "authorization",
    "cookie",
    "sign",
    "signature",
)


def is_https_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def sanitize_request_target(target: str) -> str:
    parsed = urlparse(str(target or ""))
    if not parsed.query:
        return str(target or "")
    redacted = []
    for key, values in parse_qs(parsed.query, keep_blank_values=True).items():
        key_text = key.lower()
        safe_values = ["***redacted***"] if any(marker in key_text for marker in SENSITIVE_FIELD_MARKERS) else values
        for value in safe_values:
            redacted.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(redacted, doseq=True)))


def redact_sensitive(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(marker in key_text for marker in SENSITIVE_FIELD_MARKERS):
                redacted[key] = "***redacted***"
            else:
                redacted[key] = redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive(item) for item in value]
    return value


def safe_public_payment(payment: dict) -> dict:
    allowed = {
        "provider",
        "channel",
        "state",
        "displayMode",
        "qrcodeUrl",
        "paymentUrl",
        "providerOrderId",
        "message",
    }
    item = {key: payment.get(key) for key in allowed if payment.get(key) is not None}
    for key in ("qrcodeUrl", "paymentUrl"):
        if key in item:
            item[key] = safe_public_payment_url(item[key])
    return item


def safe_public_payment_url(value: str | None) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    if url.startswith("data:image/"):
        try:
            header, encoded = url.split(",", 1)
            mime = header[5:].split(";", 1)[0]
            if mime not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
                return ""
            base64.b64decode(encoded, validate=True)
            return url
        except (ValueError, binascii.Error):
            return ""
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url
    if parsed.scheme.lower() in {"alipays", "weixin", "wechat"}:
        return url
    return ""


def safe_provider_payload(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}
    return redact_sensitive(payload)


PERSISTED_GENERATION_SETTING_KEYS = {
    "model",
    "quality",
    "size",
    "aspectRatio",
    "count",
    "referenceMode",
    "outputFormat",
    "background",
    "moderation",
    "outputCompression",
    "duration",
    "resolution",
    "mode",
    "motion",
    "negativePrompt",
    "cameraControl",
}


def compact_stored_value(value, max_string: int = 500, max_items: int = 30):
    if isinstance(value, str):
        return value[:max_string]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        compact = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                compact["__truncated__"] = True
                break
            key_text = str(key)[:80]
            if any(marker in key_text.lower() for marker in SENSITIVE_FIELD_MARKERS):
                compact[key_text] = "***redacted***"
            else:
                compact[key_text] = compact_stored_value(item, max_string=max_string, max_items=max_items)
        return compact
    if isinstance(value, list):
        return [compact_stored_value(item, max_string=max_string, max_items=max_items) for item in value[:max_items]]
    return str(value)[:max_string]


def safe_provider_generation_payload(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}
    safe = {
        "keys": sorted(str(key) for key in payload.keys())[:30],
        "promptLength": len(str(payload.get("prompt") or "")),
        "negativePromptLength": len(str(payload.get("negative_prompt") or "")),
        "imageUrlCount": len(payload.get("image_urls") or []) if isinstance(payload.get("image_urls"), list) else 0,
    }
    for key in (
        "model",
        "n",
        "size",
        "resolution",
        "quality",
        "duration",
        "aspect_ratio",
        "output_format",
        "background",
        "moderation",
    ):
        if key in payload:
            safe[key] = compact_stored_value(payload.get(key), max_string=120, max_items=10)
    if "camera_control" in payload:
        safe["cameraControlKeys"] = sorted(str(key) for key in (payload.get("camera_control") or {}).keys())[:20] if isinstance(payload.get("camera_control"), dict) else []
    return safe


def safe_generation_request_snapshot(
    original_payload: dict,
    settings: dict,
    reference_images: list[dict],
    provider_payload: dict,
    pricing: dict,
) -> dict:
    request_settings = {
        key: compact_stored_value(value)
        for key, value in (settings or {}).items()
        if key in PERSISTED_GENERATION_SETTING_KEYS
    }
    return {
        "templateId": str(original_payload.get("templateId") or "")[:128],
        "params": compact_stored_value(original_payload.get("params") if isinstance(original_payload.get("params"), dict) else {}),
        "settings": request_settings,
        "referenceImages": compact_stored_value(reference_images, max_string=160, max_items=MAX_REFERENCE_IMAGE_COUNT),
        "providerPayload": safe_provider_generation_payload(provider_payload),
        "pricing": compact_stored_value(pricing),
    }


def safe_provider_response_summary(response: dict | None) -> dict:
    if not isinstance(response, dict):
        return {}
    data = response.get("data")
    message = response.get("message") or response.get("msg") or ""
    return {
        "keys": sorted(str(key) for key in response.keys())[:20],
        "dataType": type(data).__name__ if data is not None else "",
        "code": str(response.get("code") or response.get("status") or "")[:80],
        "messagePresent": bool(message),
        "messageLength": len(str(message)),
    }


def safe_upload_filename(value: str | None, fallback: str) -> str:
    raw = Path(str(value or fallback).replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
    return cleaned[:120] or fallback


def bool_int(value) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value else 0
    if isinstance(value, str):
        return 1 if value.lower() in {"1", "true", "yes", "on", "enabled"} else 0
    return 0


def is_timeout_error_message(message: str | None) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return False
    markers = (
        "timed out",
        "timeout",
        "time out",
        "deadline exceeded",
        "read operation timed out",
        "operation timed out",
        "request timeout",
        "gateway timeout",
    )
    return any(marker in text for marker in markers)


def normalize_upstream_error(error, default_message: str = "Upstream service is temporarily unavailable") -> str:
    message = str(error or "").strip()
    if not message:
        return default_message
    if is_timeout_error_message(message):
        return "Upstream service timed out; please try again later"
    return default_message


def mobile_code_digest(mobile: str, purpose: str, code: str) -> str:
    material = f"{mobile}:{purpose}:{str(code or '').strip()}".encode("utf-8")
    key_material = (YCIMAGE_ADMIN_TOKEN or MPAY_KEY or APIMART_API_KEY or DEFAULT_ADMIN_PASSWORD or "ycimage-local-secret").encode("utf-8")
    return "hmac_sha256:" + hmac.new(key_material, material, hashlib.sha256).hexdigest()


def mobile_code_matches(stored_code: str, mobile: str, purpose: str, submitted_code: str) -> bool:
    submitted_code = str(submitted_code or "").strip()
    if not re.fullmatch(r"\d{6}", submitted_code):
        return False
    stored_code = str(stored_code or "")
    if stored_code.startswith("hmac_sha256:"):
        return hmac.compare_digest(stored_code, mobile_code_digest(mobile, purpose, submitted_code))
    return hmac.compare_digest(submitted_code, stored_code)


ALLOWED_JOB_STATUS_TRANSITIONS = {
    "draft": {"queued", "cancelled"},
    "queued": {"running", "review", "failed", "cancelled"},
    "running": {"success", "review", "failed", "cancelled"},
    "review": {"running", "success", "failed", "cancelled"},
    "failed": {"queued", "running"},
    "cancelled": {"queued", "running"},
    "success": set(),
}
ALLOWED_TEMPLATE_STATUSES = {"enabled", "hidden", "archived"}
ALLOWED_REVIEW_RISK_LEVELS = {"low", "medium", "high", "critical"}
ALLOWED_REVIEW_STATUSES = {"pending", "approved", "rejected", "manual", "escalated"}


def validate_job_status_transition(current_status: str, next_status: str) -> None:
    current = str(current_status or "")
    desired = str(next_status or "")
    if current == desired:
        return
    if desired not in ALLOWED_JOB_STATUS_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid job status transition: {current or 'unknown'} -> {desired or 'unknown'}")


def bounded_int(value, field_name: str, minimum: int, maximum: int, default: int | None = None) -> int:
    if value is None or value == "":
        if default is not None:
            value = default
        else:
            raise ValueError(f"{field_name} is required")
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must be an integer") from error
    if number < minimum or number > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}")
    return number


def bounded_float(value, field_name: str, minimum: float, maximum: float, default: float | None = None) -> float:
    if value is None or value == "":
        if default is not None:
            value = default
        else:
            raise ValueError(f"{field_name} is required")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must be a number") from error
    if number < minimum or number > maximum:
        raise ValueError(f"{field_name} must be between {minimum:g} and {maximum:g}")
    return number


def bounded_text(value, field_name: str, maximum: int, default: str = "", required: bool = False) -> str:
    text = str(value if value is not None else default).strip()
    if required and not text:
        raise ValueError(f"{field_name} is required")
    if len(text) > maximum:
        raise ValueError(f"{field_name} must be {maximum} characters or less")
    return text


def validate_template_status(value) -> str:
    status = str(value or "").strip().lower()
    if status not in ALLOWED_TEMPLATE_STATUSES:
        raise ValueError("Invalid template status")
    return status


def validate_review_risk(value) -> str:
    risk = str(value or "medium").strip().lower()
    if risk not in ALLOWED_REVIEW_RISK_LEVELS:
        raise ValueError("Invalid review risk level")
    return risk


def validate_review_status(value) -> str:
    status = str(value or "").strip().lower()
    if status not in ALLOWED_REVIEW_STATUSES:
        raise ValueError("Invalid review status")
    return status


def route_timeout_seconds(
    route_row: sqlite3.Row | None,
    default: int = 90,
    minimum: int | None = None,
) -> int:
    try:
        timeout = int(route_row["timeout_seconds"] if route_row and route_row["timeout_seconds"] else default)
    except (TypeError, ValueError):
        timeout = int(default)
    if minimum is not None:
        timeout = max(timeout, int(minimum))
    return timeout


def is_public_static_request(rel: str, path: Path) -> bool:
    rel = rel.replace("\\", "/").lstrip("/")
    if not rel:
        return True
    parts = [part for part in rel.split("/") if part]
    if not parts:
        return True
    if any(part.startswith(".") for part in parts):
        return False
    if parts[0] in BLOCKED_STATIC_DIRS:
        return False
    lowered_parts = {part.lower() for part in parts}
    if lowered_parts & BLOCKED_STATIC_PARTS:
        return False
    name = path.name.lower()
    if name in BLOCKED_STATIC_FILENAMES or path.suffix.lower() in BLOCKED_STATIC_SUFFIXES:
        return False
    if name.startswith(("tmp_", "snippet_")):
        return False
    is_asset_path = parts[0] == "assets" or (parts[0] == "webapp" and len(parts) > 1 and parts[1] == "assets")
    if is_asset_path and path.suffix.lower() == ".js":
        return rel in PUBLIC_ASSET_JS_FILES
    if parts[0] == "webapp" and len(parts) > 1 and parts[1] == "assets":
        return path.suffix.lower() in PUBLIC_ASSET_SUFFIXES
    if parts[0] == "assets":
        return path.suffix.lower() in PUBLIC_ASSET_SUFFIXES
    if parts[0] == "webapp":
        return len(parts) == 2 and parts[1] in PUBLIC_ROOT_FILES
    return len(parts) == 1 and rel in PUBLIC_ROOT_FILES


def flatten_query(query: dict) -> dict:
    return {key: values[0] if isinstance(values, list) and values else values for key, values in query.items()}


def epay_v1_sign(params: dict, key: str) -> str:
    parts: list[str] = []
    for name in sorted(params):
        if name in {"sign", "sign_type"}:
            continue
        value = params[name]
        if value is None or value == "" or isinstance(value, (dict, list, tuple, set)):
            continue
        parts.append(f"{name}={value}")
    return hashlib.md5(("&".join(parts) + key).encode("utf-8")).hexdigest()


def epay_v1_signature_matches(params: dict, signature: str, keys: list[str]) -> bool:
    candidate = str(signature or "").lower()
    if not candidate:
        return False
    for key in keys:
        if key and hmac.compare_digest(epay_v1_sign(params, key).lower(), candidate):
            return True
    return False


def epay_channel(channel: str) -> str:
    return {"wechat": "wxpay", "alipay": "alipay"}.get(channel, channel)


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def ensure_credit_ledger_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_credit_ledger_reference
        ON credit_ledger(reference_type, reference_id, direction)
        """
    )
    duplicates = conn.execute(
        """
        SELECT reference_id, COUNT(*) AS count
        FROM credit_ledger
        WHERE reference_type = 'order'
          AND direction = 'credit'
          AND reference_id IS NOT NULL
        GROUP BY reference_id
        HAVING COUNT(*) > 1
        LIMIT 5
        """
    ).fetchall()
    if duplicates:
        sample = ", ".join(f"{row['reference_id']}({row['count']})" for row in duplicates)
        raise RuntimeError(f"Duplicate order credit ledger rows must be reconciled before migration: {sample}")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_credit_ledger_order_credit_once
        ON credit_ledger(reference_type, reference_id, direction)
        WHERE reference_type = 'order' AND direction = 'credit' AND reference_id IS NOT NULL
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
        (2, "credit_ledger_order_idempotency"),
    )


def ensure_auth_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS auth_verification_codes (
            id TEXT PRIMARY KEY,
            mobile TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT 'register',
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            consumed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS referral_codes (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            invite_code TEXT NOT NULL UNIQUE,
            invite_count INTEGER NOT NULL DEFAULT 0,
            reward_credits INTEGER NOT NULL DEFAULT 100,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS referral_events (
            id TEXT PRIMARY KEY,
            inviter_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            invited_user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            invite_code TEXT NOT NULL,
            reward_amount INTEGER NOT NULL DEFAULT 100,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_auth_codes_mobile_created
        ON auth_verification_codes(mobile, created_at DESC);

        CREATE TABLE IF NOT EXISTS auth_password_credentials (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            algorithm TEXT NOT NULL DEFAULT 'pbkdf2_sha256',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    columns = {row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in conn.execute("PRAGMA table_info(auth_password_credentials)").fetchall()}
    if "metadata_json" not in columns:
        conn.execute("ALTER TABLE auth_password_credentials ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")


def migrate_plaintext_secrets(conn: sqlite3.Connection) -> None:
    provider_rows = conn.execute(
        "SELECT id, metadata_json FROM model_providers WHERE metadata_json IS NOT NULL AND metadata_json != ''"
    ).fetchall()
    for row in provider_rows:
        provider_id = row["id"] if isinstance(row, sqlite3.Row) else row[0]
        metadata_json = row["metadata_json"] if isinstance(row, sqlite3.Row) else row[1]
        metadata = json_loads(metadata_json, {})
        if not isinstance(metadata, dict) or not metadata.get("apiKey") or metadata.get("apiKeyEncrypted"):
            continue
        set_metadata_secret(metadata, "apiKey", str(metadata.get("apiKey") or ""))
        conn.execute("UPDATE model_providers SET metadata_json = ? WHERE id = ?", (json_dumps(metadata), provider_id))

    setting_rows = conn.execute(
        "SELECT key, value FROM app_settings WHERE key IN (?, ?, ?)",
        tuple(sorted(SECRET_SETTING_KEYS)),
    ).fetchall()
    for row in setting_rows:
        setting_key = row["key"] if isinstance(row, sqlite3.Row) else row[0]
        raw_value = row["value"] if isinstance(row, sqlite3.Row) else row[1]
        value = str(raw_value or "").strip()
        if not value or value.startswith(SECRET_PREFIX):
            continue
        conn.execute("UPDATE app_settings SET value = ?, updated_at = ? WHERE key = ?", (encrypt_secret(value), now(), setting_key))


def ensure_apimart_official_route(conn: sqlite3.Connection) -> None:
    provider = conn.execute("SELECT metadata_json FROM model_providers WHERE id = 'provider_apimart'").fetchone()
    metadata = json_loads(provider["metadata_json"], {}) if provider else {}
    metadata.update(
        {
            "imageEndpoint": "/v1/images/generations",
            "taskEndpoint": "/v1/tasks/{task_id}",
            "imageUploadEndpoint": "/v1/uploads/images",
            "officialImageModel": APIMART_OFFICIAL_MODEL,
            "docsUrl": "https://docs.apimart.ai/cn/api-reference/images/gpt-image-2/official",
            "auth": "Authorization: Bearer APIMART_API_KEY",
        }
    )
    conn.execute(
        """
        INSERT INTO model_providers(
            id, name, provider_type, base_url, status, server_key_status, health_status, last_checked_at, metadata_json
        )
        VALUES ('provider_apimart', 'APIMart', 'apimart', ?, 'active', 'not_configured', 'unknown', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            provider_type = excluded.provider_type,
            base_url = CASE
                WHEN model_providers.base_url IS NULL OR model_providers.base_url = ''
                THEN excluded.base_url
                ELSE model_providers.base_url
            END,
            status = 'active',
            metadata_json = excluded.metadata_json
        """,
        (APIMART_BASE_URL, now(), json_dumps(metadata)),
    )
    conn.execute(
        """
        INSERT INTO model_routes(
            id, provider_id, route_code, display_name, model_name, modality, quality,
            supported_sizes_json, supported_ratios_json, default_size, default_ratio,
            credit_cost, priority, timeout_seconds, retry_limit, success_rate, avg_latency_ms, status, metadata_json
        )
        VALUES (
            'route_gpt_image_2_official', 'provider_apimart', ?, 'GPT Image 2 Official',
            ?, 'image', 'high', ?, ?, '1:1', '1:1',
            15, 70, 120, 2, 97.8, 18600, 'active', ?
        )
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
            APIMART_OFFICIAL_ROUTE_CODE,
            APIMART_OFFICIAL_MODEL,
            json_dumps(APIMART_OFFICIAL_SIZES),
            json_dumps(APIMART_OFFICIAL_SIZES),
            json_dumps({"source": "apimart_docs", "docsUrl": "https://docs.apimart.ai/cn/api-reference/images/gpt-image-2/official"}),
        ),
    )
    conn.execute(
        """
        INSERT INTO app_settings(key, value, value_type, description, updated_at)
        VALUES ('generation.default_model_route', ?, 'string', 'Default image model route', ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            value_type = excluded.value_type,
            description = excluded.description,
            updated_at = excluded.updated_at
        """,
        (DEFAULT_IMAGE_ROUTE_CODE, now()),
    )


def row_dict(row: sqlite3.Row | None) -> dict:
    return dict(row) if row else {}


def sanitize_connection_test_result(result: dict) -> dict:
    safe = {key: value for key, value in result.items() if key != "attempts"}
    if safe.get("message"):
        safe["message"] = normalize_upstream_error(safe["message"])[:240]
    return safe


def asset_url(asset_id: str | None, fallback: str | None = "") -> str:
    if asset_id:
        return f"/api/assets/{asset_id}"
    return fallback or ""


def assert_public_http_url(value: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("Remote asset URL is not allowed")
    host = parsed.hostname
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise RuntimeError("Remote asset host could not be resolved") from error
    checked: set[str] = set()
    for address in addresses:
        ip_text = address[4][0]
        if ip_text in checked:
            continue
        checked.add(ip_text)
        ip = ipaddress.ip_address(ip_text)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise RuntimeError("Remote asset URL is not allowed")
    return url


class SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        safe_url = assert_public_http_url(urljoin(req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, safe_url)


SAFE_URL_OPENER = build_opener(SafeRedirectHandler)


def category_from_value(conn: sqlite3.Connection, value: str | None) -> str | None:
    if not value or value == "all":
        return None
    row = conn.execute(
        """
        SELECT id FROM template_categories
        WHERE id = ? OR source_value = ? OR slug = ? OR name_zh = ?
        LIMIT 1
        """,
        (value, value, value, value),
    ).fetchone()
    if row:
        return row["id"]

    slug = slugify(value)
    category_id = f"cat_manual_{slug.replace('-', '_')}"
    conn.execute(
        """
        INSERT OR IGNORE INTO template_categories(
            id, source_value, name_zh, name_en, slug, description, sort_order, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, 999, 1)
        """,
        (category_id, value, value, value, slug, f"{value} category"),
    )
    return category_id


def model_route_id_from_value(conn: sqlite3.Connection, value: str | None) -> str | None:
    if not value:
        value = DEFAULT_IMAGE_ROUTE_CODE
    row = conn.execute(
        """
        SELECT id FROM model_routes
        WHERE id = ? OR route_code = ? OR model_name = ?
        ORDER BY CASE WHEN route_code = ? THEN 0 WHEN id = ? THEN 1 ELSE 2 END, priority DESC
        LIMIT 1
        """,
        (value, value, value, value, value),
    ).fetchone()
    if row:
        return row["id"]
    return None


def route_code_from_id(conn: sqlite3.Connection, route_id: str | None) -> str:
    if not route_id:
        return ""
    row = conn.execute("SELECT route_code FROM model_routes WHERE id = ?", (route_id,)).fetchone()
    return row["route_code"] if row else route_id


def template_modality(conn: sqlite3.Connection, template_id: str | None) -> str:
    if not template_id:
        return ""
    row = conn.execute(
        """
        SELECT t.metadata_json, mr.modality AS route_modality
        FROM templates t
        LEFT JOIN model_routes mr ON mr.id = t.default_model_route_id
        WHERE t.id = ?
        LIMIT 1
        """,
        (template_id,),
    ).fetchone()
    if not row:
        return ""
    metadata = json_loads(row["metadata_json"], {})
    return str(metadata.get("modality") or row["route_modality"] or "image")


def audit(conn: sqlite3.Connection, action: str, entity_type: str, entity_id: str | None, after=None, before=None) -> None:
    conn.execute(
        """
        INSERT INTO admin_audit_logs(
            id, actor_user_id, action, entity_type, entity_id, before_json, after_json,
            ip_address, user_agent, created_at
        )
        VALUES (?, 'user_admin', ?, ?, ?, ?, ?, '127.0.0.1', 'local-admin-api', ?)
        """,
        (
            uid("audit"),
            action,
            entity_type,
            entity_id,
            json_dumps(before) if before is not None else None,
            json_dumps(after) if after is not None else None,
            now(),
        ),
    )


def upsert_local_asset(conn: sqlite3.Connection, asset_type: str, path_or_url: str | None, prefix: str) -> tuple[str | None, str]:
    if not path_or_url:
        return None, ""
    value = path_or_url.strip()
    if value.startswith("/api/assets/"):
        asset_id = value.rsplit("/", 1)[-1]
        asset = conn.execute("SELECT id, asset_type, owner_user_id FROM assets WHERE id = ? LIMIT 1", (asset_id,)).fetchone()
        if not asset:
            raise ValueError("Referenced asset does not exist")
        if asset["asset_type"] not in {"template_cover", "case_image", "generated_image", "reference_image", "avatar", "other"}:
            raise ValueError("Referenced asset is not an image")
        return asset_id, value
    if value.startswith("http://") or value.startswith("https://"):
        raise ValueError("Remote asset URLs are not allowed; upload the image or use an existing asset")
    if value.startswith("data:image/") and "," in value:
        header, encoded = value.split(",", 1)
        mime = header[5:].split(";", 1)[0] or "image/jpeg"
        if not mime.startswith("image/"):
            raise ValueError("Template cover must be an image")
        try:
            content = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ValueError("Invalid template cover encoding") from exc
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("Template cover must be 10MB or smaller")
        actual_mime = image_mime_from_magic(content)
        if actual_mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise ValueError("Invalid reference image signature")
        if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise ValueError("Unsupported reference image type")
        if actual_mime != mime:
            mime = actual_mime

        checksum = hashlib.sha256(content).hexdigest()
        suffix = mimetypes.guess_extension(mime) or ".jpg"
        asset_id = f"{prefix}_{checksum[:16]}"
        storage_path = f"database://{asset_id}{suffix}"
        conn.execute(
            """
            INSERT INTO assets(
                id, asset_type, storage_provider, storage_path, public_url, mime_type,
                byte_size, checksum, status, moderation_status, metadata_json, created_at
            )
            VALUES (?, ?, 'database', ?, ?, ?, ?, ?, 'active', 'approved', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                asset_type = excluded.asset_type,
                storage_provider = excluded.storage_provider,
                storage_path = excluded.storage_path,
                public_url = excluded.public_url,
                mime_type = excluded.mime_type,
                byte_size = excluded.byte_size,
                checksum = excluded.checksum,
                status = 'active',
                moderation_status = 'approved',
                metadata_json = excluded.metadata_json
            """,
            (
                asset_id,
                asset_type,
                storage_path,
                f"/api/assets/{asset_id}",
                mime,
                len(content),
                checksum,
                json_dumps({"source": "admin_upload"}),
                now(),
            ),
        )
        conn.execute(
            """
            INSERT INTO asset_blobs(asset_id, content, byte_size, sha256, embedded_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                content = excluded.content,
                byte_size = excluded.byte_size,
                sha256 = excluded.sha256,
                embedded_at = excluded.embedded_at
            """,
            (asset_id, sqlite3.Binary(content), len(content), checksum, now()),
        )
        return asset_id, f"/api/assets/{asset_id}"

    rel = value.replace("\\", "/").lstrip("/")
    rel_path = Path(rel)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise ValueError("Template cover path is not allowed")
    full_path = (ROOT / rel).resolve()
    allowed_roots = [
        (WEBAPP_ROOT / "assets").resolve(),
        (ROOT / "assets").resolve(),
    ]
    if (
        not str(full_path).startswith(str(ROOT.resolve()))
        or not full_path.exists()
        or not full_path.is_file()
        or not any(str(full_path).startswith(str(root)) for root in allowed_roots)
        or full_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
    ):
        raise ValueError("Template cover must be an uploaded image or a public image asset")

    content = full_path.read_bytes()
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("Template cover is too large")
    checksum = hashlib.sha256(content).hexdigest()
    mime = mimetypes.guess_type(str(full_path))[0] or "application/octet-stream"
    if mime != "image/svg+xml":
        actual_mime = image_mime_from_magic(content)
        if actual_mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise ValueError("Invalid template cover signature")
        mime = actual_mime
    asset_id = f"{prefix}_{checksum[:16]}"
    conn.execute(
        """
        INSERT INTO assets(
            id, asset_type, storage_provider, storage_path, public_url, mime_type,
            byte_size, checksum, status, moderation_status, metadata_json, created_at
        )
        VALUES (?, ?, 'database', ?, ?, ?, ?, ?, 'active', 'approved', '{}', ?)
        ON CONFLICT(id) DO UPDATE SET
            asset_type = excluded.asset_type,
            storage_path = excluded.storage_path,
            public_url = excluded.public_url,
            mime_type = excluded.mime_type,
            byte_size = excluded.byte_size,
            checksum = excluded.checksum,
            status = 'active',
            moderation_status = 'approved'
        """,
        (asset_id, asset_type, rel, rel, mime, len(content), checksum, now()),
    )
    conn.execute(
        """
        INSERT INTO asset_blobs(asset_id, content, byte_size, sha256, embedded_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
            content = excluded.content,
            byte_size = excluded.byte_size,
            sha256 = excluded.sha256,
            embedded_at = excluded.embedded_at
        """,
        (asset_id, sqlite3.Binary(content), len(content), checksum, now()),
    )
    return asset_id, f"/api/assets/{asset_id}"


def image_mime_from_magic(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return "image/gif"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_reference_images(images: list[dict] | None) -> None:
    image_items = list(images or [])
    if len(image_items) > MAX_REFERENCE_IMAGE_COUNT:
        raise ValueError(f"Too many reference images; max {MAX_REFERENCE_IMAGE_COUNT}")
    for image in image_items:
        data_url = str(image.get("dataUrl") or "")
        if not data_url.startswith("data:image/") or "," not in data_url:
            raise ValueError("Invalid reference image data URL")
        header, encoded = data_url.split(",", 1)
        mime = str(image.get("mimeType") or header[5:].split(";", 1)[0] or "image/jpeg")
        if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise ValueError("Unsupported reference image type")
        try:
            content = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ValueError("Invalid reference image encoding") from exc
        if len(content) > MAX_REFERENCE_IMAGE_BYTES:
            raise ValueError("Reference image is too large")
        actual_mime = image_mime_from_magic(content)
        if actual_mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise ValueError("Invalid reference image signature")


def store_reference_images(conn: sqlite3.Connection, images: list[dict] | None, job_id: str, user_id: str) -> list[dict]:
    validate_reference_images(images)
    image_items = list(images or [])
    if len(image_items) > MAX_REFERENCE_IMAGE_COUNT:
        raise ValueError(f"Too many reference images; max {MAX_REFERENCE_IMAGE_COUNT}")

    stored = []
    for index, image in enumerate(image_items):
        data_url = str(image.get("dataUrl") or "")
        if not data_url.startswith("data:image/") or "," not in data_url:
            raise ValueError("Invalid reference image data URL")

        header, encoded = data_url.split(",", 1)
        mime = str(image.get("mimeType") or header[5:].split(";", 1)[0] or "image/jpeg")
        if not mime.startswith("image/"):
            raise ValueError("Reference file must be an image")

        try:
            content = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ValueError("Invalid reference image encoding") from exc

        if len(content) > MAX_REFERENCE_IMAGE_BYTES:
            raise ValueError("Reference image is too large")
        actual_mime = image_mime_from_magic(content)
        if actual_mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise ValueError("Invalid reference image signature")
        if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
            raise ValueError("Unsupported reference image type")
        if actual_mime != mime:
            mime = actual_mime

        checksum = hashlib.sha256(content).hexdigest()
        asset_id = f"asset_ref_{checksum[:16]}"
        name = str(image.get("name") or f"reference-{index + 1}")
        metadata = {"filename": name, "jobId": job_id, "source": "template_generator"}
        conn.execute(
            """
            INSERT INTO assets(
                id, owner_user_id, organization_id, asset_type, storage_provider, storage_path,
                public_url, mime_type, byte_size, checksum, status, moderation_status, metadata_json, created_at
            )
            VALUES (?, ?, 'org_default', 'reference_image', 'database', ?, ?, ?, ?, ?,
                    'active', 'pending', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                owner_user_id = excluded.owner_user_id,
                organization_id = excluded.organization_id,
                storage_provider = excluded.storage_provider,
                storage_path = excluded.storage_path,
                public_url = excluded.public_url,
                mime_type = excluded.mime_type,
                byte_size = excluded.byte_size,
                checksum = excluded.checksum,
                status = 'active',
                metadata_json = excluded.metadata_json
            """,
            (
                asset_id,
                user_id,
                f"database://{asset_id}",
                f"/api/assets/{asset_id}",
                mime,
                len(content),
                checksum,
                json_dumps(metadata),
                now(),
            ),
        )
        conn.execute(
            """
            INSERT INTO asset_blobs(asset_id, content, byte_size, sha256, embedded_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                content = excluded.content,
                byte_size = excluded.byte_size,
                sha256 = excluded.sha256,
                embedded_at = excluded.embedded_at
            """,
            (asset_id, sqlite3.Binary(content), len(content), checksum, now()),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO generation_job_assets(job_id, asset_id, role, sort_order)
            VALUES (?, ?, 'reference', ?)
            """,
            (job_id, asset_id, index),
        )
        stored.append(
            {
                "assetId": asset_id,
                "url": f"/api/assets/{asset_id}",
                "name": name,
                "mimeType": mime,
                "byteSize": len(content),
            }
        )

    return stored


def asset_id_from_url(value: str | None) -> str | None:
    text = str(value or "").strip()
    if text.startswith("/api/assets/"):
        return text.rsplit("/", 1)[-1]
    return None


def list_generation_job_assets(
    conn: sqlite3.Connection,
    job_id: str,
    role: str | None = None,
) -> list[sqlite3.Row]:
    sql = """
        SELECT
            gja.job_id,
            gja.asset_id,
            gja.role,
            gja.sort_order,
            a.public_url,
            a.mime_type,
            a.asset_type,
            a.owner_user_id
        FROM generation_job_assets gja
        JOIN assets a ON a.id = gja.asset_id
        WHERE gja.job_id = ?
    """
    params: list[object] = [job_id]
    if role:
        sql += " AND gja.role = ?"
        params.append(role)
    sql += " ORDER BY gja.sort_order ASC, gja.asset_id ASC"
    return conn.execute(sql, params).fetchall()


def build_generation_job_asset_urls(conn: sqlite3.Connection, job_id: str, modality: str) -> dict:
    outputs = [asset_url(row["asset_id"], row["public_url"]) for row in list_generation_job_assets(conn, job_id, "output")]
    thumbnails = [asset_url(row["asset_id"], row["public_url"]) for row in list_generation_job_assets(conn, job_id, "thumbnail")]
    if modality == "video":
        return {
            "videoUrl": outputs[0] if outputs else "",
            "thumbnailUrl": thumbnails[0] if thumbnails else "",
        }
    return {
        "imageUrls": outputs,
        "imageUrl": outputs[0] if outputs else "",
        "thumbnailUrl": thumbnails[0] if thumbnails else "",
    }


def download_remote_binary(url: str, timeout: int = RESULT_DOWNLOAD_TIMEOUT_SECONDS) -> tuple[bytes, str]:
    safe_url = assert_public_http_url(url)
    request = Request(
        safe_url,
        headers={
            "User-Agent": RESULT_DOWNLOAD_USER_AGENT,
            "Accept": "image/*,video/*,application/octet-stream;q=0.8,*/*;q=0.5",
        },
        method="GET",
    )
    try:
        with SAFE_URL_OPENER.open(request, timeout=timeout) as response:
            assert_public_http_url(response.geturl())
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_REMOTE_DOWNLOAD_BYTES:
                raise RuntimeError("Remote asset is too large")
            content = response.read(MAX_REMOTE_DOWNLOAD_BYTES + 1)
            if len(content) > MAX_REMOTE_DOWNLOAD_BYTES:
                raise RuntimeError("Remote asset is too large")
            mime = response.headers.get_content_type() or mimetypes.guess_type(safe_url)[0] or "application/octet-stream"
            return content, mime
    except HTTPError as error:
        raise RuntimeError(f"Remote asset download failed: HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError("Remote asset download failed") from error
    except RuntimeError:
        raise
    except Exception as error:  # noqa: BLE001
        raise RuntimeError("Remote asset download failed") from error


def store_generation_job_asset(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    job_id: str,
    role: str,
    source_url: str,
    sort_order: int = 0,
) -> dict:
    local_asset_id = asset_id_from_url(source_url)
    if local_asset_id:
        row = conn.execute("SELECT id, public_url, mime_type, asset_type FROM assets WHERE id = ? LIMIT 1", (local_asset_id,)).fetchone()
        if row:
            conn.execute(
                """
                INSERT OR REPLACE INTO generation_job_assets(job_id, asset_id, role, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (job_id, local_asset_id, role, sort_order),
            )
            return {
                "assetId": row["id"],
                "url": asset_url(row["id"], row["public_url"]),
                "mimeType": row["mime_type"] or "application/octet-stream",
                "assetType": row["asset_type"] or "generated_image",
            }

    content, mime = download_remote_binary(source_url)
    checksum = hashlib.sha256(content).hexdigest()
    suffix = mimetypes.guess_extension(mime) or Path(str(source_url).split("?", 1)[0]).suffix or ".bin"
    asset_type = "generated_video" if mime.startswith("video/") else "generated_image"
    asset_id = f"asset_gen_{job_id[-8:]}_{role}_{sort_order + 1}_{checksum[:8]}"
    storage_path = f"database://{asset_id}{suffix}"
    public_url = f"/api/assets/{asset_id}"
    metadata = {
        "jobId": job_id,
        "role": role,
        "sourceUrl": source_url,
        "sortOrder": sort_order,
    }
    conn.execute(
        """
        INSERT INTO assets(
            id, owner_user_id, organization_id, asset_type, storage_provider, storage_path,
            public_url, mime_type, byte_size, checksum, status, moderation_status, metadata_json, created_at
        )
        VALUES (?, ?, 'org_default', ?, 'database', ?, ?, ?, ?, ?,
                'active', 'approved', ?, ?)
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
            status = 'active',
            moderation_status = 'approved',
            metadata_json = excluded.metadata_json
        """,
        (
            asset_id,
            user_id,
            asset_type,
            storage_path,
            public_url,
            mime,
            len(content),
            checksum,
            json_dumps(metadata),
            now(),
        ),
    )
    conn.execute(
        """
        INSERT INTO asset_blobs(asset_id, content, byte_size, sha256, embedded_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
            content = excluded.content,
            byte_size = excluded.byte_size,
            sha256 = excluded.sha256,
            embedded_at = excluded.embedded_at
        """,
        (asset_id, sqlite3.Binary(content), len(content), checksum, now()),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO generation_job_assets(job_id, asset_id, role, sort_order)
        VALUES (?, ?, ?, ?)
        """,
        (job_id, asset_id, role, sort_order),
    )
    return {"assetId": asset_id, "url": public_url, "mimeType": mime, "assetType": asset_type}


def refresh_completed_job_provider_payload(conn: sqlite3.Connection, job: sqlite3.Row, modality: str) -> dict:
    response_json = json_loads(job["provider_response_json"], {})
    task_id = response_json.get("apimartTaskId") or response_json.get("taskId")
    if not task_id:
        return response_json
    api_key = effective_apimart_api_key(conn)
    if not api_key:
        return response_json
    try:
        provider_status = call_json_api(
            "GET",
            f"{effective_apimart_base_url(conn)}/v1/tasks/{task_id}?language=zh",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
    except Exception:
        return response_json
    task_payload = extract_apimart_task_payload(provider_status)
    local_status = map_apimart_status(task_payload.get("status") if isinstance(task_payload, dict) else "")
    if local_status != "success":
        return response_json
    result_urls = extract_video_result(provider_status) if modality == "video" else extract_image_result(provider_status)
    return {
        **response_json,
        "taskStatus": provider_status,
        "progress": task_payload.get("progress") if isinstance(task_payload, dict) else response_json.get("progress"),
        **result_urls,
    }


def ensure_generation_job_outputs_persisted(conn: sqlite3.Connection, job: sqlite3.Row | None) -> sqlite3.Row | None:
    if not job or job["status"] != "success":
        return job

    model = conn.execute("SELECT modality FROM model_routes WHERE id = ?", (job["model_route_id"],)).fetchone()
    modality = model["modality"] if model else "image"
    existing_rows = list_generation_job_assets(conn, job["id"], "output")
    existing_thumbnail_rows = list_generation_job_assets(conn, job["id"], "thumbnail") if modality == "video" else []
    existing_urls = build_generation_job_asset_urls(conn, job["id"], modality)
    response_json = json_loads(job["provider_response_json"], {})
    source_payload = response_json

    needs_output = not existing_rows
    needs_thumbnail = modality == "video" and not existing_thumbnail_rows
    if needs_output or needs_thumbnail:
        source_payload = refresh_completed_job_provider_payload(conn, job, modality)

    try:
        conn.execute("BEGIN")
        if modality == "video":
            result = extract_video_result(source_payload)
            output_url = existing_urls.get("videoUrl") or result.get("videoUrl") or ""
            thumbnail_url = existing_urls.get("thumbnailUrl") or result.get("thumbnailUrl") or ""
            if output_url and not existing_urls.get("videoUrl"):
                try:
                    store_generation_job_asset(
                        conn,
                        user_id=job["user_id"],
                        job_id=job["id"],
                        role="output",
                        source_url=output_url,
                        sort_order=0,
                    )
                except RuntimeError:
                    pass
            if thumbnail_url and not existing_urls.get("thumbnailUrl"):
                try:
                    store_generation_job_asset(
                        conn,
                        user_id=job["user_id"],
                        job_id=job["id"],
                        role="thumbnail",
                        source_url=thumbnail_url,
                        sort_order=0,
                    )
                except RuntimeError:
                    pass
        else:
            result = extract_image_result(source_payload)
            source_urls = existing_urls.get("imageUrls") or result.get("imageUrls") or []
            if not isinstance(source_urls, list):
                source_urls = [source_urls] if source_urls else []
            if source_urls and not existing_urls.get("imageUrl"):
                for index, source_url in enumerate(source_urls):
                    if not source_url:
                        continue
                    try:
                        store_generation_job_asset(
                            conn,
                            user_id=job["user_id"],
                            job_id=job["id"],
                            role="output",
                            source_url=source_url,
                            sort_order=index,
                        )
                    except RuntimeError:
                        continue

        merged_urls = build_generation_job_asset_urls(conn, job["id"], modality)
        if modality == "video":
            merged_response = {
                **source_payload,
                "videoUrl": merged_urls.get("videoUrl") or source_payload.get("videoUrl") or "",
                "thumbnailUrl": merged_urls.get("thumbnailUrl") or source_payload.get("thumbnailUrl") or "",
            }
        else:
            merged_response = {
                **source_payload,
                "imageUrls": merged_urls.get("imageUrls") or source_payload.get("imageUrls") or [],
                "imageUrl": merged_urls.get("imageUrl") or source_payload.get("imageUrl") or "",
            }
        conn.execute(
            "UPDATE generation_jobs SET provider_response_json = ?, updated_at = ? WHERE id = ?",
            (json_dumps(merged_response), now(), job["id"]),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        return job

    updated_job = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job["id"],)).fetchone()
    merged_response = json_loads(updated_job["provider_response_json"], {}) if updated_job else {}
    if modality == "video":
        still_remote = str(merged_response.get("videoUrl") or "").startswith("http")
        if needs_output and still_remote:
            try:
                conn.execute("BEGIN")
                merged_response["videoUrl"] = ""
                if needs_thumbnail:
                    merged_response["thumbnailUrl"] = ""
                conn.execute(
                    "UPDATE generation_jobs SET provider_response_json = ?, updated_at = ? WHERE id = ?",
                    (json_dumps(merged_response), now(), job["id"]),
                )
                conn.execute("COMMIT")
                updated_job = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job["id"],)).fetchone()
            except Exception:
                conn.execute("ROLLBACK")
    else:
        still_remote = any(str(url or "").startswith("http") for url in (merged_response.get("imageUrls") or [])) or str(merged_response.get("imageUrl") or "").startswith("http")
        if needs_output and still_remote:
            try:
                conn.execute("BEGIN")
                merged_response["imageUrl"] = ""
                merged_response["imageUrls"] = []
                conn.execute(
                    "UPDATE generation_jobs SET provider_response_json = ?, updated_at = ? WHERE id = ?",
                    (json_dumps(merged_response), now(), job["id"]),
                )
                conn.execute("COMMIT")
                updated_job = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job["id"],)).fetchone()
            except Exception:
                conn.execute("ROLLBACK")

    return updated_job


def delete_asset_if_orphaned(conn: sqlite3.Connection, asset_id: str | None) -> None:
    if not asset_id:
        return
    local_url = f"/api/assets/{asset_id}"
    referenced = (
        conn.execute("SELECT 1 FROM generation_job_assets WHERE asset_id = ? LIMIT 1", (asset_id,)).fetchone()
        or conn.execute("SELECT 1 FROM templates WHERE cover_asset_id = ? LIMIT 1", (asset_id,)).fetchone()
        or conn.execute("SELECT 1 FROM templates WHERE cover_url = ? LIMIT 1", (local_url,)).fetchone()
    )
    if referenced:
        return
    conn.execute("DELETE FROM asset_blobs WHERE asset_id = ?", (asset_id,))
    conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))


def prune_account_job_history(conn: sqlite3.Connection, user_id: str, keep: int = ACCOUNT_JOB_HISTORY_LIMIT) -> None:
    old_rows = conn.execute(
        """
        SELECT id
        FROM generation_jobs
        WHERE user_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT -1 OFFSET ?
        """,
        (user_id, keep),
    ).fetchall()
    for row in old_rows:
        job_id = row["id"]
        asset_ids = [item["asset_id"] for item in list_generation_job_assets(conn, job_id)]
        conn.execute("DELETE FROM generation_job_assets WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM generation_jobs WHERE id = ?", (job_id,))
        for asset_id in asset_ids:
            delete_asset_if_orphaned(conn, asset_id)


def ensure_image_route_defaults(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE model_routes
        SET timeout_seconds = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE modality = 'image'
          AND (timeout_seconds IS NULL OR timeout_seconds < ?)
        """,
        (IMAGE_GENERATION_TIMEOUT_FLOOR, IMAGE_GENERATION_TIMEOUT_FLOOR),
    )


def call_json_api(method: str, url: str, headers: dict | None = None, payload: dict | None = None, timeout: int = 60) -> dict:
    safe_url = assert_public_http_url(url)
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = dict(headers or {})
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
    req = Request(safe_url, data=body, headers=request_headers, method=method)
    try:
        with SAFE_URL_OPENER.open(req, timeout=timeout) as response:
            assert_public_http_url(response.geturl())
            raw = response.read()
    except HTTPError as error:
        raise RuntimeError(f"Upstream HTTP {error.code}") from error
    except URLError as error:
        raise RuntimeError("Upstream connection failed") from error
    except RuntimeError:
        raise
    except Exception as error:  # noqa: BLE001
        raise RuntimeError("Upstream request failed") from error
    return json.loads(raw.decode("utf-8")) if raw else {}


def extract_balance_summary(payload: dict) -> str:
    candidates = [payload]
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        candidates.append(data)
    for source in candidates:
        for key in ("balance", "credits", "credit", "remaining", "amount"):
            value = source.get(key) if isinstance(source, dict) else None
            if value is not None and value != "":
                return str(value)
    return ""


def test_apimart_connection(
    conn: sqlite3.Connection,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> dict:
    form_key = str(api_key_override or "").strip()
    saved_base_url = effective_apimart_base_url(conn)
    requested_base_url = str(base_url_override or "").strip().rstrip("/")
    base_url = requested_base_url or saved_base_url
    if requested_base_url and requested_base_url != saved_base_url and not form_key:
        return {
            "ok": False,
            "status": "blocked",
            "message": "Testing a custom APIMart base URL requires a temporary API key",
            "baseUrl": base_url,
            "keySource": "missing",
            "checkedAt": now(),
            "latencyMs": None,
            "balance": "",
            "endpoint": "",
        }
    api_key = form_key or effective_apimart_api_key(conn)
    try:
        assert_public_http_url(base_url)
    except RuntimeError:
        return {
            "ok": False,
            "status": "error",
            "message": "APIMart base URL is not allowed",
            "baseUrl": base_url,
            "keySource": "form" if form_key else ("environment" if APIMART_API_KEY else ("database" if api_key else "missing")),
            "checkedAt": now(),
            "latencyMs": None,
            "balance": "",
            "endpoint": "",
        }
    key_source = "form" if form_key else ("environment" if APIMART_API_KEY else ("database" if api_key else "missing"))
    checked_at = now()
    if not api_key:
        return {
            "ok": False,
            "status": "not_configured",
            "message": "APIMart API key is not configured",
            "baseUrl": base_url,
            "keySource": key_source,
            "checkedAt": checked_at,
            "latencyMs": None,
            "balance": "",
            "endpoint": "",
        }

    endpoints = ("/v1/balance", "/v1/user/balance")
    failures = []
    for endpoint in endpoints:
        started = time.perf_counter()
        try:
            response = call_json_api(
                "GET",
                f"{base_url}{endpoint}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=20,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": True,
                "status": "healthy",
                "message": "APIMart connection is healthy",
                "baseUrl": base_url,
                "keySource": key_source,
                "checkedAt": checked_at,
                "latencyMs": latency_ms,
                "balance": extract_balance_summary(response),
                "endpoint": endpoint,
            }
        except Exception as error:  # noqa: BLE001
            latency_ms = int((time.perf_counter() - started) * 1000)
            failures.append({"endpoint": endpoint, "latencyMs": latency_ms, "error": str(error)[:500]})

    last = failures[-1] if failures else {"endpoint": "", "latencyMs": None, "error": "APIMart connection failed"}
    return {
        "ok": False,
        "status": "error",
        "message": last["error"],
        "baseUrl": base_url,
        "keySource": key_source,
        "checkedAt": checked_at,
        "latencyMs": last["latencyMs"],
        "balance": "",
        "endpoint": last["endpoint"],
        "attempts": failures,
    }


def parse_apimart_task_id(response: dict) -> str:
    data = response.get("data")
    if isinstance(data, list) and data:
        return str(data[0].get("task_id") or data[0].get("id") or "")
    if isinstance(data, dict):
        return str(data.get("task_id") or data.get("id") or "")
    return str(response.get("task_id") or response.get("id") or "")


def upload_image_to_apimart(
    image: dict,
    api_key: str | None = None,
    base_url: str | None = None,
    *,
    timeout: int = IMAGE_REFERENCE_UPLOAD_TIMEOUT,
    retry_limit: int = IMAGE_REFERENCE_UPLOAD_RETRY_LIMIT,
) -> str:
    api_key = api_key or APIMART_API_KEY
    base_url = assert_public_http_url((base_url or APIMART_BASE_URL).rstrip("/"))
    if not api_key:
        raise RuntimeError("APIMart API key is not configured")
    data_url = str(image.get("dataUrl") or "")
    if not data_url.startswith("data:image/") or "," not in data_url:
        raise RuntimeError("Invalid reference image data URL")

    header, encoded = data_url.split(",", 1)
    mime = str(image.get("mimeType") or header[5:].split(";", 1)[0] or "image/jpeg")
    if mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        raise RuntimeError("Unsupported reference image type")
    suffix = mimetypes.guess_extension(mime) or ".jpg"
    filename = safe_upload_filename(image.get("name"), f"reference{suffix}")
    content = base64.b64decode(encoded, validate=True)
    if len(content) > MAX_REFERENCE_IMAGE_BYTES:
        raise RuntimeError("Reference image is too large")
    actual_mime = image_mime_from_magic(content)
    if actual_mime not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        raise RuntimeError("Invalid reference image signature")
    if actual_mime != mime:
        mime = actual_mime
    boundary = f"----YCImage{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")

    payload = {}
    for attempt in range(max(0, int(retry_limit)) + 1):
        req = Request(
            f"{base_url}/v1/uploads/images",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with SAFE_URL_OPENER.open(req, timeout=timeout) as response:
                assert_public_http_url(response.geturl())
                payload = json.loads(response.read().decode("utf-8"))
                break
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            message = normalize_upstream_error(detail or error, "Image upload service is temporarily unavailable")
            raise RuntimeError("APIMart image upload failed: " + message) from error
        except Exception as error:  # noqa: BLE001
            if attempt < max(0, int(retry_limit)) and is_timeout_error_message(str(error)):
                time.sleep(min(2 + attempt, 3))
                continue
            message = normalize_upstream_error(error, "Image upload service is temporarily unavailable")
            raise RuntimeError("APIMart image upload failed: " + message) from error

    data = payload.get("data")
    image_url = payload.get("url")
    if not image_url and isinstance(data, dict):
        image_url = data.get("url")
    if not image_url:
        raise RuntimeError("APIMart upload URL is invalid")
    return str(image_url)


def build_video_payload(route_row: sqlite3.Row | None, settings: dict, prompt: str, reference_images: list[dict], api_key: str | None = None, base_url: str | None = None) -> dict:
    model = route_row["model_name"] if route_row else settings.get("model")
    model = model or "wan2.6-i2v-flash"
    duration = int(settings.get("duration") or 5)
    resolution = settings.get("resolution") or settings.get("quality") or settings.get("size") or "720p"
    aspect_ratio = settings.get("aspectRatio") or settings.get("size") or "16:9"
    motion = str(settings.get("motion") or "").strip().lower()
    payload = {
        "model": model,
        "prompt": append_video_motion_prompt(prompt, motion),
        "duration": max(2, min(duration, 25)),
    }
    if model.startswith("grok-imagine"):
        payload.update({"quality": resolution, "size": aspect_ratio})
    else:
        payload.update({"resolution": resolution, "aspect_ratio": aspect_ratio})
    if settings.get("negativePrompt"):
        payload["negative_prompt"] = settings["negativePrompt"]
    camera_control = settings.get("cameraControl")
    if isinstance(camera_control, dict) and camera_control:
        payload["camera_control"] = camera_control
    if reference_images:
        payload["image_urls"] = [upload_image_to_apimart(reference_images[0], api_key, base_url)]
    return payload


def append_video_motion_prompt(prompt: str, motion: str | None) -> str:
    motion_hints = {
        "dolly-in": "slow dolly-in camera movement",
        "pan-left": "gentle horizontal pan from left to right",
        "pull-back": "slow pull-back camera movement",
        "orbit": "subtle orbit camera move around the subject",
    }
    base_prompt = str(prompt or "").strip()
    hint = motion_hints.get(str(motion or "").strip().lower())
    if not hint:
        return base_prompt
    if hint.lower() in base_prompt.lower():
        return base_prompt
    separator = "\n\n" if base_prompt else ""
    return f"{base_prompt}{separator}Camera movement: {hint}."


def video_model_requires_reference(route_row: sqlite3.Row | None) -> bool:
    if not route_row:
        return False
    signature = " ".join(
        [
            str(route_row["route_code"] or ""),
            str(route_row["model_name"] or ""),
            str(route_row["id"] or ""),
        ]
    ).lower()
    return ("i2v" in signature) or ("image-to-video" in signature) or ("video-motion-v1" in signature)


def video_model_supported_durations(route_row: sqlite3.Row | None) -> list[int]:
    if not route_row:
        return [5, 8, 10]
    metadata = json_loads(route_row["metadata_json"], {})
    configured = metadata.get("supportedDurations")
    if isinstance(configured, list) and configured:
        return [int(value) for value in configured if isinstance(value, (int, float, str)) and str(value).isdigit()]

    signature = " ".join(
        [
            str(route_row["route_code"] or ""),
            str(route_row["model_name"] or ""),
            str(route_row["id"] or ""),
        ]
    ).lower()
    if "sora-2" in signature:
        return [4, 8, 12, 16, 20]
    if "grok-imagine" in signature:
        return [6, 8, 10, 12]
    return [5, 8, 10]


def video_duration_error(route_row: sqlite3.Row | None, duration_value) -> str | None:
    try:
        duration = int(duration_value or 0)
    except (TypeError, ValueError):
        return "Invalid video duration"

    signature = " ".join(
        [
            str(route_row["route_code"] or "") if route_row else "",
            str(route_row["model_name"] or "") if route_row else "",
            str(route_row["id"] or "") if route_row else "",
        ]
    ).lower()
    if "sora-2" in signature:
        allowed = video_model_supported_durations(route_row)
        if duration not in allowed:
            allowed_text = ", ".join(str(value) for value in allowed)
            return f"Sora 2 only supports durations: {allowed_text}"
        return None
    if "grok-imagine" in signature:
        if duration < 6 or duration > 30:
            return "Grok Imagine only supports 6-30 seconds"
        return None
    if duration < 2 or duration > 25:
        return "Current model only supports 2-25 seconds"
    return None


def normalized_image_quality(value: str | None) -> str:
    quality = str(value or "high").strip().lower()
    return QUALITY_ALIASES.get(quality, quality if quality in QUALITY_CREDIT_RULES else "high")


def official_image_resolution(value: str | None, settings: dict) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"1k", "2k", "4k"}:
        return raw

    for candidate in (
        str(settings.get("size") or "").strip(),
        str(settings.get("aspectRatio") or "").strip(),
    ):
        if candidate in APIMART_PIXEL_SIZE_TO_RESOLUTION:
            return APIMART_PIXEL_SIZE_TO_RESOLUTION[candidate]

    # Official docs treat quality and resolution as separate knobs.
    # If the caller did not explicitly ask for 2k/4k and did not provide
    # a larger pixel size, stay on the 1k tier to avoid silent upscaling.
    return "1k"


def official_image_size(settings: dict) -> str:
    candidates = [
        str(settings.get("aspectRatio") or "").strip(),
        str(settings.get("size") or "").strip(),
    ]
    for candidate in candidates:
        if candidate in APIMART_OFFICIAL_SIZES:
            return candidate
        mapped = APIMART_PIXEL_SIZE_TO_RATIO.get(candidate)
        if mapped:
            return mapped
    return "1:1"


def is_official_image_route(route_row: sqlite3.Row | None, model: str) -> bool:
    route_code = str(route_row["route_code"] if route_row else "").strip()
    return route_code == APIMART_OFFICIAL_ROUTE_CODE or model == APIMART_OFFICIAL_MODEL


def build_image_payload(
    route_row: sqlite3.Row | None,
    settings: dict,
    prompt: str,
    reference_images: list[dict],
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict:
    model = route_row["model_name"] if route_row else settings.get("model")
    model = model or APIMART_OFFICIAL_MODEL
    count = min(clamp_output_count(settings.get("count")), 4)
    requested_quality = settings.get("quality") or (route_row["quality"] if route_row else "high") or "high"
    quality = normalized_image_quality(requested_quality)
    if is_official_image_route(route_row, model):
        model = APIMART_OFFICIAL_MODEL
        size = official_image_size(settings)
        resolution = official_image_resolution(settings.get("resolution"), settings)
    else:
        resolution = {
            "low": "1k",
            "medium": "1k",
            "high": "2k",
        }.get(quality, "2k")
        size = settings.get("size") or settings.get("aspectRatio") or "1024x1024"
    payload = {
        "model": model,
        "prompt": prompt,
        "n": count,
        "size": size,
        "resolution": resolution,
        "quality": quality,
    }
    if reference_images:
        image_urls = []
        for item in reference_images[:10]:
            if item.get("url"):
                image_urls.append(str(item["url"]))
            elif item.get("dataUrl"):
                image_urls.append(upload_image_to_apimart(item, api_key, base_url))
        if image_urls:
            payload["image_urls"] = image_urls
    for key in ("outputFormat", "background", "moderation"):
        value = settings.get(key)
        if value:
            payload_key = {
                "outputFormat": "output_format",
                "background": "background",
                "moderation": "moderation",
            }[key]
            payload[payload_key] = value
    if settings.get("outputCompression"):
        try:
            payload["output_compression"] = int(settings.get("outputCompression"))
        except (TypeError, ValueError):
            pass
    return payload


def extract_apimart_task_payload(response: dict) -> dict:
    data = response.get("data")
    if isinstance(data, list) and data:
        item = data[0]
        return item if isinstance(item, dict) else {"value": item}
    if isinstance(data, dict):
        return data
    return response


def extract_image_result(response: dict) -> dict:
    data = extract_apimart_task_payload(response)
    result = data.get("result") if isinstance(data, dict) else {}
    result = result if isinstance(result, dict) else {}
    task_status = response.get("taskStatus") if isinstance(response, dict) and isinstance(response.get("taskStatus"), dict) else {}
    task_status_payload = extract_apimart_task_payload(task_status) if task_status else {}
    candidates = []
    sources = (
        result,
        data if isinstance(data, dict) else {},
        task_status_payload if isinstance(task_status_payload, dict) else {},
        task_status,
        response,
    )
    for source in sources:
        if not isinstance(source, dict):
            continue
        nested_result = source.get("result") if isinstance(source.get("result"), dict) else {}
        for candidate_source in (source, nested_result):
            if not isinstance(candidate_source, dict):
                continue
            images = candidate_source.get("images") or candidate_source.get("image_urls") or candidate_source.get("urls") or []
            if isinstance(images, list):
                candidates.extend(images)
            elif isinstance(images, str):
                candidates.append(images)
            direct = candidate_source.get("image_url") or candidate_source.get("url")
            if direct:
                candidates.append(direct)
    image_urls = []
    def append_image_url(value) -> None:
        if isinstance(value, list):
            for nested in value:
                append_image_url(nested)
        elif value:
            image_urls.append(str(value))

    for item in candidates:
        if isinstance(item, dict):
            url = item.get("url") or item.get("image_url") or item.get("b64_json") or item.get("data")
        else:
            url = item
        append_image_url(url)
    return {
        "imageUrls": image_urls,
        "imageUrl": image_urls[0] if image_urls else "",
    }


def map_apimart_status(status: str | None) -> str:
    normalized = (status or "").lower()
    if normalized in {"completed", "succeeded", "success"}:
        return "success"
    if normalized in {"failed", "error"}:
        return "failed"
    if normalized in {"cancelled", "canceled"}:
        return "cancelled"
    if normalized in {"processing", "running", "pending", "submitted", "queued"}:
        return "running"
    return "running"


def extract_video_result(response: dict) -> dict:
    data = extract_apimart_task_payload(response)
    result = data.get("result") if isinstance(data, dict) else {}
    result = result if isinstance(result, dict) else {}
    task_status = response.get("taskStatus") if isinstance(response, dict) and isinstance(response.get("taskStatus"), dict) else {}
    task_status_payload = extract_apimart_task_payload(task_status) if task_status else {}
    task_status_result = task_status_payload.get("result") if isinstance(task_status_payload, dict) and isinstance(task_status_payload.get("result"), dict) else {}
    videos = (
        result.get("videos")
        or (data.get("videos") if isinstance(data, dict) else [])
        or task_status_result.get("videos")
        or (task_status_payload.get("videos") if isinstance(task_status_payload, dict) else [])
        or task_status.get("videos")
    )
    video_url = ""
    if isinstance(videos, list) and videos:
        first = videos[0]
        if isinstance(first, dict):
            urls = first.get("url") or first.get("urls") or first.get("video_url")
            if isinstance(urls, list) and urls:
                video_url = str(urls[0])
            elif isinstance(urls, str):
                video_url = urls
        elif isinstance(first, str):
            video_url = first
    if not video_url:
        direct = (
            result.get("video_url")
            or result.get("url")
            or (data.get("video_url") if isinstance(data, dict) else "")
            or task_status_result.get("video_url")
            or task_status_result.get("url")
            or (task_status_payload.get("video_url") if isinstance(task_status_payload, dict) else "")
            or task_status.get("video_url")
            or task_status.get("url")
        )
        if isinstance(direct, list) and direct:
            video_url = str(direct[0])
        elif direct:
            video_url = str(direct)

    thumbnail_url = (
        result.get("thumbnail_url")
        or result.get("thumbnail")
        or (data.get("thumbnail_url") if isinstance(data, dict) else "")
        or task_status_result.get("thumbnail_url")
        or task_status_result.get("thumbnail")
        or (task_status_payload.get("thumbnail_url") if isinstance(task_status_payload, dict) else "")
        or task_status.get("thumbnail_url")
        or task_status.get("thumbnail")
    )
    return {
        "videoUrl": video_url,
        "thumbnailUrl": thumbnail_url or "",
    }


def refresh_image_job_from_provider(conn: sqlite3.Connection, job: sqlite3.Row) -> dict:
    response_json = json_loads(job["provider_response_json"], {})
    task_id = response_json.get("apimartTaskId") or response_json.get("taskId")
    if not task_id:
        image_result = extract_image_result(response_json) if response_json else {"imageUrl": "", "imageUrls": []}
        if image_result.get("imageUrl"):
            try:
                conn.execute("BEGIN")
                conn.execute(
                    """
                    UPDATE generation_jobs
                    SET status = 'success', provider_response_json = ?, finished_at = ?, updated_at = ?,
                        latency_ms = COALESCE(latency_ms, CAST((julianday(?) - julianday(queued_at)) * 86400000 AS INTEGER)),
                        error_message = NULL
                    WHERE id = ?
                    """,
                    (json_dumps({**response_json, **image_result}), now(), now(), now(), job["id"]),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            updated = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job["id"],)).fetchone()
            updated = ensure_generation_job_outputs_persisted(conn, updated) or updated
            return serialize_generation_job(conn, updated)

        try:
            conn.execute("BEGIN")
            conn.execute(
                """
                UPDATE generation_jobs
                SET status = 'failed', error_message = ?, finished_at = ?, updated_at = ?
                WHERE id = ? AND status IN ('queued', 'running')
                """,
                ("Provider task was not created; please submit a new generation. Charged credits will be refunded.", now(), now(), job["id"]),
            )
            refund_failed_generation_credits(conn, job["id"], reason="generation_failed_refund")
            audit(
                conn,
                "image.provider_missing_task",
                "generation_job",
                job["id"],
                {"providerResponseKeys": sorted(response_json.keys()) if response_json else []},
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        updated = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job["id"],)).fetchone()
        return serialize_generation_job(conn, updated)
    api_key = effective_apimart_api_key(conn)
    base_url = effective_apimart_base_url(conn)
    if not api_key:
        result = serialize_generation_job(conn, job)
        result["message"] = "Image job was submitted, but APIMart API key is not configured."
        return result
    if job["status"] not in {"queued", "running"}:
        return serialize_generation_job(conn, job)

    provider_status = call_json_api(
        "GET",
        f"{base_url}/v1/tasks/{task_id}?language=zh",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    task_payload = extract_apimart_task_payload(provider_status)
    local_status = map_apimart_status(task_payload.get("status") if isinstance(task_payload, dict) else "")
    progress = task_payload.get("progress") if isinstance(task_payload, dict) else None
    image_result = extract_image_result(provider_status)
    started_at = parse_iso_datetime(job["started_at"] or job["queued_at"] or job["created_at"])
    stale_after_seconds = IMAGE_JOB_STALE_MINUTES * 60
    if local_status == "running" and started_at:
        age_seconds = max(0, int((datetime.now(timezone.utc) - started_at).total_seconds()))
        if age_seconds >= stale_after_seconds and not image_result.get("imageUrl"):
            local_status = "failed"
            task_payload = {
                **(task_payload if isinstance(task_payload, dict) else {}),
                "message": f"Image job exceeded {IMAGE_JOB_STALE_MINUTES} minutes without a result and was marked failed."
            }
    merged_response = {
        **response_json,
        "taskStatus": provider_status,
        "progress": progress,
        **image_result,
    }

    fields = ["status = ?", "provider_response_json = ?", "updated_at = ?"]
    values = [local_status, json_dumps(merged_response), now()]
    if local_status == "running":
        fields.append("started_at = COALESCE(started_at, ?)")
        values.append(now())
    if local_status == "success":
        fields.extend(["finished_at = ?", "latency_ms = COALESCE(latency_ms, CAST((julianday(?) - julianday(queued_at)) * 86400000 AS INTEGER))", "error_message = NULL"])
        values.extend([now(), now()])
    if local_status in {"failed", "cancelled"}:
        error_message = task_payload.get("error") or task_payload.get("message") or "Image generation failed; credits were refunded."
        fields.extend(["finished_at = ?", "error_message = ?"])
        values.extend([now(), str(error_message)])
    values.append(job["id"])

    try:
        conn.execute("BEGIN")
        conn.execute(f"UPDATE generation_jobs SET {', '.join(fields)} WHERE id = ?", values)
        refund_result = {"amount": 0, "balance": 0, "refunded": False}
        if local_status in {"failed", "cancelled"}:
            refund_result = refund_failed_generation_credits(conn, job["id"], reason="generation_failed_refund")
        audit(
            conn,
            "image.provider_refresh",
            "generation_job",
            job["id"],
            {"status": local_status, "taskId": task_id, "refund": refund_result},
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    updated = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job["id"],)).fetchone()
    if local_status == "success":
        updated = ensure_generation_job_outputs_persisted(conn, updated) or updated
    return serialize_generation_job(conn, updated)


def calculate_video_credit_cost(route_row: sqlite3.Row | None, settings: dict) -> tuple[int, dict]:
    base_cost = int(route_row["credit_cost"] if route_row else 18)
    resolution = settings.get("resolution") or settings.get("quality") or "720p"
    aspect_ratio = settings.get("aspectRatio") or "16:9"
    try:
        duration = int(settings.get("duration") or 5)
    except (TypeError, ValueError):
        duration = 5
    duration = max(2, min(duration, 25))
    resolution_rule = VIDEO_RESOLUTION_CREDIT_RULES.get(resolution, VIDEO_RESOLUTION_CREDIT_RULES["720p"])
    duration_factor = max(1, duration / 5)
    single_cost = max(1, math.ceil(base_cost * float(resolution_rule["factor"]) * duration_factor))
    return single_cost, {
        "baseCost": base_cost,
        "singleCost": single_cost,
        "count": 1,
        "resolution": resolution,
        "resolutionLabel": resolution_rule["label"],
        "resolutionFactor": resolution_rule["factor"],
        "duration": duration,
        "durationFactor": duration_factor,
        "aspectRatio": aspect_ratio,
    }


def refresh_video_job_from_provider(conn: sqlite3.Connection, job: sqlite3.Row) -> dict:
    response_json = json_loads(job["provider_response_json"], {})
    task_id = response_json.get("apimartTaskId") or response_json.get("taskId")
    if not task_id:
        return serialize_generation_job(conn, job)

    api_key = effective_apimart_api_key(conn)
    base_url = effective_apimart_base_url(conn)
    if not api_key:
        result = serialize_generation_job(conn, job)
        result["message"] = "Video job was submitted, but APIMart API key is not configured."
        return result

    if job["status"] not in {"queued", "running"}:
        return serialize_generation_job(conn, job)

    provider_status = call_json_api(
        "GET",
        f"{base_url}/v1/tasks/{task_id}?language=zh",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    task_payload = extract_apimart_task_payload(provider_status)
    local_status = map_apimart_status(task_payload.get("status") if isinstance(task_payload, dict) else "")
    progress = task_payload.get("progress") if isinstance(task_payload, dict) else None
    result = extract_video_result(provider_status)
    started_at = parse_iso_datetime(job["started_at"] or job["queued_at"] or job["created_at"])
    stale_after_seconds = VIDEO_JOB_STALE_MINUTES * 60
    if local_status == "running" and started_at:
        age_seconds = max(0, int((datetime.now(timezone.utc) - started_at).total_seconds()))
        if age_seconds >= stale_after_seconds and not result.get("videoUrl"):
            local_status = "failed"
            task_payload = {
                **(task_payload if isinstance(task_payload, dict) else {}),
                "message": f"Video job exceeded {VIDEO_JOB_STALE_MINUTES} minutes without a result and was marked failed."
            }
    merged_response = {
        **response_json,
        "taskStatus": provider_status,
        "progress": progress,
        **result,
    }

    fields = ["status = ?", "provider_response_json = ?", "updated_at = ?"]
    values = [local_status, json_dumps(merged_response), now()]
    if local_status == "running":
        fields.append("started_at = COALESCE(started_at, ?)")
        values.append(now())
    if local_status == "success":
        fields.extend(["finished_at = ?", "latency_ms = COALESCE(latency_ms, CAST((julianday(?) - julianday(queued_at)) * 86400000 AS INTEGER))", "error_message = NULL"])
        values.extend([now(), now()])
    if local_status in {"failed", "cancelled"}:
        error_message = task_payload.get("error") or task_payload.get("message") or "Video generation failed; credits were refunded."
        fields.extend(["finished_at = ?", "error_message = ?"])
        values.extend([now(), str(error_message)])
    values.append(job["id"])

    try:
        conn.execute("BEGIN")
        conn.execute(f"UPDATE generation_jobs SET {', '.join(fields)} WHERE id = ?", values)
        refund_result = {"amount": 0, "balance": 0, "refunded": False}
        if local_status in {"failed", "cancelled"}:
            refund_result = refund_failed_generation_credits(conn, job["id"], reason="video_generation_failed_refund")
        audit(
            conn,
            "video.provider_refresh",
            "generation_job",
            job["id"],
            {"status": local_status, "taskId": task_id, "refund": refund_result},
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    updated = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job["id"],)).fetchone()
    if local_status == "success":
        updated = ensure_generation_job_outputs_persisted(conn, updated) or updated
    return serialize_generation_job(conn, updated)


def serialize_param(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "key": row["param_key"],
        "label": row["label"],
        "token": row["token"],
        "default": row["default_value"] or "",
        "type": row["param_type"] or "text",
        "required": bool(row["required"]),
        "options": json_loads(row["options_json"], []),
        "sortOrder": row["sort_order"],
    }


def load_template_params(conn: sqlite3.Connection, template_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT * FROM template_params
        WHERE template_id = ?
        ORDER BY sort_order, label
        """,
        (template_id,),
    ).fetchall()
    return [serialize_param(row) for row in rows]


def serialize_template(conn: sqlite3.Connection, row: sqlite3.Row, include_params: bool = False) -> dict:
    data = row_dict(row)
    metadata = json_loads(data.get("metadata_json"), {})
    source_case = metadata.get("sourceCase") or {}
    tags = metadata.get("tags") or []
    scenes = metadata.get("scenes") or []
    cover = asset_url(data.get("cover_asset_id"), data.get("cover_url"))
    if source_case:
        source_case = {**source_case, "image": cover}

    param_count = data.get("param_count")
    params = load_template_params(conn, data["id"]) if include_params else []
    if include_params:
        param_count = len(params)

    source_type = data.get("source_type") or "manual"
    category = data.get("category_value") or data.get("category_name") or ""

    return {
        "id": data["id"],
        "modality": metadata.get("modality") or data.get("route_modality") or "image",
        "templateKind": metadata.get("templateKind") or ("video" if (metadata.get("modality") or data.get("route_modality")) == "video" else "image"),
        "sourceTemplateId": data.get("source_template_id"),
        "caseId": data.get("case_id"),
        "title": data["title"],
        "description": data.get("description") or "",
        "category": category,
        "categoryLabel": data.get("category_label") or category or "Uncategorized",
        "cover": cover,
        "coverAssetId": data.get("cover_asset_id"),
        "coverUrl": data.get("cover_url") or "",
        "imageAlt": data.get("image_alt") or data["title"],
        "tags": tags,
        "scenes": scenes,
        "promoVideo": metadata.get("promoVideo") or "",
        "provider": metadata.get("provider") or "",
        "featured": bool(data.get("featured")),
        "status": data.get("status"),
        "enabled": data.get("status") == "enabled",
        "creditCost": data.get("credit_cost") or 5,
        "defaultQuality": data.get("default_quality") or "medium",
        "defaultAspectRatio": data.get("default_aspect_ratio") or "1:1",
        "defaultSize": data.get("default_size") or "1024x1024",
        "modelRoute": data.get("route_code") or "",
        "modelRouteName": data.get("route_name") or "",
        "allowReferenceImage": bool(data.get("allow_reference_image")),
        "sortScore": data.get("sort_score") or 0,
        "usageToday": data.get("usage_count") or 0,
        "usageCount": data.get("usage_count") or 0,
        "conversionRate": data.get("conversion_rate") or 0,
        "paramCount": param_count or 0,
        "params": params,
        "promptTemplate": data.get("prompt_template") or "",
        "source": "repo" if source_type == "repo" else "custom",
        "sourceLabel": data.get("source_label") or ("GitHub templates" if source_type == "repo" else "Manual"),
        "sourceUrl": data.get("source_url") or "",
        "originalUrl": data.get("original_url") or "",
        "sourceCase": source_case,
        "createdAt": data.get("created_at"),
        "updatedAt": data.get("updated_at"),
    }


TEMPLATE_SELECT = """
SELECT
    t.*,
    tc.source_value AS category_value,
    tc.name_zh AS category_label,
    ts.source_type AS source_type,
    mr.route_code AS route_code,
    mr.modality AS route_modality,
    mr.display_name AS route_name,
    COUNT(tp.id) AS param_count
FROM templates t
LEFT JOIN template_categories tc ON tc.id = t.category_id
LEFT JOIN template_sources ts ON ts.id = t.source_id
LEFT JOIN model_routes mr ON mr.id = t.default_model_route_id
LEFT JOIN template_params tp ON tp.template_id = t.id
"""


def query_templates(conn: sqlite3.Connection, query: dict, include_params: bool = False, include_private: bool = False) -> dict:
    where = []
    params: list = []
    if not include_private:
        where.append("(t.metadata_json IS NULL OR t.metadata_json NOT LIKE ?)")
        params.append(f"%{CUSTOM_TEMPLATE_METADATA_MARKER}%")

    status = query.get("status", ["enabled"])[0]
    if status and status != "all":
        where.append("t.status = ?")
        params.append(status)

    featured = query.get("featured", [""])[0]
    if featured in {"1", "true", "yes"}:
        where.append("t.featured = 1")

    modality = query.get("modality", query.get("type", [""]))[0]
    if modality in {"image", "video"}:
        where.append("COALESCE(mr.modality, 'image') = ?")
        params.append(modality)

    category = query.get("category", ["all"])[0]
    if category and category != "all":
        where.append("(tc.source_value = ? OR tc.slug = ? OR tc.id = ? OR tc.name_zh = ?)")
        params.extend([category, category, category, category])

    search = query.get("q", query.get("query", [""]))[0].strip()
    if search:
        like = f"%{search}%"
        where.append(
            "(t.title LIKE ? OR t.description LIKE ? OR t.prompt_template LIKE ? OR tc.name_zh LIKE ? OR tc.source_value LIKE ?)"
        )
        params.extend([like, like, like, like, like])

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    total_row = conn.execute(
        f"""
        SELECT COUNT(DISTINCT t.id) AS c
        FROM templates t
        LEFT JOIN template_categories tc ON tc.id = t.category_id
        LEFT JOIN template_sources ts ON ts.id = t.source_id
        LEFT JOIN model_routes mr ON mr.id = t.default_model_route_id
        {where_sql}
        """,
        params,
    ).fetchone()
    total = int(total_row["c"] if total_row else 0)

    page_size = int(query.get("page_size", query.get("limit", ["30"]))[0] or 30)
    page_size = max(1, min(page_size, 1000))
    page = max(1, int(query.get("page", ["1"])[0] or 1))
    offset = (page - 1) * page_size

    order = query.get("sort", ["featured"])[0]
    if order == "usage":
        order_sql = "ORDER BY t.usage_count DESC, t.sort_score DESC, t.updated_at DESC"
    elif order == "title":
        order_sql = "ORDER BY t.title COLLATE NOCASE ASC"
    elif order == "updated":
        order_sql = "ORDER BY t.created_at DESC, t.updated_at DESC"
    else:
        order_sql = "ORDER BY t.featured DESC, t.sort_score DESC, t.usage_count DESC, t.case_id DESC"

    rows = conn.execute(
        f"""
        {TEMPLATE_SELECT}
        {where_sql}
        GROUP BY t.id
        {order_sql}
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, offset],
    ).fetchall()

    return {
        "items": [serialize_template(conn, row, include_params=include_params) for row in rows],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


def get_template(conn: sqlite3.Connection, identifier: str, include_private: bool = False) -> dict | None:
    private_sql = "" if include_private else "AND (t.metadata_json IS NULL OR t.metadata_json NOT LIKE ?)"
    params = [identifier, identifier]
    if not include_private:
        params.append(f"%{CUSTOM_TEMPLATE_METADATA_MARKER}%")
    row = conn.execute(
        f"""
        {TEMPLATE_SELECT}
        WHERE (t.id = ? OR t.source_template_id = ?)
        {private_sql}
        GROUP BY t.id
        LIMIT 1
        """,
        params,
    ).fetchone()
    return serialize_template(conn, row, include_params=True) if row else None


def list_categories(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            tc.id, tc.source_value, tc.name_zh, tc.slug, tc.sort_order,
            COUNT(t.id) AS template_count
        FROM template_categories tc
        LEFT JOIN templates t ON t.category_id = tc.id AND t.status != 'archived'
        WHERE tc.is_active = 1
        GROUP BY tc.id
        ORDER BY tc.sort_order, tc.name_zh
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "value": row["source_value"],
            "label": row["name_zh"],
            "slug": row["slug"],
            "count": row["template_count"],
        }
        for row in rows
    ]


def app_settings(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("SELECT key, value, value_type FROM app_settings").fetchall()
    raw = {row["key"]: row for row in rows}

    def get(key: str, default=None):
        row = raw.get(key)
        if not row:
            return default
        if row["value_type"] == "number":
            try:
                return int(row["value"])
            except ValueError:
                return default
        if row["value_type"] == "boolean":
            return row["value"].lower() in {"1", "true", "yes", "on"}
        return row["value"]

    return {
        "siteName": get("site.name", "YCImage"),
        "homeTemplateLimit": get("site.home_template_limit", 30),
        "defaultModel": get("generation.default_model_route", DEFAULT_IMAGE_ROUTE_CODE),
        "defaultQuality": get("generation.default_quality", "medium"),
        "heroTemplateIds": json_loads(get("site.hero_template_ids", "[]"), []),
        "enablePublicLibrary": get("site.public_template_library", True),
        "requireReviewBeforeDownload": get("site.require_review_before_download", False),
        "payment": {
            "provider": PAYMENT_PROVIDER_ENV or get("payment.provider", "mpay"),
            "jeepayBaseUrl": get("payment.jeepay_base_url", JEEPAY_BASE_URL),
            "mchNo": get("payment.jeepay_mch_no", JEEPAY_MCH_NO),
            "appId": get("payment.jeepay_app_id", JEEPAY_APP_ID),
            "mpayBaseUrl": get("payment.mpay_base_url", MPAY_BASE_URL),
            "mpayPidConfigured": bool(get("payment.mpay_pid", MPAY_PID)),
            "returnUrl": MPAY_RETURN_URL or get("payment.return_url", "http://127.0.0.1:4178/account.html"),
            "notifyPath": get("payment.notify_path", "/api/pay/notify/mpay"),
            "enabledChannels": ["wechat", "alipay"],
        },
        "pricingRules": {
            "quality": QUALITY_CREDIT_RULES,
            "size": SIZE_CREDIT_RULES,
            "videoResolution": VIDEO_RESOLUTION_CREDIT_RULES,
        },
    }


def clamp_output_count(value) -> int:
    try:
        count = int(value or 1)
    except (TypeError, ValueError):
        count = 1
    return max(1, min(count, 8))


def calculate_credit_cost(route_row: sqlite3.Row | None, settings: dict) -> tuple[int, dict]:
    base_cost = int(route_row["credit_cost"] if route_row else 5)
    quality = normalized_image_quality(settings.get("quality") or "high")
    if is_official_image_route(route_row, route_row["model_name"] if route_row else APIMART_OFFICIAL_MODEL):
        size = official_image_size(settings)
    else:
        size = settings.get("size") or settings.get("aspectRatio") or "1024x1024"
    count = clamp_output_count(settings.get("count"))
    quality_rule = QUALITY_CREDIT_RULES.get(quality, QUALITY_CREDIT_RULES["high"])
    size_rule = SIZE_CREDIT_RULES.get(size, SIZE_CREDIT_RULES["1024x1024"])
    single_cost = max(1, math.ceil(base_cost * float(quality_rule["factor"]) * float(size_rule["factor"])))
    total_cost = single_cost * count
    return total_cost, {
        "baseCost": base_cost,
        "singleCost": single_cost,
        "count": count,
        "quality": quality,
        "qualityLabel": quality_rule["label"],
        "qualityFactor": quality_rule["factor"],
        "size": size,
        "sizeLabel": size_rule["label"],
        "sizeFactor": size_rule["factor"],
    }


def serialize_generation_job(conn: sqlite3.Connection, job: sqlite3.Row | None) -> dict:
    if not job:
        return {}
    response = json_loads(job["provider_response_json"], {})
    request_payload = json_loads(job["request_payload_json"], {})
    model = conn.execute(
        """
        SELECT mr.route_code, mr.display_name, mr.modality, mp.name AS provider_name
        FROM model_routes mr
        LEFT JOIN model_providers mp ON mp.id = mr.provider_id
        WHERE mr.id = ?
        """,
        (job["model_route_id"],),
    ).fetchone()
    modality = model["modality"] if model else ""
    persisted_urls = build_generation_job_asset_urls(conn, job["id"], modality or "image")
    video_result = extract_video_result(response) if response else {"videoUrl": "", "thumbnailUrl": ""}
    image_result = extract_image_result(response) if response else {"imageUrl": "", "imageUrls": []}
    return {
        "id": job["id"],
        "jobId": job["id"],
        "jobNo": job["job_no"],
        "status": job["status"],
        "templateId": job["template_id"] or "",
        "model": model["route_code"] if model else "",
        "modelName": model["display_name"] if model else "",
        "modality": modality,
        "provider": model["provider_name"] if model else "",
        "providerTaskId": response.get("apimartTaskId") or response.get("taskId") or "",
        "prompt": job["prompt_final"],
        "creditCost": job["credit_cost"],
        "quality": job["quality"],
        "aspectRatio": job["aspect_ratio"],
        "size": job["size"],
        "progress": response.get("progress"),
        "imageUrl": persisted_urls.get("imageUrl") or image_result.get("imageUrl") or response.get("imageUrl") or "",
        "imageUrls": persisted_urls.get("imageUrls") or image_result.get("imageUrls") or response.get("imageUrls") or [],
        "videoUrl": persisted_urls.get("videoUrl") or video_result.get("videoUrl") or response.get("videoUrl") or "",
        "thumbnailUrl": persisted_urls.get("thumbnailUrl") or video_result.get("thumbnailUrl") or response.get("thumbnailUrl") or "",
        "error": job["error_message"] or "",
        "request": request_payload,
        "createdAt": job["created_at"],
        "updatedAt": job["updated_at"],
        "finishedAt": job["finished_at"] or "",
    }


def ensure_credit_account(conn: sqlite3.Connection, user_id: str) -> sqlite3.Row:
    account = conn.execute("SELECT * FROM credit_accounts WHERE user_id = ?", (user_id,)).fetchone()
    if account:
        return account

    account_id = uid("ca")
    conn.execute(
        """
        INSERT INTO credit_accounts(id, user_id, balance, frozen_balance, lifetime_purchased, lifetime_granted, lifetime_spent, updated_at)
        VALUES (?, ?, 0, 0, 0, 0, 0, ?)
        """,
        (account_id, user_id, now()),
    )
    return conn.execute("SELECT * FROM credit_accounts WHERE id = ?", (account_id,)).fetchone()


def ensure_sufficient_credits(conn: sqlite3.Connection, user_id: str, amount: int) -> sqlite3.Row:
    account = ensure_credit_account(conn, user_id)
    balance = int(account["balance"] or 0)
    if balance < int(amount or 0):
        raise ValueError(f"Insufficient credits: current {balance}, required {int(amount or 0)}")
    return account


def grant_credit(
    conn: sqlite3.Connection,
    user_id: str,
    amount: int,
    reason: str,
    reference_type: str = "system",
    reference_id: str | None = None,
    operator_user_id: str | None = "user_admin",
    metadata: dict | None = None,
) -> dict:
    amount = int(amount or 0)
    account = ensure_credit_account(conn, user_id)
    if amount <= 0:
        return {"amount": 0, "balance": int(account["balance"] or 0)}
    if reference_type == "order" and reference_id:
        existing = conn.execute(
            """
            SELECT balance_after
            FROM credit_ledger
            WHERE reference_type = 'order'
              AND reference_id = ?
              AND direction = 'credit'
            LIMIT 1
            """,
            (reference_id,),
        ).fetchone()
        if existing:
            return {"amount": 0, "balance": int(existing["balance_after"] or account["balance"] or 0), "alreadyGranted": True}

    new_balance = int(account["balance"] or 0) + amount
    conn.execute(
        """
        UPDATE credit_accounts
        SET balance = ?, lifetime_granted = lifetime_granted + ?, updated_at = ?
        WHERE id = ?
        """,
        (new_balance, amount, now(), account["id"]),
    )
    conn.execute(
        """
        INSERT INTO credit_ledger(
            id, account_id, user_id, direction, amount, balance_after, reason,
            reference_type, reference_id, operator_user_id, metadata_json, created_at
        )
        VALUES (?, ?, ?, 'credit', ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uid("ledger"),
            account["id"],
            user_id,
            amount,
            new_balance,
            reason,
            reference_type,
            reference_id,
            operator_user_id,
            json_dumps(metadata or {}),
            now(),
        ),
    )
    return {"amount": amount, "balance": new_balance}


def normalize_mobile(value: str | None) -> str:
    raw = re.sub(r"\D+", "", str(value or ""))
    if raw.startswith("86") and len(raw) == 13:
        raw = raw[2:]
    if not re.fullmatch(r"1\d{10}", raw):
        raise ValueError("Invalid mobile number")
    return raw


def normalize_email(value: str | None) -> str:
    email = str(value or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Invalid email address")
    return email


def validate_password(value: str | None) -> str:
    password = str(value or "")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must include at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must include at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must include at least one digit")
    return password


def password_hash(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 160000)
    return digest.hex()


def store_password(conn: sqlite3.Connection, user_id: str, password: str, metadata: dict | None = None) -> None:
    salt = uuid.uuid4().hex + uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO auth_password_credentials(user_id, password_hash, password_salt, algorithm, metadata_json, created_at, updated_at)
        VALUES (?, ?, ?, 'pbkdf2_sha256', ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            password_hash = excluded.password_hash,
            password_salt = excluded.password_salt,
            algorithm = excluded.algorithm,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (user_id, password_hash(password, salt), salt, json_dumps(metadata or {}), now(), now()),
    )


def verify_password(conn: sqlite3.Connection, user_id: str, password: str) -> bool:
    row = conn.execute(
        "SELECT password_hash, password_salt FROM auth_password_credentials WHERE user_id = ? LIMIT 1",
        (user_id,),
    ).fetchone()
    if not row:
        return False
    expected = password_hash(str(password or ""), row["password_salt"])
    return hmac.compare_digest(expected, row["password_hash"])


def password_is_configured(conn: sqlite3.Connection, user_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM auth_password_credentials WHERE user_id = ? LIMIT 1",
        (user_id,),
    ).fetchone()
    return bool(row)


def password_metadata(conn: sqlite3.Connection, user_id: str) -> dict:
    row = conn.execute(
        "SELECT metadata_json FROM auth_password_credentials WHERE user_id = ? LIMIT 1",
        (user_id,),
    ).fetchone()
    return json_loads(row["metadata_json"], {}) if row else {}


def admin_password_must_change(conn: sqlite3.Connection, user_id: str = "user_admin") -> bool:
    metadata = password_metadata(conn, user_id)
    return bool(metadata.get("mustChange"))


def require_admin_reauth(
    conn: sqlite3.Connection,
    admin_user: sqlite3.Row | None,
    payload: dict,
    action: str,
    token_authenticated: bool = False,
) -> None:
    if not admin_user:
        raise RequestRejected(403, "Admin authentication required")
    if token_authenticated:
        return
    password = str(payload.get("adminPassword") or payload.get("currentPassword") or "").strip()
    if not password:
        raise RequestRejected(403, f"Admin password confirmation is required for {action}")
    if not password_is_configured(conn, admin_user["id"]) or not verify_password(conn, admin_user["id"], password):
        raise RequestRejected(403, "Admin password confirmation failed")
    for field in ("adminPassword", "currentPassword", "confirmPassword"):
        payload.pop(field, None)


def ensure_admin_password(conn: sqlite3.Connection) -> None:
    admin = conn.execute("SELECT id FROM users WHERE id = 'user_admin' LIMIT 1").fetchone()
    if not admin or password_is_configured(conn, "user_admin"):
        return
    bootstrap_password = YCIMAGE_ADMIN_PASSWORD or DEFAULT_ADMIN_PASSWORD
    validate_password(bootstrap_password)
    must_change = not YCIMAGE_ADMIN_PASSWORD and hmac.compare_digest(bootstrap_password, DEFAULT_ADMIN_PASSWORD)
    store_password(conn, "user_admin", bootstrap_password, {"bootstrapDefault": must_change, "mustChange": must_change})


def user_is_admin(conn: sqlite3.Connection, user_row: sqlite3.Row | None) -> bool:
    if not user_row:
        return False
    role = conn.execute("SELECT name, permissions_json FROM roles WHERE id = ? LIMIT 1", (user_row["role_id"],)).fetchone()
    if not role:
        return False
    permissions = json_loads(role["permissions_json"], [])
    return role["name"] in {"admin", "owner"} or user_has_permission(conn, user_row, "admin:*") or any(
        user_has_permission(conn, user_row, permission) for permission in ADMIN_CONSOLE_PERMISSIONS
    )


def user_permissions(conn: sqlite3.Connection, user_row: sqlite3.Row | None) -> set[str]:
    if not user_row:
        return set()
    role = conn.execute("SELECT name, permissions_json FROM roles WHERE id = ? LIMIT 1", (user_row["role_id"],)).fetchone()
    permissions = set(json_loads(role["permissions_json"], [])) if role else set()
    if role and role["name"] in {"admin", "owner"}:
        permissions.add("admin:*")
    return {str(item) for item in permissions}


def permission_matches(granted: str, required: str) -> bool:
    if granted in {"*", "admin:*", required}:
        return True
    if granted.endswith(":*"):
        prefix = granted.rsplit(":", 1)[0]
        return required.startswith(f"{prefix}:")
    return False


def user_has_permission(conn: sqlite3.Connection, user_row: sqlite3.Row | None, required: str) -> bool:
    return any(permission_matches(permission, required) for permission in user_permissions(conn, user_row))


def require_admin_permission(conn: sqlite3.Connection, admin_user: sqlite3.Row | None, required: str) -> None:
    if not admin_user or not user_has_permission(conn, admin_user, required):
        raise RequestRejected(403, f"Admin permission required: {required}")


def user_can_access_job(conn: sqlite3.Connection, user_row: sqlite3.Row | None, job: sqlite3.Row | None) -> bool:
    if not user_row or not job:
        return False
    return bool(job["user_id"] == user_row["id"] or user_is_admin(conn, user_row))


def asset_is_public(row: sqlite3.Row | None) -> bool:
    if not row:
        return False
    return row["asset_type"] in {"template_cover", "case_image", "other"} and not row["owner_user_id"]


def user_can_access_asset(conn: sqlite3.Connection, user_row: sqlite3.Row | None, asset: sqlite3.Row | None) -> bool:
    if not asset:
        return False
    if asset_is_public(asset):
        return True
    if not user_row:
        return False
    if user_is_admin(conn, user_row):
        return True
    if asset["owner_user_id"] == user_row["id"]:
        return True
    linked = conn.execute(
        """
        SELECT 1
        FROM generation_job_assets gja
        JOIN generation_jobs gj ON gj.id = gja.job_id
        WHERE gja.asset_id = ? AND gj.user_id = ?
        LIMIT 1
        """,
        (asset["id"], user_row["id"]),
    ).fetchone()
    return bool(linked)


def session_cookie_header(token: str, expires_at: str) -> str:
    max_age = max(60, SESSION_TTL_SECONDS)
    secure = "; Secure" if SECURE_COOKIES else ""
    return f"ycimage_session={token}; Path=/; Max-Age={max_age}; SameSite=Lax; HttpOnly{secure}"


def csrf_token_for_session(token: str) -> str:
    return hmac.new(secret_key_material().encode("utf-8"), str(token or "").encode("utf-8"), hashlib.sha256).hexdigest()


def csrf_cookie_header(token: str) -> str:
    max_age = max(60, SESSION_TTL_SECONDS)
    secure = "; Secure" if SECURE_COOKIES else ""
    return f"ycimage_csrf={token}; Path=/; Max-Age={max_age}; SameSite=Lax{secure}"


def auth_cookie_headers(session: dict) -> dict[str, str]:
    return {
        "Set-Cookie": session_cookie_header(session["token"], session["expiresAt"]),
        "Set-Cookie-CSRF": csrf_cookie_header(session["csrfToken"]),
    }


def expired_session_cookie_header() -> str:
    return "ycimage_session=; Path=/; Max-Age=0; SameSite=Lax; HttpOnly"


def expired_csrf_cookie_header() -> str:
    return "ycimage_csrf=; Path=/; Max-Age=0; SameSite=Lax"


def expired_auth_cookie_headers() -> dict[str, str]:
    return {
        "Set-Cookie": expired_session_cookie_header(),
        "Set-Cookie-CSRF": expired_csrf_cookie_header(),
    }


def create_referral_code(conn: sqlite3.Connection, user_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM referral_codes WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        return row
    invite_code = ""
    while True:
        invite_code = f"YC{uuid.uuid4().hex[:6].upper()}"
        exists = conn.execute("SELECT 1 FROM referral_codes WHERE invite_code = ?", (invite_code,)).fetchone()
        if not exists:
            break
    conn.execute(
        """
        INSERT INTO referral_codes(user_id, invite_code, invite_count, reward_credits, created_at)
        VALUES (?, ?, 0, 100, ?)
        """,
        (user_id, invite_code, now()),
    )
    return conn.execute("SELECT * FROM referral_codes WHERE user_id = ?", (user_id,)).fetchone()


def issue_session(conn: sqlite3.Connection, user_id: str) -> dict:
    token = session_token()
    csrf_token = csrf_token_for_session(token)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session_id = uid("sess")
    created = now()
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS)).replace(microsecond=0).isoformat()
    conn.execute(
        """
        INSERT INTO user_sessions(
            id, user_id, session_token_hash, ip_address, user_agent, expires_at, revoked_at, created_at
        )
        VALUES (?, ?, ?, '127.0.0.1', 'web-local', ?, NULL, ?)
        """,
        (session_id, user_id, token_hash, expires_at, created),
    )
    conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (created, created, user_id))
    return {"token": token, "csrfToken": csrf_token, "sessionId": session_id, "expiresAt": expires_at}


def revoke_all_sessions_for_user(conn: sqlite3.Connection, user_id: str) -> None:
    conn.execute(
        "UPDATE user_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
        (now(), user_id),
    )


def list_active_pricing_plans(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, code, name, plan_type, price_cents, currency, credits, period_days, features_json
        FROM pricing_plans
        WHERE status = 'active'
        ORDER BY sort_order, price_cents
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "code": row["code"],
            "name": row["name"],
            "planType": row["plan_type"],
            "price": round((row["price_cents"] or 0) / 100, 2),
            "priceCents": int(row["price_cents"] or 0),
            "currency": row["currency"] or "CNY",
            "credits": int(row["credits"] or 0),
            "periodDays": row["period_days"],
            "features": json_loads(row["features_json"], []),
        }
        for row in rows
    ]


def get_pricing_plan(conn: sqlite3.Connection, value: str | None) -> sqlite3.Row | None:
    if not value:
        return None
    value = PLAN_CODE_ALIASES.get(value, value)
    return conn.execute(
        """
        SELECT *
        FROM pricing_plans
        WHERE status = 'active' AND (id = ? OR code = ?)
        LIMIT 1
        """,
        (value, value),
    ).fetchone()


def calculate_order_entitlement(conn: sqlite3.Connection, user: sqlite3.Row, plan: sqlite3.Row) -> dict:
    amount_cents = int(plan["price_cents"] or 0)
    grant_credits = int(plan["credits"] or 0)
    entitlement = {
        "amountCents": amount_cents,
        "grantCredits": grant_credits,
        "upgrade": None,
    }
    if plan["plan_type"] != "subscription":
        return entitlement

    target_code = str(plan["code"] or "")
    current_code = str(user["membership_level"] or "free")
    current_rank = SUBSCRIPTION_PLAN_RANK.get(current_code, 0)
    target_rank = SUBSCRIPTION_PLAN_RANK.get(target_code, 0)
    if not current_rank or not target_rank or target_rank <= current_rank:
        return entitlement

    current_plan = get_pricing_plan(conn, current_code)
    if not current_plan or current_plan["plan_type"] != "subscription":
        return entitlement

    current_amount = int(current_plan["price_cents"] or 0)
    current_credits = int(current_plan["credits"] or 0)
    entitlement["amountCents"] = max(0, amount_cents - current_amount)
    entitlement["grantCredits"] = max(0, grant_credits - current_credits)
    entitlement["upgrade"] = {
        "from": current_code,
        "to": target_code,
        "fromName": current_plan["name"],
        "toName": plan["name"],
        "originalAmountCents": amount_cents,
        "deductedAmountCents": current_amount,
        "originalCredits": grant_credits,
        "deductedCredits": current_credits,
    }
    return entitlement


def resolve_payment_settings(conn: sqlite3.Connection) -> dict:
    settings = app_settings(conn).get("payment") or {}
    notify_secret = conn.execute("SELECT value FROM app_settings WHERE key = 'payment.notify_secret' LIMIT 1").fetchone()
    api_key = conn.execute("SELECT value FROM app_settings WHERE key = 'payment.jeepay_api_key' LIMIT 1").fetchone()
    provider_row = conn.execute("SELECT value FROM app_settings WHERE key = 'payment.provider' LIMIT 1").fetchone()
    mpay_pid = conn.execute("SELECT value FROM app_settings WHERE key = 'payment.mpay_pid' LIMIT 1").fetchone()
    mpay_key = conn.execute("SELECT value FROM app_settings WHERE key = 'payment.mpay_key' LIMIT 1").fetchone()
    mpay_base_url = (settings.get("mpayBaseUrl") or MPAY_BASE_URL).rstrip("/")
    resolved_mpay_pid = (mpay_pid["value"] if mpay_pid else "") or MPAY_PID
    resolved_mpay_key = app_setting_secret_value(mpay_key, MPAY_KEY)
    provider = PAYMENT_PROVIDER_ENV or (provider_row["value"] if provider_row else "") or ("mpay" if mpay_base_url and resolved_mpay_pid and resolved_mpay_key else "manual")
    return {
        "provider": provider,
        "jeepayBaseUrl": (settings.get("jeepayBaseUrl") or JEEPAY_BASE_URL).rstrip("/"),
        "mchNo": settings.get("mchNo") or JEEPAY_MCH_NO,
        "appId": settings.get("appId") or JEEPAY_APP_ID,
        "apiKey": app_setting_secret_value(api_key, JEEPAY_API_KEY),
        "notifySecret": app_setting_secret_value(notify_secret, JEEPAY_NOTIFY_SECRET),
        "mpayBaseUrl": mpay_base_url,
        "mpayPid": resolved_mpay_pid,
        "mpayKey": resolved_mpay_key,
        "mpayOldKeys": MPAY_OLD_KEYS,
        "mpaySubmitPath": MPAY_SUBMIT_PATH if MPAY_SUBMIT_PATH.startswith("/") else f"/{MPAY_SUBMIT_PATH}",
        "mpayMapiPath": MPAY_MAPI_PATH if MPAY_MAPI_PATH.startswith("/") else f"/{MPAY_MAPI_PATH}",
        "mpayNotifyUrl": MPAY_NOTIFY_URL,
        "returnUrl": MPAY_RETURN_URL or settings.get("returnUrl") or "http://127.0.0.1:4178/account.html",
        "notifyPath": "/api/pay/notify/mpay" if provider == "mpay" else (settings.get("notifyPath") or "/api/pay/notify/jeepay"),
        "serviceContact": settings.get("serviceContact") or "AI-CREATIVE-2026",
        "serviceQrcodeUrl": settings.get("serviceQrcodeUrl") or "",
        "enabledChannels": ["wechat", "alipay"],
    }


def public_payment_settings(conn: sqlite3.Connection) -> dict:
    config = resolve_payment_settings(conn)
    auto_enabled = config["provider"] == "mpay" and bool(config["mpayBaseUrl"] and config["mpayPid"] and config["mpayKey"])
    return {
        "provider": "mpay" if auto_enabled else "manual",
        "autoPayEnabled": auto_enabled,
        "enabledChannels": ["wechat", "alipay"],
    }


def payment_notify_url(config: dict) -> str:
    base = config.get("returnUrl") or "http://127.0.0.1:4178/account.html"
    parsed = urlparse(base)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "http://127.0.0.1:4178"
    path = config.get("notifyPath") or "/api/pay/notify/jeepay"
    return f"{origin}{path}"


def sign_jeepay_payload(payload: dict, api_key: str) -> str:
    parts = []
    for key in sorted(payload.keys()):
        value = payload[key]
        if value is None or value == "" or key == "sign":
            continue
        parts.append(f"{key}={value}")
    parts.append(f"key={api_key}")
    return hashlib.md5("&".join(parts).encode("utf-8")).hexdigest().upper()


def create_local_order(conn: sqlite3.Connection, user: sqlite3.Row, plan: sqlite3.Row, channel: str) -> dict:
    order_id = uid("order")
    order_no = f"ORD-{uuid.uuid4().hex[:10].upper()}"
    entitlement = calculate_order_entitlement(conn, user, plan)
    metadata = {
        "planCode": plan["code"],
        "planType": plan["plan_type"],
        "credits": entitlement["grantCredits"],
        "grantCredits": entitlement["grantCredits"],
        "targetCredits": int(plan["credits"] or 0),
        "originalAmountCents": int(plan["price_cents"] or 0),
        "periodDays": plan["period_days"],
    }
    if entitlement["upgrade"]:
        metadata["upgrade"] = entitlement["upgrade"]
    conn.execute(
        """
        INSERT INTO orders(
            id, order_no, user_id, organization_id, plan_id, amount_cents, currency,
            payment_channel, payment_provider_order_id, status, paid_at, refunded_at,
            notes, metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'pending', NULL, NULL, '', ?, ?, ?)
        """,
        (
            order_id,
            order_no,
            user["id"],
            user["organization_id"],
            plan["id"],
            entitlement["amountCents"],
            plan["currency"] or "CNY",
            channel,
            json_dumps(metadata),
            now(),
            now(),
        ),
    )
    return {"id": order_id, "orderNo": order_no, "plan": plan, "metadata": metadata, "amountCents": entitlement["amountCents"], "currency": plan["currency"] or "CNY"}


def apply_paid_order(conn: sqlite3.Connection, order_row: sqlite3.Row, provider_order_id: str | None = None, provider_payload: dict | None = None) -> dict:
    if order_row["status"] == "paid":
        return {"ok": True, "status": "paid", "alreadyPaid": True}
    if order_row["status"] != "pending":
        raise ValueError("Order is not payable")
    plan = conn.execute("SELECT * FROM pricing_plans WHERE id = ?", (order_row["plan_id"],)).fetchone()
    if not plan:
        raise ValueError("Order pricing plan does not exist")
    metadata = json_loads(order_row["metadata_json"], {})
    if provider_payload:
        metadata["providerPayload"] = safe_provider_payload(provider_payload)
    conn.execute(
        """
        UPDATE orders
        SET status = 'paid',
            payment_provider_order_id = COALESCE(?, payment_provider_order_id),
            paid_at = ?,
            metadata_json = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (provider_order_id, now(), json_dumps(metadata), now(), order_row["id"]),
    )
    credits = int(metadata.get("grantCredits") if metadata.get("grantCredits") is not None else metadata.get("credits") or plan["credits"] or 0)
    if credits > 0:
        grant_credit(conn, order_row["user_id"], credits, "purchase_payment", "order", order_row["id"], "user_admin", {"orderNo": order_row["order_no"], "planCode": plan["code"]})
        conn.execute(
            """
            UPDATE credit_accounts
            SET lifetime_purchased = lifetime_purchased + ?, updated_at = ?
            WHERE user_id = ?
            """,
            (credits, now(), order_row["user_id"]),
        )
    if plan["plan_type"] == "subscription":
        membership = {"monthly": "monthly", "creator": "creator", "studio": "studio"}.get(plan["code"], "monthly")
        conn.execute("UPDATE users SET membership_level = ?, updated_at = ? WHERE id = ?", (membership, now(), order_row["user_id"]))
    return {"ok": True, "status": "paid", "alreadyPaid": False}


def build_jeepay_payment(conn: sqlite3.Connection, order: dict, channel: str) -> dict:
    config = resolve_payment_settings(conn)
    if not config["jeepayBaseUrl"] or not config["mchNo"] or not config["appId"] or not config["apiKey"]:
        raise RuntimeError("Jeepay payment configuration is incomplete")
    jeepay_url = assert_public_http_url(f"{config['jeepayBaseUrl']}/api/pay/unifiedOrder")
    way_code = {"wechat": "WX_NATIVE", "alipay": "ALI_NATIVE"}.get(channel, "WX_NATIVE")
    payload = {
        "mchNo": config["mchNo"],
        "appId": config["appId"],
        "mchOrderNo": order["orderNo"],
        "wayCode": way_code,
        "amount": order["amountCents"],
        "currency": order["currency"],
        "clientIp": "127.0.0.1",
        "subject": f"YCImage {order['plan']['name']}",
        "body": f"{order['plan']['name']} / {int(order['metadata'].get('grantCredits') or order['plan']['credits'] or 0)} credits",
        "notifyUrl": payment_notify_url(config),
        "returnUrl": f"{config['returnUrl']}?orderNo={order['orderNo']}",
    }
    payload["sign"] = sign_jeepay_payload(payload, config["apiKey"])
    request = Request(
        jeepay_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with SAFE_URL_OPENER.open(request, timeout=20) as response:
            assert_public_http_url(response.geturl())
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Jeepay request failed: HTTP {exc.code} {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Unable to connect to Jeepay: {exc.reason}") from exc
    resp_code = str(data.get("code") or data.get("retCode") or "")
    if resp_code not in {"0", "SUCCESS", "200"}:
        raise RuntimeError(data.get("msg") or data.get("retMsg") or "Jeepay returned an error")
    body = data.get("data") or data.get("bizResponse") or {}
    pay_data = body.get("payData") or {}
    pay_url = pay_data.get("payUrl") or pay_data.get("codeUrl") or body.get("payUrl") or body.get("codeUrl") or ""
    return {
        "provider": "jeepay",
        "channel": channel,
        "state": "pending",
        "displayMode": "qrcode" if pay_url else "redirect",
        "payUrl": pay_url,
        "qrcodeUrl": pay_url,
        "providerOrderId": body.get("payOrderId") or body.get("payOrderNo") or "",
        "raw": data,
    }


def build_mpay_payment(conn: sqlite3.Connection, order: dict, channel: str) -> dict:
    config = resolve_payment_settings(conn)
    if not config["mpayBaseUrl"] or not config["mpayPid"] or not config["mpayKey"]:
        raise RuntimeError("MPAY payment configuration is incomplete")
    mpay_url = assert_public_http_url(f"{config['mpayBaseUrl']}{config['mpayMapiPath']}")

    return_url = config["returnUrl"]
    if "?" in return_url:
        return_url = f"{return_url}&orderNo={order['orderNo']}"
    else:
        return_url = f"{return_url}?orderNo={order['orderNo']}"
    notify_url = config["mpayNotifyUrl"] or payment_notify_url(config)
    params = {
        "pid": config["mpayPid"],
        "type": epay_channel(channel),
        "out_trade_no": order["orderNo"],
        "notify_url": notify_url,
        "return_url": return_url,
        "name": f"YCImage {order['plan']['name']}",
        "money": f"{int(order['amountCents'] or 0) / 100:.2f}",
        "param": order["id"],
        "sign_type": "MD5",
    }
    params["sign"] = epay_v1_sign(params, config["mpayKey"])
    mapi_path = config["mpayMapiPath"]
    request = Request(
        mpay_url,
        data=urlencode(params).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with SAFE_URL_OPENER.open(request, timeout=20) as response:
            assert_public_http_url(response.geturl())
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"MPAY request failed: HTTP {exc.code} {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Unable to connect to MPAY: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("MPAY response is not valid JSON") from exc

    if str(data.get("code") or "") not in {"1", "SUCCESS", "200"}:
        raise RuntimeError(str(data.get("msg") or data.get("message") or "MPAY returned an error"))

    qrcode_value = str(
        data.get("qrcode")
        or data.get("qr_code")
        or ""
    ).strip()
    pay_url = str(data.get("payurl") or data.get("pay_url") or "").strip()
    urlscheme = str(data.get("urlscheme") or data.get("scheme") or "").strip()
    provider_order_id = str(data.get("trade_no") or data.get("api_trade_no") or "").strip()

    if qrcode_value:
        return {
            "provider": "mpay",
            "channel": channel,
            "state": "pending",
            "displayMode": "qrcode",
            "qrcodeUrl": qrcode_value,
            "paymentUrl": pay_url or qrcode_value,
            "providerOrderId": provider_order_id,
            "raw": data,
            "message": "Scan the QR code with the selected payment app. Credits will be applied after payment succeeds.",
        }

    if pay_url:
        return {
            "provider": "mpay",
            "channel": channel,
            "state": "pending",
            "displayMode": "redirect",
            "paymentUrl": pay_url,
            "providerOrderId": provider_order_id,
            "raw": data,
            "message": "Open the payment link to complete payment. Credits will be applied after payment succeeds.",
        }

    if urlscheme:
        return {
            "provider": "mpay",
            "channel": channel,
            "state": "pending",
            "displayMode": "redirect",
            "paymentUrl": urlscheme,
            "providerOrderId": provider_order_id,
            "raw": data,
            "message": "Open the payment link to complete payment. Credits will be applied after payment succeeds.",
        }

    raise RuntimeError("MPAY did not return a usable QR code or payment link")


def mpay_query_order(config: dict, order_no: str) -> dict:
    if not order_no:
        raise ValueError("Missing order number")
    if not config["mpayBaseUrl"] or not config["mpayPid"] or not config["mpayKey"]:
        raise RuntimeError("MPAY payment configuration is incomplete")
    mpay_url = assert_public_http_url(f"{config['mpayBaseUrl']}/api")
    params = {
        "act": "order",
        "pid": config["mpayPid"],
        "key": config["mpayKey"],
        "out_trade_no": order_no,
    }
    request = Request(
        mpay_url,
        data=urlencode(params).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with SAFE_URL_OPENER.open(request, timeout=20) as response:
            assert_public_http_url(response.geturl())
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"MPAY query failed: HTTP {exc.code} {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Unable to connect to MPAY: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("MPAY query response is not valid JSON") from exc
    if str(data.get("code") or "") not in {"1", "SUCCESS", "200"}:
        raise RuntimeError(str(data.get("msg") or data.get("message") or "MPAY returned an error"))
    return data


def mpay_query_cashier_status(config: dict, provider_order_id: str) -> dict:
    if not provider_order_id:
        return {}
    base_url = str(config.get("mpayBaseUrl") or "").rstrip("/")
    if not base_url:
        raise RuntimeError("MPAY payment configuration is incomplete")
    status_url = assert_public_http_url(f"{base_url}/api/cashier/pay-order-status?pay_no={quote(provider_order_id)}")
    request = Request(
        status_url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with SAFE_URL_OPENER.open(request, timeout=20) as response:
            assert_public_http_url(response.geturl())
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"MPAY cashier status failed: HTTP {exc.code} {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Unable to connect to MPAY cashier status: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("MPAY cashier status response is not valid JSON") from exc
    if str(data.get("code") or "") not in {"1", "SUCCESS", "200"}:
        raise RuntimeError(str(data.get("msg") or data.get("message") or "MPAY cashier status returned an error"))
    payload = data.get("data")
    return payload if isinstance(payload, dict) else {}


def reconcile_mpay_order(conn: sqlite3.Connection, order_row: sqlite3.Row) -> sqlite3.Row:
    if not order_row:
        raise ValueError("Order not found")
    status = str(order_row["status"] or "").lower()
    if status == "paid":
        return order_row
    if status not in {"pending", "processing"}:
        return order_row
    config = resolve_payment_settings(conn)
    if config["provider"] != "mpay":
        return order_row
    payload = mpay_query_order(config, str(order_row["order_no"] or ""))
    provider_order_id = str(payload.get("trade_no") or payload.get("api_trade_no") or order_row["payment_provider_order_id"] or "").strip()
    remote_status = str(payload.get("status") or "").strip()
    cashier_payload = {}
    if provider_order_id:
        try:
            cashier_payload = mpay_query_cashier_status(config, provider_order_id)
        except Exception:
            cashier_payload = {}
    if cashier_payload:
        remote_status = str(cashier_payload.get("status") or remote_status).strip()
        payload = {**payload, "cashierStatus": cashier_payload}

    if remote_status == "1":
        try:
            conn.execute("BEGIN IMMEDIATE")
            locked_order = conn.execute("SELECT * FROM orders WHERE id = ? LIMIT 1", (order_row["id"],)).fetchone()
            if not locked_order:
                conn.execute("ROLLBACK")
                raise ValueError("Order not found")
            if str(locked_order["status"] or "").lower() == "pending":
                apply_paid_order(conn, locked_order, provider_order_id, payload)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    else:
        metadata = json_loads(order_row["metadata_json"], {})
        metadata["providerPayload"] = safe_provider_payload(payload)
        local_status = None
        note = ""
        if remote_status == "3":
            local_status = "failed"
            note = "MPAY marked the order as failed."
        elif remote_status in {"4", "closed"}:
            local_status = "cancelled"
            note = "MPAY marked the order as closed."
        elif remote_status in {"5", "timeout"}:
            local_status = "failed"
            note = "MPAY marked the order as timed out."

        if local_status:
            conn.execute(
                """
                UPDATE orders
                SET status = ?,
                    payment_provider_order_id = COALESCE(?, payment_provider_order_id),
                    notes = ?,
                    metadata_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (local_status, provider_order_id, note, json_dumps(metadata), now(), order_row["id"]),
            )
        elif provider_order_id:
            conn.execute(
                """
                UPDATE orders
                SET payment_provider_order_id = COALESCE(?, payment_provider_order_id),
                    metadata_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (provider_order_id, json_dumps(metadata), now(), order_row["id"]),
            )

    return conn.execute("SELECT * FROM orders WHERE id = ? LIMIT 1", (order_row["id"],)).fetchone()


def serialize_payment_order(conn: sqlite3.Connection, order_row: sqlite3.Row | None) -> dict:
    if not order_row:
        return {}
    plan = conn.execute("SELECT code, name, plan_type, credits, period_days FROM pricing_plans WHERE id = ?", (order_row["plan_id"],)).fetchone()
    metadata = json_loads(order_row["metadata_json"], {})
    public_metadata = redact_sensitive(metadata)
    return {
        "id": order_row["id"],
        "orderNo": order_row["order_no"],
        "status": order_row["status"],
        "amount": round((order_row["amount_cents"] or 0) / 100, 2),
        "amountCents": int(order_row["amount_cents"] or 0),
        "currency": order_row["currency"] or "CNY",
        "channel": order_row["payment_channel"] or "",
        "providerOrderId": order_row["payment_provider_order_id"] or "",
        "paidAt": order_row["paid_at"] or "",
        "createdAt": order_row["created_at"],
        "updatedAt": order_row["updated_at"],
        "plan": {
            "code": plan["code"] if plan else metadata.get("planCode", ""),
            "name": plan["name"] if plan else "",
            "type": plan["plan_type"] if plan else "",
            "credits": int(plan["credits"] or 0) if plan else int(metadata.get("targetCredits") or metadata.get("credits") or 0),
            "grantCredits": int(metadata.get("grantCredits") if metadata.get("grantCredits") is not None else metadata.get("credits") or 0),
            "periodDays": plan["period_days"] if plan else metadata.get("periodDays"),
        },
        "metadata": public_metadata,
    }


def get_user_by_session(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return conn.execute(
        """
        SELECT u.*
        FROM user_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.session_token_hash = ?
          AND s.revoked_at IS NULL
          AND s.expires_at > ?
        ORDER BY s.created_at DESC
        LIMIT 1
        """,
        (token_hash, now()),
    ).fetchone()


def serialize_account_summary(conn: sqlite3.Connection, user_row: sqlite3.Row | None, session: dict | None = None) -> dict:
    if not user_row:
        return {"authenticated": False}
    account = ensure_credit_account(conn, user_row["id"])
    profile = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_row["id"],)).fetchone()
    works_count = conn.execute("SELECT COUNT(*) AS c FROM generation_jobs WHERE user_id = ?", (user_row["id"],)).fetchone()["c"]
    collections_count = conn.execute("SELECT COUNT(*) AS c FROM collections WHERE user_id = ?", (user_row["id"],)).fetchone()["c"]
    custom_templates_count = count_custom_templates(conn, user_row["id"])
    invite = create_referral_code(conn, user_row["id"])
    password_configured = password_is_configured(conn, user_row["id"])
    public_session = {}
    if session:
        public_session = {
            "sessionId": session.get("sessionId", ""),
            "expiresAt": session.get("expiresAt", ""),
        }
    return {
        "authenticated": True,
        "session": public_session,
        "user": {
            "id": user_row["id"],
            "displayName": user_row["display_name"],
            "mobile": user_row["mobile"] or "",
            "email": user_row["email"] or "",
            "wechatOpenId": user_row["wechat_openid"] or "",
            "membershipLevel": user_row["membership_level"] or "free",
            "status": user_row["status"] or "active",
            "companyName": (profile["company_name"] if profile else "") or "",
            "passwordConfigured": password_configured,
        },
        "stats": {
            "credits": int(account["balance"] or 0),
            "works": int(works_count or 0),
            "favorites": int(collections_count or 0),
            "customTemplates": int(custom_templates_count or 0),
            "membership": user_row["membership_level"] or "free",
        },
        "invite": {
            "code": invite["invite_code"],
            "count": int(invite["invite_count"] or 0),
            "rewardCredits": int(invite["reward_credits"] or 100),
        },
    }


def list_account_ledger(conn: sqlite3.Connection, user_id: str, limit: int = 80) -> list[dict]:
    rows = conn.execute(
        """
        SELECT direction, amount, balance_after, reason, reference_type, reference_id, metadata_json, created_at
        FROM credit_ledger
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    labels = {
        "register_bonus": "Registration bonus",
        "invite_register_reward": "Invite reward",
        "generation_cost": "Generation cost",
        "generation_failed_refund": "Generation refund",
        "video_generation_failed_refund": "Video generation refund",
        "admin_grant": "Admin grant",
        "initial_seed": "Initial seed",
    }
    return [
        {
            "direction": row["direction"],
            "amount": int(row["amount"] or 0),
            "balanceAfter": int(row["balance_after"] or 0),
            "reason": row["reason"],
            "reasonLabel": labels.get(row["reason"], row["reason"]),
            "referenceType": row["reference_type"] or "",
            "referenceId": row["reference_id"] or "",
            "metadata": json_loads(row["metadata_json"], {}),
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def list_account_jobs(conn: sqlite3.Connection, user_id: str, limit: int = ACCOUNT_JOB_HISTORY_LIMIT) -> list[dict]:
    rows = conn.execute(
        """
        SELECT gj.*, t.title AS template_title, t.cover_asset_id, t.cover_url
        FROM generation_jobs gj
        LEFT JOIN templates t ON t.id = gj.template_id
        WHERE gj.user_id = ?
        ORDER BY gj.created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    jobs = []
    for row in rows:
        hydrated_row = row
        if row["status"] in {"queued", "running"}:
            model = conn.execute("SELECT modality FROM model_routes WHERE id = ?", (row["model_route_id"],)).fetchone()
            try:
                if model and model["modality"] == "video":
                    refresh_video_job_from_provider(conn, row)
                else:
                    refresh_image_job_from_provider(conn, row)
                hydrated_row = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (row["id"],)).fetchone() or row
            except RuntimeError:
                hydrated_row = row
        if hydrated_row["status"] == "success":
            hydrated_row = ensure_generation_job_outputs_persisted(conn, hydrated_row) or hydrated_row
        item = serialize_generation_job(conn, hydrated_row)
        item["templateTitle"] = row["template_title"] or "Prompt template"
        item["cover"] = (
            item.get("thumbnailUrl")
            or item.get("imageUrl")
            or ((item.get("imageUrls") or [""])[0])
            or asset_url(row["cover_asset_id"], row["cover_url"])
        )
        jobs.append(item)
    return jobs


def custom_template_limit(membership_level: str | None, user_id: str | None = None) -> int:
    return ACCOUNT_CUSTOM_TEMPLATE_LIMIT


def count_custom_templates(conn: sqlite3.Connection, user_id: str) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM templates
        WHERE created_by = ?
          AND metadata_json LIKE ?
          AND status != 'archived'
        """,
        (user_id, f"%{CUSTOM_TEMPLATE_METADATA_MARKER}%"),
    ).fetchone()
    return int(row["c"] if row else 0)


def list_account_custom_templates(conn: sqlite3.Connection, user_id: str, limit: int = ACCOUNT_CUSTOM_TEMPLATE_LIMIT) -> list[dict]:
    rows = conn.execute(
        f"""
        {TEMPLATE_SELECT}
        WHERE t.created_by = ?
          AND t.metadata_json LIKE ?
          AND t.status != 'archived'
        GROUP BY t.id
        ORDER BY t.created_at DESC
        LIMIT ?
        """,
        (user_id, f"%{CUSTOM_TEMPLATE_METADATA_MARKER}%", limit),
    ).fetchall()
    return [serialize_template(conn, row, include_params=True) for row in rows]


def get_account_custom_template_row(conn: sqlite3.Connection, user_id: str, template_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM templates
        WHERE id = ?
          AND created_by = ?
          AND metadata_json LIKE ?
          AND status != 'archived'
        LIMIT 1
        """,
        (template_id, user_id, f"%{CUSTOM_TEMPLATE_METADATA_MARKER}%"),
    ).fetchone()



def create_custom_template_from_payload(conn: sqlite3.Connection, user: sqlite3.Row, payload: dict) -> dict:
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("Prompt is required before saving a custom template")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError("Prompt is too long")

    current_count = count_custom_templates(conn, user["id"])
    limit = custom_template_limit(user["membership_level"], user["id"])
    if current_count >= limit:
        raise ValueError(f"Current account can save at most {limit} custom templates")

    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
    title = str(payload.get("title") or "").strip() or prompt[:28].strip() or "Custom image template"
    title = title[:120]
    description = (str(payload.get("description") or "").strip() or "Saved from custom image generation")[:300]
    route_id = model_route_id_from_value(conn, settings.get("model"))
    category_id = category_from_value(conn, payload.get("category") or "custom")
    cover_asset_id, cover_url = upsert_local_asset(
        conn,
        "template_cover",
        str(payload.get("coverUrl") or "").strip(),
        "asset_custom_template_cover",
    )
    template_id = uid("tpl_custom")
    created_at = now()
    metadata = {
        "tags": ["custom", "image-generation"],
        "scenes": ["custom-generation"],
        "sourceCase": {},
        "templateKind": "image",
        "modality": "image",
        "ownerUserId": user["id"],
        "savedFrom": "custom-image-workbench",
        "settings": settings,
    }

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
        VALUES (?, NULL, NULL, NULL, ?, ?, ?, ?, NULL, ?, ?, ?, ?, NULL, NULL,
                'enabled', 0, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?, ?)
        """,
        (
            template_id,
            category_id,
            title,
            description,
            prompt,
            cover_asset_id,
            cover_url,
            title,
            "User custom template",
            bounded_int(payload.get("creditCost"), "Template credit cost", 0, 500, 5),
            route_id,
            settings.get("quality") or "high",
            settings.get("aspectRatio") or settings.get("size") or "1:1",
            settings.get("size") or settings.get("aspectRatio") or "1024x1024",
            bool_int((settings.get("referenceMode") or "optional") != "text-only"),
            json_dumps(metadata),
            user["id"],
            created_at,
            created_at,
        ),
    )
    audit(
        conn,
        "custom_template.create",
        "template",
        template_id,
        {"userId": user["id"], "limit": limit, "count": current_count + 1},
    )
    template = get_template(conn, template_id, include_private=True)
    template["limit"] = limit
    template["count"] = current_count + 1
    return template


def update_custom_template_from_payload(
    conn: sqlite3.Connection,
    user: sqlite3.Row,
    template_id: str,
    payload: dict,
) -> dict:
    current = get_account_custom_template_row(conn, user["id"], template_id)
    if not current:
        raise ValueError("Template not found or already deleted")

    metadata = json_loads(current["metadata_json"], {})
    current_settings = metadata.get("settings") if isinstance(metadata.get("settings"), dict) else {}
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else current_settings
    prompt = str(payload.get("prompt") if payload.get("prompt") is not None else current["prompt_template"] or "").strip()
    if not prompt:
        raise ValueError("Prompt is required before updating a custom template")

    title = str(payload.get("title") if payload.get("title") is not None else current["title"] or "").strip()
    if not title:
        title = prompt[:28].strip() or (current["title"] or template_id)
    description = str(payload.get("description") if payload.get("description") is not None else current["description"] or "").strip()
    if not description:
        description = "Saved from custom image generation"
    cover_input = payload.get("coverUrl") if payload.get("coverUrl") is not None else current["cover_url"]
    cover_asset_id, cover_url = upsert_local_asset(
        conn,
        "template_cover",
        str(cover_input or "").strip(),
        "asset_custom_template_cover",
    )
    route_id = model_route_id_from_value(conn, settings.get("model")) or current["default_model_route_id"]
    metadata.update(
        {
            "templateKind": "image",
            "modality": "image",
            "ownerUserId": user["id"],
            "savedFrom": "custom-image-workbench",
            "settings": settings,
        }
    )
    conn.execute(
        """
        UPDATE templates
        SET title = ?,
            description = ?,
            prompt_template = ?,
            cover_asset_id = ?,
            cover_url = ?,
            image_alt = ?,
            credit_cost = ?,
            default_model_route_id = ?,
            default_quality = ?,
            default_aspect_ratio = ?,
            default_size = ?,
            allow_reference_image = ?,
            metadata_json = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            title,
            description,
            prompt,
            cover_asset_id,
            cover_url,
            title,
            bounded_int(payload.get("creditCost"), "Template credit cost", 0, 500, int(current["credit_cost"] or 5)),
            route_id,
            settings.get("quality") or current["default_quality"] or "high",
            settings.get("aspectRatio") or current["default_aspect_ratio"] or "1:1",
            settings.get("size") or current["default_size"] or "1024x1024",
            bool_int((settings.get("referenceMode") or "optional") != "text-only"),
            json_dumps(metadata),
            now(),
            template_id,
        ),
    )
    audit(conn, "custom_template.update", "template", template_id, {"userId": user["id"]})
    return get_template(conn, template_id, include_private=True) or {}


def archive_custom_template(conn: sqlite3.Connection, user: sqlite3.Row, template_id: str) -> int:
    current = get_account_custom_template_row(conn, user["id"], template_id)
    if not current:
        raise ValueError("Template not found or already deleted")
    conn.execute("UPDATE templates SET status = 'archived', updated_at = ? WHERE id = ?", (now(), template_id))
    audit(conn, "custom_template.delete", "template", template_id, {"userId": user["id"]})
    return count_custom_templates(conn, user["id"])


def list_account_orders(conn: sqlite3.Connection, user_id: str, limit: int = 60) -> list[dict]:
    rows = conn.execute(
        """
        SELECT o.*, pp.name AS plan_name, pp.credits AS plan_credits
        FROM orders o
        LEFT JOIN pricing_plans pp ON pp.id = o.plan_id
        WHERE o.user_id = ?
        ORDER BY o.created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [
        {
            "id": row["order_no"],
            "dbId": row["id"],
            "plan": row["plan_name"] or "Custom order",
            "credits": int(row["plan_credits"] or 0),
            "amount": round((row["amount_cents"] or 0) / 100, 2),
            "currency": row["currency"] or "CNY",
            "status": row["status"],
            "channel": row["payment_channel"],
            "paidAt": row["paid_at"] or "",
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def list_account_invites(conn: sqlite3.Connection, user_id: str, limit: int = 60) -> list[dict]:
    rows = conn.execute(
        """
        SELECT re.*, u.display_name AS invited_name, u.mobile AS invited_mobile, u.email AS invited_email
        FROM referral_events re
        LEFT JOIN users u ON u.id = re.invited_user_id
        WHERE re.inviter_user_id = ?
        ORDER BY re.created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "inviteCode": row["invite_code"],
            "rewardAmount": int(row["reward_amount"] or 0),
            "invitedUser": row["invited_name"] or row["invited_mobile"] or row["invited_email"] or "New user",
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def issue_mobile_code(conn: sqlite3.Connection, mobile: str, purpose: str = "register") -> dict:
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc).replace(microsecond=0).timestamp() + 300
    expires_iso = datetime.fromtimestamp(expires_at, timezone.utc).replace(microsecond=0).isoformat()
    conn.execute(
        """
        INSERT INTO auth_verification_codes(id, mobile, purpose, code, expires_at, consumed_at, created_at)
        VALUES (?, ?, ?, ?, ?, NULL, ?)
        """,
        (uid("sms"), mobile, purpose, mobile_code_digest(mobile, purpose, code), expires_iso, now()),
    )
    return {"mobile": mobile, "code": code, "expiresAt": expires_iso}


def verify_mobile_code(conn: sqlite3.Connection, mobile: str, code: str, purpose: str = "register") -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT *
        FROM auth_verification_codes
        WHERE mobile = ? AND purpose = ? AND consumed_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (mobile, purpose),
    ).fetchone()
    if not row:
        raise ValueError("Verification code is required")
    if row["expires_at"] <= now():
        raise ValueError("Verification code has expired")
    if not mobile_code_matches(str(row["code"]), mobile, purpose, str(code or "")):
        raise ValueError("Verification code is incorrect")
    conn.execute("UPDATE auth_verification_codes SET consumed_at = ? WHERE id = ?", (now(), row["id"]))
    return row


def charge_generation_credits(conn: sqlite3.Connection, user_id: str, job_id: str, amount: int, metadata: dict | None = None) -> dict:
    amount = int(amount or 0)
    if amount <= 0:
        return {"amount": 0, "balance": ensure_credit_account(conn, user_id)["balance"] or 0}

    totals = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN direction = 'debit' THEN amount ELSE 0 END), 0) AS debited,
            COALESCE(SUM(CASE WHEN direction = 'refund' THEN amount ELSE 0 END), 0) AS refunded
        FROM credit_ledger
        WHERE reference_type = 'generation_job' AND reference_id = ?
        """,
        (job_id,),
    ).fetchone()
    outstanding = max(0, int(totals["debited"] or 0) - int(totals["refunded"] or 0))
    if outstanding >= amount:
        account = ensure_credit_account(conn, user_id)
        return {"amount": 0, "balance": account["balance"] or 0}

    amount_to_charge = amount - outstanding
    account = ensure_credit_account(conn, user_id)
    current_balance = int(account["balance"] or 0)
    if current_balance < amount_to_charge:
        raise ValueError(f"Insufficient credits: current {current_balance}, required {amount_to_charge}")

    new_balance = current_balance - amount_to_charge
    updated = conn.execute(
        """
        UPDATE credit_accounts
        SET balance = balance - ?, lifetime_spent = lifetime_spent + ?, updated_at = ?
        WHERE id = ? AND balance >= ?
        """,
        (amount_to_charge, amount_to_charge, now(), account["id"], amount_to_charge),
    )
    if updated.rowcount != 1:
        current = conn.execute("SELECT balance FROM credit_accounts WHERE id = ?", (account["id"],)).fetchone()
        current_balance = int(current["balance"] or 0) if current else 0
        raise ValueError(f"Insufficient credits: current {current_balance}, required {amount_to_charge}")
    refreshed = conn.execute("SELECT balance FROM credit_accounts WHERE id = ?", (account["id"],)).fetchone()
    new_balance = int(refreshed["balance"] or 0) if refreshed else 0
    conn.execute(
        """
        INSERT INTO credit_ledger(
            id, account_id, user_id, direction, amount, balance_after, reason,
            reference_type, reference_id, operator_user_id, metadata_json, created_at
        )
        VALUES (?, ?, ?, 'debit', ?, ?, 'generation_cost', 'generation_job', ?, NULL, ?, ?)
        """,
        (uid("ledger"), account["id"], user_id, amount_to_charge, new_balance, job_id, json_dumps(metadata or {}), now()),
    )
    return {"amount": amount_to_charge, "balance": new_balance}


def refund_failed_generation_credits(
    conn: sqlite3.Connection,
    job_id: str,
    operator_user_id: str | None = "user_admin",
    reason: str = "generation_failed_refund",
) -> dict:
    job = conn.execute("SELECT id, user_id FROM generation_jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        return {"amount": 0, "balance": 0, "refunded": False}

    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN direction = 'debit' THEN amount ELSE 0 END), 0) AS debited,
            COALESCE(SUM(CASE WHEN direction = 'refund' THEN amount ELSE 0 END), 0) AS refunded
        FROM credit_ledger
        WHERE reference_type = 'generation_job' AND reference_id = ?
        """,
        (job_id,),
    ).fetchone()
    amount = max(0, int(row["debited"] or 0) - int(row["refunded"] or 0))
    account = ensure_credit_account(conn, job["user_id"])
    if amount <= 0:
        return {"amount": 0, "balance": account["balance"] or 0, "refunded": False}

    new_balance = int(account["balance"] or 0) + amount
    conn.execute(
        """
        UPDATE credit_accounts
        SET balance = ?, lifetime_spent = MAX(lifetime_spent - ?, 0), updated_at = ?
        WHERE id = ?
        """,
        (new_balance, amount, now(), account["id"]),
    )
    conn.execute(
        """
        INSERT INTO credit_ledger(
            id, account_id, user_id, direction, amount, balance_after, reason,
            reference_type, reference_id, operator_user_id, metadata_json, created_at
        )
        VALUES (?, ?, ?, 'refund', ?, ?, ?, 'generation_job', ?, ?, '{}', ?)
        """,
        (uid("ledger"), account["id"], job["user_id"], amount, new_balance, reason, job_id, operator_user_id, now()),
    )
    return {"amount": amount, "balance": new_balance, "refunded": True}



def list_models(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT mr.*, mp.name AS provider_name, mp.server_key_status
        FROM model_routes mr
        JOIN model_providers mp ON mp.id = mr.provider_id
        ORDER BY mr.priority DESC, mr.display_name
        """
    ).fetchall()
    generation_server_key_status = "configured" if effective_apimart_api_key(conn) else "not_configured"
    models = []
    for row in rows:
        sizes = json_loads(row["supported_sizes_json"], [])
        ratios = json_loads(row["supported_ratios_json"], [])
        metadata = json_loads(row["metadata_json"], {})
        modality = row["modality"] or "image"
        models.append(
            {
                "id": row["route_code"],
                "dbId": row["id"],
                "name": row["display_name"],
                "provider": row["provider_name"],
                "scenario": "Image generation" if modality == "image" else "Video generation",
                "quality": row["quality"],
                "size": " / ".join(str(item) for item in sizes),
                "sizes": sizes,
                "ratios": ratios,
                "defaultSize": row["default_size"],
                "defaultRatio": row["default_ratio"],
                "cost": row["credit_cost"],
                "successRate": row["success_rate"],
                "latency": f"{row['avg_latency_ms'] / 1000:.1f}s" if row["avg_latency_ms"] else "-",
                "enabled": row["status"] == "active",
                "serverKeyStatus": generation_server_key_status if modality in {"image", "video"} else row["server_key_status"],
                "retryLimit": row["retry_limit"],
                "modality": modality,
                "modelName": row["model_name"],
                "timeoutSeconds": row["timeout_seconds"],
                "supportedDurations": video_model_supported_durations(row) if modality == "video" else [],
                "metadata": redact_sensitive(metadata),
            }
        )
    return models


def normalize_model_route_payload(payload: dict, existing: sqlite3.Row | None = None) -> dict:
    route_code = str(payload.get("routeCode") or (existing["route_code"] if existing else "") or "").strip()
    if not route_code:
        route_code = f"custom-route-{uuid.uuid4().hex[:8]}"
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{2,80}", route_code):
        raise ValueError("Model route code contains invalid characters")

    name = str(payload.get("name") or payload.get("displayName") or (existing["display_name"] if existing else "") or "Custom model route").strip()
    if not name or len(name) > 120:
        raise ValueError("Model route name is required and must be 120 characters or less")

    model_name = str(payload.get("modelName") or (existing["model_name"] if existing else "") or route_code).strip()
    if not model_name or len(model_name) > 120:
        raise ValueError("Model name is required and must be 120 characters or less")

    modality = str(payload.get("modality") or (existing["modality"] if existing else "image")).strip().lower()
    if modality not in ALLOWED_MODEL_MODALITIES:
        raise ValueError("Model modality must be image or video")

    quality = str(payload.get("quality") or (existing["quality"] if existing else "high")).strip().lower()
    quality = QUALITY_ALIASES.get(quality, quality)
    if quality not in ALLOWED_MODEL_QUALITIES:
        raise ValueError("Model quality is invalid")

    sizes = payload.get("sizes")
    if sizes is None and existing:
        sizes = json_loads(existing["supported_sizes_json"], [])
    if isinstance(sizes, str):
        sizes = [item.strip() for item in sizes.split(",") if item.strip()]
    if not isinstance(sizes, list) or not sizes:
        sizes = ["1024x1024"] if modality == "image" else ["16:9"]
    sizes = [str(item).strip() for item in sizes if str(item).strip()][:30]

    ratios = payload.get("ratios")
    if ratios is None and existing:
        ratios = json_loads(existing["supported_ratios_json"], [])
    if isinstance(ratios, str):
        ratios = [item.strip() for item in ratios.split(",") if item.strip()]
    if not isinstance(ratios, list) or not ratios:
        ratios = ["1:1"] if modality == "image" else ["16:9"]
    ratios = [str(item).strip() for item in ratios if str(item).strip()][:30]

    default_size = str(payload.get("defaultSize") or (existing["default_size"] if existing else "") or sizes[0]).strip()
    default_ratio = str(payload.get("defaultRatio") or (existing["default_ratio"] if existing else "") or ratios[0]).strip()
    cost = int(payload.get("cost") if payload.get("cost") is not None else (existing["credit_cost"] if existing else 5))
    if cost < 0 or cost > 500:
        raise ValueError("Model credit cost must be between 0 and 500")
    timeout_seconds = int(payload.get("timeoutSeconds") or (existing["timeout_seconds"] if existing else IMAGE_GENERATION_TIMEOUT_FLOOR))
    timeout_seconds = max(30, min(timeout_seconds, 600))
    retry_limit = int(payload.get("retryLimit") if payload.get("retryLimit") is not None else (existing["retry_limit"] if existing else 2))
    retry_limit = max(0, min(retry_limit, 5))
    status = "active" if bool_int(payload.get("enabled", existing["status"] == "active" if existing else False)) else "disabled"
    return {
        "routeCode": route_code,
        "name": name,
        "modelName": model_name,
        "modality": modality,
        "quality": quality,
        "sizes": sizes,
        "ratios": ratios,
        "defaultSize": default_size,
        "defaultRatio": default_ratio,
        "cost": cost,
        "timeoutSeconds": timeout_seconds,
        "retryLimit": retry_limit,
        "status": status,
    }


def list_jobs(conn: sqlite3.Connection, limit: int = 160) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            gj.*, u.display_name AS user_name, t.title AS template_title, mr.route_code
        FROM generation_jobs gj
        LEFT JOIN users u ON u.id = gj.user_id
        LEFT JOIN templates t ON t.id = gj.template_id
        LEFT JOIN model_routes mr ON mr.id = gj.model_route_id
        ORDER BY gj.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "jobNo": row["job_no"],
            "user": row["user_name"] or "Unknown user",
            "templateId": row["template_id"] or "",
            "templateTitle": row["template_title"] or "Prompt template",
            "model": row["route_code"] or "",
            "status": row["status"],
            "latency": f"{row['latency_ms'] / 1000:.1f}s" if row["latency_ms"] else "-",
            "cost": row["credit_cost"],
            "createdAt": row["created_at"],
            "prompt": row["prompt_final"],
            "error": row["error_message"] or "",
        }
        for row in rows
    ]

def membership_label(value: str | None) -> str:
    return {
        "free": "Free",
        "monthly": "Monthly",
        "creator": "Creator",
        "studio": "Studio",
        "enterprise": "Enterprise",
        "credit_pack": "Credit pack",
    }.get(value or "", value or "User")


def list_users(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT * FROM v_user_account_summary
        ORDER BY generation_count DESC, balance DESC
        """
    ).fetchall()
    return [
        {
            "id": row["user_id"],
            "name": row["display_name"],
            "role": membership_label(row["membership_level"]),
            "membershipLevel": row["membership_level"],
            "credits": row["balance"] or 0,
            "monthlyJobs": row["generation_count"] or 0,
            "lastActive": "Recently active",
            "risk": "Low balance" if (row["balance"] or 0) < 30 else "Normal",
            "status": row["status"],
        }
        for row in rows
    ]


def list_orders(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT o.*, u.display_name AS user_name, pp.name AS plan_name
        FROM orders o
        LEFT JOIN users u ON u.id = o.user_id
        LEFT JOIN pricing_plans pp ON pp.id = o.plan_id
        ORDER BY o.created_at DESC
        LIMIT 80
        """
    ).fetchall()
    return [
        {
            "id": row["order_no"],
            "dbId": row["id"],
            "user": row["user_name"] or "Unknown user",
            "plan": row["plan_name"] or "Custom order",
            "amount": round((row["amount_cents"] or 0) / 100, 2),
            "status": row["status"],
            "channel": row["payment_channel"],
            "time": row["created_at"],
        }
        for row in rows
    ]

def list_reviews(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            ri.*, u.display_name AS user_name,
            gj.template_id,
            t.title AS template_title,
            t.cover_asset_id,
            t.cover_url
        FROM review_items ri
        LEFT JOIN users u ON u.id = ri.user_id
        LEFT JOIN generation_jobs gj ON gj.id = ri.subject_id
        LEFT JOIN templates t ON t.id = COALESCE(gj.template_id, ri.subject_id)
        ORDER BY ri.created_at DESC
        LIMIT 80
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["template_title"] or row["subject_id"],
            "image": asset_url(row["cover_asset_id"], row["cover_url"]),
            "user": row["user_name"] or "Unknown user",
            "risk": row["risk_level"],
            "reason": row["reason"],
            "status": row["status"],
            "prompt": row["subject_id"],
        }
        for row in rows
    ]

def list_activities(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT action, entity_type, entity_id, after_json, created_at
        FROM admin_audit_logs
        ORDER BY created_at DESC
        LIMIT 40
        """
    ).fetchall()
    return [
        {
            "type": row["entity_type"],
            "title": row["action"],
            "detail": row["entity_id"] or "System action",
            "time": row["created_at"],
        }
        for row in rows
    ]

def admin_state(conn: sqlite3.Connection, admin_user: sqlite3.Row | None = None) -> dict:
    can_templates = admin_user is None or user_has_permission(conn, admin_user, "templates:read")
    can_models = admin_user is None or user_has_permission(conn, admin_user, "models:read")
    can_jobs = admin_user is None or user_has_permission(conn, admin_user, "jobs:read")
    can_users = admin_user is None or user_has_permission(conn, admin_user, "users:read")
    can_orders = admin_user is None or user_has_permission(conn, admin_user, "orders:read")
    can_reviews = admin_user is None or user_has_permission(conn, admin_user, "reviews:write")
    can_settings = admin_user is None or user_has_permission(conn, admin_user, "settings:write")
    can_api = admin_user is None or user_has_permission(conn, admin_user, "payments:config")
    can_security = admin_user is None or user_has_permission(conn, admin_user, "admin:*")
    templates = (
        query_templates(
            conn,
            {"status": ["all"], "page_size": ["1000"], "page": ["1"], "sort": ["featured"]},
            include_params=True,
            include_private=True,
        )["items"]
        if can_templates
        else []
    )
    settings = app_settings(conn)
    apimart_provider = conn.execute("SELECT * FROM model_providers WHERE id = 'provider_apimart'").fetchone()
    if not apimart_provider:
        apimart_provider = conn.execute("SELECT * FROM model_providers WHERE id = 'provider_openai_compatible'").fetchone()
    apimart_metadata = json_loads(apimart_provider["metadata_json"], {}) if apimart_provider else {}
    key_configured = bool(APIMART_API_KEY or metadata_secret_configured(apimart_metadata, "apiKey"))
    apimart_base_url = effective_apimart_base_url(conn)
    connection_test = apimart_metadata.get("lastConnectionTest") if isinstance(apimart_metadata.get("lastConnectionTest"), dict) else {}
    state_user_id = admin_user["id"] if admin_user else "user_admin"
    state_user = conn.execute("SELECT id, email, mobile, display_name FROM users WHERE id = ? LIMIT 1", (state_user_id,)).fetchone()
    admin_password_configured = password_is_configured(conn, state_user_id)
    admin_must_change = admin_password_must_change(conn, state_user_id)
    return {
        "permissions": sorted(user_permissions(conn, admin_user)) if admin_user else ["admin:*"],
        "settings": settings if can_settings or can_templates else {},
        "api": {
            "endpoint": apimart_metadata.get("apiEndpoint") or "/api/generate-image",
            "balanceEndpoint": apimart_metadata.get("balanceEndpoint") or "/api/admin/model-balance",
            "serverKeyStatus": ("env_configured" if APIMART_API_KEY else ("configured" if key_configured else "not_configured")) if can_api else "restricted",
            "apimartBaseUrl": apimart_base_url if can_api else "",
            "apimartKeyConfigured": key_configured if can_api else False,
            "keySource": ("environment" if APIMART_API_KEY else ("database" if metadata_secret_configured(apimart_metadata, "apiKey") else "missing")) if can_api else "restricted",
            "connectionTest": connection_test if can_api else {},
            "retryLimit": 2,
        },
        "security": {
            "adminUserId": state_user["id"] if can_security and state_user else "restricted",
            "adminEmail": state_user["email"] if can_security and state_user else "restricted",
            "adminMobile": state_user["mobile"] if can_security and state_user else "",
            "adminName": state_user["display_name"] if can_security and state_user else "Admin",
            "adminPasswordConfigured": admin_password_configured,
            "adminPasswordMustChange": admin_must_change,
        },
        "templates": templates,
        "categories": list_categories(conn),
        "models": list_models(conn) if can_models else [],
        "jobs": list_jobs(conn) if can_jobs else [],
        "users": list_users(conn) if can_users else [],
        "orders": list_orders(conn) if can_orders else [],
        "reviewItems": list_reviews(conn) if can_reviews else [],
        "activities": list_activities(conn) if can_security else [],
        "stats": {
            "images": conn.execute("SELECT COUNT(*) AS c FROM asset_blobs").fetchone()["c"],
            "assets": conn.execute("SELECT COUNT(*) AS c FROM assets").fetchone()["c"],
        },
    }



def upsert_template_from_payload(conn: sqlite3.Connection, payload: dict) -> dict:
    source_id = "src_manual_admin"
    conn.execute(
        """
        INSERT INTO template_sources(id, name, source_type, repository_url, license, synced_at, metadata_json)
        VALUES (?, ?, 'manual', NULL, NULL, ?, '{}')
        ON CONFLICT(id) DO UPDATE SET name = excluded.name, synced_at = excluded.synced_at
        """,
        (source_id, "Manual admin templates", now()),
    )

    template_id = str(payload.get("id") or f"tpl_manual_{uuid.uuid4().hex[:12]}").strip()
    existing = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    category_id = category_from_value(conn, payload.get("category"))
    route_id = model_route_id_from_value(conn, payload.get("modelRoute") or payload.get("defaultModelRoute"))
    cover_value = payload.get("cover") or payload.get("coverUrl")
    cover_asset_id, cover_public = upsert_local_asset(conn, "template_cover", cover_value, "asset_manual_cover")
    if not cover_public:
        cover_public = ""

    params = payload.get("params") or []
    if isinstance(params, str):
        params = [item.strip() for item in params.split(",") if item.strip()]
    normalized_params = []
    for index, item in enumerate(params[:30]):
        if isinstance(item, str):
            raw = item.strip()[:120]
            if not raw:
                continue
            label = raw
            options = []
            if "=" in raw:
                label, option_text = raw.split("=", 1)
                label = label.strip()[:80] or f"Field {index + 1}"
                options = [option.strip()[:80] for option in option_text.split("|") if option.strip()][:30]
            key = slugify(label).replace("-", "_")
            normalized_params.append(
                {
                    "key": key,
                    "label": label,
                    "default": options[0] if options else "",
                    "token": None,
                    "type": "select" if options else "text",
                    "options": options,
                }
            )
        elif isinstance(item, dict):
            label = str(item.get("label") or item.get("key") or f"Field {index + 1}").strip()[:80]
            key = str(item.get("key") or slugify(label).replace("-", "_")).strip()[:80]
            options = item.get("options") or []
            if isinstance(options, str):
                options = [option.strip()[:80] for option in options.split("|") if option.strip()]
            if not isinstance(options, list):
                options = []
            param_type = str(item.get("type") or ("select" if options else "text"))
            if param_type not in {"text", "select", "number", "textarea", "chinese-slot"}:
                param_type = "select" if options else "text"
            normalized_params.append(
                {
                    "key": key or f"field_{index + 1}",
                    "label": label or f"Field {index + 1}",
                    "default": str(item.get("default") or "")[:200],
                    "token": item.get("token"),
                    "type": param_type,
                    "options": options[:30],
                }
            )

    status = validate_template_status(payload.get("status") or ("enabled" if payload.get("enabled", True) else "hidden"))
    featured = bool_int(payload.get("featured", False))
    metadata = {"tags": payload.get("tags") or [], "scenes": payload.get("scenes") or [], "sourceCase": {}}
    prompt = str(payload.get("promptTemplate") or payload.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("Template prompt is required")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError("Template prompt is too long")
    title = str(payload.get("title") or "Untitled template").strip()[:120] or "Untitled template"
    credit_cost = bounded_int(payload.get("creditCost"), "Template credit cost", 0, 500, 5)
    sort_score = bounded_float(payload.get("sortScore"), "Template sort score", -10000, 10000, 500 if featured else 0)
    usage_count = bounded_int(payload.get("usageToday") or payload.get("usageCount"), "Template usage count", 0, 10_000_000, 0)
    conversion_rate = bounded_float(payload.get("conversionRate"), "Template conversion rate", 0, 1, 0)

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
        VALUES (?, ?, NULL, NULL, ?, ?, ?, ?, NULL, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, 'user_admin', ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            category_id = excluded.category_id,
            title = excluded.title,
            description = excluded.description,
            prompt_template = excluded.prompt_template,
            cover_asset_id = excluded.cover_asset_id,
            cover_url = excluded.cover_url,
            image_alt = excluded.image_alt,
            status = excluded.status,
            featured = excluded.featured,
            credit_cost = excluded.credit_cost,
            default_model_route_id = excluded.default_model_route_id,
            default_quality = excluded.default_quality,
            default_aspect_ratio = excluded.default_aspect_ratio,
            default_size = excluded.default_size,
            allow_reference_image = excluded.allow_reference_image,
            sort_score = excluded.sort_score,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (
            template_id,
            source_id if not existing else existing["source_id"] or source_id,
            category_id,
            title,
            str(payload.get("description") or "")[:500],
            prompt,
            cover_asset_id,
            cover_public,
            str(payload.get("imageAlt") or title)[:160],
            "Manual admin template",
            status,
            featured,
            credit_cost,
            route_id,
            str(payload.get("defaultQuality") or "high"),
            str(payload.get("defaultAspectRatio") or "1:1"),
            str(payload.get("defaultSize") or "1024x1024"),
            bool_int(payload.get("allowReferenceImage", True)),
            sort_score,
            usage_count,
            conversion_rate,
            json_dumps(metadata),
            now(),
            now(),
        ),
    )

    conn.execute("DELETE FROM template_params WHERE template_id = ?", (template_id,))
    for index, param in enumerate(normalized_params):
        conn.execute(
            """
            INSERT INTO template_params(
                id, template_id, param_key, label, token, default_value, param_type, required, options_json, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                f"tparam_{template_id}_{index + 1}",
                template_id,
                param["key"],
                param["label"],
                param["token"],
                param["default"],
                param["type"],
                json_dumps(param.get("options") or []),
                index,
            ),
        )

    audit(conn, "template.save", "template", template_id, {"title": title, "featured": featured})
    return get_template(conn, template_id, include_private=True) or {}


def update_settings(conn: sqlite3.Connection, payload: dict) -> dict:
    updates: list[tuple[str, str, str, str]] = []
    if payload.get("siteName") is not None:
        site_name = str(payload.get("siteName") or "").strip()
        if not site_name or len(site_name) > 80:
            raise ValueError("Site name is required and must be 80 characters or less")
        updates.append(("site.name", site_name, "string", "Site name"))

    if payload.get("homeTemplateLimit") is not None:
        try:
            home_limit = int(payload.get("homeTemplateLimit"))
        except (TypeError, ValueError) as error:
            raise ValueError("Home template limit must be a number") from error
        home_limit = max(3, min(home_limit, 48))
        updates.append(("site.home_template_limit", str(home_limit), "number", "Home template limit"))

    if payload.get("defaultModel") is not None:
        default_model = str(payload.get("defaultModel") or "").strip()
        route_id = model_route_id_from_value(conn, default_model)
        if not route_id:
            raise ValueError("Default model route does not exist")
        route_code = route_code_from_id(conn, route_id)
        updates.append(("generation.default_model_route", route_code, "string", "Default model route"))

    if payload.get("defaultQuality") is not None:
        default_quality = str(payload.get("defaultQuality") or "medium").strip().lower()
        default_quality = QUALITY_ALIASES.get(default_quality, default_quality)
        if default_quality not in ALLOWED_MODEL_QUALITIES:
            raise ValueError("Default quality is invalid")
        updates.append(("generation.default_quality", default_quality, "string", "Default image quality"))

    if payload.get("heroTemplateIds") is not None:
        hero_ids = payload.get("heroTemplateIds")
        if not isinstance(hero_ids, list):
            raise ValueError("Hero template IDs must be a list")
        clean_ids: list[str] = []
        for item in hero_ids[:6]:
            template_id = str(item or "").strip()
            if not template_id:
                continue
            template = get_template(conn, template_id, include_private=False)
            if not template:
                raise ValueError("Hero template does not exist or is not public")
            clean_ids.append(template["id"])
        updates.append(("site.hero_template_ids", json_dumps(clean_ids), "string", "Hero template ids"))

    if payload.get("enablePublicLibrary") is not None:
        updates.append(("site.public_template_library", "true" if bool_int(payload.get("enablePublicLibrary")) else "false", "boolean", "Enable public template library"))

    if payload.get("requireReviewBeforeDownload") is not None:
        updates.append(
            (
                "site.require_review_before_download",
                "true" if bool_int(payload.get("requireReviewBeforeDownload")) else "false",
                "boolean",
                "Require review before download",
            )
        )

    if payload.get("paymentServiceContact") is not None:
        contact = str(payload.get("paymentServiceContact") or "").strip()[:120]
        updates.append(("payment.service_contact", contact, "string", "Payment service contact"))

    if payload.get("paymentServiceQrcodeUrl") is not None:
        qrcode = str(payload.get("paymentServiceQrcodeUrl") or "").strip()
        if qrcode:
            if qrcode.startswith("/api/assets/"):
                pass
            elif qrcode.startswith("assets/") or qrcode.startswith("webapp/assets/"):
                pass
            elif qrcode.startswith("data:image/"):
                raise ValueError("Payment QR code must be uploaded as an asset before saving")
            else:
                try:
                    assert_public_http_url(qrcode)
                except RuntimeError as error:
                    raise ValueError("Payment QR code URL must be a public http(s) URL or local asset") from error
        updates.append(("payment.service_qrcode_url", qrcode, "string", "Payment service QR code URL"))

    for key, value, value_type, description in updates:
        conn.execute(
            """
            INSERT INTO app_settings(key, value, value_type, description, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                value_type = excluded.value_type,
                description = excluded.description,
                updated_at = excluded.updated_at
            """,
            (key, value, value_type, description, now()),
        )
    audit(conn, "settings.update", "app_settings", "site", redact_sensitive(payload))
    return app_settings(conn)


class RequestRejected(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class AppHandler(BaseHTTPRequestHandler):
    server_version = "AIWorkshopHTTP/1.0"

    def do_OPTIONS(self) -> None:
        cors_origin = self.cors_origin()
        if self.headers.get("Origin") and not cors_origin:
            self.send_response(403)
            self.send_security_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(204)
        self.send_security_headers()
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Admin-Token, X-Requested-With, X-CSRF-Token")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self.enforce_rate_limit("GET", parsed.path)
                self.handle_api("GET", parsed.path, parse_qs(parsed.query))
            else:
                self.serve_static(parsed.path)
        except RequestRejected as error:
            self.send_json(error.status, public_safe_error(error.message))
        except Exception as error:  # noqa: BLE001
            error_id = uid("err")
            sys.stderr.write(f"Unhandled GET error {error_id}: {type(error).__name__}\n")
            self.send_json(500, public_safe_error("Internal server error"))

    def do_POST(self) -> None:
        self.handle_write("POST")

    def do_PATCH(self) -> None:
        self.handle_write("PATCH")

    def do_PUT(self) -> None:
        self.handle_write("PUT")

    def do_DELETE(self) -> None:
        self.handle_write("DELETE")

    def handle_write(self, method: str) -> None:
        try:
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/api/"):
                self.send_json(404, {"error": "Not found"})
                return
            self.enforce_write_request(method, parsed.path)
            self.enforce_rate_limit(method, parsed.path)
            self.handle_api(method, parsed.path, parse_qs(parsed.query), self.read_json())
        except RequestRejected as error:
            self.send_json(error.status, public_safe_error(error.message))
        except json.JSONDecodeError:
            self.send_json(400, public_safe_error("Malformed JSON body"))
        except UnicodeDecodeError:
            self.send_json(400, public_safe_error("Request body must be UTF-8"))
        except Exception as error:  # noqa: BLE001
            error_id = uid("err")
            sys.stderr.write(f"Unhandled {method} error {error_id}: {type(error).__name__}\n")
            self.send_json(500, public_safe_error("Internal server error"))

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError as error:
            raise RequestRejected(400, "Invalid Content-Length") from error
        if length <= 0:
            return {}
        content_type = (self.headers.get("Content-Type") or "").lower()
        max_body = MAX_FORM_BODY_BYTES if "application/x-www-form-urlencoded" in content_type else MAX_JSON_BODY_BYTES
        if length > max_body:
            self.rfile.read(length)
            raise RequestRejected(413, "Request body is too large")
        if "application/json" not in content_type and "application/x-www-form-urlencoded" not in content_type:
            raise RequestRejected(415, "Unsupported Content-Type")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        text = raw.decode("utf-8")
        if "application/x-www-form-urlencoded" in content_type:
            return flatten_query(parse_qs(text, keep_blank_values=True))
        return json.loads(text)

    def send_security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "media-src 'self' data: blob: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'",
        )
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        if SECURE_COOKIES or (self.headers.get("X-Forwarded-Proto") or "").lower() == "https":
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    def enforce_write_request(self, method: str, path: str) -> None:
        if method not in {"POST", "PATCH", "PUT", "DELETE"}:
            return
        origin = self.headers.get("Origin")
        if origin and not self.cors_origin() and not path.startswith("/api/pay/notify/"):
            raise RequestRejected(403, "Origin is not allowed")
        if path.startswith("/api/pay/notify/"):
            return
        cookie = self.headers.get("Cookie") or ""
        uses_session_cookie = "ycimage_session=" in cookie
        has_bearer = bool((self.headers.get("Authorization") or "").lower().startswith("bearer "))
        requested_with = (self.headers.get("X-Requested-With") or "").lower()
        if uses_session_cookie and not has_bearer and requested_with != "xmlhttprequest":
            raise RequestRejected(403, "CSRF protection rejected the request")
        if uses_session_cookie and not has_bearer:
            csrf_header = self.headers.get("X-CSRF-Token") or ""
            csrf_cookie = ""
            session_cookie = ""
            for part in cookie.split(";"):
                key, _, value = part.strip().partition("=")
                if key == "ycimage_csrf":
                    csrf_cookie = value.strip()
                elif key == "ycimage_session":
                    session_cookie = value.strip()
            expected_csrf = csrf_token_for_session(session_cookie)
            if (
                not csrf_header
                or not csrf_cookie
                or not session_cookie
                or not hmac.compare_digest(csrf_header, csrf_cookie)
                or not hmac.compare_digest(csrf_cookie, expected_csrf)
            ):
                raise RequestRejected(403, "CSRF protection rejected the request")

    def rate_limit_route(self, method: str, path: str) -> tuple[str, int, int] | None:
        if path in RATE_LIMIT_RULES:
            limit, window = RATE_LIMIT_RULES[path]
            return path, limit, window
        if path.startswith("/api/assets/"):
            return "/api/assets/*", 240, 60
        if path.startswith("/api/jobs/"):
            return "/api/jobs/*", 120, 60
        if method in {"POST", "PATCH", "PUT", "DELETE"}:
            limit, window = DEFAULT_WRITE_RATE_LIMIT
            return f"{method}:{path}", limit, window
        return None

    def enforce_rate_limit(self, method: str, path: str) -> None:
        route = self.rate_limit_route(method, path)
        if not route:
            return
        route_key, limit, window = route
        now_ts = time.monotonic()
        subjects = [f"ip:{self.client_address[0]}"]
        token = self.bearer_token()
        if token:
            subjects.append(f"token:{hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]}")
        for subject in subjects:
            key = (subject, route_key)
            recent = [item for item in RATE_LIMIT_BUCKETS.get(key, []) if now_ts - item < window]
            if len(recent) >= limit:
                raise RequestRejected(429, "Too many requests")
            recent.append(now_ts)
            RATE_LIMIT_BUCKETS[key] = recent

    def cors_origin(self) -> str:
        origin = (self.headers.get("Origin") or "").rstrip("/")
        if origin and origin in ALLOWED_CORS_ORIGINS:
            return origin
        return ""

    def request_cookie_value(self, name: str) -> str:
        cookie = self.headers.get("Cookie") or ""
        for part in cookie.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value.strip()
        return ""

    def maybe_refresh_csrf_cookie_headers(self) -> dict[str, str]:
        session_cookie = self.request_cookie_value("ycimage_session")
        if not session_cookie:
            return {}
        csrf_cookie = self.request_cookie_value("ycimage_csrf")
        expected_csrf = csrf_token_for_session(session_cookie)
        if csrf_cookie and hmac.compare_digest(csrf_cookie, expected_csrf):
            return {}
        return {"Set-Cookie-CSRF": csrf_cookie_header(expected_csrf)}

    def send_json(self, status: int, payload: dict | list, extra_headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        cors_origin = self.cors_origin()
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Cache-Control", "no-store")
        headers_to_send = self.maybe_refresh_csrf_cookie_headers()
        headers_to_send.update(extra_headers or {})
        for key, value in headers_to_send.items():
            header_name = "Set-Cookie" if key.lower().startswith("set-cookie") else key
            self.send_header(header_name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status: int, body: str, mime: str = "text/plain; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_security_headers()
        self.send_header("Content-Type", mime)
        cors_origin = self.cors_origin()
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def bearer_token(self) -> str:
        auth = self.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            return auth.split(" ", 1)[1].strip()
        cookie = self.headers.get("Cookie") or ""
        for part in cookie.split(";"):
            key, _, value = part.strip().partition("=")
            if key == "ycimage_session":
                return value.strip()
        return ""

    def request_is_local(self) -> bool:
        host = self.client_address[0] if self.client_address else ""
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return host in {"localhost", "::1"}

    def admin_token_authenticated(self) -> bool:
        admin_token = self.headers.get("X-Admin-Token") or ""
        if not YCIMAGE_ADMIN_TOKEN or not admin_token:
            return False
        if not YCIMAGE_ADMIN_TOKEN_REMOTE and not self.request_is_local():
            return False
        return hmac.compare_digest(admin_token, YCIMAGE_ADMIN_TOKEN)

    def request_admin_user(self, conn: sqlite3.Connection) -> sqlite3.Row | None:
        if self.admin_token_authenticated():
            return conn.execute("SELECT * FROM users WHERE id = 'user_admin' LIMIT 1").fetchone()
        user = get_user_by_session(conn, self.bearer_token())
        return user if user_is_admin(conn, user) else None

    def require_admin(self, conn: sqlite3.Connection) -> sqlite3.Row | None:
        user = self.request_admin_user(conn)
        if not user:
            self.send_json(401, {"error": "Admin authentication required", "message": "Admin authentication required"})
            return None
        return user

    def send_binary(self, status: int, body: bytes, mime: str, cache: str = "public, max-age=86400") -> None:
        self.send_response(status)
        self.send_security_headers()
        self.send_header("Content-Type", mime)
        cors_origin = self.cors_origin()
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_api(self, method: str, path: str, query: dict, payload: dict | None = None) -> None:
        payload = payload or {}
        with connect(self.server.db_path) as conn:  # type: ignore[attr-defined]
            if method == "GET" and path == "/api/health":
                self.send_json(200, {"ok": True})
                return

            if method == "GET" and path == "/api/settings/public":
                settings = app_settings(conn)
                settings["payment"] = public_payment_settings(conn)
                counts = {
                    "imageBlobs": conn.execute("SELECT COUNT(*) AS c FROM asset_blobs").fetchone()["c"],
                    "assets": conn.execute("SELECT COUNT(*) AS c FROM assets").fetchone()["c"],
                    "styleTemplates": conn.execute("SELECT COUNT(*) AS c FROM style_templates WHERE status = 'enabled'").fetchone()["c"],
                    "templates": conn.execute("SELECT COUNT(*) AS c FROM templates WHERE status = 'enabled'").fetchone()["c"],
                }
                self.send_json(
                    200,
                    {
                        "settings": settings,
                        "models": list_models(conn),
                        "counts": counts,
                        "apiEndpoint": "/api/generate-image",
                        "pricingPlans": list_active_pricing_plans(conn),
                    },
                )
                return

            if method == "GET" and path == "/api/pricing/plans":
                self.send_json(200, {"items": list_active_pricing_plans(conn)})
                return

            if method == "GET" and path == "/api/auth/me":
                user = get_user_by_session(conn, self.bearer_token())
                self.send_json(200, serialize_account_summary(conn, user))
                return

            if method == "GET" and path == "/api/account/dashboard":
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                prune_account_job_history(conn, user["id"], ACCOUNT_JOB_HISTORY_LIMIT)
                summary = serialize_account_summary(conn, user)
                summary["ledger"] = list_account_ledger(conn, user["id"], 12)
                summary["jobs"] = list_account_jobs(conn, user["id"], ACCOUNT_JOB_HISTORY_LIMIT)
                summary["orders"] = list_account_orders(conn, user["id"], 8)
                summary["invites"] = list_account_invites(conn, user["id"], 8)
                summary["customTemplates"] = list_account_custom_templates(conn, user["id"], ACCOUNT_CUSTOM_TEMPLATE_LIMIT)
                summary["limits"] = {
                    "jobs": ACCOUNT_JOB_HISTORY_LIMIT,
                    "customTemplates": custom_template_limit(user["membership_level"], user["id"]),
                }
                self.send_json(200, summary)
                return

            if method == "GET" and path == "/api/account/ledger":
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                self.send_json(200, {"items": list_account_ledger(conn, user["id"])})
                return

            if method == "GET" and path == "/api/account/jobs":
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                prune_account_job_history(conn, user["id"], ACCOUNT_JOB_HISTORY_LIMIT)
                self.send_json(200, {"items": list_account_jobs(conn, user["id"], ACCOUNT_JOB_HISTORY_LIMIT), "limit": ACCOUNT_JOB_HISTORY_LIMIT})
                return

            if method == "POST" and path == "/api/account/password":
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    current_password = str(payload.get("currentPassword") or "")
                    new_password = validate_password(payload.get("newPassword"))
                    confirm_password = str(payload.get("confirmPassword") or "")
                    if new_password != confirm_password:
                        raise ValueError("New passwords do not match")
                    if password_is_configured(conn, user["id"]):
                        if not verify_password(conn, user["id"], current_password):
                            raise ValueError("Current password is incorrect")
                        if hmac.compare_digest(current_password, new_password):
                            raise ValueError("New password must differ from current password")
                    store_password(conn, user["id"], new_password)
                    revoke_all_sessions_for_user(conn, user["id"])
                    session = issue_session(conn, user["id"])
                    audit(conn, "account.password.update", "user", user["id"], {"passwordUpdated": True})
                except ValueError as error:
                    conn.execute("ROLLBACK")
                    self.send_json(400, client_error_payload(error, 400))
                    return
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                conn.execute("COMMIT")
                refreshed_user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "message": "Password updated successfully",
                        "account": serialize_account_summary(conn, refreshed_user),
                    },
                    auth_cookie_headers(session),
                )
                return

            if path == "/api/account/custom-templates":
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in before saving templates"})
                    return
                if method == "GET":
                    limit = custom_template_limit(user["membership_level"], user["id"])
                    items = list_account_custom_templates(conn, user["id"], ACCOUNT_CUSTOM_TEMPLATE_LIMIT)
                    self.send_json(200, {"items": items, "count": len(items), "limit": limit})
                    return
                if method == "POST":
                    try:
                        conn.execute("BEGIN IMMEDIATE")
                        item = create_custom_template_from_payload(conn, user, payload)
                        conn.execute("COMMIT")
                    except ValueError as error:
                        conn.execute("ROLLBACK")
                        self.send_json(400, client_error_payload(error, 400))
                        return
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise
                    self.send_json(
                        201,
                        {
                            "item": item,
                            "count": item.get("count"),
                            "limit": item.get("limit"),
                            "message": f"Template saved. Current {item.get('count')} / {item.get('limit')}.",
                        },
                    )
                    return

            if path.startswith("/api/account/custom-templates/"):
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in before managing templates"})
                    return
                template_id = unquote(path.rsplit("/", 1)[-1])
                if method == "GET":
                    row = get_account_custom_template_row(conn, user["id"], template_id)
                    if not row:
                        self.send_json(404, {"error": "Template not found", "message": "Template not found or already deleted"})
                        return
                    self.send_json(200, {"item": get_template(conn, template_id, include_private=True)})
                    return
                if method == "PATCH":
                    try:
                        conn.execute("BEGIN IMMEDIATE")
                        item = update_custom_template_from_payload(conn, user, template_id, payload)
                        conn.execute("COMMIT")
                    except ValueError as error:
                        conn.execute("ROLLBACK")
                        self.send_json(400, client_error_payload(error, 400))
                        return
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise
                    self.send_json(200, {"item": item, "message": "Template updated"})
                    return
                if method == "DELETE":
                    try:
                        conn.execute("BEGIN IMMEDIATE")
                        count = archive_custom_template(conn, user, template_id)
                        conn.execute("COMMIT")
                    except ValueError as error:
                        conn.execute("ROLLBACK")
                        self.send_json(400, client_error_payload(error, 400))
                        return
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise
                    self.send_json(
                        200,
                        {
                            "ok": True,
                            "count": count,
                            "limit": custom_template_limit(user["membership_level"], user["id"]),
                            "message": "Template deleted",
                        },
                    )
                    return

            if method == "GET" and path == "/api/account/orders":
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                self.send_json(200, {"items": list_account_orders(conn, user["id"])})
                return

            if method == "GET" and path == "/api/account/invites":
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                self.send_json(200, {"items": list_account_invites(conn, user["id"])})
                return

            if method == "GET" and path.startswith("/api/pay/orders/"):
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                order_no = unquote(path.rsplit("/", 1)[-1])
                order_row = conn.execute(
                    "SELECT * FROM orders WHERE order_no = ? AND user_id = ? LIMIT 1",
                    (order_no, user["id"]),
                ).fetchone()
                if not order_row:
                    self.send_json(404, {"error": "Order not found", "message": "Order not found"})
                    return
                if str(order_row["status"] or "").lower() == "pending":
                    try:
                        order_row = reconcile_mpay_order(conn, order_row)
                    except Exception as error:  # noqa: BLE001
                        audit(conn, "payment.reconcile_failed", "order", order_row["id"], {"error": normalize_upstream_error(error)})
                self.send_json(200, {"item": serialize_payment_order(conn, order_row)})
                return

            if method == "POST" and path == "/api/auth/mobile-code":
                if not ENABLE_MOBILE_AUTH:
                    self.send_json(404, {"error": "Mobile auth disabled", "message": "Mobile authentication is disabled"})
                    return
                try:
                    mobile = normalize_mobile(payload.get("mobile"))
                    purpose = str(payload.get("purpose") or "register").strip() or "register"
                    code = issue_mobile_code(conn, mobile, purpose)
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "mobile": mobile,
                        "expiresAt": code["expiresAt"],
                        "message": "Verification code sent",
                        **({"debugCode": code["code"]} if DEBUG_AUTH_CODES else {}),
                    },
                )
                return

            if method == "POST" and path == "/api/pay/orders":
                user = get_user_by_session(conn, self.bearer_token())
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                plan_value = str(payload.get("planId") or payload.get("planCode") or "").strip()
                channel = str(payload.get("channel") or "wechat").strip().lower()
                if channel not in {"wechat", "alipay"}:
                    self.send_json(400, {"error": "Invalid channel", "message": "Unsupported payment channel"})
                    return
                payment_config = resolve_payment_settings(conn)
                if payment_config["provider"] != "mpay":
                    self.send_json(400, {"error": "Payment disabled", "message": "MPAY payment is not enabled"})
                    return
                plan = get_pricing_plan(conn, plan_value)
                if not plan:
                    self.send_json(404, {"error": "Plan not found", "message": "Plan not found"})
                    return
                if int(plan["price_cents"] or 0) <= 0:
                    self.send_json(400, {"error": "Free plan", "message": "Free plan does not require payment"})
                    return
                order = create_local_order(conn, user, plan, channel)
                try:
                    payment = build_mpay_payment(conn, order, channel)
                except Exception as error:  # noqa: BLE001
                    conn.execute(
                        "UPDATE orders SET status = 'failed', notes = ?, updated_at = ? WHERE id = ?",
                        ("Payment initialization failed", now(), order["id"]),
                    )
                    audit(conn, "payment.init_failed", "order", order["id"], {"error": normalize_upstream_error(error)})
                    self.send_json(502, {"error": "Payment init failed", "message": "Payment is temporarily unavailable. Please try again later."})
                    return
                provider_order_id = payment.get("providerOrderId")
                if provider_order_id:
                    metadata = order["metadata"] | {"paymentInit": redact_sensitive(payment.get("raw", {})), "paymentProvider": payment.get("provider")}
                    conn.execute(
                        "UPDATE orders SET payment_provider_order_id = ?, metadata_json = ?, updated_at = ? WHERE id = ?",
                        (provider_order_id, json_dumps(metadata), now(), order["id"]),
                    )
                order_row = conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
                self.send_json(200, {"item": serialize_payment_order(conn, order_row), "payment": safe_public_payment(payment)})
                return

            if method == "GET" and path == "/api/pay/notify/mpay":
                self.send_text(405, "fail")
                return

            if method == "POST" and path == "/api/pay/notify/mpay":
                config = resolve_payment_settings(conn)
                if config["provider"] != "mpay":
                    self.send_text(404, "fail")
                    return
                if not config["mpayKey"]:
                    self.send_text(403, "fail")
                    return
                notify_payload = payload
                signature = str(notify_payload.get("sign") or "")
                if not signature:
                    self.send_text(400, "fail")
                    return
                if not epay_v1_signature_matches(notify_payload, signature, [config["mpayKey"], *config.get("mpayOldKeys", [])]):
                    self.send_text(400, "fail")
                    return
                callback_pid = str(notify_payload.get("pid") or "").strip()
                if not callback_pid or not hmac.compare_digest(callback_pid, str(config["mpayPid"])):
                    self.send_text(400, "fail")
                    return
                order_no = str(notify_payload.get("out_trade_no") or "").strip()
                if not order_no:
                    self.send_text(400, "fail")
                    return
                order_row = conn.execute("SELECT * FROM orders WHERE order_no = ? LIMIT 1", (order_no,)).fetchone()
                if not order_row:
                    self.send_text(404, "fail")
                    return
                try:
                    paid_cents = int(round(float(str(notify_payload.get("money") or "0")) * 100))
                except ValueError:
                    paid_cents = 0
                if paid_cents != int(order_row["amount_cents"] or 0):
                    self.send_text(400, "fail")
                    return
                trade_status = str(notify_payload.get("trade_status") or notify_payload.get("status") or "").upper()
                if trade_status in {"TRADE_SUCCESS", "TRADE_FINISHED", "1", "SUCCESS", "PAID"}:
                    try:
                        conn.execute("BEGIN IMMEDIATE")
                        locked_order = conn.execute("SELECT * FROM orders WHERE order_no = ? LIMIT 1", (order_no,)).fetchone()
                        apply_paid_order(
                            conn,
                            locked_order,
                            str(notify_payload.get("trade_no") or notify_payload.get("api_trade_no") or ""),
                            notify_payload,
                        )
                        conn.execute("COMMIT")
                    except ValueError:
                        conn.execute("ROLLBACK")
                        self.send_text(409, "fail")
                        return
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise
                    self.send_text(200, "success")
                    return
                self.send_text(200, "fail")
                return

            if method == "POST" and path == "/api/pay/notify/jeepay":
                config = resolve_payment_settings(conn)
                if config["provider"] != "jeepay":
                    self.send_json(404, {"error": "Payment provider disabled", "message": "Payment provider disabled"})
                    return
                signature = str(payload.get("sign") or "")
                if not config["notifySecret"]:
                    self.send_json(403, {"error": "Notify secret missing", "message": "Notify secret is not configured"})
                    return
                if not signature:
                    self.send_json(400, {"error": "Missing sign", "message": "Missing callback signature"})
                    return
                sign_payload = dict(payload)
                sign_payload.pop("sign", None)
                expected = sign_jeepay_payload(sign_payload, config["notifySecret"])
                if not hmac.compare_digest(expected, signature):
                    self.send_json(400, {"error": "Invalid sign", "message": "Callback signature verification failed"})
                    return
                order_no = str(payload.get("mchOrderNo") or payload.get("orderNo") or "").strip()
                if not order_no:
                    self.send_json(400, {"error": "Missing order no", "message": "Missing order number"})
                    return
                order_row = conn.execute("SELECT * FROM orders WHERE order_no = ? LIMIT 1", (order_no,)).fetchone()
                if not order_row:
                    self.send_json(404, {"error": "Order not found", "message": "Order not found"})
                    return
                mch_no = str(payload.get("mchNo") or payload.get("mchno") or "").strip()
                app_id = str(payload.get("appId") or payload.get("appid") or "").strip()
                if not mch_no or not app_id:
                    self.send_json(400, {"error": "Missing merchant identifiers", "message": "Missing merchant identifiers"})
                    return
                if config["mchNo"] and not hmac.compare_digest(mch_no, str(config["mchNo"])):
                    self.send_json(400, {"error": "Merchant mismatch", "message": "Callback merchant verification failed"})
                    return
                if config["appId"] and not hmac.compare_digest(app_id, str(config["appId"])):
                    self.send_json(400, {"error": "App mismatch", "message": "Callback application verification failed"})
                    return
                try:
                    paid_cents = int(str(payload.get("amount") or payload.get("payAmount") or "0").strip())
                except (TypeError, ValueError):
                    self.send_json(400, {"error": "Invalid amount", "message": "Callback amount is invalid"})
                    return
                if paid_cents != int(order_row["amount_cents"] or 0):
                    self.send_json(400, {"error": "Amount mismatch", "message": "Callback amount verification failed"})
                    return
                pay_status = str(payload.get("state") or payload.get("status") or "").lower()
                if pay_status in {"2", "success", "paid"}:
                    try:
                        conn.execute("BEGIN IMMEDIATE")
                        locked_order = conn.execute("SELECT * FROM orders WHERE order_no = ? LIMIT 1", (order_no,)).fetchone()
                        result = apply_paid_order(
                            conn,
                            locked_order,
                            str(payload.get("payOrderId") or payload.get("providerOrderId") or ""),
                            payload,
                        )
                        conn.execute("COMMIT")
                    except ValueError as error:
                        conn.execute("ROLLBACK")
                        self.send_json(409, client_error_payload(error, 409, fallback="Conflict"))
                        return
                    except Exception:
                        conn.execute("ROLLBACK")
                        raise
                    self.send_text(200, "success")
                    return
                if pay_status in {"3", "failed", "closed", "cancelled"}:
                    if str(order_row["status"] or "").lower() == "paid":
                        self.send_text(200, "success")
                        return
                    conn.execute(
                        "UPDATE orders SET status = 'failed', metadata_json = ?, updated_at = ? WHERE id = ?",
                        (json_dumps({"providerPayload": safe_provider_payload(payload)}), now(), order_row["id"]),
                    )
                    self.send_text(200, "success")
                    return
                self.send_text(200, "success")
                return

            if method == "POST" and path == "/api/auth/register":
                transaction_started = False
                try:
                    email = normalize_email(payload.get("email"))
                    raw_mobile = str(payload.get("mobile") or "").strip()
                    mobile = normalize_mobile(raw_mobile) if raw_mobile else None
                    if mobile and not ENABLE_MOBILE_AUTH:
                        raise ValueError("Mobile registration is disabled; please use email registration")
                    password = validate_password(payload.get("password"))
                    confirm_password = str(payload.get("confirmPassword") or "")
                    if password != confirm_password:
                        raise ValueError("Passwords do not match")
                    code = str(payload.get("code") or "").strip()
                    display_name = str(payload.get("displayName") or "").strip() or email.split("@", 1)[0]
                    invite_code = str(payload.get("inviteCode") or "").strip().upper()
                    if mobile and not code:
                        raise ValueError("Mobile verification code is required")
                    exists = conn.execute(
                        "SELECT 1 FROM users WHERE email = ? OR (? IS NOT NULL AND mobile = ?)",
                        (email, mobile, mobile),
                    ).fetchone()
                    if exists:
                        self.send_json(409, {"error": "Account exists", "message": "Email or mobile has already been registered"})
                        return
                    if mobile:
                        verify_mobile_code(conn, mobile, code, "register")

                    user_id = uid("user")
                    conn.execute("BEGIN IMMEDIATE")
                    transaction_started = True
                    conn.execute(
                        """
                        INSERT INTO users(
                            id, organization_id, display_name, mobile, email, role_id,
                            membership_level, status, locale, created_at, updated_at
                        )
                        VALUES (?, 'org_default', ?, ?, ?, 'role_user', 'free', 'active', 'zh-CN', ?, ?)
                        """,
                        (user_id, display_name, mobile, email, now(), now()),
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO user_profiles(user_id, preferences_json) VALUES (?, '{}')",
                        (user_id,),
                    )
                    store_password(conn, user_id, password)
                    grant_credit(conn, user_id, 100, "register_bonus", "auth", "register", None, {"source": "mobile"})
                    create_referral_code(conn, user_id)

                    inviter = None
                    if invite_code:
                        inviter = conn.execute(
                            "SELECT * FROM referral_codes WHERE invite_code = ?",
                            (invite_code,),
                        ).fetchone()
                    if inviter and inviter["user_id"] != user_id:
                        reward_amount = int(inviter["reward_credits"] or 100)
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO referral_events(
                                id, inviter_user_id, invited_user_id, invite_code, reward_amount, created_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (uid("ref"), inviter["user_id"], user_id, invite_code, reward_amount, now()),
                        )
                        conn.execute(
                            "UPDATE referral_codes SET invite_count = invite_count + 1 WHERE user_id = ?",
                            (inviter["user_id"],),
                        )
                        grant_credit(
                            conn,
                            inviter["user_id"],
                            reward_amount,
                            "invite_register_reward",
                            "referral",
                            user_id,
                            None,
                            {"inviteCode": invite_code},
                        )

                    session = issue_session(conn, user_id)
                    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                    result = serialize_account_summary(conn, user, session)
                    result["message"] = "Registration succeeded; 100 credits granted."
                    conn.execute("COMMIT")
                    transaction_started = False
                except ValueError as error:
                    if transaction_started:
                        conn.execute("ROLLBACK")
                    self.send_json(400, client_error_payload(error, 400))
                    return
                except Exception:
                    if transaction_started:
                        conn.execute("ROLLBACK")
                    raise
                self.send_json(201, result, auth_cookie_headers(session))
                return

            if method == "POST" and path == "/api/auth/password-login":
                try:
                    account = str(payload.get("account") or payload.get("email") or "").strip().lower()
                    password = str(payload.get("password") or "")
                    if not account or not password:
                        raise ValueError("Email and password are required")
                    if "@" not in account:
                        raise ValueError("Only email/password login is enabled")
                    email = normalize_email(account)
                    user = conn.execute(
                        "SELECT * FROM users WHERE email = ? AND status = 'active' LIMIT 1",
                        (email,),
                    ).fetchone()
                    if not user or not verify_password(conn, user["id"], password):
                        raise ValueError("Invalid email or password")
                    session = issue_session(conn, user["id"])
                    result = serialize_account_summary(conn, user, session)
                    result["message"] = "Login succeeded"
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                self.send_json(200, result, auth_cookie_headers(session))
                return

            if method == "POST" and path == "/api/auth/wechat-login":
                if not ENABLE_WECHAT_MOCK_LOGIN:
                    self.send_json(404, {"error": "Wechat login disabled", "message": "Wechat login is disabled"})
                    return
                raw_code = str(payload.get("code") or payload.get("wechatCode") or "").strip()
                if not raw_code:
                    self.send_json(400, {"error": "Missing code", "message": "Wechat authorization code is required"})
                    return
                open_id = f"wx_mock_{hashlib.sha256(raw_code.encode('utf-8')).hexdigest()[:18]}"
                invite_code = str(payload.get("inviteCode") or "").strip().upper()
                display_name = str(payload.get("displayName") or "").strip() or "Wechat user"
                conn.execute("BEGIN")
                try:
                    user = conn.execute("SELECT * FROM users WHERE wechat_openid = ?", (open_id,)).fetchone()
                    is_new_user = user is None
                    if is_new_user:
                        user_id = uid("user")
                        conn.execute(
                            """
                            INSERT INTO users(
                                id, organization_id, display_name, wechat_openid, role_id,
                                membership_level, status, locale, created_at, updated_at
                            )
                            VALUES (?, 'org_default', ?, ?, 'role_user', 'free', 'active', 'zh-CN', ?, ?)
                            """,
                            (user_id, display_name, open_id, now(), now()),
                        )
                        conn.execute(
                            "INSERT OR IGNORE INTO user_profiles(user_id, preferences_json) VALUES (?, '{}')",
                            (user_id,),
                        )
                        grant_credit(conn, user_id, 100, "register_bonus", "auth", "wechat", None, {"source": "wechat"})
                        create_referral_code(conn, user_id)
                        if invite_code:
                            inviter = conn.execute("SELECT * FROM referral_codes WHERE invite_code = ?", (invite_code,)).fetchone()
                            if inviter and inviter["user_id"] != user_id:
                                reward_amount = int(inviter["reward_credits"] or 100)
                                conn.execute(
                                    """
                                    INSERT OR IGNORE INTO referral_events(
                                        id, inviter_user_id, invited_user_id, invite_code, reward_amount, created_at
                                    )
                                    VALUES (?, ?, ?, ?, ?, ?)
                                    """,
                                    (uid("ref"), inviter["user_id"], user_id, invite_code, reward_amount, now()),
                                )
                                conn.execute("UPDATE referral_codes SET invite_count = invite_count + 1 WHERE user_id = ?", (inviter["user_id"],))
                                grant_credit(conn, inviter["user_id"], reward_amount, "invite_register_reward", "referral", user_id, None, {"inviteCode": invite_code})
                        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                    session = issue_session(conn, user["id"])
                    result = serialize_account_summary(conn, user, session)
                    result["message"] = "Wechat login succeeded; 100 credits granted." if is_new_user else "Wechat login succeeded"
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                self.send_json(200, result, auth_cookie_headers(session))
                return

            if method == "POST" and path == "/api/auth/logout":
                token = self.bearer_token()
                if token:
                    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                    conn.execute(
                        "UPDATE user_sessions SET revoked_at = ? WHERE session_token_hash = ?",
                        (now(), token_hash),
                    )
                self.send_json(200, {"ok": True}, expired_auth_cookie_headers())
                return

            if method == "POST" and path == "/api/auth/logout-all":
                token = self.bearer_token()
                user = get_user_by_session(conn, token)
                if not user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                revoke_all_sessions_for_user(conn, user["id"])
                audit(conn, "auth.logout_all", "user", user["id"], {"revokedAllSessions": True})
                self.send_json(200, {"ok": True}, expired_auth_cookie_headers())
                return

            if method == "GET" and path == "/api/categories":
                self.send_json(200, {"items": list_categories(conn)})
                return

            if method == "GET" and path == "/api/templates":
                include_params = query.get("include_params", ["0"])[0] in {"1", "true", "yes"}
                result = query_templates(conn, query, include_params=include_params)
                result["categories"] = list_categories(conn)
                result["settings"] = app_settings(conn)
                result["settings"]["payment"] = public_payment_settings(conn)
                self.send_json(200, result)
                return

            if method == "GET" and path.startswith("/api/templates/"):
                template_id = unquote(path.rsplit("/", 1)[-1])
                template = get_template(conn, template_id)
                if not template:
                    self.send_json(404, {"error": "Template not found"})
                    return
                self.send_json(200, {"item": template})
                return

            if method == "GET" and path.startswith("/api/assets/"):
                asset_id = unquote(path.rsplit("/", 1)[-1])
                row = conn.execute(
                    """
                    SELECT ab.content, a.*
                    FROM asset_blobs ab
                    JOIN assets a ON a.id = ab.asset_id
                    WHERE ab.asset_id = ?
                    """,
                    (asset_id,),
                ).fetchone()
                if not row:
                    self.send_json(404, {"error": "Asset not found"})
                    return
                session_user = get_user_by_session(conn, self.bearer_token())
                if not session_user and not asset_is_public(row):
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                if not user_can_access_asset(conn, session_user, row):
                    self.send_json(403, {"error": "Forbidden", "message": "Access denied"})
                    return
                self.send_binary(200, row["content"], row["mime_type"] or "application/octet-stream")
                return

            if method == "GET" and path.startswith("/api/jobs/"):
                job_id = unquote(path.rsplit("/", 1)[-1])
                job = conn.execute("SELECT * FROM generation_jobs WHERE id = ? OR job_no = ?", (job_id, job_id)).fetchone()
                if not job:
                    self.send_json(404, {"error": "Job not found", "message": "Job not found"})
                    return
                session_user = get_user_by_session(conn, self.bearer_token())
                if not session_user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in"})
                    return
                if not user_can_access_job(conn, session_user, job):
                    self.send_json(403, {"error": "Forbidden", "message": "Access denied"})
                    return
                model = conn.execute("SELECT modality FROM model_routes WHERE id = ?", (job["model_route_id"],)).fetchone()
                if model and model["modality"] == "video" and job["status"] in {"queued", "running"}:
                    try:
                        item = refresh_video_job_from_provider(conn, job)
                    except RuntimeError as error:
                        item = serialize_generation_job(conn, job)
                        item["message"] = normalize_upstream_error(error)
                elif model and model["modality"] == "image" and job["status"] in {"queued", "running"}:
                    try:
                        item = refresh_image_job_from_provider(conn, job)
                    except RuntimeError as error:
                        item = serialize_generation_job(conn, job)
                        item["message"] = normalize_upstream_error(error)
                else:
                    hydrated_job = ensure_generation_job_outputs_persisted(conn, job) if job["status"] == "success" else job
                    item = serialize_generation_job(conn, hydrated_job)
                self.send_json(200, {"item": item})
                return

            if method == "POST" and path == "/api/generate-image":
                session_user = get_user_by_session(conn, self.bearer_token())
                if not session_user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in before generating images"})
                    return
                user_id = session_user["id"]
                template_id = payload.get("templateId")
                prompt = str(payload.get("prompt") or "").strip()
                settings = payload.get("settings") or {}
                reference_images = payload.get("referenceImages") or []
                if len(prompt) > MAX_PROMPT_LENGTH:
                    self.send_json(400, {"error": "Prompt too long", "message": "Prompt too long"})
                    return
                if template_modality(conn, template_id) == "video":
                    self.send_json(400, {"error": "Invalid template modality", "message": "Use the video generation endpoint for video templates"})
                    return
                if not prompt:
                    self.send_json(400, {"error": "Prompt required", "message": "Prompt is required"})
                    return
                if not isinstance(reference_images, list):
                    self.send_json(400, {"error": "Invalid reference images", "message": "Reference images must be a list"})
                    return
                if any(not isinstance(item, dict) for item in reference_images):
                    self.send_json(400, {"error": "Invalid reference images", "message": "Reference images must be objects"})
                    return
                if settings.get("referenceMode") == "text-only":
                    reference_images = []
                if settings.get("referenceMode") == "required" and not reference_images:
                    self.send_json(400, {"error": "Reference image required", "message": "Reference image is required"})
                    return
                if len(reference_images) > MAX_REFERENCE_IMAGE_COUNT:
                    self.send_json(400, {"error": "Too many reference images", "message": f"Max {MAX_REFERENCE_IMAGE_COUNT} reference images"})
                    return
                try:
                    validate_reference_images(reference_images)
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                if clamp_output_count(settings.get("count")) > 4:
                    self.send_json(400, {"error": "Too many outputs", "message": "Max 4 images per request"})
                    return
                api_key = effective_apimart_api_key(conn)
                base_url = effective_apimart_base_url(conn)
                if not api_key:
                    self.send_json(
                        503,
                        {
                            "error": "Image service is not configured",
                            "message": "Image service is not configured; no credits were charged.",
                            "refund": {"amount": 0, "refunded": False},
                        },
                    )
                    return

                route_id = model_route_id_from_value(conn, settings.get("model"))
                route_row = conn.execute("SELECT * FROM model_routes WHERE id = ?", (route_id,)).fetchone()
                if route_row and route_row["modality"] != "image":
                    self.send_json(400, {"error": "Invalid model", "message": "Please choose an image model"})
                    return
                credit_cost, pricing_breakdown = calculate_credit_cost(route_row, settings)
                output_count = pricing_breakdown["count"]
                try:
                    ensure_sufficient_credits(conn, user_id, credit_cost)
                except ValueError as error:
                    self.send_json(402, client_error_payload(error, 402, extra={"creditCost": credit_cost}))
                    return
                try:
                    provider_payload = build_image_payload(route_row, settings, prompt, reference_images, api_key, base_url)
                except Exception as error:  # noqa: BLE001
                    self.send_json(
                        502,
                        {
                            "error": "Reference image preparation failed",
                            "message": "Reference image preparation failed; no credits were charged.",
                            "stage": "reference_upload",
                            "refund": {"amount": 0, "refunded": False},
                        },
                    )
                    return
                try:
                    provider_response = call_json_api(
                        "POST",
                        f"{base_url}/v1/images/generations",
                        headers={"Authorization": f"Bearer {api_key}"},
                        payload=provider_payload,
                        timeout=route_timeout_seconds(route_row, 90, IMAGE_GENERATION_TIMEOUT_FLOOR),
                    )
                except Exception as error:  # noqa: BLE001
                    self.send_json(
                        502,
                        {
                            "error": "Image job submit failed",
                            "message": "Image job submit failed; no credits were charged.",
                            "stage": "submit",
                            "refund": {"amount": 0, "refunded": False},
                        },
                    )
                    return
                apimart_task_id = parse_apimart_task_id(provider_response)
                if not apimart_task_id:
                    self.send_json(
                        502,
                        {
                            "error": "Image job submit failed",
                            "message": "Image service did not return a task id; no credits were charged.",
                            "providerResponseSummary": safe_provider_response_summary(provider_response),
                        },
                    )
                    return
                job_id = uid("job")
                job_no = f"JOB-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:4]}"
                reference_file_summary = [
                    {
                        "name": item.get("name"),
                        "mimeType": item.get("mimeType"),
                        "byteSize": item.get("byteSize"),
                    }
                    for item in reference_images
                ]
                stored_settings = {**settings, "count": output_count}
                request_payload = safe_generation_request_snapshot(
                    payload,
                    stored_settings,
                    reference_file_summary,
                    provider_payload,
                    pricing_breakdown,
                )
                provider_record = {
                    "apimartTaskId": apimart_task_id,
                    "submitResponse": provider_response,
                    "provider": "APIMart",
                }
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute(
                        """
                        INSERT INTO generation_jobs(
                            id, job_no, user_id, organization_id, template_id, model_route_id, status,
                            prompt_final, prompt_params_json, quality, aspect_ratio, size, output_count,
                            reference_mode, credit_cost, request_payload_json, provider_response_json,
                            queued_at, created_at, updated_at
                        )
                        VALUES (?, ?, ?, 'org_default', ?, ?, 'queued', ?, ?, ?, ?, ?, ?,
                                ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            job_id,
                            job_no,
                            user_id,
                            template_id,
                            route_id,
                            prompt,
                            json_dumps(payload.get("params") or {}),
                            settings.get("quality") or "high",
                            settings.get("aspectRatio") or "1:1",
                            settings.get("size") or "1024x1024",
                            output_count,
                            settings.get("referenceMode") or "optional",
                            credit_cost,
                            json_dumps(request_payload),
                            json_dumps(provider_record),
                            now(),
                            now(),
                            now(),
                        ),
                    )
                    charge_result = charge_generation_credits(
                        conn,
                        user_id,
                        job_id,
                        credit_cost,
                        {"jobNo": job_no, "pricing": pricing_breakdown, "templateId": template_id},
                    )
                    reference_assets = store_reference_images(conn, reference_images, job_id, user_id)
                    if reference_assets:
                        request_payload["referenceAssets"] = reference_assets
                        conn.execute(
                            "UPDATE generation_jobs SET request_payload_json = ?, updated_at = ? WHERE id = ?",
                            (json_dumps(request_payload), now(), job_id),
                        )
                    audit(
                        conn,
                        "generation.enqueue",
                        "generation_job",
                        job_id,
                        {"templateId": template_id, "references": len(reference_assets), "creditCost": credit_cost},
                    )
                    prune_account_job_history(conn, user_id, ACCOUNT_JOB_HISTORY_LIMIT)
                    conn.execute("COMMIT")
                except ValueError as error:
                    conn.execute("ROLLBACK")
                    self.send_json(400, client_error_payload(error, 400))
                    return
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                self.send_json(
                    202,
                    {
                        "jobId": job_id,
                        "jobNo": job_no,
                        "status": "queued",
                        "providerTaskId": apimart_task_id,
                        "creditCost": credit_cost,
                        "balanceAfter": charge_result["balance"],
                        "pricing": pricing_breakdown,
                        "referenceCount": len(reference_images),
                        "referenceAssets": reference_assets,
                        "message": f"Image job queued. Charged {credit_cost} credits. Reference images: {len(reference_images)}.",
                    },
                )
                return

            if method == "POST" and path == "/api/generate-video":
                session_user = get_user_by_session(conn, self.bearer_token())
                if not session_user:
                    self.send_json(401, {"authenticated": False, "message": "Please sign in before generating videos"})
                    return
                user_id = session_user["id"]
                template_id = payload.get("templateId")
                prompt = str(payload.get("prompt") or "").strip()
                settings = payload.get("settings") or {}
                reference_images = payload.get("referenceImages") or []
                if len(prompt) > MAX_PROMPT_LENGTH:
                    self.send_json(400, {"error": "Prompt too long", "message": "Prompt too long"})
                    return
                if template_id and template_modality(conn, template_id) != "video":
                    self.send_json(400, {"error": "Invalid template modality", "message": "Use the image generation endpoint for image templates"})
                    return

                if not prompt:
                    self.send_json(400, {"error": "Prompt required", "message": "Prompt is required"})
                    return
                if not isinstance(reference_images, list) or any(not isinstance(item, dict) for item in reference_images):
                    self.send_json(400, {"error": "Invalid reference images", "message": "Reference images must be a list of objects"})
                    return
                if len(reference_images) > MAX_REFERENCE_IMAGE_COUNT:
                    self.send_json(400, {"error": "Too many reference images", "message": f"Max {MAX_REFERENCE_IMAGE_COUNT} reference images"})
                    return
                try:
                    validate_reference_images(reference_images)
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                api_key = effective_apimart_api_key(conn)
                base_url = effective_apimart_base_url(conn)
                if not api_key:
                    self.send_json(
                        503,
                        {
                            "error": "Video service is not configured",
                            "message": "Video service is not configured; no credits were charged.",
                            "refund": {"amount": 0, "refunded": False},
                        },
                    )
                    return

                route_id = model_route_id_from_value(conn, settings.get("model") or "wan2.6-i2v-flash")
                route_row = conn.execute("SELECT * FROM model_routes WHERE id = ?", (route_id,)).fetchone()
                if not route_row or route_row["modality"] != "video":
                    self.send_json(400, {"error": "Invalid model", "message": "Please choose a video model"})
                    return
                requested_mode = str(settings.get("mode") or ("image" if reference_images else "text")).strip().lower()
                if requested_mode == "text" and video_model_requires_reference(route_row):
                    self.send_json(
                        400,
                        {
                            "error": "Reference image required",
                            "message": "Current model requires image-to-video input. Upload a reference image or choose a text-to-video model.",
                        },
                    )
                    return
                duration_message = video_duration_error(route_row, settings.get("duration"))
                if duration_message:
                    self.send_json(400, {"error": duration_message, "message": duration_message})
                    return
                credit_cost, pricing_breakdown = calculate_video_credit_cost(route_row, settings)
                try:
                    ensure_sufficient_credits(conn, user_id, credit_cost)
                except ValueError as error:
                    self.send_json(402, client_error_payload(error, 402, extra={"creditCost": credit_cost}))
                    return

                try:
                    provider_payload = build_video_payload(route_row, settings, prompt, reference_images, api_key, base_url)
                    provider_response = call_json_api(
                        "POST",
                        f"{base_url}/v1/videos/generations",
                        headers={"Authorization": f"Bearer {api_key}"},
                        payload=provider_payload,
                        timeout=int(route_row["timeout_seconds"] or 90),
                    )
                except Exception as error:  # noqa: BLE001
                    self.send_json(
                        502,
                        {
                            "error": "Video job submit failed",
                            "message": "Video job submit failed; no credits were charged.",
                            "refund": {"amount": 0, "refunded": False},
                        },
                    )
                    return

                apimart_task_id = parse_apimart_task_id(provider_response)
                if not apimart_task_id:
                    self.send_json(
                        502,
                        {
                            "error": "Video job submit failed",
                            "message": "Video service did not return a task id; no credits were charged.",
                            "providerResponseSummary": safe_provider_response_summary(provider_response),
                        },
                    )
                    return

                job_id = uid("job")
                job_no = f"VID-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:4]}"
                reference_file_summary = [
                    {
                        "name": item.get("name"),
                        "mimeType": item.get("mimeType"),
                        "byteSize": item.get("byteSize"),
                    }
                    for item in reference_images
                ]
                stored_settings = {
                    **settings,
                    "model": route_row["route_code"],
                    "modelName": route_row["model_name"],
                    "count": 1,
                }
                request_payload = safe_generation_request_snapshot(
                    payload,
                    stored_settings,
                    reference_file_summary,
                    provider_payload,
                    pricing_breakdown,
                )
                provider_record = {
                    "apimartTaskId": apimart_task_id,
                    "submitResponse": provider_response,
                    "provider": "APIMart",
                }
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute(
                        """
                        INSERT INTO generation_jobs(
                            id, job_no, user_id, organization_id, template_id, model_route_id, status,
                            prompt_final, prompt_params_json, quality, aspect_ratio, size, output_count,
                            reference_mode, credit_cost, request_payload_json, provider_response_json,
                            queued_at, started_at, created_at, updated_at
                        )
                        VALUES (?, ?, ?, 'org_default', ?, ?, 'queued', ?, ?, ?, ?, ?, 1,
                                ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            job_id,
                            job_no,
                            user_id,
                            template_id,
                            route_id,
                            prompt,
                            json_dumps(payload.get("params") or {}),
                            settings.get("resolution") or settings.get("quality") or "720p",
                            settings.get("aspectRatio") or "16:9",
                            settings.get("resolution") or "720p",
                            "optional" if reference_images else "text-only",
                            credit_cost,
                            json_dumps(request_payload),
                            json_dumps(provider_record),
                            now(),
                            now(),
                            now(),
                            now(),
                        ),
                    )
                    charge_result = charge_generation_credits(
                        conn,
                        user_id,
                        job_id,
                        credit_cost,
                        {"jobNo": job_no, "pricing": pricing_breakdown, "templateId": template_id, "providerTaskId": apimart_task_id},
                    )
                    reference_assets = store_reference_images(conn, reference_images, job_id, user_id)
                    if reference_assets:
                        request_payload["referenceAssets"] = reference_assets
                        conn.execute(
                            "UPDATE generation_jobs SET request_payload_json = ?, updated_at = ? WHERE id = ?",
                            (json_dumps(request_payload), now(), job_id),
                        )
                    audit(
                        conn,
                        "video.generation.enqueue",
                        "generation_job",
                        job_id,
                        {"templateId": template_id, "taskId": apimart_task_id, "creditCost": credit_cost},
                    )
                    prune_account_job_history(conn, user_id, ACCOUNT_JOB_HISTORY_LIMIT)
                    conn.execute("COMMIT")
                except ValueError as error:
                    conn.execute("ROLLBACK")
                    self.send_json(400, client_error_payload(error, 400))
                    return
                except Exception:
                    conn.execute("ROLLBACK")
                    raise

                self.send_json(
                    202,
                    {
                        "jobId": job_id,
                        "jobNo": job_no,
                        "status": "queued",
                        "providerTaskId": apimart_task_id,
                        "creditCost": credit_cost,
                        "balanceAfter": charge_result["balance"],
                        "pricing": pricing_breakdown,
                        "referenceCount": len(reference_images),
                        "message": f"Video job queued. Charged {credit_cost} credits.",
                    },
                )
                return

            admin_user = None
            if path.startswith("/api/admin/"):
                admin_user = self.require_admin(conn)
                if not admin_user:
                    return
                if path not in {"/api/admin/state", "/api/admin/password"} and admin_password_must_change(conn, admin_user["id"]):
                    self.send_json(
                        403,
                        {
                            "error": "Admin password change required",
                            "message": "Change the default admin password before using the admin console.",
                        },
                    )
                    return

            if method == "GET" and path == "/api/admin/state":
                self.send_json(200, admin_state(conn, admin_user))
                return

            if method == "POST" and path == "/api/admin/password":
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    current_password = str(payload.get("currentPassword") or "")
                    new_password = validate_password(payload.get("newPassword"))
                    confirm_password = str(payload.get("confirmPassword") or "")
                    if new_password != confirm_password:
                        raise ValueError("New passwords do not match")
                    target_user_id = admin_user["id"] if admin_user else "user_admin"
                    if password_is_configured(conn, target_user_id) and not verify_password(conn, target_user_id, current_password):
                        raise ValueError("Current admin password is incorrect")
                    if current_password and hmac.compare_digest(current_password, new_password):
                        raise ValueError("New password must differ from current password")
                    store_password(conn, target_user_id, new_password, {"mustChange": False})
                    revoke_all_sessions_for_user(conn, target_user_id)
                    session = issue_session(conn, target_user_id)
                    audit(conn, "admin.password.update", "user", target_user_id, {"passwordUpdated": True})
                except ValueError as error:
                    conn.execute("ROLLBACK")
                    self.send_json(400, client_error_payload(error, 400))
                    return
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                conn.execute("COMMIT")
                refreshed_admin = get_user_by_session(conn, session["token"])
                self.send_json(
                    200,
                    {"ok": True, "message": "Admin password updated", "state": admin_state(conn, refreshed_admin)},
                    auth_cookie_headers(session),
                )
                return

            if method == "POST" and path == "/api/admin/sync-github":
                try:
                    require_admin_permission(conn, admin_user, "templates:sync")
                    require_admin_reauth(conn, admin_user, payload, "template repository sync", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                result = run_sync()
                audit(conn, "template.sync_github", "template_source", "src_awesome_gpt_image_2", result)
                self.send_json(200, {"ok": True, **result, "state": admin_state(conn, admin_user)})
                return

            if method == "POST" and path == "/api/admin/sync-video-templates":
                try:
                    require_admin_permission(conn, admin_user, "templates:sync")
                    require_admin_reauth(conn, admin_user, payload, "video template sync", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                result = run_video_sync()
                audit(conn, "template.sync_video_templates", "template_source", "src_apimart_video_templates", result)
                self.send_json(200, {"ok": True, **result, "state": admin_state(conn, admin_user)})
                return

            if method == "POST" and path == "/api/admin/templates":
                try:
                    require_admin_permission(conn, admin_user, "templates:write")
                    require_admin_reauth(conn, admin_user, payload, "template changes", self.admin_token_authenticated())
                    item = upsert_template_from_payload(conn, payload)
                except RequestRejected as error:
                    self.send_json(error.status, client_error_payload(error.message, error.status))
                    return
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                self.send_json(200, {"item": item})
                return

            if method == "PATCH" and path.startswith("/api/admin/templates/"):
                template_id = unquote(path.rsplit("/", 1)[-1])
                current = get_template(conn, template_id, include_private=True)
                if not current:
                    self.send_json(404, {"error": "Template not found"})
                    return
                try:
                    require_admin_permission(conn, admin_user, "templates:write")
                    require_admin_reauth(conn, admin_user, payload, "template changes", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                if set(payload).issubset({"status", "enabled", "featured", "creditCost", "sortScore"}):
                    try:
                        updates = []
                        values = []
                        if "enabled" in payload:
                            updates.append("status = ?")
                            values.append("enabled" if payload["enabled"] else "hidden")
                        if "status" in payload:
                            updates.append("status = ?")
                            values.append(validate_template_status(payload["status"]))
                        if "featured" in payload:
                            updates.append("featured = ?")
                            values.append(bool_int(payload["featured"]))
                        if "creditCost" in payload:
                            updates.append("credit_cost = ?")
                            values.append(bounded_int(payload["creditCost"], "Template credit cost", 0, 500))
                        if "sortScore" in payload:
                            updates.append("sort_score = ?")
                            values.append(bounded_float(payload["sortScore"], "Template sort score", -10000, 10000))
                    except ValueError as error:
                        self.send_json(400, client_error_payload(error, 400))
                        return
                    updates.append("updated_at = ?")
                    values.append(now())
                    values.append(template_id)
                    conn.execute(f"UPDATE templates SET {', '.join(updates)} WHERE id = ?", values)
                    audit(conn, "template.patch", "template", template_id, payload)
                    self.send_json(200, {"item": get_template(conn, template_id, include_private=True)})
                else:
                    payload["id"] = template_id
                    item = upsert_template_from_payload(conn, payload)
                    self.send_json(200, {"item": item})
                return

            if method == "DELETE" and path.startswith("/api/admin/templates/"):
                template_id = unquote(path.rsplit("/", 1)[-1])
                try:
                    require_admin_permission(conn, admin_user, "templates:write")
                    require_admin_reauth(conn, admin_user, payload, "template deletion", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                source = conn.execute(
                    """
                    SELECT ts.source_type FROM templates t
                    LEFT JOIN template_sources ts ON ts.id = t.source_id
                    WHERE t.id = ?
                    """,
                    (template_id,),
                ).fetchone()
                if not source:
                    self.send_json(404, {"error": "Template not found"})
                    return
                if source["source_type"] != "manual":
                    conn.execute("UPDATE templates SET status = 'archived', updated_at = ? WHERE id = ?", (now(), template_id))
                else:
                    conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
                audit(conn, "template.delete", "template", template_id)
                self.send_json(200, {"ok": True})
                return

            if method == "POST" and path == "/api/admin/jobs":
                try:
                    require_admin_permission(conn, admin_user, "jobs:write")
                    require_admin_reauth(conn, admin_user, payload, "admin job creation", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                template_id = payload.get("templateId")
                template = get_template(conn, template_id, include_private=True) if template_id else None
                route_id = model_route_id_from_value(conn, payload.get("model"))
                job_id = uid("job")
                job_no = f"JOB-{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:4]}"
                try:
                    credit_cost = bounded_int(payload.get("cost"), "Job credit cost", 0, 500, int((template or {}).get("creditCost") or 5))
                    prompt = bounded_text(
                        payload.get("prompt") or (template or {}).get("promptTemplate"),
                        "Job prompt",
                        MAX_PROMPT_LENGTH,
                        "Admin queued generation job",
                        required=True,
                    )
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute(
                        """
                        INSERT INTO generation_jobs(
                            id, job_no, user_id, organization_id, template_id, model_route_id, status,
                            prompt_final, prompt_params_json, quality, aspect_ratio, size, output_count,
                            reference_mode, credit_cost, request_payload_json, provider_response_json,
                            queued_at, created_at, updated_at
                        )
                        VALUES (?, ?, 'user_admin', 'org_default', ?, ?, 'queued', ?, '{}', 'high', '1:1',
                                '1024x1024', 1, 'optional', ?, '{}', '{}', ?, ?, ?)
                        """,
                        (
                            job_id,
                            job_no,
                            template_id,
                            route_id,
                            prompt,
                            credit_cost,
                            now(),
                            now(),
                            now(),
                        ),
                    )
                    charge_result = charge_generation_credits(
                        conn,
                        "user_admin",
                        job_id,
                        credit_cost,
                        {"jobNo": job_no, "source": "admin"},
                    )
                    audit(conn, "generation.admin_create", "generation_job", job_id, {"creditCost": credit_cost})
                    conn.execute("COMMIT")
                except ValueError as error:
                    conn.execute("ROLLBACK")
                    self.send_json(400, client_error_payload(error, 400))
                    return
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                self.send_json(200, {"ok": True, "jobId": job_id, "jobNo": job_no, "balanceAfter": charge_result["balance"]})
                return

            if method == "PATCH" and path.startswith("/api/admin/jobs/"):
                job_id = unquote(path.rsplit("/", 1)[-1])
                status = payload.get("status")
                if status not in {"queued", "running", "success", "failed", "review", "cancelled"}:
                    self.send_json(400, {"error": "Invalid status"})
                    return
                try:
                    require_admin_permission(conn, admin_user, "jobs:write")
                    require_admin_reauth(conn, admin_user, payload, "job status changes", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                job = conn.execute("SELECT * FROM generation_jobs WHERE id = ?", (job_id,)).fetchone()
                if not job:
                    self.send_json(404, {"error": "Job not found"})
                    return
                try:
                    validate_job_status_transition(job["status"], status)
                except ValueError as error:
                    self.send_json(409, client_error_payload(error, 409, fallback="Conflict"))
                    return

                refund_result = {"amount": 0, "balance": 0, "refunded": False}
                charge_result = {"amount": 0, "balance": 0}
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    if job["status"] == "failed" and status in {"queued", "running", "success", "review"}:
                        charge_result = charge_generation_credits(
                            conn,
                            job["user_id"],
                            job_id,
                            int(job["credit_cost"] or 0),
                            {"jobNo": job["job_no"], "retry": True, "nextStatus": status},
                        )

                    fields = ["status = ?", "updated_at = ?"]
                    values = [status, now()]
                    if status == "success":
                        fields.extend(["finished_at = ?", "latency_ms = COALESCE(latency_ms, 12000)", "error_message = NULL"])
                        values.append(now())
                    elif status == "failed":
                        fields.append("error_message = ?")
                        values.append(payload.get("error") or "Generation failed; credits will be refunded based on ledger")
                    elif status == "review":
                        fields.append("error_message = NULL")
                    values.append(job_id)
                    conn.execute(f"UPDATE generation_jobs SET {', '.join(fields)} WHERE id = ?", values)

                    if status == "failed":
                        refund_result = refund_failed_generation_credits(conn, job_id, reason="generation_failed_refund")

                    audit(
                        conn,
                        "generation.status_update",
                        "generation_job",
                        job_id,
                        {"status": status, "refund": refund_result, "charge": charge_result},
                    )
                    conn.execute("COMMIT")
                except ValueError as error:
                    conn.execute("ROLLBACK")
                    self.send_json(400, client_error_payload(error, 400))
                    return
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                self.send_json(200, {"ok": True, "refund": refund_result, "charge": charge_result})
                return

            if method == "POST" and path == "/api/admin/jobs/retry-failed":
                try:
                    require_admin_permission(conn, admin_user, "jobs:write")
                    require_admin_reauth(conn, admin_user, payload, "bulk job retry", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                rows = conn.execute("SELECT * FROM generation_jobs WHERE status = 'failed'").fetchall()
                retried = 0
                skipped = 0
                charged = 0
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    for job in rows:
                        try:
                            charge = charge_generation_credits(
                                conn,
                                job["user_id"],
                                job["id"],
                                int(job["credit_cost"] or 0),
                                {"jobNo": job["job_no"], "retry": True, "source": "bulk_retry"},
                            )
                        except ValueError:
                            skipped += 1
                            continue
                        charged += int(charge.get("amount") or 0)
                        retried += 1
                        conn.execute(
                            "UPDATE generation_jobs SET status = 'queued', error_message = NULL, updated_at = ? WHERE id = ?",
                            (now(), job["id"]),
                        )
                    audit(conn, "generation.retry_failed", "generation_job", "failed", {"count": retried, "skipped": skipped, "charged": charged})
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                self.send_json(200, {"count": retried, "skipped": skipped, "charged": charged})
                return

            if method == "DELETE" and path == "/api/admin/jobs/completed":
                try:
                    require_admin_permission(conn, admin_user, "jobs:write")
                    require_admin_reauth(conn, admin_user, payload, "completed job cleanup", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                row = conn.execute("SELECT COUNT(*) AS c FROM generation_jobs WHERE status = 'success'").fetchone()
                conn.execute("DELETE FROM generation_jobs WHERE status = 'success'")
                audit(conn, "generation.clear_success", "generation_job", "success", {"count": row["c"]})
                self.send_json(200, {"count": row["c"]})
                return

            if method == "POST" and path == "/api/admin/models":
                try:
                    require_admin_permission(conn, admin_user, "models:write")
                    require_admin_reauth(conn, admin_user, payload, "model route changes", self.admin_token_authenticated())
                    normalized = normalize_model_route_payload(payload)
                    if conn.execute("SELECT 1 FROM model_routes WHERE route_code = ? LIMIT 1", (normalized["routeCode"],)).fetchone():
                        raise ValueError("Model route code already exists")
                    provider = (
                        conn.execute("SELECT id FROM model_providers WHERE id = 'provider_openai_compatible' LIMIT 1").fetchone()
                        or conn.execute("SELECT id FROM model_providers WHERE id = 'provider_apimart' LIMIT 1").fetchone()
                    )
                    if not provider:
                        raise ValueError("No model provider is configured")
                    route_id = uid("route")
                    conn.execute(
                        """
                        INSERT INTO model_routes(
                            id, provider_id, route_code, display_name, model_name, modality, quality,
                            supported_sizes_json, supported_ratios_json, default_size, default_ratio,
                            credit_cost, priority, timeout_seconds, retry_limit, success_rate, avg_latency_ms,
                            status, metadata_json, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                ?, 50, ?, ?, 0, 0, ?, '{}', ?, ?)
                        """,
                        (
                            route_id,
                            provider["id"],
                            normalized["routeCode"],
                            normalized["name"],
                            normalized["modelName"],
                            normalized["modality"],
                            normalized["quality"],
                            json_dumps(normalized["sizes"]),
                            json_dumps(normalized["ratios"]),
                            normalized["defaultSize"],
                            normalized["defaultRatio"],
                            normalized["cost"],
                            normalized["timeoutSeconds"],
                            normalized["retryLimit"],
                            normalized["status"],
                            now(),
                            now(),
                        ),
                    )
                    audit(conn, "model_route.create", "model_route", route_id, normalized)
                except RequestRejected as error:
                    self.send_json(error.status, client_error_payload(error.message, error.status))
                    return
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                self.send_json(200, {"ok": True, "item": normalized})
                return

            if method == "PATCH" and path.startswith("/api/admin/models/"):
                route_value = unquote(path.rsplit("/", 1)[-1])
                route_id = model_route_id_from_value(conn, route_value)
                if not route_id:
                    self.send_json(404, {"error": "Model route not found"})
                    return
                current = conn.execute("SELECT * FROM model_routes WHERE id = ? LIMIT 1", (route_id,)).fetchone()
                try:
                    require_admin_permission(conn, admin_user, "models:write")
                    require_admin_reauth(conn, admin_user, payload, "model route changes", self.admin_token_authenticated())
                    if set(payload).issubset({"enabled"}):
                        conn.execute(
                            "UPDATE model_routes SET status = ?, updated_at = ? WHERE id = ?",
                            ("active" if payload["enabled"] else "disabled", now(), route_id),
                        )
                        normalized = {"enabled": bool(payload["enabled"])}
                    else:
                        normalized = normalize_model_route_payload(payload, current)
                        duplicate = conn.execute(
                            "SELECT 1 FROM model_routes WHERE route_code = ? AND id != ? LIMIT 1",
                            (normalized["routeCode"], route_id),
                        ).fetchone()
                        if duplicate:
                            raise ValueError("Model route code already exists")
                        conn.execute(
                            """
                            UPDATE model_routes
                            SET route_code = ?,
                                display_name = ?,
                                model_name = ?,
                                modality = ?,
                                quality = ?,
                                supported_sizes_json = ?,
                                supported_ratios_json = ?,
                                default_size = ?,
                                default_ratio = ?,
                                credit_cost = ?,
                                timeout_seconds = ?,
                                retry_limit = ?,
                                status = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                normalized["routeCode"],
                                normalized["name"],
                                normalized["modelName"],
                                normalized["modality"],
                                normalized["quality"],
                                json_dumps(normalized["sizes"]),
                                json_dumps(normalized["ratios"]),
                                normalized["defaultSize"],
                                normalized["defaultRatio"],
                                normalized["cost"],
                                normalized["timeoutSeconds"],
                                normalized["retryLimit"],
                                normalized["status"],
                                now(),
                                route_id,
                            ),
                        )
                    audit(conn, "model_route.patch", "model_route", route_id, normalized)
                except RequestRejected as error:
                    self.send_json(error.status, client_error_payload(error.message, error.status))
                    return
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                self.send_json(200, {"ok": True})
                return

            if method == "DELETE" and path.startswith("/api/admin/models/"):
                route_value = unquote(path.rsplit("/", 1)[-1])
                route_id = model_route_id_from_value(conn, route_value)
                if not route_id:
                    self.send_json(404, {"error": "Model route not found"})
                    return
                try:
                    require_admin_permission(conn, admin_user, "models:write")
                    require_admin_reauth(conn, admin_user, payload, "model route deletion", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                referenced = (
                    conn.execute("SELECT 1 FROM generation_jobs WHERE model_route_id = ? LIMIT 1", (route_id,)).fetchone()
                    or conn.execute("SELECT 1 FROM templates WHERE default_model_route_id = ? LIMIT 1", (route_id,)).fetchone()
                )
                if referenced:
                    conn.execute(
                        "UPDATE model_routes SET status = ?, updated_at = ? WHERE id = ?",
                        ("disabled", now(), route_id),
                    )
                    mode = "disabled"
                else:
                    conn.execute("DELETE FROM model_routes WHERE id = ?", (route_id,))
                    mode = "deleted"
                audit(conn, "model_route.delete", "model_route", route_id, {"mode": mode})
                self.send_json(200, {"ok": True, "mode": mode})
                return

            if method == "POST" and path == "/api/admin/credits/grant":
                transaction_started = False
                try:
                    require_admin_permission(conn, admin_user, "credits:grant")
                    require_admin_reauth(conn, admin_user, payload, "credit grants", self.admin_token_authenticated())
                    user_id = str(payload.get("userId") or "").strip()
                    if not user_id:
                        raise ValueError("Target user is required")
                    target_user = conn.execute("SELECT id FROM users WHERE id = ? AND status != 'disabled' LIMIT 1", (user_id,)).fetchone()
                    if not target_user:
                        raise ValueError("Target user does not exist")
                    try:
                        amount = int(payload.get("amount"))
                    except (TypeError, ValueError) as error:
                        raise ValueError("Credit amount must be an integer") from error
                    if amount < 1 or amount > MAX_ADMIN_CREDIT_GRANT:
                        raise ValueError(f"Credit amount must be between 1 and {MAX_ADMIN_CREDIT_GRANT}")
                    reason_text = str(payload.get("reason") or "").strip()
                    if not reason_text or len(reason_text) > 200:
                        raise ValueError("Grant reason is required and must be 200 characters or less")
                    conn.execute("BEGIN IMMEDIATE")
                    transaction_started = True
                    account = conn.execute("SELECT * FROM credit_accounts WHERE user_id = ?", (user_id,)).fetchone()
                    if not account:
                        account_id = uid("ca")
                        conn.execute(
                            "INSERT INTO credit_accounts(id, user_id, balance, lifetime_granted, updated_at) VALUES (?, ?, 0, 0, ?)",
                            (account_id, user_id, now()),
                        )
                        account = conn.execute("SELECT * FROM credit_accounts WHERE user_id = ?", (user_id,)).fetchone()
                    new_balance = int(account["balance"] or 0) + amount
                    conn.execute(
                        "UPDATE credit_accounts SET balance = ?, lifetime_granted = lifetime_granted + ?, updated_at = ? WHERE id = ?",
                        (new_balance, amount, now(), account["id"]),
                    )
                    conn.execute(
                        """
                        INSERT INTO credit_ledger(
                            id, account_id, user_id, direction, amount, balance_after, reason,
                            reference_type, reference_id, operator_user_id, metadata_json, created_at
                        )
                        VALUES (?, ?, ?, 'credit', ?, ?, 'admin_grant', 'admin', 'manual', ?, ?, ?)
                        """,
                        (
                            uid("ledger"),
                            account["id"],
                            user_id,
                            amount,
                            new_balance,
                            admin_user["id"] if admin_user else "user_admin",
                            json_dumps({"reason": reason_text}),
                            now(),
                        ),
                    )
                    audit(conn, "credit.grant", "user", user_id, {"amount": amount, "reason": reason_text, "operator": admin_user["id"] if admin_user else "user_admin"})
                    conn.execute("COMMIT")
                    transaction_started = False
                except RequestRejected as error:
                    if transaction_started:
                        conn.execute("ROLLBACK")
                    self.send_json(error.status, client_error_payload(error.message, error.status))
                    return
                except ValueError as error:
                    if transaction_started:
                        conn.execute("ROLLBACK")
                    self.send_json(400, client_error_payload(error, 400))
                    return
                except Exception:
                    if transaction_started:
                        conn.execute("ROLLBACK")
                    raise
                self.send_json(200, {"ok": True, "balance": new_balance})
                return

            if method == "PATCH" and path.startswith("/api/admin/users/"):
                user_id = unquote(path.rsplit("/", 1)[-1])
                try:
                    require_admin_permission(conn, admin_user, "users:write")
                    require_admin_reauth(conn, admin_user, payload, "user account changes", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                target_user = conn.execute("SELECT id, membership_level FROM users WHERE id = ? LIMIT 1", (user_id,)).fetchone()
                if not target_user:
                    self.send_json(404, {"error": "User not found", "message": "User not found"})
                    return
                before = {"membershipLevel": target_user["membership_level"]}
                after = {}
                if "membershipLevel" in payload:
                    membership_level = str(payload.get("membershipLevel") or "").strip()
                    if membership_level not in ALLOWED_MEMBERSHIP_LEVELS:
                        self.send_json(400, {"error": "Invalid membership level", "message": "Invalid membership level"})
                        return
                    conn.execute(
                        "UPDATE users SET membership_level = ?, updated_at = ? WHERE id = ?",
                        (membership_level, now(), user_id),
                    )
                    after["membershipLevel"] = membership_level
                audit(conn, "user.patch", "user", user_id, after, before)
                self.send_json(200, {"ok": True})
                return

            if method == "POST" and path == "/api/admin/reviews":
                try:
                    require_admin_permission(conn, admin_user, "reviews:write")
                    require_admin_reauth(conn, admin_user, payload, "review item creation", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                template_id = payload.get("templateId")
                try:
                    risk = validate_review_risk(payload.get("risk"))
                    reason = bounded_text(payload.get("reason"), "Review reason", 500, "Admin created review item")
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                review_id = uid("review")
                conn.execute(
                    """
                    INSERT INTO review_items(
                        id, subject_type, subject_id, user_id, risk_level, reason, status, metadata_json, created_at
                    )
                    VALUES (?, 'template', ?, 'user_admin', ?, ?, 'pending', '{}', ?)
                    """,
                    (
                        review_id,
                        template_id or "manual-review",
                        risk,
                        reason,
                        now(),
                    ),
                )
                audit(conn, "review.create", "review_item", review_id, {"risk": risk, "subjectId": template_id or "manual-review"})
                self.send_json(200, {"ok": True})
                return

            if method == "POST" and path == "/api/admin/reviews/approve-low-risk":
                try:
                    require_admin_permission(conn, admin_user, "reviews:write")
                    require_admin_reauth(conn, admin_user, payload, "bulk review approval", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM review_items WHERE risk_level = 'low' AND status = 'pending'"
                ).fetchone()
                conn.execute(
                    """
                    UPDATE review_items
                    SET status = 'approved', reviewer_user_id = 'user_admin', reviewed_at = ?, decision_note = 'Bulk approved low risk review items'
                    WHERE risk_level = 'low' AND status = 'pending'
                    """,
                    (now(),),
                )
                audit(conn, "review.approve_low_risk", "review_item", "low-risk", {"count": row["c"]})
                self.send_json(200, {"count": row["c"]})
                return

            if method == "PATCH" and path.startswith("/api/admin/reviews/"):
                review_id = unquote(path.rsplit("/", 1)[-1])
                try:
                    status = validate_review_status(payload.get("status"))
                    note = bounded_text(payload.get("note"), "Review note", 500)
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                try:
                    require_admin_permission(conn, admin_user, "reviews:write")
                    require_admin_reauth(conn, admin_user, payload, "review status changes", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                conn.execute(
                    """
                    UPDATE review_items
                    SET status = ?, reviewer_user_id = 'user_admin', reviewed_at = ?, decision_note = ?
                    WHERE id = ?
                    """,
                    (status, now(), note, review_id),
                )
                audit(conn, "review.status_update", "review_item", review_id, {"status": status})
                self.send_json(200, {"ok": True})
                return

            if method == "POST" and path == "/api/admin/api-settings/test":
                try:
                    require_admin_permission(conn, admin_user, "payments:config")
                    require_admin_reauth(conn, admin_user, payload, "API connection testing", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                provider = conn.execute("SELECT * FROM model_providers WHERE id = 'provider_apimart'").fetchone()
                provider_id = "provider_apimart" if provider else "provider_openai_compatible"
                provider = conn.execute("SELECT * FROM model_providers WHERE id = ?", (provider_id,)).fetchone()
                metadata = json_loads(provider["metadata_json"], {}) if provider else {}
                test_result = test_apimart_connection(
                    conn,
                    api_key_override=payload.get("apiKey"),
                    base_url_override=payload.get("baseUrl"),
                )
                safe_test_result = sanitize_connection_test_result(test_result)
                metadata["lastConnectionTest"] = safe_test_result
                conn.execute(
                    """
                    UPDATE model_providers
                    SET health_status = ?,
                        last_checked_at = ?,
                        metadata_json = ?
                    WHERE id = ?
                    """,
                    (
                        "healthy" if test_result.get("ok") else "error",
                        test_result["checkedAt"],
                        json_dumps(metadata),
                        provider_id,
                    ),
                )
                audit(conn, "api_settings.test_connection", "model_provider", provider_id, safe_test_result)
                self.send_json(200, {"ok": bool(test_result.get("ok")), "test": safe_test_result, "state": admin_state(conn, admin_user)})
                return

            if method in {"PUT", "POST"} and path == "/api/admin/api-settings":
                try:
                    require_admin_permission(conn, admin_user, "payments:config")
                    require_admin_reauth(conn, admin_user, payload, "API settings changes", self.admin_token_authenticated())
                except (RequestRejected, ValueError) as error:
                    self.send_json(403, client_error_payload(error, 403, fallback="Access denied"))
                    return
                provider = conn.execute("SELECT * FROM model_providers WHERE id = 'provider_apimart'").fetchone()
                provider_id = "provider_apimart" if provider else "provider_openai_compatible"
                provider = conn.execute("SELECT * FROM model_providers WHERE id = ?", (provider_id,)).fetchone()
                metadata = json_loads(provider["metadata_json"], {}) if provider else {}
                previous_base_url = str((provider["base_url"] if provider else "") or "").strip().rstrip("/")
                api_key = str(payload.get("apiKey") or "").strip()
                clear_api_key = bool_int(payload.get("clearApiKey"))
                if clear_api_key:
                    metadata.pop("apiKey", None)
                    metadata.pop("apiKeyEncrypted", None)
                elif api_key:
                    set_metadata_secret(metadata, "apiKey", api_key)
                api_endpoint = str(payload.get("apiEndpoint") or "/api/generate-image").strip() or "/api/generate-image"
                balance_endpoint = str(payload.get("balanceEndpoint") or "/api/admin/model-balance").strip() or "/api/admin/model-balance"
                metadata["apiEndpoint"] = api_endpoint
                metadata["balanceEndpoint"] = balance_endpoint
                base_url = str(payload.get("baseUrl") or APIMART_BASE_URL).strip().rstrip("/") or APIMART_BASE_URL
                try:
                    assert_public_http_url(base_url)
                except RuntimeError:
                    self.send_json(400, {"error": "Invalid base URL", "message": "API base URL must be a public http(s) endpoint"})
                    return
                if clear_api_key or api_key or previous_base_url != base_url:
                    metadata.pop("lastConnectionTest", None)
                key_configured = bool(APIMART_API_KEY or metadata_secret_configured(metadata, "apiKey"))
                conn.execute(
                    """
                    UPDATE model_providers
                    SET base_url = ?,
                        server_key_status = ?,
                        metadata_json = ?,
                        last_checked_at = ?
                    WHERE id = ?
                    """,
                    (
                        base_url,
                        "env_configured" if APIMART_API_KEY else ("configured" if key_configured else "not_configured"),
                        json_dumps(metadata),
                        now(),
                        provider_id,
                    ),
                )
                audit(conn, "api_settings.update", "model_provider", provider_id, {"baseUrl": base_url, "keyConfigured": key_configured})
                self.send_json(200, {"ok": True, "state": admin_state(conn, admin_user)})
                return

            if method in {"PUT", "POST"} and path == "/api/admin/settings":
                try:
                    require_admin_permission(conn, admin_user, "settings:write")
                    require_admin_reauth(conn, admin_user, payload, "site settings changes", self.admin_token_authenticated())
                    settings = update_settings(conn, payload)
                except RequestRejected as error:
                    self.send_json(error.status, client_error_payload(error.message, error.status))
                    return
                except ValueError as error:
                    self.send_json(400, client_error_payload(error, 400))
                    return
                self.send_json(200, {"settings": settings})
                return

            self.send_json(404, {"error": "API route not found", "path": path})

    def serve_static(self, request_path: str) -> None:
        rel = unquote(request_path.lstrip("/")) or "index.html"
        if rel.endswith("/"):
            rel += "index.html"
        root = ROOT.resolve()
        webapp_root = WEBAPP_ROOT.resolve()
        preferred = (WEBAPP_ROOT / rel).resolve()
        fallback = (ROOT / rel).resolve()
        if str(preferred).startswith(str(webapp_root)) and preferred.exists() and preferred.is_file():
            path = preferred
        else:
            path = fallback
        if (
            not str(path).startswith(str(root))
            or not path.exists()
            or not path.is_file()
            or not is_public_static_request(rel, path)
        ):
            self.send_json(404, {"error": "Not found"})
            return
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        cache = "no-store" if path.suffix.lower() in {".html", ".js", ".css"} else "public, max-age=86400"
        self.send_binary(200, path.read_bytes(), mime, cache=cache)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        sanitized_args = tuple(sanitize_request_target(arg) if isinstance(arg, str) else arg for arg in args)
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % sanitized_args))


def run_sync() -> dict:
    if not REPO_SYNC_SCRIPT.exists():
        raise RuntimeError(f"Missing sync script: {REPO_SYNC_SCRIPT}")
    if not SYNC_SCRIPT.exists():
        raise RuntimeError(f"Missing database sync script: {SYNC_SCRIPT}")
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    repo = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_SYNC_SCRIPT),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )
    if repo.returncode != 0:
        message = (repo.stderr or repo.stdout or "GitHub sync failed").strip()
        raise RuntimeError(f"GitHub sync failed: {message}")
    db_sync = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )
    if db_sync.returncode != 0:
        message = (db_sync.stderr or db_sync.stdout or "Database sync failed").strip()
        raise RuntimeError(f"Database sync failed: {message}")
    return {
        "repoOutput": repo.stdout.strip()[-2000:],
        "repoError": repo.stderr.strip()[-2000:],
        "dbOutput": db_sync.stdout.strip()[-2000:],
        "dbError": db_sync.stderr.strip()[-2000:],
        "syncedAt": now(),
    }


def run_video_sync() -> dict:
    if not VIDEO_SYNC_SCRIPT.exists():
        raise RuntimeError(f"Missing video sync script: {VIDEO_SYNC_SCRIPT}")
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    result = subprocess.run(
        [sys.executable, str(VIDEO_SYNC_SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Video template sync failed").strip())
    return {
        "dbOutput": result.stdout.strip()[-2000:],
        "syncedAt": now(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI Workshop local API/static server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4178)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    validate_runtime_security_config()
    with connect(args.db) as conn:
        ensure_credit_ledger_schema(conn)
        ensure_auth_schema(conn)
        ensure_admin_password(conn)
        ensure_apimart_official_route(conn)
        ensure_image_route_defaults(conn)
        migrate_plaintext_secrets(conn)

    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    server.db_path = args.db  # type: ignore[attr-defined]
    print(f"AI Workshop server: http://{args.host}:{args.port}/index.html")
    print(f"SQLite database: {args.db}")
    server.serve_forever()


if __name__ == "__main__":
    main()
