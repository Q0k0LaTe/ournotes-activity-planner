const test = require('node:test');
const assert = require('node:assert/strict');
const {plan} = require('../workbench/web/event-math.js');

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

test('rejects costs that cannot occur in event 1', () => {
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
