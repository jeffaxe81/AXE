"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const [portfolioPath, qualityPath] = process.argv.slice(2);
if (!portfolioPath || !qualityPath) throw new Error("Usage: node test_dashboard.cjs <index.html> <qualidade.html>");

function mockPage(path) {
  const html = fs.readFileSync(path, "utf8");
  const script = html.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(script, "Expected one inline script: " + path);
  new vm.Script(script[1], {filename: path});
  const timers = new Map(), storage = {}, elements = new Map(), events = {};
  let timerSeq = 0;
  const element = id => {
    if (elements.has(id)) return elements.get(id);
    const obj = {
      id, value: "", textContent: "", innerHTML: "", disabled: false, className: "",
      style: {}, options: [], children: [], selectedIndex: 1,
      classList: {add(){}, remove(){}, toggle(){}},
      addEventListener(){}, remove(){}, click(){}, setAttribute(){},
      appendChild(child) {this.children.push(child); this.options.push(child); return child;},
      replaceChildren(){this.children = [];},
      querySelector(){return null;}
    };
    elements.set(id,obj);
    return obj;
  };
  for (const id of ["search","sort","trend-project","trend-range","history-project"]) element(id);
  element("sort").value = "priority";
  element("trend-project").value = "all";
  element("history-project").value = "all";
  element("trend-range").value = "30";
  element("trend-range").options = [
    {textContent:"7 dias"},{textContent:"30 dias"},
    {textContent:"90 dias"},{textContent:"Todo o histórico"}
  ];
  const document = {
    hidden: false, getElementById: element,
    querySelectorAll(){return []}, querySelector(){return null},
    addEventListener(name,cb){events["document:"+name] = cb;},
    body: {appendChild(){}},
    createElement(){return {
      value:"",textContent:"",children:[],className:"",style:{},
      appendChild(c){this.children.push(c);return c;},
      addEventListener(){},remove(){},click(){}
    }}
  };
  const window = {
    addEventListener(name,cb){events["window:"+name] = cb;},
    print(){}
  };
  const context = vm.createContext({
    document, window, navigator: {onLine:true},
    localStorage: {getItem:key=>storage[key]??null,setItem:(key,val)=>{storage[key]=val;}},
    setTimeout(){}, setInterval(cb,ms){const id = ++timerSeq;timers.set(id,{cb,ms});return id;},
    clearInterval(id){timers.delete(id);},
    fetch: async()=>({ok:true,json:async()=>({
      schema_version:1,owner:"jeffaxe81",generated_at:null,projects:{},progress_history:[]
    })}),
    Blob: class {}, URL: {createObjectURL(){return "blob:mock"}, revokeObjectURL(){}}
  });
  vm.runInContext(script[1],context);
  return {context,timers,elements,events,storage,fn:expr=>vm.runInContext(expr,context)};
}

function checkModes(page,selector){
  const p = mockPage(page);
  const set = p.fn(selector);
  const intervals = () => [...p.timers.values()].map(t=>t.ms);
  set("manual");
  assert.deepEqual(intervals(),[], "Manual cannot leave a running timer");
  set("15s");
  assert.deepEqual(intervals(),[15000], "15s should create exactly one timer");
  set("30s");
  assert.deepEqual(intervals(),[30000], "30s should replace previous timer");
  set("online");
  assert.deepEqual(intervals(),[15000], "Online uses a 15s visibility-aware check");
  set("manual");
  assert.deepEqual(intervals(),[], "Returning to Manual stops every timer");
  assert.equal(p.storage["axe-delivery-sync-mode-v2"],"manual");
  return p;
}

checkModes(portfolioPath,"setSyncMode");
checkModes(qualityPath,"setQualitySyncMode");

