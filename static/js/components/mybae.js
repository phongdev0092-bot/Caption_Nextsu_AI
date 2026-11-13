// ==========================================================
// COMPONENT: AUTO BYPASS MYBAE (tab-bypass-mybae)
// Sheet GID: 1795923064
// Mirrors the Phân Công Tay component pattern.
// ==========================================================

const badgeMyBaePending       = document.getElementById('badgeMyBaePending');
const mybaeStatTotal          = document.getElementById('mybaeStatTotal');
const mybaeStatPending        = document.getElementById('mybaeStatPending');
const mybaeStatDone           = document.getElementById('mybaeStatDone');
const mybaeStatError          = document.getElementById('mybaeStatError');
const chkMyBaeVisible         = document.getElementById('chkMyBaeVisible');
const btnRunAutoMyBae         = document.getElementById('btnRunAutoMyBae');
const mybaeSpinner            = document.getElementById('mybaeSpinner');
const mybaeRunIcon            = document.getElementById('mybaeRunIcon');
const mybaeRunText            = document.getElementById('mybaeRunText');
const mybaeProgressTracker    = document.getElementById('mybaeProgressTracker');
const mybaeTrackerStatus      = document.getElementById('mybaeTrackerStatus');
const mybaeTrackerPercent     = document.getElementById('mybaeTrackerPercent');
const mybaeProgressBar        = document.getElementById('mybaeProgressBar');
const inputSearchMyBae        = document.getElementById('inputSearchMyBae');
const selectMyBaeFilterStatus = document.getElementById('selectMyBaeFilterStatus');
const chkMyBaeSelectAll       = document.getElementById('chkMyBaeSelectAll');
const tbodyMyBaeList          = document.getElementById('tbodyMyBaeList');
const mybaeTableFooterText    = document.getElementById('mybaeTableFooterText');
const mybaeSelectedCountText  = document.getElementById('mybaeSelectedCountText');
const btnRefreshMyBaeSheetData = document.getElementById('btnRefreshMyBaeSheetData');
const btnExportMyBaeData      = document.getElementById('btnExportMyBaeData');
const inputMyBaeWebhookUrl    = document.getElementById('inputMyBaeWebhookUrl');
const btnSaveMyBaeWebhook     = document.getElementById('btnSaveMyBaeWebhook');
const mybaeWebhookStatusBadge = document.getElementById('mybaeWebhookStatusBadge');
const btnAutoMyBaeModeToggle  = document.getElementById('btnAutoMyBaeModeToggle');
const autoMyBaeModeText       = document.getElementById('autoMyBaeModeText');
const autoMyBaeModeDot        = document.getElementById('autoMyBaeModeDot');
const mybaeLogTerminal        = document.getElementById('mybaeLogTerminal');
const btnClearMyBaeLogs       = document.getElementById('btnClearMyBaeLogs');
const selectDateFilterMyBae   = document.getElementById('selectDateFilterMyBae');
const btnClearMyBaeCache      = document.getElementById('btnClearMyBaeCache');

let currentMyBaeRecords   = [];
let isMyBaeRunning        = false;
// Mặc định BẬT đọc sheet 4s/lần
let autoMyBaeMode         = localStorage.getItem('autoMyBaeMode') !== 'false';
let autoMyBaeCountdownTimer = null;
let autoMyBaeCountdown    = 0;

const MYBAE_WEBHOOK_BADGE_ON  = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200';
const MYBAE_WEBHOOK_BADGE_OFF = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200';

// ===================== TRẠNG THÁI DÒNG =====================
// Kết Quả luôn là "Đã xử lý" (kể cả lỗi) nên phân biệt thành công/lỗi dựa vào Thao Tác
function _mybaeIsError(r) {
  const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
  return tt.includes('không thành công') || tt.includes('lỗi');
}
function _mybaeIsSuccess(r) {
  const kq = String(r['Kết Quả'] || '').trim().toLowerCase();
  const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
  if (tt) return tt.includes('thành công') && !tt.includes('không');
  return kq === 'đã xử lý';
}
function _mybaeIsPending(r) {
  return !_mybaeIsSuccess(r) && !_mybaeIsError(r);
}

