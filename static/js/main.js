// ==========================================================
// MAIN: KHỞI TẠO & POLLING (nạp cuối cùng)
// ==========================================================

// Initial runs
updateCurrentContracts();
loadRetrievalData();
loadImportHistory();
loadBypassSheetData('0');
loadClsSheetData();
loadAssignSheetData();
loadClearSignalSheetData();
loadResetSignalSheetData();
loadMyBaeSheetData();
loadSpamPoolSheetData();
loadBypassNatSheetData();
loadPortSheetData();
pollStatus();
updateStorageInfo();
loadModalConfig();
updateAutoModeUI();
updateAutoClsModeUI();
updateAutoAssignModeUI();
updateAutoClearSignalModeUI();
updateAutoResetSignalModeUI();
updateAutoMyBaeModeUI();
updateAutoSpamPoolModeUI();
updateAutoBypassNatModeUI();
updateAutoPortModeUI();

// Global Pending Notification Badges & Cross-tab Awareness
let previousPendingCounts = {
  bypass: 0,
  cls: 0,
  assign: 0,
  clearSignal: 0,
  resetSignal: 0,
  mybae: 0,
  spampool: 0,
  bypassNat: 0,
  port: 0
};
let isInitialBadgeCheck = true;

function updateBadgeElement(elId, count) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (count > 0) {
    el.textContent = count;
    el.classList.remove('hidden');
  } else {
    el.classList.add('hidden');
  }
}

