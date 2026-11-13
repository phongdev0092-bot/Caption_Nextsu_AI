// ==========================================================
// COMPONENT: AUTO SPAMPOOL & DEACTIVE IPV6 (tab-spampool)
// Hệ thống: Radius Portal (http://radius-portal.fpt.net)
// Google Sheet GID: 2070394876
// ==========================================================

const badgeSpamPoolPending       = document.getElementById('badgeSpamPoolPending');
const spampoolStatTotal          = document.getElementById('spampoolStatTotal');
const spampoolStatPending        = document.getElementById('spampoolStatPending');
const spampoolStatDone           = document.getElementById('spampoolStatDone');
const spampoolStatError          = document.getElementById('spampoolStatError');

const btnRefreshSpamPoolSheetData= document.getElementById('btnRefreshSpamPoolSheetData');
const btnClearSpamPoolCache      = document.getElementById('btnClearSpamPoolCache');
const btnExportSpamPoolData      = document.getElementById('btnExportSpamPoolData');
const btnSpamPoolLogin            = document.getElementById('btnSpamPoolLogin');

const inputSpamPoolWebhookUrl    = document.getElementById('inputSpamPoolWebhookUrl');
const btnSaveSpamPoolWebhook     = document.getElementById('btnSaveSpamPoolWebhook');
const spampoolWebhookStatusBadge = document.getElementById('spampoolWebhookStatusBadge');

const btnStartAutoSpamPool       = document.getElementById('btnStartAutoSpamPool');
const btnStopAutoSpamPool        = document.getElementById('btnStopAutoSpamPool');
const cbSpamPoolVisibleChrome    = document.getElementById('cbSpamPoolVisibleChrome');

const inputSpamPoolSingleSHD     = document.getElementById('inputSpamPoolSingleSHD');
const btnTestSingleSpamPool      = document.getElementById('btnTestSingleSpamPool');

const spampoolProgressContainer  = document.getElementById('spampoolProgressContainer');
const spampoolProgressText       = document.getElementById('spampoolProgressText');
const spampoolProgressPercent    = document.getElementById('spampoolProgressPercent');
const spampoolProgressBar        = document.getElementById('spampoolProgressBar');

const inputFilterSpamPoolTable   = document.getElementById('inputFilterSpamPoolTable');
const selectFilterSpamPoolStatus = document.getElementById('selectFilterSpamPoolStatus');
const spampoolTableCount         = document.getElementById('spampoolTableCount');
const tbodySpamPool              = document.getElementById('tbodySpamPool');

const btnAutoSpamPoolModeToggle  = document.getElementById('btnAutoSpamPoolModeToggle');
const autoSpamPoolModeDot        = document.getElementById('autoSpamPoolModeDot');
const autoSpamPoolModeText       = document.getElementById('autoSpamPoolModeText');
const selectDateFilterSpamPool   = document.getElementById('selectDateFilterSpamPool');
const spampoolLogTerminal        = document.getElementById('spampoolLogTerminal');
const btnClearSpamPoolLogs       = document.getElementById('btnClearSpamPoolLogs');

currentSpamPoolRecords = currentSpamPoolRecords || [];
isSpamPoolRunning = false;
autoSpamPoolMode = localStorage.getItem('autoSpamPoolMode') !== 'false';
autoSpamPoolCountdownTimer = null;
autoSpamPoolCountdown = 0;
let spampoolPollTimer = null;


// ===================== AUTO MODE UI =====================
function updateAutoSpamPoolModeUI() {
  if (!btnAutoSpamPoolModeToggle) return;
  const sidebarBadge = document.getElementById('sidebarAutoSpamPoolBadge');
  if (autoSpamPoolMode) {
    btnAutoSpamPoolModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-teal-500 bg-teal-50 text-teal-700 transition-all shadow-sm animate-pulse cursor-pointer';
    if (autoSpamPoolModeText) autoSpamPoolModeText.textContent = 'Tự Động: BẬT';
    if (autoSpamPoolModeDot) autoSpamPoolModeDot.className = 'w-2 h-2 rounded-full bg-teal-600 transition-all animate-bounce';
    if (sidebarBadge) sidebarBadge.classList.remove('hidden');
  } else {
    btnAutoSpamPoolModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-slate-200 bg-white text-slate-600 hover:border-teal-400 hover:bg-teal-50 hover:text-teal-700 transition-all shadow-sm cursor-pointer';
    if (autoSpamPoolModeText) autoSpamPoolModeText.textContent = 'Tự Động: TẮT';
    if (autoSpamPoolModeDot) autoSpamPoolModeDot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all';
    if (sidebarBadge) sidebarBadge.classList.add('hidden');
  }
}
updateAutoSpamPoolModeUI();

