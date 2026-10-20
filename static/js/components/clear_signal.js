// ==========================================================
// COMPONENT: AUTO CLEAR TÍN HIỆU (tab-clear-signal)
// Sheet GID: 0 (Sheet ID: 1dXsWnon9myjDlcWM6BRLqDt_pxWBmTYFgb17k7R24vc)
// ==========================================================

const badgeClearSignalPending       = document.getElementById('badgeClearSignalPending');
const clearSignalStatTotal          = document.getElementById('clearSignalStatTotal');
const clearSignalStatPending        = document.getElementById('clearSignalStatPending');
const clearSignalStatDone           = document.getElementById('clearSignalStatDone');
const clearSignalStatError          = document.getElementById('clearSignalStatError');
const chkClearSignalVisible         = document.getElementById('chkClearSignalVisible');
const btnRunAutoClearSignal         = document.getElementById('btnRunAutoClearSignal');
const clearSignalSpinner            = document.getElementById('clearSignalSpinner');
const clearSignalRunIcon            = document.getElementById('clearSignalRunIcon');
const clearSignalRunText            = document.getElementById('clearSignalRunText');
const clearSignalProgressTracker    = document.getElementById('clearSignalProgressTracker');
const clearSignalTrackerStatus      = document.getElementById('clearSignalTrackerStatus');
const clearSignalTrackerPercent     = document.getElementById('clearSignalTrackerPercent');
const clearSignalProgressBar        = document.getElementById('clearSignalProgressBar');
const inputSearchClearSignal        = document.getElementById('inputSearchClearSignal');
const selectClearSignalFilterStatus = document.getElementById('selectClearSignalFilterStatus');
const chkClearSignalSelectAll       = document.getElementById('chkClearSignalSelectAll');
const tbodyClearSignalList          = document.getElementById('tbodyClearSignalList');
const clearSignalTableFooterText    = document.getElementById('clearSignalTableFooterText');
const clearSignalSelectedCountText  = document.getElementById('clearSignalSelectedCountText');
const btnRefreshClearSignalSheetData= document.getElementById('btnRefreshClearSignalSheetData');
const btnExportClearSignalData      = document.getElementById('btnExportClearSignalData');
const inputClearSignalWebhookUrl    = document.getElementById('inputClearSignalWebhookUrl');
const btnSaveClearSignalWebhook     = document.getElementById('btnSaveClearSignalWebhook');
const clearSignalWebhookStatusBadge = document.getElementById('clearSignalWebhookStatusBadge');
const btnAutoClearSignalModeToggle  = document.getElementById('btnAutoClearSignalModeToggle');
const autoClearSignalModeIcon       = document.getElementById('autoClearSignalModeIcon');
const autoClearSignalModeText       = document.getElementById('autoClearSignalModeText');
const autoClearSignalModeDot        = document.getElementById('autoClearSignalModeDot');
const clearSignalLogTerminal        = document.getElementById('clearSignalLogTerminal');
const btnClearClearSignalLogs       = document.getElementById('btnClearClearSignalLogs');

let currentClearSignalRecords  = [];
let selectedClearSignalShds    = new Set();
let isClearSignalRunning       = false;
autoClearSignalMode            = localStorage.getItem('autoClearSignalMode') !== 'false'; // Mặc định là BẬT
autoClearSignalCountdownTimer  = null;
autoClearSignalCountdown       = 0;

// ===================== WEBHOOK =====================
async function initClearSignalWebhook() {
  try {
    let saved = '';
    const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
    saved = cfg.clear_signal_webhook_url || '';
    if (!saved) {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        saved = data.clear_signal_webhook_url || data.google_sheet_webhook_url || '';
        cfg.clear_signal_webhook_url = saved;
        localStorage.setItem('appConfig', JSON.stringify(cfg));
      }
    }
    if (inputClearSignalWebhookUrl && saved) {
      inputClearSignalWebhookUrl.value = saved;
      if (clearSignalWebhookStatusBadge) {
        clearSignalWebhookStatusBadge.textContent = '✓ Đã kết nối Webhook';
        clearSignalWebhookStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200';
      }
    }
  } catch (e) {}
}
initClearSignalWebhook();

