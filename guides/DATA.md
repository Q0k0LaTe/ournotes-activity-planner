# 数据、模型与许可证

本项目的养成与技能基准固定为公开源码 v0.2.5，应用仓库 `core/` 修正层、`workbench/` 活动配队与单曲模拟模块：

```text
OurNotes-配队程序-v0.2.5.zip
SHA-256: 396a5b670f8e15f7ce3e5582ca9ed114658d40de801f9d7233351027888ca914
基础归档: 2026-10-01，活动 #1；Master 增量: 2026-10-09、2026-10-18
当前活动 ID: 3；活动 #1、#2 基础奖励保留为历史记录
成员卡: 70；Snap: 73（含国际服 #70）
歌曲: 89（转换谱面 356）
```

基础 ZIP 位于 `browser/upstream/`，不改动其原始字节。构建先验证基础 SHA-256，再叠加 `data_updates/2026-10-09/` 和 `data_updates/2026-10-18/` 的固定哈希日服 Master 表、卡图与谱面，最后补入 `data_updates/2026-10-11/` 的国际服留影 #70。活动 #1、#2 的规范化奖励表保留，当前计算使用活动 #3。固定模型的源码覆盖哈希仍记录在 `build-info.json` 的 `core_overrides` 中。公开包不含原玩家卡库、私人养成观察、截图结算或 SQLite；初始化时使用空白个人卡库。测试生成器只使用合成养成。

## 来源

| 内容 | 公开来源与固定版本 |
| --- | --- |
| Master 数据 | [StarMoe-org/moenotes-masterdata](https://github.com/StarMoe-org/moenotes-masterdata/commit/afe0f81f9fde53512febd37c5ec7702c766aee48) 日服提交 `afe0f81f9fde53512febd37c5ec7702c766aee48`。网站使用的 71 张表中 25 张变化、46 张未变，字节与 Git blob 哈希见 `data_updates/2026-10-18/manifest.json`。基础归档提交为 `0f8644dd85b7c3d21794fb3f718e48773cd1cc60`。 |
| 活动与新卡 | 同一 Master 提交中的活动 #3、成员 #68–#70、留影 #69/#71–#73；活动基础奖励由原始表分组生成 `event_3.json`。国际服 #70 仍按固定 [国际服提交](https://github.com/StarMoe-org/moenotes-masterdata/tree/dfcb4787b7c376a321838336babe59af69b66e39/en) 的行与图覆盖。 |
| 卡图与谱面 | 新增缩略图及两首歌的 8 张原始谱面取自 [haneoka 日服静态素材](https://haneoka.org/jp/ja/)，下载地址、原图和转换结果哈希见本次清单。PNG 缩略图用 `cwebp -q 90 -m 6` 生成站点 WebP；转换谱面使用固定 [nnnotes](https://github.com/MetaSekaiLab/nnnotes/tree/b1e12c4ab31cfed6cd453e562aeeb66c3821af83) 的 `deckdata.chart_record`。 |
| 养成字段参考 | [StarMoe-org/moenotes](https://github.com/StarMoe-org/moenotes)，`bb43324feff14e1295f5e798eb3948e60535aa21` |
| 综合力、收益、跳过与 AP 计算参考 | [empty-sekai/ournotes-deck](https://github.com/empty-sekai/ournotes-deck)，`dbd9cf01a4854808dceb6aedcd4041af372faeee` |

综合力、活动加成、技能、歌曲得分与结算估算沿用固定模型。默认无歌曲活动配队先按活动 PT 加成排序；单曲搜索可按理论 AP 的保守评级比较每局活动 PT、徽章或最低分。普通跳过固定按 C 评级奖励结算，跳过参考分数不参与奖励或最高分；挑战演出不能跳过。活动拉表用每局模型值或玩家实测值计算。活动 #3 的五张 SR 奖励门槛为 75,000／125,000／200,000／300,000／525,000 PT；挑战 200 CP 的 B／A／S／SS 活动 PT 基础值为 2,750／3,500／4,500／5,500。旧活动的实机截图验证不自动适用于活动 #3，收益仍是客户端参考模型估算。公式、旧实验与不确定范围见 [活动计算验证](EVENT-VALIDATION.md)。静态网站的 `build-info.json` 记录模型、浏览器版本和运行数据哈希。

当前覆盖活动 #3、普通／挑战单人、撃奏关闭。无歌曲潜力指标假设 AP/PERFECT、正生命值、每名成员发动一次且均匀覆盖，不包含顺序与截断；具体歌曲评分按已转换谱面与 120 种技能顺序估算。数据不会自动更新。

## 更新固定基准

1. 先核对新活动或机制的数据、公式和来源，展开现有基准阅读调用路径。
2. 在 `data_updates/<日期>/` 固定来源提交、原表或增量、卡图和谱面哈希；保留旧活动归档，不覆盖已验证的历史记录。
3. 在构建层对新数据逐字节核验，生成对应 `normalized/event_<ID>.json` 和转换谱面；更新活动编号、界面和来源说明。
4. 若模型版本本身改变，另建固定公开基准 ZIP，并更新 `upstream.json` 的实际 SHA-256；界面匹配失败必须修正，不能删除检查以强行通过。
5. 重新生成原生基准，运行浏览器结果、整数精度、续算与多标签页验收；比较活动收益和单曲模拟结果。
6. 更新版本、文档和站点构建，保留可回退的旧版本。

本地版本或公共源发生更新不会自动进入网页。不要将新数据替换到已验证的旧公式后直接宣布支持新活动。

## 许可证

本项目新增源码与文档采用根目录 MIT 许可证。原模型保留 MIT/Apache-2.0 文本，nnnotes 参考转换源码保留 MIT。Pyodide、CPython、Emscripten、OR-Tools WASM、Protobuf 和 Long 的许可证随构建发布，位于网站 `licenses/`；新增运行许可证源位于 `browser/license-source/`。

moenotes 养成参考快照没有根许可证文件，本项目没有为其声明许可授予。游戏数据、卡图和谱面的权利归各权利人；本项目代码许可证不授予这些素材的版权。完整记录见根目录和网站的 `THIRD-PARTY-NOTICES.txt`。再次分发时保留相应说明与许可证。
