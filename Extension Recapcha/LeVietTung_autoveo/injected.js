// MAIN world. Strips `_grecaptcha*` localStorage pre+post mint so background
// markers don't accumulate (degrades score).
'use strict';

(function () {
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

  function waitForGrecaptcha(timeoutMs = 12_000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const check = () => {
        if (window.grecaptcha?.enterprise?.execute) return resolve();
        if (Date.now() - start > timeoutMs) {
          return reject(new Error('grecaptcha not available'));
        }
        setTimeout(check, 200);
      };
      check();
    });
  }

  function clearGrecaptchaCache() {
    try {
      Object.keys(localStorage)
        .filter((k) => k.startsWith('_grecaptcha'))
        .forEach((k) => localStorage.removeItem(k));
    } catch (_) {}
  }

  async function mintRecaptchaToken(action) {
    await waitForGrecaptcha();
    clearGrecaptchaCache();
    const execFn =
      typeof window.__realGrecaptchaExecute === 'function'
        ? window.__realGrecaptchaExecute
        : window.grecaptcha.enterprise.execute.bind(window.grecaptcha.enterprise);
    const token = await execFn(SITE_KEY, { action });
    clearGrecaptchaCache();
    return token;
  }

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
              token: JSON.stringify({ ok: resp.ok, status: resp.status, text, email: wiz.oPEP7c || '' }),
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
  window.__upprojectInstalled = true;
})();
