// ==========================================================
// COMPONENT: AUTO CẤP/THU HỒI PORT (tab-port)
// Google Sheet ID: 1Sw-qSbLzvVdcW4rj7ywEZBEzKI6w5M82EQeYJUpdx7M
// GID: 966043489
// Cột: ID | Tác Vụ | Email | MSNV | Account Inside | SHD | Tập Điểm | Port | Nguyên Nhân 1 | Ngày Cập Nhật | Kết Quả | Thao Tác
// ==========================================================

const badgePortPending        = document.getElementById('badgePortPending');
const portStatTotal           = document.getElementById('portStatTotal');
const portStatPending         = document.getElementById('portStatPending');
const portStatDone            = document.getElementById('portStatDone');
const portStatError           = document.getElementById('portStatError');

const btnRefreshPortSheetData = document.getElementById('btnRefreshPortSheetData');
const btnClearPortCache       = document.getElementById('btnClearPortCache');
const btnExportPortData       = document.getElementById('btnExportPortData');

const btnStartAutoPort        = document.getElementById('btnStartAutoPort');
const btnStopAutoPort         = document.getElementById('btnStopAutoPort');
const cbPortVisibleChrome     = document.getElementById('cbPortVisibleChrome');

const inputPortSingleSHD      = document.getElementById('inputPortSingleSHD');
const btnTestSinglePort       = document.getElementById('btnTestSinglePort');

const portProgressContainer   = document.getElementById('portProgressContainer');
const portProgressText        = document.getElementById('portProgressText');
const portProgressPercent     = document.getElementById('portProgressPercent');
const portProgressBar         = document.getElementById('portProgressBar');

const inputFilterPortTable    = document.getElementById('inputFilterPortTable');
const selectFilterPortStatus  = document.getElementById('selectFilterPortStatus');
const portTableCount          = document.getElementById('portTableCount');
const tbodyPort               = document.getElementById('tbodyPort');

const btnAutoPortModeToggle   = document.getElementById('btnAutoPortModeToggle');
const autoPortModeDot         = document.getElementById('autoPortModeDot');
const autoPortModeText        = document.getElementById('autoPortModeText');
const selectDateFilterPort    = document.getElementById('selectDateFilterPort');

let currentPortRecords = [];
let isPortRunning = false;
let autoPortMode = localStorage.getItem('autoPortMode') !== 'false';
let portPollTimer = null;
let autoPortCountdownTimer = null;
let currentPortPage = 1;


// ===================== AUTO MODE UI =====================
function updateAutoPortModeUI() {
  if (!btnAutoPortModeToggle) return;
  const sidebarBadge = document.getElementById('sidebarAutoPortBadge');
  if (autoPortMode) {
    btnAutoPortModeToggle.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold border-2 border-cyan-500 bg-cyan-50 text-cyan-700 transition-all shadow-sm animate-pulse cursor-pointer';
    if (autoPortModeText) autoPortModeText.textContent = 'Auto 4s: BẬT';
    if (autoPortModeDot) autoPortModeDot.className = 'w-2 h-2 rounded-full bg-cyan-600 transition-all animate-bounce';
    if (sidebarBadge) sidebarBadge.classList.remove('hidden');
  } else {
    btnAutoPortModeToggle.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold border-2 border-slate-200 bg-white text-slate-600 hover:border-cyan-400 hover:bg-cyan-50 hover:text-cyan-700 transition-all shadow-sm cursor-pointer';
    if (autoPortModeText) autoPortModeText.textContent = 'Auto 4s: TẮT';
    if (autoPortModeDot) autoPortModeDot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all';
    if (sidebarBadge) sidebarBadge.classList.add('hidden');
  }
}
updateAutoPortModeUI();

if (btnAutoPortModeToggle) {
  btnAutoPortModeToggle.addEventListener('click', () => {
    autoPortMode = !autoPortMode;
    localStorage.setItem('autoPortMode', autoPortMode ? 'true' : 'false');
    updateAutoPortModeUI();
    // Đồng bộ lên server orchestrator
    fetch('/api/auto-modes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port: autoPortMode })
    }).catch(() => {});

    if (autoPortMode) {
      showSnackbar('🤖 Chế độ Tự Động Cấp/Thu Hồi Port đã BẬT!');
    } else {
      showSnackbar('Chế độ Tự Động Cấp/Thu Hồi Port đã TẮT.');
    }
  });
}


