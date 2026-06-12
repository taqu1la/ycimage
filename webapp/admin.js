const TEMPLATE_PAGE_SIZE = 16;
const LOCAL_API_ORIGIN = "http://127.0.0.1:4178";
const DEFAULT_IMAGE_MODEL = "gpt-image-2-high";
const LEGACY_AUTH_STORAGE_KEY = "ycimage_auth_session";
const LEGACY_ADMIN_TOKEN_STORAGE_KEY = "ycimage_admin_token";

const CATEGORY_LABELS = {
    "Architecture & Spaces": "Architecture & Spaces",
    "Brand & Logos": "Brand & Logos",
    "Characters & People": "Characters & People",
    "Charts & Infographics": "Charts & Infographics",
    "Documents & Publishing": "Documents & Publishing",
    "History & Classical Themes": "History & Classical Themes",
    "Illustration & Art": "Illustration & Art",
    "Other Use Cases": "Other Use Cases",
    "Photography & Realism": "Photography & Realism",
    "Posters & Typography": "Posters & Typography",
    "Products & E-commerce": "Products & E-commerce",
    "Scenes & Storytelling": "Scenes & Storytelling",
    "UI & Interfaces": "UI & Interfaces"
};

const STATUS_LABELS = {
    queued: ["Queued", "neutral"],
    running: ["Running", "warning"],
    success: ["Success", "success"],
    failed: ["Failed", "danger"],
    review: ["In review", "warning"],
    enabled: ["Enabled", "success"],
    hidden: ["Hidden", "neutral"],
    archived: ["Archived", "neutral"],
    paid: ["Paid", "success"],
    pending: ["Pending", "warning"],
    refunded: ["Refunded", "danger"],
    approved: ["Approved", "success"],
    rejected: ["Rejected", "danger"],
    manual: ["Manual", "neutral"],
    escalated: ["Escalated", "danger"]
};

let adminState = createEmptyState();
let templateState = {
    page: 1,
    query: "",
    category: "all",
    status: "all",
    sort: "updated"
};
let templateCoverUpload = null;
let modelRouteState = {
    editingId: ""
};
let adminSessionReady = false;

document.addEventListener("DOMContentLoaded", async () => {
    clearLegacyAuthStorage();
    bindNavigation();
    bindGlobalActions();
    bindTemplateControls();
    bindJobControls();
    bindModelControls();
    bindUserControls();
    bindReviewControls();
    bindSettingsForms();
    await loadAdminState();
});

function createEmptyState() {
    return {
        settings: {
            siteName: "YCImage",
            homeTemplateLimit: 30,
            defaultModel: DEFAULT_IMAGE_MODEL,
            defaultQuality: "medium",
            enablePublicLibrary: true,
            requireReviewBeforeDownload: false,
            heroTemplateIds: []
        },
        api: {
            endpoint: "/api/generate-image",
            balanceEndpoint: "/api/admin/model-balance",
            serverKeyStatus: "not_configured",
            apimartBaseUrl: "https://api.apimart.ai",
            apimartKeyConfigured: false,
            retryLimit: 2
        },
        security: {
            adminEmail: "admin@example.com",
            adminName: "Admin",
            adminPasswordConfigured: false
        },
        templates: [],
        categories: [],
        models: [],
        jobs: [],
        users: [],
        orders: [],
        reviewItems: [],
        activities: [],
        stats: { images: 0, assets: 0 }
    };
}

