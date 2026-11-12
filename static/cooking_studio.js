/* Template 005: POV Cooking Studio — Auto Script + Voice Library + Account Selector + 1-Click Final MP4 */
(() => {
  let projectId = "";
  let currentRecipe = null;
  let scriptDishKey = "";
  let scriptDirtyByUser = false;
  let pollTimer = null;
  let mediaSignature = "";
  let cachedDefaults = null;

  const esc = value =>
    String(value ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));

  const media = path => `/api/media?path=${encodeURIComponent(path)}`;

  async function call(url, data) {
    const response = await fetch(
      url,
      data === undefined
        ? { cache: "no-store" }
        : {
            method: "POST",
            cache: "no-store",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
          }
    );
    const result = await response.json();
    if (!response.ok || !result.ok) {
      const rawErr = result.error || "Không thực hiện được thao tác này.";
      if (rawErr === "Unknown endpoint") {
        throw new Error(
          "Server Python đang chạy phiên bản cũ trong bộ nhớ (chưa nạp API mới của Template #005). Vui lòng chạy lại Chay_Skill_Web.bat (hoặc khởi động lại server.py) rồi bấm Reload!"
        );
      }
      throw new Error(rawErr);
    }
    return result;
  }

  async function loadCookingDefaultsWithFallback() {
    const defaults = await call(`/api/cooking/default?_t=${Date.now()}`);
    if (!Array.isArray(defaults.voices) || !defaults.voices.length) {
      try {
        const charRes = await call(`/api/characters?_t=${Date.now()}`);
        const vList = Array.isArray(charRes.voices_list)
          ? charRes.voices_list
          : Object.values(charRes.voices || {});
        if (vList.length) {
          defaults.voices = vList.map(v => ({
            ...v,
            recommended_for_cooking:
              Array.isArray(v.recommended_templates) &&
              (v.recommended_templates.includes("002") || v.recommended_templates.includes("005")),
          }));
          if (!defaults.default_voice_key) {
            const rec = defaults.voices.find(v => v.recommended_for_cooking) || defaults.voices[0];
            if (rec) defaults.default_voice_key = rec.key;
          }
        }
      } catch (_) {}
    }
    if (!Array.isArray(defaults.accounts) || !defaults.accounts.length) {
      try {
        const setRes = await call(`/api/settings?_t=${Date.now()}`);
        const det = setRes.settings?.detected_flow_accounts || setRes.detected_flow_accounts || [];
        if (Array.isArray(det) && det.length) {
          defaults.accounts = det.map(a => ({
            profile_name: a.profile_name || a.name,
            name: a.name || a.profile_name,
            project_id: a.project_id || "",
            active: a.active !== false,
            has_cookies: a.has_cookies !== false,
            display_label: a.display_label || a.name || a.profile_name,
          }));
          if (!defaults.default_profile) {
            const firstReady = defaults.accounts.find(a => a.has_cookies) || defaults.accounts[0];
            if (firstReady) defaults.default_profile = firstReady.profile_name;
          }
        }
      } catch (_) {}
    }
    return defaults;
  }

  function show(message, bad = false) {
    const target = document.getElementById("cookingMessage");
    if (!target) return;
    target.innerHTML = esc(message);
    target.style.color = bad ? "#fca5a5" : "#6ee7b7";
    target.style.borderColor = bad ? "rgba(239,68,68,0.45)" : "rgba(16,185,129,0.38)";
    target.style.background = bad ? "rgba(127,29,29,0.22)" : "rgba(6,78,59,0.22)";
  }

  function getSelectedVoiceState() {
    const sel = document.getElementById("cookingVoiceSelect");
    const customInp = document.getElementById("cookingCustomVoiceId");
    const rawVal = sel ? sel.value : "";
    if (!rawVal || rawVal === "__ASMR__") {
      return { audio_mode: "asmr", voice_id: "", voice_obj: null };
    }
    if (rawVal === "__CUSTOM__") {
      const cid = (customInp?.value || "").trim();
      return { audio_mode: "voice", voice_id: cid, voice_obj: null };
    }
    const voices = cachedDefaults?.voices || [];
    const found = voices.find(v => v.key === rawVal || v.voice_id === rawVal) || null;
    return {
      audio_mode: "voice",
      voice_id: found ? (found.key || found.voice_id) : rawVal,
      voice_obj: found,
    };
  }

  function syncVoiceDependentControls() {
    const st = getSelectedVoiceState();
    const customWrap = document.getElementById("cookingCustomVoiceWrap");
    const previewBtn = document.getElementById("cookingVoicePreviewBtn");
    const subChk = document.getElementById("cookingSubtitles");
    const subWrap = document.getElementById("cookingSubtitlesWrap");
    const voBox = document.getElementById("cookingNarrationWrap");

    if (customWrap) {
      customWrap.style.display = document.getElementById("cookingVoiceSelect")?.value === "__CUSTOM__" ? "block" : "none";
    }
    if (previewBtn) {
      previewBtn.disabled = !(st.voice_obj && (st.voice_obj.sample_vn_abs || st.voice_obj.sample_url));
    }
    if (subChk && subWrap) {
      subChk.disabled = st.audio_mode !== "voice";
      if (st.audio_mode !== "voice") subChk.checked = false;
      subWrap.style.opacity = st.audio_mode === "voice" ? "1" : "0.5";
    }
    if (voBox) {
      voBox.style.display = st.audio_mode === "voice" ? "block" : "none";
    }
  }

  function playSelectedVoiceSample() {
    const st = getSelectedVoiceState();
    const player = document.getElementById("cookingVoiceAudio");
    if (!player || !st.voice_obj) {
      show("Giọng đang chọn chưa có file mẫu nghe thử.", true);
      return;
    }
    const src = st.voice_obj.sample_vn_abs
      ? media(st.voice_obj.sample_vn_abs)
      : st.voice_obj.sample_url || "";
    if (!src) {
      show("Chưa tìm thấy file âm thanh mẫu cho giọng này.", true);
      return;
    }
    player.style.display = "block";
    player.src = src;
    player.play().catch(() => {});
    show(`🔊 Đang nghe thử giọng: ${st.voice_obj.name}`);
  }

  function renderScriptSummaryCards(recipeObj) {
    const box = document.getElementById("cookingScriptSummary");
    if (!box || !recipeObj || !Array.isArray(recipeObj.clips)) return;
    const isVoice = (recipeObj.audio_mode || getSelectedVoiceState().audio_mode) === "voice";
    const slots = ["0.0–2.6s", "2.6–5.2s", "5.2–7.7s"];

    box.innerHTML = recipeObj.clips
      .map((clip, idx) => {
        const vnActions = Array.isArray(clip.actions_vn) && clip.actions_vn.length === 6 ? clip.actions_vn : clip.actions || [];
        const voLines = Array.isArray(clip.voiceover) ? clip.voiceover : [];
        return `
          <div style="background:#0a101d;border:1px solid rgba(99,102,241,0.3);border-radius:10px;padding:11px 13px;display:flex;flex-direction:column;gap:7px;min-width:0;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
              <span style="font-weight:800;font-size:12.5px;color:#fde68a;">🎬 Cảnh ${idx + 1}: ${esc(clip.title || `Đoạn ${idx + 1}`)}</span>
              <span style="font-size:10.5px;color:#93c5fd;background:rgba(30,58,138,0.35);padding:2px 7px;border-radius:999px;">8s · 6 ô 2K</span>
            </div>
            <ol style="margin:0;padding-left:17px;font-size:11.5px;color:#cbd5e1;line-height:1.45;">
              ${vnActions.map(a => `<li style="margin-bottom:2px;">${esc(a)}</li>`).join("")}
            </ol>
            ${
              isVoice && voLines.length
                ? `<div style="margin-top:2px;padding:7px 9px;border-radius:7px;background:rgba(16,185,129,0.09);border:1px solid rgba(16,185,129,0.3);font-size:11px;color:#a7f3d0;line-height:1.45;">
                    <div style="font-weight:800;color:#34d399;margin-bottom:3px;">🎙️ Lời dẫn Voice theo nhịp 8 giây:</div>
                    ${voLines
                      .map(
                        (line, li) =>
                          `<div><code style="color:#fcd34d;font-size:10px;">[${slots[li] || "—"}]</code> "${esc(line)}" <span style="color:#64748b;font-size:10px;">(${line.trim().split(/\s+/).filter(Boolean).length} từ)</span></div>`
                      )
                      .join("")}
                  </div>`
                : `<div style="font-size:10.5px;color:#94a3b8;">🎧 Âm thanh ASMR tự nhiên theo từng thao tác nấu (không lời thoại).</div>`
            }
          </div>
        `;
      })
      .join("");
  }

  function populateEditorFromRecipe(recipeObj) {
    if (!recipeObj || !Array.isArray(recipeObj.clips)) return;
    currentRecipe = JSON.parse(JSON.stringify(recipeObj));
    scriptDishKey = `${(recipeObj.dish || "").trim().toLowerCase()}|${recipeObj.clips.length}|${recipeObj.audio_mode || "asmr"}`;
    scriptDirtyByUser = false;

    const dishInp = document.getElementById("cookingDish");
    if (dishInp && recipeObj.dish) dishInp.value = recipeObj.dish;

    const numSel = document.getElementById("cookingNumClips");
    if (numSel && recipeObj.clips.length >= 1 && recipeObj.clips.length <= 6) {
      numSel.value = String(recipeObj.clips.length);
    }

    const actionsEl = document.getElementById("cookingActions");
    if (actionsEl) {
      actionsEl.value = recipeObj.clips.flatMap(c => c.actions || []).join("\n");
    }

    const voEl = document.getElementById("cookingNarration");
    if (voEl) {
      const allVo = recipeObj.clips.flatMap(c => c.voiceover || []);
      voEl.value = allVo.join("\n");
    }

    renderScriptSummaryCards(recipeObj);
  }

  function collectEditedRecipeOrNull() {
    const dish = (document.getElementById("cookingDish")?.value || "").trim();
    const numClips = parseInt(document.getElementById("cookingNumClips")?.value || "3", 10);
    const vState = getSelectedVoiceState();
    const curKey = `${dish.toLowerCase()}|${numClips}|${vState.audio_mode}`;

    // If user hasn't manually edited textareas and changed dish/clip count, let backend auto-generate fresh script!
    if (!scriptDirtyByUser && (!currentRecipe || curKey !== scriptDishKey)) {
      return null;
    }
    if (!currentRecipe && !scriptDirtyByUser) {
      return null;
    }

    const actions = (document.getElementById("cookingActions")?.value || "")
      .split("\n")
      .map(x => x.trim())
      .filter(Boolean);
    if (!actions.length || actions.length % 6 !== 0 || actions.length > 36) {
      if (!scriptDirtyByUser) return null;
      throw new Error("Phần hành động cần đúng bội số 6 dòng (6 dòng cho mỗi cảnh 8 giây, tối đa 36 dòng).");
    }

    const clipCount = actions.length / 6;
    const baseClips = Array.isArray(currentRecipe?.clips) ? currentRecipe.clips : [];
    const builtClips = Array.from({ length: clipCount }, (_, i) => {
      const prev = baseClips[i] || {};
      const slice = actions.slice(i * 6, i * 6 + 6);
      return {
        title: prev.title || `${dish} · Đoạn ${i + 1}`,
        start_state:
          prev.start_state ||
          (i === 0
            ? "Empty clean cookware; ingredients prepped in small clear glass bowls."
            : `Continue the exact food and cookware state established in clip ${i}.`),
        actions: slice,
        actions_vn: Array.isArray(prev.actions_vn) && prev.actions_vn.length === 6 ? prev.actions_vn : undefined,
      };
    });

    if (vState.audio_mode === "voice") {
      const lines = (document.getElementById("cookingNarration")?.value || "")
        .split("\n")
        .map(x => x.trim())
        .filter(Boolean);
      if (lines.length === clipCount * 3) {
        builtClips.forEach((c, i) => {
          c.voiceover = lines.slice(i * 3, i * 3 + 3);
        });
      } else if (scriptDirtyByUser && lines.length > 0) {
        throw new Error(`Chế độ Có Voice cần đúng ${clipCount * 3} dòng lời dẫn (3 câu cho mỗi cảnh 8 giây), hiện có ${lines.length} dòng.`);
      }
    }

    return {
      dish,
      dish_en: currentRecipe?.dish && currentRecipe.dish.toLowerCase() === dish.toLowerCase() ? (currentRecipe.dish_en || "") : "",
      visual_continuity:
        currentRecipe?.dish && currentRecipe.dish.toLowerCase() === dish.toLowerCase()
          ? currentRecipe.visual_continuity || ""
          : "",
      audio_mode: vState.audio_mode,
      voice_id: vState.voice_id,
      has_subtitles: Boolean(document.getElementById("cookingSubtitles")?.checked && vState.audio_mode === "voice"),
      clips: builtClips,
    };
  }

  async function generateScriptPreview(silentIfEmpty = false) {
    const dish = (document.getElementById("cookingDish")?.value || "").trim();
    if (!dish) {
      if (!silentIfEmpty) show("Vui lòng gõ tên món ăn trước khi sinh kịch bản.", true);
      return null;
    }
    const vState = getSelectedVoiceState();
    const numClips = parseInt(document.getElementById("cookingNumClips")?.value || "3", 10);
    const notes = (document.getElementById("cookingNotes")?.value || "").trim();
    const hasSubtitles = Boolean(document.getElementById("cookingSubtitles")?.checked && vState.audio_mode === "voice");

    const genBtn = document.getElementById("cookingGenScriptBtn");
    if (genBtn) {
      genBtn.disabled = true;
      genBtn.textContent = "⏳ Đang sinh kịch bản...";
    }
    try {
      show(`✨ Đang tự sinh công thức 6 ô/cảnh & lời dẫn cho món "${dish}"...`);
      const res = await call("/api/cooking/generate-script", {
        dish,
        num_clips: numClips,
        audio_mode: vState.audio_mode,
        voice_id: vState.voice_id,
        custom_notes: notes,
        has_subtitles: hasSubtitles,
      });
      populateEditorFromRecipe(res.recipe);
      show(
        `✅ Đã tự sinh kịch bản "${res.recipe.dish}" (${res.recipe.clips.length} cảnh × 8s${
          vState.audio_mode === "voice" ? " • Đã khớp lời dẫn theo giọng đọc" : " • Chế độ ASMR"
        }). Bấm "🚀 Tạo Video Final Luôn" để chạy ra MP4!`
      );
      return res.recipe;
    } catch (error) {
      show(error.message, true);
      return null;
    } finally {
      if (genBtn) {
        genBtn.disabled = false;
        genBtn.textContent = "✨ Tự sinh kịch bản";
      }
    }
  }

  function renderProject(project) {
    if (!project) return;
    const running = !!project.is_running;
    const done = project.status === "done" && !!project.final_video_path;

    const statusMsg = done
      ? `🎉 Video Final 1080p 60FPS cho món "${project.dish}" đã hoàn tất! Bạn có thể xem và tải ngay bên dưới.`
      : project.status_message || `Trạng thái dự án: ${project.status}`;
    show(statusMsg, project.status === "error");

    const autoBtn = document.getElementById("cookingAutoFinalBtn");
    const stopBtn = document.getElementById("cookingStopBtn");
    const boardsBtn = document.getElementById("cookingBoards");
    const videoBtn = document.getElementById("cookingVideo");
    const badgeEl = document.getElementById("cookingActiveProjectBadge");

    if (autoBtn) autoBtn.disabled = running;
    if (stopBtn) stopBtn.style.display = running ? "inline-flex" : "none";
    if (boardsBtn) boardsBtn.disabled = running;
    if (videoBtn) {
      videoBtn.disabled =
        running ||
        done ||
        !Array.isArray(project.clips) ||
        !project.clips.every(c => c.native_2k && c.uploaded_2k_uuid);
    }
    if (badgeEl) {
      const modeLbl = project.recipe?.audio_mode === "voice"
        ? `🎙️ ${project.recipe?.voice_name || "Có Voice"}`
        : "🎧 ASMR";
      badgeEl.innerHTML = `📁 Dự án đang mở: <code>${esc(project.project_id)}</code> · <b>${esc(project.dish)}</b> · ${esc(modeLbl)} ${
        project.profile ? `· TK: <code>${esc(project.profile)}</code>` : ""
      }`;
      badgeEl.style.display = "block";
    }

    const signature = JSON.stringify([
      project.project_id,
      project.status,
      running,
      project.final_video_path,
      (project.clips || []).map(c => [c.id, c.native_2k, c.uploaded_2k_uuid, c.video_done, c.storyboard_dimensions]),
    ]);
    if (signature === mediaSignature) return;
    mediaSignature = signature;

    const finalBox = document.getElementById("cookingFinal");
    if (finalBox) {
      finalBox.innerHTML =
        done && project.final_video_path
          ? `
            <div style="margin:14px 0;padding:16px;border-radius:14px;background:linear-gradient(145deg,rgba(6,78,59,0.38),rgba(15,23,42,0.95));border:1px solid rgba(16,185,129,0.55);display:flex;gap:18px;flex-wrap:wrap;align-items:center;">
              <video controls preload="metadata" style="width:250px;max-width:100%;aspect-ratio:9/16;border-radius:10px;background:#000;border:1px solid rgba(255,255,255,0.16);" src="${media(project.final_video_path)}"></video>
              <div style="flex:1;min-width:240px;display:flex;flex-direction:column;gap:8px;">
                <div style="font-size:17px;font-weight:900;color:#34d399;">🎉 VIDEO FINAL HOÀN CHỈNH · 1080p 60FPS</div>
                <div style="font-size:13.5px;color:#f8fafc;font-weight:700;">🍲 Món ăn: ${esc(project.dish)}</div>
                <div style="font-size:12px;color:#cbd5e1;">
                  Âm thanh: <b>${project.recipe?.audio_mode === "voice" ? esc(project.recipe?.voice_name || "Có Voice") : "ASMR gốc"}</b>
                  ${project.final_duration_sec ? ` · Thời lượng: <b>${esc(project.final_duration_sec)}s</b>` : ""}
                </div>
                <div style="font-size:11px;color:#94a3b8;font-family:Consolas,monospace;word-break:break-all;">${esc(project.final_video_path)}</div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px;">
                  <a class="btn btn-success" style="font-weight:800;padding:8px 14px;text-decoration:none;" href="${media(project.final_video_path)}" download>⬇️ Tải Video Final (.MP4)</a>
                  <button class="btn btn-outline" onclick="if(typeof openFolder==='function') openFolder('final_videos');">📂 Mở thư mục Video Final</button>
                </div>
              </div>
            </div>
          `
          : "";
    }

    const gallery = document.getElementById("cookingGallery");
    if (gallery) {
      gallery.innerHTML = (project.clips || [])
        .map((clip, idx) => {
          const imageRel = clip.native_2k ? `projects/${project.project_id}/${clip.storyboard_file}` : "";
          const dims = Array.isArray(clip.storyboard_dimensions) ? `${clip.storyboard_dimensions[0]}×${clip.storyboard_dimensions[1]}` : "2K";
          const vo = Array.isArray(clip.voiceover) && clip.voiceover.length
            ? `<div style="font-size:11px;color:#a7f3d0;background:rgba(16,185,129,0.08);padding:6px 8px;border-radius:6px;margin-bottom:8px;">🎙️ ${clip.voiceover.map(esc).join(" · ")}</div>`
            : "";
          return `
            <section style="background:#0b1120;border:1px solid rgba(71,85,105,0.65);border-radius:12px;padding:12px;min-width:0;display:flex;flex-direction:column;gap:8px;">
              <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
                <b style="color:#fde68a;font-size:13px;">Cảnh ${idx + 1}: ${esc(clip.title)}</b>
                <span style="font-size:11px;color:#93c5fd;">${esc(clip.id)} · 8s · 6 ô</span>
              </div>
              <div style="font-size:11px;color:#94a3b8;">
                ${clip.native_2k ? `✅ Storyboard gốc ${esc(dims)}` : "⏳ Chưa tạo storyboard 2K"}
                ${clip.uploaded_2k_uuid ? " · ☁️ Đã re-upload tham chiếu" : ""}
                ${clip.video_done ? " · 🎬 Đã xong clip 1080p" : ""}
              </div>
              ${vo}
              ${
                imageRel
                  ? `<div style="background:#050811;border-radius:8px;padding:6px;text-align:center;">
                      <a href="${media(imageRel)}" target="_blank" rel="noopener" title="Bấm mở ảnh Storyboard 2K gốc">
                        <img src="${media(imageRel)}" style="width:100%;max-height:380px;object-fit:contain;border-radius:6px;" alt="Storyboard ${esc(clip.id)}">
                      </a>
                      <div style="margin-top:5px;"><a style="font-size:11.5px;color:#38bdf8;" href="${media(imageRel)}" download>⬇️ Tải Storyboard 2K (${esc(clip.id)})</a></div>
                    </div>`
                  : ""
              }
              ${
                clip.video_done
                  ? `<video controls preload="metadata" style="width:100%;max-height:360px;border-radius:8px;background:#000;" src="${media(`projects/${project.project_id}/${clip.file}`)}"></video>`
                  : ""
              }
            </section>
          `;
        })
        .join("");
    }
  }

  async function refresh() {
    if (!projectId || !document.getElementById("cookingStudioModal")) return;
    try {
      const res = await call(`/api/cooking/status?project_id=${encodeURIComponent(projectId)}`);
      renderProject(res.project);
    } catch (error) {
      show(error.message, true);
    }
  }

  async function runOneClickAutoFinal() {
    try {
      const dish = (document.getElementById("cookingDish")?.value || "").trim();
      if (!dish) throw new Error("Vui lòng nhập tên món ăn cần tạo video!");

      const vState = getSelectedVoiceState();
      if (vState.audio_mode === "voice" && !vState.voice_id) {
        throw new Error("Vui lòng chọn giọng đọc trong danh sách (hoặc chọn chế độ Chỉ ASMR)!");
      }
      const profile = (document.getElementById("cookingAccountSelect")?.value || "").trim();
      if (!profile) throw new Error("Vui lòng chọn tài khoản Google Flow trong danh sách!");

      const numClips = parseInt(document.getElementById("cookingNumClips")?.value || "3", 10);
      const videoProvider = (document.getElementById("cookingVideoProvider")?.value || "google_flow").trim();
      const notes = (document.getElementById("cookingNotes")?.value || "").trim();
      const hasSubtitles = Boolean(document.getElementById("cookingSubtitles")?.checked && vState.audio_mode === "voice");
      const editedRecipe = collectEditedRecipeOrNull();

      const autoBtn = document.getElementById("cookingAutoFinalBtn");
      if (autoBtn) autoBtn.disabled = true;
      show(`🚀 Đang tự sinh kịch bản "${dish}", khởi tạo dự án và chạy thẳng tới Video Final 1080p 60FPS (${videoProvider === "google_vids" ? "Google Vids Omni 1080p" : "Google Flow"})...`);

      const res = await call("/api/cooking/quick-run", {
        dish,
        voice_id: vState.voice_id,
        audio_mode: vState.audio_mode,
        profile_name: profile,
        num_clips: numClips,
        custom_notes: notes,
        has_subtitles: hasSubtitles,
        recipe: editedRecipe,
        stage: "auto",
        video_provider: videoProvider,
      });

      projectId = res.project_id;
      mediaSignature = "";
      if (res.manifest?.recipe) {
        populateEditorFromRecipe(res.manifest.recipe);
      }
      if (res.manifest) {
        renderProject(res.manifest);
      }
      if (typeof refreshAll === "function") refreshAll(true);
    } catch (error) {
      const autoBtn = document.getElementById("cookingAutoFinalBtn");
      if (autoBtn) autoBtn.disabled = false;
      show(error.message, true);
    }
  }

  async function startManualStage(stage) {
    try {
      if (!projectId) throw new Error("Hãy bấm '1. Lưu dự án từ kịch bản' trước khi chạy từng bước.");
      if (stage === "video" && !document.getElementById("cookingReviewed")?.checked) {
        throw new Error("Hãy kiểm tra ảnh Storyboard 2K và tích xác nhận đủ 6 ô trước khi tạo video.");
      }
      const profile = (document.getElementById("cookingAccountSelect")?.value || "").trim();
      const videoProvider = (document.getElementById("cookingVideoProvider")?.value || "google_flow").trim();
      await call("/api/cooking/run", {
        project_id: projectId,
        stage,
        profile_name: profile,
        storyboards_reviewed: Boolean(document.getElementById("cookingReviewed")?.checked),
        video_provider: videoProvider,
      });
      show("⏳ Đã khởi chạy bước " + stage + ". Hệ thống đang tự động cập nhật tiến trình...");
      await refresh();
    } catch (error) {
      show(error.message, true);
    }
  }

  async function loadExistingCookingProject(targetPid) {
    if (!targetPid) return;
    const res = await call(`/api/cooking/status?project_id=${encodeURIComponent(targetPid)}`);
    const proj = res.project;
    projectId = proj.project_id;
    mediaSignature = "";

    if (proj.recipe) {
      const rec = proj.recipe;
      const vSel = document.getElementById("cookingVoiceSelect");
      const customInp = document.getElementById("cookingCustomVoiceId");
      if (vSel) {
        if (rec.audio_mode === "voice" && (rec.voice_key || rec.voice_id)) {
          const voices = cachedDefaults?.voices || [];
          const match = voices.find(
            v => v.key === rec.voice_key || v.key === rec.voice_id || v.voice_id === rec.voice_id
          );
          if (match) {
            vSel.value = match.key;
          } else {
            vSel.value = "__CUSTOM__";
            if (customInp) customInp.value = rec.voice_id || "";
          }
        } else {
          vSel.value = "__ASMR__";
        }
      }
      const subChk = document.getElementById("cookingSubtitles");
      if (subChk) subChk.checked = !!rec.has_subtitles;
      syncVoiceDependentControls();
      populateEditorFromRecipe(rec);
    }

    const accSel = document.getElementById("cookingAccountSelect");
    if (accSel && proj.profile) {
      const hasOpt = Array.from(accSel.options).some(o => o.value === proj.profile);
      if (!hasOpt) {
        const opt = document.createElement("option");
        opt.value = proj.profile;
        opt.textContent = proj.profile;
        accSel.appendChild(opt);
      }
      accSel.value = proj.profile;
    }
    const revChk = document.getElementById("cookingReviewed");
    if (revChk) revChk.checked = !!proj.storyboards_reviewed;
    const provSel = document.getElementById("cookingVideoProvider");
    if (provSel && proj.video_provider) provSel.value = proj.video_provider;

    renderProject(proj);
  }

  window.openCookingStudio = async (existingProjectId = "", initialDish = "") => {
    const existingModal = document.getElementById("cookingStudioModal");
    if (existingModal) {
      if (existingProjectId) {
        await loadExistingCookingProject(existingProjectId);
      } else if (initialDish) {
        const inp = document.getElementById("cookingDish");
        if (inp) inp.value = initialDish;
        await generateScriptPreview(true);
      }
      return;
    }

    const defaults = await loadCookingDefaultsWithFallback();
    cachedDefaults = defaults;
    const voices = defaults.voices || [];
    const accounts = defaults.accounts || [];
    const suggested = defaults.suggested_dishes || [];
    const recent = defaults.recent_projects || [];

    const cookingVoices = voices.filter(v => v.recommended_for_cooking);
    const otherVoices = voices.filter(v => !v.recommended_for_cooking);
    const fmtVoiceOpt = v => {
      const icon = v.gender === "male" ? "👨" : "👩";
      const reg = v.region === "south" ? "Miền Nam" : v.region === "central" ? "Miền Trung" : "Miền Bắc";
      return `<option value="${esc(v.key)}" ${v.key === defaults.default_voice_key ? "selected" : ""}>${icon} ${esc(v.name)} [${reg}]</option>`;
    };

    const voiceOptionsHtml = `
      ${cookingVoices.length ? `<optgroup label="🍲 Giọng Đề Xuất Cho Nấu Ăn & Ẩm Thực (${cookingVoices.length})">${cookingVoices.map(fmtVoiceOpt).join("")}</optgroup>` : ""}
      ${otherVoices.length ? `<optgroup label="🎙️ Giọng Khác Trong Thư Viện (${otherVoices.length})">${otherVoices.map(fmtVoiceOpt).join("")}</optgroup>` : ""}
      <optgroup label="🎧 Chế Độ Không Giọng Đọc">
        <option value="__ASMR__">🎧 Chỉ ASMR tự nhiên (Không lời thoại)</option>
      </optgroup>
      <optgroup label="⚙️ Nâng Cao">
        <option value="__CUSTOM__">✍️ Nhập mã Voice UUID tùy chỉnh...</option>
      </optgroup>
    `;

    const accountOptionsHtml = accounts
      .map(
        a =>
          `<option value="${esc(a.profile_name)}" ${a.profile_name === defaults.default_profile ? "selected" : ""}>${
            a.has_cookies ? "✅" : "⚠️"
          } ${esc(a.display_label || a.profile_name)}</option>`
      )
      .join("");

    const recentOptionsHtml = recent
      .map(
        p =>
          `<option value="${esc(p.project_id)}">${p.has_final ? "🎬" : "📁"} ${esc(p.dish)} (${
            p.audio_mode === "voice" ? "Có Voice" : "ASMR"
          } · ${esc(p.status)})</option>`
      )
      .join("");

    const startDish = (initialDish || defaults.recipe?.dish || "Sườn xào chua ngọt").trim();
    projectId = "";
    currentRecipe = null;
    mediaSignature = "";

    const modal = document.createElement("div");
    modal.id = "cookingStudioModal";
    modal.style.cssText =
      "position:fixed;inset:0;z-index:100000;background:rgba(3,7,18,0.88);backdrop-filter:blur(4px);overflow:auto;padding:20px;color:#e2e8f0;";

    modal.innerHTML = `
      <div style="position:relative;max-width:1220px;margin:auto;background:linear-gradient(180deg,#111827,#090d16);border:1px solid rgba(245,158,11,0.42);border-radius:16px;padding:18px 22px 20px;box-shadow:0 20px 50px rgba(0,0,0,0.65);">
        <!-- HEADER -->
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.09);">
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
              <span style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#050811;font-weight:900;font-size:12px;padding:3px 10px;border-radius:6px;">TEMPLATE #005</span>
              <h2 style="margin:0;font-size:18.5px;color:#fff;">🍲 Nấu Ăn POV · Tự Sinh Kịch Bản → Storyboard 2K → Video Final 1080p</h2>
            </div>
            <p style="margin:5px 0 0;font-size:12.5px;color:#94a3b8;">
              Chỉ cần <b>gõ tên món ăn</b> + <b>chọn giọng đọc trong danh sách</b> + <b>chọn tài khoản</b> rồi bấm <b>🚀 Tạo Video Final Luôn</b>. (Bấm <b>ESC</b> hoặc nút <b>✕</b> góc phải để đóng)
            </p>
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-shrink:0;">
            ${
              recent.length
                ? `<select id="cookingRecentSelect" style="max-width:225px;background:#0b1120;border:1px solid rgba(255,255,255,0.16);color:#cbd5e1;padding:6px 9px;border-radius:8px;font-size:12px;">
                    <option value="">📂 Dự án đã tạo (${recent.length})...</option>
                    ${recentOptionsHtml}
                  </select>`
                : ""
            }
            <button id="cookingDemo" type="button" class="btn btn-outline" style="padding:6px 11px;font-size:12px;white-space:nowrap;">▶️ Xem Demo V2</button>
            <button id="cookingClose" type="button" title="Đóng cửa sổ (Phím tắt: ESC)" aria-label="Đóng" style="cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:5px;height:34px;padding:0 12px;border-radius:9px;background:rgba(239,68,68,0.18);border:1px solid rgba(239,68,68,0.55);color:#fca5a5;font-size:13px;font-weight:900;white-space:nowrap;transition:all 0.15s;" onmouseover="this.style.background='#ef4444';this.style.color='#fff';" onmouseout="this.style.background='rgba(239,68,68,0.18)';this.style.color='#fca5a5';">✕ Đóng</button>
          </div>
        </div>

        <!-- MAIN 1-CLICK FORM -->
        <div style="margin-top:14px;padding:15px 16px;border-radius:13px;background:rgba(15,23,42,0.78);border:1px solid rgba(99,102,241,0.35);display:flex;flex-direction:column;gap:12px;">
          <div style="display:grid;grid-template-columns:1.25fr 1.25fr 1fr;gap:12px;align-items:start;">
            <!-- Cột 1: Tên món ăn -->
            <div>
              <label style="display:block;font-size:12px;font-weight:800;color:#fcd34d;margin-bottom:5px;">🍲 1. Nhập Tên Món Ăn Cần Làm Video</label>
              <input id="cookingDish" style="width:100%;padding:9px 12px;border-radius:9px;background:#060a13;border:1px solid rgba(252,211,77,0.45);color:#fff;font-size:13.5px;font-weight:700;" placeholder="VD: Sườn xào chua ngọt, Thịt kho tàu..." value="${esc(startDish)}" />
              <div style="display:flex;gap:5px;flex-wrap:wrap;margin-top:7px;">
                ${suggested
                  .slice(0, 8)
                  .map(
                    d =>
                      `<button type="button" class="cooking-dish-chip" data-dish="${esc(d)}" style="cursor:pointer;padding:3px 8px;border-radius:999px;background:#131c2e;border:1px solid rgba(255,255,255,0.12);color:#cbd5e1;font-size:11px;">${esc(d)}</button>`
                  )
                  .join("")}
              </div>
            </div>

            <!-- Cột 2: Chọn Giọng Đọc từ Thư Viện -->
            <div>
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;gap:6px;">
                <label style="font-size:12px;font-weight:800;color:#34d399;margin:0;">🎙️ 2. Chọn Giọng Đọc (Thư Viện Voice)</label>
                <button type="button" id="cookingVoicePreviewBtn" class="btn btn-xs btn-amber" style="padding:3px 9px;font-size:11px;font-weight:800;">🔊 Nghe thử</button>
              </div>
              <select id="cookingVoiceSelect" style="width:100%;padding:9px 10px;border-radius:9px;background:#060a13;border:1px solid rgba(16,185,129,0.45);color:#fff;font-size:12.5px;font-weight:700;">
                ${voiceOptionsHtml}
              </select>
              <div id="cookingCustomVoiceWrap" style="display:none;margin-top:6px;">
                <input id="cookingCustomVoiceId" style="width:100%;padding:7px 10px;border-radius:8px;background:#060a13;border:1px solid rgba(255,255,255,0.2);color:#e2e8f0;font-size:12px;" placeholder="Dán mã Voice UUID 36 ký tự trên Google Flow..." />
              </div>
              <audio id="cookingVoiceAudio" controls style="display:none;width:100%;height:30px;margin-top:6px;"></audio>
            </div>

            <!-- Cột 3: Chọn Tài Khoản Google & Nguồn Tạo Video -->
            <div>
              <label style="display:block;font-size:12px;font-weight:800;color:#67e8f9;margin-bottom:5px;">🔑 3. Chọn Tài Khoản Google & Nguồn Video</label>
              <select id="cookingAccountSelect" style="width:100%;padding:9px 10px;border-radius:9px;background:#060a13;border:1px solid rgba(56,189,248,0.45);color:#fff;font-size:12.5px;font-weight:700;">
                ${accountOptionsHtml}
              </select>
              <select id="cookingVideoProvider" title="Chọn nền tảng tạo Video 8s 1080p từ Storyboard 2K" style="width:100%;margin-top:6px;padding:6px 9px;border-radius:8px;background:#09131f;border:1px solid rgba(16,185,129,0.45);color:#6ee7b7;font-size:11.5px;font-weight:700;">
                <option value="google_flow" ${defaults.default_video_provider !== "google_vids" ? "selected" : ""}>🎬 Video qua Google Flow (Hỗ trợ Voice UUID)</option>
                <option value="google_vids" ${defaults.default_video_provider === "google_vids" ? "selected" : ""}>🌐 Video qua Google Vids Omni 1080p (Không reCAPTCHA)</option>
              </select>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:7px;align-items:center;">
                <select id="cookingNumClips" title="Số phân cảnh 8 giây" style="width:100%;padding:6px 8px;border-radius:8px;background:#0b1120;border:1px solid rgba(255,255,255,0.15);color:#cbd5e1;font-size:11.5px;font-weight:700;">
                  <option value="2">🎞️ 2 cảnh × 8s (16s)</option>
                  <option value="3" selected>🎞️ 3 cảnh × 8s (24s Chuẩn)</option>
                  <option value="4">🎞️ 4 cảnh × 8s (32s)</option>
                </select>
                <label id="cookingSubtitlesWrap" style="display:flex;align-items:center;gap:5px;font-size:11.5px;color:#cbd5e1;cursor:pointer;margin:0;" title="Tùy chọn đốt phụ đề lời dẫn tiếng Việt gọn gàng lên Video Final">
                  <input type="checkbox" id="cookingSubtitles" style="width:auto;" />
                  <span>🔤 Kèm phụ đề TV</span>
                </label>
              </div>
            </div>
          </div>

          <!-- Ghi chú nhỏ + Hàng Nút Chạy Luôn -->
          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding-top:8px;border-top:1px solid rgba(255,255,255,0.08);">
            <input id="cookingNotes" style="flex:1;min-width:220px;padding:8px 11px;border-radius:8px;background:#060a13;border:1px solid rgba(255,255,255,0.12);color:#cbd5e1;font-size:12px;" placeholder="📝 Ghi chú thêm (tùy chọn, VD: nấu nồi đất, vị cay đậm, thêm hành lá... — để trống hệ thống vẫn tự sinh chuẩn)" />
            <button type="button" id="cookingGenScriptBtn" class="btn btn-amber" style="padding:9px 14px;font-size:12.5px;font-weight:800;">✨ Tự sinh kịch bản</button>
            <button type="button" id="cookingAutoFinalBtn" class="btn btn-success" style="padding:10px 20px;font-size:13.5px;font-weight:900;box-shadow:0 6px 20px rgba(16,185,129,0.35);">
              🚀 Tạo Video Final Luôn (Tự Động 100%)
            </button>
            <button type="button" id="cookingStopBtn" class="btn btn-danger" style="display:none;padding:9px 14px;font-size:12.5px;font-weight:800;">⏹️ Dừng chạy</button>
          </div>
        </div>

        <!-- STATUS BANNER -->
        <div id="cookingActiveProjectBadge" style="display:none;margin-top:10px;font-size:12px;color:#93c5fd;"></div>
        <div id="cookingMessage" role="status" style="margin-top:10px;padding:9px 12px;border-radius:9px;border:1px solid rgba(16,185,129,0.38);background:rgba(6,78,59,0.22);font-size:12.5px;font-weight:600;"></div>

        <!-- FINAL VIDEO OUTPUT -->
        <div id="cookingFinal"></div>

        <!-- AUTO-GENERATED SCRIPT CARDS PREVIEW -->
        <div style="margin-top:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
            <span style="font-size:13px;font-weight:800;color:#e2e8f0;">📋 Kịch Bản Phân Cảnh & Lời Dẫn Tự Động (6 ô Storyboard / Cảnh 8 Giây)</span>
            <span style="font-size:11px;color:#94a3b8;">Đổi món hoặc đổi giọng đọc rồi bấm <b>✨ Tự sinh kịch bản</b> để cập nhật xem trước</span>
          </div>
          <div id="cookingScriptSummary" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px;"></div>
        </div>

        <!-- ADVANCED DRAWER: MANUAL EDIT & 2-STEP REVIEWED WORKFLOW -->
        <details style="margin-top:12px;background:#080d18;border:1px solid rgba(255,255,255,0.1);border-radius:11px;padding:10px 14px;">
          <summary style="cursor:pointer;font-size:12.5px;font-weight:800;color:#a5b4fc;user-select:none;">
            🛠️ Tùy chỉnh sâu kịch bản / Chạy kiểm duyệt từng bước (Tạo Storyboard 2K riêng → Xem & Duyệt → Tạo Video)
          </summary>
          <div style="margin-top:12px;display:flex;flex-direction:column;gap:10px;">
            <div id="cookingNarrationWrap">
              <label style="font-size:11.5px;font-weight:700;color:#34d399;display:block;margin-bottom:4px;">🎙️ Kịch bản lời dẫn tiếng Việt (3 câu mỗi cảnh × 6–10 từ, viết số bằng chữ):</label>
              <textarea id="cookingNarration" rows="6" style="width:100%;background:#050811;color:#e2e8f0;border:1px solid rgba(16,185,129,0.35);border-radius:8px;padding:9px;font-size:12px;line-height:1.45;" placeholder="Mỗi cảnh 3 dòng tương ứng nhịp [0–2.6s], [2.6–5.2s], [5.2–7.7s]"></textarea>
            </div>
            <div>
              <label style="font-size:11.5px;font-weight:700;color:#fcd34d;display:block;margin-bottom:4px;">🎬 Hành động chi tiết cho AI Storyboard & Video (6 dòng mỗi cảnh theo đúng thứ tự nấu):</label>
              <textarea id="cookingActions" rows="9" style="width:100%;background:#050811;color:#e2e8f0;border:1px solid rgba(255,255,255,0.18);border-radius:8px;padding:9px;font-size:12px;line-height:1.45;"></textarea>
            </div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
              <button type="button" class="btn btn-amber" id="cookingPrepare">1. Lưu dự án từ kịch bản đang sửa</button>
              <button type="button" class="btn btn-primary" id="cookingBoards" disabled>2. Chỉ tạo Storyboard 2K & upload lại</button>
              <label style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:#cbd5e1;cursor:pointer;margin:0;">
                <input type="checkbox" id="cookingReviewed" style="width:auto;" />
                <span>Tôi đã xem Storyboard 2K: đủ 6 ô, đúng thao tác</span>
              </label>
              <button type="button" class="btn btn-success" id="cookingVideo" disabled>3. Tạo Video 8s & Ghép Final</button>
            </div>
          </div>
        </details>

        <!-- STORYBOARD & SCENE VIDEO GALLERY -->
        <div id="cookingGallery" style="margin-top:14px;display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px;"></div>
      </div>
    `;

    document.body.appendChild(modal);

    // Wire events (Close button + ESC key + Backdrop click)
    const closeCookingModal = () => {
      clearInterval(pollTimer);
      window.removeEventListener("keydown", onCookingEscKey, true);
      const player = document.getElementById("cookingVoiceAudio");
      if (player) player.pause();
      modal.remove();
      if (projectId && window.STATE) {
        window.STATE.currentProjectId = projectId;
        if (window.STATE.projectDetailsCache) delete window.STATE.projectDetailsCache[projectId];
        window.STATE.renderedProjectSig = "";
      }
      if (typeof window.refreshAll === "function") {
        window.refreshAll(false);
      }
    };
    const onCookingEscKey = ev => {
      if (ev.key === "Escape") {
        ev.preventDefault();
        ev.stopPropagation();
        closeCookingModal();
      }
    };
    window.addEventListener("keydown", onCookingEscKey, true);
    modal.addEventListener("click", ev => {
      if (ev.target === modal) closeCookingModal();
    });
    modal.querySelector("#cookingClose").onclick = closeCookingModal;

    modal.querySelector("#cookingVoicePreviewBtn").onclick = playSelectedVoiceSample;

    modal.querySelector("#cookingVoiceSelect").onchange = async () => {
      syncVoiceDependentControls();
      if (!scriptDirtyByUser && (document.getElementById("cookingDish")?.value || "").trim()) {
        await generateScriptPreview(true);
      } else if (currentRecipe) {
        renderScriptSummaryCards(currentRecipe);
      }
    };

    modal.querySelector("#cookingNumClips").onchange = async () => {
      if (!scriptDirtyByUser && (document.getElementById("cookingDish")?.value || "").trim()) {
        await generateScriptPreview(true);
      }
    };

    modal.querySelector("#cookingDish").onkeydown = ev => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        generateScriptPreview(false);
      }
    };

    modal.querySelectorAll(".cooking-dish-chip").forEach(btn => {
      btn.onclick = async () => {
        const d = btn.getAttribute("data-dish") || "";
        const inp = document.getElementById("cookingDish");
        if (inp && d) {
          inp.value = d;
          scriptDirtyByUser = false;
          await generateScriptPreview(true);
        }
      };
    });

    modal.querySelector("#cookingActions").oninput = () => {
      scriptDirtyByUser = true;
    };
    modal.querySelector("#cookingNarration").oninput = () => {
      scriptDirtyByUser = true;
    };

    modal.querySelector("#cookingGenScriptBtn").onclick = () => {
      scriptDirtyByUser = false;
      generateScriptPreview(false);
    };

    modal.querySelector("#cookingAutoFinalBtn").onclick = runOneClickAutoFinal;

    modal.querySelector("#cookingStopBtn").onclick = async () => {
      if (!projectId) return;
      try {
        await call("/api/cooking/stop", { project_id: projectId });
        show("⏹️ Đã dừng tiến trình nấu ăn hiện tại.");
        await refresh();
      } catch (error) {
        show(error.message, true);
      }
    };

    modal.querySelector("#cookingDemo").onclick = async () => {
      try {
        await loadExistingCookingProject(defaults.demo_project_id);
      } catch (error) {
        show(error.message, true);
      }
    };

    const recentSel = modal.querySelector("#cookingRecentSelect");
    if (recentSel) {
      recentSel.onchange = async () => {
        if (recentSel.value) {
          try {
            await loadExistingCookingProject(recentSel.value);
          } catch (error) {
            show(error.message, true);
          }
        }
      };
    }

    modal.querySelector("#cookingPrepare").onclick = async () => {
      try {
        const dish = (document.getElementById("cookingDish")?.value || "").trim();
        if (!dish) throw new Error("Vui lòng nhập tên món ăn.");
        const vState = getSelectedVoiceState();
        if (vState.audio_mode === "voice" && !vState.voice_id) {
          throw new Error("Vui lòng chọn giọng đọc trong danh sách!");
        }
        const edited = collectEditedRecipeOrNull();
        const res = await call("/api/cooking/prepare", {
          dish,
          voice_id: vState.voice_id,
          audio_mode: vState.audio_mode,
          num_clips: parseInt(document.getElementById("cookingNumClips")?.value || "3", 10),
          custom_notes: (document.getElementById("cookingNotes")?.value || "").trim(),
          has_subtitles: Boolean(document.getElementById("cookingSubtitles")?.checked && vState.audio_mode === "voice"),
          recipe: edited,
          auto_script: !edited,
        });
        projectId = res.project.project_id;
        mediaSignature = "";
        modal.querySelector("#cookingReviewed").checked = false;
        populateEditorFromRecipe(res.project.recipe);
        renderProject(res.project);
        show(`✅ Đã lưu dự án "${res.project.project_id}". Bạn có thể bấm "2. Chỉ tạo Storyboard 2K" hoặc "🚀 Tạo Video Final Luôn".`);
      } catch (error) {
        show(error.message, true);
      }
    };

    modal.querySelector("#cookingBoards").onclick = () => startManualStage("storyboards");
    modal.querySelector("#cookingVideo").onclick = () => startManualStage("video");

    syncVoiceDependentControls();
    pollTimer = setInterval(refresh, 4000);

    if (existingProjectId) {
      try {
        await loadExistingCookingProject(existingProjectId);
      } catch (error) {
        show(error.message, true);
      }
    } else {
      if (defaults.recipe && !initialDish) {
        populateEditorFromRecipe(defaults.recipe);
      }
      await generateScriptPreview(true);
    }
  };
})();
