"use strict";
const fs=require("node:fs");
const vm=require("node:vm");
const assert=require("node:assert/strict");
const pages=["index.html","qualidade.html"];
let passed=0;
for(const page of pages){
 const html=fs.readFileSync(page,"utf8");
 assert.match(html,/<!doctype html>/i,page+": DOCTYPE ausente");
 assert.match(html,/<html\b[^>]*lang="pt-BR"/,page+": idioma ausente");
 const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)];
 assert.ok(scripts.length>0,page+": script não localizado");
 for(let i=0;i<scripts.length;i++)new vm.Script(scripts[i][1],{filename:page+"#script-"+(i+1)});
 const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
 assert.equal(new Set(ids).size,ids.length,page+": ids HTML duplicados");
 for(const match of html.matchAll(/href="\.\/([^"#?]+)(?:[?#][^"]*)?"/g)){
  const target=decodeURIComponent(match[1]);
  assert.ok(fs.existsSync(target),page+": link local quebrado: "+target);
 }
 assert.equal((html.match(/<section\b/g)||[]).length,(html.match(/<\/section\s*>/g)||[]).length,page+": seções não balanceadas");
 if(page==="index.html"){
  assert.match(html,/href="\.\/qualidade\.html"/, "Página principal não aponta para qualidade");
  assert.match(html,/const pct=p=>Math\.round/, "Fórmula de marcos ausente");
  assert.match(html,/function releasePending\(row\)/, "Checklist de pendências de liberação ausente");
  assert.match(html,/class="release-blockers"/, "Painel de pendências expansível ausente");
  assert.match(html,/releasePending\(x\)\.join/, "Exportação de pendências CSV ausente");
  assert.match(html,/function releaseReviewEvidence\(project,nowMs=Date\.now\(\)\)/, "Revisão de evidências CI ausente");
  assert.match(html,/class="release-review"/, "Seção de referências para revisão ausente");
  assert.match(html,/CI para revisão/, "Exportação CI para revisão ausente");

  assert.match(html,/id="evidence-triage-list"/, "Fila de evidências ausente");
  assert.match(html,/function triageEvidence\(project,record,nowMs=Date\.now\(\)\)/,
    "Classificação de observações ausente");
  assert.match(html,/axe-fila-evidencias\.csv/, "Exportação CSV da fila ausente");
  const triageStart=html.indexOf("function triageEvidence("),
        triageEnd=html.indexOf("function evidenceTriageRows(",triageStart);
  assert.ok(triageStart>=0&&triageEnd>triageStart,"Função de triagem ausente");
  const ctx=vm.createContext({});
  vm.runInContext(html.slice(triageStart,triageEnd),ctx);
  const at=Date.parse("2026-10-23T22:00:00Z"),sha="a".repeat(40);
  const project={id:"crm-vendas"};
  const base={ci:{id:123,status:"completed",conclusion:"success",head_sha:sha},
    tests:{status:"available",run_id:123,run_conclusion:"success",head_sha:sha,
      passed:12,failed:0,skipped:1},
    verified_at:{ci:"2026-10-23T21:59:00Z",tests:"2026-10-23T21:59:00Z"},errors:{}};
  function triage(rec,when=at){
    ctx.record=rec;
    return vm.runInContext("triageEvidence({id:'crm-vendas'},record,"+when+")",ctx);
  }
  assert.equal(triage(base).kind,"review");
  assert.equal(triage({...base,ci:null}).kind,"no_ci");
  assert.equal(triage({...base,tests:{...base.tests,run_id:124}}).kind,"missing_counts");
  assert.equal(triage({...base,tests:{...base.tests,head_sha:"b".repeat(40)}}).kind,"missing_counts");
  assert.equal(triage({...base,tests:{...base.tests,failed:1}}).kind,"tests_failed");
  assert.equal(triage({...base,tests:{...base.tests,partial:true}}).kind,"partial");
  assert.equal(triage({...base,ci:{...base.ci,conclusion:"failure"}}).kind,"ci_failed");
  assert.equal(triage({...base,ci:{...base.ci,id:0}}).kind,"unverified");
  assert.equal(triage({...base,errors:{ci:"HTTP 403"}}).kind,"unverified");
  assert.equal(triage(base,at+40*60000).kind,"unverified");
  assert.equal(triage({}).kind,"unverified");

  // Exercitar a função isoladamente, sem permitir promoção implícita de critérios.
  const start=html.indexOf("function releaseReviewEvidence("),end=html.indexOf("function renderReleases()",start);
  assert.ok(start>=0&&end>start,"Função de revisão não isolável");
  const testCtx=vm.createContext({sourceRecords:{},repo:p=>"https://github.com/jeffaxe81/"+p.id});
  vm.runInContext(html.slice(start,end),testCtx);
  const proj={id:"crm-vendas"},sha="a".repeat(40),now=Date.parse("2026-10-23T22:00:00Z");
  function checkEvidence(record,when=now){
   testCtx.sourceRecords={"crm-vendas":record};
   return vm.runInContext("releaseReviewEvidence({id:'crm-vendas'},"+when+")",testCtx);
  }
  const good={ci:{id:123,head_sha:sha,status:"completed",conclusion:"success"},
    tests:{status:"available",run_id:123,head_sha:sha,run_conclusion:"success",
      passed:12,failed:1,skipped:2},
    verified_at:{ci:"2026-10-23T21:58:00Z",tests:"2026-10-23T21:58:00Z"},errors:{}};
  const verified=checkEvidence(good);
  assert.equal(verified.ciStatus,"recent");
  assert.equal(verified.ciUrl,"https://github.com/jeffaxe81/crm-vendas/actions/runs/123");
  assert.equal(verified.testCounts.passed,12);
  assert.equal(verified.testCounts.failed,1);
  const old=checkEvidence(good,now+40*60000);
  assert.equal(old.ciStatus,"historical");
  assert.equal(old.testCounts.stale,true);
  assert.equal(checkEvidence({...good,tests:{...good.tests,head_sha:"b".repeat(40)}}).testCounts,null);
  assert.equal(checkEvidence({...good,tests:{...good.tests,run_id:124}}).testCounts,null);
  assert.equal(checkEvidence({...good,errors:{ci:"API failure"}}).ciUrl,null);
  assert.equal(checkEvidence({...good,ci:{...good.ci,head_sha:"invalid"}}).ciUrl,null);
  assert.equal(checkEvidence({}).ciStatus,"unavailable");
 }
 if(page==="qualidade.html"){
  for(const id of ["rows","status","refresh","export","merged-count","ci-count"]){
   assert.ok(ids.includes(id),"Painel sem ID "+id);
  }
  assert.match(html,/per_page=1/, "Consulta deve limitar-se à última PR/CI");
  assert.match(html,/axe-evidencias-pr-ci\.csv/, "Exportação CSV ausente");
 }
 passed++;
 process.stdout.write("✓ "+page+": JavaScript, estrutura, IDs e links verificados\n");
}
process.stdout.write("PASS: "+passed+" páginas verificadas\n");
