# Save to Knowledge Repository (Chrome extension)

Right-click text you've selected on any page and save it as a Markdown file, straight into a folder on your Mac.

## Install it (unpacked, for now)

1. Unzip `kr-capture.zip` somewhere you'll keep it — this folder *is* the extension, so don't delete it after installing.
2. Open Chrome, go to `chrome://extensions`.
3. Turn on **Developer mode** (top right toggle).
4. Click **Load unpacked**, and select the unzipped `kr-capture` folder.
5. The extension icon (green "K") shows up in your extensions list.

## First use

1. Select text on any page, right-click, choose **Save to Knowledge Repository**.
2. A small window opens with the selected text, a title field (pre-filled with the page title — edit it), and a **Choose folder…** button.
3. Click **Choose folder…** and pick your working folder — this is a one-time step. Chrome will ask you to confirm; after that, it's remembered and won't ask again unless you revoke the permission or remove the extension.
4. Set the title, click **Save**.

The file is named from the title (e.g. "Q3 Retro Notes" → `q3-retro-notes.md`) and saved straight into the folder you picked. If a file with that name already exists, it'll ask you for a different filename instead of overwriting anything.

## What's in the file

```
---
title: "Q3 Retro Notes"
source: https://example.com/the-page
date_captured: 2026-09-09
---

The text you selected goes here.
```

## Notes

- The folder you pick is stored in the extension's own local storage on this Mac/Chrome profile — it doesn't sync anywhere, per what we talked about.
- Since this is unpacked/developer mode, Chrome may occasionally show a "Disable developer mode extensions" nag banner — that's normal for unpacked extensions and safe to dismiss.
- If you ever want to point it at a different folder, just click **Choose folder…** again next time you use it.