function apiUrl(path) {
    if (!path) return "";
    const value = String(path).trim();
    if (/^https?:\/\//i.test(value) || isSafeDataImageUrl(value) || value.startsWith("blob:")) return value;
    if (/^[a-z][a-z0-9+.-]*:/i.test(value)) return "";
    if (window.location.protocol === "file:" && value.startsWith("/")) return `${LOCAL_API_ORIGIN}${value}`;
    return value;
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

function clearLegacyAuthStorage() {
    try {
        localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY);
        localStorage.removeItem(LEGACY_ADMIN_TOKEN_STORAGE_KEY);
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

function adminHeaders(extra = {}) {
    const headers = { Accept: "application/json", "X-Requested-With": "XMLHttpRequest", ...extra };
    const csrf = csrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
    return headers;
}

function apiRequestOptions(method = "GET", extra = {}) {
    const options = {
        method,
        credentials: "include",
        cache: "no-store",
        ...extra
    };
    options.headers = adminHeaders(extra.headers || {});
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
    const data = await response.clone().json().catch(() => ({}));
    const message = String(data.message || data.error || "");
    if (!message.includes("CSRF protection rejected")) return response;
    await refreshCsrfCookie();
    return execute();
}

function buildApiError(response, data = {}) {
    const error = new Error(data.message || data.error || `HTTP ${response.status}`);
    error.status = response.status;
    error.data = data;
    return error;
}

async function apiGet(path) {
    const response = await apiFetch(path, "GET");
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw buildApiError(response, data);
    }
    return response.json();
}

async function apiSend(method, path, payload = {}) {
    const response = await apiFetch(path, method, {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw buildApiError(response, data);
    }
    return response.json();
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

function showAdminLogin(message = "Admin sign-in required.") {
    adminSessionReady = false;
    document.body.classList.add("admin-auth-required");
    byId("adminLoginShell")?.classList.remove("is-hidden");
    setText("adminLoginStatus", message);
}

function hideAdminLogin() {
    adminSessionReady = true;
    document.body.classList.remove("admin-auth-required");
    byId("adminLoginShell")?.classList.add("is-hidden");
}

async function signInAdmin(event) {
    event?.preventDefault?.();
    const email = byId("adminLoginEmail")?.value.trim() || "";
    const password = byId("adminLoginPassword")?.value || "";
    const button = byId("adminLoginSubmit");
    if (!email || !password) {
        toast("Email and password are required");
        return;
    }
    if (button) {
        button.disabled = true;
        button.textContent = "Signing in...";
    }
    try {
        await apiSend("POST", "/api/auth/password-login", { email, password });
        hideAdminLogin();
        byId("adminLoginPassword").value = "";
        await loadAdminState();
        toast("Admin sign-in succeeded");
    } catch (error) {
        showAdminLogin(error.message || "Admin sign-in failed");
        toast(error.message || "Admin sign-in failed");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Sign in";
        }
    }
}

async function loadAdminState() {
    setText("adminDbStatus", "Reading SQLite database...");
    try {
        adminState = await apiGet("/api/admin/state");
        hideAdminLogin();
        hydrateStaticOptions();
        renderAll();
        setText("adminDbStatus", `${adminState.templates.length} templates / ${adminState.stats.images} images loaded`);
    } catch (error) {
        if (error.status === 401) {
            showAdminLogin("Admin sign-in required. Use your administrator email/password.");
        } else {
            hideAdminLogin();
        }
        adminState = createEmptyState();
        renderAll();
        setText("adminDbStatus", error.status === 401 ? "Admin sign-in required" : "Backend API unavailable");
        toast(error.message || "Admin API read failed. Start backend/server.py first.");
    }
}

async function refreshAdminState(message = "") {
    await loadAdminState();
    if (message) toast(message);
}

function bindNavigation() {
    document.querySelectorAll("[data-admin-view]").forEach(button => {
        button.addEventListener("click", () => switchView(button.dataset.adminView));
    });
    document.querySelectorAll("[data-jump-view]").forEach(button => {
        button.addEventListener("click", () => switchView(button.dataset.jumpView));
    });
}

function switchView(view) {
    document.querySelectorAll("[data-admin-view]").forEach(button => {
        const selected = button.dataset.adminView === view;
        button.classList.toggle("active", selected);
        button.setAttribute("aria-selected", selected ? "true" : "false");
    });
    document.querySelectorAll(".admin-view").forEach(section => {
        const selected = section.id === `view-${view}`;
        section.classList.toggle("active", selected);
        section.hidden = !selected;
        if (selected) {
            setText("adminPageTitle", section.dataset.title || "Admin");
        }
    });
}

function bindGlobalActions() {
    byId("adminLoginForm")?.addEventListener("submit", signInAdmin);
    byId("seedDemoData")?.addEventListener("click", async () => {
        toast("Demo data is stored in the database.");
        await refreshAdminState();
    });
    byId("exportAdminData")?.addEventListener("click", downloadAdminData);
    byId("downloadData")?.addEventListener("click", downloadAdminData);
    byId("importDataTrigger")?.addEventListener("click", () => toast("Use the admin API for imports in production."));
    byId("clearCompletedJobs")?.addEventListener("click", async () => {
        await apiSend("DELETE", "/api/admin/jobs/completed", await withAdminPassword({}, "clear completed jobs"));
        await refreshAdminState("Completed jobs cleaned from database");
    });
    byId("clearAdminStorage")?.addEventListener("click", () => {
        localStorage.removeItem("aiWorkshopAdminStateV2");
        toast("Local admin cache cleared; database remains authoritative.");
    });
}

function bindTemplateControls() {
    ["templateSearch", "templateCategoryFilter", "templateStatusFilter", "templateSort"].forEach(id => {
        byId(id)?.addEventListener("input", updateTemplateFilters);
        byId(id)?.addEventListener("change", updateTemplateFilters);
    });
    byId("templateSearchButton")?.addEventListener("click", updateTemplateFilters);
    byId("templateSearch")?.addEventListener("keydown", event => {
        if (event.key === "Enter") {
            event.preventDefault();
            updateTemplateFilters();
        }
    });
    byId("templatePrev")?.addEventListener("click", () => {
        templateState.page = Math.max(1, templateState.page - 1);
        renderTemplates();
    });
    byId("templateNext")?.addEventListener("click", () => {
        const total = getTemplateTotalPages();
        templateState.page = Math.min(total, templateState.page + 1);
        renderTemplates();
    });
    byId("syncRepoTemplates")?.addEventListener("click", syncGithubTemplates);
    byId("syncVideoTemplates")?.addEventListener("click", syncVideoTemplates);
    byId("openTemplateDrawer")?.addEventListener("click", () => openTemplateDrawer());
    byId("saveHomeTemplateLimitQuick")?.addEventListener("click", saveHomeTemplateLimitQuick);
    byId("saveHeroTemplatesQuick")?.addEventListener("click", saveHeroTemplatesQuick);
    byId("closeTemplateDrawer")?.addEventListener("click", closeTemplateDrawer);
    byId("templateDrawer")?.addEventListener("click", event => {
        if (event.target.id === "templateDrawer") closeTemplateDrawer();
    });
    byId("templateForm")?.addEventListener("submit", saveTemplateFromForm);
    byId("templateCover")?.addEventListener("input", () => {
        templateCoverUpload = null;
        setTemplateCoverPreview(byId("templateCover").value.trim());
    });
    bindTemplateCoverUpload();
    byId("deleteCustomTemplate")?.addEventListener("click", deleteTemplateFromDrawer);
}

async function syncGithubTemplates() {
    const button = byId("syncRepoTemplates");
    const oldText = button?.textContent;
    if (button) {
        button.disabled = true;
        button.textContent = "Syncing GitHub";
    }
    try {
        const result = await apiSend("POST", "/api/admin/sync-github", await withAdminPassword({}, "sync template repository"));
        adminState = result.state || adminState;
        hydrateStaticOptions();
        renderAll();
        const synced = result.syncedCount || result.count || 0;
        toast(`GitHub templates synced${synced ? `; processed ${synced}` : ""}`);
    } catch (error) {
        const detail = error?.data?.detail || error?.data?.stderr || error?.data?.output || error?.message || "Unknown error";
        console.error("sync-github failed:", error);
        toast(`Sync failed: ${detail}`, "error");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = oldText || "Sync GitHub templates";
        }
    }
}

async function syncVideoTemplates() {
    const button = byId("syncVideoTemplates");
    const oldText = button?.textContent;
    if (button) {
        button.disabled = true;
        button.textContent = "Syncing video templates";
    }
    try {
        const result = await apiSend("POST", "/api/admin/sync-video-templates", await withAdminPassword({}, "sync video templates"));
        adminState = result.state || adminState;
        renderAll();
        toast("Video templates synced to the database");
    } catch (error) {
        toast(`Sync failed: ${error.message}`, "error");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = oldText || "Sync video templates";
        }
    }
}

function bindTemplateCoverUpload() {
    const button = byId("templateCoverUpload");
    const input = byId("templateCoverFile");
    if (!button || !input) return;

    const openPicker = () => input.click();
    button.addEventListener("click", openPicker);
    button.addEventListener("dragover", event => {
        event.preventDefault();
        button.classList.add("dragover");
    });
    button.addEventListener("dragleave", () => button.classList.remove("dragover"));
    button.addEventListener("drop", event => {
        event.preventDefault();
        button.classList.remove("dragover");
        const file = event.dataTransfer.files?.[0];
        if (file) handleTemplateCoverFile(file);
    });
    input.addEventListener("change", event => {
        const file = event.target.files?.[0];
        if (file) handleTemplateCoverFile(file);
        input.value = "";
    });
}

function handleTemplateCoverFile(file) {
    if (!isAllowedUploadImageType(file.type)) {
        toast("璇蜂笂浼?JPG銆丳NG 鎴?WebP 鍥剧墖");
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        toast("妯℃澘閰嶅浘涓嶈兘瓒呰繃 10MB");
        return;
    }
    const reader = new FileReader();
    reader.onload = event => {
        templateCoverUpload = {
            name: file.name,
            mimeType: file.type || "image/jpeg",
            byteSize: file.size,
            dataUrl: event.target.result
        };
        byId("templateCover").value = "";
        setTemplateCoverPreview(templateCoverUpload.dataUrl, file.name);
        toast("妯℃澘閰嶅浘宸查€夋嫨锛屼繚瀛樻ā鏉垮悗鍏ュ簱");
    };
    reader.onerror = () => toast("妯℃澘閰嶅浘璇诲彇澶辫触");
    reader.readAsDataURL(file);
}

function setTemplateCoverPreview(url = "", label = "") {
    const preview = byId("templateCoverPreview");
    if (!preview) return;
    if (!url) {
        preview.innerHTML = `<span>No image selected</span>`;
        return;
    }
    const safeUrl = safeMediaUrl(url);
    preview.innerHTML = safeUrl
        ? `<img src="${escapeAttr(safeUrl)}" alt="${escapeAttr(label || "Template cover preview")}">`
        : `<span>Invalid image URL</span>`;
}

function updateTemplateFilters() {
    templateState.query = byId("templateSearch").value.trim().toLowerCase();
    templateState.category = byId("templateCategoryFilter").value;
    templateState.status = byId("templateStatusFilter").value;
    templateState.sort = byId("templateSort").value;
    templateState.page = 1;
    renderTemplates();
}

function bindJobControls() {
    ["jobStatusFilter", "jobModelFilter", "jobSearch"].forEach(id => {
        byId(id)?.addEventListener("input", renderJobs);
        byId(id)?.addEventListener("change", renderJobs);
    });
    byId("addGenerationJob")?.addEventListener("click", addGenerationJob);
    byId("retryFailedJobs")?.addEventListener("click", async () => {
        const data = await apiSend("POST", "/api/admin/jobs/retry-failed", await withAdminPassword({}, "retry failed jobs"));
        const skipped = data.skipped ? `; skipped ${data.skipped} due to insufficient credits` : "";
        await refreshAdminState(`Retried ${data.count || 0} failed jobs and charged ${data.charged || 0} credits${skipped}`);
    });
}

function bindModelControls() {
    byId("addModelRoute")?.addEventListener("click", async () => {
        await apiSend("POST", "/api/admin/models", await withAdminPassword({
            name: "Custom model route",
            routeCode: `custom-route-${Date.now()}`,
            modelName: "custom-image-model",
            quality: "medium",
            cost: 5,
            enabled: false
        }, "create model route"));
        await refreshAdminState("Model route created");
    });
    byId("apiSettingsForm")?.addEventListener("submit", event => {
        event.preventDefault();
        toast("API keys and gateway URLs are configured on the server; this page only shows status.");
    });
}

function bindUserControls() {
    byId("grantCredits")?.addEventListener("click", async () => {
        const first = adminState.users[0];
        if (!first) return;
        const reason = prompt("Enter a credit grant reason. It will be written to the audit log.", "Operations adjustment") || "";
        if (!reason.trim()) {
            toast("Credit grants require a reason.", "warning");
            return;
        }
        await apiSend("POST", "/api/admin/credits/grant", await withAdminPassword({ userId: first.id, amount: 100, reason: reason.trim() }, "grant user credits"));
        await refreshAdminState(`Granted 100 credits to ${first.name}`);
    });
}

function bindReviewControls() {
    byId("approveAllSafe")?.addEventListener("click", async () => {
        const data = await apiSend("POST", "/api/admin/reviews/approve-low-risk", await withAdminPassword({}, "bulk approve low-risk review items"));
        await refreshAdminState(`Approved ${data.count || 0} low-risk review items`);
    });
    byId("addReviewItem")?.addEventListener("click", async () => {
        const template = adminState.templates[0];
        await apiSend("POST", "/api/admin/reviews", await withAdminPassword({
            templateId: template?.id,
            risk: "medium",
            reason: "Admin-created review sample"
        }, "create review item"));
        await refreshAdminState("Review item added");
    });
}

function bindSettingsForms() {
    byId("siteSettingsForm")?.addEventListener("submit", async event => {
        event.preventDefault();
        const payload = {
            siteName: byId("siteName").value.trim() || "YCImage",
            homeTemplateLimit: Number(byId("homeTemplateLimit").value || 30),
            defaultModel: byId("defaultModel").value,
            defaultQuality: byId("defaultQuality").value,
            heroTemplateIds: [
                byId("heroTemplate1")?.value || "",
                byId("heroTemplate2")?.value || "",
                byId("heroTemplate3")?.value || ""
            ].filter(Boolean),
            enablePublicLibrary: byId("enablePublicLibrary").checked,
            requireReviewBeforeDownload: byId("requireReviewBeforeDownload").checked
        };
        await apiSend("PUT", "/api/admin/settings", await withAdminPassword(payload, "save site settings"));
        await refreshAdminState("Site settings saved to the database");
    });
    byId("adminPasswordForm")?.addEventListener("submit", saveAdminPasswordFromForm);
}

async function saveAdminPasswordFromForm(event) {
    event.preventDefault();
    const currentPassword = byId("adminCurrentPassword")?.value || "";
    const newPassword = byId("adminNewPassword")?.value || "";
    const confirmPassword = byId("adminConfirmPassword")?.value || "";
    if (newPassword !== confirmPassword) {
        toast("New passwords do not match", "error");
        return;
    }
    const button = event.submitter || byId("adminPasswordForm")?.querySelector("button[type='submit']");
    if (button) {
        button.disabled = true;
        button.textContent = "Updating...";
    }
    try {
        const data = await apiSend("POST", "/api/admin/password", {
            currentPassword,
            newPassword,
            confirmPassword
        });
        adminState = data.state || adminState;
        forgetAdminPassword();
        byId("adminPasswordForm")?.reset();
        renderSettings();
        toast(data.message || "Admin password updated", "success");
    } catch (error) {
        toast(error.message || "Admin password update failed", "error");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Update admin password";
        }
    }
}

