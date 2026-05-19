---
name: weread-heatmap
description: 微信阅读热力图生成 — 通过 Agent API Gateway 获取阅读数据并生成 GitHub 风格 SVG 热力图
version: 1.0.0
---

# 微信阅读热力图生成

通过 Agent API Gateway 获取微信读书每日阅读时长，生成 GitHub 贡献图风格的 SVG 热力图。

## 调用方式

### 1. CLI（本地 / CI 均可）

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API Key
export WEREAD_API_KEY=wrk-xxxxxxxx

# 默认年份（去年至今）
python heatmap.py

# 指定年份范围
python heatmap.py --start 2023 --end 2025

# 自定义输出路径 + JSON 数据导出
python heatmap.py --output reading.svg --json reading.json --stats
```

### 2. Python 模块调用

```python
from weread_auth import WeReadAuth
from heatmap import fetch_reading_data, Poster

# 认证（从环境变量 WEREAD_API_KEY 读取）
auth = WeReadAuth()
auth.init_auth()

# 获取数据：返回 {date_str: reading_seconds}
daily_data = fetch_reading_data(auth, start_year=2024, end_year=2025)

# 生成 SVG
poster = Poster(start_year=2024, end_year=2025)
poster.load_reading_data(daily_data)
poster.generate_svg()
```

### 3. Harness / Agent 调用

```markdown
调用 weread-heatmap skill:
- skill: weread-heatmap
- args: --start 2024 --end 2025 --output heatmap.svg
```

## CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--start` | 去年 | 起始年份 |
| `--end` | 今年 | 结束年份 |
| `--output` | `heatmap.svg` | SVG 输出路径 |
| `--json` | 无 | 同时导出原始数据 JSON |
| `--stats` | false | 打印阅读统计摘要 |

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `WEREAD_API_KEY` | 是 | API Key，格式 `wrk-xxxxxxxx` |
| `START_YEAR` | 否 | 起始年份（CLI 参数优先） |
| `END_YEAR` | 否 | 结束年份（CLI 参数优先） |
| `NAME` | 否 | 图表标题，默认"微信阅读热力图" |
| `TRACK_COLOR` | 否 | 无数据格子颜色，默认 `#EBEDF0` |
| `TRACK_SPECIAL1_COLOR` | 否 | 轻度阅读（0-30分钟），默认 `#9BE9A8` |
| `TRACK_SPECIAL2_COLOR` | 否 | 中度阅读（30-60分钟），默认 `#40C463` |
| `TRACK_SPECIAL3_COLOR` | 否 | 重度阅读（1-2小时），默认 `#30A14E` |
| `TRACK_SPECIAL4_COLOR` | 否 | 深度阅读（2小时+），默认 `#216E39` |

## 数据来源

通过 Agent API Gateway（`POST https://i.weread.qq.com/api/agent/gateway`）调用 `/readdata/detail` 接口：

- 逐年调用 `mode=annually`，从 `dailyReadTimes` 提取日粒度数据
- 若某年无 `dailyReadTimes`，回退到 `readTimes`（月粒度）
- 数据单位：秒，热力图按阈值分 5 级着色

## 输出

- **heatmap.svg**：GitHub 风格热力图，一年一行，7列/周，每格代表一天
- **reading.json**（可选）：原始 `{date_str: seconds}` 数据

## 认证

只支持 API Key（Bearer Token）方式：

```bash
export WEREAD_API_KEY=wrk-xxxxxxxx
```

GitHub Actions 中通过 `WEREAD_API_KEY` Secret 配置。
