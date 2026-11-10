    function renderRolesList() {
      const box = document.getElementById("roleList");
      box.innerHTML = STATE.roles.map(r => `
        <div class="proj-item" onclick="loadRoleContent('${r.filename}')">
          <div style="font-weight:700; font-size:12px;">📄 ${r.filename}</div>
          <div style="font-size:10.5px; color:var(--muted); margin-top:3px;">
            ${(r.size / 1024).toFixed(1)} KB • ${r.updated_at}
          </div>
        </div>
      `).join("");
    }

    async function loadRoleContent(filename) {
      const res = await apiGet(`/api/roles/read?file=${encodeURIComponent(filename)}`);
      if (!res.ok) return;
      document.getElementById("inpRoleFilename").value = res.filename;
      document.getElementById("inpRoleContent").value = res.content;
    }

    function newRoleSkill() {
      document.getElementById("inpRoleFilename").value = "RoleSkillMoi.MD";
      document.getElementById("inpRoleContent").value = "# ROLE SKILL MỚI\n\nMô tả quy tắc phân tích sản phẩm...";
    }

    async function saveCurrentRole() {
      const filename = document.getElementById("inpRoleFilename").value.trim();
      const content = document.getElementById("inpRoleContent").value;
      if (!filename) return alert("Nhập tên file Role Skill!");
      const res = await apiPost("/api/roles/save", { filename, content });
      if (res.ok) {
        alert("Đã lưu Role Skill: " + filename);
        await refreshAll();
      }
    }

    async function deleteCurrentRole() {
      const filename = document.getElementById("inpRoleFilename").value.trim();
      if (!filename || !confirm(`Xóa Role Skill ${filename}?`)) return;
      await apiPost("/api/roles/delete", { filename });
      document.getElementById("inpRoleFilename").value = "";
      document.getElementById("inpRoleContent").value = "";
      await refreshAll();
    }

    function renderAccountsTable() {
      const gAccs = STATE.accounts.google_accounts || [];
      const cAccs = STATE.accounts.grok_accounts || [];
      const badgeFlow = document.getElementById("badgeFlowMultiAccCount");
      if (badgeFlow) {
        const activeG = gAccs.filter(x => x.active).length;
        badgeFlow.textContent = `${activeG}/${gAccs.length} Tài khoản Flow đang bật • Chạy Đa Luồng`;
      }
      const box = document.getElementById("accountsTable");
      if (!box) return;
      if (!gAccs.length && !cAccs.length) {
        box.innerHTML = `<div style="color:var(--muted); padding:10px;">Chưa có tài khoản nào. Hãy bấm <b>➕ Thêm Tài Khoản Flow Mới</b> ở trên để bắt đầu.</div>`;
        return;
      }

      let html = "";
      if (gAccs.length > 0) {
        html += `
          <div style="font-size:11.5px; font-weight:800; color:#60a5fa; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
            <span>🌐 DANH SÁCH TÀI KHOẢN GOOGLE FLOW CHẠY ĐA LUỒNG (${gAccs.length} TÀI KHOẢN)</span>
            <span style="font-size:10.5px; color:#93c5fd;">Hệ thống tự động xoay vòng (Round-Robin) tất cả các tài khoản đang bật</span>
          </div>
        `;
        html += gAccs.map((a, idx) => {
          const prof = a.profile_name || "leviettung04";
          const projId = a.project_id || a.proxy_url || "";
          const cookieBadge = a.has_cookie
            ? `<span class="badge badge-done" style="font-size:9.5px;">🍪 Đã có Cookie</span>`
            : `<span class="badge badge-wait" style="font-size:9.5px;">🍪 Chờ Cookie</span>`;
          const tokenBadge = a.has_token
            ? `<span class="badge badge-run" style="font-size:9.5px;">🔑 Đã có Bearer Token</span>`
            : `<span class="badge" style="background:rgba(148,163,184,0.15); color:#cbd5e1; font-size:9.5px;">🔑 Tự lấy qua Chrome</span>`;
          return `
            <div class="proj-item" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; cursor:default; border-color:${a.active ? 'rgba(59,130,246,0.4)' : 'var(--border)'};">
              <div>
                <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                  <span class="badge badge-run">#${idx + 1}</span>
                  <span style="font-size:13px; font-weight:800; color:#f8fafc;">🌐 ${a.name}</span>
                  ${cookieBadge}
                  ${tokenBadge}
                  <span class="badge ${a.active ? 'badge-done' : 'badge-fail'}">${a.active ? '✅ Đang Bật Đa Luồng' : '⏸️ Đang Tắt'}</span>
                </div>
                <div style="font-size:11px; color:var(--muted); margin-top:4px;">
                  Profile Chrome: <code style="color:#fde68a; font-weight:700;">${prof}</code> |
                  Project ID: <code>${projId}</code> |
                  Models: <span style="color:#a5f3fc">${(a.available_video_models || []).join(", ")}</span>
                </div>
              </div>
              <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                <button class="btn btn-xs btn-primary" onclick="openChromeForProfile('${prof}')" title="Mở ngay cửa sổ Google Chrome độc lập của riêng tài khoản '${prof}' lên trước màn hình">🌐 Mở Chrome (${prof})</button>
                <button class="btn btn-xs btn-success" onclick="refreshGoogleFlowSession('${prof}')" title="Tự động đóng Chrome (nếu đang mở) và trích xuất/làm mới Cookie & Token ngay cho tài khoản '${prof}'">🔄 Tự Lấy Cookie Mới</button>
                <button class="btn btn-xs btn-primary" style="background:#0284c7; border-color:#38bdf8;" onclick="scanAndSyncFlowVoices('${prof}', false)" title="Quét toàn bộ các Voice tạo thủ công trên Google Flow của tài khoản '${prof}' về Tool">🎙️ Đồng Bộ Voice</button>
                <button class="btn btn-xs btn-amber" onclick="openAddGoogleAccountModal('${prof}', '${a.name}', '${projId}')" title="Dán nhanh Cookie hoặc Bearer Token cho tài khoản này">🍪 Cookie / Token</button>
                <button class="btn btn-xs btn-outline" onclick="toggleAccount('${a.name}')">${a.active ? 'Tắt' : 'Bật'}</button>
                <button class="btn btn-xs btn-danger" onclick="deleteAccount('${a.name}')">🗑️</button>
              </div>
            </div>
          `;
        }).join("");
      }

      if (cAccs.length > 0) {
        html += `
          <div style="font-size:11.5px; font-weight:800; color:#34d399; margin:12px 0 6px 0;">
            ⚡ TÀI KHOẢN CLIPROXY — GROK / CHATGPT CODEX (${cAccs.length} TÀI KHOẢN)
          </div>
        `;
        html += cAccs.map(a => `
          <div class="proj-item" style="display:flex; justify-content:space-between; align-items:center; cursor:default;">
            <div>
              <div style="font-size:12.5px; font-weight:700;">
                ⚡ CLIProxy (Grok / ChatGPT Codex): ${a.name}
              </div>
              <div style="font-size:11px; color:var(--muted); margin-top:2px;">
                Endpoint: <code>${a.proxy_url || 'http://127.0.0.1:8317/v1'}</code> |
                Models: <span style="color:#a5f3fc">${(a.available_video_models || []).join(", ")}, gpt-image-1</span>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <span class="badge ${a.active ? 'badge-done' : 'badge-fail'}">${a.active ? 'Đang Bật' : 'Đang Tắt'}</span>
              <button class="btn btn-xs btn-outline" onclick="toggleAccount('${a.name}')">${a.active ? 'Tắt' : 'Bật'}</button>
              <button class="btn btn-xs btn-danger" onclick="deleteAccount('${a.name}')">🗑️</button>
            </div>
          </div>
        `).join("");
      }

      box.innerHTML = html;
    }

    async function openCaptchaSolverChrome() {
      const banner = document.getElementById("loginStatusBanner");
      if (banner) {
        banner.innerHTML = `🧩 Đang mở Profile Chrome RIÊNG BIỆT (<b>captcha_bridge_solver</b>) gắn sẵn Extension <b>LeVietTung_autoveo</b> — <b>KHÔNG cần đăng nhập tài khoản Google</b>, chỉ để treo giải Captcha!`;
      }
      if (typeof toast === "function") {
        toast("🧩 Đang mở Chrome riêng treo Extension giải Captcha (Không Login)...", "info");
      }
      const res = await apiPost("/api/accounts/open-captcha-extension-chrome", {});
      if (res && res.ok) {
        if (banner) banner.innerHTML = `✅ ${res.message}`;
        if (typeof toast === "function") toast(res.message, "ok");
      }
    }

    async function openChromeForProfile(profName) {
      const prof = (profName || document.getElementById("inpGoogleProfile")?.value || "leviettung04").trim();
      const banner = document.getElementById("loginStatusBanner");
      if (banner) banner.innerHTML = `🌐 Đang mở cửa sổ Chrome độc lập cho Profile <b>${prof}</b> (sau khi đăng nhập xong, hãy ĐÓNG cửa sổ Chrome này để tự động lưu Cookie)...`;
      if (typeof toast === "function") toast(`🌐 Đang mở Chrome độc lập cho Profile '${prof}'...`, "info");
      const res = await apiPost("/api/accounts/open-chrome-profile", { profile_name: prof });
      if (res && res.ok) {
        if (typeof toast === "function") toast(res.message || `✅ Đã mở cửa sổ Chrome (${prof})!`, "ok");
        await refreshAll(true);
      }
    }

    async function refreshGoogleFlowSession(profName = "") {
      const target = (profName || "").trim();
      const banner = document.getElementById("loginStatusBanner");
      if (banner) {
        banner.innerHTML = target
          ? `🔄 Đang tự động mở ngầm Profile Chrome <b>${target}</b> để lấy Cookie & Token Google Flow mới...`
          : `🔄 Đang tự động kiểm tra & lấy Cookie mới cho toàn bộ tài khoản Google Flow...`;
      }
      if (typeof toast === "function") {
        toast(target ? `🔄 Đang tự động lấy Cookie mới cho '${target}'...` : "🔄 Đang tự động làm mới Cookie tất cả tài khoản Flow...", "info");
      }
      const res = await apiPost("/api/accounts/refresh-google", {
        profile_name: target,
        force_refresh: true,
        check_credits: true,
      });
      if (res && res.ok) {
        if (typeof toast === "function") toast(res.message || "✅ Đã tự động cập nhật Cookie Google Flow mới!", "ok");
        await refreshAll(false);
      } else {
        const errMsg = (res && (res.error || res.message)) || "Không thể tự lấy Cookie — hãy bấm Mở Chrome để đăng nhập 1 lần.";
        if (typeof toast === "function") toast(errMsg, "err");
        await refreshAll(false);
      }
    }

    async function loginGoogleProfileDirect(profName) {
      const inp = document.getElementById("inpGoogleProfile");
      if (inp && profName) inp.value = profName;
      await loginGoogleFlow(profName);
    }

    async function loginGoogleFlow(profOverride = "") {
      let prof = (profOverride || document.getElementById("inpGoogleProfile")?.value || "").trim();
      if (!prof) {
        return await quickCreateNewGoogleAccount();
      }
      const banner = document.getElementById("loginStatusBanner");
      if (banner) banner.innerHTML = `🔍 Đang mở trình duyệt Chrome độc lập (Profile: <b>${prof}</b>) để đăng nhập Google Flow 1 lần...`;
      if (typeof toast === "function") toast(`🔑 Đang mở Chrome Profile '${prof}' để đăng nhập Google Flow...`, "info");
      const res = await apiPost("/api/accounts/login-google", { profile_name: prof });
      if (res && res.ok) {
        setTimeout(() => refreshAll(true), 500);
      }
    }

    async function openPythonAccountGui(profName = "", autoLogin = false) {
      const prof = (profName || document.getElementById("inpGoogleProfile")?.value || "").trim();
      const banner = document.getElementById("loginStatusBanner");
      if (banner) banner.innerHTML = `🐍 Đang mở cửa sổ <b>Quản Lý Tài Khoản Google Flow (Python Desktop PyQt6)</b>...`;
      if (typeof toast === "function") toast("🐍 Đang mở cửa sổ Quản Lý Tài Khoản Google Flow (Python Tool)...", "info");
      const res = await apiPost("/api/accounts/open-python-gui", { profile_name: prof, auto_login: autoLogin });
      if (res && res.ok) {
        if (banner) banner.innerHTML = `✅ ${res.message || "Đã mở cửa sổ Python Tool (PyQt6) trên màn hình!"}`;
        if (typeof toast === "function") toast(res.message || "✅ Đã mở cửa sổ Python Tool!", "ok");
      }
    }

    async function quickCreateNewGoogleAccount() {
      const gAccs = (STATE.accounts && STATE.accounts.google_accounts) || [];
      const existingProfs = new Set(gAccs.map(a => (a.profile_name || "").toLowerCase()));
      let nextIdx = Math.max(2, gAccs.length + 1);
      while (existingProfs.has(`flow_acc_${nextIdx}`)) nextIdx++;
      const suggestedProf = `flow_acc_${nextIdx}`;
      const inpEl = document.getElementById("inpGoogleProfile");
      const typedProf = (inpEl ? inpEl.value.trim() : "").replace(/[^a-zA-Z0-9._@-]+/g, "_");
      const cleanProf = (typedProf && !existingProfs.has(typedProf.toLowerCase())) ? typedProf : suggestedProf;
      if (inpEl) inpEl.value = cleanProf;
      const banner = document.getElementById("loginStatusBanner");
      if (banner) banner.innerHTML = `🚀 Đang tạo Profile Chrome mới <b>${cleanProf}</b> và mở cửa sổ đăng nhập Google Flow...`;
      if (typeof toast === "function") {
        toast(`🚀 Đang tạo Profile Chrome mới '${cleanProf}' và mở trình duyệt...`, "info");
      }
      const res = await apiPost("/api/accounts/add-google-account", {
        profile_name: cleanProf,
        email: cleanProf,
        project_id: "bf4979d1-548a-44bd-a265-3927bba76dc1",
        open_browser: true,
      });
      if (res && res.ok) {
        if (typeof toast === "function") toast(res.message || `✅ Đã mở Chrome cho Profile mới: ${cleanProf}`, "ok");
        await refreshAll(false);
        if (typeof loadSettingsTab === "function") loadSettingsTab(false);
      } else {
        alert((res && res.error) || "Lỗi khi tạo tài khoản Google Flow mới");
      }
    }

    function openAddGoogleAccountModal(prof = "", email = "", projId = "") {
      const gAccs = (STATE.accounts && STATE.accounts.google_accounts) || [];
      let defProf = prof;
      if (!defProf) {
        const existingProfs = new Set(gAccs.map(a => a.profile_name));
        let nextIdx = gAccs.length + 1;
        while (existingProfs.has(`flow_acc_${nextIdx}`)) nextIdx++;
        defProf = `flow_acc_${nextIdx}`;
      }
      document.getElementById("inpModalGoogleProfile").value = defProf;
      document.getElementById("inpModalGoogleEmail").value = email || `Google_${defProf}`;
      document.getElementById("inpModalGoogleProjId").value = projId || "bf4979d1-548a-44bd-a265-3927bba76dc1";
      document.getElementById("inpModalGoogleToken").value = "";
      document.getElementById("inpModalGoogleCookie").value = "";
      openModal("modalAddGoogleAccount");
    }

    async function submitAddGoogleAccount(openBrowser = true) {
      const profile_name = document.getElementById("inpModalGoogleProfile").value.trim();
      const email = document.getElementById("inpModalGoogleEmail").value.trim();
      const project_id = document.getElementById("inpModalGoogleProjId").value.trim();
      const bearer_token = document.getElementById("inpModalGoogleToken").value.trim();
      const cookie_input = document.getElementById("inpModalGoogleCookie").value.trim();

      if (!profile_name) {
        alert("Vui lòng nhập Mã Profile Chrome (VD: flow_acc_2)!");
        return;
      }
      closeModal("modalAddGoogleAccount");
      if (typeof toast === "function") {
        toast(openBrowser ? `🚀 Đang tạo Profile '${profile_name}' & mở Chrome...` : `💾 Đang lưu tài khoản '${profile_name}'...`, "info");
      }
      const res = await apiPost("/api/accounts/add-google-account", {
        profile_name,
        email,
        project_id,
        bearer_token,
        cookie_input,
        open_browser: openBrowser,
      });
      if (res && res.ok) {
        if (typeof toast === "function") toast(res.message || "✅ Đã lưu tài khoản Google Flow!", "ok");
        await refreshAll(false);
        if (typeof loadSettingsTab === "function") loadSettingsTab(false);
      } else {
        alert((res && res.error) || "Lỗi khi thêm tài khoản Google Flow");
      }
    }

    async function syncAllGoogleProfiles() {
      if (typeof toast === "function") toast("🔄 Đang quét toàn bộ Profile Chrome và Cookie Google Flow...", "info");
      const res = await apiPost("/api/accounts/sync-google-profiles", {});
      if (res && res.ok) {
        if (typeof toast === "function") toast(`✅ Đã đồng bộ Profile Google Flow (Thêm mới: ${res.added || 0})`, "ok");
        await refreshAll(false);
      }
    }

    async function loginCliProxy(provider) {
      const banner = document.getElementById("loginStatusBanner");
      if (banner) banner.innerHTML = `🔑 Đang khởi tạo OAuth và mở trình duyệt đăng nhập <b>${provider}</b>...`;
      if (typeof showToast === "function") showToast(`🔑 Đang mở trình duyệt đăng nhập ${provider}...`);
      const res = await apiPost("/api/accounts/login-cliproxy", { provider });
      if (res && res.ok) {
        setTimeout(() => refreshAll(true), 1200);
      }
    }

    async function syncCliProxy() {
      const res = await apiPost("/api/accounts/sync-cliproxy", {});
      if (res.ok) {
        alert(`Đã đồng bộ CLIProxy! Thêm mới: ${res.added}, Xóa hết hạn: ${res.removed}`);
        refreshAll();
      }
    }

    async function toggleAccount(name) {
      await apiPost("/api/accounts/toggle", { name });
      refreshAll();
    }

    async function deleteAccount(name) {
      if (!confirm(`Xóa tài khoản ${name}?`)) return;
      await apiPost("/api/accounts/delete", { name });
      refreshAll();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TAB MỚI 1: SẢN PHẨM (CRAWL TỰ ĐỘNG CÁCH 1 / CÁCH 2 & CHỌN TEMPLATE VIDEO)
    // ═══════════════════════════════════════════════════════════════════════
    STATE.productsStore = [];
    STATE.videoTemplates = [];
    STATE.templateRootDir = "Template";
    STATE.prodStoreFilter = "all";
    STATE.prodStoreViewMode = "table"; // 'table' (chuẩn Ảnh 2) | 'grid'
    STATE.selectedStorePids = new Set();

    function showProdBanner(msg, isErr = false) {
      const el = document.getElementById("prodStatusBanner");
      if (!el) return;
      el.style.display = msg ? "block" : "none";
      el.style.color = isErr ? "#fca5a5" : "#a5f3fc";
      el.style.borderColor = isErr ? "rgba(239,68,68,0.45)" : "var(--border-light)";
      el.innerHTML = msg;
    }

    function toggleBulkProdDrawer() {
      const el = document.getElementById("bulkProdDrawer");
      if (el) el.style.display = (el.style.display === "none" ? "block" : "none");
    }

    function setProdStoreViewMode(mode) {
      STATE.prodStoreViewMode = (mode === "grid") ? "grid" : "table";
      const tblWrap = document.getElementById("productsStoreTableContainer");
      const gridWrap = document.getElementById("productsStoreGrid");
      const btnTbl = document.getElementById("btnStoreViewTable");
      const btnGrd = document.getElementById("btnStoreViewGrid");
      if (tblWrap) tblWrap.style.display = STATE.prodStoreViewMode === "table" ? "block" : "none";
      if (gridWrap) gridWrap.style.display = STATE.prodStoreViewMode === "grid" ? "grid" : "none";
      if (btnTbl) btnTbl.className = STATE.prodStoreViewMode === "table" ? "btn btn-xs btn-amber" : "btn btn-xs btn-outline";
      if (btnGrd) btnGrd.className = STATE.prodStoreViewMode === "grid" ? "btn btn-xs btn-amber" : "btn btn-xs btn-outline";
      renderProductsStoreGrid();
    }

    function setProdStoreFilter(flt) {
      STATE.prodStoreFilter = flt;
      ["All", "HasVideo", "Hot", "Ready", "Pending"].forEach(k => {
        const b = document.getElementById("fltProd" + k);
        if (b) b.classList.remove("active");
      });
      const mapBtn = { all: "fltProdAll", has_video: "fltProdHasVideo", hot: "fltProdHot", ready: "fltProdReady", pending: "fltProdPending" };
      const act = document.getElementById(mapBtn[flt] || "fltProdAll");
      if (act) act.classList.add("active");
      renderProductsStoreGrid();
    }

    function toggleStorePriceSoldSort() {
      const sel = document.getElementById("selStoreSort");
      if (!sel) return;
      if (sel.value === "sold_desc") sel.value = "price_asc";
      else if (sel.value === "price_asc") sel.value = "price_desc";
      else sel.value = "sold_desc";
      renderProductsStoreGrid();
    }

    function _parseNumVal(raw) {
      if (raw === undefined || raw === null || raw === "") return 0;
      const n = parseInt(String(raw).replace(/[^\d]/g, ""), 10);
      return isNaN(n) ? 0 : n;
    }

    function _updateSelectedCounters() {
      const cnt = STATE.selectedStorePids.size;
      ["cntProdSelectedCopy", "cntProdSelectedVid", "cntProdSelectedDel"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = cnt;
      });
    }

    function toggleSelectSingleStoreProduct(pid, checked) {
      if (checked) STATE.selectedStorePids.add(String(pid));
      else STATE.selectedStorePids.delete(String(pid));
      _updateSelectedCounters();
      const row = document.getElementById(`pstoreRow_${pid}`);
      if (row) {
        if (checked) row.classList.add("selected");
        else row.classList.remove("selected");
      }
    }

    function toggleSelectGroupStoreProducts(dateKey, checked) {
      const visible = STATE._lastFilteredStoreProds || [];
      visible.forEach(p => {
        if ((p.date_key || "unknown") === dateKey) {
          if (checked) STATE.selectedStorePids.add(String(p.product_id));
          else STATE.selectedStorePids.delete(String(p.product_id));
        }
      });
      renderProductsStoreGrid();
    }

    function toggleSelectAllStoreProducts(checked) {
      const visible = STATE._lastFilteredStoreProds || [];
      visible.forEach(p => {
        if (checked) STATE.selectedStorePids.add(String(p.product_id));
        else STATE.selectedStorePids.delete(String(p.product_id));
      });
      renderProductsStoreGrid();
    }

    function _getTargetStoreProductsForBulk() {
      const all = STATE.productsStore || [];
      if (STATE.selectedStorePids.size > 0) {
        return all.filter(p => STATE.selectedStorePids.has(String(p.product_id)));
      }
      return STATE._lastFilteredStoreProds || all;
    }

    function copyStoreGroupIds(dateKey) {
      const visible = (STATE._lastFilteredStoreProds || []).filter(p => (p.date_key || "unknown") === dateKey);
      if (!visible.length) return;
      const ids = visible.map(p => p.product_id).join("\n");
      navigator.clipboard.writeText(ids);
      showProdBanner(`📋 Đã copy <b>${visible.length} ID sản phẩm</b> trong nhóm ngày <b>${visible[0].date_label || dateKey}</b>!`);
    }

    function copySelectedStoreProducts(mode = "id") {
      const targets = _getTargetStoreProductsForBulk();
      if (!targets.length) return alert("Chưa có sản phẩm nào để copy!");
      let text = "";
      if (mode === "id") {
        text = targets.map(p => p.product_id).join("\n");
        navigator.clipboard.writeText(text);
        showProdBanner(`📋 Đã copy <b>${targets.length} ID sản phẩm</b> vào Clipboard!`);
      } else if (mode === "images") {
        const links = [];
        targets.forEach(p => {
          const rImgs = (p.remote_images && p.remote_images.length) ? p.remote_images : (p.local_images || []);
          rImgs.forEach(u => links.push(u));
        });
        navigator.clipboard.writeText(links.join("\n"));
        showProdBanner(`🖼️ Đã copy <b>${links.length} link ảnh</b> của ${targets.length} sản phẩm!`);
      } else if (mode === "full") {
        text = targets.map((p, i) => [
          `#${i + 1}. ${p.title || '(Chưa có tiêu đề)'}`,
          `   - ID: ${p.product_id}`,
          `   - Shop: ${p.seller || 'TikTok Shop'}`,
          `   - Giá: ${formatVndPrice(p.price)} | Đã bán: ${formatSoldNumber(p.sold_count_label || p.sold_count)}`,
          `   - Link: ${p.web_url || ('https://shop.tiktok.com/vn/pdp/' + p.product_id)}`,
        ].join("\n")).join("\n\n");
        navigator.clipboard.writeText(text);
        showProdBanner(`📑 Đã copy <b>Full thông tin của ${targets.length} sản phẩm</b> vào Clipboard!`);
      } else {
        text = targets.map(p => `${p.product_id}\t${p.title || ''}\t${formatVndPrice(p.price)}\t${formatSoldNumber(p.sold_count_label || p.sold_count)}`).join("\n");
        navigator.clipboard.writeText(text);
        showProdBanner(`📋 Đã copy danh sách <b>${targets.length} sản phẩm</b> (ID • Tên • Giá • Đã bán)!`);
      }
    }

    async function crawlSelectedOrMissingStoreProducts(method = "auto") {
      const selectedIds = Array.from(STATE.selectedStorePids);
      if (selectedIds.length > 0) {
        showProdBanner(`⏳ Đang tải thông tin & ảnh cho <b>${selectedIds.length} sản phẩm đã chọn</b> bằng ${method === 'browser' ? 'Cách 2 (Browser)' : 'Cách 1 (Auto 1→2)'}...`);
        let okCnt = 0;
        for (const pid of selectedIds) {
          const r = await apiPost("/api/products-store/fetch-details", { product_id: pid, method, force: true });
          if (r && r.ok) okCnt++;
        }
        showProdBanner(`✅ Đã tải xong <b>${okCnt}/${selectedIds.length}</b> sản phẩm đã chọn!`);
        await loadProductsStore(false);
        await refreshAll(true);
      } else {
        await batchFetchMissingProducts(method);
      }
    }

    async function batchCreateVideoForSelectedProducts() {
      const selectedIds = Array.from(STATE.selectedStorePids);
      if (!selectedIds.length) {
        return alert("Vui lòng tích chọn ít nhất 1 sản phẩm trong bảng để Tạo Video hàng loạt!");
      }
      const tpl = document.getElementById("selQuickTemplate")?.value || "001";
      const vpc = document.getElementById("selQuickVideosPerChar")?.value || "";
      if (!confirm(`🎬 Khởi tạo kịch bản (Template: ${tpl}) cho ${selectedIds.length} sản phẩm đã chọn và chạy tạo Video?`)) return;
      showProdBanner(`🚀 Đang khởi tạo kịch bản cho <b>${selectedIds.length} sản phẩm</b> theo Template <b>${tpl}</b>...`);
      let lastPid = selectedIds[0];
      for (let i = 0; i < selectedIds.length; i++) {
        const pid = selectedIds[i];
        lastPid = pid;
        await apiPost("/api/products-store/create-video", {
          input: pid,
          template_name: tpl,
          method: "auto",
          videos_per_character: vpc ? parseInt(vpc, 10) : null,
          force_regenerate_prompts: true,
          auto_run: (i === 0), // Chạy luồng tự động cho SP đầu tiên ngay lập tức
        });
      }
      showProdBanner(`🎉 Đã tạo xong kịch bản cho <b>${selectedIds.length} sản phẩm</b> và bắt đầu chạy đa luồng!`);
      await loadProductsStore(false);
      await refreshAll(false);
      STATE.currentProjectId = lastPid;
      switchTab("dashboard", document.getElementById("navBtn-dashboard"));
      loadProjectDetail(lastPid, false);
    }

    async function deleteSelectedStoreProducts() {
      const selectedIds = Array.from(STATE.selectedStorePids);
      if (!selectedIds.length) return alert("Vui lòng tích chọn ít nhất 1 sản phẩm để xóa!");
      if (!confirm(`🗑️ Bạn có chắc muốn xóa ${selectedIds.length} sản phẩm đã chọn khỏi danh sách?`)) return;
      for (const pid of selectedIds) {
        await apiPost("/api/products-store/delete", { product_id: pid, delete_project: false });
        STATE.selectedStorePids.delete(pid);
      }
      showProdBanner(`🗑️ Đã xóa ${selectedIds.length} sản phẩm đã chọn.`);
      await loadProductsStore(false);
    }

    async function toggleHotProductQuick(pid, ev) {
      if (ev) ev.stopPropagation();
      const p = (STATE.productsStore || []).find(x => x.product_id === pid);
      if (!p) return;
      p.is_hot = !p.is_hot;
      renderProductsStoreGrid();
      await apiPost("/api/products-store/toggle-hot", { product_id: pid, is_hot: p.is_hot });
    }

    function populateTemplateDropdowns(templates) {
      STATE.videoTemplates = templates || [];
      const optsHtml = STATE.videoTemplates.map(t =>
        `<option value="${t.code || t.folder_name}">[Mã #${t.code || '001'}] ${t.folder_name} — ${t.name}</option>`
      ).join("") || `<option value="001">[Mã #001] Nhà Xưởng — Nhà Xưởng (Xả Kho Tận Gốc)</option>`;

      const sel = document.getElementById("selQuickTemplate");
      if (sel) {
        const cur = sel.value;
        sel.innerHTML = optsHtml;
        if (cur && STATE.videoTemplates.some(t => (t.code === cur || t.folder_name === cur))) sel.value = cur;
      }

      const selMkt = document.getElementById("selMarketQuickCode");
      if (selMkt) {
        const curM = selMkt.value;
        selMkt.innerHTML = optsHtml;
        if (curM && STATE.videoTemplates.some(t => (t.code === curM || t.folder_name === curM))) selMkt.value = curM;
      }
      if (typeof updateMarketAiCommandPreview === "function") updateMarketAiCommandPreview();
    }

    async function loadProductsStore(forceMsg = false) {
      if (forceMsg) showProdBanner("⏳ Đang tải danh sách sản phẩm & Template...");
      const res = await apiGet("/api/products-store");
      if (!res || !res.ok) {
        if (forceMsg) showProdBanner("❌ Không tải được danh sách sản phẩm.", true);
        return;
      }
      STATE.productsStore = res.products || [];
      if (res.templates) populateTemplateDropdowns(res.templates);
      if (forceMsg) showProdBanner(`✅ Đã đồng bộ ${STATE.productsStore.length} sản phẩm và ${(res.templates || []).length} Template Video.`);
      renderProductsStoreGrid();
    }

    function formatVndPrice(raw) {
      if (raw === undefined || raw === null || raw === "") return "";
      const s = String(raw).trim();
      const num = parseInt(s.replace(/[^\d]/g, ""), 10);
      if (!isNaN(num) && num > 0) {
        return num.toLocaleString("en-US") + " ₫";
      }
      return s.includes("₫") ? s : (s + " ₫");
    }

    function formatSoldNumber(raw) {
      if (raw === undefined || raw === null || raw === "") return "0";
      const s = String(raw).trim();
      const num = parseInt(s.replace(/[^\d]/g, ""), 10);
      if (!isNaN(num) && num > 0 && /^\d+$/.test(s.replace(/[.,]/g, ""))) {
        return num.toLocaleString("en-US");
      }
      return s;
    }

    function renderProductsStoreGrid() {
      const gridBox = document.getElementById("productsStoreGrid");
      const tblBody = document.getElementById("productsStoreTableBody");
      if (!gridBox && !tblBody) return;

      const prods = STATE.productsStore || [];
      const q = (document.getElementById("inpStoreSearch")?.value || "").trim().toLowerCase();
      const dateFlt = document.getElementById("selStoreDateFilter")?.value || "all";
      const sortMode = document.getElementById("selStoreSort")?.value || "date_desc";

      // Cập nhật dropdown lọc theo ngày (📅 Tất cả ngày + từng ngày)
      const dayGroupsMap = new Map();
      prods.forEach(p => {
        const dk = p.date_key || "unknown";
        const dl = p.date_label || "Ngày khác";
        if (!dayGroupsMap.has(dk)) dayGroupsMap.set(dk, { key: dk, label: dl, count: 0 });
        dayGroupsMap.get(dk).count++;
      });
      const selDateEl = document.getElementById("selStoreDateFilter");
      if (selDateEl) {
        const curVal = selDateEl.value || "all";
        const sortedDays = Array.from(dayGroupsMap.values()).sort((a, b) => b.key.localeCompare(a.key));
        selDateEl.innerHTML = `<option value="all">📅 Tất cả ngày (${prods.length})</option>` +
          sortedDays.map(d => `<option value="${d.key}" ${d.key === curVal ? 'selected' : ''}>📅 ${d.label} (${d.count})</option>`).join("");
      }

      const cntAll = prods.length;
      const cntVid = prods.filter(p => (p.final_videos_count || 0) > 0).length;
      const cntReady = prods.filter(p => p.status === "ready" || (p.image_count || 0) > 0).length;
      const cntPending = prods.filter(p => p.status !== "ready" && (p.image_count || 0) === 0).length;
      const cntHot = prods.filter(p => p.is_hot).length;

      const setTxt = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
      setTxt("cntProdAll", cntAll);
      setTxt("cntProdTotalSub", cntAll);
      setTxt("cntProdDays", Math.max(1, dayGroupsMap.size));
      setTxt("cntProdHasVideo", cntVid);
      setTxt("cntProdReady", cntReady);
      setTxt("cntProdPending", cntPending);
      setTxt("cntProdHot", cntHot);
      setTxt("stFooterStoreProds", cntAll);

      const pendWrap = document.getElementById("badgeProdPendingWrap");
      if (pendWrap) pendWrap.style.display = cntPending > 0 ? "inline-flex" : "none";

      let filtered = prods.filter(p => {
        if (STATE.prodStoreFilter === "has_video" && !(p.final_videos_count > 0)) return false;
        if (STATE.prodStoreFilter === "hot" && !p.is_hot) return false;
        if (STATE.prodStoreFilter === "ready" && !(p.status === "ready" || p.image_count > 0)) return false;
        if (STATE.prodStoreFilter === "pending" && (p.status === "ready" || p.image_count > 0)) return false;
        if (dateFlt !== "all" && (p.date_key || "unknown") !== dateFlt) return false;
        if (q) {
          const hay = `${p.product_id} ${p.title || ''} ${p.seller || ''} ${p.price || ''} ${p.category || ''}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });

      // Sắp xếp danh sách theo tiêu chí đã chọn
      filtered = [...filtered].sort((a, b) => {
        if (sortMode === "video_first") {
          const vd = (b.final_videos_count || 0) - (a.final_videos_count || 0);
          if (vd !== 0) return vd;
          return (b.created_ts || 0) - (a.created_ts || 0);
        }
        if (sortMode === "sold_desc") {
          return _parseNumVal(b.sold_count || b.sold_count_label) - _parseNumVal(a.sold_count || a.sold_count_label);
        }
        if (sortMode === "price_asc") {
          return (_parseNumVal(a.price) || 999999999) - (_parseNumVal(b.price) || 999999999);
        }
        if (sortMode === "price_desc") {
          return _parseNumVal(b.price) - _parseNumVal(a.price);
        }
        if (sortMode === "hot_first") {
          if (Boolean(b.is_hot) !== Boolean(a.is_hot)) return b.is_hot ? 1 : -1;
          return (b.created_ts || 0) - (a.created_ts || 0);
        }
        // Mặc định: date_desc (Theo ngày mới nhất)
        return (b.created_ts || 0) - (a.created_ts || 0);
      });

      STATE._lastFilteredStoreProds = filtered;
      _updateSelectedCounters();

      const chkAll = document.getElementById("chkStoreSelectAll");
      if (chkAll) {
        chkAll.checked = filtered.length > 0 && filtered.every(p => STATE.selectedStorePids.has(String(p.product_id)));
      }

      if (!filtered.length) {
        const emptyHtml = `<div style="color:var(--muted); padding:32px; text-align:center; background:#0b0e15;">Chưa có sản phẩm phù hợp bộ lọc. Bạn có thể dán Link / ID sản phẩm lên thanh phía trên để tải về.</div>`;
        if (tblBody) tblBody.innerHTML = emptyHtml;
        if (gridBox) gridBox.innerHTML = `<div style="grid-column:1/-1;">${emptyHtml}</div>`;
        return;
      }

      // ── 1. RENDER DẠNG BẢNG PHÂN NHÓM NGÀY (CHUẨN PHONG CÁCH ẢNH 2) ──
      if (tblBody) {
        let globalRowIdx = 0;
        const renderSingleRow = (p) => {
          globalRowIdx++;
          const pid = p.product_id;
          const isChecked = STATE.selectedStorePids.has(String(pid));
          const thumb = p.primary_image_path ? `/api/media?path=${encodeURIComponent(p.primary_image_path)}` : "";
          const hasVids = (p.final_videos_count || 0) > 0;
          const tplCode = p.template_code || "001";
          const tplName = p.template_name || "Nhà Xưởng";
          const priceFmt = formatVndPrice(p.price) || "—";
          const soldFmt = formatSoldNumber(p.sold_count_label || p.sold_count);
          const timeLbl = p.time_label || "12:00";
          const webUrl = p.web_url || `https://shop.tiktok.com/vn/pdp/${pid}`;

          return `
            <div class="pstore-row ${isChecked ? 'selected' : ''}" id="pstoreRow_${pid}">
              <!-- Cột 1: Checkbox -->
              <div style="display:flex; align-items:center; justify-content:center;">
                <input type="checkbox" style="width:15px; height:15px; cursor:pointer; accent-color:#3b82f6;"
                       ${isChecked ? 'checked' : ''}
                       onchange="toggleSelectSingleStoreProduct('${pid}', this.checked)" />
              </div>

              <!-- Cột 2: Số thứ tự # -->
              <div style="font-size:12px; font-weight:700; color:#64748b;">${globalRowIdx}</div>

              <!-- Cột 3: Nút đánh dấu HOT 🔥 -->
              <div style="display:flex; justify-content:center;">
                <button class="pstore-hot-btn ${p.is_hot ? 'active' : ''}"
                        onclick="toggleHotProductQuick('${pid}', event)"
                        title="${p.is_hot ? 'Đang đánh dấu HOT (Bấm để bỏ)' : 'Bấm để đánh dấu SP HOT'}">🔥</button>
              </div>

              <!-- Cột 4: Ảnh đại diện (Bấm để mở Xem Full & Zoom Lightbox!) -->
              <div>
                <div style="width:46px; height:46px; border-radius:8px; overflow:hidden; background:#05070c; border:1px solid rgba(255,255,255,0.14); position:relative; cursor:zoom-in;"
                     onclick="openProductGalleryLightbox('${pid}', 0)"
                     title="Bấm vào ảnh để Xem Full Màn Hình & Phóng To (${p.image_count || 0} ảnh)">
                  ${thumb ? `
                    <img src="${thumb}" loading="lazy" style="width:100%; height:100%; object-fit:cover;" />
                  ` : `
                    <div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:#475569; font-size:14px;">📷</div>
                  `}
                  ${(p.image_count || 0) > 1 ? `<span style="position:absolute; bottom:1px; right:1px; background:rgba(0,0,0,0.82); color:#fcd34d; font-size:8.5px; font-weight:800; padding:0 3px; border-radius:3px;">${p.image_count}</span>` : ''}
                </div>
              </div>

              <!-- Cột 5: Sản phẩm & Cửa hàng -->
              <div style="min-width:0; display:flex; flex-direction:column; gap:4px;">
                <div onclick="openProductGalleryModal('${pid}')"
                     title="${(p.title || '').replace(/"/g, '&quot;')} — Bấm để mở Chi Tiết Sản Phẩm & Tạo Video"
                     style="font-size:13.5px; font-weight:800; color:#f8fafc; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer;">
                  ${p.title || `<span style="color:#64748b; font-style:italic;">(Sản phẩm #${pid} — Bấm Tải ảnh & mô tả)</span>`}
                </div>
                <div style="display:flex; align-items:center; gap:10px; font-size:11.5px; color:#94a3b8; flex-wrap:wrap;">
                  <span style="display:inline-flex; align-items:center; gap:4px;">🏪 <b style="color:#cbd5e1; font-weight:600;">${p.seller || 'TikTok Shop'}</b></span>
                  <span style="color:#64748b;">⏰ ${timeLbl}</span>
                  <span style="color:#a78bfa; font-weight:700; font-size:10.5px;">#${tplCode} ${tplName}</span>
                  ${hasVids ? `
                    <span onclick="STATE.currentProjectId='${pid}'; switchTab('dashboard', document.getElementById('navBtn-dashboard')); loadProjectDetail('${pid}', false);"
                          title="Bấm để mở xem ${p.final_videos_count} Video Final trong Studio"
                          style="cursor:pointer; background:rgba(16,185,129,0.18); border:1px solid rgba(16,185,129,0.45); color:#34d399; font-size:10px; font-weight:800; padding:1px 7px; border-radius:999px;">
                      🎬 ${p.final_videos_count} Video Final
                    </span>
                  ` : ''}
                </div>
              </div>

              <!-- Cột 6: Giá & Đã bán -->
              <div style="display:flex; flex-direction:column; gap:3px;">
                <div style="font-size:13.5px; font-weight:800; color:#10b981;">${priceFmt}</div>
                <div style="font-size:12px; font-weight:700; color:#f59e0b; display:flex; align-items:center; gap:3px;">
                  <span>🔥</span> <span>${soldFmt}</span>
                </div>
              </div>

              <!-- Cột 7: ID Sản phẩm (1-click Copy) -->
              <div>
                <span class="pstore-id-pill" onclick="navigator.clipboard.writeText('${pid}'); showProdBanner('📋 Đã copy ID: <b>${pid}</b>');" title="Bấm để copy ID sản phẩm ${pid}">
                  📋 ${pid}
                </span>
              </div>

              <!-- Cột 8: Web (Mở link TikTok Shop + Copy link) -->
              <div style="display:flex; align-items:center; gap:5px;">
                <button onclick="window.open('${webUrl}', '_blank')"
                        title="Mở trang sản phẩm trên TikTok Shop"
                        style="cursor:pointer; display:inline-flex; align-items:center; gap:4px; padding:4px 9px; border-radius:7px; background:rgba(29,78,216,0.2); border:1px solid rgba(59,130,246,0.45); color:#60a5fa; font-size:11.5px; font-weight:700;">
                  🌐 Web
                </button>
                <button onclick="navigator.clipboard.writeText('${webUrl}'); showProdBanner('📋 Đã copy link TikTok Shop của SP ${pid}!');"
                        title="Copy link TikTok Shop"
                        style="cursor:pointer; padding:4px 7px; border-radius:7px; background:#151924; border:1px solid rgba(255,255,255,0.1); color:#cbd5e1; font-size:11.5px;">
                  📋
                </button>
              </div>

              <!-- Cột 9: Tạo Video & Thao tác nhanh -->
              <div style="display:flex; align-items:center; justify-content:flex-end; gap:5px;">
                <button onclick="createVideoForStoreProduct('${pid}', true)"
                        title="Tạo kịch bản theo Template & Chạy đa luồng tạo Video Final 60FPS"
                        style="cursor:pointer; padding:4px 9px; border-radius:7px; background:rgba(16,185,129,0.18); border:1px solid rgba(16,185,129,0.5); color:#34d399; font-size:11.5px; font-weight:800;">
                  🎬 Tạo Video
                </button>
                <button onclick="openProductGalleryModal('${pid}')"
                        title="Mở bảng Chi Tiết Sản Phẩm, Xem Bộ Ảnh & Cấu Hình Video"
                        style="cursor:pointer; padding:4px 8px; border-radius:7px; background:#151924; border:1px solid rgba(255,255,255,0.12); color:#e2e8f0; font-size:11.5px; font-weight:700;">
                  👁️ Chi tiết
                </button>
                <button onclick="openFolderEncoded('${encodeURIComponent(p.crawler_dir || p.project_dir || ('data/tiktok_crawler/data/product_images/' + pid))}')"
                        title="Mở thư mục chứa ảnh / dữ liệu của sản phẩm này trên máy tính"
                        style="cursor:pointer; padding:4px 7px; border-radius:7px; background:rgba(245,158,11,0.14); border:1px solid rgba(245,158,11,0.4); color:#fbbf24; font-size:11.5px; font-weight:700;">
                  📂
                </button>
                <button onclick="copyFullProductSummary('${pid}')"
                        title="Copy Full thông tin sản phẩm này"
                        style="cursor:pointer; padding:4px 7px; border-radius:7px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.35); color:#34d399; font-size:11.5px; font-weight:700;">
                  📋
                </button>
              </div>
            </div>
          `;
        };

        // Nếu đang sắp xếp theo ngày (date_desc), hiển thị dòng tiêu đề nhóm Ngày giống hệt Ảnh 2!
        if (sortMode === "date_desc") {
          const groups = [];
          const gMap = new Map();
          filtered.forEach(p => {
            const dk = p.date_key || "unknown";
            if (!gMap.has(dk)) {
              const gObj = { key: dk, label: p.date_label || "Ngày khác", items: [] };
              gMap.set(dk, gObj);
              groups.push(gObj);
            }
            gMap.get(dk).items.push(p);
          });

          tblBody.innerHTML = groups.map(g => {
            const isToday = g.label === "Hôm nay";
            const badgeBg = isToday ? "rgba(16, 185, 129, 0.16)" : "rgba(99, 102, 241, 0.16)";
            const badgeBorder = isToday ? "rgba(16, 185, 129, 0.4)" : "rgba(99, 102, 241, 0.4)";
            const badgeColor = isToday ? "#34d399" : "#818cf8";
            const allGroupChecked = g.items.every(x => STATE.selectedStorePids.has(String(x.product_id)));

            return `
              <div class="pstore-group-row">
                <div style="display:flex; align-items:center; gap:10px;">
                  <input type="checkbox" style="width:15px; height:15px; cursor:pointer; accent-color:#10b981;"
                         ${allGroupChecked ? 'checked' : ''}
                         onchange="toggleSelectGroupStoreProducts('${g.key}', this.checked)"
                         title="Chọn tất cả sản phẩm trong ngày ${g.label}" />
                  <span style="display:inline-flex; align-items:center; gap:6px; padding:4px 12px; border-radius:999px; background:${badgeBg}; border:1px solid ${badgeBorder}; color:${badgeColor}; font-size:12px; font-weight:800;">
                    📅 ${g.label}
                  </span>
                  <span style="font-size:12px; color:#64748b; font-weight:600;">(${g.items.length} sản phẩm)</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                  <button onclick="copyStoreGroupIds('${g.key}')"
                          style="cursor:pointer; display:inline-flex; align-items:center; gap:5px; padding:4px 11px; border-radius:8px; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.38); color:#34d399; font-size:11.5px; font-weight:700;">
                    📋 Copy ID nhóm (${g.items.length})
                  </button>
                </div>
              </div>
              ${g.items.map(p => renderSingleRow(p)).join("")}
            `;
          }).join("");
        } else {
          tblBody.innerHTML = filtered.map(p => renderSingleRow(p)).join("");
        }
      }

      // ── 2. RENDER DẠNG LƯỚI THẺ (KHI CHUYỂN SANG DẠNG THẺ GRID) ──
      if (gridBox && STATE.prodStoreViewMode === "grid") {
        gridBox.innerHTML = filtered.map(p => {
          const pid = p.product_id;
          const thumb = p.primary_image_path ? `/api/media?path=${encodeURIComponent(p.primary_image_path)}` : "";
          const hasVids = (p.final_videos_count || 0) > 0;
          const isReady = p.status === "ready" || (p.image_count || 0) > 0;
          const tplCode = p.template_code || "001";
          const tplName = p.template_name || "Nhà Xưởng";
          const priceFmt = formatVndPrice(p.price);
          const origPriceFmt = p.original_price ? formatVndPrice(p.original_price) : "";
          const soldFmt = formatSoldNumber(p.sold_count_label || p.sold_count);

          let statusBadge = `<span class="badge badge-wait" style="font-size:10px;">⏳ Chưa crawl</span>`;
          if (hasVids) statusBadge = `<span class="badge badge-done" style="font-size:10px; background:rgba(16,185,129,0.2); color:#34d399; border:1px solid rgba(16,185,129,0.45);">🎬 ${p.final_videos_count} Video Final</span>`;
          else if (isReady) statusBadge = `<span class="badge badge-run" style="font-size:10px; background:rgba(59,130,246,0.18); color:#60a5fa; border:1px solid rgba(59,130,246,0.4);">🖼️ ${p.image_count} ảnh SP</span>`;

          return `
            <div class="variant-card ${hasVids ? 'done-card' : ''}" style="padding:12px; gap:10px; border-radius:12px; background:linear-gradient(165deg, #111827 0%, #0b0f19 100%); border:1px solid ${hasVids ? 'rgba(16,185,129,0.45)' : (isReady ? 'rgba(59,130,246,0.26)' : 'rgba(255,255,255,0.08)')}; box-shadow:0 6px 18px rgba(0,0,0,0.32); transition:all 0.18s ease;">
              <div style="display:flex; gap:12px; align-items:start;">
                <div style="width:88px; height:88px; border-radius:10px; overflow:hidden; background:#05070c; border:1px solid rgba(255,255,255,0.12); flex-shrink:0; position:relative; cursor:zoom-in;" onclick="openProductGalleryLightbox('${pid}', 0)" title="Bấm vào ảnh để Xem Full Màn Hình & Phóng To">
                  ${thumb ? `<img src="${thumb}" loading="lazy" style="width:100%; height:100%; object-fit:cover; transition:transform 0.2s;" onmouseover="this.style.transform='scale(1.06)'" onmouseout="this.style.transform='scale(1)'" />` : `<div style="width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; color:var(--muted); font-size:10px; text-align:center; padding:4px;"><span>📷</span><span>Chưa có ảnh</span></div>`}
                  <span style="position:absolute; bottom:4px; right:4px; background:rgba(0,0,0,0.84); color:#fcd34d; font-size:9.5px; font-weight:800; padding:1.5px 5px; border-radius:4px; border:1px solid rgba(252,211,77,0.3);">${p.image_count || 0} ảnh</span>
                  ${p.is_hot ? `<span style="position:absolute; top:4px; left:4px; background:rgba(239,68,68,0.92); color:#fff; font-size:9px; font-weight:800; padding:1px 4px; border-radius:4px;">🔥 HOT</span>` : ''}
                </div>

                <div style="flex:1; min-width:0; display:flex; flex-direction:column; gap:4px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; gap:4px;">
                    <span class="proj-id-tag" style="cursor:pointer; font-size:10.5px; padding:2px 6px;" onclick="navigator.clipboard.writeText('${pid}'); showProdBanner('📋 Đã copy ID: ${pid}');" title="Bấm để copy ID">ID: ${pid}</span>
                    ${statusBadge}
                  </div>
                  <div style="font-size:12.5px; font-weight:700; color:#f8fafc; line-height:1.38; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; cursor:pointer;" onclick="openProductGalleryModal('${pid}')" title="${(p.title || '').replace(/"/g, '&quot;')}">
                    ${p.title || `<span style="color:var(--muted); font-style:italic;">(Chưa tải tiêu đề — Bấm Crawl Cách 1 hoặc 2)</span>`}
                  </div>
                  <div style="margin-top:2px; display:flex; flex-wrap:wrap; gap:8px; align-items:baseline;">
                    ${priceFmt ? `<span style="font-size:13.5px; font-weight:800; color:#10b981;">💰 ${priceFmt}</span>` : ''}
                    ${origPriceFmt && origPriceFmt !== priceFmt ? `<span style="font-size:10.5px; color:#64748b; text-decoration:line-through;">${origPriceFmt}</span>` : ''}
                    ${(p.sold_count || p.sold_count_label) ? `<span style="font-size:11px; font-weight:700; color:#f59e0b;">🔥 Đã bán: ${soldFmt}</span>` : ''}
                  </div>
                  <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; font-size:10.5px; color:#94a3b8;">
                    <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">🏪 ${p.seller || 'TikTok Shop'}</span>
                    <span style="color:#c4b5fd; font-weight:700; flex-shrink:0;">#${tplCode} ${tplName}</span>
                  </div>
                </div>
              </div>

              <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.07); flex-wrap:wrap;">
                <div style="display:flex; gap:5px; flex-wrap:wrap;">
                  <button class="btn btn-xs btn-success" style="font-weight:700; padding:4px 8px;" onclick="createVideoForStoreProduct('${pid}', true)" title="Tạo kịch bản theo Template đang chọn & Chạy đa luồng tạo Video Final">🎬 Tạo Video</button>
                  <button class="btn btn-xs btn-outline" style="border-color:rgba(139,92,246,0.45); color:#ddd6fe; padding:4px 8px;" onclick="openProductGalleryModal('${pid}')" title="Xem Chi Tiết Sản Phẩm, Bộ Ảnh & Trung Tâm Tạo Video AI">👁️ Chi Tiết & Tạo Video</button>
                  ${p.has_project ? `<button class="btn btn-xs btn-primary" style="padding:4px 7px;" onclick="STATE.currentProjectId='${pid}'; switchTab('dashboard', document.querySelector('.nav-btn')); loadProjectDetail('${pid}', false);" title="Mở trong Studio Dự Án">📊 Studio</button>` : ''}
                </div>
                <div style="display:flex; gap:4px;">
                  <button class="btn btn-xs btn-primary" onclick="crawlSingleStoreProduct('${pid}', 'auto')" title="Crawl lại bằng Cách 1 (SPAI Auto -> Cách 2)">⚡ C1</button>
                  <button class="btn btn-xs btn-amber" onclick="crawlSingleStoreProduct('${pid}', 'browser')" title="Crawl bằng Cách 2 (Trình duyệt TikTokShop + Captcha BoxPhone)">🌐 C2</button>
                  ${(p.crawler_dir || p.project_dir) ? `<button class="btn btn-xs btn-outline" onclick="openFolderEncoded('${encodeURIComponent(p.crawler_dir || p.project_dir)}')" title="Mở thư mục sản phẩm trên máy tính">📂</button>` : ''}
                  <button class="btn btn-xs btn-danger" onclick="deleteStoreProduct('${pid}')" title="Xoá khỏi danh sách">🗑️</button>
                </div>
              </div>
            </div>
          `;
        }).join("");
      }
    }

    async function quickCrawlProduct(method = "auto") {
      const inp = document.getElementById("inpQuickProdUrl").value.trim();
      if (!inp) return alert("Vui lòng dán Link sản phẩm TikTok hoặc ID sản phẩm!");
      showProdBanner(`⏳ Đang tải thông tin & bộ ảnh sản phẩm (${method === 'browser' ? 'Cách 2: Browser TikTokShop + Captcha' : 'Cách 1: SPAI Auto -> Cách 2'})...`);
      const res = await apiPost("/api/products-store/add", {
        input: inp,
        method: method,
        force: true,
      });
      if (!res || !res.ok) {
        showProdBanner(`❌ Lỗi tải sản phẩm: ${(res && res.error) || 'Không xác định'}`, true);
        return;
      }
      showProdBanner(`✅ Đã tải thành công sản phẩm <b>${res.pid}</b> (${(res.info && (res.info.name || res.info.title)) || ''}) — ${res.images?.length || 0} ảnh!`);
      await loadProductsStore(false);
      await refreshAll(true);
    }

    async function quickCreateVideoFromInput() {
      const inp = document.getElementById("inpQuickProdUrl").value.trim();
      if (!inp) return alert("Vui lòng dán Link sản phẩm TikTok hoặc ID sản phẩm!");
      const tpl = document.getElementById("selQuickTemplate")?.value || "Nhà Xưởng";
      const vpc = document.getElementById("selQuickVideosPerChar")?.value || "";
      showProdBanner(`🚀 Đang kiểm tra / tự động Crawl sản phẩm và khởi tạo kịch bản theo Template <b>${tpl}</b>...`);
      const res = await apiPost("/api/products-store/create-video", {
        input: inp,
        template_name: tpl,
        method: "auto",
        videos_per_character: vpc ? parseInt(vpc, 10) : null,
        force_regenerate_prompts: true,
        auto_run: true,
      });
      if (!res || !res.ok) {
        showProdBanner(`❌ Lỗi: ${(res && res.error) || 'Không thể khởi tạo video'}`, true);
        return;
      }
      showProdBanner(`🎉 Đã chuẩn bị xong <b>${res.videos_count} kịch bản (${res.template_name})</b> cho SP <b>${res.pid}</b> (${res.product_name}) và kích hoạt chạy đa luồng!`);
      await loadProductsStore(false);
      await refreshAll(false);
      STATE.currentProjectId = res.pid;
      loadProjectDetail(res.pid, false);
    }

    async function submitBatchProducts(method = "auto") {
      const txt = document.getElementById("inpBulkProdUrls").value.trim();
      if (!txt) return alert("Vui lòng dán ít nhất 1 Link hoặc ID sản phẩm!");
      showProdBanner(`⏳ Đang giải mã danh sách Link/ID và tải ngầm thông tin sản phẩm (${method})...`);
      const res = await apiPost("/api/products-store/batch-add", {
        text: txt,
        method: method,
        auto_fetch: true,
      });
      if (res && res.ok) {
        document.getElementById("inpBulkProdUrls").value = "";
        showProdBanner(`✅ Đã thêm <b>${res.added_count}</b> sản phẩm vào hàng đợi tải tự động!`);
        await loadProductsStore(false);
      }
    }

    async function batchFetchMissingProducts(method = "auto") {
      showProdBanner(`⏳ Đang crawl toàn bộ sản phẩm chưa đủ thông tin bằng ${method === 'browser' ? 'Cách 2 (Browser + Captcha)' : 'Cách 1 (SPAI Auto -> Cách 2)'}...`);
      const res = await apiPost("/api/products-store/fetch-details", {
        product_id: "",
        method: method,
        force: false,
      });
      if (res && res.ok) {
        showProdBanner(`✅ Hoàn tất tải chi tiết: thành công <b>${res.fetched}/${res.total_checked}</b> sản phẩm.`);
        await loadProductsStore(false);
        await refreshAll(true);
      }
    }

    async function crawlSingleStoreProduct(pid, method = "auto") {
      showProdBanner(`⏳ Đang tải thông tin & ảnh cho SP <b>${pid}</b> (${method === 'browser' ? 'Cách 2 Browser' : 'Cách 1 Auto'})...`);
      const res = await apiPost("/api/products-store/fetch-details", {
        product_id: pid,
        method: method,
        force: true,
      });
      if (!res || !res.ok) {
        showProdBanner(`❌ Lỗi tải SP ${pid}: ${(res && res.error) || 'Thất bại'}`, true);
        return;
      }
      showProdBanner(`✅ Đã cập nhật SP <b>${pid}</b> (${res.images?.length || 0} ảnh).`);
      await loadProductsStore(false);
      await refreshAll(true);
    }

    async function createVideoForStoreProduct(pid, autoRun = true) {
      const tpl = document.getElementById("selQuickTemplate")?.value || "Nhà Xưởng";
      const vpc = document.getElementById("selQuickVideosPerChar")?.value || "";
      showProdBanner(`🎬 Đang tạo kịch bản Template <b>${tpl}</b> và chạy đa luồng cho SP <b>${pid}</b>...`);
      const res = await apiPost("/api/products-store/create-video", {
        input: pid,
        template_name: tpl,
        method: "auto",
        videos_per_character: vpc ? parseInt(vpc, 10) : null,
        force_regenerate_prompts: true,
        auto_run: autoRun,
      });
      if (!res || !res.ok) {
        showProdBanner(`❌ Lỗi tạo video SP ${pid}: ${(res && res.error) || ''}`, true);
        return;
      }
      showProdBanner(`🎉 Đã khởi chạy tạo <b>${res.videos_count} Video Final</b> (Template: <b>${res.template_name}</b>) cho SP <b>${pid}</b>!`);
      await loadProductsStore(false);
      await refreshAll(false);
      STATE.currentProjectId = pid;
      switchTab("dashboard", document.querySelector(".nav-btn"));
      loadProjectDetail(pid, false);
    }

    async function deleteStoreProduct(pid) {
      if (!confirm(`Xoá sản phẩm ${pid} khỏi danh sách nghiên cứu?`)) return;
      await apiPost("/api/products-store/delete", { product_id: pid, delete_project: false });
      await loadProductsStore(false);
    }

    function openProductGalleryModal(pid, activeIdx = 0) {
      const p = (STATE.productsStore || []).find(x => x.product_id === pid);
      if (!p) return;
      STATE.currentPgPid = pid;
      const imgs = p.local_images || [];
      const remoteImgs = p.remote_images || [];
      const curPrimary = (p.primary_product_refs && p.primary_product_refs[0]) || (imgs[0] ? imgs[0].split(/[\\/]/).pop() : "prod_1.jpg");

      let selIdx = activeIdx;
      if (selIdx < 0 || selIdx >= Math.max(1, imgs.length)) selIdx = 0;
      STATE.currentPgImgIdx = selIdx;

      const curAbsPath = imgs[selIdx] || p.primary_image_path || "";
      const curBname = curAbsPath ? curAbsPath.split(/[\\/]/).pop() : "";
      const isCurPrimary = curBname && curBname === curPrimary;

      const priceFmt = formatVndPrice(p.price) || "—";
      const origPriceFmt = p.original_price ? formatVndPrice(p.original_price) : "";
      const soldFmt = formatSoldNumber(p.sold_count_label || p.sold_count || "0");
      const shopName = p.seller || "TikTok Shop VN";
      const categoryLabel = p.category || "Chưa phân loại";
      const statusLabel = p.status_label || (parseInt(String(p.sold_count || "0").replace(/[^\d]/g, ""), 10) >= 50000 ? "Đã bán quá 50,000 đơn (bão hòa)" : "Đang kinh doanh tốt");
      const folderPath = p.crawler_dir || p.project_dir || "";
      const folderFiles = p.folder_files || [];
      const variations = (p.variations && p.variations.length) ? p.variations : ["Mặc định"];

      const thumbsHtml = imgs.map((absPath, idx) => {
        const bname = absPath.split(/[\\/]/).pop();
        const isPri = (bname === curPrimary);
        const isSel = (idx === selIdx);
        return `
          <div onclick="switchPgGalleryImage('${pid}', ${idx})" style="width:56px; height:56px; border-radius:8px; overflow:hidden; flex-shrink:0; cursor:pointer; position:relative; border:2px solid ${isSel ? '#10b981' : (isPri ? '#f59e0b' : 'rgba(255,255,255,0.14)')}; background:#000; opacity:${isSel ? '1' : '0.78'}; transition:all 0.15s;" title="${bname}${isPri ? ' (⭐ Ảnh Mẫu AI)' : ''}">
            <img src="/api/media?path=${encodeURIComponent(absPath)}" style="width:100%; height:100%; object-fit:cover;" />
            ${isPri ? `<span style="position:absolute; top:2px; right:2px; background:#f59e0b; color:#000; font-size:8px; font-weight:900; padding:0 3px; border-radius:3px;">⭐</span>` : ''}
          </div>
        `;
      }).join("");

      const folderFilesHtml = folderFiles.map(f => {
        const icon = f.is_dir ? "📁" : (f.name.endsWith(".json") ? "📄" : "🖼️");
        const sizeTxt = (!f.is_dir && f.size_kb) ? ` (${f.size_kb} KB)` : "";
        return `
          <span onclick="openFolderEncoded('${encodeURIComponent(f.path)}')" style="cursor:pointer; display:inline-flex; align-items:center; gap:5px; padding:4px 9px; border-radius:6px; background:#161b26; border:1px solid rgba(255,255,255,0.1); font-size:11px; color:#cbd5e1;" title="Bấm để mở ${f.name}">
            ${icon} <span>${f.name}${sizeTxt}</span>
          </span>
        `;
      }).join("");

      const variationsHtml = variations.map(v => `
        <span style="display:inline-flex; align-items:center; gap:4px; padding:4px 10px; border-radius:999px; background:#161b26; border:1px solid rgba(255,255,255,0.12); font-size:11.5px; color:#cbd5e1;">
          Thông số: <b style="color:#fff;">${v}</b>
        </span>
      `).join("");

      const tplOptions = (STATE.videoTemplates || []).map(t =>
        `<option value="${t.code || t.folder_name}" ${(t.folder_name === p.template_name || t.code === p.template_code) ? 'selected' : ''}>[Mã #${t.code || '001'}] ${t.folder_name} — ${t.name}</option>`
      ).join("") || `<option value="001">[Mã #001] Nhà Xưởng</option>`;

      document.getElementById("pgModalBody").innerHTML = `
        <div style="background:#0f1218; color:#f8fafc; padding:18px 22px; border-radius:16px; position:relative;">
          <!-- TOP BADGES BAR (Giống Ảnh 2) -->
          <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px;">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <span style="display:inline-flex; align-items:center; gap:5px; padding:4px 11px; border-radius:999px; background:rgba(16,185,129,0.14); border:1px solid rgba(16,185,129,0.35); color:#34d399; font-size:11.5px; font-weight:700;">
                🏪 ${shopName}
              </span>
              <span style="display:inline-flex; align-items:center; gap:5px; padding:4px 11px; border-radius:999px; background:rgba(245,158,11,0.14); border:1px solid rgba(245,158,11,0.35); color:#fbbf24; font-size:11.5px; font-weight:600;">
                🏷️ ${categoryLabel}
              </span>
              <span style="display:inline-flex; align-items:center; gap:5px; padding:4px 11px; border-radius:999px; background:#181c26; border:1px solid rgba(255,255,255,0.12); color:#94a3b8; font-size:11.5px;">
                ${statusLabel}
              </span>
              <button onclick="toggleHotProduct('${pid}')" style="cursor:pointer; display:inline-flex; align-items:center; gap:5px; padding:4px 11px; border-radius:999px; background:${p.is_hot ? 'rgba(239,68,68,0.25)' : '#181c26'}; border:1px solid ${p.is_hot ? '#ef4444' : 'rgba(255,255,255,0.14)'}; color:${p.is_hot ? '#fca5a5' : '#e2e8f0'}; font-size:11.5px; font-weight:700;">
                🔥 ${p.is_hot ? 'Đã đánh dấu HOT' : 'Đánh dấu HOT'}
              </button>
              <button onclick="copyFullProductSummary('${pid}')" style="cursor:pointer; display:inline-flex; align-items:center; gap:5px; padding:4px 12px; border-radius:999px; background:#10b981; border:none; color:#052e16; font-size:11.5px; font-weight:800;">
                📋 Copy Full thông tin SP
              </button>
            </div>
            <button onclick="closeModal('modalProductGallery')" style="width:32px; height:32px; border-radius:8px; background:#181c26; border:1px solid rgba(255,255,255,0.12); color:#cbd5e1; font-size:16px; cursor:pointer; display:flex; align-items:center; justify-content:center;">✕</button>
          </div>

          <!-- PRODUCT TITLE -->
          <div style="font-size:17px; font-weight:800; color:#ffffff; line-height:1.4; margin-bottom:16px;">
            ${p.title || `(Sản phẩm ID ${pid} — Bấm Tải lại Auto 1→2 hoặc Cách 2 để lấy đầy đủ thông tin)`}
          </div>

          <!-- 2 COLUMNS LAYOUT -->
          <div style="display:grid; grid-template-columns: 350px 1fr; gap:20px; align-items:start;">
            <!-- LEFT COLUMN: GALLERY + ACTION PILLS + LOCAL FOLDER -->
            <div style="display:flex; flex-direction:column; gap:10px;">
              <!-- MAIN 1:1 IMAGE -->
              <div style="width:100%; aspect-ratio:1/1; border-radius:14px; overflow:hidden; background:#05070c; border:1px solid rgba(255,255,255,0.14); position:relative;">
                ${curAbsPath ? `
                  <img id="pgMainImgEl" src="/api/media?path=${encodeURIComponent(curAbsPath)}" style="width:100%; height:100%; object-fit:contain; cursor:zoom-in;" onclick="openProductGalleryLightbox('${pid}', ${selIdx})" title="Bấm vào ảnh để Xem Full Màn Hình & Phóng To / Thu Nhỏ" />
                  <button class="btn btn-xs btn-amber" style="position:absolute; bottom:10px; left:10px; font-weight:800; box-shadow:0 4px 12px rgba(0,0,0,0.6);" onclick="openProductGalleryLightbox('${pid}', ${selIdx})">🔍 Xem Full & Zoom</button>
                ` : `
                  <div style="width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; color:var(--muted); gap:8px;">
                    <span style="font-size:32px;">📷</span>
                    <span>Chưa có ảnh sản phẩm</span>
                  </div>
                `}
                <span id="pgMainImgCounter" style="position:absolute; bottom:10px; right:10px; background:rgba(0,0,0,0.78); color:#fff; font-size:12px; font-weight:800; padding:3px 9px; border-radius:8px; border:1px solid rgba(255,255,255,0.18);">
                  ${imgs.length ? `${selIdx + 1}/${imgs.length}` : '0/0'}
                </span>
                ${isCurPrimary ? `
                  <span style="position:absolute; top:10px; left:10px; background:rgba(245,158,11,0.95); color:#000; font-size:11px; font-weight:900; padding:3px 9px; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.4);">
                    ⭐ ẢNH MẪU AI ĐANG CHỌN
                  </span>
                ` : ''}
              </div>

              <!-- THUMBNAIL STRIP -->
              <div style="display:flex; gap:7px; overflow-x:auto; padding-bottom:4px;">
                ${thumbsHtml}
              </div>

              <!-- IMAGE & CRAWL ACTION PILLS -->
              <div style="display:flex; flex-wrap:wrap; gap:6px;">
                ${curAbsPath ? `<button class="btn btn-xs btn-amber" style="padding:5px 10px; font-weight:800;" onclick="openProductGalleryLightbox('${pid}', ${selIdx})">🔍 Phóng to / Xem tất cả ảnh (${imgs.length})</button>` : ''}
                ${curAbsPath ? `<button class="btn btn-xs btn-outline" style="background:#161b26; border-color:rgba(255,255,255,0.14); color:#e2e8f0; padding:5px 10px;" onclick="window.open('/api/media?path=${encodeURIComponent(curAbsPath)}', '_blank')">🔗 Mở tab mới</button>` : ''}
                <button class="btn btn-xs btn-outline" style="background:#161b26; border-color:rgba(255,255,255,0.14); color:#e2e8f0; padding:5px 10px;" onclick="copyProductImageLinks('${pid}')">📋 Copy link ảnh (${remoteImgs.length || imgs.length})</button>
                ${curBname ? `<button class="btn btn-xs ${isCurPrimary ? 'btn-amber' : 'btn-outline'}" style="padding:5px 10px;" onclick="setProductPrimaryRefImage('${pid}', '${curBname}')">⭐ ${isCurPrimary ? 'Đang Là Mẫu AI' : 'Chọn Ảnh Này Làm Mẫu AI'}</button>` : ''}
                ${folderPath ? `<button class="btn btn-xs btn-outline" style="background:#161b26; border-color:rgba(255,255,255,0.14); color:#e2e8f0; padding:5px 10px;" onclick="openFolderEncoded('${encodeURIComponent(folderPath)}')">📂 Mở thư mục máy tính</button>` : ''}
                <button class="btn btn-xs btn-outline" style="background:#161b26; border-color:rgba(59,130,246,0.4); color:#93c5fd; padding:5px 10px;" onclick="crawlSingleStoreProduct('${pid}', 'auto')">🔄 Tải lại (Auto 1→2)</button>
                <button class="btn btn-xs btn-outline" style="background:rgba(37,99,235,0.16); border-color:rgba(59,130,246,0.5); color:#60a5fa; padding:5px 10px;" onclick="crawlSingleStoreProduct('${pid}', 'browser')">🌐 Tải bằng Trình duyệt (Cách 2)</button>
              </div>

              <!-- LOCAL FOLDER CARD (Giống Ảnh 2) -->
              <div style="background:#121621; border:1px solid rgba(255,255,255,0.09); border-radius:12px; padding:12px; display:flex; flex-direction:column; gap:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap;">
                  <div style="font-size:12px; font-weight:800; color:#e2e8f0; display:flex; align-items:center; gap:6px;">
                    📁 Thư mục Sản phẩm trên máy tính
                  </div>
                  <div style="display:flex; gap:6px;">
                    <button class="btn btn-xs btn-outline" style="background:#1a2030; font-size:10.5px; padding:4px 8px;" onclick="navigator.clipboard.writeText('${folderPath.replace(/\\/g, '\\\\')}'); showProdBanner('📋 Đã copy đường dẫn thư mục!');">📋 Copy Path</button>
                    ${folderPath ? `<button class="btn btn-xs" style="background:linear-gradient(135deg, #f43f5e, #e11d48); color:#fff; border:none; font-size:10.5px; font-weight:800; padding:4px 9px;" onclick="openFolderEncoded('${encodeURIComponent(folderPath)}')">📂 Bật File Explorer</button>` : ''}
                  </div>
                </div>
                <div style="background:#090c12; border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:8px 10px; font-family:Consolas, monospace; font-size:11px; color:#94a3b8; word-break:break-all; line-height:1.4;">
                  ${folderPath || 'Chưa tạo thư mục'}
                </div>
                <div style="font-size:11px; color:#64748b;">Các tệp tin trong thư mục:</div>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                  ${folderFilesHtml || '<span style="font-size:11px; color:var(--muted);">Chưa có tệp tin</span>'}
                </div>
              </div>
            </div>

            <!-- RIGHT COLUMN: KPI CARDS + ID + PDP LINK + VARIATIONS + AI VIDEO CREATION HUB -->
            <div style="display:flex; flex-direction:column; gap:14px;">
              <!-- 3 KPI CARDS -->
              <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px;">
                <div style="background:#141822; border:1px solid rgba(255,255,255,0.09); border-radius:12px; padding:12px 14px;">
                  <div style="font-size:11px; font-weight:700; color:#94a3b8; margin-bottom:4px;">💰 GIÁ BÁN</div>
                  <div style="font-size:21px; font-weight:900; color:#10b981;">${priceFmt}</div>
                  <div style="font-size:11.5px; color:#64748b; text-decoration:line-through; min-height:16px;">${(origPriceFmt && origPriceFmt !== priceFmt) ? origPriceFmt : ''}</div>
                </div>

                <div style="background:#141822; border:1px solid rgba(255,255,255,0.09); border-radius:12px; padding:12px 14px;">
                  <div style="font-size:11px; font-weight:700; color:#94a3b8; margin-bottom:4px;">🔥 ĐÃ BÁN</div>
                  <div style="font-size:21px; font-weight:900; color:#ffffff;">${soldFmt}</div>
                  <div style="font-size:11px; color:#64748b;">Đơn hàng TikTok Shop</div>
                </div>

                <div style="background:#141822; border:1px solid rgba(255,255,255,0.09); border-radius:12px; padding:12px 14px;">
                  <div style="font-size:11px; font-weight:700; color:#94a3b8; margin-bottom:4px;">🎬 VIDEO AI / TỈ LỆ 7 NGÀY</div>
                  <div style="font-size:19px; font-weight:900; color:${(p.final_videos_count || 0) > 0 ? '#34d399' : '#e2e8f0'};">
                    ${(p.final_videos_count || 0) > 0 ? `${p.final_videos_count} Video 60fps` : (p.ratio_label || '—')}
                  </div>
                  <div style="font-size:11px; color:#64748b;">${p.videos_count ? `Đã có ${p.videos_count} kịch bản` : 'Đơn vs Creator / AI Studio'}</div>
                </div>
              </div>

              <!-- ID SẢN PHẨM -->
              <div>
                <div style="font-size:11px; font-weight:800; color:#94a3b8; letter-spacing:0.4px; margin-bottom:5px;">ID SẢN PHẨM</div>
                <div style="display:flex; gap:8px;">
                  <input type="text" readonly value="${pid}" style="flex:1; background:#0b0e15; border:1px solid rgba(255,255,255,0.12); color:#f8fafc; font-weight:800; font-size:13.5px; padding:9px 12px; border-radius:9px;" />
                  <button class="btn btn-outline" style="background:#161b26; border-color:rgba(255,255,255,0.14); padding:0 16px; font-weight:700;" onclick="navigator.clipboard.writeText('${pid}'); showProdBanner('📋 Đã copy ID: ${pid}');">📋 Copy</button>
                </div>
              </div>

              <!-- LINK TIKTOK SHOP PDP (WEB DESKTOP) -->
              <div>
                <div style="font-size:11px; font-weight:800; color:#94a3b8; letter-spacing:0.4px; margin-bottom:5px;">LINK TIKTOK SHOP PDP (WEB DESKTOP)</div>
                <div style="display:flex; gap:8px;">
                  <input type="text" readonly value="${p.web_url || `https://shop.tiktok.com/vn/pdp/${pid}`}" style="flex:1; background:#0b0e15; border:1px solid rgba(255,255,255,0.12); color:#cbd5e1; font-size:12.5px; padding:9px 12px; border-radius:9px;" />
                  <button class="btn" style="background:linear-gradient(135deg, #f43f5e, #e11d48); color:#fff; border:none; padding:0 16px; font-weight:800; border-radius:9px;" onclick="window.open('${p.web_url || `https://shop.tiktok.com/vn/pdp/${pid}`}', '_blank')">🌐 Mở Web</button>
                  <button class="btn btn-outline" style="background:#161b26; border-color:rgba(255,255,255,0.14); padding:0 12px;" onclick="navigator.clipboard.writeText('${p.web_url || `https://shop.tiktok.com/vn/pdp/${pid}`}'); showProdBanner('📋 Đã copy Link PDP!');">📋</button>
                </div>
              </div>

              <!-- PHÂN LOẠI HÀNG -->
              <div>
                <div style="font-size:11px; font-weight:800; color:#94a3b8; letter-spacing:0.4px; margin-bottom:6px;">PHÂN LOẠI HÀNG</div>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                  ${variationsHtml}
                </div>
              </div>

              <!-- MÔ TẢ SẢN PHẨM CHI TIẾT -->
              <div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                  <span style="font-size:11px; font-weight:800; color:#94a3b8; letter-spacing:0.4px;">📝 MÔ TẢ SẢN PHẨM & ĐẶC ĐIỂM CRAWL VỀ</span>
                  <span style="font-size:10.5px; color:#64748b;">Nguồn: ${p.crawl_source || 'TikTok Shop PDP'}</span>
                </div>
                <textarea rows="3" readonly style="width:100%; background:#0b0e15; border:1px solid rgba(255,255,255,0.1); border-radius:9px; padding:8px 11px; font-size:11.5px; color:#cbd5e1; line-height:1.45;">${p.description || '(Chưa có mô tả chi tiết — Hãy bấm Tải lại Auto 1→2 hoặc Cách 2)'}</textarea>
              </div>

              <!-- TRUNG TÂM TẠO VIDEO AI RIÊNG BIỆT CỦA TOOL (SKILL VIDEO VEO) -->
              <div style="background:linear-gradient(145deg, rgba(16,185,129,0.10), rgba(139,92,246,0.12)); border:1px solid rgba(16,185,129,0.4); border-radius:14px; padding:14px 16px; display:flex; flex-direction:column; gap:10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
                  <div style="font-size:13px; font-weight:900; color:#34d399; display:flex; align-items:center; gap:6px;">
                    🎬 TRUNG TÂM TẠO VIDEO AI RIÊNG BIỆT (SKILL VIDEO VEO — 60 FPS + SUBTITLE)
                  </div>
                  <span style="font-size:11px; color:#fcd34d; font-weight:700;">⭐ Ảnh mẫu AI: ${curPrimary}</span>
                </div>

                <div style="display:grid; grid-template-columns: 1.5fr 1fr; gap:10px;">
                  <div>
                    <label style="font-size:11px; color:#cbd5e1; margin-bottom:4px; display:block;">🏪 Chọn Mã Template & Role Skill Video</label>
                    <select id="selModalProdTpl" style="width:100%; background:#090d16; border:1px solid rgba(255,255,255,0.18); color:#fff; font-weight:700; padding:8px 10px; border-radius:8px;">
                      ${tplOptions}
                    </select>
                  </div>
                  <div>
                    <label style="font-size:11px; color:#cbd5e1; margin-bottom:4px; display:block;">🎞️ Số Lượng Video / Nhân Vật</label>
                    <select id="selModalProdVpc" style="width:100%; background:#090d16; border:1px solid rgba(255,255,255,0.18); color:#fff; font-weight:700; padding:8px 10px; border-radius:8px;">
                      <option value="1" ${p.videos_per_character === 1 ? 'selected' : ''}>1 Video / Nhân vật</option>
                      <option value="2" ${p.videos_per_character === 2 ? 'selected' : ''}>2 Video / Nhân vật</option>
                      <option value="3" ${(!p.videos_per_character || p.videos_per_character === 3) ? 'selected' : ''}>3 Video / Nhân vật (6 Video)</option>
                      <option value="4" ${p.videos_per_character === 4 ? 'selected' : ''}>4 Video / Nhân vật</option>
                      <option value="5" ${p.videos_per_character === 5 ? 'selected' : ''}>5 Video / Nhân vật</option>
                    </select>
                  </div>
                </div>

                <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:2px;">
                  <button class="btn btn-success" style="flex:1.4; min-width:220px; padding:10px 14px; font-size:13px; font-weight:800;" onclick="createVideoFromGalleryModal('${pid}', true)">
                    🚀 Tạo Video Ngay Với Template Đang Chọn
                  </button>
                  <button class="btn btn-primary" style="flex:1; min-width:170px; padding:10px 12px; font-size:12.5px; font-weight:700;" onclick="createVideoFromGalleryModal('${pid}', false)">
                    📝 Chỉ Sinh Kịch Bản (prompts.json)
                  </button>
                </div>

                <div style="display:flex; flex-wrap:wrap; gap:8px;">
                  <button class="btn btn-xs btn-amber" style="padding:6px 11px; font-weight:700;" onclick="copyAgentCommandFromGalleryModal('${pid}')">
                    🤖 Copy Lệnh Gửi AI Agent (Theo Mã Template)
                  </button>
                  <button class="btn btn-xs btn-outline" style="border-color:rgba(245,158,11,0.45); color:#fde68a; padding:6px 11px;" onclick="closeModal('modalProductGallery'); switchTab('characters', document.querySelectorAll('.nav-btn')[2]); setTimeout(() => { const el = document.getElementById('selCharGenProduct'); if (el) el.value = '${pid}'; }, 150);">
                    ✨ Tạo Ảnh Nhân Vật Cầm SP Này (2K)
                  </button>
                  ${p.has_project ? `
                    <button class="btn btn-xs btn-outline" style="border-color:rgba(59,130,246,0.5); color:#93c5fd; padding:6px 11px;" onclick="closeModal('modalProductGallery'); STATE.currentProjectId='${pid}'; switchTab('dashboard', document.querySelector('.nav-btn')); loadProjectDetail('${pid}', false);">
                      📊 Mở Xem Trong Studio Dự Án (${p.final_videos_count || 0} Video Final)
                    </button>
                  ` : ''}
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
      openModal("modalProductGallery");
    }

    function switchPgGalleryImage(pid, idx) {
      openProductGalleryModal(pid, idx);
    }

    function openProductGalleryLightbox(pid, selIdx = 0) {
      const p = (STATE.productsStore || []).find(x => x.product_id === pid);
      if (!p) return;
      const imgs = p.local_images || [];
      if (!imgs.length && p.primary_image_path) imgs.push(p.primary_image_path);
      if (!imgs.length) return;
      const gallery = imgs.map((absPath, i) => ({
        absPath,
        title: `${p.title || ('SP ' + pid)} — Ảnh ${i + 1}/${imgs.length}`,
      }));
      openImageLightbox(imgs[selIdx] || imgs[0], gallery[selIdx]?.title || p.title, gallery, selIdx);
    }

    function openCharacterRefLightbox(charKey) {
      const chars = STATE.charLib?.characters || [];
      const gallery = chars.filter(c => c.ref_image_abs).map(c => ({
        absPath: c.ref_image_abs,
        title: `👤 Nhân vật ${c.key.toUpperCase()}: ${c.name || ''} (Character Sheet Tham Chiếu)`,
      }));
      const target = chars.find(c => c.key === charKey);
      if (!target || !target.ref_image_abs) return;
      openImageLightbox(target.ref_image_abs, `👤 ${target.name} (${charKey.toUpperCase()})`, gallery);
    }

    function openSheetTemplateLightbox(tplIdx) {
      const templates = STATE.charLib?.sheet_templates || [];
      const t = templates[tplIdx];
      if (!t) return;
      const imgEl = document.getElementById(`sheetPreviewImg_${tplIdx}`);
      const curSrc = imgEl ? imgEl.getAttribute("src") : "";
      const gallery = [];
      templates.forEach((tpl, i) => {
        if (tpl.sample_image_path) {
          gallery.push({
            absPath: tpl.sample_image_path,
            title: `🤖 [Mẫu #${i + 1} - Ảnh AI Demo] ${tpl.name}`,
          });
        }
        if (tpl.reference_image_path && tpl.reference_image_path !== tpl.sample_image_path) {
          gallery.push({
            absPath: tpl.reference_image_path,
            title: `📌 [Mẫu #${i + 1} - Ảnh Ref Gốc] ${tpl.name}`,
          });
        }
      });
      openImageLightbox(curSrc || t.sample_image_path, t.name, gallery);
    }

    function copyProductImageLinks(pid) {
      const p = (STATE.productsStore || []).find(x => x.product_id === pid);
      if (!p) return;
      const links = (p.remote_images && p.remote_images.length) ? p.remote_images : (p.local_images || []);
      if (!links.length) return alert("Chưa có link ảnh nào cho sản phẩm này!");
      navigator.clipboard.writeText(links.join("\n"));
      showProdBanner(`📋 Đã copy ${links.length} link ảnh của SP <b>${pid}</b> vào Clipboard!`);
    }

    function copyFullProductSummary(pid) {
      const p = (STATE.productsStore || []).find(x => x.product_id === pid);
      if (!p) return;
      const lines = [
        `🛍️ Tên sản phẩm: ${p.title || ''}`,
        `🆔 ID sản phẩm: ${pid}`,
        `🏪 Shop: ${p.seller || 'TikTok Shop'}`,
        `💰 Giá bán: ${formatVndPrice(p.price)} ${p.original_price ? `(Giá gốc: ${formatVndPrice(p.original_price)})` : ''}`,
        `🔥 Đã bán: ${formatSoldNumber(p.sold_count_label || p.sold_count)}`,
        `🔗 Link PDP: ${p.web_url || `https://shop.tiktok.com/vn/pdp/${pid}`}`,
        `📦 Phân loại: ${(p.variations || ['Mặc định']).join(', ')}`,
        `📝 Mô tả: ${p.description || ''}`,
      ];
      navigator.clipboard.writeText(lines.join("\n"));
      showProdBanner(`📋 Đã copy Full thông tin sản phẩm <b>${pid}</b>!`);
    }

    function copyAgentCommandFromGalleryModal(pid) {
      const tpl = document.getElementById("selModalProdTpl")?.value || "001";
      const cmd = `Hãy tạo video cho sản phẩm ID ${pid} theo Template ${tpl}`;
      navigator.clipboard.writeText(cmd);
      showProdBanner(`🤖 Đã copy lệnh gửi AI Agent: "<b>${cmd}</b>"`);
    }

    async function toggleHotProduct(pid) {
      const p = (STATE.productsStore || []).find(x => x.product_id === pid);
      if (!p) return;
      p.is_hot = !p.is_hot;
      await apiPost("/api/products-store/toggle-hot", { product_id: pid, is_hot: p.is_hot });
      openProductGalleryModal(pid, STATE.currentPgImgIdx || 0);
      renderProductsStoreGrid();
    }

    async function setProductPrimaryRefImage(pid, filename) {
      const tpl = document.getElementById("selModalProdTpl")?.value || "Nhà Xưởng";
      const vpc = parseInt(document.getElementById("selModalProdVpc")?.value || "3", 10);
      await apiPost("/api/products-store/create-video", {
        input: pid,
        template_name: tpl,
        videos_per_character: vpc,
        primary_product_refs: [filename],
        force_regenerate_prompts: false,
        auto_run: false,
      });
      await loadProductsStore(false);
      openProductGalleryModal(pid, STATE.currentPgImgIdx || 0);
    }

    async function createVideoFromGalleryModal(pid, autoRun) {
      const tpl = document.getElementById("selModalProdTpl")?.value || "Nhà Xưởng";
      const vpc = parseInt(document.getElementById("selModalProdVpc")?.value || "3", 10);
      closeModal("modalProductGallery");
      showProdBanner(`🚀 Đang tạo kịch bản (${tpl}, ${vpc} video/NV) cho SP <b>${pid}</b>...`);
      const res = await apiPost("/api/products-store/create-video", {
        input: pid,
        template_name: tpl,
        videos_per_character: vpc,
        force_regenerate_prompts: true,
        auto_run: autoRun,
      });
      if (res && res.ok) {
        showProdBanner(`✅ Đã tạo ${res.videos_count} kịch bản cho SP <b>${pid}</b> ${autoRun ? 'và bắt đầu chạy đa luồng!' : ''}`);
        await loadProductsStore(false);
        await refreshAll(false);
        if (autoRun) {
          STATE.currentProjectId = pid;
          switchTab("dashboard", document.querySelector(".nav-btn"));
          loadProjectDetail(pid, false);
        }
      }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TAB MỚI 2: THƯ VIỆN NHÂN VẬT & CHARACTER SHEET TEMPLATES
    // ═══════════════════════════════════════════════════════════════════════
    STATE.charLib = null;
    STATE.voiceFilter = "all";

    function showCharVoiceBanner(msg, isErr = false) {
      const el = document.getElementById("charVoiceBanner");
      if (!el) return;
      el.style.display = "block";
      el.style.borderColor = isErr ? "rgba(239,68,68,0.5)" : "rgba(56,189,248,0.45)";
      el.style.color = isErr ? "#fca5a5" : "#bae6fd";
      el.innerHTML = msg;
    }

    async function loadCharacterLibrary() {
      const res = await apiGet("/api/characters");
      if (!res || !res.ok) return;
      STATE.charLib = res;
      renderCharactersTab();
    }

    function renderCharactersTab() {
      const lib = STATE.charLib;
      if (!lib) return;

      const selVpc = document.getElementById("selGlobalVideosPerChar");
      if (selVpc) selVpc.value = String(lib.default_videos_per_character || 3);
      const selModel = document.getElementById("selGlobalImgModel");
      if (selModel) selModel.value = lib.default_image_model || "nano_banana";

      const templates = lib.sheet_templates || [];
      const selTpl = document.getElementById("selGlobalSheetTemplate");
      if (selTpl) {
        selTpl.innerHTML = templates.map(t =>
          `<option value="${t.id}" ${t.id === lib.default_sheet_template_id ? 'selected' : ''}>${t.name}</option>`
        ).join("");
      }

      const voicesList = lib.voices_list || [];
      const builtinVoicesList = lib.builtin_flow_voices || [];
      const vCntLbl = document.getElementById("voiceCountLabel");
      if (vCntLbl) vCntLbl.textContent = voicesList.length;

      const chars = lib.characters || [];
      const cntLbl = document.getElementById("charCountLabel");
      if (cntLbl) cntLbl.textContent = chars.length;

      const cGrid = document.getElementById("charactersGrid");
      if (cGrid) {
        cGrid.innerHTML = chars.map(c => {
          const ck = c.key;
          const imgSrc = c.ref_image_abs ? `/api/media?path=${encodeURIComponent(c.ref_image_abs)}` : "";
          const tplOpts = templates.map(t =>
            `<option value="${t.id}" ${t.id === c.sheet_template_id ? 'selected' : ''}>${t.name}</option>`
          ).join("");

          let matchedCustom = false;
          const customOpts = voicesList.map(v => {
            const rIcon = v.region === 'south' ? '☀️' : (v.region === 'central' ? '🌿' : '🌸');
            const isSel = (c.default_voice === v.key) || (!c.default_voice && c.voice_id === v.voice_id);
            if (isSel) matchedCustom = true;
            return `<option value="${v.key}" ${isSel ? 'selected' : ''}>${rIcon} ${v.name}</option>`;
          }).join("");

          const builtinOpts = builtinVoicesList.map(b => {
            const bVal = `builtin:${b.slug}`;
            const isSel = !matchedCustom && (c.default_voice === bVal || c.voice_id === b.slug);
            return `<option value="${bVal}" ${isSel ? 'selected' : ''}>🌐 ${b.display_name}</option>`;
          }).join("");

          const voiceOpts = `
            <optgroup label="🌟 Giọng Việt Nam Đã Custom (${voicesList.length} Giọng)">${customOpts}</optgroup>
            <optgroup label="🌐 30 Giọng Gốc Google Flow (Built-in)">${builtinOpts}</optgroup>
          `;

          const curVoiceObj = voicesList.find(v => (c.default_voice === v.key) || (!c.default_voice && c.voice_id === v.voice_id)) || voicesList[0] || {};
          const sampleTxt = curVoiceObj.sample_dialogue_vn || "Chào các bác nhé, hôm nay em dẫn mọi người vào tận xưởng kiểm chứng chất lượng thực tế!";
          const regShort = c.voice_region === 'south' ? '☀️ Nam' : (c.voice_region === 'central' ? '🌿 Trung' : '🌸 Bắc');
          const genShort = c.voice_gender === 'male' ? '👨 Nam' : '👩 Nữ';
          const pillCls = ck === 'nv1' ? 'char-nv1' : (ck === 'nv2' ? 'char-nv2' : 'char-nv3');
          const subTxt = c.subtitle || (ck === 'nv1' ? 'Tóc ngang vai • Kính đen' : (ck === 'nv2' ? 'Tóc buộc cao • Kẹp màu' : 'Sơ mi Linen • Đồ Nam'));

          return `
            <div class="card" style="margin:0; min-width:0; overflow:hidden; border-color:${c.enabled ? 'rgba(99,102,241,0.48)' : 'var(--border)'}; background:linear-gradient(160deg, #101726 0%, #090d16 100%);">
              <!-- HEADER NHÂN VẬT GỌN GÀNG TRÊN 1 HÀNG DUY NHẤT -->
              <div style="display:flex; justify-content:space-between; align-items:center; padding-bottom:8px; margin-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.07); gap:8px; flex-wrap:nowrap;">
                <div style="display:flex; align-items:center; gap:8px; min-width:0; flex:1;">
                  <span class="char-pill ${pillCls}" style="font-size:11px; padding:3px 8px; flex-shrink:0;">${ck.toUpperCase()}</span>
                  <div style="min-width:0; flex:1; display:flex; align-items:baseline; gap:6px; overflow:hidden;">
                    <span style="font-weight:800; font-size:13.5px; color:#f8fafc; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${c.name || ck.toUpperCase()}</span>
                    <span style="font-size:11px; color:#94a3b8; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">• ${subTxt}</span>
                  </div>
                </div>
                <div style="display:flex; align-items:center; gap:5px; flex-shrink:0;">
                  <span class="badge" style="background:rgba(16,185,129,0.14); color:#34d399; border:1px solid rgba(16,185,129,0.32); font-size:10.5px;">${genShort} • ${regShort}</span>
                  <span class="badge ${c.enabled ? 'badge-done' : 'badge-fail'}" style="font-size:10.5px;">${c.enabled ? '● Bật' : '○ Tắt'}</span>
                  <button class="btn btn-xs btn-outline" style="padding:3px 7px;" onclick="openEditCharacterModal('${ck}')" title="Chỉnh sửa chi tiết nhân vật">✏️ Sửa</button>
                  <button class="btn btn-xs btn-danger" style="padding:3px 6px;" onclick="deleteSingleCharacter('${ck}')" title="Xoá nhân vật">🗑️</button>
                </div>
              </div>

              <div style="display:grid; grid-template-columns: 165px minmax(0, 1fr); gap:12px; align-items:start; width:100%;">
                <div style="width:165px;">
                  <div style="width:165px; height:128px; border-radius:8px; overflow:hidden; background:#000; border:1px solid var(--border-light); cursor:zoom-in; position:relative;" onclick="openCharacterRefLightbox('${ck}')" title="Bấm vào ảnh để Xem Full Màn Hình & Phóng To / Thu Nhỏ">
                    ${imgSrc ? `<img src="${imgSrc}" style="width:100%; height:100%; object-fit:cover;" /><span style="position:absolute; bottom:4px; right:4px; background:rgba(0,0,0,0.78); color:#fcd34d; font-size:9.5px; font-weight:800; padding:1.5px 6px; border-radius:4px;">🔍 Zoom</span>` : `<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:var(--muted); font-size:11px;">Chưa có ảnh</div>`}
                  </div>
                  <div style="display:flex; flex-direction:column; gap:5px; margin-top:6px;">
                    <button class="btn btn-xs btn-amber" style="width:100%;" onclick="openCharImageGenModal('${ck}', 'character_sheet')">✨ Tạo Character Sheet AI</button>
                    <button class="btn btn-xs btn-primary" style="width:100%;" onclick="openCharImageGenModal('${ck}', 'product_ref')">🛍️ Tạo Ảnh Cầm SP (AI)</button>
                  </div>
                </div>

                <div style="display:flex; flex-direction:column; gap:7px; min-width:0; width:100%;">
                  <!-- Tích Hợp Chọn Giọng Đọc, Nghe Thử Tiếng Việt & Custom Giọng Ngay Trong Nhân Vật -->
                  <div style="background:#080c14; border:1px solid rgba(16,185,129,0.35); border-radius:8px; padding:8px 10px; min-width:0; width:100%; box-sizing:border-box;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; gap:6px; flex-wrap:wrap;">
                      <div style="display:flex; align-items:center; gap:8px;">
                        <label style="color:#34d399; margin:0; font-size:11px; font-weight:800;">🎙️ Giọng Đọc (${ck.toUpperCase()})</label>
                        <label style="margin:0; font-size:10.5px; color:#fde68a; display:flex; align-items:center; gap:4px; cursor:pointer;">
                          <input type="checkbox" id="chkCharLockVoice_${ck}" style="width:auto;" ${c.lock_voice_to_character !== false ? 'checked' : ''} />
                          🔒 Khóa cố định
                        </label>
                      </div>
                      <div style="display:flex; gap:4px; align-items:center;">
                        <button class="btn btn-xs btn-amber" style="font-weight:800; padding:3px 8px;" onclick="previewCharSelectedVoice('${ck}')" title="Nghe thử mẫu giọng Tiếng Việt của giọng đang chọn">🔊 Nghe thử</button>
                        <button class="btn btn-xs btn-outline" style="padding:3px 7px;" onclick="openVoiceEditorForChar('${ck}')" title="Chỉnh sửa hoặc Tự Custom giọng đang chọn trên Google Flow">✏️ Custom</button>
                        <button class="btn btn-xs btn-success" style="padding:3px 7px;" onclick="openVoiceEditorModal('', '', '${ck}')" title="Tạo mới 1 giọng đọc riêng cho nhân vật này">➕ Mới</button>
                      </div>
                    </div>
                    <select id="selCharVoice_${ck}" style="width:100%; max-width:100%; font-size:11.5px; font-weight:700; margin-bottom:5px;" onchange="onCharCardVoiceChange('${ck}')">
                      ${voiceOpts}
                    </select>
                    <div id="charVoiceSummary_${ck}" style="font-size:10.5px; color:#94a3b8; line-height:1.35; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100%; display:block;" title="${sampleTxt.replace(/"/g, '&quot;')}">
                      🗣️ Mẫu TV: <span style="color:#cbd5e1;">"${sampleTxt}"</span>
                    </div>
                  </div>

                  <div class="grid-2" style="gap:8px; min-width:0;">
                    <div style="min-width:0;">
                      <label>🎞️ Số Video / Sản Phẩm</label>
                      <select id="selCharVpc_${ck}" style="width:100%;">
                        <option value="1" ${c.videos_per_character === 1 ? 'selected' : ''}>1 Video / SP</option>
                        <option value="2" ${c.videos_per_character === 2 ? 'selected' : ''}>2 Video / SP</option>
                        <option value="3" ${c.videos_per_character === 3 ? 'selected' : ''}>3 Video / SP</option>
                        <option value="4" ${c.videos_per_character === 4 ? 'selected' : ''}>4 Video / SP</option>
                        <option value="5" ${c.videos_per_character === 5 ? 'selected' : ''}>5 Video / SP</option>
                      </select>
                    </div>
                    <div style="min-width:0;">
                      <label>🤖 Model Ảnh Ưa Thích</label>
                      <select id="selCharModel_${ck}" style="width:100%;">
                        <option value="nano_banana" ${c.preferred_image_model === 'nano_banana' ? 'selected' : ''}>🍌 Nano Banana 2.1</option>
                        <option value="chatgpt" ${c.preferred_image_model === 'chatgpt' ? 'selected' : ''}>🤖 ChatGPT Image</option>
                      </select>
                    </div>
                  </div>

                  <div style="min-width:0;">
                    <label>🧩 Mẫu Character Sheet Áp Dụng</label>
                    <select id="selCharSheetTpl_${ck}" style="width:100%; max-width:100%;">${tplOpts}</select>
                  </div>

                  <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; margin-top:2px; flex-wrap:wrap;">
                    <label style="margin:0; display:flex; align-items:center; gap:5px; cursor:pointer; color:#e2e8f0; font-size:11.5px;">
                      <input type="checkbox" id="chkCharEnabled_${ck}" style="width:auto;" ${c.enabled ? 'checked' : ''} />
                      Bật nhân vật này khi tạo video
                    </label>
                    <button class="btn btn-xs btn-success" style="font-weight:800; padding:5px 10px;" onclick="saveSingleCharacterQuick('${ck}')">💾 Lưu Nhân Vật</button>
                  </div>
                </div>
              </div>
            </div>
          `;
        }).join("");
      }

      renderVoicesLibraryGrid();
      renderBuiltinFlowVoicesGrid();

      const tGrid = document.getElementById("sheetTemplatesGrid");
      if (tGrid) {
        tGrid.innerHTML = templates.map((t, idx) => {
          const sImg = t.sample_image_path ? `/api/media?path=${encodeURIComponent(t.sample_image_path)}` : "";
          const rImg = t.reference_image_path ? `/api/media?path=${encodeURIComponent(t.reference_image_path)}` : "";
          const breakdownHtml = (t.structure_breakdown || []).map(b => `<li style="margin-bottom:2px;">${b}</li>`).join("");
          const rawPromptToCopy = (t.raw_reference_prompt || t.character_sheet_prompt || "").replace(/`/g, "\\`").replace(/\$/g, "\\$");
          return `
            <div style="background:linear-gradient(165deg, #0d1424 0%, #080c15 100%); border:1px solid rgba(245,158,11,0.35); border-radius:12px; padding:12px 14px; display:flex; flex-direction:column; justify-content:space-between; gap:9px; box-shadow:0 6px 20px rgba(0,0,0,0.4); min-width:0; overflow:hidden;">
              <div style="display:flex; flex-direction:column; gap:8px; min-width:0;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; padding-bottom:6px; border-bottom:1px solid rgba(255,255,255,0.07); flex-wrap:nowrap;">
                  <div style="min-width:0; flex:1; display:flex; align-items:baseline; gap:6px; overflow:hidden;">
                    <span style="font-weight:800; font-size:13px; color:#fde68a; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${t.name}</span>
                    ${t.subtitle ? `<span style="font-size:10.5px; color:#94a3b8; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">• ${t.subtitle}</span>` : ''}
                  </div>
                  <div style="display:flex; gap:4px; flex-shrink:0; align-items:center;">
                    <span class="badge" style="background:rgba(56,189,248,0.16); color:#38bdf8; border:1px solid rgba(56,189,248,0.35); font-size:10px;">${t.aspect_ratio || '3:2'}</span>
                    <span class="badge badge-run" style="font-size:10px;">${t.badge || 'TEMPLATE'}</span>
                  </div>
                </div>

                ${sImg ? `
                  <div style="position:relative; background:#030509; border-radius:8px; border:1px solid rgba(255,255,255,0.12); overflow:hidden;">
                    <img id="sheetPreviewImg_${idx}" src="${sImg}" style="width:100%; height:235px; object-fit:contain; background:#fff; cursor:zoom-in; display:block;" onclick="openSheetTemplateLightbox(${idx})" title="Bấm vào ảnh để Xem Full Màn Hình & Phóng To / Thu Nhỏ" />
                    <button class="btn btn-xs btn-primary" style="position:absolute; top:6px; left:6px; padding:3px 8px; font-size:10px; font-weight:800; box-shadow:0 4px 12px rgba(0,0,0,0.6);" onclick="openSheetTemplateLightbox(${idx})">🔍 Xem Full & Zoom</button>
                    ${rImg ? `
                      <div style="position:absolute; bottom:6px; right:6px; display:flex; gap:4px; background:rgba(9,13,22,0.88); padding:4px 6px; border-radius:6px; border:1px solid rgba(245,158,11,0.45);">
                        <button class="btn btn-xs btn-amber" style="padding:2px 7px; font-size:10px;" onclick="document.getElementById('sheetPreviewImg_${idx}').src='${sImg}'">🤖 Ảnh AI Demo</button>
                        <button class="btn btn-xs btn-outline" style="padding:2px 7px; font-size:10px;" onclick="document.getElementById('sheetPreviewImg_${idx}').src='${rImg}'">📌 Ảnh Ref Gốc</button>
                      </div>
                    ` : ''}
                  </div>
                ` : ''}

                ${t.use_case_guide ? `
                  <div style="background:rgba(16,185,129,0.10); border:1px solid rgba(16,185,129,0.32); border-radius:7px; padding:6px 9px; font-size:11px; color:#6ee7b7; line-height:1.4; font-weight:600;">
                    ${t.use_case_guide}
                  </div>
                ` : ''}

                <div style="font-size:11px; color:#cbd5e1; line-height:1.4;">${t.description || ''}</div>

                ${breakdownHtml ? `
                  <div style="background:#060911; border:1px solid rgba(255,255,255,0.07); border-radius:7px; padding:7px 10px; font-size:10.5px; color:#94a3b8;">
                    <div style="font-weight:800; color:#a5b4fc; margin-bottom:3px;">📐 Cấu trúc bố cục Character Sheet:</div>
                    <ul style="margin:0 0 0 15px; padding:0; line-height:1.4;">${breakdownHtml}</ul>
                  </div>
                ` : ''}

                <details style="background:#050811; border:1px solid rgba(245,158,11,0.25); border-radius:7px; padding:6px 9px;">
                  <summary style="cursor:pointer; font-size:11px; font-weight:700; color:#fcd34d;">📜 Xem Prompt Gốc Chuẩn Của Mẫu Này</summary>
                  <pre style="margin-top:6px; white-space:pre-wrap; word-break:break-word; font-family:Consolas, monospace; font-size:10.5px; color:#e2e8f0; line-height:1.45;">${(t.raw_reference_prompt || t.character_sheet_prompt || '').replace(/</g, '&lt;')}</pre>
                </details>
              </div>

              <div style="display:flex; gap:6px; justify-content:space-between; align-items:center; flex-wrap:wrap; padding-top:6px; border-top:1px solid rgba(255,255,255,0.07);">
                <div style="display:flex; gap:5px;">
                  <button class="btn btn-xs btn-primary" onclick="openSheetTemplateLightbox(${idx})">🔍 Xem Full & Zoom</button>
                  <button class="btn btn-xs btn-outline" onclick="navigator.clipboard.writeText(\`${rawPromptToCopy}\`); showCharVoiceBanner('📋 Đã copy Prompt Character Sheet của <b>${t.name.replace(/'/g, '')}</b>!');">📋 Copy Prompt</button>
                  <button class="btn btn-xs btn-outline" onclick="openFolderEncoded('${encodeURIComponent(t.sample_image_path || '')}')">📂 Mở File</button>
                </div>
                <div style="display:flex; gap:5px;">
                  <button class="btn btn-xs btn-amber" style="font-weight:800;" onclick="openCharImageGenModal('nv1', 'character_sheet', '${t.id}')">✨ Dùng Mẫu Này Tạo Ảnh</button>
                  <button class="btn btn-xs btn-outline" onclick="openSheetTemplateEditor('${t.id}')">✏️ Sửa Prompt</button>
                </div>
              </div>
            </div>
          `;
        }).join("");
      }
    }

    function switchVoiceStudioSubtab(subtab) {
      STATE.voiceSubtab = subtab;
      const paneCustom = document.getElementById("voiceSubtabPaneCustom");
      const paneBuiltin = document.getElementById("voiceSubtabPaneBuiltin");
      const btnCustom = document.getElementById("btnVoiceSubtabCustom");
      const btnBuiltin = document.getElementById("btnVoiceSubtabBuiltin");
      if (paneCustom) paneCustom.style.display = subtab === "custom" ? "block" : "none";
      if (paneBuiltin) paneBuiltin.style.display = subtab === "builtin" ? "block" : "none";
      if (btnCustom) {
        btnCustom.className = subtab === "custom" ? "btn btn-sm btn-success" : "btn btn-sm btn-outline";
      }
      if (btnBuiltin) {
        btnBuiltin.className = subtab === "builtin" ? "btn btn-sm btn-success" : "btn btn-sm btn-outline";
      }
    }

    function onSelectCommonVnDialoguePreset() {
      const sel = document.getElementById("selCommonVnDialogue");
      const inp = document.getElementById("inpCustomVnDialogue");
      if (sel && inp && sel.value) {
        inp.value = sel.value;
      }
    }

    function setVoiceLibraryFilter(flt, btnEl) {
      STATE.voiceFilter = flt;
      const bar = document.getElementById("voiceFilterBar");
      if (bar) {
        bar.querySelectorAll(".btn-filter").forEach(b => b.classList.remove("active"));
      }
      if (btnEl) btnEl.classList.add("active");
      renderVoicesLibraryGrid();
      renderBuiltinFlowVoicesGrid();
    }

    function renderVoicesLibraryGrid() {
      const box = document.getElementById("voicesLibraryGrid");
      if (!box || !STATE.charLib) return;
      const voices = STATE.charLib.voices_list || [];
      const flt = STATE.voiceFilter || "all";

      // Populate Common Vietnamese Dialogue Presets dropdown if empty
      const selPreset = document.getElementById("selCommonVnDialogue");
      const presets = STATE.charLib.common_vn_dialogues || [];
      if (selPreset && selPreset.options.length <= 1 && presets.length > 0) {
        selPreset.innerHTML = presets.map((p, i) => `<option value="${p.text.replace(/"/g, '&quot;')}" ${i === 0 ? 'selected' : ''}>${p.label}</option>`).join("");
        const inpCustom = document.getElementById("inpCustomVnDialogue");
        if (inpCustom && !inpCustom.value && presets[0]) {
          inpCustom.value = presets[0].text;
        }
      }

      const customCountEl = document.getElementById("customVoicesTabCount");
      if (customCountEl) customCountEl.textContent = voices.length;

      const filtered = voices.filter(v => {
        if (flt === "all") return true;
        if (flt === "north" || flt === "south" || flt === "central") return v.region === flt;
        if (flt === "female" || flt === "male") return v.gender === flt;
        if (flt === "energetic_sale" || flt === "sweet_foodie") return v.tone_style === flt;
        return true;
      });

      box.innerHTML = filtered.map(v => {
        const vk = v.key;
        const regColor = v.region === "south" ? "#f59e0b" : (v.region === "central" ? "#10b981" : "#38bdf8");
        const genIcon = v.gender === "male" ? "👨 Nam" : "👩 Nữ";
        const cats = (v.recommended_categories || []).join(" • ");
        const hasFlowAudio = Boolean(v.has_flow_vn_audio);
        const sampleText = v.sample_dialogue_vn || "Mấy bà ơi tin được không, hũ kho quẹt tôm khô tóp mỡ đặc sánh như này mà giá tận xưởng rẻ bèo luôn á!";
        const shortUuid = (v.voice_id || "").length > 18 ? (v.voice_id.slice(0, 8) + "..." + v.voice_id.slice(-6)) : (v.voice_id || "");

        return `
          <div style="background:linear-gradient(160deg, #101827 0%, #090d16 100%); border:1px solid ${hasFlowAudio ? 'rgba(16,185,129,0.35)' : 'rgba(255,255,255,0.12)'}; border-radius:11px; padding:11px 13px; display:flex; flex-direction:column; justify-content:space-between; gap:8px;">
            <div style="display:flex; flex-direction:column; gap:6px;">
              <!-- Header gọn gàng -->
              <div style="display:flex; justify-content:space-between; align-items:start; gap:6px;">
                <div style="font-size:13px; font-weight:800; color:#f8fafc; line-height:1.3;">🎙️ ${v.name}</div>
                <div style="display:flex; gap:4px; align-items:center; flex-shrink:0;">
                  ${hasFlowAudio ? `<span class="badge" style="background:rgba(16,185,129,0.2); color:#34d399; border:1px solid rgba(16,185,129,0.4); font-size:9.5px;">✅ Đã Custom Flow</span>` : ''}
                  <span style="font-family:Consolas, monospace; font-size:10px; color:#94a3b8; background:#050811; padding:2px 6px; border-radius:4px; border:1px solid rgba(255,255,255,0.08);">#${vk}</span>
                </div>
              </div>

              <!-- Nhãn Vùng miền • Giới tính • Phong cách -->
              <div style="display:flex; gap:5px; flex-wrap:wrap; align-items:center;">
                <span class="badge" style="background:rgba(255,255,255,0.08); color:#e2e8f0; font-size:10.5px;">${genIcon}</span>
                <span class="badge" style="background:rgba(56,189,248,0.14); color:${regColor}; border:1px solid ${regColor}44; font-size:10.5px;">🗺️ ${v.region_label || v.region}</span>
                <span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399; font-size:10.5px;">${v.tone_label || v.tone_style}</span>
                <code style="font-size:10px; color:#67e8f9; background:#050811; padding:1px 5px; border-radius:4px;" title="Flow Voice ID: ${v.voice_id}">🆔 ${shortUuid}</code>
              </div>

              <!-- Câu thoại mẫu Tiếng Việt của Giọng -->
              <div style="background:#060a12; border-left:3px solid #10b981; border-radius:6px; padding:6px 9px; font-size:11px; color:#e2e8f0; line-height:1.4;">
                <span style="color:#6ee7b7; font-weight:700;">🗣️ Mẫu Tiếng Việt:</span> "${sampleText}"
              </div>

              <!-- Chi tiết kỹ thuật thu gọn để không rối mắt -->
              <details style="background:#070b14; border:1px solid rgba(255,255,255,0.06); border-radius:6px; padding:4px 8px; font-size:10.5px; color:#94a3b8;">
                <summary style="cursor:pointer; color:#93c5fd; font-weight:700; user-select:none;">🔍 Xem chi tiết UUID, Prompt Âm học & Ngành hàng hợp</summary>
                <div style="margin-top:5px; display:flex; flex-direction:column; gap:3px; line-height:1.4;">
                  <div>📌 <b>Mô tả:</b> ${v.description || ''}</div>
                  <div>🆔 <b>Full Voice UUID:</b> <code style="color:#67e8f9;">${v.voice_id}</code> (${v.speed_wpm || '42-46 từ/10s'})</div>
                  <div>🔮 <b>Director's Notes (EN):</b> <span style="color:#a5b4fc; font-family:Consolas, monospace;">${v.voice_prompt_en || ''}</span></div>
                  <div>💬 <b>Từ đệm vùng miền:</b> <span style="color:#fcd34d;">"${v.dialect_markers_vn || ''}"</span></div>
                  <div>🏷️ <b>Ngành hàng:</b> <span style="color:#34d399;">${cats}</span></div>
                </div>
              </details>
            </div>

            <!-- Cụm nút thao tác rõ ràng: Nghe Thử Tiếng Việt | Đọc Câu Đang Chọn | Tự Custom Lại Trên Flow | Gắn NV -->
            <div style="display:flex; justify-content:space-between; align-items:center; gap:5px; flex-wrap:wrap; padding-top:6px; border-top:1px solid rgba(255,255,255,0.07);">
              <div style="display:flex; gap:4px; flex-wrap:wrap;">
                <button class="btn btn-xs btn-amber" style="font-weight:800;" onclick="previewVoiceVietnamese('${vk}', '', true)" title="Nghe thử mẫu giọng Tiếng Việt đã tạo trực tiếp từ Google Flow">🔊 Nghe Thử Tiếng Việt</button>
                <button class="btn btn-xs btn-outline" onclick="previewVoiceVietnamese('${vk}', '', false)" title="Đọc câu thoại Tiếng Việt đang chọn trên thanh công cụ">🗣️ Đọc Câu Đang Chọn</button>
                <button class="btn btn-xs btn-success" onclick="autoCustomVoiceOnFlowQuick('${vk}')" title="Tự động đẩy cấu hình giọng này lên Google Flow để tạo & lấy file giọng đọc mới về">🚀 Tự Custom Trên Flow</button>
              </div>
              <div style="display:flex; gap:4px; align-items:center;">
                <button class="btn btn-xs btn-primary" onclick="bindVoiceToCharacterQuick('${vk}', 'nv1')" title="Gắn cố định giọng này cho Nhân Vật 1">🔒 NV1</button>
                <button class="btn btn-xs btn-primary" onclick="bindVoiceToCharacterQuick('${vk}', 'nv2')" title="Gắn cố định giọng này cho Nhân Vật 2">🔒 NV2</button>
                <button class="btn btn-xs btn-outline" onclick="openVoiceEditorModal('${vk}')" title="Chỉnh sửa hoặc Custom chi tiết">✏️</button>
                ${(vk !== 'nv1' && vk !== 'nv2') ? `<button class="btn btn-xs btn-danger" onclick="deleteVoiceProfile('${vk}')">🗑️</button>` : ''}
              </div>
            </div>
          </div>
        `;
      }).join("");
    }

    function renderBuiltinFlowVoicesGrid() {
      const box = document.getElementById("builtinFlowVoicesGrid");
      if (!box || !STATE.charLib) return;
      const bVoices = STATE.charLib.builtin_flow_voices || [];
      const flt = STATE.voiceFilter || "all";

      const builtinCountEl = document.getElementById("builtinVoicesTabCount");
      if (builtinCountEl) builtinCountEl.textContent = bVoices.length;

      const filtered = bVoices.filter(b => {
        if (flt === "female" || flt === "male") return b.gender === flt;
        return true;
      });

      box.innerHTML = filtered.map(b => {
        const genBadge = b.gender === "male" ? "👨 Nam" : "👩 Nữ";
        const genColor = b.gender === "male" ? "#38bdf8" : "#f472b6";
        return `
          <div style="background:#0c1220; border:1px solid rgba(255,255,255,0.1); border-radius:9px; padding:9px 11px; display:flex; flex-direction:column; justify-content:space-between; gap:6px;">
            <div>
              <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
                <span style="font-weight:800; font-size:12.5px; color:#f8fafc;">${b.display_name}</span>
                <div style="display:flex; gap:4px; align-items:center;">
                  <span class="badge" style="background:rgba(255,255,255,0.07); color:${genColor}; font-size:10px;">${genBadge}</span>
                  <code style="font-size:10px; color:#67e8f9; background:#050811; padding:1px 5px; border-radius:4px;">${b.slug}</code>
                </div>
              </div>
              <div style="font-size:11px; color:#94a3b8; margin-top:4px; line-height:1.35;">${b.description}</div>
            </div>
            <div style="display:flex; gap:4px; flex-wrap:wrap; padding-top:4px; border-top:1px solid rgba(255,255,255,0.06);">
              <button class="btn btn-xs btn-amber" style="flex:1; font-weight:700;" onclick="previewBuiltinVoiceVietnamese('${b.slug}', '${b.gender}', '${b.display_name.replace(/'/g, '')}')">🔊 Nghe Thử TV</button>
              <button class="btn btn-xs btn-outline" onclick="playVoiceSampleUrl('${b.sample_url}', '${b.display_name.replace(/'/g, '')} (WAV Gốc)')">🎵 Gốc</button>
              <button class="btn btn-xs btn-success" style="flex:1; font-weight:700;" onclick="openVoiceEditorModal('', '${b.slug}')">🚀 Custom Giọng VN</button>
            </div>
          </div>
        `;
      }).join("");
    }

    function playVoiceSampleUrl(url, label) {
      const player = document.getElementById("voiceSampleAudioPlayer");
      const lbl = document.getElementById("voicePreviewNowPlayingLabel");
      const bar = document.getElementById("voicePreviewInlineBar");
      if (!player || !url) return;
      if (bar) bar.style.display = "flex";
      player.style.display = "block";
      player.src = url;
      player.play().catch(() => {});
      if (lbl) lbl.innerHTML = `🔊 Đang phát: <b style="color:#34d399;">${label}</b>`;
      showCharVoiceBanner(`🔊 Đang phát mẫu giọng đọc: <b>${label}</b>`);
    }

    function onCharCardVoiceChange(ck) {
      const val = document.getElementById(`selCharVoice_${ck}`)?.value || "";
      const summaryEl = document.getElementById(`charVoiceSummary_${ck}`);
      if (!summaryEl) return;
      const voices = STATE.charLib?.voices_list || [];
      const bVoices = STATE.charLib?.builtin_flow_voices || [];
      if (val.startsWith("builtin:")) {
        const slug = val.replace("builtin:", "");
        const b = bVoices.find(x => x.slug === slug);
        if (b) {
          summaryEl.innerHTML = `🌐 Giọng gốc Google Flow: <b style="color:#67e8f9;">${b.display_name} (${slug})</b> — ${b.description}`;
        }
      } else {
        const v = voices.find(x => x.key === val);
        if (v) {
          const sampleTxt = v.sample_dialogue_vn || "";
          summaryEl.innerHTML = `🗣️ Mẫu TV: <span style="color:#cbd5e1;">"${sampleTxt}"</span>`;
          summaryEl.title = sampleTxt;
        }
      }
    }

    function previewCharSelectedVoice(ck) {
      const val = document.getElementById(`selCharVoice_${ck}`)?.value || "";
      if (!val) return;
      if (val.startsWith("builtin:")) {
        const slug = val.replace("builtin:", "");
        const b = (STATE.charLib?.builtin_flow_voices || []).find(x => x.slug === slug);
        previewBuiltinVoiceVietnamese(slug, b?.gender || "female", b?.display_name || slug);
      } else {
        previewVoiceVietnamese(val, "", true);
      }
    }

    function openVoiceEditorForChar(ck) {
      const val = document.getElementById(`selCharVoice_${ck}`)?.value || "";
      if (val.startsWith("builtin:")) {
        const slug = val.replace("builtin:", "");
        openVoiceEditorModal("", slug, ck);
      } else {
        openVoiceEditorModal(val, "", ck);
      }
    }

    function previewEditCharModalVoice() {
      const val = document.getElementById("selEditCharVoiceKey")?.value || "";
      if (!val) return;
      if (val.startsWith("builtin:")) {
        const slug = val.replace("builtin:", "");
        const b = (STATE.charLib?.builtin_flow_voices || []).find(x => x.slug === slug);
        previewBuiltinVoiceVietnamese(slug, b?.gender || "female", b?.display_name || slug);
      } else {
        previewVoiceVietnamese(val, "", true);
      }
    }

    async function previewVoiceVietnamese(voiceKey, overrideText = "", preferFlowSample = true) {
      const voices = STATE.charLib?.voices_list || [];
      const v = voices.find(x => x.key === voiceKey);
      const customInp = document.getElementById("inpCustomVnDialogue")?.value?.trim() || "";

      // Nếu bấm "Nghe Thử Tiếng Việt" mặc định và giọng đã có sẵn file âm thanh Tiếng Việt từ Google Flow -> phát ngay lập tức!
      if (preferFlowSample && v && v.has_flow_vn_audio && v.sample_vn_abs) {
        const flowUrl = `/api/media?path=${encodeURIComponent(v.sample_vn_abs)}&t=${Date.now()}`;
        playVoiceSampleUrl(flowUrl, `${v.name} (Giọng Tiếng Việt Chuẩn Google Flow)`);
        return;
      }

      const dialogueText = overrideText || customInp || (v ? v.sample_dialogue_vn : "") || "Mấy bà ơi tin được không, hũ kho quẹt tôm khô tóp mỡ đặc sánh như này mà giá tận xưởng rẻ bèo luôn á!";
      showCharVoiceBanner(`⏳ Đang tạo âm thanh Tiếng Việt cho giọng <b>#${voiceKey}</b>: "${dialogueText.slice(0, 55)}..."`);
      const res = await apiPost("/api/characters/preview-voice-vn", {
        voice_key: voiceKey,
        dialogue_vn: dialogueText,
        force_regenerate: !preferFlowSample,
      });
      if (res && res.ok && res.audio_url) {
        playVoiceSampleUrl(res.audio_url + `&t=${Date.now()}`, `${v ? v.name : voiceKey} — "${res.dialogue_vn.slice(0, 42)}..."`);
      } else {
        alert((res && res.error) || "Không thể tạo âm thanh nghe thử Tiếng Việt.");
      }
    }

    async function previewBuiltinVoiceVietnamese(slug, gender, displayName) {
      const dialogueText = document.getElementById("inpCustomVnDialogue")?.value?.trim() || "Mấy bà ơi tin được không, sản phẩm xịn sò chuẩn tận xưởng như này mà giá đang ưu đãi cực hời luôn nha!";
      showCharVoiceBanner(`⏳ Đang đọc thử Tiếng Việt cho giọng gốc <b>${displayName}</b>...`);
      const res = await apiPost("/api/characters/preview-voice-vn", {
        voice_key: `builtin_${slug}`,
        gender: gender || "female",
        region: "north",
        tone_style: "trustworthy_expert",
        dialogue_vn: dialogueText,
        force_regenerate: true,
      });
      if (res && res.ok && res.audio_url) {
        playVoiceSampleUrl(res.audio_url + `&t=${Date.now()}`, `${displayName} (Đọc thử Tiếng Việt)`);
      }
    }

    async function previewVoiceInModalVn() {
      const vk = document.getElementById("inpVoiceKey")?.value?.trim() || "custom_preview";
      const txt = document.getElementById("inpVoiceSampleVn")?.value?.trim() || "Mấy bà ơi tin được không, sản phẩm chất lượng tận xưởng mà giá cực kỳ ưu đãi luôn nha!";
      const gender = document.getElementById("selVoiceGender")?.value || "female";
      const region = document.getElementById("selVoiceRegion")?.value || "south";
      const tone = document.getElementById("selVoiceTone")?.value || "energetic_sale";
      const statusBox = document.getElementById("modalVoiceFlowSyncStatus");
      if (statusBox) {
        statusBox.style.display = "block";
        statusBox.innerHTML = `⏳ Đang tổng hợp âm thanh Tiếng Việt cho câu mẫu: <i>"${txt}"</i>...`;
      }
      const res = await apiPost("/api/characters/preview-voice-vn", {
        voice_key: vk,
        gender,
        region,
        tone_style: tone,
        dialogue_vn: txt,
        force_regenerate: true,
      });
      if (res && res.ok && res.audio_url) {
        playVoiceSampleUrl(res.audio_url + `&t=${Date.now()}`, `${vk} (Nghe thử Tiếng Việt)`);
        if (statusBox) {
          statusBox.innerHTML = `🔊 Đang phát câu thoại mẫu Tiếng Việt! Bạn có thể bấm <b>🚀 Tự Custom Lên Google Flow & Lấy Về Kho</b> để tạo giọng chính thức trên Google Flow.`;
        }
      }
    }

    async function autoCustomVoiceOnFlowQuick(voiceKey) {
      const voices = STATE.charLib?.voices_list || [];
      const v = voices.find(x => x.key === voiceKey);
      if (!v) return;
      const customInp = document.getElementById("inpCustomVnDialogue")?.value?.trim() || v.sample_dialogue_vn || "";
      if (!confirm(`🚀 Tự động đẩy giọng "${v.name}" (#${v.key}) lên Google Flow để Custom giọng đọc mới và tải mẫu âm thanh Tiếng Việt về máy?\n\n🗣️ Câu thoại mẫu Tiếng Việt:\n"${customInp}"`)) {
        return;
      }
      showCharVoiceBanner(`⏳ Đang kết nối Google Flow (CDP) để tự động Custom giọng <b>${v.name}</b> và tải âm thanh Tiếng Việt về máy (khoảng 12-18 giây)...`);
      const res = await apiPost("/api/characters/create-flow-custom-voice", {
        key: v.key,
        name: v.name,
        gender: v.gender,
        region: v.region,
        tone_style: v.tone_style,
        voice_prompt_en: v.voice_prompt_en,
        sample_dialogue_vn: customInp,
        dialect_markers_vn: v.dialect_markers_vn,
        recommended_categories: v.recommended_categories,
        speed_wpm: v.speed_wpm,
        description: v.description,
      });
      if (res && res.ok) {
        STATE.charLib = res;
        renderCharactersTab();
        showCharVoiceBanner(`✅ ${res.flow_sync_message}`);
        if (res.audio_url) {
          playVoiceSampleUrl(res.audio_url + `&t=${Date.now()}`, `${v.name} (Vừa Custom Từ Google Flow)`);
        }
      } else {
        alert((res && res.error) || "Không thể tự động Custom trên Google Flow.");
      }
    }

    async function bindVoiceToCharacterQuick(voiceKey, charKey) {
      const res = await apiPost("/api/characters/save", {
        character: {
          key: charKey,
          default_voice: voiceKey,
          lock_voice_to_character: true,
        }
      });
      if (res && res.ok) {
        STATE.charLib = res;
        renderCharactersTab();
        showCharVoiceBanner(`🔒 Đã gắn cố định giọng đọc <b>#${voiceKey}</b> cho nhân vật <b>${charKey.toUpperCase()}</b>!`);
      }
    }

    async function scanAndSyncFlowVoices() {
      showCharVoiceBanner("⏳ Đang quét danh sách Voice UUID từ các Project Google Flow & Kho Giọng Built-in...");
      const res = await apiPost("/api/characters/scan-flow-voices", {});
      if (res && res.ok) {
        STATE.charLib = res;
        renderCharactersTab();
        showCharVoiceBanner(`✅ ${res.scan_message}`);
      }
    }

    async function runAiVoiceRecommendation() {
      const box = document.getElementById("aiVoiceRecResultBox");
      if (!box) return;
      const pid = document.getElementById("selVoiceRecProduct")?.value || "";
      const tpl = document.getElementById("selVoiceRecTemplate")?.value || "002";
      const reg = document.getElementById("selVoiceRecRegion")?.value || "auto";
      const gen = document.getElementById("selVoiceRecGender")?.value || "auto";

      box.innerHTML = `<div style="color:var(--muted); font-size:11.5px;">⏳ AI Agent đang phân tích ngành hàng sản phẩm, cấu trúc Template #${tpl} và chấm điểm các giọng đọc...</div>`;
      const res = await apiPost("/api/characters/recommend-voice", {
        product_id: pid,
        template_code: tpl,
        preferred_region: reg,
        preferred_gender: gen,
      });
      if (!res || !res.ok) {
        box.innerHTML = `<div style="color:#fca5a5;">Không thể phân tích giọng đọc.</div>`;
        return;
      }

      const recs = res.top_recommendations || [];
      const criteriaHtml = (res.ai_criteria_explanation || []).map(c => `<div style="font-size:11px; color:#cbd5e1;">${c}</div>`).join("");


      const cardsHtml = recs.slice(0, 3).map((item, idx) => {
        const v = item.voice || {};
        const rankBadge = idx === 0 ? "🏆 KHUYẾN NGHỊ SỐ 1" : (idx === 1 ? "🥈 LỰA CHỌN SỐ 2" : "🥉 LỰA CHỌN SỐ 3");
        const borderCol = idx === 0 ? "rgba(16,185,129,0.55)" : "rgba(255,255,255,0.12)";
        return `
          <div style="background:#0d1322; border:1px solid ${borderCol}; border-radius:10px; padding:10px 12px; display:flex; flex-direction:column; gap:6px;">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
              <span class="badge" style="background:${idx === 0 ? 'rgba(16,185,129,0.22)' : 'rgba(99,102,241,0.18)'}; color:${idx === 0 ? '#34d399' : '#a5b4fc'}; font-weight:800;">${rankBadge} • Độ hợp: ${item.score}%</span>
              <span style="font-size:10.5px; color:#fcd34d; font-weight:700;">${v.region_label || ''}</span>
            </div>
            <div style="font-size:13px; font-weight:800; color:#fff;">🎙️ ${v.name}</div>
            <div style="font-size:11px; color:#93c5fd;">
              ${(item.reasons || []).map(r => `• ${r}`).join("<br/>")}
            </div>
            <div style="background:#060911; border:1px solid rgba(255,255,255,0.07); border-radius:6px; padding:6px 8px; font-size:11px; color:#fde68a;">
              💬 <b>Hook mẫu (${v.region_label || 'Việt Nam'}):</b> "${item.sample_hook_vn}"
            </div>
            <div style="display:flex; gap:5px; flex-wrap:wrap; margin-top:2px;">
              <button class="btn btn-xs btn-success" style="flex:1; font-weight:800;" onclick="applyRecommendedVoiceAndCreateVideo('${pid}', '${tpl}', '${v.key}')">🎬 Áp Dụng Giọng Này & Tạo Video</button>
              <button class="btn btn-xs btn-primary" onclick="bindVoiceToCharacterQuick('${v.key}', 'nv1')">🔒 Gắn Cho NV1</button>
              <button class="btn btn-xs btn-outline" onclick="navigator.clipboard.writeText('Tạo video cho sản phẩm ID ${pid} theo template ${tpl} với giọng đọc ${v.key} (${v.name})'); showCharVoiceBanner('🤖 Đã copy lệnh gửi AI Agent kèm giọng đọc!');">🤖 Copy Lệnh AI</button>
            </div>
          </div>
        `;
      }).join("");

      box.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.08);">
          <div>
            <span style="font-size:12px; color:#94a3b8;">Sản phẩm đang phân tích:</span>
            <b style="font-size:12.5px; color:#fff; margin-left:4px;">${res.product_title}</b>
          </div>
          <span class="badge" style="background:rgba(245,158,11,0.18); color:#fbbf24; border:1px solid rgba(245,158,11,0.4); font-size:11.5px;">Ngành hàng AI nhận diện: ${res.detected_category}</span>
        </div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap:10px; margin-bottom:10px;">
          ${cardsHtml}
        </div>
        <details style="background:#0b101b; border:1px solid rgba(255,255,255,0.07); border-radius:8px; padding:7px 10px;">
          <summary style="cursor:pointer; font-size:11.5px; font-weight:700; color:#a5b4fc;">🧠 Xem 4 Nguyên Tắc AI Agent Dựa Vào Để Đưa Ra Khuyến Nghị & Viết Prompt Giọng Đọc</summary>
          <div style="margin-top:6px; display:flex; flex-direction:column; gap:4px;">${criteriaHtml}</div>
        </details>
      `;
    }

    async function applyRecommendedVoiceAndCreateVideo(pid, tplCode, voiceKey) {
      if (!pid) return alert("Vui lòng chọn 1 sản phẩm trước!");
      await bindVoiceToCharacterQuick(voiceKey, "nv1");
      showCharVoiceBanner(`🚀 Đang tạo kịch bản & chạy video cho SP <b>${pid}</b> với Template <b>#${tplCode}</b> và giọng đọc <b>#${voiceKey}</b>...`);
      const res = await apiPost("/api/products-store/create-video", {
        input: pid,
        template_name: tplCode,
        method: "auto",
        force_regenerate_prompts: true,
        auto_run: true,
      });
      if (res && res.ok) {
        STATE.currentProjectId = pid;
        switchTab("dashboard", document.querySelector(".nav-btn"));
        loadProjectDetail(pid, false);
      }
    }

    function openVoiceEditorModal(voiceKey = "", prefillFlowSlug = "", bindToCharKey = "") {
      STATE.editingVoiceForCharKey = bindToCharKey || "";
      const lib = STATE.charLib || {};
      const voices = lib.voices_list || [];
      const bVoices = lib.builtin_flow_voices || [];
      const selSlug = document.getElementById("selVoiceFlowSlug");
      if (selSlug) {
        selSlug.innerHTML = `<option value="">-- Giữ UUID hiện tại hoặc chọn từ 30 Giọng Google Flow --</option>` +
          bVoices.map(b => `<option value="${b.slug}">${b.display_name} [slug: ${b.slug}]</option>`).join("");
      }

      const statusBox = document.getElementById("modalVoiceFlowSyncStatus");
      if (statusBox) statusBox.style.display = "none";

      const v = voices.find(x => x.key === voiceKey);
      if (v) {
        document.getElementById("editVoiceModalTitle").textContent = `✏️ Chỉnh Sửa / Tự Custom Giọng Đọc Trên Flow (#${v.key})`;
        document.getElementById("inpVoiceKey").value = v.key;
        document.getElementById("inpVoiceName").value = v.name || "";
        document.getElementById("selVoiceGender").value = v.gender || "female";
        document.getElementById("selVoiceRegion").value = v.region || "north";
        document.getElementById("selVoiceTone").value = v.tone_style || "trustworthy_expert";
        if (selSlug) selSlug.value = v.flow_slug || "";
        document.getElementById("inpVoiceId").value = v.voice_id || "";
        document.getElementById("selVoiceSpeed").value = v.speed_wpm || "40-44 từ / 10s (Tốc độ Chuẩn)";
        document.getElementById("inpVoiceCategories").value = (v.recommended_categories || []).join(", ");
        document.getElementById("inpVoicePromptEn").value = v.voice_prompt_en || "";
        document.getElementById("inpVoiceSampleVn").value = v.sample_dialogue_vn || "Mấy bà ơi tin được không, hũ kho quẹt tôm khô tóp mỡ đặc sánh như này mà giá tận xưởng rẻ bèo luôn á!";
        document.getElementById("inpVoiceDialects").value = v.dialect_markers_vn || "";
        document.getElementById("inpVoiceDesc").value = v.description || "";
      } else {
        const nextIdx = voices.length + 1;
        document.getElementById("editVoiceModalTitle").textContent = `🎙️ Tạo & Tự Custom Giọng Đọc Mới Lên Google Flow`;
        document.getElementById("inpVoiceKey").value = prefillFlowSlug ? `v_${prefillFlowSlug}_vn` : `v${nextIdx}_custom_voice`;
        document.getElementById("inpVoiceName").value = prefillFlowSlug ? `Giọng Việt Nam (${prefillFlowSlug.toUpperCase()})` : `Giọng Nữ Miền Nam • Chốt Sale #${nextIdx}`;
        const bMatch = bVoices.find(b => b.slug === prefillFlowSlug);
        document.getElementById("selVoiceGender").value = bMatch ? (bMatch.gender || "female") : "female";
        document.getElementById("selVoiceRegion").value = "south";
        document.getElementById("selVoiceTone").value = "energetic_sale";
        if (selSlug) selSlug.value = prefillFlowSlug || "";
        document.getElementById("inpVoiceId").value = prefillFlowSlug || "27f51973-e290-4a38-bd7a-9d6fbe81b2f6";
        document.getElementById("selVoiceSpeed").value = "44-48 từ / 10s (Tốc độ Nhanh)";
        document.getElementById("inpVoiceCategories").value = "Đồ ăn vặt, Thời trang, Mỹ phẩm, Gia dụng";
        document.getElementById("inpVoiceDesc").value = "Giọng đọc tuỳ chỉnh vùng miền & năng lượng cho video Affiliate TikTok Shop.";
        autoGenerateVoicePromptInModal();
      }
      openModal("modalEditVoice");
    }

    function onSelectBuiltinFlowVoiceInModal() {
      const slug = document.getElementById("selVoiceFlowSlug")?.value || "";
      if (!slug) return;
      const bVoices = STATE.charLib?.builtin_flow_voices || [];
      const b = bVoices.find(x => x.slug === slug);
      if (b) {
        document.getElementById("inpVoiceId").value = b.slug;
        if (b.gender) document.getElementById("selVoiceGender").value = b.gender;
        autoGenerateVoicePromptInModal();
      }
    }

    function autoGenerateVoicePromptInModal() {
      const gender = document.getElementById("selVoiceGender")?.value || "female";
      const region = document.getElementById("selVoiceRegion")?.value || "north";
      const tone = document.getElementById("selVoiceTone")?.value || "trustworthy_expert";
      const isMale = gender === "male";

      // Tự động đồng bộ Giọng Gốc Google Flow (`selVoiceFlowSlug`) đúng giới tính Nam / Nữ
      const selSlug = document.getElementById("selVoiceFlowSlug");
      if (selSlug) {
        const curSlug = (selSlug.value || "").toLowerCase();
        const maleSlugs = ["fenrir", "puck", "alnilam", "sadachbia", "orus", "achird", "algenib", "algieba", "charon", "enceladus", "iapetus", "rasalgethi", "schedar", "umbriel", "zubenelgenubi"];
        const femaleSlugs = ["zephyr", "erinome", "leda", "laomedeia", "aoede", "kore", "callirrhoe", "autonoe", "despina", "achernar", "gacrux", "pulcherrima", "sulafat", "vindemiatrix"];
        if (isMale && (!curSlug || femaleSlugs.includes(curSlug))) {
          selSlug.value = (region === "south" || tone === "sweet_foodie") ? "puck" : (tone === "trustworthy_expert" ? "alnilam" : "fenrir");
        } else if (!isMale && (!curSlug || maleSlugs.includes(curSlug))) {
          selSlug.value = tone === "sweet_foodie" ? "leda" : (tone === "trustworthy_expert" ? "erinome" : "zephyr");
        }
      }

      const rEn = region === "south" ? "Southern Vietnamese (Saigon accent)" : (region === "central" ? "Central Vietnamese (Hue/Da Nang accent)" : "Northern Vietnamese (Hanoi accent)");
      const priceWords = region === "south"
        ? "“ba mươi cành”, “bốn trăm ka”, “năm triệu”, “hai triệu rưỡi”, “hai trăm”, “xịn xò”, “cực kỳ rẻ” and “miễn phí ship”"
        : "“ba mươi ka”, “bốn trăm ka”, “năm triệu”, “bốn triệu”, “ba triệu”, “hai triệu rưỡi”, “hai triệu”, “cực kỳ rẻ” and “miễn phí ship”";

      let deliveryEn = "energetic and authoritative TikTok Shop factory direct & QC expert sales delivery, persuasive and trustworthy, warm confident smile audible in the voice, fast moderately paced speech with crisp consonants";
      if (tone === "energetic_sale") {
        deliveryEn = "energetic TikTok Shop sales delivery, persuasive but not aggressive, warm smile audible in the voice, confident and conversational, fast moderately paced speech with crisp consonants";
      } else if (tone === "sweet_foodie") {
        deliveryEn = "cheerful and appetizing TikTok Shop food and lifestyle reviewer delivery, warm mouth-watering inflection, friendly smile audible in the voice, confident and conversational, moderately fast speech with crisp consonants";
      } else if (tone === "chill_story") {
        deliveryEn = "warm, sincere and reassuring TikTok Shop storytelling and specialty consultant delivery, gentle smile audible in the voice, smooth and conversational articulation with crisp consonants";
      }

      if (isMale) {
        document.getElementById("inpVoicePromptEn").value =
          `Vietnamese male commercial presenter, young adult masculine voice, bright and energetic baritone-tenor pitch, clear forward chest projection, natural ${rEn} pronunciation, ${deliveryEn}. Emphasize important words and prices such as ${priceWords}. Use short natural pauses after each price, slight playful disbelief when saying “không phải”, and an excited reassuring lift at the end of promotional sentences. Keep the same male voice, masculine pitch, accent, loudness, speaking speed and emotional style across every clip. No announcer voice, no radio voice, no singing, no whispering, no shouting, no female resonance, no high-pitched female voice, no English accent, no robotic delivery.`;
      } else {
        document.getElementById("inpVoicePromptEn").value =
          `Vietnamese female commercial presenter, young adult voice, bright and friendly, mid-to-high pitch, clear forward projection, natural ${rEn} pronunciation, ${deliveryEn}. Emphasize important words and prices such as ${priceWords}. Use short natural pauses after each price, slight playful disbelief when saying “không phải”, and an excited reassuring lift at the end of promotional sentences. Keep the same female voice, pitch, accent, loudness, speaking speed and emotional style across every clip. No announcer voice, no radio voice, no singing, no whispering, no shouting, no male resonance, no English accent, no robotic delivery.`;
      }

      if (region === "south") {
        document.getElementById("inpVoiceDialects").value = isMale
          ? "anh chị em ơi, xịn xò từng chi tiết, ba mươi cành, miễn phí ship, hốt lẹ liền tay nghen"
          : "mấy bà ơi, cả nhà nha, nghen, thiệt sự cuốn xỉu, hốt lẹ liền tay";
        document.getElementById("inpVoiceSampleVn").value = isMale
          ? "Anh chị em ơi xả kho tận xưởng chỉ ba mươi cành miễn phí ship tới tận nhà! Xịn xò từng chi tiết, hốt lẹ liền tay nghen!"
          : "Mấy bà ơi tin được không, hũ kho quẹt tôm khô tóp mỡ đặc sánh như này mà giá tận xưởng rẻ bèo luôn á!";
      } else if (region === "central") {
        document.getElementById("inpVoiceDialects").value = "mọi người ơi, hương vị quê nhà đậm đà khó quên, thương mời cả nhà";
        document.getElementById("inpVoiceSampleVn").value = "Mọi người ơi, hương vị đặc sản quê nhà đậm đà khó quên, nguyên liệu tươi sạch làm thủ công tỉ mỉ, thương mời cả nhà!";
      } else {
        document.getElementById("inpVoiceDialects").value = "các bác ơi, mọi người nhé, đấy ạ, chuẩn chỉnh tận xưởng, miễn phí ship, săn ngay";
        document.getElementById("inpVoiceSampleVn").value = "30k miễn phí ship tới tận nhà cho nguyên một thắt lưng nam tặng thêm đồng hồ này. Ở đâu bán cái giá đó thì em cũng đến";
      }
    }

    function _collectVoiceModalPayload() {
      return {
        key: document.getElementById("inpVoiceKey").value.trim(),
        name: document.getElementById("inpVoiceName").value.trim(),
        gender: document.getElementById("selVoiceGender").value,
        region: document.getElementById("selVoiceRegion").value,
        tone_style: document.getElementById("selVoiceTone").value,
        flow_slug: document.getElementById("selVoiceFlowSlug").value,
        voice_id: document.getElementById("inpVoiceId").value.trim(),
        speed_wpm: document.getElementById("selVoiceSpeed").value,
        recommended_categories: document.getElementById("inpVoiceCategories").value.trim(),
        voice_prompt_en: document.getElementById("inpVoicePromptEn").value.trim(),
        sample_dialogue_vn: document.getElementById("inpVoiceSampleVn").value.trim(),
        dialect_markers_vn: document.getElementById("inpVoiceDialects").value.trim(),
        description: document.getElementById("inpVoiceDesc").value.trim(),
      };
    }

    async function submitSaveVoiceModal() {
      const payload = _collectVoiceModalPayload();
      const res = await apiPost("/api/characters/save-voice", payload);
      if (res && res.ok) {
        STATE.charLib = res;
        if (STATE.editingVoiceForCharKey) {
          await bindVoiceToCharacterQuick(payload.key, STATE.editingVoiceForCharKey);
          populateEditCharVoiceDropdown(payload.key);
          onEditCharVoiceKeyChange();
        }
        closeModal("modalEditVoice");
        renderCharactersTab();
        showCharVoiceBanner(`✅ Đã lưu giọng đọc <b>${payload.name}</b>!`);
      }
    }

    async function submitCreateCustomVoiceOnFlowModal() {
      const payload = _collectVoiceModalPayload();
      if (!payload.key || !payload.name) {
        return alert("Vui lòng nhập Mã Giọng Đọc và Tên Hiển Thị!");
      }
      const btn = document.getElementById("btnAutoCustomVoiceOnFlowModal");
      const statusBox = document.getElementById("modalVoiceFlowSyncStatus");
      if (btn) {
        btn.disabled = true;
        btn.textContent = "⏳ Đang Tự Custom Trên Google Flow (15s)...";
      }
      if (statusBox) {
        statusBox.style.display = "block";
        statusBox.innerHTML = `🚀 Đang điều khiển trình duyệt Google Flow điền lời thoại Tiếng Việt <i>"${payload.sample_dialogue_vn}"</i> + Chỉ dẫn giọng đọc, bấm <b>Xem trước</b>, bắt luồng âm thanh WAV/MP3 và bấm <b>Lưu giọng nói mới</b>...`;
      }
      const res = await apiPost("/api/characters/create-flow-custom-voice", payload);
      if (btn) {
        btn.disabled = false;
        btn.textContent = "🚀 Tự Custom Lên Google Flow & Lấy Về Kho";
      }
      if (res && res.ok) {
        STATE.charLib = res;
        if (res.created_voice && res.created_voice.voice_id) {
          document.getElementById("inpVoiceId").value = res.created_voice.voice_id;
        }
        if (STATE.editingVoiceForCharKey) {
          await bindVoiceToCharacterQuick(payload.key, STATE.editingVoiceForCharKey);
          populateEditCharVoiceDropdown(payload.key);
          onEditCharVoiceKeyChange();
        }
        if (statusBox) {
          statusBox.innerHTML = `✅ <b>Thành công!</b> ${res.flow_sync_message}<br/>🆔 Flow Voice UUID: <code style="color:#34d399;">${res.created_voice?.voice_id || ''}</code> — Đã tải mẫu âm thanh Tiếng Việt về máy!`;
        }
        renderCharactersTab();
        showCharVoiceBanner(`✅ ${res.flow_sync_message}`);
        if (res.audio_url) {
          playVoiceSampleUrl(res.audio_url + `&t=${Date.now()}`, `${payload.name} (Vừa Custom Từ Google Flow)`);
        }
      } else {
        if (statusBox) {
          statusBox.innerHTML = `❌ Lỗi: ${(res && res.error) || 'Không thể kết nối Google Flow.'}`;
        }
      }
    }

    async function deleteVoiceProfile(vk) {
      if (!confirm(`Xoá giọng đọc #${vk} khỏi thư viện?`)) return;
      const res = await apiPost("/api/characters/delete-voice", { voice_key: vk });
      if (res && res.ok) {
        STATE.charLib = res;
        renderCharactersTab();
        showCharVoiceBanner(`🗑️ Đã xoá giọng đọc #${vk}.`);
      } else if (res && res.error) {
        alert(res.error);
      }
    }

    async function saveGlobalCharacterSettings() {
      const vpc = parseInt(document.getElementById("selGlobalVideosPerChar").value || "3", 10);
      const imgModel = document.getElementById("selGlobalImgModel").value || "nano_banana";
      const sheetTpl = document.getElementById("selGlobalSheetTemplate").value || "sheet_6panel_studio";
      const res = await apiPost("/api/characters/save", {
        default_videos_per_character: vpc,
        default_image_model: imgModel,
        default_sheet_template_id: sheetTpl,
        apply_to_all_characters: true,
      });
      if (res && res.ok) {
        STATE.charLib = res;
        renderCharactersTab();
        showCharVoiceBanner(`✅ Đã lưu cài đặt chung: <b>${vpc} video / nhân vật / sản phẩm</b>!`);
      }
    }

    async function saveSingleCharacterQuick(ck) {
      const vpc = parseInt(document.getElementById(`selCharVpc_${ck}`)?.value || "3", 10);
      const model = document.getElementById(`selCharModel_${ck}`)?.value || "nano_banana";
      const sheetTpl = document.getElementById(`selCharSheetTpl_${ck}`)?.value || "sheet_6panel_studio";
      const enabled = !!document.getElementById(`chkCharEnabled_${ck}`)?.checked;
      const rawVoiceVal = document.getElementById(`selCharVoice_${ck}`)?.value || ck;
      const lockVoice = !!document.getElementById(`chkCharLockVoice_${ck}`)?.checked;

      const charPayload = {
        key: ck,
        enabled: enabled,
        videos_per_character: vpc,
        preferred_image_model: model,
        sheet_template_id: sheetTpl,
        default_voice: rawVoiceVal,
        lock_voice_to_character: lockVoice,
      };
      if (rawVoiceVal.startsWith("builtin:")) {
        const slug = rawVoiceVal.replace("builtin:", "");
        const b = (STATE.charLib?.builtin_flow_voices || []).find(x => x.slug === slug);
        charPayload.voice_id = slug;
        charPayload.voice_name = b ? `${b.display_name} (${slug})` : slug;
      }

      const res = await apiPost("/api/characters/save", { character: charPayload });
      if (res && res.ok) {
        STATE.charLib = res;
        renderCharactersTab();
        showCharVoiceBanner(`✅ Đã lưu nhân vật <b>${ck.toUpperCase()}</b> và gắn giọng đọc <b>${rawVoiceVal}</b> (${vpc} video / sản phẩm)!`);
      }
    }

    function populateEditCharVoiceDropdown(selectedKey = "") {
      const sel = document.getElementById("selEditCharVoiceKey");
      if (!sel) return;
      const voices = STATE.charLib?.voices_list || [];
      const bVoices = STATE.charLib?.builtin_flow_voices || [];
      let matchedCustom = false;
      const customOpts = voices.map(v => {
        const isSel = v.key === selectedKey;
        if (isSel) matchedCustom = true;
        return `<option value="${v.key}" ${isSel ? 'selected' : ''}>[${v.gender === 'male' ? 'Nam' : 'Nữ'} • ${v.region_label || v.region}] ${v.name}</option>`;
      }).join("");
      const builtinOpts = bVoices.map(b => {
        const bVal = `builtin:${b.slug}`;
        const isSel = !matchedCustom && (selectedKey === bVal || selectedKey === b.slug);
        return `<option value="${bVal}" ${isSel ? 'selected' : ''}>[${b.gender === 'male' ? 'Nam' : 'Nữ'} • Flow Gốc] ${b.display_name} (${b.slug})</option>`;
      }).join("");
      sel.innerHTML = `
        <optgroup label="🌟 Giọng Việt Nam Đã Custom (${voices.length} Giọng)">${customOpts}</optgroup>
        <optgroup label="🌐 30 Giọng Gốc Google Flow (Built-in)">${builtinOpts}</optgroup>
      `;
    }

    function onEditCharVoiceKeyChange() {
      const vk = document.getElementById("selEditCharVoiceKey")?.value || "";
      if (vk.startsWith("builtin:")) {
        const slug = vk.replace("builtin:", "");
        const b = (STATE.charLib?.builtin_flow_voices || []).find(x => x.slug === slug);
        document.getElementById("inpEditCharVoiceId").value = slug;
        document.getElementById("inpEditCharVoiceName").value = b ? `${b.display_name} (${slug})` : slug;
        return;
      }
      const v = (STATE.charLib?.voices_list || []).find(x => x.key === vk);
      if (v) {
        document.getElementById("inpEditCharVoiceId").value = v.voice_id || "";
        document.getElementById("inpEditCharVoiceName").value = v.name || "";
      }
    }

    function openAddCharacterModal() {
      document.getElementById("editCharModalTitle").textContent = "➕ Thêm Nhân Vật Mới & Gắn Giọng Đọc Cố Định";
      const nextNum = ((STATE.charLib?.characters || []).length) + 1;
      document.getElementById("inpEditCharKey").value = `nv${nextNum}`;
      document.getElementById("inpEditCharName").value = `Nhân Vật ${nextNum}`;
      document.getElementById("inpEditCharUuid").value = "";
      document.getElementById("inpEditCharProjId").value = "932bc2a1-07ea-4199-b147-80ab0018d41c";
      populateEditCharVoiceDropdown("v3_nu_nam_foodie");
      onEditCharVoiceKeyChange();
      document.getElementById("chkEditCharLockVoice").checked = true;
      document.getElementById("selEditCharVpc").value = "3";
      document.getElementById("inpEditCharAppearance").value = "young Vietnamese woman, friendly confident smile, identical face";
      document.getElementById("inpEditCharFile").value = "";
      openModal("modalEditChar");
    }

    function openEditCharacterModal(ck) {
      const c = (STATE.charLib?.characters || []).find(x => x.key === ck);
      if (!c) return;
      document.getElementById("editCharModalTitle").textContent = `✏️ Chỉnh Sửa Nhân Vật (${ck.toUpperCase()})`;
      document.getElementById("inpEditCharKey").value = c.key;
      document.getElementById("inpEditCharName").value = c.name || "";
      document.getElementById("inpEditCharUuid").value = c.character_id || "";
      document.getElementById("inpEditCharProjId").value = c.project_id || "";
      populateEditCharVoiceDropdown(c.default_voice || ck);
      document.getElementById("inpEditCharVoiceId").value = c.voice_id || "";
      document.getElementById("inpEditCharVoiceName").value = c.voice_name || "";
      document.getElementById("chkEditCharLockVoice").checked = c.lock_voice_to_character !== false;
      document.getElementById("selEditCharVpc").value = String(c.videos_per_character || 3);
      document.getElementById("inpEditCharAppearance").value = c.appearance_en || "";
      document.getElementById("inpEditCharFile").value = "";
      openModal("modalEditChar");
    }

    function fileToBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    }

    async function submitSaveCharacterModal() {
      const ck = document.getElementById("inpEditCharKey").value.trim().toLowerCase();
      const fileInp = document.getElementById("inpEditCharFile");
      let b64 = "";
      if (fileInp && fileInp.files && fileInp.files[0]) {
        b64 = await fileToBase64(fileInp.files[0]);
      }
      const res = await apiPost("/api/characters/save", {
        character: {
          key: ck,
          name: document.getElementById("inpEditCharName").value.trim(),
          character_id: document.getElementById("inpEditCharUuid").value.trim(),
          project_id: document.getElementById("inpEditCharProjId").value.trim(),
          default_voice: document.getElementById("selEditCharVoiceKey").value,
          lock_voice_to_character: !!document.getElementById("chkEditCharLockVoice").checked,
          voice_id: document.getElementById("inpEditCharVoiceId").value.trim(),
          voice_name: document.getElementById("inpEditCharVoiceName").value.trim(),
          videos_per_character: parseInt(document.getElementById("selEditCharVpc").value || "3", 10),
          appearance_en: document.getElementById("inpEditCharAppearance").value.trim(),
          uploaded_image_base64: b64 || undefined,
        }
      });
      if (res && res.ok) {
        STATE.charLib = res;
        closeModal("modalEditChar");
        renderCharactersTab();
        showCharVoiceBanner(`✅ Đã lưu nhân vật <b>${ck.toUpperCase()}</b> và gắn cố định giọng đọc!`);
      }
    }

    async function deleteSingleCharacter(ck) {
      if (!confirm(`Xoá nhân vật ${ck.toUpperCase()} khỏi thư viện?`)) return;
      const res = await apiPost("/api/characters/delete", { char_key: ck });
      if (res && res.ok) {
        STATE.charLib = res;
        renderCharactersTab();
      }
    }

    function openSheetTemplateEditor(tplId = "") {
      const templates = STATE.charLib?.sheet_templates || [];
      const t = templates.find(x => x.id === tplId) || {};
      document.getElementById("inpTplId").value = t.id || `sheet_mau_${templates.length + 1}`;
      document.getElementById("inpTplName").value = t.name || `Mẫu ${templates.length + 1}: Character Sheet Tuỳ Chỉnh`;
      document.getElementById("inpTplDesc").value = t.description || "";
      document.getElementById("inpTplSheetPrompt").value = t.character_sheet_prompt || (templates[0]?.character_sheet_prompt || "");
      document.getElementById("inpTplProdPrompt").value = t.product_with_character_prompt || (templates[0]?.product_with_character_prompt || "");
      document.getElementById("inpTplSampleFile").value = "";
      openModal("modalEditSheetTpl");
    }

    async function submitSaveSheetTemplate() {
      const fileInp = document.getElementById("inpTplSampleFile");
      let b64 = "";
      if (fileInp && fileInp.files && fileInp.files[0]) {
        b64 = await fileToBase64(fileInp.files[0]);
      }
      const res = await apiPost("/api/characters/save-sheet-template", {
        id: document.getElementById("inpTplId").value.trim(),
        name: document.getElementById("inpTplName").value.trim(),
        description: document.getElementById("inpTplDesc").value.trim(),
        character_sheet_prompt: document.getElementById("inpTplSheetPrompt").value.trim(),
        product_with_character_prompt: document.getElementById("inpTplProdPrompt").value.trim(),
        uploaded_sample_base64: b64 || undefined,
      });
      if (res && res.ok) {
        STATE.charLib = res;
        closeModal("modalEditSheetTpl");
        renderCharactersTab();
      }
    }

    function openCharImageGenModal(charKey = "nv1", mode = "character_sheet", tplId = "") {
      const lib = STATE.charLib;
      if (!lib) return;
      const chars = lib.characters || [];
      const templates = lib.sheet_templates || [];

      const selChar = document.getElementById("selGenCharKey");
      selChar.innerHTML = chars.map(c => `<option value="${c.key}">${c.key.toUpperCase()} — ${c.name}</option>`).join("");
      if (charKey) selChar.value = charKey;

      const selTpl = document.getElementById("selGenSheetTemplate");
      selTpl.innerHTML = templates.map(t => `<option value="${t.id}">${t.name}</option>`).join("");
      if (tplId) selTpl.value = tplId;

      document.getElementById("selGenMode").value = mode || "character_sheet";
      const curChar = chars.find(x => x.key === (selChar.value || "nv1")) || chars[0] || {};
      const chosenTpl = templates.find(x => x.id === (selTpl.value || "")) || templates[0] || {};
      document.getElementById("selGenModel").value = curChar.preferred_image_model || lib.default_image_model || "nano_banana";
      document.getElementById("inpGenAppearance").value = (tplId && chosenTpl.default_character_example)
        ? chosenTpl.default_character_example
        : (curChar.appearance_en || "young Vietnamese woman, shoulder-length layered black hair, friendly smile");
      document.getElementById("genImgStatusText").textContent = "";
      document.getElementById("genImgResultBox").innerHTML = "";
      onGenModeOrTplChange();
      openModal("modalCharGenerator");
    }

    function onGenModeOrTplChange() {
      const lib = STATE.charLib;
      if (!lib) return;
      const mode = document.getElementById("selGenMode").value;
      const tplId = document.getElementById("selGenSheetTemplate").value;
      const charKey = document.getElementById("selGenCharKey").value;
      const curChar = (lib.characters || []).find(x => x.key === charKey) || {};
      const tpl = (lib.sheet_templates || []).find(x => x.id === tplId) || (lib.sheet_templates || [])[0] || {};
      const appInput = document.getElementById("inpGenAppearance");
      if (STATE._lastGenTplId !== tplId && tpl.default_character_example) {
        appInput.value = tpl.default_character_example;
      }
      STATE._lastGenTplId = tplId;
      const desc = (appInput.value || tpl.default_character_example || curChar.appearance_en || "young Vietnamese woman").trim();

      let p = "";
      if (mode === "product_ref") {
        p = (tpl.product_with_character_prompt || "")
          .replace("{character_description}", desc)
          .replace("{outfit_en}", "wearing a polite professional blazer over a collared shirt and dark trousers")
          .replace("{setting_en}", "standing behind a worktable in a modern factory inspection room");
      } else {
        p = (tpl.character_sheet_prompt || "").replace("{character_description}", desc);
      }
      document.getElementById("inpGenFinalPrompt").value = p;
    }

    async function submitGenerateCharOrProdImage() {
      const mode = document.getElementById("selGenMode").value;
      const model = document.getElementById("selGenModel").value;
      const tplId = document.getElementById("selGenSheetTemplate").value;
      const charKey = document.getElementById("selGenCharKey").value;
      const pid = document.getElementById("inpGenPid").value.trim();
      const appearance = document.getElementById("inpGenAppearance").value.trim();
      const customPrompt = document.getElementById("inpGenFinalPrompt").value.trim();

      document.getElementById("genImgStatusText").textContent = `⏳ Đang tạo ảnh bằng model ${model === 'chatgpt' ? 'ChatGPT Image' : 'Nano Banana 2.1 (2K)'}...`;
      const res = await apiPost("/api/characters/generate-image", {
        mode,
        model,
        sheet_template_id: tplId,
        char_key: charKey,
        pid,
        appearance_en: appearance,
        custom_prompt: customPrompt,
      });
      if (!res || !res.ok) {
        document.getElementById("genImgStatusText").textContent = `❌ Lỗi: ${(res && res.error) || 'Không tạo được ảnh'}`;
        return;
      }
      document.getElementById("genImgStatusText").textContent = `✅ Đã tạo thành công bằng ${res.model_used}!`;
      document.getElementById("genImgResultBox").innerHTML = `
        <div style="background:#090d16; border:1px solid #10b981; border-radius:8px; padding:10px; display:flex; gap:12px; align-items:center;">
          <img src="/api/media?path=${encodeURIComponent(res.image_path)}" style="width:180px; max-height:220px; object-fit:contain; border-radius:6px; background:#000;" />
          <div style="display:flex; flex-direction:column; gap:6px;">
            <div style="font-weight:700; color:#34d399;">🎉 Ảnh mới đã được lưu!</div>
            <div style="font-size:11px; color:var(--muted);">Đường dẫn: <code>${res.image_path}</code></div>
            <div style="display:flex; gap:8px;">
              <button class="btn btn-xs btn-success" onclick="openFolderEncoded('${encodeURIComponent(res.image_path)}')">📂 Mở File Trong Explorer</button>
            </div>
          </div>
        </div>
      `;
      await loadCharacterLibrary();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TAB MỚI: CHỢ TEMPLATE & ROLE SKILL (MÃ SỐ ĐỘC NHẤT 001, 002, 003 + 1 DEMO VIDEO 60FPS)
    // ═══════════════════════════════════════════════════════════════════════
    STATE.templateMarketFilter = "all";
    STATE.curModalTemplateCodeOrName = "001";
    STATE.curModalDocKey = "ROLE_SKILL.md";

    function showMarketBanner(msg, isErr = false) {
      const el = document.getElementById("marketStatusBanner");
      if (!el) return;
      el.style.display = msg ? "block" : "none";
      el.style.color = isErr ? "#fca5a5" : "#a5f3fc";
      el.style.borderColor = isErr ? "rgba(239,68,68,0.45)" : "var(--border-light)";
      el.innerHTML = msg;
    }

    function updateMarketAiCommandPreview() {
      const urlVal = (document.getElementById("inpMarketQuickUrl")?.value || "").trim() || "<Link_hoặc_ID_Sản_Phẩm>";
      const codeVal = (document.getElementById("selMarketQuickCode")?.value || "001").trim();
      const prevEl = document.getElementById("txtMarketAiCmdPreview");
      if (prevEl) {
        prevEl.textContent = `Tạo các sản phẩm cho ID ${urlVal} theo template ${codeVal}`;
      }
    }

    function copyMarketAiCommand(customCode = "") {
      const urlVal = (document.getElementById("inpMarketQuickUrl")?.value || "").trim() || "<Link_hoặc_ID_Sản_Phẩm>";
      const codeVal = customCode || (document.getElementById("selMarketQuickCode")?.value || "001").trim();
      const cmd = `Tạo các sản phẩm cho ID ${urlVal} theo template ${codeVal}`;
      navigator.clipboard.writeText(cmd);
      showMarketBanner(`📋 Đã copy lệnh gửi AI Agent: <code>${cmd}</code>`);
    }

    async function runQuickFromMarketplace(overrideCode = "") {
      const selMkt = document.getElementById("selMarketQuickCode");
      if (overrideCode && selMkt) {
        selMkt.value = overrideCode;
        updateMarketAiCommandPreview();
      }
      const inpEl = document.getElementById("inpMarketQuickUrl");
      const rawUrl = (inpEl?.value || "").trim();
      const tplCode = overrideCode || (selMkt?.value || "001").trim();
      const vpc = parseInt(document.getElementById("selMarketQuickVpc")?.value || "3", 10);

      if (!rawUrl) {
        if (inpEl) {
          inpEl.focus();
          inpEl.style.borderColor = "#f59e0b";
          setTimeout(() => { inpEl.style.borderColor = ""; }, 2000);
        }
        showMarketBanner(`✨ Đã chọn <b>Mã Template #${tplCode}</b>! Vui lòng dán <b>Link hoặc ID sản phẩm TikTok</b> vào ô bên trên rồi bấm <b>🎬 Tạo Video Ngay Trên UI</b> (hoặc Enter).`);
        return;
      }

      showMarketBanner(`🚀 Đang tự động Crawl sản phẩm <b>${rawUrl}</b>, sinh kịch bản theo <b>Template #${tplCode}</b> và khởi chạy render 1080p 60 FPS...`);
      const res = await apiPost("/api/products-store/create-video", {
        input: rawUrl,
        template_name: tplCode,
        method: "auto",
        videos_per_character: vpc,
        force_regenerate_prompts: true,
        auto_run: true,
      });
      if (!res || !res.ok) {
        showMarketBanner(`❌ Lỗi khởi tạo video với Template #${tplCode}: ${(res && res.error) || 'Không xác định'}`, true);
        return;
      }
      showMarketBanner(`🎉 Đã khởi tạo thành công <b>${res.videos_count} kịch bản (Mã #${res.template_code || tplCode} — ${res.template_name})</b> cho SP <b>${res.pid}</b> và bắt đầu chạy đa luồng 60 FPS!`);
      await loadProductsStore(false);
      await refreshAll(false);
      STATE.currentProjectId = res.pid;
      switchTab("dashboard", document.getElementById("navBtn-dashboard"));
      loadProjectDetail(res.pid, false);
    }

    async function loadTemplatesMarketplace(forceRefresh = false) {
      const res = await apiGet("/api/templates");
      if (res && res.ok) {
        STATE.videoTemplates = res.templates || [];
        STATE.templateRootDir = res.template_root_dir || "Template";
        populateTemplateDropdowns(STATE.videoTemplates);
      }
      renderTemplatesMarketplace();
      loadFashionMotionStudio(false);
      if (forceRefresh) {
        showMarketBanner(`✅ Đã làm mới Chợ Template: ${(STATE.videoTemplates || []).length} Template sẵn sàng.`);
      }
    }

    function setTemplateMarketFilter(flt, btnEl) {
      STATE.templateMarketFilter = flt || "all";
      const bar = document.getElementById("tplCategoryFilterBar");
      if (bar) {
        bar.querySelectorAll(".btn-filter").forEach(b => b.classList.remove("active"));
      }
      if (btnEl) btnEl.classList.add("active");
      renderTemplatesMarketplace();
      if (flt === "004") {
        switchTab("fashion", document.getElementById("navBtn-fashion"));
      }
    }

    function useTemplateFromMarketplace(codeOrFolder) {
      if (String(codeOrFolder).includes("004") || String(codeOrFolder).toLowerCase().includes("fashion")) {
        switchTab("fashion", document.getElementById("navBtn-fashion"));
        loadFashionMotionStudio(true);
        return;
      }
      const selQuick = document.getElementById("selQuickTemplate");
      const selMkt = document.getElementById("selMarketQuickCode");
      populateTemplateDropdowns(STATE.videoTemplates || []);
      if (selQuick) selQuick.value = codeOrFolder;
      if (selMkt) selMkt.value = codeOrFolder;
      updateMarketAiCommandPreview();
      runQuickFromMarketplace(codeOrFolder);
    }

    async function openSampleProductInStudio(pid, folderName) {
      STATE.currentProjectId = pid;
      switchTab("dashboard", document.getElementById("navBtn-dashboard"));
      await loadProjectDetail(pid, false);
    }

    function renderTemplatesMarketplace() {
      const box = document.getElementById("templatesMarketGrid");
      if (!box) return;
      const allTpls = STATE.videoTemplates || [];
      const cntEl = document.getElementById("cntTplAll");
      if (cntEl) cntEl.textContent = allTpls.length;

      const flt = (STATE.templateMarketFilter || "all").toLowerCase();
      const filtered = allTpls.filter(t => {
        if (flt === "all") return true;
        return (
          String(t.code || "").toLowerCase() === flt ||
          (t.id || "").toLowerCase().includes(flt) ||
          (t.folder_name || "").toLowerCase().includes(flt)
        );
      });

      if (!filtered.length) {
        box.innerHTML = `<div class="card" style="grid-column:1/-1; text-align:center; color:var(--muted); padding:24px;">Chưa có Template phù hợp bộ lọc.</div>`;
        return;
      }

      box.innerHTML = filtered.map((t, idx) => {
        const code = t.code || String(idx + 1).padStart(3, "0");
        const tid = (t.id || `tpl_${code}`).replace(/[^a-zA-Z0-9_]/g, "_");
        const primaryVid = t.primary_demo_video || (t.demo_videos && t.demo_videos[0]) || null;
        const scenes = t.scene_breakdown || [];
        const highlights = t.highlights || [];
        const sampleProds = t.sample_products || [];
        const firstSample = sampleProds[0] || null;
        const aiCmdSample = `Tạo các sản phẩm cho ID ${firstSample ? firstSample.product_id : '<ID_SP>'} theo template ${code}`;

        const scenesCompactHtml = scenes.slice(0, 3).map(sc => `
          <div style="background:#080c15; border:1px solid var(--border); border-radius:6px; padding:6px 8px;">
            <div style="font-size:10.5px; font-weight:800; color:#fde68a;">🎬 ${sc.title}</div>
            <div style="font-size:10px; color:var(--muted); margin-top:2px; line-height:1.3; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">${sc.purpose || ''}</div>
          </div>
        `).join("");

        return `
          <div class="card" style="margin:0; padding:13px; display:flex; flex-direction:column; justify-content:space-between; gap:10px; border-color:rgba(245,158,11,0.42); background:linear-gradient(180deg, rgba(18,23,36,0.98), rgba(10,14,23,0.99)); box-shadow:0 8px 24px rgba(0,0,0,0.35);">
            <div>
              <!-- Dòng 1: Mã số Template độc nhất (#001, #002, #003) + Tier Badge + Giá -->
              <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; margin-bottom:7px; flex-wrap:wrap;">
                <div style="display:flex; align-items:center; gap:6px;">
                  <span onclick="navigator.clipboard.writeText('template ${code}'); showMarketBanner('📋 Đã copy mã: <b>template ${code}</b>');"
                        title="Bấm để copy mã Template #${code}"
                        style="cursor:pointer; background:linear-gradient(135deg, #f59e0b, #d97706); color:#050811; font-weight:900; font-size:12px; padding:3px 10px; border-radius:6px; letter-spacing:0.5px; box-shadow:0 2px 8px rgba(245,158,11,0.35);">
                    🏷️ MÃ #${code}
                  </span>
                  <span class="badge" style="background:rgba(99,102,241,0.18); color:#a5b4fc; border:1px solid rgba(99,102,241,0.4); font-size:10px;">${t.category || 'TikTok Affiliate'}</span>
                </div>
                <span class="badge badge-done" style="font-size:10px; padding:2px 8px;">💎 ${t.price_label || 'Đã Kích Hoạt'}</span>
              </div>

              <!-- Dòng 2: Tên Template & Mô tả tóm tắt -->
              <div style="font-size:14px; font-weight:800; color:#fff; line-height:1.3;">
                Template ${code} — ${t.name}
              </div>
              <div style="font-size:11px; color:var(--muted); margin-top:4px; line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;" title="${(t.description || '').replace(/"/g, '&quot;')}">
                ${t.description || ''}
              </div>

              <!-- Dòng 3: Thông số chuẩn 60 FPS + Sub Karaoke + Role Skill -->
              <div style="display:flex; gap:5px; flex-wrap:wrap; margin-top:7px;">
                <span class="badge badge-run" style="font-size:9.8px;">📐 ${t.scenes_per_video} Cảnh × ${t.scene_duration_sec}s (${t.video_aspect || '9:16'})</span>
                <span class="badge" style="background:rgba(16,185,129,0.16); color:#34d399; border:1px solid rgba(16,185,129,0.4); font-size:9.8px;">🎬 ${t.video_resolution || '1080p • 60 FPS'}</span>
                <span class="badge" style="background:rgba(245,158,11,0.16); color:#fcd34d; border:1px solid rgba(245,158,11,0.4); font-size:9.8px;">🔤 Có Sub Karaoke</span>
                <span class="badge" style="background:rgba(6,182,212,0.16); color:#67e8f9; border:1px solid rgba(6,182,212,0.4); font-size:9.8px;">🧠 Kèm Role Skill (.MD)</span>
              </div>

              <!-- Dòng 4: Bố cục 2 cột gọn trong Card: [Trái: 1 Video Demo Hoàn Thiện 9:16] | [Phải: Điểm mạnh & Kịch bản 3 Cảnh] -->
              <div style="display:grid; grid-template-columns: 162px 1fr; gap:10px; margin-top:10px; align-items:start;">
                <!-- Cột Trái: 01 Video Demo Hoàn Thiện Chất Lượng Tốt Nhất -->
                <div style="background:#060911; border:1px solid rgba(245,158,11,0.45); border-radius:8px; padding:5px; display:flex; flex-direction:column; gap:5px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:9.5px; font-weight:800; color:#fbbf24;">▶️ DEMO FINAL 60FPS</span>
                    ${primaryVid ? `<button class="btn btn-xs btn-outline" style="padding:1px 5px; font-size:9px;" onclick="openVerticalVideoModal('${encodeURIComponent(primaryVid.path || '')}', '', '', 'Template #${code} — ${t.folder_name.replace(/'/g, "\\'")}')">📱 Phóng to</button>` : ''}
                  </div>
                  <div style="width:100%; aspect-ratio:9/16; background:#000; border-radius:6px; overflow:hidden; position:relative;">
                    ${primaryVid ? `
                      <video id="tplDemoVid_${tid}" controls preload="metadata" style="width:100%; height:100%; object-fit:cover; background:#000;" src="${primaryVid.url}"></video>
                    ` : `<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:var(--muted); font-size:10px;">Chưa có video</div>`}
                  </div>
                  <div style="font-size:9.5px; color:#fde68a; font-weight:700; text-align:center; line-height:1.25; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
                    ${t.demo_video_caption || (primaryVid ? primaryVid.label : 'Video Demo 1080p 60FPS')}
                  </div>
                </div>

                <!-- Cột Phải: Tóm tắt Role Skill & 3 Phân cảnh -->
                <div style="display:flex; flex-direction:column; gap:6px;">
                  <div style="background:rgba(16,185,129,0.07); border:1px solid rgba(16,185,129,0.28); border-radius:6px; padding:6px 8px;">
                    <div style="font-size:10px; font-weight:800; color:#34d399; margin-bottom:3px;">✨ ĐẶC ĐIỂM ROLE SKILL #${code}:</div>
                    ${highlights.slice(0, 3).map(h => `<div style="font-size:10px; color:#e2e8f0; line-height:1.35; margin-bottom:2px;">• ${h}</div>`).join("")}
                  </div>
                  <div style="display:flex; flex-direction:column; gap:4px;">
                    ${scenesCompactHtml}
                  </div>
                </div>
              </div>
            </div>

            <!-- Dòng 5: Hộp Lệnh AI Agent & Cụm Nút Thao Tác Trực Tiếp -->
            <div style="display:flex; flex-direction:column; gap:7px; padding-top:8px; border-top:1px solid var(--border);">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; background:#070a12; border:1px dashed rgba(99,102,241,0.4); border-radius:6px; padding:5px 8px;">
                <span style="font-size:10px; color:#c7d2fe; font-family:Consolas, monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${aiCmdSample}">
                  🤖 <b>AI Agent:</b> "${aiCmdSample}"
                </span>
                <button class="btn btn-xs btn-outline" style="padding:2px 7px; font-size:10px; flex-shrink:0;" onclick="copyMarketAiCommand('${code}')">📋 Copy Lệnh</button>
              </div>

              <div style="display:grid; grid-template-columns: 1.2fr 1.1fr auto; gap:6px;">
                <button class="btn btn-xs btn-success" style="padding:7px 8px; font-size:11px; font-weight:800; justify-content:center;" onclick="useTemplateFromMarketplace('${code}')">
                  🎬 Dùng Template #${code}
                </button>
                <button class="btn btn-xs btn-amber" style="padding:7px 8px; font-size:11px; font-weight:800; justify-content:center;" onclick="openTemplateDetailModal('${code}')">
                  🧠 Role Skill & Quy Trình
                </button>
                ${firstSample ? `
                  <button class="btn btn-xs btn-outline" style="padding:7px 8px; font-size:10.5px; border-color:rgba(16,185,129,0.45); color:#6ee7b7;" onclick="openSampleProductInStudio('${firstSample.product_id}', '${t.folder_name}')" title="Mở xem dự án mẫu đã render trong Studio">
                    👁️ SP Mẫu
                  </button>
                ` : `
                  <button class="btn btn-xs btn-outline" style="padding:7px 8px; font-size:10.5px;" onclick="openFolderEncoded('${encodeURIComponent(t.folder_path || '')}')" title="Mở thư mục Template">
                    📂 Folder
                  </button>
                `}
              </div>
            </div>
          </div>
        `;
      }).join("");
    }

    async function openTemplateDetailModal(codeOrFolder) {
      const res = await apiGet(`/api/templates/detail?name=${encodeURIComponent(codeOrFolder)}`);
      if (!res || !res.ok) return alert("Không tải được chi tiết Template & Role Skill!");
      const cfg = res.config || {};
      const code = res.code || cfg.code || "001";
      const docs = res.docs || {};
      const primaryVid = res.primary_demo_video || (res.demo_videos && res.demo_videos[0]) || null;
      const wfSteps = cfg.workflow_steps || [];

      STATE.curModalTemplateCodeOrName = code;
      STATE.curModalTemplateFolder = res.folder_name;
      STATE.curModalTemplateDocs = docs;

      document.getElementById("tplDetailModalTitle").textContent = `🏷️ Mã Template #${code} (${res.folder_name}) — Xem & Chỉnh Sửa Role Skill (.MD) & Quy Trình`;

      const docKeys = Object.keys(docs);
      const firstDocKey = docKeys.includes("ROLE_SKILL.md") ? "ROLE_SKILL.md" : (docKeys.includes("SKILL.md") ? "SKILL.md" : (docKeys[0] || "ROLE_SKILL.md"));
      STATE.curModalDocKey = firstDocKey;

      const wfHtml = wfSteps.map(ws => `
        <div style="background:#090d16; border:1px solid rgba(245,158,11,0.25); border-radius:6px; padding:6px 8px; font-size:10.5px;">
          <b style="color:#fde68a;">${ws.icon || '⚡'} ${ws.title}:</b> <span style="color:var(--muted);">${ws.detail}</span>
        </div>
      `).join("");

      document.getElementById("tplDetailModalBody").innerHTML = `
        <div style="display:grid; grid-template-columns: 310px 1fr; gap:14px; align-items:start;">
          <!-- Cột Trái: 01 Video Demo Hoàn Thiện 60 FPS + Quy Trình 4 Bước + Nút Chạy Ngay -->
          <div style="display:flex; flex-direction:column; gap:8px; background:#080c14; border:1px solid var(--border-light); border-radius:8px; padding:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="badge" style="background:#f59e0b; color:#050811; font-weight:900;">🏷️ MÃ TEMPLATE #${code}</span>
              <span style="font-size:10.5px; color:#34d399; font-weight:700;">1080p • 60 FPS • Sub</span>
            </div>
            <div style="width:100%; aspect-ratio:9/16; max-height:380px; background:#000; border-radius:7px; overflow:hidden; border:1px solid rgba(245,158,11,0.4);">
              ${primaryVid ? `
                <video controls preload="metadata" style="width:100%; height:100%; object-fit:contain; background:#000;" src="${primaryVid.url}"></video>
              ` : `<div style="color:var(--muted); padding:20px; text-align:center;">Chưa có video demo</div>`}
            </div>
            <div style="font-size:10.5px; color:#fde68a; font-weight:700; text-align:center;">
              ${cfg.demo_video_caption || (primaryVid ? primaryVid.label : '')}
            </div>
            <div style="display:flex; flex-direction:column; gap:5px; margin-top:4px;">
              ${wfHtml}
            </div>
            <button class="btn btn-success" style="width:100%; padding:8px; font-weight:800;" onclick="closeModal('modalTemplateDetail'); useTemplateFromMarketplace('${code}')">
              🎬 Dùng Template #${code} Tạo Video Ngay
            </button>
            <button class="btn btn-outline" style="width:100%;" onclick="copyMarketAiCommand('${code}')">
              🤖 Copy Lệnh Gửi AI Agent (Template ${code})
            </button>
          </div>

          <!-- Cột Phải: Trình Soạn Thảo Trực Tiếp Role Skill (.MD), Kịch Bản & Cấu Hình Template -->
          <div style="display:flex; flex-direction:column; gap:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap; background:#090d16; padding:8px 10px; border-radius:8px; border:1px solid var(--border);">
              <div style="display:flex; gap:5px; flex-wrap:wrap;" id="tplDocTabsBar">
                ${docKeys.map(dk => `
                  <button class="btn btn-xs ${dk === firstDocKey ? 'btn-amber' : 'btn-outline'}" onclick="switchTplDetailDocTab('${dk}', this)">
                    ${dk === 'ROLE_SKILL.md' ? '🧠 ROLE_SKILL.md (Role Skill Chính)' : ('📄 ' + dk)}
                  </button>
                `).join("")}
              </div>
              <div style="display:flex; gap:6px; align-items:center;">
                <button class="btn btn-xs btn-success" style="padding:5px 12px; font-weight:800;" onclick="saveTplDetailDoc()">💾 Lưu Role Skill / Tài Liệu</button>
                <button class="btn btn-xs btn-outline" onclick="openFolderEncoded('${encodeURIComponent(res.folder_path || '')}')">📂 Mở Folder</button>
              </div>
            </div>
            <div id="tplDocSaveStatus" style="font-size:11px; color:#34d399; display:none;"></div>
            <textarea id="tplDocContentViewer" rows="25" style="font-family:Consolas, monospace; font-size:12px; line-height:1.5; background:#060911; color:#e2e8f0; border:1px solid var(--border-light); border-radius:8px; padding:12px;">${(docs[firstDocKey] || '').replace(/</g, '&lt;')}</textarea>
          </div>
        </div>
      `;
      openModal("modalTemplateDetail");
    }

    function switchTplDetailDocTab(docKey, btnEl) {
      const docs = STATE.curModalTemplateDocs || {};
      const viewer = document.getElementById("tplDocContentViewer");
      if (viewer && STATE.curModalDocKey) {
        docs[STATE.curModalDocKey] = viewer.value;
      }
      STATE.curModalDocKey = docKey;
      if (viewer) viewer.value = docs[docKey] || "";
      const bar = document.getElementById("tplDocTabsBar");
      if (bar) {
        bar.querySelectorAll("button").forEach(b => {
          b.className = "btn btn-xs btn-outline";
        });
      }
      if (btnEl) btnEl.className = "btn btn-xs btn-amber";
    }

    async function saveTplDetailDoc() {
      const folderName = STATE.curModalTemplateFolder || "";
      const docKey = STATE.curModalDocKey || "ROLE_SKILL.md";
      const viewer = document.getElementById("tplDocContentViewer");
      if (!folderName || !viewer) return;
      const content = viewer.value;
      if (STATE.curModalTemplateDocs) STATE.curModalTemplateDocs[docKey] = content;
      const res = await apiPost("/api/templates/save_doc", {
        folder_name: folderName,
        doc_name: docKey,
        content,
      });
      const stEl = document.getElementById("tplDocSaveStatus");
      if (stEl) {
        stEl.style.display = "block";
        stEl.textContent = (res && res.ok) ? `✅ Đã lưu ${docKey} thành công!` : `❌ Lỗi: ${(res && res.error) || 'Không lưu được'}`;
      }
    }

    // =========================================================================================
    // STUDIO TEMPLATE #004: MOTION CONTROL VIDEO FASHION (4 BƯỚC CHUẨN: AI PHÂN TÍCH VIDEO -> 4-5 BỘ ĐỒ 2K -> VIDEO PHÂN CẢNH -> RENDER HẬU KỲ VIDEO FINAL)
    // =========================================================================================
    STATE.fashionProject = null;
    STATE.fashionProjectsList = [];
    STATE.fashionRefVideosLib = [];
    STATE.fashionDefaultOutfits = [];
    STATE.fashionOutfits = [];
    STATE.fashionStandardPrompts = {};
    STATE.fashionCharacters = [];
    STATE.fashionLibrary = { characters: [], outfits: [] };
    STATE.fashionVideoTemplatesCatalog = { total: 0, categories: [], templates: [] };
    STATE.selectedFashionTemplateCode = "FVT_001";
    STATE.activeFashionTplCategory = "all";
    STATE.activeFashionPromptTab = "deconstructed_outfit_flatlay_2k";
    STATE.selectedFashionRawProdImage = "";

    function showFashionBanner(msg, isErr = false) {
      const el = document.getElementById("fashionStudioStatusBanner");
      if (el) {
        el.style.display = msg ? "block" : "none";
        el.style.borderColor = isErr ? "rgba(239,68,68,0.55)" : "rgba(236,72,153,0.45)";
        el.style.color = isErr ? "#fca5a5" : "#f9a8d4";
        el.innerHTML = msg || "";
      }
      if (typeof showMarketBanner === "function") {
        showMarketBanner(msg);
      }
    }

    function formatPromptWithInlineChipsHtml(promptText) {
      if (!promptText) return "";
      const esc = String(promptText)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br/>");
      return esc.replace(/\[([^\]]+\.(?:png|jpg|jpeg|webp|mp4))\]/gi, (m, fn) => {
        const isVid = /\.mp4$/i.test(fn);
        const isLastFrame = /last_frame/i.test(fn);
        const bg = isVid ? "rgba(6,182,212,0.22)" : (isLastFrame ? "rgba(16,185,129,0.25)" : "rgba(59,130,246,0.22)");
        const col = isVid ? "#67e8f9" : (isLastFrame ? "#34d399" : "#93c5fd");
        const bdr = isVid ? "rgba(6,182,212,0.55)" : (isLastFrame ? "rgba(16,185,129,0.65)" : "rgba(59,130,246,0.55)");
        const ico = isVid ? "🎬" : (isLastFrame ? "🎞️" : "🖼️");
        return `<span style="display:inline-flex; align-items:center; gap:4px; background:${bg}; color:${col}; border:1px solid ${bdr}; border-radius:5px; padding:1px 7px; font-weight:800; font-family:Consolas,monospace; font-size:11px; margin:0 2px;">${ico} ${fn}</span>`;
      });
    }

    // -----------------------------------------------------------------------------------------
    // BỘ HÀM ĐIỀU KHIỂN VIDEO & FILE TRỰC TIẾP TRONG TAB THỜI TRANG (KHÔNG CẦN BẤM MENU ⋮)
    // -----------------------------------------------------------------------------------------
    function toggleFashionInlineVideo(vidId, btnId = "") {
      const v = typeof vidId === "string" ? document.getElementById(vidId) : vidId;
      if (!v) return;
      if (v.paused || v.ended) {
        document.querySelectorAll("#tab-fashion video").forEach(other => {
          if (other !== v && !other.paused) {
            other.pause();
          }
        });
        v.muted = false;
        v.volume = 1.0;
        v.play().catch(() => {});
        if (btnId) {
          const btn = document.getElementById(btnId);
          if (btn) btn.innerHTML = "⏸️ Dừng";
        }
      } else {
        v.pause();
        if (btnId) {
          const btn = document.getElementById(btnId);
          if (btn) btn.innerHTML = "▶️ Phát";
        }
      }
    }

    function toggleFashionInlineMute(vidId, btnId = "") {
      const v = typeof vidId === "string" ? document.getElementById(vidId) : vidId;
      if (!v) return;
      v.muted = !v.muted;
      if (!v.muted) v.volume = 1.0;
      if (btnId) {
        const btn = document.getElementById(btnId);
        if (btn) btn.innerHTML = v.muted ? "🔇 Bật tiếng" : "🔊 Có tiếng";
      }
    }

    function downloadFashionMedia(encodedPath) {
      if (!encodedPath) return;
      const rawPath = decodeURIComponent(encodedPath);
      const fn = rawPath.split(/[\\/]/).pop() || "fashion_video.mp4";
      if (typeof downloadFileDirect === "function") {
        downloadFileDirect(encodedPath, fn);
      } else {
        const a = document.createElement("a");
        a.href = `/api/media?path=${encodedPath}`;
        a.download = fn;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
      if (typeof toast === "function") toast(`⬇️ Đang tải xuống: ${fn}`, "ok");
    }

    function copyFashionPath(encodedPath) {
      if (!encodedPath) return;
      const rawPath = decodeURIComponent(encodedPath);
      navigator.clipboard.writeText(rawPath);
      showFashionBanner(`📋 Đã copy đường dẫn file vào Clipboard: <code>${rawPath}</code>`);
      if (typeof toast === "function") toast(`📋 Đã copy đường dẫn: ${rawPath.split(/[\\/]/).pop()}`, "ok");
    }

    function openFashionSceneVideoModal(projectId, sceneIdx = 0) {
      const projs = STATE.fashionProjectsList || [];
      const fp = projs.find(p => p.project_id === projectId) || (STATE.fashionProject?.project_id === projectId ? STATE.fashionProject : null);
      if (!fp) return;
      const sc = (fp.scenes || [])[sceneIdx];
      if (!sc) return;
      const vidPath = sc.output_video_path || sc.ref_clip_path || "";
      if (!vidPath) {
        showFashionBanner(`⚠️ Phân cảnh ${sceneIdx + 1} của dự án <b>${projectId}</b> chưa có file video.`, true);
        return;
      }
      const refImgPath = fp.char_sheet_2k?.path || "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/07_Nhan_Vat_Basic_Phong_Ngu_2K.png";
      const ovImgPath = "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/01_Character_Sheet_4_Outfits_2K.png";
      openVerticalVideoModal(
        encodeURIComponent(vidPath),
        encodeURIComponent(refImgPath),
        encodeURIComponent(ovImgPath),
        `${fp.title || projectId} — Phân Cảnh ${sceneIdx + 1} (${sc.duration || 8}s)`,
        "",
        ""
      );
    }

    async function renderFashionFinalForProject(projectId) {
      const slug = projectId || STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19";
      showFashionBanner(`⏳ Đang Render Hậu Kỳ ghép nối các Video Phân Cảnh + Nhạc Gốc thành Video Final 1080p 60FPS cho dự án <b>${slug}</b>...`);
      if (typeof toast === "function") toast(`🎞️ Đang ghép hậu kỳ Video Final 60FPS (${slug})...`, "info");
      const res = await apiPost("/api/fashion_motion/render_final", { project_id: slug });
      if (res && res.ok) {
        await loadFashionMotionStudio(false, slug);
        showFashionBanner(`🎉 ${res.message || 'Đã Render Hậu Kỳ xong Video Final 1080p 60FPS!'}`);
        if (typeof toast === "function") toast("🎉 Đã ghép xong Video Final 1080p 60FPS!", "ok");
      } else {
        showFashionBanner(`❌ Lỗi Render Hậu Kỳ: ${(res && res.error) || 'Không xác định'}`, true);
      }
    }

    async function runFashionFlowForProject(projectId) {
      if (projectId && STATE.fashionProject?.project_id !== projectId) {
        await loadFashionMotionStudio(false, projectId);
      }
      STATE.lastUserClickedTemplateCode = "";
      await runFashionProjectOnFlow();
    }

    async function changeSingleFashionOutfitImage(idx) {
      const item = (STATE.fashionOutfits || [])[idx];
      if (!item) return;
      const res = await apiGet("/api/pick_file?kind=image");
      if (!res || !res.ok || !res.path) return;
      const fn = res.path.split(/[\\/]/).pop();
      item.path = res.path;
      item.filename = fn;
      item.name = `Bộ ${idx + 1}: ${fn}`;
      renderFashionOutfitsList();
      showFashionBanner(`👗 Đã đổi ảnh Bộ #${idx + 1} thành <b>${fn}</b>!`);
    }

    function removeSingleFashionOutfit(idx) {
      if (!Array.isArray(STATE.fashionOutfits) || idx < 0 || idx >= STATE.fashionOutfits.length) return;
      const removed = STATE.fashionOutfits.splice(idx, 1)[0];
      renderFashionOutfitsList();
      showFashionBanner(`🗑️ Đã xoá <b>${removed?.name || removed?.filename || 'Bộ đồ'}</b> khỏi danh sách phối đồ.`);
    }

    function syncFashionOutfitsWithDefaults(projOutfits, defaultOutfits) {
      const activeList = Array.isArray(projOutfits) ? projOutfits : [];
      const defList = Array.isArray(defaultOutfits) ? defaultOutfits : [];
      const activeIds = new Set(activeList.map(o => o.id || o.filename));
      const merged = activeList.map(o => ({ ...o, enabled: true }));
      defList.forEach(d => {
        const key = d.id || d.filename;
        if (!activeIds.has(key) && !activeList.some(x => x.filename === d.filename)) {
          merged.push({
            ...d,
            path: d.path || `ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/${d.filename}`,
            lookbook_model_path: d.lookbook_model_path || (d.lookbook_model_filename ? `ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/${d.lookbook_model_filename}` : ""),
            width: d.width || 2048,
            height: d.height || 2559,
            is_2k: true,
            enabled: merged.length < 5,
          });
        }
      });
      return merged;
    }

    async function loadFashionMotionStudio(forceToast = false, targetProjectId = "") {
      const wantPid = targetProjectId || (STATE.fashionProject && STATE.fashionProject.project_id) || "";
      const res = await apiGet(`/api/fashion_motion/projects?project_id=${encodeURIComponent(wantPid)}`);
      if (!res || !res.ok) return;
      STATE.fashionStandardPrompts = res.standard_prompts || {};
      STATE.fashionCharacters = res.characters || (STATE.charLib?.characters) || [];
      STATE.fashionLibrary = res.fashion_library || { characters: [], outfits: [] };
      STATE.fashionVideoTemplatesCatalog = res.video_templates_catalog || { total: 0, categories: [], templates: [] };
      STATE.fashionProjectsList = res.projects || [];
      STATE.fashionRefVideosLib = res.ref_videos_library || [];
      STATE.fashionDefaultOutfits = res.default_outfits || [];

      const runningProj = !targetProjectId ? (STATE.fashionProjectsList || []).find(p => p.status === "running_flow") : null;
      const proj = runningProj || res.active_project || res.current_project || STATE.fashionProjectsList[0] || null;
      if (!proj) return;
      STATE.fashionProject = proj;
      if (proj.source_template_code) {
        STATE.selectedFashionTemplateCode = proj.source_template_code;
      } else if (!STATE.selectedFashionTemplateCode && (STATE.fashionVideoTemplatesCatalog.templates || []).length) {
        STATE.selectedFashionTemplateCode = STATE.fashionVideoTemplatesCatalog.templates[0].code;
      }
      STATE.fashionOutfits = syncFashionOutfitsWithDefaults(proj.outfits || [], STATE.fashionDefaultOutfits);

      populateFashionProjectDropdown();
      populateFashionRefVideoLibDropdown();
      populateFashionCharacterPicker();
      populateFashionProductStorePicker(false);
      renderFashionVideoTemplatesHub();
      renderFashionMotionStudio();
      renderFashionStandardPromptBox();
      if (forceToast) {
        showFashionBanner(`👗 Đã tải dự án Video Thời Trang: <b>${proj.title}</b> (${(proj.scenes || []).length} phân cảnh × ${proj.split_plan?.scene_duration || 8}s • ${(proj.outfits || []).length} Bộ Đồ 2K • Kho ${STATE.fashionVideoTemplatesCatalog.total || 30} Template Video)`);
      }
    }

    function setFashionTplCategoryFilter(catKey, btnEl) {
      STATE.activeFashionTplCategory = catKey || "all";
      const bar = document.getElementById("fashionTplCategoryBar");
      if (bar && btnEl) {
        bar.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btnEl.classList.add("active");
      }
      filterFashionVideoTemplatesGrid();
    }

    function renderFashionVideoTemplatesHub() {
      const cat = STATE.fashionVideoTemplatesCatalog || { total: 0, templates: [] };
      const allTpls = cat.templates || [];
      const badgeEl = document.getElementById("badgeFashionTplTotalCount");
      if (badgeEl) {
        badgeEl.textContent = `${allTpls.length} Template Đã Phân Tích Sẵn`;
      }
      const hubTitleEl = document.getElementById("badgeFashionTplHubTitle");
      if (hubTitleEl && allTpls.length > 0) {
        const lastCode = allTpls[allTpls.length - 1]?.code || `FVT_${String(allTpls.length).padStart(3, "0")}`;
        hubTitleEl.textContent = `🎬 KHO ${allTpls.length} TEMPLATE VIDEO MẪU (FVT_001 ➔ ${lastCode})`;
      }
      const bar = document.getElementById("fashionTplCategoryBar");
      if (bar && Array.isArray(cat.categories) && cat.categories.length) {
        const counts = { all: allTpls.length };
        allTpls.forEach(t => {
          const ck = t.category || "glowup";
          counts[ck] = (counts[ck] || 0) + 1;
        });
        bar.innerHTML = cat.categories.map(c => {
          const isAct = (STATE.activeFashionTplCategory || "all") === c.key;
          const cnt = counts[c.key] || 0;
          const labelTxt = c.key === "all" ? `🌟 Tất cả (${cnt})` : `${c.label} (${cnt})`;
          return `<button class="btn-filter ${isAct ? 'active' : ''}" onclick="setFashionTplCategoryFilter('${c.key}', this)">${labelTxt}</button>`;
        }).join("");
      }
      filterFashionVideoTemplatesGrid();
      renderSelectedFashionTemplateDetail();
    }

    function filterFashionVideoTemplatesGrid() {
      const grid = document.getElementById("fashionVideoTemplatesGrid");
      if (!grid) return;
      const allTpls = (STATE.fashionVideoTemplatesCatalog && STATE.fashionVideoTemplatesCatalog.templates) || [];
      const q = (document.getElementById("inpFashionTplSearch")?.value || "").trim().toLowerCase();
      const catFilter = STATE.activeFashionTplCategory || "all";

      const filtered = allTpls.filter(t => {
        if (catFilter !== "all" && t.category !== catFilter) return false;
        if (!q) return true;
        const hay = `${t.code} ${t.filename} ${t.title} ${t.category_label} ${t.background_setting} ${t.action_description}`.toLowerCase();
        return hay.includes(q);
      });

      if (!filtered.length) {
        grid.innerHTML = `<div style="grid-column:1/-1; padding:24px; text-align:center; color:#94a3b8; font-size:12px;">Không tìm thấy Template Video phù hợp. Hãy thử từ khóa khác hoặc bấm <b>🔄 Quét Video Mới Trong Folder</b>.</div>`;
        return;
      }

      const curCode = STATE.selectedFashionTemplateCode || filtered[0].code;
      grid.innerHTML = filtered.map(t => {
        const isSel = t.code === curCode;
        const thumbUrl = `/api/media?path=${encodeURIComponent(t.thumb_path || '')}`;
        const vEnc = encodeURIComponent(t.video_path || '');
        const thEnc = encodeURIComponent(t.thumb_path || '');
        return `
          <div onclick="selectFashionVideoTemplate('${t.code}')"
               style="cursor:pointer; background:${isSel ? 'linear-gradient(160deg, rgba(236,72,153,0.22), rgba(15,23,42,0.96))' : '#080d18'}; border:1.5px solid ${isSel ? '#ec4899' : 'rgba(255,255,255,0.1)'}; border-radius:9px; padding:6px; display:flex; flex-direction:column; gap:5px; transition:all 0.15s; box-shadow:${isSel ? '0 0 16px rgba(236,72,153,0.35)' : 'none'};">
            <div style="width:100%; aspect-ratio:9/14; border-radius:6px; overflow:hidden; background:#000; position:relative;">
              <img src="${thumbUrl}" loading="lazy" style="width:100%; height:100%; object-fit:cover;" />
              <span style="position:absolute; top:5px; left:5px; background:linear-gradient(135deg,#ec4899,#8b5cf6); color:#fff; font-size:10px; font-weight:900; padding:1.5px 6px; border-radius:4px; box-shadow:0 2px 8px rgba(0,0,0,0.6);">
                ${t.code}
              </span>
              <span style="position:absolute; top:5px; right:5px; background:rgba(0,0,0,0.82); color:#fde68a; font-size:9.5px; font-weight:800; padding:1.5px 5px; border-radius:4px; border:1px solid rgba(253,230,138,0.35);">
                ${t.duration}s • ${t.num_scenes} cảnh
              </span>
              <button class="btn btn-xs btn-primary"
                      style="position:absolute; bottom:26px; right:5px; padding:2px 6px; font-size:9px; font-weight:800; background:rgba(37,99,235,0.92); border-color:#60a5fa; box-shadow:0 2px 8px rgba(0,0,0,0.65);"
                      onclick="event.stopPropagation(); openVerticalVideoModal('${vEnc}', '${thEnc}', '', '[${t.code}] ${(t.title || '').replace(/'/g, '')} (${t.duration}s)', '', '');"
                      title="Mở xem phóng to dọc 9:16 có tiếng cho Template ${t.code}">
                📱 9:16
              </button>
              <span style="position:absolute; bottom:5px; left:5px; right:5px; background:rgba(4,7,14,0.85); color:#67e8f9; font-size:9px; font-weight:700; padding:2px 5px; border-radius:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                ${t.category_label || ''} • ${t.recommended_outfits || 4} bộ đồ
              </span>
            </div>
            <div style="font-size:11px; font-weight:800; color:#f8fafc; line-height:1.3; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; min-height:28px;" title="${(t.title || '').replace(/"/g, '&quot;')}">
              ${t.title}
            </div>
            <div style="font-size:9.5px; color:#94a3b8; line-height:1.3; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
              🏠 ${t.background_setting || ''}
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:3px; margin-top:auto;">
              <button class="btn btn-xs ${isSel ? 'btn-amber' : 'btn-outline'}" style="justify-content:center; font-size:9px; padding:3px 3px; font-weight:800;"
                      onclick="event.stopPropagation(); selectFashionVideoTemplate('${t.code}');"
                      title="Xem & nghe thử Video Mẫu ${t.code} có tiếng">
                ${isSel ? '🔊 Đang Xem' : '▶️ Xem'}
              </button>
              <button class="btn btn-xs btn-primary" style="justify-content:center; font-size:9px; padding:3px 3px; font-weight:800;"
                      onclick="event.stopPropagation(); selectFashionVideoTemplate('${t.code}'); applySelectedFashionTemplate(false);"
                      title="Nạp ngay Template ${t.code} vào kịch bản (Cắt clip 30FPS + Tạo Prompt)">
                ⚡ Nạp
              </button>
              <button class="btn btn-xs btn-success" style="justify-content:center; font-size:9px; padding:3px 3px; font-weight:900;"
                      onclick="event.stopPropagation(); selectFashionVideoTemplate('${t.code}'); applySelectedFashionTemplate(true);"
                      title="Bấm Render tạo ngay Video Final với Template ${t.code}">
                🚀 Render
              </button>
            </div>
          </div>
        `;
      }).join("");
    }

    function selectFashionVideoTemplate(code) {
      STATE.selectedFashionTemplateCode = code;
      STATE.lastUserClickedTemplateCode = code;
      filterFashionVideoTemplatesGrid();
      renderSelectedFashionTemplateDetail(true);
    }

    function renderSelectedFashionTemplateDetail(playWithSound = false) {
      const box = document.getElementById("fashionSelectedTemplateDetailBox");
      if (!box) return;
      const allTpls = (STATE.fashionVideoTemplatesCatalog && STATE.fashionVideoTemplatesCatalog.templates) || [];
      if (!allTpls.length) {
        box.innerHTML = `<div style="padding:20px; text-align:center; color:#94a3b8;">Đang tải danh mục 30+ Template Video Thời Trang...</div>`;
        return;
      }
      const curCode = STATE.selectedFashionTemplateCode || allTpls[0].code;
      const tpl = allTpls.find(x => x.code === curCode) || allTpls[0];
      const vidEnc = encodeURIComponent(tpl.video_path || '');
      const stripEnc = encodeURIComponent(tpl.strip_path || '');
      const vidUrl = `/api/media?path=${vidEnc}`;
      const stripUrl = `/api/media?path=${stripEnc}`;
      const bpList = tpl.scenes_blueprint || [];

      const curGenMode = document.getElementById("selFashionGenerationMode")?.value || (STATE.fashionProject && STATE.fashionProject.generation_mode) || "chained_i2v";
      const isI2vMode = curGenMode === "chained_i2v";

      const bpHtml = bpList.map(bp => {
        const activeBpPrompt = (isI2vMode ? (bp.prompt_chained_i2v || bp.prompt_template) : (bp.prompt_template || bp.prompt_chained_i2v)) || '';
        const tsDisplay = isI2vMode
          ? ((bp.transition_timestamps_sec && bp.transition_timestamps_sec.length) ? bp.transition_timestamps_sec.join(', ') : (bp.transition_timestamps || []).join(', '))
          : (bp.transition_timestamps || []).join(', ');
        const modeBadgeTxt = isI2vMode ? '⚡ I2V Timeline 0.1s' : '🎥 Video Ref';
        return `
        <div style="background:#0a0f1d; border:1px solid rgba(59,130,246,0.35); border-radius:7px; padding:7px 9px; margin-top:5px;">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; margin-bottom:3px; flex-wrap:wrap;">
            <span style="font-size:10.5px; font-weight:800; color:#67e8f9;">✂️ Phân cảnh ${bp.scene_index} (${bp.start_sec}s – ${bp.end_sec}s) • <span style="color:#a78bfa;">${modeBadgeTxt}</span> • Đổi đồ tại: <b style="color:#fde68a;">${tsDisplay}</b></span>
            <button class="btn btn-xs btn-outline" style="font-size:9px; padding:1px 6px;" onclick="navigator.clipboard.writeText(${JSON.stringify(activeBpPrompt).replace(/"/g, '&quot;')}); showFashionBanner('📋 Đã copy Prompt Mẫu Phân Cảnh ${bp.scene_index} của ${tpl.code}!');">📋 Copy Prompt</button>
          </div>
          <div style="font-size:10px; color:#e2e8f0; line-height:1.45; max-height:115px; overflow-y:auto; white-space:pre-wrap;">${formatPromptWithInlineChipsHtml(activeBpPrompt)}</div>
        </div>
      `;
      }).join("");

      box.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:8px;">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:6px;">
            <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
              <span class="badge" style="background:linear-gradient(135deg,#ec4899,#8b5cf6); color:#fff; font-weight:900; font-size:11px;">🏷️ MÃ ${tpl.code}</span>
              <span style="font-size:12.5px; font-weight:900; color:#fff;">${tpl.title}</span>
            </div>
            <div style="display:flex; gap:4px; align-items:center;">
              <span class="badge" style="background:rgba(6,182,212,0.18); color:#67e8f9; font-size:10px;">${tpl.category_label || ''}</span>
              <button class="btn btn-xs btn-primary" style="font-size:9.5px; padding:2px 7px;" onclick="openVerticalVideoModal('${vidEnc}', '${stripEnc}', '', '[${tpl.code}] ${(tpl.title || '').replace(/'/g, '')} (${tpl.duration}s)', '', '')">📱 Phóng To 9:16</button>
            </div>
          </div>

          <div style="display:grid; grid-template-columns: 162px 1fr; gap:10px; align-items:start;">
            <!-- Video Demo 9:16 của Template (Có đầy đủ nút điều khiển bên dưới, không cần bấm ⋮) -->
            <div style="display:flex; flex-direction:column; gap:4px;">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:4px;">
                <span style="font-size:9.5px; font-weight:800; color:#fde68a;">🔊 VIDEO DEMO (${tpl.duration}S)</span>
                <span style="font-size:8.5px; color:#34d399; font-weight:700;">Bấm ảnh để Phát</span>
              </div>
              <div style="width:100%; aspect-ratio:9/16; background:#000; border-radius:7px; overflow:hidden; border:1.5px solid #ec4899; box-shadow:0 6px 18px rgba(0,0,0,0.6); position:relative; cursor:pointer;"
                   onclick="toggleFashionInlineVideo('fashionTplDemoVideoPlayer', 'btnPlayTplDemoVid')">
                <video id="fashionTplDemoVideoPlayer" class="fashion-clean-video" controls controlslist="nodownload noplaybackrate" disablepictureinpicture ${playWithSound ? 'autoplay' : ''} loop playsinline preload="metadata"
                       onloadedmetadata="this.muted=false; this.volume=1.0;"
                       onplay="const b=document.getElementById('btnPlayTplDemoVid'); if(b) b.innerHTML='⏸️ Dừng';"
                       onpause="const b=document.getElementById('btnPlayTplDemoVid'); if(b) b.innerHTML='▶️ Phát';"
                       style="width:100%; height:100%; object-fit:cover;" src="${vidUrl}"></video>
              </div>
              <!-- Thanh 6 Nút Điều Khiển Trực Tiếp Cho Video Demo -->
              <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:3px;">
                <button id="btnPlayTplDemoVid" class="btn btn-xs btn-success" style="padding:3px 2px; font-size:9px; font-weight:800; justify-content:center;"
                        onclick="toggleFashionInlineVideo('fashionTplDemoVideoPlayer', 'btnPlayTplDemoVid')">
                  ▶️ Phát
                </button>
                <button id="btnMuteTplDemoVid" class="btn btn-xs btn-amber" style="padding:3px 2px; font-size:9px; font-weight:800; justify-content:center;"
                        onclick="toggleFashionInlineMute('fashionTplDemoVideoPlayer', 'btnMuteTplDemoVid')">
                  🔊 Tiếng
                </button>
                <button class="btn btn-xs btn-primary" style="padding:3px 2px; font-size:9px; font-weight:800; justify-content:center;"
                        onclick="openVerticalVideoModal('${vidEnc}', '${stripEnc}', '', '[${tpl.code}] ${(tpl.title || '').replace(/'/g, '')} (${tpl.duration}s)', '', '')">
                  📱 9:16
                </button>
                <button class="btn btn-xs btn-outline" style="padding:3px 2px; font-size:9px; font-weight:800; justify-content:center;"
                        onclick="openFileEncoded('${vidEnc}')" title="Mở bằng trình phát video của máy tính">
                  🖥️ Player
                </button>
                <button class="btn btn-xs btn-outline" style="padding:3px 2px; font-size:9px; font-weight:800; justify-content:center;"
                        onclick="openFolderEncoded('${vidEnc}')" title="Mở vị trí file video gốc trong Explorer">
                  📂 File
                </button>
                <button class="btn btn-xs btn-outline" style="padding:3px 2px; font-size:9px; font-weight:800; justify-content:center;"
                        onclick="downloadFashionMedia('${vidEnc}')" title="Tải file video mẫu về máy">
                  ⬇️ Tải
                </button>
              </div>
              <div style="font-size:8.5px; color:#94a3b8; text-align:center; font-family:Consolas,monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${tpl.filename}">
                ${tpl.filename}
              </div>
            </div>

            <!-- Thông Tin Phân Tích Sẵn: Bối Cảnh + Hành Động + Nhịp Cắt + Nút Chạy -->
            <div style="display:flex; flex-direction:column; gap:6px; min-width:0;">
              <div style="background:rgba(236,72,153,0.1); border-left:3px solid #ec4899; padding:5px 8px; border-radius:4px; font-size:10.5px; color:#f8fafc; line-height:1.4;">
                <div><b style="color:#f9a8d4;">🏠 Bối cảnh gốc:</b> ${tpl.background_setting || ''}</div>
                <div style="margin-top:3px;"><b style="color:#67e8f9;">💃 Hành động & Chuyển động:</b> ${tpl.action_description || ''}</div>
                <div style="margin-top:3px; font-size:10px; color:#fde68a;">
                  ⏱️ Thời lượng: <b>${tpl.duration}s</b> (${tpl.width}×${tpl.height}) ➔ Chia <b>${tpl.num_scenes} cảnh × 8s (30FPS)</b> • Phối <b>${tpl.recommended_outfits || 4} Bộ Đồ</b>
                </div>
              </div>

              <!-- Dải 6 Khung Hình Keyframe Tóm Tắt Video -->
              <div onclick="openLightbox('${stripUrl}', 'Dải 6 Khung Hình Phân Tích Template ${tpl.code}: ${(tpl.title || '').replace(/'/g, "\\'")}')"
                   style="cursor:pointer; background:#090d18; border:1px solid rgba(255,255,255,0.12); border-radius:6px; padding:4px; display:flex; flex-direction:column; gap:3px;"
                   title="Bấm để phóng to dải 6 khung hình của Template ${tpl.code}">
                <div style="display:flex; justify-content:space-between; font-size:9.5px; color:#cbd5e1; font-weight:700;">
                  <span>🎞️ Dải 6 Keyframe Biến Hình Của ${tpl.code}:</span>
                  <span style="color:#93c5fd;">🔍 Phóng to</span>
                </div>
                <img src="${stripUrl}" style="width:100%; height:56px; object-fit:cover; border-radius:4px;" />
              </div>

              <!-- Các Nút Thao Tác Chính: Áp Dụng Template Hoặc Bấm Render Ra Video Final Luôn -->
              <div style="display:flex; flex-direction:column; gap:5px; margin-top:2px;">
                <button class="btn btn-amber" style="width:100%; justify-content:center; font-weight:900; font-size:11px; padding:7px 10px;"
                        onclick="applySelectedFashionTemplate(false)">
                  ⚡ Nạp Template ${tpl.code} Vào Dự Án (Cắt Clip 30FPS + Tạo Prompt Mẫu)
                </button>
                <button class="btn btn-success" style="width:100%; justify-content:center; font-weight:900; font-size:11.5px; padding:8px 10px; box-shadow:0 4px 14px rgba(16,185,129,0.4);"
                        onclick="applySelectedFashionTemplate(true)">
                  🚀 BẤM RENDER RA VIDEO FINAL NGAY VỚI TEMPLATE ${tpl.code}
                </button>
              </div>
            </div>
          </div>

          <!-- Prompt Mẫu Đã Tạo Sẵn Cho Từng Phân Cảnh -->
          <div style="margin-top:2px;">
            <div style="font-size:10.5px; font-weight:800; color:#a5b4fc;">📝 PROMPT & TIMELINE MẪU ĐÃ TẠO SẴN CHO ${tpl.code} (TỰ ĐỘNG GẮN NHÂN VẬT & BỘ ĐỒ CỦA BẠN):</div>
            ${bpHtml}
          </div>
        </div>
      `;
      if (playWithSound) {
        const vidEl = document.getElementById("fashionTplDemoVideoPlayer");
        if (vidEl) {
          vidEl.muted = false;
          vidEl.volume = 1.0;
          vidEl.play().catch(() => {});
        }
      }
    }

    async function rescanFashionVideoTemplates(force = false) {
      showFashionBanner("⏳ Đang quét thư mục <code>Template Thời Trang Video</code>, chuẩn hóa mã FVT_xxx và phân tích sẵn Hành động + Bối cảnh + Prompt mẫu...");
      const res = await apiPost("/api/fashion_motion/scan_templates", { force: !!force });
      if (res && res.ok && res.video_templates_catalog) {
        STATE.fashionVideoTemplatesCatalog = res.video_templates_catalog;
        if (res.fashion_library) STATE.fashionLibrary = res.fashion_library;
        renderFashionVideoTemplatesHub();
        showFashionBanner(`✅ Đã đồng bộ xong <b>${res.video_templates_catalog.total} Template Video Thời Trang</b> (Mã <code>FVT_001</code> ➔ <code>FVT_${String(res.video_templates_catalog.total).padStart(3, '0')}</code>)!`);
      } else {
        showFashionBanner(`❌ Lỗi quét thư mục Template: ${(res && res.error) || 'Không xác định'}`, true);
      }
    }

    async function applySelectedFashionTemplate(autoRunFlow = false) {
      const code = STATE.selectedFashionTemplateCode || "FVT_001";
      const base_char_path = document.getElementById("inpFashionBaseChar")?.value || "";
      const char_sheet_path = document.getElementById("inpFashionCharSheet")?.value || "";
      const enabledOutfits = (STATE.fashionOutfits || []).filter(o => o.enabled !== false);

      const prepHtml = `
        <div style="display:flex; flex-direction:column; gap:6px;">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
            <span style="font-weight:900; color:#fde68a; font-size:12px;">
              ⏳ ĐANG XỬ LÝ TEMPLATE ${code}: Đang cắt các phân cảnh 8s chuẩn 30FPS & gắn 5 Ảnh Tham Chiếu 2K vào kịch bản...
            </span>
            <span class="badge" style="background:rgba(245,158,11,0.25); color:#fde68a; border:1px solid #f59e0b;">Đang cắt Clip 30FPS...</span>
          </div>
          <div style="width:100%; height:7px; background:#090e1a; border-radius:99px; overflow:hidden; border:1px solid rgba(255,255,255,0.1);">
            <div style="width:35%; height:100%; background:linear-gradient(90deg,#f59e0b,#ec4899,#06b6d4); border-radius:99px; transition:width 0.3s;"></div>
          </div>
        </div>
      `;
      ["fashionLiveMonitorBarTop", "fashionLiveMonitorBar"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.style.display = "block";
          el.innerHTML = prepHtml;
        }
      });

      showFashionBanner(
        autoRunFlow
          ? `🚀 Đang áp dụng Template <b>${code}</b> (kèm Nhân vật + ${enabledOutfits.length} Bộ Đồ 2K), cắt clip 30FPS và gửi thẳng lên <b>Google Flow (Omni 1.1 Flash)</b> để Render ra Video Final...`
          : `⚡ Đang nạp Template <b>${code}</b>, cắt các phân cảnh 8s chuẩn 30FPS và gắn Nhân vật + ${enabledOutfits.length} Bộ Đồ 2K vào kịch bản...`
      );

      const generation_mode = document.getElementById("selFashionGenerationMode")?.value || STATE.fashionProject?.generation_mode || "chained_i2v";
      const res = await apiPost("/api/fashion_motion/apply_template", {
        template_code: code,
        base_char_path,
        char_sheet_path,
        outfit_items: enabledOutfits,
        generation_mode,
        auto_run_flow: !!autoRunFlow,
      });

      if (res && res.ok) {
        STATE.fashionProject = res;
        if (Array.isArray(res.projects)) {
          STATE.fashionProjectsList = res.projects;
        }
        STATE.fashionOutfits = syncFashionOutfitsWithDefaults(res.outfits || [], STATE.fashionDefaultOutfits);
        populateFashionProjectDropdown();

        if (autoRunFlow) {
          STATE.fashionProject.status = "running_flow";
          STATE.fashionProject.status_message = `🚀 Đang khởi động trình duyệt Google Flow & tải 5 Ảnh Tham Chiếu 2K + Video Clip 30FPS cho Template ${code}...`;
          (STATE.fashionProject.scenes || []).forEach(s => {
            s.status = "preparing";
            s.attempt = 1;
            s.max_attempts = 4;
            s.status_detail = "🚀 Đang kết nối Google Flow & tải 5 ảnh tham chiếu 2K...";
          });
          renderFashionMotionStudio();
          showFashionBanner(`🚀 Đã khởi tạo xong kịch bản từ Template <b>${code}</b> (${res.title}) và đang chạy tự động trên <b>Google Flow (Omni 1.1 Flash)</b>! Theo dõi tiến trình trực tiếp bên dưới.`);
          startFashionLiveStatusMonitor(res.project_id);
          document.getElementById("fashionLiveMonitorBarTop")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else {
          renderFashionMotionStudio();
          const readyHtml = `
            <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
              <div style="display:flex; flex-direction:column; gap:3px;">
                <div style="font-weight:900; color:#34d399; font-size:12px;">
                  ✅ ĐÃ NẠP XONG TEMPLATE ${code}: <span style="color:#fff;">${res.title}</span> (${(res.scenes || []).length} phân cảnh × 8s • 30FPS)
                </div>
                <div style="font-size:11px; color:#cbd5e1;">
                  Đã cắt sẵn Clip Tham Chiếu 30FPS và gắn đủ 5 Ảnh Tham Chiếu 2K cho từng cảnh. Bấm nút <b>🚀 BẤM RENDER VIDEO FINAL NGAY</b> bên phải để bắt đầu tạo video!
                </div>
              </div>
              <button class="btn btn-success" style="font-weight:900; font-size:12px; padding:8px 16px; box-shadow:0 4px 16px rgba(16,185,129,0.45);" onclick="runFashionProjectOnFlow()">
                🚀 BẤM RENDER VIDEO FINAL NGAY (${code})
              </button>
            </div>
          `;
          ["fashionLiveMonitorBarTop", "fashionLiveMonitorBar"].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
              el.style.display = "block";
              el.innerHTML = readyHtml;
            }
          });
          showFashionBanner(`✅ Đã áp dụng Template <b>${code}</b> (${res.title}) — Đã cắt sẵn <b>${(res.scenes || []).length} phân cảnh 8s (30FPS)</b> và tạo xong Prompt mẫu. Bấm <b>🚀 BẤM RENDER VIDEO FINAL</b> để chạy Google Flow!`);
        }
      } else {
        showFashionBanner(`❌ Lỗi áp dụng Template ${code}: ${(res && res.error) || 'Không xác định'}`, true);
      }
    }

    function populateFashionProjectDropdown() {
      const sel = document.getElementById("selFashionProjectSlug");
      if (!sel) return;
      const projs = STATE.fashionProjectsList || [];
      const curSlug = STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19";
      if (!projs.length) return;
      sel.innerHTML = projs.map(p => {
        const scCnt = (p.scenes || []).length;
        const outCnt = (p.outfits || []).length;
        const dur = p.reference_video?.duration || 0;
        const hasFinal = p.final_video_ready ? "✅ Có Video Final" : "⏳ Chờ Render";
        return `<option value="${p.project_id}" ${p.project_id === curSlug ? "selected" : ""}>👗 [${p.project_id}] ${p.title || p.project_id} (${dur}s • ${scCnt} cảnh • ${outCnt} bộ đồ • ${hasFinal})</option>`;
      }).join("");
    }

    function populateFashionRefVideoLibDropdown() {
      const sel = document.getElementById("selFashionRefVideoLib");
      if (!sel) return;
      const vids = STATE.fashionRefVideosLib || [];
      const curRefName = STATE.fashionProject?.reference_video?.filename || "";
      const opts = [`<option value="">-- 🎬 Chọn nhanh Video Gốc trong thư viện (${vids.length} video) --</option>`];
      vids.forEach(v => {
        const isCur = curRefName && v.filename === curRefName;
        opts.push(`<option value="${v.path.replace(/"/g, '&quot;')}" ${isCur ? "selected" : ""}>🎞️ ${v.filename} (${v.size_mb} MB)</option>`);
      });
      sel.innerHTML = opts.join("");
    }

    async function onSelectFashionProjectSlug(slug) {
      if (!slug) return;
      await loadFashionMotionStudio(true, slug);
    }

    async function onSelectFashionRefVideoFromLib(videoPath) {
      if (!videoPath) return;
      const inpVid = document.getElementById("inpFashionRefVideo");
      if (inpVid) inpVid.value = videoPath;
      const fn = videoPath.split(/[\\/]/).pop();
      showFashionBanner(`🎬 Đã chọn Video Tham Chiếu Gốc: <b>${fn}</b>. Bấm <b>✂️ Bước 1+3: AI Phân Tích Video & Tạo Các Phân Cảnh</b> để AI chia cảnh và tạo video ngay!`);
    }

    async function promptCreateNewFashionProject() {
      const pickRes = await apiGet("/api/pick_file?kind=video");
      if (!pickRes || !pickRes.ok || !pickRes.path) return;
      const vPath = pickRes.path;
      const fn = vPath.split(/[\\/]/).pop().replace(/\.[^.]+$/, "");
      const cleanSlug = "fashion_" + fn.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 28) + "_" + String(Date.now()).slice(-4);
      const inpVid = document.getElementById("inpFashionRefVideo");
      if (inpVid) inpVid.value = vPath;
      await analyzeAndBuildFashionProject(cleanSlug, `Lookbook Thời Trang AI 2K (${fn})`);
    }

    function toggleAllFashionOutfits(checked = true) {
      (STATE.fashionOutfits || []).forEach(o => {
        o.enabled = !!checked;
      });
      renderFashionOutfitsList();
    }

    function selectFirstNFashionOutfits(n = 4) {
      (STATE.fashionOutfits || []).forEach((o, idx) => {
        o.enabled = idx < n;
      });
      renderFashionOutfitsList();
      showFashionBanner(`👗 Đã chọn <b>${n} Bộ Đồ 2K đầu tiên</b> để phân bổ vào các phân cảnh video!`);
    }

    function copyFashionAiAgentCommand() {
      const cmd = STATE.fashionProject?.ai_agent_command
        || `Phân tích video thời trang '${document.getElementById("inpFashionRefVideo")?.value || ""}' và tạo kịch bản chia phân cảnh thay 4-5 bộ đồ 2K rồi render hậu kỳ thành video final`;
      navigator.clipboard.writeText(cmd);
      showFashionBanner(`🤖 Đã copy câu lệnh gửi AI Agent vào Clipboard: <code>${cmd}</code>`);
      if (typeof toast === "function") toast("🤖 Đã copy câu lệnh phân tích Video cho AI Agent!", "ok");
    }

    function populateFashionCharacterPicker() {
      const sel = document.getElementById("selFashionCharFromLib");
      if (!sel) return;
      const libChars = (STATE.fashionLibrary && Array.isArray(STATE.fashionLibrary.characters)) ? STATE.fashionLibrary.characters : [];
      const fallbackChars = (STATE.fashionCharacters && STATE.fashionCharacters.length)
        ? STATE.fashionCharacters
        : ((STATE.charLib && STATE.charLib.characters) || []);

      const merged = [];
      const seen = new Set();
      libChars.forEach(c => {
        const k = c.id || c.key;
        if (!k || seen.has(k)) return;
        seen.add(k);
        merged.push({
          key: k,
          name: c.name || k,
          subtitle: c.desc || (c.is_default ? "Mặc Định Chuẩn 2K" : "Nhân vật tùy chỉnh"),
          pose_sheet_path: c.pose_sheet_path || "",
          bg_ref_path: c.bg_ref_path || "",
          is_default: !!c.is_default,
        });
      });
      fallbackChars.forEach(c => {
        const k = c.key || c.id;
        if (!k || seen.has(k)) return;
        seen.add(k);
        merged.push({
          key: k,
          name: c.name || k,
          subtitle: c.subtitle || "",
          pose_sheet_path: c.wardrobe_sheet_abs || c.ref_image_abs || "",
          bg_ref_path: c.bedroom_ref_abs || c.ref_image_abs || "",
          is_default: k === "nv5",
        });
      });

      if (!merged.length) return;
      const curVal = sel.value || merged[0].key;
      sel.innerHTML = merged.map(c => {
        const tag = c.is_default ? "👗 [MẶC ĐỊNH 2K]" : "👤";
        return `<option value="${c.key}" ${c.key === curVal ? "selected" : ""}>${tag} ${c.name} (${c.subtitle || ""})</option>`;
      }).join("");
    }

    function onSelectFashionCharacterFromLibrary(charKey) {
      const libChars = (STATE.fashionLibrary && Array.isArray(STATE.fashionLibrary.characters)) ? STATE.fashionLibrary.characters : [];
      const fallbackChars = (STATE.fashionCharacters && STATE.fashionCharacters.length)
        ? STATE.fashionCharacters
        : ((STATE.charLib && STATE.charLib.characters) || []);

      let found = libChars.find(c => (c.id || c.key) === charKey);
      let baseImg = "";
      let sheetImg = "";
      let charName = charKey;

      if (found) {
        baseImg = found.bg_ref_path || found.pose_sheet_path || "";
        sheetImg = found.pose_sheet_path || found.bg_ref_path || "";
        charName = found.name || charKey;
      } else {
        found = fallbackChars.find(c => (c.key || c.id) === charKey);
        if (!found) return;
        baseImg = found.bedroom_ref_abs || found.ref_image_abs || "";
        sheetImg = found.wardrobe_sheet_abs || found.ref_image_abs || "";
        charName = found.name || charKey;
      }

      const inpChar = document.getElementById("inpFashionBaseChar");
      const inpSheet = document.getElementById("inpFashionCharSheet");
      if (inpChar && baseImg) inpChar.value = baseImg;
      if (inpSheet && sheetImg) inpSheet.value = sheetImg;

      if (STATE.fashionProject) {
        if (baseImg) {
          STATE.fashionProject.base_char_2k = {
            filename: baseImg.split(/[\\/]/).pop(),
            path: baseImg,
            width: 1536,
            height: 2752,
            is_2k: true,
          };
        }
        if (sheetImg) {
          STATE.fashionProject.char_sheet_2k = {
            asset_key: "char_sheet_2k",
            filename: sheetImg.split(/[\\/]/).pop(),
            path: sheetImg,
          };
        }
        renderFashionMotionStudio();
      }
      showFashionBanner(`👤 Đã chọn Nhân Vật <b>${charName}</b> từ Thư Viện Nhân Vật và tự động gắn Ảnh Character Sheet 2K + Bối Cảnh 2K!`);
    }

    async function promptAddNewFashionCharacter() {
      const pickPose = await apiGet("/api/pick_file?kind=image");
      if (!pickPose || !pickPose.ok || !pickPose.path) return;
      const fn = pickPose.path.split(/[\\/]/).pop();
      const defaultName = fn.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ");
      const charName = window.prompt("Nhập tên Nhân Vật Thời Trang mới:", `Người Mẫu ${defaultName}`);
      if (!charName) return;

      const curBg = document.getElementById("inpFashionBaseChar")?.value || pickPose.path;
      showFashionBanner(`⏳ Đang lưu nhân vật mới <b>${charName}</b> vào Thư Viện Nhân Vật Thời Trang...`);
      const res = await apiPost("/api/fashion_motion/add_character", {
        name: charName.trim(),
        pose_sheet_path: pickPose.path,
        bg_ref_path: curBg,
        desc: `Nhân vật thời trang (${fn})`,
      });
      if (res && res.ok && res.character) {
        if (!STATE.fashionLibrary) STATE.fashionLibrary = { characters: [], outfits: [] };
        if (!Array.isArray(STATE.fashionLibrary.characters)) STATE.fashionLibrary.characters = [];
        STATE.fashionLibrary.characters.push(res.character);
        populateFashionCharacterPicker();
        const sel = document.getElementById("selFashionCharFromLib");
        if (sel) sel.value = res.character.id;
        onSelectFashionCharacterFromLibrary(res.character.id);
        showFashionBanner(`✅ Đã thêm Nhân Vật <b>${res.character.name}</b> vào Thư Viện và chọn làm Nhân Vật hiện tại!`);
      } else {
        showFashionBanner(`❌ Lỗi thêm nhân vật: ${(res && res.error) || "Không xác định"}`, true);
      }
    }

    async function pickAndDeconstructNewOutfit2K() {
      const pickRes = await apiGet("/api/pick_file?kind=image");
      if (!pickRes || !pickRes.ok || !pickRes.path) return;
      const rawPath = pickRes.path;
      const fn = rawPath.split(/[\\/]/).pop();
      const defaultName = `Bộ ${(STATE.fashionOutfits || []).length + 1}: ${fn.replace(/\.[^.]+$/, "")}`;
      const outfitName = window.prompt("Nhập tên Bộ Đồ / Sản Phẩm Mới (sẽ tự động tách nền trắng 2K chỉ giữ quần áo + phụ kiện):", defaultName) || defaultName;
      const modelMode = document.getElementById("selDeconstructOutfitModel")?.value || "nano_banana";

      showFashionBanner(`⏳ Đang tách quần áo <b>${fn}</b> ra Ảnh Tham Chiếu Nền Trắng 2K bằng <b>${modelMode.toUpperCase()}</b>...`);
      if (typeof toast === "function") toast("🪄 Đang tách sản phẩm ra ảnh nền trắng 2K...", "info");

      const res = await apiPost("/api/fashion_motion/deconstruct_outfit_2k", {
        raw_image_path: rawPath,
        outfit_name: outfitName,
        model_mode: modelMode,
        project_id: STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19",
      });

      if (res && res.ok && res.outfit) {
        const newOutfit = Object.assign({}, res.outfit, { enabled: true });
        if (!Array.isArray(STATE.fashionOutfits)) STATE.fashionOutfits = [];
        STATE.fashionOutfits.push(newOutfit);
        renderFashionOutfitsList();
        showFashionBanner(`✅ Đã tách thành công Sản Phẩm Nền Trắng 2K: <b>${newOutfit.filename}</b> (${res.method_used || modelMode}) và thêm vào Bộ #${STATE.fashionOutfits.length}!`);
        if (typeof toast === "function") toast(`✅ Đã tạo Product Sheet 2K: ${newOutfit.filename}`, "ok");
      } else {
        const err = (res && res.error) || "Không thể tách ảnh sản phẩm";
        showFashionBanner(`❌ Lỗi tách sản phẩm nền trắng 2K: ${err}`, true);
      }
    }

    async function deconstructSingleOutfitToWhiteBg2K(idx) {
      const item = (STATE.fashionOutfits || [])[idx];
      if (!item || !item.path) return;
      const modelMode = document.getElementById("selDeconstructOutfitModel")?.value || "nano_banana";
      showFashionBanner(`⏳ Đang chuẩn hóa Bộ #${idx + 1} (<b>${item.filename}</b>) thành Ảnh Tham Chiếu Quần Áo Nền Trắng 2K (${modelMode.toUpperCase()})...`);
      const res = await apiPost("/api/fashion_motion/deconstruct_outfit_2k", {
        raw_image_path: item.path,
        outfit_name: item.name || `Bộ ${idx + 1}`,
        outfit_desc: item.short_desc || "",
        model_mode: modelMode,
        project_id: STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19",
      });
      if (res && res.ok && res.outfit) {
        STATE.fashionOutfits[idx] = Object.assign({}, item, res.outfit, { enabled: item.enabled !== false });
        renderFashionOutfitsList();
        showFashionBanner(`✅ Đã chuẩn hóa Bộ #${idx + 1} thành ảnh nền trắng 2K: <b>${res.outfit.filename}</b>!`);
      } else {
        showFashionBanner(`❌ Lỗi tách nền trắng 2K: ${(res && res.error) || "Không xác định"}`, true);
      }
    }

    async function populateFashionProductStorePicker(forceReload = false) {
      const sel = document.getElementById("selFashionProdFromStore");
      if (!sel) return;
      if (forceReload || !STATE.productsStore || !STATE.productsStore.length) {
        try {
          const r = await apiGet("/api/products-store");
          if (r && r.ok && Array.isArray(r.items)) {
            STATE.productsStore = r.items;
          }
        } catch (e) {}
      }
      const storeItems = STATE.productsStore || [];
      const projItems = STATE.projects || [];
      const options = [`<option value="">-- 🛍️ Chọn sản phẩm từ Kho Sản Phẩm (${storeItems.length} SP) / Dự Án (${projItems.length} SP) để lấy ảnh quần áo gốc --</option>`];
      const seen = new Set();
      storeItems.forEach(it => {
        const pid = String(it.product_id || it.id || "");
        if (!pid || seen.has(pid)) return;
        seen.add(pid);
        const imgCnt = (it.local_images || []).length;
        options.push(`<option value="${pid}">🛍️ [${pid}] ${(it.title || it.name || pid).slice(0, 68)} (${imgCnt} ảnh gốc)</option>`);
      });
      projItems.forEach(p => {
        const pid = String(p.id || "");
        if (!pid || seen.has(pid)) return;
        seen.add(pid);
        options.push(`<option value="${pid}">📁 [${pid}] ${(p.name || pid).slice(0, 68)}</option>`);
      });
      sel.innerHTML = options.join("");
    }

    async function onSelectFashionProductFromStore(pid) {
      const strip = document.getElementById("fashionStoreProdImagesStrip");
      if (!strip) return;
      if (!pid) {
        strip.style.display = "none";
        strip.innerHTML = "";
        return;
      }
      strip.style.display = "block";
      strip.innerHTML = `<div style="font-size:11px; color:#93c5fd;">⏳ Đang tải danh sách ảnh sản phẩm gốc của <b>${pid}</b>...</div>`;

      let images = [];
      let prodTitle = pid;
      const storeHit = (STATE.productsStore || []).find(x => String(x.product_id || x.id) === String(pid));
      if (storeHit && Array.isArray(storeHit.local_images) && storeHit.local_images.length) {
        images = storeHit.local_images;
        prodTitle = storeHit.title || storeHit.name || pid;
      } else {
        const rProj = await apiGet(`/api/project?id=${encodeURIComponent(pid)}`);
        if (rProj && rProj.ok && rProj.project) {
          prodTitle = rProj.project.name || pid;
          images = rProj.project.product_images || [];
        }
      }

      if (!images.length) {
        strip.innerHTML = `<div style="font-size:11px; color:#fca5a5;">⚠️ Sản phẩm <b>${prodTitle}</b> chưa có ảnh tải về máy. Hãy bấm tải ảnh ở tab Sản Phẩm trước.</div>`;
        return;
      }

      const safeTitle = String(prodTitle || pid).replace(/'/g, "\\'").replace(/"/g, "&quot;");
      strip.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:6px;">
          <span style="font-size:11px; font-weight:800; color:#fde68a;">🖼️ Ảnh Gốc Của Sản Phẩm: <span style="color:#fff;">${prodTitle}</span> (${images.length} ảnh) — Chọn ảnh để Tách Quần Áo + Phụ Kiện 2K hoặc Đưa Vào Bộ Đồ:</span>
        </div>
        <div style="display:flex; gap:8px; overflow-x:auto; padding-bottom:4px;">
          ${images.map((imgP, iIdx) => {
            const u = `/api/media?path=${encodeURIComponent(imgP)}`;
            const safeP = String(imgP).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
            return `
              <div style="background:#070b14; border:1px solid rgba(99,102,241,0.45); border-radius:7px; padding:6px; width:155px; flex-shrink:0; display:flex; flex-direction:column; gap:5px;">
                <div style="width:100%; height:135px; border-radius:5px; overflow:hidden; background:#000; cursor:pointer;"
                     onclick="openLightbox('${u}', 'Ảnh SP Gốc #${iIdx + 1}: ${safeTitle}')">
                  <img src="${u}" style="width:100%; height:100%; object-fit:cover;" />
                </div>
                <div style="font-size:9.5px; color:#cbd5e1; text-align:center; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Ảnh gốc #${iIdx + 1}</div>
                <button class="btn btn-xs btn-amber" style="width:100%; justify-content:center; font-size:9.5px; padding:4px;"
                        onclick="prepareDeconstructOutfitFromStoreImage('${safeP}', '${safeTitle}')"
                        title="Biến ảnh quần áo gốc này thành Ảnh Product Sheet Tách Riêng Quần Áo + Phụ Kiện Nền Trắng 2K">
                  🪄 Tách Quần Áo+Phụ Kiện 2K
                </button>
                <button class="btn btn-xs btn-success" style="width:100%; justify-content:center; font-size:9.5px; padding:4px;"
                        onclick="addStoreImageDirectlyAsFashionOutfit('${safeP}', '${safeTitle}')">
                  ➕ Đưa Luôn Vào Bộ Đồ
                </button>
              </div>
            `;
          }).join("")}
        </div>
      `;
    }

    function addStoreImageDirectlyAsFashionOutfit(imgPath, prodTitle) {
      if (!imgPath) return;
      const fn = imgPath.split(/[\\/]/).pop();
      const idx = (STATE.fashionOutfits || []).length + 1;
      STATE.fashionOutfits.push({
        id: `outfit_store_${idx}_${Date.now()}`,
        filename: fn,
        path: imgPath,
        name: `Bộ ${idx}: ${(prodTitle || fn).slice(0, 36)}`,
        short_desc: `bộ trang phục ${prodTitle || fn} theo đúng ảnh tham chiếu ${fn}`,
        en_desc: `exact fashion outfit from product reference image ${fn}`,
        width: 1536,
        height: 2752,
        is_2k: true,
        enabled: true,
      });
      renderFashionOutfitsList();
      showFashionBanner(`👗 Đã thêm ảnh sản phẩm <b>${fn}</b> vào Danh Sách Bộ Đồ Thay Theo Nhạc (Bộ #${idx})!`);
    }

    function prepareDeconstructOutfitFromStoreImage(imgPath, prodTitle) {
      STATE.selectedFashionRawProdImage = imgPath;
      const det = document.getElementById("detailsFashionAuxTools");
      if (det) det.open = true;
      selectFashionPromptBuilderTab("deconstructed_outfit_flatlay_2k");
      const inpRef = document.getElementById("inpFashionStdPromptRefImg");
      if (inpRef) inpRef.value = imgPath;
      const card = document.getElementById("cardFashionPromptsBuilder");
      if (card) card.scrollIntoView({ behavior: "smooth" });
      showFashionBanner(`🪄 Đã nạp ảnh gốc <b>${imgPath.split(/[\\/]/).pop()}</b> vào <b>Prompt #1 (Tách Quần Áo + Phụ Kiện Nền Trắng 2K)</b>!`);
    }

    function selectFashionPromptBuilderTab(promptKey, btnEl) {
      STATE.activeFashionPromptTab = promptKey || "deconstructed_outfit_flatlay_2k";
      const det = document.getElementById("detailsFashionAuxTools");
      if (det) det.open = true;
      const tabsBar = document.getElementById("fashionStdPromptTabs");
      if (tabsBar && btnEl) {
        tabsBar.querySelectorAll("button").forEach(b => {
          b.className = "btn btn-xs btn-outline";
        });
        btnEl.className = "btn btn-xs btn-amber";
      }
      renderFashionStandardPromptBox();
    }

    function renderFashionStandardPromptBox() {
      const box = document.getElementById("fashionStdPromptBody");
      if (!box) return;
      const key = STATE.activeFashionPromptTab || "deconstructed_outfit_flatlay_2k";
      const stdMap = STATE.fashionStandardPrompts || {};
      const item = stdMap[key] || {
        id: key,
        title: "Prompt Chuẩn Thời Trang 2K",
        badge: "2K FASHION AI",
        aspect_ratio: "4:5 (2048×2559 2K)",
        guide_vn: "Đính kèm ảnh sản phẩm gốc hoặc Character Sheet để tạo ảnh 2K chuẩn thương mại.",
        rendered_prompt: "",
      };

      const sampleMap = {
        deconstructed_outfit_flatlay_2k: "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/05_Product_Sheet_Quan_Sooc_Trang_2K.png",
        wardrobe_4looks_character_sheet_2k: "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/01_Character_Sheet_4_Outfits_2K.png",
        fashion_model_turnaround_5poses_2k: "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/02_Character_Sheet_Basic_Poses_2K.png",
        base_char_bedroom_2k: "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/09_NV5_Phong_Tu_Go_Mo_Dau_2K.png",
      };
      const sampleRel = sampleMap[key] || sampleMap.deconstructed_outfit_flatlay_2k;
      const sampleUrl = `/api/media?path=${encodeURIComponent(sampleRel)}`;
      const defaultRefImg = STATE.selectedFashionRawProdImage
        || (key === "wardrobe_4looks_character_sheet_2k" ? (document.getElementById("inpFashionCharSheet")?.value || "flow_final_pipeline/characters/nv5_ref.png") : "")
        || (key === "base_char_bedroom_2k" ? "flow_final_pipeline/characters/nv5_ref.png" : "");

      box.innerHTML = `
        <div style="display:grid; grid-template-columns: 165px 1fr; gap:12px; align-items:start; background:#070a14; border:1px solid rgba(139,92,246,0.35); border-radius:8px; padding:10px;">
          <div style="display:flex; flex-direction:column; gap:5px;">
            <div style="font-size:10px; font-weight:800; color:#c4b5fd; text-align:center;">🖼️ ẢNH MẪU KẾT QUẢ 2K</div>
            <div style="width:100%; aspect-ratio:4/5; border-radius:7px; overflow:hidden; background:#000; border:1px solid rgba(139,92,246,0.5); cursor:pointer;"
                 onclick="openLightbox('${sampleUrl}', '${(item.title || '').replace(/'/g, "\\'")}')">
              <img src="${sampleUrl}" style="width:100%; height:100%; object-fit:cover;" />
            </div>
            <span class="badge" style="background:rgba(16,185,129,0.18); color:#34d399; text-align:center; justify-content:center; font-size:9.5px;">${item.aspect_ratio || '2048×2559 2K'}</span>
          </div>

          <div style="display:flex; flex-direction:column; gap:7px;">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;">
              <span style="font-size:12px; font-weight:800; color:#fde68a;">${item.title || ''}</span>
              <span class="badge" style="background:rgba(236,72,153,0.2); color:#f9a8d4; border:1px solid rgba(236,72,153,0.45);">${item.badge || '2K'}</span>
            </div>
            <div style="font-size:11px; color:#cbd5e1; line-height:1.4; background:rgba(139,92,246,0.1); border-left:3px solid #8b5cf6; padding:5px 8px; border-radius:4px;">
              💡 ${item.guide_vn || ''}
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <span style="font-size:10.5px; font-weight:700; color:#93c5fd; white-space:nowrap;">📎 Ảnh Gốc Đính Kèm (SP Quần Áo / NV5):</span>
              <input id="inpFashionStdPromptRefImg" value="${(defaultRefImg || '').replace(/"/g, '&quot;')}" placeholder="Chọn ảnh quần áo gốc từ Kho SP hoặc bấm Chọn Ảnh từ máy..." style="font-size:11px; flex:1;" />
              <button class="btn btn-xs btn-outline" onclick="pickFashionFile('inpFashionStdPromptRefImg', 'image')">📂 Chọn Ảnh Gốc</button>
            </div>
            <div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="font-size:10.5px; font-weight:800; color:#a5b4fc;">📝 PROMPT CHUẨN 2K (CÓ THỂ CHỈNH SỬA MÔ TẢ QUẦN ÁO & PHỤ KIỆN):</span>
                <button class="btn btn-xs btn-primary" style="padding:2px 9px; font-size:10px;"
                        onclick="navigator.clipboard.writeText(document.getElementById('txtFashionStdPromptEditor').value); showFashionBanner('📋 Đã copy Prompt Chuẩn Thời Trang 2K vào Clipboard!');">
                  📋 Copy Prompt Chuẩn
                </button>
              </div>
              <textarea id="txtFashionStdPromptEditor" rows="5" style="font-family:Consolas,monospace; font-size:11px; line-height:1.45; width:100%; background:#050811; color:#f1f5f9; border:1px solid rgba(99,102,241,0.4); border-radius:6px; padding:8px;">${(item.rendered_prompt || '').replace(/</g, '&lt;')}</textarea>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
              <button class="btn btn-xs btn-success" style="padding:6px 12px; font-weight:800;" onclick="runGenerateFashion2kAssetOnFlow('${key}')">
                ✨ Tạo Ảnh 2K Trực Tiếp Trên Google Flow (Nano Banana 2.1 2K) & Đưa Vào Dự Án
              </button>
              <span id="fashionStdPromptGenStatus" style="font-size:11px; color:#34d399;"></span>
            </div>
          </div>
        </div>
      `;
    }

    async function runGenerateFashion2kAssetOnFlow(assetType) {
      const promptStr = document.getElementById("txtFashionStdPromptEditor")?.value || "";
      const refImg = document.getElementById("inpFashionStdPromptRefImg")?.value || "";
      const stEl = document.getElementById("fashionStdPromptGenStatus");
      const refs = [];
      if (refImg.trim()) refs.push(refImg.trim());
      if (assetType === "wardrobe_4looks_character_sheet_2k") {
        (STATE.fashionOutfits || []).filter(o => o.enabled !== false).forEach(o => {
          if (o.path && !refs.includes(o.path)) refs.push(o.path);
        });
      }
      if (stEl) stEl.innerHTML = "⏳ Đang gửi lên Google Flow tạo ảnh 2K (Nano Banana 2.1 + Upscale 2K)...";
      showFashionBanner("⏳ Đang tạo ảnh Thời Trang Chuẩn 2K trên Google Flow...");

      const res = await apiPost("/api/fashion_motion/generate_2k_asset", {
        asset_type: assetType,
        prompt: promptStr,
        ref_image_paths: refs,
        project_id: STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19",
      });
      if (res && res.ok && res.path) {
        if (stEl) stEl.innerHTML = `✅ Đã tạo xong ảnh 2K: <b>${res.filename}</b> (${res.width}×${res.height})`;
        if (assetType === "deconstructed_outfit_flatlay_2k") {
          addStoreImageDirectlyAsFashionOutfit(res.path, `Product Sheet 2K (${res.filename})`);
        } else if (assetType === "wardrobe_4looks_character_sheet_2k" || assetType === "fashion_model_turnaround_5poses_2k") {
          const inpSheet = document.getElementById("inpFashionCharSheet");
          if (inpSheet) inpSheet.value = res.path;
        } else if (assetType === "base_char_bedroom_2k") {
          const inpChar = document.getElementById("inpFashionBaseChar");
          if (inpChar) inpChar.value = res.path;
        }
        showFashionBanner(`✅ Đã tạo thành công ảnh 2K <b>${res.filename}</b> (${res.width}×${res.height}) và tự động gắn vào dự án!`);
      } else {
        const errMsg = (res && res.error) || "Không thể tạo ảnh 2K";
        if (stEl) stEl.innerHTML = `<span style="color:#f87171;">❌ Lỗi: ${errMsg}</span>`;
        showFashionBanner(`❌ Lỗi tạo ảnh 2K: ${errMsg}`, true);
      }
    }

    async function pickFashionFile(inputId, kind = "image") {
      const res = await apiGet(`/api/pick_file?kind=${encodeURIComponent(kind)}`);
      if (res && res.ok && res.path) {
        const inp = document.getElementById(inputId);
        if (inp) inp.value = res.path;
      }
    }

    async function addCustomFashionOutfitFromDisk() {
      const res = await apiGet("/api/pick_file?kind=image");
      if (!res || !res.ok || !res.path) return;
      const fn = res.path.split(/[\\/]/).pop();
      const idx = (STATE.fashionOutfits || []).length + 1;
      STATE.fashionOutfits.push({
        id: `outfit_custom_${idx}_${Date.now()}`,
        filename: fn,
        path: res.path,
        name: `Bộ ${idx}: ${fn}`,
        short_desc: `trang phục thời trang theo đúng ảnh tham chiếu ${fn}`,
        en_desc: `exact fashion outfit matching reference image ${fn}`,
        width: 1536,
        height: 2752,
        is_2k: true,
        enabled: true,
      });
      renderFashionOutfitsList();
      showFashionBanner(`👗 Đã thêm Bộ Đồ #${idx} (<b>${fn}</b>) vào danh sách phối đồ!`);
    }

    function renderFashionOutfitsList() {
      const grid = document.getElementById("fashionOutfitsGrid");
      if (!grid) return;
      const list = STATE.fashionOutfits || [];
      grid.innerHTML = list.map((o, idx) => {
        const oEnc = encodeURIComponent(o.path || '');
        const imgUrl = `/api/media?path=${oEnc}`;
        const lbPath = o.lookbook_model_path || (o.lookbook_model_filename ? `ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/${o.lookbook_model_filename}` : "");
        const lbUrl = lbPath ? `/api/media?path=${encodeURIComponent(lbPath)}` : "";
        const safeName = (o.name || o.filename || '').replace(/'/g, "\\'");
        return `
          <div style="background:#0a0f1d; border:1px solid ${o.enabled !== false ? 'rgba(245,158,11,0.55)' : 'var(--border)'}; border-radius:8px; padding:8px; display:flex; gap:8px; align-items:center;">
            <div style="display:flex; gap:4px; flex-shrink:0;">
              <div style="width:54px; height:76px; border-radius:6px; overflow:hidden; background:#000; cursor:pointer; border:1px solid rgba(245,158,11,0.45); position:relative;"
                   onclick="openLightbox('${imgUrl}', '${safeName} (Product Sheet 2K)')"
                   title="Bấm để xem Ảnh Tách Quần Áo & Phụ Kiện 2K">
                <img src="${imgUrl}" style="width:100%; height:100%; object-fit:cover;" />
                <span style="position:absolute; bottom:2px; left:2px; background:rgba(0,0,0,0.78); color:#fde68a; font-size:8px; font-weight:800; padding:0 4px; border-radius:3px;">Đồ 2K</span>
              </div>
              ${lbUrl ? `
                <div style="width:54px; height:76px; border-radius:6px; overflow:hidden; background:#000; cursor:pointer; border:1px solid rgba(236,72,153,0.5); position:relative;"
                     onclick="openLightbox('${lbUrl}', 'NV5 Mặc ${safeName} (2K Lookbook)')"
                     title="Bấm để xem Ảnh NV5 Mặc Bộ Đồ Này Trong Phòng Thay Đồ 2K">
                  <img src="${lbUrl}" style="width:100%; height:100%; object-fit:cover;" />
                  <span style="position:absolute; bottom:2px; left:2px; background:rgba(236,72,153,0.85); color:#fff; font-size:8px; font-weight:800; padding:0 4px; border-radius:3px;">Mẫu 2K</span>
                </div>
              ` : ''}
            </div>
            <div style="flex:1; min-width:0;">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:4px; flex-wrap:wrap;">
                <label style="display:flex; align-items:center; gap:5px; font-size:11px; font-weight:800; color:#fde68a; cursor:pointer; margin:0;">
                  <input type="checkbox" ${o.enabled !== false ? 'checked' : ''} onchange="STATE.fashionOutfits[${idx}].enabled = this.checked" />
                  <span>Bộ #${idx + 1}</span>
                </label>
                <div style="display:flex; gap:3px; align-items:center; flex-wrap:wrap;">
                  <button class="btn btn-xs btn-outline" style="padding:1px 5px; font-size:8.5px; color:#93c5fd;"
                          onclick="openLightbox('${imgUrl}', '${safeName} (Product Sheet 2K)')" title="Xem phóng to ảnh 2K">🔍 Xem</button>
                  <button class="btn btn-xs btn-outline" style="padding:1px 5px; font-size:8.5px; color:#fde68a;"
                          onclick="changeSingleFashionOutfitImage(${idx})" title="Chọn ảnh sản phẩm khác từ máy tính cho Bộ #${idx + 1}">📂 Đổi</button>
                  <button class="btn btn-xs btn-outline" style="padding:1px 5px; font-size:8.5px; color:#f9a8d4; border-color:rgba(236,72,153,0.45);"
                          onclick="deconstructSingleOutfitToWhiteBg2K(${idx})"
                          title="Tách sản phẩm này ra Ảnh Tham Chiếu Nền Trắng Chuẩn 2K (ChatGPT / Banana 2K)">
                    🪄 Tách 2K
                  </button>
                  <button class="btn btn-xs btn-outline" style="padding:1px 5px; font-size:8.5px;"
                          onclick="openFolderEncoded('${oEnc}')" title="Mở vị trí file ảnh trong Explorer">📂</button>
                  <button class="btn btn-xs btn-danger" style="padding:1px 5px; font-size:8.5px;"
                          onclick="removeSingleFashionOutfit(${idx})" title="Xoá Bộ #${idx + 1} khỏi danh sách">🗑️</button>
                </div>
              </div>
              <div style="font-size:10.5px; font-weight:700; color:#fff; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${o.name || o.filename}">${o.name || o.filename}</div>
              <div style="font-size:9.5px; color:#93c5fd; font-family:Consolas,monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">[${o.filename}]</div>
              <input value="${(o.short_desc || '').replace(/"/g, '&quot;')}"
                     onchange="STATE.fashionOutfits[${idx}].short_desc = this.value"
                     placeholder="Mô tả chi tiết bộ đồ..."
                     style="margin-top:4px; font-size:10px; padding:3px 6px; width:100%;" />
            </div>
          </div>
        `;
      }).join("");
    }

    async function onChangeFashionGenerationMode(modeVal) {
      const normMode = (String(modeVal || "").toLowerCase().includes("i2v") || String(modeVal || "").toLowerCase().includes("chained")) ? "chained_i2v" : "video_ref";
      const selMode = document.getElementById("selFashionGenerationMode");
      if (selMode && selMode.value !== normMode) selMode.value = normMode;
      const selStyle = document.getElementById("selFashionPromptStyle");
      if (selStyle) selStyle.value = normMode === "chained_i2v" ? "chained_i2v" : "timeline_pro";

      if (!STATE.fashionProject) return;
      const slug = STATE.fashionProject.project_id || "fashion_lookbook_chan_vay_6e19";
      STATE.fashionProject.generation_mode = normMode;
      STATE.fashionProject.prompt_style = normMode === "chained_i2v" ? "chained_i2v" : "timeline_pro";

      try {
        const res = await apiPost("/api/fashion_motion/switch_mode", {
          project_id: slug,
          generation_mode: normMode,
        });
        if (res && res.ok && res.project) {
          STATE.fashionProject = res.project;
          if (Array.isArray(res.projects)) STATE.fashionProjectsList = res.projects;
        }
      } catch (e) {}

      renderFashionMotionStudio();
      showFashionBanner(
        normMode === "chained_i2v"
          ? `✨ Đã chuyển sang chế độ <b>Chained Img2Video + Timeline 0.1s Chuẩn Nhạc</b> (Không dùng Video Ref • Phân cảnh 2 tự động cắt Frame cuối Cảnh 1 <code>scene_s1_last_frame_2k.png</code> để nối tiếp liền mạch)!`
          : `🎬 Đã chuyển sang chế độ <b>Motion Control Video Ref</b> (Dùng Video Gốc làm Ref • Phân cảnh 2 tự động dùng Frame cuối Cảnh 1 <code>scene_s1_last_frame_2k.png</code> làm ảnh mở đầu nối tiếp)!`
      );
    }

    function switchFashionPromptStyleUI(styleVal) {
      if (!STATE.fashionProject) return;
      const isI2V = styleVal === "chained_i2v";
      const normMode = isI2V ? "chained_i2v" : "video_ref";
      const selMode = document.getElementById("selFashionGenerationMode");
      if (selMode && selMode.value !== normMode) selMode.value = normMode;
      STATE.fashionProject.generation_mode = normMode;
      STATE.fashionProject.prompt_style = styleVal;
      (STATE.fashionProject.scenes || []).forEach(sc => {
        sc.active_prompt_style = styleVal;
        sc.generation_mode = normMode;
        if (styleVal === "chained_i2v") {
          sc.prompt = sc.prompt_chained_i2v || sc.prompt;
        } else if (styleVal === "concise_flow") {
          sc.prompt = sc.prompt_concise_flow || sc.prompt_timeline_pro || sc.prompt;
        } else {
          sc.prompt = sc.prompt_timeline_pro || sc.prompt;
        }
      });
      renderFashionScenesTimeline();
    }

    function renderFashionMotionStudio() {
      const proj = STATE.fashionProject;
      if (!proj) return;

      const curGenMode = proj.generation_mode || "chained_i2v";
      const selGenMode = document.getElementById("selFashionGenerationMode");
      if (selGenMode) selGenMode.value = curGenMode;
      const selPStyle = document.getElementById("selFashionPromptStyle");
      if (selPStyle) selPStyle.value = curGenMode === "chained_i2v" ? "chained_i2v" : (proj.prompt_style || "timeline_pro");

      const inpChar = document.getElementById("inpFashionBaseChar");
      if (inpChar && proj.base_char_2k?.path) inpChar.value = proj.base_char_2k.path;

      const inpSheet = document.getElementById("inpFashionCharSheet");
      if (inpSheet && proj.char_sheet_2k?.path) inpSheet.value = proj.char_sheet_2k.path;

      const inpVid = document.getElementById("inpFashionRefVideo");
      if (inpVid && proj.reference_video?.path) inpVid.value = proj.reference_video.path;

      const charBox = document.getElementById("fashionCharPreviewBox");
      if (charBox && proj.base_char_2k) {
        const cEnc = encodeURIComponent(proj.base_char_2k.path || '');
        const cUrl = `/api/media?path=${cEnc}`;
        const csEnc = proj.char_sheet_2k?.path ? encodeURIComponent(proj.char_sheet_2k.path) : "";
        const csUrl = csEnc ? `/api/media?path=${csEnc}` : "";
        charBox.innerHTML = `
          <div style="width:52px; height:74px; border-radius:6px; overflow:hidden; border:1px solid #ec4899; cursor:pointer; flex-shrink:0;"
               onclick="openLightbox('${cUrl}', 'Ảnh Nhân Vật Gốc 2K: ${proj.base_char_2k.filename} (${proj.base_char_2k.width}×${proj.base_char_2k.height})')">
            <img src="${cUrl}" style="width:100%; height:100%; object-fit:cover;" />
          </div>
          ${csUrl ? `
            <div style="width:52px; height:74px; border-radius:6px; overflow:hidden; border:1px solid #8b5cf6; cursor:pointer; flex-shrink:0;"
                 onclick="openLightbox('${csUrl}', 'Ảnh Bối Cảnh Phòng Tham Chiếu 2K: ${proj.char_sheet_2k.filename}')">
              <img src="${csUrl}" style="width:100%; height:100%; object-fit:cover;" />
            </div>
          ` : ''}
          <div style="font-size:10.5px; color:#cbd5e1; line-height:1.35; flex:1; min-width:0;">
            <div>✅ <b>Nhân vật 2K:</b> <code style="color:#f9a8d4;">${proj.base_char_2k.filename}</code> (${proj.base_char_2k.width}×${proj.base_char_2k.height})</div>
            ${proj.char_sheet_2k ? `<div>🏠 <b>Bối cảnh 2K:</b> <code style="color:#c4b5fd;">${proj.char_sheet_2k.filename}</code></div>` : ''}
            <div style="display:flex; gap:4px; flex-wrap:wrap; margin-top:4px;">
              <button class="btn btn-xs btn-outline" style="font-size:9px; padding:2px 6px;" onclick="openLightbox('${cUrl}', 'Ảnh Nhân Vật 2K: ${proj.base_char_2k.filename}')">🔍 Xem NV</button>
              ${csUrl ? `<button class="btn btn-xs btn-outline" style="font-size:9px; padding:2px 6px;" onclick="openLightbox('${csUrl}', 'Ảnh Bối Cảnh 2K: ${proj.char_sheet_2k.filename}')">🔍 Xem Bối Cảnh</button>` : ''}
              <button class="btn btn-xs btn-outline" style="font-size:9px; padding:2px 6px;" onclick="openFolderEncoded('${cEnc}')">📂 Mở Folder</button>
            </div>
          </div>
        `;
      }

      const sumBox = document.getElementById("fashionVideoSplitSummary");
      if (sumBox && proj.split_plan && proj.reference_video) {
        const sp = proj.split_plan;
        const rv = proj.reference_video;
        const gCuts = (proj.global_cuts_info?.visual_cuts || []).map(c => `${c.timestamp_colon}s`).join(", ") || "Tự động theo nhịp";
        const gBeats = (proj.global_cuts_info?.audio_beats || []).slice(0, 6).map(b => `${b.timestamp_colon}s`).join(", ") || "Tự động";
        const rvEnc = encodeURIComponent(rv.path || '');
        const refVidUrl = `/api/media?path=${rvEnc}#t=0.5`;
        sumBox.innerHTML = `
          <div style="display:flex; gap:10px; align-items:center;">
            <div style="width:56px; height:92px; border-radius:6px; overflow:hidden; background:#000; border:1px solid rgba(6,182,212,0.5); flex-shrink:0; cursor:pointer; position:relative;"
                 onclick="toggleFashionInlineVideo('fStep1RefVid', 'btnStep1RefPlay')"
                 title="Bấm vào video để Phát/Dừng có tiếng">
              <video id="fStep1RefVid" class="fashion-clean-video" preload="metadata" onloadedmetadata="if(this.currentTime===0){try{this.currentTime=0.5;}catch(e){}}" style="width:100%; height:100%; object-fit:cover;" src="${refVidUrl}"></video>
              <span style="position:absolute; bottom:2px; left:2px; right:2px; background:rgba(0,0,0,0.78); color:#67e8f9; font-size:8px; font-weight:800; text-align:center; border-radius:3px;">▶️ Bấm phát</span>
            </div>
            <div style="flex:1; min-width:0; line-height:1.4;">
              <div>🎯 <b>Video Gốc:</b> <code style="color:#fff;">${rv.filename}</code> — Dài <b>${rv.duration}s</b> (${rv.width}×${rv.height} • ${rv.fps} FPS)</div>
              <div style="color:#fde68a; font-weight:800;">✂️ ${sp.reason} (Model: <code>${sp.model_key_edit}</code>)</div>
              <div style="font-size:10px; color:#cbd5e1;">👁️ Điểm cắt cảnh: <b style="color:#34d399;">${gCuts}</b> | 🎵 Nhịp Beat: <b>${gBeats}</b></div>
              <div style="display:flex; gap:4px; flex-wrap:wrap; margin-top:4px;">
                <button id="btnStep1RefPlay" class="btn btn-xs btn-success" style="font-size:9px; padding:2px 7px;" onclick="toggleFashionInlineVideo('fStep1RefVid', 'btnStep1RefPlay')">▶️ Phát</button>
                <button class="btn btn-xs btn-primary" style="font-size:9px; padding:2px 7px;" onclick="openVerticalVideoModal('${rvEnc}', '', '', 'Video Tham Chiếu Gốc: ${(rv.filename || '').replace(/'/g, '')} (${rv.duration}s)', '', '')">📱 Xem Dọc 9:16</button>
                <button class="btn btn-xs btn-outline" style="font-size:9px; padding:2px 7px;" onclick="openFileEncoded('${rvEnc}')">🖥️ Player Máy</button>
                <button class="btn btn-xs btn-outline" style="font-size:9px; padding:2px 7px;" onclick="openFolderEncoded('${rvEnc}')">📂 Mở File</button>
              </div>
            </div>
          </div>
        `;
      }

      renderFashionOutfitsList();
      renderFashionLiveMonitorBar();
      renderFashionScenesTimeline();
      renderFashionFinalPostProdCard();
      if (proj.status === "running_flow" && !STATE._fashionFlowPollTimer) {
        startFashionLiveStatusMonitor(proj.project_id);
      }
    }

    function _getFashionSceneStatusBadgeHtml(sc, outVidUrl) {
      const st = String(sc.status || "");
      const attempt = sc.attempt || 1;
      const maxAtt = sc.max_attempts || 4;
      const elapsed = sc.elapsed_sec ? ` • ${sc.elapsed_sec}s` : "";

      if (st.startsWith("retrying")) {
        return `<span class="badge" style="background:rgba(245,158,11,0.28); color:#fde68a; border:1px solid #f59e0b; font-weight:900;">🔁 Đang tự động Retry ngay (Lần ${attempt}/${maxAtt})</span>`;
      }
      if (st === "preparing" || st === "uploading_video" || st === "submitting") {
        return `<span class="badge" style="background:rgba(6,182,212,0.22); color:#67e8f9; border:1px solid #06b6d4; font-weight:800;">🚀 Đang gửi lên Google Flow (Lần ${attempt}/${maxAtt})</span>`;
      }
      if (st === "submitted_720p" || st.startsWith("rendering")) {
        return `<span class="badge" style="background:rgba(59,130,246,0.24); color:#93c5fd; border:1px solid #3b82f6; font-weight:800;">⏳ Đang tạo Video (Lần ${attempt}/${maxAtt}${elapsed})</span>`;
      }
      if (st === "upsampling_1080p") {
        return `<span class="badge" style="background:rgba(168,85,247,0.25); color:#e9d5ff; border:1px solid #a855f7; font-weight:800;">✨ Đang nâng cấp 1080p...</span>`;
      }
      if (st.startsWith("failed")) {
        return `<span class="badge" style="background:rgba(239,68,68,0.22); color:#fca5a5; border:1px solid #ef4444; font-weight:800;">❌ Lỗi (${st.replace('failed:', '')}) — Có thể Retry</span>`;
      }
      if (outVidUrl || st === "done") {
        return `<span class="badge badge-done">✅ Đã tạo Video Phân Cảnh (${sc.duration}s)</span>`;
      }
      return `<span class="badge badge-wait">⏳ Chờ tạo Video</span>`;
    }

    function renderFashionLiveMonitorBar() {
      const bars = [
        document.getElementById("fashionLiveMonitorBarTop"),
        document.getElementById("fashionLiveMonitorBar"),
      ].filter(Boolean);
      const proj = STATE.fashionProject;
      if (!bars.length || !proj) return;

      const scenes = proj.scenes || [];
      const activeScenes = scenes.filter(s => {
        const st = String(s.status || "");
        return st === "preparing" || st === "uploading_video" || st === "submitting" || st === "submitted_720p" || st === "upsampling_1080p" || st.startsWith("rendering") || st.startsWith("retrying");
      });
      const failedScenes = scenes.filter(s => String(s.status || "").startsWith("failed"));
      const doneScenes = scenes.filter(s => String(s.status || "") === "done" || !!s.output_video_path);

      if (!activeScenes.length && !failedScenes.length && proj.status !== "running_flow") {
        bars.forEach(b => {
          b.style.display = "none";
          b.innerHTML = "";
        });
        return;
      }

      // Tính phần trăm tiến trình trực quan
      let totalScore = 0;
      scenes.forEach(s => {
        const st = String(s.status || "");
        if (st === "done" || s.output_video_path) totalScore += 100;
        else if (st === "upsampling_1080p") totalScore += 84;
        else if (st.startsWith("rendering") || st === "submitted_720p") {
          const elSec = Number(s.elapsed_sec || 0);
          totalScore += Math.min(78, 35 + Math.floor(elSec * 0.4));
        } else if (st.startsWith("retrying")) totalScore += 32;
        else if (st === "submitting") totalScore += 28;
        else if (st === "uploading_video") totalScore += 20;
        else if (st === "preparing") totalScore += 12;
      });
      const pct = scenes.length
        ? (proj.final_video_ready && doneScenes.length === scenes.length ? 100 : Math.max(10, Math.min(96, Math.round(totalScore / scenes.length))))
        : 15;
      const elapsedSecTotal = STATE._fashionRunStartTs ? Math.max(1, Math.round((Date.now() - STATE._fashionRunStartTs) / 1000)) : 0;

      const scenePills = scenes.map(s => {
        const st = String(s.status || "ready");
        const att = s.attempt || 1;
        const maxAtt = s.max_attempts || 4;
        let color = "#94a3b8";
        let bg = "rgba(148,163,184,0.12)";
        let icon = "⏳";
        if (st === "done" || s.output_video_path) {
          color = "#34d399";
          bg = "rgba(16,185,129,0.16)";
          icon = "✅";
        } else if (st.startsWith("retrying")) {
          color = "#fde68a";
          bg = "rgba(245,158,11,0.22)";
          icon = "🔁";
        } else if (st.startsWith("failed")) {
          color = "#fca5a5";
          bg = "rgba(239,68,68,0.22)";
          icon = "❌";
        } else if (activeScenes.includes(s)) {
          color = "#67e8f9";
          bg = "rgba(6,182,212,0.18)";
          icon = "🔄";
        }
        return `
          <span style="display:inline-flex; align-items:center; gap:5px; padding:4px 10px; border-radius:6px; background:${bg}; color:${color}; border:1px solid ${color}66; font-size:11px; font-weight:800;">
            ${icon} Cảnh ${s.scene_index}: ${s.status_detail || st} (Lần ${att}/${maxAtt})
          </span>
        `;
      }).join("");

      const html = `
        <div style="display:flex; flex-direction:column; gap:7px;">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
            <div style="font-weight:900; color:#67e8f9; font-size:12px;">
              📡 TIẾN TRÌNH TẠO VIDEO GOOGLE FLOW (${proj.updated_at || 'Live'}${elapsedSecTotal ? ` • ⏱️ Đã chạy ${elapsedSecTotal}s` : ''}):
              <span style="color:#fdf2f8; font-weight:800;">${proj.status_message || 'Đang chạy tạo video trên Google Flow (Omni 1.1 Flash)...'}</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="badge" style="background:linear-gradient(135deg,#06b6d4,#10b981); color:#04131a; font-weight:900; font-size:11px; padding:3px 9px;">
                ⚡ Tiến độ: ${pct}% (${doneScenes.length}/${scenes.length} cảnh hoàn tất)
              </span>
              ${failedScenes.length ? `
                <button class="btn btn-xs btn-amber" style="font-weight:900; padding:5px 11px;" onclick="retryAllFailedFashionScenes(false)">
                  🔁 Retry Ngay ${failedScenes.length} Cảnh Lỗi
                </button>
              ` : ''}
            </div>
          </div>
          <div style="width:100%; height:8px; background:#060a14; border-radius:99px; overflow:hidden; border:1px solid rgba(6,182,212,0.4);">
            <div style="width:${pct}%; height:100%; background:linear-gradient(90deg,#ec4899,#06b6d4,#10b981); border-radius:99px; transition:width 0.4s;"></div>
          </div>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">${scenePills}</div>
        </div>
      `;

      bars.forEach(b => {
        b.style.display = "block";
        b.innerHTML = html;
      });
    }

    function renderFashionScenesTimeline() {
      const box = document.getElementById("fashionScenesTimelineContainer");
      const proj = STATE.fashionProject;
      if (!box || !proj) return;
      const scenes = proj.scenes || [];
      const genMode = proj.generation_mode || document.getElementById("selFashionGenerationMode")?.value || "chained_i2v";
      const styleVal = document.getElementById("selFashionPromptStyle")?.value || proj.prompt_style || (genMode === "chained_i2v" ? "chained_i2v" : "timeline_pro");
      const cacheBust = Date.now();

      box.innerHTML = scenes.map((sc, scIdx) => {
        const scNum = Number(sc.scene_index || (scIdx + 1));
        const clipEnc = encodeURIComponent(sc.ref_clip_path || '');
        const clipUrl = `/api/media?path=${clipEnc}&t=${cacheBust}#t=0.5`;
        const outVidPath = sc.output_video_path || "";
        const outVidEnc = outVidPath ? encodeURIComponent(outVidPath) : "";
        const outVidUrl = outVidEnc ? `/api/media?path=${outVidEnc}&t=${cacheBust}#t=0.5` : "";
        const kfSheetPath = sc.keyframe_sheet_path || "";
        const kfSheetEnc = kfSheetPath ? encodeURIComponent(kfSheetPath) : "";
        const kfSheetUrl = kfSheetEnc ? `/api/media?path=${kfSheetEnc}&t=${cacheBust}` : "";

        const stRef = sc.start_char_ref || {};
        const stImgPath = stRef.is_continuity_generated && !stRef.exists_on_disk
          ? (proj.base_char_2k?.path || "")
          : (stRef.path || proj.base_char_2k?.path || "");
        const stImgEnc = encodeURIComponent(stImgPath);
        const stImgUrl = `/api/media?path=${stImgEnc}`;
        const activePrompt = (genMode === "chained_i2v" || styleVal === "chained_i2v")
          ? (sc.prompt_chained_i2v || sc.prompt)
          : ((styleVal === "concise_flow") ? (sc.prompt_concise_flow || sc.prompt_timeline_pro || sc.prompt) : (sc.prompt_timeline_pro || sc.prompt));
        const transitions = sc.transitions || [];

        const bgImgPath = proj.char_sheet_2k?.path || "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/07_Nhan_Vat_Basic_Phong_Ngu_2K.png";
        const bgImgEnc = encodeURIComponent(bgImgPath);
        const bgImgUrl = `/api/media?path=${bgImgEnc}`;
        const bgImgFn = proj.char_sheet_2k?.filename || "07_Nhan_Vat_Basic_Phong_Ngu_2K.png";
        const ovImgPath = "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/01_Character_Sheet_4_Outfits_2K.png";
        const ovImgEnc = encodeURIComponent(ovImgPath);
        const overallSheetUrl = `/api/media?path=${ovImgEnc}`;

        // Nếu là Phân cảnh 2+ (scNum >= 2), ảnh mở đầu là Frame cuối của Phân cảnh 1 (`scene_s1_last_frame_2k.png`)!
        const prevLfObj = sc.prev_scene_last_frame_ref || {};
        const prevLfFn = prevLfObj.filename || `scene_s${scNum - 1}_last_frame_2k.png`;
        const prevLfPath = prevLfObj.path || `${proj.project_dir || ('flow_final_pipeline/fashion_motion_studio/projects/' + proj.project_id)}/assets_2k/${prevLfFn}`;
        const prevLfEnc = encodeURIComponent(prevLfPath);
        const prevLfUrl = `/api/media?path=${prevLfEnc}&t=${cacheBust}`;

        const clipVidDomId = `fClipRefVid_${sc.id || scIdx}`;
        const clipBtnDomId = `btnClipRefPlay_${sc.id || scIdx}`;
        const clipMuteDomId = `btnClipRefMute_${sc.id || scIdx}`;
        const outVidDomId = `fSceneOutVid_${sc.id || scIdx}`;
        const outBtnDomId = `btnSceneOutPlay_${sc.id || scIdx}`;
        const outMuteDomId = `btnSceneOutMute_${sc.id || scIdx}`;

        const openFrameChipHtml = scNum >= 2
          ? `<span onclick="openLightbox('${prevLfUrl}', 'Frame Cuối Cảnh ${scNum - 1} Nối Tiếp Sang Cảnh ${scNum}: ${prevLfFn}')" style="cursor:pointer; display:inline-flex; align-items:center; gap:4px; background:rgba(16,185,129,0.24); color:#34d399; border:1px solid rgba(16,185,129,0.65); padding:2px 7px; border-radius:5px; font-size:10px; font-weight:800;" title="Ảnh Frame cuối của Phân cảnh ${scNum - 1} dùng để mở đầu nối tiếp Phân cảnh ${scNum}">
               🎞️ Frame cuối Cảnh ${scNum - 1}: ${prevLfFn}
             </span>`
          : `<span onclick="openLightbox('${bgImgUrl}', '${bgImgFn}')" style="cursor:pointer; display:inline-flex; align-items:center; gap:4px; background:rgba(59,130,246,0.18); color:#93c5fd; border:1px solid rgba(59,130,246,0.45); padding:2px 7px; border-radius:5px; font-size:10px; font-weight:700;">
               🏠 Mở đầu: ${bgImgFn}
             </span>`;

        const ingredientsChipsHtml = genMode === "chained_i2v"
          ? `
            <div style="display:flex; gap:5px; align-items:center; flex-wrap:wrap; background:#050811; padding:6px 8px; border-radius:7px; border:1px solid rgba(16,185,129,0.4);">
              <span style="font-size:10px; font-weight:900; color:#34d399;">✨ 2 Ảnh Ref I2V + Timeline 0.1s Cảnh ${sc.scene_index} (Không dùng Video Ref):</span>
              ${openFrameChipHtml}
              <span onclick="openLightbox('${overallSheetUrl}', '01_Character_Sheet_4_Outfits_2K.png')" style="cursor:pointer; display:inline-flex; align-items:center; gap:4px; background:rgba(168,85,247,0.18); color:#e9d5ff; border:1px solid rgba(168,85,247,0.45); padding:2px 7px; border-radius:5px; font-size:10px; font-weight:700;">
                📋 01_Character_Sheet_4_Outfits_2K.png
              </span>
              ${transitions.map((tr, tIdx) => {
                const oUrl = `/api/media?path=${encodeURIComponent(tr.outfit?.path || '')}`;
                return `
                  <span onclick="openLightbox('${oUrl}', '${tr.outfit?.name || ''}')" style="cursor:pointer; display:inline-flex; align-items:center; gap:4px; background:rgba(245,158,11,0.18); color:#fde68a; border:1px solid rgba(245,158,11,0.45); padding:2px 7px; border-radius:5px; font-size:10px; font-weight:700;">
                    🎵 Beat @${Number(tr.timestamp_sec || 0).toFixed(2)}s: Look ${(scNum === 1 ? 0 : 2) + tIdx + 1} (${tr.outfit?.filename || ''})
                  </span>
                `;
              }).join("")}
            </div>
          `
          : `
            <div style="display:flex; gap:5px; align-items:center; flex-wrap:wrap; background:#050811; padding:6px 8px; border-radius:7px; border:1px solid rgba(255,255,255,0.1);">
              <span style="font-size:10px; font-weight:800; color:#94a3b8;">📎 5 Ảnh Ref + 1 Video Cảnh ${sc.scene_index}:</span>
              <span onclick="openLightbox('${stImgUrl}', '${stRef.filename || ''}')" style="cursor:pointer; display:inline-flex; align-items:center; gap:4px; background:rgba(236,72,153,0.18); color:#f9a8d4; border:1px solid rgba(236,72,153,0.45); padding:2px 7px; border-radius:5px; font-size:10px; font-weight:700;">
                👤 ${stRef.filename || '02_Character_Sheet_Basic_Poses_2K.png'}
              </span>
              <span onclick="openLightbox('${overallSheetUrl}', '01_Character_Sheet_4_Outfits_2K.png')" style="cursor:pointer; display:inline-flex; align-items:center; gap:4px; background:rgba(168,85,247,0.18); color:#e9d5ff; border:1px solid rgba(168,85,247,0.45); padding:2px 7px; border-radius:5px; font-size:10px; font-weight:700;">
                📋 01_Character_Sheet_4_Outfits_2K.png
              </span>
              ${openFrameChipHtml}
              ${transitions.slice(0, 2).map(tr => {
                const oUrl = `/api/media?path=${encodeURIComponent(tr.outfit?.path || '')}`;
                return `
                  <span onclick="openLightbox('${oUrl}', '${tr.outfit?.name || ''}')" style="cursor:pointer; display:inline-flex; align-items:center; gap:4px; background:rgba(245,158,11,0.18); color:#fde68a; border:1px solid rgba(245,158,11,0.45); padding:2px 7px; border-radius:5px; font-size:10px; font-weight:700;">
                    👗 @${tr.timestamp_colon}s: ${tr.outfit?.filename || ''}
                  </span>
                `;
              }).join("")}
              <span onclick="openVerticalVideoModal('${clipEnc}', '${bgImgEnc}', '${ovImgEnc}', 'Clip Tham Chiếu Cảnh ${sc.scene_index} (${sc.duration}s)', '', '')" style="cursor:pointer; display:inline-flex; align-items:center; gap:4px; background:rgba(6,182,212,0.18); color:#67e8f9; border:1px solid rgba(6,182,212,0.45); padding:2px 7px; border-radius:5px; font-size:10px; font-weight:700;" title="Bấm để mở xem phóng to Clip Tham Chiếu 9:16">
                🎞️ ${sc.ref_clip_filename} (${sc.duration}s)
              </span>
            </div>
          `;

        const transitionsEditorHtml = transitions.map((tr, trIdx) => `
          <div style="display:flex; align-items:center; gap:8px; background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3); padding:5px 8px; border-radius:6px; font-size:11px;">
            <span style="color:#fde68a; font-weight:800;">🎵 Đổi đồ #${trIdx + 1} tại giây:</span>
            <input id="inpCutTs_${sc.id}_${trIdx}" value="${tr.timestamp_colon}" style="width:64px; font-weight:800; color:#67e8f9; text-align:center; padding:2px 5px; font-size:11px;" />
            <span style="color:#e2e8f0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">➔ Mặc <b>${tr.outfit?.name || tr.outfit?.filename}</b></span>
          </div>
        `).join("");

        const stStr = String(sc.status || "");
        const isSceneFailed = stStr.startsWith("failed");
        const isSceneRetrying = stStr.startsWith("retrying");

        return `
          <div style="background:#080c16; border:1px solid ${isSceneFailed ? '#ef4444' : (isSceneRetrying ? '#f59e0b' : 'rgba(236,72,153,0.42)')}; border-radius:10px; padding:12px; display:flex; flex-direction:column; gap:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; border-bottom:1px solid var(--border); padding-bottom:7px;">
              <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                <span class="badge" style="background:linear-gradient(135deg,#ec4899,#6366f1); color:#fff; font-weight:900;">✂️ PHÂN CẢNH ${sc.scene_index} (${sc.start_sec}s – ${sc.end_sec}s)</span>
                <span class="badge" style="background:rgba(139,92,246,0.2); color:#c4b5fd; border:1px solid rgba(139,92,246,0.45);">🤖 ${sc.ai_model_used || 'AI Vision Analyzer'}</span>
                ${_getFashionSceneStatusBadgeHtml(sc, outVidUrl)}
              </div>
              <div style="display:flex; gap:5px; flex-wrap:wrap;">
                ${outVidEnc ? `
                  <button class="btn btn-xs btn-primary" onclick="openVerticalVideoModal('${outVidEnc}', '${bgImgEnc}', '${ovImgEnc}', 'Video Phân Cảnh ${sc.scene_index} (${sc.duration}s)', '', '')" title="Mở xem phóng to dọc 9:16 cho Video Phân Cảnh ${sc.scene_index}">
                    📱 Xem Cảnh ${sc.scene_index} (9:16)
                  </button>
                  <button class="btn btn-xs btn-outline" onclick="openFolderEncoded('${outVidEnc}')" title="Mở file Video Phân Cảnh ${sc.scene_index} trong Explorer">
                    📂 Mở File
                  </button>
                ` : ''}
                <button class="btn btn-xs btn-amber" onclick="runSingleFashionScene('${sc.id}')" title="Chạy lại / Retry ngay Phân Cảnh ${sc.scene_index}">
                  🔁 Retry Cảnh ${sc.scene_index}
                </button>
                <button class="btn btn-xs btn-success" onclick="runSingleFashionScene('${sc.id}')" title="Render Video AI Phân Cảnh ${sc.scene_index} trên Google Flow (Tác nhân · Omni 1.1 Flash · abra_edit)">
                  🎬 Render Cảnh ${sc.scene_index} (Flow)
                </button>
              </div>
            </div>

            ${sc.status_detail ? `
              <div style="background:${isSceneFailed ? 'rgba(239,68,68,0.14)' : (isSceneRetrying ? 'rgba(245,158,11,0.16)' : 'rgba(59,130,246,0.12)')}; border:1px solid ${isSceneFailed ? 'rgba(239,68,68,0.45)' : (isSceneRetrying ? 'rgba(245,158,11,0.5)' : 'rgba(59,130,246,0.35)')}; padding:5px 9px; border-radius:6px; font-size:11px; font-weight:700; color:${isSceneFailed ? '#fca5a5' : (isSceneRetrying ? '#fde68a' : '#93c5fd')};">
                ${sc.status_detail}
              </div>
            ` : ''}

            <!-- AI Phân Tích Chuyển Động Của Phân Cảnh -->
            ${sc.ai_motion_summary_vn ? `
              <div style="background:rgba(6,182,212,0.09); border-left:3px solid #06b6d4; padding:6px 10px; border-radius:5px; font-size:11px; color:#cbd5e1; line-height:1.45;">
                <b style="color:#67e8f9;">👁️ AI Phân Tích Chuyển Động Cảnh ${sc.scene_index}:</b> ${sc.ai_motion_summary_vn}
              </div>
            ` : ''}

            <div style="display:grid; grid-template-columns: 296px 1fr; gap:12px; align-items:start;">
              <!-- Cột Trái: 2 Video Song Song (Clip Gốc Đã Cắt vs Video Phân Cảnh Mới 2K) + Bộ Nút Đầy Đủ Dưới Mỗi Video -->
              <div style="display:flex; flex-direction:column; gap:6px;">
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px;">
                  <!-- Khung Clip Gốc -->
                  <div style="background:#04060c; border:1px solid rgba(6,182,212,0.45); border-radius:7px; padding:4px; display:flex; flex-direction:column; gap:4px;">
                    <div style="font-size:9px; font-weight:800; color:#67e8f9; text-align:center;">🎬 CLIP GỐC #${sc.scene_index} (${sc.duration}S)</div>
                    <div style="width:100%; aspect-ratio:9/16; background:#000; border-radius:5px; overflow:hidden; cursor:pointer; position:relative;"
                         onclick="toggleFashionInlineVideo('${clipVidDomId}', '${clipBtnDomId}')"
                         title="Bấm trực tiếp vào video để Phát / Dừng có tiếng">
                      <video id="${clipVidDomId}" class="fashion-clean-video" preload="metadata"
                             onloadedmetadata="if(this.currentTime===0){try{this.currentTime=0.5;}catch(e){}}"
                             onplay="const b=document.getElementById('${clipBtnDomId}'); if(b) b.innerHTML='⏸️ Dừng';"
                             onpause="const b=document.getElementById('${clipBtnDomId}'); if(b) b.innerHTML='▶️ Phát';"
                             style="width:100%; height:100%; object-fit:cover;" src="${clipUrl}"></video>
                    </div>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:3px;">
                      <button id="${clipBtnDomId}" class="btn btn-xs btn-success" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                              onclick="toggleFashionInlineVideo('${clipVidDomId}', '${clipBtnDomId}')">▶️ Phát</button>
                      <button id="${clipMuteDomId}" class="btn btn-xs btn-amber" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                              onclick="toggleFashionInlineMute('${clipVidDomId}', '${clipMuteDomId}')">🔊 Tiếng</button>
                      <button class="btn btn-xs btn-primary" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                              onclick="openVerticalVideoModal('${clipEnc}', '${bgImgEnc}', '${ovImgEnc}', 'Clip Tham Chiếu Cảnh ${sc.scene_index} (${sc.duration}s)', '', '')">📱 9:16</button>
                      <button class="btn btn-xs btn-outline" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                              onclick="openFolderEncoded('${clipEnc}')">📂 File</button>
                    </div>
                  </div>

                  <!-- Khung Video Phân Cảnh AI 2K -->
                  <div style="background:#04060c; border:1px solid rgba(16,185,129,0.55); border-radius:7px; padding:4px; display:flex; flex-direction:column; gap:4px;">
                    <div style="font-size:9px; font-weight:800; color:#34d399; text-align:center;">✨ VIDEO CẢNH #${sc.scene_index} (2K)</div>
                    <div style="width:100%; aspect-ratio:9/16; background:#000; border-radius:5px; overflow:hidden; display:flex; align-items:center; justify-content:center; cursor:pointer; position:relative;"
                         onclick="${outVidUrl ? `toggleFashionInlineVideo('${outVidDomId}', '${outBtnDomId}')` : `runSingleFashionScene('${sc.id}')`}"
                         title="${outVidUrl ? 'Bấm trực tiếp vào video để Phát / Dừng có tiếng' : 'Bấm để Render Video Phân Cảnh này'}">
                      ${outVidUrl
                        ? `<video id="${outVidDomId}" class="fashion-clean-video" preload="metadata"
                                  onloadedmetadata="if(this.currentTime===0){try{this.currentTime=0.5;}catch(e){}}"
                                  onplay="const b=document.getElementById('${outBtnDomId}'); if(b) b.innerHTML='⏸️ Dừng';"
                                  onpause="const b=document.getElementById('${outBtnDomId}'); if(b) b.innerHTML='▶️ Phát';"
                                  style="width:100%; height:100%; object-fit:cover;" src="${outVidUrl}"></video>`
                        : `<div style="font-size:10px; color:#94a3b8; text-align:center; padding:8px;">Bấm <b>🎬 Render Cảnh ${sc.scene_index}</b></div>`
                      }
                    </div>
                    ${outVidUrl ? `
                      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:3px;">
                        <button id="${outBtnDomId}" class="btn btn-xs btn-success" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                                onclick="toggleFashionInlineVideo('${outVidDomId}', '${outBtnDomId}')">▶️ Phát</button>
                        <button id="${outMuteDomId}" class="btn btn-xs btn-amber" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                                onclick="toggleFashionInlineMute('${outVidDomId}', '${outMuteDomId}')">🔊 Tiếng</button>
                        <button class="btn btn-xs btn-primary" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                                onclick="openVerticalVideoModal('${outVidEnc}', '${bgImgEnc}', '${ovImgEnc}', 'Video Phân Cảnh ${sc.scene_index} (${sc.duration}s)', '', '')">📱 9:16</button>
                        <button class="btn btn-xs btn-outline" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                                onclick="openFileEncoded('${outVidEnc}')">🖥️ Player</button>
                        <button class="btn btn-xs btn-outline" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                                onclick="openFolderEncoded('${outVidEnc}')">📂 File</button>
                        <button class="btn btn-xs btn-outline" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                                onclick="downloadFashionMedia('${outVidEnc}')">⬇️ Tải</button>
                      </div>
                    ` : `
                      <button class="btn btn-xs btn-success" style="width:100%; justify-content:center; font-size:9px; padding:4px;" onclick="runSingleFashionScene('${sc.id}')">
                        🎬 Render Cảnh ${sc.scene_index}
                      </button>
                    `}
                  </div>
                </div>
                ${kfSheetUrl ? `
                  <div onclick="openLightbox('${kfSheetUrl}', 'Bảng Keyframe 0.5s Phân Cảnh ${sc.scene_index} (${sc.start_sec}s - ${sc.end_sec}s)')"
                       style="cursor:pointer; background:#050811; border:1px solid rgba(245,158,11,0.4); border-radius:6px; padding:4px 8px; display:flex; align-items:center; justify-content:space-between; font-size:10px; color:#fde68a; font-weight:700;">
                    <span>🎞️ Xem Bảng Keyframe 0.5s (AI Vision)</span>
                    <span style="color:#93c5fd;">🔍 Phóng to</span>
                  </div>
                ` : ''}
              </div>

              <!-- Cột Phải: Ingredients + Mốc Giây Đổi Đồ Theo Beat + Timeline Prompt Có Chip Ảnh -->
              <div style="display:flex; flex-direction:column; gap:8px;">
                ${ingredientsChipsHtml}
                <div style="display:flex; flex-direction:column; gap:5px;">
                  ${transitionsEditorHtml}
                </div>
                <div style="background:#050811; border:1px solid rgba(59,130,246,0.4); border-radius:8px; padding:9px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px; flex-wrap:wrap; gap:6px;">
                    <span style="font-size:10.5px; font-weight:800; color:#93c5fd;">💬 PROMPT PHÂN CẢNH ${sc.scene_index} (GẮN CHIP ẢNH INLINE CHUẨN GOOGLE FLOW):</span>
                    <button class="btn btn-xs btn-primary" style="padding:2px 8px; font-size:10px;"
                            onclick="navigator.clipboard.writeText(STATE.fashionProject.scenes[${scIdx}].prompt); showFashionBanner('📋 Đã copy Prompt Phân Cảnh ${sc.scene_index}!');">
                      📋 Copy Prompt Cảnh ${sc.scene_index}
                    </button>
                  </div>
                  <div style="font-size:11px; color:#f1f5f9; line-height:1.5; background:#090e1a; padding:8px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.08); max-height:155px; overflow-y:auto;">
                    ${formatPromptWithInlineChipsHtml(activePrompt)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        `;
      }).join("");
    }

    function renderFashionFinalPostProdCard() {
      const box = document.getElementById("fashionFinalVideoPreviewBox");
      const topFinalsBar = document.getElementById("fashionCompletedFinalsTopBar");
      const proj = STATE.fashionProject;
      if (!box || !proj) return;
      const cacheBust = Date.now();
      const finalPath = proj.final_video_path || "";
      const finalEnc = encodeURIComponent(finalPath);
      const hasFinal = !!proj.final_video_ready && !!finalPath;
      const finalUrl = hasFinal ? `/api/media?path=${finalEnc}&t=${cacheBust}#t=0.5` : "";
      const scCount = (proj.scenes || []).length;
      const outCount = (proj.outfits || []).length;
      const totalDur = proj.reference_video?.duration || (scCount * 8);
      const curRefImgEnc = encodeURIComponent(proj.char_sheet_2k?.path || "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/07_Nhan_Vat_Basic_Phong_Ngu_2K.png");
      const curOvImgEnc = encodeURIComponent("ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/01_Character_Sheet_4_Outfits_2K.png");

      // Danh sách tất cả các Dự Án Thời Trang đã có Video Final để hiển thị Tổng Hợp ngay trên đầu Tab & Bước 4
      const allCompletedFinals = (STATE.fashionProjectsList || []).filter(p => !!p.final_video_ready && !!p.final_video_path);

      if (topFinalsBar) {
        if (allCompletedFinals.length > 0) {
          topFinalsBar.style.display = "block";
          topFinalsBar.innerHTML = `
            <div style="background:linear-gradient(135deg, rgba(6,38,31,0.94), rgba(11,18,34,0.97)); border:1.5px solid rgba(16,185,129,0.65); border-radius:10px; padding:10px 14px; box-shadow:0 8px 24px rgba(0,0,0,0.45);">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:9px;">
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                  <span class="badge" style="background:linear-gradient(135deg,#10b981,#06b6d4); color:#022c22; font-weight:900; font-size:11px; padding:3px 10px;">🏆 KHO VIDEO FINAL THỜI TRANG ĐÃ HOÀN TẤT (${allCompletedFinals.length} VIDEO • 1080P 60FPS)</span>
                  <span style="font-size:11.5px; color:#d1fae5; font-weight:700;">Bấm thẳng vào video hoặc nút <b>▶️ Phát Có Tiếng</b>, <b>📱 Phóng To 9:16</b>, <b>⬇️ Tải MP4</b> (Không bị che bởi menu 3 chấm)!</span>
                </div>
                <div style="display:flex; gap:6px; flex-wrap:wrap;">
                  <button class="btn btn-xs btn-primary" style="font-weight:800;" onclick="switchTab('dashboard', document.getElementById('navBtn-dashboard')); if(STATE.fashionProject?.project_id) loadProjectDetail(STATE.fashionProject.project_id, false);">📊 Xem Trong Tổng Hợp (Studio Dự Án)</button>
                  <button class="btn btn-xs btn-amber" style="font-weight:800;" onclick="switchTab('matrix', document.getElementById('navBtn-matrix'));">🌐 Mở Bảng Matrix Video Final</button>
                  <button class="btn btn-xs btn-success" style="font-weight:800;" onclick="openFolder('final_videos')">📂 Mở Folder final_videos</button>
                </div>
              </div>
              <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(410px, 1fr)); gap:12px;">
                ${allCompletedFinals.map((fp, fIdx) => {
                  const isCur = fp.project_id === proj.project_id;
                  const fEnc = encodeURIComponent(fp.final_video_path || '');
                  const fUrl = `/api/media?path=${fEnc}&t=${cacheBust}#t=0.5`;
                  const refImgEnc = encodeURIComponent(fp.char_sheet_2k?.path || "ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/07_Nhan_Vat_Basic_Phong_Ngu_2K.png");
                  const ovImgEnc = encodeURIComponent("ảnh mẫu thumbnail/Tron_Bo_7_Anh_2K/01_Character_Sheet_4_Outfits_2K.png");
                  const tplBadge = fp.source_template_code || "#004";
                  const vidDomId = `fTopFinalVid_${fIdx}`;
                  const playBtnId = `btnTopFinalPlay_${fIdx}`;
                  const muteBtnId = `btnTopFinalMute_${fIdx}`;
                  const safeTitle = (fp.title || fp.project_id).replace(/'/g, "");
                  const fnShort = fp.final_video_path.split(/[\\\\/]/).pop();
                  return `
                    <div style="background:#050914; border:1.5px solid ${isCur ? '#10b981' : 'rgba(255,255,255,0.16)'}; border-radius:10px; padding:9px; display:grid; grid-template-columns: 112px 1fr; gap:11px; align-items:start; box-shadow:${isCur ? '0 0 18px rgba(16,185,129,0.22)' : 'none'};">
                      <!-- Cột Trái: Khung Video Dọc 9:16 (Bấm trực tiếp để Phát/Dừng có tiếng, không hiện menu 3 chấm trắng) -->
                      <div style="display:flex; flex-direction:column; gap:4px;">
                        <div style="width:112px; aspect-ratio:9/16; background:#000; border-radius:7px; overflow:hidden; border:1.5px solid ${isCur ? '#10b981' : 'rgba(16,185,129,0.5)'}; cursor:pointer; position:relative;"
                             onclick="toggleFashionInlineVideo('${vidDomId}', '${playBtnId}')"
                             title="Bấm trực tiếp vào khung hình để Phát / Dừng video có tiếng">
                          <video id="${vidDomId}" class="fashion-clean-video" preload="metadata"
                                 onloadedmetadata="if(this.currentTime===0){try{this.currentTime=0.5;}catch(e){}}"
                                 onplay="const b=document.getElementById('${playBtnId}'); if(b) b.innerHTML='⏸️ Dừng'; const b2=document.getElementById('${playBtnId}_main'); if(b2) b2.innerHTML='⏸️ Dừng Video';"
                                 onpause="const b=document.getElementById('${playBtnId}'); if(b) b.innerHTML='▶️ Phát'; const b2=document.getElementById('${playBtnId}_main'); if(b2) b2.innerHTML='▶️ Phát Có Tiếng';"
                                 style="width:100%; height:100%; object-fit:cover;" src="${fUrl}"></video>
                          <span style="position:absolute; bottom:4px; left:4px; right:4px; background:rgba(4,9,20,0.82); color:#6ee7b7; font-size:8.5px; font-weight:800; text-align:center; padding:1.5px 4px; border-radius:4px; border:1px solid rgba(16,185,129,0.4);">
                            🔊 Bấm để phát
                          </span>
                        </div>
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:3px;">
                          <button id="${playBtnId}" class="btn btn-xs btn-success" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                                  onclick="toggleFashionInlineVideo('${vidDomId}', '${playBtnId}')">▶️ Phát</button>
                          <button id="${muteBtnId}" class="btn btn-xs btn-amber" style="padding:2px 3px; font-size:8.5px; font-weight:800; justify-content:center;"
                                  onclick="toggleFashionInlineMute('${vidDomId}', '${muteBtnId}')">🔊 Tiếng</button>
                        </div>
                      </div>

                      <!-- Cột Phải: Thông Tin Video Final + Đầy Đủ Các Nút Điều Khiển -->
                      <div style="display:flex; flex-direction:column; gap:5px; min-width:0;">
                        <div style="display:flex; align-items:center; justify-content:space-between; gap:5px; flex-wrap:wrap;">
                          <div style="display:flex; align-items:center; gap:5px; flex-wrap:wrap;">
                            <span class="badge" style="background:linear-gradient(135deg,#ec4899,#8b5cf6); color:#fff; font-weight:900; font-size:9.5px;">${tplBadge}</span>
                            <span class="badge badge-done" style="font-size:9.5px;">✅ 1080p • 24FPS</span>
                            ${isCur ? `<span class="badge" style="background:rgba(16,185,129,0.22); color:#34d399; border:1px solid #10b981; font-size:9px; font-weight:900;">● Đang mở</span>` : ''}
                          </div>
                          ${fp.final_rendered_at ? `<span style="font-size:9px; color:#94a3b8;">🕒 ${fp.final_rendered_at}</span>` : ''}
                        </div>

                        <div style="font-size:12px; font-weight:800; color:#f8fafc; line-height:1.3; overflow:hidden; text-overflow:ellipsis; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;" title="${(fp.title || fp.project_id).replace(/"/g, '&quot;')}">
                          ${fp.title || fp.project_id}
                        </div>
                        <div style="font-size:10px; color:#fde68a; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-family:Consolas,monospace;" title="${fp.final_video_path}">
                          📄 ${fnShort}
                        </div>

                        <!-- Hàng Nút 1: Phát Có Tiếng, Phóng To 9:16, Mở Player Máy, Mở File, Tải MP4, Copy Path -->
                        <div style="display:flex; gap:4px; flex-wrap:wrap; margin-top:2px;">
                          <button id="${playBtnId}_main" class="btn btn-xs btn-success" style="padding:4px 8px; font-size:10px; font-weight:900;"
                                  onclick="toggleFashionInlineVideo('${vidDomId}', '${playBtnId}')">
                            ▶️ Phát Có Tiếng
                          </button>
                          <button class="btn btn-xs btn-primary" style="padding:4px 8px; font-size:10px; font-weight:800;"
                                  onclick="openVerticalVideoModal('${fEnc}', '${refImgEnc}', '${ovImgEnc}', '${safeTitle} — VIDEO FINAL 16S', '${fp.project_id}', 'v1')">
                            📱 Phóng To 9:16
                          </button>
                          <button class="btn btn-xs btn-amber" style="padding:4px 7px; font-size:10px; font-weight:800;"
                                  onclick="openFileEncoded('${fEnc}')" title="Mở bằng trình phát video của Windows">
                            🖥️ Mở Player
                          </button>
                          <button class="btn btn-xs btn-outline" style="padding:4px 7px; font-size:10px; font-weight:800; color:#6ee7b7; border-color:rgba(16,185,129,0.5);"
                                  onclick="openFolderEncoded('${fEnc}')" title="Mở thư mục và chọn đúng file MP4 này">
                            📂 Mở File
                          </button>
                          <button class="btn btn-xs btn-outline" style="padding:4px 7px; font-size:10px; font-weight:800; color:#93c5fd; border-color:rgba(59,130,246,0.5);"
                                  onclick="downloadFashionMedia('${fEnc}')" title="Tải trực tiếp file MP4 về máy">
                            ⬇️ Tải MP4
                          </button>
                          <button class="btn btn-xs btn-outline" style="padding:4px 7px; font-size:10px; font-weight:800;"
                                  onclick="copyFashionPath('${fEnc}')" title="Copy đường dẫn file MP4 vào Clipboard">
                            📋 Copy Path
                          </button>
                        </div>

                        <!-- Hàng Nút 2: Xem Cảnh 1, Xem Cảnh 2, Nạp Kịch Bản, Ghép Lại Final, Render Lại AI -->
                        <div style="display:flex; gap:4px; flex-wrap:wrap; padding-top:4px; border-top:1px dashed rgba(255,255,255,0.1);">
                          <button class="btn btn-xs btn-outline" style="padding:3px 7px; font-size:9.5px; font-weight:800; color:#67e8f9; border-color:rgba(6,182,212,0.45);"
                                  onclick="openFashionSceneVideoModal('${fp.project_id}', 0)" title="Xem riêng Video Phân Cảnh 1 (0s-8s) ở chế độ dọc 9:16">
                            🎬 Xem Cảnh 1
                          </button>
                          <button class="btn btn-xs btn-outline" style="padding:3px 7px; font-size:9.5px; font-weight:800; color:#67e8f9; border-color:rgba(6,182,212,0.45);"
                                  onclick="openFashionSceneVideoModal('${fp.project_id}', 1)" title="Xem riêng Video Phân Cảnh 2 (8s-16s) ở chế độ dọc 9:16">
                            🎬 Xem Cảnh 2
                          </button>
                          <button class="btn btn-xs ${isCur ? 'btn-outline' : 'btn-amber'}" style="padding:3px 7px; font-size:9.5px; font-weight:800;"
                                  onclick="onSelectFashionProjectSlug('${fp.project_id}'); document.getElementById('fashionScenesTimelineContainer')?.scrollIntoView({behavior:'smooth'});"
                                  title="Nạp kịch bản dự án này xuống Bước 1–4 bên dưới để xem/chỉnh sửa">
                            👁️ Xem Kịch Bản Cảnh 1 & 2
                          </button>
                          <button class="btn btn-xs btn-outline" style="padding:3px 7px; font-size:9.5px; font-weight:800; color:#f9a8d4; border-color:rgba(236,72,153,0.45);"
                                  onclick="renderFashionFinalForProject('${fp.project_id}')" title="Chạy ghép hậu kỳ lại Video Final 24FPS cho dự án này">
                            🎞️ Ghép Lại
                          </button>
                          <button class="btn btn-xs btn-outline" style="padding:3px 7px; font-size:9.5px; font-weight:800; color:#fde68a; border-color:rgba(245,158,11,0.45);"
                                  onclick="runFashionFlowForProject('${fp.project_id}')" title="Chạy Render lại Video AI trên Google Flow cho dự án này">
                            🚀 Render Lại AI
                          </button>
                        </div>
                      </div>
                    </div>
                  `;
                }).join("")}
              </div>
            </div>
          `;
        } else {
          topFinalsBar.style.display = "none";
          topFinalsBar.innerHTML = "";
        }
      }

      box.innerHTML = `
        <div style="display:grid; grid-template-columns: 215px 1fr; gap:16px; align-items:center;">
          <!-- Cột Trái: Trình Phát Video Final 9:16 Hoàn Chỉnh (1080p 24FPS) + Đầy Đủ Nút Dưới Video -->
          <div style="background:#04070e; border:2px solid ${hasFinal ? '#10b981' : 'rgba(148,163,184,0.35)'}; border-radius:10px; padding:6px; display:flex; flex-direction:column; gap:5px; box-shadow:0 8px 24px rgba(0,0,0,0.5);">
            <div style="font-size:10px; font-weight:900; color:#34d399; text-align:center;">🏆 VIDEO FINAL HOÀN CHỈNH (1080P • 24FPS)</div>
            <div style="width:100%; aspect-ratio:9/16; background:#000; border-radius:7px; overflow:hidden; display:flex; align-items:center; justify-content:center; cursor:pointer;"
                 onclick="${hasFinal ? `toggleFashionInlineVideo('fBottomStep4FinalVid', 'btnBottomStep4Play')` : `renderFashionFinalPostProd()`}">
              ${hasFinal
                ? `<video id="fBottomStep4FinalVid" class="fashion-clean-video" controls controlslist="nodownload noplaybackrate" disablepictureinpicture preload="metadata"
                          onloadedmetadata="if(this.currentTime===0){try{this.currentTime=0.5;}catch(e){}}"
                          onplay="const b=document.getElementById('btnBottomStep4Play'); if(b) b.innerHTML='⏸️ Dừng';"
                          onpause="const b=document.getElementById('btnBottomStep4Play'); if(b) b.innerHTML='▶️ Phát';"
                          style="width:100%; height:100%; object-fit:cover;" src="${finalUrl}"></video>`
                : `<div style="font-size:11px; color:#94a3b8; text-align:center; padding:12px;">Chưa ghép hậu kỳ.<br/>Bấm nút <b>Render Hậu Kỳ Video Final</b> bên phải!</div>`
              }
            </div>
            ${hasFinal ? `
              <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:3px;">
                <button id="btnBottomStep4Play" class="btn btn-xs btn-success" style="padding:3px 2px; font-size:9px; font-weight:800; justify-content:center;"
                        onclick="toggleFashionInlineVideo('fBottomStep4FinalVid', 'btnBottomStep4Play')">▶️ Phát</button>
                <button id="btnBottomStep4Mute" class="btn btn-xs btn-amber" style="padding:3px 2px; font-size:9px; font-weight:800; justify-content:center;"
                        onclick="toggleFashionInlineMute('fBottomStep4FinalVid', 'btnBottomStep4Mute')">🔊 Tiếng</button>
                <button class="btn btn-xs btn-primary" style="padding:3px 2px; font-size:9px; font-weight:800; justify-content:center;"
                        onclick="openVerticalVideoModal('${finalEnc}', '${curRefImgEnc}', '${curOvImgEnc}', '${(proj.title || proj.project_id).replace(/'/g, '')} — VIDEO FINAL 16S', '${proj.project_id}', 'v1')">📱 9:16</button>
              </div>
            ` : ''}
          </div>

          <!-- Cột Phải: Thông Tin Hậu Kỳ Ghép Phân Cảnh + Nhạc Gốc & Các Nút Xuất Bản -->
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                <span class="badge" style="background:linear-gradient(135deg,#10b981,#059669); color:#022c22; font-weight:900; font-size:11px; padding:3px 10px;">🎬 BƯỚC 4: RENDER HẬU KỲ VIDEO FINAL</span>
                <span style="font-size:15px; font-weight:900; color:#ecfdf5;">${proj.title || proj.project_id}</span>
                ${hasFinal ? `<span class="badge badge-done">✅ Sẵn sàng Upload TikTok / Reels / Shorts</span>` : `<span class="badge badge-wait">⏳ Chờ Render Hậu Kỳ</span>`}
              </div>
              <div style="font-size:11.5px; color:#cbd5e1; margin-top:6px; line-height:1.5;">
                • <b>Ghép nối mượt mà:</b> Tự động nối <b>${scCount} Video Phân Cảnh</b> + đồng bộ <b>Nhạc Gốc AAC 192kbps</b> của Video Tham Chiếu (<code>${proj.reference_video?.filename || ''}</code> — ${totalDur}s) ở chuẩn khung hình gốc <b>1080×1920 • 24 FPS</b> mượt mà.<br/>
                • <b>Số lượng trang phục đã phối:</b> <b>${outCount} Bộ Đồ 2K</b> biến hình khớp chính xác từng điểm cắt hình ảnh & nhịp bass nhạc nền.<br/>
                • <b>Đường dẫn xuất file Final:</b> <code style="color:#fde68a;">${finalPath || 'final_videos/' + proj.project_id + '_final.mp4'}</code>
              </div>
            </div>

            <div style="display:flex; gap:7px; flex-wrap:wrap;">
              <button class="btn btn-success" style="padding:8px 15px; font-weight:900; font-size:12px;" onclick="renderFashionFinalPostProd()">
                🎞️ Render Hậu Kỳ Ghép ${scCount} Phân Cảnh + Nhạc Gốc Thành Video Final (1080p 24FPS)
              </button>
              <button class="btn btn-primary" style="padding:8px 14px; font-weight:800;" onclick="runFashionProjectOnFlow()">
                🚀 Chạy Tạo Video Phân Cảnh Qua Google Flow (Omni Flash)
              </button>
              ${hasFinal ? `
                <button class="btn btn-primary" style="padding:8px 12px; font-weight:800; background:#2563eb;" onclick="openVerticalVideoModal('${finalEnc}', '${curRefImgEnc}', '${curOvImgEnc}', '${(proj.title || proj.project_id).replace(/'/g, '')} — VIDEO FINAL 16S', '${proj.project_id}', 'v1')">
                  📱 Xem Phóng To Dọc 9:16
                </button>
                <button class="btn btn-amber" style="padding:8px 12px; font-weight:800;" onclick="openFileEncoded('${finalEnc}')">
                  🖥️ Mở Xem Bằng Trình Phát Máy Tính
                </button>
                <button class="btn btn-outline" style="padding:8px 12px; font-weight:800; color:#6ee7b7; border-color:rgba(16,185,129,0.5);" onclick="openFolderEncoded('${finalEnc}')">
                  📂 Chọn File Trong Explorer
                </button>
                <button class="btn btn-outline" style="padding:8px 12px; font-weight:800; color:#93c5fd; border-color:rgba(59,130,246,0.5);" onclick="downloadFashionMedia('${finalEnc}')">
                  ⬇️ Tải Video MP4
                </button>
                <button class="btn btn-outline" style="padding:8px 12px; font-weight:800;" onclick="copyFashionPath('${finalEnc}')">
                  📋 Copy Đường Dẫn File
                </button>
              ` : ''}
              <button class="btn btn-outline" style="padding:8px 12px;" onclick="openFolder('final_videos')">
                📂 Mở Thư Mục Video Final
              </button>
              <button class="btn btn-primary" style="padding:8px 12px; background:#6366f1; border-color:#818cf8;" onclick="switchTab('dashboard', document.getElementById('navBtn-dashboard')); if(STATE.fashionProject?.project_id) loadProjectDetail(STATE.fashionProject.project_id, false);">
                📊 Xem Trong Tab Studio Dự Án (Tổng Hợp)
              </button>
            </div>
          </div>
        </div>
      `;
    }

    function startFashionLiveStatusMonitor(targetSlug = "") {
      const slug = targetSlug || STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19";
      if (STATE._fashionFlowPollTimer) {
        clearInterval(STATE._fashionFlowPollTimer);
        STATE._fashionFlowPollTimer = null;
      }
      if (STATE._fashionElapsedTicker) {
        clearInterval(STATE._fashionElapsedTicker);
        STATE._fashionElapsedTicker = null;
      }
      if (!STATE._fashionWatchdogRetries) STATE._fashionWatchdogRetries = {};
      if (!STATE._fashionRunStartTs) STATE._fashionRunStartTs = Date.now();

      renderFashionLiveMonitorBar();
      STATE._fashionElapsedTicker = setInterval(() => {
        if (STATE.fashionProject && STATE.fashionProject.status === "running_flow") {
          renderFashionLiveMonitorBar();
        }
      }, 1000);

      let ticks = 0;
      STATE._fashionFlowPollTimer = setInterval(async () => {
        ticks++;
        const r = await apiGet(`/api/fashion_motion/projects?project_id=${encodeURIComponent(slug)}`);
        const nextProj = r && (r.active_project || r.current_project);
        if (!r || !r.ok || !nextProj) return;

        if (Array.isArray(r.projects)) STATE.fashionProjectsList = r.projects;
        STATE.fashionProject = nextProj;
        populateFashionProjectDropdown();
        renderFashionCompletedVideosShelf();
        renderFashionLiveMonitorBar();
        renderFashionScenesTimeline();
        renderFashionFinalPostProdCard();

        if (nextProj.status_message) {
          const isErr = String(nextProj.status || "").startsWith("failed");
          showFashionBanner(nextProj.status_message, isErr);
        }

        const isStillRunning = nextProj.status === "running_flow" || (nextProj.scenes || []).some(s => {
          const st = String(s.status || "");
          return st === "preparing" || st === "uploading_video" || st === "submitting" || st === "submitted_720p" || st === "upsampling_1080p" || st.startsWith("rendering") || st.startsWith("retrying");
        });

        if (!isStillRunning) {
          const failedList = (nextProj.scenes || []).filter(s => String(s.status || "").startsWith("failed"));
          const autoWatchdogOn = document.getElementById("chkFashionAutoRetryWatchdog")?.checked !== false;
          const wdCount = STATE._fashionWatchdogRetries[slug] || 0;

          if (failedList.length > 0 && autoWatchdogOn && wdCount < 2) {
            STATE._fashionWatchdogRetries[slug] = wdCount + 1;
            showFashionBanner(`🔁 [Watchdog Tự Động Retry Lần ${wdCount + 1}/2] Phát hiện ${failedList.length} phân cảnh lỗi (${failedList.map(x => x.id.toUpperCase()).join(", ")}) -> Đang tự động kích hoạt Retry ngay lập tức!`);
            await retryAllFailedFashionScenes(true);
            return;
          }

          clearInterval(STATE._fashionFlowPollTimer);
          STATE._fashionFlowPollTimer = null;
          if (STATE._fashionElapsedTicker) {
            clearInterval(STATE._fashionElapsedTicker);
            STATE._fashionElapsedTicker = null;
          }
          STATE._fashionRunStartTs = 0;
          if (nextProj.final_video_ready) {
            showFashionBanner(`🎉 Đã tạo xong toàn bộ phân cảnh và Render Hậu Kỳ hoàn tất Video Final 1080p 24FPS!`);
            if (typeof refreshAll === "function") refreshAll(true);
          }
        } else if (ticks > 360) {
          clearInterval(STATE._fashionFlowPollTimer);
          STATE._fashionFlowPollTimer = null;
          if (STATE._fashionElapsedTicker) {
            clearInterval(STATE._fashionElapsedTicker);
            STATE._fashionElapsedTicker = null;
          }
        }
      }, 2000);
    }

    async function retryAllFailedFashionScenes(isAutoWatchdog = false) {
      const slug = STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19";
      if (!isAutoWatchdog) {
        STATE._fashionWatchdogRetries = STATE._fashionWatchdogRetries || {};
        STATE._fashionWatchdogRetries[slug] = 0;
      }
      STATE._fashionRunStartTs = Date.now();
      showFashionBanner(`🔁 Đang kích hoạt Retry ngay lập tức cho các phân cảnh lỗi của dự án <b>${slug}</b> trên Google Flow...`);
      const res = await apiPost("/api/fashion_motion/retry_failed", {
        project_id: slug,
      });
      if (res && res.ok) {
        showFashionBanner(`🚀 ${res.message || 'Đang chạy Retry tự động trên Google Flow...'}`);
        startFashionLiveStatusMonitor(slug);
      } else {
        showFashionBanner(`❌ Lỗi kích hoạt Retry: ${(res && res.error) || 'Không xác định'}`, true);
      }
    }

    async function runSingleFashionScene(sceneId) {
      const slug = STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19";
      const generation_mode = document.getElementById("selFashionGenerationMode")?.value || STATE.fashionProject?.generation_mode || "chained_i2v";
      STATE._fashionRunStartTs = Date.now();
      if (STATE.fashionProject) {
        STATE.fashionProject.generation_mode = generation_mode;
        STATE.fashionProject.status = "running_flow";
        STATE.fashionProject.status_message = `🚀 Đang gửi Phân Cảnh ${sceneId.toUpperCase()} lên Google Flow (${generation_mode === 'chained_i2v' ? 'Chained I2V 0.1s' : 'Motion Control Video Ref'})...`;
        (STATE.fashionProject.scenes || []).forEach(s => {
          if (s.id === sceneId) {
            s.status = "preparing";
            s.attempt = 1;
            s.max_attempts = 4;
            s.status_detail = "🚀 Đang kết nối Google Flow & tải ảnh tham chiếu 2K...";
          }
        });
        renderFashionLiveMonitorBar();
        renderFashionScenesTimeline();
      }
      showFashionBanner(`⏳ Đang gửi Phân Cảnh <b>${sceneId.toUpperCase()}</b> lên Google Flow (${generation_mode === 'chained_i2v' ? 'Chained Img2Video 0.1s' : 'Motion Control Video Ref'})...`);
      const res = await apiPost("/api/fashion_motion/run_scene", {
        project_id: slug,
        scene_id: sceneId,
        generation_mode,
        async: true,
      });
      if (res && res.ok) {
        if (res.project) STATE.fashionProject = res.project;
        showFashionBanner(res.message || `🚀 Đang tạo Video Phân Cảnh ${sceneId.toUpperCase()} trên Google Flow!`);
        startFashionLiveStatusMonitor(slug);
      } else {
        showFashionBanner(`❌ Lỗi tạo phân cảnh ${sceneId}: ${(res && res.error) || 'Không xác định'}`, true);
      }
    }

    async function renderFashionFinalPostProd() {
      const slug = STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19";
      showFashionBanner(`⏳ Đang Render Hậu Kỳ ghép các Video Phân Cảnh + Nhạc Gốc thành Video Final 1080×1920 mượt mà cho dự án <b>${slug}</b>...`);
      const res = await apiPost("/api/fashion_motion/render_final", {
        project_id: slug,
      });
      if (res && res.ok && res.project) {
        STATE.fashionProject = res.project;
        renderFashionMotionStudio();
        showFashionBanner(`🎉 ${res.message || 'Đã Render Hậu Kỳ xong Video Final 1080p mượt mà!'}`);
        document.getElementById("cardFashionPostProdFinal")?.scrollIntoView({ behavior: "smooth" });
      } else {
        showFashionBanner(`❌ Lỗi Render Hậu Kỳ: ${(res && res.error) || 'Không xác định'}`, true);
      }
    }

    async function analyzeAndBuildFashionProject(overrideSlug = "", overrideTitle = "") {
      const base_char_path = document.getElementById("inpFashionBaseChar")?.value || "";
      const char_sheet_path = document.getElementById("inpFashionCharSheet")?.value || "";
      const ref_video_path = document.getElementById("inpFashionRefVideo")?.value || "";
      const preferred_chunk_sec = document.getElementById("selFashionChunkSec")?.value || "auto";
      const generation_mode = document.getElementById("selFashionGenerationMode")?.value || STATE.fashionProject?.generation_mode || "chained_i2v";
      const prompt_style = document.getElementById("selFashionPromptStyle")?.value || (generation_mode === "chained_i2v" ? "chained_i2v" : "timeline_pro");
      const ai_provider = document.getElementById("selFashionAiProvider")?.value || "auto";
      const ai_model = document.getElementById("selFashionAiModel")?.value || "gemini-2.5-flash";

      const enabledOutfits = (STATE.fashionOutfits || []).filter(o => o.enabled !== false);
      const custom_scene_cuts = {};
      if (!overrideSlug && STATE.fashionProject && Array.isArray(STATE.fashionProject.scenes)) {
        const prevRef = STATE.fashionProject.reference_video?.path || "";
        if (prevRef && ref_video_path && prevRef === ref_video_path && enabledOutfits.length === (STATE.fashionProject.outfits || []).length) {
          STATE.fashionProject.scenes.forEach(sc => {
            const cuts = [];
            (sc.transitions || []).forEach((tr, trIdx) => {
              const inp = document.getElementById(`inpCutTs_${sc.id}_${trIdx}`);
              if (inp && inp.value.trim()) cuts.push(inp.value.trim());
            });
            if (cuts.length) custom_scene_cuts[sc.id] = cuts;
          });
        }
      }

      const targetSlug = overrideSlug || STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19";
      const targetTitle = overrideTitle || STATE.fashionProject?.title || `Lookbook Thời Trang AI 2K (${enabledOutfits.length} Bộ Đồ)`;

      showFashionBanner(`⏳ Đang phân tích Video Tham Chiếu chuẩn từng 0.1s theo nhạc (Chế độ: <b>${generation_mode === 'chained_i2v' ? 'Chained Img2Video 0.1s' : 'Motion Control Video Ref'}</b>) và gán ${enabledOutfits.length} Bộ Đồ 2K...`);
      const res = await apiPost("/api/fashion_motion/analyze_and_create", {
        project_id: targetSlug,
        title: targetTitle,
        base_char_path,
        char_sheet_path,
        ref_video_path,
        outfit_items: enabledOutfits,
        preferred_chunk_sec,
        generation_mode,
        prompt_style,
        custom_scene_cuts,
        ai_provider,
        ai_model,
        auto_render_preview_final: false,
      });
      if (res && res.ok) {
        STATE.fashionProject = res;
        if (Array.isArray(res.projects)) {
          STATE.fashionProjectsList = res.projects;
        }
        STATE.fashionOutfits = syncFashionOutfitsWithDefaults(res.outfits || [], STATE.fashionDefaultOutfits);
        populateFashionProjectDropdown();
        renderFashionMotionStudio();
        showFashionBanner(`✅ Đã phân tích Video Gốc (${res.reference_video?.duration}s), căn nhịp 0.1s theo nhạc cho <b>${(res.scenes || []).length} Phân Cảnh × ${res.split_plan?.scene_duration}s</b> (Cảnh 2 tự động nối tiếp Frame cuối Cảnh 1)!`);
      } else {
        showFashionBanner(`❌ Lỗi phân tích: ${(res && res.error) || 'Không xác định'}`, true);
      }
    }

    async function runFashionProjectOnFlow() {
      const clickedTpl = STATE.lastUserClickedTemplateCode || "";
      const curProjTpl = STATE.fashionProject?.source_template_code || "";
      if (clickedTpl && curProjTpl !== clickedTpl && STATE.fashionProject?.project_id !== `fashion_tpl_${clickedTpl.toLowerCase()}`) {
        return await applySelectedFashionTemplate(true);
      }

      const slug = STATE.fashionProject?.project_id || "fashion_lookbook_chan_vay_6e19";
      const generation_mode = document.getElementById("selFashionGenerationMode")?.value || STATE.fashionProject?.generation_mode || "chained_i2v";
      STATE._fashionWatchdogRetries = STATE._fashionWatchdogRetries || {};
      STATE._fashionWatchdogRetries[slug] = 0;
      STATE._fashionRunStartTs = Date.now();

      if (STATE.fashionProject) {
        STATE.fashionProject.generation_mode = generation_mode;
        STATE.fashionProject.status = "running_flow";
        STATE.fashionProject.status_message = `🚀 Đang khởi động trình duyệt Google Flow (${generation_mode === 'chained_i2v' ? 'Chained Img2Video 0.1s Chuẩn Nhạc' : 'Motion Control Video Ref'}) cho dự án ${slug}...`;
        (STATE.fashionProject.scenes || []).forEach(s => {
          s.status = "preparing";
          s.attempt = 1;
          s.max_attempts = 4;
          s.status_detail = "🚀 Đang kết nối Google Flow & tải nguyên liệu 2K...";
        });
        renderFashionLiveMonitorBar();
        renderFashionScenesTimeline();
        document.getElementById("fashionLiveMonitorBarTop")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }

      showFashionBanner(`🚀 Đang gửi dự án <b>${slug}</b> (Chế độ: <b>${generation_mode === 'chained_i2v' ? 'Chained Img2Video + Timeline 0.1s Chuẩn Nhạc' : 'Motion Control Video Ref'}</b> • Cảnh 2 nối tiếp Frame cuối Cảnh 1) lên Google Flow...`);
      const res = await apiPost("/api/fashion_motion/run_flow", {
        project_id: slug,
        generation_mode,
      });
      if (res && res.ok) {
        if (res.project) STATE.fashionProject = res.project;
        showFashionBanner(`✅ ${res.message}`);
        startFashionLiveStatusMonitor(slug);
      } else {
        showFashionBanner(`❌ Lỗi: ${(res && res.error) || 'Không thể khởi chạy'}`, true);
      }
    }

    // =========================================================================================
    // NÚT NỔI LIÊN HỆ & TRỢ LÝ 24/7 (KÉO THẢ DI CHUYỂN TỰ DO + BẤM MỞ MENU ZALO / FACEBOOK)
    // =========================================================================================
    const FAB_STORAGE_KEY = "skillautoveo_fab_pos_v1";

    function adjustFabPopoverDirection() {
      const widget = document.getElementById("floatingAssistantWidget");
      const pop = document.getElementById("fabPopoverPanel");
      if (!widget || !pop) return;
      const rect = widget.getBoundingClientRect();
      if (rect.top < 360) {
        pop.classList.add("open-down");
      } else {
        pop.classList.remove("open-down");
      }
      if (rect.left < 340) {
        pop.classList.add("open-right");
      } else {
        pop.classList.remove("open-right");
      }
    }

    function toggleFloatingAssistant(ev) {
      if (ev) ev.stopPropagation();
      const pop = document.getElementById("fabPopoverPanel");
      if (!pop) return;
      const isOpen = pop.classList.contains("open");
      if (isOpen) {
        pop.classList.remove("open");
      } else {
        adjustFabPopoverDirection();
        pop.classList.add("open");
      }
    }

    function closeFloatingAssistant() {
      const pop = document.getElementById("fabPopoverPanel");
      if (pop) pop.classList.remove("open");
    }

    function resetFloatingAssistantPos() {
      const widget = document.getElementById("floatingAssistantWidget");
      if (!widget) return;
      localStorage.removeItem(FAB_STORAGE_KEY);
      widget.style.left = "auto";
      widget.style.top = "auto";
      widget.style.right = "20px";
      widget.style.bottom = "44px";
      adjustFabPopoverDirection();
    }

    function initFloatingAssistantDrag() {
      const widget = document.getElementById("floatingAssistantWidget");
      const trigger = document.getElementById("fabTriggerBtn");
      if (!widget || !trigger || trigger.dataset.fabBound === "1") return;
      trigger.dataset.fabBound = "1";
      widget.style.zIndex = "10500";

      try {
        const saved = JSON.parse(localStorage.getItem(FAB_STORAGE_KEY) || "null");
        if (saved && typeof saved.left === "number" && typeof saved.top === "number") {
          const maxL = Math.max(10, window.innerWidth - 190);
          const maxT = Math.max(10, window.innerHeight - 60);
          widget.style.right = "auto";
          widget.style.bottom = "auto";
          widget.style.left = `${Math.min(Math.max(8, saved.left), maxL)}px`;
          widget.style.top = `${Math.min(Math.max(8, saved.top), maxT)}px`;
        }
      } catch (e) {}

      let isDragging = false;
      let hasMoved = false;
      let startX = 0;
      let startY = 0;
      let origLeft = 0;
      let origTop = 0;

      const onStart = (clientX, clientY) => {
        const rect = widget.getBoundingClientRect();
        isDragging = true;
        hasMoved = false;
        startX = clientX;
        startY = clientY;
        origLeft = rect.left;
        origTop = rect.top;
      };

      const onMove = (clientX, clientY) => {
        if (!isDragging) return;
        const dx = clientX - startX;
        const dy = clientY - startY;
        if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
          hasMoved = true;
        }
        if (!hasMoved) return;

        const w = widget.offsetWidth || 175;
        const h = widget.offsetHeight || 46;
        const newLeft = Math.min(Math.max(6, origLeft + dx), window.innerWidth - w - 6);
        const newTop = Math.min(Math.max(6, origTop + dy), window.innerHeight - h - 6);

        widget.style.right = "auto";
        widget.style.bottom = "auto";
        widget.style.left = `${newLeft}px`;
        widget.style.top = `${newTop}px`;
        adjustFabPopoverDirection();
      };

      const onEnd = () => {
        if (!isDragging) return;
        isDragging = false;
        if (hasMoved) {
          const rect = widget.getBoundingClientRect();
          try {
            localStorage.setItem(FAB_STORAGE_KEY, JSON.stringify({ left: Math.round(rect.left), top: Math.round(rect.top) }));
          } catch (e) {}
        } else {
          toggleFloatingAssistant();
        }
      };

      trigger.addEventListener("mousedown", (e) => {
        if (e.button !== 0) return;
        e.preventDefault();
        e.stopPropagation();
        onStart(e.clientX, e.clientY);
      });
      window.addEventListener("mousemove", (e) => onMove(e.clientX, e.clientY));
      window.addEventListener("mouseup", () => onEnd());

      trigger.addEventListener("touchstart", (e) => {
        if (!e.touches || !e.touches[0]) return;
        onStart(e.touches[0].clientX, e.touches[0].clientY);
      }, { passive: true });
      window.addEventListener("touchmove", (e) => {
        if (!isDragging || !e.touches || !e.touches[0]) return;
        onMove(e.touches[0].clientX, e.touches[0].clientY);
      }, { passive: true });
      window.addEventListener("touchend", () => onEnd());

      document.addEventListener("click", (e) => {
        if (!widget.contains(e.target)) {
          closeFloatingAssistant();
        }
      });

      window.addEventListener("resize", () => {
        if (widget.style.left && widget.style.left !== "auto") {
          const rect = widget.getBoundingClientRect();
          const w = widget.offsetWidth || 175;
          const h = widget.offsetHeight || 46;
          widget.style.left = `${Math.min(Math.max(6, rect.left), window.innerWidth - w - 6)}px`;
          widget.style.top = `${Math.min(Math.max(6, rect.top), window.innerHeight - h - 6)}px`;
        }
      });
    }

    function openBulkImportModal() {
      if (typeof openModal === "function") openModal("modalBulkImport");
    }

    function openLightbox(srcOrUrl, title = "") {
      if (typeof openImageLightbox === "function") {
        openImageLightbox(srcOrUrl, title);
      }
    }

    function toast(msg, kind = "info") {
      if (typeof showWfToast === "function" && document.getElementById("tab-workflow")?.classList.contains("active")) {
        showWfToast(msg, kind === "err" ? "error" : (kind === "ok" ? "success" : "info"));
        return;
      }
      let box = document.getElementById("globalToastBox");
      if (!box) {
        box = document.createElement("div");
        box.id = "globalToastBox";
        box.style.cssText = "position:fixed;bottom:22px;left:50%;transform:translateX(-50%);z-index:11000;background:#111827;color:#f8fafc;border:1px solid rgba(59,130,246,0.5);padding:8px 16px;border-radius:99px;font-size:12px;font-weight:700;box-shadow:0 10px 28px rgba(0,0,0,0.75);pointer-events:none;transition:opacity 0.2s;";
        document.body.appendChild(box);
      }
      box.textContent = msg;
      box.style.opacity = "1";
      clearTimeout(box._timer);
      box._timer = setTimeout(() => { box.style.opacity = "0"; }, 3200);
    }

    // =========================================================================================
    // KHỞI ĐỘNG TỰ ĐỘNG KHI MỞ GIAO DIỆN WEB (NẠP NGAY 179 DỰ ÁN TRONG STUDIO, KHO SP & NHÂN VẬT)

    // =========================================================================================
    // CHROME CDP — KẾT NỐI CHROME ĐỂ SUBMIT GOOGLE FLOW JOB
    // =========================================================================================
    async function checkChromeCdpStatus() {
      const dot = document.getElementById("cdpStatusDot");
      const msg = document.getElementById("cdpStatusMsg");
      const banner = document.getElementById("chromeCdpBanner");
      if (dot) dot.style.background = "#fbbf24";
      if (msg) msg.textContent = "Đang kiểm tra kết nối Chrome...";
      try {
        const res = await apiPost("/api/flow/cdp_status", {});
        if (res && res.ok) {
          if (dot) dot.style.background = "#22c55e";
          if (msg) msg.innerHTML = `<b style="color:#22c55e">✅ Chrome đã kết nối!</b> ${res.browser || ""} — ${res.flow_tabs || 0} tab Google Flow. Session: <b style="color:#a5f3fc">${res.account || "đang kiểm tra..."}</b>`;
          if (banner) banner.style.borderColor = "rgba(34,197,94,0.6)";
        } else {
          if (dot) dot.style.background = "#ef4444";
          if (msg) msg.innerHTML = `<b style="color:#ef4444">❌ Chưa kết nối Chrome</b>: ${res && res.error || "CDP port 9222 chưa mở"}. Nhấn <b>⚡ Bật Chrome Debug Port</b> để bật.`;
          if (banner) banner.style.borderColor = "rgba(239,68,68,0.6)";
        }
      } catch (e) {
        if (dot) dot.style.background = "#ef4444";
        if (msg) msg.textContent = "Lỗi kiểm tra: " + e.message;
      }
    }

    async function launchChromeWithCdp() {
      const btn = document.getElementById("btnLaunchCdp");
      if (btn) { btn.disabled = true; btn.textContent = "⏳ Đang xử lý..."; }
      try {
        const res = await apiPost("/api/flow/launch_chrome_cdp", {});
        if (res && res.ok) {
          toast("✅ " + (res.message || "Chrome đang khởi động lại với debug port..."), "ok");
          setTimeout(checkChromeCdpStatus, 6000);
        } else {
          toast("❌ " + ((res && res.error) || "Không thể bật Chrome Debug Port"), "err");
          showCdpHelp();
        }
      } catch(e) {
        toast("❌ Lỗi: " + e.message, "err");
        showCdpHelp();
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = "⚡ Bật Chrome Debug Port"; }
      }
    }

    function showCdpHelp() {
      const CMD = 'taskkill /f /im chrome.exe & timeout 2 & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --restore-last-session';
      const helpHtml = `<div id="cdpHelpOverlay" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.82);z-index:9999;display:flex;align-items:center;justify-content:center;" onclick="document.getElementById('cdpHelpOverlay')?.remove()">
        <div style="background:#0f172a;border:1.5px solid rgba(99,102,241,0.6);border-radius:12px;padding:24px;max-width:600px;width:92%;color:#e2e8f0;" onclick="event.stopPropagation()">
          <div style="font-size:15px;font-weight:900;color:#a5b4fc;margin-bottom:12px;">&#128279; Cách kết nối Chrome với Tool (một lần duy nhất)</div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">Chạy lệnh sau trong <b>cmd.exe</b> (không phải PowerShell):</div>
          <div style="background:#0d1322;border:1px solid rgba(99,102,241,0.3);border-radius:7px;padding:12px;font-size:11px;color:#fde68a;font-family:monospace;margin-bottom:12px;word-break:break-all;user-select:all;">
            taskkill /f /im chrome.exe &amp; timeout 2 &amp; "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --restore-last-session
          </div>
          <div style="font-size:11.5px;color:#94a3b8;margin-bottom:16px;line-height:1.6;">
            ✅ Chrome sẽ tự restore lại tất cả tabs (kể cả tab Google Flow đang mở)<br/>
            ✅ Sau đó nhấn <b>&#128269; Kiểm Tra</b> để xác nhận kết nối<br/>
            ✅ Tool sẽ tự lấy session và submit video AI lên Google Flow
          </div>
          <div style="display:flex;gap:8px;justify-content:flex-end;">
            <button class="btn btn-xs btn-outline" onclick="document.getElementById('cdpHelpOverlay')?.remove()">Đóng</button>
            <button class="btn btn-xs" style="background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#fff;border:none;font-weight:800;" onclick="navigator.clipboard.writeText('taskkill /f /im chrome.exe & timeout 2 & \"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\" --remote-debugging-port=9222 --restore-last-session').then(()=>toast('✅ Đã copy!','ok'));this.textContent='✅ Copied!'">&#128203; Copy Lệnh</button>
          </div>
        </div>
      </div>`;
      document.getElementById('cdpHelpOverlay')?.remove();
      document.body.insertAdjacentHTML('beforeend', helpHtml);
    }


    // =========================================================================================
    // PROFILE SESSION MANAGER — Lấy cookies + WIZ tokens từ Chrome profiles
    // =========================================================================================
    let _cdpProfileList = [];

    async function loadCdpProfileList() {
      try {
        const res = await apiPost("/api/flow/list_profiles", {});
        if (res && res.ok) {
          _cdpProfileList = res.profiles || [];
          const sel = document.getElementById("selCdpProfile");
          if (sel) {
            sel.innerHTML = '<option value="">-- Chọn Chrome Profile --</option>';
            const groups = { system: "🖥️ System Chrome Profiles", native: "🛠️ Tool Native Profiles" };
            const grouped = { system: [], native: [] };
            for (const p of _cdpProfileList) {
              grouped[p.source]?.push(p);
            }
            for (const [src, label] of Object.entries(groups)) {
              const items = grouped[src] || [];
              if (!items.length) continue;
              const og = document.createElement("optgroup");
              og.label = label;
              for (const p of items) {
                const opt = document.createElement("option");
                opt.value = p.id;
                const hasSession = p.has_session ? "✅" : "⬜";
                opt.textContent = `${hasSession} ${p.id}${p.email ? " — " + p.email : ""}${p.name && p.name !== p.id ? " (" + p.name + ")" : ""}`;
                og.appendChild(opt);
              }
              sel.appendChild(og);
            }
            // Auto-select Profile 13 (leviettung04)
            const auto = _cdpProfileList.find(p => p.email && p.email.includes("leviettung04"));
            if (auto) sel.value = auto.id;
          }
        }
      } catch(e) {}
    }

    async function extractSessionFromProfile() {
      const sel = document.getElementById("selCdpProfile");
      const profile = sel ? sel.value : "";
      if (!profile) { toast("❌ Chưa chọn profile!", "err"); return; }
      const btn = document.getElementById("btnExtractSession");
      if (btn) { btn.disabled = true; btn.textContent = "⏳ Đang lấy session..."; }
      const dot = document.getElementById("cdpStatusDot");
      const msg = document.getElementById("cdpStatusMsg");
      if (dot) dot.style.background = "#fbbf24";
      if (msg) msg.textContent = "Đang mở Chrome profile và lấy cookies...";
      try {
        const res = await apiPost("/api/flow/extract_session", { profile });
        if (res && res.ok) {
          if (dot) dot.style.background = "#22c55e";
          if (msg) msg.innerHTML = `<b style="color:#22c55e">✅ Đã lấy session!</b> ${res.message || ""}`;
          toast("✅ " + (res.message || "Session đã được lưu!"), "ok");
          document.getElementById("chromeCdpBanner")?.style?.setProperty("border-color", "rgba(34,197,94,0.6)");
          loadCdpProfileList(); // Refresh để cập nhật ✅
        } else {
          if (dot) dot.style.background = "#ef4444";
          if (msg) msg.innerHTML = `<b style="color:#ef4444">❌ Thất bại:</b> ${(res && res.error) || "Lỗi không xác định"}`;
          toast("❌ " + ((res && res.error) || "Extraction thất bại"), "err");
        }
      } catch(e) {
        if (dot) dot.style.background = "#ef4444";
        toast("❌ Lỗi: " + e.message, "err");
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = "🔑 Lấy Session"; }
      }
    }

    async function extractSessionViaCdp() {
      const btn = document.getElementById("btnExtractCdp");
      if (btn) { btn.disabled = true; btn.textContent = "⏳..."; }
      try {
        const res = await apiPost("/api/flow/extract_session", { profile: "cdp" });
        if (res && res.ok) {
          toast("✅ " + (res.message || "CDP session đã được lưu!"), "ok");
          const msg = document.getElementById("cdpStatusMsg");
          if (msg) msg.innerHTML = `<b style="color:#22c55e">✅ CDP Session OK!</b> ${res.message || ""}`;
        } else {
          toast("❌ " + ((res && res.error) || "CDP extraction thất bại"), "err");
        }
      } catch(e) {
        toast("❌ " + e.message, "err");
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = "🔗 Lấy từ CDP"; }
      }
    }
// === Token Manager auto-refresh controls ===
async function toggleAutoRefreshToken(enabled) {
  const profileSel = document.getElementById("selCdpProfile");
  const profiles = profileSel && profileSel.value ? [profileSel.value] : null;
  try {
    const r = await fetch("/api/flow/token_manager_toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled, profiles })
    });
    const res = await r.json();
    const statusEl = document.getElementById("tokenMgrStatusText");
    if (statusEl) statusEl.textContent = res?.message || (enabled ? "✅ Đang hoạt động" : "⬜ Đã tắt");
    if (typeof toast === "function") toast(res?.message || (enabled ? "✅ Tự động refresh bật" : "⬜ Tự động refresh tắt"), res?.ok ? "ok" : "err");
  } catch(e) {
    if (typeof toast === "function") toast("Lỗi toggle token manager: " + e, "err");
  }
}

async function checkTokenManagerStatus() {
  const statusEl = document.getElementById("tokenMgrStatusText");
  if (statusEl) statusEl.textContent = "Đang kiểm tra...";
  try {
    const r2 = await fetch("/api/flow/token_manager_status");
    const res = await r2.json();
    if (!res) return;
    const enabled = res.enabled ? "✅ Bật" : "⬜ Tắt";
    const profiles = res.profiles ? res.profiles.join(", ") : "Tất cả";
    const lastRefresh = res.last_refresh || "Chưa";
    const statusText = `${enabled} | Profiles: ${profiles} | Làm mới lần cuối: ${lastRefresh}`;
    if (statusEl) statusEl.textContent = statusText;
    // Sync checkbox
    const chk = document.getElementById("chkAutoRefreshToken");
    if (chk) chk.checked = !!res.enabled;
    if (typeof toast === "function") toast(`Token Manager: ${enabledTxt}`, "ok");
  } catch(e) {
    if (statusEl) statusEl.textContent = "Lỗi kết nối";
    if (typeof toast === "function") toast("Lỗi kiểm tra token manager: " + e, "err");
  }
}



    // Patch: Load profile list khi vào tab accounts (CDP banner đã chuyển sang Tài Khoản)
    const _origSwitchTabExt = typeof _origSwitchTab !== "undefined" ? _origSwitchTab : (window.switchTab || null);
    if (!window._cdpSwitchPatched && typeof switchTab === "function") {
      const _prevSwitch = window.switchTab;
      window.switchTab = function(tabId, btn) {
        _prevSwitch(tabId, btn);
        if (tabId === "accounts") {
          setTimeout(() => { checkChromeCdpStatus(); loadCdpProfileList(); }, 400);
        }
      };
      window._cdpSwitchPatched = true;
    }

    // =========================================================================================
    (function bootstrapSkillStudio() {
      initFloatingAssistantDrag();
      refreshAll(false);
      loadProductsStore(false);
      loadTemplatesMarketplace(false);
      loadCharacterLibrary();
      setInterval(async () => {
        refreshAll(true);
        const isFashionTab = document.getElementById("tab-fashion-motion")?.classList.contains("active");
        if (isFashionTab && !STATE._fashionFlowPollTimer) {
          try {
            const curSlug = STATE.fashionProject?.project_id || "";
            const r = await apiGet(`/api/fashion_motion/projects?project_id=${encodeURIComponent(curSlug)}`);
            if (r && r.ok) {
              const nextProj = r.active_project || r.current_project;
              const prevDoneCnt = (STATE.fashionProjectsList || []).filter(p => p.final_video_ready).length;
              const nextDoneCnt = (r.projects || []).filter(p => p.final_video_ready).length;
              const prevUpd = STATE.fashionProject?.updated_at || "";
              const nextUpd = nextProj?.updated_at || "";
              if (nextProj && (nextDoneCnt !== prevDoneCnt || nextUpd !== prevUpd || nextProj.status === "running_flow")) {
                STATE.fashionProjectsList = r.projects || [];
                STATE.fashionProject = nextProj;
                populateFashionProjectDropdown();
                renderFashionCompletedVideosShelf();
                renderFashionLiveMonitorBar();
                renderFashionScenesTimeline();
                renderFashionFinalPostProdCard();
                if (nextProj.status === "running_flow") {
                  startFashionLiveStatusMonitor(nextProj.project_id);
                }
              }
            }
          } catch (e) {}
        }
      }, 5000);
    })();
  