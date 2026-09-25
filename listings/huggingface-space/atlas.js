/* Original, dependency-free typed evidence graph. Browser-only synthetic UI. */
(() => {
  'use strict';
  const { scenarios, relationMeta, selectContext, pathTo } = window.SwarmAtlas;
  const ns = 'http://www.w3.org/2000/svg';
  const $ = id => document.getElementById(id);
  const svg = $('atlas-graph');
  const relationGroups = {
    ALL: null,
    EVIDENCE: new Set(['DERIVED_FROM', 'SUPPLIES', 'INFORMS', 'SUPPORTS', 'TRIGGERS']),
    POLICY: new Set(['CONSTRAINS', 'EVALUATES', 'AUTHORIZES']),
    OUTCOME: new Set(['MEASURED_BY']),
    DENIED: new Set(['BLOCKED']),
  };
  const state = {
    tier: 'consumer', relation: 'ALL', focus: { kind: 'node', id: 'task' },
    positions: {}, transform: { x: 0, y: 0, k: 1 }, feedback: {},
  };
  for (const tier of Object.keys(scenarios)) state.feedback[tier] = { accepted: 0, rejected: 0 };
  const svgEl = (tag, attrs = {}) => {
    const element = document.createElementNS(ns, tag);
    for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, String(value));
    return element;
  };
  const htmlEl = (tag, className, content) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (content !== undefined) element.textContent = String(content);
    return element;
  };
  const current = () => scenarios[state.tier];
  const pos = node => state.positions[node.id] || { x: node.x, y: node.y };
  const fmt = value => value.toFixed(2);
  const policy = () => {
    const f = state.feedback[state.tier];
    return f.accepted >= 2 && f.accepted > f.rejected ? 'RICH' : 'COMPACT';
  };
  const selection = () => selectContext(current(), Number($('budget').value), policy() === 'RICH' ? 4 : 2);
  const matching = () => $('node-search').value.trim().toLowerCase();
  const filterAllows = edge => !relationGroups[state.relation] || relationGroups[state.relation].has(edge.type);
  function focusPath() {
    if (state.focus.kind !== 'node') return [];
    return pathTo(current(), state.focus.id);
  }
  function applyTransform() {
    const t = state.transform;
    $('graph-viewport').setAttribute('transform', `translate(${t.x} ${t.y}) scale(${t.k})`);
    $('zoom-label').textContent = `${Math.round(t.k * 100)}%`;
  }
  function screenToGraph(clientX, clientY) {
    const pt = svg.createSVGPoint(); pt.x = clientX; pt.y = clientY;
    const viewport = $('graph-viewport');
    return pt.matrixTransform(viewport.getScreenCTM().inverse());
  }
  function drawZones(layer) {
    const groups = [
      [26, 42, 190, 570, '01 / INPUTS'], [243, 42, 225, 570, '02 / MEMORY'],
      [487, 42, 170, 570, '03 / TASK'], [675, 42, 250, 570, '04 / GATES + CANDIDATES'],
      [943, 42, 182, 570, '05 / OUTCOMES'],
    ];
    for (const [x, y, width, height, title] of groups) {
      layer.append(svgEl('rect', { x, y, width, height, rx: 10, class: 'zone' }));
      const label = svgEl('text', { x: x + 12, y: y + 23, class: 'zone-title' });
      label.textContent = title; layer.append(label);
    }
    layer.append(svgEl('circle', { cx: 575, cy: 315, r: 220, class: 'sweep' }));
  }
  function edgeGeometry(edge, a, b) {
    const startX = a.x < b.x ? a.x + 63 : a.x - 63;
    const endX = a.x < b.x ? b.x - 63 : b.x + 63;
    const bend = Math.min(120, Math.max(45, Math.abs(endX - startX) * .43));
    const sign = endX > startX ? 1 : -1;
    if (edge.id === 'event:TRIGGERS:task') return [[startX, a.y], [startX + 135, a.y + 62], [endX - 70, b.y + 180], [endX, b.y]];
    return [[startX, a.y], [startX + bend * sign, a.y], [endX - bend * sign, b.y], [endX, b.y]];
  }
  function edgePath(edge, a, b) {
    const [p0, p1, p2, p3] = edgeGeometry(edge, a, b);
    return `M ${p0[0]} ${p0[1]} C ${p1[0]} ${p1[1]}, ${p2[0]} ${p2[1]}, ${p3[0]} ${p3[1]}`;
  }
  function edgeLabelPosition(edge, a, b) {
    const placements = {
      'catalog:SUPPLIES:candidate': [.23, 15],
      'event:TRIGGERS:task': [.48, 16],
      'preference:INFORMS:task': [.42, -15],
      'history:INFORMS:task': [.74, 18],
      'foreign:BLOCKED:task': [.33, 14],
      'rule:CONSTRAINS:gate': [.55, -15],
    };
    const [t, dy] = placements[edge.id] || [.5, -10];
    const [p0, p1, p2, p3] = edgeGeometry(edge, a, b), u = 1 - t;
    return [u ** 3 * p0[0] + 3 * u ** 2 * t * p1[0] + 3 * u * t ** 2 * p2[0] + t ** 3 * p3[0],
      u ** 3 * p0[1] + 3 * u ** 2 * t * p1[1] + 3 * u * t ** 2 * p2[1] + t ** 3 * p3[1] + dy];
  }
  function drawEdge(layer, labelLayer, edge, nodes, sel, path, query) {
    if (!filterAllows(edge)) return;
    const a = pos(nodes.get(edge.from)), b = pos(nodes.get(edge.to));
    const color = relationMeta[edge.type].color;
    const match = !query || `${edge.type} ${edge.evidence} ${nodes.get(edge.from).label} ${nodes.get(edge.to).label}`.toLowerCase().includes(query);
    const onPath = path.includes(edge.from) && path.includes(edge.to) && Math.abs(path.indexOf(edge.from) - path.indexOf(edge.to)) === 1;
    const emphasized = state.focus.kind === 'edge' && state.focus.id === edge.id || onPath;
    const group = svgEl('g', { class: `edge-group${match ? '' : ' dimmed'}` });
    const curve = svgEl('path', {
      d: edgePath(edge, a, b), class: `edge${edge.type === 'BLOCKED' ? ' blocked' : ''}${emphasized ? ' emphasis' : ''}${match ? '' : ' dimmed'}`,
      stroke: color, 'marker-end': `url(#arrow-${edge.type})`, 'data-id': edge.id,
    });
    curve.style.color = color;
    const hit = svgEl('path', { d: edgePath(edge, a, b), stroke: 'transparent', 'stroke-width': 18, fill: 'none', style: 'cursor:pointer', tabindex: 0, role: 'button', 'aria-label': `${edge.type.replaceAll('_', ' ')}: ${nodes.get(edge.from).label} to ${nodes.get(edge.to).label}` });
    const inspect = event => { event.stopPropagation(); state.focus = { kind: 'edge', id: edge.id }; draw(); };
    hit.addEventListener('click', inspect);
    hit.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); inspect(event); } });
    group.append(curve, hit); layer.append(group);
    const [labelX, labelY] = edgeLabelPosition(edge, a, b);
    const label = svgEl('text', { x: labelX, y: labelY, class: `edge-label${match ? '' : ' dimmed'}` });
    label.textContent = relationMeta[edge.type].label;
    labelLayer.append(label);
  }
  function nodeStatus(node, sel) {
    if (node.scope === 'other-tenant') return 'DENIED';
    if (node.contextEligible) return sel.selected.includes(node.id) ? 'ADMITTED' : 'CANDIDATE';
    return node.kind.toUpperCase();
  }
  function drawNode(layer, node, sel, path, query) {
    const p = pos(node), status = nodeStatus(node, sel);
    const match = !query || `${node.label} ${node.kind} ${node.source} ${node.scope}`.toLowerCase().includes(query);
    const focused = state.focus.kind === 'node' && state.focus.id === node.id;
    const group = svgEl('g', { transform: `translate(${p.x} ${p.y})`, class: `node${status === 'ADMITTED' ? ' selected' : ''}${status === 'DENIED' ? ' denied' : ''}${focused ? ' focused' : ''}${match || path.includes(node.id) ? '' : ' dimmed'}`, tabindex: 0, role: 'button', 'aria-label': `${node.label}, ${status}, ${node.scope}` });
    const accent = status === 'DENIED' ? '#ff9dac' : status === 'ADMITTED' ? '#9cf2cf' : node.kind === 'gate' || node.kind === 'constraint' ? '#f6d391' : node.kind === 'outcome' ? '#f4b4df' : '#86bedb';
    group.append(svgEl('rect', { x: -63, y: -31, width: 126, height: 62, rx: 9, class: 'frame' }));
    group.append(svgEl('line', { x1: -62, x2: -62, y1: -20, y2: 20, class: 'side-line', stroke: accent }));
    const kind = svgEl('text', { x: -49, y: -12, class: 'node-kind' }); kind.textContent = node.kind.toUpperCase();
    const title = svgEl('text', { x: -49, y: 6, class: 'node-label' }); title.textContent = node.label;
    const meta = svgEl('text', { x: -49, y: 22, class: 'node-meta' }); meta.textContent = node.scope === 'other-tenant' ? 'OUT OF SCOPE' : node.contextEligible ? `${node.tokens} tokens · trust ${node.trust}` : node.scope.toUpperCase();
    group.append(kind, title, meta);
    const onSelect = () => { state.focus = { kind: 'node', id: node.id }; draw(); };
    let drag = null;
    group.addEventListener('pointerdown', event => { if (event.button !== 0) return; event.stopPropagation(); drag = { x: event.clientX, y: event.clientY, moved: false }; group.setPointerCapture(event.pointerId); });
    group.addEventListener('pointermove', event => {
      if (!drag) return;
      const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
      if (!drag.moved) return;
      const point = screenToGraph(event.clientX, event.clientY);
      state.positions[node.id] = { x: Math.max(65, Math.min(1090, point.x)), y: Math.max(55, Math.min(610, point.y)) };
      drag.x = event.clientX; drag.y = event.clientY;
      // Redraw after release to preserve pointer capture during drag.
      group.setAttribute('transform', `translate(${state.positions[node.id].x} ${state.positions[node.id].y})`);
    });
    group.addEventListener('pointerup', event => { if (!drag) return; const moved = drag.moved; drag = null; group.releasePointerCapture(event.pointerId); if (moved) draw(); else onSelect(); });
    group.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(); } });
    layer.append(group);
  }
  function draw() {
    const s = current(), sel = selection(), query = matching();
    const nodes = new Map(s.nodes.map(n => [n.id, n]));
    const path = focusPath();
    svg.replaceChildren();
    const defs = svgEl('defs');
    for (const [type, meta] of Object.entries(relationMeta)) {
      const marker = svgEl('marker', { id: `arrow-${type}`, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 5, markerHeight: 5, orient: 'auto-start-reverse' });
      marker.append(svgEl('path', { d: 'M 0 1 L 9 5 L 0 9 z', fill: meta.color })); defs.append(marker);
    }
    svg.append(defs);
    const viewport = svgEl('g', { id: 'graph-viewport' });
    const zones = svgEl('g'), edges = svgEl('g'), labels = svgEl('g'), nodesLayer = svgEl('g');
    drawZones(zones);
    for (const edge of s.edges) drawEdge(edges, labels, edge, nodes, sel, path, query);
    for (const node of s.nodes) drawNode(nodesLayer, node, sel, path, query);
    viewport.append(zones, edges, labels, nodesLayer); svg.append(viewport); applyTransform();
    updateUI(s, sel); updateInspection(s, sel);
  }
  function setInspection(title, badge, description, rows, path) {
    $('inspect-kind').textContent = badge;
    const box = $('inspection'); box.replaceChildren();
    box.append(htmlEl('h3', '', title), htmlEl('p', 'inspect-text', description));
    for (const [label, value] of rows) {
      const line = htmlEl('div', 'inspect-row'); line.append(htmlEl('span', '', label), htmlEl('span', '', value)); box.append(line);
    }
    if (path) box.append(htmlEl('div', 'inspect-path', path));
  }
  function updateInspection(s, sel) {
    if (state.focus.kind === 'edge') {
      const edge = s.edges.find(e => e.id === state.focus.id);
      if (!edge) return;
      const from = s.nodes.find(n => n.id === edge.from), to = s.nodes.find(n => n.id === edge.to);
      setInspection(`${from.label} → ${to.label}`, edge.type.replaceAll('_', ' '), edge.evidence,
        [['Relation type', relationMeta[edge.type].label], ['Confidence', fmt(edge.confidence)], ['Source scope', from.scope], ['Target scope', to.scope]],
        edge.type === 'BLOCKED' ? 'DENIED / cross-tenant source cannot enter the context bundle' : `${from.id} → ${edge.type} → ${to.id}`);
      return;
    }
    const node = s.nodes.find(n => n.id === state.focus.id) || s.nodes.find(n => n.id === 'task');
    const status = nodeStatus(node, sel);
    const path = pathTo(s, node.id);
    setInspection(node.label, status, node.id === 'task' ? s.query : node.source,
      [['Type', node.kind], ['Visibility', node.scope], ['Trust', `${node.trust}/3`], ['Freshness', node.freshness], ['Token cost', node.tokens || '—'], ['Relevance', node.contextEligible ? fmt(node.relevance) : '—']],
      node.id === 'task' ? `GOAL / ${s.descriptions.goal}` : status === 'DENIED' ? 'DENIED / no context path or token allocation' : `EXPLAIN PATH / ${path.join(' → ')}`);
  }
  function updateUI(s, sel) {
    $('scenario-title').textContent = s.title;
    $('scenario-subtitle').textContent = s.subtitle;
    $('scale-chip').textContent = `${state.tier.toUpperCase()} / SYNTHETIC`;
    $('selected-count').textContent = sel.selected.length;
    $('token-count').textContent = sel.used;
    $('denied-count').textContent = sel.denied.length;
    $('relation-count').textContent = s.edges.length;
    $('budget-value').textContent = $('budget').value;
    $('policy-name').textContent = policy();
    $('graph-summary').textContent = `${s.nodes.length} nodes · ${s.edges.length} typed relations · ${sel.selected.length} admitted`;
    const f = state.feedback[state.tier];
    $('feedback-state').textContent = `${f.accepted} accepted · ${f.rejected} rejected`;
    for (const tab of document.querySelectorAll('.tab')) {
      const active = tab.dataset.tier === state.tier;
      tab.classList.toggle('active', active); tab.setAttribute('aria-selected', String(active));
    }
    for (const button of document.querySelectorAll('.relation-filter')) {
      const active = button.dataset.relation === state.relation;
      button.classList.toggle('off', !active); button.setAttribute('aria-pressed', String(active));
    }
  }
  function zoom(factor, originX = 575, originY = 315) {
    const t = state.transform, next = Math.max(.7, Math.min(2.1, t.k * factor));
    const ratio = next / t.k;
    t.x = originX - (originX - t.x) * ratio;
    t.y = originY - (originY - t.y) * ratio;
    t.k = next; applyTransform();
  }
  function exportSVG() {
    const copy = svg.cloneNode(true);
    copy.setAttribute('xmlns', ns); copy.setAttribute('width', '1380'); copy.setAttribute('height', '780');
    const style = svgEl('style');
    style.textContent = `svg{background:#0c1b2b}.zone{fill:#132b3b;stroke:#335062}.zone-title{fill:#90b7c7;font:800 12px monospace}.edge{fill:none;stroke-width:2.5;opacity:.8}.edge.blocked{stroke-dasharray:5 5}.edge-label{fill:#dbedf4;font:700 10px monospace;text-anchor:middle;paint-order:stroke;stroke:#0c1b2b;stroke-width:5px}.node .frame{fill:#173146;stroke:#7ab3c7;stroke-width:2}.node.selected .frame{fill:#1d4b45;stroke:#a8f6d0}.node.denied .frame{fill:#472b3e;stroke:#f395a7}.node .side-line{stroke-width:3}.node .node-kind{fill:#a6c8d8;font:800 9px monospace}.node .node-label{fill:#fff;font:700 14px sans-serif}.node .node-meta{fill:#c4dce5;font:11px monospace}.node.dimmed,.edge.dimmed,.edge-label.dimmed{opacity:.15}.sweep{fill:none;stroke:#477c80}`;
    copy.insertBefore(style, copy.firstChild);
    const data = new Blob([new XMLSerializer().serializeToString(copy)], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(data), link = document.createElement('a');
    link.href = url; link.download = `swarm-context-${state.tier}-graph.svg`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function attach() {
    const filters = $('relation-filters');
    for (const type of Object.keys(relationGroups)) {
      const button = htmlEl('button', 'relation-filter', type);
      button.type = 'button'; button.dataset.relation = type;
      const dot = htmlEl('i'); dot.style.setProperty('--rel-color', type === 'ALL' ? '#9becda' : type === 'DENIED' ? '#fa829c' : type === 'POLICY' ? '#ffd38b' : type === 'OUTCOME' ? '#f5aad8' : '#8ca9ec');
      button.prepend(dot); button.addEventListener('click', () => { state.relation = type; draw(); }); filters.append(button);
    }
    document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {
      state.tier = tab.dataset.tier; state.positions = {}; state.focus = { kind: 'node', id: 'task' };
      state.transform = { x: 0, y: 0, k: 1 }; $('node-search').value = ''; draw();
    }));
    $('node-search').addEventListener('input', draw);
    $('budget').addEventListener('input', draw);
    $('accept').addEventListener('click', () => { state.feedback[state.tier].accepted++; draw(); });
    $('reject').addEventListener('click', () => { state.feedback[state.tier].rejected++; draw(); });
    $('zoom-in').addEventListener('click', () => zoom(1.15));
    $('zoom-out').addEventListener('click', () => zoom(1 / 1.15));
    $('reset-view').addEventListener('click', () => { state.transform = { x: 0, y: 0, k: 1 }; state.positions = {}; draw(); });
    $('export-svg').addEventListener('click', exportSVG);
    svg.addEventListener('wheel', event => {
      event.preventDefault();
      const rect = svg.getBoundingClientRect();
      const x = (event.clientX - rect.left) * 1150 / rect.width;
      const y = (event.clientY - rect.top) * 650 / rect.height;
      zoom(event.deltaY < 0 ? 1.12 : 1 / 1.12, x, y);
    }, { passive: false });
    let pan = null;
    svg.addEventListener('pointerdown', event => {
      if (event.button !== 0 || event.target.closest('.edge-group, .node')) return;
      pan = { x: event.clientX, y: event.clientY }; svg.setPointerCapture(event.pointerId); svg.classList.add('panning');
    });
    svg.addEventListener('pointermove', event => {
      if (!pan) return;
      const rect = svg.getBoundingClientRect();
      state.transform.x += (event.clientX - pan.x) * 1150 / rect.width;
      state.transform.y += (event.clientY - pan.y) * 650 / rect.height;
      pan = { x: event.clientX, y: event.clientY }; applyTransform();
    });
    svg.addEventListener('pointerup', event => { if (!pan) return; pan = null; svg.releasePointerCapture(event.pointerId); svg.classList.remove('panning'); });
    draw();
  }
  attach();
})();
