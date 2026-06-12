import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const currentFile = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFile);
const currentName = path.basename(currentFile);

const entries = await fs.readdir(currentDir, { withFileTypes: true });
const candidates = await Promise.all(
    entries
        .filter(entry => entry.isFile() && /^build-awesome-db.*\.mjs$/i.test(entry.name) && entry.name !== currentName)
        .map(async entry => {
            const fullPath = path.join(currentDir, entry.name);
            const stat = await fs.stat(fullPath);
            return { fullPath, mtimeMs: stat.mtimeMs };
        })
);

if (!candidates.length) {
    throw new Error("Missing build-awesome-db*.mjs implementation");
}

candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
await import(pathToFileURL(candidates[0].fullPath).href);
