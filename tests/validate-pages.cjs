"use strict";
const fs=require("node:fs");
const vm=require("node:vm");
const assert=require("node:assert/strict");
const pages=["index.html","qualidade.html","resumo.html"];
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
  assert.match(html,/href="\.\/resumo\.html"/, "Página principal não aponta para o resumo");
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
  const at=Date.parse("2026-10-23T22:00:00Z"),triageSha="a".repeat(40);
  const project={id:"crm-vendas"};
  const base={ci:{id:123,status:"completed",conclusion:"success",head_sha:triageSha},
    tests:{status:"available",run_id:123,run_conclusion:"success",head_sha:triageSha,
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

  // A medição de etapas deve coincidir com o mesmo run ID/SHA e coleta recente.
  {
    const s0=html.indexOf("function ciStepEvidence("),
          s1=html.indexOf("function renderEvidenceTriage()",s0);
    assert.ok(s0>0&&s1>s0,"Validador de etapas da CI ausente");
    const ctx2=vm.createContext({});
    vm.runInContext(html.slice(s0,s1),ctx2);
    const sha2="b".repeat(40), at2=Date.parse("2026-10-23T22:00:00Z");
    const sample={ci:{id:123,head_sha:sha2},
      verified_at:{ci_test_steps:"2026-10-23T21:58:00Z"},
      errors:{},
      ci_test_steps:{status:"observed",run_id:123,head_sha:sha2,partial:false,
        steps:[{job_id:321,name:"Run repository tests",status:"completed",conclusion:"success"},
               {job_id:322,name:"Run integration tests",status:"completed",conclusion:"failure"}]}};
    const check=(rec,when=at2)=>{
      ctx2.row=rec;return vm.runInContext("ciStepEvidence({id:'crm-vendas'},row,"+when+")",ctx2);
    };
    assert.equal(check(sample).kind,"observed");
    assert.equal(check(sample).passed,1);
    assert.equal(check(sample).failed,1);
    assert.equal(check(sample).steps.length,2);
    assert.equal(check({...sample,ci_test_steps:{...sample.ci_test_steps,run_id:124}}).kind,"unknown");
    assert.equal(check({...sample,ci_test_steps:{...sample.ci_test_steps,head_sha:"a".repeat(40)}}).kind,"unknown");
    assert.equal(check({...sample,errors:{ci_test_steps:"API"}}).kind,"unknown");
    assert.equal(check(sample,at2+40*60000).kind,"unknown");
    assert.equal(check({}).kind,"unknown");
  }


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
 if(page==="resumo.html"){
  for(const id of ["project-grid","total-projects","overall-progress","overall-milestones","source-message","refresh","search","result-count"]){
    assert.ok(ids.includes(id),"Resumo sem ID: "+id);
  }
  assert.match(html,/const PROJECTS=\[/,"Catálogo de projetos ausente");
  const projectSection=html.slice(html.indexOf("const PROJECTS=["),html.indexOf("const grid="));
  const repoIds=[...projectSection.matchAll(/\bid:"([^"]+)"/g)].map(x=>x[1]);
  assert.equal(repoIds.length,10,"Resumo deve listar os dez projetos monitorados");
  assert.equal(new Set(repoIds).size,10,"Repositórios duplicados no resumo");
  for(const project of ["crm-vendas","dispatch","pabx-mvp","axe-voice-desktop","dispatch-v2",
     "centralizador-controle","aderencia_tecnica","axe-gestao-convites","central-despacho-alertas-publicacao","axe-fomento"]){
    assert.ok(repoIds.includes(project),"Projeto ausente no resumo: "+project);
  }
  assert.match(html,/portfolio-status\.json/,"Resumo não consulta o snapshot oficial");
  assert.match(html,/source\.progress/,"Resumo não usa marcos verificados do snapshot");
   assert.match(html,/axe-fomento/,"Resumo não possui AXE Fomento");
  assert.match(html,/function freshness\(data,now=Date\.now\(\)\)/,"Proteção de dados antigos ausente");
  assert.match(html,/now-time>20\*60000/,"Dados com mais de 20 min não sinalizados como antigos");
  assert.match(html,/status de execução não é homologação/,"Sem aviso de limite da CI");
  assert.match(html,/href="\.\/index\.html#liberacao"/,"Sem acesso à homologação");

  assert.match(html,/function milestoneDetails\(/,"Resumo não apresenta marcos rastreáveis");
  assert.match(html,/function releaseDetails\(/,"Resumo não verifica registro GO/NO-GO");
  assert.match(html,/function observedEvidence\(/,"Resumo não mostra as fontes GitHub");
  assert.match(html,/class="project-details"/,"Resumo sem detalhe expansível de projeto");
  assert.match(html,/Link direto deste projeto/,"Links individuais ausentes");
  const canonicalHtml=fs.readFileSync("index.html","utf8");
  const expectedMilestones=Object.fromEntries(
    [...canonicalHtml.matchAll(/\{id:"([^"]+)",name:"([^"]+)"[\s\S]*?milestones:\[([\s\S]*?)\],history:\[/g)]
      .map(match=>[match[1],JSON.parse("["+match[3]+"]")])
  );
  const milestoneStart=html.indexOf("const MILESTONES="),
        milestoneEnd=html.indexOf("const grid=",milestoneStart);
  const logicStart=html.indexOf("function milestoneDetails("),
        logicEnd=html.indexOf("function render(){",logicStart);
  assert.ok(milestoneStart>=0&&milestoneEnd>milestoneStart&&logicEnd>logicStart,"Lógica de marcos não isolável");
  const ctx=vm.createContext({source:null,repoUrl:id=>"https://github.com/jeffaxe81/"+id,
    escapeText:str=>String(str).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))});
  vm.runInContext(html.slice(milestoneStart,milestoneEnd)+html.slice(logicStart,logicEnd),ctx);
  const actualMilestones=JSON.parse(JSON.stringify(vm.runInContext("MILESTONES",ctx)));
  assert.deepEqual(actualMilestones,expectedMilestones,"Resumos de marcos diferentes da fonte oficial do painel");
  assert.equal(Object.keys(actualMilestones).length,10);
  assert.deepEqual(actualMilestones["axe-fomento"],[["Escopo da V1 e roadmap registrados no README",true],["Código-fonte da V1 e testes disponíveis para verificação",false],["Integração verificável com editais oficiais e respectivas fontes",false],["Segurança, isolamento municipal e testes integrados homologados",false],["Aceite operacional e liberação para produção registrados",false]],"Somente a documentação do Fomento possui marco concluído");
  assert.equal(actualMilestones["axe-fomento"].filter(x=>x[1]).length,1);
  const releaseLedger=JSON.parse(fs.readFileSync("release-approvals.json","utf8"));
  assert.equal(Object.keys(releaseLedger.projects).length,10,"Livro de homologação deve listar dez projetos");
  const fomentoLedger=releaseLedger.projects["axe-fomento"];
  assert.ok(fomentoLedger,"Fomento deve possuir livro de homologação");
  assert.deepEqual(fomentoLedger.decisions,[],"Não registrar GO sem homologação");
  assert.deepEqual(Object.keys(fomentoLedger.checks).sort(),["approval","data","functional","rollback","security"].sort());
  assert.ok(Object.values(fomentoLedger.checks).every(x=>x.status==="not_recorded"&&x.evidence===null),
    "Requisitos do Fomento não podem ser presumidos");

  const proj={id:"crm-vendas"},rows=actualMilestones[proj.id],done=rows.filter(x=>x[1]).length;
  const sample={progress:{"crm-vendas":{completed:done,total:rows.length}}};
  ctx.sample=sample;
  assert.equal(vm.runInContext("milestoneDetails({id:'crm-vendas'},sample).state",ctx),"matching");
  ctx.sample={progress:{"crm-vendas":{completed:done+1,total:rows.length}}};
  assert.equal(vm.runInContext("milestoneDetails({id:'crm-vendas'},sample).state",ctx),"mismatch");
  assert.equal(vm.runInContext("milestoneDetails({id:'unknown'},sample).state",ctx),"missing");
  const checks=Object.fromEntries(["functional","security","data","rollback","approval"].map(
    k=>[k,{status:"not_recorded",evidence:null}]));
  ctx.ledger={owner:"jeffaxe81",schema_version:1,projects:{"crm-vendas":{checks,decisions:[]}}};
  ctx.sample={release_control:ctx.ledger};
  assert.equal(vm.runInContext("releaseDetails({id:'crm-vendas'},sample).state",ctx),"unrecorded");
  ctx.sample.release_control.projects["crm-vendas"].decisions.push({outcome:"GO"});
  assert.equal(vm.runInContext("releaseDetails({id:'crm-vendas'},sample).state",ctx),"unknown",
    "GO without verified checks must not be shown as approved");
  ctx.sample.release_control.projects["crm-vendas"].decisions[0].outcome="NO-GO";
  assert.equal(vm.runInContext("releaseDetails({id:'crm-vendas'},sample).state",ctx),"no-go");
  ctx.sample={projects:{"crm-vendas":{ci:{id:123,head_sha:"a".repeat(40),status:"completed",conclusion:"success"},
    prs:{latest:{number:316,state:"open"}},commits:[{sha:"b".repeat(40),title:"Verified commit"}],errors:{}}}};
  const evidence=vm.runInContext("observedEvidence({id:'crm-vendas'},sample)",ctx);
  assert.equal(evidence.ci.url,"https://github.com/jeffaxe81/crm-vendas/actions/runs/123");
  assert.equal(evidence.pr.url,"https://github.com/jeffaxe81/crm-vendas/pull/316");
  ctx.sample.projects["crm-vendas"].ci.head_sha="invalid";
  assert.equal(vm.runInContext("observedEvidence({id:'crm-vendas'},sample).ci",ctx),null);
  const fake={id:"crm-vendas"};
  ctx.project=fake;
  ctx.details={state:"matching",rows:[["<script>alert(1)</script>",true]],done:1,total:1};
  ctx.release={label:"Sem GO ou NO-GO formal registrado",checks:0,total:5};
  ctx.evidence={pr:null,ci:null,commit:null};
  const safe=vm.runInContext("renderProjectDetails(project,details,release,evidence)",ctx);
  assert.ok(safe.includes("&lt;script&gt;")&&!safe.includes("<script>"),"HTML do projeto deve escapar conteúdo");

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