function hydrateStaticOptions() {
    const categories = adminState.categories || [];
    fillSelect("templateCategoryFilter", [["all", "鍏ㄩ儴鍒嗙被"], ...categories.map(category => [category.value, category.label])]);
    fillSelect("templateCategory", categories.map(category => [category.value, category.label]));
    fillSelect("templateModelRoute", adminState.models.map(model => [model.id, model.name]));
    fillSelect("jobModelFilter", [["all", "鍏ㄩ儴妯″瀷"], ...adminState.models.map(model => [model.id, model.name])]);
    fillSelect("defaultModel", adminState.models.map(model => [model.id, model.name]));
}

function renderAll() {
    renderOverview();
    renderHomeTemplateSlots();
    renderTemplates();
    renderJobs();
    renderModels();
    renderApiSettings();
    renderUsers();
    renderReviews();
    renderSettings();
    renderSecuritySettings();
}

function renderOverview() {
    const templates = adminState.templates;
    const activeTemplates = templates.filter(template => template.enabled !== false);
    const jobs = adminState.jobs;
    const successJobs = jobs.filter(job => job.status === "success");
    const failedJobs = jobs.filter(job => job.status === "failed");
    const revenue = adminState.orders.filter(order => order.status === "paid").reduce((sum, order) => sum + Number(order.amount || 0), 0);
    const credits = adminState.users.reduce((sum, user) => sum + Number(user.credits || 0), 0);
    const reviewPending = adminState.reviewItems.filter(item => item.status === "pending").length;
    const featured = templates.filter(template => template.featured && template.enabled !== false).length;

    const metrics = [
        ["Templates", templates.length, `${activeTemplates.length} enabled`, ""],
        ["Homepage picks", featured, `Target ${adminState.settings.homeTemplateLimit || 30}`, featured >= 30 ? "" : "warning"],
        ["Images stored", adminState.stats.images || 0, "Read from SQLite blobs", ""],
        ["Generation jobs", jobs.length, `${successJobs.length} successful`, ""],
        ["Failed jobs", failedJobs.length, failedJobs.length ? "Needs attention" : "Stable", failedJobs.length ? "danger" : ""],
        ["Pending review", reviewPending, reviewPending ? "Needs manual review" : "Clear", reviewPending ? "warning" : ""],
        ["Revenue", `¥${revenue}`, `${credits} user credits remaining`, ""]
    ];

    byId("metricGrid").innerHTML = metrics.map(([label, value, note, tone]) => `
        <article class="metric-card ${tone || ""}">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
            <small>${escapeHtml(note)}</small>
        </article>
    `).join("");

    renderFunnel();
    renderRisks();
    renderTopTemplateRows();
    renderActivity();
}

function renderFunnel() {
    const jobs = adminState.jobs.length || 1;
    const success = adminState.jobs.filter(job => job.status === "success").length;
    const paid = adminState.orders.filter(order => order.status === "paid").length;
    const steps = [
        ["Template impressions", Math.max(12486, adminState.templates.length * 32), 100],
        ["Template detail visits", Math.max(3260, adminState.templates.length * 8), 26],
        ["Generation submissions", jobs, 12],
        ["Successful generations", success, Math.max(4, success / jobs * 12)],
        ["Paid orders", paid, 3]
    ];
    byId("funnelList").innerHTML = steps.map(([label, value, percent]) => `
        <div class="funnel-item">
            <span>${escapeHtml(label)}</span>
            <div class="funnel-bar"><span style="width:${Math.max(4, percent)}%"></span></div>
            <strong>${Number(value).toLocaleString("zh-CN")}</strong>
        </div>
    `).join("");
}

function renderRisks() {
    const failed = adminState.jobs.filter(job => job.status === "failed").length;
    const pending = adminState.reviewItems.filter(item => item.status === "pending").length;
    const lowCredits = adminState.users.filter(user => user.credits < 30).length;
    const featured = adminState.templates.filter(template => template.featured && template.enabled !== false).length;
    const risks = [
        ["Backend connection", adminState.templates.length ? "SQLite API healthy" : "API unavailable", adminState.templates.length ? "success" : "danger"],
        ["Homepage picks", `${featured} / ${adminState.settings.homeTemplateLimit || 30}`, featured >= 30 ? "success" : "warning"],
        ["Failed jobs", `${failed} jobs can be retried`, failed ? "warning" : "success"],
        ["Review backlog", `${pending} pending review items`, pending ? "warning" : "success"],
        ["Credit warning", `${lowCredits} users below 30 credits`, lowCredits ? "warning" : "success"]
    ];
    byId("riskList").innerHTML = risks.map(([title, detail, tone]) => `
        <div class="risk-item">
            <strong>${escapeHtml(title)} <span class="status-pill ${tone}">${toneLabel(tone)}</span></strong>
            <span>${escapeHtml(detail)}</span>
        </div>
    `).join("");
}

function renderTopTemplateRows() {
    const rows = getOperationalTemplates()
        .filter(template => template.enabled !== false)
        .sort((a, b) => (b.usageToday || 0) - (a.usageToday || 0))
        .slice(0, 8)
        .map(template => `
            <tr>
                <td>
                    <div class="row-title">
                        <img src="${escapeAttr(safeMediaUrl(template.cover || ""))}" alt="${escapeAttr(template.title)}">
                        <div>
                            <strong>${escapeHtml(template.title)}</strong>
                            <span>${escapeHtml(template.id)}</span>
                        </div>
                    </div>
                </td>
                <td>${escapeHtml(template.categoryLabel || getCategoryLabel(template.category))}</td>
                <td>${template.paramCount || 0}</td>
                <td>${template.usageToday || 0}</td>
                <td>${Number(template.conversionRate || 0).toFixed(1)}%</td>
            </tr>
        `).join("");
    byId("topTemplateRows").innerHTML = rows || `<tr><td colspan="5">鏆傛棤妯℃澘鏁版嵁</td></tr>`;
}

function renderActivity() {
    byId("activityList").innerHTML = adminState.activities.slice(0, 8).map(item => `
        <div class="timeline-item">
            <strong>${escapeHtml(item.title)}</strong>
            <span>${escapeHtml(item.detail)} 路 ${escapeHtml(formatTime(item.time))}</span>
        </div>
    `).join("") || `<div class="timeline-item"><strong>绛夊緟鍚庡彴鎿嶄綔</strong><span>鍚屾銆佷繚瀛樸€佸鏍哥瓑鍔ㄤ綔浼氬啓鍏ユ暟鎹簱瀹¤鏃ュ織銆?/span></div>`;
}

