const state = {
    page: 1,
    pageSize: 12,
    category: "all",
    type: "all",
    query: "",
    total: 0,
    totalPages: 1,
    items: [],
    requestToken: 0
};

const LOCAL_API_ORIGIN = "http://127.0.0.1:4178";

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
    const fileName = window.location.pathname.split("/").pop() || "templates.html";
    const search = window.location.search || "";
    const hash = window.location.hash || "";
    const target = `${servicePageUrl(fileName)}${search}${hash}`;
    if (window.location.href === target) return false;
    window.location.replace(target);
    return true;
}

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

document.addEventListener("DOMContentLoaded", () => {
    if (redirectToServicePageIfNeeded()) return;
    initLibrary();
});

function scrollLibraryToTop() {
    const target = document.querySelector(".template-library-page") || document.getElementById("libraryGrid");
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function initLibraryTypeFromUrl() {
    const type = new URLSearchParams(window.location.search).get("type");
    state.type = type === "video" || type === "image" ? type : "all";
}

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

async function apiGet(path) {
    const response = await fetch(apiUrl(path), {
        credentials: "include",
        cache: "no-store",
        headers: { Accept: "application/json" }
    });
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const error = new Error(data.message || data.error || `HTTP ${response.status}`);
        error.status = response.status;
        throw error;
    }
    return response.json();
}

async function initLibrary() {
    initLibraryTypeFromUrl();
    const categorySelect = document.getElementById("libraryCategory");
    try {
        const categories = await apiGet("/api/categories");
        categorySelect.innerHTML = `<option value="all">全部分类</option>${(categories.items || []).map(category => `<option value="${escapeHtml(category.value)}">${escapeHtml(category.label)} (${category.count})</option>`).join("")}`;
    } catch (error) {
        document.getElementById("libraryGrid").innerHTML = `<div class="empty-admin">后端 API 未连接，无法读取数据库模板。</div>`;
        return;
    }

    document.getElementById("librarySearch")?.addEventListener("input", event => {
        state.query = event.target.value.trim();
        state.page = 1;
        renderLibrary();
    });

    categorySelect?.addEventListener("change", event => {
        state.category = event.target.value;
        state.page = 1;
        renderLibrary();
    });

    document.getElementById("libraryPageSize")?.addEventListener("change", event => {
        state.pageSize = Number(event.target.value || 12);
        state.page = 1;
        renderLibrary();
    });

    document.getElementById("libraryPrev")?.addEventListener("click", () => {
        state.page = Math.max(1, state.page - 1);
        renderLibrary();
        scrollLibraryToTop();
    });

    document.getElementById("libraryNext")?.addEventListener("click", () => {
        const totalPages = getTotalPages();
        state.page = Math.min(totalPages, state.page + 1);
        renderLibrary();
        scrollLibraryToTop();
    });

    renderLibrary();
}

function getTotalPages() {
    return state.totalPages || 1;
}

async function renderLibrary() {
    const grid = document.getElementById("libraryGrid");
    const requestToken = ++state.requestToken;
    grid.innerHTML = `<article class="awesome-template-card loading-card"><div class="awesome-template-cover"></div><div><span>Loading</span><h3>正在读取数据库模板</h3><small>SQLite API</small></div></article>`;

    try {
        const params = new URLSearchParams({
            page: state.page,
            page_size: state.pageSize,
            category: state.category,
            q: state.query,
            status: "enabled"
        });
        if (state.type !== "all") params.set("modality", state.type);
        const data = await apiGet(`/api/templates?${params.toString()}`);
        if (requestToken !== state.requestToken) return;
        state.items = data.items || [];
        state.total = data.total || 0;
        state.totalPages = data.totalPages || 1;
        state.page = data.page || state.page;
    } catch (error) {
        if (requestToken !== state.requestToken) return;
        grid.innerHTML = `<div class="empty-admin">模板库 API 读取失败，请确认后端服务已启动。</div>`;
        return;
    }
    if (requestToken !== state.requestToken) return;

    const start = (state.page - 1) * state.pageSize;
    const end = Math.min(start + state.items.length, state.total);
    const pageLabel = `第 ${state.page} / ${state.totalPages} 页`;

    grid.innerHTML = state.items.length ? state.items.map(renderCard).join("") : `<div class="empty-admin">没有符合条件的模板</div>`;
    document.getElementById("libraryCount").textContent = state.total ? `${state.total} 个模板，当前 ${start + 1}-${end}` : "0 个模板";
    document.getElementById("libraryPageInfo").textContent = pageLabel;
    document.getElementById("libraryBottomPageInfo").textContent = pageLabel;
    document.getElementById("libraryPrev").disabled = state.page <= 1;
    document.getElementById("libraryNext").disabled = state.page >= state.totalPages;
}

function renderCard(template) {
    const title = template.title || "案例模板";
    const description = template.description || "";
    const cover = safeMediaUrl(template.cover || template.sourceCase?.image || "");
    const isVideo = template.modality === "video" || template.templateKind === "video";
    const promo = template.promoVideo || "";
    const paramCount = template.paramCount || template.params?.length || 0;
    const href = isVideo
        ? servicePageUrl("index.html", `#video-workbench:${encodeURIComponent(template.id)}`)
        : servicePageUrl("index.html", `#template-editor:${encodeURIComponent(template.id)}`);
    const media = cover
        ? (isVideo && promo
            ? `<video src="${escapeAttr(safeMediaUrl(promo))}" muted autoplay loop playsinline poster="${escapeAttr(cover)}"></video>`
            : `<img src="${escapeAttr(cover)}" alt="${escapeHtml(template.imageAlt || title)}" loading="lazy">`)
        : `<div class="awesome-template-cover-placeholder"><strong>${escapeHtml(title.slice(0, 24))}</strong><small>暂无封面</small></div>`;

    return `
        <article class="awesome-template-card" data-template-id="${escapeHtml(template.id)}">
            <a class="awesome-template-cover" href="${escapeAttr(href)}" aria-label="使用 ${escapeHtml(title)} 模板">
                ${media}
            </a>
            <div>
                <span>${escapeHtml(isVideo ? "短视频模板" : template.categoryLabel || getCategoryLabel(template.category))}</span>
                <h3>${escapeHtml(title)}</h3>
                <p>${escapeHtml(description)}</p>
                <small>${paramCount ? `${paramCount} 个可调参数` : "可编辑 Prompt"} · ${isVideo ? "视频" : "图片"}</small>
                <a class="card-action" href="${escapeAttr(href)}">${isVideo ? "生成视频" : "使用模板"}</a>
            </div>
        </article>
    `;
}

function getCategoryLabel(category) {
    return CATEGORY_LABELS[category] || category || "未分类";
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
