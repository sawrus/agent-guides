let catalog;
let current = null;
let idx;
let docs = [];
let activeTheme = 'light';

const menuEl = document.getElementById('menu');
const contentEl = document.getElementById('content');
const searchEl = document.getElementById('search');
const langEl = document.getElementById('language');
const themeToggleEl = document.getElementById('theme-toggle');

applyTheme(getStoredTheme());
configureMermaid();

init();

async function init() {
  const res = await fetch('./catalog.json');
  catalog = await res.json();
  buildIndex();
  renderMenu(catalog.areas);
  if (docs[0]) renderWorkflow(docs[0].id);
}

function buildIndex() {
  docs = [];
  for (const area of catalog.areas) {
    for (const wf of area.workflows) {
      docs.push({
        id: `${area.area}:${wf.trigger}`,
        area: area.area,
        trigger: wf.trigger,
        name: wf.name,
        description: wf.description,
        examples: (wf.examples?.both || []).map((e) => `${e.en}\n${e.ru}`).join('\n'),
        data: wf,
      });
    }
  }

  idx = lunr(function () {
    this.ref('id');
    this.field('area');
    this.field('trigger');
    this.field('name');
    this.field('description');
    this.field('examples');
    docs.forEach((d) => this.add(d));
  });
}

function renderMenu(areas, filteredIds = null) {
  menuEl.innerHTML = '';
  const groupedAreas = groupAreasBySection(areas, filteredIds);

  for (const group of groupedAreas) {
    const groupNode = document.createElement('details');
    groupNode.className = 'menu-group';
    groupNode.open = isGroupOpen(group, filteredIds);

    const groupSummary = document.createElement('summary');
    groupSummary.className = 'menu-group__summary';
    groupSummary.textContent = group.label;
    groupNode.appendChild(groupSummary);

    const sectionsNode = document.createElement('div');
    sectionsNode.className = 'menu-group__sections';

    for (const section of group.sections) {
      const sectionNode = document.createElement('details');
      sectionNode.className = 'menu-section';
      sectionNode.open = isSectionOpen(section, filteredIds);

      const sectionSummary = document.createElement('summary');
      sectionSummary.className = 'menu-section__summary';
      sectionSummary.textContent = section.label;
      sectionNode.appendChild(sectionSummary);

      const workflowList = document.createElement('div');
      workflowList.className = 'menu-section__workflows';

      for (const workflow of section.workflows) {
        const btn = document.createElement('button');
        btn.className = 'wf-btn';
        btn.dataset.workflowId = workflow.id;
        btn.textContent = `${workflow.trigger} — ${workflow.name}`;
        btn.onclick = () => renderWorkflow(workflow.id);
        workflowList.appendChild(btn);
      }

      sectionNode.appendChild(workflowList);
      sectionsNode.appendChild(sectionNode);
    }

    groupNode.appendChild(sectionsNode);
    menuEl.appendChild(groupNode);
  }

  updateActiveMenuItem();
}

function groupAreasBySection(areas, filteredIds) {
  const groups = new Map();

  for (const area of areas) {
    const [groupName, ...sectionParts] = area.area.split('/');
    const sectionName = sectionParts.join('/') || groupName;
    const workflows = area.workflows
      .map((wf) => ({
        id: `${area.area}:${wf.trigger}`,
        trigger: wf.trigger,
        name: wf.name,
      }))
      .filter((wf) => !filteredIds || filteredIds.has(wf.id));

    if (!workflows.length) continue;

    if (!groups.has(groupName)) {
      groups.set(groupName, { label: groupName, sections: [] });
    }

    groups.get(groupName).sections.push({
      label: sectionName,
      area: area.area,
      workflows,
    });
  }

  return [...groups.values()];
}

function isGroupOpen(group, filteredIds) {
  if (filteredIds) return true;
  return group.sections.some((section) => section.workflows.some((workflow) => workflow.id === current?.id));
}

function isSectionOpen(section, filteredIds) {
  if (filteredIds) return true;
  return section.workflows.some((workflow) => workflow.id === current?.id);
}

