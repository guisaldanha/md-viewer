<div align="center">
  <h1>📝 MD Viewer</h1>
  <p><i>A fast, lightweight Markdown viewer for the desktop.</i></p>
</div>

## Overview

MD Viewer renders `.md` files as beautiful, styled HTML inside a native desktop window. No browser needed, no Electron overhead. Just open a file and read.

**v2.0 is a complete rewrite** focused on performance, GitHub-flavored Markdown compatibility, and a polished user experience.

---

## 📥 Download the Installer (Windows)

Just want to use MD Viewer without building from source?

Download the ready-to-use installer and start viewing your Markdown files in seconds:

<div align="center">
  <a href="https://github.com/guisaldanha/md-viewer/releases/latest/download/MDViewerSetup3.0.1.exe">
    <img src="assets/download-installer.png" alt="Installer MD Viewer" width="400">
  </a>
</div>

## ✨ Features

### Core
- ⚡ **Instant rendering** — HTML is cached by `(path, mtime)`, so reopening an unmodified file is instant with zero re-parsing
- 🔁 **Auto-reload** — powered by [watchdog](https://github.com/gorakhargosh/watchdog); any save in an external editor refreshes the preview automatically with a debounced 300 ms delay
- 🔗 **MD-to-MD navigation** — links like `[install](install.md)` open the linked file directly inside the viewer
- 🖼️ **Local image support** — relative paths like `./images/photo.png` are resolved to absolute `file://` URIs so embedded images always load correctly

### Markdown
- ✅ **Task lists** — `- [x] done` / `- [ ] todo`
- ~~**Strikethrough**~~ — `~~text~~`
- ==**Highlight**== — `==text==`
- 😄 **Emoji** — `:smile:` rendered as Unicode, fully offline
- 📊 **Tables**, **footnotes**, **definition lists**, **abbreviations**
- 🔣 **Fenced code blocks** with [Prism.js](https://prismjs.com/) syntax highlighting (GitHub style via `pymdownx.superfences`)
- 📐 **Math / LaTeX** — inline `$...$` and block `$$...$$` rendered by [KaTeX](https://katex.org/)
- 📈 **Mermaid diagrams** — ` ```mermaid ` blocks rendered by [Mermaid](https://mermaid.js.org/)
- 🔖 **Table of Contents** — add `[TOC]` anywhere in the document
- `[[WikiLinks]]` support
- **@mentions** — `@username` links to the GitHub profile
- **GFM autolinks** — bare `https://` and `www.` URLs become clickable links automatically

### Interface
- 🌙 **Dark / Light mode** toggle — respects `prefers-color-scheme` on first launch, persists your choice
- 🔍 **In-document search** (`Ctrl+F`) — highlights all matches, navigate with `Enter` / `Shift+Enter`, shows `X / total` count
- 📑 **TOC sidebar** — collapsible, populated automatically from document headings
- ✏️ **Edit button** — opens the current file in VSCode, Notepad++, or your available text editor
- 📤 **Export** — save as self-contained **HTML** or **DOCX** (via pypandoc), print/save as **PDF** through the OS print dialog

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| <kbd>Ctrl</kbd>+<kbd>O</kbd> | Open file |
| <kbd>Ctrl</kbd>+<kbd>F</kbd> | Search |
| <kbd>Enter</kbd> / <kbd>Shift</kbd>+<kbd>Enter</kbd> | Next / previous search result |
| <kbd>Esc</kbd> | Close search |
| <kbd>T</kbd> | Toggle TOC sidebar |
| <kbd>E</kbd> | Edit in external editor |
| <kbd>Backspace</kbd> | Go back to previous file |

---

## 🚀 Getting Started

### Requirements

- Python 3.11 or higher
- A Windows, macOS, or Linux desktop

### Installation

```bash
# Clone the repository
git clone https://github.com/guisaldanha/md-viewer.git
cd md-viewer

# Install dependencies
pip install pywebview markdown pymdown-extensions watchdog

# Optional: DOCX export
pip install pypandoc
```

### Run

```bash
python main.py

# Or open a specific file directly
python main.py path/to/document.md
```

---

## 📦 Building a Standalone Executable (Windows)

```bash
pip install pyinstaller

pyinstaller --windowed \
            --add-data "assets;assets" \
            --icon "assets\icon-mdviewer.ico" \
            --hidden-import=pymdownx.superfences \
            --hidden-import=pymdownx.highlight \
            --hidden-import=pymdownx.tasklist \
            --hidden-import=pymdownx.tilde \
            --hidden-import=pymdownx.emoji \
            --hidden-import=pymdownx.mark \
            --icon "assets\\icon-mdviewer.ico" \
            --name MDViewer \
            main.py
```

> On macOS / Linux replace the `;` separator in `--add-data` with `:`

### Associate `.md` files with MD Viewer (Windows)

Run once as Administrator after installing:

```bat
assoc .md=MDViewerFile
ftype MDViewerFile="C:\path\to\MDViewer.exe" "%1"
```

---

## 🏗️ Architecture

The v2 rewrite is organized around a few key principles:

**Single HTML shell** — The window loads one HTML page at startup with all CSS and Prism.js embedded inline. When a new file is opened, only the `innerHTML` of `#content` is swapped via `evaluate_js()` — no full page reloads, no CSS flash.

**Render cache** — Parsed HTML is stored in `_md_cache` keyed by `(abs_path, mtime)`. Navigating back to a previously visited file is instant. The watchdog invalidates the cache entry automatically on save.

**Reusable parser** — A single `markdown.Markdown()` instance is created at startup. Between documents, `md.reset()` clears per-document state (footnote counters, heading IDs, TOC tree) without rebuilding the extension objects, which is the expensive part.

**Native dialogs** — File open/save use pywebview's `create_file_dialog()` instead of `<input type="file">`, because the browser sandbox intentionally hides the full file path. Python needs it to resolve relative asset paths.

---

## 📦 Bundled Assets

The following third-party libraries are embedded inline in the shell HTML at runtime. All are distributed under the **MIT License**.

| File | Library | Version | License | Source |
|---|---|---|---|---|
| `prism.min.js` + `prism.min.css` | [Prism.js](https://prismjs.com/) | — | MIT | [github.com/PrismJS/prism](https://github.com/PrismJS/prism) |
| `mermaid.min.js` | [Mermaid](https://mermaid.js.org/) | — | MIT | [github.com/mermaid-js/mermaid](https://github.com/mermaid-js/mermaid) |
| `katex.min.js` + `katex.min.css` + `auto-render.min.js` | [KaTeX](https://katex.org/) | — | MIT | [github.com/KaTeX/KaTeX](https://github.com/KaTeX/KaTeX) |

> These files are **not included** in the repository — download them separately and place them in the `assets/` folder. See each project's repository for the exact license text.

---

## 🛠️ Optional Dependencies

| Package | Feature | Install |
|---|---|---|
| `pymdown-extensions` | Task lists, emoji, strikethrough, superfences | `pip install pymdown-extensions` |
| `watchdog` | Auto-reload on file save | `pip install watchdog` |
| `pypandoc` | DOCX export (auto-downloads pandoc binary on first use) | `pip install pypandoc` |

All optional — the app runs without them, features degrade gracefully.

---

## ⚠️ Windows Security Warning

Windows may flag the executable as potentially dangerous because it lacks a paid code-signing certificate. The source code is fully open — feel free to review it and build the executable yourself. Click **"Run anyway"** to proceed.

---

------------------------------------------------------------------------


## 👨‍💻 Author

Developed by **Guilherme Saldanha**

- GitHub: [https://github.com/guisaldanha](https://github.com/guisaldanha)
- Site: [https://guisaldanha.com](https://guisaldanha.com)

------------------------------------------------------------------------

# ❤️ Support the Developer

If this project saves you time or helps your workflow, consider supporting its development.

Ways to help:

- ⭐ Star the repository
- 🔁 Share with other developers
- ☕ Buy me a coffee by [clicking here (PayPal)](https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business=guisaldanha@gmail.com&item_name=Buy%20a%20coffee%20because%20MD%20Viewer)

------------------------------------------------------------------------

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

------------------------------------------------------------------------
<div align="center">
  <p>Made with ☕ by Guilherme Saldanha</p>
</div>