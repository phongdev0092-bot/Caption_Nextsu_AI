// ==========================================================
// COMPONENT: STUB TABS (5 chức năng Auto đang phát triển)
// Phân Công Tay / Bypass MyBAE / Pool-Deactive IPv6 /
// Hoàn Tất PTC-PBT / Cấp-Thu Hồi CCDC
//
// Khi làm chức năng thật: tạo static/js/components/<ten>.js riêng,
// gọi registerTab(...) và bỏ mục tương ứng khỏi STUB_TABS (index.html).
// ==========================================================

document.querySelectorAll('.stub-tab-panel').forEach(panel => {
  const key = panel.dataset.key;
  const $ = (suffix) => document.getElementById(`stub-${key}-${suffix}`);
  const btnRun = $('run');
  const btnAuto = $('auto-toggle');
  const autoText = $('auto-text');
  const autoDot = $('auto-dot');
  const logBox = $('log');
  const btnClearLog = $('clear-log');

  registerTab(panel.id);

  function appendLog(text) {
    if (!logBox) return;
    const row = document.createElement('div');
    row.textContent = `[${new Date().toLocaleTimeString('vi-VN')}] ${text}`;
    logBox.appendChild(row);
    logBox.scrollTop = logBox.scrollHeight;
  }

  if (btnRun) {
    btnRun.addEventListener('click', () => {
      appendLog('Chức năng đang phát triển — chưa có backend để thực thi.');
      showSnackbar('🚧 Chức năng này đang được phát triển.');
    });
  }

  if (btnAuto) {
    btnAuto.addEventListener('click', () => {
      showSnackbar('🚧 Chế độ Tự Động chưa khả dụng cho chức năng này.');
    });
  }

  if (btnClearLog && logBox) {
    btnClearLog.addEventListener('click', () => { logBox.innerHTML = ''; });
  }
});
