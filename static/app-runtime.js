let polling=null, roomViewGeneration=0, recallCount=0;   // 渲染时也保持单次轮询，切换会话后丢弃旧批次
async function poll(){
  if(!RID||(polling&&polling.rid===RID&&polling.generation===roomViewGeneration))return;
  const rid=RID, generation=roomViewGeneration, request={rid,generation};polling=request;
  try{
    if(!S)await loadState();if(rid!==RID||generation!==roomViewGeneration)return;
    const r=await fetch(api('messages')+'?since='+since,{cache:'no-store'});
    if(r.status===404){if(rid!==RID||generation!==roomViewGeneration)return;if(polling===request)polling=null;return roomGone()}
    const j=await r.json();
    if(rid!==RID||generation!==roomViewGeneration)return;
    if(j.meeting!==curMeeting){curMeeting=j.meeting;feed.innerHTML='';if(since!==0||j.messages.length<j.next){since=0;if(polling===request)polling=null;return poll()}}
    const atBottom=feed.scrollHeight-feed.scrollTop-feed.clientHeight<60;
    for(let i=0;i<j.messages.length;i++){
      if(rid!==RID||generation!==roomViewGeneration)return;
      add(j.messages[i]);
      if((i+1)%20===0&&i+1<j.messages.length)await new Promise(resolve=>setTimeout(resolve,0));
    }
    if((j.recalled?.length||0)!==recallCount){recallCount=j.recalled?.length||0;applyMessageRecalls(j.recalled)}
    syncUndo();since=j.next;
    if(j.messages.length&&atBottom)feed.scrollTop=feed.scrollHeight;
    lastRun={running:j.running||[],queued:j.queued||0};
    if(!document.hidden)markSeen(rid,j.next);
  }catch(e){}
  finally{if(polling===request)polling=null}
  if(rid!==RID)return;
  await loadState();
  drawStatus();
}
async function loadState(){
  if(!RID)return;const generation=roomViewGeneration;
  try{const r=await fetch(api('state'),{cache:'no-store'});if(generation!==roomViewGeneration)return;if(r.status===404)return roomGone();const j=await r.json();if(generation!==roomViewGeneration)return;S=j;drawState()}catch(e){}
}
// ===== 几场会议：切换、列表、谁在跑、哪场在等你 =====
const roomList=document.getElementById('roomList');
let ROOMS=[];
// 一场会议的状态牌：在跑 > 有话对你说（AI @用户 了你还没看）> 有新消息
function roomBadge(m){
  if((m.running||[]).some(x=>!x.startsWith('compact:')))return ['run',(m.running.filter(x=>!x.startsWith('compact:')).join('、'))+' 在想'];
  if(m.id===RID)return null;
  const seen=seenMap()[m.id];
  if(seen==null)return null;   // 这台浏览器没看过的老会议：不标
  if(m.last_to_user>=seen)return ['you','等你'];
  if(m.count>seen)return ['','新 '+(m.count-seen)];
  return null;
}
roomList.addEventListener('click',e=>{
  const a=e.target.closest('a[data-id]');if(!a)return;
  if(e.ctrlKey||e.metaKey||e.shiftKey||e.button)return;   // Ctrl 点 / 中键：新标签页里开
  e.preventDefault();switchRoom(a.dataset.id);
});
function resetRoomView(){
  hideMenu();selectionTools.hidden=true;setMeetingSide(false);
  since=0;recallCount=0;curMeeting=undefined;S=null;feed.innerHTML='';
  for(const k in msgById)delete msgById[k];
  liveCards.clear();
  restoreDraft();lastRun={running:[],queued:0};
  annVal='';showAnn();boardSig='';closeEdit();
  if(typeof closeToc==='function')closeToc();
  if(vw.classList.contains('on')){if(ed?.dirty)saveImageEdit(ed);endEdit();vw.classList.remove('on')}
  document.getElementById('stops').dataset.k='';
}
function switchRoom(id,replace){
  if(!id)return;
  if(id!==RID){
    ta.blur();roomViewGeneration++;RID=id;resetRoomView();resumeDraftUploads(id);
  }else if(!S){restoreDraft();resumeDraftUploads(id)}
  const params=new URLSearchParams(location.search);
  params.set('r',id);
  const u='?'+params.toString();
  if(location.search!==u)(replace?history.replaceState:history.pushState).call(history,{r:id},'',u);
  post(api('open'),{});
  drawRooms();
  poll().then(()=>{feed.scrollTop=feed.scrollHeight;queueJump()});
}
addEventListener('popstate',()=>{
  const id=new URLSearchParams(location.search).get('r');
  if(id&&id!==RID)switchRoom(id,true);
});
addEventListener('pageshow',event=>{if(event.persisted)restoreDraft()});
let goneShown=false;
function roomGone(){
  if(goneShown)return;goneShown=true;
  showModal('<h3>这场会议不在了</h3><div class="hint">它被删了（移进了回收站），或者会议号不对。</div><div class="btns"><button type="button" id="gList" class="pri">去会话管理</button></div>');
  document.getElementById('gList').onclick=()=>{goneShown=false;hideModal();RID=null;resetRoomView();pickRoom()};
}
async function pickRoom(){
  const j=await pollRooms();
  const rooms=(j&&j.rooms)||[];
  const id=(j&&j.last&&rooms.some(m=>m.id===j.last)&&j.last)||((rooms.find(m=>!m.archived)||rooms[0]||{}).id);
  if(id)switchRoom(id,true);
  else {drawState();feed.innerHTML='<div class="workspace-empty"><h2>开始一场新会话</h2><p>添加联系人，创建项目，再邀请成员一起协作。</p><button id="emptyNew">＋ 创建项目 / 会话</button></div>';document.getElementById('emptyNew').onclick=()=>openNew(true)}
}
document.getElementById('rNew').onclick=()=>openNew(false);
if(document.addEventListener)document.addEventListener('visibilitychange',()=>{if(!document.hidden){if(RID){if(since)markSeen(RID,since);poll()}pollRooms()}});
setInterval(()=>{if(!document.hidden&&RID)poll()},1500);
setInterval(()=>{if(!document.hidden)pollRooms()},3000);
refreshContacts().catch(e=>console.error(e));
setInterval(()=>{if(!document.hidden)refreshContacts(undefined,true).catch(()=>{})},10000);
if(RID)switchRoom(RID,true);else pickRoom();
