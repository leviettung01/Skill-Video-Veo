/**
 * Flow Kit — Chrome Extension Background Service Worker
 *
 * Connects to local Python agent via WebSocket (agent runs WS server).
 * Captures bearer token, solves reCAPTCHA, proxies API calls through browser.
 */

const AGENT_WS_URL = 'ws://127.0.0.1:9888';
const API_KEY = 'AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY';
const FLOW_TAB_URLS = [
  'https://labs.google/*',
  'https://flow.google.com/*',
  'https://*.google.com/*',
];

let ws = null;
let flowKey = null;
let callbackSecret = null;
let state = 'idle';
let manualDisconnect = false;
let metrics = {
  tokenCapturedAt: null,
  requestCount: 0,
  successCount: 0,
  failedCount: 0,
  lastError: null,
};

// ─── URL → Log Type Classifier ─────────────────────────────

const _VISIBLE_TYPES = new Set(['GEN_IMG', 'GEN_VID', 'GEN_VID_REF', 'UPSCALE', 'TRACKING', 'URL_REFRESH']);

function _classifyApiUrl(url) {
  if (url.includes('uploadImage'))                     return 'UPLOAD';
  if (url.includes('batchGenerateImages'))              return 'GEN_IMG';
  if (url.includes('UpsampleVideo'))                   return 'UPSCALE';
  if (url.includes('ReferenceImages'))                 return 'GEN_VID_REF';
  if (url.includes('batchAsyncGenerateVideo'))          return 'GEN_VID';
  if (url.includes('batchCheckAsync'))                  return 'POLL';
  if (url.includes('upsampleImage'))                   return 'UPS_IMG';
  if (url.includes('/media/'))                         return 'MEDIA';
  if (url.includes('/credits'))                        return 'CREDITS';
  return 'API';
}

// ─── Request Log ────────────────────────────────────────────

let requestLog = [];

function addRequestLog(entry) {
  requestLog.unshift(entry);
  if (requestLog.length > 100) requestLog.pop();
  broadcastRequestLog();
}

function updateRequestLog(id, updates) {
  const entry = requestLog.find((e) => e.id === id);
  if (entry) Object.assign(entry, updates);
  broadcastRequestLog();
}

function broadcastRequestLog() {
  chrome.runtime.sendMessage({ type: 'REQUEST_LOG_UPDATE', log: requestLog }).catch(() => {});
}

// ─── Startup ────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(init);
chrome.runtime.onStartup.addListener(init);
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'reconnect') connectToAgent();
  if (alarm.name === 'keepAlive') keepAlive();
  if (alarm.name === 'token-refresh') {
    await captureTokenFromFlowTab();
  }
});

async function init() {
  const data = await chrome.storage.local.get(['flowKey', 'metrics', 'callbackSecret']);
  if (data.flowKey) flowKey = data.flowKey;
  if (data.metrics) Object.assign(metrics, data.metrics);
  if (data.callbackSecret) callbackSecret = data.callbackSecret;
  connectToAgent();
  chrome.alarms.create('keepAlive', { periodInMinutes: 0.4 });
}

// ─── Token Capture ──────────────────────────────────────────

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    if (!details?.requestHeaders?.length) return;
    const authHeader = details.requestHeaders.find(
      (h) => h.name?.toLowerCase() === 'authorization',
    );
    const value = authHeader?.value || '';
    if (!value.startsWith('Bearer ya29.')) return;

    const token = value.replace(/^Bearer\s+/i, '').trim();
    if (!token) return;

    if (token === flowKey) return;

    flowKey = token;
    metrics.tokenCapturedAt = Date.now();
    chrome.storage.local.set({ flowKey, metrics });
    console.log('[FlowAgent] Bearer token captured');

    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
    }
  },
  { urls: ['https://aisandbox-pa.googleapis.com/*', 'https://labs.google/*', 'https://flow.google.com/*'] },
  ['requestHeaders', 'extraHeaders'],
);