const p = mockPage(portfolioPath);
const q = mockPage(qualityPath);
const source = p.fn("sourceFreshness");
const quality = q.fn("evaluateSourceMeta");
const now = Date.parse("2026-10-22T21:50:00Z");
const date = minutes => new Date(now-minutes*60000).toISOString();
const cases = [
  [null,null,"unknown",""],
  [{verified_at:{commits:date(1),prs:date(1),ci:date(1)}},
   {verified_at:{prs:date(1),ci:date(1)}},"fresh","ok"],
  [{verified_at:{commits:date(1)}},{verified_at:{prs:date(1)}},"partial","partial"],
  [{verified_at:{commits:date(21),prs:date(21),ci:date(21)}},
   {verified_at:{prs:date(21),ci:date(21)}},"stale","stale"],
  [{verified_at:{commits:date(1),prs:date(1),ci:date(1)},errors:{ci:"API"}},
   {verified_at:{prs:date(1),ci:date(1)},errors:{ci:"API"}},"error","error"]
];
for (const [one,two,expectedOne,expectedTwo] of cases) {
  assert.equal(source(one,now).kind,expectedOne);
  assert.equal(quality(two,now).kind,expectedTwo);
}
// A fila nunca transforma ausência de leitura em zero e respeita a ordem editorial.
const queueNow=Date.parse("2026-10-23T06:10:00Z");
const recent=new Date(queueNow-2*60000).toISOString();
const checked=p.fn("nextStepInfo(PROJECTS[0],{prs:{open:2},ci:{conclusion:'failure'},verified_at:{prs:'"+recent+"',ci:'"+recent+"'},commits:[{date:'2026-10-22'}]}, "+queueNow+")");
assert.equal(checked.remaining,3);
assert.equal(checked.pending[0],"Onboarding homologado");
assert.equal(checked.openPrs,2);
assert.equal(checked.ciResult,"failure");
assert.equal(checked.quiet,false);
const unavailable=p.fn("nextStepInfo(PROJECTS[0],{prs:{open:0},ci:{conclusion:'success'},verified_at:{prs:'2026-09-01T00:00:00Z',ci:'2026-09-01T00:00:00Z'}}, "+queueNow+")");
assert.equal(unavailable.openPrs,null,"Stale PR data is unknown, never zero");
assert.equal(unavailable.ciResult,null,"Stale CI data is unknown, never success");
const errored=p.fn("nextStepInfo(PROJECTS[0],{prs:{open:2},ci:{conclusion:'failure'},errors:{prs:'HTTPError',ci:'HTTPError'},verified_at:{prs:'"+recent+"',ci:'"+recent+"'}}, "+queueNow+")");
assert.equal(errored.openPrs,null);
assert.equal(errored.ciResult,null);
assert.equal(p.fn("queueItems().length"),9);
p.fn("queueFilter.value='all'; renderQueue()");
assert.ok(p.elements.get("queue-list").innerHTML.includes("Onboarding homologado"));
assert.ok(p.elements.get("queue-list").innerHTML.includes("Issues ↗"));
assert.ok(p.elements.get("queue-list").innerHTML.includes("PRs ↗"));
assert.ok(checked.ciRunUrl===null,"Without a verified CI run ID no link may be invented");
assert.ok(p.elements.get("queue-summary").innerHTML.includes("Pendências mapeadas"));
assert.ok(p.elements.get("queue-list").innerHTML.includes("sem leitura recente"));
// Evidências só afetam a rastreabilidade, não a conclusão editorial.
assert.equal(p.fn("trackedRows().length"),15,"Exactly fifteen reviewed GitHub links");
assert.equal(p.fn("PROJECTS[0].milestones.filter(m=>m[1]).length"),4);
const trace=JSON.stringify({"crm-vendas":{"2":[{"kind":"pr","number":281,"state":"merged","verified_at":"2026-10-23T15:20:00Z"}]}});
p.fn("trackingData="+trace);
const activeTrace=p.fn("trackedRows().find(x=>x.p.id==='crm-vendas'&&x.index===2)");
assert.equal(activeTrace.ref.number,281);
assert.equal(p.fn("PROJECTS[0].milestones.filter(m=>m[1]).length"),4);
p.fn("document.getElementById('tracking-filter').value='all'; renderTracking()");
assert.ok(p.elements.get("tracking-rows").innerHTML.includes("pull/281"));
assert.ok(p.elements.get("tracking-rows").innerHTML.includes("Não verificado"));
assert.ok(p.elements.get("tracking-summary").innerHTML.includes("Vínculos revisados"));
// Matriz de gates: classificação editorial de todos os marcos; CI independente.
const coverage=p.fn("PROJECTS.map(x=>({id:x.id,all:[...GATE_MATRIX[x.id].dev,...GATE_MATRIX[x.id].tests,...GATE_MATRIX[x.id].homolog,...GATE_MATRIX[x.id].release],size:x.milestones.length}))");
for(const entry of coverage) {
  assert.equal(entry.all.length,entry.size,"Every monitored milestone must have a stage");
  assert.equal(new Set(entry.all).size,entry.size,"Milestone stages cannot overlap");
  assert.ok(entry.all.every(i=>i>=0&&i<entry.size));
}
const crmGate=p.fn("gateRecord(PROJECTS[0],"+queueNow+")");
assert.equal(crmGate.counts.dev.completed,3);
assert.equal(crmGate.counts.dev.total,3);
assert.equal(crmGate.counts.tests.completed,1);
assert.equal(crmGate.counts.homolog.completed,0);
assert.equal(crmGate.counts.release.completed,0);
assert.equal(crmGate.ciState,"Não verificada");
const validCi=JSON.stringify({"crm-vendas":{verified_at:{ci:recent},errors:{},ci:{id:12345,status:"completed",conclusion:"success"}}});
p.fn("sourceRecords="+validCi);
const successGate=p.fn("gateRecord(PROJECTS[0],"+queueNow+")");
assert.equal(successGate.ciState,"Sucesso");
assert.equal(successGate.ciLink,"https://github.com/jeffaxe81/crm-vendas/actions/runs/12345");
assert.equal(p.fn("PROJECTS[0].milestones.filter(m=>m[1]).length"),4);
p.fn("document.getElementById('gate-filter').value='all'; renderGateMatrix()");
assert.ok(p.elements.get("gate-table").innerHTML.includes("Homologação"));
assert.ok(p.elements.get("gate-table").innerHTML.includes("Não mapeado"));
assert.ok(p.elements.get("gate-summary").innerHTML.includes("Liberação pendente"));
p.fn("sourceRecords={}");

