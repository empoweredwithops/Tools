// Creates the right-click menu item and hands the selected text off to save.html.
// Uses the browser.* namespace, which is what Safari Web Extensions implement.

browser.runtime.onInstalled.addListener(() => {
  browser.contextMenus.create({
    id: "save-to-kr",
    title: "Save to Knowledge Repository",
    contexts: ["selection"]
  });
});

browser.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "save-to-kr") return;

  const payload = {
    selectionText: info.selectionText || "",
    pageTitle: (tab && tab.title) || "",
    pageUrl: info.pageUrl || (tab && tab.url) || ""
  };

  await browser.storage.local.set({ pendingCapture: payload });

  browser.windows.create({
    url: browser.runtime.getURL("save.html"),
    type: "popup",
    width: 520,
    height: 680
  });
});
