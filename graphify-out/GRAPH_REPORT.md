# Graph Report - Data Retrieval Tool  (2026-11-19)

## Corpus Check
- 63 files · ~135,973 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: .bat 5, (none) 3, .css 2)

## Summary
- 1682 nodes · 3553 edges · 68 communities (44 shown, 24 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 116 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8da28369`
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
- normalize_nfc
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
- invalidate_session
- auto_import_routes.py
- merge_tk_with_existing
- get_default_date_range
- atomic_write_json
- _auto_orchestrator_cycle
- _FakeAssignAdapter
- _FakeDriverExec
- run.sh
- acquire_db_lock
- _click_iam_login_button
- hoan_tat_ptc_pbt.js
- create_blueprint
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

## Communities (68 total, 24 thin omitted)

### Community 0 - "dom.js"
Cohesion: 0.02
Nodes (125): appSidebar, assignLogTerminal, badgeBypassPending, bannerDot, bannerHost, bannerText, btnAutoFetch, btnBackToBypass (+117 more)

### Community 1 - "inside_report_crawler.py"
Cohesion: 0.11
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
Cohesion: 0.10
Nodes (36): fetch_sheet_data(), get_reset_user_shds(), _is_auto_reset_cache_entry(), is_clear_success(), is_final_status(), load_cache(), normalize_nfc(), parse_vn_datetime() (+28 more)

### Community 12 - "route"
Cohesion: 0.06
Nodes (60): save_config(), add_log(), _apply_bypass_cache_to_record(), _auto_reset_after_clear_loop(), clear_all_sessions_api(), clear_assign_cache(), clear_bypass_cache(), clear_bypass_nat_cache() (+52 more)

### Community 13 - "release_inside_task"
Cohesion: 0.08
Nodes (24): release_inside_task(), try_acquire_inside_task(), fetch_sheet_data(), bypass_nat_manual_login(), check_cached_contract_48h(), check_session_api(), get_cls_sheet_data(), make_task_logger() (+16 more)

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
Nodes (12): _safe_log(), InsideSession, _sanitize_log(), NavigationContext, _emit(), evaluate_pbt_xac_minh_conditions(), is_already_completed(), _norm_ws_lower() (+4 more)

### Community 18 - "bypass.js"
Cohesion: 0.09
Nodes (20): appsScriptCodeBlock, autoModeDot, autoModeIcon, autoModeText, btnAutoModeToggle, btnCloseWebhookGuide, btnCopyScriptCode, btnOkWebhookGuide (+12 more)

### Community 19 - "InsideBypassNatAutomation"
Cohesion: 0.13
Nodes (7): get_radius_profile_dir(), run_radius_login(), get_radius_profile_dir(), InsideBypassNatAutomation, save_cache(), update_sheet_remote_bypass_nat(), worker_bypass_nat()

### Community 20 - "core_login.py"
Cohesion: 0.05
Nodes (37): Nguồn Dữ Liệu Phân Quyền Admin, Quy Tắc Phân Quyền Admin (Admin Privileges Rule), Quy Tắc Thực Thi, extract_secret_from_qr_image(), _get_file_lock(), parse_proto(), parse_varint(), _canonical_column() (+29 more)

### Community 22 - "orchestrator.py"
Cohesion: 0.09
Nodes (15): is_enabled(), load_settings(), _parse_bool(), _build_assign_adapter(), close_extra_ticket_tabs(), _append_audit_jsonl(), BatchRunSummary, _emit() (+7 more)

### Community 23 - "mod2_navigator.py"
Cohesion: 0.05
Nodes (23): AuthError, FeatureDisabledError, SessionExpiredError, _dump_dom_readonly(), _emit(), _format_probe_summary_txt(), _main_cli(), navigate_to_ticket() (+15 more)

### Community 24 - "InsideClearClsAutomation"
Cohesion: 0.12
Nodes (6): _cfg_keep_inside_session(), close_driver_and_clear_session(), invalidate_session(), InsideClearClsAutomation, update_sheet_remote_cls(), worker_cls()

### Community 25 - "InsideAssignAutomation"
Cohesion: 0.06
Nodes (8): clean_str(), format_assign_thao_tac(), InsideAssignAutomation, _xp(), remove_accents(), InsideMyBaeAutomation, _pick_option(), worker_assign()

### Community 27 - "auto_import_service.py"
Cohesion: 0.13
Nodes (12): _worker(), _build_arg_parser(), create_readonly_kpi_engine(), ensure_infra_tables(), force_unlock_db(), _import_kpi_engine_class(), main(), release_db_lock() (+4 more)

### Community 29 - "auto_import_config.py"
Cohesion: 0.22
Nodes (6): get_dataset_config(), get_db_url(), is_auto_import_enabled(), load_local_env(), _parse_bool(), _parse_partners()

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
Cohesion: 0.16
Nodes (9): _emit(), execute_complete_ticket(), ExecutionResult, _select_labeled_dropdown(), _select_table_cell_dropdown(), _update_thong_tin_bao_tri_if_needed(), _update_thong_tin_dich_vu(), _wait_for_popup() (+1 more)

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
Nodes (12): main(), get_active_account_info(), get_am_account_info(), inside_session_healthy(), load_config(), _read_cookie_store(), restore_inside_cookies(), run_fpt_login() (+4 more)

### Community 47 - "AutoHoanTatSettings"
Cohesion: 0.11
Nodes (12): AutoHoanTatSettings, _acquire_cross_process_lock(), _check_main_server_busy(), create_inside_session(), _is_pid_running(), _main_cli(), ProfileBusyError, _release_cross_process_lock() (+4 more)

### Community 48 - "invalidate_session"
Cohesion: 0.18
Nodes (6): build_chrome_options(), clean_profile_locks_and_orphans(), clear_inside_session(), create_driver_with_retry(), get_inside_profile_dir(), init_chrome_driver()

### Community 50 - "auto_import_routes.py"
Cohesion: 0.29
Nodes (7): api_auto_import_run(), api_auto_import_seed(), api_auto_import_status(), api_auto_import_toggle(), api_auto_import_unlock(), _read_recent_audit_logs(), _update_env_flag()

### Community 54 - "atomic_write_json"
Cohesion: 0.16
Nodes (12): atomic_write_json(), fetch_sheet_data(), is_thu_hoi_port_task(), load_cache(), save_cache(), clear_auto_attempts(), get_port_sheet(), _release_remaining_auto_attempts() (+4 more)

### Community 55 - "_auto_orchestrator_cycle"
Cohesion: 0.10
Nodes (12): _auto_any_running(), _auto_orchestrator_cycle(), _auto_orchestrator_loop(), auto_overview_api(), _auto_task_states(), download_full_log(), _ensure_bg_threads_on_request(), _flush_log_to_disk() (+4 more)

### Community 62 - "_click_iam_login_button"
Cohesion: 0.17
Nodes (7): _click_iam_login_button(), _log(), _find_iam_button_candidate(), _is_iam_redirected(), _login_inside_via_iam_am(), log(), _should_use_iam_login()

### Community 66 - "hoan_tat_ptc_pbt.js"
Cohesion: 0.42
Nodes (9): escapeHtml(), getFilteredRecords(), loadSheet(), normUpper(), pollStatus(), renderLogs(), renderTable(), startRun() (+1 more)

### Community 68 - "create_blueprint"
Cohesion: 0.12
Nodes (9): create_blueprint(), api_config(), api_run(), _worker(), _on_progress(), api_sheet(), _get_cfg(), index() (+1 more)

## Knowledge Gaps
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InsideAssignAutomation` connect `InsideAssignAutomation` to `InsideClearClsAutomation`, `core_login.py`, `orchestrator.py`, `mod2_navigator.py`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `AutoHoanTatSettings` (e.g. with `fetch_sheet_data()` and `fetch_sheet_from_file()`) actually correct?**
  _`AutoHoanTatSettings` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `dom.js` be split into smaller, more focused modules?**
  _Cohesion score 0.015873015873015872 - nodes in this community are weakly interconnected._
- **Why does `load_config()` connect `load_config` to `InsideBypassAutomation`, `inside_spampool.py`, `inside_signal.py`, `route`, `release_inside_task`, `InsideBypassNatAutomation`, `core_login.py`, `InsideScraper`, `atomic_write_json`, `InsideClearClsAutomation`, `InsidePortAutomation`, `InsideSignalAutomation`, `ModernInsideFPTApp`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Should `inside_report_crawler.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11088709677419355 - nodes in this community are weakly interconnected._
- **Why does `InsideBypassAutomation` connect `InsideBypassAutomation` to `core_login.py`, `release_inside_task`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `mybae.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05152394775036284 - nodes in this community are weakly interconnected._