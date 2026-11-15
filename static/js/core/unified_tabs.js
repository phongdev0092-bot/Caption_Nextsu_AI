// ==========================================================
// UNIFIED WORK TABS UI ENGINE (Caption Nextsu AI v4.0)
// Thống nhất giao diện MUI: KPI Cards, Charts, SpeedDial, Date Filter & SHD Search
// Tối ưu cho cả Web và Mobile
// ==========================================================

window.UnifiedWorkTabs = (function() {
  const chartInstances = {};

  // Parse date string (dd/mm/yyyy hh:mm:ss or yyyy-mm-dd hh:mm:ss or ISO)
  function parseRecordDate(dateStr) {
    if (!dateStr) return null;
    const s = String(dateStr).trim();
    if (!s) return null;

    // Pattern dd/mm/yyyy [hh:mm[:ss]]
    const m = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?/);
    if (m) {
      const d = parseInt(m[1], 10);
      const mo = parseInt(m[2], 10) - 1;
      const y = parseInt(m[3], 10);
      const hh = m[4] ? parseInt(m[4], 10) : 0;
      const mm = m[5] ? parseInt(m[5], 10) : 0;
      const ss = m[6] ? parseInt(m[6], 10) : 0;
      return new Date(y, mo, d, hh, mm, ss);
    }

    // Pattern yyyy-mm-dd [hh:mm[:ss]]
    const m2 = s.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?/);
    if (m2) {
      const y = parseInt(m2[1], 10);
      const mo = parseInt(m2[2], 10) - 1;
      const d = parseInt(m2[3], 10);
      const hh = m2[4] ? parseInt(m2[4], 10) : 0;
      const mm = m2[5] ? parseInt(m2[5], 10) : 0;
      const ss = m2[6] ? parseInt(m2[6], 10) : 0;
      return new Date(y, mo, d, hh, mm, ss);
    }

    const dObj = new Date(s);
    return isNaN(dObj.getTime()) ? null : dObj;
  }

  // Get epoch timestamp in ms for sorting from nearest to farthest
  function getRecordTimestamp(r) {
    if (!r) return 0;
    if (r.created_at_ts && typeof r.created_at_ts === 'number') {
      return r.created_at_ts > 1e11 ? r.created_at_ts : r.created_at_ts * 1000;
    }
    const dStr = r['Ngày Cập Nhật'] || r['Ngày cập nhật'] || r['Ngày Cập Nhật'] ||
                 r['Thời gian'] || r['timestamp'] || r['created_date'] || r['time'] || '';
    const d = parseRecordDate(dStr);
    return d ? d.getTime() : 0;
  }

  function getRecordNumericId(r) {
    if (!r) return 0;
    const raw = r['ID'] !== undefined ? r['ID'] : (r['id'] !== undefined ? r['id'] : '');
    const n = parseInt(String(raw).trim(), 10);
    return Number.isFinite(n) ? n : 0;
  }

  function isPendingSheetRow(r) {
    if (!r || typeof r !== 'object') return false;
    const hasSheetCols = (
      'Thao Tác' in r || 'Thao tác' in r ||
      'Kết Quả' in r || 'Kết quả' in r || 'Kết Quả' in r
    );
    if (!hasSheetCols) return false;
    return !isRecordDone(r) && !isRecordError(r);
  }

  // Sort records: pending sheet requests first, then newest-to-oldest by timestamp / ID / sheet bottom order
  function sortRecordsNewestFirst(records) {
    if (!Array.isArray(records)) return [];
    return records
      .map((r, idx) => ({ r, idx }))
      .sort((a, b) => {
        const pendA = isPendingSheetRow(a.r) ? 0 : 1;
        const pendB = isPendingSheetRow(b.r) ? 0 : 1;
        if (pendA !== pendB) return pendA - pendB;

        const tA = getRecordTimestamp(a.r);
        const tB = getRecordTimestamp(b.r);
        if (tB !== tA) return tB - tA;

        const idA = getRecordNumericId(a.r);
        const idB = getRecordNumericId(b.r);
        if (idB !== idA) return idB - idA;

        // Google Sheet appends new rows at the bottom -> higher original index appears first
        return b.idx - a.idx;
      })
      .map(item => item.r);
  }

  // Paginate an array (default 10 items per page)
  function paginate(records, page = 1, pageSize = 10) {
    const list = Array.isArray(records) ? records : [];
    const total = list.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const currentPage = Math.min(Math.max(1, parseInt(page, 10) || 1), totalPages);
    const startIdx = total === 0 ? 0 : (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, total);
    const items = list.slice(startIdx, endIdx);
    return {
      items,
      currentPage,
      totalPages,
      total,
      startIdx,
      endIdx,
      pageSize
    };
  }

  // Render unified pagination bar
  function renderPagination(container, state, onPageChange) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el) return;
    if (!state || state.total === 0) {
      el.innerHTML = '';
      return;
    }

    const { currentPage, totalPages, total, startIdx, endIdx } = state;
    if (totalPages <= 1) {
      el.innerHTML = `
        <div class="flex items-center justify-between flex-wrap gap-2 pt-2.5 text-xs text-slate-500 border-t border-slate-100">
          <span>Hiển thị <strong class="text-slate-800">${startIdx + 1} - ${endIdx}</strong> / <strong class="text-slate-800">${total}</strong> HĐ</span>
          <span class="text-[11.5px] text-slate-400 font-medium">Trang 1 / 1 (10 dòng/trang)</span>
        </div>
      `;
      return;
    }

    let pageNumbers = [];
    if (totalPages <= 7) {
      for (let p = 1; p <= totalPages; p++) pageNumbers.push(p);
    } else {
      pageNumbers.push(1);
      if (currentPage > 3) pageNumbers.push('...');
      const startP = Math.max(2, currentPage - 1);
      const endP = Math.min(totalPages - 1, currentPage + 1);
      for (let p = startP; p <= endP; p++) pageNumbers.push(p);
      if (currentPage < totalPages - 2) pageNumbers.push('...');
      pageNumbers.push(totalPages);
    }

    let pagesHtml = pageNumbers.map(p => {
      if (p === '...') {
        return `<span class="px-1.5 text-slate-400 select-none">…</span>`;
      }
      const isActive = p === currentPage;
      const cls = isActive
        ? 'w-7 h-7 rounded-lg bg-blue-600 text-white font-bold text-xs shadow-xs'
        : 'w-7 h-7 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-medium cursor-pointer';
      return `<button type="button" class="pg-num-btn ${cls}" data-page="${p}">${p}</button>`;
    }).join('');

    el.innerHTML = `
      <div class="flex items-center justify-between flex-wrap gap-2 pt-2.5 text-xs text-slate-600 border-t border-slate-100">
        <div class="text-[12px] text-slate-500">
          Hiển thị <strong class="text-slate-800">${startIdx + 1} - ${endIdx}</strong> / <strong class="text-slate-800">${total}</strong> HĐ
          <span class="text-slate-400 text-[11px] ml-1">(Trang ${currentPage}/${totalPages} • 10 dòng/trang)</span>
        </div>
        <div class="flex items-center gap-1" role="navigation" aria-label="Phân trang bảng dữ liệu">
          <button type="button" class="pg-btn pg-first px-2 h-7 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs text-slate-600 font-medium disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer" data-page="1" ${currentPage === 1 ? 'disabled' : ''} title="Trang đầu" aria-label="Trang đầu">«</button>
          <button type="button" class="pg-btn pg-prev px-2.5 h-7 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs text-slate-600 font-medium disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer" data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''} title="Trang trước" aria-label="Trang trước">‹ Trước</button>
          <div class="flex items-center gap-1 mx-0.5">
            ${pagesHtml}
          </div>
          <button type="button" class="pg-btn pg-next px-2.5 h-7 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs text-slate-600 font-medium disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer" data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''} title="Trang sau" aria-label="Trang sau">Sau ›</button>
          <button type="button" class="pg-btn pg-last px-2 h-7 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs text-slate-600 font-medium disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer" data-page="${totalPages}" ${currentPage === totalPages ? 'disabled' : ''} title="Trang cuối" aria-label="Trang cuối">»</button>
        </div>
      </div>
    `;

    el.querySelectorAll('button[data-page]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const p = parseInt(e.currentTarget.getAttribute('data-page'), 10);
        if (!isNaN(p) && p >= 1 && p <= totalPages && p !== currentPage) {
          if (typeof onPageChange === 'function') onPageChange(p);
        }
      });
    });
  }

  // Check if date falls in selected range
  function isDateInRange(recordDate, rangeType) {
    if (!rangeType || rangeType === 'all') return true;
    if (!recordDate) return true;

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const rDay = new Date(recordDate.getFullYear(), recordDate.getMonth(), recordDate.getDate());

    if (rangeType === 'today') {
      return rDay.getTime() === today.getTime();
    }
    if (rangeType === '7days') {
      const past7 = new Date(today);
      past7.setDate(past7.getDate() - 7);
      return rDay >= past7 && rDay <= today;
    }
    if (rangeType === '30days') {
      const past30 = new Date(today);
      past30.setDate(past30.getDate() - 30);
      return rDay >= past30 && rDay <= today;
    }
    return true;
  }

  // Check if record failed / rejected
  function isRecordError(r) {
    if (!r) return false;
    const tt = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
    const kq = String(r['Kết Quả'] || r['Kết quả'] || r['Kết Quả'] || '').trim().toLowerCase();
    return (
      tt.includes('không thành công') || tt.includes('lỗi') || tt.includes('thất bại') ||
      tt.includes('vi phạm') || tt.includes('từ chối') || tt.includes('error') ||
      kq.includes('không thành công') || kq.includes('lỗi') || kq.includes('thất bại') || kq.includes('error')
    );
  }

  // Check if record is Success / Done
  function isRecordDone(r) {
    if (!r) return false;
    const tt = String(r['Thao Tác'] || r['Thao tác'] || '').trim().toLowerCase();
    const kq = String(r['Kết Quả'] || r['Kết quả'] || r['Kết Quả'] || '').trim().toLowerCase();
    if (tt === 'chưa cập nhật' || tt === 'chưa xử lý' || tt === 'nan') {
      return false;
    }
    if (tt && isRecordError(r)) {
      return false;
    }
    if (tt) {
      return (
        (tt.includes('thành công') && !tt.includes('không thành công')) ||
        tt.includes('đã xử lý') ||
        tt.includes('đã clear') ||
        tt.includes('đã phân công') ||
        tt.includes('hoàn tất') ||
        tt.includes('spampool')
      );
    }
    if (kq === 'chưa cập nhật' || kq === 'chưa xử lý' || kq === 'nan' || !kq) {
      return false;
    }
    if (isRecordError(r)) {
      return false;
    }
    return (
      kq.includes('đã xử lý') ||
      (kq.includes('thành công') && !kq.includes('không thành công')) ||
      kq.includes('đã clear') ||
      kq.includes('đã cấp') ||
      kq.includes('hoàn tất')
    );
  }

  // Get staff identifier
  function getStaff(r) {
    const possible = ['Email NVKT', 'Email', 'Account Inside', 'MSNV', 'Người Tạo', 'User'];
    for (const k of possible) {
      if (r[k] && String(r[k]).trim()) {
        let v = String(r[k]).trim();
        if (v.includes('@')) v = v.split('@')[0];
        return v;
      }
    }
    return 'Chưa rõ';
  }

  // Filter records by Date, SHD query, and Result status
  function filterRecords(records, options = {}) {
    if (!Array.isArray(records)) return [];
    
    let dateRange = 'today';
    let shdQuery = '';
    let resultStatus = 'all';

    if (typeof options === 'string') {
      dateRange = options || 'today';
    } else if (typeof options === 'object' && options !== null) {
      dateRange = options.dateRange !== undefined ? options.dateRange : 'today';
      shdQuery = options.shdQuery || '';
      resultStatus = options.resultStatus || 'all';
    }

    const query = (shdQuery || '').trim().toLowerCase();

    const filtered = records.filter(r => {
      const isPending = !isRecordDone(r) && !isRecordError(r);

      // 1. Date filter (luôn giữ lại các dòng đang chờ xử lý để yêu cầu mới/tồn đọng không bị ẩn)
      if (dateRange && dateRange !== 'all' && !isPending) {
        const dStr = r['Ngày Cập Nhật'] || r['Ngày cập nhật'] || r['Ngày Cập Nhật'] || r['Thời gian'] || '';
        const dObj = parseRecordDate(dStr);
        if (dObj && !isDateInRange(dObj, dateRange)) {
          return false;
        }
      }

      // 2. SHD / Email / Staff Search
      if (query) {
        const shd = String(r['SHD'] || r['Số Hợp Đồng'] || r['Số hợp đồng'] || '').toLowerCase();
        const email = String(r['Email NVKT'] || r['Email'] || r['Nhân viên kỹ thuật'] || '').toLowerCase();
        const msnv = String(r['MSNV'] || '').toLowerCase();
        const acc = String(r['Account Inside'] || r['Account'] || '').toLowerCase();
        if (!shd.includes(query) && !email.includes(query) && !msnv.includes(query) && !acc.includes(query)) {
          return false;
        }
      }

      // 3. Result status filter
      if (resultStatus === 'done') {
        if (!isRecordDone(r)) return false;
      } else if (resultStatus === 'pending') {
        if (!isPending) return false;
      }

      // 4. Hậu kiểm filter
      if (options && typeof options === 'object' && options.hauKiemFilter && options.hauKiemFilter !== 'all') {
        const hk = String(r['Hậu kiểm'] || r['Hậu Kiểm'] || '').trim().toUpperCase();
        if (options.hauKiemFilter === 'pass' && hk !== 'ĐẠT') return false;
        if (options.hauKiemFilter === 'fail' && hk !== 'KHÔNG ĐẠT') return false;
      }

      return true;
    });

    return sortRecordsNewestFirst(filtered);
  }

  // Render or Update Chart.js Daily Volume Bar Chart
  function updateDailyChart(canvasId, records, dateRange = 'all') {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    // Filter by date range if provided
    let targetRecords = records;
    if (dateRange && dateRange !== 'all') {
      targetRecords = filterRecords(records, dateRange);
    }

    // Group counts by Day (last 7 or active days)
    const dayMap = {};
    const now = new Date();

    // Default init last 5-7 days
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const key = `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
      dayMap[key] = { done: 0, pending: 0 };
    }

    targetRecords.forEach(r => {
      const dStr = r['Ngày Cập Nhật'] || r['Ngày cập nhật'] || '';
      const dObj = parseRecordDate(dStr);
      if (dObj) {
        const key = `${String(dObj.getDate()).padStart(2, '0')}/${String(dObj.getMonth() + 1).padStart(2, '0')}`;
        if (!dayMap[key]) {
          dayMap[key] = { done: 0, pending: 0 };
        }
        if (isRecordDone(r)) {
          dayMap[key].done++;
        } else {
          dayMap[key].pending++;
        }
      }
    });

    const labels = Object.keys(dayMap);
    const doneData = labels.map(k => dayMap[k].done);
    const pendingData = labels.map(k => dayMap[k].pending);

    if (chartInstances[canvasId]) {
      try {
        chartInstances[canvasId].destroy();
      } catch (e) {}
    }

    try {
      const ctx = canvas.getContext('2d');
      chartInstances[canvasId] = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Đã Xử Lý Thành Công',
              data: doneData,
              backgroundColor: '#10b981',
              borderRadius: 6,
              borderSkipped: false,
            },
            {
              label: 'Chờ Xử Lý',
              data: pendingData,
              backgroundColor: '#f59e0b',
              borderRadius: 6,
              borderSkipped: false,
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false
          },
          plugins: {
            legend: {
              position: 'top',
              labels: {
                boxWidth: 12,
                boxHeight: 12,
                usePointStyle: true,
                pointStyle: 'rectRounded',
                padding: 14,
                font: { size: 12, weight: '600', family: "'Google Sans', Roboto, sans-serif" }
              }
            },
            tooltip: {
              backgroundColor: '#0f172a',
              padding: 11,
              cornerRadius: 8,
              titleFont: { size: 12, weight: '700' },
              bodyFont: { size: 12 },
              footerFont: { size: 11, weight: '600' },
              callbacks: {
                title: function(items) {
                  return items && items.length ? `Ngày: ${items[0].label}` : '';
                },
                label: function(ctx) {
                  const val = ctx.parsed.y || 0;
                  return ` ${ctx.dataset.label}: ${val} HĐ`;
                },
                footer: function(items) {
                  if (!items || !items.length) return '';
                  const sum = items.reduce((acc, it) => acc + (it.parsed.y || 0), 0);
                  return `Tổng trong ngày: ${sum} HĐ`;
                }
              }
            }
          },
          scales: {
            x: {
              stacked: true,
              grid: { display: false },
              title: {
                display: true,
                text: 'Ngày cập nhật (DD/MM)',
                color: '#64748b',
                font: { size: 11, weight: '600' }
              },
              ticks: { font: { size: 11, weight: '500' }, color: '#475569' }
            },
            y: {
              stacked: true,
              beginAtZero: true,
              title: {
                display: true,
                text: 'Số lượng HĐ',
                color: '#64748b',
                font: { size: 11, weight: '600' }
              },
              ticks: {
                precision: 0,
                font: { size: 11 },
                color: '#475569'
              },
              grid: { color: '#e2e8f0' }
            }
          }
        }
      });
    } catch (chartErr) {
      // Ignore hidden canvas or detached context errors
    }
  }

  // Render TOP 5 Staff List
  function updateTopStaff(containerId, records, dateRange = 'all') {
    const container = document.getElementById(containerId);
    if (!container) return;

    let targetRecords = records;
    if (dateRange && dateRange !== 'all') {
      targetRecords = filterRecords(records, dateRange);
    }

    const staffMap = {};
    targetRecords.forEach(r => {
      const s = getStaff(r);
      if (s && s !== 'Chưa rõ') {
        staffMap[s] = (staffMap[s] || 0) + 1;
      }
    });

    const sorted = Object.entries(staffMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    if (sorted.length === 0) {
      container.innerHTML = `
        <div class="h-full min-h-[140px] flex flex-col items-center justify-center p-4 text-center text-slate-400 text-xs">
          <span class="text-2xl mb-1">👥</span>
          <span>Chưa có dữ liệu nhân sự</span>
        </div>
      `;
      return;
    }

    const maxCount = sorted[0][1] || 1;
    const rankColors = [
      { bg: 'bg-amber-500' },
      { bg: 'bg-slate-400' },
      { bg: 'bg-amber-700' },
      { bg: 'bg-blue-500' },
      { bg: 'bg-indigo-500' }
    ];

    let html = '';
    sorted.forEach(([staff, count], idx) => {
      const pct = Math.round((count / maxCount) * 100);
      const c = rankColors[idx] || rankColors[3];
      html += `
        <div class="p-2 rounded-xl bg-slate-50 hover:bg-slate-100/80 transition-all flex items-center gap-2.5">
          <div class="w-6 h-6 rounded-full ${c.bg} text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">
            ${idx + 1}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between text-xs mb-1">
              <span class="font-semibold text-slate-800 truncate" title="${staff}">${staff}</span>
              <span class="font-bold text-slate-900 ml-2 font-mono">${count} HĐ</span>
            </div>
            <div class="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div class="h-full bg-blue-600 rounded-full transition-all duration-500" style="width: ${pct}%;"></div>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  // Setup speed dial hover and click toggle for mobile
  function initSpeedDials() {
    document.querySelectorAll('.speed-dial-trigger').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const menu = btn.parentElement.querySelector('.speed-dial-menu');
        if (menu) {
          menu.classList.toggle('opacity-0');
          menu.classList.toggle('invisible');
        }
      });
    });

    document.addEventListener('click', () => {
      document.querySelectorAll('.speed-dial-menu').forEach(menu => {
        menu.classList.add('opacity-0');
        menu.classList.add('invisible');
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initSpeedDials();
  });

  return {
    parseRecordDate,
    getRecordTimestamp,
    sortRecordsNewestFirst,
    paginate,
    renderPagination,
    isDateInRange,
    isRecordDone,
    isRecordError,
    getStaff,
    filterRecords,
    updateDailyChart,
    updateTopStaff,
    initSpeedDials
  };
})();
