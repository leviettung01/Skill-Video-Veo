/* Progressive template detail: planned structure, real scene examples, media, docs. */
(() => {
  const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const media = p => '/api/media?path='+encodeURIComponent(p);
  let current;
  window.switchTemplateExplorerTab = name => {
    document.querySelectorAll('.te-panel').forEach(p=>p.hidden=p.dataset.panel!==name);
    document.querySelectorAll('.te-tabs button').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===name)));
  };
  window.renderTemplateExample = (index, targetId='teSceneExamples', projectOverride=null) => {
    const project=projectOverride || (current.demo_projects||[])[Number(index)];
    const target=document.getElementById(targetId);
    if(!project){target.innerHTML='<div class="te-empty">Chưa có dự án mẫu với phân cảnh riêng. Xem cấu trúc thiết kế phía trên và ảnh mẫu trong mục Ảnh & video.</div>';return;}
    target.innerHTML=(project.scenes||[]).map((s,i)=>{
      const duration=s.duration_sec || current?.config?.scene_duration_sec;
      const actions=(s.actions_vn && s.actions_vn.length) ? s.actions_vn : (s.actions||[]);
      const vo=Array.isArray(s.voiceover)?s.voiceover:[];
      return `<details class="te-scene" ${i===0?'open':''}><summary><span class="te-num">${String(i+1).padStart(2,'0')}</span><span class="te-scene-title">${esc(s.scene_title||'Phân cảnh '+(i+1))}<small>${esc(duration||'—')} giây · ${s.video_path?'Có clip thực tế':'Chưa có clip riêng'}</small></span></summary><div class="te-scene-body">
      <div class="te-media-pair"><figure><figcaption>Ảnh tham chiếu / Storyboard 2K</figcaption>${s.image_path?`<a href="${media(s.image_path)}" target="_blank" rel="noopener"><img loading="lazy" src="${media(s.image_path)}" alt="Ảnh cảnh ${i+1}"></a>`:'<p class="te-note">Chưa có ảnh tham chiếu.</p>'}</figure><figure><figcaption>Video phân cảnh</figcaption>${s.video_path?`<video controls preload="none" src="${media(s.video_path)}"></video><a href="${media(s.video_path)}" download>Tải clip</a>`:'<p class="te-note">Chưa có file video riêng.</p>'}</figure></div>
      ${vo.length?`<div class="te-note" style="margin-top:10px;padding:8px 10px;border-radius:8px;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);color:#a7f3d0;"><b>🎙️ Lời dẫn Voice:</b> ${vo.map(x=>`"${esc(x)}"`).join(' · ')}</div>`:''}
      ${actions.length?`<ol class="te-actions">${actions.map((a,n)=>`<li><b>Shot ${n+1}</b>${esc(a)}</li>`).join('')}</ol>`:`<p class="te-note" style="margin-top:12px">${esc(s.scene_description||'')}</p>`}
      ${['image_prompt','video_prompt'].map(k=>s[k]?`<details class="te-prompt"><summary>${k==='image_prompt'?'Prompt ảnh':'Prompt video'} · Xem đầy đủ</summary><pre>${esc(s[k])}</pre></details>`:'').join('')}</div></details>`;
    }).join('')+`<p class="te-note">Nguồn: ${esc(project.name)}. Thời lượng và số cảnh của demo thực tế có thể khác cấu trúc mặc định sau khi dựng.</p><button class="btn btn-outline" onclick="closeModal('modalTemplateDetail');openSampleProductInStudio('${esc(project.id)}','')">Mở dự án này trong Studio</button>`;
  };
  window.renderCookingProjectOverview = (project, background) => {
    const signature=JSON.stringify([project.id,project.products,project.live_status]);
    const body=document.getElementById('curProjBody');
    if(background && body.dataset.cookingSignature===signature)return;
    body.dataset.cookingSignature=signature;
    const product=project.products[0]||{};
    const isVoice=(product.audio_mode||project.audio_mode)==='voice';
    const audioTag=isVoice?`🎙️ ${product.voice_name||'Có Voice'}`:'🎧 ASMR';
    const stepText=project.live_status?.current_step_text||'';
    document.getElementById('livePipelineMonitorBanner').style.display='none';
    document.getElementById('curProjTitle').innerHTML=`<div><b>${esc(project.name)}</b><div class="te-caption">Template #005 · ${esc(product.scenes?.length||0)} phân cảnh · ${esc(audioTag)} · ${product.final_video_path?'Video hoàn tất':(project.is_running?'Đang render tự động':'Đang chuẩn bị')}</div></div>`;
    document.getElementById('curProjActions').innerHTML=`<button class="btn btn-outline" onclick="openTemplateDetailModal('005')">Phân cảnh & Template</button><button class="btn btn-amber" onclick="openCookingStudio('')">➕ Tạo Món Mới</button><button class="btn btn-success" onclick="openCookingStudio('${esc(project.id)}')">🎬 Mở Template #005</button>`;
    body.innerHTML=`<div class="te-shell">${stepText?`<div style="margin-bottom:12px;padding:9px 12px;border-radius:9px;background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.35);color:#6ee7b7;font-size:12.5px;font-weight:600;">${esc(stepText)}</div>`:''}<div class="te-layout"><aside class="te-aside">${product.final_video_path?`<video controls preload="metadata" src="${media(product.final_video_path)}"></video><p><a class="btn btn-success" style="width:100%;text-align:center;" href="${media(product.final_video_path)}" download>⬇️ Tải video hoàn chỉnh</a></p>`:'<p class="te-note">Chưa có video hoàn chỉnh. Bấm <b>🎬 Mở Template #005</b> để theo dõi hoặc chạy tạo video.</p>'}<div class="te-tags"><span class="te-tag">9:16 · 1080p 60FPS</span><span class="te-tag">${esc(audioTag)}</span><span class="te-tag">Storyboard 2K</span></div></aside><main style="min-width:0"><h3>Phân cảnh của dự án</h3><p class="te-note">Xem clip, ảnh Storyboard 2K, lời dẫn và prompt của từng cảnh.</p><div id="cookingSharedScenes"></div></main></div></div>`;
    renderTemplateExample(0,'cookingSharedScenes',{id:project.id,name:project.name,scenes:product.scenes||[]});
  };
  window.renderTemplateExplorer = res => {
    current=res;
    const cfg=res.config||{},code=res.code;
    const body=document.getElementById('tplDetailModalBody');
    const editor=body.firstElementChild?.children[1];
    const video=res.primary_demo_video;
    document.getElementById('tplDetailModalTitle').textContent=`Template #${code} · Chi tiết & phân cảnh`;
    const plans=cfg.scene_breakdown||[],projects=res.demo_projects||[];
    const subOrAudioTag = String(code)==='005' ? '🎙️ Có Voice / 🎧 ASMR' : (cfg.has_subtitles===false?'Không phụ đề':'Có phụ đề');
    body.innerHTML=`<div class="te-shell"><header class="te-head"><div><span class="te-eyebrow">TEMPLATE #${esc(code)}</span><h2>${esc(cfg.name||res.folder_name)}</h2><p>${esc(cfg.description)}</p></div></header><div class="te-layout"><aside class="te-aside">${video?`<video controls preload="metadata" src="${esc(video.url)}"></video>`:'<div class="te-empty">Chưa có demo final</div>'}<div class="te-caption">${esc(cfg.demo_video_caption||video?.label||'')}</div><div class="te-tags"><span class="te-tag">${esc(cfg.scenes_per_video)} cảnh × ${esc(cfg.scene_duration_sec)}s</span><span class="te-tag">${esc(cfg.video_aspect||'9:16')}</span><span class="te-tag">${esc(subOrAudioTag)}</span></div><button class="btn btn-success" style="width:100%" onclick="closeModal('modalTemplateDetail');useTemplateFromMarketplace('${esc(code)}')">Dùng Template #${esc(code)}</button></aside><main style="min-width:0"><nav class="te-tabs" role="tablist" aria-label="Chi tiết template">${[['scenes','Phân cảnh'],['overview','Tổng quan'],['assets','Ảnh & video'],['docs','Tài liệu & Prompt']].map(([id,label])=>`<button role="tab" data-tab="${id}" aria-selected="${id==='scenes'}" onclick="switchTemplateExplorerTab('${id}')">${label}</button>`).join('')}</nav>
    <section class="te-panel" data-panel="scenes"><h3>Cấu trúc thiết kế</h3><p class="te-note">Mục đích và góc máy của từng cảnh trong template.</p><div class="te-plan">${plans.map((p,i)=>`<article><strong>${String(i+1).padStart(2,'0')} · ${esc(p.title)}</strong><p>${esc(p.purpose)}</p>${p.camera?`<details><summary>Góc máy & bố cục</summary><p>${esc(p.camera)}</p></details>`:''}</article>`).join('')}</div><h3>Phân cảnh demo thực tế</h3>${projects.length?`<div class="te-selector"><label for="teExampleSelect">Dự án mẫu</label><select id="teExampleSelect" onchange="renderTemplateExample(this.value)">${projects.map((p,i)=>`<option value="${i}">${esc(p.name)}</option>`).join('')}</select></div>`:''}<div id="teSceneExamples"></div></section>
    <section class="te-panel" data-panel="overview" hidden><h3>Điểm nổi bật</h3><div class="te-plan">${(cfg.highlights||[]).map(h=>`<article><p>${esc(h)}</p></article>`).join('')}</div><h3>Quy trình sản xuất</h3>${(cfg.workflow_steps||[]).map((s,i)=>`<article class="te-step"><strong>${String(i+1).padStart(2,'0')} · ${esc(s.title)}</strong><p>${esc(s.detail)}</p></article>`).join('')}</section>
    <section class="te-panel" data-panel="assets" hidden><h3>Thư viện mẫu</h3><p class="te-note">Ảnh tham chiếu, storyboard và video đã lưu cùng template. Bấm ảnh để xem bản gốc.</p><div class="te-assets">${(res.demo_videos||[]).map(v=>`<figure><video controls preload="none" src="${esc(v.url)}"></video><figcaption>${esc(v.label)}</figcaption></figure>`).join('')}${(res.demo_images||[]).map(a=>`<figure><a href="${esc(a.url)}" target="_blank" rel="noopener"><img loading="lazy" src="${esc(a.url)}" alt="${esc(a.label)}"></a><figcaption>${esc(a.label)}</figcaption></figure>`).join('')}</div></section>
    <section class="te-panel te-docs" data-panel="docs" hidden><h3>Tài liệu & Prompt</h3><p class="te-note">Mở Master prompt, Role Skill và tài liệu nguồn; chỉnh sửa và lưu khi cần.</p><div id="teDocEditor"></div></section></main></div></div>`;
    if(editor)document.getElementById('teDocEditor').appendChild(editor);
    window.renderTemplateExample(0);
  };
})();
