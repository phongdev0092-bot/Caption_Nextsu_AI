// ==========================================================
// CORE: TAB REGISTRY & NAVIGATION
// Mỗi component đăng ký tab của mình bằng registerTab().
// Nút sidebar chỉ cần thuộc tính data-tab="<id panel>".
// ==========================================================

const tabRegistry = {};

/**
 * @param {string} panelId   id của <section class="tab-panel">
 * @param {{title?: string, onActivate?: Function}} meta
 */
function registerTab(panelId, meta = {}) {
  tabRegistry[panelId] = meta;
}

function switchTab(targetTab) {
  document.querySelectorAll('.sidebar-nav-item[data-tab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === targetTab);
    btn.setAttribute('aria-selected', btn.dataset.tab === targetTab ? 'true' : 'false');
  });
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === targetTab);
  });

  const meta = tabRegistry[targetTab] || {};
  const navBtn = document.querySelector(`.sidebar-nav-item[data-tab="${targetTab}"]`);
  const title = meta.title || (navBtn && navBtn.dataset.title) || '';
  if (topbarCurrentTitle && title) topbarCurrentTitle.textContent = title;

  if (typeof meta.onActivate === 'function') meta.onActivate();

  if (window.innerWidth <= 1024 && appSidebar) {
    appSidebar.classList.remove('mobile-open');
  }
}

document.querySelectorAll('.sidebar-nav-item[data-tab]').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

if (btnBackToBypass) {
  btnBackToBypass.addEventListener('click', () => switchTab('tab-tasks'));
}

registerTab('tab-retrieval', { title: 'Auto Lấy Thông Tin' });
registerTab('tab-import', { title: 'Auto Import' });
