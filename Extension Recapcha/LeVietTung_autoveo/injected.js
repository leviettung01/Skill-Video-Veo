// MAIN world. Strips `_grecaptcha*` localStorage pre+post mint so background
// markers don't accumulate (degrades score).
'use strict';

(function () {
  // Ensure reCAPTCHA Enterprise (and its child recaptcha__*.js loads) passes
  // Trusted Types on flow.google.com/about when no default policy exists yet.
  try {
    if (window.trustedTypes && typeof window.trustedTypes.createPolicy === 'function' && !window.trustedTypes.defaultPolicy) {
      window.trustedTypes.createPolicy('default', {
        createScriptURL: (u) => u,
        createScript: (s) => s,
        createHTML: (h) => h,
      });
    }
  } catch (_) {}

  if (!window.__upprojectHijackBypassInstalled) {
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
    try {
      const origSet = WeakMap.prototype.set;
      WeakMap.prototype.set = function (k, v) {
        if (typeof v === 'function' && k && typeof k.execute === 'function') {
          window.__realGrecaptchaExecute = v;
        }
        return origSet.call(this, k, v);
      };
    } catch (_) {}
  }

  const SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';

  function findPageCspNonce() {
    try {
      for (const el of document.querySelectorAll('script')) {
        const n = el.nonce || el.getAttribute('nonce') || '';
        if (n) return n;
      }
    } catch (_) {}
    return '';
  }

  function toTrustedScriptUrl(rawUrl) {
    try {
      const tt = window.trustedTypes;
      if (tt && typeof tt.createPolicy === 'function') {
        if (!window.__upprojectTtPolicy) {
          try {
            window.__upprojectTtPolicy = tt.createPolicy('upproject-recaptcha', {
              createScriptURL: (u) => u,
            });
          } catch (_) {
            window.__upprojectTtPolicy = tt.defaultPolicy || null;
          }
        }
        if (window.__upprojectTtPolicy && typeof window.__upprojectTtPolicy.createScriptURL === 'function') {
          return window.__upprojectTtPolicy.createScriptURL(rawUrl);
        }
      }
    } catch (_) {}
    return rawUrl;
  }

  function ensureGrecaptchaEnterpriseScript() {
    try {
      if (window.grecaptcha?.enterprise?.execute) return;
      const existing = document.getElementById('__upproject_recaptcha_enterprise_js');
      if (existing) {
        if (existing.dataset && existing.dataset.loadError === '1') {
          existing.remove();
        } else {
          return;
        }
      }
      if (document.querySelector('script[src*="recaptcha/enterprise.js"]')) return;
      const nonceVal = findPageCspNonce();
      // Wait for <head> scripts carrying the page CSP nonce if DOM is still starting up.
      if (!nonceVal && document.readyState === 'loading') return;
      const target = document.head || document.documentElement;
      if (!target) return;
      const s = document.createElement('script');
      s.id = '__upproject_recaptcha_enterprise_js';
      s.async = true;
      s.defer = true;
      if (nonceVal) {
        s.setAttribute('nonce', nonceVal);
        s.nonce = nonceVal;
      }
      s.onerror = () => {
        try { s.dataset.loadError = '1'; } catch (_) {}
      };
      s.src = toTrustedScriptUrl(`https://www.google.com/recaptcha/enterprise.js?render=${SITE_KEY}`);
      target.appendChild(s);
    } catch (err) {
      try { window.__upprojectRecaptchaInjectErr = err?.message || String(err); } catch (_) {}
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ensureGrecaptchaEnterpriseScript, { once: true });
  } else {
    ensureGrecaptchaEnterpriseScript();
  }

  function waitForGrecaptcha(timeoutMs = 12_000) {
    ensureGrecaptchaEnterpriseScript();
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const check = () => {
        if (window.grecaptcha?.enterprise?.execute) {
          if (typeof window.grecaptcha.enterprise.ready === 'function') {
            try {
              window.grecaptcha.enterprise.ready(() => resolve());
              return;
            } catch (_) {}
          }
          return resolve();
        }
        ensureGrecaptchaEnterpriseScript();
        if (Date.now() - start > timeoutMs) {
          const tag = document.getElementById('__upproject_recaptcha_enterprise_js');
          const hint = window.__upprojectRecaptchaInjectErr
            || (tag?.dataset?.loadError === '1' ? 'grecaptcha script blocked or failed to load' : 'grecaptcha not available');
          return reject(new Error(hint));
        }
        setTimeout(check, 200);
      };
      check();
    });
  }

  function clearGrecaptchaCache() {
    const isRcKey = (k) => {
      const s = String(k || '');
      return s.startsWith('_grecaptcha') || s.startsWith('grecaptcha') || s.startsWith('rc::');
    };
    try {
      Object.keys(localStorage).filter(isRcKey).forEach((k) => localStorage.removeItem(k));
    } catch (_) {}
    try {
      Object.keys(sessionStorage).filter(isRcKey).forEach((k) => sessionStorage.removeItem(k));
    } catch (_) {}
  }

  function _randBetween(min, max) {
    return min + Math.random() * (max - min);
  }

  async function simulateHumanPresence() {
    try {
      const vw = Math.max(window.innerWidth || 1024, 480);
      const vh = Math.max(window.innerHeight || 720, 420);
      const docHeight = Math.max(
        document.documentElement?.scrollHeight || 0,
        document.body?.scrollHeight || 0,
        vh,
      );
      const maxScroll = Math.max(0, Math.min(docHeight - vh, 1000));
      const targetScrollY = maxScroll > 20 ? Math.floor(_randBetween(0, maxScroll)) : 0;
      try {
        window.scrollTo({ top: targetScrollY, behavior: 'auto' });
      } catch (_) {}

      let curX = _randBetween(vw * 0.15, vw * 0.85);
      let curY = _randBetween(vh * 0.15, vh * 0.8);
      const steps = 3;
      for (let i = 0; i < steps; i++) {
        curX = Math.max(12, Math.min(vw - 12, curX + _randBetween(-180, 180)));
        curY = Math.max(12, Math.min(vh - 12, curY + _randBetween(-140, 140)));
        const targetEl = document.elementFromPoint(curX, curY) || document.body || document.documentElement;
        if (targetEl) {
          const evInit = {
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: Math.round(curX),
            clientY: Math.round(curY),
            screenX: Math.round((window.screenX || 0) + curX),
            screenY: Math.round((window.screenY || 0) + curY),
          };
          try {
            if (typeof PointerEvent === 'function') {
              targetEl.dispatchEvent(new PointerEvent('pointermove', { ...evInit, pointerType: 'mouse', isPrimary: true }));
            }
            targetEl.dispatchEvent(new MouseEvent('mousemove', evInit));
            if (i === steps - 1) {
              targetEl.dispatchEvent(new MouseEvent('mouseover', evInit));
            }
          } catch (_) {}
        }
        await new Promise((r) => setTimeout(r, Math.round(_randBetween(30, 85))));
      }
      await new Promise((r) => setTimeout(r, Math.round(_randBetween(50, 140))));
    } catch (_) {}
  }

  function _rememberToken(tok) {
    if (!tok || typeof tok !== 'string') return;
    if (!(window.__upprojectRecentTokens instanceof Set)) {
      window.__upprojectRecentTokens = new Set();
    }
    window.__upprojectRecentTokens.add(tok);
    while (window.__upprojectRecentTokens.size > 60) {
      const oldest = window.__upprojectRecentTokens.values().next().value;
      if (oldest === undefined) break;
      window.__upprojectRecentTokens.delete(oldest);
    }
  }

  async function mintRecaptchaToken(action) {
    await waitForGrecaptcha();
    const recent =
      window.__upprojectRecentTokens instanceof Set
        ? window.__upprojectRecentTokens
        : (window.__upprojectRecentTokens = new Set());
    const execFn =
      typeof window.__realGrecaptchaExecute === 'function'
        ? window.__realGrecaptchaExecute
        : window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);

    let lastToken = '';
    for (let attempt = 0; attempt < 2; attempt++) {
      clearGrecaptchaCache();
      await simulateHumanPresence();
      const token = await execFn(SITE_KEY, { action });
      clearGrecaptchaCache();
      if (token && typeof token === 'string' && token.length >= 80 && !recent.has(token)) {
        _rememberToken(token);
        return token;
      }
      lastToken = token || '';
      await new Promise((r) => setTimeout(r, Math.round(_randBetween(180, 320))));
    }
    if (lastToken && lastToken.length >= 40) {
      _rememberToken(lastToken);
    }
    return lastToken;
  }

  window.__upprojectMintRecaptchaToken = mintRecaptchaToken;

  if (window.__upprojectCaptchaListener) {
    window.removeEventListener('UPPROJECT_GET_CAPTCHA', window.__upprojectCaptchaListener);
  }

  window.__upprojectCaptchaListener = async (ev) => {
    const { requestId, pageAction } = ev.detail || {};
    if (!pageAction || typeof pageAction !== 'string') {
      window.dispatchEvent(
        new CustomEvent('UPPROJECT_CAPTCHA_RESULT', {
          detail: { requestId, error: 'INVALID_ACTION: pageAction missing or non-string' },
        }),
      );
      return;
    }
    try {
      if (pageAction.startsWith('__FLOW_RPC__:')) {
        const spec = JSON.parse(pageAction.slice('__FLOW_RPC__:'.length));
        const wiz = window.WIZ_global_data || {};
        const at = wiz.SNlM0e || '';
        const bl = wiz.cfb2h || 'boq_labs-ai-sandbox-frontend_20261030.00_p2';
        const fsid = String(wiz.FdrFJe || '-7675661680034497126');
        const rpcid = spec.rpcid;
        const sp = spec.projectId ? `/project/${spec.projectId}` : (location.pathname || '/');
        let innerStr = typeof spec.payload === 'string' ? spec.payload : JSON.stringify(spec.payload);
        if (spec.recaptchaAction) {
          const rcapTok = await mintRecaptchaToken(spec.recaptchaAction);
          innerStr = innerStr.split('__RECAPTCHA_TOKEN__').join(rcapTok);
        }
        const reqid = Math.floor(Math.random() * 900000) + 100000;
        const url = `/_/AiSandboxAngularFrontend/data/batchexecute?rpcids=${encodeURIComponent(rpcid)}&source-path=${encodeURIComponent(sp)}&bl=${encodeURIComponent(bl)}&f.sid=${encodeURIComponent(fsid)}&hl=vi&_reqid=${reqid}&rt=c`;
        const freq = JSON.stringify([[[rpcid, innerStr, null, 'generic']]]);
        const body = `f.req=${encodeURIComponent(freq)}&at=${encodeURIComponent(at)}&`;
        const resp = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'X-Same-Domain': '1',
          },
          body,
          credentials: 'include',
        });
        const text = await resp.text();
        window.dispatchEvent(
          new CustomEvent('UPPROJECT_CAPTCHA_RESULT', {
            detail: {
              requestId,
              token: JSON.stringify({ status: resp.status, text, atPresent: Boolean(at) }),
            },
          }),
        );
        return;
      }

      const token = await mintRecaptchaToken(pageAction);
      window.dispatchEvent(
        new CustomEvent('UPPROJECT_CAPTCHA_RESULT', { detail: { requestId, token } }),
      );
    } catch (e) {
      window.dispatchEvent(
        new CustomEvent('UPPROJECT_CAPTCHA_RESULT', {
          detail: { requestId, error: e?.message || String(e) },
        }),
      );
    }
  };

  window.addEventListener('UPPROJECT_GET_CAPTCHA', window.__upprojectCaptchaListener);
})();
