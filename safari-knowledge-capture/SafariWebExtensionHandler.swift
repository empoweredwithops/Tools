// Replace the auto-generated SafariWebExtensionHandler.swift (in the
// "<App Name> Extension" group in Xcode) with this file.
//
// This is the native side of the extension: Safari has no
// File System Access API for JS, so the JS side (save.js) sends messages
// here via browser.runtime.sendNativeMessage, and this handles the actual
// folder picker + file writes using standard macOS APIs.
//
// Requires: the Extension target's App Sandbox capability must have
// "File Access" > "User Selected File" set to "Read/Write" in Xcode's
// Signing & Capabilities tab (see BUILD-INSTRUCTIONS.md).

import SafariServices
import AppKit
import os.log

let SFExtensionMessageKey = "message"

class SafariWebExtensionHandler: NSObject, NSExtensionRequestHandling {

    static let bookmarkKey = "krWorkingFolderBookmark"

    func beginRequest(with context: NSExtensionContext) {
        let item = context.inputItems.first as? NSExtensionItem
        let message = item?.userInfo?[SFExtensionMessageKey] as? [String: Any] ?? [:]
        let action = message["action"] as? String ?? ""

        os_log(.default, "kr-capture: received action %@", action)

        let responseBody: [String: Any]

        switch action {
        case "getFolderStatus":
            responseBody = Self.getFolderStatus()
        case "chooseFolder":
            responseBody = Self.chooseFolderSync()
        case "checkFileExists":
            let filename = message["filename"] as? String ?? ""
            responseBody = Self.checkFileExists(filename: filename)
        case "writeFile":
            let filename = message["filename"] as? String ?? ""
            let content = message["content"] as? String ?? ""
            responseBody = Self.writeFile(filename: filename, content: content)
        default:
            responseBody = ["ok": false, "error": "unknown action: \(action)"]
        }

        let response = NSExtensionItem()
        response.userInfo = [SFExtensionMessageKey: responseBody]
        context.completeRequest(returningItems: [response], completionHandler: nil)
    }

    // MARK: - Security-scoped bookmark handling

    static func resolveFolderURL() -> URL? {
        guard let data = UserDefaults.standard.data(forKey: bookmarkKey) else { return nil }
        var isStale = false
        guard let url = try? URL(
            resolvingBookmarkData: data,
            options: [.withSecurityScope],
            relativeTo: nil,
            bookmarkDataIsStale: &isStale
        ) else {
            return nil
        }
        return url
    }

    static func getFolderStatus() -> [String: Any] {
        guard let url = resolveFolderURL() else {
            return ["ok": true, "folderName": NSNull()]
        }
        return ["ok": true, "folderName": url.lastPathComponent]
    }

    static func chooseFolderSync() -> [String: Any] {
        var result: [String: Any] = ["ok": false, "error": "cancelled"]
        let semaphore = DispatchSemaphore(value: 0)

        DispatchQueue.main.async {
            let panel = NSOpenPanel()
            panel.canChooseDirectories = true
            panel.canChooseFiles = false
            panel.allowsMultipleSelection = false
            panel.prompt = "Choose"
            panel.message = "Choose your Knowledge Repository working folder"

            NSApp.activate(ignoringOtherApps: true)
            let response = panel.runModal()

            if response == .OK, let url = panel.url {
                do {
                    let bookmark = try url.bookmarkData(
                        options: [.withSecurityScope],
                        includingResourceValuesForKeys: nil,
                        relativeTo: nil
                    )
                    UserDefaults.standard.set(bookmark, forKey: bookmarkKey)
                    result = ["ok": true, "folderName": url.lastPathComponent]
                } catch {
                    result = ["ok": false, "error": "bookmark failed: \(error.localizedDescription)"]
                }
            } else {
                result = ["ok": false, "error": "cancelled"]
            }
            semaphore.signal()
        }

        semaphore.wait()
        return result
    }

    static func withFolderAccess<T>(_ body: (URL) -> T) -> T? {
        guard let url = resolveFolderURL() else { return nil }
        guard url.startAccessingSecurityScopedResource() else { return nil }
        defer { url.stopAccessingSecurityScopedResource() }
        return body(url)
    }

    static func checkFileExists(filename: String) -> [String: Any] {
        guard !filename.isEmpty else { return ["ok": false, "error": "no filename"] }

        let exists = withFolderAccess { folder -> Bool in
            let fileURL = folder.appendingPathComponent(filename)
            return FileManager.default.fileExists(atPath: fileURL.path)
        }

        guard let exists = exists else {
            return ["ok": false, "error": "no folder chosen yet"]
        }
        return ["ok": true, "exists": exists]
    }

    static func writeFile(filename: String, content: String) -> [String: Any] {
        guard !filename.isEmpty else { return ["ok": false, "error": "no filename"] }

        let written = withFolderAccess { folder -> Bool in
            let fileURL = folder.appendingPathComponent(filename)
            do {
                try content.write(to: fileURL, atomically: true, encoding: .utf8)
                return true
            } catch {
                os_log(.error, "kr-capture: write failed: %@", error.localizedDescription)
                return false
            }
        }

        guard let written = written, written else {
            return ["ok": false, "error": "write failed or no folder chosen yet"]
        }
        return ["ok": true]
    }
}