const releaseBefore=p.fn("PROJECTS.reduce((n,x)=>n+x.milestones.filter(m=>m[1]).length,0)");
assert.equal(releaseBefore,30);
assert.equal(p.fn("releaseState(PROJECTS[0]).state"),"unrecorded","Unknown is not GO");
const notReady=JSON.stringify({schema_version:1,owner:"jeffaxe81",projects:{
  "crm-vendas":{checks:{},decisions:[{outcome:"GO",reviewer:"release-reviewer",
   recorded_at:"2026-10-23T15:40:00Z",sha:"a".repeat(40),
   reference:"https://github.com/jeffaxe81/crm-vendas/pull/281",
   reason:"Test approval must not bypass missing evidence"}]}
}});
p.fn("releaseControl="+notReady);
assert.equal(p.fn("releaseState(PROJECTS[0]).state"),"invalid","A GO without all controls stays invalid");
p.fn("releaseControl.projects['crm-vendas'].decisions[0].outcome='NO_GO'");
assert.equal(p.fn("releaseState(PROJECTS[0]).state"),"no_go");
p.fn("document.getElementById('release-filter').value='all'; renderReleases()");
assert.ok(p.elements.get("release-summary").innerHTML.includes("Critérios documentados"));
assert.ok(p.elements.get("release-cards").innerHTML.includes("NO-GO registrado"));
assert.ok(p.elements.get("release-cards").innerHTML.includes("Aceite formal"));
assert.equal(p.fn("PROJECTS.reduce((n,x)=>n+x.milestones.filter(m=>m[1]).length,0)"),releaseBefore,
 "Formal decisions never alter the editorial milestone progress");

const sampleOnline=JSON.stringify({"crm-vendas":{prs:{active:[
  {number:17,title:"Homologar painel",updated_at:"2026-10-23T12:00:00Z",draft:false}]},
 commits:[{sha:"f".repeat(40),date:"2026-10-23",title:"Add dashboard"}],
 ci:{id:123,updated_at:"2026-10-23T11:30:00Z",status:"completed",conclusion:"failure",name:"CI"}}});
p.fn("sourceRecords="+sampleOnline);
p.fn("onlineProject.value='crm-vendas';onlineType.value='all';renderOnline()");
assert.equal(p.fn("onlineEvents().length"),3,"One PR, one commit and one CI should appear");
assert.ok(p.elements.get("online-feed").innerHTML.includes("Homologar painel"));
assert.ok(p.elements.get("online-feed").innerHTML.includes("pull/17"));
assert.ok(p.elements.get("online-feed").innerHTML.includes("commit/"));
assert.equal(p.fn("safeVersionUrl(PROJECTS[0],'../../bad','tag')"),null);
p.fn("versionHistory="+JSON.stringify({"crm-vendas":[
 {version:"v0.6.1",kind:"release",name:"Stable",published_at:"2026-10-20T12:00:00Z",first_seen_at:"2026-10-21T00:00:00Z"},
 {version:"checkpoint/safe",kind:"tag",first_seen_at:"2026-10-19T00:00:00Z"}]}));
p.fn("versionProject.value='crm-vendas';versionKind.value='all';renderVersions()");
assert.equal(p.fn("allVersions().length"),2);
assert.ok(p.elements.get("versions-list").innerHTML.includes("Release publicada"));
p.fn("renderProjects()");
assert.ok(p.elements.get("projects").innerHTML.includes("Release publicada: "),"Project card should surface reviewed published release");
assert.ok(p.elements.get("projects").innerHTML.includes("v0.6.1"),"Project card must expose the version number");
assert.ok(p.elements.get("versions-list").innerHTML.includes("Tag de código"));
assert.ok(p.elements.get("versions-list").innerHTML.includes("checkpoint%2Fsafe"));
p.fn("versionKind.value='release';renderVersions()");
assert.ok(!p.elements.get("versions-list").innerHTML.includes("checkpoint%2Fsafe"));
console.log("PASS: Online PR, commits, CI, tags and independently published Releases");
console.log("PASS: fail-closed GO/NO-GO controls, CSV structure, and separate milestone progress");
console.log("PASS: nine stage-gate matrices, explicit milestones, independent CI and release status");
console.log("PASS: fila de próximas entregas, 9 projetos, nulidade de PR/CI desatualizadas e evidências verificadas");
console.log("PASS: HTML JavaScript, manual/15s/30s/online timers and 10 freshness scenarios");
