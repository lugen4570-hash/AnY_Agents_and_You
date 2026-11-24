// The backend checks the fixed official manifest and downloads the installer.
(function(){
  const entry=document.getElementById('updateApp');
  if(!entry)return;
  const officialDownloads='https://lugen4570-hash.github.io/AnY_Agents_and_You/download.html#desktop';
  const VISIBLE_STATES=new Set(['available','downloading','downloaded','installing','installed']);
  let timer=null, bgTimer=null, latest=null;
  function syncEntry(data){
    const visible=!!(data && VISIBLE_STATES.has(data.state));
    entry.hidden=!visible;
    entry.classList.toggle('has-update',visible);
  }
  syncEntry(null);
  async function get(path){const r=await fetch(path,{cache:'no-store'});const data=await r.json();if(!r.ok)throw Error(data.error||'更新请求失败');return data}
  function render(data){
    latest=data;
    syncEntry(data);
    const box=document.getElementById('updateContent');if(!box)return;
    let body='<p>当前版本：'+esc(data.current||'未知')+'</p>';
    if(data.state==='available'){
      const label=data.macos?'下载 macOS ZIP':(data.can_install?'下载并更新':'下载安装程序');
      const hint=data.macos?'解压新版后运行「构建 AnY 桌面版.command」，退出 AnY 后替换 AnY.app。浏览器版可以直接从新目录启动。'
        :(data.can_install?'更新会在任务结束后关闭并重新打开 AnY，会话数据会保留。':'下载后请关闭 AnY，再手动运行安装程序。原来使用解压版时，请在安装向导中选择原来的程序文件夹，以继续使用其中的 data 数据。');
      body+='<p>发现新版本 '+esc(data.latest)+'。</p>'+(data.notes?'<p>'+esc(data.notes)+'</p>':'')+'<button id="updateDownload" class="pri">'+label+'</button><p class="hint">'+hint+'</p>';
    }
    else if(data.state==='downloading'){
      const pct=Math.floor((data.downloaded||0)*100/(data.size||1));
      const parts=[];
      if(data.size)parts.push(((data.downloaded||0)/1048576).toFixed(1)+' / '+(data.size/1048576).toFixed(1)+' MB');
      if(data.speed>0)parts.push(data.speed>=1048576?(data.speed/1048576).toFixed(1)+' MB/s':Math.round(data.speed/1024)+' KB/s');
      body+='<p>正在下载… '+pct+'%'+(parts.length?'（'+parts.join(' · ')+'）':'')+'</p>';
    }
    else if(data.state==='downloaded'){
      const next=data.macos?'<p>请解压 ZIP。桌面版可双击其中的构建脚本，退出 AnY 后替换应用。</p>'
        :(data.can_install?'<button id="updateInstall" class="pri">安装并重新打开</button>':'<p>请关闭 AnY 后手动运行：</p>');
      body+='<p>下载完成，文件已校验。</p>'+(data.error?'<p role="alert">'+esc(data.error)+'</p>':'')+next+'<p><code>'+esc(data.path)+'</code></p>';
    }
    else if(data.state==='installing')body+='<p>正在安装更新，AnY 将关闭并在安装完成后重新打开。</p>';
    else if(data.state==='installed')body+='<p>安装完成。如果 AnY 没有自动重新打开，请退出后重新打开。</p>';
    else if(data.state==='current')body+='<p>当前已是最新发布版本（'+esc(data.latest)+'）。</p>';
    else body+='<p role="alert">'+esc(data.error||'正在检查更新…')+'</p>';
    box.innerHTML=body+'<p><a href="'+officialDownloads+'" target="_blank" rel="noopener noreferrer">打开官网下载页</a></p>';
    const button=document.getElementById('updateDownload');
    if(button)button.onclick=async()=>{if(data.can_install&&!confirm('更新时会关闭并重新打开 AnY。请确认当前没有未完成的操作。继续吗？'))return;button.disabled=true;try{const [ok,result]=await post('/api/update/download',data.can_install?{auto_install:true}:{});if(!ok)throw Error(result.error||'下载失败');render(result);poll()}catch(e){box.insertAdjacentHTML('beforeend','<p role="alert">'+esc(e.message)+'</p>');button.disabled=false}};
    const install=document.getElementById('updateInstall');
    if(install)install.onclick=async()=>{if(!confirm('更新时会关闭并重新打开 AnY。继续吗？'))return;install.disabled=true;try{const [ok,result]=await post('/api/update/install',{});if(!ok)throw Error(result.error||'安装失败');render(result)}catch(e){box.insertAdjacentHTML('beforeend','<p role="alert">'+esc(e.message)+'</p>');install.disabled=false}};
    if(data.state==='downloading'||data.state==='installing')poll();
  }
  function poll(){clearTimeout(timer);timer=setTimeout(async()=>{try{render(await get('/api/update/status'))}catch(e){const box=document.getElementById('updateContent');if(box)box.textContent='无法获取下载状态，请检查后台是否运行。'}},1000)}
  async function check(){try{render(await get('/api/update/check'))}catch(e){render({state:'error',current:latest&&latest.current,error:e.message})}}
  function scheduleBackgroundCheck(delay){clearTimeout(bgTimer);bgTimer=setTimeout(async()=>{try{const data=await get('/api/update/check');latest=data;syncEntry(data);}catch(e){}finally{scheduleBackgroundCheck(3600000);}},delay)}
  entry.onclick=()=>{showModal('<h3>AnY 更新</h3><div id="updateContent" aria-live="polite"><p>正在检查更新…</p></div><div class="btns"><button id="updateRefresh">重新检查</button><button id="updateClose">关闭</button></div>');document.getElementById('updateClose').onclick=()=>{clearTimeout(timer);hideModal()};document.getElementById('updateRefresh').onclick=check;check()};
  scheduleBackgroundCheck(5000);
})();
