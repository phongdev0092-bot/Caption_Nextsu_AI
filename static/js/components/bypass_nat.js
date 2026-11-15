// ==========================================================
// COMPONENT: AUTO BYPASS NAT (tab-bypass-nat)
// Hệ thống: Radius Portal (http://radius-portal.fpt.net)
// Google Sheet GID: 1907537423
// ==========================================================

const badgeBypassNatPending        = document.getElementById('badgeBypassNatPending');
const bypassNatStatTotal           = document.getElementById('bypassNatStatTotal');
const bypassNatStatPending         = document.getElementById('bypassNatStatPending');
const bypassNatStatDone            = document.getElementById('bypassNatStatDone');
const bypassNatStatError           = document.getElementById('bypassNatStatError');

const btnRefreshBypassNatSheetData = document.getElementById('btnRefreshBypassNatSheetData');
const btnClearBypassNatCache       = document.getElementById('btnClearBypassNatCache');
const btnExportBypassNatData       = document.getElementById('btnExportBypassNatData');
const btnBypassNatLogin            = document.getElementById('btnBypassNatLogin');

const inputBypassNatWebhookUrl     = document.getElementById('inputBypassNatWebhookUrl');
const btnSaveBypassNatWebhook      = document.getElementById('btnSaveBypassNatWebhook');
const bypassNatWebhookStatusBadge  = document.getElementById('bypassNatWebhookStatusBadge');

const btnStartAutoBypassNat        = document.getElementById('btnStartAutoBypassNat');
const btnStopAutoBypassNat         = document.getElementById('btnStopAutoBypassNat');
const cbBypassNatVisibleChrome     = document.getElementById('cbBypassNatVisibleChrome');

const inputBypassNatSingleSHD      = document.getElementById('inputBypassNatSingleSHD');
const btnTestSingleBypassNat       = document.getElementById('btnTestSingleBypassNat');

const bypassNatProgressContainer   = document.getElementById('bypassNatProgressContainer');
const bypassNatProgressText        = document.getElementById('bypassNatProgressText');
const bypassNatProgressPercent     = document.getElementById('bypassNatProgressPercent');
const bypassNatProgressBar         = document.getElementById('bypassNatProgressBar');

const inputFilterBypassNatTable    = document.getElementById('inputFilterBypassNatTable');
const selectFilterBypassNatStatus  = document.getElementById('selectFilterBypassNatStatus');
const bypassNatTableCount          = document.getElementById('bypassNatTableCount');
const tbodyBypassNat               = document.getElementById('tbodyBypassNat');

const btnAutoBypassNatModeToggle   = document.getElementById('btnAutoBypassNatModeToggle');
const autoBypassNatModeDot         = document.getElementById('autoBypassNatModeDot');
const autoBypassNatModeText        = document.getElementById('autoBypassNatModeText');
const selectDateFilterBypassNat    = document.getElementById('selectDateFilterBypassNat');

let currentBypassNatRecords = [];
let isBypassNatRunning = false;
let autoBypassNatMode = localStorage.getItem('autoBypassNatMode') !== 'false';
let autoBypassNatCountdownTimer = null;
let autoBypassNatCountdown = 0;
let currentBypassNatPage = 1;


// ===================== AUTO MODE UI =====================
function updateAutoBypassNatModeUI() {
  if (!btnAutoBypassNatModeToggle) return;
  const sidebarBadge = document.getElementById('sidebarAutoBypassNatBadge');
  if (autoBypassNatMode) {
    btnAutoBypassNatModeToggle.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold border-2 border-indigo-500 bg-indigo-50 text-indigo-700 transition-all shadow-sm animate-pulse cursor-pointer';
    if (autoBypassNatModeText) autoBypassNatModeText.textContent = 'Auto 4s: BẬT';
    if (autoBypassNatModeDot) autoBypassNatModeDot.className = 'w-2 h-2 rounded-full bg-indigo-600 transition-all animate-bounce';
    if (sidebarBadge) sidebarBadge.classList.remove('hidden');
  } else {
    btnAutoBypassNatModeToggle.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold border-2 border-slate-200 bg-white text-slate-600 hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-700 transition-all shadow-sm cursor-pointer';
    if (autoBypassNatModeText) autoBypassNatModeText.textContent = 'Auto 4s: TẮT';
    if (autoBypassNatModeDot) autoBypassNatModeDot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all';
    if (sidebarBadge) sidebarBadge.classList.add('hidden');
  }
}
updateAutoBypassNatModeUI();

