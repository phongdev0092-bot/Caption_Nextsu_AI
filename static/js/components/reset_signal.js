// ==========================================================
// COMPONENT: AUTO CẤP LẠI TÍN HIỆU (tab-reset-signal)
// Sheet GID: 1100152201 (Sheet ID: 1dXsWnon9myjDlcWM6BRLqDt_pxWBmTYFgb17k7R24vc)
// ==========================================================

const badgeResetSignalPending       = document.getElementById('badgeResetSignalPending');
const resetSignalStatTotal          = document.getElementById('resetSignalStatTotal');
const resetSignalStatPending        = document.getElementById('resetSignalStatPending');
const resetSignalStatDone           = document.getElementById('resetSignalStatDone');
const resetSignalStatError          = document.getElementById('resetSignalStatError');
const chkResetSignalVisible         = document.getElementById('chkResetSignalVisible');
const btnRunAutoResetSignal         = document.getElementById('btnRunAutoResetSignal');
const resetSignalSpinner            = document.getElementById('resetSignalSpinner');
const resetSignalRunIcon            = document.getElementById('resetSignalRunIcon');
const resetSignalRunText            = document.getElementById('resetSignalRunText');
const resetSignalProgressTracker    = document.getElementById('resetSignalProgressTracker');
const resetSignalTrackerStatus      = document.getElementById('resetSignalTrackerStatus');
const resetSignalTrackerPercent     = document.getElementById('resetSignalTrackerPercent');
const resetSignalProgressBar        = document.getElementById('resetSignalProgressBar');
const inputSearchResetSignal        = document.getElementById('inputSearchResetSignal');
const selectResetSignalFilterStatus = document.getElementById('selectResetSignalFilterStatus');
const chkResetSignalSelectAll       = document.getElementById('chkResetSignalSelectAll');
const tbodyResetSignalList          = document.getElementById('tbodyResetSignalList');
const resetSignalTableFooterText    = document.getElementById('resetSignalTableFooterText');
const resetSignalSelectedCountText  = document.getElementById('resetSignalSelectedCountText');
const btnRefreshResetSignalSheetData= document.getElementById('btnRefreshResetSignalSheetData');
const btnExportResetSignalData      = document.getElementById('btnExportResetSignalData');
const inputResetSignalWebhookUrl    = document.getElementById('inputResetSignalWebhookUrl');
const btnSaveResetSignalWebhook     = document.getElementById('btnSaveResetSignalWebhook');
const resetSignalWebhookStatusBadge = document.getElementById('resetSignalWebhookStatusBadge');
const btnAutoResetSignalModeToggle  = document.getElementById('btnAutoResetSignalModeToggle');
const autoResetSignalModeIcon       = document.getElementById('autoResetSignalModeIcon');
const autoResetSignalModeText       = document.getElementById('autoResetSignalModeText');
const autoResetSignalModeDot        = document.getElementById('autoResetSignalModeDot');
const resetSignalLogTerminal        = document.getElementById('resetSignalLogTerminal');
const btnClearResetSignalLogs       = document.getElementById('btnClearResetSignalLogs');
const selectDateFilterResetSignal   = document.getElementById('selectDateFilterResetSignal');
const btnClearResetSignalCache      = document.getElementById('btnClearResetSignalCache');

let currentResetSignalRecords  = [];
let currentFilteredResetSignalRecords = [];
let selectedResetSignalShds    = new Set();
let isResetSignalRunning       = false;
autoResetSignalMode            = localStorage.getItem('autoResetSignalMode') !== 'false'; // Mặc định là BẬT
autoResetSignalCountdownTimer  = null;
autoResetSignalCountdown       = 0;

// ===================== WEBHOOK =====================
async function initResetSignalWebhook() {
  try {
    let saved = '';
    const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
    saved = cfg.reset_signal_webhook_url || '';
    if (!saved) {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        saved = data.reset_signal_webhook_url || data.google_sheet_webhook_url || '';
        cfg.reset_signal_webhook_url = saved;
        localStorage.setItem('appConfig', JSON.stringify(cfg));
      }
    }
    if (inputResetSignalWebhookUrl && saved) {
      inputResetSignalWebhookUrl.value = saved;
      if (resetSignalWebhookStatusBadge) {
        resetSignalWebhookStatusBadge.textContent = '✓ Đã kết nối Webhook';
        resetSignalWebhookStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-purple-100 text-purple-800 border border-purple-200';
      }
    }
  } catch (e) {}
}
initResetSignalWebhook();

