// ═══════════════════════════════════════════════════════════════════════════
// ⚡ LÊ VIỆT TÙNG — SKILLAUTOVEO WORKFLOW STUDIO PRO (THUẦN VIỆT + MUSEFLOW + GOOGLE FLOW)
// Hệ thống Sơ đồ Nối dây Trực quan: Hỗ trợ Node Video, Xem Full (Văn bản/Ảnh 2K/Video),
// Menu Chuột phải 3 Ngữ cảnh (Node / Dây nối / Bàn cờ), Alt+Kéo Nhân bản,
// Kịch bản Đa cảnh ➔ Node, Thứ tự chạy, và Thanh Timeline Ghép Cảnh Xuất MP4.
// ═══════════════════════════════════════════════════════════════════════════

const WF_NODE_CATALOG = [
  {
    type: "image",
    badge: "ẢNH REF",
    title: "🖼️ Ảnh Đầu Vào (Nhân Vật / Sản Phẩm 2K)",
    icon: "🖼️",
    iconColor: "#818cf8",
    desc: "Tải ảnh từ máy tính hoặc chọn từ Thư viện Nhân vật (NV1–NV5) / Kho 176 Sản phẩm làm ảnh tham chiếu.",
    defaultLabel: "Ảnh Tham Chiếu",
  },
  {
    type: "video",
    badge: "VIDEO REF",
    title: "🎬 Video Đầu Vào (Video Mẫu Chuyển Động / Clip)",
    icon: "🎬",
    iconColor: "#f472b6",
    desc: "Thêm video có sẵn (.mp4/.mov/.webm) làm mẫu chuyển động (Motion Ref), tách Frame cuối nối cảnh hoặc ghép vào Timeline.",
    defaultLabel: "Video Tham Chiếu",
  },
  {
    type: "references",
    badge: "BỘ ẢNH REF",
    title: "🗂️ Gom Nhóm Ảnh Tham Chiếu (References Pack)",
    icon: "🗂️",
    iconColor: "#a78bfa",
    desc: "Gom nhiều ảnh tham chiếu (Nhân vật + Quần áo + Phụ kiện + Bối cảnh, tối đa 6 ảnh) truyền sang các Node tạo Ảnh/Video.",
    defaultLabel: "Bộ Ảnh Tham Chiếu",
  },
  {
    type: "prompt",
    badge: "PROMPT AI",
    title: "📝 Prompt / Kịch Bản AI (ChatGPT / Gemini CLIProxy)",
    icon: "📝",
    iconColor: "#38bdf8",
    desc: "Soạn câu lệnh Prompt hoặc nhờ ChatGPT/Gemini (CLIProxy :8317) tự viết kịch bản, phân tích ảnh Vision, dịch Anh–Việt.",
    defaultLabel: "Prompt Chính",
  },
  {
    type: "negativePrompt",
    badge: "PROMPT ÂM",
    title: "🚫 Prompt Âm (Negative Prompt — Tránh Lỗi AI)",
    icon: "🚫",
    iconColor: "#f87171",
    desc: "Liệt kê những chi tiết muốn AI tránh (biến dạng tay, sai logo, mờ nhoè, chữ rác) khi nối vào Node tạo Ảnh/Video.",
    defaultLabel: "Tránh Lỗi (Negative)",
  },
  {
    type: "text",
    badge: "VĂN BẢN",
    title: "📄 Văn Bản Tĩnh (Khoá Nhân Vật / Bối Cảnh @slug)",
    icon: "📄",
    iconColor: "#94a3b8",
    desc: "Khối văn bản cố định dùng để khoá Style, khoá Nhân vật ([CHAR LOCK]) hoặc chèn tự động qua biến @slug.",
    defaultLabel: "Khoá Nhân Vật / Style",
  },
  {
    type: "textAppend",
    badge: "NỐI CHỮ",
    title: "➕ Nối Đuôi Văn Bản (Text Append)",
    icon: "➕",
    iconColor: "#2dd4bf",
    desc: "Nối thêm hậu tố (góc máy, ánh sáng, thông số 2K 8s) vào sau văn bản truyền từ Node phía trước.",
    defaultLabel: "Nối Thêm Hậu Tố",
  },
  {
    type: "textConcat",
    badge: "GỘP CHỮ",
    title: "🔀 Gộp Nhiều Văn Bản (Text Merge — Nhiều Nhánh)",
    icon: "🔀",
    iconColor: "#34d399",
    desc: "Gộp nhiều dây văn bản (Khoá Style + Khoá Nhân Vật + Hành Động Cảnh) thành 1 Prompt hoàn chỉnh duy nhất.",
    defaultLabel: "Gộp Văn Bản Đa Nhánh",
  },
  {
    type: "text_extract",
    badge: "TÁCH CHỮ",
    title: "✂️ Tách Văn Bản Tự Động (Text Extract / Regex / JSON)",
    icon: "✂️",
    iconColor: "#fbbf24",
    desc: "Tách một đoạn văn bản từ đầu ra AI theo từ khoá đánh dấu, trường JSON hoặc biểu thức Regex.",
    defaultLabel: "Tách Văn Bản",
  },
  {
    type: "generate",
    badge: "GOOGLE FLOW",
    title: "✦ Tạo Ảnh 2K / Video Google Flow (Nano Banana / Omni / Veo 3.1)",
    icon: "✦",
    iconColor: "#a3e635",
    desc: "Render Ảnh 2K (Nano Banana 2.1 / Pro) hoặc Video 1080p (Omni 1.1 Flash / Veo 3.1) trực tiếp trên Google Flow.",
    defaultLabel: "Google Flow - Tạo Ảnh 2K",
  },
  {
    type: "gpt_image",
    badge: "CHATGPT",
    title: "🤖 Tạo Ảnh ChatGPT (CLIProxy GPT-Image-1)",
    icon: "🤖",
    iconColor: "#10b981",
    desc: "Tạo ảnh thương mại / tách nền sản phẩm phẳng (Flat-lay) qua ChatGPT Image (CLIProxy :8317).",
    defaultLabel: "ChatGPT - Tạo Ảnh",
  },
  {
    type: "grok_generate",
    badge: "GROK AI",
    title: "⚡ Tạo Ảnh / Video Grok (CLIProxy Grok Imagine)",
    icon: "⚡",
    iconColor: "#f59e0b",
    desc: "Tạo ảnh hoặc video qua Grok (grok-imagine-image / grok-imagine-video trên CLIProxy).",
    defaultLabel: "Grok - Tạo Ảnh/Video",
  },
  {
    type: "gemini_generate",
    badge: "GEMINI",
    title: "💎 Tạo Ảnh / Video Gemini (CLIProxy / Flow)",
    icon: "💎",
    iconColor: "#c084fc",
    desc: "Tạo ảnh/video thông qua hệ thống Gemini đa phương thức.",
    defaultLabel: "Gemini - Tạo Ảnh/Video",
  },
  {
    type: "preview",
    badge: "XEM TRƯỚC",
    title: "👁️ Khung Xem Trước Full (Preview Node)",
    icon: "👁️",
    iconColor: "#60a5fa",
    desc: "Nhận bất kỳ dây Văn bản, Ảnh 2K hoặc Video nào để hiển thị và kiểm tra trực tiếp trên bàn cờ.",
    defaultLabel: "Khung Xem Trước",
  },
  {
    type: "auto_download",
    badge: "TẢI VỀ",
    title: "⬇️ Tự Động Lưu Kết Quả (Auto Download)",
    icon: "⬇️",
    iconColor: "#38bdf8",
    desc: "Tự động sao lưu file Ảnh 2K / Video MP4 từ Node phía trước vào thư mục final_videos.",
    defaultLabel: "Tự Động Lưu File",
  },
  {
    type: "note",
    badge: "GHI CHÚ",
    title: "📌 Ghi Chú Trên Sơ Đồ (Note Card)",
    icon: "📌",
    iconColor: "#fde047",
    desc: "Thẻ ghi chú hướng dẫn hoặc chú thích ngay trên bàn cờ (không chạy AI).",
    defaultLabel: "Ghi Chú",
  },
];

const WF_STATE = {
  initialized: false,
  workflowsList: [],
  currentWfId: "",
  doc: null,
  selectedNodeId: null,
  selectedNodeIds: new Set(),
  inspectorTab: "config",
  tool: "select", // 'select' | 'pan' | 'group'
  zoom: 0.68,
  panX: 360,
  panY: 380,
  isPanning: false,
  panStartX: 0,
  panStartY: 0,
  origPanX: 0,
  origPanY: 0,
  draggingNodeId: null,
  nodeDragStartX: 0,
  nodeDragStartY: 0,
  nodeOrigPositions: {}, // { nodeId: { x, y } }
  altDragDuplicated: false,
  draggingGroupId: null,
  groupDragStartX: 0,
  groupDragStartY: 0,
  groupOrigPos: null,
  draggingNoteId: null,
  noteDragStartX: 0,
  noteDragStartY: 0,
  noteOrigPos: null,
  drawingGroup: null, // { startX, startY, curX, curY }
  marquee: null, // { startClientX, startClientY, curClientX, curClientY }
  connectingFrom: null, // { nodeId, handle: 'output_1', startX, startY, curX, curY }
  pendingConnectSource: null, // { nodeId, handle } when dropping wire on empty space
  contextMenuCanvasPos: { x: 200, y: 0 },
  addNodeIndex: 0,
  history: [],
  historyIdx: -1,
  pollTimer: null,
  mediaPickerTargetNodeId: null,
  fullViewerNodeId: null,
  runOrderItems: [],
  characters: [],
};

function _wfEscHtml(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function _getWfBody() {
  if (!WF_STATE.doc) {
    WF_STATE.doc = {
      version: "1.0",
      type: "workflow",
      exported_at: new Date().toISOString(),
      _wf_id: "wf_custom_new",
      workflow: {
        name: "Sơ Đồ Workflow Mới",
        description: "",
        settings: { max_parallel: 2, max_retries: 2, retry_delay_ms: 5000, run_count: 0 },
        nodes: [],
        edges: [],
        groups: [],
        notes: [],
        timeline: [],
      },
    };
  }
  if (!WF_STATE.doc.workflow) {
    WF_STATE.doc = {
      version: "1.0",
      type: "workflow",
      exported_at: new Date().toISOString(),
      _wf_id: WF_STATE.doc._wf_id || "wf_custom_new",
      workflow: WF_STATE.doc,
    };
  }
  const wf = WF_STATE.doc.workflow;
  if (!Array.isArray(wf.nodes)) wf.nodes = [];
  if (!Array.isArray(wf.edges)) wf.edges = [];
  if (!Array.isArray(wf.groups)) wf.groups = [];
  if (!Array.isArray(wf.notes)) wf.notes = [];
  if (!Array.isArray(wf.timeline)) wf.timeline = [];
  if (!wf.settings) wf.settings = { max_parallel: 2, max_retries: 2, retry_delay_ms: 5000, run_count: 0 };
  return wf;
}

function wfPushHistory() {
  const wf = _getWfBody();
  const snap = JSON.stringify({
    nodes: wf.nodes,
    edges: wf.edges,
    groups: wf.groups,
    notes: wf.notes,
    timeline: wf.timeline,
  });
  if (WF_STATE.historyIdx >= 0 && WF_STATE.history[WF_STATE.historyIdx] === snap) return;
  WF_STATE.history = WF_STATE.history.slice(0, WF_STATE.historyIdx + 1);
  WF_STATE.history.push(snap);
  if (WF_STATE.history.length > 40) WF_STATE.history.shift();
  WF_STATE.historyIdx = WF_STATE.history.length - 1;
}

function wfUndo() {
  if (WF_STATE.historyIdx <= 0) return;
  WF_STATE.historyIdx -= 1;
  const snap = JSON.parse(WF_STATE.history[WF_STATE.historyIdx]);
  const wf = _getWfBody();
  wf.nodes = snap.nodes || [];
  wf.edges = snap.edges || [];
  wf.groups = snap.groups || [];
  wf.notes = snap.notes || [];
  wf.timeline = snap.timeline || [];
  renderWorkflowCanvas();
  renderWfInspector();
  renderWfTimelineDock();
}

function wfRedo() {
  if (WF_STATE.historyIdx >= WF_STATE.history.length - 1) return;
  WF_STATE.historyIdx += 1;
  const snap = JSON.parse(WF_STATE.history[WF_STATE.historyIdx]);
  const wf = _getWfBody();
  wf.nodes = snap.nodes || [];
  wf.edges = snap.edges || [];
  wf.groups = snap.groups || [];
  wf.notes = snap.notes || [];
  wf.timeline = snap.timeline || [];
  renderWorkflowCanvas();
  renderWfInspector();
  renderWfTimelineDock();
}

async function initOrRefreshWorkflowTab() {
  if (!WF_STATE.initialized) {
    setupWorkflowCanvasInteractions();
    WF_STATE.initialized = true;
  }
  await loadWorkflowsListFromServer(false);
}

async function loadWorkflowsListFromServer(keepCurrent = false) {
  try {
    const res = await apiGet("/api/workflows/list");
    if (res && res.ok) {
      WF_STATE.workflowsList = res.workflows || [];
      if (Array.isArray(res.characters) && res.characters.length) {
        WF_STATE.characters = res.characters;
      }
      const sel = document.getElementById("selWorkflowDoc");
      if (sel) {
        sel.innerHTML = WF_STATE.workflowsList.map(doc => {
          const id = doc._wf_id || "";
          const name = (doc.workflow && doc.workflow.name) || id;
          const nCount = ((doc.workflow && doc.workflow.nodes) || []).length;
          return `<option value="${_wfEscHtml(id)}">${_wfEscHtml(name)} (${nCount} Node)</option>`;
        }).join("");
      }

      let targetDoc = null;
      if (keepCurrent && WF_STATE.currentWfId) {
        targetDoc = WF_STATE.workflowsList.find(d => d._wf_id === WF_STATE.currentWfId);
      }
      if (!targetDoc && WF_STATE.workflowsList.length > 0) {
        targetDoc = WF_STATE.workflowsList.find(d => d._wf_id === "wf_elevator_mirror_outfit_check") || WF_STATE.workflowsList[0];
      }
      if (targetDoc) {
        loadWorkflowDocumentIntoCanvas(targetDoc, !keepCurrent);
      }
    }
  } catch (e) {
    console.error("loadWorkflowsListFromServer error:", e);
  }
}

function onSelectWorkflowDoc(wfId) {
  const found = (WF_STATE.workflowsList || []).find(d => d._wf_id === wfId);
  if (found) {
    loadWorkflowDocumentIntoCanvas(found, true);
  }
}

function loadWorkflowDocumentIntoCanvas(docObj, autoFit = true) {
  WF_STATE.doc = JSON.parse(JSON.stringify(docObj));
  WF_STATE.currentWfId = WF_STATE.doc._wf_id || "wf_custom";
  const wf = _getWfBody();

  const sel = document.getElementById("selWorkflowDoc");
  if (sel && sel.value !== WF_STATE.currentWfId) sel.value = WF_STATE.currentWfId;

  const titleInp = document.getElementById("inpWorkflowTitle");
  if (titleInp) titleInp.value = wf.name || "Sơ Đồ Workflow";

  WF_STATE.history = [];
  WF_STATE.historyIdx = -1;
  wfPushHistory();

  const firstGen = wf.nodes.find(n => n.node_type === "generate") || wf.nodes[0];
  WF_STATE.selectedNodeId = firstGen ? firstGen.id : null;
  WF_STATE.selectedNodeIds = new Set(WF_STATE.selectedNodeId ? [WF_STATE.selectedNodeId] : []);

  renderWorkflowCanvas();
  renderWfInspector();
  renderWfTimelineDock();
  if (autoFit) {
    setTimeout(() => fitWorkflowCanvasView(), 50);
  }
}

function _applyWfStageTransform() {
  const stage = document.getElementById("wfTransformStage");
  if (stage) {
    stage.style.transform = `translate(${WF_STATE.panX}px, ${WF_STATE.panY}px) scale(${WF_STATE.zoom})`;
  }
  const lbl = document.getElementById("wfZoomPctLabel");
  if (lbl) lbl.textContent = `${Math.round(WF_STATE.zoom * 100)}%`;
  const vp = document.getElementById("wfViewport");
  if (vp) {
    const bgSize = Math.max(12, Math.round(24 * WF_STATE.zoom));
    const majorSize = bgSize * 5;
    vp.style.backgroundSize = `${bgSize}px ${bgSize}px, ${majorSize}px ${majorSize}px, ${majorSize}px ${majorSize}px`;
    vp.style.backgroundPosition = `${Math.round(WF_STATE.panX)}px ${Math.round(WF_STATE.panY)}px`;
  }
}

function zoomWfCanvas(delta, clientX = null, clientY = null) {
  const vp = document.getElementById("wfViewport");
  if (!vp) return;
  const rect = vp.getBoundingClientRect();
  const cx = clientX !== null ? (clientX - rect.left) : (rect.width / 2);
  const cy = clientY !== null ? (clientY - rect.top) : (rect.height / 2);

  const oldZoom = WF_STATE.zoom;
  const newZoom = Math.min(2.2, Math.max(0.22, +(oldZoom + delta).toFixed(3)));
  if (newZoom === oldZoom) return;

  const worldX = (cx - WF_STATE.panX) / oldZoom;
  const worldY = (cy - WF_STATE.panY) / oldZoom;
  WF_STATE.zoom = newZoom;
  WF_STATE.panX = cx - worldX * newZoom;
  WF_STATE.panY = cy - worldY * newZoom;
  _applyWfStageTransform();
}

function resetWfCanvasZoom() {
  WF_STATE.zoom = 1.0;
  _applyWfStageTransform();
}

function fitWorkflowCanvasView() {
  const vp = document.getElementById("wfViewport");
  const wf = _getWfBody();
  if (!vp || !wf.nodes.length) {
    WF_STATE.zoom = 0.75;
    WF_STATE.panX = 320;
    WF_STATE.panY = 300;
    _applyWfStageTransform();
    return;
  }
  const rect = vp.getBoundingClientRect();
  const vw = Math.max(500, rect.width - 110);
  const vh = Math.max(380, rect.height - 90);

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  wf.nodes.forEach(n => {
    const x = Number(n.pos_x || 0);
    const y = Number(n.pos_y || 0);
    const w = 285;
    const h = 360;
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x + w > maxX) maxX = x + w;
    if (y + h > maxY) maxY = y + h;
  });

  const bw = Math.max(340, maxX - minX + 160);
  const bh = Math.max(340, maxY - minY + 160);
  const zoom = Math.min(1.0, Math.max(0.30, Math.min(vw / bw, vh / bh)));
  WF_STATE.zoom = +zoom.toFixed(3);
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  WF_STATE.panX = Math.round(rect.width / 2 - centerX * WF_STATE.zoom + 24);
  WF_STATE.panY = Math.round(rect.height / 2 - centerY * WF_STATE.zoom);
  _applyWfStageTransform();
}

function autoLayoutWorkflowNodes() {
  const wf = _getWfBody();
  if (!wf.nodes.length) return;
  wfPushHistory();

  const inDegree = {};
  const adj = {};
  wf.nodes.forEach(n => {
    inDegree[n.id] = 0;
    adj[n.id] = [];
  });
  wf.edges.forEach(e => {
    if (adj[e.source_node_id] && inDegree[e.target_node_id] !== undefined) {
      adj[e.source_node_id].push(e.target_node_id);
      inDegree[e.target_node_id] += 1;
    }
  });

  const levelMap = {};
  let queue = wf.nodes.filter(n => inDegree[n.id] === 0).map(n => n.id);
  queue.forEach(id => { levelMap[id] = 0; });

  while (queue.length > 0) {
    const cur = queue.shift();
    const curLv = levelMap[cur] || 0;
    (adj[cur] || []).forEach(nxt => {
      levelMap[nxt] = Math.max(levelMap[nxt] || 0, curLv + 1);
      inDegree[nxt] -= 1;
      if (inDegree[nxt] <= 0) queue.push(nxt);
    });
  }

  const cols = {};
  wf.nodes.forEach(n => {
    const lv = levelMap[n.id] !== undefined ? levelMap[n.id] : 0;
    if (!cols[lv]) cols[lv] = [];
    cols[lv].push(n);
  });

  Object.keys(cols).sort((a, b) => Number(a) - Number(b)).forEach(lvKey => {
    const lv = Number(lvKey);
    const list = cols[lvKey];
    list.forEach((n, idx) => {
      n.pos_x = 120 + lv * 355;
      n.pos_y = -240 + idx * 390;
    });
  });

  renderWorkflowCanvas();
  fitWorkflowCanvasView();
  if (typeof toast === "function") toast("📐 Đã tự động sắp xếp sơ đồ Node thẳng hàng!", "ok");
}

function _getMediaUrlForWfPath(p) {
  if (!p) return "";
  const s = String(p).trim();
  if (!s) return "";
  if (s.startsWith("/api/media") || s.startsWith("http://") || s.startsWith("https://") || s.startsWith("data:")) return s;
  return `/api/media?path=${encodeURIComponent(s)}`;
}

function _isVideoFile(p) {
  if (!p) return false;
  return /\.(mp4|mov|webm|mkv)(\?|$)/i.test(String(p));
}

// ── TÍNH TOÁN NỘI DUNG VĂN BẢN / PROMPT ĐÃ GỘP TỪ CÁC NODE PHÍA TRƯỚC (GIỐNG MUSEFLOW) ──
function resolveWfNodeMergedText(nodeId, visited = new Set()) {
  if (!nodeId || visited.has(nodeId)) return "";
  visited.add(nodeId);
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return "";
  const cfg = node.config || {};
  const ntype = (node.node_type || "").toLowerCase();

  // Tìm các dây nối văn bản đi vào node này
  const inEdges = wf.edges.filter(e => e.target_node_id === nodeId);
  const upstreamTexts = [];
  const negativeTexts = [];

  inEdges.forEach(e => {
    const upNode = wf.nodes.find(x => x.id === e.source_node_id);
    if (!upNode) return;
    const upType = (upNode.node_type || "").toLowerCase();
    const isTextEdge = e.target_handle === "input_2" || e.edge_type === "text" || ["prompt", "negativeprompt", "text", "textappend", "textconcat", "text_extract"].includes(upType);
    if (!isTextEdge) return;
    const t = resolveWfNodeMergedText(upNode.id, new Set(visited)).trim();
    if (!t) return;
    if (upType === "negativeprompt") negativeTexts.push(t);
    else upstreamTexts.push(t);
  });

  const ownRaw = String(cfg.result_text || cfg.prompt || cfg.text || cfg.note || "").trim();
  let combined = "";

  if (ntype === "textconcat") {
    const sep = cfg.separator !== undefined ? String(cfg.separator) : "\n\n";
    const parts = [...upstreamTexts];
    if (ownRaw) parts.push(ownRaw);
    combined = parts.filter(Boolean).join(sep);
  } else if (ntype === "textappend") {
    const base = upstreamTexts.join("\n").trim();
    const suffix = String(cfg.suffix || ownRaw || "").trim();
    const sep = cfg.separator !== undefined ? String(cfg.separator) : ", ";
    combined = [base, suffix].filter(Boolean).join(sep);
  } else if (["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(ntype)) {
    if (cfg.use_own_prompt && ownRaw) {
      combined = ownRaw;
    } else if (upstreamTexts.length > 0) {
      combined = upstreamTexts.join("\n\n");
      if (ownRaw && cfg.append_own_prompt) combined += "\n" + ownRaw;
    } else {
      combined = ownRaw;
    }
  } else {
    combined = ownRaw || upstreamTexts.join("\n\n");
  }

  // Thay thế biến @slug nếu có trong văn bản
  if (combined && combined.includes("@")) {
    wf.nodes.forEach(other => {
      const slug = other.config && other.config.slug;
      if (slug && combined.includes(`@${slug}`)) {
        const val = String(other.config.result_text || other.config.prompt || other.config.text || other.config.file_path || "").trim();
        if (val) {
          combined = combined.split(`@${slug}`).join(val);
        }
      }
    });
  }

  if (negativeTexts.length > 0) {
    combined = `${combined}\n\n[NEGATIVE PROMPT / TRÁNH LỖI]: ${negativeTexts.join(", ")}`.trim();
  }
  return combined;
}

function resolveWfNodeUpstreamMedia(nodeId) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return [];
  const cfg = node.config || {};
  const list = [];
  if (cfg.result_path) list.push(cfg.result_path);
  if (cfg.file_path && !list.includes(cfg.file_path)) list.push(cfg.file_path);
  if (Array.isArray(cfg.reference_images)) {
    cfg.reference_images.forEach(p => { if (p && !list.includes(p)) list.push(p); });
  }
  wf.edges.filter(e => e.target_node_id === nodeId).forEach(e => {
    const up = wf.nodes.find(x => x.id === e.source_node_id);
    if (!up || !up.config) return;
    const upP = up.config.result_path || up.config.file_path;
    if (upP && !list.includes(upP)) list.push(upP);
    if (Array.isArray(up.config.reference_images)) {
      up.config.reference_images.forEach(p => { if (p && !list.includes(p)) list.push(p); });
    }
  });
  return list;
}

