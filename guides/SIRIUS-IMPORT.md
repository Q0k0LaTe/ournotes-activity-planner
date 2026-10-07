# 从 Sirius API Proxy 导入持有卡

这是一个手动导入实验。Sirius API Proxy 的私有 `GET /internal/v1/account/player-data` 接口返回所配置游戏账号的玩家数据；其 `playerData.memberCards` 和 `playerData.supportCards` 列表带有卡牌 `masterId`。目前本站只用这些编号标记持有卡，不读取或保存响应中的账号字段，也不自动同步或推断养成数值。

## 使用

1. 按 [Sirius API Proxy 的说明](https://github.com/Srirus-Project/sirius-api-proxy#quick-start) 在自己的电脑上运行代理，配置你自己的游戏账号。将服务限制在 `127.0.0.1`，设置独立的内部令牌。日服需要已有账号；账号配置见 [上游文档](https://github.com/Srirus-Project/sirius-api-proxy/blob/main/docs/ACCOUNTS.md)。不要把游戏凭据或内部令牌发给本站。
2. 在同一台电脑的终端导出私有数据。此命令使用你已设置的环境变量 `SIRIUS_INTERNAL_TOKEN`：

   ```sh
   curl --fail --silent --show-error \
     -H "Authorization: Bearer ${SIRIUS_INTERNAL_TOKEN:?}" \
     http://127.0.0.1:9999/internal/v1/account/player-data \
     -o sirius-player-data.json
   ```

3. 在本站点击“导入卡库 / Sirius”，选择 `sirius-player-data.json`。导入会建立独立档案并保留原有档案。页面只在内存里读取原始文件，将可识别的卡牌编号保存到浏览器档案；之后可以删除本机的原始导出文件。

如果上游没有配置游戏账号，该接口会返回 `503 account_unavailable`。没有真实账号数据时，无法确认该账号在实服的字段内容与卡牌数量。

## 当前范围

- 上游 Protobuf 定义包含成员卡和留影的 `master_id`，但我们尚未用真实账号响应核对这一导入流程。
- 支持上游 JSON 的 `playerData` / `memberCards` / `supportCards` / `masterId` 字段，以及对应的下划线字段名。重复编号会合并；当前图鉴没有的编号会跳过并提示数量。
- 导入时不写入等级、特训、觉醒、技能等级或突破次数。上游 `exp`、`awakeCount` 和 `cardRank` 与本站阶段的换算尚未实测，直接套用可能产生错误配队。
- 原始玩家数据是私有资料。只在自己的电脑上保存和导入，不要公开分享导出的 JSON。Sirius 是非官方工具；使用前自行核对游戏的[服务条款](https://bang-dream-on.bushimo.jp/rule/)。