function updateGlobalPendingBadges() {
  // Lưu ý: let ở classic script KHÔNG đính vào window → phải truy cập trực tiếp tên biến
  const _bypassRecs  = (typeof currentBypassRecords  !== 'undefined' ? currentBypassRecords  : []);
  const _clsRecs     = (typeof currentClsRecords     !== 'undefined' ? currentClsRecords     : []);
  const _assignRecs  = (typeof currentAssignRecords  !== 'undefined' ? currentAssignRecords  : []);
  const _csigRecs    = (typeof currentClearSignalRecords !== 'undefined' ? currentClearSignalRecords : []);
  const _rsigRecs    = (typeof currentResetSignalRecords !== 'undefined' ? currentResetSignalRecords : []);
  const _mybaeRecs   = (typeof currentMyBaeRecords   !== 'undefined' ? currentMyBaeRecords   : []);
  const _spamRecs    = (typeof currentSpamPoolRecords !== 'undefined' ? currentSpamPoolRecords : []);
  const _natRecs     = (typeof currentBypassNatRecords !== 'undefined' ? currentBypassNatRecords : []);
  const _portRecs    = (typeof currentPortRecords !== 'undefined' ? currentPortRecords : []);

  const bypassPending = _bypassRecs.filter(r => {
    const st = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
    return st !== 'đã xử lý';
  }).length;

  const clsPending = _clsRecs.filter(r => {
    const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
    const kq = String(r['Kết Quả'] || '').trim().toLowerCase();
    return !tt.includes('thành công') && !kq.includes('đã xử lý');
  }).length;

  const assignPending = _assignRecs.filter(r => {
    return typeof _isAssignAutoPending === 'function' ? _isAssignAutoPending(r) : false;
  }).length;

  const clearSignalPending = _csigRecs.filter(r => {
    return typeof _isClearSignalFinalDone === 'function' ? !_isClearSignalFinalDone(r) : false;
  }).length;

  const resetSignalPending = _rsigRecs.filter(r => {
    return typeof _isResetSignalFinalDone === 'function' ? !_isResetSignalFinalDone(r) : false;
  }).length;

  const mybaePending = _mybaeRecs.filter(r => {
    return typeof _mybaeIsPending === 'function' ? _mybaeIsPending(r) : false;
  }).length;

  const spampoolPending = _spamRecs.filter(r => {
    const kq = String(r['Kết Quả'] || '').trim().toLowerCase();
    const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
    return !kq.includes('đã xử lý') && !tt.includes('đã xử lý') && !tt.includes('thành công');
  }).length;

  const bypassNatPending = _natRecs.filter(r => {
    const kq = String(r['Kết Quả'] || '').trim().toLowerCase();
    const tt = String(r['Thao Tác'] || '').trim().toLowerCase();
    return !kq.includes('đã xử lý') && !tt.includes('đã xử lý') && !tt.includes('thành công');
  }).length;

  const portPending = _portRecs.filter(r => {
    const kq = String(r['Ngày Cập Nhật'] || r['Ngày cập nhật'] || '').trim().toLowerCase();
    const tt = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
    if (typeof isPendingPortRow === 'function') {
      return isPendingPortRow(kq, tt);
    }
    return kq === 'chưa cập nhật' || tt === 'chưa cập nhật' || tt === 'chưa xử lý' || !kq || !tt;
  }).length;

  // Cập nhật badges sidebar
  updateBadgeElement('navPendingBadgeBypass', bypassPending);
  updateBadgeElement('navPendingBadgeCls', clsPending);
  updateBadgeElement('navPendingBadgeAssign', assignPending);
  updateBadgeElement('navPendingBadgeClearSignal', clearSignalPending);
  updateBadgeElement('navPendingBadgeResetSignal', resetSignalPending);
  updateBadgeElement('navPendingBadgeMyBae', mybaePending);
  updateBadgeElement('navPendingBadgeSpamPool', spampoolPending);
  updateBadgeElement('navPendingBadgeBypassNat', bypassNatPending);
  updateBadgeElement('navPendingBadgePort', portPending);

  // Cập nhật Title trình duyệt để người dùng nhìn thấy số lượng chờ xử lý ngay cả khi ở tab khác / thu nhỏ cửa sổ
  const totalPending = bypassPending + clsPending + assignPending + clearSignalPending + resetSignalPending + mybaePending + spampoolPending + bypassNatPending + portPending;
  if (totalPending > 0) {
    document.title = `(${totalPending}) Caption Nextsu AI - FPT Automation`;
  } else {
    document.title = 'Caption Nextsu AI - FPT Data Retrieval Tool';
  }

  // Phát hiện hợp đồng mới xuất hiện ở tab khác và thông báo nổi bật cho người dùng
  if (!isInitialBadgeCheck) {
    if (bypassPending > previousPendingCounts.bypass) {
      showSnackbar(`🔔 [Auto Bypass] Phát hiện ${bypassPending} hợp đồng đang chờ xử lý!`);
    }
    if (clsPending > previousPendingCounts.cls) {
      showSnackbar(`🔔 [Clear Cls] Phát hiện ${clsPending} hợp đồng đang chờ xử lý!`);
    }
    if (assignPending > previousPendingCounts.assign) {
      showSnackbar(`🔔 [Phân Công Tay] Phát hiện ${assignPending} hợp đồng đang chờ xử lý!`);
    }
    if (clearSignalPending > previousPendingCounts.clearSignal) {
      showSnackbar(`🔔 [Clear Tín Hiệu] Phát hiện ${clearSignalPending} hợp đồng đang chờ xử lý!`);
    }
    if (resetSignalPending > previousPendingCounts.resetSignal) {
      showSnackbar(`🔔 [Cấp Lại Tín Hiệu] Phát hiện ${resetSignalPending} hợp đồng đang chờ xử lý!`);
    }
    if (mybaePending > previousPendingCounts.mybae) {
      showSnackbar(`🔔 [Bypass MyBAE] Phát hiện ${mybaePending} hợp đồng đang chờ xử lý!`);
    }
    if (spampoolPending > previousPendingCounts.spampool) {
      showSnackbar(`🔔 [SpamPool] Phát hiện ${spampoolPending} hợp đồng đang chờ xử lý!`);
    }
    if (bypassNatPending > previousPendingCounts.bypassNat) {
      showSnackbar(`🔔 [Bypass NAT] Phát hiện ${bypassNatPending} hợp đồng đang chờ xử lý!`);
    }
    if (portPending > previousPendingCounts.port) {
      showSnackbar(`🔔 [Cấp/Thu Hồi Port] Phát hiện ${portPending} hợp đồng đang chờ xử lý!`);
    }
  }

  previousPendingCounts = {
    bypass: bypassPending,
    cls: clsPending,
    assign: assignPending,
    clearSignal: clearSignalPending,
    resetSignal: resetSignalPending,
    mybae: mybaePending,
    spampool: spampoolPending,
    bypassNat: bypassNatPending,
    port: portPending
  };
  isInitialBadgeCheck = false;
}

// Initial badge update
setTimeout(updateGlobalPendingBadges, 1500);

// Polling intervals
setInterval(loadRetrievalData, 2000);
setInterval(pollStatus, 2000);
setInterval(fetchLiveOtps, 1000);

const _TASK_POLLERS = [
  { tabId: 'tab-tasks',         isRunning: () => typeof isBypassRunning !== 'undefined' && isBypassRunning,           poll: () => typeof pollBypassStatus === 'function' && pollBypassStatus() },
  { tabId: 'tab-clear-cls',     isRunning: () => typeof isClsRunning !== 'undefined' && isClsRunning,                 poll: () => typeof pollClsStatus === 'function' && pollClsStatus() },
  { tabId: 'tab-manual-assign', isRunning: () => typeof isAssignRunning !== 'undefined' && isAssignRunning,           poll: () => typeof pollAssignStatus === 'function' && pollAssignStatus() },
  { tabId: 'tab-clear-signal',  isRunning: () => typeof isClearSignalRunning !== 'undefined' && isClearSignalRunning, poll: () => typeof pollClearSignalStatus === 'function' && pollClearSignalStatus() },
  { tabId: 'tab-reset-signal',  isRunning: () => typeof isResetSignalRunning !== 'undefined' && isResetSignalRunning, poll: () => typeof pollResetSignalStatus === 'function' && pollResetSignalStatus() },
  { tabId: 'tab-bypass-mybae',  isRunning: () => typeof isMyBaeRunning !== 'undefined' && isMyBaeRunning,             poll: () => typeof pollMyBaeStatus === 'function' && pollMyBaeStatus() },
  { tabId: 'tab-spampool',      isRunning: () => typeof isSpamPoolRunning !== 'undefined' && isSpamPoolRunning,       poll: () => typeof pollSpamPoolStatus === 'function' && pollSpamPoolStatus() },
  { tabId: 'tab-bypass-nat',    isRunning: () => typeof isBypassNatRunning !== 'undefined' && isBypassNatRunning,     poll: () => typeof pollBypassNatStatus === 'function' && pollBypassNatStatus() },
  { tabId: 'tab-port',          isRunning: () => typeof isPortRunning !== 'undefined' && isPortRunning,               poll: () => typeof pollPortStatus === 'function' && pollPortStatus() }
];