// ===================== TẢI DỮ LIỆU SHEET =====================
async function loadPortSheetData() {
  if (tbodyPort && currentPortRecords.length === 0) {
    if (tbodyPort.children.length === 0 ||
        (tbodyPort.children.length === 1 && tbodyPort.children[0].textContent.includes('tải'))) {
      tbodyPort.innerHTML = `
        <tr>
          <td colspan="11" class="p-8 text-center text-slate-400">
            <div class="flex items-center justify-center gap-2">
              <svg class="animate-spin h-5 w-5 text-cyan-600" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
              <span>Đang tải dữ liệu từ Google Sheet...</span>
            </div>
          </td>
        </tr>
      `;
    }
  }

  try {
    const res = await fetch('/api/port/sheet?_t=' + Date.now());
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      currentPortRecords = data.records || [];
      if (!isPortRunning) renderPortTable();
      updatePortStats();
    } else {
      if (currentPortRecords.length === 0 && tbodyPort) {
        tbodyPort.innerHTML = `
          <tr>
            <td colspan="11" class="p-8 text-center text-rose-500 font-medium">
              ❌ Lỗi tải dữ liệu: ${escapeHtml(data.message || 'Không xác định')}
            </td>
          </tr>
        `;
      }
    }
  } catch (e) {
    if (currentPortRecords.length === 0 && tbodyPort) {
      tbodyPort.innerHTML = `
        <tr>
          <td colspan="11" class="p-8 text-center text-rose-500 font-medium">
            ❌ Không thể kết nối đến máy chủ nội bộ.
          </td>
        </tr>
      `;
    }
  }
}

// Quy định: Ngày Cập Nhật hoặc Thao Tác là 'Chưa cập nhật' (hoặc Chưa xử lý) -> Chưa xử lý
function isProcessedPortRow(ngay, tt) {
  const t = String(tt || '').toLowerCase().trim();
  const n = String(ngay || '').toLowerCase().trim();

  if (t.includes('chưa cập nhật') || t.includes('chưa xử lý') || t.includes('chưa xử lí') || !t) return false;
  if (t.includes('thành công') || t.includes('đã xử lý') || t.includes('đã xử lí') || t.includes('đã cấp') || t.includes('đã thu hồi') || t.includes('hoàn tất') || t.includes('đã cập nhật')) return true;
  if (t.includes('lỗi') || t.includes('thất bại') || t.includes('không')) return true;
  if (n.includes('chưa cập nhật') || n.includes('chưa xử lý') || n.includes('chưa xử lí') || !n) return false;
  return true;
}

function isPendingPortRow(ngay, tt) {
  return !isProcessedPortRow(ngay, tt);
}

function updatePortStats() {
  const total = currentPortRecords.length;
  let pending = 0;
  let done = 0;
  let error = 0;

  currentPortRecords.forEach(r => {
    const ngay = r['Ngày Cập Nhật'] || '';
    const tt = r['Thao Tác'] || '';
    const tLow = String(tt).toLowerCase();

    if (isPendingPortRow(ngay, tt)) {
      pending++;
    } else if (tLow.includes('lỗi') || tLow.includes('thất bại') || tLow.includes('không')) {
      error++;
    } else {
      done++;
    }
  });

  if (portStatTotal) portStatTotal.textContent = total;
  if (portStatPending) portStatPending.textContent = pending;
  if (portStatDone) portStatDone.textContent = done;
  if (portStatError) portStatError.textContent = error;
  if (badgePortPending) badgePortPending.textContent = `${pending} chờ xử lý`;

  const navBadge = document.getElementById('navPendingBadgePort');
  if (navBadge) {
    if (pending > 0) {
      navBadge.textContent = pending;
      navBadge.classList.remove('hidden');
    } else {
      navBadge.classList.add('hidden');
    }
  }
}

