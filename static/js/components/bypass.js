// ==========================================================
// COMPONENT: AUTO BYPASS (tab-tasks)
// ==========================================================

// ========================================================
// TAB 3: AUTO BYPASS - QUẢN LÝ BYPASS & GOOGLE SHEETS
// ========================================================

// ByPass Google Sheet GID 0
function switchBypassSubTab(gid = '0') {
  currentBypassGid = gid;
  if (sheetCurrentTabTitle) sheetCurrentTabTitle.textContent = 'ByPass (GID: 0)';
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
    sheetDataTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 28px; color: #80868b;"><span>⏳ Đang tải dữ liệu từ Google Sheet...</span></td></tr>';
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
      sheetDataTableBody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 24px; color: #d93025;">❌ ${escapeHtml(data.message || 'Không thể đọc dữ liệu từ Google Sheet')}</td></tr>`;
    }
  } catch (err) {
    sheetDataTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 24px; color: #d93025;">❌ Lỗi kết nối khi tải dữ liệu từ Google Sheet</td></tr>';
  }
}


function updateBypassStats(records) {
  const total = records.length;
  let pending = 0;
  let done = 0;

  records.forEach(r => {
    const st = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
    if (st === 'đã xử lý') {
      done++;
    } else {
      pending++;
    }
  });

  if (sheetStatTotal) sheetStatTotal.textContent = total;
  if (sheetStatPending) sheetStatPending.textContent = pending;
  if (sheetStatDone) sheetStatDone.textContent = done;
  if (badgeBypassPending) badgeBypassPending.textContent = `${pending} chờ xử lý`;
  if (sheetRecordCountText) sheetRecordCountText.textContent = `${total} dòng (${pending} chờ)`;
}

function getRecordField(r, ...possibleKeys) {
  for (const k of possibleKeys) {
    if (r[k] !== undefined && r[k] !== null && String(r[k]).trim() !== '') {
      return String(r[k]).trim();
    }
  }
  return '';
}