if (btnAutoBypassNatModeToggle) {
  btnAutoBypassNatModeToggle.addEventListener('click', () => {
    autoBypassNatMode = !autoBypassNatMode;
    localStorage.setItem('autoBypassNatMode', autoBypassNatMode ? 'true' : 'false');
    updateAutoBypassNatModeUI();
    // Đồng bộ lên server orchestrator
    fetch('/api/auto-modes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bypass_nat: autoBypassNatMode })
    }).catch(() => {});

    if (autoBypassNatMode) {
      showSnackbar('🤖 Chế độ Tự Động Bypass NAT đã BẬT (Auto nền máy chủ)!');
    } else {
      showSnackbar('Chế độ Tự Động Bypass NAT đã TẮT.');
    }
  });
}

function checkAndAutoTriggerBypassNat() {
  // Auto nền máy chủ (_auto_orchestrator_loop) tự động quét và chạy ngầm, không cần trình duyệt kích hoạt trùng lặp
}

// ===================== WEBHOOK =====================
(function initBypassNatWebhook() {
  fetch('/api/config')
    .then(r => r.json())
    .then(cfg => {
      const url = cfg.bypass_nat_webhook_url || cfg.spampool_webhook_url || cfg.google_sheet_webhook_url || '';
      if (inputBypassNatWebhookUrl && url) {
        inputBypassNatWebhookUrl.value = url;
      }
    })
    .catch(() => {});
})();

if (btnSaveBypassNatWebhook && inputBypassNatWebhookUrl) {
  btnSaveBypassNatWebhook.addEventListener('click', async () => {
    const url = inputBypassNatWebhookUrl.value.trim();
    try {
      const res = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bypass_nat_webhook_url: url })
      });
      if (res.ok) {
        showSnackbar('✅ Đã lưu cấu hình Webhook Bypass NAT!');
      } else {
        showSnackbar('❌ Lỗi khi lưu Webhook');
      }
    } catch (e) {
      showSnackbar('❌ Lỗi kết nối');
    }
  });
}

// ===================== LOAD SHEET DATA =====================
async function loadBypassNatSheetData() {
  try {
    const res = await fetch('/api/bypass_nat/sheet?_t=' + Date.now());
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      currentBypassNatRecords = data.records || [];
      updateBypassNatStats();
      renderBypassNatTable();
      if (typeof updateGlobalPendingBadges === 'function') {
        updateGlobalPendingBadges();
      }
      checkAndAutoTriggerBypassNat();
    } else {
      if (currentBypassNatRecords.length === 0 && tbodyBypassNat) {
        tbodyBypassNat.innerHTML = `
          <tr>
            <td colspan="9" class="p-8 text-center text-rose-500 font-medium">
              ❌ Không thể tải dữ liệu Google Sheet (${data.message || 'Lỗi không xác định'})
            </td>
          </tr>
        `;
      }
    }
  } catch (e) {
    if (currentBypassNatRecords.length === 0 && tbodyBypassNat) {
      tbodyBypassNat.innerHTML = `
        <tr>
          <td colspan="9" class="p-8 text-center text-rose-500 font-medium">
            ❌ Không thể kết nối đến máy chủ nội bộ.
          </td>
        </tr>
      `;
    }
  }
}

function isProcessedBypassNatRow(kq, tt) {
  const k = String(kq || '').toLowerCase();
  const t = String(tt || '').toLowerCase();
  if (t.includes('thành công kết thúc') || t.includes('bypass nat trước đó') || t.includes('đã được bypass nat')) return true;
  if (t.includes('chưa cập nhật') || !t.trim() || t.includes('chưa xử lý')) return false;
  if (k.includes('đã xử lý') && !t.includes('chưa') && !t.includes('lỗi') && !t.includes('không')) return true;
  return false;
}

