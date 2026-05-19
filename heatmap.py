#!/usr/bin/env python3
"""
微信阅读热力图生成工具
通过 Agent API Gateway 获取阅读数据，生成 GitHub 风格 SVG 热力图。

用法:
  python heatmap.py                          # 使用默认年份
  python heatmap.py --start 2023 --end 2025  # 指定年份范围
  python heatmap.py --output reading.svg     # 自定义输出路径
  python heatmap.py --json reading.json      # 输出原始数据 JSON
"""

import argparse
import calendar
import datetime
import json
import os
import sys

import requests
from svgwrite import Drawing

from weread_auth import WeReadAuth

# ---------- 主题配色 ----------

THEMES = {
    "github": {
        "label": "GitHub 绿",
        "levels": ["#EBEDF0", "#9BE9A8", "#40C463", "#30A14E", "#216E39"],
        "text": "#24292E",
        "title": "#24292E",
    },
    "weread": {
        "label": "微信读书蓝",
        "levels": ["#E8F4F8", "#B5E1FF", "#5AB6FD", "#34A7FF", "#0077CC"],
        "text": "#1A3A5C",
        "title": "#0D2B45",
    },
    "warm": {
        "label": "暖阳橙",
        "levels": ["#FFF8E7", "#FFF7B2", "#FFEE4A", "#FFD700", "#FFA500"],
        "text": "#5C3A1A",
        "title": "#3D260D",
    },
    "purple": {
        "label": "梦幻紫",
        "levels": ["#F5F0FA", "#F7D6F8", "#E5A3E6", "#CA5BCC", "#A74AA8"],
        "text": "#3A1A5C",
        "title": "#2A0D45",
    },
    "ocean": {
        "label": "海洋青",
        "levels": ["#E8F8F5", "#A8E6CF", "#55B89D", "#2D8F76", "#1A6B5A"],
        "text": "#1A3A35",
        "title": "#0D2620",
    },
    "rose": {
        "label": "玫瑰粉",
        "levels": ["#FFF0F3", "#FFCCD5", "#FF8FA3", "#FF477E", "#E5256C"],
        "text": "#5C1A35",
        "title": "#3D0D23",
    },
}

DEFAULT_THEME = "github"

# ---------- 常量配置 ----------

NAME = os.getenv("NAME", "微信阅读热力图")

DOM_BOX_TUPLE = (10, 10)
DOM_BOX_PADING = 2
DOM_BOX_RADIUS = 2
YEAR_FONT_SIZE = 14
MONTH_FONT_SIZE = 12
SUMMARY_FONT_SIZE = 12
MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

READING_THRESHOLDS = {
    "light": 1800,   # 30分钟
    "medium": 3600,  # 1小时
    "heavy": 7200,   # 2小时
}


def load_theme(name: str) -> dict:
    """加载主题配色，返回 {levels: [...], text: ..., title: ...}"""
    theme = THEMES.get(name)
    if theme:
        return theme
    # 尝试模糊匹配
    matches = [k for k in THEMES if k.startswith(name.lower())]
    if matches:
        return THEMES[matches[0]]
    print(f"未知主题 '{name}'，可选: {', '.join(THEMES.keys())}")
    return THEMES[DEFAULT_THEME]


# ---------- 辅助类 ----------

class Range:
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def diameter(self):
        return self.upper - self.lower


class Offset:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def tuple(self):
        return (self.x, self.y)


class Poster:
    """海报类，存储绘图所需的数据和配置"""

    def __init__(self, start_year, end_year, theme=None):
        self.tracks = None
        self.years = []
        self.start_year = start_year
        self.end_year = end_year
        self.theme = theme or load_theme(os.getenv("THEME_COLOR", DEFAULT_THEME))
        self.colors = {
            "track": self.theme["levels"][0],
            "special1": self.theme["levels"][1],
            "special2": self.theme["levels"][2],
            "special3": self.theme["levels"][3],
            "special4": self.theme["levels"][4],
            "dom": self.theme["levels"][0],
            "text_color": self.theme["text"],
            "title_color": self.theme["title"],
            "year_txt_color": self.theme["text"],
            "month_txt_color": self.theme["text"],
        }
        self.reading_thresholds = READING_THRESHOLDS
        self.length_range_by_date = None
        self.total_sum_year_dict = {}
        self.output_path = "heatmap.svg"


