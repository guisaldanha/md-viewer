/* ================================================================
   MD Viewer — client-side logic
   Loaded inline after prism.min.js so Prism is always available.
================================================================ */

/* ----------------------------------------------------------------
   Toast helper  (used for reload indicator and "file not found")
---------------------------------------------------------------- */
var _toastTimer = null;
function showToast(msg, duration) {
  var el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  if (_toastTimer) clearTimeout(_toastTimer);
  _toastTimer = setTimeout(function () { el.classList.remove('show'); }, duration || 2000);
}
function showReloadToast() { showToast('\u21BB Reloading\u2026', 1200); }

/* ----------------------------------------------------------------
   MD link navigation
   Links like [install](install.md) get data-md-link="<abs_path>"
   injected by Python.  We intercept the click and ask Python to
   open the file (so relative assets in the new file resolve too).
---------------------------------------------------------------- */
document.getElementById('content').addEventListener('click', function (e) {
  var a = e.target.closest('a[data-md-link]');
  if (a) {
    e.preventDefault();
    window.pywebview.api.open_md_link(a.getAttribute('data-md-link'));
  }
});

/* ----------------------------------------------------------------
   Theme  (persisted in localStorage, respects prefers-color-scheme)
---------------------------------------------------------------- */
(function () {
  var saved = null;
  try { saved = localStorage.getItem('mdv-theme'); } catch (e) {}
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
  } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();

document.getElementById('btn-theme').addEventListener('click', function () {
  var cur  = document.documentElement.getAttribute('data-theme');
  var next = (cur === 'dark') ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('mdv-theme', next); } catch (e) {}
});

/* ----------------------------------------------------------------
   KaTeX math rendering
   Runs auto-render on #content to process $...$ and $$...$$ blocks.
   Degrades gracefully when katex / renderMathInElement are absent.
---------------------------------------------------------------- */
function renderMath() {
  if (typeof renderMathInElement === 'undefined') return;
  try {
    renderMathInElement(document.getElementById('content'), {
      delimiters: [
        { left: '$$', right: '$$', display: true  },
        { left: '$',  right: '$',  display: false },
        { left: '\\(', right: '\\)', display: false },
        { left: '\\[', right: '\\]', display: true  },
      ],
      throwOnError: false,
    });
  } catch (e) {
    console.warn('[MDViewer] KaTeX render error:', e);
  }
}

/* ----------------------------------------------------------------
   Mermaid diagram rendering
   Finds every <code class="language-mermaid"> block produced by the
   Markdown parser and replaces it with a <div class="mermaid"> that
   the mermaid library can render.  Degrades gracefully when
   mermaid.min.js is not present in the assets folder.
---------------------------------------------------------------- */
function renderMermaid() {
  if (typeof mermaid === 'undefined') return;

  var blocks = document.querySelectorAll('pre > code.language-mermaid');
  if (!blocks.length) return;

  blocks.forEach(function (code) {
    var pre     = code.parentNode;
    var source  = code.textContent;
    var div     = document.createElement('div');
    div.className = 'mermaid';
    div.textContent = source;
    pre.parentNode.replaceChild(div, pre);
  });

  /* mermaid.initialize must be called before run() on first use */
  try {
    mermaid.initialize({
      startOnLoad: false,
      theme: document.documentElement.getAttribute('data-theme') === 'light'
             ? 'default' : 'dark',
    });
    mermaid.run({ nodes: document.querySelectorAll('.mermaid') });
  } catch (e) {
    console.warn('[MDViewer] mermaid render error:', e);
  }
}

/* ----------------------------------------------------------------
   Content updater  (called from Python via evaluate_js on fresh
   file opens — always resets scroll to top)
---------------------------------------------------------------- */
function updateContent(contentHtml, tocHtml) {
  clearSearch();
  document.getElementById('content').innerHTML = contentHtml;
  Prism.highlightAll();
  renderMermaid();
  renderMath();
  document.getElementById('main').scrollTop = 0;

  /* Always rebuild TOC nav; user opens sidebar manually with T / button */
  document.getElementById('toc').innerHTML = tocHtml || '';
}