function isPendingBypassNatRow(kq, tt) {
  if (isProcessedBypassNatRow(kq, tt)) return false;
  const k = String(kq || '').toLowerCase();
  const t = String(tt || '').toLowerCase();
  if (t.includes('chưa cập nhật') || k.includes('chưa cập nhật')) return true;
  if (t.includes('chưa xử lý') || k.includes('chưa xử lý')) return true;
  if (!t.trim() || !k.trim()) return true;
  return false;
}

function updateBypassNatStats() {
  const total = currentBypassNatRecords.length;
  let pending = 0;
  let done = 0;
  let error = 0;

  currentBypassNatRecords.forEach(r => {
    const kq = r['Kết Quả'] || '';
    const tt = r['Thao Tác'] || '';
    if (isProcessedBypassNatRow(kq, tt)) {
      done++;
    } else if (isPendingBypassNatRow(kq, tt)) {
      pending++;
    } else {
      error++;
    }
  });

  if (bypassNatStatTotal) bypassNatStatTotal.textContent = total;
  if (bypassNatStatPending) bypassNatStatPending.textContent = pending;
  if (bypassNatStatDone) bypassNatStatDone.textContent = done;
  if (bypassNatStatError) bypassNatStatError.textContent = error;
  if (badgeBypassNatPending) badgeBypassNatPending.textContent = `${pending} chờ xử lý`;
}