// ===================== WEBHOOK =====================
function _setMyBaeWebhookBadge(hasUrl) {
  if (!mybaeWebhookStatusBadge) return;
  mybaeWebhookStatusBadge.textContent = hasUrl ? '✓ Đã kết nối Webhook' : '⚠ Chưa cấu hình Webhook';
  mybaeWebhookStatusBadge.className = hasUrl ? MYBAE_WEBHOOK_BADGE_ON : MYBAE_WEBHOOK_BADGE_OFF;
}

(function initMyBaeWebhook() {
  try {
    const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
    const saved = cfg.mybae_webhook_url || '';
    if (inputMyBaeWebhookUrl && saved) {
      inputMyBaeWebhookUrl.value = saved;
      _setMyBaeWebhookBadge(true);
    }
  } catch (e) {}
  // Đồng bộ lại từ server (mybae_webhook_url hoặc webhook chung)
  fetch('/api/config').then(r => r.json()).then(data => {
    const saved = data.mybae_webhook_url || data.google_sheet_webhook_url || '';
    if (inputMyBaeWebhookUrl && saved && !inputMyBaeWebhookUrl.value) {
      inputMyBaeWebhookUrl.value = saved;
      _setMyBaeWebhookBadge(true);
    }
  }).catch(() => {});
})();

if (btnSaveMyBaeWebhook) {
  btnSaveMyBaeWebhook.addEventListener('click', async () => {
    const url = inputMyBaeWebhookUrl ? inputMyBaeWebhookUrl.value.trim() : '';
    try {
      const res = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mybae_webhook_url: url })
      });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        showSnackbar('💾 Đã lưu Webhook Bypass MyBAE!');
        _setMyBaeWebhookBadge(!!url);
        try {
          const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
          cfg.mybae_webhook_url = url;
          localStorage.setItem('appConfig', JSON.stringify(cfg));
        } catch (e) {}
      } else {
        showSnackbar('❌ ' + (data.message || 'Không thể lưu Webhook'));
      }
    } catch (e) {
      showSnackbar('❌ Lỗi kết nối khi lưu Webhook');
    }
  });
}

// ===================== AUTO MODE =====================
function updateAutoMyBaeModeUI() {
  if (!btnAutoMyBaeModeToggle) return;
  const sidebarBadge = document.getElementById('sidebarAutoMyBaeBadge');
  if (sidebarBadge) sidebarBadge.classList.toggle('hidden', !autoMyBaeMode);
  if (autoMyBaeMode) {
    btnAutoMyBaeModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-orange-500 bg-orange-50 text-orange-700 transition-all shadow-sm animate-pulse cursor-pointer';
    if (autoMyBaeModeText) autoMyBaeModeText.textContent = 'Tự Động: BẬT';
    if (autoMyBaeModeDot) autoMyBaeModeDot.className = 'w-2 h-2 rounded-full bg-orange-600 transition-all animate-bounce';
  } else {
    btnAutoMyBaeModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-slate-200 bg-white text-slate-600 hover:border-orange-400 hover:bg-orange-50 hover:text-orange-700 transition-all shadow-sm cursor-pointer';
    if (autoMyBaeModeText) autoMyBaeModeText.textContent = 'Tự Động: TẮT';
    if (autoMyBaeModeDot) autoMyBaeModeDot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all';
  }
}
updateAutoMyBaeModeUI();

if (btnAutoMyBaeModeToggle) {
  btnAutoMyBaeModeToggle.addEventListener('click', () => {
    autoMyBaeMode = !autoMyBaeMode;
    localStorage.setItem('autoMyBaeMode', autoMyBaeMode ? 'true' : 'false');
    updateAutoMyBaeModeUI();
    if (autoMyBaeMode) {
      showSnackbar('🤖 Chế độ Tự Động Bypass MyBAE đã BẬT!');
      checkAndAutoTriggerMyBae();
    } else {
      showSnackbar('Chế độ Tự Động Bypass MyBAE đã TẮT.');
      if (autoMyBaeCountdownTimer) {
        clearInterval(autoMyBaeCountdownTimer);
        autoMyBaeCountdownTimer = null;
        updateAutoMyBaeModeUI();
      }
    }
  });
}