if (btnAutoSpamPoolModeToggle) {
  btnAutoSpamPoolModeToggle.addEventListener('click', () => {
    autoSpamPoolMode = !autoSpamPoolMode;
    localStorage.setItem('autoSpamPoolMode', autoSpamPoolMode ? 'true' : 'false');
    updateAutoSpamPoolModeUI();
    // Đồng bộ lên server orchestrator
    fetch('/api/auto-modes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spampool: autoSpamPoolMode })
    }).catch(() => {});

    if (autoSpamPoolMode) {
      showSnackbar('🤖 Chế độ Tự Động SpamPool đã BẬT (Auto nền máy chủ)!');
    } else {
      showSnackbar('Chế độ Tự Động SpamPool đã TẮT.');
    }
  });
}

function checkAndAutoTriggerSpamPool() {
  // Auto nền máy chủ (_auto_orchestrator_loop) tự động quét và chạy ngầm, không cần trình duyệt kích hoạt trùng lặp
}

// ===================== WEBHOOK =====================
(function initSpamPoolWebhook() {
  try {
    const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
    const saved = cfg.spampool_webhook_url || cfg.google_sheet_webhook_url || '';
    if (inputSpamPoolWebhookUrl && saved) {
      inputSpamPoolWebhookUrl.value = saved;
      if (spampoolWebhookStatusBadge) {
        spampoolWebhookStatusBadge.textContent = '✓ Đã kết nối Webhook';
        spampoolWebhookStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200';
      }
    }
  } catch (e) {}
})();

if (btnSaveSpamPoolWebhook) {
  btnSaveSpamPoolWebhook.addEventListener('click', async () => {
    const url = inputSpamPoolWebhookUrl ? inputSpamPoolWebhookUrl.value.trim() : '';
    try {
      const res = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spampool_webhook_url: url })
      });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        showSnackbar('💾 Đã lưu Webhook SpamPool!');
        if (spampoolWebhookStatusBadge) {
          spampoolWebhookStatusBadge.textContent = url ? '✓ Đã kết nối Webhook' : '⚠ Chưa cấu hình Webhook';
          spampoolWebhookStatusBadge.className = url
            ? 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200'
            : 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200';
        }
        try {
          const cfg = JSON.parse(localStorage.getItem('appConfig') || '{}');
          cfg.spampool_webhook_url = url;
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

// ===================== TẢI DỮ LIỆU SHEET =====================
async function loadSpamPoolSheetData() {
  if (tbodySpamPool && currentSpamPoolRecords.length === 0) {
    if (tbodySpamPool.children.length === 0 ||
        (tbodySpamPool.children.length === 1 && tbodySpamPool.children[0].textContent.includes('tải'))) {
      tbodySpamPool.innerHTML = `
        <tr>
          <td colspan="9" class="p-8 text-center text-slate-400">
            <div class="flex items-center justify-center gap-2">
              <svg class="animate-spin h-5 w-5 text-teal-600" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
              <span>Đang tải dữ liệu từ Google Sheet...</span>
            </div>
          </td>
        </tr>
      `;
    }
  }

  try {
    const res = await fetch('/api/spampool/sheet?_t=' + Date.now());
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      currentSpamPoolRecords = data.records || [];
      if (!isSpamPoolRunning) renderSpamPoolTable();
      updateSpamPoolStats();
      if (autoSpamPoolMode && !isSpamPoolRunning && !autoSpamPoolCountdownTimer) {
        checkAndAutoTriggerSpamPool();
      }
    } else {
      if (currentSpamPoolRecords.length === 0 && tbodySpamPool) {
        tbodySpamPool.innerHTML = `
          <tr>
            <td colspan="9" class="p-8 text-center text-rose-500 font-medium">
              ❌ Lỗi tải dữ liệu: ${data.message || 'Không xác định'}
            </td>
          </tr>
        `;
      }
    }
  } catch (e) {
    if (currentSpamPoolRecords.length === 0 && tbodySpamPool) {
      tbodySpamPool.innerHTML = `
        <tr>
          <td colspan="9" class="p-8 text-center text-rose-500 font-medium">
            ❌ Không thể kết nối đến máy chủ nội bộ.
          </td>
        </tr>
      `;
    }
  }
}

