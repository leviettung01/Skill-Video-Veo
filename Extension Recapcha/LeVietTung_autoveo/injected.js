/**
 * Injected into MAIN world on labs.google — has access to window.grecaptcha
 * Also intercepts TRPC fetch responses to capture fresh signed media URLs.
 */
const SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';
const _seenMediaUrls = new Set();
const _mediaUrlPattern = /https:\/\/(?:storage\.googleapis\.com|[\w\-.]+\.googleusercontent\.com|aisandbox-pa\.googleapis\.com|flow-content\.google)[^\s"'<>]*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[^\s"'<>]*/gi;

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

function emitMediaUrls(source, text) {
  if (!text) return;
  const matches = String(text || '').match(_mediaUrlPattern) || [];
  const fresh = [];
  for (const raw of matches) {
    const url = raw.replace(/\\u0026/g, '&').replace(/\\/g, '');
    if (_seenMediaUrls.has(url)) continue;
    _seenMediaUrls.add(url);
    fresh.push(url);
  }
  if (fresh.length) {
    window.dispatchEvent(new CustomEvent('TRPC_MEDIA_URLS', {
      detail: { url: source, body: JSON.stringify(fresh) },
    }));
  }
}

function checkAndEmitToken(headers) {
  if (!headers) return;
  let auth = null;
  try {
    if (typeof headers.get === 'function') {
      auth = headers.get('authorization') || headers.get('Authorization');
    } else if (typeof headers === 'object') {
      auth = headers.authorization || headers.Authorization || headers['authorization'] || headers['Authorization'];
    }
  } catch {}
  if (auth && typeof auth === 'string' && auth.includes('ya29.')) {
    const match = auth.match(/ya29\.[a-zA-Z0-9_\-]+/);
    if (match) {
      window.dispatchEvent(new CustomEvent('TOKEN_CAPTURED', { detail: { token: match[0] } }));
    }
  }
}

function scanStorageForToken() {
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      const val = localStorage.getItem(key);
      if (val && val.includes('ya29.')) {
        const match = val.match(/ya29\.[a-zA-Z0-9_\-]+/);
        if (match) {
          window.dispatchEvent(new CustomEvent('TOKEN_CAPTURED', { detail: { token: match[0] } }));
          return;
        }
      }
    }
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      const val = sessionStorage.getItem(key);
      if (val && val.includes('ya29.')) {
        const match = val.match(/ya29\.[a-zA-Z0-9_\-]+/);
        if (match) {
          window.dispatchEvent(new CustomEvent('TOKEN_CAPTURED', { detail: { token: match[0] } }));
          return;
        }
      }
    }
  } catch {}
}

scanStorageForToken();
setInterval(scanStorageForToken, 3000);
window.addEventListener('SCAN_TOKEN', scanStorageForToken);

// ─── TRPC Response Monitor ─────────────────────────────────
// Monkey-patch fetch to intercept TRPC responses containing media URLs and bearer tokens.

const _originalFetch = window.fetch;
window.fetch = async function (...args) {
  try {
    const init = args[1];
    if (init && init.headers) {
      checkAndEmitToken(init.headers);
    }
  } catch {}
  const response = await _originalFetch.apply(this, args);
  try {
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
    // Intercept API calls on labs.google / flow.google.com / googleapis that return project/flow data
    if ((url.includes('/fx/api/') || url.includes('/api/') || url.includes('googleapis.com')) && response.ok) {
      const clone = response.clone();
      clone.text().then(text => {
        emitMediaUrls(url, text);
      }).catch(() => {});
    }
  } catch {}
  return response;
};

// Flow revisions have used both fetch and XHR for project data. Monitor both,
// and also scan resource/video URLs already present in the rendered gallery so
// a completed result can be recovered without downloading encodedVideo first.
const _xhrOpen = XMLHttpRequest.prototype.open;
const _xhrSend = XMLHttpRequest.prototype.send;
const _xhrSetHeader = XMLHttpRequest.prototype.setRequestHeader;

XMLHttpRequest.prototype.open = function (method, url, ...rest) {
  this.__flowkitUrl = String(url || '');
  return _xhrOpen.call(this, method, url, ...rest);
};

