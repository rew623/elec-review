// 실제 PDF로 앱 전체 흐름 시험 (Playwright, 저장소 폴더를 http로 띄운 뒤 실행)
//   cd 저장소 && python3 -m http.server 8767 &
//   ln -s /경로/도면.pdf ./test.pdf      (시험 뒤 꼭 지울 것: *.pdf 는 .gitignore 처리돼 있음)
//   NODE_PATH=$(npm root -g) node tools/e2e.js [쪽번호들…]   예) node tools/e2e.js 101 37 71
const {chromium}=require('playwright');
(async()=>{
  const pages=process.argv.slice(2).map(Number);const b=await chromium.launch();
  const pg=await b.newPage({viewport:{width:+process.env.VW||1280,height:+process.env.VH||900}});
  const errs=[];pg.on('pageerror',e=>errs.push(e.message));
  await pg.goto('http://localhost:8767/index.html');
  await pg.waitForFunction(()=>window.pdfjsLib,null,{timeout:20000});
  const t0=Date.now();
  pg.evaluate(async()=>{const r=await fetch('test.pdf');const bl=await r.blob();await window.__app.openPdf(new File([bl],'test.pdf',{type:'application/pdf'}))});
  await pg.waitForFunction(()=>{const S=window.__app.S;return S.segs.length&&S.auto&&S.auto.mode&&!S.auto.busy},null,{timeout:300000});
  const first=await pg.evaluate(()=>{const S=window.__app.S;return {page:S.pageNum,name:S.pageName,mode:S.auto.mode,items:(S.auto.items||[]).map(g=>g.type+':'+g.hits.length+'/'+g.qty+':'+g.status)}});
  console.log('첫 결과',Date.now()-t0,'ms',JSON.stringify(first));
  for(const p of pages){
    await pg.evaluate(p=>{window.__app.S.userPicked=true;return window.__app.loadPage(p)},p);
    await pg.waitForFunction(p=>{const S=window.__app.S;return S.pageNum===p&&S.auto&&S.auto.mode!==undefined&&!S.auto.busy},p,{timeout:120000}).catch(()=>{});
    await pg.waitForTimeout(500);
    console.log(p,JSON.stringify(await pg.evaluate(()=>{const A=window.__app.S.auto;return {mode:A.mode,legend:(A.items||[]).map(g=>g.type+':'+g.hits.length+'/'+g.qty),brk:A.brk&&A.brk.length,tags:A.tags&&A.tags.length}})));
    await pg.screenshot({path:'/tmp/e2e_'+p+'.png'});
  }
  console.log('오류',errs);await b.close();
})();
