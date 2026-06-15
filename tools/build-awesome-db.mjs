import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const repoDir = path.join(root, "assets", "awesome-gpt-image-2");
const webappRepoDir = path.join(root, "webapp", "assets", "awesome-gpt-image-2");
const dbPath = path.join(webappRepoDir, "local-db.js");
const fallbackStyleSources = [
    path.join(repoDir, "data", "style-library.json"),
    path.join(root, ".external", "style-library-4274f28aacdf.json"),
    path.join(webappRepoDir, "data", "style-library.json")
];
const fallbackCaseSources = [
    path.join(repoDir, "data", "cases.json"),
    path.join(root, ".external", "cases-f39e78ad7018.json"),
    path.join(webappRepoDir, "data", "cases.json")
];

async function firstExisting(paths) {
    for (const file of paths) {
        try {
            await fs.access(file);
            return file;
        } catch {}
    }
    return null;
}

const styleSource = await firstExisting(fallbackStyleSources);
if (!styleSource) {
    throw new Error("Missing style library source in repo or local cache");
}

const caseSource = await firstExisting(fallbackCaseSources);
if (!caseSource) {
    throw new Error("Missing cases source in repo or local cache");
}

const sourceDataDir = path.dirname(caseSource);
const webappDataDir = path.join(webappRepoDir, "data");
await fs.mkdir(webappRepoDir, { recursive: true });
if (path.resolve(sourceDataDir) !== path.resolve(webappDataDir)) {
    await fs.cp(sourceDataDir, webappDataDir, { recursive: true, force: true });
}
await fs.copyFile(styleSource, path.join(webappDataDir, "style-library.json"));

const styleData = JSON.parse(await fs.readFile(styleSource, "utf8"));
const caseData = JSON.parse(await fs.readFile(caseSource, "utf8"));
const caseMap = new Map((caseData.cases || []).map(item => [String(item.id), item]));
const WIDE_COLON = "\uFF1A";
const WIDE_COMMA = "\uFF0C";

function localImagePath(value) {
    if (!value) return null;
    return String(value).replace(/^\/images\//, "assets/awesome-gpt-image-2/data/images/");
}

function paramKey(label, index) {
    const slug = String(label || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");

    return slug ? `param-${index}-${slug}` : `param-${index}`;
}

function trimExample(label) {
    const text = String(label || "").trim();
    const colonIndexes = [];
    for (const colon of [":", WIDE_COLON]) {
        let index = text.indexOf(colon);
        while (index >= 0) {
            const before = text[index - 1] || "";
            const after = text[index + 1] || "";
            if (!/\d/.test(before) || !/\d/.test(after)) {
                colonIndexes.push(index);
            }
            index = text.indexOf(colon, index + 1);
        }
    }
    if (!colonIndexes.length) return "";

    const colon = Math.min(...colonIndexes);
    const candidate = text
        .slice(colon + 1)
        .split(new RegExp(`[\/,${WIDE_COMMA}]`))[0]
        .trim();

    return candidate;
}

function stripAfterNonRatioColon(value) {
    const text = String(value || "").trim();
    const colonIndexes = [];
    for (const colon of [":", WIDE_COLON]) {
        let index = text.indexOf(colon);
        while (index >= 0) {
            const before = text[index - 1] || "";
            const after = text[index + 1] || "";
            if (!/\d/.test(before) || !/\d/.test(after)) {
                colonIndexes.push(index);
            }
            index = text.indexOf(colon, index + 1);
        }
    }

    if (!colonIndexes.length) return text;
    return text.slice(0, Math.min(...colonIndexes)).trim();
}

function defaultParamValue(label, kind, givenDefault) {
    if (givenDefault) return givenDefault;

    const normalized = String(label || "").trim();
    const example = trimExample(normalized);
    if (example) return example;

    const upperDefaults = {
        "PACKAGE TYPE": "premium retail gift box",
        "CITY/COUNTRY": "Shanghai, China",
        "HISTORICAL_EVENT": "Silk Road caravan trade",
        "CITY": "Xi'an",
        "ROLE": "local guide",
        "TIMEPIECE": "experimental tourbillon watch"
    };

    if ((kind === "square" || kind === "paren") && upperDefaults[normalized]) {
        return upperDefaults[normalized];
    }

    if (/Product Name|brand|Brand|logo|Logo/.test(normalized)) return "Mori Studio";
    if (/title|Title|headline|Headline/.test(normalized)) return "Spring launch";
    if (/theme|Theme|topic|Topic/.test(normalized)) return "urban wellness breakfast";
    if (/color|Color|palette|Palette/.test(normalized)) return "warm white and sage green";
    if (/ratio|Ratio|format|Format|size|Size/.test(normalized)) return "3:4 vertical";
    if (/industry|Industry|solution|Solution/.test(normalized)) return "AI content generation solution";

    const cleaned = stripAfterNonRatioColon(normalized)
        .replace(/^\u5efa\u8bae\s*/, "")
        .replace(/^\u586b\u5199\s*/, "")
        .trim();

    return cleaned || "custom value";
}

function promptParams(prompt) {
    const promptText = String(prompt || "");
    const items = [];
    const seen = new Set();

    function isStandaloneLine(token, index) {
        const lineStart = promptText.lastIndexOf("\n", index) + 1;
        const nextBreak = promptText.indexOf("\n", index + token.length);
        const lineEnd = nextBreak >= 0 ? nextBreak : promptText.length;
        return promptText.slice(lineStart, lineEnd).trim() === token;
    }

    function add(token, label, kind, givenDefault = "") {
        if (!token || seen.has(token)) return;
        seen.add(token);

        const cleanLabel = String(label || "").trim() || `Param ${items.length + 1}`;
        items.push({
            key: paramKey(cleanLabel, items.length + 1),
            label: cleanLabel,
            token,
            default: defaultParamValue(cleanLabel, kind, givenDefault),
            type: kind
        });
    }

    for (const match of promptText.matchAll(/\{argument\b[^}]*\}/g)) {
        const token = match[0];
        const name = token.match(/name="([^"]+)"/)?.[1] || "";
        const fallback = token.match(/default="([^"]*)"/)?.[1] || "";
        add(token, name, "argument", fallback);
    }

    for (const match of promptText.matchAll(/\u3010([^\u3011]{1,80})\u3011/g)) {
        if (isStandaloneLine(match[0], match.index || 0)) continue;
        add(match[0], match[1], "chinese-slot");
    }

    for (const match of promptText.matchAll(/\[([A-Z][A-Z0-9_ /&.-]{2,80})\]/g)) {
        add(match[0], match[1], "square");
    }

    for (const match of promptText.matchAll(/\(([A-Z][A-Z0-9_ /&.-]{2,80})\)/g)) {
        add(match[0], match[1], "paren");
    }

    return items;
}