if (btnSaveClearSignalWebhook) {
  btnSaveClearSignalWebhook.addEventListener('click', async () => {
    const url = inputClearSignalWebhookUrl ? inputClearSignalWebhookUrl.value.trim() : '';
    try {
      const res = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clear_signal_webhook_url: url })
      });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        showSnackbar('💾 Đã lưu Webhook Clear Tín Hiệu!');
        if (clearSignalWebhookStatusBadge) {
          clearSignalWebhookStatusBadge.textContent = url ? '✓ Đã kết nối Webhook' : '⚠ Chưa cấu hình Webhook';
          clearSignalWebhookStatusBadge.className = url
            ? 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200'
            : 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200';
        }
        try {
          const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
          cfg.clear_signal_webhook_url = url;
          localStorage.setItem('appConfig', JSON.stringify(cfg));
        } catch(e) {}
      } else {
        showSnackbar('❌ ' + (data.message || 'Không thể lưu Webhook'));
      }
    } catch (e) {
      showSnackbar('❌ Lỗi kết nối khi lưu Webhook');
    }
  });
}

// ===================== AUTO MODE =====================
function updateAutoClearSignalModeUI() {
  if (!btnAutoClearSignalModeToggle) return;
  const sidebarBadge = document.getElementById('sidebarAutoClearSignalBadge');
  if (autoClearSignalMode) {
    btnAutoClearSignalModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-teal-500 bg-teal-50 text-teal-700 transition-all shadow-sm animate-pulse cursor-pointer';
    if (autoClearSignalModeText) autoClearSignalModeText.textContent = 'Tự Động: BẬT';
    if (autoClearSignalModeDot) autoClearSignalModeDot.className = 'w-2 h-2 rounded-full bg-teal-600 transition-all animate-bounce';
    if (sidebarBadge) sidebarBadge.classList.remove('hidden');
  } else {
    btnAutoClearSignalModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-slate-200 bg-white text-slate-600 hover:border-teal-400 hover:bg-teal-50 hover:text-teal-700 transition-all shadow-sm cursor-pointer';
    if (autoClearSignalModeText) autoClearSignalModeText.textContent = 'Tự Động: TẮT';
    if (autoClearSignalModeDot) autoClearSignalModeDot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all';
    if (sidebarBadge) sidebarBadge.classList.add('hidden');
  }
}
updateAutoClearSignalModeUI();

if (btnAutoClearSignalModeToggle) {
  btnAutoClearSignalModeToggle.addEventListener('click', () => {
    autoClearSignalMode = !autoClearSignalMode;
    localStorage.setItem('autoClearSignalMode', autoClearSignalMode ? 'true' : 'false');
    updateAutoClearSignalModeUI();
    if (autoClearSignalMode) {
      showSnackbar('🤖 Chế độ Tự Động Clear Tín Hiệu đã BẬT!');
      checkAndAutoTriggerClearSignal();
    } else {
      showSnackbar('Chế độ Tự Động Clear Tín Hiệu đã TẮT.');
      if (autoClearSignalCountdownTimer) {
        clearInterval(autoClearSignalCountdownTimer);
        autoClearSignalCountdownTimer = null;
        if (autoClearSignalModeText) autoClearSignalModeText.textContent = 'Tự Động: TẮT';
      }
    }
  });
}

function _isClearSignalFinalDone(r) {
  const kq = String(r['Kết Quả'] || '').trim().toLowerCase();
  return kq.includes('thành công') || kq.includes('đã xử lý') || kq.includes('lỗi') || kq.includes('thất bại') || kq.includes('không thành công');
}

function checkAndAutoTriggerClearSignal() {
  if (!autoClearSignalMode || isClearSignalRunning) return;
  const pending = currentClearSignalRecords.filter(r => !_isClearSignalFinalDone(r));
  if (pending.length === 0) return;
  if (autoClearSignalCountdownTimer) return;

  autoClearSignalCountdown = 3;
  if (autoClearSignalModeText) autoClearSignalModeText.textContent = `Tự Động: chạy sau ${autoClearSignalCountdown}s...`;
  showSnackbar(`🤖 Phát hiện ${pending.length} hợp đồng Clear Tín Hiệu chưa xử lý - Tự khởi động sau 3 giây...`);

  autoClearSignalCountdownTimer = setInterval(() => {
    autoClearSignalCountdown--;
    if (autoClearSignalCountdown > 0) {
      if (autoClearSignalModeText) autoClearSignalModeText.textContent = `Tự Động: chạy sau ${autoClearSignalCountdown}s...`;
    } else {
      clearInterval(autoClearSignalCountdownTimer);
      autoClearSignalCountdownTimer = null;
      if (autoClearSignalModeText) autoClearSignalModeText.textContent = 'Tự Động: BẬT';
      if (!isClearSignalRunning) {
        executeClearSignalProcess(null);
      }
    }
  }, 1000);
}

