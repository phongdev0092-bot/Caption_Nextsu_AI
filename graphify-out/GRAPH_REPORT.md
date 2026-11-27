# Graph Report - Data Retrieval Tool  (2026-11-27)

## Corpus Check
- 63 files · ~137,930 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .bat 5, (none) 3, .css 2)

## Summary
- 1701 nodes · 3620 edges · 75 communities (50 shown, 25 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 124 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2e7d2b83`
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
- create_driver_with_retry
- port_manage.js
- inside_signal.py
- route
- release_inside_task
- run_mybae_process
- normalize_nfc
- clear_cls.js
- validate_ticket_readonly
- bypass.js
- atomic_write_json
- core_login.py
- InsideScraper
- orchestrator.py
- mod2_navigator.py
- load_config
- InsideAssignAutomation
- InsidePortAutomation
- auto_import_service.py
- InsideSignalAutomation
- auto_import_config.py
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
- time
- auto_import_routes.py
- run_auto_import
- get_default_date_range
- inside_port.py
- _auto_orchestrator_cycle
- _FakeAssignAdapter
- _FakeDriverExec
- run.sh
- acquire_db_lock
- _click_iam_login_button
- inside_bypass.py
- orchestrator.py
- hoan_tat_ptc_pbt.js
- inside_signal.py
- create_blueprint
- create_inside_session
- _load_log_from_disk
- start_background_threads
- norm_lower
- _should_use_iam_login

## God Nodes (most connected - your core abstractions)
1. `AutoHoanTatSettings` - 54 edges
2. `InsideAssignAutomation` - 40 edges
3. `add_log()` - 39 edges
4. `load_config()` - 34 edges
5. `create_inside_session()` - 31 edges
6. `open_ticket_readonly()` - 29 edges
7. `release_inside_task()` - 29 edges
8. `normalize_nfc()` - 29 edges
9. `load_settings()` - 28 edges
10. `create_blueprint()` - 27 edges

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

## Communities (75 total, 25 thin omitted)

### Community 0 - "dom.js"
Cohesion: 0.02
Nodes (125): appSidebar, assignLogTerminal, badgeBypassPending, bannerDot, bannerHost, bannerText, btnAutoFetch, btnBackToBypass (+117 more)

### Community 1 - "inside_report_crawler.py"
Cohesion: 0.11
Nodes (12): _click_element_safe(), _complete_iam_microsoft_login(), _emit_log(), fetch_tk_report_excel(), _fill_date_range(), _is_login_screen_present(), _login_inside_with_limit(), _navigate_to_inside_v5_report() (+4 more)

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

### Community 9 - "create_driver_with_retry"
Cohesion: 0.05
Nodes (24): build_chrome_options(), clean_profile_locks_and_orphans(), clear_inside_session(), create_driver_with_retry(), get_inside_profile_dir(), get_radius_profile_dir(), init_chrome_driver(), run_radius_login() (+16 more)

### Community 10 - "port_manage.js"
Cohesion: 0.06
Nodes (37): autoPortModeDot, autoPortModeText, badgePortPending, btnAutoPortModeToggle, btnClearPortCache, btnExportPortData, btnRefreshPortSheetData, btnStartAutoPort (+29 more)

### Community 11 - "inside_signal.py"
Cohesion: 0.10
Nodes (34): fetch_sheet_data(), get_reset_user_shds(), _is_auto_reset_cache_entry(), is_clear_success(), is_final_status(), load_cache(), normalize_nfc(), save_cache() (+26 more)

### Community 12 - "route"
Cohesion: 0.06
Nodes (60): save_config(), add_log(), _apply_bypass_cache_to_record(), clear_all_sessions_api(), clear_assign_cache(), clear_bypass_cache(), clear_bypass_nat_cache(), clear_clear_signal_cache() (+52 more)

### Community 13 - "release_inside_task"
Cohesion: 0.08
Nodes (25): invalidate_session(), release_inside_task(), try_acquire_inside_task(), bypass_nat_manual_login(), check_cached_contract_48h(), check_session_api(), make_task_logger(), _logger() (+17 more)

### Community 14 - "run_mybae_process"
Cohesion: 0.22
Nodes (8): is_final_row(), _auto_pending_assign(), _auto_pending_cls(), _auto_pending_generic(), _auto_pending_mybae(), _auto_pending_mybae_generic(), export_mybae_excel(), _lc()

### Community 15 - "normalize_nfc"
Cohesion: 0.15
Nodes (9): _main_cli(), classify_ticket_type(), fetch_sheet_data(), fetch_sheet_from_file(), _norm_match_key(), normalize_nfc(), parse_csv_text(), _strip_accents_lower() (+1 more)

### Community 16 - "clear_cls.js"
Cohesion: 0.06
Nodes (31): autoClsModeDot, autoClsModeIcon, autoClsModeText, badgeClsPending, btnAutoClsModeToggle, btnRefreshClsSheetData, btnRunAutoCls, chkClsSelectAll (+23 more)

### Community 17 - "validate_ticket_readonly"
Cohesion: 0.09
Nodes (13): _safe_log(), FeatureDisabledError, InsideSession, _sanitize_log(), NavigationContext, _emit(), evaluate_pbt_xac_minh_conditions(), is_already_completed() (+5 more)

### Community 18 - "bypass.js"
Cohesion: 0.09
Nodes (20): appsScriptCodeBlock, autoModeDot, autoModeIcon, autoModeText, btnAutoModeToggle, btnCloseWebhookGuide, btnCopyScriptCode, btnOkWebhookGuide (+12 more)

### Community 19 - "atomic_write_json"
Cohesion: 0.25
Nodes (8): atomic_write_json(), save_cache(), clear_auto_attempts(), _release_remaining_auto_attempts(), start_bypass_nat_task(), update_sheet_remote_bypass_nat(), worker_bypass_nat(), test_single_bypass_nat()

### Community 20 - "core_login.py"
Cohesion: 0.12
Nodes (6): main(), extract_secret_from_qr_image(), _get_file_lock(), parse_proto(), parse_varint(), extract_ptc_fields()

### Community 22 - "orchestrator.py"
Cohesion: 0.13
Nodes (10): AutoHoanTatSettings, is_enabled(), load_settings(), _parse_bool(), save_settings(), BatchRunSummary, main(), TestWebApp (+2 more)

### Community 23 - "mod2_navigator.py"
Cohesion: 0.06
Nodes (22): _dump_dom_readonly(), _emit(), _format_probe_summary_txt(), _has_valid_pbt_marker(), _main_cli(), navigate_to_ticket(), NavigationError, open_ticket_readonly() (+14 more)

### Community 24 - "load_config"
Cohesion: 0.13
Nodes (9): get_active_account_info(), get_am_account_info(), load_config(), InsideClearClsAutomation, _get_am_credentials(), transfer_contract_to_reset_sheet(), update_clear_sheet_auto_cap_lai_cell(), get_config() (+1 more)

### Community 25 - "InsideAssignAutomation"
Cohesion: 0.06
Nodes (6): format_assign_thao_tac(), InsideAssignAutomation, _xp(), InsideMyBaeAutomation, _pick_option(), worker_assign()

### Community 27 - "auto_import_service.py"
Cohesion: 0.18
Nodes (7): _build_arg_parser(), create_readonly_kpi_engine(), ensure_infra_tables(), force_unlock_db(), _import_kpi_engine_class(), main(), seed_test_table()

### Community 29 - "auto_import_config.py"
Cohesion: 0.22
Nodes (6): get_dataset_config(), get_db_url(), is_auto_import_enabled(), load_local_env(), _parse_bool(), _parse_partners()

### Community 30 - "ModernInsideFPTApp"
Cohesion: 0.23
Nodes (3): ModernInsideFPTApp, worker(), get_totp_info()

### Community 31 - "unified_tabs.js"
Cohesion: 0.27
Nodes (12): filterRecords(), getRecordNumericId(), getRecordTimestamp(), getStaff(), isDateInRange(), isPendingSheetRow(), isRecordDone(), isRecordError() (+4 more)

### Community 32 - "FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc"
Cohesion: 0.17
Nodes (11): 1. Cách mở file dữ liệu trên Ubuntu:, 1. Khởi động ứng dụng, 2. Auto Lấy thông tin, 2. Cách chạy ứng dụng trên PC Ubuntu:, 3. Quản lý 2 Chế Độ Tài Khoản (Mặc định & Tùy chỉnh), 4. Xem chi tiết & Xuất Excel, 🧩 Cấu trúc component (Frontend), FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc (+3 more)

### Community 33 - "mod4_executor.py"
Cohesion: 0.16
Nodes (9): _emit(), execute_complete_ticket(), _select_error_table_cell(), _select_labeled_dropdown(), _step4_expand_xem_them(), _step4a_my_bao(), _step4bc_nguyen_nhan_loi(), _step5_cap_nhat_ket_qua() (+1 more)

### Community 35 - "renderBypassTable"
Cohesion: 0.23
Nodes (13): filterTableByStaff(), getRecordField(), loadBypassSheetData(), onActivate(), pollBypassStatus(), renderBypassTable(), renderTopFailedStaff(), runBypassProcess() (+5 more)

### Community 36 - "writer"
Cohesion: 0.14
Nodes (9): is_final_thao_tac(), download_retrieval_template(), export_assign_excel(), export_cls_excel(), export_retrieval_excel(), extract_record_date_str(), get_retrieval_list(), run_assign_process() (+1 more)

### Community 37 - "loadAssignSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerAssign(), _isAssignFinalDone(), loadAssignSheetData(), onActivate(), pollAssignStatus(), renderAssignTable(), runAssignProcess(), setAssignRunningState() (+2 more)

### Community 38 - "loadClsSheetData"
Cohesion: 0.27
Nodes (10): checkAndAutoTriggerBypass(), _isClsRecordDone(), loadClsSheetData(), onActivate(), pollClsStatus(), renderClsTable(), runClsProcess(), setClsRunningState() (+2 more)

### Community 43 - "load_config"
Cohesion: 0.13
Nodes (8): main(), _cfg_keep_inside_session(), close_driver_and_clear_session(), inside_session_healthy(), _read_cookie_store(), restore_inside_cookies(), run_fpt_login(), save_inside_cookies()

### Community 47 - "AutoHoanTatSettings"
Cohesion: 0.13
Nodes (8): _acquire_cross_process_lock(), AuthError, _check_main_server_busy(), _is_pid_running(), ProfileBusyError, _release_cross_process_lock(), SessionExpiredError, get_json()

### Community 48 - "time"
Cohesion: 0.25
Nodes (10): _canonical_column(), clean_str(), fetch_sheet_data(), fetch_sheet_data(), fetch_sheet_data(), normalize_nfc(), remove_accents(), _canonical_column() (+2 more)

### Community 50 - "auto_import_routes.py"
Cohesion: 0.27
Nodes (8): api_auto_import_run(), _worker(), api_auto_import_seed(), api_auto_import_status(), api_auto_import_toggle(), api_auto_import_unlock(), _read_recent_audit_logs(), _update_env_flag()

### Community 52 - "run_auto_import"
Cohesion: 0.15
Nodes (6): merge_tk_with_existing(), release_db_lock(), run_auto_import(), validate_and_parse_tk_file(), write_audit_log(), validate_downloaded_tk_excel()

### Community 54 - "inside_port.py"
Cohesion: 0.17
Nodes (11): fetch_sheet_data(), is_pending(), is_processed(), is_thu_hoi_port_task(), load_cache(), normalize_nfc(), parse_tstc_info(), remove_accents() (+3 more)

### Community 55 - "_auto_orchestrator_cycle"
Cohesion: 0.17
Nodes (8): parse_vn_datetime(), _auto_any_running(), _auto_orchestrator_cycle(), _auto_orchestrator_loop(), auto_overview_api(), _auto_task_states(), _is_record_today(), _other_inside_task_running()

### Community 62 - "_click_iam_login_button"
Cohesion: 0.25
Nodes (5): _click_iam_login_button(), _log(), _is_iam_redirected(), _login_inside_via_iam_am(), log()

### Community 64 - "inside_bypass.py"
Cohesion: 0.17
Nodes (12): Nguồn Dữ Liệu Phân Quyền Admin, Quy Tắc Phân Quyền Admin (Admin Privileges Rule), Quy Tắc Thực Thi, check_14d_hau_kiem_violation(), is_admin_staff(), is_bypass_final_status(), load_admin_staff_set(), _normalize_msnv() (+4 more)

### Community 65 - "orchestrator.py"
Cohesion: 0.16
Nodes (9): _build_assign_adapter(), close_extra_ticket_tabs(), ExecutionResult, _append_audit_jsonl(), _emit(), export_results_csv(), run_batch(), _tee_log() (+1 more)

### Community 66 - "hoan_tat_ptc_pbt.js"
Cohesion: 0.32
Nodes (13): escapeHtml(), getFilteredRecords(), loadConfig(), loadSheet(), normUpper(), pollStatus(), renderLogs(), renderTable() (+5 more)

### Community 67 - "inside_signal.py"
Cohesion: 0.18
Nodes (7): fetch_sheet_data(), is_pending(), is_processed(), load_cache(), normalize_nfc(), remove_accents(), normalize_nfc()

### Community 68 - "create_blueprint"
Cohesion: 0.11
Nodes (16): create_blueprint(), api_config(), api_run(), api_save_settings(), api_sheet(), api_status(), _auto_scanner_loop(), _get_cfg() (+8 more)

### Community 69 - "create_inside_session"
Cohesion: 0.18
Nodes (5): create_inside_session(), _main_cli(), _FakeDriver, TestMod1Auth, get_running_inside_task()

### Community 72 - "start_background_threads"
Cohesion: 0.18
Nodes (6): _auto_reset_after_clear_loop(), download_full_log(), _ensure_bg_threads_on_request(), _flush_log_to_disk(), _log_flusher_loop(), start_background_threads()

## Knowledge Gaps
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InsideAssignAutomation` connect `InsideAssignAutomation` to `orchestrator.py`, `AutoHoanTatSettings`, `time`, `mod2_navigator.py`, `load_config`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `AutoHoanTatSettings` (e.g. with `create_blueprint()` and `_RunState`) actually correct?**
  _`AutoHoanTatSettings` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Should `dom.js` be split into smaller, more focused modules?**
  _Cohesion score 0.015873015873015872 - nodes in this community are weakly interconnected._
- **Why does `InsideScraper` connect `InsideScraper` to `_should_use_iam_login`, `load_config`, `route`, `release_inside_task`, `core_login.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Should `inside_report_crawler.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11494252873563218 - nodes in this community are weakly interconnected._
- **Why does `load_config()` connect `load_config` to `InsideBypassAutomation`, `create_driver_with_retry`, `load_config`, `route`, `release_inside_task`, `inside_signal.py`, `atomic_write_json`, `core_login.py`, `InsideScraper`, `InsidePortAutomation`, `InsideSignalAutomation`, `ModernInsideFPTApp`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Should `mybae.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05152394775036284 - nodes in this community are weakly interconnected._