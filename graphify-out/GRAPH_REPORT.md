# Graph Report - Data Retrieval Tool  (2026-11-19)

## Corpus Check
- 62 files · ~135,316 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .bat 5, (none) 3, .css 2)

## Summary
- 1672 nodes · 3526 edges · 72 communities (48 shown, 24 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 121 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0be23411`
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
- .log
- clear_cls.js
- validate_ticket_readonly
- bypass.js
- InsideBypassNatAutomation
- core_login.py
- InsideScraper
- sheet_reader.py
- mod2_navigator.py
- InsideClearClsAutomation
- InsideMyBaeAutomation
- _click_iam_login_button
- auto_import_service.py
- InsideSignalAutomation
- inside_bypass.py
- ModernInsideFPTApp
- unified_tabs.js
- FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc
- mod4_executor.py
- InsideBypassAutomation
- renderBypassTable
- export_retrieval_excel
- loadAssignSheetData
- loadClsSheetData
- _FakeDriver
- import.js
- shell.js
- tabs.js
- load_config
- Template_Danh_Sach_Hop_Dong_fd19b39a.md
- create_inside_session
- create_driver_with_retry
- run_auto_import
- load_settings
- auto_import_routes.py
- run_assign_process
- _auto_orchestrator_cycle
- _FakeAssignAdapter
- InsideAssignAutomation
- run.sh
- json
- _release_remaining_auto_attempts
- auto_import_config.py
- hoan_tat_ptc_pbt.js
- fetch_sheet_data
- _RunState
- _FakeDriverExec
- acquire_db_lock
- _load_log_from_disk

## God Nodes (most connected - your core abstractions)
1. `AutoHoanTatSettings` - 44 edges
2. `InsideAssignAutomation` - 40 edges
3. `add_log()` - 39 edges
4. `load_config()` - 34 edges
5. `create_inside_session()` - 29 edges
6. `open_ticket_readonly()` - 29 edges
7. `release_inside_task()` - 29 edges
8. `InsideSession` - 28 edges
9. `normalize_nfc()` - 28 edges
10. `load_settings()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `Quy Tắc Thực Thi` --references--> `check_14d_hau_kiem_violation()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `Quy Tắc Thực Thi` --references--> `is_admin_staff()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `_build_assign_adapter()` --calls--> `InsideAssignAutomation`  [EXTRACTED]
  auto_hoan_tat/mod2_navigator.py → inside_assign.py
- `navigate_to_ticket()` --references--> `InsideAssignAutomation`  [EXTRACTED]
  auto_hoan_tat/mod2_navigator.py → inside_assign.py
- `open_ticket_readonly()` --references--> `InsideAssignAutomation`  [EXTRACTED]
  auto_hoan_tat/mod2_navigator.py → inside_assign.py

## Import Cycles
- None detected.

## Communities (72 total, 24 thin omitted)

### Community 0 - "dom.js"
Cohesion: 0.02
Nodes (125): appSidebar, assignLogTerminal, badgeBypassPending, bannerDot, bannerHost, bannerText, btnAutoFetch, btnBackToBypass (+117 more)

### Community 1 - "inside_report_crawler.py"
Cohesion: 0.13
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
Cohesion: 0.13
Nodes (12): fetch_sheet_data(), get_radius_profile_dir(), InsideSpamPoolAutomation, is_deactive_ip_task(), is_pending(), is_processed(), load_cache(), normalize_nfc() (+4 more)

### Community 10 - "port_manage.js"
Cohesion: 0.06
Nodes (37): autoPortModeDot, autoPortModeText, badgePortPending, btnAutoPortModeToggle, btnClearPortCache, btnExportPortData, btnRefreshPortSheetData, btnStartAutoPort (+29 more)

### Community 11 - "inside_signal.py"
Cohesion: 0.09
Nodes (39): fetch_sheet_data(), get_reset_user_shds(), _is_auto_reset_cache_entry(), is_clear_success(), is_final_status(), load_cache(), normalize_nfc(), parse_vn_datetime() (+31 more)

### Community 12 - "route"
Cohesion: 0.06
Nodes (56): add_log(), _auto_orchestrator_loop(), _auto_reset_after_clear_loop(), clear_assign_cache(), clear_bypass_cache(), clear_bypass_nat_cache(), clear_clear_signal_cache(), clear_cls_cache() (+48 more)

### Community 13 - "release_inside_task"
Cohesion: 0.07
Nodes (27): release_inside_task(), try_acquire_inside_task(), fetch_sheet_data(), format_mybae_thao_tac(), bypass_nat_manual_login(), check_cached_contract_48h(), check_session_api(), export_cls_excel() (+19 more)

### Community 14 - "run_mybae_process"
Cohesion: 0.22
Nodes (8): is_final_row(), _auto_pending_assign(), _auto_pending_cls(), _auto_pending_generic(), _auto_pending_mybae(), _auto_pending_mybae_generic(), export_mybae_excel(), _lc()

### Community 16 - "clear_cls.js"
Cohesion: 0.06
Nodes (31): autoClsModeDot, autoClsModeIcon, autoClsModeText, badgeClsPending, btnAutoClsModeToggle, btnRefreshClsSheetData, btnRunAutoCls, chkClsSelectAll (+23 more)

### Community 17 - "validate_ticket_readonly"
Cohesion: 0.08
Nodes (13): _safe_log(), FeatureDisabledError, InsideSession, _sanitize_log(), NavigationContext, _emit(), evaluate_pbt_xac_minh_conditions(), is_already_completed() (+5 more)

### Community 18 - "bypass.js"
Cohesion: 0.09
Nodes (20): appsScriptCodeBlock, autoModeDot, autoModeIcon, autoModeText, btnAutoModeToggle, btnCloseWebhookGuide, btnCopyScriptCode, btnOkWebhookGuide (+12 more)

### Community 19 - "InsideBypassNatAutomation"
Cohesion: 0.18
Nodes (4): get_radius_profile_dir(), InsideBypassNatAutomation, save_cache(), worker_bypass_nat()

### Community 20 - "core_login.py"
Cohesion: 0.09
Nodes (16): atomic_write_json(), _cfg_keep_inside_session(), close_driver_and_clear_session(), extract_secret_from_qr_image(), get_active_account_info(), _get_file_lock(), get_totp_info(), inside_session_healthy() (+8 more)

### Community 22 - "sheet_reader.py"
Cohesion: 0.09
Nodes (17): _build_assign_adapter(), close_extra_ticket_tabs(), ExecutionResult, _emit(), export_results_csv(), _main_cli(), run_batch(), classify_ticket_type() (+9 more)

### Community 23 - "mod2_navigator.py"
Cohesion: 0.06
Nodes (17): _dump_dom_readonly(), _emit(), _format_probe_summary_txt(), _main_cli(), navigate_to_ticket(), NavigationError, open_ticket_readonly(), probe_ticket() (+9 more)

### Community 24 - "InsideClearClsAutomation"
Cohesion: 0.17
Nodes (4): format_cls_thao_tac(), InsideClearClsAutomation, norm_lower(), worker_cls()

### Community 26 - "_click_iam_login_button"
Cohesion: 0.17
Nodes (7): _click_iam_login_button(), _log(), _find_iam_button_candidate(), _is_iam_redirected(), _login_inside_via_iam_am(), log(), _should_use_iam_login()

### Community 27 - "auto_import_service.py"
Cohesion: 0.18
Nodes (7): _build_arg_parser(), create_readonly_kpi_engine(), ensure_infra_tables(), force_unlock_db(), _import_kpi_engine_class(), main(), seed_test_table()

### Community 29 - "inside_bypass.py"
Cohesion: 0.05
Nodes (31): Nguồn Dữ Liệu Phân Quyền Admin, Quy Tắc Phân Quyền Admin (Admin Privileges Rule), Quy Tắc Thực Thi, main(), _canonical_column(), _xp(), check_14d_hau_kiem_violation(), is_admin_staff() (+23 more)

### Community 30 - "ModernInsideFPTApp"
Cohesion: 0.23
Nodes (3): main(), ModernInsideFPTApp, worker()

### Community 31 - "unified_tabs.js"
Cohesion: 0.27
Nodes (12): filterRecords(), getRecordNumericId(), getRecordTimestamp(), getStaff(), isDateInRange(), isPendingSheetRow(), isRecordDone(), isRecordError() (+4 more)

### Community 32 - "FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc"
Cohesion: 0.17
Nodes (11): 1. Cách mở file dữ liệu trên Ubuntu:, 1. Khởi động ứng dụng, 2. Auto Lấy thông tin, 2. Cách chạy ứng dụng trên PC Ubuntu:, 3. Quản lý 2 Chế Độ Tài Khoản (Mặc định & Tùy chỉnh), 4. Xem chi tiết & Xuất Excel, 🧩 Cấu trúc component (Frontend), FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc (+3 more)

### Community 33 - "mod4_executor.py"
Cohesion: 0.18
Nodes (9): _read_footer_ticket_status(), _emit(), execute_complete_ticket(), _select_labeled_dropdown(), _select_table_cell_dropdown(), _update_thong_tin_bao_tri_if_needed(), _update_thong_tin_dich_vu(), _wait_for_popup() (+1 more)

### Community 35 - "renderBypassTable"
Cohesion: 0.23
Nodes (13): filterTableByStaff(), getRecordField(), loadBypassSheetData(), onActivate(), pollBypassStatus(), renderBypassTable(), renderTopFailedStaff(), runBypassProcess() (+5 more)

### Community 36 - "export_retrieval_excel"
Cohesion: 0.40
Nodes (3): export_retrieval_excel(), extract_record_date_str(), get_retrieval_list()

### Community 37 - "loadAssignSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerAssign(), _isAssignFinalDone(), loadAssignSheetData(), onActivate(), pollAssignStatus(), renderAssignTable(), runAssignProcess(), setAssignRunningState() (+2 more)

### Community 38 - "loadClsSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerBypass(), _isClsRecordDone(), loadClsSheetData(), onActivate(), pollClsStatus(), renderClsTable(), runClsProcess(), setClsRunningState() (+2 more)

### Community 43 - "load_config"
Cohesion: 0.16
Nodes (9): get_am_account_info(), get_radius_profile_dir(), load_config(), run_radius_login(), _get_am_credentials(), update_sheet_remote_assign(), update_sheet_remote_cls(), update_sheet_remote_bypass_nat() (+1 more)

### Community 47 - "create_inside_session"
Cohesion: 0.22
Nodes (7): AutoHoanTatSettings, create_inside_session(), _main_cli(), ProfileBusyError, _FakeDriver, TestMod1Auth, get_running_inside_task()

### Community 48 - "create_driver_with_retry"
Cohesion: 0.16
Nodes (7): build_chrome_options(), clean_profile_locks_and_orphans(), clear_inside_session(), create_driver_with_retry(), get_inside_profile_dir(), init_chrome_driver(), clear_all_sessions_api()

### Community 50 - "run_auto_import"
Cohesion: 0.12
Nodes (7): validate_date_str(), merge_tk_with_existing(), release_db_lock(), run_auto_import(), validate_and_parse_tk_file(), write_audit_log(), validate_downloaded_tk_excel()

### Community 52 - "load_settings"
Cohesion: 0.09
Nodes (13): is_enabled(), load_settings(), _parse_bool(), BatchRunSummary, main(), fetch_sheet_data(), TestWebApp, _fake_runner() (+5 more)

### Community 53 - "auto_import_routes.py"
Cohesion: 0.21
Nodes (10): get_default_date_range(), is_auto_import_enabled(), api_auto_import_run(), _worker(), api_auto_import_seed(), api_auto_import_status(), api_auto_import_toggle(), api_auto_import_unlock() (+2 more)

### Community 54 - "run_assign_process"
Cohesion: 0.40
Nodes (5): fetch_sheet_data(), is_final_thao_tac(), export_assign_excel(), get_assign_sheet_data(), run_assign_process()

### Community 55 - "_auto_orchestrator_cycle"
Cohesion: 0.15
Nodes (8): is_thu_hoi_port_task(), _auto_any_running(), _auto_orchestrator_cycle(), auto_overview_api(), _auto_task_states(), _is_record_today(), _other_inside_task_running(), start_port_auto()

### Community 58 - "InsideAssignAutomation"
Cohesion: 0.27
Nodes (3): clean_str(), InsideAssignAutomation, remove_accents()

### Community 61 - "json"
Cohesion: 0.14
Nodes (8): _acquire_cross_process_lock(), AuthError, _check_main_server_busy(), _is_pid_running(), _release_cross_process_lock(), SessionExpiredError, _append_audit_jsonl(), get_json()

### Community 64 - "_release_remaining_auto_attempts"
Cohesion: 0.12
Nodes (12): load_cache(), save_cache(), clear_auto_attempts(), download_full_log(), _ensure_bg_threads_on_request(), _flush_log_to_disk(), _log_flusher_loop(), _release_remaining_auto_attempts() (+4 more)

### Community 65 - "auto_import_config.py"
Cohesion: 0.21
Nodes (5): get_dataset_config(), get_db_url(), load_local_env(), _parse_bool(), _parse_partners()

### Community 66 - "hoan_tat_ptc_pbt.js"
Cohesion: 0.42
Nodes (9): escapeHtml(), getFilteredRecords(), loadSheet(), normUpper(), pollStatus(), renderLogs(), renderTable(), startRun() (+1 more)

### Community 67 - "fetch_sheet_data"
Cohesion: 0.32
Nodes (6): fetch_sheet_data(), is_bypass_final_status(), _apply_bypass_cache_to_record(), _auto_pending_bypass(), export_bypass_excel(), get_bypass_sheet_data()

## Knowledge Gaps
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InsideAssignAutomation` connect `InsideAssignAutomation` to `.log`, `json`, `sheet_reader.py`, `mod2_navigator.py`, `InsideClearClsAutomation`, `InsideMyBaeAutomation`, `inside_bypass.py`, `._visible`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `AutoHoanTatSettings` (e.g. with `fetch_sheet_data()` and `fetch_sheet_from_file()`) actually correct?**
  _`AutoHoanTatSettings` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `dom.js` be split into smaller, more focused modules?**
  _Cohesion score 0.015873015873015872 - nodes in this community are weakly interconnected._
- **Why does `InsideMyBaeAutomation` connect `InsideMyBaeAutomation` to `InsideAssignAutomation`, `release_inside_task`, `inside_bypass.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `inside_report_crawler.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12561576354679804 - nodes in this community are weakly interconnected._
- **Why does `_FakeAssignAdapter` connect `_FakeAssignAdapter` to `validate_ticket_readonly`, `json`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Should `mybae.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05152394775036284 - nodes in this community are weakly interconnected._