async function fetchTokenFromSession() {
  try {
    const tabs = await chrome.tabs.query({
      url: FLOW_TAB_URLS,
    });
    if (tabs.length) {
      const tabId = tabs[0].id;
      console.log('[FlowAgent] Fetching token via scripting in active tab:', tabId);
      const results = await chrome.scripting.executeScript({
        target: { tabId },
        func: async () => {
          try {
            // Try flow.google.com first, then labs.google path
            let resp = await fetch('/api/auth/session').catch(() => null);
            if (!resp || !resp.ok) {
              resp = await fetch('/fx/api/auth/session').catch(() => null);
            }
            if (resp && resp.ok) {
              const data = await resp.json();
              return data?.accessToken || data?.access_token || null;
            }
          } catch (e) {
            console.error('[FlowAgent script] Fetch failed in tab:', e);
          }
          return null;
        }
      });
      const token = results?.[0]?.result;
      if (token && token.startsWith('ya29.')) {
        flowKey = token;
        metrics.tokenCapturedAt = Date.now();
        chrome.storage.local.set({ flowKey, metrics });
        console.log('[FlowAgent] Bearer token retrieved from tab scripting:', token.slice(0, 15));
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
        }
        broadcastStatus();
        return true;
      }
    }
  } catch (e) {
    console.error('[FlowAgent] ExecuteScript session fetch failed:', e);
  }

  try {
    const url = 'https://labs.google/fx/api/auth/session';
    const resp = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
      }
    });
    if (resp.ok) {
      const data = await resp.json();
      const token = data?.accessToken;
      if (token && token.startsWith('ya29.')) {
        flowKey = token;
        metrics.tokenCapturedAt = Date.now();
        chrome.storage.local.set({ flowKey, metrics });
        console.log('[FlowAgent] Bearer token fetched directly from background session:', token.slice(0, 15));
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
        }
        broadcastStatus();
        return true;
      }
    }
  } catch (e) {
    console.error('[FlowAgent] Failed to fetch token from background session:', e);
  }
  return false;
}

let _openingFlowTab = false;

async function captureTokenFromFlowTab() {
  const gotToken = await fetchTokenFromSession();
  if (gotToken) return true;

  const previousCapturedAt = metrics.tokenCapturedAt || 0;
  const tabs = await chrome.tabs.query({
    url: FLOW_TAB_URLS,
  });
  if (!tabs.length) {
    if (_openingFlowTab) {
      console.log('[FlowAgent] Flow tab already opening, skipping');
      return false;
    }
    _openingFlowTab = true;
    try {
      console.log('[FlowAgent] No Flow tab found — opening one');
      await chrome.tabs.create({ url: 'https://flow.google.com/', active: true });
      const refreshed = await waitForNewFlowToken(previousCapturedAt);
      console.log(`[FlowAgent] Token refresh on new Flow tab: ${refreshed ? 'ok' : 'timed out'}`);
      return refreshed;
    } catch (e) {
      console.error('[FlowAgent] Token refresh failed after opening tab:', e);
      return false;
    } finally {
      _openingFlowTab = false;
    }
  }
  try {
    await chrome.tabs.reload(tabs[0].id, { bypassCache: true });
    const refreshed = await waitForNewFlowToken(previousCapturedAt);
    console.log(`[FlowAgent] Token refresh on existing Flow tab: ${refreshed ? 'ok' : 'timed out'}`);
    return refreshed;
  } catch (e) {
    console.error('[FlowAgent] Token refresh failed:', e);
    return false;
  }
}

async function waitForNewFlowToken(previousCapturedAt, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (flowKey && (metrics.tokenCapturedAt || 0) > previousCapturedAt) return true;
    await sleep(400);
  }
  return false;
}

// ─── WebSocket to Agent ─────────────────────────────────────

