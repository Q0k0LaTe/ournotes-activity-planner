const test = require('node:test');
const assert = require('node:assert/strict');
const {plan, reward} = require('../workbench/web/event-math.js');
const event = {id:2};

const base = {
  now:'2026-10-05T12:00:00', endAt:'2026-10-07T23:59:00', current:0,
  target:25000, cpStart:0, normalPt:1000, normalCp:100,
  normalShop:10, normalBoost:4, normalMinutes:3,
  challengePt:5000, challengeCost:200, challengeShop:20,
  challengeMinutes:4, dailyLimit:10,
};

test('finds the minimum normal lives and preserves CP conservation', () => {
  const result = plan(base);
  assert.equal(result.neededNormal, 8);
  assert.equal(result.neededChallenge, 4);
  assert.equal(result.totalPt, 28000);
  assert.equal(result.cpRemaining, 0);
  assert.equal(result.daily.at(-1).cumulative, result.totalPt);
  assert.equal(result.daily.reduce((n, day) => n + day.normal, 0), result.neededNormal);
  assert.equal(result.daily.reduce((n, day) => n + day.challenge, 0), result.neededChallenge);
});

test('uses starting CP and can complete without normal lives', () => {
  const result = plan({...base, target:5000, cpStart:200});
  assert.equal(result.neededNormal, 0);
  assert.equal(result.neededChallenge, 1);
  assert.equal(result.boost, 0);
});

test('reports a daily capacity shortfall and rejects unreachable goals', () => {
  assert.equal(plan({...base, dailyLimit:2}).feasible, false);
  assert.throws(() => plan({...base, normalPt:0, normalCp:0, challengePt:0}), /无法达到目标/);
});

test('rejects costs that cannot occur in event 2', () => {
  assert.throws(() => plan({...base, normalBoost: 1.5}), /普通每局 Boost/);
  assert.throws(() => plan({...base, normalBoost: 11}), /普通每局 Boost/);
  assert.throws(() => plan({...base, challengeCost: 600}), /挑战每局 CP/);
});

test('meets both cumulative PT and event badge targets with conserved CP', () => {
  const result = plan({...base, currentShop:50, shopTarget:115,
    target:5000, cpStart:200, normalShop:10, challengeShop:20});
  assert.equal(result.neededNormal, 3);
  assert.equal(result.neededChallenge, 2);
  assert.equal(result.totalPt, 13000);
  assert.equal(result.totalShop, 120);
  assert.equal(result.daily.at(-1).shop, result.totalShop);
  assert.equal(result.cpRemaining, 100);
});

test('uses exact event reward bases for song-free team planning', () => {
  const bases = {normal:{D:[15,18,3],C:[25,30,4],B:[35,42,5],A:[50,60,6],S:[75,90,8],SS:[100,120,10]},
    challenge:{D:[1500,2150],C:[2000,2650],B:[2750,3400],A:[3500,4150],S:[4500,4900],SS:[5500,5650]}};
  for (const [mode, ranks] of Object.entries(bases)) {
    for (const [rank, [pt, shop, cp]] of Object.entries(ranks)) {
      for (const consumed of mode === 'normal' ? [1,4,10] : [200,400,800,1600]) {
        const factor = mode === 'normal' ? consumed * 5 : consumed / 200;
        const actual = reward(event, mode, rank, consumed, {event_pt:10800,shop_pt:14000});
        assert.deepEqual(actual, {event_pt:Math.floor(pt*factor*20800/10000),
          shop_pt:Math.floor(shop*factor*24000/10000), cp:mode === 'normal' ? cp*factor : 0});
      }
    }
  }
  assert.deepEqual(reward(event,'normal','C',4,{event_pt:7000,shop_pt:9000}),
    {event_pt:850,shop_pt:1140,cp:80});
  assert.throws(() => reward(event,'challenge','B',600,{event_pt:0,shop_pt:0}), /消耗档位/);
});

test('requires explicit per-live gains before building a schedule', () => {
  assert.throws(() => plan({...base, normalPt:'',normalCp:'',challengePt:''}), /每局收益/);
});