function isProcessedRow(kq, tt) {
  const k = String(kq || '').toLowerCase();
  const t = String(tt || '').toLowerCase();
  if (t.includes('thành công kết thúc') ||
      t.includes('spampool trước đó') || t.includes('đã được spampool') ||
      t.includes('deactive ip') || t.includes('deactivate ip') ||
      t.includes('0.0.0.0 trước đó') || t.includes('hợp đồng đã được deactive')) return true;
  if (t.includes('chưa cập nhật') || !t.trim() || t.includes('chưa xử lý')) return false;
  if (k.includes('đã xử lý') && !t.includes('chưa') && !t.includes('lỗi') && !t.includes('không')) return true;
  return false;
}

function isPendingRow(kq, tt) {
  if (isProcessedRow(kq, tt)) return false;
  const k = String(kq || '').toLowerCase();
  const t = String(tt || '').toLowerCase();
  if (t.includes('chưa cập nhật') || k.includes('chưa cập nhật')) return true;
  if (t.includes('chưa xử lý') || k.includes('chưa xử lý')) return true;
  if (!t.trim() || !k.trim()) return true;
  return false;
}

function updateSpamPoolStats() {
  const total = currentSpamPoolRecords.length;
  let pending = 0;
  let done = 0;
  let error = 0;

  currentSpamPoolRecords.forEach(r => {
    const kq = r['Kết Quả'] || '';
    const tt = r['Thao Tác'] || '';
    if (isProcessedRow(kq, tt)) {
      done++;
    } else if (isPendingRow(kq, tt)) {
      pending++;
    } else {
      error++;
    }
  });

  if (spampoolStatTotal) spampoolStatTotal.textContent = total;
  if (spampoolStatPending) spampoolStatPending.textContent = pending;
  if (spampoolStatDone) spampoolStatDone.textContent = done;
  if (spampoolStatError) spampoolStatError.textContent = error;
  if (badgeSpamPoolPending) badgeSpamPoolPending.textContent = `${pending} chờ xử lý`;
}

let currentSpamPoolPage = 1;

