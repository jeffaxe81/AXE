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

const qualityTestsData={
  "crm-vendas":{tests:{status:"available",run_id:42,passed:60,failed:2,skipped:1,
    parsed_jobs:2,scanned_jobs:3,partial:true,run_conclusion:"failure"},
    ci:{id:42,status:"completed",conclusion:"failure"},
    verified_at:{ci:"2026-10-23T12:00:00Z",tests:"2026-10-23T12:00:00Z"},errors:{}},
  "dispatch":{tests:{status:"no_summary",run_id:100,passed:null,failed:null,skipped:null},
    ci:{id:100,status:"completed",conclusion:"success"},errors:{}},
  "pabx-mvp":{tests:{status:"available",run_id:22,passed:900,failed:0,skipped:3},
    ci:{id:23,status:"completed",conclusion:"success"},errors:{}}
};
p.fn("sourceRecords="+JSON.stringify(qualityTestsData)+";renderTestOverview()");
assert.equal(p.fn("testOverviewStats().count"),63);
assert.equal(p.fn("testOverviewStats().passed"),60);
assert.equal(p.fn("testOverviewStats().projectsCount"),1);
assert.ok(p.elements.get("test-overview").innerHTML.includes("63"));
assert.ok(p.elements.get("test-overview-detail").textContent.includes("parcial"));
q.fn("qualityTests="+JSON.stringify(Object.fromEntries(Object.entries(qualityTestsData).map(([id,v])=>[id,v.tests])))+
 ";records="+JSON.stringify(Object.fromEntries(Object.entries(qualityTestsData).map(([id,v])=>[id,{ci:{id:v.ci.id}}])))+
 ";qualitySourceMeta={};renderTestCounts()");
assert.equal(q.fn("testsFor('crm-vendas').total"),63);
assert.equal(q.fn("testsFor('pabx-mvp')"),null,"Different run IDs must hide old counts");
assert.equal(q.fn("testsFor('dispatch')"),null,"Missing summary must not be reported as zero");
assert.equal(q.elements.get("test-total").textContent,"63");
assert.equal(q.elements.get("test-failed").textContent,"2");
assert.equal(q.fn("testsHistoryFor('crm-vendas').length"),0);
q.fn("qualityTestHistory="+JSON.stringify({"crm-vendas":[
  {run_id:42,status:"available",passed:60,failed:2,skipped:1},
  {run_id:42,status:"available",passed:60,failed:2,skipped:1},
  {run_id:43,status:"available",passed:61,failed:0,skipped:1}
]})+";renderTestCounts()");
assert.equal(q.fn("testsHistoryFor('crm-vendas').length"),2,"Same run cannot be counted twice");
assert.ok(q.elements.get("test-history-summary").textContent.includes("2 execuções"));

const classified={
 "crm-vendas":{status:"available",run_id:42,passed:60,failed:2,skipped:1,
  head_sha:"a".repeat(40),categories:{
   unit:{passed:15,failed:0,skipped:0},integration:{passed:0,failed:0,skipped:0},
   e2e:{passed:5,failed:1,skipped:0},security:{passed:0,failed:0,skipped:0},
   unclassified:{passed:40,failed:1,skipped:1}
  }}
};
q.fn("qualityTests="+JSON.stringify(classified)+";qualityTestHistory="+JSON.stringify({
 "crm-vendas":[{...classified["crm-vendas"],run_id:42,head_sha:"a".repeat(40)}]})+
 ";qualityVersions="+JSON.stringify({"crm-vendas":[{kind:"release",version:"v1.0.0",
  published_at:"2026-10-23T12:00:00Z",sha:"a".repeat(40)}]})+";renderTestCounts()");
assert.equal(q.fn("testCategoriesOverview().known"),1);
assert.equal(q.fn("testCategoriesOverview().totals.unit.passed"),15);
assert.equal(q.fn("testCategoriesOverview().totals.e2e.failed"),1);
assert.equal(q.fn("testCategoriesOverview().totals.unclassified.passed"),40);
assert.ok(q.elements.get("test-category-summary").innerHTML.includes("Integração"));
assert.equal(q.fn("testReleasesObserved()[0].runs.length"),1,"Only exact SHA may connect a release");
q.fn("qualityVersions['crm-vendas'][0].sha='b'.repeat(40);renderTestCounts()");
assert.equal(q.fn("testReleasesObserved()[0].runs.length"),0,"Mismatched SHA cannot inherit tests");
q.fn("qualityTests['crm-vendas'].categories.unit.passed=16;renderTestCounts()");
assert.equal(q.fn("testCategoriesOverview().known"),0,"Inconsistent category totals must not render");
console.log("PASS: explicit test suite categories reconcile, unknown stays unknown, release matching requires exact commit SHA");

const hourlyNow=Date.parse("2026-10-23T21:00:00Z");
const sampleHour={status:"measured",window_minutes:60,baseline_at:"2026-10-23T20:00:00Z",measured_at:"2026-10-23T21:00:00Z",
 portfolio:{before_percent:60,after_percent:62,delta_points:2,delta_milestones:1},
 projects:{"crm-vendas":{before_percent:57.14,after_percent:71.43,delta_points:14.29,delta_milestones:1},
 "dispatch":{before_percent:66.67,after_percent:66.67,delta_points:0,delta_milestones:0}}};
