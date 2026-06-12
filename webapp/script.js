const PRICING = {
    free: { name: "免费体验", price: 0 },
    basic: { name: "月卡", price: 29, yearly: 23 },
    pro: { name: "创作者版", price: 199, yearly: 159 },
    studio: { name: "工作室版", price: 499, yearly: 399 },
    pack200: { name: "200 积分包", price: 29 },
    pack600: { name: "600 积分包", price: 79 },
    pack1500: { name: "1500 积分包", price: 199 },
    pack6000: { name: "6000 积分包", price: 599 }
};

const PLAN_CODE_ALIASES_CLIENT = {
    basic: "monthly",
    pro: "creator",
    pack200: "pack_200",
    pack600: "pack_600",
    pack1500: "pack_1500",
    pack6000: "pack_6000"
};
const PLAN_CODE_TO_CLIENT_ID = {
    monthly: "basic",
    creator: "pro",
    studio: "studio",
    pack_200: "pack200",
    pack_600: "pack600",
    pack_1500: "pack1500",
    pack_6000: "pack6000"
};
const SUBSCRIPTION_PLAN_RANK_CLIENT = {
    monthly: 1,
    creator: 2,
    studio: 3
};
const FALLBACK_PLAN_CREDITS = {
    basic: 300,
    pro: 1500,
    studio: 6000,
    pack200: 200,
    pack600: 600,
    pack1500: 1500,
    pack6000: 6000
};

const GENERATION_API_ENDPOINT = "/api/generate-image";
const LOCAL_API_ORIGIN = "http://127.0.0.1:4178";
const DEFAULT_IMAGE_MODEL = "gpt-image-2-high";
const TEMPLATE_REFERENCE_LIMIT = 10;
const TEMPLATE_REFERENCE_MAX_SIZE = 10 * 1024 * 1024;
const VIDEO_REFERENCE_LIMIT = 10;
const VIDEO_REFERENCE_MAX_SIZE = 10 * 1024 * 1024;
const LEGACY_AUTH_STORAGE_KEY = "ycimage_auth_session";
const TEMPLATE_SIZE_TO_RATIO = {
    "1024x1024": "1:1",
    "1536x1536": "1:1",
    "2048x2048": "1:1",
    "1024x1280": "4:5",
    "1280x1024": "5:4",
    "1024x1536": "2:3",
    "1536x1024": "3:2",
    "1024x1792": "9:16",
    "1792x1024": "16:9"
};
const DEFAULT_CREDIT_RULES = {
    quality: {
        auto: { label: "Auto", factor: 1 },
        low: { label: "Low", factor: 0.7 },
        medium: { label: "Medium", factor: 1 },
        high: { label: "High", factor: 1.35 }
    },
    size: {
        auto: { label: "Auto", factor: 1 },
        "1:1": { label: "1:1", factor: 1 },
        "3:4": { label: "3:4", factor: 1.2 },
        "4:3": { label: "4:3", factor: 1.2 },
        "4:5": { label: "4:5", factor: 1.2 },
        "5:4": { label: "5:4", factor: 1.2 },
        "2:3": { label: "2:3", factor: 1.3 },
        "3:2": { label: "3:2", factor: 1.3 },
        "16:9": { label: "16:9", factor: 1.3 },
        "9:16": { label: "9:16", factor: 1.3 },
        "2:1": { label: "2:1", factor: 1.6 },
        "1:2": { label: "1:2", factor: 1.6 },
        "21:9": { label: "21:9", factor: 1.8 },
        "9:21": { label: "9:21", factor: 1.8 },
        "1024x1024": { label: "1024 x 1024", factor: 1 },
        "1024x1536": { label: "1024 x 1536", factor: 1.3 },
        "1536x1024": { label: "1536 x 1024", factor: 1.3 },
        "1536x1536": { label: "1536 x 1536", factor: 1.8 },
        "2048x2048": { label: "2048 x 2048", factor: 2.6 }
    },
    videoResolution: {
        "480p": { label: "480p", factor: 0.75 },
        "720p": { label: "720p", factor: 1 },
        "1080p": { label: "1080p", factor: 1.7 }
    }
};

let uploadedImage = null;
let generationCount = 1;
let templateReferenceImages = [];
let templateResultDownloadUrl = "";
let customImageReferenceImages = [];
let customImageResultUrls = [];
let customImageActiveResultUrl = "";
let customImagePollTimer = null;
let activeAwesomeTemplate = null;
let activeTemplateValues = {};
let awesomeTemplates = [];
let heroTemplateLookup = {};
let awesomeStats = { totalTemplates: 0, imageFiles: 0, styleTemplates: 0 };
let generationModels = [];
let videoTemplates = [];
let videoReferenceImages = [];
let activeVideoTemplate = null;
let activeVideoMode = "image";
let videoPollTimer = null;
let imagePollTimer = null;
let publicSettings = {};
let templateDataPromise = null;
let currentAccount = null;
let homeWorksSampleMarkup = "";
let activeWorksFilter = "all";
const HOME_WORK_CARD_SHAPES = ["tall", "", "", "wide", ""];
let paymentState = {
    planId: "",
    channel: "wechat",
    orderNo: "",
    pollTimer: null
};
const PAYMENT_CHANNEL_PLACEHOLDER_IMAGES = {
    wechat: "assets/payment-wechat-qr.jpg",
    alipay: "assets/payment-alipay-qr.jpg"
};
const POPULAR_TEMPLATE_LIMIT = 30;
const HOME_CATEGORY_LIMIT = 6;
let activeHomeCategoryFilter = "all";
const CATEGORY_LABELS = {
    "Architecture & Spaces": "建筑与空间",
    "Brand & Logos": "品牌与标志",
    "Characters & People": "人物与角色",
    "Charts & Infographics": "图表与信息图",
    "Documents & Publishing": "文档与出版",
    "History & Classical Themes": "历史与古典主题",
    "Illustration & Art": "插画与艺术",
    "Other Use Cases": "其他应用场景",
    "Photography & Realism": "摄影与写实",
    "Posters & Typography": "海报与字体",
    "Products & E-commerce": "产品与电商",
    "Scenes & Storytelling": "场景与叙事",
    "UI & Interfaces": "UI 与界面"
};

function isVideoTemplate(template = {}) {
    return template?.modality === "video" || template?.templateKind === "video";
}

function localServiceOrigin() {
    if (window.location.protocol !== "file:") {
        return window.location.origin;
    }
    return LOCAL_API_ORIGIN;
}

function shouldUseLocalApiFallback(value = "") {
    return window.location.protocol === "file:" && String(value).startsWith("/");
}

function servicePageUrl(path = "index.html", hash = "") {
    const cleanPath = String(path || "index.html").replace(/^\/+/, "") || "index.html";
    const url = new URL(cleanPath, `${localServiceOrigin()}/`);
    if (hash) {
        url.hash = String(hash).replace(/^#/, "");
    }
    return url.toString();
}

function redirectToServicePageIfNeeded() {
    if (window.location.protocol !== "file:") return false;
    const fileName = window.location.pathname.split("/").pop() || "index.html";
    const target = servicePageUrl(fileName, window.location.hash);
    if (window.location.href === target) return false;
    window.location.replace(target);
    return true;
}

document.addEventListener("DOMContentLoaded", () => {
    if (redirectToServicePageIfNeeded()) return;
    clearLegacySessionStorage();
    initNavigation();
    initMobileMenu();
    initTemplateFilters();
    initUpload();
    initTemplateForm();
    initWorkbench();
    initPricingToggle();
    initPaymentModal();
    initAccountModal();
    initAwesomeTemplateLibrary();
    initTemplateEditor();
    initTemplateHashSync();
    initVideoWorkbench();
});

function initNavigation() {
    const navLinks = document.querySelectorAll(".nav-links a");
    const sections = Array.from(navLinks)
        .map(link => document.querySelector(link.getAttribute("href")))
        .filter(Boolean);

    navLinks.forEach(link => {
        link.addEventListener("click", () => {
            document.getElementById("navLinks")?.classList.remove("open");
        });
    });

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            navLinks.forEach(link => {
                link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`);
            });
        });
    }, { rootMargin: "-35% 0px -55% 0px", threshold: 0.01 });

    sections.forEach(section => observer.observe(section));
}

function initMobileMenu() {
    const button = document.getElementById("mobileMenu");
    const nav = document.getElementById("navLinks");
    if (!button || !nav) return;
    button.setAttribute("aria-expanded", nav.classList.contains("open") ? "true" : "false");
    button.addEventListener("click", () => {
        const open = nav.classList.toggle("open");
        button.setAttribute("aria-expanded", open ? "true" : "false");
    });
}

function initTemplateFilters() {
    bindHomeTemplateFilterEvents();
}

function apiUrl(path) {
    if (!path) return "";
    const value = String(path).trim();
    if (/^https?:\/\//i.test(value) || isSafeDataImageUrl(value) || value.startsWith("blob:")) return value;
    if (/^[a-z][a-z0-9+.-]*:/i.test(value)) return "";
    if (shouldUseLocalApiFallback(value)) return `${LOCAL_API_ORIGIN}${value}`;
    return value;
}

const focusTrapState = new Map();

function getFocusableElements(container) {
    if (!container) return [];
    return Array.from(container.querySelectorAll([
        "a[href]",
        "button:not([disabled])",
        "input:not([disabled]):not([type='hidden'])",
        "select:not([disabled])",
        "textarea:not([disabled])",
        "[tabindex]:not([tabindex='-1'])"
    ].join(","))).filter(element => !element.hidden && element.offsetParent !== null);
}

function activateDialog(dialog, closeCallback, initialFocusSelector = "") {
    if (!dialog) return;
    focusTrapState.set(dialog, {
        previouslyFocused: document.activeElement instanceof HTMLElement ? document.activeElement : null,
        closeCallback
    });
    const focusTarget = initialFocusSelector ? dialog.querySelector(initialFocusSelector) : null;
    window.setTimeout(() => {
        const focusable = getFocusableElements(dialog);
        (focusTarget || focusable[0] || dialog).focus?.();
    }, 0);
}

function deactivateDialog(dialog) {
    const state = focusTrapState.get(dialog);
    focusTrapState.delete(dialog);
    state?.previouslyFocused?.focus?.();
}

document.addEventListener("keydown", event => {
    const activeDialog = Array.from(focusTrapState.keys()).find(dialog => dialog.getAttribute("aria-hidden") === "false");
    if (!activeDialog) return;
    if (event.key === "Escape") {
        event.preventDefault();
        focusTrapState.get(activeDialog)?.closeCallback?.();
        return;
    }
    if (event.key !== "Tab") return;
    const focusable = getFocusableElements(activeDialog);
    if (!focusable.length) {
        event.preventDefault();
        activeDialog.focus?.();
        return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
});

function assetUrl(path) {
    return safeMediaUrl(path);
}

function safeMediaUrl(path) {
    const url = apiUrl(path);
    if (!url) return "";
    if (isSafeDataImageUrl(url) || url.startsWith("blob:")) return url;
    if (/^https?:\/\//i.test(url)) return url;
    if (url.startsWith("/") || url.startsWith("./") || url.startsWith("../") || /^[A-Za-z0-9_.~/-]+$/.test(url)) return url;
    return "";
}

function isSafeDataImageUrl(value) {
    return /^data:image\/(?:jpeg|jpg|png|webp|gif);base64,[a-z0-9+/=]+$/i.test(String(value || "").trim());
}

function isAllowedUploadImageType(type) {
    return ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"].includes(String(type || "").toLowerCase());
}

function cssUrl(value) {
    const url = safeMediaUrl(value);
    return url ? `url('${String(url).replace(/['\\\n\r\f]/g, "")}')` : "";
}

function safeLinkUrl(path) {
    const url = apiUrl(path);
    if (!url) return "";
    if (/^https?:\/\//i.test(url) || url.startsWith("/") || url.startsWith("./") || url.startsWith("../") || url.startsWith("#")) return url;
    return "";
}

async function apiGet(path) {
    const response = await apiFetch(path, "GET");
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new Error(errorData.message || errorData.error || `HTTP ${response.status}`);
        error.status = response.status;
        error.data = errorData;
        throw error;
    }
    return response.json();
}

async function apiPost(path, payload) {
    const response = await apiFetch(path, "POST", {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData.message || errorData.error || `HTTP ${response.status}`;
        const error = new Error(message);
        error.status = response.status;
        error.data = errorData;
        throw error;
    }
    return response.json();
}

function clearLegacySessionStorage() {
    try {
        localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY);
    } catch (error) {
        // Storage can be unavailable in restricted browser modes; cookie auth still works.
    }
}

function csrfToken() {
    return document.cookie
        .split(";")
        .map(part => part.trim())
        .find(part => part.startsWith("ycimage_csrf="))
        ?.split("=")
        .slice(1)
        .join("=") || "";
}

function apiHeaders(extra = {}) {
    const headers = { Accept: "application/json", "X-Requested-With": "XMLHttpRequest", ...extra };
    const token = csrfToken();
    if (token) headers["X-CSRF-Token"] = token;
    return headers;
}

function apiRequestOptions(method = "GET", extra = {}) {
    const options = {
        method,
        credentials: "include",
        cache: "no-store",
        ...extra
    };
    options.headers = apiHeaders(extra.headers || {});
    return options;
}

let csrfRefreshPromise = null;

async function refreshCsrfCookie() {
    if (!csrfRefreshPromise) {
        csrfRefreshPromise = fetch(apiUrl("/api/auth/me"), apiRequestOptions("GET"))
            .catch(() => null)
            .finally(() => {
                csrfRefreshPromise = null;
            });
    }
    return csrfRefreshPromise;
}

async function apiFetch(path, method = "GET", extra = {}) {
    const execute = () => fetch(apiUrl(path), apiRequestOptions(method, extra));
    let response = await execute();
    if (response.status !== 403) return response;
    const errorData = await response.clone().json().catch(() => ({}));
    const message = String(errorData.message || errorData.error || "");
    if (!message.includes("CSRF protection rejected")) return response;
    await refreshCsrfCookie();
    return execute();
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function ensureTemplateData() {
    if (templateDataPromise) return templateDataPromise;
    templateDataPromise = (async () => {
        const [settingsData, templateData] = await Promise.all([
            apiGet("/api/settings/public"),
            apiGet(`/api/templates?featured=1&page_size=${POPULAR_TEMPLATE_LIMIT}&include_params=1&sort=featured`)
        ]);
        publicSettings = settingsData.settings || {};
        publicSettings.pricingPlans = settingsData.pricingPlans || publicSettings.pricingPlans || [];
        renderPaymentMethods();
        updatePaymentTrustPill();
        generationModels = settingsData.models || [];
        awesomeStats = {
            totalTemplates: settingsData.counts?.templates || templateData.total || 0,
            imageFiles: settingsData.counts?.imageBlobs || 0,
            styleTemplates: settingsData.counts?.styleTemplates || 0
        };
        awesomeTemplates = templateData.items || [];
        populateGenerationControls();
        await ensureHeroTemplateData();
        renderHeroTemplates();
        renderHomeTemplateGrid();
        return awesomeTemplates;
    })();
    return templateDataPromise;
}

async function ensureHeroTemplateData() {
    const heroIds = (publicSettings.heroTemplateIds || []).filter(Boolean);
    if (!heroIds.length) return [];

    const missingIds = heroIds.filter(id => !awesomeTemplates.some(item => item.id === id) && !heroTemplateLookup[id]);
    if (missingIds.length) {
        const fetchedTemplates = await Promise.all(
            missingIds.map(async id => {
                try {
                    const data = await apiGet(`/api/templates/${encodeURIComponent(id)}`);
                    return data.item || null;
                } catch (error) {
                    console.warn("Failed to load hero template", id, error);
                    return null;
                }
            })
        );
        fetchedTemplates.forEach(template => {
            if (template?.id) heroTemplateLookup[template.id] = template;
        });
    }

    return heroIds
        .map(id => awesomeTemplates.find(item => item.id === id) || heroTemplateLookup[id] || null)
        .filter(Boolean);
}

async function initAwesomeTemplateLibrary() {
    const grid = document.getElementById("awesomeTemplateGrid");
    const count = document.getElementById("awesomeTemplateCount");
    const imageCount = document.getElementById("awesomeImageCount");
    const styleCount = document.getElementById("awesomeStyleCount");

    if (!grid) return;

    try {
        await ensureTemplateData();
    } catch (error) {
        setHeroShowcaseReady();
        const serviceUrl = servicePageUrl("index.html");
        grid.innerHTML = `
            <article class="awesome-template-card loading-card">
                <div class="awesome-template-cover"></div>
                <div>
                    <span>服务地址</span>
                    <h3>请通过本地服务打开</h3>
                    <p>后台服务已启动时，直接访问本地站点地址即可读取数据库模板。</p>
                    <small>${serviceUrl}</small>
                    <a class="card-action" href="${serviceUrl}">打开本地服务</a>
                </div>
            </article>
        `;
        return;
    }

    if (count) count.textContent = awesomeStats.totalTemplates;
    if (imageCount) imageCount.textContent = awesomeStats.imageFiles;
    if (styleCount) styleCount.textContent = awesomeStats.styleTemplates;

    renderAwesomeTemplateCards();

    grid.addEventListener("click", event => {
        const trigger = event.target.closest("[data-template-id]");
        if (!trigger) return;

        const templateId = trigger.dataset.templateId;
        openAwesomeTemplate(templateId);
    });
}

function getPopularTemplates(templates) {
    const featured = templates.filter(template => template.featured);
    const withParams = templates.filter(template => template.params?.length);
    const merged = [...featured, ...withParams, ...templates];
    const seen = new Set();

    return merged.filter(template => {
        if (seen.has(template.id)) return false;
        seen.add(template.id);
        return true;
    }).slice(0, POPULAR_TEMPLATE_LIMIT);
}

function renderHomeTemplateGrid() {
    const grid = document.getElementById("homeTemplateGrid");
    if (!grid || !awesomeTemplates.length) return;
    renderHomeCategoryFilters();
    const visibleTemplates = awesomeTemplates.slice(0, 6);
    grid.innerHTML = visibleTemplates.map(template => {
        const title = getLocalized(template.title);
        const category = getCategoryLabel(template.categoryLabel || template.category);
        const cover = assetUrl(template.cover || template.sourceCase?.image || "");
        const isVideo = isVideoTemplate(template);
        const filterKey = getHomeFilterKey(template, category);
        const target = isVideo ? `#video-workbench:${encodeURIComponent(template.id)}` : `#template-editor:${encodeURIComponent(template.id)}`;
        const action = isVideo ? "生成视频" : "使用模板";
        return `
            <article class="template-card" data-category="${escapeHtml(filterKey)}">
                <button class="template-cover" type="button" data-template-id="${escapeAttr(template.id)}" style="--cover:${cssUrl(cover)}" aria-label="使用 ${escapeHtml(title)} 模板"></button>
                <div class="template-body">
                    <span class="tag ${isVideo ? "brown" : ""}">${escapeHtml(isVideo ? "短视频" : category)}</span>
                    <h3>${escapeHtml(title)}</h3>
                    <p>${escapeHtml(getLocalized(template.description) || "选择后可调整参数和提示词。")}</p>
                    <div class="card-meta">
                        <span>${Number(template.usageToday || template.usageCount || 0).toLocaleString("zh-CN")} 人用过</span>
                        <strong>${Number(template.creditCost || 5)} 积分/${isVideo ? "条" : "张"}</strong>
                    </div>
                    <a href="${escapeAttr(target)}" class="card-action" data-template-id="${escapeAttr(template.id)}">${action}</a>
                </div>
            </article>
        `;
    }).join("");

    grid.querySelectorAll("[data-template-id]").forEach(trigger => {
        trigger.addEventListener("click", event => {
            const template = awesomeTemplates.find(item => item.id === trigger.dataset.templateId);
            if (isVideoTemplate(template)) {
                event.preventDefault();
                openVideoTemplate(trigger.dataset.templateId);
                return;
            }
            event.preventDefault();
            openAwesomeTemplate(trigger.dataset.templateId);
        });
    });
    applyHomeTemplateFilter(activeHomeCategoryFilter);
}

function slugifyForFilter(value = "") {
    return String(value).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "-").replace(/^-|-$/g, "") || "all";
}

function getHomeFilterKey(template, categoryLabel = "") {
    if (template?.modality === "video" || template?.templateKind === "video") return "video";
    return slugifyForFilter(categoryLabel || template?.categoryLabel || template?.category || "other");
}

function renderHomeCategoryFilters() {
    const row = document.getElementById("homeCategoryRow");
    if (!row) return;

    const counts = new Map();
    awesomeTemplates.slice(0, POPULAR_TEMPLATE_LIMIT).forEach(template => {
        const label = template?.modality === "video" || template?.templateKind === "video"
            ? "短视频"
            : getCategoryLabel(template.categoryLabel || template.category);
        const key = getHomeFilterKey(template, label);
        const current = counts.get(key) || { key, label, count: 0 };
        current.count += 1;
        counts.set(key, current);
    });

    const topCategories = Array.from(counts.values())
        .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, "zh-CN"))
        .slice(0, HOME_CATEGORY_LIMIT);

    const validKeys = new Set(["all", ...topCategories.map(item => item.key)]);
    if (!validKeys.has(activeHomeCategoryFilter)) activeHomeCategoryFilter = "all";

    row.innerHTML = [
        `<button class="chip ${activeHomeCategoryFilter === "all" ? "active" : ""}" data-filter="all">全部</button>`,
        ...topCategories.map(item => `<button class="chip ${activeHomeCategoryFilter === item.key ? "active" : ""}" data-filter="${escapeHtml(item.key)}">${escapeHtml(item.label)}</button>`)
    ].join("");

    bindHomeTemplateFilterEvents();
}