// ── RENDER KHUNG NHÓM (GROUPS) & GHI CHÚ DÁN (STICKY NOTES) TRÊN BÀN CỜ ──
function renderWfGroupsAndNotes() {
  const wf = _getWfBody();
  const groupsLayer = document.getElementById("wfGroupsLayer");
  const notesLayer = document.getElementById("wfNotesLayer");

  if (groupsLayer) {
    let gHtml = (wf.groups || []).map(g => {
      const col = g.color || "#6366f1";
      return `
      <div class="wf-group-box" id="wfGroupEl_${g.id}"
           style="left:${Number(g.x || 0)}px; top:${Number(g.y || 0)}px; width:${Math.max(200, Number(g.width || 420))}px; height:${Math.max(160, Number(g.height || 320))}px; border-color:${col}88; background:${col}12;">
        <div class="wf-group-header"
             style="background:${col}33; border-bottom-color:${col}55;"
             onmousedown="onWfGroupMouseDown(event, '${g.id}')"
             oncontextmenu="onWfGroupContextMenu(event, '${g.id}')"
             ondblclick="event.stopPropagation(); renameWfGroupPrompt('${g.id}')">
          <span>📦 ${_wfEscHtml(g.title || 'Khung Nhóm Cảnh')}</span>
          <div style="display:flex; gap:4px;" onmousedown="event.stopPropagation()">
            <button class="wf-node-mini-btn" onclick="event.stopPropagation(); runWfGroupNodes('${g.id}')" title="▶ Chạy tất cả Node trong Nhóm này">▶</button>
            <button class="wf-node-mini-btn" onclick="event.stopPropagation(); cycleWfGroupColor('${g.id}')" title="🎨 Đổi màu Khung Nhóm">🎨</button>
            <button class="wf-node-mini-btn" onclick="event.stopPropagation(); renameWfGroupPrompt('${g.id}')" title="✏️ Đổi tên Nhóm">✏️</button>
            <button class="wf-node-mini-btn danger" onclick="event.stopPropagation(); deleteWfGroup('${g.id}')" title="🗑️ Xoá Khung Nhóm">✕</button>
          </div>
        </div>
      </div>
    `}).join("");

    if (WF_STATE.drawingGroup) {
      const dg = WF_STATE.drawingGroup;
      const gx = Math.min(dg.startX, dg.curX);
      const gy = Math.min(dg.startY, dg.curY);
      const gw = Math.max(40, Math.abs(dg.curX - dg.startX));
      const gh = Math.max(40, Math.abs(dg.curY - dg.startY));
      gHtml += `<div class="wf-group-box" style="left:${gx}px; top:${gy}px; width:${gw}px; height:${gh}px; border-color:#a3e635; background:rgba(163,230,53,0.08); pointer-events:none;"></div>`;
    }
    groupsLayer.innerHTML = gHtml;
  }

  if (notesLayer) {
    notesLayer.innerHTML = (wf.notes || []).map(nt => `
      <div class="wf-sticky-note" id="wfNoteEl_${nt.id}"
           style="left:${Number(nt.x || 0)}px; top:${Number(nt.y || 0)}px;">
        <div class="wf-sticky-head" onmousedown="onWfStickyNoteMouseDown(event, '${nt.id}')">
          <span>📌 ${_wfEscHtml(nt.title || 'Ghi Chú Nhanh')}</span>
          <button class="wf-node-mini-btn danger" style="width:18px; height:18px;" onclick="event.stopPropagation(); deleteWfStickyNote('${nt.id}')" title="Xoá ghi chú">✕</button>
        </div>
        <div class="wf-sticky-body">
          <textarea placeholder="Nhập ghi chú..." oninput="onWfStickyNoteTextInput('${nt.id}', this.value)" onmousedown="event.stopPropagation()">${_wfEscHtml(nt.text || '')}</textarea>
        </div>
      </div>
    `).join("");
  }
}

