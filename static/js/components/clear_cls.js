// ==========================================================
// COMPONENT: AUTO CLEAR CLS CÓ SR (tab-clear-cls)
// ==========================================================

// ========================================================
// TAB 4: AUTO CLEAR CLS CÓ SR (GID: 987552880)
// ========================================================
const badgeClsPending = document.getElementById('badgeClsPending');
const clsStatTotal = document.getElementById('clsStatTotal');
const clsStatPending = document.getElementById('clsStatPending');
const clsStatDone = document.getElementById('clsStatDone');
const clsStatError = document.getElementById('clsStatError');
const chkClsVisible = document.getElementById('chkClsVisible');
const btnRunAutoCls = document.getElementById('btnRunAutoCls');
const clsSpinner = document.getElementById('clsSpinner');
const clsRunIcon = document.getElementById('clsRunIcon');
const clsRunText = document.getElementById('clsRunText');
const clsProgressTracker = document.getElementById('clsProgressTracker');
const clsTrackerStatus = document.getElementById('clsTrackerStatus');
const clsTrackerPercent = document.getElementById('clsTrackerPercent');
const clsProgressBar = document.getElementById('clsProgressBar');
const inputSearchCls = document.getElementById('inputSearchCls');
const selectClsFilterStatus = document.getElementById('selectClsFilterStatus');
const selectClsFilterReason = document.getElementById('selectClsFilterReason');
const chkClsSelectAll = document.getElementById('chkClsSelectAll');
const tbodyClsList = document.getElementById('tbodyClsList');
const clsTableFooterText = document.getElementById('clsTableFooterText');
const clsSelectedCountText = document.getElementById('clsSelectedCountText');
const btnRefreshClsSheetData = document.getElementById('btnRefreshClsSheetData');

let currentClsRecords = [];
let selectedClsShds = new Set();
let isClsRunning = false;

// ===================== AUTO MODE CLEAR CLS =====================
const btnAutoClsModeToggle = document.getElementById('btnAutoClsModeToggle');
const autoClsModeIcon = document.getElementById('autoClsModeIcon');
const autoClsModeText = document.getElementById('autoClsModeText');
const autoClsModeDot = document.getElementById('autoClsModeDot');

function updateAutoClsModeUI() {
  if (!btnAutoClsModeToggle) return;
  const sidebarBadge = document.getElementById('sidebarAutoClsBadge');
  if (autoClsMode) {
    btnAutoClsModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-indigo-500 bg-indigo-50 text-indigo-700 transition-all shadow-sm animate-pulse cursor-pointer';
    if (autoClsModeIcon) autoClsModeIcon.textContent = '🤖';
    if (autoClsModeText) autoClsModeText.textContent = 'Tự Động: BẬT';
    if (autoClsModeDot) { autoClsModeDot.className = 'w-2 h-2 rounded-full bg-indigo-600 transition-all animate-bounce'; }
    if (sidebarBadge) sidebarBadge.classList.remove('hidden');
  } else {
    btnAutoClsModeToggle.className = 'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border-2 border-slate-200 bg-white text-slate-600 hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-700 transition-all shadow-sm cursor-pointer';
    if (autoClsModeIcon) autoClsModeIcon.textContent = '🤖';
    if (autoClsModeText) autoClsModeText.textContent = 'Tự Động: TẮT';
    if (autoClsModeDot) { autoClsModeDot.className = 'w-2 h-2 rounded-full bg-slate-300 transition-all'; }
    if (sidebarBadge) sidebarBadge.classList.add('hidden');
  }
}

if (btnAutoClsModeToggle) {
  btnAutoClsModeToggle.addEventListener('click', () => {
    autoClsMode = !autoClsMode;
    localStorage.setItem('autoClsMode', autoClsMode ? 'true' : 'false');
    updateAutoClsModeUI();
    if (autoClsMode) {
      showSnackbar('🤖 Chế độ Tự Động Clear Cls đã BẬT - Sẽ tự xử lý khi phát hiện hợp đồng chưa cập nhật kể cả khi bạn ở tab khác!');
      checkAndAutoTriggerCls();
    } else {
      showSnackbar('Chế độ Tự Động Clear Cls đã TẮT.');
      if (autoClsCountdownTimer) {
        clearInterval(autoClsCountdownTimer);
        autoClsCountdownTimer = null;
        if (autoClsModeText) autoClsModeText.textContent = 'Tự Động: TẮT';
      }
    }
  });
}

