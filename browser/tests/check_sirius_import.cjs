const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const BASE=process.env.OURNOTES_BROWSER_URL||'http://127.0.0.1:8768/';

async function importJson(page,value){
  await page.locator('#import').setInputFiles({name:'player-data.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(value))});
  await page.waitForFunction(()=>document.getElementById('import').value==='');
}

(async()=>{
  const browser=await chromium.launch({headless:true,channel:process.env.OURNOTES_BROWSER_CHANNEL||(process.platform==='win32'?'msedge':undefined)});
  try{
    const context=await browser.newContext();
    await context.route('**/*',route=>new URL(route.request().url()).origin===new URL(BASE).origin?route.continue():route.abort());
    const page=await context.newPage();
    await page.goto(BASE);
    await page.waitForFunction(()=>document.getElementById('ownedCount').textContent==='0 + 0'||!document.getElementById('loadError').hidden,null,{timeout:120000});
    if(await page.locator('#loadError').isVisible())throw new Error(await page.locator('#loadError').textContent());
    const initial=await page.evaluate(()=>window.EventHost.archives.profiles.length);
    const raw={accountid:'synthetic-private-id',playerData:{memberCards:[
      {masterId:'27',exp:123,liveSkillLevel:3},{masterId:'28'},{masterId:'27'},{masterId:'900001'}
    ],supportCards:[{masterId:'33',cardRank:4}]},iapAppleAccountBinding:'synthetic-private-binding'};
    await importJson(page,raw);
    await page.waitForFunction(()=>document.getElementById('ownedCount').textContent==='2 + 1');
    const result=await page.evaluate(()=>({state:window.EventHost.state,archives:window.EventHost.archives,
      saved:Object.values(localStorage).join('\n')}));
    assert.equal(result.archives.profiles.length,initial+1);
    assert.deepEqual(result.state.profile.inventory.members.map(x=>x.id),[27,28]);
    assert.deepEqual(result.state.profile.inventory.snaps.map(x=>x.id),[33]);
    assert.deepEqual(result.state.candidate_member_ids,[27,28]);
    assert.deepEqual(result.state.candidate_snap_ids,[33]);
    assert.equal(result.state.profile.inventory.members[0].level,null);
    assert.equal(result.state.profile.inventory.members[0].live_skill_level,null);
    assert.ok((await page.locator('#message').textContent()).includes('当前图鉴未收录 1 张'));
    assert.ok((await page.locator('#message').textContent()).includes('重复卡牌 1 张'));
    assert.ok(!JSON.stringify(result.archives).includes('synthetic-private'));
    assert.ok(!result.saved.includes('synthetic-private'));
    await importJson(page,{playerData:{memberCards:{masterId:'27'}}});
    assert.ok((await page.locator('#message').textContent()).includes('格式不正确'));
    assert.equal(await page.evaluate(()=>window.EventHost.archives.profiles.length),initial+1);
    await importJson(page,{playerData:{memberCards:[{masterId:'900001'}]}});
    assert.ok((await page.locator('#message').textContent()).includes('没有当前图鉴可识别的卡牌'));
    assert.equal(await page.evaluate(()=>window.EventHost.archives.profiles.length),initial+1);
    await importJson(page,{player_data:{member_cards:[{master_id:'30'}],support_cards:[{master_id:'37'}]}});
    await page.waitForFunction(()=>document.getElementById('ownedCount').textContent==='1 + 1');
    assert.equal(await page.evaluate(()=>window.EventHost.archives.profiles.length),initial+2);
    await page.setViewportSize({width:390,height:850});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    console.log('Sirius import: ownership, privacy, validation, snake_case passed');
    await context.close();
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