// Chế độ tự động chỉ nhặt dòng CHƯA có Thao Tác (dòng lỗi phải chạy tay lại để không lặp vô hạn)
function checkAndAutoTriggerMyBae() {
  if (!autoMyBaeMode || isMyBaeRunning) return;
  const pending = currentMyBaeRecords.filter(_mybaeIsPending);
  if (pending.length === 0) return;
  if (autoMyBaeCountdownTimer) return;

  autoMyBaeCountdown = 3;
  if (autoMyBaeModeText) autoMyBaeModeText.textContent = `Tự Động: chạy sau ${autoMyBaeCountdown}s...`;
  showSnackbar(`🤖 Phát hiện ${pending.length} hợp đồng Bypass MyBAE chưa xử lý - Tự khởi động sau 3 giây...`);

  autoMyBaeCountdownTimer = setInterval(() => {
    autoMyBaeCountdown--;
    if (autoMyBaeCountdown > 0) {
      if (autoMyBaeModeText) autoMyBaeModeText.textContent = `Tự Động: chạy sau ${autoMyBaeCountdown}s...`;
    } else {
      clearInterval(autoMyBaeCountdownTimer);
      autoMyBaeCountdownTimer = null;
      if (autoMyBaeModeText) autoMyBaeModeText.textContent = 'Tự Động: BẬT';
      if (!autoMyBaeMode || isMyBaeRunning) return;
      const stillPending = currentMyBaeRecords.filter(_mybaeIsPending);
      if (stillPending.length > 0) {
        showSnackbar(`🚀 Tự động khởi động Bypass MyBAE cho ${stillPending.length} hợp đồng...`);
        runMyBaeProcess(stillPending, true);
      }
    }
  }, 1000);
}

// ===================== LOAD DATA =====================
async function loadMyBaeSheetData() {
  if (!tbodyMyBaeList) return;
  try {
    const res = await fetch(`/api/mybae/sheet-data?_t=${Date.now()}`);
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      currentMyBaeRecords = data.records || [];
      updateMyBaeStats(currentMyBaeRecords);
      if (!isMyBaeRunning) renderMyBaeTable(currentMyBaeRecords);
      if (autoMyBaeMode && !isMyBaeRunning && !autoMyBaeCountdownTimer) {
        checkAndAutoTriggerMyBae();
      }
    } else {
      tbodyMyBaeList.innerHTML = `<tr><td colspan="10" class="text-center py-6 text-rose-500 font-medium">❌ ${escapeHtml(data.message || 'Không thể đọc dữ liệu từ Google Sheet')}</td></tr>`;
    }
  } catch (e) {
    tbodyMyBaeList.innerHTML = '<tr><td colspan="10" class="text-center py-6 text-rose-500 font-medium">❌ Lỗi kết nối khi tải Google Sheet</td></tr>';
  }
}

// ===================== STATS =====================
function updateMyBaeStats(records) {
  let pending = 0, done = 0, error = 0;
  records.forEach(r => {
    if (_mybaeIsSuccess(r)) done++;
    else if (_mybaeIsError(r)) error++;
    else pending++;
  });
  if (mybaeStatTotal)   mybaeStatTotal.textContent   = records.length;
  if (mybaeStatPending) mybaeStatPending.textContent = pending;
  if (mybaeStatDone)    mybaeStatDone.textContent    = done;
  if (mybaeStatError)   mybaeStatError.textContent   = error;
  if (badgeMyBaePending) badgeMyBaePending.textContent = `${pending} chờ xử lý`;
}

let currentMyBaePage = 1;