function renderTemplates() {
    const grid = byId("templateAdminGrid");
    if (!grid) return;

    const filtered = getFilteredTemplates();
    const totalPages = getTemplateTotalPages(filtered);
    templateState.page = Math.min(templateState.page, totalPages);
    const start = (templateState.page - 1) * TEMPLATE_PAGE_SIZE;
    const pageItems = filtered.slice(start, start + TEMPLATE_PAGE_SIZE);

    grid.innerHTML = pageItems.length ? pageItems.map(template => {
        const cover = safeMediaUrl(template.cover || "");
        const coverMarkup = cover
            ? `<img src="${escapeAttr(cover)}" alt="${escapeAttr(template.title)}">`
            : `<div class="template-admin-cover-placeholder"><strong>${escapeHtml((template.title || "Untitled template").slice(0, 20))}</strong><small>No cover</small></div>`;
        return `
        <article class="template-admin-card ${template.enabled === false ? "hidden-card" : ""}">
            <div class="template-admin-cover">
                ${coverMarkup}
            </div>
            <div class="template-admin-body">
                <div class="template-admin-meta">
                    <span>${escapeHtml(template.categoryLabel || getCategoryLabel(template.category))}</span>
                    <span>${template.paramCount || 0} params</span>
                </div>
                <h3>${escapeHtml(template.title)}</h3>
                <div class="template-admin-flags">
                    <span class="status-pill ${template.enabled === false ? "neutral" : "success"}">${template.enabled === false ? "Hidden" : "Enabled"}</span>
                    ${template.featured ? `<span class="status-pill warning">Homepage</span>` : ""}
                    ${template.source === "custom" ? `<span class="status-pill neutral">Manual</span>` : `<span class="status-pill neutral">GitHub</span>`}
                </div>
                <div class="template-admin-meta">
                    <span>${template.creditCost || 5} credits</span>
                    <span>${template.usageToday || 0} uses</span>
                </div>
                <div class="inline-actions" style="margin-top:10px">
                    <button type="button" data-action="edit-template" data-id="${escapeAttr(template.id)}">Edit</button>
                    <button type="button" data-action="toggle-template" data-id="${escapeAttr(template.id)}">${template.enabled === false ? "Enable" : "Hide"}</button>
                    <button type="button" data-action="feature-template" data-id="${escapeAttr(template.id)}">${template.featured ? "Remove homepage" : "Add homepage"}</button>
                    <button type="button" data-action="pin-template" data-id="${escapeAttr(template.id)}">Pin hot</button>
                    <button type="button" data-action="hero-slot-1" data-id="${escapeAttr(template.id)}">Hero 1</button>
                    <button type="button" data-action="hero-slot-2" data-id="${escapeAttr(template.id)}">Hero 2</button>
                    <button type="button" data-action="hero-slot-3" data-id="${escapeAttr(template.id)}">Hero 3</button>
                </div>
            </div>
        </article>
    `;
    }).join("") : `<div class="empty-admin">No matching templates</div>`;

    byId("templatePageInfo").textContent = `Page ${templateState.page} / ${totalPages}, ${filtered.length} total`;
    byId("templatePrev").disabled = templateState.page <= 1;
    byId("templateNext").disabled = templateState.page >= totalPages;

    grid.querySelectorAll("[data-action]").forEach(button => {
        button.addEventListener("click", () => handleTemplateAction(button.dataset.action, button.dataset.id));
    });
}

function getFeaturedTemplates() {
    return getOperationalTemplates()
        .filter(template => template.enabled !== false && template.featured)
        .sort((a, b) => (b.sortScore || 0) - (a.sortScore || 0) || (b.usageToday || 0) - (a.usageToday || 0));
}

function renderHomeTemplateSlots() {
    const slots = byId("homeTemplateSlots");
    if (!slots) return;
    const limit = Number(adminState.settings.homeTemplateLimit || 30);
    const featured = getFeaturedTemplates().slice(0, limit);
    const quickLimit = byId("homeTemplateLimitQuick");
    if (quickLimit) quickLimit.value = limit;

    if (!featured.length) {
        slots.innerHTML = `<div class="empty-admin">No homepage templates yet. Add one from a template card below.</div>`;
        return;
    }

    slots.innerHTML = featured.map((template, index) => {
        const cover = safeMediaUrl(template.cover || "");
        const coverMarkup = cover
            ? `<img src="${escapeAttr(cover)}" alt="${escapeAttr(template.title)}">`
            : `<div class="template-admin-cover-placeholder"><strong>${escapeHtml((template.title || "Untitled template").slice(0, 20))}</strong><small>No cover</small></div>`;
        return `
        <article class="home-template-slot">
            ${coverMarkup}
            <b>${index + 1}. ${escapeHtml(template.title)}</b>
            <small>${escapeHtml(template.categoryLabel || getCategoryLabel(template.category))} - ${Number(template.sortScore || 0).toFixed(0)} weight</small>
            <div class="inline-actions">
                <button type="button" data-hot-action="up" data-id="${escapeAttr(template.id)}" ${index === 0 ? "disabled" : ""}>Up</button>
                <button type="button" data-hot-action="down" data-id="${escapeAttr(template.id)}" ${index === featured.length - 1 ? "disabled" : ""}>Down</button>
                <button type="button" data-hot-action="remove" data-id="${escapeAttr(template.id)}">Remove</button>
            </div>
        </article>
    `;
    }).join("");

    slots.querySelectorAll("[data-hot-action]").forEach(button => {
        button.addEventListener("click", () => handleHotTemplateAction(button.dataset.hotAction, button.dataset.id));
    });
}

async function handleHotTemplateAction(action, id) {
    const list = getFeaturedTemplates();
    const index = list.findIndex(template => template.id === id);
    if (index < 0) return;

    if (action === "remove") {
        await apiSend("PATCH", `/api/admin/templates/${encodeURIComponent(id)}`, await withAdminPassword({ featured: false }, "remove homepage template"));
        await refreshAdminState("Removed from homepage templates");
        return;
    }

    const nextIndex = action === "up" ? index - 1 : index + 1;
    if (nextIndex < 0 || nextIndex >= list.length) return;
    const reordered = [...list];
    [reordered[index], reordered[nextIndex]] = [reordered[nextIndex], reordered[index]];
    await saveHomeTemplateOrder(reordered);
}

async function pinHomeTemplate(id) {
    const list = getFeaturedTemplates().filter(template => template.id !== id);
    const template = getOperationalTemplates().find(item => item.id === id);
    if (!template) return;
    await saveHomeTemplateOrder([{ ...template, featured: true }, ...list], true);
}

async function saveHomeTemplateOrder(ordered, forceFeatured = false) {
    const adminPasswordPayload = await withAdminPassword({}, "reorder homepage templates");
    const adminPassword = adminPasswordPayload.adminPassword;
    const jobs = ordered.map((template, index) => {
        const payload = { sortScore: 10000 - index * 10 };
        if (forceFeatured || !template.featured) payload.featured = true;
        if (adminPassword) payload.adminPassword = adminPassword;
        return apiSend("PATCH", `/api/admin/templates/${encodeURIComponent(template.id)}`, payload);
    });
    await Promise.all(jobs);
    await refreshAdminState("Homepage template order updated");
}

async function saveHomeTemplateLimitQuick() {
    const value = Math.max(3, Math.min(48, Number(byId("homeTemplateLimitQuick")?.value || 30)));
    const settings = adminState.settings || {};
    await apiSend("PUT", "/api/admin/settings", await withAdminPassword({
        siteName: settings.siteName || "YCImage",
        homeTemplateLimit: value,
        defaultModel: settings.defaultModel || DEFAULT_IMAGE_MODEL,
        defaultQuality: settings.defaultQuality || "medium",
        enablePublicLibrary: settings.enablePublicLibrary !== false,
        requireReviewBeforeDownload: Boolean(settings.requireReviewBeforeDownload)
    }, "update homepage template limit"));
    await refreshAdminState("Homepage template limit saved");
}

function getHeroTemplateIdsFromQuickPanel() {
    return [
        byId("heroTemplate1Quick")?.value || "",
        byId("heroTemplate2Quick")?.value || "",
        byId("heroTemplate3Quick")?.value || ""
    ];
}

async function saveHeroTemplatesQuick() {
    const settings = adminState.settings || {};
    await apiSend("PUT", "/api/admin/settings", await withAdminPassword({
        siteName: settings.siteName || "YCImage",
        homeTemplateLimit: Number(settings.homeTemplateLimit || 30),
        defaultModel: settings.defaultModel || DEFAULT_IMAGE_MODEL,
        defaultQuality: settings.defaultQuality || "medium",
        heroTemplateIds: getHeroTemplateIdsFromQuickPanel().filter(Boolean),
        enablePublicLibrary: settings.enablePublicLibrary !== false,
        requireReviewBeforeDownload: Boolean(settings.requireReviewBeforeDownload)
    }, "update hero templates"));
    await refreshAdminState("Hero templates saved");
    renderHeroTemplatePreview();
}

async function assignHeroTemplate(slotIndex, templateId) {
    const heroIds = adminState.settings.heroTemplateIds ? [...adminState.settings.heroTemplateIds] : [];
    while (heroIds.length < 3) heroIds.push("");
    heroIds[slotIndex] = templateId;
    const settings = adminState.settings || {};
    await apiSend("PUT", "/api/admin/settings", await withAdminPassword({
        siteName: settings.siteName || "YCImage",
        homeTemplateLimit: Number(settings.homeTemplateLimit || 30),
        defaultModel: settings.defaultModel || DEFAULT_IMAGE_MODEL,
        defaultQuality: settings.defaultQuality || "medium",
        heroTemplateIds: heroIds.filter(Boolean),
        enablePublicLibrary: settings.enablePublicLibrary !== false,
        requireReviewBeforeDownload: Boolean(settings.requireReviewBeforeDownload)
    }, "update hero template"));
    await refreshAdminState(`Hero template ${slotIndex + 1} updated`);
    renderHeroTemplatePreview();
}

