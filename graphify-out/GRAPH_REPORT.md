# Graph Report - Data Retrieval Tool  (2026-11-15)

## Corpus Check
- 44 files · ~114,028 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .bat 4, (none) 2, .example 1)

## Summary
- 1385 nodes · 2753 edges · 57 communities (38 shown, 19 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 79 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `89aed237`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- dom.js
- inside_report_crawler.py
- mybae.js
- settings.js
- assign.js
- clear_signal.js
- reset_signal.js
- bypass_nat.js
- spampool.js
- inside_spampool.py
- port_manage.js
- inside_signal.py
- route
- add_log
- run_mybae_process
- norm_lower
- clear_cls.js
- json
- bypass.js
- create_driver_with_retry
- InsideScraper
- core_login.py
- load_config
- InsidePortAutomation
- InsideMyBaeAutomation
- inside_bypass.py
- auto_import_service.py
- InsideSignalAutomation
- time
- ModernInsideFPTApp
- unified_tabs.js
- FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc
- inside_port.py
- renderBypassTable
- inside_bypass_nat.py
- loadAssignSheetData
- loadClsSheetData
- remove_accents
- import.js
- shell.js
- tabs.js
- test_single_port
- Template_Danh_Sach_Hop_Dong_fd19b39a.md
- _click_iam_login_button
- download_full_log
- run.sh
- _auto_orchestrator_cycle
- _load_log_from_disk
- _auto_reset_after_clear_check

## God Nodes (most connected - your core abstractions)
1. `add_log()` - 70 edges
2. `load_config()` - 34 edges
3. `InsideAssignAutomation` - 34 edges
4. `release_inside_task()` - 25 edges
5. `run_fpt_login()` - 22 edges
6. `fetch_tk_report_excel()` - 22 edges
7. `run_auto_import()` - 21 edges
8. `fetch_sheet_data()` - 18 edges
9. `InsideMyBaeAutomation` - 18 edges
10. `InsideScraper` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Quy Tắc Thực Thi` --references--> `check_14d_hau_kiem_violation()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `Quy Tắc Thực Thi` --references--> `is_admin_staff()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `export_retrieval_excel()` --indirect_call--> `writer()`  [INFERRED]
  server.py → test_concurrency_and_safeguards.py
- `export_bypass_excel()` --indirect_call--> `writer()`  [INFERRED]
  server.py → test_concurrency_and_safeguards.py
- `export_cls_excel()` --indirect_call--> `writer()`  [INFERRED]
  server.py → test_concurrency_and_safeguards.py

## Import Cycles
- None detected.

## Communities (57 total, 19 thin omitted)

### Community 0 - "dom.js"
Cohesion: 0.02
Nodes (125): appSidebar, assignLogTerminal, badgeBypassPending, bannerDot, bannerHost, bannerText, btnAutoFetch, btnBackToBypass (+117 more)

### Community 1 - "inside_report_crawler.py"
Cohesion: 0.07
Nodes (21): close_driver_and_clear_session(), get_am_account_info(), inside_session_healthy(), _read_cookie_store(), restore_inside_cookies(), save_inside_cookies(), _click_element_safe(), _complete_iam_microsoft_login() (+13 more)

### Community 2 - "mybae.js"
Cohesion: 0.05
Nodes (49): autoMyBaeModeDot, autoMyBaeModeText, badgeMyBaePending, btnAutoMyBaeModeToggle, btnClearMyBaeCache, btnClearMyBaeLogs, btnExportMyBaeData, btnRefreshMyBaeSheetData (+41 more)

### Community 3 - "settings.js"
Cohesion: 0.05
Nodes (41): pollStatus(), setLoginButtonState(), formatDateDataDisplay(), initialTodayStr, loadRetrievalData(), openDetailModal(), renderContractTags(), renderRetrievalTable() (+33 more)

### Community 4 - "assign.js"
Cohesion: 0.05
Nodes (36): assignKnownShds, assignProgressBar, assignProgressTracker, assignRunIcon, assignRunText, assignSelectedCountText, assignSpinner, assignStatDone (+28 more)

### Community 5 - "clear_signal.js"
Cohesion: 0.05
Nodes (45): autoClearSignalModeDot, autoClearSignalModeIcon, autoClearSignalModeText, badgeClearSignalPending, btnAutoClearSignalModeToggle, btnClearClearSignalCache, btnClearClearSignalLogs, btnExportClearSignalData (+37 more)

### Community 6 - "reset_signal.js"
Cohesion: 0.05
Nodes (45): autoResetSignalModeDot, autoResetSignalModeIcon, autoResetSignalModeText, badgeResetSignalPending, btnAutoResetSignalModeToggle, btnClearResetSignalCache, btnClearResetSignalLogs, btnExportResetSignalData (+37 more)

### Community 7 - "bypass_nat.js"
Cohesion: 0.06
Nodes (42): autoBypassNatModeDot, autoBypassNatModeText, badgeBypassNatPending, btnAutoBypassNatModeToggle, btnBypassNatLogin, btnClearBypassNatCache, btnExportBypassNatData, btnRefreshBypassNatSheetData (+34 more)

### Community 8 - "spampool.js"
Cohesion: 0.05
Nodes (42): autoSpamPoolModeDot, autoSpamPoolModeText, badgeSpamPoolPending, btnAutoSpamPoolModeToggle, btnClearSpamPoolCache, btnClearSpamPoolLogs, btnExportSpamPoolData, btnRefreshSpamPoolSheetData (+34 more)

### Community 9 - "inside_spampool.py"
Cohesion: 0.12
Nodes (13): fetch_sheet_data(), get_radius_profile_dir(), InsideSpamPoolAutomation, is_deactive_ip_task(), is_pending(), is_processed(), load_cache(), remove_accents() (+5 more)

### Community 10 - "port_manage.js"
Cohesion: 0.06
Nodes (37): autoPortModeDot, autoPortModeText, badgePortPending, btnAutoPortModeToggle, btnClearPortCache, btnExportPortData, btnRefreshPortSheetData, btnStartAutoPort (+29 more)

### Community 11 - "inside_signal.py"
Cohesion: 0.10
Nodes (30): is_final_thao_tac(), fetch_sheet_data(), get_reset_user_shds(), _is_auto_reset_cache_entry(), is_clear_success(), is_final_status(), normalize_nfc(), _auto_pending_clear_signal() (+22 more)

### Community 12 - "route"
Cohesion: 0.05
Nodes (55): save_config(), _apply_bypass_cache_to_record(), bypass_nat_manual_login(), clear_bypass_cache(), clear_bypass_nat_cache(), clear_clear_signal_cache(), clear_cls_cache(), clear_mybae_cache() (+47 more)

### Community 13 - "add_log"
Cohesion: 0.09
Nodes (36): atomic_write_json(), invalidate_session(), release_inside_task(), try_acquire_inside_task(), add_log(), check_cached_contract_48h(), check_session_api(), clear_all_sessions_api() (+28 more)

### Community 14 - "run_mybae_process"
Cohesion: 0.22
Nodes (8): is_final_row(), _auto_pending_assign(), _auto_pending_cls(), _auto_pending_generic(), _auto_pending_mybae(), _auto_pending_mybae_generic(), export_mybae_excel(), _lc()

### Community 15 - "norm_lower"
Cohesion: 0.18
Nodes (3): format_cls_thao_tac(), InsideClearClsAutomation, norm_lower()

### Community 16 - "clear_cls.js"
Cohesion: 0.06
Nodes (31): autoClsModeDot, autoClsModeIcon, autoClsModeText, badgeClsPending, btnAutoClsModeToggle, btnRefreshClsSheetData, btnRunAutoCls, chkClsSelectAll (+23 more)

### Community 17 - "json"
Cohesion: 0.15
Nodes (4): main(), get_radius_profile_dir(), get_port_profile_dir(), get_json()

### Community 18 - "bypass.js"
Cohesion: 0.09
Nodes (20): appsScriptCodeBlock, autoModeDot, autoModeIcon, autoModeText, btnAutoModeToggle, btnCloseWebhookGuide, btnCopyScriptCode, btnOkWebhookGuide (+12 more)

### Community 19 - "create_driver_with_retry"
Cohesion: 0.06
Nodes (14): build_chrome_options(), clean_profile_locks_and_orphans(), clear_inside_session(), create_driver_with_retry(), get_inside_profile_dir(), init_chrome_driver(), run_radius_login(), InsideBypassAutomation (+6 more)

### Community 22 - "core_login.py"
Cohesion: 0.12
Nodes (6): extract_secret_from_qr_image(), _get_file_lock(), parse_proto(), parse_varint(), extract_ptc_fields(), normalize_nfc()

### Community 23 - "load_config"
Cohesion: 0.15
Nodes (8): main(), _cfg_keep_inside_session(), get_active_account_info(), load_config(), run_fpt_login(), transfer_contract_to_reset_sheet(), update_clear_sheet_auto_cap_lai_cell(), get_config()

### Community 26 - "inside_bypass.py"
Cohesion: 0.16
Nodes (13): Nguồn Dữ Liệu Phân Quyền Admin, Quy Tắc Phân Quyền Admin (Admin Privileges Rule), Quy Tắc Thực Thi, check_14d_hau_kiem_violation(), fetch_sheet_data(), is_admin_staff(), is_bypass_final_status(), load_admin_staff_set() (+5 more)

### Community 27 - "auto_import_service.py"
Cohesion: 0.06
Nodes (30): get_dataset_config(), get_db_url(), get_default_date_range(), is_auto_import_enabled(), load_local_env(), _parse_bool(), _parse_partners(), validate_date_str() (+22 more)

### Community 29 - "time"
Cohesion: 0.28
Nodes (10): _canonical_column(), clean_str(), fetch_sheet_data(), format_assign_thao_tac(), fetch_sheet_data(), normalize_nfc(), remove_accents(), _canonical_column() (+2 more)

### Community 30 - "ModernInsideFPTApp"
Cohesion: 0.23
Nodes (3): ModernInsideFPTApp, worker(), get_totp_info()

### Community 31 - "unified_tabs.js"
Cohesion: 0.27
Nodes (12): filterRecords(), getRecordNumericId(), getRecordTimestamp(), getStaff(), isDateInRange(), isPendingSheetRow(), isRecordDone(), isRecordError() (+4 more)

### Community 32 - "FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc"
Cohesion: 0.17
Nodes (11): 1. Cách mở file dữ liệu trên Ubuntu:, 1. Khởi động ứng dụng, 2. Auto Lấy thông tin, 2. Cách chạy ứng dụng trên PC Ubuntu:, 3. Quản lý 2 Chế Độ Tài Khoản (Mặc định & Tùy chỉnh), 4. Xem chi tiết & Xuất Excel, 🧩 Cấu trúc component (Frontend), FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc (+3 more)

### Community 34 - "inside_port.py"
Cohesion: 0.20
Nodes (9): fetch_sheet_data(), is_pending(), is_processed(), is_thu_hoi_port_task(), load_cache(), normalize_nfc(), parse_tstc_info(), remove_accents() (+1 more)

### Community 35 - "renderBypassTable"
Cohesion: 0.23
Nodes (13): filterTableByStaff(), getRecordField(), loadBypassSheetData(), onActivate(), pollBypassStatus(), renderBypassTable(), renderTopFailedStaff(), runBypassProcess() (+5 more)

### Community 36 - "inside_bypass_nat.py"
Cohesion: 0.31
Nodes (5): fetch_sheet_data(), is_pending(), is_processed(), normalize_nfc(), remove_accents()

### Community 37 - "loadAssignSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerAssign(), _isAssignFinalDone(), loadAssignSheetData(), onActivate(), pollAssignStatus(), renderAssignTable(), runAssignProcess(), setAssignRunningState() (+2 more)

### Community 38 - "loadClsSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerBypass(), _isClsRecordDone(), loadClsSheetData(), onActivate(), pollClsStatus(), renderClsTable(), runClsProcess(), setClsRunningState() (+2 more)

### Community 43 - "test_single_port"
Cohesion: 0.67
Nodes (4): save_cache(), worker_port(), test_single_port(), _update_port_sheet_webhook()

### Community 48 - "_click_iam_login_button"
Cohesion: 0.17
Nodes (7): _click_iam_login_button(), _log(), _find_iam_button_candidate(), _is_iam_redirected(), _login_inside_via_iam_am(), log(), _should_use_iam_login()

### Community 54 - "download_full_log"
Cohesion: 0.40
Nodes (3): download_full_log(), _flush_log_to_disk(), _log_flusher_loop()

### Community 64 - "_auto_orchestrator_cycle"
Cohesion: 0.19
Nodes (10): load_cache(), parse_vn_datetime(), save_cache(), update_cache_record(), auto_modes_api(), _auto_orchestrator_cycle(), auto_overview_api(), _auto_task_states() (+2 more)

### Community 66 - "_auto_reset_after_clear_check"
Cohesion: 0.10
Nodes (11): get_running_inside_task(), _auto_any_running(), _auto_orchestrator_loop(), _auto_reset_after_clear_check(), _auto_reset_after_clear_loop(), _ensure_bg_threads_on_request(), _other_inside_task_running(), _parse_vn_dt() (+3 more)

## Knowledge Gaps
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InsideAssignAutomation` connect `remove_accents` to `.navigate_to_assign_page`, `add_log`, `norm_lower`, `InsideAssignAutomation`, `InsideMyBaeAutomation`, `time`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `add_log()` (e.g. with `clear_all_sessions_api()` and `worker_assign()`) actually correct?**
  _`add_log()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `dom.js` be split into smaller, more focused modules?**
  _Cohesion score 0.015873015873015872 - nodes in this community are weakly interconnected._
- **Why does `InsideBypassAutomation` connect `create_driver_with_retry` to `inside_bypass.py`, `add_log`, `load_config`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `inside_report_crawler.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0663265306122449 - nodes in this community are weakly interconnected._
- **Why does `load_config()` connect `load_config` to `inside_report_crawler.py`, `inside_spampool.py`, `inside_signal.py`, `route`, `add_log`, `test_single_port`, `create_driver_with_retry`, `InsideScraper`, `core_login.py`, `InsidePortAutomation`, `InsideSignalAutomation`, `ModernInsideFPTApp`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Should `mybae.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05152394775036284 - nodes in this community are weakly interconnected._