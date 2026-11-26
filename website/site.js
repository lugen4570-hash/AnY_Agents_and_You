document.documentElement.classList.add('has-js');

const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');

const topbar = document.querySelector('.topbar');
if (topbar) {
  const canvas = document.createElement('canvas');
  canvas.className = 'signal-rain';
  canvas.setAttribute('aria-hidden', 'true');
  document.body.prepend(canvas);

  const toggle = document.createElement('button');
  toggle.type = 'button';
  toggle.className = 'signal-motion-toggle';
  toggle.setAttribute('aria-label', '背景动效');
  toggle.innerHTML = '<svg viewBox="0 0 16 16" aria-hidden="true"><path class="signal-pause" d="M4 3h2.5v10H4zm5.5 0H12v10H9.5z"/><path class="signal-play" d="M5 2.5 13 8l-8 5.5Z"/></svg>';
  topbar.after(toggle);

  const aiStrings = [
    '0xA7F2E4', '01101001', '::MCP->AI', '∀x∈λ(ctx)', 'SHA256:09',
    '{diff:0x3E}', 'fn(agent)', '0x7F8B1C', '10110100', '0xE4A832',
  ];
  const humanPhrases = [
    '先讨论再动手', '为什么这么改', '我来确认', '换个思路',
    '对齐目标', '一起看看', '等等看这里', '按步撤回',
  ];
  const ctx = canvas.getContext('2d');
  let drops = [];
  let clusters = [];
  let width = 0;
  let height = 0;
  let dpr = 1;
  let rafId = 0;
  let lastTick = 0;
  let paused = false;

  try { paused = sessionStorage.getItem('any-signal-paused') === 'yes'; } catch {}

  function pickClusters() {
    const clusterCount = width < 640 ? 2 : 3;
    clusters = Array.from({ length: clusterCount }, () => (0.1 + Math.random() * 0.8) * width);
  }

  function pickDropX(startY, prewarm, excludeIndex) {
    const pad = 18;
    const usable = Math.max(40, width - pad * 2);
    const spread = width < 640 ? 64 : 120;
    let chosen = pad + Math.random() * usable;

    for (let attempt = 0; attempt < 5; attempt++) {
      let candidate;
      if (clusters.length && Math.random() < 0.56) {
        const center = clusters[Math.floor(Math.random() * clusters.length)];
        candidate = center + (Math.random() + Math.random() - 1) * spread;
      } else {
        candidate = pad + Math.random() * usable;
      }
      candidate = Math.max(pad, Math.min(width - pad, candidate));
      const crowded = drops.some((other, idx) => {
        if (idx === excludeIndex || !other) return false;
        if (Math.abs(other.x - candidate) >= 20) return false;
        return prewarm ? Math.abs(other.y - startY) < 130 : other.y < 150;
      });
      chosen = candidate;
      if (!crowded) break;
    }
    return chosen;
  }

  function createDrop(index, prewarm) {
    const isHuman = Math.random() < 0.25;
    const step = isHuman ? (20 + Math.random() * 4) : (16 + Math.random() * 5);
    const source = isHuman
      ? humanPhrases[Math.floor(Math.random() * humanPhrases.length)]
      : aiStrings[Math.floor(Math.random() * aiStrings.length)];
    const trail = isHuman ? 5 + Math.floor(Math.random() * 6) : 6 + Math.floor(Math.random() * 11);
    const paceRoll = Math.random();
    const baseSpeed = paceRoll < 0.36
      ? (20 + Math.random() * 22)
      : (paceRoll < 0.78 ? (46 + Math.random() * 44) : (102 + Math.random() * 72));
    const depth = 0.42 + Math.random() * 0.58;
    const speed = (isHuman ? Math.min(baseSpeed, 112) : baseSpeed) * (0.72 + depth * 0.36);
    const span = height + trail * step + 260;
    const startY = prewarm
      ? Math.random() * span - trail * step * 0.45
      : -(Math.random() * 420 + 30);
    const chars = Array.from({ length: trail + 1 }, (_, r) => source[r % source.length]);
    return {
      x: pickDropX(startY, prewarm, index),
      y: startY,
      step,
      trail,
      speed,
      depth,
      isHuman,
      chars,
    };
  }

  function layoutDrops() {
    width = window.innerWidth;
    height = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.floor(width * dpr));
    canvas.height = Math.max(1, Math.floor(height * dpr));
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    pickClusters();
    const dropCount = Math.max(7, Math.round(width / (width < 640 ? 54 : 62)));
    drops = [];
    for (let i = 0; i < dropCount; i++) {
      drops.push(createDrop(i, true));
    }
  }

  function drawFrame(dtSeconds) {
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    const dimFactor = motionPreference.matches ? 0.42 : 1;

    for (let i = 0; i < drops.length; i++) {
      const d = drops[i];
      if (dtSeconds > 0) {
        d.y += d.speed * dtSeconds;
        if (d.y - d.trail * d.step > height + 36) {
          drops[i] = createDrop(i, false);
          continue;
        }
      }

      ctx.font = d.isHuman
        ? `500 ${Math.round(11 + d.depth * 2)}px "Segoe UI","PingFang SC","Microsoft YaHei",sans-serif`
        : `600 ${Math.round(12 + d.depth * 2)}px "Cascadia Code",ui-monospace,Consolas,monospace`;

      for (let t = 0; t <= d.trail; t++) {
        const py = d.y - t * d.step;
        if (py < -d.step || py > height + d.step) continue;
        const ch = d.chars[(d.trail - t) % d.chars.length];
        const progress = 1 - t / (d.trail + 1);
        const alpha = Math.pow(progress, 1.55) * (d.isHuman ? 0.46 : 0.78) * d.depth * dimFactor;
        if (alpha < 0.02) continue;

        if (t === 0) {
          ctx.shadowBlur = d.isHuman ? 7 : 11;
          ctx.shadowColor = d.isHuman ? 'rgba(183, 208, 220, 0.65)' : 'rgba(244, 207, 108, 0.85)';
          ctx.fillStyle = d.isHuman
            ? `rgba(230, 240, 248, ${Math.min(0.88, alpha + 0.14)})`
            : `rgba(255, 245, 204, ${Math.min(0.94, alpha + 0.12)})`;
        } else {
          ctx.shadowBlur = 0;
          if (d.isHuman) {
            ctx.fillStyle = `rgba(168, 198, 222, ${alpha.toFixed(3)})`;
          } else if (t <= 3) {
            ctx.fillStyle = `rgba(244, 207, 108, ${alpha.toFixed(3)})`;
          } else {
            ctx.fillStyle = `rgba(228, 168, 50, ${(alpha * 0.85).toFixed(3)})`;
          }
        }
        ctx.fillText(ch, d.x, py);
      }
      ctx.shadowBlur = 0;
    }
  }

  function step(now) {
    if (paused || motionPreference.matches) {
      rafId = 0;
      return;
    }
    const dt = lastTick ? Math.min(0.06, (now - lastTick) / 1000) : 0.016;
    lastTick = now;
    if (!document.hidden) drawFrame(dt);
    rafId = window.requestAnimationFrame(step);
  }

  function syncField() {
    document.documentElement.toggleAttribute('data-motion-paused', paused);
    toggle.setAttribute('aria-pressed', String(!paused));
    toggle.title = paused ? '播放页面动效' : '暂停页面动效';
    if (paused || motionPreference.matches) {
      if (rafId) {
        window.cancelAnimationFrame(rafId);
        rafId = 0;
      }
      lastTick = 0;
      drawFrame(0);
    } else if (!rafId) {
      lastTick = 0;
      rafId = window.requestAnimationFrame(step);
    }
  }

  layoutDrops();
  drawFrame(0);
  syncField();

  window.addEventListener('resize', () => {
    layoutDrops();
    drawFrame(0);
  });
  motionPreference.addEventListener('change', syncField);
  toggle.addEventListener('click', () => {
    paused = !paused;
    try { sessionStorage.setItem('any-signal-paused', paused ? 'yes' : 'no'); } catch {}
    syncField();
  });
}
const stage = document.querySelector('[data-stage]');
if (stage) {
  const scenarios = {
    discuss: {
      targets: ['Antigravity', 'Codex'],
      caption: '两位 Agent 在同一场会话里接上彼此的思路。',
      active: ['antigravity', 'codex'],
      prompt: '@Claude 帮忙补充跨设备测试。',
      messages: [
        ['你', '发起讨论', '@Antigravity 梳理登录流程，@Codex 看看哪里可以简化。先讨论。'],
        ['Antigravity', '流程梳理', '登录和设备连接各有一套检查，我把入口整理到了看板。'],
        ['Codex', '方案建议', '可以先把共用校验抽出来，让登录和设备连接各自调用。'],
      ],
    },
    debate: {
      targets: ['论道共识'],
      caption: '围绕一个问题分轮发言，再收拢成共识。',
      active: ['claude', 'kimi'],
      prompt: '/debate 选择议题与参与者',
      messages: [
        ['你', '论道议题', '手机和电脑同时在线时，草稿该怎么保存？'],
        ['Claude', '第 1 轮', '把草稿按设备保存，每台设备都可以继续上次的编辑。'],
        ['Kimi Code', '第 2 轮', '同意。还要验证切回原设备时，能找回刚才粘贴的图片。'],
        ['Claude', '共识', '草稿按设备保存，并把图片恢复加进回归检查。'],
      ],
    },
    work: {
      targets: ['安装包', '官网下载'],
      caption: '两位 Agent 并行核查，最后一步由你确认。',
      active: ['codex', 'claude'],
      prompt: '确认后继续…',
      messages: [
        ['你', '发任务', '@Codex 查安装包能不能启动，@Claude 核对官网下载。'],
        ['Codex', '检查安装包', '已装好并启动，可以创建会话，也能正常退出。'],
        ['Claude', '核对下载', '安装版和便携版都能下载，校验值一致。'],
        ['系统', '等待确认', 'Codex 请求替换官网首页的工作台截图。'],
      ],
    },
  };

  const scenariosButtons = [...stage.querySelectorAll('[data-scenario]')];
  const viewButtons = [...stage.querySelectorAll('[data-stage-view]')];
  const caps = [...stage.querySelectorAll('[data-agent-cap]')];
  const feed = stage.querySelector('[data-stage-feed]');
  const prompt = stage.querySelector('[data-stage-prompt]');
  const poster = stage.closest('[data-poster]');
  const caption = stage.querySelector('[data-poster-caption]');
  const signalTargets = stage.querySelector('[data-signal-targets]');
  const signalLines = [...stage.querySelectorAll('.signal-line')];
  const signalBeads = [...stage.querySelectorAll('[data-signal-bead]')];
  const replay = stage.querySelector('[data-stage-replay]');
  const light = stage.querySelector('.stage-light');
  let transitions = [];
  const colors = new Map(caps.map((chip) => [
    chip.textContent.trim(), chip.style.getPropertyValue('--dot'),
  ]));

  function renderMessage([name, status, text]) {
    const row = document.createElement('div');
    row.className = name === '你' ? 'msg-row human' : name === '系统' ? 'msg-row approval' : 'msg-row ai';
    if (colors.has(name)) row.style.setProperty('--agent-color', colors.get(name));

    const header = document.createElement('header');
    const speaker = document.createElement('b');
    const meta = document.createElement('span');
    const message = document.createElement('p');
    speaker.textContent = name;
    meta.textContent = status;
    message.textContent = text;
    header.append(speaker);
    if (row.classList.contains('ai')) {
      const badge = document.createElement('span');
      badge.className = 'speaker-kind';
      badge.textContent = 'AI';
      header.append(badge);
    }
    header.append(meta);
    row.append(header, message);
    return row;
  }

  function renderScenario(key) {
    const { active, messages, prompt: nextPrompt, caption: nextCaption, targets } = scenarios[key];
    stage.dataset.scenarioMode = key;
    poster.dataset.scene = key;
    for (const button of scenariosButtons) {
      button.setAttribute('aria-pressed', String(button.dataset.scenario === key));
    }
    for (const chip of caps) {
      chip.classList.toggle('is-active', active.includes(chip.dataset.agentCap));
    }
    feed.replaceChildren(...messages.map(renderMessage));
    prompt.textContent = nextPrompt;
    caption.textContent = nextCaption;
    signalTargets.replaceChildren(...targets.map((target) => {
      const node = document.createElement('span');
      node.className = 'signal-node';
      node.textContent = target;
      return node;
    }));
  }

  function clearMotion() {
    for (const animation of transitions) animation.cancel();
    transitions = [];
  }

  function playSignal() {
    if (motionPreference.matches || !stage.animate ||
        document.documentElement.hasAttribute('data-motion-paused')) return;
    const paths = signalLines.filter((line) => line.dataset.signal === poster.dataset.scene);
    for (const [index, path] of paths.entries()) {
      const bead = signalBeads[index];
      const travel = bead.querySelector('animateMotion');
      if (!travel?.beginElement) continue;
      travel.setAttribute('path', path.getAttribute('d'));
      travel.beginElement();
      transitions.push(bead.animate(
        [{ opacity: 0 }, { opacity: 1, offset: .12 }, { opacity: 1, offset: .84 }, { opacity: 0 }],
        { duration: 920 },
      ));
    }
  }

  function playCut() {
    clearMotion();
    if (motionPreference.matches || !feed.animate) return;
    const easing = 'cubic-bezier(.22,1,.36,1)';
    playSignal();
    transitions.push(
      light.animate(
        [{ opacity: .12 }, { opacity: .84, offset: .5 }, { opacity: .48 }],
        { duration: 900, easing },
      ),
      signalTargets.animate(
        [{ boxShadow: '0 0 0 0 currentColor' }, { boxShadow: '0 0 0 10px transparent' }],
        { duration: 400, delay: 710, easing },
      ),
    );
    for (const [index, row] of [...feed.children].entries()) {
      transitions.push(row.animate(
        [{ opacity: .18, transform: 'translateY(9px)' }, { opacity: 1, transform: 'translateY(0)' }],
        { delay: 180 + index * 220, duration: 380, easing, fill: 'backwards' },
      ));
    }
  }

  const syncMotion = () => {
    clearMotion();
    replay.hidden = motionPreference.matches || !feed.animate;
  };
  motionPreference.addEventListener('change', syncMotion);
  replay.addEventListener('click', playCut);
  syncMotion();
  for (const button of scenariosButtons) {
    button.addEventListener('click', () => {
      if (button.getAttribute('aria-pressed') === 'true') return;
      renderScenario(button.dataset.scenario);
      playCut();
    });
  }
  for (const button of viewButtons) {
    button.addEventListener('click', () => {
      if (button.getAttribute('aria-pressed') === 'true') return;
      stage.dataset.view = button.dataset.stageView;
      for (const view of viewButtons) {
        view.setAttribute('aria-pressed', String(view === button));
      }
      playCut();
      if (!motionPreference.matches && feed.animate) {
        transitions.push(feed.animate(
          [{ opacity: .4, transform: 'translateX(8px)' }, { opacity: 1, transform: 'translateX(0)' }],
          { duration: 340, easing: 'cubic-bezier(.2,.75,.25,1)' },
        ));
      }
    });
  }
  renderScenario('work');
  playCut();
  const pulseLoop = window.setInterval(() => {
    if (document.hidden) return;
    transitions = transitions.filter((animation) => animation.playState === 'running');
    playSignal();
  }, 3600);
  window.addEventListener('beforeunload', () => window.clearInterval(pulseLoop), { once: true });
}

