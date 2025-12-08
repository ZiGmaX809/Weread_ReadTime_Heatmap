import json
import datetime
import calendar
import requests
import os
import sys
from svgwrite import Drawing
from svgwrite.animate import Animate
from weread_auth import WeReadAuth  # 导入新的认证模块

# 常量配置
TRACK_COLOR = os.getenv("TRACK_COLOR", "#EBEDF0")  # 默认颜色（无阅读时间）
TRACK_SPECIAL1_COLOR = os.getenv("TRACK_SPECIAL1_COLOR", "#9BE9A8")  # 轻度阅读（0-30分钟）
TRACK_SPECIAL2_COLOR = os.getenv("TRACK_SPECIAL2_COLOR", "#40C463")  # 中度阅读（30分钟-1小时）
TRACK_SPECIAL3_COLOR = os.getenv("TRACK_SPECIAL3_COLOR", "#30A14E")  # 重度阅读（1-2小时）
TRACK_SPECIAL4_COLOR = os.getenv("TRACK_SPECIAL4_COLOR", "#216E39")  # 深度阅读（2小时以上）
DEFAULT_DOM_COLOR = os.getenv("DEFAULT_DOM_COLOR", "#EBEDF0")  # 默认日期块颜色
TEXT_COLOR = os.getenv("TEXT_COLOR", "#24292E")  # 默认文本颜色
TITLE_COLOR = os.getenv("TITLE_COLOR", "#24292E")
YEAR_TXT_COLOR = os.getenv("YEAR_TXT_COLOR", "#24292E")
MONTH_TXT_COLOR = os.getenv("MONTH_TXT_COLOR", "#24292E")
NAME = os.getenv("NAME", "微信阅读热力图")  # 图表标题
DOM_BOX_TUPLE = (10, 10)        # 格子尺寸
DOM_BOX_PADING = 2              # 格子间距
DOM_BOX_RADIUS = 2              # 格子圆角
YEAR_FONT_SIZE = 14             # 年份字体大小
MONTH_FONT_SIZE = 12            # 月份字体大小
SUMMARY_FONT_SIZE = 12          # 年度总结字体大小
MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

# 阅读时间阈值（秒）
READING_THRESHOLDS = {
    "light": 1800,    # 30分钟
    "medium": 3600,   # 1小时
    "heavy": 7200     # 2小时
}

# 辅助类
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

    def add_offset(self, offset):
        return Offset(self.x + offset.x, self.y + offset.y)

class Dimensions:
    """尺寸类"""
    def __init__(self, width, height):
        self.width = width
        self.height = height

def get_current_date():
    """获取当前日期"""
    return datetime.datetime.now()

def get_weekday(date):
    """获取日期对应的星期几（0-6，0表示周日）"""
    return date.weekday() + 1 if date.weekday() < 6 else 0

def get_first_sunday_of_year(year):
    """获取指定年份的第一个周日"""
    date = datetime.date(year, 1, 1)
    while get_weekday(date) != 0:
        date += datetime.timedelta(days=1)
    return date

def is_same_day(date1, date2):
    """判断两个日期是否是同一天"""
    return date1.year == date2.year and date1.month == date2.month and date1.day == date2.day

def get_day_of_year(date):
    """获取日期是该年的第几天"""
    return (date - datetime.date(date.year, 1, 1)).days + 1

def color_picker(reading_time):
    """根据阅读时间选择颜色"""
    if reading_time is None or reading_time == 0:
        return TRACK_COLOR
    elif reading_time < READING_THRESHOLDS["light"]:
        return TRACK_SPECIAL1_COLOR
    elif reading_time < READING_THRESHOLDS["medium"]:
        return TRACK_SPECIAL2_COLOR
    elif reading_time < READING_THRESHOLDS["heavy"]:
        return TRACK_SPECIAL3_COLOR
    else:
        return TRACK_SPECIAL4_COLOR