function renderBypassNatTable() {
  if (!tbodyBypassNat) return;

  // Đồng bộ xóa cột ID khỏi thead và ẩn nhãn GID nếu DOM cũ còn lưu trên trình duyệt
  const tblNat = document.getElementById('tableBypassNat');
  if (tblNat) {
    tblNat.querySelectorAll('thead th').forEach(th => {
      if (th.textContent.trim().toUpperCase() === 'ID') th.remove();
    });
  }
  const tabNatEl = document.getElementById('tab-bypass-nat');
  if (tabNatEl) {
    tabNatEl.querySelectorAll('span, div').forEach(el => {
      if (el.children.length === 0 && /GID:\s*\d+/i.test(el.textContent)) {
        if (el.textContent.trim().startsWith('GID:')) el.remove();
        else el.textContent = el.textContent.replace(/\(?\s*GID:\s*\d+\s*\)?/gi, '').trim();
      }
    });
  }

  const dateFilter = selectDateFilterBypassNat ? selectDateFilterBypassNat.value : 'today';
  const search = inputFilterBypassNatTable ? inputFilterBypassNatTable.value.trim().toLowerCase() : '';
  const filter = selectFilterBypassNatStatus ? selectFilterBypassNatStatus.value : 'ALL';

  // Apply unified date filtering first
  let dateFiltered = currentBypassNatRecords;
  if (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.filterRecords === 'function') {
    dateFiltered = window.UnifiedWorkTabs.filterRecords(currentBypassNatRecords, dateFilter);
  }

  // Render Charts & Top Staff
  if (window.UnifiedWorkTabs) {
    if (typeof window.UnifiedWorkTabs.updateDailyChart === 'function') {
      window.UnifiedWorkTabs.updateDailyChart('bypassNatDailyChart', currentBypassNatRecords, dateFilter);
    }
    if (typeof window.UnifiedWorkTabs.updateTopStaff === 'function') {
      window.UnifiedWorkTabs.updateTopStaff('bypassNatTopStaffContainer', currentBypassNatRecords, dateFilter);
    }
  }

  const filtered = dateFiltered.filter(r => {
    const kq = String(r['Kết Quả'] || '');
    const tt = String(r['Thao Tác'] || '');

    // Status filter
    if (filter === 'PENDING' && !isPendingBypassNatRow(kq, tt)) return false;
    if (filter === 'DONE' && !isProcessedBypassNatRow(kq, tt)) return false;
    if (filter === 'ERROR' && (isPendingBypassNatRow(kq, tt) || isProcessedBypassNatRow(kq, tt))) return false;

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

  if (bypassNatTableCount) {
    bypassNatTableCount.textContent = `Hiển thị ${sortedFiltered.length} / ${currentBypassNatRecords.length} bản ghi`;
  }

  if (sortedFiltered.length === 0) {
    tbodyBypassNat.innerHTML = `
      <tr>
        <td colspan="9" class="p-8 text-center text-slate-400">
          Không có bản ghi nào phù hợp với bộ lọc.
        </td>
      </tr>
    `;
    if (window.UnifiedWorkTabs) {
      window.UnifiedWorkTabs.renderPagination('bypassNatPagination', { total: 0 });
    }
    return;
  }

  // Phân trang 10 dòng 1 trang
  const pageState = window.UnifiedWorkTabs
    ? window.UnifiedWorkTabs.paginate(sortedFiltered, currentBypassNatPage, 10)
    : { items: sortedFiltered.slice(0, 10), currentPage: 1, totalPages: Math.ceil(sortedFiltered.length / 10), total: sortedFiltered.length, startIdx: 0, endIdx: Math.min(10, sortedFiltered.length) };
  currentBypassNatPage = pageState.currentPage;

  tbodyBypassNat.innerHTML = pageState.items.map((r, idx) => {
    const globalIdx = pageState.startIdx + idx;
    const shd = r['SHD'] || '';
    const tacVu = r['Tác Vụ'] || '';
    const email = r['Email'] || '';
    const nguyenNhan = r['Nguyên Nhân 1'] || '';
    const ngay = r['Ngày Cập Nhật'] || '';
    const kq = r['Kết Quả'] || '';
    const tt = r['Thao Tác'] || '';

    // Badges
    let kqBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">Chưa cập nhật</span>';
    if (isProcessedBypassNatRow(kq, tt)) {
      kqBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">✓ Đã xử lý</span>';
    } else if (kq.toLowerCase().includes('lỗi') || tt.toLowerCase().includes('lỗi')) {
      kqBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-100 text-rose-800 border border-rose-300">✕ Lỗi</span>';
    } else if (isPendingBypassNatRow(kq, tt)) {
      kqBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-300">⏳ Chưa cập nhật</span>';
    }

    let ttClass = 'text-slate-600';
    if (tt.includes('thành công')) ttClass = 'text-emerald-700 font-semibold';
    else if (tt.includes('Trước Đó') || tt.includes('Trước đó')) ttClass = 'text-indigo-700 font-semibold';
    else if (tt.toLowerCase().includes('lỗi')) ttClass = 'text-rose-600 font-medium';

    return `
      <tr class="hover:bg-indigo-50/40 transition-colors">
        <td class="p-3 text-center text-slate-400 font-mono text-[11px]">${globalIdx + 1}</td>
        <td class="p-3 text-slate-800 font-medium">${tacVu}</td>
        <td class="p-3 text-slate-600">${email}</td>
        <td class="p-3 font-mono font-bold text-indigo-700 text-xs">${shd}</td>
        <td class="p-3 text-slate-600 text-[11px]">${nguyenNhan}</td>
        <td class="p-3 text-slate-500 font-mono text-[11px]">${ngay}</td>
        <td class="p-3">${kqBadge}</td>
        <td class="p-3 text-xs ${ttClass}">${tt || '<span class="text-slate-300">Chưa có</span>'}</td>
        <td class="p-3 text-center">
          <button type="button" onclick="runSingleBypassNatRow('${shd}')"
            class="px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-[11px] font-semibold transition-all shadow-2xs hover:shadow-xs cursor-pointer"
            title="Thực thi Bypass NAT cho riêng HĐ ${shd}">
            ⚡ Chạy
          </button>
        </td>
      </tr>
    `;
  }).join('');

  // Render pagination controls
  if (window.UnifiedWorkTabs) {
    window.UnifiedWorkTabs.renderPagination('bypassNatPagination', pageState, (newPage) => {
      currentBypassNatPage = newPage;
      renderBypassNatTable();
    });
  }
}

// ===================== TIẾN TRÌNH AUTO =====================
async function startAutoBypassNat() {
  if (isBypassNatRunning) return;

  const visible = cbBypassNatVisibleChrome ? cbBypassNatVisibleChrome.checked : false;
  try {
    btnStartAutoBypassNat.classList.add('hidden');
    if (btnStopAutoBypassNat) btnStopAutoBypassNat.classList.remove('hidden');
    if (bypassNatProgressContainer) bypassNatProgressContainer.classList.remove('hidden');

    const res = await fetch('/api/bypass_nat/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ headless: !visible })
    });
    const data = await res.json();
    if (res.ok && data.status === 'started') {
      isBypassNatRunning = true;
      showSnackbar('🚀 Đã bắt đầu tiến trình Auto Bypass NAT!');
      startBypassNatPolling();
    } else {
      btnStartAutoBypassNat.classList.remove('hidden');
      if (btnStopAutoBypassNat) btnStopAutoBypassNat.classList.add('hidden');
      showSnackbar('❌ ' + (data.message || 'Không thể khởi động Auto Bypass NAT'));
    }
  } catch (e) {
    btnStartAutoBypassNat.classList.remove('hidden');
    if (btnStopAutoBypassNat) btnStopAutoBypassNat.classList.add('hidden');
    showSnackbar('❌ Lỗi kết nối máy chủ');
  }
}

async function stopAutoBypassNat() {
  try {
    const res = await fetch('/api/bypass_nat/stop', { method: 'POST' });
    const data = await res.json();
    showSnackbar('⏹ ' + (data.message || 'Đã gửi lệnh dừng tiến trình Bypass NAT'));
  } catch (e) {
    showSnackbar('❌ Không thể dừng tiến trình');
  }
}

function startBypassNatPolling() {
  pollBypassNatStatus();
}

async function pollBypassNatStatus() {
  try {
    const res = await fetch('/api/bypass_nat/status?_t=' + Date.now());
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      const t = data.task || {};
      const total = t.total || 0;
      const current = t.current_index || 0;
      const msg = t.message || 'Đang thực hiện...';
      const isRunning = t.is_running || false;

      if (isRunning) {
        const percent = total > 0 ? Math.round((current / total) * 100) : 0;
        if (bypassNatProgressContainer) bypassNatProgressContainer.classList.remove('hidden');
        if (bypassNatProgressBar) bypassNatProgressBar.style.width = percent + '%';
        if (bypassNatProgressPercent) bypassNatProgressPercent.textContent = percent + '%';
        if (bypassNatProgressText) bypassNatProgressText.textContent = msg;
        if (!isBypassNatRunning) {
          isBypassNatRunning = true;
          btnStartAutoBypassNat.classList.add('hidden');
          if (btnStopAutoBypassNat) btnStopAutoBypassNat.classList.remove('hidden');
        }
      } else if (isBypassNatRunning) {
        isBypassNatRunning = false;
        const percent = total > 0 ? Math.round((current / total) * 100) : 100;
        if (bypassNatProgressBar) bypassNatProgressBar.style.width = percent + '%';
        if (bypassNatProgressPercent) bypassNatProgressPercent.textContent = percent + '%';
        if (bypassNatProgressText) bypassNatProgressText.textContent = msg;
        btnStartAutoBypassNat.classList.remove('hidden');
        if (btnStopAutoBypassNat) btnStopAutoBypassNat.classList.add('hidden');
        showSnackbar('🏁 Hoàn tất phiên Bypass NAT!');
        loadBypassNatSheetData();
      }
    }
  } catch (e) {
    console.warn('Polling bypass_nat error:', e);
  }
}