// ===================== DATA LOADING & RENDERING =====================
async function loadClearSignalSheetData() {
  try {
    const res = await fetch('/api/clear-signal/sheet-data?gid=0');
    if (!res.ok) return;
    const data = await res.json();
    if (data.status !== 'ok') return;

    currentClearSignalRecords = data.records || [];
    renderClearSignalTable();
    updateClearSignalKPIs();

    if (autoClearSignalMode && !isClearSignalRunning && !autoClearSignalCountdownTimer) {
      const pendingCount = currentClearSignalRecords.filter(r => !_isClearSignalFinalDone(r)).length;
      if (pendingCount > 0) {
        checkAndAutoTriggerClearSignal();
      }
    }
  } catch (err) {}
}

function updateClearSignalKPIs() {
  const total = currentClearSignalRecords.length;
  let done = 0, error = 0, pending = 0;

  currentClearSignalRecords.forEach(r => {
    const kq = String(r['Kết Quả'] || '').trim().toLowerCase();
    if (kq.includes('thành công') || kq.includes('đã xử lý')) {
      done++;
    } else if (kq.includes('lỗi') || kq.includes('thất bại') || kq.includes('không thành công')) {
      error++;
    } else {
      pending++;
    }
  });

  if (clearSignalStatTotal)   clearSignalStatTotal.textContent   = total;
  if (clearSignalStatPending) clearSignalStatPending.textContent = pending;
  if (clearSignalStatDone)    clearSignalStatDone.textContent    = done;
  if (clearSignalStatError)   clearSignalStatError.textContent   = error;
  if (badgeClearSignalPending)badgeClearSignalPending.textContent= `${pending} chờ xử lý`;
}

function renderClearSignalTable() {
  if (!tbodyClearSignalList) return;

  const keyword = inputSearchClearSignal ? inputSearchClearSignal.value.trim().toLowerCase() : '';
  const filterStatus = selectClearSignalFilterStatus ? selectClearSignalFilterStatus.value : 'all';

  const filtered = currentClearSignalRecords.filter(r => {
    if (filterStatus === 'pending' && _isClearSignalFinalDone(r)) return false;
    if (filterStatus === 'done' && !String(r['Kết Quả'] || '').toLowerCase().includes('thành công') && !String(r['Kết Quả'] || '').toLowerCase().includes('đã xử lý')) return false;
    if (filterStatus === 'error' && !String(r['Kết Quả'] || '').toLowerCase().includes('lỗi') && !String(r['Kết Quả'] || '').toLowerCase().includes('thất bại')) return false;

    if (!keyword) return true;
    const shd = String(r['SHD'] || '').toLowerCase();
    const ten = String(r['Họ và Tên'] || '').toLowerCase();
    const mail= String(r['Email'] || '').toLowerCase();
    const mac = String(r['MAC'] || '').toLowerCase();
    return shd.includes(keyword) || ten.includes(keyword) || mail.includes(keyword) || mac.includes(keyword);
  });

  if (clearSignalTableFooterText) {
    clearSignalTableFooterText.textContent = `Hiển thị ${filtered.length} / ${currentClearSignalRecords.length} bản ghi`;
  }
  if (clearSignalSelectedCountText) {
    clearSignalSelectedCountText.textContent = `(${selectedClearSignalShds.size} HĐ đã chọn)`;
  }

  if (filtered.length === 0) {
    tbodyClearSignalList.innerHTML = `
      <tr>
        <td colspan="9" class="text-center py-8 text-slate-400">
          Không tìm thấy hợp đồng Clear Tín Hiệu phù hợp
        </td>
      </tr>`;
    return;
  }

  tbodyClearSignalList.innerHTML = filtered.map((r, idx) => {
    const shd = r['SHD'] || '';
    const isChecked = selectedClearSignalShds.has(shd) ? 'checked' : '';
    const kq = r['Kết Quả'] || '';
    const kqLower = kq.toLowerCase();

    let badgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
    let badgeText = kq || 'Chưa xử lý';

    if (kqLower.includes('thành công') || kqLower.includes('đã xử lý')) {
      badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    } else if (kqLower.includes('lỗi') || kqLower.includes('thất bại') || kqLower.includes('không thành công')) {
      badgeClass = 'bg-rose-50 text-rose-700 border-rose-200';
    }

    return `
      <tr class="hover:bg-teal-50/40 transition-colors border-b border-slate-100">
        <td class="p-3 text-center">
          <input type="checkbox" class="chk-clear-signal-row rounded text-teal-600" data-shd="${shd}" ${isChecked}>
        </td>
        <td class="p-3 text-center font-semibold text-slate-500">${idx + 1}</td>
        <td class="p-3 font-semibold text-slate-800">${r['Họ và Tên'] || '-'}</td>
        <td class="p-3 text-slate-600 text-xs">${r['Email'] || '-'}</td>
        <td class="p-3 font-mono font-bold text-teal-700">${shd || '-'}</td>
        <td class="p-3 font-mono text-xs text-slate-700 bg-slate-50 px-2 py-1 rounded inline-block my-2 border border-slate-200">${r['MAC'] || '-'}</td>
        <td class="p-3 text-slate-500 text-xs">${r['Ngày Cập Nhật'] || '-'}</td>
        <td class="p-3 text-center">
          <span class="inline-block px-2.5 py-1 text-[11px] font-semibold rounded-full border ${badgeClass}">
            ${badgeText}
          </span>
        </td>
        <td class="p-3 text-center">
          <button type="button" class="btn-run-single-clear-signal px-2 py-1 bg-teal-50 text-teal-700 hover:bg-teal-100 rounded text-xs font-semibold border border-teal-200 transition-all cursor-pointer" data-shd="${shd}">
            ⚡ Chạy
          </button>
        </td>
      </tr>
    `;
  }).join('');

  // Row selection handler
  tbodyClearSignalList.querySelectorAll('.chk-clear-signal-row').forEach(cb => {
    cb.addEventListener('change', (e) => {
      const shd = e.target.dataset.shd;
      if (e.target.checked) selectedClearSignalShds.add(shd);
      else selectedClearSignalShds.delete(shd);
      if (clearSignalSelectedCountText) clearSignalSelectedCountText.textContent = `(${selectedClearSignalShds.size} HĐ đã chọn)`;
    });
  });

  // Single run handler
  tbodyClearSignalList.querySelectorAll('.btn-run-single-clear-signal').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const shd = e.currentTarget.dataset.shd;
      const targetRecord = currentClearSignalRecords.find(r => r['SHD'] === shd);
      if (targetRecord) executeClearSignalProcess([targetRecord]);
    });
  });
}

