// 状态行：谁在想、想了多久，下面是它这一轮最近说的一句中途的话（不进会议记录，点一下展开）
let lastRun={running:[],queued:0};
const stLive=document.getElementById('stLive');
const openLive=new Set();
stLive.onclick=e=>{const l=e.target.closest('.ln');if(!l)return;const a=l.dataset.ai;openLive.has(a)?openLive.delete(a):openLive.add(a);l.classList.toggle('open')};
function fmtDur(s){return s<60?s+' 秒':s<3600?Math.floor(s/60)+' 分钟':Math.floor(s/3600)+' 小时 '+Math.floor(s%3600/60)+' 分'}
function drawStatus(){
  const lv=(S&&S.live)||{};
  const rn=lastRun.running.map(x=>x.startsWith('compact:')?x.slice(8)+' 正在压缩':x==='compact'?'正在压缩':x+' 正在想'+(lv[x]&&lv[x].secs>=60?'（'+fmtDur(lv[x].secs)+'）':''));
  const stT=document.getElementById('stText');
  if(rn.length){st.classList.add('on');stT.textContent=rn.join('，')+'…'+(lastRun.queued?' · 排队 '+lastRun.queued+' 条':'')}
  else if(lastRun.queued){st.classList.add('on');stT.textContent='队列还有 '+lastRun.queued+' 条'}
  else st.classList.remove('on');
  const h=Object.keys(lv).filter(a=>lv[a].text&&lastRun.running.includes(a)).map(a=>'<div class="ln '+esc(a)+(openLive.has(a)?' open':'')+'" data-ai="'+esc(a)+'" title="点一下展开 / 收起"><b>'+esc(a)+'</b><span class="t">'+esc(lv[a].time.slice(0,5))+'</span>'+esc(lv[a].text)+'</div>').join('');
  if(stLive.innerHTML!==h)stLive.innerHTML=h;
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
  // 公告在前，未完成待办其次，已完成垫底
  const rank=i=>i.kind==='note'?0:i.done?2:1;
  const sorted=items.slice().sort((a,b)=>rank(a)-rank(b)||a.id-b.id);
  boardList.innerHTML=sorted.length?sorted.map(i=>'<li class="'+(i.done?'done':'')+'" data-id="'+i.id+'">'+
    (i.kind==='todo'?'<input type="checkbox"'+(i.done?' checked':'')+'>':'<span class="pin">&#128204;</span>')+
    '<span class="bt">#'+i.id+' '+esc(i.text)+'<small>'+esc(i.by)+'</small></span><button type="button" class="bx" title="删掉">&times;</button></li>').join('')
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
const bar=document.getElementById('bar'),titleEl=document.getElementById('title');
const meetingToolsButton=document.getElementById('menu');
function closeMeetingTools(restoreFocus=false){
  bar.classList.remove('show');meetingToolsButton.setAttribute('aria-expanded','false');
  if(restoreFocus)meetingToolsButton.focus();
}
function placeMeetingTools(){
  const r=meetingToolsButton.getBoundingClientRect();
  bar.style.top=Math.min(r.bottom+8,innerHeight-80)+'px';
  bar.style.right=Math.max(12,innerWidth-r.right)+'px';
  bar.style.maxHeight=Math.max(60,innerHeight-r.bottom-24)+'px';
}
meetingToolsButton.onclick=()=>{
  if(bar.classList.contains('show'))return closeMeetingTools(true);
  document.body.classList.remove('nav-open');bar.classList.add('show');
  meetingToolsButton.setAttribute('aria-expanded','true');placeMeetingTools();
  const first=bar.querySelector('button:not(:disabled)');if(first)first.focus();
};
bar.addEventListener('click',e=>{if(e.target.closest('button')&&!e.target.closest('button').disabled)closeMeetingTools()});
document.addEventListener('pointerdown',e=>{if(!bar.contains(e.target)&&!meetingToolsButton.contains(e.target))closeMeetingTools()});
addEventListener('resize',()=>{if(bar.classList.contains('show'))placeMeetingTools()});
const meetingSide=document.getElementById('side'),meetingSideBg=document.getElementById('sideBg');
let sideReturnFocus=null;
function setMeetingSide(open){
  if(open){sideReturnFocus=document.activeElement;closeMeetingTools();document.body.classList.remove('nav-open')}
  meetingSide.classList.toggle('on',open);meetingSideBg.classList.toggle('on',open);
  meetingSide.inert=!open;document.getElementById('bSide').setAttribute('aria-expanded',String(open));
  if(open){drawMeetingDetails();document.getElementById('sideX').focus();}
  else if(sideReturnFocus){meetingToolsButton.focus();sideReturnFocus=null;}
}
document.getElementById('bSide').onclick=()=>setMeetingSide(true);
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
  if(e.key==='Escape'){
    if(meetingSide.classList.contains('on')){e.preventDefault();setMeetingSide(false)}
    else if(bar.classList.contains('show')){e.preventDefault();closeMeetingTools(true)}
  }
  if(e.key==='Tab'&&meetingSide.classList.contains('on')&&!modal.classList.contains('show')){
    const buttons=[...meetingSide.querySelectorAll('button,input,textarea,select,a[href]')].filter(el=>!el.disabled&&el.getClientRects().length);
    const first=buttons[0],last=buttons[buttons.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
  }
});
function fmtK(n){return n>=1e6?(n/1e6).toFixed(n%1e6?1:0)+'M':Math.round(n/1000)+'k'}
function ctxHtml(x){
  const c=x&&x.ctx;if(!c||!c.used)return '';
  if(!c.window)return '<span class="cx">上下文 '+fmtK(c.used)+'</span>';
  const p=Math.round(c.used*100/c.window);
  return '<span class="cx'+(p>=80?' hi':'')+'">上下文 '+p+'%</span>';
}
function ctxTitle(x){
  const c=x&&x.ctx;if(!c||!c.used)return '上下文：还没数据（回过一轮话后显示）';
  return '上下文：'+fmtK(c.used)+(c.window?' / '+fmtK(c.window):'')+' tokens（'+c.time+' 那轮结束时）';
}
// ===== 参会者（不止 claude / codex）：颜色、首字母、胶囊 =====
function agentMeta(id){return ((S&&S.agents)||CONTACTS||[]).find(a=>a.id===id)||null}
function isAgent(id){return !!(id&&id!=='你'&&id!=='系统')}
function agentColor(id){const a=agentMeta(id);return (a&&a.color)||'#888'}
function agentLetter(id){const a=agentMeta(id);return (a&&a.letter)||(id||'?').slice(0,1).toUpperCase()}