class Drawer:
    """绘图器，负责生成 SVG 热力图"""

    def __init__(self, poster):
        self.poster = poster
        self.year_style = f"font-size:{YEAR_FONT_SIZE}px; font-family:Arial;"
        self.month_names_style = f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;"
        self.summary_style = (
            f"font-size:{SUMMARY_FONT_SIZE}px; font-family:Arial; font-style:italic;"
        )

    def process_read_times(self, read_times):
        """将 {timestamp: seconds} 转为 {date_str: seconds}"""
        tracks = {}
        for timestamp, duration in read_times.items():
            date = datetime.datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d")
            tracks[date] = duration
        return tracks

    def get_color_by_threshold(self, duration):
        if duration == 0:
            return self.poster.colors["dom"]
        if duration < self.poster.reading_thresholds["light"]:
            return self.poster.colors["special1"]
        if duration < self.poster.reading_thresholds["medium"]:
            return self.poster.colors["special2"]
        if duration < self.poster.reading_thresholds["heavy"]:
            return self.poster.colors["special3"]
        return self.poster.colors["special4"]

    def format_duration(self, seconds):
        if seconds < 60:
            return f"{seconds}秒"
        if seconds < 3600:
            return f"{seconds // 60}分钟"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}小时{minutes}分钟" if minutes else f"{hours}小时"

    def gen_day_box(self, dr, rect_x, rect_y, date_title, day_tracks):
        color = DEFAULT_DOM_COLOR
        if day_tracks:
            color = self.get_color_by_threshold(day_tracks)
            formatted = self.format_duration(day_tracks)
            date_title = f"{date_title} {formatted}"

        rect = dr.rect(
            (rect_x, rect_y),
            DOM_BOX_TUPLE,
            fill=color,
            rx=DOM_BOX_RADIUS,
            ry=DOM_BOX_RADIUS,
        )
        rect.set_desc(title=date_title)
        return rect

    def draw_one_calendar(self, dr, year, offset):
        """绘制单年的日历热力图"""
        initial_y = offset.y

        start_date_weekday, _ = calendar.monthrange(year, 1)
        if start_date_weekday == 6:
            start_date_weekday = 0
        else:
            start_date_weekday += 1

        github_rect_first_day = datetime.date(year, 1, 1)
        github_rect_day = github_rect_first_day + datetime.timedelta(-start_date_weekday)

        year_length = self.poster.total_sum_year_dict.get(year, 0)
        year_duration = self.format_duration(year_length)

        offset.y += DOM_BOX_PADING + YEAR_FONT_SIZE

        size = DOM_BOX_PADING + DOM_BOX_TUPLE[1]
        rect_x = offset.x
        current_month = -1

        # 计算月份标签出现位置
        month_positions = []
        temp_day = github_rect_day
        for week in range(54):
            if temp_day.month != current_month and temp_day.year == year:
                month_positions.append((week, temp_day.month))
                current_month = temp_day.month
            temp_day += datetime.timedelta(7)

        current_month = -1
        week_index = 0
        while github_rect_day.year <= year:
            rect_x = offset.x + week_index * size

            # 月份标签
            for week_pos, month_num in month_positions:
                if week_index == week_pos:
                    month_name = MONTH_NAMES[month_num - 1]
                    dr.add(
                        dr.text(
                            month_name,
                            insert=(rect_x, offset.y),
                            fill=self.poster.colors["month_txt_color"],
                            style=self.month_names_style,
                        )
                    )

            # 一周的格子
            for day_in_week in range(7):
                if github_rect_day.year > year:
                    break

                rect_y = offset.y + size * day_in_week + DOM_BOX_PADING
                date_title = str(github_rect_day)

                if github_rect_day.year == year:
                    day_tracks = self.poster.tracks.get(date_title, 0)
                    rect = self.gen_day_box(dr, rect_x, rect_y, date_title, day_tracks)
                    dr.add(rect)

                github_rect_day += datetime.timedelta(1)

            week_index += 1

        last_box_y = offset.y + size * 7

        dr.add(
            dr.text(
                f"{year}年度总阅读时间: {year_duration}",
                insert=(offset.x, last_box_y + 15),
                fill=self.poster.colors["year_txt_color"],
                style=self.summary_style,
            )
        )

        offset.y = last_box_y + 30

    def draw(self, dr, offset):
        if self.poster.tracks is None:
            raise Exception("No tracks to draw")

        # 按年份倒序绘制（最新的在上面）
        for year in range(self.poster.start_year, self.poster.end_year + 1)[::-1]:
            self.draw_one_calendar(dr, year, offset)

    def draw_legend(self, dr, offset):
        dr.add(
            dr.text(
                "阅读时长图例:",
                insert=(offset.x, offset.y),
                fill=self.poster.colors["text_color"],
                style=self.month_names_style,
            )
        )

        legend_items = [
            {"color": self.poster.colors["dom"], "text": "无阅读"},
            {
                "color": self.poster.colors["special1"],
                "text": f"< {self.format_duration(self.poster.reading_thresholds['light'])}",
            },
            {
                "color": self.poster.colors["special2"],
                "text": f"< {self.format_duration(self.poster.reading_thresholds['medium'])}",
            },
            {
                "color": self.poster.colors["special3"],
                "text": f"< {self.format_duration(self.poster.reading_thresholds['heavy'])}",
            },
            {
                "color": self.poster.colors["special4"],
                "text": f">= {self.format_duration(self.poster.reading_thresholds['heavy'])}",
            },
        ]

        legend_x = offset.x
        legend_y = offset.y + MONTH_FONT_SIZE + DOM_BOX_PADING

        for item in legend_items:
            dr.add(
                dr.rect(
                    (legend_x, legend_y),
                    (DOM_BOX_TUPLE[0], DOM_BOX_TUPLE[1]),
                    fill=item["color"],
                    rx=DOM_BOX_RADIUS,
                    ry=DOM_BOX_RADIUS,
                )
            )
            dr.add(
                dr.text(
                    item["text"],
                    insert=(legend_x + DOM_BOX_TUPLE[0] + 5, legend_y + DOM_BOX_TUPLE[1] - 2),
                    fill=self.poster.colors["text_color"],
                    style=f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;",
                )
            )
            legend_x += 100


