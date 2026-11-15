// ==========================================================
// CORE: STORAGE, SESSION MONITOR, TOAST
// ==========================================================

// ----------------- STORAGE & SESSION MONITOR -----------------
async function updateStorageInfo() {
  try {
    const res = await fetch('/api/retrieval/storage-info');
    if (res.ok) {
      const d = await res.json();
      const cnt = d.records_count || 0;
      if (zstdCount) zstdCount.textContent = cnt;
      if (sidebarZstdCount) sidebarZstdCount.textContent = cnt;
      
      let sizeStr = '0 B';
      const bytes = d.compressed_bytes || 0;
      if (bytes < 1024) sizeStr = `${bytes} B`;
      else if (bytes < 1024 * 1024) sizeStr = `${(bytes / 1024).toFixed(1)} KB`;
      else sizeStr = `${(bytes / (1024 * 1024)).toFixed(2)} MB`;

      if (zstdSize) zstdSize.textContent = sizeStr;
      if (sidebarZstdSize) sidebarZstdSize.textContent = sizeStr;
    }
  } catch (e) {}
}

async function checkSessionStatus(showAlert = false) {
  if (sessionDot) sessionDot.className = 'session-dot checking';
  if (sessionLabel) sessionLabel.textContent = 'Đang kiểm tra...';
  if (sidebarSessionDot) sidebarSessionDot.className = 'session-dot checking';
  if (sidebarSessionLabel) sidebarSessionLabel.textContent = 'Kiểm tra...';

  try {
    const res = await fetch('/api/session/check');
    const d = await res.json();
    if (d.is_alive) {
      if (sessionDot) sessionDot.className = 'session-dot alive';
      if (sessionLabel) sessionLabel.textContent = 'Phiên Khả Dụng';
      if (sidebarSessionDot) sidebarSessionDot.className = 'session-dot alive';
      if (sidebarSessionLabel) sidebarSessionLabel.textContent = 'Khả Dụng';
      if (showAlert) showSnackbar(d.message || 'Phiên Inside FPT đang hoạt động!');
    } else {
      if (sessionDot) sessionDot.className = 'session-dot expired';
      if (sessionLabel) sessionLabel.textContent = 'Phiên Hết Hạn';
      if (sidebarSessionDot) sidebarSessionDot.className = 'session-dot expired';
      if (sidebarSessionLabel) sidebarSessionLabel.textContent = 'Hết Hạn';
      if (showAlert) showSnackbar(d.message || 'Phiên hết hạn, vui lòng bấm Đăng Nhập!');
    }
  } catch (e) {
    if (sessionDot) sessionDot.className = 'session-dot unknown';
    if (sessionLabel) sessionLabel.textContent = 'Kiểm Tra Lại';
    if (sidebarSessionDot) sidebarSessionDot.className = 'session-dot unknown';
    if (sidebarSessionLabel) sidebarSessionLabel.textContent = 'Kiểm Tra';
  }
}

if (btnCheckSession) {
  btnCheckSession.addEventListener('click', () => checkSessionStatus(true));
}
if (sidebarSessionBtn) {
  sidebarSessionBtn.addEventListener('click', () => checkSessionStatus(true));
}

// Sidebar Collapse / Expand Toggle
if (btnCollapseSidebar && appSidebar) {
  btnCollapseSidebar.addEventListener('click', () => {
    appSidebar.classList.toggle('collapsed');
  });
}

if (btnToggleSidebarMobile && appSidebar) {
  btnToggleSidebarMobile.addEventListener('click', () => {
    appSidebar.classList.toggle('mobile-open');
  });
}

if (btnSidebarSwitchAcc) {
  btnSidebarSwitchAcc.addEventListener('click', () => {
    if (settingsModalBackdrop) settingsModalBackdrop.classList.add('open');
  });
}

if (btnSidebarSettings) {
  btnSidebarSettings.addEventListener('click', () => {
    if (settingsModalBackdrop) settingsModalBackdrop.classList.add('open');
  });
}

