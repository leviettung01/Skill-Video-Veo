(() => {
  const MODAL_ID = "modalTransformStudio";
  const STYLE_ID = "tsStudioStyles";
  let job = "";
  let timer = null;
  let queueTimer = null;
  let library = null;
  let data = null;
  let submitting = false;
  let activeTemplateCode = "";
  let charMode = "library"; // "library" | "upload" | "auto"
  let prodMode = "upload";  // "upload" | "library"
  let charUploadUrl = "";
  let prodUploadUrl = "";
  let monitorTab = "demo";  // "demo" | "final"
  let activeJobState = null;

  const find = (sel) => document.querySelector("#" + MODAL_ID + " " + sel);
  const findAll = (sel) => [...document.querySelectorAll("#" + MODAL_ID + " " + sel)];
  const media = (path) => "/api/media?path=" + encodeURIComponent(path);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));

  function setText(sel, value) {
    const el = find(sel);
    if (el) el.textContent = value;
  }

  async function request(url, body) {
    const response = await fetch(url, body ? {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    } : {});
    if (response.status === 404 && url.startsWith("/api/transform/default")) {
      throw new Error("Server đang chạy bản cũ. Vui lòng khởi động lại SkillAutoVeo để dùng Studio Biến Hình.");
    }
    const result = await response.json();
    if (!result.ok) throw new Error(result.error || "Tool không trả kết quả.");
    return result;
  }

  function fileData(file) {
    if (!file) return Promise.resolve("");
    if (file.size > 12000000) throw new Error("Ảnh tối đa 12 MB.");
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("Không đọc được tệp ảnh."));
      reader.readAsDataURL(file);
    });
  }

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      #${MODAL_ID} {
        z-index: 12000 !important;
      }
      #${MODAL_ID} [hidden] {
        display: none !important;
      }
      #${MODAL_ID} .ts-dialog {
        width: min(1140px, 96vw);
        max-width: 1140px !important;
        max-height: 92vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        padding: 0 !important;
        background: linear-gradient(180deg, #0f172a 0%, #090e1a 100%);
        border: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 0 28px 80px rgba(0, 0, 0, 0.72);
        border-radius: 18px;
      }
      #${MODAL_ID} input[type="checkbox"],
      #${MODAL_ID} input[type="radio"] {
        width: auto !important;
        flex: 0 0 auto;
        margin: 0;
        padding: 0;
      }
      #${MODAL_ID} .ts-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        padding: 15px 20px;
        background: rgba(15, 23, 42, 0.92);
        border-bottom: 1px solid rgba(148, 163, 184, 0.16);
      }
      #${MODAL_ID} .ts-head-left {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 0;
        flex: 1;
      }
      #${MODAL_ID} .ts-code-pill {
        flex-shrink: 0;
        padding: 5px 11px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.05em;
        color: #fef3c7;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.28), rgba(217, 119, 6, 0.14));
        border: 1px solid rgba(245, 158, 11, 0.48);
      }
      #${MODAL_ID} .ts-head-titles { min-width: 0; }
      #${MODAL_ID} .ts-title {
        font-size: 16px;
        font-weight: 800;
        color: #f8fafc;
        margin: 0;
        line-height: 1.25;
      }
      #${MODAL_ID} .ts-subtitle {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      #${MODAL_ID} .ts-head-actions {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-shrink: 0;
      }
      #${MODAL_ID} .ts-tpl-select {
        width: auto !important;
        min-width: 190px;
        max-width: 260px;
        padding: 7px 10px;
        border-radius: 10px;
        background: #162033;
        border: 1px solid rgba(148, 163, 184, 0.28);
        color: #e2e8f0;
        font-size: 12px;
        font-weight: 600;
      }
      #${MODAL_ID} .ts-close-btn {
        width: 34px;
        height: 34px;
        padding: 0;
        border-radius: 10px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
      }
      #${MODAL_ID} .ts-workspace {
        display: grid;
        grid-template-columns: minmax(0, 1.45fr) 360px;
        gap: 18px;
        padding: 18px 20px;
        overflow-y: auto;
        flex: 1;
        min-height: 0;
      }
      @media (max-width: 920px) {
        #${MODAL_ID} .ts-workspace {
          grid-template-columns: 1fr;
        }
      }
      #${MODAL_ID} .ts-col-left {
        display: flex;
        flex-direction: column;
        gap: 16px;
        min-width: 0;
      }
      #${MODAL_ID} .ts-section {
        background: rgba(15, 23, 42, 0.65);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 14px;
        padding: 14px 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      #${MODAL_ID} .ts-sec-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        flex-wrap: wrap;
      }
      #${MODAL_ID} .ts-sec-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 800;
        color: #f1f5f9;
        letter-spacing: 0.01em;
      }
      #${MODAL_ID} .ts-step-num {
        width: 22px;
        height: 22px;
        border-radius: 7px;
        background: rgba(245, 158, 11, 0.18);
        border: 1px solid rgba(245, 158, 11, 0.45);
        color: #fbbf24;
        font-size: 11px;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
      #${MODAL_ID} .ts-preset-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 10px;
      }
      #${MODAL_ID} .ts-preset-card {
        text-align: left;
        cursor: pointer;
        border-radius: 12px;
        padding: 12px 13px;
        background: #111a2c;
        border: 1px solid rgba(148, 163, 184, 0.2);
        color: #cbd5e1;
        transition: all 0.16s ease;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      #${MODAL_ID} .ts-preset-card:hover {
        border-color: rgba(245, 158, 11, 0.55);
        background: #162238;
        transform: translateY(-1px);
      }
      #${MODAL_ID} .ts-preset-card.active {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.16), rgba(6, 182, 212, 0.08));
        border-color: #f59e0b;
        box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.35), 0 8px 20px rgba(0, 0, 0, 0.25);
        color: #f8fafc;
      }
      #${MODAL_ID} .ts-preset-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }
      #${MODAL_ID} .ts-preset-name {
        font-size: 14px;
        font-weight: 800;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 7px;
      }
      #${MODAL_ID} .ts-preset-badge {
        font-size: 10px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 999px;
        background: rgba(148, 163, 184, 0.14);
        color: #94a3b8;
        white-space: nowrap;
      }
      #${MODAL_ID} .ts-preset-card.active .ts-preset-badge {
        background: rgba(245, 158, 11, 0.24);
        color: #fde68a;
      }
      #${MODAL_ID} .ts-preset-desc {
        font-size: 11.5px;
        line-height: 1.45;
        color: #94a3b8;
      }
      #${MODAL_ID} .ts-preset-card.active .ts-preset-desc {
        color: #cbd5e1;
      }
      #${MODAL_ID} .ts-audio-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
        padding: 10px 12px;
        border-radius: 10px;
        background: rgba(11, 18, 32, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.14);
      }
      #${MODAL_ID} .ts-switch {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        cursor: pointer;
        user-select: none;
        font-size: 12.5px;
        font-weight: 600;
        color: #e2e8f0;
      }
      #${MODAL_ID} .ts-switch input {
        position: absolute;
        opacity: 0;
        pointer-events: none;
      }
      #${MODAL_ID} .ts-switch-track {
        width: 38px;
        height: 22px;
        border-radius: 999px;
        background: #334155;
        border: 1px solid rgba(148, 163, 184, 0.35);
        position: relative;
        transition: all 0.18s ease;
        flex-shrink: 0;
      }
      #${MODAL_ID} .ts-switch-track::after {
        content: "";
        position: absolute;
        top: 2px;
        left: 2px;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #f8fafc;
        transition: transform 0.18s ease;
      }
      #${MODAL_ID} .ts-switch input:checked + .ts-switch-track {
        background: #10b981;
        border-color: #34d399;
      }
      #${MODAL_ID} .ts-switch input:checked + .ts-switch-track::after {
        transform: translateX(16px);
      }
      #${MODAL_ID} .ts-spec-chips {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
      }
      #${MODAL_ID} .ts-spec-chip {
        font-size: 11px;
        font-weight: 600;
        color: #94a3b8;
        padding: 3px 8px;
        border-radius: 7px;
        background: rgba(30, 41, 59, 0.8);
      }
      #${MODAL_ID} .ts-inputs-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }
      @media (max-width: 720px) {
        #${MODAL_ID} .ts-inputs-grid {
          grid-template-columns: 1fr;
        }
      }
      #${MODAL_ID} .ts-asset-card {
        border-radius: 12px;
        padding: 13px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        background: #0c1424;
      }
      #${MODAL_ID} .ts-asset-char {
        border: 1px solid rgba(6, 182, 212, 0.34);
        box-shadow: inset 0 1px 0 rgba(6, 182, 212, 0.1);
      }
      #${MODAL_ID} .ts-asset-prod {
        border: 1px solid rgba(245, 158, 11, 0.34);
        box-shadow: inset 0 1px 0 rgba(245, 158, 11, 0.1);
      }
      #${MODAL_ID} .ts-asset-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }
      #${MODAL_ID} .ts-asset-title {
        font-size: 13px;
        font-weight: 800;
        color: #f8fafc;
      }
      #${MODAL_ID} .ts-asset-tag {
        font-size: 10.5px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 999px;
      }
      #${MODAL_ID} .ts-tag-cyan { background: rgba(6, 182, 212, 0.18); color: #67e8f9; }
      #${MODAL_ID} .ts-tag-amber { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
      #${MODAL_ID} .ts-seg {
        display: flex;
        gap: 4px;
        padding: 3px;
        border-radius: 9px;
        background: #141f35;
        border: 1px solid rgba(148, 163, 184, 0.15);
      }
      #${MODAL_ID} .ts-seg-btn {
        flex: 1;
        border: none;
        background: transparent;
        color: #94a3b8;
        font-size: 11.5px;
        font-weight: 700;
        padding: 6px 8px;
        border-radius: 7px;
        cursor: pointer;
        transition: all 0.15s ease;
        white-space: nowrap;
      }
      #${MODAL_ID} .ts-seg-btn:hover { color: #e2e8f0; }
      #${MODAL_ID} .ts-seg-btn.active {
        background: #24334f;
        color: #f8fafc;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.28);
      }
      #${MODAL_ID} .ts-dropzone {
        position: relative;
        border: 1.5px dashed rgba(148, 163, 184, 0.36);
        border-radius: 11px;
        padding: 12px;
        min-height: 158px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(15, 23, 42, 0.55);
        cursor: pointer;
        transition: all 0.16s ease;
        text-align: center;
      }
      #${MODAL_ID} .ts-dropzone:hover,
      #${MODAL_ID} .ts-dropzone.dragover {
        border-color: #38bdf8;
        background: rgba(14, 116, 144, 0.14);
      }
      #${MODAL_ID} .ts-asset-prod .ts-dropzone:hover,
      #${MODAL_ID} .ts-asset-prod .ts-dropzone.dragover {
        border-color: #f59e0b;
        background: rgba(245, 158, 11, 0.11);
      }
      #${MODAL_ID} .ts-dropzone input[type="file"] {
        display: none !important;
      }
      #${MODAL_ID} .ts-dz-empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        color: #94a3b8;
      }
      #${MODAL_ID} .ts-dz-icon {
        width: 38px;
        height: 38px;
        border-radius: 11px;
        background: rgba(30, 41, 59, 0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
      }
      #${MODAL_ID} .ts-dz-filled {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 11px;
        text-align: left;
      }
      #${MODAL_ID} .ts-dz-thumb {
        width: 78px;
        height: 114px;
        object-fit: cover;
        border-radius: 9px;
        border: 1px solid rgba(148, 163, 184, 0.35);
        flex-shrink: 0;
        background: #080d18;
      }
      #${MODAL_ID} .ts-dz-meta {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      #${MODAL_ID} .ts-dz-fname {
        font-size: 12px;
        font-weight: 700;
        color: #f8fafc;
        word-break: break-word;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      #${MODAL_ID} .ts-dz-actions {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
      }
      #${MODAL_ID} .ts-mini-btn {
        font-size: 11px;
        font-weight: 700;
        padding: 4px 9px;
        border-radius: 7px;
        border: 1px solid rgba(148, 163, 184, 0.28);
        background: #172236;
        color: #e2e8f0;
        cursor: pointer;
      }
      #${MODAL_ID} .ts-mini-btn:hover { background: #22314d; }
      #${MODAL_ID} .ts-gallery-strip {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(76px, 1fr));
        gap: 7px;
        max-height: 168px;
        overflow-y: auto;
        padding: 2px;
      }
      #${MODAL_ID} .ts-avatar-card {
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 9px;
        padding: 4px;
        background: #121c30;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        gap: 4px;
        transition: all 0.14s ease;
        text-align: center;
      }
      #${MODAL_ID} .ts-avatar-card:hover { border-color: #38bdf8; }
      #${MODAL_ID} .ts-avatar-card.active {
        border-color: #06b6d4;
        background: rgba(6, 182, 212, 0.16);
        box-shadow: 0 0 0 1px rgba(6, 182, 212, 0.35);
      }
      #${MODAL_ID} .ts-avatar-card img {
        width: 100%;
        height: 68px;
        object-fit: cover;
        border-radius: 6px;
      }
      #${MODAL_ID} .ts-avatar-name {
        font-size: 10.5px;
        font-weight: 600;
        color: #e2e8f0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      #${MODAL_ID} .ts-provider-row {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 8px;
      }
      @media (max-width: 640px) {
        #${MODAL_ID} .ts-provider-row { grid-template-columns: 1fr; }
      }
      #${MODAL_ID} .ts-prov-pill {
        border: 1px solid rgba(148, 163, 184, 0.22);
        background: #10192b;
        border-radius: 10px;
        padding: 8px 10px;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        gap: 2px;
        text-align: left;
        transition: all 0.14s ease;
      }
      #${MODAL_ID} .ts-prov-pill:hover { border-color: rgba(245, 158, 11, 0.45); }
      #${MODAL_ID} .ts-prov-pill.active {
        border-color: #f59e0b;
        background: rgba(245, 158, 11, 0.14);
      }
      #${MODAL_ID} .ts-prov-pill strong { font-size: 12px; color: #f8fafc; }
      #${MODAL_ID} .ts-prov-pill span { font-size: 10.5px; color: #94a3b8; }
      #${MODAL_ID} .ts-col-right {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      #${MODAL_ID} .ts-monitor-card {
        background: #0a101d;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 16px;
        padding: 13px;
        display: flex;
        flex-direction: column;
        gap: 11px;
      }
      #${MODAL_ID} .ts-phone-frame {
        position: relative;
        width: 100%;
        max-width: 245px;
        aspect-ratio: 9 / 16;
        margin: 0 auto;
        border-radius: 18px;
        overflow: hidden;
        background: #03060c;
        border: 2px solid rgba(148, 163, 184, 0.24);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
      }
      #${MODAL_ID} .ts-phone-frame video {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }
      #${MODAL_ID} .ts-phone-empty {
        padding: 20px;
        text-align: center;
        color: #64748b;
        font-size: 12px;
        line-height: 1.5;
      }
      #${MODAL_ID} .ts-stepper {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 4px;
      }
      #${MODAL_ID} .ts-step-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        font-size: 9.5px;
        font-weight: 700;
        color: #64748b;
        text-align: center;
      }
      #${MODAL_ID} .ts-step-bar {
        width: 100%;
        height: 4px;
        border-radius: 999px;
        background: #1e293b;
      }
      #${MODAL_ID} .ts-step-item.done { color: #34d399; }
      #${MODAL_ID} .ts-step-item.done .ts-step-bar { background: #10b981; }
      #${MODAL_ID} .ts-step-item.active { color: #fbbf24; }
      #${MODAL_ID} .ts-step-item.active .ts-step-bar {
        background: linear-gradient(90deg, #f59e0b, #fbbf24);
        box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
      }
      #${MODAL_ID} .ts-status-box {
        border-radius: 10px;
        padding: 9px 11px;
        background: #11192b;
        border: 1px solid rgba(148, 163, 184, 0.18);
        font-size: 12px;
        line-height: 1.45;
        color: #cbd5e1;
        min-height: 42px;
        word-break: break-word;
      }
      #${MODAL_ID} .ts-status-box.running {
        border-color: rgba(245, 158, 11, 0.45);
        color: #fde68a;
        background: rgba(245, 158, 11, 0.08);
      }
      #${MODAL_ID} .ts-status-box.done {
        border-color: rgba(16, 185, 129, 0.48);
        color: #a7f3d0;
        background: rgba(16, 185, 129, 0.08);
      }
      #${MODAL_ID} .ts-status-box.error {
        border-color: rgba(239, 68, 68, 0.5);
        color: #fecaca;
        background: rgba(239, 68, 68, 0.1);
      }
      #${MODAL_ID} .ts-refs-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 7px;
      }
      #${MODAL_ID} .ts-ref-tile {
        display: flex;
        align-items: center;
        gap: 7px;
        padding: 5px;
        border-radius: 9px;
        background: #131d31;
        border: 1px solid rgba(148, 163, 184, 0.2);
        text-decoration: none;
        color: #e2e8f0;
        transition: border-color 0.15s ease;
      }
      #${MODAL_ID} .ts-ref-tile:hover { border-color: #38bdf8; }
      #${MODAL_ID} .ts-ref-tile img {
        width: 34px;
        height: 48px;
        object-fit: cover;
        border-radius: 6px;
        flex-shrink: 0;
      }
      #${MODAL_ID} .ts-ref-tile-info { min-width: 0; }
      #${MODAL_ID} .ts-ref-tile-name {
        font-size: 11px;
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      #${MODAL_ID} .ts-ref-tile-dim {
        font-size: 10px;
        color: #94a3b8;
      }
      #${MODAL_ID} .ts-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 13px 20px;
        background: rgba(11, 18, 32, 0.96);
        border-top: 1px solid rgba(148, 163, 184, 0.16);
        flex-wrap: wrap;
      }
      #${MODAL_ID} .ts-ready-note {
        font-size: 12px;
        color: #94a3b8;
      }
      #${MODAL_ID} .ts-footer-btns {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-left: auto;
      }
      #${MODAL_ID} .ts-cta-btn {
        background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%);
        color: #090d16;
        font-weight: 800;
        border: none;
        padding: 10px 20px;
        border-radius: 11px;
        cursor: pointer;
        font-size: 13.5px;
        box-shadow: 0 8px 22px rgba(245, 158, 11, 0.28);
        transition: all 0.16s ease;
      }
      #${MODAL_ID} .ts-cta-btn:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 12px 26px rgba(245, 158, 11, 0.38);
      }
      #${MODAL_ID} .ts-cta-btn:disabled {
        opacity: 0.55;
        cursor: not-allowed;
      }
      #${MODAL_ID} .ts-queue-panel {
        border: 1px solid rgba(56, 189, 248, 0.28);
        background: rgba(15, 23, 42, 0.72);
        border-radius: 10px;
        padding: 9px 10px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      #${MODAL_ID} .ts-queue-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
        font-size: 11px;
        font-weight: 800;
        color: #7dd3fc;
      }
      #${MODAL_ID} .ts-queue-list {
        display: flex;
        flex-direction: column;
        gap: 5px;
        max-height: 155px;
        overflow-y: auto;
      }
      #${MODAL_ID} .ts-queue-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        padding: 6px 8px;
        border-radius: 8px;
        background: #111b2e;
        border: 1px solid rgba(148, 163, 184, 0.16);
        font-size: 11px;
        color: #e2e8f0;
      }
      #${MODAL_ID} .ts-queue-item.is-current {
        border-color: rgba(245, 158, 11, 0.55);
        background: rgba(245, 158, 11, 0.08);
      }
      #${MODAL_ID} .ts-queue-info {
        min-width: 0;
        flex: 1;
      }
      #${MODAL_ID} .ts-queue-title {
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      #${MODAL_ID} .ts-queue-sub {
        font-size: 10px;
        color: #94a3b8;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      #${MODAL_ID} .ts-queue-go {
        border: 1px solid rgba(56, 189, 248, 0.45);
        background: rgba(14, 116, 144, 0.25);
        color: #e0f2fe;
        border-radius: 7px;
        padding: 3px 8px;
        font-size: 10.5px;
        font-weight: 700;
        cursor: pointer;
        flex-shrink: 0;
      }
      #${MODAL_ID} .ts-queue-go:hover {
        background: rgba(56, 189, 248, 0.3);
      }
    `;
    document.head.appendChild(style);
  }

  function renderTemplateHeader() {
    const tpl = data?.template || {};
    const code = tpl.code || "006";
    activeTemplateCode = code;
    setText("#tfCodePill", "TEMPLATE #" + code);
    setText("#tfTitle", tpl.name || "Studio Biến Hình");
    setText("#tfSubtitle", tpl.subtitle || tpl.description || "2 cảnh × 8 giây · Nhân vật + Sản phẩm tham chiếu 2K");

    const switcher = find("#tfTemplateSelect");
    const list = Array.isArray(data?.studio_templates) ? data.studio_templates : [];
    if (switcher) {
      switcher.replaceChildren(...list.map((t) => new Option(`#${t.code} · ${t.name} (${t.preset_count || 1} kịch bản)`, t.code)));
      switcher.value = code;
      switcher.hidden = list.length <= 1;
    }

    const charBox = find("#tfCharCard");
    if (charBox) charBox.hidden = tpl.supports_character === false;
    setText("#tfCharHeading", tpl.character_label || "Nhân vật tham chiếu");
    const prodBox = find("#tfProdCard");
    if (prodBox) prodBox.hidden = tpl.supports_product === false;
    setText("#tfProdHeading", tpl.product_label || "Sản phẩm / Trang phục");
    const downloadBtn = find("#tfDownload");
    if (downloadBtn) downloadBtn.setAttribute("download", `template_${code}.mp4`);
  }

  function renderPresetCards() {
    const sel = find("#tfPreset");
    const grid = find("#tfPresetGrid");
    if (!sel || !grid) return;
    const entries = Object.entries(data?.presets || {});
    const prev = sel.value;
    sel.replaceChildren(...entries.map(([k, p]) => new Option(p.title || k, k)));
    if (prev && data?.presets?.[prev]) sel.value = prev;
    else if (entries.length) sel.value = entries[0][0];

    const activeKey = sel.value;
    grid.replaceChildren(...entries.map(([key, p]) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ts-preset-card" + (key === activeKey ? " active" : "");
      btn.innerHTML = `
        <div class="ts-preset-top">
          <div class="ts-preset-name"><span>${esc(p.icon || "🎬")}</span><span>${esc(p.title || key)}</span></div>
          ${p.badge ? `<span class="ts-preset-badge">${esc(p.badge)}</span>` : ""}
        </div>
        <div class="ts-preset-desc">${esc(p.summary || "")}</div>
      `;
      btn.onclick = () => {
        sel.value = key;
        renderPresetCards();
        presetChanged();
        updateReadinessHint();
      };
      return btn;
    }));
  }

  function presetChanged() {
    const key = find("#tfPreset")?.value;
    const p = data?.presets?.[key];
    if (!p) return;
    setText("#tfSummary", p.summary || "");
    const demoVideo = find("#tfDemo");
    const demoMissing = find("#tfDemoEmpty");
    if (demoVideo) {
      if (p.demo_exists !== false && p.demo) {
        demoVideo.hidden = false;
        if (demoMissing) demoMissing.hidden = true;
        const src = media(p.demo);
        if (demoVideo.getAttribute("data-src") !== src) {
          demoVideo.setAttribute("data-src", src);
          demoVideo.src = src;
        }
      } else {
        demoVideo.hidden = true;
        if (demoMissing) demoMissing.hidden = false;
      }
    }

    const rows = [p.title, "", "TÁCH SẢN PHẨM NỀN TRẮNG 2K", data.product_prompt || ""];
    (p.scenes || []).forEach((s, i) => {
      rows.push("", `CẢNH ${i + 1} · ${s.title || ""} · ${s.duration_sec || 8}s`, "ẢNH: " + (s.image_prompt || ""), "VIDEO: " + (s.prompt || ""));
    });
    setText("#tfPrompts", rows.join("\n"));
  }

  function switchMonitorTab(tab) {
    monitorTab = tab === "final" ? "final" : "demo";
    findAll("[data-mon-tab]").forEach((b) => b.classList.toggle("active", b.dataset.monTab === monitorTab));
    const demoV = find("#tfDemo");
    const demoEmpty = find("#tfDemoEmpty");
    const finalV = find("#tfFinal");
    const finalEmpty = find("#tfFinalEmpty");
    const hasFinal = Boolean(finalV && finalV.getAttribute("data-path"));
    const p = data?.presets?.[find("#tfPreset")?.value];
    const hasDemo = Boolean(p && p.demo_exists !== false && p.demo);

    if (monitorTab === "demo") {
      if (finalV) { finalV.pause(); finalV.hidden = true; }
      if (finalEmpty) finalEmpty.hidden = true;
      if (demoV) demoV.hidden = !hasDemo;
      if (demoEmpty) demoEmpty.hidden = hasDemo;
    } else {
      if (demoV) { demoV.pause(); demoV.hidden = true; }
      if (demoEmpty) demoEmpty.hidden = true;
      if (finalV) finalV.hidden = !hasFinal;
      if (finalEmpty) finalEmpty.hidden = hasFinal;
    }
  }

  function setCharacterMode(mode) {
    charMode = mode;
    findAll("[data-char-mode]").forEach((b) => b.classList.toggle("active", b.dataset.charMode === charMode));
    const libPane = find("#tfCharLibPane");
    const upPane = find("#tfCharUploadPane");
    const autoPane = find("#tfCharAutoPane");
    if (libPane) libPane.hidden = charMode !== "library";
    if (upPane) upPane.hidden = charMode !== "upload";
    if (autoPane) autoPane.hidden = charMode !== "auto";

    if (charMode !== "upload") {
      find("#tfCharacter").value = "";
    }
    if (charMode === "auto") {
      find("#tfCharSelect").value = "";
    }
    renderCharacterPreview();
    updateReadinessHint();
  }

  function populateCharacters() {
    const sel = find("#tfCharSelect");
    const strip = find("#tfCharGrid");
    const chars = Array.isArray(data?.characters) ? data.characters : [];
    if (sel) {
      const prev = sel.value;
      sel.replaceChildren(
        new Option("Tự AI tạo khuôn mặt", ""),
        ...chars.map((c) => new Option(c.name || c.key, c.key)),
        new Option("Tải từ máy", "__upload__")
      );
      if (prev && [...sel.options].some((o) => o.value === prev)) sel.value = prev;
      else if (charMode === "library" && chars.length) sel.value = chars[0].key;
      else if (!chars.length && charMode === "library") charMode = "upload";
    }
    if (strip) {
      if (!chars.length) {
        strip.innerHTML = `<div style="grid-column:1/-1;font-size:11.5px;color:#94a3b8;padding:12px;text-align:center">Thư viện chưa có nhân vật. Hãy chuyển sang tab <b>Tải lên</b> để chọn ảnh từ máy.</div>`;
      } else {
        const curKey = sel?.value || "";
        strip.replaceChildren(...chars.map((c) => {
          const rawPreview = String(c.preview || c.path || "");
          const src = (rawPreview.startsWith("/api/") || rawPreview.startsWith("data:") || rawPreview.startsWith("http"))
            ? rawPreview
            : media(rawPreview.replace(/^\/+/, ""));
          const card = document.createElement("button");
          card.type = "button";
          card.className = "ts-avatar-card" + (c.key === curKey ? " active" : "");
          card.innerHTML = `<img src="${esc(src)}" alt="${esc(c.name || c.key)}"><div class="ts-avatar-name">${esc(c.name || c.key)}</div>`;
          card.onclick = () => {
            if (sel) sel.value = c.key;
            setCharacterMode("library");
            populateCharacters();
          };
          return card;
        }));
      }
    }
    setCharacterMode(charMode);
  }

  function renderCharacterPreview() {
    const file = find("#tfCharacter")?.files?.[0];
    const selVal = find("#tfCharSelect")?.value || "";
    const emptyBox = find("#tfCharDzEmpty");
    const filledBox = find("#tfCharDzFilled");
    const dzImg = find("#tfCharPreview");

    if (charMode === "upload" && file) {
      if (charUploadUrl && charUploadUrl.startsWith("blob:")) URL.revokeObjectURL(charUploadUrl);
      charUploadUrl = URL.createObjectURL(file);
      if (dzImg) { dzImg.src = charUploadUrl; dzImg.hidden = false; }
      setText("#tfCharFileName", file.name);
      setText("#tfCharFileMeta", `${(file.size / 1024).toFixed(0)} KB · Giữ đúng khuôn mặt qua 2 cảnh`);
      if (emptyBox) emptyBox.hidden = true;
      if (filledBox) filledBox.hidden = false;
      setText("#tfCharCaption", "✓ Ảnh nhân vật tự tải: " + file.name);
      return;
    }

    if (emptyBox) emptyBox.hidden = false;
    if (filledBox) filledBox.hidden = true;
    if (charMode === "library" && selVal && selVal !== "__upload__") {
      const chosen = (data?.characters || []).find((c) => c.key === selVal);
      setText("#tfCharCaption", chosen ? ("✓ Thư viện nhân vật: " + (chosen.name || chosen.key)) : "");
    } else if (charMode === "upload") {
      setText("#tfCharCaption", "Kéo thả hoặc nhấn vào khung trên để tải ảnh chân dung / Character Sheet");
    } else {
      setText("#tfCharCaption", "AI sẽ tự tạo gương mặt phù hợp với kịch bản");
    }
  }

  async function setProductMode(mode) {
    prodMode = mode === "library" ? "library" : "upload";
    findAll("[data-prod-mode]").forEach((b) => b.classList.toggle("active", b.dataset.prodMode === prodMode));
    const sourceSel = find("#tfSource");
    if (sourceSel) sourceSel.value = prodMode;
    find("#tfUploadRow").hidden = prodMode !== "upload";
    find("#tfLibrary").hidden = prodMode !== "library";

    if (prodMode === "library" && !library) {
      try {
        library = (await request("/api/transform/products")).products || [];
        filterProducts();
      } catch (err) {
        setText("#tfStatus", err.message);
      }
    }
    updateReadinessHint();
  }

  function renderProductUploadPreview() {
    const file = find("#tfUpload")?.files?.[0];
    const emptyBox = find("#tfProdDzEmpty");
    const filledBox = find("#tfProdDzFilled");
    const img = find("#tfUploadPreview");

    if (file) {
      if (prodUploadUrl && prodUploadUrl.startsWith("blob:")) URL.revokeObjectURL(prodUploadUrl);
      prodUploadUrl = URL.createObjectURL(file);
      if (img) { img.src = prodUploadUrl; img.hidden = false; }
      setText("#tfProdFileName", file.name);
      setText("#tfProdFileMeta", `${(file.size / 1024).toFixed(0)} KB · Tự tách nền trắng #FFFFFF 2K`);
      if (emptyBox) emptyBox.hidden = true;
      if (filledBox) filledBox.hidden = false;
    } else {
      if (img) { img.hidden = true; img.removeAttribute("src"); }
      if (emptyBox) emptyBox.hidden = false;
      if (filledBox) filledBox.hidden = true;
    }
    updateReadinessHint();
  }

  function filterProducts() {
    const q = (find("#tfSearch")?.value || "").toLocaleLowerCase().trim();
    const items = (library || []).filter((p) => p.images?.length && (p.title + " " + (p.category || "") + " " + p.id).toLocaleLowerCase().includes(q));
    const sel = find("#tfProduct");
    const prev = sel?.value;
    if (sel) {
      sel.replaceChildren(
        new Option(items.length ? "Chọn sản phẩm..." : "Không tìm thấy sản phẩm", ""),
        ...items.map((p) => new Option(p.title, p.id))
      );
      if (prev && items.some((x) => x.id === prev)) sel.value = prev;
      else if (items.length) sel.value = items[0].id;
    }
    const grid = find("#tfProductGrid");
    if (grid) {
      const curId = sel?.value || "";
      if (!items.length) {
        grid.innerHTML = `<div style="grid-column:1/-1;font-size:11.5px;color:#94a3b8;padding:12px;text-align:center">Kho chưa có sản phẩm phù hợp.</div>`;
      } else {
        grid.replaceChildren(...items.slice(0, 24).map((p) => {
          const thumb = p.images[0]?.path ? media(p.images[0].path) : "";
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "ts-avatar-card" + (p.id === curId ? " active" : "");
          btn.innerHTML = `${thumb ? `<img src="${esc(thumb)}" alt="${esc(p.title)}">` : ""}<div class="ts-avatar-name">${esc(p.title)}</div>`;
          btn.onclick = () => {
            if (sel) sel.value = p.id;
            filterProducts();
            libraryImages();
          };
          return btn;
        }));
      }
    }
    libraryImages();
  }

  function libraryImages() {
    const p = (library || []).find((x) => x.id === find("#tfProduct")?.value);
    const imgSel = find("#tfImage");
    if (imgSel) {
      imgSel.replaceChildren(...(p?.images || []).map((img, i) => new Option("Góc ảnh " + (i + 1), img.index)));
    }
    libraryPreview();
    updateReadinessHint();
  }

  function libraryPreview() {
    const p = (library || []).find((x) => x.id === find("#tfProduct")?.value);
    const chosen = p?.images?.find((x) => String(x.index) === String(find("#tfImage")?.value));
    const image = find("#tfPreview");
    if (image) {
      image.hidden = !chosen;
      if (chosen) image.src = media(chosen.path);
      else image.removeAttribute("src");
    }
  }

  function updateReadinessHint() {
    const hint = find("#tfReadiness");
    if (!hint) return;
    const presetTitle = data?.presets?.[find("#tfPreset")?.value]?.title || "Kịch bản";
    const tpl = data?.template || {};
    let charText = "AI tự tạo mặt";
    if (tpl.supports_character === false) {
      charText = "";
    } else if (charMode === "upload") {
      const f = find("#tfCharacter")?.files?.[0];
      charText = f ? ("NV: " + f.name) : "⚠️ Thiếu file nhân vật";
    } else if (charMode === "library") {
      const key = find("#tfCharSelect")?.value;
      const c = (data?.characters || []).find((x) => x.key === key);
      charText = c ? ("NV: " + (c.name || c.key)) : "⚠️ Chưa chọn NV";
    }

    let prodText = "";
    if (tpl.supports_product !== false) {
      if (prodMode === "upload") {
        const pf = find("#tfUpload")?.files?.[0];
        prodText = pf ? ("SP: " + pf.name) : "⚠️ Chưa tải ảnh sản phẩm";
      } else {
        const pid = find("#tfProduct")?.value;
        const p = (library || []).find((x) => x.id === pid);
        prodText = p ? ("SP: " + p.title) : "⚠️ Chưa chọn SP trong kho";
      }
    }
    hint.textContent = [presetTitle, charText, prodText].filter(Boolean).join(" · ");
  }

  const REF_LABELS = {
    character: "Nhân vật gốc",
    product: "Sản phẩm 2K",
    before: "Ảnh Cảnh 1",
    reveal: "Ảnh Cảnh 2"
  };

  function updateStepper(state) {
    const steps = findAll("#tfStepper .ts-step-item");
    if (!steps.length) return;
    const refs = state?.refs || {};
    const status = state?.status || "";
    const hasProd = Boolean(refs.product);
    const hasBefore = Boolean(refs.before);
    const hasReveal = Boolean(refs.reveal);
    const hasFinal = Boolean(state?.final);
    const doneCount = status === "done" && hasFinal ? 5 : hasReveal ? 3 : hasBefore ? 2 : hasProd ? 1 : 0;
    const activeIdx = (status === "running" || status === "queued") ? Math.min(4, doneCount) : -1;

    steps.forEach((el, idx) => {
      el.classList.toggle("done", idx < doneCount);
      el.classList.toggle("active", idx === activeIdx);
    });
  }

  function showState(state) {
    activeJobState = state;
    const box = find("#tfStatus");
    if (box) {
      box.textContent = state?.message || "Sẵn sàng nhận ảnh nhân vật & sản phẩm để dựng video 16s.";
      box.className = "ts-status-box " + (state?.status || "");
    }
    updateStepper(state);

    const refs = find("#tfRefs");
    if (refs) {
      refs.replaceChildren();
      Object.entries(state?.refs || {}).forEach(([key, ref]) => {
        const refPath = typeof ref === "string" ? ref : ref?.path;
        if (!refPath) return;
        const dims = Array.isArray(ref?.dimensions) && ref.dimensions.length ? ref.dimensions.join("×") : "";
        const tile = document.createElement("a");
        tile.className = "ts-ref-tile";
        tile.href = media(refPath);
        tile.download = key + (key === "character" ? "_input.jpg" : "_2k.jpg");
        tile.title = "Nhấn để tải " + (REF_LABELS[key] || key);
        tile.innerHTML = `
          <img src="${esc(media(refPath))}" alt="${esc(REF_LABELS[key] || key)}">
          <div class="ts-ref-tile-info">
            <div class="ts-ref-tile-name">${esc(REF_LABELS[key] || key)}</div>
            <div class="ts-ref-tile-dim">${esc(dims || "Tải ảnh")}</div>
          </div>
        `;
        refs.appendChild(tile);
      });
    }

    const video = find("#tfFinal");
    const download = find("#tfDownload");
    const openProjBtn = find("#tfOpenProj");
    if (state?.final) {
      const nextSrc = media(state.final);
      if (video && video.getAttribute("data-path") !== state.final) {
        video.setAttribute("data-path", state.final);
        video.src = nextSrc;
      }
      if (download) { download.href = nextSrc; download.hidden = false; }
      if (openProjBtn) openProjBtn.hidden = false;
      if (state.status === "done") switchMonitorTab("final");
    } else {
      if (video) {
        video.removeAttribute("data-path");
        video.removeAttribute("src");
        video.load();
      }
      if (download) download.hidden = true;
      if (openProjBtn) openProjBtn.hidden = true;
    }
  }

  function pushProjectToStudio(projectObj, pid, opts = { activateTab: true }) {
    if (!pid) return;
    try {
      if (typeof STATE === "object" && STATE) {
        if (projectObj && typeof projectObj === "object") {
          const idxEntry = Object.assign({}, projectObj);
          delete idxEntry.products;
          if (!Array.isArray(STATE.projects)) STATE.projects = [];
          STATE.projects = [idxEntry, ...STATE.projects.filter((p) => p && p.id !== pid)];
          if (STATE.projectDetailsCache && typeof STATE.projectDetailsCache === "object") {
            STATE.projectDetailsCache[pid] = projectObj;
          }
        }
        STATE.currentProjectId = pid;
        STATE.renderedProjectSig = "";
      }
      if (opts && opts.activateTab !== false && typeof switchTab === "function") {
        switchTab("dashboard", document.getElementById("navBtn-dashboard"));
      }
      if (typeof renderProjectsList === "function") renderProjectsList();
      if (typeof loadProjectDetail === "function") {
        Promise.resolve(loadProjectDetail(pid, false)).catch(() => { });
      }
      if (typeof refreshAll === "function") {
        Promise.resolve(refreshAll(false)).catch(() => { });
      }
    } catch (_) { }
  }

  function openProjectInStudio(pid) {
    const targetPid = pid || job;
    find("#tfDemo")?.pause();
    find("#tfFinal")?.pause();
    closeModal(MODAL_ID);
    if (targetPid) {
      pushProjectToStudio(null, targetPid, { activateTab: true });
    } else if (typeof switchTab === "function") {
      switchTab("dashboard", document.getElementById("navBtn-dashboard"));
    }
  }

  function renderStudioQueue(queueRes) {
    const wrap = find("#tfStudioQueue");
    const viewBtn = find("#tfViewStudio");
    const rows = Array.isArray(queueRes?.jobs) ? queueRes.jobs : [];
    const activeRows = rows.filter((r) => r.is_running);
    const displayRows = rows.slice(0, 6);
    if (viewBtn) {
      viewBtn.hidden = rows.length === 0 && !job;
      if (activeRows.length > 0) {
        viewBtn.textContent = `📺 Studio Dự Án (${activeRows.length} đang chạy)`;
      } else {
        viewBtn.textContent = "📺 Mở Studio Dự Án";
      }
    }
    if (!wrap) return;
    if (!displayRows.length) {
      wrap.hidden = true;
      wrap.replaceChildren();
      return;
    }
    wrap.hidden = false;
    const maxSlots = Number(queueRes?.max_slots || 2);
    const activeCnt = Number(queueRes?.active_count || 0);
    const queuedCnt = Number(queueRes?.queued_count || 0);
    const summaryText = activeRows.length > 0
      ? `🚀 Đa luồng: ${activeCnt}/${maxSlots} chạy · ${queuedCnt} chờ`
      : `📂 Dự án Studio gần đây (${displayRows.length})`;
    wrap.innerHTML = `
      <div class="ts-queue-head">
        <span>${esc(summaryText)}</span>
        <button type="button" class="ts-queue-go" id="tfQueueOpenStudio">Mở Studio →</button>
      </div>
      <div class="ts-queue-list" id="tfQueueList"></div>
    `;
    const listEl = find("#tfQueueList");
    displayRows.forEach((r) => {
      const item = document.createElement("div");
      item.className = "ts-queue-item" + (r.id === job ? " is-current" : "");
      const badge = r.is_running
        ? (r.is_queued ? `⏳ Xếp hàng (${r.progress_pct || 0}%)` : `⚡ ${r.progress_pct || 0}%`)
        : (r.status === "done" ? "✅ Xong 100%" : (r.status === "stopped" ? "⏹ Đã dừng" : "❌ Lỗi"));
      item.innerHTML = `
        <div class="ts-queue-info" style="cursor:pointer">
          <div class="ts-queue-title">${esc(r.name || r.id)}</div>
          <div class="ts-queue-sub">${esc(badge)} · ${esc(r.message || "")}</div>
        </div>
        <button type="button" class="ts-queue-go">Xem</button>
      `;
      item.querySelector(".ts-queue-info").onclick = () => {
        job = r.id;
        check().catch(() => { });
      };
      item.querySelector(".ts-queue-go").onclick = () => openProjectInStudio(r.id);
      listEl?.appendChild(item);
    });
    const openAllBtn = find("#tfQueueOpenStudio");
    if (openAllBtn) openAllBtn.onclick = () => openProjectInStudio(activeRows[0]?.id || job || displayRows[0]?.id || "");
  }

  async function refreshStudioQueue() {
    clearTimeout(queueTimer);
    const modal = document.getElementById(MODAL_ID);
    if (!modal || modal.hidden || (!modal.classList.contains("open") && !modal.classList.contains("active"))) return;
    try {
      const qRes = await request("/api/transform/jobs?limit=12");
      renderStudioQueue(qRes);
      if ((qRes?.active_count || 0) > 0 || (qRes?.queued_count || 0) > 0) {
        queueTimer = setTimeout(refreshStudioQueue, 3200);
      }
    } catch (_) { }
  }

  async function check() {
    clearTimeout(timer);
    const startBtn = find("#tfStart");
    if (startBtn && !submitting) {
      startBtn.disabled = false;
      startBtn.textContent = "✨ Tạo Video 16s Ngay";
    }
    if (!job) {
      showState({ status: "", message: "Sẵn sàng tạo nhiều video 16s song song — bấm Tạo để chuyển ngay sang Studio Dự Án.", refs: {} });
      return;
    }
    try {
      const state = await request("/api/transform/status?id=" + encodeURIComponent(job));
      showState(state);
      const isJobRunning = ["queued", "running"].includes(state.status);
      if (isJobRunning) {
        timer = setTimeout(check, 2800);
      } else {
        refreshStudioQueue().catch(() => { });
        if (typeof refreshAll === "function") {
          refreshAll(true).catch(() => { });
        }
      }
    } catch (error) {
      const box = find("#tfStatus");
      if (box) { box.textContent = error.message; box.className = "ts-status-box error"; }
    }
  }

  async function start() {
    if (submitting) return;
    submitting = true;
    const startBtn = find("#tfStart");
    if (startBtn) {
      startBtn.disabled = true;
      startBtn.textContent = "⏳ Đang gửi sang Studio...";
    }
    try {
      const tpl = data?.template || {};
      const payload = {
        template_code: tpl.code || activeTemplateCode || "006",
        preset: find("#tfPreset")?.value || "",
        image_provider: find("#tfProvider")?.value || "banana",
        video_model: find("#tfVideoModel")?.value || "Omni 1.1 Flash",
        music: Boolean(find("#tfMusic")?.checked)
      };

      if (tpl.supports_character !== false) {
        if (charMode === "upload") {
          const cf = find("#tfCharacter")?.files?.[0];
          if (!cf) throw new Error("Hãy tải lên ảnh nhân vật hoặc chuyển sang Thư viện / AI tự tạo.");
          payload.character_upload = await fileData(cf);
        } else if (charMode === "library") {
          const cKey = find("#tfCharSelect")?.value;
          if (!cKey || cKey === "__upload__") throw new Error("Chọn 1 nhân vật trong thư viện.");
          payload.character_key = cKey;
        }
      }

      if (tpl.supports_product !== false) {
        if (prodMode === "library") {
          payload.product_id = find("#tfProduct")?.value;
          payload.image_index = Number(find("#tfImage")?.value || 0);
          if (!payload.product_id) throw new Error("Hãy chọn 1 sản phẩm từ kho.");
          const matchedProd = (library || []).find((x) => x.id === payload.product_id);
          if (matchedProd?.title) payload.product_label = matchedProd.title;
        } else {
          const pf = find("#tfUpload")?.files?.[0];
          if (!pf) throw new Error("Hãy tải lên ảnh sản phẩm / trang phục trước khi tạo video.");
          payload.product_label = pf.name || "";
          payload.product_upload = await fileData(pf);
        }
      }

      const res = await request("/api/transform/start", payload);
      job = res.id;
      localStorage.setItem("template006Job", job);

      // Ngay lập tức chuyển dự án mới sang Studio Dự Án & mở khóa nút để tạo tiếp video khác
      pushProjectToStudio(res.project, res.id, { activateTab: true });
      showState({
        status: "running",
        message: "✅ Đã đưa dự án sang Studio Dự Án! Đang chạy ngầm đa luồng — bạn có thể đổi SP/kịch bản và bấm Tạo tiếp ngay.",
        refs: {}
      });
      if (typeof toast === "function") {
        toast("🚀 Đã chuyển dự án sang Studio Dự Án! Bạn có thể tiếp tục dùng Template này để tạo thêm video mới.", "ok");
      }
      refreshStudioQueue().catch(() => { });
      check().catch(() => { });
    } catch (error) {
      const box = find("#tfStatus");
      if (box) { box.textContent = error.message; box.className = "ts-status-box error"; }
    } finally {
      submitting = false;
      if (startBtn) {
        startBtn.disabled = false;
        startBtn.textContent = "✨ Tạo Video 16s Ngay";
      }
    }
  }

  function wireDropzone(zoneSel, inputSel, onFile) {
    const zone = find(zoneSel);
    const input = find(inputSel);
    if (!zone || !input) return;
    zone.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      input.click();
    });
    zone.addEventListener("dragover", (e) => {
      e.preventDefault();
      zone.classList.add("dragover");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("dragover");
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      onFile();
    });
  }

  function mount() {
    injectStyles();
    const root = document.createElement("div");
    root.id = MODAL_ID;
    root.className = "modal-backdrop";
    root.innerHTML = `
      <div class="modal-box ts-dialog" role="dialog" aria-modal="true" aria-labelledby="tfTitle">
        <div class="ts-header">
          <div class="ts-head-left">
            <span class="ts-code-pill" id="tfCodePill">TEMPLATE #006</span>
            <div class="ts-head-titles">
              <div class="ts-title" id="tfTitle">Biến hình thời trang</div>
              <div class="ts-subtitle" id="tfSubtitle">Studio 2 cảnh 8s + Khớp nhạc chuyển cảnh mượt</div>
            </div>
          </div>
          <div class="ts-head-actions">
            <select id="tfTemplateSelect" class="ts-tpl-select" aria-label="Chuyển đổi Template Studio" hidden></select>
            <button class="btn btn-outline ts-close-btn" id="tfClose" type="button" aria-label="Đóng">✕</button>
          </div>
        </div>

        <div class="ts-workspace">
          <div class="ts-col-left">
            <div class="ts-section">
              <div class="ts-sec-head">
                <div class="ts-sec-title"><span class="ts-step-num">1</span><span>Chọn kịch bản biến hình</span></div>
                <div class="ts-spec-chips">
                  <span class="ts-spec-chip">9:16 Dọc</span>
                  <span class="ts-spec-chip">16 Giây (2×8s)</span>
                  <span class="ts-spec-chip">Ép đen &amp; Bung nhạc</span>
                </div>
              </div>
              <select id="tfPreset" hidden></select>
              <div class="ts-preset-grid" id="tfPresetGrid"></div>
              <div id="tfSummary" style="display:none"></div>
              <div class="ts-audio-bar">
                <label class="ts-switch">
                  <input id="tfMusic" type="checkbox" checked>
                  <span class="ts-switch-track"></span>
                  <span>Ghép âm thanh &amp; khớp nhịp drop nhạc từ video mẫu</span>
                </label>
              </div>
            </div>

            <div class="ts-section">
              <div class="ts-sec-head">
                <div class="ts-sec-title"><span class="ts-step-num">2</span><span>Nhân vật tham chiếu &amp; Sản phẩm đầu vào</span></div>
              </div>
              <div class="ts-inputs-grid">
                <div class="ts-asset-card ts-asset-char" id="tfCharCard">
                  <div class="ts-asset-head">
                    <span class="ts-asset-title" id="tfCharHeading">Nhân vật tham chiếu</span>
                    <span class="ts-asset-tag ts-tag-cyan">Giữ khuôn mặt 2 cảnh</span>
                  </div>
                  <div class="ts-seg">
                    <button type="button" class="ts-seg-btn" data-char-mode="library">🧑 Thư viện</button>
                    <button type="button" class="ts-seg-btn" data-char-mode="upload">📤 Tải lên</button>
                    <button type="button" class="ts-seg-btn" data-char-mode="auto">✨ AI tự tạo</button>
                  </div>
                  <select id="tfCharSelect" hidden></select>
                  <div id="tfCharLibPane">
                    <div class="ts-gallery-strip" id="tfCharGrid"></div>
                  </div>
                  <div id="tfCharUploadPane" hidden>
                    <input id="tfCharacter" type="file" accept="image/jpeg,image/png,image/webp" style="display:none">
                    <div class="ts-dropzone" id="tfCharDropzone">
                      <div class="ts-dz-empty" id="tfCharDzEmpty">
                        <div class="ts-dz-icon">🧑</div>
                        <div style="font-size:12px;font-weight:700;color:#e2e8f0">Nhấn hoặc kéo thả ảnh Nhân vật</div>
                        <div style="font-size:11px">Hỗ trợ ảnh chân dung &amp; Character Sheet</div>
                      </div>
                      <div class="ts-dz-filled" id="tfCharDzFilled" hidden>
                        <img id="tfCharPreview" class="ts-dz-thumb" alt="Xem trước nhân vật">
                        <div class="ts-dz-meta">
                          <div class="ts-dz-fname" id="tfCharFileName"></div>
                          <div style="font-size:11px;color:#94a3b8" id="tfCharFileMeta"></div>
                          <div class="ts-dz-actions">
                            <button type="button" class="ts-mini-btn" id="tfCharSwap">Đổi ảnh</button>
                            <button type="button" class="ts-mini-btn" id="tfCharClear">✕ Xoá</button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div id="tfCharAutoPane" hidden style="padding:20px 10px;text-align:center;color:#94a3b8;font-size:12px;border:1px dashed rgba(6,182,212,0.28);border-radius:10px">
                    Hệ thống sẽ tự sinh gương mặt diễn viên phù hợp với bối cảnh kịch bản.
                  </div>
                  <small id="tfCharCaption" style="font-size:11px;color:#67e8f9"></small>
                </div>

                <div class="ts-asset-card ts-asset-prod" id="tfProdCard">
                  <div class="ts-asset-head">
                    <span class="ts-asset-title" id="tfProdHeading">Sản phẩm / Trang phục</span>
                    <span class="ts-asset-tag ts-tag-amber">Tách nền trắng 2K</span>
                  </div>
                  <select id="tfSource" hidden>
                    <option value="upload">Tải từ máy</option>
                    <option value="library">Kho sản phẩm</option>
                  </select>
                  <div class="ts-seg">
                    <button type="button" class="ts-seg-btn active" data-prod-mode="upload">📤 Tải từ máy</button>
                    <button type="button" class="ts-seg-btn" data-prod-mode="library">🏬 Kho sản phẩm</button>
                  </div>
                  <div id="tfUploadRow">
                    <input id="tfUpload" type="file" accept="image/jpeg,image/png,image/webp" style="display:none">
                    <div class="ts-dropzone" id="tfProdDropzone">
                      <div class="ts-dz-empty" id="tfProdDzEmpty">
                        <div class="ts-dz-icon">👗</div>
                        <div style="font-size:12px;font-weight:700;color:#e2e8f0">Nhấn hoặc kéo thả ảnh Sản phẩm</div>
                        <div style="font-size:11px">Chấp nhận ảnh rời hoặc ảnh mẫu đang mặc</div>
                      </div>
                      <div class="ts-dz-filled" id="tfProdDzFilled" hidden>
                        <img id="tfUploadPreview" class="ts-dz-thumb" alt="Xem trước sản phẩm">
                        <div class="ts-dz-meta">
                          <div class="ts-dz-fname" id="tfProdFileName"></div>
                          <div style="font-size:11px;color:#94a3b8" id="tfProdFileMeta"></div>
                          <div class="ts-dz-actions">
                            <button type="button" class="ts-mini-btn" id="tfProdSwap">Đổi ảnh</button>
                            <button type="button" class="ts-mini-btn" id="tfProdClear">✕ Xoá</button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div id="tfLibrary" hidden style="display:flex;flex-direction:column;gap:8px">
                    <input id="tfSearch" type="search" aria-label="Tìm sản phẩm" placeholder="🔍 Tìm tên hoặc mã sản phẩm..." style="padding:7px 10px;border-radius:8px;font-size:12px">
                    <select id="tfProduct" hidden></select>
                    <div class="ts-gallery-strip" id="tfProductGrid" style="max-height:118px"></div>
                    <div style="display:flex;align-items:center;gap:8px">
                      <select id="tfImage" aria-label="Góc ảnh sản phẩm" style="font-size:12px;padding:6px 8px"></select>
                      <img id="tfPreview" alt="Ảnh sản phẩm đã chọn" hidden style="width:42px;height:54px;object-fit:cover;border-radius:6px;border:1px solid rgba(245,158,11,0.5)">
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="ts-section">
              <div class="ts-sec-head">
                <div class="ts-sec-title"><span class="ts-step-num">3</span><span>Model AI tạo ảnh tham chiếu 2K &amp; Prompt Timeline</span></div>
              </div>
              <select id="tfProvider" hidden>
                <option value="banana">Nano Banana 2.1 (Flow)</option>
                <option value="chatgpt">ChatGPT Image (gpt-image-2)</option>
                <option value="cliproxy_gemini">Gemini Image (CLIProxy :8317)</option>
              </select>
              <div class="ts-provider-row" id="tfProviderPills">
                <button type="button" class="ts-prov-pill active" data-prov="banana">
                  <strong>🍌 Nano Banana 2.1</strong><span>Chạy trực tiếp Google Flow</span>
                </button>
                <button type="button" class="ts-prov-pill" data-prov="chatgpt">
                  <strong>🎨 ChatGPT Image</strong><span>GPT-Image-2 · Sắc nét</span>
                </button>
                <button type="button" class="ts-prov-pill" data-prov="cliproxy_gemini">
                  <strong>✨ Gemini 3.1 Flash</strong><span>Qua CLIProxy :8317</span>
                </button>
              </div>
              <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:8px;margin-bottom:6px;font-size:12px">
                <label for="tfVideoModel" style="font-weight:700;color:#cbd5e1;white-space:nowrap">🎬 Model tạo Video 2×8s:</label>
                <select id="tfVideoModel" aria-label="Model tạo video" style="font-size:12px;padding:6px 10px;border-radius:8px;background:#0f172a;color:#f8fafc;border:1px solid rgba(148,163,184,0.28);flex:1;max-width:290px">
                  <option value="Omni 1.1 Flash" selected>⚡ Omni 1.1 Flash (Google Flow · Khuyên dùng)</option>
                  <option value="Omni 1.2 Flash">⚡ Omni 1.2 Flash (Google Flow)</option>
                  <option value="Veo 3.1 - Fast">Veo 3.1 - Fast</option>
                  <option value="Veo 3.1 - Quality">Veo 3.1 - Quality</option>
                </select>
              </div>
              <details style="font-size:12px;color:#94a3b8">
                <summary style="cursor:pointer;font-weight:700;color:#cbd5e1;padding:4px 0">Xem cấu trúc Prompt &amp; Timeline chuẩn từng cảnh</summary>
                <pre id="tfPrompts" style="white-space:pre-wrap;margin-top:8px;padding:10px;border-radius:9px;background:#090e1a;border:1px solid rgba(148,163,184,0.14);font-size:11px;line-height:1.5;max-height:200px;overflow-y:auto"></pre>
              </details>
            </div>
          </div>

          <div class="ts-col-right">
            <div class="ts-monitor-card">
              <div class="ts-seg">
                <button type="button" class="ts-seg-btn active" data-mon-tab="demo">🎬 Video Mẫu</button>
                <button type="button" class="ts-seg-btn" data-mon-tab="final">✨ Video Kết Quả</button>
              </div>
              <div class="ts-phone-frame">
                <video id="tfDemo" controls playsinline preload="metadata" aria-label="Video tham khảo"></video>
                <div id="tfDemoEmpty" class="ts-phone-empty" hidden>Template này chưa kèm file video mẫu, hoặc chưa tìm thấy video demo.</div>
                <video id="tfFinal" controls playsinline hidden aria-label="Video thành phẩm"></video>
                <div id="tfFinalEmpty" class="ts-phone-empty" hidden>Nhấn <b>Tạo Video 16s Ngay</b> để AI render 2 cảnh 8s và ghép chuyển cảnh mượt vào đây.</div>
              </div>
              <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
                <a class="btn btn-amber" id="tfDownload" download="template_006.mp4" hidden style="font-size:12px;padding:7px 14px;text-decoration:none">⬇️ Tải Video Final</a>
                <button type="button" class="btn btn-outline" id="tfOpenProj" hidden style="font-size:12px;padding:7px 12px">📂 Mở Dự Án</button>
              </div>

              <div class="ts-stepper" id="tfStepper">
                <div class="ts-step-item"><div class="ts-step-bar"></div><span>1. Tách SP</span></div>
                <div class="ts-step-item"><div class="ts-step-bar"></div><span>2. Cảnh 1</span></div>
                <div class="ts-step-item"><div class="ts-step-bar"></div><span>3. Cảnh 2</span></div>
                <div class="ts-step-item"><div class="ts-step-bar"></div><span>4. Video 2×8s</span></div>
                <div class="ts-step-item"><div class="ts-step-bar"></div><span>5. Nhạc &amp; Cut</span></div>
              </div>

              <div id="tfStatus" class="ts-status-box" role="status" aria-live="polite">Sẵn sàng tạo nhiều video 16s song song — bấm Tạo để đẩy sang Studio Dự Án.</div>
              <div id="tfRefs" class="ts-refs-grid"></div>
              <div id="tfStudioQueue" class="ts-queue-panel" hidden></div>
            </div>
          </div>
        </div>

        <div class="ts-footer">
          <div class="ts-ready-note" id="tfReadiness">Chọn kịch bản và ảnh đầu vào</div>
          <div class="ts-footer-btns">
            <button type="button" class="btn btn-outline" id="tfViewStudio" hidden style="font-size:12.5px">📺 Mở Studio Dự Án</button>
            <button type="button" class="btn btn-outline" id="tfCancelBtn">Đóng</button>
            <button type="button" class="ts-cta-btn" id="tfStart">✨ Tạo Video 16s Ngay</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(root);

    const handleClose = () => {
      clearTimeout(timer);
      clearTimeout(queueTimer);
      find("#tfDemo")?.pause();
      find("#tfFinal")?.pause();
      closeModal(MODAL_ID);
    };
    find("#tfClose").onclick = handleClose;
    find("#tfCancelBtn").onclick = handleClose;
    root.onclick = (e) => { if (e.target === root) handleClose(); };

    find("#tfTemplateSelect").onchange = async (e) => {
      await loadStudioTemplate(e.target.value);
    };
    find("#tfPreset").onchange = () => { renderPresetCards(); presetChanged(); updateReadinessHint(); };

    findAll("[data-char-mode]").forEach((btn) => {
      btn.onclick = () => setCharacterMode(btn.dataset.charMode);
    });
    findAll("[data-prod-mode]").forEach((btn) => {
      btn.onclick = () => setProductMode(btn.dataset.prodMode);
    });
    findAll("[data-mon-tab]").forEach((btn) => {
      btn.onclick = () => switchMonitorTab(btn.dataset.monTab);
    });
    findAll("[data-prov]").forEach((btn) => {
      btn.onclick = () => {
        findAll("[data-prov]").forEach((b) => b.classList.toggle("active", b === btn));
        find("#tfProvider").value = btn.dataset.prov;
      };
    });

    wireDropzone("#tfCharDropzone", "#tfCharacter", () => {
      setCharacterMode("upload");
      renderCharacterPreview();
      updateReadinessHint();
    });
    wireDropzone("#tfProdDropzone", "#tfUpload", renderProductUploadPreview);

    find("#tfCharacter").onchange = () => {
      if (find("#tfCharacter").files[0]) setCharacterMode("upload");
      renderCharacterPreview();
      updateReadinessHint();
    };
    find("#tfCharSwap").onclick = () => find("#tfCharacter").click();
    find("#tfCharClear").onclick = () => {
      find("#tfCharacter").value = "";
      renderCharacterPreview();
      updateReadinessHint();
    };

    find("#tfUpload").onchange = renderProductUploadPreview;
    find("#tfProdSwap").onclick = () => find("#tfUpload").click();
    find("#tfProdClear").onclick = () => {
      find("#tfUpload").value = "";
      renderProductUploadPreview();
    };

    find("#tfSearch").oninput = filterProducts;
    find("#tfProduct").onchange = libraryImages;
    find("#tfImage").onchange = libraryPreview;
    find("#tfStart").onclick = start;
    find("#tfOpenProj").onclick = () => openProjectInStudio(job);
    const viewStudioBtn = find("#tfViewStudio");
    if (viewStudioBtn) viewStudioBtn.onclick = () => openProjectInStudio(job);
  }

  async function loadStudioTemplate(tplCode = "") {
    const query = tplCode ? ("?template=" + encodeURIComponent(tplCode)) : "";
    data = await request("/api/transform/default" + query);
    renderTemplateHeader();
    renderPresetCards();
    presetChanged();
    switchMonitorTab("demo");
    populateCharacters();
    updateReadinessHint();
  }

  window.openTransformStudio = async (existing = "", templateCode = "") => {
    let resolvedCode = String(templateCode || "").trim();
    if (existing && !resolvedCode) {
      try {
        const st = await request("/api/transform/status?id=" + encodeURIComponent(existing));
        if (st?.template_code) resolvedCode = st.template_code;
      } catch (_) { }
    }
    if (!document.getElementById(MODAL_ID)) {
      mount();
    }
    await loadStudioTemplate(resolvedCode);
    if (existing) {
      job = existing;
      localStorage.setItem("template006Job", job);
    } else {
      job = "";
      localStorage.removeItem("template006Job");
    }
    openModal(MODAL_ID);
    await check();
    refreshStudioQueue().catch(() => { });
  };
})();