function connectToAgent() {
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return;

  try {
    ws = new WebSocket(AGENT_WS_URL);
  } catch (e) {
    console.error('[FlowAgent] WS connect error:', e);
    setTimeout(connectToAgent, 1500);
    return;
  }

  ws.onopen = async () => {
    console.log('[FlowAgent] Connected to agent');
    chrome.alarms.clear('reconnect');
    setState('idle');

    await fetchTokenFromSession();
    chrome.alarms.create('token-refresh', { periodInMinutes: 45 });

    ws.send(JSON.stringify({
      type: 'extension_ready',
      flowKeyPresent: !!flowKey,
      tokenAge: flowKey && metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
    }));
    if (flowKey) {
      ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
    }
  };

  ws.onmessage = async ({ data }) => {
    try {
      const msg = JSON.parse(data);

      if (msg.method === 'api_request') {
        if (msg.params?.url?.startsWith('https://labs.google/') || msg.params?.url?.startsWith('https://flow.google.com/')) {
          await handleTrpcRequest(msg);
        } else {
          await handleApiRequest(msg);
        }
      } else if (msg.method === 'trpc_request') {
        await handleTrpcRequest(msg);
      } else if (msg.method === 'solve_captcha') {
        await handleSolveCaptcha(msg);
      } else if (msg.method === 'get_status') {
        sendToAgent({
          id: msg.id,
          result: {
            state,
            flowKeyPresent: !!flowKey,
            manualDisconnect,
            tokenAge: metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
            metrics,
          },
        });
      } else if (msg.method === 'get_cookies') {
        try {
          const cookies = await chrome.cookies.getAll({ domain: 'google.com' });
          const labsCookies = await chrome.cookies.getAll({ domain: 'labs.google' });
          const allCookies = [...cookies, ...labsCookies];
          const cookieHeader = allCookies.map(c => `${c.name}=${c.value}`).join('; ');
          sendToAgent({ id: msg.id, result: { cookieHeader, count: allCookies.length } });
        } catch (e) {
          sendToAgent({ id: msg.id, error: e.message });
        }
      } else if (msg.method === 'script_extract_videos') {
        try {
          const tabs = await chrome.tabs.query({
            url: FLOW_TAB_URLS,
          });
          if (!tabs.length) {
            sendToAgent({ id: msg.id, error: 'NO_FLOW_TAB' });
            return;
          }
          const results = await chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            func: () => {
              const items = [];
              for (const v of document.querySelectorAll('video, source')) {
                const src = v.src || v.currentSrc;
                if (src) items.push({ type: 'video_tag', url: src });
              }
              for (const p of performance.getEntriesByType('resource')) {
                if (p.name && (p.name.includes('storage.googleapis.com') || p.name.includes('.mp4') || p.name.includes('googleusercontent.com'))) {
                  items.push({ type: 'performance', url: p.name });
                }
              }
              for (const a of document.querySelectorAll('a[download], a[href*="storage.googleapis.com"]')) {
                if (a.href) items.push({ type: 'link', url: a.href });
              }
              return items;
            },
          });
          const found = results?.[0]?.result || [];
          sendToAgent({ id: msg.id, result: { count: found.length, items: found } });
        } catch (e) {
          sendToAgent({ id: msg.id, error: e.message });
        }
      } else if (msg.method === 'extract_page_media') {
        await handleExtractPageMedia(msg);
      } else if (msg.method === 'reload_extension') {
        sendToAgent({ id: msg.id, result: { reloading: true } });
        setTimeout(() => chrome.runtime.reload(), 100);
      } else if (msg.type === 'callback_secret') {
        callbackSecret = msg.secret;
        chrome.storage.local.set({ callbackSecret: msg.secret });
        console.log('[FlowAgent] Received callback secret');
      } else if (msg.type === 'pong') {
        // keepalive response
      }
    } catch (e) {
      console.error('[FlowAgent] Message error:', e);
    }
  };

  ws.onclose = () => {
    setState('idle');
    setTimeout(connectToAgent, 1500);
  };

  ws.onerror = (e) => {
    console.error('[FlowAgent] WS error:', e);
    metrics.lastError = 'WS_ERROR';
    setTimeout(connectToAgent, 1500);
  };
}