// Select all checkbox
if (chkClearSignalSelectAll) {
  chkClearSignalSelectAll.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    if (isChecked) {
      currentClearSignalRecords.forEach(r => { if (r['SHD']) selectedClearSignalShds.add(r['SHD']); });
    } else {
      selectedClearSignalShds.clear();
    }
    renderClearSignalTable();
  });
}

if (inputSearchClearSignal) inputSearchClearSignal.addEventListener('input', renderClearSignalTable);
if (selectClearSignalFilterStatus) selectClearSignalFilterStatus.addEventListener('change', renderClearSignalTable);
if (btnRefreshClearSignalSheetData) {
  btnRefreshClearSignalSheetData.addEventListener('click', () => {
    showSnackbar('🔄 Đang tải lại dữ liệu Clear Tín Hiệu từ Google Sheet...');
    loadClearSignalSheetData();
  });
}

// ===================== EXECUTION RUNNER =====================
async function executeClearSignalProcess(selectedRecords = null) {
  if (isClearSignalRunning) {
    showSnackbar('⚠️ Đang có tiến trình Clear Tín Hiệu đang chạy...');
    return;
  }

  const isVisible = chkClearSignalVisible ? chkClearSignalVisible.checked : false;

  let recordsToRun = selectedRecords;
  if (!recordsToRun) {
    if (selectedClearSignalShds.size > 0) {
      recordsToRun = currentClearSignalRecords.filter(r => selectedClearSignalShds.has(r['SHD']));
    } else {
      recordsToRun = currentClearSignalRecords.filter(r => !_isClearSignalFinalDone(r));
      if (recordsToRun.length === 0) recordsToRun = currentClearSignalRecords;
    }
  }

  if (!recordsToRun || recordsToRun.length === 0) {
    showSnackbar('Không tìm thấy hợp đồng nào để xử lý');
    return;
  }

  setClearSignalRunningState(true);
  showSnackbar(`🚀 Bắt đầu xử lý ${recordsToRun.length} hợp đồng Clear Tín Hiệu...`);

  try {
    const res = await fetch('/api/clear-signal/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        records: recordsToRun,
        headless: !isVisible
      })
    });
    const data = await res.json();
    if (!res.ok) {
      showSnackbar('❌ ' + (data.message || 'Lỗi khởi chạy'));
      setClearSignalRunningState(false);
    }
  } catch (err) {
    showSnackbar('❌ Lỗi kết nối máy chủ');
    setClearSignalRunningState(false);
  }
}

