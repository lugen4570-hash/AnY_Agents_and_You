function render(t,md){
  const parts=t.split('```');let h='';
  parts.forEach((p,i)=>{
    if(i%2){h+='<pre>'+esc(p.replace(/^[^\n]*\n/,''))+'</pre>'}
    else h+=md?mdBlock(p):esc(p);
  });
  return h;
}
// 简易 markdown：先转义再套标签，只出现下面写死的几种标签；链接只认 http(s)
function mdInline(s){
  const hold=[];
  const keep=h=>{hold.push(h);return '\u0000'+(hold.length-1)+'\u0000'};
  s=s.replace(/`([^`\n]+)`/g,(_,c)=>keep('<code>'+esc(c)+'</code>'));
  s=s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g,(_,tx,u)=>keep('<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(tx)+'</a>'));
  s=s.replace(/(^|[^"\w\u0000])(https?:\/\/[^\s<>\u0000]+?)([.,;:!?)）。，；：！？]*(?:\s|$))/g,(_,a,u,z)=>a+keep('<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(u)+'</a>')+z);
  s=esc(s);
  s=s.replace(/\*\*([^*\n]+?)\*\*/g,'<strong>$1</strong>').replace(/~~([^~\n]+?)~~/g,'<del>$1</del>');
  s=s.replace(/(^|[^*\w])\*([^*\s][^*\n]*?)\*(?![*\w])/g,'$1<em>$2</em>');
  return s.replace(/\u0000(\d+)\u0000/g,(_,n)=>hold[+n]);
}
function mdBlock(t){
  const L=t.replace(/\r/g,'').split('\n');let h='',i=0;const para=[];
  const flush=()=>{if(para.length){h+='<p>'+para.map(mdInline).join('<br>')+'</p>';para.length=0}};
  const cells=r=>r.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(c=>c.trim());
  const isRow=l=>/^\s*\|.*\|\s*$/.test(l);
  const isSep=l=>/^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l)&&l.indexOf('-')>=0;
  const LI=/^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
  while(i<L.length){
    const l=L[i];let m;
    if(!l.trim()){flush();i++;continue}
    if(m=l.match(/^(#{1,6})\s+(.*)$/)){flush();const n=Math.min(m[1].length+2,6);h+='<h'+n+'>'+mdInline(m[2])+'</h'+n+'>';i++;continue}
    if(/^\s*([-*_])(\s*\1){2,}\s*$/.test(l)){flush();h+='<hr>';i++;continue}
    if(/^\s*>/.test(l)){flush();const q=[];while(i<L.length&&/^\s*>/.test(L[i])){q.push(L[i].replace(/^\s*>\s?/,''));i++}h+='<blockquote>'+mdBlock(q.join('\n'))+'</blockquote>';continue}
    if(isRow(l)&&i+1<L.length&&isSep(L[i+1])){
      flush();const hd=cells(l);i+=2;let b='';
      while(i<L.length&&isRow(L[i])){b+='<tr>'+cells(L[i]).map(c=>'<td>'+mdInline(c)+'</td>').join('')+'</tr>';i++}
      h+='<div class="tbl"><table><thead><tr>'+hd.map(c=>'<th>'+mdInline(c)+'</th>').join('')+'</tr></thead><tbody>'+b+'</tbody></table></div>';continue;
    }
    if(m=l.match(LI)){
      flush();const items=[];
      while(i<L.length){
        const x=L[i].match(LI);
        if(x){items.push({ind:x[1].replace(/\t/g,'    ').length,ol:/\d/.test(x[2]),text:x[3]});i++}
        else if(L[i].trim()&&/^\s+/.test(L[i])&&items.length){items[items.length-1].text+='\n'+L[i].trim();i++}
        else if(!L[i].trim()&&i+1<L.length&&LI.test(L[i+1])){i++}
        else break;
      }
      let o='';const st=[];
      for(const it of items){
        while(st.length&&it.ind<st[st.length-1].ind)o+='</li></'+st.pop().tag+'>';
        const top=st[st.length-1];
        const tag=it.ol?'ol':'ul';
        if(!top||it.ind>top.ind){o+='<'+tag+'><li>';st.push({ind:it.ind,tag})}
        else if(top.tag!==tag){o+='</li></'+top.tag+'><'+tag+'><li>';top.tag=tag}   // 同级换了类型（无序 → 有序）另起一个列表
        else o+='</li><li>';
        o+=it.text.split('\n').map(mdInline).join('<br>');
      }
      while(st.length)o+='</li></'+st.pop().tag+'>';
      h+=o;continue;
    }
    para.push(l);i++;
  }
  flush();return h;
}
function fmtSize(n){return n>1048576?(n/1048576).toFixed(1)+' MB':Math.max(1,Math.round(n/1024))+' KB'}
function attHtml(list){
  if(!list||!list.length)return '';
  return '<div class="atts">'+list.map(a=>{
    const u=esc(a.url||''),n=esc(a.name);
    if(a.kind==='image')return '<a class="img" href="'+u+'" data-name="'+n+'" target="_blank" rel="noopener"><img src="'+u+'" alt="'+n+'" loading="lazy"></a>';
    if(a.kind==='audio')return '<audio controls preload="none" src="'+u+'"></audio>';
    return '<span class="file-actions"><a class="file" href="'+u+'" data-name="'+n+'" title="预览文件">'+n+' · '+fmtSize(a.size)+'</a><a class="file-download" href="'+u+'" download="'+n+'" aria-label="下载 '+n+'">下载</a></span>';
  }).join('')+'</div>';
}
function add(m){
  const d=document.createElement('div');
  const cls=m.speaker==='你'?'me':isAgent(m.speaker)?'ai':'sys';
  d.className='msg '+cls+(m.to_user?' touser':'')+(m.step!=null?' step':'');
  if(cls==='ai'){d.style.setProperty('--c',agentColor(m.speaker));d.dataset.l=agentLetter(m.speaker)}
  const tag=m.to_user?'<span class="tag">→ 用户</span>':'';
  const who=cls==='sys'?'':'<div class="who"><span class="nm">'+esc((agentMeta(m.speaker)||{}).label||m.speaker)+'</span><span class="tm">'+esc(m.time)+'</span>'+tag+'<span class="message-actions"><button type="button" class="mc" title="复制消息文字">复制</button><button type="button" class="rp" title="选中文字可引用片段">引用</button></span></div>';
  const q=m.reply_to?'<div class="qt" data-to="'+m.reply_to.id+'">'+esc(m.reply_to.speaker)+'：'+(m.reply_to.part?'“'+esc(m.reply_to.text)+'”':esc(m.reply_to.text))+'</div>':'';
  d.dataset.id=m.id;msgById[m.id]=m;
  const md=cls==='ai';
  d.innerHTML=who+q+(m.text?'<div class="body'+(md?' md':'')+'">'+render(m.text,md)+'</div>':'')+attHtml(m.attachments)+(m.step!=null?'<button type="button" class="undo" data-step="'+m.step+'">撤回这一步</button>':'');
  feed.appendChild(d);
  const ub=d.querySelector('.undo');if(ub)ub.onclick=()=>undoStep(m.step);
  d.querySelectorAll('.message-actions button').forEach(b=>b.onmousedown=e=>e.preventDefault());
  const rb=d.querySelector('.rp');if(rb)rb.onclick=()=>{const selected=selIn();setQuote(m,selected&&selected.id===m.id?selected.text:'')};
  const cb=d.querySelector('.mc');if(cb)cb.onclick=()=>copyMessageText(m.text||'');
  const qb=d.querySelector('.qt');if(qb)qb.onclick=()=>{const o=feed.querySelector('.msg[data-id="'+qb.dataset.to+'"]');if(o){o.scrollIntoView({block:'center',behavior:'smooth'});o.classList.add('flash');setTimeout(()=>o.classList.remove('flash'),1200)}};
}
let attachmentPreviewController=null;
function stopAttachmentPreview(){
  if(attachmentPreviewController)attachmentPreviewController.abort();
  attachmentPreviewController=null;
  const frame=mbox.querySelector('iframe.attachment-frame');if(frame)frame.remove();
}
async function attachmentHtml(text,file,controller){
  const doc=new DOMParser().parseFromString(text,'text/html'),base=doc.createElement('base'),directory=new URL('.',file);
  base.href=directory.href;doc.head.prepend(base);
  // Sandboxed HTML has no owner cookies. Fetch its sibling assets here, without
  // giving the document access to the meeting's origin or authentication token.
  let total=0;
  for(const node of doc.querySelectorAll('img[src],script[src],link[rel~="stylesheet"][href],audio[src],video[src],source[src]')){
    const attr=node.hasAttribute('src')?'src':'href',value=node.getAttribute(attr);
    if(!value||/^(data:|blob:|#)/i.test(value))continue;
    const resource=new URL(value,directory),decoded=decodeURIComponent(resource.pathname);
    if(resource.origin!==file.origin||!resource.pathname.startsWith(directory.pathname)||decoded.includes('\\')||decoded.split('/').some(p=>p==='..'||p==='.'))continue;
    const response=await fetch(resource.href,{signal:controller.signal});if(!response.ok)continue;
    if(Number(response.headers.get('Content-Length'))+total>8*1024*1024)throw Error('页面引用的附件超过 8 MB，请下载后打开。');
    const blob=await response.blob();total+=blob.size;
    if(total>8*1024*1024)throw Error('页面引用的附件超过 8 MB，请下载后打开。');
    if(controller.signal.aborted)throw new DOMException('Preview closed','AbortError');
    const url=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('附件资源读取失败。'));reader.readAsDataURL(blob)});
    if(controller.signal.aborted)throw new DOMException('Preview closed','AbortError');
    node.setAttribute(attr,url);
  }
  return '<!doctype html>'+doc.documentElement.outerHTML;
}
function attachmentPreviewType(name){
  const ext=(String(name).split('.').pop()||'').toLowerCase();
  if(['html','htm'].includes(ext))return 'html';
  if(ext==='pdf')return 'pdf';
  if(['txt','md','markdown','json','csv','tsv','log','yaml','yml','xml','svg','css','js','ts','py','sh','toml','ini','sql'].includes(ext))return 'text';
  return '';
}
async function openAttachment(url,name){
  const file=new URL(url,location.origin);
  if(file.origin!==location.origin||!file.pathname.startsWith('/files/')){alert('附件地址无效，请刷新会话后重试。');return}
  showModal('<div class="attachment-heading"><h3>'+esc(name)+'</h3><div><a class="attachment-download" href="'+esc(file.href)+'" download="'+esc(name)+'">下载</a><button type="button" onclick="hideModal()">关闭</button></div></div><p id="attachmentStatus" class="hint" role="status">正在打开文件…</p><div id="attachmentContent"></div>');
  mbox.classList.add('file-preview');
  const content=document.getElementById('attachmentContent'),status=document.getElementById('attachmentStatus');
  const type=attachmentPreviewType(name),controller=new AbortController();attachmentPreviewController=controller;
  if(!type){status.textContent='此格式暂不支持内嵌预览，请下载后用系统应用打开。';return}
  try{
    if(type==='pdf'){
      const frame=document.createElement('iframe');frame.className='attachment-frame';frame.title=name;frame.src=file.href;
      content.appendChild(frame);status.textContent='PDF 预览；若设备不支持显示，可使用上方下载。';return;
    }
    const response=await fetch(file.href,{signal:controller.signal});
    if(!response.ok)throw Error(response.status===404?'文件不存在或已被移除。':apiError(response.status));
    const max=4*1024*1024;
    if(Number(response.headers.get('Content-Length'))>max)throw Error('文件超过 4 MB，请下载后打开。');
    const blob=await response.blob();if(blob.size>max)throw Error('文件超过 4 MB，请下载后打开。');
    const text=await blob.text();
    if(controller.signal.aborted||attachmentPreviewController!==controller)return;
    if(type==='html'){
      const html=await attachmentHtml(text,file,controller);
      if(controller.signal.aborted||attachmentPreviewController!==controller)return;
      const frame=document.createElement('iframe');frame.className='attachment-frame';frame.title=name;
      frame.setAttribute('sandbox','allow-scripts');frame.setAttribute('referrerpolicy','no-referrer');
      frame.srcdoc=html;
      content.appendChild(frame);status.textContent='HTML 预览';
    }else{
      const pre=document.createElement('pre');pre.className='attachment-text';pre.textContent=text;content.appendChild(pre);status.textContent='文本预览';
    }
  }catch(error){if(!controller.signal.aborted&&attachmentPreviewController===controller)status.textContent='无法预览：'+error.message+' 可使用上方下载。'}
}
feed.addEventListener('click',e=>{
  const a=e.target.closest('.atts a.file');
  if(!a||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button)return;
  e.preventDefault();openAttachment(a.getAttribute('href'),a.dataset.name||a.textContent);
});
// 附件
let pend=[],uploading=0;
const pendEl=document.getElementById('pend'),fileEl=document.getElementById('file');
function drawPend(){
  pendEl.innerHTML='';pendEl.style.display=(pend.length||uploading)?'flex':'none';
  pend.forEach((a,i)=>{
    const c=document.createElement('div');c.className='chip';
    c.innerHTML=(a.kind==='image'?'<img src="'+esc(a.url)+'"><span>'+esc(a.name)+'</span>':'<button class="chip-open" type="button" title="预览文件">'+esc(a.name)+'</button>')+'<button class="x" type="button">&times;</button>';
    c.querySelector('.x').onclick=()=>{pend.splice(i,1);drawPend()};
    const fileButton=c.querySelector('.chip-open');if(fileButton)fileButton.onclick=()=>openAttachment(a.url,a.name);
    const im=c.querySelector('img');
    if(im)im.onclick=()=>{const ims=pend.map((p,k)=>({url:p.url,name:p.name,pend:k})).filter(p=>pend[p.pend].kind==='image');openViewer(ims,ims.findIndex(p=>p.pend===i))};
    pendEl.appendChild(c);
  });
  if(uploading){const c=document.createElement('div');c.className='chip';c.textContent='上传中 '+uploading+' 个…';pendEl.appendChild(c)}
}
async function upload(f){
  uploading++;drawPend();
  try{
    const r=await fetch(api('upload')+'?name='+encodeURIComponent(f.name||'file'),{method:'POST',body:f});
    const j=await r.json();
    if(!r.ok)throw new Error(j.error||r.status);
    pend.push(j);
  }catch(e){alert('上传失败：'+f.name+'\n'+e.message)}
  uploading--;drawPend();
}
document.getElementById('clip').onclick=()=>fileEl.click();
// 粘贴：剪贴板里有图片 / 文件就当附件传；同时有文字时文字照常粘
ta.addEventListener('paste',e=>{
  const cd=e.clipboardData;if(!cd)return;
  const fs=[...cd.items].filter(i=>i.kind==='file').map(i=>i.getAsFile()).filter(Boolean);
  if(!fs.length)return;
  if(!cd.getData('text/plain'))e.preventDefault();
  const t=new Date(),stamp=[t.getHours(),t.getMinutes(),t.getSeconds()].map(n=>String(n).padStart(2,'0')).join('');
  (async()=>{for(let i=0;i<fs.length;i++){let f=fs[i];
    if(!f.name||/^image\.\w+$/i.test(f.name)){const ext=(f.type.split('/')[1]||'png').replace('jpeg','jpg');f=new File([f],'粘贴_'+stamp+(fs.length>1?'_'+(i+1):'')+'.'+ext,{type:f.type})}
    await upload(f)}})();
});
// 拖文件到页面上也行
let dragN=0;
document.addEventListener('dragenter',e=>{if([...(e.dataTransfer||{}).types||[]].includes('Files')){dragN++;document.body.classList.add('drag')}});
document.addEventListener('dragleave',()=>{if(dragN&&!--dragN)document.body.classList.remove('drag')});
document.addEventListener('dragover',e=>{if([...(e.dataTransfer||{}).types||[]].includes('Files'))e.preventDefault()});
document.addEventListener('drop',async e=>{
  if(!e.dataTransfer||!e.dataTransfer.files.length)return;
  e.preventDefault();dragN=0;document.body.classList.remove('drag');
  for(const f of [...e.dataTransfer.files])await upload(f);
});
// 引用回复
let quote=null;
const quoteEl=document.getElementById('quote');
function setQuote(m,part){
  if(!m){quote=null;quoteEl.classList.remove('on');return}
  part=(part||'').replace(/\s+/g,' ').trim();
  if(part){quote={id:m.id,speaker:m.speaker,part};quoteEl.querySelector('.qtx').textContent='回复 '+m.speaker+' 这段：“'+part+'”';quoteEl.classList.add('on');ta.focus();return}
  const t=(m.text||'').replace(/\*\*|__|~~|`+/g,'').replace(/^\s*(#+|[-*>])\s+/gm,'').replace(/\s+/g,' ').trim()||((m.attachments||[]).length?'（附件）':'');
  quote={id:m.id,speaker:m.speaker};
  quoteEl.querySelector('.qtx').textContent='回复 '+m.speaker+'：'+t;
  quoteEl.classList.add('on');ta.focus();
}
document.getElementById('quoteX').onclick=()=>setQuote(null);
// 选中的文字落在哪条消息里
function selIn(){
  const sel=getSelection();if(!sel||sel.isCollapsed||!sel.rangeCount)return null;
  const text=sel.toString().trim();if(!text)return null;
  const a=sel.getRangeAt(0).commonAncestorContainer;
  const el=(a.nodeType===1?a:a.parentElement).closest('.msg[data-id]');
  if(!el)return null;
  return {id:+el.dataset.id,text};
}
const cmenu=document.getElementById('cmenu');
cmenu.setAttribute('role','group');cmenu.setAttribute('aria-label','消息操作');
const selectionTools=document.createElement('div');
selectionTools.id='selectionTools';selectionTools.hidden=true;
selectionTools.setAttribute('role','group');selectionTools.setAttribute('aria-label','选中文字操作');
selectionTools.innerHTML='<button type="button" data-selection="copy">复制选中</button><button type="button" data-selection="quote">引用选中</button>';
document.body.appendChild(selectionTools);
const copyNotice=document.createElement('div');copyNotice.id='copyNotice';copyNotice.setAttribute('role','status');document.body.appendChild(copyNotice);
let copyNoticeTimer;
async function copyMessageText(text){
  const ok=await copyText(text);
  copyNotice.textContent=ok?'已复制':'复制失败，请选中文字后按 Ctrl/Cmd+C';
  copyNotice.classList.add('on');clearTimeout(copyNoticeTimer);
  copyNoticeTimer=setTimeout(()=>copyNotice.classList.remove('on'),2500);
}
function placeMessageTools(element,x,y){
  const w=element.offsetWidth,h=element.offsetHeight;
  element.style.left=Math.max(8,Math.min(x,innerWidth-w-8))+'px';
  element.style.top=Math.max(8,Math.min(y,innerHeight-h-8))+'px';
}
function hideMenu(){cmenu.classList.remove('on')}
function updateSelectionTools(){
  const selected=selIn();
  if(!selected||!msgById[selected.id]||cmenu.classList.contains('on')){selectionTools.hidden=true;return}
  const rect=getSelection().getRangeAt(0).getBoundingClientRect(),bounds=feed.getBoundingClientRect();
  if(rect.bottom<bounds.top||rect.top>bounds.bottom){selectionTools.hidden=true;return}
  selectionTools.hidden=false;
  placeMessageTools(selectionTools,rect.left,Math.max(bounds.top+8,rect.top-selectionTools.offsetHeight-8));
}
document.addEventListener('selectionchange',updateSelectionTools);
selectionTools.onmousedown=e=>e.preventDefault();
selectionTools.onclick=e=>{
  const button=e.target.closest('[data-selection]'),selected=selIn();if(!button||!selected)return;
  if(button.dataset.selection==='copy')copyMessageText(selected.text);
  else {setQuote(msgById[selected.id],selected.text);getSelection().removeAllRanges();selectionTools.hidden=true;}
};
feed.addEventListener('contextmenu',e=>{
  const el=e.target.closest('.msg[data-id]');if(!el)return;
  const m=msgById[+el.dataset.id];if(!m)return;
  const x=selIn(),part=x&&x.id===m.id?x.text:'';
  e.preventDefault();selectionTools.hidden=true;
  const items=[];
  if(part){items.push(['复制选中文字',()=>copyMessageText(part)]);items.push(['引用选中片段',()=>setQuote(m,part)])}
  items.push(['复制整条消息',()=>copyMessageText(m.text||'')]);
  if(m.speaker==='你'||isAgent(m.speaker))items.push(['引用整条消息',()=>setQuote(m)]);
  cmenu.innerHTML='';
  items.forEach(([t,f])=>{const b=document.createElement('button');b.type='button';b.textContent=t;b.onclick=()=>{hideMenu();f()};cmenu.appendChild(b)});
  cmenu.classList.add('on');placeMessageTools(cmenu,e.clientX,e.clientY);
  if(e.button===0)cmenu.querySelector('button').focus();
});
cmenu.onmousedown=e=>e.preventDefault();
document.addEventListener('mousedown',e=>{if(!cmenu.contains(e.target))hideMenu()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){hideMenu();selectionTools.hidden=true;}});
feed.addEventListener('scroll',()=>{hideMenu();updateSelectionTools()});
addEventListener('resize',()=>{hideMenu();updateSelectionTools()});
fileEl.onchange=async()=>{const fs=[...fileEl.files];fileEl.value='';for(const f of fs)await upload(f)};
async function send(){
  const text=ta.value.trim();
  if(uploading){alert('附件还在上传，稍等一下');return}
  if(!text&&!pend.length)return;
  const atts=pend,qm=quote;
  ta.value='';ta.style.height='auto';pend=[];drawPend();quote=null;quoteEl.classList.remove('on');
  try{
    const body={text,attachments:atts.map(a=>({path:a.path,kind:a.kind}))};
    if(qm){body.reply_to=qm.id;if(qm.part)body.reply_part=qm.part}
    const r=await fetch(api('send'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok)throw 0;
  }catch(e){ta.value=text;pend=atts;drawPend();if(qm){quote=qm;quoteEl.classList.add('on')}}
  poll();setTimeout(()=>{feed.scrollTop=feed.scrollHeight},100);
}
document.getElementById('send').onclick=send;
ta.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!touch&&!e.isComposing){e.preventDefault();send()}});
ta.addEventListener('input',()=>{ta.style.height='auto';ta.style.height=Math.min(ta.scrollHeight,140)+'px'});
// 跳到我的发言：点 = 上一条 / 下一条"你"说的话，长按 = 到顶 / 到底
const jumpEl=document.getElementById('jump'),jUp=document.getElementById('jUp'),jDn=document.getElementById('jDn');
function feedTop(){return feed.getBoundingClientRect().top+12}
function myMsgs(){return [...feed.querySelectorAll('.msg.me')]}
function prevMine(){const t=feedTop()-4;return myMsgs().filter(e=>e.getBoundingClientRect().top<t).pop()}
function nextMine(){const t=feedTop()+4;return myMsgs().find(e=>e.getBoundingClientRect().top>t)}
function atEnd(){return feed.scrollHeight-feed.scrollTop-feed.clientHeight<4}
// 平滑滚动；页面在后台等情况下动画不走，就直接跳过去
function scrollFeed(top){
  const from=feed.scrollTop;top=Math.max(0,Math.min(top,feed.scrollHeight-feed.clientHeight));
  feed.scrollTo({top,behavior:'smooth'});
  setTimeout(()=>{if(Math.abs(feed.scrollTop-from)<1&&Math.abs(top-from)>1)feed.scrollTop=top},400);
}
function goTo(el){
  scrollFeed(feed.scrollTop+el.getBoundingClientRect().top-feedTop());
  el.classList.remove('flash');void el.offsetWidth;el.classList.add('flash');setTimeout(()=>el.classList.remove('flash'),1200);
}
function syncJump(){
  const scrollable=feed.scrollHeight>feed.clientHeight+20;
  jumpEl.classList.toggle('on',scrollable);
  if(!scrollable)return;
  // 两边都在：位置跟着聊天区右边、输入区（和状态行）上面
  const fr=feed.getBoundingClientRect();
  jumpEl.style.right=Math.max(8,innerWidth-fr.right+16)+'px';
  jumpEl.style.bottom=Math.max(8,innerHeight-fr.bottom+12)+'px';
  jUp.classList.toggle('dim',!prevMine()&&feed.scrollTop<4);
  jDn.classList.toggle('dim',atEnd());
}
function holdable(btn,onTap,onHold){
  let timer=null,held=false;
  const clear=()=>{clearTimeout(timer);timer=null};
  btn.addEventListener('pointerdown',e=>{if(e.button)return;held=false;clear();timer=setTimeout(()=>{held=true;timer=null;onHold();if(navigator.vibrate)navigator.vibrate(15)},500)});
  ['pointerup','pointerleave','pointercancel'].forEach(t=>btn.addEventListener(t,clear));
  btn.addEventListener('click',e=>{if(held){held=false;e.preventDefault();return}onTap()});
  btn.addEventListener('contextmenu',e=>e.preventDefault());   // 手机长按别弹菜单
}
holdable(jUp,()=>{const el=prevMine();if(el)goTo(el);else scrollFeed(0)},()=>scrollFeed(0));
holdable(jDn,()=>{const el=nextMine();if(el)goTo(el);else scrollFeed(feed.scrollHeight)},()=>scrollFeed(feed.scrollHeight));
let jumpRaf=0;
const queueJump=()=>{if(!jumpRaf)jumpRaf=requestAnimationFrame(()=>{jumpRaf=0;syncJump()})};
feed.addEventListener('scroll',queueJump);addEventListener('resize',queueJump);
if(window.ResizeObserver){const ro=new ResizeObserver(queueJump);ro.observe(feed);ro.observe(document.querySelector('footer'))}
setInterval(queueJump,1500);
// 我的发言目录：列出"你"说过的每一句，点一下跳过去
const tocEl=document.getElementById('toc'),tocList=document.getElementById('tocList'),tocQ=document.getElementById('tocQ');
const narrow=()=>innerWidth<=700;
function tocLine(m){
  const t=(m.text||'').replace(/```[\s\S]*?(```|$)/g,' [代码] ').replace(/\s+/g,' ').trim();
  const n=(m.attachments||[]).length;
  return (t||'')+(n?(t?' ':'')+'📎'+n:'')||'（空）';
}
function curMine(){const mid=feedTop()+feed.clientHeight/3;return myMsgs().filter(e=>e.getBoundingClientRect().top<=mid).pop()}
function drawToc(){
  const q=tocQ.value.trim().toLowerCase(),cur=curMine();
  const els=myMsgs();
  document.getElementById('tocN').textContent=els.length+' 条';
  tocList.innerHTML='';
  let curLi=null;
  els.forEach((el,i)=>{
    const m=msgById[+el.dataset.id];if(!m)return;
    const line=tocLine(m);
    if(q&&line.toLowerCase().indexOf(q)<0)return;
    const li=document.createElement('li');
    li.innerHTML='<span class="t">'+esc((m.time||'').slice(0,5)||'#'+(i+1))+'</span><span class="x">'+esc(line)+'</span>';
    li.title=(m.text||'').slice(0,400);
    if(el===cur){li.classList.add('cur');curLi=li}
    li.onclick=()=>{goTo(el);if(narrow())closeToc();else{tocList.querySelectorAll('.cur').forEach(x=>x.classList.remove('cur'));li.classList.add('cur')}};
    tocList.appendChild(li);
  });
  if(!tocList.children.length){const li=document.createElement('li');li.className='empty';li.textContent=q?'没搜到':'你还没发过言';tocList.appendChild(li)}
  if(curLi)curLi.scrollIntoView({block:'center'});
}
function placeToc(){
  if(narrow()){tocEl.style.left=tocEl.style.right=tocEl.style.bottom='';return}
  const r=jumpEl.getBoundingClientRect();
  tocEl.style.right=(innerWidth-r.left+8)+'px';
  tocEl.style.bottom=(innerHeight-r.bottom)+'px';
  tocEl.style.left='auto';
}
function openToc(){tocQ.value='';tocEl.classList.add('on');placeToc();drawToc();if(!touch)tocQ.focus()}
function closeToc(){tocEl.classList.remove('on')}
document.getElementById('jToc').onclick=()=>tocEl.classList.contains('on')?closeToc():openToc();
document.getElementById('tocX').onclick=closeToc;
tocQ.addEventListener('input',drawToc);
document.addEventListener('pointerdown',e=>{if(tocEl.classList.contains('on')&&!tocEl.contains(e.target)&&!e.target.closest('#jToc'))closeToc()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&tocEl.classList.contains('on'))closeToc()});
addEventListener('resize',()=>{if(tocEl.classList.contains('on'))placeToc()});
