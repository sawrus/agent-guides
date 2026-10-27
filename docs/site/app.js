// Static docs site: renders rules, workflows, and skills from catalog.json (scripts/build_docs_catalog.py).
// The page functions are pure (catalog data in, markdown out), so tests can call them without a browser.

const KINDS = [
  { kind: 'rule', label: 'Rules', key: 'rules' },
  { kind: 'workflow', label: 'Workflows', key: 'workflows' },
  { kind: 'skill', label: 'Skills', key: 'skills' },
];

// --- pure helpers (no DOM) -----------------------------------------------------------------------------------

function docId(kind, area, name) {
  return `${kind}/${area}/${name}`;
}

function code(value) {
  const s = String(value ?? '');
  const ticks = (s.match(/`+/g) || []).reduce((n, run) => Math.max(n, run.length), 0);
  const fence = '`'.repeat(ticks + 1);
  const pad = s.startsWith('`') || s.endsWith('`') ? ' ' : '';
  return `${fence}${pad}${s}${pad}${fence}`;
}

function escapeFence(s) {
  return (s || '').replace(/```/g, '\\`\\`\\`');
}

function section(title, body) {
  return body && body.trim() ? `## ${title}\n\n${body.trim()}\n` : '';
}

function bullets(items, fmt = (x) => x) {
  return (items || []).filter((x) => x !== '' && x != null).map((x) => `- ${fmt(x)}`).join('\n');
}

function refLinks(refs, pathToId) {
  return bullets(refs, (r) => {
    const id = r.path && pathToId ? pathToId.get(r.path) : null;
    return id ? `[${r.name}](#${id})` : r.path ? `${r.name} (${code(r.path)})` : `${r.name} (missing)`;
  });
}

function sourceLine(path) {
  return path ? `---\n\n<div class="meta">Source: <code>${path}</code></div>\n` : '';
}

function buildDocs(cat) {
  const out = [];
  for (const area of cat.areas || []) {
    for (const { kind, key } of KINDS) {
      for (const item of area[key] || []) {
        const path = item.path || item.workflow_path;
        out.push({
          id: docId(kind, area.area, item.name),
          kind,
          area: area.area,
          name: item.name,
          trigger: item.trigger || '',
          description: item.description || '',
          examples: (item.examples || []).join('\n'),
          text: kind === 'workflow'
            ? (item.steps || []).map((s) => `${s.title} ${s.do} ${s.done_when}`).join('\n') + (item.body || '')
            : item.body || '',
          path,
          data: item,
        });
      }
    }
  }
  return out;
}

function workflowMarkdown(wf, area, pathToId) {
  const header = `# ${wf.name}\n\n${wf.trigger ? `${code(wf.trigger)} · ` : ''}<span class="chip">workflow</span> <span class="chip">${area}</span>\n`;
  const when = [
    wf.use_when ? `**Use when:** ${wf.use_when}` : '',
    wf.avoid_when ? `**Avoid when:** ${wf.avoid_when}` : '',
  ].filter(Boolean).join('\n\n');
  const io = [
    (wf.inputs || []).length ? `**Inputs:** ${wf.inputs.map(code).join(', ')}` : '',
    (wf.outputs || []).length ? `**Outputs:** ${wf.outputs.map(code).join(', ')}` : '',
  ].filter(Boolean).join('\n\n');
  const steps = (wf.steps || []).map((s, i) => [
    `### ${i + 1}. ${s.title}`,
    s.do ? `**Do:** ${s.do}` : '',
    s.done_when ? `**Done when:** ${s.done_when}` : '',
  ].filter(Boolean).join('\n\n')).join('\n\n');
  const examples = (wf.examples || []).map((ex) => `\`\`\`\n${escapeFence(ex)}\n\`\`\``).join('\n\n');

  return [
    header,
    wf.description,
    when,
    section('Inputs → outputs', io),
    section('Steps', steps || wf.body || ''),
    section('Checks', bullets(wf.checks, code)),
    section('Artifacts', bullets(wf.artifacts, code)),
    section('Rules', refLinks(wf.rule_refs, pathToId)),
    section('Skills', refLinks(wf.skill_refs, pathToId)),
    section('Example requests', examples),
    sourceLine(wf.workflow_path),
  ].filter((x) => x && x.trim()).join('\n\n');
}

function ruleMarkdown(rule, area) {
  const scope = (rule.paths || []).length
    ? (rule.paths || []).map(code).join(' ')
    : rule.trigger === 'manual'
      ? 'manual — load it on request; no file pattern loads it'
      : rule.trigger || '';
  return [
    `# ${rule.name}\n\n<span class="chip">rule</span> <span class="chip">${area}</span>\n`,
    rule.description,
    scope ? `**Applies to:** ${scope}` : '',
    rule.body ? `---\n\n${rule.body}` : '',
    sourceLine(rule.path),
  ].filter((x) => x && x.trim()).join('\n\n');
}

function skillMarkdown(skill, area) {
  return [
    `# ${skill.name}\n\n<span class="chip">skill</span> <span class="chip">${area}</span>\n`,
    skill.description,
    skill.body ? `---\n\n${skill.body}` : '',
    sourceLine(skill.path),
  ].filter((x) => x && x.trim()).join('\n\n');
}

function homeMarkdown(cat) {
  const s = cat.stats || {};
  const rows = (cat.areas || []).map((a) => {
    const first = KINDS.map(({ kind, key }) => (a[key] || [])[0] && docId(kind, a.area, a[key][0].name)).find(Boolean);
    const counts = KINDS.map(({ kind, key }) => {
      const n = (a[key] || []).length;
      return `${n} ${kind}${n === 1 ? '' : 's'}`;
    }).join(', ');
    const title = first ? `[${a.area}](#${first})` : a.area;
    return `- **${title}** — ${a.summary ? `${a.summary} ` : ''}<span class="meta">(${counts})</span>`;
  });
  return [
    '# agentic pack',
    `${s.rules || 0} rules, ${s.workflows || 0} workflows, and ${s.skills || 0} skills. Rules load by file ` +
      'pattern (`paths:`) or on request; workflows are task procedures with steps; skills are tools that ' +
      'workflows and rules call.',
    section('Specs', rows.join('\n')),
  ].filter(Boolean).join('\n\n');
}

function renderDocMarkdown(doc, pathToId) {
  if (!doc) return '';
  if (doc.kind === 'workflow') return workflowMarkdown(doc.data, doc.area, pathToId);
  if (doc.kind === 'rule') return ruleMarkdown(doc.data, doc.area);
  return skillMarkdown(doc.data, doc.area);
}

function groupAreas(areas, filteredIds) {
  const groups = new Map();
  for (const area of areas) {
    const [groupName, ...rest] = area.area.split('/');
    const kinds = KINDS.map(({ kind, label, key }) => ({
      kind,
      label,
      items: (area[key] || [])
        .map((item) => ({ id: docId(kind, area.area, item.name), name: item.name }))
        .filter((item) => !filteredIds || filteredIds.has(item.id)),
    })).filter((k) => k.items.length);
    if (!kinds.length) continue;
    if (!groups.has(groupName)) groups.set(groupName, { label: groupName, sections: [] });
    groups.get(groupName).sections.push({ label: rest.join('/') || groupName, area: area.area, kinds });
  }
  return [...groups.values()];
}

// --- browser part --------------------------------------------------------------------------------------------

if (typeof document !== 'undefined') {
  let catalog;
  let current = null;
  let idx;
  let docs = [];
  let pathToId = new Map();

  const menuEl = document.getElementById('menu');
  const contentEl = document.getElementById('content');
  const searchEl = document.getElementById('search');
  const themeToggleEl = document.getElementById('theme-toggle');

  const sectionHas = (section, id) => section.kinds.some((k) => k.items.some((item) => item.id === id));

  function renderMenu(filteredIds = null) {
    menuEl.innerHTML = '';
    for (const group of groupAreas(catalog.areas, filteredIds)) {
      const groupNode = document.createElement('details');
      groupNode.className = 'menu-group';
      groupNode.open = Boolean(filteredIds) || group.sections.some((s) => sectionHas(s, current?.id));
      const groupSummary = document.createElement('summary');
      groupSummary.className = 'menu-group__summary';
      groupSummary.textContent = group.label;
      groupNode.appendChild(groupSummary);

      const sectionsNode = document.createElement('div');
      sectionsNode.className = 'menu-group__sections';
      for (const sec of group.sections) {
        const sectionNode = document.createElement('details');
        sectionNode.className = 'menu-section';
        sectionNode.open = Boolean(filteredIds) || sectionHas(sec, current?.id);
        const sectionSummary = document.createElement('summary');
        sectionSummary.className = 'menu-section__summary';
        sectionSummary.textContent = sec.label;
        sectionNode.appendChild(sectionSummary);

        const list = document.createElement('div');
        list.className = 'menu-section__workflows';
        for (const kind of sec.kinds) {
          const label = document.createElement('div');
          label.className = 'menu-kind';
          label.textContent = kind.label;
          list.appendChild(label);
          for (const item of kind.items) {
            const btn = document.createElement('button');
            btn.className = 'wf-btn';
            btn.dataset.docId = item.id;
            btn.textContent = item.name;
            btn.onclick = () => { window.location.hash = item.id; };
            list.appendChild(btn);
          }
        }
        sectionNode.appendChild(list);
        sectionsNode.appendChild(sectionNode);
      }
      groupNode.appendChild(sectionsNode);
      menuEl.appendChild(groupNode);
    }
    updateActiveMenuItem();
  }

  function updateActiveMenuItem() {
    for (const btn of menuEl.querySelectorAll('.wf-btn')) {
      const isActive = btn.dataset.docId === current?.id;
      btn.classList.toggle('wf-btn--active', isActive);
      if (isActive) {
        btn.setAttribute('aria-current', 'page');
        btn.closest('.menu-section')?.setAttribute('open', '');
        btn.closest('.menu-group')?.setAttribute('open', '');
      } else {
        btn.removeAttribute('aria-current');
      }
    }
  }

  function renderRoute() {
    const id = decodeURIComponent(window.location.hash.replace(/^#/, ''));
    current = docs.find((d) => d.id === id) || null;
    contentEl.innerHTML = marked.parse(current ? renderDocMarkdown(current, pathToId) : homeMarkdown(catalog));
    contentEl.scrollTop = 0;
    updateActiveMenuItem();
  }

  function getStoredTheme() {
    try {
      return window.localStorage.getItem('docs-site-theme') === 'dark' ? 'dark' : 'light';
    } catch {
      return 'light';
    }
  }

  function storeTheme(theme) {
    try {
      window.localStorage.setItem('docs-site-theme', theme);
    } catch {
      // localStorage can be unavailable in private or restricted browser modes.
    }
  }

  let activeTheme = 'light';
  function applyTheme(theme) {
    activeTheme = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.dataset.theme = activeTheme;
    if (!themeToggleEl) return;
    const isDark = activeTheme === 'dark';
    themeToggleEl.setAttribute('aria-pressed', String(isDark));
    themeToggleEl.textContent = isDark ? 'Light' : 'Dark';
  }

  applyTheme(getStoredTheme());

  (async function init() {
    const res = await fetch('./catalog.json');
    catalog = await res.json();
    docs = buildDocs(catalog);
    pathToId = new Map(docs.map((d) => [d.path, d.id]));
    idx = lunr(function () {
      this.ref('id');
      ['kind', 'area', 'trigger', 'name', 'description', 'examples', 'text'].forEach((f) => this.field(f));
      docs.forEach((d) => this.add(d));
    });
    renderMenu();
    renderRoute();
  })();

  window.addEventListener('hashchange', renderRoute);

  searchEl.addEventListener('input', () => {
    const q = searchEl.value.trim();
    if (!q) {
      renderMenu();
      return;
    }
    let results = [];
    try {
      results = idx.search(q.split(/\s+/).flatMap((t) => [t, `${t}*`]).join(' '));
    } catch {
      results = idx.search(q.replace(/[:~^*+-]/g, ' '));
    }
    renderMenu(new Set(results.map((r) => r.ref)));
  });

  themeToggleEl.addEventListener('click', () => {
    const nextTheme = activeTheme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
    storeTheme(nextTheme);
  });
}

if (typeof module !== 'undefined') {
  module.exports = { buildDocs, workflowMarkdown, ruleMarkdown, skillMarkdown, homeMarkdown, renderDocMarkdown, groupAreas };
}