// ===================== RUN SINGLE ROW =====================
async function runSingleBypassNatRow(shd) {
  if (!shd) return;
  const rec = currentBypassNatRecords.find(r => String(r['SHD'] || '').trim().toUpperCase() === String(shd).trim().toUpperCase());
  const nguyenNhan = rec ? (rec['Nguyên Nhân 1'] || '') : '';
  runSingleBypassNatAction(shd, nguyenNhan);
}

async function runSingleBypassNatAction(shd, nguyenNhan = '') {
  const visible = cbBypassNatVisibleChrome ? cbBypassNatVisibleChrome.checked : false;
  showSnackbar(`⚡ Đang thực thi Bypass NAT cho HĐ ${shd}...`);
  if (bypassNatProgressContainer) bypassNatProgressContainer.classList.remove('hidden');
  if (bypassNatProgressText) bypassNatProgressText.textContent = `Đang xử lý hợp đồng ${shd}...`;
  if (bypassNatProgressBar) bypassNatProgressBar.style.width = '50%';

  try {
    const res = await fetch('/api/bypass_nat/test_single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shd: shd, nguyen_nhan_1: nguyenNhan, headless: !visible })
    });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showSnackbar(`✅ HĐ ${shd}: Thao tác='${data.thao_tac}' | Kết quả='${data.ket_qua}'`);
      if (bypassNatProgressText) bypassNatProgressText.textContent = `✅ HĐ ${shd}: ${data.thao_tac}`;
      if (bypassNatProgressBar) bypassNatProgressBar.style.width = '100%';
      loadBypassNatSheetData();
    } else {
      showSnackbar(`❌ Thất bại: ${data.message || 'Lỗi không xác định'}`);
      if (bypassNatProgressText) bypassNatProgressText.textContent = `❌ ${data.message || 'Lỗi xử lý'}`;
    }
  } catch (e) {
    showSnackbar('❌ Lỗi kết nối máy chủ: ' + e.message);
  }
}

