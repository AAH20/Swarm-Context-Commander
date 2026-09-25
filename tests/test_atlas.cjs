const test = require('node:test');
const assert = require('node:assert/strict');
const { scenarios, relationMeta, selectContext, pathTo } = require('../listings/huggingface-space/atlas-core.js');

test('each synthetic tier has a valid typed graph and a blocked cross-tenant edge', () => {
  assert.deepEqual(Object.keys(scenarios).sort(), ['consumer', 'enterprise', 'smb']);
  for (const [tier, graph] of Object.entries(scenarios)) {
    const ids = new Set(graph.nodes.map(node => node.id));
    assert.equal(ids.size, graph.nodes.length, `${tier}: duplicate node`);
    assert.equal(graph.edges.length, 12);
    for (const edge of graph.edges) {
      assert.ok(ids.has(edge.from) && ids.has(edge.to), `${tier}: dangling edge`);
      assert.ok(relationMeta[edge.type], `${tier}: unknown relation type`);
      assert.ok(edge.confidence >= 0 && edge.confidence <= 1);
    }
    assert.equal(graph.edges.filter(edge => edge.type === 'BLOCKED').length, 1);
    assert.deepEqual(pathTo(graph, 'foreign'), [], `${tier}: blocked edge enters explanation path`);
    assert.deepEqual(pathTo(graph, 'outcome'), ['task', 'gate', 'decision', 'outcome']);
  }
});

test('selection is deterministic, budgeted and never admits other-tenant records', () => {
  for (const graph of Object.values(scenarios)) {
    for (const budget of [0, 24, 72, 120, 200]) {
      const a = selectContext(graph, budget, 4);
      assert.deepEqual(a, selectContext(graph, budget, 4));
      assert.ok(a.used <= budget);
      assert.ok(a.selected.length <= 4);
      assert.deepEqual(a.denied, ['foreign']);
      assert.ok(!a.selected.includes('foreign'));
      assert.equal(a.used, a.selected.reduce((sum, id) => sum + graph.nodes.find(n => n.id === id).tokens, 0));
    }
  }
  assert.throws(() => selectContext(scenarios.consumer, -1), /invalid budget/);
});
