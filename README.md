# 微信阅读热力图

![heatmap](./heatmap.svg)

通过 Agent API Gateway 获取微信读书每日阅读时长，自动生成 GitHub 贡献图风格的 SVG 热力图。

## 配色预览

`assets/` 目录下提供了多种配色方案的预览：

| 绿色系（默认） | 蓝色系 | 橙色系 | 紫色系 |
|:---:|:---:|:---:|:---:|
| ![green](./assets/216E39.svg) | ![blue](./assets/0077CC.svg) | ![orange](./assets/FFA500.svg) | ![purple](./assets/A74AA8.svg) |

<details>
<summary>查看全部配色方案</summary>

| 颜色 | 预览 | 颜色 | 预览 |
|------|------|------|------|
| `#9BE9A8` | ![](./assets/9BE9A8.svg) | `#216E39` | ![](./assets/216E39.svg) |
| `#40C463` | ![](./assets/40C463.svg) | `#30A14E` | ![](./assets/30A14E.svg) |
| `#0077CC` | ![](./assets/0077CC.svg) | `#34A7FF` | ![](./assets/34A7FF.svg) |
| `#5AB6FD` | ![](./assets/5AB6FD.svg) | `#B5E1FF` | ![](./assets/B5E1FF.svg) |
| `#FFA500` | ![](./assets/FFA500.svg) | `#FFD700` | ![](./assets/FFD700.svg) |
| `#FFEE4A` | ![](./assets/FFEE4A.svg) | `#FFF7B2` | ![](./assets/FFF7B2.svg) |
| `#A74AA8` | ![](./assets/A74AA8.svg) | `#CA5BCC` | ![](./assets/CA5BCC.svg) |
| `#E5A3E6` | ![](./assets/E5A3E6.svg) | `#F7D6F8` | ![](./assets/F7D6F8.svg) |

</details>

## 快速开始

### 1. 获取 API Key

1. 联系微信读书 Agent API 服务获取 `WEREAD_API_KEY`（格式 `wrk-xxxxxxxx`）
2. 设置环境变量：
   ```bash
   export WEREAD_API_KEY=wrk-xxxxxxxx
   ```

### 2. 本地运行

```bash
pip install -r requirements.txt
python heatmap.py
python heatmap.py --start 2023 --end 2025 --stats
```

### 3. GitHub Actions 配置

> **必须设置 Secret，否则 Action 会失败。**

1. Fork 或克隆本项目到你的仓库
2. 进入 **Settings → Secrets and variables → Actions**
3. 点击 **New repository secret**，填写：
   - **Name**：`WEREAD_API_KEY`
   - **Value**：`wrk-xxxxxxxx`
4. 点击 **Add secret** 保存
5. 进入 **Actions** 标签，选择工作流，点击 **Run workflow** 测试

## 配置选项

### CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--start` | 今年 | 起始年份 |
| `--end` | 今年 | 结束年份 |
| `--output` | `heatmap.svg` | SVG 输出路径 |
| `--json` | 无 | 同时导出原始数据到 JSON |
| `--stats` | false | 打印阅读统计摘要 |

### 颜色配置

通过环境变量或 GitHub Variables 自定义所有颜色：

#### 阅读时长格子颜色（5 级梯度）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TRACK_COLOR` | `#EBEDF0` | 无阅读记录的格子 |
| `TRACK_SPECIAL1_COLOR` | `#9BE9A8` | 轻度阅读（0–30 分钟） |
| `TRACK_SPECIAL2_COLOR` | `#40C463` | 中度阅读（30–60 分钟） |
| `TRACK_SPECIAL3_COLOR` | `#30A14E` | 重度阅读（1–2 小时） |
| `TRACK_SPECIAL4_COLOR` | `#216E39` | 深度阅读（2 小时以上） |

#### 文字颜色

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TITLE_COLOR` | `#24292E` | 图表标题颜色 |
| `YEAR_TXT_COLOR` | `#24292E` | 年度总结文字颜色 |
| `MONTH_TXT_COLOR` | `#24292E` | 月份标签颜色 |
| `TEXT_COLOR` | `#24292E` | 通用文本颜色 |
| `DEFAULT_DOM_COLOR` | `#EBEDF0` | 默认格子颜色 |

#### 其他配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `NAME` | 微信阅读热力图 | 图表标题文字 |
| `START_YEAR` | 今年 | 起始年份 |
| `END_YEAR` | 今年 | 结束年份 |

### 配色方案示例

```bash
# 蓝色系
TRACK_SPECIAL1_COLOR=#B5E1FF TRACK_SPECIAL2_COLOR=#5AB6FD \
TRACK_SPECIAL3_COLOR=#34A7FF TRACK_SPECIAL4_COLOR=#0077CC \
python heatmap.py

# 橙黄系
TRACK_SPECIAL1_COLOR=#FFF7B2 TRACK_SPECIAL2_COLOR=#FFEE4A \
TRACK_SPECIAL3_COLOR=#FFD700 TRACK_SPECIAL4_COLOR=#FFA500 \
python heatmap.py

# 紫色系
TRACK_SPECIAL1_COLOR=#F7D6F8 TRACK_SPECIAL2_COLOR=#E5A3E6 \
TRACK_SPECIAL3_COLOR=#CA5BCC TRACK_SPECIAL4_COLOR=#A74AA8 \
python heatmap.py
```

## GitHub Actions

### 自动运行

工作流每天 **UTC 0:00（北京时间 8:00）** 自动触发。

### 手动触发

1. 进入仓库 **Actions** 标签页
2. 选择 **微信阅读热力图自动生成**
3. 点击 **Run workflow**
4. 可选填入 `start_year` / `end_year`，点击 **Run workflow**

### 手动触发（gh CLI）

```bash
gh workflow run weread-heatmap.yml
gh workflow run weread-heatmap.yml -f start_year=2023 -f end_year=2025
gh run list --workflow=weread-heatmap.yml --limit=5
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `heatmap.py` | 主程序，数据获取 + SVG 生成 + CLI |
| `weread_auth.py` | 认证模块，Agent API Gateway |
| `.github/workflows/weread-heatmap.yml` | GitHub Actions 工作流 |
| `weread-skills/heatmap.md` | Skill 定义，供 Agent 调用 |
| `heatmap.svg` | 生成的热力图 |
| `assets/` | 配色预览 SVG |

## 工作原理

1. 通过 Agent API Gateway 逐月调用 `/readdata/detail`（`mode=monthly`）
2. `monthly` 模式的 `readTimes` 按天分桶，获取每日阅读秒数
3. 按阈值映射 5 级颜色，生成 GitHub 风格 SVG 热力图
4. GitHub Actions 每日自动更新并提交到仓库

## FAQ

**API Key 有过期时间吗？** — 长期有效，无需定期更换。

**Action 失败怎么办？** — 检查 Secret 配置，查看运行日志，或本地 `python heatmap.py` 排查。

**年份范围在哪设置？** — 删除 GitHub Variables 中的 `START_YEAR` / `END_YEAR` 即可使用当年默认值。

## 许可证

MIT