if (btnDownloadTemplate) {
  btnDownloadTemplate.addEventListener('click', (e) => {
    e.preventDefault();
    window.location.href = '/api/retrieval/template';
  });
}

// ----------------- TOAST / SNACKBAR -----------------
let _snackbarTimer = null;
function showSnackbar(msg) {
  const bar = document.getElementById('muiSnackbar');
  const txt = document.getElementById('snackbarText');
  if (bar && txt) {
    txt.textContent = msg;
    bar.classList.remove('toast-success', 'toast-warning', 'toast-error', 'toast-info');
    const lower = String(msg || '').toLowerCase();
    if (
      lower.includes('lỗi') || lower.includes('không thể') || lower.includes('thất bại') ||
      lower.includes('hết hạn') || lower.includes('❌') || lower.includes('⛔')
    ) {
      bar.classList.add('toast-error');
    } else if (
      lower.includes('đang chạy') || lower.includes('bận') || lower.includes('vui lòng đợi') ||
      lower.includes('chưa có') || lower.includes('⚠') || lower.includes('⏳')
    ) {
      bar.classList.add('toast-warning');
    } else if (
      lower.includes('thành công') || lower.includes('hoàn tất') || lower.includes('đã lưu') ||
      lower.includes('đã bật') || lower.includes('khả dụng') || lower.includes('✓') || lower.includes('✅')
    ) {
      bar.classList.add('toast-success');
    } else {
      bar.classList.add('toast-info');
    }
    bar.classList.add('open');
    if (_snackbarTimer) clearTimeout(_snackbarTimer);
    _snackbarTimer = setTimeout(() => bar.classList.remove('open'), 3600);
  }
}