function renderHeroTemplatePreview() {
    const target = byId("heroTemplatePreview");
    if (!target) return;
    const heroIds = adminState.settings?.heroTemplateIds || [];
    const lines = heroIds.slice(0, 3).map((id, index) => {
        const template = getOperationalTemplates().find(item => item.id === id);
        return `<span><strong>Hero ${index + 1}:</strong> ${escapeHtml(template?.title || "Not set")}</span>`;
    });
    target.innerHTML = lines.length ? lines.join("<br>") : "<span>No hero templates configured</span>";
}

function getFilteredTemplates() {
    const q = templateState.query;
    return getOperationalTemplates()
        .filter(template => {
            const categoryMatch = templateState.category === "all" || template.category === templateState.category || template.categoryLabel === templateState.category;
            const statusMatch = templateMatchesStatus(template, templateState.status);
            const haystack = [
                template.title,
                template.category,
                template.categoryLabel,
                template.description,
                ...(template.tags || [])
            ].join(" ").toLowerCase();
            return categoryMatch && statusMatch && (!q || haystack.includes(q));
        })
        .sort((a, b) => sortTemplates(a, b, templateState.sort));
}

function templateMatchesStatus(template, status) {
    if (status === "all") return true;
    if (status === "enabled") return template.enabled !== false;
    if (status === "featured") return !!template.featured;
    if (status === "hidden") return template.enabled === false;
    if (status === "missingParams") return !template.paramCount;
    return true;
}

function sortTemplates(a, b, sort) {
    if (sort === "updated") return dateValue(b.createdAt || b.updatedAt) - dateValue(a.createdAt || a.updatedAt);
    if (sort === "usage") return (b.usageToday || 0) - (a.usageToday || 0);
    if (sort === "params") return (b.paramCount || 0) - (a.paramCount || 0);
    if (sort === "title") return a.title.localeCompare(b.title, "zh-CN");
    return Number(b.featured) - Number(a.featured) || (b.sortScore || 0) - (a.sortScore || 0);
}

function dateValue(value) {
    const time = new Date(value || 0).getTime();
    return Number.isNaN(time) ? 0 : time;
}

function getTemplateTotalPages(items = getFilteredTemplates()) {
    return Math.max(1, Math.ceil(items.length / TEMPLATE_PAGE_SIZE));
}

async function handleTemplateAction(action, id) {
    const template = getOperationalTemplates().find(item => item.id === id);
    if (!template) return;
    if (action === "edit-template") {
        openTemplateDrawer(id);
        return;
    }
    if (action === "toggle-template") {
        await apiSend("PATCH", `/api/admin/templates/${encodeURIComponent(id)}`, await withAdminPassword({ enabled: template.enabled === false }, "change template visibility"));
        await refreshAdminState(template.enabled === false ? "Template enabled" : "Template hidden");
        return;
    }
    if (action === "feature-template") {
        await apiSend("PATCH", `/api/admin/templates/${encodeURIComponent(id)}`, await withAdminPassword({ featured: !template.featured }, "change homepage recommendation"));
        await refreshAdminState(template.featured ? "Removed from homepage recommendations" : "Added to homepage recommendations");
        return;
    }
    if (action === "pin-template") {
        await pinHomeTemplate(id);
        return;
    }
    if (action === "hero-slot-1") {
        await assignHeroTemplate(0, id);
        return;
    }
    if (action === "hero-slot-2") {
        await assignHeroTemplate(1, id);
        return;
    }
    if (action === "hero-slot-3") {
        await assignHeroTemplate(2, id);
    }
}

function openTemplateDrawer(id = "") {
    const template = id ? getOperationalTemplates().find(item => item.id === id) : null;
    templateCoverUpload = null;
    byId("drawerTitle").textContent = template ? "缂栬緫妯℃澘" : "鏂板缓妯℃澘";
    byId("templateId").value = template?.id || "";
    byId("templateTitle").value = template?.title || "";
    byId("templateCategory").value = template?.category || adminState.categories[0]?.value || "";
    byId("templateEnabled").value = template?.enabled === false ? "hidden" : "enabled";
    byId("templateFeatured").value = template?.featured ? "true" : "false";
    byId("templateCreditCost").value = template?.creditCost || 5;
    byId("templateModelRoute").value = template?.modelRoute || adminState.settings.defaultModel;
    byId("templateCover").value = template?.coverUrl || template?.cover || "";
    setTemplateCoverPreview(template?.cover || template?.coverUrl || "");
    byId("templateParams").value = template?.params?.map(param => param.label || param.key).join(", ") || "";
    byId("templatePrompt").value = template?.promptTemplate || template?.description || "";
    byId("deleteCustomTemplate").style.visibility = template?.source === "custom" ? "visible" : "hidden";
    byId("templateDrawer").classList.add("active");
    byId("templateDrawer").setAttribute("aria-hidden", "false");
    activateDialog(byId("templateDrawer"), closeTemplateDrawer, "#templateTitle");
}

function closeTemplateDrawer() {
    templateCoverUpload = null;
    byId("templateDrawer").classList.remove("active");
    byId("templateDrawer").setAttribute("aria-hidden", "true");
    deactivateDialog(byId("templateDrawer"));
}

async function saveTemplateFromForm(event) {
    event.preventDefault();
    const params = byId("templateParams").value.split(",").map(item => item.trim()).filter(Boolean);
    const coverValue = templateCoverUpload?.dataUrl || byId("templateCover").value.trim();
    if (!coverValue) {
        toast("Upload a template cover or enter a valid cover URL first.", "error");
        byId("templateCoverUpload")?.focus();
        return;
    }
    const payload = {
        id: byId("templateId").value || undefined,
        title: byId("templateTitle").value.trim(),
        category: byId("templateCategory").value,
        cover: coverValue,
        promptTemplate: byId("templatePrompt").value.trim(),
        params,
        status: byId("templateEnabled").value,
        featured: byId("templateFeatured").value === "true",
        creditCost: Number(byId("templateCreditCost").value || 5),
        modelRoute: byId("templateModelRoute").value
    };
    const method = payload.id ? "PATCH" : "POST";
    const path = payload.id ? `/api/admin/templates/${encodeURIComponent(payload.id)}` : "/api/admin/templates";
    await apiSend(method, path, await withAdminPassword(payload, "save template settings"));
    closeTemplateDrawer();
    await refreshAdminState("Template saved to the database");
}

async function deleteTemplateFromDrawer() {
    const id = byId("templateId").value;
    if (!id) return;
    await apiSend("DELETE", `/api/admin/templates/${encodeURIComponent(id)}`, await withAdminPassword({}, "delete or archive template"));
    closeTemplateDrawer();
    await refreshAdminState("Template deleted or archived");
}

function renderJobs() {
    const status = byId("jobStatusFilter")?.value || "all";
    const model = byId("jobModelFilter")?.value || "all";
    const query = byId("jobSearch")?.value?.trim().toLowerCase() || "";
    const modelMap = Object.fromEntries(adminState.models.map(item => [item.id, item.name]));
    const rows = adminState.jobs
        .filter(job => status === "all" || job.status === status)
        .filter(job => model === "all" || job.model === model)
        .filter(job => !query || [job.id, job.jobNo, job.user, job.templateTitle].join(" ").toLowerCase().includes(query))
        .map(job => `
            <tr>
                <td><strong>${escapeHtml(job.jobNo || job.id)}</strong><br><span style="color:#778197">${escapeHtml(formatTime(job.createdAt))}</span></td>
                <td>${escapeHtml(job.user)}</td>
                <td>${escapeHtml(job.templateTitle)}<br><span style="color:#778197">${escapeHtml(modelMap[job.model] || job.model)}</span></td>
                <td>${renderStatus(job.status)}${job.error ? `<br><span style="color:#b42318">${escapeHtml(job.error)}</span>` : ""}</td>
                <td>${escapeHtml(job.latency)}</td>
                <td>${job.cost} 绉垎</td>
                <td>
                    <div class="inline-actions">
                        <button type="button" data-job-action="success" data-id="${escapeAttr(job.id)}">鏍囪鎴愬姛</button>
                        <button type="button" data-job-action="review" data-id="${escapeAttr(job.id)}">閫佸</button>
                        <button type="button" data-job-action="failed" data-id="${escapeAttr(job.id)}">澶辫触</button>
                    </div>
                </td>
            </tr>
        `).join("");
    byId("jobRows").innerHTML = rows || `<tr><td colspan="7">鏆傛棤浠诲姟</td></tr>`;
    byId("jobRows").querySelectorAll("[data-job-action]").forEach(button => {
        button.addEventListener("click", () => updateJobStatus(button.dataset.id, button.dataset.jobAction));
    });
}