const nestedGroups = [...document.querySelectorAll('[data-nested-group]')];
function activateNestedTab(targetId, updateHash = false) {
  for (const group of nestedGroups) {
    const tabs = [...group.querySelectorAll('[data-nested-tab]')];
    const panels = [...group.querySelectorAll('[data-nested-panel]')];
    if (!tabs.some((t) => t.dataset.nestedTab === targetId)) continue;
    for (const t of tabs) {
      t.setAttribute('aria-selected', String(t.dataset.nestedTab === targetId));
    }
    for (const p of panels) {
      p.hidden = p.dataset.nestedPanel !== targetId;
    }
    if (updateHash) {
      history.replaceState(null, '', '#' + targetId);
    }
    return group;
  }
  return null;
}

if (nestedGroups.length) {
  for (const group of nestedGroups) {
    for (const tab of group.querySelectorAll('[data-nested-tab]')) {
      tab.addEventListener('click', () => {
        activateNestedTab(tab.dataset.nestedTab, true);
      });
    }
  }

  for (const jumper of document.querySelectorAll('[data-jump-tab]')) {
    jumper.addEventListener('click', (e) => {
      const targetId = jumper.dataset.jumpTab;
      const group = activateNestedTab(targetId, true);
      if (group) {
        e.preventDefault();
        group.scrollIntoView({ behavior: motionPreference.matches ? 'auto' : 'smooth', block: 'start' });
      }
    });
  }

  function syncNestedFromHash() {
    const hashId = window.location.hash.slice(1);
    if (hashId) activateNestedTab(hashId, false);
  }
  syncNestedFromHash();
  window.addEventListener('hashchange', syncNestedFromHash);
}

