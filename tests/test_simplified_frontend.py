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
 mbox:{querySelectorAll:selector=>selector==='.item'?[row]:[]},post:async()=>[true,{}],confirm:()=>true,alert:message=>{throw Error(message)},
 resetRoomView:()=>reset++,pickRoom:async()=>picked++,pollRooms:async()=>{},closeMeetingTools(){},switchRoom(){}});
vm.runInContext(code,ctx);
(async()=>{await ctx.openList();assert.match(html,/<button type="button" class="db">删除/);await node('.db').onclick({stopPropagation(){}});
 assert.equal(ctx.RID,null);assert.equal(ctx.roomViewGeneration,1);assert.equal(reset,1);assert.equal(picked,1);assert.equal(hidden,1);assert.equal(href,'/?owner_tab=keep');
})().catch(e=>{console.error(e);process.exitCode=1});
''')


if __name__ == '__main__':
    unittest.main()
