(function(){const m=document.querySelector('meta[name=rt-token]'),t=m?m.content:'';if(!t)return;if(t.startsWith('dev_')){try{localStorage.setItem('cojam_owner_device_token',t)}catch(e){}}const f=window.fetch;window.fetch=function(u,o){o=o||{};const h=new Headers(o.headers||{});h.set('X-RT-Token',t);o.headers=h;return f.call(this,u,o)}})();
// Each owner tab registers separately. A short grace period permits reload and tab handoff.
function ownerTabId(search){
  try{
    const id=new URLSearchParams(search).get('owner_tab')||'';
    return /^[A-Za-z0-9_-]{16,80}$/.test(id)?id:'';
  }catch(e){return ''}
}
// crypto.randomUUID 只在 HTTPS 或 localhost 可用；局域网/Tailscale 的 http 地址需要降级。
function ownerInstance(){
  try{
    const id=crypto.randomUUID().replace(/-/g,'');
    if(/^[A-Za-z0-9_-]{16,80}$/.test(id))return id;
  }catch(e){}
  const bytes=new Uint8Array(16);
  try{crypto.getRandomValues(bytes)}catch(e){for(let i=0;i<16;i++)bytes[i]=Math.floor(Math.random()*256)}
  return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
}
(function(){
  const desktop=ownerTabId(location.search);
  const nativeOwnedHeartbeat=Boolean((typeof window!=='undefined'&&window.cojamDesktop&&window.cojamDesktop.nativeHeartbeat)||(typeof window!=='undefined'&&window.__COJAM_NATIVE_HEARTBEAT__===true));
  const instance=desktop||ownerInstance(), endpoint='/api/ui/session';
  let tab=desktop||instance;
  try{
    if(!desktop){
      const navigation=performance.getEntriesByType('navigation')[0];
      if(navigation&&navigation.type==='reload')tab=sessionStorage.getItem('cojam_owner_tab')||instance;
      sessionStorage.setItem('cojam_owner_tab',tab);
    }
  }catch(e){}
  let exiting=false,timer=0;
  const hasActiveJobs=()=>((typeof lastRun!=='undefined'&&(lastRun.running.length||lastRun.queued))||(typeof ROOMS!=='undefined'&&ROOMS.some(r=>(Array.isArray(r.running)?r.running.length:!!r.running)||r.queued)));
  const report=action=>fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tab,action,instance}),keepalive:true}).catch(()=>{});
  if(!nativeOwnedHeartbeat){
    report('open');
    timer=setInterval(()=>{if(!exiting)report('ping')},30000);
    addEventListener('pageshow',event=>{if(event.persisted&&!exiting)report('open')});
    addEventListener('pagehide',()=>{if(!exiting)report('close')});
  }
  if(!desktop&&!nativeOwnedHeartbeat)addEventListener('beforeunload',event=>{if(!exiting&&hasActiveJobs()){event.preventDefault();event.returnValue=''}});
  document.getElementById('quitApp').onclick=async()=>{
    if(hasActiveJobs()&&!confirm('还有任务正在运行或排队，退出会中断这些任务。确定退出合拍吗？'))return;
    const [ok,j]=await post('/api/server/exit',{});
    if(!ok){alert(j.error||'退出失败');return}
    exiting=true;if(timer)clearInterval(timer);
    document.body.innerHTML='<main class="closed-screen"><img src="/static/logo.svg" width="60" height="60" alt=""><h1>合拍已退出</h1><p>本机服务已停止。需要时重新打开合拍即可。</p><button onclick="window.close()">关闭页面</button></main>';
  };
})();
const feed=document.getElementById('feed'),ta=document.getElementById('ta'),st=document.getElementById('status');
const touch=matchMedia('(pointer:coarse)').matches||('ontouchstart' in window);
let since=0,curMeeting=undefined,S=null;
const msgById={};
// 这个标签页开着的会议（会议号在地址栏 ?r=…；每个标签页可以开不同的会议）
let RID=new URLSearchParams(location.search).get('r')||null;
const api=a=>'/api/r/'+encodeURIComponent(RID||'-')+'/'+a;
if(navigator.serviceWorker&&navigator.serviceWorker.getRegistrations)navigator.serviceWorker.getRegistrations().then(rs=>rs.forEach(r=>r.unregister())).catch(()=>{});
if(window.caches&&caches.keys)caches.keys().then(ks=>ks.forEach(k=>{if(k.startsWith('ai-bridge-'))caches.delete(k)})).catch(()=>{});
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
const modal=document.getElementById('modal'),mbox=document.getElementById('mbox');
let modalReturnFocus=null;
function showModal(html){if(typeof stopAttachmentPreview==='function')stopAttachmentPreview();mbox.classList.remove('file-preview');if(!modal.classList.contains('show'))modalReturnFocus=document.activeElement;mbox.innerHTML=html;modal.classList.add('show');mbox.setAttribute('aria-label',(mbox.querySelector('h3')||mbox.querySelector('.eyebrow')||{textContent:'会话设置'}).textContent);mbox.focus({preventScroll:true});if(typeof connectionModalChanged==='function')connectionModalChanged()}
function hideModal(){const shown=modal.classList.contains('show');modal.classList.remove('show');if(typeof stopAttachmentPreview==='function')stopAttachmentPreview();if(typeof stopConnectionWizard==='function')stopConnectionWizard();if(shown&&modalReturnFocus&&modalReturnFocus.isConnected)modalReturnFocus.focus({preventScroll:true})}
document.addEventListener('keydown',e=>{if(!modal.classList.contains('show'))return;if(e.key==='Escape'){e.preventDefault();hideModal();return}if(e.key!=='Tab')return;const nodes=[...mbox.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href],[tabindex="0"]')].filter(n=>n.getClientRects().length);if(!nodes.length){e.preventDefault();mbox.focus();return}const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&(document.activeElement===first||document.activeElement===mbox)){e.preventDefault();last.focus()}else if(!e.shiftKey&&(document.activeElement===last||document.activeElement===mbox)){e.preventDefault();first.focus()}});
let modalBackdropPress=null,modalBackdropClick=false;
modal.addEventListener('pointerdown',e=>{modalBackdropClick=false;modalBackdropPress=e.target===modal&&e.button===0&&e.isPrimary!==false?{id:e.pointerId,x:e.clientX,y:e.clientY,moved:false}:null});
modal.addEventListener('pointermove',e=>{if(modalBackdropPress&&e.pointerId===modalBackdropPress.id&&Math.hypot(e.clientX-modalBackdropPress.x,e.clientY-modalBackdropPress.y)>5)modalBackdropPress.moved=true});
modal.addEventListener('pointerup',e=>{const p=modalBackdropPress;modalBackdropClick=!!p&&e.pointerId===p.id&&e.target===modal&&!p.moved&&Math.hypot(e.clientX-p.x,e.clientY-p.y)<=5;modalBackdropPress=null});
modal.addEventListener('pointercancel',()=>{modalBackdropPress=null;modalBackdropClick=false});
modal.onclick=e=>{const close=modalBackdropClick&&e.target===modal;modalBackdropClick=false;if(close)hideModal()};
function apiError(status){return status===404?'后台缺少这个功能，可能仍在运行旧版本。请退出旧后台并重新打开合拍 Cojam。':status===403?'页面的连接凭证已失效，请刷新页面后重试。':status>=500?'后台处理失败，请查看应用日志并检查数据目录是否可写。':'请求失败（HTTP '+status+'）'}
async function post(url,obj){let r;try{r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj||{})})}catch(e){return [false,{error:'无法连接合拍 Cojam 后台，请确认应用正在运行。'}]}let j;try{j=await r.json()}catch(e){return [false,{error:apiError(r.status)}]}if(!j||typeof j!=='object')return [false,{error:apiError(r.status)}];if(!r.ok)j.error=r.status===403?apiError(403):(j.error||apiError(r.status));return [r.ok,j]}
function fallbackCopy(t){
  const active=document.activeElement,selection=getSelection();
  const ranges=selection?Array.from({length:selection.rangeCount},(_,i)=>selection.getRangeAt(i).cloneRange()):[];
  const x=document.createElement('textarea');x.value=t;x.setAttribute('aria-label','复制消息');
  x.style.cssText='position:fixed;top:0;left:-9999px';document.body.appendChild(x);x.select();
  let ok=false;try{ok=document.execCommand('copy')}catch(e){}finally{
    x.remove();if(active&&active.focus)active.focus({preventScroll:true});
    if(selection){selection.removeAllRanges();ranges.forEach(r=>selection.addRange(r))}
  }return ok;
}
async function copyText(t){
  if(navigator.clipboard&&window.isSecureContext){try{await navigator.clipboard.writeText(t);return true}catch(e){}}
  return fallbackCopy(t);
}
function seenMap(){try{return JSON.parse(localStorage.getItem('rt_seen')||'{}')}catch(e){return {}}}
function markSeen(rid,n){try{const m=seenMap();if(m[rid]!==n){m[rid]=n;localStorage.setItem('rt_seen',JSON.stringify(m))}}catch(e){}}
