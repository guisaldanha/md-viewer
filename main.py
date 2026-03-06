"""
# =============================================================================
# MDViewer
# Copyright (c) 2024 Guilherme Saldanha — https://guisaldanha.com
# Licensed under the MIT License.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
# =============================================================================
"""

"""
# DEPENDENCIES (required):
#   pip install pywebview markdown pymdown-extensions watchdog
#
# DEPENDENCIES (optional — features degrade gracefully without them):
#   pip install pypandoc        # DOCX export (also auto-downloads pandoc binary
#                               # on first use via pypandoc.download_pandoc())
#
# COMPILE (single executable, Windows):
#   pip install pyinstaller
# =============================================================================
"""

"""
1. Limpa a pasta dist antiga
Remove-Item -Recurse -Force .\\dist -ErrorAction SilentlyContinue

2. Compila o Python para Executável usando PyInstaller:
pyinstaller --windowed --add-data "assets;assets" --hidden-import=pymdownx.superfences --hidden-import=pymdownx.highlight --hidden-import=pymdownx.tasklist --hidden-import=pymdownx.tilde --hidden-import=pymdownx.emoji --icon "assets\\icon-mdviewer.ico" --name MDViewer main.py

  Linux/macOS: replace semicolon with colon in --add-data

3. Copia a pasta 'assets' para dentro da 'dist\\MDViewer'
Copy-Item -Path ".\\assets" -Destination ".\\dist\\MDViewer\\assets" -Recurse -Force

4. Gera o Instalador do Windows
& "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" "InnoSetup\\installer-script.iss"
"""

import json
import os
import re
import sys
import threading
from pathlib import Path

import markdown
import webview

# pymdownx is optional — degrade gracefully if not installed
try:
    import pymdownx.emoji as _pymdownx_emoji
    _PYMDOWNX_AVAILABLE = True
except ImportError:
    _PYMDOWNX_AVAILABLE = False

# watchdog is optional — auto-reload disabled when absent
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler as _FSEventHandler
    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False
    _FSEventHandler = object   # harmless base for the stub class below

# pypandoc is optional — DOCX export disabled when absent
try:
    import pypandoc as _pypandoc
    _PYPANDOC_AVAILABLE = True
except ImportError:
    _PYPANDOC_AVAILABLE = False


class _FileChangeHandler(_FSEventHandler):
    """
    Watchdog handler that fires a debounced callback when a specific file
    is modified or atomically replaced (write-to-temp + rename pattern used
    by most editors: VSCode, vim, Sublime, etc.).

    Debounce of 300 ms collapses bursts of rapid events into a single reload.
    """

    def __init__(self, filepath: str, callback) -> None:
        if _WATCHDOG_AVAILABLE:
            super().__init__()
        self._filepath = os.path.abspath(filepath)
        self._callback = callback
        self._timer: threading.Timer | None = None

    # watchdog calls these on the observer thread
    def on_modified(self, event) -> None:
        if not event.is_directory and os.path.abspath(event.src_path) == self._filepath:
            self._debounce()

    def on_moved(self, event) -> None:
        # Atomic-save: editor writes tmp → renames to target
        if hasattr(event, "dest_path") and os.path.abspath(event.dest_path) == self._filepath:
            self._debounce()

    def _debounce(self) -> None:
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(0.3, self._callback)
        self._timer.daemon = True
        self._timer.start()


def _emoji_to_unicode(
    index, shortname, alias, uc, alt, title, category, options, md
) -> str:
    """
    Render GitHub emojis as plain Unicode characters.
    Avoids any external CDN — works fully offline.
    Falls back to the :shortcode: text when no Unicode char exists.
    """
    return alt if alt else shortname


