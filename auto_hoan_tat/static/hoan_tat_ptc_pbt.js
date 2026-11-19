(function () {
  "use strict";

  const el = (id) => document.getElementById(id);
  const API_BASE = String(window.AHT_API_BASE || "").replace(/\/+$/, "");

  let allRecords = [];
  let selectedShds = new Set();
  let resultsByShd = {};
  let pollTimer = null;

  function normUpper(s) {
    return String(s || "").normalize("NFC").replace(/\s+/g, " ").trim().toUpperCase();
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function updateModeBadge() {
    const isDry = el("chkDryRun").checked;
    const badge = el("modeBadge");
    if (isDry) {
      badge.className = "aht-pill pill-dry";
      badge.textContent = "Chế độ: DRY-RUN (Mô phỏng)";
    } else {
      badge.className = "aht-pill pill-real";
      badge.textContent = "Chế độ: CHẠY THẬT (Ghi dữ liệu)";
    }
  }

  function getFilteredRecords() {
    const q = normUpper(el("searchShd").value);
    const loai = el("filterLoai").value;
    const tv = normUpper(el("filterTacVu").value);

    return allRecords.filter((r) => {
      if (q && !normUpper(r.shd).includes(q)) return false;
      if (loai === "INVALID" && r.loai) return false;
      if (loai && loai !== "INVALID" && r.loai !== loai) return false;
      if (tv && normUpper(r.tac_vu) !== tv) return false;
      return true;
    });
  }

  function statusBadgeHtml(st) {
    if (!st) return '<span class="badge b-invalid">Chưa chạy</span>';
    if (st === "SUCCESS") return '<span class="badge b-ok">✓ Đã hoàn tất</span>';
    if (st === "DRY_RUN_READY") return '<span class="badge b-ok">✓ Đủ ĐK (DRY-RUN)</span>';
    if (st === "NOT_ELIGIBLE") return '<span class="badge b-warn">⚠ Không đủ ĐK</span>';
    if (st === "SKIPPED_ALREADY_DONE") return '<span class="badge b-invalid">Đã xong trước đó</span>';
    if (st === "SKIPPED_UNSUPPORTED") return '<span class="badge b-invalid">Bỏ qua</span>';
    return '<span class="badge b-err">✕ Lỗi</span>';
  }

  function renderTable() {
    const tbody = el("ticketTableBody");
    const rows = getFilteredRecords();

    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="8" style="text-align:center;color:#64748b;padding:24px;">Không có phiếu nào khớp bộ lọc.</td></tr>';
      return;
    }

    tbody.innerHTML = rows
      .map((r) => {
        const shdKey = normUpper(r.shd);
        const checked = selectedShds.has(shdKey) ? "checked" : "";
        const runRec = resultsByShd[shdKey];

        let loaiBadge = '<span class="badge b-invalid">Không hợp lệ</span>';
        if (r.loai === "PBT") {
          loaiBadge = `<span class="badge b-pbt">PBT</span> <small style="color:#64748b;">${escapeHtml(r.tab_dich)}</small>`;
        } else if (r.loai === "PTC") {
          loaiBadge = `<span class="badge b-ptc">PTC</span> <small style="color:#64748b;">${escapeHtml(r.tab_dich)}</small>`;
        }

        const detailText = runRec
          ? escapeHtml(runRec.ket_qua || "")
          : escapeHtml(r.loai_ly_do || "Sẵn sàng kiểm tra");

        return `
          <tr>
            <td><input type="checkbox" class="row-chk" data-shd="${escapeHtml(shdKey)}" ${checked} /></td>
            <td>${escapeHtml(r.row_id || "")}</td>
            <td><strong>${escapeHtml(r.shd || "")}</strong></td>
            <td>${escapeHtml(r.tac_vu || "")}</td>
            <td>${loaiBadge}</td>
            <td>${escapeHtml(r.ket_qua || "")}</td>
            <td>${statusBadgeHtml(runRec ? runRec.status : "")}</td>
            <td style="font-size:12.5px;color:#334155;">${detailText}</td>
          </tr>
        `;
      })
      .join("");

    tbody.querySelectorAll(".row-chk").forEach((chk) => {
      chk.addEventListener("change", () => {
        const key = chk.getAttribute("data-shd");
        if (chk.checked) selectedShds.add(key);
        else selectedShds.delete(key);
      });
    });
  }

  function renderLogs(logs) {
    const box = el("liveLogs");
    if (!logs || !logs.length) {
      box.innerHTML = '<div class="log-info">Chưa có nhật ký hoạt động.</div>';
      return;
    }
    box.innerHTML = logs
      .map(
        (item) =>
          `<div class="log-${escapeHtml(item.level || "info")}">[${escapeHtml(item.time)}] ${escapeHtml(item.message)}</div>`
      )
      .join("");
    box.scrollTop = box.scrollHeight;
  }

  async function loadSheet() {
    el("btnReload").disabled = true;
    el("progressText").textContent = "Đang tải dữ liệu từ Google Sheet...";
    try {
      const resp = await fetch(`${API_BASE}/api/sheet`);
      const data = await resp.json();
      if (!resp.ok || data.status !== "ok") {
        throw new Error(data.message || "Không tải được Google Sheet");
      }
      allRecords = data.records || [];
      selectedShds = new Set(allRecords.map((r) => normUpper(r.shd)).filter(Boolean));
      el("chkSelectAll").checked = true;

      el("statTotal").textContent = data.counts.total;
      el("statPbt").textContent = data.counts.pbt;
      el("statPtc").textContent = data.counts.ptc;
      el("sheetFetchedAt").textContent = "Cập nhật: " + (data.fetched_at || "");
      el("progressText").textContent = `Đã nạp ${data.counts.total} phiếu từ Google Sheet.`;
      renderTable();
    } catch (err) {
      el("progressText").textContent = "Lỗi tải Sheet: " + err.message;
    } finally {
      el("btnReload").disabled = false;
    }
  }

  async function pollStatus() {
    try {
      const resp = await fetch(`${API_BASE}/api/status`);
      const st = await resp.json();

      resultsByShd = st.results_by_shd || {};
      renderTable();
      renderLogs(st.logs || []);

      const total = st.total || 0;
      const done = st.processed || 0;
      const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
      el("progressFill").style.width = pct + "%";

      const vals = Object.values(resultsByShd);
      el("statSuccess").textContent = vals.filter(
        (r) => r.status === "SUCCESS" || r.status === "DRY_RUN_READY"
      ).length;
      el("statNotEligible").textContent = vals.filter((r) => r.status === "NOT_ELIGIBLE").length;
      el("statErrors").textContent = vals.filter((r) => r.status === "ERROR").length;

      el("btnRun").disabled = st.running;
      el("btnStop").disabled = !st.running;

      if (st.running) {
        el("progressText").textContent = `Đang chạy [${st.mode}] ${done}/${total} phiếu${
          st.current_shd ? " — HĐ: " + st.current_shd : ""
        }...`;
      } else if (st.finished_at) {
        el("progressText").textContent = st.error
          ? `Dừng do lỗi: ${st.error}`
          : `Hoàn tất lượt [${st.mode}] lúc ${st.finished_at} (${done}/${total} phiếu).`;
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
      }
    } catch (err) {
      // Bỏ qua lỗi mạng thoáng qua khi poll
    }
  }

  async function startRun(dryRun) {
    const filtered = getFilteredRecords();
    const chosen = filtered
      .map((r) => normUpper(r.shd))
      .filter((shd) => shd && selectedShds.has(shd));

    if (!chosen.length) {
      alert("Vui lòng chọn ít nhất 1 phiếu có SHD để chạy.");
      return;
    }

    el("btnRun").disabled = true;
    try {
      const resp = await fetch(`${API_BASE}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dry_run: dryRun,
          visible: el("chkVisible").checked,
          shds: chosen,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        alert(data.message || "Không thể khởi chạy tác vụ.");
        el("btnRun").disabled = false;
        return;
      }
      el("btnStop").disabled = false;
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(pollStatus, 1000);
      pollStatus();
    } catch (err) {
      alert("Lỗi kết nối server: " + err.message);
      el("btnRun").disabled = false;
    }
  }

  // Event bindings
  el("chkDryRun").addEventListener("change", updateModeBadge);
  el("btnReload").addEventListener("click", loadSheet);
  el("searchShd").addEventListener("input", renderTable);
  el("filterLoai").addEventListener("change", renderTable);
  el("filterTacVu").addEventListener("change", renderTable);

  el("chkSelectAll").addEventListener("change", (e) => {
    const checked = e.target.checked;
    getFilteredRecords().forEach((r) => {
      const key = normUpper(r.shd);
      if (!key) return;
      if (checked) selectedShds.add(key);
      else selectedShds.delete(key);
    });
    renderTable();
  });

  el("btnRun").addEventListener("click", () => {
    const isDry = el("chkDryRun").checked;
    if (isDry) {
      startRun(true);
      return;
    }
    const count = getFilteredRecords().filter((r) => selectedShds.has(normUpper(r.shd))).length;
    el("confirmRealCount").textContent = `Số phiếu đang chọn để CHẠY THẬT: ${count} phiếu.`;
    el("confirmRealModal").classList.add("open");
  });

  el("btnCancelReal").addEventListener("click", () => {
    el("confirmRealModal").classList.remove("open");
  });

  el("btnConfirmReal").addEventListener("click", () => {
    el("confirmRealModal").classList.remove("open");
    startRun(false);
  });

  el("btnStop").addEventListener("click", async () => {
    await fetch(`${API_BASE}/api/stop`, { method: "POST" });
    pollStatus();
  });

  el("btnExportCsv").addEventListener("click", () => {
    window.location.href = `${API_BASE}/api/export-csv`;
  });

  el("btnClearLogs").addEventListener("click", async () => {
    await fetch(`${API_BASE}/api/logs/clear`, { method: "POST" });
    renderLogs([]);
  });

  // Init
  updateModeBadge();
  loadSheet();
  pollStatus();
})();
