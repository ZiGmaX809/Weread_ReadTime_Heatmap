import json
import datetime
import calendar
import requests
import os
from svgwrite import Drawing
from svgwrite.animate import Animate

# 常量配置
TRACK_COLOR = os.getenv("TRACK_COLOR")
TRACK_SPECIAL_COLOR = os.getenv("TRACK_SPECIAL_COLOR")
TRACK_SPECIAL2_COLOR = os.getenv("TRACK_SPECIAL2_COLOR")
TRACK_SPECIAL3_COLOR = os.getenv("TRACK_SPECIAL3_COLOR")
DEFAULT_DOM_COLOR = os.getenv("DEFAULT_DOM_COLOR")
TEXT_COLOR = os.getenv("TEXT_COLOR")
NAME = os.getenv("NAME")
DOM_BOX_TUPLE = (10, 10)  # 格子尺寸
DOM_BOX_PADING = 2        # 格子间距
DOM_BOX_RADIUS = 2        # 格子圆角
YEAR_FONT_SIZE = 14       # 年份字体大小
MONTH_FONT_SIZE = 12      # 月份字体大小（添加了缺失的值）
MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

# 辅助类
class Range:
    """数值范围类，用于颜色插值计算"""
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def diameter(self):
        return self.upper - self.lower

class Offset:
    """坐标偏移类，用于跟踪绘图位置"""
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def tuple(self):
        return (self.x, self.y)

class Poster:
    """海报类，存储绘图所需的数据和配置"""
    def __init__(self):
        self.tracks = None
        self.years = []
        self.colors = {
            "track": TRACK_COLOR,
            "special": TRACK_SPECIAL_COLOR,
            "special2": TRACK_SPECIAL2_COLOR,
            "special3": TRACK_SPECIAL3_COLOR,
            "dom": DEFAULT_DOM_COLOR,
            "text": TEXT_COLOR
        }
        self.units = "secs"
        self.with_animation = False
        self.type_list = ["readtime"]
        self.special_number = {
            "special_number1": 3600,
            "special_number2": 1800
        }
        self.length_range_by_date = None
        self.total_sum_year_dict = {}
        # 从环境变量获取年份范围
        self.start_year = int(os.getenv("START_YEAR", 2020))
        self.end_year = int(os.getenv("END_YEAR", 2025))

class Drawer:
    """绘图器，负责生成SVG热力图"""
    name = "readtime"

    def __init__(self, poster):
        self.poster = poster
        self.year_style = f"font-size:{YEAR_FONT_SIZE}px; font-family:Arial;"
        self.month_names_style = f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial"

    def process_read_times(self, read_times):
        """处理阅读时间数据，将时间戳转换为日期格式"""
        tracks = {}
        for timestamp, duration in read_times.items():
            date = datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d')
            tracks[date] = duration
        return tracks

    def hex_to_rgb(self, hex_color):
        """将十六进制颜色转换为RGB元组"""
        return tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))

    def rgb_to_hex(self, rgb):
        """将RGB元组转换为十六进制颜色"""
        return '#%02x%02x%02x' % rgb

    def interpolate_color(self, color_from, color_to, ratio):
        """在两个颜色之间进行线性插值"""
        from_rgb = self.hex_to_rgb(color_from)
        to_rgb = self.hex_to_rgb(color_to)
        result = tuple(int(from_rgb[i] + (to_rgb[i] - from_rgb[i]) * ratio) for i in range(3))
        return self.rgb_to_hex(result)

    def make_color(self, length_range, length):
        """根据数值在范围中的位置计算颜色"""
        color_from = self.poster.colors["track"]
        color_to = self.poster.colors["special3"]
        diff = length_range.diameter()
        if diff == 0:
            return color_from

        return self.interpolate_color(
            color_from, color_to, (length - length_range.lower) / diff
        )

    def gen_day_box(self, dr, rect_x, rect_y, date_title, day_tracks):
        """生成单日格子"""
        color = DEFAULT_DOM_COLOR
        if day_tracks:
            color = self.make_color(self.poster.length_range_by_date, day_tracks)
            date_title = f"{date_title} {day_tracks} {self.poster.units}"
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
        # 计算该年1月1日是星期几
        start_date_weekday, _ = calendar.monthrange(year, 1)
        github_rect_first_day = datetime.date(year, 1, 1)
        github_rect_day = github_rect_first_day + datetime.timedelta(-start_date_weekday)

        # 计算该年总阅读时间并转换为小时单位
        year_length = self.poster.total_sum_year_dict.get(year, 0)
        year_units = "hours"
        year_length = str(int(year_length / 3600)) + f" {year_units}"

        # 添加年份标题
        offset.y += DOM_BOX_PADING + YEAR_FONT_SIZE
        dr.add(
            dr.text(
                f"{year}: {year_length}",
                insert=offset.tuple(),
                fill=self.poster.colors["text"],
                style=self.year_style,
            )
        )
        offset.y += DOM_BOX_PADING + MONTH_FONT_SIZE

        # 绘制日历格子
        size = DOM_BOX_PADING + DOM_BOX_TUPLE[1]
        rect_x = offset.x
        month = MONTH_NAMES[0]

        for index in range(54):
            # 添加月份标签
            if index == 0 or (index > 0 and index < 53 and month != MONTH_NAMES[github_rect_day.month - 1]):
                month = MONTH_NAMES[github_rect_day.month - 1]
                dr.add(
                    dr.text(
                        f"{month}",
                        insert=(rect_x, offset.y),
                        fill=self.poster.colors["text"],
                        style=self.month_names_style,
                    )
                )

            # 绘制一周的格子
            for week in range(7):
                if int(github_rect_day.year) > year:
                    break
                rect_y = offset.y + size * week + DOM_BOX_PADING
                date_title = str(github_rect_day)
                day_tracks = self.poster.tracks.get(date_title)
                rect = self.gen_day_box(dr, rect_x, rect_y, date_title, day_tracks)
                dr.add(rect)
                github_rect_day += datetime.timedelta(1)
            rect_x += size
        offset.y += size * 7

    def draw(self, dr, offset, is_summary=False):
        """绘制完整的热力图"""
        if self.poster.tracks is None:
            raise Exception("No tracks to draw")

        # 按年份倒序绘制
        for year in range(self.poster.start_year, self.poster.end_year + 1)[::-1]:
            self.draw_one_calendar(dr, year, offset)