const dlSelector = document.querySelector('[data-download-selector]');
if (dlSelector) {
  const tiles = [...dlSelector.querySelectorAll('[data-platform-tile]')];
  const panels = [...dlSelector.querySelectorAll('[data-platform-panel]')];

  function selectDownloadPlatform(platform, updateHash = false) {
    const target = ['windows', 'macos', 'cli'].includes(platform) ? platform : 'windows';
    for (const tile of tiles) {
      const current = tile.dataset.platformTile === target;
      tile.setAttribute('aria-selected', String(current));
      tile.tabIndex = current ? 0 : -1;
    }
    for (const panel of panels) {
      panel.hidden = panel.dataset.platformPanel !== target;
    }
    if (updateHash) {
      history.replaceState(null, '', '#' + target);
    }
  }

  for (const [index, tile] of tiles.entries()) {
    tile.addEventListener('click', () => {
      selectDownloadPlatform(tile.dataset.platformTile, true);
    });
    tile.addEventListener('keydown', (event) => {
      const destinations = {
        ArrowUp: (index + tiles.length - 1) % tiles.length,
        ArrowLeft: (index + tiles.length - 1) % tiles.length,
        ArrowDown: (index + 1) % tiles.length,
        ArrowRight: (index + 1) % tiles.length,
        Home: 0,
        End: tiles.length - 1,
      };
      const destination = tiles[destinations[event.key]];
      if (!destination) return;
      event.preventDefault();
      selectDownloadPlatform(destination.dataset.platformTile, true);
      destination.focus();
    });
  }

  function syncDownloadFromEnv() {
    const hash = window.location.hash.slice(1);
    if (['windows', 'macos', 'cli'].includes(hash)) {
      selectDownloadPlatform(hash, false);
      return;
    }
    const ua = navigator.userAgentData?.platform || navigator.userAgent || '';
    if (/Mac/i.test(ua)) selectDownloadPlatform('macos', false);
    else if (/Linux/i.test(ua) && !/Android/i.test(ua)) selectDownloadPlatform('cli', false);
    else selectDownloadPlatform('windows', false);
  }
  syncDownloadFromEnv();
  window.addEventListener('hashchange', syncDownloadFromEnv);
}

