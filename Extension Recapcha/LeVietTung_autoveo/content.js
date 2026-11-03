/**
 * Content script — bridge between background.js and injected.js
 * Injects injected.js into MAIN world to access window.grecaptcha
 */
(function () {
  // Smart auto-redirect: labs.google/fx/[locale/]tools/flow/* -> flow.google.com/*
  try {
    const loc = window.location;
    if (loc.hostname === "labs.google") {
      const match = loc.href.match(/^https?:\/\/labs\.google\/fx\/(?:[a-zA-Z-_]+\/)?tools\/flow(\/.*|\?.*)?$/);
      if (match) {
        const rest = match[1] || "/";
        const newUrl = "https://flow.google.com" + (rest.startsWith("/") ? rest : "/" + rest);
        console.log(`[FlowKit] Auto-redirecting ${loc.href} -> ${newUrl}`);
        loc.replace(newUrl);
        return;
      }
      if (loc.pathname.startsWith("/fx/tools/flow") || loc.pathname.match(/^\/fx\/[a-z]{2}\/tools\/flow/)) {
        loc.replace("https://flow.google.com/");
        return;
      }
    }
  } catch (_) {}

  const s = document.createElement('script');
  s.src = chrome.runtime.getURL('injected.js');
  s.onload = () => s.remove();
  (document.head || document.documentElement).appendChild(s);

  // Force trigger token scan after document matches
  window.addEventListener('load', () => {
    window.dispatchEvent(new CustomEvent('SCAN_TOKEN'));
  });
})();


chrome.runtime.onMessage.addListener((msg, _, reply) => {
  if (msg.type === 'EXTRACT_PAGE_MEDIA') {
    const handler = (e) => {
      window.removeEventListener('EXTRACT_PAGE_MEDIA_RESULT', handler);
      reply(e.detail || { urls: [] });
    };
    window.addEventListener('EXTRACT_PAGE_MEDIA_RESULT', handler, { once: true });
    window.dispatchEvent(new CustomEvent('EXTRACT_PAGE_MEDIA'));
    return true;
  }

  if (msg.type !== 'GET_CAPTCHA') return;

  const { requestId, pageAction } = msg;
  let settled = false;
  const replyOnce = (payload) => {
    if (settled) return;
    settled = true;
    reply(payload);
  };

  const handler = (e) => {
    if (e.detail?.requestId === requestId) {
      window.removeEventListener('CAPTCHA_RESULT', handler);
      clearTimeout(timer);
      replyOnce({ token: e.detail.token, error: e.detail.error });
    }
  };

  const timer = setTimeout(() => {
    window.removeEventListener('CAPTCHA_RESULT', handler);
    replyOnce({ error: 'CONTENT_TIMEOUT' });
  }, 25000);

  window.addEventListener('CAPTCHA_RESULT', handler);

  try {
    window.dispatchEvent(new CustomEvent('GET_CAPTCHA', {
      detail: { requestId, pageAction },
    }));
  } catch (error) {
    clearTimeout(timer);
    window.removeEventListener('CAPTCHA_RESULT', handler);
    replyOnce({ error: error?.message || 'CAPTCHA_DISPATCH_FAILED' });
  }

  return true; // keep channel open for async reply
});

// ─── TRPC Media URL Monitor ─────────────────────────────────
// Forward intercepted TRPC responses with media URLs to background.js
window.addEventListener('TRPC_MEDIA_URLS', (e) => {
  const { url, body } = e.detail || {};
  if (!body) return;
  try {
    chrome.runtime.sendMessage({
      type: 'TRPC_MEDIA_URLS',
      trpcUrl: url,
      body,
    }).catch(() => {});
  } catch (_) {
    // The tab can briefly retain an old content-script context while the
    // extension is reloaded. Ignore that transient state until the page is
    // reloaded and receives a fresh content script.
  }
});

// ─── Token Monitor ──────────────────────────────────────────
// Forward intercepted Bearer tokens from main world to background.js
window.addEventListener('TOKEN_CAPTURED', (e) => {
  const token = e.detail?.token;
  if (!token) return;
  try {
    chrome.runtime.sendMessage({
      type: 'TOKEN_CAPTURED',
      token,
    }).catch(() => {});
  } catch (_) {
    // See the heartbeat guard below.
  }
});

// ─── Heartbeat Monitor ──────────────────────────────────────
// Keep background service worker awake and connected while Google Flow tab is open
setInterval(() => {
  try {
    chrome.runtime.sendMessage({ type: 'HEARTBEAT' }).catch(() => {});
  } catch (_) {
    // chrome.runtime can throw synchronously when this content script belongs
    // to an extension context that was just reloaded.
  }
}, 4000);
try {
  chrome.runtime.sendMessage({ type: 'HEARTBEAT' }).catch(() => {});
} catch (_) {
  // The next page reload installs a fresh content script.
}
