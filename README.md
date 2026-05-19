# 微信阅读热力图

通过 Agent API Gateway 获取微信读书每日阅读时长，自动生成 GitHub 贡献图风格的 SVG 热力图。

## 功能特点

- **API Key 认证** — 使用 Bearer Token，比 Cookie 更稳定持久
- **GitHub Actions 自动化** — 每日自动更新，无需手动干预
- **本地 CLI** — 支持本地运行，灵活控制参数
- **逐年日粒度数据** — 通过 `/readdata/detail` 接口获取每日阅读时长
- **模块化设计** — 可被其他脚本、Skill/Agent 调用

## 快速开始

### 1. 获取 API Key

1. 联系微信读书 Agent API 服务获取 `WEREAD_API_KEY`（格式 `wrk-xxxxxxxx`）
2. 设置环境变量：
   ```bash
   export WEREAD_API_KEY=wrk-xxxxxxxx
   ```

### 2. 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 生成热力图
python heatmap.py

# 指定年份范围 + 统计输出
python heatmap.py --start 2023 --end 2025 --stats

# 自定义输出 + 导出原始数据
python heatmap.py --output reading.svg --json reading.json
```

### 3. GitHub Actions 配置

1. Fork 或克隆本项目到你的仓库
2. 进入 **Settings → Secrets and variables → Actions**
3. 添加 **Repository secret**：
   - **Name**: `WEREAD_API_KEY`
   - **Value**: `wrk-xxxxxxxx`
4. Actions 将每天 UTC 0:00 自动运行，也可在 Actions 页面手动触发

## 配置选项

### CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--start` | 去年 | 起始年份 |
| `--end` | 今年 | 结束年份 |
| `--output` | `heatmap.svg` | SVG 输出路径 |
| `--json` | 无 | 同时导出原始数据到 JSON |
| `--stats` | false | 打印阅读统计摘要 |

### 环境变量 / GitHub Variables

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEREAD_API_KEY` | - | **必填**，API Key |
| `START_YEAR` | 去年 | 起始年份 |
| `END_YEAR` | 今年 | 结束年份 |
| `NAME` | 微信阅读热力图 | 图表标题 |
| `TRACK_COLOR` | `#EBEDF0` | 无阅读 |
| `TRACK_SPECIAL1_COLOR` | `#9BE9A8` | 0–30 分钟 |
| `TRACK_SPECIAL2_COLOR` | `#40C463` | 30–60 分钟 |
| `TRACK_SPECIAL3_COLOR` | `#30A14E` | 1–2 小时 |
| `TRACK_SPECIAL4_COLOR` | `#216E39` | 2 小时以上 |

## GitHub Actions

### 自动运行

工作流每天 **UTC 0:00（北京时间 8:00）** 自动触发，生成热力图并提交到仓库。

### 手动触发

1. 进入仓库 **Actions** 标签页
2. 左侧选择 **微信阅读热力图自动生成**
3. 点击 **Run workflow** 下拉按钮
4. 可选填入 `start_year` / `end_year`（留空使用默认值）
5. 点击绿色 **Run workflow** 按钮

### 手动触发（gh CLI）

```bash
# 使用默认年份
gh workflow run weread-heatmap.yml

# 指定年份范围
gh workflow run weread-heatmap.yml -f start_year=2023 -f end_year=2025

# 查看最近运行状态
gh run list --workflow=weread-heatmap.yml --limit=5

# 查看某次运行的日志
gh run view <run-id> --log
```

### 运行结果

- 成功：`heatmap.svg` 自动提交到仓库根目录
- 失败：查看运行日志，常见原因：API Key 未配置或已失效

## 模块调用

```python
from weread_auth import WeReadAuth
from heatmap import fetch_reading_data, Poster

auth = WeReadAuth()
auth.init_auth()

# 获取阅读数据 → {date_str: seconds}
daily_data = fetch_reading_data(auth, start_year=2024, end_year=2025)

# 生成 SVG
poster = Poster(start_year=2024, end_year=2025)
poster.load_reading_data(daily_data)
poster.generate_svg()

# 查看统计
stats = poster.get_statistics()
print(f"阅读 {stats['reading_days']} 天, {stats['total_hours']}小时{stats['total_minutes']}分钟")
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `heatmap.py` | 主程序，数据获取 + SVG 生成 + CLI |
| `weread_auth.py` | 认证模块，Agent API Gateway 调用 |
| `.github/workflows/weread-heatmap.yml` | GitHub Actions 工作流 |
| `weread-skills/heatmap.md` | Skill 定义，供 Harness/Agent 调用 |
| `heatmap.svg` | 生成的热力图输出 |

## 工作原理

1. 通过 Agent API Gateway（`POST /api/agent/gateway`）调用 `/readdata/detail`
2. 逐年请求 `mode=annually`，提取 `dailyReadTimes` 获取日粒度阅读时长
3. 将每日秒数映射到 5 级颜色，生成 GitHub 风格 SVG 热力图
4. GitHub Actions 每日自动更新并提交到仓库

## FAQ

### API Key 有过期时间吗？

API Key 长期有效，无需像 Cookie 一样定期更换。

### 可以显示多账号数据吗？

目前仅支持单账号。如需多账号，可通过多次调用合并数据。

### Action 运行失败怎么办？

1. 检查 `WEREAD_API_KEY` Secret 是否正确配置
2. 查看 Action 运行日志了解错误详情
3. 尝试本地运行 `python heatmap.py` 排查问题

## 许可证

MIT
