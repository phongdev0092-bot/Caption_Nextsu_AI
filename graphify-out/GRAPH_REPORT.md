# Graph Report - Data Retrieval Tool  (2026-11-14)

## Corpus Check
- 53 files · ~116,224 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: .bat 4, (none) 2, .example 1)

## Summary
- 1317 nodes · 2608 edges · 62 communities (41 shown, 21 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 96 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d99e1f0e`
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
- InsideClearClsAutomation
- clear_cls.js
- core_login.py
- bypass.js
- InsideBypassNatAutomation
- InsideScraper
- InsideMyBaeAutomation
- InsideBypassAutomation
- InsidePortAutomation
- inside_port.py
- inside_bypass.py
- run_auto_import
- InsideAssignAutomation
- auto_import_config.py
- ModernInsideFPTApp
- unified_tabs.js
- FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc
- inside_bypass_nat.py
- auto_import_service.py
- load_config
- fetch_sheet_data
- renderBypassTable
- .log
- os
- import.js
- shell.js
- tabs.js
- renderClsTable
- Template_Danh_Sach_Hop_Dong_fd19b39a.md
- inside_bypass.py
- save_records_zstd
- _auto_orchestrator_cycle
- inside_signal.py
- validate_date_str
- acquire_db_lock
- run_assign_process
- download_full_log
- checkAndAutoTriggerBypass
- _load_log_from_disk
- is_bypass_final_status

## God Nodes (most connected - your core abstractions)
1. `add_log()` - 70 edges
2. `load_config()` - 35 edges
3. `InsideAssignAutomation` - 34 edges
4. `run_fpt_login()` - 22 edges
5. `run_auto_import()` - 21 edges
6. `fetch_tk_report_excel()` - 20 edges
7. `InsideMyBaeAutomation` - 18 edges
8. `create_driver_with_retry()` - 17 edges
9. `InsideScraper` - 17 edges
10. `fetch_sheet_data()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `Quy Tắc Thực Thi` --references--> `check_14d_hau_kiem_violation()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `Quy Tắc Thực Thi` --references--> `is_admin_staff()`  [INFERRED]
  .agents/rules/admin_privileges.md → inside_bypass.py
- `main()` --calls--> `run_fpt_login()`  [EXTRACTED]
  cli_login.py → core_login.py
- `pollBypassStatus()` --indirect_call--> `checkAndAutoTriggerCls()`  [INFERRED]
  static/js/components/bypass.js → static/js/components/clear_cls.js
- `pollClsStatus()` --indirect_call--> `checkAndAutoTriggerBypass()`  [INFERRED]
  static/js/components/clear_cls.js → static/js/components/bypass.js

## Import Cycles
- None detected.

## Communities (62 total, 21 thin omitted)

### Community 0 - "dom.js"
Cohesion: 0.02
Nodes (125): appSidebar, assignLogTerminal, badgeBypassPending, bannerDot, bannerHost, bannerText, btnAutoFetch, btnBackToBypass (+117 more)

### Community 1 - "inside_report_crawler.py"
Cohesion: 0.11
Nodes (14): _click_element_safe(), _complete_iam_microsoft_login(), _create_crawler_driver(), _emit_log(), fetch_tk_report_excel(), _fill_date_range(), _get_am_credentials(), _is_login_screen_present() (+6 more)

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
Nodes (43): autoClearSignalModeDot, autoClearSignalModeIcon, autoClearSignalModeText, badgeClearSignalPending, btnAutoClearSignalModeToggle, btnClearClearSignalCache, btnClearClearSignalLogs, btnExportClearSignalData (+35 more)

### Community 6 - "reset_signal.js"
Cohesion: 0.05
Nodes (43): autoResetSignalModeDot, autoResetSignalModeIcon, autoResetSignalModeText, badgeResetSignalPending, btnAutoResetSignalModeToggle, btnClearResetSignalCache, btnClearResetSignalLogs, btnExportResetSignalData (+35 more)

### Community 7 - "bypass_nat.js"
Cohesion: 0.06
Nodes (42): autoBypassNatModeDot, autoBypassNatModeText, badgeBypassNatPending, btnAutoBypassNatModeToggle, btnBypassNatLogin, btnClearBypassNatCache, btnExportBypassNatData, btnRefreshBypassNatSheetData (+34 more)

### Community 8 - "spampool.js"
Cohesion: 0.06
Nodes (41): autoSpamPoolModeDot, autoSpamPoolModeText, badgeSpamPoolPending, btnAutoSpamPoolModeToggle, btnClearSpamPoolCache, btnClearSpamPoolLogs, btnExportSpamPoolData, btnRefreshSpamPoolSheetData (+33 more)

### Community 9 - "inside_spampool.py"
Cohesion: 0.14
Nodes (10): fetch_sheet_data(), InsideSpamPoolAutomation, is_deactive_ip_task(), is_pending(), is_processed(), load_cache(), remove_accents(), save_cache() (+2 more)

### Community 10 - "port_manage.js"
Cohesion: 0.06
Nodes (37): autoPortModeDot, autoPortModeText, badgePortPending, btnAutoPortModeToggle, btnClearPortCache, btnExportPortData, btnRefreshPortSheetData, btnStartAutoPort (+29 more)

### Community 11 - "inside_signal.py"
Cohesion: 0.15
Nodes (7): invalidate_session(), InsideSignalAutomation, transfer_contract_to_reset_sheet(), close(), update_cache_record(), worker_clear_signal(), worker_reset_signal()

### Community 12 - "route"
Cohesion: 0.06
Nodes (37): run.sh script, _apply_bypass_cache_to_record(), check_session_api(), clear_all_sessions_api(), download_retrieval_template(), export_bypass_excel(), export_cls_excel(), export_retrieval_excel() (+29 more)

### Community 13 - "add_log"
Cohesion: 0.07
Nodes (34): add_log(), bypass_nat_manual_login(), clear_assign_cache(), clear_auto_attempts(), clear_bypass_cache(), clear_bypass_nat_cache(), clear_clear_signal_cache(), clear_cls_cache() (+26 more)

### Community 14 - "run_mybae_process"
Cohesion: 0.14
Nodes (13): is_final_row(), _auto_any_running(), _auto_pending_assign(), _auto_pending_cls(), _auto_pending_generic(), _auto_pending_mybae(), _auto_pending_mybae_generic(), export_mybae_excel() (+5 more)

### Community 16 - "clear_cls.js"
Cohesion: 0.06
Nodes (28): autoClsModeDot, autoClsModeIcon, autoClsModeText, badgeClsPending, btnAutoClsModeToggle, btnRefreshClsSheetData, btnRunAutoCls, chkClsSelectAll (+20 more)

### Community 17 - "core_login.py"
Cohesion: 0.09
Nodes (16): _cfg_keep_inside_session(), close_driver_and_clear_session(), extract_secret_from_qr_image(), get_am_account_info(), get_totp_info(), inside_session_healthy(), _login_inside_via_iam_am(), parse_proto() (+8 more)

### Community 18 - "bypass.js"
Cohesion: 0.09
Nodes (16): appsScriptCodeBlock, autoModeDot, autoModeIcon, autoModeText, btnAutoModeToggle, btnCloseWebhookGuide, btnCopyScriptCode, btnOkWebhookGuide (+8 more)

### Community 19 - "InsideBypassNatAutomation"
Cohesion: 0.18
Nodes (6): get_radius_profile_dir(), InsideBypassNatAutomation, load_cache(), save_cache(), worker_bypass_nat(), test_single_bypass_nat()

### Community 21 - "InsideScraper"
Cohesion: 0.15
Nodes (3): InsideScraper, check_cached_contract_48h(), worker()

### Community 25 - "inside_port.py"
Cohesion: 0.18
Nodes (9): fetch_sheet_data(), is_pending(), is_processed(), load_cache(), normalize_nfc(), parse_tstc_info(), remove_accents(), save_cache() (+1 more)

### Community 26 - "inside_bypass.py"
Cohesion: 0.26
Nodes (9): _canonical_column(), fetch_sheet_data(), fetch_sheet_data(), format_cls_thao_tac(), norm_lower(), normalize_nfc(), _canonical_column(), fetch_sheet_data() (+1 more)

### Community 27 - "run_auto_import"
Cohesion: 0.13
Nodes (8): api_auto_import_run(), _worker(), merge_tk_with_existing(), release_db_lock(), run_auto_import(), validate_and_parse_tk_file(), write_audit_log(), validate_downloaded_tk_excel()

### Community 28 - "InsideAssignAutomation"
Cohesion: 0.19
Nodes (4): clean_str(), InsideAssignAutomation, _xp(), remove_accents()

### Community 29 - "auto_import_config.py"
Cohesion: 0.13
Nodes (12): get_dataset_config(), get_default_date_range(), is_auto_import_enabled(), load_local_env(), _parse_bool(), _parse_partners(), api_auto_import_seed(), api_auto_import_status() (+4 more)

### Community 31 - "unified_tabs.js"
Cohesion: 0.29
Nodes (9): filterRecords(), getRecordTimestamp(), getStaff(), isDateInRange(), isRecordDone(), parseRecordDate(), sortRecordsNewestFirst(), updateDailyChart() (+1 more)

### Community 32 - "FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc"
Cohesion: 0.17
Nodes (11): 1. Cách mở file dữ liệu trên Ubuntu:, 1. Khởi động ứng dụng, 2. Auto Lấy thông tin, 2. Cách chạy ứng dụng trên PC Ubuntu:, 3. Quản lý 2 Chế Độ Tài Khoản (Mặc định & Tùy chỉnh), 4. Xem chi tiết & Xuất Excel, 🧩 Cấu trúc component (Frontend), FPT Data Retrieval Tool - Sidebar UI (Tailwind & MUI) & Auto Công Việc (+3 more)

### Community 33 - "inside_bypass_nat.py"
Cohesion: 0.31
Nodes (5): fetch_sheet_data(), is_pending(), is_processed(), normalize_nfc(), remove_accents()

### Community 34 - "auto_import_service.py"
Cohesion: 0.16
Nodes (8): get_db_url(), _build_arg_parser(), create_readonly_kpi_engine(), ensure_infra_tables(), force_unlock_db(), _import_kpi_engine_class(), main(), seed_test_table()

### Community 35 - "load_config"
Cohesion: 0.23
Nodes (11): get_active_account_info(), load_config(), save_config(), update_clear_sheet_auto_cap_lai_cell(), get_config(), get_otp(), scan_qr(), start_bypass_nat_task() (+3 more)

### Community 36 - "fetch_sheet_data"
Cohesion: 0.10
Nodes (23): fetch_sheet_data(), get_reset_user_shds(), _is_auto_reset_cache_entry(), is_clear_success(), is_final_status(), load_cache(), normalize_nfc(), save_cache() (+15 more)

### Community 37 - "renderBypassTable"
Cohesion: 0.26
Nodes (12): filterTableByStaff(), getRecordField(), loadBypassSheetData(), onActivate(), pollBypassStatus(), renderBypassTable(), renderTopFailedStaff(), runBypassProcess() (+4 more)

### Community 39 - "os"
Cohesion: 0.11
Nodes (10): main(), build_chrome_options(), clean_profile_locks_and_orphans(), clear_inside_session(), create_driver_with_retry(), get_inside_profile_dir(), get_radius_profile_dir(), init_chrome_driver() (+2 more)

### Community 43 - "renderClsTable"
Cohesion: 0.31
Nodes (9): checkAndAutoTriggerCls(), loadClsSheetData(), onActivate(), pollClsStatus(), renderClsTable(), runClsProcess(), setClsRunningState(), updateClsSelectedCount() (+1 more)

### Community 47 - "inside_bypass.py"
Cohesion: 0.18
Nodes (11): Nguồn Dữ Liệu Phân Quyền Admin, Quy Tắc Phân Quyền Admin (Admin Privileges Rule), Quy Tắc Thực Thi, check_14d_hau_kiem_violation(), fetch_sheet_data(), is_admin_staff(), load_admin_staff_set(), _normalize_msnv() (+3 more)

### Community 48 - "save_records_zstd"
Cohesion: 0.40
Nodes (3): clear_retrieval_records(), load_records_zstd(), save_records_zstd()

### Community 49 - "_auto_orchestrator_cycle"
Cohesion: 0.14
Nodes (10): is_thu_hoi_port_task(), parse_vn_datetime(), _auto_orchestrator_cycle(), _auto_orchestrator_loop(), auto_overview_api(), _auto_task_states(), _is_record_today(), start_port_auto() (+2 more)

### Community 50 - "inside_signal.py"
Cohesion: 0.18
Nodes (3): main(), extract_ptc_fields(), normalize_nfc()

### Community 53 - "run_assign_process"
Cohesion: 0.40
Nodes (4): is_final_thao_tac(), export_assign_excel(), run_assign_process(), update_sheet_remote_assign()

### Community 54 - "download_full_log"
Cohesion: 0.40
Nodes (3): download_full_log(), _flush_log_to_disk(), _log_flusher_loop()

### Community 55 - "checkAndAutoTriggerBypass"
Cohesion: 0.60
Nodes (5): _bypassAutoKey(), _bypassAutoPending(), _bypassAutoTriedMap(), _bypassMarkAutoTried(), checkAndAutoTriggerBypass()

## Knowledge Gaps
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `pollBypassStatus()` connect `renderBypassTable` to `settings.js`, `bypass.js`, `renderClsTable`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `add_log()` (e.g. with `clear_all_sessions_api()` and `worker_assign()`) actually correct?**
  _`add_log()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `dom.js` be split into smaller, more focused modules?**
  _Cohesion score 0.015873015873015872 - nodes in this community are weakly interconnected._
- **Why does `pollBypassNatStatus()` connect `bypass_nat.js` to `settings.js`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Should `inside_report_crawler.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10795454545454546 - nodes in this community are weakly interconnected._
- **Why does `load_config()` connect `load_config` to `inside_report_crawler.py`, `fetch_sheet_data`, `.log`, `inside_spampool.py`, `inside_signal.py`, `add_log`, `run_mybae_process`, `core_login.py`, `_auto_orchestrator_cycle`, `InsideBypassNatAutomation`, `InsideScraper`, `run_assign_process`, `InsideBypassAutomation`, `InsidePortAutomation`, `inside_port.py`, `ModernInsideFPTApp`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Should `mybae.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05697278911564626 - nodes in this community are weakly interconnected._