function renderPortTable() {
  if (!tbodyPort) return;

  // Đồng bộ xóa cột ID khỏi thead và ẩn nhãn GID nếu DOM cũ còn lưu trên trình duyệt
  const tblPort = document.getElementById('tablePort');
  if (tblPort) {
    tblPort.querySelectorAll('thead th').forEach(th => {
      if (th.textContent.trim().toUpperCase() === 'ID') th.remove();
    });
  }
  const tabPortEl = document.getElementById('tab-port');
  if (tabPortEl) {
    tabPortEl.querySelectorAll('span, div').forEach(el => {
      if (el.children.length === 0 && /GID:\s*\d+/i.test(el.textContent)) {
        if (el.textContent.trim().startsWith('GID:')) el.remove();
        else el.textContent = el.textContent.replace(/\(?\s*GID:\s*\d+\s*\)?/gi, '').trim();
      }
    });
  }

  const dateFilter = selectDateFilterPort ? selectDateFilterPort.value : 'today';
  const search = inputFilterPortTable ? inputFilterPortTable.value.trim().toLowerCase() : '';
  const filter = selectFilterPortStatus ? selectFilterPortStatus.value : 'ALL';

  // Apply unified date filtering
  let dateFiltered = currentPortRecords;
  if (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.filterRecords === 'function') {
    dateFiltered = window.UnifiedWorkTabs.filterRecords(currentPortRecords, dateFilter);
  }

  // Render Charts & Top Staff
  if (window.UnifiedWorkTabs) {
    if (typeof window.UnifiedWorkTabs.updateDailyChart === 'function') {
      window.UnifiedWorkTabs.updateDailyChart('portDailyChart', currentPortRecords, dateFilter);
    }
    if (typeof window.UnifiedWorkTabs.updateTopStaff === 'function') {
      window.UnifiedWorkTabs.updateTopStaff('portTopStaffContainer', currentPortRecords, dateFilter);
    }
  }

  const filtered = dateFiltered.filter(r => {
    const ngay = String(r['Ngày Cập Nhật'] || '');
    const tt = String(r['Thao Tác'] || '');
    const tLow = tt.toLowerCase();
    const isPend = isPendingPortRow(ngay, tt);
    const isErr = !isPend && (tLow.includes('lỗi') || tLow.includes('thất bại') || tLow.includes('không'));
    const isDone = !isPend && !isErr;

    // Status filter
    if (filter === 'PENDING' && !isPend) return false;
    if (filter === 'DONE' && !isDone) return false;
    if (filter === 'ERROR' && !isErr) return false;

    // Search query
    if (search) {
      const matchText = [
        r['ID'], r['Tác Vụ'], r['Email'], r['MSNV'], r['Account Inside'],
        r['Số Hợp Đồng'], r['SHD'], r['Tập Điểm'], r['Port'], r['Nguyên Nhân 1'], r['Ngày Cập Nhật'], r['Kết Quả'], tt
      ].join(' ').toLowerCase();
      if (!matchText.includes(search)) return false;
    }
    return true;
  });

  // Đảm bảo luôn sắp xếp từ gần nhất đến xa nhất (mới nhất lên đầu)
  const sortedFiltered = (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.sortRecordsNewestFirst === 'function')
    ? window.UnifiedWorkTabs.sortRecordsNewestFirst(filtered)
    : filtered;

  if (portTableCount) {
    portTableCount.textContent = `Hiển thị ${sortedFiltered.length} / ${currentPortRecords.length} bản ghi`;
  }

  if (sortedFiltered.length === 0) {
    tbodyPort.innerHTML = `
      <tr>
        <td colspan="13" class="p-8 text-center text-slate-400">
          Không có bản ghi nào phù hợp với bộ lọc.
        </td>
      </tr>
    `;
    if (window.UnifiedWorkTabs) {
      window.UnifiedWorkTabs.renderPagination('portPagination', { total: 0 });
    }
    return;
  }

  // Phân trang 10 dòng 1 trang
  const pageState = window.UnifiedWorkTabs
    ? window.UnifiedWorkTabs.paginate(sortedFiltered, currentPortPage, 10)
    : { items: sortedFiltered.slice(0, 10), currentPage: 1, totalPages: Math.ceil(sortedFiltered.length / 10), total: sortedFiltered.length, startIdx: 0, endIdx: Math.min(10, sortedFiltered.length) };
  currentPortPage = pageState.currentPage;

  tbodyPort.innerHTML = pageState.items.map((r, idx) => {
    const globalIdx = pageState.startIdx + idx;
    const id = r['ID'] || '';
    const tacVu = r['Tác Vụ'] || '';
    const email = r['Email'] || '';
    const msnv = r['MSNV'] || '';
    const account = r['Account Inside'] || '';
    const shd = r['Số Hợp Đồng'] || r['SHD'] || '';
    const tapDiem = r['Tập Điểm'] || '';
    const port = r['Port'] || '';
    const nn1 = r['Nguyên Nhân 1'] || '';
    const ngay = r['Ngày Cập Nhật'] || '';
    const ketQua = r['Kết Quả'] || '';
    const tt = r['Thao Tác'] || '';

    // Badges trạng thái Thao Tác & Kết Quả
    let ttBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-300">⏳ Chưa cập nhật</span>';
    const isPend = isPendingPortRow(ngay, tt);
    const tLow = tt.toLowerCase();

    if (!isPend) {
      if (tLow.includes('lỗi') || tLow.includes('thất bại') || tLow.includes('không')) {
        ttBadge = `<span class="inline-block px-2.5 py-1 rounded-lg text-[10.5px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 max-w-[300px] whitespace-normal leading-snug" title="${escapeHtml(tt)}">⛔ ${escapeHtml(tt)}</span>`;
      } else {
        ttBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">✓ ${escapeHtml(tt || 'Đã xử lý')}</span>`;
      }
    } else if (tt && tt !== 'Chưa cập nhật') {
      ttBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">${escapeHtml(tt)}</span>`;
    }

    let kqBadge = '<span class="text-slate-400 text-[11px]">—</span>';
    const kqLow = String(ketQua).toLowerCase().trim();
    if (kqLow) {
      if (kqLow.includes('đã xử lý') || kqLow.includes('đã xử lí') || kqLow.includes('thành công') && !kqLow.includes('không')) {
        kqBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">✓ ${escapeHtml(ketQua)}</span>`;
      } else if (kqLow.includes('không') || kqLow.includes('lỗi') || kqLow.includes('thất bại')) {
        kqBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">✕ ${escapeHtml(ketQua)}</span>`;
      } else if (kqLow.includes('chưa')) {
        kqBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">⏳ ${escapeHtml(ketQua)}</span>`;
      } else {
        kqBadge = `<span class="text-slate-600 text-[11px]">${escapeHtml(ketQua)}</span>`;
      }
    }

    return `
      <tr class="hover:bg-cyan-50/40 transition-colors">
        <td class="p-3 text-center text-slate-400 font-mono text-[11px]">${globalIdx + 1}</td>
        <td class="p-3 text-slate-800 font-medium">
          <span class="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            ${escapeHtml(tacVu)}
          </span>
        </td>
        <td class="p-3 text-slate-600 text-[11px]">${escapeHtml(email)}</td>
        <td class="p-3 text-slate-500 font-mono text-[11px]">${escapeHtml(msnv)}</td>
        <td class="p-3 text-slate-700 text-xs">${escapeHtml(account)}</td>
        <td class="p-3 font-mono font-bold text-cyan-700 text-xs">${escapeHtml(shd || '—')}</td>
        <td class="p-3 font-mono text-slate-700 text-xs font-semibold">${escapeHtml(tapDiem || '—')}</td>
        <td class="p-3 font-mono text-center">
          ${port ? `<span class="px-2 py-0.5 rounded-md font-bold text-xs bg-cyan-100 text-cyan-800 border border-cyan-200">${escapeHtml(port)}</span>` : '<span class="text-slate-400">—</span>'}
        </td>
        <td class="p-3 text-slate-600 text-[11.5px]">${escapeHtml(nn1 || '—')}</td>
        <td class="p-3 text-slate-500 font-mono text-[11px]">${escapeHtml(ngay)}</td>
        <td class="p-3 text-xs">${kqBadge}</td>
        <td class="p-3 text-xs">${ttBadge}</td>
        <td class="p-3 text-center">
          <button type="button" onclick="runSinglePortRow('${escapeHtml(shd)}', '${escapeHtml(id)}', '${escapeHtml(tacVu).replace(/'/g, "\\'")}', '${escapeHtml(tapDiem).replace(/'/g, "\\'")}', '${escapeHtml(port).replace(/'/g, "\\'")}')"
            class="px-2.5 py-1 rounded-lg bg-cyan-50 hover:bg-cyan-100 text-cyan-700 border border-cyan-200 text-[11px] font-semibold transition-all shadow-2xs hover:shadow-xs cursor-pointer"
            title="Thực thi Cấp/Thu Hồi Port">
            ⚡ Chạy
          </button>
        </td>
      </tr>
    `;
  }).join('');

  // Render pagination controls
  if (window.UnifiedWorkTabs) {
    window.UnifiedWorkTabs.renderPagination('portPagination', pageState, (newPage) => {
      currentPortPage = newPage;
      renderPortTable();
    });
  }
}

