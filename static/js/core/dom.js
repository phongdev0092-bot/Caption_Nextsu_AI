// ==========================================================
// CORE: DOM REFERENCES & GLOBAL STATE
// Classic script, không còn closure: mọi file js/ dùng chung scope toàn cục theo thứ tự nạp trong index.html.
// ==========================================================

// Elements
const bannerHost = document.getElementById('bannerHost');
if (bannerHost) bannerHost.textContent = window.location.host || 'Localhost';

const bannerDot = document.getElementById('bannerDot');
const bannerText = document.getElementById('bannerText');

// Single Background Login Button
const btnSingleLogin = document.getElementById('btnSingleLogin');
const loginLabel = document.getElementById('loginLabel');
const loginSpinner = document.getElementById('loginSpinner');
const loginIconKey = document.getElementById('loginIconKey');
const loginIconCheck = document.getElementById('loginIconCheck');

// Tabs & Sidebar Elements
const tabBtn1 = document.getElementById('tabBtn1');
const tabBtn2 = document.getElementById('tabBtn2');
const tabBtn3 = document.getElementById('tabBtn3');
const tabBtn4 = document.getElementById('tabBtn4');
const tabRetrieval = document.getElementById('tab-retrieval');
const tabImport = document.getElementById('tab-import');
const tabTasks = document.getElementById('tab-tasks');
const tabClearCls = document.getElementById('tab-clear-cls');
const btnBackToBypass = document.getElementById('btnBackToBypass');
const appSidebar = document.getElementById('appSidebar');
const btnCollapseSidebar = document.getElementById('btnCollapseSidebar');
const btnToggleSidebarMobile = document.getElementById('btnToggleSidebarMobile');
const topbarCurrentTitle = document.getElementById('topbarCurrentTitle');
const sidebarAccName = document.getElementById('sidebarAccName');
const sidebarSessionDot = document.getElementById('sidebarSessionDot');
const sidebarSessionLabel = document.getElementById('sidebarSessionLabel');
const sidebarSessionBtn = document.getElementById('sidebarSessionBtn');
const btnSidebarSwitchAcc = document.getElementById('btnSidebarSwitchAcc');
const btnSidebarSettings = document.getElementById('btnSidebarSettings');
const sidebarZstdCount = document.getElementById('sidebarZstdCount');
const sidebarZstdSize = document.getElementById('sidebarZstdSize');

// Retrieval Control Elements
const modeSingle = document.getElementById('modeSingle');
const modeFile = document.getElementById('modeFile');
const singleInputWrap = document.getElementById('singleInputWrap');
const fileInputWrap = document.getElementById('fileInputWrap');
const singleContractInput = document.getElementById('singleContractInput');
const contractFileInput = document.getElementById('contractFileInput');
const contractFileLabel = document.getElementById('contractFileLabel');
const contractTags = document.getElementById('contractTags');
const btnAutoFetch = document.getElementById('btnAutoFetch');
const fetchSpinner = document.getElementById('fetchSpinner');
const fetchRocketIcon = document.getElementById('fetchRocketIcon');
const fetchBtnText = document.getElementById('fetchBtnText');
const processTracker = document.getElementById('processTracker');
const trackerStatusText = document.getElementById('trackerStatusText');
const trackerPercent = document.getElementById('trackerPercent');
const trackerFill = document.getElementById('trackerFill');

// Table Elements
const retrievalSearchInput = document.getElementById('retrievalSearchInput');
const retrievalStatusSelect = document.getElementById('retrievalStatusSelect');
const retrievalDateFrom = document.getElementById('retrievalDateFrom');
const retrievalDateTo = document.getElementById('retrievalDateTo');
const btnFilterToday = document.getElementById('btnFilterToday');
const btnClearDateFilter = document.getElementById('btnClearDateFilter');
const filterCountBadge = document.getElementById('filterCountBadge');
const retrievalTableBody = document.getElementById('retrievalTableBody');
const btnExportExcel = document.getElementById('btnExportExcel');
const btnExportExcelText = document.getElementById('btnExportExcelText');
const btnClearTable = document.getElementById('btnClearTable');

// Detail Modal Elements
const detailModalBackdrop = document.getElementById('detailModalBackdrop');
const detailModalTitle = document.getElementById('detailModalTitle');
const detailModalBody = document.getElementById('detailModalBody');
const btnCloseDetailModal = document.getElementById('btnCloseDetailModal');
const btnCloseDetailModal2 = document.getElementById('btnCloseDetailModal2');
const btnCopyDetailModal = document.getElementById('btnCopyDetailModal');

// Import Elements
const importDropzone = document.getElementById('importDropzone');
const importFileInput = document.getElementById('importFileInput');
const btnExecuteImport = document.getElementById('btnExecuteImport');
const importHistoryList = document.getElementById('importHistoryList');
const btnDownloadTemplate = document.getElementById('btnDownloadTemplate');

