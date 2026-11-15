// ==========================================================
// COMPONENT: AUTO PHÂN CÔNG TAY (tab-manual-assign)
// Sheet GID: 909147347
// Mirrors the CLS component pattern.
// ==========================================================

const badgeAssignPending      = document.getElementById('badgeAssignPending');
const assignStatTotal         = document.getElementById('assignStatTotal');
const assignStatPending       = document.getElementById('assignStatPending');
const assignStatDone          = document.getElementById('assignStatDone');
const assignStatError         = document.getElementById('assignStatError');
const chkAssignVisible        = document.getElementById('chkAssignVisible');
const btnRunAutoAssign        = document.getElementById('btnRunAutoAssign');
const assignSpinner           = document.getElementById('assignSpinner');
const assignRunIcon           = document.getElementById('assignRunIcon');
const assignRunText           = document.getElementById('assignRunText');
const assignProgressTracker   = document.getElementById('assignProgressTracker');
const assignTrackerStatus     = document.getElementById('assignTrackerStatus');
const assignTrackerPercent    = document.getElementById('assignTrackerPercent');
const assignProgressBar       = document.getElementById('assignProgressBar');
const inputSearchAssign       = document.getElementById('inputSearchAssign');
const selectAssignFilterStatus= document.getElementById('selectAssignFilterStatus');
const selectAssignFilterType  = document.getElementById('selectAssignFilterType');
const chkAssignSelectAll      = document.getElementById('chkAssignSelectAll');
const tbodyAssignList         = document.getElementById('tbodyAssignList');
const assignTableFooterText   = document.getElementById('assignTableFooterText');
const assignSelectedCountText = document.getElementById('assignSelectedCountText');
const btnRefreshAssignSheetData = document.getElementById('btnRefreshAssignSheetData');
const inputAssignWebhookUrl   = document.getElementById('inputAssignWebhookUrl');
const btnSaveAssignWebhook    = document.getElementById('btnSaveAssignWebhook');
const assignWebhookStatusBadge= document.getElementById('assignWebhookStatusBadge');
const btnAutoAssignModeToggle = document.getElementById('btnAutoAssignModeToggle');
const autoAssignModeIcon      = document.getElementById('autoAssignModeIcon');
const autoAssignModeText      = document.getElementById('autoAssignModeText');
const autoAssignModeDot       = document.getElementById('autoAssignModeDot');
// assignLogTerminal, btnClearAssignLogs, btnExportAssignData được khai báo trong core/dom.js
const selectDateFilterAssign  = document.getElementById('selectDateFilterAssign');
const btnClearAssignCache     = document.getElementById('btnClearAssignCache');

let currentAssignRecords      = [];
let currentFilteredAssignRecords = [];
let selectedAssignShds        = new Set();
let assignKnownShds           = new Set();
let assignUserForcedShds      = new Set();
let isAssignRunning           = false;
autoAssignMode            = localStorage.getItem('autoAssignMode') !== 'false';
autoAssignCountdownTimer  = null;
autoAssignCountdown       = 0;

// ===================== WEBHOOK =====================
(function initAssignWebhook() {
  try {
    const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
    const saved = cfg.assign_webhook_url || '';
    if (inputAssignWebhookUrl && saved) {
      inputAssignWebhookUrl.value = saved;
      if (assignWebhookStatusBadge) {
        assignWebhookStatusBadge.textContent = '✓ Đã kết nối Webhook';
        assignWebhookStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200';
      }
    }
  } catch (e) {}
})();

