// Guided onboarding. Credentials stay in this modal's memory and never in localStorage.
let connectionWizard = null, connectionSequence = 0;
async function checkConnectionBackend(signal) {
  let info;
  try {
    const response = await fetch('/api/server/info', {signal});
    if (!response.ok) throw Error();
    info = await response.json();
  } catch (e) { if (signal && signal.aborted) throw e; throw Error('无法连接 AnY 后台，请重新打开 AnY 后重试。'); }
  if (info.app !== 'AI Bridge' || info.version !== '2.8.42' || info.api_revision !== 3)
    throw Error('界面与后台版本不一致。请重新打开最新的 AnY，再刷新此页面。');
  return info;
}
function hostFromUrl(value) {
  try { return new URL(value).hostname.replace(/^\[|\]$/g, '').toLowerCase(); } catch (e) { return ''; }
}
function isLoopbackHost(host) {
  return ['127.0.0.1', 'localhost', '::1'].includes(host);
}
function connectionDefaultBase(type, info, origin) {
  if (!['user', 'external', 'mydevice'].includes(type)) return origin;
  const host = hostFromUrl(origin);
  if (!host) return origin;
  // When already using a remote address, it is the only address known to
  // work from this device; replacing it with the server's LAN breaks tunnels.
  if (!isLoopbackHost(host)) return origin;
  // 在本机打开页面时给别的设备生成地址：同一个 WiFi 最常用，默认局域网。
  // 没有局域网地址（或对方在外部网络）才用 Tailscale。
  if (type === 'mydevice') return (info && info.lan_url) || (info && info.tailscale_url) || origin;
  return (info && (info.lan_url || info.tailscale_url)) || origin;
}
function connectionBaseWarning(base) {
  try {
    const host = new URL(base).hostname.replace(/^\[|\]$/g, '');
    if (['127.0.0.1', 'localhost', '::1'].includes(host)) return '这是本机地址，只有这台电脑能打开；手机和别的设备连不上。';
  } catch (e) { return '地址格式不对，请填写完整地址，例如 http://192.168.1.5:8766。'; }
  return '';
}
const CONNECTION_TYPES = {
  mydevice: ['我的设备', '手机、平板或另一台电脑获得完整界面，并以「我」的身份参与。', uiIcon('device')],
  local: ['本机 Harness', '接入运行在这台设备上的 CLI 或桌面软件。', uiIcon('terminal')],
  external: ['其他设备上的 Harness', '先填写对方能打开的 AnY 地址，再选择那台设备上的 CLI 或桌面端。', uiIcon('device')],
  http: ['HTTP 服务', '填写你自己的 Harness 服务地址，由本应用主动调用并测试回复。', uiIcon('link')],
  direct: ['API Key 直连', '用服务商提供的 API Key 直接参与文字讨论，无需安装命令行工具。', uiIcon('link')],
  user: ['用户接入', '生成邀请链接，让其他人以自己的身份加入指定会话。', uiIcon('user')]
};
function stopConnectionWizard() {
  if (connectionWizard) { clearInterval(connectionWizard.timer); if (connectionWizard.controller) connectionWizard.controller.abort(); connectionWizard.token = ''; connectionWizard.form.serviceKey = ''; }
  connectionWizard = null;
}
function connectionModalChanged() {
  const box = document.getElementById('connectionWizard');
  if (connectionWizard && (!box || box.dataset.flow !== String(connectionWizard.seq))) stopConnectionWizard();
}
function snapshotConnectionWizard(w) {
  captureConnectionForm(w);
  return {
    step: w.step,
    type: w.type,
    page: w.page,
    device: w.device,
    detected: w.detected,
    initialContact: w.initialContact,
    id: w.id,
    base: w.base,
    localChoice: w.localChoice,
    saved: w.saved,
    memberMode: w.memberMode,
    target: w.target,
    project: w.project,
    info: w.info,
    status: w.status,
    member: w.member,
    token: w.token,
    form: {...w.form, serviceKey: ''},
    permissions: {...w.permissions},
    directSaved: w.directSaved ? {...w.directSaved} : undefined,
  };
}
function restoreConnectionWizard(snapshot) {
  stopConnectionWizard();
  const w = {
    ...snapshot,
    seq: ++connectionSequence,
    form: {...(snapshot.form || {})},
    permissions: {...(snapshot.permissions || {})},
    controller: new AbortController(),
    busy: false,
  };
  connectionWizard = w;
  renderConnectionWizard();
}
async function connectionGet(url) {
  const response = await fetch(url);
  let data = {};
  try { data = await response.json(); } catch (e) {}
  return [response.ok, data];
}
async function renderDeviceSetup(w) {
  const select = document.getElementById('connDeviceBase');
  const custom = document.getElementById('connDeviceCustomBase');
  const hint = document.getElementById('connDeviceBaseHint');
  const options = [];
  if (w.info && w.info.lan_url) options.push([w.info.lan_url, '局域网（同一个 WiFi）']);
  if (w.info && w.info.tailscale_url) options.push([w.info.tailscale_url, 'Tailscale（对方也登录同一 Tailscale）']);
  options.push([location.origin, '当前地址（仅这台电脑）']);
  select.innerHTML = options.map(([value, label]) => '<option value="' + esc(value) + '">' + esc(label) + '</option>').join('')
    + '<option value="__custom__">自定义 HTTPS 地址</option>';
  const known = options.some(([value]) => value === w.base);
  select.value = known ? w.base : '__custom__';
  custom.value = known ? '' : w.base;
  custom.hidden = known;
  // 页面开在本机回环地址时，8765 只有这台电脑能打开；设备链接换成
  // 局域网（8766）或 Tailscale（8767）是正常的，不说清楚会以为出了错。
  const localOpen = isLoopbackHost(hostFromUrl(location.origin));
  const showHint = () => {
    const issue = connectionBaseWarning(w.base);
    hint.textContent = issue || (localOpen
      ? '本机界面用的 ' + new URL(location.origin).host + ' 只有这台电脑能打开；手机 / 其他设备请选局域网地址（同一个 WiFi），人在外面时选 Tailscale。'
      : '用要接入的设备扫描二维码或打开链接。只发给可信设备。');
    hint.classList.toggle('warn', !!issue);
  };
  select.onchange = () => {
    custom.hidden = select.value !== '__custom__';
    w.base = select.value === '__custom__' ? custom.value.trim().replace(/\/+$/, '') : select.value;
    showHint();
  };
  custom.oninput = () => { w.base = custom.value.trim().replace(/\/+$/, ''); showHint(); };
  showHint();
  document.getElementById('connDeviceCreate').onclick = () => generateDeviceCode(w);
  try {
    const [ok, data] = await connectionGet('/api/devices');
    if (!ok) throw Error(data.error || '读取设备失败');
    if (!wizardCurrent(w) || w.type !== 'mydevice' || w.step !== 2) return;
    w.account = data.account;
    w.devices = data.devices || [];
    renderDeviceList(w);
  } catch (error) {
    const list = document.getElementById('connDeviceList');
    if (wizardCurrent(w) && list) list.textContent = error.message;
  }
}
function renderDeviceList(w) {
  const box = document.getElementById('connDeviceList');
  if (!box) return;
  box.innerHTML = (w.devices || []).map(device =>
    '<div class="connection-device"><span><b>' + esc(device.label) + '</b><small>'
    + (device.online ? '在线' : '最近在线 ' + new Date((device.last_seen || device.created) * 1000).toLocaleString())
    + ' · @' + esc(device.id) + '</small></span>'
    + (device.current ? '<small>当前设备</small>' : '<button data-device-revoke="' + esc(device.id) + '">撤销</button>')
    + '</div>').join('') || '<p class="hint">还没有接入其他设备。</p>';
  box.querySelectorAll('[data-device-revoke]').forEach(button => {
    button.onclick = () => revokeDevice(w, button.dataset.deviceRevoke);
  });
}
async function revokeDevice(w, id) {
  if (!confirm('撤销后，这台设备下次请求就会失去完整界面。继续？')) return;
  const [ok, data] = await post('/api/devices/revoke', {id});
  if (!ok) return wizardError(data.error || '撤销失败');
  const [listOk, listing] = await connectionGet('/api/devices');
  if (listOk) { w.devices = listing.devices || []; renderDeviceList(w); }
}
async function generateDeviceCode(w) {
  if (w.busy) return;
  wizardError('');
  const nameInput = document.getElementById('connDeviceName');
  const baseSelect = document.getElementById('connDeviceBase');
  if (nameInput) w.form.deviceName = nameInput.value;
  if (baseSelect) w.base = baseSelect.value === '__custom__'
    ? document.getElementById('connDeviceCustomBase').value.trim().replace(/\/+$/, '') : baseSelect.value;
  try {
    const url = new URL(w.base);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/') throw 0;
  } catch (e) { wizardError('请填写完整的服务根地址，例如 https://example.ts.net'); return; }
  setConnectionBusy(w, true);
  try {
    const [ok, data] = await post('/api/devices/link', {
      label: connectionDeviceName(w.form.deviceName), base: w.base
    });
    if (!ok) throw Error(data.error || '生成失败');
    const issue = connectionBaseWarning(w.base);
    const box = document.getElementById('connDeviceResult');
    box.innerHTML = '<div class="connection-evidence success"><b>✓ 个人设备链接已生成</b>'
      + '<p id="connDeviceLinkStatus">此链接可重复使用，直到你撤销设备。请复制并保存，只发给你信任的设备；持有链接的人可使用你的身份。</p></div>'
      + (isLoopbackHost(hostFromUrl(location.origin))
        ? '<p class="hint">链接里的地址和你在本机用的 ' + esc(new URL(location.origin).host) + ' 不同是正常的：本机入口只给这台电脑用，其他设备走局域网或 Tailscale 入口。</p>'
        : '')
      + (issue ? '<p class="hint connection-base-warning">' + esc(issue) + ' 先换一个设备能打开的地址。</p>'
               : '<div id="connQr" class="connection-qr" aria-label="设备接入二维码"></div>')
      + '<input id="connDeviceUrl" readonly aria-label="设备接入链接"><button id="connDeviceCopy">复制接入链接</button>';
    document.getElementById('connDeviceUrl').value = data.url || '';
    w.deviceCopied = false;
    document.getElementById('connDeviceCopy').onclick = async event => {
      await copyText(data.url || ''); w.deviceCopied = true; event.target.textContent = '已复制';
    };
    if (!issue) renderConnectionQrUrl('connQr', data.url || '');
    clearInterval(w.timer);
    w.timer = setInterval(() => pollDeviceEnrollment(w, data.id), 2000);
  } catch (error) {
    wizardError(error.message);
  } finally {
    if (wizardCurrent(w)) setConnectionBusy(w, false);
  }
}
async function pollDeviceEnrollment(w, id) {
  if (!wizardCurrent(w) || w.type !== 'mydevice' || w.step !== 2) { clearInterval(w.timer); return; }
  if (w.devicePolling) return;
  w.devicePolling = true;
  try {
    const [ok, status] = await connectionGet('/api/devices');
    const device = ok && (status.devices || []).find(item => item.id === id);
    if (device && device.last_seen && wizardCurrent(w)) {
      if (w.deviceCopied) {
        clearInterval(w.timer);
        try { await refreshContacts(); } finally { if (wizardCurrent(w)) connectionLeaveModal(); }
      } else {
        const message = document.getElementById('connDeviceLinkStatus');
        if (message) message.textContent = '设备已接入。请复制并保存这个链接，以后可以在其他浏览器重复打开；关闭后不会再次显示。';
      }
    }
  } catch (e) { /* Retry while the code remains valid. */ }
  finally { w.devicePolling = false; }
}
function renderConnectionQrUrl(id, text) {
  const box = document.getElementById(id);
  if (!box || typeof QRCode !== 'function') return;
  try {
    new QRCode(box, {text, width: 168, height: 168, correctLevel: QRCode.CorrectLevel.M});
  } catch (error) { box.textContent = '二维码没生成出来，请直接用链接。'; }
}
async function startConnectionWizard(id, type) {
  stopConnectionWizard();
  document.body.classList.remove('nav-open');
  const w = {seq: ++connectionSequence, step: 1, type: ['ai', 'external'].includes(type) ? '' : type || '',
    page: type === 'ai' ? 'harness' : type === 'external' ? 'device' : 'entry', device: type === 'external' ? 'remote' : 'local', id: id || '', token: '', base: location.origin,
    form: {}, status: null, busy: false, permissions: connectionDefaultPermissions()};
  connectionWizard = w;
  w.controller = new AbortController();
  const canBack = typeof hasModalBack === 'function' && hasModalBack();
  showModal('<div id="connectionWizard" data-flow="' + w.seq + '"><h3>正在准备接入…</h3><p class="hint" role="status">正在读取联系人和连接信息。</p><div class="btns">' + (canBack ? '<button type="button" id="connLoadingBack">返回</button>' : '') + '<button onclick="hideModal()">取消</button></div></div>');
  const loadingBack = canBack && document.getElementById('connLoadingBack');
  if (loadingBack) loadingBack.onclick = () => { stopConnectionWizard(); popModalBack(); };
  const timeout = setTimeout(() => w.controller.abort(), 15000);
  try {
    const [info] = await Promise.all([checkConnectionBackend(w.controller.signal), refreshContacts(w.controller.signal, true)]);
    if (connectionWizard !== w) return;
    const contact = CONTACTS.find(a => a.id === id);
    if (contact) {
      w.initialContact = true;
      w.type = contact.http_protocol === 'openai_chat' ? 'direct' : contact.kind === 'user' ? 'user' : contact.driver === 'external' ? 'external' : contact.driver === 'http' ? 'http' : 'local';
      w.status = (agCat.connections || {})[id] || null;
      w.localChoice = id; w.saved = true; w.step = 2;
      w.permissions = {...w.permissions, ...(contact.default_permissions || {})};
      if (w.type === 'direct') {
        w.form.model = contact.default?.[0] || '';
        const [ok, config] = await connectionGet('/api/agents/config?id=' + encodeURIComponent(id));
        if (connectionWizard !== w) return;
        if (ok) w.form.endpoint = config.values.endpoint;
        w.directSaved = {endpoint:w.form.endpoint || '', model:w.form.model};
      }
    } else if (w.type) w.step = 2;
    w.info = info;
    w.base = connectionDefaultBase(w.page === 'device' ? 'external' : w.type, info, location.origin);
    renderConnectionWizard();
  } catch (e) {
    if (connectionWizard !== w) return;
    const message = w.controller.signal.aborted ? '读取接入信息超时，请检查后台是否仍在运行后重试。' : (e.message || '无法读取联系人');
    stopConnectionWizard(); showModal('<h3>接入暂不可用</h3><p role="alert">' + esc(message) + '</p><div class="btns">' + (canBack ? '<button type="button" id="connErrBack">返回</button>' : '') + '<button id="connErrRetry">重试</button><button onclick="hideModal()">关闭</button></div>');
    const errBack = canBack && document.getElementById('connErrBack');
    if (errBack) errBack.onclick = () => popModalBack();
    const errRetry = document.getElementById('connErrRetry');
    if (errRetry) errRetry.onclick = () => startConnectionWizard(id, type);
  } finally { clearTimeout(timeout); }
}
function addContact() { return startConnectionWizard(); }
function openConnection(id) {
  const contact = CONTACTS.find(a => a.id === id);
  return contact && contact.kind !== 'user' && typeof openAgentSettings === 'function' ? openAgentSettings(id) : startConnectionWizard(id);
}
function connectionContact(w) { return CONTACTS.find(a => a.id === w.id); }
function wizardCurrent(w) { return connectionWizard === w && !!document.getElementById('connectionWizard'); }
function wizardError(message) { const e = document.getElementById('connError'); if (e) e.textContent = message || ''; }
function connectionLeaveModal() {
  if (typeof hasModalBack === 'function' && hasModalBack()) { stopConnectionWizard(); popModalBack(); }
  else hideModal();
}
function connectionBack(w) {
  if (w.busy) return;
  if (w.step > 2) { w.step = w.step === 3 ? 2 : 3; renderConnectionWizard(); return; }
  if (w.step === 2 && !w.initialContact && w.type !== 'mydevice') {
    const page = w.type === 'user' ? 'entry' : w.type === 'local' || w.type === 'http' || w.device === 'remote' ? 'kind' : 'desktop';
    const {info, base, device, detected} = w;
    stopConnectionWizard();
    connectionWizard = {
      seq: ++connectionSequence, step: w.type === 'http' ? 2 : 1, type: w.type === 'http' ? 'local' : '', page, device, info, base, detected,
      form: {}, controller: new AbortController(), permissions: connectionDefaultPermissions(),
    };
    renderConnectionWizard();
    return;
  }
  const previous = {harness:'entry', device:'harness', kind:w.device === 'remote' ? 'device' : 'harness', desktop:'kind'}[w.page];
  if (w.step === 1 && previous) { w.page = previous; renderConnectionWizard(); }
  else connectionLeaveModal();
}
function connectionDefaultPermissions() {
  return {read:true, post:true, trigger:true, board:false, files:false, work:false};
}
function wizardFrame(w, content) {
  const personal = w.type === 'mydevice';
  const steps = ['选择方式', '配置与验证', '会话与权限', '完成'];
  const canBack = w.step > 1 || w.page !== 'entry' || (typeof hasModalBack === 'function' && hasModalBack());
  const pageKey = [w.seq, w.step, w.page, w.type].join('/');
  const scroll = w.renderedPage === pageKey ? document.getElementById('connBody')?.scrollTop || 0 : 0;
  w.renderedPage = pageKey;
  showModal('<div id="connectionWizard" data-flow="' + w.seq + '"><div class="connection-heading">' + (canBack ? '<button type="button" class="modal-back" id="connWizardBack">← 返回</button>' : '') + '<span class="eyebrow">' + (personal ? '个人设置' : '添加联系人 / 接入') + '</span><button id="connClose" aria-label="关闭接入引导">×</button></div>'
    + (personal || w.type === 'user' ? '' : '<ol class="connection-steps">' + steps.map((s, i) => '<li class="' + (i + 1 === w.step ? 'active' : i + 1 < w.step ? 'done' : '') + '"><span>' + (i + 1) + '</span>' + s + '</li>').join('') + '</ol>')
    + '<div id="connBody" tabindex="0" aria-label="接入设置">' + content + '<p id="connError" role="alert"></p></div></div>');
  document.getElementById('connBody').scrollTop = scroll;
  if (canBack) document.getElementById('connWizardBack').onclick = () => connectionBack(w);
  document.getElementById('connClose').onclick = hideModal;
}
function connectionChoices(w, title, hint, choices, select) {
  wizardFrame(w, '<h3>' + title + '</h3><p class="hint">' + hint + '</p><div class="connection-choices">'
    + choices.map(([id, [label, detail, icon]]) => '<button type="button" class="connection-choice" data-connection-type="' + id + '"><span class="connection-symbol">' + icon + '</span><span><b>' + label + '</b><small>' + detail + '</small></span><span aria-hidden="true">›</span></button>').join('') + '</div>');
  mbox.querySelectorAll('[data-connection-type]').forEach(button => { button.onclick = () => select(button.dataset.connectionType); });
}
function connectionGo(w, page) { w.page = page; renderConnectionWizard(); }
function connectionSetup(w, type, memberMode) {
  w.type = type; w.memberMode = memberMode; w.step = 2;
  if (type === 'user' || w.device !== 'remote') w.base = connectionDefaultBase(type === 'external' ? '' : type, w.info, location.origin);
  renderConnectionWizard();
}
function renderConnectionDevice(w) {
  wizardFrame(w, '<h3>配置其他设备</h3><p class="hint">先在那台设备的浏览器里打开下方地址，确认能访问这台电脑上的 AnY。</p>'
    + '<label>其他设备能访问的 AnY 地址<input id="connRemoteBase" type="url" value="' + esc(w.base) + '"></label>'
    + '<p class="hint">在同一个局域网，使用 AnY 的局域网地址。跨网络请填写双方可访问的 Tailscale 或 HTTPS 地址。</p>'
    + '<div class="btns connection-actions"><button id="connDeviceNext" class="pri">下一步：选择 Harness 类型</button></div>');
  const input = document.getElementById('connRemoteBase');
  input.oninput = () => { w.base = input.value.trim().replace(/\/+$/, ''); wizardError(''); };
  document.getElementById('connDeviceNext').onclick = () => {
    const warning = connectionBaseWarning(w.base);
    if (warning || !validConnectionBase(w.base)) { wizardError(warning || '请填写对方设备能打开的 AnY 根地址。'); return; }
    connectionGo(w, 'kind');
  };
}
function renderConnectionWizard() {
  const w = connectionWizard; if (!w) return;
  clearInterval(w.timer);
  if (w.step === 1) {
    if (w.page === 'device') renderConnectionDevice(w);
    else if (w.page === 'desktop') renderDesktopHarness(w);
    else if (w.page === 'kind') {
      const remote = w.device === 'remote';
      connectionChoices(w, remote ? '其他设备上的 Harness' : '本机 Harness', '选择 Harness 的运行方式。', [
        ['cli', ['CLI 端', remote ? '在那台设备运行成员连接端，让 CLI 自动接收任务并回复。' : '选择已检索到的命令行程序，直接配置并验证。', uiIcon('terminal')]],
        ['desktop', ['桌面端', '下载并配置 AnY MCP，让桌面 Harness 加入会话。', uiIcon('device')]],
      ], type => {
        if (type === 'cli') connectionSetup(w, remote ? 'external' : 'local', remote ? 'auto' : undefined);
        else if (remote) connectionSetup(w, 'external', 'manual');
        else connectionGo(w, 'desktop');
      });
    } else if (w.page === 'harness') {
      connectionChoices(w, 'Harness 在哪里运行？', '选择运行 Harness 的设备。', ['local', 'external'].map(id => [id, CONNECTION_TYPES[id]]), type => {
        w.device = type === 'external' ? 'remote' : 'local';
        w.base = connectionDefaultBase(type, w.info, location.origin);
        connectionGo(w, w.device === 'remote' ? 'device' : 'kind');
      });
    } else {
      connectionChoices(w, '谁来加入 AnY 会话？', '选择要邀请的人或要接入的 Harness。', [
        ['user', CONNECTION_TYPES.user],
        ['harness', ['Harness 接入', '接入本机或其他设备上的 Harness。', uiIcon('terminal')]],
      ], type => type === 'user' ? connectionSetup(w, 'user') : connectionGo(w, 'harness'));
    }
  } else if (w.step === 2) renderConnectionSetup(w);
  else if (w.step === 3) renderConnectionAssignment(w);
  else renderConnectionComplete(w);
}
const ANY_MCP_PAGE = 'https://lugen4570-hash.github.io/AnY_Agents_and_You/mcp.html';
function connectionProgramRows(items, selected, customLabel) {
  return '<div class="connection-programs">' + [...items, {id:'__custom__', label:customLabel}].map(item =>
    '<button type="button" data-conn-program="' + esc(item.id) + '"'
    + (selected ? ' aria-pressed="' + (selected === item.id) + '"' : '')
    + '><b>' + esc(item.label) + '</b>' + (item.id === '__custom__' ? '' : '<small>已检索到</small>') + '</button>').join('') + '</div>';
}
function renderDesktopHarness(w) {
  const items = (w.detected || []).filter(item => ['desktop', 'both'].includes(item.kind) || item.level === 'mcp');
  wizardFrame(w, '<h3>本机 Harness · 桌面端</h3><p class="hint">选择要配置 MCP 的桌面软件。</p>'
    + '<button id="connDesktopScan"' + (w.scanning ? ' disabled' : '') + '>' + (w.scanning ? '正在检索…' : '重新检索已安装程序') + '</button>'
    + connectionProgramRows(items, '', '其他支持 MCP 的桌面软件'));
  mbox.querySelectorAll('[data-conn-program]').forEach(button => {
    button.onclick = () => {
      const item = items.find(item => item.id === button.dataset.connProgram);
      w.form.label = item ? item.label : '';
      connectionSetup(w, 'external', 'manual');
    };
  });
  document.getElementById('connDesktopScan').onclick = () => scanDesktopHarness(w, true);
  if (!w.detected && !w.scanning) scanDesktopHarness(w, false);
}
async function scanDesktopHarness(w, force) {
  if (w.scanning) return;
  w.scanning = true;
  const button = document.getElementById('connDesktopScan');
  button.disabled = true;
  button.textContent = '正在检索…';
  try {
    const [ok, result] = force ? await post('/api/discovery/scan', {}) : await connectionGet('/api/discovery');
    if (!ok) throw Error(result.error || '检索失败，请重试。');
    w.detected = result.detected || [];
    if (wizardCurrent(w) && w.step === 1 && w.page === 'desktop') {
      w.scanning = false;
      renderDesktopHarness(w);
    }
  } catch (error) {
    w.detected ||= [];
    if (wizardCurrent(w) && button === document.getElementById('connDesktopScan')) wizardError(error.message);
  } finally {
    w.scanning = false;
    const current = wizardCurrent(w) && document.getElementById('connDesktopScan');
    if (current) { current.disabled = false; current.textContent = '重新检索已安装程序'; }
  }
}
function connectionNameFields(w) {
  if (w.saved) return '<div class="connection-identity"><b>' + esc((connectionContact(w) || {}).label || w.id) + '</b><small>@' + esc(w.id) + '</small></div>';
  const direct = w.type === 'direct';
  return '<label>联系人名称' + (direct ? '（可选）' : '') + '<input id="connName" maxlength="40" placeholder="' + (direct ? '留空使用模型名称' : '例如：我的 Harness') + '" value="' + esc(w.form.label || '') + '"></label><details class="connection-advanced"><summary>高级：自定义联系人 ID</summary><input id="connId" maxlength="24" placeholder="留空自动生成，小写英文和数字" value="' + esc(w.form.id || '') + '"></details>';
}
function connectionArgsMarkup(w) {
  const values = Array.isArray(w.form.args) ? w.form.args : w.form.localDriver === 'acp' ? ['acp'] : ['-p','{prompt}'];
  return agentListEditor('wizard-args', values);
}
function renderConnectionSetup(w) {
  const title = w.type === 'local' ? '本机 Harness · CLI 端' : w.type === 'external' && !w.initialContact
    ? (w.device === 'remote' ? '其他设备上的 Harness' : '本机 Harness') + (w.memberMode === 'manual' ? ' · 桌面端' : ' · CLI 端')
    : CONNECTION_TYPES[w.type][0];
  let content = '<h3>' + title + '</h3>';
  if (w.type === 'mydevice') {
    content += '<p class="hint">生成可重复使用的个人设备链接，保存后可在不同浏览器打开。该链接拥有你的完整权限，请妥善保管。</p>'
      + '<label>设备名称<input id="connDeviceName" maxlength="40" placeholder="例如：我的 iPhone" value="' + esc(w.form.deviceName || '') + '"></label>'
      + '<label>接入地址<select id="connDeviceBase"></select></label><input id="connDeviceCustomBase" type="url" placeholder="https://example.ts.net" aria-label="自定义接入地址" hidden>'
      + '<p class="hint" id="connDeviceBaseHint"></p>'
      + '<button id="connDeviceCreate" class="pri">生成个人设备链接</button>'
      + '<div id="connDeviceResult"></div>'
      + '<h4>已接入的设备</h4><div id="connDeviceList">正在读取…</div>';
  } else if (w.type === 'user') {
    w.target = w.target || ((ROOMS.find(r => !r.archived) || {}).id || '__new__');
    if (!w.guestPermissionsReady) {
      w.permissions = {read:true,post:true,trigger:false};
      w.guestPermissionsReady = true;
    }
    content += '<p class="hint">邀请票不会预先创建联系人。对方打开链接后领取身份，只加入你选择的会话。</p>'
      + '<label>会话<select id="connGuestRoom">' + ROOMS.filter(r => !r.archived).map(r => '<option value="' + esc(r.id) + '"' + (w.target === r.id ? ' selected' : '') + '>' + esc(r.title) + '</option>').join('') + '<option value="__new__"' + (w.target === '__new__' ? ' selected' : '') + '>＋ 新建会话</option></select></label>'
      + '<div id="connGuestNew"' + (w.target === '__new__' ? '' : ' hidden') + '><label>新会话标题<input id="connGuestTitle" maxlength="60" placeholder="例如：与朋友协作"></label></div>'
      + '<h4>此会话内的权限</h4><div id="connPermissions" class="perm-grid">' + renderPermissionChoices(w) + '</div>'
      + '<details class="connection-advanced"><summary>邀请地址（对方能打开的地址）</summary><label>接入地址<input id="connBase" value="' + esc(w.base) + '"></label><p class="hint" id="connBaseHint"></p></details>'
      + '<button id="connGuestGenerate" class="pri">生成邀请</button><div id="connGuestResult"></div>'
      + '<h4>邀请与游客</h4><div id="connInviteList">正在读取…</div>';
  } else if (w.type === 'local') {
    const local = localAgentChoices();
    w.localChoice = w.localChoice || (local.find(a => a.enabled) || {}).id || '__custom__';
    if (w.localChoice !== '__custom__' && !local.some(a => a.id === w.localChoice)) {
      w.localChoice = (local[0] || {}).id || '__custom__';
      w.id = ''; w.saved = false; w.status = null;
    }
    content += '<p class="hint">选择一个已检索到的程序。安装或卸载后可以重新检索。</p><button id="connRescan" type="button">重新检索已安装程序</button>'
      + '<div id="connProgramList">' + connectionProgramRows(local, w.localChoice, '手动添加 CLI 或 ACP 程序') + '</div>' + '<section id="connCustom"' + (w.localChoice === '__custom__' ? '' : ' hidden') + '><h4>手动填写程序</h4>' + connectionNameFields(w.localChoice === '__custom__' ? w : {...w, saved: false}) + '<label>协议类型<select id="connLocalDriver"><option value="cli"' + (w.form.localDriver !== 'acp' ? ' selected' : '') + '>无头命令行 (CLI)</option><option value="acp"' + (w.form.localDriver === 'acp' ? ' selected' : '') + '>ACP 协议 (Agent Client Protocol)</option></select></label><label>命令或可执行文件路径<input id="connCommand" placeholder="my-agent 或完整程序路径" value="' + esc(w.form.command || '') + '"></label><h4>调用参数</h4><p class="hint">每个参数单独添加，不需要引号或配置文件。</p><div id="connArgs">' + connectionArgsMarkup(w) + '</div></section><button id="connCheck" class="pri">检测并验证程序</button><p class="hint">检查程序是否可用；登录和模型权限将在首次回复时确认。</p>';
    if (!local.length) content += '<p class="hint">还没找到可以直接调用的命令行程序。安装并登录后，再回来检索。</p>';
    content += '<p><button type="button" id="connCustomHttp">连接自建 Harness 服务</button></p>';
  } else {
    content += connectionNameFields(w);
    if (w.type === 'direct') {
      const remote = agCat.local_workspace === false;
      content += remote ? '<p class="hint">请在运行 AnY 的设备上修改模型连接和 API Key。</p>' :
        '<label>模型服务地址<input id="connEndpoint" type="url" placeholder="https://api.openai.com/v1" value="' + esc(w.form.endpoint || '') + '"></label>'
        + '<label>模型名称<input id="connModelName" maxlength="200" placeholder="服务商提供的模型 ID" value="' + esc(w.form.model || '') + '"></label>'
        + '<label>API Key<input id="connServiceKey" type="password" autocomplete="off" placeholder="' + (w.saved ? '留空使用已保存的 Key' : '粘贴服务商提供的 Key') + '"></label>';
      content += '<p class="hint">这是文字模型。测试会发一句短消息，可能使用少量额度。加入会话后，讨论文字会发送给该服务商。</p><button id="connCheck" class="pri">测试模型回复</button>';
    } else if (w.type === 'http') {
      content += w.saved ? '<p class="hint">使用此联系人已保存的回调地址和服务密钥。</p>' : '<label>Harness 回调地址<input id="connEndpoint" placeholder="http://127.0.0.1:9100/bridge" value="' + esc(w.form.endpoint || '') + '"></label><label>服务密钥（可选）<input id="connServiceKey" type="password" autocomplete="off" value="' + esc(w.form.serviceKey || '') + '"></label>';
      content += '<p class="hint">测试会向服务发送一条只需简短回复的验证消息，可能消耗少量模型额度，不授予工具或文件权限。</p><button id="connCheck" class="pri">测试连接与回复</button><details class="connection-advanced"><summary>查看服务需要实现的协议</summary><p>接收 POST JSON，其中包含 prompt、speaker、mode、permissions。返回 <code>{"text":"连接成功"}</code>。</p></details>';
    } else {
      if (w.initialContact) {
        content += '<label>参与方式<select id="connMemberMode"><option value="auto"'+(w.memberMode !== 'manual'?' selected':'')+'>CLI 端 · 自动接收任务并回复</option><option value="manual"'+(w.memberMode === 'manual'?' selected':'')+'>桌面端 · 通过 MCP 参与</option></select></label>';
        content += '<label>接入地址<input id="connBase" value="' + esc(w.base) + '"></label><p class="hint" id="connBaseHint"></p>';
      } else {
        content += '<p class="hint">AnY 地址：<code>' + esc(w.base) + '</code></p>';
      }
      if (w.memberMode === 'manual') content += '<p><a href="' + ANY_MCP_PAGE + '" target="_blank" rel="noopener noreferrer">下载 AnY MCP 或复制配置提示词 ↗</a></p><p class="hint">在运行 Harness 的设备上按官网指引安装。生成接入密钥后，把这里显示的地址和密钥填入 Harness 的 MCP 设置。</p>';
      else content += '<p class="hint">在另一台设备打开成员连接端，导入这里生成的配置，再选择那台设备上的 CLI。</p>';
      content += '<button id="connGenerate" class="pri">' + (w.memberMode === 'manual' ? '生成 MCP 接入密钥' : '生成成员连接配置') + '</button>'
        + (w.status && w.status.has_key ? '<button id="connRevoke">撤销现有密钥 / 邀请</button><p class="hint">已有密钥不会再次显示明文；重新生成会使旧密钥和旧邀请失效。</p>' : '') + '<div id="connCredentials"></div>';
    }
  }
  if (['mydevice', 'user'].includes(w.type)) {
    content += '<div class="btns connection-actions"><button id="connNext" class="pri">完成</button></div>';
  } else {
    content += '<div id="connEvidence" class="connection-evidence" aria-live="polite"></div><div class="btns connection-actions">' + (w.type === 'direct' ? '' : '<button id="connLater">稍后验证，先分配会话</button>') + '<button id="connNext" class="pri" disabled>下一步：会话与权限</button></div>';
  }
  wizardFrame(w, content);
  if (document.getElementById('connLater')) document.getElementById('connLater').onclick = () => advanceConnection(w);
  document.getElementById('connNext').onclick = () => advanceConnection(w);
  if (w.type === 'mydevice') {
    renderDeviceSetup(w);
  }
  if (w.type === 'local') {
    const argsBox = document.getElementById('connArgs');
    if (argsBox) argsBox.onclick = event => {
      const remove = event.target.closest('[data-agent-remove]');
      if (remove) remove.closest('.agent-value-row').remove();
      const add = event.target.closest('[data-agent-add]');
      if (add) { const rows = argsBox.querySelector('[data-agent-rows]'); rows.insertAdjacentHTML('beforeend', agentListRow('')); rows.lastElementChild.querySelector('input').focus(); }
    };
    const driverChoice = document.getElementById('connLocalDriver');
    if (driverChoice) driverChoice.onchange = () => { captureConnectionForm(w); w.form.args = driverChoice.value === 'acp' ? ['acp'] : ['-p','{prompt}']; renderConnectionWizard(); };
    document.getElementById('connCustomHttp').onclick = () => {
      if (w.busy) return;
      w.id = ''; w.saved = false; w.status = null; w.form = {};
      connectionSetup(w, 'http');
    };
    const rescan = document.getElementById('connRescan');
    rescan.onclick = async () => {
      if (w.busy || w.scanning) return;
      captureConnectionForm(w);
      w.scanning = true;
      rescan.disabled = true;
      rescan.textContent = '正在检索…';
      try {
        await refreshContacts(w.controller.signal, true);
        if (wizardCurrent(w) && w.type === 'local' && w.step === 2 && !w.busy) {
          w.status = (agCat.connections || {})[w.id] || null;
          w.scanning = false;
          renderConnectionWizard();
        }
      } catch (error) { if (wizardCurrent(w)) wizardError('检索失败，请检查后台后重试。'); }
      finally { w.scanning = false; rescan.disabled = false; rescan.textContent = '重新检索已安装程序'; }
    };
    mbox.querySelectorAll('[data-conn-program]').forEach(button => {
      button.onclick = () => {
        if (w.busy || w.scanning || w.localChoice === button.dataset.connProgram) return;
        w.localChoice = button.dataset.connProgram;
        w.id = w.localChoice === '__custom__' ? '' : w.localChoice;
        w.saved = !!w.id; w.status = (agCat.connections || {})[w.id] || null; w.form = {};
        renderConnectionWizard();
        document.getElementById('connProgramList').querySelector('[aria-pressed="true"]')?.focus({preventScroll:true});
      };
    });
    if (w.localChoice !== '__custom__') { w.id = w.localChoice; w.saved = true; w.status = (agCat.connections || {})[w.id] || w.status; }
  }
  if (w.type === 'user') {
    renderGuestSetup(w);
  }
  const baseInput = document.getElementById('connBase');
  if (baseInput && w.type !== 'user') {
    const hint = document.getElementById('connBaseHint');
    const showBaseHint = () => {
      const issue = connectionBaseWarning(w.base);
      hint.textContent = issue || '这个地址必须能在朋友的电脑上打开。同一局域网可用局域网地址；跨网络需双方可达的 Tailscale 或 HTTPS 地址。HTTP 的消息和密钥未加密，避免在不可信网络使用。';
      hint.classList.toggle('warn', !!issue);
    };
    showBaseHint();
    baseInput.oninput = () => {
      w.base = baseInput.value.trim().replace(/\/+$/, '');
      showBaseHint();
      if (w.token) renderConnectionCredentials(w);
    };
  }
  const check = document.getElementById('connCheck'); if (check) check.onclick = () => checkConnection(w);
  if (w.type === 'direct') {
    for (const id of ['connEndpoint','connModelName','connServiceKey']) {
      const input = document.getElementById(id);
      if (input) input.oninput = () => updateConnectionEvidence(w);
    }
  }
  const generate = document.getElementById('connGenerate'); if (generate) generate.onclick = () => generateConnection(w);
  const revoke = document.getElementById('connRevoke'); if (revoke) revoke.onclick = async () => {
    if (w.busy || !confirm('撤销后，此联系人的现有密钥和邀请立即失效，继续？')) return;
    setConnectionBusy(w, true);
    try { const [ok, j] = await post('/api/contacts/key', {id:w.id, revoke:true}); if (!ok) throw Error(j.error || '撤销失败'); if (wizardCurrent(w)) { w.token = ''; w.member = {automatic:false}; w.status = {state:'unconfigured', label:'密钥已撤销', has_key:false}; renderConnectionWizard(); } }
    catch (e) { if (wizardCurrent(w)) wizardError(e.message); }
    finally { if (wizardCurrent(w)) setConnectionBusy(w, false); }
  };
  const memberMode = document.getElementById('connMemberMode');
  if (memberMode) memberMode.onchange = () => { captureConnectionForm(w); w.memberMode = memberMode.value; renderConnectionWizard(); };
  if (w.token) renderConnectionCredentials(w);
  updateConnectionEvidence(w);
  if (w.type === 'external' && w.id) w.timer = setInterval(() => pollConnectionEvidence(w), 2000);
}
function localAgentChoices() {
  return [...new Map([...CONTACTS, ...((agCat && agCat.discovered_presets) || [])]
    .filter(a => ['cli', 'acp', 'claude', 'codex'].includes(a.driver) && a.enabled && a.cli_available !== false).map(a => [a.id, a])).values()];
}
function captureConnectionForm(w) {
  const value = id => { const e = document.getElementById(id); return e ? e.value.trim() : undefined; };
  for (const [field, id] of Object.entries({label:'connName', id:'connId', localDriver:'connLocalDriver', command:'connCommand', endpoint:'connEndpoint', model:'connModelName', serviceKey:'connServiceKey', deviceName:'connDeviceName'})) {
    const v = value(id); if (v !== undefined) w.form[field] = v;
  }
  const args = document.getElementById('connArgs');
  if (args) w.form.args = [...args.querySelectorAll('[data-agent-value]')].map(input => input.value).filter(value => value !== '');
  if (document.getElementById('connBase')) w.base = value('connBase').replace(/\/+$/, '');
}
async function saveConnectionContact(w) {
  captureConnectionForm(w);
  if (w.saved && w.type !== 'direct') return;
  if (w.saved && !w.form.serviceKey) {
    if ((w.form.endpoint || '') !== w.directSaved.endpoint || w.form.model !== w.directSaved.model) {
      throw Error('修改服务地址或模型时，请重新填写 API Key');
    }
    return;
  }
  if (w.saved) w.form.label = (connectionContact(w) || {}).label;
  if (w.type === 'direct' && !w.form.label) w.form.label = (w.form.model || '').slice(0, 40);
  if (!w.form.label) throw Error('请填写联系人名称');
  const prefix = w.type === 'user' ? 'person' : w.type === 'local' ? 'agent' : w.type === 'direct' ? 'model' : 'harness';
  const id = w.saved ? w.id : w.form.id || prefix + '-' + crypto.getRandomValues(new Uint32Array(1))[0].toString(36);
  if (!w.saved && CONTACTS.some(a => a.id === id)) throw Error('此联系人 ID 已存在，请换一个或从联系人列表继续接入');
  const localDrv = w.form.localDriver === 'acp' ? 'acp' : 'cli';
  const spec = {id, label: w.form.label, kind: w.type === 'user' ? 'user' : 'agent', driver: ['user','external'].includes(w.type) ? 'external' : w.type === 'local' ? localDrv : 'http', enabled: true};
  if (w.type === 'local') {
    if (!w.form.command) throw Error('请填写程序命令或路径');
    const args = w.form.args || [];
    if (!Array.isArray(args) || !args.every(x => typeof x === 'string')) throw Error('请逐项填写启动参数');
    spec.bin = [w.form.command]; spec.args = localDrv === 'acp' ? {acp: args} : {base: args}; spec.context = 'full'; delete spec.enabled;
  }
  if (w.type === 'http') { const u = new URL(w.form.endpoint); if (!['http:','https:'].includes(u.protocol)) throw Error('回调地址必须以 http:// 或 https:// 开头'); spec.endpoint = w.form.endpoint; spec.token = w.form.serviceKey || ''; }
  if (w.type === 'direct') {
    if (!w.form.endpoint || !w.form.model || !w.form.serviceKey) throw Error('请填写模型服务地址、模型名称和 API Key');
    Object.assign(spec, {http_protocol:'openai_chat', endpoint:w.form.endpoint, token:w.form.serviceKey, default:[w.form.model, '']});
  }
  const [ok, j] = await post('/api/agents/add', {spec}); if (!ok) throw Error(j.error || '联系人保存失败');
  if (w.type === 'direct') {
    w.directSaved = {endpoint:w.form.endpoint, model:w.form.model};
    w.status = null;
    w.form.serviceKey = '';
    const input = wizardCurrent(w) && document.getElementById('connServiceKey');
    if (input) input.value = '';
  }
  w.id = id; w.saved = true; await refreshContacts();
}
function setConnectionBusy(w, busy) {
  w.busy = busy;
  if (!wizardCurrent(w)) return;
  mbox.querySelectorAll('button,input,select,textarea').forEach(e => { if (e.id !== 'connClose') e.disabled = busy; });
  if (!busy) updateConnectionEvidence(w);
  const assign = document.getElementById('connAssign'); if (assign) assign.disabled = busy || !!w.loadingAssignment;
}
async function checkConnection(w) {
  if (w.busy) return; wizardError(''); setConnectionBusy(w, true);
  try {
    if (w.type === 'local' && (agCat.discovered_presets || []).some(a => a.id === w.id)) {
      const [restored, result] = await post('/api/agents/restore', {id:w.id});
      if (!restored) throw Error(result.error || '恢复联系人失败');
      await refreshContacts();
    }
    await saveConnectionContact(w); if (!wizardCurrent(w)) return;
    const box = document.getElementById('connEvidence'); box.textContent = ['http','direct'].includes(w.type) ? '正在等待服务回复…' : '正在验证程序能否启动…';
    const [ok, j] = await post('/api/contacts/check', {id: w.id}); if (!ok) throw Error(j.error || '验证失败');
    if (!wizardCurrent(w)) return; w.status = j.connection;
    await refreshContacts(); if (!wizardCurrent(w)) return;
  } catch (e) { if (wizardCurrent(w)) wizardError(e.message || '验证失败，请重试'); }
  finally { if (wizardCurrent(w)) { setConnectionBusy(w, false); updateConnectionEvidence(w); } }
}
function updateConnectionEvidence(w) {
  const box = document.getElementById('connEvidence'); if (!box) return;
  let status = w.status || {state: 'unchecked', label: ['external','user'].includes(w.type) ? '等待生成连接配置' : '尚未验证'};
  const member = w.member || (agCat.members || {})[w.id];
  if (member && member.standby) status = {state:'connected', label:'MCP 待命中', detail:'已在软件内开启待命模式（'+member.device+'）。在会话中 @ 它即可派发任务。执行端按会话选择；离线后需手动切回本机程序。'};
  else if (w.type === 'external' && member && member.automatic) status = {state:'connected', label:'自动响应已连接', detail:'成员设备：'+member.device+'。被 @ 后会自动处理并回复原会话。'};
  else if (w.type === 'external' && status.state === 'connected') status = {...status, label:'消息通道已连接', detail:'可以手动参与；在该软件里输入 /any_standby 或开启成员连接端后，才能自动响应会议室任务。'};
  const address = document.getElementById('connEndpoint');
  const dirtyDirect = w.type === 'direct' && address && w.directSaved && (address.value.trim() !== w.directSaved.endpoint
    || document.getElementById('connModelName').value.trim() !== w.directSaved.model || !!document.getElementById('connServiceKey').value.trim());
  if (dirtyDirect) status = {state:'unchecked', label:'设置已改动，请重新测试'};
  const good = ['ready','connected'].includes(status.state) && !(w.type === 'external' && w.memberMode !== 'manual' && !(member && member.automatic));
  const extraBtns = [];
  if (member && member.standby) extraBtns.push('<button type="button" id="connStopStandby">停止待命</button>');
  if (w.id && w.type !== 'user' && w.type !== 'mydevice') extraBtns.push('<button type="button" id="connCustomHb">自定义此联系人的心跳与超时</button>');
  box.className = 'connection-evidence ' + (good ? 'success' : status.state === 'failed' ? 'failure' : 'pending');
  box.innerHTML = '<b>' + (good ? '✓ ' : '○ ') + esc(status.label) + '</b><p>' + esc(status.detail || (status.state === 'connected' ? '已收到对方的认证连接' + (status.client ? ' · ' + status.client : '') : ['external','user'].includes(w.type) ? '配置或复制邀请后仍需对方实际打开连接。此处会自动更新，无需手动确认。' : '验证结果会显示在这里。')) + '</p>' + (extraBtns.length ? '<div class="btns" style="justify-content:flex-start;margin-top:8px">' + extraBtns.join('') + '</div>' : '');
  const stopBtn = document.getElementById('connStopStandby');
  if (stopBtn) stopBtn.onclick = async () => {
    stopBtn.disabled = true;
    await post('/api/members/standby/stop', {id: w.id});
    await refreshContacts();
    w.member = (agCat.members || {})[w.id] || {automatic: false};
    updateConnectionEvidence(w);
  };
  const hbBtn = document.getElementById('connCustomHb');
  if (hbBtn) hbBtn.onclick = () => {
    const snapshot = snapshotConnectionWizard(w);
    if (typeof pushModalBack === 'function') pushModalBack(() => restoreConnectionWizard(snapshot));
    openConnectionSettingsModal(w.id);
  };
  const next = document.getElementById('connNext');
  if (next) next.disabled = w.busy || (!['user', 'mydevice'].includes(w.type) && !good);
}
async function pollConnectionEvidence(w) {
  if (!wizardCurrent(w) || w.step !== 2) { clearInterval(w.timer); return; }
  if (w.polling || w.busy) return; w.polling = true;
  try { const [ok, j] = await post('/api/contacts/status', {id: w.id}); if (ok && wizardCurrent(w) && w.step === 2) { w.status = j.connection; w.member = j.member; updateConnectionEvidence(w); } }
  catch (e) { if (wizardCurrent(w)) { w.status = {...w.status, state:'offline', label:'暂时无法获取连接状态'}; updateConnectionEvidence(w); } }
  finally { w.polling = false; }
}
function validConnectionBase(base) {
  try {
    const url = new URL(base);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password && !url.search && !url.hash && url.pathname === '/';
  } catch (error) { return false; }
}
async function generateConnection(w) {
  if (w.busy) return; wizardError(''); captureConnectionForm(w);
  if (!validConnectionBase(w.base)) { wizardError('请填写 AnY 根地址，例如 http://127.0.0.1:8765 或 https://bridge.example.com'); return; }
  if ((w.status && w.status.has_key || w.token) && !confirm('重新生成会使这个联系人的旧密钥和邀请立即失效，继续？')) return;
  setConnectionBusy(w, true);
  try {
    await saveConnectionContact(w); if (!wizardCurrent(w)) return;
    const [ok, j] = await post('/api/contacts/key', {id: w.id}); if (!ok) throw Error(j.error || '生成失败');
    if (!wizardCurrent(w)) return;
    w.token = j.token; w.member = {automatic:false}; w.status = {state: 'waiting', label: '等待对方连接', has_key: true};
    renderConnectionWizard();
  } catch (e) { if (wizardCurrent(w)) wizardError(e.message || '生成失败'); }
  finally { if (wizardCurrent(w)) setConnectionBusy(w, false); }
}
function connectionGuestUrl(base, token) {
  return base.replace(/\/+$/, '') + '/join#invite=' + encodeURIComponent(token);
}
function connectionInviteStatus(invite) {
  if (!invite || invite.revoked) return '已撤销';
  if (!invite.expires || invite.expires * 1000 < Date.now()) return '已过期';
  if (invite.guest_count) return '已加入 ' + invite.guest_count + ' 位游客';
  return '等待加入';
}
async function renderGuestSetup(w) {
  const select = document.getElementById('connGuestRoom');
  const newBox = document.getElementById('connGuestNew');
  if (select) select.onchange = () => {
    w.target = select.value;
    newBox.hidden = w.target !== '__new__';
  };
  const baseInput = document.getElementById('connBase');
  const hint = document.getElementById('connBaseHint');
  const showHint = () => {
    const issue = connectionBaseWarning(w.base);
    hint.textContent = issue || '游客的手机/电脑要能打开这个地址。跨网络需要你提供双方可达的地址。';
    hint.classList.toggle('warn', !!issue);
  };
  if (baseInput) {
    showHint();
    baseInput.oninput = () => { w.base = baseInput.value.trim().replace(/\/+$/, ''); showHint(); };
  }
  const generate = document.getElementById('connGuestGenerate');
  if (generate) generate.onclick = () => generateGuestInvite(w);
  if (w.inviteUrl) renderGuestInviteResult(w);
  await loadGuestInvites(w);
  if (wizardCurrent(w) && w.step === 2) w.timer = setInterval(() => pollGuestInvites(w), 3000);
}
async function loadGuestInvites(w) {
  try {
    const [ok, data] = await connectionGet('/api/invites');
    if (!ok) throw Error(data.error || '读取邀请失败');
    w.invites = data.invites || [];
    renderGuestInviteList(w);
  } catch (error) {
    const box = document.getElementById('connInviteList');
    if (box) box.textContent = error.message;
  }
}
function renderGuestInviteResult(w) {
  const box = document.getElementById('connGuestResult');
  if (!box) return;
  const issue = connectionBaseWarning(w.base);
  box.innerHTML = (issue ? '<p class="hint connection-base-warning">' + esc(issue) + ' 先换一个对方能打开的地址。</p>' : '')
    + '<input id="connGuestUrl" readonly aria-label="邀请链接"><button id="connGuestCopy">复制邀请链接</button>'
    + (issue ? '' : '<div id="connGuestQr" class="connection-qr" aria-label="邀请二维码"></div>');
  document.getElementById('connGuestUrl').value = w.inviteUrl;
  document.getElementById('connGuestCopy').onclick = async event => { await copyText(w.inviteUrl); event.target.textContent = '已复制'; };
  if (!issue) renderConnectionQrUrl('connGuestQr', w.inviteUrl);
}
function renderGuestInviteList(w) {
  const box = document.getElementById('connInviteList');
  if (!box) return;
  box.innerHTML = (w.invites || []).map(invite => {
    const room = ROOMS.find(r => r.id === invite.room);
    return '<div class="connection-invite"><span><b>' + esc((room || {}).title || invite.room) + '</b><small>'
      + esc(connectionInviteStatus(invite)) + ' · 创建于 ' + new Date((invite.created || 0) * 1000).toLocaleString()
      + ' · 有效至 ' + new Date((invite.expires || 0) * 1000).toLocaleString() + '</small>'
      + (invite.guests || []).map(guest => '<small class="connection-guest">' + esc(guest.label) + ' · ' + esc(guest.device || '设备未知') + (guest.online ? ' · 在线' : '') + ' <button data-guest-remove="' + esc(guest.id) + '">移除</button></small>').join('')
      + '</span>' + (invite.revoked ? '' : '<button data-invite-revoke="' + esc(invite.id) + '">撤销邀请</button>') + '</div>';
  }).join('') || '<p class="hint">还没有邀请。生成后会出现在这里。</p>';
  box.querySelectorAll('[data-invite-revoke]').forEach(button => {
    button.onclick = () => revokeGuestInvite(w, button.dataset.inviteRevoke);
  });
  box.querySelectorAll('[data-guest-remove]').forEach(button => {
    button.onclick = () => removeGuest(w, button.dataset.guestRemove);
  });
}
async function pollGuestInvites(w) {
  if (!wizardCurrent(w) || w.step !== 2) { clearInterval(w.timer); return; }
  await loadGuestInvites(w);
}
async function generateGuestInvite(w) {
  if (w.busy) return;
  wizardError('');
  w.permissions = Object.fromEntries([...mbox.querySelectorAll('[data-connection-permission]')].map(i => [i.dataset.connectionPermission, i.checked]));
  const title = document.getElementById('connGuestTitle');
  setConnectionBusy(w, true);
  try {
    if (w.target === '__new__') {
      const [ok, created] = await post('/api/rooms/new', {
        project: (PROJECTS[0] || {}).id || '', title: (title && title.value.trim()) || '与朋友协作', participants: []
      });
      if (!ok) throw Error(created.error || '会话创建失败');
      w.target = created.id;
      await pollRooms();
    }
    const [ok, data] = await post('/api/invites', {
      room: w.target, permissions: w.permissions, label: '游客邀请', expires_days: 7, base: w.base
    });
    if (!ok) throw Error(data.error || '邀请生成失败');
    w.inviteUrl = data.url || connectionGuestUrl(w.base, data.token);
    w.step = 2;
    renderConnectionWizard();
  } catch (error) {
    if (wizardCurrent(w)) wizardError(error.message);
  } finally {
    if (wizardCurrent(w)) setConnectionBusy(w, false);
  }
}
async function revokeGuestInvite(w, id) {
  if (!confirm('撤销后，这张邀请不能再兑换；已加入的游客不受影响。继续？')) return;
  const [ok, data] = await post('/api/invites/revoke', {id});
  if (!ok) return wizardError(data.error || '撤销失败');
  await loadGuestInvites(w);
}
async function removeGuest(w, id) {
  if (!confirm('移除后，这位游客会退出所有会话，密钥立即失效。继续？')) return;
  const [ok, data] = await post('/api/guests/remove', {id});
  if (!ok) return wizardError(data.error || '移除失败');
  await loadGuestInvites(w);
}
function connectionDeviceName(value) { return (value || '').trim() || '我的设备'; }
function connectionDeviceUrl(base, code) { return base.replace(/\/+$/, '') + '/enroll#code=' + encodeURIComponent(code); }
function renderConnectionCredentials(w) {
  const box = document.getElementById('connCredentials'); if (!box || !w.token) return;
  if (w.memberMode !== 'manual') {
    box.innerHTML = '<ol class="connection-instructions"><li>下载下方的成员连接端和连接配置，通过可信渠道把两个文件发给朋友。</li><li>朋友解压连接端：Windows 双击 start-member.bat；Mac 双击 start-member.command（需要 Python 3.11 和 Tk）。</li><li>朋友导入连接配置，选择自己电脑上的 Harness 和工作文件夹，点击「连接并开启自动响应」。</li><li>这里显示「自动响应已连接」后，选择会话与权限。成员随后能接收任务、回复和互相 @。</li></ol><p><a href="/static/member-connector.zip" download="AnY-Member.zip">下载成员连接端（Windows / macOS 源码包）</a></p><button id="connDownloadMember" class="pri">下载此成员的连接配置</button><button id="connCopyMember">复制连接配置</button><p class="hint">连接配置含成员密钥，只发给对应朋友，不要公开。跨网络需要朋友能够访问上面的地址；不会自动组网，也无需开放朋友电脑的入站端口。</p>';
    const profile = JSON.stringify({protocol:1, server:w.base, key:w.token, member:w.id},null,2);
    document.getElementById('connCopyMember').onclick = () => copyText(profile);
    document.getElementById('connDownloadMember').onclick = () => { const url=URL.createObjectURL(new Blob([profile],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='ai-bridge-'+w.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000); };
  } else {
    box.innerHTML = '<label>MCP 地址<input id="connMcpUrl" readonly></label><button type="button" id="connCopyMcpUrl">复制地址</button>'
      + '<label>联系人接入密钥<input id="connRawKey" readonly></label><button type="button" id="connCopyKey">复制密钥</button>'
      + '<p class="hint">按安装说明把地址和密钥分别填入 AI_BRIDGE_URL 和 AI_BRIDGE_TOKEN。重新加载 MCP，然后让 Harness 调用 list_rooms。分配会话后，就能验证它是否看得到该会话。</p>';
    const url = w.base + '/mcp';
    document.getElementById('connMcpUrl').value = url;
    document.getElementById('connRawKey').value = w.token;
    document.getElementById('connCopyMcpUrl').onclick = () => copyText(url);
    document.getElementById('connCopyKey').onclick = () => copyText(w.token);
  }
}
async function advanceConnection(w) {
  if (w.type === 'user' || w.type === 'mydevice') { connectionLeaveModal(); refreshContacts(); loadState(); return; }
  if (w.busy) return; wizardError(''); setConnectionBusy(w, true);
  try {
    await saveConnectionContact(w); await pollRooms(); if (!wizardCurrent(w)) return;
    w.target = w.target || RID || (ROOMS.find(r => !r.archived) || {}).id || '__new__';
    w.project = w.project || (PROJECTS[0] || {}).id || '__new__'; w.step = 3; renderConnectionWizard();
  } catch (e) { if (wizardCurrent(w)) wizardError(e.message); }
  finally { if (wizardCurrent(w)) setConnectionBusy(w, false); }
}
function renderPermissionChoices(w) {
  if (w.type === 'user') {
    return HUMAN_ROOM_PERM_GROUPS.map(g => '<label><input type="checkbox" data-connection-permission="' + g.id + '"' + (w.permissions[g.id] ? ' checked' : '') + '><span>' + esc(g.label) + '<small class="perm-sub">' + esc(g.hint) + '</small></span></label>').join('');
  }
  if (w.type === 'direct') return '<p class="hint">这个模型只参与房间文字讨论。</p>';
  if (typeof PERM_GROUPS !== 'undefined' && typeof groupPermValue === 'function') {
    return PERM_GROUPS.map(g => '<label><input type="checkbox" data-connection-permission-group="' + g.id + '"' + (groupPermValue(w.permissions, g) ? ' checked' : '') + '><span>' + esc(g.label) + '<small class="perm-sub">' + esc(g.hint) + '</small></span></label>').join('');
  }
  return Object.entries(PERM_LABELS).map(([key, label]) => '<label><input type="checkbox" data-connection-permission="' + key + '"' + (w.permissions[key] ? ' checked' : '') + '>' + label + '</label>').join('');
}
function renderConnectionAssignment(w) {
  const contact = connectionContact(w) || {label: w.id};
  wizardFrame(w, '<h3>让' + esc(contact.label) + '加入哪个会话？</h3><p class="hint">该联系人只会加入你选择的会话。其他会话的成员和权限保持独立。</p><label>会话<select id="connRoom">' + ROOMS.filter(r => !r.archived || r.id === w.target).map(r => '<option value="' + esc(r.id) + '"' + (w.target === r.id ? ' selected' : '') + '>' + esc(((PROJECTS.find(p => p.id === r.project) || {}).name || '项目') + ' / ' + r.title) + '</option>').join('') + '<option value="__new__"' + (w.target === '__new__' ? ' selected' : '') + '>＋ 新建会话</option></select></label><div id="connNewRoom"' + (w.target === '__new__' ? '' : ' hidden') + '><label>所属项目<select id="connProject">' + PROJECTS.map(p => '<option value="' + esc(p.id) + '"' + (w.project === p.id ? ' selected' : '') + '>' + esc(p.name) + '</option>').join('') + '<option value="__new__"' + (w.project === '__new__' ? ' selected' : '') + '>＋ 新建项目</option></select></label><div id="connNewProject"' + (w.project === '__new__' ? '' : ' hidden') + '><label>项目名称<input id="connProjectName" maxlength="60" placeholder="例如：我的项目"></label><label>项目工作文件夹<input id="connWorkdir" placeholder="已存在的文件夹完整路径" value="' + esc((agCat && agCat.default_dir) || '') + '"></label></div><label>会话标题<input id="connRoomTitle" maxlength="60" placeholder="例如：与 ' + esc(contact.label) + ' 协作"></label></div><h4>此会话内的权限</h4><div id="connPermissions" class="perm-grid">' + renderPermissionChoices(w) + '</div><p class="hint">干活还需会话切换到干活模式。CLI / 外部 Harness 的文件与命令权限由其自身环境落实。</p><div class="btns connection-actions"><button id="connAssignmentBack">返回连接设置</button><button id="connSaveOnly">仅保留联系人，暂不加入</button><button id="connAssign" class="pri">保存并加入会话</button></div>');
  attachWorkspaceFolderPicker('connWorkdir');
  document.getElementById('connRoom').onchange = () => updateConnectionAssignment(w);
  document.getElementById('connProject').onchange = e => { w.project = e.target.value; document.getElementById('connNewProject').hidden = w.project !== '__new__'; };
  document.getElementById('connAssignmentBack').onclick = () => connectionBack(w);
  document.getElementById('connSaveOnly').onclick = () => { w.assigned = false; w.step = 4; renderConnectionWizard(); };
  document.getElementById('connAssign').onclick = () => assignConnection(w);
  updateConnectionAssignment(w);
}
async function updateConnectionAssignment(w) {
  const seq = (w.assignmentSeq || 0) + 1; w.assignmentSeq = seq;
  w.target = document.getElementById('connRoom').value;
  document.getElementById('connNewRoom').hidden = w.target !== '__new__';
  if (w.target === '__new__') { w.loadingAssignment = false; w.permissions = {read:true,post:true,trigger:true,board:false,files:false,work:false,...((connectionContact(w) || {}).default_permissions || {})}; document.getElementById('connPermissions').innerHTML = renderPermissionChoices(w); document.getElementById('connAssign').disabled = w.busy; return; }
  w.loadingAssignment = true;
  const save = document.getElementById('connAssign'); save.disabled = true;
  try {
    const r = await fetch('/api/r/' + encodeURIComponent(w.target) + '/state'); const state = await r.json(); if (!r.ok) throw Error(state.error || '读取会话失败');
    if (!wizardCurrent(w) || w.assignmentSeq !== seq || w.step !== 3) return;
    w.permissions = (state.permissions || {})[w.id] || {read:true,post:true,trigger:true,board:false,files:false,work:false,...((connectionContact(w) || {}).default_permissions || {})};
    w.loadingAssignment = false; document.getElementById('connPermissions').innerHTML = renderPermissionChoices(w); save.disabled = w.busy;
  } catch (e) { if (wizardCurrent(w) && w.assignmentSeq === seq) wizardError(e.message); }
}
async function assignConnection(w) {
  if (w.busy) return;
  const groupBoxes = [...mbox.querySelectorAll('[data-connection-permission-group]')];
  if (w.type === 'direct') {
    w.permissions = {read:true,post:true,trigger:false,board:false,files:false,work:false};
  } else if (groupBoxes.length && typeof expandGroupedPerms === 'function') {
    w.permissions = expandGroupedPerms(Object.fromEntries(groupBoxes.map(i => [i.dataset.connectionPermissionGroup, i.checked])));
  } else {
    w.permissions = Object.fromEntries([...mbox.querySelectorAll('[data-connection-permission]')].map(i => [i.dataset.connectionPermission, i.checked]));
  }
  const roomTitle = document.getElementById('connRoomTitle').value.trim() || '与' + (connectionContact(w) || {}).label + '协作';
  const projectName = document.getElementById('connProjectName').value.trim(), workdir = document.getElementById('connWorkdir').value.trim();
  setConnectionBusy(w, true); wizardError('');
  try {
    if (w.target === '__new__') {
      if (w.project === '__new__') {
        const [ok, j] = await post('/api/projects/new', {name: projectName, workdir}); if (!ok) throw Error(j.error || '项目创建失败');
        w.project = j.project.id;
        if (!wizardCurrent(w)) return;
      }
      const [ok, j] = await post('/api/rooms/new', {project: w.project, title: roomTitle, participants: []}); if (!ok) throw Error(j.error || '会话创建失败');
      w.target = j.id;
      if (!wizardCurrent(w)) return;
      if (wizardCurrent(w)) { const select = document.getElementById('connRoom'); select.add(new Option(roomTitle, j.id)); select.value = j.id; }
    }
    const [ok, j] = await post('/api/r/' + encodeURIComponent(w.target) + '/invite', {contact: w.id, permissions: w.permissions}); if (!ok) throw Error(j.error || '邀请失败');
    await pollRooms(); await refreshContacts(); if (!wizardCurrent(w)) return;
    w.assigned = true; w.status = (agCat.connections || {})[w.id] || w.status; w.step = 4; renderConnectionWizard();
  } catch (e) { if (wizardCurrent(w)) wizardError(e.message); }
  finally { if (wizardCurrent(w)) setConnectionBusy(w, false); }
}
function renderConnectionComplete(w) {
  const finishWizard = async () => {
    if (typeof hasModalBack === 'function' && hasModalBack()) {
      connectionLeaveModal();
      refreshContacts();
      if (typeof loadState === 'function') loadState();
    } else {
      hideModal();
      refreshContacts();
      loadState();
    }
  };
  const contact = connectionContact(w) || {label:w.id}, room = ROOMS.find(r => r.id === w.target);
  const automatic = w.type === 'external' && ((w.member || (agCat.members||{})[w.id] || {}).automatic);
  const good = automatic || w.status && ['ready','connected'].includes(w.status.state);
  const connectionLabel = automatic ? '自动响应已连接：可与本机成员一样接收任务并回复' : w.type === 'external' ? '成员已保存。消息通道与自动响应状态可在联系人中查看。' : good ? w.status.label : '联系人已保存，尚未完成连接验证。可以稍后从联系人列表继续接入。';
  const permSummary = (typeof PERM_GROUPS !== 'undefined' && typeof groupPermValue === 'function')
    ? PERM_GROUPS.filter(g => groupPermValue(w.permissions, g)).map(g => esc(g.label)).join('、')
    : Object.entries(PERM_LABELS).filter(([k]) => w.permissions[k]).map(([,label]) => esc(label)).join('、');
  wizardFrame(w, '<div class="connection-complete"><span class="connection-symbol">✓</span><h3>' + (w.assigned ? '已加入会话' : '联系人已添加') + '</h3><p><b>' + esc(contact.label) + '</b>' + (w.assigned ? ' · ' + esc((room || {}).title || '') : '') + '</p><p class="hint">' + esc(connectionLabel) + '</p>' + (w.assigned ? '<p class="hint">权限：' + (permSummary || '仅查看') + '</p>' : '') + '</div><div class="btns"><button id="connDone">完成</button>' + (w.assigned ? '<button id="connEnter" class="pri">进入会话</button>' : '') + '</div>');
  document.getElementById('connDone').onclick = finishWizard;
  const enter = document.getElementById('connEnter'); if (enter) enter.onclick = () => { const rid = w.target; hideModal(); switchRoom(rid); };
}

async function openDiscoveryModal(forceRescan = false) {
  stopConnectionWizard();
  document.body.classList.remove('nav-open');
  const canBack = typeof hasModalBack === 'function' && hasModalBack();
  showModal('<div id="discoveryModal"><h3>正在扫描本机 Agent…</h3><p class="hint" role="status">正在检索命令行、ACP 程序、桌面软件与 MCP 配置。</p><div class="btns">' + (canBack ? '<button type="button" id="discLoadingBack">返回</button>' : '') + '<button onclick="hideModal()">关闭</button></div></div>');
  const loadingBack = canBack && document.getElementById('discLoadingBack');
  if (loadingBack) loadingBack.onclick = () => popModalBack();
  const [ok, disc] = forceRescan ? await post('/api/discovery/scan', {}) : await connectionGet('/api/discovery');
  if (!ok || !disc) {
    showModal('<h3>扫描失败</h3><p role="alert">' + esc((disc && disc.error) || '无法读取本机扫描结果') + '</p><div class="btns">' + (canBack ? '<button type="button" id="discErrBack">返回</button>' : '') + '<button onclick="hideModal()">关闭</button></div>');
    const errBack = canBack && document.getElementById('discErrBack');
    if (errBack) errBack.onclick = () => popModalBack();
    return;
  }
  await refreshContacts();
  renderDiscoveryModal(disc);
}

function renderDiscoveryModal(disc) {
  const canBack = typeof hasModalBack === 'function' && hasModalBack();
  const detected = (disc && disc.detected) || [];
  const rows = detected.map(item => {
    const member = ((agCat || {}).members || {})[item.id] || {};
    const direct = item.level === 'direct';
    const desktop = item.level === 'mcp' || item.kind === 'desktop' || item.kind === 'both';
    const label = member.standby ? 'MCP 待命中' : member.automatic ? '自动响应端在线' : direct && item.connected ? 'CLI 已验证' : item.mcp_installed ? 'MCP 已配置，等待待命' : '已检测，待配置';
    const actions = (direct ? '<button data-disc-config="'+esc(item.id)+'" data-via="'+esc(item.via)+'">配置 CLI</button>' : '')
      + (desktop && item.mcp_host ? '<button data-disc-config="'+esc(item.id)+'" data-via="mcp">配置桌面 / MCP</button>' : '')
      + (item.level === 'unsupported' ? '<span class="hint">暂未适配自动接入</span>' : '');
    return '<div class="disc-row agent-room-row"><div><b>'+esc(item.label)+'</b> <small>@'+esc(item.id)+'</small><p class="hint">'+esc(label)+'</p><small>'+esc(item.exe || item.desktop_path || '')+'</small></div><div class="btns">'+actions+'</div></div>';
  }).join('');
  showModal('<div id="discoveryModal"><div class="connection-heading">'+(canBack?'<button type="button" class="modal-back" id="discBack">← 返回</button>':'')+'<span class="eyebrow">本机 Agent 自动发现</span><button id="discClose" aria-label="关闭">×</button></div><h3>在这台电脑上发现 '+detected.length+' 个 Agent</h3><p class="hint">CLI 走直连；桌面配置 MCP 后开启 /any_standby，以真实心跳保持接入。扫描只提供候选程序，所有修改均进入同一个 Agent 设置页。</p>'+rows+'<p id="discError" role="alert"></p><div class="btns"><button id="discRescan">重新扫描</button><button id="discManual">手动添加</button><button id="discDone" class="pri">完成</button></div></div>');
  const current = document.getElementById('discoveryModal');
  if (canBack && document.getElementById('discBack')) document.getElementById('discBack').onclick = () => popModalBack();
  document.getElementById('discClose').onclick = hideModal;
  document.getElementById('discDone').onclick = () => { if (canBack) popModalBack(); else hideModal(); };
  document.getElementById('discRescan').onclick = () => openDiscoveryModal(true);
  document.getElementById('discManual').onclick = () => { if (typeof pushModalBack === 'function') pushModalBack(() => openDiscoveryModal(false)); startConnectionWizard(); };
  mbox.querySelectorAll('[data-disc-config]').forEach(button => button.onclick = async () => {
    button.disabled = true;
    try {
      const [ok,result] = await post('/api/discovery/prepare',{id:button.dataset.discConfig,via:button.dataset.via});
      if(document.getElementById('discoveryModal')!==current)return;
      if(!ok)throw Error(result.error || '无法准备 Agent 设置');
      await refreshContacts();
      if(document.getElementById('discoveryModal')===current){
        if (typeof pushModalBack === 'function') pushModalBack(() => openDiscoveryModal(false));
        openAgentSettings(result.id,result.tab);
      }
    } catch(error) { if(document.getElementById('discoveryModal')===current)document.getElementById('discError').textContent=error.message; }
    finally { button.disabled=false; }
  });
}

async function openConnectionSettingsModal(contactId = '') {
  stopConnectionWizard();
  document.body.classList.remove('nav-open');
  const canBack = typeof hasModalBack === 'function' && hasModalBack();
  const finish = () => { if (canBack) popModalBack(); else hideModal(); };
  const [ok, snap] = await connectionGet('/api/settings/connection');
  if (!ok || !snap) {
    showModal('<h3>无法读取连接与心跳设置</h3><div class="btns">' + (canBack ? '<button type="button" id="hbErrBack">返回</button>' : '') + '<button onclick="hideModal()">关闭</button></div>');
    const errBack = canBack && document.getElementById('hbErrBack');
    if (errBack) errBack.onclick = () => popModalBack();
    return;
  }
  const pid = contactId || '';
  const fields = snap.fields || {};
  const current = pid ? {...snap.global, ...((snap.contacts || {})[pid] || {})} : (snap.global || {});
  const hasOverride = pid && snap.contacts && snap.contacts[pid] && Object.keys(snap.contacts[pid]).length > 0;
  const order = ['heartbeat_interval', 'offline_after', 'long_poll', 'standby_poll', 'standby_max', 'task_timeout_discuss', 'task_timeout_work', 'reconnect', 'reconnect_max', 'idle_reap'];
  const inputsHtml = order.filter(k => fields[k]).map(k => {
    const f = fields[k];
    if (k === 'reconnect') {
      return '<label>' + esc(f.label) + '<select data-hb-field="' + k + '"><option value="1"' + (current[k] ? ' selected' : '') + '>开启（掉线后自动退避重连）</option><option value="0"' + (!current[k] ? ' selected' : '') + '>关闭</option></select></label>';
    }
    return '<label>' + esc(f.label) + ' <small class="hint">(' + f.min + '–' + f.max + '，默认 ' + f.default + ')</small><input type="number" data-hb-field="' + k + '" min="' + f.min + '" max="' + f.max + '" value="' + esc(current[k]) + '"></label>';
  }).join('');
  showModal('<div id="connSettingsModal"><div class="connection-heading">' + (canBack ? '<button type="button" class="modal-back" id="hbBack">← 返回</button>' : '') + '<span class="eyebrow">AnY 统一管控</span><button id="hbClose" aria-label="关闭">×</button></div>'
    + '<h3>' + (pid ? '联系人心跳与超时设置（@' + esc(pid) + '）' : '全局连接与心跳设置') + '</h3>'
    + '<p class="hint">所有参数保存在 AnY 端并自动下发给成员连接端、MCP 待命端和本机常驻进程，正在运行的连接端会在下一次心跳时自动同步。</p>'
    + (pid ? '<p class="hint">' + (hasOverride ? '当前使用此联系人的独立覆盖配置。' : '当前继承全局默认设置；保存后将仅对此联系人单独生效。') + '</p>' : '')
    + '<div class="hb-grid">' + inputsHtml + '</div>'
    + '<p id="hbError" role="alert"></p>'
    + '<div class="btns"><button type="button" id="hbCancel">取消</button>'
    + (pid && hasOverride ? '<button type="button" id="hbReset">恢复继承全局设置</button>' : '')
    + '<button type="button" id="hbSave" class="pri">保存设置</button></div></div>');
  if (canBack && document.getElementById('hbBack')) document.getElementById('hbBack').onclick = () => popModalBack();
  document.getElementById('hbClose').onclick = hideModal;
  document.getElementById('hbCancel').onclick = finish;
  const resetBtn = document.getElementById('hbReset');
  if (resetBtn) resetBtn.onclick = async () => {
    await post('/api/settings/connection', {id: pid, clear_contact: true});
    await refreshContacts();
    finish();
  };
  document.getElementById('hbSave').onclick = async e => {
    const btn = e.currentTarget;
    btn.disabled = true;
    const values = {};
    mbox.querySelectorAll('[data-hb-field]').forEach(inp => {
      values[inp.dataset.hbField] = Number(inp.value);
    });
    const body = pid ? {id: pid, contact: values} : {global: values};
    const [savedOk, res] = await post('/api/settings/connection', body);
    btn.disabled = false;
    if (!savedOk) {
      document.getElementById('hbError').textContent = (res && res.error) || '保存失败';
      return;
    }
    await refreshContacts();
    finish();
  };
}