async function copyTextWithFeedback(text, selectEl, statusEl, okText, fallbackText) {
  try {
    await navigator.clipboard.writeText(text);
    if (statusEl) statusEl.textContent = okText;
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(selectEl);
    selection?.removeAllRanges();
    selection?.addRange(range);
    if (statusEl) statusEl.textContent = fallbackText;
  }
}

const mcpSetup = document.querySelector('[data-mcp-setup]');
if (mcpSetup) {
  const host = mcpSetup.querySelector('#mcp-host');
  const hostNote = mcpSetup.querySelector('[data-mcp-host-note]');
  const prompt = mcpSetup.querySelector('[data-mcp-prompt]');
  const status = mcpSetup.querySelector('[data-mcp-status]');
  const copy = mcpSetup.querySelector('[data-copy-mcp]');
  const initialPrompt = prompt.textContent;
  const genericNote = hostNote.textContent;
  const hostNotes = {
    Codex: '在 Codex 的用户 MCP 设置中添加 STDIO 服务，或将 TOML 样例合并到 ~/.codex/config.toml。',
    'Claude Code': '用 claude mcp add 添加用户级 STDIO 服务，完整参数见安装说明。',
    'Claude Desktop': '打开「设置 → 开发者 → 编辑配置」，合并安装说明中的 JSON 配置。',
    Cursor: '在 Cursor 的 MCP 设置中添加服务，或将 JSON 样例合并到 ~/.cursor/mcp.json。',
  };
  const modes = mcpSetup.querySelectorAll('[data-mcp-mode]');
  const panels = mcpSetup.querySelectorAll('[data-mcp-panel]');

  function selectMode(mode) {
    for (const button of modes) button.setAttribute('aria-pressed', String(button.dataset.mcpMode === mode));
    for (const panel of panels) panel.hidden = panel.dataset.mcpPanel !== mode;
    status.textContent = '';
  }
  function updateHost() {
    prompt.textContent = host.value ? initialPrompt.replace('当前 Harness', host.value) : initialPrompt;
    hostNote.textContent = hostNotes[host.value] || genericNote;
    status.textContent = '';
  }

  mcpSetup.querySelector('[data-mcp-controls]').hidden = false;
  copy.hidden = false;
  for (const button of modes) button.addEventListener('click', () => selectMode(button.dataset.mcpMode));
  host.addEventListener('change', updateHost);
  copy.addEventListener('click', () => copyTextWithFeedback(
    prompt.textContent, prompt, status, '提示词已复制。', '提示词已选中，可手动复制。'
  ));
  selectMode('agent');
  updateHost();
}