function bindHomeTemplateFilterEvents() {
    document.querySelectorAll("#homeCategoryRow .chip[data-filter]").forEach(chip => {
        chip.addEventListener("click", () => applyHomeTemplateFilter(chip.dataset.filter || "all"));
    });
}

function applyHomeTemplateFilter(filter = "all") {
    activeHomeCategoryFilter = filter || "all";
    document.querySelectorAll("#homeCategoryRow .chip[data-filter]").forEach(chip => {
        chip.classList.toggle("active", chip.dataset.filter === activeHomeCategoryFilter);
    });
    document.querySelectorAll("#homeTemplateGrid .template-card").forEach(card => {
        const show = activeHomeCategoryFilter === "all" || card.dataset.category === activeHomeCategoryFilter;
        card.style.display = show ? "" : "none";
    });
}

function renderAwesomeTemplateCards() {
    const grid = document.getElementById("awesomeTemplateGrid");
    const visibleInfo = document.getElementById("awesomeVisibleInfo");
    const templates = awesomeTemplates;

    if (!grid || !templates.length) return;

    const visibleTemplates = templates.slice(0, POPULAR_TEMPLATE_LIMIT);

    grid.innerHTML = visibleTemplates.map(template => {
        const title = getLocalized(template.title);
        const description = getLocalized(template.description);
        const tags = Array.isArray(template.tags) ? template.tags.slice(0, 3).join(" / ") : "";
        const paramCount = Array.isArray(template.params) ? template.params.length : 0;
        const sourceTitle = template.sourceLabel || template.sourceCase?.title || "本地案例";
        const cover = assetUrl(template.cover || template.sourceCase?.image || "");

        return `
            <article class="awesome-template-card" data-template-id="${escapeHtml(template.id)}">
                <button class="awesome-template-cover" type="button" data-template-id="${escapeHtml(template.id)}" aria-label="使用 ${escapeHtml(title)} 模板">
                    <img src="${escapeHtml(cover)}" alt="${escapeHtml(template.imageAlt || title)}" loading="lazy">
                </button>
                <div>
                    <span>${escapeHtml(getCategoryLabel(template.category))}</span>
                    <h3>${escapeHtml(title)}</h3>
                    <p>${escapeHtml(description)}</p>
                    <small>${escapeHtml(paramCount ? `${paramCount} 个可调参数 / ${sourceTitle}` : `可编辑 Prompt / ${sourceTitle}`)}</small>
                    <button class="card-action awesome-use-template" type="button" data-template-id="${escapeHtml(template.id)}">使用模板</button>
                </div>
            </article>
        `;
    }).join("");

    if (visibleInfo) {
        visibleInfo.textContent = `首页精选 ${visibleTemplates.length} 个模板，完整 ${awesomeStats.totalTemplates || templates.length} 个在模板库页`;
    }
}

function getLocalized(value) {
    if (!value) return "";
    if (typeof value === "string") return value;
    return value.zh || value.en || "";
}

function getCategoryLabel(category) {
    return CATEGORY_LABELS[category] || category || "未分类";
}

const PROMPT_GUIDE_PATTERNS = {
    subject: [
        [/family|parents|children|child|kids?|friends?|selfie|couple/i, "家庭亲子 / 朋友合影"],
        [/pet|cat|dog|puppy|kitten/i, "宠物头像 / 宠物写真"],
        [/product|e-?commerce|packaging|bottle|cosmetic|jewelry/i, "商品展示 / 电商主图"],
        [/brand|logo|identity|mascot/i, "品牌视觉 / Logo 延展"],
        [/portrait|headshot|character|person|people|girl|boy|woman|man/i, "人物形象 / 角色头像"],
        [/ui|interface|app|dashboard|website/i, "界面设计 / 应用展示"],
        [/poster|typography|cover|flyer|banner/i, "海报封面 / 字体排版"]
    ],
    scene: [
        [/travel|vacation|tourist|trip|journey/i, "旅行打卡"],
        [/city|urban|street|station|subway|airport|train/i, "城市街区 / 交通站点"],
        [/shopping|mall|store|market|cafe|restaurant/i, "商场门店 / 生活消费"],
        [/outdoor|nature|park|forest|garden|playground/i, "户外自然 / 公园游乐"],
        [/home|room|interior|bedroom|kitchen|office/i, "室内空间"],
        [/beach|sea|ocean|mountain|lake/i, "自然风景"],
        [/studio|white background|clean background/i, "棚拍 / 干净背景"]
    ],
    style: [
        [/kawaii|cute|adorable|chibi/i, "可爱萌系"],
        [/anime|manga|cartoon/i, "动漫插画"],
        [/paper-?cut|paper craft|diorama|cardboard|felt|layered paper/i, "纸雕 / 手工拼贴"],
        [/collage|scrapbook|sticker/i, "拼贴手账 / 贴纸风"],
        [/photorealistic|realistic|cinematic photo|photography/i, "写实摄影"],
        [/watercolor|gouache|oil painting|painting/i, "绘画质感"],
        [/3d|clay|toy|miniature/i, "3D 玩具 / 微缩模型"],
        [/minimal|clean|flat/i, "简洁扁平"],
        [/luxury|premium|editorial/i, "高级商业感"]
    ],
    mood: [
        [/pastel|soft color|warm|cozy|nostalgic|dreamy/i, "柔和温暖"],
        [/dramatic|cinematic|moody/i, "电影感"],
        [/playful|whimsical|fun/i, "轻松有趣"],
        [/fresh|bright|sunny/i, "明亮清新"],
        [/dark|noir|cyberpunk|neon/i, "暗色霓虹"]
    ],
    composition: [
        [/vertical|portrait orientation|9:16|4:5|2:3/i, "竖版构图"],
        [/horizontal|landscape|16:9|3:2|wide/i, "横版构图"],
        [/square|1:1/i, "方图构图"],
        [/close-?up|macro/i, "近景特写"],
        [/full body|wide shot|panorama/i, "全身 / 大场景"]
    ]
};

function promptGuideMatches(text, entries, limit = 4) {
    const found = [];
    entries.forEach(([pattern, label]) => {
        if (pattern.test(text) && !found.includes(label)) found.push(label);
    });
    return found.slice(0, limit);
}

function normalizePromptFieldLabel(value = "") {
    const raw = String(value || "").trim();
    const text = raw.toLowerCase().replace(/[_-]+/g, " ");
    const rules = [
        [/package|packaging|box|container/, "包装类型"],
        [/product|item|object|goods/, "商品/主体"],
        [/brand|logo/, "品牌名/Logo"],
        [/text|copy|headline|title|slogan|label/, "文字内容"],
        [/scene|location|place|background|environment/, "场景/背景"],
        [/style|visual|aesthetic/, "视觉风格"],
        [/color|palette|tone/, "颜色/主色"],
        [/material|texture|finish/, "材质质感"],
        [/character|person|people|subject|model/, "人物/主体"],
        [/pet|animal/, "宠物/动物"],
        [/mood|emotion|atmosphere/, "氛围情绪"],
        [/size|ratio|composition|layout/, "构图比例"],
        [/camera|angle|view|perspective/, "视角/镜头"]
    ];
    const matched = rules.find(([pattern]) => pattern.test(text));
    if (matched) return matched[1];
    return raw || "自定义内容";
}

function buildTemplateGuideText(text = "", template = {}) {
    const tags = Array.isArray(template.tags) ? template.tags : [];
    const scenes = Array.isArray(template.scenes) ? template.scenes : [];
    return [
        text,
        getLocalized(template.title),
        getLocalized(template.description),
        template.category,
        template.categoryLabel,
        template.sourceCase?.category,
        template.sourceCase?.promptPreview,
        ...tags,
        ...scenes
    ].filter(Boolean).join(" ").toLowerCase();
}

function detectTemplateUseCase(text = "", template = {}) {
    const haystack = buildTemplateGuideText(text, template);
    const categoryText = `${template.category || ""} ${template.categoryLabel || ""}`.toLowerCase();
    const cases = [
        {
            id: "packaging",
            weight: [
                [/包装|包装结构|包装盒|礼盒|盒型|纸盒|袋装|吊卡|包装设计|パッケージ|package type|product packaging|industrial design packaging|packaging|retail box|gift box|opp bag|pouch|sachet|carton|blister pack|box design/, 8],
                [/products? & e-?commerce|产品与电商/, 1]
            ],
            summary: "这个模板适合生成商品包装结构图、礼盒方案、产品设定稿。用户重点改包装类型、商品品类、品牌文字、材质颜色和展示视角。",
            targets: ["包装类型", "商品品类", "品牌名/文字", "材质颜色", "展示角度"],
            tags: ["包装设计", "商品展示", "结构图", "材质标注", "商业出图"],
            placeholder: "例如：把包装类型改成高端咖啡豆礼盒，品牌名写成「MORNING LAB」，主色用深绿色和奶油白，材质是磨砂纸盒，保留结构图和尺寸标注。"
        },
        {
            id: "storeDisplay",
            weight: [
                [/展架|立牌|门店|餐饮|异形|kt板|套餐|促销|主推产品|本地生活|pop\s|display stand|standee|retail display|point of sale|store signage/, 8],
                [/products? & e-?commerce|产品与电商/, 1]
            ],
            summary: "这个模板适合做门店异形展架、餐饮立牌、促销物料成品图。用户重点改品牌名、主标题、主推产品、卖点标签、促销信息和主色调。",
            targets: ["品牌名", "主标题", "主推产品", "卖点标签", "促销信息", "主色调"],
            tags: ["门店物料", "异形展架", "餐饮促销", "商业落地", "成品展示"],
            placeholder: "例如：品牌名改成「阿婆小面」，主标题写「招牌牛肉面」，主推产品是红烧牛肉面，加卖点「现熬牛骨汤」「大块牛肉」，主色用番茄红和暖黄色。"
        },
        {
            id: "product",
            weight: [
                [/商品|产品|电商|主图|详情页|商业广告|product|e-?commerce|commercial|bottle|cosmetic|jewelry|shoe|bag|watch|skincare|food photography/, 5],
                [/products? & e-?commerce|产品与电商/, 3]
            ],
            summary: "这个模板适合做商品主图、详情页视觉或商业广告图。用户重点改商品、卖点、背景、材质和色彩。",
            targets: ["商品主体", "卖点/文案", "背景场景", "材质质感", "主色调"],
            tags: ["商品图", "电商主图", "商业广告", "质感表现"],
            placeholder: "例如：把商品改成一瓶蓝色精华液，背景是浅灰高端浴室台面，突出补水和清透质感，画面更适合小红书封面。"
        },
        {
            id: "familyTravel",
            weight: [
                [/亲子|旅行|旅游|朋友|合影|妈妈|孩子|手账|贴纸|family|parents|children|kids?|travel|vacation|tourist|selfie|scrapbook|collage/, 6]
            ],
            summary: "这个模板适合做亲子旅行、朋友出游、生活记录类拼贴图。用户重点改人物关系、城市地点、游玩场景和贴纸文字。",
            targets: ["人物关系", "旅行地点", "具体场景", "贴纸文字", "整体氛围"],
            tags: ["亲子旅行", "拼贴手账", "小红书", "可爱贴纸", "生活记录"],
            placeholder: "例如：把地点改成上海迪士尼，人物换成妈妈和两个孩子，加入城堡、气球和游乐园贴纸，整体更像小红书旅行手账。"
        },
        {
            id: "portrait",
            weight: [
                [/人像|头像|人物|角色|写真|portrait|headshot|character|person|people|girl|boy|woman|man|avatar/, 5],
                [/characters? & people|人物与角色/, 3]
            ],
            summary: "这个模板适合做人像、头像、角色设定或人物写真。用户重点改人物身份、服装、表情、背景和画面风格。",
            targets: ["人物身份", "服装造型", "表情动作", "背景环境", "风格质感"],
            tags: ["人物头像", "角色设定", "写真", "表情动作"],
            placeholder: "例如：把人物改成 28 岁咖啡店主理人，穿米色风衣，表情自然微笑，背景是上海街边咖啡馆，整体温暖写实。"
        },
        {
            id: "poster",
            weight: [
                [/海报|封面|主视觉|标题|广告语|poster|flyer|cover|banner|typography|headline|campaign/, 5],
                [/posters? & typography|海报与字体/, 4]
            ],
            summary: "这个模板适合做海报、封面、活动主视觉。用户重点改标题文字、活动主题、视觉元素、配色和版式比例。",
            targets: ["标题文字", "活动主题", "核心元素", "配色", "版式比例"],
            tags: ["海报", "封面", "活动主视觉", "字体排版"],
            placeholder: "例如：做一张夏季新品发布海报，标题是「清爽一夏」，主色蓝白，加入冰块、水花和产品瓶，适合 4:5 社媒封面。"
        },
        {
            id: "brand",
            weight: [
                [/品牌|标志|视觉识别|品牌名称|logo|brand|identity|mascot|visual system|key visual|\bkv\b/, 6],
                [/brand & logos|品牌与标志/, 6]
            ],
            summary: "这个模板适合做品牌视觉、Logo 延展或吉祥物设计。用户重点改品牌名、行业属性、符号元素、色彩和应用场景。",
            targets: ["品牌名", "行业属性", "符号元素", "品牌色", "应用场景"],
            tags: ["品牌设计", "Logo", "吉祥物", "视觉系统"],
            placeholder: "例如：品牌名改成「云野茶室」，行业是新中式茶饮，加入云朵和茶叶符号，主色墨绿和米白，整体高级安静。"
        },
        {
            id: "ui",
            weight: [
                [/界面|应用|网页|仪表盘|后台|登录页|组件|ui|interface|app|dashboard|website|mobile screen|web app/, 6],
                [/ui & interfaces|ui 与界面/, 6]
            ],
            summary: "这个模板适合生成应用界面、网页视觉、仪表盘或产品 UI 展示。用户重点改产品类型、页面模块、核心数据、品牌色和设备场景。",
            targets: ["产品类型", "页面模块", "核心数据", "品牌色", "设备场景"],
            tags: ["UI 界面", "应用展示", "网页视觉", "产品原型"],
            placeholder: "例如：把产品改成健身教练预约 App，页面包含课程卡片、日历、会员数据和预约按钮，主色用黑白加荧光绿，整体干净运动感。"
        },
        {
            id: "pet",
            weight: [
                [/宠物|猫|狗|兔|仓鼠|毛孩子|拍立得|pet|cat|dog|puppy|kitten|animal|polaroid-style watercolor pet/, 8]
            ],
            summary: "这个模板适合做宠物头像、宠物写真或萌宠周边图。用户重点改宠物种类、毛色、表情、动作和背景。",
            targets: ["宠物种类", "毛色特征", "表情动作", "背景", "风格"],
            tags: ["宠物", "萌系", "头像", "周边图"],
            placeholder: "例如：把宠物改成一只银渐层猫，圆脸大眼睛，戴红色围巾，背景是冬天窗边，整体温暖可爱。"
        },
        {
            id: "space",
            weight: [
                [/建筑|空间|室内|房间|家居|店面|architecture|interior|room|home|kitchen|office|storefront|retail space/, 5],
                [/architecture & spaces|建筑与空间/, 6]
            ],
            summary: "这个模板适合做建筑空间、室内设计、门店场景或家居氛围图。用户重点改空间类型、功能区域、材质、灯光和陈设。",
            targets: ["空间类型", "功能区域", "材质", "灯光", "陈设风格"],
            tags: ["建筑空间", "室内设计", "场景氛围", "材质灯光"],
            placeholder: "例如：把空间改成 40 平米社区咖啡店，加入吧台、两人座、木质墙面和暖色吊灯，整体是安静自然的日式杂志感。"
        }
    ];

    const ranked = cases
        .map(item => ({
            ...item,
            score: item.weight.reduce((total, [pattern, score]) => {
                const targetText = score >= 6 && /&|与/.test(String(pattern)) ? categoryText : haystack;
                return total + (pattern.test(targetText) ? score : 0);
            }, 0)
        }))
        .filter(item => item.score > 0)
        .sort((a, b) => b.score - a.score);

    return ranked[0] || {
        id: "general",
        summary: "这个模板已经固定了基础构图和画面质感。用户主要改主体、场景、颜色、文字和风格要求即可。",
        targets: ["主体内容", "场景/背景", "文字内容", "颜色氛围", "风格质感"],
        tags: ["通用模板", "可改主体", "可改场景", "可改风格"],
        placeholder: "例如：把主体改成你的产品或人物，说明要出现的场景、颜色、文字和风格；没有特别要求的部分会沿用模板底稿。"
    };
}

function uniquePromptItems(items, limit = 8) {
    return [...new Set(items.filter(Boolean).map(item => String(item).trim()).filter(Boolean))].slice(0, limit);
}

function templateParamTargets(params = []) {
    return uniquePromptItems(params.map(param => normalizePromptFieldLabel(param.label || param.key)), 6);
}

function getTemplatePromptText(template = {}, prompt = "") {
    return [
        prompt,
        getLocalized(template.title),
        getLocalized(template.description),
        template.promptTemplate,
        template.sourceCase?.promptPreview
    ].filter(Boolean).join(" ").toLowerCase();
}

function templateParamLabels(params = [], limit = 4) {
    return uniquePromptItems(params.map(param => param.label || param.key), limit);
}

function buildTemplateSpecificPlaceholder(template = {}, useCase = {}, params = []) {
    const title = getLocalized(template.title) || "";
    const text = getTemplatePromptText(template, template.promptTemplate || "");
    const labels = templateParamLabels(params, 4);
    const labelHint = labels.length ? `左侧先改「${labels.join("」「")}」；` : "";

    if (/夹层|2x2|grid|sandwich|layering|editorial designer/.test(text)) {
        return `${labelHint}例如：品牌名改成「Tesla」，主体选择汽车和钥匙扣，使用低饱和红黑灰品牌色，保留 2x2 网格、几何色块和前后遮挡的夹层效果。`;
    }

    if (/奶茶|茶饮|喜茶|蜜雪|抹茶|咖啡|饮品|matcha|\btea\b|\bdrink\b|\blatte\b|\bcoffee\b|\bbubble tea\b/.test(text)) {
        if (/kv|key visual|概念海报|广告|poster/.test(text)) {
            return `${labelHint}例如：品牌改成「茶百道」，主推产品写「杨枝甘露奶茶」，广告语写「一口清爽刚刚好」，目标人群是年轻女生，画面保持高级茶饮 KV 海报质感。`;
        }
        if (/触点|视觉板|touchpoint|identity|system|merchandise/.test(text)) {
            return `${labelHint}例如：品牌名改成「山野抹茶」，产品改成抹茶拿铁和抹茶甜品组合，保留杯子、包装盒、手提袋、贴纸和菜单卡的整套品牌触点展示。`;
        }
        return `${labelHint}例如：把主体改成一杯厚乳抹茶拿铁，加入茶叶、冰块和奶盖飞溅，主色用抹茶绿和米白，整体清爽高级。`;
    }

    if (/展架|立牌|门店|餐饮|pop\s|standee|display stand/.test(text)) {
        return `${labelHint}例如：品牌名改成「阿婆小面」，主标题写「招牌牛肉面」，主推产品是红烧牛肉面，加卖点「现熬牛骨汤」「大块牛肉」，主色用番茄红和暖黄色。`;
    }

    if (/包装|礼盒|盒型|纸盒|package|packaging|retail box|gift box|opp bag|pouch/.test(text)) {
        return `${labelHint}例如：把包装改成高端咖啡豆礼盒，品牌名写「MORNING LAB」，主色用深绿色和奶油白，材质是磨砂纸盒，保留结构图、展开视图和尺寸标注。`;
    }

    if (/品牌|logo|identity|brand|visual system|mascot/.test(text)) {
        return `${labelHint}例如：品牌名改成「云野茶室」，行业是新中式茶饮，加入云朵和茶叶符号，主色墨绿和米白，应用场景包含杯子、包装和社媒封面。`;
    }

    if (/宠物|猫|狗|兔|仓鼠|毛孩子|pet|cat|dog|puppy|kitten/.test(text)) {
        return `${labelHint}例如：宠物改成一只银渐层猫，圆脸大眼睛，戴红色围巾，名字写「糯米」，背景是冬天窗边，整体温暖可爱。`;
    }

    if (/人像|头像|人物|角色|portrait|headshot|character|girl|boy|woman|man/.test(text)) {
        return `${labelHint}例如：人物改成 28 岁咖啡店主理人，穿米色风衣，自然微笑，背景是上海街边咖啡馆，整体温暖写实。`;
    }

    if (/ui|界面|app|dashboard|website|interface/.test(text)) {
        return `${labelHint}例如：产品改成健身教练预约 App，页面包含课程卡片、日历、会员数据和预约按钮，主色用黑白加荧光绿，整体干净运动感。`;
    }

    return `${labelHint}${useCase.placeholder || "例如：把主体、场景、颜色、文字和风格改成你自己的要求；没有特别说明的部分会沿用当前模板。"}${title ? ` 当前模板是「${title}」，尽量保留它的构图和质感。` : ""}`;
}

