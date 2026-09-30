// Verify the UI projection against checkpoint states without a browser or model.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../cockpit/index.html'), 'utf8');
const source = html.slice(html.indexOf('function workflowNodes(job)'), html.indexOf('function renderWorkflowTrace(job)'));
const context = vm.createContext({});
vm.runInContext(source, context);
const decision = {action:'delegate', role:'developer', task:'Write result', reason:'Need result', skills:['implement-feature']};
const entry = {step:1, decision};
const project = (status, history, extra={}) => context.workflowNodes({status, result:{history,...extra}});
let nodes = project('running', [entry], {in_flight:{kind:'worker', decision}});
assert.equal(nodes.length, 1);
assert.equal(nodes[0].kind, 'running');
nodes = project('blocked', [entry], {in_flight:{kind:'worker', decision}});
assert.equal(nodes[0].detail, 'Ausgang ungeklärt');
nodes = project('awaiting_approval', [entry], {pending_approval:{id:'approval'}});
assert.equal(nodes[0].detail, 'Freigabe erforderlich');
nodes = project('running', [entry], {in_flight:{kind:'worker-resume'}});
assert.equal(nodes.length, 1);
assert.equal(nodes[0].kind, 'running');
nodes = project('running', [{...entry, report:{status:'success'}}], {in_flight:{kind:'worker',decision:{...decision,task:'Second edit'}}});
assert.equal(nodes.length, 2);
assert.equal(nodes[1].kind, 'running');
nodes = project('running', [{...entry, report:{status:'success'}}], {in_flight:{kind:'planner',step:2}});
assert.equal(nodes[1].label, 'Planung');
nodes = project('completed', [entry, {decision:{action:'finish'}}]);
assert.equal(nodes[0].kind, 'pending'); // overall success must not invent missing evidence
assert.equal(nodes[1].label, 'Abschluss');
assert.equal(nodes[1].kind, 'done');
nodes = project('blocked', [{decision:{action:'finish'}}]);
assert.equal(nodes[0].kind, 'failed'); // refused completion gate
nodes = project('completed', [
  {...entry,report:{status:'success'}},
  {decision:{action:'delegate',role:'reviewer'},report:{status:'needs_revision'}},
  {...entry,report:{status:'success'}},
  {decision:{action:'delegate',role:'reviewer'},report:{status:'success'}},
  {decision:{action:'finish'}},
]);
assert.equal(nodes.map(n=>n.kind).join(','), 'done,review,done,done,done');
assert.equal(project('blocked', [{decision:{action:'blocked'}}])[0].kind, 'failed');
console.log('Workflow trace: 10 checkpoint scenarios passed');