const installer = document.querySelector('[data-installer]');
if (installer) {
  const command = installer.querySelector('[data-command]');
  const status = document.querySelector('[data-copy-status]');
  const platformButtons = [...installer.querySelectorAll('[data-platform]')];
  const posixCommand = command.textContent;

  function selectCliOs(platform) {
    command.textContent = platform === 'windows' ? command.dataset.windowsCommand : posixCommand;
    for (const button of platformButtons) {
      button.setAttribute('aria-pressed', String(button.dataset.platform === platform));
    }
    if (status) status.textContent = '';
  }

  const device = navigator.userAgentData?.platform || navigator.userAgent || '';
  selectCliOs(/Windows/i.test(device) ? 'windows' : 'posix');
  for (const button of platformButtons) {
    button.addEventListener('click', () => selectCliOs(button.dataset.platform));
  }
  installer.querySelector('[data-copy]').addEventListener('click', () => {
    copyTextWithFeedback(command.textContent, command, status, '已复制。粘贴到终端后按回车即可。', '命令已选中，可手动复制。');
  });
}

const wechatBanner = document.querySelector('[data-wechat-banner]');
if (wechatBanner) {
  const ua = navigator.userAgent || '';
  if (/MicroMessenger|Android|iPhone|iPad|Mobile/i.test(ua)) {
    wechatBanner.hidden = false;
  }
  const shareUrlEl = wechatBanner.querySelector('[data-share-url]');
  const copyShareBtn = wechatBanner.querySelector('[data-copy-share]');
  if (shareUrlEl && window.location.protocol.startsWith('http')) {
    shareUrlEl.textContent = window.location.href.split('#')[0];
  }
  copyShareBtn?.addEventListener('click', () => {
    copyTextWithFeedback(
      shareUrlEl?.textContent || window.location.href,
      shareUrlEl,
      copyShareBtn,
      '已复制链接',
      '请长按链接手动复制',
    );
  });
}