// ── RENDER TOÀN BỘ THẺ NODE TRÊN CANVAS (THUẦN VIỆT + ĐIỀU KHIỂN TRỰC TIẾP + XEM FULL) ──
function renderWorkflowCanvas() {
  const wf = _getWfBody();
  const nodesLayer = document.getElementById("wfNodesLayer");
  const edgesSvg = document.getElementById("wfEdgesSvg");
  if (!nodesLayer || !edgesSvg) return;

  const runsEl = document.getElementById("wfRunsStatText");
  if (runsEl) runsEl.textContent = `${(wf.settings && wf.settings.run_count) || 0}`;
  const nodesEl = document.getElementById("wfNodesStatText");
  if (nodesEl) nodesEl.textContent = `${wf.nodes.length} Node`;
  const speedBadge = document.getElementById("wfSpeedBadge");
  if (speedBadge) speedBadge.textContent = `x${(wf.settings && wf.settings.max_parallel) || 2} Đa luồng ⚡`;

  renderWfGroupsAndNotes();

  nodesLayer.innerHTML = wf.nodes.map(n => {
    if (!n.config) n.config = {};
    const cfg = n.config;
    const ntype = (n.node_type || "generate").toLowerCase();
    const isGen = ["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(ntype);
    const isMedia = ["image", "video", "references", "preview"].includes(ntype);
    const isTextLike = ["prompt", "negativeprompt", "text", "textappend", "textconcat", "text_extract", "note"].includes(ntype);
    const isSelected = WF_STATE.selectedNodeId === n.id || WF_STATE.selectedNodeIds.has(n.id);

    const st = (cfg.status || (cfg.result_path || cfg.file_path ? "done" : "idle")).toLowerCase();
    const dotClass = st === "running" ? "running" : (st === "error" ? "error" : (st === "done" ? "" : "idle"));
    const catMeta = WF_NODE_CATALOG.find(c => c.type.toLowerCase() === ntype) || { icon: "✦", badge: ntype.toUpperCase() };

    const mediaPath = cfg.result_path || cfg.file_path || ((cfg.reference_images || [])[0]) || (ntype === "preview" ? (resolveWfNodeUpstreamMedia(n.id)[0] || "") : "");
    const mediaUrl = _getMediaUrlForWfPath(mediaPath);
    const isVid = (cfg.mode === "video") || ntype === "video" || _isVideoFile(mediaPath);
    const isLandscape = (cfg.aspect_ratio === "16:9");

    // Tính số nhánh văn bản hoặc ảnh đang nối vào node này
    const inEdges = wf.edges.filter(e => e.target_node_id === n.id);
    const inTextCount = inEdges.filter(e => e.target_handle === "input_2" || e.edge_type === "text").length;
    const inMediaCount = inEdges.filter(e => e.target_handle !== "input_2" && e.edge_type !== "text").length;

    let bodyHtml = "";

    // 1. NODE ẢNH / VIDEO ĐẦU VÀO / GOM ẢNH REF / PREVIEW
    if (isMedia) {
      const refCount = Array.isArray(cfg.reference_images) ? cfg.reference_images.length : 0;
      const previewText = ntype === "preview" ? resolveWfNodeMergedText(n.id) : "";
      bodyHtml = `
        <div class="wf-node-media-box ${isLandscape ? 'landscape' : ''}"
             ondblclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')">
          ${mediaUrl ? (isVid ? `
            <video src="${mediaUrl}" controls muted loop playsinline preload="metadata" style="width:100%; height:100%; object-fit:cover;"></video>
          ` : `
            <img src="${mediaUrl}" alt="${_wfEscHtml(n.label || '')}" loading="lazy" />
          `) : (previewText ? `
            <div style="padding:10px; font-size:11px; color:#e2e8f0; overflow-y:auto; max-height:100%; width:100%; white-space:pre-wrap;">${_wfEscHtml(previewText.slice(0, 320))}</div>
          ` : `
            <div style="text-align:center; padding:14px; color:#64748b; font-size:11px; cursor:pointer;" onclick="event.stopPropagation(); pickFileForWfNode('${n.id}')">
              <div style="font-size:28px; margin-bottom:6px;">${ntype === 'video' ? '🎬' : (ntype === 'references' ? '🗂️' : '🖼️')}</div>
              <div style="font-weight:700; color:#cbd5e1;">${ntype === 'video' ? 'Bấm chọn Video (.mp4/.mov)' : 'Bấm chọn Ảnh 2K / Video'}</div>
              <div style="font-size:10px; margin-top:3px;">Hoặc chọn từ Kho Nhân vật / SP</div>
            </div>
          `)}

          <div class="wf-node-media-overlay">
            <div style="display:flex; justify-content:space-between; gap:4px;">
              <span style="background:rgba(0,0,0,0.75); color:#f8fafc; font-size:9.5px; font-weight:800; padding:2px 6px; border-radius:4px;">
                ${isVid ? '🎬 VIDEO' : '🖼️ ẢNH'} ${refCount > 1 ? `(+${refCount} ảnh)` : ''}
              </span>
              ${mediaPath ? `<button class="btn btn-xs btn-amber" style="font-size:9.5px; padding:2px 7px; font-weight:800;" onclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')">🔍 Xem Full</button>` : ''}
            </div>
            <div style="display:flex; justify-content:space-between; gap:4px; flex-wrap:wrap;">
              <button class="btn btn-xs" style="background:rgba(9,13,22,0.88); color:#e2e8f0; border:1px solid rgba(255,255,255,0.2); font-size:9.5px; padding:3px 7px;" onclick="event.stopPropagation(); pickFileForWfNode('${n.id}', ${ntype === 'references'})">📂 Chọn File</button>
              <button class="btn btn-xs" style="background:rgba(99,102,241,0.92); color:#fff; border:none; font-size:9.5px; padding:3px 7px;" onclick="event.stopPropagation(); openWfMediaLibraryPicker('${n.id}')">📚 Kho NV/SP</button>
              ${isVid && mediaPath ? `<button class="btn btn-xs" style="background:rgba(244,114,182,0.92); color:#050811; font-weight:800; border:none; font-size:9.5px; padding:3px 7px;" onclick="event.stopPropagation(); extractWfVideoEndFrameToNode('${n.id}')" title="Tách Frame cuối của Video này thành Node Ảnh mới">📸 Frame Cuối</button>` : ''}
            </div>
          </div>
        </div>

        <div class="wf-node-action-bar">
          <button class="wf-node-btn-full" onclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')" title="Mở xem toàn màn hình (Ảnh 2K / Video / Chi tiết)">🔍 Xem Full</button>
          <button class="wf-node-btn-run" style="background:rgba(99,102,241,0.18); border-color:rgba(99,102,241,0.45); color:#c7d2fe;" onclick="event.stopPropagation(); pickFileForWfNode('${n.id}', ${ntype === 'references'})">📂 Đổi File</button>
          ${isVid && mediaPath ? `<button class="wf-node-btn-run" onclick="event.stopPropagation(); addWfNodeVideoToTimeline('${n.id}')" title="Đưa video này xuống Thanh Timeline Ghép Cảnh">🎞️ +Timeline</button>` : ''}
        </div>
      `;
    }
    // 2. NODE TẠO ẢNH 2K / TẠO VIDEO AI (GOOGLE FLOW / CHATGPT / GROK / GEMINI)
    else if (isGen) {
      const modeIcon = isVid ? "🎬" : "🖼️";
      const mergedPrompt = resolveWfNodeMergedText(n.id);
      bodyHtml = `
        <div class="wf-node-media-box ${isLandscape ? 'landscape' : ''}"
             ondblclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')">
          ${mediaUrl ? (isVid ? `
            <video src="${mediaUrl}" controls muted loop playsinline preload="metadata" style="width:100%; height:100%; object-fit:cover;"></video>
          ` : `
            <img src="${mediaUrl}" alt="${_wfEscHtml(n.label || '')}" loading="lazy" />
          `) : `
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; color:#64748b; padding:12px; text-align:center;">
              <span style="font-size:26px; opacity:0.8;">${modeIcon}</span>
              <span style="font-size:11px; font-weight:700; color:#cbd5e1;">${isVid ? 'Sẵn sàng Render Video AI' : 'Sẵn sàng Render Ảnh 2K'}</span>
              <span style="font-size:9.5px; color:#94a3b8;">🔗 ${inMediaCount} Ảnh/Video Ref • 📝 ${inTextCount} Prompt nối vào</span>
              ${st === "running" ? `<span style="font-size:10.5px; color:#f59e0b; font-weight:800;">⏳ Đang tạo trên AI...</span>` : ""}
              ${st === "error" && cfg.error ? `<span style="font-size:9.5px; color:#f87171; padding:0 6px;">❌ ${_wfEscHtml(cfg.error.slice(0, 90))}</span>` : ""}
            </div>
          `}
          ${mediaUrl ? `
            <div class="wf-node-media-overlay">
              <div style="display:flex; justify-content:space-between;">
                <span style="background:rgba(16,185,129,0.9); color:#052e16; font-size:9.5px; font-weight:900; padding:2px 6px; border-radius:4px;">✅ ĐÃ TẠO XONG</span>
                <button class="btn btn-xs btn-amber" style="font-size:9.5px; padding:2px 7px; font-weight:800;" onclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')">🔍 Xem Full</button>
              </div>
              <div style="display:flex; justify-content:space-between; gap:4px;">
                ${isVid ? `<button class="btn btn-xs btn-success" style="font-size:9.5px; padding:2px 6px;" onclick="event.stopPropagation(); addWfNodeVideoToTimeline('${n.id}')">🎞️ +Timeline</button>` : ''}
                ${isVid ? `<button class="btn btn-xs" style="background:#f472b6; color:#050811; font-weight:800; border:none; font-size:9.5px; padding:2px 6px;" onclick="event.stopPropagation(); extractWfVideoEndFrameToNode('${n.id}')">📸 Frame Cuối</button>` : ''}
                <button class="btn btn-xs btn-outline" style="background:rgba(0,0,0,0.8); font-size:9.5px; padding:2px 6px;" onclick="event.stopPropagation(); spawnNewMediaNodeFromResult('${encodeURIComponent(mediaPath)}', '${isVid ? 'video' : 'image'}')">➕ Tách Ra Node</button>
              </div>
            </div>
          ` : ''}
        </div>

        <!-- Điều khiển trực tiếp ngay trên thẻ Node Generate -->
        <div class="wf-node-inline-controls" onmousedown="event.stopPropagation()">
          <select class="wf-node-inline-select" onchange="onWfNodeInlineModeChange('${n.id}', this.value)" title="Chọn chế độ Tạo Ảnh 2K hoặc Tạo Video">
            <option value="image" ${!isVid ? 'selected' : ''}>🖼️ Ảnh 2K</option>
            <option value="video" ${isVid ? 'selected' : ''}>🎬 Video</option>
          </select>
          <select class="wf-node-inline-select" onchange="onWfNodeInlineConfigChange('${n.id}', 'aspect_ratio', this.value)" title="Tỷ lệ khung hình">
            <option value="9:16" ${(cfg.aspect_ratio || '9:16') === '9:16' ? 'selected' : ''}>📱 9:16</option>
            <option value="16:9" ${cfg.aspect_ratio === '16:9' ? 'selected' : ''}>🖥 16:9</option>
            <option value="1:1" ${cfg.aspect_ratio === '1:1' ? 'selected' : ''}>⬛ 1:1</option>
          </select>
          ${isVid ? `
            <select class="wf-node-inline-select" onchange="onWfNodeInlineConfigChange('${n.id}', 'duration', this.value)" title="Thời lượng Video">
              <option value="8s" ${(cfg.duration || '8s') === '8s' ? 'selected' : ''}>⏱ 8s</option>
              <option value="10s" ${cfg.duration === '10s' ? 'selected' : ''}>⏱ 10s</option>
              <option value="15s" ${cfg.duration === '15s' ? 'selected' : ''}>⏱ 15s</option>
            </select>
          ` : ''}
        </div>

        ${(cfg.use_own_prompt || inTextCount === 0) ? `
          <textarea class="wf-node-inline-textarea" style="min-height:54px;"
                    placeholder="Nhập Prompt trực tiếp hoặc nối dây từ Node Prompt vào cổng 📝..."
                    onmousedown="event.stopPropagation()"
                    oninput="onWfNodeInlinePromptInput('${n.id}', this.value)">${_wfEscHtml(cfg.prompt || '')}</textarea>
        ` : `
          <div style="font-size:10px; color:#94a3b8; background:#080b12; border:1px solid rgba(56,189,248,0.22); border-radius:7px; padding:5px 7px; max-height:48px; overflow:hidden; cursor:pointer;"
               onclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')"
               title="Nhấp để Xem Full Prompt đã gộp từ các dây nối">
            🔗 <b style="color:#38bdf8;">Prompt nối vào:</b> ${_wfEscHtml(mergedPrompt.slice(0, 95))}${mergedPrompt.length > 95 ? '...' : ''}
          </div>
        `}

        <div class="wf-node-action-bar">
          <button class="wf-node-btn-full" onclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')" title="Xem Full Ảnh 2K / Video / Toàn bộ Prompt đã gộp">🔍 Xem Full</button>
          ${isVid && mediaPath ? `<button class="wf-node-btn-run" style="background:rgba(168,85,247,0.2); border-color:rgba(168,85,247,0.5); color:#e9d5ff;" onclick="event.stopPropagation(); addWfNodeVideoToTimeline('${n.id}')">🎞️ +Timeline</button>` : ''}
          <button class="wf-node-btn-run" onclick="event.stopPropagation(); runWorkflowExecution('${n.id}')" title="Chạy riêng Node này">▶ Chạy</button>
        </div>
      `;
    }
    // 3. NODE VĂN BẢN / PROMPT / GỘP CHỮ / GHI CHÚ (CHO PHÉP GÕ TRỰC TIẾP & XEM FULL)
    else if (isTextLike) {
      const rawTxt = cfg.prompt || cfg.text || cfg.note || cfg.suffix || "";
      const mergedTxt = resolveWfNodeMergedText(n.id);
      bodyHtml = `
        <textarea class="wf-node-inline-textarea"
                  placeholder="${ntype === 'textconcat' ? 'Ghi chú thêm (Node này sẽ tự động gộp tất cả các dây văn bản nối vào)...' : 'Nhập nội dung văn bản / Prompt trực tiếp tại đây...'}"
                  onmousedown="event.stopPropagation()"
                  oninput="onWfNodeInlinePromptInput('${n.id}', this.value)">${_wfEscHtml(rawTxt)}</textarea>

        ${(ntype === "textconcat" || ntype === "textappend" || inTextCount > 0) ? `
          <div style="font-size:10px; color:#a7f3d0; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); border-radius:6px; padding:4px 7px; display:flex; justify-content:space-between; align-items:center;">
            <span>🔗 Đang gộp <b>${inTextCount}</b> nhánh (${mergedTxt.length} ký tự)</span>
            <span style="text-decoration:underline; cursor:pointer;" onclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')">Xem gộp</span>
          </div>
        ` : ''}

        <div class="wf-node-action-bar">
          <button class="wf-node-btn-full" onclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')" title="Mở cửa sổ lớn Xem Full & Chỉnh sửa toàn bộ văn bản / Prompt đã gộp">🔍 Xem Full Chữ</button>
          ${ntype === "prompt" ? `<button class="wf-node-btn-run" onclick="event.stopPropagation(); testRunPromptNodeWithAi('${n.id}')" title="Nhờ AI ChatGPT/Gemini viết hoặc hoàn thiện Prompt">🪄 AI Viết</button>` : ''}
          <button class="wf-node-btn-run" style="background:rgba(255,255,255,0.06); border-color:rgba(255,255,255,0.15); color:#cbd5e1;" onclick="event.stopPropagation(); navigator.clipboard.writeText(resolveWfNodeMergedText('${n.id}')); if(typeof toast==='function') toast('📋 Đã copy toàn bộ nội dung Node!','ok');" title="Copy toàn bộ nội dung">📋 Copy</button>
        </div>
      `;
    } else {
      bodyHtml = `
        <div class="wf-node-action-bar">
          <button class="wf-node-btn-full" onclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')">🔍 Xem Full</button>
          <button class="wf-node-btn-run" onclick="event.stopPropagation(); runWorkflowExecution('${n.id}')">▶ Chạy</button>
        </div>
      `;
    }

    const showMediaInPort = !["text", "negativeprompt", "textappend", "textconcat", "note"].includes(ntype);
    const showTextInPort = !["image", "video", "references", "note"].includes(ntype);
    const showOutPort = ntype !== "note";

    const modelBadge = isGen
      ? `${cfg.model || 'Nano Banana 2.1'} • ${cfg.aspect_ratio || '9:16'}`
      : (ntype === "prompt" ? (cfg.ai_enabled ? `🤖 ${cfg.model || 'ChatGPT/Gemini'}` : "📝 Prompt") : (cfg.slug ? `@${cfg.slug}` : catMeta.badge));

    const typeCls = isGen ? "wf-node-generate" : (ntype === "video" ? "wf-node-video" : (ntype === "image" ? "wf-node-image" : (ntype === "prompt" ? "wf-node-prompt" : "")));

    return `
      <div class="wf-node-card ${typeCls} ${isSelected ? 'selected' : ''} ${cfg.disabled ? 'is-disabled' : ''} status-${st}"
           id="wfNodeEl_${n.id}"
           data-node-id="${n.id}"
           style="left:${Number(n.pos_x || 0)}px; top:${Number(n.pos_y || 0)}px;"
           onmousedown="onWfNodeMouseDown(event, '${n.id}')"
           onclick="onWfNodeClick(event, '${n.id}')"
           oncontextmenu="onWfNodeContextMenu(event, '${n.id}')">

        ${showMediaInPort ? `
          <div class="wf-port wf-port-in-media"
               data-node-id="${n.id}" data-handle="input_1" data-dir="in"
               title="Cổng nhận Ảnh / Video tham chiếu (input_1) — Kéo dây từ Node Ảnh/Video thả vào đây"
               onmousedown="event.stopPropagation(); onWfPortClick('${n.id}', 'input_1', 'in', event)"
               onmouseup="event.stopPropagation(); onWfPortMouseUp('${n.id}', 'input_1', 'in', event)">
            🖼️
            <span class="wf-port-label">🖼️ Ảnh / Video Ref</span>
          </div>
        ` : ''}

        ${showTextInPort ? `
          <div class="wf-port wf-port-in-text"
               data-node-id="${n.id}" data-handle="input_2" data-dir="in"
               title="Cổng nhận Văn bản / Prompt (input_2) — Kéo dây từ Node Prompt / Văn bản thả vào đây"
               onmousedown="event.stopPropagation(); onWfPortClick('${n.id}', 'input_2', 'in', event)"
               onmouseup="event.stopPropagation(); onWfPortMouseUp('${n.id}', 'input_2', 'in', event)">
            📝
            <span class="wf-port-label">📝 Prompt / Văn bản</span>
          </div>
        ` : ''}

        ${showOutPort ? `
          <div class="wf-port wf-port-out"
               data-node-id="${n.id}" data-handle="output_1" data-dir="out"
               title="Cổng xuất dữ liệu (output_1) — Giữ chuột kéo sang Node tiếp theo hoặc thả ra vùng trống để tạo nhanh Node mới!"
               onmousedown="event.stopPropagation(); onWfPortOutMouseDown('${n.id}', 'output_1', event)">
            ⚡
            <span class="wf-port-label">⚡ Kết quả ra (Kéo nối dây)</span>
          </div>
        ` : ''}

        <div class="wf-node-head" ondblclick="event.stopPropagation(); renameWfNodePrompt('${n.id}')">
          <div class="wf-node-title-wrap">
            <span style="font-size:12px;">${catMeta.icon || '✦'}</span>
            <span class="wf-node-type-badge">${_wfEscHtml(catMeta.badge || ntype)}</span>
            <span class="wf-node-title" title="${_wfEscHtml(n.label || n.id)} (Nhấp đúp tiêu đề để đổi tên)">${_wfEscHtml(n.label || n.id)}</span>
          </div>
          <div class="wf-node-head-actions" onmousedown="event.stopPropagation()">
            <button class="wf-node-mini-btn" onclick="event.stopPropagation(); openWfNodeFullViewer('${n.id}')" title="🔍 Xem Full nội dung Node này">🔍</button>
            <button class="wf-node-mini-btn" onclick="event.stopPropagation(); duplicateWfNodeById('${n.id}')" title="📋 Sao chép / Nhân bản Node này">📋</button>
            <button class="wf-node-mini-btn" onclick="event.stopPropagation(); runWorkflowExecution('${n.id}')" title="▶ Chạy riêng Node này">▶</button>
            <button class="wf-node-mini-btn danger" onclick="event.stopPropagation(); deleteWfNodeById('${n.id}')" title="🗑️ Xoá Node này">✕</button>
            <span class="wf-node-status-dot ${dotClass}" title="Trạng thái: ${st}"></span>
          </div>
        </div>

        <div class="wf-node-body">
          ${bodyHtml}
        </div>

        <div class="wf-node-foot">
          <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${_wfEscHtml(modelBadge)}</span>
          <span style="color:#64748b; font-family:Consolas,monospace;">${cfg.slug ? `@${_wfEscHtml(cfg.slug)}` : ''}</span>
        </div>
      </div>
    `;
  }).join("");

  _applyWfStageTransform();
  renderWorkflowEdgesSvg();
  if (typeof updateWfMultiSelectToolbar === "function") updateWfMultiSelectToolbar();
}

function _getNodePortCoords(node, handle) {
  const x = Number(node.pos_x || 0);
  const y = Number(node.pos_y || 0);
  const ntype = (node.node_type || "generate").toLowerCase();
  const isGen = ["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(ntype);
  const el = document.getElementById(`wfNodeEl_${node.id}`);
  const w = (el && el.offsetWidth > 40) ? el.offsetWidth : (isGen ? 285 : 265);
  const h = (el && el.offsetHeight > 40) ? el.offsetHeight : (isGen ? 390 : 260);

  if (handle === "output_1" || handle === "out") {
    return { x: x + w, y: y + h * 0.52 };
  }
  if (handle === "input_2") {
    return { x: x, y: y + h * 0.68 };
  }
  return { x: x, y: y + h * 0.38 };
}

function _buildBezierPathD(x1, y1, x2, y2) {
  const dx = Math.max(70, Math.abs(x2 - x1) * 0.48);
  const cx1 = x1 + dx;
  const cy1 = y1;
  const cx2 = x2 - dx;
  const cy2 = y2;
  return `M ${x1.toFixed(1)} ${y1.toFixed(1)} C ${cx1.toFixed(1)} ${cy1.toFixed(1)}, ${cx2.toFixed(1)} ${cy2.toFixed(1)}, ${x2.toFixed(1)} ${y2.toFixed(1)}`;
}

function renderWorkflowEdgesSvg() {
  const wf = _getWfBody();
  const svg = document.getElementById("wfEdgesSvg");
  if (!svg) return;

  const nodeMap = {};
  wf.nodes.forEach(n => { nodeMap[n.id] = n; });

  let pathsHtml = "";
  wf.edges.forEach((e, idx) => {
    const srcNode = nodeMap[e.source_node_id];
    const dstNode = nodeMap[e.target_node_id];
    if (!srcNode || !dstNode) return;
    const p1 = _getNodePortCoords(srcNode, e.source_handle || "output_1");
    const p2 = _getNodePortCoords(dstNode, e.target_handle || "input_1");
    const d = _buildBezierPathD(p1.x, p1.y, p2.x, p2.y);
    const srcType = (srcNode.node_type || "").toLowerCase();
    const isTextEdge = (e.edge_type === "text" || e.target_handle === "input_2");
    const isVideoEdge = !isTextEdge && (srcType === "video" || (srcNode.config && srcNode.config.mode === "video"));
    const edgeTypeClass = isTextEdge ? "edge-text" : (isVideoEdge ? "edge-video" : "edge-image");
    const dstStatus = ((dstNode.config && dstNode.config.status) || "").toLowerCase();
    const runClass = dstStatus === "running" ? "edge-running" : "";
    pathsHtml += `
      <g class="wf-edge-group"
         onclick="event.stopPropagation(); confirmOrRemoveWfEdge(${idx})"
         oncontextmenu="onWfEdgeContextMenu(event, ${idx})">
        <path class="wf-edge-hit" d="${d}" />
        <path class="wf-edge-path ${edgeTypeClass} ${runClass}" d="${d}">
          <title>🔗 Dây nối: ${_wfEscHtml(srcNode.label || srcNode.id)} ➔ ${_wfEscHtml(dstNode.label || dstNode.id)} (Nhấp hoặc Chuột phải để xoá dây)</title>
        </path>
      </g>
    `;
  });

  if (WF_STATE.connectingFrom) {
    const c = WF_STATE.connectingFrom;
    const d = _buildBezierPathD(c.startX, c.startY, c.curX, c.curY);
    pathsHtml += `<path d="${d}" fill="none" stroke="#a3e635" stroke-width="3" stroke-dasharray="7 5" pointer-events="none" />`;
  }

  svg.innerHTML = pathsHtml;
}

// ── CẬP NHẬT TRỰC TIẾP TỪ CÁC Ô INLINE TRÊN THẺ NODE ──
function onWfNodeInlinePromptInput(nodeId, val) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return;
  if (!node.config) node.config = {};
  node.config.prompt = val;
  if (node.node_type === "text") node.config.text = val;
  if (node.node_type === "note") node.config.note = val;
  if (node.node_type === "textAppend") node.config.suffix = val;
  if (WF_STATE.selectedNodeId === nodeId) {
    const inspTxt = document.getElementById("txtWfInspPrompt");
    if (inspTxt && document.activeElement !== inspTxt) inspTxt.value = val;
  }
}

function onWfNodeInlineModeChange(nodeId, newMode) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return;
  if (!node.config) node.config = {};
  wfPushHistory();
  node.config.mode = newMode;
  if (newMode === "video") {
    if (!node.config.model || node.config.model.includes("Banana") || node.config.model.includes("gpt")) {
      node.config.model = "Omni 1.1 Flash";
    }
    if (node.label && node.label.includes("Tạo Ảnh")) {
      node.label = node.label.replace("Tạo Ảnh 2K", "Tạo Video").replace("Tạo Ảnh", "Tạo Video");
    }
  } else {
    if (!node.config.model || node.config.model.includes("Omni") || node.config.model.includes("Veo")) {
      node.config.model = "Nano Banana 2.1";
    }
  }
  renderWorkflowCanvas();
  if (WF_STATE.selectedNodeId === nodeId) renderWfInspector();
}

function onWfNodeInlineConfigChange(nodeId, key, val) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return;
  if (!node.config) node.config = {};
  wfPushHistory();
  node.config[key] = val;
  renderWorkflowCanvas();
  if (WF_STATE.selectedNodeId === nodeId) renderWfInspector();
}

// ── XOÁ, ĐỔI TÊN, NHÂN BẢN (DUPLICATE), NGẮT DÂY NODE ──
function confirmOrRemoveWfEdge(edgeIdx) {
  const wf = _getWfBody();
  if (edgeIdx < 0 || edgeIdx >= wf.edges.length) return;
  wfPushHistory();
  wf.edges.splice(edgeIdx, 1);
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast("🔌 Đã xoá dây nối!", "info");
}

function removeWfEdgeByNodes(sourceId, targetId, targetHandle = null) {
  const wf = _getWfBody();
  wfPushHistory();
  wf.edges = wf.edges.filter(e => {
    if (e.source_node_id === sourceId && e.target_node_id === targetId) {
      if (!targetHandle || e.target_handle === targetHandle) return false;
    }
    return true;
  });
  renderWorkflowCanvas();
  renderWfInspector();
}

function disconnectAllWfNodeEdges(nodeId) {
  const wf = _getWfBody();
  wfPushHistory();
  const before = wf.edges.length;
  wf.edges = wf.edges.filter(e => e.source_node_id !== nodeId && e.target_node_id !== nodeId);
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast(`🔌 Đã ngắt ${before - wf.edges.length} dây nối của Node!`, "info");
}

function renameWfNodePrompt(nodeId) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return;
  const nextName = prompt("✏️ Nhập tên mới cho Node:", node.label || node.id);
  if (nextName !== null && nextName.trim()) {
    wfPushHistory();
    node.label = nextName.trim();
    renderWorkflowCanvas();
    if (WF_STATE.selectedNodeId === nodeId) renderWfInspector();
  }
}

function duplicateWfNodeById(nodeId, offsetX = 50, offsetY = 50) {
  const wf = _getWfBody();
  const orig = wf.nodes.find(n => n.id === nodeId);
  if (!orig) return null;
  wfPushHistory();
  const uid = `n_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 5)}`;
  const copyCfg = JSON.parse(JSON.stringify(orig.config || {}));
  copyCfg.slug = `${(copyCfg.slug || orig.node_type || 'node')}_copy_${wf.nodes.length + 1}`;
  if (["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(orig.node_type)) {
    copyCfg.status = "idle";
  }
  const newNode = {
    id: uid,
    node_type: orig.node_type,
    label: `${orig.label || orig.id} (Bản sao)`,
    pos_x: Number(orig.pos_x || 0) + offsetX,
    pos_y: Number(orig.pos_y || 0) + offsetY,
    config: copyCfg,
  };
  wf.nodes.push(newNode);

  // Sao chép luôn các dây nối đầu vào của Node gốc sang Node bản sao (giống MuseFlow!)
  wf.edges.filter(e => e.target_node_id === nodeId).forEach(inEdge => {
    wf.edges.push({
      source_node_id: inEdge.source_node_id,
      target_node_id: uid,
      source_handle: inEdge.source_handle || "output_1",
      target_handle: inEdge.target_handle || "input_1",
      edge_type: inEdge.edge_type || "image_ref",
    });
  });

  WF_STATE.selectedNodeId = uid;
  WF_STATE.selectedNodeIds = new Set([uid]);
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast(`📋 Đã sao chép Node: ${newNode.label}`, "ok");
  return newNode;
}

function duplicateSelectedWfNode() {
  if (WF_STATE.selectedNodeIds && WF_STATE.selectedNodeIds.size > 1) {
    const ids = Array.from(WF_STATE.selectedNodeIds);
    const newIds = [];
    ids.forEach(id => {
      const copy = duplicateWfNodeById(id, 60, 60);
      if (copy) newIds.push(copy.id);
    });
    WF_STATE.selectedNodeIds = new Set(newIds);
    renderWorkflowCanvas();
    return;
  }
  if (WF_STATE.selectedNodeId) {
    duplicateWfNodeById(WF_STATE.selectedNodeId, 55, 55);
  }
}

function deleteWfNodeById(nodeId) {
  const wf = _getWfBody();
  wfPushHistory();
  wf.nodes = wf.nodes.filter(n => n.id !== nodeId);
  wf.edges = wf.edges.filter(e => e.source_node_id !== nodeId && e.target_node_id !== nodeId);
  WF_STATE.selectedNodeIds.delete(nodeId);
  if (WF_STATE.selectedNodeId === nodeId) {
    WF_STATE.selectedNodeId = wf.nodes[0] ? wf.nodes[0].id : null;
  }
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast("🗑️ Đã xoá Node khỏi sơ đồ!", "info");
}

function deleteSelectedWfNode() {
  const wf = _getWfBody();
  const toDelete = new Set(WF_STATE.selectedNodeIds || []);
  if (WF_STATE.selectedNodeId) toDelete.add(WF_STATE.selectedNodeId);
  if (!toDelete.size) return;
  wfPushHistory();
  wf.nodes = wf.nodes.filter(n => !toDelete.has(n.id));
  wf.edges = wf.edges.filter(e => !toDelete.has(e.source_node_id) && !toDelete.has(e.target_node_id));
  WF_STATE.selectedNodeIds.clear();
  WF_STATE.selectedNodeId = wf.nodes[0] ? wf.nodes[0].id : null;
  renderWorkflowCanvas();
  renderWfInspector();
}


function toggleDisableWfNode(nodeId = null) {
  const wf = _getWfBody();
  const id = nodeId || WF_STATE.selectedNodeId;
  const node = wf.nodes.find(n => n.id === id);
  if (!node) return;
  if (!node.config) node.config = {};
  wfPushHistory();
  node.config.disabled = !node.config.disabled;
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast(node.config.disabled ? "⏻ Đã tạm tắt Node này!" : "✅ Đã bật lại Node!", "info");
}

function resetSelectedWfNode(nodeId = null) {
  const wf = _getWfBody();
  const id = nodeId || WF_STATE.selectedNodeId;
  const node = wf.nodes.find(n => n.id === id);
  if (!node || !node.config) return;
  wfPushHistory();
  node.config.status = "idle";
  node.config.error = "";
  if (["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(node.node_type)) {
    node.config.result_path = "";
    node.config.result_paths = [];
  }
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast("↻ Đã đặt lại trạng thái Node!", "info");
}

// ── TƯƠNG TÁC CHUỘT TRÊN BÀN CỜ, KÉO NODE (ALT+DRAG NHÂN BẢN), KÉO DÂY NỐI ──
function onWfNodeMouseDown(ev, nodeId) {
  if (ev.button !== 0) return;
  ev.stopPropagation();
  hideWfContextMenu();

  const wf = _getWfBody();
  let node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return;

  // Giữ phím Alt + Kéo chuột ➔ Nhân bản Node ngay lập tức (chuẩn MuseFlow!)
  if (ev.altKey) {
    const cloned = duplicateWfNodeById(nodeId, 0, 0);
    if (cloned) {
      node = cloned;
      nodeId = cloned.id;
    }
  } else {
    wfPushHistory();
  }

  if (ev.shiftKey || ev.ctrlKey) {
    if (WF_STATE.selectedNodeIds.has(nodeId)) {
      WF_STATE.selectedNodeIds.delete(nodeId);
    } else {
      WF_STATE.selectedNodeIds.add(nodeId);
    }
    WF_STATE.selectedNodeId = nodeId;
  } else {
    if (!WF_STATE.selectedNodeIds.has(nodeId)) {
      WF_STATE.selectedNodeIds = new Set([nodeId]);
    }
    WF_STATE.selectedNodeId = nodeId;
  }

  document.querySelectorAll(".wf-node-card").forEach(el => {
    const id = el.getAttribute("data-node-id");
    el.classList.toggle("selected", id === WF_STATE.selectedNodeId || WF_STATE.selectedNodeIds.has(id));
  });

  WF_STATE.draggingNodeId = nodeId;
  WF_STATE.dragStartMouseX = ev.clientX;
  WF_STATE.dragStartMouseY = ev.clientY;
  WF_STATE.dragStartNodeX = Number(node.pos_x || 0);
  WF_STATE.dragStartNodeY = Number(node.pos_y || 0);
  WF_STATE.nodeOrigPositions = {};
  wf.nodes.forEach(n => {
    if (n.id === nodeId || WF_STATE.selectedNodeIds.has(n.id)) {
      WF_STATE.nodeOrigPositions[n.id] = { x: Number(n.pos_x || 0), y: Number(n.pos_y || 0) };
    }
  });

  if (typeof updateWfMultiSelectToolbar === "function") updateWfMultiSelectToolbar();
  renderWfInspector();
}

function onWfNodeClick(ev, nodeId) {
  ev.stopPropagation();
  WF_STATE.selectedNodeId = nodeId;
  renderWfInspector();
}

function onWfPortOutMouseDown(nodeId, handle, ev) {
  ev.stopPropagation();
  hideWfContextMenu();
  const wf = _getWfBody();
  const srcNode = wf.nodes.find(n => n.id === nodeId);
  if (!srcNode) return;
  const p = _getNodePortCoords(srcNode, handle);
  WF_STATE.connectingFrom = {
    nodeId,
    handle: handle || "output_1",
    startX: p.x,
    startY: p.y,
    curX: p.x,
    curY: p.y,
  };
}

function onWfPortMouseUp(targetNodeId, targetHandle, dir, ev) {
  ev.stopPropagation();
  if (!WF_STATE.connectingFrom) return;
  const src = WF_STATE.connectingFrom;
  WF_STATE.connectingFrom = null;
  if (src.nodeId === targetNodeId) {
    renderWorkflowEdgesSvg();
    return;
  }
  _createWfEdgeBetween(src.nodeId, src.handle, targetNodeId, targetHandle);
}

function onWfPortClick(nodeId, handle, dir, ev) {
  ev.stopPropagation();
  if (dir === "out") {
    onWfPortOutMouseDown(nodeId, handle, ev);
  } else if (WF_STATE.connectingFrom) {
    onWfPortMouseUp(nodeId, handle, dir, ev);
  }
}

function _createWfEdgeBetween(sourceNodeId, sourceHandle, targetNodeId, targetHandle) {
  const wf = _getWfBody();
  const srcNode = wf.nodes.find(n => n.id === sourceNodeId);
  const dstNode = wf.nodes.find(n => n.id === targetNodeId);
  if (!srcNode || !dstNode || sourceNodeId === targetNodeId) return;

  const srcType = (srcNode.node_type || "").toLowerCase();
  const isTextSrc = ["prompt", "negativeprompt", "text", "textappend", "textconcat", "text_extract"].includes(srcType);

  let finalTargetHandle = targetHandle || (isTextSrc ? "input_2" : "input_1");
  if (isTextSrc && !targetHandle) finalTargetHandle = "input_2";
  const edgeType = (finalTargetHandle === "input_2" || isTextSrc) ? "text" : "image_ref";

  const exists = wf.edges.some(e =>
    e.source_node_id === sourceNodeId &&
    e.target_node_id === targetNodeId &&
    (e.target_handle || "input_1") === finalTargetHandle
  );
  if (!exists) {
    wfPushHistory();
    wf.edges.push({
      source_node_id: sourceNodeId,
      target_node_id: targetNodeId,
      source_handle: sourceHandle || "output_1",
      target_handle: finalTargetHandle,
      edge_type: edgeType,
    });
    if (typeof toast === "function") {
      toast(`🔗 Đã nối dây: ${srcNode.label || srcNode.id} ➔ ${dstNode.label || dstNode.id}`, "ok");
    }
  }
  renderWorkflowCanvas();
  renderWfInspector();
}


// ═══════════════════════════════════════════════════════════════════════════
// PHẦN 2A: CÔNG CỤ BÀN CỜ, QUÉT CHỌN & GỘP NHIỀU NODE (MARQUEE & GROUP),
//          MENU CHUỘT PHẢI 5 NGỮ CẢNH, THÊM NODE & BẢNG CẤU HÌNH INSPECTOR
// ═══════════════════════════════════════════════════════════════════════════

const WF_GROUP_COLORS = ["#6366f1", "#a855f7", "#ec4899", "#10b981", "#f59e0b", "#06b6d4"];

function _screenToCanvasCoords(clientX, clientY) {
  const vp = document.getElementById("wfViewport");
  if (!vp) return { x: 200, y: 0 };
  const rect = vp.getBoundingClientRect();
  return {
    x: Math.round((clientX - rect.left - WF_STATE.panX) / WF_STATE.zoom),
    y: Math.round((clientY - rect.top - WF_STATE.panY) / WF_STATE.zoom),
  };
}

function setWfCanvasTool(toolName) {
  WF_STATE.tool = toolName || "select";
  WF_STATE.toolMode = WF_STATE.tool;
  const bSel = document.getElementById("wfToolSelectBtn");
  const bPan = document.getElementById("wfToolPanBtn");
  const bGrp = document.getElementById("wfToolGroupBtn");
  if (bSel) bSel.classList.toggle("active", WF_STATE.tool === "select");
  if (bPan) bPan.classList.toggle("active", WF_STATE.tool === "pan");
  if (bGrp) bGrp.classList.toggle("active", WF_STATE.tool === "group");
  const vp = document.getElementById("wfViewport");
  if (vp) {
    vp.classList.toggle("grouping", WF_STATE.tool === "group");
    vp.style.cursor = WF_STATE.tool === "pan" ? "grab" : (WF_STATE.tool === "group" ? "crosshair" : "default");
  }
}

function setWfToolMode(toolName) {
  setWfCanvasTool(toolName);
}

function updateWfMultiSelectToolbar() {
  const bar = document.getElementById("wfMultiSelectBar");
  const badge = document.getElementById("wfMultiSelectCountBadge");
  if (!bar) return;
  const count = WF_STATE.selectedNodeIds ? WF_STATE.selectedNodeIds.size : 0;
  if (count >= 2) {
    bar.style.display = "flex";
    if (badge) badge.textContent = `📦 Đã chọn ${count} Node`;
  } else {
    bar.style.display = "none";
  }
}

function clearWfMultiSelection() {
  WF_STATE.selectedNodeIds.clear();
  WF_STATE.selectedNodeId = null;
  document.querySelectorAll(".wf-node-card").forEach(el => el.classList.remove("selected"));
  updateWfMultiSelectToolbar();
  renderWfInspector();
}

function selectAllWfNodes() {
  const wf = _getWfBody();
  WF_STATE.selectedNodeIds = new Set(wf.nodes.map(n => n.id));
  if (wf.nodes[0]) WF_STATE.selectedNodeId = wf.nodes[0].id;
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast(`☑️ Đã chọn toàn bộ ${wf.nodes.length} Node trên bàn cờ!`, "ok");
}

function alignSelectedWfNodes(direction = "horizontal") {
  const wf = _getWfBody();
  const selected = wf.nodes.filter(n => WF_STATE.selectedNodeIds.has(n.id));
  if (selected.length < 2) {
    if (typeof toast === "function") toast("⚠️ Hãy quét chọn ít nhất 2 Node để căn hàng!", "info");
    return;
  }
  wfPushHistory();
  if (direction === "horizontal") {
    selected.sort((a, b) => Number(a.pos_x || 0) - Number(b.pos_x || 0));
    const avgY = Math.round(selected.reduce((s, n) => s + Number(n.pos_y || 0), 0) / selected.length);
    const startX = Number(selected[0].pos_x || 0);
    selected.forEach((n, idx) => {
      n.pos_x = startX + idx * 340;
      n.pos_y = avgY;
    });
  } else {
    selected.sort((a, b) => Number(a.pos_y || 0) - Number(b.pos_y || 0));
    const avgX = Math.round(selected.reduce((s, n) => s + Number(n.pos_x || 0), 0) / selected.length);
    const startY = Number(selected[0].pos_y || 0);
    selected.forEach((n, idx) => {
      n.pos_x = avgX;
      n.pos_y = startY + idx * 380;
    });
  }
  renderWorkflowCanvas();
  if (typeof toast === "function") toast(`📐 Đã căn thẳng hàng ${selected.length} Node đã chọn!`, "ok");
}

// ── GỘP CÁC NODE ĐANG CHỌN THÀNH KHUNG NHÓM (CTRL+G HOẶC NÚT GỘP NHÓM) ──
function groupSelectedWfNodes(customTitle = null) {
  const wf = _getWfBody();
  if (!Array.isArray(wf.groups)) wf.groups = [];
  const selIds = new Set(WF_STATE.selectedNodeIds || []);
  if (WF_STATE.selectedNodeId) selIds.add(WF_STATE.selectedNodeId);
  const selectedNodes = wf.nodes.filter(n => selIds.has(n.id));

  if (!selectedNodes.length) {
    setWfCanvasTool("group");
    if (typeof toast === "function") {
      toast("▱ Hãy giữ chuột trái kéo trên bàn cờ để vẽ Khung Nhóm (hoặc quét chọn các Node trước rồi bấm Gộp Nhóm)!", "info");
    }
    return null;
  }

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  selectedNodes.forEach(n => {
    const x = Number(n.pos_x || 0);
    const y = Number(n.pos_y || 0);
    const el = document.getElementById(`wfNodeEl_${n.id}`);
    const w = (el && el.offsetWidth > 40) ? el.offsetWidth : 285;
    const h = (el && el.offsetHeight > 40) ? el.offsetHeight : 360;
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x + w > maxX) maxX = x + w;
    if (y + h > maxY) maxY = y + h;
  });

  wfPushHistory();
  const padX = 36;
  const padTop = 54;
  const padBottom = 34;
  const grpColor = WF_GROUP_COLORS[wf.groups.length % WF_GROUP_COLORS.length];
  const grpObj = {
    id: `grp_${Date.now().toString(36)}`,
    title: customTitle || `Nhóm Phân Cảnh #${wf.groups.length + 1} (${selectedNodes.length} Node)`,
    x: Math.round(minX - padX),
    y: Math.round(minY - padTop),
    width: Math.max(320, Math.round((maxX - minX) + padX * 2)),
    height: Math.max(240, Math.round((maxY - minY) + padTop + padBottom)),
    color: grpColor,
  };
  wf.groups.push(grpObj);
  renderWfGroupsAndNotes();
  if (typeof toast === "function") {
    toast(`📦 Đã gộp ${selectedNodes.length} Node vào "${grpObj.title}"! Kéo tiêu đề nhóm để di chuyển cả cụm.`, "ok");
  }
  return grpObj;
}

function _getNodesInsideGroup(g) {
  const wf = _getWfBody();
  if (!g) return [];
  const gx1 = Number(g.x || 0);
  const gy1 = Number(g.y || 0);
  const gx2 = gx1 + Math.max(200, Number(g.width || 420));
  const gy2 = gy1 + Math.max(160, Number(g.height || 320));
  return wf.nodes.filter(n => {
    const cx = Number(n.pos_x || 0) + 135;
    const cy = Number(n.pos_y || 0) + 140;
    return cx >= gx1 && cx <= gx2 && cy >= gy1 && cy <= gy2;
  });
}

function onWfGroupMouseDown(ev, groupId) {
  if (ev.button !== 0) return;
  ev.stopPropagation();
  hideWfContextMenu();
  const wf = _getWfBody();
  const g = (wf.groups || []).find(x => x.id === groupId);
  if (!g) return;
  wfPushHistory();
  WF_STATE.draggingGroupId = groupId;
  WF_STATE.dragStartMouseX = ev.clientX;
  WF_STATE.dragStartMouseY = ev.clientY;
  WF_STATE.dragStartNodeX = Number(g.x || 0);
  WF_STATE.dragStartNodeY = Number(g.y || 0);
  // Ghi nhận vị trí ban đầu của tất cả các Node nằm trong Khung Nhóm để kéo cả cụm đi cùng!
  const members = _getNodesInsideGroup(g);
  WF_STATE.groupMemberOrigPositions = {};
  members.forEach(n => {
    WF_STATE.groupMemberOrigPositions[n.id] = { x: Number(n.pos_x || 0), y: Number(n.pos_y || 0) };
  });
}

function cycleWfGroupColor(groupId) {
  const wf = _getWfBody();
  const g = (wf.groups || []).find(x => x.id === groupId);
  if (!g) return;
  const idx = WF_GROUP_COLORS.indexOf(g.color || "#6366f1");
  g.color = WF_GROUP_COLORS[(idx + 1) % WF_GROUP_COLORS.length];
  renderWfGroupsAndNotes();
}

function renameWfGroupPrompt(groupId) {
  const wf = _getWfBody();
  const g = (wf.groups || []).find(x => x.id === groupId);
  if (!g) return;
  const val = prompt("📦 Nhập tên mới cho Khung Nhóm:", g.title || "Khung Nhóm Cảnh");
  if (val !== null && val.trim()) {
    wfPushHistory();
    g.title = val.trim();
    renderWfGroupsAndNotes();
  }
}

function deleteWfGroup(groupId, alsoDeleteNodes = false) {
  const wf = _getWfBody();
  const g = (wf.groups || []).find(x => x.id === groupId);
  if (!g) return;
  wfPushHistory();
  if (alsoDeleteNodes) {
    const memberIds = new Set(_getNodesInsideGroup(g).map(n => n.id));
    wf.nodes = wf.nodes.filter(n => !memberIds.has(n.id));
    wf.edges = wf.edges.filter(e => !memberIds.has(e.source_node_id) && !memberIds.has(e.target_node_id));
  }
  wf.groups = (wf.groups || []).filter(x => x.id !== groupId);
  renderWorkflowCanvas();
}

function selectNodesInWfGroup(groupId) {
  const wf = _getWfBody();
  const g = (wf.groups || []).find(x => x.id === groupId);
  if (!g) return;
  const members = _getNodesInsideGroup(g);
  WF_STATE.selectedNodeIds = new Set(members.map(n => n.id));
  if (members[0]) WF_STATE.selectedNodeId = members[0].id;
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast(`☑️ Đã chọn ${members.length} Node trong "${g.title}"!`, "ok");
}

function runWfGroupNodes(groupId) {
  const wf = _getWfBody();
  const g = (wf.groups || []).find(x => x.id === groupId);
  if (!g) return;
  const members = _getNodesInsideGroup(g);
  if (!members.length) {
    if (typeof toast === "function") toast("⚠️ Chưa có Node nào nằm trong Khung Nhóm này!", "err");
    return;
  }
  runWorkflowExecution(null, members.map(n => n.id));
}

function duplicateWfGroupWithNodes(groupId) {
  const wf = _getWfBody();
  const g = (wf.groups || []).find(x => x.id === groupId);
  if (!g) return;
  const members = _getNodesInsideGroup(g);
  wfPushHistory();
  const offsetX = 60;
  const offsetY = Number(g.height || 320) + 50;
  const idMap = {};
  members.forEach(orig => {
    const uid = `n_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 5)}`;
    idMap[orig.id] = uid;
    const copyCfg = JSON.parse(JSON.stringify(orig.config || {}));
    copyCfg.slug = `${(copyCfg.slug || orig.node_type || 'node')}_copy_${wf.nodes.length + 1}`;
    wf.nodes.push({
      id: uid,
      node_type: orig.node_type,
      label: `${orig.label || orig.id} (Bản sao)`,
      pos_x: Number(orig.pos_x || 0) + offsetX,
      pos_y: Number(orig.pos_y || 0) + offsetY,
      config: copyCfg,
    });
  });
  // Sao chép dây nối nội bộ và dây nối đầu vào
  const memberSet = new Set(members.map(m => m.id));
  wf.edges.slice().forEach(e => {
    if (memberSet.has(e.target_node_id)) {
      wf.edges.push({
        source_node_id: memberSet.has(e.source_node_id) ? idMap[e.source_node_id] : e.source_node_id,
        target_node_id: idMap[e.target_node_id],
        source_handle: e.source_handle || "output_1",
        target_handle: e.target_handle || "input_1",
        edge_type: e.edge_type || "image_ref",
      });
    }
  });
  wf.groups.push({
    id: `grp_${Date.now().toString(36)}`,
    title: `${g.title || 'Nhóm'} (Bản sao)`,
    x: Number(g.x || 0) + offsetX,
    y: Number(g.y || 0) + offsetY,
    width: g.width,
    height: g.height,
    color: g.color || "#a855f7",
  });
  WF_STATE.selectedNodeIds = new Set(Object.values(idMap));
  renderWorkflowCanvas();
  if (typeof toast === "function") toast(`📋 Đã nhân bản Nhóm "${g.title}" cùng ${members.length} Node bên trong!`, "ok");
}

function runSelectedWfNodesCluster() {
  const ids = Array.from(WF_STATE.selectedNodeIds || []);
  if (!ids.length && WF_STATE.selectedNodeId) ids.push(WF_STATE.selectedNodeId);
  if (!ids.length) return;
  runWorkflowExecution(null, ids);
}

// ── GHI CHÚ DÁN (STICKY NOTES) ──
function addWfStickyNoteAtCenter(x = null, y = null) {
  const wf = _getWfBody();
  if (!Array.isArray(wf.notes)) wf.notes = [];
  wfPushHistory();
  const vp = document.getElementById("wfViewport");
  const cx = x !== null ? x : Math.round(((vp ? vp.clientWidth * 0.42 : 460) - WF_STATE.panX) / WF_STATE.zoom);
  const cy = y !== null ? y : Math.round(((vp ? vp.clientHeight * 0.35 : 260) - WF_STATE.panY) / WF_STATE.zoom);
  wf.notes.push({
    id: `note_${Date.now().toString(36)}`,
    title: `Ghi chú #${wf.notes.length + 1}`,
    text: "Ghi chú kịch bản / lưu ý ánh sáng / trang phục cho phân cảnh này...",
    x: cx,
    y: cy,
  });
  renderWfGroupsAndNotes();
  if (typeof toast === "function") toast("📌 Đã dán Ghi chú mới lên Bàn cờ!", "ok");
}

function onWfStickyNoteMouseDown(ev, noteId) {
  if (ev.button !== 0) return;
  ev.stopPropagation();
  hideWfContextMenu();
  const wf = _getWfBody();
  const nt = (wf.notes || []).find(x => x.id === noteId);
  if (!nt) return;
  wfPushHistory();
  WF_STATE.draggingStickyId = noteId;
  WF_STATE.dragStartMouseX = ev.clientX;
  WF_STATE.dragStartMouseY = ev.clientY;
  WF_STATE.dragStartNodeX = Number(nt.x || 0);
  WF_STATE.dragStartNodeY = Number(nt.y || 0);
}

function onWfStickyNoteTextInput(noteId, val) {
  const wf = _getWfBody();
  const nt = (wf.notes || []).find(x => x.id === noteId);
  if (nt) nt.text = val;
}

function deleteWfStickyNote(noteId) {
  const wf = _getWfBody();
  wfPushHistory();
  wf.notes = (wf.notes || []).filter(x => x.id !== noteId);
  renderWfGroupsAndNotes();
}

// ── SỰ KIỆN TƯƠNG TÁC TRÊN BÀN CỜ (#wfViewport): QUÉT CHỌN MARQUEE, KÉO BÀN CỜ, VẼ GROUP, MENU CHUỘT PHẢI ──
function setupWorkflowCanvasInteractions() {
  const vp = document.getElementById("wfViewport");
  if (!vp || vp._wfBound) return;
  vp._wfBound = true;

  // Bắt sự kiện Chuột phải (Right-Click) trên toàn bộ vùng trống bàn cờ
  vp.addEventListener("contextmenu", (ev) => {
    if (ev.target && (ev.target.closest(".wf-node-card") || ev.target.closest(".wf-edge-group") || ev.target.closest(".wf-group-header"))) {
      return;
    }
    openWfCanvasContextMenu(ev);
  });

  vp.addEventListener("mousedown", (ev) => {
    if (ev.button === 2) return;
    hideWfContextMenu();

    // Chuột giữa (button === 1) hoặc giữ phím Space hoặc đang chọn công cụ Pan ('✋') ➔ Kéo dịch chuyển Bàn cờ
    const isEmptyCanvasTarget = (
      ev.target === vp ||
      ev.target.id === "wfTransformStage" ||
      ev.target.id === "wfEdgesSvg" ||
      ev.target.id === "wfGroupsLayer" ||
      ev.target.id === "wfNotesLayer" ||
      ev.target.id === "wfNodesLayer"
    );
    if (!isEmptyCanvasTarget) return;

    if (ev.button === 1 || WF_STATE.spacePressed || WF_STATE.tool === "pan") {
      WF_STATE.isPanning = true;
      WF_STATE.panStartX = ev.clientX - WF_STATE.panX;
      WF_STATE.panStartY = ev.clientY - WF_STATE.panY;
      vp.classList.add("panning");
      return;
    }

    if (WF_STATE.tool === "group") {
      const pt = _screenToCanvasCoords(ev.clientX, ev.clientY);
      WF_STATE.drawingGroup = { startX: pt.x, startY: pt.y, curX: pt.x + 260, curY: pt.y + 200 };
      renderWfGroupsAndNotes();
      return;
    }

    // Mặc định ở công cụ Chọn ('↖' select):
    // Giữ Chuột trái kéo trên nền trống sẽ vẽ khung Quét Chọn Nhiều Node (Marquee Selection #wfMarqueeRect)!
    // (Nếu giữ Alt + Kéo nền trống thì Pan nhanh bàn cờ)
    if (ev.altKey) {
      WF_STATE.isPanning = true;
      WF_STATE.panStartX = ev.clientX - WF_STATE.panX;
      WF_STATE.panStartY = ev.clientY - WF_STATE.panY;
      vp.classList.add("panning");
      return;
    }

    WF_STATE.marquee = {
      startClientX: ev.clientX,
      startClientY: ev.clientY,
      curClientX: ev.clientX,
      curClientY: ev.clientY,
      additive: !!(ev.shiftKey || ev.ctrlKey),
      initialSelected: new Set(ev.shiftKey || ev.ctrlKey ? WF_STATE.selectedNodeIds : []),
      moved: false,
    };
  });

  window.addEventListener("mousemove", (ev) => {
    const wf = _getWfBody();

    // 1. Kéo 1 hoặc cả cụm nhiều Node đang chọn
    if (WF_STATE.draggingNodeId) {
      const dx = (ev.clientX - WF_STATE.dragStartMouseX) / WF_STATE.zoom;
      const dy = (ev.clientY - WF_STATE.dragStartMouseY) / WF_STATE.zoom;
      const origMap = WF_STATE.nodeOrigPositions || {};
      const dragIds = Object.keys(origMap).length ? Object.keys(origMap) : [WF_STATE.draggingNodeId];
      dragIds.forEach(id => {
        const nd = wf.nodes.find(n => n.id === id);
        if (!nd) return;
        const basePos = origMap[id] || { x: WF_STATE.dragStartNodeX, y: WF_STATE.dragStartNodeY };
        nd.pos_x = Math.round(basePos.x + dx);
        nd.pos_y = Math.round(basePos.y + dy);
        const el = document.getElementById(`wfNodeEl_${nd.id}`);
        if (el) {
          el.style.left = `${nd.pos_x}px`;
          el.style.top = `${nd.pos_y}px`;
        }
      });
      renderWorkflowEdgesSvg();
      return;
    }

    // 2. Kéo Khung Nhóm (Group Frame) + tự động di chuyển tất cả các Node bên trong nhóm!
    if (WF_STATE.draggingGroupId) {
      const g = (wf.groups || []).find(x => x.id === WF_STATE.draggingGroupId);
      if (g) {
        const dx = (ev.clientX - WF_STATE.dragStartMouseX) / WF_STATE.zoom;
        const dy = (ev.clientY - WF_STATE.dragStartMouseY) / WF_STATE.zoom;
        g.x = Math.round(WF_STATE.dragStartNodeX + dx);
        g.y = Math.round(WF_STATE.dragStartNodeY + dy);
        const memberOrig = WF_STATE.groupMemberOrigPositions || {};
        Object.keys(memberOrig).forEach(nid => {
          const nd = wf.nodes.find(n => n.id === nid);
          if (nd) {
            nd.pos_x = Math.round(memberOrig[nid].x + dx);
            nd.pos_y = Math.round(memberOrig[nid].y + dy);
            const el = document.getElementById(`wfNodeEl_${nd.id}`);
            if (el) {
              el.style.left = `${nd.pos_x}px`;
              el.style.top = `${nd.pos_y}px`;
            }
          }
        });
        renderWfGroupsAndNotes();
        renderWorkflowEdgesSvg();
      }
      return;
    }

    // 3. Kéo Ghi chú dán (Sticky Note)
    if (WF_STATE.draggingStickyId) {
      const nt = (wf.notes || []).find(x => x.id === WF_STATE.draggingStickyId);
      if (nt) {
        const dx = (ev.clientX - WF_STATE.dragStartMouseX) / WF_STATE.zoom;
        const dy = (ev.clientY - WF_STATE.dragStartMouseY) / WF_STATE.zoom;
        nt.x = Math.round(WF_STATE.dragStartNodeX + dx);
        nt.y = Math.round(WF_STATE.dragStartNodeY + dy);
        renderWfGroupsAndNotes();
      }
      return;
    }

    // 4. Đang kéo vẽ Khung Nhóm mới
    if (WF_STATE.drawingGroup) {
      const pt = _screenToCanvasCoords(ev.clientX, ev.clientY);
      WF_STATE.drawingGroup.curX = pt.x;
      WF_STATE.drawingGroup.curY = pt.y;
      renderWfGroupsAndNotes();
      return;
    }

    // 5. Đang kéo dây nối từ cổng ⚡
    if (WF_STATE.connectingFrom) {
      const pt = _screenToCanvasCoords(ev.clientX, ev.clientY);
      WF_STATE.connectingFrom.curX = pt.x;
      WF_STATE.connectingFrom.curY = pt.y;
      renderWorkflowEdgesSvg();
      return;
    }

    // 6. Đang quét chọn nhiều Node bằng khung Marquee (#wfMarqueeRect)
    if (WF_STATE.marquee) {
      const mq = WF_STATE.marquee;
      mq.curClientX = ev.clientX;
      mq.curClientY = ev.clientY;
      const dist = Math.hypot(mq.curClientX - mq.startClientX, mq.curClientY - mq.startClientY);
      if (dist > 5) mq.moved = true;
      const mqEl = document.getElementById("wfMarqueeRect");
      if (mqEl && mq.moved) {
        const x1 = Math.min(mq.startClientX, mq.curClientX);
        const y1 = Math.min(mq.startClientY, mq.curClientY);
        const w = Math.abs(mq.curClientX - mq.startClientX);
        const h = Math.abs(mq.curClientY - mq.startClientY);
        mqEl.style.display = "block";
        mqEl.style.left = `${x1}px`;
        mqEl.style.top = `${y1}px`;
        mqEl.style.width = `${w}px`;
        mqEl.style.height = `${h}px`;

        const nextSel = new Set(mq.initialSelected);
        document.querySelectorAll(".wf-node-card").forEach(cardEl => {
          const nid = cardEl.getAttribute("data-node-id");
          const r = cardEl.getBoundingClientRect();
          const hit = !(r.right < x1 || r.left > x1 + w || r.bottom < y1 || r.top > y1 + h);
          if (hit && nid) nextSel.add(nid);
          cardEl.classList.toggle("selected", nextSel.has(nid));
        });
        WF_STATE.selectedNodeIds = nextSel;
        if (nextSel.size > 0) WF_STATE.selectedNodeId = Array.from(nextSel)[0];
        updateWfMultiSelectToolbar();
      }
      return;
    }

    // 7. Đang Pan bàn cờ
    if (WF_STATE.isPanning) {
      WF_STATE.panX = ev.clientX - WF_STATE.panStartX;
      WF_STATE.panY = ev.clientY - WF_STATE.panStartY;
      _applyWfStageTransform();
    }
  });

  window.addEventListener("mouseup", (ev) => {
    WF_STATE.draggingNodeId = null;
    WF_STATE.draggingGroupId = null;
    WF_STATE.draggingStickyId = null;
    if (WF_STATE.isPanning) {
      WF_STATE.isPanning = false;
      vp.classList.remove("panning");
    }

    if (WF_STATE.marquee) {
      const mq = WF_STATE.marquee;
      WF_STATE.marquee = null;
      const mqEl = document.getElementById("wfMarqueeRect");
      if (mqEl) mqEl.style.display = "none";
      if (!mq.moved && !mq.additive) {
        clearWfMultiSelection();
      } else {
        updateWfMultiSelectToolbar();
        renderWfInspector();
      }
    }

    if (WF_STATE.drawingGroup) {
      const dg = WF_STATE.drawingGroup;
      WF_STATE.drawingGroup = null;
      const wf = _getWfBody();
      if (!Array.isArray(wf.groups)) wf.groups = [];
      const gx = Math.round(Math.min(dg.startX, dg.curX));
      const gy = Math.round(Math.min(dg.startY, dg.curY));
      const gw = Math.max(260, Math.round(Math.abs(dg.curX - dg.startX)));
      const gh = Math.max(180, Math.round(Math.abs(dg.curY - dg.startY)));
      wfPushHistory();
      const newG = {
        id: `grp_${Date.now().toString(36)}`,
        title: `Phân Cảnh / Nhóm #${wf.groups.length + 1}`,
        x: gx,
        y: gy,
        width: gw,
        height: gh,
        color: WF_GROUP_COLORS[wf.groups.length % WF_GROUP_COLORS.length],
      };
      wf.groups.push(newG);
      setWfCanvasTool("select");
      renderWfGroupsAndNotes();
      selectNodesInWfGroup(newG.id);
      if (typeof toast === "function") toast("📦 Đã tạo Khung Nhóm Cảnh!", "ok");
    }

    // Nếu thả dây từ cổng ⚡ ra vùng trống ➔ Mở menu chọn Node đích để tạo & nối tự động
    if (WF_STATE.connectingFrom) {
      const pending = WF_STATE.connectingFrom;
      WF_STATE.connectingFrom = null;
      renderWorkflowEdgesSvg();
      const targetEl = document.elementFromPoint(ev.clientX, ev.clientY);
      const portEl = targetEl && targetEl.closest ? targetEl.closest(".wf-port") : null;
      const cardEl = targetEl && targetEl.closest ? targetEl.closest(".wf-node-card") : null;
      if (portEl && portEl.getAttribute("data-dir") === "in") {
        const dstId = portEl.getAttribute("data-node-id");
        const dstH = portEl.getAttribute("data-handle") || "input_1";
        _createWfEdgeBetween(pending.nodeId, pending.handle, dstId, dstH);
      } else if (cardEl && cardEl.getAttribute("data-node-id") !== pending.nodeId) {
        const dstId = cardEl.getAttribute("data-node-id");
        _createWfEdgeBetween(pending.nodeId, pending.handle, dstId, null);
      } else {
        openWfConnectionPickerMenu(ev.clientX, ev.clientY, pending.nodeId, pending.handle);
      }
    }
  });

  vp.addEventListener("wheel", (ev) => {
    if (ev.target && ev.target.tagName === "TEXTAREA") return;
    ev.preventDefault();
    const delta = ev.deltaY < 0 ? 0.08 : -0.08;
    zoomWfCanvas(delta, ev.clientX, ev.clientY);
  }, { passive: false });

  window.addEventListener("keydown", (ev) => {
    if (ev.code === "Space" && !["INPUT", "TEXTAREA", "SELECT"].includes((ev.target && ev.target.tagName) || "")) {
      WF_STATE.spacePressed = true;
    }
    const wfTab = document.getElementById("tab-workflow");
    if (!wfTab || !wfTab.classList.contains("active")) return;
    const tag = (ev.target && ev.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "z") {
      ev.preventDefault();
      if (ev.shiftKey) wfRedo(); else wfUndo();
    } else if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "y") {
      ev.preventDefault();
      wfRedo();
    } else if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "d") {
      ev.preventDefault();
      duplicateSelectedWfNode();
    } else if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "g") {
      ev.preventDefault();
      groupSelectedWfNodes();
    } else if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "a") {
      ev.preventDefault();
      selectAllWfNodes();
    } else if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") {
      ev.preventDefault();
      saveCurrentWorkflowToDisk(true);
    } else if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") {
      ev.preventDefault();
      runWorkflowExecution(null);
    } else if (ev.key === "Delete" || ev.key === "Backspace") {
      ev.preventDefault();
      deleteSelectedWfNode();
    } else if (ev.key.toLowerCase() === "n" && !ev.ctrlKey && !ev.metaKey) {
      ev.preventDefault();
      openAddWorkflowNodeModal();
    } else if (ev.key.toLowerCase() === "v" && !ev.ctrlKey && !ev.metaKey) {
      ev.preventDefault();
      setWfCanvasTool("select");
    } else if (ev.key.toLowerCase() === "h" && !ev.ctrlKey && !ev.metaKey) {
      ev.preventDefault();
      setWfCanvasTool("pan");
    } else if (ev.key.toLowerCase() === "g" && !ev.ctrlKey && !ev.metaKey) {
      ev.preventDefault();
      if (WF_STATE.selectedNodeIds && WF_STATE.selectedNodeIds.size >= 2) {
        groupSelectedWfNodes();
      } else {
        setWfCanvasTool(WF_STATE.tool === "group" ? "select" : "group");
      }
    } else if (ev.key.toLowerCase() === "t" && !ev.ctrlKey && !ev.metaKey) {
      ev.preventDefault();
      addWfStickyNoteAtCenter();
    } else if (ev.key === "Escape") {
      hideWfContextMenu();
      clearWfMultiSelection();
    }
  });

  window.addEventListener("keyup", (ev) => {
    if (ev.code === "Space") WF_STATE.spacePressed = false;
  });

  document.addEventListener("click", (ev) => {
    const menu = document.getElementById("wfContextMenu");
    if (menu && menu.classList.contains("open") && !menu.contains(ev.target)) {
      hideWfContextMenu();
    }
  });
}

