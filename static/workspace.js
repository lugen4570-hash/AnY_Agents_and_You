// Desktop bridge abstraction shared across browser, pywebview and Tauri 2 shells.
function createCojamDesktop(win){
  const target=win||(typeof window!=='undefined'?window:globalThis);
  const tauriInvoke=()=>{const t=target&&target.__TAURI_INTERNALS__;return t&&typeof t.invoke==='function'?t.invoke.bind(t):null;};
  const pyApi=()=>{const p=target&&target.pywebview;return p&&p.api?p.api:null;};
  const kind=()=>tauriInvoke()?'tauri':(pyApi()?'pywebview':'web');
  const canChooseWorkdir=()=>Boolean(tauriInvoke()||(pyApi()&&typeof pyApi().choose_workdir==='function'));
  const canChooseAgentFile=()=>Boolean(tauriInvoke()||(pyApi()&&typeof pyApi().choose_agent_file==='function'));
  const chooseWorkdir=async()=>{
    const inv=tauriInvoke();
    if(inv)return await inv('cojam_choose_workdir');
    const api=pyApi();
    if(api&&typeof api.choose_workdir==='function')return await api.choose_workdir();
    throw Error('桌面文件夹选择器不可用');
  };
  const chooseAgentFile=async()=>{
    const inv=tauriInvoke();
    if(inv)return await inv('cojam_choose_agent_file');
    const api=pyApi();
    if(api&&typeof api.choose_agent_file==='function')return await api.choose_agent_file();
    throw Error('桌面文件选择器不可用');
  };
  const ready=cb=>{
    if(typeof cb!=='function'||!target||typeof target.addEventListener!=='function')return;
    if(canChooseWorkdir()||canChooseAgentFile()){cb();return;}
    const onReady=()=>{
      if(typeof target.removeEventListener==='function'){
        target.removeEventListener('pywebviewready',onReady);
        target.removeEventListener('cojamdesktopready',onReady);
      }
      cb();
    };
    target.addEventListener('pywebviewready',onReady,{once:true});
    target.addEventListener('cojamdesktopready',onReady,{once:true});
  };
  return {
    get kind(){return kind();},
    get nativeHeartbeat(){return Boolean(target&&target.__COJAM_NATIVE_HEARTBEAT__===true);},
    canChooseWorkdir,
    canChooseAgentFile,
    chooseWorkdir,
    chooseAgentFile,
    ready,
  };
}
if(typeof window!=='undefined'){window.cojamDesktop=window.cojamDesktop||createCojamDesktop(window);}

