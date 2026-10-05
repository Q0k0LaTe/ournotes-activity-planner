/* Integer activity planning. This file is also loaded by the browser build. */
(function (root) {
  'use strict';
  function integer(value, label, min = 0) {
    const n = Number(value);
    if (!Number.isSafeInteger(n) || n < min) throw new Error(label + '需填写不小于 ' + min + ' 的整数。');
    return n;
  }
  function positive(value, label) {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) throw new Error(label + '需填写大于 0 的数字。');
    return n;
  }
  function plan(raw) {
    const current = integer(raw.current, '当前活动 PT');
    const target = integer(raw.target, '目标活动 PT');
    const currentShop = integer(raw.currentShop || 0, '当前活动徽章');
    const shopTarget = raw.shopTarget === '' || raw.shopTarget == null ? null : integer(raw.shopTarget, '目标活动徽章');
    const cpStart = integer(raw.cpStart, '当前 CP');
    const normalPt = integer(raw.normalPt, '普通每局 PT');
    const normalCp = integer(raw.normalCp, '普通每局 CP');
    const normalShop = integer(raw.normalShop || 0, '普通每局活动徽章');
    const normalBoost = integer(raw.normalBoost, '普通每局 Boost', 1);
    if (normalBoost > 10) throw new Error('普通每局 Boost 只能选择 1～10。');
    const normalMinutes = positive(raw.normalMinutes, '普通每局耗时');
    const challengePt = integer(raw.challengePt, '挑战每局 PT');
    const challengeCost = integer(raw.challengeCost, '挑战每局 CP', 1);
    if (![200, 400, 800, 1600].includes(challengeCost))
      throw new Error('挑战每局 CP 只能选择 200、400、800、1600。');
    const challengeShop = integer(raw.challengeShop || 0, '挑战每局活动徽章');
    const challengeMinutes = positive(raw.challengeMinutes, '挑战每局耗时');
    const dailyLimit = raw.dailyLimit === '' || raw.dailyLimit == null ? null : integer(raw.dailyLimit, '每日普通场数上限', 1);
    const end = new Date(raw.endAt);
    const now = raw.now ? new Date(raw.now) : new Date();
    if (!Number.isFinite(end.getTime()) || !Number.isFinite(now.getTime()) || end <= now)
      throw new Error('活动结束时间需晚于当前时间。');
    const days = [];
    let day = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const finalDay = new Date(end.getFullYear(), end.getMonth(), end.getDate());
    while (day <= finalDay && days.length < 366) {
      days.push(`${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`);
      day = new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1);
    }
    if (!days.length || days.length >= 366) throw new Error('请设置一年内的活动结束时间。');
    const challengeCount = n => Math.floor((cpStart + n * normalCp) / challengeCost);
    const points = n => current + n * normalPt + challengeCount(n) * challengePt;
    const badges = n => currentShop + n * normalShop + challengeCount(n) * challengeShop;
    const met = n => points(n) >= target && (shopTarget === null || badges(n) >= shopTarget);
    if (points(0) < target && normalPt === 0 && (normalCp === 0 || challengePt === 0))
      throw new Error('当前每局收益无法达到目标，请填写实测收益或重新模拟。');
    if (shopTarget !== null && badges(0) < shopTarget && normalShop === 0 && (normalCp === 0 || challengeShop === 0))
      throw new Error('当前每局活动徽章收益无法达到目标，请填写实测收益或重新模拟。');
    let low = 0, high = 1;
    while (!met(high)) {
      high *= 2;
      if (!Number.isSafeInteger(high) || high > 1e9) throw new Error('目标过高，超出可计算范围。');
    }
    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (met(mid)) high = mid; else low = mid + 1;
    }
    const neededNormal = low;
    // Only spend CP needed to meet the target. Unused CP remains visible.
    const availableChallenge = challengeCount(neededNormal);
    const neededForPt = challengePt > 0 ? Math.max(0, Math.ceil((target - current - neededNormal * normalPt) / challengePt)) : 0;
    const neededForBadges = shopTarget !== null && challengeShop > 0
      ? Math.max(0, Math.ceil((shopTarget - currentShop - neededNormal * normalShop) / challengeShop)) : 0;
    const neededChallenge = Math.min(availableChallenge, Math.max(neededForPt, neededForBadges));
    const totalPt = current + neededNormal * normalPt + neededChallenge * challengePt;
    const totalShop = currentShop + neededNormal * normalShop + neededChallenge * challengeShop;
    const cpRemaining = cpStart + neededNormal * normalCp - neededChallenge * challengeCost;
    const daily = [];
    let remainingNormal = neededNormal, remainingChallenge = neededChallenge;
    let cp = cpStart, cumulative = current, shop = currentShop;
    days.forEach((date, index) => {
      const normal = Math.ceil(remainingNormal / (days.length - index));
      remainingNormal -= normal;
      cp += normal * normalCp;
      // Spend enough CP each day to keep the target on pace, retaining spare CP.
      const challenge = Math.min(remainingChallenge, Math.floor(cp / challengeCost));
      remainingChallenge -= challenge;
      cp -= challenge * challengeCost;
      cumulative += normal * normalPt + challenge * challengePt;
      shop += normal * normalShop + challenge * challengeShop;
      daily.push({date, normal, challenge, cumulative, shop, cp,
        boost: normal * normalBoost,
        minutes: normal * normalMinutes + challenge * challengeMinutes});
    });
    return {neededNormal, neededChallenge, totalPt, totalShop, cpRemaining,
      boost: neededNormal * normalBoost,
      minutes: neededNormal * normalMinutes + neededChallenge * challengeMinutes,
      daily, dailyLimit, feasible: dailyLimit == null || daily.every(row => row.normal <= dailyLimit)};
  }
  root.EventMath = {plan};
  if (typeof module !== 'undefined' && module.exports) module.exports = {plan};
})(typeof globalThis !== 'undefined' ? globalThis : this);
