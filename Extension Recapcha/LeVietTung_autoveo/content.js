// ISOLATED-world bridge. Injects MAIN-world `injected.js` so
// grecaptcha.enterprise.execute runs in Flow's React context (real userActivation).
// Guard prevents duplicate onMessage listeners across retry injections.
'use strict';

(function installContentBridge() {
  // Smart auto-redirect: labs.google/fx/[locale/]tools/flow/* -> flow.google.com/*
  try {
    const loc = window.location;
    if (loc.hostname === "labs.google") {
      const match = loc.href.match(/^https?:\/\/labs\.google\/fx\/(?:[a-zA-Z-_]+\/)?tools\/flow(\/.*|\?.*)?$/);
      if (match) {
        const rest = match[1] || "/";
        const newUrl = "https://flow.google.com" + (rest.startsWith("/") ? rest : "/" + rest);
        console.log(`[LeVietTung_autoveo] Auto-redirecting ${loc.href} -> ${newUrl}`);
        loc.replace(newUrl);
        return;
      }
      if (loc.pathname.startsWith("/fx/tools/flow") || loc.pathname.match(/^\/fx\/[a-z]{2}\/tools\/flow/)) {
        loc.replace("https://flow.google.com/");
        return;
      }
    }
  } catch (_) {}

  if (!window.__upprojectHijackPatchV3) {
    window.__upprojectHijackPatchV3 = true;
    const ps = document.createElement('script');
    ps.src = chrome.runtime.getURL('injected.js');
    ps.onload = () => ps.remove();
    (document.head || document.documentElement).appendChild(ps);
  }

  if (window.__upprojectContentInstalled) return;
  window.__upprojectContentInstalled = true;

  const s = document.createElement('script');
  s.src = chrome.runtime.getURL('injected.js');
  s.onload = () => s.remove();
  (document.head || document.documentElement).appendChild(s);

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type !== 'GET_CAPTCHA') return undefined;
    const { requestId, pageAction } = msg;

    const handler = (ev) => {
      if (ev.detail?.requestId !== requestId) return;
      window.removeEventListener('UPPROJECT_CAPTCHA_RESULT', handler);
      clearTimeout(timer);
      sendResponse({ token: ev.detail?.token, error: ev.detail?.error });
    };

    const timer = setTimeout(() => {
      window.removeEventListener('UPPROJECT_CAPTCHA_RESULT', handler);
      sendResponse({ error: 'CONTENT_TIMEOUT' });
    }, 22_000);

    window.addEventListener('UPPROJECT_CAPTCHA_RESULT', handler);
    window.dispatchEvent(
      new CustomEvent('UPPROJECT_GET_CAPTCHA', { detail: { requestId, pageAction } }),
    );

    return true;
  });
})();