class Poster:
    """热力图海报类"""
    def __init__(self, start_year, end_year):
        self.start_year = start_year
        self.end_year = end_year
        self.reading_data = {}  # 存储阅读数据 {date: reading_time}

        # 颜色配置
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
            "month_txt_color": MONTH_TXT_COLOR
        }

        # 日期和时间
        self.current_date = get_current_date()
        self.dimensions = None

        # 绘制配置
        self.dom_box_dimensions = Dimensions(*DOM_BOX_TUPLE)
        self.dom_box_padding = DOM_BOX_PADING
        self.dom_box_radius = DOM_BOX_RADIUS
        self.poster_padding = 30

    def load_reading_data(self, data):
        """加载阅读数据"""
        read_times = data.get('readTimes', [])

        for item in read_times:
            # 解析日期，微信读书返回的日期是时间戳形式
            date_timestamp = item.get('date')
            if date_timestamp:
                # 转换为日期对象
                date_obj = datetime.datetime.fromtimestamp(date_timestamp)
                date_str = date_obj.strftime('%Y-%m-%d')
                read_time = item.get('readTime', 0)
                self.reading_data[date_str] = read_time

        print(f"加载了 {len(self.reading_data)} 天的阅读数据")

    def generate_svg(self):
        """生成SVG热力图"""
        # 计算SVG尺寸
        self.dimensions = self.calculate_svg_dimensions()

        # 创建SVG绘图
        dwg = Drawing(
            'heatmap.svg',
            size=(self.dimensions.width, self.dimensions.height)
        )

        # 设置背景
        dwg.add(dwg.rect(
            insert=(0, 0),
            size=(self.dimensions.width, self.dimensions.height),
            fill='white'
        ))

        # 绘制标题
        self.draw_title(dwg)

        # 绘制各年份数据
        current_y = 60
        for year in range(self.start_year, self.end_year + 1):
            self.draw_year_data(dwg, year, current_y)
            # 计算下一年份的Y位置
            weeks_in_year = 53  # 最多53周
            year_height = 7 * (self.dom_box_dimensions.height + self.dom_box_padding) + 30 + 20
            current_y += year_height

        # 绘制图例
        self.draw_legend(dwg, current_y - 30)

        # 保存SVG
        dwg.save()
        print(f"热力图已保存到: heatmap.svg")

    def calculate_svg_dimensions(self):
        """动态计算SVG尺寸"""
        year_count = self.end_year - self.start_year + 1
        cell_size = self.dom_box_dimensions.width
        padding = self.dom_box_padding

        # 计算宽度：53周 * 格子尺寸 + 月份标签宽度 + 左右边距
        svg_width = 53 * (cell_size + padding) + 30 + self.poster_padding * 2

        # 计算高度：年份数量 * (7行格子 + 月份标签 + 年份标签 + 间距) + 标题高度 + 图例高度
        year_height = 7 * (cell_size + padding) + 30 + 30  # 7天 + 月份标签 + 年份标签
        svg_height = year_count * year_height + 60 + 50 + self.poster_padding * 2  # 标题 + 图例

        return Dimensions(svg_width, svg_height)

    def draw_title(self, dwg):
        """绘制标题"""
        dwg.add(dwg.text(
            NAME,
            insert=(self.dimensions.width // 2, 30),
            fill=self.colors["title_color"],
            style=f"font-size:18px; font-family:Arial; font-weight:bold; text-anchor:middle;"
        ))

    def draw_year_data(self, dwg, year, start_y):
        """绘制指定年份的数据"""
        # 绘制年份标签
        dwg.add(dwg.text(
            str(year),
            insert=(15, start_y + 15),
            fill=self.colors["year_txt_color"],
            style=f"font-size:{YEAR_FONT_SIZE}px; font-family:Arial;"
        ))

        # 绘制月份标签
        month_x = 80  # 月份标签起始X位置
        for month_idx, month_name in enumerate(MONTH_NAMES):
            # 计算月份标签位置（近似）
            first_day = datetime.date(year, month_idx + 1, 1)
            first_sunday = get_first_sunday_of_year(year)
            week_num = (first_day - first_sunday).days // 7

            dwg.add(dwg.text(
                month_name,
                insert=(month_x + week_num * (self.dom_box_dimensions.width + self.dom_box_padding), start_y + 15),
                fill=self.colors["month_txt_color"],
                style=f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;"
            ))

        # 绘制日期格子
        current_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)

        # 找到第一个周日
        first_sunday = get_first_sunday_of_year(year)

        # 计算年度统计
        total_days = 0
        reading_days = 0
        total_time = 0

        while current_date <= end_date:
            # 计算格子位置
            days_diff = (current_date - first_sunday).days
            week_num = days_diff // 7
            day_of_week = days_diff % 7

            if week_num >= 0:  # 只绘制该年内的日期
                x = 80 + week_num * (self.dom_box_dimensions.width + self.dom_box_padding)
                y = start_y + 30 + day_of_week * (self.dom_box_dimensions.height + self.dom_box_padding)

                # 获取该天的阅读时间
                date_str = current_date.strftime('%Y-%m-%d')
                reading_time = self.reading_data.get(date_str, 0)

                # 统计
                total_days += 1
                if reading_time > 0:
                    reading_days += 1
                    total_time += reading_time

                # 绘制格子
                color = color_picker(reading_time)
                rect = dwg.rect(
                    insert=(x, y),
                    size=self.dom_box_dimensions,
                    fill=color,
                    rx=self.dom_box_radius,
                    ry=self.dom_box_radius
                )

                # 添加提示信息
                title_text = f"{date_str}: {reading_time // 60}分{reading_time % 60}秒"
                rect.set_desc(title=title_text)

                dwg.add(rect)

            current_date += datetime.timedelta(days=1)

        # 绘制年度总结
        summary_y = start_y + 30 + 8 * (self.dom_box_dimensions.height + self.dom_box_padding)
        avg_time = total_time // reading_days if reading_days > 0 else 0

        summary_text = f"阅读 {reading_days} 天, 总计 {total_time // 3600}小时{total_time % 3600 // 60}分钟, 平均 {avg_time // 60}分钟/天"
        dwg.add(dwg.text(
            summary_text,
            insert=(80, summary_y),
            fill=self.colors["text_color"],
            style=f"font-size:{SUMMARY_FONT_SIZE}px; font-family:Arial;"
        ))

    def draw_legend(self, dwg, y):
        """绘制图例"""
        legend_x = 80
        legend_y = y

        # 图例标签
        dwg.add(dwg.text(
            "Less",
            insert=(legend_x - 30, legend_y + 8),
            fill=self.colors["text_color"],
            style=f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;"
        ))

        # 绘制颜色方块
        colors = [
            (TRACK_COLOR, "无数据"),
            (TRACK_SPECIAL1_COLOR, "0-30分钟"),
            (TRACK_SPECIAL2_COLOR, "30-60分钟"),
            (TRACK_SPECIAL3_COLOR, "1-2小时"),
            (TRACK_SPECIAL4_COLOR, "2小时+")
        ]

        for color, label in colors:
            dwg.add(dwg.rect(
                insert=(legend_x, legend_y),
                size=self.dom_box_dimensions,
                fill=color,
                rx=self.dom_box_radius,
                ry=self.dom_box_radius
            ))

            legend_x += 15  # 间距

        # "More" 标签
        dwg.add(dwg.text(
            "More",
            insert=(legend_x, legend_y + 8),
            fill=self.colors["text_color"],
            style=f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;"
        ))

