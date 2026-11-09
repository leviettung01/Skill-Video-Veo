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
const FLOW_URL = 'https://flow.google.com/';

const EXTENSION_VERSION = chrome.runtime.getManifest().version;
const ANCHOR_NAME_RE = /grecaptcha/i;
const ANCHOR_TOP_LEVEL_SITES = [
  'https://labs.google',
  'https://flow.google.com',
  'https://www.google.com',
  'https://google.com',
];

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

async function detectFlowSessionInfo() {
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
    // Fallback chuẩn Google Flow WIZ HTML ("oPEP7c":"email@gmail.com" + "SNlM0e")
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

function addRequestLog(entry) {
  requestLog.unshift(entry);
  if (requestLog.length > 100) requestLog.pop();
  chrome.storage.local.set({ requestLog, metrics }).catch(() => {});
  chrome.runtime.sendMessage({ type: 'REQUEST_LOG_UPDATE', log: requestLog }).catch(() => {});
  broadcastStatusPush();
}

function updateRequestLog(id, updates) {
  const entry = requestLog.find((e) => e.id === id);
  if (entry) Object.assign(entry, updates);
  chrome.storage.local.set({ requestLog, metrics }).catch(() => {});
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

async function postJson(path, payload) {
  try {
    const flowCookies = await collectFlowAuthCookies();
    const flowSession = await detectFlowSessionInfo();
    const profId = await getOrCreateProfileId();
    await fetch(`${bridgeBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ profileId: profId, flowCookies, flowSession, ...payload }),
    });
  } catch (e) {
    console.warn('[LeVietTung_autoveo] post failed:', path, e?.message || e);
  }
}

// ── Tab helpers ───────────────────────────────────────────────────────

async function findFlowTab() {
  const [labsTabs, flowTabs] = await Promise.all([
    chrome.tabs.query({ url: 'https://labs.google/*' }),
    chrome.tabs.query({ url: 'https://flow.google.com/*' }),
  ]);
  const allTabs = [...flowTabs, ...labsTabs];
  const tabs = allTabs.filter((tab) => {
    try {
      const u = new URL(tab.url || '');
      if (u.hostname === 'flow.google.com') return true;
      if (u.hostname === 'labs.google') {
        return /^\/fx\/(?:[^/]+\/)?tools\/flow(?:\/|$)/.test(u.pathname);
      }
      return false;
    } catch (_) {
      return false;
    }
  });
  return tabs.length > 0 ? tabs[0] : null;
}

async function ensureContentScript(tabId) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      world: 'MAIN',
      func: () => {
        if (window.__upprojectHijackBypassInstalled) return;
        window.__upprojectHijackBypassInstalled = true;
        try {
          const origAssign = Object.assign;
          Object.assign = function (target, ...sources) {
            const res = origAssign.apply(this, [target, ...sources]);
            if (res && res.action === 'extension_hijack_detected') {
              for (const src of sources) {
                if (
                  src &&
                  typeof src.action === 'string' &&
                  src.action !== 'extension_hijack_detected'
                ) {
                  res.action = src.action;
                  break;
                }
              }
            }
            return res;
          };
        } catch (_) {}
      },
    });
  } catch (_) {}
  return chrome.scripting
    .executeScript({ target: { tabId }, files: ['content.js'] })
    .catch(() => undefined);
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
        { origins: ['https://www.google.com', 'https://www.recaptcha.net'] },
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

async function handleCaptcha(command) {
  const { commandId, action } = command;
  const startedAt = Date.now();
  const logId = commandId || `mint-${startedAt}`;

  metrics.requestCount += 1;
  const isFlowRpc = typeof action === 'string' && action.startsWith('__FLOW_RPC__:');
  addRequestLog({
    id: logId,
    type: isFlowRpc ? 'FLOW_RPC' : (action || 'GET_CAPTCHA'),
    time: new Date().toISOString(),
    status: 'PROCESSING',
    url: FLOW_URL,
    payloadSummary: isFlowRpc ? action.slice(0, 120) : `reCAPTCHA action=${action}`,
  });

  let tab = await findFlowTab();
  if (!tab?.id) {
    try {
      tab = await chrome.tabs.create({ url: FLOW_URL, active: false });
      if (tab?.id) {
        await waitForTabLoad(tab.id, 25_000);
        await new Promise((r) => setTimeout(r, 2000));
      }
    } catch (_) {}
  }
  if (!tab?.id) {
    metrics.failedCount += 1;
    updateRequestLog(logId, { status: 'FAILED', error: 'NO_FLOW_TAB' });
    await postJson('/api/internal/captcha/result', { commandId, error: 'NO_FLOW_TAB' });
    return;
  }

  await ensureContentScript(tab.id);

  const ask = (timeoutMs) =>
    new Promise((resolve) => {
      const timer = setTimeout(() => resolve({ error: 'CAPTCHA_TIMEOUT' }), timeoutMs);
      chrome.tabs.sendMessage(
        tab.id,
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

  let reply = await ask(25_000);
  if (!reply?.token) {
    await ensureContentScript(tab.id);
    await new Promise((r) => setTimeout(r, 200));
    reply = await ask(20_000);
  }

  if (reply?.token) {
    const durationMs = Date.now() - startedAt;
    lastMintOkAt = Date.now();
    lastMintDurationMs = durationMs;
    metrics.successCount += 1;
    void chrome.storage.session.set({
      lastMintOkAt,
      lastMintDurationMs,
    });
    void chrome.storage.local.set({
      lastMintOkAt,
      lastMintDurationMs,
      metrics,
    });
    updateRequestLog(logId, {
      status: 'COMPLETED',
      httpStatus: 200,
      responseSummary: `Token minted in ${durationMs}ms (${String(reply.token).slice(0, 24)}...)`,
    });
    await postJson('/api/internal/captcha/result', { commandId, token: reply.token });
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
}

async function handleSoftReset(command) {
  const { commandId } = command;
  let tab = await findFlowTab();
  if (!tab?.id) {
    try {
      tab = await chrome.tabs.create({ url: FLOW_URL, active: false });
      if (tab?.id) {
        await waitForTabLoad(tab.id, 25_000);
        await new Promise((r) => setTimeout(r, 2000));
      }
    } catch (_) {}
  }
  if (!tab?.id) {
    await postJson('/api/internal/captcha/result', { commandId, error: 'NO_FLOW_TAB' });
    return;
  }
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      world: 'MAIN',
      func: () => {
        const keys = Object.keys(localStorage).filter((k) => k.startsWith('_grecaptcha'));
        keys.forEach((k) => localStorage.removeItem(k));
        return keys.length;
      },
    });
    await clearRecaptchaCookieAnchor();
    await postJson('/api/internal/captcha/event', {
      type: 'extension_ready',
      version: EXTENSION_VERSION,
    });
    await postJson('/api/internal/captcha/result', { commandId, token: 'soft_reset_ok' });
  } catch (e) {
    await postJson('/api/internal/captcha/result', {
      commandId,
      error: e?.message || 'SOFT_RESET_FAILED',
    });
  }
}

async function handleHardReset(command) {
  const { commandId } = command;
  let tab = await findFlowTab();
  if (!tab?.id) {
    try {
      tab = await chrome.tabs.create({ url: FLOW_URL, active: false });
      if (tab?.id) {
        await waitForTabLoad(tab.id, 25_000);
        await new Promise((r) => setTimeout(r, 2000));
      }
    } catch (_) {}
  }
  if (!tab?.id) {
    await postJson('/api/internal/captcha/result', { commandId, error: 'NO_FLOW_TAB' });
    return;
  }
  try {
    await clearRecaptchaCookieAnchor();
    await chrome.tabs.update(tab.id, { url: 'about:blank' });
    await new Promise((r) => setTimeout(r, 1500));
    await chrome.tabs.update(tab.id, { url: FLOW_URL });
    await waitForTabLoad(tab.id, 30_000);
    await new Promise((r) => setTimeout(r, 2500));
    await postJson('/api/internal/captcha/event', {
      type: 'extension_ready',
      version: EXTENSION_VERSION,
    });
    await postJson('/api/internal/captcha/result', { commandId, token: 'hard_reset_ok' });
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
      const resp = await fetch(
        `${bridgeBase}/api/internal/captcha/poll` +
          `?profileId=${encodeURIComponent(profId)}&timeout=${POLL_TIMEOUT_MS}`,
        { method: 'GET', headers: authHeaders() },
      );
      if (resp.ok || resp.status === 204) {
        if (resp.ok) {
          const data = await resp.json().catch(() => ({}));
          commands = Array.isArray(data?.commands) ? data.commands : [];
        }
        consecutivePollErrors = 0;
        lastPollOkAt = Date.now();
        void chrome.storage.session.set({ lastPollOkAt });
        void chrome.storage.local.set({ lastPollOkAt });
        updateBadge();
        broadcastStatusPush();
      } else {
        consecutivePollErrors += 1;
        updateBadge();
        broadcastStatusPush();
      }
    } catch {
      consecutivePollErrors += 1;
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
      const hasFlowTab = await probeFlowTab();
      const flowCookies = await collectFlowAuthCookies();
      const flowSession = await detectFlowSessionInfo();
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
      await postJson('/api/internal/captcha/event', {
        type: 'heartbeat',
        version: EXTENSION_VERSION,
        hasFlowTab: await probeFlowTab(),
      });
      sendResponse({ ok: true });
    })();
    return true;
  }

  return false;
});

// 24s keepalive + heartbeat
chrome.alarms.create('upproject-keepalive', { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'upproject-keepalive' && !configMissing && !manualDisconnect) {
    const hasFlowTab = await probeFlowTab();
    const payload = { type: 'heartbeat', version: EXTENSION_VERSION, hasFlowTab: Boolean(hasFlowTab) };
    void postJson('/api/internal/captcha/event', payload);
    if (!isPolling) {
      void pollLoop();
    }
  }
});

// ── Bootstrap ─────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  void loadBridgeConfig().then(() => {
    if (!configMissing) {
      void postJson('/api/internal/captcha/event', {
        type: 'extension_installed',
        version: EXTENSION_VERSION,
      });
      void pollLoop();
    }
  });
});

void closeDuplicateOptionsTabs();
void loadBridgeConfig().then(() => {
  if (!configMissing) {
    void postJson('/api/internal/captcha/event', {
      type: 'extension_ready',
      version: EXTENSION_VERSION,
    });
    void pollLoop();
  }
});