// ===================== TIẾN TRÌNH AUTO =====================
async function startAutoPort() {
  if (isPortRunning) return;

  const visible = cbPortVisibleChrome ? cbPortVisibleChrome.checked : false;
  try {
    if (btnStartAutoPort) btnStartAutoPort.classList.add('hidden');
    if (btnStopAutoPort) btnStopAutoPort.classList.remove('hidden');
    if (portProgressContainer) portProgressContainer.classList.remove('hidden');
    if (portProgressText) portProgressText.textContent = 'Đang khởi động tiến trình Cấp/Thu Hồi Port...';

    const res = await fetch('/api/port/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ headless: !visible })
    });
    const data = await res.json();
    if (res.ok && data.status === 'started') {
      isPortRunning = true;
      showSnackbar('🚀 Đã bắt đầu tiến trình Cấp/Thu Hồi Port!');
      startPortPolling();
    } else {
      if (btnStartAutoPort) btnStartAutoPort.classList.remove('hidden');
      if (btnStopAutoPort) btnStopAutoPort.classList.add('hidden');
      showSnackbar('ℹ️ ' + (data.message || 'Hệ thống đã nhận lệnh'));
    }
  } catch (e) {
    if (btnStartAutoPort) btnStartAutoPort.classList.remove('hidden');
    if (btnStopAutoPort) btnStopAutoPort.classList.add('hidden');
    showSnackbar('❌ Lỗi kết nối máy chủ');
  }
}

