// static/app.js - komplette Frontend-Engine: rendering, controls, drag/drop, combat modal
(async function(){
  const svg = document.getElementById('mapSVG'); if(!svg){ console.error("mapSVG not found"); return; }
  const ghostContainer = document.getElementById('ghostContainer');
  const q = id => document.getElementById(id);
  const GAME_ID = window.GAME_ID || '';
  function logHistory(txt){ const h=q('history'); if(!h) return; h.textContent = txt; }
  async function fetchJSON(url, opts){ const r = await fetch(url, opts); try { return await r.json(); } catch(e){ console.error('fetchJSON parse',e); return null; } }

  // colors from lobby
  let colors = {};
  try{ const raw = localStorage.getItem('ti_colors_'+GAME_ID); if(raw) colors = JSON.parse(raw); }catch(e){ colors = {}; }
  const fallbackColor = '#1f6feb';

  const SYSTEMS = [
    {id:'s_mec', x:600, y:180, name:'Mecatol Rex'},
    {id:'s_alpha', x:200, y:320, name:'Alpha'},
    {id:'s_beta', x:980, y:360, name:'Beta'},
    {id:'s_gamma', x:700, y:620, name:'Gamma'},
    {id:'s_delta', x:120, y:120, name:'Delta'}
  ];

  svg.innerHTML = '';
  const defs = document.createElementNS(svg.namespaceURI,'defs'); svg.appendChild(defs);
  const viewport = document.createElementNS(svg.namespaceURI,'g'); viewport.id='viewport'; svg.appendChild(viewport);

  function drawBase(){
    viewport.innerHTML = '';
    SYSTEMS.forEach(s=>{
      const g = document.createElementNS(svg.namespaceURI,'g');
      g.setAttribute('id','sys_'+s.id);
      g.setAttribute('transform', `translate(${s.x},${s.y})`);
      g.style.cursor = 'pointer';
      const circle = document.createElementNS(svg.namespaceURI,'circle');
      circle.setAttribute('r',36); circle.setAttribute('cx',0); circle.setAttribute('cy',0);
      circle.setAttribute('fill','url(#planetGrad)'); circle.setAttribute('stroke','rgba(255,255,255,0.04)'); circle.setAttribute('stroke-width','2');
      g.appendChild(circle);
      const label = document.createElementNS(svg.namespaceURI,'text');
      label.setAttribute('x',0); label.setAttribute('y',62); label.setAttribute('text-anchor','middle');
      label.setAttribute('fill','#cfe8ff'); label.setAttribute('font-size','12'); label.textContent=s.name;
      g.appendChild(label);
      const tg = document.createElementNS(svg.namespaceURI,'g'); tg.setAttribute('class','tokens'); tg.setAttribute('transform','translate(-40,40)');
      g.appendChild(tg);
      viewport.appendChild(g);
    });
    if(!defs.querySelector('#planetGrad')){
      const ggrad = document.createElementNS(svg.namespaceURI,'radialGradient'); ggrad.id='planetGrad';
      const stop1 = document.createElementNS(svg.namespaceURI,'stop'); stop1.setAttribute('offset','0%'); stop1.setAttribute('stop-color','#b7dfff');
      const stop2 = document.createElementNS(svg.namespaceURI,'stop'); stop2.setAttribute('offset','60%'); stop2.setAttribute('stop-color','#2d7fb8');
      const stop3 = document.createElementNS(svg.namespaceURI,'stop'); stop3.setAttribute('offset','100%'); stop3.setAttribute('stop-color','#07283b');
      ggrad.appendChild(stop1); ggrad.appendChild(stop2); ggrad.appendChild(stop3); defs.appendChild(ggrad);
    }
  }

  // pan & zoom
  const VIEW_W=1200, VIEW_H=800; svg.setAttribute('viewBox', `0 0 ${VIEW_W} ${VIEW_H}`);
  let scale=1, tx=0, ty=0, isDragging=false, lastX=0, lastY=0;
  function applyTransform(){ viewport.setAttribute('transform', `translate(${tx},${ty}) scale(${scale})`); }
  svg.addEventListener('wheel', ev => {
    ev.preventDefault(); const delta = -ev.deltaY; const zoomAmount = delta > 0 ? 1.12 : 1/1.12;
    const pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY; const ctm = svg.getScreenCTM().inverse();
    const mouse = pt.matrixTransform(ctm); const preX = (mouse.x - tx)/scale; const preY = (mouse.y - ty)/scale;
    scale = Math.max(0.3, Math.min(3.0, scale * zoomAmount));
    tx = mouse.x - preX * scale; ty = mouse.y - preY * scale; applyTransform();
  }, {passive:false});
  svg.addEventListener('pointerdown', ev => { if(ev.target.closest && ev.target.closest('.tokens')) return; isDragging=true; lastX=ev.clientX; lastY=ev.clientY; svg.setPointerCapture(ev.pointerId); svg.style.cursor='grabbing'; });
  window.addEventListener('pointerup', ev => { isDragging=false; svg.style.cursor='grab'; });
  window.addEventListener('pointermove', ev => { if(!isDragging) return; const dx=ev.clientX-lastX, dy=ev.clientY-lastY; lastX=ev.clientX; lastY=ev.clientY; tx+=dx; ty+=dy; applyTransform(); });
  svg.addEventListener('dblclick', ()=>{ scale=1; tx=0; ty=0; applyTransform(); });

  // Shapes map
  const SHAPE_MAP = {
    'Infantry': { kind:'circle', r:5 },
    'Fighter':  { kind:'triangle', size:10 },
    'Cruiser':  { kind:'triangle', size:14 },
    'Destroyer':{ kind:'rect', size:12 },
    'Carrier':  { kind:'rect', size:16 },
    'default':  { kind:'circle', r:6 }
  };

  function createShapeForUnit(u, svgNS, cx, cy){
    const info = SHAPE_MAP[u.type] || SHAPE_MAP['default'];
    if(info.kind === 'circle'){
      const c = document.createElementNS(svgNS,'circle'); c.setAttribute('cx', cx); c.setAttribute('cy', cy); c.setAttribute('r', info.r || 6); return c;
    } else if(info.kind === 'rect'){
      const s = info.size || 12; const r = document.createElementNS(svgNS,'rect'); r.setAttribute('x', cx - s/2); r.setAttribute('y', cy - s/2); r.setAttribute('width', s); r.setAttribute('height', s); return r;
    } else if(info.kind === 'triangle'){
      const s = info.size || 12; const h = s * Math.sqrt(3)/2; const p1 = `${cx},${cy - (2/3)*h}`; const p2 = `${cx - s/2},${cy + (1/3)*h}`; const p3 = `${cx + s/2},${cy + (1/3)*h}`; const poly = document.createElementNS(svgNS,'polygon'); poly.setAttribute('points', `${p1} ${p2} ${p3}`); return poly;
    }
    const c = document.createElementNS(svgNS,'circle'); c.setAttribute('cx',cx); c.setAttribute('cy',cy); c.setAttribute('r','6'); return c;
  }

  // Rendering tokens and interactions
  function renderTokens(state){
    SYSTEMS.forEach(s=>{
      const g = document.getElementById('sys_'+s.id); if(!g) return;
      const tg = g.querySelector('.tokens'); if(tg) tg.innerHTML='';
    });
    if(!state || !state.systems) return;

    state.systems.forEach(sys=>{
      const g = document.getElementById('sys_'+sys.id); if(!g) return;
      const tg = g.querySelector('.tokens');
      let offsetX = 0;
      Object.keys(sys.ships || {}).forEach(playerName=>{
        const units = sys.ships[playerName] || [];
        units.forEach((u, idx)=>{
          const cx = offsetX + (idx%6) * 16; const cy = Math.floor(idx/6) * 18;
          const shape = createShapeForUnit(u, svg.namespaceURI, cx, cy);
          const col = (colors && colors[playerName]) ? colors[playerName] : fallbackColor;
          shape.setAttribute('fill', col); shape.setAttribute('stroke', 'rgba(255,255,255,0.03)');
          shape.setAttribute('data-uid', u.uid); shape.setAttribute('data-player', playerName); shape.setAttribute('data-system', sys.id);
          shape.style.cursor = 'pointer';
          shape.addEventListener('pointerdown', tokenPointerDown);
          shape.addEventListener('click', (ev)=>{ ev.stopPropagation(); const fromSel=q('moveFrom'), unitSel=q('moveUnit'); if(fromSel && unitSel){ fromSel.value = sys.id; populateUnitsForFrom().then(()=>{ const opt=Array.from(unitSel.options).find(o=>o.value===u.uid); if(opt) opt.selected=true; }); } });
          tg.appendChild(shape);
        });
        offsetX += 120;
      });
    });

    SYSTEMS.forEach(s=>{
      const sysG = document.getElementById('sys_'+s.id); if(!sysG) return;
      sysG.onclick = async (ev)=>{
        ev.stopPropagation();
        const toSel = q('moveTo'); if(toSel) toSel.value = s.id;
        const player = q('activePlayer') ? q('activePlayer').value : null;
        const uidSel = q('moveUnit'); const fromSel = q('moveFrom');
        if(player && uidSel && uidSel.value && fromSel && fromSel.value){
          await doMove(player, fromSel.value, s.id, uidSel.value);
        }
      };
    });
  }

  // Drag & Drop
  let dragging = null;
  function tokenPointerDown(ev){
    if(!window.__TI_MOVES_ALLOWED) { console.log('Move blocked: not active player'); return; }
    ev.stopPropagation();
    const target = ev.currentTarget;
    const uid = target.getAttribute('data-uid');
    const player = target.getAttribute('data-player');
    const fromSys = target.getAttribute('data-system');
    const rect = target.getBoundingClientRect();
    const ghost = document.createElement('div'); ghost.className='ghost-token';
    ghost.style.left = (rect.left + rect.width/2 - 7) + 'px'; ghost.style.top = (rect.top + rect.height/2 - 7) + 'px';
    ghost.style.background = target.getAttribute('fill') || '#ddd';
    ghostContainer.appendChild(ghost);
    dragging = {uid, player, fromSys, ghostEl: ghost};
    window.addEventListener('pointermove', tokenPointerMove);
    window.addEventListener('pointerup', tokenPointerUp, {once:true});
    try{ target.setPointerCapture(ev.pointerId); }catch(e){}
  }
  function tokenPointerMove(ev){ if(!dragging) return; dragging.ghostEl.style.left = (ev.clientX - 7) + 'px'; dragging.ghostEl.style.top = (ev.clientY - 7) + 'px'; }
  async function tokenPointerUp(ev){
    if(!dragging) return;
    const elems = document.elementsFromPoint(ev.clientX, ev.clientY);
    let sysId = null;
    for(const el of elems){
      if(!el) continue;
      if(el.id && el.id.startsWith('sys_')){ sysId = el.id.replace('sys_',''); break; }
      if(el.closest){
        const p = el.closest('[id^="sys_"]'); if(p){ sysId = p.id.replace('sys_',''); break; }
      }
    }
    if(sysId && sysId !== dragging.fromSys){
      try{
        const origEl = document.querySelector(`[data-uid="${dragging.uid}"]`);
        if(origEl){
          const targetG = document.getElementById('sys_'+sysId);
          const targetTokens = targetG ? targetG.querySelector('.tokens') : null;
          if(targetTokens){
            const clone = origEl.cloneNode(true);
            clone.setAttribute('data-system', sysId);
            clone.addEventListener('pointerdown', tokenPointerDown);
            targetTokens.appendChild(clone);
            origEl.remove();
          }
        }
      } catch(e){ console.warn('optimistic UI move failed', e); }
      try{ dragging.ghostEl.remove(); }catch(e){}
      const res = await doMove(dragging.player, dragging.fromSys, sysId, dragging.uid, {animate:false});
      if(!res || res.error){ alert('Move wurde abgelehnt oder Fehler auf dem Server. UI wird neu geladen.'); await populateControls(); }
      else { setTimeout(()=> populateControls(), 300); }
    } else {
      try{ dragging.ghostEl.remove(); }catch(e){}
    }
    window.removeEventListener('pointermove', tokenPointerMove);
    dragging = null;
  }

  // Animate move helper
  function getSystemScreenPos(sysId){
    const g = document.getElementById('sys_'+sysId); if(!g) return null;
    const bbox = g.getBBox(); const cx = bbox.x + bbox.width/2, cy = bbox.y + bbox.height/2;
    const pt = svg.createSVGPoint(); pt.x = cx; pt.y = cy;
    return pt.matrixTransform(g.getScreenCTM());
  }
  function animateMove(uid, fromId, toId){
    return new Promise((resolve)=>{
      const start = getSystemScreenPos(fromId); const end = getSystemScreenPos(toId);
      if(!start || !end){ resolve(); return; }
      const ghost = document.createElement('div'); ghost.className='ghost-token';
      ghost.style.left = (start.x - 7) + 'px'; ghost.style.top = (start.y - 7) + 'px';
      const existing = document.querySelector(`[data-uid="${uid}"]`);
      if(existing) ghost.style.background = existing.getAttribute('fill') || '#ddd';
      ghostContainer.appendChild(ghost);
      const duration = 420; const t0 = performance.now();
      function frame(t){
        const p = Math.min(1, (t - t0) / duration); const x = start.x + (end.x - start.x) * p; const y = start.y + (end.y - start.y) * p;
        ghost.style.left = (x - 7) + 'px'; ghost.style.top = (y - 7) + 'px';
        if(p < 1) requestAnimationFrame(frame); else { try{ ghost.remove(); }catch(e){}; resolve(); }
      }
      requestAnimationFrame(frame);
    });
  }

  // doMove returns server response
  async function doMove(player, fromSys, toSys, uid, opts = {animate:false}){
    const payload = { game_id: GAME_ID, player: player, action: { type:'move', from: fromSys, to: toSys, unit_uid: uid } };
    const res = await fetchJSON('/api/move', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    if(!res){ return { ok:false, error:'no_response' }; }
    if(res.ok && !res.combat_pending && opts.animate){ try{ await animateMove(uid, fromSys, toSys); }catch(e){ console.warn('animation error', e); } }
    if(res.combat_pending){
      const j = await fetchJSON('/api/space_combat/get', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ game_id: GAME_ID, system_id: res.system })});
      if(j && j.ok && j.pending){ openCombatModal(j.pending); }
    }
    return res;
  }

  // populateControls + preserve selections
  async function populateControls(){
    const st = await fetchJSON('/api/state?game_id='+encodeURIComponent(GAME_ID));
    if(!st){ console.warn('no state from server'); return; }
    const activeSel = q('activePlayer') ? q('activePlayer').value : null;
    const fromSelVal = q('moveFrom') ? q('moveFrom').value : null;
    const toSelVal = q('moveTo') ? q('moveTo').value : null;
    const unitSelVal = q('moveUnit') ? q('moveUnit').value : null;
    const active = q('activePlayer');
    if(active){ active.innerHTML=''; (st.players || []).forEach(p=>{ const o=document.createElement('option'); o.value=p.name; o.textContent=p.name; active.appendChild(o); }); if(activeSel && Array.from(active.options).some(o=>o.value===activeSel)) active.value=activeSel; else if(active.options.length>0 && !activeSel) active.value = active.options[0].value; }
    const from = q('moveFrom'); const to = q('moveTo'); if(from) from.innerHTML=''; if(to) to.innerHTML='';
    (st.systems || []).forEach(s=>{ const label = s.id + ' — ' + (s.planets && s.planets[0] && s.planets[0].name || ''); if(from){ const o1=document.createElement('option'); o1.value=s.id; o1.textContent=label; from.appendChild(o1); } if(to){ const o2=document.createElement('option'); o2.value=s.id; o2.textContent=label; to.appendChild(o2); } });
    if(from){ if(fromSelVal && Array.from(from.options).some(o=>o.value===fromSelVal)) from.value = fromSelVal; }
    if(to){ if(toSelVal && Array.from(to.options).some(o=>o.value===toSelVal)) to.value = toSelVal; }
    await populateUnitsForFrom(unitSelVal, fromSelVal);
    logHistory((st.history||[]).slice(-60).join('\n'));
    renderTokens(st);
    q('roundNum').textContent = st.round || 0;
    updateUIForTurn(st);
    if(!(st.players && st.players.length)) console.warn('state.players empty');
  }

  async function populateUnitsForFrom(prevUnitUid = null, prevFromVal = null){
    const fromElem = q('moveFrom'); const unitElem = q('moveUnit'); if(!unitElem || !fromElem) return;
    const currentFrom = fromElem.value;
    if(prevFromVal && prevFromVal === currentFrom && unitElem.options && unitElem.options.length > 0){
      if(prevUnitUid){ const existing = Array.from(unitElem.options).find(o => o.value === prevUnitUid); if(existing) existing.selected = true; } return;
    }
    const st = await fetchJSON('/api/state?game_id='+encodeURIComponent(GAME_ID));
    unitElem.innerHTML = '';
    if(!st){ const o=document.createElement('option'); o.value=''; o.textContent='(keine Einheiten)'; unitElem.appendChild(o); return; }
    const sys = (st.systems || []).find(s => s.id === currentFrom);
    const player = q('activePlayer') ? q('activePlayer').value : null;
    if(!sys || !sys.ships || !sys.ships[player] || sys.ships[player].length === 0){
      const o=document.createElement('option'); o.value=''; o.textContent='(keine Einheiten)'; unitElem.appendChild(o); return;
    }
    sys.ships[player].forEach(u=>{ const o=document.createElement('option'); o.value=u.uid; o.textContent=u.type + ' — ' + u.uid; unitElem.appendChild(o); });
    if(prevUnitUid){ const selOpt = Array.from(unitElem.options).find(o => o.value === prevUnitUid); if(selOpt) selOpt.selected = true; }
  }

  // UI lock/unlock depending on current player
  function updateUIForTurn(state){
    const serverActive = state ? (state.current_player || state.active_player || null) : null;
    const localActive = q('activePlayer') ? q('activePlayer').value : null;
    const isAllowed = (serverActive && localActive && (serverActive === localActive));
    const controls = [ q('btnDoMove'), q('btnProduce'), q('btnStrategy'), q('btnNext'), q('btnSave') ];
    controls.forEach(c => { if(c) c.disabled = !isAllowed; });
    window.__TI_MOVES_ALLOWED = !!isAllowed;
  }

  // UI event handlers
  if(q('moveFrom')) q('moveFrom').addEventListener('change', ()=> populateUnitsForFrom());
  if(q('activePlayer')) q('activePlayer').addEventListener('change', ()=> populateUnitsForFrom());
  if(q('btnDoMove')) q('btnDoMove').addEventListener('click', async ()=>{ const player = q('activePlayer').value; const from = q('moveFrom').value; const to = q('moveTo').value; const uid = q('moveUnit').value; if(!player || !from || !to || !uid){ alert('Bitte Player/From/To/Unit wählen'); return; } await doMove(player, from, to, uid, {animate:true}); await populateControls(); });
  if(q('btnRefresh')) q('btnRefresh').addEventListener('click', populateControls);
  if(q('btnProduce')) q('btnProduce').addEventListener('click', async ()=>{ const player = q('activePlayer').value; const unit = q('produceType').value; if(!player){ alert('Choose player'); return; } const r = await fetchJSON('/api/produce', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ game_id: GAME_ID, player: player, unit_type: unit })}); if(r && r.ok){ await populateControls(); } else alert('Produce failed: ' + JSON.stringify(r)); });
  if(q('btnStrategy')) q('btnStrategy').addEventListener('click', async ()=>{ const player = q('activePlayer').value; const card = parseInt(q('strategyCard').value || '0',10); if(!player){ alert('Bitte wähle zuerst den aktiven Spieler.'); return; } if(!card || card < 1 || card > 8){ alert('Wähle eine gültige Strategienummer (1–8).'); return; } q('btnStrategy').disabled=true; q('btnStrategy').textContent='Picking…'; try{ const r = await fetchJSON('/api/strategy_pick', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ game_id: GAME_ID, player: player, card: card })}); if(!r) alert('Keine Antwort vom Server.'); else if(r.ok){ alert('Strategiekarte gewählt: ' + card); await populateControls(); } else { alert('Strategy konnte nicht gewählt werden: ' + (r.error || JSON.stringify(r))); await populateControls(); } }catch(err){ console.error(err); alert('Fehler beim Strategy-Pick'); await populateControls(); } finally{ q('btnStrategy').disabled=false; q('btnStrategy').textContent='Pick Strategy'; } });
  if(q('btnSave')) q('btnSave').addEventListener('click', async ()=>{ const name = prompt('Save name?'); if(!name) return; const r = await fetchJSON('/api/save', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ game_id: GAME_ID, name: name })}); if(r && r.ok) alert('Saved: ' + (r.path||'OK')); else alert('Save failed'); });
  if(q('btnNext')) q('btnNext').addEventListener('click', async ()=>{ const r = await fetchJSON('/api/next', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ game_id: GAME_ID })}); await populateControls(); });

  // Combat modal logic
  const modalBackdrop = q('combatModalBackdrop'); const attackerUnitsEl = q('attackerUnits'); const defenderUnitsEl = q('defenderUnits');
  let currentPending = null;
  function openCombatModal(pending){
    currentPending = pending; modalBackdrop.style.display = 'flex'; modalBackdrop.setAttribute('aria-hidden','false'); q('combatInfo').textContent = `System: ${pending.system_id}`; q('attackerName').textContent = pending.attacker; q('defenderName').textContent = pending.defender; q('attackerHits').textContent = pending.attacker_hits || 0; q('defenderHits').textContent = pending.defender_hits || 0;
    attackerUnitsEl.innerHTML=''; defenderUnitsEl.innerHTML='';
    const createTile = (uid, owner, container) => { const t = document.createElement('div'); t.className='unit-tile'; t.textContent = uid; t.dataset.uid = uid; t.dataset.owner = owner; t.addEventListener('click', ()=> { t.classList.toggle('selected'); enforceSelectionLimits(); }); container.appendChild(t); };
    (pending.attacker_units||[]).forEach(u=> createTile(u.uid || u.uid, pending.attacker, attackerUnitsEl));
    (pending.defender_units||[]).forEach(u=> createTile(u.uid || u.uid, pending.defender, defenderUnitsEl));
    enforceSelectionLimits();
  }
  function enforceSelectionLimits(){ const maxA = currentPending ? (currentPending.attacker_hits||0) : 0; const maxD = currentPending ? (currentPending.defender_hits||0) : 0; const selA = Array.from(attackerUnitsEl.querySelectorAll('.unit-tile.selected')); const selD = Array.from(defenderUnitsEl.querySelectorAll('.unit-tile.selected')); if(selA.length > maxA){ for(let i = selA.length-1; i>=maxA; i--){ selA[i].classList.remove('selected'); } } if(selD.length > maxD){ for(let i = selD.length-1; i>=maxD; i--){ selD[i].classList.remove('selected'); } } q('attackerHits').textContent = maxA - (attackerUnitsEl.querySelectorAll('.unit-tile.selected')||[]).length; q('defenderHits').textContent = maxD - (defenderUnitsEl.querySelectorAll('.unit-tile.selected')||[]).length; }
  q('combatCancel').addEventListener('click', ()=>{ modalBackdrop.style.display='none'; modalBackdrop.setAttribute('aria-hidden','true'); currentPending=null; });
  q('combatResolve').addEventListener('click', async ()=>{ if(!currentPending) return; const attackerSelected = Array.from(attackerUnitsEl.querySelectorAll('.unit-tile.selected')).map(n=>n.dataset.uid); const defenderSelected = Array.from(defenderUnitsEl.querySelectorAll('.unit-tile.selected')).map(n=>n.dataset.uid); if(attackerSelected.length > (currentPending.attacker_hits||0) || defenderSelected.length > (currentPending.defender_hits||0)){ alert('Zu viele Verluste ausgewählt'); return; } const res = await fetchJSON('/api/space_combat/resolve', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ game_id: GAME_ID, system_id: currentPending.system_id, attacker_losses: attackerSelected, defender_losses: defenderSelected })}); if(res && res.ok){ modalBackdrop.style.display='none'; modalBackdrop.setAttribute('aria-hidden','true'); currentPending=null; await populateControls(); } else { alert('Resolve failed: ' + JSON.stringify(res)); } });

  async function checkPendingLoop(){ const st = await fetchJSON('/api/state?game_id='+encodeURIComponent(GAME_ID)); if(st && st.pending_combats){ for(const sysId in st.pending_combats){ const pending = st.pending_combats[sysId]; if(pending){ if(!currentPending || currentPending.system_id !== pending.system_id){ openCombatModal(pending); break; } } } } }

  drawBase(); await populateControls(); setInterval(async ()=>{ await populateControls(); await checkPendingLoop(); }, 2000);

})();
