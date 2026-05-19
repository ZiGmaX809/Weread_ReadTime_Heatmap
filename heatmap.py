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

# 阅读时间阈值（秒）
READING_THRESHOLDS = {
    "light": 1800,   # 30分钟
    "medium": 3600,  # 1小时
    "heavy": 7200,   # 2小时
}


# ---------- 辅助类 ----------

class Range:
    """数值范围类，用于颜色插值计算"""

    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def diameter(self):
        return self.upper - self.lower


class Offset:
    """位置偏移类"""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __iter__(self):
        return iter((self.x, self.y))

    def add_offset(self, offset):
        return Offset(self.x + offset.x, self.y + offset.y)


class Dimensions:
    """尺寸类，可被解包为 (width, height)"""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def __iter__(self):
        return iter((self.width, self.height))


# ---------- 日期工具 ----------

def get_current_date():
    return datetime.datetime.now()


def get_weekday(date):
    """获取日期对应的星期几（0=周日）"""
    return date.weekday() + 1 if date.weekday() < 6 else 0


def get_first_sunday_of_year(year):
    """获取指定年份的第一个周日"""
    date = datetime.date(year, 1, 1)
    while get_weekday(date) != 0:
        date += datetime.timedelta(days=1)
    return date


def color_picker(reading_time):
    """根据阅读时间选择格子颜色"""
    if reading_time is None or reading_time == 0:
        return TRACK_COLOR
    if reading_time < READING_THRESHOLDS["light"]:
        return TRACK_SPECIAL1_COLOR
    if reading_time < READING_THRESHOLDS["medium"]:
        return TRACK_SPECIAL2_COLOR
    if reading_time < READING_THRESHOLDS["heavy"]:
        return TRACK_SPECIAL3_COLOR
    return TRACK_SPECIAL4_COLOR


# ---------- 数据获取 ----------

def _parse_readtimes(readtimes: dict) -> dict:
    """将 readTimes / dailyReadTimes 的 {timestamp_str: seconds} 转为 {date_str: seconds}"""
    result = {}
    for ts_str, seconds in readtimes.items():
        ts = int(ts_str)
        date_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        result[date_str] = seconds
    return result


def _fetch_year_via_monthly(auth: WeReadAuth, year: int) -> dict:
    """
    逐月调用 /readdata/detail (mode=monthly) 获取日粒度数据。
    monthly 模式的 readTimes 按天分桶，适合热力图使用。
    """
    all_daily = {}

    for month in range(1, 13):
        # baseTime 取该月 15 号，服务端归一化到该月 1 日
        base_time = int(datetime.datetime(year, month, 15).timestamp())

        try:
            resp = auth.call_gateway(
                "/readdata/detail", mode="monthly", baseTime=base_time
            )
        except Exception as e:
            print(f"  {year}-{month:02d} 数据获取失败: {e}")
            continue

        # monthly 的 readTimes 按天分桶：{day_timestamp: seconds}
        read_times = resp.get("readTimes", {})
        if not read_times:
            continue

        daily = _parse_readtimes(read_times)
        all_daily.update(daily)

    return all_daily


def fetch_reading_data(auth: WeReadAuth, start_year: int, end_year: int) -> dict:
    """
    获取每日阅读数据，返回 {date_str: reading_seconds} 字典。
    策略：
      1. 逐年调用 annually，优先用 dailyReadTimes（日粒度，1 次请求/年）
      2. 若无 dailyReadTimes，回退到逐月调用 monthly（12 次请求/年）
    """
    all_daily_data = {}

    for year in range(start_year, end_year + 1):
        base_time = int(datetime.datetime(year, 6, 15).timestamp())

        try:
            resp = auth.call_gateway(
                "/readdata/detail", mode="annually", baseTime=base_time
            )
        except Exception as e:
            print(f"获取 {year} 年数据失败: {e}")
            continue

        # 优先使用 dailyReadTimes（真正的日粒度）
        daily_data = resp.get("dailyReadTimes")

        if daily_data:
            parsed = _parse_readtimes(daily_data)
            all_daily_data.update(parsed)
            print(f"{year} 年: {len(parsed)} 天 (dailyReadTimes)")
        else:
            # dailyReadTimes 不存在，回退到逐月调用获取日粒度数据
            print(f"{year} 年: 无 dailyReadTimes，逐月获取...")
            monthly_daily = _fetch_year_via_monthly(auth, year)
            all_daily_data.update(monthly_daily)
            print(f"{year} 年: {len(monthly_daily)} 天 (monthly 回退)")

    return all_daily_data


