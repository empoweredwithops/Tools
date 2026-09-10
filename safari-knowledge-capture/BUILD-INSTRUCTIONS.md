# Building the Safari version

Safari doesn't have the API Chrome uses to write directly to a folder you pick (no File System Access API). So this version works a little differently under the hood: the extension talks to a small native Swift handler that does the folder picking and file writing — same end result for you, just built with Apple's tools instead of pure JS. That's why this one needs Xcode instead of a simple "load unpacked."

Everything below runs on your Mac, not in a Cowork session — a few Terminal commands and some clicking in Xcode.

## 1. Convert the extension into an Xcode project

Open Terminal and run:

```bash
xcrun safari-web-extension-converter "$HOME/Documents/kr-capture-safari/extension-source" \
  --project-location "$HOME/Documents/kr-capture-safari" \
  --app-name "Knowledge Repository" \
  --bundle-identifier com.empoweredwithops.krcapture \
  --macos-only \
  --no-open
```

If it asks to confirm anything, say yes. This generates an Xcode project at:

```
~/Documents/kr-capture-safari/Knowledge Repository/Knowledge Repository.xcodeproj
```

## 2. Open it in Xcode

```bash
open "$HOME/Documents/kr-capture-safari/Knowledge Repository/Knowledge Repository.xcodeproj"
```

## 3. Swap in the real native handler

In Xcode's Project Navigator (left sidebar), find **SafariWebExtensionHandler.swift** inside the **"Knowledge Repository Extension"** group. Open it, select all (⌘A), delete, and paste in the contents of the `SafariWebExtensionHandler.swift` file I sent alongside this one. Save (⌘S).

## 4. Turn on folder read/write for the extension

Click the **"Knowledge Repository Extension"** target (blue project icon at the top of the navigator → target list) → **Signing & Capabilities** tab. Under **App Sandbox**, find **File Access → User Selected File** and change it from "None" to **Read/Write**.

## 5. Set your signing team

Still in **Signing & Capabilities**, do this for *both* targets — "Knowledge Repository" (the app) and "Knowledge Repository Extension":

- Under **Signing**, set **Team** to your Apple ID.
- If no team is listed: Xcode menu → Settings → Accounts → **+** → sign in with your Apple ID. A free personal team is fine for this — it's just for running locally on your own Mac.

## 6. Build and run

At the top of the Xcode window, make sure the scheme is **"Knowledge Repository"** (the app, not the extension) and the destination is **My Mac**. Click the ▶ Run button.

This builds, signs, and launches the small container app — that's what registers the extension with Safari. You can quit that app afterward; it doesn't need to stay open.

## 7. Turn it on in Safari

Safari menu → **Settings** → **Extensions** tab → check the box next to **"Save to Knowledge Repository"**.

## 8. Test it

Select text on any page, right-click, choose **Save to Knowledge Repository**. First time, click **Choose folder…** and pick your working folder — that's a native macOS folder picker this time, not a browser one, but it works the same way: pick once, it's remembered.

## If something goes wrong

- **Build errors on the Swift file**: paste me the exact error text and I'll fix it — I can't compile Swift myself to catch every edge case in advance.
- **"Choose folder" does nothing / extension doesn't appear**: quit and re-run from Xcode (step 6), then re-check Safari's Extensions list.
- **Signing errors**: usually means step 5 wasn't applied to both targets, or you need to pick a real Team instead of "None".
