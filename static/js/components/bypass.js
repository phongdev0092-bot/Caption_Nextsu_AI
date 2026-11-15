// ==========================================================
// COMPONENT: AUTO BYPASS (tab-tasks)
// ==========================================================

// ========================================================
// TAB 3: AUTO BYPASS - QUẢN LÝ BYPASS & GOOGLE SHEETS
// ========================================================

// ByPass Google Sheet GID 0
function switchBypassSubTab(gid = '0') {
  currentBypassGid = gid;
  if (sheetCurrentTabTitle) sheetCurrentTabTitle.textContent = 'ByPass';
  loadBypassSheetData(gid);
}

if (btnSubTabBypass) {
  btnSubTabBypass.addEventListener('click', () => switchBypassSubTab('0'));
}

// Load Google Sheet Data
async function loadBypassSheetData(gid = currentBypassGid) {
  if (!sheetDataTableBody) return;
  // Chỉ hiện loading khi bảng rỗng, tránh flicker khi auto-refresh 4s
  if (sheetDataTableBody.children.length === 0 || (sheetDataTableBody.children.length === 1 && sheetDataTableBody.children[0].textContent.includes('Đang tải'))) {
    sheetDataTableBody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding: 28px; color: #80868b;"><span>⏳ Đang tải dữ liệu từ Google Sheet...</span></td></tr>';
  }

  try {
    const res = await fetch(`/api/bypass/sheet-data?gid=${gid}&_t=${Date.now()}`);
    const data = await res.json();

    if (res.ok && data.status === 'ok') {
      currentBypassRecords = data.records || [];
      updateBypassStats(currentBypassRecords);
      // Khi đang bypass, chỉ update KPI stats; bảng đã cập nhật realtime qua pollBypassStatus
      if (!isBypassRunning) {
        renderBypassTable(currentBypassRecords);
      }
      // Tự động kiểm tra và kích hoạt nếu chế độ Auto ByPass đang BẬT
      if (autoBypassMode && !isBypassRunning && !isClsRunning && !autoBypassCountdownTimer) {
        checkAndAutoTriggerBypass();
      }
      // Cập nhật timestamp đồng bộ
      const syncEl = document.getElementById('sheetLastSyncTime');
      if (syncEl) {
        const now = new Date();
        syncEl.textContent = now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      }
    } else {
      sheetDataTableBody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding: 24px; color: #d93025;">❌ ${escapeHtml(data.message || 'Không thể đọc dữ liệu từ Google Sheet')}</td></tr>`;
    }
  } catch (err) {
    sheetDataTableBody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding: 24px; color: #d93025;">❌ Lỗi kết nối khi tải dữ liệu từ Google Sheet</td></tr>';
  }
}


function updateBypassStats(records) {
  const total = records.length;
  let pending = 0;
  let done = 0;
  let hkPass = 0;
  let hkFail = 0;

  records.forEach(r => {
    const st = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
    if (st === 'đã xử lý' || st.includes('vi phạm') || st.includes('từ chối') || st.includes('không thành công')) {
      done++;
    } else {
      pending++;
    }

    const hk = (getRecordField(r, 'Hậu kiểm', 'Hậu Kiểm', 'Hau kiem') || '').trim().toUpperCase();
    const suyHao = (getRecordField(r, 'Suy Hao Hậu Kiểm', 'Suy hao hậu kiểm', 'Suy Hao', 'Suy hao') || '').trim().toLowerCase();
    const isMatTinHieu = suyHao.includes('mất tín hiệu') || hk.toLowerCase().includes('mất tín hiệu');
    if (hk === 'ĐẠT') {
      hkPass++;
    } else if (hk === 'KHÔNG ĐẠT' && !isMatTinHieu) {
      hkFail++;
    }
  });

  if (sheetStatTotal) sheetStatTotal.textContent = total;
  if (sheetStatPending) sheetStatPending.textContent = pending;
  if (sheetStatDone) sheetStatDone.textContent = done;
  if (badgeBypassPending) badgeBypassPending.textContent = `${pending} chờ xử lý`;
  if (sheetRecordCountText) sheetRecordCountText.textContent = `${total} dòng (${pending} chờ)`;

  const statFailEl = document.getElementById('sheetStatHauKiemFail');
  const statPassEl = document.getElementById('sheetStatHauKiemPass');
  const statFailPctEl = document.getElementById('sheetStatHauKiemFailPct');
  if (statFailEl) statFailEl.textContent = hkFail;
  if (statPassEl) statPassEl.textContent = hkPass;
  if (statFailPctEl) {
    const pct = total > 0 ? Math.round((hkFail / total) * 100) : 0;
    statFailPctEl.textContent = `Tỷ lệ không đạt: ${pct}%`;
  }
}

function getRecordField(r, ...possibleKeys) {
  for (const k of possibleKeys) {
    if (r[k] !== undefined && r[k] !== null && String(r[k]).trim() !== '') {
      return String(r[k]).trim();
    }
  }
  return '';
}

