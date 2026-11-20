// ISOLATED-world bridge. Injects MAIN-world `injected.js` so
// grecaptcha.enterprise.execute runs in Flow's page context.
// Guard prevents duplicate onMessage listeners across retry injections.
'use strict';

(function installContentBridge() {
  // Smart auto-redirect: labs.google/fx/[locale/]tools/flow/* -> flow.google.com/about
  try {
    const loc = window.location;
    if (loc.hostname === 'labs.google') {
      const match = loc.href.match(/^https?:\/\/labs\.google\/fx\/(?:[a-zA-Z-_]+\/)?tools\/flow(\/.*|\?.*)?$/);
      if (match) {
        const rest = match[1] || '/about';
        const newUrl = 'https://flow.google.com' + (rest === '/' ? '/about' : (rest.startsWith('/') ? rest : '/' + rest));
        console.log(`[LeVietTung_autoveo] Auto-redirecting ${loc.href} -> ${newUrl}`);
        loc.replace(newUrl);
        return;
      }
      if (loc.pathname.startsWith('/fx/tools/flow') || /^\/fx\/[a-z]{2}\/tools\/flow/.test(loc.pathname)) {
        loc.replace('https://flow.google.com/about');
        return;
      }
    }
  } catch (_) {}

  const injectMainScript = () => {
    try {
      const ps = document.createElement('script');
      ps.src = chrome.runtime.getURL('injected.js');
      for (const el of document.querySelectorAll('script')) {
        const n = el.nonce || el.getAttribute('nonce') || '';
        if (n) {
          ps.setAttribute('nonce', n);
          ps.nonce = n;
          break;
        }
      }
      ps.onload = () => ps.remove();
      (document.head || document.documentElement).appendChild(ps);
    } catch (_) {}
  };

  if (window.__upprojectContentInstalled) {
    injectMainScript();
    return;
  }
  window.__upprojectContentInstalled = true;
  injectMainScript();

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
