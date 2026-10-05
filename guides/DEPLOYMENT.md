# GitHub 与 Vercel 发布、更新与回退

本仓库通过根目录的 `vercel.json` 从源码构建静态网站，输出目录为 `browser/dist/`。个人卡库和求解均在用户浏览器本地；Vercel 只托管静态文件，不需要计算 API 或数据库。

## 首次部署

1. 将源码推送到自己的 GitHub 仓库。不要提交 `work/`、`workbench/runtime/`、`browser/public/`、`browser/dist/` 或个人卡库；这些路径已在 `.gitignore` 中排除。
2. 在 Vercel 中导入该 GitHub 仓库，Root Directory 保持仓库根目录。保留 `vercel.json` 中的安装命令、构建命令、输出目录和跨源隔离响应头。
3. 发布后在正式 HTTPS 地址打开页面，检查是否完成浏览器计算组件初始化，并用合成测试卡库实际执行一次计算和导出。HTTP 200 本身不能证明求解器可用。

构建需要 Node.js 22+ 与 Python 3。Vercel 的构建环境运行 `browser/build_browser.py --build`，从锁定的公开基准和修正源码生成页面；浏览器运行所需的 Python、OR-Tools WASM 与卡图均随静态站点一起发布。

## 更新

先运行 [开发与验证步骤](DEVELOPMENT.md)，确认 `python -B tools/check_build.py`、`python -B tools/verify_release.py --site browser/dist` 和 `python -B tools/run_checks.py` 通过。提交源码并推送 `main` 后，已连接的 Vercel 项目自动构建生产部署。CI 验证与正式站点验收是两项独立检查。

个人卡库按网站来源和路径保存在浏览器。迁移域名或路径前，请先导出全部档案；新来源不会自动取得旧网站的本地数据。源码或模型变化可能使旧搜索缓存失效，需要重新计算。

## 回退

通过 Git revert 或重新提交已验证的旧版本源码回退，再等待 Vercel 完成新部署。回退后仍须在正式网址检查初始化、计算与导出。

原参考项目的 GitHub Pages 发布方式见 [doublequiet-on/ournotes-team-planner-web](https://github.com/doublequiet-on/ournotes-team-planner-web)。
