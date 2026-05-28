const PRICING = {
    free: { name: "免费体验", price: 0 },
    basic: { name: "月卡", price: 29, yearly: 23 },
    pro: { name: "创作者版", price: 99, yearly: 79 },
    studio: { name: "工作室版", price: 299, yearly: 239 },
    pack200: { name: "200 积分包", price: 19 },
    pack600: { name: "600 积分包", price: 49 },
    pack1500: { name: "1500 积分包", price: 99 },
    pack6000: { name: "6000 积分包", price: 299 }
};

const GENERATION_API_ENDPOINT = "/api/generate-image";
const LOCAL_API_ORIGIN = "http://127.0.0.1:4178";
const TEMPLATE_REFERENCE_LIMIT = 10;
const TEMPLATE_REFERENCE_MAX_SIZE = 10 * 1024 * 1024;
const DEFAULT_CREDIT_RULES = {
    quality: {
        draft: { label: "快速草稿", factor: 0.7 },
        standard: { label: "标准", factor: 1 },
        high: { label: "高质量", factor: 1.35 },
        ultra: { label: "超清", factor: 1.8 }
    },
    size: {
        "1024x1024": { label: "1024 x 1024", factor: 1 },
        "1024x1536": { label: "1024 x 1536", factor: 1.3 },
        "1536x1024": { label: "1536 x 1024", factor: 1.3 },
        "1536x1536": { label: "1536 x 1536", factor: 1.8 },
        "2048x2048": { label: "2048 x 2048", factor: 2.6 }
    }
};

let uploadedImage = null;
let generationCount = 1;
let templateReferenceImages = [];
let templateResultDownloadUrl = "";
let activeAwesomeTemplate = null;
let activeTemplateValues = {};
let awesomeTemplates = [];
let awesomeStats = { totalTemplates: 0, imageFiles: 0, styleTemplates: 0 };
let generationModels = [];
let publicSettings = {};
let templateDataPromise = null;
const POPULAR_TEMPLATE_LIMIT = 30;
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
    document.getElementById("mobileMenu")?.addEventListener("click", () => {
        document.getElementById("navLinks")?.classList.toggle("open");
    });
}

function initTemplateFilters() {
    const chips = document.querySelectorAll(".chip[data-filter]");
    const cards = document.querySelectorAll(".template-card");

    chips.forEach(chip => {
        chip.addEventListener("click", () => {
            const filter = chip.dataset.filter;
            chips.forEach(item => item.classList.remove("active"));
            chip.classList.add("active");
            cards.forEach(card => {
                const show = filter === "all" || card.dataset.category === filter;
                card.style.display = show ? "" : "none";
            });
        });
    });
}

