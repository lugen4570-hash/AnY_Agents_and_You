// Desktop bridge abstraction shared across browser, pywebview and Tauri 2 shells.
function createAnYDesktop(win){
  const target=win||(typeof window!=='undefined'?window:globalThis);
  const tauriInvoke=()=>{const t=target&&target.__TAURI_INTERNALS__;return t&&typeof t.invoke==='function'?t.invoke.bind(t):null;};
  const pyApi=()=>{const p=target&&target.pywebview;return p&&p.api?p.api:null;};
  const kind=()=>tauriInvoke()?'tauri':(pyApi()?'pywebview':'web');
  const canChooseWorkdir=()=>Boolean(tauriInvoke()||(pyApi()&&typeof pyApi().choose_workdir==='function'));
  const canChooseAgentFile=()=>Boolean(tauriInvoke()||(pyApi()&&typeof pyApi().choose_agent_file==='function'));
  const chooseWorkdir=async()=>{
    const inv=tauriInvoke();
    if(inv)return await inv('any_choose_workdir');
    const api=pyApi();
    if(api&&typeof api.choose_workdir==='function')return await api.choose_workdir();
    throw Error('桌面文件夹选择器不可用');
  };
  const chooseAgentFile=async()=>{
    const inv=tauriInvoke();
    if(inv)return await inv('any_choose_agent_file');
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
        target.removeEventListener('anydesktopready',onReady);
        target.removeEventListener('cojamdesktopready',onReady);
      }
      cb();
    };
    target.addEventListener('pywebviewready',onReady,{once:true});
    target.addEventListener('anydesktopready',onReady,{once:true});
    target.addEventListener('cojamdesktopready',onReady,{once:true});
  };
  return {
    get kind(){return kind();},
    get nativeHeartbeat(){return Boolean(target&&(target.__ANY_NATIVE_HEARTBEAT__===true||target.__COJAM_NATIVE_HEARTBEAT__===true));},
    canChooseWorkdir,
    canChooseAgentFile,
    chooseWorkdir,
    chooseAgentFile,
    ready,
  };
}
if(typeof window!=='undefined'){
  window.anyDesktop=window.anyDesktop||createAnYDesktop(window);
  window.cojamDesktop=window.cojamDesktop||window.anyDesktop;
}