// ── MENU CHUỘT PHẢI ĐA NGỮ CẢNH 5 CHẾ ĐỘ (NODE / CỤM NHIỀU NODE / KHUNG NHÓM / DÂY NỐI / BÀN CỜ) ──
function hideWfContextMenu() {
  const menu = document.getElementById("wfContextMenu");
  if (menu) {
    menu.classList.remove("open");
    menu.style.display = "none";
  }
}

function _positionAndShowWfMenu(clientX, clientY, innerHtml) {
  const menu = document.getElementById("wfContextMenu");
  if (!menu) return;
  menu.innerHTML = innerHtml;
  menu.classList.add("open");
  menu.style.display = "flex";
  const mw = 285;
  const mh = Math.min(520, menu.scrollHeight || 420);
  const x = Math.max(10, Math.min(clientX, window.innerWidth - mw - 12));
  const y = Math.max(10, Math.min(clientY, window.innerHeight - mh - 12));
  menu.style.left = `${x}px`;
  menu.style.top = `${y}px`;
}

// 1. Chuột phải vào 1 Node (hoặc Cụm nhiều Node đang chọn)
function onWfNodeContextMenu(ev, nodeId) {
  ev.preventDefault();
  ev.stopPropagation();
  if (!WF_STATE.selectedNodeIds.has(nodeId)) {
    WF_STATE.selectedNodeIds = new Set([nodeId]);
  }
  WF_STATE.selectedNodeId = nodeId;
  renderWorkflowCanvas();
  renderWfInspector();

  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return;
  const cfg = node.config || {};
  const ntype = (node.node_type || "").toLowerCase();
  const mediaPath = cfg.result_path || cfg.file_path || "";
  const isVid = cfg.mode === "video" || ntype === "video" || _isVideoFile(mediaPath);
  const multiCount = WF_STATE.selectedNodeIds.size;

  const clusterSectionHtml = multiCount > 1 ? `
    <div class="wf-ctx-header" style="background:rgba(244,114,182,0.15); color:#f9a8d4;">
      <span>📦 CỤM ĐANG CHỌN (${multiCount} NODE)</span>
      <span>CLUSTER</span>
    </div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); groupSelectedWfNodes()">
      <span>📦 Gộp ${multiCount} Node Này Thành Khung Nhóm</span><span style="font-size:10px; color:#94a3b8;">Ctrl+G</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); runSelectedWfNodesCluster()">
      <span>▶️ Chạy Cả Cụm ${multiCount} Node Đã Chọn</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); openWfBatchGeneratorModal()">
      <span style="color:#fde68a; font-weight:800;">🚀 Tạo Số Lượng Lớn (Batch) Cho Cụm Này</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); duplicateSelectedWfNode()">
      <span>📋 Nhân Bản Cả Cụm (${multiCount} Node)</span><span style="font-size:10px; color:#94a3b8;">Ctrl+D</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); alignSelectedWfNodes('horizontal')">
      <span>↔️ Căn Thẳng Hàng Ngang Cụm Đã Chọn</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); alignSelectedWfNodes('vertical')">
      <span>↕️ Căn Thẳng Cột Dọc Cụm Đã Chọn</span>
    </button>
    <button class="wf-ctx-item danger" onclick="hideWfContextMenu(); deleteSelectedWfNode()">
      <span>🗑️ Xoá Cả Cụm (${multiCount} Node)</span><span style="font-size:10px;">Del</span>
    </button>
    <div class="wf-ctx-sep"></div>
  ` : "";

  const html = `
    ${clusterSectionHtml}
    <div class="wf-ctx-header">
      <span>${_wfEscHtml(node.label || node.id)}</span>
      <span style="font-size:9px; color:#94a3b8;">${_wfEscHtml(ntype.toUpperCase())}</span>
    </div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); openWfNodeFullViewer('${node.id}')">
      <span>🔍 Xem Full Nội Dung (Chữ / Ảnh 2K / Video)</span><span style="font-size:10px; color:#94a3b8;">DblClick</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); runWorkflowExecution('${node.id}')">
      <span>▶ Chạy Riêng Node Này</span><span style="font-size:10px; color:#a3e635;">Run</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); rerunWfNodeStrict('${node.id}')">
      <span>↻ Chạy Lại (Khoá Chặt Nhân Vật & Sản Phẩm)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); openWfBatchGeneratorModal('${node.id}')">
      <span style="color:#fde68a; font-weight:800;">🚀 Tạo Số Lượng Lớn (Batch / Hàng Loạt)</span>
    </button>
    <div class="wf-ctx-sep"></div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); groupSelectedWfNodes()">
      <span>📦 Đóng Khung Nhóm Quanh Node Này</span><span style="font-size:10px; color:#94a3b8;">Ctrl+G</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); renameWfNodePrompt('${node.id}')">
      <span>✏️ Đổi Tên Hiển Thị Node</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); duplicateWfNodeById('${node.id}')">
      <span>📋 Sao Chép / Nhân Bản Node</span><span style="font-size:10px; color:#94a3b8;">Ctrl+D</span>
    </button>
    ${["image", "video", "references", "generate"].includes(ntype) ? `
      <button class="wf-ctx-item" onclick="hideWfContextMenu(); pickFileForWfNode('${node.id}', ${ntype === 'references'})">
        <span>📂 Chọn File Ảnh / Video Từ Máy Tính</span>
      </button>
      <button class="wf-ctx-item" onclick="hideWfContextMenu(); openWfMediaLibraryPicker('${node.id}')">
        <span>📚 Chọn Từ Kho Nhân Vật (NV1–NV5) / 176 SP</span>
      </button>
    ` : ''}
    <div class="wf-ctx-sep"></div>
    <div style="padding:3px 10px; font-size:9.5px; font-weight:800; color:#38bdf8;">🔗 TẠO & NỐI NHANH NODE TIẾP THEO:</div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${node.id}', 'generate', 'image')">
      <span>🖼️ ➔ Nối sang Node Tạo Ảnh 2K (Google Flow)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${node.id}', 'generate', 'video')">
      <span>🎬 ➔ Nối sang Node Tạo Video AI (Omni / Veo 3.1)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${node.id}', 'textConcat')">
      <span>🔀 ➔ Nối sang Node Gộp Văn Bản (Text Merge)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${node.id}', 'preview')">
      <span>👁️ ➔ Nối sang Khung Xem Trước (Preview)</span>
    </button>
    ${isVid && mediaPath ? `
      <div class="wf-ctx-sep"></div>
      <button class="wf-ctx-item" style="color:#f472b6;" onclick="hideWfContextMenu(); extractWfVideoEndFrameToNode('${node.id}')">
        <span>📸 Tách Frame Cuối Video ➔ Tạo Node Ảnh 2K</span>
      </button>
      <button class="wf-ctx-item" style="color:#c084fc;" onclick="hideWfContextMenu(); addWfNodeVideoToTimeline('${node.id}')">
        <span>🎞️ Đưa Video Này Vào Thanh Timeline MP4</span>
      </button>
    ` : ''}
    <div class="wf-ctx-sep"></div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); disconnectAllWfNodeEdges('${node.id}')">
      <span>🔌 Ngắt Toàn Bộ Dây Nối Của Node</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); toggleDisableWfNode('${node.id}')">
      <span>⏻ ${cfg.disabled ? 'Bật Lại Node Này' : 'Tạm Tắt Node (Bỏ qua khi chạy)'}</span>
    </button>
    <button class="wf-ctx-item danger" onclick="hideWfContextMenu(); deleteWfNodeById('${node.id}')">
      <span>🗑️ Xoá Node Này Khỏi Sơ Đồ</span><span style="font-size:10px;">Del</span>
    </button>
  `;
  _positionAndShowWfMenu(ev.clientX, ev.clientY, html);
}