// ===================== CACHE & EXCEL =====================
async function clearBypassNatCache() {
  try {
    const res = await fetch('/api/bypass_nat/clear_cache', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showSnackbar('🧹 Đã xóa toàn bộ bộ nhớ đệm cache Bypass NAT!');
      loadBypassNatSheetData();
    } else {
      showSnackbar('❌ ' + (data.message || 'Không thể xóa cache'));
    }
  } catch (e) {
    showSnackbar('❌ Lỗi kết nối');
  }
}

function exportBypassNatExcel() {
  if (!currentBypassNatRecords || currentBypassNatRecords.length === 0) {
    showSnackbar('⚠ Không có dữ liệu để xuất Excel');
    return;
  }
  const headers = ['STT', 'ID', 'Tác Vụ', 'Email', 'MSNV', 'Account Inside', 'SHD', 'Nguyên Nhân 1', 'Ngày Cập Nhật', 'Kết Quả', 'Thao Tác'];
  const rows = currentBypassNatRecords.map((r, i) => [
    i + 1,
    `"${(r['ID'] || '').replace(/"/g, '""')}"`,
    `"${(r['Tác Vụ'] || '').replace(/"/g, '""')}"`,
    `"${(r['Email'] || '').replace(/"/g, '""')}"`,
    `"${(r['MSNV'] || '').replace(/"/g, '""')}"`,
    `"${(r['Account Inside'] || '').replace(/"/g, '""')}"`,
    `"${(r['SHD'] || '').replace(/"/g, '""')}"`,
    `"${(r['Nguyên Nhân 1'] || '').replace(/"/g, '""')}"`,
    `"${(r['Ngày Cập Nhật'] || '').replace(/"/g, '""')}"`,
    `"${(r['Kết Quả'] || '').replace(/"/g, '""')}"`,
    `"${(r['Thao Tác'] || '').replace(/"/g, '""')}"`
  ]);

  const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(e => e.join(','))].join('\r\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Bypass_NAT_Results_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showSnackbar('📥 Đã tải file Excel kết quả Bypass NAT!');
}

// ===================== EVENT LISTENERS =====================
if (btnRefreshBypassNatSheetData) {
  btnRefreshBypassNatSheetData.addEventListener('click', () => {
    loadBypassNatSheetData();
    showSnackbar('🔄 Đang làm mới dữ liệu từ Google Sheet GID 1907537423...');
  });
}

if (btnClearBypassNatCache) {
  btnClearBypassNatCache.addEventListener('click', clearBypassNatCache);
}

if (btnExportBypassNatData) {
  btnExportBypassNatData.addEventListener('click', exportBypassNatExcel);
}

