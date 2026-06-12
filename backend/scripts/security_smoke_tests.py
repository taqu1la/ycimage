from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import sqlite3
import threading
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import server  # noqa: E402

DB_PATH = ROOT / "backend" / "data" / "security_smoke.db"
BASE_URL = os.environ.get("YCIMAGE_SECURITY_TEST_BASE_URL", "http://127.0.0.1:4179")
ADMIN_PASSWORD = "Admin123457"
CSRF_BY_COOKIE: dict[str, str] = {}


def admin_payload(payload: dict | None = None, password: str = ADMIN_PASSWORD) -> dict:
    return {**(payload or {}), "adminPassword": password}


def request(
    method: str,
    path: str,
    body: dict | None = None,
    headers: dict | None = None,
    default_xhr: bool = True,
) -> tuple[int, dict | str, dict]:
    data = None
    req_headers = {"Accept": "application/json", "Connection": "close", **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
        if default_xhr:
            req_headers.setdefault("X-Requested-With", "XMLHttpRequest")
        cookie = req_headers.get("Cookie", "")
        csrf = CSRF_BY_COOKIE.get(cookie, "")
        if csrf and default_xhr:
            req_headers.setdefault("X-CSRF-Token", csrf)
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            response_headers = dict(response.headers)
            response_headers["__set_cookie_all__"] = response.headers.get_all("Set-Cookie") or []
            return response.status, parse_body(raw), response_headers
    except urllib.error.HTTPError as error:
        raw = error.read()
        error_headers = dict(error.headers)
        error_headers["__set_cookie_all__"] = error.headers.get_all("Set-Cookie") or []
        return error.code, parse_body(raw), error_headers


def raw_request(method: str, path: str, body: bytes, headers: dict | None = None) -> tuple[int, dict | str, dict]:
    req_headers = {"Connection": "close", **(headers or {})}
    cookie = req_headers.get("Cookie", "")
    csrf = CSRF_BY_COOKIE.get(cookie, "")
    if csrf and req_headers.get("X-Requested-With"):
        req_headers.setdefault("X-CSRF-Token", csrf)
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            response_headers = dict(response.headers)
            response_headers["__set_cookie_all__"] = response.headers.get_all("Set-Cookie") or []
            return response.status, parse_body(raw), response_headers
    except urllib.error.HTTPError as error:
        raw = error.read()
        error_headers = dict(error.headers)
        error_headers["__set_cookie_all__"] = error.headers.get_all("Set-Cookie") or []
        return error.code, parse_body(raw), error_headers


def start_server() -> ThreadingHTTPServer:
    parsed = urllib.parse.urlparse(BASE_URL)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 4179
    httpd = ThreadingHTTPServer((host, port), server.AppHandler)
    httpd.db_path = DB_PATH  # type: ignore[attr-defined]
    thread = threading.Thread(target=httpd.serve_forever, name="ycimage-security-smoke", daemon=True)
    thread.start()

    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            status, _, _ = request("GET", "/api/health")
            if status == 200:
                return httpd
        except Exception:
            pass
        time.sleep(0.1)
    httpd.shutdown()
    raise RuntimeError(f"Security smoke test server did not start at {BASE_URL}")


def parse_body(raw: bytes):
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def header_values(headers: dict, name: str) -> list[str]:
    values = []
    for key, value in headers.items():
        if key.lower() == name.lower():
            values.append(value)
    return values


def capture_auth_cookies(headers: dict) -> str:
    set_cookies = headers.get("__set_cookie_all__") or header_values(headers, "Set-Cookie")
    session_cookie = ""
    csrf_cookie = ""
    csrf_token = ""
    for cookie in set_cookies:
        first = cookie.split(";", 1)[0]
        if first.startswith("ycimage_session="):
            session_cookie = first
        if first.startswith("ycimage_csrf="):
            csrf_cookie = first
            csrf_token = first.split("=", 1)[1]
    assert session_cookie, headers
    assert csrf_token, headers
    full_cookie = f"{session_cookie}; {csrf_cookie}"
    CSRF_BY_COOKIE[session_cookie] = csrf_token
    CSRF_BY_COOKIE[full_cookie] = csrf_token
    return full_cookie


def init_db() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript((ROOT / "backend" / "schema.sql").read_text(encoding="utf-8"))
        conn.executescript(
            """
            INSERT INTO organizations(id, name, slug, status) VALUES ('org_default', 'YCImage', 'ycimage', 'active');
            INSERT INTO roles(id, name, permissions_json) VALUES
                ('role_user', 'user', '[]'),
                ('role_template_ops', 'template_ops', '["templates:read","templates:write"]'),
                ('role_admin', 'admin', '["admin:*"]');
            INSERT INTO users(id, organization_id, display_name, email, role_id, status)
            VALUES
                ('user_a', 'org_default', 'User A', 'a@example.com', 'role_user', 'active'),
                ('user_b', 'org_default', 'User B', 'b@example.com', 'role_user', 'active'),
                ('user_template_ops', 'org_default', 'Template Ops', 'ops@example.com', 'role_template_ops', 'active'),
                ('user_admin', 'org_default', 'Admin', 'admin@example.com', 'role_admin', 'active');
            INSERT INTO credit_accounts(id, user_id, balance, lifetime_granted)
            VALUES
                ('ca_a', 'user_a', 20, 20),
                ('ca_b', 'user_b', 20, 20),
                ('ca_template_ops', 'user_template_ops', 20, 20),
                ('ca_admin', 'user_admin', 999, 999);
            INSERT INTO pricing_plans(id, code, name, plan_type, price_cents, credits, status)
            VALUES ('plan_pack', 'pack_200', 'Pack 200', 'credit_pack', 2900, 200, 'active');
            INSERT INTO model_providers(id, name, provider_type, base_url, status)
            VALUES ('provider_apimart', 'APIMart', 'apimart', 'https://api.apimart.ai', 'active');
            INSERT INTO model_routes(
                id, provider_id, route_code, display_name, model_name, modality, quality,
                supported_sizes_json, supported_ratios_json, credit_cost, status
            )
            VALUES (
                'route_img', 'provider_apimart', 'gpt-image-2-high', 'Image', 'gpt-image-2',
                'image', 'high', '["1024x1024"]', '["1:1"]', 5, 'active'
            );
            INSERT INTO templates(id, title, prompt_template, status, credit_cost, default_model_route_id, created_by)
            VALUES ('tpl_img', 'Template', 'Prompt', 'enabled', 5, 'route_img', 'user_admin');
            INSERT INTO generation_jobs(
                id, job_no, user_id, organization_id, template_id, model_route_id, status,
                prompt_final, quality, aspect_ratio, size, output_count, credit_cost
            )
            VALUES
                ('job_a', 'JOB-A', 'user_a', 'org_default', 'tpl_img', 'route_img', 'success', 'private prompt A', 'high', '1:1', '1024x1024', 1, 5),
                ('job_b', 'JOB-B', 'user_b', 'org_default', 'tpl_img', 'route_img', 'success', 'private prompt B', 'high', '1:1', '1024x1024', 1, 5);
            INSERT INTO assets(id, owner_user_id, asset_type, storage_provider, storage_path, mime_type, byte_size, status)
            VALUES
                ('asset_private_a', 'user_a', 'generated_image', 'database', 'database://asset_private_a', 'image/png', 8, 'active'),
                ('asset_private_b', 'user_b', 'generated_image', 'database', 'database://asset_private_b', 'image/png', 8, 'active'),
                ('asset_public', NULL, 'template_cover', 'database', 'database://asset_public', 'image/png', 8, 'active');
            INSERT INTO asset_blobs(asset_id, content, byte_size, sha256)
            VALUES
                ('asset_private_a', X'89504E470D0A1A0A', 8, 'x'),
                ('asset_private_b', X'89504E470D0A1A0A', 8, 'x'),
                ('asset_public', X'89504E470D0A1A0A', 8, 'x');
            INSERT INTO generation_job_assets(job_id, asset_id, role, sort_order)
            VALUES
                ('job_a', 'asset_private_a', 'output', 0),
                ('job_b', 'asset_private_b', 'output', 0);
            """
        )
        server.ensure_auth_schema(conn)
        server.migrate_plaintext_secrets(conn)
        server.store_password(conn, "user_a", "Password1")
        server.store_password(conn, "user_b", "Password1")
        server.store_password(conn, "user_template_ops", "Password1")
        server.store_password(conn, "user_admin", "Password1")
        conn.commit()
    finally:
        conn.close()


def login(email: str) -> str:
    status, body, headers = request("POST", "/api/auth/password-login", {"email": email, "password": "Password1"})
    assert status == 200, body
    assert "token" not in body.get("session", {}), body.get("session")
    return capture_auth_cookies(headers)


def login_with_password(email: str, password: str) -> str:
    status, body, headers = request("POST", "/api/auth/password-login", {"email": email, "password": password})
    assert status == 200, body
    assert "token" not in body.get("session", {}), body.get("session")
    return capture_auth_cookies(headers)


def mpay_sign(params: dict, key: str) -> str:
    parts = []
    for name in sorted(params):
        if name in {"sign", "sign_type"}:
            continue
        value = params[name]
        if value in {None, ""} or isinstance(value, (dict, list, tuple, set)):
            continue
        parts.append(f"{name}={value}")
    return hashlib.md5(("&".join(parts) + key).encode("utf-8")).hexdigest()


def assert_runtime_security_config_validation() -> None:
    original = {
        "IS_PRODUCTION": server.IS_PRODUCTION,
        "YCIMAGE_SECRET_KEY": server.YCIMAGE_SECRET_KEY,
        "YCIMAGE_ADMIN_PASSWORD": server.YCIMAGE_ADMIN_PASSWORD,
        "YCIMAGE_ADMIN_TOKEN": server.YCIMAGE_ADMIN_TOKEN,
        "ALLOWED_CORS_ORIGINS": server.ALLOWED_CORS_ORIGINS,
        "SECURE_COOKIES": server.SECURE_COOKIES,
        "PAYMENT_PROVIDER_ENV": server.PAYMENT_PROVIDER_ENV,
        "MPAY_PID": server.MPAY_PID,
        "MPAY_KEY": server.MPAY_KEY,
        "MPAY_NOTIFY_URL": server.MPAY_NOTIFY_URL,
        "MPAY_RETURN_URL": server.MPAY_RETURN_URL,
    }
    try:
        server.IS_PRODUCTION = True
        server.YCIMAGE_SECRET_KEY = "short"
        server.YCIMAGE_ADMIN_PASSWORD = ""
        server.YCIMAGE_ADMIN_TOKEN = "weak"
        server.ALLOWED_CORS_ORIGINS = {"*", "http://localhost:4178", "http://ycimage.example"}
        server.SECURE_COOKIES = False
        server.PAYMENT_PROVIDER_ENV = "mpay"
        server.MPAY_PID = ""
        server.MPAY_KEY = ""
        server.MPAY_NOTIFY_URL = "http://ycimage.example/api/pay/notify/mpay"
        server.MPAY_RETURN_URL = "http://ycimage.example/account.html"
        try:
            server.validate_runtime_security_config()
            raise AssertionError("unsafe production config was accepted")
        except RuntimeError as error:
            message = str(error)
            assert "YCIMAGE_SECRET_KEY" in message, message
            assert "YCIMAGE_ADMIN_PASSWORD" in message, message
            assert "YCIMAGE_ADMIN_TOKEN" in message, message
            assert "Secure cookies" in message, message
            assert "localhost" in message, message
            assert "HTTPS" in message, message
            assert "MPAY_PID" in message, message
            assert "MPAY_NOTIFY_URL" in message, message
            assert "MPAY_RETURN_URL" in message, message

        server.YCIMAGE_SECRET_KEY = "x" * 32
        server.YCIMAGE_ADMIN_PASSWORD = ADMIN_PASSWORD
        server.YCIMAGE_ADMIN_TOKEN = "t" * 32
        server.ALLOWED_CORS_ORIGINS = {"https://ycimage.example"}
        server.SECURE_COOKIES = True
        server.PAYMENT_PROVIDER_ENV = "mpay"
        server.MPAY_PID = "pid"
        server.MPAY_KEY = "secret"
        server.MPAY_NOTIFY_URL = "https://ycimage.example/api/pay/notify/mpay"
        server.MPAY_RETURN_URL = "https://ycimage.example/account.html"
        server.validate_runtime_security_config()
    finally:
        for key, value in original.items():
            setattr(server, key, value)


def run() -> None:
    init_db()
    CSRF_BY_COOKIE.clear()
    assert_runtime_security_config_validation()
    server.PAYMENT_PROVIDER_ENV = "mpay"
    server.MPAY_BASE_URL = "https://mpay.example.test"
    server.MPAY_PID = "pid"
    server.MPAY_KEY = "secret"
    server.MPAY_OLD_KEYS = ["old-secret"]
    server.RATE_LIMIT_BUCKETS.clear()

    httpd = start_server()
    try:
        status, health, _ = request("GET", "/api/health")
        assert status == 200, health
        assert health == {"ok": True}, health
        status, _, headers = request("GET", "/index.html")
        csp = headers.get("Content-Security-Policy", "")
        assert status == 200, status
        assert "script-src 'self'" in csp, csp
        assert "object-src 'none'" in csp, csp
        assert "frame-ancestors 'none'" in csp, csp

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            issued = server.issue_mobile_code(conn, "13800138000", "register")
            stored_code = conn.execute(
                "SELECT code FROM auth_verification_codes WHERE mobile = ? ORDER BY created_at DESC LIMIT 1",
                ("13800138000",),
            ).fetchone()["code"]
            assert stored_code != issued["code"], stored_code
            assert str(stored_code).startswith("hmac_sha256:"), stored_code
            server.verify_mobile_code(conn, "13800138000", issued["code"], "register")
            try:
                server.verify_mobile_code(conn, "13800138000", issued["code"], "register")
                raise AssertionError("verification code was reusable")
            except ValueError:
                pass
            conn.execute(
                """
                INSERT INTO auth_verification_codes(id, mobile, purpose, code, expires_at, consumed_at, created_at)
                VALUES (?, '13800138001', 'register', '123456', ?, NULL, ?)
                """,
                (server.uid("sms"), "2999-01-01T00:00:00+00:00", server.now()),
            )
            server.verify_mobile_code(conn, "13800138001", "123456", "register")
            conn.commit()

        cookie_a = login("a@example.com")
        cookie_b = login("b@example.com")

        cookie_a_second = login("a@example.com")
        status, body, _ = request("POST", "/api/auth/logout-all", {}, headers={"Cookie": cookie_a})
        assert status == 200, body
        status, body, _ = request("GET", "/api/account/dashboard", headers={"Cookie": cookie_a})
        assert status == 401, body
        status, body, _ = request("GET", "/api/account/dashboard", headers={"Cookie": cookie_a_second})
        assert status == 401, body
        cookie_a = login("a@example.com")

        status, body, headers = request(
            "POST",
            "/api/account/password",
            {
                "currentPassword": "Password1",
                "newPassword": "Password2A",
                "confirmPassword": "Password2A",
            },
            headers={"Cookie": cookie_a},
        )
        assert status == 200, body
        old_cookie_a = cookie_a
        cookie_a = capture_auth_cookies(headers)
        status, body, _ = request("GET", "/api/account/dashboard", headers={"Cookie": old_cookie_a})
        assert status == 401, body
        status, body, _ = request("GET", "/api/account/dashboard", headers={"Cookie": cookie_a})
        assert status == 200, body
        cookie_a_second = login_with_password("a@example.com", "Password2A")
        status, body, headers = request(
            "POST",
            "/api/account/password",
            {
                "currentPassword": "Password2A",
                "newPassword": "Password1A2",
                "confirmPassword": "Password1A2",
            },
            headers={"Cookie": cookie_a},
        )
        assert status == 200, body
        cookie_a = capture_auth_cookies(headers)
        status, body, _ = request("GET", "/api/account/dashboard", headers={"Cookie": cookie_a_second})
        assert status == 401, body
        status, body, _ = request("GET", "/api/account/dashboard", headers={"Cookie": cookie_a})
        assert status == 200, body

        status, _, _ = request("GET", "/api/jobs/job_a")
        assert status == 401, status

        status, body, _ = request("GET", "/api/jobs/job_b", headers={"Cookie": cookie_a})
        assert status == 403, body

        status, _, _ = request("GET", "/api/assets/asset_private_b", headers={"Cookie": cookie_a})
        assert status == 403, status

        status, _, _ = request("GET", "/api/assets/asset_private_a")
        assert status == 401, status

        status, _, _ = request("GET", "/api/assets/asset_public")
        assert status == 200, status

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            server.store_password(conn, "user_admin", "Admin123456", {"mustChange": True, "bootstrapDefault": True})
            conn.commit()
        admin_cookie = login_with_password("admin@example.com", "Admin123456")
        status, admin_state, _ = request("GET", "/api/admin/state", headers={"Cookie": admin_cookie})
        assert status == 200, admin_state
        assert admin_state["security"]["adminPasswordMustChange"] is True, admin_state["security"]
        tiny_png = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii")
        status, body, _ = request("POST", "/api/admin/sync-video-templates", {}, headers={"Cookie": admin_cookie})
        assert status == 403, body
        status, body, _ = request(
            "POST",
            "/api/admin/password",
            {"currentPassword": "Admin123456", "newPassword": "Admin123457", "confirmPassword": "Admin123457"},
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        assert body["state"]["security"]["adminPasswordMustChange"] is False, body["state"]["security"]
        old_admin_cookie = admin_cookie
        admin_cookie = capture_auth_cookies(_)
        status, body, _ = request("GET", "/api/admin/state", headers={"Cookie": old_admin_cookie})
        assert status == 401, body
        status, body, _ = request("GET", "/api/admin/state", headers={"Cookie": admin_cookie})
        assert status == 200, body
        template_ops_cookie = login("ops@example.com")
        status, template_ops_state, _ = request("GET", "/api/admin/state", headers={"Cookie": template_ops_cookie})
        assert status == 200, template_ops_state
        assert template_ops_state["templates"], template_ops_state
        assert template_ops_state["users"] == [], template_ops_state["users"]
        assert template_ops_state["orders"] == [], template_ops_state["orders"]
        assert template_ops_state["api"]["keySource"] == "restricted", template_ops_state["api"]
        status, body, _ = request(
            "POST",
            "/api/admin/credits/grant",
            admin_payload({"userId": "user_a", "amount": 50, "reason": "template ops should not grant credits"}),
            headers={"Cookie": template_ops_cookie},
        )
        assert status == 403, body
        assert body["message"] == "Access denied", body
        assert "credits:grant" not in json.dumps(body), body

        status, body, _ = request(
            "POST",
            "/api/admin/credits/grant",
            {"userId": "user_a", "amount": 50, "reason": "non-admin attempt"},
            headers={"Cookie": cookie_a},
        )
        assert status == 401, body
        status, body, _ = request(
            "POST",
            "/api/admin/credits/grant",
            {"userId": "user_a", "amount": 50, "reason": "missing reauth"},
            headers={"Cookie": admin_cookie},
        )
        assert status == 403, body
        status, body, _ = request(
            "POST",
            "/api/admin/credits/grant",
            admin_payload({"userId": "user_a", "amount": 50}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        status, body, _ = request(
            "POST",
            "/api/admin/credits/grant",
            admin_payload({"userId": "user_a", "amount": -1, "reason": "invalid negative amount"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        status, body, _ = request(
            "POST",
            "/api/admin/credits/grant",
            admin_payload({"userId": "user_a", "amount": 50, "reason": "security smoke test grant"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        with sqlite3.connect(DB_PATH) as conn:
            balance = conn.execute("SELECT balance FROM credit_accounts WHERE user_id = 'user_a'").fetchone()[0]
            audit_rows = conn.execute("SELECT COUNT(*) FROM admin_audit_logs WHERE action='credit.grant' AND entity_id='user_a'").fetchone()[0]
            ledger_reason = conn.execute(
                "SELECT metadata_json FROM credit_ledger WHERE reason='admin_grant' AND user_id='user_a' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()[0]
        assert balance == 70, balance
        assert audit_rows == 1, audit_rows
        assert json.loads(ledger_reason)["reason"] == "security smoke test grant", ledger_reason

        status, body, _ = request(
            "POST",
            "/api/admin/models",
            admin_payload({"routeCode": "../bad", "name": "Bad", "modelName": "bad", "cost": -1}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        status, body, _ = request(
            "POST",
            "/api/admin/models",
            admin_payload({"routeCode": "custom-secure-route", "name": "Secure Route", "modelName": "secure-model", "quality": "medium", "cost": 7, "enabled": False}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/models/custom-secure-route",
            admin_payload({"cost": 9, "enabled": True, "quality": "high"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        status, body, _ = request("DELETE", "/api/admin/models/custom-secure-route", admin_payload(), headers={"Cookie": admin_cookie})
        assert status == 200, body
        assert body["mode"] in {"deleted", "disabled"}, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/users/user_a",
            admin_payload({"membershipLevel": "root"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/users/user_a",
            admin_payload({"membershipLevel": "monthly"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        status, body, _ = request(
            "PUT",
            "/api/admin/settings",
            admin_payload({"siteName": "YCImage", "defaultModel": "missing-model", "defaultQuality": "medium"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        status, body, _ = request(
            "PUT",
            "/api/admin/settings",
            admin_payload({"siteName": "YCImage", "homeTemplateLimit": 999, "defaultModel": "gpt-image-2-high", "defaultQuality": "medium"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        assert body["settings"]["homeTemplateLimit"] == 48, body["settings"]

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO generation_jobs(
                    id, job_no, user_id, organization_id, template_id, model_route_id, status,
                    prompt_final, quality, aspect_ratio, size, output_count, credit_cost
                )
                VALUES ('job_state_smoke', 'JOB-STATE', 'user_a', 'org_default', 'tpl_img', 'route_img',
                        'queued', 'state machine test', 'high', '1:1', '1024x1024', 1, 0)
                """
            )
            conn.commit()
        status, body, _ = request(
            "PATCH",
            "/api/admin/jobs/job_state_smoke",
            {"status": "success"},
            headers={"Cookie": admin_cookie},
        )
        assert status == 403, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/jobs/job_state_smoke",
            admin_payload({"status": "success"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 409, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/jobs/job_state_smoke",
            {"status": "running", "adminPassword": "wrong-password"},
            headers={"Cookie": admin_cookie},
        )
        assert status == 403, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/jobs/job_state_smoke",
            admin_payload({"status": "running"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/jobs/job_state_smoke",
            admin_payload({"status": "success"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/jobs/job_state_smoke",
            admin_payload({"status": "queued"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 409, body

        original_build_mpay_payment = server.build_mpay_payment

        def fake_mpay_payment(conn, order, channel):  # noqa: ANN001
            return {
                "provider": "mpay",
                "channel": channel,
                "state": "pending",
                "displayMode": "qrcode",
                "qrcodeUrl": "javascript:alert(1)",
                "paymentUrl": "file:///etc/passwd",
                "providerOrderId": "provider-safe-price-test",
            }

        server.build_mpay_payment = fake_mpay_payment
        try:
            status, body, _ = request(
                "POST",
                "/api/pay/orders",
                {"planCode": "pack_200", "priceCents": 1, "credits": 999999, "channel": "wechat"},
                headers={"Cookie": cookie_a},
            )
        finally:
            server.build_mpay_payment = original_build_mpay_payment
        assert status == 200, body
        assert body["item"]["amountCents"] == 2900, body["item"]
        assert body["item"]["plan"]["credits"] == 200, body["item"]["plan"]
        assert body["payment"]["qrcodeUrl"] == "", body["payment"]
        assert body["payment"]["paymentUrl"] == "", body["payment"]
        status, body, _ = request("GET", f"/api/pay/orders/{body['item']['orderNo']}", headers={"Cookie": cookie_b})
        assert status == 404, body

        for blocked_base_url in ("http://127.0.0.1:4179", "http://169.254.169.254"):
            status, body, _ = request(
                "POST",
                "/api/admin/api-settings",
                admin_payload({"baseUrl": blocked_base_url, "apiKey": "test-key"}),
                headers={"Cookie": admin_cookie},
            )
            assert status == 400, body

        status, body, _ = request(
            "PUT",
            "/api/admin/api-settings",
            admin_payload(
                {
                    "baseUrl": "https://example.com",
                    "apiEndpoint": "/api/generate-image",
                    "balanceEndpoint": "/api/admin/model-balance",
                    "apiKey": "apimart-db-secret",
                }
            ),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        assert body["state"]["api"]["apimartKeyConfigured"] is True, body["state"]["api"]
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            metadata_json = conn.execute("SELECT metadata_json FROM model_providers WHERE id = 'provider_apimart'").fetchone()["metadata_json"]
            metadata = json.loads(metadata_json)
            assert metadata.get("apiKey") is None, metadata
            assert str(metadata.get("apiKeyEncrypted") or "").startswith("enc:v1:"), metadata
            assert "apimart-db-secret" not in metadata_json, metadata_json
            assert server.effective_apimart_api_key(conn) == "apimart-db-secret"

            metadata["apiKey"] = "legacy-plaintext-secret"
            metadata.pop("apiKeyEncrypted", None)
            conn.execute("UPDATE model_providers SET metadata_json = ? WHERE id = 'provider_apimart'", (json.dumps(metadata),))
            server.migrate_plaintext_secrets(conn)
            migrated_json = conn.execute("SELECT metadata_json FROM model_providers WHERE id = 'provider_apimart'").fetchone()["metadata_json"]
            migrated = json.loads(migrated_json)
            assert migrated.get("apiKey") is None, migrated
            assert str(migrated.get("apiKeyEncrypted") or "").startswith("enc:v1:"), migrated
            assert "legacy-plaintext-secret" not in migrated_json, migrated_json
            assert server.effective_apimart_api_key(conn) == "legacy-plaintext-secret"

        status, body, _ = request(
            "POST",
            "/api/admin/templates",
            {
                "title": "missing reauth template",
                "promptTemplate": "should be blocked",
                "coverUrl": tiny_png,
            },
            headers={"Cookie": admin_cookie},
        )
        assert status == 403, body
        status, template_body, _ = request(
            "POST",
            "/api/admin/templates",
            admin_payload(
                {
                    "id": "tpl_admin_security_smoke",
                    "title": "Admin security template",
                    "promptTemplate": "safe prompt",
                    "coverUrl": tiny_png,
                    "status": "hidden",
                    "creditCost": 3,
                }
            ),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, template_body
        status, body, _ = request(
            "PATCH",
            "/api/admin/templates/tpl_admin_security_smoke",
            admin_payload({"featured": True, "sortScore": 123}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/templates/tpl_admin_security_smoke",
            admin_payload({"status": "published"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        status, body, _ = request(
            "PATCH",
            "/api/admin/templates/tpl_admin_security_smoke",
            admin_payload({"creditCost": -5}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        status, body, _ = request(
            "POST",
            "/api/admin/jobs",
            admin_payload({"templateId": "tpl_admin_security_smoke", "cost": -1, "prompt": "invalid cost"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        status, body, _ = request(
            "POST",
            "/api/admin/reviews",
            {"templateId": "tpl_admin_security_smoke", "risk": "medium", "reason": "missing reauth review"},
            headers={"Cookie": admin_cookie},
        )
        assert status == 403, body
        status, body, _ = request(
            "POST",
            "/api/admin/reviews",
            admin_payload({"templateId": "tpl_admin_security_smoke", "risk": "extreme", "reason": "invalid risk"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        status, body, _ = request(
            "POST",
            "/api/admin/reviews",
            admin_payload({"templateId": "tpl_admin_security_smoke", "risk": "medium", "reason": "security smoke review"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        with sqlite3.connect(DB_PATH) as conn:
            review_id = conn.execute("SELECT id FROM review_items WHERE subject_id = 'tpl_admin_security_smoke' ORDER BY created_at DESC LIMIT 1").fetchone()[0]
        status, body, _ = request(
            "PATCH",
            f"/api/admin/reviews/{review_id}",
            admin_payload({"status": "approved", "note": "x" * 501}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 400, body
        assert body["message"] == "Review note must be 500 characters or less", body
        status, body, _ = request(
            "PATCH",
            f"/api/admin/reviews/{review_id}",
            admin_payload({"status": "approved", "note": "security smoke approved"}),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body
        status, body, _ = request(
            "DELETE",
            "/api/admin/templates/tpl_admin_security_smoke",
            admin_payload(),
            headers={"Cookie": admin_cookie},
        )
        assert status == 200, body

        original_call_json_api = server.call_json_api
        leaked_authorization_headers: list[str] = []

        def capture_connection_test_call(method, url, headers=None, payload=None, timeout=60):  # noqa: ANN001
            if headers and headers.get("Authorization"):
                leaked_authorization_headers.append(headers["Authorization"])
            return {"balance": "ok"}

        server.call_json_api = capture_connection_test_call
        try:
            status, body, _ = request(
                "POST",
                "/api/admin/api-settings/test",
                admin_payload({"baseUrl": "https://api.example.test"}),
                headers={"Cookie": admin_cookie},
            )
            assert status == 200, body
            assert body["test"]["status"] == "blocked", body
            assert leaked_authorization_headers == [], leaked_authorization_headers
        finally:
            server.call_json_api = original_call_json_api

        status, _, _ = request("GET", "/assets/awesome-gpt-image-2/data/mpay_v2_webman-master/config/route.php")
        assert status == 404, status

        status, _, _ = request("GET", "/assets/awesome-gpt-image-2/data/mpay_v2_webman-master/public/mer/static/js/login-form-C0LAiycW.js")
        assert status == 404, status

        for blocked_static_path in (
            "/.gitignore",
            "/backend/schema.sql",
            "/backend/data/app.db",
            "/tools/sync-awesome-gpt-image-2.ps1",
            "/assets/awesome-gpt-image-2/package-lock.json",
            "/assets/awesome-gpt-image-2/local-db.js",
            "/assets/awesome-gpt-image-2/data/gpt-image2-site-01a26d310243.js",
        ):
            status, _, _ = request("GET", blocked_static_path)
            assert status == 404, blocked_static_path
        status, _, _ = request("GET", "/assets/vendor/qrcode.min.js")
        assert status == 200, status

        server.RATE_LIMIT_BUCKETS.clear()
        for index in range(8):
            status, _, _ = request("POST", "/api/auth/password-login", {"email": f"missing{index}@example.com", "password": "WrongPass1"})
            assert status == 400, status
        status, _, _ = request("POST", "/api/auth/password-login", {"email": "missing8@example.com", "password": "WrongPass1"})
        assert status == 429, status
        server.RATE_LIMIT_BUCKETS.clear()

        status, body, _ = raw_request(
            "POST",
            "/api/auth/password-login",
            b'{"email":"a@example.com","password":"Password1"}',
            {"Content-Type": "text/plain"},
        )
        assert status == 415, body

        old_max_json = server.MAX_JSON_BODY_BYTES
        try:
            server.MAX_JSON_BODY_BYTES = 64
            status, body, _ = request(
                "POST",
                "/api/auth/password-login",
                {"email": "a@example.com", "password": "Password1", "padding": "x" * 256},
            )
            assert status == 413, body
        finally:
            server.MAX_JSON_BODY_BYTES = old_max_json

        status, _, _ = request(
            "POST",
            "/api/account/password",
            {"currentPassword": "Password1", "newPassword": "Password2", "confirmPassword": "Password2"},
            headers={"Cookie": cookie_a, "Content-Type": "application/json"},
            default_xhr=False,
        )
        assert status == 403, status
        status, _, _ = request(
            "POST",
            "/api/account/password",
            {"currentPassword": "Password1", "newPassword": "Password2", "confirmPassword": "Password2"},
            headers={"Cookie": cookie_a, "Content-Type": "application/json", "X-CSRF-Token": "wrong-token"},
        )
        assert status == 403, status
        session_only_cookie = cookie_a.split(";", 1)[0]
        status, _, _ = request(
            "POST",
            "/api/account/password",
            {"currentPassword": "Password1", "newPassword": "Password2", "confirmPassword": "Password2"},
            headers={"Cookie": f"{session_only_cookie}; ycimage_csrf=attacker", "Content-Type": "application/json", "X-CSRF-Token": "attacker"},
        )
        assert status == 403, status

        status, body, _ = request(
            "POST",
            "/api/account/custom-templates",
            {"title": "leak attempt", "prompt": "private prompt", "coverUrl": "backend/server.py", "settings": {"model": "gpt-image-2-high"}},
            headers={"Cookie": cookie_a},
        )
        assert status == 400, body

        status, custom_body, _ = request(
            "POST",
            "/api/account/custom-templates",
            {
                "title": "private custom template",
                "prompt": "private custom prompt",
                "coverUrl": tiny_png,
                "settings": {"model": "gpt-image-2-high"},
            },
            headers={"Cookie": cookie_a},
        )
        assert status == 201, custom_body
        custom_template_id = custom_body["item"]["id"]
        status, public_templates, _ = request("GET", "/api/templates?status=all&include_params=1", headers={"Cookie": cookie_b})
        assert status == 200, public_templates
        assert custom_template_id not in {item["id"] for item in public_templates["items"]}, public_templates
        status, body, _ = request("GET", f"/api/templates/{custom_template_id}", headers={"Cookie": cookie_b})
        assert status == 404, body
        status, body, _ = request("GET", f"/api/account/custom-templates/{custom_template_id}", headers={"Cookie": cookie_b})
        assert status == 404, body
        status, body, _ = request("GET", f"/api/account/custom-templates/{custom_template_id}", headers={"Cookie": cookie_a})
        assert status == 200, body

        bad_reference = {
            "dataUrl": "data:image/png;base64," + base64.b64encode(b"not-an-image").decode("ascii"),
            "mimeType": "image/png",
            "name": "fake.png",
        }
        status, body, _ = request(
            "POST",
            "/api/generate-image",
            {"templateId": "tpl_img", "prompt": "hello", "settings": {"model": "gpt-image-2-high"}, "referenceImages": [bad_reference]},
            headers={"Cookie": cookie_a},
        )
        assert status == 400, body

        original_call_json_api = server.call_json_api
        original_apimart_api_key = server.APIMART_API_KEY

        def fake_call_json_api(method, url, headers=None, payload=None, timeout=60):  # noqa: ANN001
            assert headers and "Authorization" in headers
            assert payload and payload.get("prompt") == "secret prompt should not be stored in request snapshot"
            return {"data": {"task_id": "task-safe-request-snapshot", "status": "queued"}}

        server.call_json_api = fake_call_json_api
        server.APIMART_API_KEY = "test-apimart-key"
        try:
            status, generate_body, _ = request(
                "POST",
                "/api/generate-image",
                {
                    "templateId": "tpl_img",
                    "prompt": "secret prompt should not be stored in request snapshot",
                    "settings": {"model": "gpt-image-2-high", "quality": "high", "count": 1},
                    "unexpectedAdminField": "must-not-persist",
                },
                headers={"Cookie": cookie_a},
            )
        finally:
            server.call_json_api = original_call_json_api
            server.APIMART_API_KEY = original_apimart_api_key
        assert status == 202, generate_body
        generation_credit_cost = int(generate_body["creditCost"])
        with sqlite3.connect(DB_PATH) as conn:
            snapshot_json = conn.execute(
                "SELECT request_payload_json FROM generation_jobs WHERE id = ?",
                (generate_body["jobId"],),
            ).fetchone()[0]
        request_snapshot = json.loads(snapshot_json)
        assert "unexpectedAdminField" not in request_snapshot, request_snapshot
        assert "secret prompt should not be stored" not in snapshot_json, request_snapshot
        assert request_snapshot["providerPayload"]["promptLength"] > 0, request_snapshot
        assert "prompt" not in request_snapshot["providerPayload"], request_snapshot

        def fake_call_json_api_without_task(method, url, headers=None, payload=None, timeout=60):  # noqa: ANN001
            return {"code": "500", "message": "upstream leaked secret=abc123", "data": {"status": "failed"}}

        server.call_json_api = fake_call_json_api_without_task
        server.APIMART_API_KEY = "test-apimart-key"
        try:
            status, missing_task_body, _ = request(
                "POST",
                "/api/generate-image",
                {
                    "templateId": "tpl_img",
                    "prompt": "missing task id response should be sanitized",
                    "settings": {"model": "gpt-image-2-high", "quality": "high", "count": 1},
                },
                headers={"Cookie": cookie_a},
            )
        finally:
            server.call_json_api = original_call_json_api
            server.APIMART_API_KEY = original_apimart_api_key
        assert status == 502, missing_task_body
        summary = missing_task_body.get("providerResponseSummary", {})
        assert summary.get("messagePresent") is True, summary
        assert summary.get("messageLength") == len("upstream leaked secret=abc123"), summary
        assert "message" not in summary, summary
        assert "abc123" not in json.dumps(missing_task_body), missing_task_body

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute(
                "INSERT INTO orders(id, order_no, user_id, organization_id, plan_id, amount_cents, currency, payment_channel, status, metadata_json) VALUES (?, ?, ?, ?, ?, ?, 'CNY', 'wechat', 'pending', ?)",
                ("order_paid", "ORD-PAID", "user_a", "org_default", "plan_pack", 2900, json.dumps({"grantCredits": 200})),
            )
            conn.execute(
                "INSERT INTO orders(id, order_no, user_id, organization_id, plan_id, amount_cents, currency, payment_channel, status, metadata_json) VALUES (?, ?, ?, ?, ?, ?, 'CNY', 'wechat', 'pending', ?)",
                ("order_old_key", "ORD-OLDKEY", "user_a", "org_default", "plan_pack", 2900, json.dumps({"grantCredits": 200})),
            )
            conn.execute(
                "INSERT INTO orders(id, order_no, user_id, organization_id, plan_id, amount_cents, currency, payment_channel, status, metadata_json) VALUES (?, ?, ?, ?, ?, ?, 'CNY', 'wechat', 'pending', ?)",
                ("order_jeepay", "ORD-JEEPAY", "user_a", "org_default", "plan_pack", 2900, json.dumps({"grantCredits": 200})),
            )
            conn.execute(
                "INSERT INTO orders(id, order_no, user_id, organization_id, plan_id, amount_cents, currency, payment_channel, status, metadata_json) VALUES (?, ?, ?, ?, ?, ?, 'CNY', 'wechat', 'paid', ?)",
                ("order_jeepay_paid", "ORD-JEEPAY-PAID", "user_a", "org_default", "plan_pack", 2900, json.dumps({"grantCredits": 200})),
            )
            conn.commit()

        params = {"pid": "pid", "out_trade_no": "ORD-PAID", "money": "29.00", "trade_status": "TRADE_SUCCESS", "trade_no": "T1"}
        bad_sign_params = dict(params)
        bad_sign_params["sign"] = "bad-signature"
        status, _, _ = request("POST", "/api/pay/notify/mpay", bad_sign_params)
        assert status == 400, status
        wrong_amount_params = dict(params)
        wrong_amount_params["money"] = "0.01"
        wrong_amount_params["sign"] = mpay_sign(wrong_amount_params, "secret")
        status, _, _ = request("POST", "/api/pay/notify/mpay", wrong_amount_params)
        assert status == 400, status
        missing_pid_params = dict(params)
        missing_pid_params.pop("pid")
        missing_pid_params["sign"] = mpay_sign(missing_pid_params, "secret")
        status, _, _ = request("POST", "/api/pay/notify/mpay", missing_pid_params)
        assert status == 400, status
        wrong_pid_params = dict(params)
        wrong_pid_params["pid"] = "attacker-pid"
        wrong_pid_params["sign"] = mpay_sign(wrong_pid_params, "secret")
        status, _, _ = request("POST", "/api/pay/notify/mpay", wrong_pid_params)
        assert status == 400, status
        status, _, _ = request(
            "POST",
            "/api/pay/notify/mpay",
            {**bad_sign_params, "sign": "bad-signature"},
            headers={"Cookie": cookie_a, "X-CSRF-Token": "wrong-token"},
        )
        assert status == 400, status
        status, body, _ = request("GET", "/api/pay/orders/ORD-PAID", headers={"Cookie": cookie_b})
        assert status == 404, body

        params["sign"] = mpay_sign(params, "secret")
        query = urllib.parse.urlencode(params)
        status, _, _ = request("GET", f"/api/pay/notify/mpay?{query}")
        assert status == 405, status
        status, _, _ = request("POST", "/api/pay/notify/mpay", params)
        assert status == 200, status
        status, _, _ = request("POST", "/api/pay/notify/mpay", params)
        assert status == 200, status
        status, order_body, _ = request("GET", "/api/pay/orders/ORD-PAID", headers={"Cookie": cookie_a})
        assert status == 200, order_body
        provider_payload = order_body["item"]["metadata"].get("providerPayload", {})
        assert provider_payload.get("sign") == "***redacted***", provider_payload
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT balance FROM credit_accounts WHERE user_id = 'user_a'").fetchone()
            balance = row[0]
            credits = conn.execute("SELECT COUNT(*) FROM credit_ledger WHERE reference_type='order' AND reference_id='order_paid'").fetchone()[0]
            metadata_json = conn.execute("SELECT metadata_json FROM orders WHERE id = 'order_paid'").fetchone()[0]
            stored_provider_payload = json.loads(metadata_json).get("providerPayload", {})
        assert balance == 270 - generation_credit_cost, balance
        assert credits == 1, credits
        assert stored_provider_payload.get("sign") == "***redacted***", stored_provider_payload

        old_key_params = {"pid": "pid", "out_trade_no": "ORD-OLDKEY", "money": "29.00", "trade_status": "TRADE_SUCCESS", "trade_no": "T2"}
        old_key_params["sign"] = mpay_sign(old_key_params, "old-secret")
        status, _, _ = request("POST", "/api/pay/notify/mpay", old_key_params)
        assert status == 200, status
        status, old_key_order_body, _ = request("GET", "/api/pay/orders/ORD-OLDKEY", headers={"Cookie": cookie_a})
        assert status == 200, old_key_order_body
        assert old_key_order_body["item"]["status"] == "paid", old_key_order_body

        server.PAYMENT_PROVIDER_ENV = "jeepay"
        server.JEEPAY_MCH_NO = "mch-test"
        server.JEEPAY_APP_ID = "app-test"
        server.JEEPAY_NOTIFY_SECRET = "jeepay-secret"
        jeepay_params = {
            "mchNo": "mch-test",
            "appId": "app-test",
            "mchOrderNo": "ORD-JEEPAY",
            "amount": "2900",
            "state": "2",
            "payOrderId": "JP-ORDER-1",
        }
        bad_jeepay = dict(jeepay_params)
        bad_jeepay["sign"] = "bad-signature"
        status, _, _ = request("POST", "/api/pay/notify/jeepay", bad_jeepay)
        assert status == 400, status

        wrong_jeepay_amount = dict(jeepay_params)
        wrong_jeepay_amount["amount"] = "1"
        wrong_jeepay_amount["sign"] = server.sign_jeepay_payload(wrong_jeepay_amount, "jeepay-secret")
        status, _, _ = request("POST", "/api/pay/notify/jeepay", wrong_jeepay_amount)
        assert status == 400, status

        wrong_merchant = dict(jeepay_params)
        wrong_merchant["mchNo"] = "mch-attacker"
        wrong_merchant["sign"] = server.sign_jeepay_payload(wrong_merchant, "jeepay-secret")
        status, _, _ = request("POST", "/api/pay/notify/jeepay", wrong_merchant)
        assert status == 400, status

        jeepay_params["sign"] = server.sign_jeepay_payload(jeepay_params, "jeepay-secret")
        status, body, _ = request("POST", "/api/pay/notify/jeepay", jeepay_params)
        assert status == 200, body
        assert body == "success", body
        status, order_body, _ = request("GET", "/api/pay/orders/ORD-JEEPAY", headers={"Cookie": cookie_a})
        assert status == 200, order_body
        assert order_body["item"]["status"] == "paid", order_body

        jeepay_failed_paid = {
            "mchNo": "mch-test",
            "appId": "app-test",
            "mchOrderNo": "ORD-JEEPAY-PAID",
            "amount": "2900",
            "state": "3",
            "payOrderId": "JP-ORDER-2",
        }
        jeepay_failed_paid["sign"] = server.sign_jeepay_payload(jeepay_failed_paid, "jeepay-secret")
        status, body, _ = request("POST", "/api/pay/notify/jeepay", jeepay_failed_paid)
        assert status == 200, body
        assert body == "success", body
        status, order_body, _ = request("GET", "/api/pay/orders/ORD-JEEPAY-PAID", headers={"Cookie": cookie_a})
        assert status == 200, order_body
        assert order_body["item"]["status"] == "paid", order_body
        server.PAYMENT_PROVIDER_ENV = "mpay"

        for blocked_url in ("file:///etc/passwd", "http://127.0.0.1:4179/api/health", "http://169.254.169.254/latest/meta-data/"):
            try:
                server.download_remote_binary(blocked_url, timeout=1)
                raise AssertionError(f"SSRF URL unexpectedly allowed: {blocked_url}")
            except RuntimeError:
                pass

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("UPDATE credit_accounts SET balance = 8 WHERE user_id = 'user_a'")
            conn.commit()
            conn.execute("BEGIN IMMEDIATE")
            server.charge_generation_credits(conn, "user_a", "atomic_job_1", 8, {})
            try:
                server.charge_generation_credits(conn, "user_a", "atomic_job_2", 8, {})
                raise AssertionError("second charge unexpectedly succeeded")
            except ValueError:
                pass
            conn.execute("ROLLBACK")
    finally:
        httpd.shutdown()
        httpd.server_close()

    print("security smoke tests passed")


if __name__ == "__main__":
    run()
