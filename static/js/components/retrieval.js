// ==========================================================
// COMPONENT: AUTO LẤY THÔNG TIN (tab-retrieval)
// ==========================================================

// ----------------- RETRIEVAL MODE SWITCHING -----------------
modeSingle.addEventListener('change', () => {
  singleInputWrap.style.display = 'flex';
  fileInputWrap.style.display = 'none';
  updateCurrentContracts();
});

modeFile.addEventListener('change', () => {
  singleInputWrap.style.display = 'none';
  fileInputWrap.style.display = 'flex';
});

singleContractInput.addEventListener('input', () => {
  updateCurrentContracts();
});

function updateCurrentContracts() {
  if (modeSingle.checked) {
    const val = singleContractInput.value.trim();
    currentContracts = val ? [val] : [];
  }
  renderContractTags();
}

function renderContractTags() {
  contractTags.innerHTML = '';
  if (currentContracts.length === 0) {
    contractTags.innerHTML = `<span style="color:#80868b; font-style:italic;">Chưa có số hợp đồng nào</span>`;
    return;
  }
  currentContracts.slice(0, 8).forEach(c => {
    const tag = document.createElement('span');
    tag.className = 'contract-tag';
    tag.textContent = c;
    contractTags.appendChild(tag);
  });
  if (currentContracts.length > 8) {
    const more = document.createElement('span');
    more.className = 'contract-tag';
    more.textContent = `+${currentContracts.length - 8} HĐ khác`;
    contractTags.appendChild(more);
  }
}

// Handle Contract File Upload
contractFileInput.addEventListener('change', async () => {
  if (!contractFileInput.files.length) return;
  const file = contractFileInput.files[0];
  contractFileLabel.textContent = `Đang phân tích: ${file.name}...`;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/retrieval/upload-file', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      currentContracts = data.contracts || [];
      contractFileLabel.textContent = `File: ${file.name} (${currentContracts.length} HĐ)`;
      renderContractTags();
      showSnackbar(`Đã đọc ${currentContracts.length} số hợp đồng từ file!`);
    } else {
      showSnackbar(data.message || 'Lỗi đọc file hợp đồng');
      contractFileLabel.textContent = 'Chọn hoặc kéo file .xlsx, .txt vào đây...';
    }
  } catch (err) {
    showSnackbar('Lỗi kết nối khi tải file');
    contractFileLabel.textContent = 'Chọn hoặc kéo file .xlsx, .txt vào đây...';
  }
});

// ----------------- AUTO LẤY THÔNG TIN (EXECUTION) -----------------
btnAutoFetch.addEventListener('click', async () => {
  if (isRetrieving) return;

  if (currentContracts.length === 0) {
    showSnackbar('Vui lòng nhập hoặc chọn ít nhất 1 số hợp đồng!');
    return;
  }

  isRetrieving = true;
  btnAutoFetch.disabled = true;
  fetchSpinner.style.display = 'inline-block';
  fetchRocketIcon.style.display = 'none';
  fetchBtnText.textContent = 'Đang lấy thông tin...';
  processTracker.style.display = 'flex';
  trackerPercent.textContent = '0%';
  trackerFill.style.width = '0%';
  trackerStatusText.textContent = `Bắt đầu xử lý ${currentContracts.length} hợp đồng...`;

  showSnackbar(`Bắt đầu tự động lấy dữ liệu ${currentContracts.length} hợp đồng...`);

  try {
    const res = await fetch('/api/retrieval/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contracts: currentContracts })
    });
    const data = await res.json();
    if (!res.ok) {
      showSnackbar(data.message || 'Lỗi khởi chạy tiến trình');
      resetFetchButton();
    }
  } catch (err) {
    showSnackbar('Lỗi kết nối máy chủ');
    resetFetchButton();
  }
});

function resetFetchButton() {
  isRetrieving = false;
  btnAutoFetch.disabled = false;
  fetchSpinner.style.display = 'none';
  fetchRocketIcon.style.display = 'inline-block';
  fetchBtnText.textContent = 'Auto Lấy Thông Tin';
}

