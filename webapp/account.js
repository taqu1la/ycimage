const LEGACY_AUTH_STORAGE_KEY = "ycimage_auth_session";
const LOCAL_API_ORIGIN = "http://127.0.0.1:4178";

let accountState = null;

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
    const fileName = window.location.pathname.split("/").pop() || "account.html";
    const target = servicePageUrl(fileName, window.location.hash);
    if (window.location.href === target) return false;
    window.location.replace(target);
    return true;
}

document.addEventListener("DOMContentLoaded", () => {
    if (redirectToServicePageIfNeeded()) return;
    clearLegacySessionStorage();
    bindNavigation();
    bindActions();
    loadDashboard();
});

function apiUrl(path) {
    if (!path) return "";
    const value = String(path).trim();
    if (/^https?:\/\//i.test(value) || isSafeDataImageUrl(value) || value.startsWith("blob:")) return value;
    if (/^[a-z][a-z0-9+.-]*:/i.test(value)) return "";
    if (shouldUseLocalApiFallback(value)) return `${LOCAL_API_ORIGIN}${value}`;
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

function cssUrl(value) {
    const url = safeMediaUrl(value);
    return url ? `url("${String(url).replace(/["\\\n\r\f]/g, "")}")` : "";
}

function safeLinkUrl(path) {
    const url = apiUrl(path);
    if (!url) return "";
    if (/^https?:\/\//i.test(url) || url.startsWith("/") || url.startsWith("./") || url.startsWith("../") || url.startsWith("#")) return url;
    return "";
}

function clearLegacySessionStorage() {
    try {
        localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY);
    } catch {
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

function authHeaders(extra = {}) {
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
    options.headers = authHeaders(extra.headers || {});
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

async function apiGet(path) {
    const response = await apiFetch(path, "GET");
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const error = new Error(data.message || data.error || `HTTP ${response.status}`);
        error.status = response.status;
        throw error;
    }
    return response.json();
}

async function apiPost(path, payload = {}) {
    const response = await apiFetch(path, "POST", {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const error = new Error(data.message || data.error || `HTTP ${response.status}`);
        error.status = response.status;
        throw error;
    }
    return response.json();
}

async function apiPatch(path, payload = {}) {
    const response = await apiFetch(path, "PATCH", {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const error = new Error(data.message || data.error || `HTTP ${response.status}`);
        error.status = response.status;
        throw error;
    }
    return response.json();
}

async function apiDelete(path) {
    const response = await apiFetch(path, "DELETE");
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const error = new Error(data.message || data.error || `HTTP ${response.status}`);
        error.status = response.status;
        throw error;
    }
    return response.json();
}

function bindNavigation() {
    document.querySelectorAll("[data-account-view]").forEach(button => {
        button.addEventListener("click", () => setView(button.dataset.accountView));
    });
    document.querySelectorAll("[data-jump-view]").forEach(button => {
        button.addEventListener("click", () => setView(button.dataset.jumpView));
    });
}

function bindActions() {
    document.getElementById("copyAccountInvite")?.addEventListener("click", copyInvite);
    document.getElementById("copyInviteLarge")?.addEventListener("click", copyInvite);
    document.getElementById("accountLogout")?.addEventListener("click", logout);
    document.getElementById("securityLogout")?.addEventListener("click", logout);
    document.getElementById("buyCreditsButton")?.addEventListener("click", () => {
        window.location.href = servicePageUrl("index.html", "#pricing");
    });
    document.getElementById("viewPricingButton")?.addEventListener("click", () => {
        window.location.href = servicePageUrl("index.html", "#pricing");
    });
    document.getElementById("passwordForm")?.addEventListener("submit", changePassword);
    document.getElementById("workHistory")?.addEventListener("click", handleWorkHistoryClick);
    document.getElementById("customTemplateList")?.addEventListener("click", handleCustomTemplateClick);
    document.getElementById("customTemplateForm")?.addEventListener("submit", saveCustomTemplateEdit);
    document.getElementById("createCustomTemplateButton")?.addEventListener("click", beginCreateCustomTemplate);
    document.getElementById("cancelCustomTemplateEdit")?.addEventListener("click", cancelCustomTemplateEdit);
    document.getElementById("cancelCustomTemplateEditFooter")?.addEventListener("click", cancelCustomTemplateEdit);
}

function setView(name) {
    const view = name || "overview";
    document.querySelectorAll("[data-account-view]").forEach(button => {
        const selected = button.dataset.accountView === view;
        button.classList.toggle("active", selected);
        button.setAttribute("aria-selected", selected ? "true" : "false");
    });
    document.querySelectorAll(".account-view").forEach(section => {
        const selected = section.id === `view-${view}`;
        section.classList.toggle("active", selected);
        section.hidden = !selected;
    });
}

async function loadDashboard() {
    try {
        accountState = await apiGet("/api/account/dashboard");
        renderDashboard();
    } catch (error) {
        renderLoggedOut(error.message);
    }
}

function renderLoggedOut(message = "") {
    document.getElementById("loginRequired").hidden = false;
    document.getElementById("accountContent").hidden = true;
    setText("accountUserName", "未登录");
    setText("accountUserMeta", message || "返回首页完成登录后再查看个人中心");
    setText("accountGreeting", "请先登录 YCImage");
    setText("accountIntro", "登录后可以管理积分、作品、订单和邀请码。");
}

function renderDashboard() {
    const user = accountState.user || {};
    const stats = accountState.stats || {};
    const invite = accountState.invite || {};
    const passwordConfigured = Boolean(user.passwordConfigured);

    document.getElementById("loginRequired").hidden = true;
    document.getElementById("accountContent").hidden = false;

    setText("accountUserName", user.displayName || user.mobile || user.email || "YCImage 用户");
    setText("accountUserMeta", [maskMobile(user.mobile), user.email].filter(Boolean).join(" · ") || "邮箱登录用户");
    setText("accountAvatar", initials(user.displayName || user.email || user.mobile));
    setText("accountGreeting", `${user.displayName || "你好"}，这里是你的创作资产`);
    setText("accountIntro", `当前可用 ${stats.credits || 0} 积分，邀请码 ${invite.code || "--"}.`);

    setText("metricCredits", stats.credits ?? 0);
    setText("metricWorks", stats.works ?? 0);
    setText("metricFavorites", stats.customTemplates ?? stats.favorites ?? 0);
    setText("metricMembership", membershipLabel(stats.membership || user.membershipLevel));

    setText("inviteCodeBig", invite.code || "--");
    setText("inviteRule", `已邀请 ${invite.count || 0} 人，好友注册成功后你可获得 ${invite.rewardCredits || 100} 积分。`);
    setText("securityMobile", user.mobile ? maskMobile(user.mobile) : "未绑定");
    setText("securityEmail", user.email || "未绑定");
    setText("securityWechat", user.wechatOpenId ? "已绑定" : "未绑定");
    setText(
        "passwordSecurityHint",
        passwordConfigured
            ? "当前账号已设置登录密码，修改时需要先验证旧密码。"
            : "当前账号还没有设置登录密码，可以直接创建新密码。"
    );
    setText(
        "passwordHint",
        passwordConfigured
            ? "请输入当前密码、新密码和确认密码。"
            : "首次设置密码时，当前密码可以留空。"
    );

    const currentPassword = document.getElementById("currentPassword");
    const passwordAccountEmail = document.getElementById("passwordAccountEmail");
    if (passwordAccountEmail) {
        passwordAccountEmail.value = user.email || user.mobile || "";
    }
    if (currentPassword) {
        currentPassword.placeholder = passwordConfigured ? "请输入当前密码" : "没有旧密码可留空";
    }

    renderJobs(accountState.jobs || []);
    renderCustomTemplates(accountState.customTemplates || [], accountState.limits || {});
    renderLedger(accountState.ledger || []);
    renderOrders(accountState.orders || []);
    renderInvites(accountState.invites || []);
}

function renderJobs(jobs) {
    const recent = document.getElementById("recentJobs");
    const full = document.getElementById("workHistory");
    recent.innerHTML = jobs.slice(0, 5).map(renderCompactJob).join("") || emptyState("还没有生成作品，先去模板库开始创作。");
    full.innerHTML = jobs.map(renderWorkRow).join("") || emptyState("暂无作品记录。生成图片或视频后会自动出现在这里。");
}

function renderCompactJob(job) {
    const resultLabel = job.modality === "video" ? "视频" : "图片";
    return `
        <div class="list-row">
            <div class="list-row-top">
                <strong>${escapeHtml(job.templateTitle || "自定义 Prompt")}</strong>
                ${statusPill(job.status)}
            </div>
            <small>${escapeHtml(job.jobNo || job.id)} · ${formatTime(job.createdAt)} · ${resultLabel} · ${Number(job.creditCost || 0)} 积分</small>
        </div>
    `;
}

function renderWorkRow(job) {
    const previewUrl = getJobPreviewUrl(job);
    const resultCount = getJobResultUrls(job).length;
    const canOpen = Boolean(getJobResultUrl(job));
    const thumbStyle = previewUrl ? `style="background-image:${cssUrl(previewUrl)}"` : "";
    const summary = job.status === "success" && !canOpen
        ? "结果链接已失效或仍在整理中，可重新生成一版。"
        : truncateText(job.prompt || job.modelName || job.model || "生成任务", 72);
    return `
        <article class="work-row">
            <div class="work-thumb" ${thumbStyle}></div>
            <div class="work-meta">
                <strong>${escapeHtml(job.templateTitle || "自定义 Prompt")}</strong>
                <p>${escapeHtml(summary)}</p>
                <small>${escapeHtml(job.jobNo || job.id)} · ${formatTime(job.createdAt)} · ${job.modality === "video" ? "视频" : "图片"}</small>
            </div>
            <div class="work-side">
                <div class="work-status">
                    ${statusPill(job.status)}
                    <small>${Number(job.creditCost || 0)} 积分${resultCount > 1 ? ` · ${resultCount} 张` : ""}</small>
                </div>
                <div class="work-actions">
                    <button class="btn btn-secondary" type="button" data-job-action="open" data-job-id="${escapeAttr(job.id)}" ${canOpen ? "" : "disabled"}>打开结果</button>
                    <button class="btn btn-primary" type="button" data-job-action="download" data-job-id="${escapeAttr(job.id)}" ${canOpen ? "" : "disabled"}>下载原图</button>
                </div>
            </div>
        </article>
    `;
}

function renderLedger(items) {
    const recent = document.getElementById("recentLedger");
    const full = document.getElementById("ledgerTable");
    recent.innerHTML = items.slice(0, 5).map(renderLedgerRow).join("") || emptyState("暂无积分流水。");
    full.innerHTML = items.map(renderLedgerRow).join("") || emptyState("暂无积分流水。注册、购买、生成和退款都会记录在这里。");
}

function renderLedgerRow(item) {
    const positive = ["credit", "refund", "unfreeze"].includes(item.direction);
    return `
        <div class="ledger-row">
            <div>
                <strong>${escapeHtml(item.reasonLabel || item.reason)}</strong>
                <small>${formatTime(item.createdAt)} · 余额 ${Number(item.balanceAfter || 0)}</small>
            </div>
            <span class="amount-pill ${positive ? "amount-credit" : "amount-debit"}">${positive ? "+" : "-"}${Number(item.amount || 0)}</span>
        </div>
    `;
}

function renderOrders(items) {
    const target = document.getElementById("orderList");
    target.innerHTML = items.map(order => `
        <article class="order-row">
            <div>
                <strong>${escapeHtml(order.plan || "自定义订单")}</strong>
                <small>${escapeHtml(order.id)} · ${formatTime(order.createdAt)} · ${escapeHtml(order.channel || "支付渠道")}</small>
            </div>
            <div>
                ${statusPill(order.status)}
                <strong>¥${Number(order.amount || 0).toFixed(2)}</strong>
            </div>
        </article>
    `).join("") || emptyState("暂无订单。购买会员或积分包后会显示在这里。");
}

function renderInvites(items) {
    const target = document.getElementById("inviteList");
    target.innerHTML = items.map(item => `
        <div class="list-row">
            <div class="list-row-top">
                <strong>${escapeHtml(item.invitedUser || "新用户")}</strong>
                <span class="amount-pill amount-credit">+${Number(item.rewardAmount || 0)}</span>
            </div>
            <small>${escapeHtml(item.inviteCode)} · ${formatTime(item.createdAt)}</small>
        </div>
    `).join("") || emptyState("还没有邀请记录。复制邀请码发给好友，注册成功后奖励会自动到账。");
}

function renderCustomTemplates(items, limits = {}) {
    const target = document.getElementById("customTemplateList");
    if (!target) return;
    const limit = Number(limits.customTemplates || 10);
    setText("customTemplateCountHint", `${items.length} / ${limit} 个模板`);
    target.innerHTML = items.map(renderCustomTemplateRow).join("") || emptyState("还没有保存模板。先去图像工作台生成一张图，再把常用 Prompt 保存成模板。");
}

function renderCustomTemplateRow(template) {
    const cover = safeMediaUrl(template.cover || template.image || "");
    const thumbStyle = cover ? `style="background-image:${cssUrl(cover)}"` : "";
    const prompt = String(template.promptTemplate || template.prompt || "").trim();
    const useTemplateHref = servicePageUrl("index.html", `#template-editor:${encodeURIComponent(template.id)}`);
    const defaults = [
        template.defaultQuality || "",
        template.defaultAspectRatio || "",
        template.defaultSize || ""
    ].filter(Boolean).join(" · ");
    return `
        <article class="work-row" data-template-id="${escapeAttr(template.id)}">
            <div class="work-thumb" ${thumbStyle}></div>
            <div class="work-meta">
                <strong>${escapeHtml(template.title || "我的模板")}</strong>
                <p>${escapeHtml(template.description || truncateText(prompt, 80) || "自定义模板")}</p>
                <small>${escapeHtml(template.id)}${defaults ? ` · ${escapeHtml(defaults)}` : ""}</small>
            </div>
            <div class="work-side">
                <div class="work-status">
                    <small>${escapeHtml(truncateText(prompt, 56) || "可直接在生成器里继续使用")}</small>
                </div>
                <div class="work-actions">
                    <a class="btn btn-secondary" href="${escapeAttr(useTemplateHref)}">使用模板</a>
                    <button class="btn btn-secondary" type="button" data-template-action="edit" data-template-id="${escapeAttr(template.id)}">编辑</button>
                    <button class="btn btn-primary" type="button" data-template-action="delete" data-template-id="${escapeAttr(template.id)}">删除</button>
                </div>
            </div>
        </article>
    `;
}

function statusPill(status) {
    const map = {
        queued: ["排队中", "status-running"],
        running: ["生成中", "status-running"],
        success: ["已完成", "status-success"],
        paid: ["已支付", "status-success"],
        manual: ["人工处理", "status-running"],
        failed: ["失败", "status-failed"],
        cancelled: ["已取消", "status-failed"],
        refunded: ["已退款", "status-failed"],
        pending: ["待支付", "status-running"],
        review: ["审核中", "status-running"]
    };
    const item = map[status] || [status || "未知", ""];
    return `<span class="status-pill ${item[1]}">${escapeHtml(item[0])}</span>`;
}

function membershipLabel(value) {
    const map = {
        free: "免费体验",
        monthly: "月卡",
        creator: "创作版",
        studio: "工作室版",
        enterprise: "企业版",
        credit_pack: "积分包用户"
    };
    return map[value] || value || "免费体验";
}

async function copyInvite() {
    const code = accountState?.invite?.code;
    if (!code) {
        showToast("暂无邀请码", "error");
        return;
    }
    try {
        await navigator.clipboard.writeText(code);
        showToast("邀请码已复制");
    } catch {
        window.prompt("复制邀请码", code);
        showToast(`邀请码：${code}`);
    }
}

async function logout() {
    try {
        await apiPost("/api/auth/logout", {});
    } catch {
        // keep local logout available
    }
    clearLegacySessionStorage();
    accountState = { authenticated: false };
    renderLoggedOut();
    showToast("已退出登录");
    setTimeout(() => {
        window.location.href = servicePageUrl("index.html");
    }, 180);
}

async function changePassword(event) {
    event.preventDefault();
    const submit = document.getElementById("passwordSubmitButton");
    const currentPassword = document.getElementById("currentPassword")?.value || "";
    const newPassword = document.getElementById("newPassword")?.value || "";
    const confirmPassword = document.getElementById("confirmPassword")?.value || "";

    if (!newPassword || !confirmPassword) {
        showToast("请填写新密码和确认密码", "error");
        return;
    }

    if (submit) {
        submit.disabled = true;
        submit.textContent = "保存中";
    }
    try {
        const data = await apiPost("/api/account/password", {
            currentPassword,
            newPassword,
            confirmPassword
        });
        if (accountState?.user) {
            accountState.user.passwordConfigured = true;
        }
        setText("passwordHint", "密码已更新，下次登录请使用新密码。");
        document.getElementById("currentPassword").value = "";
        document.getElementById("newPassword").value = "";
        document.getElementById("confirmPassword").value = "";
        renderDashboard();
        showToast(data.message || "密码已更新");
    } catch (error) {
        showToast(error.message || "修改密码失败", "error");
    } finally {
        if (submit) {
            submit.disabled = false;
            submit.textContent = "更新密码";
        }
    }
}

function handleWorkHistoryClick(event) {
    const button = event.target.closest("[data-job-action][data-job-id]");
    if (!button) return;
    const job = (accountState?.jobs || []).find(item => item.id === button.dataset.jobId);
    if (!job) return;
    const action = button.dataset.jobAction;
    if (action === "open") {
        openJobResult(job);
        return;
    }
    if (action === "download") {
        downloadJobResult(job, button);
    }
}

function handleCustomTemplateClick(event) {
    const button = event.target.closest("[data-template-action][data-template-id]");
    if (!button) return;
    const template = (accountState?.customTemplates || []).find(item => item.id === button.dataset.templateId);
    if (!template) return;
    const action = button.dataset.templateAction;
    if (action === "edit") {
        beginCustomTemplateEdit(template);
        return;
    }
    if (action === "delete") {
        deleteCustomTemplate(template, button);
    }
}

function getJobResultUrls(job = {}) {
    const urls = [];
    if (job.modality === "video") {
        if (job.videoUrl) urls.push(job.videoUrl);
        if (job.thumbnailUrl && job.thumbnailUrl !== job.videoUrl) urls.push(job.thumbnailUrl);
        return urls;
    }
    if (Array.isArray(job.imageUrls)) {
        urls.push(...job.imageUrls.filter(Boolean));
    }
    if (job.imageUrl) urls.unshift(job.imageUrl);
    return [...new Set(urls)];
}

function getJobResultUrl(job = {}) {
    return getJobResultUrls(job)[0] || "";
}

function getJobPreviewUrl(job = {}) {
    return (
        job.thumbnailUrl ||
        job.imageUrl ||
        (Array.isArray(job.imageUrls) ? job.imageUrls[0] : "") ||
        job.cover ||
        job.videoUrl ||
        ""
    );
}

function getJobFileExtension(url = "", mime = "") {
    const mimeMap = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/webp": "webp",
        "image/gif": "gif",
        "video/mp4": "mp4",
        "video/webm": "webm"
    };
    if (mimeMap[mime]) return mimeMap[mime];
    const cleanUrl = String(url || "").split("?")[0].split("#")[0];
    const match = cleanUrl.match(/\.([a-z0-9]{2,5})$/i);
    return match ? match[1].toLowerCase() : "png";
}

function getJobFileName(job = {}, url = "", mime = "") {
    const title = job.templateTitle || job.modelName || job.prompt || "生成结果";
    const safeTitle = String(title).replace(/[\\/:*?"<>|]+/g, "-").replace(/\s+/g, " ").trim() || "生成结果";
    return `${safeTitle}.${getJobFileExtension(url, mime)}`;
}

function canFetchResultForDownload(url) {
    if (/^(data|blob):/i.test(String(url || ""))) return true;
    try {
        const parsed = new URL(url, window.location.href);
        return parsed.origin === window.location.origin;
    } catch {
        return false;
    }
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

function openJobResult(job) {
    const url = getJobResultUrl(job);
    if (!url) {
        showToast("生成完成后才能打开结果", "error");
        return;
    }
    const safeUrl = safeLinkUrl(url);
    if (!safeUrl) {
        showToast("结果链接不可用", "error");
        return;
    }
    openUrlInNewTab(safeUrl);
    showToast("结果已在新窗口打开");
}

async function downloadJobResult(job, button) {
    const url = getJobResultUrl(job);
    if (!url) {
        showToast("生成完成后可下载", "error");
        return;
    }
    const resolvedUrl = safeLinkUrl(url);
    if (!resolvedUrl) {
        showToast("结果链接不可用", "error");
        return;
    }
    if (!canFetchResultForDownload(resolvedUrl)) {
        openJobResult(job);
        return;
    }

    const originalText = button?.textContent || "下载原图";
    if (button) {
        button.disabled = true;
        button.textContent = "准备下载";
    }
    try {
        const response = await fetch(resolvedUrl, { credentials: "include", cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        triggerBrowserDownload(blobUrl, getJobFileName(job, resolvedUrl, blob.type));
        setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);
        showToast("已开始下载结果");
    } catch {
        openJobResult(job);
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

function beginCustomTemplateEdit(template) {
    if (!template) return;
    setView("templates");
    const panel = document.getElementById("customTemplateEditorPanel");
    if (panel) panel.hidden = false;
    setText("customTemplateEditorEyebrow", "模板编辑");
    setText("customTemplateEditorTitle", "修改模板内容");
    setText("saveCustomTemplateButton", "保存修改");
    const title = document.getElementById("customTemplateTitle");
    const description = document.getElementById("customTemplateDescription");
    const prompt = document.getElementById("customTemplatePrompt");
    const id = document.getElementById("customTemplateId");
    if (id) id.value = template.id || "";
    if (title) title.value = template.title || "";
    if (description) description.value = template.description || "";
    if (prompt) prompt.value = template.promptTemplate || template.prompt || "";
    panel?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function beginCreateCustomTemplate() {
    setView("templates");
    const panel = document.getElementById("customTemplateEditorPanel");
    if (panel) panel.hidden = false;
    document.getElementById("customTemplateForm")?.reset();
    setText("customTemplateEditorEyebrow", "手动新建");
    setText("customTemplateEditorTitle", "直接新增一个常用模板");
    setText("saveCustomTemplateButton", "保存模板");
    const id = document.getElementById("customTemplateId");
    if (id) id.value = "";
    const prompt = document.getElementById("customTemplatePrompt");
    prompt?.focus();
    panel?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function cancelCustomTemplateEdit() {
    const panel = document.getElementById("customTemplateEditorPanel");
    if (panel) panel.hidden = true;
    document.getElementById("customTemplateForm")?.reset();
    const id = document.getElementById("customTemplateId");
    if (id) id.value = "";
    setText("customTemplateEditorEyebrow", "模板编辑");
    setText("customTemplateEditorTitle", "修改模板内容");
    setText("saveCustomTemplateButton", "保存修改");
}

async function saveCustomTemplateEdit(event) {
    event.preventDefault();
    const templateId = document.getElementById("customTemplateId")?.value || "";
    const title = document.getElementById("customTemplateTitle")?.value?.trim() || "";
    const description = document.getElementById("customTemplateDescription")?.value?.trim() || "";
    const prompt = document.getElementById("customTemplatePrompt")?.value?.trim() || "";
    if (!prompt) {
        showToast("Prompt 不能为空", "error");
        return;
    }
    const button = document.getElementById("saveCustomTemplateButton");
    const originalText = button?.textContent || "保存修改";
    if (button) {
        button.disabled = true;
        button.textContent = templateId ? "保存中" : "创建中";
    }
    try {
        const payload = {
            title,
            description,
            prompt
        };
        const data = templateId
            ? await apiPatch(`/api/account/custom-templates/${encodeURIComponent(templateId)}`, payload)
            : await apiPost("/api/account/custom-templates", payload);
        const item = data.item || {};
        const list = Array.isArray(accountState?.customTemplates) ? [...accountState.customTemplates] : [];
        const index = list.findIndex(template => template.id === item.id);
        if (index >= 0) {
            list[index] = { ...list[index], ...item };
        } else {
            list.unshift(item);
        }
        const nextLimits = {
            ...(accountState?.limits || {}),
            customTemplates: Number(data.limit ?? item.limit ?? accountState?.limits?.customTemplates ?? 10)
        };
        accountState = {
            ...(accountState || {}),
            customTemplates: list,
            limits: nextLimits
        };
        if (accountState?.stats) {
            accountState.stats.customTemplates = list.length;
            setText("metricFavorites", accountState.stats.customTemplates);
        }
        renderCustomTemplates(list, nextLimits);
        cancelCustomTemplateEdit();
        showToast(data.message || (templateId ? "模板已更新" : "模板已保存"));
    } catch (error) {
        showToast(error.message || (templateId ? "模板更新失败" : "模板创建失败"), "error");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

async function deleteCustomTemplate(template, button) {
    if (!template?.id) return;
    if (!window.confirm(`确定删除模板「${template.title || "未命名模板"}」吗？`)) return;
    const originalText = button?.textContent || "删除";
    if (button) {
        button.disabled = true;
        button.textContent = "删除中";
    }
    try {
        const data = await apiDelete(`/api/account/custom-templates/${encodeURIComponent(template.id)}`);
        const list = (accountState?.customTemplates || []).filter(item => item.id !== template.id);
        accountState = {
            ...(accountState || {}),
            customTemplates: list,
            limits: {
                ...(accountState?.limits || {}),
                customTemplates: data.limit || accountState?.limits?.customTemplates || 10
            }
        };
        if (accountState?.stats) {
            accountState.stats.customTemplates = Number(data.count ?? list.length);
            setText("metricFavorites", accountState.stats.customTemplates);
        }
        if (document.getElementById("customTemplateId")?.value === template.id) {
            cancelCustomTemplateEdit();
        }
        renderCustomTemplates(list, accountState?.limits || {});
        showToast(data.message || "模板已删除");
    } catch (error) {
        showToast(error.message || "模板删除失败", "error");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value ?? "";
}

function initials(value) {
    const text = String(value || "YC").trim();
    if (!text) return "YC";
    if (/[\u4e00-\u9fa5]/.test(text)) return text.slice(0, 2);
    return text.slice(0, 2).toUpperCase();
}

function maskMobile(value) {
    const raw = String(value || "");
    return raw.length === 11 ? `${raw.slice(0, 3)}****${raw.slice(7)}` : raw;
}

function formatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function truncateText(value, maxLength) {
    const text = String(value || "").trim();
    if (!text) return "";
    if (text.length <= maxLength) return text;
    return `${text.slice(0, Math.max(0, maxLength - 1))}…`;
}

function emptyState(text) {
    return `<div class="empty-state">${escapeHtml(text)}</div>`;
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

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;"
    }[char]));
}

function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, "&#96;");
}
