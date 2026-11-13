// ==========================================================
// AUTO MONITOR: Bảng theo dõi tổng quan Auto nền (nổi góc phải dưới)
// - Tổng số HĐ chờ xử lý toàn hệ thống + từng tab
// - Tiến trình đang chạy (tab, HĐ hiện tại, tiến độ)
// - Nhật ký gần nhất
// ==========================================================
(function () {
  const css = `
  #autoMon{position:fixed;right:18px;bottom:18px;z-index:9999;font-family:Inter,Segoe UI,sans-serif}
  #autoMonBtn{display:flex;align-items:center;gap:8px;padding:10px 16px;border-radius:999px;border:0;cursor:pointer;
    color:#fff;font-weight:700;font-size:13px;box-shadow:0 8px 24px rgba(15,23,42,.25);background:linear-gradient(135deg,#0ea5e9,#6366f1);transition:transform .15s}
  #autoMonBtn:hover{transform:translateY(-2px)}
  #autoMonBtn.busy{background:linear-gradient(135deg,#f59e0b,#ef4444)}
  #autoMonBtn .dot{width:9px;height:9px;border-radius:50%;background:#4ade80;box-shadow:0 0 0 0 rgba(74,222,128,.7);animation:amPulse 1.6s infinite}
  #autoMonBtn.busy .dot{background:#fff}
  @keyframes amPulse{70%{box-shadow:0 0 0 8px rgba(74,222,128,0)}100%{box-shadow:0 0 0 0 rgba(74,222,128,0)}}
  #autoMonPanel{display:none;position:absolute;right:0;bottom:52px;width:440px;max-height:78vh;overflow:hidden;border-radius:16px;
    background:rgba(255,255,255,.98);backdrop-filter:blur(10px);border:1px solid #e2e8f0;box-shadow:0 20px 50px rgba(15,23,42,.25);flex-direction:column}
  #autoMonPanel.open{display:flex}
  .am-head{padding:14px 16px;background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff}
  .am-head .big{font-size:24px;font-weight:800;line-height:1.1;display:flex;align-items:baseline;gap:8px}
  .am-head .big .today-num{color:#34d399}
  .am-head .big .sep{color:#64748b;font-weight:600;font-size:18px}
  .am-head .big .wait-num{color:#fbbf24}
  .am-head .sub{font-size:11px;color:#94a3b8;margin-top:4px}
  .am-run{margin:10px 12px 0;padding:10px 12px;border-radius:12px;font-size:12px}
  .am-run.on{background:#fff7ed;border:1px solid #fdba74;color:#9a3412}
  .am-run.off{background:#f0fdf4;border:1px solid #86efac;color:#166534}
  .am-bar{height:6px;border-radius:6px;background:#fed7aa;margin-top:6px;overflow:hidden}
  .am-bar i{display:block;height:100%;background:#f97316;transition:width .4s}
  .am-tabs{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:10px 12px}
  .am-tab{display:flex;justify-content:space-between;align-items:center;gap:6px;padding:7px 10px;border-radius:10px;background:#f8fafc;border:1px solid #e2e8f0;font-size:11.5px;color:#334155}
  .am-tab .am-counts{display:inline-flex;align-items:center;gap:4px;flex-shrink:0}
  .am-tab b{min-width:22px;text-align:center;padding:1px 6px;border-radius:999px;background:#e2e8f0;color:#475569;font-size:10.5px;font-weight:700}
  .am-tab b.today{background:#dcfce7;color:#15803d;border:1px solid #bbf7d0}
  .am-tab b.wait{background:#e2e8f0;color:#475569}
  .am-tab.has b.wait{background:#f59e0b;color:#fff}
  .am-tab.off{opacity:.5}
  .am-logs-head{display:flex;justify-content:space-between;align-items:center;padding:8px 14px 6px;border-top:1px solid #e2e8f0;background:#f8fafc}
  .am-logs{flex:1;overflow:auto;max-height:260px;min-height:160px;padding:6px 12px 10px;font-family:Consolas,monospace;font-size:11px;background:#0f172a;color:#cbd5e1}
  .am-logs div{padding:3px 0;border-bottom:1px dashed #1e293b}
  .am-logs .t{color:#64748b;margin-right:6px}
  .am-logs .error{color:#f87171}.am-logs .warning{color:#fbbf24}.am-logs .success{color:#34d399}.am-logs .info{color:#93c5fd}
  `;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  const root = document.createElement('div');
  root.id = 'autoMon';
  root.innerHTML = `
    <div id="autoMonPanel" role="dialog" aria-label="Theo dõi Auto nền">
      <div class="am-head">
        <div style="display:flex;justify-content:space-between;align-items:flex-end">
          <div>
            <div class="big">
              <span class="today-num" id="amToday">0 Today</span>
              <span class="sep">-</span>
              <span class="wait-num" id="amTotal">0 Chờ</span>
            </div>
            <div class="sub">Số lượng tác vụ xử lý ngày Today - Chờ (toàn hệ thống)</div>
          </div>
          <div class="sub" style="text-align:right">Quét mỗi <span id="amInterval">5</span>s<br>Lần quét cuối: <b id="amLast" style="color:#e2e8f0">--</b></div>
        </div>
      </div>
      <div class="am-run off" id="amRun">✅ Hệ thống đang rảnh</div>
      <div class="am-tabs" id="amTabs"></div>
      <div class="am-logs-head">
        <span style="font-weight:700;font-size:11px;color:#475569;text-transform:uppercase;letter-spacing:0.04em">📋 Nhật Ký Hoạt Động Auto</span>
        <button type="button" id="amClearLogsBtn" style="background:none;border:none;cursor:pointer;font-size:11px;color:#64748b;font-weight:600" title="Xóa màn hình nhật ký">🧹 Xóa</button>
      </div>
      <div class="am-logs" id="amLogs"></div>
    </div>
    <button type="button" id="autoMonBtn" title="Theo dõi Auto BOT: Số lượng tác vụ xử lý ngày Today - Chờ"><span class="dot"></span><span id="amBtnText">Auto BOT: 0 Today - 0 Chờ</span></button>`;
  document.body.appendChild(root);

  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  $('autoMonBtn').addEventListener('click', () => $('autoMonPanel').classList.toggle('open'));

  let logsCleared = false;
  $('amClearLogsBtn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    logsCleared = true;
    $('amLogs').innerHTML = '<div style="color:#94a3b8;font-style:italic">Đã làm sạch nhật ký trên màn hình</div>';
  });

  const ORDER = ['bypass', 'cls', 'assign', 'clear_signal', 'reset_signal', 'mybae', 'spampool', 'bypass_nat', 'port'];

  async function refresh() {
    try {
      const res = await fetch('/api/auto/overview?_t=' + Date.now());
      if (!res.ok) return;
      const d = await res.json();
      const run = d.running;
      const totalToday = d.total_today || 0;
      const totalPending = d.total_pending || 0;

      $('amToday').textContent = `${totalToday} Today`;
      $('amTotal').textContent = `${totalPending} Chờ`;
      $('amLast').textContent = d.last_scan || '--';
      $('amInterval').textContent = d.scan_interval;

      const btn = $('autoMonBtn');
      btn.classList.toggle('busy', !!run);
      $('amBtnText').textContent = run
        ? `Đang chạy ${run.label} ${run.current}/${run.total} · ${totalToday} Today - ${totalPending} Chờ`
        : `Auto BOT: ${totalToday} Today - ${totalPending} Chờ`;

      const runEl = $('amRun');
      if (run) {
        const pct = run.total ? Math.round(run.current / run.total * 100) : 0;
        runEl.className = 'am-run on';
        runEl.innerHTML = `⚙️ <b>Đang xử lý: ${esc(run.label)}</b> — ${run.current}/${run.total} HĐ
          ${run.shd ? `<br>HĐ hiện tại: <b>${esc(run.shd)}</b>` : ''}
          <div style="margin-top:4px;opacity:.85">${esc(run.message)}</div>
          <div class="am-bar"><i style="width:${pct}%"></i></div>`;
      } else {
        runEl.className = 'am-run off';
        runEl.textContent = totalPending ? '⏳ Rảnh — sẽ tự chạy ở lần quét kế tiếp' : `✅ Hệ thống đang rảnh (${totalToday} tác vụ xử lý hôm nay)`;
      }

      $('amTabs').innerHTML = ORDER.filter(k => d.tabs[k]).map(k => {
        const t = d.tabs[k];
        const tip = (t.shds || []).join(', ');
        const todayCnt = t.today || 0;
        const pendCnt = t.pending || 0;
        return `<div class="am-tab ${pendCnt ? 'has' : ''} ${t.auto ? '' : 'off'}" title="${esc(tip || `Hôm nay: ${todayCnt} | Chờ: ${pendCnt}`)}">
          <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(t.label)}${t.auto ? '' : ' (tắt)'}</span>
          <span class="am-counts">
            <b class="today" title="Số tác vụ xử lý hôm nay (Today)">${todayCnt}</b>
            <span style="color:#94a3b8;font-weight:700">-</span>
            <b class="wait" title="Số tác vụ đang chờ xử lý">${pendCnt}</b>
          </span>
        </div>`;
      }).join('');

      if (!logsCleared) {
        $('amLogs').innerHTML = (d.logs || []).map(l =>
          `<div class="${esc(l.level)}"><span class="t">${esc(l.time)}</span>${esc(l.text)}</div>`).join('') ||
          '<div style="color:#94a3b8">Chưa có nhật ký</div>';
      }
    } catch (e) { /* bỏ qua lỗi mạng tạm thời */ }
  }

  refresh();
  setInterval(refresh, 2000);
})();
