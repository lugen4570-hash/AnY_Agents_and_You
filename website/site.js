document.documentElement.classList.add('has-js');

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const topbar = document.querySelector('[data-topbar]');
if (topbar) {
  const syncTopbar = () => topbar.classList.toggle('scrolled', window.scrollY > 12);
  syncTopbar();
  window.addEventListener('scroll', syncTopbar, { passive: true });
}

const revealItems = [...document.querySelectorAll('.reveal')];
if (revealItems.length) {
  if ('IntersectionObserver' in window && !reducedMotion) {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -24px 0px' }
    );
    for (const item of revealItems) observer.observe(item);
  } else {
    for (const item of revealItems) item.classList.add('is-visible');
  }
}

const stage = document.querySelector('[data-stage]');
if (stage) {
  const scenarios = {
    discuss: {
      active: ['antigravity', 'codex'],
      prompt: '@Claude @Gemini 继续补充各自视角，或在看板确认分工…',
      messages: [
        {
          role: 'human',
          name: '你 · 议题发起人',
          text: '请 @Antigravity 梳理现有鉴权链路，@Codex 和 @Claude 先各给一版重构意见，不要急着改文件。',
        },
        {
          role: 'ai',
          name: 'Antigravity',
          initial: 'A',
          color: '#6022e8',
          meta: '只读梳理 · 上下文 24%',
          text: '已定位 3 处中间件与令牌校验入口，调用图和风险边界已发在看板里，请 @Codex 评估拆分方案。',
        },
        {
          role: 'ai',
          name: 'Codex',
          initial: 'X',
          color: '#10a37f',
          meta: '方案评审 · 就绪',
          text: '建议先抽离无状态校验层再迁移会话表，回归面最小。请 @Claude 复核并发刷新竞态。',
        },
      ],
    },
    debate: {
      active: ['claude', 'gemini'],
      prompt: '论道第 2 轮完成，可点「总结收尾」形成可执行待办…',
      messages: [
        {
          role: 'ai',
          name: 'Claude',
          initial: 'C',
          color: '#d97757',
          meta: '第 1 轮 · 架构视角',
          text: '并发刷新竞态建议用单飞锁 + 短宽限期，避免全量锁阻塞正常读写请求。',
        },
        {
          role: 'ai',
          name: 'Gemini',
          initial: 'G',
          color: '#2563eb',
          meta: '第 2 轮 · 边界反驳',
          text: '补充离线成员与长连接重连场景：宽限期需按设备指纹隔离，否则跨设备成员会话会互挤。',
        },
        {
          role: 'ai',
          name: 'Cursor',
          initial: 'R',
          color: '#7c3aed',
          meta: '第 2 轮 · 测试补充',
          text: '同意双方结论，已整理 4 条回归用例草案发给 @你 确认后即可切到干活模式。',
        },
      ],
    },
    work: {
      active: ['codex', 'antigravity'],
      prompt: '干活模式 · 文件护栏已锁定 auth_guard.py，空闲 Agent 可随时切模型',
      messages: [
        {
          role: 'human',
          name: '你 · 已切换干活模式',
          text: '按讨论结论执行：@Codex 负责 `auth_guard.py` 与单元测试，@Antigravity 负责成员会话隔离检查。',
        },
        {
          role: 'ai',
          name: 'Codex',
          initial: 'X',
          color: '#10a37f',
          meta: '干活中 · 已锁定 auth_guard.py',
          text: '私有 Git 快照已拍取。已完成单飞锁重构并跑通 18 项校验，请 @OpenCode 复查终端边界。',
        },
        {
          role: 'ai',
          name: 'Antigravity',
          initial: 'A',
          color: '#6022e8',
          meta: '空闲 · 模型可独立切换',
          text: '成员会话隔离与设备指纹检查无回归，所有改动支持在右侧面板按步撤回。',
        },
      ],
    },
  };

  const tabs = [...stage.querySelectorAll('[data-scenario]')];
  const caps = [...stage.querySelectorAll('[data-agent-cap]')];
  const feed = stage.querySelector('[data-stage-feed]');
  const promptEl = stage.querySelector('[data-stage-prompt]');
  const keys = Object.keys(scenarios);
  let current = 'discuss';
  let timer = null;
  let paused = false;

  function buildMessageRow(item) {
    const row = document.createElement('div');
    if (item.role === 'human') {
      row.className = 'msg-row human';
      const bubble = document.createElement('div');
      bubble.className = 'msg-bubble';
      const small = document.createElement('small');
      small.textContent = item.name;
      bubble.append(small, document.createTextNode(item.text));
      row.appendChild(bubble);
      return row;
    }
    row.className = 'msg-row ai';
    const avatar = document.createElement('span');
    avatar.className = 'msg-avatar';
    avatar.style.setProperty('--c', item.color);
    avatar.textContent = item.initial;

    const body = document.createElement('div');
    body.className = 'msg-body';
    const header = document.createElement('header');
    const b = document.createElement('b');
    b.textContent = item.name;
    const span = document.createElement('span');
    span.textContent = item.meta;
    header.append(b, span);

    const p = document.createElement('p');
    p.textContent = item.text;
    body.append(header, p);
    row.append(avatar, body);
    return row;
  }

  function renderScenario(key) {
    const data = scenarios[key];
    if (!data || !feed) return;
    current = key;
    for (const tab of tabs) {
      tab.setAttribute('aria-selected', String(tab.dataset.scenario === key));
    }
    for (const cap of caps) {
      cap.classList.toggle('is-active', data.active.includes(cap.dataset.agentCap));
    }
    feed.replaceChildren(...data.messages.map(buildMessageRow));
    if (promptEl) promptEl.textContent = data.prompt;
  }

  for (const tab of tabs) {
    tab.addEventListener('click', () => {
      paused = true;
      if (timer) clearInterval(timer);
      renderScenario(tab.dataset.scenario);
    });
  }

  renderScenario(current);

  if (!reducedMotion) {
    stage.addEventListener('mouseenter', () => { paused = true; });
    stage.addEventListener('mouseleave', () => { paused = false; });
    stage.addEventListener('focusin', () => { paused = true; });
    stage.addEventListener('focusout', () => { paused = false; });
    timer = window.setInterval(() => {
      if (paused) return;
      const next = keys[(keys.indexOf(current) + 1) % keys.length];
      renderScenario(next);
    }, 7000);
  }
}