// BẢNG TOP CÁC NHÂN SỰ BYPASS KHÔNG ĐẠT NHIỀU NHẤT - TOP 10
function renderTopFailedStaff(records) {
  const container = document.getElementById('topFailedStaffTableBody');
  const badgeTotal = document.getElementById('badgeTopFailedTotal');
  if (!container) return;

  const dateFilter = document.getElementById('selectDateFilterBypass')?.value || 'all';
  let targetRecords = records;
  if (dateFilter && dateFilter !== 'all' && window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.filterRecords === 'function') {
    targetRecords = window.UnifiedWorkTabs.filterRecords(records, { dateRange: dateFilter });
  }

  const staffMap = {};
  let totalFailedCount = 0;

  targetRecords.forEach(r => {
    const email = getRecordField(r, 'Email', 'Nhân viên kỹ thuật', 'Nhân viên kỹ thuật');
    if (!email) return;

    const msnv = getRecordField(r, 'MSNV');
    const account = getRecordField(r, 'Account Inside', 'Account');
    const hk = (getRecordField(r, 'Hậu kiểm', 'Hậu Kiểm', 'Hau kiem') || '').trim().toUpperCase();
    const suyHao = getRecordField(r, 'Suy Hao Hậu Kiểm', 'Suy hao hậu kiểm', 'Suy Hao', 'Suy hao');

    if (!staffMap[email]) {
      staffMap[email] = {
        email: email,
        msnv: msnv,
        account: account,
        total: 0,
        dat: 0,
        khong_dat: 0,
        suyHaoCounts: {}
      };
    }

    staffMap[email].total++;
    const isMatTinHieu = (suyHao || '').toLowerCase().includes('mất tín hiệu') || hk.toLowerCase().includes('mất tín hiệu');
    if (hk === 'KHÔNG ĐẠT' && !isMatTinHieu) {
      staffMap[email].khong_dat++;
      totalFailedCount++;
      if (suyHao) {
        staffMap[email].suyHaoCounts[suyHao] = (staffMap[email].suyHaoCounts[suyHao] || 0) + 1;
      }
    } else if (hk === 'ĐẠT') {
      staffMap[email].dat++;
    }
  });

  if (badgeTotal) {
    badgeTotal.textContent = `${totalFailedCount} ca Không Đạt`;
  }

  // Sắp xếp giảm dần theo số ca Không Đạt, sau đó theo tổng số ca
  const sortedStaff = Object.values(staffMap)
    .filter(s => s.khong_dat > 0)
    .sort((a, b) => {
      if (b.khong_dat !== a.khong_dat) return b.khong_dat - a.khong_dat;
      return b.total - a.total;
    })
    .slice(0, 10);

  if (sortedStaff.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="7" class="text-center py-6 text-slate-400">
          <div class="flex flex-col items-center justify-center gap-1">
            <span class="text-2xl">🎉</span>
            <span class="text-xs font-medium text-emerald-600">Không có nhân sự nào có hợp đồng Bypass "Không Đạt" trong khoảng thời gian đã chọn!</span>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  const maxFailed = sortedStaff[0].khong_dat || 1;

  container.innerHTML = '';
  sortedStaff.forEach((s, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-rose-50/40 transition-colors';

    const pct = Math.round((s.khong_dat / s.total) * 100);
    const barWidth = Math.max(10, Math.round((s.khong_dat / maxFailed) * 100));

    // Huy hiệu Hạng 1, 2, 3 và 4-10
    let rankBadge = `<span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold bg-slate-100 text-slate-700">${idx + 1}</span>`;
    if (idx === 0) {
      rankBadge = `<span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold bg-amber-500 text-white shadow-sm ring-2 ring-amber-200" title="Hạng 1 nhiều Không Đạt nhất">🥇</span>`;
    } else if (idx === 1) {
      rankBadge = `<span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold bg-slate-400 text-white shadow-sm ring-2 ring-slate-200" title="Hạng 2">🥈</span>`;
    } else if (idx === 2) {
      rankBadge = `<span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold bg-amber-700 text-white shadow-sm ring-2 ring-amber-100" title="Hạng 3">🥉</span>`;
    }

    // Liệt kê top nguyên nhân suy hao phổ biến nhất
    const sortedReasons = Object.entries(s.suyHaoCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([reason, cnt]) => `${reason} (${cnt})`)
      .slice(0, 2)
      .join(', ');

    tr.innerHTML = `
      <td style="text-align: center;">${rankBadge}</td>
      <td>
        <div class="flex items-center gap-1.5">
          <span class="font-mono text-xs font-semibold text-slate-800">${escapeHtml(s.email)}</span>
        </div>
      </td>
      <td>
        <div class="text-[11px] font-mono text-slate-600">
          <div class="font-semibold text-slate-700">${escapeHtml(s.account || '—')}</div>
          ${s.msnv ? `<div class="text-[10px] text-slate-400 font-mono">MS: ${escapeHtml(String(s.msnv))}</div>` : ''}
        </div>
      </td>
      <td style="text-align: center;">
        <div class="inline-flex flex-col items-center">
          <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
            ${s.khong_dat} ca
          </span>
          <div class="w-16 h-1.5 bg-slate-200 rounded-full mt-1 overflow-hidden">
            <div class="h-full bg-rose-500 rounded-full transition-all duration-500" style="width: ${barWidth}%;"></div>
          </div>
        </div>
      </td>
      <td style="text-align: center;">
        <div class="text-xs font-medium text-slate-700">
          <span class="font-bold text-rose-600">${pct}%</span>
          <span class="text-slate-400 text-[10.5px]">(${s.khong_dat}/${s.total})</span>
        </div>
      </td>
      <td>
        <span class="text-[11px] text-slate-600 font-mono" title="${escapeHtml(sortedReasons || 'Chưa có thông số suy hao')}">${escapeHtml(sortedReasons || '—')}</span>
      </td>
      <td style="text-align: center;">
        <button type="button" class="btn-filter-staff-bypass px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-rose-50 text-rose-700 hover:bg-rose-100 hover:text-rose-800 transition-colors cursor-pointer border border-rose-200" data-email="${escapeHtml(s.email)}" title="Lọc các hợp đồng của ${escapeHtml(s.email)} trên bảng dưới">
          🔍 Lọc HĐ
        </button>
      </td>
    `;

    container.appendChild(tr);
  });

  // Gắn sự kiện click cho nút "Lọc HĐ"
  container.querySelectorAll('.btn-filter-staff-bypass').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const email = e.currentTarget.dataset.email;
      filterTableByStaff(email);
    });
  });
}

