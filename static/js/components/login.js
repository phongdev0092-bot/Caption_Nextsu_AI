// ==========================================================
// COMPONENT: SINGLE LOGIN BUTTON & STATUS POLL
// ==========================================================

// ----------------- SINGLE LOGIN BUTTON (BACKGROUND) -----------------
function setLoginButtonState(state, user = '') {
  currentLoginState = state;
  btnSingleLogin.className = `mui-login-btn ${state}`;

  if (state === 'idle') {
    loginSpinner.style.display = 'none';
    loginIconKey.style.display = 'inline-block';
    loginIconCheck.style.display = 'none';
    loginLabel.textContent = 'Đăng Nhập';
    btnSingleLogin.disabled = false;
    bannerDot.className = 'banner-dot';
    bannerText.innerHTML = 'Hệ thống sẵn sàng. Nhập số hợp đồng bên dưới hoặc gán file để tự động lấy thông tin từ Inside FPT.';
  } else if (state === 'loading') {
    loginSpinner.style.display = 'inline-block';
    loginIconKey.style.display = 'none';
    loginIconCheck.style.display = 'none';
    loginLabel.textContent = 'Đang đăng nhập ngầm...';
    btnSingleLogin.disabled = true;
    bannerDot.className = 'banner-dot loading';
    bannerText.innerHTML = 'Đang chạy ngầm trình duyệt Chrome & xác thực mã Google Authenticator OTP...';
  } else if (state === 'success') {
    loginSpinner.style.display = 'none';
    loginIconKey.style.display = 'none';
    loginIconCheck.style.display = 'inline-block';
    loginLabel.textContent = '✓ Đã đăng nhập';
    btnSingleLogin.disabled = false;
    bannerDot.className = 'banner-dot online';
    bannerText.innerHTML = `Đã kết nối thành công tài khoản: <strong>${user || 'phuongnam.phongnh5'}</strong> (Inside FPT)`;
  }
}

btnSingleLogin.addEventListener('click', async () => {
  if (currentLoginState === 'loading') return;
  if (currentLoginState === 'success') {
    showSnackbar('Bạn đã đăng nhập thành công vào Inside FPT!');
    return;
  }

  setLoginButtonState('loading');
  showSnackbar('Đang tiến hành đăng nhập ngầm vào Inside FPT...');

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ headless: true, keep_browser_open: false })
    });
    const data = await res.json();
    if (!res.ok) {
      showSnackbar(data.message || 'Không thể bắt đầu đăng nhập');
      setLoginButtonState('idle');
    }
  } catch (err) {
    showSnackbar('Lỗi kết nối máy chủ');
    setLoginButtonState('idle');
  }
});

// Poll login status
async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    if (res.ok) {
      const data = await res.json();
      const task = data.task || {};
      if (task.status === 'running') {
        if (currentLoginState !== 'loading') setLoginButtonState('loading');
      } else if (task.status === 'success') {
        if (currentLoginState !== 'success') {
          setLoginButtonState('success', task.user);
        }
      } else if (task.status === 'error') {
        if (currentLoginState === 'loading') {
          setLoginButtonState('idle');
          showSnackbar(task.message || 'Đăng nhập không thành công');
        }
      }

      if (bypassSessionStatus) {
        if (task.status === 'success') {
          bypassSessionStatus.textContent = task.user ? `Đã đăng nhập (${task.user})` : 'Phiên hoạt động';
          bypassSessionStatus.className = 'text-sm font-bold text-emerald-600 mt-1';
        } else if (task.status === 'running') {
          bypassSessionStatus.textContent = 'Đang đăng nhập...';
          bypassSessionStatus.className = 'text-sm font-bold text-blue-600 mt-1';
        } else {
          bypassSessionStatus.textContent = 'Sẵn sàng kết nối';
          bypassSessionStatus.className = 'text-sm font-bold text-slate-700 mt-1';
        }
      }

      // Render live logs in terminals
      if (data.logs) {
        if (typeof renderBypassTerminalLogs === 'function') renderBypassTerminalLogs(data.logs);
        if (typeof renderClsTerminalLogs === 'function') renderClsTerminalLogs(data.logs);
        if (typeof renderAssignTerminalLogs === 'function') renderAssignTerminalLogs(data.logs);
        if (typeof renderClearSignalTerminalLogs === 'function') renderClearSignalTerminalLogs(data.logs);
        if (typeof renderResetSignalTerminalLogs === 'function') renderResetSignalTerminalLogs(data.logs);
      }
    }
  } catch (err) {}
}