if (btnSaveResetSignalWebhook) {
  btnSaveResetSignalWebhook.addEventListener('click', async () => {
    const url = inputResetSignalWebhookUrl ? inputResetSignalWebhookUrl.value.trim() : '';
    try {
      const res = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reset_signal_webhook_url: url })
      });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        showSnackbar('💾 Đã lưu Webhook Cấp Lại Tín Hiệu!');
        if (resetSignalWebhookStatusBadge) {
          resetSignalWebhookStatusBadge.textContent = url ? '✓ Đã kết nối Webhook' : '⚠ Chưa cấu hình Webhook';
          resetSignalWebhookStatusBadge.className = url
            ? 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200'
            : 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200';
        }
        try {
          const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
          cfg.reset_signal_webhook_url = url;
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
function updateAutoResetSignalModeUI() {
  if (!btnAutoResetSignalModeToggle) return;
  const sidebarBadge = document.getElementById('sidebarAutoResetSignalBadge');
  if (autoResetSignalMode) {
    btnAutoResetSignalModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-purple-500 bg-purple-50 text-purple-700 transition-all shadow-sm animate-pulse cursor-pointer';
    if (autoResetSignalModeText) autoResetSignalModeText.textContent = 'Tự Động: BẬT';
    if (autoResetSignalModeDot) autoResetSignalModeDot.className = 'w-2 h-2 rounded-full bg-purple-600 transition-all animate-bounce';
    if (sidebarBadge) sidebarBadge.classList.remove('hidden');
  } else {
    btnAutoResetSignalModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-slate-200 bg-white text-slate-600 hover:border-purple-400 hover:bg-purple-50 hover:text-purple-700 transition-all shadow-sm cursor-pointer';
    if (autoResetSignalModeText) autoResetSignalModeText.textContent = 'Tự Động: TẮT';
    if (autoResetSignalModeDot) autoResetSignalModeDot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all';
    if (sidebarBadge) sidebarBadge.classList.add('hidden');
  }
}
updateAutoResetSignalModeUI();

if (btnAutoResetSignalModeToggle) {
  btnAutoResetSignalModeToggle.addEventListener('click', () => {
    autoResetSignalMode = !autoResetSignalMode;
    localStorage.setItem('autoResetSignalMode', autoResetSignalMode ? 'true' : 'false');
    updateAutoResetSignalModeUI();
    fetch('/api/auto-modes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reset_signal: autoResetSignalMode })
    }).catch(() => {});
    if (autoResetSignalMode) {
      showSnackbar('🤖 Chế độ Tự Động Cấp Lại Tín Hiệu đã BẬT - Hệ thống chạy nền tự động sẽ điều phối!');
    } else {
      showSnackbar('Chế độ Tự Động Cấp Lại Tín Hiệu đã TẮT.');
      if (autoResetSignalCountdownTimer) {
        clearInterval(autoResetSignalCountdownTimer);
        autoResetSignalCountdownTimer = null;
        if (autoResetSignalModeText) autoResetSignalModeText.textContent = 'Tự Động: TẮT';
      }
    }
  });
}

function _isResetSignalFinalDone(r) {
  const kq = String(r['Kết Quả'] || '').trim().toLowerCase();
  return kq.includes('thành công')
      || kq.includes('đã xử lý')
      || kq.includes('đã cấp')
      || kq.includes('cấp lại')
      || kq.includes('tự động')
      || kq.includes('lỗi')
      || kq.includes('thất bại')
      || kq.includes('không thành công');
}

function _isResetSignalAutoEligible(r) {
  if (!r) return false;
  if (r._is_old_day_backlog || r._manual_only || r._login_or_server_error_locked) return false;
  const kq = String(r['Kết Quả'] || '').trim().toLowerCase();
  if (kq.includes('lỗi')) return false;
  return !_isResetSignalFinalDone(r);
}

// Việc tự động kích hoạt được điều phối tập trung ở Backend (_auto_orchestrator_loop)
function checkAndAutoTriggerResetSignal() {
  return;
}