// ===================== TABLE RENDER =====================
function renderMyBaeTable(records) {
  if (!tbodyMyBaeList) return;
  const dateFilter   = selectDateFilterMyBae ? selectDateFilterMyBae.value : 'today';
  const query        = inputSearchMyBae ? inputSearchMyBae.value.trim().toLowerCase() : '';
  const statusFilter = selectMyBaeFilterStatus ? selectMyBaeFilterStatus.value : 'all';

  // Apply unified date filtering first
  let dateFiltered = records;
  if (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.filterRecords === 'function') {
    dateFiltered = window.UnifiedWorkTabs.filterRecords(records, dateFilter);
  }

  // Render Charts & Top Staff
  if (window.UnifiedWorkTabs) {
    if (typeof window.UnifiedWorkTabs.updateDailyChart === 'function') {
      window.UnifiedWorkTabs.updateDailyChart('mybaeDailyChart', records, dateFilter);
    }
    if (typeof window.UnifiedWorkTabs.updateTopStaff === 'function') {
      window.UnifiedWorkTabs.updateTopStaff('mybaeTopStaffContainer', records, dateFilter);
    }
  }

  const filtered = dateFiltered.filter(r => {
    const shd    = String(r['SHD'] || '').toLowerCase();
    const email  = String(r['Email'] || '').toLowerCase();
    const reason = String(r['Nguyên Nhân 1'] || '').toLowerCase();
    if (query && !shd.includes(query) && !email.includes(query) && !reason.includes(query)) return false;
    if (statusFilter === 'pending') return _mybaeIsPending(r);
    if (statusFilter === 'done')    return _mybaeIsSuccess(r);
    if (statusFilter === 'error')   return _mybaeIsError(r);
    return true;
  });

  // Đảm bảo luôn sắp xếp từ gần nhất đến xa nhất (mới nhất lên đầu)
  const sortedFiltered = (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.sortRecordsNewestFirst === 'function')
    ? window.UnifiedWorkTabs.sortRecordsNewestFirst(filtered)
    : filtered;

  if (mybaeTableFooterText) {
    mybaeTableFooterText.textContent = `Hiển thị ${sortedFiltered.length} bản ghi`;
  }

  if (sortedFiltered.length === 0) {
    tbodyMyBaeList.innerHTML = '<tr><td colspan="10" class="text-center py-8 text-slate-400">Không có bản ghi nào phù hợp với bộ lọc</td></tr>';
    if (window.UnifiedWorkTabs) {
      window.UnifiedWorkTabs.renderPagination('mybaePagination', { total: 0 });
    }
    return;
  }

  // Phân trang 10 dòng 1 trang
  const pageState = window.UnifiedWorkTabs
    ? window.UnifiedWorkTabs.paginate(sortedFiltered, currentMyBaePage, 10)
    : { items: sortedFiltered.slice(0, 10), currentPage: 1, totalPages: Math.ceil(sortedFiltered.length / 10), total: sortedFiltered.length, startIdx: 0, endIdx: Math.min(10, sortedFiltered.length) };
  currentMyBaePage = pageState.currentPage;

  tbodyMyBaeList.innerHTML = '';
  pageState.items.forEach((r, idx) => {
    const globalIdx = pageState.startIdx + idx;
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50 transition-colors';

    const shd    = String(r['SHD'] || '').trim();
    const email  = r['Email'] || '';
    const reason = r['Nguyên Nhân 1'] || '';
    const ngay   = r['Ngày Cập Nhật'] || '';
    const kq     = String(r['Kết Quả'] || '').trim();
    const tt     = String(r['Thao Tác'] || '').trim();
    const tacVu  = r['Tác Vụ'] || 'Bypass MyBAE';
    const isChecked = _mybaeIsPending(r);

    let badgeKq = '<span class="text-slate-300">—</span>';
    if (kq) {
      badgeKq = `<span class="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-sky-50 text-sky-700 border border-sky-100">${escapeHtml(kq)}</span>`;
    }

    let badgeTt = '<span class="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600">Chưa xử lý</span>';
    if (_mybaeIsSuccess(r) && tt) {
      badgeTt = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">✓ ${escapeHtml(tt)}</span>`;
    } else if (_mybaeIsError(r)) {
      badgeTt = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200" title="${escapeHtml(tt)}">✕ ${escapeHtml(tt)}</span>`;
    } else if (tt) {
      badgeTt = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">${escapeHtml(tt)}</span>`;
    }

    tr.innerHTML = `
      <td class="p-3 text-center">
        <input type="checkbox" class="mybae-row-checkbox rounded text-orange-600" data-shd="${escapeHtml(shd)}" ${isChecked ? 'checked' : ''}>
      </td>
      <td class="p-3 text-center text-slate-500 font-mono">${globalIdx + 1}</td>
      <td class="p-3 font-medium text-slate-700">${escapeHtml(tacVu)}</td>
      <td class="p-3"><strong class="font-mono text-orange-700 text-xs">${escapeHtml(shd)}</strong></td>
      <td class="p-3 font-mono text-[11px] text-slate-600">${escapeHtml(email)}</td>
      <td class="p-3 font-medium text-slate-700 text-[11px]">${escapeHtml(reason)}</td>
      <td class="p-3 font-mono text-[11px] text-slate-500">${escapeHtml(ngay)}</td>
      <td class="p-3 text-center">${badgeKq}</td>
      <td class="p-3">${badgeTt}</td>
      <td class="p-3 text-center">
        <button type="button" class="btn-run-single-mybae px-2 py-1 rounded-lg text-[11px] font-semibold bg-orange-50 text-orange-600 hover:bg-orange-100 transition-colors" data-shd="${escapeHtml(shd)}" title="Chạy Bypass MyBAE chỉ cho HĐ này">
          ▶ Chạy
        </button>
      </td>
    `;
    tbodyMyBaeList.appendChild(tr);
  });

  // Render pagination controls
  if (window.UnifiedWorkTabs) {
    window.UnifiedWorkTabs.renderPagination('mybaePagination', pageState, (newPage) => {
      currentMyBaePage = newPage;
      renderMyBaeTable(currentMyBaeRecords);
    });
  }

  updateMyBaeSelectedCount();

  tbodyMyBaeList.querySelectorAll('.btn-run-single-mybae').forEach(btn => {
    btn.addEventListener('click', e => {
      const shd = e.currentTarget.dataset.shd;
      const target = currentMyBaeRecords.find(r => String(r['SHD'] || '').trim() === shd);
      if (target) runMyBaeProcess([target]);
    });
  });

  tbodyMyBaeList.querySelectorAll('.mybae-row-checkbox').forEach(chk => {
    chk.addEventListener('change', updateMyBaeSelectedCount);
  });
}