function renderTemplatePromptGuide(template, prompt) {
    const target = document.getElementById("templatePromptGuide");
    if (!target) return;
    const params = Array.isArray(template?.params) ? template.params : [];
    const useCase = detectTemplateUseCase(prompt || "", template || {});
    const paramTargets = templateParamTargets(params);
    const editTargets = uniquePromptItems([...useCase.targets, ...paramTargets], 6);
    const category = getCategoryLabel(template?.categoryLabel || template?.category);
    const tags = uniquePromptItems([...useCase.tags, category && category !== "未分类" ? category : ""], 9);
    const title = getLocalized(template?.title) || "这个模板";
    const paramAdvice = params.length
        ? `左侧已有 ${params.length} 个参数位，建议先改参数；如果还想补充特殊要求，就写在下面的自定义修改要求里。`
        : "这个模板没有参数位，建议直接在下面的自定义修改要求里描述你要替换的主体、场景、颜色和文字。";

    target.innerHTML = `
        <span>中文创作说明</span>
        <strong>${escapeHtml(title)}</strong>
        <p>${escapeHtml(useCase.summary)}</p>
        <div class="prompt-guide-section">
            <b>建议优先修改</b>
            <div class="prompt-guide-list">
                ${editTargets.map(item => `<em>${escapeHtml(item)}</em>`).join("")}
            </div>
        </div>
        <div class="prompt-guide-section">
            <b>模板用途</b>
            <div class="prompt-guide-tags">
                ${tags.map(item => `<em>${escapeHtml(item)}</em>`).join("") || "<em>通用模板</em>"}
            </div>
        </div>
        <p>${escapeHtml(paramAdvice)}</p>
    `;

    const userEdit = document.getElementById("templateUserPromptEdit");
    if (userEdit) {
        userEdit.placeholder = buildTemplateSpecificPlaceholder(template, useCase, params);
        userEdit.dataset.templateId = template?.id || "";
    }
    const userHint = document.getElementById("templateUserPromptHint");
    if (userHint) {
        userHint.textContent = params.length
            ? `这里写中文补充要求，会和「${title}」模板底稿、左侧 ${params.length} 个参数一起提交生成。`
            : `这里写中文补充要求，会和「${title}」模板底稿一起提交生成；没有写到的部分沿用模板。`;
    }
}

async function initTemplateEditor() {
    document.getElementById("templateParamForm")?.addEventListener("input", event => {
        const field = event.target.closest("[data-param-key]");
        if (!field || !activeAwesomeTemplate) return;

        activeTemplateValues[field.dataset.paramKey] = field.value;
        updateTemplatePromptFromParams();
    });
    document.getElementById("templateParamForm")?.addEventListener("click", event => {
        const button = event.target.closest(".param-choice-group [data-param-key]");
        if (!button || !activeAwesomeTemplate) return;
        const key = button.dataset.paramKey;
        activeTemplateValues[key] = button.dataset.paramValue || button.textContent.trim();
        button.closest(".param-choice-group")?.querySelectorAll("button").forEach(item => {
            item.classList.toggle("active", item === button);
        });
        updateTemplatePromptFromParams();
    });

    document.getElementById("templatePromptEditor")?.addEventListener("input", () => {
        updatePromptStats();
        if (activeAwesomeTemplate) {
            renderTemplatePromptGuide(activeAwesomeTemplate, document.getElementById("templatePromptEditor")?.value || "");
        }
    });
    document.getElementById("templateUserPromptEdit")?.addEventListener("input", updatePromptStats);
    document.getElementById("copyTemplatePrompt")?.addEventListener("click", copyTemplatePrompt);
    document.getElementById("resetTemplateParams")?.addEventListener("click", resetTemplateParams);
    document.getElementById("generateFromTemplate")?.addEventListener("click", requestTemplateGeneration);
    document.getElementById("downloadTemplateResult")?.addEventListener("click", downloadTemplateResult);
    initTemplateReferenceUpload();
    document.getElementById("templateGenerationConfig")?.addEventListener("change", event => {
        if (event.target?.id === "templateModel") {
            populateSizeOptionsForModel();
            syncTemplateSizeSelection({ force: false });
        }
        if (event.target?.id === "templateAspectRatio") {
            syncTemplateSizeSelection({ force: false });
        }
        if (event.target?.id === "templateImageSize") {
            const size = document.getElementById("templateImageSize");
            if (size) {
                size.dataset.manual = "1";
            }
        }
        updateOfficialImageOptions();
        updateTemplateCreditEstimate();
    });

    const initialId = getTemplateIdFromLocation();
    try {
        const templates = await ensureTemplateData();
        if (initialId) {
            await openAwesomeTemplate(initialId, false);
        } else {
            const imageTemplates = templates.filter(template => !isVideoTemplate(template));
            const defaultTemplate = imageTemplates.find(template => template.params?.length) || imageTemplates[0];
            if (!defaultTemplate) return;
            renderTemplateEditor(defaultTemplate, { shouldScroll: false, updateUrl: false });
        }
    } catch (error) {
        setText("editorResultSummary", "后端 API 未连接，无法读取数据库模板。");
    }
}

function getTemplateIdFromLocation() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("template")) return params.get("template");

    const hashMatch = window.location.hash.match(/^#template-editor[:=]([^&]+)/);
    return hashMatch ? decodeURIComponent(hashMatch[1]) : "";
}

function getVideoTemplateIdFromLocation() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("videoTemplate")) return params.get("videoTemplate");

    const hashMatch = window.location.hash.match(/^#video-workbench[:=]([^&]+)/);
    return hashMatch ? decodeURIComponent(hashMatch[1]) : "";
}

function initTemplateHashSync() {
    window.addEventListener("hashchange", async () => {
        const videoTemplateId = getVideoTemplateIdFromLocation();
        if (videoTemplateId) {
            try {
                await openVideoTemplate(videoTemplateId, false);
            } catch (error) {
                showToast(error.message || "切换视频模板失败", "error");
            }
            return;
        }

        const templateId = getTemplateIdFromLocation();
        if (!templateId) return;
        if (activeAwesomeTemplate?.id === templateId) {
            renderTemplatePromptGuide(activeAwesomeTemplate, document.getElementById("templatePromptEditor")?.value || activeAwesomeTemplate.promptTemplate || "");
            return;
        }
        try {
            await ensureTemplateData();
            await openAwesomeTemplate(templateId, false);
        } catch (error) {
            showToast(error.message || "切换模板失败", "error");
        }
    });
}

async function openAwesomeTemplate(templateId, updateUrl = true) {
    const requestedId = String(templateId || "");
    let template = awesomeTemplates.find(item => item.id === requestedId || item.sourceTemplateId === requestedId);
    const listedParamCount = Number(template?.paramCount || 0);
    const listedParams = Array.isArray(template?.params) ? template.params : [];
    const needsFullTemplate = !template
        || !Array.isArray(template.params)
        || template.id !== requestedId
        || (listedParamCount > 0 && listedParams.length < listedParamCount);

    if (needsFullTemplate) {
        try {
            const data = await apiGet(`/api/templates/${encodeURIComponent(requestedId)}`);
            template = data.item;
            const existingIndex = awesomeTemplates.findIndex(item => item.id === template?.id);
            if (existingIndex >= 0) {
                awesomeTemplates[existingIndex] = { ...awesomeTemplates[existingIndex], ...template };
            } else if (template) {
                awesomeTemplates.unshift(template);
            }
        } catch (error) {
            template = null;
        }
    }

    if (!template) {
        showToast("没有在数据库里找到对应模板", "error");
        return;
    }

    if (isVideoTemplate(template)) {
        openVideoTemplate(template.id || requestedId, updateUrl);
        return;
    }

    renderTemplateEditor(template, { shouldScroll: true, updateUrl });
}