function compactCase(item) {
    if (!item) return null;
    return {
        id: item.id,
        title: item.title,
        category: item.category,
        image: localImagePath(item.image),
        promptPreview: item.promptPreview
    };
}

const styleTemplates = (styleData.templates || []).map(template => {
    const sourceCases = (template.exampleCases || [])
        .map(id => caseMap.get(String(id)))
        .filter(Boolean)
        .map(compactCase);

    let selectedCase = null;
    for (const caseMeta of sourceCases) {
        const candidate = caseMap.get(String(caseMeta.id));
        if (promptParams(candidate?.prompt).length) {
            selectedCase = candidate;
            break;
        }
    }

    if (!selectedCase && sourceCases.length) {
        selectedCase = caseMap.get(String(sourceCases[0].id));
    }

    const promptTemplate = selectedCase?.prompt || "";

    return {
        id: template.id,
        anchor: template.anchor,
        title: template.title,
        description: template.description,
        category: template.category,
        cover: localImagePath(template.cover),
        tags: template.tags,
        useWhen: template.useWhen,
        guidance: template.guidance,
        pitfalls: template.pitfalls,
        exampleCases: template.exampleCases,
        sourceCases,
        sourceCase: compactCase(selectedCase),
        promptTemplate,
        params: promptParams(promptTemplate)
    };
});

const templates = (caseData.cases || []).map(item => ({
    id: `case-${item.id}`,
    caseId: item.id,
    title: item.title,
    description: item.promptPreview,
    category: item.category,
    cover: localImagePath(item.image),
    imageAlt: item.imageAlt,
    tags: item.styles || [],
    scenes: item.scenes || [],
    featured: Boolean(item.featured),
    sourceLabel: item.sourceLabel,
    sourceUrl: item.sourceUrl,
    githubUrl: item.githubUrl,
    sourceCase: compactCase(item),
    promptTemplate: item.prompt || "",
    params: promptParams(item.prompt)
}));

const imageRoot = path.join(webappDataDir, "images");
const imageFiles = (await fs.readdir(imageRoot)).filter(file => /\.(png|jpe?g|webp)$/i.test(file));

const db = {
    repository: styleData.repository,
    templateDocument: styleData.templateDocument,
    totalCases: caseData.totalCases,
    imageFiles: imageFiles.length,
    categories: caseData.categories,
    styles: caseData.styles,
    styleCategories: styleData.categories,
    styleTemplates,
    templates,
    updatedFrom: "freestylefly/awesome-gpt-image-2:data/style-library.json,data/cases.json"
};

await fs.writeFile(dbPath, `window.AWESOME_GPT_IMAGE_2_DB = ${JSON.stringify(db)};\n`, "utf8");

console.log(JSON.stringify({
    templates: templates.length,
    templatesWithParams: templates.filter(template => template.params.length).length,
    styleTemplates: styleTemplates.length,
    imageFiles: imageFiles.length,
    database: dbPath
}, null, 2));
