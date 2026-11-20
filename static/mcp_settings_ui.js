(() => {
  const MOUNT_ID = "mcpSettingsMount";
  let mcpState = null;
  let activeClientTab = "antigravity";
  let showRawToken = false;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));

  async function mcpReq(url, body) {
    const res = await fetch(url, body ? {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    } : {});
    return await res.json();
  }

  function notify(msg, kind = "ok") {
    if (typeof toast === "function") toast(msg, kind);
    else alert(msg);
  }

  async function copyText(text, label) {
    try {
      await navigator.clipboard.writeText(text);
      notify(`📋 Đã copy ${label}!`, "ok");
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      notify(`📋 Đã copy ${label}!`, "ok");
    }
  }

  function render() {
    const mount = document.getElementById(MOUNT_ID);
    if (!mount) return;
    if (!mcpState) {
      mount.innerHTML = `<div style="padding:14px; color:#94a3b8; font-size:12px;">⏳ Đang tải trạng thái cổng MCP AI Agent...</div>`;
      return;
    }

    const entitled = Boolean(mcpState.entitled);
    const enabled = Boolean(mcpState.enabled);
    const ent = mcpState.entitlement || {};
    const cfg = mcpState.client_configs || {};
    const audit = Array.isArray(mcpState.recent_audit) ? mcpState.recent_audit : [];
    const tools = Array.isArray(mcpState.tools_summary) ? mcpState.tools_summary : [];

    const clientTabs = [
      { id: "antigravity", label: "⚡ Antigravity / Gemini CLI", code: cfg.antigravity_gemini || "" },
      { id: "claude_cli", label: "🤖 Claude Code (CLI)", code: cfg.claude_code_cli || "" },
      { id: "claude_desktop", label: "🖥️ Claude Desktop (Stdio)", code: cfg.claude_desktop_stdio || "" },
      { id: "codex", label: "💬 ChatGPT / Codex CLI", code: cfg.codex_chatgpt_toml || "" },
    ];
    const curTab = clientTabs.find((t) => t.id === activeClientTab) || clientTabs[0];

    mount.innerHTML = `
      <div style="background:linear-gradient(135deg, rgba(15,23,42,0.96), rgba(30,27,75,0.55)); border:1px solid ${entitled ? 'rgba(56,189,248,0.45)' : 'rgba(245,158,11,0.45)'}; border-radius:14px; padding:16px 18px; margin-top:16px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap; margin-bottom:12px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <h3 style="margin:0; font-size:15px; color:#f8fafc;">🤖 Kết Nối AI Agent qua MCP (ChatGPT/Codex · Claude · Gemini/Antigravity)</h3>
              <span style="padding:2px 9px; border-radius:999px; font-size:11px; font-weight:800; ${entitled ? 'background:rgba(16,185,129,0.2); color:#6ee7b7; border:1px solid rgba(16,185,129,0.5);' : 'background:rgba(245,158,11,0.18); color:#fde68a; border:1px solid rgba(245,158,11,0.5);'}">
                ${entitled ? `✅ Đã Cấp Quyền MCP (${esc(ent.account || 'Pro')})` : '🔒 Chỉ Mở Cho Tài Khoản Được Cấp Quyền'}
              </span>
            </div>
            <div style="font-size:12px; color:#cbd5e1; margin-top:5px; line-height:1.5;">
              Cho phép AI Agent ra lệnh trực tiếp cho tool tạo video theo ID sản phẩm, chọn Template, tạo nhân vật &amp; giọng đọc, kiểm tra tiến độ, retry cảnh lỗi…
              <b style="color:#7dd3fc;">Bảo mật 100% mã nguồn</b> (chỉ mở các công cụ nghiệp vụ theo ID, không lộ mã nguồn, cookie hay token).
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:11px; color:#94a3b8; background:#090d16; border:1px solid rgba(148,163,184,0.25); padding:4px 9px; border-radius:7px;" title="Mã thiết bị dùng khi xin cấp quyền MCP gắn máy">
              HWID: <code style="color:#38bdf8;">${esc(mcpState.hwid_short || '')}</code>
            </span>
            <button type="button" class="btn btn-xs btn-outline" id="mcpCopyHwidBtn">📋 Copy HWID</button>
          </div>
        </div>

        ${!entitled ? `
          <div style="background:rgba(15,23,42,0.85); border:1px dashed rgba(245,158,11,0.45); border-radius:10px; padding:12px 14px;">
            <div style="font-size:12px; color:#fde68a; font-weight:700; margin-bottom:6px;">🔐 ${esc(ent.reason || 'Tính năng đang bị khóa cho tài khoản thường.')}</div>
            <div style="font-size:11.5px; color:#94a3b8; margin-bottom:10px;">
              Nếu tài khoản của bạn đã được cấp <b>Mã Cấp Quyền MCP (MCP1.…)</b>, hãy dán vào ô bên dưới để kích hoạt:
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <input id="mcpGrantKeyInput" placeholder="Dán mã cấp quyền MCP1.eyJ..." style="flex:1; min-width:260px; font-family:Consolas, monospace; font-size:12px;" />
              <button type="button" class="btn btn-amber" id="mcpInstallGrantBtn" style="font-weight:800;">🔓 Kích Hoạt Quyền MCP</button>
            </div>
          </div>
        ` : `
          <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:10px; margin-bottom:12px;">
            <div style="background:#090d16; border:1px solid rgba(148,163,184,0.22); border-radius:10px; padding:10px 12px;">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
                <span style="font-size:12px; font-weight:800; color:#e2e8f0;">⚡ Trạng Thái Cổng MCP Local</span>
                <button type="button" class="btn btn-xs ${enabled ? 'btn-danger' : 'btn-success'}" id="mcpToggleBtn" style="font-weight:800;">
                  ${enabled ? '⏹️ Tắt Cổng MCP' : '▶️ Bật Cổng MCP'}
                </button>
              </div>
              <div style="font-size:11.5px; margin-top:6px; color:${enabled ? '#6ee7b7' : '#fbbf24'};">
                ${enabled ? '🟢 Đang hoạt động — Sẵn sàng nhận lệnh từ AI Agent' : '🟡 Đã cấp quyền nhưng đang Tắt'}
              </div>
              <div style="font-size:11px; color:#94a3b8; margin-top:4px;">
                Endpoint: <code style="color:#7dd3fc;">${esc(mcpState.endpoint_url)}</code>
                · Protocol <code>${esc(mcpState.protocol_version)}</code> · <b>${mcpState.tools_count || 0}</b> công cụ AI
              </div>
            </div>

            <div style="background:#090d16; border:1px solid rgba(148,163,184,0.22); border-radius:10px; padding:10px 12px;">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
                <span style="font-size:12px; font-weight:800; color:#e2e8f0;">🔑 Bearer Token Xác Thực</span>
                <div style="display:flex; gap:5px;">
                  <button type="button" class="btn btn-xs btn-outline" id="mcpRevealTokBtn">${showRawToken ? '🙈 Ẩn' : '👁️ Hiện'}</button>
                  <button type="button" class="btn btn-xs btn-primary" id="mcpCopyTokBtn">📋 Copy</button>
                  <button type="button" class="btn btn-xs btn-amber" id="mcpRotateTokBtn">🔄 Đổi Token</button>
                </div>
              </div>
              <div style="margin-top:7px; font-family:Consolas, monospace; font-size:11.5px; color:#fde68a; background:#0f172a; padding:6px 8px; border-radius:6px; word-break:break-all;">
                ${esc(showRawToken ? (mcpState.token || '') : (mcpState.token_masked || ''))}
              </div>
            </div>
          </div>

          <div style="background:#090d16; border:1px solid rgba(56,189,248,0.28); border-radius:10px; padding:11px 12px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
              <div style="display:flex; gap:6px; flex-wrap:wrap;">
                ${clientTabs.map((t) => `
                  <button type="button" class="btn btn-xs ${t.id === curTab.id ? 'btn-primary' : 'btn-outline'}" data-mcp-tab="${t.id}">${esc(t.label)}</button>
                `).join("")}
              </div>
              <button type="button" class="btn btn-xs btn-success" id="mcpCopyCfgBtn">📋 Copy Cấu Hình Này</button>
            </div>
            <pre id="mcpClientCfgPre" style="margin:0; padding:10px; background:#050811; border:1px solid rgba(148,163,184,0.18); border-radius:8px; color:#e2e8f0; font-family:Consolas, monospace; font-size:11.5px; overflow-x:auto; white-space:pre-wrap;">${esc(curTab.code)}</pre>
          </div>

          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
            <details style="background:#090d16; border:1px solid rgba(148,163,184,0.2); border-radius:9px; padding:8px 10px;">
              <summary style="cursor:pointer; font-size:12px; font-weight:700; color:#7dd3fc;">🧰 Danh sách ${tools.length} Công Cụ AI Agent được phép gọi</summary>
              <div style="margin-top:8px; max-height:210px; overflow-y:auto; display:flex; flex-direction:column; gap:5px;">
                ${tools.map((t) => `
                  <div style="font-size:11px; border-bottom:1px dashed rgba(148,163,184,0.12); padding-bottom:4px;">
                    <code style="color:#fde68a; font-weight:700;">${esc(t.name)}</code>
                    <div style="color:#94a3b8; margin-top:2px;">${esc(t.description)}</div>
                  </div>
                `).join("")}
              </div>
            </details>

            <details style="background:#090d16; border:1px solid rgba(148,163,184,0.2); border-radius:9px; padding:8px 10px;">
              <summary style="cursor:pointer; font-size:12px; font-weight:700; color:#a7f3d0;">📜 Nhật Ký Lệnh AI Agent Gần Nhất (${audit.length})</summary>
              <div style="margin-top:8px; max-height:210px; overflow-y:auto; display:flex; flex-direction:column; gap:4px; font-family:Consolas, monospace; font-size:10.5px;">
                ${audit.length ? audit.map((a) => `
                  <div style="color:${a.ok ? '#86efac' : '#fca5a5'}; border-bottom:1px dashed rgba(148,163,184,0.12); padding-bottom:3px;">
                    [${esc(a.ts)}] ${a.ok ? '✅' : '❌'} <b>${esc(a.tool)}</b> (${a.ms || 0}ms) ${a.error ? '— ' + esc(a.error) : ''}
                  </div>
                `).join("") : '<div style="color:#64748b;">Chưa có lệnh nào từ AI Agent.</div>'}
              </div>
            </details>
          </div>
        `}
      </div>
    `;

    const hwidBtn = document.getElementById("mcpCopyHwidBtn");
    if (hwidBtn) hwidBtn.onclick = () => copyText(mcpState.hwid_full || mcpState.hwid_short || "", "HWID máy");

    const installBtn = document.getElementById("mcpInstallGrantBtn");
    if (installBtn) {
      installBtn.onclick = async () => {
        const keyVal = (document.getElementById("mcpGrantKeyInput")?.value || "").trim();
        if (!keyVal) return notify("Vui lòng dán mã cấp quyền MCP1.… trước!", "err");
        const r = await mcpReq("/api/mcp/install-grant", { grant_key: keyVal });
        if (r && r.ok) {
          mcpState = r;
          render();
          notify(r.message || "✅ Đã mở khóa MCP!", "ok");
        } else {
          notify((r && r.error) || "Mã cấp quyền MCP không hợp lệ.", "err");
        }
      };
    }

    const toggleBtn = document.getElementById("mcpToggleBtn");
    if (toggleBtn) {
      toggleBtn.onclick = async () => {
        const r = await mcpReq("/api/mcp/toggle", { enabled: !enabled });
        if (r && r.ok) {
          mcpState = r;
          render();
          notify(r.enabled ? "🟢 Đã bật cổng MCP AI Agent!" : "⏹️ Đã tắt cổng MCP.", "ok");
        } else {
          notify((r && r.error) || "Không thể thay đổi trạng thái MCP.", "err");
        }
      };
    }

    const revBtn = document.getElementById("mcpRevealTokBtn");
    if (revBtn) revBtn.onclick = () => { showRawToken = !showRawToken; render(); };

    const copyTokBtn = document.getElementById("mcpCopyTokBtn");
    if (copyTokBtn) copyTokBtn.onclick = () => copyText(mcpState.token || "", "MCP Bearer Token");

    const rotBtn = document.getElementById("mcpRotateTokBtn");
    if (rotBtn) {
      rotBtn.onclick = async () => {
        if (!confirm("Tạo Bearer Token MCP mới? Các AI Agent cũ sẽ cần cập nhật token mới.")) return;
        const r = await mcpReq("/api/mcp/rotate-token", {});
        if (r && r.ok) {
          mcpState = r;
          render();
          notify(r.message || "✅ Đã xoay Token MCP mới!", "ok");
        } else {
          notify((r && r.error) || "Không thể tạo token mới.", "err");
        }
      };
    }

    mount.querySelectorAll("[data-mcp-tab]").forEach((btn) => {
      btn.onclick = () => { activeClientTab = btn.dataset.mcpTab; render(); };
    });

    const copyCfgBtn = document.getElementById("mcpCopyCfgBtn");
    if (copyCfgBtn) copyCfgBtn.onclick = () => copyText(curTab.code || "", `cấu hình ${curTab.label}`);
  }

  async function refreshMcpPanel() {
    try {
      const r = await mcpReq("/api/mcp/status");
      if (r && r.ok) {
        mcpState = r;
        render();
      }
    } catch (_) { }
  }

  window.refreshMcpSettingsPanel = refreshMcpPanel;
  document.addEventListener("DOMContentLoaded", () => {
    refreshMcpPanel();
    const navSet = document.getElementById("navBtn-settings");
    if (navSet) {
      navSet.addEventListener("click", () => setTimeout(refreshMcpPanel, 150));
    }
  });
})();
