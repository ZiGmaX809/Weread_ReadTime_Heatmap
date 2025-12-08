# 微信阅读热力图自动化生成工具

使用 GitHub Actions 自动获取您的微信读书数据，生成阅读时长热力图。

## 功能特点

- 🔥 **完全自动化**：每天自动更新，无需手动干预
- 🍪 **稳定认证**：使用 Cookie 认证方式，比抓包更稳定
- 📊 **美观图表**：生成 SVG 格式的热力图，支持自定义颜色
- ⚙️ **灵活配置**：支持自定义年份、颜色、标题等
- 🚀 **零部署**：直接在 GitHub Actions 中运行

## 快速开始

### 1. 获取微信读书 Cookie

#### 方法一：浏览器开发者工具（推荐）

1. 在 Chrome 浏览器中打开 [微信读书网页版](https://weread.qq.com)
2. 登录您的账号
3. 按 `F12` 打开开发者工具
4. 切换到 **Network**（网络）标签页
5. 刷新页面或点击任意一本书
6. 在请求列表中找到任一发送到 `i.weread.qq.com` 的请求
7. 点击该请求，在右侧找到 **Request Headers**
8. 复制完整的 `Cookie` 值

Cookie 格式示例：
```
wr_name=yourname; wr_vid=123456789; wr_skey=abcdef123456; wr_gid=123; wr_umid=abcdef; wr_rt=1234567890; wr_aid=xxx; wr_expires=1234567890
```

#### 方法二：使用浏览器插件

安装 Cookie 导出插件（如 "Get cookies.txt LOCALLY"），导出 `weread.qq.com` 域名的 Cookie。

### 2. 配置 GitHub 项目

1. **Fork 本项目** 或 **克隆到您的仓库**
2. 进入仓库的 **Settings** -> **Secrets and variables** -> **Actions**
3. 点击 **New repository secret**，添加以下 Secret：
   - **Name**: `WEREAD_COOKIE`
   - **Value**: 粘贴您获取的 Cookie 字符串

### 3. 运行 GitHub Actions

1. 进入仓库的 **Actions** 标签页
2. 选择 "微信阅读热力图自动生成" 工作流
3. 点击 **Run workflow** 手动触发一次
4. 等待运行完成，热力图将自动生成并提交到仓库

## 配置选项（可选）

您可以在仓库的 **Settings** -> **Secrets and variables** -> **Actions** -> **Variables** 中添加以下配置：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `START_YEAR` | 2024 | 热力图开始年份 |
| `END_YEAR` | 2025 | 热力图结束年份 |
| `NAME` | 微信阅读热力图 | 图表标题 |
| `TRACK_COLOR` | #EBEDF0 | 无阅读时间的颜色 |
| `TRACK_SPECIAL1_COLOR` | #9BE9A8 | 0-30分钟颜色 |
| `TRACK_SPECIAL2_COLOR` | #40C463 | 30-60分钟颜色 |
| `TRACK_SPECIAL3_COLOR` | #30A14E | 1-2小时颜色 |
| `TRACK_SPECIAL4_COLOR` | #216E39 | 2小时以上颜色 |

## 文件说明

### 核心文件

- `heatmap_new.py` - 主程序，生成热力图
- `weread_auth.py` - 认证模块，处理 Cookie 认证
- `.github/workflows/weread-heatmap-new.yml` - GitHub Actions 工作流配置

### 输出文件

- `heatmap.svg` - 生成的热力图文件（在仓库根目录）

## 工作原理

1. GitHub Actions 每天自动触发（北京时间 8:00）
2. 从 GitHub Secrets 读取 Cookie
3. 使用 Cookie 访问微信读书 API 获取阅读数据
4. 将数据处理成热力图格式
5. 生成 SVG 文件并自动提交到仓库

## 常见问题

### Q: Cookie 有多久有效期？

A: 微信读书的 Cookie 通常有效期为 1-3 个月。如果发现 Action 失败，需要重新获取 Cookie 并更新。

### Q: 如何更新 Cookie？

A: 重复获取 Cookie 的步骤，然后在 GitHub Secrets 中更新 `WEREAD_COOKIE` 的值。

### Q: Action 运行失败怎么办？

1. 检查 Cookie 格式是否正确
2. 确认 Cookie 未过期
3. 查看 Action 运行日志，了解具体错误信息
4. 尝试手动触发一次 Action

### Q: 可以显示多账号的数据吗？

A: 目前版本仅支持单账号。可以通过修改代码支持多账号数据合并。

## 更新日志

### v2.0.0（新版本）
- ✨ 使用 Cookie 认证替代抓包方案
- ✨ 支持从 GitHub Secrets 直接读取 Cookie
- ✨ 完全自动化，无需 Quantumult X
- ✨ 更稳定的认证方式
- ✨ 简化配置流程

### v1.0.0（原版本）
- 依赖 Quantumult X 抓包
- 使用 GitHub Gist 存储认证信息
- 需要复杂的网络配置

## 迁移指南

如果您正在使用旧版本，请参考 [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) 进行迁移。

## 安全提醒

- Cookie 包含您的登录凭证，请勿泄露给他人
- 使用私有仓库可以更好地保护您的数据
- 定期更新 Cookie 以确保安全

## 技术支持

如果遇到问题，请：
1. 查看最近的 Action 运行日志
2. 确认配置是否正确
3. 搜索已有的 Issues
4. 创建新的 Issue 并提供详细错误信息

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](./LICENSE) 文件。

---

**享受阅读，让数据见证您的成长！** 📚✨