// ===================== DATA LOADING & RENDERING =====================
async function loadResetSignalSheetData() {
  try {
    const res = await fetch('/api/reset-signal/sheet-data?gid=1100152201');
    if (!res.ok) return;
    const data = await res.json();
    if (data.status !== 'ok') return;

    currentResetSignalRecords = data.records || [];
    const validResetShds = new Set(currentResetSignalRecords.map(r => String(r['SHD'] || '').trim()).filter(Boolean));
    Array.from(selectedResetSignalShds).forEach(s => { if (!validResetShds.has(s)) selectedResetSignalShds.delete(s); });
    renderResetSignalTable();
    updateResetSignalKPIs();

    if (autoResetSignalMode && !isResetSignalRunning && !autoResetSignalCountdownTimer) {
      const pendingCount = currentResetSignalRecords.filter(r => _isResetSignalAutoEligible(r)).length;
      if (pendingCount > 0) {
        checkAndAutoTriggerResetSignal();
      }
    }
  } catch (err) {}
}

function updateResetSignalKPIs() {
  const total = currentResetSignalRecords.length;
  let done = 0, error = 0, pending = 0;

  currentResetSignalRecords.forEach(r => {
    const kq = String(r['Kết Quả'] || '').trim().toLowerCase();
    if (kq.includes('thành công') || kq.includes('đã xử lý')
        || kq.includes('đã cấp') || kq.includes('cấp lại') || kq.includes('tự động')) {
      done++;
    } else if (kq.includes('lỗi') || kq.includes('thất bại') || kq.includes('không thành công')) {
      error++;
    } else {
      pending++;
    }
  });

  if (resetSignalStatTotal)   resetSignalStatTotal.textContent   = total;
  if (resetSignalStatPending) resetSignalStatPending.textContent = pending;
  if (resetSignalStatDone)    resetSignalStatDone.textContent    = done;
  if (resetSignalStatError)   resetSignalStatError.textContent   = error;
  if (badgeResetSignalPending)badgeResetSignalPending.textContent= `${pending} chờ xử lý`;
}

let currentResetSignalPage = 1;

