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
function showSnackbar(msg) {
  const bar = document.getElementById('muiSnackbar');
  const txt = document.getElementById('snackbarText');
  if (bar && txt) {
    txt.textContent = msg;
    bar.classList.add('open');
    setTimeout(() => bar.classList.remove('open'), 3200);
  }
}
