// 看图：就在这一页里看，左右切换；能画笔 / 箭头 / 框 / 文字 / 裁剪，改完的图放进输入框
const vw=document.getElementById('viewer'),vStage=document.getElementById('vStage'),vImg=document.getElementById('vImg');
const vCv=document.getElementById('vCv'),vOv=document.getElementById('vOv'),vWrap=document.getElementById('vWrap'),vHint=document.getElementById('vHint');
const vctx=vCv.getContext('2d'),octx=vOv.getContext('2d');
let vList=[],vIdx=0,ed=null;
function openViewer(list,i){if(!list.length)return;vList=list;vIdx=Math.max(0,i);vw.classList.add('on');showImg()}
function closeViewer(){if(ed&&ed.hist.length&&!confirm('标注还没放进输入框，丢掉？'))return;endEdit();vw.classList.remove('on');vImg.removeAttribute('src')}
function showImg(){
  const it=vList[vIdx];endEdit();vStage.classList.remove('zoom');vImg.removeEventListener('load',startEdit);
  vImg.src=it.url;vImg.alt=it.name||'';
  document.getElementById('vOrig').href=it.url;
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
  if(ed){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();undoEdit()}return}
  if(e.key==='ArrowLeft')step(-1);else if(e.key==='ArrowRight')step(1);
});
// —— 标注 ——
const TOOL_HINT={pen:'按住拖动画线',arrow:'从起点拖到箭头指的地方',rect:'拖出一个框',text:'点一下要写字的位置',crop:'拖出要留下的区域，松手就裁'};
const THICK=[['细',.6],['中',1],['粗',1.8]];
function startEdit(){
  if(!vImg.complete){vImg.addEventListener('load',startEdit,{once:true});return}   // 刚切过来还在加载：加载完再进
  if(!vImg.naturalWidth){alert('这张图打不开');return}
  vStage.classList.remove('zoom');
  ed={hist:[],tool:ed&&ed.tool||'pen',color:document.querySelector('#vTools .sw.on').dataset.color,thick:ed?ed.thick:1,drag:null};
  setSize(vImg.naturalWidth,vImg.naturalHeight);vctx.drawImage(vImg,0,0);
  vw.classList.add('edit');syncTools();fitCanvas();
}
function endEdit(){ed=null;vw.classList.remove('edit')}
function cancelEdit(){if(ed.hist.length&&!confirm('丢掉这次的标注？'))return;endEdit()}
function setSize(w,h){vCv.width=vOv.width=w;vCv.height=vOv.height=h}
function fitCanvas(){
  if(!ed)return;
  const W=vStage.clientWidth-16,H=vStage.clientHeight-16,s=Math.min(W/vCv.width,H/vCv.height,1);
  const w=Math.round(vCv.width*s)+'px',h=Math.round(vCv.height*s)+'px';
  vCv.style.width=vOv.style.width=w;vCv.style.height=vOv.style.height=h;
}
addEventListener('resize',fitCanvas);
function syncTools(){
  document.querySelectorAll('#vTools [data-tool]').forEach(b=>b.classList.toggle('on',b.dataset.tool===ed.tool));
  document.getElementById('vUndo').disabled=!ed.hist.length;
  document.getElementById('vThick').textContent=THICK.find(t=>t[1]===ed.thick)[0];
  vHint.textContent=TOOL_HINT[ed.tool]+(touch?'':' · Ctrl+Z 撤销 · Esc 取消');
  vWrap.style.cursor=ed.tool==='text'?'text':'crosshair';
}
document.querySelectorAll('#vTools [data-tool]').forEach(b=>b.onclick=()=>{ed.tool=b.dataset.tool;syncTools()});
document.querySelectorAll('#vTools .sw').forEach(b=>b.onclick=()=>{document.querySelectorAll('#vTools .sw').forEach(x=>x.classList.toggle('on',x===b));if(ed)ed.color=b.dataset.color});
document.getElementById('vThick').onclick=()=>{const i=THICK.findIndex(t=>t[1]===ed.thick);ed.thick=THICK[(i+1)%THICK.length][1];syncTools()};
document.getElementById('vEdit').onclick=startEdit;
document.getElementById('vCancel').onclick=cancelEdit;
document.getElementById('vUndo').onclick=()=>undoEdit();
function lw(){return Math.max(2,Math.round(Math.max(vCv.width,vCv.height)/170*ed.thick))}
function snap(){
  const c=document.createElement('canvas');c.width=vCv.width;c.height=vCv.height;c.getContext('2d').drawImage(vCv,0,0);
  ed.hist.push(c);if(ed.hist.length>30)ed.hist.shift();syncTools();
}
function undoEdit(){
  if(!ed||!ed.hist.length)return;
  const c=ed.hist.pop();setSize(c.width,c.height);vctx.drawImage(c,0,0);fitCanvas();syncTools();
}
function pt(e){const r=vCv.getBoundingClientRect();return {x:(e.clientX-r.left)*vCv.width/r.width,y:(e.clientY-r.top)*vCv.height/r.height}}
function stroke(c,col,w){c.strokeStyle=col;c.fillStyle=col;c.lineWidth=w;c.lineCap='round';c.lineJoin='round'}
function drawArrow(c,a,b){
  const w=c.lineWidth,ang=Math.atan2(b.y-a.y,b.x-a.x),hl=Math.max(w*4,12);
  c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x-Math.cos(ang)*hl*.6,b.y-Math.sin(ang)*hl*.6);c.stroke();
  c.beginPath();c.moveTo(b.x,b.y);c.lineTo(b.x-hl*Math.cos(ang-.45),b.y-hl*Math.sin(ang-.45));c.lineTo(b.x-hl*Math.cos(ang+.45),b.y-hl*Math.sin(ang+.45));c.closePath();c.fill();
}
function box(a,b){return {x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),w:Math.abs(b.x-a.x),h:Math.abs(b.y-a.y)}}
function preview(a,b){
  octx.clearRect(0,0,vOv.width,vOv.height);stroke(octx,ed.color,lw());
  if(ed.tool==='arrow')drawArrow(octx,a,b);
  else if(ed.tool==='rect'){const r=box(a,b);octx.strokeRect(r.x,r.y,r.w,r.h)}
  else if(ed.tool==='crop'){
    const r=box(a,b);octx.fillStyle='rgba(0,0,0,.55)';octx.fillRect(0,0,vOv.width,vOv.height);octx.clearRect(r.x,r.y,r.w,r.h);
    octx.setLineDash([lw()*3,lw()*2]);octx.strokeStyle='#fff';octx.lineWidth=Math.max(1,lw()/2);octx.strokeRect(r.x,r.y,r.w,r.h);octx.setLineDash([]);
  }
}
vWrap.addEventListener('pointerdown',e=>{
  if(!ed||e.button)return;e.preventDefault();
  const p=pt(e);
  if(ed.tool==='text'){
    const s=prompt('写什么？');if(!s||!s.trim())return;
    snap();const fs=Math.max(16,Math.round(Math.max(vCv.width,vCv.height)/32*ed.thick));
    vctx.font='bold '+fs+'px system-ui,"Microsoft YaHei",sans-serif';vctx.textBaseline='top';
    vctx.lineWidth=Math.max(2,fs/7);vctx.lineJoin='round';vctx.strokeStyle=ed.color==='#111111'?'#fff':'rgba(0,0,0,.75)';vctx.fillStyle=ed.color;
    s.split('\n').forEach((l,i)=>{vctx.strokeText(l,p.x,p.y+i*fs*1.25);vctx.fillText(l,p.x,p.y+i*fs*1.25)});
    return;
  }
  vWrap.setPointerCapture(e.pointerId);
  ed.drag={a:p,b:p};
  if(ed.tool==='pen'){snap();stroke(vctx,ed.color,lw());vctx.beginPath();vctx.moveTo(p.x,p.y);vctx.lineTo(p.x+.01,p.y);vctx.stroke()}
});
vWrap.addEventListener('pointermove',e=>{
  if(!ed||!ed.drag)return;
  const p=pt(e),d=ed.drag;
  if(ed.tool==='pen'){vctx.beginPath();vctx.moveTo(d.b.x,d.b.y);vctx.lineTo(p.x,p.y);vctx.stroke();d.b=p}
  else{d.b=p;preview(d.a,p)}
});
function finishDrag(){
  if(!ed||!ed.drag)return;
  const {a,b}=ed.drag;ed.drag=null;octx.clearRect(0,0,vOv.width,vOv.height);
  if(ed.tool==='pen')return;
  const r=box(a,b),min=Math.max(6,lw()*2);
  if(r.w<min&&r.h<min)return;
  if(ed.tool==='crop'){
    if(r.w<min||r.h<min)return;
    const x=Math.max(0,Math.round(r.x)),y=Math.max(0,Math.round(r.y));
    const w=Math.min(vCv.width-x,Math.round(r.w)),h=Math.min(vCv.height-y,Math.round(r.h));
    snap();const c=ed.hist[ed.hist.length-1];setSize(w,h);vctx.drawImage(c,x,y,w,h,0,0,w,h);fitCanvas();return;
  }
  snap();stroke(vctx,ed.color,lw());
  if(ed.tool==='arrow')drawArrow(vctx,a,b);else vctx.strokeRect(r.x,r.y,r.w,r.h);
}
vWrap.addEventListener('pointerup',finishDrag);
vWrap.addEventListener('pointercancel',finishDrag);
function editedName(){const n=(vList[vIdx].name||'图片').replace(/\.[^.]+$/,'');return (/_标注$/.test(n)?n:n+'_标注')+'.png'}
function canvasFile(){return new Promise(r=>vCv.toBlob(b=>r(b&&new File([b],editedName(),{type:'image/png'})),'image/png'))}
document.getElementById('vSave').onclick=async()=>{
  const f=await canvasFile();if(!f)return;
  const a=document.createElement('a');a.href=URL.createObjectURL(f);a.download=f.name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),5000);
};
document.getElementById('vDone').onclick=async()=>{
  const f=await canvasFile();if(!f){alert('导出失败');return}
  const it=vList[vIdx];
  if(it.pend!=null&&pend[it.pend]&&pend[it.pend].url===it.url){pend.splice(it.pend,1);drawPend()}   // 改的是还没发的附件：换掉原图
  endEdit();vw.classList.remove('on');vImg.removeAttribute('src');
  await upload(f);ta.focus();
};
