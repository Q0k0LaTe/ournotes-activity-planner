# 数据、模型与许可证

本项目的养成与技能基准固定为公开源码 v0.2.5，应用仓库 `core/` 修正层、`workbench/` 活动配队与单曲模拟模块：

```text
OurNotes-配队程序-v0.2.5.zip
SHA-256: 396a5b670f8e15f7ce3e5582ca9ed114658d40de801f9d7233351027888ca914
基础归档: 2026-10-01，活动 #1；当前 Master 增量: 2026-10-09
当前活动 ID: 2；活动 #1 基础奖励保留为历史记录
成员卡: 67；Snap: 68
歌曲: 87（转换谱面 348）；活动配队不指定歌曲，歌曲模拟使用这些谱面
```

基础 ZIP 位于 `browser/upstream/`，不改动其原始字节。构建先验证基础 SHA-256，再叠加 `data_updates/2026-10-09/` 中固定哈希的 Master 表、卡图与谱面。71 份运行 Master 表逐字节对应本次固定来源提交；旧活动的 `normalized/event_1.json` 仍保留。优化层的八个源码文件及其 SHA-256 另记录在 `build-info.json` 的 `core_overrides` 中；运行包必须逐字节匹配这些文件。公开包不含原玩家卡库、私人养成观察、截图结算或 SQLite；初始化时使用空白个人卡库。测试生成器只使用合成养成。

## 来源

| 内容 | 公开来源与固定版本 |
| --- | --- |
| Master 数据 | [StarMoe-org/moenotes-masterdata](https://github.com/StarMoe-org/moenotes-masterdata)，当前 `29b2365a5ed294b4a517a9109c3cfa5ca89125f1`；基础归档 `0f8644dd85b7c3d21794fb3f718e48773cd1cc60`。变化表、未变化表和卡图哈希见 `data_updates/2026-10-09/manifest.json` |
| 活动与新卡 | 同一 Master 提交中的活动 #2、成员 #65–#67、留影 #65–#68；成员 #64 仍保留 10 月 3 日已存卡图。活动基础奖励由 Master 分组生成 `event_2.json` |
| 养成字段参考 | [StarMoe-org/moenotes](https://github.com/StarMoe-org/moenotes)，`bb43324feff14e1295f5e798eb3948e60535aa21` |
| 综合力、收益、跳过与 AP 计算参考 | [empty-sekai/ournotes-deck](https://github.com/empty-sekai/ournotes-deck)，`dbd9cf01a4854808dceb6aedcd4041af372faeee` |
| 谱面转换参考 | [MetaSekaiLab/nnnotes](https://github.com/MetaSekaiLab/nnnotes)，`b1e12c4ab31cfed6cd453e562aeeb66c3821af83` |
| 谱面与卡图公共地址 | [bdon / Moenotes](https://bdon.moe/)，实际字节哈希保留在公开源清单 |

综合力、活动加成、技能、歌曲得分与结算估算沿用固定模型。默认无歌曲活动配队先按活动 PT 加成排序；单曲搜索可按理论 AP 的保守评级比较每局活动 PT、徽章或最低分。普通跳过固定按 C 评级奖励结算，跳过参考分数不参与奖励或最高分；挑战演出不能跳过。活动拉表用每局模型值或玩家实测值计算。新活动 #2 的基础奖励、加成与谱面均已接入；尚无本轮实机结算，收益仅为客户端参考模型估算。旧活动 #1 的实机截图验证不自动适用于活动 #2。公式、旧实验与不确定范围见 [活动计算验证](EVENT-VALIDATION.md)。来源清单位于基础归档 `research/2026-10-01/`、本次增量和 `licenses/source_manifest.json`。静态网站的 `build-info.json` 记录模型、浏览器版本和运行数据哈希。

v0.2.5 按游戏帮助修正本项目调用上下文：普通演出关闭成员与 Snap 的活动参数加成，挑战开启；PT 加成保持独立。详见 [模式修复说明](POWER-MODES.md) 与 [基准差异](../model-fixes/0.2.5-power-modes.patch)。计算参考源码未更换，Master 原始表按本次固定提交更新。

当前覆盖活动 #2、普通／挑战单人、撃奏关闭。无歌曲潜力指标假设 AP/PERFECT、正生命值、每名成员发动一次且均匀覆盖，不包含顺序与截断；具体歌曲评分按已转换谱面与 120 种技能顺序估算。新谱面 #100111 与 #100112 的 8 个难度由固定 `nnnotes` 转换器生成，并以原始资产及转换结果哈希核验。历史截图校准不能代替新版游戏实测。数据不会自动更新。活动规则可对照 [haneoka 活动 #2 页面](https://haneoka.org/intl/zh-CN/events/2/)。

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