function scheduleReconnect() {
  chrome.alarms.create('reconnect', { delayInMinutes: 0.083 }); // ~5s
}

function keepAlive() {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  } else {
    connectToAgent();
  }
}

function sendToAgent(msg) {
  if (msg.id) {
    fetch('http://127.0.0.1:8100/api/ext/callback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(msg),
    }).catch(() => {
      if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
    });
    return;
  }
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

// ─── reCAPTCHA Solving ──────────────────────────────────────

async function solveCaptchaDirect(tabId, captchaAction) {
  const SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      world: 'MAIN',
      func: async (siteKey, action) => {
        const start = Date.now();
        while (!window.grecaptcha?.enterprise?.execute) {
          if (Date.now() - start > 12000) throw new Error('grecaptcha not ready');
          await new Promise(r => setTimeout(r, 200));
        }
        return await window.grecaptcha.enterprise.execute(siteKey, { action });
      },
      args: [SITE_KEY, captchaAction || 'VIDEO_GENERATION'],
    });
    const token = results?.[0]?.result;
    if (token && typeof token === 'string' && token.length > 20) {
      return { token };
    }
  } catch (e) {
    console.warn('[FlowAgent] Direct executeScript captcha failed:', e);
  }
  return null;
}

async function requestCaptchaFromTab(tabId, requestId, pageAction) {
  const direct = await solveCaptchaDirect(tabId, pageAction);
  if (direct?.token) return direct;

  let lastError = null;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      return await chrome.tabs.sendMessage(tabId, {
        type: 'GET_CAPTCHA',
        requestId,
        pageAction,
      });
    } catch (error) {
      lastError = error;
      const msg = String(error?.message || '');
      const transient = /No SW|Receiving end does not exist|Could not establish connection|message channel closed|asynchronous response|The tab was closed|frame with ID/i.test(msg);
      if (!transient || attempt >= 2) break;
      try {
        await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
      } catch (injectError) {
        lastError = injectError;
      }
      await sleep(500 + attempt * 700);
    }
  }
  throw lastError || new Error('CAPTCHA_CHANNEL_FAILED');
}

async function solveCaptcha(requestId, captchaAction) {
  const tabs = await chrome.tabs.query({
    url: ['https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*/tools/flow*', 'https://flow.google.com/*'],
  });

  if (!tabs.length) {
    try {
      const createdTab = await chrome.tabs.create({ url: 'https://flow.google.com/', active: false });
      await sleep(8000);
      const targetTabId = createdTab?.id;
      if (!targetTabId) return { error: 'NO_FLOW_TAB' };
      let lastError = null;
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          return await Promise.race([
            requestCaptchaFromTab(targetTabId, `${requestId}-${attempt}`, captchaAction),
            new Promise((_, rej) => setTimeout(() => rej(new Error('CAPTCHA_TIMEOUT')), 35000)),
          ]);
        } catch (e) {
          lastError = e;
          await sleep(1000 + attempt * 1500);
        }
      }
      return { error: lastError?.message || 'CAPTCHA_FAILED' };
    } catch (e) {
      return { error: e.message || 'NO_FLOW_TAB' };
    }
  }

  let lastError = null;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      return await Promise.race([
        requestCaptchaFromTab(tabs[0].id, `${requestId}-${attempt}`, captchaAction),
        new Promise((_, rej) => setTimeout(() => rej(new Error('CAPTCHA_TIMEOUT')), 35000)),
      ]);
    } catch (e) {
      lastError = e;
      await sleep(1000 + attempt * 1500);
    }
  }
  return { error: lastError?.message || 'CAPTCHA_FAILED' };
}