// Contacts belong to the application. Membership and permissions belong to a conversation.
let PROJECTS=[],CONTACTS=[],contactMode='global';
function uiIcon(name){const paths={folder:'M3 7V5a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7Z',message:'M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 3V6a2 2 0 0 1 2-2Z',members:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',panel:'M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1ZM15 3v18',arrow:'M5 12h14M13 6l6 6-6 6',terminal:'m5 7 4 5-4 5M13 17h6',device:'M4 3h16v13H4ZM8 21h8M12 16v5',link:'m10 13 4-4M8 15l-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0M13 9l1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0',user:'M20 21v-2a6 6 0 0 0-6-6h-4a6 6 0 0 0-6 6v2M16 5a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z'};return '<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+(paths[name]||paths.message)+'"/></svg>'}
const PERM_LABELS={read:'读取会话',post:'发言',trigger:'唤起其他 AI',board:'编辑看板',files:'分享本机文件',work:'允许干活'};
const PERM_GROUPS=[
  {id:'chat',label:'参与对话',hint:'读消息、发言、@成员',keys:['read','post','trigger'],defaults:true},
  {id:'collab',label:'看板与附件',hint:'改看板、发文件',keys:['board','files'],defaults:false},
  {id:'work',label:'允许干活',hint:'改文件与跑命令（需干活模式）',keys:['work'],defaults:false},
];
function groupPermValue(perms,group){
  if(!perms)return group.defaults;
  const defined=group.keys.filter(k=>perms[k]!==undefined);
  return defined.length?defined.some(k=>!!perms[k]):group.defaults;
}
function expandGroupedPerms(groupState){
  const out={};
  PERM_GROUPS.forEach(g=>{const v=!!groupState[g.id];g.keys.forEach(k=>{out[k]=v;});});
  return out;
}
function contactPicker(ids){return CONTACTS.filter(a=>a.enabled).map(a=>'<label class="contact-pick"><input type="checkbox" data-contact="'+esc(a.id)+'"'+(ids.includes(a.id)?' checked':'')+'>'+esc(a.label)+' <small>'+esc(a.kind==='user'?'用户':AG_DRV[a.driver])+'</small></label>').join('')||'<p class="hint">先在左侧添加联系人，也可以先创建空会话。</p>'}
let contactsRequestSequence=0, contactsAppliedSequence=0;
async function refreshContacts(signal,reload=false){const seq=++contactsRequestSequence;const r=await fetch('/api/agents'+(reload?'?reload=1':''),{signal});if(!r.ok)throw Error('读取联系人失败');const data=await r.json();if((signal&&signal.aborted)||seq<contactsAppliedSequence)return;contactsAppliedSequence=seq;agCat=data;CONTACTS=agCat.agents||[];drawContacts();if(typeof drawQuick==='function')drawQuick()}
function contactStatusLabel(a){const c=(agCat.connections||{})[a.id]||{},m=(agCat.members||{})[a.id]||{};if(m.standby)return 'MCP 待命中';if(m.automatic)return '自动响应已连接';if(a.kind==='user'&&c.state==='waiting')return '邀请已生成，从未连接';return c.label||'未验证'}
function contactChannelLabel(a){
  const c=(agCat.connections||{})[a.id]||{},m=(agCat.members||{})[a.id]||{};
  if(a.kind==='user')return '网页接入'+(c.client?' · '+c.client:'');
  if(m.standby)return 'MCP 待命'+((m.device)?' · '+m.device:'');   // Claude/Codex 桌面端也能待命，不只 external
  if(a.driver==='external')return (m.automatic?'自动响应端':'外部接入')+((m.device||c.client)?' · '+(m.device||c.client):'');
  if(a.driver==='acp')return 'ACP 直连';
  return a.driver==='http'?'HTTP 服务':'本机程序';
}
let contactListMarkup='';
function drawContacts(){const box=document.getElementById('contactList');const contacts=CONTACTS.filter(a=>a.enabled||a.user&&!['cli','acp','claude','codex'].includes(a.driver)),devices=agCat.owner_devices||[];const own='<li><button data-owner-devices><span class="avatar" style="--c:#8257ed">我</span><span>我<small>用户 · 本机账户</small><small class="contact-channel">↳ 本机会议室</small>'+devices.map(d=>'<small class="contact-channel">↳ '+esc(d.label)+' · '+(d.online?'最近在线':'离线')+'</small>').join('')+'</span></button></li>';const html=own+contacts.map(a=>'<li class="contact-row"><button data-contact-open="'+esc(a.id)+'"><span class="avatar" style="--c:'+esc(a.color)+'">'+esc(a.letter)+'</span><span>'+esc(a.label)+'<small>@'+esc(a.id)+' · '+esc(a.kind==='user'?'用户':'Harness')+'</small><small class="contact-channel">↳ '+esc(contactChannelLabel(a))+' · '+esc(a.enabled?contactStatusLabel(a):'未找到程序')+'</small></span></button>'+(a.builtin?'':'<button class="contact-delete" data-contact-delete="'+esc(a.id)+'" aria-label="删除联系人 '+esc(a.label)+'" title="删除联系人">×</button>')+'</li>').join('');if(html!==contactListMarkup){const scroll=box.scrollTop;const active=document.activeElement;const owner=active&&active.hasAttribute&&active.hasAttribute('data-owner-devices');const id=active&&active.dataset&&(active.dataset.contactOpen||active.dataset.contactDelete);const deleting=active&&active.dataset&&!!active.dataset.contactDelete;box.innerHTML=html;contactListMarkup=html;box.scrollTop=scroll;if(owner||id){const buttons=box.querySelectorAll('button');const target=[...buttons].find(b=>owner?b.hasAttribute('data-owner-devices'):(deleting?b.dataset.contactDelete:b.dataset.contactOpen)===id);if(target)target.focus({preventScroll:true})}}document.getElementById('contactCount').textContent=contacts.length+1}
function drawRoomIdentity(){
  const selected=ROOMS.find(m=>m.id===RID),project=PROJECTS.find(p=>p.id===(selected&&selected.project));
  document.getElementById('roomContext').textContent=project?project.name:'会话空间';
  document.getElementById('roomSummary').textContent=S&&S.participants?S.participants.length+' 位受邀成员 · 独立会话与权限':'人和 AI，在同一张桌上';
  document.getElementById('roomMemberFaces').innerHTML=((S&&S.participants)||[]).slice(0,4).map(id=>{const a=CONTACTS.find(c=>c.id===id);return '<span style="--c:'+esc(a?a.color:'#787d83')+'">'+esc(a?a.letter:id.slice(0,1).toUpperCase())+'</span>'}).join('');
  const brief=S&&S.announcement||'';document.getElementById('sessionBrief').hidden=!brief.trim();document.getElementById('sessionBriefText').textContent=brief;
}
function drawRooms(){
  const live=ROOMS.filter(m=>!m.archived||m.id===RID),query=document.getElementById('navSearch').value.trim().toLocaleLowerCase();
  drawRoomIdentity();
  const row=m=>{const b=roomBadge(m);return '<li class="'+(m.id===RID?'cur':'')+'"><a href="?r='+encodeURIComponent(m.id)+'" data-id="'+esc(m.id)+'"'+(m.id===RID?' aria-current="page"':'')+'>'+uiIcon('message')+'<span class="dot '+(b?(b[0]||'new'):'')+'"></span><span class="t">'+esc(m.title)+'</span>'+(b?'<span class="b '+b[0]+'">'+esc(b[1])+'</span>':'')+'</a></li>'};
  const html=PROJECTS.map(p=>{
    const matchesProject=p.name.toLocaleLowerCase().includes(query);
    const rooms=live.filter(m=>(m.project||legacyProject(m.workdir))===p.id&&(matchesProject||m.title.toLocaleLowerCase().includes(query)));
    if(query&&!matchesProject&&!rooms.length)return '';
    const expanded=!!query||!collapsedProjects.has(p.id);
    return '<li class="project"><div class="project-head"><button data-project-toggle="'+esc(p.id)+'" aria-expanded="'+expanded+'">'+uiIcon('folder')+' <span>'+esc(p.name)+'</span><span class="project-count">'+rooms.length+'</span></button><button data-project-new="'+esc(p.id)+'" title="在此项目下新建会话" aria-label="新建会话">＋</button></div><ul class="rl project-rooms"'+(expanded?'':' hidden')+'>'+rooms.map(row).join('')+'</ul></li>';
  }).join('')||'<li class="nav-empty">'+(query?'没有匹配的项目或会话':'创建项目，开始第一场会话。')+'</li>';
  if(roomList.innerHTML!==html)roomList.innerHTML=html;
  const wait=ROOMS.filter(m=>m.id!==RID&&!m.archived&&(roomBadge(m)||[])[0]==='you').length;
  const manage=document.getElementById('bList');
  manage.innerHTML='管理'+(wait?' <span class="nav-wait">'+wait+'</span>':'');
  manage.setAttribute('aria-label','会话管理、归档与回收站'+(wait?'，'+wait+' 个其他会话等你回复':''));
  manage.title='会话管理、归档与回收站'+(wait?' · '+wait+' 个其他会话等你回复':'');
  const nav=document.getElementById('navToggle');nav.classList.toggle('attn',wait>0);
  nav.setAttribute('aria-label','打开联系人和项目'+(wait?'，'+wait+' 个其他会话等你回复':''));
  document.title=(wait?'('+wait+') ':'')+(S&&S.title?S.title+' · AnY':'AnY');
}
// The server supplies resolved project IDs, including migrated folder groups.
function legacyProject(wd){return (PROJECTS.find(p=>p.workdir===wd)||{}).id||''}
const collapsedProjects=new Set();
async function pollRooms(){try{const r=await fetch('/api/rooms',{cache:'no-store'});if(!r.ok)throw Error('读取项目失败');const j=await r.json();ROOMS=j.rooms||[];PROJECTS=j.projects||[];const m=seenMap();ROOMS.forEach(r=>{if(m[r.id]==null)m[r.id]=r.count});try{localStorage.setItem('rt_seen',JSON.stringify(m))}catch(e){}drawRooms();return j}catch(e){return null}}
function attachWorkspaceFolderPicker(inputId){
  const input=document.getElementById(inputId);if(!input)return;
  const catalog=typeof agCat!=='undefined'&&agCat;
  if(catalog&&catalog.local_workspace===false)return;
  const macBrowserPicker=catalog&&catalog.macos_workspace_picker===true;
  const button=document.createElement('button');button.type='button';button.textContent='选择文件夹';button.hidden=true;
  input.parentElement.append(button);
  const bridge=(typeof window!=='undefined'&&window.cojamDesktop)||null;
  const legacy=()=>typeof window!=='undefined'&&window.pywebview&&window.pywebview.api&&typeof window.pywebview.api.choose_workdir==='function'?window.pywebview.api:null;
  const canPickNatively=()=>bridge?bridge.canChooseWorkdir():!!legacy();
  const enable=()=>{button.hidden=!(canPickNatively()||macBrowserPicker)};
  enable();
  if(bridge&&typeof bridge.ready==='function')bridge.ready(enable);
  else if(typeof window!=='undefined'&&typeof window.addEventListener==='function')window.addEventListener('pywebviewready',enable,{once:true});
  button.onclick=async()=>{
    button.disabled=true;
    try {
      let path;
      if(canPickNatively()){
        path=await (bridge?bridge.chooseWorkdir():legacy().choose_workdir());
      } else if(macBrowserPicker){
        const [ok,result]=await post('/api/projects/choose-workdir',{});
        if(!ok)throw Error(result.error);
        path=result.workdir;
      }
      if(path){input.value=path;input.dispatchEvent(new Event('input',{bubbles:true}))}
    } catch(e){
      alert('无法打开文件夹选择器，请重试或手动填写路径。');
    } finally {
      button.disabled=false;
    }
  };
}
async function openProject(){document.body.classList.remove('nav-open');
  if(!agCat){
    try{await refreshContacts()}catch(e){alert('无法读取本机项目设置，请重试。');return}
  }
  if(agCat.local_workspace===false){showModal('<h3>新建项目</h3><p class="hint">当前是通过其他设备连接。手机网页不支持使用本地文件夹创建项目，也不能选择或指定运行合拍的电脑文件夹。</p><div class="btns"><button onclick="hideModal()">关闭</button></div>');return}showModal('<h3>新建项目</h3><p class="hint">项目中的会话共用工作文件夹，各自管理成员和权限。</p><label>项目名称<input id="pName" maxlength="60" placeholder="例如：我的应用"></label><label>工作文件夹<input id="pWd" placeholder="工作文件夹完整路径" value="'+esc((S&&S.workdir)||agCat.default_dir||'')+'"></label><p id="pErr" role="alert"></p><div class="btns"><button id="pCancel">取消</button><button id="pSave" class="pri">创建项目</button></div>');attachWorkspaceFolderPicker('pWd');document.getElementById('pCancel').onclick=hideModal;document.getElementById('pSave').onclick=async e=>{const button=e.currentTarget;if(button.disabled)return;const name=document.getElementById('pName').value,workdir=document.getElementById('pWd').value;button.disabled=true;button.textContent='正在创建…';try{const [ok,j]=await post('/api/projects/new',{name,workdir});if(!ok){const error=document.getElementById('pErr');if(error)error.textContent=j.error||'创建失败';return}await pollRooms();if(document.getElementById('pSave')===button){hideModal();openNew(false,j.project.id)}}finally{button.disabled=false;button.textContent='创建项目'}};document.getElementById('pName').focus()}
async function openNew(first,projectId){
  document.body.classList.remove('nav-open');
  await pollRooms();await refreshContacts();if(!PROJECTS.length)return openProject();
  const selected=projectId||(S&&(S.project||legacyProject(S.workdir)))||PROJECTS[0].id;
  showModal('<h3>新建会话</h3><label>所属项目<select id="nProject">'+PROJECTS.map(p=>'<option value="'+esc(p.id)+'"'+(selected===p.id?' selected':'')+'>'+esc(p.name)+'</option>').join('')+'</select></label><label>会话标题<input id="nTitle" maxlength="60" placeholder="这次想做什么？"></label><label>目标<textarea id="nAnn" placeholder="描述目标，可稍后修改"></textarea></label><h4>邀请联系人</h4><p class="hint">已按 Agent 的默认加入设置勾选，可以在创建前调整。</p><div id="nContacts">'+contactPicker(agCat.default_participants || [])+'</div><div class="btns"><button id="nCancel">取消</button><button id="nOk" class="pri">创建会话</button></div>');
  document.getElementById('nCancel').onclick=hideModal;document.getElementById('nOk').onclick=async e=>{const button=e.currentTarget;if(button.disabled)return;const body={title:document.getElementById('nTitle').value,announcement:document.getElementById('nAnn').value,project:document.getElementById('nProject').value,participants:[...mbox.querySelectorAll('[data-contact]:checked')].map(e=>e.dataset.contact)};button.disabled=true;button.textContent='正在创建…';try{const [ok,j]=await post('/api/rooms/new',body);if(!ok)return alert(j.error||'创建失败');if(document.getElementById('nOk')===button){hideModal();document.body.classList.remove('nav-open');switchRoom(j.id)}pollRooms()}finally{button.disabled=false;button.textContent='创建会话'}};document.getElementById('nTitle').focus();
}
async function openAgents(){if(!RID)return;contactMode='members';const rid=RID;await refreshContacts();if(rid!==RID)return;const ids=(S&&S.participants)||[],perms=(S&&S.permissions)||{};
  const memberList=CONTACTS.filter(a=>a.enabled||ids.includes(a.id));
  const rowHtml=a=>{
    const p=perms[a.id]||{read:true,post:true,trigger:true,board:false,files:false,work:false};
    return '<section class="member-row" data-member="'+esc(a.id)+'"><label class="contact-pick"><input type="checkbox" data-member-check'+(ids.includes(a.id)?' checked':'')+'>'+esc(a.label)+' <small>@'+esc(a.id)+'</small></label><div class="perm-grid">'+PERM_GROUPS.map(g=>'<label><input type="checkbox" data-perm-group="'+g.id+'"'+(groupPermValue(p,g)?' checked':'')+'><span>'+esc(g.label)+'<small class="perm-sub">'+esc(g.hint)+'</small></span></label>').join('')+'</div></section>';
  };
  const bulkBar='<div class="perm-bulk-bar"><button type="button" class="perm-bulk-btn" id="mMembersAll"></button><div class="perm-bulk-perms">'+PERM_GROUPS.map(g=>'<button type="button" class="perm-bulk-btn" data-perm-all="'+g.id+'"></button>').join('')+'</div></div>';
  showModal('<h3>会话成员与权限</h3><p class="hint">仅影响当前会话。同一联系人在其他会话中的权限独立配置。干活权限还需会话切到干活模式；CLI / 外部 Harness 必须自行遵守只读约定。</p>'+bulkBar+'<div id="memberRows">'+memberList.map(rowHtml).join('')+'</div><div class="btns"><button id="mClose">取消</button><button id="mSave" class="pri">保存成员和权限</button></div>');
  const rows=[...mbox.querySelectorAll('[data-member]')];
  const activeRows=()=>rows.filter(r=>r.querySelector('[data-member-check]').checked);
  const syncBulk=()=>{
    const active=activeRows();
    const mBtn=document.getElementById('mMembersAll');
    if(mBtn){
      const allM=rows.length>0&&active.length===rows.length;
      mBtn.disabled=!rows.length;
      mBtn.classList.toggle('on',allM);
      mBtn.setAttribute('aria-pressed',String(allM));
      mBtn.textContent=allM?'✓ 成员已全选（点击全取消）':'全选成员（'+active.length+'/'+rows.length+'）';
    }
    PERM_GROUPS.forEach(g=>{
      const b=mbox.querySelector('[data-perm-all="'+g.id+'"]');if(!b)return;
      const onCount=active.filter(r=>r.querySelector('[data-perm-group="'+g.id+'"]').checked).length;
      const allOn=active.length>0&&onCount===active.length;
      b.disabled=!active.length;
      b.classList.toggle('on',allOn);
      b.setAttribute('aria-pressed',String(allOn));
      b.textContent=allOn?'✓ '+g.label+'（点此全关）':g.label+'（一键全开）';
    });
  };
  const syncRow=row=>{const on=row.querySelector('[data-member-check]').checked;row.querySelectorAll('[data-perm-group]').forEach(i=>i.disabled=!on);};
  rows.forEach(row=>{
    syncRow(row);
    row.querySelector('[data-member-check]').onchange=()=>{syncRow(row);syncBulk();};
    row.querySelectorAll('[data-perm-group]').forEach(i=>{i.onchange=syncBulk;});
  });
  const mAllBtn=document.getElementById('mMembersAll');
  if(mAllBtn)mAllBtn.onclick=()=>{
    const allM=rows.length>0&&activeRows().length===rows.length;
    rows.forEach(row=>{row.querySelector('[data-member-check]').checked=!allM;syncRow(row);});
    syncBulk();
  };
  mbox.querySelectorAll('[data-perm-all]').forEach(btn=>{
    btn.onclick=()=>{
      const gid=btn.dataset.permAll,active=activeRows();
      if(!active.length)return;
      const allOn=active.every(r=>r.querySelector('[data-perm-group="'+gid+'"]').checked);
      active.forEach(r=>{r.querySelector('[data-perm-group="'+gid+'"]').checked=!allOn;});
      syncBulk();
    };
  });
  syncBulk();
  document.getElementById('mClose').onclick=hideModal;document.getElementById('mSave').onclick=async()=>{const participants=[],permissions={};rows.forEach(row=>{if(!row.querySelector('[data-member-check]').checked)return;const id=row.dataset.member;participants.push(id);const state={};row.querySelectorAll('[data-perm-group]').forEach(i=>{state[i.dataset.permGroup]=i.checked;});permissions[id]=expandGroupedPerms(state);});const [ok,j]=await post('/api/r/'+encodeURIComponent(rid)+'/members',{participants,permissions});if(!ok)return alert(j.error||'保存失败');hideModal();await loadState()};
}
document.getElementById('contactsAdd').onclick=()=>startConnectionWizard();
if(document.getElementById('agentSettingsBtn'))document.getElementById('agentSettingsBtn').onclick=()=>openAgentManager();
document.getElementById('contactList').onclick=async e=>{const del=e.target.closest('[data-contact-delete]');if(del){const id=del.dataset.contactDelete,contact=CONTACTS.find(a=>a.id===id);if(!confirm('删除联系人 '+(contact?contact.label:id)+'？将自动从所有会话移除，接入密钥失效，历史消息保留。'))return;del.disabled=true;const [ok,j]=await post('/api/agents/remove',{id});if(!ok){del.disabled=false;return alert(j.error||'删除失败')}await refreshContacts();if(RID)await loadState();return}if(e.target.closest('[data-owner-devices]'))return startConnectionWizard('','mydevice');const b=e.target.closest('[data-contact-open]');if(b)openConnection(b.dataset.contactOpen)};
document.getElementById('projectAdd').onclick=openProject;
const NAV_COLLAPSE_KEY='cojam_nav_collapsed';
const isDesktopNav=()=>typeof matchMedia==='function'&&matchMedia('(min-width:850px)').matches;
function setNavCollapsed(collapsed){
  const on=!!collapsed;
  document.body.classList.toggle('nav-collapsed',on);
  try{localStorage.setItem(NAV_COLLAPSE_KEY,on?'1':'0')}catch(e){}
  const t=document.getElementById('navToggle'),c=document.getElementById('navClose'),r=document.getElementById('rooms');
  if(t)t.setAttribute('aria-expanded',String(!on));
  if(c)c.setAttribute('aria-expanded',String(!on));
  if(r&&'inert' in r)r.inert=isDesktopNav()&&on;
}
try{if(localStorage.getItem(NAV_COLLAPSE_KEY)==='1')setNavCollapsed(true)}catch(e){}
document.getElementById('navToggle').onclick=()=>isDesktopNav()?setNavCollapsed(false):document.body.classList.toggle('nav-open');
document.getElementById('navClose').onclick=()=>isDesktopNav()?setNavCollapsed(true):document.body.classList.remove('nav-open');
document.getElementById('navShade').onclick=()=>document.body.classList.remove('nav-open');
document.getElementById('roomList').addEventListener('click',e=>{const add=e.target.closest('[data-project-new]'),toggle=e.target.closest('[data-project-toggle]');if(add)openNew(false,add.dataset.projectNew);if(toggle){const id=toggle.dataset.projectToggle;collapsedProjects.has(id)?collapsedProjects.delete(id):collapsedProjects.add(id);drawRooms()}if(e.target.closest('a[data-id]'))document.body.classList.remove('nav-open')});

const navSearch=document.getElementById('navSearch');
navSearch.addEventListener('input',drawRooms);
navSearch.addEventListener('keydown',e=>{if(e.key==='Escape'){navSearch.value='';drawRooms();navSearch.blur()}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'&&!document.getElementById('modal').classList.contains('show')){e.preventDefault();if(isDesktopNav())setNavCollapsed(false);else document.body.classList.add('nav-open');navSearch.focus();navSearch.select()}});
if(!/Mac|iPhone|iPad/.test(navigator.platform))document.querySelector('.nav-search kbd').textContent='Ctrl K';