def get_readtiming_data(cookie):
    """从微信读书API获取阅读数据"""
    url = "https://i.weread.qq.com/readdata/summary?synckey=0"
    headers = {
        "Cookie": cookie
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        return {"errCode": 1001, "message": "未授权，请重新登录"}
    else:
        raise Exception(f"获取数据失败: {response.status_code}")

def refresh_cookies(cookie):
    print("尝试刷新cookies...")
    
    url = "https://weread.qq.com/"
    headers = {
        "Cookie": cookie
    }
    
    try:
        response = requests.get(url, headers=headers)
        new_cookies = response.cookies.get_dict()

        # 更新cookie
        cookie_parts = cookie.split(';')
        updated_cookie = []
        for part in cookie_parts:
            key = part.split('=')[0].strip()
            if key not in new_cookies:
                updated_cookie.append(part)
        
        for key, value in new_cookies.items():
            updated_cookie.append(f"{key}={value}")
        
        updated_cookie_str = '; '.join(updated_cookie)
        print("已生成新的cookie")
        return True, updated_cookie_str
    except Exception as e:
        print(f"刷新cookies时出错: {e}")
        return False, None

def calculate_svg_dimensions(poster):
    """动态计算SVG尺寸"""
    year_count = poster.end_year - poster.start_year + 1
    cell_size = DOM_BOX_TUPLE[0]  # 每个格子的尺寸
    padding = DOM_BOX_PADING  # 格子间距
    month_label_width = 30  # 月份标签宽度
    
    # 计算宽度：53周 * 格子尺寸 + 月份标签宽度
    svg_width = 53 * (cell_size + padding) + month_label_width
    # 计算高度：年份数量 * (7行格子 + 标题高度)
    svg_height = year_count * (7 * (cell_size + padding) + 30) + 20
    
    return svg_width, svg_height

def main():
    """主函数"""
    # 检查环境变量
    cookie = os.getenv("WEREAD_COOKIE") 
    if not cookie:
        raise Exception("WEREAD_COOKIE 未设置")
    
    # 初始化数据
    data = None
    
    # 获取阅读数据，如果失败则尝试刷新cookie
    try:
        data = get_readtiming_data(cookie)
        if data.get("errCode") == 1001:  # 未登录状态
            print("检测到未登录状态，尝试刷新cookies...")
            success, new_cookie = refresh_cookies(cookie)
            if success:
                print("cookies刷新成功，重新获取数据...")
                cookie = new_cookie
                data = get_readtiming_data(cookie)
                if data.get("errCode") == 1001:
                    print("自动刷新cookies后仍然未登录")
            else:
                print("cookies刷新失败，请手动更新cookies")
    except Exception as e:
        print(f"获取阅读数据时出错: {e}")
        return

    # 如果无法获取数据，则退出
    if data is None:
        print("无法获取阅读数据，请检查网络连接或cookie是否有效")
        return
    
    # 初始化海报对象
    poster = Poster()
    drawer = Drawer(poster)
    
    # 处理阅读时间数据
    tracks = drawer.process_read_times(data['readTimes'])
    poster.tracks = tracks
    
    # 提取年份信息
    dates = list(tracks.keys())
    years = sorted(list(set([int(date.split('-')[0]) for date in dates])))
    poster.years = [min(years), max(years)]
    
    # 计算数值范围和年度总和
    durations = list(tracks.values())
    if durations:  # 确保列表不为空
        poster.length_range_by_date = Range(min(durations), max(durations))
        
        # 计算每年的总阅读时间
        for year in years:
            total = sum([duration for date, duration in tracks.items() if date.startswith(str(year))])
            poster.total_sum_year_dict[year] = total
    
    # 计算SVG尺寸
    svg_width, svg_height = calculate_svg_dimensions(poster)
    
    # 创建SVG绘图对象
    dr = Drawing('heatmap.svg', size=(svg_width, svg_height))
    offset = Offset(0, 20)  # 初始偏移
    
    # 添加标题
    dr.add(dr.text(
        NAME,
        insert=(0, 20), 
        fill=poster.colors["text"],
        style=f"font-size:20px; font-family:Arial;font-weight:bold;"
    ))
    
    # 绘制热力图
    drawer.draw(dr, offset)
    dr.save()

if __name__ == '__main__':
    main()