// 2. Chuột phải vào tiêu đề Khung Nhóm (Group Box)
function onWfGroupContextMenu(ev, groupId) {
  ev.preventDefault();
  ev.stopPropagation();
  const wf = _getWfBody();
  const g = (wf.groups || []).find(x => x.id === groupId);
  if (!g) return;
  const members = _getNodesInsideGroup(g);
  const html = `
    <div class="wf-ctx-header">
      <span>📦 ${_wfEscHtml(g.title || 'KHUNG NHÓM')}</span>
      <span>${members.length} NODE</span>
    </div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); selectNodesInWfGroup('${g.id}')">
      <span>☑️ Chọn Tất Cả (${members.length}) Node Trong Nhóm</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); runWfGroupNodes('${g.id}')">
      <span>▶️ Chạy Tất Cả Node Trong Nhóm Này</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); selectNodesInWfGroup('${g.id}'); openWfBatchGeneratorModal()">
      <span style="color:#fde68a; font-weight:800;">🚀 Tạo Số Lượng Lớn (Batch) Cho Nhóm Này</span>
    </button>
    <div class="wf-ctx-sep"></div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); renameWfGroupPrompt('${g.id}')">
      <span>✏️ Đổi Tên Khung Nhóm</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); cycleWfGroupColor('${g.id}')">
      <span>🎨 Đổi Màu Khung Nhóm</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); duplicateWfGroupWithNodes('${g.id}')">
      <span>📋 Nhân Bản Cả Nhóm & Các Node Bên Trong</span>
    </button>
    <div class="wf-ctx-sep"></div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); deleteWfGroup('${g.id}', false)">
      <span>🔓 Bung Khung Nhóm (Giữ Nguyên Các Node)</span>
    </button>
    <button class="wf-ctx-item danger" onclick="hideWfContextMenu(); deleteWfGroup('${g.id}', true)">
      <span>🗑️ Xoá Khung Nhóm & Cả ${members.length} Node Bên Trong</span>
    </button>
  `;
  _positionAndShowWfMenu(ev.clientX, ev.clientY, html);
}

// 3. Chuột phải vào Dây nối (Edge)
function onWfEdgeContextMenu(ev, edgeIdx) {
  ev.preventDefault();
  ev.stopPropagation();
  const wf = _getWfBody();
  const e = wf.edges[edgeIdx];
  if (!e) return;
  const src = wf.nodes.find(n => n.id === e.source_node_id);
  const dst = wf.nodes.find(n => n.id === e.target_node_id);
  const html = `
    <div class="wf-ctx-header">
      <span>🔗 DÂY NỐI DỮ LIỆU</span>
    </div>
    <div style="padding:6px 10px; font-size:10.5px; color:#cbd5e1;">
      <b>${_wfEscHtml((src && src.label) || e.source_node_id)}</b> ➔ <b>${_wfEscHtml((dst && dst.label) || e.target_node_id)}</b>
    </div>
    <div class="wf-ctx-sep"></div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); insertIntermediateNodeOnWfEdge(${edgeIdx}, 'textConcat')">
      <span>➕ Chèn Node Gộp Văn Bản Vào Giữa Dây Này</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); insertIntermediateNodeOnWfEdge(${edgeIdx}, 'preview')">
      <span>👁️ Chèn Khung Xem Trước Vào Giữa Dây Này</span>
    </button>
    <button class="wf-ctx-item danger" onclick="hideWfContextMenu(); confirmOrRemoveWfEdge(${edgeIdx})">
      <span>🗑️ Ngắt / Xoá Dây Nối Này</span>
    </button>
  `;
  _positionAndShowWfMenu(ev.clientX, ev.clientY, html);
}

function insertIntermediateNodeOnWfEdge(edgeIdx, nodeType = "textConcat") {
  const wf = _getWfBody();
  const e = wf.edges[edgeIdx];
  if (!e) return;
  const src = wf.nodes.find(n => n.id === e.source_node_id);
  const dst = wf.nodes.find(n => n.id === e.target_node_id);
  if (!src || !dst) return;
  wfPushHistory();
  const midX = Math.round((Number(src.pos_x || 0) + Number(dst.pos_x || 0)) / 2);
  const midY = Math.round((Number(src.pos_y || 0) + Number(dst.pos_y || 0)) / 2);
  const oldTargetHandle = e.target_handle || "input_1";
  wf.edges.splice(edgeIdx, 1);
  const midNode = addNodeToActiveWorkflow(nodeType, { x: midX, y: midY });
  if (midNode) {
    _createWfEdgeBetween(src.id, "output_1", midNode.id, null);
    _createWfEdgeBetween(midNode.id, "output_1", dst.id, oldTargetHandle);
  }
}

// 4. Chuột phải vào Vùng Trống Bàn Cờ (Canvas)
function openWfCanvasContextMenu(ev) {
  ev.preventDefault();
  ev.stopPropagation();
  const pt = _screenToCanvasCoords(ev.clientX, ev.clientY);
  WF_STATE.contextMenuPos = pt;
  WF_STATE.contextMenuCanvasPos = pt;
  const selCount = WF_STATE.selectedNodeIds ? WF_STATE.selectedNodeIds.size : 0;

  const html = `
    <div class="wf-ctx-header">
      <span>⚡ MENU BÀN CỜ WORKFLOW AI</span>
      <span style="font-size:9px; color:#94a3b8;">(${pt.x}, ${pt.y})</span>
    </div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); openAddWorkflowNodeModal()">
      <span>➕ Mở Kho Thêm Node Mới (16 Loại Node)</span><span style="font-size:10px; color:#94a3b8;">Phím N</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); openWfBatchGeneratorModal()">
      <span style="color:#fde68a; font-weight:800;">🚀 Tạo Số Lượng Lớn (Batch / Hàng Loạt SP)</span>
    </button>
    ${selCount >= 1 ? `
      <button class="wf-ctx-item" onclick="hideWfContextMenu(); groupSelectedWfNodes()">
        <span style="color:#f9a8d4; font-weight:800;">📦 Gộp ${selCount} Node Đang Chọn Thành Nhóm</span><span style="font-size:10px; color:#94a3b8;">Ctrl+G</span>
      </button>
    ` : ''}
    <div class="wf-ctx-sep"></div>
    <div style="padding:3px 10px; font-size:9.5px; font-weight:800; color:#a3e635;">⚡ THẢ NHANH NODE TẠI VỊ TRÍ CHUỘT:</div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); addNodeToActiveWorkflow('image', {x:${pt.x}, y:${pt.y}})">
      <span>🖼️ + Node Ảnh Đầu Vào (Nhân vật / Sản phẩm)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); addNodeToActiveWorkflow('video', {x:${pt.x}, y:${pt.y}})">
      <span>🎬 + Node Video Đầu Vào (Video mẫu / Motion Ref)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); addNodeToActiveWorkflow('prompt', {x:${pt.x}, y:${pt.y}})">
      <span>📝 + Node Prompt Câu Lệnh (Gõ chữ & AI hỗ trợ)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); addNodeToActiveWorkflow('textConcat', {x:${pt.x}, y:${pt.y}})">
      <span>🔀 + Node Gộp Nhiều Văn Bản (Text Merge)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); addNodeToActiveWorkflow('generate', {x:${pt.x}, y:${pt.y}, mode:'image'})">
      <span>✦ + Node Google Flow — Tạo Ảnh 2K</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); addNodeToActiveWorkflow('generate', {x:${pt.x}, y:${pt.y}, mode:'video'})">
      <span>🎥 + Node Google Flow — Tạo Video 1080p</span>
    </button>
    <div class="wf-ctx-sep"></div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); setWfCanvasTool('group')">
      <span>▱ Kéo Vẽ Khung Nhóm Cảnh Mới</span><span style="font-size:10px; color:#94a3b8;">Phím G</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); addWfStickyNoteAtCenter(${pt.x}, ${pt.y})">
      <span>📌 Dán Ghi Chú Nhanh Tại Đây</span><span style="font-size:10px; color:#94a3b8;">Phím T</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); openWfMediaLibraryPicker(null)">
      <span>📚 Mở Kho Nhân Vật (NV1–NV5) & 176 Sản Phẩm</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); openWfScriptToNodesModal()">
      <span>📜 Kịch Bản Đa Cảnh ➔ Tự Động Rải Sơ Đồ Node</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); openWfRunOrderModal()">
      <span>⇅ Xem & Sắp Xếp Thứ Tự Chạy Các Node</span>
    </button>
    <div class="wf-ctx-sep"></div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); selectAllWfNodes()">
      <span>☑️ Chọn Tất Cả Node Trên Bàn Cờ</span><span style="font-size:10px; color:#94a3b8;">Ctrl+A</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); autoLayoutWorkflowNodes()">
      <span>📐 Tự Động Xếp Đẹp Sơ Đồ Node</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); fitWorkflowCanvasView()">
      <span>🗖 Căn Giữa & Thu Phóng Vừa Khung Hình</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); runWorkflowExecution(null)">
      <span style="color:#a3e635; font-weight:800;">▶ Chạy Toàn Bộ Sơ Đồ Workflow</span><span style="font-size:10px; color:#94a3b8;">Ctrl+Enter</span>
    </button>
  `;
  _positionAndShowWfMenu(ev.clientX, ev.clientY, html);
}

// 5. Khi kéo dây từ cổng ⚡ thả ra vùng trống ➔ Tự bật menu chọn Node đích để tạo và nối dây!
function openWfConnectionPickerMenu(clientX, clientY, sourceNodeId, sourceHandle) {
  const wf = _getWfBody();
  const srcNode = wf.nodes.find(n => n.id === sourceNodeId);
  if (!srcNode) return;
  const pt = _screenToCanvasCoords(clientX, clientY);

  const html = `
    <div class="wf-ctx-header">
      <span>⚡ NỐI TỪ "${_wfEscHtml((srcNode.label || srcNode.id).slice(0, 22))}" SANG:</span>
    </div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${sourceNodeId}', 'generate', 'image', ${pt.x}, ${pt.y})">
      <span>🖼️ Tạo Ảnh 2K (Google Flow Nano Banana 2.1)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${sourceNodeId}', 'generate', 'video', ${pt.x}, ${pt.y})">
      <span>🎬 Tạo Video AI (Google Flow Omni 1.1 / Veo 3.1)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${sourceNodeId}', 'gpt_image', 'image', ${pt.x}, ${pt.y})">
      <span>🤖 Tạo Ảnh qua ChatGPT Image (CLIProxy)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${sourceNodeId}', 'grok_generate', 'video', ${pt.x}, ${pt.y})">
      <span>⚡ Tạo Ảnh/Video qua xAI Grok (CLIProxy)</span>
    </button>
    <div class="wf-ctx-sep"></div>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${sourceNodeId}', 'textConcat', null, ${pt.x}, ${pt.y})">
      <span>🔀 Gộp Nhiều Văn Bản (Text Merge)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${sourceNodeId}', 'textAppend', null, ${pt.x}, ${pt.y})">
      <span>➕ Nối Thêm Hậu Tố Prompt (Text Append)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${sourceNodeId}', 'preview', null, ${pt.x}, ${pt.y})">
      <span>👁️ Khung Xem Trước Kết Quả (Preview)</span>
    </button>
    <button class="wf-ctx-item" onclick="hideWfContextMenu(); spawnAndConnectWfNode('${sourceNodeId}', 'auto_download', null, ${pt.x}, ${pt.y})">
      <span>⬇️ Tự Động Lưu Vào final_videos/</span>
    </button>
  `;
  _positionAndShowWfMenu(clientX, clientY, html);
}

function spawnAndConnectWfNode(sourceNodeId, targetType, modeOverride = null, posX = null, posY = null) {
  const wf = _getWfBody();
  const srcNode = wf.nodes.find(n => n.id === sourceNodeId);
  if (!srcNode) return;
  const x = posX !== null ? posX : Number(srcNode.pos_x || 0) + 350;
  const y = posY !== null ? posY : Number(srcNode.pos_y || 0);
  const newNode = addNodeToActiveWorkflow(targetType, { x, y, mode: modeOverride });
  if (newNode) {
    _createWfEdgeBetween(sourceNodeId, "output_1", newNode.id, null);
  }
}

// ── THÊM NODE MỚI VÀO SƠ ĐỒ (#modalWfAddNode) ──
function openAddWorkflowNodeModal() {
  openModal("modalWfAddNode");
  const inp = document.getElementById("inpWfSearchNode");
  if (inp) {
    inp.value = "";
    setTimeout(() => inp.focus(), 50);
  }
  renderWfAddNodeCatalog("");
}
const openWfAddNodeModal = openAddWorkflowNodeModal;

function renderWfAddNodeCatalog(filterText = "") {
  const listEl = document.getElementById("wfAddNodeListContainer");
  if (!listEl) return;
  const q = (filterText || "").trim().toLowerCase();
  const items = WF_NODE_CATALOG.filter(c =>
    !q ||
    c.title.toLowerCase().includes(q) ||
    c.desc.toLowerCase().includes(q) ||
    c.type.toLowerCase().includes(q) ||
    c.badge.toLowerCase().includes(q)
  );
  listEl.innerHTML = items.map(item => `
    <div class="wf-addnode-item"
         onclick="addNodeToActiveWorkflow('${item.type}'); closeModal('modalWfAddNode');">
      <div class="wf-addnode-icon" style="color:${item.iconColor || '#a3e635'};">
        ${item.icon}
      </div>
      <div style="flex:1; min-width:0;">
        <div style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
          <span style="font-size:12.5px; font-weight:800; color:#f8fafc;">${_wfEscHtml(item.title)}</span>
          <span style="font-size:9px; font-weight:800; padding:2px 6px; border-radius:4px; background:rgba(163,230,53,0.14); color:#a3e635;">${_wfEscHtml(item.badge)}</span>
        </div>
        <div style="font-size:11px; color:#94a3b8; margin-top:3px; line-height:1.4;">${_wfEscHtml(item.desc)}</div>
      </div>
    </div>
  `).join("");
}

function quickAddWorkflowNode(nodeType) {
  return addNodeToActiveWorkflow(nodeType);
}