async function stopAutoPort() {
  try {
    const res = await fetch('/api/port/stop', { method: 'POST' });
    const data = await res.json();
    showSnackbar('⏹ ' + (data.message || 'Đã gửi lệnh dừng tiến trình'));
    isPortRunning = false;
    if (btnStartAutoPort) btnStartAutoPort.classList.remove('hidden');
    if (btnStopAutoPort) btnStopAutoPort.classList.add('hidden');
    if (portProgressContainer) portProgressContainer.classList.add('hidden');
  } catch (e) {
    showSnackbar('❌ Không thể dừng tiến trình');
  }
}

function startPortPolling() {
  if (portPollTimer) clearInterval(portPollTimer);
  portPollTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/port/status?_t=' + Date.now());
      const data = await res.json();
      if (res.ok && data.status === 'ok') {
        const t = data.task || {};
        const total = t.total || 0;
        const current = t.current_index || 0;
        const msg = t.message || 'Đang thực hiện...';
        const isRunning = t.is_running || false;

        const percent = total > 0 ? Math.round((current / total) * 100) : 0;
        if (portProgressBar) portProgressBar.style.width = percent + '%';
        if (portProgressPercent) portProgressPercent.textContent = percent + '%';
        if (portProgressText) portProgressText.textContent = msg;

        if (!isRunning) {
          clearInterval(portPollTimer);
          isPortRunning = false;
          if (btnStartAutoPort) btnStartAutoPort.classList.remove('hidden');
          if (btnStopAutoPort) btnStopAutoPort.classList.add('hidden');
          loadPortSheetData();
        }
      }
    } catch (e) {}
  }, 2500);
}

async function pollPortStatus() {
  try {
    const res = await fetch('/api/port/status?_t=' + Date.now());
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      const t = data.task || {};
      const isRunning = t.is_running || false;
      if (isRunning && !isPortRunning) {
        isPortRunning = true;
        if (btnStartAutoPort) btnStartAutoPort.classList.add('hidden');
        if (btnStopAutoPort) btnStopAutoPort.classList.remove('hidden');
        if (portProgressContainer) portProgressContainer.classList.remove('hidden');
        startPortPolling();
      } else if (!isRunning && isPortRunning) {
        isPortRunning = false;
        if (btnStartAutoPort) btnStartAutoPort.classList.remove('hidden');
        if (btnStopAutoPort) btnStopAutoPort.classList.add('hidden');
      }
    }
  } catch (e) {}
}

