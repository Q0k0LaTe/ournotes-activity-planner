# 配队工作台浏览器适配 · v0.3.3

本版将活动 #2 的五张 SR 默认目标改为 525,000 PT，并在网页显示挑战奖励分档；国际服留影 #70「Abracadabra」继续保留。参阅 [仓库 README](../README.md)、[开发说明](../guides/DEVELOPMENT.md) 和 [验证说明](../guides/VALIDATION.md)。

在此目录运行 `npx pnpm@11.19.0 install --frozen-lockfile`、`npx pnpm@11.19.0 build`，然后用 `python -B tests/preview_server.py` 本地预览。

`upstream/` 为校验过的公开核心 v0.2.5 基准 ZIP。界面源文件位于 `../workbench/web/`；此目录的 index.html、generated-app.js、style.css、public/、dist/ 都由构建生成。Python 与 OR-Tools WASM 自托管，无计算后台；私人输入不得加入构建目录。