# ---------- 数据获取 ----------

def fetch_reading_data(auth: WeReadAuth, start_year: int, end_year: int) -> dict:
    """
    获取每日阅读数据，返回 {timestamp_str: seconds} 原始格式。
    逐月调用 /readdata/detail (mode=monthly)，monthly 的 readTimes 按天分桶。
    """
    all_read_times = {}

    for year in range(start_year, end_year + 1):
        year_total = 0
        for month in range(1, 13):
            # 跳过未来月份
            now = datetime.datetime.now()
            if year > now.year or (year == now.year and month > now.month):
                break

            base_time = int(datetime.datetime(year, month, 15).timestamp())

            try:
                resp = auth.call_gateway(
                    "/readdata/detail", mode="monthly", baseTime=base_time
                )
            except Exception as e:
                print(f"  {year}-{month:02d} 获取失败: {e}")
                continue

            read_times = resp.get("readTimes", {})
            if read_times:
                all_read_times.update(read_times)
                # 累计该月秒数
                month_total = sum(read_times.values())
                year_total += month_total

        print(f"{year} 年: 累计 {len([k for k in all_read_times if str(year) in str(datetime.datetime.fromtimestamp(int(k)).year)])} 天")

    return all_read_times


def calculate_svg_dimensions(poster):
    year_count = poster.end_year - poster.start_year + 1
    cell_size = DOM_BOX_TUPLE[0]
    padding = DOM_BOX_PADING

    svg_width = 54 * (cell_size + padding)
    svg_height = year_count * (7 * (cell_size + padding) + 30 + 20) + 50

    return svg_width, svg_height


# ---------- CLI ----------

