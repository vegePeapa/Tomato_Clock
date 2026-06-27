import sys
import json
import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QFrame, QPushButton, QGridLayout
)
from PyQt6.QtCore import Qt, QDate, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from constants import DATA_FILE_FULL_PATH
# 导入原有的时间轴组件
from paint import TimelineWidget

DATA_PATH = DATA_FILE_FULL_PATH


class CalendarCell(QFrame):
    """日历单元格 - 显示单日的任务概览"""

    def __init__(self, date_str, day_data=None, parent=None):
        super().__init__(parent)
        self.date_str = date_str
        self.day_data = day_data or []
        self.setFrameStyle(QFrame.Shape.Box)
        self.setMinimumSize(110, 100)  # 最小尺寸限制
        self.setMaximumSize(220, 180)  # 最大尺寸限制
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 计算当天的统计信息
        self.focus_tasks = [t for t in self.day_data if t.get("mode") == "专注"]
        self.total_duration = sum(t.get("duration", 0) for t in self.focus_tasks)
        # 按任务名称去重统计（统计所有模式的任务）
        task_names = set(t.get("task-name", "未命名") for t in self.day_data)
        self.task_count = len(task_names)

        # 根据专注时长设置背景色
        self.bg_color = self._get_bg_color_by_duration()
        self.text_color = self._get_text_color()
        self.border_color = self._get_border_color()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.bg_color};
                border: 1px solid {self.border_color};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border: 2px solid {self._get_hover_color()};
                background-color: {self._lighten_color(self.bg_color)};
            }}
        """)

        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)  # 调整边距
        layout.setSpacing(4)  # 减小间距

        # 日期数字
        date_num = date_str.split("-")[-1]
        date_label = QLabel(date_num)
        date_label.setFont(QFont("Arial", 15, QFont.Weight.Bold))  # 稍微减小字体
        date_label.setStyleSheet(f"color: {self.text_color};")
        date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(date_label)

        # 专注时长
        if self.total_duration > 0:
            hours, minutes = divmod(self.total_duration, 3600)
            minutes = minutes // 60
            if hours > 0:
                duration_text = f"🎯 {hours}h {minutes}m"
            else:
                duration_text = f"🎯 {minutes}m"

            duration_label = QLabel(duration_text)
            duration_label.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))  # 减小字体
            duration_label.setStyleSheet(f"color: {self.text_color}; background-color: rgba(255,255,255,0.3); border-radius: 6px; padding: 3px 6px;")  # 减小padding
            duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(duration_label)

            # 任务预览
            task_preview = self._get_task_preview()
            if task_preview:
                preview_label = QLabel(task_preview)
                preview_label.setFont(QFont("Microsoft YaHei", 8))  # 减小字体
                preview_label.setStyleSheet(f"color: {self.text_color}; background-color: rgba(255,255,255,0.2); border-radius: 5px; padding: 4px;")  # 减小padding
                preview_label.setWordWrap(True)
                preview_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
                layout.addWidget(preview_label, 1)  # 添加stretch factor让预览区域可以扩展

            # 任务数量
            count_label = QLabel(f"📋 {self.task_count}个")
            count_label.setFont(QFont("Microsoft YaHei", 8))  # 减小字体
            count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            count_label.setStyleSheet(f"color: {self.text_color}; opacity: 0.8;")
            layout.addWidget(count_label)
        else:
            no_data_label = QLabel("😴 无记录")
            no_data_label.setFont(QFont("Microsoft YaHei", 10))  # 减小字体
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data_label.setStyleSheet("color: #999;")
            layout.addWidget(no_data_label)
            layout.addStretch()

    def _get_bg_color_by_duration(self):
        """根据专注时长返回背景色(渐变色方案)"""
        minutes = self.total_duration / 60

        if minutes == 0:
            return "#f8f9fa"
        elif minutes < 30:
            return "#e8f5e9"  # 浅绿
        elif minutes < 60:
            return "#c8e6c9"  # 中绿
        elif minutes < 120:
            return "#81c784"  # 深绿
        elif minutes < 180:
            return "#4caf50"  # 更深绿
        elif minutes < 240:
            return "#66bb6a"  # 金绿
        else:
            return "#ffa726"  # 橙色成就

    def _get_text_color(self):
        """根据背景色返回合适的文字颜色"""
        minutes = self.total_duration / 60
        if minutes < 30:
            return "#2e7d32"
        elif minutes < 120:
            return "#1b5e20"
        else:
            return "#ffffff"

    def _get_border_color(self):
        """根据专注时长返回边框颜色"""
        minutes = self.total_duration / 60
        if minutes == 0:
            return "#e0e0e0"
        elif minutes < 120:
            return "#a5d6a7"
        else:
            return "#43a047"

    def _get_hover_color(self):
        """返回悬停时的边框颜色"""
        minutes = self.total_duration / 60
        if minutes == 0:
            return "#bdbdbd"
        elif minutes < 120:
            return "#66bb6a"
        else:
            return "#2e7d32"

    def _lighten_color(self, color):
        """使颜色变亮(用于悬停效果)"""
        color_map = {
            "#f8f9fa": "#f1f3f4",
            "#e8f5e9": "#c8e6c9",
            "#c8e6c9": "#a5d6a7",
            "#81c784": "#66bb6a",
            "#4caf50": "#43a047",
            "#66bb6a": "#2e7d32",
            "#ffa726": "#fb8c00"
        }
        return color_map.get(color, "#c8e6c9")

    def _get_task_preview(self):
        """获取任务预览文本"""
        if not self.focus_tasks:
            return ""

        # 获取去重后的任务名称
        task_names = list(set(task.get("task-name", "未命名") for task in self.focus_tasks))

        # 生成预览文本,只显示任务名称,不显示次数
        preview_lines = task_names[:4]  # 最多显示4个任务名称

        return "\n".join(preview_lines)


class StatCard(QFrame):
    """统计卡片 - 显示单个指标"""

    def __init__(self, title, value, icon_char, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f5fcf8);
                border: 1.5px solid #dcefe3;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Header layout (Icon + Title)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self.icon_label = QLabel(icon_char)
        self.icon_label.setFont(QFont("Segoe UI Emoji", 14))
        self.icon_label.setStyleSheet("border: none; background: transparent;")
        header_layout.addWidget(self.icon_label)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Medium))
        self.title_label.setStyleSheet("color: #606f7b; border: none; background: transparent;")
        header_layout.addWidget(self.title_label, 1)

        layout.addLayout(header_layout)

        # Value label
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Microsoft YaHei UI", 13, QFont.Weight.Bold))
        self.value_label.setStyleSheet("color: #1b4332; border: none; background: transparent; padding-top: 2px;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.value_label)

    def update_value(self, value):
        self.value_label.setText(value)


class DetailPanel(QFrame):
    """右侧详情面板 - 显示选中日期的详细信息"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFixedWidth(0)  # 初始宽度为0
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border-left: 3px solid #4caf50;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 日期标题
        self.date_label = QLabel("选择日期查看详情")
        self.date_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        self.date_label.setStyleSheet("color: #2e7d32; padding: 10px; background-color: #e8f5e9; border-radius: 8px;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.date_label)

        # 分隔线
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("background-color: #e0e0e0; max-height: 2px;")
        layout.addWidget(line1)

        # 当日统计
        stats_label = QLabel("📊 当日统计")
        stats_label.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        stats_label.setStyleSheet("color: #43a047; margin-top: 5px;")
        layout.addWidget(stats_label)

        # 统计卡片网格容器
        self.stats_grid_widget = QWidget()
        self.stats_grid_layout = QGridLayout(self.stats_grid_widget)
        self.stats_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_grid_layout.setSpacing(10)

        # 创建四个独立的统计卡片
        self.card_total_time = StatCard("总专注时长", "0m", "🎯")
        self.card_sessions = StatCard("专注次数", "0 次", "🔥")
        self.card_task_types = StatCard("任务种类", "0 种", "📋")
        self.card_efficiency = StatCard("平均 / 最长", "0m / 0m", "📈")

        self.stats_grid_layout.addWidget(self.card_total_time, 0, 0)
        self.stats_grid_layout.addWidget(self.card_sessions, 0, 1)
        self.stats_grid_layout.addWidget(self.card_task_types, 1, 0)
        self.stats_grid_layout.addWidget(self.card_efficiency, 1, 1)

        layout.addWidget(self.stats_grid_widget)

        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("background-color: #e0e0e0; max-height: 2px;")
        layout.addWidget(line2)

        # 时间轴
        timeline_label = QLabel("⏰ 时间轴视图")
        timeline_label.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        timeline_label.setStyleSheet("color: #43a047; margin-top: 5px;")
        layout.addWidget(timeline_label)

        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)

        # 关闭按钮
        close_btn = QPushButton("✖ 关闭面板")
        close_btn.setFont(QFont("Microsoft YaHei", 11))
        close_btn.setFixedHeight(40)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #43a047;
            }
            QPushButton:pressed {
                background-color: #2e7d32;
            }
        """)
        close_btn.clicked.connect(self.hide_panel)
        layout.addWidget(close_btn)

        layout.addStretch()

        # 保存主窗口引用
        self.main_window = None

    def set_main_window(self, main_window):
        """设置主窗口引用"""
        self.main_window = main_window

    def update_content(self, date_str, day_data):
        """更新面板内容"""
        self.date_str = date_str
        self.day_data = day_data

        # 更新日期标签
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date_obj.weekday()]
            self.date_label.setText(f"📅 {date_str} {weekday}")
        except:
            self.date_label.setText(f"📅 {date_str}")

        # 计算统计数据
        focus_tasks = [t for t in day_data if t.get("mode") == "专注"]
        total_duration = sum(t.get("duration", 0) for t in focus_tasks)
        # 按任务名称去重统计
        task_names = set(t.get("task-name", "未命名") for t in focus_tasks)
        unique_task_count = len(task_names)
        record_count = len(focus_tasks)

        if record_count > 0:
            avg_duration = total_duration // record_count
            max_duration = max((t.get("duration", 0) for t in focus_tasks), default=0)

            hours, minutes = divmod(total_duration, 3600)
            minutes = minutes // 60
            avg_minutes = avg_duration // 60
            max_minutes = max_duration // 60

            total_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            self.card_total_time.update_value(total_str)
            self.card_sessions.update_value(f"{record_count} 次")
            self.card_task_types.update_value(f"{unique_task_count} 种")
            self.card_efficiency.update_value(f"{avg_minutes}m / {max_minutes}m")
        else:
            self.card_total_time.update_value("0m")
            self.card_sessions.update_value("0 次")
            self.card_task_types.update_value("0 种")
            self.card_efficiency.update_value("0m / 0m")

        # 更新时间轴
        self.timeline.set_data(day_data, date_str)

    def show_panel(self):
        """显示面板(带动画)"""
        target_width = 450  # 增加面板宽度
        self.animation = QPropertyAnimation(self, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(target_width)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.start()

        # 同时更新固定宽度
        self.setFixedWidth(target_width)

    def hide_panel(self):
        """隐藏面板(带动画)"""
        self.animation = QPropertyAnimation(self, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.finished.connect(self._on_hide_finished)
        self.animation.start()

    def _on_hide_finished(self):
        """动画结束后的回调"""
        self.setFixedWidth(0)


class CalendarTimelineWindow(QMainWindow):
    """主窗口 - 日历时间轴应用"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("专注时间日历")
        self.setGeometry(100, 100, 1200, 800)

        # 加载数据
        self.data = self._load_data()
        self.current_date = datetime.now()
        self.selected_date = None

        # 创建主界面
        self._init_ui()

        # 设置当前月份
        self._update_calendar()

    def _load_data(self):
        """加载main_data.json"""
        try:
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载数据失败: {e}")
            return {}

    def _init_ui(self):
        """初始化UI"""
        # 设置窗口背景与整体配色，避免暗黑模式系统背景影响
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f5fcf8, stop:0.5 #f0fbf6, stop:1 #e8f9f0);
            }
            QWidget#centralWidget {
                background: transparent;
            }
            QWidget#leftWidget {
                background: transparent;
            }
        """)

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        # 主布局 - 水平布局(左侧固定 + 右侧抽屉)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧固定区域
        self.left_widget = QWidget()
        self.left_widget.setObjectName("leftWidget")
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(20, 20, 20, 20)
        self.left_layout.setSpacing(15)


        # 月度统计栏
        self._create_month_stats_bar(self.left_layout)

        # 月份导航
        self._create_month_navigation(self.left_layout)

        # 日历网格
        self._create_calendar_grid(self.left_layout)

        self.left_widget.setMinimumWidth(900)

        # 右侧详情面板
        self.detail_panel = DetailPanel()
        self.detail_panel.set_main_window(self)

        # 添加到主布局
        main_layout.addWidget(self.left_widget)
        main_layout.addWidget(self.detail_panel)

        # 设置左侧拉伸因子为1,右侧为0
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 0)

    def _create_month_stats_bar(self, layout):
        """创建月度统计栏"""
        # 如果已存在统计栏,先移除
        if hasattr(self, 'stats_frame') and self.stats_frame is not None:
            layout.removeWidget(self.stats_frame)
            self.stats_frame.deleteLater()

        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e8f5e9, stop:1 #c8e6c9);
                border-radius: 12px;
                padding: 18px;
                border: 2px solid #a5d6a7;
            }
        """)
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setSpacing(25)

        # 计算当前月份的统计数据
        month_key = self.current_date.strftime("%Y-%m")
        total_duration = 0
        days_with_data = 0
        total_tasks = 0

        for date_str, tasks in self.data.items():
            if date_str.startswith(month_key):
                focus_tasks = [t for t in tasks if t.get("mode") == "专注"]
                if focus_tasks:
                    days_with_data += 1
                    total_tasks += len(focus_tasks)
                    total_duration += sum(t.get("duration", 0) for t in focus_tasks)

        # 计算平均
        avg_duration = total_duration / days_with_data if days_with_data > 0 else 0
        hours, minutes = divmod(int(total_duration), 3600)
        minutes = minutes // 60
        avg_minutes = int(avg_duration // 60)

        # 创建统计卡片
        stats_items = [
            ("总时长", f"{hours}h {minutes}m"),
            ("有记录天数", f"{days_with_data}天"),
            ("任务总数", f"{total_tasks}个"),
            ("日均时长", f"{avg_minutes}m")
        ]

        for title, value in stats_items:
            card = QWidget()
            card.setStyleSheet("""
                QWidget {
                    background-color: rgba(255, 255, 255, 0.6);
                    border-radius: 10px;
                    padding: 12px;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(6)

            title_label = QLabel(title)
            title_label.setFont(QFont("Microsoft YaHei", 10))
            title_label.setStyleSheet("color: #558b2f;")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            value_label = QLabel(value)
            value_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
            value_label.setStyleSheet("color: #2e7d32;")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            card_layout.addWidget(title_label)
            card_layout.addWidget(value_label)
            stats_layout.addWidget(card)

        stats_layout.addStretch()

        # 插入到布局的第一个位置(顶部)
        layout.insertWidget(0, self.stats_frame)

    def _create_month_navigation(self, layout):
        """创建月份导航"""
        nav_widget = QWidget()
        nav_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                padding: 8px;
            }
        """)
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(15)

        # 上一个月
        prev_month_btn = QPushButton("◀ 上月")
        prev_month_btn.setFont(QFont("Microsoft YaHei", 11))
        prev_month_btn.setFixedHeight(38)
        prev_month_btn.setStyleSheet("""
            QPushButton {
                background-color: #66bb6a;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4caf50;
            }
            QPushButton:pressed {
                background-color: #43a047;
            }
        """)
        prev_month_btn.clicked.connect(self._prev_month)
        nav_layout.addWidget(prev_month_btn)

        # 当前月份显示
        self.month_label = QLabel()
        self.month_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        self.month_label.setStyleSheet("color: #2e7d32; padding: 8px 16px; background-color: #e8f5e9; border-radius: 8px;")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.month_label, 1)

        # 下一个月
        next_month_btn = QPushButton("下月 ▶")
        next_month_btn.setFont(QFont("Microsoft YaHei", 11))
        next_month_btn.setFixedHeight(38)
        next_month_btn.setStyleSheet("""
            QPushButton {
                background-color: #66bb6a;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4caf50;
            }
            QPushButton:pressed {
                background-color: #43a047;
            }
        """)
        next_month_btn.clicked.connect(self._next_month)
        nav_layout.addWidget(next_month_btn)

        layout.addWidget(nav_widget)

    def _create_calendar_grid(self, layout):
        """创建日历网格"""
        # 星期标题
        week_widget = QWidget()
        week_widget.setStyleSheet("background-color: #f1f8e9; border-radius: 10px; padding: 10px;")
        week_layout = QGridLayout(week_widget)
        week_layout.setSpacing(8)

        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekend_colors = {"周六": "#e57373", "周日": "#e57373"}  # 周末用红色
        weekday_colors = {"周一": "#558b2f", "周二": "#558b2f", "周三": "#558b2f",
                          "周四": "#558b2f", "周五": "#558b2f", "周六": "#e57373", "周日": "#e57373"}

        for i, day in enumerate(weekdays):
            day_label = QLabel(day)
            day_label.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            day_label.setStyleSheet(f"""
                color: {weekday_colors[day]};
                padding: 8px;
                background-color: rgba(255, 255, 255, 0.7);
                border-radius: 6px;
            """)
            week_layout.addWidget(day_label, 0, i)

        layout.addWidget(week_widget)

        # 日历单元格容器
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_area.viewport().setStyleSheet("background: transparent;")

        self.calendar_widget = QWidget()
        self.calendar_widget.setStyleSheet("background: transparent;")
        self.calendar_layout = QGridLayout(self.calendar_widget)
        self.calendar_layout.setSpacing(8)

        scroll_area.setWidget(self.calendar_widget)
        layout.addWidget(scroll_area, 1)


    def _update_calendar(self):
        """更新日历显示"""
        # 清空现有单元格
        while self.calendar_layout.count():
            item = self.calendar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 更新月份标签
        self.month_label.setText(f"{self.current_date.year}年{self.current_date.month}月")

        # 重新创建统计栏
        # 清除旧的统计栏
        old_stats = self.findChild(QFrame, "month_stats")
        if old_stats:
            old_stats.deleteLater()

        # 获取当月的第一天和最后一天
        first_day = self.current_date.replace(day=1)
        if self.current_date.month == 12:
            last_day = self.current_date.replace(year=self.current_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = self.current_date.replace(month=self.current_date.month + 1, day=1) - timedelta(days=1)

        # 计算第一天是周几 (0=周一, 6=周日)
        first_weekday = first_day.weekday()

        # 填充日历
        row = 1
        col = first_weekday

        for day in range(1, last_day.day + 1):
            date_str = self.current_date.strftime(f"%Y-%m-{day:02d}")
            day_data = self.data.get(date_str, [])

            # 创建单元格
            cell = CalendarCell(date_str, day_data)
            cell.mousePressEvent = lambda event, ds=date_str, dd=day_data: self._on_date_clicked(ds, dd)

            self.calendar_layout.addWidget(cell, row, col)

            col += 1
            if col > 6:
                col = 0
                row += 1

        # 添加弹性空间
        self.calendar_layout.setColumnStretch(0, 1)
        self.calendar_layout.setColumnStretch(1, 1)
        self.calendar_layout.setColumnStretch(2, 1)
        self.calendar_layout.setColumnStretch(3, 1)
        self.calendar_layout.setColumnStretch(4, 1)
        self.calendar_layout.setColumnStretch(5, 1)
        self.calendar_layout.setColumnStretch(6, 1)

    def _on_date_clicked(self, date_str, day_data):
        """日期点击事件"""
        self.selected_date = date_str

        # 更新详情面板内容
        self.detail_panel.update_content(date_str, day_data)

        # 显示详情面板
        self.detail_panel.show_panel()

        # 扩展窗口宽度
        self._expand_window()

    def _expand_window(self):
        """扩展窗口以容纳右侧面板"""
        current_width = self.width()
        target_width = current_width + 400

        animation = QPropertyAnimation(self, b"size")
        animation.setDuration(300)
        animation.setStartValue(self.size())
        animation.setEndValue(QSize(target_width, self.height()))
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()

    def _prev_month(self):
        """上一个月"""
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)

        # 重新创建统计栏
        self._create_month_stats_bar(self.left_layout)
        self._update_calendar()

    def _next_month(self):
        """下一个月"""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)

        # 重新创建统计栏
        self._create_month_stats_bar(self.left_layout)
        self._update_calendar()