function filterTableByStaff(email) {
  const searchInput = document.getElementById('inputSearchBypassSHD');
  if (searchInput) {
    searchInput.value = email;
  }
  currentBypassPage = 1;
  renderBypassTable(currentBypassRecords);
  const tableEl = document.getElementById('sheetDataTable');
  if (tableEl) {
    tableEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  showSnackbar(`🔍 Đã lọc danh sách theo nhân sự: ${email}`);
}

let currentBypassPage = 1;

function renderBypassTable(records) {
  if (!sheetDataTableBody) return;
  const filter = sheetFilterStatusSelect ? sheetFilterStatusSelect.value : 'all';
  const hkFilter = document.getElementById('sheetFilterHauKiemSelect')?.value || 'all';
  const dateFilter = document.getElementById('selectDateFilterBypass')?.value || 'today';
  const shdSearch = document.getElementById('inputSearchBypassSHD')?.value || '';

  // Update Charts & Top 5 via UnifiedWorkTabs
  if (window.UnifiedWorkTabs) {
    window.UnifiedWorkTabs.updateDailyChart('bypassDailyChart', records, dateFilter);
    window.UnifiedWorkTabs.updateTopStaff('bypassTopStaffContainer', records, dateFilter);
  }

  // Cập nhật Bảng TOP 10 Nhân Sự Bypass Không Đạt Nhiều Nhất
  renderTopFailedStaff(records);

  let filtered = window.UnifiedWorkTabs ? window.UnifiedWorkTabs.filterRecords(records, {
    dateRange: dateFilter,
    shdQuery: shdSearch,
    resultStatus: filter,
    hauKiemFilter: hkFilter
  }) : records;

  // Đảm bảo luôn sắp xếp từ gần nhất đến xa nhất (mới nhất lên đầu)
  if (window.UnifiedWorkTabs && typeof window.UnifiedWorkTabs.sortRecordsNewestFirst === 'function') {
    filtered = window.UnifiedWorkTabs.sortRecordsNewestFirst(filtered);
  }

  if (sheetRecordCountText) {
    sheetRecordCountText.textContent = `${filtered.length}/${records.length} dòng`;
  }

  if (filtered.length === 0) {
    sheetDataTableBody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding: 28px; color: #80868b;">Không có bản ghi nào phù hợp với bộ lọc</td></tr>';
    if (window.UnifiedWorkTabs) {
      window.UnifiedWorkTabs.renderPagination('bypassPagination', { total: 0 });
    }
    return;
  }

  // Phân trang 10 dòng 1 trang
  const pageState = window.UnifiedWorkTabs
    ? window.UnifiedWorkTabs.paginate(filtered, currentBypassPage, 10)
    : { items: filtered.slice(0, 10), currentPage: 1, totalPages: Math.ceil(filtered.length / 10), total: filtered.length, startIdx: 0, endIdx: Math.min(10, filtered.length) };
  currentBypassPage = pageState.currentPage;

  sheetDataTableBody.innerHTML = '';
  pageState.items.forEach((r, idx) => {
    const globalIdx = pageState.startIdx + idx;
    const tr = document.createElement('tr');
    const tacVu = getRecordField(r, 'Tác Vụ', 'Tác Vụ') || 'ByPass';
    const shd = getRecordField(r, 'SHD', 'Số Hợp Đồng', 'Số hợp đồng');
    const email = getRecordField(r, 'Email', 'Nhân viên kỹ thuật', 'Nhân viên kỹ thuật');
    const nn1 = getRecordField(r, 'Nguyên Nhân 1', 'Tình trạng ByPass', 'Tình trạng ByPass');
    const nn2 = getRecordField(r, 'Nguyên Nhân 2', 'Lý do ByPass', 'Lý do ByPass');
    const ngay = getRecordField(r, 'Ngày Cập Nhật', 'Ngày Cập Nhật');
    const thaoTac = getRecordField(r, 'Thao Tác', 'Thao tác');
    const hauKiem = (getRecordField(r, 'Hậu kiểm', 'Hậu Kiểm', 'Hau kiem') || '').trim().toUpperCase();
    const suyHao = getRecordField(r, 'Suy Hao Hậu Kiểm', 'Suy hao hậu kiểm', 'Suy Hao', 'Suy hao');

    tr.dataset.shd = shd;

    // Badge Hậu Kiểm (Cột đầu tiên)
    let badgeHauKiem = '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium text-slate-400 bg-slate-100">—</span>';
    if (hauKiem === 'ĐẠT') {
      badgeHauKiem = `
        <div class="flex flex-col items-center">
          <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-300 shadow-xs">
            ✓ ĐẠT
          </span>
          ${suyHao ? `<span class="text-[10px] text-slate-500 font-mono mt-0.5" title="Suy hao: ${escapeHtml(suyHao)}">${escapeHtml(suyHao)}</span>` : ''}
        </div>
      `;
    } else if (hauKiem === 'KHÔNG ĐẠT') {
      badgeHauKiem = `
        <div class="flex flex-col items-center">
          <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-300 shadow-xs">
            ✕ KHÔNG ĐẠT
          </span>
          ${suyHao ? `<span class="text-[10px] text-rose-600 font-semibold font-mono mt-0.5" title="Suy hao: ${escapeHtml(suyHao)}">${escapeHtml(suyHao)}</span>` : ''}
        </div>
      `;
    } else if (suyHao) {
      badgeHauKiem = `<span class="text-[11px] text-slate-600 font-mono">${escapeHtml(suyHao)}</span>`;
    }

    let badgeThaoTac = '<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">⏳ Chưa xử lý</span>';
    const ttLower = thaoTac.toLowerCase();
    if (ttLower === 'đã xử lý') {
      badgeThaoTac = '<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">✓ Đã xử lý</span>';
    } else if (ttLower.includes('vi phạm') || ttLower.includes('từ chối') || ttLower.includes('không thành công')) {
      badgeThaoTac = `<span class="inline-block px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 max-w-[300px] whitespace-normal leading-snug" title="${escapeHtml(thaoTac)}">⛔ ${escapeHtml(thaoTac)}</span>`;
    } else if (ttLower === 'lỗi' || ttLower.startsWith('lỗi')) {
      badgeThaoTac = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">✕ ${escapeHtml(thaoTac)}</span>`;
    } else if (thaoTac && !['chưa xử lý', 'chưa cập nhật', 'nan'].includes(ttLower)) {
      badgeThaoTac = `<span class="inline-block px-2.5 py-0.5 rounded-lg text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">${escapeHtml(thaoTac)}</span>`;
    }

    tr.innerHTML = `
      <td style="text-align: center;" data-col="hau-kiem">${badgeHauKiem}</td>
      <td style="color:#5f6368; font-weight:500;">${globalIdx + 1}</td>
      <td><span class="font-medium text-slate-700">${escapeHtml(tacVu)}</span></td>
      <td><strong class="font-mono text-blue-700 text-xs" data-col="shd">${escapeHtml(shd)}</strong></td>
      <td><span class="font-mono text-[11.5px] text-slate-700" data-col="email">${escapeHtml(email)}</span></td>
      <td><span class="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-800 text-[11px] font-medium">${escapeHtml(nn1)}</span></td>
      <td><span class="text-slate-600 text-[11.5px]">${escapeHtml(nn2)}</span></td>
      <td><span class="text-slate-500 font-mono text-[11px]" data-col="ngay">${escapeHtml(ngay)}</span></td>
      <td data-col="thao-tac">${badgeThaoTac}</td>
      <td style="text-align: center;">
        <button type="button" class="btn-run-single-bypass px-2 py-1 rounded-lg text-[11px] font-medium bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors cursor-pointer" data-shd="${escapeHtml(shd)}" data-row-id="${escapeHtml(String(r['ID'] || ''))}" title="Chạy ByPass chỉ cho hợp đồng này">
          ▶ Chạy
        </button>
      </td>
    `;

    sheetDataTableBody.appendChild(tr);
  });

  // Render pagination bar
  if (window.UnifiedWorkTabs) {
    window.UnifiedWorkTabs.renderPagination('bypassPagination', pageState, (newPage) => {
      currentBypassPage = newPage;
      renderBypassTable(currentBypassRecords);
    });
  }

  // Attach click events for single row runs
  sheetDataTableBody.querySelectorAll('.btn-run-single-bypass').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const shd = e.currentTarget.dataset.shd;
      const rowId = e.currentTarget.dataset.rowId;
      const targetRecord = (rowId && currentBypassRecords.find(r => String(r['ID'] || '') === rowId))
        || [...currentBypassRecords].reverse().find(r => getRecordField(r, 'SHD', 'Số Hợp Đồng', 'Số hợp đồng') === shd);
      if (targetRecord) {
        runBypassProcess([targetRecord]);
      }
    });
  });
}