const guideDialog = document.querySelector('[data-install-guide]');
if (guideDialog) {
  const guideTitle = guideDialog.querySelector('[data-guide-title]');
  const guideBodies = [...guideDialog.querySelectorAll('[data-guide-body]')];
  const guideSupportLink = guideDialog.querySelector('[data-guide-support-link]');

  function openGuide(platform) {
    for (const body of guideBodies) {
      body.hidden = body.dataset.guideBody !== platform;
    }
    if (guideTitle) {
      guideTitle.textContent = platform === 'macos' ? 'macOS 下载已开始' : 'Windows 下载已开始';
    }
    if (guideSupportLink) {
      guideSupportLink.href = platform === 'macos' ? 'support.html#install-mac' : 'support.html#install-win';
    }
    if (typeof guideDialog.showModal === 'function') {
      if (!guideDialog.open) guideDialog.showModal();
    } else {
      guideDialog.setAttribute('open', '');
    }
  }

  for (const trigger of document.querySelectorAll('[data-guide-trigger]')) {
    trigger.addEventListener('click', () => {
      openGuide(trigger.dataset.guideTrigger);
    });
  }
  for (const closeBtn of guideDialog.querySelectorAll('[data-guide-close]')) {
    closeBtn.addEventListener('click', () => {
      if (typeof guideDialog.close === 'function') guideDialog.close();
      else guideDialog.removeAttribute('open');
    });
  }
  guideDialog.addEventListener('click', (event) => {
    if (event.target === guideDialog && typeof guideDialog.close === 'function') {
      guideDialog.close();
    }
  });
}