function addNodeToActiveWorkflow(nodeType, opts = {}) {
  const wf = _getWfBody();
  wfPushHistory();
  const cat = WF_NODE_CATALOG.find(c => c.type.toLowerCase() === (nodeType || "").toLowerCase()) || WF_NODE_CATALOG[0];
  const uid = `n_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 5)}`;
  const slug = `${cat.type.toLowerCase()}_${wf.nodes.length + 1}`;
  const isGen = ["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(cat.type);
  const mode = opts.mode || (cat.type === "video" ? "video" : "image");

  const cfg = {
    slug,
    mode,
    provider: cat.type === "gpt_image" ? "cliproxy_gpt" : (cat.type === "grok_generate" ? "grok" : (cat.type === "gemini_generate" ? "cliproxy_gemini" : "flow")),
    model: isGen ? (mode === "video" ? "Omni 1.1 Flash" : "Nano Banana 2.1") : (cat.type === "prompt" ? "gpt-5.4" : ""),
    aspect_ratio: opts.aspect_ratio || "9:16",
    count: 1,
    duration: "8s",
    resolution: "1080p",
    use_own_prompt: false,
    prompt: opts.prompt || "",
    file_path: opts.filePath || "",
    result_path: opts.filePath || "",
    reference_images: opts.filePath ? [opts.filePath] : [],
    auto_download: false,
    status: opts.filePath || ["prompt", "text", "note", "textConcat", "textAppend", "negativePrompt"].includes(cat.type) ? "done" : "idle",
  };

  const vp = document.getElementById("wfViewport");
  const defaultX = Math.round(((vp ? vp.clientWidth * 0.36 : 420) - WF_STATE.panX) / WF_STATE.zoom) + (wf.nodes.length % 4) * 40;
  const defaultY = Math.round(((vp ? vp.clientHeight * 0.28 : 220) - WF_STATE.panY) / WF_STATE.zoom) + (wf.nodes.length % 4) * 40;

  let label = opts.label || cat.defaultLabel || cat.title;
  if (opts.mode === "video" && cat.type === "generate" && !opts.label) label = "Google Flow — Tạo Video AI";
  if (opts.mode === "image" && cat.type === "generate" && !opts.label) label = "Google Flow — Tạo Ảnh 2K";

  const newNode = {
    id: uid,
    node_id: uid,
    node_type: cat.type,
    label: label,
    node_name: label,
    pos_x: opts.x !== undefined ? opts.x : defaultX,
    pos_y: opts.y !== undefined ? opts.y : defaultY,
    config: cfg,
  };
  wf.nodes.push(newNode);
  WF_STATE.selectedNodeId = uid;
  WF_STATE.selectedNodeIds = new Set([uid]);
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast(`➕ Đã thêm Node: ${newNode.label}`, "ok");
  return newNode;
}

function spawnNewMediaNodeFromResult(encodedPath, mediaType = "image") {
  const path = decodeURIComponent(encodedPath || "");
  if (!path) return;
  const wf = _getWfBody();
  const sel = wf.nodes.find(n => n.id === WF_STATE.selectedNodeId);
  const x = sel ? Number(sel.pos_x || 0) + 340 : 520;
  const y = sel ? Number(sel.pos_y || 0) : 220;
  const baseName = path.split(/[\\/]/).pop() || "Kết quả";
  addNodeToActiveWorkflow(mediaType === "video" ? "video" : "image", {
    x,
    y,
    filePath: path,
    label: `${mediaType === 'video' ? '🎬 Video:' : '🖼️ Ảnh 2K:'} ${baseName.slice(0, 22)}`,
  });
}

// ── BẢNG CHI TIẾT CẤU HÌNH NODE BÊN PHẢI (#wfInspectorSidebar & #wfInspectorBody) ──
function closeWfInspector() {
  const sb = document.getElementById("wfInspectorSidebar");
  if (sb) sb.classList.add("closed");
}

function toggleSelectedWfNodeDisabled() {
  toggleDisableWfNode(WF_STATE.selectedNodeId);
}

function saveSelectedWfNodeFromInspector() {
  saveCurrentWorkflowToDisk(true);
}

function switchWfInspectorTab(tab) {
  WF_STATE.inspectorTab = tab || "config";
  const bCfg = document.getElementById("wfInspTabBtnConfig");
  const bRes = document.getElementById("wfInspTabBtnResults");
  if (bCfg) bCfg.classList.toggle("active", WF_STATE.inspectorTab === "config");
  if (bRes) bRes.classList.toggle("active", WF_STATE.inspectorTab === "results");
  renderWfInspector();
}

function renderWfInspector() {
  const sb = document.getElementById("wfInspectorSidebar");
  const body = document.getElementById("wfInspectorBody");
  if (!body) return;
  if (sb) sb.classList.remove("closed");

  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === WF_STATE.selectedNodeId);
  if (!node) {
    body.innerHTML = `
      <div style="text-align:center; padding:32px 12px; color:#64748b; font-size:11.5px;">
        <div style="font-size:30px; margin-bottom:8px;">👆</div>
        <div style="font-weight:800; color:#cbd5e1; margin-bottom:6px;">Chưa chọn Node nào</div>
        <div>Nhấp chuột trái vào 1 Node để chỉnh thông số, kéo chuột trái trên nền trống để quét gộp nhiều Node, hoặc <b>Chuột phải</b> để mở Menu thao tác nhanh!</div>
      </div>
    `;
    return;
  }

  if (!node.config) node.config = {};
  const cfg = node.config;
  const ntype = (node.node_type || "generate").toLowerCase();
  const isGen = ["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(ntype);
  const isMedia = ["image", "video", "references", "preview"].includes(ntype);
  const catMeta = WF_NODE_CATALOG.find(c => c.type.toLowerCase() === ntype) || { icon: "✦", title: ntype };
  const inEdges = wf.edges.filter(e => e.target_node_id === node.id);
  const outEdges = wf.edges.filter(e => e.source_node_id === node.id);
  const mergedText = resolveWfNodeMergedText(node.id);
  const mediaPath = cfg.result_path || cfg.file_path || "";
  const mediaUrl = _getMediaUrlForWfPath(mediaPath);
  const isVid = cfg.mode === "video" || ntype === "video" || _isVideoFile(mediaPath);

  if (WF_STATE.inspectorTab === "results") {
    const batchHist = Array.isArray(wf.batch_history) ? wf.batch_history : [];
    body.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:10px;">
        <div style="font-size:12px; font-weight:800; color:#f8fafc;">${catMeta.icon} ${_wfEscHtml(node.label || node.id)}</div>
        ${mediaUrl ? `
          <div style="border-radius:10px; overflow:hidden; border:1px solid rgba(255,255,255,0.12); background:#05080f;">
            ${isVid
              ? `<video src="${mediaUrl}" controls autoplay loop muted style="width:100%; max-height:280px; object-fit:contain;"></video>`
              : `<img src="${mediaUrl}" style="width:100%; max-height:280px; object-fit:contain; cursor:pointer;" onclick="openWfNodeFullViewer('${node.id}')" />`
            }
          </div>
          <div style="font-size:10px; color:#94a3b8; word-break:break-all; font-family:Consolas,monospace;">📁 ${_wfEscHtml(mediaPath)}</div>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button class="btn btn-xs btn-amber" style="flex:1; font-weight:800;" onclick="openWfNodeFullViewer('${node.id}')">🔍 Xem Full</button>
            <button class="btn btn-xs btn-primary" style="flex:1;" onclick="spawnNewMediaNodeFromResult('${encodeURIComponent(mediaPath)}', '${isVid ? 'video' : 'image'}')">➕ Tách Ra Node</button>
            ${isVid ? `<button class="btn btn-xs btn-success" style="width:100%;" onclick="addWfNodeVideoToTimeline('${node.id}')">🎞️ Đưa Vào Thanh Timeline MP4</button>` : ''}
          </div>
        ` : `
          <div style="padding:18px; text-align:center; color:#64748b; border:1px dashed rgba(255,255,255,0.12); border-radius:10px; font-size:11px;">
            Chưa có file Ảnh/Video kết quả cho Node này. Hãy bấm <b>▶ Chạy Node</b>!
          </div>
        `}
        ${mergedText ? `
          <div>
            <div style="font-size:10.5px; font-weight:800; color:#38bdf8; margin-bottom:4px;">📝 VĂN BẢN / PROMPT ĐÃ GỘP (${mergedText.length} ký tự):</div>
            <div style="background:#080c14; border:1px solid rgba(56,189,248,0.25); border-radius:8px; padding:8px; font-size:11px; color:#e2e8f0; white-space:pre-wrap; max-height:190px; overflow-y:auto;">${_wfEscHtml(mergedText)}</div>
          </div>
        ` : ''}
        ${batchHist.length ? `
          <div style="border-top:1px solid rgba(255,255,255,0.08); padding-top:8px;">
            <div style="font-size:10.5px; font-weight:800; color:#fde68a; margin-bottom:6px;">🚀 LỊCH SỬ CHẠY SỐ LƯỢNG LỚN (${batchHist.length} LÔ):</div>
            <div style="display:flex; flex-direction:column; gap:5px; max-height:220px; overflow-y:auto;">
              ${batchHist.slice(0, 12).map(b => `
                <div style="background:#111726; border:1px solid rgba(255,255,255,0.08); border-radius:7px; padding:6px 8px; font-size:10.5px;">
                  <div style="display:flex; justify-content:space-between; font-weight:800; color:#f8fafc;">
                    <span>#${b.batch_index} • ${_wfEscHtml(b.label || '')}</span>
                    <span style="color:#a3e635;">${_wfEscHtml(b.finished_at || '')}</span>
                  </div>
                  ${b.exported_mp4 ? `<div style="margin-top:4px;"><a href="${b.exported_mp4_url}" target="_blank" style="color:#38bdf8; text-decoration:underline;">🎬 Mở Video MP4 Đã Xuất</a></div>` : ''}
                </div>
              `).join("")}
            </div>
          </div>
        ` : ''}
      </div>
    `;
    return;
  }

  // Tab Cấu hình (Config)
  body.innerHTML = `
    <div style="background:rgba(163,230,53,0.08); border:1px solid rgba(163,230,53,0.25); border-radius:9px; padding:8px 10px; display:flex; align-items:center; justify-content:space-between;">
      <div>
        <div style="font-size:11.5px; font-weight:800; color:#d9f99d;">${catMeta.icon} ${_wfEscHtml(catMeta.title)}</div>
        <div style="font-size:9.5px; color:#94a3b8;">ID: ${_wfEscHtml(node.id)} • Trạng thái: <b>${_wfEscHtml(cfg.status || 'idle')}</b></div>
      </div>
      <button class="btn btn-xs btn-amber" style="font-weight:800;" onclick="openWfNodeFullViewer('${node.id}')">🔍 Xem Full</button>
    </div>

    <div>
      <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#94a3b8; margin-bottom:4px;">
        <span style="font-weight:700; color:#e2e8f0;">🏷️ Tên hiển thị của Node</span>
        <span style="font-family:Consolas,monospace; color:#38bdf8;">@${_wfEscHtml(cfg.slug || 'node')}</span>
      </div>
      <input type="text" value="${_wfEscHtml(node.label || '')}"
             oninput="onWfInspFieldChange('label', this.value)"
             style="width:100%; background:#0a0d14; border:1px solid rgba(255,255,255,0.12); color:#f8fafc; padding:7px 10px; border-radius:7px; font-size:12px; font-weight:700;" />
    </div>

    <div>
      <label style="font-size:10.5px; color:#94a3b8; display:block; margin-bottom:4px;">🔗 Mã @slug (chèn @slug vào Prompt khác)</label>
      <input type="text" value="${_wfEscHtml(cfg.slug || '')}"
             oninput="onWfInspFieldChange('slug', this.value)"
             style="width:100%; background:#0a0d14; border:1px solid rgba(255,255,255,0.1); color:#38bdf8; padding:6px 10px; border-radius:7px; font-size:11px; font-family:Consolas,monospace;" />
    </div>

    ${isMedia ? `
      <div style="background:#0b101b; border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:8px;">
        <div style="font-size:11px; font-weight:800; color:#f8fafc;">📂 Nguồn Ảnh / Video Tham Chiếu</div>
        <div style="display:flex; gap:6px;">
          <button class="btn btn-xs btn-primary" style="flex:1; padding:6px;" onclick="pickFileForWfNode('${node.id}', ${ntype === 'references'})">📂 Chọn File Máy Tính</button>
          <button class="btn btn-xs btn-outline" style="flex:1; padding:6px; border-color:#818cf8; color:#c7d2fe;" onclick="openWfMediaLibraryPicker('${node.id}')">📚 Kho NV / 176 SP</button>
        </div>
        <input type="text" value="${_wfEscHtml(cfg.file_path || cfg.result_path || '')}"
               placeholder="Đường dẫn file ảnh (.png/.jpg) hoặc video (.mp4)..."
               oninput="onWfInspFieldChange('file_path', this.value)"
               style="width:100%; font-size:10.5px; font-family:Consolas,monospace; background:#070a10;" />
        <button class="btn btn-xs btn-outline" style="border-color:#f59e0b; color:#fde68a; font-weight:800;" onclick="openWfBatchGeneratorModal('${node.id}')">
          🚀 Thay Hàng Loạt Sản Phẩm / Bộ Đồ Vào Node Này
        </button>
        ${isVid && mediaPath ? `
          <button class="btn btn-xs" style="background:rgba(244,114,182,0.2); color:#f472b6; border:1px solid rgba(244,114,182,0.45); font-weight:800; padding:6px;" onclick="extractWfVideoEndFrameToNode('${node.id}')">
            📸 Tách Frame Cuối Video Này Thành Node Ảnh 2K
          </button>
        ` : ''}
      </div>
    ` : ''}

    ${isGen ? `
      <div style="background:#0b101b; border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:10px; display:flex; flex-direction:column; gap:9px;">
        <div style="font-size:11px; font-weight:800; color:#a3e635;">⚙️ Cài Đặt Tạo Ảnh 2K / Video AI</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
          <button class="btn btn-xs ${cfg.mode !== 'video' ? 'btn-primary' : 'btn-outline'}"
                  onclick="onWfNodeInlineModeChange('${node.id}', 'image')">🖼️ Tạo Ảnh 2K</button>
          <button class="btn btn-xs ${cfg.mode === 'video' ? 'btn-primary' : 'btn-outline'}"
                  onclick="onWfNodeInlineModeChange('${node.id}', 'video')">🎬 Tạo Video AI</button>
        </div>
        <div>
          <label style="font-size:10.5px; color:#94a3b8; display:block; margin-bottom:3px;">🤖 Model AI thực thi</label>
          <select onchange="onWfInspFieldChange('model', this.value)" style="width:100%; font-size:11.5px;">
            ${cfg.mode === 'video' ? `
              <option value="Omni 1.1 Flash" ${(cfg.model || '').includes('Omni') ? 'selected' : ''}>🎬 Google Flow — Omni 1.1 Flash (Đa Tham Chiếu)</option>
              <option value="Veo 3.1 - Fast" ${(cfg.model || '').includes('Fast') ? 'selected' : ''}>🎬 Google Flow — Veo 3.1 Fast (Nhanh + Voice)</option>
              <option value="Veo 3.1 - Quality" ${(cfg.model || '').includes('Quality') ? 'selected' : ''}>🎬 Google Flow — Veo 3.1 Quality (Cinema)</option>
              <option value="grok-imagine-video" ${(cfg.model || '').includes('grok') ? 'selected' : ''}>⚡ xAI Grok Imagine Video (CLIProxy)</option>
            ` : `
              <option value="Nano Banana 2.1" ${(cfg.model || '').includes('2.1') ? 'selected' : ''}>🍌 Google Flow — Nano Banana 2.1 (Chuẩn 2K)</option>
              <option value="Nano Banana Pro" ${(cfg.model || '').includes('Pro') ? 'selected' : ''}>🍌 Google Flow — Nano Banana Pro (Siêu Nét)</option>
              <option value="Nano Banana 2 Lite" ${(cfg.model || '').includes('Lite') ? 'selected' : ''}>🍌 Google Flow — Nano Banana 2 Lite</option>
              <option value="gpt-image-1" ${(cfg.model || '').includes('gpt') ? 'selected' : ''}>🤖 ChatGPT Image (CLIProxy)</option>
              <option value="grok-imagine-image" ${(cfg.model || '').includes('grok') ? 'selected' : ''}>⚡ xAI Grok Imagine Image (CLIProxy)</option>
            `}
          </select>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
          <div>
            <label style="font-size:10px; color:#94a3b8; display:block; margin-bottom:3px;">📐 Tỷ lệ khung hình</label>
            <select onchange="onWfInspFieldChange('aspect_ratio', this.value)" style="width:100%; font-size:11px;">
              <option value="9:16" ${(cfg.aspect_ratio || '9:16') === '9:16' ? 'selected' : ''}>📱 9:16 (Dọc TikTok/Reels)</option>
              <option value="16:9" ${cfg.aspect_ratio === '16:9' ? 'selected' : ''}>🖥 16:9 (Ngang YouTube)</option>
              <option value="4:5" ${cfg.aspect_ratio === '4:5' ? 'selected' : ''}>🖼️ 4:5 (Lookbook)</option>
              <option value="1:1" ${cfg.aspect_ratio === '1:1' ? 'selected' : ''}>⬛ 1:1 (Vuông)</option>
            </select>
          </div>
          <div>
            <label style="font-size:10px; color:#94a3b8; display:block; margin-bottom:3px;">${cfg.mode === 'video' ? '⏱ Thời lượng Video' : '🔢 Số lượng biến thể'}</label>
            ${cfg.mode === 'video' ? `
              <select onchange="onWfInspFieldChange('duration', this.value)" style="width:100%; font-size:11px;">
                <option value="8s" ${(cfg.duration || '8s') === '8s' ? 'selected' : ''}>⏱ 8 giây</option>
                <option value="10s" ${cfg.duration === '10s' ? 'selected' : ''}>⏱ 10 giây</option>
                <option value="6s" ${cfg.duration === '6s' ? 'selected' : ''}>⏱ 6 giây</option>
              </select>
            ` : `
              <input type="number" min="1" max="10" value="${Number(cfg.count || 1)}"
                     onchange="onWfInspFieldChange('count', Number(this.value))" style="width:100%; font-size:11px;" />
            `}
          </div>
        </div>
        <label style="display:flex; align-items:center; justify-content:space-between; font-size:11px; color:#cbd5e1; cursor:pointer; padding-top:4px;">
          <span>✍️ Dùng Prompt riêng tại Node này</span>
          <input type="checkbox" ${cfg.use_own_prompt ? 'checked' : ''} onchange="onWfInspFieldChange('use_own_prompt', this.checked)" />
        </label>
        <label style="display:flex; align-items:center; justify-content:space-between; font-size:11px; color:#cbd5e1; cursor:pointer;">
          <span>⬇️ Tự động tải file 2K/1080p khi xong</span>
          <input type="checkbox" ${cfg.auto_download ? 'checked' : ''} onchange="onWfInspFieldChange('auto_download', this.checked)" />
        </label>
        <button class="btn btn-xs btn-outline" style="border-color:#f59e0b; color:#fde68a; font-weight:800; padding:6px;" onclick="openWfBatchGeneratorModal('${node.id}')">
          🚀 Mở Trung Tâm Tạo Số Lượng Lớn (Batch Matrix)
        </button>
      </div>
    ` : ''}

    <div style="display:flex; flex-direction:column; gap:5px;">
      <div style="display:flex; align-items:center; justify-content:space-between;">
        <label style="font-size:11px; font-weight:800; color:#e2e8f0;">📝 Nội dung Văn bản / Prompt</label>
        <button class="btn btn-xs btn-outline" style="font-size:9.5px; padding:2px 7px;" onclick="openWfNodeFullViewer('${node.id}')">🔍 Xem & Sửa Full</button>
      </div>
      <textarea id="txtWfInspPrompt" rows="5"
                placeholder="Nhập câu lệnh Prompt, mô tả bối cảnh, hoặc dùng @slug để chèn nội dung từ Node khác..."
                oninput="onWfInspFieldChange('prompt', this.value)"
                style="width:100%; font-size:11.5px; background:#080b12; color:#f8fafc; border:1px solid rgba(255,255,255,0.14); border-radius:8px; padding:8px; line-height:1.45;">${_wfEscHtml(cfg.prompt || cfg.text || cfg.note || cfg.suffix || '')}</textarea>
      ${ntype === 'prompt' ? `
        <div style="display:flex; gap:6px; align-items:center; justify-content:space-between; margin-top:2px;">
          <label style="font-size:10.5px; color:#94a3b8; display:flex; align-items:center; gap:5px; cursor:pointer;">
            <input type="checkbox" ${cfg.ai_enabled ? 'checked' : ''} onchange="onWfInspFieldChange('ai_enabled', this.checked)" />
            🤖 Dùng AI CLIProxy tự mở rộng
          </label>
          <button class="btn btn-xs btn-primary" onclick="testRunPromptNodeWithAi('${node.id}')">🪄 AI Viết Ngay</button>
        </div>
      ` : ''}
    </div>

    <div style="background:#0b101b; border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:9px 10px; display:flex; flex-direction:column; gap:6px;">
      <div style="font-size:10.5px; font-weight:800; color:#94a3b8; display:flex; justify-content:space-between;">
        <span>🔌 DÂY NỐI VÀO (${inEdges.length}) & RA (${outEdges.length})</span>
        ${(inEdges.length + outEdges.length) > 0 ? `<span style="color:#f87171; cursor:pointer;" onclick="disconnectAllWfNodeEdges('${node.id}')">Ngắt tất cả</span>` : ''}
      </div>
      ${inEdges.length ? inEdges.map(e => {
        const up = wf.nodes.find(x => x.id === e.source_node_id);
        const isTxt = e.target_handle === "input_2" || e.edge_type === "text";
        return `
          <div style="display:flex; align-items:center; justify-content:space-between; background:#111827; padding:4px 8px; border-radius:6px; font-size:10.5px;">
            <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${isTxt ? '📝' : '🖼️'} Từ: <b style="color:#f8fafc;">${_wfEscHtml((up && up.label) || e.source_node_id)}</b></span>
            <button class="wf-node-mini-btn danger" style="width:18px; height:18px;" onclick="removeWfEdgeByNodes('${e.source_node_id}', '${node.id}', '${e.target_handle || ''}')" title="Gỡ dây nối này">✕</button>
          </div>
        `;
      }).join("") : `<div style="font-size:10px; color:#64748b;">Chưa có dây nào nối vào Node này.</div>`}
    </div>
  `;
}

function onWfInspFieldChange(field, val) {
  if (field === false) return;
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === WF_STATE.selectedNodeId);
  if (!node) return;
  if (!node.config) node.config = {};
  if (field === "label") {
    node.label = val;
    node.node_name = val;
  } else if (field === "prompt") {
    node.config.prompt = val;
    node.prompt = val;
    if (node.node_type === "text") node.config.text = val;
    if (node.node_type === "note") node.config.note = val;
    if (node.node_type === "textAppend") node.config.suffix = val;
  } else if (field === "file_path") {
    node.config.file_path = val;
    node.config.result_path = val;
    node.config.reference_images = val ? [val] : [];
    node.config.status = val ? "done" : "idle";
  } else {
    node.config[field] = val;
  }
  renderWorkflowCanvas();
}


// ── CHỌN FILE ẢNH / VIDEO TỪ MÁY TÍNH HOẶC KHO 176 SẢN PHẨM + NV1..NV5 ──
async function pickFileForWfNode(nodeId, multiple = false) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return;
  if (!node.config) node.config = {};
  const ntype = (node.node_type || "").toLowerCase();

  try {
    const fileType = (ntype === "video" || node.config.mode === "video") ? "video" : "image";
    const r = await fetch(`/api/pick_file?kind=${fileType}`).then(x => x.json());
    if (r.ok && (r.path || (r.paths && r.paths.length))) {
      wfPushHistory();
      const paths = (r.paths && r.paths.length) ? r.paths : [r.path];
      if (multiple || ntype === "references") {
        const existing = Array.isArray(node.config.reference_images) ? node.config.reference_images : [];
        node.config.reference_images = [...new Set([...existing, ...paths])];
        node.config.file_path = node.config.reference_images[0] || "";
        node.config.result_path = node.config.file_path;
      } else {
        const chosen = paths[0];
        node.config.file_path = chosen;
        node.config.result_path = chosen;
        node.config.reference_images = [chosen];
        node.local_path = chosen;
        if (_isVideoFile(chosen) && ntype === "image") {
          node.node_type = "video";
          node.config.mode = "video";
        }
      }
      node.config.status = "done";
      renderWorkflowCanvas();
      renderWfInspector();
      await saveCurrentWorkflowToDisk(true);
      if (typeof toast === "function") toast(`📂 Đã nạp file vào Node "${node.label}"!`, "ok");
    }
  } catch (e) {
    if (typeof toast === "function") toast("Lỗi mở hộp thoại chọn file: " + e.message, "err");
  }
}

async function openWfMediaLibraryPicker(targetNodeId = null) {
  WF_STATE.mediaPickerTargetNodeId = targetNodeId || WF_STATE.selectedNodeId || null;
  openModal("modalWfMediaPicker");
  const body = document.getElementById("wfMediaPickerBody");
  if (!body) return;
  body.innerHTML = `<div style="padding:24px; text-align:center; color:#94a3b8;">⏳ Đang tải Kho Nhân Vật (NV1–NV5), Kho 176 Sản Phẩm và Ảnh 2K / Video đã tạo...</div>`;

  try {
    const [ovRes, wfListRes] = await Promise.all([
      fetch("/api/studio/overview").then(r => r.json()).catch(() => ({})),
      fetch("/api/workflows/list").then(r => r.json()).catch(() => ({ workflows: [] })),
    ]);

    const chars = ovRes.characters || WF_STATE.characters || [];
    const prods = (ovRes.catalog_products || ovRes.products || []).slice(0, 60);

    const charCardsHtml = chars.map(c => {
      const imgPath = c.default_image_path || c.image_path || (c.images && c.images[0]) || "";
      const imgUrl = _getMediaUrlForWfPath(imgPath);
      if (!imgPath) return "";
      return `
        <div class="wf-media-pick-card" onclick="assignMediaToWfNode('${encodeURIComponent(imgPath)}', 'image', '${_wfEscHtml(c.name || c.id)}')">
          <img src="${imgUrl}" style="width:100%; height:130px; object-fit:cover; border-radius:7px; background:#05080f;" />
          <div style="font-size:11px; font-weight:800; color:#f8fafc; margin-top:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">👤 ${_wfEscHtml(c.name || c.id)}</div>
          <div style="font-size:9.5px; color:#a3e635;">Nhân vật chuẩn 2K</div>
        </div>
      `;
    }).join("");

    const prodCardsHtml = prods.map(p => {
      const imgPath = p.image_path || (p.images && p.images[0]) || "";
      const imgUrl = _getMediaUrlForWfPath(imgPath);
      if (!imgPath) return "";
      return `
        <div class="wf-media-pick-card" onclick="assignMediaToWfNode('${encodeURIComponent(imgPath)}', 'image', '${_wfEscHtml(p.name || p.product_id)}')">
          <img src="${imgUrl}" style="width:100%; height:120px; object-fit:cover; border-radius:7px; background:#05080f;" />
          <div style="font-size:10.5px; font-weight:700; color:#e2e8f0; margin-top:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">🛍️ ${_wfEscHtml(p.name || p.product_id)}</div>
          <div style="font-size:9.5px; color:#38bdf8;">Mã: ${_wfEscHtml(p.product_id || '')}</div>
        </div>
      `;
    }).join("");

    const wf = _getWfBody();
    const curMediaNodes = (wf.nodes || []).filter(n => n.config && (n.config.result_path || n.config.file_path));
    const curAssetsHtml = curMediaNodes.map(n => {
      const p = n.config.result_path || n.config.file_path || "";
      const url = _getMediaUrlForWfPath(p);
      const isV = _isVideoFile(p);
      return `
        <div class="wf-media-pick-card" onclick="assignMediaToWfNode('${encodeURIComponent(p)}', '${isV ? 'video' : 'image'}', '${_wfEscHtml(n.label || n.id)}')">
          ${isV
            ? `<video src="${url}" muted loop autoplay playsinline style="width:100%; height:120px; object-fit:cover; border-radius:7px; background:#05080f;"></video>`
            : `<img src="${url}" style="width:100%; height:120px; object-fit:cover; border-radius:7px; background:#05080f;" />`
          }
          <div style="font-size:10.5px; font-weight:700; color:#f8fafc; margin-top:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${isV ? '🎬' : '🖼️'} ${_wfEscHtml(n.label || n.id)}</div>
          <div style="font-size:9.5px; color:#c084fc;">Trong Sơ đồ hiện tại</div>
        </div>
      `;
    }).join("");

    body.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div style="display:flex; align-items:center; justify-content:space-between; background:rgba(99,102,241,0.12); border:1px solid rgba(99,102,241,0.3); border-radius:9px; padding:10px 14px;">
          <div style="font-size:12px; color:#e2e8f0;">
            ${WF_STATE.mediaPickerTargetNodeId
              ? `🎯 Đang chọn Media để nạp vào Node: <b style="color:#a3e635;">${_wfEscHtml(WF_STATE.mediaPickerTargetNodeId)}</b>`
              : `➕ Nhấp vào bất kỳ Nhân vật / Sản phẩm / Video nào bên dưới để <b>tạo ngay Node mới</b> trên bàn cờ!`
            }
          </div>
          <button class="btn btn-xs btn-primary" onclick="closeModal('modalWfMediaPicker'); pickFileForWfNode('${WF_STATE.mediaPickerTargetNodeId || WF_STATE.selectedNodeId || ''}', false)">📂 Chọn File Ngoài Máy Tính</button>
        </div>

        ${curAssetsHtml ? `
          <div>
            <div style="font-size:12px; font-weight:800; color:#c084fc; margin-bottom:8px;">✨ ẢNH 2K & VIDEO TRONG WORKFLOW HIỆN TẠI</div>
            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(145px, 1fr)); gap:10px;">${curAssetsHtml}</div>
          </div>
        ` : ''}

        <div>
          <div style="font-size:12px; font-weight:800; color:#a3e635; margin-bottom:8px;">👤 KHO NHÂN VẬT AI CHUẨN (NV1 – NV5 & CHARACTER SHEET)</div>
          <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(145px, 1fr)); gap:10px;">
            ${charCardsHtml || `<div style="color:#64748b; font-size:11px;">Chưa có nhân vật.</div>`}
          </div>
        </div>

        <div>
          <div style="font-size:12px; font-weight:800; color:#38bdf8; margin-bottom:8px;">🛍️ KHO 176 SẢN PHẨM & BỘ ĐỒ THỜI TRANG</div>
          <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(135px, 1fr)); gap:10px; max-height:340px; overflow-y:auto; padding-right:4px;">
            ${prodCardsHtml || `<div style="color:#64748b; font-size:11px;">Chưa có sản phẩm trong kho.</div>`}
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<div style="color:#f87171; padding:16px;">Lỗi tải kho Media: ${_wfEscHtml(err.message)}</div>`;
  }
}

function assignMediaToWfNode(encodedPath, mediaType = "image", titleHint = "") {
  const path = decodeURIComponent(encodedPath || "");
  if (!path) return;
  const wf = _getWfBody();
  wfPushHistory();
  const targetId = WF_STATE.mediaPickerTargetNodeId;
  const node = targetId ? wf.nodes.find(n => n.id === targetId) : null;

  if (node) {
    if (!node.config) node.config = {};
    if ((node.node_type || "").toLowerCase() === "references") {
      const arr = Array.isArray(node.config.reference_images) ? node.config.reference_images : [];
      if (!arr.includes(path)) arr.push(path);
      node.config.reference_images = arr;
      node.config.file_path = arr[0] || path;
      node.config.result_path = node.config.file_path;
    } else {
      node.config.file_path = path;
      node.config.result_path = path;
      node.config.reference_images = [path];
      node.local_path = path;
    }
    node.config.status = "done";
    if (titleHint && (!node.label || node.label.includes("Đầu Vào"))) {
      node.label = `${mediaType === 'video' ? '🎬' : '🖼️'} ${titleHint}`;
    }
    if (typeof toast === "function") toast(`✅ Đã gán "${titleHint || path.split(/[\\/]/).pop()}" vào Node!`, "ok");
  } else {
    addNodeToActiveWorkflow(mediaType === "video" ? "video" : "image", {
      filePath: path,
      label: titleHint ? `${mediaType === 'video' ? '🎬' : '🖼️'} ${titleHint}` : undefined,
    });
  }
  closeModal("modalWfMediaPicker");
  renderWorkflowCanvas();
  renderWfInspector();
  saveCurrentWorkflowToDisk(true);
}

// ── MODAL XEM FULL NỘI DUNG NODE (FULL TEXT / ẢNH 2K / VIDEO 1080P — #modalWfNodeFullViewer) ──
function openWfNodeFullViewer(nodeId) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === (nodeId || WF_STATE.selectedNodeId));
  if (!node) return;
  WF_STATE.fullViewerNodeId = node.id;
  openModal("modalWfNodeFullViewer");

  const titleEl = document.getElementById("wfFullViewerTitle");
  const bodyEl = document.getElementById("wfFullViewerBody");
  if (!bodyEl) return;

  const cfg = node.config || {};
  const ntype = (node.node_type || "generate").toLowerCase();
  const mediaPath = cfg.result_path || cfg.file_path || "";
  const mediaUrl = _getMediaUrlForWfPath(mediaPath);
  const isVid = cfg.mode === "video" || ntype === "video" || _isVideoFile(mediaPath);
  const mergedPrompt = resolveWfNodeMergedText(node.id);
  const refList = _collectUpstreamMediaPaths(node.id);

  if (titleEl) {
    titleEl.innerHTML = `🔍 XEM FULL NODE: <span style="color:#a3e635;">${_wfEscHtml(node.label || node.id)}</span> <span style="font-size:11px; color:#94a3b8; font-weight:600;">(@${_wfEscHtml(cfg.slug || node.id)} • ${_wfEscHtml(ntype.toUpperCase())})</span>`;
  }

  bodyEl.innerHTML = `
    <div style="display:grid; grid-template-columns:${mediaUrl ? '1.25fr 1fr' : '1fr'}; gap:18px; align-items:start;">
      ${mediaUrl ? `
        <div style="background:#05080f; border:1px solid rgba(255,255,255,0.12); border-radius:12px; padding:12px; display:flex; flex-direction:column; align-items:center; gap:10px;">
          ${isVid
            ? `<video src="${mediaUrl}" controls autoplay loop style="width:100%; max-height:66vh; border-radius:8px; background:#000;"></video>`
            : `<img src="${mediaUrl}" style="width:100%; max-height:66vh; object-fit:contain; border-radius:8px;" />`
          }
          <div style="width:100%; display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; font-size:11px; color:#94a3b8;">
            <span style="font-family:Consolas,monospace; word-break:break-all;">📁 ${_wfEscHtml(mediaPath)}</span>
            <div style="display:flex; gap:6px;">
              <a href="${mediaUrl}" download class="btn btn-xs btn-primary" style="text-decoration:none;">⬇️ Tải File Gốc (2K/1080p)</a>
              ${isVid ? `
                <button class="btn btn-xs" style="background:rgba(244,114,182,0.2); color:#f472b6; border:1px solid rgba(244,114,182,0.4); font-weight:800;" onclick="closeModal('modalWfNodeFullViewer'); extractWfVideoEndFrameToNode('${node.id}')">📸 Tách Frame Cuối ➔ Node Ảnh</button>
                <button class="btn btn-xs btn-success" onclick="addWfNodeVideoToTimeline('${node.id}')">🎞️ + Vào Timeline MP4</button>
              ` : ''}
            </div>
          </div>
        </div>
      ` : ''}

      <div style="display:flex; flex-direction:column; gap:12px;">
        <div style="background:#0d1322; border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px;">
          <div style="font-size:11.5px; font-weight:800; color:#a3e635; margin-bottom:6px;">✍️ NỘI DUNG GỐC CỦA NODE NÀY (Chỉnh sửa trực tiếp bên dưới):</div>
          <textarea id="txtWfFullViewerPrompt" rows="7"
                    style="width:100%; background:#070a12; color:#f8fafc; border:1px solid rgba(255,255,255,0.16); border-radius:8px; padding:10px; font-size:12.5px; line-height:1.55;"
                    oninput="onWfFullViewerPromptEdit('${node.id}', this.value)">${_wfEscHtml(cfg.prompt || cfg.text || cfg.note || cfg.suffix || '')}</textarea>
        </div>

        ${mergedPrompt && mergedPrompt !== (cfg.prompt || cfg.text || '') ? `
          <div style="background:rgba(56,189,248,0.08); border:1px solid rgba(56,189,248,0.3); border-radius:10px; padding:12px;">
            <div style="font-size:11.5px; font-weight:800; color:#38bdf8; margin-bottom:6px;">🔀 TỔNG HỢP VĂN BẢN / PROMPT THỰC TẾ KHI CHẠY (Đã gộp các dây nối vào):</div>
            <div style="font-size:12px; color:#e2e8f0; white-space:pre-wrap; line-height:1.55; max-height:220px; overflow-y:auto;">${_wfEscHtml(mergedPrompt)}</div>
          </div>
        ` : ''}

        ${refList.length ? `
          <div style="background:#0d1322; border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px;">
            <div style="font-size:11.5px; font-weight:800; color:#f472b6; margin-bottom:8px;">🖼️ DANH SÁCH ẢNH / VIDEO THAM CHIẾU ĐẦU VÀO (${refList.length} File):</div>
            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(110px, 1fr)); gap:8px;">
              ${refList.map((rp, idx) => {
                const ru = _getMediaUrlForWfPath(rp);
                const rv = _isVideoFile(rp);
                return `
                  <div style="background:#060911; border:1px solid rgba(255,255,255,0.12); border-radius:7px; padding:4px; text-align:center;">
                    <div style="font-size:9px; font-weight:800; color:#a3e635; margin-bottom:2px;">REF #${idx + 1}</div>
                    ${rv
                      ? `<video src="${ru}" muted loop autoplay playsinline style="width:100%; height:90px; object-fit:cover; border-radius:5px;"></video>`
                      : `<img src="${ru}" style="width:100%; height:90px; object-fit:cover; border-radius:5px;" />`
                    }
                    <div style="font-size:9.5px; color:#cbd5e1; margin-top:3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${_wfEscHtml(rp.split(/[\\/]/).pop())}</div>
                  </div>
                `;
              }).join("")}
            </div>
          </div>
        ` : ''}
      </div>
    </div>
  `;
}