async function handleSolveCaptcha(msg) {
  const { id, params } = msg;
  const result = await solveCaptcha(id, params?.captchaAction || 'VIDEO_GENERATION');

  metrics.requestCount++;
  if (result?.token) {
    metrics.successCount++;
  } else {
    metrics.failedCount++;
    metrics.lastError = result?.error || 'NO_TOKEN';
  }
  chrome.storage.local.set({ metrics });

  sendToAgent({ id, result });
}

// ─── API Request Proxy ──────────────────────────────────────

async function handleTrpcRequest(msg) {
  const { id, params } = msg;
  const { url, method = 'POST', headers = {}, body } = params;

  if (!url || (!url.startsWith('https://labs.google/') && !url.startsWith('https://flow.google.com/'))) {
    sendToAgent({ id, error: 'INVALID_TRPC_URL' });
    return;
  }

  setState('running');
  const logId = id;
  const logType = url.includes('createProject') ? 'CREATE_PROJECT' : 'TRPC';

  const isMediaRedirect = url.includes('/media.getMediaUrlRedirect');
  const fetchHeaders = { ...(body ? { 'Content-Type': 'application/json' } : {}), ...headers };
  if (!isMediaRedirect && flowKey && !fetchHeaders['authorization'] && !fetchHeaders['Authorization']) {
    fetchHeaders['authorization'] = `Bearer ${flowKey}`;
  }
  if (isMediaRedirect) {
    delete fetchHeaders['authorization'];
    delete fetchHeaders['Authorization'];
    delete fetchHeaders['content-type'];
    delete fetchHeaders['Content-Type'];
  }

  try {
    const resp = await fetch(url, {
      method: isMediaRedirect ? 'GET' : method,
      headers: fetchHeaders,
      body: (!isMediaRedirect && body) ? JSON.stringify(body) : undefined,
      credentials: 'include',
      redirect: 'follow',
    });
    if (isMediaRedirect) {
      const finalUrl = (resp.url && resp.url !== url && resp.url.startsWith('https://')) ? resp.url : '';
      const location = resp.headers.get('location') || resp.headers.get('Location') || '';
      const resolved = finalUrl || location;
      const data = {
        location: resolved,
        url: resolved,
        redirectUrl: resolved,
        redirected: resp.redirected,
        status: resp.status,
      };
      chrome.storage.local.set({ metrics });
      updateRequestLog(logId, { status: 'success' });
      sendToAgent({ id, status: resp.status, data });
      return;
    }
    const data = await resp.json();
    chrome.storage.local.set({ metrics });
    updateRequestLog(logId, { status: 'success' });
    sendToAgent({ id, status: resp.status, data });
  } catch (e) {
    console.error('[FlowAgent] tRPC request failed:', e);
    chrome.storage.local.set({ metrics });
    updateRequestLog(logId, { status: 'failed', error: e.message || 'TRPC_FETCH_FAILED' });
    sendToAgent({ id, error: e.message || 'TRPC_FETCH_FAILED' });
  } finally {
    setState('idle');
  }
}