class MDViewer:
    VERSION = "3.0.0"

    # ------------------------------------------------------------------ #
    #  Markdown extension list                                             #
    #                                                                      #
    #  NOTE: 'extra' is NOT used as a bundle here because it includes     #
    #  'fenced_code', which conflicts with pymdownx.superfences.          #
    #  Instead we list extra's sub-extensions individually.               #
    # ------------------------------------------------------------------ #
    _BASE_EXTENSIONS = [
        # --- ex-'extra' components (minus fenced_code) ---
        "abbr",        # *[HTML]: HyperText Markup Language
        "attr_list",   # {.class #id attr=value} on elements
        "def_list",    # definition lists
        "footnotes",   # [^1] footnote syntax
        "md_in_html",  # Markdown inside HTML blocks (markdown="1")
        "tables",      # | col | col |
        # --- standalone ---
        "nl2br",       # single newline -> <br>
        "sane_lists",  # fixes list edge-cases
        "toc",         # [TOC] macro + md.toc attribute
        "wikilinks",   # [[WikiLinks]]
    ]

    _PYMDOWNX_EXTENSIONS = [
        "pymdownx.superfences",  # better fenced code blocks (GitHub style)
        "pymdownx.tasklist",     # - [x] / - [ ] checkboxes
        "pymdownx.tilde",        # ~~strikethrough~~ and ~subscript~
        "pymdownx.mark",         # ==highlight== syntax
        "pymdownx.emoji",        # :smile: :rocket: etc.
    ]

    # ------------------------------------------------------------------ #

    def __init__(self, file_path: str | None = None) -> None:
        self.file_path = file_path
        self.base_dir  = self._resolve_base_dir()
        self._asset_cache: dict[str, str] = {}
        self._current_file: str | None = None   # absolute path of the open file
        self._history: list[str] = []            # navigation back-stack
        self._observer = None                   # watchdog Observer | None

        # Render cache: abs_path -> (mtime, content_html, toc_html)
        # Invalidated automatically when mtime changes (e.g. after a save).
        self._md_cache: dict[str, tuple[float, str, str]] = {}

        # Build the final extension list once at startup
        self._extensions = list(self._BASE_EXTENSIONS)
        self._ext_configs: dict = {}

        if _PYMDOWNX_AVAILABLE:
            self._extensions.extend(self._PYMDOWNX_EXTENSIONS)
            self._ext_configs = {
                "pymdownx.tasklist": {
                    "custom_checkbox": True,   # renders styled <label>+<input>
                    "clickable_checkbox": False,
                },
                "pymdownx.emoji": {
                    "emoji_index":     _pymdownx_emoji.gemoji,
                    "emoji_generator": _emoji_to_unicode,
                },
            }
        else:
            # Fall back to built-in fenced_code when pymdownx is absent
            self._extensions.append("fenced_code")
            print(
                "[MDViewer] pymdownx not found — task lists, superfences, highlight, emoji and "
                "strikethrough are disabled.\n"
                "           Install with: pip install pymdownx",
                file=sys.stderr,
            )

        # Single parser instance, reused via .reset() between documents.
        # Extensions are instantiated once here — this is the real cost.
        # .reset() clears per-document state (footnote counters, refs, TOC…)
        # without re-building the extension objects.
        self._md_parser = markdown.Markdown(
            extensions=self._extensions,
            extension_configs=self._ext_configs,
        )

    # ------------------------------------------------------------------ #
    #  Path / file helpers                                                 #
    # ------------------------------------------------------------------ #

    def _resolve_base_dir(self) -> str:
        """
        Return the directory that contains the assets/ folder.

        PyInstaller bundle modes:
          --onefile  ->  assets land in sys._MEIPASS (temp extraction dir)
          --onedir   ->  assets sit next to the .exe
        """
        if getattr(sys, "frozen", False):
            if hasattr(sys, "_MEIPASS"):
                return sys._MEIPASS          # type: ignore[attr-defined]
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _read_asset(self, filename: str) -> str:
        """Read an asset file once; return cached string on subsequent calls."""
        if filename not in self._asset_cache:
            path = os.path.join(self.base_dir, "assets", filename)
            try:
                with open(path, encoding="utf-8") as fh:
                    self._asset_cache[filename] = fh.read()
            except OSError as exc:
                self._asset_cache[filename] = (
                    f"/* Could not load {filename}: {exc} */"
                )
        return self._asset_cache[filename]

    def _read_file(self, file_path: str) -> str:
        """Read a user-supplied Markdown file."""
        try:
            with open(file_path, encoding="utf-8") as fh:
                return fh.read()
        except OSError as exc:
            return f"# Error opening file\n\n```\n{exc}\n```"

    # ------------------------------------------------------------------ #
    #  Markdown processing                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _preprocess_md(md_content: str) -> str:
        """
        CommonMark-compatible pre-processing for features python-markdown skips.

        - Backslash hard line break (spec 6.7):
            '\\' at end of line -> two trailing spaces -> <br>
        - <details> / <summary> blocks:
            Inject markdown="1" so md_in_html processes the inner content.
            Without this attribute the extension leaves the block as raw HTML
            and lists, emphasis, code etc. inside are not rendered.
        - @mention (GFM):
            @username -> [@username](https://github.com/username)
        """
        # Backslash hard line break
        result = re.sub(r"\\\n", "  \n", md_content)

        # Auto-inject markdown="1" on <details> tags that don't already have it
        result = re.sub(
            r'<details(?![^>]*\bmarkdown\b)([^>]*)>',
            r'<details markdown="1"\1>',
            result,
            flags=re.IGNORECASE,
        )

        # Protect $$...$$ display math blocks from the Markdown parser.
        # python-markdown mangles backslashes and wraps content in <p> tags
        # before KaTeX gets a chance to render it.
        # Solution: convert to a raw <div class="math-block"> which md_in_html
        # and the block parser both leave completely untouched.
        result = re.sub(
            r'\$\$\s*\n([\s\S]*?)\n\s*\$\$',
            lambda m: f'<div class="math-block">$$\n{m.group(1)}\n$$</div>',
            result,
        )

        # GFM autolink literals — convert bare URLs to Markdown links so the
        # parser renders them as clickable anchors, matching GitHub behaviour:
        #   https://example.com  ->  [https://example.com](https://example.com)
        #   http://example.com   ->  [http://example.com](http://example.com)
        #   www.example.com      ->  [www.example.com](http://www.example.com)
        #
        # Negative lookbehind avoids double-processing URLs already inside
        # Markdown links (](, src=", href=") or angle-bracket autolinks (<).
        result = re.sub(
            r'(?<![(\[<"\'])(?<!\]\()(https?://[^\s\)\]"\'<>]+)',
            lambda m: f'[{m.group(1)}]({m.group(1)})',
            result,
        )
        result = re.sub(
            r'(?<![(\[<"\'/])(www\.[A-Za-z0-9\-]+\.[^\s\)\]"\'<>]+)',
            lambda m: f'[{m.group(1)}](http://{m.group(1)})',
            result,
        )

        # @mention -> GitHub profile link (GFM behaviour)
        # Negative lookbehind avoids matching inside URLs (github.com/@user)
        # or existing Markdown links. GitHub username rules: 1-39 chars,
        # alphanumeric + hyphens, no leading/trailing hyphen.
        result = re.sub(
            r'(?<![=/\w@])@([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)',
            r'[@\1](https://github.com/\1)',
            result,
        )

        return result

    def _md_to_html(self, md_content: str) -> tuple[str, str]:
        """
        Convert Markdown to HTML using the shared parser instance.

        .reset() clears per-document state (footnote counters, heading ids,
        reference links, TOC tree…) so each call is independent, while the
        extension objects themselves — the expensive part — are built only once.

        Returns (content_html, toc_html).
        toc_html is an empty string when the document has no headings.
        """
        self._md_parser.reset()
        content_html = self._md_parser.convert(self._preprocess_md(md_content))
        toc_html     = getattr(self._md_parser, "toc", "")
        return content_html, toc_html

    @staticmethod
    def _process_links(html: str, base_dir: str) -> str:
        """
        Process every <a href="..."> in the HTML fragment:

        ┌─────────────────────┬──────────────────────────────────────────┐
        │ href pattern        │ treatment                                │
        ├─────────────────────┼──────────────────────────────────────────┤
        │ #anchor             │ kept as-is  (in-page scroll)             │
        │ relative *.md       │ data-md-link="<abs_path>"  (JS opens it) │
        │ relative non-.md    │ resolved to file:// and opened externally│
        │ http(s):// etc.     │ target="_blank"  (opens in system browser)│
        └─────────────────────┴──────────────────────────────────────────┘
        """
        external = ("http://", "https://", "mailto:", "ftp://")

        def handle(m: re.Match) -> str:
            prefix = m.group(1)   # everything before href value, e.g. '<a '
            href   = m.group(2)
            suffix = m.group(3)   # everything after href value

            # In-page anchor — untouched
            if href.startswith("#"):
                return m.group(0)

            # External URL — new tab
            if href.startswith(external):
                return f'{prefix}href="{href}" target="_blank"{suffix}'

            # Already absolute file:// — new tab
            if href.startswith("file://"):
                return f'{prefix}href="{href}" target="_blank"{suffix}'

            # Relative path — resolve and decide
            resolved = (Path(base_dir) / href).resolve()
            if resolved.suffix.lower() == ".md":
                # Intercept in JS → open via Python (gives us the full path)
                abs_str = str(resolved).replace("\\", "/")
                return f'{prefix}href="#" data-md-link="{abs_str}"{suffix}'

            # Other relative link (PDF, HTML…) — open externally as file://
            return f'{prefix}href="{resolved.as_uri()}" target="_blank"{suffix}'

        # Match the opening tag up to (not including) the closing >
        return re.sub(r'(<a\s[^>]*?)href="([^"]*)"([^>]*>)', handle, html)

    @staticmethod
    def _resolve_asset_paths(html: str, base_dir: str) -> str:
        """
        Embed local images as base64 data: URIs directly in the HTML.

        Why base64 instead of file:// URIs
        ------------------------------------
        pywebview loads the shell via load_html(string), which gives the page
        a null origin.  WebView2 (Edge, used on Windows) blocks cross-origin
        file:// resource loads from a null-origin page, so <img src="file:///...">
        silently fails.  Embedding as data: URIs sidesteps all security
        restrictions — the image bytes travel inside the HTML itself.

        Handles:
          • Relative paths   → resolved against base_dir, embedded as base64
          • Absolute paths   → embedded as base64 if the file exists
          • http(s)://       → left unchanged (remote images load fine)
          • data:            → already embedded, left unchanged
          • file://          → converted to base64 (legacy / other callers)

        MIME type is inferred from the file extension; falls back to
        image/png for unknown types.
        """
        import base64
        import mimetypes

        _MIME_MAP = {
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif":  "image/gif",
            ".webp": "image/webp",
            ".svg":  "image/svg+xml",
            ".ico":  "image/x-icon",
            ".bmp":  "image/bmp",
        }

        skip_prefix = ("http://", "https://", "data:")

        def embed(m: re.Match) -> str:
            raw = m.group(1)

            # Remote or already-embedded — leave untouched
            if raw.startswith(skip_prefix):
                return m.group(0)

            # Resolve the path to an absolute filesystem path
            if raw.startswith("file://"):
                # Strip file:// prefix (handles file:///C:/... on Windows too)
                local_path = Path(raw[7:].lstrip("/"))
                # Re-add drive letter on Windows: file:///C:/... → C:/...
                if raw.startswith("file:///") and len(raw) > 10 and raw[8].isalpha() and raw[9] == ":":
                    local_path = Path(raw[8:])
            else:
                local_path = (Path(base_dir) / raw).resolve()

            if not local_path.is_file():
                return m.group(0)   # file not found — leave as-is

            ext  = local_path.suffix.lower()
            mime = _MIME_MAP.get(ext) or mimetypes.guess_type(str(local_path))[0] or "image/png"
            try:
                data = base64.b64encode(local_path.read_bytes()).decode("ascii")
            except OSError:
                return m.group(0)

            return f'src="data:{mime};base64,{data}"'

        return re.sub(r'src="([^"]*)"', embed, html)

    # ------------------------------------------------------------------ #
    #  HTML shell                                                          #
    # ------------------------------------------------------------------ #

    def _shell_html(self) -> str:
        """
        Build the one-time HTML page loaded into the WebView window.

        Layout
        ------
        +-- #toolbar -----------------------------------------------+
        |  [= TOC]  [Open]  [search bar]                   [theme]  |
        +-----------------------------------------------------------+
        +-- #layout ------------------------------------------------+
        |  +-- #sidebar --+  +-- #main -------------------------+   |
        |  |   nav#toc    |  |   div#content                    |   |
        |  +--------------+  +---------------------------------+    |
        +-----------------------------------------------------------+

        All CSS lives in assets/style.css; all JS in assets/viewer.js.
        Both are read once, cached, and embedded inline so the page is
        fully self-contained (no external file: requests at runtime).
        Content is injected via updateContent() / reloadContent()
        without a full page reload.
        """
        style      = self._read_asset("style.css")
        prism_css  = self._read_asset("prism.min.css")
        katex_css  = self._read_asset("katex.min.css")
        prism_js   = self._read_asset("prism.min.js")
        viewer_js  = self._read_asset("viewer.js")
        mermaid_js = self._read_asset("mermaid.min.js")
        katex_js   = self._read_asset("katex.min.js")
        katex_ar   = self._read_asset("auto-render.min.js")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
{style}
{prism_css}
{katex_css}
  </style>
