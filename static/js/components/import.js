// ==========================================================
// COMPONENT: AUTO IMPORT (tab-import)
// ==========================================================

// ----------------- TAB 2: AUTO IMPORT -----------------
let selectedImportFile = null;
importDropzone.addEventListener('click', () => importFileInput.click());
importDropzone.addEventListener('dragover', (e) => { e.preventDefault(); importDropzone.classList.add('dragover'); });
importDropzone.addEventListener('dragleave', () => importDropzone.classList.remove('dragover'));
importDropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  importDropzone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) handlePickedImportFile(e.dataTransfer.files[0]);
});

importFileInput.addEventListener('change', () => {
  if (importFileInput.files.length > 0) handlePickedImportFile(importFileInput.files[0]);
});

function handlePickedImportFile(file) {
  selectedImportFile = file;
  btnExecuteImport.disabled = false;
  importDropzone.querySelector('.dropzone-primary-text').innerHTML = `Đã chọn file: <strong style="color:#1a73e8;">${escapeHtml(file.name)}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
  showSnackbar(`Đã tải file ${file.name}. Bấm "Tiến hành Auto Import" để thực thi.`);
}

btnExecuteImport.addEventListener('click', async () => {
  if (!selectedImportFile) return;
  btnExecuteImport.disabled = true;
  btnExecuteImport.innerHTML = `<span>⏳ Đang xử lý import...</span>`;
  showSnackbar('Đang tự động xác thực và đẩy dữ liệu lên Inside FPT...');

  const formData = new FormData();
  formData.append('file', selectedImportFile);

  try {
    const res = await fetch('/api/import/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (res.ok) {
      showSnackbar('Đã hoàn tất Auto Import thành công!');
      loadImportHistory();
      selectedImportFile = null;
      importDropzone.querySelector('.dropzone-primary-text').innerHTML = `Kéo thả file Excel vào đây hoặc <span class="link-btn">Duyệt file từ máy</span>`;
    } else {
      showSnackbar(data.message || 'Lỗi khi import file');
    }
  } catch (err) {
    showSnackbar('Lỗi kết nối khi gửi dữ liệu');
  } finally {
    btnExecuteImport.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
      </svg>
      <span>Tiến hành Auto Import</span>
    `;
    btnExecuteImport.disabled = !selectedImportFile;
  }
});

btnDownloadTemplate.addEventListener('click', () => {
  showSnackbar('Đang tải file Excel mẫu...');
});

async function loadImportHistory() {
  try {
    const res = await fetch('/api/import/history');
    if (res.ok) {
      const data = await res.json();
      renderImportHistory(data.history || []);
    }
  } catch (err) {}
}

function renderImportHistory(list) {
  importHistoryList.innerHTML = '';
  list.forEach(item => {
    const el = document.createElement('div');
    el.className = 'history-item';
    el.innerHTML = `
      <div>
        <div class="history-filename">📊 ${escapeHtml(item.filename)}</div>
        <div class="history-meta">Thời gian: ${item.date} • Thành công: <strong style="color:#1e8e3e;">${item.success}</strong> / ${item.total}</div>
      </div>
      <span class="badge-status ${item.failed === 0 ? 'success' : 'pending'}">${item.status}</span>
    `;
    importHistoryList.appendChild(el);
  });
}
