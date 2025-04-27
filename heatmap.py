import json
import datetime
import calendar
import requests
import os
import sys
from svgwrite import Drawing
from svgwrite.animate import Animate

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
            "track": TRACK_COLOR,  # 无阅读
            "special1": TRACK_SPECIAL1_COLOR,  # 轻度阅读（0-30分钟）
            "special2": TRACK_SPECIAL2_COLOR,  # 中度阅读（30分钟-1小时）
            "special3": TRACK_SPECIAL3_COLOR,  # 重度阅读（1-2小时）
            "special4": TRACK_SPECIAL4_COLOR,  # 深度阅读（2小时以上）
            "dom": DEFAULT_DOM_COLOR,
            "text_color": TEXT_COLOR,
            "title_color": TITLE_COLOR,
            "year_txt_color": YEAR_TXT_COLOR,
            "month_txt_color": MONTH_TXT_COLOR
        }
        self.units = "secs"
        self.with_animation = False
        self.type_list = ["readtime"]
        # 使用新的阈值配置替代原来的special_number
        self.reading_thresholds = READING_THRESHOLDS
        self.length_range_by_date = None
        self.total_sum_year_dict = {}
        # 从环境变量获取年份范围
        self.start_year = int(os.getenv("START_YEAR", 2024))
        self.end_year = int(os.getenv("END_YEAR", 2025))