function renderTemplateEditor(template, options = {}) {
    if (isVideoTemplate(template)) {
        openVideoTemplate(template.id, options.updateUrl !== false);
        return;
    }

    const title = getLocalized(template.title) || "案例模板";
    const description = getLocalized(template.description) || template.sourceCase?.promptPreview || "";
    const params = Array.isArray(template.params) ? template.params : [];

    activeAwesomeTemplate = template;
    activeTemplateValues = Object.fromEntries(params.map(param => [param.key, param.default || ""]));
    const userEdit = document.getElementById("templateUserPromptEdit");
    if (userEdit) userEdit.value = "";

    setText("editorTemplateTitle", title);
    setText("editorTemplateDescription", description);
    setText("editorResultTitle", title);
    setText("editorResultSummary", params.length ? "先改左侧参数；需要额外定制时，在右侧写中文修改要求。" : "这个模板没有参数位，直接在右侧写中文修改要求即可。");
    setText("editorResultMeta", "生成完成后可下载高清图。");
    setText("promptTemplateName", title);
    setText("promptTemplateMeta", `${Number(template.creditCost || 5)} 积分基础 · ${params.length || 0} 个参数`);
    setCover("promptTemplateImage", template.cover || template.image || template.coverUrl || template.imageUrl || "");

    resetTemplateResultPreview();
    setTemplateGenerationDefaults(template);
    renderTemplateParamForm(template);
    updateTemplatePromptFromParams();

    document.querySelectorAll(".awesome-template-card").forEach(card => {
        card.classList.toggle("active", card.dataset.templateId === template.id);
    });

    if (options.updateUrl !== false) {
        history.replaceState(null, "", `#template-editor:${encodeURIComponent(template.id)}`);
    }

    if (options.shouldScroll !== false) {
        document.getElementById("template-editor")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function renderTemplateParamForm(template) {
    const form = document.getElementById("templateParamForm");
    if (!form) return;

    const params = Array.isArray(template.params) ? template.params : [];
    if (!params.length) {
        form.innerHTML = `
            <div class="param-empty">
                <strong>这个模板没有识别到参数位</strong>
                <p>直接在右侧「自定义修改要求」里写要替换的主体、场景、文字和颜色；高级用户可展开英文底稿微调。</p>
            </div>
        `;
        return;
    }

    form.innerHTML = `
        <div class="param-header">
            <span>可调参数</span>
            <strong>${params.length} 项</strong>
        </div>
        <div class="param-grid">
            ${params.map(param => renderParamField(param)).join("")}
        </div>
    `;
}

function renderParamField(param) {
    const value = activeTemplateValues[param.key] ?? param.default ?? "";
    const label = param.label || param.key;
    const options = Array.isArray(param.options) ? param.options.filter(Boolean) : [];
    if (options.length) {
        return `
            <label class="param-field param-choice-field">
                <span>${escapeHtml(label)}</span>
                <div class="param-choice-group" data-param-choice="${escapeAttr(param.key)}">
                    ${options.map(option => `
                        <button type="button" class="${String(value) === String(option) ? "active" : ""}" data-param-key="${escapeAttr(param.key)}" data-param-value="${escapeAttr(option)}">${escapeHtml(option)}</button>
                    `).join("")}
                </div>
            </label>
        `;
    }
    const isLong = value.length > 70 || /prompt|description|content|copy|主题|说明|描述|内容/i.test(label);

    if (isLong) {
        return `
            <label class="param-field param-field-wide">
                <span>${escapeHtml(label)}</span>
                <textarea data-param-key="${escapeHtml(param.key)}" rows="3">${escapeHtml(value)}</textarea>
            </label>
        `;
    }

    return `
        <label class="param-field">
            <span>${escapeHtml(label)}</span>
            <input data-param-key="${escapeHtml(param.key)}" type="text" value="${escapeHtml(value)}">
        </label>
    `;
}

function updateTemplatePromptFromParams() {
    if (!activeAwesomeTemplate) return;

    const prompt = buildPrompt(activeAwesomeTemplate, activeTemplateValues);
    const editor = document.getElementById("templatePromptEditor");
    if (editor) editor.value = prompt;
    renderTemplatePromptGuide(activeAwesomeTemplate, prompt);
    updatePromptStats();
}

function buildPrompt(template, values = {}) {
    let prompt = template.promptTemplate || "";
    const params = Array.isArray(template.params) ? template.params : [];

    params.forEach(param => {
        const rawValue = values[param.key] ?? param.default ?? "";
        const value = String(rawValue).trim() || param.default || "";
        if (!param.token) return;
        prompt = prompt.split(param.token).join(value);
    });

    return prompt;
}

function updatePromptStats() {
    const stats = document.getElementById("promptStats");
    if (!stats) return;

    const length = buildFinalTemplatePrompt().trim().length;
    stats.textContent = `最终 ${length} 字符`;
}

function getTemplateUserInstruction() {
    return document.getElementById("templateUserPromptEdit")?.value?.trim() || "";
}

function buildFinalTemplatePrompt() {
    const basePrompt = document.getElementById("templatePromptEditor")?.value?.trim() || "";
    const userInstruction = getTemplateUserInstruction();
    if (!userInstruction) return basePrompt;
    return [
        basePrompt,
        "",
        "User customization in Chinese, must follow:",
        userInstruction,
        "",
        "Keep the original template style, composition quality, and detail level unless the Chinese customization explicitly changes them."
    ].join("\n");
}

async function copyTemplatePrompt() {
    const prompt = buildFinalTemplatePrompt().trim();
    if (!prompt) {
        showToast("当前没有可复制的 Prompt", "error");
        return;
    }

    try {
        await navigator.clipboard.writeText(prompt);
        showToast("Prompt 已复制");
    } catch (error) {
        const editor = document.getElementById("templatePromptEditor");
        editor?.focus();
        editor?.select();
        showToast("浏览器未开放剪贴板权限，已选中 Prompt", "error");
    }
}

function resetTemplateParams() {
    if (!activeAwesomeTemplate) return;
    renderTemplateEditor(activeAwesomeTemplate, { shouldScroll: false, updateUrl: false });
    showToast("参数已重置");
}

function normalizeTemplateSizeRatio(value = "") {
    const candidate = String(value || "").trim();
    if (!candidate) return "";
    if (candidate === "auto") return "auto";
    if (candidate.includes(":")) return candidate;
    return TEMPLATE_SIZE_TO_RATIO[candidate] || "";
}

function resolveTemplateImageSize(aspectRatio, preferredSize) {
    const sizeSelect = document.getElementById("templateImageSize");
    const requestedAspectRatio = String(aspectRatio || "").trim() || "1:1";
    const requestedSize = String(preferredSize || "").trim();
    if (!sizeSelect) {
        return requestedSize === "auto" ? requestedAspectRatio : (requestedSize || requestedAspectRatio);
    }

    const values = [...sizeSelect.options].map(option => option.value);
    if (requestedSize === "auto") {
        return requestedAspectRatio === "auto" ? "auto" : requestedAspectRatio;
    }

    const requestedSizeRatio = normalizeTemplateSizeRatio(requestedSize);
    if (
        requestedAspectRatio
        && requestedAspectRatio !== "auto"
        && requestedSizeRatio
        && requestedSizeRatio !== "auto"
        && requestedSizeRatio !== requestedAspectRatio
        && values.includes(requestedAspectRatio)
    ) {
        return requestedAspectRatio;
    }

    if (requestedSize && values.includes(requestedSize)) {
        return requestedSize;
    }
    if (requestedAspectRatio && values.includes(requestedAspectRatio)) {
        return requestedAspectRatio;
    }
    return values[0] || requestedAspectRatio || "1:1";
}

function syncTemplateSizeSelection({ force = false } = {}) {
    const ratioSelect = document.getElementById("templateAspectRatio");
    const sizeSelect = document.getElementById("templateImageSize");
    if (!ratioSelect || !sizeSelect) return;

    const previousRatio = ratioSelect.dataset.previousValue || "";
    const currentSize = sizeSelect.value || "";
    const currentSizeRatio = normalizeTemplateSizeRatio(currentSize);
    const manualOverride = sizeSelect.dataset.manual === "1";
    const shouldSync = force
        || !manualOverride
        || !currentSize
        || currentSize === "auto"
        || currentSize === previousRatio
        || (previousRatio && currentSizeRatio === previousRatio);

    if (shouldSync) {
        sizeSelect.value = resolveTemplateImageSize(ratioSelect.value || "1:1", currentSize);
        sizeSelect.dataset.manual = "0";
        sizeSelect.dataset.syncedValue = sizeSelect.value || "";
    }

    ratioSelect.dataset.previousValue = ratioSelect.value || "";
}

function getTemplateGenerationSettings() {
    const aspectRatio = document.getElementById("templateAspectRatio")?.value || "1:1";
    const sizeSelect = document.getElementById("templateImageSize");
    const imageSize = sizeSelect?.value || aspectRatio || "1:1";
    const resolvedSize = sizeSelect?.dataset.manual === "1"
        ? (imageSize === "auto" ? aspectRatio : imageSize)
        : resolveTemplateImageSize(aspectRatio, imageSize);
    return {
        model: document.getElementById("templateModel")?.value || publicSettings.defaultModel || DEFAULT_IMAGE_MODEL,
        quality: document.getElementById("templateQuality")?.value || "medium",
        aspectRatio,
        size: resolvedSize,
        count: Number(document.getElementById("templateOutputCount")?.value || 1),
        outputFormat: document.getElementById("templateOutputFormat")?.value || "png",
        background: document.getElementById("templateBackground")?.value || "auto",
        moderation: document.getElementById("templateModeration")?.value || "auto",
        outputCompression: document.getElementById("templateOutputCompression")?.value || "",
        referenceMode: document.getElementById("templateReferenceMode")?.value || "optional"
    };
}

function populateGenerationControls() {
    const model = document.getElementById("templateModel");
    if (model && generationModels.length) {
        const current = model.value || publicSettings.defaultModel || DEFAULT_IMAGE_MODEL;
        model.innerHTML = generationModels
            .filter(item => item.enabled !== false && item.modality !== "video")
            .map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · ${Number(item.cost || 5)} 积分基础</option>`)
            .join("");
        if ([...model.options].some(option => option.value === current)) {
            model.value = current;
        }
    }

    populateQualityOptions();
    populateSizeOptionsForModel();
    updateOfficialImageOptions();
    updateTemplateCreditEstimate();
    populateCustomImageControls();
    updateCustomImageOfficialOptions();
    updateCustomImageCreditEstimate();
}

function setTemplateGenerationDefaults(template) {
    populateGenerationControls();
    const model = document.getElementById("templateModel");
    const quality = document.getElementById("templateQuality");
    const ratio = document.getElementById("templateAspectRatio");
    const size = document.getElementById("templateImageSize");
    const preferredModel = isOfficialGptImageRoute(template.modelRoute)
        ? publicSettings.defaultModel || DEFAULT_IMAGE_MODEL
        : template.modelRoute || publicSettings.defaultModel || DEFAULT_IMAGE_MODEL;
    if (model && preferredModel && [...model.options].some(option => option.value === preferredModel)) {
        model.value = preferredModel;
    }
    populateSizeOptionsForModel();
    if (quality && template.defaultQuality) quality.value = template.defaultQuality;
    if (ratio && template.defaultAspectRatio) ratio.value = template.defaultAspectRatio;
    if (size && template.defaultSize && [...size.options].some(option => option.value === template.defaultSize)) {
        size.value = template.defaultSize;
    }
    if (size) size.dataset.manual = "0";
    if (ratio) ratio.dataset.previousValue = ratio.value || "";
    syncTemplateSizeSelection({ force: true });
    updateOfficialImageOptions();
    updateTemplateCreditEstimate();
}

function getCreditRules() {
    return publicSettings.pricingRules || DEFAULT_CREDIT_RULES;
}

function getSelectedModel() {
    const selected = document.getElementById("templateModel")?.value;
    return generationModels.find(item => item.id === selected) || generationModels.find(item => item.id === publicSettings.defaultModel) || generationModels[0] || null;
}

function getCreditRule(group, value) {
    const rules = getCreditRules()[group] || DEFAULT_CREDIT_RULES[group] || {};
    return rules[value] || DEFAULT_CREDIT_RULES[group]?.[value] || { label: value, factor: 1 };
}

function populateQualityOptions() {
    const quality = document.getElementById("templateQuality");
    if (!quality) return;

    const current = quality.value || publicSettings.defaultQuality || "medium";
    const qualityRules = getCreditRules().quality || DEFAULT_CREDIT_RULES.quality;
    quality.innerHTML = Object.entries(qualityRules).map(([value, rule]) => {
        const factor = Number(rule.factor || 1);
        return `<option value="${escapeHtml(value)}">${escapeHtml(rule.label || value)} · x${factor.toFixed(2)}</option>`;
    }).join("");
    quality.value = [...quality.options].some(option => option.value === current) ? current : "medium";
}

function populateSizeOptionsForModel() {
    const size = document.getElementById("templateImageSize");
    if (!size) return;

    const current = size.value || document.getElementById("templateAspectRatio")?.value || "1:1";
    const selectedModel = getSelectedModel();
    const modelSizes = Array.isArray(selectedModel?.sizes) ? selectedModel.sizes : [];
    const sizeRules = getCreditRules().size || DEFAULT_CREDIT_RULES.size;
    const values = [...new Set([...modelSizes, ...Object.keys(sizeRules)])];

    size.innerHTML = values.map(value => {
        const rule = getCreditRule("size", value);
        const factor = Number(rule.factor || 1);
        return `<option value="${escapeHtml(value)}">${escapeHtml(rule.label || value.replace("x", " x "))} · x${factor.toFixed(2)}</option>`;
    }).join("");
    const fallback = document.getElementById("templateAspectRatio")?.value || selectedModel?.defaultSize || "1:1";
    size.value = values.includes(current) ? current : (values.includes(fallback) ? fallback : selectedModel?.defaultSize || "1:1");
    if (size.value !== current) {
        size.dataset.manual = "0";
    }
}

function isOfficialGptImageRoute(modelId = "") {
    return String(modelId || "").trim() === "gpt-image-2-official";
}

function toggleOptionDisabled(select, value, disabled) {
    const option = [...(select?.options || [])].find(item => item.value === value);
    if (option) option.disabled = disabled;
}

function updateOfficialImageOptions() {
    const settings = getTemplateGenerationSettings();
    const isOfficial = isOfficialGptImageRoute(settings.model);
    const outputFormat = document.getElementById("templateOutputFormat");
    const background = document.getElementById("templateBackground");
    const moderation = document.getElementById("templateModeration");
    const compression = document.getElementById("templateOutputCompression");
    const ratio = document.getElementById("templateAspectRatio");
    const hint = document.getElementById("templateOfficialOptionHint");

    if (ratio) {
        toggleOptionDisabled(ratio, "auto", !isOfficial);
        if (!isOfficial && ratio.value === "auto") ratio.value = "1:1";
    }

    if (outputFormat) outputFormat.disabled = !isOfficial;
    if (background) {
        background.disabled = !isOfficial;
        toggleOptionDisabled(background, "transparent", isOfficial);
        if (isOfficial && background.value === "transparent") {
            background.value = "auto";
        }
    }
    if (moderation) moderation.disabled = !isOfficial;
    if (compression) compression.disabled = !isOfficial;

    if (isOfficial && outputFormat?.value === "jpeg" && background?.value === "transparent") {
        background.value = "auto";
        showToast("JPEG 不能搭配透明背景，已自动切回自动背景", "error");
    }

    if (hint) {
        hint.textContent = isOfficial
            ? "当前为 APIMART official 路由：支持输出格式、背景、审核强度、压缩强度；transparent 与 JPEG 不兼容，且 official 路由不支持 transparent。"
            : "当前不是 official 路由：额外参数将保持默认，仅基础质量、比例、尺寸、数量会生效。";
    }
}

function getImageModels() {
    return generationModels.filter(item => item.enabled !== false && item.modality !== "video");
}

function getPreferredImageModelId() {
    const preferred = publicSettings.defaultModel || DEFAULT_IMAGE_MODEL;
    const models = getImageModels();
    if (models.some(item => item.id === preferred)) return preferred;
    if (models.some(item => item.id === DEFAULT_IMAGE_MODEL)) return DEFAULT_IMAGE_MODEL;
    return models[0]?.id || DEFAULT_IMAGE_MODEL;
}

function getSelectedCustomImageModel() {
    const selected = document.getElementById("customImageModel")?.value;
    const models = getImageModels();
    return models.find(item => item.id === selected)
        || models.find(item => item.id === getPreferredImageModelId())
        || models[0]
        || null;
}

function getCustomImageSettings() {
    const size = document.getElementById("customImageSize")?.value || "1024x1024";
    const referenceMode = document.getElementById("customImageReferenceMode")?.value || (customImageReferenceImages.length ? "optional" : "text-only");
    const settings = {
        model: document.getElementById("customImageModel")?.value || getPreferredImageModelId(),
        quality: document.getElementById("customImageQuality")?.value || publicSettings.defaultQuality || "medium",
        aspectRatio: size,
        size,
        count: Number(document.getElementById("customImageCount")?.value || 1),
        outputFormat: document.getElementById("customImageOutputFormat")?.value || "png",
        background: document.getElementById("customImageBackground")?.value || "auto",
        moderation: document.getElementById("customImageModeration")?.value || "auto",
        outputCompression: document.getElementById("customImageOutputCompression")?.value || "",
        referenceMode
    };
    if (!settings.outputCompression) delete settings.outputCompression;
    return settings;
}

function populateCustomImageControls() {
    const root = document.getElementById("image-workbench");
    if (!root) return;
    populateCustomImageModels();
    populateCustomImageQualityOptions();
    populateCustomImageSizeOptions();
}

function populateCustomImageModels() {
    const select = document.getElementById("customImageModel");
    if (!select) return;
    const models = getImageModels();
    const current = select.value || getPreferredImageModelId();
    if (!models.length) {
        select.innerHTML = `<option value="${escapeAttr(DEFAULT_IMAGE_MODEL)}">GPT-Image2 高清</option>`;
        select.value = DEFAULT_IMAGE_MODEL;
        return;
    }
    select.innerHTML = models.map(item => {
        const cost = Number(item.cost || 5);
        const serverHint = item.serverKeyStatus === "not_configured" ? " · 未配置 Key" : "";
        return `<option value="${escapeAttr(item.id)}">${escapeHtml(item.name)} · ${cost} 积分基础${escapeHtml(serverHint)}</option>`;
    }).join("");
    select.value = models.some(item => item.id === current) ? current : getPreferredImageModelId();
}

function populateCustomImageQualityOptions() {
    const select = document.getElementById("customImageQuality");
    if (!select) return;
    const current = select.value || publicSettings.defaultQuality || "medium";
    const qualityRules = getCreditRules().quality || DEFAULT_CREDIT_RULES.quality;
    select.innerHTML = Object.entries(qualityRules).map(([value, rule]) => {
        const labelMap = {
            auto: "Auto 自动",
            low: "低成本",
            medium: "标准",
            high: "高清"
        };
        const factor = Number(rule.factor || 1);
        return `<option value="${escapeAttr(value)}">${escapeHtml(labelMap[value] || rule.label || value)} · x${factor.toFixed(2)}</option>`;
    }).join("");
    select.value = [...select.options].some(option => option.value === current) ? current : "medium";
}

function populateCustomImageSizeOptions() {
    const select = document.getElementById("customImageSize");
    if (!select) return;
    const selectedModel = getSelectedCustomImageModel();
    const isOfficial = isOfficialGptImageRoute(selectedModel?.id);
    const current = select.value || selectedModel?.defaultSize || (isOfficial ? "1:1" : "1024x1024");
    const modelValues = Array.isArray(selectedModel?.sizes) ? selectedModel.sizes : [];
    const fallbackValues = isOfficial
        ? ["auto", "1:1", "3:4", "4:3", "4:5", "5:4", "2:3", "3:2", "16:9", "9:16", "2:1", "1:2", "21:9", "9:21"]
        : ["1024x1024", "1024x1536", "1536x1024", "1536x1536"];
    const values = [...new Set([...(modelValues.length ? modelValues : fallbackValues), ...fallbackValues])];
    select.innerHTML = values.map(value => {
        const rule = getCreditRule("size", value);
        const factor = Number(rule.factor || 1);
        const label = rule.label || value.replace("x", " x ");
        return `<option value="${escapeAttr(value)}">${escapeHtml(label)} · x${factor.toFixed(2)}</option>`;
    }).join("");
    select.value = values.includes(current) ? current : selectedModel?.defaultSize || values[0];
}

function updateCustomImageOfficialOptions() {
    const settings = getCustomImageSettings();
    const isOfficial = isOfficialGptImageRoute(settings.model);
    const outputFormat = document.getElementById("customImageOutputFormat");
    const background = document.getElementById("customImageBackground");
    const moderation = document.getElementById("customImageModeration");
    const compression = document.getElementById("customImageOutputCompression");
    const hint = document.getElementById("customImageOfficialHint");
    const meta = document.getElementById("customImageModelMeta");

    if (outputFormat) outputFormat.disabled = !isOfficial;
    if (background) {
        background.disabled = !isOfficial;
        toggleOptionDisabled(background, "transparent", isOfficial);
        if (isOfficial && background.value === "transparent") background.value = "auto";
    }
    if (moderation) moderation.disabled = !isOfficial;
    if (compression) compression.disabled = !isOfficial;

    if (hint) {
        hint.textContent = isOfficial
            ? "当前为 GPT Image 2 Official：支持 Auto 比例、输出格式、背景、审核强度和压缩强度；official 路由不支持透明背景。"
            : "当前为默认高清链路：主要使用模型、质量、尺寸、数量和参考图；高级输出参数会保持默认。";
    }
    if (meta) {
        meta.textContent = isOfficial ? "Official 参数已启用" : "默认高清链路";
    }
}

function calculateCustomImageCreditCost(settings = getCustomImageSettings()) {
    const selectedModel = getSelectedCustomImageModel();
    const baseCost = Number(selectedModel?.cost || 5);
    const qualityRule = getCreditRule("quality", settings.quality);
    const sizeRule = getCreditRule("size", settings.size);
    const count = Math.max(1, Math.min(4, Number(settings.count || 1)));
    const qualityFactor = Number(qualityRule.factor || 1);
    const sizeFactor = Number(sizeRule.factor || 1);
    const singleCost = Math.max(1, Math.ceil(baseCost * qualityFactor * sizeFactor));
    const total = singleCost * count;

    return {
        total,
        singleCost,
        baseCost,
        count,
        modelName: selectedModel?.name || settings.model,
        qualityLabel: qualityRule.label || settings.quality,
        qualityFactor,
        sizeLabel: sizeRule.label || settings.size,
        sizeFactor
    };
}

function updateCustomImageCreditEstimate() {
    const estimate = calculateCustomImageCreditCost();
    const estimateNode = document.getElementById("customImageCreditEstimate");
    const breakdownNode = document.getElementById("customImageCreditBreakdown");
    const button = document.getElementById("generateCustomImage");

    if (estimateNode) estimateNode.textContent = `${estimate.total} 积分`;
    if (breakdownNode) {
        breakdownNode.textContent = `${estimate.modelName} 基础 ${estimate.baseCost}，${estimate.qualityLabel} x${estimate.qualityFactor.toFixed(2)}，${estimate.sizeLabel} x${estimate.sizeFactor.toFixed(2)}，共 ${estimate.count} 张。`;
    }
    if (button && !button.disabled) {
        button.textContent = `生成 · ${estimate.total} 积分`;
    }
}

function calculateTemplateCreditCost(settings = getTemplateGenerationSettings()) {
    const selectedModel = getSelectedModel();
    const baseCost = Number(selectedModel?.cost || activeAwesomeTemplate?.creditCost || 5);
    const qualityRule = getCreditRule("quality", settings.quality);
    const sizeRule = getCreditRule("size", settings.size);
    const count = Math.max(1, Math.min(8, Number(settings.count || 1)));
    const qualityFactor = Number(qualityRule.factor || 1);
    const sizeFactor = Number(sizeRule.factor || 1);
    const singleCost = Math.max(1, Math.ceil(baseCost * qualityFactor * sizeFactor));
    const total = singleCost * count;

    return {
        total,
        singleCost,
        baseCost,
        count,
        modelName: selectedModel?.name || settings.model,
        qualityLabel: qualityRule.label || settings.quality,
        qualityFactor,
        sizeLabel: sizeRule.label || settings.size,
        sizeFactor
    };
}

function updateTemplateCreditEstimate() {
    const estimate = calculateTemplateCreditCost();
    const estimateNode = document.getElementById("templateCreditEstimate");
    const breakdownNode = document.getElementById("templateCreditBreakdown");
    const button = document.getElementById("generateFromTemplate");

    if (estimateNode) estimateNode.textContent = `${estimate.total} 积分`;
    if (breakdownNode) {
        breakdownNode.textContent = `${estimate.modelName} 基础 ${estimate.baseCost}，${estimate.qualityLabel} x${estimate.qualityFactor.toFixed(2)}，${estimate.sizeLabel} x${estimate.sizeFactor.toFixed(2)}，共 ${estimate.count} 张。`;
    }
    if (button && !button.disabled) {
        button.textContent = "生成";
    }
}

function initTemplateReferenceUpload() {
    const drop = document.getElementById("templateReferenceDrop");
    const input = document.getElementById("templateReferenceInput");
    const preview = document.getElementById("templateReferencePreview");

    const openPicker = () => input?.click();
    drop?.addEventListener("click", event => {
        if (event.target.closest("[data-reference-remove]")) return;
        openPicker();
    });
    drop?.addEventListener("keydown", event => {
        if (event.target.closest("[data-reference-remove]")) return;
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openPicker();
        }
    });
    input?.addEventListener("change", event => {
        handleTemplateReferenceFiles(event.target.files);
        input.value = "";
    });
    drop?.addEventListener("dragover", event => {
        event.preventDefault();
        drop.classList.add("dragover");
    });
    drop?.addEventListener("dragleave", () => {
        drop.classList.remove("dragover");
    });
    drop?.addEventListener("drop", event => {
        event.preventDefault();
        drop.classList.remove("dragover");
        handleTemplateReferenceFiles(event.dataTransfer.files);
    });
    preview?.addEventListener("click", event => {
        const removeButton = event.target.closest("[data-reference-remove]");
        if (!removeButton) return;
        removeTemplateReferenceImage(removeButton.dataset.referenceRemove);
    });
    renderTemplateReferenceImages();
}

function createReferenceId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `ref_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

async function handleTemplateReferenceFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    const remaining = TEMPLATE_REFERENCE_LIMIT - templateReferenceImages.length;
    if (remaining <= 0) {
        showToast("最多上传 10 张参考图", "error");
        return;
    }

    if (files.length > remaining) {
        showToast(`最多还能上传 ${remaining} 张参考图`, "error");
    }

    const acceptedFiles = files.slice(0, remaining);
    const loaded = [];
    for (const file of acceptedFiles) {
        try {
            loaded.push(await readTemplateReferenceImage(file));
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    if (!loaded.length) return;
    templateReferenceImages = [...templateReferenceImages, ...loaded].slice(0, TEMPLATE_REFERENCE_LIMIT);
    syncReferenceModeFromUploads();
    renderTemplateReferenceImages();
    showToast(`已上传 ${templateReferenceImages.length} 张参考图`);
}

function readTemplateReferenceImage(file) {
    return new Promise((resolve, reject) => {
        if (!isAllowedUploadImageType(file.type)) {
            reject(new Error("请上传 JPG、PNG 或 WebP 图片"));
            return;
        }
        if (file.size > TEMPLATE_REFERENCE_MAX_SIZE) {
            reject(new Error("单张图片不能超过 10MB"));
            return;
        }

        const reader = new FileReader();
        reader.onload = event => {
            resolve({
                id: createReferenceId(),
                name: file.name,
                type: file.type || "image/jpeg",
                size: file.size,
                dataUrl: event.target.result
            });
        };
        reader.onerror = () => reject(new Error("图片读取失败"));
        reader.readAsDataURL(file);
    });
}

function syncReferenceModeFromUploads() {
    const mode = document.getElementById("templateReferenceMode");
    if (mode && templateReferenceImages.length && mode.value === "text-only") {
        mode.value = "optional";
    }
}

function removeTemplateReferenceImage(id) {
    templateReferenceImages = templateReferenceImages.filter(image => image.id !== id);
    renderTemplateReferenceImages();
}

function renderTemplateReferenceImages() {
    const count = document.getElementById("templateReferenceCount");
    const drop = document.getElementById("templateReferenceDrop");
    const preview = document.getElementById("templateReferencePreview");
    if (count) count.textContent = `${templateReferenceImages.length} / ${TEMPLATE_REFERENCE_LIMIT}`;
    if (!preview) return;

    if (!templateReferenceImages.length) {
        drop?.classList.remove("has-images");
        preview.innerHTML = `<span class="template-reference-empty">最多 10 张，单张 10MB 内</span>`;
        return;
    }

    drop?.classList.add("has-images");
    preview.innerHTML = templateReferenceImages.map(image => `
        <article class="template-reference-thumb">
            <img src="${escapeAttr(safeMediaUrl(image.dataUrl))}" alt="${escapeHtml(image.name || "参考图")}">
            <button type="button" aria-label="移除 ${escapeHtml(image.name || "参考图")}" data-reference-remove="${escapeAttr(image.id)}">×</button>
        </article>
    `).join("");
}

function getTemplateReferencePayload(settings) {
    if (settings.referenceMode === "text-only") return [];
    return templateReferenceImages.map(image => ({
        name: image.name,
        mimeType: image.type,
        byteSize: image.size,
        dataUrl: image.dataUrl
    }));
}

function initCustomImageReferenceUpload() {
    const drop = document.getElementById("customImageReferenceDrop");
    const input = document.getElementById("customImageReferenceInput");
    const preview = document.getElementById("customImageReferencePreview");
    const openPicker = () => input?.click();

    drop?.addEventListener("click", event => {
        if (event.target.closest("[data-custom-reference-remove]")) return;
        openPicker();
    });
    drop?.addEventListener("keydown", event => {
        if (event.target.closest("[data-custom-reference-remove]")) return;
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openPicker();
        }
    });
    input?.addEventListener("change", event => {
        handleCustomImageReferenceFiles(event.target.files);
        input.value = "";
    });
    drop?.addEventListener("dragover", event => {
        event.preventDefault();
        drop.classList.add("dragover");
    });
    drop?.addEventListener("dragleave", () => drop.classList.remove("dragover"));
    drop?.addEventListener("drop", event => {
        event.preventDefault();
        drop.classList.remove("dragover");
        handleCustomImageReferenceFiles(event.dataTransfer.files);
    });
    preview?.addEventListener("click", event => {
        const removeButton = event.target.closest("[data-custom-reference-remove]");
        if (!removeButton) return;
        customImageReferenceImages = customImageReferenceImages.filter(image => image.id !== removeButton.dataset.customReferenceRemove);
        renderCustomImageReferenceImages();
        updateCustomImageReferenceModeFromUploads();
    });
    renderCustomImageReferenceImages();
}

async function handleCustomImageReferenceFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;

    const remaining = TEMPLATE_REFERENCE_LIMIT - customImageReferenceImages.length;
    if (remaining <= 0) {
        showToast("最多上传 10 张参考图", "error");
        return;
    }
    if (files.length > remaining) {
        showToast(`最多还能上传 ${remaining} 张参考图`, "error");
    }

    const loaded = [];
    for (const file of files.slice(0, remaining)) {
        try {
            loaded.push(await readTemplateReferenceImage(file));
        } catch (error) {
            showToast(error.message, "error");
        }
    }
    if (!loaded.length) return;

    customImageReferenceImages = [...customImageReferenceImages, ...loaded].slice(0, TEMPLATE_REFERENCE_LIMIT);
    renderCustomImageReferenceImages();
    updateCustomImageReferenceModeFromUploads();
    showToast(`已上传 ${customImageReferenceImages.length} 张参考图`);
}

function updateCustomImageReferenceModeFromUploads() {
    const mode = document.getElementById("customImageReferenceMode");
    if (!mode) return;
    if (customImageReferenceImages.length && mode.value === "text-only") {
        mode.value = "optional";
    }
    if (!customImageReferenceImages.length && mode.value === "optional") {
        mode.value = "text-only";
    }
}

function renderCustomImageReferenceImages() {
    const count = document.getElementById("customImageReferenceCount");
    const drop = document.getElementById("customImageReferenceDrop");
    const preview = document.getElementById("customImageReferencePreview");
    if (count) count.textContent = `${customImageReferenceImages.length} / ${TEMPLATE_REFERENCE_LIMIT}`;
    if (!preview) return;

    if (!customImageReferenceImages.length) {
        drop?.classList.remove("has-images");
        preview.innerHTML = `<span class="template-reference-empty">可选上传参考图，最多 10 张，单张 10MB 内</span>`;
        return;
    }

    drop?.classList.add("has-images");
    preview.innerHTML = customImageReferenceImages.map(image => `
        <article class="template-reference-thumb">
            <img src="${escapeAttr(safeMediaUrl(image.dataUrl))}" alt="${escapeHtml(image.name || "参考图")}">
            <button type="button" aria-label="移除 ${escapeHtml(image.name || "参考图")}" data-custom-reference-remove="${escapeAttr(image.id)}">×</button>
        </article>
    `).join("");
}

function getCustomImageReferencePayload(settings) {
    if (settings.referenceMode === "text-only") return [];
    return customImageReferenceImages.map(image => ({
        name: image.name,
        mimeType: image.type,
        byteSize: image.size,
        dataUrl: image.dataUrl
    }));
}

function getCustomImageTemplateTitle(prompt = "") {
    const compact = String(prompt || "").replace(/\s+/g, " ").trim();
    return compact ? compact.slice(0, 24) : "自定义图片模板";
}

function setCustomImageResultState(state, data = {}) {
    const preview = document.getElementById("customImageResultPreview");
    const download = document.getElementById("downloadCustomImageResult");
    const open = document.getElementById("openCustomImageResult");
    if (!preview) return;

    preview.classList.remove("is-empty", "generating", "result-error", "has-result");
    if (state !== "success") {
        customImageActiveResultUrl = "";
        preview.style.removeProperty("--cover");
        renderCustomImageResultGallery([]);
        if (download) download.disabled = true;
        if (open) open.disabled = true;
    }

    if (state === "loading") {
        preview.classList.add("is-empty", "generating");
        setText("customImageResultPlaceholder", data.label || "正在生成，请耐心等候");
        setText("customImageResultTitle", "正在生成");
        setText("customImageResultMeta", data.meta || "任务处理中");
        setText("customImageResultSummary", data.summary || "任务已提交，正在等待上游返回结果。");
        return;
    }

    if (state === "error") {
        preview.classList.add("is-empty", "result-error");
        setText("customImageResultPlaceholder", "生成失败，请重试");
        setText("customImageResultTitle", "生成失败");
        setText("customImageResultMeta", "未产生结果");
        setText("customImageResultSummary", data.summary || "图片生成失败，本次不应实际消耗积分；如已预扣或误扣会自动退回。");
        return;
    }

    if (state === "success") {
        const urls = (Array.isArray(data.urls) ? data.urls : [data.url]).filter(Boolean);
        setCustomImageResultImages(urls);
        return;
    }

    preview.classList.add("is-empty");
    setText("customImageResultPlaceholder", "等待生成结果");
    setText("customImageResultTitle", "输出结果");
    setText("customImageResultMeta", "等待生成");
    setText("customImageResultSummary", "左侧填写提示词后提交生成；生成完成后可下载或在新窗口打开。");
}

function setCustomImageResultImages(urls) {
    const preview = document.getElementById("customImageResultPreview");
    const download = document.getElementById("downloadCustomImageResult");
    const open = document.getElementById("openCustomImageResult");
    const cleanUrls = [...new Set((urls || []).filter(Boolean).map(url => assetUrl(url)))];
    if (!preview || !cleanUrls.length) return;

    customImageResultUrls = cleanUrls;
    customImageActiveResultUrl = cleanUrls[0];
    preview.classList.remove("is-empty", "generating", "result-error");
    preview.classList.add("has-result");
    const activeCover = cssUrl(customImageActiveResultUrl);
    if (activeCover) preview.style.setProperty("--cover", activeCover);
    setText("customImageResultPlaceholder", "");
    setText("customImageResultTitle", "生成完成");
    setText("customImageResultMeta", `${cleanUrls.length} 张结果`);
    setText("customImageResultSummary", "图片已生成，可以下载当前选中图片，或在新窗口打开保存原图。");
    if (download) download.disabled = false;
    if (open) open.disabled = false;
    renderCustomImageResultGallery(cleanUrls);
}

function renderCustomImageResultGallery(urls = customImageResultUrls) {
    const gallery = document.getElementById("customImageResultGallery");
    if (!gallery) return;
    if (!urls.length || urls.length <= 1) {
        gallery.hidden = true;
        gallery.innerHTML = "";
        return;
    }
    gallery.hidden = false;
    gallery.innerHTML = urls.map((url, index) => `
        <button class="${url === customImageActiveResultUrl ? "active" : ""}" type="button" data-custom-result-url="${escapeAttr(url)}" aria-label="查看第 ${index + 1} 张结果">
            <img src="${escapeAttr(url)}" alt="生成结果 ${index + 1}">
        </button>
    `).join("");
}

function selectCustomImageResult(url) {
    if (!url) return;
    customImageActiveResultUrl = assetUrl(url);
    const preview = document.getElementById("customImageResultPreview");
    if (preview) {
        const activeCover = cssUrl(customImageActiveResultUrl);
        if (activeCover) preview.style.setProperty("--cover", activeCover);
    }
    renderCustomImageResultGallery(customImageResultUrls);
}

function normalizeGeneratedImageUrls(data = {}) {
    const urls = [];
    if (Array.isArray(data.imageUrls)) urls.push(...data.imageUrls);
    if (data.imageUrl) urls.unshift(data.imageUrl);
    if (Array.isArray(data.urls)) urls.push(...data.urls);
    return [...new Set(urls.filter(Boolean))];
}

async function requestCustomImageGeneration(event) {
    event?.preventDefault();
    const prompt = document.getElementById("customImagePrompt")?.value?.trim() || "";
    if (!prompt) {
        showToast("请先填写提示词", "error");
        return;
    }

    const settings = getCustomImageSettings();
    const referenceImages = getCustomImageReferencePayload(settings);
    if (settings.referenceMode === "required" && !referenceImages.length) {
        showToast("当前设置为必须参考图，请先上传图片", "error");
        setCustomImageResultState("error", { summary: "参考图策略设置为必须上传，请先上传参考图后再生成。" });
        return;
    }

    const estimate = calculateCustomImageCreditCost(settings);
    const button = document.getElementById("generateCustomImage");
    if (button) {
        button.disabled = true;
        button.textContent = "提交中";
    }
    if (customImagePollTimer) clearTimeout(customImagePollTimer);
    customImageResultUrls = [];
    setCustomImageResultState("loading", {
        summary: `正在提交图片任务，本次预计消耗 ${estimate.total} 积分，参考图 ${referenceImages.length} 张。`
    });

    try {
        const data = await apiPost(GENERATION_API_ENDPOINT, {
            templateId: null,
            templateTitle: "自定义图片生成",
            prompt,
            params: { source: "custom-image-workbench" },
            settings,
            referenceImages
        });
        const urls = normalizeGeneratedImageUrls(data);
        if (urls.length) {
            setCustomImageResultState("success", { urls });
            showToast("图片生成完成");
            return;
        }
        if (!data?.jobId) {
            throw new Error(data?.message || "图片任务提交后没有返回任务编号");
        }
        setCustomImageResultState("loading", {
            meta: data.jobNo || "队列中",
            summary: data.message || `任务 ${data.jobNo || data.jobId} 已进入生成队列，正在等待结果。`
        });
        showToast("生成任务已提交");
        pollCustomImageJob(data.jobId);
    } catch (error) {
        setCustomImageResultState("error", {
            summary: error.message || "图片服务暂时不可用，本次不会扣除积分。"
        });
        showToast(error.message || "无法提交图片生成", "error");
    } finally {
        if (button) {
            button.disabled = false;
            updateCustomImageCreditEstimate();
        }
    }
}

async function pollCustomImageJob(jobId, attempt = 0) {
    if (!jobId) return;
    if (attempt > 120) {
        setCustomImageResultState("error", {
            summary: "这条任务超过预期仍未返回结果，系统可能已卡住。你可以去个人中心刷新记录，或重新生成一版。"
        });
        return;
    }

    try {
        await sleep(attempt === 0 ? 1800 : 0);
        const data = await apiGet(`/api/jobs/${encodeURIComponent(jobId)}`);
        const job = data.item || {};
        const urls = normalizeGeneratedImageUrls(job);
        if (job.status === "success" && urls.length) {
            setCustomImageResultState("success", { urls });
            showToast("图片生成完成");
            return;
        }
        if (["failed", "cancelled"].includes(job.status)) {
            setCustomImageResultState("error", {
                summary: job.error || "图片生成失败，本次不应实际消耗积分；如已预扣或误扣会自动退回。"
            });
            return;
        }
        setCustomImageResultState("loading", {
            label: "正在生成，请耐心等候",
            meta: job.jobNo || "处理中",
            summary: job.message || `任务 ${job.jobNo || jobId} 处理中${job.progress ? `，进度 ${job.progress}%` : ""}。`
        });
        customImagePollTimer = setTimeout(() => pollCustomImageJob(jobId, attempt + 1), 5000);
    } catch (error) {
        setText("customImageResultSummary", error.message || "暂时无法刷新任务状态，稍后会继续尝试。");
        customImagePollTimer = setTimeout(() => pollCustomImageJob(jobId, attempt + 1), 7000);
    }
}

function getCustomImageResultFileName(url = "", mime = "") {
    const extension = getResultFileExtension(url, mime);
    const prompt = document.getElementById("customImagePrompt")?.value?.trim() || "自定义图片";
    const safeTitle = prompt.slice(0, 24).replace(/[\\/:*?"<>|]+/g, "-").replace(/\s+/g, " ").trim() || "自定义图片";
    return `${safeTitle}.${extension}`;
}

function openCustomImageResult() {
    if (!customImageActiveResultUrl) {
        showToast("生成完成后才能打开结果", "error");
        return;
    }
    openUrlInNewTab(customImageActiveResultUrl);
    showToast("图片已在新窗口打开");
}

async function downloadCustomImageResult() {
    if (!customImageActiveResultUrl) {
        showToast("生成完成后可下载", "error");
        return;
    }
    if (!canFetchResultForDownload(customImageActiveResultUrl)) {
        openCustomImageResult();
        return;
    }

    const button = document.getElementById("downloadCustomImageResult");
    const originalText = button?.textContent || "下载结果";
    if (button) {
        button.disabled = true;
        button.textContent = "准备下载";
    }
    try {
        const response = await fetch(customImageActiveResultUrl, { credentials: "include", cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        triggerBrowserDownload(blobUrl, getCustomImageResultFileName(customImageActiveResultUrl, blob.type));
        setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);
        showToast("已开始下载结果图");
    } catch (error) {
        openCustomImageResult();
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

async function saveCustomImageTemplate() {
    const prompt = document.getElementById("customImagePrompt")?.value?.trim() || "";
    if (!prompt) {
        showToast("请先填写提示词，再保存模板", "error");
        return;
    }

    const settings = getCustomImageSettings();
    const estimate = calculateCustomImageCreditCost(settings);
    const button = document.getElementById("saveCustomImageTemplate");
    const originalText = button?.textContent || "保存模板";
    if (button) {
        button.disabled = true;
        button.textContent = "保存中";
    }

    try {
        const data = await apiPost("/api/account/custom-templates", {
            title: getCustomImageTemplateTitle(prompt),
            description: "从自定义图片生成入口保存，可在模板库继续复用。",
            prompt,
            settings,
            coverUrl: customImageActiveResultUrl || "",
            creditCost: estimate.baseCost
        });
        showToast(data.message || "模板已保存");
        if (data.item?.id) {
            setText("customImageResultSummary", `模板已保存为「${getLocalized(data.item.title) || data.item.title}」，当前 ${data.count || ""} / ${data.limit || 10} 个。`);
        }
    } catch (error) {
        showToast(error.message || "保存模板失败", "error");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

function resetCustomImageWorkbench() {
    const prompt = document.getElementById("customImagePrompt");
    const count = document.getElementById("customImageCount");
    const mode = document.getElementById("customImageReferenceMode");
    const compression = document.getElementById("customImageOutputCompression");
    if (prompt) prompt.value = "";
    if (count) count.value = "1";
    if (mode) mode.value = "optional";
    if (compression) compression.value = "";
    customImageReferenceImages = [];
    customImageResultUrls = [];
    if (customImagePollTimer) clearTimeout(customImagePollTimer);
    renderCustomImageReferenceImages();
    setCustomImageResultState("idle");
    updateCustomImageCreditEstimate();
}

function resetTemplateResultPreview() {
    templateResultDownloadUrl = "";
    const image = document.getElementById("editorResultImage");
    const download = document.getElementById("downloadTemplateResult");
    if (image) {
        image.classList.add("is-empty");
        image.classList.remove("has-result", "generating", "result-error");
        image.style.removeProperty("--cover");
    }
    setText("editorResultPlaceholder", "等待生成结果");
    if (download) {
        download.disabled = true;
        download.textContent = "生成后下载";
    }
}

function setTemplateResultGenerating(isGenerating, label = "正在生成，请耐心等候") {
    const image = document.getElementById("editorResultImage");
    if (!image) return;
    image.classList.toggle("generating", Boolean(isGenerating));
    if (isGenerating) {
        image.classList.remove("result-error");
        image.classList.add("is-empty");
        image.classList.remove("has-result");
        image.style.removeProperty("--cover");
        setText("editorResultPlaceholder", label);
    } else if (!image.classList.contains("has-result") && !image.classList.contains("result-error")) {
        setText("editorResultPlaceholder", "等待生成结果");
    }
}

function setTemplateResultError() {
    const image = document.getElementById("editorResultImage");
    if (!image) return;
    image.classList.add("is-empty", "result-error");
    image.classList.remove("has-result", "generating");
    image.style.removeProperty("--cover");
    setText("editorResultPlaceholder", "生成失败，请重试");
}

function setTemplateResultImage(url) {
    const image = document.getElementById("editorResultImage");
    const download = document.getElementById("downloadTemplateResult");
    if (!image || !url) return;

    templateResultDownloadUrl = assetUrl(url);
    image.classList.remove("is-empty", "generating", "result-error");
    image.classList.add("has-result");
    setCover("editorResultImage", templateResultDownloadUrl);
    if (download) {
        download.disabled = false;
        download.textContent = "下载结果";
    }
    setText("editorResultMeta", "结果已生成，可以下载高清图。");
}

function getResultFileExtension(url = "", mime = "") {
    const mimeMap = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif"
    };
    if (mimeMap[mime]) return mimeMap[mime];
    const cleanUrl = String(url || "").split("?")[0].split("#")[0];
    const match = cleanUrl.match(/\.([a-z0-9]{2,5})$/i);
    return match ? match[1].toLowerCase() : "png";
}

function getResultFileName(url = "", mime = "") {
    const title = getLocalized(activeAwesomeTemplate?.title) || "生成结果";
    const safeTitle = String(title).replace(/[\\/:*?"<>|]+/g, "-").replace(/\s+/g, " ").trim() || "生成结果";
    return `${safeTitle}.${getResultFileExtension(url, mime)}`;
}

function triggerBrowserDownload(url, filename) {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    link.remove();
}

function openUrlInNewTab(url) {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    document.body.appendChild(link);
    link.click();
    link.remove();
}

function canFetchResultForDownload(url) {
    if (/^(data|blob):/i.test(String(url || ""))) return true;
    try {
        const parsed = new URL(url, window.location.href);
        return parsed.origin === window.location.origin;
    } catch (error) {
        return false;
    }
}

function openTemplateResultInNewPage() {
    openUrlInNewTab(templateResultDownloadUrl);
    showToast("图片已在新窗口打开，可在新页面中保存原图");
}

async function downloadTemplateResult() {
    if (!templateResultDownloadUrl) {
        showToast("生成完成后可下载", "error");
        return;
    }

    if (!canFetchResultForDownload(templateResultDownloadUrl)) {
        openTemplateResultInNewPage();
        return;
    }

    const button = document.getElementById("downloadTemplateResult");
    const originalText = button?.textContent || "下载结果";
    if (button) {
        button.disabled = true;
        button.textContent = "准备下载...";
    }

    try {
        const response = await fetch(templateResultDownloadUrl, { credentials: "include", cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        triggerBrowserDownload(blobUrl, getResultFileName(templateResultDownloadUrl, blob.type));
        setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);
        showToast("已开始下载结果图");
    } catch (error) {
        openTemplateResultInNewPage();
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

async function requestTemplateGeneration() {
    const prompt = buildFinalTemplatePrompt().trim();
    if (!prompt) {
        showToast("请先选择模板或填写 Prompt", "error");
        return;
    }

    const button = document.getElementById("generateFromTemplate");
    const resultSummary = document.getElementById("editorResultSummary");
    const settings = getTemplateGenerationSettings();
    const estimate = calculateTemplateCreditCost(settings);
    const referenceImages = getTemplateReferencePayload(settings);
    if (settings.referenceMode === "required" && !referenceImages.length) {
        showToast("请先上传参考图", "error");
        setText("editorResultSummary", "当前模板要求参考图，请先上传图片后再生成。");
        return;
    }

    const payload = {
        templateId: activeAwesomeTemplate?.id,
        templateTitle: getLocalized(activeAwesomeTemplate?.title),
        prompt,
        params: { ...activeTemplateValues, userInstruction: getTemplateUserInstruction() },
        settings,
        referenceImages
    };

    if (button) {
        button.disabled = true;
        button.textContent = "生成中";
    }
    let keepWaitingForResult = false;
    setTemplateResultGenerating(true);
    setText("editorResultTitle", "正在生成");

    setText("editorResultSummary", `正在生成，本次预计消耗 ${estimate.total} 积分，参考图 ${referenceImages.length} 张。`);

    try {
        const data = await apiPost(GENERATION_API_ENDPOINT, payload);
        if (data?.imageUrl) {
            setTemplateResultImage(data.imageUrl);
            setText("editorResultTitle", "生成完成");
        } else {
            keepWaitingForResult = true;
            setTemplateResultGenerating(true);
            setText("editorResultTitle", "生成任务处理中");
            setText("editorResultMeta", `${data?.jobNo ? `任务编号 ${data.jobNo}，` : ""}请耐心等候，生成完成后可下载高清图。`);
        }
        const creditCost = data?.creditCost || estimate.total;
        setText("editorResultSummary", data?.message || `任务 ${data?.jobNo || data?.jobId || ""} 已进入生成队列，预计消耗 ${creditCost} 积分；生成失败不应实际消耗积分，如已预扣或误扣会自动退回。`);
        showToast("生成任务已提交");
        if (keepWaitingForResult && data?.jobId) {
            if (imagePollTimer) clearTimeout(imagePollTimer);
            pollImageJob(data.jobId);
        }
    } catch (error) {
        setTemplateResultError();
        setText("editorResultTitle", "生成失败");
        setText("editorResultSummary", error.message || "生成服务暂不可用，请稍后重试。");
        showToast(error.message || "无法提交生成", "error");
    } finally {
        if (!keepWaitingForResult) {
            setTemplateResultGenerating(false);
        }
        if (button) {
            button.disabled = false;
            updateTemplateCreditEstimate();
        }
    }
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value || "";
}

function setCover(id, url) {
    const element = document.getElementById(id);
    if (element && url) {
        const safeUrl = cssUrl(url);
        if (safeUrl) element.style.setProperty("--cover", safeUrl);
    }
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function escapeAttr(value) {
    return escapeHtml(value).replace(/'/g, "&#39;").replace(/`/g, "&#96;");
}

function initUpload() {
    const uploadArea = document.getElementById("image-upload");
    const fileInput = document.getElementById("image-input");

    uploadArea?.addEventListener("click", event => {
        const removeButton = event.target.closest("[data-remove-image]");
        if (removeButton) {
            event.preventDefault();
            event.stopPropagation();
            removeImage();
            return;
        }
        fileInput?.click();
    });

    fileInput?.addEventListener("change", event => {
        const file = event.target.files?.[0];
        if (file) handleImageUpload(file);
    });

    uploadArea?.addEventListener("dragover", event => {
        event.preventDefault();
        uploadArea.classList.add("dragover");
    });

    uploadArea?.addEventListener("dragleave", () => {
        uploadArea.classList.remove("dragover");
    });

    uploadArea?.addEventListener("drop", event => {
        event.preventDefault();
        uploadArea.classList.remove("dragover");
        const file = event.dataTransfer.files?.[0];
        if (file) handleImageUpload(file);
    });
}

function handleImageUpload(file) {
    if (!isAllowedUploadImageType(file.type)) {
        showToast("请上传 JPG、PNG 或 WebP 图片", "error");
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showToast("图片大小不能超过 10MB", "error");
        return;
    }

    const reader = new FileReader();
    reader.onload = event => {
        uploadedImage = event.target.result;
        const uploadArea = document.getElementById("image-upload");
        uploadArea.innerHTML = `
            <div class="uploaded-preview">
                <img src="${uploadedImage}" alt="已上传的参考图">
                <button type="button" class="btn btn-secondary" data-remove-image>重新上传</button>
            </div>
        `;

        document.querySelectorAll(".quality-check span")[0].textContent = "清晰度：良好";
        document.querySelectorAll(".quality-check span")[1].textContent = "主体：单只宠物";
        document.querySelectorAll(".quality-check span")[2].textContent = "遮挡：轻微";
        updatePreview();
        showToast("照片已上传，可以继续填写模板字段");
    };
    reader.readAsDataURL(file);
}

function removeImage() {
    uploadedImage = null;
    const uploadArea = document.getElementById("image-upload");
    uploadArea.innerHTML = `
        <div class="upload-placeholder">
            <span class="icon-upload" aria-hidden="true"></span>
            <strong>拖拽或点击上传</strong>
            <p>建议上传正脸或半身清晰照片，避免多只宠物同框。</p>
        </div>
    `;
    document.getElementById("image-input").value = "";
    document.querySelectorAll(".quality-check span")[0].textContent = "清晰度：待检测";
    document.querySelectorAll(".quality-check span")[1].textContent = "主体：待检测";
    document.querySelectorAll(".quality-check span")[2].textContent = "遮挡：待检测";
}

function initTemplateForm() {
    document.querySelectorAll(".swatch").forEach(button => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".swatch").forEach(item => item.classList.remove("active"));
            button.classList.add("active");
            updatePreview();
        });
    });

    document.querySelectorAll(".quantity").forEach(button => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".quantity").forEach(item => item.classList.remove("active"));
            button.classList.add("active");
            generationCount = Number(button.dataset.count || 1);
        });
    });

    ["petName", "petType", "petMood", "appearance", "bgDensity", "styleStrength", "popPart", "popStyle", "namePosition", "nameStyle", "decorations"].forEach(id => {
        document.getElementById(id)?.addEventListener("input", updatePreview);
        document.getElementById(id)?.addEventListener("change", updatePreview);
    });

    document.getElementById("generateBtn")?.addEventListener("click", simulateGeneration);
    document.getElementById("regenerateBtn")?.addEventListener("click", simulateGeneration);
    document.getElementById("downloadBtn")?.addEventListener("click", () => showToast("当前为静态原型，接入后端后会下载原图"));
    document.getElementById("clearPreview")?.addEventListener("click", removeImage);
}

function updatePreview() {
    const name = document.getElementById("petName")?.value?.trim();
    const previewName = document.getElementById("previewName");
    if (previewName) {
        previewName.textContent = name || "Nuo Mi";
    }
}

async function simulateGeneration() {
    const name = document.getElementById("petName")?.value?.trim();
    const type = document.getElementById("petType")?.value || "宠物";
    const mood = document.getElementById("petMood")?.value || "乖巧";
    const popPart = document.getElementById("popPart")?.value || "前爪";
    const color = document.querySelector(".swatch.active")?.dataset.color || "奶油黄";
    const resultArea = document.getElementById("resultArea");
    const generateBtn = document.getElementById("generateBtn");

    if (!uploadedImage) {
        showToast("建议先上传宠物照片，模板会更稳定", "error");
    }

    generateBtn.disabled = true;
    generateBtn.textContent = "生成中";
    let keepWaitingForResult = false;
    resultArea.innerHTML = `
        <div class="generation-state">
            <div class="progress-track"><span id="progressBar" style="width:35%"></span></div>
            <strong>正在进入生成队列</strong>
            <p>${mood}表情，${color}背景，${popPart}自然出框。</p>
        </div>
    `;

    const prompt = `生成一张${type}拍立得风格图片，名字是${name || "Nuo Mi"}，表情${mood}，背景${color}，${popPart}自然出框。`;
    try {
        const data = await apiPost("/api/generate-image", {
            templateId: activeAwesomeTemplate?.id || null,
            templateTitle: "宠物拍立得",
            prompt,
            params: { name, type, mood, color, popPart },
            settings: {
                model: publicSettings.defaultModel || DEFAULT_IMAGE_MODEL,
                quality: publicSettings.defaultQuality || "medium",
                aspectRatio: "4:5",
                size: "4:5",
                count: generationCount,
                referenceMode: uploadedImage ? "optional" : "text-only"
            }
        });
        resultArea.innerHTML = `
            <div class="generation-state">
                <strong>${escapeHtml(data.jobNo || data.jobId || "任务已提交")}</strong>
                <p>${escapeHtml(data.message || "生成任务已进入队列，请在任务列表查看状态。")}</p>
            </div>
        `;
        showToast("生成任务已提交");
        if (data.jobId) {
            keepWaitingForResult = true;
            pollQuickGenerationJob(data.jobId, resultArea, generateBtn);
        }
    } catch (error) {
        resultArea.innerHTML = `
            <div class="generation-state">
                <strong>生成服务暂不可用</strong>
                <p>请稍后重试或联系管理员。</p>
            </div>
        `;
        showToast("无法提交生成", "error");
    } finally {
        if (!keepWaitingForResult) {
            generateBtn.disabled = false;
            generateBtn.textContent = "立即生成";
        }
    }
}

async function pollQuickGenerationJob(jobId, resultArea, generateBtn, attempt = 0) {
    if (!jobId || attempt > 120) {
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.textContent = "立即生成";
        }
        return;
    }
    try {
        await sleep(attempt === 0 ? 1800 : 0);
        const data = await apiGet(`/api/jobs/${encodeURIComponent(jobId)}`);
        const job = data.item || {};
        const imageUrl = job.imageUrl || (Array.isArray(job.imageUrls) && job.imageUrls.length ? job.imageUrls[0] : "");
        if (job.status === "success" && imageUrl) {
            resultArea.innerHTML = `
                <div class="generation-state">
                    <strong>生成完成</strong>
                    <p>图片已生成，可以继续去模板编辑器查看高清结果。</p>
                    <div class="result-preview-inline" style="margin-top:14px;">
                        <img src="${escapeAttr(assetUrl(imageUrl))}" alt="生成结果" style="width:100%;border-radius:18px;object-fit:cover;">
                    </div>
                </div>
            `;
            showToast("图片生成完成");
            if (generateBtn) {
                generateBtn.disabled = false;
                generateBtn.textContent = "立即生成";
            }
            return;
        }
        if (["failed", "cancelled"].includes(job.status)) {
            resultArea.innerHTML = `
                <div class="generation-state">
                    <strong>生成失败</strong>
                    <p>${escapeHtml(job.error || "图片生成失败，本次不应实际消耗积分；如已预扣或误扣会自动退回。")}</p>
                </div>
            `;
            if (generateBtn) {
                generateBtn.disabled = false;
                generateBtn.textContent = "立即生成";
            }
            return;
        }
        resultArea.innerHTML = `
            <div class="generation-state">
                <div class="progress-track"><span id="progressBar" style="width:${Math.min(92, 35 + attempt * 4)}%"></span></div>
                <strong>正在生成</strong>
                <p>${escapeHtml(job.message || `任务 ${job.jobNo || jobId} 处理中，请耐心等候。`)}</p>
            </div>
        `;
        setTimeout(() => pollQuickGenerationJob(jobId, resultArea, generateBtn, attempt + 1), 5000);
    } catch (error) {
        resultArea.innerHTML = `
            <div class="generation-state">
                <strong>等待结果中</strong>
                <p>${escapeHtml(error.message || "暂时无法刷新任务状态，稍后继续尝试。")}</p>
            </div>
        `;
        setTimeout(() => pollQuickGenerationJob(jobId, resultArea, generateBtn, attempt + 1), 7000);
    }
}

async function initVideoWorkbench() {
    const root = document.getElementById("video-workbench");
    if (!root) return;

    bindVideoControls();
    renderVideoReferences();
    setVideoResultState("idle");

    try {
        await ensureTemplateData();
        populateVideoModels();
        await loadVideoTemplates();
        const initialVideoTemplateId = getVideoTemplateIdFromLocation();
        if (initialVideoTemplateId) {
            await openVideoTemplate(initialVideoTemplateId, false);
        }
        updateVideoCreditEstimate();
    } catch (error) {
        setText("videoResultSummary", "后端 API 未连接，暂时无法读取视频模型和模板。");
    }
}

function bindVideoControls() {
    document.querySelectorAll("[data-video-mode]").forEach(button => {
        button.addEventListener("click", () => {
            activeVideoMode = button.dataset.videoMode || "image";
            updateVideoModeTabs();
            updateVideoModeState();
            ensureVideoModeCompatibleModel(true);
            updateVideoCreditEstimate();
        });
    });

    ["videoModel", "videoResolution", "videoAspectRatio", "videoDuration", "videoMotion"].forEach(id => {
        document.getElementById(id)?.addEventListener("change", () => {
            if (id === "videoModel") {
                populateVideoOptionsForModel();
                ensureVideoModeCompatibleModel(true);
            }
            updateVideoCreditEstimate();
        });
    });
    document.getElementById("videoPrompt")?.addEventListener("input", () => {
        activeVideoTemplate = null;
    });
    document.getElementById("generateVideo")?.addEventListener("click", requestVideoGeneration);
    document.getElementById("downloadVideoResult")?.addEventListener("click", event => {
        if (event.currentTarget.classList.contains("disabled")) event.preventDefault();
    });
    initVideoReferenceUpload();
}

function updateVideoModeTabs() {
    document.querySelectorAll("[data-video-mode]").forEach(item => {
        const selected = item.dataset.videoMode === activeVideoMode;
        item.classList.toggle("active", selected);
        item.setAttribute("aria-selected", selected ? "true" : "false");
    });
    const panel = document.getElementById("videoModePanel");
    const activeTab = Array.from(document.querySelectorAll("[data-video-mode]")).find(item => item.dataset.videoMode === activeVideoMode);
    if (panel && activeTab?.id) panel.setAttribute("aria-labelledby", activeTab.id);
}

function getVideoModels() {
    return generationModels.filter(item => item.enabled !== false && item.modality === "video");
}

function isReferenceOnlyVideoModel(model = getSelectedVideoModel()) {
    const signature = [model?.id, model?.modelName, model?.dbId]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
    return /(^|[^a-z])(i2v|image-to-video)([^a-z]|$)/.test(signature) || signature.includes("video-motion-v1");
}

function getPreferredTextVideoModel() {
    return getVideoModels().find(model => !isReferenceOnlyVideoModel(model)) || null;
}

function ensureVideoModeCompatibleModel(notify = false) {
    if (activeVideoMode !== "text") return false;
    const select = document.getElementById("videoModel");
    if (!select) return false;
    const current = getSelectedVideoModel();
    if (!isReferenceOnlyVideoModel(current)) return false;

    const fallback = getPreferredTextVideoModel();
    if (!fallback || select.value === fallback.id) return false;

    select.value = fallback.id;
    populateVideoOptionsForModel();
    updateVideoCreditEstimate();
    if (notify) {
        showToast(`文生视频已自动切换到 ${fallback.name}`);
    }
    return true;
}

function populateVideoModels() {
    const select = document.getElementById("videoModel");
    if (!select) return;
    const models = getVideoModels();
    if (!models.length) {
        select.innerHTML = `<option value="wan2.6-i2v-flash">Wan2.6 图生视频快速</option>`;
        return;
    }
    const current = select.value;
    select.innerHTML = models.map(item => {
        return `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · 基础 ${Number(item.cost || 18)} 积分</option>`;
    }).join("");
    select.value = models.some(item => item.id === current) ? current : models[0].id;
    populateVideoOptionsForModel();
}

function populateVideoOptionsForModel() {
    const model = getSelectedVideoModel();
    const resolution = document.getElementById("videoResolution");
    const ratio = document.getElementById("videoAspectRatio");
    const duration = document.getElementById("videoDuration");
    if (resolution && model?.sizes?.length) {
        const current = resolution.value;
        resolution.innerHTML = model.sizes.map(size => `<option value="${escapeHtml(size)}">${escapeHtml(size)}</option>`).join("");
        resolution.value = model.sizes.includes(current) ? current : model.defaultSize || model.sizes[0];
    }
    if (ratio && model?.ratios?.length) {
        const current = ratio.value;
        ratio.innerHTML = model.ratios.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("");
        ratio.value = model.ratios.includes(current) ? current : model.defaultRatio || model.ratios[0];
    }
    if (duration && model?.supportedDurations?.length) {
        const current = Number(duration.value || 0);
        duration.innerHTML = model.supportedDurations
            .map(value => `<option value="${escapeHtml(value)}">${escapeHtml(`${value} 秒`)}</option>`)
            .join("");
        duration.value = model.supportedDurations.includes(current) ? String(current) : String(model.supportedDurations[0]);
    }
}

function getSelectedVideoModel() {
    const selected = document.getElementById("videoModel")?.value;
    return getVideoModels().find(item => item.id === selected) || getVideoModels()[0] || null;
}

function getVideoSettings() {
    return {
        model: document.getElementById("videoModel")?.value || "wan2.6-i2v-flash",
        resolution: document.getElementById("videoResolution")?.value || "720p",
        aspectRatio: document.getElementById("videoAspectRatio")?.value || "16:9",
        duration: Number(document.getElementById("videoDuration")?.value || 5),
        motion: document.getElementById("videoMotion")?.value || "dolly-in",
        mode: activeVideoMode
    };
}

function calculateVideoCreditCost(settings = getVideoSettings()) {
    const model = getSelectedVideoModel();
    const baseCost = Number(model?.cost || activeVideoTemplate?.creditCost || 18);
    const rules = getCreditRules().videoResolution || DEFAULT_CREDIT_RULES.videoResolution;
    const resolutionRule = rules[settings.resolution] || DEFAULT_CREDIT_RULES.videoResolution["720p"];
    const duration = Math.max(2, Math.min(25, Number(settings.duration || 5)));
    const durationFactor = Math.max(1, duration / 5);
    const resolutionFactor = Number(resolutionRule.factor || 1);
    const total = Math.max(1, Math.ceil(baseCost * resolutionFactor * durationFactor));
    return {
        total,
        baseCost,
        duration,
        durationFactor,
        modelName: model?.name || settings.model,
        resolutionLabel: resolutionRule.label || settings.resolution,
        resolutionFactor
    };
}

function updateVideoCreditEstimate() {
    const settings = getVideoSettings();
    const estimate = calculateVideoCreditCost(settings);
    setText("videoCreditEstimate", `${estimate.total} 积分`);
    setText("videoCreditBreakdown", `${estimate.modelName} 基础 ${estimate.baseCost}，${estimate.resolutionLabel} x${estimate.resolutionFactor.toFixed(2)}，${estimate.duration} 秒 x${estimate.durationFactor.toFixed(2)}。`);
}

function updateVideoModeState() {
    const drop = document.getElementById("videoReferenceDrop");
    if (!drop) return;
    const isTextMode = activeVideoMode === "text";
    drop.classList.toggle("optional", isTextMode);
    drop.querySelector("strong").textContent = isTextMode ? "可选上传参考图" : "上传图片";
}

async function loadVideoTemplates() {
    const grid = document.getElementById("videoTemplateGrid");
    if (!grid) return;
    grid.innerHTML = `<div class="video-template-empty">正在读取视频模板</div>`;
    try {
        const data = await apiGet("/api/templates?modality=video&page_size=8&include_params=1&sort=featured");
        videoTemplates = data.items || [];
        renderVideoTemplates();
    } catch (error) {
        grid.innerHTML = `<div class="video-template-empty">视频模板暂未入库</div>`;
    }
}

function renderVideoTemplates() {
    const grid = document.getElementById("videoTemplateGrid");
    if (!grid) return;
    if (!videoTemplates.length) {
        grid.innerHTML = `<div class="video-template-empty">暂无视频模板</div>`;
        return;
    }
    grid.innerHTML = videoTemplates.slice(0, 6).map(template => {
        const title = getLocalized(template.title);
        const promo = template.promoVideo || "";
        const media = promo
            ? `<video src="${escapeAttr(assetUrl(promo))}" muted autoplay loop playsinline poster="${escapeAttr(assetUrl(template.cover))}"></video>`
            : `<img src="${escapeAttr(assetUrl(template.cover))}" alt="${escapeHtml(template.imageAlt || title)}" loading="lazy">`;
        return `
            <button class="video-template-card" type="button" data-video-template-id="${escapeAttr(template.id)}">
                ${media}
                <span>${escapeHtml(title)}</span>
                <small>${Number(template.creditCost || 18)} 积分起</small>
            </button>
        `;
    }).join("");
    grid.querySelectorAll("[data-video-template-id]").forEach(button => {
        button.addEventListener("click", () => applyVideoTemplate(button.dataset.videoTemplateId));
    });
}

async function openVideoTemplate(templateId, updateUrl = true) {
    const requestedId = String(templateId || "");
    if (!requestedId) return;
    await ensureTemplateData();
    if (!videoTemplates.length) {
        await loadVideoTemplates();
    }

    let template = videoTemplates.find(item => item.id === requestedId || item.sourceTemplateId === requestedId)
        || awesomeTemplates.find(item => (item.id === requestedId || item.sourceTemplateId === requestedId) && isVideoTemplate(item));

    if (!template || !Array.isArray(template.params)) {
        try {
            const data = await apiGet(`/api/templates/${encodeURIComponent(requestedId)}`);
            template = data.item;
        } catch (error) {
            template = null;
        }
    }

    if (!template || !isVideoTemplate(template)) {
        showToast("没有在数据库里找到对应视频模板", "error");
        return;
    }

    const existingIndex = videoTemplates.findIndex(item => item.id === template.id);
    if (existingIndex >= 0) {
        videoTemplates[existingIndex] = { ...videoTemplates[existingIndex], ...template };
    } else {
        videoTemplates.unshift(template);
    }
    renderVideoTemplates();
    applyVideoTemplate(template.id);
    if (updateUrl !== false) {
        history.replaceState(null, "", `#video-workbench:${encodeURIComponent(template.id)}`);
    }
    document.getElementById("video-workbench")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function applyVideoTemplate(templateId) {
    const template = videoTemplates.find(item => item.id === templateId || item.sourceTemplateId === templateId);
    if (!template) return;
    activeVideoTemplate = template;
    document.querySelectorAll(".video-template-card").forEach(card => {
        card.classList.toggle("active", card.dataset.videoTemplateId === templateId);
    });
    const prompt = buildPrompt(template, Object.fromEntries((template.params || []).map(param => [param.key, param.default || ""])));
    const promptField = document.getElementById("videoPrompt");
    if (promptField) promptField.value = prompt;
    const model = document.getElementById("videoModel");
    const resolution = document.getElementById("videoResolution");
    const ratio = document.getElementById("videoAspectRatio");
    if (model && template.modelRoute && [...model.options].some(option => option.value === template.modelRoute)) {
        model.value = template.modelRoute;
        populateVideoOptionsForModel();
    }
    if (resolution && template.defaultSize && [...resolution.options].some(option => option.value === template.defaultSize)) {
        resolution.value = template.defaultSize;
    }
    if (ratio && template.defaultAspectRatio && [...ratio.options].some(option => option.value === template.defaultAspectRatio)) {
        ratio.value = template.defaultAspectRatio;
    }
    if (!template.allowReferenceImage) {
        activeVideoMode = "text";
        updateVideoModeTabs();
        updateVideoModeState();
    }
    updateVideoCreditEstimate();
    setText("videoResultSummary", `${getLocalized(template.title)} 已载入，可继续修改提示词后生成。`);
}

function initVideoReferenceUpload() {
    const drop = document.getElementById("videoReferenceDrop");
    const input = document.getElementById("videoReferenceInput");
    const openPicker = () => input?.click();
    drop?.addEventListener("click", openPicker);
    drop?.addEventListener("keydown", event => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openPicker();
        }
    });
    input?.addEventListener("change", event => {
        handleVideoReferenceFiles(event.target.files);
        input.value = "";
    });
    drop?.addEventListener("dragover", event => {
        event.preventDefault();
        drop.classList.add("dragover");
    });
    drop?.addEventListener("dragleave", () => drop.classList.remove("dragover"));
    drop?.addEventListener("drop", event => {
        event.preventDefault();
        drop.classList.remove("dragover");
        handleVideoReferenceFiles(event.dataTransfer.files);
    });
    document.getElementById("videoReferencePreview")?.addEventListener("click", event => {
        const remove = event.target.closest("[data-video-reference-remove]");
        if (!remove) return;
        videoReferenceImages = videoReferenceImages.filter(image => image.id !== remove.dataset.videoReferenceRemove);
        renderVideoReferences();
    });
}

async function handleVideoReferenceFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    const remaining = VIDEO_REFERENCE_LIMIT - videoReferenceImages.length;
    if (remaining <= 0) {
        showToast("视频参考图最多上传 10 张", "error");
        return;
    }
    const loaded = [];
    for (const file of files.slice(0, remaining)) {
        try {
            loaded.push(await readVideoReferenceImage(file));
        } catch (error) {
            showToast(error.message, "error");
        }
    }
    if (!loaded.length) return;
    videoReferenceImages = [...videoReferenceImages, ...loaded].slice(0, VIDEO_REFERENCE_LIMIT);
    activeVideoMode = "image";
    updateVideoModeTabs();
    updateVideoModeState();
    renderVideoReferences();
}

function readVideoReferenceImage(file) {
    return new Promise((resolve, reject) => {
        if (!isAllowedUploadImageType(file.type)) {
            reject(new Error("请上传 JPG、PNG 或 WebP 图片"));
            return;
        }
        if (file.size > VIDEO_REFERENCE_MAX_SIZE) {
            reject(new Error("单张图片不能超过 10MB"));
            return;
        }
        const reader = new FileReader();
        reader.onload = event => {
            resolve({
                id: createReferenceId(),
                name: file.name,
                type: file.type || "image/jpeg",
                size: file.size,
                dataUrl: event.target.result
            });
        };
        reader.onerror = () => reject(new Error("图片读取失败"));
        reader.readAsDataURL(file);
    });
}

function renderVideoReferences() {
    setText("videoReferenceCount", `${videoReferenceImages.length} / ${VIDEO_REFERENCE_LIMIT}`);
    const preview = document.getElementById("videoReferencePreview");
    if (!preview) return;
    if (!videoReferenceImages.length) {
        preview.innerHTML = `<span>最多 10 张，单张 10MB 内</span>`;
        return;
    }
    preview.innerHTML = videoReferenceImages.map(image => `
        <article class="template-reference-thumb">
            <img src="${escapeAttr(safeMediaUrl(image.dataUrl))}" alt="${escapeHtml(image.name || "参考图")}">
            <button type="button" aria-label="移除 ${escapeHtml(image.name || "参考图")}" data-video-reference-remove="${escapeAttr(image.id)}">×</button>
        </article>
    `).join("");
}

function getVideoReferencePayload() {
    if (activeVideoMode === "text") return [];
    return videoReferenceImages.map(image => ({
        name: image.name,
        mimeType: image.type,
        byteSize: image.size,
        dataUrl: image.dataUrl
    }));
}

function setVideoResultState(state, data = {}) {
    const preview = document.getElementById("videoPreview");
    const download = document.getElementById("downloadVideoResult");
    if (!preview) return;
    preview.classList.remove("is-loading", "is-error", "has-video");
    preview.querySelector("video")?.remove();
    preview.querySelector(".play-button")?.classList.toggle("hidden", state !== "idle");
    if (download) {
        download.classList.add("disabled");
        download.removeAttribute("href");
    }

    if (state === "loading") {
        preview.classList.add("is-loading");
        setText("videoPreviewLabel", data.label || "视频生成中，请耐心等候");
        setText("videoResultTitle", "正在生成");
        setText("videoResultSummary", data.summary || "任务已提交，正在等待上游返回结果。");
        return;
    }
    if (state === "error") {
        preview.classList.add("is-error");
        setText("videoPreviewLabel", "生成失败");
        setText("videoResultTitle", "生成失败");
        setText("videoResultSummary", data.summary || "视频生成失败，本次不应实际消耗积分；如已预扣或误扣会自动退回。");
        return;
    }
    if (state === "success" && data.videoUrl) {
        preview.classList.add("has-video");
        const videoUrl = assetUrl(data.videoUrl);
        preview.innerHTML = `<video controls playsinline src="${escapeAttr(videoUrl)}"></video><span id="videoPreviewLabel" class="hidden"></span>`;
        if (download) {
            download.classList.remove("disabled");
            download.href = safeLinkUrl(data.videoUrl);
        }
        setText("videoResultTitle", "生成完成");
        setText("videoResultSummary", "视频已生成，可以在线播放和下载。");
        return;
    }
    setText("videoPreviewLabel", "等待生成结果");
    setText("videoResultTitle", "视频结果");
    setText("videoResultSummary", "生成完成后可以在线播放和下载。");
}

async function requestVideoGeneration() {
    const prompt = document.getElementById("videoPrompt")?.value?.trim();
    if (!prompt) {
        showToast("请先填写视频 Prompt", "error");
        return;
    }
    if (activeVideoMode === "image" && !videoReferenceImages.length) {
        showToast("图生视频请先上传参考图", "error");
        return;
    }
    ensureVideoModeCompatibleModel(true);
    if (activeVideoMode === "text" && isReferenceOnlyVideoModel()) {
        showToast("当前模型只支持图生视频，请切换到支持文生的模型", "error");
        return;
    }

    const settings = getVideoSettings();
    const estimate = calculateVideoCreditCost(settings);
    const referenceImages = getVideoReferencePayload();
    const button = document.getElementById("generateVideo");
    if (button) {
        button.disabled = true;
        button.textContent = "生成中";
    }
    clearTimeout(videoPollTimer);
    setVideoResultState("loading", {
        summary: `正在提交视频任务，本次预计消耗 ${estimate.total} 积分。`
    });

    try {
        const data = await apiPost("/api/generate-video", {
            templateId: activeVideoTemplate?.id || null,
            templateTitle: getLocalized(activeVideoTemplate?.title),
            prompt,
            params: {},
            settings,
            referenceImages
        });
        setText("videoResultSummary", data.message || `任务 ${data.jobNo || data.jobId} 已提交，请耐心等候。`);
        showToast("视频任务已提交");
        pollVideoJob(data.jobId);
    } catch (error) {
        setVideoResultState("error", { summary: error.message || "视频服务暂不可用，本次不会扣除积分。" });
        showToast(error.message || "无法提交视频生成", "error");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "生成";
        }
    }
}

async function pollVideoJob(jobId, attempt = 0) {
    if (!jobId) return;
    if (attempt > 120) {
        setVideoResultState("error", {
            summary: "这条视频任务超过预期仍未返回结果，系统可能已卡住。你可以去个人中心刷新记录，或重新生成一版。"
        });
        return;
    }
    try {
        await sleep(attempt === 0 ? 1800 : 0);
        const data = await apiGet(`/api/jobs/${encodeURIComponent(jobId)}`);
        const job = data.item || {};
        if (job.status === "success" && job.videoUrl) {
            setVideoResultState("success", { videoUrl: job.videoUrl });
            showToast("视频生成完成");
            return;
        }
        if (["failed", "cancelled"].includes(job.status)) {
            setVideoResultState("error", {
                summary: job.error || "视频生成失败，本次不应实际消耗积分；如已预扣或误扣会自动退回。"
            });
            return;
        }
        setVideoResultState("loading", {
            label: "视频生成中，请耐心等候",
            summary: job.message || `任务 ${job.jobNo || jobId} 处理中${job.progress ? `，进度 ${job.progress}%` : ""}。`
        });
        videoPollTimer = setTimeout(() => pollVideoJob(jobId, attempt + 1), 5000);
    } catch (error) {
        setText("videoResultSummary", error.message || "暂时无法刷新任务状态，稍后会继续尝试。");
        videoPollTimer = setTimeout(() => pollVideoJob(jobId, attempt + 1), 7000);
    }
}

function initWorkbench() {
    document.getElementById("toggleAdvanced")?.addEventListener("click", event => {
        const panel = document.getElementById("customImageAdvancedPanel");
        panel?.classList.toggle("open");
        event.currentTarget.textContent = panel?.classList.contains("open") ? "收起高级参数" : "展开高级参数";
    });

    ["customImageModel", "customImageQuality", "customImageSize", "customImageCount", "customImageReferenceMode", "customImageOutputFormat", "customImageBackground", "customImageModeration", "customImageOutputCompression"].forEach(id => {
        document.getElementById(id)?.addEventListener("change", () => {
            if (id === "customImageModel") {
                populateCustomImageSizeOptions();
            }
            updateCustomImageOfficialOptions();
            updateCustomImageCreditEstimate();
        });
    });

    document.getElementById("customImageModel")?.addEventListener("change", () => {
        populateCustomImageSizeOptions();
    });
    document.getElementById("customImageForm")?.addEventListener("submit", requestCustomImageGeneration);
    document.getElementById("resetCustomImage")?.addEventListener("click", resetCustomImageWorkbench);
    document.getElementById("downloadCustomImageResult")?.addEventListener("click", downloadCustomImageResult);
    document.getElementById("openCustomImageResult")?.addEventListener("click", openCustomImageResult);
    document.getElementById("saveCustomImageTemplate")?.addEventListener("click", saveCustomImageTemplate);
    document.getElementById("customImageResultGallery")?.addEventListener("click", event => {
        const button = event.target.closest("[data-custom-result-url]");
        if (!button) return;
        selectCustomImageResult(button.dataset.customResultUrl);
    });

    initCustomImageReferenceUpload();
    setCustomImageResultState("idle");
    populateCustomImageControls();
    updateCustomImageOfficialOptions();
    updateCustomImageCreditEstimate();

    document.querySelectorAll(".mode-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const group = tab.closest(".mode-tabs") || document;
            group.querySelectorAll(".mode-tab").forEach(item => item.classList.remove("active"));
            tab.classList.add("active");
        });
    });

    initWorksTabs();
}

function initWorksTabs() {
    const root = document.getElementById("works");
    if (!root) return;

    const tabs = [...root.querySelectorAll(".tab[data-work-filter]")];
    const masonry = document.getElementById("worksMasonry");
    if (!tabs.length || !masonry) return;
    if (!homeWorksSampleMarkup) homeWorksSampleMarkup = masonry.innerHTML;

    tabs.forEach(tab => {
        if (tab.dataset.boundWorksTab === "true") return;
        tab.dataset.boundWorksTab = "true";
        tab.addEventListener("click", () => {
            activeWorksFilter = tab.dataset.workFilter || "all";
            applyWorksFilter(activeWorksFilter);
        });
    });

    activeWorksFilter = root.querySelector(".tab.active")?.dataset.workFilter || "all";
    refreshHomeWorksSection();
}

async function refreshHomeWorksSection() {
    const root = document.getElementById("works");
    const masonry = document.getElementById("worksMasonry");
    if (!root || !masonry) return;

    try {
        const data = await apiGet("/api/account/jobs");
        renderUserWorks(data.items || []);
    } catch (error) {
        if (error?.status === 401 && currentAccount?.authenticated) currentAccount = { authenticated: false };
        renderSampleWorks();
    }
}

function renderSampleWorks() {
    const masonry = document.getElementById("worksMasonry");
    if (!masonry) return;
    masonry.innerHTML = homeWorksSampleMarkup;
    setText("worksEyebrow", "作品示例");
    setText("worksHeading", "登录后这里会自动切换成你的真实生成记录");
    document.getElementById("worksFavoriteTab")?.classList.remove("hidden");
    document.getElementById("worksAccountLink")?.classList.add("hidden");
    applyWorksFilter(activeWorksFilter);
}

function renderUserWorks(items) {
    const masonry = document.getElementById("worksMasonry");
    const accountLink = document.getElementById("worksAccountLink");
    if (!masonry) return;

    setText("worksEyebrow", "我的最近作品");
    setText("worksHeading", "这里展示最近生成的真实结果，可直接点开查看原图或视频");
    document.getElementById("worksFavoriteTab")?.classList.add("hidden");

    if (!Array.isArray(items) || !items.length) {
        masonry.innerHTML = "";
        activeWorksFilter = "all";
        accountLink?.classList.remove("hidden");
        if (accountLink) {
            accountLink.href = "#templates";
            accountLink.textContent = "去模板区开始生成";
        }
        applyWorksFilter(activeWorksFilter);
        return;
    }

    if (activeWorksFilter === "favorite") activeWorksFilter = "all";
    masonry.innerHTML = items.slice(0, 8).map(renderUserWorkCard).join("");
    if (accountLink) {
        accountLink.href = servicePageUrl("account.html");
        accountLink.textContent = "去个人中心查看完整作品库";
        accountLink.classList.remove("hidden");
    }
    applyWorksFilter(activeWorksFilter);
}

function renderUserWorkCard(job, index) {
    const previewUrl = getHomeWorkPreviewUrl(job);
    const resultUrl = getHomeWorkResultUrl(job);
    const href = resultUrl ? safeLinkUrl(resultUrl) : servicePageUrl("account.html");
    const shape = HOME_WORK_CARD_SHAPES[index % HOME_WORK_CARD_SHAPES.length];
    const title = getLocalized(job.templateTitle) || job.templateTitle || (job.modality === "video" ? "视频作品" : "图片作品");
    const meta = `${homeWorkStatusLabel(job.status)} · ${formatHomeWorkTime(job.createdAt)}`;
    const summary = `${title} · ${job.modality === "video" ? "视频" : "图片"}${job.creditCost ? ` · ${Number(job.creditCost)}积分` : ""}`;
    const coverStyle = previewUrl
        ? `style="background-image:${cssUrl(previewUrl)}"`
        : 'style="background-image:linear-gradient(135deg, #e8edf5, #d9e2ef)"';
    return `
        <a class="work-card dynamic-work-card ${shape}" data-work-type="${escapeAttr(job.modality === "video" ? "video" : "image")}" data-work-favorite="false" href="${escapeAttr(href)}" ${href && resultUrl ? 'target="_blank" rel="noopener noreferrer"' : ""} ${coverStyle}>
            <small>${escapeHtml(meta)}</small>
            <span>${escapeHtml(summary)}</span>
        </a>
    `;
}

function getHomeWorkResultUrl(job = {}) {
    if (job.modality === "video") return job.videoUrl || job.thumbnailUrl || "";
    if (Array.isArray(job.imageUrls) && job.imageUrls.length) return job.imageUrls[0];
    return job.imageUrl || job.cover || "";
}

function getHomeWorkPreviewUrl(job = {}) {
    return job.cover || job.thumbnailUrl || job.imageUrl || (Array.isArray(job.imageUrls) ? job.imageUrls[0] : "") || "";
}

function homeWorkStatusLabel(status) {
    return {
        queued: "排队中",
        running: "生成中",
        success: "已完成",
        failed: "失败",
        pending: "待支付"
    }[status] || (status || "处理中");
}

function formatHomeWorkTime(value) {
    if (!value) return "刚刚";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function applyWorksFilter(filter) {
    const root = document.getElementById("works");
    const empty = document.getElementById("worksEmptyState");
    if (!root) return;

    const tabs = [...root.querySelectorAll(".tab[data-work-filter]")];
    const cards = [...root.querySelectorAll(".work-card[data-work-type]")];
    const favoriteVisible = !document.getElementById("worksFavoriteTab")?.classList.contains("hidden");
    const effectiveFilter = !favoriteVisible && filter === "favorite" ? "all" : filter;
    let visibleCount = 0;

    tabs.forEach(tab => {
        tab.classList.toggle("active", tab.dataset.workFilter === effectiveFilter);
    });
    cards.forEach(card => {
        const type = card.dataset.workType || "image";
        const favorite = card.dataset.workFavorite === "true";
        const visible = effectiveFilter === "image"
            ? type === "image"
            : effectiveFilter === "video"
                ? type === "video"
                : effectiveFilter === "favorite"
                    ? favorite
                    : true;
        card.classList.toggle("hidden", !visible);
        if (visible) visibleCount += 1;
    });
    empty?.classList.toggle("hidden", visibleCount > 0);
}

function initPricingToggle() {
    const toggle = document.getElementById("billingCycle");
    const amounts = document.querySelectorAll(".price .amount[data-monthly]");

    toggle?.addEventListener("change", () => {
        amounts.forEach(el => {
            const value = toggle.checked ? el.dataset.yearly : el.dataset.monthly;
            el.textContent = `¥${value}`;
        });
    });
}

function initPaymentModal() {
    const modal = document.getElementById("paymentModal");
    modal?.addEventListener("click", event => {
        if (event.target === modal) closePayment();
    });
    document.querySelectorAll("[data-open-payment]").forEach(button => {
        button.addEventListener("click", () => openPayment(button.dataset.openPayment || "free"));
    });
    document.querySelectorAll("[data-close-payment]").forEach(button => {
        button.addEventListener("click", closePayment);
    });
    bindPaymentMethodButtons();
    document.getElementById("paymentAction")?.addEventListener("click", submitPaymentOrder);
}

function bindPaymentMethodButtons() {
    document.querySelectorAll(".payment-method[data-method]").forEach(button => {
        button.addEventListener("click", () => selectMethod(button.dataset.method || "wechat", button));
    });
}

function renderPaymentMethods() {
    const container = document.querySelector(".payment-methods");
    if (!container) return;
    const payment = publicSettings.payment || {};
    const channels = (payment.enabledChannels || ["wechat", "alipay"]).filter(channel => channel !== "service");
    const visibleChannels = channels.length ? channels : ["wechat", "alipay"];
    const labels = {
        wechat: "微信支付",
        alipay: "支付宝"
    };
    container.innerHTML = visibleChannels
        .filter(channel => labels[channel])
        .map((channel, index) => `<button class="payment-method ${index === 0 ? "active" : ""}" type="button" data-method="${channel}">${labels[channel]}</button>`)
        .join("");
    bindPaymentMethodButtons();
    const firstMethod = container.querySelector(".payment-method[data-method]");
    if (firstMethod) selectMethod(firstMethod.dataset.method || "wechat", firstMethod);
}

function updatePaymentTrustPill() {
    const pill = document.getElementById("paymentTrustPill");
    if (!pill) return;
    pill.textContent = "微信 / 支付宝扫码";
}

function normalizePlanCode(planId) {
    return PLAN_CODE_ALIASES_CLIENT[planId] || planId || "";
}

function clientPlanIdFor(planId) {
    const code = normalizePlanCode(planId);
    return PLAN_CODE_TO_CLIENT_ID[code] || planId;
}

function getPricingPlanConfig(planId) {
    const code = normalizePlanCode(planId);
    const id = code ? `plan_${code}` : "";
    return (publicSettings.pricingPlans || []).find(item => item.code === code || item.code === planId || item.id === planId || item.id === id) || null;
}

function getPlanPriceCents(planId) {
    const serverPlan = getPricingPlanConfig(planId);
    if (serverPlan && Number.isFinite(Number(serverPlan.priceCents))) {
        return Number(serverPlan.priceCents);
    }
    const localPlan = PRICING[clientPlanIdFor(planId)] || PRICING[planId];
    return Math.round(Number(localPlan?.price || 0) * 100);
}

function getPlanCredits(planId) {
    const serverPlan = getPricingPlanConfig(planId);
    if (serverPlan && Number.isFinite(Number(serverPlan.credits))) {
        return Number(serverPlan.credits);
    }
    return FALLBACK_PLAN_CREDITS[clientPlanIdFor(planId)] || 0;
}

function currentMembershipCode() {
    return currentAccount?.stats?.membership || currentAccount?.user?.membershipLevel || "free";
}

function formatCnyFromCents(cents) {
    const value = Number(cents || 0) / 100;
    return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
}

function paymentQuoteFor(planId) {
    const targetCode = normalizePlanCode(planId);
    const targetRank = SUBSCRIPTION_PLAN_RANK_CLIENT[targetCode] || 0;
    const targetPriceCents = getPlanPriceCents(planId);
    const targetCredits = getPlanCredits(planId);
    const quote = {
        amountCents: targetPriceCents,
        note: targetCredits ? `本次开通到账 ${targetCredits} 积分。` : ""
    };
    if (!targetRank || !currentAccount?.authenticated) {
        return quote;
    }

    const currentCode = currentMembershipCode();
    const currentRank = SUBSCRIPTION_PLAN_RANK_CLIENT[currentCode] || 0;
    if (!currentRank || targetRank <= currentRank) {
        return quote;
    }

    const currentPriceCents = getPlanPriceCents(currentCode);
    const currentCredits = getPlanCredits(currentCode);
    const upgradeAmountCents = Math.max(0, targetPriceCents - currentPriceCents);
    const grantCredits = Math.max(0, targetCredits - currentCredits);
    return {
        amountCents: upgradeAmountCents,
        note: `升级补差价：原价 ¥${formatCnyFromCents(targetPriceCents)}，已抵扣 ¥${formatCnyFromCents(currentPriceCents)}；本次到账 ${grantCredits} 积分。`,
        upgrade: true
    };
}

function setPaymentQuote(planId, serverOrder = null) {
    const plan = PRICING[clientPlanIdFor(planId)] || PRICING[planId] || PRICING.pro;
    const quote = serverOrder
        ? {
            amountCents: Number(serverOrder.amountCents ?? Math.round(Number(serverOrder.amount || 0) * 100)),
            note: serverOrder.metadata?.upgrade
                ? `升级补差价：原价 ¥${formatCnyFromCents(serverOrder.metadata.upgrade.originalAmountCents)}，已抵扣 ¥${formatCnyFromCents(serverOrder.metadata.upgrade.deductedAmountCents)}；本次到账 ${serverOrder.plan?.grantCredits || serverOrder.metadata?.grantCredits || 0} 积分。`
                : (serverOrder.plan?.grantCredits ? `本次到账 ${serverOrder.plan.grantCredits} 积分。` : "")
        }
        : paymentQuoteFor(planId);

    setText("planName", plan.name);
    setText("planPrice", formatCnyFromCents(quote.amountCents));
    setText("paymentQuoteNote", quote.note || "");
}

function openPayment(planId) {
    if (clientPlanIdFor(planId) === "free") {
        startFreeExperience();
        return;
    }
    paymentState.planId = planId;
    paymentState.orderNo = "";
    setPaymentQuote(planId);
    setPaymentBusy(false);
    if (!["wechat", "alipay"].includes(paymentState.channel)) paymentState.channel = "wechat";
    renderPaymentResult({ displayMode: "placeholder", message: "创建订单后会显示 MPAY 扫码支付二维码；支付成功后通常会自动到账，如未到账可联系客服核验开通。" });
    const firstMethod = document.querySelector(".payment-method[data-method]");
    if (firstMethod) selectMethod(firstMethod.dataset.method || "wechat", firstMethod);
    const modal = document.getElementById("paymentModal");
    modal?.classList.add("active");
    modal?.setAttribute("aria-hidden", "false");
    activateDialog(modal, closePayment, "#paymentAction");
}

function startFreeExperience() {
    closePayment();
    if (!currentAccount?.authenticated) {
        openAccountModal("register");
        showToast("先注册即可领取免费体验积分");
        return;
    }

    const target = document.getElementById("template-editor") || document.getElementById("templates");
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
    if (document.getElementById("template-editor")) {
        history.replaceState(null, "", "#template-editor");
    }
    showToast("免费体验已开启，直接开始生成即可");
}

function closePayment() {
    if (paymentState.pollTimer) {
        clearTimeout(paymentState.pollTimer);
        paymentState.pollTimer = null;
    }
    const modal = document.getElementById("paymentModal");
    modal?.classList.remove("active");
    modal?.setAttribute("aria-hidden", "true");
    deactivateDialog(modal);
}

function selectMethod(method, target) {
    document.querySelectorAll(".payment-method").forEach(item => item.classList.remove("active"));
    target?.classList.add("active");
    paymentState.channel = method === "alipay" ? "alipay" : "wechat";

    const hint = document.getElementById("qrcodeHint");
    const hintMap = {
        wechat: "下单后显示微信扫码支付二维码，通常自动到账；未到账可联系客服核验开通",
        alipay: "下单后显示支付宝扫码支付二维码，通常自动到账；未到账可联系客服核验开通"
    };
    if (hint) hint.textContent = hintMap[paymentState.channel] || hintMap.wechat;
    const action = document.getElementById("paymentAction");
    if (action) action.textContent = "立即创建支付二维码";
    if (!paymentState.orderNo) {
        renderPaymentResult({ displayMode: "placeholder", message: hintMap[paymentState.channel] || hintMap.wechat });
    }
}

function setPaymentBusy(busy) {
    const action = document.getElementById("paymentAction");
    if (!action) return;
    action.disabled = busy;
    action.textContent = busy ? "正在创建二维码..." : "立即创建支付二维码";
}

function looksLikeQrPayload(value) {
    if (!value) return false;
    const text = String(value).trim();
    return /^(weixin|alipayqr|https?:\/\/|wxp:|alipays?:|uppay:|unionpay:)/i.test(text);
}

function renderDynamicQrcode(target, value) {
    if (!target || !value || typeof QRCode === "undefined") return false;
    target.innerHTML = "";
    new QRCode(target, {
        text: String(value),
        width: 168,
        height: 168,
        colorDark: "#111111",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
    });
    const generated = target.querySelector("img, canvas");
    if (generated) {
        generated.classList.add("qrcode-image");
    }
    return Boolean(generated);
}

function getPaymentPlaceholderImage(channel = paymentState.channel) {
    return safeMediaUrl(PAYMENT_CHANNEL_PLACEHOLDER_IMAGES[channel] || PAYMENT_CHANNEL_PLACEHOLDER_IMAGES.wechat);
}

function renderPaymentResult(payment) {
    const area = document.getElementById("qrcodeArea");
    const contact = document.getElementById("paymentContactValue");
    if (!area) return;
    const message = payment?.message || "";
    if (payment?.displayMode === "qrcode" && payment.qrcodeUrl) {
        const qrValue = String(payment.qrcodeUrl || "").trim();
        if (looksLikeQrPayload(qrValue)) {
            area.innerHTML = `
                <div class="qrcode-image-wrap" id="paymentDynamicQrcode" aria-label="支付二维码"></div>
                <p id="qrcodeHint">${escapeHtml(message || "请扫码完成支付，系统会自动刷新订单状态。")}</p>
            `;
            const target = document.getElementById("paymentDynamicQrcode");
            if (!renderDynamicQrcode(target, qrValue)) {
                const safeQrLink = safeLinkUrl(qrValue);
                area.innerHTML = `
                    <div class="qrcode-placeholder">扫码支付</div>
                    <p id="qrcodeHint">${escapeHtml(message || "二维码生成失败，请重新创建订单。")}</p>
                    ${safeQrLink ? `<a class="btn btn-primary btn-full" href="${escapeAttr(safeQrLink)}" target="_blank" rel="noopener noreferrer">打开支付链接</a>` : ""}
                `;
            }
        } else {
            const qrImageUrl = safeMediaUrl(qrValue);
            area.innerHTML = `
                <div class="qrcode-image-wrap">
                    ${qrImageUrl ? `<img class="qrcode-image" src="${escapeAttr(qrImageUrl)}" alt="支付二维码">` : `<div class="qrcode-placeholder">MPAY</div>`}
                </div>
                <p id="qrcodeHint">${escapeHtml(message || "请扫码完成支付，系统会自动刷新订单状态。")}</p>
            `;
        }
    } else if (payment?.displayMode === "redirect" && payment.paymentUrl) {
        const paymentUrl = safeLinkUrl(payment.paymentUrl);
        area.innerHTML = `
            <p id="qrcodeHint">${escapeHtml(message || "请打开支付链接完成支付。")}</p>
            ${paymentUrl ? `<a class="btn btn-primary btn-full" href="${escapeAttr(paymentUrl)}" target="_blank" rel="noopener noreferrer">打开支付链接</a>` : ""}
        `;
    } else {
        const placeholderImageUrl = getPaymentPlaceholderImage();
        area.innerHTML = `
            <div class="qrcode-image-wrap">
                ${placeholderImageUrl ? `<img class="qrcode-image" src="${escapeAttr(placeholderImageUrl)}" alt="${escapeAttr(paymentState.channel === "alipay" ? "支付宝收款码" : "微信收款码")}">` : `<div class="qrcode-placeholder">MPAY</div>`}
            </div>
            <p id="qrcodeHint">${escapeHtml(message || "创建订单后会生成本单专属支付二维码。")}</p>
        `;
    }
    if (contact) contact.textContent = paymentState.orderNo ? `订单 ${paymentState.orderNo} 等待支付` : "等待创建订单";
}

async function submitPaymentOrder() {
    if (!currentAccount?.authenticated) {
        await refreshAccountState();
    }
    if (!currentAccount?.authenticated) {
        closePayment();
        openAccountModal("login");
        showToast("请先登录后再提交订单", "error");
        return;
    }
    if (!paymentState.planId) return;
    setPaymentBusy(true);
    try {
        const data = await apiPost("/api/pay/orders", {
            planCode: paymentState.planId,
            channel: paymentState.channel
        });
        paymentState.orderNo = data.item?.orderNo || "";
        if (data.item) setPaymentQuote(paymentState.planId, data.item);
        renderPaymentResult(data.payment || {});
        if (paymentState.orderNo) {
            startPaymentPolling(paymentState.orderNo);
        } else {
            await refreshAccountState();
        }
    } catch (error) {
        renderPaymentResult({ displayMode: "placeholder", message: error.message || "创建支付订单失败，请稍后再试。" });
        showToast(error.message || "创建支付订单失败", "error");
    } finally {
        setPaymentBusy(false);
    }
}

function startPaymentPolling(orderNo) {
    if (paymentState.pollTimer) {
        clearTimeout(paymentState.pollTimer);
        paymentState.pollTimer = null;
    }
    const poll = async () => {
        try {
            const data = await apiGet(`/api/pay/orders/${encodeURIComponent(orderNo)}`);
            const item = data.item || {};
            if (item.status === "paid") {
                renderPaymentResult({ displayMode: "placeholder", message: "支付成功，会员或积分通常会自动到账；如未到账请联系客服核验。" });
                await refreshAccountState();
                showToast("支付成功，权益已到账");
                return;
            }
            if (item.status === "failed" || item.status === "cancelled" || item.status === "refunded") {
                renderPaymentResult({ displayMode: "placeholder", message: "订单未支付成功，请重新创建订单。" });
                return;
            }
        } catch (error) {
            console.warn("payment poll failed", error);
        }
        paymentState.pollTimer = window.setTimeout(poll, 3000);
    };
    paymentState.pollTimer = window.setTimeout(poll, 3000);
}

function initAccountModal() {
    const modal = document.getElementById("accountModal");
    document.querySelectorAll("[data-open-account]").forEach(button => {
        button.addEventListener("click", () => {
            if (currentAccount?.authenticated) {
                window.location.href = servicePageUrl("account.html");
                return;
            }
            openAccountModal();
        });
    });
    document.querySelectorAll("[data-open-register]").forEach(button => {
        button.addEventListener("click", () => {
            if (currentAccount?.authenticated) {
                window.location.href = servicePageUrl("account.html");
                return;
            }
            openAccountModal("register");
        });
    });

    document.querySelectorAll("[data-auth-tab]").forEach(button => {
        button.addEventListener("click", () => switchAuthTab(button.dataset.authTab));
    });

    document.getElementById("loginForm")?.addEventListener("submit", event => {
        event.preventDefault();
        loginWithPassword();
    });
    document.getElementById("registerForm")?.addEventListener("submit", event => {
        event.preventDefault();
        registerWithEmail();
    });
    document.getElementById("copyInviteCode")?.addEventListener("click", copyInviteCode);
    document.getElementById("logoutAccount")?.addEventListener("click", logoutAccount);

    refreshAccountState();

    document.querySelectorAll("[data-close-account]").forEach(button => {
        button.addEventListener("click", () => {
            closeAccountModal();
        });
    });

    modal?.addEventListener("click", event => {
        if (event.target === modal) closeAccountModal();
    });
}

function openAccountModal(preferredTab = "") {
    const modal = document.getElementById("accountModal");
    if (!currentAccount?.authenticated && preferredTab) switchAuthTab(preferredTab);
    renderAccountState();
    modal?.classList.add("active");
    modal?.setAttribute("aria-hidden", "false");
    activateDialog(modal, closeAccountModal, currentAccount?.authenticated ? "#logoutAccount" : "#loginEmail");
}

function closeAccountModal() {
    const modal = document.getElementById("accountModal");
    modal?.classList.remove("active");
    modal?.setAttribute("aria-hidden", "true");
    deactivateDialog(modal);
}

function switchAuthTab(tab) {
    const nextTab = tab === "register" ? "register" : "login";
    document.querySelectorAll("[data-auth-tab]").forEach(button => {
        const selected = button.dataset.authTab === nextTab;
        button.classList.toggle("active", selected);
        button.setAttribute("aria-selected", selected ? "true" : "false");
    });
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    loginForm?.classList.toggle("active", nextTab === "login");
    registerForm?.classList.toggle("active", nextTab === "register");
    if (loginForm) loginForm.hidden = nextTab !== "login";
    if (registerForm) registerForm.hidden = nextTab !== "register";
}

async function refreshAccountState() {
    try {
        currentAccount = await apiGet("/api/auth/me");
    } catch (error) {
        currentAccount = { authenticated: false };
    }
    renderAccountState();
    await refreshHomeWorksSection();
}

function renderAccountState() {
    const authenticated = Boolean(currentAccount?.authenticated);
    document.getElementById("authGuestView")?.classList.toggle("active", !authenticated);
    document.getElementById("authAccountView")?.classList.toggle("active", authenticated);
    setText("accountModalTitle", authenticated ? "账户中心" : "登录/注册");

    const navLogin = document.querySelector("[data-open-account]");
    if (navLogin) navLogin.textContent = authenticated ? "账户中心" : "登录/注册";
    document.querySelectorAll("[data-open-register]").forEach(button => {
        button.classList.toggle("hidden", authenticated);
        button.setAttribute("aria-hidden", authenticated ? "true" : "false");
    });

    if (!authenticated) return;
    const user = currentAccount.user || {};
    const stats = currentAccount.stats || {};
    const invite = currentAccount.invite || {};
    setText("accountName", user.displayName || user.mobile || user.email || "YCImage 用户");
    setText("accountCredits", `${stats.credits ?? 0}`);
    setText("accountWorks", `${stats.works ?? 0}`);
    setText("accountFavorites", `${stats.favorites ?? 0}`);
    setText("accountMembership", membershipLabel(stats.membership || user.membershipLevel));
    setText("accountInviteCode", invite.code || "--");
    setText("accountInviteMeta", `已邀请 ${invite.count || 0} 人；好友注册成功后，你获得 ${invite.rewardCredits || 100} 积分。`);
}

function membershipLabel(value) {
    const map = {
        free: "免费体验",
        monthly: "月卡",
        creator: "创作者版",
        studio: "工作室版",
        enterprise: "企业版",
        credit_pack: "积分包用户"
    };
    return map[value] || value || "免费体验";
}

async function loginWithPassword() {
    const submit = document.querySelector("#loginForm button[type='submit']");
    const payload = {
        email: document.getElementById("loginEmail")?.value?.trim(),
        password: document.getElementById("loginPassword")?.value || ""
    };
    if (submit) {
        submit.disabled = true;
        submit.textContent = "登录中";
    }
    try {
        const data = await apiPost("/api/auth/password-login", payload);
        currentAccount = data;
        renderAccountState();
        await refreshHomeWorksSection();
        closeAccountModal();
        showToast(data.message || "登录成功");
    } catch (error) {
        setText("loginHint", error.message || "登录失败");
        showToast(error.message || "登录失败", "error");
    } finally {
        if (submit) {
            submit.disabled = false;
            submit.textContent = "登录";
        }
    }
}

async function registerWithEmail() {
    const submit = document.querySelector("#registerForm button[type='submit']");
    const password = document.getElementById("registerPassword")?.value || "";
    const confirmPassword = document.getElementById("registerConfirmPassword")?.value || "";
    const passwordError = validateRegisterPassword(password, confirmPassword);
    if (passwordError) {
        setText("registerHint", passwordError);
        showToast(passwordError, "error");
        return;
    }
    const payload = {
        email: document.getElementById("registerEmail")?.value?.trim(),
        password,
        confirmPassword,
        inviteCode: document.getElementById("registerInviteCode")?.value?.trim(),
        displayName: document.getElementById("registerDisplayName")?.value?.trim()
    };
    if (submit) {
        submit.disabled = true;
        submit.textContent = "注册中";
    }
    try {
        const data = await apiPost("/api/auth/register", payload);
        currentAccount = data;
        renderAccountState();
        await refreshHomeWorksSection();
        closeAccountModal();
        showToast(data.message || "注册成功");
    } catch (error) {
        showToast(error.message || "注册失败", "error");
    } finally {
        if (submit) {
            submit.disabled = false;
            submit.textContent = "注册并领取 100 积分";
        }
    }
}

function validateRegisterPassword(password, confirmPassword) {
    if (password.length < 8) return "密码至少需要 8 位";
    if (!/[A-Z]/.test(password)) return "密码需要包含至少 1 个大写字母";
    if (!/[a-z]/.test(password)) return "密码需要包含至少 1 个小写字母";
    if (!/\d/.test(password)) return "密码需要包含至少 1 个数字";
    if (password !== confirmPassword) return "两次输入的密码不一致";
    return "";
}

async function copyInviteCode() {
    const code = currentAccount?.invite?.code;
    if (!code) return;
    try {
        await navigator.clipboard.writeText(code);
        showToast("邀请码已复制");
    } catch (error) {
        showToast(`邀请码：${code}`);
    }
}

async function logoutAccount() {
    try {
        await apiPost("/api/auth/logout", {});
    } catch (error) {
        // Local logout still clears any legacy browser token when the server is unavailable.
    }
    clearLegacySessionStorage();
    currentAccount = { authenticated: false };
    renderAccountState();
    await refreshHomeWorksSection();
    showToast("已退出登录");
}

function showToast(message, type = "success") {
    const container = document.getElementById("toast");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.setAttribute("role", type === "error" ? "alert" : "status");
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(6px)";
    }, 2400);

    setTimeout(() => toast.remove(), 2800);
}