async function addGenerationJob() {
    const template = getOperationalTemplates()[0];
    await apiSend("POST", "/api/admin/jobs", await withAdminPassword({
        templateId: template?.id,
        model: adminState.settings.defaultModel,
        cost: template?.creditCost || 5
    }, "create admin generation job"));
    await refreshAdminState("Admin queued generation job created");
}

async function updateJobStatus(id, status) {
    const data = await apiSend("PATCH", `/api/admin/jobs/${encodeURIComponent(id)}`, await withAdminPassword({ status }, "change generation job status"));
    if (status === "failed" && data.refund?.amount) {
        await refreshAdminState(`Job marked failed; refunded ${data.refund.amount} credits`);
        return;
    }
    if (data.charge?.amount) {
        await refreshAdminState(`Job status saved; charged ${data.charge.amount} credits`);
        return;
    }
    await refreshAdminState("Job status saved to the database");
}

function bindModelControls() {
    byId("addModelRoute")?.addEventListener("click", () => openModelRouteDrawer());
    byId("closeModelRouteDrawer")?.addEventListener("click", closeModelRouteDrawer);
    byId("modelRouteModality")?.addEventListener("change", toggleVideoRouteFields);
    byId("modelRouteDrawer")?.addEventListener("click", event => {
        if (event.target.id === "modelRouteDrawer") closeModelRouteDrawer();
    });
    byId("modelRouteForm")?.addEventListener("submit", saveModelRouteFromForm);
    byId("deleteModelRoute")?.addEventListener("click", deleteModelRouteFromDrawer);
    byId("apiSettingsForm")?.addEventListener("submit", saveApiSettingsFromForm);
}

function renderModels() {
    byId("modelRouteList").innerHTML = adminState.models.map(model => `
        <article class="model-route">
            <div class="route-main">
                <strong>${escapeHtml(model.name)} ${model.enabled ? renderStatus("enabled") : renderStatus("hidden")}</strong>
                <span>${escapeHtml(model.provider)} 路 ${escapeHtml(model.scenario)} 路 ${escapeHtml(model.size)}</span>
            </div>
            <div class="route-metrics">
                <span>${model.cost} 绉垎/寮?/span>
                <span>鎴愬姛鐜?${model.successRate}%</span>
                <span>${escapeHtml(model.latency)}</span>
                <button type="button" data-model-toggle="${escapeAttr(model.id)}">${model.enabled ? "鍋滅敤" : "鍚敤"}</button>
            </div>
        </article>
    `).join("");
    byId("modelRouteList").querySelectorAll("[data-model-toggle]").forEach(button => {
        button.addEventListener("click", async () => {
            const model = adminState.models.find(item => item.id === button.dataset.modelToggle);
            if (!model) return;
            await apiSend("PATCH", `/api/admin/models/${encodeURIComponent(model.id)}`, { enabled: !model.enabled });
            await refreshAdminState("妯″瀷璺敱鐘舵€佸凡鏇存柊");
        });
    });
    byId("apiEndpointSetting").value = adminState.api.endpoint;
    byId("apiBalanceEndpoint").value = adminState.api.balanceEndpoint;
    byId("serverKeyStatus").value = adminState.api.serverKeyStatus;
    byId("retryLimit").value = adminState.api.retryLimit;
}

function renderUsers() {
    byId("userRows").innerHTML = adminState.users.map(user => `
        <tr>
            <td><strong>${escapeHtml(user.name)}</strong><br><span style="color:#778197">${escapeHtml(user.id)}</span></td>
            <td>${escapeHtml(user.role)}</td>
            <td>${user.credits}</td>
            <td>${user.monthlyJobs}</td>
            <td>${escapeHtml(user.lastActive)}<br><span style="color:#778197">${escapeHtml(user.risk)}</span></td>
            <td>
                <div class="inline-actions">
                    <button type="button" data-credit-user="${escapeAttr(user.id)}">+50 credits</button>
                    <button type="button" data-vip-user="${escapeAttr(user.id)}">Set monthly</button>
                </div>
            </td>
        </tr>
    `).join("");
    byId("userRows").querySelectorAll("[data-credit-user]").forEach(button => {
        button.addEventListener("click", async () => {
            const reason = prompt("Enter a credit grant reason. It will be written to the audit log.", "Support adjustment") || "";
            if (!reason.trim()) {
                toast("Credit grants require a reason.", "warning");
                return;
            }
            await apiSend("POST", "/api/admin/credits/grant", await withAdminPassword({ userId: button.dataset.creditUser, amount: 50, reason: reason.trim() }, "grant user credits"));
            await refreshAdminState("Credits written to ledger");
        });
    });
    byId("userRows").querySelectorAll("[data-vip-user]").forEach(button => {
        button.addEventListener("click", async () => {
            await apiSend("PATCH", `/api/admin/users/${encodeURIComponent(button.dataset.vipUser)}`, await withAdminPassword({ membershipLevel: "monthly" }, "change user membership level"));
            await refreshAdminState("Membership level updated");
        });
    });

    byId("orderList").innerHTML = adminState.orders.map(order => `
        <article class="order-item">
            <strong>${escapeHtml(order.user)} 路 楼${order.amount} ${renderStatus(order.status)}</strong>
            <span>${escapeHtml(order.plan)} 路 ${escapeHtml(order.channel)} 路 ${escapeHtml(formatTime(order.time))} 路 ${escapeHtml(order.id)}</span>
        </article>
    `).join("") || `<article class="order-item"><strong>鏆傛棤璁㈠崟</strong><span>璁㈠崟浼氫粠鏁版嵁搴?orders 琛ㄨ鍙栥€?/span></article>`;
}

function renderReviews() {
    byId("reviewGrid").innerHTML = adminState.reviewItems.map(item => `
        <article class="review-card">
            <img src="${escapeAttr(safeMediaUrl(item.image || ""))}" alt="${escapeAttr(item.title)}">
            <div class="review-card-body">
                <span class="status-pill ${riskClass(item.risk)}">${riskLabel(item.risk)}</span>
                ${renderStatus(item.status)}
                <h3>${escapeHtml(item.title)}</h3>
                <p>${escapeHtml(item.user)} 路 ${escapeHtml(item.reason)}</p>
                <div class="inline-actions">
                    <button type="button" data-review-action="approved" data-id="${escapeAttr(item.id)}">閫氳繃</button>
                    <button type="button" data-review-action="rejected" data-id="${escapeAttr(item.id)}">鎷掔粷</button>
                    <button type="button" data-review-action="manual" data-id="${escapeAttr(item.id)}">浜哄伐澶勭悊</button>
                </div>
            </div>
        </article>
    `).join("") || `<div class="empty-admin">鏆傛棤瀹℃牳鍐呭</div>`;
    byId("reviewGrid").querySelectorAll("[data-review-action]").forEach(button => {
        button.addEventListener("click", () => updateReviewStatus(button.dataset.id, button.dataset.reviewAction));
    });
}

async function updateReviewStatus(id, status) {
    await apiSend("PATCH", `/api/admin/reviews/${encodeURIComponent(id)}`, { status });
    await refreshAdminState("瀹℃牳鐘舵€佸凡鏇存柊");
}

function renderSettings() {
    byId("siteName").value = adminState.settings.siteName;
    byId("homeTemplateLimit").value = adminState.settings.homeTemplateLimit;
    if (byId("homeTemplateLimitQuick")) byId("homeTemplateLimitQuick").value = adminState.settings.homeTemplateLimit;
    byId("defaultModel").value = adminState.settings.defaultModel;
    byId("defaultQuality").value = adminState.settings.defaultQuality;
    byId("enablePublicLibrary").checked = adminState.settings.enablePublicLibrary;
    byId("requireReviewBeforeDownload").checked = adminState.settings.requireReviewBeforeDownload;
}

function getOperationalTemplates() {
    return adminState.templates || [];
}