// Contacts belong to the application. Membership and permissions belong to a conversation.
let PROJECTS=[],CONTACTS=[],contactMode='global';
function uiIcon(name){const paths={folder:'M3 7V5a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7Z',message:'M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 3V6a2 2 0 0 1 2-2Z',members:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',panel:'M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1ZM15 3v18',arrow:'M5 12h14M13 6l6 6-6 6',terminal:'m5 7 4 5-4 5M13 17h6',device:'M4 3h16v13H4ZM8 21h8M12 16v5',link:'m10 13 4-4M8 15l-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0M13 9l1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0',user:'M20 21v-2a6 6 0 0 0-6-6h-4a6 6 0 0 0-6 6v2M16 5a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z'};return '<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+(paths[name]||paths.message)+'"/></svg>'}
const PERM_LABELS={read:'读取会话',post:'发言',trigger:'唤起其他 AI',board:'编辑看板',files:'分享本机文件',work:'允许干活'};
const PERM_GROUPS=[
  {id:'chat',label:'参与对话',hint:'读消息、发言、@成员',keys:['read','post','trigger'],defaults:true},
  {id:'collab',label:'看板与附件',hint:'改看板、发文件',keys:['board','files'],defaults:false},
  {id:'work',label:'允许干活',hint:'改文件与跑命令（需干活模式）',keys:['work'],defaults:false},
];
const HUMAN_ROOM_PERM_GROUPS=[
  {id:'read',label:'读消息',hint:'查看本人有权看到的会话消息',keys:['read'],defaults:true},
  {id:'post',label:'发言',hint:'在会话中发消息',keys:['post'],defaults:true},
  {id:'trigger',label:'调用开放的 Agent',hint:'点名提问，限独立只读讨论',keys:['trigger'],defaults:false},
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
let contactsRequestSequence=0, contactsAppliedSequence=0;
let contactInstallation=null, contactInstallationSequence=0, contactPoll=null;
async function refreshContacts(signal,reload=false){
  const seq=++contactsRequestSequence;
  const r=await fetch('/api/agents'+(reload?'?reload=1':'?summary=1'),{signal});
  if(!r.ok)throw Error('读取联系人失败');
  const data=await r.json();
  if(signal?.aborted)return;
  // 安装详情只随主动扫描返回。独立排序，避免轻量轮询盖掉接入向导所需的结果。
  if(reload&&seq>=contactInstallationSequence){
    contactInstallationSequence=seq;
    contactInstallation={hosts:data.hosts||[],discovered_presets:data.discovered_presets||[]};
    if(agCat)Object.assign(agCat,contactInstallation);
  }
  if(seq<contactsAppliedSequence)return;
  contactsAppliedSequence=seq;
  agCat={...data,...contactInstallation};
  CONTACTS=agCat.agents||[];
  drawContacts();
  if(typeof drawQuick==='function')drawQuick();
}
function pollContacts(){
  if(!contactPoll)contactPoll=refreshContacts().finally(()=>{contactPoll=null});
  return contactPoll;
}
async function loadContactPanel(title,ready,retry){
  showModal('<h3>'+esc(title)+'</h3><p role="status" id="contactPanelStatus">正在读取…</p><div class="btns"><button type="button" id="contactPanelCancel">取消</button></div>');
  const status=document.getElementById('contactPanelStatus');
  const current=()=>status.isConnected&&modal.classList.contains('show');
  document.getElementById('contactPanelCancel').onclick=()=>hasModalBack()?popModalBack():hideModal();
  try{await ready;return current()}
  catch(error){
    if(current()){
      status.textContent=error.message;
      const button=document.getElementById('contactPanelCancel');
      const retryButton=document.createElement('button');
      retryButton.type='button';retryButton.textContent='重试';retryButton.onclick=retry;
      button.before(retryButton);
    }
    return false;
  }
}
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
  const context=document.getElementById('roomContext');
  context.hidden=!project;context.textContent=project?.name||'';
}
function drawRooms(){
  const live=ROOMS.filter(m=>!m.archived||m.id===RID),query=document.getElementById('navSearch').value.trim().toLocaleLowerCase();
  drawRoomIdentity();
  const canMove=PROJECTS.length>1;
  const row=m=>{const b=roomBadge(m);return '<li class="'+(m.id===RID?'cur':'')+'"><a href="?r='+encodeURIComponent(m.id)+'" data-id="'+esc(m.id)+'" draggable="'+canMove+'"'+(canMove?' title="拖到其他项目可移动会话"':'')+(m.id===RID?' aria-current="page"':'')+'>'+uiIcon('message')+'<span class="dot '+(b?(b[0]||'new'):'')+'"></span><span class="t">'+esc(m.title)+'</span>'+(b?'<span class="b '+b[0]+'">'+esc(b[1])+'</span>':'')+'</a></li>'};
  const html=PROJECTS.map(p=>{
    const matchesProject=p.name.toLocaleLowerCase().includes(query);
    const rooms=live.filter(m=>(m.project||legacyProject(m.workdir))===p.id&&(matchesProject||m.title.toLocaleLowerCase().includes(query)));
    if(query&&!matchesProject&&!rooms.length)return '';
    const expanded=!!query||!collapsedProjects.has(p.id);
    const isRemote=typeof agCat!=='undefined'&&agCat&&agCat.local_workspace===false;
    const settings=isRemote?'':'<button data-project-edit="'+esc(p.id)+'" title="项目设置" aria-label="'+esc(p.name)+'的项目设置">⚙</button>';
    return '<li class="project" data-project-drop="'+esc(p.id)+'"><div class="project-head"><button data-project-toggle="'+esc(p.id)+'" aria-expanded="'+expanded+'">'+uiIcon('folder')+' <span>'+esc(p.name)+'</span><span class="project-count">'+rooms.length+'</span></button>'+settings+'<button data-project-new="'+esc(p.id)+'" title="在此项目下新建会话" aria-label="新建会话">＋</button></div><ul class="rl project-rooms"'+(expanded?'':' hidden')+'>'+rooms.map(row).join('')+'</ul></li>';
  }).join('')||'<li class="nav-empty">'+(query?'没有匹配的项目或会话':'创建项目，开始第一场会话。')+'</li>';
  if(!roomList.dataset.dragging&&roomList.innerHTML!==html)roomList.innerHTML=html;
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
  const append=input.dataset?.appendFolders!==undefined;
  const catalog=typeof agCat!=='undefined'&&agCat;
  if(catalog&&catalog.local_workspace===false)return;
  const macBrowserPicker=catalog&&catalog.macos_workspace_picker===true;
  const button=document.createElement('button');button.type='button';button.textContent=append?'添加文件夹':'选择文件夹';button.hidden=true;
  button.setAttribute('aria-label','选择文件夹');
  input.parentElement.after(button);
  const bridge=(typeof window!=='undefined'&&(window.anyDesktop||window.cojamDesktop))||null;
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
      if(path){input.value=append&&input.value.trim()?input.value.trimEnd()+'\n'+path:path;input.dispatchEvent(new Event('input',{bubbles:true}))}
    } catch(e){
      alert('无法打开文件夹选择器，请重试或手动填写路径。');
    } finally {
      button.disabled=false;
    }
  };
}
async function openProject(project){document.body.classList.remove('nav-open');
  const canBack=typeof hasModalBack==='function'&&hasModalBack();
  const finish=()=>{if(canBack)popModalBack();else hideModal();};
  if(!agCat){
    try{await refreshContacts()}catch(e){alert('无法读取本机项目设置，请重试。');return}
  }
  if(agCat.local_workspace===false){showModal('<div class="connection-heading">'+(canBack?'<button type="button" class="modal-back" id="pBack">← 返回</button>':'')+'<h3>项目设置</h3><button type="button" id="pClose" aria-label="关闭">×</button></div><p class="hint">请在运行 AnY 的设备上管理项目工作目录。</p><div class="btns">'+(canBack?'<button type="button" id="pCancel">返回</button>':'')+'<button onclick="hideModal()">关闭</button></div>');if(canBack&&document.getElementById('pBack'))document.getElementById('pBack').onclick=()=>popModalBack();if(canBack&&document.getElementById('pCancel'))document.getElementById('pCancel').onclick=()=>popModalBack();if(document.getElementById('pClose'))document.getElementById('pClose').onclick=hideModal;return}
  const paths=project?(project.workdirs||[project.workdir]):[];
  showModal((canBack?'<div class="connection-heading"><button type="button" class="modal-back" id="pBack">← 返回</button><h3>'+(project?'项目设置':'新建项目')+'</h3><button type="button" id="pClose" aria-label="关闭">×</button></div>':'<h3>'+(project?'项目设置':'新建项目')+'</h3>')+'<form id="projectForm"><label>项目名称<input id="pName" maxlength="60" required value="'+esc(project?.name||'')+'" placeholder="例如：我的应用"></label><label>工作文件夹<textarea id="pWd" rows="4" required data-append-folders placeholder="每行一个完整路径">'+esc(paths.join('\n'))+'</textarea></label><p class="hint">每行填一个完整路径。第一行是新会话的默认目录，已有会话保留各自的目录。</p><p id="pErr" class="form-error" role="alert"></p><div class="btns"><button type="button" id="pCancel">取消</button><button id="pSave" class="pri" type="submit">'+(project?'保存设置':'创建项目')+'</button></div></form>');
  attachWorkspaceFolderPicker('pWd');
  const form=document.getElementById('projectForm'),button=document.getElementById('pSave');
  if(canBack&&document.getElementById('pBack'))document.getElementById('pBack').onclick=()=>popModalBack();
  if(document.getElementById('pClose'))document.getElementById('pClose').onclick=hideModal;
  document.getElementById('pCancel').onclick=finish;
  form.onsubmit=async e=>{
    e.preventDefault();if(button.disabled)return;
    const name=document.getElementById('pName').value;
    const workdirs=document.getElementById('pWd').value.split(/\r?\n/).map(path=>path.trim()).filter(Boolean);
    const error=document.getElementById('pErr');
    button.disabled=true;error.textContent='';
    try{
      const [ok,j]=await post(project?'/api/projects/update':'/api/projects/new',{id:project?.id,name,workdirs});
      if(!ok){error.textContent=j.error||'保存失败';return}
      await pollRooms();
      if(document.getElementById('projectForm')!==form||!modal.classList.contains('show'))return;
      if(canBack&&project)popModalBack();
      else{hideModal();if(!project)openNew(false,j.project.id);}
    }finally{button.disabled=false}
  };
  document.getElementById('pName').focus();
}
async function openNew(first,projectId){
  document.body.classList.remove('nav-open');
  if(!PROJECTS.length||!agCat){
    const ready=Promise.all([PROJECTS.length?null:pollRooms().then(result=>{if(!result)throw Error('读取项目失败')}),agCat?null:pollContacts()]);
    if(!await loadContactPanel('新建会话',ready,()=>openNew(first,projectId)))return;
  }
  if(!PROJECTS.length)return openProject();
  const selected=projectId||(S&&(S.project||legacyProject(S.workdir)))||PROJECTS[0].id;
  const members=CONTACTS.filter(a=>a.enabled).map(a=>memberPermissionRow(a,false,a.default_permissions||{})).join('');
  showModal('<h3>新建会话</h3><label>所属项目<select id="nProject">'+PROJECTS.map(p=>'<option value="'+esc(p.id)+'"'+(selected===p.id?' selected':'')+'>'+esc(p.name)+'</option>').join('')+'</select></label><label>会话标题<input id="nTitle" maxlength="60" placeholder="这次想做什么？"></label><label>目标<textarea id="nAnn" placeholder="描述目标，可稍后修改"></textarea></label><h4>邀请联系人和设置权限</h4><div id="nContacts">'+(members||'<p class="hint">可以先创建空会话。</p>')+'</div><div class="btns"><button type="button" id="nCancel">取消</button><button type="button" id="nOk" class="pri">创建会话</button></div>');
  const rows=[...document.getElementById('nContacts').querySelectorAll('[data-member]')];
  const projectChoice=document.getElementById('nProject'),createButton=document.getElementById('nOk');
  let workspaceChoice;
  const localWs=typeof agCat==='undefined'||!agCat||agCat.local_workspace!==false;
  if(localWs&&typeof document.createElement==='function'&&typeof post==='function'){
    const label=document.createElement('label');label.textContent='工作目录与分支';
    workspaceChoice=document.createElement('select');workspaceChoice.id='nWorkspace';label.appendChild(workspaceChoice);
    projectChoice.parentElement.after(label);
    let request=0;
    projectChoice.onchange=async()=>{
      const id=projectChoice.value,current=++request;
      const project=PROJECTS.find(p=>p.id===id);
      const folders=(project?.workdirs||[project?.workdir]).filter(Boolean);
      workspaceChoice.innerHTML='<option value="">正在读取工作目录…</option>';
      workspaceChoice.disabled=true;createButton.disabled=true;
      const [ok,j]=await post('/api/projects/workspaces',{id});
      if(current!==request||!workspaceChoice.isConnected)return;
      const options=ok?j.workspaces:folders.map(path=>({path,branch:''}));
      workspaceChoice.innerHTML=options.map(w=>'<option value="'+esc(w.path)+'">'+esc(w.branch?w.branch+' · '+w.path:w.path)+'</option>').join('')||'<option value="">项目没有可用的工作目录</option>';
      workspaceChoice.disabled=!options.length;createButton.disabled=!options.length;
    };
    projectChoice.onchange();
  }
  rows.forEach(row=>{
    const update=()=>syncMemberPermissionRow(row);update();row.querySelector('[data-member-check]').onchange=update;
    row.querySelectorAll('[data-perm-group]').forEach(i=>{i.onchange=()=>{i.dataset.edited='true'}});
  });
  document.getElementById('nCancel').onclick=hideModal;
  document.getElementById('nOk').onclick=async e=>{
    const button=e.currentTarget;if(button.disabled)return;
    const body={title:document.getElementById('nTitle').value,announcement:document.getElementById('nAnn').value,project:projectChoice.value,workspace:workspaceChoice?.value,...readMemberPermissions(rows)};
    projectChoice.disabled=true;if(workspaceChoice)workspaceChoice.disabled=true;
    button.disabled=true;button.textContent='正在创建…';
    try{const [ok,j]=await post('/api/rooms/new',body);if(!ok)return alert(j.error||'创建失败');if(document.getElementById('nOk')===button){hideModal();switchRoom(j.id)}pollRooms()}
    finally{projectChoice.disabled=false;if(workspaceChoice)workspaceChoice.disabled=false;button.disabled=false;button.textContent='创建会话'}
  };
  document.getElementById('nTitle').focus();
}
function memberPermissionRow(a,selected,p,shared,editable=false){
  const human=a.kind==='user',groups=human?HUMAN_ROOM_PERM_GROUPS:PERM_GROUPS;
  const sharing=shared!==undefined&&a.http_protocol?'<label><input type="checkbox" data-guest-discussion'+(shared?' checked':'')+'><span>接受外部成员提问<small class="perm-sub">仅用可见对话，不读取电脑文件</small></span></label>':'';
  const edit=editable?'<button type="button" data-contact-policy="'+esc(a.id)+'">'+(human?'调用与历史':'共享与工作区')+'</button>':'';
  return '<section class="member-row" data-member="'+esc(a.id)+'" data-permissions="'+esc(JSON.stringify(p))+'"><label class="contact-pick"><input type="checkbox" data-member-check'+(selected?' checked':'')+'>'+esc(a.label)+' <small>'+(human?'用户':'Agent')+' · @'+esc(a.id)+'</small></label>'+edit+'<div class="perm-grid">'+groups.map(g=>'<label><input type="checkbox" data-perm-group="'+g.id+'"'+(groupPermValue(p,g)?' checked':'')+'><span>'+esc(g.label)+'<small class="perm-sub">'+esc(g.hint)+'</small></span></label>').join('')+sharing+'</div></section>';
}
function syncMemberPermissionRow(row){
  const on=row.querySelector('[data-member-check]').checked;
  row.querySelectorAll('[data-perm-group]').forEach(i=>i.disabled=!on);
  row.querySelectorAll('[data-guest-discussion]').forEach(i=>i.disabled=!on);
}
function readMemberPermissions(rows,withSharing=false){
  const participants=[],permissions={},guest_discussion={};
  rows.forEach(row=>{
    if(!row.querySelector('[data-member-check]').checked)return;
    const id=row.dataset.member,state={},edited=new Set(),original=JSON.parse(row.dataset.permissions||'{}');
    participants.push(id);
    row.querySelectorAll('[data-perm-group]').forEach(i=>{state[i.dataset.permGroup]=i.checked;if(i.dataset.edited)edited.add(i.dataset.permGroup)});
    const human=CONTACTS.some(a=>a.id===id&&a.kind==='user');
    const groups=human?HUMAN_ROOM_PERM_GROUPS:PERM_GROUPS;
    if(row.querySelectorAll('[data-guest-discussion]')[0]?.checked)guest_discussion[id]=true;
    permissions[id]={};
    groups.forEach(group=>{
      const unchanged=!edited.has(group.id)&&state[group.id]===groupPermValue(original,group);
      group.keys.forEach(key=>{permissions[id][key]=unchanged?(original[key]??group.defaults):!!state[group.id]});
    });
  });
  return withSharing?{participants,permissions,guest_discussion}:{participants,permissions};
}
async function openAgents(){
  if(!RID)return;
  contactMode='members';const rid=RID;const canBack=typeof hasModalBack==='function'&&hasModalBack();
  if(!agCat&&!await loadContactPanel('会话成员与权限',pollContacts(),openAgents))return;
  if(rid!==RID)return;
  const ids=(S&&S.participants)||[],perms=(S&&S.permissions)||{};
  const memberList=CONTACTS.filter(a=>a.enabled||ids.includes(a.id));
  const catalog=typeof agCat==='undefined'?null:agCat;
  const withSharing=catalog?.local_workspace!==false;
  const rowHtml=a=>memberPermissionRow(a,ids.includes(a.id),perms[a.id]||a.default_permissions||{},
    withSharing&&!S?.agent_policies?.[a.id]?.accept_users?!!S?.guest_discussion?.[a.id]:undefined,withSharing&&ids.includes(a.id));
  const devices=withSharing?(catalog?.owner_devices||[]):[];
  const devicePermissions=devices.length?'<h4>允许派活的配对设备</h4><p class="hint">勾选后，这台设备可在本会话派活和审批。</p><div class="perm-grid">'+devices.map(d=>'<label><input type="checkbox" data-dispatch-device="'+esc(d.id)+'"'+(S?.dispatch_devices?.includes(d.id)?' checked':'')+'>'+esc(d.label||d.id)+'</label>').join('')+'</div>':'';
  const bulkBar=withSharing?'<div class="perm-bulk-bar"><button type="button" class="perm-bulk-btn" id="mMembersAll"></button><div class="perm-bulk-perms">'+PERM_GROUPS.map(g=>'<button type="button" class="perm-bulk-btn" data-perm-all="'+g.id+'"></button>').join('')+'</div></div>':'';
  const hint=withSharing?'外部用户点名提问时，用户的调用权限与模型的共享设置都要开启。实际读写和命令范围由执行端限制。':'请在运行 AnY 的电脑上管理本会话成员权限。';
  const footer=withSharing?'<button id="mClose">取消</button><button id="mSave" class="pri">保存成员和权限</button>':'<button id="mClose">关闭</button>';
  const revoked=(S?.revoked_tasks||[]).slice(-8).map(row=>'<p class="hint">@'+esc(row.member)+' · '+esc(row.reason)+'</p>').join('');
  showModal((canBack?'<div class="connection-heading"><button type="button" class="modal-back" id="mHeaderBack">← 返回</button><h3>会话成员与权限</h3><button type="button" id="mHeaderClose" aria-label="关闭">×</button></div>':'<h3>会话成员与权限</h3>')+'<p class="hint">'+hint+'</p>'+revoked+devicePermissions+bulkBar+'<div id="memberRows">'+memberList.map(rowHtml).join('')+'</div><div class="btns">'+footer+'</div>');
  if(canBack&&document.getElementById('mHeaderBack'))document.getElementById('mHeaderBack').onclick=()=>popModalBack();
  if(document.getElementById('mHeaderClose'))document.getElementById('mHeaderClose').onclick=hideModal;
  document.getElementById('mClose').onclick=()=>canBack?popModalBack():hideModal();
  if(!withSharing){mbox.querySelectorAll('#memberRows input').forEach(input=>input.disabled=true);return;}
  mbox.querySelectorAll('[data-contact-policy]').forEach(button=>button.onclick=()=>{if(typeof pushModalBack==='function')pushModalBack(()=>openAgents());openContactPolicy(button.dataset.contactPolicy);});
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
      const inputs=active.map(r=>r.querySelector('[data-perm-group="'+g.id+'"]')).filter(Boolean);
      const allOn=inputs.length>0&&inputs.every(input=>input.checked);
      b.disabled=!inputs.length;
      b.classList.toggle('on',allOn);
      b.setAttribute('aria-pressed',String(allOn));
      b.textContent=allOn?'✓ '+g.label+'（点此全关）':g.label+'（一键全开）';
    });
  };
  const syncRow=syncMemberPermissionRow;
  rows.forEach(row=>{
    syncRow(row);
    row.querySelector('[data-member-check]').onchange=()=>{syncRow(row);syncBulk();};
    row.querySelectorAll('[data-perm-group]').forEach(i=>{i.onchange=()=>{i.dataset.edited='true';syncBulk()}});
  });
  const mAllBtn=document.getElementById('mMembersAll');
  if(mAllBtn)mAllBtn.onclick=()=>{
    const allM=rows.length>0&&activeRows().length===rows.length;
    rows.forEach(row=>{row.querySelector('[data-member-check]').checked=!allM;syncRow(row);});
    syncBulk();
  };
  mbox.querySelectorAll('[data-perm-all]').forEach(btn=>{
    btn.onclick=()=>{
      const gid=btn.dataset.permAll,inputs=activeRows().map(r=>r.querySelector('[data-perm-group="'+gid+'"]')).filter(Boolean);
      if(!inputs.length)return;
      const allOn=inputs.every(input=>input.checked);
      inputs.forEach(input=>{input.checked=!allOn;input.dataset.edited='true'});
      syncBulk();
    };
  });
  syncBulk();
  document.getElementById('mSave').onclick=async()=>{
    const body=readMemberPermissions(rows,true);
    body.dispatch_devices=[...mbox.querySelectorAll('[data-dispatch-device]:checked')].map(input=>input.dataset.dispatchDevice);
    const [ok,j]=await post('/api/r/'+encodeURIComponent(rid)+'/members',body);
    if(!ok)return alert(j.error||'保存失败');await loadState();if(canBack)popModalBack();else hideModal();
  };
}
function contactPolicyChoices(field,title,options,value){
  const selected=value||[];
  const rows=options.map(a=>'<label><input type="checkbox" value="'+esc(a.id)+'" data-policy-value="'+field+'"'+(selected.includes(a.id)?' checked':'')+'>'+esc(a.label||a.id)+'</label>').join('');
  return '<label><input type="checkbox" data-policy-enabled="'+field+'"'+(value!==undefined?' checked':'')+'>'+title+'</label><div class="perm-grid">'+(rows||'<small>本会话暂无可选联系人</small>')+'</div>';
}
function openContactPolicy(id){
  const rid=RID,contact=CONTACTS.find(a=>a.id===id);
  if(!rid||!contact||!S?.participants?.includes(id))return;
  const roster=CONTACTS.filter(a=>S.participants.includes(a.id));
  const humans=roster.filter(a=>a.kind==='user'),others=roster.filter(a=>a.kind!=='user'&&a.id!==id);
  const human=contact.kind==='user',policy=(human?S.user_policies?.[id]:S.agent_policies?.[id])||{};
  const checks=human
    ? '<label>历史消息<select id="contactHistory"><option value="since_join">从加入时开始</option><option value="all_room"'+(policy.history_scope==='all_room'?' selected':'')+'>允许看本房可公开的历史</option></select></label>'
      +contactPolicyChoices('call_agents','只允许调用下列 Agent',others.filter(a=>a.http_protocol),policy.call_agents)
    : (contact.http_protocol?contactPolicyChoices('accept_users','只接受下列外部成员提问',humans,policy.accept_users):'')
      +'<label><input type="checkbox" id="policyHandoff"'+(policy.accept_handoff!==false?' checked':'')+'>接收其他 Agent 转派</label>'
      +contactPolicyChoices('accept_agents','只接收这些 Agent 的转派',others,policy.accept_agents)
      +contactPolicyChoices('handoff_targets','只允许转派给下列 Agent',others,policy.handoff_targets)
      +(!contact.http_protocol?'<h4>工作区</h4><p class="hint">'+esc(S.members?.[id]?.workdir||S.workdir||'')+'。如果当前执行端无法强制落实所选限制，任务会被拦下。</p><label><input type="checkbox" id="policyWorkspace"'+(policy.workspace?' checked':'')+'>为此工作区单独授权</label><div class="perm-grid">'+[['read','读取'],['write','写入'],['exec','执行命令']].map(([key,label])=>'<label><input type="checkbox" data-policy-workspace="'+key+'"'+(policy.workspace?.[key]?' checked':'')+'>'+label+'</label>').join('')+'</div>':'');
  const revoke='<button id="contactPolicyRevoke" type="button">立即撤权</button>';
  const goBack=()=>typeof hasModalBack==='function'&&hasModalBack()?popModalBack():openAgents();
  showModal('<div class="connection-heading"><button type="button" class="modal-back" id="contactPolicyTopBack">← 返回</button><h3>'+esc(contact.label||id)+'</h3><button type="button" id="contactPolicyClose" aria-label="关闭">×</button></div>'+checks+'<div class="btns">'+revoke+'<button id="contactPolicyBack">返回</button><button class="pri" id="contactPolicySave">保存授权</button></div>');
  document.getElementById('contactPolicyClose').onclick=hideModal;
  document.getElementById('contactPolicyTopBack').onclick=goBack;
  document.getElementById('contactPolicyBack').onclick=goBack;
  const revokeButton=document.getElementById('contactPolicyRevoke');
  if(revokeButton)revokeButton.onclick=async()=>{
    const prompt=human?'撤销此用户在本会话的权限？':'撤销此 Agent 在本会话的权限，并停止它正在执行的任务？';
    if(rid!==RID||!confirm(prompt))return;
    const [ok,j]=await post('/api/r/'+encodeURIComponent(rid)+'/contact/revoke',{contact:id});
    if(!ok)return alert(j.error||'撤权失败');
    if(rid===RID){await loadState();await goBack();}
  };
  document.getElementById('contactPolicySave').onclick=async()=>{
    if(rid!==RID)return;
    const next={};
    for(const field of ['call_agents','accept_users','accept_agents','handoff_targets']){
      if(mbox.querySelector('[data-policy-enabled="'+field+'"]')?.checked){
        next[field]=[...mbox.querySelectorAll('[data-policy-value="'+field+'"]:checked')].map(input=>input.value);
      }
    }
    if(human){next.history_scope=document.getElementById('contactHistory').value;}
    else{
      next.accept_handoff=document.getElementById('policyHandoff').checked;
      if(document.getElementById('policyWorkspace')?.checked){
        next.workspace=Object.fromEntries([...mbox.querySelectorAll('[data-policy-workspace]')].map(input=>[input.dataset.policyWorkspace,input.checked]));
      }
    }
    const [ok,j]=await post('/api/r/'+encodeURIComponent(rid)+'/contact/policies',{contact:id,policy:next});
    if(!ok)return alert(j.error||'保存授权失败');
    if(rid===RID){await loadState();await goBack();}
  };
}
document.getElementById('contactsAdd').onclick=()=>startConnectionWizard();
if(document.getElementById('agentSettingsBtn'))document.getElementById('agentSettingsBtn').onclick=()=>openAgentManager();
document.getElementById('contactList').onclick=async e=>{const del=e.target.closest('[data-contact-delete]');if(del){const id=del.dataset.contactDelete,contact=CONTACTS.find(a=>a.id===id);if(!confirm('删除联系人 '+(contact?contact.label:id)+'？将自动从所有会话移除，接入密钥失效，历史消息保留。'))return;del.disabled=true;const [ok,j]=await post('/api/agents/remove',{id});if(!ok){del.disabled=false;return alert(j.error||'删除失败')}await refreshContacts();if(RID)await loadState();return}if(e.target.closest('[data-owner-devices]'))return startConnectionWizard('','mydevice');const b=e.target.closest('[data-contact-open]');if(b)openConnection(b.dataset.contactOpen)};
document.getElementById('projectAdd').onclick=()=>openProject();
const NAV_COLLAPSE_KEY='any_nav_collapsed';
const LEGACY_NAV_COLLAPSE_KEY='cojam_nav_collapsed';
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
try{if((localStorage.getItem(NAV_COLLAPSE_KEY)||localStorage.getItem(LEGACY_NAV_COLLAPSE_KEY))==='1')setNavCollapsed(true)}catch(e){}
document.getElementById('navToggle').onclick=()=>isDesktopNav()?setNavCollapsed(false):document.body.classList.toggle('nav-open');
document.getElementById('navClose').onclick=()=>isDesktopNav()?setNavCollapsed(true):document.body.classList.remove('nav-open');
document.getElementById('navShade').onclick=()=>document.body.classList.remove('nav-open');
document.getElementById('roomList').addEventListener('click',e=>{const add=e.target.closest('[data-project-new]'),edit=e.target.closest('[data-project-edit]'),toggle=e.target.closest('[data-project-toggle]');if(add)openNew(false,add.dataset.projectNew);if(edit){const project=PROJECTS.find(p=>p.id===edit.dataset.projectEdit);if(project)openProject(project)}if(toggle){const id=toggle.dataset.projectToggle;collapsedProjects.has(id)?collapsedProjects.delete(id):collapsedProjects.add(id);drawRooms()}if(e.target.closest('a[data-id]'))document.body.classList.remove('nav-open')});

