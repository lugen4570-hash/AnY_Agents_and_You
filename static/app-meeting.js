// Agent 进度放在消息流里，头像可展开公开的进度文本。
let lastRun={running:[],queued:0};
const liveCards=new Map();
function newAgentProgress(id){
  const node=document.createElement('details');node.className='agent-progress';node.style.setProperty('--c',agentColor(id));
  node.innerHTML='<summary><span class="progress-face">'+esc(agentLetter(id))+'</span><span>'+esc((agentMeta(id)||{}).label||id)+'</span><span class="progress-label"></span></summary><div class="progress-text"></div>';
  return {node,label:node.querySelector('.progress-label'),text:node.querySelector('.progress-text')};
}
function attachAgentProgress(message,element){
  const active=liveCards.get(message.speaker);
  if(!message.progress){settleAgentProgress(message.speaker);return}
  const card=active||newAgentProgress(message.speaker);
  liveCards.delete(message.speaker);
  card.label.textContent='过程';card.text.textContent=message.progress;
  element.appendChild(card.node);
}
function settleAgentProgress(ai){
  const card=liveCards.get(ai);if(!card)return;
  liveCards.delete(ai);
  if(!card.text.textContent)card.node.remove();else card.label.textContent='过程';
}
function drawLiveCards(running,live){
  for(const id of liveCards.keys())if(!running.includes(id))settleAgentProgress(id);
  const atBottom=feed.scrollHeight-feed.scrollTop-feed.clientHeight<60;
  for(const id of running){
    let card=liveCards.get(id);
    if(!card){
      card=newAgentProgress(id);liveCards.set(id,card);feed.appendChild(card.node);
    }
    const entry=live[id]||{};
    card.label.textContent=entry.secs>=60?'思考中 · '+fmtDur(entry.secs):'思考中';
    const text=entry.details||entry.text;if(text&&card.text.textContent!==text)card.text.textContent=text;
  }
  if(atBottom&&running.length)feed.scrollTop=feed.scrollHeight;
}
function fmtDur(s){return s<60?s+' 秒':s<3600?Math.floor(s/60)+' 分钟':Math.floor(s/3600)+' 小时 '+Math.floor(s%3600/60)+' 分'}
function drawStatus(){
  const lv=(S&&S.live)||{};
  const running=(S&&S.running)||lastRun.running;
  const rn=running.map(x=>x.startsWith('compact:')?x.slice(8)+' 正在压缩':x==='compact'?'正在压缩':x+' 正在想'+(lv[x]&&lv[x].secs>=60?'（'+fmtDur(lv[x].secs)+'）':''));
  const stT=document.getElementById('stText');
  if(rn.length){st.classList.add('on');stT.textContent=rn.join('，')+'…'+(lastRun.queued?' · 排队 '+lastRun.queued+' 条':'')}
  else if(lastRun.queued){st.classList.add('on');stT.textContent='队列还有 '+lastRun.queued+' 条'}
  else st.classList.remove('on');
  drawLiveCards(running.filter(id=>!id.startsWith('compact')),lv);
}
// 公告
const annEl=document.getElementById('ann'),annText=document.getElementById('annText'),annEdit=document.getElementById('annEdit'),annTa=document.getElementById('annTa'),annBtn=document.getElementById('annBtn');
let annVal='';
function showAnn(){annText.textContent=annVal.trim()||'（还没写这场会议的目标，点"编辑目标"写一句：要做成什么）'}
function loadAnn(){if(S&&annEdit.style.display!=='block'){annVal=S.announcement||'';showAnn()}}
annText.onclick=()=>annEl.classList.toggle('open');
annBtn.onclick=()=>{annTa.value=annVal;annEdit.style.display='block';annEl.classList.remove('open');annText.style.display='none';annBtn.style.display='none';annTa.focus()};
function closeEdit(){annEdit.style.display='none';annText.style.display='';annBtn.style.display=''}
document.getElementById('annCancel').onclick=closeEdit;
document.getElementById('annSave').onclick=async()=>{
  try{
    const r=await fetch(api('announcement'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:annTa.value})});
    if(!r.ok)throw 0;annVal=annTa.value;showAnn();closeEdit();poll();
  }catch(e){alert('目标保存失败（可能超过 16KB）')}
};

// 看板
const boardList=document.getElementById('boardList'),boardBtn=document.getElementById('boardBtn'),bText=document.getElementById('bText');
let boardSig='';
boardBtn.onclick=()=>annEl.classList.toggle('open');
function drawBoard(){
  const items=(S&&S.board)||[];
  const todo=items.filter(i=>i.kind==='todo'&&!i.done).length;
  boardBtn.textContent='看板'+(items.length?' '+(todo?todo+' 待办':items.length):'');
  const sig=JSON.stringify(items);if(sig===boardSig)return;boardSig=sig;
  const sections=[
    ['todo','待办',items.filter(i=>i.kind==='todo'&&!i.done)],
    ['note','公告',items.filter(i=>i.kind!=='todo')],
    ['done','已完成',items.filter(i=>i.kind==='todo'&&i.done)],
  ];
  boardList.innerHTML=items.length?sections.filter(([, , rows])=>rows.length).map(([key,label,rows])=>
    '<li class="board-section-heading" data-board-section="'+key+'"><strong>'+label+'</strong><span>'+rows.length+'</span></li>'+
    rows.sort((a,b)=>a.id-b.id).map(i=>'<li class="'+(i.done?'done':'')+'" data-id="'+i.id+'">'+
      (i.kind==='todo'?'<input type="checkbox" aria-label="标记待办 #'+i.id+'"'+(i.done?' checked':'')+'>':'<span class="pin" aria-hidden="true">›</span>')+
      '<span class="bt">#'+i.id+' '+esc(i.text)+'<small>'+esc(i.by)+'</small></span><button type="button" class="bx" title="删掉">&times;</button></li>').join('')
  ).join('')
    :'<li class="empty">（空的。你和会里的 AI 都能往这写公告、待办）</li>';
}
async function boardPost(o){const [ok,j]=await post(api('board'),o);if(!ok)alert(j.error||'失败');await loadState();poll()}
boardList.onclick=e=>{
  const li=e.target.closest('li[data-id]');if(!li)return;const id=+li.dataset.id;
  if(e.target.matches('input[type=checkbox]'))boardPost({op:e.target.checked?'done':'undone',id});
  else if(e.target.closest('.bx')&&confirm('删掉 #'+id+'？'))boardPost({op:'del',id});
};
async function boardAdd(){const t=bText.value.trim();if(!t)return;bText.value='';await boardPost({op:'add',kind:document.getElementById('bKind').value,text:t})}
document.getElementById('bAdd').onclick=boardAdd;
bText.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.isComposing){e.preventDefault();boardAdd()}});

