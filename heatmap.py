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

# ---------- 常量配置 ----------

TRACK_COLOR = os.getenv("TRACK_COLOR", "#EBEDF0")
TRACK_SPECIAL1_COLOR = os.getenv("TRACK_SPECIAL1_COLOR", "#9BE9A8")
TRACK_SPECIAL2_COLOR = os.getenv("TRACK_SPECIAL2_COLOR", "#40C463")
TRACK_SPECIAL3_COLOR = os.getenv("TRACK_SPECIAL3_COLOR", "#30A14E")
TRACK_SPECIAL4_COLOR = os.getenv("TRACK_SPECIAL4_COLOR", "#216E39")
DEFAULT_DOM_COLOR = os.getenv("DEFAULT_DOM_COLOR", "#EBEDF0")
TEXT_COLOR = os.getenv("TEXT_COLOR", "#24292E")
TITLE_COLOR = os.getenv("TITLE_COLOR", "#24292E")
YEAR_TXT_COLOR = os.getenv("YEAR_TXT_COLOR", "#24292E")
MONTH_TXT_COLOR = os.getenv("MONTH_TXT_COLOR", "#24292E")
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

    def __init__(self, start_year, end_year):
        self.tracks = None
        self.years = []
        self.start_year = start_year
        self.end_year = end_year
        self.colors = {
            "track": TRACK_COLOR,
            "special1": TRACK_SPECIAL1_COLOR,
            "special2": TRACK_SPECIAL2_COLOR,
            "special3": TRACK_SPECIAL3_COLOR,
            "special4": TRACK_SPECIAL4_COLOR,
            "dom": DEFAULT_DOM_COLOR,
            "text_color": TEXT_COLOR,
            "title_color": TITLE_COLOR,
            "year_txt_color": YEAR_TXT_COLOR,
            "month_txt_color": MONTH_TXT_COLOR,
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
    parser = argparse.ArgumentParser(
        description="微信阅读热力图生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python heatmap.py
  python heatmap.py --start 2023 --end 2025
  python heatmap.py --output reading.svg --json reading.json
  WEREAD_API_KEY=wrk-xxx python heatmap.py
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
    poster = Poster(args.start, args.end)
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