// Filter change event
if (sheetFilterStatusSelect) {
  sheetFilterStatusSelect.addEventListener('change', () => {
    renderBypassTable(currentBypassRecords);
  });
}

// Refresh Sheet Data Button
if (btnRefreshSheetData) {
  btnRefreshSheetData.addEventListener('click', () => {
    showSnackbar('Đang tải lại dữ liệu mới nhất từ Google Sheet...');
    loadBypassSheetData(currentBypassGid);
  });
}

// Run Auto ByPass Process
async function runBypassProcess(specificRecords = null) {
  if (isBypassRunning) {
    showSnackbar('Đang có tiến trình Auto ByPass đang chạy...');
    return;
  }

  const headless = chkByPassVisible ? !chkByPassVisible.checked : true;
  const payload = {
    gid: currentBypassGid,
    headless: headless
  };

  if (specificRecords && specificRecords.length > 0) {
    payload.records = specificRecords;
  }

  try {
    setBypassButtonRunning(true);
    if (bypassProgressTracker) bypassProgressTracker.style.display = 'block';
    if (bypassTrackerStatus) bypassTrackerStatus.textContent = 'Đang khởi tạo trình duyệt Chrome Inside FPT...';
    if (bypassTrackerPercent) bypassTrackerPercent.textContent = '0%';
    if (bypassTrackerFill) bypassTrackerFill.style.width = '0%';

    showSnackbar('Đang kết nối Chrome và điều hướng trang Quản Lý ByPass Inside...');

    const res = await fetch('/api/bypass/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok) {
      isBypassRunning = true;
      showSnackbar(`Đã bắt đầu xử lý ${data.count || ''} hợp đồng!`);
    } else {
      setBypassButtonRunning(false);
      if (bypassProgressTracker) bypassProgressTracker.style.display = 'none';
      showSnackbar(data.message || 'Lỗi khi khởi chạy Auto ByPass');
    }
  } catch (err) {
    setBypassButtonRunning(false);
    if (bypassProgressTracker) bypassProgressTracker.style.display = 'none';
    showSnackbar('Lỗi kết nối khi gửi lệnh Auto ByPass');
  }
}