// Kiểm tra và tự kích hoạt Clear Cls nếu có dòng chưa cập nhật / chưa xử lý
function checkAndAutoTriggerCls() {
  if (!autoClsMode || isClsRunning || isBypassRunning) return;

  // Đếm số dòng chưa cập nhật (chưa xử lý)
  const pendingRows = currentClsRecords.filter(r => {
    const kq = String(r['Kết Quả'] || r['Kết Quả'] || '').trim().toLowerCase();
    const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
    const isDone = kq === 'đã xử lý' || 
                   tt === 'đã clear' || 
                   tt.includes('cập nhật thành công') || 
                   (tt.includes('thành công') && !tt.includes('không')) || 
                   tt.includes('không thành công') || 
                   tt.includes('lỗi');
    return !isDone;
  });

  if (pendingRows.length === 0) return; // Không có dòng nào cần xử lý

  if (autoClsCountdownTimer) return; // Đang đếm ngược rồi

  // Đếm ngược 3 giây rồi tự chạy
  autoClsCountdown = 3;
  if (autoClsModeText) autoClsModeText.textContent = `Tự Động: chạy sau ${autoClsCountdown}s...`;
  showSnackbar(`🤖 Phát hiện ${pendingRows.length} hợp đồng Clear Cls chưa cập nhật - Tự khởi động sau 3 giây...`);

  autoClsCountdownTimer = setInterval(() => {
    autoClsCountdown--;
    if (autoClsCountdown > 0) {
      if (autoClsModeText) autoClsModeText.textContent = `Tự Động: chạy sau ${autoClsCountdown}s...`;
    } else {
      clearInterval(autoClsCountdownTimer);
      autoClsCountdownTimer = null;
      if (autoClsModeText) autoClsModeText.textContent = 'Tự Động: BẬT';

      if (!autoClsMode || isClsRunning || isBypassRunning) return;
      const stillPending = currentClsRecords.filter(r => {
        const kq = String(r['Kết Quả'] || r['Kết Quả'] || '').trim().toLowerCase();
        const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
        const isDone = kq === 'đã xử lý' || 
                       tt === 'đã clear' || 
                       tt.includes('cập nhật thành công') || 
                       (tt.includes('thành công') && !tt.includes('không')) || 
                       tt.includes('không thành công') || 
                       tt.includes('lỗi');
        return !isDone;
      });

      if (stillPending.length > 0) {
        showSnackbar(`🚀 Tự động khởi động Clear Cls cho ${stillPending.length} hợp đồng...`);
        runClsProcess(stillPending);
      }
    }
  }, 1000);
}

async function loadClsSheetData() {
  if (!tbodyClsList) return;
  if (tbodyClsList.children.length === 0 || (tbodyClsList.children.length === 1 && tbodyClsList.children[0].textContent.includes('Đang tải'))) {
    tbodyClsList.innerHTML = '<tr><td colspan="10" class="text-center py-8 text-slate-400"><span>⏳ Đang tải dữ liệu từ Google Sheet (GID: 987552880)...</span></td></tr>';
  }

  try {
    const res = await fetch(`/api/cls/sheet-data?gid=987552880&_t=${Date.now()}`);
    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      currentClsRecords = data.records || [];
      updateClsStats(currentClsRecords);
      if (!isClsRunning) {
        renderClsTable(currentClsRecords);
      }
      if (autoClsMode && !isClsRunning && !isBypassRunning && !autoClsCountdownTimer) {
        checkAndAutoTriggerCls();
      }
    } else {
      tbodyClsList.innerHTML = `<tr><td colspan="10" class="text-center py-6 text-rose-500 font-medium">❌ ${escapeHtml(data.message || 'Không thể đọc dữ liệu từ Google Sheet')}</td></tr>`;
    }
  } catch (e) {
    tbodyClsList.innerHTML = '<tr><td colspan="10" class="text-center py-6 text-rose-500 font-medium">❌ Lỗi kết nối khi tải Google Sheet</td></tr>';
  }
}

function updateClsStats(records) {
  const total = records.length;
  let pending = 0;
  let done = 0;
  let error = 0;

  records.forEach(r => {
    const kq = String(r['Kết Quả'] || r['Kết Quả'] || '').trim().toLowerCase();
    const tt = String(r['Thao Tác'] || '').trim().toLowerCase();

    const hasFinalError = tt.includes('không thành công') || tt.includes('lỗi');
    const hasFinalSuccess = tt === 'đã clear' || 
                            tt.includes('cập nhật thành công') || 
                            (tt.includes('thành công') && !tt.includes('không')) || 
                            (kq === 'đã xử lý' && tt && !tt.includes('chưa'));

    if (hasFinalError) {
      error++;
    } else if (hasFinalSuccess) {
      done++;
    } else {
      pending++;
    }
  });

  if (clsStatTotal) clsStatTotal.textContent = total;
  if (clsStatPending) clsStatPending.textContent = pending;
  if (clsStatDone) clsStatDone.textContent = done;
  if (clsStatError) clsStatError.textContent = error;
  if (badgeClsPending) badgeClsPending.textContent = `${pending} chờ xử lý`;
}