function updateMyBaeSelectedCount() {
  const checked = tbodyMyBaeList ? tbodyMyBaeList.querySelectorAll('.mybae-row-checkbox:checked').length : 0;
  if (mybaeSelectedCountText) mybaeSelectedCountText.textContent = `(${checked} HĐ đã chọn)`;
}

if (chkMyBaeSelectAll) {
  chkMyBaeSelectAll.addEventListener('change', e => {
    const checked = e.target.checked;
    if (tbodyMyBaeList) {
      tbodyMyBaeList.querySelectorAll('.mybae-row-checkbox').forEach(chk => { chk.checked = checked; });
    }
    updateMyBaeSelectedCount();
  });
}

if (inputSearchMyBae)        inputSearchMyBae.addEventListener('input',  () => { currentMyBaePage = 1; renderMyBaeTable(currentMyBaeRecords); });
if (selectMyBaeFilterStatus) selectMyBaeFilterStatus.addEventListener('change', () => { currentMyBaePage = 1; renderMyBaeTable(currentMyBaeRecords); });
if (selectDateFilterMyBae)   selectDateFilterMyBae.addEventListener('change',   () => { currentMyBaePage = 1; renderMyBaeTable(currentMyBaeRecords); });
if (btnRefreshMyBaeSheetData) {
  btnRefreshMyBaeSheetData.addEventListener('click', () => {
    showSnackbar('Đang làm mới dữ liệu từ Google Sheet (GID: 1795923064)...');
    loadMyBaeSheetData();
  });
}
if (btnClearMyBaeCache) {
  btnClearMyBaeCache.addEventListener('click', async () => {
    try {
      await fetch('/api/mybae/clear-cache', { method: 'POST' });
      showSnackbar('🧹 Đã xóa bộ nhớ đệm Bypass MyBAE!');
      loadMyBaeSheetData();
    } catch (e) {
      showSnackbar('Không thể xóa cache Bypass MyBAE');
    }
  });
}

// ===================== RUN =====================
async function runMyBaeProcess(specificRecords = null, silent = false) {
  if (isMyBaeRunning) {
    if (!silent) showSnackbar('Đang có tiến trình Bypass MyBAE đang chạy...');
    return;
  }

  let recordsToRun = specificRecords;
  if (!recordsToRun) {
    const checkedShds = new Set();
    if (tbodyMyBaeList) {
      tbodyMyBaeList.querySelectorAll('.mybae-row-checkbox:checked').forEach(c => checkedShds.add(c.dataset.shd));
    }
    if (checkedShds.size > 0) {
      recordsToRun = currentMyBaeRecords.filter(r => checkedShds.has(String(r['SHD'] || '').trim()));
    }
  }

  if (!recordsToRun || recordsToRun.length === 0) {
    if (!silent) showSnackbar('⚠️ Chưa có hợp đồng nào được chọn để xử lý!');
    return;
  }

  try {
    setMyBaeRunningState(true);
    const isVisible = chkMyBaeVisible ? chkMyBaeVisible.checked : false;
    const res = await fetch('/api/mybae/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ headless: !isVisible, records: recordsToRun })
    });
    const data = await res.json();
    if (res.ok && data.status === 'started') {
      const modeDesc = !isVisible ? 'chạy ngầm' : 'đang mở Chrome trực tiếp trên màn hình';
      showSnackbar(`🚀 Đã khởi động Bypass MyBAE cho ${data.count} hợp đồng (${modeDesc})!`);
    } else {
      setMyBaeRunningState(false);
      if (!silent || data.status !== 'busy') showSnackbar(data.message || 'Không thể bắt đầu Bypass MyBAE');
    }
  } catch (err) {
    setMyBaeRunningState(false);
    showSnackbar(`Lỗi kết nối máy chủ: ${err}`);
  }
}