/* ----------------------------------------------------------------
   Reload updater  (called from Python via evaluate_js when the
   watched file changes — restores the previous scroll position so
   the viewport stays in place after an auto-reload)
---------------------------------------------------------------- */
function reloadContent(contentHtml, tocHtml) {
  var mainEl = document.getElementById('main');
  var savedScroll = mainEl.scrollTop;

  clearSearch();
  document.getElementById('content').innerHTML = contentHtml;
  Prism.highlightAll();
  renderMermaid();
  renderMath();

  /* Restore scroll three times:
     1. Immediately — catches cases where layout is already ready.
     2. First rAF   — after browser paint, handles most cases.
     3. Second rAF  — Prism's syntax highlighting can trigger a second
                      layout pass that resets scrollTop back to 0;
                      the nested rAF fires after that second pass. */
  mainEl.scrollTop = savedScroll;
  requestAnimationFrame(function () {
    mainEl.scrollTop = savedScroll;
    requestAnimationFrame(function () {
      mainEl.scrollTop = savedScroll;
    });
  });

  document.getElementById('toc').innerHTML = tocHtml || '';
}

/* ----------------------------------------------------------------
   File open
---------------------------------------------------------------- */
function openFile() { window.pywebview.api.open_file(); }

document.getElementById('btn-open').addEventListener('click', openFile);
document.getElementById('btn-edit').addEventListener('click', function () {
  window.pywebview.api.edit_file();
});

/* ----------------------------------------------------------------
   Export dropdown
---------------------------------------------------------------- */
(function () {
  var btn  = document.getElementById('btn-export');
  var menu = document.getElementById('export-menu');

  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    menu.classList.toggle('open');
  });

  /* Close when clicking anywhere outside */
  document.addEventListener('click', function () {
    menu.classList.remove('open');
  });

  function exportAction(apiMethod) {
    menu.classList.remove('open');
    window.pywebview.api[apiMethod]();
  }

  document.getElementById('btn-export-pdf') .addEventListener('click', function (e) { e.stopPropagation(); exportAction('export_pdf');  });
  document.getElementById('btn-export-html').addEventListener('click', function (e) { e.stopPropagation(); exportAction('export_html'); });
  document.getElementById('btn-export-docx').addEventListener('click', function (e) { e.stopPropagation(); exportAction('export_docx'); });
})();

/* ----------------------------------------------------------------
   Print
---------------------------------------------------------------- */
document.getElementById('btn-print').addEventListener('click', function () {
  window.print();
});

/* ----------------------------------------------------------------
   TOC sidebar toggle
---------------------------------------------------------------- */
document.getElementById('btn-toc').addEventListener('click', function () {
  document.getElementById('sidebar').classList.toggle('visible');
});

/* ----------------------------------------------------------------
   Search  (Ctrl+F)

   Walk text nodes inside #content, wrap every match with
   <mark class="hit">.  The current match gets class "cur" too.
   We keep a flat array of <mark> nodes for prev/next navigation.
   Prism span structure is preserved — we only split text nodes.
---------------------------------------------------------------- */
var _hits = [], _curIdx = -1, _lastQuery = '';

function clearSearch() {
  document.querySelectorAll('mark.hit').forEach(function (m) {
    var p = m.parentNode;
    while (m.firstChild) p.insertBefore(m.firstChild, m);
    p.removeChild(m);
    p.normalize();
  });
  _hits = []; _curIdx = -1; _lastQuery = '';
  document.getElementById('search-count').textContent = '';
}