if (btnRunAutoBypass) {
  btnRunAutoBypass.addEventListener('click', () => {
    runBypassProcess();
  });
}

function setBypassButtonRunning(running) {
  if (!btnRunAutoBypass) return;
  if (running) {
    btnRunAutoBypass.disabled = true;
    if (bypassSpinner) bypassSpinner.style.display = 'inline-block';
    if (bypassRunIcon) bypassRunIcon.style.display = 'none';
    if (bypassRunText) bypassRunText.textContent = 'Đang Auto ByPass...';
  } else {
    btnRunAutoBypass.disabled = false;
    if (bypassSpinner) bypassSpinner.style.display = 'none';
    if (bypassRunIcon) bypassRunIcon.style.display = 'inline';
    if (bypassRunText) bypassRunText.textContent = 'Bắt Đầu Auto ByPass Trên Inside';
  }
}

// Poll ByPass Progress & Status (sử dụng live-status API để cập nhật UI tức thì)
async function pollBypassStatus() {
  try {
    const res = await fetch('/api/bypass/live-status');
    if (res.ok) {
      const d = await res.json();
      const task = d.task || {};
      const processedInSession = d.processed_in_session || [];

      // Cập nhật badge/trạng thái từng hàng trong bảng UI ngay lập tức
      if (processedInSession.length > 0) {
        processedInSession.forEach(item => {
          if (!lastProcessedShdSet.has(item.shd)) {
            lastProcessedShdSet.add(item.shd);
            // Tìm hàng trong bảng và cập nhật badge ngay
            updateRowStatusInTable(item.shd, item.status, item.time);
          }
        });
      }

      if (task.is_running) {
        isBypassRunning = true;
        setBypassButtonRunning(true);
        if (bypassProgressTracker) bypassProgressTracker.style.display = 'block';

        const currentIdx = task.current_index || 0;
        const total = task.total || 1;
        const pct = Math.min(100, Math.round((currentIdx / total) * 100));

        if (bypassTrackerPercent) bypassTrackerPercent.textContent = `${pct}%`;
        if (bypassTrackerFill) bypassTrackerFill.style.width = `${pct}%`;
        if (bypassTrackerStatus) bypassTrackerStatus.textContent = task.message || `Đang xử lý HĐ ${task.current_shd || ''}...`;
      } else {
        if (isBypassRunning) {
          // Vừa hoàn tất
          isBypassRunning = false;
          setBypassButtonRunning(false);
          if (bypassTrackerPercent) bypassTrackerPercent.textContent = '100%';
          if (bypassTrackerFill) bypassTrackerFill.style.width = '100%';
          if (bypassTrackerStatus) bypassTrackerStatus.textContent = task.message || 'Hoàn tất Auto ByPass!';
          showSnackbar('Tiến trình Auto ByPass đã hoàn tất!');
          setTimeout(() => {
            if (bypassProgressTracker && !isBypassRunning) bypassProgressTracker.style.display = 'none';
          }, 5000);
          // Reset tracking set và reload bảng lần cuối để đồng bộ
          lastProcessedShdSet.clear();
          loadBypassSheetData(currentBypassGid);
          // Nếu có tiến trình Clear Cls đang đợi, kích hoạt kiểm tra ngay
          if (autoClsMode && !isClsRunning && !autoClsCountdownTimer) {
            setTimeout(checkAndAutoTriggerCls, 1000);
          }
        }
      }
    }
  } catch (e) {}
}

