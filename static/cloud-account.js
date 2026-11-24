/* Optional account and preference synchronization. Cloud credentials stay in the local backend. */
(() => {
  const fields = ['theme', 'language'];
  const labels = { theme: '外观主题', language: '界面语言' };
  const messages = {
    device_limit: '登录设备已达上限。请在已登录的设备上移除一台，再试一次。',
    invalid_code: '验证码有误或已过期，请核对后再试。',
    phone_taken: '这个手机号已绑定到其他测试账号。',
    sms_wait: '验证码已发送，请等待 60 秒后重试。',
    sms_failed: '测试短信暂时未能发送。',
    channel_unavailable: '该登录通道暂未开放。',
    invalid_request: '请核对填写的内容。',
    cloud_unavailable: '暂时无法连接云服务，稍后会重试。',
  };
  let pane, hooks, caps, session, socket, socketKey, heartbeat, topicRef = 0;
  let qrTimer, qrGeneration = 0, codeUntil = 0, syncTimer, syncRunning = false;
  let selected = 'wechat', snapshot, profile, conflict, status = '';
  let signedOutMessage = '';

  function currentView() {
    return pane?.isConnected && pane.closest('#modal')?.classList.contains('show');
  }

  function say(message) {
    status = message;
    const output = currentView() && pane.querySelector('[role="status"]');
    if (output) output.textContent = message;
  }

  function closeSocket() {
    clearInterval(heartbeat);
    socket?.close();
    socket = null;
    socketKey = null;
  }

  function signedOut(message) {
    session = null;
    snapshot = null;
    conflict = null;
    profile = null;
    caps && (caps.signed_in = false);
    signedOutMessage = message;
    closeSocket();
    if (currentView()) render();
  }

  async function api(action, data = {}) {
    let result;
    try {
      const response = await fetch('/api/cloud/account', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...data, action }),
      });
      result = await response.json();
    } catch (_) {
      result = { error: 'cloud_unavailable' };
    }
    if (result.error === 'signed_out' && (session || caps?.signed_in)) {
      signedOut('此设备的云账号已退出，可以继续使用本地功能。');
    }
    return result;
  }

  function watchSession(next) {
    if (!next.realtime || !next.topic || !next.realtime.startsWith('wss://')) return;
    const key = next.realtime + '|' + next.topic;
    if (key === socketKey) return;
    closeSocket();
    try {
      const channel = 'realtime:' + next.topic;
      const ws = new WebSocket(next.realtime);
      socket = ws;
      socketKey = key;
      function send(topic, event, payload) {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ topic, event, payload, ref: String(++topicRef) }));
      }
      ws.addEventListener('open', () => {
        send(channel, 'phx_join', { config: { broadcast: { self: false, ack: false }, private: false } });
        heartbeat = setInterval(() => send('phoenix', 'heartbeat', {}), 25000);
        void verifySession();
      });
      ws.addEventListener('message', ({ data }) => {
        try {
          const msg = JSON.parse(data);
          if (msg.topic === channel && msg.event === 'broadcast' && msg.payload?.event === 'session_changed') {
            void verifySession();
          }
        } catch (_) {}
      });
      ws.addEventListener('close', () => {
        if (socket === ws) closeSocket();
      });
    } catch (_) {
      closeSocket();
    }
  }

  function profileKey(account) { return 'any-cloud-preferences:' + account; }

  function readProfile(account) {
    try {
      const saved = JSON.parse(localStorage.getItem(profileKey(account)));
      if (saved?.enabled && saved.pending && saved.baseline) return saved;
    } catch (_) {}
    return { enabled: false, pending: {}, baseline: {} };
  }

  function saveProfile() {
    if (!session || !profile) return;
    try { localStorage.setItem(profileKey(session.account), JSON.stringify(profile)); } catch (_) {}
  }

  async function verifySession() {
    const next = await api('session');
    if (next.error) return false;
    if (!session || session.account !== next.account) {
      profile = readProfile(next.account);
      snapshot = null;
      conflict = null;
    }
    session = next;
    caps.signed_in = true;
    watchSession(next);
    return true;
  }

  function applySnapshot(remote) {
    snapshot = remote;
    profile.baseline = remote.preferences;
    saveProfile();
    for (const key of fields) {
      if (!(key in profile.pending) && key in remote.preferences) hooks.apply(key, remote.preferences[key]);
    }
  }

  function scheduleSync(delay = 400) {
    clearTimeout(syncTimer);
    syncTimer = setTimeout(() => void sync(), delay);
  }

  async function sync() {
    if (!session || !profile?.enabled || syncRunning || conflict) return;
    const owner = session.account;
    const local = profile;
    syncRunning = true;
    const changes = { ...local.pending };
    try {
      const remote = await api('preferences');
      if (owner !== session?.account || local !== profile) return;
      if (remote.error) {
        say(messages[remote.error] || '同步暂时中断。');
        scheduleSync(15000);
        return;
      }
      // Rebase edits to different fields. Keep same-field conflicts for the user to resolve.
      const colliding = fields.filter(key => changes[key] &&
        (remote.preferences[key] ?? null) !== changes[key].base &&
        remote.preferences[key] !== changes[key].value);
      if (colliding.length) {
        conflict = { remote, fields: colliding };
        say('另一台设备也修改了' + colliding.map(key => labels[key]).join('、') + '。请选择保留哪一份。');
        if (currentView()) showSyncControls();
        return;
      }
      const patch = Object.fromEntries(Object.entries(changes).map(([key, change]) => [key, change.value]));
      const result = Object.keys(patch).length
        ? await api('sync', { version: remote.version, preferences: patch })
        : remote;
      if (owner !== session?.account || local !== profile) return;
      if (result.error) {
        if (result.error !== 'conflict') say(messages[result.error] || '同步暂时中断。');
        scheduleSync(result.error === 'conflict' ? 500 : 15000);
        return;
      }
      for (const key of Object.keys(changes)) {
        if (profile.pending[key] === changes[key]) delete profile.pending[key];
        else if (profile.pending[key]) profile.pending[key].base = result.preferences[key] ?? null;
      }
      applySnapshot(result);
      if (Object.keys(profile.pending).length) scheduleSync();
      else if (Object.keys(changes).length) say('偏好已同步。');
    } finally {
      syncRunning = false;
    }
  }

  function enqueue(key, value) {
    if (!session || !profile?.enabled || !fields.includes(key)) return;
    const previous = profile.pending[key];
    profile.pending[key] = { value, base: previous ? previous.base : profile.baseline[key] ?? null };
    saveProfile();
    scheduleSync();
  }

  function permission() {
    if (!pane.querySelector('[data-consent]')?.checked) {
      say('请先阅读并勾选用户协议和隐私政策，再继续登录。');
      pane.querySelector('[data-consent]')?.focus();
      return null;
    }
    return { consent: caps.consent_version };
  }

  async function beginQR() {
    const accepted = permission();
    if (!accepted) return;
    const generation = ++qrGeneration;
    clearTimeout(qrTimer);
    say('正在生成微信二维码…');
    const res = await api('qr_create', accepted);
    if (!currentView() || generation !== qrGeneration) return;
    if (!res.attempt) return say(messages[res.error] || '二维码暂时无法生成，请刷新重试。');
    const qr = pane.querySelector('[data-qr]');
    const image = qr.querySelector('img');
    if (res.image?.startsWith('https://mp.weixin.qq.com/cgi-bin/showqrcode?')) {
      image.src = res.image;
      image.hidden = false;
    } else {
      image.removeAttribute('src');
      image.hidden = true;
    }
    say('请用微信扫描二维码。');
    async function poll() {
      if (!currentView() || generation !== qrGeneration) return;
      if (Date.now() >= Date.parse(res.expires)) return say('二维码已过期，请点击刷新。');
      const result = await api('qr_poll', { attempt: res.attempt });
      if (generation !== qrGeneration) return;
      if (result.signed_in) return await loginComplete();
      if (result.status === 'expired') return say('二维码已过期，请点击刷新。');
      if (result.error && result.error !== 'cloud_unavailable') return say(messages[result.error] || '登录未完成，请刷新重试。');
      if (result.status === 'scanned') say('已扫码，请在微信中确认登录。');
      if (result.error) say('暂时无法获取扫码状态，正在重试。');
      qrTimer = setTimeout(poll, 1800);
    }
    qrTimer = setTimeout(poll, 1000);
  }

  async function loginComplete() {
    caps.signed_in = true;
    signedOutMessage = '';
    status = '';
    if (await verifySession() && currentView()) render();
  }

  function showSMS(bind) {
    const form = pane.querySelector('[data-sms-form]');
    form.hidden = false;
    form.innerHTML = '<label>手机号<input name="phone" type="tel" autocomplete="tel" placeholder="+86 及手机号" required></label>'
      + '<label>验证码<input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6"></label>'
      + '<button type="button" data-send-code>获取验证码</button>'
      + '<button type="submit" class="pri">' + (bind ? '绑定手机号' : '登录') + '</button>';
    const send = form.querySelector('[data-send-code]');
    function countdown() {
      if (!send.isConnected || !currentView()) return;
      const remaining = Math.max(0, Math.ceil((codeUntil - Date.now()) / 1000));
      send.disabled = remaining > 0;
      send.textContent = remaining ? remaining + ' 秒后重发' : '获取验证码';
      if (remaining) setTimeout(countdown, 250);
    }
    const phoneNumber = () => form.elements.phone.value.replace(/[ -]/g, '');
    send.onclick = async () => {
      const accepted = permission();
      if (!accepted) return;
      send.disabled = true;
      const result = await api('sms_send', { ...accepted, phone: phoneNumber() });
      if (result.retry_after || result.error === 'sms_wait') codeUntil = Date.now() + 60000;
      countdown();
      say(result.ok ? '验证码已发送。' : (messages[result.error] || '发送失败。'));
    };
    form.onsubmit = async event => {
      event.preventDefault();
      const accepted = permission();
      if (!accepted) return;
      const code = form.elements.code.value.trim();
      if (!/^\d{6}$/.test(code)) return say('请输入 6 位验证码。');
      const submit = form.querySelector('[type="submit"]');
      submit.disabled = true;
      const result = await api(bind ? 'sms_bind' : 'sms_verify', { ...accepted, phone: phoneNumber(), code });
      if (result.signed_in || result.ok) await loginComplete();
      else say(messages[result.error] || '验证码校验失败。');
      submit.disabled = false;
    };
    countdown();
  }

  const consent = '<label class="cloud-consent"><input type="checkbox" data-consent>我已阅读并同意'
    + ' <a href="/static/cloud-terms.html" target="_blank" rel="noopener">用户协议</a>及'
    + ' <a href="/static/cloud-privacy.html" target="_blank" rel="noopener">隐私政策</a></label>';

  function showSyncControls() {
    const box = currentView() && pane.querySelector('[data-sync]');
    if (!box || !profile) return;
    box.innerHTML = profile.enabled
      ? '<button type="button" data-pause-sync>暂停同步</button>'
      : '<button type="button" class="pri" data-enable-sync>同意同步偏好</button>';
    if (!profile.enabled) {
      box.querySelector('button').onclick = async () => {
        const localProfile = profile;
        const remote = await api('preferences');
        if (remote.error || profile !== localProfile || !profile) {
          if (remote.error !== 'signed_out') say(messages[remote.error] || '暂时无法读取云偏好。');
          return;
        }
        profile.enabled = true;
        applySnapshot(remote);
        if (remote.version === 0) for (const key of fields) enqueue(key, hooks.read(key));
        say(remote.version ? '已恢复云端偏好。' : '正在同步当前偏好。');
        showSyncControls();
      };
    } else {
      box.querySelector('button').onclick = () => {
        profile = { enabled: false, pending: {}, baseline: {} };
        conflict = null;
        saveProfile();
        showSyncControls();
        say('已暂停同步。');
      };
    }
    if (!conflict) return;
    box.insertAdjacentHTML('beforeend', '<div class="cloud-actions"><button type="button" data-keep>保留此设备的修改</button>'
      + '<button type="button" data-use-cloud>使用云端修改</button></div>');
    function resolve(keep) {
      const pending = conflict;
      for (const key of pending.fields) {
        if (keep) profile.pending[key].base = pending.remote.preferences[key] ?? null;
        else delete profile.pending[key];
      }
      conflict = null;
      saveProfile();
      say('正在同步…');
      showSyncControls();
      scheduleSync(0);
    }
    box.querySelector('[data-keep]').onclick = () => resolve(true);
    box.querySelector('[data-use-cloud]').onclick = () => resolve(false);
  }

  async function showDevices() {
    const list = currentView() && pane.querySelector('[data-devices]');
    if (!list) return;
    const available = await api('devices');
    if (!list.isConnected || !currentView()) return;
    if (!Array.isArray(available.devices)) {
      if (available.error !== 'signed_out') say(messages[available.error] || '无法读取登录设备。');
      return;
    }
    list.replaceChildren();
    pane.querySelector('[data-device-limit]').textContent = '已登录 ' + available.devices.length + ' / ' + available.limit + ' 台设备';
    for (const row of available.devices) {
      const item = document.createElement('li');
      const name = document.createElement('span');
      name.textContent = row.name + (row.current ? '（当前设备）' : '');
      item.append(name);
      if (row.current) pane.querySelector('[data-device-name]').elements.name.value = row.name;
      else {
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = '下线';
        remove.setAttribute('aria-label', '下线 ' + row.name);
        remove.onclick = async () => {
          remove.disabled = true;
          const result = await api('revoke', { id: row.id });
          if (result.ok) {
            await showDevices();
            say('设备已下线。');
          } else {
            remove.disabled = false;
            say(messages[result.error] || '下线失败。');
          }
        };
        item.append(remove);
      }
      list.append(item);
    }
  }

  function render() {
    clearTimeout(qrTimer);
    qrGeneration += 1;
    if (!caps?.enabled) {
      pane.innerHTML = '<section class="settings-group"><h4>微信扫码</h4><p class="hint">云账号暂未开放。你可以直接使用本地协作。</p></section>';
      return;
    }
    if (session) {
      pane.innerHTML = '<p class="hint">测试环境</p><section class="settings-group"><h4>登录设备</h4><p class="hint" data-device-limit></p>'
        + '<form class="cloud-actions" data-device-name><label>此设备名称<input name="name" maxlength="60" required></label>'
        + '<button type="submit">保存名称</button></form><ul class="cloud-devices" data-devices></ul></section>'
        + '<section class="settings-group"><h4>偏好同步</h4><p class="hint">同步外观主题与界面语言。云端已有偏好时，本机将采用云端设置。</p>'
        + '<div data-sync></div></section>'
        + (caps.sms && !session.phone_bound ? '<details class="settings-group"><summary>绑定手机号</summary>'
          + consent + '<form class="cloud-actions" data-sms-form></form></details>' : '')
        + '<button type="button" data-logout>退出云账号</button><p class="hint" role="status"></p>';
      const nameForm = pane.querySelector('[data-device-name]');
      nameForm.onsubmit = async event => {
        event.preventDefault();
        const result = await api('rename', { name: nameForm.elements.name.value });
        if (result.ok) await showDevices();
        if (result.error !== 'signed_out') say(result.ok ? '设备名称已保存。' : messages[result.error] || '名称未保存。');
      };
      pane.querySelector('[data-logout]').onclick = async () => {
        const result = await api('logout');
        if (result.ok) signedOut('已退出云账号。');
        else if (result.error !== 'signed_out') say(messages[result.error] || '暂时无法退出，请重试。');
      };
      if (caps.sms && !session.phone_bound) showSMS(true);
      showSyncControls();
      void showDevices();
      say(status);
      return;
    }
    pane.innerHTML = '<section class="settings-group"><div class="settings-segmented" data-channels>'
      + '<button type="button" data-channel="wechat">微信扫码</button>'
      + (caps.sms ? '<button type="button" data-channel="sms">手机号登录</button>' : '')
      + '</div><p class="hint">测试环境 · 也可继续免登录使用 AnY。</p>' + consent
      + '<div class="cloud-qr" data-qr hidden><img alt="微信登录二维码" width="176" height="176" hidden>'
      + '<button type="button" data-refresh-qr>获取二维码 / 刷新</button></div>'
      + '<form class="cloud-actions" data-sms-form hidden></form><p class="hint" role="status"></p></section>';
    const qr = pane.querySelector('[data-qr]');
    qr.hidden = selected !== 'wechat' || !caps.wechat;
    pane.querySelectorAll('[data-channel]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.channel === selected));
      button.onclick = () => {
        selected = button.dataset.channel;
        render();
      };
    });
    if (!qr.hidden) pane.querySelector('[data-refresh-qr]').onclick = beginQR;
    if (selected === 'sms') showSMS(false);
    say(signedOutMessage || (selected === 'wechat' && !caps.wechat ? '微信扫码暂未开放。' : ''));
  }

  async function mount(element) {
    pane = element;
    selected = 'wechat';
    pane.innerHTML = '<p class="hint" role="status">正在加载账号设置…</p>';
    const ready = await api('capabilities');
    if (pane !== element || !currentView()) return;
    if (ready.error) {
      say(messages[ready.error] || '请在运行 AnY 的设备上打开账号设置。');
      return;
    }
    caps = ready;
    if (ready.signed_in) await verifySession();
    if (pane === element && currentView()) render();
  }

  async function tick() {
    if (caps?.signed_in && await verifySession()) {
      if (profile?.enabled) scheduleSync(0);
    }
  }

  window.anyCloudAccount = {
    mount,
    setPreference: enqueue,
    start(integration) {
      hooks = integration;
      void api('capabilities').then(result => {
        if (result.enabled && !caps) {
          caps = result;
          void tick();
        }
      });
      setInterval(() => void tick(), 30000);
      window.addEventListener('online', () => void tick());
      window.addEventListener('focus', () => void tick());
    },
  };
})();