function renderSpamPoolTable() {
  if (!tbodySpamPool) return;

  // Đồng bộ xóa cột ID khỏi thead và ẩn nhãn GID nếu DOM cũ còn lưu trên trình duyệt
  const tblSpam = document.getElementById('tableSpamPool');
  if (tblSpam) {
    tblSpam.querySelectorAll('thead th').forEach(th => {
      if (th.textContent.trim().toUpperCase() === 'ID') th.remove();
    });
  }
  const tabSpamEl = document.getElementById('tab-spampool');
  if (tabSpamEl) {
    tabSpamEl.querySelectorAll('span, div').forEach(el => {
      if (el.children.length === 0 && /GID:\s*\d+/i.test(el.textContent)) {
        if (el.textContent.trim().startsWith('GID:')) el.remove();
        else el.textContent = el.textContent.replace(/\(?\s*GID:\s*\d+\s*\)?/gi, '').trim();
      }
    });
  }

  const dateFilter = selectDateFilterSpamPool ? selectDateFilterSpamPool.value : 'today';
  const search = inputFilterSpamPoolTable ? inputFilterSpamPoolTable.value.trim().toLowerCase() : '';
  const filter = selectFilterSpamPoolStatus ? selectFilterSpamPoolStatus.value : 'ALL';

  // Apply unified date filtering first
  let dateFiltered = currentSpamPoolRecords;
  if (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.filterRecords === 'function') {
    dateFiltered = window.UnifiedWorkTabs.filterRecords(currentSpamPoolRecords, dateFilter);
  }

  // Render Charts & Top Staff
  if (window.UnifiedWorkTabs) {
    if (typeof window.UnifiedWorkTabs.updateDailyChart === 'function') {
      window.UnifiedWorkTabs.updateDailyChart('spampoolDailyChart', currentSpamPoolRecords, dateFilter);
    }
    if (typeof window.UnifiedWorkTabs.updateTopStaff === 'function') {
      window.UnifiedWorkTabs.updateTopStaff('spampoolTopStaffContainer', currentSpamPoolRecords, dateFilter);
    }
  }

  const filtered = dateFiltered.filter(r => {
    const kq = String(r['Kết Quả'] || '');
    const tt = String(r['Thao Tác'] || '');

    // Status filter
    if (filter === 'PENDING' && !isPendingRow(kq, tt)) return false;
    if (filter === 'DONE' && !isProcessedRow(kq, tt)) return false;
    if (filter === 'ERROR' && (isPendingRow(kq, tt) || isProcessedRow(kq, tt))) return false;

    // Search query
    if (search) {
      const matchText = [
        r['ID'], r['Tác Vụ'], r['Email'], r['MSNV'], r['Account Inside'],
        r['SHD'], r['Nguyên Nhân 1'], r['Ngày Cập Nhật'], kq, tt
      ].join(' ').toLowerCase();
      if (!matchText.includes(search)) return false;
    }
    return true;
  });

  // Đảm bảo luôn sắp xếp từ gần nhất đến xa nhất (mới nhất lên đầu)
  const sortedFiltered = (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.sortRecordsNewestFirst === 'function')
    ? window.UnifiedWorkTabs.sortRecordsNewestFirst(filtered)
    : filtered;

  if (spampoolTableCount) {
    spampoolTableCount.textContent = `Hiển thị ${sortedFiltered.length} / ${currentSpamPoolRecords.length} bản ghi`;
  }

  if (sortedFiltered.length === 0) {
    tbodySpamPool.innerHTML = `
      <tr>
        <td colspan="9" class="p-8 text-center text-slate-400">
          Không có bản ghi nào phù hợp với bộ lọc.
        </td>
      </tr>
    `;
    if (window.UnifiedWorkTabs) {
      window.UnifiedWorkTabs.renderPagination('spampoolPagination', { total: 0 });
    }
    return;
  }

  // Phân trang 10 dòng 1 trang
  const pageState = window.UnifiedWorkTabs
    ? window.UnifiedWorkTabs.paginate(sortedFiltered, currentSpamPoolPage, 10)
    : { items: sortedFiltered.slice(0, 10), currentPage: 1, totalPages: Math.ceil(sortedFiltered.length / 10), total: sortedFiltered.length, startIdx: 0, endIdx: Math.min(10, sortedFiltered.length) };
  currentSpamPoolPage = pageState.currentPage;

  tbodySpamPool.innerHTML = pageState.items.map((r, idx) => {
    const globalIdx = pageState.startIdx + idx;
    const shd = r['SHD'] || '';
    const id = r['ID'] || '';
    const tacVu = r['Tác Vụ'] || '';
    const email = r['Email'] || '';
    const nguyenNhan = r['Nguyên Nhân 1'] || '';
    const ngay = r['Ngày Cập Nhật'] || '';
    const kq = r['Kết Quả'] || '';
    const tt = r['Thao Tác'] || '';

    // Badges
    let kqBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">Chưa cập nhật</span>';
    if (isProcessedRow(kq, tt)) {
      kqBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">✓ Đã xử lý</span>';
    } else if (kq.toLowerCase().includes('lỗi') || tt.toLowerCase().includes('lỗi')) {
      kqBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-100 text-rose-800 border border-rose-300">✕ Lỗi</span>';
    } else if (isPendingRow(kq, tt)) {
      kqBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-300">⏳ Chưa cập nhật</span>';
    }

    let ttClass = 'text-slate-600';
    if (tt.includes('thành công')) ttClass = 'text-emerald-700 font-semibold';
    else if (tt.includes('Trước Đó') || tt.includes('Trước đó')) ttClass = 'text-teal-700 font-semibold';
    else if (tt.toLowerCase().includes('lỗi')) ttClass = 'text-rose-600 font-medium';

    return `
      <tr class="hover:bg-teal-50/40 transition-colors">
        <td class="p-3 text-center text-slate-400 font-mono text-[11px]">${globalIdx + 1}</td>
        <td class="p-3 text-slate-800 font-medium">${tacVu}</td>
        <td class="p-3 text-slate-600">${email}</td>
        <td class="p-3 font-mono font-bold text-teal-700 text-xs">${shd}</td>
        <td class="p-3 text-slate-600 text-[11px]">${nguyenNhan}</td>
        <td class="p-3 text-slate-500 font-mono text-[11px]">${ngay}</td>
        <td class="p-3">${kqBadge}</td>
        <td class="p-3 text-xs ${ttClass}">${tt || '<span class="text-slate-300">Chưa có</span>'}</td>
        <td class="p-3 text-center">
          <button type="button" onclick="runSingleSpamPoolRow('${shd}', '${id}', '${(tacVu || '').replace(/'/g, "\\'")}')"
            class="px-2.5 py-1 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-700 border border-teal-200 text-[11px] font-semibold transition-all shadow-2xs hover:shadow-xs cursor-pointer"
            title="Thực thi tác vụ cho HĐ ${shd}">
            ⚡ Chạy
          </button>
        </td>
      </tr>
    `;
  }).join('');

  // Render pagination controls
  if (window.UnifiedWorkTabs) {
    window.UnifiedWorkTabs.renderPagination('spampoolPagination', pageState, (newPage) => {
      currentSpamPoolPage = newPage;
      renderSpamPoolTable();
    });
  }
}