def get_readtiming_data(auth: WeReadAuth):
    """从微信读书API获取阅读数据"""
    url = "https://i.weread.qq.com/readdata/summary?synckey=0"
    headers = auth.get_auth_headers()

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        return {"errCode": 1001, "message": "未授权，请重新登录"}
    else:
        raise Exception(f"获取数据失败: {response.status_code}")

def main():
    """主函数"""
    # 获取环境变量
    start_year = int(os.getenv("START_YEAR", "2024"))
    end_year = int(os.getenv("END_YEAR", "2025"))
    gist_url = os.getenv("GIST_URL", "")  # GIST_URL 现在是可选的

    # 初始化认证器
    auth = WeReadAuth()

    # 初始化认证（优先从 GitHub Secrets 加载）
    if not auth.init_auth(gist_url):
        print("无法加载 Cookie，请检查 GitHub Secrets 中的 WEREAD_COOKIE")
        print("或者确保 GIST_URL 指向包含 Cookie 的 Gist")
        return

    # 测试认证有效性
    is_valid, info = auth.test_auth()
    if not is_valid:
        print("认证已失效，请更新 Cookie")
        print(f"错误信息: {info.get('error', '未知错误')}")
        return

    # 获取阅读数据
    try:
        print("正在获取阅读数据...")
        data = get_readtiming_data(auth)

        if data.get("errCode") == 1001:
            print("认证失败，请检查 cookies 是否有效")
            return

        if not data.get('readTimes'):
            print("未获取到阅读数据")
            return

        print(f"成功获取 {len(data.get('readTimes', []))} 条阅读记录")

    except Exception as e:
        print(f"获取阅读数据时出错: {e}")
        return

    # 创建热力图
    poster = Poster(start_year, end_year)
    poster.load_reading_data(data)
    poster.generate_svg()

if __name__ == "__main__":
    main()