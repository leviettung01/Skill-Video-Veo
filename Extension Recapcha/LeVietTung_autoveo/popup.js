'use strict';

const DEFAULT_BRIDGE_BASE = 'http://127.0.0.1:4000';
const DEFAULT_BRIDGE_SECRET = 'ff065320a43b73b8959756fac4830553c1ee664bb7762467c46eb1de80d7e39d';

const banner = document.getElementById('status-banner');
const dot = document.getElementById('status-dot');
const labelEl = document.getElementById('status-label');
const subEl = document.getElementById('status-sub');
const popUrl = document.getElementById('pop-url');
const popSecret = document.getElementById('pop-secret');
const btnSaveTest = document.getElementById('btn-save-test');
const popTestRes = document.getElementById('pop-test-res');
const btnOptions = document.getElementById('btn-options');
const btnSidePanel = document.getElementById('btn-sidepanel');
const btnFlow = document.getElementById('btn-flow');

const STATE_LABELS = {
  noconfig: 'Chưa cấu hình',
  connected: 'Kết nối ổn định (:4000)',
  stale: 'Kết nối chậm',
  offline: 'Mất kết nối',
};

function formatAgoShort(ts) {
  if (!ts) return null;
  const secs = Math.round((Date.now() - ts) / 1000);
  if (secs < 5) return 'vừa xong';
  if (secs < 60) return `${secs}s trước`;
  return `${Math.round(secs / 60)}m trước`;
}

function applyState(state, pollAgo, mintAgo) {
  banner.dataset.state = state;
  dot.dataset.state = state;
  labelEl.textContent = STATE_LABELS[state] ?? state;
  if (state === 'noconfig') {
    subEl.textContent = 'Nhập Bridge URL + Secret bên dưới';
  } else if (mintAgo) {
    subEl.textContent = `Poll: ${pollAgo || 'vừa xong'} • Mint: ${mintAgo}`;
  } else {
    subEl.textContent = `Poll cuối: ${pollAgo || 'vừa xong'}`;
  }
}

function resolveStatus() {
  chrome.storage.local.get(
    ['bridgeBase', 'bridgeSecret', 'lastPollOkAt', 'lastMintOkAt'],
    ({ bridgeBase, bridgeSecret, lastPollOkAt, lastMintOkAt }) => {
      if (!popUrl.value) popUrl.value = bridgeBase || DEFAULT_BRIDGE_BASE;
      if (!popSecret.value) popSecret.value = bridgeSecret || DEFAULT_BRIDGE_SECRET;

      const now = Date.now();
      const pollAge = lastPollOkAt ? now - lastPollOkAt : Infinity;
      const pollAgo = formatAgoShort(lastPollOkAt);
      const mintAgo = formatAgoShort(lastMintOkAt);

      let state;
      if (pollAge < 35_000) state = 'connected';
      else if (pollAge < 120_000) state = 'stale';
      else state = 'offline';

      applyState(state, pollAgo, mintAgo);
    },
  );
}

chrome.storage.local.get(['bridgeBase', 'bridgeSecret'], ({ bridgeBase, bridgeSecret }) => {
  popUrl.value = bridgeBase || DEFAULT_BRIDGE_BASE;
  popSecret.value = bridgeSecret || DEFAULT_BRIDGE_SECRET;
});

btnSaveTest.addEventListener('click', async () => {
  const bridgeBase = popUrl.value.trim().replace(/\/+$/, '') || DEFAULT_BRIDGE_BASE;
  const bridgeSecret = popSecret.value.trim() || DEFAULT_BRIDGE_SECRET;
  chrome.storage.local.set({ bridgeBase, bridgeSecret }, () => {
    chrome.runtime.sendMessage({ type: 'RECONNECT' }, () => {});
  });
  try {
    const resp = await fetch(`${bridgeBase}/api/internal/captcha/stats`, {
      method: 'GET',
      headers: { 'x-local-auth': bridgeSecret },
    });
    if (resp.ok) {
      const data = await resp.json().catch(() => ({}));
      popTestRes.className = 'test-box ok';
      popTestRes.textContent = `✓ OK — pending: ${data.pendingCount ?? 0}, queued: ${data.queuedCount ?? 0}, pollers: ${data.pollerWaitingCount ?? 1}`;
      applyState('connected', 'vừa xong', null);
    } else {
      popTestRes.className = 'test-box fail';
      popTestRes.textContent = `✗ HTTP ${resp.status}`;
    }
  } catch (e) {
    popTestRes.className = 'test-box fail';
    popTestRes.textContent = `✗ ${e?.message || 'Lỗi kết nối cổng 4000'}`;
  }
});

resolveStatus();
setInterval(resolveStatus, 3_000);

btnOptions.addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
  window.close();
});

btnSidePanel.addEventListener('click', async () => {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && chrome.sidePanel?.open) {
      await chrome.sidePanel.open({ windowId: tab.windowId });
      window.close();
      return;
    }
  } catch (_) {}
  chrome.runtime.openOptionsPage();
  window.close();
});

btnFlow.addEventListener('click', () => {
  chrome.tabs.create({ url: 'https://flow.google.com/' });
  window.close();
});
