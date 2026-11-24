document.documentElement.classList.add('has-js');

const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
const stage = document.querySelector('[data-stage]');
if (stage) {
  const scenarios = {
    discuss: {
      target: '多个 Agent',
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
      target: '按轮发言',
      caption: '围绕一个问题分轮发言，再收拢成共识。',
      active: ['claude', 'gemini'],
      prompt: '/debate 选择议题与参与者',
      messages: [
        ['你', '论道议题', '手机和电脑同时在线时，草稿该怎么保存？'],
        ['Claude', '第 1 轮', '把草稿按设备保存，每台设备都可以继续上次的编辑。'],
        ['Gemini', '第 2 轮', '同意。还要验证切回原设备时，能找回刚才粘贴的图片。'],
      ],
    },
    work: {
      target: '文件护栏',
      caption: '点名分工，文件护栏让两边各自推进。',
      active: ['codex', 'antigravity'],
      prompt: '@Antigravity 核对安装页的链接。',
      messages: [
        ['你', '切换干活模式', '@Codex 更新安装说明，@Antigravity 验证移动端布局。'],
        ['Codex', '修改文档', '已占用安装文档。新增了 Windows 和 macOS 的启动步骤。'],
        ['Antigravity', '检查布局', '窄屏下的安装命令现在可以横向滚动，导航也能完整显示。'],
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
  const targetNode = stage.querySelector('[data-signal-target]');
  const signalLines = [...stage.querySelectorAll('[data-signal]')];
  const signalBead = stage.querySelector('[data-signal-bead]');
  const signalTravel = stage.querySelector('[data-signal-travel]');
  const replay = stage.querySelector('[data-stage-replay]');
  const light = stage.querySelector('.park-light');
  let transitions = [];
  const colors = new Map(caps.map((chip) => [
    chip.textContent.trim(), chip.style.getPropertyValue('--dot'),
  ]));

  function renderMessage([name, status, text]) {
    const row = document.createElement('div');
    row.className = name === '你' ? 'msg-row human' : 'msg-row';
    if (colors.has(name)) row.style.setProperty('--agent-color', colors.get(name));

    const header = document.createElement('header');
    const speaker = document.createElement('b');
    const meta = document.createElement('span');
    const message = document.createElement('p');
    speaker.textContent = name;
    meta.textContent = status;
    message.textContent = text;
    header.append(speaker, meta);
    row.append(header, message);
    return row;
  }

  function renderScenario(key) {
    const { active, messages, prompt: nextPrompt, caption: nextCaption, target } = scenarios[key];
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
    targetNode.textContent = target;
  }

  function clearMotion() {
    for (const animation of transitions) animation.cancel();
    transitions = [];
  }

  function playCut() {
    clearMotion();
    if (motionPreference.matches || !feed.animate) return;
    const route = signalLines.find((line) => line.dataset.signal === poster.dataset.scene);
    const easing = 'cubic-bezier(.22,1,.36,1)';
    if (signalTravel.beginElement) {
      signalTravel.setAttribute('path', route.getAttribute('d').split('M', 2).join('M'));
      signalTravel.beginElement();
      transitions.push(signalBead.animate(
        [{ opacity: 0 }, { opacity: 1, offset: .12 }, { opacity: 1, offset: .82 }, { opacity: 0 }],
        { duration: 860 },
      ));
    }
    transitions.push(
      route.animate(
        [{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }],
        { duration: 820, easing: 'ease-out' },
      ),
      light.animate(
        [{ opacity: .12 }, { opacity: .84, offset: .5 }, { opacity: .48 }],
        { duration: 900, easing },
      ),
      targetNode.animate(
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
  stage.addEventListener('pointermove', (event) => {
    if (event.pointerType !== 'mouse' || motionPreference.matches) return;
    const { x, y, width, height } = stage.getBoundingClientRect();
    stage.style.setProperty('--park-x', `${8 * ((event.clientX - x) / width - .5)}px`);
    stage.style.setProperty('--park-y', `${8 * ((event.clientY - y) / height - .5)}px`);
  });
  stage.addEventListener('pointerleave', () => {
    stage.style.removeProperty('--park-x');
    stage.style.removeProperty('--park-y');
  });
  renderScenario('discuss');
  playCut();
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

if (dlSelector) {
  fetch('downloads/manifest.json', { cache: 'no-store' })
    .then((resp) => (resp.ok ? resp.json() : null))
    .then((manifest) => {
      if (!manifest) return;
      const setupBtn = document.querySelector('[data-dl-target="win-setup"]');
      const portableBtn = document.querySelector('[data-dl-target="win-portable"]');
      const armBtn = document.querySelector('[data-dl-target="mac-arm64"]');
      const intelBtn = document.querySelector('[data-dl-target="mac-x86_64"]');
      const pyBtn = document.querySelector('[data-dl-target="mac-python"]');
      if (setupBtn && manifest.windows?.setup?.url) setupBtn.href = manifest.windows.setup.url;
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
