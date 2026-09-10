// Safari has no File System Access API (no showDirectoryPicker), so folder
// picking and file writing happen in native Swift code (SafariWebExtensionHandler.swift)
// via browser.runtime.sendNativeMessage. This file owns the same business logic
// as the Chrome version's save.js (slugify, frontmatter, conflict handling) —
// only the "talk to the filesystem" calls are swapped for native messages.

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

// --- Native messaging bridge ---
// "application.id" is unused by Safari (there's only one native host — the
// containing app) but the WebExtension API still expects an argument there.

function nativeMessage(action, extra = {}) {
  return browser.runtime.sendNativeMessage("application.id", { action, ...extra });
}

async function refreshFolderLabel() {
  try {
    const res = await nativeMessage("getFolderStatus");
    if (res && res.ok && res.folderName) {
      $("folder-name").textContent = res.folderName;
    } else {
      $("folder-name").textContent = "not set";
    }
  } catch (e) {
    $("folder-name").textContent = "not set";
    setStatus("Couldn't reach the native app: " + e.message);
  }
}

$("choose-folder").addEventListener("click", async () => {
  setStatus("");
  try {
    const res = await nativeMessage("chooseFolder");
    if (res && res.ok) {
      $("folder-name").textContent = res.folderName;
    } else if (res && res.error !== "cancelled") {
      setStatus("Couldn't set folder: " + res.error);
    }
  } catch (e) {
    setStatus("Couldn't reach the native app: " + e.message);
  }
});

async function attemptSave(filename) {
  const existsRes = await nativeMessage("checkFileExists", { filename });
  if (!existsRes || !existsRes.ok) {
    setStatus(existsRes && existsRes.error ? existsRes.error : "Choose a folder first.");
    return false;
  }

  if (existsRes.exists) {
    $("filename-conflict").hidden = false;
    $("conflict-msg").textContent = `"${filename}" already exists. Choose a different name.`;
    $("new-filename").value = suggestNextName(filename);
    setStatus("");
    return false;
  }

  const title = $("title-input").value.trim();
  const md = buildMarkdown(title, capture.pageUrl, capture.selectionText);
  const writeRes = await nativeMessage("writeFile", { filename, content: md });
  if (!writeRes || !writeRes.ok) {
    setStatus("Couldn't save: " + (writeRes && writeRes.error ? writeRes.error : "unknown error"));
    return false;
  }

  setStatus(`Saved as ${filename}`);
  setTimeout(() => window.close(), 900);
  return true;
}

$("save-btn").addEventListener("click", async () => {
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

  try {
    const ok = await attemptSave(filename);
    if (ok) $("filename-conflict").hidden = true;
  } catch (e) {
    setStatus("Couldn't reach the native app: " + e.message);
  }
});

(async function init() {
  const stored = await browser.storage.local.get("pendingCapture");
  if (stored.pendingCapture) capture = stored.pendingCapture;
  browser.storage.local.remove("pendingCapture");

  $("title-input").value = capture.pageTitle || "";
  $("source-url").textContent = capture.pageUrl || "";
  $("preview").value = capture.selectionText || "";

  await refreshFolderLabel();
})();
