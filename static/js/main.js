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
pollStatus();
updateStorageInfo();
loadModalConfig();
updateAutoModeUI();
updateAutoClsModeUI();
updateAutoAssignModeUI();
updateAutoClearSignalModeUI();
updateAutoResetSignalModeUI();

// Polling intervals
setInterval(loadRetrievalData, 2000);
setInterval(pollStatus, 2500);
setInterval(fetchLiveOtps, 1000);
setInterval(pollBypassStatus, 2000);
setInterval(pollClsStatus, 2000);
setInterval(pollAssignStatus, 2000);
setInterval(pollClearSignalStatus, 2000);
setInterval(pollResetSignalStatus, 2000);
setInterval(() => {
  // Luôn refresh ByPass Sheet nếu đang ở Tab 3 HOẶC autoBypassMode đang BẬT
  if ((tabTasks && tabTasks.classList.contains('active')) || autoBypassMode) {
    if (!isBypassRunning) {
      loadBypassSheetData(currentBypassGid);
    }
  }
  // Luôn refresh Clear Cls Sheet nếu đang ở Tab 4 HOẶC autoClsMode đang BẬT
  if ((tabClearCls && tabClearCls.classList.contains('active')) || autoClsMode) {
    if (!isClsRunning) {
      loadClsSheetData();
    }
  }
  // Luôn refresh Assign Sheet nếu đang ở Tab 5 HOẶC autoAssignMode đang BẬT
  const tabAssign = document.getElementById('tab-manual-assign');
  if ((tabAssign && tabAssign.classList.contains('active')) || autoAssignMode) {
    if (!isAssignRunning) {
      loadAssignSheetData();
    }
  }
  // Luôn refresh Clear Signal Sheet nếu đang ở Tab Clear Signal HOẶC autoClearSignalMode đang BẬT
  const tabClearSig = document.getElementById('tab-clear-signal');
  if ((tabClearSig && tabClearSig.classList.contains('active')) || autoClearSignalMode) {
    if (!isClearSignalRunning) {
      loadClearSignalSheetData();
    }
  }
  // Luôn refresh Reset Signal Sheet nếu đang ở Tab Reset Signal HOẶC autoResetSignalMode đang BẬT
  const tabResetSig = document.getElementById('tab-reset-signal');
  if ((tabResetSig && tabResetSig.classList.contains('active')) || autoResetSignalMode) {
    if (!isResetSignalRunning) {
      loadResetSignalSheetData();
    }
  }

  // Kiểm tra và tự kích hoạt nếu auto mode ByPass đã bật
  if (autoBypassMode && !isBypassRunning && !isClsRunning && !autoBypassCountdownTimer) {
    checkAndAutoTriggerBypass();
  }
  // Kiểm tra và tự kích hoạt nếu auto mode Clear Cls đã bật
  if (autoClsMode && !isClsRunning && !isBypassRunning && !autoClsCountdownTimer) {
    checkAndAutoTriggerCls();
  }
  // Kiểm tra và tự kích hoạt nếu auto mode Phân Công Tay đã bật
  if (autoAssignMode && !isAssignRunning && !autoAssignCountdownTimer) {
    checkAndAutoTriggerAssign();
  }
  // Kiểm tra và tự kích hoạt nếu auto mode Clear Tín Hiệu đã bật
  if (autoClearSignalMode && !isClearSignalRunning && !autoClearSignalCountdownTimer) {
    checkAndAutoTriggerClearSignal();
  }
  // Kiểm tra và tự kích hoạt nếu auto mode Cấp Lại Tín Hiệu đã bật
  if (autoResetSignalMode && !isResetSignalRunning && !autoResetSignalCountdownTimer) {
    checkAndAutoTriggerResetSignal();
  }
}, 4000);

