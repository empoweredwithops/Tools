// Creates the right-click menu item and hands the selected text off to save.html.

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-to-kr",
    title: "Save to Knowledge Repository",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "save-to-kr") return;

  const payload = {
    selectionText: info.selectionText || "",
    pageTitle: (tab && tab.title) || "",
    pageUrl: info.pageUrl || (tab && tab.url) || ""
  };

  await chrome.storage.session.set({ pendingCapture: payload });

  chrome.windows.create({
    url: chrome.runtime.getURL("save.html"),
    type: "popup",
    width: 520,
    height: 680
  });
});