if (btnRunAutoClearSignal) {
  btnRunAutoClearSignal.addEventListener('click', () => executeClearSignalProcess(null));
}

function setClearSignalRunningState(running) {
  isClearSignalRunning = running;
  if (running) {
    if (clearSignalSpinner) clearSignalSpinner.style.display = 'inline-block';
    if (clearSignalRunIcon) clearSignalRunIcon.style.display = 'none';
    if (clearSignalRunText) clearSignalRunText.textContent = 'Đang Xử Lý...';
    if (btnRunAutoClearSignal) btnRunAutoClearSignal.disabled = true;
    if (clearSignalProgressTracker) clearSignalProgressTracker.style.display = 'block';
  } else {
    if (clearSignalSpinner) clearSignalSpinner.style.display = 'none';
    if (clearSignalRunIcon) clearSignalRunIcon.style.display = 'inline-block';
    if (clearSignalRunText) clearSignalRunText.textContent = 'Bắt Đầu Clear Tín Hiệu';
    if (btnRunAutoClearSignal) btnRunAutoClearSignal.disabled = false;
    if (clearSignalProgressTracker) clearSignalProgressTracker.style.display = 'none';
  }
}

// ===================== STATUS POLLING & LOGS =====================
async function pollClearSignalStatus() {
  try {
    const res = await fetch('/api/clear-signal/live-status');
    if (!res.ok) return;
    const data = await res.json();
    const task = data.task || {};

    if (task.is_running) {
      if (!isClearSignalRunning) setClearSignalRunningState(true);
      const total = task.total || 1;
      const idx = task.current_index || 0;
      const pct = Math.round((idx / total) * 100);

      if (clearSignalTrackerPercent) clearSignalTrackerPercent.textContent = `${pct}%`;
      if (clearSignalProgressBar) clearSignalProgressBar.style.width = `${pct}%`;
      if (clearSignalTrackerStatus) clearSignalTrackerStatus.textContent = task.message || `Đang xử lý ${idx}/${total}...`;
    } else {
      if (isClearSignalRunning) {
        setClearSignalRunningState(false);
        showSnackbar('🎉 ' + (task.message || 'Đã hoàn tất tiến trình Clear Tín Hiệu!'));
        loadClearSignalSheetData();
      }
    }
  } catch (e) {}
}

function renderClearSignalTerminalLogs(logs) {
  if (!clearSignalLogTerminal || !logs) return;
  const filtered = logs.filter(l => l.task_id === 'clear_signal' || (l.text && l.text.toLowerCase().includes('clear tín hiệu')));
  if (filtered.length === 0) return;

  clearSignalLogTerminal.innerHTML = filtered.slice(0, 40).map(l => {
    let colorClass = 'text-slate-300';
    if (l.level === 'success') colorClass = 'text-emerald-400 font-semibold';
    else if (l.level === 'error') colorClass = 'text-rose-400 font-semibold';
    else if (l.level === 'warning') colorClass = 'text-amber-300';
    return `<div class="${colorClass}"><span class="text-slate-500">[${l.time}]</span> ${l.text}</div>`;
  }).join('');
}

if (btnClearClearSignalLogs) {
  btnClearClearSignalLogs.addEventListener('click', () => {
    if (clearSignalLogTerminal) clearSignalLogTerminal.innerHTML = '<div class="text-slate-500 italic">Đã xóa nhật ký.</div>';
  });
}

// ===================== EXPORT EXCEL =====================
if (btnExportClearSignalData) {
  btnExportClearSignalData.addEventListener('click', () => {
    const filter = selectClearSignalFilterStatus ? selectClearSignalFilterStatus.value : 'all';
    showSnackbar('📥 Đang xuất dữ liệu Clear Tín Hiệu ra Excel...');
    window.location.href = `/api/clear-signal/export?gid=0&status=${filter}`;
  });
}

// ===================== TAB REGISTRATION =====================
registerTab('tab-clear-signal', {
  title: 'Auto Clear Tín Hiệu',
  onActivate: () => loadClearSignalSheetData()
});