# ---------- SVG 热力图 ----------

class Poster:
    """热力图海报类"""

    def __init__(self, start_year, end_year):
        self.start_year = start_year
        self.end_year = end_year
        self.reading_data = {}

        self.colors = {
            "track_color": TRACK_COLOR,
            "track_special1": TRACK_SPECIAL1_COLOR,
            "track_special2": TRACK_SPECIAL2_COLOR,
            "track_special3": TRACK_SPECIAL3_COLOR,
            "track_special4": TRACK_SPECIAL4_COLOR,
            "default_dom_color": DEFAULT_DOM_COLOR,
            "text_color": TEXT_COLOR,
            "title_color": TITLE_COLOR,
            "year_txt_color": YEAR_TXT_COLOR,
            "month_txt_color": MONTH_TXT_COLOR,
        }

        self.current_date = get_current_date()
        self.dimensions = None
        self.dom_box_dimensions = Dimensions(*DOM_BOX_TUPLE)
        self.dom_box_padding = DOM_BOX_PADING
        self.dom_box_radius = DOM_BOX_RADIUS
        self.poster_padding = 30
        self.output_path = "heatmap.svg"

    def load_reading_data(self, data: dict):
        """加载阅读数据。data 格式: {date_str: reading_seconds}"""
        self.reading_data = data
        print(f"加载了 {len(self.reading_data)} 天的阅读数据")

    def get_statistics(self) -> dict:
        """计算统计信息"""
        total_seconds = sum(self.reading_data.values())
        reading_days = len([s for s in self.reading_data.values() if s > 0])
        total_days = len(self.reading_data)
        avg_per_day = total_seconds // reading_days if reading_days > 0 else 0
        return {
            "total_seconds": total_seconds,
            "total_hours": total_seconds // 3600,
            "total_minutes": (total_seconds % 3600) // 60,
            "reading_days": reading_days,
            "total_days": total_days,
            "avg_minutes_per_day": avg_per_day // 60,
        }

    def generate_svg(self):
        """生成 SVG 热力图"""
        self.dimensions = self.calculate_svg_dimensions()

        dwg = Drawing(
            self.output_path,
            size=(self.dimensions.width, self.dimensions.height),
        )

        dwg.add(
            dwg.rect(
                insert=(0, 0),
                size=(self.dimensions.width, self.dimensions.height),
                fill="white",
            )
        )

        self.draw_title(dwg)

        current_y = 60
        for year in range(self.start_year, self.end_year + 1):
            self.draw_year_data(dwg, year, current_y)
            year_height = (
                7 * (self.dom_box_dimensions.height + self.dom_box_padding) + 30 + 20
            )
            current_y += year_height

        self.draw_legend(dwg, current_y - 30)
        dwg.save()
        print(f"热力图已保存到: {self.output_path}")

    def calculate_svg_dimensions(self):
        year_count = self.end_year - self.start_year + 1
        cell_size = self.dom_box_dimensions.width
        padding = self.dom_box_padding
        svg_width = 53 * (cell_size + padding) + 30 + self.poster_padding * 2
        year_height = 7 * (cell_size + padding) + 30 + 30
        svg_height = (
            year_count * year_height + 60 + 50 + self.poster_padding * 2
        )
        return Dimensions(svg_width, svg_height)

    def draw_title(self, dwg):
        dwg.add(
            dwg.text(
                NAME,
                insert=(self.dimensions.width // 2, 30),
                fill=self.colors["title_color"],
                style=(
                    "font-size:18px; font-family:Arial; "
                    "font-weight:bold; text-anchor:middle;"
                ),
            )
        )

    def draw_year_data(self, dwg, year, start_y):
        """绘制指定年份的热力图数据"""
        # 年份标签
        dwg.add(
            dwg.text(
                str(year),
                insert=(15, start_y + 15),
                fill=self.colors["year_txt_color"],
                style=f"font-size:{YEAR_FONT_SIZE}px; font-family:Arial;",
            )
        )

        # 月份标签
        month_x = 80
        for month_idx, month_name in enumerate(MONTH_NAMES):
            first_day = datetime.date(year, month_idx + 1, 1)
            first_sunday = get_first_sunday_of_year(year)
            week_num = (first_day - first_sunday).days // 7

            dwg.add(
                dwg.text(
                    month_name,
                    insert=(
                        month_x
                        + week_num
                        * (self.dom_box_dimensions.width + self.dom_box_padding),
                        start_y + 15,
                    ),
                    fill=self.colors["month_txt_color"],
                    style=f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;",
                )
            )

        # 日期格子
        current_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)
        first_sunday = get_first_sunday_of_year(year)

        total_days = 0
        reading_days = 0
        total_time = 0

        while current_date <= end_date:
            days_diff = (current_date - first_sunday).days
            week_num = days_diff // 7
            day_of_week = days_diff % 7

            if week_num >= 0:
                x = 80 + week_num * (
                    self.dom_box_dimensions.width + self.dom_box_padding
                )
                y = (
                    start_y
                    + 30
                    + day_of_week
                    * (self.dom_box_dimensions.height + self.dom_box_padding)
                )

                date_str = current_date.strftime("%Y-%m-%d")
                reading_time = self.reading_data.get(date_str, 0)

                total_days += 1
                if reading_time > 0:
                    reading_days += 1
                    total_time += reading_time

                color = color_picker(reading_time)
                rect = dwg.rect(
                    insert=(x, y),
                    size=self.dom_box_dimensions,
                    fill=color,
                    rx=self.dom_box_radius,
                    ry=self.dom_box_radius,
                )

                minutes = reading_time // 60
                seconds = reading_time % 60
                rect.set_desc(title=f"{date_str}: {minutes}分{seconds}秒")
                dwg.add(rect)

            current_date += datetime.timedelta(days=1)

        # 年度总结
        summary_y = (
            start_y
            + 30
            + 8 * (self.dom_box_dimensions.height + self.dom_box_padding)
        )
        avg_time = total_time // reading_days if reading_days > 0 else 0

        summary_text = (
            f"阅读 {reading_days} 天, "
            f"总计 {total_time // 3600}小时{total_time % 3600 // 60}分钟, "
            f"平均 {avg_time // 60}分钟/天"
        )
        dwg.add(
            dwg.text(
                summary_text,
                insert=(80, summary_y),
                fill=self.colors["text_color"],
                style=f"font-size:{SUMMARY_FONT_SIZE}px; font-family:Arial;",
            )
        )

    def draw_legend(self, dwg, y):
        """绘制图例"""
        legend_x = 80
        legend_y = y

        dwg.add(
            dwg.text(
                "Less",
                insert=(legend_x - 30, legend_y + 8),
                fill=self.colors["text_color"],
                style=f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;",
            )
        )

        colors = [
            TRACK_COLOR,
            TRACK_SPECIAL1_COLOR,
            TRACK_SPECIAL2_COLOR,
            TRACK_SPECIAL3_COLOR,
            TRACK_SPECIAL4_COLOR,
        ]

        for color in colors:
            dwg.add(
                dwg.rect(
                    insert=(legend_x, legend_y),
                    size=self.dom_box_dimensions,
                    fill=color,
                    rx=self.dom_box_radius,
                    ry=self.dom_box_radius,
                )
            )
            legend_x += 15

        dwg.add(
            dwg.text(
                "More",
                insert=(legend_x, legend_y + 8),
                fill=self.colors["text_color"],
                style=f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;",
            )
        )