// ===================== TEST NHANH 1 HĐ =====================
window.runSinglePortRow = function(shd, rowId = '', tacVu = '', tapDiem = '', port = '') {
  if (!shd && !rowId && !tapDiem) return;
  runSinglePortAction(shd, tacVu, rowId, tapDiem, port);
};

async function runSinglePortAction(shd, tacVu = '', rowId = '', tapDiem = '', port = '') {
  if (!shd && !rowId && !tapDiem) return;
  const label = shd || tapDiem || ('ID ' + rowId);
  const visible = cbPortVisibleChrome ? cbPortVisibleChrome.checked : false;
  showSnackbar(`⚡ Đang chuẩn bị thao tác cho [${label}]...`);

  // Loading state trên nút Chạy Thử
  const oldBtnHtml = btnTestSinglePort ? btnTestSinglePort.innerHTML : '';
  if (btnTestSinglePort) {
    btnTestSinglePort.disabled = true;
    btnTestSinglePort.innerHTML = `<span class="inline-block animate-spin">⏳</span> <span>Đang chạy ${escapeHtml(label)}...</span>`;
    btnTestSinglePort.classList.add('opacity-75');
  }

  if (portProgressContainer) portProgressContainer.classList.remove('hidden');
  if (portProgressText) portProgressText.textContent = `Đang gửi yêu cầu cho ${escapeHtml(label)}...`;
  if (portProgressBar) portProgressBar.style.width = '60%';

  try {
    const res = await fetch('/api/port/test_single', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shd: shd, row_id: rowId, tac_vu: tacVu, tap_diem: tapDiem, port: port, headless: !visible })
    });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showSnackbar(`✅ ${label}: ${data.thao_tac || data.message || 'Thành công'}`);
      if (portProgressText) portProgressText.textContent = `✅ ${label}: ${data.thao_tac || data.message || 'Đã xử lý'}`;
      if (portProgressBar) portProgressBar.style.width = '100%';
      loadPortSheetData();
    } else {
      showSnackbar(`ℹ️ ${label}: ${data.message || 'Đã ghi nhận yêu cầu'}`);
      if (portProgressText) portProgressText.textContent = `ℹ️ ${label}: ${data.message || 'Đã ghi nhận yêu cầu'}`;
    }
  } catch (e) {
    showSnackbar('❌ Lỗi kết nối khi thử HĐ: ' + (e.message || e));
    if (portProgressText) portProgressText.textContent = `❌ Lỗi kết nối khi test ${label}`;
  } finally {
    if (btnTestSinglePort) {
      btnTestSinglePort.disabled = false;
      btnTestSinglePort.innerHTML = oldBtnHtml || '<span>Test</span>';
      btnTestSinglePort.classList.remove('opacity-75');
    }
    setTimeout(() => {
      if (!isPortRunning && portProgressContainer) {
        portProgressContainer.classList.add('hidden');
      }
    }, 4000);
  }
}

// ===================== XÓA CACHE =====================
async function clearPortCache() {
  if (!confirm('Bạn có chắc chắn muốn xóa cache trạng thái Cấp/Thu Hồi Port để tải lại từ đầu?')) return;
  try {
    const res = await fetch('/api/port/clear_cache', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      showSnackbar('🧹 Đã xóa sạch cache Cấp/Thu Hồi Port!');
      loadPortSheetData();
    } else {
      showSnackbar('❌ Lỗi xóa cache');
    }
  } catch (e) {
    showSnackbar('❌ Lỗi kết nối');
  }
}

// ===================== XUẤT EXCEL =====================
function exportPortExcel() {
  if (currentPortRecords.length === 0) {
    showSnackbar('⚠ Không có dữ liệu để xuất file');
    return;
  }
  const headers = ['ID', 'Tác Vụ', 'Email', 'MSNV', 'Account Inside', 'Số Hợp Đồng', 'Tập Điểm', 'Port', 'Nguyên Nhân 1', 'Ngày Cập Nhật', 'Kết Quả', 'Thao Tác'];
  const rows = [headers];
  currentPortRecords.forEach(r => {
    rows.push(headers.map(h => `"${String(r[h] || '').replace(/"/g, '""')}"`));
  });
  const csvContent = '\uFEFF' + rows.map(e => e.join(',')).join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Cap_Thu_Hoi_Port_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showSnackbar('📥 Đã tải file Excel kết quả Cấp/Thu Hồi Port!');
}

