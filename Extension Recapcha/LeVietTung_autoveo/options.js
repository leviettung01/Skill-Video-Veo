'use strict';

const DEFAULT_BRIDGE_BASE = 'http://127.0.0.1:4000';
const DEFAULT_BRIDGE_SECRET = 'ff065320a43b73b8959756fac4830553c1ee664bb7762467c46eb1de80d7e39d';

const bridgeUrlInput = document.getElementById('bridge-url');
const bridgeSecretInput = document.getElementById('bridge-secret');
const toggleSecretBtn = document.getElementById('toggle-secret');
const eyeIcon = document.getElementById('eye-icon');
const saveBtn = document.getElementById('save-btn');
const testBtn = document.getElementById('test-btn');
const syncBtn = document.getElementById('sync-btn');
const testResult = document.getElementById('test-result');
const lastPollEl = document.getElementById('last-poll');
const lastMintEl = document.getElementById('last-mint');
const lastMintDurEl = document.getElementById('last-mint-duration');
const openFlowBtn = document.getElementById('open-flow-btn');

chrome.storage.local.get(
  ['bridgeBase', 'bridgeSecret'],
  ({ bridgeBase, bridgeSecret }) => {
    bridgeUrlInput.value = bridgeBase || DEFAULT_BRIDGE_BASE;
    bridgeSecretInput.value = bridgeSecret || DEFAULT_BRIDGE_SECRET;
    updateSaveState();
    runConnectionTest();
  },
);

function updateSaveState() {
  const urlOk = bridgeUrlInput.value.trim().length > 0;
  const secretOk = bridgeSecretInput.value.trim().length > 0;
  saveBtn.disabled = !(urlOk && secretOk);
}

bridgeUrlInput.addEventListener('input', updateSaveState);
bridgeSecretInput.addEventListener('input', updateSaveState);

let secretVisible = false;
toggleSecretBtn.addEventListener('click', () => {
  secretVisible = !secretVisible;
  bridgeSecretInput.type = secretVisible ? 'text' : 'password';
  eyeIcon.textContent = secretVisible ? '🙈' : '👁';
  toggleSecretBtn.setAttribute('aria-label', secretVisible ? 'Ẩn secret' : 'Hiện secret');
});

document.getElementById('config-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const bridgeBase = bridgeUrlInput.value.trim().replace(/\/+$/, '');
  const bridgeSecret = bridgeSecretInput.value.trim();
  chrome.storage.local.set({ bridgeBase, bridgeSecret }, () => {
    chrome.runtime.sendMessage({ type: 'RECONNECT' }, () => {});
    const original = saveBtn.textContent;
    saveBtn.textContent = '✓ Đã lưu';
    saveBtn.disabled = true;
    setTimeout(() => {
      saveBtn.textContent = original;
      updateSaveState();
    }, 1800);
    runConnectionTest();
  });
});

async function runConnectionTest() {
  const bridgeBase = bridgeUrlInput.value.trim().replace(/\/+$/, '');
  const bridgeSecret = bridgeSecretInput.value.trim();
  if (!bridgeBase || !bridgeSecret) {
    showTestResult(false, 'Vui lòng nhập Bridge URL và Bridge Secret trước.');
    return;
  }
  const originalText = testBtn.textContent;
  testBtn.disabled = true;
  testBtn.textContent = 'Đang kiểm tra...';
  hideTestResult();

  try {
    const resp = await fetch(`${bridgeBase}/api/internal/captcha/stats`, {
      method: 'GET',
      headers: { 'x-local-auth': bridgeSecret },
    });
    if (resp.ok) {
      const data = await resp.json().catch(() => ({}));
      const pending = data.pendingCount ?? 0;
      const queued = data.queuedCount ?? 0;
      const pollers = data.pollerWaitingCount ?? 1;
      showTestResult(true, `OK — pending: ${pending}, queued: ${queued}, pollers: ${pollers}`);
    } else {
      showTestResult(false, `HTTP ${resp.status} ${resp.statusText}`);
    }
  } catch (e) {
    showTestResult(false, e?.message || 'Không thể kết nối tới backend (:4000)');
  } finally {
    testBtn.disabled = false;
    testBtn.textContent = originalText;
  }
}

testBtn.addEventListener('click', runConnectionTest);

if (syncBtn) {
  syncBtn.addEventListener('click', () => {
    const bridgeBase = bridgeUrlInput.value.trim().replace(/\/+$/, '') || DEFAULT_BRIDGE_BASE;
    chrome.runtime.sendMessage({ type: 'AUTO_SYNC_CONFIG', bridgeBase }, (res) => {
      if (res && res.ok) {
        bridgeUrlInput.value = res.bridgeBase || DEFAULT_BRIDGE_BASE;
        bridgeSecretInput.value = res.bridgeSecret || DEFAULT_BRIDGE_SECRET;
        updateSaveState();
        runConnectionTest();
      } else {
        showTestResult(false, 'Không đọc được cấu hình tự động từ cổng 4000.');
      }
    });
  });
}

function showTestResult(ok, msg) {
  testResult.hidden = false;
  testResult.textContent = ok ? `✓ ${msg}` : `✗ ${msg}`;
  testResult.className = `test-result ${ok ? 'test-ok' : 'test-fail'}`;
}

function hideTestResult() {
  testResult.hidden = true;
  testResult.textContent = '';
  testResult.className = 'test-result';
}

function formatAgo(ts) {
  if (!ts) return '—';
  const secs = Math.round((Date.now() - ts) / 1000);
  if (secs < 5) return 'Vừa xong';
  if (secs < 60) return `${secs}s trước`;
  const mins = Math.floor(secs / 60);
  const rem = secs % 60;
  return rem > 0 ? `${mins}m ${rem}s trước` : `${mins}m trước`;
}

function refreshStatus() {
  chrome.storage.local.get(
    ['lastPollOkAt', 'lastMintOkAt', 'lastMintDurationMs'],
    ({ lastPollOkAt, lastMintOkAt, lastMintDurationMs }) => {
      lastPollEl.textContent = formatAgo(lastPollOkAt);
      lastMintEl.textContent = formatAgo(lastMintOkAt);
      lastMintDurEl.textContent = lastMintDurationMs != null ? `${lastMintDurationMs}ms` : '—';
    },
  );
}

refreshStatus();
const statusTimer = setInterval(refreshStatus, 3_000);
window.addEventListener('unload', () => clearInterval(statusTimer));

openFlowBtn.addEventListener('click', () => {
  chrome.tabs.create({ url: 'https://flow.google.com/' });
});