function onWfFullViewerPromptEdit(nodeId, val) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return;
  if (!node.config) node.config = {};
  node.config.prompt = val;
  node.prompt = val;
  if (node.node_type === "text") node.config.text = val;
  if (node.node_type === "note") node.config.note = val;
  if (node.node_type === "textAppend") node.config.suffix = val;
  renderWorkflowCanvas();
  if (WF_STATE.selectedNodeId === nodeId) renderWfInspector();
}

function runNodeFromFullViewer() {
  const nid = WF_STATE.fullViewerNodeId || WF_STATE.selectedNodeId;
  closeModal("modalWfNodeFullViewer");
  if (nid) runWorkflowExecution(nid);
}

// ── TÁCH FRAME CUỐI VIDEO THÀNH NODE ẢNH 2K ĐỂ NỐI TIẾP PHÂN CẢNH SAU ──
async function extractWfVideoEndFrameToNode(nodeId) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node || !node.config) return;
  const videoPath = node.config.result_path || node.config.file_path || "";
  if (!videoPath) {
    if (typeof toast === "function") toast("Node này chưa có file Video để tách frame cuối!", "err");
    return;
  }
  try {
    if (typeof toast === "function") toast("📸 Đang tách Frame cuối chuẩn 2K từ Video...", "info");
    const r = await fetch("/api/workflows/extract_end_frame", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_path: videoPath, wf_id: WF_STATE.currentWfId || "wf" }),
    }).then(x => x.json());

    const fPath = r.frame_path || r.output_path || r.path;
    if (!r.ok || !fPath) {
      throw new Error(r.error || "Không tách được frame cuối");
    }
    wfPushHistory();
    const newImgNode = addNodeToActiveWorkflow("image", {
      x: Number(node.pos_x || 0) + 340,
      y: Number(node.pos_y || 0),
      filePath: fPath,
      label: `📸 Frame Cuối — ${node.label || node.id}`,
    });
    if (newImgNode) {
      _createWfEdgeBetween(node.id, "output_1", newImgNode.id, "input_1");
    }
    if (typeof toast === "function") toast("✅ Đã tách Frame cuối thành Node Ảnh 2K mới để nối sang Cảnh tiếp theo!", "ok");
  } catch (e) {
    if (typeof toast === "function") toast("Lỗi tách Frame cuối: " + e.message, "err");
  }
}

// ── KỊCH BẢN ĐA CẢNH ➔ TỰ ĐỘNG RẢI SƠ ĐỒ NODE (#modalWfScriptToNodes) ──
function openWfScriptToNodesModal() {
  openModal("modalWfScriptToNodes");
  const txt = document.getElementById("txtWfScriptInput");
  if (txt && !txt.value.trim()) {
    insertSampleVietnameseSceneScript();
  }
}

function insertSampleVietnameseSceneScript() {
  const txt = document.getElementById("txtWfScriptInput");
  if (!txt) return;
  txt.value = [
    "Cảnh 1: Người mẫu nữ Việt Nam mặc bộ đồ Look 1 đứng trước gương thang máy hiện đại, ánh sáng sang trọng, cầm điện thoại quay mirror selfie nhẹ nhàng.",
    "Cảnh 2: Cửa thang máy mở ra, người mẫu bước ra hành lang sảnh lớn với thần thái tự tin, bộ trang phục chuyển mượt sang Look 2 năng động theo nhịp nhạc.",
    "Cảnh 3: Cận cảnh chi tiết chất liệu vải cao cấp và phụ kiện túi xách, người mẫu xoay nhẹ một vòng kết thúc video lookbook cuốn hút."
  ].join("\n\n");
}

async function aiGenerateSceneScriptForWorkflow() {
  const txt = document.getElementById("txtWfScriptInput");
  if (!txt) return;
  const seed = txt.value.trim() || "Video thời trang biến hình 3 bộ trang phục sang trọng cho TikTok 9:16";
  try {
    if (typeof toast === "function") toast("🤖 Đang nhờ AI CLIProxy biên tập kịch bản phân cảnh...", "info");
    const r = await fetch("/api/workflows/test_prompt_ai", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "gpt-5.4",
        prompt: `Hãy viết kịch bản gồm 3 cảnh ngắn gọn (mỗi cảnh trên 1 đoạn bắt đầu bằng "Cảnh 1:", "Cảnh 2:", "Cảnh 3:") để tạo video AI thời trang/sản phẩm 9:16 từ ý tưởng sau:\n${seed}`,
      }),
    }).then(x => x.json());
    const outTxt = r.text || r.result_text;
    if (r.ok && outTxt) {
      txt.value = outTxt;
      if (typeof toast === "function") toast("✨ AI đã viết xong kịch bản đa cảnh!", "ok");
    }
  } catch (e) {
    if (typeof toast === "function") toast("Lỗi gọi AI viết kịch bản: " + e.message, "err");
  }
}

function applyScriptToWorkflowNodes() {
  const txt = document.getElementById("txtWfScriptInput");
  const modeEl = document.getElementById("selWfScriptMode");
  const flowEl = document.getElementById("selWfScriptFlowType");
  const ratioEl = document.getElementById("selWfScriptAspectRatio");
  if (!txt || !txt.value.trim()) {
    if (typeof toast === "function") toast("Hãy nhập nội dung kịch bản trước!", "err");
    return;
  }

  const rawLines = txt.value
    .split(/\n+/)
    .map(s => s.trim())
    .filter(Boolean);
  if (!rawLines.length) return;

  const wf = _getWfBody();
  wfPushHistory();

  if (modeEl && modeEl.value === "replace") {
    wf.nodes = [];
    wf.edges = [];
    wf.groups = [];
  }

  const flowType = flowEl ? flowEl.value : "prompt_img_vid";
  const aspect = ratioEl ? ratioEl.value : "9:16";
  const baseY = wf.nodes.length ? Math.max(...wf.nodes.map(n => Number(n.pos_y || 0))) + 380 : 120;

  const charNode = addNodeToActiveWorkflow("image", {
    x: 80,
    y: baseY + 60,
    label: "👤 Ảnh Nhân Vật Tham Chiếu",
  });
  const prodNode = addNodeToActiveWorkflow("image", {
    x: 80,
    y: baseY + 380,
    label: "🛍️ Ảnh Sản Phẩm / Trang Phục",
  });

  rawLines.forEach((sceneText, idx) => {
    const rowY = baseY + idx * 340;
    const pNode = addNodeToActiveWorkflow("prompt", {
      x: 430,
      y: rowY,
      prompt: sceneText,
      label: `📝 Prompt Cảnh ${idx + 1}`,
    });

    if (flowType === "prompt_img_vid") {
      const imgGen = addNodeToActiveWorkflow("generate", {
        x: 790,
        y: rowY,
        mode: "image",
        aspect_ratio: aspect,
        label: `🖼️ Tạo Ảnh 2K — Cảnh ${idx + 1}`,
      });
      const vidGen = addNodeToActiveWorkflow("generate", {
        x: 1160,
        y: rowY,
        mode: "video",
        aspect_ratio: aspect,
        label: `🎬 Tạo Video 1080p — Cảnh ${idx + 1}`,
      });
      if (charNode && imgGen) _createWfEdgeBetween(charNode.id, "output_1", imgGen.id, "input_1");
      if (prodNode && imgGen) _createWfEdgeBetween(prodNode.id, "output_1", imgGen.id, "input_1");
      if (pNode && imgGen) _createWfEdgeBetween(pNode.id, "output_1", imgGen.id, "input_2");
      if (imgGen && vidGen) _createWfEdgeBetween(imgGen.id, "output_1", vidGen.id, "input_1");
      if (prodNode && vidGen) _createWfEdgeBetween(prodNode.id, "output_1", vidGen.id, "input_1");
      if (pNode && vidGen) _createWfEdgeBetween(pNode.id, "output_1", vidGen.id, "input_2");
    } else if (flowType === "prompt_vid") {
      const vidGen = addNodeToActiveWorkflow("generate", {
        x: 820,
        y: rowY,
        mode: "video",
        aspect_ratio: aspect,
        label: `🎬 Tạo Video 1080p — Cảnh ${idx + 1}`,
      });
      if (charNode && vidGen) _createWfEdgeBetween(charNode.id, "output_1", vidGen.id, "input_1");
      if (prodNode && vidGen) _createWfEdgeBetween(prodNode.id, "output_1", vidGen.id, "input_1");
      if (pNode && vidGen) _createWfEdgeBetween(pNode.id, "output_1", vidGen.id, "input_2");
    } else {
      const imgGen = addNodeToActiveWorkflow("generate", {
        x: 820,
        y: rowY,
        mode: "image",
        aspect_ratio: aspect,
        label: `🖼️ Tạo Ảnh 2K — Cảnh ${idx + 1}`,
      });
      if (charNode && imgGen) _createWfEdgeBetween(charNode.id, "output_1", imgGen.id, "input_1");
      if (prodNode && imgGen) _createWfEdgeBetween(prodNode.id, "output_1", imgGen.id, "input_1");
      if (pNode && imgGen) _createWfEdgeBetween(pNode.id, "output_1", imgGen.id, "input_2");
    }
  });

  closeModal("modalWfScriptToNodes");
  renderWorkflowCanvas();
  setTimeout(() => fitWorkflowCanvasView(), 80);
  if (typeof toast === "function") toast(`📜 Đã tự động rải ${rawLines.length} phân cảnh thành sơ đồ Node chuẩn!`, "ok");
}

// ── THỨ TỰ CHẠY NODE (TOPOLOGICAL RUN ORDER — #modalWfRunOrder) ──
function _computeTopologicalNodeOrder() {
  const wf = _getWfBody();
  const nodes = wf.nodes || [];
  const edges = wf.edges || [];
  const inDegree = {};
  const adj = {};
  nodes.forEach(n => {
    inDegree[n.id] = 0;
    adj[n.id] = [];
  });
  edges.forEach(e => {
    if (adj[e.source_node_id] && inDegree[e.target_node_id] !== undefined) {
      adj[e.source_node_id].push(e.target_node_id);
      inDegree[e.target_node_id]++;
    }
  });
  const q = nodes.filter(n => inDegree[n.id] === 0).map(n => n.id);
  const orderedIds = [];
  while (q.length) {
    const u = q.shift();
    orderedIds.push(u);
    (adj[u] || []).forEach(v => {
      inDegree[v]--;
      if (inDegree[v] === 0) q.push(v);
    });
  }
  nodes.forEach(n => {
    if (!orderedIds.includes(n.id)) orderedIds.push(n.id);
  });
  return orderedIds.map(id => nodes.find(n => n.id === id)).filter(Boolean);
}

function openWfRunOrderModal() {
  openModal("modalWfRunOrder");
  const listEl = document.getElementById("wfRunOrderListContainer");
  const warnEl = document.getElementById("wfRunOrderWarningBox");
  if (!listEl) return;

  const ordered = _computeTopologicalNodeOrder();
  const wf = _getWfBody();
  const disconnectedGen = ordered.filter(n => {
    const nt = (n.node_type || "").toLowerCase();
    if (!["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(nt)) return false;
    const hasIn = wf.edges.some(e => e.target_node_id === n.id);
    const hasOwnPrompt = Boolean(n.config && (n.config.prompt || "").trim());
    return !hasIn && !hasOwnPrompt;
  });

  if (warnEl) {
    if (disconnectedGen.length) {
      warnEl.style.display = "block";
      warnEl.innerHTML = `⚠️ Phát hiện <b>${disconnectedGen.length} Node Tạo AI</b> chưa được nối dây Đầu vào và chưa có Prompt riêng: ${disconnectedGen.map(x => `<b>${_wfEscHtml(x.label || x.id)}</b>`).join(", ")}.`;
    } else {
      warnEl.style.display = "none";
    }
  }

  listEl.innerHTML = ordered.map((n, i) => {
    const cfg = n.config || {};
    const ntype = (n.node_type || "").toLowerCase();
    const checked = !cfg.disabled;
    return `
      <label style="display:flex; align-items:center; justify-content:space-between; background:#0d1322; border:1px solid rgba(255,255,255,0.09); border-radius:8px; padding:8px 12px; cursor:pointer;">
        <div style="display:flex; align-items:center; gap:10px;">
          <input type="checkbox" class="wf-run-order-chk" value="${n.id}" ${checked ? 'checked' : ''} />
          <span style="background:rgba(163,230,53,0.16); color:#a3e635; font-size:10.5px; font-weight:800; padding:2px 7px; border-radius:5px;">Bước #${i + 1}</span>
          <div>
            <div style="font-size:12px; font-weight:800; color:#f8fafc;">${_wfEscHtml(n.label || n.id)}</div>
            <div style="font-size:10px; color:#94a3b8;">Loại: ${_wfEscHtml(ntype.toUpperCase())} • @${_wfEscHtml(cfg.slug || n.id)}</div>
          </div>
        </div>
        <span style="font-size:10.5px; font-weight:700; color:${cfg.status === 'done' ? '#22c55e' : '#94a3b8'};">${_wfEscHtml((cfg.status || 'idle').toUpperCase())}</span>
      </label>
    `;
  }).join("");
}

function toggleAllWfRunOrderItems(state) {
  document.querySelectorAll(".wf-run-order-chk").forEach(chk => {
    chk.checked = Boolean(state);
  });
}

function confirmAndRunOrderedWfNodes() {
  const selectedIds = Array.from(document.querySelectorAll(".wf-run-order-chk:checked")).map(el => el.value);
  closeModal("modalWfRunOrder");
  if (!selectedIds.length) {
    if (typeof toast === "function") toast("Chưa chọn Node nào để chạy!", "err");
    return;
  }
  runWorkflowExecution(null, selectedIds);
}

// ── THANH TIMELINE GHÉP CÁC SCENE VIDEO & XUẤT MP4 HOÀN CHỈNH (#wfTimelineDock) ──
function toggleWfTimelineDock(forceOpen = null) {
  const dock = document.getElementById("wfTimelineDock");
  if (!dock) return;
  const isOpen = forceOpen !== null ? forceOpen : dock.style.display === "none";
  dock.style.display = isOpen ? "flex" : "none";
  if (isOpen) renderWfTimelineDock();
}

function renderWfTimelineDock() {
  const wf = _getWfBody();
  if (!Array.isArray(wf.timeline)) wf.timeline = [];
  const badge = document.getElementById("wfTimelineCountBadge");
  const sumEl = document.getElementById("wfTimelineSummaryText");
  const track = document.getElementById("wfTimelineTrack");

  if (badge) badge.textContent = String(wf.timeline.length);
  const totalSec = wf.timeline.reduce((acc, c) => acc + (parseFloat(c.duration) || 8), 0);
  if (sumEl) sumEl.textContent = `${wf.timeline.length} clip • ~${totalSec}s`;
  if (!track) return;

  if (!wf.timeline.length) {
    track.innerHTML = `
      <div style="color:#64748b; font-size:11.5px; padding:18px; display:flex; align-items:center; gap:10px;">
        <span>🎞️ Chưa có clip nào trên Timeline.</span>
        <button class="btn btn-xs btn-primary" onclick="addAllCompletedVideoNodesToTimeline()">📥 Tự động gom tất cả Node Video đã xong vào Timeline</button>
      </div>
    `;
    return;
  }

  track.innerHTML = wf.timeline.map((clip, idx) => {
    const vUrl = _getMediaUrlForWfPath(clip.video_path || "");
    return `
      <div style="min-width:175px; max-width:175px; background:#0d1322; border:1px solid rgba(168,85,247,0.35); border-radius:9px; padding:6px; display:flex; flex-direction:column; gap:4px; position:relative; flex-shrink:0;">
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:10px; font-weight:800; color:#e9d5ff;">
          <span>🎬 Cảnh #${idx + 1} (${_wfEscHtml(String(clip.duration || '8s'))})</span>
          <button class="wf-node-mini-btn danger" style="width:18px; height:18px;" onclick="removeWfTimelineClip(${idx})" title="Xoá khỏi Timeline">✕</button>
        </div>
        <video src="${vUrl}" muted loop autoplay playsinline style="width:100%; height:78px; object-fit:cover; border-radius:6px; background:#000; cursor:pointer;" onclick="window.open('${vUrl}', '_blank')"></video>
        <div style="font-size:10px; color:#cbd5e1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${_wfEscHtml(clip.label || clip.node_id || '')}</div>
      </div>
    `;
  }).join("");
}

function addWfNodeVideoToTimeline(nodeId) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node || !node.config) return;
  const vPath = node.config.result_path || node.config.file_path || "";
  if (!vPath) {
    if (typeof toast === "function") toast("Node này chưa có file Video kết quả!", "err");
    return;
  }
  if (!Array.isArray(wf.timeline)) wf.timeline = [];
  wf.timeline.push({
    clip_id: `clip_${Date.now().toString(36)}_${wf.timeline.length + 1}`,
    node_id: node.id,
    label: node.label || node.id,
    video_path: vPath,
    duration: node.config.duration || "8s",
  });
  toggleWfTimelineDock(true);
  renderWfTimelineDock();
  if (typeof toast === "function") toast(`🎞️ Đã thêm "${node.label}" vào Thanh Timeline!`, "ok");
}

function addAllCompletedVideoNodesToTimeline() {
  const wf = _getWfBody();
  if (!Array.isArray(wf.timeline)) wf.timeline = [];
  let added = 0;
  (wf.nodes || []).forEach(n => {
    const cfg = n.config || {};
    const p = cfg.result_path || cfg.file_path || "";
    if (!p || !_isVideoFile(p)) return;
    if (!wf.timeline.some(c => c.video_path === p)) {
      wf.timeline.push({
        clip_id: `clip_${Date.now().toString(36)}_${wf.timeline.length + 1}`,
        node_id: n.id,
        label: n.label || n.id,
        video_path: p,
        duration: cfg.duration || "8s",
      });
      added++;
    }
  });
  toggleWfTimelineDock(true);
  renderWfTimelineDock();
  if (typeof toast === "function") toast(`📥 Đã gom ${added} Video vào Thanh Timeline!`, "ok");
}

function removeWfTimelineClip(idx) {
  const wf = _getWfBody();
  if (!Array.isArray(wf.timeline)) return;
  wf.timeline.splice(idx, 1);
  renderWfTimelineDock();
}

function clearWfTimelineClips() {
  const wf = _getWfBody();
  wf.timeline = [];
  renderWfTimelineDock();
}

function playWfTimelineSequencePreview() {
  const wf = _getWfBody();
  const clips = wf.timeline || [];
  if (!clips.length) {
    if (typeof toast === "function") toast("Chưa có clip nào trên Timeline để phát thử!", "err");
    return;
  }
  const firstNode = wf.nodes.find(n => n.id === clips[0].node_id);
  if (firstNode) {
    openWfNodeFullViewer(firstNode.id);
  } else {
    window.open(_getMediaUrlForWfPath(clips[0].video_path), "_blank");
  }
}

async function exportWfTimelineToMp4() {
  const wf = _getWfBody();
  if (!wf.timeline || !wf.timeline.length) {
    addAllCompletedVideoNodesToTimeline();
  }
  if (!wf.timeline || !wf.timeline.length) {
    if (typeof toast === "function") toast("Chưa có clip Video nào để ghép MP4!", "err");
    return;
  }
  try {
    if (typeof toast === "function") toast("🎬 Đang ghép nối các Scene trên Timeline thành Video MP4 hoàn chỉnh...", "info");
    await saveCurrentWorkflowToDisk(true);
    const r = await fetch("/api/workflows/export_timeline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        wf_id: WF_STATE.currentWfId || "workflow_timeline",
        wf_name: wf.name || "workflow_timeline",
        clips: wf.timeline,
      }),
    }).then(x => x.json());

    const outP = r.output_path || r.path;
    if (!r.ok || !outP) {
      throw new Error(r.error || "Ghép MP4 thất bại");
    }
    if (typeof toast === "function") toast(`✅ Đã xuất Video Final MP4 thành công: ${outP.split(/[\\/]/).pop()}`, "ok");
    const mediaUrl = _getMediaUrlForWfPath(outP);
    if (mediaUrl) window.open(mediaUrl, "_blank");
  } catch (e) {
    if (typeof toast === "function") toast("Lỗi xuất MP4 Timeline: " + e.message, "err");
  }
}

// ── TRUNG TÂM TẠO SỐ LƯỢNG LỚN (BULK / BATCH GENERATOR — #modalWfBatchGenerator) ──
async function openWfBatchGeneratorModal(preferNodeId = null) {
  openModal("modalWfBatchGenerator");
  const body = document.getElementById("wfBatchGeneratorBody");
  if (!body) return;

  if (!WF_STATE.batchCatalogProducts || !WF_STATE.batchCatalogProducts.length) {
    try {
      const ov = await fetch("/api/studio/overview").then(r => r.json()).catch(() => ({}));
      WF_STATE.batchCatalogProducts = (ov.catalog_products || ov.products || []).slice(0, 60);
    } catch (_) {
      WF_STATE.batchCatalogProducts = [];
    }
  }

  const wf = _getWfBody();
  const imgNodes = (wf.nodes || []).filter(n => ["image", "references"].includes((n.node_type || "").toLowerCase()));
  const promptNodes = (wf.nodes || []).filter(n => ["prompt", "text", "generate"].includes((n.node_type || "").toLowerCase()));

  if (preferNodeId) {
    const pNode = wf.nodes.find(n => n.id === preferNodeId);
    if (pNode && ["image", "references"].includes((pNode.node_type || "").toLowerCase())) {
      WF_STATE.batchMode = "product_swap";
      WF_STATE.batchTargetImageNodeId = pNode.id;
    } else if (pNode && ["prompt", "text"].includes((pNode.node_type || "").toLowerCase())) {
      WF_STATE.batchMode = "prompt_list";
      WF_STATE.batchTargetPromptNodeId = pNode.id;
    }
  }
  if (!WF_STATE.batchTargetImageNodeId && imgNodes.length) {
    const prodCandidate = imgNodes.find(n => /outfit|sản phẩm|trang phục|đồ|look|product/i.test(n.label || "")) || imgNodes[imgNodes.length - 1];
    WF_STATE.batchTargetImageNodeId = prodCandidate.id;
  }
  if (!WF_STATE.batchTargetPromptNodeId && promptNodes.length) {
    WF_STATE.batchTargetPromptNodeId = promptNodes[0].id;
  }

  renderWfBatchGeneratorModal();
}

function switchWfBatchMode(mode) {
  WF_STATE.batchMode = mode || "variations";
  renderWfBatchGeneratorModal();
}

function toggleBatchProductSelection(encodedPath) {
  const path = decodeURIComponent(encodedPath || "");
  if (!path) return;
  const idx = WF_STATE.batchSelectedFiles.indexOf(path);
  if (idx >= 0) {
    WF_STATE.batchSelectedFiles.splice(idx, 1);
  } else {
    WF_STATE.batchSelectedFiles.push(path);
  }
  renderWfBatchGeneratorModal();
}

async function pickBatchLocalFiles() {
  try {
    const r = await fetch("/api/pick_file?kind=image").then(x => x.json());
    if (r.ok && (r.paths || r.path)) {
      const list = r.paths && r.paths.length ? r.paths : [r.path];
      list.forEach(p => {
        if (p && !WF_STATE.batchSelectedFiles.includes(p)) {
          WF_STATE.batchSelectedFiles.push(p);
        }
      });
      renderWfBatchGeneratorModal();
      if (typeof toast === "function") toast(`📂 Đã thêm ${list.length} ảnh vào danh sách chạy hàng loạt!`, "ok");
    }
  } catch (e) {
    if (typeof toast === "function") toast("Lỗi chọn file: " + e.message, "err");
  }
}

function insertSampleBatchPrompts() {
  const el = document.getElementById("txtWfBatchPrompts");
  if (!el) return;
  el.value = [
    "Người mẫu mặc bộ trang phục dạo phố năng động, xoay nhẹ trước gương thang máy với ánh sáng điện ảnh 2K.",
    "Người mẫu diện thiết kế công sở thanh lịch, bước đi tự tin tại sảnh tòa nhà hiện đại, chuyển động mượt mà.",
    "Người mẫu khoe thần thái sang trọng trong bộ váy dạ hội, quay cận cảnh chất liệu vải cao cấp chuẩn lookbook."
  ].join("\n");
}