// ===================== EVENT LISTENERS =====================
if (btnRefreshPortSheetData) {
  btnRefreshPortSheetData.addEventListener('click', () => {
    loadPortSheetData();
    showSnackbar('🔄 Đang làm mới dữ liệu từ Google Sheet...');
  });
}

if (btnClearPortCache) {
  btnClearPortCache.addEventListener('click', clearPortCache);
}

if (btnExportPortData) {
  btnExportPortData.addEventListener('click', exportPortExcel);
}

if (btnStartAutoPort) {
  btnStartAutoPort.addEventListener('click', startAutoPort);
}

if (btnStopAutoPort) {
  btnStopAutoPort.addEventListener('click', stopAutoPort);
}

if (btnTestSinglePort) {
  btnTestSinglePort.addEventListener('click', () => {
    let shd = inputPortSingleSHD ? inputPortSingleSHD.value.trim().toUpperCase() : '';
    if (!shd) {
      const firstPending = currentPortRecords.find(r => isPendingPortRow(r['Ngày Cập Nhật'], r['Thao Tác'])) || currentPortRecords[0];
      if (firstPending && (firstPending['Số Hợp Đồng'] || firstPending['SHD'])) {
        shd = String(firstPending['Số Hợp Đồng'] || firstPending['SHD']).trim().toUpperCase();
        if (inputPortSingleSHD) inputPortSingleSHD.value = shd;
        showSnackbar(`⚡ Tự động chọn HĐ [${shd}] từ Google Sheet để chạy thử`);
      }
    }
    if (!shd) {
      showSnackbar('⚠ Vui lòng nhập Số Hợp Đồng để chạy thử');
      return;
    }
    const rec = currentPortRecords.find(r => String(r['Số Hợp Đồng'] || r['SHD'] || '').trim().toUpperCase() === shd);
    const tacVu = rec ? (rec['Tác Vụ'] || '') : '';
    const rowId = rec ? (rec['ID'] || '') : '';
    runSinglePortAction(shd, tacVu, rowId);
  });
}

if (inputFilterPortTable) {
  inputFilterPortTable.addEventListener('input', () => { currentPortPage = 1; renderPortTable(); });
}

if (selectFilterPortStatus) {
  selectFilterPortStatus.addEventListener('change', () => { currentPortPage = 1; renderPortTable(); });
}

if (selectDateFilterPort) {
  selectDateFilterPort.addEventListener('change', () => { currentPortPage = 1; renderPortTable(); });
}

// Đăng ký tab với hệ thống chuyển tab
if (typeof registerTab === 'function') {
  registerTab('tab-port', {
    title: 'Cấp/Thu Hồi Port',
    onActivate: () => {
      loadPortSheetData();
    }
  });
}

function checkAndAutoTriggerPort() {
  if (!autoPortMode || isPortRunning || autoPortCountdownTimer) return;
  const pendingRows = currentPortRecords.filter(r =>
    (String(r['Số Hợp Đồng'] || r['SHD'] || '').trim() || String(r['Tập Điểm'] || '').trim() || String(r['Port'] || '').trim())
    && isPendingPortRow(r['Ngày Cập Nhật'], r['Thao Tác'])
  );
  if (pendingRows.length === 0) return;

  autoPortCountdownTimer = setTimeout(() => {
    autoPortCountdownTimer = null;
    if (autoPortMode && !isPortRunning) {
      startAutoPort();
    }
  }, 1500);
}

// Xuất các hàm ra phạm vi toàn cục
window.loadPortSheetData = loadPortSheetData;
window.updateAutoPortModeUI = updateAutoPortModeUI;
window.renderPortTable = renderPortTable;
window.pollPortStatus = pollPortStatus;
window.checkAndAutoTriggerPort = checkAndAutoTriggerPort;
window.isPendingPortRow = isPendingPortRow;
window.isProcessedPortRow = isProcessedPortRow;