class Drawer:
    """绘图器，负责生成SVG热力图"""
    name = "readtime"

    def __init__(self, poster):
        self.poster = poster
        self.year_style = f"font-size:{YEAR_FONT_SIZE}px; font-family:Arial;"
        self.month_names_style = f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;"
        self.summary_style = f"font-size:{SUMMARY_FONT_SIZE}px; font-family:Arial; font-style:italic;"

    def process_read_times(self, read_times):
        """处理阅读时间数据，将时间戳转换为日期格式"""
        tracks = {}
        for timestamp, duration in read_times.items():
            date = datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d')
            tracks[date] = duration
        return tracks

    def get_color_by_threshold(self, duration):
        """根据阅读时长阈值确定颜色"""
        if duration == 0:
            return self.poster.colors["dom"]  # 无阅读
        elif duration < self.poster.reading_thresholds["light"]:
            return self.poster.colors["special1"]  # 轻度阅读（0-30分钟）
        elif duration < self.poster.reading_thresholds["medium"]:
            return self.poster.colors["special2"]  # 中度阅读（30分钟-1小时）
        elif duration < self.poster.reading_thresholds["heavy"]:
            return self.poster.colors["special3"]  # 重度阅读（1-2小时）
        else:
            return self.poster.colors["special4"]  # 深度阅读（2小时以上）

    def format_duration(self, seconds):
        """将秒数格式化为更友好的时间格式"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes == 0:
                return f"{hours}小时"
            else:
                return f"{hours}小时{minutes}分钟"

    def gen_day_box(self, dr, rect_x, rect_y, date_title, day_tracks):
        """生成单日格子"""
        # 默认颜色（无阅读）
        color = DEFAULT_DOM_COLOR
        
        if day_tracks:
            # 根据阅读时长阈值确定颜色
            color = self.get_color_by_threshold(day_tracks)
            # 格式化阅读时长为更友好的格式
            formatted_duration = self.format_duration(day_tracks)
            date_title = f"{date_title} {formatted_duration}"
            
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
        # 存储初始Y偏移以便后面添加年度总结
        initial_y = offset.y
        
        # 计算该年1月1日是星期几(0是周一，6是周日)
        start_date_weekday, _ = calendar.monthrange(year, 1)
        
        # 调整weekday，使星期日为第一天(与GitHub保持一致)
        if start_date_weekday == 6:  # 如果是周日
            start_date_weekday = 0
        else:
            start_date_weekday += 1
            
        github_rect_first_day = datetime.date(year, 1, 1)
        github_rect_day = github_rect_first_day + datetime.timedelta(-start_date_weekday)

        # 计算该年总阅读时间并转换为小时单位
        year_length = self.poster.total_sum_year_dict.get(year, 0)
        year_hours = year_length // 3600
        year_minutes = (year_length % 3600) // 60
        
        if year_minutes == 0:
            year_duration = f"{year_hours}小时"
        else:
            year_duration = f"{year_hours}小时{year_minutes}分钟"

        offset.y += DOM_BOX_PADING + YEAR_FONT_SIZE
        
        # 绘制日历格子
        size = DOM_BOX_PADING + DOM_BOX_TUPLE[1]
        rect_x = offset.x
        current_month = -1  # 初始化为不存在的月份值

        # 绘制月份标签位置
        month_positions = []
        temp_day = github_rect_day
        for week in range(54):
            if temp_day.month != current_month and temp_day.year == year:
                month_positions.append((week, temp_day.month))
                current_month = temp_day.month
            temp_day += datetime.timedelta(7)  # 前进一周
        
        # 重置
        current_month = -1
        
        # 绘制周格子
        for week_index in range(54):
            rect_x = offset.x + week_index * size
            
            # 检查并添加月份标签
            for week_pos, month_num in month_positions:
                if week_index == week_pos:
                    month_name = MONTH_NAMES[month_num - 1]
                    dr.add(
                        dr.text(
                            f"{month_name}",
                            insert=(rect_x, offset.y),
                            fill=self.poster.colors["month_txt_color"],
                            style=self.month_names_style,
                        )
                    )
            
            # 绘制一周的格子
            for day_in_week in range(7):
                if github_rect_day.year > year:
                    break
                    
                rect_y = offset.y + size * day_in_week + DOM_BOX_PADING
                date_title = str(github_rect_day)
                
                # 只为当前年份的日期绘制格子
                if github_rect_day.year == year:
                    day_tracks = self.poster.tracks.get(date_title, 0)
                    rect = self.gen_day_box(dr, rect_x, rect_y, date_title, day_tracks)
                    dr.add(rect)
                
                github_rect_day += datetime.timedelta(1)
        
        # 计算最后一个格子的位置
        last_box_y = offset.y + size * 7
        
        # 在日历底部添加年度总阅读时间
        dr.add(
            dr.text(
                f"{year}年度总阅读时间: {year_duration}",
                insert=(offset.x, last_box_y + 15),  # 放在最后一行格子下方
                fill=self.poster.colors["year_txt_color"],
                style=self.summary_style,
            )
        )
                
        # 更新Y偏移，为下一年的热力图留出空间
        offset.y = last_box_y + 30  # 增加足够的空间放置年度总结

    def draw(self, dr, offset, is_summary=False):
        """绘制完整的热力图"""
        if self.poster.tracks is None:
            raise Exception("No tracks to draw")

        # 按年份倒序绘制
        for year in range(self.poster.start_year, self.poster.end_year + 1)[::-1]:
            self.draw_one_calendar(dr, year, offset)

    def draw_legend(self, dr, offset):
        """绘制图例"""
        legend_title = "阅读时长图例:"
        dr.add(
            dr.text(
                legend_title,
                insert=(offset.x, offset.y),
                fill=self.poster.colors["text_color"],
                style=self.month_names_style,
            )
        )
        
        # 绘制图例项
        size = DOM_BOX_TUPLE[0] + DOM_BOX_PADING
        legend_items = [
            {"color": self.poster.colors["dom"], "text": "无阅读"},
            {"color": self.poster.colors["special1"], "text": f"< {self.format_duration(self.poster.reading_thresholds['light'])}"},
            {"color": self.poster.colors["special2"], "text": f"< {self.format_duration(self.poster.reading_thresholds['medium'])}"},
            {"color": self.poster.colors["special3"], "text": f"< {self.format_duration(self.poster.reading_thresholds['heavy'])}"},
            {"color": self.poster.colors["special4"], "text": f">= {self.format_duration(self.poster.reading_thresholds['heavy'])}"}
        ]
        
        # 计算图例布局
        legend_x = offset.x
        legend_y = offset.y + MONTH_FONT_SIZE + DOM_BOX_PADING
        
        for item in legend_items:
            # 绘制颜色方块
            dr.add(
                dr.rect(
                    (legend_x, legend_y),
                    (DOM_BOX_TUPLE[0], DOM_BOX_TUPLE[1]),
                    fill=item["color"],
                    rx=DOM_BOX_RADIUS,
                    ry=DOM_BOX_RADIUS,
                )
            )
            
            # 绘制文本说明
            dr.add(
                dr.text(
                    item["text"],
                    insert=(legend_x + DOM_BOX_TUPLE[0] + 5, legend_y + DOM_BOX_TUPLE[1] - 2),
                    fill=self.poster.colors["text_color"],
                    style=f"font-size:{MONTH_FONT_SIZE}px; font-family:Arial;"
                )
            )
            
            legend_x += 100  # 移动到下一个图例项位置

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
    
    # 计算宽度：53周 * 格子尺寸
    svg_width = 54 * (cell_size + padding)
    # 计算高度：年份数量 * (7行格子 + 标题高度 + 年份间距 + 年度总结高度) + 图例高度
    svg_height = year_count * (7 * (cell_size + padding) + 30 + 20) + 30  # 增加每年底部总结的高度
    
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
    if data is None or not data.get('readTimes'):
        print("无法获取阅读数据，请检查网络连接或cookie是否有效")
        sys.exit(1)  # 使用非零退出码退出脚本
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
    offset = Offset(0, 30)  # 增加初始偏移，给左侧和顶部留出空间
    
    # 添加标题
    dr.add(dr.text(
        NAME,
        insert=(offset.x, 20), 
        fill=poster.colors["title_color"],
        style=f"font-size:20px; font-family:Arial; font-weight:bold;"
    ))
    
    # 绘制热力图
    drawer.draw(dr, offset)
    
    # 计算图例位置并绘制图例
    # legend_offset = Offset(offset.x, svg_height - 50)
    # drawer.draw_legend(dr, legend_offset)
    
    dr.save()
    print(f"热力图已生成: heatmap.svg")

if __name__ == '__main__':
    main()