if (btnBypassNatLogin) {
  btnBypassNatLogin.addEventListener('click', async () => {
    const visible = cbBypassNatVisibleChrome ? cbBypassNatVisibleChrome.checked : false;
    showSnackbar('🔐 Đang xác thực đăng nhập Radius Portal...');
    if (bypassNatProgressContainer) bypassNatProgressContainer.classList.remove('hidden');
    if (bypassNatProgressText) bypassNatProgressText.textContent = 'Đang tiến hành đăng nhập Radius Portal qua IAM & Microsoft Azure AD SSO...';
    if (bypassNatProgressBar) bypassNatProgressBar.style.width = '40%';
    try {
      const res = await fetch('/api/bypass_nat/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ headless: !visible, force: true })
      });
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        showSnackbar('✅ ' + (data.message || 'Đăng nhập Radius Portal thành công!'));
        if (bypassNatProgressText) bypassNatProgressText.textContent = '✅ Đã xác thực thành công vào Radius Portal (' + (data.url || '') + ')';
        if (bypassNatProgressBar) bypassNatProgressBar.style.width = '100%';
      } else {
        showSnackbar('❌ ' + (data.message || 'Đăng nhập thất bại'));
        if (bypassNatProgressText) bypassNatProgressText.textContent = '❌ Đăng nhập thất bại: ' + (data.message || '');
      }
    } catch (e) {
      showSnackbar('❌ Lỗi kết nối đến server: ' + e.message);
    }
  });
}

if (btnStartAutoBypassNat) {
  btnStartAutoBypassNat.addEventListener('click', startAutoBypassNat);
}

if (btnStopAutoBypassNat) {
  btnStopAutoBypassNat.addEventListener('click', stopAutoBypassNat);
}

if (btnTestSingleBypassNat) {
  btnTestSingleBypassNat.addEventListener('click', () => {
    let shd = inputBypassNatSingleSHD ? inputBypassNatSingleSHD.value.trim().toUpperCase() : '';
    if (!shd) {
      // Tự động lấy HĐ đầu tiên đang chờ xử lý từ danh sách sheet
      const firstPending = currentBypassNatRecords.find(r => isPendingBypassNatRow(r['Kết Quả'], r['Thao Tác'])) || currentBypassNatRecords[0];
      if (firstPending && firstPending['SHD']) {
        shd = String(firstPending['SHD']).trim().toUpperCase();
        if (inputBypassNatSingleSHD) inputBypassNatSingleSHD.value = shd;
        showSnackbar(`⚡ Tự động chọn HĐ [${shd}] từ Google Sheet để chạy thử`);
      }
    }
    if (!shd) {
      showSnackbar('⚠ Vui lòng nhập Số Hợp Đồng để chạy thử');
      return;
    }
    const rec = currentBypassNatRecords.find(r => String(r['SHD'] || '').trim().toUpperCase() === shd);
    const nguyenNhan = rec ? (rec['Nguyên Nhân 1'] || '') : '';
    runSingleBypassNatAction(shd, nguyenNhan);
  });
}

if (inputFilterBypassNatTable) {
  inputFilterBypassNatTable.addEventListener('input', () => { currentBypassNatPage = 1; renderBypassNatTable(); });
}

if (selectFilterBypassNatStatus) {
  selectFilterBypassNatStatus.addEventListener('change', () => { currentBypassNatPage = 1; renderBypassNatTable(); });
}

if (selectDateFilterBypassNat) {
  selectDateFilterBypassNat.addEventListener('change', () => { currentBypassNatPage = 1; renderBypassNatTable(); });
}

// Đăng ký tab với hệ thống chuyển tab
if (typeof registerTab === 'function') {
  registerTab('tab-bypass-nat', {
    title: 'Auto Bypass NAT',
    onActivate: () => {
      loadBypassNatSheetData();
    }
  });
}

// Xuất các hàm ra phạm vi toàn cục cho main.js polling
window.pollBypassNatStatus = pollBypassNatStatus;
window.loadBypassNatSheetData = loadBypassNatSheetData;
window.updateAutoBypassNatModeUI = updateAutoBypassNatModeUI;
window.checkAndAutoTriggerBypassNat = checkAndAutoTriggerBypassNat;
window.runSingleBypassNatRow = runSingleBypassNatRow;
