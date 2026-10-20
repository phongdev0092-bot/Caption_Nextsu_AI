// ==========================================================
// COMPONENT: SETTINGS, DUAL ACCOUNT & LIVE OTP
// ==========================================================

// ----------------- DUAL-ACCOUNT SETTINGS & LIVE OTP -----------------
const headerAccPill = document.getElementById('headerAccPill');
const headerAccName = document.getElementById('headerAccName');
const btnTabAccDefault = document.getElementById('btnTabAccDefault');
const btnTabAccCustom = document.getElementById('btnTabAccCustom');
const accContentDefault = document.getElementById('accContentDefault');
const accContentCustom = document.getElementById('accContentCustom');
const radioChooseDefault = document.getElementById('radioChooseDefault');
const radioChooseCustom = document.getElementById('radioChooseCustom');
const defaultOtpCode = document.getElementById('defaultOtpCode');
const defaultOtpTimer = document.getElementById('defaultOtpTimer');
const defaultOtpFill = document.getElementById('defaultOtpFill');
const btnCopyDefaultOtp = document.getElementById('btnCopyDefaultOtp');

// Custom Account Form Elements
const customUsername = document.getElementById('customUsername');
const customPassword = document.getElementById('customPassword');
const btnToggleCustomPwd = document.getElementById('btnToggleCustomPwd');
const customUseOtp = document.getElementById('customUseOtp');
const customOtpBox = document.getElementById('customOtpBox');
const customSecret = document.getElementById('customSecret');
const customQrFile = document.getElementById('customQrFile');
const customOtpCode = document.getElementById('customOtpCode');
const customOtpTimer = document.getElementById('customOtpTimer');
const customOtpFill = document.getElementById('customOtpFill');
const btnCopyCustomOtp = document.getElementById('btnCopyCustomOtp');

if (headerAccPill) {
  headerAccPill.addEventListener('click', () => {
    settingsModalBackdrop.classList.add('open');
    loadModalConfig();
  });
}

btnOpenSettings.addEventListener('click', () => {
  settingsModalBackdrop.classList.add('open');
  loadModalConfig();
});

function closeModal() { settingsModalBackdrop.classList.remove('open'); }
btnCloseSettings.addEventListener('click', closeModal);
btnCancelSettings.addEventListener('click', closeModal);
settingsModalBackdrop.addEventListener('click', (e) => {
  if (e.target === settingsModalBackdrop) closeModal();
});

// Account Tab Switching in Modal
function switchAccountTab(mode) {
  if (mode === 'default') {
    btnTabAccDefault.classList.add('active');
    btnTabAccCustom.classList.remove('active');
    btnTabAccDefault.querySelector('.acc-tab-radio').textContent = '●';
    btnTabAccCustom.querySelector('.acc-tab-radio').textContent = '○';
    accContentDefault.style.display = 'block';
    accContentCustom.style.display = 'none';
  } else {
    btnTabAccCustom.classList.add('active');
    btnTabAccDefault.classList.remove('active');
    btnTabAccCustom.querySelector('.acc-tab-radio').textContent = '●';
    btnTabAccDefault.querySelector('.acc-tab-radio').textContent = '○';
    accContentCustom.style.display = 'block';
    accContentDefault.style.display = 'none';
  }
}

btnTabAccDefault.addEventListener('click', () => switchAccountTab('default'));
btnTabAccCustom.addEventListener('click', () => switchAccountTab('custom'));

// Toggle Custom OTP Box
customUseOtp.addEventListener('change', () => {
  customOtpBox.style.display = customUseOtp.checked ? 'block' : 'none';
});

async function loadModalConfig() {
  try {
    const res = await fetch('/api/config');
    if (res.ok) {
      const cfg = await res.json();
      const active = cfg.active_account || 'default';
      if (active === 'default') {
        radioChooseDefault.checked = true;
        switchAccountTab('default');
      } else {
        radioChooseCustom.checked = true;
        switchAccountTab('custom');
      }

      // Fill custom account fields
      const custom = cfg.custom_account || {};
      customUsername.value = custom.username || '';
      customPassword.value = custom.password || '';
      customUseOtp.checked = !!custom.use_otp;
      customOtpBox.style.display = custom.use_otp ? 'block' : 'none';
      // Update header badge
      updateHeaderAccountBadge(cfg);

      // Sync webhook input
      const hookUrl = cfg.google_sheet_webhook_url || '';
      const inputHook = document.getElementById('inputSheetWebhookUrl');
      const badgeHook = document.getElementById('webhookStatusBadge');
      if (inputHook) inputHook.value = hookUrl;
      if (badgeHook) {
        if (hookUrl) {
          badgeHook.textContent = '✓ Đã kết nối Webhook';
          badgeHook.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200';
        } else {
          badgeHook.textContent = 'Chưa kết nối Webhook';
          badgeHook.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200';
        }
      }

      // Sync Clear Cls webhook input
      const clsHookUrl = cfg.cls_webhook_url || '';
      const inputClsHook = document.getElementById('inputClsWebhookUrl');
      const badgeClsHook = document.getElementById('clsWebhookStatusBadge');
      if (inputClsHook) inputClsHook.value = clsHookUrl;
      if (badgeClsHook) {
        if (clsHookUrl) {
          badgeClsHook.textContent = '✓ Đã kết nối Webhook Clear Cls';
          badgeClsHook.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-800 border border-emerald-200';
        } else {
          badgeClsHook.textContent = 'Chưa kết nối Webhook';
          badgeClsHook.className = 'text-[10px] px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200';
        }
      }
    }
  } catch (err) {}
}