function renderHeroTemplates() {
    const heroIds = publicSettings.heroTemplateIds || [];
    if (!heroIds.length) {
        setHeroShowcaseReady();
        return;
    }

    const defaults = [
        { imageId: "heroImagePrimary", titleId: "heroTitlePrimary", metaId: "heroMetaPrimary" },
        { imageId: "heroImageSecondary", titleId: "heroTitleSecondary", metaId: "" },
        { imageId: "heroImageTertiary", titleId: "heroTitleTertiary", metaId: "" }
    ];

    defaults.forEach((slot, index) => {
        const templateId = heroIds[index];
        if (!templateId) return;
        const template = awesomeTemplates.find(item => item.id === templateId) || heroTemplateLookup[templateId];
        if (!template) return;

        const title = getLocalized(template.title);
        const cover = assetUrl(template.cover || template.sourceCase?.image || "");
        const imageNode = document.getElementById(slot.imageId);
        const titleNode = document.getElementById(slot.titleId);
        const metaNode = slot.metaId ? document.getElementById(slot.metaId) : null;

        if (imageNode && cover) {
            imageNode.style.backgroundImage = `linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(0, 0, 0, 0.12)), ${cssUrl(cover)}`;
            imageNode.style.backgroundSize = "cover";
            imageNode.style.backgroundPosition = "center";
        }
        if (titleNode) titleNode.textContent = title;
        if (metaNode) {
            const unit = isVideoTemplate(template) ? "条" : "张";
            metaNode.textContent = `${Number(template.creditCost || 5)} 积分 / ${unit}`;
        }
    });
    setHeroShowcaseReady();
}