function renderBypassTable(records) {
  if (!sheetDataTableBody) return;
  const filter = sheetFilterStatusSelect ? sheetFilterStatusSelect.value : 'all';

  let filtered = records.filter(r => {
    const st = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
    if (filter === 'pending') return st !== 'đã xử lý';
    if (filter === 'done') return st === 'đã xử lý';
    return true;
  });

  if (filtered.length === 0) {
    sheetDataTableBody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 28px; color: #80868b;">Không có bản ghi nào phù hợp với bộ lọc</td></tr>';
    return;
  }

  sheetDataTableBody.innerHTML = '';
  filtered.forEach((r, idx) => {
    const tr = document.createElement('tr');
    const tacVu = getRecordField(r, 'Tác Vụ', 'Tác Vụ') || 'ByPass';
    const shd = getRecordField(r, 'SHD', 'Số Hợp Đồng', 'Số hợp đồng');
    const email = getRecordField(r, 'Email', 'Nhân viên kỹ thuật', 'Nhân viên kỹ thuật');
    const nn1 = getRecordField(r, 'Nguyên Nhân 1', 'Tình trạng ByPass', 'Tình trạng ByPass');
    const nn2 = getRecordField(r, 'Nguyên Nhân 2', 'Lý do ByPass', 'Lý do ByPass');
    const ngay = getRecordField(r, 'Ngày Cập Nhật', 'Ngày Cập Nhật');
    const thaoTac = getRecordField(r, 'Thao Tác', 'Thao tác');

    let badgeThaoTac = '<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">⏳ Chưa xử lý</span>';
    if (thaoTac.toLowerCase() === 'đã xử lý') {
      badgeThaoTac = '<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">✓ Đã xử lý</span>';
    } else if (thaoTac.toLowerCase() === 'lỗi') {
      badgeThaoTac = '<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">✕ Lỗi</span>';
    }

    tr.innerHTML = `
      <td style="color:#5f6368; font-weight:500;">${idx + 1}</td>
      <td><span class="font-medium text-slate-700">${escapeHtml(tacVu)}</span></td>
      <td><strong class="font-mono text-blue-700 text-xs">${escapeHtml(shd)}</strong></td>
      <td><span class="font-mono text-[11.5px] text-slate-700">${escapeHtml(email)}</span></td>
      <td><span class="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-800 text-[11px] font-medium">${escapeHtml(nn1)}</span></td>
      <td><span class="text-slate-600 text-[11.5px]">${escapeHtml(nn2)}</span></td>
      <td><span class="text-slate-500 font-mono text-[11px]">${escapeHtml(ngay)}</span></td>
      <td>${badgeThaoTac}</td>
      <td style="text-align: center;">
        <button type="button" class="btn-run-single-bypass px-2 py-1 rounded-lg text-[11px] font-medium bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors" data-shd="${escapeHtml(shd)}" title="Chạy ByPass chỉ cho hợp đồng này">
          ▶ Chạy
        </button>
      </td>
    `;

    sheetDataTableBody.appendChild(tr);
  });

  // Attach click events for single row runs
  sheetDataTableBody.querySelectorAll('.btn-run-single-bypass').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const shd = e.currentTarget.dataset.shd;
      const targetRecord = currentBypassRecords.find(r => getRecordField(r, 'SHD', 'Số Hợp Đồng', 'Số hợp đồng') === shd);
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
      showSnackbar(data.message || 'Lỗi khi khởi chạy Auto ByPass');
    }
  } catch (err) {
    setBypassButtonRunning(false);
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
    // Tìm cột SHD trong row
    const cells = row.querySelectorAll('td');
    if (cells.length < 4) return;
    const shdCell = cells[2]; // STT, Tác Vụ, SHD, ...
    if (shdCell && shdCell.textContent.trim() === shd) {
      // Cập nhật cột Thao Tác (index 7)
      const thaoTacCell = cells[7];
      const ngayCell = cells[6]; // Ngày Cập Nhật
      if (thaoTacCell) {
        let badgeHtml = '';
        if (status === 'Đã xử lý') {
          badgeHtml = '<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 transition-all">\u2713 Đã xử lý</span>';
          row.style.transition = 'background 0.5s';
          row.style.background = 'rgba(16, 185, 129, 0.06)';
          setTimeout(() => { row.style.background = ''; }, 3000);
        } else if (status === 'Lỗi') {
          badgeHtml = '<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">✕ Lỗi</span>';
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
    if (autoBypassMode) {
      showSnackbar('🤖 Chế độ Tự Động ByPass đã BẬT - Sẽ tự xử lý khi phát hiện hợp đồng mới kể cả khi bạn ở tab khác!');
      // Kiểm tra ngay lập tức sau khi bật
      checkAndAutoTriggerBypass();
    } else {
      showSnackbar('Chế độ Tự Động ByPass đã TẮT.');
      // Hủy countdown nếu đang đếm
      if (autoBypassCountdownTimer) {
        clearInterval(autoBypassCountdownTimer);
        autoBypassCountdownTimer = null;
        if (autoModeText) autoModeText.textContent = 'Tự Động: TẮT';
      }
    }
  });
}

// Kiểm tra và tự kích hoạt bypass nếu có dòng chưa xử lý
function checkAndAutoTriggerBypass() {
  if (!autoBypassMode || isBypassRunning || isClsRunning) return;

  // Đếm số dòng chưa xử lý
  const pendingRows = currentBypassRecords.filter(r => {
    const st = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
    return st !== 'đã xử lý';
  });

  if (pendingRows.length === 0) return; // Không có gì để chạy

  // Nếu đang có countdown rồi thì không tạo thêm
  if (autoBypassCountdownTimer) return;

  // Đếm ngược 3 giây rồi tự chạy
  autoBypassCountdown = 3;
  if (autoModeText) autoModeText.textContent = `Tự Động: chạy sau ${autoBypassCountdown}s...`;
  showSnackbar(`🤖 Phát hiện ${pendingRows.length} hợp đồng ByPass chưa xử lý - Tự khởi động sau 3 giây...`);

  autoBypassCountdownTimer = setInterval(() => {
    autoBypassCountdown--;
    if (autoBypassCountdown > 0) {
      if (autoModeText) autoModeText.textContent = `Tự Động: chạy sau ${autoBypassCountdown}s...`;
    } else {
      clearInterval(autoBypassCountdownTimer);
      autoBypassCountdownTimer = null;
      if (autoModeText) autoModeText.textContent = 'Tự Động: BẬT';

      // Kiểm tra lại lần nữa trước khi chạy
      if (!autoBypassMode || isBypassRunning || isClsRunning) return;
      const stillPending = currentBypassRecords.filter(r => {
        const st = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
        return st !== 'đã xử lý';
      });
      if (stillPending.length > 0) {
        showSnackbar(`🚀 Tự động khởi động ByPass ${stillPending.length} hợp đồng...`);
        runBypassProcess(stillPending);
      }
    }
  }, 1000);
}

registerTab('tab-tasks', {
  title: 'Auto Bypass',
  onActivate() {
    if (currentBypassRecords.length > 0 && !isBypassRunning) renderBypassTable(currentBypassRecords);
    loadBypassSheetData('0');
  }
});