// ----------------- DARK MODE & UI POLISH SYNC -----------------
(function initThemeAndUiPolish() {
  const root = document.documentElement;
  const btnTheme = document.getElementById('btnThemeToggle');
  const iconTheme = document.getElementById('themeToggleIcon');

  function applyTheme(theme) {
    const isDark = theme === 'dark';
    root.classList.toggle('dark', isDark);
    if (iconTheme) iconTheme.textContent = isDark ? 'light_mode' : 'dark_mode';
    if (btnTheme) {
      btnTheme.setAttribute('title', isDark ? 'Chuyển sang giao diện Sáng' : 'Chuyển sang giao diện Tối');
    }
  }

  let savedTheme = null;
  try {
    savedTheme = localStorage.getItem('uiTheme');
  } catch (e) {}

  if (savedTheme === 'dark' || savedTheme === 'light') {
    applyTheme(savedTheme);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    applyTheme('dark');
  }

  if (btnTheme) {
    btnTheme.addEventListener('click', () => {
      const next = root.classList.contains('dark') ? 'light' : 'dark';
      applyTheme(next);
      try {
        localStorage.setItem('uiTheme', next);
      } catch (e) {}
    });
  }

  const SCOPE_LABELS = {
    today: 'Theo bộ lọc: Hôm nay',
    '7days': 'Theo bộ lọc: 7 ngày',
    '30days': 'Theo bộ lọc: 30 ngày',
    all: 'Theo bộ lọc: Toàn Sheet'
  };

  function syncScopeBadges() {
    document.querySelectorAll('.kpi-scope-badge[data-scope-select]').forEach(badge => {
      const selId = badge.getAttribute('data-scope-select');
      const sel = selId ? document.getElementById(selId) : null;
      if (sel) {
        const val = sel.value || 'today';
        badge.textContent = SCOPE_LABELS[val] || 'Theo bộ lọc';
      }
    });
  }

  function syncSidebarAutoDots() {
    const map = [
      { id: 'sidebarAutoBypassBadge', mode: () => typeof autoBypassMode !== 'undefined' && autoBypassMode, run: () => typeof isBypassRunning !== 'undefined' && isBypassRunning },
      { id: 'sidebarAutoClsBadge', mode: () => typeof autoClsMode !== 'undefined' && autoClsMode, run: () => typeof isClsRunning !== 'undefined' && isClsRunning },
      { id: 'sidebarAutoAssignBadge', mode: () => typeof autoAssignMode !== 'undefined' && autoAssignMode, run: () => typeof isAssignRunning !== 'undefined' && isAssignRunning },
      { id: 'sidebarAutoClearSignalBadge', mode: () => typeof autoClearSignalMode !== 'undefined' && autoClearSignalMode, run: () => typeof isClearSignalRunning !== 'undefined' && isClearSignalRunning },
      { id: 'sidebarAutoResetSignalBadge', mode: () => typeof autoResetSignalMode !== 'undefined' && autoResetSignalMode, run: () => typeof isResetSignalRunning !== 'undefined' && isResetSignalRunning },
      { id: 'sidebarAutoMyBaeBadge', mode: () => typeof autoMyBaeMode !== 'undefined' && autoMyBaeMode, run: () => typeof isMyBaeRunning !== 'undefined' && isMyBaeRunning },
      { id: 'sidebarAutoSpamPoolBadge', mode: () => typeof autoSpamPoolMode !== 'undefined' && autoSpamPoolMode, run: () => typeof isSpamPoolRunning !== 'undefined' && isSpamPoolRunning },
      { id: 'sidebarAutoBypassNatBadge', mode: () => typeof autoBypassNatMode !== 'undefined' && autoBypassNatMode, run: () => typeof isBypassNatRunning !== 'undefined' && isBypassNatRunning },
      { id: 'sidebarAutoPortBadge', mode: () => typeof autoPortMode !== 'undefined' && autoPortMode, run: () => typeof isPortRunning !== 'undefined' && isPortRunning }
    ];
    map.forEach(item => {
      const el = document.getElementById(item.id);
      if (!el) return;
      const isOn = !!item.mode();
      const isRun = !!item.run();
      if (isRun) {
        el.setAttribute('data-auto-state', 'running');
        el.setAttribute('title', 'Đang chạy tác vụ');
      } else if (isOn) {
        el.setAttribute('data-auto-state', 'on');
        el.setAttribute('title', 'Chế độ Auto: Đang bật');
      } else {
        el.removeAttribute('data-auto-state');
        el.setAttribute('title', 'Chế độ Auto: Đang tắt');
      }
    });
  }

  function enhanceDataTables() {
    document.querySelectorAll('.mui-table, table.w-full.text-left.border-collapse').forEach(tbl => {
      const headers = Array.from(tbl.querySelectorAll('thead th'));
      let shdIdx = -1;
      let actionTextIdx = -1;
      headers.forEach((th, idx) => {
        const txt = (th.textContent || '').trim().toLowerCase();
        if (shdIdx === -1 && (txt.includes('số hợp đồng') || txt === 'shd' || txt.includes('số hđ'))) {
          shdIdx = idx;
          th.classList.add('col-sticky-shd');
        }
        if (txt === 'thao tác' || txt.includes('thao tác / log')) {
          actionTextIdx = idx;
        }
      });
      if (shdIdx >= 0 || actionTextIdx >= 0) {
        tbl.querySelectorAll('tbody tr').forEach(tr => {
          const cells = tr.children;
          if (!cells || cells.length <= 1) return;
          if (shdIdx >= 0 && cells[shdIdx]) {
            cells[shdIdx].classList.add('col-sticky-shd');
          }
          if (actionTextIdx >= 0 && cells[actionTextIdx]) {
            const td = cells[actionTextIdx];
            const fullText = (td.textContent || '').trim();
            if (fullText && !td.getAttribute('title')) {
              td.setAttribute('title', fullText);
            }
          }
        });
      }
    });
  }

  document.addEventListener('change', (e) => {
    if (e.target && e.target.tagName === 'SELECT') {
      syncScopeBadges();
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    syncScopeBadges();
    syncSidebarAutoDots();
    enhanceDataTables();
    setInterval(() => {
      syncScopeBadges();
      syncSidebarAutoDots();
      enhanceDataTables();
    }, 1500);
  });
})();
