from pathlib import Path
import shutil
import subprocess
import unittest


class UpdateUi(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the update UI test')
    def test_desktop_requests_automatic_install_after_confirmation(self):
        root=Path(__file__).resolve().parents[1]
        code=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={};function node(id){return elements[id]||=({innerHTML:'',disabled:false,classList:{toggle(){}},insertAdjacentHTML(){}})}
let request=null;const ctx=vm.createContext({document:{getElementById:node},esc:String,showModal(){},hideModal(){},confirm:()=>true,
 setTimeout:()=>1,clearTimeout(){},fetch:async()=>({ok:true,json:async()=>({state:'available',current:'2.6.4',latest:'2.6.5',can_install:true})}),
 post:async(url,body)=>{request={url,body};return [true,{state:'downloading'}]}});
vm.runInContext(fs.readFileSync('static/update.js','utf8'),ctx);
(async()=>{node('updateApp').onclick();await new Promise(r=>global.setTimeout(r,10));
 assert.match(node('updateContent').innerHTML,/下载并更新/);await node('updateDownload').onclick();
 assert.equal(request.url,'/api/update/download');assert.equal(request.body.auto_install,true)})().catch(e=>{console.error(e);process.exitCode=1});
'''
        r=subprocess.run(['node','-e',code],cwd=root,capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the update UI test')
    def test_check_and_download_use_internal_api(self):
        root=Path(__file__).resolve().parents[1]
        code=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={};function node(id){return elements[id]||=( {innerHTML:'',disabled:false,classList:{toggle(){}},insertAdjacentHTML(){}} )}
const calls=[],ctx=vm.createContext({document:{getElementById:node},esc:s=>String(s),showModal(){},hideModal(){},
 setTimeout:()=>1,clearTimeout(){},fetch:async url=>{calls.push(url);return {ok:true,json:async()=>({state:'available',current:'2.6.1',latest:'2.6.2',size:3,macos:true})}},
 post:async(url,body)=>{calls.push(url);assert.equal(body.auto_install,undefined);return [true,{state:'downloading',current:'2.6.1',size:3,downloaded:0}]}});
vm.runInContext(fs.readFileSync('static/update.js','utf8'),ctx);
(async()=>{node('updateApp').onclick();await new Promise(resolve=>global.setTimeout(resolve,10));
assert.match(node('updateContent').innerHTML,/2.6.2/);
assert.match(node('updateContent').innerHTML,/下载 macOS ZIP/);
await node('updateDownload').onclick();
assert.ok(calls.includes('/api/update/check'));assert.ok(calls.includes('/api/update/download'));})();
'''
        r=subprocess.run(['node','-e',code],cwd=root,capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for the update UI test')
    def test_update_button_stays_hidden_until_update_is_available(self):
        root=Path(__file__).resolve().parents[1]
        code=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={};
function node(id){
 return elements[id]||=({innerHTML:'',disabled:false,hidden:true,classes:new Set(),
  classList:{toggle(k,v){if(v)this.s.add(k);else this.s.delete(k)},contains(k){return this.s.has(k)},s:null},
  insertAdjacentHTML(){}});
}
const timers=[];
let reply={state:'current',current:'2.8.5',latest:'2.8.5'};
const updateNode=node('updateApp');
updateNode.classList.s=updateNode.classes;
const ctx=vm.createContext({document:{getElementById:node},esc:String,showModal(){},hideModal(){},
 setTimeout:(fn,ms)=>{timers.push([fn,ms]);return timers.length;},clearTimeout(){},
 fetch:async()=>({ok:true,json:async()=>reply}),post:async()=>[true,{}]});
vm.runInContext(fs.readFileSync('static/update.js','utf8'),ctx);
(async()=>{
 assert.equal(updateNode.hidden,true);
 assert.equal(timers[0][1],5000);
 await timers[0][0]();
 assert.equal(updateNode.hidden,true);
 assert.equal(updateNode.classList.contains('has-update'),false);
 reply={state:'error',current:'2.8.5',error:'network'};
 await timers[1][0]();
 assert.equal(updateNode.hidden,true);
 reply={state:'available',current:'2.8.5',latest:'2.8.6',size:100};
 await timers[2][0]();
 assert.equal(updateNode.hidden,false);
 assert.equal(updateNode.classList.contains('has-update'),true);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        r=subprocess.run(['node','-e',code],cwd=root,capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)


if __name__ == '__main__': unittest.main()