function setHeroShowcaseReady() {
    document.querySelector(".hero-showcase")?.classList.remove("hero-loading");
}

function getHomeCategoryDisplayLabel(label = "") {
    const aliases = {
        "\u4ea7\u54c1\u4e0e\u7535\u5546": "\u4ea7\u54c1\u56fe",
        "\u6d77\u62a5\u4e0e\u5b57\u4f53": "\u6d77\u62a5\u5c01\u9762",
        "\u6444\u5f71\u4e0e\u5199\u5b9e": "\u6444\u5f71\u5199\u771f",
        "\u56fe\u8868\u4e0e\u4fe1\u606f\u56fe": "\u4fe1\u606f\u56fe",
        "\u54c1\u724c\u4e0e\u6807\u5fd7": "\u54c1\u724c\u8bbe\u8ba1",
        "\u63d2\u753b\u4e0e\u827a\u672f": "\u63d2\u753b",
        "\u4eba\u7269\u4e0e\u89d2\u8272": "\u4eba\u7269",
        "\u77ed\u89c6\u9891": "\u77ed\u89c6\u9891"
    };
    return aliases[label] || label;
}

function getHomeFilterKey(template, categoryLabel = "") {
    if (isVideoTemplate(template)) return "video";
    return slugifyForFilter(categoryLabel || template?.categoryLabel || template?.category || "other");
}