async function handleApiRequest(msg) {
  const { id, params } = msg;
  const { url, method, headers, body, captchaAction } = params;

  if (!url) {
    sendToAgent({ id, error: 'MISSING_URL' });
    return;
  }

  if (!url.startsWith('https://aisandbox-pa.googleapis.com/')) {
    sendToAgent({ id, error: 'INVALID_URL' });
    return;
  }

  setState('running');
  const hasCaptcha = !!captchaAction;
  if (hasCaptcha) metrics.requestCount++;

  const logId = id;
  const logType = _classifyApiUrl(url);
  if (_VISIBLE_TYPES.has(logType)) {
    const payloadSummary = body ? JSON.stringify(body).slice(0, 200) : null;
    addRequestLog({ id: logId, type: logType, time: new Date().toISOString(), status: 'processing', error: null, outputUrl: null, url, payloadSummary });
  }

  try {
    const tokenAge = metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : Infinity;
    if (!flowKey || tokenAge > 50 * 60 * 1000) {
      await captureTokenFromFlowTab();
    }

    // Step 1: Solve captcha if needed
    let captchaToken = null;
    if (captchaAction) {
      let captchaResult = null;
      for (let attempt = 0; attempt < 3 && !captchaToken; attempt++) {
        captchaResult = await solveCaptcha(`${id}-captcha-${attempt}`, captchaAction);
        captchaToken = captchaResult?.token || null;
        if (!captchaToken && attempt < 2) await sleep(1200 + attempt * 1800);
      }
      if (!captchaToken) {
        const err = captchaResult?.error || 'CAPTCHA_FAILED';
        console.error(`[FlowAgent] Captcha failed for ${captchaAction}: ${err}`);
        sendToAgent({ id, status: 403, error: `CAPTCHA_FAILED: ${err}` });
        if (hasCaptcha) { metrics.failedCount++; metrics.lastError = `CAPTCHA_FAILED: ${err}`; }
        chrome.storage.local.set({ metrics });
        updateRequestLog(logId, { status: 'failed', error: `CAPTCHA_FAILED: ${err}` });
        setState('idle');
        return;
      }
    }

    // Step 2: Inject captcha token into body
    let finalBody = body;
    if (captchaToken && finalBody) {
      finalBody = JSON.parse(JSON.stringify(finalBody));
      if (finalBody.clientContext?.recaptchaContext) {
        finalBody.clientContext.recaptchaContext.token = captchaToken;
      }
      if (finalBody.requests && Array.isArray(finalBody.requests)) {
        for (const req of finalBody.requests) {
          if (req.clientContext?.recaptchaContext) {
            req.clientContext.recaptchaContext.token = captchaToken;
          }
        }
      }
    }

    // Step 3: Use flowKey for auth
    const activeFlowKey = flowKey;
    if (!activeFlowKey) {
      sendToAgent({ id, status: 503, error: 'NO_FLOW_KEY' });
      if (hasCaptcha) { metrics.failedCount++; metrics.lastError = 'NO_FLOW_KEY'; }
      chrome.storage.local.set({ metrics });
      updateRequestLog(logId, { status: 'failed', error: 'NO_FLOW_KEY' });
      setState('idle');
      return;
    }

    const fetchHeaders = { ...(headers || {}) };
    fetchHeaders['authorization'] = `Bearer ${activeFlowKey}`;

    // Step 4: Make the API call from browser context
    let response = await fetch(url, {
      method: method || 'POST',
      headers: fetchHeaders,
      credentials: 'include',
      body: method === 'GET' ? undefined : JSON.stringify(finalBody),
    });

    if (response.status === 401 && await captureTokenFromFlowTab() && flowKey) {
      let retryBody = finalBody;
      if (captchaAction) {
        const retryCaptcha = await solveCaptcha(`${id}-auth-retry`, captchaAction);
        if (retryCaptcha?.token && body) {
          retryBody = JSON.parse(JSON.stringify(body));
          if (retryBody.clientContext?.recaptchaContext) {
            retryBody.clientContext.recaptchaContext.token = retryCaptcha.token;
          }
          if (Array.isArray(retryBody.requests)) {
            for (const req of retryBody.requests) {
              if (req.clientContext?.recaptchaContext) {
                req.clientContext.recaptchaContext.token = retryCaptcha.token;
              }
            }
          }
        }
      }
      fetchHeaders['authorization'] = `Bearer ${flowKey}`;
      response = await fetch(url, {
        method: method || 'POST',
        headers: fetchHeaders,
        credentials: 'include',
        body: method === 'GET' ? undefined : JSON.stringify(retryBody),
      });
    }

    let responseData;
    const responseText = await response.text();
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = responseText;
    }

    sendToAgent({
      id,
      status: response.status,
      data: responseData,
    });

    const responseSummary = responseText ? responseText.slice(0, 300) : null;
    if (response.ok) {
      if (hasCaptcha) { metrics.successCount++; metrics.lastError = null; }
      updateRequestLog(logId, { status: 'success', httpStatus: response.status, responseSummary });
    } else {
      if (hasCaptcha) { metrics.failedCount++; metrics.lastError = `API_${response.status}`; }
      updateRequestLog(logId, { status: 'failed', error: `API_${response.status}`, httpStatus: response.status, responseSummary });
    }
  } catch (e) {
    sendToAgent({
      id,
      status: 500,
      error: e.message || 'API_REQUEST_FAILED',
    });
    if (hasCaptcha) { metrics.failedCount++; metrics.lastError = e.message; }
    updateRequestLog(logId, { status: 'failed', error: e.message || 'API_REQUEST_FAILED' });
  }

  chrome.storage.local.set({ metrics });
  setState('idle');
}

