/* Regenerate the original SVG preview from the same synthetic graph fixture. */
const fs = require('node:fs');
const path = require('node:path');
const { scenarios, relationMeta, selectContext } = require('../listings/huggingface-space/atlas-core.js');
const s = scenarios.enterprise;
const sel = selectContext(s, 120, 4);
const esc = value => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[char]);
const positions = Object.fromEntries(s.nodes.map(n => [n.id, n]));
const placements = {
  'catalog:SUPPLIES:candidate': [.23, 15],
  'event:TRIGGERS:task': [.48, 16],
  'preference:INFORMS:task': [.42, -15],
  'history:INFORMS:task': [.74, 18],
  'foreign:BLOCKED:task': [.33, 14],
  'rule:CONSTRAINS:gate': [.55, -15],
};
const zones = [[22, 40, 194, 570, '01 / INPUTS'], [238, 40, 230, 570, '02 / MEMORY'], [486, 40, 170, 570, '03 / TASK'], [675, 40, 250, 570, '04 / GATES + CANDIDATES'], [945, 40, 180, 570, '05 / OUTCOMES']];
const lines = s.edges.map(e => {
  const a = positions[e.from], b = positions[e.to], color = relationMeta[e.type].color;
  const x1 = a.x < b.x ? a.x + 63 : a.x - 63, x2 = a.x < b.x ? b.x - 63 : b.x + 63;
  const sign = x2 > x1 ? 1 : -1, bend = Math.min(120, Math.max(45, Math.abs(x2 - x1) * .43));
  const [p0, p1, p2, p3] = e.id === 'event:TRIGGERS:task'
    ? [[x1, a.y], [x1 + 135, a.y + 62], [x2 - 70, b.y + 180], [x2, b.y]]
    : [[x1, a.y], [x1 + bend * sign, a.y], [x2 - bend * sign, b.y], [x2, b.y]];
  const d = `M ${p0[0]} ${p0[1]} C ${p1[0]} ${p1[1]}, ${p2[0]} ${p2[1]}, ${p3[0]} ${p3[1]}`;
  const label = relationMeta[e.type].label;
  const [t, dy] = placements[e.id] || [.5, -10], u = 1 - t;
  const lx = u ** 3 * p0[0] + 3 * u ** 2 * t * p1[0] + 3 * u * t ** 2 * p2[0] + t ** 3 * p3[0];
  const ly = u ** 3 * p0[1] + 3 * u ** 2 * t * p1[1] + 3 * u * t ** 2 * p2[1] + t ** 3 * p3[1] + dy;
  return `<path d="${d}" fill="none" stroke="${color}" stroke-width="2.3" stroke-opacity=".78" ${e.type === 'BLOCKED' ? 'stroke-dasharray="6 5"' : ''} marker-end="url(#arrow-${e.type})"/><text x="${lx}" y="${ly}" class="edge-label">${esc(label)}</text>`;
}).join('\n');
const nodes = s.nodes.map(n => {
  const status = n.scope === 'other-tenant' ? 'DENIED' : sel.selected.includes(n.id) ? 'ADMITTED' : n.kind.toUpperCase();
  const border = status === 'DENIED' ? '#f097ae' : status === 'ADMITTED' ? '#a5f7ce' : '#77a8c1';
  const fill = status === 'DENIED' ? '#43283a' : status === 'ADMITTED' ? '#1e4d49' : '#152b3c';
  const meta = status === 'DENIED' ? 'OUT OF SCOPE' : n.contextEligible ? `${n.tokens} tokens · trust ${n.trust}` : n.scope.toUpperCase();
  return `<g transform="translate(${n.x} ${n.y})"><rect x="-63" y="-31" width="126" height="62" rx="9" fill="${fill}" stroke="${border}" stroke-width="1.8"/><path d="M -62 -20 V 20" stroke="${border}" stroke-width="3"/><text x="-49" y="-12" class="node-kind">${esc(status)}</text><text x="-49" y="6" class="node-label">${esc(n.label)}</text><text x="-49" y="22" class="node-meta">${esc(meta)}</text></g>`;
}).join('\n');
const markers = Object.entries(relationMeta).map(([type, meta]) => `<marker id="arrow-${type}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 1 L 9 5 L 0 9 z" fill="${meta.color}"/></marker>`).join('');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1380" height="790" viewBox="0 0 1150 660" role="img" aria-labelledby="title desc">
<title id="title">Swarm Context Commander original enterprise evidence graph</title><desc id="desc">Twelve nodes across source, memory, task, policy and outcome lanes, connected by named directed relations; one cross-tenant source is denied.</desc>
<defs><radialGradient id="bg"><stop stop-color="#16374c"/><stop offset="1" stop-color="#081725"/></radialGradient>${markers}</defs><style>.title{fill:#e7f7ff;font:700 25px system-ui,sans-serif;letter-spacing:-1px}.subtitle{fill:#9cc3d3;font:12px system-ui,sans-serif}.zone-title{fill:#729bad;font:800 10px monospace;letter-spacing:1.6px}.edge-label{fill:#c8e0e9;font:700 9px monospace;text-anchor:middle;paint-order:stroke;stroke:#102436;stroke-width:5px}.node-kind{fill:#a8d2de;font:800 8px monospace;letter-spacing:.6px}.node-label{fill:#f1fbff;font:700 12px system-ui,sans-serif}.node-meta{fill:#b9d1df;font:9px monospace}</style>
<rect width="1150" height="660" fill="url(#bg)"/><text x="24" y="25" class="title">Context Atlas / Incident operations</text><text x="816" y="24" class="subtitle">ORIGINAL GRAPH · SYNTHETIC DATA</text>
${zones.map(([x,y,w,h,label]) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="#ffffff05" stroke="#476d7c55"/><text x="${x+11}" y="${y+23}" class="zone-title">${label}</text>`).join('\n')}
${lines}
${nodes}
<text x="23" y="642" class="subtitle">12 source-linked nodes  ·  12 typed relations  ·  ${sel.selected.length} admitted  ·  1 tenant-scope denial</text><text x="939" y="642" class="subtitle">swarmcontext / v1</text>
</svg>\n`;
const target = path.join(__dirname, '..', 'assets', 'context-atlas-preview.svg');
if (process.argv.includes('--check')) {
  if (!fs.existsSync(target) || fs.readFileSync(target, 'utf8') !== svg) {
    console.error('Preview is stale. Run node scripts/render-atlas-preview.js'); process.exit(1);
  }
} else {
  fs.writeFileSync(target, svg);
  console.log(target);
}