let _statusPollTick = 0;
setInterval(() => {
  _statusPollTick = (_statusPollTick + 1) % 3;
  const pollIdleNow = (_statusPollTick === 0); // Tab nền rảnh: 6000ms; tab đang mở hoặc đang chạy: 2000ms
  _TASK_POLLERS.forEach(item => {
    const el = document.getElementById(item.tabId);
    const isActive = !!(el && el.classList.contains('active'));
    if (isActive || item.isRunning() || pollIdleNow) {
      try {
        item.poll();
      } catch (e) {}
    }
  });
}, 2000);

// Quét nền định kỳ liên tab
let bgPollCycle = 0;
setInterval(() => {
  const tabTasks = document.getElementById('tab-tasks');
  const tabClearCls = document.getElementById('tab-clear-cls');
  const tabAssign = document.getElementById('tab-manual-assign');
  const tabClearSig = document.getElementById('tab-clear-signal');
  const tabResetSig = document.getElementById('tab-reset-signal');
  const tabMyBae = document.getElementById('tab-bypass-mybae');
  const tabSpamPool = document.getElementById('tab-spampool');
  const tabBypassNat = document.getElementById('tab-bypass-nat');
  const tabPort = document.getElementById('tab-port');

  // Luôn làm mới tab người dùng đang xem
  if (tabTasks && tabTasks.classList.contains('active') && !isBypassRunning) loadBypassSheetData(currentBypassGid);
  else if (tabClearCls && tabClearCls.classList.contains('active') && !isClsRunning) loadClsSheetData();
  else if (tabAssign && tabAssign.classList.contains('active') && !isAssignRunning) loadAssignSheetData();
  else if (tabClearSig && tabClearSig.classList.contains('active') && !isClearSignalRunning) loadClearSignalSheetData();
  else if (tabResetSig && tabResetSig.classList.contains('active') && !isResetSignalRunning) loadResetSignalSheetData();
  else if (tabMyBae && tabMyBae.classList.contains('active') && !isMyBaeRunning) loadMyBaeSheetData();
  else if (tabSpamPool && tabSpamPool.classList.contains('active') && !isSpamPoolRunning) loadSpamPoolSheetData();
  else if (tabBypassNat && tabBypassNat.classList.contains('active') && !isBypassNatRunning) loadBypassNatSheetData();
  else if (tabPort && tabPort.classList.contains('active') && !isPortRunning) loadPortSheetData();

  // Luân phiên quét nền dữ liệu các tab khác để phát hiện hợp đồng mới
  bgPollCycle = (bgPollCycle + 1) % 8;
  if (bgPollCycle === 0 && !isBypassRunning) loadBypassSheetData(currentBypassGid);
  else if (bgPollCycle === 1 && !isClsRunning) loadClsSheetData();
  else if (bgPollCycle === 2 && !isAssignRunning) loadAssignSheetData();
  else if (bgPollCycle === 3 && !isClearSignalRunning && !isResetSignalRunning) {
    loadClearSignalSheetData();
    loadResetSignalSheetData();
  }
  else if (bgPollCycle === 4 && !isMyBaeRunning) loadMyBaeSheetData();
  else if (bgPollCycle === 5 && !isSpamPoolRunning) loadSpamPoolSheetData();
  else if (bgPollCycle === 6 && !isBypassNatRunning) loadBypassNatSheetData();
  else if (bgPollCycle === 7 && !isPortRunning) loadPortSheetData();

  // Cập nhật huy hiệu thông báo toàn hệ thống
  updateGlobalPendingBadges();

  // Đồng bộ trạng thái nút Tự Động lên server (chỉ điều phối duy nhất phía backend)
  fetch('/api/auto-modes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bypass: !!autoBypassMode, cls: !!autoClsMode, assign: !!autoAssignMode,
      clear_signal: !!autoClearSignalMode, reset_signal: !!autoResetSignalMode,
      mybae: !!autoMyBaeMode, spampool: !!autoSpamPoolMode,
      bypass_nat: !!autoBypassNatMode,
      port: !!autoPortMode
    })
  }).catch(() => {});
}, 3500);