// ===================== TIẾN TRÌNH AUTO =====================
async function startAutoSpamPool() {
  if (isSpamPoolRunning) return;

  const visible = cbSpamPoolVisibleChrome ? cbSpamPoolVisibleChrome.checked : true;
  try {
    btnStartAutoSpamPool.classList.add('hidden');
    if (btnStopAutoSpamPool) btnStopAutoSpamPool.classList.remove('hidden');
    if (spampoolProgressContainer) spampoolProgressContainer.classList.remove('hidden');

    const res = await fetch('/api/spampool/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ headless: !visible })
    });
    const data = await res.json();
    if (res.ok && data.status === 'started') {
      isSpamPoolRunning = true;
      showSnackbar('🚀 Đã bắt đầu tiến trình Auto SpamPool!');
      startSpamPoolPolling();
    } else {
      btnStartAutoSpamPool.classList.remove('hidden');
      if (btnStopAutoSpamPool) btnStopAutoSpamPool.classList.add('hidden');
      showSnackbar('❌ ' + (data.message || 'Không thể khởi động Auto SpamPool'));
    }
  } catch (e) {
    btnStartAutoSpamPool.classList.remove('hidden');
    if (btnStopAutoSpamPool) btnStopAutoSpamPool.classList.add('hidden');
    showSnackbar('❌ Lỗi kết nối máy chủ');
  }
}

async function stopAutoSpamPool() {
  try {
    const res = await fetch('/api/spampool/stop', { method: 'POST' });
    const data = await res.json();
    showSnackbar('⏹ ' + (data.message || 'Đã gửi lệnh dừng tiến trình SpamPool'));
  } catch (e) {
    showSnackbar('❌ Không thể dừng tiến trình');
  }
}