const windowsSetupLink = document.querySelector('[data-dl-target="win-setup"]');
if (windowsSetupLink && !dlSelector) {
  fetch('update.json', { cache: 'no-store' })
    .then((response) => (response.ok ? response.json() : null))
    .then((update) => { if (update?.url) windowsSetupLink.href = update.url; })
    .catch(() => {});
}
if (dlSelector) {
  fetch('downloads/manifest.json', { cache: 'no-store' })
    .then((resp) => (resp.ok ? resp.json() : null))
    .then((manifest) => {
      if (!manifest) return;
      const portableBtn = document.querySelector('[data-dl-target="win-portable"]');
      const armBtn = document.querySelector('[data-dl-target="mac-arm64"]');
      const intelBtn = document.querySelector('[data-dl-target="mac-x86_64"]');
      const pyBtn = document.querySelector('[data-dl-target="mac-python"]');
      if (windowsSetupLink && manifest.windows?.setup?.url) windowsSetupLink.href = manifest.windows.setup.url;
      if (portableBtn && manifest.windows?.portable?.url) portableBtn.href = manifest.windows.portable.url;
      if (armBtn && manifest.macos?.arm64?.url) armBtn.href = manifest.macos.arm64.url;
      if (intelBtn && manifest.macos?.x86_64?.url) intelBtn.href = manifest.macos.x86_64.url;
      if (pyBtn && manifest.macos?.python?.url) pyBtn.href = manifest.macos.python.url;
    })
    .catch(() => {});
}

const docSearch = document.querySelector('[data-doc-search]');
if (docSearch) {
  const searchStatus = document.querySelector('[data-doc-search-status]');
  const sections = [...document.querySelectorAll('.doc-section')];

  docSearch.addEventListener('input', () => {
    const q = docSearch.value.trim().toLowerCase();
    if (!q) {
      for (const sec of sections) sec.hidden = false;
      for (const blk of document.querySelectorAll('[data-doc-block]')) blk.hidden = false;
      if (searchStatus) searchStatus.textContent = '';
      return;
    }

    let matchedCount = 0;
    for (const sec of sections) {
      const text = ((sec.textContent || '') + ' ' + (sec.dataset.keywords || '')).toLowerCase();
      const matched = text.includes(q);
      sec.hidden = !matched;
      if (matched) matchedCount += 1;
    }
    if (searchStatus) {
      searchStatus.textContent = matchedCount ? `找到 ${matchedCount} 个相关章节` : '没有匹配的章节，请换个关键词试试';
    }
  });
}

const docNavLinks = [...document.querySelectorAll('[data-doc-nav] > a')];
if (docNavLinks.length && 'IntersectionObserver' in window) {
  const secTargets = docNavLinks
    .map((a) => document.querySelector(a.getAttribute('href')))
    .filter(Boolean);
  const navObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const id = '#' + entry.target.id;
        for (const link of docNavLinks) {
          link.classList.toggle('is-active', link.getAttribute('href') === id);
        }
      }
    },
    { rootMargin: '-20% 0px -65% 0px' }
  );
  for (const sec of secTargets) navObserver.observe(sec);
}

(() => {
  if (motionPreference.matches) return;

  const revealTargets = [...document.querySelectorAll('.quick-start, .nested-shell, .doc-card, .platform-panels')];
  if (revealTargets.length && 'IntersectionObserver' in window) {
    const revObserver = new IntersectionObserver(
      (entries, observer) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.08, rootMargin: '0px 0px -30px 0px' }
    );
    for (const el of revealTargets) {
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight * 0.92) continue;
      el.classList.add('reveal-on-scroll');
      revObserver.observe(el);
    }
  }

})();