if (btnSaveAssignWebhook) {
  btnSaveAssignWebhook.addEventListener('click', async () => {
    const url = inputAssignWebhookUrl ? inputAssignWebhookUrl.value.trim() : '';
    try {
      const res = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assign_webhook_url: url })
      });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        showSnackbar('💾 Đã lưu Webhook Phân Công Tay!');
        if (assignWebhookStatusBadge) {
          assignWebhookStatusBadge.textContent = url ? '✓ Đã kết nối Webhook' : '⚠ Chưa cấu hình Webhook';
          assignWebhookStatusBadge.className = url
            ? 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200'
            : 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200';
        }
        try {
          const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
          cfg.assign_webhook_url = url;
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
function updateAutoAssignModeUI() {
  if (!btnAutoAssignModeToggle) return;
  const sidebarBadge = document.getElementById('sidebarAutoAssignBadge');
  if (autoAssignMode) {
    btnAutoAssignModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-sky-500 bg-sky-50 text-sky-700 transition-all shadow-sm animate-pulse cursor-pointer';
    if (autoAssignModeText) autoAssignModeText.textContent = 'Tự Động: BẬT';
    if (autoAssignModeDot) autoAssignModeDot.className = 'w-2 h-2 rounded-full bg-sky-600 transition-all animate-bounce';
    if (sidebarBadge) sidebarBadge.classList.remove('hidden');
  } else {
    btnAutoAssignModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-slate-200 bg-white text-slate-600 hover:border-sky-400 hover:bg-sky-50 hover:text-sky-700 transition-all shadow-sm cursor-pointer';
    if (autoAssignModeText) autoAssignModeText.textContent = 'Tự Động: TẮT';
    if (autoAssignModeDot) autoAssignModeDot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all';
    if (sidebarBadge) sidebarBadge.classList.add('hidden');
  }
}
updateAutoAssignModeUI();

if (btnAutoAssignModeToggle) {
  btnAutoAssignModeToggle.addEventListener('click', () => {
    autoAssignMode = !autoAssignMode;
    localStorage.setItem('autoAssignMode', autoAssignMode ? 'true' : 'false');
    updateAutoAssignModeUI();
    fetch('/api/auto-modes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assign: autoAssignMode })
    }).catch(() => {});
    if (autoAssignMode) {
      showSnackbar('🤖 Chế độ Tự Động Phân Công Tay đã BẬT - Hệ thống chạy nền tự động sẽ điều phối!');
    } else {
      showSnackbar('Chế độ Tự Động Phân Công Tay đã TẮT.');
      if (autoAssignCountdownTimer) {
        clearInterval(autoAssignCountdownTimer);
        autoAssignCountdownTimer = null;
        if (autoAssignModeText) autoAssignModeText.textContent = 'Tự Động: TẮT';
      }
    }
  });
}

function _isAssignFinalDone(r) {
  const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
  if (!tt || tt.includes('không thành công') || tt.includes('thất bại') || tt.includes('chưa') || tt.includes('lỗi') || tt.includes('error')) {
    return false;
  }
  return tt.includes('cập nhật thành công') || tt.includes('thành công!') || tt.includes('đã xử lý');
}

// Auto chỉ chạy HĐ CHƯA từng xử lý (Thao Tác trống / "Chưa cập nhật" / "Chưa xử lý"). HĐ đã có kết quả (kể cả lỗi) phải chạy lại thủ công.
function _isAssignAutoPending(r) {
  const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
  return !tt || tt === 'chưa cập nhật' || tt === 'chưa xử lý';
}

// Việc tự động kích hoạt được điều phối tập trung ở Backend (_auto_orchestrator_loop)
function checkAndAutoTriggerAssign() {
  return;
}

// ===================== LOAD DATA =====================
async function loadAssignSheetData() {
  if (!tbodyAssignList) return;
  if (tbodyAssignList.children.length === 0 ||
      (tbodyAssignList.children.length === 1 && tbodyAssignList.children[0].textContent.includes('tải'))) {
    tbodyAssignList.innerHTML = '<tr><td colspan="12" class="text-center py-8 text-slate-400"><span>⏳ Đang tải dữ liệu từ Google Sheet (GID: 909147347)...</span></td></tr>';
  }
  try {
    const res = await fetch(`/api/assign/sheet-data?_t=${Date.now()}`);
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      currentAssignRecords = data.records || [];
      const validShds = new Set(currentAssignRecords.map(r => String(r['SHD'] || '').trim()).filter(Boolean));
      Array.from(selectedAssignShds).forEach(s => { if (!validShds.has(s)) selectedAssignShds.delete(s); });
      Array.from(assignKnownShds).forEach(s => { if (!validShds.has(s)) assignKnownShds.delete(s); });
      currentAssignRecords.forEach(r => {
        const shd = String(r['SHD'] || '').trim();
        if (!shd) return;
        const done = _isAssignFinalDone(r);
        if (!assignKnownShds.has(shd)) {
          assignKnownShds.add(shd);
          if (!done) selectedAssignShds.add(shd);
        } else if (done && !assignUserForcedShds.has(shd)) {
          selectedAssignShds.delete(shd);
        }
      });
      updateAssignStats(currentAssignRecords);
      if (!isAssignRunning) renderAssignTable(currentAssignRecords);
      if (autoAssignMode && !isAssignRunning && !autoAssignCountdownTimer) {
        checkAndAutoTriggerAssign();
      }
    } else {
      tbodyAssignList.innerHTML = `<tr><td colspan="11" class="text-center py-6 text-rose-500 font-medium">❌ ${escapeHtml(data.message || 'Không thể đọc dữ liệu từ Google Sheet')}</td></tr>`;
    }
  } catch (e) {
    tbodyAssignList.innerHTML = '<tr><td colspan="11" class="text-center py-6 text-rose-500 font-medium">❌ Lỗi kết nối khi tải Google Sheet</td></tr>';
  }
}

