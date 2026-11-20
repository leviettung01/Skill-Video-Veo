/**
 * LeVietTung_autoveo — Captcha & Token Bridge Service Worker (v2.1.0)
 * Hỗ trợ đầy đủ Cấu hình kết nối (Bridge URL + Bridge Secret + Test kết nối),
 * Long-Polling tới http://127.0.0.1:4000, đồng bộ Cookie Google Flow & Nhật ký Mint Captcha.
 */
'use strict';

const DEFAULT_BRIDGE_BASE = 'http://127.0.0.1:4000';
const DEFAULT_BRIDGE_SECRET = 'ff065320a43b73b8959756fac4830553c1ee664bb7762467c46eb1de80d7e39d';
const PROFILE_ID = 'upproject-main';
const POLL_TIMEOUT_MS = 25_000;
const FLOW_URL = 'https://flow.google.com/about';

const EXTENSION_VERSION = chrome.runtime.getManifest().version;
const DEFAULT_FLOW_POOL_TARGET = 2;
const MAX_FLOW_POOL_TARGET = 6;
let FLOW_POOL_TARGET = DEFAULT_FLOW_POOL_TARGET;
const PROACTIVE_ROTATE_EVERY = 24;
const IDLE_TAB_CLOSE_MS = 45_000;
const CACHE_PURGE_COOLDOWN_MS = 60_000;
const SESSION_DETECT_TTL_MS = 600_000;
const FLOW_POOL_URLS = [
  'https://flow.google.com/about?ext_pool=1#overview',
  'https://flow.google.com/about?ext_pool=1#features',
  'https://flow.google.com/about?ext_pool=1#tools',
  'https://flow.google.com/about?ext_pool=1#models',
  'https://flow.google.com/about?ext_pool=1#showcase',
  'https://flow.google.com/about?ext_pool=1#community',
];
const ANCHOR_NAME_RE = /grecaptcha/i;
const ANCHOR_TOP_LEVEL_SITES = [
  'https://labs.google',
  'https://flow.google.com',
  'https://www.google.com',
  'https://google.com',
];

const tabInFlightCounts = new Map();
const tabMintCounts = new Map();
const tabLastUsedAt = new Map();
const tabCooldownUntil = new Map();
const TAB_COOLDOWN_MS = 20_000;
const rotatingTabs = new Set();
const extensionPoolTabIds = new Set();
const pendingRetireTabs = new Set();
const recentIssuedTokens = new Set();
let _poolEnsurePromise = null;
let _pruneTabsPromise = null;
let _activeResetPromise = null;
let _idleCleanupTimer = null;
let lastCommandAt = 0;
let lastCachePurgeAt = 0;
let globalMintCount = 0;
let _urlCycleIndex = 0;

let consecutivePollErrors = 0;
let bridgeBase = DEFAULT_BRIDGE_BASE;
let bridgeSecret = DEFAULT_BRIDGE_SECRET;
let configMissing = false;
let isPolling = false;
let manualDisconnect = false;
let lastPollOkAt = null;
let lastMintOkAt = null;
let lastMintDurationMs = null;
let detectedFlowEmail = '';
let detectedFlowToken = '';
let detectedFlowProjectId = '';
let cachedProfileId = '';
let _lastSessionDetectAt = 0;
let _lastLocalPollSaveAt = 0;
let _persistLogTimer = null;

if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
}

async function getOrCreateProfileId() {
  try {
    const allFlowTabs = await chrome.tabs.query({ url: ['https://flow.google.com/*', 'https://labs.google/*'] });
    for (const t of allFlowTabs) {
      if (!t.url) continue;
      try {
        const u = new URL(t.url);
        const ep = (u.searchParams.get('ext_profile') || '').trim();
        if (ep) {
          cachedProfileId = ep;
          await chrome.storage.local.set({ extProfileId: ep });
          return cachedProfileId;
        }
      } catch (_) {}
    }
    if (cachedProfileId) return cachedProfileId;
    const st = await chrome.storage.local.get(['extProfileId']);
    if (st && typeof st.extProfileId === 'string' && st.extProfileId.trim()) {
      cachedProfileId = st.extProfileId.trim();
      return cachedProfileId;
    }
  } catch (_) {}
  if (detectedFlowEmail && detectedFlowEmail.includes('@')) {
    return detectedFlowEmail.split('@')[0];
  }
  return PROFILE_ID;
}

async function closeDuplicateOptionsTabs() {
  try {
    const allTabs = await chrome.tabs.query({});
    for (const t of allTabs) {
      if (t.url && t.url.startsWith('chrome-extension://') && t.url.includes('/options.html')) {
        chrome.tabs.remove(t.id).catch(() => {});
      }
    }
  } catch (_) {}
}

async function detectFlowSessionInfo({ force = false, knownCookies = null } = {}) {
  const now = Date.now();
  if (!force && _lastSessionDetectAt > 0 && now - _lastSessionDetectAt < SESSION_DETECT_TTL_MS) {
    return {
      email: detectedFlowEmail,
      accessToken: detectedFlowToken,
      projectId: detectedFlowProjectId,
      profileId: cachedProfileId,
    };
  }
  try {
    const flowTab = await findFlowTab();
    if (flowTab && flowTab.url) {
      const mProj = flowTab.url.match(/\/project\/([0-9a-fA-F-]{32,36})/);
      if (mProj && mProj[1]) {
        detectedFlowProjectId = mProj[1];
      }
      try {
        const u = new URL(flowTab.url);
        const ep = (u.searchParams.get('ext_profile') || '').trim();
        if (ep) {
          cachedProfileId = ep;
          chrome.storage.local.set({ extProfileId: ep }).catch(() => {});
        }
      } catch (_) {}
    }
    const cookies = Array.isArray(knownCookies) ? knownCookies : await collectFlowAuthCookies();
    const hasGoogleAuth = cookies.some((c) => c.name === 'SID' || c.name.startsWith('__Secure-1PSID') || c.name.startsWith('__Secure-3PSID'));
    _lastSessionDetectAt = now;
    if (!hasGoogleAuth) {
      // Dedicated Captcha Solver Chrome profile runs logged out — skip 4x Google HTTPS probes completely.
      return {
        email: detectedFlowEmail,
        accessToken: detectedFlowToken,
        projectId: detectedFlowProjectId,
        profileId: cachedProfileId,
      };
    }
    for (const url of [
      'https://flow.google.com/fx/api/auth/session',
      'https://labs.google/fx/api/auth/session',
      'https://flow.google.com/api/auth/session',
    ]) {
      try {
        const r = await fetch(url, { method: 'GET', credentials: 'include' });
        if (r.ok) {
          const js = await r.json().catch(() => ({}));
          const email = js?.user?.email || js?.email || '';
          const tok = js?.access_token || js?.accessToken || '';
          if (email && email.includes('@')) {
            detectedFlowEmail = email.trim();
          }
          if (tok && String(tok).startsWith('ya29.')) {
            detectedFlowToken = String(tok).trim();
          }
          if (detectedFlowEmail) break;
        }
      } catch (_) {}
    }
    if (!detectedFlowEmail) {
      try {
        const rHtml = await fetch('https://flow.google.com/', { method: 'GET', credentials: 'include' });
        if (rHtml.ok) {
          const html = await rHtml.text();
          if (html && html.includes('"SNlM0e"')) {
            const mEmail = html.match(/"oPEP7c"\s*:\s*"([^"]+@[^"]+)"/);
            if (mEmail && mEmail[1]) {
              detectedFlowEmail = mEmail[1].trim();
            }
            if (!detectedFlowProjectId) {
              const mP = html.match(/\/project\/([0-9a-fA-F-]{32,36})/);
              if (mP && mP[1]) {
                detectedFlowProjectId = mP[1];
              }
            }
          }
        }
      } catch (_) {}
    }
  } catch (_) {}
  return {
    email: detectedFlowEmail,
    accessToken: detectedFlowToken,
    projectId: detectedFlowProjectId,
    profileId: cachedProfileId,
  };
}

