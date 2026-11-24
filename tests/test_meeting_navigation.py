"""Regression checks for the meeting toolbar and the formerly unbound details button."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node is required for UI handlers')
class MeetingNavigation(unittest.TestCase):
    def test_toolbar_details_close_and_focus(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const meetingJs=fs.readFileSync('static/app-meeting.js','utf8');
const source=meetingJs.slice(meetingJs.indexOf('const meetingToolsButton='),meetingJs.indexOf('function fmtK('));
const nodes={},events={};let focused='',details=0;
function node(id){return nodes[id]||=(function(){const classes=new Set(),attrs={};return {
 id,style:{},disabled:false,inert:true,
 classList:{add:c=>classes.add(c),remove:c=>classes.delete(c),contains:c=>classes.has(c),toggle(c,on){if(on===undefined)on=!classes.has(c);on?classes.add(c):classes.delete(c);return on}},
 setAttribute:(k,v)=>attrs[k]=v,getAttribute:k=>attrs[k],removeAttribute:k=>delete attrs[k],focus(){focused=id},
 contains:el=>el===nodes[id],querySelector:()=>node('bMode'),querySelectorAll:()=>[],
 getBoundingClientRect:()=>({bottom:60,right:380}),addEventListener:(k,f)=>events[id+':'+k]=f
}})()}
const ctx=vm.createContext({bar:node('bar'),modal:node('modal'),innerHeight:844,innerWidth:390,
 document:{getElementById:node,activeElement:node('menu'),body:node('body'),addEventListener:(k,f)=>events[k]=f},
 addEventListener:(k,f)=>events['window:'+k]=f,drawMeetingDetails:()=>details++,openAi(){}});
vm.runInContext(source,ctx);
const toggle=node('sideToggleBtn');
toggle.onclick();assert.equal(toggle.getAttribute('aria-expanded'),'true');
assert.equal(details,1);assert.equal(node('side').inert,false);assert.ok(node('side').classList.contains('on'));assert.equal(focused,'sideX');
node('sideX').onclick();assert.equal(node('side').inert,true);assert.equal(focused,'sideToggleBtn');
toggle.onclick();toggle.onclick();assert.equal(toggle.getAttribute('aria-expanded'),'false');
toggle.onclick();node('sideBg').onclick();assert.equal(node('side').inert,true);
toggle.onclick();events.keydown({key:'Escape',preventDefault(){}});assert.equal(node('side').inert,true);
"""
        result = subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_waiting_notifications_belong_to_sidebar_and_ignore_current_or_archived(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('static/workspace.js','utf8');
const part=source.slice(source.indexOf('function drawRooms(){'),source.indexOf('// The server supplies'));
const nodes={};function node(id){return nodes[id]||={innerHTML:'',value:'',textContent:'',attrs:{},dataset:{},
 setAttribute(k,v){this.attrs[k]=v},classList:{toggle(k,v){this[k]=v}}}}
const ctx=vm.createContext({PROJECTS:[{id:'project',name:'Project'}],ROOMS:[
 {id:'current',project:'project',title:'Current',waiting:true},
 {id:'waiting',project:'project',title:'Waiting',waiting:true},
 {id:'archived',project:'project',title:'Archived',waiting:true,archived:true}],
 RID:'current',S:{title:'Current'},collapsedProjects:new Set(),roomList:node('roomList'),
 document:{getElementById:node,title:''},drawRoomIdentity(){},roomBadge:m=>m.waiting?['you','等你']:null,
 esc:String,uiIcon:()=>'',legacyProject:()=>''});
vm.runInContext(part,ctx);ctx.drawRooms();
assert.match(node('bList').innerHTML,/管理.*nav-wait.*1/);
assert.match(node('bList').attrs['aria-label'],/1 个其他会话等你回复/);
assert.equal(node('navToggle').classList.attn,true);
assert.match(ctx.document.title,/^\(1\)/);
assert.equal(nodes.menu,undefined,'global waiting state must not affect current meeting tools');
assert.equal((node('roomList').innerHTML.match(/data-project-new=/g)||[]).length,1);
assert.doesNotMatch(node('roomList').innerHTML,/new-conversation/);
ctx.ROOMS[1].waiting=false;ctx.drawRooms();
assert.equal(node('bList').innerHTML,'管理');assert.equal(node('navToggle').classList.attn,false);
assert.doesNotMatch(node('bList').attrs['aria-label'],/等你回复/);
"""
        result = subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


    def test_new_room_does_not_preselect_recommended_contacts(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('static/workspace.js','utf8');
const part=source.slice(source.indexOf('async function openNew('),source.indexOf('function syncMemberPermissionRow('));
const nodes={};let markup='';
const ctx=vm.createContext({PROJECTS:[{id:'project',name:'Project'}],S:null,PERM_GROUPS:[],
 CONTACTS:[{id:'claude',label:'Claude',enabled:true},{id:'codex',label:'Codex',enabled:true}],
 agCat:{default_participants:['claude']},esc:String,
 document:{body:{classList:{remove(){}}},getElementById:id=>nodes[id]||={querySelectorAll:()=>[],focus(){}}},
 async pollRooms(){},async refreshContacts(){},showModal:html=>markup=html,hideModal(){}});
vm.runInContext(part,ctx);
ctx.openNew().then(()=>{
 assert.equal((markup.match(/data-member-check>/g)||[]).length,2);
 assert.doesNotMatch(markup,/data-member-check checked/);
}).catch(error=>{console.error(error);process.exitCode=1});
"""
        result = subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dragging_room_moves_it_to_a_different_project(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('static/workspace.js','utf8');
const part=source.slice(source.indexOf('function bindRoomDrag('),source.indexOf('const navSearch='));
const calls=[],events={},collapsedProjects=new Set(['target']);let polls=0,preventions=0;
const node=dataset=>{const classes=new Set();return {dataset,classes,
 classList:{add:c=>classes.add(c),remove:c=>classes.delete(c)}}};
const list={...node({}),addEventListener:(name,fn)=>events[name]=fn};
const link=node({id:'room'}),origin=node({projectDrop:'origin'}),target=node({projectDrop:'target'});
link.closest=selector=>selector.startsWith('a')?link:origin;
target.closest=()=>target;
const ctx=vm.createContext({document:{getElementById:()=>list},collapsedProjects,drawRooms(){},
 async post(url,body){calls.push([url,JSON.parse(JSON.stringify(body))]);return [true,{}]},
 async pollRooms(){polls++}});
vm.runInContext(part,ctx);
const event=target=>({target,dataTransfer:{setData(){}},preventDefault(){preventions++}});
(async()=>{
 await events.drop(event(target));
 assert.equal(calls.length,0);
 events.dragstart(event(link));
 await events.drop(event(link));
 assert.equal(calls.length,0);
 events.dragover(event(target));
 assert.ok(target.classes.has('project-drop-target'));
 assert.equal(list.dataset.dragging,'true');
 await events.drop(event(target));
 assert.deepEqual(calls,[['/api/rooms/move',{id:'room',project:'target'}]]);
 assert.equal(preventions,2);
 assert.equal(polls,1);
 assert.equal(collapsedProjects.has('target'),false);
 assert.equal(list.dataset.dragging,undefined);
 assert.equal(target.classes.size,0);
 events.dragstart(event(link));
 events.dragover(event(target));
 events.dragend();
 assert.equal(target.classes.size,0);
 assert.equal(link.classes.size,0);
})().catch(error=>{console.error(error);process.exitCode=1});
"""
        result = subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_sidebar_room_context_menu_and_width_resize(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync('static/workspace.js','utf8');
const part=source.slice(source.indexOf('function placeSidebarMenu('));
const calls=[],store=new Map(),winEvents={},resizerEvents={},listEvents={},menuChildren=[];
function makeClassList(){const s=new Set();return {add:c=>s.add(c),remove:c=>s.delete(c),toggle:(c,on)=>on?s.add(c):s.delete(c),contains:c=>s.has(c)}}
const cmenu={style:{},classList:makeClassList(),offsetWidth:160,offsetHeight:120,
 set innerHTML(v){menuChildren.length=0},appendChild:el=>menuChildren.push(el)};
const resizer={addEventListener:(k,fn)=>resizerEvents[k]=fn,setPointerCapture(){}};
const roomsEl={getBoundingClientRect:()=>({width:276})};
const roomList={addEventListener:(k,fn)=>listEvents[k]=fn};
const rootStyle={props:new Map(),setProperty:(k,v)=>rootStyle.props.set(k,v),removeProperty:k=>rootStyle.props.delete(k)};
const ctx=vm.createContext({
  PROJECTS:[{id:'p1',name:'Proj 1'},{id:'p2',name:'Proj 2'}],
  ROOMS:[{id:'r1',project:'p1',title:'Room 1',archived:false,running:[],queued:0}],
  RID:'r1',S:{project:'p1'},collapsedProjects:new Set(['p2']),
  localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},
  document:{
    documentElement:{style:rootStyle},
    body:{classList:makeClassList()},
    createElement:tag=>({tag,type:'',className:'',textContent:'',disabled:false,onclick:null}),
    getElementById:id=>({cmenu,navResizer:resizer,rooms:roomsEl,roomList}[id]||null),
  },
  addEventListener:(k,fn)=>winEvents[k]=fn,
  isDesktopNav:()=>true,
  legacyProject:()=>'',
  alert:m=>{throw Error(m)},
  async post(url,body){calls.push([url,body]);return [true,{}]},
  async pollRooms(){calls.push(['pollRooms'])},
});
vm.runInContext(part,ctx);
const link={dataset:{id:'r1'}};
listEvents.contextmenu({target:{closest:sel=>sel==='a[data-id]'?link:null},clientX:40,clientY:60,preventDefault(){}});
assert.ok(cmenu.classList.contains('on'));
const moveBtn=menuChildren.find(el=>el.textContent==='↳ Proj 2');
assert.ok(moveBtn);
(async()=>{
  await moveBtn.onclick();
  assert.deepEqual(JSON.parse(JSON.stringify(calls)),[['/api/rooms/move',{id:'r1',project:'p2'}],['pollRooms']]);
  assert.equal(ctx.S.project,'p2');
  assert.equal(ctx.collapsedProjects.has('p2'),false);
  resizerEvents.pointerdown({button:0,clientX:276,pointerId:1,preventDefault(){}});
  winEvents.pointermove({clientX:350});
  assert.equal(rootStyle.props.get('--nav-w'),'350px');
  winEvents.pointerup({});
  assert.equal(store.get('any_nav_width'),'350');
  resizerEvents.dblclick();
  assert.equal(rootStyle.props.has('--nav-w'),false);
  assert.equal(store.has('any_nav_width'),false);
})().catch(error=>{console.error(error);process.exitCode=1});
"""
        result = subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_debate_continue_button_visibility_and_submit(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const indexHtml=fs.readFileSync('index.html','utf8');
assert.doesNotMatch(indexHtml,/id="debateContinueBtn"/);
const meetingJs=fs.readFileSync('static/app-meeting.js','utf8');
const part=meetingJs.slice(meetingJs.indexOf('const debateBtn='),meetingJs.indexOf('function syncUndo('));
const nodes={},posts=[];let modalHtml='',modalClosed=0,polled=0;
function node(id){return nodes[id]||={id,hidden:false,disabled:false,textContent:'',title:'',parentElement:null,
 children:[],appendChild(c){c.parentElement=this;this.children.push(c)},
 remove(){if(this.parentElement){this.parentElement.children=this.parentElement.children.filter(x=>x!==this);this.parentElement=null}delete nodes[this.id]},
 classList:{toggle(k,v){this[k]=v}},focus(){},addEventListener(){}}}
const msgNode1=node('msg-1'), msgNode2=node('msg-2'), msgNode3=node('msg-3');
const feed={
 querySelector:sel=>{
  const m=sel.match(/\.msg\[data-id="(\d+)"\]/);
  return m?({1:msgNode1,2:msgNode2,3:msgNode3}[m[1]]||null):null;
 }
};
const formObj={
 elements:{namedItem:name=>({moderator:{value:'claude',innerHTML:''},feedback:{focus(){}}}[name])},
 querySelector:()=>({disabled:false}),
 querySelectorAll:()=>[{value:'codex'},{value:'claude'}],
 onchange:null,onsubmit:null,
};
const ctx=vm.createContext({
 RID:'room1',
 S:{meeting:'room1',participants:['codex','claude'],permissions:{codex:{read:true,post:true},claude:{read:true,post:true}},ais:{codex:{},claude:{}},debate:null},
 msgById:{
  1:{id:1,speaker:'codex',origin:'debate',text:'首轮观点'},
  2:{id:2,speaker:'claude',origin:'debate-summary',text:'论道总结'},
  3:{id:3,speaker:'你',text:'论道之后的普通聊天'},
 },
 feed,
 esc:String,
 agentMeta:id=>({label:id,kind:'agent'}),
 api:p=>'/api/r/room1/'+p,
 poll(){polled++},
 hideModal(){modalClosed++},
 showModal(html){modalHtml=html},
 FormData:function(){return {get:k=>({feedback:'请重点补充边界场景',minimum:'1',maximum:'2'}[k]??'')}},
 document:{
  createElement:tag=>({tagName:tag,id:'',type:'',className:'',textContent:'',title:'',parentElement:null,onclick:null,remove(){if(this.parentElement){this.parentElement.children=this.parentElement.children.filter(x=>x!==this);this.parentElement=null}if(this.id)delete nodes[this.id]}}),
  getElementById:id=>id==='debateContinueForm'?formObj:(nodes[id]||(id==='debateContinueBtn'?null:node(id))),
 },
 async post(url,body){posts.push([url,JSON.parse(JSON.stringify(body))]);return [true,{debate:{topic:'议题',status:'running',completed_rounds:1}}]},
});
const origCreate=ctx.document.createElement;
ctx.document.createElement=tag=>{const el=origCreate(tag);return new Proxy(el,{set(target,prop,val){target[prop]=val;if(prop==='id'&&val)nodes[val]=target;return true}})};
vm.runInContext(part,ctx);
ctx.drawDebate();
assert.equal(ctx.document.getElementById('debateContinueBtn'),null);
ctx.S.debate={topic:'议题',status:'running',completed_rounds:0,participants:['codex','claude'],moderator:'claude'};
ctx.drawDebate();
assert.equal(ctx.document.getElementById('debateContinueBtn'),null);
ctx.S.debate={topic:'议题',status:'completed',completed_rounds:1,participants:['codex','claude'],moderator:'claude'};
ctx.drawDebate();
const btn=ctx.document.getElementById('debateContinueBtn');
assert.ok(btn);
assert.equal(btn.parentElement,msgNode2,'button must attach to last debate message, not post-debate chat or composer');
assert.equal(msgNode3.children.length,0);
btn.onclick();
assert.match(modalHtml,/继续论道/);
assert.match(modalHtml,/已辩 1 轮/);
(async()=>{
 await formObj.onsubmit({preventDefault(){}});
 assert.deepEqual(JSON.parse(JSON.stringify(posts)),[['/api/r/room1/debate/continue',{
  feedback:'请重点补充边界场景',participants:['codex','claude'],min_rounds:1,max_rounds:2,moderator:'claude'
 }]]);
 assert.equal(modalClosed,1);
 assert.equal(polled,1);
 assert.equal(ctx.S.debate.status,'running');
 assert.equal(ctx.document.getElementById('debateContinueBtn'),null);
})().catch(error=>{console.error(error);process.exitCode=1});
"""
        result = subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