function downloadAdminData() {
    const payload = JSON.stringify(adminState, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ai-workshop-admin-db-snapshot-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast("Current database snapshot exported");
}

function renderStatus(status) {
    const [label, tone] = STATUS_LABELS[status] || [status, "neutral"];
    return `<span class="status-pill ${tone}">${escapeHtml(label)}</span>`;
}

function toneLabel(tone) {
    if (tone === "success") return "OK";
    if (tone === "warning") return "Attention";
    if (tone === "danger") return "Risk";
    return "Info";
}

function riskClass(risk) {
    return risk === "low" ? "success" : risk === "medium" ? "warning" : "danger";
}

function riskLabel(risk) {
    return risk === "low" ? "Low" : risk === "medium" ? "Medium" : risk === "critical" ? "Critical" : "High";
}

function getCategoryLabel(category) {
    return CATEGORY_LABELS[category] || category || "Uncategorized";
}

function fillSelect(id, options) {
    const select = byId(id);
    if (!select) return;
    const previous = select.value;
    select.innerHTML = options.map(([value, label]) => `<option value="${escapeAttr(value)}">${escapeHtml(label)}</option>`).join("");
    if (options.some(([value]) => value === previous)) select.value = previous;
}

function formatTime(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function setText(id, text) {
    const el = byId(id);
    if (el) el.textContent = text;
}

function byId(id) {
    return document.getElementById(id);
}

function toast(message) {
    const container = byId("adminToast");
    if (!container) return;
    const item = document.createElement("div");
    item.className = "admin-toast-item";
    item.setAttribute("role", "status");
    item.textContent = message;
    container.appendChild(item);
    setTimeout(() => item.remove(), 3200);
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function escapeAttr(value) {
    return escapeHtml(value).replace(/'/g, "&#39;");
}

let adminPasswordCache = { value: "", expiresAt: 0 };

function forgetAdminPassword() {
    adminPasswordCache = { value: "", expiresAt: 0 };
}

async function withAdminPassword(payload = {}, reason = "sensitive admin action") {
    const nowTs = Date.now();
    let password = adminPasswordCache.expiresAt > nowTs ? adminPasswordCache.value : "";
    if (!password) {
        password = window.prompt(`璇疯緭鍏ョ鐞嗗憳褰撳墠瀵嗙爜浠ョ‘璁わ細${reason}`) || "";
        if (!password.trim()) {
            throw new Error("绠＄悊鍛樺瘑鐮佺‘璁ゅ凡鍙栨秷");
        }
        adminPasswordCache = { value: password, expiresAt: nowTs + 5 * 60 * 1000 };
    }
    return { ...payload, adminPassword: password };
}

function bindModelControls() {
    byId("addModelRoute")?.addEventListener("click", () => openModelRouteDrawer());
    byId("closeModelRouteDrawer")?.addEventListener("click", closeModelRouteDrawer);
    byId("modelRouteModality")?.addEventListener("change", toggleVideoRouteFields);
    byId("modelRouteDrawer")?.addEventListener("click", event => {
        if (event.target.id === "modelRouteDrawer") closeModelRouteDrawer();
    });
    byId("modelRouteForm")?.addEventListener("submit", saveModelRouteFromForm);
    byId("deleteModelRoute")?.addEventListener("click", deleteModelRouteFromDrawer);
    byId("apiSettingsForm")?.addEventListener("submit", event => {
        event.preventDefault();
        toast("API keys and gateway URLs are configured on the server; this page only shows status.");
    });
}

function renderModels() {
    const list = byId("modelRouteList");
    if (!list) return;
    list.innerHTML = adminState.models.map(model => `
        <article class="model-route">
            <div class="route-main">
                <strong>${escapeHtml(model.name)} ${model.enabled ? renderStatus("enabled") : renderStatus("hidden")}</strong>
                <span>${escapeHtml(model.provider)} 路 ${escapeHtml(model.scenario)} 路 ${escapeHtml(model.size)}</span>
            </div>
            <div class="route-metrics">
                <span>${model.cost} 绉垎/寮?/span>
                <span>鎴愬姛鐜?${model.successRate}%</span>
                <span>${escapeHtml(model.latency)}</span>
                <div class="inline-actions">
                    <button type="button" data-model-action="edit" data-id="${escapeAttr(model.id)}">缂栬緫</button>
                    <button type="button" data-model-action="toggle" data-id="${escapeAttr(model.id)}">${model.enabled ? "鍋滅敤" : "鍚敤"}</button>
                    <button type="button" data-model-action="delete" data-id="${escapeAttr(model.id)}">鍒犻櫎</button>
                </div>
            </div>
        </article>
    `).join("");
    list.querySelectorAll("[data-model-action]").forEach(button => {
        button.addEventListener("click", () => handleModelRouteAction(button.dataset.modelAction, button.dataset.id));
    });
}

function renderApiSettings() {
    const api = adminState.api || {};
    if (byId("apiEndpointSetting")) byId("apiEndpointSetting").value = api.endpoint || "/api/generate-image";
    if (byId("apiBalanceEndpoint")) byId("apiBalanceEndpoint").value = api.balanceEndpoint || "/api/admin/model-balance";
    if (byId("apimartBaseUrl")) byId("apimartBaseUrl").value = api.apimartBaseUrl || "https://api.apimart.ai";
    if (byId("apimartApiKey")) byId("apimartApiKey").value = "";
    if (byId("clearApimartApiKey")) byId("clearApimartApiKey").checked = false;
    if (byId("serverKeyStatus")) {
        const status = api.serverKeyStatus || (api.apimartKeyConfigured ? "configured" : "not_configured");
        byId("serverKeyStatus").value = [...byId("serverKeyStatus").options].some(option => option.value === status) ? status : "configured";
    }
    if (byId("retryLimit")) byId("retryLimit").value = api.retryLimit ?? 2;
    renderApiConnectionStatus(api.connectionTest, api);
}

function renderApiConnectionStatus(test = {}, api = {}) {
    const panel = byId("apiConnectionPanel");
    if (!panel) return;
    const title = byId("apiConnectionTitle");
    const meta = byId("apiConnectionMeta");
    const detail = byId("apiConnectionDetail");
    const configured = Boolean(api.apimartKeyConfigured);
    const sourceLabel = {
        environment: "Environment",
        database: "Database",
        form: "Form key",
        missing: "Not configured"
    }[test.keySource || api.keySource] || "Unknown source";
    panel.classList.toggle("success", Boolean(test.ok));
    panel.classList.toggle("danger", test.ok === false || (!configured && !test.checkedAt));
    if (title) title.textContent = test.checkedAt ? (test.ok ? "Connection healthy" : "Connection failed") : (configured ? "Configured, not tested" : "API key not configured");
    if (meta) {
        const hasLatency = test.latencyMs !== null && test.latencyMs !== undefined && test.latencyMs !== "" && Number.isFinite(Number(test.latencyMs));
        const latency = hasLatency ? ` - ${test.latencyMs}ms` : "";
        meta.textContent = `${sourceLabel}${latency}${test.checkedAt ? ` - ${formatTime(test.checkedAt)}` : ""}`;
    }
    if (detail) {
        const balance = test.balance ? `Balance: ${test.balance}. ` : "";
        const endpoint = test.endpoint ? `Endpoint: ${test.endpoint}. ` : "";
        detail.textContent = test.checkedAt
            ? `${balance}${endpoint}${test.message || ""}`
            : (configured ? "Run a connection test to verify the active server-side APIMart key." : "Save an APIMart API key or set APIMART_API_KEY on the server.");
    }
}

function getModelRouteById(id = "") {
    return adminState.models.find(item => item.id === id || item.dbId === id) || null;
}

function openModelRouteDrawer(id = "") {
    const model = getModelRouteById(id);
    modelRouteState.editingId = model?.id || "";
    setText("modelDrawerTitle", model ? "缂栬緫璺敱" : "鏂板璺敱");
    byId("modelRouteId").value = model?.id || "";
    byId("modelRouteName").value = model?.name || "";
    byId("modelRouteCode").value = model?.id || `custom-route-${Date.now()}`;
    byId("modelRouteProvider").value = model?.providerId || "provider_openai_compatible";
    byId("modelRouteModelName").value = model?.modelName || "";
    byId("modelRouteModality").value = model?.modality || "image";
    byId("modelRouteQuality").value = model?.quality || "high";
    byId("modelRouteSizes").value = (model?.sizes || ["1024x1024"]).join(", ");
    byId("modelRouteRatios").value = (model?.ratios || ["1:1"]).join(", ");
    byId("modelRouteDefaultSize").value = model?.defaultSize || "1024x1024";
    byId("modelRouteDefaultRatio").value = model?.defaultRatio || "1:1";
    byId("modelRouteCost").value = model?.cost ?? 5;
    byId("modelRoutePriority").value = model?.priority ?? 50;
    byId("modelRouteRetryLimit").value = model?.retryLimit ?? 2;
    byId("modelRouteTimeout").value = model?.timeoutSeconds ?? 90;
    byId("modelRouteSuccessRate").value = model?.successRate ?? 0;
    byId("modelRouteLatencyMs").value = parseLatencyMs(model?.latency);
    byId("modelRouteEnabled").checked = Boolean(model?.enabled);
    byId("modelRouteDurations").value = (model?.supportedDurations || []).join(", ");
    byId("deleteModelRoute").style.visibility = model ? "visible" : "hidden";
    byId("modelRouteDrawer").classList.add("active");
    byId("modelRouteDrawer").setAttribute("aria-hidden", "false");
    activateDialog(byId("modelRouteDrawer"), closeModelRouteDrawer, "#modelRouteName");
    toggleVideoRouteFields();
}

function closeModelRouteDrawer() {
    modelRouteState.editingId = "";
    byId("modelRouteDrawer").classList.remove("active");
    byId("modelRouteDrawer").setAttribute("aria-hidden", "true");
    deactivateDialog(byId("modelRouteDrawer"));
}

function toggleVideoRouteFields() {
    const isVideo = byId("modelRouteModality")?.value === "video";
    byId("modelRouteDurationsWrap")?.classList.toggle("is-hidden", !isVideo);
}

function parseCsvField(value = "") {
    return String(value).split(",").map(item => item.trim()).filter(Boolean);
}

function parseLatencyMs(value = "") {
    if (!value || value === "-") return 0;
    const text = String(value).trim().toLowerCase();
    if (text.endsWith("ms")) return Number(text.replace("ms", "").trim()) || 0;
    if (text.endsWith("s")) return Math.round((Number(text.replace("s", "").trim()) || 0) * 1000);
    return Number(text) || 0;
}

async function saveModelRouteFromForm(event) {
    event.preventDefault();
    const id = byId("modelRouteId").value.trim();
    const payload = {
        routeCode: byId("modelRouteCode").value.trim(),
        name: byId("modelRouteName").value.trim(),
        providerId: byId("modelRouteProvider").value,
        modelName: byId("modelRouteModelName").value.trim(),
        modality: byId("modelRouteModality").value,
        quality: byId("modelRouteQuality").value,
        sizes: parseCsvField(byId("modelRouteSizes").value),
        ratios: parseCsvField(byId("modelRouteRatios").value),
        defaultSize: byId("modelRouteDefaultSize").value.trim(),
        defaultRatio: byId("modelRouteDefaultRatio").value.trim(),
        cost: Number(byId("modelRouteCost").value || 5),
        priority: Number(byId("modelRoutePriority").value || 50),
        retryLimit: Number(byId("modelRouteRetryLimit").value || 2),
        timeoutSeconds: Number(byId("modelRouteTimeout").value || 90),
        successRate: Number(byId("modelRouteSuccessRate").value || 0),
        avgLatencyMs: Number(byId("modelRouteLatencyMs").value || 0),
        enabled: byId("modelRouteEnabled").checked,
        supportedDurations: parseCsvField(byId("modelRouteDurations").value).map(value => Number(value)).filter(Number.isFinite)
    };
    const method = id ? "PATCH" : "POST";
    const path = id ? `/api/admin/models/${encodeURIComponent(id)}` : "/api/admin/models";
    await apiSend(method, path, await withAdminPassword(payload, "save model route"));
    closeModelRouteDrawer();
    await refreshAdminState(id ? "Model route updated" : "Model route created");
}

async function deleteModelRouteFromDrawer() {
    const id = byId("modelRouteId").value.trim();
    if (!id) return;
    const model = getModelRouteById(id);
    const ok = window.confirm(`Delete model route "${model?.name || id}"?`);
    if (!ok) return;
    await apiSend("DELETE", `/api/admin/models/${encodeURIComponent(id)}`, await withAdminPassword({}, "delete model route"));
    closeModelRouteDrawer();
    await refreshAdminState("Model route deleted or disabled");
}

async function handleModelRouteAction(action, id) {
    const model = getModelRouteById(id);
    if (!model) return;
    if (action === "edit") {
        openModelRouteDrawer(id);
        return;
    }
    if (action === "toggle") {
        await apiSend("PATCH", `/api/admin/models/${encodeURIComponent(model.id)}`, await withAdminPassword({ enabled: !model.enabled }, "toggle model route"));
        await refreshAdminState("Model route status updated");
        return;
    }
    if (action === "delete") {
        const ok = window.confirm(`Delete model route "${model.name}"?`);
        if (!ok) return;
        await apiSend("DELETE", `/api/admin/models/${encodeURIComponent(model.id)}`, await withAdminPassword({}, "delete model route"));
        await refreshAdminState("Model route deleted or disabled");
    }
}

function hydrateStaticOptions() {
    const categories = adminState.categories || [];
    const templateOptions = [["", "Not set"], ...getOperationalTemplates().map(template => [template.id, template.title])];
    fillSelect("templateCategoryFilter", [["all", "All categories"], ...categories.map(category => [category.value, category.label])]);
    fillSelect("templateCategory", categories.map(category => [category.value, category.label]));
    fillSelect("templateModelRoute", adminState.models.map(model => [model.id, model.name]));
    fillSelect("jobModelFilter", [["all", "All models"], ...adminState.models.map(model => [model.id, model.name])]);
    fillSelect("defaultModel", adminState.models.map(model => [model.id, model.name]));
    fillSelect("heroTemplate1", templateOptions);
    fillSelect("heroTemplate2", templateOptions);
    fillSelect("heroTemplate3", templateOptions);
    fillSelect("heroTemplate1Quick", templateOptions);
    fillSelect("heroTemplate2Quick", templateOptions);
    fillSelect("heroTemplate3Quick", templateOptions);
}

function renderSettings() {
    byId("siteName").value = adminState.settings.siteName;
    byId("homeTemplateLimit").value = adminState.settings.homeTemplateLimit;
    if (byId("homeTemplateLimitQuick")) byId("homeTemplateLimitQuick").value = adminState.settings.homeTemplateLimit;
    byId("defaultModel").value = adminState.settings.defaultModel;
    byId("defaultQuality").value = adminState.settings.defaultQuality;
    byId("enablePublicLibrary").checked = adminState.settings.enablePublicLibrary;
    byId("requireReviewBeforeDownload").checked = adminState.settings.requireReviewBeforeDownload;
    const heroIds = adminState.settings.heroTemplateIds || [];
    byId("heroTemplate1").value = heroIds[0] || "";
    byId("heroTemplate2").value = heroIds[1] || "";
    byId("heroTemplate3").value = heroIds[2] || "";
    if (byId("heroTemplate1Quick")) byId("heroTemplate1Quick").value = heroIds[0] || "";
    if (byId("heroTemplate2Quick")) byId("heroTemplate2Quick").value = heroIds[1] || "";
    if (byId("heroTemplate3Quick")) byId("heroTemplate3Quick").value = heroIds[2] || "";
    renderHeroTemplatePreview();
}

function renderSecuritySettings() {
    const security = adminState.security || {};
    const email = security.adminEmail || "admin@example.com";
    const configuredText = security.adminPasswordConfigured ? "password configured" : "password not configured";
    setText("adminSecurityStatus", `Admin account: ${email}; ${configuredText}. Changes are written to SQLite immediately.`);
}

async function saveApiSettingsFromForm(event) {
    event.preventDefault();
    const payload = {
        providerId: "provider_apimart",
        apiEndpoint: byId("apiEndpointSetting")?.value.trim() || "/api/generate-image",
        balanceEndpoint: byId("apiBalanceEndpoint")?.value.trim() || "/api/admin/model-balance",
        baseUrl: byId("apimartBaseUrl")?.value.trim() || "",
        apiKey: byId("apimartApiKey")?.value.trim() || "",
        clearApiKey: Boolean(byId("clearApimartApiKey")?.checked)
    };
    await apiSend("PUT", "/api/admin/api-settings", await withAdminPassword(payload, "update API key or gateway settings"));
    await refreshAdminState("API connection settings saved to the database");
}

async function testApiConnectionFromForm() {
    const button = byId("testApiConnection");
    const payload = {
        baseUrl: byId("apimartBaseUrl")?.value.trim() || "",
        apiKey: byId("apimartApiKey")?.value.trim() || ""
    };
    if (button) {
        button.disabled = true;
        button.textContent = "Testing...";
    }
    try {
        const data = await apiSend("POST", "/api/admin/api-settings/test", await withAdminPassword(payload, "test API connection"));
        adminState = data.state || adminState;
        renderAll();
        const test = data.test || {};
        toast(test.ok ? `Connection healthy in ${test.latencyMs}ms` : `Connection failed: ${test.message}`, test.ok ? "success" : "error");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Test connection";
        }
    }
}

function bindModelControls() {
    byId("addModelRoute")?.addEventListener("click", () => openModelRouteDrawer());
    byId("closeModelRouteDrawer")?.addEventListener("click", closeModelRouteDrawer);
    byId("modelRouteModality")?.addEventListener("change", toggleVideoRouteFields);
    byId("modelRouteDrawer")?.addEventListener("click", event => {
        if (event.target.id === "modelRouteDrawer") closeModelRouteDrawer();
    });
    byId("modelRouteForm")?.addEventListener("submit", saveModelRouteFromForm);
    byId("deleteModelRoute")?.addEventListener("click", deleteModelRouteFromDrawer);
    byId("apiSettingsForm")?.addEventListener("submit", saveApiSettingsFromForm);
    byId("testApiConnection")?.addEventListener("click", testApiConnectionFromForm);
}