// ===================== STATS =====================
function updateAssignStats(records) {
  let pending = 0, done = 0, error = 0;
  records.forEach(r => {
    const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
    if (tt.includes('không thành công') || tt.includes('lỗi') || tt.includes('thất bại')) error++;
    else if (tt.includes('cập nhật thành công') || (tt.includes('thành công') && !tt.includes('không'))) done++;
    else pending++;
  });
  if (assignStatTotal) assignStatTotal.textContent = records.length;
  if (assignStatPending) assignStatPending.textContent = pending;
  if (assignStatDone) assignStatDone.textContent = done;
  if (assignStatError) assignStatError.textContent = error;
  if (badgeAssignPending) badgeAssignPending.textContent = `${pending} chờ xử lý`;
}

let currentAssignPage = 1;

// ===================== TABLE RENDER =====================
function renderAssignTable(records) {
  if (!tbodyAssignList) return;
  const dateFilter   = selectDateFilterAssign ? selectDateFilterAssign.value : 'today';
  const query        = inputSearchAssign ? inputSearchAssign.value.trim().toLowerCase() : '';
  const statusFilter = selectAssignFilterStatus ? selectAssignFilterStatus.value : 'all';
  const typeFilter   = selectAssignFilterType   ? selectAssignFilterType.value   : 'all';

  // Apply unified date filtering first
  let dateFiltered = records;
  if (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.filterRecords === 'function') {
    dateFiltered = window.UnifiedWorkTabs.filterRecords(records, dateFilter);
  }

  let filtered = dateFiltered.filter(r => {
    const shd      = String(r['SHD'] || '').toLowerCase();
    const email    = String(r['Email'] || '').toLowerCase();
    const block    = String(r['Block Đến'] || '').toLowerCase();
    const nv       = String(r['Nhân Viên Đến'] || '').toLowerCase();
    const loai     = String(r['Loại Tác Vụ'] || '').toLowerCase();
    const tt       = String(r['Thao Tác'] || '').trim().toLowerCase();

    if (query && !shd.includes(query) && !email.includes(query) && !block.includes(query) && !nv.includes(query)) {
      return false;
    }
    if (typeFilter !== 'all' && !loai.includes(typeFilter.toLowerCase())) return false;

    const isSuccess = tt.includes('cập nhật thành công') || (tt.includes('thành công') && !tt.includes('không'));
    const isError   = tt.includes('không thành công') || tt.includes('lỗi') || tt.includes('thất bại');
    const isPending = !isSuccess;

    if (statusFilter === 'pending') return isPending;
    if (statusFilter === 'done')    return isSuccess;
    if (statusFilter === 'error')   return isError;
    return true;
  });

  // Đảm bảo luôn sắp xếp từ gần nhất đến xa nhất (mới nhất lên đầu)
  if (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.sortRecordsNewestFirst === 'function') {
    filtered = window.UnifiedWorkTabs.sortRecordsNewestFirst(filtered);
  }
  currentFilteredAssignRecords = filtered;

  if (assignTableFooterText) {
    assignTableFooterText.textContent = `Hiển thị ${filtered.length} bản ghi`;
  }

  if (filtered.length === 0) {
    tbodyAssignList.innerHTML = '<tr><td colspan="11" class="text-center py-8 text-slate-400">Không có bản ghi nào phù hợp với bộ lọc</td></tr>';
    if (window.UnifiedWorkTabs) {
      window.UnifiedWorkTabs.renderPagination('assignPagination', { total: 0 });
    }
    updateAssignSelectedCount();
    return;
  }

  // Phân trang 10 dòng 1 trang
  const pageState = window.UnifiedWorkTabs
    ? window.UnifiedWorkTabs.paginate(filtered, currentAssignPage, 10)
    : { items: filtered.slice(0, 10), currentPage: 1, totalPages: Math.ceil(filtered.length / 10), total: filtered.length, startIdx: 0, endIdx: Math.min(10, filtered.length) };
  currentAssignPage = pageState.currentPage;

  tbodyAssignList.innerHTML = '';
  pageState.items.forEach((r, idx) => {
    const globalIdx = pageState.startIdx + idx;
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50 transition-colors';

    const shd   = String(r['SHD'] || '').trim();
    const email = r['Email'] || '';
    const loai  = r['Loại Tác Vụ'] || '';
    const block = r['Block Đến'] || '';
    const nv    = r['Nhân Viên Đến'] || '';
    const ngay  = r['Ngày Cập Nhật'] || '';
    const tt    = String(r['Thao Tác'] || '').trim();
    const tacVu = r['Tác Vụ'] || 'Phân Công Tay';

    const isChecked = selectedAssignShds.has(shd);

    // Badge Thao Tác
    let badgeTt = '<span class="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600">Chưa xử lý</span>';
    const ttL = tt.toLowerCase();
    if (ttL.includes('cập nhật thành công') || (ttL.includes('thành công') && !ttL.includes('không'))) {
      badgeTt = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">✓ ${escapeHtml(tt)}</span>`;
    } else if (ttL.includes('không thành công') || ttL.includes('lỗi')) {
      badgeTt = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200" title="${escapeHtml(tt)}">✕ ${escapeHtml(tt)}</span>`;
    } else if (tt) {
      badgeTt = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">${escapeHtml(tt)}</span>`;
    }

    // Loại tác vụ badge
    const loaiBadge = loai.toUpperCase().includes('TRIỂN KHAI')
      ? `<span class="px-2 py-0.5 rounded bg-sky-50 text-sky-700 text-[10px] font-bold border border-sky-100">TRIỂN KHAI</span>`
      : loai.toUpperCase().includes('BẢO TRÌ')
        ? `<span class="px-2 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px] font-bold border border-amber-100">BẢO TRÌ</span>`
        : `<span class="px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-medium">${escapeHtml(loai)}</span>`;

    tr.innerHTML = `
      <td class="p-3 text-center">
        <input type="checkbox" class="assign-row-checkbox rounded text-sky-600" data-shd="${escapeHtml(shd)}" ${isChecked ? 'checked' : ''}>
      </td>
      <td class="p-3 text-center text-slate-500 font-mono">${globalIdx + 1}</td>
      <td class="p-3 font-medium text-slate-700">${escapeHtml(tacVu)}</td>
      <td class="p-3"><strong class="font-mono text-sky-700 text-xs">${escapeHtml(shd)}</strong></td>
      <td class="p-3 font-mono text-[11px] text-slate-600">${escapeHtml(email)}</td>
      <td class="p-3">${loaiBadge}</td>
      <td class="p-3 font-medium text-slate-700 text-[11px]">${escapeHtml(block)}</td>
      <td class="p-3 font-medium text-slate-700 text-[11px]">${escapeHtml(nv)}</td>
      <td class="p-3 font-mono text-[11px] text-slate-500">${escapeHtml(ngay)}</td>
      <td class="p-3">${badgeTt}</td>
      <td class="p-3 text-center">
        <button type="button" class="btn-run-single-assign px-2 py-1 rounded-lg text-[11px] font-semibold bg-sky-50 text-sky-600 hover:bg-sky-100 transition-colors" data-shd="${escapeHtml(shd)}" title="Chạy Phân Công Tay chỉ cho HĐ này">
          ▶ Chạy
        </button>
      </td>
    `;
    tbodyAssignList.appendChild(tr);
  });

  // Render pagination controls
  if (window.UnifiedWorkTabs) {
    window.UnifiedWorkTabs.renderPagination('assignPagination', pageState, (newPage) => {
      currentAssignPage = newPage;
      renderAssignTable(currentAssignRecords);
    });
  }

  updateAssignSelectedCount();

  // Single-run click
  tbodyAssignList.querySelectorAll('.btn-run-single-assign').forEach(btn => {
    btn.addEventListener('click', e => {
      const shd = e.currentTarget.dataset.shd;
      const target = currentAssignRecords.find(r => String(r['SHD'] || '').trim() === shd);
      if (target) runAssignProcess([target]);
    });
  });

  // Checkbox changes
  tbodyAssignList.querySelectorAll('.assign-row-checkbox').forEach(chk => {
    chk.addEventListener('change', e => {
      const shd = e.target.dataset.shd;
      if (e.target.checked) {
        selectedAssignShds.add(shd);
        assignUserForcedShds.add(shd);
      } else {
        selectedAssignShds.delete(shd);
        assignUserForcedShds.delete(shd);
      }
      updateAssignSelectedCount();
    });
  });

  // Safe Chart & Top Staff update after table has successfully rendered
  try {
    if (window.UnifiedWorkTabs) {
      if (typeof window.UnifiedWorkTabs.updateDailyChart === 'function') {
        window.UnifiedWorkTabs.updateDailyChart('assignDailyChart', records, dateFilter);
      }
      if (typeof window.UnifiedWorkTabs.updateTopStaff === 'function') {
        window.UnifiedWorkTabs.updateTopStaff('assignTopStaffContainer', records, dateFilter);
      }
    }
  } catch (err) {}
}