// 会议状态 / 顶部按钮
const titleEl=document.getElementById('title');
const meetingToolsButton=document.getElementById('sideToggleBtn');
const meetingSide=document.getElementById('side'),meetingSideBg=document.getElementById('sideBg');
const meetingSidePin=document.getElementById('sidePin');
const wideMeetingSide=typeof matchMedia==='function'?matchMedia('(min-width:1200px)'):null;
let meetingSidePinned=false;
function syncMeetingSideLayout(){
  const open=meetingSide.classList.contains('on'),docked=open&&meetingSidePinned&&wideMeetingSide?.matches;
  document.body.classList.toggle('meeting-side-docked',!!docked);
  meetingSideBg.classList.toggle('on',open&&!docked);
  meetingSide.setAttribute('role',docked?'complementary':'dialog');
  if(docked)meetingSide.removeAttribute('aria-modal');else meetingSide.setAttribute('aria-modal','true');
  if(meetingSidePin){
    meetingSidePin.setAttribute('aria-pressed',String(meetingSidePinned));
    meetingSidePin.textContent=meetingSidePinned?'取消固定':'固定';
  }
}
wideMeetingSide?.addEventListener?.('change',syncMeetingSideLayout);
if(meetingSidePin)meetingSidePin.onclick=()=>{meetingSidePinned=!meetingSidePinned;syncMeetingSideLayout()};
function setMeetingSide(open){
  const wasOpen=meetingSide.classList.contains('on');
  if(open)document.body.classList.remove('nav-open');
  meetingSide.classList.toggle('on',open);syncMeetingSideLayout();
  meetingSide.inert=!open;meetingToolsButton.setAttribute('aria-expanded',String(open));
  if(open){drawMeetingDetails();document.getElementById('sideX').focus();}
  else if(wasOpen)meetingToolsButton.focus();
}
meetingToolsButton.onclick=()=>setMeetingSide(!meetingSide.classList.contains('on'));
document.getElementById('sideX').onclick=()=>setMeetingSide(false);
meetingSideBg.onclick=()=>setMeetingSide(false);
meetingSide.querySelectorAll('.card').forEach(card=>{
  const heading=card.querySelector('h4'),button=document.createElement('button');
  const label=heading.querySelector('.ct').textContent;
  button.type='button';button.className='card-fold';button.textContent='⌄';button.setAttribute('aria-label','收起'+label);button.setAttribute('aria-expanded','true');
  button.onclick=()=>{const closed=card.classList.toggle('shut');button.setAttribute('aria-expanded',String(!closed));button.setAttribute('aria-label',(closed?'展开':'收起')+label)};
  heading.appendChild(button);
});
meetingSide.addEventListener('click',e=>{const button=e.target.closest('[data-detail-agent]');if(button){const id=button.dataset.detailAgent;setMeetingSide(false);openAi(id)}});
document.addEventListener('keydown',e=>{
  if(document.body.classList.contains('meeting-side-docked'))return;
  if(e.key==='Escape'){
    if(meetingSide.classList.contains('on')){e.preventDefault();setMeetingSide(false)}
  }
  if(e.key==='Tab'&&meetingSide.classList.contains('on')&&!modal.classList.contains('show')){
    const buttons=[...meetingSide.querySelectorAll('button,input,textarea,select,a[href]')].filter(el=>!el.disabled&&el.getClientRects().length);
    const first=buttons[0],last=buttons[buttons.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
  }
});
function fmtK(n){return n>=1e6?(n/1e6).toFixed(n%1e6?1:0)+'M':Math.round(n/1000)+'k'}
function ctxTitle(x){
  const c=x&&x.ctx;if(!c||!c.used)return '上下文：还没数据（回过一轮话后显示）';
  return '上下文：'+fmtK(c.used)+(c.window?' / '+fmtK(c.window):'')+' tokens（'+c.time+' 那轮结束时）';
}
// ===== 参会者（不止 claude / codex）：颜色、首字母、胶囊 =====
function agentMeta(id){return ((S&&S.agents)||CONTACTS||[]).find(a=>a.id===id)||null}
function isAgent(id){return !!(id&&id!=='你'&&id!=='系统')}
function agentColor(id){const a=agentMeta(id);return (a&&a.color)||'#888'}
function agentLetter(id){const a=agentMeta(id);return (a&&a.letter)||(id||'?').slice(0,1).toUpperCase()}

const quickEl=document.getElementById('quick');
function drawQuick(){          // 输入框上面那排 @：跟着这场会议的参会者走
  if(!quickEl)return;
  const ids=(S&&S.participants)||[];
  const key=ids.join(',');
  if(quickEl.dataset.k===key)return;
  quickEl.dataset.k=key;
  quickEl.innerHTML=ids.map(id=>{const contact=CONTACTS.find(a=>a.id===id),label=contact&&contact.label||id;return '<button type="button" data-ins="@'+esc(id)+' " title="@'+esc(id)+'">@'+esc(label)+'</button>'}).join('')
    +'<button type="button" data-ins="@用户 ">@用户</button>';
  quickEl.querySelectorAll('button').forEach(b=>b.onclick=()=>{
    const t=document.getElementById('ta');if(!t)return;t.value+=b.dataset.ins;t.dispatchEvent(new Event('input',{bubbles:true}));t.focus();
  });
}
const AG_DRV={cli:'命令行程序',acp:'ACP 常驻协议',http:'网页服务',external:'在它自己的界面里',claude:'Claude Code 命令行',codex:'Codex 常驻服务'};
let agCat=null;
function drawState(){
  drawRoomIdentity();
  const has=S&&S.meeting;
  document.getElementById('bAgents').disabled=!has;document.getElementById('ta').disabled=!has;document.getElementById('send').disabled=!has;
  const wd=has?(S.workdir||''):'',other=has&&wd&&wd!==S.default_workdir;
  const wdName=wd.replace(/[\\/]+$/,'').split(/[\\/]/).pop();
  titleEl.innerHTML=has?esc(S.title)+(other?' <span class="wdn">· '+esc(wdName)+'</span>':''):'（还没有会议）';
  titleEl.title=wd;
  document.getElementById('wd').textContent=has?'📁 '+wd:'';
  drawRooms();
  drawQuick();
  const cx=S&&S.ais&&S.ais.claude;   // 落盘是 claude 的活：它不在会里就不能按
  document.getElementById('bWrap').disabled=!has||!cx||cx.handed_off||cx.busy;
  const work=!!(has&&S.mode==='work');
  document.body.classList.toggle('work',work);
  document.getElementById('bRename').disabled=!has;
  drawDebate();
  syncUndo();
  loadAnn();
  drawBoard();
  drawStops();
  drawClaims();
  drawMeetingDetails();
  if(typeof syncHarnessUi==='function')syncHarnessUi();
}
function drawMeetingDetails(){
  const state=S||{},ais=Object.entries(state.ais||{}),empty=text=>'<p class="hint">'+esc(text)+'</p>';
  const label=id=>(agentMeta(id)||{}).label||id;
  const put=(id,html)=>{const el=document.getElementById(id);if(el&&el.innerHTML!==html)el.innerHTML=html};
  const git=state.git;
  put('envBox',state.workdir?'<p class="detail-path">'+esc(state.workdir)+'</p><p class="hint">'+(git?'分支 '+esc(git.branch)+' · '+esc(git.changed)+' 处未提交改动'+(git.track?' · '+esc(git.track):''):'此工作目录未提供 Git 状态')+'</p>':empty('尚未选择会议工作目录。'));
  put('ctxBox',ais.map(([id,x])=>'<div class="detail-agent"><b>'+esc(label(id))+'</b><p class="hint">'+esc(ctxTitle(x))+'</p><button data-detail-agent="'+esc(id)+'">模型与执行端</button></div>').join('')||empty('邀请 Agent 后可查看其上下文状态。'));
  const steps=(state.steps||[]).filter(step=>!step.undone&&step.files&&step.files.length);
  const files=steps.slice(-8).reverse().map(step=>'<div class="detail-agent"><b>'+esc(label(step.ai))+' · 第 '+esc(step.seq)+' 步</b>'+step.files.map(file=>'<p class="detail-path">'+esc(file.st)+' · '+esc(file.path)+'</p>').join('')+'</div>').join('');
  put('outBox',files||empty('暂无已记录的文件改动；共享附件请在消息中查看。'));
  document.getElementById('outN').textContent=steps.length?steps.length+' 步':'';
  document.getElementById('claimN').textContent=(state.claims||[]).length||'';
  if(typeof drawSideAgentsPane==='function')drawSideAgentsPane();
}
function openRename(rid,title,after=loadState){
  setMeetingSide(false);
  const canBack=typeof hasModalBack==='function'&&hasModalBack();
  const finish=()=>{if(canBack)popModalBack();else hideModal();};
  showModal((canBack?'<div class="connection-heading"><button type="button" class="modal-back" id="renameBack">← 返回</button><h3>修改会话名称</h3><button type="button" id="renameClose" aria-label="关闭">×</button></div>':'<h3>修改会话名称</h3>')+'<form id="renameForm"><label>会话名称<input id="renameTitle" maxlength="60" required></label><p class="form-error" role="alert"></p><div class="btns"><button type="button" id="renameCancel">取消</button><button class="pri" type="submit">保存</button></div></form>');
  const form=document.getElementById('renameForm'),input=document.getElementById('renameTitle'),submit=form.querySelector('[type=submit]');
  input.value=title;input.focus();input.select();
  if(canBack&&document.getElementById('renameBack'))document.getElementById('renameBack').onclick=()=>popModalBack();
  if(document.getElementById('renameClose'))document.getElementById('renameClose').onclick=hideModal;
  document.getElementById('renameCancel').onclick=finish;
  form.onsubmit=async e=>{
    e.preventDefault();if(submit.disabled)return;submit.disabled=true;
    const [ok,j]=await post('/api/r/'+encodeURIComponent(rid)+'/rename',{title:input.value});
    submit.disabled=false;
    if(!ok){form.querySelector('.form-error').textContent=j.error||'保存失败';return}
    if(document.getElementById('renameForm')!==form)return pollRooms();
    if(rid===RID)await loadState();await pollRooms();
    if(canBack)popModalBack();
    else{hideModal();if(after!==loadState)await after();}
  };
}
document.getElementById('bRename').onclick=()=>{if(S&&S.meeting===RID)openRename(RID,S.title)};

const debateBtn=document.getElementById('debateBtn');
function canContinueDebate(){
  return !!(S&&S.meeting===RID&&!S.archived&&['completed','cancelled','failed','interrupted'].includes(S.debate?.status));
}
function drawDebate(){
  const d=S&&S.debate,active=d&&['running','summarizing'].includes(d.status);
  debateBtn.disabled=!(S&&S.meeting)||!!(active&&(d.finish_requested||d.status==='summarizing'));
  debateBtn.textContent=!active?'论道':d.status==='summarizing'?'正在总结':d.finish_requested?'等待总结':'结束并总结';
  debateBtn.title=active?d.topic+' · 已完成 '+d.completed_rounds+' 轮':'设定议题，让 Agent 独立表态、交叉反驳并总结';
  debateBtn.classList.toggle('is-debating',!!active);
  let button=document.getElementById('debateContinueBtn');
  let message;
  if(canContinueDebate()){
    message=Object.values(msgById).filter(m=>m&&!m.recalled).sort((a,b)=>Number(b.id)-Number(a.id)).find(m=>m.origin==='debate-summary'||m.origin==='debate'||
      (m.speaker==='系统'&&/^(开始论道：|继续论道：|论道未完成。)/.test(m.text||'')));
  }
  const anchor=message&&feed.querySelector('.msg[data-id="'+message.id+'"]');
  if(!anchor){button?.remove();return}
  if(!button){
    button=document.createElement('button');button.type='button';button.id='debateContinueBtn';
    button.className='composer-chip';button.textContent='继续论道';button.onclick=openDebateContinue;
  }
  button.title='对「'+d.topic+'」补充反馈或新回答后继续论道';
  if(button.parentElement!==anchor)anchor.appendChild(button);
}
debateBtn.onclick=async()=>{
  const rid=RID;if(!S||S.meeting!==rid)return;
  const d=S.debate;
  if(d&&d.status==='running'){
    debateBtn.disabled=true;
    const [ok,j]=await post(api('debate/finish'),{});
    if(rid!==RID)return;
    if(!ok){alert(j.error||'操作失败');drawDebate();return}
    S.debate=j.debate;drawDebate();poll();return;
  }
  const ids=(S.participants||[]).filter(id=>(agentMeta(id)||{}).kind!=='user'&&S.permissions?.[id]?.read&&S.permissions?.[id]?.post&&!S.ais?.[id]?.handed_off);
  const label=id=>(agentMeta(id)||{}).label||id;
  if(!ids.length)return alert('请先邀请能读消息和发言的 Agent。');
  showModal('<h3>开始论道</h3><form id="debateForm"><label>议题<textarea name="topic" required placeholder="要讨论什么？"></textarea></label><div class="debate-rounds"><label>最少轮数<input name="minimum" type="number" min="0" step="1" value="0" required></label><label>最多轮数<input name="maximum" type="number" min="0" step="1" value="3" placeholder="留空不限"></label></div><p class="hint">第 1 轮各参辩 Agent 并行独立表态（互不可见，避免先入为主）；第 2 轮起互相可见并交叉反驳。无异议的 Agent 可跳过发言（仍计轮数）。最多填 0 时直接总结，留空则不限轮数。</p><fieldset class="debate-agents"><legend>参辩成员</legend>'+ids.map(id=>'<label class="contact-pick"><input type="checkbox" name="participant" value="'+esc(id)+'" checked>'+esc(label(id))+'</label>').join('')+'</fieldset><label>总结由谁负责<select name="moderator" required></select></label><p class="form-error" role="alert"></p><div class="btns"><button type="button" id="debateCancel">取消</button><button class="pri" type="submit">开始论道</button></div></form>');
  const form=document.getElementById('debateForm'),moderator=form.elements.namedItem('moderator'),submit=form.querySelector('[type=submit]');
  const selected=()=>[...form.querySelectorAll('input[name=participant]:checked')].map(i=>i.value);
  const sync=()=>{
    const prev=moderator.value,participants=selected();
    moderator.innerHTML=participants.map(id=>'<option value="'+esc(id)+'">'+esc(label(id))+'</option>').join('');
    if(participants.includes(prev))moderator.value=prev;
  };
  form.onchange=sync;sync();
  document.getElementById('debateCancel').onclick=hideModal;
  form.elements.namedItem('topic').focus();
  form.onsubmit=async e=>{
    e.preventDefault();if(rid!==RID||submit.disabled)return;
    const f=new FormData(form),max=f.get('maximum');submit.disabled=true;
    const [ok,j]=await post(api('debate/start'),{topic:f.get('topic'),participants:selected(),min_rounds:Number(f.get('minimum')),max_rounds:max===''?null:Number(max),moderator:moderator.value});
    submit.disabled=false;
    if(!ok){form.querySelector('.form-error').textContent=j.error||'启动失败';return}
    if(document.getElementById('debateForm')===form)hideModal();
    if(rid===RID){S.debate=j.debate;drawDebate();poll()}
  };
};
function openDebateContinue(){
  const rid=RID;if(!canContinueDebate())return;
  const d=S.debate;
  const ids=(S.participants||[]).filter(id=>(agentMeta(id)||{}).kind!=='user'&&S.permissions?.[id]?.read&&S.permissions?.[id]?.post&&!S.ais?.[id]?.handed_off);
  const label=id=>(agentMeta(id)||{}).label||id;
  if(!ids.length)return alert('请先邀请能读消息和发言的 Agent。');
  const prevSet=new Set((d.participants||[]).filter(id=>ids.includes(id)));
  const checked=id=>prevSet.size?prevSet.has(id):true;
  showModal('<h3>继续论道</h3><p class="hint">原议题：'+esc(d.topic)+'（已辩 '+esc(d.completed_rounds)+' 轮）</p><form id="debateContinueForm"><label>你的反馈或新回答<textarea name="feedback" required placeholder="对刚才的结论哪里不满意？写下你的新回答、补充条件或追问方向…"></textarea></label><div class="debate-rounds"><label>再辩最少轮数<input name="minimum" type="number" min="0" step="1" value="1" required></label><label>再辩最多轮数<input name="maximum" type="number" min="0" step="1" value="3" placeholder="留空不限"></label></div><p class="hint">再辩首轮各 Agent 会结合你的反馈独立表态，之后再交叉反驳；无异议可跳过发言（仍计轮数）。</p><fieldset class="debate-agents"><legend>参辩成员</legend>'+ids.map(id=>'<label class="contact-pick"><input type="checkbox" name="participant" value="'+esc(id)+'"'+(checked(id)?' checked':'')+'>'+esc(label(id))+'</label>').join('')+'</fieldset><label>总结由谁负责<select name="moderator" required></select></label><p class="form-error" role="alert"></p><div class="btns"><button type="button" id="debateContinueCancel">取消</button><button class="pri" type="submit">继续论道</button></div></form>');
  const form=document.getElementById('debateContinueForm'),moderator=form.elements.namedItem('moderator'),submit=form.querySelector('[type=submit]');
  const selected=()=>[...form.querySelectorAll('input[name=participant]:checked')].map(i=>i.value);
  const sync=(prefer='')=>{
    const prev=prefer||moderator.value,participants=selected();
    moderator.innerHTML=participants.map(id=>'<option value="'+esc(id)+'">'+esc(label(id))+'</option>').join('');
    if(participants.includes(prev))moderator.value=prev;
  };
  form.onchange=()=>sync();sync(d.moderator||'');
  document.getElementById('debateContinueCancel').onclick=hideModal;
  form.elements.namedItem('feedback').focus();
  form.onsubmit=async e=>{
    e.preventDefault();if(rid!==RID||submit.disabled)return;
    const f=new FormData(form),max=f.get('maximum');submit.disabled=true;
    const [ok,j]=await post(api('debate/continue'),{feedback:f.get('feedback'),participants:selected(),min_rounds:Number(f.get('minimum')),max_rounds:max===''?null:Number(max),moderator:moderator.value});
    submit.disabled=false;
    if(!ok){form.querySelector('.form-error').textContent=j.error||'继续论道失败';return}
    if(document.getElementById('debateContinueForm')===form)hideModal();
    if(rid===RID){S.debate=j.debate;drawDebate();poll()}
  };
};
function syncUndo(){
  const done=new Set((S&&S.steps_undone)||[]);
  document.querySelectorAll('.undo').forEach(b=>{const u=done.has(+b.dataset.step);b.disabled=u;b.textContent=u?'已撤回':'撤回这一步'});
}
async function undoStep(n){
  const [pok,pj]=await post(api('undo/preview'),{step:n});
  if(!pok){alert(pj.error||'失败');await loadState();poll();return}
  const pl=pj.plan||{items:[],outside:[]};
  const lst=pl.items.map(i=>{const a=i.act==='删除'?'删除（这步新增的）':i.act==='还原'?'还原成改前':'撤不回，不动';return a+'  '+i.path}).join('\n');
  if(!confirm('撤回 '+pl.ai+' 的这一步？只动它自己记录里的这些文件：\n\n'+lst+(pl.outside.length?'\n\n项目外的文件撤不回：\n'+pl.outside.join('\n'):'')))return;
  const [ok,j]=await post(api('undo'),{step:n});
  if(!ok)alert(j.error||'失败');
  await loadState();poll();
}
async function toggleMode(){
  const to=(S&&S.mode==='work')?'discuss':'work';
  if(to==='work'&&!confirm('切到干活模式？\n\nclaude 和 codex 拿到完整权限，跟你平时在桌面版里用一样：改文件、跑命令、联网、用 git。只有 MCP 工具不加载（为了回得快）。\n它们用编辑工具改的文件每一步都记下来，可以一键撤回；用命令写的文件、删掉的文件、git 操作撤不回。'))return;
  const [ok,j]=await post(api('mode'),{mode:to});
  if(!ok)alert(j.error||'失败');
  await loadState();poll();
}
function openMoveRoom(room,projects){
  const destinations=projects.filter(p=>p.id!==room.project);
  const goBack=()=>typeof hasModalBack==='function'&&hasModalBack()?popModalBack():openList();
  showModal('<div class="connection-heading"><button type="button" class="modal-back" id="moveTopBack">← 返回</button><h3>移动会话</h3><button type="button" id="moveClose" aria-label="关闭">×</button></div><p class="hint">「'+esc(room.title)+'」的聊天记录、附件和工作目录会保留。</p><label>目标项目<select id="moveProject">'+destinations.map(p=>'<option value="'+esc(p.id)+'">'+esc(p.name)+'</option>').join('')+'</select></label><p id="moveError" role="alert"></p><div class="btns"><button type="button" id="moveBack">返回</button><button type="button" id="moveSave" class="pri">移动会话</button></div>');
  document.getElementById('moveClose').onclick=hideModal;
  document.getElementById('moveTopBack').onclick=goBack;
  document.getElementById('moveBack').onclick=goBack;
  document.getElementById('moveSave').onclick=async e=>{
    const button=e.currentTarget,project=document.getElementById('moveProject').value;
    button.disabled=true;
    const [ok,result]=await post('/api/rooms/move',{id:room.id,project});
    if(ok)await pollRooms();
    if(document.getElementById('moveSave')!==button)return;
    if(ok)return goBack();
    button.disabled=false;
    document.getElementById('moveError').textContent=result.error||'移动失败';
  };
}
async function openList(showTrash){
  const j=await (await fetch('/api/rooms',{cache:'no-store'})).json();
  const tj=await (await fetch('/api/trash',{cache:'no-store'})).json();
  const projects=j.projects||[],projectNames=new Map(projects.map(p=>[p.id,p.name]));
  const projectStats=new Map(projects.map(p=>{
    const owned=j.rooms.filter(room=>room.project===p.id);
    const busy=owned.filter(room=>(room.running||[]).length||room.queued).length;
    const inTrash=tj.trash.filter(room=>room.project===p.id).length;
    return [p.id,{count:owned.length,busy,inTrash}];
  }));
  const projectRows=projects.map(p=>{
    const st=projectStats.get(p.id)||{count:0,busy:0,inTrash:0};
    const isRemote=typeof agCat!=='undefined'&&agCat&&agCat.local_workspace===false;
    const folders=(p.workdirs||[p.workdir]).filter(Boolean);
    return '<div class="item project-item"><span class="tt">'+esc(p.name)+' <small>'+st.count+' 场会话'+(folders.length>1?' · '+folders.length+' 个目录':'')+(st.inTrash?' · 回收站 '+st.inTrash+' 场':'')+'</small></span><span class="acts">'+(isRemote?'':'<button type="button" data-project-edit="'+esc(p.id)+'">设置</button>')+'<button type="button" data-project-delete="'+esc(p.id)+'"'+(st.busy?' disabled':'')+'>删除项目</button></span></div>';
  }).join('');
  const rows=j.rooms.map(m=>{const cur=m.id===RID,b=roomBadge(m),projectName=projectNames.get(m.project);return '<div class="item'+(m.archived?' arch':'')+'" data-id="'+esc(m.id)+'"><span class="tt">'+(b?'<span class="rl"><span class="b '+b[0]+'">'+esc(b[1])+'</span></span> ':'')+esc(m.title)+(projectName?' <small>· '+esc(projectName)+'</small>':'')+(cur?' <small>（这个标签页）</small>':'')+(m.archived?' <small>（已归档）</small>':'')+'</span><span class="acts"><small>'+esc(m.created.slice(5,16))+'</small>'+
    '<button type="button" class="rn">改名</button><button type="button" class="mv"'+(projects.length<2?' disabled':'')+'>移动到项目</button><button type="button" class="ab" data-on="'+(m.archived?0:1)+'">'+(m.archived?'取消归档':'归档')+'</button><button type="button" class="db"'+((m.running||[]).length||m.queued?' disabled':'')+'>删除</button></span></div>'}).join('');
  const trows=tj.trash.map(m=>'<div class="item" data-id="'+esc(m.id)+'" data-title="'+esc(m.title)+'"><span class="tt">'+esc(m.title)+'</span><span class="acts"><button type="button" class="rb">恢复</button><button type="button" class="pb">彻底删除</button></span></div>').join('');
  const canBack=typeof hasModalBack==='function'&&hasModalBack();
  const isTrashOpen=()=>document.getElementById('trashBox')?.style.display==='block';
  const pushListBack=()=>{if(typeof pushModalBack==='function'){const trash=isTrashOpen();pushModalBack(()=>openList(trash));}};
  showModal((canBack?'<div class="connection-heading"><button type="button" class="modal-back" id="lBack">← 返回</button><h3>项目与会话管理</h3><button type="button" id="lHeaderClose" aria-label="关闭">×</button></div>':'<h3>项目与会话管理</h3>')+'<h4>项目</h4>'+(projectRows||'<p class="hint">还没有项目</p>')+
    (projectRows?'<p class="hint">删除项目会将该项目下的会话（含已归档）移入回收站，磁盘上的工作文件夹会保留。</p>':'')+
    '<h4>会话</h4>'+(rows||'<div class="hint">还没有会议</div>')+
    '<div class="btns" style="margin-top:10px"><button type="button" id="lTrash">回收站（'+tj.trash.length+'）</button><button type="button" id="lClose">关闭</button></div>'+
    '<div id="trashBox" style="display:'+(showTrash?'block':'none')+'"><h3 style="margin-top:14px">回收站</h3>'+(trows||'<div class="hint">空的</div>')+
    (tj.trash.length?'<div class="btns" style="margin-top:8px"><button type="button" id="lPurge">清空回收站</button></div>':'')+
    '<div class="hint">彻底删除会尝试清理各 Agent 的对应会话，仍被其他会议使用的会话会保留。</div></div>'+
    '<div class="hint" style="margin-top:12px">几场会议可以同时跑。想并排看：在会议上按 Ctrl 点（或鼠标中键）在新标签页打开。</div>');
  if(canBack&&document.getElementById('lBack'))document.getElementById('lBack').onclick=()=>popModalBack();
  if(document.getElementById('lHeaderClose'))document.getElementById('lHeaderClose').onclick=hideModal;
  document.getElementById('lClose').onclick=hideModal;
  document.getElementById('lTrash').onclick=()=>{const b=document.getElementById('trashBox');b.style.display=b.style.display==='none'?'block':'none'};
  const act=async(url,body)=>{const [ok,jj]=await post(url,body);if(!ok){alert(jj.error||'失败');return false}return true};
  mbox.querySelectorAll('[data-project-edit]').forEach(button=>{
    button.onclick=()=>{
      const project=projects.find(p=>p.id===button.dataset.projectEdit);
      if(project&&typeof openProject==='function'){pushListBack();openProject(project);}
    };
  });
  mbox.querySelectorAll('[data-project-delete]').forEach(button=>{
    button.onclick=async()=>{
      const id=button.dataset.projectDelete,st=projectStats.get(id)||{count:0,busy:0,inTrash:0};
      const name=projectNames.get(id)||id;
      const msg=st.count?'删除项目「'+name+'」？项目下的 '+st.count+' 场会话（含已归档）会移入回收站，磁盘上的工作文件夹会保留。':'删除项目「'+name+'」？磁盘上的工作文件夹会保留。';
      if(!confirm(msg))return;
      button.disabled=true;
      const [ok,res]=await post('/api/projects/delete',{id});
      if(!ok){alert((res&&res.error)||'失败');button.disabled=false;return}
      const trashed=new Set((res&&res.trashed_rooms)||[]);
      if(RID&&trashed.has(RID)){
        hideModal();roomViewGeneration++;RID=null;resetRoomView();
        const params=new URLSearchParams(location.search);params.delete('r');
        history.replaceState({},'',location.pathname+(params.size?'?'+params.toString():''));
        await pickRoom();
        return;
      }
      await pollRooms();if(button.isConnected)openList(showTrash);
    };
  });
  async function purge(button,id,title){
    if(!confirm(id?'彻底删除「'+title+'」及对应的 Agent 会话？':'彻底删除回收站里的所有会话及对应的 Agent 会话？'))return;
    const owner=document.getElementById('trashBox');owner.querySelectorAll('button').forEach(b=>b.disabled=true);
    button.textContent='正在清理…';
    const [ok,result]=await post('/api/trash/purge',id?{id}:{});
    pollRooms();
    if(document.getElementById('trashBox')!==owner)return;
    const rows=(result.cleanup||[]).map(x=>'<li><b>'+esc(x.room)+' · '+esc(x.ai)+'</b><p>'+esc(x.message)+'</p><code>'+esc(x.session)+'</code></li>').join('');
    showModal('<div class="connection-heading"><button type="button" class="modal-back" id="cleanupBack">← 返回</button><h3>回收站清理结果</h3><button type="button" id="cleanupClose" aria-label="关闭">×</button></div>'+(ok?'':'<p role="alert">'+esc(result.error||'清理失败')+'</p>')+(rows?'<ul class="cleanup-results">'+rows+'</ul>':'<p class="hint">没有需要报告的 Agent 会话。</p>')+'<div class="btns"><button class="pri" type="button" id="cleanupDone">返回回收站</button></div>');
    document.getElementById('cleanupClose').onclick=hideModal;
    document.getElementById('cleanupBack').onclick=()=>openList(true);
    document.getElementById('cleanupDone').onclick=()=>openList(true);
  }
  mbox.querySelectorAll('#trashBox .item').forEach(el=>{
    el.querySelector('.rb').onclick=async e=>{e.stopPropagation();if(await act('/api/trash/restore',{id:el.dataset.id})){pollRooms();openList(true)}};
    el.querySelector('.pb').onclick=e=>purge(e.currentTarget,el.dataset.id,el.dataset.title);
  });
  const pg=document.getElementById('lPurge');
  if(pg)pg.onclick=()=>purge(pg);
  mbox.querySelectorAll('.item[data-id]').forEach(el=>{
    if(el.closest('#trashBox'))return;
    const room=j.rooms.find(room=>room.id===el.dataset.id);
    el.querySelector('.rn').onclick=e=>{e.stopPropagation();pushListBack();openRename(room.id,room.title,openList)};
    el.querySelector('.mv').onclick=e=>{e.stopPropagation();pushListBack();openMoveRoom(room,projects)};
    el.querySelector('.ab').onclick=async e=>{e.stopPropagation();if(await act('/api/rooms/archive',{id:el.dataset.id,on:el.querySelector('.ab').dataset.on==='1'})){await loadState();pollRooms();openList()}};
    el.querySelector('.db').onclick=async e=>{e.stopPropagation();
      if(!confirm('把「'+el.querySelector('.tt').textContent+'」移到回收站？（可以恢复）'))return;
      if(await act('/api/rooms/delete',{id:el.dataset.id})){
        if(el.dataset.id===RID){hideModal();roomViewGeneration++;RID=null;resetRoomView();const params=new URLSearchParams(location.search);params.delete('r');history.replaceState({},'',location.pathname+(params.size?'?'+params.toString():''));await pickRoom()}
        else {await pollRooms();openList(true)}
      }};
    el.onclick=()=>{hideModal();setMeetingSide(false);switchRoom(el.dataset.id)};
  });
}
function openAi(a){
  const x=S&&S.ais&&S.ais[a];if(!x)return;
  const canBack=typeof hasModalBack==='function'&&hasModalBack();
  const title=esc((CONTACTS.find(c=>c.id===a)||{}).label||a);
  let h=canBack?'<div class="connection-heading"><button type="button" class="modal-back" id="aBack">← 返回</button><h3>'+title+'</h3><button type="button" id="aHeaderClose" aria-label="关闭">×</button></div>':'<h3>'+title+'</h3>';
  const mo=x.model||{models:[],efforts:[],model:'',effort:''};
  const aiBusy=!!(x.busy||(S&&((S.running||[]).includes(a)||(S.running||[]).includes('compact:'+a))));
  h+=modelSettingsMarkup(mo,aiBusy);
  h+=executionSettingsMarkup(a,(S.execution||{})[a],aiBusy);
  const spec=agentMeta(a)||{};
  const hasTerminal=['claude','codex'].includes(spec.driver)||x.handoff;
  if(hasTerminal){
    h+='<h3 style="margin-top:14px">会话与终端</h3>';
    if(!x.session)h+='<div class="hint">还没叫过它，先在会议里 @ 它一次。</div>';
    else h+='<div class="hint">'+(x.handed_off?'现在在终端里，网页里不会叫它。':'在会议里。')+'</div><code>'+esc(x.cmd||'')+'</code>';
    h+='<div class="btns"><button type="button" id="aClose">关闭</button>';
    if(x.session)h+='<button type="button" id="aCopy">复制命令</button>';
    h+='<button type="button" class="pri" id="aToggle"'+((!x.session||(!x.handed_off&&x.busy)||(!x.handoff&&!x.handed_off))?' disabled':'')+'>'+(x.handed_off?'收回':'交给终端')+'</button></div>';
    if(x.session&&!x.handed_off&&x.busy)h+='<div class="hint">它正在跑或排着队，说完才能交。</div>';
  }
  if(x.session)h+='<div class="btns"><button type="button" id="aReset"'+((aiBusy||x.handed_off)?' disabled':'')+'>重开 Agent 会话</button></div>';
  if(!hasTerminal)h+='<div class="btns" style="margin-top:14px"><button type="button" id="aClose">关闭</button></div>';
  showModal(h);
  bindModelSettings(a,mo,aiBusy);
  bindExecutionSettings(a,(S.execution||{})[a],aiBusy);
  if(canBack&&document.getElementById('aBack'))document.getElementById('aBack').onclick=()=>popModalBack();
  if(document.getElementById('aHeaderClose'))document.getElementById('aHeaderClose').onclick=hideModal;
  document.getElementById('aClose').onclick=hideModal;
  const reset=document.getElementById('aReset');if(reset)reset.onclick=async()=>{
    if(!confirm('下次 @ '+a+' 时开启新会话？此会议的聊天记录仍会保留。'))return;
    const rid=RID;reset.disabled=true;
    const [ok,j]=await post(api('session/reset'),{ai:a});
    if(rid!==RID)return;
    if(!ok){alert(j.error||'重开失败');reset.disabled=false;return}
    await loadState();poll();if(document.getElementById('aReset')===reset)openAi(a);
  };
  const c=document.getElementById('aCopy');if(c)c.onclick=()=>{copyText(x.cmd);c.textContent='已复制'};
  const t=document.getElementById('aToggle');if(t)t.onclick=async()=>{
    const [ok,j]=await post(api('handoff'),{ai:a,on:!x.handed_off});
    if(!ok){alert(j.error||'失败');return}
    await loadState();poll();openAi(a);
  };
}
document.getElementById('bList').onclick=()=>{document.body.classList.remove('nav-open');openList()};
const stopsEl=document.getElementById('stops');
function drawStops(){
  // 压缩停不了（也不该停），只在它真在回话或排着回话时出"停"
  const busy=((S&&S.participants)||[]).filter(a=>{const x=S&&S.ais&&S.ais[a];return S&&((S.running||[]).includes(a)||(x&&x.busy&&!x.compacting))});
  const each=!!(S&&S.stop_each);   // 旧版后端不认按人停，只给全停
  const want=(each?busy.map(a=>'停 '+a):[]).concat(busy.length>1||(!each&&busy.length)?['全停']:[]).join('|');
  if(stopsEl.dataset.k===want)return;stopsEl.dataset.k=want;
  stopsEl.innerHTML='';
  if(each)busy.forEach(a=>{const b=document.createElement('button');b.type='button';b.textContent='停 '+a;b.title='只打断 '+a+'，另一个不受影响';b.onclick=()=>stopAi(a);stopsEl.appendChild(b)});
  if(busy.length>1||(!each&&busy.length)){const b=document.createElement('button');b.type='button';b.textContent=each?'全停':'停';b.onclick=()=>stopAi('');stopsEl.appendChild(b)}
}
async function stopAi(a){
  const who=a||'会里的 AI';
  if(!confirm('强行打断 '+who+'？\n\n正在跑的立刻停掉，连同它起的命令（比如 git push）；它排着的也清掉。\n已经改了的文件不会自动还原，干活模式下可以按步骤撤回。'))return;
  const [ok,j]=await post(api('stop'),a?{ai:a}:{});if(!ok)alert(j.error||'失败');poll();
}
document.getElementById('bWrap').onclick=async()=>{
  if(!confirm('落盘？\n\nclaude 会把这场会议定下的结论写进工作文件夹里的文档（文件夹里有 wrapup 技能就照它做），然后 git 提交并推送。\n这一轮它有完整权限，不管现在是讨论还是干活模式。'))return;
  const [ok,j]=await post(api('wrapup'));if(!ok)alert(j.error||'失败');setMeetingSide(false);poll();
};
document.getElementById('bAgents').onclick=()=>{setMeetingSide(false);openAgents()};
// ===== 正在改的文件（文件护栏）=====
const claimList=document.getElementById('claimList');
let claimSig='';
function drawClaims(){
  const cs=(S&&S.claims)||[];
  document.getElementById('claims').classList.toggle('on',true);
  const sig=JSON.stringify(cs);if(sig===claimSig)return;claimSig=sig;
  claimList.innerHTML=cs.length?cs.map(c=>{
    const nm=c.shown.replace(/[\\/]+$/,'').split(/[\\/]/).pop()||c.shown;
    const how=c.kind==='auto'?'这一轮在改':'占着'+(c.mins_left!=null?'，还剩约 '+c.mins_left+' 分钟':'')+(c.reason?'：'+c.reason:'');
    return '<li class="ai-'+esc(c.ai)+'"><span class="cf"><b>'+esc(nm)+(c.dir?'/':'')+'</b> · '+esc(c.who)+'<small>'+esc(how)+' · '+esc(c.shown)+'</small></span><button type="button" data-key="'+esc(c.key)+'" title="强行放开（AI 下次改它就不会被挡）">放开</button></li>';
  }).join(''):'<li style="color:var(--faint)">（没人占着文件。AI 改文件时会自动占住，说完就放开）</li>';
}
claimList.onclick=async e=>{
  const b=e.target.closest('button[data-key]');if(!b)return;
  if(!confirm('强行放开这个文件？\n\n占着它的 AI 可能还在改；放开后别的 AI 就能同时改它了。'))return;
  const [ok,j]=await post('/api/claims/release',{key:b.dataset.key});if(!ok)alert(j.error||'失败');await loadState();
};
document.getElementById('cMine').onclick=async()=>{
  const t=prompt('你自己在手动改哪些文件？占住后 AI 改它们会被挡下。\n填完整路径，几个用换行或分号隔开：');
  if(!t||!t.trim())return;
  const mins=prompt('占多久（分钟，最多 240）？','60');if(mins===null)return;
  const [ok,j]=await post('/api/claims/mine',{paths:t.split(/[;\n]+/).map(x=>x.trim()).filter(Boolean),minutes:+mins||60});
  if(!ok){alert(j.error||'失败');return}
  if(j.blocked&&j.blocked.length)alert('这些现在被 AI 占着，没占上：\n'+j.blocked.map(x=>x.path+'（'+x.by+'）').join('\n'));
  await loadState();
};

// ===== 工具：这场会议里 MCP / 插件 / 技能开哪些 =====
async function loadTools(a,x){
  const onSaved=arguments.length>2?arguments[2]:null;
  const box=document.getElementById('toolsBox');if(!box)return;
  const rid=RID,url=api('tools'),current=()=>RID===rid&&document.getElementById('toolsBox')===box;
  let t;
  try{const r=await fetch(url+'?ai='+a,{cache:'no-store'});t=await r.json();if(!r.ok)throw 0}catch(e){if(current())box.innerHTML='<div class="hint">读不到工具清单</div>';return}
  if(!current())return;
  const li=(id,on,name,sub,tags,locked)=>'<li class="'+(locked?'lk':'')+'"><input type="checkbox" data-id="'+esc(id)+'"'+(on?' checked':'')+(locked?' disabled':'')+'><span class="tn">'+esc(name)+(tags||[]).map(g=>'<span class="tg">'+esc(g)+'</span>').join('')+(sub?'<small>'+esc(sub)+'</small>':'')+'</span></li>';
  const empty='<li class="empty">（没有）</li>';
  const pName=id=>id.replace(/@.*$/,'');
  box.innerHTML=
    '<div class="hint">只管这场会议的 '+a+'。会议室自己的 bridge（看目标、占文件、中途发进度）一直接着。</div>'+
    '<h4>MCP 服务（只在干活模式加载）</h4><ul class="tl" id="tMcp">'+(t.mcp.map(m=>li(m.name,m.on,m.name,m.source)).join('')||empty)+'</ul>'+
    '<h4>插件</h4><ul class="tl" id="tPlug">'+(t.plugins.map(p=>li(p.id,p.on,p.label||pName(p.id),p.label?'':p.id,[p.hooks?'带钩子':'',p.synced?'claude.ai 同步':'',p.global?'':'平时关着'].filter(Boolean))).join('')||empty)+'</ul>'+
    '<h4>技能</h4><ul class="tl" id="tSkill">'+(t.skills.map(k=>li(k.name,k.on,k.name,(k.locked?'插件带的，跟着插件开关 · ':k.source+' · ')+(k.desc||''),[],k.locked)).join('')||empty)+'</ul>'+
    '<div class="btns"><button type="button" id="tSave"'+(x.busy?' disabled':'')+'>保存工具设置</button></div>'+
    '<div class="hint">'+(x.busy?'它正在跑或排着队，说完才能改。':'带钩子的插件（比如 superpowers 开场会往会话里塞一大段说明）、从 claude.ai 同步来的插件，会议室里默认关。改了下一轮生效'+(a==='codex'?'（codex 的后台会重起一次）':'')+'。')+'</div>';
  const defOn=p=>(p.hooks||p.synced)?false:p.global;
  document.getElementById('tSave').onclick=async()=>{
    if(!current())return;
    const val=sel=>[...box.querySelectorAll(sel+' input[data-id]')];
    const mcp=val('#tMcp').filter(i=>i.checked).map(i=>i.dataset.id);
    const plugins={};
    val('#tPlug').forEach(i=>{const p=t.plugins.find(q=>q.id===i.dataset.id);if(!p)return;if(i.checked!==defOn(p)||p.set)plugins[p.id]=i.checked});
    const skills_off=val('#tSkill').filter(i=>!i.disabled&&!i.checked).map(i=>i.dataset.id);
    const [ok,j]=await post(url,{ai:a,tools:{mcp,plugins,skills_off}});
    if(!current())return;
    if(!ok){alert(j.error||'失败');return}
    if(typeof window!=='undefined'&&(window.AnYHarness||window.CojamHarness)&&typeof (window.AnYHarness||window.CojamHarness).invalidateRoomTools==='function'){
      (window.AnYHarness||window.CojamHarness).invalidateRoomTools(rid,a);
    }
    await loadState();
    if(typeof onSaved==='function')await onSaved();
    else openAi(a);
  };
}
drawQuick();