let metrics = {
  requestCount: 0,
  successCount: 0,
  failedCount: 0,
  lastError: null,
};

let requestLog = [];

function schedulePersistLogAndMetrics() {
  if (_persistLogTimer) return;
  _persistLogTimer = setTimeout(() => {
    _persistLogTimer = null;
    chrome.storage.local.set({
      requestLog,
      metrics,
      lastMintOkAt,
      lastMintDurationMs,
    }).catch(() => {});
  }, 1_500);
}

function addRequestLog(entry) {
  requestLog.unshift(entry);
  if (requestLog.length > 100) requestLog.pop();
  schedulePersistLogAndMetrics();
  chrome.runtime.sendMessage({ type: 'REQUEST_LOG_UPDATE', log: requestLog }).catch(() => {});
  broadcastStatusPush();
}

function updateRequestLog(id, updates) {
  const entry = requestLog.find((e) => e.id === id);
  if (entry) Object.assign(entry, updates);
  schedulePersistLogAndMetrics();
  chrome.runtime.sendMessage({ type: 'REQUEST_LOG_UPDATE', log: requestLog }).catch(() => {});
  broadcastStatusPush();
}

function broadcastStatusPush() {
  chrome.runtime.sendMessage({ type: 'STATUS_PUSH' }).catch(() => {});
}

// ── Config ────────────────────────────────────────────────────────────

async function autoSyncConfigFromBackend(baseCandidate) {
  const targetBase = (baseCandidate || bridgeBase || DEFAULT_BRIDGE_BASE).replace(/\/+$/, '');
  try {
    const resp = await fetch(`${targetBase}/api/internal/captcha/config`, { method: 'GET' });
    if (resp.ok) {
      const data = await resp.json().catch(() => ({}));
      if (data.bridgeSecret && typeof data.bridgeSecret === 'string') {
        bridgeSecret = data.bridgeSecret;
      }
      if (data.bridgeBase && typeof data.bridgeBase === 'string') {
        bridgeBase = data.bridgeBase.replace(/\/+$/, '');
      }
      await chrome.storage.local.set({ bridgeBase, bridgeSecret });
      return { ok: true, bridgeBase, bridgeSecret };
    }
  } catch (_) {}
  return { ok: false, bridgeBase, bridgeSecret };
}

async function loadBridgeConfig() {
  const stored = await chrome.storage.local.get([
    'bridgeBase',
    'bridgeSecret',
    'metrics',
    'requestLog',
    'lastPollOkAt',
    'lastMintOkAt',
    'lastMintDurationMs',
  ]);
  if (stored.metrics) Object.assign(metrics, stored.metrics);
  if (Array.isArray(stored.requestLog)) requestLog = stored.requestLog;
  if (stored.lastPollOkAt) lastPollOkAt = stored.lastPollOkAt;
  if (stored.lastMintOkAt) lastMintOkAt = stored.lastMintOkAt;
  if (stored.lastMintDurationMs != null) lastMintDurationMs = stored.lastMintDurationMs;

  let needSaveDefaults = false;
  if (typeof stored.bridgeBase === 'string' && stored.bridgeBase.trim()) {
    bridgeBase = stored.bridgeBase.trim().replace(/\/+$/, '');
  } else {
    bridgeBase = DEFAULT_BRIDGE_BASE;
    needSaveDefaults = true;
  }

  if (typeof stored.bridgeSecret === 'string' && stored.bridgeSecret.trim()) {
    bridgeSecret = stored.bridgeSecret.trim();
  } else {
    bridgeSecret = DEFAULT_BRIDGE_SECRET;
    needSaveDefaults = true;
  }

  if (needSaveDefaults) {
    await chrome.storage.local.set({ bridgeBase, bridgeSecret });
  }

  // Thử đồng bộ tự động với backend nếu đang mở cổng 4000
  await autoSyncConfigFromBackend(bridgeBase);

  configMissing = !bridgeBase || !bridgeSecret;
  updateBadge();
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'local') return;
  let updated = false;
  if (changes.bridgeBase && typeof changes.bridgeBase.newValue === 'string') {
    bridgeBase = changes.bridgeBase.newValue.trim().replace(/\/+$/, '');
    updated = true;
  }
  if (changes.bridgeSecret && typeof changes.bridgeSecret.newValue === 'string') {
    bridgeSecret = changes.bridgeSecret.newValue.trim();
    updated = true;
  }
  if (!updated) return;

  const wasConfigMissing = configMissing;
  configMissing = !bridgeBase || !bridgeSecret;
  updateBadge();
  broadcastStatusPush();

  if ((wasConfigMissing || !isPolling) && !configMissing && !manualDisconnect) {
    void pollLoop();
  }
});

// ── Badge ─────────────────────────────────────────────────────────────