function bindRoomDrag(list){
  let source=null,highlight=null;
  function mark(project){
    if(highlight===project)return;
    if(highlight)highlight.classList.remove('project-drop-target');
    highlight=project;
    if(highlight)highlight.classList.add('project-drop-target');
  }
  function destination(event){
    const project=event.target.closest('[data-project-drop]');
    return source&&project&&project!==source.project?project:null;
  }
  function endDrag(){
    if(!source)return;
    mark(null);
    source.link.classList.remove('room-drag-source');
    source=null;
    delete list.dataset.dragging;
    drawRooms();
  }
  list.addEventListener('dragstart',event=>{
    const link=event.target.closest('a[data-id][draggable="true"]');
    if(!link)return;
    source={link,project:link.closest('[data-project-drop]')};
    event.dataTransfer.setData('application/x-any-room',link.dataset.id);
    event.dataTransfer.effectAllowed='move';
    list.dataset.dragging='true';
    link.classList.add('room-drag-source');
  });
  list.addEventListener('dragover',event=>{
    const project=destination(event);
    mark(project);
    if(!project)return;
    event.preventDefault();
    event.dataTransfer.dropEffect='move';
  });
  list.addEventListener('dragleave',event=>{
    if(highlight&&!highlight.contains(event.relatedTarget))mark(null);
  });
  list.addEventListener('dragend',endDrag);
  list.addEventListener('drop',async event=>{
    const target=destination(event);
    if(!target)return;
    event.preventDefault();
    const id=source.link.dataset.id,project=target.dataset.projectDrop;
    endDrag();
    const [ok,result]=await post('/api/rooms/move',{id,project});
    if(!ok)return alert(result.error||'移动失败');
    collapsedProjects.delete(project);
    if(typeof RID!=='undefined'&&RID===id&&typeof S!=='undefined'&&S)S.project=project;
    await pollRooms();
  });
}
bindRoomDrag(document.getElementById('roomList'));

