const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require('playwright');
const BASE=process.env.OURNOTES_BROWSER_URL||'http://127.0.0.1:8881/';

async function ready(page){
  await page.waitForFunction(()=>document.getElementById('ownedCount').textContent||!document.getElementById('loadError').hidden,null,{timeout:120000});
  if(await page.locator('#loadError').isVisible())throw new Error(await page.locator('#loadError').textContent());
}
async function own(page,kind,id){
  await page.locator(`[data-kind-tab="${kind}"]`).click();
  await page.locator(`#cardCatalog [data-add="${kind}"][data-id="${id}"]`).click();
  await page.waitForFunction(({kind,id})=>window.EventHost.state.profile.inventory[kind].some(card=>card.id===id),{kind,id});
  await page.locator('#cardEditor [data-close="cardEditor"]').first().click();
}
async function rename(page,name){
  await page.locator('#renameProfile').click();
  assert.equal(await page.locator('#archiveName').evaluate(el=>document.activeElement===el),true);
  await page.locator('#archiveName').fill(name);
  await page.locator('#archiveName').press('Tab');
  await page.waitForFunction(name=>window.EventHost.state.name===name,name);
}

(async()=>{
  const browser=await chromium.launch({headless:true,channel:process.env.OURNOTES_BROWSER_CHANNEL||(process.platform==='win32'?'msedge':undefined)});
  try{
    const context=await browser.newContext({acceptDownloads:true});
    await context.route('**/*',route=>new URL(route.request().url()).origin===new URL(BASE).origin?route.continue():route.abort());
    const page=await context.newPage();
    await page.goto(BASE);await ready(page);
    assert.equal(await page.locator('#ownedCount').textContent(),'0 + 0');
    const initial=await page.evaluate(()=>window.EventHost.archives.profiles.length);

    await page.locator('#newAccount').click();
    await page.waitForFunction(()=>window.EventHost.state.name==='账号 1');
    const first=await page.evaluate(()=>window.EventHost.archives.active_id);
    await own(page,'members',27);await own(page,'snaps',33);
    assert.equal(await page.locator('#ownedCount').textContent(),'1 + 1');

    await page.locator('#newAccount').click();
    await page.waitForFunction(()=>window.EventHost.state.name==='账号 2');
    const second=await page.evaluate(()=>window.EventHost.archives.active_id);
    await own(page,'members',30);await own(page,'snaps',37);
    await rename(page,'狗狗');
    assert.equal(await page.locator('#profileSelect option:checked').textContent(),'狗狗');

    await page.locator('#profileSelect').selectOption(first);
    await page.waitForFunction(id=>window.EventHost.archives.active_id===id,first);
    assert.deepEqual(await page.evaluate(()=>window.EventHost.state.profile.inventory.members.map(c=>c.id)),[27]);
    assert.deepEqual(await page.evaluate(()=>window.EventHost.state.profile.inventory.snaps.map(c=>c.id)),[33]);
    await rename(page,'猫猫');
    await page.locator('#profileSelect').selectOption(second);
    await page.waitForFunction(id=>window.EventHost.archives.active_id===id,second);
    assert.deepEqual(await page.evaluate(()=>window.EventHost.state.profile.inventory.members.map(c=>c.id)),[30]);
    assert.deepEqual(await page.evaluate(()=>window.EventHost.state.profile.inventory.snaps.map(c=>c.id)),[37]);
    assert.equal(await page.evaluate(()=>window.EventHost.archives.profiles.length),initial+2);

    const download=page.waitForEvent('download');await page.locator('#exportAll').click();
    const backup=JSON.parse(fs.readFileSync(await (await download).path(),'utf8'));
    assert.equal(backup.schema_version,2);
    assert.deepEqual(backup.profiles.slice(-2).map(p=>p.input.name),['猫猫','狗狗']);
    assert.deepEqual(backup.profiles.slice(-2).map(p=>p.input.profile.inventory.members[0].id),[27,30]);

    await page.locator('#import').setInputFiles({name:'unrelated.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({unrelated_format:true}))});
    await page.waitForFunction(()=>document.getElementById('message').classList.contains('error'));
    assert.equal(await page.evaluate(()=>window.EventHost.archives.profiles.length),initial+2);

    await page.reload();await ready(page);
    assert.equal(await page.evaluate(()=>window.EventHost.state.name),'狗狗');
    assert.deepEqual(await page.evaluate(()=>window.EventHost.archives.profiles.slice(-2).map(p=>p.input.name)),['猫猫','狗狗']);
    assert.deepEqual(await page.evaluate(()=>window.EventHost.state.profile.inventory.members.map(c=>c.id)),[30]);
    await page.setViewportSize({width:390,height:850});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    console.log('Account profiles: create, isolate, rename, switch, backup and reload passed');
    await context.close();
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
