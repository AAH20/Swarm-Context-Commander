/* Synthetic graph fixtures and pure, inspectable selection logic. No external calls. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SwarmAtlas = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const positions = {
    identity: [110, 128], catalog: [110, 310], event: [110, 506],
    preference: [345, 112], rule: [345, 270], history: [345, 432], foreign: [345, 575],
    task: [575, 315], gate: [795, 185], candidate: [795, 405],
    decision: [1005, 230], outcome: [1005, 470],
  };
  const makeNode = (id, label, kind, extra = {}) => ({
    id, label, kind, x: positions[id][0], y: positions[id][1],
    scope: 'tenant', trust: 3, freshness: 'current', tokens: 0,
    source: 'synthetic fixture', relevance: 0, contextEligible: false,
    ...extra,
  });
  function scenario(title, subtitle, tenant, query, descriptions, nodeSpecs, edgeSpecs) {
    const nodes = nodeSpecs.map(([id, label, kind, extra]) => makeNode(id, label, kind, extra));
    const edges = edgeSpecs.map(([from, to, type, confidence, evidence]) => ({
      id: `${from}:${type}:${to}`, from, to, type, confidence, evidence,
    }));
    return { title, subtitle, tenant, query, descriptions, nodes, edges };
  }
  const commonEdges = [
    ['identity', 'preference', 'DERIVED_FROM', .99, 'Owned profile entry'],
    ['identity', 'rule', 'DERIVED_FROM', .96, 'Owner constraint'],
    ['catalog', 'candidate', 'SUPPLIES', .94, 'Catalog snapshot'],
    ['event', 'task', 'TRIGGERS', 1, 'Current request'],
    ['preference', 'task', 'INFORMS', .91, 'Relevant preference'],
    ['rule', 'gate', 'CONSTRAINS', .99, 'Explicit constraint'],
    ['history', 'task', 'INFORMS', .70, 'Earlier observation'],
    ['task', 'gate', 'EVALUATES', 1, 'Policy checkpoint'],
    ['gate', 'decision', 'AUTHORIZES', .99, 'Approved policy only'],
    ['candidate', 'decision', 'SUPPORTS', .86, 'Candidate evidence'],
    ['decision', 'outcome', 'MEASURED_BY', .95, 'Independent outcome'],
    ['foreign', 'task', 'BLOCKED', 1, 'Cross-tenant source denied'],
  ];
  const scenarios = {
    consumer: scenario(
      'Personal decision graph', 'A repairable product within a real budget', 'household-alex',
      'Find a repairable headset below $80',
      { goal: 'Accepted recommendation with budget and repair preference respected', gate: 'Agent owner + public scope; cross-person data denied' },
      [
        ['identity', 'Alex profile', 'actor', { scope: 'agent', source: 'synthetic profile / p-01' }],
        ['catalog', 'Product catalog', 'source', { scope: 'public', source: 'synthetic catalog / c-01' }],
        ['event', 'Shopping request', 'event', { scope: 'agent', source: 'synthetic request / e-01' }],
        ['preference', 'Repairability', 'memory', { scope: 'agent', tokens: 22, relevance: .96, contextEligible: true, source: 'profile / p-01', freshness: '2d old' }],
        ['rule', '$80 budget', 'constraint', { scope: 'agent', tokens: 18, relevance: 1, contextEligible: true, source: 'profile / p-01', freshness: 'today' }],
        ['history', 'Prior return', 'memory', { scope: 'agent', tokens: 28, relevance: .54, contextEligible: true, source: 'order / o-14', freshness: '30d old' }],
        ['foreign', 'Other profile', 'denied', { scope: 'other-tenant', tokens: 15, relevance: .99, contextEligible: true, source: 'unrelated tenant / denied' }],
        ['task', 'Select headset', 'task', { scope: 'agent' }],
        ['gate', 'Scope + budget', 'gate', { scope: 'agent' }],
        ['candidate', 'Headset A', 'candidate', { scope: 'public', tokens: 25, relevance: .84, contextEligible: true, source: 'catalog / c-01', freshness: '7d old' }],
        ['decision', 'Recommendation', 'decision', { scope: 'agent' }],
        ['outcome', 'User accepts?', 'outcome', { scope: 'agent' }],
      ], commonEdges),
    smb: scenario(
      'Merchant operations graph', 'Restock before demand rises without losing margin', 'merchant-01',
      'Restock inventory above margin floor',
      { goal: 'Accepted replenishment decision per fully loaded dollar', gate: 'Merchant tenant scope; competitor data denied' },
      [
        ['identity', 'Merchant team', 'actor', { source: 'synthetic staff / t-01' }],
        ['catalog', 'Supplier feed', 'source', { source: 'synthetic supplier / s-03' }],
        ['event', 'Low-stock alert', 'event', { source: 'synthetic event / e-07' }],
        ['preference', 'Seasonal demand', 'memory', { tokens: 30, relevance: .79, contextEligible: true, source: 'forecast / f-02', freshness: '1d old' }],
        ['rule', 'Margin floor', 'constraint', { tokens: 24, relevance: 1, contextEligible: true, source: 'policy / m-01', freshness: 'today' }],
        ['history', 'Last reorder', 'memory', { tokens: 27, relevance: .58, contextEligible: true, source: 'order / o-09', freshness: '21d old' }],
        ['foreign', 'Rival margin', 'denied', { scope: 'other-tenant', tokens: 15, relevance: .99, contextEligible: true, source: 'unrelated tenant / denied' }],
        ['task', 'Plan restock', 'task'],
        ['gate', 'Tenant + margin', 'gate'],
        ['candidate', 'Supplier quote', 'candidate', { tokens: 32, relevance: .91, contextEligible: true, source: 'supplier / s-03', freshness: 'today' }],
        ['decision', 'Order proposal', 'decision'],
        ['outcome', 'Margin kept?', 'outcome'],
      ], commonEdges),
    enterprise: scenario(
      'Incident operations graph', 'A source-linked handoff under a strict policy', 'ops-tenant',
      'Prepare incident handoff and recovery checks',
      { goal: 'Accepted handoff within incident SLO and access boundary', gate: 'Current kernel: tenant + agent only; role/region policy is future work' },
      [
        ['identity', 'Response team', 'actor', { source: 'synthetic roster / r-01' }],
        ['catalog', 'Runbook store', 'source', { source: 'synthetic docs / d-04' }],
        ['event', 'Incident page', 'event', { source: 'synthetic alert / a-05' }],
        ['preference', 'On-call owner', 'memory', { scope: 'agent', tokens: 27, relevance: .82, contextEligible: true, source: 'roster / r-01', freshness: 'today' }],
        ['rule', 'Handoff rule', 'constraint', { tokens: 26, relevance: 1, contextEligible: true, source: 'policy / h-01', freshness: 'today' }],
        ['history', 'Prior incident', 'memory', { tokens: 33, relevance: .61, contextEligible: true, source: 'case / i-11', freshness: '14d old' }],
        ['foreign', 'Other tenant', 'denied', { scope: 'other-tenant', tokens: 19, relevance: .99, contextEligible: true, source: 'unrelated tenant / denied' }],
        ['task', 'Build handoff', 'task'],
        ['gate', 'Scope + trust', 'gate'],
        ['candidate', 'Recovery runbook', 'candidate', { tokens: 35, relevance: .94, contextEligible: true, source: 'runbook / d-04', freshness: '2d old' }],
        ['decision', 'Handoff packet', 'decision'],
        ['outcome', 'Reviewer signs?', 'outcome'],
      ], commonEdges),
  };
  const relationMeta = {
    DERIVED_FROM: { color: '#8ca9ec', label: 'derived from' },
    SUPPLIES: { color: '#7fd8dd', label: 'supplies' },
    TRIGGERS: { color: '#e6b5ff', label: 'triggers' },
    INFORMS: { color: '#91bcff', label: 'informs' },
    CONSTRAINS: { color: '#ffd38b', label: 'constrains' },
    EVALUATES: { color: '#b0d6fe', label: 'evaluates' },
    AUTHORIZES: { color: '#a0ecba', label: 'authorizes' },
    SUPPORTS: { color: '#75dce6', label: 'supports' },
    MEASURED_BY: { color: '#f5aad8', label: 'measured by' },
    BLOCKED: { color: '#fa829c', label: 'blocked' },
  };
  function selectContext(scenarioData, budget, maxItems = 4) {
    if (!Number.isFinite(budget) || budget < 0 || !Number.isInteger(maxItems) || maxItems < 0) throw new Error('invalid budget or maxItems');
    const candidates = scenarioData.nodes.filter(n => n.contextEligible && n.scope !== 'other-tenant');
    candidates.sort((a, b) => (b.relevance + b.trust * .04) - (a.relevance + a.trust * .04) || a.id.localeCompare(b.id));
    const selected = []; let used = 0;
    for (const item of candidates) {
      if (selected.length < maxItems && used + item.tokens <= budget) { selected.push(item.id); used += item.tokens; }
    }
    return { selected, used, denied: scenarioData.nodes.filter(n => n.contextEligible && n.scope === 'other-tenant').map(n => n.id) };
  }
  function pathTo(scenarioData, targetId) {
    const graph = new Map(scenarioData.nodes.map(n => [n.id, []]));
    scenarioData.edges.filter(e => e.type !== 'BLOCKED').forEach(e => {
      graph.get(e.from).push(e.to); graph.get(e.to).push(e.from);
    });
    if (!graph.has(targetId)) return [];
    const queue = [['task']]; const seen = new Set(['task']);
    for (const path of queue) {
      const last = path[path.length - 1];
      if (last === targetId) return path;
      for (const next of graph.get(last)) if (!seen.has(next)) { seen.add(next); queue.push([...path, next]); }
    }
    return [];
  }
  return { scenarios, relationMeta, selectContext, pathTo };
});