async function copyElementText(targetEl, statusEl, okText, fallbackText) {
  const text = targetEl.textContent;
  try {
    await navigator.clipboard.writeText(text);
    if (statusEl) statusEl.textContent = okText;
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(targetEl);
    selection?.removeAllRanges();
    selection?.addRange(range);
    if (statusEl) statusEl.textContent = fallbackText;
  }
}

const gitBtn = document.querySelector('[data-copy-git]');
const gitCmd = document.querySelector('#git-command');
const gitStatus = document.querySelector('[data-copy-git-status]');
if (gitBtn && gitCmd) {
  gitBtn.addEventListener('click', () => {
    copyElementText(gitCmd, gitStatus, '已复制克隆与启动命令，粘贴到终端即可运行。', '命令已选中，可按 Ctrl+C 复制。');
  });
}

const views = [...document.querySelectorAll('.download-view')];
const navigation = [...document.querySelectorAll('[data-view]')];
if (views.length) {
  function showView() {
    const requested = window.location.hash.slice(1);
    const selected = requested === 'cli' ? 'cli' : 'desktop';
    for (const view of views) view.hidden = view.id !== selected;
    for (const link of navigation) {
      if (link.dataset.view === selected) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    }
  }
  showView();
  window.addEventListener('hashchange', showView);
}

const installer = document.querySelector('[data-installer]');
if (installer) {
  const command = installer.querySelector('[data-command]');
  const status = document.querySelector('[data-copy-status]');
  const platformButtons = [...installer.querySelectorAll('[data-platform]')];
  const posixCommand = command.textContent;

  function selectPlatform(platform) {
    command.textContent = platform === 'windows' ? posixCommand.replace(/^python3/, 'py -3') : posixCommand;
    for (const button of platformButtons) {
      button.setAttribute('aria-pressed', String(button.dataset.platform === platform));
    }
    if (status) status.textContent = '';
  }

  const device = navigator.userAgentData?.platform || navigator.userAgent;
  selectPlatform(/Windows/i.test(device) ? 'windows' : 'posix');
  for (const button of platformButtons) {
    button.addEventListener('click', () => selectPlatform(button.dataset.platform));
  }
  installer.querySelector('[data-copy]').addEventListener('click', () => {
    copyElementText(command, status, '已复制。粘贴到终端后按回车。', '命令已选中，可手动复制。');
  });
}
