# Graph Report - Data Retrieval Tool  (2026-11-19)

## Corpus Check
- 63 files · ~135,935 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .bat 5, (none) 3, .css 2)

## Summary
- 1681 nodes · 3553 edges · 72 communities (48 shown, 24 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `02b3a664`
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
- test_web_app.py
- clear_cls.js
- validate_ticket_readonly
- bypass.js
- InsideBypassNatAutomation
- core_login.py
- InsideScraper
- orchestrator.py
- mod2_navigator.py
- InsideClearClsAutomation
- InsideAssignAutomation
- InsidePortAutomation
- auto_import_service.py
- InsideSignalAutomation
- inside_bypass.py
- ModernInsideFPTApp
- unified_tabs.js
- FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc
- mod4_executor.py
- InsideBypassAutomation
- renderBypassTable
- writer
- loadAssignSheetData
- loadClsSheetData
- _FakeDriver
- import.js
- shell.js
- tabs.js
- load_config
- Template_Danh_Sach_Hop_Dong_fd19b39a.md
- AutoHoanTatSettings
- invalidate_session
- is_pending
- close_driver_and_clear_session
- run_assign_process
- atomic_write_json
- _auto_orchestrator_cycle
- _FakeAssignAdapter
- _FakeDriverExec
- run.sh
- inside_bypass_nat.py
- _click_iam_login_button
- start_background_threads
- Quy Tắc Phân Quyền Admin (Admin Privileges Rule)
- hoan_tat_ptc_pbt.js
- check_14d_hau_kiem_violation
- create_blueprint
- urllib_request
- _load_log_from_disk

## God Nodes (most connected - your core abstractions)
1. `AutoHoanTatSettings` - 46 edges
2. `InsideAssignAutomation` - 40 edges
3. `add_log()` - 39 edges
4. `load_config()` - 34 edges
5. `open_ticket_readonly()` - 29 edges
6. `create_inside_session()` - 29 edges
7. `release_inside_task()` - 29 edges
8. `normalize_nfc()` - 29 edges
9. `InsideSession` - 28 edges
10. `load_settings()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `Quy Tắc Thực Thi` --references--> `check_14d_hau_kiem_violation()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `Quy Tắc Thực Thi` --references--> `is_admin_staff()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `_build_assign_adapter()` --calls--> `InsideAssignAutomation`  [EXTRACTED]
  auto_hoan_tat/mod2_navigator.py → inside_assign.py
- `open_ticket_readonly()` --references--> `InsideAssignAutomation`  [EXTRACTED]
  auto_hoan_tat/mod2_navigator.py → inside_assign.py
- `navigate_to_ticket()` --references--> `InsideAssignAutomation`  [EXTRACTED]
  auto_hoan_tat/mod2_navigator.py → inside_assign.py

## Import Cycles
- None detected.

## Communities (72 total, 24 thin omitted)

### Community 0 - "dom.js"
Cohesion: 0.02
Nodes (125): appSidebar, assignLogTerminal, badgeBypassPending, bannerDot, bannerHost, bannerText, btnAutoFetch, btnBackToBypass (+117 more)

### Community 1 - "inside_report_crawler.py"
Cohesion: 0.11
Nodes (14): _click_element_safe(), _complete_iam_microsoft_login(), _create_crawler_driver(), _emit_log(), fetch_tk_report_excel(), _fill_date_range(), _is_login_screen_present(), _login_inside_with_limit() (+6 more)

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
Cohesion: 0.10
Nodes (36): fetch_sheet_data(), get_reset_user_shds(), _is_auto_reset_cache_entry(), is_clear_success(), is_final_status(), load_cache(), normalize_nfc(), parse_vn_datetime() (+28 more)

### Community 12 - "route"
Cohesion: 0.06
Nodes (59): save_config(), add_log(), _apply_bypass_cache_to_record(), clear_all_sessions_api(), clear_assign_cache(), clear_bypass_cache(), clear_bypass_nat_cache(), clear_clear_signal_cache() (+51 more)

### Community 13 - "release_inside_task"
Cohesion: 0.08
Nodes (23): release_inside_task(), try_acquire_inside_task(), format_mybae_thao_tac(), bypass_nat_manual_login(), check_cached_contract_48h(), check_session_api(), make_task_logger(), _logger() (+15 more)

### Community 14 - "run_mybae_process"
Cohesion: 0.22
Nodes (8): is_final_row(), _auto_pending_assign(), _auto_pending_cls(), _auto_pending_generic(), _auto_pending_mybae(), _auto_pending_mybae_generic(), export_mybae_excel(), _lc()

### Community 15 - "test_web_app.py"
Cohesion: 0.22
Nodes (5): BatchRunSummary, main(), TestWebApp, _fake_runner(), create_app()

### Community 16 - "clear_cls.js"
Cohesion: 0.06
Nodes (31): autoClsModeDot, autoClsModeIcon, autoClsModeText, badgeClsPending, btnAutoClsModeToggle, btnRefreshClsSheetData, btnRunAutoCls, chkClsSelectAll (+23 more)

### Community 17 - "validate_ticket_readonly"
Cohesion: 0.09
Nodes (12): _safe_log(), InsideSession, _sanitize_log(), NavigationContext, _emit(), evaluate_pbt_xac_minh_conditions(), is_already_completed(), _norm_ws_lower() (+4 more)

### Community 18 - "bypass.js"
Cohesion: 0.09
Nodes (20): appsScriptCodeBlock, autoModeDot, autoModeIcon, autoModeText, btnAutoModeToggle, btnCloseWebhookGuide, btnCopyScriptCode, btnOkWebhookGuide (+12 more)

### Community 19 - "InsideBypassNatAutomation"
Cohesion: 0.14
Nodes (7): get_radius_profile_dir(), run_radius_login(), get_radius_profile_dir(), InsideBypassNatAutomation, load_cache(), save_cache(), worker_bypass_nat()

### Community 20 - "core_login.py"
Cohesion: 0.14
Nodes (5): extract_secret_from_qr_image(), _get_file_lock(), parse_proto(), parse_varint(), extract_ptc_fields()

### Community 22 - "orchestrator.py"
Cohesion: 0.09
Nodes (17): is_enabled(), load_settings(), _parse_bool(), close_extra_ticket_tabs(), _append_audit_jsonl(), _emit(), export_results_csv(), _main_cli() (+9 more)

### Community 23 - "mod2_navigator.py"
Cohesion: 0.05
Nodes (21): _build_assign_adapter(), _dump_dom_readonly(), _emit(), _format_probe_summary_txt(), _main_cli(), navigate_to_ticket(), NavigationError, open_ticket_readonly() (+13 more)

### Community 24 - "InsideClearClsAutomation"
Cohesion: 0.13
Nodes (6): invalidate_session(), format_cls_thao_tac(), InsideClearClsAutomation, norm_lower(), update_sheet_remote_cls(), worker_cls()

### Community 25 - "InsideAssignAutomation"
Cohesion: 0.06
Nodes (8): clean_str(), format_assign_thao_tac(), InsideAssignAutomation, _xp(), remove_accents(), InsideMyBaeAutomation, _pick_option(), worker_assign()

### Community 27 - "auto_import_service.py"
Cohesion: 0.06
Nodes (30): get_dataset_config(), get_db_url(), get_default_date_range(), is_auto_import_enabled(), load_local_env(), _parse_bool(), _parse_partners(), validate_date_str() (+22 more)

### Community 29 - "inside_bypass.py"
Cohesion: 0.24
Nodes (5): _canonical_column(), normalize_nfc(), _canonical_column(), fetch_sheet_data(), parse_tstc_info()

### Community 30 - "ModernInsideFPTApp"
Cohesion: 0.19
Nodes (4): main(), ModernInsideFPTApp, worker(), get_totp_info()

### Community 31 - "unified_tabs.js"
Cohesion: 0.27
Nodes (12): filterRecords(), getRecordNumericId(), getRecordTimestamp(), getStaff(), isDateInRange(), isPendingSheetRow(), isRecordDone(), isRecordError() (+4 more)

### Community 32 - "FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc"
Cohesion: 0.17
Nodes (11): 1. Cách mở file dữ liệu trên Ubuntu:, 1. Khởi động ứng dụng, 2. Auto Lấy thông tin, 2. Cách chạy ứng dụng trên PC Ubuntu:, 3. Quản lý 2 Chế Độ Tài Khoản (Mặc định & Tùy chỉnh), 4. Xem chi tiết & Xuất Excel, 🧩 Cấu trúc component (Frontend), FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc (+3 more)

### Community 33 - "mod4_executor.py"
Cohesion: 0.13
Nodes (10): _main_cli(), _emit(), execute_complete_ticket(), ExecutionResult, _select_labeled_dropdown(), _select_table_cell_dropdown(), _update_thong_tin_bao_tri_if_needed(), _update_thong_tin_dich_vu() (+2 more)

### Community 35 - "renderBypassTable"
Cohesion: 0.23
Nodes (13): filterTableByStaff(), getRecordField(), loadBypassSheetData(), onActivate(), pollBypassStatus(), renderBypassTable(), renderTopFailedStaff(), runBypassProcess() (+5 more)

### Community 36 - "writer"
Cohesion: 0.14
Nodes (9): fetch_sheet_data(), download_retrieval_template(), export_cls_excel(), export_retrieval_excel(), extract_record_date_str(), get_cls_sheet_data(), get_retrieval_list(), run_cls_process() (+1 more)

### Community 37 - "loadAssignSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerAssign(), _isAssignFinalDone(), loadAssignSheetData(), onActivate(), pollAssignStatus(), renderAssignTable(), runAssignProcess(), setAssignRunningState() (+2 more)

### Community 38 - "loadClsSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerBypass(), _isClsRecordDone(), loadClsSheetData(), onActivate(), pollClsStatus(), renderClsTable(), runClsProcess(), setClsRunningState() (+2 more)

### Community 43 - "load_config"
Cohesion: 0.12
Nodes (13): main(), _cfg_keep_inside_session(), get_active_account_info(), get_am_account_info(), inside_session_healthy(), load_config(), _read_cookie_store(), restore_inside_cookies() (+5 more)

### Community 47 - "AutoHoanTatSettings"
Cohesion: 0.11
Nodes (13): AutoHoanTatSettings, _acquire_cross_process_lock(), AuthError, _check_main_server_busy(), create_inside_session(), FeatureDisabledError, _is_pid_running(), ProfileBusyError (+5 more)

### Community 48 - "invalidate_session"
Cohesion: 0.18
Nodes (6): build_chrome_options(), clean_profile_locks_and_orphans(), clear_inside_session(), create_driver_with_retry(), get_inside_profile_dir(), init_chrome_driver()

### Community 50 - "is_pending"
Cohesion: 0.33
Nodes (4): is_pending(), is_processed(), is_thu_hoi_port_task(), remove_accents()

### Community 53 - "run_assign_process"
Cohesion: 0.40
Nodes (5): fetch_sheet_data(), is_final_thao_tac(), export_assign_excel(), get_assign_sheet_data(), run_assign_process()

### Community 54 - "atomic_write_json"
Cohesion: 0.21
Nodes (9): atomic_write_json(), fetch_sheet_data(), load_cache(), save_cache(), clear_auto_attempts(), get_port_sheet(), _release_remaining_auto_attempts(), start_port_auto() (+1 more)

### Community 55 - "_auto_orchestrator_cycle"
Cohesion: 0.18
Nodes (7): _auto_any_running(), _auto_orchestrator_cycle(), _auto_orchestrator_loop(), auto_overview_api(), _auto_task_states(), _is_record_today(), _other_inside_task_running()

### Community 61 - "inside_bypass_nat.py"
Cohesion: 0.24
Nodes (6): fetch_sheet_data(), is_pending(), is_processed(), normalize_nfc(), remove_accents(), normalize_nfc()

### Community 62 - "_click_iam_login_button"
Cohesion: 0.20
Nodes (6): _click_iam_login_button(), _log(), _find_iam_button_candidate(), _is_iam_redirected(), _login_inside_via_iam_am(), log()

### Community 64 - "start_background_threads"
Cohesion: 0.18
Nodes (6): _auto_reset_after_clear_loop(), download_full_log(), _ensure_bg_threads_on_request(), _flush_log_to_disk(), _log_flusher_loop(), start_background_threads()

### Community 66 - "hoan_tat_ptc_pbt.js"
Cohesion: 0.42
Nodes (9): escapeHtml(), getFilteredRecords(), loadSheet(), normUpper(), pollStatus(), renderLogs(), renderTable(), startRun() (+1 more)

### Community 67 - "check_14d_hau_kiem_violation"
Cohesion: 0.19
Nodes (11): Quy Tắc Thực Thi, check_14d_hau_kiem_violation(), fetch_sheet_data(), is_admin_staff(), is_bypass_final_status(), load_admin_staff_set(), _normalize_msnv(), normalize_nfc() (+3 more)

### Community 68 - "create_blueprint"
Cohesion: 0.12
Nodes (9): create_blueprint(), api_config(), api_run(), _worker(), _on_progress(), api_sheet(), _get_cfg(), index() (+1 more)

## Knowledge Gaps
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InsideAssignAutomation` connect `InsideAssignAutomation` to `InsideClearClsAutomation`, `inside_bypass.py`, `AutoHoanTatSettings`, `mod2_navigator.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `AutoHoanTatSettings` (e.g. with `fetch_sheet_data()` and `fetch_sheet_from_file()`) actually correct?**
  _`AutoHoanTatSettings` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `dom.js` be split into smaller, more focused modules?**
  _Cohesion score 0.015873015873015872 - nodes in this community are weakly interconnected._
- **Why does `normalize_nfc()` connect `orchestrator.py` to `mod4_executor.py`, `create_blueprint`, `validate_ticket_readonly`, `mod2_navigator.py`, `inside_bypass_nat.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Should `inside_report_crawler.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10795454545454546 - nodes in this community are weakly interconnected._
- **Why does `InsideScraper` connect `InsideScraper` to `release_inside_task`, `core_login.py`, `route`, `close_driver_and_clear_session`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `mybae.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05152394775036284 - nodes in this community are weakly interconnected._