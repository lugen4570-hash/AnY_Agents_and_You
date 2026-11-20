// Cojam Harness UI (M2 + M3):
// - Theme (system / light / dark) and Language (auto / zh-CN / en)
// - Composer bar (mode, target-aware model chip + popover, extensions shortcut, / skill menu)
// - Right inspector 3-tab controller (Agents / Board / Output) with inline session tools
// - Global Settings center (General / Agents & Connections / Extensions / About & Updates)
(function (root) {
  const THEME_KEY = 'cojam_theme';
  const LANG_KEY = 'cojam_lang';
  const SIDE_TAB_KEY = 'cojam_side_tab';

  const I18N = {
    'zh-CN': {
      'nav.settings': '设置',
      'nav.new': '＋ 新建会话',
      'nav.search': '搜索项目或会话',
      'side.title': '会议详情与看板',
      'side.tabAgents': '成员',
      'side.tabBoard': '看板',
      'side.tabOutput': '产出',
      'mode.discuss': '讨论模式',
      'mode.work': '干活模式',
      'composer.model': '模型',
      'composer.ext': '扩展',
      'composer.hint': '@ 指定成员 · / 技能',
      'composer.placeholder': '有什么新想法？@ 指定成员，/ 调用技能…',
      'composer.desktopManaged': '由桌面端管理',
      'composer.desktopSkillHint': '为桌面端接入，技能由原软件管理，请在原软件中使用。',
      'composer.noSkills': '当前没有可用技能。',
      'composer.sendTo': '将发送给',
      'composer.allAgents': '全员',
      'composer.save': '保存',
      'composer.openFull': '执行端与详情',
      'composer.pending': '下轮生效',
      'composer.busy': '运行中锁定',
      'settings.title': '设置',
      'settings.general': '通用',
      'settings.agents': 'Agent 与连接',
      'settings.extensions': '扩展',
      'settings.about': '关于与更新',
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
    },
    en: {
      'nav.settings': 'Settings',
      'nav.new': '+ New Session',
      'nav.search': 'Search projects or sessions',
      'side.title': 'Session Inspector',
      'side.tabAgents': 'Agents',
      'side.tabBoard': 'Board',
      'side.tabOutput': 'Output',
      'mode.discuss': 'Discuss',
      'mode.work': 'Work',
      'composer.model': 'Models',
      'composer.ext': 'Extensions',
      'composer.hint': '@ mention · / skills',
      'composer.placeholder': 'Type a message… @ to mention, / for skills',
      'composer.desktopManaged': 'Managed by desktop app',
      'composer.desktopSkillHint': 'is connected via desktop MCP. Skills are managed in its host app.',
      'composer.noSkills': 'No enabled skills available.',
      'composer.sendTo': 'To',
      'composer.allAgents': 'All agents',
      'composer.save': 'Save',
      'composer.openFull': 'Endpoint & details',
      'composer.pending': 'Next turn',
      'composer.busy': 'Locked while busy',
      'settings.title': 'Settings',
      'settings.general': 'General',
      'settings.agents': 'Agents & Connections',
      'settings.extensions': 'Extensions',
      'settings.about': 'About & Updates',
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
    },
  };

  function safeStorageGet(key, fallback) {
    try { return localStorage.getItem(key) || fallback; } catch (e) { return fallback; }
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
    const v = safeStorageGet(THEME_KEY, 'system');
    return (v === 'light' || v === 'dark' || v === 'system') ? v : 'system';
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
      const modelLabel = mo.label || mo.model || mo.default_model || t('composer.model');
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
    parseSlashQuery,
    filterSlashSkills,
    applySlashSelection,
    classifyExtensionBadges,
    validateImportPayload,
  };
  root.CojamHarness = exported;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = exported;
  }

  if (typeof document === 'undefined') return;

  // ===== Live Browser Integration =====
  const toolsCache = new Map(); // key: rid + ':' + aiId -> tools payload
  let slashActiveIndex = 0;
  let slashState = null;
  let currentSideTab = safeStorageGet(SIDE_TAB_KEY, 'agents');
  let extensionsCache = null;
  let settingsTab = 'general';
  let extSubTab = 'skill';
  let extImportOpen = false;

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

  async function ensureRoomTools(aiId) {
    if (typeof RID === 'undefined' || !RID || !aiId) return null;
    const key = RID + ':' + aiId;
    if (toolsCache.has(key)) return toolsCache.get(key);
    try {
      const r = await fetch(api('tools') + '?ai=' + encodeURIComponent(aiId), { cache: 'no-store' });
      if (!r.ok) return null;
      const data = await r.json();
      toolsCache.set(key, data);
      return data;
    } catch (e) {
      return null;
    }
  }

  // ---- Right Inspector 3-Tab Controller ----
  function setSideTab(tab) {
    const valid = ['agents', 'board', 'output'].includes(tab) ? tab : 'agents';
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
        : (mo.label || mo.model || mo.default_model || '默认模型');
      const ctxDesc = typeof ctxTitle === 'function' ? ctxTitle(x) : '';
      const permBlocked = state.mode === 'work' && state.permissions && state.permissions[id] && state.permissions[id].work === false;
      return '<div class="side-agent-card" data-side-agent="' + esc(id) + '">'
        + '<div class="side-agent-head"><span class="side-agent-dot" style="--c:' + esc(color) + '"></span>'
        + '<span class="side-agent-name">' + esc(name) + '</span>'
        + '<span class="side-agent-badge' + (desktop ? ' desktop' : '') + '">' + esc(endpointLabel) + '</span></div>'
        + (permBlocked ? '<p class="side-agent-meta" style="color:var(--work)">当前会议已切到干活模式，但此成员未开启「允许干活」权限，仍将只读。</p>' : '')
        + '<p class="side-agent-meta">' + esc(modelDesc) + (ctxDesc ? '<br>' + esc(ctxDesc) : '') + '</p>'
        + '<div class="side-agent-actions">'
        + (permBlocked ? '<button type="button" data-open-perms="' + esc(id) + '">开启允许干活</button>' : '')
        + '<button type="button" data-open-ai="' + esc(id) + '">模型与执行端</button>'
        + (desktop
          ? '<button type="button" disabled title="桌面端由原软件管理扩展">' + esc(t('ext.hostManaged')) + '</button>'
          : '<button type="button" data-inline-tools="' + esc(id) + '">本会话扩展开关</button>')
        + '</div><div class="side-tools-inline" data-inline-tools-box="' + esc(id) + '" hidden></div></div>';
    }).join('');
  }

  async function toggleInlineTools(aiId, box) {
    if (!box) return;
    if (!box.hidden) { box.hidden = true; return; }
    box.hidden = false;
    box.innerHTML = '<p class="hint">读取中…</p>';
    const rid = RID;
    toolsCache.delete(rid + ':' + aiId);
    const data = await ensureRoomTools(aiId);
    if (RID !== rid) return;
    if (!data) {
      box.innerHTML = '<p class="hint">读取本会话扩展清单失败。</p>';
      return;
    }
    const x = (S && S.ais && S.ais[aiId]) || {};
    const row = (id, on, name, sub, locked) => '<li class="' + (locked ? 'lk' : '') + '"><input type="checkbox" data-id="' + esc(id) + '"' + (on ? ' checked' : '') + (locked ? ' disabled' : '') + '><span class="tn">' + esc(name) + (sub ? '<small>' + esc(sub) + '</small>' : '') + '</span></li>';
    const empty = '<li class="empty">（无）</li>';
    box.innerHTML =
      '<h5>MCP</h5><ul class="tl" data-k="mcp">' + ((data.mcp || []).map(m => row(m.name, m.on, m.name, m.source, false)).join('') || empty) + '</ul>'
      + '<h5>插件</h5><ul class="tl" data-k="plugins">' + ((data.plugins || []).map(p => row(p.id, p.on, p.label || p.id.replace(/@.*$/, ''), p.hooks ? '带钩子' : '', false)).join('') || empty) + '</ul>'
      + '<h5>技能</h5><ul class="tl" data-k="skills">' + ((data.skills || []).map(k => row(k.name, k.on, k.name, k.locked ? '跟随插件开关' : (k.desc || ''), k.locked)).join('') || empty) + '</ul>'
      + '<div class="btns"><button type="button" data-inline-save="' + esc(aiId) + '" class="pri"' + (x.busy ? ' disabled' : '') + '>保存</button></div>';
    const saveBtn = box.querySelector('[data-inline-save]');
    if (saveBtn) {
      saveBtn.onclick = async () => {
        const val = k => [...box.querySelectorAll('ul[data-k="' + k + '"] input[data-id]')];
        const mcp = val('mcp').filter(i => i.checked).map(i => i.dataset.id);
        const defOn = p => (p.hooks || p.synced) ? false : p.global;
        const plugins = {};
        val('plugins').forEach(i => {
          const p = (data.plugins || []).find(q => q.id === i.dataset.id);
          if (p && (i.checked !== defOn(p) || p.set)) plugins[p.id] = i.checked;
        });
        const skills_off = val('skills').filter(i => !i.disabled && !i.checked).map(i => i.dataset.id);
        saveBtn.disabled = true;
        const [ok, j] = await post(api('tools'), { ai: aiId, tools: { mcp, plugins, skills_off } });
        if (!ok) { alert((j && j.error) || '保存失败'); saveBtn.disabled = false; return; }
        toolsCache.delete(rid + ':' + aiId);
        await loadState();
        box.hidden = true;
      };
    }
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

    if (modeBtn) {
      modeBtn.disabled = !has;
      modeBtn.classList.toggle('work', work);
      modeBtn.textContent = work ? t('mode.work') : t('mode.discuss');
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
      const statusText = busy ? t('composer.busy') : (mo.apply_status === 'pending' ? t('composer.pending') : (mo.label || ''));
      const modelOptions = '<option value="">' + esc(mo.default_model ? '默认：' + modelOptionLabel(mo, mo.default_model) : '默认模型') + '</option>'
        + models.map(v => '<option value="' + esc(v) + '"' + (v === curModel ? ' selected' : '') + '>' + esc(modelOptionLabel(mo, v)) + '</option>').join('');
      const effortOptions = efforts.length
        ? '<select data-pop-effort="' + esc(id) + '"' + (busy ? ' disabled' : '') + '><option value="">默认强度</option>'
          + efforts.map(e => '<option value="' + esc(e) + '"' + (e === curEffort ? ' selected' : '') + '>' + esc((EFFORT_LABELS[e] || e)) + '</option>').join('') + '</select>'
        : '';
      return '<div class="pop-agent-row" data-pop-ai="' + esc(id) + '">'
        + '<div class="pop-agent-top"><b>' + esc(name) + '</b><span class="pop-agent-status">' + esc(statusText) + '</span></div>'
        + '<div class="pop-agent-controls"><select data-pop-model="' + esc(id) + '"' + (busy ? ' disabled' : '') + '>' + modelOptions + '</select>' + effortOptions + '</div>'
        + '<div class="pop-agent-foot"><button type="button" data-pop-open="' + esc(id) + '">' + esc(t('composer.openFull')) + '</button>'
        + '<button type="button" class="pri" data-pop-save="' + esc(id) + '"' + (busy ? ' disabled' : '') + '>' + esc(t('composer.save')) + '</button></div></div>';
    }).join('');

    pop.innerHTML = '<div class="composer-popover-head"><strong>' + esc(t('composer.model')) + '</strong><button type="button" id="popCloseBtn" aria-label="关闭">&times;</button></div>' + rows;
    pop.hidden = false;
    if (btn) btn.setAttribute('aria-expanded', 'true');
    const closeBtn = document.getElementById('popCloseBtn');
    if (closeBtn) closeBtn.onclick = closeComposerPopover;
  }

  // ---- Slash Skill Autocomplete ----
  function closeSlashMenu() {
    const menu = document.getElementById('slashMenu');
    if (menu) menu.hidden = true;
    slashState = null;
    slashActiveIndex = 0;
  }

  async function updateSlashMenu() {
    const taEl = document.getElementById('ta');
    const menu = document.getElementById('slashMenu');
    if (!taEl || !menu || !S || !S.meeting) return closeSlashMenu();
    const slash = parseSlashQuery(taEl.value, taEl.selectionStart);
    if (!slash) return closeSlashMenu();

    const target = resolveComposerTarget(taEl.value, S);
    const needIds = (target.mode === 'single' ? [target.aiId] : target.aiIds).filter(id => !isDesktopManaged(S, id));
    await Promise.all(needIds.map(id => ensureRoomTools(id)));

    const toolsByAi = {};
    needIds.forEach(id => { toolsByAi[id] = toolsCache.get(RID + ':' + id) || null; });
    const res = filterSlashSkills(taEl.value, taEl.selectionStart, S, toolsByAi, CONTACTS);
    if (!res) return closeSlashMenu();
    slashState = res;
    if (slashActiveIndex >= res.items.length) slashActiveIndex = 0;

    let html = '';
    if (res.notice) html += '<div class="slash-notice">' + esc(res.notice) + '</div>';
    if (!res.desktopOnly) {
      if (!res.items.length) {
        html += '<div class="slash-notice">' + esc(t('composer.noSkills')) + '</div>';
      } else {
        html += res.items.map((item, idx) =>
          '<button type="button" role="option" class="slash-item' + (idx === slashActiveIndex ? ' active' : '') + '" data-slash-idx="' + idx + '">'
          + '<span class="slash-item-main"><span class="slash-item-name">/' + esc(item.name) + '</span>'
          + (item.desc ? '<span class="slash-item-desc">' + esc(item.desc) + '</span>' : '') + '</span>'
          + '<span class="slash-item-agents">' + item.agentLabels.map(l => '<span class="slash-agent-tag">' + esc(l) + '</span>').join('') + '</span>'
          + '</button>'
        ).join('');
      }
    }
    menu.innerHTML = html;
    menu.hidden = false;
  }

  function pickSlashItem(idx) {
    if (!slashState || !slashState.items[idx]) return;
    const taEl = document.getElementById('ta');
    if (!taEl) return;
    const item = slashState.items[idx];
    const applied = applySlashSelection(taEl.value, slashState.slash, item, slashState.target);
    taEl.value = applied.text;
    closeSlashMenu();
    taEl.focus();
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
    const tabs = [
      ['general', t('settings.general')],
      ['agents', t('settings.agents')],
      ['extensions', t('settings.extensions')],
      ['about', t('settings.about')],
    ];
    return '<div id="appSettingsModal">'
      + '<nav class="settings-nav" aria-label="' + esc(t('settings.title')) + '">'
      + '<div class="settings-nav-title">' + esc(t('settings.title')) + '</div>'
      + tabs.map(([id, label]) => '<button type="button" data-settings-tab="' + id + '" aria-selected="' + String(id === activeTab) + '">' + esc(label) + '</button>').join('')
      + '</nav>'
      + '<div class="settings-main"><div class="settings-head"><h3>' + esc(heading) + '</h3>'
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
    const list = (typeof CONTACTS !== 'undefined' ? CONTACTS : []).filter(a => a && a.kind !== 'user');
    const rows = list.map(a => {
      const status = typeof contactStatusLabel === 'function' ? contactStatusLabel(a) : '';
      const channel = typeof contactChannelLabel === 'function' ? contactChannelLabel(a) : (a.driver || '');
      return '<div class="ext-item"><div class="ext-item-top"><b>' + esc(a.label || a.id) + '</b>'
        + '<span class="ext-badge">@' + esc(a.id) + '</span>'
        + '<span class="ext-badge">' + esc(channel) + '</span>'
        + (status ? '<span class="ext-badge">' + esc(status) + '</span>' : '')
        + '<button type="button" style="margin-left:auto" data-settings-agent="' + esc(a.id) + '">配置</button></div></div>';
    }).join('') || '<p class="hint">尚未配置任何 Agent。</p>';
    return '<div class="ext-toolbar"><p class="hint" style="margin:0">修改 Agent 的程序路径、默认模型、思考强度与桌面 MCP 接入。</p>'
      + '<div class="ext-actions"><button type="button" id="settingsOpenManager">管理与扫描</button><button type="button" class="pri" id="settingsAddAgent">＋ 接入</button></div></div>'
      + '<div class="ext-list">' + rows + '</div>';
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
      const canPick = Boolean(window.cojamDesktop && window.cojamDesktop.canChooseWorkdir());
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
    return '<div class="settings-group"><h4>合拍 Cojam</h4>'
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
        btn.onclick = () => { applyTheme(btn.dataset.themeChoice); openAppSettings('general'); };
      });
      body.querySelectorAll('[data-lang-choice]').forEach(btn => {
        btn.onclick = () => { applyLang(btn.dataset.langChoice); openAppSettings('general'); };
      });
    } else if (tab === 'agents') {
      const mgr = document.getElementById('settingsOpenManager');
      if (mgr) mgr.onclick = () => { if (typeof openAgentManager === 'function') openAgentManager(); };
      const add = document.getElementById('settingsAddAgent');
      if (add) add.onclick = () => { if (typeof startConnectionWizard === 'function') startConnectionWizard(); };
      body.querySelectorAll('[data-settings-agent]').forEach(btn => {
        btn.onclick = () => { if (typeof openAgentSettings === 'function') openAgentSettings(btn.dataset.settingsAgent); };
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
        if (pickBtn && window.cojamDesktop) {
          pickBtn.onclick = async () => {
            try {
              const p = await window.cojamDesktop.chooseWorkdir();
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
      agents: t('settings.agents'),
      extensions: t('settings.extensions'),
      about: t('settings.about'),
    };
    const bodyHtml = settingsTab === 'general' ? renderGeneralTab()
      : settingsTab === 'agents' ? renderAgentsTab()
      : settingsTab === 'about' ? renderAboutTab()
      : '<p class="hint">正在加载…</p>';
    showModal(renderSettingsShell(settingsTab, bodyHtml, headings[settingsTab] || t('settings.title')));
    document.body.classList.remove('nav-open');
    const closeBtn = document.getElementById('settingsCloseBtn');
    if (closeBtn) closeBtn.onclick = hideModal;
    mbox.querySelectorAll('[data-settings-tab]').forEach(btn => {
      btn.onclick = () => openAppSettings(btn.dataset.settingsTab);
    });
    bindSettingsTab(settingsTab);
  }

  // ---- Wire DOM Events ----
  function syncHarnessUi() {
    syncComposerBar();
    setSideTab(currentSideTab);
  }

  root.syncHarnessUi = syncHarnessUi;
  root.drawSideAgentsPane = drawSideAgentsPane;
  root.openAppSettings = openAppSettings;
  root.openInspectorTab = openInspectorTab;

  // Apply persisted preferences immediately
  applyTheme(getThemePref());
  applyLang(getLangPref());
  setSideTab(currentSideTab);

  const openSettingsBtn = document.getElementById('openSettingsBtn');
  if (openSettingsBtn) openSettingsBtn.onclick = () => openAppSettings('general');

  const sideToggleBtn = document.getElementById('sideToggleBtn');
  if (sideToggleBtn) {
    sideToggleBtn.onclick = () => {
      const side = document.getElementById('side');
      const isOpen = side && side.classList.contains('on');
      if (typeof setMeetingSide === 'function') setMeetingSide(!isOpen);
      sideToggleBtn.setAttribute('aria-expanded', String(!isOpen));
    };
  }

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
      const toolsBtn = e.target.closest('[data-inline-tools]');
      if (toolsBtn) {
        const aiId = toolsBtn.dataset.inlineTools;
        const box = sideAgentsPane.querySelector('[data-inline-tools-box="' + aiId + '"]');
        toggleInlineTools(aiId, box);
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
  if (composerExtBtn) composerExtBtn.onclick = () => { closeComposerPopover(); openInspectorTab('agents'); };

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
      effSel.innerHTML = '<option value="">默认强度</option>' + choices.map(c => '<option value="' + esc(c) + '">' + esc(EFFORT_LABELS[c] || c) + '</option>').join('');
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
      if (item) pickSlashItem(Number(item.dataset.slashIdx));
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
        slashActiveIndex = (slashActiveIndex + 1) % slashState.items.length;
        updateSlashMenu();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        slashActiveIndex = (slashActiveIndex - 1 + slashState.items.length) % slashState.items.length;
        updateSlashMenu();
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        e.stopImmediatePropagation();
        pickSlashItem(slashActiveIndex);
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
})(typeof window !== 'undefined' ? window : globalThis);
