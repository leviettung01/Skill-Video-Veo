/**
 * LeVietTung_autoveo — Side Panel Controller (v2.1.0)
 * Tích hợp đầy đủ Cấu hình kết nối (Bridge URL + Bridge Secret + Lưu + Test kết nối)
 * & Trạng thái Poll/Mint trực tiếp trên Side Panel.
 */
'use strict';

const DEFAULT_BRIDGE_BASE = 'http://127.0.0.1:4000';
const DEFAULT_BRIDGE_SECRET = 'ff065320a43b73b8959756fac4830553c1ee664bb7762467c46eb1de80d7e39d';

const spUrlInput = document.getElementById('sp-bridge-url');
const spSecretInput = document.getElementById('sp-bridge-secret');
const spToggleSecretBtn = document.getElementById('sp-toggle-secret');
const spSaveBtn = document.getElementById('sp-save-btn');
const spTestBtn = document.getElementById('sp-test-btn');
const spSyncBtn = document.getElementById('sp-sync-btn');
const spTestResult = document.getElementById('sp-test-result');
const spLastPoll = document.getElementById('sp-last-poll');
const spLastMint = document.getElementById('sp-last-mint');
const spLastMintDur = document.getElementById('sp-last-mint-dur');

let secretVisible = false;
spToggleSecretBtn.addEventListener('click', () => {
  secretVisible = !secretVisible;
  spSecretInput.type = secretVisible ? 'text' : 'password';
  spToggleSecretBtn.textContent = secretVisible ? '🙈' : '👁';
});

chrome.storage.local.get(['bridgeBase', 'bridgeSecret'], ({ bridgeBase, bridgeSecret }) => {
  spUrlInput.value = bridgeBase || DEFAULT_BRIDGE_BASE;
  spSecretInput.value = bridgeSecret || DEFAULT_BRIDGE_SECRET;
  testBridgeConnection(true);
});

spSaveBtn.addEventListener('click', () => {
  const bridgeBase = spUrlInput.value.trim().replace(/\/+$/, '') || DEFAULT_BRIDGE_BASE;
  const bridgeSecret = spSecretInput.value.trim() || DEFAULT_BRIDGE_SECRET;
  chrome.storage.local.set({ bridgeBase, bridgeSecret }, () => {
    chrome.runtime.sendMessage({ type: 'RECONNECT' }, () => {});
    spSaveBtn.textContent = '✓ Đã lưu';
    setTimeout(() => { spSaveBtn.textContent = 'Lưu cấu hình'; }, 1500);
    testBridgeConnection(false);
  });
});

spTestBtn.addEventListener('click', () => testBridgeConnection(false));

spSyncBtn.addEventListener('click', () => {
  const bridgeBase = spUrlInput.value.trim().replace(/\/+$/, '') || DEFAULT_BRIDGE_BASE;
  chrome.runtime.sendMessage({ type: 'AUTO_SYNC_CONFIG', bridgeBase }, (res) => {
    if (res && res.ok) {
      spUrlInput.value = res.bridgeBase || DEFAULT_BRIDGE_BASE;
      spSecretInput.value = res.bridgeSecret || DEFAULT_BRIDGE_SECRET;
      testBridgeConnection(false);
    } else {
      showSpTestBanner(false, 'Không tự động đọc được từ cổng 4000');
    }
  });
});

const spFlowEmailBadge = document.getElementById('sp-flow-email-badge');

async function testBridgeConnection(silentIfFail = false) {
  const bridgeBase = spUrlInput.value.trim().replace(/\/+$/, '');
  const bridgeSecret = spSecretInput.value.trim();
  if (!bridgeBase || !bridgeSecret) {
    if (!silentIfFail) showSpTestBanner(false, 'Hãy nhập Bridge URL & Secret');
    return;
  }
  spTestBtn.textContent = 'Đang test...';
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
      showSpTestBanner(true, `OK — pending: ${pending}, queued: ${queued}, pollers: ${pollers}`);
    } else if (!silentIfFail) {
      showSpTestBanner(false, `HTTP ${resp.status}`);
    }
  } catch (e) {
    if (!silentIfFail) showSpTestBanner(false, e?.message || 'Chưa kết nối cổng 4000');
  } finally {
    spTestBtn.textContent = 'Test kết nối';
  }
}

function showSpTestBanner(ok, msg) {
  spTestResult.className = `test-banner ${ok ? 'ok' : 'fail'}`;
  spTestResult.textContent = ok ? `✓ ${msg}` : `✗ ${msg}`;
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

function formatTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
  } catch {
    return '—';
  }
}