const capsEl=document.getElementById('caps');
function drawCaps(){
  const ids=(S&&S.participants)||[];
  const key=ids.map(id=>id+':'+((CONTACTS.find(a=>a.id===id)||{}).label||'')).join(',');
  if(capsEl.dataset.k!==key){          // 参会的人变了才重建按钮，平时只改里面
    capsEl.dataset.k=key;capsEl.innerHTML='';
    ids.forEach(a=>{
      const b=document.createElement('button');b.type='button';b.className='cap';b.dataset.ai=a;
      b.style.setProperty('--c',agentColor(a));b.onclick=()=>((agentMeta(a)||{}).kind==='user'?openAgents():openAi(a));capsEl.appendChild(b);
    });
  }
  ids.forEach(a=>{
    const b=capsEl.querySelector('.cap[data-ai="'+a+'"]');if(!b)return;
    const [t,c]=capText(a);if(b.innerHTML!==t)b.innerHTML=t;
    b.className=c;b.title=(agentMeta(a)||{}).kind==='user'?'点击管理成员与权限':'点击设置模型、上下文与压缩。'+ctxTitle(S&&S.ais&&S.ais[a]);
  });
}
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
    const t=document.getElementById('ta');if(!t)return;t.value+=b.dataset.ins;t.focus();
  });
}
const AG_DRV={cli:'命令行程序',acp:'ACP 常驻协议',http:'网页服务',external:'在它自己的界面里',claude:'Claude Code 命令行',codex:'Codex 常驻服务'};
let agCat=null;
function capText(a){
  // 三段：名字 / 模型（手机上隐藏）/ 状态；电脑边栏里模型和状态各占一行
  const x=S&&S.ais&&S.ais[a];
  const member=S&&S.members&&S.members[a],meta=agentMeta(a)||{};
  let s,cls='cap';
  if(x&&x.handed_off){s='在终端';cls+=' term'}
  else if(S&&(S.running||[]).includes(a)){s='在想';cls+=' think'}
  else if(S&&(S.running||[]).includes('compact:'+a)){s='压缩中';cls+=' think'}
  else if(x&&x.compacting){s='等着压缩'}
  else if(x&&x.busy){s='排队'}
  else{s=meta.kind==='user'?'用户':member&&member.transport==='member'?(member.automatic?'自动响应就绪':'等待连接'):'空闲';cls+=' off'}
  const h='<span class="cn">'+esc((agentMeta(a)||{}).label||a)+'</span><span class="cm">'+esc((x&&x.model&&x.model.label)||'默认 · 默认')+'</span><span class="cs">'+s+'</span>'+ctxHtml(x);
  return [h,cls];
}
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
  drawCaps();
  drawQuick();
  const cx=S&&S.ais&&S.ais.claude;   // 落盘是 claude 的活：它不在会里就不能按
  document.getElementById('bWrap').disabled=!has||!cx||cx.handed_off||cx.busy;
  const work=!!(has&&S.mode==='work');
  document.body.classList.toggle('work',work);
  const bm=document.getElementById('bMode');bm.disabled=!has;bm.textContent=work?'干活模式':'讨论模式';bm.classList.toggle('on',work);
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
  const put=(id,html)=>{const el=document.getElementById(id);if(el.innerHTML!==html)el.innerHTML=html};
  const git=state.git;
  put('envBox',state.workdir?'<p class="detail-path">'+esc(state.workdir)+'</p><p class="hint">'+(git?'分支 '+esc(git.branch)+' · '+esc(git.changed)+' 处未提交改动'+(git.track?' · '+esc(git.track):''):'此工作目录未提供 Git 状态')+'</p>':empty('尚未选择会议工作目录。'));
  put('ctxBox',ais.map(([id,x])=>'<div class="detail-agent"><b>'+esc(label(id))+'</b><p class="hint">'+esc(ctxTitle(x))+'</p><button data-detail-agent="'+esc(id)+'">模型、effort 与上下文</button></div>').join('')||empty('邀请 Agent 后可查看其上下文状态。'));
  put('toolBox',ais.map(([id,x])=>'<div class="detail-agent"><b>'+esc(label(id))+'</b><p class="hint">'+esc(x.tools||'暂未提供工具信息')+'</p><button data-detail-agent="'+esc(id)+'">查看 Agent 设置</button></div>').join('')||empty('当前会议还没有 Agent。'));
  const steps=(state.steps||[]).filter(step=>!step.undone&&step.files&&step.files.length);
  const files=steps.slice(-8).reverse().map(step=>'<div class="detail-agent"><b>'+esc(label(step.ai))+' · 第 '+esc(step.seq)+' 步</b>'+step.files.map(file=>'<p class="detail-path">'+esc(file.st)+' · '+esc(file.path)+'</p>').join('')+'</div>').join('');
  put('outBox',files||empty('暂无已记录的文件改动；共享附件请在消息中查看。'));
  document.getElementById('outN').textContent=steps.length?steps.length+' 步':'';
  document.getElementById('claimN').textContent=(state.claims||[]).length||'';
  if(typeof drawSideAgentsPane==='function')drawSideAgentsPane();
}
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
  closeMeetingTools();await loadState();poll();
}
function openMoveRoom(room,projects){
  const destinations=projects.filter(p=>p.id!==room.project);
  showModal('<h3>移动会话</h3><p class="hint">「'+esc(room.title)+'」的聊天记录、附件和工作目录会保留。</p><label>目标项目<select id="moveProject">'+destinations.map(p=>'<option value="'+esc(p.id)+'">'+esc(p.name)+'</option>').join('')+'</select></label><p id="moveError" role="alert"></p><div class="btns"><button type="button" id="moveBack">返回</button><button type="button" id="moveSave" class="pri">移动会话</button></div>');
  document.getElementById('moveBack').onclick=()=>openList();
  document.getElementById('moveSave').onclick=async e=>{
    const button=e.currentTarget,project=document.getElementById('moveProject').value;
    button.disabled=true;
    const [ok,result]=await post('/api/rooms/move',{id:room.id,project});
    if(ok)await pollRooms();
    if(document.getElementById('moveSave')!==button)return;
    if(ok)return openList();
    button.disabled=false;
    document.getElementById('moveError').textContent=result.error||'移动失败';
  };
}
async function openList(showTrash){
  const j=await (await fetch('/api/rooms',{cache:'no-store'})).json();
  const tj=await (await fetch('/api/trash',{cache:'no-store'})).json();
  const projects=j.projects||[],projectNames=new Map(projects.map(p=>[p.id,p.name]));
  const projectRows=projects.map(p=>{
    const count=j.rooms.filter(room=>room.project===p.id).length;
    const inTrash=tj.trash.filter(room=>room.project===p.id).length;
    return '<div class="item project-item"><span class="tt">'+esc(p.name)+' <small>'+count+' 场会话'+(inTrash?' · 回收站 '+inTrash+' 场':'')+'</small></span><span class="acts"><button type="button" data-project-delete="'+esc(p.id)+'"'+(count||inTrash?' disabled':'')+'>删除项目</button></span></div>';
  }).join('');
  const rows=j.rooms.map(m=>{const cur=m.id===RID,b=roomBadge(m),projectName=projectNames.get(m.project);return '<div class="item'+(m.archived?' arch':'')+'" data-id="'+esc(m.id)+'"><span class="tt">'+(b?'<span class="rl"><span class="b '+b[0]+'">'+esc(b[1])+'</span></span> ':'')+esc(m.title)+(projectName?' <small>· '+esc(projectName)+'</small>':'')+(cur?' <small>（这个标签页）</small>':'')+(m.archived?' <small>（已归档）</small>':'')+'</span><span class="acts"><small>'+esc(m.created.slice(5,16))+'</small>'+
    '<button type="button" class="mv"'+(projects.length<2?' disabled':'')+'>移动到项目</button><button type="button" class="ab" data-on="'+(m.archived?0:1)+'">'+(m.archived?'取消归档':'归档')+'</button><button type="button" class="db"'+((m.running||[]).length||m.queued?' disabled':'')+'>删除</button></span></div>'}).join('');
  const trows=tj.trash.map(m=>'<div class="item" data-id="'+esc(m.id)+'" data-title="'+esc(m.title)+'"><span class="tt">'+esc(m.title)+'</span><span class="acts"><button type="button" class="rb">恢复</button></span></div>').join('');
  showModal('<h3>项目与会话管理</h3><h4>项目</h4>'+(projectRows||'<p class="hint">还没有项目</p>')+
    (projectRows?'<p class="hint">移走会话并处理回收站中的会话后，即可删除空项目。磁盘上的工作文件夹会保留。</p>':'')+
    '<h4>会话</h4>'+(rows||'<div class="hint">还没有会议</div>')+
    '<div class="btns" style="margin-top:10px"><button type="button" id="lTrash">回收站（'+tj.trash.length+'）</button><button type="button" id="lClose">关闭</button></div>'+
    '<div id="trashBox" style="display:'+(showTrash?'block':'none')+'"><h3 style="margin-top:14px">回收站</h3>'+(trows||'<div class="hint">空的</div>')+
    (tj.trash.length?'<div class="btns" style="margin-top:8px"><button type="button" id="lPurge">清空回收站</button></div>':'')+
    '<div class="hint">彻底删除会尝试清理各 Agent 的对应会话，仍被其他会议使用的会话会保留。</div></div>'+
    '<div class="hint" style="margin-top:12px">几场会议可以同时跑。想并排看：在会议上按 Ctrl 点（或鼠标中键）在新标签页打开。</div>');
  document.getElementById('lClose').onclick=hideModal;
  document.getElementById('lTrash').onclick=()=>{const b=document.getElementById('trashBox');b.style.display=b.style.display==='none'?'block':'none'};
  const act=async(url,body)=>{const [ok,jj]=await post(url,body);if(!ok){alert(jj.error||'失败');return false}return true};
  mbox.querySelectorAll('[data-project-delete]').forEach(button=>{
    button.onclick=async()=>{
      const id=button.dataset.projectDelete;
      if(!confirm('删除空项目「'+projectNames.get(id)+'」？磁盘上的工作文件夹会保留。'))return;
      button.disabled=true;
      if(await act('/api/projects/delete',{id})){await pollRooms();if(button.isConnected)openList(showTrash)}
      else button.disabled=false;
    };
  });
  mbox.querySelectorAll('#trashBox .item').forEach(el=>{
    el.querySelector('.rb').onclick=async e=>{e.stopPropagation();if(await act('/api/trash/restore',{id:el.dataset.id})){pollRooms();openList(true)}};
  });
  const pg=document.getElementById('lPurge');
  if(pg)pg.onclick=async()=>{if(!confirm('清空回收站？清空后找不回来。\n\n这些会议里 claude、codex 各自的会话（~/.claude、~/.codex 下的记录）也一起删掉；别的会议还在用的不删。'))return;if(await act('/api/trash/purge',{}))openList(true)};
  mbox.querySelectorAll('.item[data-id]').forEach(el=>{
    if(el.closest('#trashBox'))return;
    const room=j.rooms.find(room=>room.id===el.dataset.id);
    el.querySelector('.mv').onclick=e=>{e.stopPropagation();openMoveRoom(room,projects)};
    el.querySelector('.ab').onclick=async e=>{e.stopPropagation();if(await act('/api/rooms/archive',{id:el.dataset.id,on:el.querySelector('.ab').dataset.on==='1'})){await loadState();pollRooms();openList()}};
    el.querySelector('.db').onclick=async e=>{e.stopPropagation();
      if(!confirm('把「'+el.querySelector('.tt').textContent+'」移到回收站？（可以恢复）'))return;
      if(await act('/api/rooms/delete',{id:el.dataset.id})){
        if(el.dataset.id===RID){hideModal();roomViewGeneration++;RID=null;resetRoomView();const params=new URLSearchParams(location.search);params.delete('r');history.replaceState({},'',location.pathname+(params.size?'?'+params.toString():''));await pickRoom()}
        else {await pollRooms();openList(true)}
      }};
    el.onclick=()=>{hideModal();closeMeetingTools();switchRoom(el.dataset.id)};
  });
}
function openAi(a){
  const x=S&&S.ais&&S.ais[a];if(!x)return;
  let h='<h3>'+esc((CONTACTS.find(c=>c.id===a)||{}).label||a)+'</h3>';
  const mo=x.model||{models:[],efforts:[],model:'',effort:''};
  const aiBusy=!!(x.busy||(S&&((S.running||[]).includes(a)||(S.running||[]).includes('compact:'+a))));
  h+=modelSettingsMarkup(mo,aiBusy);
  h+=executionSettingsMarkup(a,(S.execution||{})[a],aiBusy);
  const spec=agentMeta(a)||{};
  const hasTerminal=['claude','codex'].includes(spec.driver)||x.handoff;
  const hasTools=['claude','codex'].includes(spec.driver)||(x.caps&&x.caps.tools);
  if(hasTerminal){
    h+='<h3 style="margin-top:14px">会话与终端</h3>';
    if(!x.session)h+='<div class="hint">还没叫过它，先在会议里 @ 它一次。</div>';
    else h+='<div class="hint">'+(x.handed_off?'现在在终端里，网页里不会叫它。':'在会议里。')+'</div><code>'+esc(x.cmd||'')+'</code>';
    h+='<div class="btns"><button type="button" id="aClose">关闭</button>';
    if(x.session)h+='<button type="button" id="aCopy">复制命令</button>';
    h+='<button type="button" class="pri" id="aToggle"'+((!x.session||(!x.handed_off&&x.busy)||(!x.handoff&&!x.handed_off))?' disabled':'')+'>'+(x.handed_off?'收回':'交给终端')+'</button></div>';
    if(x.session&&!x.handed_off&&x.busy)h+='<div class="hint">它正在跑或排着队，说完才能交。</div>';
  }
  const isDesktop=!!(S.execution&&S.execution[a]&&S.execution[a].endpoint==='desktop');
  const canC=typeof x.can_compact==='boolean'?(!x.compacting&&!x.handed_off&&!isDesktop&&x.can_compact):(x.session&&!x.handed_off&&!x.compacting&&!isDesktop);
  const compactHint=x.compacting?'正在压缩，压完会议里会插一条消息。'
    :x.handed_off?'在终端里，收回来再压。'
    :isDesktop?'当前不由 CLI 执行，请在当前执行端压缩。'
    :!canC?(x.session?'当前状态暂不可压缩。':'还没建会话，或暂无可压缩的新记录。')
    :'聊久了会变慢、变贵。压完它只记要点，其他成员不受影响。'+(x.compact_at?'（上次压缩：'+esc(x.compact_at)+'）':'')+(x.ctx&&x.ctx.used?'<br>现在上下文用了 '+fmtK(x.ctx.used)+(x.ctx.window?' / '+fmtK(x.ctx.window)+'（'+Math.round(x.ctx.used*100/x.ctx.window)+'%）':'')+'。':'');
  h+='<h3 style="margin-top:14px">压缩上下文</h3><div class="hint">'+compactHint+'</div>'+
    '<div class="btns"><button type="button" id="aCompact"'+(canC?'':' disabled')+'>压缩 '+esc(a)+'</button></div>';
  if(hasTools)h+='<h3 style="margin-top:14px">工具（这场会议）</h3><div id="toolsBox"><div class="hint">读取中…</div></div>';
  if(!hasTerminal)h+='<div class="btns" style="margin-top:14px"><button type="button" id="aClose">关闭</button></div>';
  showModal(h);
  if(hasTools)loadTools(a,x);
  bindModelSettings(a,mo,aiBusy);
  bindExecutionSettings(a,(S.execution||{})[a],aiBusy);
  document.getElementById('aClose').onclick=hideModal;
  document.getElementById('aCompact').onclick=async()=>{
    if(!confirm('压缩 '+a+' 的上下文？压完它只记要点。'+(x.busy?'\n\n它手上有活，会等这一轮说完再压。':'')))return;
    const [ok,j]=await post(api('compact'),{ai:a});if(!ok)alert(j.error||'失败');await loadState();poll();openAi(a);
  };
  const c=document.getElementById('aCopy');if(c)c.onclick=()=>{copyText(x.cmd);c.textContent='已复制'};
  const t=document.getElementById('aToggle');if(t)t.onclick=async()=>{
    const [ok,j]=await post(api('handoff'),{ai:a,on:!x.handed_off});
    if(!ok){alert(j.error||'失败');return}
    await loadState();poll();openAi(a);
  };
}
document.getElementById('bList').onclick=()=>{document.body.classList.remove('nav-open');openList()};
document.getElementById('bMode').onclick=toggleMode;
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
  const [ok,j]=await post(api('wrapup'));if(!ok)alert(j.error||'失败');closeMeetingTools();poll();
};
document.getElementById('bAgents').onclick=openAgents;
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
    await loadState();openAi(a);
  };
}
drawQuick();