function updateAssignSelectedCount() {
  if (assignSelectedCountText) assignSelectedCountText.textContent = `(${selectedAssignShds.size} HĐ đã chọn)`;
  if (chkAssignSelectAll) {
    const filteredShds = currentFilteredAssignRecords.map(r => String(r['SHD'] || '').trim()).filter(Boolean);
    chkAssignSelectAll.checked = filteredShds.length > 0 && filteredShds.every(s => selectedAssignShds.has(s));
  }
}

if (chkAssignSelectAll) {
  chkAssignSelectAll.addEventListener('change', e => {
    const checked = e.target.checked;
    const targetList = currentFilteredAssignRecords;
    targetList.forEach(r => {
      const shd = String(r['SHD'] || '').trim();
      if (!shd) return;
      if (checked) {
        selectedAssignShds.add(shd);
        assignUserForcedShds.add(shd);
      } else {
        selectedAssignShds.delete(shd);
        assignUserForcedShds.delete(shd);
      }
    });
    renderAssignTable(currentAssignRecords);
  });
}

if (inputSearchAssign)        inputSearchAssign.addEventListener('input',  () => { currentAssignPage = 1; renderAssignTable(currentAssignRecords); });
if (selectAssignFilterStatus) selectAssignFilterStatus.addEventListener('change', () => { currentAssignPage = 1; renderAssignTable(currentAssignRecords); });
if (selectAssignFilterType)   selectAssignFilterType.addEventListener('change',   () => { currentAssignPage = 1; renderAssignTable(currentAssignRecords); });
if (selectDateFilterAssign)   selectDateFilterAssign.addEventListener('change',   () => { currentAssignPage = 1; renderAssignTable(currentAssignRecords); });
if (btnRefreshAssignSheetData) {
  btnRefreshAssignSheetData.addEventListener('click', () => {
    showSnackbar('Đang làm mới dữ liệu từ Google Sheet (GID: 909147347)...');
    loadAssignSheetData();
  });
}
if (btnClearAssignCache) {
  btnClearAssignCache.addEventListener('click', async () => {
    try {
      await fetch('/api/assign/clear-cache', { method: 'POST' });
      showSnackbar('🧹 Đã xóa bộ nhớ đệm Phân Công Tay!');
      loadAssignSheetData();
    } catch (e) {
      showSnackbar('Không thể xóa cache Phân Công Tay');
    }
  });
}