function renderHomeCategoryFilters() {
    const row = document.getElementById("homeCategoryRow");
    if (!row) return;

    const counts = new Map();
    awesomeTemplates.slice(0, POPULAR_TEMPLATE_LIMIT).forEach(template => {
        const label = isVideoTemplate(template)
            ? "\u77ed\u89c6\u9891"
            : getCategoryLabel(template.categoryLabel || template.category);
        const key = getHomeFilterKey(template, label);
        const current = counts.get(key) || { key, label, count: 0 };
        current.count += 1;
        counts.set(key, current);
    });

    const topCategories = Array.from(counts.values())
        .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, "zh-CN"))
        .slice(0, HOME_CATEGORY_LIMIT);

    const validKeys = new Set(["all", ...topCategories.map(item => item.key)]);
    if (!validKeys.has(activeHomeCategoryFilter)) activeHomeCategoryFilter = "all";

    row.innerHTML = [
        `<button class="chip ${activeHomeCategoryFilter === "all" ? "active" : ""}" data-filter="all">\u5168\u90e8</button>`,
        ...topCategories.map(item => `<button class="chip ${activeHomeCategoryFilter === item.key ? "active" : ""}" data-filter="${escapeHtml(item.key)}">${escapeHtml(getHomeCategoryDisplayLabel(item.label))}</button>`)
    ].join("");

    bindHomeTemplateFilterEvents();
}