function startSpamPoolPolling() {
  if (spampoolPollTimer) clearInterval(spampoolPollTimer);
  spampoolPollTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/spampool/status?_t=' + Date.now());
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        const t = data.task || {};
        const total = t.total || 0;
        const current = t.current_index || 0;
        const msg = t.message || 'Đang thực hiện...';
        const isRunning = t.is_running || false;

        const percent = total > 0 ? Math.round((current / total) * 100) : 0;
        if (spampoolProgressBar) spampoolProgressBar.style.width = percent + '%';
        if (spampoolProgressPercent) spampoolProgressPercent.textContent = percent + '%';
        if (spampoolProgressText) spampoolProgressText.textContent = msg;

        if (!isRunning) {
          clearInterval(spampoolPollTimer);
          isSpamPoolRunning = false;
          if (btnStartAutoSpamPool) btnStartAutoSpamPool.classList.remove('hidden');
          if (btnStopAutoSpamPool) btnStopAutoSpamPool.classList.add('hidden');
          loadSpamPoolSheetData();
        }
      }
    } catch (e) {}
  }, 2000);
}

// ===================== TEST NHANH 1 HĐ =====================
window.runSingleSpamPoolRow = function(shd, rowId = '', tacVu = '') {
  if (!shd) return;
  if (!tacVu) {
    let rec = null;
    if (rowId) {
      rec = currentSpamPoolRecords.find(r => String(r['ID'] || '').trim() === String(rowId).trim());
    }
    if (!rec) {
      rec = currentSpamPoolRecords.find(r => String(r['SHD'] || '').trim().toUpperCase() === String(shd).trim().toUpperCase() && isPendingRow(r['Kết Quả'], r['Thao Tác']));
    }
    if (!rec) {
      rec = currentSpamPoolRecords.find(r => String(r['SHD'] || '').trim().toUpperCase() === String(shd).trim().toUpperCase());
    }
    tacVu = rec ? (rec['Tác Vụ'] || '') : '';
    if (!rowId && rec) rowId = rec['ID'] || '';
  }
  runSingleSpamPoolAction(shd, tacVu, rowId);
};

async function runSingleSpamPoolAction(shd, tacVu = '', rowId = '') {
  if (!shd) return;
  const tvLow = (tacVu || '').toLowerCase();
  const isDeactiveIp = tvLow.includes('0.0.0.0') || tvLow.includes('deactive') || tvLow.includes('deactivate');
  const actionLabel = isDeactiveIp ? 'Deactive IP 0.0.0.0' : 'SpamPool';
  const visible = cbSpamPoolVisibleChrome ? cbSpamPoolVisibleChrome.checked : true;
  showSnackbar(`⚡ Đang kích hoạt ${actionLabel} cho HĐ ${shd}... Trình duyệt Chrome đang mở...`);

  // Loading state trên nút Chạy Thử
  const oldBtnHtml = btnTestSingleSpamPool ? btnTestSingleSpamPool.innerHTML : '';
  if (btnTestSingleSpamPool) {
    btnTestSingleSpamPool.disabled = true;
    btnTestSingleSpamPool.innerHTML = `<span class="inline-block animate-spin">⏳</span> <span>Đang chạy ${shd}...</span>`;
    btnTestSingleSpamPool.classList.add('opacity-75');
  }

  if (spampoolProgressContainer) spampoolProgressContainer.classList.remove('hidden');
  if (spampoolProgressText) spampoolProgressText.textContent = `Đang chạy thử ${actionLabel} cho HĐ ${shd} (Radius Portal)...`;
  if (spampoolProgressBar) spampoolProgressBar.style.width = '50%';

  try {
    const res = await fetch('/api/spampool/test_single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shd: shd, row_id: rowId, tac_vu: tacVu, headless: !visible })
    });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showSnackbar(`✅ HĐ ${shd}: ${data.thao_tac || 'Thành công'}`);
      if (spampoolProgressText) spampoolProgressText.textContent = `✅ Hoàn tất HĐ ${shd}: ${data.thao_tac || 'Đã xử lý'}`;
      if (spampoolProgressBar) spampoolProgressBar.style.width = '100%';
      loadSpamPoolSheetData();
    } else {
      showSnackbar(`❌ HĐ ${shd}: ${data.message || 'Thất bại'}`);
      if (spampoolProgressText) spampoolProgressText.textContent = `❌ Lỗi HĐ ${shd}: ${data.message || 'Thất bại'}`;
    }
  } catch (e) {
    showSnackbar('❌ Lỗi kết nối khi test 1 HĐ: ' + (e.message || e));
    if (spampoolProgressText) spampoolProgressText.textContent = `❌ Lỗi kết nối khi test HĐ ${shd}`;
  } finally {
    if (btnTestSingleSpamPool) {
      btnTestSingleSpamPool.disabled = false;
      btnTestSingleSpamPool.innerHTML = oldBtnHtml || '<span>⚡</span> <span>Chạy Thử</span>';
      btnTestSingleSpamPool.classList.remove('opacity-75');
    }
    setTimeout(() => {
      if (!isSpamPoolRunning && spampoolProgressContainer) {
        spampoolProgressContainer.classList.add('hidden');
      }
    }, 4000);
  }
}

