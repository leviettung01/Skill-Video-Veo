// Cloud Account, Day Subscription, App Updater & Paid Template Store UI

(function () {
  if (window.__SAV_CLOUD_UI_LOADED) return;
  window.__SAV_CLOUD_UI_LOADED = true;

  let _cloudState = null;

  function escHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showMsg(msg, kind) {
    if (typeof window.toast === "function") {
      window.toast(msg, kind || "info");
    } else {
      alert(msg);
    }
  }

  async function cloudFetch(url, opts) {
    const res = await fetch(url, opts || {});
    return await res.json().catch(() => ({ ok: false, message: "HTTP " + res.status }));
  }

  function ensureTopbarPillAndModal() {
    const actions = document.querySelector(".topbar-actions");
    if (actions && !document.getElementById("btnCloudAccountPill")) {
      const btn = document.createElement("button");
      btn.id = "btnCloudAccountPill";
      btn.className = "btn btn-outline";
      btn.style.cssText = "padding:5px 10px; font-size:11.5px; border-color:rgba(245,158,11,0.5); color:#fbbf24;";
      btn.textContent = "☁️ Tài khoản Server";
      btn.onclick = () => openCloudModal("login");
      actions.prepend(btn);
    }

    if (!document.getElementById("modalCloudAccount")) {
      const wrap = document.createElement("div");
      wrap.id = "modalCloudAccount";
      wrap.className = "modal-backdrop";
      wrap.style.cssText = "position:fixed;inset:0;background:rgba(2,6,23,0.82);display:none;align-items:center;justify-content:center;z-index:9999;padding:16px;";
      wrap.innerHTML = `
        <div style="background:#0f172a;border:1px solid rgba(245,158,11,0.45);border-radius:14px;width:100%;max-width:720px;max-height:88vh;overflow:auto;padding:18px;color:#f1f5f9;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <div style="font-size:15px;font-weight:800;color:#fbbf24;">☁️ Tài Khoản Bản Quyền, Kho Template &amp; Cập Nhật Tool</div>
            <button id="btnCloseCloudModal" class="btn btn-xs btn-outline">✖ Đóng</button>
          </div>
          <div id="cloudModalBody">Đang tải...</div>
        </div>
      `;
      document.body.appendChild(wrap);
      document.getElementById("btnCloseCloudModal").onclick = closeCloudModal;
    }
  }

  function renderTopbarPill() {
    const btn = document.getElementById("btnCloudAccountPill");
    if (!btn) return;
    if (_cloudState && _cloudState.authenticated && _cloudState.user) {
      const u = _cloudState.user;
      const days = u.days_remaining ?? 0;
      const color = days <= 3 ? "#f87171" : "#34d399";
      btn.style.borderColor = days <= 3 ? "rgba(239,68,68,0.6)" : "rgba(16,185,129,0.55)";
      btn.style.color = color;
      btn.textContent = `⏳ Còn ${days} ngày (${u.plan_tier || "pro"})`;
    } else if (_cloudState && _cloudState.pending_email) {
      btn.style.color = "#fbbf24";
      btn.textContent = `⏳ Chờ duyệt (#${_cloudState.pending_user_id || "?"})`;
    } else {
      btn.style.color = "#fbbf24";
      btn.textContent = "☁️ Đăng nhập / Đăng ký";
    }
  }

  function closeCloudModal() {
    const m = document.getElementById("modalCloudAccount");
    if (m) m.style.display = "none";
  }

  async function openCloudModal(initialView) {
    ensureTopbarPillAndModal();
    const m = document.getElementById("modalCloudAccount");
    m.style.display = "flex";
    await refreshCloudStatus(true);
    renderCloudModalContent(initialView);
  }

  function renderCloudModalContent(mode) {
    const body = document.getElementById("cloudModalBody");
    if (!body) return;
    const s = _cloudState || {};
    const srvUrl = escHtml(s.server_url || "http://127.0.0.1:8000");

    if (s.authenticated && s.user) {
      const u = s.user;
      body.innerHTML = `
        <div style="background:#111827;border:1px solid rgba(148,163,184,0.2);border-radius:10px;padding:12px;margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;align-items:center;">
            <div>
              <div style="font-weight:800;font-size:14px;">👤 ${escHtml(u.full_name || u.email)} (#${u.id})</div>
              <div style="color:#94a3b8;font-size:12px;">Email: ${escHtml(u.email)} · Máy: ${u.active_devices || 1}/${u.max_devices || 1} · Gói: <strong style="color:#38bdf8;">${escHtml(u.plan_tier)}</strong></div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:18px;font-weight:800;color:#34d399;">Còn ${u.days_remaining || 0} ngày</div>
              <div style="color:#94a3b8;font-size:11px;">Tool v${escHtml(s.app_version || "6.1.0")}</div>
            </div>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;">
            <button class="btn btn-xs btn-primary" id="btnCloudCheckUpdate">🚀 Kiểm tra Update Tool</button>
            <button class="btn btn-xs btn-success" id="btnCloudLoadStore">🛍️ Mở Kho Template &amp; Gói VIP</button>
            <button class="btn btn-xs btn-outline" id="btnCloudSyncState">🔄 Đồng bộ quyền mới</button>
            <button class="btn btn-xs btn-amber" id="btnCloudUnbind">💻 Gỡ máy này (còn ${u.unbind_remaining ?? 0} lượt)</button>
            <button class="btn btn-xs btn-danger" id="btnCloudLogout">Đăng xuất</button>
          </div>
        </div>
        <div id="cloudDynamicArea" style="font-size:12.5px;">Nhấn <strong>"Mở Kho Template &amp; Gói VIP"</strong> để xem mẫu mới hoặc mẫu bán thêm.</div>
      `;
      document.getElementById("btnCloudSyncState").onclick = async () => {
        await refreshCloudStatus(true);
        renderCloudModalContent();
        showMsg("Đã đồng bộ thời hạn và quyền từ Server!", "ok");
      };
      document.getElementById("btnCloudCheckUpdate").onclick = checkAndStageUpdate;
      document.getElementById("btnCloudLoadStore").onclick = loadAndRenderCloudStore;
      document.getElementById("btnCloudUnbind").onclick = async () => {
        if (!confirm("Bạn muốn hủy liên kết máy này để chuyển sang máy tính khác?")) return;
        const r = await cloudFetch("/api/cloud/unbind", { method: "POST" });
        if (r.ok) {
          showMsg(r.message || "Đã gỡ thiết bị.", "ok");
          await refreshCloudStatus(false);
          renderCloudModalContent("login");
        } else {
          showMsg(r.message || "Không gỡ được máy.", "error");
        }
      };
      document.getElementById("btnCloudLogout").onclick = async () => {
        await cloudFetch("/api/cloud/logout", { method: "POST" });
        await refreshCloudStatus(false);
        renderCloudModalContent("login");
      };
      return;
    }

    const activeMode = mode === "register" ? "register" : "login";
    const pendingBox = s.pending_email ? `
      <div style="background:rgba(245,158,11,0.14);border:1px solid rgba(245,158,11,0.45);padding:10px;border-radius:8px;margin-bottom:10px;">
        <strong>⏳ Tài khoản đang chờ Admin duyệt:</strong> ${escHtml(s.pending_email)} (Mã TK: <strong>#${s.pending_user_id || "?"}</strong>).<br/>
        <span style="color:#cbd5e1;font-size:11.5px;">Sau khi Admin bấm kích hoạt và cấp số ngày trên Server, bạn đăng nhập bên dưới để dùng ngay.</span>
      </div>` : "";
    const errBox = s.error ? `<div style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.45);padding:8px;border-radius:8px;margin-bottom:10px;color:#fca5a5;">${escHtml(s.error)}</div>` : "";

    body.innerHTML = `
      ${pendingBox}${errBox}
      <div style="display:flex;gap:8px;margin-bottom:12px;">
        <button class="btn btn-xs ${activeMode === "login" ? "btn-primary" : "btn-outline"}" id="tabCloudLoginBtn">🔐 Đăng Nhập</button>
        <button class="btn btn-xs ${activeMode === "register" ? "btn-primary" : "btn-outline"}" id="tabCloudRegBtn">📝 Đăng Ký Tài Khoản Mới</button>
      </div>
      <div style="display:grid;gap:8px;">
        <div><label style="font-size:11px;color:#94a3b8;">Server URL</label><input id="inpCloudUrl" class="input" value="${srvUrl}" /></div>
        <div><label style="font-size:11px;color:#94a3b8;">Email</label><input id="inpCloudEmail" class="input" type="email" value="${escHtml(s.pending_email || "")}" placeholder="email@domain.com" /></div>
        ${activeMode === "register" ? `
          <div><label style="font-size:11px;color:#94a3b8;">Họ tên</label><input id="inpCloudName" class="input" placeholder="Nguyễn Văn A" /></div>
          <div><label style="font-size:11px;color:#94a3b8;">Số Zalo / SĐT (để Admin đối soát duyệt nhanh)</label><input id="inpCloudZalo" class="input" placeholder="09xx..." /></div>
        ` : ""}
        <div><label style="font-size:11px;color:#94a3b8;">Mật khẩu</label><input id="inpCloudPass" class="input" type="password" placeholder="Tối thiểu 6 ký tự" /></div>
        <button class="btn btn-primary" id="btnCloudSubmitAuth">${activeMode === "register" ? "📝 Gửi Đăng Ký Chờ Admin Duyệt" : "🔓 Đăng Nhập & Kích Hoạt Máy"}</button>
      </div>
    `;
    document.getElementById("tabCloudLoginBtn").onclick = () => renderCloudModalContent("login");
    document.getElementById("tabCloudRegBtn").onclick = () => renderCloudModalContent("register");
    document.getElementById("btnCloudSubmitAuth").onclick = async () => {
      const server_url = document.getElementById("inpCloudUrl").value.trim();
      const email = document.getElementById("inpCloudEmail").value.trim();
      const password = document.getElementById("inpCloudPass").value;
      if (activeMode === "register") {
        const full_name = document.getElementById("inpCloudName").value.trim();
        const phone_zalo = document.getElementById("inpCloudZalo").value.trim();
        const r = await cloudFetch("/api/cloud/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ server_url, email, password, full_name, phone_zalo }),
        });
        showMsg(r.message || (r.ok ? "Đăng ký thành công!" : "Đăng ký lỗi"), r.ok ? "ok" : "error");
        await refreshCloudStatus(false);
        renderCloudModalContent("login");
      } else {
        const r = await cloudFetch("/api/cloud/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ server_url, email, password }),
        });
        if (r.ok) {
          showMsg("Đăng nhập & kích hoạt thành công!", "ok");
          await refreshCloudStatus(false);
          renderCloudModalContent();
        } else {
          showMsg(r.message || "Đăng nhập thất bại", "error");
          await refreshCloudStatus(false);
          renderCloudModalContent("login");
        }
      }
    };
  }

  async function checkAndStageUpdate() {
    const area = document.getElementById("cloudDynamicArea");
    if (!area) return;
    area.innerHTML = "Đang kiểm tra bản cập nhật Tool trên Server...";
    const r = await cloudFetch("/api/cloud/check-update");
    if (!r.ok) {
      area.innerHTML = `<span style="color:#f87171;">${escHtml(r.message || "Lỗi kiểm tra")}</span>`;
      return;
    }
    if (!r.update_available || !r.latest) {
      area.innerHTML = `<span style="color:#34d399;">✅ Bạn đang dùng phiên bản mới nhất (${escHtml(r.current_version)}).</span>`;
      return;
    }
    const rel = r.latest;
    area.innerHTML = `
      <div style="background:#111827;border:1px solid rgba(56,189,248,0.45);padding:12px;border-radius:10px;">
        <div style="font-weight:800;color:#38bdf8;">🚀 Có bản cập nhật mới v${escHtml(rel.version)} (${(Number(rel.size_bytes || 0) / 1048576).toFixed(2)} MB)</div>
        <div style="margin:6px 0;color:#cbd5e1;white-space:pre-line;">${escHtml(rel.changelog || "")}</div>
        <button class="btn btn-xs btn-success" id="btnStageCloudUpdate">⬇️ Tải Bản Cập Nhật Về Máy</button>
      </div>
    `;
    document.getElementById("btnStageCloudUpdate").onclick = async () => {
      area.innerHTML = "⏳ Đang tải và kiểm tra mã SHA-256...";
      const s = await cloudFetch("/api/cloud/stage-update", { method: "POST" });
      if (s.ok) {
        area.innerHTML = `<div style="color:#34d399;">✅ Đã tải xong v${escHtml(s.version)} và kiểm SHA-256 hợp lệ tại: <code>${escHtml(s.staged_path)}</code></div>`;
      } else {
        area.innerHTML = `<div style="color:#f87171;">❌ ${escHtml(s.message || "Tải lỗi")}</div>`;
      }
    };
  }

  async function loadAndRenderCloudStore() {
    const area = document.getElementById("cloudDynamicArea");
    if (!area) return;
    area.innerHTML = "Đang tải danh sách Template & Gói mở rộng từ Server...";
    const r = await cloudFetch("/api/cloud/store/catalog");
    if (!r.ok) {
      area.innerHTML = `<span style="color:#f87171;">${escHtml(r.message || "Không tải được kho template")}</span>`;
      return;
    }
    const tpls = r.templates || [];
    if (!tpls.length) {
      area.innerHTML = "Kho Server hiện chưa đăng template nào.";
      return;
    }
    area.innerHTML = tpls.map(t => `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;background:#111827;border:1px solid rgba(148,163,184,0.2);border-radius:9px;padding:10px;margin-bottom:8px;">
        <div>
          <div style="font-weight:700;">${t.unlocked ? "🟢" : "🔒"} ${escHtml(t.title)} <code style="color:#fbbf24;">${escHtml(t.id)}</code></div>
          <div style="color:#94a3b8;font-size:11.5px;">Loại: ${escHtml(t.kind)} · v${escHtml(t.version)} · ${t.unlocked ? "Đã mở khóa" : "Mua thêm VIP: " + Number(t.price_vnd || 0).toLocaleString("vi-VN") + "đ"}</div>
        </div>
        <div>
          ${t.unlocked
            ? `<button class="btn btn-xs btn-success btn-cloud-dl-tpl" data-id="${escHtml(t.id)}" data-kind="${escHtml(t.kind)}">⬇️ Đồng bộ về Tool</button>`
            : `<button class="btn btn-xs btn-amber btn-cloud-buy-tpl" data-id="${escHtml(t.id)}" data-pack="${escHtml(t.pack_id || "")}" data-price="${t.price_vnd || 0}">🛒 Mua / Mở khóa</button>`}
        </div>
      </div>
    `).join("");

    area.querySelectorAll(".btn-cloud-dl-tpl").forEach(btn => {
      btn.onclick = async () => {
        btn.disabled = true;
        btn.textContent = "⏳ Đang tải...";
        const res = await cloudFetch("/api/cloud/store/sync-template", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ template_id: btn.dataset.id, kind: btn.dataset.kind }),
        });
        if (res.ok) {
          btn.textContent = "✅ Đã tải xong";
          showMsg(`Đã cập nhật ${btn.dataset.id} vào Tool!`, "ok");
          if (typeof window.refreshAll === "function") window.refreshAll(false);
        } else {
          btn.disabled = false;
          btn.textContent = "⬇️ Đồng bộ về Tool";
          showMsg(res.message || "Lỗi đồng bộ template", "error");
        }
      };
    });

    area.querySelectorAll(".btn-cloud-buy-tpl").forEach(btn => {
      btn.onclick = () => {
        const u = (_cloudState && _cloudState.user) || {};
        alert(
          `Để mở khóa "${btn.dataset.id}" (Pack: ${btn.dataset.pack}, Giá: ${Number(btn.dataset.price || 0).toLocaleString("vi-VN")}đ):\n` +
          `1. Nhắn Zalo Admin gửi Mã TK: #${u.id || "?"} (${u.email || ""})\n` +
          `2. Sau khi Admin cấp quyền trên Server, bấm "🔄 Đồng bộ quyền mới" là tải về dùng ngay!`
        );
      };
    });
  }

  async function refreshCloudStatus(refreshOnline) {
    _cloudState = await cloudFetch(`/api/cloud/status?refresh=${refreshOnline ? "1" : "0"}`);
    renderTopbarPill();
    if (_cloudState && _cloudState.enforced && !_cloudState.authenticated) {
      openCloudModal("login");
    }
    return _cloudState;
  }

  window.openCloudAccountModal = openCloudModal;

  document.addEventListener("DOMContentLoaded", () => {
    ensureTopbarPillAndModal();
    refreshCloudStatus(false);
  });
})();