function bindHomeTemplateFilterEvents() {
    document.querySelectorAll("#homeCategoryRow .chip[data-filter]").forEach(chip => {
        chip.onclick = () => applyHomeTemplateFilter(chip.dataset.filter || "all");
    });
}

function applyHomeTemplateFilter(filter = "all") {
    activeHomeCategoryFilter = filter || "all";
    document.querySelectorAll("#homeCategoryRow .chip[data-filter]").forEach(chip => {
        chip.classList.toggle("active", chip.dataset.filter === activeHomeCategoryFilter);
    });
    const grid = document.getElementById("homeTemplateGrid");
    if (!grid || !awesomeTemplates.length) return;
    const sourceTemplates = awesomeTemplates.slice(0, POPULAR_TEMPLATE_LIMIT);
    const filteredTemplates = activeHomeCategoryFilter === "all"
        ? sourceTemplates
        : sourceTemplates.filter(template => {
            const category = getCategoryLabel(template.categoryLabel || template.category);
            return getHomeFilterKey(template, category) === activeHomeCategoryFilter;
        });
    const visibleTemplates = filteredTemplates.slice(0, 6);

    grid.innerHTML = visibleTemplates.map(template => {
        const title = getLocalized(template.title);
        const category = getCategoryLabel(template.categoryLabel || template.category);
        const cover = assetUrl(template.cover || template.sourceCase?.image || "");
        const isVideo = isVideoTemplate(template);
        const filterKey = getHomeFilterKey(template, category);
        const target = isVideo ? `#video-workbench:${encodeURIComponent(template.id)}` : `#template-editor:${encodeURIComponent(template.id)}`;
        const action = isVideo ? "\u751f\u6210\u89c6\u9891" : "\u4f7f\u7528\u6a21\u677f";
        return `
            <article class="template-card" data-category="${escapeHtml(filterKey)}">
                <button class="template-cover" type="button" data-template-id="${escapeAttr(template.id)}" style="--cover:${cssUrl(cover)}" aria-label="\u4f7f\u7528 ${escapeHtml(title)} \u6a21\u677f"></button>
                <div class="template-body">
                    <span class="tag ${isVideo ? "brown" : ""}">${escapeHtml(isVideo ? "\u77ed\u89c6\u9891" : category)}</span>
                    <h3>${escapeHtml(title)}</h3>
                    <p>${escapeHtml(getLocalized(template.description) || "\u9009\u62e9\u540e\u53ef\u8c03\u6574\u53c2\u6570\u548c Prompt\u3002")}</p>
                    <div class="card-meta">
                        <span>${Number(template.usageToday || template.usageCount || 0).toLocaleString("zh-CN")} \u4eba\u4f7f\u7528</span>
                        <strong>${Number(template.creditCost || 5)} \u79ef\u5206/${isVideo ? "\u6761" : "\u5f20"}</strong>
                    </div>
                    <a href="${escapeAttr(target)}" class="card-action" data-template-id="${escapeAttr(template.id)}">${action}</a>
                </div>
            </article>
        `;
    }).join("");

    grid.querySelectorAll("[data-template-id]").forEach(trigger => {
        trigger.addEventListener("click", event => {
            const template = awesomeTemplates.find(item => item.id === trigger.dataset.templateId);
            if (isVideoTemplate(template)) {
                event.preventDefault();
                openVideoTemplate(trigger.dataset.templateId);
                return;
            }
            event.preventDefault();
            openAwesomeTemplate(trigger.dataset.templateId);
        });
    });
}

function renderHomeTemplateGrid() {
    const grid = document.getElementById("homeTemplateGrid");
    if (!grid || !awesomeTemplates.length) return;
    renderHomeCategoryFilters();
    applyHomeTemplateFilter(activeHomeCategoryFilter);
}

async function pollImageJob(jobId, attempt = 0) {
    if (!jobId) return;
    if (attempt > 120) {
        setTemplateResultError();
        setText("editorResultTitle", "生成耗时过长");
        setText("editorResultSummary", "这条任务超过预期仍未返回结果，系统可能已卡住。你可以去个人中心刷新记录，或直接重新生成一版。");
        return;
    }
    try {
        await sleep(attempt === 0 ? 1800 : 0);
        const data = await apiGet(`/api/jobs/${encodeURIComponent(jobId)}`);
        const job = data.item || {};
        const imageUrl = job.imageUrl || (Array.isArray(job.imageUrls) && job.imageUrls.length ? job.imageUrls[0] : "");
        if (job.status === "success" && imageUrl) {
            setTemplateResultImage(imageUrl);
            setTemplateResultGenerating(false);
            setText("editorResultTitle", "生成完成");
            setText("editorResultSummary", "图片已生成，可以下载高清图。");
            showToast("图片生成完成");
            return;
        }
        if (["failed", "cancelled"].includes(job.status)) {
            setTemplateResultError();
            setText("editorResultTitle", "生成失败");
            setText("editorResultSummary", job.error || "图片生成失败，本次不应实际消耗积分；如已预扣或误扣会自动退回。");
            return;
        }
        setTemplateResultGenerating(true, "正在生成，请耐心等候");
        setText("editorResultSummary", job.message || `任务 ${job.jobNo || jobId} 处理中${job.progress ? `，进度 ${job.progress}%` : ""}。`);
        imagePollTimer = setTimeout(() => pollImageJob(jobId, attempt + 1), 5000);
    } catch (error) {
        setText("editorResultSummary", error.message || "暂时无法刷新任务状态，稍后会继续尝试。");
        imagePollTimer = setTimeout(() => pollImageJob(jobId, attempt + 1), 7000);
    }
}