function renderResetSignalTable() {
  if (!tbodyResetSignalList) return;

  const dateFilter = selectDateFilterResetSignal ? selectDateFilterResetSignal.value : 'today';
  const keyword = inputSearchResetSignal ? inputSearchResetSignal.value.trim().toLowerCase() : '';
  const filterStatus = selectResetSignalFilterStatus ? selectResetSignalFilterStatus.value : 'all';

  // Apply unified date filtering first
  let dateFiltered = currentResetSignalRecords;
  if (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.filterRecords === 'function') {
    dateFiltered = window.UnifiedWorkTabs.filterRecords(currentResetSignalRecords, dateFilter);
  }

  // Render Charts & Top Staff
  if (window.UnifiedWorkTabs) {
    if (typeof window.UnifiedWorkTabs.updateDailyChart === 'function') {
      window.UnifiedWorkTabs.updateDailyChart('resetSignalDailyChart', currentResetSignalRecords, dateFilter);
    }
    if (typeof window.UnifiedWorkTabs.updateTopStaff === 'function') {
      window.UnifiedWorkTabs.updateTopStaff('resetSignalTopStaffContainer', currentResetSignalRecords, dateFilter);
    }
  }

  const filtered = dateFiltered.filter(r => {
    if (filterStatus === 'pending' && _isResetSignalFinalDone(r)) return false;
    if (filterStatus === 'done' && !_isResetSignalFinalDone(r)) return false;
    if (filterStatus === 'error' && !String(r['Kết Quả'] || '').toLowerCase().includes('lỗi') && !String(r['Kết Quả'] || '').toLowerCase().includes('thất bại')) return false;

    if (!keyword) return true;
    const shd = String(r['SHD'] || '').toLowerCase();
    const ten = String(r['Họ và Tên'] || '').toLowerCase();
    const mail= String(r['Email'] || '').toLowerCase();
    const nguon= String(r['Nguồn'] || r['Nguon'] || '').toLowerCase();
    return shd.includes(keyword) || ten.includes(keyword) || mail.includes(keyword) || nguon.includes(keyword);
  });

  // Đảm bảo luôn sắp xếp từ gần nhất đến xa nhất (mới nhất lên đầu)
  const sortedFiltered = (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.sortRecordsNewestFirst === 'function')
    ? window.UnifiedWorkTabs.sortRecordsNewestFirst(filtered)
    : filtered;
  currentFilteredResetSignalRecords = sortedFiltered;

  if (resetSignalTableFooterText) {
    resetSignalTableFooterText.textContent = `Hiển thị ${sortedFiltered.length} / ${currentResetSignalRecords.length} bản ghi`;
  }
  if (resetSignalSelectedCountText) {
    resetSignalSelectedCountText.textContent = `(${selectedResetSignalShds.size} HĐ đã chọn)`;
  }

  if (sortedFiltered.length === 0) {
    tbodyResetSignalList.innerHTML = `
      <tr>
        <td colspan="9" class="text-center py-8 text-slate-400">
          Không tìm thấy hợp đồng Cấp Lại Tín Hiệu phù hợp
        </td>
      </tr>`;
    if (window.UnifiedWorkTabs) {
      window.UnifiedWorkTabs.renderPagination('resetSignalPagination', { total: 0 });
    }
    return;
  }

  // Phân trang 10 dòng 1 trang
  const pageState = window.UnifiedWorkTabs
    ? window.UnifiedWorkTabs.paginate(sortedFiltered, currentResetSignalPage, 10)
    : { items: sortedFiltered.slice(0, 10), currentPage: 1, totalPages: Math.ceil(sortedFiltered.length / 10), total: sortedFiltered.length, startIdx: 0, endIdx: Math.min(10, sortedFiltered.length) };
  currentResetSignalPage = pageState.currentPage;

  tbodyResetSignalList.innerHTML = pageState.items.map((r, idx) => {
    const globalIdx = pageState.startIdx + idx;
    const shd = r['SHD'] || '';
    const isChecked = selectedResetSignalShds.has(shd) ? 'checked' : '';
    const kq = r['Kết Quả'] || '';
    const kqLower = kq.toLowerCase();

    let badgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
    let badgeText = kq || 'Chưa cập nhật';

    const _isDone   = kqLower.includes('thành công') || kqLower.includes('đã xử lý')
                   || kqLower.includes('đã cấp')     || kqLower.includes('cấp lại')
                   || kqLower.includes('tự động');
    const _isError  = kqLower.includes('lỗi') || kqLower.includes('thất bại') || kqLower.includes('không thành công');
    const _isPending = !kq || kqLower.includes('chưa');

    if (_isDone) {
      badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    } else if (_isError) {
      badgeClass = 'bg-rose-50 text-rose-700 border-rose-200';
    } else if (_isPending) {
      badgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
      badgeText  = kq || 'Chưa cập nhật';
    }

    const nguon = r['Nguồn'] || r['Nguon'] || 'User';
    let nguonBadgeClass = 'bg-blue-50 text-blue-700 border-blue-200';
    let nguonIcon = '👤';
    if (nguon.includes('Auto') || nguon.includes('72H') || nguon.includes('72h')) {
      nguonBadgeClass = 'bg-purple-50 text-purple-700 border-purple-200 font-semibold';
      nguonIcon = '🤖';
    }

    return `
      <tr class="hover:bg-purple-50/40 transition-colors border-b border-slate-100">
        <td class="p-3 text-center">
          <input type="checkbox" class="chk-reset-signal-row rounded text-purple-600" data-shd="${shd}" ${isChecked}>
        </td>
        <td class="p-3 text-center font-semibold text-slate-500">${globalIdx + 1}</td>
        <td class="p-3 font-semibold text-slate-800">${r['Họ và Tên'] || '-'}</td>
        <td class="p-3 text-slate-600 text-xs">${r['Email'] || '-'}</td>
        <td class="p-3 font-mono font-bold text-purple-700">${shd || '-'}</td>
        <td class="p-3 text-slate-500 text-xs">${r['Ngày Cập Nhật'] || '-'}</td>
        <td class="p-3 text-center">
          <span class="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] rounded-full border ${nguonBadgeClass}">
            <span>${nguonIcon}</span>
            <span>${nguon}</span>
          </span>
        </td>
        <td class="p-3 text-center">
          <span class="inline-block px-2.5 py-1 text-[11px] font-semibold rounded-full border ${badgeClass}">
            ${badgeText}
          </span>
        </td>
        <td class="p-3 text-center">
          <button type="button" class="btn-run-single-reset-signal px-2 py-1 bg-purple-50 text-purple-700 hover:bg-purple-100 rounded text-xs font-semibold border border-purple-200 transition-all cursor-pointer" data-shd="${shd}">
            ⚡ Chạy
          </button>
        </td>
      </tr>
    `;
  }).join('');

  // Render pagination controls
  if (window.UnifiedWorkTabs) {
    window.UnifiedWorkTabs.renderPagination('resetSignalPagination', pageState, (newPage) => {
      currentResetSignalPage = newPage;
      renderResetSignalTable();
    });
  }

  // Row selection handler
  tbodyResetSignalList.querySelectorAll('.chk-reset-signal-row').forEach(cb => {
    cb.addEventListener('change', (e) => {
      const shd = e.target.dataset.shd;
      if (e.target.checked) selectedResetSignalShds.add(shd);
      else selectedResetSignalShds.delete(shd);
      if (resetSignalSelectedCountText) resetSignalSelectedCountText.textContent = `(${selectedResetSignalShds.size} HĐ đã chọn)`;
    });
  });

  // Single run handler
  tbodyResetSignalList.querySelectorAll('.btn-run-single-reset-signal').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const shd = e.currentTarget.dataset.shd;
      const targetRecord = currentResetSignalRecords.find(r => r['SHD'] === shd);
      if (targetRecord) executeResetSignalProcess([targetRecord], false);
    });
  });
}

