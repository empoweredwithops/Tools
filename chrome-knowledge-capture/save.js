// Handles: reading the captured selection, picking/remembering the working
// folder, and writing the Markdown file (with a filename-conflict retry).

const DB_NAME = "kr-extension";
const STORE_NAME = "handles";
const HANDLE_KEY = "workingFolder";

let folderHandle = null;
let capture = { selectionText: "", pageTitle: "", pageUrl: "" };

function $(id) { return document.getElementById(id); }

function setStatus(msg) { $("status").textContent = msg || ""; }

function slugify(str) {
  return (
    str
      .trim()
      .toLowerCase()
      .replace(/['"]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "untitled"
  );
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function buildMarkdown(title, sourceUrl, text) {
  const escapedTitle = title.replace(/"/g, '\\"');
  return [
    "---",
    `title: "${escapedTitle}"`,
    `source: ${sourceUrl || "unknown"}`,
    `date_captured: ${todayISO()}`,
    "---",
    "",
    text.trim(),
    ""
  ].join("\n");
}

function suggestNextName(filename) {
  const base = filename.replace(/\.md$/i, "");
  const m = base.match(/^(.*)-(\d+)$/);
  const nextBase = m ? `${m[1]}-${parseInt(m[2], 10) + 1}` : `${base}-2`;
  return `${nextBase}.md`;
}

// --- IndexedDB: persist the chosen FileSystemDirectoryHandle across sessions ---

function idbOpen() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE_NAME);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbGet(key) {
  const db = await idbOpen();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbSet(key, value) {
  const db = await idbOpen();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// --- File System Access helpers ---

async function ensurePermission(handle) {
  const opts = { mode: "readwrite" };
  if ((await handle.queryPermission(opts)) === "granted") return true;
  if ((await handle.requestPermission(opts)) === "granted") return true;
  return false;
}

async function loadSavedFolder() {
  let stored;
  try {
    stored = await idbGet(HANDLE_KEY);
  } catch (e) {
    return;
  }
  if (!stored) return;
  const ok = await ensurePermission(stored);
  if (ok) {
    folderHandle = stored;
    $("folder-name").textContent = stored.name;
  } else {
    $("folder-name").textContent = "permission needed — choose folder";
  }
}

async function fileExists(handle, name) {
  try {
    await handle.getFileHandle(name, { create: false });
    return true;
  } catch (e) {
    return false;
  }
}

async function writeFile(handle, name, content) {
  const fileHandle = await handle.getFileHandle(name, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(content);
  await writable.close();
}

async function attemptSave(filename) {
  const exists = await fileExists(folderHandle, filename);
  if (exists) {
    $("filename-conflict").hidden = false;
    $("conflict-msg").textContent = `"${filename}" already exists. Choose a different name.`;
    $("new-filename").value = suggestNextName(filename);
    setStatus("");
    return false;
  }

  const title = $("title-input").value.trim();
  const md = buildMarkdown(title, capture.pageUrl, capture.selectionText);
  await writeFile(folderHandle, filename, md);
  setStatus(`Saved as ${filename}`);
  setTimeout(() => window.close(), 900);
  return true;
}

// --- Wiring ---

$("choose-folder").addEventListener("click", async () => {
  try {
    const handle = await window.showDirectoryPicker();
    const ok = await ensurePermission(handle);
    if (!ok) {
      setStatus("Permission denied for that folder.");
      return;
    }
    folderHandle = handle;
    await idbSet(HANDLE_KEY, handle);
    $("folder-name").textContent = handle.name;
    setStatus("");
  } catch (e) {
    if (e.name !== "AbortError") setStatus("Couldn't set folder: " + e.message);
  }
});

$("save-btn").addEventListener("click", async () => {
  if (!folderHandle) {
    setStatus("Choose a folder first.");
    return;
  }

  const conflictVisible = !$("filename-conflict").hidden;
  let filename;

  if (conflictVisible) {
    const newName = $("new-filename").value.trim();
    if (!newName) {
      setStatus("Enter a filename.");
      return;
    }
    filename = newName.toLowerCase().endsWith(".md") ? newName : newName + ".md";
  } else {
    const title = $("title-input").value.trim();
    if (!title) {
      setStatus("Enter a document title.");
      return;
    }
    filename = slugify(title) + ".md";
  }

  const ok = await attemptSave(filename);
  if (ok) $("filename-conflict").hidden = true;
});

(async function init() {
  const stored = await chrome.storage.session.get("pendingCapture");
  if (stored.pendingCapture) capture = stored.pendingCapture;

  $("title-input").value = capture.pageTitle || "";
  $("source-url").textContent = capture.pageUrl || "";
  $("preview").value = capture.selectionText || "";

  await loadSavedFolder();
})();