function renderClsTable(records) {
  if (!tbodyClsList) return;

  const query = inputSearchCls ? inputSearchCls.value.trim().toLowerCase() : '';
  const statusFilter = selectClsFilterStatus ? selectClsFilterStatus.value : 'all';
  const reasonFilter = selectClsFilterReason ? selectClsFilterReason.value : 'all';

  let filtered = records.filter(r => {
    const shd = String(r['SHD'] || '').toLowerCase();
    const email = String(r['Email'] || '').toLowerCase();
    const tacVu = String(r['Tác Vụ'] || r['Tác Vụ'] || '').toLowerCase();
    const nn1 = String(r['Nguyên Nhân 1'] || '').toLowerCase();
    const kq = String(r['Kết Quả'] || r['Kết Quả'] || '').toLowerCase();
    const tt = String(r['Thao Tác'] || '').toLowerCase();

    // Search match
    if (query && !shd.includes(query) && !email.includes(query) && !tacVu.includes(query) && !nn1.includes(query)) {
      return false;
    }

    // Reason filter
    if (reasonFilter !== 'all') {
      if (!nn1.includes(reasonFilter.toLowerCase())) return false;
    }

    // Status filter
    const isDone = (tt === 'đã clear' || tt.includes('cập nhật thành công') || (tt.includes('thành công') && !tt.includes('không')) || tt.includes('không thành công') || tt.includes('lỗi')) || (kq === 'đã xử lý' && tt && !tt.includes('chưa'));
    if (statusFilter === 'pending') {
      return !isDone;
    } else if (statusFilter === 'done') {
      return isDone && !tt.includes('không thành công') && !tt.includes('lỗi');
    } else if (statusFilter === 'error') {
      return tt.includes('không thành công') || tt.includes('lỗi');
    }

    return true;
  });

  if (filtered.length === 0) {
    tbodyClsList.innerHTML = '<tr><td colspan="10" class="text-center py-8 text-slate-400">Không có bản ghi nào phù hợp với bộ lọc</td></tr>';
    if (clsTableFooterText) clsTableFooterText.textContent = 'Hiển thị 0 bản ghi';
    return;
  }

  tbodyClsList.innerHTML = '';
  filtered.forEach((r, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50 transition-colors';

    const tacVu = r['Tác Vụ'] || r['Tác Vụ'] || 'Clear Cls có SR';
    const shd = String(r['SHD'] || '').trim();
    const email = r['Email'] || '';
    const msnv = r['MSNV'] || '';
    const nn1 = r['Nguyên Nhân 1'] || 'KH không có nhu cầu bảo trì';
    const ngay = r['Ngày Cập Nhật'] || r['Ngày Cập Nhật'] || '';
    const kq = String(r['Kết Quả'] || r['Kết Quả'] || '').trim();
    const tt = String(r['Thao Tác'] || '').trim();

    const isChecked = selectedClsShds.has(shd) || (!selectedClsShds.size && (kq.toLowerCase() !== 'đã xử lý' && !tt.toLowerCase().includes('thành công') && tt.toLowerCase() !== 'đã clear' && !tt.toLowerCase().includes('không thành công')));

    // Badge Kết Quả
    let badgeKq = '<span class="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600">Chưa xử lý</span>';
    if (kq.toLowerCase() === 'đã xử lý' || tt.toLowerCase() === 'đã clear' || tt.toLowerCase().includes('thành công') || tt.toLowerCase().includes('không thành công')) {
      badgeKq = '<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">✓ Đã xử lý</span>';
    }

    // Badge Thao Tác
    let badgeTt = '<span class="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600">Chưa xử lý</span>';
    const ttLower = tt.toLowerCase();
    if (ttLower.includes('cập nhật thành công') || (ttLower.includes('thành công') && !ttLower.includes('không')) || ttLower === 'đã clear' || ttLower === 'đã xử lý') {
      badgeTt = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">✓ ${escapeHtml(tt || 'Cập nhật thành công!')}</span>`;
    } else if (ttLower.includes('không thành công') || ttLower.includes('lỗi')) {
      badgeTt = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200" title="${escapeHtml(tt)}">✕ ${escapeHtml(tt)}</span>`;
    } else if (tt) {
      badgeTt = `<span class="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">${escapeHtml(tt)}</span>`;
    }

    tr.innerHTML = `
      <td class="p-3 text-center">
        <input type="checkbox" class="cls-row-checkbox rounded text-indigo-600" data-shd="${escapeHtml(shd)}" ${isChecked ? 'checked' : ''}>
      </td>
      <td class="p-3 text-center text-slate-500 font-mono">${idx + 1}</td>
      <td class="p-3 font-medium text-slate-700">${escapeHtml(tacVu)}</td>
      <td class="p-3"><strong class="font-mono text-indigo-700 text-xs">${escapeHtml(shd)}</strong></td>
      <td class="p-3 font-mono text-[11px] text-slate-600">${escapeHtml(email)}</td>
      <td class="p-3"><span class="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-800 text-[11px] font-medium">${escapeHtml(nn1)}</span></td>
      <td class="p-3 font-mono text-[11px] text-slate-500">${escapeHtml(ngay)}</td>
      <td class="p-3 text-center">${badgeKq}</td>
      <td class="p-3">${badgeTt}</td>
      <td class="p-3 text-center">
        <button type="button" class="btn-run-single-cls px-2 py-1 rounded-lg text-[11px] font-semibold bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition-colors" data-shd="${escapeHtml(shd)}" title="Chạy Clear Cls chỉ cho HĐ này">
          ▶ Chạy
        </button>
      </td>
    `;

    tbodyClsList.appendChild(tr);
  });

  if (clsTableFooterText) {
    clsTableFooterText.textContent = `Hiển thị ${filtered.length}/${records.length} bản ghi`;
  }
  updateClsSelectedCount();

  // Attach single run click
  tbodyClsList.querySelectorAll('.btn-run-single-cls').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const shd = e.currentTarget.dataset.shd;
      const target = currentClsRecords.find(r => String(r['SHD'] || '').trim() === shd);
      if (target) {
        runClsProcess([target]);
      }
    });
  });

  // Checkbox changes
  tbodyClsList.querySelectorAll('.cls-row-checkbox').forEach(chk => {
    chk.addEventListener('change', (e) => {
      const shd = e.target.dataset.shd;
      if (e.target.checked) selectedClsShds.add(shd);
      else selectedClsShds.delete(shd);
      updateClsSelectedCount();
    });
  });
}