// ----------------- LOAD & RENDER TABLE -----------------
function formatDateDataDisplay(r) {
  const raw = r.timestamp || '';
  if (!raw) return '-';
  if (raw.length >= 10 && raw[4] === '-' && raw[7] === '-') {
    const parts = raw.split(' ');
    const dParts = parts[0].split('-');
    const dStr = `${dParts[2]}/${dParts[1]}/${dParts[0]}`;
    const tStr = parts[1] ? parts[1].slice(0, 5) : '';
    return tStr ? `${dStr} ${tStr}` : dStr;
  }
  return raw;
}

async function loadRetrievalData() {
  const q = encodeURIComponent(retrievalSearchInput.value.trim());
  const st = encodeURIComponent(retrievalStatusSelect.value);
  const from = retrievalDateFrom ? encodeURIComponent(retrievalDateFrom.value.trim()) : '';
  const to = retrievalDateTo ? encodeURIComponent(retrievalDateTo.value.trim()) : '';

  try {
    const res = await fetch(`/api/retrieval/list?q=${q}&status=${st}&from=${from}&to=${to}`);
    if (res.ok) {
      const data = await res.json();
      currentRecords = data.records || [];
      renderRetrievalTable(currentRecords);
      updateStorageInfo();

      // Cập nhật huy hiệu số bản ghi được lọc
      const isFiltered = (q || (st && st !== 'all') || from || to);
      if (filterCountBadge) {
        if (isFiltered) {
          filterCountBadge.textContent = `Đang lọc: ${currentRecords.length} / ${data.total_unfiltered || currentRecords.length} HĐ`;
          filterCountBadge.classList.remove('hidden');
        } else {
          filterCountBadge.classList.add('hidden');
        }
      }

      // Cập nhật text nút Export
      if (btnExportExcelText) {
        if (from || to) {
          btnExportExcelText.textContent = `Xuất Excel (${currentRecords.length} HĐ)`;
        } else {
          btnExportExcelText.textContent = `Xuất Excel (Tất cả)`;
        }
      }

      // Update progress if task running
      const task = data.task || {};
      if (task.is_running) {
        isRetrieving = true;
        btnAutoFetch.disabled = true;
        fetchSpinner.style.display = 'inline-block';
        fetchRocketIcon.style.display = 'none';
        fetchBtnText.textContent = 'Đang lấy thông tin...';
        processTracker.style.display = 'flex';
        trackerStatusText.textContent = task.message || 'Đang xử lý...';

        const pct = task.total > 0 ? Math.round((task.current_index / task.total) * 100) : 0;
        trackerPercent.textContent = `${pct}%`;
        trackerFill.style.width = `${pct}%`;
      } else if (isRetrieving) {
        resetFetchButton();
        trackerPercent.textContent = '100%';
        trackerFill.style.width = '100%';
        trackerStatusText.textContent = task.message || 'Hoàn tất!';
        showSnackbar('Đã hoàn tất tiến trình lấy thông tin hợp đồng!');
      }
    }
  } catch (err) {}
}