// Select all checkbox
if (chkResetSignalSelectAll) {
  chkResetSignalSelectAll.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    const targetList = currentFilteredResetSignalRecords;
    targetList.forEach(r => {
      const shd = String(r['SHD'] || '').trim();
      if (!shd) return;
      if (isChecked) selectedResetSignalShds.add(shd);
      else selectedResetSignalShds.delete(shd);
    });
    renderResetSignalTable();
  });
}

if (inputSearchResetSignal) inputSearchResetSignal.addEventListener('input', () => { currentResetSignalPage = 1; renderResetSignalTable(); });
if (selectResetSignalFilterStatus) selectResetSignalFilterStatus.addEventListener('change', () => { currentResetSignalPage = 1; renderResetSignalTable(); });
if (selectDateFilterResetSignal)   selectDateFilterResetSignal.addEventListener('change',   () => { currentResetSignalPage = 1; renderResetSignalTable(); });
if (btnRefreshResetSignalSheetData) {
  btnRefreshResetSignalSheetData.addEventListener('click', () => {
    showSnackbar('🔄 Đang tải lại dữ liệu Cấp Lại Tín Hiệu từ Google Sheet...');
    loadResetSignalSheetData();
  });
}
if (btnClearResetSignalCache) {
  btnClearResetSignalCache.addEventListener('click', async () => {
    try {
      await fetch('/api/reset-signal/clear-cache', { method: 'POST' });
      showSnackbar('🧹 Đã xóa bộ nhớ đệm Cấp Lại Tín Hiệu!');
      loadResetSignalSheetData();
    } catch (e) {
      showSnackbar('Không thể xóa cache Cấp Lại Tín Hiệu');
    }
  });
}

// ===================== EXECUTION RUNNER =====================
async function executeResetSignalProcess(selectedRecords = null, isAuto = false) {
  if (isResetSignalRunning) {
    showSnackbar('⚠️ Đang có tiến trình Cấp Lại Tín Hiệu đang chạy...');
    return;
  }

  const isVisible = chkResetSignalVisible ? chkResetSignalVisible.checked : false;

  let recordsToRun = selectedRecords;
  if (!recordsToRun) {
    if (isAuto) {
      recordsToRun = currentResetSignalRecords.filter(r => _isResetSignalAutoEligible(r));
    } else if (selectedResetSignalShds.size > 0) {
      recordsToRun = currentResetSignalRecords.filter(r => selectedResetSignalShds.has(r['SHD']));
    } else {
      recordsToRun = currentResetSignalRecords.filter(r => !_isResetSignalFinalDone(r));
    }
  }

  if (!recordsToRun || recordsToRun.length === 0) {
    showSnackbar('ℹ️ Không có hợp đồng mới cần xử lý Cấp Lại Tín Hiệu!');
    return;
  }

  if (!isAuto && !selectedRecords) {
    const doneCount = recordsToRun.filter(r => _isResetSignalFinalDone(r)).length;
    if (doneCount >= 2 && !window.confirm(`Bạn đang chọn chạy lại ${doneCount} hợp đồng đã xử lý xong. Bạn có chắc chắn muốn chạy lại?`)) {
      return;
    }
  }

  setResetSignalRunningState(true);
  showSnackbar(`🚀 Bắt đầu xử lý ${recordsToRun.length} hợp đồng Cấp Lại Tín Hiệu...`);

  try {
    const res = await fetch('/api/reset-signal/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        records: recordsToRun,
        headless: !isVisible,
        manual: !isAuto
      })
    });
    const data = await res.json();
    if (!res.ok || (data.status !== 'started' && data.status !== 'ok')) {
      showSnackbar((data.status === 'empty' ? 'ℹ️ ' : '❌ ') + (data.message || 'Lỗi khởi chạy'));
      setResetSignalRunningState(false);
    }
  } catch (err) {
    showSnackbar('❌ Lỗi kết nối máy chủ');
    setResetSignalRunningState(false);
  }
}