function updateClsSelectedCount() {
  const checked = tbodyClsList ? tbodyClsList.querySelectorAll('.cls-row-checkbox:checked').length : 0;
  if (clsSelectedCountText) {
    clsSelectedCountText.textContent = `(${checked} HĐ đã chọn)`;
  }
}

if (chkClsSelectAll) {
  chkClsSelectAll.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    if (tbodyClsList) {
      tbodyClsList.querySelectorAll('.cls-row-checkbox').forEach(chk => {
        chk.checked = isChecked;
        const shd = chk.dataset.shd;
        if (isChecked) selectedClsShds.add(shd);
        else selectedClsShds.delete(shd);
      });
    }
    updateClsSelectedCount();
  });
}

if (inputSearchCls) inputSearchCls.addEventListener('input', () => renderClsTable(currentClsRecords));
if (selectClsFilterStatus) selectClsFilterStatus.addEventListener('change', () => renderClsTable(currentClsRecords));
if (selectClsFilterReason) selectClsFilterReason.addEventListener('change', () => renderClsTable(currentClsRecords));
if (btnRefreshClsSheetData) {
  btnRefreshClsSheetData.addEventListener('click', () => {
    showSnackbar('Đang làm mới dữ liệu từ Google Sheet (GID: 987552880)...');
    loadClsSheetData();
  });
}

async function runClsProcess(specificRecords = null) {
  if (isClsRunning) {
    showSnackbar('Đang có tiến trình Clear Cls đang chạy...');
    return;
  }

  let recordsToRun = specificRecords;
  if (!recordsToRun) {
    const checkedShds = new Set();
    if (tbodyClsList) {
      tbodyClsList.querySelectorAll('.cls-row-checkbox:checked').forEach(c => checkedShds.add(c.dataset.shd));
    }
    if (checkedShds.size > 0) {
      recordsToRun = currentClsRecords.filter(r => checkedShds.has(String(r['SHD'] || '').trim()));
    }
  }

  try {
    setClsRunningState(true);
    const isVisible = chkClsVisible ? chkClsVisible.checked : false;
    const isHeadless = !isVisible;
    const res = await fetch('/api/cls/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        headless: isHeadless,
        records: recordsToRun
      })
    });

    const data = await res.json();
    if (res.ok && data.status === 'started') {
      const modeDesc = isHeadless ? 'chạy ngầm' : 'đang mở Chrome trực tiếp trên màn hình';
      showSnackbar(`🚀 Đã khởi động Auto Clear Cls cho ${data.count} hợp đồng (${modeDesc})!`);
    } else {
      setClsRunningState(false);
      showSnackbar(data.message || 'Không thể bắt đầu Clear Cls');
    }
  } catch (err) {
    setClsRunningState(false);
    showSnackbar(`Lỗi kết nối máy chủ: ${err}`);
  }
}

