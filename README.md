# Our Notes 活动配队与拉表模拟器

基于 [ournotes-team-planner-web](https://github.com/doublequiet-on/ournotes-team-planner-web) 的本地网页版。目标是先从玩家自己的卡库寻找活动队伍，再估算普通、挑战演出的收益并生成活动进度表。

## 已实现

- **活动配队**：录入已拥有的成员卡、留影与实际养成；不指定歌曲时按活动 PT 加成寻找当前候选池的队伍，同加成再比较综合潜力。可改选综合潜力、活动徽章加成等目标，设置必带卡、队长和留影绑定。
- **卡组档案**：多个档案分别保存实际养成与升级规划。浏览器本地自动保存，支持 JSON 导入、单档案导出和全部备份。计算结果按档案缓存。
- **Sirius 持有卡导入（实验）**：可导入 Sirius API Proxy 私有玩家数据接口导出的 JSON，只提取当前图鉴可识别的成员卡与留影编号，养成仍需手动填写。用法与测试范围见 [Sirius 导入说明](guides/SIRIUS-IMPORT.md)。
- **歌曲验证**：选推荐队伍估算指定歌曲的理论 AP 分数、评级和活动收益；普通跳过固定按 C 评级奖励结算，页面上的跳过模型分数仅供参考，不计最高分。也可从当前已勾选卡池搜索该谱面的最高单场活动 PT、活动徽章或理论 AP 分数。AP 比较 120 种技能发动顺序的最低估算分数，搜索完成后才显示最优结论。
- **活动拉表**：将模拟收益填入普通／挑战每局数据，也可改填游戏实测；按目标 PT、可选的目标活动徽章、当前 CP 与每日上限生成剩余场次和 CSV。

活动优先配队不要求选择歌曲。它的排序目标是**活动 PT 加成**：普通跳过固定 C 时，同 Boost 下可直接比较每局 PT；手打和挑战演出的实际收益还取决于歌曲评级与 Boost／CP 消耗，指定歌曲后应选择“每局活动 PT 最高”搜索。挑战门票凹榜分则选择“单曲理论分数最高”。公式和验证范围见 [活动计算验证](guides/EVENT-VALIDATION.md)，常见配队说法的实验见 [玩家说法验证](guides/CLAIM-EXPERIMENTS.md)。

## 数据范围

当前基准为 **2026-10-01 日服快照、活动 #1**，并已补入 10 月 3 日 Master 数据中的成员卡 #64「马桥心玖 Happy Birthday 26-27」及其队长技能。可对照 [haneoka 活动页](https://haneoka.org/intl/zh-CN/events/1/) 的活动加成和奖励。其余活动、歌曲和卡牌仍以原快照为准，数据不会自动更新。计算假设 AP/PERFECT、正生命值，辅助与撃奏关闭。普通演出不计活动参数加成，挑战演出计入。模型分数是估算，实际活动收益可用游戏结算校正。

## 本地运行

需要 Node.js 22+ 和 Python 3.11+。在项目目录执行：

```sh
cd browser
npx pnpm@11.19.0 install --frozen-lockfile
npx pnpm@11.19.0 build
python3 -B tests/preview_server.py
```

然后打开 [本机预览](http://127.0.0.1:8877/ournotes-planner/)。首次打开需要下载浏览器计算组件，建议使用近期 Chrome 或 Edge。构建产物在 `browser/dist/`。个人卡库和计算均留在浏览器本地；换设备或清理网站数据前请导出全部档案。

## Vercel 部署

仓库根目录的 `vercel.json` 安装锁定的浏览器依赖，运行 Python/Vite 构建，并发布 `browser/dist/`。跨源隔离响应头让浏览器直接使用 SharedArrayBuffer 运行本地 WASM 求解器；无需计算后台或数据库。导入 GitHub 仓库时将 Root Directory 留在仓库根目录。推送 `main` 后，已连接的 Vercel 项目会自动构建发布。首次访问生产网址时，仍应实际检查卡库录入、计算和导出。

原项目的许可证与第三方来源见 [LICENSE](LICENSE)、[THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt) 和 [数据来源](guides/DATA.md)。本项目未获得游戏官方授权。