XMLHttpRequest.prototype.setRequestHeader = function (header, value) {
  try {
    if (header && String(header).toLowerCase() === 'authorization' && value && String(value).includes('ya29.')) {
      const match = String(value).match(/ya29\.[a-zA-Z0-9_\-]+/);
      if (match) {
        window.dispatchEvent(new CustomEvent('TOKEN_CAPTURED', { detail: { token: match[0] } }));
      }
    }
  } catch {}
  return _xhrSetHeader.apply(this, arguments);
};

XMLHttpRequest.prototype.send = function (...args) {
  this.addEventListener('load', () => {
    try {
      if (this.__flowkitUrl.includes('/fx/api/') || this.__flowkitUrl.includes('/api/') || this.__flowkitUrl.includes('googleapis.com')) {
        emitMediaUrls(this.__flowkitUrl, this.responseText || '');
      }
    } catch {}
  }, { once: true });
  return _xhrSend.apply(this, args);
};

function scanRenderedMedia() {
  try {
    for (const entry of performance.getEntriesByType('resource')) {
      if (entry.name && (entry.name.includes('storage.googleapis.com') || entry.name.includes('googleusercontent.com') || entry.name.includes('aisandbox-pa.googleapis.com'))) {
        emitMediaUrls('performance', entry.name);
      }
    }
    const uuidRe = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    for (const node of document.querySelectorAll('video, source, img, [data-media-id], [data-id]')) {
      const src = node.currentSrc || node.src || node.getAttribute('src') || '';
      const closestWithId = node.closest('[data-media-id], [data-id], [id]');
      const idVal = node.getAttribute('data-media-id') || node.getAttribute('data-id') || (closestWithId ? (closestWithId.getAttribute('data-media-id') || closestWithId.getAttribute('data-id') || closestWithId.id) : '');
      if (src && uuidRe.test(src)) {
        emitMediaUrls('dom', src);
      } else if (src && idVal && uuidRe.test(idVal)) {
        const mid = idVal.match(uuidRe)[0];
        emitMediaUrls('dom_mapped', JSON.stringify({ mediaId: mid, url: src }));
      }
    }
    for (const node of document.querySelectorAll('[style*="url"]')) {
      const style = node.getAttribute('style') || '';
      if (style) emitMediaUrls('dom_style', style);
    }
  } catch {}
}

window.addEventListener('EXTRACT_PAGE_MEDIA', () => {
  try {
    scanRenderedMedia();
    const urls = [];
    for (const entry of performance.getEntriesByType('resource')) {
      if (entry.name && (entry.name.includes('storage.googleapis.com') || entry.name.includes('googleusercontent.com') || entry.name.includes('aisandbox-pa.googleapis.com'))) {
        urls.push(entry.name);
      }
    }
    for (const node of document.querySelectorAll('video, source, img, a, [data-media-id], [data-id]')) {
      const src = node.currentSrc || node.src || node.getAttribute('src') || node.href || '';
      if (src && (src.includes('storage.googleapis.com') || src.includes('googleusercontent.com') || src.includes('http'))) {
        urls.push(src);
      }
    }
    window.dispatchEvent(new CustomEvent('EXTRACT_PAGE_MEDIA_RESULT', { detail: { urls } }));
  } catch (err) {
    window.dispatchEvent(new CustomEvent('EXTRACT_PAGE_MEDIA_RESULT', { detail: { urls: [], error: String(err) } }));
  }
});


window.addEventListener('GET_CAPTCHA', async ({ detail }) => {
  const { requestId, pageAction } = detail;
  try {
    await waitForGrecaptcha();
    const token = await window.grecaptcha.enterprise.execute(SITE_KEY, {
      action: pageAction,
    });
    window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
      detail: { requestId, token },
    }));
  } catch (e) {
    window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
      detail: { requestId, error: e.message },
    }));
  }
});

function waitForGrecaptcha(timeout = 10000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      if (window.grecaptcha?.enterprise?.execute) return resolve();
      if (Date.now() - start > timeout) return reject(new Error('grecaptcha not available'));
      setTimeout(check, 200);
    };
    check();
  });
}
