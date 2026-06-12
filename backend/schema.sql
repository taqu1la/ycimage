PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'string',
    description TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    plan_code TEXT NOT NULL DEFAULT 'free',
    billing_email TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    permissions_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL,
    mobile TEXT UNIQUE,
    email TEXT UNIQUE,
    wechat_openid TEXT UNIQUE,
    avatar_url TEXT,
    role_id TEXT REFERENCES roles(id) ON DELETE SET NULL,
    membership_level TEXT NOT NULL DEFAULT 'free',
    status TEXT NOT NULL DEFAULT 'active',
    locale TEXT NOT NULL DEFAULT 'zh-CN',
    last_login_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    company_name TEXT,
    industry TEXT,
    city TEXT,
    use_case TEXT,
    designer_level TEXT,
    preferences_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash TEXT NOT NULL UNIQUE,
    ip_address TEXT,
    user_agent TEXT,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS credit_accounts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    balance INTEGER NOT NULL DEFAULT 0 CHECK(balance >= 0),
    frozen_balance INTEGER NOT NULL DEFAULT 0 CHECK(frozen_balance >= 0),
    lifetime_purchased INTEGER NOT NULL DEFAULT 0,
    lifetime_granted INTEGER NOT NULL DEFAULT 0,
    lifetime_spent INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS credit_ledger (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES credit_accounts(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    direction TEXT NOT NULL CHECK(direction IN ('credit','debit','freeze','unfreeze','refund')),
    amount INTEGER NOT NULL CHECK(amount > 0),
    balance_after INTEGER NOT NULL,
    reason TEXT NOT NULL,
    reference_type TEXT,
    reference_id TEXT,
    operator_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pricing_plans (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    plan_type TEXT NOT NULL CHECK(plan_type IN ('free','subscription','credit_pack','enterprise')),
    price_cents INTEGER NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'CNY',
    credits INTEGER NOT NULL DEFAULT 0,
    period_days INTEGER,
    features_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    order_no TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
    plan_id TEXT REFERENCES pricing_plans(id) ON DELETE SET NULL,
    amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'CNY',
    payment_channel TEXT NOT NULL,
    payment_provider_order_id TEXT,
    status TEXT NOT NULL CHECK(status IN ('pending','paid','failed','cancelled','refunded','manual')),
    paid_at TEXT,
    refunded_at TEXT,
    notes TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    invoice_title TEXT NOT NULL,
    tax_no TEXT,
    email TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    file_asset_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS template_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK(source_type IN ('repo','manual','import','system')),
    repository_url TEXT,
    license TEXT,
    synced_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS template_categories (
    id TEXT PRIMARY KEY,
    source_value TEXT NOT NULL UNIQUE,
    name_zh TEXT NOT NULL,
    name_en TEXT,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES template_sources(id) ON DELETE SET NULL,
    source_template_id TEXT,
    case_id INTEGER,
    category_id TEXT REFERENCES template_categories(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    prompt_template TEXT NOT NULL,
    negative_prompt TEXT,
    cover_asset_id TEXT,
    cover_url TEXT,
    image_alt TEXT,
    source_label TEXT,
    source_url TEXT,
    original_url TEXT,
    status TEXT NOT NULL DEFAULT 'enabled' CHECK(status IN ('enabled','hidden','archived','draft')),
    featured INTEGER NOT NULL DEFAULT 0,
    credit_cost INTEGER NOT NULL DEFAULT 5,
    default_model_route_id TEXT,
    default_quality TEXT NOT NULL DEFAULT 'high',
    default_aspect_ratio TEXT NOT NULL DEFAULT '1:1',
    default_size TEXT NOT NULL DEFAULT '1024x1024',
    allow_reference_image INTEGER NOT NULL DEFAULT 1,
    sort_score REAL NOT NULL DEFAULT 0,
    usage_count INTEGER NOT NULL DEFAULT 0,
    conversion_rate REAL NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, source_template_id)
);

CREATE TABLE IF NOT EXISTS template_params (
    id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    param_key TEXT NOT NULL,
    label TEXT NOT NULL,
    token TEXT,
    default_value TEXT,
    param_type TEXT NOT NULL DEFAULT 'text',
    required INTEGER NOT NULL DEFAULT 0,
    options_json TEXT NOT NULL DEFAULT '[]',
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE(template_id, param_key)
);

CREATE TABLE IF NOT EXISTS template_tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS template_tag_map (
    template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL REFERENCES template_tags(id) ON DELETE CASCADE,
    PRIMARY KEY(template_id, tag_id)
);

CREATE TABLE IF NOT EXISTS template_scene_map (
    template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    scene TEXT NOT NULL,
    PRIMARY KEY(template_id, scene)
);

CREATE TABLE IF NOT EXISTS style_templates (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES template_sources(id) ON DELETE SET NULL,
    category_id TEXT REFERENCES template_categories(id) ON DELETE SET NULL,
    title_zh TEXT NOT NULL,
    title_en TEXT,
    description_zh TEXT,
    description_en TEXT,
    cover_url TEXT,
    prompt_template TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    guidance_json TEXT NOT NULL DEFAULT '{}',
    pitfalls_json TEXT NOT NULL DEFAULT '{}',
    example_cases_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'enabled',
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS model_providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    provider_type TEXT NOT NULL DEFAULT 'openai-compatible',
    base_url TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    server_key_status TEXT NOT NULL DEFAULT 'not_configured',
    health_status TEXT NOT NULL DEFAULT 'unknown',
    last_checked_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS model_routes (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES model_providers(id) ON DELETE CASCADE,
    route_code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    modality TEXT NOT NULL CHECK(modality IN ('image','video','text','multimodal')),
    quality TEXT NOT NULL DEFAULT 'high',
    supported_sizes_json TEXT NOT NULL DEFAULT '[]',
    supported_ratios_json TEXT NOT NULL DEFAULT '[]',
    default_size TEXT NOT NULL DEFAULT '1024x1024',
    default_ratio TEXT NOT NULL DEFAULT '1:1',
    credit_cost INTEGER NOT NULL DEFAULT 5,
    priority INTEGER NOT NULL DEFAULT 100,
    timeout_seconds INTEGER NOT NULL DEFAULT 90,
    retry_limit INTEGER NOT NULL DEFAULT 2,
    fallback_route_id TEXT REFERENCES model_routes(id) ON DELETE SET NULL,
    success_rate REAL NOT NULL DEFAULT 0,
    avg_latency_ms INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    owner_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
    asset_type TEXT NOT NULL CHECK(asset_type IN ('template_cover','case_image','reference_image','generated_image','generated_video','avatar','document','invoice','other')),
    storage_provider TEXT NOT NULL DEFAULT 'local',
    storage_path TEXT NOT NULL,
    public_url TEXT,
    mime_type TEXT,
    byte_size INTEGER,
    width INTEGER,
    height INTEGER,
    checksum TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    moderation_status TEXT NOT NULL DEFAULT 'pending',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asset_blobs (
    asset_id TEXT PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
    content BLOB NOT NULL,
    byte_size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    embedded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generation_jobs (
    id TEXT PRIMARY KEY,
    job_no TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
    template_id TEXT REFERENCES templates(id) ON DELETE SET NULL,
    model_route_id TEXT REFERENCES model_routes(id) ON DELETE SET NULL,
    status TEXT NOT NULL CHECK(status IN ('draft','queued','running','success','failed','cancelled','review')),
    prompt_final TEXT NOT NULL,
    prompt_params_json TEXT NOT NULL DEFAULT '{}',
    negative_prompt TEXT,
    quality TEXT NOT NULL DEFAULT 'high',
    aspect_ratio TEXT NOT NULL DEFAULT '1:1',
    size TEXT NOT NULL DEFAULT '1024x1024',
    output_count INTEGER NOT NULL DEFAULT 1,
    reference_mode TEXT NOT NULL DEFAULT 'optional',
    credit_cost INTEGER NOT NULL DEFAULT 0,
    request_payload_json TEXT NOT NULL DEFAULT '{}',
    provider_response_json TEXT NOT NULL DEFAULT '{}',
    error_code TEXT,
    error_message TEXT,
    queued_at TEXT,
    started_at TEXT,
    finished_at TEXT,
    latency_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generation_job_assets (
    job_id TEXT NOT NULL REFERENCES generation_jobs(id) ON DELETE CASCADE,
    asset_id TEXT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('reference','output','thumbnail','mask')),
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(job_id, asset_id, role)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id TEXT PRIMARY KEY,
    template_id TEXT REFERENCES templates(id) ON DELETE CASCADE,
    version_no INTEGER NOT NULL,
    title TEXT,
    prompt_template TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '[]',
    change_note TEXT,
    created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(template_id, version_no)
);

CREATE TABLE IF NOT EXISTS review_items (
    id TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL CHECK(subject_type IN ('asset','generation_job','template','prompt','user')),
    subject_id TEXT NOT NULL,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    risk_level TEXT NOT NULL CHECK(risk_level IN ('low','medium','high','critical')),
    reason TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','manual','escalated')),
    reviewer_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TEXT,
    decision_note TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS moderation_rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK(rule_type IN ('keyword','regex','provider_signal','manual')),
    pattern TEXT,
    action TEXT NOT NULL CHECK(action IN ('allow','review','block')),
    risk_level TEXT NOT NULL DEFAULT 'medium',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    visibility TEXT NOT NULL DEFAULT 'private',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collection_items (
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    asset_id TEXT REFERENCES assets(id) ON DELETE CASCADE,
    template_id TEXT REFERENCES templates(id) ON DELETE CASCADE,
    job_id TEXT REFERENCES generation_jobs(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL CHECK(item_type IN ('asset','template','job')),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(collection_id, item_type, sort_order)
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    notification_type TEXT NOT NULL DEFAULT 'system',
    read_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhooks (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    target_url TEXT NOT NULL,
    secret_hint TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id TEXT PRIMARY KEY,
    webhook_id TEXT NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event_id TEXT NOT NULL,
    request_body_json TEXT NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TEXT,
    delivered_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    scopes_json TEXT NOT NULL DEFAULT '[]',
    last_used_at TEXT,
    revoked_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id TEXT PRIMARY KEY,
    actor_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    before_json TEXT,
    after_json TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics_events (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    anonymous_id TEXT,
    event_name TEXT NOT NULL,
    page TEXT,
    entity_type TEXT,
    entity_id TEXT,
    properties_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS template_daily_stats (
    stat_date TEXT NOT NULL,
    template_id TEXT NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    views INTEGER NOT NULL DEFAULT 0,
    opens INTEGER NOT NULL DEFAULT 0,
    generations INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    downloads INTEGER NOT NULL DEFAULT 0,
    paid_conversions INTEGER NOT NULL DEFAULT 0,
    revenue_cents INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(stat_date, template_id)
);

CREATE TABLE IF NOT EXISTS model_daily_stats (
    stat_date TEXT NOT NULL,
    model_route_id TEXT NOT NULL REFERENCES model_routes(id) ON DELETE CASCADE,
    requests INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    failures INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms INTEGER NOT NULL DEFAULT 0,
    credits_spent INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(stat_date, model_route_id)
);

CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_auth_codes_mobile_created ON auth_verification_codes(mobile, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_user_created ON credit_ledger(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_reference ON credit_ledger(reference_type, reference_id, direction);
CREATE UNIQUE INDEX IF NOT EXISTS ux_credit_ledger_order_credit_once
ON credit_ledger(reference_type, reference_id, direction)
WHERE reference_type = 'order' AND direction = 'credit' AND reference_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_templates_category_status ON templates(category_id, status);
CREATE INDEX IF NOT EXISTS idx_templates_featured_score ON templates(featured, sort_score DESC);
CREATE INDEX IF NOT EXISTS idx_template_params_template ON template_params(template_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_assets_owner ON assets(owner_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_user_created ON generation_jobs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON generation_jobs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_template ON generation_jobs(template_id);
CREATE INDEX IF NOT EXISTS idx_reviews_status_risk ON review_items(status, risk_level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON admin_audit_logs(entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_name_created ON analytics_events(event_name, created_at DESC);

CREATE VIEW IF NOT EXISTS v_template_operational AS
SELECT
    t.id,
    t.title,
    tc.name_zh AS category_name,
    t.status,
    t.featured,
    t.credit_cost,
    t.cover_url,
    t.usage_count,
    t.conversion_rate,
    COUNT(tp.id) AS param_count,
    t.updated_at
FROM templates t
LEFT JOIN template_categories tc ON tc.id = t.category_id
LEFT JOIN template_params tp ON tp.template_id = t.id
GROUP BY t.id;

CREATE VIEW IF NOT EXISTS v_user_account_summary AS
SELECT
    u.id AS user_id,
    u.display_name,
    u.membership_level,
    u.status,
    ca.balance,
    ca.frozen_balance,
    ca.lifetime_purchased,
    ca.lifetime_granted,
    ca.lifetime_spent,
    COUNT(gj.id) AS generation_count
FROM users u
LEFT JOIN credit_accounts ca ON ca.user_id = u.id
LEFT JOIN generation_jobs gj ON gj.user_id = u.id
GROUP BY u.id;
