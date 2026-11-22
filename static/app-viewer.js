// 看图：就在这一页里看，左右切换；能画笔 / 箭头 / 框 / 文字 / 裁剪，改完的图放进输入框
const vw=document.getElementById('viewer'),vStage=document.getElementById('vStage'),vImg=document.getElementById('vImg');
const vCv=document.getElementById('vCv'),vOv=document.getElementById('vOv'),vWrap=document.getElementById('vWrap'),vHint=document.getElementById('vHint');
const vctx=vCv.getContext('2d'),octx=vOv.getContext('2d');
let vList=[],vIdx=0,ed=null,editorLoad=0;
const savedImageEdits=new Map();
function openViewer(list,i){if(!list.length)return;vList=list;vIdx=Math.max(0,i);vw.classList.add('on');showImg()}
function closeViewer(){if(ed&&ed.dirty&&!confirm('丢掉还没保存的操作？'))return;endEdit();vw.classList.remove('on');vImg.removeAttribute('src')}
function showImg(){
  const it=vList[vIdx];endEdit();vStage.classList.remove('zoom');
  vImg.src=it.url;vImg.alt=it.name||'';
  document.getElementById('vOrig').href=it.attachment?.edit?.source||it.url;
  document.getElementById('vInfo').textContent=(vList.length>1?(vIdx+1)+' / '+vList.length+'  ':'')+(it.name||'');
  document.getElementById('vPrev').style.visibility=vIdx>0?'':'hidden';
  document.getElementById('vNext').style.visibility=vIdx<vList.length-1?'':'hidden';
  vHint.textContent=vList.length>1?(touch?'左右滑动切换 · 点图看原尺寸':'← → 切换 · 点图看原尺寸 · Esc 关闭'):(touch?'点图看原尺寸':'点图看原尺寸 · Esc 关闭');
}
function step(d){const j=vIdx+d;if(j<0||j>=vList.length||ed)return;vIdx=j;showImg()}
feed.addEventListener('click',e=>{
  const a=e.target.closest('.atts a.img');
  if(!a||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button)return;   // Ctrl 点照旧开新标签页
  e.preventDefault();
  const els=[...feed.querySelectorAll('.atts a.img')];
  openViewer(els.map(x=>({url:x.getAttribute('href'),name:x.dataset.name||''})),els.indexOf(a));
});
document.getElementById('vPrev').onclick=()=>step(-1);
document.getElementById('vNext').onclick=()=>step(1);
document.getElementById('vClose').onclick=closeViewer;
vImg.onclick=()=>{if(!swiped)vStage.classList.toggle('zoom')};
vStage.addEventListener('click',e=>{if(e.target===vStage&&!ed)closeViewer()});
// 手机左右滑
let sx=null,sy=0,swiped=false;
vStage.addEventListener('pointerdown',e=>{swiped=false;if(ed||vStage.classList.contains('zoom')||e.pointerType==='mouse')return;sx=e.clientX;sy=e.clientY});
vStage.addEventListener('pointerup',e=>{if(sx==null)return;const dx=e.clientX-sx,dy=e.clientY-sy;sx=null;if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)*1.5){swiped=true;step(dx<0?1:-1)}});
vStage.addEventListener('pointercancel',()=>{sx=null});
document.addEventListener('keydown',e=>{
  if(!vw.classList.contains('on'))return;
  if(e.key==='Escape'){e.preventDefault();ed?cancelEdit():closeViewer();return}
  if(ed){if((e.ctrlKey||e.metaKey)&&['z','y'].includes(e.key.toLowerCase())){e.preventDefault();moveHistory(e.shiftKey||e.key.toLowerCase()==='y'?1:-1)}return}
  if(e.key==='ArrowLeft')step(-1);else if(e.key==='ArrowRight')step(1);
});
// —— 标注 ——
const TOOL_HINT={pen:'按住拖动画线',arrow:'从起点拖到箭头指的地方',rect:'拖出一个框',text:'点一下要写字的位置',crop:'拖出要留下的区域，松手就裁',erase:'拖动擦除标注',mosaic:'框选需要打码的区域'};
const THICK=[['细',.6],['中',1],['粗',1.8]];
function imageEditKey(it){return 'cojam.image-edit.'+RID+'.'+it.url}
function restoreImageEdit(key,it){
  let cached=savedImageEdits.get(key);
  if(!cached)try{cached=JSON.parse(sessionStorage.getItem(key))}catch(e){}
  return cached||it.attachment?.edit;
}
function saveImageEdit(state){
  const data={source:state.source,name:state.name,ops:state.ops.slice(),cursor:state.cursor};
  savedImageEdits.set(state.key,data);
  try{sessionStorage.setItem(state.key,JSON.stringify(data))}catch(e){}
  if(ed===state)ed.dirty=false;
  return data;
}
function startEdit(){
  const it=vList[vIdx],token=++editorLoad,key=imageEditKey(it),saved=restoreImageEdit(key,it);
  const source=saved?.source||it.url,img=new Image();
  img.onerror=()=>{if(token===editorLoad)alert('这张图打不开')};
  img.onload=()=>{
    if(token!==editorLoad||!vw.classList.contains('on'))return;
    ed={img,source,key,name:saved?.name||it.name,ops:saved?.ops?.slice()||[],cursor:saved?.cursor||0,
        tool:'pen',color:document.querySelector('#vTools .sw.on').dataset.color,thick:1,drag:null,dirty:false,busy:false,
        base:document.createElement('canvas'),layer:document.createElement('canvas')};
    vw.classList.add('edit');replay();syncTools();
  };
  vStage.classList.remove('zoom');
  img.src=source;
}
function endEdit(){editorLoad++;ed=null;vw.classList.remove('edit')}
function cancelEdit(){if(ed.busy||ed.dirty&&!confirm('丢掉还没保存的操作？'))return;endEdit()}
function setSize(w,h){vCv.width=vOv.width=w;vCv.height=vOv.height=h}
function fitCanvas(){
  if(!ed)return;
  const W=Math.max(1,vStage.clientWidth-16),H=Math.max(1,vStage.clientHeight-16),s=Math.min(W/vCv.width,H/vCv.height,1);
  const w=Math.round(vCv.width*s)+'px',h=Math.round(vCv.height*s)+'px';
  vCv.style.width=vOv.style.width=w;vCv.style.height=vOv.style.height=h;
}
addEventListener('resize',fitCanvas);
function syncTools(){
  document.querySelectorAll('#vTools [data-tool]').forEach(b=>b.classList.toggle('on',b.dataset.tool===ed.tool));
  document.getElementById('vUndo').disabled=ed.busy||!ed.cursor;
  document.getElementById('vRedo').disabled=ed.busy||ed.cursor===ed.ops.length;
  ['vDone','vSave','vCancel'].forEach(id=>document.getElementById(id).disabled=ed.busy);
  document.getElementById('vThick').textContent=THICK.find(t=>t[1]===ed.thick)[0];
  vHint.textContent=TOOL_HINT[ed.tool]+(touch?'':' · Ctrl+Z 撤销 · Esc 取消');
  vWrap.style.cursor=ed.tool==='text'?'text':'crosshair';
}
document.querySelectorAll('#vTools [data-tool]').forEach(b=>b.onclick=()=>{ed.tool=b.dataset.tool;syncTools()});
document.querySelectorAll('#vTools .sw').forEach(b=>b.onclick=()=>{document.querySelectorAll('#vTools .sw').forEach(x=>x.classList.toggle('on',x===b));if(ed)ed.color=b.dataset.color});
document.getElementById('vThick').onclick=()=>{const i=THICK.findIndex(t=>t[1]===ed.thick);ed.thick=THICK[(i+1)%THICK.length][1];syncTools()};
document.getElementById('vEdit').onclick=startEdit;
document.getElementById('vCancel').onclick=cancelEdit;
document.getElementById('vUndo').onclick=()=>moveHistory(-1);
document.getElementById('vRedo').onclick=()=>moveHistory(1);
function lw(){return Math.max(2,Math.round(Math.max(vCv.width,vCv.height)/170*ed.thick))}
function commitEdit(op){
  ed.ops.splice(ed.cursor,ed.ops.length-ed.cursor,op);ed.cursor++;ed.dirty=true;
  applyEdit(op);drawEditedImage();syncTools();
}
function moveHistory(delta){
  if(!ed||ed.busy||ed.drag)return;
  const cursor=ed.cursor+delta;if(cursor<0||cursor>ed.ops.length)return;
  ed.cursor=cursor;ed.dirty=true;replay();syncTools();
}
function pt(e){const r=vCv.getBoundingClientRect();return {x:Math.max(0,Math.min(vCv.width,(e.clientX-r.left)*vCv.width/r.width)),y:Math.max(0,Math.min(vCv.height,(e.clientY-r.top)*vCv.height/r.height))}}
function stroke(c,col,w){c.strokeStyle=col;c.fillStyle=col;c.lineWidth=w;c.lineCap='round';c.lineJoin='round'}
function drawArrow(c,a,b){
  const w=c.lineWidth,ang=Math.atan2(b.y-a.y,b.x-a.x),hl=Math.max(w*4,12);
  c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x-Math.cos(ang)*hl*.6,b.y-Math.sin(ang)*hl*.6);c.stroke();
  c.beginPath();c.moveTo(b.x,b.y);c.lineTo(b.x-hl*Math.cos(ang-.45),b.y-hl*Math.sin(ang-.45));c.lineTo(b.x-hl*Math.cos(ang+.45),b.y-hl*Math.sin(ang+.45));c.closePath();c.fill();
}
function box(a,b){return {x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),w:Math.abs(b.x-a.x),h:Math.abs(b.y-a.y)}}
function drawPath(ctx,points){
  ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);
  if(points.length===1)ctx.lineTo(points[0].x+.01,points[0].y);
  else points.slice(1).forEach(p=>ctx.lineTo(p.x,p.y));
  ctx.stroke();
}
function cropLayer(canvas,r){
  const copy=document.createElement('canvas');copy.width=r.w;copy.height=r.h;
  copy.getContext('2d').drawImage(canvas,r.x,r.y,r.w,r.h,0,0,r.w,r.h);
  canvas.width=r.w;canvas.height=r.h;canvas.getContext('2d').drawImage(copy,0,0);
}
function applyEdit(op){
  const layer=ed.layer.getContext('2d'),base=ed.base.getContext('2d');
  if(op.tool==='crop'){cropLayer(ed.base,op.rect);cropLayer(ed.layer,op.rect);return}
  if(op.tool==='mosaic'){
    const r=op.rect,pixels=document.createElement('canvas');
    pixels.width=Math.max(1,Math.ceil(r.w/op.block));pixels.height=Math.max(1,Math.ceil(r.h/op.block));
    pixels.getContext('2d').drawImage(ed.base,r.x,r.y,r.w,r.h,0,0,pixels.width,pixels.height);
    base.save();base.clearRect(r.x,r.y,r.w,r.h);base.imageSmoothingEnabled=false;
    base.drawImage(pixels,r.x,r.y,r.w,r.h);base.restore();return;
  }
  layer.save();stroke(layer,op.color,op.width);
  if(op.tool==='erase'){layer.globalCompositeOperation='destination-out';layer.strokeStyle='#000';drawPath(layer,op.points)}
  else if(op.tool==='pen')drawPath(layer,op.points);
  else if(op.tool==='arrow')drawArrow(layer,op.a,op.b);
  else if(op.tool==='rect')layer.strokeRect(op.rect.x,op.rect.y,op.rect.w,op.rect.h);
  else if(op.tool==='text'){
    layer.font='bold '+op.size+'px system-ui,"Microsoft YaHei",sans-serif';layer.textBaseline='top';
    layer.lineWidth=Math.max(2,op.size/7);layer.strokeStyle=op.color==='#111111'?'#fff':'rgba(0,0,0,.75)';
    op.text.split('\n').forEach((line,i)=>{const y=op.a.y+i*op.size*1.25;layer.strokeText(line,op.a.x,y);layer.fillText(line,op.a.x,y)});
  }
  layer.restore();
}
function drawEditedImage(){
  if(vCv.width!==ed.base.width||vCv.height!==ed.base.height)setSize(ed.base.width,ed.base.height);
  vctx.clearRect(0,0,vCv.width,vCv.height);vctx.drawImage(ed.base,0,0);vctx.drawImage(ed.layer,0,0);fitCanvas();
}
function replay(){
  ed.base.width=ed.layer.width=ed.img.naturalWidth;ed.base.height=ed.layer.height=ed.img.naturalHeight;
  ed.base.getContext('2d').drawImage(ed.img,0,0);
  ed.ops.slice(0,ed.cursor).forEach(applyEdit);drawEditedImage();
}
function preview(d){
  const {tool,a,b,width,color,points}=d,r=box(a,b);
  octx.clearRect(0,0,vOv.width,vOv.height);stroke(octx,color,width);
  if(tool==='arrow')drawArrow(octx,a,b);
  else if(tool==='pen'||tool==='erase'){
    if(tool==='erase')octx.strokeStyle='rgba(220,220,220,.7)';
    drawPath(octx,points);
  }else{
    if(tool==='crop'){
      octx.fillStyle='rgba(0,0,0,.55)';octx.fillRect(0,0,vOv.width,vOv.height);octx.clearRect(r.x,r.y,r.w,r.h);
      octx.strokeStyle='#fff';
    }else if(tool==='mosaic'){octx.fillStyle='rgba(30,30,30,.35)';octx.fillRect(r.x,r.y,r.w,r.h)}
    octx.strokeRect(r.x,r.y,r.w,r.h);
  }
}
vWrap.addEventListener('pointerdown',e=>{
  if(!ed||ed.busy||ed.drag||e.button!==0)return;e.preventDefault();
  const a=pt(e),{tool,color}=ed,width=lw()*(tool==='erase'?4:1);
  if(tool==='text'){
    const text=prompt('输入标注文字');if(!text?.trim())return;
    commitEdit({tool,color,width,a,text,size:Math.max(16,Math.round(Math.max(vCv.width,vCv.height)/32*ed.thick))});
    return;
  }
  vWrap.setPointerCapture(e.pointerId);
  ed.drag={pointer:e.pointerId,tool,color,width,a,b:a,points:[a]};preview(ed.drag);
});
vWrap.addEventListener('pointermove',e=>{
  const d=ed?.drag;if(!d||d.pointer!==e.pointerId)return;
  d.b=pt(e);
  if(d.tool==='pen'||d.tool==='erase')d.points.push(d.b);
  preview(d);
});
function finishDrag(e){
  const d=ed?.drag;if(!d||d.pointer!==e.pointerId)return;
  ed.drag=null;octx.clearRect(0,0,vOv.width,vOv.height);
  if(e.type==='pointercancel')return;
  const {tool,color,width,a,points}=d,b=pt(e),r=box(a,b),min=Math.max(4,width);
  if(tool==='pen'||tool==='erase'){
    if(b.x!==d.b.x||b.y!==d.b.y)points.push(b);
    commitEdit({tool,color,width,points});return;
  }
  if(tool==='crop'||tool==='mosaic'){
    if(r.w<min||r.h<min)return;
    const x=Math.floor(r.x),y=Math.floor(r.y),w=Math.ceil(r.x+r.w)-x,h=Math.ceil(r.y+r.h)-y;
    commitEdit({tool,rect:{x,y,w,h},block:Math.max(8,Math.round(width*3))});return;
  }
  if(r.w>=min||r.h>=min)commitEdit({tool,color,width,a,b,rect:r});
}
vWrap.addEventListener('pointerup',finishDrag);
vWrap.addEventListener('pointercancel',finishDrag);
function canvasFile(){
  const n=(ed.name||'图片').replace(/\.[^.]+$/,''),name=(/_标注$/.test(n)?n:n+'_标注')+'.png';
  return new Promise(resolve=>vCv.toBlob(blob=>resolve(blob&&new File([blob],name,{type:'image/png'})),'image/png'));
}
document.getElementById('vSave').onclick=async()=>{
  const current=ed;if(!current||current.drag||current.busy)return;
  current.busy=true;syncTools();
  try{
    const f=await canvasFile();if(!f||ed!==current)return;
    saveImageEdit(current);
    const a=document.createElement('a');a.href=URL.createObjectURL(f);a.download=f.name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),5000);
  }finally{if(ed===current){current.busy=false;syncTools()}}
};
document.getElementById('vDone').onclick=async()=>{
  const current=ed,it=vList[vIdx],rid=RID;if(!current||current.drag||current.busy)return;
  current.busy=true;syncTools();
  try{
    const f=await canvasFile();if(!f){alert('导出失败');return}
    if(ed!==current)return;
    const data={source:current.source,name:current.name,ops:current.ops.slice(),cursor:current.cursor};
    if(!await upload(f,rid,it.attachment,data)||ed!==current)return;
    saveImageEdit(current);closeViewer();ta.focus();
  }finally{if(ed===current){current.busy=false;syncTools()}}
};