// ===================== XÓA CACHE =====================
async function clearSpamPoolCache() {
  if (!confirm('Bạn có chắc chắn muốn xóa cache trạng thái SpamPool để xử lý lại từ đầu?')) return;
  try {
    const res = await fetch('/api/spampool/clear_cache', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showSnackbar('🧹 Đã xóa sạch cache SpamPool!');
      loadSpamPoolSheetData();
    } else {
      showSnackbar('❌ Lỗi xóa cache');
    }
  } catch (e) {
    showSnackbar('❌ Lỗi kết nối');
  }
}

// ===================== XUẤT EXCEL =====================
function exportSpamPoolExcel() {
  if (currentSpamPoolRecords.length === 0) {
    showSnackbar('⚠ Không có dữ liệu để xuất file');
    return;
  }
  const headers = ['ID', 'Tác Vụ', 'Email', 'MSNV', 'Account Inside', 'SHD', 'Nguyên Nhân 1', 'Ngày Cập Nhật', 'Kết Quả', 'Thao Tác'];
  const rows = [headers];
  currentSpamPoolRecords.forEach(r => {
    rows.push(headers.map(h => `"${String(r[h] || '').replace(/"/g, '""')}"`));
  });
  const csvContent = '\uFEFF' + rows.map(e => e.join(',')).join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `SpamPool_Results_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showSnackbar('📥 Đã tải file Excel kết quả SpamPool!');
}

// ===================== EVENT LISTENERS =====================
if (btnRefreshSpamPoolSheetData) {
  btnRefreshSpamPoolSheetData.addEventListener('click', () => {
    loadSpamPoolSheetData();
    showSnackbar('🔄 Đang làm mới dữ liệu từ Google Sheet...');
  });
}

if (btnClearSpamPoolCache) {
  btnClearSpamPoolCache.addEventListener('click', clearSpamPoolCache);
}

if (btnExportSpamPoolData) {
  btnExportSpamPoolData.addEventListener('click', exportSpamPoolExcel);
}

if (btnSpamPoolLogin) {
  btnSpamPoolLogin.addEventListener('click', async () => {
    const visible = cbSpamPoolVisibleChrome ? cbSpamPoolVisibleChrome.checked : true;
    showSnackbar('🔐 Đang xác thực đăng nhập Radius Portal...');
    if (spampoolProgressContainer) spampoolProgressContainer.classList.remove('hidden');
    if (spampoolProgressText) spampoolProgressText.textContent = 'Đang tiến hành đăng nhập Radius Portal qua IAM & Microsoft Azure AD SSO...';
    if (spampoolProgressBar) spampoolProgressBar.style.width = '40%';
    try {
      const res = await fetch('/api/spampool/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ headless: !visible, force: true })
      });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        showSnackbar('✅ ' + (data.message || 'Đăng nhập Radius Portal thành công!'));
        if (spampoolProgressText) spampoolProgressText.textContent = '✅ Đã xác thực thành công vào Radius Portal (' + (data.url || '') + ')';
        if (spampoolProgressBar) spampoolProgressBar.style.width = '100%';
      } else {
        showSnackbar('❌ ' + (data.message || 'Đăng nhập thất bại'));
        if (spampoolProgressText) spampoolProgressText.textContent = '❌ Đăng nhập thất bại: ' + (data.message || '');
      }
    } catch (e) {
      showSnackbar('❌ Lỗi kết nối đến server: ' + e.message);
    }
  });
}

if (btnStartAutoSpamPool) {
  btnStartAutoSpamPool.addEventListener('click', startAutoSpamPool);
}

if (btnStopAutoSpamPool) {
  btnStopAutoSpamPool.addEventListener('click', stopAutoSpamPool);
}

if (btnTestSingleSpamPool) {
  btnTestSingleSpamPool.addEventListener('click', () => {
    let shd = inputSpamPoolSingleSHD ? inputSpamPoolSingleSHD.value.trim().toUpperCase() : '';
    if (!shd) {
      // Tự động lấy HĐ đầu tiên đang chờ xử lý từ danh sách sheet
      const firstPending = currentSpamPoolRecords.find(r => isPendingRow(r['Kết Quả'], r['Thao Tác'])) || currentSpamPoolRecords[0];
      if (firstPending && firstPending['SHD']) {
        shd = String(firstPending['SHD']).trim().toUpperCase();
        if (inputSpamPoolSingleSHD) inputSpamPoolSingleSHD.value = shd;
        showSnackbar(`⚡ Tự động chọn HĐ [${shd}] từ Google Sheet để chạy thử`);
      }
    }
    if (!shd) {
      showSnackbar('⚠ Vui lòng nhập Số Hợp Đồng để chạy thử');
      return;
    }
    let rec = currentSpamPoolRecords.find(r => String(r['SHD'] || '').trim().toUpperCase() === shd && isPendingRow(r['Kết Quả'], r['Thao Tác']));
    if (!rec) {
      rec = currentSpamPoolRecords.find(r => String(r['SHD'] || '').trim().toUpperCase() === shd);
    }
    const tacVu = rec ? (rec['Tác Vụ'] || '') : '';
    const rowId = rec ? (rec['ID'] || '') : '';
    runSingleSpamPoolAction(shd, tacVu, rowId);
  });
}

if (inputFilterSpamPoolTable) {
  inputFilterSpamPoolTable.addEventListener('input', () => { currentSpamPoolPage = 1; renderSpamPoolTable(); });
}

if (selectFilterSpamPoolStatus) {
  selectFilterSpamPoolStatus.addEventListener('change', () => { currentSpamPoolPage = 1; renderSpamPoolTable(); });
}

if (selectDateFilterSpamPool) {
  selectDateFilterSpamPool.addEventListener('change', () => { currentSpamPoolPage = 1; renderSpamPoolTable(); });
}

// Live Terminal Logs Rendering cho SpamPool
function renderSpamPoolTerminalLogs(logs) {
  if (!spampoolLogTerminal || !logs || logs.length === 0) return;

  const relevant = logs.filter(l => {
    const txt = (l.text || '').toLowerCase();
    return txt.includes('spampool') || txt.includes('radius') || txt.includes('savecus') || txt.includes('azure') || txt.includes('iam');
  });
  const displayLogs = (relevant.length > 0 ? relevant : logs).slice(-40);
  spampoolLogTerminal.innerHTML = '';
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
    spampoolLogTerminal.appendChild(item);
  });
  spampoolLogTerminal.scrollTop = spampoolLogTerminal.scrollHeight;
}

if (btnClearSpamPoolLogs && spampoolLogTerminal) {
  btnClearSpamPoolLogs.addEventListener('click', () => {
    spampoolLogTerminal.innerHTML = '<div class="text-slate-500 italic">Nhật ký SpamPool đã được làm sạch</div>';
  });
}

// Đăng ký tab với hệ thống chuyển tab
if (typeof registerTab === 'function') {
  registerTab('tab-spampool', {
    title: 'Auto SpamPool & Deactive IPv6',
    onActivate: () => {
      loadSpamPoolSheetData();
    }
  });
}

// Xuất các hàm ra phạm vi toàn cục cho main.js polling
window.pollSpamPoolStatus = pollSpamPoolStatus;
window.loadSpamPoolSheetData = loadSpamPoolSheetData;
window.updateAutoSpamPoolModeUI = updateAutoSpamPoolModeUI;
window.checkAndAutoTriggerSpamPool = checkAndAutoTriggerSpamPool;
window.renderSpamPoolTerminalLogs = renderSpamPoolTerminalLogs;