function updateBadge() {
  if (configMissing) {
    chrome.action.setBadgeText({ text: '!' });
    chrome.action.setBadgeBackgroundColor({ color: '#dc2626' });
    chrome.action.setTitle({ title: 'LeVietTung_autoveo: Chưa cấu hình URL + Secret' });
  } else if (consecutivePollErrors === 0 && lastPollOkAt && Date.now() - lastPollOkAt < 40_000) {
    chrome.action.setBadgeText({ text: 'ON' });
    chrome.action.setBadgeBackgroundColor({ color: '#10b981' });
    chrome.action.setTitle({ title: 'LeVietTung_autoveo — Đã kết nối Captcha Bridge (:4000)' });
  } else {
    chrome.action.setBadgeText({ text: '' });
    chrome.action.setTitle({ title: 'LeVietTung_autoveo — Lê Việt Tùng (Zalo: 0915967790)' });
  }
}

// ── HTTP helpers ──────────────────────────────────────────────────────

function authHeaders() {
  return bridgeSecret ? { 'x-local-auth': bridgeSecret } : {};
}

async function collectFlowAuthCookies() {
  try {
    const all = await chrome.cookies.getAll({});
    return all
      .filter((c) => {
        const d = String(c.domain || '').toLowerCase();
        return (
          d === 'flow.google.com' ||
          d === '.flow.google.com' ||
          d === 'labs.google' ||
          d === '.labs.google' ||
          d === '.google.com' ||
          d === 'google.com' ||
          d === 'accounts.google.com'
        );
      })
      .map((c) => ({
        name: c.name,
        value: c.value,
        domain: c.domain,
        path: c.path || '/',
        expires: c.expirationDate || -1,
        httpOnly: Boolean(c.httpOnly),
        secure: Boolean(c.secure),
        sameSite: c.sameSite === 'no_restriction' ? 'None' : c.sameSite === 'strict' ? 'Strict' : 'Lax',
      }));
  } catch (_) {
    return [];
  }
}

