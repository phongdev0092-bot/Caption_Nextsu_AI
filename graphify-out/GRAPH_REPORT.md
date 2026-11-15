# Graph Report - Data Retrieval Tool  (2026-11-15)

## Corpus Check
- 53 files · ~114,759 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .bat 4, (none) 2, .example 1)

## Summary
- 1340 nodes · 2685 edges · 67 communities (40 shown, 27 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 98 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f8af72b4`
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
- load_config
- run_mybae_process
- norm_lower
- clear_cls.js
- os
- bypass.js
- InsideBypassNatAutomation
- InsideScraper
- core_login.py
- InsideBypassAutomation
- InsidePortAutomation
- InsideMyBaeAutomation
- time
- run_auto_import
- InsideSignalAutomation
- save_records_zstd
- ModernInsideFPTApp
- unified_tabs.js
- FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc
- .log
- inside_report_crawler.py
- run_radius_login
- auto_import_config.py
- run_fpt_login
- remove_accents
- import.js
- shell.js
- tabs.js
- create_driver_with_retry
- Template_Danh_Sach_Hop_Dong_fd19b39a.md
- auto_import_service.py
- _click_iam_login_button
- auto_import_routes.py
- get_default_date_range
- force_unlock_db
- run_assign_process
- download_full_log
- acquire_db_lock
- extract_record_date_str
- close_driver_and_clear_session
- run.sh
- auto_overview_api
- _load_log_from_disk
- trigger_check_72h_api

## God Nodes (most connected - your core abstractions)
1. `add_log()` - 70 edges
2. `load_config()` - 35 edges
3. `InsideAssignAutomation` - 34 edges
4. `run_fpt_login()` - 25 edges
5. `fetch_tk_report_excel()` - 22 edges
6. `run_auto_import()` - 21 edges
7. `fetch_sheet_data()` - 18 edges
8. `InsideMyBaeAutomation` - 18 edges
9. `InsideScraper` - 17 edges
10. `create_driver_with_retry()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Quy Tắc Thực Thi` --references--> `check_14d_hau_kiem_violation()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `Quy Tắc Thực Thi` --references--> `is_admin_staff()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `pollBypassStatus()` --indirect_call--> `checkAndAutoTriggerCls()`  [INFERRED]
  static/js/components/bypass.js → static/js/components/clear_cls.js
- `pollClsStatus()` --indirect_call--> `checkAndAutoTriggerBypass()`  [INFERRED]
  static/js/components/clear_cls.js → static/js/components/bypass.js
- `_lc()` --calls--> `normalize_nfc()`  [EXTRACTED]
  server.py → inside_signal.py

## Import Cycles
- None detected.

## Communities (67 total, 27 thin omitted)

### Community 0 - "dom.js"
Cohesion: 0.02
Nodes (125): appSidebar, assignLogTerminal, badgeBypassPending, bannerDot, bannerHost, bannerText, btnAutoFetch, btnBackToBypass (+117 more)

### Community 1 - "inside_report_crawler.py"
Cohesion: 0.19
Nodes (8): _complete_iam_microsoft_login(), _create_crawler_driver(), _emit_log(), fetch_tk_report_excel(), _login_inside_with_limit(), _navigate_to_inside_v5_report(), _switch_to_frame_containing(), _wait_download_complete()

### Community 2 - "mybae.js"
Cohesion: 0.06
Nodes (45): autoMyBaeModeDot, autoMyBaeModeText, badgeMyBaePending, btnAutoMyBaeModeToggle, btnClearMyBaeCache, btnClearMyBaeLogs, btnExportMyBaeData, btnRefreshMyBaeSheetData (+37 more)

### Community 3 - "settings.js"
Cohesion: 0.05
Nodes (40): pollStatus(), setLoginButtonState(), formatDateDataDisplay(), initialTodayStr, loadRetrievalData(), openDetailModal(), renderContractTags(), renderRetrievalTable() (+32 more)

### Community 4 - "assign.js"
Cohesion: 0.05
Nodes (44): assignProgressBar, assignProgressTracker, assignRunIcon, assignRunText, assignSelectedCountText, assignSpinner, assignStatDone, assignStatError (+36 more)

### Community 5 - "clear_signal.js"
Cohesion: 0.05
Nodes (44): autoClearSignalModeDot, autoClearSignalModeIcon, autoClearSignalModeText, badgeClearSignalPending, btnAutoClearSignalModeToggle, btnClearClearSignalCache, btnClearClearSignalLogs, btnExportClearSignalData (+36 more)

### Community 6 - "reset_signal.js"
Cohesion: 0.05
Nodes (44): autoResetSignalModeDot, autoResetSignalModeIcon, autoResetSignalModeText, badgeResetSignalPending, btnAutoResetSignalModeToggle, btnClearResetSignalCache, btnClearResetSignalLogs, btnExportResetSignalData (+36 more)

### Community 7 - "bypass_nat.js"
Cohesion: 0.06
Nodes (42): autoBypassNatModeDot, autoBypassNatModeText, badgeBypassNatPending, btnAutoBypassNatModeToggle, btnBypassNatLogin, btnClearBypassNatCache, btnExportBypassNatData, btnRefreshBypassNatSheetData (+34 more)

### Community 8 - "spampool.js"
Cohesion: 0.06
Nodes (41): autoSpamPoolModeDot, autoSpamPoolModeText, badgeSpamPoolPending, btnAutoSpamPoolModeToggle, btnClearSpamPoolCache, btnClearSpamPoolLogs, btnExportSpamPoolData, btnRefreshSpamPoolSheetData (+33 more)

### Community 9 - "inside_spampool.py"
Cohesion: 0.16
Nodes (8): get_radius_profile_dir(), InsideSpamPoolAutomation, is_deactive_ip_task(), is_pending(), load_cache(), save_cache(), worker_spampool(), test_single_spampool()

### Community 10 - "port_manage.js"
Cohesion: 0.06
Nodes (37): autoPortModeDot, autoPortModeText, badgePortPending, btnAutoPortModeToggle, btnClearPortCache, btnExportPortData, btnRefreshPortSheetData, btnStartAutoPort (+29 more)

### Community 11 - "inside_signal.py"
Cohesion: 0.10
Nodes (34): fetch_sheet_data(), get_reset_user_shds(), _is_auto_reset_cache_entry(), is_clear_success(), is_final_status(), load_cache(), normalize_nfc(), parse_vn_datetime() (+26 more)

### Community 12 - "route"
Cohesion: 0.06
Nodes (63): add_log(), _auto_orchestrator_loop(), _auto_pending_clear_signal(), _auto_pending_reset_signal(), _auto_pending_signal(), bypass_nat_manual_login(), check_session_api(), clear_all_sessions_api() (+55 more)

### Community 13 - "load_config"
Cohesion: 0.14
Nodes (18): get_active_account_info(), load_config(), save_config(), transfer_contract_to_reset_sheet(), close(), get_config(), get_otp(), run_bypass_process() (+10 more)

### Community 14 - "run_mybae_process"
Cohesion: 0.14
Nodes (13): is_final_row(), _auto_any_running(), _auto_pending_assign(), _auto_pending_cls(), _auto_pending_generic(), _auto_pending_mybae(), _auto_pending_mybae_generic(), export_mybae_excel() (+5 more)

### Community 16 - "clear_cls.js"
Cohesion: 0.06
Nodes (37): autoClsModeDot, autoClsModeIcon, autoClsModeText, badgeClsPending, btnAutoClsModeToggle, btnRefreshClsSheetData, btnRunAutoCls, checkAndAutoTriggerCls() (+29 more)

### Community 17 - "os"
Cohesion: 0.22
Nodes (4): clear_inside_session(), get_radius_profile_dir(), invalidate_session(), get_port_profile_dir()

### Community 18 - "bypass.js"
Cohesion: 0.09
Nodes (33): appsScriptCodeBlock, autoModeDot, autoModeIcon, autoModeText, btnAutoModeToggle, btnCloseWebhookGuide, btnCopyScriptCode, btnOkWebhookGuide (+25 more)

### Community 19 - "InsideBypassNatAutomation"
Cohesion: 0.12
Nodes (11): fetch_sheet_data(), get_radius_profile_dir(), InsideBypassNatAutomation, is_pending(), is_processed(), load_cache(), remove_accents(), save_cache() (+3 more)

### Community 21 - "InsideScraper"
Cohesion: 0.13
Nodes (4): _should_use_iam_login(), InsideScraper, check_cached_contract_48h(), worker()

### Community 22 - "core_login.py"
Cohesion: 0.23
Nodes (4): extract_secret_from_qr_image(), get_totp_info(), parse_proto(), parse_varint()

### Community 24 - "InsidePortAutomation"
Cohesion: 0.23
Nodes (3): InsidePortAutomation, save_cache(), test_single_port()

### Community 26 - "time"
Cohesion: 0.06
Nodes (41): Nguồn Dữ Liệu Phân Quyền Admin, Quy Tắc Phân Quyền Admin (Admin Privileges Rule), Quy Tắc Thực Thi, _canonical_column(), clean_str(), fetch_sheet_data(), format_assign_thao_tac(), check_14d_hau_kiem_violation() (+33 more)

### Community 27 - "run_auto_import"
Cohesion: 0.14
Nodes (7): _worker(), merge_tk_with_existing(), release_db_lock(), run_auto_import(), validate_and_parse_tk_file(), write_audit_log(), validate_downloaded_tk_excel()

### Community 29 - "save_records_zstd"
Cohesion: 0.40
Nodes (3): clear_retrieval_records(), load_records_zstd(), save_records_zstd()

### Community 30 - "ModernInsideFPTApp"
Cohesion: 0.23
Nodes (3): main(), ModernInsideFPTApp, worker()

### Community 31 - "unified_tabs.js"
Cohesion: 0.27
Nodes (12): filterRecords(), getRecordNumericId(), getRecordTimestamp(), getStaff(), isDateInRange(), isPendingSheetRow(), isRecordDone(), isRecordError() (+4 more)

### Community 32 - "FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc"
Cohesion: 0.17
Nodes (11): 1. Cách mở file dữ liệu trên Ubuntu:, 1. Khởi động ứng dụng, 2. Auto Lấy thông tin, 2. Cách chạy ứng dụng trên PC Ubuntu:, 3. Quản lý 2 Chế Độ Tài Khoản (Mặc định & Tùy chỉnh), 4. Xem chi tiết & Xuất Excel, 🧩 Cấu trúc component (Frontend), FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc (+3 more)

### Community 34 - "inside_report_crawler.py"
Cohesion: 0.14
Nodes (5): _click_element_safe(), _fill_date_range(), _is_login_screen_present(), _select_dropdown_near_label(), SessionExpiredError

### Community 35 - "run_radius_login"
Cohesion: 0.33
Nodes (3): get_am_account_info(), run_radius_login(), _get_am_credentials()

### Community 37 - "auto_import_config.py"
Cohesion: 0.22
Nodes (6): get_dataset_config(), get_db_url(), is_auto_import_enabled(), load_local_env(), _parse_bool(), _parse_partners()

### Community 38 - "run_fpt_login"
Cohesion: 0.18
Nodes (6): main(), inside_session_healthy(), _read_cookie_store(), restore_inside_cookies(), run_fpt_login(), save_inside_cookies()

### Community 43 - "create_driver_with_retry"
Cohesion: 0.20
Nodes (5): build_chrome_options(), clean_profile_locks_and_orphans(), create_driver_with_retry(), get_inside_profile_dir(), init_chrome_driver()

### Community 47 - "auto_import_service.py"
Cohesion: 0.18
Nodes (7): api_auto_import_seed(), _build_arg_parser(), create_readonly_kpi_engine(), _import_kpi_engine_class(), main(), seed_test_table(), get_json()

### Community 48 - "_click_iam_login_button"
Cohesion: 0.20
Nodes (6): _click_iam_login_button(), _log(), _find_iam_button_candidate(), _is_iam_redirected(), _login_inside_via_iam_am(), log()

### Community 49 - "auto_import_routes.py"
Cohesion: 0.25
Nodes (5): api_auto_import_run(), api_auto_import_status(), api_auto_import_toggle(), _read_recent_audit_logs(), _update_env_flag()

### Community 52 - "force_unlock_db"
Cohesion: 0.40
Nodes (3): api_auto_import_unlock(), ensure_infra_tables(), force_unlock_db()

### Community 53 - "run_assign_process"
Cohesion: 0.25
Nodes (7): is_final_thao_tac(), clear_assign_cache(), clear_auto_attempts(), export_assign_excel(), run_assign_process(), update_sheet_remote_assign(), worker_assign()

### Community 54 - "download_full_log"
Cohesion: 0.40
Nodes (3): download_full_log(), _flush_log_to_disk(), _log_flusher_loop()

### Community 56 - "extract_record_date_str"
Cohesion: 0.40
Nodes (3): export_retrieval_excel(), extract_record_date_str(), get_retrieval_list()

## Knowledge Gaps
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load_config()` connect `load_config` to `.log`, `run_radius_login`, `run_fpt_login`, `inside_spampool.py`, `inside_signal.py`, `route`, `run_mybae_process`, `auto_import_service.py`, `InsideBypassNatAutomation`, `InsideScraper`, `core_login.py`, `InsideBypassAutomation`, `InsidePortAutomation`, `run_assign_process`, `close_driver_and_clear_session`, `InsideSignalAutomation`, `ModernInsideFPTApp`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `add_log()` (e.g. with `clear_all_sessions_api()` and `worker_assign()`) actually correct?**
  _`add_log()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `dom.js` be split into smaller, more focused modules?**
  _Cohesion score 0.015873015873015872 - nodes in this community are weakly interconnected._
- **Why does `pollClsStatus()` connect `clear_cls.js` to `bypass.js`, `settings.js`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `mybae.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05697278911564626 - nodes in this community are weakly interconnected._
- **Why does `add_log()` connect `route` to `.log`, `inside_spampool.py`, `inside_signal.py`, `load_config`, `run_mybae_process`, `InsideBypassNatAutomation`, `run_assign_process`, `InsideScraper`, `InsidePortAutomation`, `save_records_zstd`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `settings.js` be split into smaller, more focused modules?**
  _Cohesion score 0.04964539007092199 - nodes in this community are weakly interconnected._