</head>
<body>

  <!-- ── Toolbar ── -->
  <div id="toolbar">
    <button id="btn-toc"  title="Toggle table of contents (T)">&#8801; TOC</button>
    <button id="btn-open" title="Open file (Ctrl+O)">Open&#8230;</button>
    <button id="btn-edit" title="Edit in default editor (E)">&#9998; Edit</button>

    <!-- Export dropdown -->
    <div class="dropdown" id="export-dropdown">
      <button id="btn-export" title="Export document">Export &#9660;</button>
      <div class="dropdown-menu" id="export-menu">
        <button id="btn-export-pdf"  title="Export as PDF">&#128462; PDF</button>
        <button id="btn-export-html" title="Export as HTML">&#128196; HTML</button>
        <button id="btn-export-docx" title="Export as DOCX">&#128196; DOCX</button>
      </div>
    </div>

    <button id="btn-print" title="Print (Ctrl+P)">&#128424; Print</button>

    <div id="search-bar">
      <input id="search-input" type="text" placeholder="Search&#8230;" autocomplete="off">
      <span  id="search-count"></span>
      <button id="btn-prev" title="Previous (Shift+Enter)">&#8593;</button>
      <button id="btn-next" title="Next (Enter)">&#8595;</button>
      <button id="btn-search-close" title="Close (Esc)">&#10005;</button>
    </div>

    <div class="spacer"></div>
    <button id="btn-theme" title="Toggle dark/light mode">&#9790;</button>
  </div>

  <!-- ── Layout ── -->
  <div id="layout">
    <aside id="sidebar">
      <div id="toc-title">Contents</div>
      <nav id="toc"></nav>
    </aside>
    <div id="main">
      <div id="content"></div>
    </div>
  </div>

  <div id="toast"></div>

  <script>
{prism_js}
{mermaid_js}
{katex_js}
{katex_ar}
{viewer_js}
  </script>