// ─── State & Popup ──────────────────────────────────────────

function setState(newState) {
  state = newState;
  const badges = { idle: '●', running: '▶', off: '○' };
  const colors = { idle: '#22c55e', running: '#f59e0b', off: '#6b7280' };
  chrome.action.setBadgeText({ text: badges[state] || '' });
  chrome.action.setBadgeBackgroundColor({ color: colors[state] || '#000' });
  broadcastStatus();
}

function broadcastStatus() {
  chrome.runtime.sendMessage({ type: 'STATUS_PUSH' }).catch(() => {});
}

chrome.runtime.onMessage.addListener((msg, _, reply) => {
  if (msg.type === 'HEARTBEAT') {
    if (!manualDisconnect && (!ws || ws.readyState === WebSocket.CLOSED)) {
      connectToAgent();
    }
    reply({ ok: true, connected: ws?.readyState === WebSocket.OPEN });
    return true;
  }

  if (msg.type === 'STATUS') {
    if (!manualDisconnect && (!ws || ws.readyState === WebSocket.CLOSED)) {
      connectToAgent();
    }
    reply({
      connected: ws?.readyState === WebSocket.OPEN,
      agentConnected: ws?.readyState === WebSocket.OPEN,
      flowKeyPresent: !!flowKey,
      manualDisconnect,
      tokenAge: metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
      metrics: {
        requestCount: metrics.requestCount,
        successCount: metrics.successCount,
        failedCount: metrics.failedCount,
        lastError: metrics.lastError,
      },
      state,
    });
  }

  if (msg.type === 'TOKEN_CAPTURED' && msg.token) {
    const token = String(msg.token).trim();
    if (token && token !== flowKey) {
      flowKey = token;
      metrics.tokenCapturedAt = Date.now();
      chrome.storage.local.set({ flowKey, metrics });
      console.log('[FlowAgent] Bearer token captured from page fetch/XHR');
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
      }
      broadcastStatus();
    }
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'DISCONNECT') {
    manualDisconnect = true;
    if (ws) ws.close();
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'RECONNECT') {
    manualDisconnect = false;
    connectToAgent();
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'REQUEST_LOG') {
    reply({ log: requestLog });
    return true;
  }

  if (msg.type === 'OPEN_FLOW_TAB') {
    chrome.tabs.query({
      url: FLOW_TAB_URLS,
    }).then((tabs) => {
      if (tabs.length) {
        chrome.tabs.update(tabs[0].id, { active: true });
        reply({ ok: true, tabId: tabs[0].id });
      } else {
        chrome.tabs.create({ url: 'https://flow.google.com/' })
          .then((tab) => reply({ ok: true, tabId: tab.id }))
          .catch((e) => reply({ error: e.message }));
      }
    }).catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === 'REFRESH_TOKEN') {
    captureTokenFromFlowTab()
      .then(() => reply({ ok: true }))
      .catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === 'TEST_CAPTCHA') {
    solveCaptcha(`test-${Date.now()}`, msg.pageAction || 'IMAGE_GENERATION')
      .then((r) => reply(r))
      .catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === 'TRPC_MEDIA_URLS') {
    handleTrpcMediaUrls(msg.trpcUrl, msg.body);
    reply({ ok: true });
    return true;
  }

  return true;
});

