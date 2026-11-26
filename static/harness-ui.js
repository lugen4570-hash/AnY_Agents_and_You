// AnY Harness UI (M2 + M3):
// - Theme (system / light / dark) and Language (auto / zh-CN / en)
// - Composer bar (mode, target-aware model chip + popover, extensions shortcut, / skill menu)
// - Right inspector 3-tab controller (Agents / Board / Output) with inline session tools
// - Global Settings center (General / Agents & Connections / Extensions / About & Updates)
(function (root) {
  const THEME_KEY = 'any_theme';
  const LANG_KEY = 'any_lang';
  const SIDE_TAB_KEY = 'any_side_tab';
  const LEGACY_KEYS = { any_theme: 'cojam_theme', any_lang: 'cojam_lang', any_side_tab: 'cojam_side_tab' };

  const I18N = {
    'zh-CN': {
      'nav.settings': '设置',
      'nav.new': '＋ 新建会话',
      'nav.search': '搜索项目或会话',
      'side.title': '会议详情与看板',
      'side.tabAgents': '成员',
      'side.tabBoard': '看板',
      'side.tabOutput': '产出',
      'side.tabChanges': '改动',
      'mode.discuss': '讨论模式',
      'mode.work': '干活模式',
      'composer.model': '模型',
      'composer.modelField': '模型',
      'composer.effortField': '思考强度',
      'composer.ext': '扩展',
      'composer.hint': '@ 指定成员 · / 命令与技能',
      'composer.placeholder': '有什么新想法？@ 指定成员，/ 命令与技能…',
      'composer.desktopManaged': '由桌面端管理',
      'composer.desktopSkillHint': '为桌面端接入，技能由原软件管理，请在原软件中使用。',
      'composer.noSkills': '当前没有可用命令或技能。',
      'composer.loadingSkills': '正在读取 Agent 技能…',
      'composer.sendTo': '将发送给',
      'composer.allAgents': '全员',
      'composer.save': '保存',
      'composer.openFull': '执行端与详情',
      'composer.pending': '下轮生效',
      'composer.busy': '运行中锁定',
      'settings.title': '设置',
      'settings.general': '通用',
      'settings.cloud': '账号与同步',
      'settings.agents': 'Agent 与连接',
      'settings.extensions': '扩展',
      'settings.about': '关于与更新',
      'settings.tutorial': '使用教学',
      'settings.theme': '外观主题',
      'settings.themeHint': '仅影响当前客户端的界面外观。',
      'settings.themeSystem': '跟随系统',
      'settings.themeLight': '浅色',
      'settings.themeDark': '深色',
      'settings.lang': '界面语言',
      'settings.langHint': '仅影响当前客户端的界面语言。',
      'settings.langAuto': '自动',
      'settings.langZh': '简体中文',
      'settings.langEn': 'English',
      'ext.skill': '技能',
      'ext.plugin': '插件',
      'ext.mcp': 'MCP',
      'ext.refresh': '刷新',
      'ext.import': '导入本地技能',
      'ext.openFolder': '打开目录',
      'ext.hostManaged': '由原软件管理',
      'ext.defaultOff': '默认关闭',
      'ext.defaultOn': '默认开启',
      'ext.scopeUser': '个人',
      'ext.scopeProject': '项目',
      'ext.scopeHost': '宿主',
      'onboard.title': '开始第一场协作',
      'onboard.subtitle': '接入 AI，在这个房间测试回复，再开始协作。',
      'onboard.step1Title': '接入 AI',
      'onboard.step1Empty': '当前会话还没有 AI 成员。扫描或连接本机已有 CLI / 桌面端即可开聊。',
      'onboard.step1Ready': '已接入 {n} 位 AI 成员：',
      'onboard.addAi': '接入 AI',
      'onboard.addMoreAi': '接入更多 AI',
      'onboard.manageMembers': '管理本会话成员',
      'onboard.pickFromContacts': '从已有联系人拉入',
      'onboard.step2Title': '实测真实回复',
      'onboard.step2NeedAi': '先完成第 1 步接入至少一位 AI，再在房间内发送测试消息验证真实回复。',
      'onboard.step2Desc': '直接通过当前房间发送一句短测试（含 Claude / Codex 真实链路），确认成员都能正常回复。',
      'onboard.sendTest': '发送测试消息验证',
      'onboard.fillTest': '填入输入框',
      'onboard.step3Title': '发第一条消息',
      'onboard.step3Desc': '选一句开场白填入会话输入框，或回到会话后输入自己的任务。',
      'onboard.defaultTestPrompt': '请简短回复一句「已就绪」，确认我们可以开始协作。',
      'verify.runningTitle': '正在验证真实回复（{done}/{total}）',
      'verify.doneTitle': '全部 {total} 位 AI 已成功回复，可以开始协作！',
      'verify.replied': '已回复',
      'verify.running': '回复中…',
      'verify.waiting': '等待回复',
      'verify.failed': '失败',
      'verify.dismiss': '关闭',
    },
    en: {
      'nav.settings': 'Settings',
      'nav.new': '+ New Session',
      'nav.search': 'Search projects or sessions',
      'side.title': 'Session Inspector',
      'side.tabAgents': 'Agents',
      'side.tabBoard': 'Board',
      'side.tabOutput': 'Output',
      'side.tabChanges': 'Changes',
      'mode.discuss': 'Discuss',
      'mode.work': 'Work',
      'composer.model': 'Models',
      'composer.modelField': 'Model',
      'composer.effortField': 'Reasoning effort',
      'composer.ext': 'Extensions',
      'composer.hint': '@ mention · / commands & skills',
      'composer.placeholder': 'Type a message… @ to mention, / for commands & skills',
      'composer.desktopManaged': 'Managed by desktop app',
      'composer.desktopSkillHint': 'is connected via desktop MCP. Skills are managed in its host app.',
      'composer.noSkills': 'No matching commands or skills.',
      'composer.loadingSkills': 'Loading agent skills…',
      'composer.sendTo': 'To',
      'composer.allAgents': 'All agents',
      'composer.save': 'Save',
      'composer.openFull': 'Endpoint & details',
      'composer.pending': 'Next turn',
      'composer.busy': 'Locked while busy',
      'settings.title': 'Settings',
      'settings.general': 'General',
      'settings.cloud': 'Account & Sync',
      'settings.agents': 'Agents & Connections',
      'settings.extensions': 'Extensions',
      'settings.about': 'About & Updates',
      'settings.tutorial': 'Getting Started',
      'settings.theme': 'Appearance',
      'settings.themeHint': 'Applies only to this client.',
      'settings.themeSystem': 'System',
      'settings.themeLight': 'Light',
      'settings.themeDark': 'Dark',
      'settings.lang': 'Language',
      'settings.langHint': 'Applies only to this client.',
      'settings.langAuto': 'Auto',
      'settings.langZh': '简体中文',
      'settings.langEn': 'English',
      'ext.skill': 'Skills',
      'ext.plugin': 'Plugins',
      'ext.mcp': 'MCP',
      'ext.refresh': 'Refresh',
      'ext.import': 'Import Local Skill',
      'ext.openFolder': 'Open Folder',
      'ext.hostManaged': 'Managed by host app',
      'ext.defaultOff': 'Off by default',
      'ext.defaultOn': 'On by default',
      'ext.scopeUser': 'User',
      'ext.scopeProject': 'Project',
      'ext.scopeHost': 'Host',
      'onboard.title': 'Start Your First Session',
      'onboard.subtitle': 'Connect AI members and test their replies in this room.',
      'onboard.step1Title': 'Connect AI',
      'onboard.step1Empty': 'No AI members in this room yet. Scan or connect a local CLI or desktop agent.',
      'onboard.step1Ready': '{n} AI member(s) connected:',
      'onboard.addAi': 'Connect AI',
      'onboard.addMoreAi': 'Connect More AI',
      'onboard.manageMembers': 'Manage Room Members',
      'onboard.pickFromContacts': 'Add from Contacts',
      'onboard.step2Title': 'Verify Real Reply',
      'onboard.step2NeedAi': 'Connect at least one AI in Step 1, then send a test message here to verify real replies.',
      'onboard.step2Desc': 'Send a short test message directly through this room (verifies Claude / Codex end-to-end).',
      'onboard.sendTest': 'Send Test & Verify',
      'onboard.fillTest': 'Fill Composer',
      'onboard.step3Title': 'Send First Message',
      'onboard.step3Desc': 'Pick a starter prompt or return to your session to type your own task.',
      'onboard.defaultTestPrompt': 'Please reply briefly with "Ready" to confirm we can start collaborating.',
      'verify.runningTitle': 'Verifying real replies ({done}/{total})',
      'verify.doneTitle': 'All {total} AI(s) replied successfully — ready to collaborate!',
      'verify.replied': 'Replied',
      'verify.running': 'Replying…',
      'verify.waiting': 'Waiting',
      'verify.failed': 'Failed',
      'verify.dismiss': 'Dismiss',
    },
  };

  function safeStorageGet(key, fallback) {
    try {
      const val = localStorage.getItem(key);
      if (val) return val;
      const legacy = LEGACY_KEYS[key] ? localStorage.getItem(LEGACY_KEYS[key]) : '';
      return legacy || fallback;
    } catch (e) { return fallback; }
  }
  function safeStorageSet(key, val) {
    try { localStorage.setItem(key, val); } catch (e) {}
  }

  function resolveLang(pref) {
    if (pref === 'en' || pref === 'zh-CN') return pref;
    const nav = (typeof navigator !== 'undefined' && navigator.language) ? navigator.language.toLowerCase() : 'zh-cn';
    return nav.startsWith('en') ? 'en' : 'zh-CN';
  }

  function getLangPref() {
    const v = safeStorageGet(LANG_KEY, 'auto');
    return (v === 'zh-CN' || v === 'en' || v === 'auto') ? v : 'auto';
  }

  function t(key) {
    const lang = resolveLang(getLangPref());
    return (I18N[lang] && I18N[lang][key]) || I18N['zh-CN'][key] || key;
  }

  function getThemePref() {
    const v = safeStorageGet(THEME_KEY, 'dark');
    return (v === 'light' || v === 'dark' || v === 'system') ? v : 'dark';
  }

  function applyTheme(pref) {
    const value = (pref === 'light' || pref === 'dark') ? pref : 'system';
    safeStorageSet(THEME_KEY, value);
    if (typeof document === 'undefined') return value;
    const el = document.documentElement;
    if (value === 'system') delete el.dataset.theme;
    else el.dataset.theme = value;
    const meta = document.querySelector('meta[name="color-scheme"]');
    if (meta) meta.content = value === 'system' ? 'light dark' : value;
    document.querySelectorAll('meta[name="theme-color"][data-system-media]').forEach(tag => {
      const theme = tag.dataset.theme;
      tag.media = value === 'system' ? tag.dataset.systemMedia : value === theme ? 'all' : 'not all';
    });
    return value;
  }

  function applyLang(pref) {
    const value = (pref === 'zh-CN' || pref === 'en') ? pref : 'auto';
    safeStorageSet(LANG_KEY, value);
    const resolved = resolveLang(value);
    if (typeof document === 'undefined') return resolved;
    document.documentElement.lang = resolved;
    document.querySelectorAll('[data-i18n]').forEach(el => {
      el.textContent = t(el.dataset.i18n);
    });
    const search = document.getElementById('navSearch');
    if (search) search.placeholder = t('nav.search');
    const taEl = document.getElementById('ta');
    if (taEl) taEl.placeholder = t('composer.placeholder');
    const extBtn = document.getElementById('composerExtBtn');
    if (extBtn) extBtn.textContent = t('composer.ext');
    if (typeof syncHarnessUi === 'function') syncHarnessUi();
    return resolved;
  }

  // ===== Pure Helpers (Unit-Testable) =====

  function getRoomAiIds(state) {
    const parts = (state && state.participants) || [];
    const ais = (state && state.ais) || {};
    const agents = (state && state.agents) || [];
    const userSet = new Set(agents.filter(a => a && a.kind === 'user').map(a => a.id));
    const ordered = parts.filter(id => !userSet.has(id) && (ais[id] || agents.some(a => a.id === id && a.kind !== 'user')));
    if (ordered.length) return ordered;
    return Object.keys(ais);
  }

  function isDesktopManaged(state, aiId) {
    const exec = state && state.execution && state.execution[aiId];
    const mo = state && state.ais && state.ais[aiId] && state.ais[aiId].model;
    if (exec && exec.endpoint === 'desktop') return true;
    if (mo && (mo.apply_status === 'read_only' || mo.model_supported === false)) return true;
    return false;
  }

  function extractExplicitMentions(text, aiIds) {
    const valid = new Set(aiIds || []);
    const found = [];
    const re = /(^|[\s(（])@([A-Za-z0-9_.-]+)/g;
    let m;
    while ((m = re.exec(String(text || ''))) !== null) {
      const id = m[2];
      if (valid.has(id) && !found.includes(id)) found.push(id);
    }
    return found;
  }

  function resolveComposerTarget(text, state) {
    const aiIds = getRoomAiIds(state);
    const mentions = extractExplicitMentions(text, aiIds);
    if (mentions.length === 1) {
      return { mode: 'single', aiId: mentions[0], explicit: true, aiIds };
    }
    if (mentions.length > 1) {
      return { mode: 'multi', aiIds: mentions, explicit: true, allAiIds: aiIds };
    }
    if (aiIds.length === 1) {
      return { mode: 'single', aiId: aiIds[0], explicit: false, aiIds };
    }
    return { mode: 'multi', aiIds, explicit: false, allAiIds: aiIds };
  }

  function agentDisplayName(state, contacts, id) {
    const list = (state && state.agents) || contacts || [];
    const found = list.find(a => a && a.id === id);
    return (found && found.label) || id;
  }

  function buildModelChipState(text, state, contacts) {
    const target = resolveComposerTarget(text, state);
    if (!state || !state.meeting || !target.aiIds.length) {
      return { disabled: true, label: t('composer.model'), readonly: false, pending: false, target };
    }
    if (target.mode === 'single') {
      const id = target.aiId;
      const name = agentDisplayName(state, contacts, id);
      const x = (state.ais && state.ais[id]) || {};
      const mo = x.model || {};
      const desktop = isDesktopManaged(state, id);
      if (desktop) {
        const reported = mo.observed && mo.observed.model ? mo.observed.model : '';
        const textLabel = reported
          ? name + ' · ' + reported
          : name + ' · ' + t('composer.desktopManaged');
        return { disabled: false, label: textLabel, readonly: true, pending: false, target };
      }
      const modelLabel = (mo.model || mo.observed?.model) ? (mo.label || mo.model || mo.observed.model) : t('composer.model');
      const pending = mo.apply_status === 'pending';
      return {
        disabled: false,
        label: name + ' · ' + modelLabel,
        readonly: false,
        pending,
        target,
      };
    }
    const count = target.aiIds.length;
    return {
      disabled: false,
      label: t('composer.model') + ' (' + count + ')',
      readonly: false,
      pending: target.aiIds.some(id => {
        const mo = state.ais && state.ais[id] && state.ais[id].model;
        return mo && mo.apply_status === 'pending';
      }),
      target,
    };
  }

  function parseSlashQuery(text, cursorPos) {
    const s = String(text || '');
    const pos = typeof cursorPos === 'number' ? cursorPos : s.length;
    const before = s.slice(0, pos);
    const m = before.match(/(^|\s)\/([A-Za-z0-9_.:-]*)$/);
    if (!m) return null;
    const slashStart = pos - m[2].length - 1;
    return { query: m[2].toLowerCase(), start: slashStart, end: pos };
  }

  function filterSlashSkills(text, cursorPos, state, toolsByAi, contacts) {
    const slash = parseSlashQuery(text, cursorPos);
    if (!slash) return null;
    const target = resolveComposerTarget(text, state);
    const q = slash.query;
    const desktopNotes = [];
    const entriesMap = new Map();

    if (target.mode === 'single') {
      const id = target.aiId;
      const name = agentDisplayName(state, contacts, id);
      if (isDesktopManaged(state, id)) {
        return {
          slash,
          target,
          desktopOnly: true,
          notice: '@' + name + ' ' + t('composer.desktopSkillHint'),
          items: [],
          desktopNotes: [],
        };
      }
      const tools = (toolsByAi && toolsByAi[id]) || null;
      const skills = (tools && tools.skills) || [];
      skills.filter(k => k && k.on !== false).forEach(k => {
        const nm = String(k.name || '');
        if (q && !nm.toLowerCase().includes(q) && !String(k.desc || '').toLowerCase().includes(q)) return;
        entriesMap.set(nm, { name: nm, desc: k.desc || '', agentIds: [id], agentLabels: [name] });
      });
      return { slash, target, desktopOnly: false, notice: '', items: [...entriesMap.values()], desktopNotes };
    }

    // Multi-agent / broadcast
    target.aiIds.forEach(id => {
      const name = agentDisplayName(state, contacts, id);
      if (isDesktopManaged(state, id)) {
        desktopNotes.push(name + '：' + t('ext.hostManaged'));
        return;
      }
      const tools = (toolsByAi && toolsByAi[id]) || null;
      const skills = (tools && tools.skills) || [];
      skills.filter(k => k && k.on !== false).forEach(k => {
        const nm = String(k.name || '');
        if (q && !nm.toLowerCase().includes(q) && !String(k.desc || '').toLowerCase().includes(q)) return;
        if (!entriesMap.has(nm)) {
          entriesMap.set(nm, { name: nm, desc: k.desc || '', agentIds: [id], agentLabels: [name] });
        } else {
          const prev = entriesMap.get(nm);
          if (!prev.agentIds.includes(id)) {
            prev.agentIds.push(id);
            prev.agentLabels.push(name);
          }
        }
      });
    });

    return {
      slash,
      target,
      desktopOnly: false,
      notice: desktopNotes.length ? desktopNotes.join(' · ') : '',
      items: [...entriesMap.values()],
      desktopNotes,
    };
  }

  const SLASH_COMMANDS = [
    {
      name: 'compact',
      aliases: ['压缩'],
      argsHint: '[@成员]',
      fillArgs: false,
      desc: '压缩上下文（只记要点；可填 @成员 或 /compact 成员）',
      descEn: 'Compact context (optionally @agent)',
    },
    {
      name: 'skills',
      aliases: ['skill', '技能'],
      argsHint: '[@成员]',
      fillArgs: false,
      desc: '配置本会话技能、MCP 与插件',
      descEn: 'Configure session skills, MCP & plugins',
    },
    {
      name: 'mode',
      aliases: ['模式'],
      argsHint: '[discuss|work]',
      fillArgs: false,
      desc: '切换只读讨论模式或允许改文件的干活模式',
      descEn: 'Switch discuss/work mode (/mode work or discuss)',
    },
    {
      name: 'model',
      aliases: ['模型'],
      argsHint: '[@成员]',
      fillArgs: false,
      desc: '调整当前成员模型与思考强度',
      descEn: 'Choose model and reasoning effort',
    },
    {
      name: 'stop',
      aliases: ['停'],
      argsHint: '[@成员]',
      fillArgs: false,
      desc: '立即打断正在回复或排队的 AI（默认全停）',
      descEn: 'Stop running/queued agent replies',
    },
    {
      name: 'debate',
      aliases: ['论道'],
      argsHint: '[议题]',
      fillArgs: false,
      desc: '发起多轮 AI 轮流论道并总结',
      descEn: 'Start multi-round agent debate',
    },
    {
      name: 'debate-continue',
      aliases: ['继续论道'],
      argsHint: '[补充意见]',
      fillArgs: false,
      desc: '补充意见，继续上一场论道',
      descEn: 'Continue the previous debate with feedback',
    },
    {
      name: 'debate-finish',
      aliases: ['finish', '总结论道'],
      argsHint: '',
      fillArgs: false,
      desc: '结束当前论道并请主持人总结收尾',
      descEn: 'Finish active debate and summarize',
    },
    {
      name: 'wrapup',
      aliases: ['落盘'],
      argsHint: '',
      fillArgs: false,
      desc: '整理会议结论落盘并提交',
      descEn: 'Wrap up session conclusions to docs/git',
    },
    {
      name: 'status',
      aliases: ['状态'],
      argsHint: '',
      fillArgs: false,
      desc: '打开右侧详情查看目录、文件护栏与上下文用量',
      descEn: 'Show workspace, file locks & context details',
    },
    {
      name: 'agents',
      aliases: ['成员'],
      argsHint: '',
      fillArgs: false,
      desc: '管理本场会话成员与权限开关',
      descEn: 'Manage session members and permissions',
    },
    {
      name: 'scan',
      aliases: ['扫描'],
      argsHint: '',
      fillArgs: false,
      desc: '重新扫描本机安装的 CLI 与桌面端 Harness',
      descEn: 'Scan local installed CLI and desktop harnesses',
    },
    {
      name: 'connect',
      aliases: ['接入', '连接'],
      argsHint: '[@成员]',
      fillArgs: false,
      desc: '配置 Agent 接入方式、MCP 与参数设置',
      descEn: 'Configure agent connections and settings',
    },
    {
      name: 'invite',
      aliases: ['邀请'],
      argsHint: '',
      fillArgs: false,
      desc: '新增 AI 成员、手机设备或邀请他人旁听',
      descEn: 'Add agent, device or invite participant',
    },
    {
      name: 'handoff',
      aliases: ['交终端'],
      argsHint: '@成员',
      fillArgs: true,
      desc: '将本机 AI 会话交给原生终端继续操作',
      descEn: 'Hand off native session to terminal',
    },
    {
      name: 'return',
      aliases: ['收回'],
      argsHint: '@成员',
      fillArgs: true,
      desc: '从终端收回已交出的 AI 会话控制权',
      descEn: 'Return session from terminal to room',
    },
    {
      name: 'announce',
      aliases: ['目标', '公告'],
      argsHint: '[内容]',
      fillArgs: false,
      desc: '设置或编辑本场会议的目标公告',
      descEn: 'Set or edit meeting goal/announcement',
    },
    {
      name: 'todo',
      aliases: ['待办'],
      argsHint: '内容',
      fillArgs: true,
      desc: '向当前会话看板新增一条待办（/todo 内容）',
      descEn: 'Add todo item to board (/todo text)',
    },
    {
      name: 'done',
      aliases: ['完成'],
      argsHint: '#编号',
      fillArgs: true,
      desc: '标记看板中的 #编号 待办为已完成',
      descEn: 'Mark board todo #id as done (/done #id)',
    },
    {
      name: 'undo',
      aliases: ['撤回'],
      argsHint: '',
      fillArgs: false,
      desc: '预览并按步撤回最近一次干活文件修改',
      descEn: 'Preview and undo latest edit step',
    },
    {
      name: 'new',
      aliases: ['新建'],
      argsHint: '',
      fillArgs: false,
      desc: '在当前项目下新建一场会话',
      descEn: 'Create a new session in current project',
    },
    {
      name: 'resume',
      aliases: ['会话列表', '切换'],
      argsHint: '',
      fillArgs: false,
      desc: '切换历史会话或打开项目/回收站管理',
      descEn: 'Browse/switch sessions and trash',
    },
    {
      name: 'project',
      aliases: ['项目'],
      argsHint: '',
      fillArgs: false,
      desc: '新建绑定本地工作目录的项目',
      descEn: 'Create a new workspace project',
    },
    {
      name: 'rename',
      aliases: ['改名'],
      argsHint: '[新标题]',
      fillArgs: false,
      desc: '修改当前会话标题',
      descEn: 'Rename current session',
    },
    {
      name: 'help',
      aliases: ['帮助'],
      argsHint: '',
      fillArgs: false,
      desc: '查看所有斜杠命令说明与示例',
      descEn: 'Show all slash commands and usage',
    },
    {
      name: 'quit',
      aliases: ['exit', '退出'],
      argsHint: '',
      fillArgs: false,
      desc: '安全退出 AnY 客户端与后台服务',
      descEn: 'Quit AnY client and backend server',
    },
  ];

  const SLASH_COMMAND_MAP = new Map();
  SLASH_COMMANDS.forEach(cmd => {
    SLASH_COMMAND_MAP.set(cmd.name.toLowerCase(), cmd);
    (cmd.aliases || []).forEach(a => SLASH_COMMAND_MAP.set(String(a).toLowerCase(), cmd));
  });
  const MEMBER_ARG_COMMANDS = new Set(['compact', 'skills', 'stop', 'model', 'handoff', 'return', 'connect']);

  function filterSlashCommands(text, cursorPos, state, contacts) {
    const slash = parseSlashQuery(text, cursorPos);
    if (!slash) return null;
    const q = slash.query;
    const target = resolveComposerTarget(text, state);
    const isEn = resolveLang(getLangPref()) === 'en';
    const isCjk = /[\u4e00-\u9fa5]/.test(q);
    const matched = SLASH_COMMANDS.filter(cmd =>
      !q
      || cmd.name.includes(q)
      || (cmd.aliases || []).some(a => a.toLowerCase().includes(q))
      || (isCjk && (cmd.desc.toLowerCase().includes(q) || cmd.descEn.toLowerCase().includes(q)))
    );
    if (q) {
      matched.sort((a, b) => Number(!a.name.startsWith(q)) - Number(!b.name.startsWith(q)));
    }
    const items = matched.map(cmd => ({
      kind: 'command',
      name: cmd.name,
      argsHint: cmd.argsHint || '',
      fillArgs: Boolean(cmd.fillArgs),
      desc: isEn ? cmd.descEn : cmd.desc,
      agentIds: target.mode === 'single' ? [target.aiId] : (target.aiIds || []),
      agentLabels: [],
    }));
    return { slash, target, items };
  }

  function buildSlashMenuModel(text, cursorPos, state, toolsByAi, contacts) {
    const cmdRes = filterSlashCommands(text, cursorPos, state, contacts);
    const skillRes = filterSlashSkills(text, cursorPos, state, toolsByAi, contacts);
    const slash = (cmdRes && cmdRes.slash) || (skillRes && skillRes.slash) || null;
    const target = (cmdRes && cmdRes.target) || (skillRes && skillRes.target) || resolveComposerTarget(text, state);
    const commandItems = (cmdRes && cmdRes.items) || [];
    const skillItems = ((skillRes && skillRes.items) || []).map(item => Object.assign({ kind: 'skill' }, item));
    const ownerIds = [];
    skillItems.forEach(item => {
      (item.agentIds || []).forEach(id => {
        if (!ownerIds.includes(id)) ownerIds.push(id);
      });
    });
    const singleSkillOwnerLabel = ownerIds.length === 1 ? agentDisplayName(state, contacts, ownerIds[0]) : '';
    const showPerSkillOwnerTags = ownerIds.length > 1;
    return {
      slash,
      target,
      desktopOnly: Boolean(skillRes && skillRes.desktopOnly && !commandItems.length),
      notice: (skillRes && skillRes.notice) || '',
      commandItems,
      skillItems,
      singleSkillOwnerLabel,
      showPerSkillOwnerTags,
      items: [...commandItems, ...skillItems],
    };
  }

  function parseComposerSlashCommand(text, state) {
    const s = String(text || '').trim();
    if (s.startsWith('//')) return null;
    const m = s.match(/^((?:@[A-Za-z0-9_.-]+\s+)*)\/([A-Za-z0-9_.\-\u4e00-\u9fa5]+)(?:\s+([\s\S]*))?$/);
    if (!m) return null;
    const spec = SLASH_COMMAND_MAP.get(m[2].toLowerCase());
    if (!spec) return null;
    const aiIds = getRoomAiIds(state);
    const mentions = extractExplicitMentions(s, aiIds);
    const arg = (m[3] || '').trim();
    let targetIds = [];
    let error = '';
    if (MEMBER_ARG_COMMANDS.has(spec.name)) {
      if (arg) {
        const cleanArg = arg.replace(/^@/, '').trim();
        const pool = spec.name === 'connect' && Array.isArray(state && state.agents)
          ? [...new Set([...aiIds, ...state.agents.map(a => a && a.id).filter(Boolean)])]
          : aiIds;
        const matched = pool.find(id => id.toLowerCase() === cleanArg.toLowerCase())
          || pool.find(id => agentDisplayName(state, null, id).toLowerCase() === cleanArg.toLowerCase());
        if (matched) targetIds = [matched];
        else error = '未找到可操作的会话成员：' + arg;
      } else if (mentions.length) {
        targetIds = mentions;
      }
    } else if (mentions.length) {
      targetIds = mentions;
    }
    return {
      command: spec.name,
      targetIds,
      explicitTarget: Boolean((MEMBER_ARG_COMMANDS.has(spec.name) && arg) || mentions.length),
      argText: arg,
      error,
    };
  }

  function applySlashSelection(text, slash, skillItem, target) {
    const before = text.slice(0, slash.start);
    const after = text.slice(slash.end);
    const inserted = '/' + skillItem.name + (after.startsWith(' ') ? '' : ' ');
    let next = before + inserted + after;
    let recipientIds = target.explicit ? (target.mode === 'single' ? [target.aiId] : target.aiIds) : skillItem.agentIds;
    // If user had NOT explicitly @-mentioned anyone and the skill targets a subset of agents, prepend @agent.
    if (!target.explicit && target.mode === 'multi' && skillItem.agentIds && skillItem.agentIds.length === 1) {
      const prefix = '@' + skillItem.agentIds[0] + ' ';
      if (!next.startsWith(prefix)) next = prefix + next;
    }
    return { text: next, recipientIds };
  }

  function classifyExtensionBadges(item) {
    const badges = [];
    const tags = Array.isArray(item && item.tags) ? item.tags : [];
    const scope = item && item.scope;
    const hostManaged = tags.includes('host_managed') || scope === 'host';
    if (scope === 'user') badges.push({ label: t('ext.scopeUser'), tone: '' });
    else if (scope === 'project') badges.push({ label: t('ext.scopeProject'), tone: '' });
    if (hostManaged) {
      badges.push({ label: t('ext.hostManaged'), tone: 'warn' });
    } else if (item && item.default_on === false) {
      badges.push({ label: t('ext.defaultOff'), tone: 'warn' });
    } else if (item && item.default_on === true) {
      badges.push({ label: t('ext.defaultOn'), tone: 'ok' });
    }
    if (tags.includes('hooks')) badges.push({ label: 'hooks', tone: 'warn' });
    if (tags.includes('synced')) badges.push({ label: 'synced', tone: '' });
    if (item && item.plugin_id) badges.push({ label: 'plugin: ' + item.plugin_id, tone: '' });
    return badges;
  }

  function validateImportPayload({ agent_id, scope, project_id, source_path }) {
    const cleanAgent = String(agent_id || '').trim();
    const cleanScope = scope === 'project' ? 'project' : 'user';
    const cleanPath = String(source_path || '').trim();
    if (!cleanAgent) return { ok: false, error: '请选择目标 Agent。' };
    if (!cleanPath) return { ok: false, error: '请填写本地技能文件夹路径。' };
    const payload = { agent_id: cleanAgent, scope: cleanScope, source_path: cleanPath };
    if (cleanScope === 'project') {
      const cleanProj = String(project_id || '').trim();
      if (!cleanProj) return { ok: false, error: '当前没有选中的项目，请改用「个人」范围或先进入项目会话。' };
      payload.project_id = cleanProj;
    }
    return { ok: true, payload };
  }

  function blockedWorkTargets(state, target) {
    if (!state || state.mode !== 'work' || !state.permissions || !target) return [];
    const ids = target.mode === 'single' ? [target.aiId] : (target.aiIds || []);
    return ids.filter(id => state.permissions[id] && state.permissions[id].work === false);
  }

  function buildOnboardingState(state, contacts) {
    if (!state || !state.meeting) {
      return {
        roomAiIds: [],
        roomAis: [],
        availableContactAis: [],
        testPrompt: t('onboard.defaultTestPrompt'),
      };
    }
    const roomAiIds = getRoomAiIds(state);
    const allContacts = Array.isArray(contacts) ? contacts : ((state && state.agents) || []);
    const roomAis = roomAiIds.map(id => {
      const meta = allContacts.find(c => c && c.id === id)
        || ((state && state.agents) || []).find(c => c && c.id === id)
        || {};
      return {
        id,
        label: meta.label || id,
        color: meta.color || '#64748b',
        letter: meta.letter || String(id).slice(0, 1).toUpperCase(),
        enabled: meta.enabled !== false,
      };
    });
    const inRoom = new Set(roomAiIds);
    const availableContactAis = allContacts
      .filter(c => c && c.kind !== 'user' && c.enabled && !inRoom.has(c.id))
      .map(c => ({ id: c.id, label: c.label || c.id }));
    return {
      roomAiIds,
      roomAis,
      availableContactAis,
      testPrompt: t('onboard.defaultTestPrompt'),
    };
  }

  function buildVerificationTrackerState(state, messages, runningIds, tracker) {
    if (!tracker || tracker.dismissed || !state || state.meeting !== tracker.roomId) {
      return { active: false, allReplied: false, repliedCount: 0, totalCount: 0, items: [] };
    }
    const roomSet = new Set(getRoomAiIds(state));
    const targetAiIds = (tracker.targetAiIds || []).filter(id => roomSet.has(id));
    if (!targetAiIds.length) {
      return { active: false, allReplied: false, repliedCount: 0, totalCount: 0, items: [] };
    }
    const baseline = Number.isInteger(tracker.baselineMaxId) ? tracker.baselineMaxId : -1;
    const list = Array.isArray(messages) ? messages : [];
    let recent = list.filter(m => m && !m.recalled && Number(m.id) > baseline);
    if (tracker.prompt) {
      const source = recent.find(m => m.speaker === '你' && m.text === tracker.prompt);
      recent = source ? recent.filter(m => m.source_message === source.id) : [];
    }
    const runningSet = new Set(Array.isArray(runningIds) ? runningIds : []);
    const contacts = (state && state.agents) || [];
    const items = targetAiIds.map(id => {
      const label = agentDisplayName(state, contacts, id);
      const aiState = (state.ais && state.ais[id]) || {};
      const replied = recent.some(m => m.speaker === id);
      if (replied) return { id, label, status: 'replied', detail: '' };
      if (runningSet.has(id) || aiState.busy) return { id, label, status: 'running', detail: '' };
      const sysErr = recent.find(m => m.failure?.ai === id) || (!tracker.prompt && recent.find(m => m.speaker === '系统' && typeof m.text === 'string' && m.text.includes(id) && /失败|超时|错误|error|failed/i.test(m.text)));
      if (aiState.last_error || sysErr) {
        return { id, label, status: 'failed', detail: aiState.last_error || (sysErr && sysErr.text) || '' };
      }
      return { id, label, status: 'waiting', detail: '' };
    });
    const repliedCount = items.filter(i => i.status === 'replied').length;
    return {
      active: true,
      allReplied: repliedCount === items.length,
      repliedCount,
      totalCount: items.length,
      items,
    };
  }

  // ===== Export pure API for Node unit tests =====
  const exported = {
    applyTheme,
    applyLang,
    getThemePref,
    getLangPref,
    resolveLang,
    getRoomAiIds,
    isDesktopManaged,
    extractExplicitMentions,
    resolveComposerTarget,
    buildModelChipState,
    blockedWorkTargets,
    buildOnboardingState,
    buildVerificationTrackerState,
    parseSlashQuery,
    filterSlashCommands,
    parseComposerSlashCommand,
    buildSlashMenuModel,
    filterSlashSkills,
    applySlashSelection,
    classifyExtensionBadges,
    validateImportPayload,
  };
  root.AnYHarness = exported;
  root.CojamHarness = exported;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = exported;
  }

  if (typeof document === 'undefined') return;

  // ===== Live Browser Integration =====
  const toolsCache = new Map(); // key: rid + ':' + aiId -> tools payload
  const toolsRequests = new Map();
  let slashRevision = 0;
  let slashActiveIndex = 0;
  let slashState = null;
  let currentSideTab = safeStorageGet(SIDE_TAB_KEY, 'agents');
  let extensionsCache = null;
  let settingsTab = 'general';
  let extSubTab = 'skill';
  let extImportOpen = false;
  let verifyTracker = null;
  let verifySig = '';

  function htmlEsc(v) {
    if (typeof esc === 'function') return esc(v);
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function currentMaxMessageId() {
    if (typeof msgById === 'undefined' || !msgById) return -1;
    let maxId = -1;
    for (const m of Object.values(msgById)) {
      const id = Number(m && m.id) || 0;
      if (id > maxId) maxId = id;
    }
    return maxId;
  }

  function fillComposerText(text, autoSend) {
    const taEl = document.getElementById('ta');
    if (!taEl) return;
    taEl.value = text;
    taEl.dispatchEvent(new Event('input', { bubbles: true }));
    if (autoSend && typeof send === 'function') {
      send();
    } else {
      taEl.focus();
    }
  }

  function renderOnboarding(container) {
    const state = typeof S !== 'undefined' ? S : null;
    const contacts = typeof CONTACTS !== 'undefined' ? CONTACTS : [];
    const model = buildOnboardingState(state, contacts);

    const lang = resolveLang(getLangPref());
    const starters = lang === 'en'
      ? [
          'Summarize the project structure and main entry points',
          'Let us discuss a design plan for a new feature',
          'Help investigate a recent error or failing test',
        ]
      : [
          '先帮我梳理这个项目的目录和核心入口',
          '我想做一个新功能，先一起讨论方案',
          '帮我排查最近的一处报错原因',
        ];
    const card = document.createElement('section');
    card.id = 'roomOnboarding';
    card.className = 'room-onboarding';
    card.setAttribute('aria-label', t('onboard.title'));

    const step1Done = model.roomAis.length > 0;
    const step1Class = step1Done ? 'is-done' : 'is-active';
    const step2Class = !step1Done ? 'is-disabled' : 'is-active';
    const step3Class = !step1Done ? 'is-disabled' : '';

    const step1Desc = step1Done
      ? t('onboard.step1Ready').replace('{n}', String(model.roomAis.length))
      : t('onboard.step1Empty');
    const chipsHtml = step1Done
      ? '<div class="onboard-ai-chips">' + model.roomAis.map(a =>
          '<span class="onboard-ai-chip" style="--c:' + htmlEsc(a.color) + '"><span class="onboard-ai-dot"></span>' + htmlEsc(a.label) + '</span>'
        ).join('') + '</div>'
      : '';
    const step1Actions = step1Done
      ? '<button type="button" data-onboard-action="manage">' + htmlEsc(t('onboard.manageMembers')) + '</button>'
        + '<button type="button" data-onboard-action="connect">' + htmlEsc(t('onboard.addMoreAi')) + '</button>'
      : '<button type="button" class="pri" data-onboard-action="connect">' + htmlEsc(t('onboard.addAi')) + '</button>'
        + (model.availableContactAis.length
          ? '<button type="button" data-onboard-action="manage">' + htmlEsc(t('onboard.pickFromContacts')) + '</button>'
          : '');

    const step2Body = step1Done
      ? '<p>' + htmlEsc(t('onboard.step2Desc')) + '</p>'
        + '<div class="onboard-prompt-preview">' + htmlEsc(model.testPrompt) + '</div>'
        + '<div class="onboard-actions">'
        + '<button type="button" class="pri" data-onboard-action="send-test">' + htmlEsc(t('onboard.sendTest')) + '</button>'
        + '<button type="button" data-onboard-action="fill-test">' + htmlEsc(t('onboard.fillTest')) + '</button>'
        + '</div>'
      : '<p>' + htmlEsc(t('onboard.step2NeedAi')) + '</p>'
        + '<div class="onboard-actions"><button type="button" disabled>' + htmlEsc(t('onboard.sendTest')) + '</button></div>';

    const step3Body = '<p>' + htmlEsc(t('onboard.step3Desc')) + '</p>'
      + '<div class="onboard-starters">' + starters.map((s, idx) =>
        '<button type="button" class="onboard-starter" data-onboard-starter="' + idx + '"' + (step1Done ? '' : ' disabled') + '>' + htmlEsc(s) + '</button>'
      ).join('') + '</div>';

    card.innerHTML =
      '<div class="onboard-head"><h2>' + htmlEsc(t('onboard.title')) + '</h2><p>' + htmlEsc(t('onboard.subtitle')) + '</p></div>'
      + '<div class="onboard-steps">'
      +   '<div class="onboard-step ' + step1Class + '"><span class="onboard-step-num">' + (step1Done ? '✓' : '1') + '</span><div class="onboard-step-body"><h3>' + htmlEsc(t('onboard.step1Title')) + '</h3><p>' + htmlEsc(step1Desc) + '</p>' + chipsHtml + '<div class="onboard-actions">' + step1Actions + '</div></div></div>'
      +   '<div class="onboard-step ' + step2Class + '"><span class="onboard-step-num">2</span><div class="onboard-step-body"><h3>' + htmlEsc(t('onboard.step2Title')) + '</h3>' + step2Body + '</div></div>'
      +   '<div class="onboard-step ' + step3Class + '"><span class="onboard-step-num">3</span><div class="onboard-step-body"><h3>' + htmlEsc(t('onboard.step3Title')) + '</h3>' + step3Body + '</div></div>'
      + '</div>';

    card.onclick = async e => {
      const actionBtn = e.target.closest('[data-onboard-action]');
      if (actionBtn) {
        const act = actionBtn.dataset.onboardAction;
        if (act === 'connect') {
          if (typeof pushModalBack === 'function' && card.closest('#appSettingsModal')) {
            pushModalBack(() => openAppSettings('tutorial'));
          }
          if (typeof startConnectionWizard === 'function') startConnectionWizard('', 'ai');
          else if (typeof openConnection === 'function') openConnection();
        } else if (act === 'manage') {
          if (typeof pushModalBack === 'function' && card.closest('#appSettingsModal')) {
            pushModalBack(() => openAppSettings('tutorial'));
          }
          if (typeof openAgents === 'function') openAgents();
        } else if (act === 'fill-test') {
          hideModal();
          fillComposerText(model.testPrompt, false);
        } else if (act === 'send-test') {
          if (S?.meeting !== state.meeting) return;
          verifyTracker = {
            roomId: state.meeting,
            baselineMaxId: currentMaxMessageId(),
            targetAiIds: model.roomAiIds.slice(),
            prompt: model.testPrompt,
            dismissed: false,
          };
          verifySig = '';
          actionBtn.disabled = true;
          const attempt = verifyTracker;
          const [ok, data] = await post(api('send'), {text:model.testPrompt});
          if (verifyTracker !== attempt || S?.meeting !== state.meeting) return;
          if (!ok) {
            verifyTracker = null;
            actionBtn.disabled = false;
            alert(data.error || '发送失败，请重试。');
          } else {
            if (card.isConnected) hideModal();
            poll();
          }
        }
        return;
      }
      const starterBtn = e.target.closest('[data-onboard-starter]');
      if (starterBtn) {
        const text = starters[Number(starterBtn.dataset.onboardStarter)];
        if (text) { hideModal(); fillComposerText(text, false); }
      }
    };

    container.appendChild(card);
  }

  function syncVerificationBanner() {
    const feedEl = document.getElementById('feed');
    if (!feedEl) return;
    const state = typeof S !== 'undefined' ? S : null;
    if (verifyTracker && (!state || state.meeting !== verifyTracker.roomId)) {
      verifyTracker = null;
    }
    const messages = typeof msgById !== 'undefined' && msgById ? Object.values(msgById) : [];
    const runningIds = (typeof lastRun !== 'undefined' && lastRun && lastRun.running) || [];
    const model = buildVerificationTrackerState(state, messages, runningIds, verifyTracker);
    const existing = document.getElementById('roomVerifyBanner');
    if (!model.active) {
      if (existing) existing.remove();
      verifySig = '';
      return;
    }

    const lang = resolveLang(getLangPref());
    const sig = JSON.stringify({ lang, model });
    if (existing && verifySig === sig) return;
    verifySig = sig;

    const statusLabel = st => st === 'replied' ? t('verify.replied')
      : st === 'running' ? t('verify.running')
      : st === 'failed' ? t('verify.failed')
      : t('verify.waiting');
    const summaryText = (model.allReplied ? t('verify.doneTitle') : t('verify.runningTitle'))
      .replace('{done}', String(model.repliedCount))
      .replace('{total}', String(model.totalCount));

    const banner = existing || document.createElement('div');
    banner.id = 'roomVerifyBanner';
    banner.className = 'room-verify-banner' + (model.allReplied ? ' is-done' : '');
    banner.setAttribute('role', 'status');
    banner.innerHTML =
      '<span class="room-verify-summary">' + htmlEsc(summaryText) + '</span>'
      + '<div class="room-verify-chips">' + model.items.map(item =>
        '<span class="verify-chip is-' + htmlEsc(item.status) + '" title="' + htmlEsc(item.detail || '') + '">'
        + htmlEsc(item.label) + ' · ' + htmlEsc(statusLabel(item.status))
        + '</span>'
      ).join('') + '</div>'
      + '<button type="button" class="room-verify-close">' + htmlEsc(t('verify.dismiss')) + '</button>';

    const closeBtn = banner.querySelector('.room-verify-close');
    if (closeBtn) {
      closeBtn.onclick = () => {
        if (verifyTracker) verifyTracker.dismissed = true;
        banner.remove();
        verifySig = '';
      };
    }

    if (!existing) feedEl.insertBefore(banner, feedEl.firstChild);
  }

  function activeProjectId() {
    if (typeof S !== 'undefined' && S && S.project) return S.project;
    if (typeof ROOMS !== 'undefined' && typeof RID !== 'undefined' && RID) {
      const rm = ROOMS.find(r => r.id === RID);
      if (rm && rm.project) return rm.project;
    }
    return '';
  }

  function isLocalWorkspace() {
    return !(typeof agCat !== 'undefined' && agCat && agCat.local_workspace === false);
  }

  function ensureRoomTools(aiId) {
    const key = RID + ':' + aiId;
    if (toolsCache.has(key)) return toolsCache.get(key);
    if (toolsRequests.has(key)) return toolsRequests.get(key);
    const request = fetch(api('tools') + '?ai=' + encodeURIComponent(aiId), { cache: 'no-store' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && toolsRequests.get(key) === request) toolsCache.set(key, data);
        return data;
      })
      .catch(() => null)
      .finally(() => { if (toolsRequests.get(key) === request) toolsRequests.delete(key); });
    toolsRequests.set(key, request);
    return request;
  }

  let inspectedStep = null;
  let changesPaneSignature = '';

  function drawChangesPane() {
    const pane = document.getElementById('sideChangesPane');
    if (!pane) return;
    const room = S?.meeting;
    if (inspectedStep?.room !== room) inspectedStep = room ? {room, seq:null} : null;
    const rows = (S?.steps || []).slice().reverse();
    if (inspectedStep?.archived && !rows.some(row => row.seq === inspectedStep.seq)) rows.push(inspectedStep.archived);
    const step = rows.find(row => row.seq === inspectedStep?.seq) || rows[0];
    const signature = JSON.stringify([room, rows, step?.seq, S?.steps_undone]);
    if (signature === changesPaneSignature) return;
    changesPaneSignature = signature;
    if (!step) {
      pane.innerHTML = '<p class="hint">这场会话还没有记录到文件改动。</p>';
      return;
    }
    const undone = (S?.steps_undone || []).includes(step.seq);
    pane.innerHTML = '<label class="change-step-label">改动步骤<select data-change-step>' + rows.map(row =>
      '<option value="' + esc(String(row.seq)) + '"' + (row.seq === step.seq ? ' selected' : '') + '>第 ' + esc(String(row.seq)) + ' 步 · ' + esc(row.ai) + ' · ' + esc(row.time || '') + '</option>').join('')
      + '</select></label><div class="change-files">' + step.files.map(file => '<button type="button" data-change-file="' + esc(file.path) + '" aria-pressed="false"><span>' + esc(file.st) + '</span>' + esc(file.path) + '</button>').join('')
      + '</div><div class="change-diff" aria-live="polite">选择文件查看差异。</div>'
      + (undone ? '<p class="hint">这一步已撤回。</p>' : '<button type="button" data-change-undo>预览撤回这一步</button>');
    pane.querySelector('[data-change-step]').onchange = event => openStepChanges(Number(event.target.value));
    const undo = pane.querySelector('[data-change-undo]');
    if (undo) undo.onclick = () => undoStep(step.seq);
    const output = pane.querySelector('.change-diff');
    let diffRequest = null;
    pane.querySelectorAll('[data-change-file]').forEach(button => {
      button.onclick = async () => {
        const request = {};
        diffRequest = request;
        pane.querySelectorAll('[data-change-file]').forEach(file => file.setAttribute('aria-pressed', String(file === button)));
        output.textContent = '正在读取差异…';
        const [ok, data] = await post(api('step/diff'), {step:step.seq, path:button.dataset.changeFile});
        if (room !== S?.meeting || diffRequest !== request || !output.isConnected) return;
        if (!ok || !data.diff) {
          output.textContent = data.reason || data.error || '这份文件没有可显示的差异。';
          return;
        }
        const pre = document.createElement('pre');
        pre.tabIndex = 0;
        for (const line of data.diff.split('\n')) {
          const span = document.createElement('span');
          if (line.startsWith('+') && !line.startsWith('+++')) span.className = 'diff-add';
          else if (line.startsWith('-') && !line.startsWith('---')) span.className = 'diff-remove';
          span.textContent = line || '\u00a0';
          pre.appendChild(span);
        }
        output.replaceChildren(pre);
      };
    });
  }

  async function openStepChanges(seq) {
    const room = S?.meeting;
    if (!room || !Number.isInteger(seq)) return;
    const request = {room, seq, archived:null};
    inspectedStep = request;
    if (!(S.steps || []).some(row => row.seq === seq)) {
      const [ok, data] = await post(api('step/info'), {step:seq});
      if (room !== S?.meeting || inspectedStep !== request) return;
      if (!ok) return alert('这一步的改动记录已不可用。');
      request.archived = data.step;
    }
    openInspectorTab('changes');
  }

  function attachRoomFeedback(message, element) {
    if (message.step != null) {
      const inspect = document.createElement('button');
      inspect.type = 'button';
      inspect.className = 'inspect-step';
      inspect.textContent = '查看改动';
      inspect.onclick = () => openStepChanges(message.step);
      element.appendChild(inspect);
    }
    if (!message.approval && !message.failure) return;
    element.classList.add('has-room-feedback');
    const controls = document.createElement('div');
    controls.className = 'room-feedback';
    controls.dataset.feedbackId = message.id;
    controls.innerHTML = '<span class="room-feedback-state"></span><div class="room-feedback-actions"></div><p class="room-feedback-error" role="status" hidden></p>';
    element.appendChild(controls);
  }

  function syncRoomFeedback() {
    const room = S?.meeting;
    if (!room) return;
    feed.querySelectorAll('[data-feedback-id]').forEach(card => {
      const id = Number(card.dataset.feedbackId), message = msgById[id];
      if (!message) return;
      const approval = message.approval;
      const failure = message.failure;
      const agent = S.ais?.[(approval || failure).ai];
      const active = approval ? agent?.approval?.id === approval.id : agent?.failure === id && !agent.busy && failure.retryable;
      const signature = JSON.stringify([active, S.mode, S.running, S.queued, S.steps_undone, (S.claims || []).map(claim => claim.key)]);
      if (card.dataset.state === signature) return;
      card.dataset.state = signature;
      card.closest('.msg').classList.toggle('awaiting-confirmation', Boolean(approval && active));
      card.closest('.msg').classList.toggle('execution-failed', Boolean(failure));
      const note = card.querySelector('.room-feedback-state');
      const actions = card.querySelector('.room-feedback-actions');
      const error = card.querySelector('.room-feedback-error');
      actions.replaceChildren();
      error.hidden = true;
      let submitting = false;
      function addAction(label, url, payload, confirmText) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = label;
        button.onclick = async () => {
          if (submitting) return;
          if (confirmText && !window.confirm(confirmText)) return;
          submitting = true;
          actions.querySelectorAll('button').forEach(action => { action.disabled = true; });
          error.hidden = true;
          const [ok, data] = await post(api(url), payload);
          if (room !== S?.meeting || !card.isConnected) return;
          if (!ok) {
            submitting = false;
            error.textContent = data.error || '操作失败，请重试。';
            error.hidden = false;
            actions.querySelectorAll('button').forEach(action => { action.disabled = false; });
          } else {
            actions.replaceChildren();
            note.textContent = approval ? '确认已提交。' : '已安排重试。';
            poll();
          }
        };
        actions.appendChild(button);
      }
      if (approval) {
        note.textContent = active ? '这次操作需要你确认。' : '确认已结束。';
        if (active) {
          addAction('仅允许这次', 'turn/approval', {id:approval.id, decision:'allow'});
          addAction('拒绝', 'turn/approval', {id:approval.id, decision:'deny'});
        }
        return;
      }
      note.textContent = failure.changes === 'recorded' ? '这一步有已记录的文件改动。'
        : failure.changes === 'unknown' ? '这一步的改动无法确认，请先检查工作区。' : '这一步在讨论模式下失败。';
      if (failure.step != null) {
        const inspect = document.createElement('button');
        inspect.type = 'button';
        inspect.textContent = '查看改动';
        inspect.onclick = () => openStepChanges(failure.step);
        actions.appendChild(inspect);
      }
      if (!active) return;
      addAction(failure.mode === 'work' ? '保留现状并重试' : '重试', 'turn/retry', {id, action:'continue'},
        failure.changes === 'unknown' ? '这一步可能已修改文件。确认按当前工作区状态重试？' : '');
      if (failure.undo_possible) {
        post(api('turn/retry/preview'), {id}).then(([ok, data]) => {
          if (submitting || room !== S?.meeting || !card.isConnected || card.dataset.state !== signature) return;
          if (ok) addAction('撤回后重试', 'turn/retry', {id, action:'undo'}, '撤回这一步的 ' + data.plan.items.length + ' 个文件改动后重试？');
        });
      }
    });
  }

  // ---- Right Inspector ----
  function setSideTab(tab) {
    const valid = ['agents', 'board', 'output', 'changes'].includes(tab) ? tab : 'agents';
    currentSideTab = valid;
    safeStorageSet(SIDE_TAB_KEY, valid);
    const side = document.getElementById('side');
    if (!side) return;
    side.querySelectorAll('[data-side-tab]').forEach(btn => {
      btn.setAttribute('aria-selected', String(btn.dataset.sideTab === valid));
    });
    side.querySelectorAll('[data-side-group]').forEach(el => {
      el.hidden = el.dataset.sideGroup !== valid;
    });
    if (valid === 'agents') drawSideAgentsPane();
    if (valid === 'changes') drawChangesPane();
  }

  function openInspectorTab(tab) {
    setSideTab(tab);
    if (typeof setMeetingSide === 'function') setMeetingSide(true);
    const btn = document.getElementById('sideToggleBtn');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }

  function drawSideAgentsPane() {
    const pane = document.getElementById('sideAgentsPane');
    if (!pane) return;
    const state = typeof S !== 'undefined' ? S : null;
    const contacts = typeof CONTACTS !== 'undefined' ? CONTACTS : [];
    const aiIds = getRoomAiIds(state);
    if (!state || !state.meeting || !aiIds.length) {
      pane.innerHTML = '<p class="hint">当前会话还没有 AI 成员。可在会话管理中邀请成员。</p>';
      return;
    }
    pane.innerHTML = aiIds.map(id => {
      const x = (state.ais && state.ais[id]) || {};
      const mo = x.model || {};
      const desktop = isDesktopManaged(state, id);
      const name = agentDisplayName(state, contacts, id);
      const color = typeof agentColor === 'function' ? agentColor(id) : '#888';
      const endpointLabel = desktop ? t('composer.desktopManaged') : ((state.execution && state.execution[id] && state.execution[id].endpoint) || 'CLI').toUpperCase();
      const modelDesc = desktop
        ? (mo.observed && mo.observed.model ? '实际回报：' + mo.observed.model : t('composer.desktopManaged'))
        : ((mo.model || mo.observed?.model) ? (mo.label || mo.model || mo.observed.model) : '跟随接入设置');
      const ctxDesc = typeof ctxTitle === 'function' ? ctxTitle(x) : '';
      const isDirectModel = state.agents?.some(agent => agent.id === id && agent.http_protocol === 'openai_chat');
      const permBlocked = !isDirectModel && state.mode === 'work' && state.permissions && state.permissions[id] && state.permissions[id].work === false;
      const [activity, activityClass] = x.approval ? ['等你确认', 'is-approval']
        : x.busy ? ['运行中', 'is-running'] : x.failure != null ? ['执行失败', 'is-failed'] : [];
      return '<div class="side-agent-card" data-side-agent="' + esc(id) + '">'
        + '<div class="side-agent-head"><span class="side-agent-dot" style="--c:' + esc(color) + '"></span>'
        + '<span class="side-agent-name">' + esc(name) + '</span>'
        + '<span class="side-agent-badge' + (desktop ? ' desktop' : '') + '">' + esc(endpointLabel) + '</span></div>'
        + (activity ? '<p class="side-agent-meta side-agent-activity ' + activityClass + '">' + esc(activity) + '</p>' : '')
        + (permBlocked ? '<p class="side-agent-meta" style="color:var(--work)">当前会议已切到干活模式，但此成员未开启「允许干活」权限，仍将只读。</p>' : '')
        + '<p class="side-agent-meta">' + esc(modelDesc) + (isDirectModel ? '<br>仅参与文字讨论' : ctxDesc ? '<br>' + esc(ctxDesc) : '') + '</p>'
        + '<div class="side-agent-actions">'
        + (permBlocked ? '<button type="button" data-open-perms="' + esc(id) + '">开启允许干活</button>' : '')
        + '<button type="button" data-open-ai="' + esc(id) + '">模型与执行端</button>'
        + '</div></div>';
    }).join('');
  }

  // ---- Composer Bar + Model Popover ----
  function syncComposerBar() {
    const state = typeof S !== 'undefined' ? S : null;
    const contacts = typeof CONTACTS !== 'undefined' ? CONTACTS : [];
    const taEl = document.getElementById('ta');
    const modeBtn = document.getElementById('composerModeBtn');
    const modelBtn = document.getElementById('composerModelBtn');
    const extBtn = document.getElementById('composerExtBtn');
    const targetHint = document.getElementById('composerTargetHint');
    const has = !!(state && state.meeting);
    const work = !!(has && state.mode === 'work');

    const modeTag = document.getElementById('modeTag');
    if (modeTag) modeTag.textContent = work ? t('mode.work') : '';

    if (modeBtn) {
      modeBtn.disabled = !has;
      modeBtn.classList.toggle('work', work);
      modeBtn.textContent = work ? t('mode.work') : t('mode.discuss');
      const restricted = work ? (state.participants || []).filter(id=>state.ais?.[id]&&state.permissions?.[id]?.work===false) : [];
      modeBtn.title = restricted.length ? '仅只读：' + restricted.map(id=>agentDisplayName(state,contacts,id)).join('、') : '切换讨论 / 干活模式';
    }
    if (extBtn) {
      extBtn.disabled = !has;
      extBtn.textContent = t('composer.ext');
    }
    if (modelBtn) {
      const chip = buildModelChipState(taEl ? taEl.value : '', state, contacts);
      modelBtn.disabled = chip.disabled;
      modelBtn.classList.toggle('readonly', chip.readonly);
      modelBtn.classList.toggle('pending', chip.pending);
      modelBtn.innerHTML = (chip.pending ? '<span class="chip-dot" title="' + esc(t('composer.pending')) + '"></span>' : '')
        + '<span class="chip-text">' + esc(chip.label) + '</span>';
      if (targetHint) {
        const blocked = blockedWorkTargets(state, chip.target);
        if (!has || !chip.target.aiIds.length) {
          targetHint.innerHTML = '';
        } else if (blocked.length) {
          const bNames = blocked.map(id => agentDisplayName(state, contacts, id)).join('、');
          targetHint.innerHTML = '<button type="button" data-composer-perms style="border:0;background:none;padding:0;color:var(--work);font:inherit;cursor:pointer" title="点击打开成员与权限设置">'
            + esc(bNames) + ' 仅只读（点此开启允许干活）</button>';
        } else if (chip.target.explicit) {
          const names = (chip.target.mode === 'single' ? [chip.target.aiId] : chip.target.aiIds)
            .map(id => '@' + agentDisplayName(state, contacts, id));
          targetHint.textContent = t('composer.sendTo') + ' ' + names.join(' ');
        } else {
          targetHint.textContent = '';
        }
      }
    }
  }

  function closeComposerPopover() {
    const pop = document.getElementById('composerPopover');
    const btn = document.getElementById('composerModelBtn');
    if (pop) pop.hidden = true;
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }

  function renderComposerModelPopover() {
    const pop = document.getElementById('composerPopover');
    const btn = document.getElementById('composerModelBtn');
    const taEl = document.getElementById('ta');
    if (!pop || !S || !S.meeting) return;
    const target = resolveComposerTarget(taEl ? taEl.value : '', S);
    const list = target.mode === 'single' ? [target.aiId] : target.aiIds;
    if (!list.length) return;

    const rows = list.map(id => {
      const x = (S.ais && S.ais[id]) || {};
      const mo = x.model || {};
      const desktop = isDesktopManaged(S, id);
      const name = agentDisplayName(S, CONTACTS, id);
      const busy = !!(x.busy || (S.running || []).includes(id) || (S.running || []).includes('compact:' + id));
      if (desktop) {
        const reported = mo.observed && mo.observed.model ? mo.observed.model : t('composer.desktopManaged');
        return '<div class="pop-agent-row" data-pop-ai="' + esc(id) + '">'
          + '<div class="pop-agent-top"><b>' + esc(name) + '</b><span class="pop-agent-status">' + esc(t('composer.desktopManaged')) + '</span></div>'
          + '<div class="pop-agent-foot"><span>' + esc(reported) + '</span>'
          + '<button type="button" data-pop-open="' + esc(id) + '">' + esc(t('composer.openFull')) + '</button></div></div>';
      }
      const models = mo.models || [];
      const curModel = mo.model || '';
      const efforts = typeof modelEfforts === 'function' ? modelEfforts(mo, curModel) : (mo.efforts || []);
      const curEffort = mo.effort || '';
      const statusText = busy ? t('composer.busy') : (mo.apply_status === 'pending' ? t('composer.pending') : ((mo.model || mo.observed?.model) ? (mo.label || '') : ''));
      const modelOptions = '<option value="">跟随接入设置</option>'
        + models.map(v => '<option value="' + esc(v) + '"' + (v === curModel ? ' selected' : '') + '>' + esc(modelOptionLabel(mo, v)) + '</option>').join('');
      const effortOptions = efforts.length
        ? '<label class="pop-agent-field"><span>' + esc(t('composer.effortField')) + '</span><select data-pop-effort="' + esc(id) + '"' + (busy ? ' disabled' : '') + '><option value="">跟随接入设置</option>'
          + efforts.map(e => '<option value="' + esc(e) + '"' + (e === curEffort ? ' selected' : '') + '>' + esc((EFFORT_LABELS[e] || e)) + '</option>').join('') + '</select></label>'
        : '';
      return '<div class="pop-agent-row" data-pop-ai="' + esc(id) + '">'
        + '<div class="pop-agent-top"><b>' + esc(name) + '</b><span class="pop-agent-status">' + esc(statusText) + '</span></div>'
        + '<div class="pop-agent-controls"><label class="pop-agent-field"><span>' + esc(t('composer.modelField')) + '</span><select data-pop-model="' + esc(id) + '"' + (busy ? ' disabled' : '') + '>' + modelOptions + '</select></label>' + effortOptions + '</div>'
        + '<div class="pop-agent-foot"><button type="button" data-pop-open="' + esc(id) + '">' + esc(t('composer.openFull')) + '</button>'
        + '<button type="button" class="pri" data-pop-save="' + esc(id) + '"' + (busy ? ' disabled' : '') + '>' + esc(t('composer.save')) + '</button></div></div>';
    }).join('');

    pop.innerHTML = '<div class="composer-popover-head"><strong>' + esc(t('composer.model')) + '</strong><button type="button" id="popCloseBtn" aria-label="关闭">&times;</button></div>' + rows;
    pop.hidden = false;
    if (btn) btn.setAttribute('aria-expanded', 'true');
    const closeBtn = document.getElementById('popCloseBtn');
    if (closeBtn) closeBtn.onclick = closeComposerPopover;
  }

  // ---- Slash Skill & Command Autocomplete ----
  function invalidateRoomTools(rid, aiId) {
    if (!rid) return;
    for (const cache of [toolsCache, toolsRequests]) {
      if (aiId) cache.delete(rid + ':' + aiId);
      else for (const key of cache.keys()) if (key.startsWith(rid + ':')) cache.delete(key);
    }
  }

  function isToolConfigurable(aiId) {
    if (!S || !aiId || isDesktopManaged(S, aiId)) return false;
    const spec = (typeof agentMeta === 'function' ? agentMeta(aiId) : null) || {};
    const x = (S.ais && S.ais[aiId]) || {};
    return ['claude', 'codex'].includes(spec.driver) || Boolean(x.caps && x.caps.tools);
  }

  function openSlashSkillsModal(preferredAi) {
    if (!S || !S.meeting) { openAppSettings('extensions'); return; }
    const aiIds = getRoomAiIds(S);
    const configurable = aiIds.filter(isToolConfigurable);
    const desktopIds = aiIds.filter(id => isDesktopManaged(S, id));
    const activeAi = (preferredAi && configurable.includes(preferredAi)) ? preferredAi : (configurable[0] || '');
    const canBack = typeof hasModalBack === 'function' && hasModalBack();
    let html = '<div id="slashSkillsModal">'
      + (canBack ? '<div class="connection-heading"><button type="button" class="modal-back" id="skillsBackBtn">← 返回</button><h3>技能与工具配置（当前会话）</h3><button type="button" id="skillsHeaderClose" aria-label="关闭">×</button></div>' : '<h3>技能与工具配置（当前会话）</h3>');
    if (preferredAi && isDesktopManaged(S, preferredAi)) {
      html += '<p class="hint">' + esc(agentDisplayName(S, CONTACTS, preferredAi)) + ' 为桌面端接入，技能与扩展由原软件管理，请在原软件中使用。</p>';
    }
    if (configurable.length > 1) {
      html += '<div class="ext-subtabs" role="tablist" style="margin-bottom:10px">'
        + configurable.map(id => '<button type="button" role="tab" data-skills-ai="' + esc(id) + '" aria-selected="' + String(id === activeAi) + '">' + esc(agentDisplayName(S, CONTACTS, id)) + '</button>').join('')
        + '</div>';
    }
    if (activeAi) {
      html += '<div id="toolsBox"><div class="hint">读取中…</div></div>';
    } else {
      html += '<p class="hint">' + (desktopIds.length ? '当前会话的成员均为桌面端管理，请在原软件中管理技能与工具。' : '当前会话没有可配置的 Agent 成员。') + '</p>';
    }
    html += '<div class="btns" style="margin-top:14px"><button type="button" id="skillsOpenExt">全局扩展与导入</button><button type="button" id="skillsCloseBtn">关闭</button></div></div>';
    showModal(html);
    const backBtn = canBack && document.getElementById('skillsBackBtn');
    if (backBtn) backBtn.onclick = () => popModalBack();
    const headerClose = document.getElementById('skillsHeaderClose');
    if (headerClose) headerClose.onclick = hideModal;
    const closeBtn = document.getElementById('skillsCloseBtn');
    if (closeBtn) closeBtn.onclick = hideModal;
    const extBtn = document.getElementById('skillsOpenExt');
    if (extBtn) extBtn.onclick = () => {
      if (typeof pushModalBack === 'function') pushModalBack(() => openSlashSkillsModal(activeAi));
      openAppSettings('extensions');
    };
    mbox.querySelectorAll('[data-skills-ai]').forEach(btn => {
      btn.onclick = () => openSlashSkillsModal(btn.dataset.skillsAi);
    });
    if (activeAi && typeof loadTools === 'function') {
      loadTools(activeAi, (S.ais && S.ais[activeAi]) || {}, () => openSlashSkillsModal(activeAi));
    }
  }

  async function executeSlashCompact(targetIds, explicitTarget) {
    if (!S || !S.meeting || !RID) return false;
    const aiIds = getRoomAiIds(S);
    const ids = targetIds && targetIds.length ? targetIds : aiIds;
    if (explicitTarget) {
      for (const id of ids) {
        const name = agentDisplayName(S, CONTACTS, id);
        const x = (S.ais && S.ais[id]) || {};
        if (isDesktopManaged(S, id)) {
          alert(name + ' 当前不由 CLI 执行，请在当前执行端压缩。');
          return false;
        }
        if (x.handed_off) {
          alert(name + ' 在终端里，收回来再压。');
          return false;
        }
        if (x.compacting) {
          alert(name + ' 正在压缩中。');
          return false;
        }
        if (x.can_compact === false) {
          alert(name + ' 还没建会话，或暂无可压缩的新记录。');
          return false;
        }
      }
      for (const id of ids) {
        const [ok, j] = await post(api('compact'), { ai: id });
        if (!ok) { alert((j && j.error) || '压缩失败'); return false; }
      }
    } else {
      const compressible = ids.filter(id => {
        const x = (S.ais && S.ais[id]) || {};
        return !isDesktopManaged(S, id) && !x.handed_off && !x.compacting && x.can_compact !== false;
      });
      if (!compressible.length) {
        alert('当前没有可压缩的成员（可能尚未建立会话、无可压缩新记录或由桌面端管理）。');
        return false;
      }
      if (compressible.length === aiIds.length) {
        const [ok, j] = await post(api('compact'), {});
        if (!ok) { alert((j && j.error) || '压缩失败'); return false; }
      } else {
        for (const id of compressible) {
          const [ok, j] = await post(api('compact'), { ai: id });
          if (!ok) { alert((j && j.error) || '压缩失败'); return false; }
        }
      }
    }
    await loadState();
    if (typeof poll === 'function') poll();
    return true;
  }

  function showSlashHelpModal() {
    if (typeof showModal !== 'function') return;
    const rows = SLASH_COMMANDS.map(cmd =>
      '<tr><td><code>/' + esc(cmd.name) + (cmd.argsHint ? ' ' + esc(cmd.argsHint) : '') + '</code></td><td>' + esc(cmd.desc) + '</td></tr>'
    ).join('');
    showModal(
      '<div id="slashHelpModal">'
      + '<div class="connection-heading"><h3>全部内置命令</h3><button type="button" id="slashHelpClose" aria-label="关闭">×</button></div>'
      + '<p class="hint">在输入框输入 <code>/</code> 可同时检索内置命令与各 Agent 技能；发送以斜杠开头的普通文字可用 <code>//</code> 开头。</p>'
      + '<div style="max-height:55vh;overflow:auto"><table class="slash-help-table"><tbody>' + rows + '</tbody></table></div>'
      + '</div>'
    );
    const closeBtn = document.getElementById('slashHelpClose');
    if (closeBtn && typeof hideModal === 'function') closeBtn.onclick = hideModal;
  }

  async function executeSlashCommand(command, targetIds, explicitTarget, argText = '') {
    closeSlashMenu();
    const targetId = targetIds && targetIds[0] ? targetIds[0] : '';
    switch (command) {
      case 'skills':
        openSlashSkillsModal(targetId);
        return true;
      case 'compact':
        return await executeSlashCompact(targetIds || [], explicitTarget);
      case 'mode': {
        const arg = String(argText || '').trim().toLowerCase();
        if (!arg) {
          if (typeof toggleMode === 'function') await toggleMode();
          return true;
        }
        const want = (arg === 'work' || arg === '干活') ? 'work' : ((arg === 'discuss' || arg === '讨论') ? 'discuss' : '');
        if (!want) { alert('用法：/mode discuss 或 /mode work'); return false; }
        if (S && S.mode === want) return true;
        if (want === 'work' && !confirm('切到干活模式？\n\n开启干活权限的成员可改文件与跑命令（每一步支持按步撤回）。')) return false;
        const [ok, j] = await post(api('mode'), { mode: want });
        if (!ok) { alert((j && j.error) || '切换模式失败'); return false; }
        await loadState();
        if (typeof poll === 'function') poll();
        return true;
      }
      case 'model':
        if (targetId && typeof openAi === 'function') openAi(targetId);
        else document.getElementById('composerModelBtn')?.click();
        return true;
      case 'stop':
        if (typeof stopAi === 'function') await stopAi(targetId);
        return true;
      case 'debate': {
        const btn = document.getElementById('debateBtn');
        if (btn) btn.click();
        if (argText) {
          setTimeout(() => {
            const topicEl = document.querySelector('#debateForm [name="topic"]');
            if (topicEl && !topicEl.value) topicEl.value = argText;
          }, 0);
        }
        return true;
      }
      case 'debate-continue': {
        if (typeof canContinueDebate !== 'function' || !canContinueDebate()) {
          alert('当前没有可继续的论道。');
          return false;
        }
        openDebateContinue();
        const feedback = document.querySelector('#debateContinueForm [name="feedback"]');
        if (!feedback) return false;
        feedback.value = argText;
        return true;
      }
      case 'debate-finish': {
        const [ok, j] = await post(api('debate/finish'), {});
        if (!ok) { alert((j && j.error) || '当前没有可结束的论道'); return false; }
        if (S && j && j.debate) S.debate = j.debate;
        if (typeof drawDebate === 'function') drawDebate();
        if (typeof poll === 'function') poll();
        return true;
      }
      case 'wrapup':
        document.getElementById('bWrap')?.click();
        return true;
      case 'status':
        if (typeof setMeetingSide === 'function') setMeetingSide(true);
        else document.getElementById('sideToggleBtn')?.click();
        return true;
      case 'agents':
        if (typeof openAgents === 'function') await openAgents();
        else document.getElementById('bAgents')?.click();
        return true;
      case 'scan':
        if (typeof openDiscoveryModal === 'function') await openDiscoveryModal(true);
        return true;
      case 'connect':
        if (targetId && typeof openAi === 'function' && S && S.ais && S.ais[targetId]) openAi(targetId);
        else if (targetId && typeof openAgentSettings === 'function') await openAgentSettings(targetId);
        else if (typeof openAgentManager === 'function') await openAgentManager();
        return true;
      case 'invite':
        if (typeof openConnection === 'function') openConnection();
        else document.getElementById('bAdd')?.click();
        return true;
      case 'handoff':
      case 'return': {
        let ai = targetId;
        if (!ai && S && S.ais) {
          const candidates = Object.keys(S.ais).filter(id => command === 'return' ? S.ais[id].handed_off : !S.ais[id].handed_off);
          if (candidates.length === 1) ai = candidates[0];
        }
        if (!ai) { alert('请指定要操作的 @成员，例如：/' + command + ' claude'); return false; }
        const [ok, j] = await post(api('handoff'), { ai, on: command === 'handoff' });
        if (!ok) { alert((j && j.error) || '操作失败'); return false; }
        await loadState();
        if (typeof poll === 'function') poll();
        if (command === 'handoff' && typeof openAi === 'function') openAi(ai);
        return true;
      }
      case 'announce':
        if (argText) {
          const [ok, j] = await post(api('announcement'), { text: argText });
          if (!ok) { alert((j && j.error) || '公告保存失败'); return false; }
          await loadState();
          if (typeof poll === 'function') poll();
        } else {
          document.getElementById('annBtn')?.click();
        }
        return true;
      case 'todo':
        if (!argText) {
          const ann = document.getElementById('ann');
          if (ann) ann.classList.add('open');
          document.getElementById('bText')?.focus();
          return false;
        }
        if (typeof boardPost === 'function') await boardPost({ op: 'add', kind: 'todo', text: argText });
        return true;
      case 'done': {
        const m = String(argText || '').match(/\d+/);
        if (!m) { alert('用法：/done #待办编号'); return false; }
        if (typeof boardPost === 'function') await boardPost({ op: 'done', id: Number(m[0]) });
        return true;
      }
      case 'undo': {
        const steps = ((S && S.steps) || []).filter(st => !st.undone);
        if (!steps.length) {
          if (typeof setMeetingSide === 'function') setMeetingSide(true);
          alert('当前会话暂无可撤回的文件修改步骤。');
          return false;
        }
        if (typeof undoStep === 'function') await undoStep(steps[steps.length - 1].seq);
        return true;
      }
      case 'new':
        if (typeof openNew === 'function') await openNew();
        else document.getElementById('bNew')?.click();
        return true;
      case 'resume':
        if (typeof openList === 'function') await openList();
        else document.getElementById('bList')?.click();
        return true;
      case 'project':
        if (typeof openProject === 'function') await openProject();
        return true;
      case 'rename':
        if (argText) {
          const [ok, j] = await post(api('rename'), { title: argText });
          if (!ok) { alert((j && j.error) || '重命名失败'); return false; }
          await loadState();
          if (typeof pollRooms === 'function') await pollRooms();
        } else if (typeof openRename === 'function' && S) {
          openRename(RID, S.title);
        }
        return true;
      case 'help':
        showSlashHelpModal();
        return true;
      case 'quit':
        document.getElementById('quitApp')?.click();
        return true;
      default:
        return false;
    }
  }

  async function handleComposerSlashCommand(text) {
    const parsed = parseComposerSlashCommand(text, S);
    if (!parsed) return { handled: false };
    if (parsed.error) {
      alert(parsed.error);
      return { handled: true, clear: false };
    }
    const ok = await executeSlashCommand(parsed.command, parsed.targetIds, parsed.explicitTarget, parsed.argText);
    return { handled: true, clear: Boolean(ok) };
  }

  exported.handleComposerSlashCommand = handleComposerSlashCommand;
  exported.invalidateRoomTools = invalidateRoomTools;

  function closeSlashMenu() {
    slashRevision++;
    const menu = document.getElementById('slashMenu');
    if (menu) menu.hidden = true;
    slashState = null;
    slashActiveIndex = 0;
  }
  root.closeComposerSlashMenu = closeSlashMenu;

  function renderSlashItem(item, idx, showOwnerTags) {
    const active = idx === slashActiveIndex ? ' active' : '';
    const cmdCls = item.kind === 'command' ? ' is-command' : '';
    let rightHtml = '';
    if (item.kind === 'command') {
      rightHtml = item.argsHint ? '<span class="slash-cmd-arg">' + esc(item.argsHint) + '</span>' : '';
    } else if (showOwnerTags && Array.isArray(item.agentLabels) && item.agentLabels.length) {
      rightHtml = '<span class="slash-item-agents">' + item.agentLabels.map(l => '<span class="slash-agent-tag">' + esc(l) + '</span>').join('') + '</span>';
    }
    return (
      '<button type="button" role="option" aria-selected="' + (idx === slashActiveIndex) + '" class="slash-item' + active + cmdCls + '" data-slash-idx="' + idx + '">'
      + '<span class="slash-item-main"><span class="slash-item-name">/' + esc(item.name) + '</span>'
      + (item.desc ? '<span class="slash-item-desc">' + esc(item.desc) + '</span>' : '') + '</span>'
      + rightHtml
      + '</button>'
    );
  }

  function updateSlashMenu() {
    const taEl = document.getElementById('ta');
    const menu = document.getElementById('slashMenu');
    if (!taEl || !menu || !S || !S.meeting) return closeSlashMenu();
    const roomId = RID, value = taEl.value, cursor = taEl.selectionStart;
    const slash = parseSlashQuery(value, cursor);
    if (!slash) return closeSlashMenu();
    const revision = ++slashRevision;
    const target = resolveComposerTarget(value, S);
    const needIds = (target.mode === 'single' ? [target.aiId] : target.aiIds).filter(id => !isDesktopManaged(S, id));
    const missing = needIds.filter(id => !toolsCache.has(roomId + ':' + id));
    drawSlashMenu(menu, value, cursor, roomId, needIds, missing.length > 0);
    if (!missing.length) return;
    Promise.all(missing.map(ensureRoomTools)).then(() => {
      if (revision !== slashRevision || RID !== roomId || S?.meeting !== roomId || taEl.value !== value || taEl.selectionStart !== cursor) return;
      drawSlashMenu(menu, value, cursor, roomId, needIds, false);
    });
  }

  function drawSlashMenu(menu, value, cursor, roomId, needIds, loading) {
    const toolsByAi = {};
    needIds.forEach(id => { toolsByAi[id] = toolsCache.get(roomId + ':' + id) || null; });
    const model = buildSlashMenuModel(value, cursor, S, toolsByAi, CONTACTS);
    const selected = slashState?.items[slashActiveIndex];
    const selectedIndex = selected ? model.items.findIndex(item => item.kind === selected.kind && item.name === selected.name) : -1;
    slashActiveIndex = Math.max(0, selectedIndex);
    slashState = model;

    let html = '';
    if (model.notice) html += '<div class="slash-notice">' + esc(model.notice) + '</div>';
    if (!model.items.length) {
      if (!model.desktopOnly) html += '<div class="slash-notice">' + esc(loading ? t('composer.loadingSkills') : t('composer.noSkills')) + '</div>';
    } else {
      let cursorIdx = 0;
      if (model.commandItems.length) {
        html += '<div class="slash-section-head"><span>内置命令 · Harness 与会话</span><span class="slash-section-meta">' + model.commandItems.length + ' 项</span></div>';
        html += model.commandItems.map(item => renderSlashItem(item, cursorIdx++, false)).join('');
      }
      if (model.skillItems.length) {
        const ownerMeta = model.singleSkillOwnerLabel
          ? esc(model.singleSkillOwnerLabel) + ' · ' + model.skillItems.length + ' 项'
          : '多成员 · ' + model.skillItems.length + ' 项';
        html += '<div class="slash-section-head"><span>Agent 技能</span><span class="slash-section-meta">' + ownerMeta + '</span></div>';
        html += model.skillItems.map(item => renderSlashItem(item, cursorIdx++, model.showPerSkillOwnerTags)).join('');
      }
    }
    menu.innerHTML = html;
    menu.hidden = false;
  }

  function moveSlashSelection(step) {
    const menu = document.getElementById('slashMenu');
    const previous = menu.querySelector('.slash-item.active');
    previous?.classList.remove('active');
    previous?.setAttribute('aria-selected', 'false');
    const count = slashState.items.length;
    slashActiveIndex = (slashActiveIndex + step + count) % count;
    const next = menu.querySelector('[data-slash-idx="' + slashActiveIndex + '"]');
    next?.classList.add('active');
    next?.setAttribute('aria-selected', 'true');
    next?.scrollIntoView({block:'nearest'});
  }

  async function pickSlashItem(idx, mode = 'execute') {
    if (!slashState || !slashState.items[idx]) return;
    const taEl = document.getElementById('ta');
    if (!taEl) return;
    const item = slashState.items[idx];
    const currentSlash = slashState.slash;
    const currentTarget = slashState.target;
    if (item.kind === 'command') {
      const before = taEl.value.slice(0, currentSlash.start);
      const after = taEl.value.slice(currentSlash.end);
      if (mode === 'tab' || item.fillArgs) {
        taEl.value = before + '/' + item.name + (after.startsWith(' ') ? '' : ' ') + after;
        closeSlashMenu();
        taEl.focus();
        if (typeof saveDraft === 'function') saveDraft();
        syncComposerBar();
        return;
      }
      const stripped = (before + after).replace(/\s{2,}/g, ' ').trim();
      const targetIds = currentTarget.explicit
        ? (currentTarget.mode === 'single' ? [currentTarget.aiId] : currentTarget.aiIds)
        : [];
      const ok = await executeSlashCommand(item.name, targetIds, currentTarget.explicit, '');
      if (ok) {
        taEl.value = /^(?:@[A-Za-z0-9_.-]+\s*)+$/.test(stripped) ? '' : stripped;
        if (typeof saveDraft === 'function') saveDraft();
        syncComposerBar();
      }
      return;
    }
    const applied = applySlashSelection(taEl.value, currentSlash, item, currentTarget);
    taEl.value = applied.text;
    closeSlashMenu();
    taEl.focus();
    if (typeof saveDraft === 'function') saveDraft();
    syncComposerBar();
  }

  // ---- Global Settings Modal (General / Agents / Extensions / About) ----
  async function fetchExtensions(refresh) {
    const pid = activeProjectId();
    const params = new URLSearchParams();
    if (pid) params.set('project_id', pid);
    if (refresh) params.set('refresh', '1');
    const url = '/api/extensions' + (params.toString() ? '?' + params.toString() : '');
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) {
      let msg = r.status === 404 ? '后端扩展接口尚未就绪（待 M1 后端启用后自动加载）。' : ('读取扩展失败（HTTP ' + r.status + '）');
      try { const j = await r.json(); if (j && j.error) msg = j.error; } catch (e) {}
      throw Error(msg);
    }
    return await r.json();
  }

  function renderSettingsShell(activeTab, bodyHtml, heading) {
    const canBack = typeof hasModalBack === 'function' && hasModalBack();
    const tabs = [
      ['general', t('settings.general')],
      ['cloud', t('settings.cloud')],
      ['agents', t('settings.agents')],
      ['extensions', t('settings.extensions')],
      ['tutorial', t('settings.tutorial')],
      ['about', t('settings.about')],
    ];
    return '<div id="appSettingsModal">'
      + '<nav class="settings-nav" aria-label="' + esc(t('settings.title')) + '">'
      + '<div class="settings-nav-title">' + esc(t('settings.title')) + '</div>'
      + tabs.map(([id, label]) => '<button type="button" data-settings-tab="' + id + '" aria-selected="' + String(id === activeTab) + '">' + esc(label) + '</button>').join('')
      + '</nav>'
      + '<div class="settings-main"><div class="settings-head">'
      + (canBack ? '<button type="button" class="modal-back" id="settingsBackBtn">← 返回</button>' : '')
      + '<h3>' + esc(heading) + '</h3>'
      + '<button type="button" class="settings-close" id="settingsCloseBtn" aria-label="关闭">&times;</button></div>'
      + '<div class="settings-body" id="settingsBody">' + bodyHtml + '</div></div></div>';
  }

  function renderGeneralTab() {
    const theme = getThemePref();
    const lang = getLangPref();
    const seg = (attr, val, cur, label) => '<button type="button" data-' + attr + '="' + val + '" aria-pressed="' + String(val === cur) + '">' + esc(label) + '</button>';
    return '<div class="settings-group"><h4>' + esc(t('settings.theme')) + '</h4><p class="hint">' + esc(t('settings.themeHint')) + '</p>'
      + '<div class="settings-segmented">'
      + seg('theme-choice', 'system', theme, t('settings.themeSystem'))
      + seg('theme-choice', 'light', theme, t('settings.themeLight'))
      + seg('theme-choice', 'dark', theme, t('settings.themeDark'))
      + '</div></div>'
      + '<div class="settings-group"><h4>' + esc(t('settings.lang')) + '</h4><p class="hint">' + esc(t('settings.langHint')) + '</p>'
      + '<div class="settings-segmented">'
      + seg('lang-choice', 'auto', lang, t('settings.langAuto'))
      + seg('lang-choice', 'zh-CN', lang, t('settings.langZh'))
      + seg('lang-choice', 'en', lang, t('settings.langEn'))
      + '</div></div>';
  }

  function renderAgentsTab() {
    const {active,presets} = groupAgentSettings(CONTACTS, agCat);
    const rows = agents => agents.map(a => {
      const status = typeof contactStatusLabel === 'function' ? contactStatusLabel(a) : '';
      const channel = typeof contactChannelLabel === 'function' ? contactChannelLabel(a) : (a.driver || '');
      return '<div class="ext-item"><div class="ext-item-top"><b>' + esc(a.label || a.id) + '</b>'
        + '<span class="ext-badge">@' + esc(a.id) + '</span>'
        + '<span class="ext-badge">' + esc(channel) + '</span>'
        + (status ? '<span class="ext-badge">' + esc(status) + '</span>' : '')
        + '<button type="button" style="margin-left:auto" data-settings-agent="' + esc(a.id) + '">配置</button></div></div>';
    }).join('');
    return '<div class="ext-toolbar"><p class="hint" style="margin:0">修改 Agent 的程序路径、默认模型、思考强度与桌面 MCP 接入。</p>'
      + '<div class="ext-actions"><button type="button" id="settingsOpenManager">管理与扫描</button><button type="button" class="pri" id="settingsAddAgent">＋ 接入</button></div></div>'
      + '<div class="ext-list">' + (rows(active) || '<p class="hint">尚未接入 Agent。</p>') + '</div>'
      + (presets.length ? '<details class="connection-advanced"><summary>其他预置 Agent（' + presets.length + '）</summary><div class="ext-list">' + rows(presets) + '</div></details>' : '');
  }

  function renderExtensionsContent(data, errorMsg) {
    const local = isLocalWorkspace();
    const roots = (data && data.skill_roots) || [];
    const importRoots = roots.filter(r => r && r.can_import);
    const items = ((data && data.items) || []).filter(i => i && i.kind === extSubTab);
    const subtabs = [
      ['skill', t('ext.skill')],
      ['plugin', t('ext.plugin')],
      ['mcp', t('ext.mcp')],
    ];
    let html = '<div class="ext-toolbar"><div class="ext-subtabs" role="tablist">'
      + subtabs.map(([id, label]) => '<button type="button" role="tab" data-ext-subtab="' + id + '" aria-selected="' + String(id === extSubTab) + '">' + esc(label) + '</button>').join('')
      + '</div><div class="ext-actions">'
      + (local && extSubTab === 'skill' && importRoots.length ? '<button type="button" class="pri" id="extImportToggle">' + esc(t('ext.import')) + '</button>' : '')
      + '<button type="button" id="extRefreshBtn">' + esc(t('ext.refresh')) + '</button>'
      + '</div></div>';

    if (errorMsg) {
      return html + '<p class="ext-error" role="alert">' + esc(errorMsg) + '</p>';
    }

    if (extImportOpen && local && extSubTab === 'skill' && importRoots.length) {
      const agents = [...new Set(importRoots.map(r => r.agent_id))];
      const pid = activeProjectId();
      const desktopBridge = window.anyDesktop || window.cojamDesktop;
      const canPick = Boolean(desktopBridge && desktopBridge.canChooseWorkdir());
      html += '<div class="ext-import-box" id="extImportBox"><h4>' + esc(t('ext.import')) + '</h4>'
        + '<div class="ext-import-grid">'
        + '<label>目标 Agent<select id="extImpAgent">' + agents.map(a => '<option value="' + esc(a) + '">' + esc(a) + '</option>').join('') + '</select></label>'
        + '<label>导入范围<select id="extImpScope"><option value="user">个人（全局）</option>' + (pid ? '<option value="project">当前项目</option>' : '') + '</select></label>'
        + '<label class="full">本地技能文件夹路径（含 SKILL.md）<div class="ext-import-path-row"><input id="extImpPath" placeholder="例如：D:\\skills\\my-skill">'
        + (canPick ? '<button type="button" id="extImpPick">选择文件夹</button>' : '') + '</div></label>'
        + '</div><p class="ext-error" id="extImpErr" role="alert"></p>'
        + '<div class="btns" style="margin-top:10px"><button type="button" id="extImpCancel">取消</button><button type="button" class="pri" id="extImpSubmit">导入</button></div></div>';
    }

    if (extSubTab === 'skill' && roots.length) {
      html += '<div class="ext-roots">' + roots.map(r =>
        '<div class="ext-root-row"><span><b>' + esc(r.agent_id) + '</b> · ' + esc(r.scope === 'project' ? t('ext.scopeProject') : t('ext.scopeUser')) + '</span>'
        + '<span class="ext-root-path">' + esc(r.path || '') + '</span>'
        + (local && r.can_open ? '<button type="button" data-open-root="' + esc(r.id) + '">' + esc(t('ext.openFolder')) + '</button>' : '')
        + '</div>'
      ).join('') + '</div>';
    }

    if (!items.length) {
      html += '<p class="hint">当前分类下暂未发现扩展条目。</p>';
      return html;
    }

    html += '<div class="ext-list">' + items.map(item => {
      const badges = classifyExtensionBadges(item);
      const agents = (item.agent_ids || []).map(a => '<span class="ext-badge">' + esc(a) + '</span>').join('');
      const badgeHtml = badges.map(b => '<span class="ext-badge' + (b.tone ? ' ' + b.tone : '') + '">' + esc(b.label) + '</span>').join('');
      return '<div class="ext-item"><div class="ext-item-top"><b>' + esc(item.name || item.id) + '</b>' + agents + badgeHtml + '</div>'
        + (item.description ? '<p class="ext-item-desc">' + esc(item.description) + '</p>' : '')
        + (item.source ? '<div class="ext-item-meta">' + esc(item.source) + '</div>' : '')
        + '</div>';
    }).join('') + '</div>';
    return html;
  }

  function renderAboutTab() {
    return '<div class="settings-group"><h4>AnY · Agents and You</h4>'
      + '<p class="hint" id="aboutVersionText">正在读取版本信息…</p>'
      + '<div class="btns" style="justify-content:flex-start;margin-top:12px">'
      + '<button type="button" class="pri" id="aboutCheckUpdate">检查更新</button></div>'
      + '<div id="aboutUpdateStatus" class="hint" style="margin-top:10px" aria-live="polite"></div></div>';
  }

  async function bindSettingsTab(tab) {
    const body = document.getElementById('settingsBody');
    if (!body) return;
    if (tab === 'general') {
      body.querySelectorAll('[data-theme-choice]').forEach(btn => {
        btn.onclick = () => {
          applyTheme(btn.dataset.themeChoice);
          root.anyCloudAccount?.setPreference('theme', getThemePref());
          openAppSettings('general');
        };
      });
      body.querySelectorAll('[data-lang-choice]').forEach(btn => {
        btn.onclick = () => {
          applyLang(btn.dataset.langChoice);
          root.anyCloudAccount?.setPreference('language', getLangPref());
          openAppSettings('general');
        };
      });
    } else if (tab === 'cloud') {
      root.anyCloudAccount?.mount(body);
    } else if (tab === 'tutorial') {
      renderOnboarding(body);
    } else if (tab === 'agents') {
      const pushSettingsAgentsBack = () => {
        if (typeof pushModalBack === 'function') pushModalBack(() => openAppSettings('agents'));
      };
      const mgr = document.getElementById('settingsOpenManager');
      if (mgr) mgr.onclick = () => { if (typeof openAgentManager === 'function') { pushSettingsAgentsBack(); openAgentManager(); } };
      const add = document.getElementById('settingsAddAgent');
      if (add) add.onclick = () => { if (typeof startConnectionWizard === 'function') { pushSettingsAgentsBack(); startConnectionWizard(); } };
      body.querySelectorAll('[data-settings-agent]').forEach(btn => {
        btn.onclick = () => { if (typeof openAgentSettings === 'function') { pushSettingsAgentsBack(); openAgentSettings(btn.dataset.settingsAgent); } };
      });
    } else if (tab === 'extensions') {
      const loadAndPaint = async (refresh) => {
        body.innerHTML = '<p class="hint">正在扫描扩展…</p>';
        try {
          extensionsCache = await fetchExtensions(refresh);
          body.innerHTML = renderExtensionsContent(extensionsCache, '');
        } catch (err) {
          body.innerHTML = renderExtensionsContent(extensionsCache, err.message);
        }
        wireExtHandlers();
      };
      const wireExtHandlers = () => {
        body.querySelectorAll('[data-ext-subtab]').forEach(btn => {
          btn.onclick = () => { extSubTab = btn.dataset.extSubtab; extImportOpen = false; body.innerHTML = renderExtensionsContent(extensionsCache, ''); wireExtHandlers(); };
        });
        const refBtn = document.getElementById('extRefreshBtn');
        if (refBtn) refBtn.onclick = () => loadAndPaint(true);
        const impBtn = document.getElementById('extImportToggle');
        if (impBtn) impBtn.onclick = () => { extImportOpen = !extImportOpen; body.innerHTML = renderExtensionsContent(extensionsCache, ''); wireExtHandlers(); };
        body.querySelectorAll('[data-open-root]').forEach(btn => {
          btn.onclick = async () => {
            btn.disabled = true;
            const [ok, j] = await post('/api/extensions/open-folder', { root_id: btn.dataset.openRoot });
            btn.disabled = false;
            if (!ok) alert((j && j.error) || '打开目录失败');
          };
        });
        const cancelBtn = document.getElementById('extImpCancel');
        if (cancelBtn) cancelBtn.onclick = () => { extImportOpen = false; body.innerHTML = renderExtensionsContent(extensionsCache, ''); wireExtHandlers(); };
        const pickBtn = document.getElementById('extImpPick');
        const desktopBridge = window.anyDesktop || window.cojamDesktop;
        if (pickBtn && desktopBridge) {
          pickBtn.onclick = async () => {
            try {
              const p = await desktopBridge.chooseWorkdir();
              const inp = document.getElementById('extImpPath');
              if (p && inp) inp.value = p;
            } catch (e) {}
          };
        }
        const subBtn = document.getElementById('extImpSubmit');
        if (subBtn) {
          subBtn.onclick = async () => {
            const errEl = document.getElementById('extImpErr');
            const agent_id = (document.getElementById('extImpAgent') || {}).value;
            const scope = (document.getElementById('extImpScope') || {}).value;
            const source_path = (document.getElementById('extImpPath') || {}).value;
            const check = validateImportPayload({ agent_id, scope, project_id: activeProjectId(), source_path });
            if (!check.ok) { if (errEl) errEl.textContent = check.error; return; }
            subBtn.disabled = true;
            if (errEl) errEl.textContent = '';
            try {
              const r = await fetch('/api/extensions/import-skill', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(check.payload),
              });
              const j = await r.json().catch(() => ({}));
              if (r.status === 409) {
                const cname = j.conflict_name ? '「' + j.conflict_name + '」' : '';
                if (errEl) errEl.textContent = j.error || ('已存在同名技能' + cname + '，已保留原技能。');
                subBtn.disabled = false;
                return;
              }
              if (!r.ok) {
                if (errEl) errEl.textContent = j.error || ('导入失败（HTTP ' + r.status + '）');
                subBtn.disabled = false;
                return;
              }
              extImportOpen = false;
              await loadAndPaint(true);
            } catch (e) {
              if (errEl) errEl.textContent = '导入请求失败，请检查后台连接。';
              subBtn.disabled = false;
            }
          };
        }
      };
      if (extensionsCache) {
        body.innerHTML = renderExtensionsContent(extensionsCache, '');
        wireExtHandlers();
      } else {
        await loadAndPaint(false);
      }
    } else if (tab === 'about') {
      const verEl = document.getElementById('aboutVersionText');
      const statusEl = document.getElementById('aboutUpdateStatus');
      const checkBtn = document.getElementById('aboutCheckUpdate');
      const loadStatus = async (url) => {
        try {
          const r = await fetch(url, { cache: 'no-store' });
          const d = await r.json();
          if (verEl) verEl.textContent = '当前版本：' + (d.current || '未知');
          if (statusEl) {
            if (d.state === 'available') statusEl.textContent = '发现新版本：' + d.latest + '（可点击左下角「更新」安装）';
            else if (d.state === 'current') statusEl.textContent = '当前已是最新版本（' + (d.latest || d.current || '') + '）。';
            else if (d.error) statusEl.textContent = d.error;
            else statusEl.textContent = '';
          }
        } catch (e) {
          if (verEl) verEl.textContent = '无法读取版本状态。';
        }
      };
      loadStatus('/api/update/status');
      if (checkBtn) checkBtn.onclick = () => loadStatus('/api/update/check');
    }
  }

  function openAppSettings(tab) {
    settingsTab = tab || settingsTab || 'general';
    const headings = {
      general: t('settings.general'),
      cloud: t('settings.cloud'),
      agents: t('settings.agents'),
      extensions: t('settings.extensions'),
      tutorial: t('settings.tutorial'),
      about: t('settings.about'),
    };
    const bodyHtml = settingsTab === 'general' ? renderGeneralTab()
      : settingsTab === 'agents' ? renderAgentsTab()
      : settingsTab === 'about' ? renderAboutTab()
      : settingsTab === 'tutorial' ? ''
      : '<p class="hint">正在加载…</p>';
    showModal(renderSettingsShell(settingsTab, bodyHtml, headings[settingsTab] || t('settings.title')));
    document.body.classList.remove('nav-open');
    const canBack = typeof hasModalBack === 'function' && hasModalBack();
    const backBtn = canBack && document.getElementById('settingsBackBtn');
    if (backBtn && typeof popModalBack === 'function') backBtn.onclick = () => popModalBack();
    const closeBtn = document.getElementById('settingsCloseBtn');
    if (closeBtn) closeBtn.onclick = hideModal;
    mbox.querySelectorAll('[data-settings-tab]').forEach(btn => {
      btn.onclick = () => openAppSettings(btn.dataset.settingsTab);
    });
    bindSettingsTab(settingsTab);
  }

  function prewarmRoomTools() {
    if (typeof fetch !== 'function' || typeof api !== 'function' || !RID || !S || S.meeting !== RID) return;
    (S.participants || []).filter(id => !isDesktopManaged(S, id)).forEach(id => {
      if (!toolsCache.has(RID + ':' + id)) ensureRoomTools(id);
    });
  }

  // ---- Wire DOM Events ----
  function syncHarnessUi() {
    syncComposerBar();
    setSideTab(currentSideTab);
    prewarmRoomTools();
    syncVerificationBanner();
    syncRoomFeedback();
  }

  root.syncHarnessUi = syncHarnessUi;
  root.attachRoomFeedback = attachRoomFeedback;
  root.drawSideAgentsPane = drawSideAgentsPane;
  root.openAppSettings = openAppSettings;
  root.openInspectorTab = openInspectorTab;

  // Apply persisted preferences immediately
  applyTheme(getThemePref());
  applyLang(getLangPref());
  root.anyCloudAccount?.start({
    read: key => key === 'theme' ? getThemePref() : getLangPref(),
    apply: (key, value) => key === 'theme' ? applyTheme(value) : applyLang(value),
  });
  setSideTab(currentSideTab);

  const openSettingsBtn = document.getElementById('openSettingsBtn');
  if (openSettingsBtn) openSettingsBtn.onclick = () => openAppSettings('general');

  const sideTabs = document.getElementById('sideTabs');
  if (sideTabs) {
    sideTabs.addEventListener('click', e => {
      const btn = e.target.closest('[data-side-tab]');
      if (btn) setSideTab(btn.dataset.sideTab);
    });
  }

  const sideAgentsPane = document.getElementById('sideAgentsPane');
  if (sideAgentsPane) {
    sideAgentsPane.addEventListener('click', e => {
      const permBtn = e.target.closest('[data-open-perms]');
      if (permBtn && typeof openAgents === 'function') {
        if (typeof setMeetingSide === 'function') setMeetingSide(false);
        openAgents();
        return;
      }
      const openBtn = e.target.closest('[data-open-ai]');
      if (openBtn && typeof openAi === 'function') {
        if (typeof setMeetingSide === 'function') setMeetingSide(false);
        openAi(openBtn.dataset.openAi);
        return;
      }
    });
  }

  const composerModeBtn = document.getElementById('composerModeBtn');
  if (composerModeBtn) composerModeBtn.onclick = () => { if (typeof toggleMode === 'function') toggleMode(); };

  const composerTargetHintEl = document.getElementById('composerTargetHint');
  if (composerTargetHintEl) {
    composerTargetHintEl.addEventListener('click', e => {
      if (e.target.closest('[data-composer-perms]') && typeof openAgents === 'function') openAgents();
    });
  }

  const composerExtBtn = document.getElementById('composerExtBtn');
  if (composerExtBtn) composerExtBtn.onclick = () => {
    closeComposerPopover();
    closeSlashMenu();
    if (typeof S !== 'undefined' && S && S.meeting) openSlashSkillsModal();
    else openAppSettings('extensions');
  };

  const composerModelBtn = document.getElementById('composerModelBtn');
  if (composerModelBtn) {
    composerModelBtn.onclick = () => {
      const pop = document.getElementById('composerPopover');
      if (pop && !pop.hidden) closeComposerPopover();
      else { closeSlashMenu(); renderComposerModelPopover(); }
    };
  }

  const composerPopover = document.getElementById('composerPopover');
  if (composerPopover) {
    composerPopover.addEventListener('change', e => {
      const sel = e.target.closest('[data-pop-model]');
      if (!sel || !S || !S.ais) return;
      const aiId = sel.dataset.popModel;
      const mo = (S.ais[aiId] && S.ais[aiId].model) || {};
      const effSel = composerPopover.querySelector('[data-pop-effort="' + aiId + '"]');
      if (!effSel || typeof modelEfforts !== 'function') return;
      const choices = modelEfforts(mo, sel.value);
      effSel.innerHTML = '<option value="">跟随接入设置</option>' + choices.map(c => '<option value="' + esc(c) + '">' + esc(EFFORT_LABELS[c] || c) + '</option>').join('');
      effSel.disabled = !choices.length;
    });
    composerPopover.addEventListener('click', async e => {
      const openBtn = e.target.closest('[data-pop-open]');
      if (openBtn) {
        closeComposerPopover();
        if (typeof openAi === 'function') openAi(openBtn.dataset.popOpen);
        return;
      }
      const saveBtn = e.target.closest('[data-pop-save]');
      if (saveBtn) {
        const aiId = saveBtn.dataset.popSave;
        const modelSel = composerPopover.querySelector('[data-pop-model="' + aiId + '"]');
        const effSel = composerPopover.querySelector('[data-pop-effort="' + aiId + '"]');
        saveBtn.disabled = true;
        const [ok, j] = await post(api('models'), {
          ai: aiId,
          model: modelSel ? modelSel.value : '',
          effort: effSel ? effSel.value : '',
        });
        if (!ok) {
          alert((j && j.error) || '保存失败');
          saveBtn.disabled = false;
          return;
        }
        await loadState();
        renderComposerModelPopover();
      }
    });
  }

  const slashMenu = document.getElementById('slashMenu');
  if (slashMenu) {
    slashMenu.addEventListener('mousedown', e => e.preventDefault());
    slashMenu.addEventListener('click', e => {
      const item = e.target.closest('[data-slash-idx]');
      if (item) pickSlashItem(Number(item.dataset.slashIdx), 'execute');
    });
  }

  const taEl = document.getElementById('ta');
  if (taEl) {
    taEl.addEventListener('input', () => { syncComposerBar(); updateSlashMenu(); });
    taEl.addEventListener('click', () => { syncComposerBar(); updateSlashMenu(); });
    taEl.addEventListener('keyup', e => {
      if (['ArrowLeft', 'ArrowRight'].includes(e.key)) updateSlashMenu();
    });
    taEl.addEventListener('keydown', e => {
      if (!slashState || !slashState.items.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        moveSlashSelection(1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        moveSlashSelection(-1);
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        e.stopImmediatePropagation();
        pickSlashItem(slashActiveIndex, e.key === 'Tab' ? 'tab' : 'execute');
      } else if (e.key === 'Escape') {
        e.preventDefault();
        closeSlashMenu();
      }
    }, true);
  }

  // Also sync composer bar when quick @ buttons are clicked
  const quickBar = document.getElementById('quick');
  if (quickBar) quickBar.addEventListener('click', () => setTimeout(syncComposerBar, 0));

  document.addEventListener('pointerdown', e => {
    const pop = document.getElementById('composerPopover');
    const btn = document.getElementById('composerModelBtn');
    if (pop && !pop.hidden && !pop.contains(e.target) && (!btn || !btn.contains(e.target))) {
      closeComposerPopover();
    }
    const sm = document.getElementById('slashMenu');
    if (sm && !sm.hidden && !sm.contains(e.target) && e.target !== taEl) {
      closeSlashMenu();
    }
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeComposerPopover();
      closeSlashMenu();
    }
  });

  /* ===== gui2: account menu + empty-state greeting ===== */
  (function gui2Shell(){
    const accountBtn=document.getElementById('accountBtn'),accountMenu=document.getElementById('accountMenu');
    if(accountBtn&&accountMenu){
      const setMenu=open=>{
        accountMenu.hidden=!open;
        accountBtn.setAttribute('aria-expanded',String(open));
        if(open){const first=[...accountMenu.querySelectorAll('button')].find(b=>!b.hidden);first&&first.focus()}
      };
      accountBtn.addEventListener('click',e=>{e.stopPropagation();setMenu(accountMenu.hidden)});
      document.addEventListener('click',e=>{
        if(accountMenu.hidden)return;
        if(!accountMenu.contains(e.target)&&!accountBtn.contains(e.target))setMenu(false);
      });
      document.addEventListener('keydown',e=>{
        if(e.key==='Escape'&&!accountMenu.hidden){setMenu(false);accountBtn.focus()}
      });
      accountMenu.addEventListener('click',e=>{if(e.target.closest('button'))setMenu(false)});
    }
    const greetNew=document.getElementById('greetNew'),rNew=document.getElementById('rNew');
    if(greetNew&&rNew)greetNew.addEventListener('click',()=>rNew.click());
    const feedEl=document.getElementById('feed');
    const syncEmpty=()=>{
      if(!document.body)return
      const empty=feedEl&&!feedEl.querySelector('.msg,.agent-progress');
      document.body.classList.toggle('chat-empty',!!empty);
      let noRoom=true;
      try{noRoom=(typeof RID==='undefined')||!RID}catch(e){}
      document.body.classList.toggle('no-room',noRoom);
      if(greetNew)greetNew.hidden=!noRoom;
    };
    if(feedEl&&typeof MutationObserver==='function')new MutationObserver(syncEmpty).observe(feedEl,{childList:true,subtree:true});
    if(typeof setInterval==='function'){const gui2Timer=setInterval(syncEmpty,700);if(gui2Timer&&typeof gui2Timer.unref==='function')gui2Timer.unref()}
    syncEmpty();
  })();
})(typeof window !== 'undefined' ? window : globalThis);