function setMyBaeRunningState(running) {
  isMyBaeRunning = running;
  if (btnRunAutoMyBae) btnRunAutoMyBae.disabled = running;
  if (mybaeSpinner)    mybaeSpinner.style.display = running ? 'inline-block' : 'none';
  if (mybaeRunIcon)    mybaeRunIcon.style.display = running ? 'none' : 'inline-block';
  if (mybaeRunText)    mybaeRunText.textContent   = running ? 'Đang Xử Lý Bypass MyBAE...' : 'Bắt Đầu Bypass MyBAE';
  if (mybaeProgressTracker) mybaeProgressTracker.style.display = running ? 'block' : 'none';
}

async function pollMyBaeStatus() {
  try {
    const res = await fetch('/api/mybae/live-status');
    if (!res.ok) return;
    const data = await res.json();
    const task = data.task || {};

    if (task.is_running) {
      setMyBaeRunningState(true);
      const cur   = task.current_index || 0;
      const total = task.total || 1;
      const pct   = Math.min(100, Math.round((cur / Math.max(1, total)) * 100));
      if (mybaeTrackerPercent) mybaeTrackerPercent.textContent = `${pct}%`;
      if (mybaeProgressBar)    mybaeProgressBar.style.width    = `${pct}%`;
      if (mybaeTrackerStatus)  mybaeTrackerStatus.textContent  = task.message || `Đang xử lý ${cur}/${total}: HĐ ${task.current_shd || ''}`;
    } else if (isMyBaeRunning) {
      setMyBaeRunningState(false);
      showSnackbar('✅ Tiến trình Bypass MyBAE đã hoàn thành!');
      loadMyBaeSheetData();
    }
  } catch (e) {}
}

if (btnRunAutoMyBae) {
  btnRunAutoMyBae.addEventListener('click', () => runMyBaeProcess());
}

// Live Terminal Logs Rendering cho Bypass MyBAE
function renderMyBaeTerminalLogs(logs) {
  if (!mybaeLogTerminal || !logs || logs.length === 0) return;

  const relevant = logs.filter(l => {
    const txt = (l.text || '').toLowerCase();
    return txt.includes('mybae') || txt.includes('đăng nhập');
  });
  const displayLogs = (relevant.length > 0 ? relevant : logs).slice(-40);
  mybaeLogTerminal.innerHTML = '';
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
    mybaeLogTerminal.appendChild(item);
  });
  mybaeLogTerminal.scrollTop = mybaeLogTerminal.scrollHeight;
}

if (btnClearMyBaeLogs && mybaeLogTerminal) {
  btnClearMyBaeLogs.addEventListener('click', () => {
    mybaeLogTerminal.innerHTML = '<div class="text-slate-500 italic">Nhật ký Bypass MyBAE đã được làm sạch</div>';
  });
}

// Xuất data xử lý Bypass MyBAE ra Excel
if (btnExportMyBaeData) {
  btnExportMyBaeData.addEventListener('click', () => {
    showSnackbar('Đang chuẩn bị file Excel xuất dữ liệu Bypass MyBAE...');
    window.location.href = `/api/mybae/export?gid=1795923064&status=all`;
  });
}

registerTab('tab-bypass-mybae', {
  title: 'Auto Bypass MyBAE',
  onActivate() {
    if (currentMyBaeRecords.length > 0 && !isMyBaeRunning) renderMyBaeTable(currentMyBaeRecords);
    loadMyBaeSheetData();
  }
});