</body>
</html>"""

    # ------------------------------------------------------------------ #
    #  File watching (auto-reload)                                         #
    # ------------------------------------------------------------------ #

    def _stop_watching(self) -> None:
        """Stop the current watchdog observer, if any."""
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=2)
            except Exception:
                pass
            self._observer = None

    def _start_watching(self, file_path: str) -> None:
        """
        Watch *file_path* for changes and reload automatically.

        watchdog observes directories, not individual files, so we schedule
        on the parent directory and filter inside _FileChangeHandler.
        The Observer thread is daemonized so it never blocks shutdown.
        """
        if not _WATCHDOG_AVAILABLE:
            return
        self._stop_watching()
        handler  = _FileChangeHandler(file_path, self._reload_current)
        observer = Observer()
        observer.schedule(
            handler,
            path=os.path.dirname(os.path.abspath(file_path)),
            recursive=False,
        )
        observer.daemon = True
        observer.start()
        self._observer = observer

    def _reload_current(self) -> None:
        """Called by watchdog (on its thread) when the watched file changes."""
        if self._current_file:
            # Invalidate the cache entry so _load_file re-parses the new content
            self._md_cache.pop(self._current_file, None)
            try:
                webview.windows[0].evaluate_js("showReloadToast()")
            except Exception:
                pass
            self._load_file(self._current_file, preserve_scroll=True)

    # ------------------------------------------------------------------ #
    #  Content loading                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _welcome_content() -> tuple[str, str]:
        html = """