function updateActiveMenuItem() {
  for (const btn of menuEl.querySelectorAll('.wf-btn')) {
    const isActive = btn.dataset.workflowId === current?.id;
    btn.classList.toggle('wf-btn--active', isActive);
    if (isActive) {
      btn.setAttribute('aria-current', 'page');
      openActiveMenuParents(btn);
    } else {
      btn.removeAttribute('aria-current');
    }
  }
}

function openActiveMenuParents(btn) {
  btn.closest('.menu-section')?.setAttribute('open', '');
  btn.closest('.menu-group')?.setAttribute('open', '');
}

function renderWorkflow(id) {
  current = docs.find((d) => d.id === id);
  if (!current) return;
  const wf = current.data;
  const lang = langEl.value;

  const examples = (wf.examples?.both || []).map((ex) => {
    const blocks = [];
    if (lang === 'both' || lang === 'en') blocks.push(`**EN**\n\n\
\`\`\`\n${escapeFence(ex.en)}\n\`\`\``);
    if (lang === 'both' || lang === 'ru') blocks.push(`**RU**\n\n\
\`\`\`\n${escapeFence(ex.ru)}\n\`\`\``);
    return `### Example ${ex.number} — ${ex.title}\n\n${blocks.join('\n\n')}`;
  }).join('\n\n');

  const md = `
# ${wf.name}  
\`${wf.trigger}\`

${wf.description || ''}

**Use when:** ${wf.use_when || '—'}

## Roles
${(wf.roles || []).map((r) => `<span class="chip">${r}</span>`).join(' ')}

${wf.workflow_diagram ? `## Agent Interaction Diagram\n\n\`\`\`mermaid\n${escapeFence(wf.workflow_diagram)}\n\`\`\`` : ''}

## Quality gates
${(wf.quality_gates || []).map((q) => `- ${q}`).join('\n') || '- —'}

## Skills
${(wf.skill_refs || []).map((s) => `- ${s.name} (${s.path || "missing"})`).join('\n') || '- —'}

## Examples (${lang.toUpperCase()})
${examples || '_No examples_'}

---

<div class="meta">Workflow source: <code>${wf.workflow_path}</code><br/>Prompt source: <code>${wf.prompt_path || '—'}</code></div>
`;

  contentEl.innerHTML = marked.parse(md);
  updateActiveMenuItem();
  renderMermaidBlocks();
}

function getStoredTheme() {
  try {
    const theme = window.localStorage.getItem('docs-site-theme');
    return theme === 'dark' ? 'dark' : 'light';
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

function applyTheme(theme) {
  activeTheme = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.dataset.theme = activeTheme;
  if (!themeToggleEl) return;
  const isDark = activeTheme === 'dark';
  themeToggleEl.setAttribute('aria-pressed', String(isDark));
  themeToggleEl.textContent = isDark ? 'Light' : 'Dark';
}

function configureMermaid() {
  if (!window.mermaid) return;
  window.mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: activeTheme === 'dark' ? 'dark' : 'default',
  });
}

function escapeFence(s) {
  return (s || '').replace(/```/g, '\\\`\\\`\\\`');
}

async function renderMermaidBlocks() {
  const blocks = [...contentEl.querySelectorAll('code.language-mermaid')];
  if (!blocks.length) return;

  const nodes = blocks.map((block) => {
    const diagram = document.createElement('div');
    diagram.className = 'mermaid';
    diagram.textContent = block.textContent;
    block.parentElement.replaceWith(diagram);
    return diagram;
  });

  if (window.mermaid) {
    configureMermaid();
    await window.mermaid.run({ nodes });
  }
}

searchEl.addEventListener('input', () => {
  const q = searchEl.value.trim();
  if (!q) {
    renderMenu(catalog.areas);
    return;
  }
  const results = idx.search(`${q}*`);
  renderMenu(catalog.areas, new Set(results.map((r) => r.ref)));
});

langEl.addEventListener('change', () => {
  if (current) renderWorkflow(current.id);
});

themeToggleEl.addEventListener('click', () => {
  const nextTheme = activeTheme === 'dark' ? 'light' : 'dark';
  applyTheme(nextTheme);
  storeTheme(nextTheme);
  if (current) renderWorkflow(current.id);
});