// ===================== RUN =====================
async function runAssignProcess(specificRecords = null) {
  if (isAssignRunning) {
    showSnackbar('Đang có tiến trình Phân Công Tay đang chạy...');
    return;
  }

  let recordsToRun = specificRecords;
  if (!recordsToRun) {
    if (selectedAssignShds.size > 0) {
      recordsToRun = currentAssignRecords.filter(r => selectedAssignShds.has(String(r['SHD'] || '').trim()));
    }
  }

  if (!recordsToRun || recordsToRun.length === 0) {
    showSnackbar('⚠️ Chưa có hợp đồng nào được chọn để xử lý!');
    return;
  }

  if (!specificRecords) {
    const doneCount = recordsToRun.filter(r => _isAssignFinalDone(r)).length;
    if (doneCount >= 2 && !window.confirm(`Bạn đang chọn chạy lại ${doneCount} hợp đồng Phân Công Tay đã xử lý. Bạn có chắc chắn muốn chạy lại?`)) {
      return;
    }
  }

  try {
    setAssignRunningState(true);
    const isVisible = chkAssignVisible ? chkAssignVisible.checked : false;
    const res = await fetch('/api/assign/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ headless: !isVisible, records: recordsToRun })
    });
    const data = await res.json();
    if (res.ok && data.status === 'started') {
      const modeDesc = !isVisible ? 'chạy ngầm' : 'đang mở Chrome trực tiếp trên màn hình';
      showSnackbar(`🚀 Đã khởi động Phân Công Tay cho ${data.count} hợp đồng (${modeDesc})!`);
    } else {
      setAssignRunningState(false);
      showSnackbar(data.message || 'Không thể bắt đầu Phân Công Tay');
    }
  } catch (err) {
    setAssignRunningState(false);
    showSnackbar(`Lỗi kết nối máy chủ: ${err}`);
  }
}