function apiUrl(path) {
    if (!path || /^https?:\/\//i.test(path) || path.startsWith("data:") || path.startsWith("blob:")) return path;
    const isLocalFrontend = ["", "127.0.0.1", "localhost"].includes(window.location.hostname);
    const isBackendOrigin = isLocalFrontend && window.location.port === "4178";
    if (window.location.protocol === "file:" && path.startsWith("/")) return `${LOCAL_API_ORIGIN}${path}`;
    if (isLocalFrontend && !isBackendOrigin && path.startsWith("/api/")) return `${LOCAL_API_ORIGIN}${path}`;
    return path;
}

function assetUrl(path) {
    return apiUrl(path);
}

async function apiGet(path) {
    const response = await fetch(apiUrl(path), { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
}

async function apiPost(path, payload) {
    const response = await fetch(apiUrl(path), {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData.message || errorData.error || `HTTP ${response.status}`;
        const error = new Error(message);
        error.data = errorData;
        throw error;
    }
    return response.json();
}

async function ensureTemplateData() {
    if (templateDataPromise) return templateDataPromise;
    templateDataPromise = (async () => {
        const [settingsData, templateData] = await Promise.all([
            apiGet("/api/settings/public"),
            apiGet(`/api/templates?featured=1&page_size=${POPULAR_TEMPLATE_LIMIT}&include_params=1&sort=featured`)
        ]);
        publicSettings = settingsData.settings || {};
        generationModels = settingsData.models || [];
        awesomeStats = {
            totalTemplates: settingsData.counts?.templates || templateData.total || 0,
            imageFiles: settingsData.counts?.imageBlobs || 0,
            styleTemplates: settingsData.counts?.styleTemplates || 0
        };
        awesomeTemplates = templateData.items || [];
        populateGenerationControls();
        return awesomeTemplates;
    })();
    return templateDataPromise;
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
        const serviceUrl = `${LOCAL_API_ORIGIN}/index.html`;
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

async function initTemplateEditor() {
    document.getElementById("templateParamForm")?.addEventListener("input", event => {
        const field = event.target.closest("[data-param-key]");
        if (!field || !activeAwesomeTemplate) return;

        activeTemplateValues[field.dataset.paramKey] = field.value;
        updateTemplatePromptFromParams();
    });

    document.getElementById("templatePromptEditor")?.addEventListener("input", updatePromptStats);
    document.getElementById("copyTemplatePrompt")?.addEventListener("click", copyTemplatePrompt);
    document.getElementById("resetTemplateParams")?.addEventListener("click", resetTemplateParams);
    document.getElementById("generateFromTemplate")?.addEventListener("click", requestTemplateGeneration);
    document.getElementById("downloadTemplateResult")?.addEventListener("click", downloadTemplateResult);
    initTemplateReferenceUpload();
    document.getElementById("templateGenerationConfig")?.addEventListener("change", event => {
        if (event.target?.id === "templateModel") {
            populateSizeOptionsForModel();
        }
        updateTemplateCreditEstimate();
    });

    const initialId = getTemplateIdFromLocation();
    try {
        const templates = await ensureTemplateData();
        if (initialId) {
            openAwesomeTemplate(initialId, false);
        } else if (templates.length) {
            const defaultTemplate = templates.find(template => template.params?.length) || templates[0];
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

async function openAwesomeTemplate(templateId, updateUrl = true) {
    let template = awesomeTemplates.find(item => item.id === templateId || item.sourceTemplateId === templateId);

    if (!template || !Array.isArray(template.params)) {
        try {
            const data = await apiGet(`/api/templates/${encodeURIComponent(templateId)}`);
            template = data.item;
            if (template && !awesomeTemplates.some(item => item.id === template.id)) {
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

    renderTemplateEditor(template, { shouldScroll: true, updateUrl });
}

function renderTemplateEditor(template, options = {}) {
    const title = getLocalized(template.title) || "案例模板";
    const description = getLocalized(template.description) || template.sourceCase?.promptPreview || "";
    const params = Array.isArray(template.params) ? template.params : [];

    activeAwesomeTemplate = template;
    activeTemplateValues = Object.fromEntries(params.map(param => [param.key, param.default || ""]));

    setText("editorTemplateTitle", title);
    setText("editorTemplateDescription", description);
    setText("editorResultTitle", title);
    setText("editorResultSummary", params.length ? "调整左侧参数后，最终 Prompt 会实时更新。" : "这个模板没有识别到参数位，可以直接修改最终 Prompt。");
    setText("editorResultMeta", "生成完成后可下载高清图。");

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
                <p>可以直接在右侧最终 Prompt 里编辑，也可以后续在数据库里为它补充自定义参数。</p>
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
    const editor = document.getElementById("templatePromptEditor");
    const stats = document.getElementById("promptStats");
    if (!editor || !stats) return;

    const length = editor.value.trim().length;
    stats.textContent = `${length} 字符`;
}

async function copyTemplatePrompt() {
    const prompt = document.getElementById("templatePromptEditor")?.value?.trim();
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

function getTemplateGenerationSettings() {
    return {
        model: document.getElementById("templateModel")?.value || publicSettings.defaultModel || "gpt-image-2-high",
        quality: document.getElementById("templateQuality")?.value || "high",
        aspectRatio: document.getElementById("templateAspectRatio")?.value || "1:1",
        size: document.getElementById("templateImageSize")?.value || "1024x1024",
        count: Number(document.getElementById("templateOutputCount")?.value || 1),
        referenceMode: document.getElementById("templateReferenceMode")?.value || "optional"
    };
}

function populateGenerationControls() {
    const model = document.getElementById("templateModel");
    if (model && generationModels.length) {
        const current = model.value || publicSettings.defaultModel;
        model.innerHTML = generationModels
            .filter(item => item.enabled !== false)
            .map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · ${Number(item.cost || 5)} 积分基础</option>`)
            .join("");
        if ([...model.options].some(option => option.value === current)) {
            model.value = current;
        }
    }

    populateQualityOptions();
    populateSizeOptionsForModel();
    updateTemplateCreditEstimate();
}

function setTemplateGenerationDefaults(template) {
    populateGenerationControls();
    const model = document.getElementById("templateModel");
    const quality = document.getElementById("templateQuality");
    const ratio = document.getElementById("templateAspectRatio");
    const size = document.getElementById("templateImageSize");
    if (model && template.modelRoute && [...model.options].some(option => option.value === template.modelRoute)) {
        model.value = template.modelRoute;
    }
    populateSizeOptionsForModel();
    if (quality && template.defaultQuality) quality.value = template.defaultQuality;
    if (ratio && template.defaultAspectRatio) ratio.value = template.defaultAspectRatio;
    if (size && template.defaultSize && [...size.options].some(option => option.value === template.defaultSize)) {
        size.value = template.defaultSize;
    }
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

    const current = quality.value || publicSettings.defaultQuality || "high";
    const qualityRules = getCreditRules().quality || DEFAULT_CREDIT_RULES.quality;
    quality.innerHTML = Object.entries(qualityRules).map(([value, rule]) => {
        const factor = Number(rule.factor || 1);
        return `<option value="${escapeHtml(value)}">${escapeHtml(rule.label || value)} · x${factor.toFixed(2)}</option>`;
    }).join("");
    quality.value = [...quality.options].some(option => option.value === current) ? current : "high";
}

function populateSizeOptionsForModel() {
    const size = document.getElementById("templateImageSize");
    if (!size) return;

    const current = size.value || "1024x1024";
    const selectedModel = getSelectedModel();
    const modelSizes = Array.isArray(selectedModel?.sizes) ? selectedModel.sizes : [];
    const sizeRules = getCreditRules().size || DEFAULT_CREDIT_RULES.size;
    const values = [...new Set([...modelSizes, ...Object.keys(sizeRules)])];

    size.innerHTML = values.map(value => {
        const rule = getCreditRule("size", value);
        const factor = Number(rule.factor || 1);
        return `<option value="${escapeHtml(value)}">${escapeHtml(rule.label || value.replace("x", " x "))} · x${factor.toFixed(2)}</option>`;
    }).join("");
    size.value = values.includes(current) ? current : selectedModel?.defaultSize || "1024x1024";
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
    drop?.addEventListener("click", openPicker);
    drop?.addEventListener("keydown", event => {
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
        if (!file.type.startsWith("image/")) {
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
    const preview = document.getElementById("templateReferencePreview");
    if (count) count.textContent = `${templateReferenceImages.length} / ${TEMPLATE_REFERENCE_LIMIT}`;
    if (!preview) return;

    if (!templateReferenceImages.length) {
        preview.innerHTML = `<span class="template-reference-empty">最多 10 张，单张 10MB 内</span>`;
        return;
    }

    preview.innerHTML = templateReferenceImages.map(image => `
        <article class="template-reference-thumb">
            <img src="${escapeHtml(image.dataUrl)}" alt="${escapeHtml(image.name || "参考图")}">
            <button type="button" aria-label="移除 ${escapeHtml(image.name || "参考图")}" data-reference-remove="${escapeHtml(image.id)}">×</button>
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
    image.classList.remove("result-error");
    if (isGenerating) {
        image.classList.add("is-empty");
        image.classList.remove("has-result");
        image.style.removeProperty("--cover");
        setText("editorResultPlaceholder", label);
    } else if (!image.classList.contains("has-result")) {
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

function downloadTemplateResult() {
    if (!templateResultDownloadUrl) {
        showToast("生成完成后可下载", "error");
        return;
    }

    const link = document.createElement("a");
    link.href = templateResultDownloadUrl;
    link.download = `${getLocalized(activeAwesomeTemplate?.title) || "生成结果"}.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
}

async function requestTemplateGeneration() {
    const prompt = document.getElementById("templatePromptEditor")?.value?.trim();
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
        params: activeTemplateValues,
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
        setText("editorResultSummary", data?.message || `任务 ${data?.jobNo || data?.jobId || ""} 已进入生成队列，本次已扣除 ${creditCost} 积分；如生成失败会自动退回。`);
        showToast("生成任务已提交");
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
        element.style.setProperty("--cover", `url('${assetUrl(url)}')`);
    }
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function initUpload() {
    const uploadArea = document.getElementById("image-upload");
    const fileInput = document.getElementById("image-input");

    uploadArea?.addEventListener("click", () => fileInput?.click());

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
    if (!file.type.startsWith("image/")) {
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
                <button type="button" class="btn btn-secondary" onclick="removeImage()">重新上传</button>
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
                model: publicSettings.defaultModel || "gpt-image-2-high",
                quality: publicSettings.defaultQuality || "high",
                aspectRatio: "4:5",
                size: "1024x1536",
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
    } catch (error) {
        resultArea.innerHTML = `
            <div class="generation-state">
                <strong>生成服务暂不可用</strong>
                <p>请稍后重试或联系管理员。</p>
            </div>
        `;
        showToast("无法提交生成", "error");
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = "立即生成";
    }
}

function initWorkbench() {
    document.getElementById("toggleAdvanced")?.addEventListener("click", event => {
        const panel = document.getElementById("advancedPanel");
        panel?.classList.toggle("open");
        event.currentTarget.textContent = panel?.classList.contains("open") ? "收起高级参数" : "展开高级参数";
    });

    document.querySelectorAll(".rail-item[data-workbench-tab]").forEach(button => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".rail-item[data-workbench-tab]").forEach(item => item.classList.remove("active"));
            button.classList.add("active");
            setText("workbenchPanelKicker", button.textContent.trim());
            setText("workbenchPanelTitle", button.dataset.title || button.textContent.trim());
        });
    });

    document.querySelectorAll(".workspace-card select").forEach(select => {
        select.addEventListener("change", updateWorkbenchSelectionState);
    });
    updateWorkbenchSelectionState();

    document.querySelectorAll(".mode-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            const group = tab.closest(".mode-tabs") || document;
            group.querySelectorAll(".mode-tab").forEach(item => item.classList.remove("active"));
            tab.classList.add("active");
        });
    });

    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(item => item.classList.remove("active"));
            tab.classList.add("active");
        });
    });
}

function updateWorkbenchSelectionState() {
    const prompt = document.getElementById("prompt");
    if (!prompt) return;

    const size = document.getElementById("size")?.value || "1:1";
    const style = document.getElementById("style")?.selectedOptions?.[0]?.textContent || "自然暖调";
    const count = document.getElementById("n")?.value || "1";
    prompt.dataset.settings = `${size} / ${style} / ${count}`;
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
}

function openPayment(planId) {
    const plan = PRICING[planId] || PRICING.pro;
    document.getElementById("planName").textContent = plan.name;
    document.getElementById("planPrice").textContent = plan.price;
    document.getElementById("paymentModal")?.classList.add("active");
    document.getElementById("paymentModal")?.setAttribute("aria-hidden", "false");
}

function closePayment() {
    document.getElementById("paymentModal")?.classList.remove("active");
    document.getElementById("paymentModal")?.setAttribute("aria-hidden", "true");
}

function selectMethod(method, target) {
    document.querySelectorAll(".payment-method").forEach(item => item.classList.remove("active"));
    target?.classList.add("active");

    const hint = document.getElementById("qrcodeHint");
    const map = {
        wechat: "微信扫码支付，支付后自动开通",
        alipay: "支付宝扫码支付，支付后自动开通",
        service: "添加客服微信，支持对公转账和发票申请"
    };
    hint.textContent = map[method] || map.wechat;
}

function initAccountModal() {
    const modal = document.getElementById("accountModal");
    document.querySelectorAll("[data-open-account]").forEach(button => {
        button.addEventListener("click", () => {
            modal?.classList.add("active");
            modal?.setAttribute("aria-hidden", "false");
        });
    });

    document.querySelectorAll("[data-close-account]").forEach(button => {
        button.addEventListener("click", () => {
            modal?.classList.remove("active");
            modal?.setAttribute("aria-hidden", "true");
        });
    });

    modal?.addEventListener("click", event => {
        if (event.target === modal) {
            modal.classList.remove("active");
            modal.setAttribute("aria-hidden", "true");
        }
    });
}

function showToast(message, type = "success") {
    const container = document.getElementById("toast");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(6px)";
    }, 2400);

    setTimeout(() => toast.remove(), 2800);
}

window.openPayment = openPayment;
window.closePayment = closePayment;
window.selectMethod = selectMethod;
window.removeImage = removeImage;