function setClsRunningState(running) {
  isClsRunning = running;
  if (btnRunAutoCls) btnRunAutoCls.disabled = running;
  if (clsSpinner) clsSpinner.style.display = running ? 'inline-block' : 'none';
  if (clsRunIcon) clsRunIcon.style.display = running ? 'none' : 'inline-block';
  if (clsRunText) clsRunText.textContent = running ? 'Đang Xử Lý Clear Cls...' : 'Bắt Đầu Auto Clear Cls';
  if (clsProgressTracker) clsProgressTracker.style.display = running ? 'block' : 'none';
}

async function pollClsStatus() {
  try {
    const res = await fetch('/api/cls/live-status');
    if (!res.ok) return;
    const data = await res.json();
    const task = data.task || {};

    if (task.is_running) {
      setClsRunningState(true);
      const cur = task.current_index || 0;
      const total = task.total || 1;
      const percent = Math.min(100, Math.round((cur / Math.max(1, total)) * 100));

      if (clsTrackerPercent) clsTrackerPercent.textContent = `${percent}%`;
      if (clsProgressBar) clsProgressBar.style.width = `${percent}%`;
      if (clsTrackerStatus) {
        clsTrackerStatus.textContent = task.message || `Đang xử lý ${cur}/${total}: ${task.current_shd || ''}`;
      }
    } else {
      if (isClsRunning) {
        setClsRunningState(false);
        showSnackbar('✅ Tiến trình Auto Clear Cls đã hoàn thành!');
        loadClsSheetData();
        // Nếu có ByPass đang chờ, kiểm tra kích hoạt ngay
        if (autoBypassMode && !isBypassRunning && !autoBypassCountdownTimer) {
          setTimeout(checkAndAutoTriggerBypass, 1000);
        }
      }
    }
  } catch (e) {}
}

if (btnRunAutoCls) {
  btnRunAutoCls.addEventListener('click', () => runClsProcess());
}

// Live Terminal Logs Rendering cho Clear Cls
function renderClsTerminalLogs(logs) {
  if (!clsLogTerminal) return;
  if (!logs || logs.length === 0) return;

  const relevant = logs.filter(l => {
    const txt = (l.text || '').toLowerCase();
    return txt.includes('clear cls') || txt.includes('cls') || txt.includes('đăng nhập') || txt.includes('phiên') || txt.includes('inside');
  });
  const displayLogs = (relevant.length > 0 ? relevant : logs).slice(-40);
  clsLogTerminal.innerHTML = '';
  displayLogs.forEach(l => {
    const item = document.createElement('div');
    item.className = 'py-0.5 leading-relaxed';
    let colorClass = 'text-slate-300';
    if (l.level === 'success') colorClass = 'text-emerald-400 font-medium';
    else if (l.level === 'warning') colorClass = 'text-amber-400';
    else if (l.level === 'error') colorClass = 'text-rose-400 font-semibold';
    else if (l.level === 'info') colorClass = 'text-indigo-300';

    item.innerHTML = `
      <span class="text-slate-500 font-mono text-[10px] select-none">[${escapeHtml(l.time)}]</span>
      <span class="${colorClass}">${escapeHtml(l.text)}</span>
    `;
    clsLogTerminal.appendChild(item);
  });
  clsLogTerminal.scrollTop = clsLogTerminal.scrollHeight;
}

if (btnClearClsLogs && clsLogTerminal) {
  btnClearClsLogs.addEventListener('click', () => {
    clsLogTerminal.innerHTML = '<div class="text-slate-500 italic">Nhật ký Clear Cls đã được làm sạch</div>';
  });
}

// Xuất data xử lý Clear Cls ra Excel
if (btnExportClsData) {
  btnExportClsData.addEventListener('click', () => {
    showSnackbar('Đang chuẩn bị file Excel xuất dữ liệu Clear Cls...');
    window.location.href = `/api/cls/export?gid=987552880&status=all`;
  });
}

registerTab('tab-clear-cls', {
  title: 'Auto Clear Cls có SR',
  onActivate() {
    if (currentClsRecords.length > 0 && !isClsRunning) renderClsTable(currentClsRecords);
    loadClsSheetData();
  }
});