function renderRetrievalTable(records) {
  retrievalTableBody.innerHTML = '';
  if (records.length === 0) {
    retrievalTableBody.innerHTML = `<tr><td colspan="16" style="text-align:center; padding: 32px; color: #80868b;">Chưa có dữ liệu phù hợp với bộ lọc. Bấm <strong>Auto Lấy Thông Tin</strong> hoặc chọn lại ngày để xem.</td></tr>`;
    return;
  }

  records.forEach((r, idx) => {
    const tr = document.createElement('tr');
    const isSuccess = r.status === 'Thành công';
    const badgeCls = isSuccess ? 'success' : 'error';
    const statusText = isSuccess ? 'Thành công' : (r.error || 'No data');
    const formattedDateData = formatDateDataDisplay(r);

    tr.innerHTML = `
      <td style="color:#80868b; font-weight:500;">${idx + 1}</td>
      <td><strong style="color:#1a73e8; font-family:var(--font-mono);">${escapeHtml(r.contract_no)}</strong></td>
      <td><strong>${escapeHtml(r.customer_name || '-')}</strong></td>
      <td style="font-family:var(--font-mono);">${escapeHtml(r.customer_phone || '-')}</td>
      <td><span style="font-weight:600; color:#1a73e8;">${escapeHtml(r.service_type || '-')}</span></td>
      <td>${escapeHtml(r.contract_status || '-')}</td>
      <td title="${escapeHtml(r.address)}">${escapeHtml(r.address || '-')}</td>
      <td title="${escapeHtml(r.service_package)}">${escapeHtml(r.service_package || '-')}</td>
      <td title="${escapeHtml(r.materials)}">${escapeHtml(r.materials || '-')}</td>
      <td>${escapeHtml(r.deploy_type || '-')}</td>
      <td>${escapeHtml(r.sales || '-')}</td>
      <td style="font-family:var(--font-mono); font-size:0.78rem;">${escapeHtml(r.tech_params || '-')}</td>
      <td style="color:#5f6368;">${escapeHtml(r.created_date || '-')}</td>
      <td style="white-space:nowrap;"><span class="date-data-badge" title="Thời gian cào Inside FPT: ${escapeHtml(r.timestamp || '')}">📅 ${escapeHtml(formattedDateData)}</span></td>
      <td><span class="badge-status ${badgeCls}">${escapeHtml(statusText)}</span></td>
      <td style="text-align:center;">
        <button type="button" class="btn-row-action" data-idx="${idx}">Chi tiết</button>
      </td>
    `;
    retrievalTableBody.appendChild(tr);
  });

  // Attach click events for detail button
  document.querySelectorAll('.btn-row-action').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const i = parseInt(e.target.dataset.idx, 10);
      if (records[i]) {
        openDetailModal(records[i]);
      }
    });
  });
}

retrievalSearchInput.addEventListener('input', () => loadRetrievalData());
retrievalStatusSelect.addEventListener('change', () => loadRetrievalData());

if (retrievalDateFrom) retrievalDateFrom.addEventListener('change', () => loadRetrievalData());
if (retrievalDateTo) retrievalDateTo.addEventListener('change', () => loadRetrievalData());

if (btnFilterToday) {
  btnFilterToday.addEventListener('click', () => {
    const today = new Date().toISOString().slice(0, 10);
    if (retrievalDateFrom) retrievalDateFrom.value = today;
    if (retrievalDateTo) retrievalDateTo.value = today;
    showSnackbar(`Đã áp dụng lọc Date Data hôm nay (${today})`);
    loadRetrievalData();
  });
}

if (btnClearDateFilter) {
  btnClearDateFilter.addEventListener('click', () => {
    if (retrievalDateFrom) retrievalDateFrom.value = '';
    if (retrievalDateTo) retrievalDateTo.value = '';
    showSnackbar('Đã xóa bộ lọc ngày (Hiển thị tất cả dữ liệu)');
    loadRetrievalData();
  });
}

// Export Excel (Lọc theo ngày nếu có chọn, ngược lại xuất tất cả)
btnExportExcel.addEventListener('click', () => {
  if (currentRecords.length === 0) {
    showSnackbar('Không có dữ liệu phù hợp với bộ lọc để xuất Excel!');
    return;
  }
  const q = encodeURIComponent(retrievalSearchInput.value.trim());
  const st = encodeURIComponent(retrievalStatusSelect.value);
  const from = retrievalDateFrom ? encodeURIComponent(retrievalDateFrom.value.trim()) : '';
  const to = retrievalDateTo ? encodeURIComponent(retrievalDateTo.value.trim()) : '';

  const exportUrl = `/api/retrieval/export?q=${q}&status=${st}&from=${from}&to=${to}`;
  if (from || to) {
    const fromStr = from ? `từ ${from}` : '';
    const toStr = to ? `đến ${to}` : '';
    showSnackbar(`Đang xuất file Excel cho ${currentRecords.length} hợp đồng (${fromStr} ${toStr})...`);
  } else {
    showSnackbar(`Đang xuất toàn bộ ${currentRecords.length} hợp đồng ra file Excel...`);
  }
  window.location.href = exportUrl;
});