if (btnRunAutoResetSignal) {
  btnRunAutoResetSignal.addEventListener('click', () => executeResetSignalProcess(null, false));
}

function setResetSignalRunningState(running) {
  isResetSignalRunning = running;
  if (running) {
    if (resetSignalSpinner) resetSignalSpinner.style.display = 'inline-block';
    if (resetSignalRunIcon) resetSignalRunIcon.style.display = 'none';
    if (resetSignalRunText) resetSignalRunText.textContent = 'Đang Xử Lý...';
    if (btnRunAutoResetSignal) btnRunAutoResetSignal.disabled = true;
    if (resetSignalProgressTracker) resetSignalProgressTracker.style.display = 'block';
  } else {
    if (resetSignalSpinner) resetSignalSpinner.style.display = 'none';
    if (resetSignalRunIcon) resetSignalRunIcon.style.display = 'inline-block';
    if (resetSignalRunText) resetSignalRunText.textContent = 'Bắt Đầu Cấp Lại Tín Hiệu';
    if (btnRunAutoResetSignal) btnRunAutoResetSignal.disabled = false;
    if (resetSignalProgressTracker) resetSignalProgressTracker.style.display = 'none';
  }
}

// ===================== STATUS POLLING & LOGS =====================
async function pollResetSignalStatus() {
  try {
    const res = await fetch('/api/reset-signal/live-status');
    if (!res.ok) return;
    const data = await res.json();
    const task = data.task || {};

    if (task.is_running) {
      if (!isResetSignalRunning) setResetSignalRunningState(true);
      const total = task.total || 1;
      const idx = task.current_index || 0;
      const pct = Math.round((idx / total) * 100);

      if (resetSignalTrackerPercent) resetSignalTrackerPercent.textContent = `${pct}%`;
      if (resetSignalProgressBar) resetSignalProgressBar.style.width = `${pct}%`;
      if (resetSignalTrackerStatus) resetSignalTrackerStatus.textContent = task.message || `Đang xử lý ${idx}/${total}...`;
    } else {
      if (isResetSignalRunning) {
        setResetSignalRunningState(false);
        showSnackbar('🎉 ' + (task.message || 'Đã hoàn tất tiến trình Cấp Lại Tín Hiệu!'));
        loadResetSignalSheetData();
      }
    }
  } catch (e) {}
}

function renderResetSignalTerminalLogs(logs) {
  if (!resetSignalLogTerminal || !logs) return;
  const filtered = logs.filter(l => l.task_id === 'reset_signal' || (l.text && l.text.toLowerCase().includes('cấp lại tín hiệu')));
  if (filtered.length === 0) return;

  resetSignalLogTerminal.innerHTML = filtered.slice(0, 40).map(l => {
    let colorClass = 'text-slate-300';
    if (l.level === 'success') colorClass = 'text-emerald-400 font-semibold';
    else if (l.level === 'error') colorClass = 'text-rose-400 font-semibold';
    else if (l.level === 'warning') colorClass = 'text-amber-300';
    return `<div class="${colorClass}"><span class="text-slate-500">[${l.time}]</span> ${l.text}</div>`;
  }).join('');
}

if (btnClearResetSignalLogs) {
  btnClearResetSignalLogs.addEventListener('click', () => {
    if (resetSignalLogTerminal) resetSignalLogTerminal.innerHTML = '<div class="text-slate-500 italic">Đã xóa nhật ký.</div>';
  });
}

// ===================== EXPORT EXCEL =====================
if (btnExportResetSignalData) {
  btnExportResetSignalData.addEventListener('click', () => {
    const filter = selectResetSignalFilterStatus ? selectResetSignalFilterStatus.value : 'all';
    showSnackbar('📥 Đang xuất dữ liệu Cấp Lại Tín Hiệu ra Excel...');
    window.location.href = `/api/reset-signal/export?gid=1100152201&status=${filter}`;
  });
}

// ===================== TAB REGISTRATION =====================
registerTab('tab-reset-signal', {
  title: 'Auto Cấp Lại Tín Hiệu',
  onActivate: () => loadResetSignalSheetData()
});