// Cập nhật trạng thái badge của một hàng trong bảng ngầm (không reload toàn bộ)
function updateRowStatusInTable(shd, status, timeStr) {
  if (!sheetDataTableBody) return;
  const allRows = sheetDataTableBody.querySelectorAll('tr');
  allRows.forEach(row => {
    // Tìm bằng data-col="shd" hoặc tr.dataset.shd
    const shdCell = row.querySelector('[data-col="shd"]');
    if (shdCell && shdCell.textContent.trim() === shd) {
      // Cập nhật cột Thao Tác
      const thaoTacCell = row.querySelector('[data-col="thao-tac"]');
      const ngayCell = row.querySelector('[data-col="ngay"]');
      if (thaoTacCell) {
        let badgeHtml = '';
        const stLower = String(status || '').trim().toLowerCase();
        if (stLower === 'đã xử lý') {
          badgeHtml = '<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 transition-all">\u2713 Đã xử lý</span>';
          row.style.transition = 'background 0.5s';
          row.style.background = 'rgba(16, 185, 129, 0.06)';
          setTimeout(() => { row.style.background = ''; }, 3000);
        } else if (stLower.includes('vi phạm') || stLower.includes('từ chối') || stLower.includes('không thành công')) {
          badgeHtml = `<span class="inline-block px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 max-w-[300px] whitespace-normal leading-snug" title="${escapeHtml(status)}">⛔ ${escapeHtml(status)}</span>`;
          row.style.background = 'rgba(239, 68, 68, 0.06)';
        } else if (stLower === 'lỗi' || stLower.startsWith('lỗi')) {
          badgeHtml = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">✕ ${escapeHtml(status)}</span>`;
          row.style.background = 'rgba(239, 68, 68, 0.05)';
        }
        if (badgeHtml) thaoTacCell.innerHTML = badgeHtml;
      }
      if (ngayCell && timeStr) {
        ngayCell.innerHTML = `<span class="text-slate-500 font-mono text-[11px]">${escapeHtml(timeStr)}</span>`;
      }
      // Cập nhật KPI realtime
      const updatedRecords = currentBypassRecords.map(r => {
        const rShd = String(r['SHD'] || r['Số Hợp Đồng'] || '').trim();
        if (rShd === shd) {
          return Object.assign({}, r, { 'Thao Tác': status, 'Ngày Cập Nhật': timeStr || '' });
        }
        return r;
      });
      currentBypassRecords = updatedRecords;
      updateBypassStats(currentBypassRecords);
    }
  });
}

// Live Terminal Logs Rendering
function renderBypassTerminalLogs(logs) {
  if (!bypassLogTerminal) return;
  if (!logs || logs.length === 0) return;

  // Lọc các log liên quan ByPass hoặc thông báo Inside FPT
  const relevant = logs.filter(l => {
    const txt = (l.text || '').toLowerCase();
    return txt.includes('bypass') || txt.includes('đăng nhập') || txt.includes('phiên') || txt.includes('inside');
  });
  const displayLogs = (relevant.length > 0 ? relevant : logs).slice(-40);
  bypassLogTerminal.innerHTML = '';
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
    bypassLogTerminal.appendChild(item);
  });
  bypassLogTerminal.scrollTop = bypassLogTerminal.scrollHeight;
}

if (btnClearBypassLogs && bypassLogTerminal) {
  btnClearBypassLogs.addEventListener('click', () => {
    bypassLogTerminal.innerHTML = '<div class="text-slate-500 italic">Nhật ký đã được làm sạch</div>';
  });
}

// Xuất data xử lý ByPass ra Excel
if (btnExportBypassData) {
  btnExportBypassData.addEventListener('click', () => {
    showSnackbar('Đang chuẩn bị file Excel xuất dữ liệu ByPass...');
    window.location.href = `/api/bypass/export?gid=${encodeURIComponent(currentBypassGid)}&status=all`;
  });
}

// Google Sheet Webhook Modal Controls
if (btnOpenSheetWebhookModal) {
  btnOpenSheetWebhookModal.addEventListener('click', async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const cfg = await res.json();
        if (inputSheetWebhookUrl) inputSheetWebhookUrl.value = cfg.google_sheet_webhook_url || '';
      }
    } catch (e) {}
    if (sheetWebhookModalBackdrop) sheetWebhookModalBackdrop.classList.add('open');
  });
}

function closeSheetWebhookModal() {
  if (sheetWebhookModalBackdrop) sheetWebhookModalBackdrop.classList.remove('open');
}

if (btnCloseSheetWebhookModal) btnCloseSheetWebhookModal.addEventListener('click', closeSheetWebhookModal);
if (btnCancelSheetWebhook) btnCancelSheetWebhook.addEventListener('click', closeSheetWebhookModal);
if (sheetWebhookModalBackdrop) {
  sheetWebhookModalBackdrop.addEventListener('click', (e) => {
    if (e.target === sheetWebhookModalBackdrop) closeSheetWebhookModal();
  });
}