# ---------- CLI ----------

def build_parser() -> argparse.ArgumentParser:
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

    # 初始化认证
    auth = WeReadAuth()
    if not auth.init_auth():
        print("请设置环境变量: export WEREAD_API_KEY=<你的API Key>")
        sys.exit(1)

    # 测试认证
    is_valid, info = auth.test_auth()
    if not is_valid:
        print("认证失败，请检查 WEREAD_API_KEY")
        print(f"错误: {info.get('error', '未知错误')}")
        sys.exit(1)
    print("认证成功 ✓")

    # 获取阅读数据
    print(f"正在获取 {args.start}–{args.end} 年阅读数据...")
    try:
        daily_data = fetch_reading_data(auth, args.start, args.end)
    except Exception as e:
        print(f"获取数据失败: {e}")
        sys.exit(1)

    if not daily_data:
        print("未获取到阅读数据")
        sys.exit(1)

    # 保存 JSON
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(daily_data, f, ensure_ascii=False, indent=2)
        print(f"原始数据已保存到: {args.json_output}")

    # 生成热力图
    poster = Poster(args.start, args.end)
    poster.output_path = args.output
    poster.load_reading_data(daily_data)
    poster.generate_svg()

    # 打印统计
    if args.stats:
        stats = poster.get_statistics()
        print("\n📊 阅读统计:")
        print(f"  阅读天数: {stats['reading_days']} 天")
        print(f"  总时长: {stats['total_hours']}小时{stats['total_minutes']}分钟")
        print(f"  日均: {stats['avg_minutes_per_day']}分钟/阅读日")


if __name__ == "__main__":
    main()