function setAssignRunningState(running) {
  isAssignRunning = running;
  if (btnRunAutoAssign) btnRunAutoAssign.disabled = running;
  if (assignSpinner)   assignSpinner.style.display   = running ? 'inline-block' : 'none';
  if (assignRunIcon)   assignRunIcon.style.display    = running ? 'none' : 'inline-block';
  if (assignRunText)   assignRunText.textContent      = running ? 'Đang Xử Lý Phân Công...' : 'Bắt Đầu Phân Công Tay';
  if (assignProgressTracker) assignProgressTracker.style.display = running ? 'block' : 'none';
}

async function pollAssignStatus() {
  try {
    const res = await fetch('/api/assign/live-status');
    if (!res.ok) return;
    const data = await res.json();
    const task = data.task || {};

    if (task.is_running) {
      setAssignRunningState(true);
      const cur   = task.current_index || 0;
      const total = task.total || 1;
      const pct   = Math.min(100, Math.round((cur / Math.max(1, total)) * 100));
      if (assignTrackerPercent) assignTrackerPercent.textContent = `${pct}%`;
      if (assignProgressBar)   assignProgressBar.style.width   = `${pct}%`;
      if (assignTrackerStatus) assignTrackerStatus.textContent = task.message || `Đang xử lý ${cur}/${total}: HĐ ${task.current_shd || ''}`;
    } else {
      if (isAssignRunning) {
        setAssignRunningState(false);
        showSnackbar('✅ Tiến trình Phân Công Tay đã hoàn thành!');
        loadAssignSheetData();
      }
    }
  } catch (e) {}
}

if (btnRunAutoAssign) {
  btnRunAutoAssign.addEventListener('click', () => runAssignProcess());
}

// Live Terminal Logs Rendering cho Phân Công Tay
function renderAssignTerminalLogs(logs) {
  if (!assignLogTerminal) return;
  if (!logs || logs.length === 0) return;

  const relevant = logs.filter(l => {
    const tid = (l.task_id || '').toLowerCase();
    const txt = (l.text || '').toLowerCase();
    return tid === 'manual_assign' || tid === 'assign' || tid === 'login' || txt.includes('phân công') || txt.includes('assign') || txt.includes('đăng nhập') || txt.includes('phiên') || txt.includes('inside');
  });
  const displayLogs = (relevant.length > 0 ? relevant : logs).slice(-40);
  assignLogTerminal.innerHTML = '';
  displayLogs.forEach(l => {
    const item = document.createElement('div');
    item.className = 'py-0.5 leading-relaxed';
    let colorClass = 'text-slate-300';
    if (l.level === 'success') colorClass = 'text-emerald-400 font-medium';
    else if (l.level === 'warning') colorClass = 'text-amber-400';
    else if (l.level === 'error') colorClass = 'text-rose-400 font-semibold';
    else if (l.level === 'info') colorClass = 'text-sky-300';

    item.innerHTML = `
      <span class="text-slate-500 font-mono text-[10px] select-none">[${escapeHtml(l.time)}]</span>
      <span class="${colorClass}">${escapeHtml(l.text)}</span>
    `;
    assignLogTerminal.appendChild(item);
  });
  assignLogTerminal.scrollTop = assignLogTerminal.scrollHeight;
}

if (btnClearAssignLogs && assignLogTerminal) {
  btnClearAssignLogs.addEventListener('click', () => {
    assignLogTerminal.innerHTML = '<div class="text-slate-500 italic">Nhật ký Phân Công Tay đã được làm sạch</div>';
  });
}

// Xuất data xử lý Phân Công Tay ra Excel
if (btnExportAssignData) {
  btnExportAssignData.addEventListener('click', () => {
    showSnackbar('Đang chuẩn bị file Excel xuất dữ liệu Phân Công Tay...');
    window.location.href = `/api/assign/export?gid=909147347&status=all`;
  });
}

registerTab('tab-manual-assign', {
  title: 'Auto Phân Công Tay',
  onActivate() {
    if (currentAssignRecords.length > 0 && !isAssignRunning) renderAssignTable(currentAssignRecords);
    loadAssignSheetData();
  }
});