const btnShowWebhookGuide = document.getElementById('btnShowWebhookGuide');
const btnShowWebhookGuideHeader = document.getElementById('btnShowWebhookGuideHeader');
const webhookGuideModalBackdrop = document.getElementById('webhookGuideModalBackdrop');
const btnCloseWebhookGuide = document.getElementById('btnCloseWebhookGuide');
const btnOkWebhookGuide = document.getElementById('btnOkWebhookGuide');
const btnCopyScriptCode = document.getElementById('btnCopyScriptCode');
const appsScriptCodeBlock = document.getElementById('appsScriptCodeBlock');
const webhookStatusBadge = document.getElementById('webhookStatusBadge');

function openWebhookGuide() {
  if (webhookGuideModalBackdrop) webhookGuideModalBackdrop.classList.add('open');
}

function closeWebhookGuide() {
  if (webhookGuideModalBackdrop) webhookGuideModalBackdrop.classList.remove('open');
}

if (btnShowWebhookGuide) btnShowWebhookGuide.addEventListener('click', openWebhookGuide);
if (btnShowWebhookGuideHeader) btnShowWebhookGuideHeader.addEventListener('click', openWebhookGuide);
if (btnCloseWebhookGuide) btnCloseWebhookGuide.addEventListener('click', closeWebhookGuide);
if (btnOkWebhookGuide) btnOkWebhookGuide.addEventListener('click', closeWebhookGuide);
if (webhookGuideModalBackdrop) {
  webhookGuideModalBackdrop.addEventListener('click', (e) => {
    if (e.target === webhookGuideModalBackdrop) closeWebhookGuide();
  });
}
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && webhookGuideModalBackdrop && webhookGuideModalBackdrop.classList.contains('open')) {
    closeWebhookGuide();
  }
});
if (btnCopyScriptCode && appsScriptCodeBlock) {
  btnCopyScriptCode.addEventListener('click', () => {
    navigator.clipboard.writeText(appsScriptCodeBlock.textContent);
    showSnackbar('Đã sao chép mã Google Apps Script vào bộ nhớ tạm!');
  });
}

if (btnSaveSheetWebhook) {
  btnSaveSheetWebhook.addEventListener('click', async () => {
    const hookUrl = inputSheetWebhookUrl ? inputSheetWebhookUrl.value.trim() : '';
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ google_sheet_webhook_url: hookUrl })
      });
      if (res.ok) {
        showSnackbar('Đã lưu cấu hình Webhook Google Sheet thành công!');
        closeSheetWebhookModal();
        if (webhookStatusBadge) {
          if (hookUrl) {
            webhookStatusBadge.textContent = '✓ Đã kết nối Webhook';
            webhookStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200';
          } else {
            webhookStatusBadge.textContent = 'Chưa kết nối Webhook';
            webhookStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200';
          }
        }
      } else {
        showSnackbar('Lỗi khi lưu cấu hình Webhook');
      }
    } catch (e) {
      showSnackbar('Lỗi kết nối khi lưu cấu hình');
    }
  });
}

// Clear Cls Webhook Controls
const btnSaveClsWebhook = document.getElementById('btnSaveClsWebhook');
const inputClsWebhookUrl = document.getElementById('inputClsWebhookUrl');
const clsWebhookStatusBadge = document.getElementById('clsWebhookStatusBadge');
const btnShowClsWebhookGuide = document.getElementById('btnShowClsWebhookGuide');

if (btnShowClsWebhookGuide) {
  btnShowClsWebhookGuide.addEventListener('click', openWebhookGuide);
}

if (btnSaveClsWebhook) {
  btnSaveClsWebhook.addEventListener('click', async () => {
    const clsHookUrl = inputClsWebhookUrl ? inputClsWebhookUrl.value.trim() : '';
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cls_webhook_url: clsHookUrl })
      });
      if (res.ok) {
        showSnackbar('✓ Đã lưu Webhook Clear Cls thành công!');
        if (clsWebhookStatusBadge) {
          if (clsHookUrl) {
            clsWebhookStatusBadge.textContent = '✓ Đã kết nối Webhook Clear Cls';
            clsWebhookStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200';
          } else {
            clsWebhookStatusBadge.textContent = 'Chưa kết nối Webhook';
            clsWebhookStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200';
          }
        }
      } else {
        showSnackbar('Lỗi khi lưu Webhook Clear Cls');
      }
    } catch (e) {
      showSnackbar('Lỗi kết nối khi lưu Webhook');
    }
  });
}

// ===================== AUTO MODE BYPASS =====================
const btnAutoModeToggle = document.getElementById('btnAutoModeToggle');
const autoModeIcon = document.getElementById('autoModeIcon');
const autoModeText = document.getElementById('autoModeText');
const autoModeDot = document.getElementById('autoModeDot');