// ─── TRPC Media URL Extractor ──────────────────────────────

function handleTrpcMediaUrls(trpcUrl, bodyText) {
  try {
    const urlMap = {};
    const uuidRe = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

    try {
      const parsed = JSON.parse(bodyText);
      const stack = [parsed];
      while (stack.length) {
        const item = stack.pop();
        if (!item || typeof item !== 'object') continue;
        if (Array.isArray(item)) {
          stack.push(...item);
          continue;
        }
        let mid = item.mediaId || item.primaryMediaId || item.id || item.name;
        if (typeof mid === 'string' && uuidRe.test(mid)) {
          const matchedId = mid.match(uuidRe)[0];
          const urlCandidate = item.url || item.fifeUrl || item.servingUri || item.videoUrl || item.downloadUrl || item.imageUri || item.src;
          if (typeof urlCandidate === 'string' && urlCandidate.startsWith('http')) {
            const mediaType = (item.mediaType === 'image' || urlCandidate.includes('image')) ? 'image' : 'video';
            urlMap[matchedId] = { mediaId: matchedId, mediaType, url: urlCandidate };
          }
        }
        for (const val of Object.values(item)) {
          if (val && typeof val === 'object') stack.push(val);
        }
      }
    } catch {}

    const urlRegex = /https:\/\/(?:storage\.googleapis\.com|[\w\-.]+\.googleusercontent\.com|aisandbox-pa\.googleapis\.com)[^\s"'<>]+/gi;
    const matches = String(bodyText || '').match(urlRegex) || [];
    for (const rawUrl of matches) {
      const url = rawUrl.replace(/\\u0026/g, '&').replace(/\\/g, '');
      const mediaMatch = url.match(uuidRe);
      if (mediaMatch) {
        const mediaId = mediaMatch[0];
        if (!urlMap[mediaId]) {
          const mediaType = url.includes('image') ? 'image' : 'video';
          urlMap[mediaId] = { mediaType, url, mediaId };
        }
      }
    }

    const entries = Object.values(urlMap);
    if (!entries.length) return;

    console.log(`[FlowAgent] Captured ${entries.length} fresh media URLs`);
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'media_urls_refresh',
        urls: entries,
      }));
    }
  } catch (e) {
    console.error('[FlowAgent] Failed to extract TRPC media URLs:', e);
  }
}

async function handleExtractPageMedia(msg) {
  try {
    const tabs = await chrome.tabs.query({
      url: FLOW_TAB_URLS,
    });
    if (!tabs.length) {
      sendToAgent({ id: msg.id, error: 'NO_FLOW_TAB' });
      return;
    }
    chrome.tabs.sendMessage(tabs[0].id, { type: 'EXTRACT_PAGE_MEDIA' }, (response) => {
      if (chrome.runtime.lastError) {
        sendToAgent({ id: msg.id, error: chrome.runtime.lastError.message });
        return;
      }
      const urls = response?.urls || [];
      handleTrpcMediaUrls('extract', JSON.stringify(urls));
      sendToAgent({ id: msg.id, result: { count: urls.length, urls } });
    });
  } catch (e) {
    sendToAgent({ id: msg.id, error: e.message });
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

init().catch((e) => console.error('[FlowAgent] Startup init failed:', e));

console.log('[FlowAgent] Extension loaded — connecting to agent...');
connectToAgent();
setInterval(keepAlive, 5000);
