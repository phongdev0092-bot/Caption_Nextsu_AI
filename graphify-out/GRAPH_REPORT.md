# Graph Report - Data Retrieval Tool  (2026-11-15)

## Corpus Check
- 44 files · ~117,223 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: .bat 4, (none) 2, .css 2)

## Summary
- 1393 nodes · 2747 edges · 58 communities (38 shown, 20 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c344dc98`
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
- release_inside_task
- run_mybae_process
- InsideClearClsAutomation
- clear_cls.js
- run_radius_login
- bypass.js
- inside_bypass_nat.py
- InsideBypassAutomation
- InsideScraper
- core_login.py
- load_config
- InsidePortAutomation
- InsideAssignAutomation
- inside_bypass.py
- auto_import_service.py
- InsideSignalAutomation
- inside_assign.py
- ModernInsideFPTApp
- unified_tabs.js
- FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc
- run_fpt_login
- inside_port.py
- renderBypassTable
- writer
- loadAssignSheetData
- loadClsSheetData
- create_driver_with_retry
- import.js
- shell.js
- tabs.js
- atomic_write_json
- Template_Danh_Sach_Hop_Dong_fd19b39a.md
- Quy Tắc Phân Quyền Admin (Admin Privileges Rule)
- _click_iam_login_button
- auto_overview_api
- run.sh
- start_background_threads
- _load_log_from_disk
- _auto_reset_after_clear_check

## God Nodes (most connected - your core abstractions)
1. `add_log()` - 39 edges
2. `InsideAssignAutomation` - 34 edges
3. `load_config()` - 34 edges
4. `release_inside_task()` - 25 edges
5. `fetch_tk_report_excel()` - 22 edges
6. `run_fpt_login()` - 22 edges
7. `run_auto_import()` - 21 edges
8. `make_task_logger()` - 20 edges
9. `InsideMyBaeAutomation` - 18 edges
10. `fetch_sheet_data()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Quy Tắc Thực Thi` --references--> `check_14d_hau_kiem_violation()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `Quy Tắc Thực Thi` --references--> `is_admin_staff()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `export_clear_signal_excel()` --indirect_call--> `writer()`  [INFERRED]
  server.py → test_concurrency_and_safeguards.py
- `export_reset_signal_excel()` --indirect_call--> `writer()`  [INFERRED]
  server.py → test_concurrency_and_safeguards.py
- `export_mybae_excel()` --indirect_call--> `writer()`  [INFERRED]
  server.py → test_concurrency_and_safeguards.py

## Import Cycles
- None detected.

## Communities (58 total, 20 thin omitted)

### Community 0 - "dom.js"
Cohesion: 0.02
Nodes (125): appSidebar, assignLogTerminal, badgeBypassPending, bannerDot, bannerHost, bannerText, btnAutoFetch, btnBackToBypass (+117 more)

### Community 1 - "inside_report_crawler.py"
Cohesion: 0.14
Nodes (13): _click_element_safe(), _complete_iam_microsoft_login(), _create_crawler_driver(), _emit_log(), fetch_tk_report_excel(), _fill_date_range(), _is_login_screen_present(), _login_inside_with_limit() (+5 more)

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
Nodes (14): fetch_sheet_data(), get_radius_profile_dir(), InsideSpamPoolAutomation, is_deactive_ip_task(), is_pending(), is_processed(), load_cache(), normalize_nfc() (+6 more)

### Community 10 - "port_manage.js"
Cohesion: 0.06
Nodes (37): autoPortModeDot, autoPortModeText, badgePortPending, btnAutoPortModeToggle, btnClearPortCache, btnExportPortData, btnRefreshPortSheetData, btnStartAutoPort (+29 more)

### Community 11 - "inside_signal.py"
Cohesion: 0.11
Nodes (33): fetch_sheet_data(), get_reset_user_shds(), _is_auto_reset_cache_entry(), is_clear_success(), is_final_status(), load_cache(), normalize_nfc(), parse_vn_datetime() (+25 more)

### Community 12 - "route"
Cohesion: 0.06
Nodes (53): save_config(), add_log(), _auto_reset_after_clear_loop(), clear_all_sessions_api(), clear_bypass_cache(), clear_bypass_nat_cache(), clear_clear_signal_cache(), clear_cls_cache() (+45 more)

### Community 13 - "release_inside_task"
Cohesion: 0.10
Nodes (21): get_running_inside_task(), release_inside_task(), try_acquire_inside_task(), fetch_sheet_data(), bypass_nat_manual_login(), check_cached_contract_48h(), check_session_api(), get_cls_sheet_data() (+13 more)

### Community 14 - "run_mybae_process"
Cohesion: 0.16
Nodes (12): normalize_nfc(), fetch_sheet_data(), is_final_row(), _auto_pending_assign(), _auto_pending_cls(), _auto_pending_generic(), _auto_pending_mybae(), _auto_pending_mybae_generic() (+4 more)

### Community 15 - "InsideClearClsAutomation"
Cohesion: 0.14
Nodes (5): invalidate_session(), format_cls_thao_tac(), InsideClearClsAutomation, norm_lower(), worker_cls()

### Community 16 - "clear_cls.js"
Cohesion: 0.06
Nodes (31): autoClsModeDot, autoClsModeIcon, autoClsModeText, badgeClsPending, btnAutoClsModeToggle, btnRefreshClsSheetData, btnRunAutoCls, chkClsSelectAll (+23 more)

### Community 18 - "bypass.js"
Cohesion: 0.09
Nodes (20): appsScriptCodeBlock, autoModeDot, autoModeIcon, autoModeText, btnAutoModeToggle, btnCloseWebhookGuide, btnCopyScriptCode, btnOkWebhookGuide (+12 more)

### Community 19 - "inside_bypass_nat.py"
Cohesion: 0.12
Nodes (12): fetch_sheet_data(), get_radius_profile_dir(), InsideBypassNatAutomation, is_pending(), is_processed(), load_cache(), normalize_nfc(), remove_accents() (+4 more)

### Community 22 - "core_login.py"
Cohesion: 0.13
Nodes (7): extract_secret_from_qr_image(), _find_iam_button_candidate(), _get_file_lock(), get_totp_info(), parse_proto(), parse_varint(), _should_use_iam_login()

### Community 23 - "load_config"
Cohesion: 0.20
Nodes (7): get_active_account_info(), get_am_account_info(), load_config(), _get_am_credentials(), get_config(), update_sheet_remote_assign(), update_sheet_remote_cls()

### Community 25 - "InsideAssignAutomation"
Cohesion: 0.06
Nodes (11): clean_str(), format_assign_thao_tac(), InsideAssignAutomation, _xp(), remove_accents(), format_mybae_thao_tac(), InsideMyBaeAutomation, _pick_option() (+3 more)

### Community 26 - "inside_bypass.py"
Cohesion: 0.17
Nodes (14): Quy Tắc Thực Thi, check_14d_hau_kiem_violation(), fetch_sheet_data(), is_admin_staff(), is_bypass_final_status(), load_admin_staff_set(), _normalize_msnv(), normalize_nfc() (+6 more)

### Community 27 - "auto_import_service.py"
Cohesion: 0.05
Nodes (33): main(), get_dataset_config(), get_db_url(), get_default_date_range(), is_auto_import_enabled(), load_local_env(), _parse_bool(), _parse_partners() (+25 more)

### Community 29 - "inside_assign.py"
Cohesion: 0.14
Nodes (3): _canonical_column(), _canonical_column(), extract_ptc_fields()

### Community 31 - "unified_tabs.js"
Cohesion: 0.27
Nodes (12): filterRecords(), getRecordNumericId(), getRecordTimestamp(), getStaff(), isDateInRange(), isPendingSheetRow(), isRecordDone(), isRecordError() (+4 more)

### Community 32 - "FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc"
Cohesion: 0.17
Nodes (11): 1. Cách mở file dữ liệu trên Ubuntu:, 1. Khởi động ứng dụng, 2. Auto Lấy thông tin, 2. Cách chạy ứng dụng trên PC Ubuntu:, 3. Quản lý 2 Chế Độ Tài Khoản (Mặc định & Tùy chỉnh), 4. Xem chi tiết & Xuất Excel, 🧩 Cấu trúc component (Frontend), FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc (+3 more)

### Community 33 - "run_fpt_login"
Cohesion: 0.14
Nodes (8): main(), _cfg_keep_inside_session(), close_driver_and_clear_session(), inside_session_healthy(), _read_cookie_store(), restore_inside_cookies(), run_fpt_login(), save_inside_cookies()

### Community 34 - "inside_port.py"
Cohesion: 0.16
Nodes (9): fetch_sheet_data(), get_port_profile_dir(), is_pending(), is_processed(), is_thu_hoi_port_task(), normalize_nfc(), parse_tstc_info(), remove_accents() (+1 more)

### Community 35 - "renderBypassTable"
Cohesion: 0.23
Nodes (13): filterTableByStaff(), getRecordField(), loadBypassSheetData(), onActivate(), pollBypassStatus(), renderBypassTable(), renderTopFailedStaff(), runBypassProcess() (+5 more)

### Community 36 - "writer"
Cohesion: 0.13
Nodes (11): fetch_sheet_data(), is_final_thao_tac(), download_retrieval_template(), export_assign_excel(), export_cls_excel(), export_retrieval_excel(), extract_record_date_str(), get_assign_sheet_data() (+3 more)

### Community 37 - "loadAssignSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerAssign(), _isAssignFinalDone(), loadAssignSheetData(), onActivate(), pollAssignStatus(), renderAssignTable(), runAssignProcess(), setAssignRunningState() (+2 more)

### Community 38 - "loadClsSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerBypass(), _isClsRecordDone(), loadClsSheetData(), onActivate(), pollClsStatus(), renderClsTable(), runClsProcess(), setClsRunningState() (+2 more)

### Community 39 - "create_driver_with_retry"
Cohesion: 0.18
Nodes (6): build_chrome_options(), clean_profile_locks_and_orphans(), clear_inside_session(), create_driver_with_retry(), get_inside_profile_dir(), init_chrome_driver()

### Community 43 - "atomic_write_json"
Cohesion: 0.24
Nodes (9): atomic_write_json(), load_cache(), save_cache(), clear_assign_cache(), clear_auto_attempts(), save_bypass_cache(), worker_port(), test_single_port() (+1 more)

### Community 48 - "_click_iam_login_button"
Cohesion: 0.25
Nodes (5): _click_iam_login_button(), _log(), _is_iam_redirected(), _login_inside_via_iam_am(), log()

### Community 64 - "start_background_threads"
Cohesion: 0.18
Nodes (6): _auto_orchestrator_loop(), download_full_log(), _ensure_bg_threads_on_request(), _flush_log_to_disk(), _log_flusher_loop(), start_background_threads()

### Community 66 - "_auto_reset_after_clear_check"
Cohesion: 0.15
Nodes (8): transfer_contract_to_reset_sheet(), update_clear_sheet_auto_cap_lai_cell(), _auto_any_running(), _auto_reset_after_clear_check(), _is_clear_success(), _other_inside_task_running(), _parse_vn_dt(), trigger_check_72h_api()

## Knowledge Gaps
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InsideMyBaeAutomation` connect `InsideAssignAutomation` to `inside_assign.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `dom.js` be split into smaller, more focused modules?**
  _Cohesion score 0.015873015873015872 - nodes in this community are weakly interconnected._
- **Why does `load_config()` connect `load_config` to `run_fpt_login`, `_auto_reset_after_clear_check`, `inside_spampool.py`, `inside_signal.py`, `route`, `release_inside_task`, `atomic_write_json`, `run_radius_login`, `inside_bypass_nat.py`, `InsideScraper`, `core_login.py`, `InsidePortAutomation`, `InsideAssignAutomation`, `InsideSignalAutomation`, `ModernInsideFPTApp`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Should `inside_report_crawler.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14022988505747128 - nodes in this community are weakly interconnected._
- **Why does `InsideAssignAutomation` connect `InsideAssignAutomation` to `inside_assign.py`, `InsideClearClsAutomation`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `mybae.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05152394775036284 - nodes in this community are weakly interconnected._
- **Should `settings.js` be split into smaller, more focused modules?**
  _Cohesion score 0.04846938775510204 - nodes in this community are weakly interconnected._