function updateHeaderAccountBadge(cfg) {
  if (!headerAccName) return;
  const mode = cfg.active_account || 'default';
  let text = 'Mặc định';
  if (mode === 'default') {
    text = 'Mặc định';
  } else {
    const uname = (cfg.custom_account && cfg.custom_account.username) || 'Tùy chỉnh';
    text = `Tùy chỉnh (${uname})`;
  }
  headerAccName.textContent = text;
  if (sidebarAccName) sidebarAccName.textContent = text;
}

btnSaveSettings.addEventListener('click', async () => {
  const active = radioChooseCustom.checked ? 'custom' : 'default';
  const payload = {
    active_account: active,
    custom_account: {
      username: customUsername.value.trim(),
      password: customPassword.value.trim(),
      use_otp: customUseOtp.checked,
      totp_secret: customSecret.value.trim()
    }
  };
  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const updated = await res.json();
      updateHeaderAccountBadge(updated);
      showSnackbar(`Đã lưu cấu hình! Tài khoản kích hoạt: [${active === 'default' ? 'Mặc định' : 'Tùy chỉnh'}]`);
      closeModal();
    }
  } catch (err) {
    showSnackbar('Lỗi khi lưu cài đặt');
  }
});

btnToggleCustomPwd.addEventListener('click', () => {
  if (customPassword.type === 'password') {
    customPassword.type = 'text';
    btnToggleCustomPwd.textContent = '🙈';
  } else {
    customPassword.type = 'password';
    btnToggleCustomPwd.textContent = '👁';
  }
});

if (btnCopyDefaultOtp) {
  btnCopyDefaultOtp.addEventListener('click', async () => {
    const code = defaultOtpCode ? defaultOtpCode.textContent : '';
    if (code && code !== '------') {
      await navigator.clipboard.writeText(code);
      showSnackbar(`Đã sao chép mã OTP mặc định [${code}]`);
    }
  });
}

btnCopyCustomOtp.addEventListener('click', async () => {
  const code = customOtpCode.textContent;
  if (code && code !== '------') {
    await navigator.clipboard.writeText(code);
    showSnackbar(`Đã sao chép mã OTP tùy chỉnh [${code}]`);
  }
});

customQrFile.addEventListener('change', async () => {
  if (customQrFile.files.length > 0) {
    showSnackbar('Đang quét mã QR cho tài khoản tùy chỉnh...');
    const fd = new FormData();
    fd.append('file', customQrFile.files[0]);
    fd.append('target', 'custom');
    try {
      const res = await fetch('/api/scan-qr', { method: 'POST', body: fd });
      const d = await res.json();
      if (res.ok) {
        customSecret.value = d.secret;
        customUseOtp.checked = true;
        customOtpBox.style.display = 'block';
        showSnackbar(`Đã quét QR thành công: ${d.secret}`);
        fetchLiveOtps();
      } else {
        showSnackbar(d.message || 'Lỗi đọc mã QR');
      }
    } catch (err) {
      showSnackbar('Lỗi tải ảnh lên');
    }
  }
});

async function fetchLiveOtps() {
  // 1. Fetch Default OTP
  try {
    const res = await fetch('/api/otp?target=default');
    if (res.ok) {
      const d = await res.json();
      if (defaultOtpCode) defaultOtpCode.textContent = d.code;
      if (defaultOtpTimer) defaultOtpTimer.textContent = `Đổi sau ${d.remaining}s`;
      if (defaultOtpFill) defaultOtpFill.style.width = `${(d.remaining / 30) * 100}%`;
    }
  } catch (e) {}

  // 2. Fetch Custom OTP if secret exists
  const sec = customSecret ? customSecret.value.trim() : '';
  if (sec && customUseOtp && customUseOtp.checked) {
    try {
      const res = await fetch(`/api/otp?secret=${encodeURIComponent(sec)}`);
      if (res.ok) {
        const d = await res.json();
        if (customOtpCode) customOtpCode.textContent = d.code;
        if (customOtpTimer) customOtpTimer.textContent = `Đổi sau ${d.remaining}s`;
        if (customOtpFill) customOtpFill.style.width = `${(d.remaining / 30) * 100}%`;
      }
    } catch (e) {}
  } else if (customOtpCode) {
    customOtpCode.textContent = '------';
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}