<div style="display:flex;flex-direction:column;justify-content:center;
            align-items:center;min-height:80vh;text-align:center;gap:14px;">
  <h2 style="margin:0;">Markdown Viewer</h2>
  <p>Press <kbd>Ctrl+O</kbd> or click the button below to open a file.</p>
  <p>You can also <strong>drag and drop</strong> a <code>.md</code> file onto this window.</p>
  <button onclick="openFile()" style="padding:8px 20px;cursor:pointer;">
    Open file&#8230;
  </button>
</div>"""
        return html, ""

    def _load_file(self, file_path: str, preserve_scroll: bool = False,
                   _history_push: bool = True) -> None:
        """
        Read -> preprocess -> convert -> process links -> resolve asset
        paths -> inject into the WebView.  Always called with a full
        absolute path so every relative reference can be resolved.

        Results are cached by (abs_path, mtime).  Opening the same
        unmodified file a second time (e.g. navigating back) is instant —
        no disk read, no markdown parse, no regex passes.
        The cache entry is automatically stale after a save because mtime
        changes, so auto-reload always gets fresh HTML.

        preserve_scroll=True uses reloadContent() in JS, which saves and
        restores the scroll position so the viewport stays in place after
        a watchdog-triggered auto-reload.

        _history_push=False skips adding the current file to the back-stack
        (used when navigating backwards so we don't re-push).
        """
        abs_path = os.path.abspath(file_path)
        base_dir = os.path.dirname(abs_path)

        # Push current file onto the back-stack before switching
        if _history_push and self._current_file and self._current_file != abs_path:
            self._history.append(self._current_file)

        try:
            mtime = os.path.getmtime(abs_path)
        except OSError:
            mtime = 0.0

        cached = self._md_cache.get(abs_path)
        if cached and cached[0] == mtime:
            content_html, toc_html = cached[1], cached[2]
        else:
            md_raw = self._read_file(abs_path)
            content_html, toc_html = self._md_to_html(md_raw)
            content_html = self._process_links(content_html, base_dir)
            content_html = self._resolve_asset_paths(content_html, base_dir)
            self._md_cache[abs_path] = (mtime, content_html, toc_html)

        self._current_file = abs_path
        webview.windows[0].set_title(
            f"MD Viewer — {os.path.basename(abs_path)}"
        )
        js_fn = "reloadContent" if preserve_scroll else "updateContent"
        webview.windows[0].evaluate_js(
            f"{js_fn}({json.dumps(content_html)}, {json.dumps(toc_html)})"
        )
        self._start_watching(abs_path)

    # ------------------------------------------------------------------ #
    #  Public JS API                                                       #
    # ------------------------------------------------------------------ #

    def open_file(self) -> None:
        """
        Open a native file-picker dialog from JavaScript.

        The native dialog (not <input type=file>) is required because the
        browser sandbox hides the full file path — Python needs it to resolve
        relative asset paths like ./images/photo.png.
        """
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Markdown files (*.md)", "All files (*.*)"),
        )
        if result:
            self._load_file(result[0])

    # ------------------------------------------------------------------ #
    #  Export helpers                                                      #
    # ------------------------------------------------------------------ #

    def _build_export_html(self) -> tuple[str, str]:
        """
        Build a clean, fully self-contained HTML document for export.

        Returns (html_string, file_stem).
        Embeds all CSS inline; contains no JS or toolbar chrome —
        suitable for PDF rendering, HTML save, or pandoc input.
        """
        if not self._current_file:
            return "", ""
        cached = self._md_cache.get(self._current_file)
        if not cached:
            return "", ""

        _, content_html, _ = cached
        title     = os.path.basename(self._current_file)
        style     = self._read_asset("style.css")
        prism_css = self._read_asset("prism.min.css")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    {style}
    {prism_css}

    /* ── Export overrides ──────────────────────────────────────────
       The shared style.css is written for the viewer shell, where
       only #main scrolls and html/body are overflow:hidden.
       In a standalone export there is no shell, so we undo every
       layout rule that would break a normal scrollable page.
    ─────────────────────────────────────────────────────────────── */
    html, body {{
      overflow: visible !important;
      height:   auto    !important;
    }}
    body {{
      margin:    40px auto !important;
      max-width: 900px     !important;
      padding:   0 24px    !important;
    }}
    #content {{
      max-width: 100% !important;
      padding:   0    !important;
      margin:    0    !important;
    }}
  </style>
</head>
<body>
<div id="content">
{content_html}
</div>
</body>
</html>"""
        return html, Path(self._current_file).stem

    @staticmethod
    def _save_dialog(filename: str, file_types: tuple) -> str | None:
        """Open a native Save dialog and return the chosen path, or None."""
        try:
            # pywebview >= 4.x
            dialog_type = webview.FileDialog.SAVE
        except AttributeError:
            # pywebview 3.x fallback
            dialog_type = webview.SAVE_DIALOG  # type: ignore[attr-defined]
        result = webview.windows[0].create_file_dialog(
            dialog_type,
            save_filename=filename,
            file_types=file_types,
        )
        if not result:
            return None
        return result[0] if isinstance(result, (list, tuple)) else result

    def _no_file_guard(self) -> bool:
        """Show a toast and return True when no file is currently open."""
        if not self._current_file:
            webview.windows[0].evaluate_js(
                "showToast('Open a Markdown file first')"
            )
            return True
        return False

    # ------------------------------------------------------------------ #
    #  Public JS API — Export & Print                                      #
    # ------------------------------------------------------------------ #

    def export_html(self) -> None:
        """Export the rendered document as a self-contained HTML file."""
        if self._no_file_guard():
            return
        html, stem = self._build_export_html()
        path = self._save_dialog(
            f"{stem}.html", ("HTML files (*.html)", "All files (*.*)")
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
            webview.windows[0].evaluate_js("showToast('Saved as HTML \u2713')")
        except OSError as exc:
            webview.windows[0].evaluate_js(
                f"showToast({json.dumps(f'HTML export failed: {exc}')})"
            )

    def export_pdf(self) -> None:
        """
        Export as PDF via the OS print dialog.

        Opens the browser print dialog — on Windows 10/11 choose
        "Microsoft Print to PDF"; on macOS choose "Save as PDF" in
        the bottom-left dropdown of the print sheet.
        No external libraries required.
        """
        if self._no_file_guard():
            return
        webview.windows[0].evaluate_js(
            "showToast('Use \u201cSave as PDF\u201d in the print dialog', 3000);"
            "setTimeout(function(){ window.print(); }, 600);"
        )

    def export_docx(self) -> None:
        """
        Export as DOCX via pypandoc.

        pypandoc can download the pandoc binary automatically on first use
        (no manual install needed).  Requires: pip install pypandoc
        """
        if self._no_file_guard():
            return

        if not _PYPANDOC_AVAILABLE:
            webview.windows[0].evaluate_js(
                "showToast('DOCX export needs pypandoc: pip install pypandoc', 4000)"
            )
            return

        # Ensure the pandoc binary exists — download it automatically if not
        try:
            _pypandoc.get_pandoc_version()
        except OSError:
            try:
                webview.windows[0].evaluate_js(
                    "showToast('Downloading pandoc (first use)\u2026', 15000)"
                )
                _pypandoc.download_pandoc()
            except Exception as exc:
                webview.windows[0].evaluate_js(
                    f"showToast({json.dumps(f'Could not get pandoc: {str(exc)[:60]}')})"
                )
                return

        path = self._save_dialog(
            f"{Path(self._current_file).stem}.docx",
            ("Word documents (*.docx)", "All files (*.*)")
        )
        if not path:
            return
        try:
            webview.windows[0].evaluate_js("showToast('Generating DOCX\u2026', 10000)")
            _pypandoc.convert_file(self._current_file, "docx", outputfile=path)
            webview.windows[0].evaluate_js("showToast('Saved as DOCX \u2713')")
        except Exception as exc:
            webview.windows[0].evaluate_js(
                f"showToast({json.dumps(f'DOCX error: {str(exc)[:60]}')})"
            )

    def edit_file(self) -> None:
        """
        Open the current file in a text editor.

        os.startfile() is intentionally NOT used — it would reopen MDViewer
        itself when MDViewer is the default handler for .md files.

        Strategy (Windows):
          1. Check PATH for known editor commands (works if user added them)
          2. Check the most common installation directories on disk
          3. Fall back to notepad.exe (always present on Windows)

        macOS / Linux: VSCode → system default text editor.
        """
        if self._no_file_guard():
            return

        import subprocess
        import shutil

        f = self._current_file

        def _try(*cmd: str) -> bool:
            try:
                # .cmd / .bat files require shell=True on Windows to execute
                needs_shell = sys.platform == "win32" and cmd[0].lower().endswith((".cmd", ".bat"))
                subprocess.Popen(list(cmd), shell=needs_shell)
                return True
            except (FileNotFoundError, OSError):
                return False

        def _find_win(*candidates: str) -> str | None:
            """Return the first candidate path that exists on disk."""
            for p in candidates:
                if os.path.isfile(p):
                    return p
            return None

        if sys.platform == "win32":
            # ── 1. Try PATH first — use resolved path so .cmd files are handled ──
            code_path = shutil.which("code")
            if code_path and _try(code_path, f): return

            npp_path = shutil.which("notepad++")
            if npp_path and _try(npp_path, f): return

            # ── 2. Search common installation directories on disk ──
            local  = os.environ.get("LOCALAPPDATA", "")
            prog   = os.environ.get("ProgramFiles",  "C:\\Program Files")
            prog86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")

            vscode = _find_win(
                os.path.join(local,  "Programs", "Microsoft VS Code", "Code.exe"),
                os.path.join(prog,   "Microsoft VS Code", "Code.exe"),
                os.path.join(prog86, "Microsoft VS Code", "Code.exe"),
            )
            if vscode and _try(vscode, f): return

            npp = _find_win(
                os.path.join(prog,   "Notepad++", "notepad++.exe"),
                os.path.join(prog86, "Notepad++", "notepad++.exe"),
            )
            if npp and _try(npp, f): return

            sublime = _find_win(
                os.path.join(prog,   "Sublime Text", "sublime_text.exe"),
                os.path.join(prog86, "Sublime Text", "sublime_text.exe"),
                os.path.join(local,  "Programs", "Sublime Text", "sublime_text.exe"),
            )
            if sublime and _try(sublime, f): return

            # ── 3. Guaranteed fallback ──
            _try("notepad.exe", f)

        elif sys.platform == "darwin":
            code_path = shutil.which("code")
            if code_path and _try(code_path, f): return
            _try("open", "-e", f)   # TextEdit

        else:
            for editor in ("code", "gedit", "kate", "mousepad", "geany"):
                p = shutil.which(editor)
                if p and _try(p, f): return
            _try("xdg-open", f)

    def open_md_link(self, abs_path: str) -> None:
        """
        Navigate to a linked .md file (called from JS when the user clicks
        a data-md-link anchor).  abs_path is the resolved absolute path
        injected by _process_links — no further path resolution needed.
        """
        norm = os.path.normpath(abs_path)
        if os.path.isfile(norm):
            self._load_file(norm)
        else:
            webview.windows[0].evaluate_js(
                f"showToast({json.dumps(f'File not found: {os.path.basename(norm)}')})"
            )

    def go_back(self) -> None:
        """
        Navigate to the previous file in the back-stack (Backspace shortcut).
        Does nothing when the history is empty.
        """
        if not self._history:
            webview.windows[0].evaluate_js("showToast('No previous file')")
            return
        prev = self._history.pop()
        if os.path.isfile(prev):
            self._load_file(prev, _history_push=False)
        else:
            webview.windows[0].evaluate_js(
                f"showToast({json.dumps(f'File not found: {os.path.basename(prev)}')})"
            )

    # ------------------------------------------------------------------ #
    #  Bootstrap                                                           #
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  Shell cache helpers                                                 #
    # ------------------------------------------------------------------ #

    # Assets that make up the shell — if any of them changes on disk the
    # cached HTML file is considered stale and rebuilt.
    _SHELL_ASSETS = [
        "style.css",
        "prism.min.css",
        "katex.min.css",
        "prism.min.js",
        "mermaid.min.js",
        "katex.min.js",
        "auto-render.min.js",
        "viewer.js",
    ]

    def _shell_mtime(self) -> float:
        """
        Return the maximum mtime across all shell assets.
        Missing files contribute 0.0 (treated as very old — not stale).
        """
        best = 0.0
        for name in self._SHELL_ASSETS:
            path = os.path.join(self.base_dir, "assets", name)
            try:
                best = max(best, os.path.getmtime(path))
            except OSError:
                pass
        return best

    def _shell_cache_path(self) -> str:
        """
        Persistent cache file next to main.py (or the .exe in a frozen build).
        Named mdviewer_shell.html so it is easy to identify and delete manually.
        """
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "mdviewer_shell.html")

    def _get_shell_path(self) -> str:
        """
        Return a file path to the shell HTML, rebuilding only when any shell
        asset is newer than the cached file.  On first run (or after an asset
        update) the file is written; subsequent launches reuse it instantly.
        """
        cache_path = self._shell_cache_path()
        asset_mtime = self._shell_mtime()

        try:
            cache_mtime = os.path.getmtime(cache_path)
            cache_valid = cache_mtime >= asset_mtime
        except OSError:
            cache_valid = False

        if not cache_valid:
            html = self._shell_html()
            with open(cache_path, "w", encoding="utf-8") as fh:
                fh.write(html)

        return cache_path

    # ------------------------------------------------------------------ #
    #  Bootstrap                                                           #
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        title = (
            f"MD Viewer — {os.path.basename(self.file_path)}"
            if self.file_path else "MD Viewer"
        )

        # Reuse the cached shell file when assets haven't changed — avoids
        # reading + concatenating several MB of JS/CSS on every launch.
        shell_path = self._get_shell_path()

        if sys.platform == "win32":
            shell_url = "file:///" + shell_path.replace("\\", "/")
        else:
            shell_url = "file://" + shell_path

        window = webview.create_window(
            title=title,
            url=shell_url,
            js_api=self,
            text_select=True,
            min_size=(760, 520),
            width=1200,
            height=800,
        )

        def on_loaded() -> None:
            if self.file_path:
                self._load_file(self.file_path)
            else:
                content_html, toc_html = self._welcome_content()
                window.evaluate_js(
                    f"updateContent({json.dumps(content_html)}, {json.dumps(toc_html)})"
                )

        def on_closed() -> None:
            self._stop_watching()

        window.events.loaded += on_loaded
        window.events.closed += on_closed
        webview.start()


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    MDViewer(file_path).run()