function renderWfBatchGeneratorModal() {
  const body = document.getElementById("wfBatchGeneratorBody");
  if (!body) return;
  const wf = _getWfBody();
  const mode = WF_STATE.batchMode || "variations";
  const imgNodes = (wf.nodes || []).filter(n => ["image", "references"].includes((n.node_type || "").toLowerCase()));
  const promptNodes = (wf.nodes || []).filter(n => ["prompt", "text", "generate"].includes((n.node_type || "").toLowerCase()));
  const selClusterCount = WF_STATE.selectedNodeIds ? WF_STATE.selectedNodeIds.size : 0;
  const batchHist = Array.isArray(wf.batch_history) ? wf.batch_history : [];

  body.innerHTML = `
    <div style="display:flex; flex-direction:column; gap:14px;">
      <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px;">
        <button class="btn ${mode === 'variations' ? 'btn-primary' : 'btn-outline'}"
                style="padding:10px; font-weight:800; display:flex; flex-direction:column; align-items:flex-start; gap:3px; text-align:left;"
                onclick="switchWfBatchMode('variations')">
          <span style="font-size:12.5px;">🔁 1. Chạy Lặp N Bộ Biến Thể</span>
          <span style="font-size:10px; opacity:0.85; font-weight:500;">Tạo hàng loạt N bộ kết quả 2K/1080p từ cùng sơ đồ để chọn bản đẹp nhất</span>
        </button>
        <button class="btn ${mode === 'product_swap' ? 'btn-primary' : 'btn-outline'}"
                style="padding:10px; font-weight:800; display:flex; flex-direction:column; align-items:flex-start; gap:3px; text-align:left;"
                onclick="switchWfBatchMode('product_swap')">
          <span style="font-size:12.5px;">👗 2. Thay Hàng Loạt Sản Phẩm / Đồ</span>
          <span style="font-size:10px; opacity:0.85; font-weight:500;">Giữ nguyên sơ đồ & nhân vật, tự động thay lần lượt nhiều ảnh Sản phẩm / Outfit</span>
        </button>
        <button class="btn ${mode === 'prompt_list' ? 'btn-primary' : 'btn-outline'}"
                style="padding:10px; font-weight:800; display:flex; flex-direction:column; align-items:flex-start; gap:3px; text-align:left;"
                onclick="switchWfBatchMode('prompt_list')">
          <span style="font-size:12.5px;">📝 3. Chạy Theo Danh Sách Prompt</span>
          <span style="font-size:10px; opacity:0.85; font-weight:500;">Mỗi dòng là 1 kịch bản/câu lệnh riêng, tự động chạy lần lượt từng dòng</span>
        </button>
      </div>

      <div style="background:#0b101d; border:1px solid rgba(255,255,255,0.1); border-radius:11px; padding:14px;">
        ${mode === "variations" ? `
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; align-items:center;">
            <div>
              <label style="font-size:12px; font-weight:800; color:#a3e635; display:block; margin-bottom:6px;">🔢 Số lượng bộ Video/Ảnh muốn sản xuất (N lô):</label>
              <input type="number" id="inpWfBatchRepeatCount" min="1" max="50" value="${Number(WF_STATE.batchRepeatCount || 3)}"
                     onchange="WF_STATE.batchRepeatCount = Number(this.value)"
                     style="width:100%; font-size:15px; font-weight:800; padding:8px 12px; background:#060911; color:#f8fafc; border:1px solid rgba(163,230,53,0.4); border-radius:8px;" />
            </div>
            <div style="font-size:11.5px; color:#cbd5e1; line-height:1.5;">
              💡 Hệ thống sẽ chạy toàn bộ sơ đồ <b>N lần liên tiếp</b> trên Google Flow, tự động xuất từng bộ ảnh 2K & video 1080p riêng biệt vào lịch sử Lô và thư mục <code>final_videos/</code>.
            </div>
          </div>
        ` : mode === "product_swap" ? `
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div style="display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;">
              <div style="flex:1; min-width:240px;">
                <label style="font-size:11.5px; font-weight:800; color:#38bdf8; display:block; margin-bottom:4px;">🎯 Chọn Node Ảnh Đích sẽ được thay thế Sản phẩm / Bộ đồ mỗi lượt:</label>
                <select id="selWfBatchTargetImgNode" onchange="WF_STATE.batchTargetImageNodeId = this.value" style="width:100%; font-size:12px; padding:7px;">
                  ${imgNodes.map(n => `<option value="${n.id}" ${n.id === WF_STATE.batchTargetImageNodeId ? 'selected' : ''}>🖼️ ${_wfEscHtml(n.label || n.id)} (@${_wfEscHtml((n.config && n.config.slug) || n.id)})</option>`).join("")}
                </select>
              </div>
              <div style="display:flex; gap:6px; align-items:center;">
                <button class="btn btn-xs btn-primary" style="padding:7px 12px; font-weight:800;" onclick="pickBatchLocalFiles()">📂 + Chọn Ảnh Từ Máy Tính</button>
                <button class="btn btn-xs btn-outline" style="padding:7px 10px;" onclick="WF_STATE.batchSelectedFiles = []; renderWfBatchGeneratorModal()">🗑️ Xoá chọn (${WF_STATE.batchSelectedFiles.length})</button>
              </div>
            </div>

            <div style="font-size:11px; color:#fde68a; font-weight:700;">
              ✅ Đã chọn <b>${WF_STATE.batchSelectedFiles.length}</b> ảnh Sản phẩm / Trang phục để chạy hàng loạt (Nhấp vào ảnh trong Kho bên dưới để chọn/bỏ chọn):
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(115px, 1fr)); gap:8px; max-height:240px; overflow-y:auto; padding:4px; background:#060911; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
              ${(WF_STATE.batchCatalogProducts || []).slice(0, 36).map(p => {
                const imgPath = p.image_path || (p.images && p.images[0]) || "";
                if (!imgPath) return "";
                const isSel = WF_STATE.batchSelectedFiles.includes(imgPath);
                return `
                  <div onclick="toggleBatchProductSelection('${encodeURIComponent(imgPath)}')"
                       style="cursor:pointer; border-radius:7px; padding:4px; background:${isSel ? 'rgba(163,230,53,0.18)' : '#0d1322'}; border:2px solid ${isSel ? '#a3e635' : 'rgba(255,255,255,0.08)'}; position:relative;">
                    <img src="${_getMediaUrlForWfPath(imgPath)}" style="width:100%; height:85px; object-fit:cover; border-radius:5px;" />
                    <div style="font-size:9.5px; color:#f8fafc; font-weight:700; margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${_wfEscHtml(p.name || p.product_id)}</div>
                    ${isSel ? `<span style="position:absolute; top:6px; right:6px; background:#a3e635; color:#052e16; font-size:9px; font-weight:900; padding:1px 5px; border-radius:4px;">✓ ĐÃ CHỌN</span>` : ''}
                  </div>
                `;
              }).join("")}
            </div>
          </div>
        ` : `
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div style="display:flex; align-items:center; justify-content:space-between;">
              <div style="flex:1;">
                <label style="font-size:11.5px; font-weight:800; color:#c084fc; display:block; margin-bottom:4px;">🎯 Chọn Node Prompt sẽ nhận câu lệnh theo từng lượt:</label>
                <select id="selWfBatchTargetPromptNode" onchange="WF_STATE.batchTargetPromptNodeId = this.value" style="width:100%; font-size:12px; padding:7px;">
                  ${promptNodes.map(n => `<option value="${n.id}" ${n.id === WF_STATE.batchTargetPromptNodeId ? 'selected' : ''}>📝 ${_wfEscHtml(n.label || n.id)} (@${_wfEscHtml((n.config && n.config.slug) || n.id)})</option>`).join("")}
                </select>
              </div>
              <button class="btn btn-xs btn-outline" style="margin-left:10px; margin-top:18px;" onclick="insertSampleBatchPrompts()">📋 Chèn 3 Prompt Mẫu</button>
            </div>
            <textarea id="txtWfBatchPrompts" rows="5"
                      placeholder="Mỗi dòng là 1 câu lệnh Prompt riêng biệt. Hệ thống sẽ chạy toàn bộ sơ đồ lần lượt cho từng dòng..."
                      style="width:100%; font-size:12px; background:#060911; color:#f8fafc; border:1px solid rgba(255,255,255,0.15); border-radius:8px; padding:10px; line-height:1.5;"></textarea>
          </div>
        `}
      </div>

      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; background:#0b101d; border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:10px 14px;">
        <div style="display:flex; gap:16px; align-items:center; flex-wrap:wrap;">
          <label style="font-size:11.5px; color:#e2e8f0; display:flex; align-items:center; gap:6px; cursor:pointer; font-weight:700;">
            <input type="checkbox" id="chkWfBatchAutoExportMp4" checked />
            🎬 Tự động ghép Timeline & xuất Video MP4 hoàn chỉnh cho mỗi lô
          </label>
          ${selClusterCount > 1 ? `
            <label style="font-size:11.5px; color:#f9a8d4; display:flex; align-items:center; gap:6px; cursor:pointer; font-weight:700;">
              <input type="checkbox" id="chkWfBatchOnlySelectedCluster" />
              📦 Chỉ chạy trong phạm vi Cụm ${selClusterCount} Node đang quét chọn
            </label>
          ` : ''}
        </div>
        <button class="btn btn-primary" style="background:linear-gradient(135deg,#f59e0b,#ea580c); border:none; color:#fff; font-weight:900; padding:9px 20px; font-size:13px; border-radius:9px;"
                onclick="startWfBatchExecution()">
          🚀 BẮT ĐẦU SẢN XUẤT HÀNG LOẠT NGAY
        </button>
      </div>

      ${batchHist.length ? `
        <div style="background:#080c15; border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:10px 14px;">
          <div style="font-size:11px; font-weight:800; color:#a3e635; margin-bottom:6px;">📦 KẾT QUẢ LÔ HÀNG LOẠT GẦN NHẤT (${batchHist.length} LÔ ĐÃ HOÀN TẤT):</div>
          <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(210px, 1fr)); gap:8px; max-height:150px; overflow-y:auto;">
            ${batchHist.slice(0, 12).map(b => `
              <div style="background:#111827; border:1px solid rgba(255,255,255,0.08); border-radius:7px; padding:7px 9px; font-size:10.5px;">
                <div style="font-weight:800; color:#f8fafc;">Lô #${b.batch_index}: ${_wfEscHtml(b.label || '')}</div>
                <div style="color:#94a3b8; font-size:9.5px; margin-top:2px;">🕒 ${_wfEscHtml(b.finished_at || '')}</div>
                ${b.exported_mp4_url ? `<a href="${b.exported_mp4_url}" target="_blank" style="display:inline-block; margin-top:4px; color:#38bdf8; font-weight:800;">▶ Xem Video MP4</a>` : ''}
              </div>
            `).join("")}
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

async function startWfBatchExecution() {
  const wf = _getWfBody();
  const mode = WF_STATE.batchMode || "variations";
  const autoExportEl = document.getElementById("chkWfBatchAutoExportMp4");
  const onlyClusterEl = document.getElementById("chkWfBatchOnlySelectedCluster");
  const batchConfig = {
    mode,
    auto_export_timeline: autoExportEl ? autoExportEl.checked : true,
  };

  if (mode === "variations") {
    const inp = document.getElementById("inpWfBatchRepeatCount");
    batchConfig.repeat_count = Math.max(1, Math.min(50, Number((inp && inp.value) || WF_STATE.batchRepeatCount || 3)));
  } else if (mode === "product_swap") {
    const selNodeEl = document.getElementById("selWfBatchTargetImgNode");
    batchConfig.target_image_node_id = (selNodeEl && selNodeEl.value) || WF_STATE.batchTargetImageNodeId;
    batchConfig.file_paths = WF_STATE.batchSelectedFiles.slice();
    if (!batchConfig.file_paths.length) {
      if (typeof toast === "function") toast("Hãy chọn ít nhất 1 ảnh Sản phẩm / Trang phục để chạy hàng loạt!", "err");
      return;
    }
  } else if (mode === "prompt_list") {
    const selPromptEl = document.getElementById("selWfBatchTargetPromptNode");
    const txtEl = document.getElementById("txtWfBatchPrompts");
    const lines = ((txtEl && txtEl.value) || "")
      .split(/\n+/)
      .map(s => s.trim())
      .filter(Boolean);
    if (!lines.length) {
      if (typeof toast === "function") toast("Hãy nhập ít nhất 1 dòng Prompt để chạy hàng loạt!", "err");
      return;
    }
    batchConfig.target_prompt_node_id = (selPromptEl && selPromptEl.value) || WF_STATE.batchTargetPromptNodeId;
    batchConfig.prompts = lines;
  }

  const selectedNodeIds = (onlyClusterEl && onlyClusterEl.checked && WF_STATE.selectedNodeIds && WF_STATE.selectedNodeIds.size)
    ? Array.from(WF_STATE.selectedNodeIds)
    : null;

  if (!wf.settings) wf.settings = {};
  wf.settings._batch_run_config = { ...batchConfig, enabled: true };

  closeModal("modalWfBatchGenerator");
  await runWorkflowExecution(null, selectedNodeIds, batchConfig);
}

// ── LƯU, TẠO MỚI, NHÂN BẢN, XOÁ, NHẬP/XUẤT JSON & CHẠY WORKFLOW ──
async function saveCurrentWorkflowToDisk(silent = false) {
  const wf = _getWfBody();
  const nameInp = document.getElementById("inpWorkflowTitle") || document.getElementById("inpWfCurrentName");
  if (nameInp && nameInp.value.trim()) {
    wf.name = nameInp.value.trim();
  }
  const wfId = WF_STATE.currentWfId || (WF_STATE.doc && (WF_STATE.doc._wf_id || WF_STATE.doc.id)) || "wf_custom";
  try {
    const r = await fetch("/api/workflows/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wf_id: wfId, workflow_doc: WF_STATE.doc }),
    }).then(x => x.json());

    if (r.ok && r.workflow) {
      WF_STATE.doc = r.workflow;
      WF_STATE.currentWfId = r.workflow._wf_id || r.workflow.id || wfId;
      await loadWorkflowsListFromServer(true);
      if (!silent && typeof toast === "function") toast(`💾 Đã lưu Workflow "${wf.name}"!`, "ok");
    }
  } catch (e) {
    if (!silent && typeof toast === "function") toast("Lỗi lưu Workflow: " + e.message, "err");
  }
}

function onRenameCurrentWorkflow(newName) {
  const wf = _getWfBody();
  if (!newName || !newName.trim()) return;
  wf.name = newName.trim();
  saveCurrentWorkflowToDisk(true);
}

async function createNewBlankWorkflow() {
  const name = prompt("Nhập tên cho Workflow mới:", `Workflow AI Mới (${new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })})`);
  if (!name) return;
  const newId = `wf_custom_${Date.now().toString(36)}`;
  WF_STATE.currentWfId = newId;
  WF_STATE.doc = {
    id: newId,
    _wf_id: newId,
    version: "1.0",
    type: "workflow",
    workflow: {
      name: name.trim(),
      description: "Workflow tự thiết kế trên Google Flow + CLIProxy",
      settings: { parallel: true, max_parallel: 2 },
      groups: [],
      nodes: [],
      edges: [],
      timeline: [],
    },
  };
  WF_STATE.selectedNodeId = null;
  WF_STATE.selectedNodeIds = new Set();
  await saveCurrentWorkflowToDisk(false);
  renderWorkflowCanvas();
  renderWfInspector();
}

async function duplicateCurrentWorkflow() {
  const cloned = JSON.parse(JSON.stringify(WF_STATE.doc || {}));
  const newId = `${WF_STATE.currentWfId || 'wf'}_copy_${Date.now().toString(36).slice(-4)}`;
  cloned.id = newId;
  cloned._wf_id = newId;
  if (cloned.workflow) {
    cloned.workflow.name = `${cloned.workflow.name || 'Workflow'} (Bản sao)`;
  }
  WF_STATE.currentWfId = newId;
  WF_STATE.doc = cloned;
  await saveCurrentWorkflowToDisk(false);
  renderWorkflowCanvas();
}

async function deleteCurrentWorkflowDoc() {
  const wf = _getWfBody();
  const wfId = WF_STATE.currentWfId || (WF_STATE.doc && (WF_STATE.doc._wf_id || WF_STATE.doc.id));
  if (!wfId) return;
  if (!confirm(`Bạn có chắc muốn xoá sơ đồ Workflow "${wf.name}" không?`)) return;
  try {
    await fetch("/api/workflows/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wf_id: wfId }),
    });
    WF_STATE.currentWfId = "";
    await loadWorkflowsListFromServer(false);
    if (typeof toast === "function") toast("🗑️ Đã xoá Workflow!", "ok");
  } catch (e) {
    if (typeof toast === "function") toast("Lỗi xoá Workflow: " + e.message, "err");
  }
}

function exportCurrentWorkflowJson() {
  const wf = _getWfBody();
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(WF_STATE.doc || wf, null, 2));
  const a = document.createElement("a");
  a.setAttribute("href", dataStr);
  const safeName = (wf.name || WF_STATE.currentWfId || "workflow").replace(/[^a-zA-Z0-9_\-\u00C0-\u1EF9]+/g, "_");
  a.setAttribute("download", `workflow_${safeName}.json`);
  document.body.appendChild(a);
  a.click();
  a.remove();
  if (typeof toast === "function") toast("📤 Đã xuất file JSON Workflow!", "ok");
}

function openWfImportModal() {
  openModal("modalWfImportJson");
}

function handleWfJsonFileUpload(ev) {
  const file = ev.target.files && ev.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    const txt = document.getElementById("txtWfImportJsonRaw");
    if (txt) txt.value = e.target.result || "";
  };
  reader.readAsText(file, "utf-8");
}

async function submitImportWorkflowJsonRaw() {
  const txt = document.getElementById("txtWfImportJsonRaw");
  if (!txt || !txt.value.trim()) {
    if (typeof toast === "function") toast("Hãy chọn file .json hoặc dán nội dung JSON vào ô!", "err");
    return;
  }
  try {
    const parsed = JSON.parse(txt.value);
    const r = await fetch("/api/workflows/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workflow_doc: parsed }),
    }).then(x => x.json());

    if (!r.ok || !r.workflow) {
      throw new Error(r.error || "Format JSON không hợp lệ");
    }
    closeModal("modalWfImportJson");
    WF_STATE.currentWfId = r.workflow._wf_id || r.workflow.id;
    await loadWorkflowsListFromServer(true);
    loadWorkflowDocumentIntoCanvas(r.workflow, true);
    if (typeof toast === "function") toast(`📥 Đã nhập thành công Workflow "${(r.workflow.workflow && r.workflow.workflow.name) || r.workflow.id}"!`, "ok");
  } catch (e) {
    if (typeof toast === "function") toast("Lỗi nhập JSON Workflow: " + e.message, "err");
  }
}

function toggleWfParallelMode(val) {
  const wf = _getWfBody();
  if (!wf.settings) wf.settings = {};
  wf.settings.parallel = Boolean(val);
}

function openWfSettingsModal() {
  const wf = _getWfBody();
  const st = wf.settings || {};
  const mSpeed = document.getElementById("chkWfSettingMaxSpeed");
  const mDown = document.getElementById("chkWfSettingAutoDownload");
  const mRatio = document.getElementById("selWfSettingAspectRatio");
  const mFolder = document.getElementById("inpWfSettingOutputFolder");
  if (mSpeed) mSpeed.checked = st.parallel !== false;
  if (mDown) mDown.checked = st.auto_download !== false;
  if (mRatio) mRatio.value = st.default_aspect_ratio || "9:16";
  if (mFolder) mFolder.value = st.output_folder || "final_videos";
  openModal("modalWfSettings");
}

function saveWfSettingsFromModal() {
  const wf = _getWfBody();
  if (!wf.settings) wf.settings = {};
  const mSpeed = document.getElementById("chkWfSettingMaxSpeed");
  const mDown = document.getElementById("chkWfSettingAutoDownload");
  const mRatio = document.getElementById("selWfSettingAspectRatio");
  const mFolder = document.getElementById("inpWfSettingOutputFolder");
  if (mSpeed) wf.settings.parallel = mSpeed.checked;
  if (mDown) wf.settings.auto_download = mDown.checked;
  if (mRatio) wf.settings.default_aspect_ratio = mRatio.value;
  if (mFolder) wf.settings.output_folder = mFolder.value.trim() || "final_videos";
  closeModal("modalWfSettings");
  saveCurrentWorkflowToDisk(false);
}

function resetWorkflowNodesStatus() {
  const wf = _getWfBody();
  wfPushHistory();
  (wf.nodes || []).forEach(n => {
    if (!n.config) n.config = {};
    const nt = (n.node_type || "").toLowerCase();
    if (["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(nt)) {
      n.config.status = "idle";
    }
  });
  renderWorkflowCanvas();
  renderWfInspector();
  if (typeof toast === "function") toast("↺ Đã đặt lại trạng thái các Node tạo AI về Chờ chạy!", "info");
}

function runSelectedWfNodeOnly() {
  if (!WF_STATE.selectedNodeId) {
    if (typeof toast === "function") toast("Hãy chọn 1 Node trước khi bấm chạy riêng!", "err");
    return;
  }
  runWorkflowExecution(WF_STATE.selectedNodeId);
}

async function testRunPromptNodeWithAi(nodeId) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node || !node.config) return;
  const seed = node.config.prompt || "";
  if (!seed.trim()) {
    if (typeof toast === "function") toast("Hãy nhập ý tưởng ngắn gọn vào ô Prompt trước!", "err");
    return;
  }
  try {
    if (typeof toast === "function") toast("🪄 Đang gọi AI CLIProxy tối ưu câu lệnh Prompt...", "info");
    const r = await fetch("/api/workflows/test_prompt_ai", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: node.config.model || "gpt-5.4",
        prompt: seed,
        image_paths: _collectUpstreamMediaPaths(node.id),
      }),
    }).then(x => x.json());

    const outTxt = r.text || r.result_text;
    if (r.ok && outTxt) {
      wfPushHistory();
      node.config.prompt = outTxt;
      node.prompt = outTxt;
      node.config.last_output = outTxt;
      node.config.status = "done";
      renderWorkflowCanvas();
      renderWfInspector();
      if (typeof toast === "function") toast("✨ AI đã nâng cấp câu lệnh Prompt thành công!", "ok");
    }
  } catch (e) {
    if (typeof toast === "function") toast("Lỗi gọi AI Prompt: " + e.message, "err");
  }
}

async function rerunWfNodeStrict(nodeId) {
  const wf = _getWfBody();
  const node = wf.nodes.find(n => n.id === nodeId);
  if (!node) return;
  if (!node.config) node.config = {};
  const lockSuffix = " [STRICT LOCK: Keep exact character facial identity, hairstyle, product details, logo, and background 100% consistent with reference images.]";
  if (!(node.config.prompt || "").includes("STRICT LOCK:")) {
    node.config.prompt = ((node.config.prompt || "") + lockSuffix).trim();
    node.prompt = node.config.prompt;
  }
  await runWorkflowExecution(nodeId);
}

async function runWorkflowExecution(singleNodeId = null, selectedNodeIds = null, batchConfig = null) {
  const wf = _getWfBody();
  if (!wf.nodes || !wf.nodes.length) {
    if (typeof toast === "function") toast("Sơ đồ Workflow đang trống, hãy thêm Node trước!", "err");
    return;
  }

  const wfId = WF_STATE.currentWfId || (WF_STATE.doc && (WF_STATE.doc._wf_id || WF_STATE.doc.id)) || "wf_custom";
  const targetSet = singleNodeId
    ? new Set([singleNodeId])
    : (selectedNodeIds && selectedNodeIds.length ? new Set(selectedNodeIds) : null);

  (wf.nodes || []).forEach(n => {
    if (!targetSet || targetSet.has(n.id)) {
      const nt = (n.node_type || "").toLowerCase();
      if (["generate", "gpt_image", "grok_generate", "gemini_generate"].includes(nt)) {
        if (!n.config) n.config = {};
        n.config.status = "running";
      }
    }
  });
  renderWorkflowCanvas();

  try {
    const payload = {
      wf_id: wfId,
      workflow_doc: WF_STATE.doc,
      target_node_id: singleNodeId || null,
      selected_node_ids: selectedNodeIds || null,
    };
    const r = await fetch("/api/workflows/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(x => x.json());

    if (!r.ok) {
      throw new Error(r.error || "Không thể khởi chạy Workflow");
    }
    if (typeof toast === "function") {
      if (batchConfig) {
        toast(`🚀 Đã khởi chạy Sản xuất Số Lượng Lớn (Batch) trên Google Flow cho "${wf.name}"!`, "ok");
      } else if (singleNodeId) {
        toast(`▶ Đang gửi lệnh chạy Node "${singleNodeId}" lên Google Flow...`, "info");
      } else if (selectedNodeIds && selectedNodeIds.length) {
        toast(`▶️ Đang gửi lệnh chạy Cụm ${selectedNodeIds.length} Node lên Google Flow...`, "info");
      } else {
        toast(`▶ Đang chạy toàn bộ Sơ đồ Workflow "${wf.name}" trên Google Flow...`, "info");
      }
    }
    startPollingWorkflowRunStatus(r.wf_id || wfId);
  } catch (e) {
    if (typeof toast === "function") toast("Lỗi chạy Workflow: " + e.message, "err");
  }
}

function startPollingWorkflowRunStatus(wfId) {
  if (WF_STATE.pollTimer) clearInterval(WF_STATE.pollTimer);
  WF_STATE.pollTimer = setInterval(async () => {
    try {
      const r = await fetch(`/api/workflows/status?wf_id=${encodeURIComponent(wfId)}`).then(x => x.json());
      const st = r.status || {};
      const nodeStates = st.node_states || {};
      const wf = _getWfBody();

      let changed = false;
      Object.keys(nodeStates).forEach(nid => {
        const ns = nodeStates[nid] || {};
        const node = (wf.nodes || []).find(n => n.id === nid);
        if (node && node.config) {
          if (ns.status && node.config.status !== ns.status) {
            node.config.status = ns.status;
            changed = true;
          }
          const resObj = ns.result || {};
          const pPath = resObj.primary_path || ((resObj.media_paths || [])[0]) || "";
          if (pPath && node.config.result_path !== pPath) {
            node.config.result_path = pPath;
            node.config.file_path = pPath;
            changed = true;
          }
        }
      });

      if (changed) {
        renderWorkflowCanvas();
        renderWfInspector();
        renderWfTimelineDock();
      }

      if (st.status && st.status !== "running") {
        clearInterval(WF_STATE.pollTimer);
        WF_STATE.pollTimer = null;
        await loadWorkflowsListFromServer(true);
        if (typeof toast === "function") {
          if (st.status === "done") {
            toast("✅ Đã hoàn tất render trên Google Flow! Ảnh 2K & Video 1080p mới đã hiển thị trên từng Node.", "ok");
          } else {
            toast(`⚠️ Kết thúc chạy Workflow (${st.status}). Kiểm tra chi tiết trên từng Node.`, "err");
          }
        }
      }
    } catch (_) {
      clearInterval(WF_STATE.pollTimer);
      WF_STATE.pollTimer = null;
    }
  }, 2000);
}