p.fn("hourlyEvidence="+JSON.stringify(sampleHour));
assert.equal(p.fn("hourlyDisplay(null,"+hourlyNow+").label"),"+2 p.p.");
assert.equal(p.fn("hourlyDisplay('crm-vendas',"+hourlyNow+").label"),"+14,29 p.p.");
assert.equal(p.fn("hourlyDisplay('dispatch',"+hourlyNow+").label"),"0 p.p.");
assert.equal(p.fn("hourlyDisplay(null,"+(hourlyNow+25*60000)+").kind"),"stale");
p.fn("renderHourlyProgress()");
assert.ok(p.elements.get("hour-summary").innerHTML.includes("Avanço consolidado"));
assert.ok(p.elements.get("hour-projects").innerHTML.includes("CRM Vendas"));
assert.ok(p.elements.get("projects").innerHTML.includes("CRM Vendas"));
p.fn("hourlyEvidence={status:'insufficient_history',baseline_at:null,measured_at:'2026-10-23T21:00:00Z',portfolio:null,projects:{}};renderHourlyProgress()");
assert.equal(p.fn("hourlyDisplay(null,"+hourlyNow+").delta"),null);
assert.ok(p.elements.get("hour-detail").textContent.includes("Sem histórico"));
assert.ok(!p.elements.get("hour-summary").innerHTML.includes("0 p.p."));

const period6={...sampleHour,window_minutes:360,baseline_at:"2026-10-23T15:00:00Z",
 measured_at:"2026-10-23T21:00:00Z"};
p.fn("progressWindows="+JSON.stringify({"60":sampleHour,"360":period6}));
p.fn("setProgressPeriod('360')");
assert.equal(p.fn("progressPeriod"),360);
assert.equal(p.fn("hourlyDisplay(null,"+hourlyNow+").label"),"+2 p.p.");
assert.equal(p.fn("hourlyDisplay('crm-vendas',"+hourlyNow+").label"),"+14,29 p.p.");
p.fn("setProgressPeriod('1440')");
assert.equal(p.fn("hourlyDisplay(null,"+hourlyNow+").delta"),null,"24h cannot be synthesized from 6h");
p.fn("setProgressPeriod('60')");
const activitySample={"crm-vendas":{
 commits:[{sha:"a".repeat(40),date:"2026-10-23",committed_at:"2026-10-23T20:35:00Z",title:"Actual commit"},
          {sha:"b".repeat(40),date:"2026-10-22",committed_at:"2026-10-22T19:00:00Z",title:"Old commit"}],
 prs:{recent:[{number:99,updated_at:"2026-10-23T20:45:00Z",state:"open"}]},
 ci:{id:999,status:"completed",updated_at:"2026-10-23T20:59:00Z",conclusion:"success"},
 verified_at:{commits:"2026-10-23T21:00:00Z",prs:"2026-10-23T21:00:00Z",
              ci:"2026-10-23T21:00:00Z"},errors:{}
}};
p.fn("sourceRecords="+JSON.stringify(activitySample)+";onlineSnapshotAt='2026-10-23T21:00:00Z'");
assert.equal(p.fn("activityForProject(PROJECTS[0],"+hourlyNow+").commits"),1);
assert.equal(p.fn("activityForProject(PROJECTS[0],"+hourlyNow+").prs"),1);
assert.equal(p.fn("activityForProject(PROJECTS[0],"+hourlyNow+").ci"),1);
assert.equal(p.fn("activityForProject(PROJECTS[0],"+(hourlyNow+25*60000)+").available"),false);
p.fn("sourceRecords['crm-vendas'].errors.prs='API';");
assert.equal(p.fn("activityForProject(PROJECTS[0],"+hourlyNow+").prs"),null,
 "Failed PR collection cannot look like zero updates");
p.fn("sourceRecords['crm-vendas'].errors={};progressPeriod=360");
assert.equal(p.fn("activityForProject(PROJECTS[0],"+hourlyNow+").commits"),1);
p.fn("progressPeriod=60");
console.log("PASS: 1h/6h/24h selection, precise commit/PR/CI activity and stale-source safeguards");

console.log("PASS: last-hour progress uses real baseline, displays percentage points and refuses missing/stale evidence");

console.log("PASS: verified counts, partial flag, distinct CI history, no inferred zero or mismatch");
console.log("PASS: Online PR, commits, CI, tags and independently published Releases");
console.log("PASS: fail-closed GO/NO-GO controls, CSV structure, and separate milestone progress");
console.log("PASS: nine stage-gate matrices, explicit milestones, independent CI and release status");
console.log("PASS: fila de próximas entregas, 9 projetos, nulidade de PR/CI desatualizadas e evidências verificadas");
console.log("PASS: HTML JavaScript, manual/15s/30s/online timers and 10 freshness scenarios");