const navSearch=document.getElementById('navSearch');
const navSessionsButton=document.getElementById('navSessionsButton'),navContactsButton=document.getElementById('navContactsButton');
function showContactsNav(show){
  document.getElementById('navSessions').hidden=show;
  document.getElementById('contactsSection').hidden=!show;
  navSessionsButton.setAttribute('aria-pressed',String(!show));
  navContactsButton.setAttribute('aria-pressed',String(show));
}
navSessionsButton.onclick=()=>showContactsNav(false);
navContactsButton.onclick=()=>showContactsNav(true);
navSearch.addEventListener('input',drawRooms);
navSearch.addEventListener('keydown',e=>{if(e.key==='Escape'){navSearch.value='';drawRooms();navSearch.blur()}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'&&!document.getElementById('modal').classList.contains('show')){e.preventDefault();if(isDesktopNav())setNavCollapsed(false);else document.body.classList.add('nav-open');showContactsNav(false);navSearch.focus();navSearch.select()}});
if(!/Mac|iPhone|iPad/.test(navigator.platform))document.querySelector('.nav-search kbd').textContent='Ctrl K';

function placeSidebarMenu(menu,x,y){
  if(typeof placeMessageTools==='function')return placeMessageTools(menu,x,y);
  const w=menu.offsetWidth||160,h=menu.offsetHeight||120;
  menu.style.left=Math.max(8,Math.min(x,(typeof innerWidth==='number'?innerWidth:800)-w-8))+'px';
  menu.style.top=Math.max(8,Math.min(y,(typeof innerHeight==='number'?innerHeight:600)-h-8))+'px';
}
function closeSidebarMenu(){
  if(typeof hideMenu==='function')return hideMenu();
  const menu=document.getElementById('cmenu');
  if(menu)menu.classList.remove('on');
}
async function moveRoomToProject(roomId,targetProjectId){
  const room=ROOMS.find(m=>m.id===roomId);
  const currentProject=room?(room.project||legacyProject(room.workdir)):'';
  if(!targetProjectId||targetProjectId===currentProject)return false;
  const [ok,result]=await post('/api/rooms/move',{id:roomId,project:targetProjectId});
  if(!ok){alert((result&&result.error)||'移动失败');return false}
  collapsedProjects.delete(targetProjectId);
  if(typeof RID!=='undefined'&&RID===roomId&&typeof S!=='undefined'&&S)S.project=targetProjectId;
  await pollRooms();
  return true;
}
function bindRoomContextMenu(list){
  if(!list)return;
  list.addEventListener('contextmenu',e=>{
    const link=e.target.closest('a[data-id]');
    const menu=document.getElementById('cmenu');
    if(!link||!menu)return;
    const room=ROOMS.find(m=>m.id===link.dataset.id);
    if(!room)return;
    e.preventDefault();
    menu.innerHTML='';
    const addBtn=(label,fn,disabled=false)=>{
      const b=document.createElement('button');
      b.type='button';b.textContent=label;b.disabled=disabled;
      b.onclick=()=>{closeSidebarMenu();return fn()};
      menu.appendChild(b);
    };
    const curPid=room.project||legacyProject(room.workdir);
    const others=PROJECTS.filter(p=>p.id!==curPid);
    if(others.length){
      const lbl=document.createElement('div');
      lbl.className='cm-label';lbl.textContent='移动到项目';
      menu.appendChild(lbl);
      others.forEach(p=>addBtn('↳ '+p.name,()=>moveRoomToProject(room.id,p.id)));
      const sep=document.createElement('div');sep.className='cm-sep';menu.appendChild(sep);
    }
    if(typeof openRename==='function')addBtn('改名',()=>openRename(room.id,room.title));
    addBtn(room.archived?'取消归档':'归档',async()=>{
      const [ok,res]=await post('/api/rooms/archive',{id:room.id,on:!room.archived});
      if(!ok)return alert((res&&res.error)||'失败');
      if(typeof RID!=='undefined'&&room.id===RID&&typeof loadState==='function')await loadState();
      await pollRooms();
    });
    const busy=!!((room.running&&room.running.length)||room.queued);
    addBtn('删除',async()=>{
      if(!confirm('把「'+room.title+'」移到回收站？（可以恢复）'))return;
      const [ok,res]=await post('/api/rooms/delete',{id:room.id});
      if(!ok)return alert((res&&res.error)||'失败');
      if(typeof RID!=='undefined'&&room.id===RID){
        roomViewGeneration++;RID=null;resetRoomView();
        const params=new URLSearchParams(location.search);params.delete('r');
        history.replaceState({},'',location.pathname+(params.size?'?'+params.toString():''));
        await pickRoom();
      }else{await pollRooms()}
    },busy);
    menu.classList.add('on');
    placeSidebarMenu(menu,e.clientX,e.clientY);
  });
}
bindRoomContextMenu(document.getElementById('roomList'));

const NAV_WIDTH_KEY='any_nav_width';
function applyNavWidth(px){
  const root=document.documentElement;
  if(!root||!root.style)return;
  if(px==null){root.style.removeProperty('--nav-w');return}
  const w=Math.round(Math.min(420,Math.max(220,px)));
  root.style.setProperty('--nav-w',w+'px');
  return w;
}
function initSidebarResize(){
  try{
    const saved=Number(localStorage.getItem(NAV_WIDTH_KEY));
    if(saved>=220&&saved<=420)applyNavWidth(saved);
  }catch(e){}
  const resizer=document.getElementById('navResizer'),nav=document.getElementById('rooms');
  if(!resizer||!nav)return;
  let drag=null;
  resizer.addEventListener('pointerdown',e=>{
    if(!isDesktopNav()||document.body.classList.contains('nav-collapsed')||e.button!==0)return;
    e.preventDefault();
    const rect=nav.getBoundingClientRect();
    drag={startX:e.clientX,startW:rect&&rect.width?rect.width:276,width:rect&&rect.width?rect.width:276};
    document.body.classList.add('nav-resizing');
    if(resizer.setPointerCapture)try{resizer.setPointerCapture(e.pointerId)}catch(err){}
  });
  const onMove=e=>{
    if(!drag)return;
    drag.width=applyNavWidth(drag.startW+(e.clientX-drag.startX));
  };
  const onEnd=()=>{
    if(!drag)return;
    const w=drag.width;drag=null;
    document.body.classList.remove('nav-resizing');
    try{localStorage.setItem(NAV_WIDTH_KEY,String(w))}catch(e){}
  };
  if(typeof addEventListener==='function'){
    addEventListener('pointermove',onMove);
    addEventListener('pointerup',onEnd);
    addEventListener('pointercancel',onEnd);
  }
  resizer.addEventListener('dblclick',()=>{
    applyNavWidth(null);
    try{localStorage.removeItem(NAV_WIDTH_KEY)}catch(e){}
  });
}
initSidebarResize();