def build_parser():
    theme_list = ", ".join(f"{k}({v['label']})" for k, v in THEMES.items())
    parser = argparse.ArgumentParser(
        description="微信阅读热力图生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
示例:
  python heatmap.py
  python heatmap.py --theme weread --start 2023 --end 2025
  python heatmap.py --theme purple --output reading.svg --stats

可用主题: {theme_list}
        """,
    )
    parser.add_argument(
        "--start",
        type=int,
        default=int(os.getenv("START_YEAR", datetime.datetime.now().year)),
        help="起始年份（默认: 今年）",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=int(os.getenv("END_YEAR", datetime.datetime.now().year)),
        help="结束年份（默认: 今年）",
    )
    parser.add_argument(
        "--theme",
        default=os.getenv("THEME_COLOR", DEFAULT_THEME),
        help=f"配色主题（默认: {DEFAULT_THEME}）",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("OUTPUT_SVG", "heatmap.svg"),
        help="SVG 输出路径（默认: heatmap.svg）",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        default=None,
        help="同时输出原始数据到 JSON 文件",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="打印统计摘要",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # 认证
    auth = WeReadAuth()
    if not auth.init_auth():
        print("请设置环境变量: export WEREAD_API_KEY=<你的API Key>")
        sys.exit(1)

    is_valid, info = auth.test_auth()
    if not is_valid:
        print(f"认证失败: {info.get('error', '未知错误')}")
        sys.exit(1)
    print("认证成功")

    # 获取原始阅读数据 {timestamp: seconds}
    print(f"正在获取 {args.start}–{args.end} 年阅读数据...")
    try:
        raw_read_times = fetch_reading_data(auth, args.start, args.end)
    except Exception as e:
        print(f"获取数据失败: {e}")
        sys.exit(1)

    if not raw_read_times:
        print("未获取到阅读数据")
        sys.exit(1)

    print(f"共获取 {len(raw_read_times)} 天的阅读记录")

    # 初始化 Poster 和 Drawer
    poster = Poster(args.start, args.end, theme=load_theme(args.theme))
    print(f"主题: {poster.theme['label']}")
    poster.output_path = args.output
    drawer = Drawer(poster)

    # 处理数据（和旧版一致）
    tracks = drawer.process_read_times(raw_read_times)
    poster.tracks = tracks

    # 提取年份信息
    dates = list(tracks.keys())
    years = sorted(set(int(d.split("-")[0]) for d in dates))
    if years:
        poster.years = [min(years), max(years)]

    # 计算数值范围和年度总和
    durations = list(tracks.values())
    if durations:
        poster.length_range_by_date = Range(min(durations), max(durations))
        for year in years:
            total = sum(v for k, v in tracks.items() if k.startswith(str(year)))
            poster.total_sum_year_dict[year] = total

    # 保存 JSON
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(tracks, f, ensure_ascii=False, indent=2)
        print(f"原始数据已保存到: {args.json_output}")

    # 生成 SVG（使用旧版绘图逻辑）
    svg_width, svg_height = calculate_svg_dimensions(poster)
    dr = Drawing(poster.output_path, size=(svg_width, svg_height))
    offset = Offset(0, 30)

    dr.add(
        dr.text(
            NAME,
            insert=(offset.x, 20),
            fill=poster.colors["title_color"],
            style="font-size:20px; font-family:Arial; font-weight:bold;",
        )
    )

    drawer.draw(dr, offset)
    # drawer.draw_legend(dr, Offset(0, svg_height - 50))

    dr.save()
    print(f"热力图已生成: {poster.output_path}")

    # 统计
    if args.stats:
        for year in sorted(poster.total_sum_year_dict):
            total = poster.total_sum_year_dict[year]
            days = len([d for d in tracks if d.startswith(str(year)) and tracks[d] > 0])
            avg = total // days if days else 0
            print(f"\n{year} 年统计:")
            print(f"  阅读天数: {days}")
            print(f"  总时长: {drawer.format_duration(total)}")
            print(f"  日均: {drawer.format_duration(avg)}")


if __name__ == "__main__":
    main()
