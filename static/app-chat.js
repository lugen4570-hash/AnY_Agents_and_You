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
function add(m,existing){
  const d=existing||document.createElement('div');
  const speaker=agentMeta(m.speaker);
  const cls=m.speaker==='你'?'me':isAgent(m.speaker)?(speaker?.kind==='user'?'human':'ai'):'sys';
  d.className='msg '+cls+(m.to_user?' touser':'')+(m.step!=null?' step':'');
  if(cls==='ai')d.style.setProperty('--c',agentColor(m.speaker));
  else d.style.removeProperty('--c');
  if(cls==='ai'||cls==='human')d.dataset.l=agentLetter(m.speaker);
  const tag=m.origin==='debate-summary'?'<span class="tag debate-summary">论道总结</span>':m.to_user?'<span class="tag">→ 用户</span>':'';
  const share=canShareRoomResult(m)?'<button type="button" class="share-result">确认分享</button>':'';
  const actions=m.recalled?'':'<span class="message-actions"><button type="button" class="mc" title="复制消息文字">复制</button><button type="button" class="rp" title="选中文字可引用片段">引用</button>'+(cls==='me'?'<button type="button" class="recall">撤回</button>':'')+share+'</span>';
  const who=cls==='sys'?'':'<div class="who"><span class="nm">'+esc(speaker?.label||m.speaker)+'</span>'+(cls==='ai'?'<span class="speaker-kind">AI</span>':cls==='human'?'<span class="speaker-kind">成员</span>':'')+'<span class="tm">'+esc(m.time)+'</span>'+tag+actions+'</div>';
  const q=m.reply_to?'<div class="qt" data-to="'+m.reply_to.id+'">'+esc(m.reply_to.speaker)+'：'+(m.reply_to.part?'“'+esc(m.reply_to.text)+'”':esc(m.reply_to.text))+'</div>':'';
  d.dataset.id=m.id;msgById[m.id]=m;
  const md=cls==='ai'||cls==='human';
  d.innerHTML=who+q+(m.text?'<div class="body'+(md?' md':'')+'">'+render(m.text,md)+'</div>':'')+attHtml(m.attachments)+(m.step!=null?'<button type="button" class="undo" data-step="'+m.step+'">撤回这一步</button>':'');
  if(typeof attachAgentProgress==='function')attachAgentProgress(m,d);
  if(typeof attachRoomFeedback==='function')attachRoomFeedback(m,d);
  if(!existing)feed.appendChild(d);
  const ub=d.querySelector('.undo');if(ub)ub.onclick=()=>undoStep(m.step);
  d.querySelectorAll('.message-actions button').forEach(b=>b.onmousedown=e=>e.preventDefault());
  const rb=d.querySelector('.rp');if(rb)rb.onclick=()=>{const selected=selIn();setQuote(m,selected&&selected.id===m.id?selected.text:'')};
  const cb=d.querySelector('.mc');if(cb)cb.onclick=()=>copyMessageText(m.text||'');
  const rc=d.querySelector('.recall');if(rc)rc.onclick=()=>recallMessage(m.id);
  const sr=d.querySelector('.share-result');if(sr)sr.onclick=()=>openRoomResultShare(m);
  const qb=d.querySelector('.qt');if(qb)qb.onclick=()=>{const o=feed.querySelector('.msg[data-id="'+qb.dataset.to+'"]');if(o){o.scrollIntoView({block:'center',behavior:'smooth'});o.classList.add('flash');setTimeout(()=>o.classList.remove('flash'),1200)}};
}
function roomShareRecipients(){
  if(typeof S==='undefined'||!S||typeof agCat==='undefined'||agCat?.local_workspace===false)return [];
  return (S.agents||[]).filter(a=>a.kind==='user'&&(S.participants||[]).includes(a.id)&&S.permissions?.[a.id]?.read);
}
function canShareRoomResult(m){
  return !m.recalled&&m.speaker!=='系统'&&m.origin!=='shared-result'&&!!(m.text||m.attachments?.length)&&roomShareRecipients().length>0;
}
function openRoomResultShare(m){
  const rid=RID;
  const recipients=roomShareRecipients().map(a=>'<label><input type="checkbox" data-share-user="'+esc(a.id)+'">'+esc(a.label||a.id)+'</label>').join('');
  const files=(m.attachments||[]).map((a,i)=>'<label><input type="checkbox" data-share-file="'+i+'">'+esc(a.name)+'</label>').join('');
  const text=m.text?'<label><input type="checkbox" id="shareResultText">分享下方正文</label><details><summary>查看正文</summary><pre class="message-text">'+esc(m.text)+'</pre></details>':'';
  showModal('<h3>确认分享给外部成员</h3><p class="hint">请选择接收人和要发出的内容。</p><div class="perm-grid">'+recipients+'</div>'+text+'<div class="perm-grid">'+files+'</div><div class="btns"><button id="cancelResultShare">取消</button><button class="pri" id="submitResultShare">确认分享</button></div>');
  document.getElementById('cancelResultShare').onclick=hideModal;
  document.getElementById('submitResultShare').onclick=async e=>{
    if(rid!==RID)return;
    const button=e.currentTarget;
    const recipients=[...mbox.querySelectorAll('[data-share-user]:checked')].map(i=>i.dataset.shareUser);
    const attachments=[...mbox.querySelectorAll('[data-share-file]:checked')].map(i=>Number(i.dataset.shareFile));
    const share_text=!!document.getElementById('shareResultText')?.checked;
    if(!recipients.length||(!share_text&&!attachments.length))return alert('请选择接收人，以及要分享的正文或附件。');
    button.disabled=true;
    try{
      const [ok,result]=await post('/api/r/'+encodeURIComponent(rid)+'/contact/share',{id:m.id,recipients,attachments,share_text});
      if(!ok)return alert(result.error||'分享失败');
      if(rid===RID){hideModal();await poll();}
    }finally{button.disabled=false;}
  };
}
function applyMessageRecalls(ids){
  if(!ids?.length)return;
  const recalled=new Set(ids);
  if(quote&&recalled.has(quote.id))setQuote(null);
  for(const m of Object.values(msgById)){
    if(recalled.has(m.id)&&!m.recalled){
      add({id:m.id,speaker:m.speaker,time:m.time,text:'消息已撤回',recalled:true},feed.querySelector('.msg[data-id="'+m.id+'"]'));
    }else if(m.reply_to&&recalled.has(m.reply_to.id)){
      m.reply_to={id:m.reply_to.id,speaker:m.reply_to.speaker,text:'消息已撤回'};
      const q=feed.querySelector('.msg[data-id="'+m.id+'"] .qt');
      if(q)q.textContent=m.reply_to.speaker+'：消息已撤回';
    }
  }
  hideMenu();
}
function restoreRecalledDraft(rid,recalled){
  if(!rid||!recalled)return;
  const draft=getDraft(rid);
  const text=typeof recalled.text==='string'?recalled.text:'';
  if(text)draft.text=draft.text?text+'\n'+draft.text:text;
  for(const att of (recalled.attachments||[])){
    if(att&&att.path&&!draft.attachments.some(item=>item&&item.path===att.path)){
      draft.attachments.push({...att});
    }
  }
  const rt=recalled.reply_to;
  if(!draft.quote&&rt&&rt.id!=null&&rt.text!=='消息已撤回'){
    const known=rid===RID?msgById[rt.id]:null;
    if(!known||!known.recalled){
      const partText=rt.part&&typeof rt.text==='string'?rt.text:'';
      const qText=typeof rt.text==='string'?rt.text:'';
      draft.quote={
        id:rt.id,
        speaker:rt.speaker||'',
        part:partText,
        label:partText?'回复 '+(rt.speaker||'')+' 这段：“'+partText+'”':'回复 '+(rt.speaker||'')+'：'+qText,
      };
    }
  }
  persistDraft(rid,draft);
  if(rid===RID){
    restoreDraft();
    if(typeof syncComposerBar==='function')syncComposerBar();
    if(typeof ta.focus==='function')ta.focus();
    if(typeof ta.setSelectionRange==='function')ta.setSelectionRange(ta.value.length,ta.value.length);
  }
}
const recallingMessages=new Set();
async function recallMessage(id){
  const rid=RID;
  if(!rid)return;
  const key=rid+':'+id;
  const cached=msgById[id];
  if(cached?.recalled||recallingMessages.has(key)||!confirm('撤回这条消息并放回输入框？AnY 会取消它触发的任务，并撤回能关联到它的 Agent 回复。读过撤回内容的本机 Agent 会在下次运行时重建会话。'))return;
  const orig=cached?{text:cached.text||'',attachments:Array.isArray(cached.attachments)?cached.attachments:[],reply_to:cached.reply_to||null}:null;
  recallingMessages.add(key);
  try{
    const [ok,j]=await post(api('recall'),{id});
    if(ok)restoreRecalledDraft(rid,j.draft||orig);
    if(rid!==RID)return;
    if(ok){applyMessageRecalls(j.recalled||[id]);if(j.stop_error)alert(j.stop_error);poll()}else alert(j.error||'撤回失败');
  }finally{recallingMessages.delete(key)}
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
let pend=[];
const drafts=new Map(), uploads=new Map(), sendingRooms=new Set();
const draftKey=rid=>'any.draft.'+rid;
let uploadStore;
const activeUploads=new Set(), uploadTransfers=new Map();
function draftUploadStore(){
  if(!uploadStore)uploadStore=new Promise((resolve,reject)=>{
    const request=indexedDB.open('any-draft-uploads',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('uploads',{keyPath:'id'}).createIndex('room','rid');
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(request.error);
  });
  return uploadStore;
}
async function draftUploadTransaction(mode,operation){
  const db=await draftUploadStore();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction('uploads',mode),request=operation(tx.objectStore('uploads'));
    tx.oncomplete=()=>resolve(request.result);
    tx.onabort=()=>reject(tx.error);
  });
}
async function resumeDraftUploads(rid){
  try{
    const records=await draftUploadTransaction('readonly',s=>s.index('room').getAll(rid));
    await Promise.all(records.map(record=>{
      if(activeUploads.has(record.id))return;
      const attachments=getDraft(rid).attachments;
      const replace=record.replacePath&&attachments.find(a=>a.path===record.replacePath);
      if(attachments.some(a=>a.uploadId===record.id)||(record.replacePath&&!replace)){
        return draftUploadTransaction('readwrite',s=>s.delete(record.id));
      }
      return upload(record.file,rid,replace,record.edit,record);
    }));
  }catch(e){}
}
function getDraft(rid){
  if(!drafts.has(rid)){
    let saved;
    try{saved=JSON.parse(sessionStorage.getItem(draftKey(rid))||localStorage.getItem(draftKey(rid)))}catch(e){}
    drafts.set(rid,saved&&Array.isArray(saved.attachments)?saved:{text:'',attachments:[],quote:null});
    if(saved)persistDraft(rid,drafts.get(rid));
  }
  return drafts.get(rid);
}
function persistDraft(rid,draft){
  if(!rid)return;
  try{
    if(draft.text||draft.attachments.length||draft.quote)localStorage.setItem(draftKey(rid),JSON.stringify(draft));
    else localStorage.removeItem(draftKey(rid));
    sessionStorage.removeItem(draftKey(rid));
  }catch(e){try{sessionStorage.setItem(draftKey(rid),JSON.stringify(draft))}catch(e){}}
}
function saveDraft(){
  if(!RID)return;
  const draft=getDraft(RID);
  Object.assign(draft,{text:ta.value,attachments:pend,quote});persistDraft(RID,draft);
}
function restoreDraft(){
  const draft=RID?getDraft(RID):{text:'',attachments:[],quote:null};
  if(ta.value!==draft.text)ta.value=draft.text;
  pend=draft.attachments;quote=draft.quote;
  renderQuote();resizeComposer();drawPend();
}
const pendEl=document.getElementById('pend'),fileEl=document.getElementById('file');
let filePickerRoom=null;
function drawPend(){
  const uploading=uploads.get(RID)||0;
  pendEl.innerHTML='';pendEl.style.display=(pend.length||uploading)?'flex':'none';
  pend.forEach((a,i)=>{
    const c=document.createElement('div');c.className='chip';
    c.innerHTML=(a.kind==='image'?'<button type="button" class="chip-image" aria-label="查看或编辑 '+esc(a.name)+'"><img src="'+esc(a.url)+'" alt=""></button><span>'+esc(a.name)+'</span>':'<button class="chip-open" type="button" title="预览文件">'+esc(a.name)+'</button>')+'<button class="x" type="button" aria-label="移除 '+esc(a.name)+'">&times;</button>';
    c.querySelector('.x').onclick=()=>{pend.splice(i,1);saveDraft();drawPend()};
    const fileButton=c.querySelector('.chip-open');if(fileButton)fileButton.onclick=()=>openAttachment(a.url,a.name);
    const im=c.querySelector('.chip-image');
    if(im)im.onclick=()=>{const ims=pend.filter(p=>p.kind==='image').map(p=>({url:p.url,name:p.name,attachment:p}));openViewer(ims,ims.findIndex(p=>p.attachment===a))};
    pendEl.appendChild(c);
  });
  if(uploading){const c=document.createElement('div');c.className='chip';c.textContent='上传中 '+uploading+' 个…';pendEl.appendChild(c)}
}
async function upload(f,rid=RID,replace=null,edit=null,saved=null){
  if(!rid||!f)return false;
  const readFileBytes=async file=>{
    if(typeof file.arrayBuffer==='function')return await file.arrayBuffer();
    if(typeof FileReader==='function'){
      return await new Promise((resolve,reject)=>{
        const reader=new FileReader();
        reader.onload=()=>resolve(reader.result);
        reader.onerror=()=>reject(reader.error||new Error('读取文件失败'));
        reader.readAsArrayBuffer(file);
      });
    }
    return null;
  };
  const uploadName=file=>{
    if(file&&file.name)return file.name;
    const mime=(file&&file.type)||'';
    const sub=(mime.split('/')[1]||'bin').split(';')[0].replace('jpeg','jpg').replace(/[^a-z0-9._-]/gi,'')||'bin';
    const t=new Date(),stamp=[t.getHours(),t.getMinutes(),t.getSeconds()].map(n=>String(n).padStart(2,'0')).join('');
    return 'upload_'+stamp+'.'+sub;
  };
  const safeUploadStoreOp=async(mode,op)=>{
    let timer;
    try{
      return await Promise.race([
        draftUploadTransaction(mode,op),
        new Promise(resolve=>{timer=setTimeout(()=>resolve(null),300)}),
      ]);
    }catch(e){return null}
    finally{if(timer)clearTimeout(timer)}
  };
  const name=(saved&&saved.fileName)||uploadName(f);
  if(typeof f.size==='number'&&f.size>25*1024*1024){if(rid===RID)alert('附件必须大于 0 字节且不超过 25 MB：'+name);return false}
  let bytes=null;
  try{bytes=await readFileBytes(f)}catch(e){if(rid===RID)alert('无法读取文件：'+name+'\n'+((e&&e.message)||e));return false}
  const byteSize=bytes?bytes.byteLength:(typeof f.size==='number'?f.size:0);
  if(!byteSize||byteSize>25*1024*1024){if(rid===RID)alert('附件必须大于 0 字节且不超过 25 MB：'+name);return false}
  const storedFile=(bytes&&typeof Blob==='function')?new Blob([bytes],{type:(f&&f.type)||'application/octet-stream'}):f;
  const uid=(typeof crypto!=='undefined'&&crypto.getRandomValues)?crypto.getRandomValues(new Uint32Array(4)).join('-'):(Date.now()+'-'+Math.random().toString(16).slice(2));
  const record=saved||{id:uid,rid,file:storedFile,fileName:name,replacePath:replace?.path,edit};
  const previous=uploadTransfers.get(rid);
  let release;
  const transfer=new Promise(resolve=>{release=resolve});
  uploadTransfers.set(rid,transfer);
  activeUploads.add(record.id);
  uploads.set(rid,(uploads.get(rid)||0)+1);if(rid===RID)drawPend();
  try{
    if(!saved)await safeUploadStoreOp('readwrite',s=>s.put(record));
    await previous;
    const headers={'Content-Type':(f&&f.type)||'application/octet-stream'};
    const r=await fetch('/api/r/'+encodeURIComponent(rid)+'/upload?name='+encodeURIComponent(name),{method:'POST',headers,body:bytes||f});
    let j={};
    if(typeof r.text==='function'){
      const raw=await r.text();
      try{j=raw?JSON.parse(raw):{}}catch(err){if(!r.ok)throw new Error('HTTP '+r.status);throw new Error('服务器返回格式异常')}
    }else{
      j=await r.json();
    }
    if(!r.ok)throw new Error(j.error||r.status);
    const draft=getDraft(rid),attachments=draft.attachments;
    const at=attachments.indexOf(replace);
    if(edit)j.edit=edit;
    j.uploadId=record.id;
    if(!replace)attachments.push(j);else if(at>=0)attachments.splice(at,1,j);
    persistDraft(rid,draft);
    await safeUploadStoreOp('readwrite',s=>s.delete(record.id));
    return !replace||at>=0;
  }catch(e){if(rid===RID)alert('上传失败：'+name+'\n'+e.message);return false}
  finally{
    release();if(uploadTransfers.get(rid)===transfer)uploadTransfers.delete(rid);
    activeUploads.delete(record.id);
    const count=uploads.get(rid)-1;if(count)uploads.set(rid,count);else uploads.delete(rid);
    if(rid===RID)drawPend();
  }
}
document.getElementById('clip').onclick=()=>{filePickerRoom=RID;fileEl.click()};
// 粘贴：剪贴板里有图片 / 文件就当附件传；同时有文字时文字照常粘
ta.addEventListener('paste',e=>{
  const cd=e.clipboardData;if(!cd)return;
  const fs=[...cd.items].filter(i=>i.kind==='file').map(i=>i.getAsFile()).filter(Boolean);
  if(!fs.length)return;
  if(!cd.getData('text/plain'))e.preventDefault();
  const t=new Date(),stamp=[t.getHours(),t.getMinutes(),t.getSeconds()].map(n=>String(n).padStart(2,'0')).join('');
  const rid=RID;
  fs.forEach((file,i)=>{let f=file;
    if(!f.name||/^image\.\w+$/i.test(f.name)){const ext=(f.type.split('/')[1]||'png').replace('jpeg','jpg');f=new File([f],'粘贴_'+stamp+(fs.length>1?'_'+(i+1):'')+'.'+ext,{type:f.type})}
    upload(f,rid)});
});
// 拖文件到页面上也行
let dragN=0;
document.addEventListener('dragenter',e=>{if([...(e.dataTransfer||{}).types||[]].includes('Files')){dragN++;document.body.classList.add('drag')}});
document.addEventListener('dragleave',()=>{if(dragN&&!--dragN)document.body.classList.remove('drag')});
document.addEventListener('dragover',e=>{if([...(e.dataTransfer||{}).types||[]].includes('Files'))e.preventDefault()});
document.addEventListener('drop',async e=>{
  if(!e.dataTransfer||!e.dataTransfer.files.length)return;
  e.preventDefault();dragN=0;document.body.classList.remove('drag');
  const rid=RID;
  await Promise.all([...e.dataTransfer.files].map(f=>upload(f,rid)));
});
// 引用回复
let quote=null;
const quoteEl=document.getElementById('quote');
function renderQuote(){
  quoteEl.classList.toggle('on',!!quote);
  if(quote)quoteEl.querySelector('.qtx').textContent=quote.label||'回复 '+quote.speaker;
}
function setQuote(m,part){
  if(!m){quote=null;renderQuote();saveDraft();return}
  if(m.recalled)return;
  part=(part||'').replace(/\s+/g,' ').trim();
  const t=(m.text||'').replace(/\*\*|__|~~|`+/g,'').replace(/^\s*(#+|[-*>])\s+/gm,'').replace(/\s+/g,' ').trim()||((m.attachments||[]).length?'（附件）':'');
  quote={id:m.id,speaker:m.speaker,part,label:part?'回复 '+m.speaker+' 这段：“'+part+'”':'回复 '+m.speaker+'：'+t};
  renderQuote();saveDraft();ta.focus();
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
  if(!selected||!msgById[selected.id]||msgById[selected.id].recalled||cmenu.classList.contains('on')){selectionTools.hidden=true;return}
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
  if(m.recalled)return;
  const x=selIn(),part=x&&x.id===m.id?x.text:'';
  e.preventDefault();selectionTools.hidden=true;
  const items=[];
  if(part){items.push(['复制选中文字',()=>copyMessageText(part)]);items.push(['引用选中片段',()=>setQuote(m,part)])}
  items.push(['复制整条消息',()=>copyMessageText(m.text||'')]);
  if(m.speaker==='你'||isAgent(m.speaker))items.push(['引用整条消息',()=>setQuote(m)]);
  if(canShareRoomResult(m))items.push(['确认分享给外部成员',()=>openRoomResultShare(m)]);
  if(m.speaker==='你')items.push(['撤回消息',()=>recallMessage(m.id)]);
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
fileEl.onchange=()=>{const fs=[...fileEl.files],rid=filePickerRoom||RID;filePickerRoom=null;fileEl.value='';fs.forEach(f=>upload(f,rid))};
async function send(){
  const rid=RID,original=ta.value;
  const harness=typeof window!=='undefined'&&(window.AnYHarness||window.CojamHarness);
  const text=(harness?.composerMention ? harness.composerMention(original,S).text : original).trim();
  if(!rid||sendingRooms.has(rid))return;
  if(uploads.get(rid)){alert('附件还在上传，稍等一下');return}
  if(!text&&!pend.length)return;
  const atts=pend.slice(),qm=quote;
  if(!atts.length&&typeof harness?.handleComposerSlashCommand==='function'){
    const slashResult=await harness.handleComposerSlashCommand(text);
    if(slashResult&&slashResult.handled){
      if(slashResult.clear){
        const draft=getDraft(rid);
        if(draft.text===original)draft.text='';
        if(draft.quote===qm)draft.quote=null;
        persistDraft(rid,draft);
        if(rid===RID)restoreDraft();
      }
      return;
    }
  }
  saveDraft();sendingRooms.add(rid);
  try{
    const body={text,attachments:atts.map(a=>({path:a.path,kind:a.kind}))};
    if(qm){body.reply_to=qm.id;if(qm.part)body.reply_part=qm.part}
    const r=await fetch(api('send'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok)throw new Error((await r.json()).error||'发送失败');
    if(rid===RID)saveDraft();
    const draft=getDraft(rid);
    if(draft.text===original)draft.text='';
    draft.attachments=draft.attachments.filter(a=>!atts.includes(a));
    if(draft.quote===qm)draft.quote=null;
    persistDraft(rid,draft);
    if(rid===RID){restoreDraft();poll();setTimeout(()=>{if(rid===RID)feed.scrollTop=feed.scrollHeight},100)}
  }catch(e){if(rid===RID)alert(e.message||'发送失败，草稿已保留')}
  finally{sendingRooms.delete(rid)}
}
document.getElementById('send').onclick=send;
ta.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!touch&&!e.isComposing){e.preventDefault();send()}});
function resizeComposer(){ta.style.height='auto';ta.style.height=Math.min(ta.scrollHeight,140)+'px'}
ta.addEventListener('input',()=>{resizeComposer();saveDraft()});
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