// Clear Table
btnClearTable.addEventListener('click', async () => {
  if (confirm('Bạn có chắc chắn muốn xóa toàn bộ bảng kết quả tra cứu này?')) {
    await fetch('/api/retrieval/clear', { method: 'POST' });
    showSnackbar('Đã xóa dữ liệu bảng thành công!');
    loadRetrievalData();
  }
});

// ----------------- DETAIL MODAL VIEW -----------------
function openDetailModal(record) {
  selectedDetailRecord = record;
  detailModalTitle.textContent = `Hợp đồng: ${record.contract_no}`;
  detailModalSub.textContent = `Trích xuất từ Inside FPT lúc ${record.timestamp || ''}`;

  detailModalBody.innerHTML = `
    <!-- Customer Info Section -->
    <div class="detail-grid-section">
      <div class="detail-section-title">👤 Thông Tin Khách Hàng</div>
      <div class="detail-item-row"><span class="detail-item-label">Họ tên khách hàng:</span><span class="detail-item-val">${escapeHtml(record.customer_name || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">SĐT chính chủ:</span><span class="detail-item-val" style="font-family:var(--font-mono);">${escapeHtml(record.customer_phone || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">Loại dịch vụ:</span><span class="detail-item-val" style="color:#1a73e8; font-weight:700;">${escapeHtml(record.service_type || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">Tình trạng HĐ:</span><span class="detail-item-val">${escapeHtml(record.contract_status || '-')}</span></div>
    </div>

    <!-- PTC Info Section -->
    <div class="detail-grid-section">
      <div class="detail-section-title">🛠️ Thông Tin Phiếu Thi Công (PTC)</div>
      <div class="detail-item-row"><span class="detail-item-label">Địa chỉ triển khai:</span><span class="detail-item-val">${escapeHtml(record.address || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">Gói dịch vụ:</span><span class="detail-item-val">${escapeHtml(record.service_package || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">Vật tư triển khai:</span><span class="detail-item-val">${escapeHtml(record.materials || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">Loại triển khai:</span><span class="detail-item-val">${escapeHtml(record.deploy_type || '-')}</span></div>
    </div>

    <!-- Other Info Section -->
    <div class="detail-grid-section">
      <div class="detail-section-title">ℹ️ Thông Tin Bổ Sung</div>
      <div class="detail-item-row"><span class="detail-item-label">Nhân viên Sales:</span><span class="detail-item-val">${escapeHtml(record.sales || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">Thông số thi công:</span><span class="detail-item-val" style="font-family:var(--font-mono);">${escapeHtml(record.tech_params || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">Ngày tạo (PTC gần nhất):</span><span class="detail-item-val">${escapeHtml(record.created_date || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">Ngày lấy dữ liệu (Date Data):</span><span class="detail-item-val" style="font-family:var(--font-mono); color:#1e8e3e; font-weight:600;">${escapeHtml(record.timestamp || '-')}</span></div>
      <div class="detail-item-row"><span class="detail-item-label">Trạng thái:</span><span class="detail-item-val">${escapeHtml(record.status || '-')}</span></div>
    </div>
  `;

  detailModalBackdrop.classList.add('open');
}

function closeDetailModal() {
  detailModalBackdrop.classList.remove('open');
}

btnCloseDetailModal.addEventListener('click', closeDetailModal);
btnCloseDetailModal2.addEventListener('click', closeDetailModal);
detailModalBackdrop.addEventListener('click', (e) => {
  if (e.target === detailModalBackdrop) closeDetailModal();
});

btnCopyDetailModal.addEventListener('click', async () => {
  if (!selectedDetailRecord) return;
  const r = selectedDetailRecord;
  const formatted = `Số HĐ: ${r.contract_no}
Họ tên KH: ${r.customer_name}
SĐT: ${r.customer_phone}
Loại DV: ${r.service_type}
Địa chỉ: ${r.address}
Gói DV: ${r.service_package}
Vật tư: ${r.materials}
Sales: ${r.sales}
Ngày tạo: ${r.created_date}`;
  await navigator.clipboard.writeText(formatted);
  showSnackbar(`Đã sao chép thông tin HĐ ${r.contract_no}!`);
});