async function postJson(path, payload, { includeSession = false } = {}) {
  try {
    const profId = cachedProfileId || (await getOrCreateProfileId());
    const bodyObj = { profileId: profId, ...payload };
    if (includeSession) {
      const flowCookies = await collectFlowAuthCookies();
      const flowSession = await detectFlowSessionInfo({ knownCookies: flowCookies });
      bodyObj.flowCookies = flowCookies;
      bodyObj.flowSession = flowSession;
    }
    const resp = await fetch(`${bridgeBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(bodyObj),
    });
    if (!resp.ok) {
      console.warn('[LeVietTung_autoveo] post non-200:', path, resp.status);
    }
  } catch (e) {
    console.warn('[LeVietTung_autoveo] post failed:', path, e?.message || e);
  }
}

// ── Tab & Pool helpers ────────────────────────────────────────────────

function nextPoolUrl() {
  const url = FLOW_POOL_URLS[_urlCycleIndex % FLOW_POOL_URLS.length];
  _urlCycleIndex += 1;
  return url;
}

function totalInFlightTabs() {
  let sum = 0;
  for (const count of tabInFlightCounts.values()) {
    sum += Number(count || 0);
  }
  return sum;
}

function rememberIssuedToken(tok) {
  if (!tok || typeof tok !== 'string') return;
  recentIssuedTokens.add(tok);
  while (recentIssuedTokens.size > 100) {
    const oldest = recentIssuedTokens.values().next().value;
    if (oldest === undefined) break;
    recentIssuedTokens.delete(oldest);
  }
}

function getTabEffectiveUrl(tab) {
  return String(tab?.url || tab?.pendingUrl || '');
}

function isAllowedFlowTabUrl(rawUrl) {
  try {
    const u = new URL(rawUrl || '');
    if (u.protocol !== 'https:') return false;
    if (u.hostname === 'flow.google.com') return true;
    if (u.hostname === 'labs.google') {
      return /^\/fx\/(?:[^/]+\/)?tools\/flow(?:\/|$)/.test(u.pathname);
    }
    return false;
  } catch (_) {
    return false;
  }
}

function isPoolWorkerTab(tab) {
  if (!tab) return false;
  if (extensionPoolTabIds.has(tab.id)) return true;
  const raw = getTabEffectiveUrl(tab);
  if (!raw) return false;
  try {
    const u = new URL(raw);
    if (u.hostname !== 'flow.google.com') return false;
    if (u.searchParams.get('ext_pool') === '1') return true;
    if (u.pathname === '/about' && /^#(overview|features|tools|models)$/i.test(u.hash || '')) {
      return true;
    }
    return false;
  } catch (_) {
    return false;
  }
}

async function listFlowTabs() {
  const allTabs = await chrome.tabs.query({});
  const valid = allTabs.filter((tab) => isAllowedFlowTabUrl(getTabEffectiveUrl(tab)));
  valid.sort((a, b) => {
    const aProj = /\/project\/[0-9a-f-]{32,36}(?:[/?#]|$)/i.test(getTabEffectiveUrl(a)) ? 0 : 1;
    const bProj = /\/project\/[0-9a-f-]{32,36}(?:[/?#]|$)/i.test(getTabEffectiveUrl(b)) ? 0 : 1;
    if (aProj !== bProj) return aProj - bProj;
    if (Boolean(a.active) !== Boolean(b.active)) return a.active ? -1 : 1;
    return Number(a.id || 0) - Number(b.id || 0);
  });
  return valid;
}

async function findFlowTab() {
  const tabs = await listFlowTabs();
  return tabs[0] || null;
}

async function purgeFlowCache({ force = false, clearAnchorCookies = false, includeStaticCache = false } = {}) {
  const now = Date.now();
  const safeClearAnchor = Boolean(clearAnchorCookies && totalInFlightTabs() === 0);
  if (!force && now - lastCachePurgeAt < CACHE_PURGE_COOLDOWN_MS) {
    if (safeClearAnchor) await clearRecaptchaCookieAnchor();
    return;
  }
  lastCachePurgeAt = now;
  if (chrome.browsingData?.remove) {
    try {
      const origins = includeStaticCache
        ? [
            'https://flow.google.com',
            'https://labs.google',
            'https://www.recaptcha.net',
          ]
        : [
            'https://flow.google.com',
            'https://labs.google',
          ];
      const dataTypes = includeStaticCache
        ? { cache: true, cacheStorage: true }
        : { cacheStorage: true };
      await chrome.browsingData.remove({ origins }, dataTypes);
    } catch (e) {
      console.warn('[LeVietTung_autoveo] purgeFlowCache warn:', e?.message || e);
    }
  }
  if (safeClearAnchor) {
    await clearRecaptchaCookieAnchor();
  }
}

function cleanupTabTracking(tabId) {
  tabInFlightCounts.delete(tabId);
  tabMintCounts.delete(tabId);
  tabLastUsedAt.delete(tabId);
  tabCooldownUntil.delete(tabId);
  rotatingTabs.delete(tabId);
  extensionPoolTabIds.delete(tabId);
  pendingRetireTabs.delete(tabId);
}

async function ensureSolverTabPool(minTabs = FLOW_POOL_TARGET) {
  if (_poolEnsurePromise) {
    return _poolEnsurePromise;
  }
  if (_activeResetPromise) {
    return await listFlowTabs();
  }
  const cappedTarget = Math.max(1, Math.min(MAX_FLOW_POOL_TARGET, Number(minTabs) || DEFAULT_FLOW_POOL_TARGET));
  _poolEnsurePromise = (async () => {
    try {
      let tabs = await listFlowTabs();
      if (tabs.length >= cappedTarget) return tabs;
      const nonPoolTab = tabs.find((t) => !isPoolWorkerTab(t));
      const windowId = (nonPoolTab || tabs[0])?.windowId;
      const needed = Math.max(0, cappedTarget - tabs.length);
      for (let i = 0; i < needed; i++) {
        try {
          const createOpts = { url: nextPoolUrl(), active: false };
          if (typeof windowId === 'number') createOpts.windowId = windowId;
          const created = await chrome.tabs.create(createOpts);
          if (created?.id) {
            extensionPoolTabIds.add(created.id);
            await waitForTabLoad(created.id, 20_000).catch(() => {});
            await new Promise((r) => setTimeout(r, 400));
            await ensureContentScript(created.id).catch(() => {});
          }
        } catch (_) {}
      }
      tabs = await listFlowTabs();
      return tabs;
    } finally {
      _poolEnsurePromise = null;
    }
  })();
  return _poolEnsurePromise;
}

async function prunePoolTabs({ targetMax = FLOW_POOL_TARGET, closeAllWorkers = false } = {}) {
  if (_pruneTabsPromise) {
    return _pruneTabsPromise;
  }
  _pruneTabsPromise = (async () => {
    let closedCount = 0;
    try {
      const tabs = await listFlowTabs();
      const cap = Math.max(0, Math.min(MAX_FLOW_POOL_TARGET, Number(targetMax) || 0));
      const workers = tabs.filter(
        (t) =>
          isPoolWorkerTab(t) &&
          (tabInFlightCounts.get(t.id) || 0) === 0 &&
          !rotatingTabs.has(t.id),
      );
      const excessCount = closeAllWorkers ? workers.length : Math.max(0, tabs.length - cap);
      if (excessCount <= 0 || workers.length === 0) return 0;

      workers.sort((a, b) => {
        if (Boolean(a.active) !== Boolean(b.active)) return a.active ? 1 : -1;
        return (tabLastUsedAt.get(a.id) || 0) - (tabLastUsedAt.get(b.id) || 0);
      });

      for (const tab of workers) {
        if (closedCount >= excessCount) break;
        rotatingTabs.add(tab.id);
        try {
          await clearTabRecaptchaStorage(tab.id).catch(() => {});
          await chrome.tabs.remove(tab.id).catch(() => {});
          cleanupTabTracking(tab.id);
          closedCount += 1;
        } catch (_) {
          rotatingTabs.delete(tab.id);
        }
      }

      if (closedCount > 0) {
        await purgeFlowCache({
          force: closeAllWorkers,
          clearAnchorCookies: totalInFlightTabs() === 0,
        });
      }
      return closedCount;
    } finally {
      _pruneTabsPromise = null;
    }
  })();
  return _pruneTabsPromise;
}

function scheduleIdleCleanup() {
  if (_idleCleanupTimer) {
    clearTimeout(_idleCleanupTimer);
    _idleCleanupTimer = null;
  }
  _idleCleanupTimer = setTimeout(() => {
    _idleCleanupTimer = null;
    if (totalInFlightTabs() === 0 && (!lastCommandAt || Date.now() - lastCommandAt >= IDLE_TAB_CLOSE_MS)) {
      void prunePoolTabs({ closeAllWorkers: true });
    }
  }, IDLE_TAB_CLOSE_MS + 1_000);
}

async function acquireFlowTab(excludeTabIds = null) {
  const targetPool = Math.max(1, Math.min(MAX_FLOW_POOL_TARGET, FLOW_POOL_TARGET));
  let tabs = await listFlowTabs();
  if (tabs.length > targetPool) {
    void prunePoolTabs({ targetMax: targetPool, closeAllWorkers: false });
  }
  if (tabs.length === 0) {
    tabs = await ensureSolverTabPool(targetPool);
  } else if (tabs.length < targetPool && !_poolEnsurePromise && !_activeResetPromise) {
    void ensureSolverTabPool(targetPool);
  }
  if (!tabs.length) return null;

  const now = Date.now();
  const isCooling = (t) => (tabCooldownUntil.get(t.id) || 0) > now;
  const isExcluded = (t) =>
    (excludeTabIds && excludeTabIds.has(t.id)) || rotatingTabs.has(t.id);

  let pool = tabs.filter((t) => !isExcluded(t) && !isCooling(t));
  if (!pool.length) {
    pool = tabs.filter((t) => !isExcluded(t));
  }
  if (!pool.length) {
    pool = excludeTabIds ? tabs.filter((t) => !excludeTabIds.has(t.id)) : tabs;
  }
  if (!pool.length) pool = tabs;

  pool.sort((a, b) => {
    const coolA = isCooling(a) ? 1 : 0;
    const coolB = isCooling(b) ? 1 : 0;
    if (coolA !== coolB) return coolA - coolB;
    const infA = tabInFlightCounts.get(a.id) || 0;
    const infB = tabInFlightCounts.get(b.id) || 0;
    if (infA !== infB) return infA - infB;
    const usedA = tabLastUsedAt.get(a.id) || 0;
    const usedB = tabLastUsedAt.get(b.id) || 0;
    if (usedA !== usedB) return usedA - usedB;
    return Number(a.id || 0) - Number(b.id || 0);
  });
  return pool[0] || null;
}

async function clearTabRecaptchaStorage(tabId) {
  try {
    const tab = await chrome.tabs.get(tabId).catch(() => null);
    if (!tab || !isAllowedFlowTabUrl(getTabEffectiveUrl(tab))) return 0;
    const res = await chrome.scripting.executeScript({
      target: { tabId },
      world: 'MAIN',
      func: () => {
        let removed = 0;
        const isRc = (k) => {
          const s = String(k || '');
          return s.startsWith('_grecaptcha') || s.startsWith('grecaptcha') || s.startsWith('rc::');
        };
        try {
          for (const k of Object.keys(localStorage).filter(isRc)) {
            localStorage.removeItem(k);
            removed++;
          }
        } catch (_) {}
        try {
          for (const k of Object.keys(sessionStorage).filter(isRc)) {
            sessionStorage.removeItem(k);
            removed++;
          }
        } catch (_) {}
        try {
          if (window.caches && typeof window.caches.keys === 'function') {
            window.caches.keys().then((keys) => {
              keys.forEach((k) => window.caches.delete(k).catch(() => {}));
            }).catch(() => {});
          }
        } catch (_) {}
        return removed;
      },
    });
    return Array.isArray(res) && res[0] ? Number(res[0].result || 0) : 0;
  } catch (_) {
    return 0;
  }
}

async function nudgeWindowGeometry(tab) {
  try {
    if (!tab?.windowId || !chrome.windows?.get || !chrome.windows?.update) return;
    const win = await chrome.windows.get(tab.windowId);
    if (!win || win.focused || win.state !== 'normal') return;
    const jitterW = Math.floor(Math.random() * 61) - 30;
    const jitterH = Math.floor(Math.random() * 41) - 20;
    const jitterL = Math.floor(Math.random() * 41) - 20;
    const jitterT = Math.floor(Math.random() * 31) - 15;
    await chrome.windows.update(win.id, {
      width: Math.max(960, Math.min(1440, (win.width || 1180) + jitterW)),
      height: Math.max(680, Math.min(960, (win.height || 820) + jitterH)),
      left: Math.max(10, (win.left || 40) + jitterL),
      top: Math.max(10, (win.top || 40) + jitterT),
    });
  } catch (_) {}
}

async function rotateTabSession(tabId, { forceAnchorClear = false } = {}) {
  if (!tabId || rotatingTabs.has(tabId)) return;
  if ((tabInFlightCounts.get(tabId) || 0) > 0) {
    pendingRetireTabs.add(tabId);
    return;
  }
  rotatingTabs.add(tabId);
  tabMintCounts.set(tabId, 0);
  try {
    const tab = await chrome.tabs.get(tabId).catch(() => null);
    if (!tab) {
      cleanupTabTracking(tabId);
      return;
    }
    await clearTabRecaptchaStorage(tabId);
    await purgeFlowCache({ clearAnchorCookies: Boolean(forceAnchorClear && totalInFlightTabs() === 0) });
    await nudgeWindowGeometry(tab);

    // Tab pool do Extension tạo -> dùng xong là tự đóng tab & xoá cache (chỉ mở tab sạch mới khi cần)
    if (isPoolWorkerTab(tab)) {
      await chrome.tabs.remove(tabId).catch(() => {});
      cleanupTabTracking(tabId);
      const stillActive = lastCommandAt > 0 && Date.now() - lastCommandAt < 10_000;
      if (stillActive && !_activeResetPromise) {
        const current = await listFlowTabs();
        if (current.length < FLOW_POOL_TARGET) {
          void ensureSolverTabPool(FLOW_POOL_TARGET);
        }
      }
      return;
    }
  } finally {
    rotatingTabs.delete(tabId);
  }
}

async function ensureContentScript(tabId) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      world: 'MAIN',
      files: ['injected.js'],
    });
  } catch (e) {
    console.debug('[LeVietTung_autoveo] injected.js warn on tab', tabId, e?.message || e);
  }
  return chrome.scripting
    .executeScript({ target: { tabId }, files: ['content.js'] })
    .catch((e) => {
      console.debug('[LeVietTung_autoveo] content.js warn on tab', tabId, e?.message || e);
      return undefined;
    });
}

async function mintDirectInMainWorld(tabId, action) {
  if (typeof action !== 'string' || !action || action.startsWith('__FLOW_RPC__:')) {
    return null;
  }
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      world: 'MAIN',
      args: [action],
      func: async (act) => {
        try {
          if (typeof window.__upprojectMintRecaptchaToken === 'function') {
            const tok = await window.__upprojectMintRecaptchaToken(act);
            return { token: tok };
          }
          return { error: 'MINT_FN_NOT_READY' };
        } catch (err) {
          return { error: err?.message || String(err) };
        }
      },
    });
    const first = Array.isArray(results) && results[0] ? results[0].result : null;
    if (first && (first.token || first.error)) {
      return first;
    }
  } catch (e) {
    return { error: e?.message || String(e) };
  }
  return null;
}

function waitForTabLoad(tabId, timeoutMs = 30_000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(onUpdated);
      chrome.tabs.onRemoved.removeListener(onRemoved);
      reject(new Error('waitForTabLoad: timeout'));
    }, timeoutMs);

    function onUpdated(id, info) {
      if (id !== tabId) return;
      if (info.status === 'complete') {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(onUpdated);
        chrome.tabs.onRemoved.removeListener(onRemoved);
        resolve();
      }
    }

    function onRemoved(id) {
      if (id !== tabId) return;
      clearTimeout(timer);
      chrome.tabs.onUpdated.removeListener(onUpdated);
      chrome.tabs.onRemoved.removeListener(onRemoved);
      reject(new Error('waitForTabLoad: tab removed'));
    }

    chrome.tabs.onUpdated.addListener(onUpdated);
    chrome.tabs.onRemoved.addListener(onRemoved);
  });
}

// ── reCAPTCHA anchor cookie ───────────────────────────────────────────

async function dumpAnchorCookies() {
  try {
    const all = await chrome.cookies.getAll({});
    const hits = all.filter((c) => ANCHOR_NAME_RE.test(c.name));
    return hits.map(
      (c) =>
        `${c.name}@${c.domain}${c.partitionKey ? ` [part:${JSON.stringify(c.partitionKey)}]` : ''}`,
    );
  } catch (_) {
    return [];
  }
}

async function removeAnchorCookies(query, extra) {
  let removed = 0;
  const cookies = await chrome.cookies.getAll(query);
  for (const cookie of cookies) {
    if (!ANCHOR_NAME_RE.test(cookie.name)) continue;
    const host = cookie.domain.startsWith('.') ? `www${cookie.domain}` : cookie.domain;
    const url = `${cookie.secure ? 'https' : 'http'}://${host}${cookie.path}`;
    try {
      const detail = await chrome.cookies.remove({
        url,
        name: cookie.name,
        storeId: cookie.storeId,
        ...extra,
      });
      if (detail !== null) removed++;
    } catch (_) {}
  }
  return removed;
}

async function clearRecaptchaCookieAnchor() {
  const before = await dumpAnchorCookies();
  let removed = 0;
  let partitionedRemoved = 0;

  try {
    removed = await removeAnchorCookies({});
  } catch (_) {}

  for (const topLevelSite of ANCHOR_TOP_LEVEL_SITES) {
    try {
      const partitionKey = { topLevelSite };
      partitionedRemoved += await removeAnchorCookies({ partitionKey }, { partitionKey });
    } catch (_) {}
  }

  if (chrome.browsingData?.remove) {
    try {
      await chrome.browsingData.remove(
        { origins: ['https://www.recaptcha.net'] },
        { cookies: true },
      );
    } catch (_) {}
  }

  const after = await dumpAnchorCookies();
  void postJson('/api/internal/captcha/event', {
    type: 'anchor_clear',
    version: EXTENSION_VERSION,
    removed,
    partitionedRemoved,
    before: before.length,
    after: after.length,
    sample: before.slice(0, 8),
  });
  return removed + partitionedRemoved;
}

// ── Captcha mint ──────────────────────────────────────────────────────

async function executeMintOnTab(tabId, commandId, action) {
  const liveTab = await chrome.tabs.get(tabId).catch(() => null);
  if (!liveTab || !isAllowedFlowTabUrl(getTabEffectiveUrl(liveTab))) {
    return { error: 'TAB_NAVIGATED_AWAY' };
  }
  await ensureContentScript(tabId);
  let reply = await mintDirectInMainWorld(tabId, action);
  const ask = (timeoutMs) =>
    new Promise((resolve) => {
      const timer = setTimeout(() => resolve({ error: 'CAPTCHA_TIMEOUT' }), timeoutMs);
      chrome.tabs.sendMessage(
        tabId,
        { type: 'GET_CAPTCHA', requestId: commandId, pageAction: action },
        (resp) => {
          clearTimeout(timer);
          if (chrome.runtime.lastError) {
            resolve({ error: chrome.runtime.lastError.message || 'TAB_NO_LISTENER' });
            return;
          }
          resolve(resp || { error: 'EMPTY_REPLY' });
        },
      );
    });

  if (!reply?.token) {
    const errLower = String(reply?.error || '').toLowerCase();
    const shouldRetryViaBridge =
      !reply
      || errLower.includes('mint_fn_not_ready')
      || errLower.includes('cannot access')
      || errLower.includes('no tab')
      || errLower.includes('empty');
    if (shouldRetryViaBridge) {
      await ensureContentScript(tabId);
      await new Promise((r) => setTimeout(r, 200));
      reply = (await mintDirectInMainWorld(tabId, action)) || (await ask(15_000));
    }
  }
  return reply;
}

async function handleCaptcha(command) {
  const { commandId, action, accountKey } = command;
  const startedAt = Date.now();
  lastCommandAt = startedAt;
  if (_idleCleanupTimer) {
    clearTimeout(_idleCleanupTimer);
    _idleCleanupTimer = null;
  }
  const logId = commandId || `mint-${startedAt}`;

  metrics.requestCount += 1;
  const isFlowRpc = typeof action === 'string' && action.startsWith('__FLOW_RPC__:');
  addRequestLog({
    id: logId,
    type: isFlowRpc ? 'FLOW_RPC' : (action || 'GET_CAPTCHA'),
    time: new Date().toISOString(),
    status: 'PROCESSING',
    url: FLOW_URL,
    payloadSummary: isFlowRpc
      ? action.slice(0, 120)
      : `reCAPTCHA action=${action}${accountKey ? ` [${accountKey}]` : ''}`,
  });

  const triedTabs = new Set();
  const maxTabAttempts = Math.min(3, Math.max(2, FLOW_POOL_TARGET));
  let reply = null;
  let chosenTabId = null;

  for (let attempt = 0; attempt < maxTabAttempts; attempt++) {
    const tab = await acquireFlowTab(triedTabs);
    if (!tab?.id || triedTabs.has(tab.id)) break;
    triedTabs.add(tab.id);
    chosenTabId = tab.id;
    tabLastUsedAt.set(tab.id, Date.now());
    tabInFlightCounts.set(tab.id, (tabInFlightCounts.get(tab.id) || 0) + 1);
    try {
      reply = await executeMintOnTab(tab.id, commandId, action);
    } finally {
      const nextCount = Math.max(0, (tabInFlightCounts.get(tab.id) || 1) - 1);
      if (nextCount === 0) {
        tabInFlightCounts.delete(tab.id);
        if (pendingRetireTabs.delete(tab.id)) {
          void rotateTabSession(tab.id, { forceAnchorClear: totalInFlightTabs() === 0 });
        }
      } else {
        tabInFlightCounts.set(tab.id, nextCount);
      }
    }

    const tok = reply?.token;
    const isFlowPayload = isFlowRpc && typeof tok === 'string' && tok.length > 0;
    const isDuplicateToken = !isFlowPayload && typeof tok === 'string' && recentIssuedTokens.has(tok);
    const isShortToken = !isFlowPayload && typeof tok === 'string' && tok.length < 80;

    if (tok && (isFlowPayload || (!isDuplicateToken && !isShortToken))) {
      tabCooldownUntil.delete(tab.id);
      break;
    }
    if (isDuplicateToken || isShortToken) {
      reply = { error: isDuplicateToken ? 'DUPLICATE_TOKEN' : 'INVALID_TOKEN_LENGTH' };
    }
    tabCooldownUntil.set(tab.id, Date.now() + TAB_COOLDOWN_MS);
    void rotateTabSession(tab.id, { forceAnchorClear: false });
  }

  if (!chosenTabId && !reply) {
    metrics.failedCount += 1;
    updateRequestLog(logId, { status: 'FAILED', error: 'NO_FLOW_TAB' });
    await postJson('/api/internal/captcha/result', { commandId, error: 'NO_FLOW_TAB' });
    scheduleIdleCleanup();
    return;
  }

  if (reply?.token) {
    if (!isFlowRpc) {
      rememberIssuedToken(reply.token);
    }
    const durationMs = Date.now() - startedAt;
    lastMintOkAt = Date.now();
    lastMintDurationMs = durationMs;
    metrics.successCount += 1;
    void chrome.storage.session.set({
      lastMintOkAt,
      lastMintDurationMs,
    });
    updateRequestLog(logId, {
      status: 'COMPLETED',
      httpStatus: 200,
      responseSummary: `Tab#${chosenTabId} minted in ${durationMs}ms (${String(reply.token).slice(0, 20)}...)`,
    });
    await postJson('/api/internal/captcha/result', { commandId, token: reply.token });

    globalMintCount += 1;
    const tabCount = (tabMintCounts.get(chosenTabId) || 0) + 1;
    tabMintCounts.set(chosenTabId, tabCount);
    if (tabCount >= PROACTIVE_ROTATE_EVERY) {
      void rotateTabSession(chosenTabId, { forceAnchorClear: globalMintCount % 48 === 0 && totalInFlightTabs() === 0 });
    } else if (globalMintCount % 48 === 0 && totalInFlightTabs() === 0) {
      void purgeFlowCache({ clearAnchorCookies: true });
    }
  } else {
    const errStr = reply?.error || 'CAPTCHA_FAILED';
    metrics.failedCount += 1;
    metrics.lastError = errStr;
    updateRequestLog(logId, { status: 'FAILED', error: errStr });
    await postJson('/api/internal/captcha/result', {
      commandId,
      error: errStr,
    });
  }
  scheduleIdleCleanup();
}

async function _runCoalescedReset(kind, workerFn) {
  if (_activeResetPromise) {
    return await _activeResetPromise;
  }
  _activeResetPromise = (async () => {
    return await workerFn();
  })();
  try {
    return await _activeResetPromise;
  } finally {
    _activeResetPromise = null;
  }
}

async function handleSoftReset(command) {
  const { commandId } = command;
  try {
    const out = await _runCoalescedReset('soft', async () => {
      const tabs = await listFlowTabs();
      await Promise.all(tabs.map((t) => clearTabRecaptchaStorage(t.id)));
      await purgeFlowCache({ force: true, clearAnchorCookies: totalInFlightTabs() === 0, includeStaticCache: true });
      tabCooldownUntil.clear();
      await prunePoolTabs({ targetMax: FLOW_POOL_TARGET, closeAllWorkers: false });
      const refreshed = await listFlowTabs();
      await postJson('/api/internal/captcha/event', {
        type: 'extension_ready',
        version: EXTENSION_VERSION,
        readyTabs: refreshed.length,
        poolSize: FLOW_POOL_TARGET,
      });
      return { token: 'soft_reset_ok' };
    });
    await postJson('/api/internal/captcha/result', { commandId, ...out });
  } catch (e) {
    await postJson('/api/internal/captcha/result', {
      commandId,
      error: e?.message || 'SOFT_RESET_FAILED',
    });
  }
}

async function handleHardReset(command) {
  const { commandId } = command;
  try {
    const out = await _runCoalescedReset('hard', async () => {
      tabCooldownUntil.clear();
      pendingRetireTabs.clear();
      const existingTabs = await listFlowTabs();
      await Promise.all(existingTabs.map((t) => clearTabRecaptchaStorage(t.id)));
      await prunePoolTabs({ closeAllWorkers: true });
      await purgeFlowCache({ force: true, clearAnchorCookies: totalInFlightTabs() === 0, includeStaticCache: true });
      const isActive = lastCommandAt > 0 && Date.now() - lastCommandAt < IDLE_TAB_CLOSE_MS;
      if (isActive) {
        const current = await listFlowTabs();
        if (current.length === 0) {
          const created = await chrome.tabs.create({ url: nextPoolUrl(), active: false }).catch(() => null);
          if (created?.id) {
            extensionPoolTabIds.add(created.id);
            await waitForTabLoad(created.id, 20_000).catch(() => {});
            await ensureContentScript(created.id).catch(() => {});
          }
        }
      }
      const refreshed = await listFlowTabs();
      await postJson('/api/internal/captcha/event', {
        type: 'extension_ready',
        version: EXTENSION_VERSION,
        readyTabs: refreshed.length,
        poolSize: FLOW_POOL_TARGET,
      });
      return { token: 'hard_reset_ok' };
    });
    await postJson('/api/internal/captcha/result', { commandId, ...out });
  } catch (e) {
    await postJson('/api/internal/captcha/result', {
      commandId,
      error: e?.message || 'HARD_RESET_FAILED',
    });
  }
}

// ── Poll loop ─────────────────────────────────────────────────────────

async function pollLoop() {
  if (isPolling) return;
  isPolling = true;
  while (true) {
    if (configMissing || manualDisconnect) {
      isPolling = false;
      updateBadge();
      broadcastStatusPush();
      return;
    }

    let commands = [];
    try {
      const profId = await getOrCreateProfileId();
      const flowTabsNow = await listFlowTabs();
      const readyTabsNow = flowTabsNow.filter((t) => !rotatingTabs.has(t.id)).length;
      const resp = await fetch(
        `${bridgeBase}/api/internal/captcha/poll` +
          `?profileId=${encodeURIComponent(profId)}&timeout=${POLL_TIMEOUT_MS}` +
          `&readyTabs=${readyTabsNow}&poolSize=${FLOW_POOL_TARGET}&busyTabs=${totalInFlightTabs()}`,
        { method: 'GET', headers: authHeaders() },
      );
      if (resp.ok || resp.status === 204) {
        if (resp.ok) {
          const data = await resp.json().catch(() => ({}));
          commands = Array.isArray(data?.commands) ? data.commands : [];
          const srvPool = Number(data?.desiredPoolSize);
          if (Number.isFinite(srvPool) && srvPool >= 1) {
            const nextPool = Math.max(1, Math.min(MAX_FLOW_POOL_TARGET, Math.round(srvPool)));
            if (nextPool !== FLOW_POOL_TARGET) {
              FLOW_POOL_TARGET = nextPool;
            }
          }
          if (flowTabsNow.length > FLOW_POOL_TARGET && !_pruneTabsPromise) {
            void prunePoolTabs({ targetMax: FLOW_POOL_TARGET, closeAllWorkers: false });
          }
        }
        consecutivePollErrors = 0;
        lastPollOkAt = Date.now();
        void chrome.storage.session.set({ lastPollOkAt });
        if (lastPollOkAt - _lastLocalPollSaveAt >= 30_000) {
          _lastLocalPollSaveAt = lastPollOkAt;
          void chrome.storage.local.set({ lastPollOkAt });
        }
        updateBadge();
        broadcastStatusPush();
      } else {
        consecutivePollErrors += 1;
        metrics.lastError = `POLL_HTTP_${resp.status}`;
        console.warn('[LeVietTung_autoveo] poll HTTP error:', resp.status);
        updateBadge();
        broadcastStatusPush();
      }
    } catch (pollErr) {
      consecutivePollErrors += 1;
      metrics.lastError = `POLL_NET_${pollErr?.message || 'OFFLINE'}`;
      updateBadge();
      broadcastStatusPush();
    }

    for (const cmd of commands) {
      if (cmd.method === 'get_captcha') void handleCaptcha(cmd);
      else if (cmd.method === 'soft_reset') void handleSoftReset(cmd);
      else if (cmd.method === 'hard_reset') void handleHardReset(cmd);
    }

    if (consecutivePollErrors > 0) {
      const backoff = Math.min(8_000, 500 * Math.pow(2, Math.min(consecutivePollErrors, 4)));
      await new Promise((r) => setTimeout(r, backoff));
    }
  }
}

async function probeFlowTab() {
  try {
    const tabs = await chrome.tabs.query({
      url: ['https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*/tools/flow*', 'https://flow.google.com/*'],
    });
    return tabs.length > 0;
  } catch (_) {
    return false;
  }
}

// ── Message Listener for SidePanel, Popup, and Options ────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || typeof msg !== 'object') return false;

  if (msg.type === 'STATUS') {
    (async () => {
      const flowTabs = await listFlowTabs();
      const hasFlowTab = flowTabs.length > 0;
      const readyTabs = flowTabs.filter((t) => !rotatingTabs.has(t.id)).length;
      const flowCookies = await collectFlowAuthCookies();
      const flowSession = await detectFlowSessionInfo({ force: false, knownCookies: flowCookies });
      const hasAuthCookie = flowCookies.some((c) => c.name === 'SID' || c.name.startsWith('__Secure-'));
      const pollAge = lastPollOkAt ? Date.now() - lastPollOkAt : Infinity;
      const agentConnected = !configMissing && !manualDisconnect && consecutivePollErrors === 0 && pollAge < 40_000;
      sendResponse({
        agentConnected,
        state: manualDisconnect ? 'off' : agentConnected ? 'connected' : configMissing ? 'noconfig' : 'connecting',
        bridgeBase,
        bridgeSecret,
        configMissing,
        lastPollOkAt,
        lastMintOkAt,
        lastMintDurationMs,
        hasFlowTab,
        readyTabs,
        poolSize: FLOW_POOL_TARGET,
        busyTabs: totalInFlightTabs(),
        flowKeyPresent: hasAuthCookie,
        flowEmail: flowSession.email || '',
        cookieCount: flowCookies.length,
        metrics,
      });
    })();
    return true;
  }

  if (msg.type === 'REQUEST_LOG') {
    sendResponse({ log: requestLog });
    return false;
  }

  if (msg.type === 'RECONNECT') {
    manualDisconnect = false;
    consecutivePollErrors = 0;
    void loadBridgeConfig().then(() => {
      if (!configMissing) {
        void postJson('/api/internal/captcha/event', {
          type: 'extension_ready',
          version: EXTENSION_VERSION,
        });
        void pollLoop();
      }
      sendResponse({ ok: true });
    });
    return true;
  }

  if (msg.type === 'DISCONNECT') {
    manualDisconnect = true;
    sendResponse({ ok: true });
    return false;
  }

  if (msg.type === 'AUTO_SYNC_CONFIG') {
    (async () => {
      const res = await autoSyncConfigFromBackend(msg.bridgeBase || bridgeBase);
      if (!isPolling && !configMissing && !manualDisconnect) {
        void pollLoop();
      }
      sendResponse(res);
    })();
    return true;
  }

  if (msg.type === 'OPEN_FLOW_TAB') {
    chrome.tabs.create({ url: FLOW_URL, active: true }, () => sendResponse({ ok: true }));
    return true;
  }

  if (msg.type === 'OPEN_OPTIONS') {
    chrome.runtime.openOptionsPage(() => sendResponse({ ok: true }));
    return true;
  }

  if (msg.type === 'REFRESH_TOKEN') {
    (async () => {
      await postJson(
        '/api/internal/captcha/event',
        {
          type: 'heartbeat',
          version: EXTENSION_VERSION,
          hasFlowTab: await probeFlowTab(),
        },
        { includeSession: true },
      );
      sendResponse({ ok: true });
    })();
    return true;
  }

  if (msg.type === 'CLEAN_TABS_CACHE') {
    (async () => {
      const closed = await prunePoolTabs({ closeAllWorkers: true });
      await purgeFlowCache({ force: true, clearAnchorCookies: totalInFlightTabs() === 0, includeStaticCache: true });
      sendResponse({ ok: true, closed });
    })();
    return true;
  }

  return false;
});

