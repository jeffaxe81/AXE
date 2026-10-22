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
