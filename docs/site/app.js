let catalog;
let current = null;
let idx;
let docs = [];

const menuEl = document.getElementById('menu');
const contentEl = document.getElementById('content');
const searchEl = document.getElementById('search');
const langEl = document.getElementById('language');

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
  for (const area of areas) {
    const title = document.createElement('div');
    title.className = 'area-title';
    title.textContent = area.area;
    menuEl.appendChild(title);

    for (const wf of area.workflows) {
      const id = `${area.area}:${wf.trigger}`;
      if (filteredIds && !filteredIds.has(id)) continue;
      const btn = document.createElement('button');
      btn.className = 'wf-btn';
      btn.textContent = `${wf.trigger} — ${wf.name}`;
      btn.onclick = () => renderWorkflow(id);
      menuEl.appendChild(btn);
    }
  }
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
}

function escapeFence(s) {
  return (s || '').replace(/```/g, '\\\`\\\`\\\`');
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