function updateStatus(data) {
  if (!data) return;

  const dot = document.getElementById('conn-dot');
  const connected = Boolean(data.agentConnected);
  dot.className = connected ? 'on' : '';

  const stateBadge = document.getElementById('state-badge');
  const st = connected ? 'connected' : (data.state || 'connecting');
  stateBadge.textContent = connected ? 'CONNECTED (:4000)' : st.toUpperCase();
  stateBadge.className = connected ? 'connected' : 'connecting';

  const tokenEl = document.getElementById('token-status');
  if (spFlowEmailBadge) {
    spFlowEmailBadge.textContent = data.flowEmail ? `📧 ${data.flowEmail}` : '';
  }
  if (data.flowKeyPresent) {
    tokenEl.textContent = data.flowEmail ? `✓ ${data.flowEmail}` : `✓ Cookie Flow (${data.cookieCount || 0})`;
    tokenEl.className = 'ok';
  } else if (data.hasFlowTab) {
    tokenEl.textContent = 'Chưa đăng nhập Flow';
    tokenEl.className = 'warn';
  } else {
    tokenEl.textContent = 'Chưa mở tab Flow';
    tokenEl.className = 'bad';
  }

  spLastPoll.textContent = formatAgo(data.lastPollOkAt);
  spLastMint.textContent = formatAgo(data.lastMintOkAt);
  spLastMintDur.textContent = data.lastMintDurationMs != null ? `${data.lastMintDurationMs}ms` : '—';

  const m = data.metrics || {};
  document.getElementById('m-total').textContent = m.requestCount || 0;
  document.getElementById('m-success').textContent = m.successCount || 0;
  document.getElementById('m-failed').textContent = m.failedCount || 0;
}

function updateRequestLog(entries) {
  const tbody = document.getElementById('log-body');
  const countEl = document.getElementById('log-count');

  if (!entries || entries.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="log-empty">Chưa có request nào</td></tr>';
    countEl.textContent = '0';
    return;
  }

  countEl.textContent = entries.length;
  tbody.innerHTML = entries.map((entry) => {
    const shortId = entry.id ? String(entry.id).slice(0, 8) : '—';
    const type = entry.type || 'CAPTCHA';
    const time = formatTime(entry.time);
    const status = entry.status || 'pending';
    const detail = entry.error || entry.responseSummary || entry.payloadSummary || '—';

    let badgeHtml = '<span class="badge badge-proc">⏳ xử lý</span>';
    if (status === 'COMPLETED' || status === 'success') {
      badgeHtml = '<span class="badge badge-ok">✓ xong</span>';
    } else if (status === 'FAILED' || status === 'failed') {
      badgeHtml = '<span class="badge badge-fail">✕ lỗi</span>';
    }

    return `<tr>
      <td class="td-id">${shortId}</td>
      <td class="td-type">${type}</td>
      <td class="td-time">${time}</td>
      <td>${badgeHtml}</td>
      <td title="${String(detail).replace(/"/g, '&quot;')}">${String(detail).slice(0, 26)}</td>
    </tr>`;
  }).join('');
}

function fetchStatus() {
  chrome.runtime.sendMessage({ type: 'STATUS' }, (data) => {
    if (chrome.runtime.lastError) return;
    updateStatus(data);
  });
}

function fetchLog() {
  chrome.runtime.sendMessage({ type: 'REQUEST_LOG' }, (data) => {
    if (chrome.runtime.lastError) return;
    if (data && data.log) updateRequestLog(data.log);
  });
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'STATUS_PUSH') fetchStatus();
  if (msg.type === 'REQUEST_LOG_UPDATE' && msg.log) updateRequestLog(msg.log);
});

document.getElementById('main-toggle').addEventListener('change', (e) => {
  const msgType = e.target.checked ? 'RECONNECT' : 'DISCONNECT';
  document.getElementById('toggle-label').textContent = e.target.checked ? 'ON' : 'OFF';
  chrome.runtime.sendMessage({ type: msgType }, () => {
    setTimeout(fetchStatus, 300);
  });
});

document.getElementById('btn-flow').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'OPEN_FLOW_TAB' });
});

document.getElementById('btn-token').addEventListener('click', () => {
  const btn = document.getElementById('btn-token');
  btn.textContent = 'Đang đồng bộ...';
  chrome.runtime.sendMessage({ type: 'REFRESH_TOKEN' }, () => {
    setTimeout(() => {
      btn.textContent = '🔄 Đồng Bộ Phiên Flow';
      fetchStatus();
      testBridgeConnection(true);
    }, 500);
  });
});

document.addEventListener('DOMContentLoaded', () => {
  chrome.runtime.sendMessage({ type: 'RECONNECT' }, () => {});
  fetchStatus();
  fetchLog();
  setInterval(fetchStatus, 2000);
  setInterval(fetchLog, 4000);
});
