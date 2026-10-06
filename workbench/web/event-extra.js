/* Song estimates and event table, layered over the existing card workbench. */
window.EventPages = (() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = value => Number(value).toLocaleString('zh-CN',{maximumFractionDigits:2});
  const tab = name => window.EventHost.tab(name);
  const notice = message => window.EventHost.notice(message);
  const post = (path, body) => window.EventHost.post(path, body);
  const on = (id, event, callback) => window.EventHost.on(id, event, callback);
  const downloadBlob = (blob, name) => window.EventHost.downloadBlob(blob, name);
  let catalog, archives, state, result, resultInput, currentPage;
  function sync() {
    const host = window.EventHost;
    if (!host) return;
    ({catalog, archives, state, result, resultInput, currentPage} = host);
  }
  const fieldIds = ['planEnd', 'planCurrent', 'planTarget', 'planCurrentShop', 'planShopTarget', 'planCpStart', 'planDailyLimit',
    'planNormalPt', 'planNormalCp', 'planNormalShop', 'planNormalBoost', 'planNormalMinutes',
    'planChallengePt', 'planChallengeCost', 'planChallengeShop', 'planChallengeMinutes'];
  const keyMap = {planEnd:'endAt', planCurrent:'current', planTarget:'target',
    planCurrentShop:'currentShop', planShopTarget:'shopTarget', planCpStart:'cpStart',
    planDailyLimit:'dailyLimit', planNormalPt:'normalPt', planNormalCp:'normalCp',
    planNormalShop:'normalShop', planNormalBoost:'normalBoost', planNormalMinutes:'normalMinutes',
    planChallengePt:'challengePt', planChallengeCost:'challengeCost',
    planChallengeShop:'challengeShop', planChallengeMinutes:'challengeMinutes'};
  let loadedProfile = null, lastSimulation = null, lastPlan = null, planSource = 'manual', planBasis = null, planModelSignature = null;
  let simulations = [], loadedSongsProfile = null, simulationsProfile = null;
  let optimum = null, optimumProfile = null, loadedOptimumProfile = null, optimizingSong = false, songJobId = null;
  let modelProfile = null;
  const key = () => `ournotes-event-plan-v1:${window.Planner?.scope || location.pathname}:${archives.active_id}`;
  const songKey = () => `ournotes-song-results-v1:${window.Planner?.scope || location.pathname}:${archives.active_id}`;
  const optimumKey = () => `ournotes-song-optimum-v1:${window.Planner?.scope || location.pathname}:${archives.active_id}`;
  const dateTimeLocal = date => {
    const d = new Date(date);
    if (!Number.isFinite(d.getTime())) return '';
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  const eventTimeLocal = value => dateTimeLocal(String(value).replaceAll('/', '-').replace(' ', 'T') + '+09:00');
  function defaults() {
    return {endAt:eventTimeLocal(catalog.event.end_at), current:'0',
      target:'675000', currentShop:'0', shopTarget:'', cpStart:'0', dailyLimit:'', normalPt:'', normalCp:'', normalShop:'0',
      normalBoost:'4', normalMinutes:'3', challengePt:'', challengeCost:'200',
      challengeShop:'0', challengeMinutes:'3'};
  }
  function fields() {
    return Object.fromEntries(fieldIds.map(id => [keyMap[id], $(id).value]));
  }
  function writeFields(value) {
    for (const id of fieldIds) $(id).value = value[keyMap[id]] ?? '';
  }
  function loadDraft() {
    if (loadedProfile === archives.active_id) return;
    loadedProfile = archives.active_id;
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(key()) || 'null'); } catch {}
    const draft = {...defaults(), ...saved?.fields};
    const migratedTime = !!saved && draft.endAt === dateTimeLocal(catalog.event.end_at);
    if (migratedTime) draft.endAt = defaults().endAt;
    writeFields(draft);
    planSource = saved?.source || 'manual'; planBasis = saved?.basis || null; modelProfile = saved?.modelProfile || null;
    planModelSignature = saved?.modelSignature || null;
    lastPlan = null; $('planOutput').hidden = true;
    $('planPreviewBoost').value = draft.normalBoost;
    $('planPreviewCost').value = draft.challengeCost;
    sourceLabel();
    if (migratedTime) saveDraft();
  }
  function sourceLabel() {
    const old = planSource === 'model' && (modelProfile !== JSON.stringify(state.profile) || planModelSignature !== window.EventHost.signature);
    $('planSource').textContent = old ? '模型值已过期，请重新计算' : planSource === 'model'
      ? planBasis === 'rank' ? '配队加成＋假设评级 · 活动 #1' : '单曲模型估算 · 活动 #1'
      : '手动实测 / 输入';
    $('planSource').className = 'badge' + (old ? ' warning-badge' : '');
  }
  function saveDraft() {
    const value = {fields:fields(), source:planSource, basis:planBasis, modelProfile, modelSignature:planModelSignature};
    try { localStorage.setItem(key(), JSON.stringify(value)); }
    catch (error) { $('planError').hidden = false; $('planError').textContent = '无法保存活动输入：' + error.message; }
  }
  function renderTeams(resetPlanTeams = false) {
    const teams = result?.teams || [];
    $('simTeam').innerHTML = teams.map((team, index) => `<option value="${index}">队伍 ${index+1} · ${esc(team.reason)} · ${fmt(team.power)} 综合力</option>`).join('');
    $('songNoTeam').hidden = teams.length > 0;
    $('runSong').disabled = teams.length === 0;
    const best = teams.reduce((index, team, i) => team.bonuses_10000.event_pt > (teams[index]?.bonuses_10000.event_pt ?? -1) ? i : index, 0);
    for (const id of ['planNormalTeam', 'planChallengeTeam']) {
      const select = $(id), previous = select.value;
      select.innerHTML = teams.map((team, index) => `<option value="${index}">队伍 ${index+1} · PT +${fmt(team.bonuses_10000.event_pt/100)}% · 徽章 +${fmt(team.bonuses_10000.shop_pt/100)}%</option>`).join('');
      if (teams.length) select.value = !resetPlanTeams && previous !== '' && Number(previous) < teams.length ? previous : String(best);
    }
    $('planNoTeams').hidden = teams.length > 0;
    $('estimatePlan').disabled = teams.length === 0;
  }
  function renderSongs() {
    if (!catalog?.songs) return;
    const challenge = $('simMode').value === 'challenge';
    $('simMethod').querySelector('option[value="skip"]').disabled = challenge;
    if (challenge && $('simMethod').value === 'skip') $('simMethod').value = 'ap';
    syncMethodOptions();
    const old = $('simSong').value;
    const songs = catalog.songs.filter(song => !challenge || song.challenge);
    $('simSong').innerHTML = songs.map(song => `<option value="${song.id}">${esc(song.title)} · #${song.id}</option>`).join('');
    if (songs.some(song => String(song.id) === old)) $('simSong').value = old;
    $('simConsumedLabel').firstChild.textContent = challenge ? '每局 CP 消耗' : '每局 Boost 消耗';
    const costs = challenge ? [200, 400, 800, 1600] : Array.from({length:10}, (_, index) => index + 1);
    $('simConsumed').innerHTML = costs.map(value => `<option value="${value}">${value}</option>`).join('');
    $('simConsumed').value = challenge ? '200' : '4';
  }
  function syncMethodOptions() {
    const skip = $('simMethod').value === 'skip';
    $('simObjective').querySelector('option[value="score"]').disabled = skip;
    if (skip && $('simObjective').value === 'score') $('simObjective').value = 'event_pt';
  }
  function renderSimulation(value) {
    const reward = value.per_live, score = value.score, skipped = value.method === 'skip';
    $('songResult').hidden = false;
    $('songResult').innerHTML = `<div class="panel-head"><h2>${esc(value.song_title)} · ${esc(value.difficulty.toUpperCase())}</h2><span class="badge">模型估算 · ${esc(value.source.snapshot)}</span></div>
      <div class="plan-stats"><div><strong>${fmt(value.power)}</strong><span>实际歌曲综合力</span></div><div><strong>${fmt(score.minimum_score)}${score.maximum_score !== score.minimum_score ? '–'+fmt(score.maximum_score) : ''}</strong><span>${skipped ? '模型参考分 · 不记最高分' : '预计分数范围'}</span></div><div><strong>${esc(score.rank)}</strong><span>${skipped ? '固定奖励评级' : '保守评级'}</span></div><div><strong>${fmt(reward.event_pt)}</strong><span>每局活动 PT</span></div><div><strong>${fmt(reward.cp)}</strong><span>每局获得 CP</span></div><div><strong>${fmt(reward.shop_pt)}</strong><span>每局活动徽章</span></div></div>
      <p class="tiny muted">${skipped ? '普通演出跳过固定按 C 评级结算，不更新最高分；模型参考分不参与奖励计算。' : '理论 AP/PERFECT，按技能顺序最低评级估算。'}普通演出不计活动参数加成；挑战演出计入。活动规则固定为 #1。</p>
      <button id="useSongResult" class="primary">填入活动拉表 →</button>`;
    $('useSongResult').addEventListener('click', () => useSimulation(value));
  }
  function renderOptimum() {
    $('songOptimizeResult').hidden = !optimum;
    if (!optimum) return;
    const row = optimum.team, skipped = optimum.method === 'skip', memberCards = new Map(catalog.members.map(card => [card.id, card]));
    const snapCards = new Map(catalog.snaps.map(card => [card.id, card]));
    const slots = row.member_ids.map((id, index) => {
      const member = memberCards.get(id), snap = snapCards.get(row.snap_ids[index]);
      return `<div class="score-slot"><img src="${esc(member.thumbnail)}" alt=""><div><strong>${id === row.leader_id ? '队长 · ' : ''}${esc(member.title)}</strong><a href="https://haneoka.org/intl/zh-CN/member-cards/${id}/" target="_blank" rel="noreferrer">${esc(member.name)} · #${id} ↗</a><small>搭配留影</small><a href="https://haneoka.org/intl/zh-CN/support-cards/${snap.id}/" target="_blank" rel="noreferrer">${esc(snap.title)} · #${snap.id} ↗</a></div></div>`;
    });
    const sameSelection = optimum.mode === $('simMode').value && optimum.song_id === Number($('simSong').value) &&
      optimum.difficulty === $('simDifficulty').value && optimum.method === $('simMethod').value &&
      optimum.consumed === Number($('simConsumed').value) && optimum.objective === $('simObjective').value;
    const goal = {score:'理论分数', event_pt:'每局活动 PT', shop_pt:'每局活动徽章'}[optimum.objective] || '理论分数';
    $('songOptimizeResult').innerHTML = `<div class="panel-head"><div><h2>${esc(optimum.song_title)} · ${sameSelection ? '当前' : '上次'}卡库${goal}最高</h2><p class="tiny muted">${esc(optimum.mode === 'challenge' ? '挑战' : '普通')} / ${esc(optimum.difficulty.toUpperCase())} / ${optimum.method === 'ap' ? 'AP' : '跳过'} · ${fmt(optimum.search.visited_member_teams)} 套成员组合已检查 · 数据快照 ${esc(optimum.source.snapshot)}</p></div><span class="badge">${sameSelection ? '完整候选池已搜索' : '与上方模拟条件不同'}</span></div>
      <div class="plan-stats"><div><strong>${fmt(row.score.minimum_score)}${row.score.maximum_score !== row.score.minimum_score ? '–'+fmt(row.score.maximum_score) : ''}</strong><span>${skipped ? '模型参考分 · 不记最高分' : '理论分数范围'}</span></div><div><strong>${esc(row.score.rank)}</strong><span>${skipped ? '固定奖励评级' : '保守评级'}</span></div><div><strong>${fmt(row.power)}</strong><span>歌曲综合力</span></div><div><strong>${fmt(row.bonuses_10000.event_pt/100)}%</strong><span>活动 PT 加成</span></div><div><strong>${fmt(row.per_live.event_pt)}</strong><span>每局活动 PT</span></div><div><strong>${fmt(row.per_live.shop_pt)}</strong><span>每局活动徽章</span></div></div>
      <div class="score-team-grid">${slots.join('')}</div><div class="actions"><button id="useSongOptimum" class="secondary">把收益填入活动拉表 →</button></div><p class="tiny muted">最优范围只包括当前档案已勾选、符合筛选和必带条件的卡牌。${skipped ? '普通跳过固定按 C 奖励结算，不记录最高分。' : 'AP 结果按 120 种技能顺序中的最低评级估算。'}实机结算需核对。</p>`;
    $('useSongOptimum').addEventListener('click', () => useSimulation({...optimum, per_live:row.per_live}));
  }
  function loadOptimum() {
    if (loadedOptimumProfile === archives.active_id) return;
    loadedOptimumProfile = archives.active_id;
    optimumProfile = JSON.stringify(state);
    try {
      const saved = JSON.parse(localStorage.getItem(optimumKey()) || 'null');
      optimum = saved?.profile === optimumProfile && saved?.signature === window.EventHost.signature && saved?.value?.search?.complete ? saved.value : null;
    } catch { optimum = null; }
    renderOptimum();
  }
  async function optimizeSong() {
    if (optimizingSong) return;
    const input = JSON.parse(JSON.stringify(state));
    const profileId = archives.active_id, profile = JSON.stringify(state);
    optimizingSong = true; $('runOptimizeSong').disabled = true;
    $('songOptimizeProgress').hidden = false;
    $('songOptimizeStage').textContent = '正在启动搜索…';
    $('songOptimizeBar').max = 1; $('songOptimizeBar').value = 0;
    try {
      const started = await post('/api/optimize-song', {input, mode:$('simMode').value,
        song_id:Number($('simSong').value), difficulty:$('simDifficulty').value,
        method:$('simMethod').value, consumed:Number($('simConsumed').value), objective:$('simObjective').value});
      songJobId = started.job_id;
      while (true) {
        const response = await (window.plannerFetch || fetch)(`/api/jobs/${songJobId}`);
        const job = await response.json();
        if (!response.ok) throw new Error(job.error || '单曲搜索已失效。');
        $('songOptimizeStage').textContent = `${job.stage || '搜索中'} · ${fmt(job.done || 0)} / ${fmt(job.total || 1)} 套成员组合`;
        $('songOptimizeBar').max = job.total || 1; $('songOptimizeBar').value = job.done || 0;
        if (job.status === 'complete') {
          if (archives.active_id !== profileId || JSON.stringify(state) !== profile) throw new Error('卡组在搜索期间发生变化，结果已丢弃。请重新搜索。');
          optimum = job.result; optimumProfile = profile;
          try { localStorage.setItem(optimumKey(), JSON.stringify({profile, signature:window.EventHost.signature, value:optimum})); }
          catch (error) { notice('最优队伍已计算，但浏览器无法保存记录：' + error.message); }
          renderOptimum(); notice('已按所选目标完成当前卡库的单曲搜索。');
          break;
        }
        if (job.status === 'cancelled') { notice('单曲搜索已取消。'); break; }
        if (job.status === 'error') throw new Error(job.error || '单曲搜索失败。');
        await new Promise(resolve => setTimeout(resolve, 350));
      }
    } finally {
      optimizingSong = false; $('runOptimizeSong').disabled = false;
      songJobId = null;
      $('songOptimizeProgress').hidden = true;
    }
  }
  function loadSimulations() {
    if (loadedSongsProfile === archives.active_id) return;
    loadedSongsProfile = archives.active_id;
    simulationsProfile = JSON.stringify(state.profile);
    try {
      const saved = JSON.parse(localStorage.getItem(songKey()) || '[]');
      simulations = Array.isArray(saved) ? saved.filter(row => row.profile === simulationsProfile && row.signature === window.EventHost.signature).map(row => row.value).slice(0, 30) : [];
    } catch { simulations = []; }
    lastSimulation = null; $('songResult').hidden = true;
    renderSongTable();
  }
  function saveSimulations() {
    simulationsProfile = JSON.stringify(state.profile);
    try { localStorage.setItem(songKey(), JSON.stringify(simulations.map(value => ({profile:simulationsProfile, signature:window.EventHost.signature, value})))); }
    catch (error) { notice('曲目列表未能保存：' + error.message); }
  }
  function renderSongTable() {
    $('songHistory').hidden = simulations.length === 0;
    $('songHistoryRows').innerHTML = simulations.map((value, index) => `<tr>
      <td>${value.mode === 'challenge' ? '挑战' : '普通'} / 队伍 ${value.team_index+1}</td>
      <td>${esc(value.song_title)} · ${esc(value.difficulty.toUpperCase())}</td>
      <td>${value.method === 'skip' ? '不记最高分' : fmt(value.score.minimum_score)}</td><td>${esc(value.score.rank)}</td>
      <td>${fmt(value.per_live.event_pt)}</td><td>${value.mode === 'challenge' ? '−'+fmt(value.consumed) : '+'+fmt(value.per_live.cp)}</td>
      <td>${fmt(value.per_live.shop_pt)}</td><td><button class="text-button" data-use-song="${index}">用于拉表 →</button></td></tr>`).join('');
  }
  async function simulate() {
    if (!result?.teams?.length || !resultInput) throw new Error('请先计算一套队伍。');
    const team = result.teams[Number($('simTeam').value)];
    $('runSong').disabled = true; $('runSong').textContent = '正在计算谱面…';
    try {
      const value = await post('/api/simulate-song', {input:resultInput, team,
        mode:$('simMode').value, song_id:Number($('simSong').value),
        difficulty:$('simDifficulty').value, method:$('simMethod').value,
        consumed:Number($('simConsumed').value)});
      value.team_index = Number($('simTeam').value);
      lastSimulation = value; renderSimulation(value);
      simulations = [value, ...simulations.filter(row => !(row.team_index === value.team_index && row.mode === value.mode &&
        row.song_id === value.song_id && row.difficulty === value.difficulty && row.method === value.method && row.consumed === value.consumed))].slice(0, 30);
      saveSimulations(); renderSongTable();
    } finally { $('runSong').disabled = false; $('runSong').textContent = '计算单曲收益 →'; }
  }
  function useSimulation(value) {
    loadDraft();
    if (value.mode === 'normal') {
      $('planNormalPt').value = value.per_live.event_pt;
      $('planNormalCp').value = value.per_live.cp;
      $('planNormalShop').value = value.per_live.shop_pt;
      $('planNormalBoost').value = value.consumed;
    } else {
      $('planChallengePt').value = value.per_live.event_pt;
      $('planChallengeShop').value = value.per_live.shop_pt;
      $('planChallengeCost').value = value.consumed;
    }
    planSource = 'model'; planBasis = 'song'; modelProfile = JSON.stringify(state.profile); planModelSignature = window.EventHost.signature;
    sourceLabel(); saveDraft(); $('planOutput').hidden = true; lastPlan = null;
    tab('eventPlan'); notice('已将单曲估算填入活动拉表。可以直接改为游戏里的实际结算值。');
  }
  function estimateFromTeams() {
    if (!result?.teams?.length) throw new Error('请先计算配队结果，或在下方填写实测单场收益。');
    const normal = result.teams[Number($('planNormalTeam').value)];
    const challenge = result.teams[Number($('planChallengeTeam').value)];
    if (!normal || !challenge) throw new Error('请选择普通和挑战演出的队伍。');
    const skipped = $('planNormalMethod').value === 'skip';
    const normalRank = skipped ? 'C' : $('planNormalRank').value;
    const challengeRank = $('planChallengeRank').value;
    const boost = Number($('planPreviewBoost').value), cost = Number($('planPreviewCost').value);
    const normalGain = window.EventMath.reward(catalog.event, 'normal', normalRank, boost, normal.bonuses_10000);
    const challengeGain = window.EventMath.reward(catalog.event, 'challenge', challengeRank, cost, challenge.bonuses_10000);
    $('planNormalPt').value = normalGain.event_pt;
    $('planNormalCp').value = normalGain.cp;
    $('planNormalShop').value = normalGain.shop_pt;
    $('planNormalBoost').value = boost;
    $('planChallengePt').value = challengeGain.event_pt;
    $('planChallengeShop').value = challengeGain.shop_pt;
    $('planChallengeCost').value = cost;
    planSource = 'model'; planBasis = 'rank'; modelProfile = JSON.stringify(state.profile);
    planModelSignature = window.EventHost.signature;
    sourceLabel(); saveDraft(); calculate();
    if (lastPlan) notice(`已按普通 ${normalRank}${skipped ? '（跳过）' : ''}、挑战 ${challengeRank} 的假设生成拉表；请用实机结算校正单场收益。`);
  }
  function renderPlan(value) {
    lastPlan = value;
    $('planOutput').hidden = false;
    $('planFeasibility').textContent = value.feasible ? '按所填每日上限可完成' : '超过每日普通场数上限';
    $('planFeasibility').className = 'badge' + (value.feasible ? '' : ' warning-badge');
    const stats = [
      [value.neededNormal, '普通演出'], [value.neededChallenge, '挑战演出'],
      [value.boost, '所需 Boost'], [Math.ceil(value.minutes), '预计分钟'],
      [value.totalPt, '预计最终 PT'], [value.totalShop, '预计最终活动徽章'], [value.cpRemaining, '剩余 CP']];
    $('planStats').innerHTML = stats.map(([n, label]) => `<div><strong>${fmt(n)}</strong><span>${label}</span></div>`).join('');
    $('planRows').innerHTML = value.daily.map(row => `<tr><td>${row.date}</td><td>${fmt(row.normal)}</td><td>${fmt(row.challenge)}</td><td>${fmt(row.boost)}</td><td>${fmt(Math.ceil(row.minutes))} 分</td><td>${fmt(row.cumulative)}</td><td>${fmt(row.shop)}</td><td>${fmt(row.cp)}</td></tr>`).join('');
  }
  function calculate() {
    try {
      const value = window.EventMath.plan(fields());
      $('planError').hidden = true; renderPlan(value); saveDraft();
    } catch (error) { $('planOutput').hidden = true; lastPlan = null;
      $('planError').hidden = false; $('planError').textContent = error.message; }
  }
  function exportCsv() {
    if (!lastPlan) { calculate(); if (!lastPlan) return; }
    const lines = [['日期','普通场数','挑战场数','Boost','耗时分钟','累计活动PT','累计活动徽章','剩余CP'],
      ...lastPlan.daily.map(r => [r.date,r.normal,r.challenge,r.boost,r.minutes,r.cumulative,r.shop,r.cp])];
    const csv = '\ufeff' + lines.map(row => row.map(v => `"${String(v).replaceAll('"','""')}"`).join(',')).join('\r\n');
    downloadBlob(new Blob([csv], {type:'text/csv;charset=utf-8'}), 'OurNotes-活动拉表.csv');
  }
  function init() {
    sync();
    $('resultToSong').addEventListener('click', () => tab('song'));
    $('resultToPlan').addEventListener('click', () => { tab('eventPlan'); $('teamRewardPanel').scrollIntoView({behavior:'smooth',block:'start'}); });
    $('songToTeam').addEventListener('click', () => tab('plan'));
    $('planToSong').addEventListener('click', () => tab('song'));
    $('planNormalMethod').addEventListener('change', () => {
      const skipped = $('planNormalMethod').value === 'skip';
      $('planNormalRank').disabled = skipped;
      $('planNormalRank').value = skipped ? 'C' : 'B';
    });
    $('simMode').addEventListener('change', () => {
      $('simObjective').value = $('simMode').value === 'challenge' ? 'score' : 'event_pt';
      renderSongs(); renderOptimum();
    });
    for (const id of ['simSong','simDifficulty','simConsumed','simObjective']) $(id).addEventListener('change', renderOptimum);
    $('simMethod').addEventListener('change', () => { syncMethodOptions(); renderOptimum(); });
    on('runSong', 'click', simulate);
    on('runOptimizeSong', 'click', optimizeSong);
    on('cancelOptimizeSong', 'click', async () => { if (songJobId) await post(`/api/jobs/${songJobId}/cancel`, {}); });
    on('calculatePlan', 'click', calculate);
    on('estimatePlan', 'click', estimateFromTeams);
    on('exportSchedule', 'click', exportCsv);
    $('songHistoryRows').addEventListener('click', event => {
      const button = event.target.closest('[data-use-song]');
      if (button) useSimulation(simulations[Number(button.dataset.useSong)]);
    });
    $('clearSongHistory').addEventListener('click', () => { simulations = []; saveSimulations(); renderSongTable(); });
    const draftChanged = id => {
      if (id.startsWith('planNormal') || id.startsWith('planChallenge')) {
        planSource = 'manual'; planBasis = null; modelProfile = null; planModelSignature = null; sourceLabel();
      }
      $('planOutput').hidden = true; lastPlan = null; saveDraft();
    };
    for (const id of fieldIds) {
      $(id).addEventListener('input', () => draftChanged(id));
      $(id).addEventListener('change', () => draftChanged(id));
    }
    renderTeams(); renderSongs(); loadDraft(); loadSimulations(); loadOptimum(); onTab(currentPage);
  }
  function onTab(name) {
    sync();
    if (!catalog || !state) return;
    if (name === 'song') { loadSimulations(); loadOptimum(); renderTeams(); }
    if (name === 'eventPlan') { loadDraft(); sourceLabel(); }
  }
  function onStateChanged() { sync(); if (catalog) { renderTeams(); sourceLabel();
    if (optimumProfile !== JSON.stringify(state)) { optimum = null; optimumProfile = JSON.stringify(state); renderOptimum(); }
    if (simulationsProfile !== JSON.stringify(state.profile)) {
      simulations = []; simulationsProfile = JSON.stringify(state.profile);
      $('songResult').hidden = true; renderSongTable();
    } } }
  function onResult() { sync(); if (catalog) renderTeams(true); }
  return {init, onTab, onStateChanged, onResult};
})();
