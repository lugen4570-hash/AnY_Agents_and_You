"""Daily settings stay simple and the active conversation can be deleted."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node is needed for UI regression tests')
class SimplifiedFrontend(unittest.TestCase):
    def run_node(self, script):
        result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_contact_opens_summary_and_advanced_requires_explicit_action(self):
        self.run_node(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('static/agent-settings.js','utf8');
const code=source.slice(source.indexOf('async function openAgentSettings('),source.indexOf('async function openAgentAdvancedSettings('));
let html='',advanced=null;const elements={};
const node=id=>elements[id]||=( {value:'My AI',querySelector:sel=>node(sel.slice(1))} );
const ctx=vm.createContext({agentSettingsSequence:0,document:{body:{classList:{remove(){}}},getElementById:id=>html.includes('id="'+id+'"')?node(id):null},
 stopConnectionWizard(){},showModal:value=>html=value,connectionGet:async()=>[true,{id:'demo',driver:'cli',values:{label:'My AI'},connection:{label:'程序可启动'}}],
 esc:String,agentInput:()=>'<input id="agentSummaryName">',hideModal(){},openAgentAdvancedSettings:id=>advanced=id});
vm.runInContext(code,ctx);
(async()=>{await ctx.openAgentSettings('demo');assert.match(html,/id="agentSummary"/);assert.equal((html.match(/<input/g)||[]).length,1);
 assert.doesNotMatch(html,/data-agent-tab|data-agent-list|MCP|启动参数|协议类型/);
 assert.equal(advanced,null);node('agentSummaryAdvanced').onclick();assert.equal(advanced,'demo');
})().catch(e=>{console.error(e);process.exitCode=1});
''')

    def test_deleting_current_room_resets_view_and_picks_replacement(self):
        self.run_node(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('static/app-meeting.js','utf8');
const code=source.slice(source.indexOf('async function openList('),source.indexOf('function openAi('));
const buttons={},node=id=>buttons[id]||={style:{},dataset:{},textContent:'Current'};let html='',reset=0,picked=0,hidden=0,href='';
const row={dataset:{id:'current'},querySelector:selector=>node(selector),closest:()=>null};
const ctx=vm.createContext({RID:'current',roomViewGeneration:0,URLSearchParams,location:{search:'?r=current&owner_tab=keep',pathname:'/'},
 history:{replaceState:(a,b,url)=>href=url},fetch:async url=>({json:async()=>url==='/api/rooms'?{rooms:[{id:'current',title:'Current',created:'2026-11-15',running:[],queued:0}]}:{trash:[]}}),
 roomBadge:()=>null,esc:String,showModal:value=>html=value,hideModal:()=>hidden++,document:{getElementById:id=>node(id)},
 mbox:{querySelectorAll:selector=>selector==='.item'||selector==='.item[data-id]'?[row]:[]},post:async()=>[true,{}],confirm:()=>true,alert:message=>{throw Error(message)},
 resetRoomView:()=>reset++,pickRoom:async()=>picked++,pollRooms:async()=>{},closeMeetingTools(){},switchRoom(){}});
vm.runInContext(code,ctx);
(async()=>{await ctx.openList();assert.match(html,/<button type="button" class="db">删除/);await node('.db').onclick({stopPropagation(){}});
 assert.equal(ctx.RID,null);assert.equal(ctx.roomViewGeneration,1);assert.equal(reset,1);assert.equal(picked,1);assert.equal(hidden,1);assert.equal(href,'/?owner_tab=keep');
})().catch(e=>{console.error(e);process.exitCode=1});
''')

    def test_secondary_modals_support_back_navigation(self):
        self.run_node(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const coreJs=fs.readFileSync('static/app-core.js','utf8');
const agentJs=fs.readFileSync('static/agent-settings.js','utf8');
const connJs=fs.readFileSync('static/connections.js','utf8');
const modelJs=fs.readFileSync('static/model-settings.js','utf8');
const wsJs=fs.readFileSync('static/workspace.js','utf8');
const meetJs=fs.readFileSync('static/app-meeting.js','utf8');
const execJs=fs.readFileSync('static/execution-settings.js','utf8');
const harnessJs=fs.readFileSync('static/harness-ui.js','utf8');

function makeNode(id){
  const classes=new Set(), attrs={}, listeners={};
  return {
    id, value:'', hidden:false, disabled:false, style:{}, dataset:{}, innerHTML:'', textContent:'',
    isConnected:true, checked:false, children:[],
    classList:{
      add:c=>classes.add(c), remove:c=>classes.delete(c), contains:c=>classes.has(c),
      toggle:(c,on)=>{if(on===undefined)on=!classes.has(c);on?classes.add(c):classes.delete(c);return on}
    },
    setAttribute:(k,v)=>attrs[k]=String(v),
    getAttribute:k=>attrs[k],
    addEventListener:(k,fn)=>listeners[k]=fn,
    appendChild(child){this.children.push(child);this.innerHTML+=(child.innerHTML||'');return child},
    parentElement:{after(){}},
    focus(){}, select(){}, click(){if(this.onclick)this.onclick()},
    closest:sel=>sel==='#appSettingsModal'&&hasId('appSettingsModal')?getNode('appSettingsModal'):null,
    querySelector:sel=>sel.startsWith('#')?getNode(sel.slice(1)):getNode('__sel:'+sel),
    querySelectorAll:sel=>{const m=sel.match(/^\[([a-z-]+)\]$/);return m?extractDataNodes(m[1]):[];},
  };
}
const pageNodes={}, pageIds=new Set(['modal','mbox','ta','feed','quick','slashMenu','composerPopover','composerBar','composerModeBtn','composerModelBtn','composerExtBtn','composerTargetHint','openSettingsBtn','side','sideTabs','sideAgentsPane']);
let nodes={}, modalHtml='';
function getNode(id){
  const n=pageIds.has(id)?(pageNodes[id]||=makeNode(id)):(nodes[id]||=makeNode(id));
  if(id==='connectionWizard'){const m=modalHtml.match(/id="connectionWizard"[^>]*data-flow="([^"]+)"/);if(m)n.dataset.flow=m[1];}
  return n;
}
function resetNodes(html){
  nodes={};
  modalHtml=html;
}
function combinedHtml(){
  return [modalHtml,nodes.agentJoinedRooms?.innerHTML,nodes.settingsBody?.innerHTML].filter(Boolean).join('\n');
}
function hasId(id){return combinedHtml().includes('id="'+id+'"')}
function extractDataNodes(attr){
  const re=new RegExp(attr+'="([^"]+)"','g'), out=[], src=combinedHtml();
  let m; while((m=re.exec(src))!==null){
    const key=attr+':'+m[1];
    const n=getNode(key);
    const camel=attr.replace(/^data-/,'').replace(/-([a-z])/g,(_,c)=>c.toUpperCase());
    n.dataset[camel]=m[1];
    out.push(n);
  }
  return out;
}

const modal=getNode('modal'), mbox=getNode('mbox');
mbox.querySelector=sel=>{
  if(sel.startsWith('#'))return hasId(sel.slice(1))?getNode(sel.slice(1)):null;
  const m=sel.match(/^\[([a-z-]+)="([^"]+)"\]$/);
  if(m){const list=extractDataNodes(m[1]);return list.find(n=>Object.values(n.dataset).includes(m[2]))||null}
  return null;
};
mbox.querySelectorAll=sel=>{
  const m=sel.match(/^\[([a-z-]+)\]$/);
  if(m)return extractDataNodes(m[1]);
  return [];
};

const doc={
  documentElement:{dataset:{},lang:'zh-CN'},
  body:makeNode('body'),
  activeElement:null,
  getElementById:id=>{
    if(['modal','mbox','ta','feed','quick','slashMenu','composerPopover','composerBar','composerModeBtn','composerModelBtn','composerExtBtn','composerTargetHint','openSettingsBtn','side','sideTabs','sideAgentsPane'].includes(id))return getNode(id);
    return hasId(id)?getNode(id):null;
  },
  querySelector:sel=>sel.startsWith('#')?(hasId(sel.slice(1))?getNode(sel.slice(1)):null):null,
  querySelectorAll:sel=>{
    if(sel.startsWith('[data-')){
      const attr=sel.replace(/[\[\]]/g,'');
      return extractDataNodes(attr);
    }
    return [];
  },
  createElement:()=>makeNode('dyn'),
  addEventListener(){},
};

const contacts=[{id:'demo',label:'Demo',driver:'cli',enabled:true,color:'#10a37f',letter:'D',default:['m1',''],default_permissions:{read:true,post:true,trigger:true,board:false,files:false,work:false}}];
const projects=[{id:'p1',name:'Proj 1',workdir:'D:/proj1',workdirs:['D:/proj1']},{id:'p2',name:'Proj 2',workdir:'D:/proj2',workdirs:['D:/proj2']}];
const rooms=[{id:'r1',project:'p1',title:'Room 1',created:'2026-11-25 10:00',archived:false,running:[],queued:0,participants:['demo']}];
const agentConfig={id:'demo',driver:'cli',enabled:true,revision:1,values:{label:'Demo',bin:['demo'],args:{base:[]},desktop:{},default:['m1',''],models:['m1'],efforts:['low','high'],model_efforts:{},default_permissions:{}},connection:{label:'已验证',has_key:false},capabilities:{models:['m1']},hosts:[]};

const ctx=vm.createContext({
  URL, FormData:function(){return {get:()=>''}}, AbortController, setTimeout, clearTimeout, setInterval, clearInterval, navigator:{language:'zh-CN'}, location:{origin:'http://127.0.0.1:8765',search:'?r=r1',pathname:'/'},
  localStorage:{getItem:()=>null,setItem(){}},
  esc:v=>String(v??''),
  document:doc,
  modal, mbox, feed:makeNode('feed'),
  RID:'r1',
  S:{meeting:'r1',project:'p1',title:'Room 1',participants:['demo'],permissions:{demo:{read:true,post:true,trigger:true,work:false}},agents:contacts,ais:{demo:{model:{models:['m1'],efforts:['low','high'],model:'',effort:''},execution:{endpoint:'cli',label:'CLI'}}},execution:{demo:{endpoint:'cli',label:'CLI',handoff_supported:false}}},
  CONTACTS:contacts, PROJECTS:projects, ROOMS:rooms,
  agCat:{local_workspace:true,agents:contacts,connections:{demo:{state:'ready',label:'已验证'}},members:{},hosts:[]},
  AG_DRV:{cli:'CLI',http:'HTTP',external:'External'},
  PERM_LABELS:{read:'读取',post:'发言',trigger:'触发',board:'看板',files:'文件',work:'干活'},
  PERM_GROUPS:[{id:'chat',label:'参与对话',hint:'',keys:['read','post','trigger'],defaults:true}],
  HUMAN_ROOM_PERM_GROUPS:[{id:'read',label:'读消息',hint:'',keys:['read'],defaults:true}],
  groupPermValue:()=>true,
  memberPermissionRow:(a,sel,p,s,ed)=>'<div data-member="'+a.id+'">'+(ed?'<button data-contact-policy="'+a.id+'"></button>':'')+'</div>',
  syncMemberPermissionRow(){},
  readMemberPermissions:()=>({participants:['demo'],permissions:{}}),
  agentMeta:id=>contacts.find(c=>c.id===id)||{},
  contactStatusLabel:()=>'已验证',
  contactChannelLabel:()=>'本机程序',
  uiIcon:()=>'',
  roomBadge:()=>null,
  api:p=>'/api/r/r1/'+p,
  setMeetingSide(){},
  attachWorkspaceFolderPicker(){},
  confirm:()=>true, alert:m=>{throw Error(m)}, loadTools:async()=>{},
  poll:async()=>{}, loadState:async()=>{}, pollRooms:async()=>{}, refreshContacts:async()=>{},
  fetch:async url=>{
    if(url==='/api/server/info')return {ok:true,json:async()=>({app:'AI Bridge',version:'2.8.42',api_revision:3,lan_url:'http://192.168.1.5:8766'})};
    if(url==='/api/rooms')return {ok:true,json:async()=>({projects,rooms})};
    if(url==='/api/trash')return {ok:true,json:async()=>({trash:[]})};
    if(url==='/api/settings/connection')return {ok:true,json:async()=>({global:{heartbeat_interval:10},contacts:{},fields:{heartbeat_interval:{label:'心跳间隔',min:3,max:120,default:10}}})};
    if(url.startsWith('/api/agents/config'))return {ok:true,json:async()=>agentConfig};
    if(url.startsWith('/api/r/r1/state'))return {ok:true,json:async()=>({meeting:'r1',title:'Room 1',participants:['demo'],permissions:{demo:{read:true,post:true}}})};
    if(url.startsWith('/api/r/r1/tools'))return {ok:true,json:async()=>({mcp:[],plugins:[],skills:[]})};
    if(url.startsWith('/api/extensions'))return {ok:true,json:async()=>({skill_roots:[],items:[]})};
    if(url.startsWith('/api/update/'))return {ok:true,json:async()=>({current:'2.8.42',latest:'2.8.42',state:'current'})};
    return {ok:true,json:async()=>({})};
  },
  post:async url=>{
    if(url==='/api/discovery/scan')return [true,{detected:[{id:'demo',label:'Demo',level:'direct',via:'cli',connected:true}]}];
    if(url==='/api/discovery/prepare')return [true,{id:'demo',tab:'cli'}];
    if(url==='/api/agents/config')return [true,{config:agentConfig}];
    return [true,{}];
  },
});

const modalCore=coreJs.slice(coreJs.indexOf('const modal=document.getElementById'),coreJs.indexOf('function apiError('));
vm.runInContext('this.window = this; this.addEventListener = () => {};',ctx);
vm.runInContext(modalCore,ctx);
const origShow=ctx.showModal, origHide=ctx.hideModal;
ctx.showModal=html=>{resetNodes(html);return origShow(html)};
ctx.hideModal=()=>{resetNodes('');return origHide()};

vm.runInContext(agentJs,ctx);
vm.runInContext(connJs,ctx);
vm.runInContext(modelJs,ctx);
vm.runInContext(execJs,ctx);
vm.runInContext(wsJs.slice(wsJs.indexOf('async function openProject('),wsJs.indexOf('document.getElementById(\'contactsAdd\')')),ctx);
vm.runInContext(meetJs.slice(meetJs.indexOf('function openRename('),meetJs.indexOf('document.getElementById(\'bRename\')')),ctx);
vm.runInContext(meetJs.slice(meetJs.indexOf('function openMoveRoom('),meetJs.indexOf('document.getElementById(\'bList\')')),ctx);
vm.runInContext(harnessJs,ctx);

(async()=>{
  // 1. Settings -> Agent Manager -> Discovery -> Agent Summary -> Agent Advanced -> Agent Membership -> Back all the way!
  ctx.openAppSettings('agents');
  assert.equal(ctx.hasModalBack(),false);
  assert.equal(hasId('settingsBackBtn'),false);

  getNode('settingsOpenManager').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('agentManagerBack'), 'Agent Manager opened from Settings must have Back button');

  getNode('contactsScan').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('discBack'), 'Discovery opened from Agent Manager must have Back button');

  await extractDataNodes('data-disc-config')[0].onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('agentSummaryBack'), 'Agent Summary opened from Discovery must have Back button');

  getNode('agentSummaryAdvanced').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('agentSettingsBack'), 'Agent Advanced must have Back button');

  await extractDataNodes('data-agent-room')[0].onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('agentMembershipTopBack'), 'Agent Membership must have top Back button, got: '+modalHtml);

  // Walk all the way back step by step
  getNode('agentMembershipTopBack').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('agentSettings'), 'Back from Membership returns to Agent Advanced');

  getNode('agentSettingsBack').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('agentSummary'), 'Back from Agent Advanced returns to Agent Summary');
  assert.ok(hasId('agentSummaryBack'), 'Agent Summary still keeps Back button to Discovery');

  getNode('agentSummaryBack').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('discoveryModal'), 'Back from Agent Summary returns to Discovery');
  assert.ok(hasId('discBack'), 'Discovery still keeps Back button to Agent Manager');

  getNode('discBack').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('agentManager'), 'Back from Discovery returns to Agent Manager');
  assert.ok(hasId('agentManagerBack'), 'Agent Manager still keeps Back button to Settings');

  getNode('agentManagerBack').onclick();
  assert.ok(hasId('appSettingsModal'), 'Back from Agent Manager returns to Settings');
  assert.equal(ctx.hasModalBack(),false);

  // 2. Agent Manager -> Heartbeat settings -> Back returns to Agent Manager
  getNode('settingsOpenManager').onclick();
  await new Promise(r=>setTimeout(r,15));
  getNode('connSettingsBtn').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('hbBack'), 'Connection settings opened from Agent Manager must have Back button');
  getNode('hbBack').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('agentManager'), 'Back from Connection settings returns to Agent Manager');
  ctx.hideModal();
  assert.equal(ctx.hasModalBack(),false);

  // 3. openAi -> Agent Settings -> Back returns to openAi
  ctx.openAi('demo');
  assert.equal(hasId('aBack'),false);
  getNode('executionAgentSettings').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('agentSummaryBack'), 'Agent Summary opened from openAi must have Back button');
  getNode('agentSummaryBack').onclick();
  assert.ok(hasId('modelSettings'), 'Back from Agent Summary returns to openAi');
  ctx.hideModal();

  // 4. openList -> Project Settings / Rename -> Back / Cancel returns to openList
  await ctx.openList();
  assert.equal(hasId('lBack'),false);
  await extractDataNodes('data-project-edit')[0].onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('pBack'), 'Project Settings opened from openList must have Back button');
  getNode('pCancel').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.match(modalHtml,/项目与会话管理/, 'Cancel in Project Settings returns to openList');
  ctx.hideModal();

  // 5. composerExtBtn (openSlashSkillsModal) -> Global Extensions -> Back returns to openSlashSkillsModal
  getNode('composerExtBtn').onclick();
  assert.ok(hasId('slashSkillsModal'));
  assert.equal(hasId('skillsBackBtn'),false);
  getNode('skillsOpenExt').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('settingsBackBtn'), 'Global Settings opened from Slash Skills must have Back button');
  getNode('settingsBackBtn').onclick();
  assert.ok(hasId('slashSkillsModal'), 'Back from Global Settings returns to Slash Skills modal');
  ctx.hideModal();

  // 6. Connection Wizard opened from Settings -> Back returns to Settings
  ctx.openAppSettings('agents');
  getNode('settingsAddAgent').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('connWizardBack'), 'Connection wizard opened from Settings must have Back button, got: '+modalHtml);
  getNode('connWizardBack').onclick();
  assert.ok(hasId('appSettingsModal'), 'Back from Connection wizard returns to Settings');
  ctx.hideModal();

  // 7. openAppSettings tutorial -> manage members (openAgents) -> contactPolicy -> Back -> Back to tutorial
  ctx.openAppSettings('tutorial');
  const manageBtn=extractDataNodes('data-onboard-action').find(n=>n.dataset.onboardAction==='manage');
  assert.ok(manageBtn,'Tutorial must render manage members button');
  await getNode('settingsBody').children[0].onclick({target:{closest:sel=>sel==='[data-onboard-action]'?manageBtn:null}});
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('mHeaderBack'), 'openAgents opened from Settings tutorial must have Back button');
  extractDataNodes('data-contact-policy')[0].onclick();
  assert.ok(hasId('contactPolicyTopBack'), 'openContactPolicy must have top Back button');
  getNode('contactPolicyTopBack').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('memberRows'), 'Back from openContactPolicy returns to openAgents');
  getNode('mHeaderBack').onclick();
  assert.ok(hasId('appSettingsModal'), 'Back from openAgents returns to Settings tutorial');
  ctx.hideModal();

  // 8. Root openAgentSettings has NO Back button
  await ctx.openAgentSettings('demo');
  assert.equal(hasId('agentSummaryBack'),false, 'Root Agent Summary must not show Back button');
  ctx.hideModal();

  // Test the real entry points and the entire back path without awaiting a request.
  contacts.push({id:'devin',label:'Devin',driver:'external',kind:'ai',enabled:true});
  ctx.agCat.discovered_presets = [
    {id:'second',label:'Second CLI',driver:'acp',enabled:true},
    {id:'qoder',label:'Qoder',driver:'external',kind:'ai',enabled:true},
  ];
  const choose = type => mbox.querySelector('[data-connection-type="'+type+'"]').onclick();
  const back = () => getNode('connWizardBack').onclick();
  await ctx.startConnectionWizard();
  assert.match(modalHtml, /用户接入.*Harness 接入/);
  assert.doesNotMatch(modalHtml, /我的设备/);
  choose('user');
  assert.ok(hasId('connGuestGenerate'));
  back();
  choose('harness');
  assert.doesNotMatch(modalHtml, /高级设置/);
  choose('local');
  choose('cli');
  assert.ok(hasId('connCheck'));
  assert.match(modalHtml, /Demo.*Second CLI.*手动添加 CLI 或 ACP 程序/);
  assert.doesNotMatch(modalHtml, /配置 Devin|配置 Qoder|connOpenScan|<select id="connLocal"/);
  back();
  assert.match(modalHtml, /CLI 端.*桌面端/);
  choose('desktop');
  assert.ok(hasId('connDesktopScan'));
  extractDataNodes('data-conn-program').find(n=>n.dataset.connProgram==='__custom__').onclick();
  assert.match(modalHtml, /本机 Harness · 桌面端/);
  assert.match(modalHtml, /\/mcp\.html/);
  back();
  back();
  back();
  choose('external');
  assert.ok(hasId('connRemoteBase'));
  getNode('connRemoteBase').value = 'http://127.0.0.1:8765';
  getNode('connRemoteBase').oninput();
  getNode('connDeviceNext').onclick();
  assert.ok(hasId('connRemoteBase'), 'Remote setup must reject a loopback address');
  getNode('connRemoteBase').value = 'https://any.example.test';
  getNode('connRemoteBase').oninput();
  getNode('connDeviceNext').onclick();
  choose('cli');
  assert.match(modalHtml, /https:\/\/any\.example\.test/);
  assert.match(modalHtml, /生成成员连接配置/);
  assert.doesNotMatch(modalHtml, /Second CLI|\/mcp\.html/);
  back();
  choose('desktop');
  assert.match(modalHtml, /其他设备上的 Harness · 桌面端/);
  assert.match(modalHtml, /生成 MCP 接入密钥/);
  ctx.hideModal();

  ctx.openAppSettings('personal');
  getNode('settingsPersonalDevices').onclick();
  await new Promise(r=>setTimeout(r,15));
  assert.ok(hasId('connDeviceCreate'), 'Personal Settings opens device management');
  back();
  assert.ok(hasId('settingsPersonalDevices'), 'Return reopens Personal Settings');
  ctx.hideModal();
})().catch(e=>{console.error(e);process.exitCode=1});
''')


if __name__ == '__main__':
    unittest.main()