chrome.tabs.onRemoved.addListener((tabId) => {
  cleanupTabTracking(tabId);
});

// 24s keepalive + heartbeat + tự dọn tab thừa / hết việc
chrome.alarms.create('upproject-keepalive', { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'upproject-keepalive' && !configMissing && !manualDisconnect) {
    const isIdle = totalInFlightTabs() === 0 && (!lastCommandAt || Date.now() - lastCommandAt >= IDLE_TAB_CLOSE_MS);
    if (isIdle) {
      await prunePoolTabs({ closeAllWorkers: true });
    } else {
      await prunePoolTabs({ targetMax: FLOW_POOL_TARGET, closeAllWorkers: false });
    }
    const flowTabs = await listFlowTabs();
    const hasFlowTab = flowTabs.length > 0;
    const readyTabs = flowTabs.filter((t) => !rotatingTabs.has(t.id)).length;
    const payload = {
      type: 'heartbeat',
      version: EXTENSION_VERSION,
      hasFlowTab: Boolean(hasFlowTab),
      readyTabs,
      poolSize: FLOW_POOL_TARGET,
      busyTabs: totalInFlightTabs(),
    };
    void postJson('/api/internal/captcha/event', payload);
    if (!isPolling) {
      void pollLoop();
    }
  }
});

// ── Bootstrap ─────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  void loadBridgeConfig().then(async () => {
    await prunePoolTabs({ closeAllWorkers: true });
    if (!configMissing) {
      void postJson('/api/internal/captcha/event', {
        type: 'extension_installed',
        version: EXTENSION_VERSION,
      });
      void pollLoop();
    }
  });
});

async function adoptExistingPoolTabsOnWakeup() {
  try {
    const tabs = await listFlowTabs();
    for (const t of tabs) {
      if (t?.id && isPoolWorkerTab(t)) {
        extensionPoolTabIds.add(t.id);
      }
    }
    if (tabs.length > FLOW_POOL_TARGET) {
      await prunePoolTabs({ targetMax: FLOW_POOL_TARGET, closeAllWorkers: false });
    }
  } catch (_) {}
}

void closeDuplicateOptionsTabs();
void loadBridgeConfig().then(async () => {
  await adoptExistingPoolTabsOnWakeup();
  if (!configMissing) {
    const flowTabs = await listFlowTabs();
    void postJson('/api/internal/captcha/event', {
      type: 'extension_ready',
      version: EXTENSION_VERSION,
      readyTabs: flowTabs.length,
      poolSize: FLOW_POOL_TARGET,
    });
    void pollLoop();
  }
});