function updateAutoModeUI() {
  if (!btnAutoModeToggle) return;
  const sidebarBadge = document.getElementById('sidebarAutoBypassBadge');
  if (autoBypassMode) {
    btnAutoModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-amber-400 bg-amber-50 text-amber-700 transition-all shadow-sm animate-pulse';
    if (autoModeIcon) autoModeIcon.textContent = '🤖';
    if (autoModeText) autoModeText.textContent = 'Tự Động: BẬT';
    if (autoModeDot) { autoModeDot.className = 'w-2 h-2 rounded-full bg-amber-500 transition-all animate-bounce'; }
    if (sidebarBadge) sidebarBadge.classList.remove('hidden');
  } else {
    btnAutoModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-slate-200 bg-white text-slate-600 hover:border-amber-400 hover:bg-amber-50 hover:text-amber-700 transition-all shadow-sm';
    if (autoModeIcon) autoModeIcon.textContent = '🤖';
    if (autoModeText) autoModeText.textContent = 'Tự Động: TẮT';
    if (autoModeDot) { autoModeDot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all'; }
    if (sidebarBadge) sidebarBadge.classList.add('hidden');
  }
}

if (btnAutoModeToggle) {
  btnAutoModeToggle.addEventListener('click', () => {
    autoBypassMode = !autoBypassMode;
    localStorage.setItem('autoBypassMode', autoBypassMode ? 'true' : 'false');
    updateAutoModeUI();
    fetch('/api/auto-modes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bypass: autoBypassMode })
    }).catch(() => {});
    if (autoBypassMode) {
      showSnackbar('🤖 Chế độ Tự Động ByPass đã BẬT - Hệ thống chạy nền tự động sẽ điều phối!');
    } else {
      showSnackbar('Chế độ Tự Động ByPass đã TẮT.');
      if (autoBypassCountdownTimer) {
        clearInterval(autoBypassCountdownTimer);
        autoBypassCountdownTimer = null;
        if (autoModeText) autoModeText.textContent = 'Tự Động: TẮT';
      }
    }
  });
}

// Auto chỉ chạy HĐ chưa từng được Auto thử (lưu 6 giờ) – tránh chạy lại vòng lặp HĐ lỗi. Chạy tay vẫn thử lại được.
function _bypassAutoKey(r) {
  const shd = String(r['SHD'] || r['Số Hợp Đồng'] || '').trim();
  const id = String(r['ID'] || '').trim();
  return id ? `${shd}_${id}` : shd;
}
function _bypassAutoTriedMap() {
  try { return JSON.parse(localStorage.getItem('bypassAutoTried') || '{}'); } catch (e) { return {}; }
}
function _bypassAutoPending(r) {
  const st = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
  if (st === 'đã xử lý' || st.includes('vi phạm') || st.includes('từ chối') || st.includes('không thành công')) return false;
  const t = _bypassAutoTriedMap()[_bypassAutoKey(r)];
  return !(t && Date.now() - t < 5 * 60 * 1000);
}
function _bypassMarkAutoTried(rows) {
  const m = _bypassAutoTriedMap();
  const now = Date.now();
  Object.keys(m).forEach(k => { if (now - m[k] > 5 * 60 * 1000) delete m[k]; });
  rows.forEach(r => { m[_bypassAutoKey(r)] = now; });
  localStorage.setItem('bypassAutoTried', JSON.stringify(m));
}

// Việc tự động kích hoạt được điều phối tập trung ở Backend (_auto_orchestrator_loop)
function checkAndAutoTriggerBypass() {
  return;
}

// Filter & Search events for ByPass
document.getElementById('selectDateFilterBypass')?.addEventListener('change', () => { currentBypassPage = 1; renderBypassTable(currentBypassRecords); });
document.getElementById('inputSearchBypassSHD')?.addEventListener('input', () => { currentBypassPage = 1; renderBypassTable(currentBypassRecords); });
document.getElementById('sheetFilterHauKiemSelect')?.addEventListener('change', () => { currentBypassPage = 1; renderBypassTable(currentBypassRecords); });
document.getElementById('sheetFilterStatusSelect')?.addEventListener('change', () => { currentBypassPage = 1; renderBypassTable(currentBypassRecords); });
document.getElementById('btnFilterAllFailedRecords')?.addEventListener('click', () => {
  const sel = document.getElementById('sheetFilterHauKiemSelect');
  if (sel) sel.value = 'fail';
  const inp = document.getElementById('inputSearchBypassSHD');
  if (inp) inp.value = '';
  currentBypassPage = 1;
  renderBypassTable(currentBypassRecords);
  const tableEl = document.getElementById('sheetDataTable');
  if (tableEl) tableEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  showSnackbar('🔍 Đã lọc hiển thị toàn bộ các hợp đồng Hậu kiểm KHÔNG ĐẠT');
});
document.getElementById('btnClearBypassCache')?.addEventListener('click', async () => {
  try {
    await fetch('/api/bypass/clear-cache', { method: 'POST' });
    showSnackbar('🧹 Đã xóa cache trạng thái ByPass!');
    loadBypassSheetData('0');
  } catch (e) {
    showSnackbar('Không thể xóa cache ByPass');
  }
});

registerTab('tab-tasks', {
  title: 'Auto Bypass',
  onActivate() {
    if (currentBypassRecords.length > 0 && !isBypassRunning) renderBypassTable(currentBypassRecords);
    loadBypassSheetData('0');
  }
});