// Settings Modal Elements
const btnOpenSettings = document.getElementById('btnOpenSettings');
const settingsModalBackdrop = document.getElementById('settingsModalBackdrop');
const btnCloseSettings = document.getElementById('btnCloseSettings');
const btnCancelSettings = document.getElementById('btnCancelSettings');
const btnSaveSettings = document.getElementById('btnSaveSettings');
const modalUsername = document.getElementById('modalUsername');
const modalPassword = document.getElementById('modalPassword');
const modalSecret = document.getElementById('modalSecret');
const modalQrFile = document.getElementById('modalQrFile');
const btnToggleModalPwd = document.getElementById('btnToggleModalPwd');
const modalOtpCode = document.getElementById('modalOtpCode');
const modalOtpTimer = document.getElementById('modalOtpTimer');
// Session and Storage Elements
const btnCheckSession = document.getElementById('btnCheckSession');
const sessionDot = document.getElementById('sessionDot');
const sessionLabel = document.getElementById('sessionLabel');
const zstdCount = document.getElementById('zstdCount');
const zstdSize = document.getElementById('zstdSize');

// Tab 3: ByPass & Google Sheets Elements
const btnSubTabBypass = document.getElementById('btnSubTabBypass');
const btnSubTabPhanCong = document.getElementById('btnSubTabPhanCong');
const badgeBypassPending = document.getElementById('badgeBypassPending');
const btnRefreshSheetData = document.getElementById('btnRefreshSheetData');
const btnOpenSheetWebhookModal = document.getElementById('btnOpenSheetWebhookModal');
const sheetStatTotal = document.getElementById('sheetStatTotal');
const sheetStatPending = document.getElementById('sheetStatPending');
const sheetStatDone = document.getElementById('sheetStatDone');
const bypassSessionStatus = document.getElementById('bypassSessionStatus');
const chkByPassVisible = document.getElementById('chkByPassVisible');
const btnRunAutoBypass = document.getElementById('btnRunAutoBypass');
const bypassSpinner = document.getElementById('bypassSpinner');
const bypassRunIcon = document.getElementById('bypassRunIcon');
const bypassRunText = document.getElementById('bypassRunText');
const bypassProgressTracker = document.getElementById('bypassProgressTracker');
const bypassTrackerStatus = document.getElementById('bypassTrackerStatus');
const bypassTrackerPercent = document.getElementById('bypassTrackerPercent');
const bypassTrackerFill = document.getElementById('bypassTrackerFill');
const sheetCurrentTabTitle = document.getElementById('sheetCurrentTabTitle');
const sheetRecordCountText = document.getElementById('sheetRecordCountText');
const sheetFilterStatusSelect = document.getElementById('sheetFilterStatusSelect');
const sheetDataTableBody = document.getElementById('sheetDataTableBody');
const bypassLogTerminal = document.getElementById('bypassLogTerminal');
const btnClearBypassLogs = document.getElementById('btnClearBypassLogs');
const clsLogTerminal = document.getElementById('clsLogTerminal');
const btnClearClsLogs = document.getElementById('btnClearClsLogs');
const assignLogTerminal = document.getElementById('assignLogTerminal');
const btnClearAssignLogs = document.getElementById('btnClearAssignLogs');
const btnExportBypassData = document.getElementById('btnExportBypassData');
const btnExportClsData = document.getElementById('btnExportClsData');
const btnExportAssignData = document.getElementById('btnExportAssignData');
const sheetWebhookModalBackdrop = document.getElementById('sheetWebhookModalBackdrop');
const inputSheetWebhookUrl = document.getElementById('inputSheetWebhookUrl');
const btnCloseSheetWebhookModal = document.getElementById('btnCloseSheetWebhookModal');
const btnCancelSheetWebhook = document.getElementById('btnCancelSheetWebhook');
const btnSaveSheetWebhook = document.getElementById('btnSaveSheetWebhook');

// Global State
let currentContracts = ['SGAFV2037'];
let currentRecords = [];
let selectedDetailRecord = null;
let isRetrieving = false;
let currentLoginState = 'idle';
let currentBypassGid = '0'; // 0 = ByPass, 909147347 = Phân Công Tay
let currentBypassRecords = [];
let isBypassRunning = false;
let lastProcessedShdSet = new Set(); // Track SHDs đã được xử lý trong phiên hiện tại
let autoBypassMode = localStorage.getItem('autoBypassMode') !== 'false';  // Mặc định Auto là BẬT
let autoBypassCountdown = 0; // Đếm ngược giây trước khi tự chạy
let autoBypassCountdownTimer = null;
let autoClsMode = localStorage.getItem('autoClsMode') !== 'false';        // Mặc định Auto là BẬT
let autoClsCountdown = 0;    // Đếm ngược giây trước khi tự chạy Clear Cls
let autoClsCountdownTimer = null;
let autoAssignMode = localStorage.getItem('autoAssignMode') !== 'false';  // Mặc định Auto là BẬT
let autoAssignCountdown = 0; // Đếm ngược giây trước khi tự chạy Phân Công Tay
let autoAssignCountdownTimer = null;
let autoClearSignalMode = localStorage.getItem('autoClearSignalMode') !== 'false'; // Mặc định Auto là BẬT
let autoClearSignalCountdown = 0;
let autoClearSignalCountdownTimer = null;
let autoResetSignalMode = localStorage.getItem('autoResetSignalMode') !== 'false'; // Mặc định Auto là BẬT
let autoResetSignalCountdown = 0;
let autoResetSignalCountdownTimer = null;
let autoSpamPoolMode = localStorage.getItem('autoSpamPoolMode') !== 'false'; // Mặc định Auto là BẬT
let autoSpamPoolCountdown = 0;
let autoSpamPoolCountdownTimer = null;
let isSpamPoolRunning = false;
let currentSpamPoolRecords = [];