function highlightQuery(query) {
  clearSearch();
  if (!query) return;
  _lastQuery = query;

  var walker = document.createTreeWalker(
    document.getElementById('content'), NodeFilter.SHOW_TEXT, null
  );
  var textNodes = [];
  var node;
  while ((node = walker.nextNode())) textNodes.push(node);

  var lq = query.toLowerCase();
  textNodes.forEach(function (tn) {
    var text  = tn.nodeValue;
    var lower = text.toLowerCase();
    var idx   = lower.indexOf(lq);
    if (idx === -1) return;

    var frag = document.createDocumentFragment();
    var pos  = 0;
    while (idx !== -1) {
      if (idx > pos) frag.appendChild(document.createTextNode(text.slice(pos, idx)));
      var mark = document.createElement('mark');
      mark.className   = 'hit';
      mark.textContent = text.slice(idx, idx + query.length);
      frag.appendChild(mark);
      _hits.push(mark);
      pos = idx + query.length;
      idx = lower.indexOf(lq, pos);
    }
    if (pos < text.length) frag.appendChild(document.createTextNode(text.slice(pos)));
    tn.parentNode.replaceChild(frag, tn);
  });

  updateCount();
  if (_hits.length) navigateTo(0);
}

function navigateTo(idx) {
  if (!_hits.length) return;
  if (_curIdx >= 0 && _curIdx < _hits.length)
    _hits[_curIdx].classList.remove('cur');
  _curIdx = (idx + _hits.length) % _hits.length;
  _hits[_curIdx].classList.add('cur');
  _hits[_curIdx].scrollIntoView({ block: 'center' });
  updateCount();
}

function updateCount() {
  var el = document.getElementById('search-count');
  if (!_lastQuery) { el.textContent = ''; return; }
  el.textContent = _hits.length
    ? (_curIdx + 1) + ' / ' + _hits.length
    : 'no results';
}

function openSearch() {
  document.getElementById('search-bar').style.display = 'flex';
  document.getElementById('search-input').focus();
}

function closeSearch() {
  document.getElementById('search-bar').style.display = 'none';
  document.getElementById('search-input').value = '';
  clearSearch();
}

document.getElementById('search-input').addEventListener('input', function () {
  highlightQuery(this.value.trim());
});
document.getElementById('btn-next').addEventListener('click', function () {
  navigateTo(_curIdx + 1);
});
document.getElementById('btn-prev').addEventListener('click', function () {
  navigateTo(_curIdx - 1);
});
document.getElementById('btn-search-close').addEventListener('click', closeSearch);

/* ----------------------------------------------------------------
   Keyboard shortcuts
---------------------------------------------------------------- */
document.addEventListener('keydown', function (e) {
  if (e.ctrlKey && e.key === 'o') { e.preventDefault(); openFile();   return; }
  if (e.ctrlKey && e.key === 'f') { e.preventDefault(); openSearch(); return; }

  /* E — edit in default editor (only when not typing in an input) */
  if (e.key === 'e' && e.target.tagName !== 'INPUT') {
    window.pywebview.api.edit_file();
    return;
  }

  /* Backspace — go back to previous file (only when not in an input) */
  if (e.key === 'Backspace' && e.target.tagName !== 'INPUT') {
    e.preventDefault();
    window.pywebview.api.go_back();
    return;
  }

  /* T — toggle TOC sidebar (only when not focused on an input) */
  if (e.key === 't' && e.target.tagName !== 'INPUT') {
    document.getElementById('sidebar').classList.toggle('visible');
    return;
  }

  /* Enter / Shift+Enter — navigate search results */
  if (e.key === 'Enter' &&
      document.getElementById('search-bar').style.display === 'flex') {
    e.preventDefault();
    navigateTo(e.shiftKey ? _curIdx - 1 : _curIdx + 1);
    return;
  }

  if (e.key === 'Escape') { closeSearch(); }
});

/* ----------------------------------------------------------------
   Drag-and-drop  (opens native dialog — browser hides full path)
---------------------------------------------------------------- */
document.addEventListener('dragover', function (e) { e.preventDefault(); });
document.addEventListener('drop', function (e) {
  e.preventDefault();
  var file = e.dataTransfer.files[0];
  if (file && file.name.toLowerCase().endsWith('.md')) openFile();
});