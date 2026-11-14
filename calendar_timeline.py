import json
import os
import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QFrame, QPushButton, QGridLayout
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor
from constants import DATA_FILE_FULL_PATH, TimerMode
from paint import TimelineWidget, TimelineCanvas, format_duration_brief

DATA_PATH = DATA_FILE_FULL_PATH


def _format_cell_duration(seconds: int) -> str:
    """日历格子中显示的紧凑时长"""
    seconds = max(0, int(seconds))
    if seconds == 0:
        return ""
    if seconds < 60:
        return "<1m"
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


class CalendarCell(QFrame):
    """日历单元格 - 暖意番茄热力图格子"""

    _HEAT_LEVELS = [
        # (max_minutes, bg, border, text, badge_bg)
        (0, "#ffffff", "#f0eae6", "#9d928e", "transparent"),
        (30, "#fff2f0", "#fbdad5", "#9f3629", "rgba(255, 91, 72, 0.12)"),
        (60, "#ffe0db", "#f9bcb3", "#8c2619", "rgba(255, 91, 72, 0.15)"),
        (120, "#ffb8ae", "#f59183", "#6d170d", "rgba(255, 255, 255, 0.35)"),
        (180, "#ff7b6a", "#ee5946", "#ffffff", "rgba(255, 255, 255, 0.24)"),
        (99999, "#eb4b38", "#d13725", "#ffffff", "rgba(255, 255, 255, 0.24)"),
    ]

    def __init__(self, date_str, day_data=None, is_today=False, is_selected=False, parent=None):
        super().__init__(parent)
        self.setObjectName("calendarCell")
        self.date_str = date_str
        self.day_data = day_data or []
        self.is_today = is_today
        self.is_selected = is_selected

        self.setMinimumSize(76, 66)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.focus_tasks = [
            t for t in self.day_data
            if t.get("mode") in (TimerMode.FOCUS, TimerMode.CANCELLED)
        ]
        self.total_duration = sum(t.get("duration", 0) for t in self.focus_tasks)
        task_names = [t.get("task-name", "未命名") for t in self.focus_tasks]
        self.unique_tasks = list(dict.fromkeys(task_names))
        self.session_count = len(self.focus_tasks)

        bg, border, text_color, badge_bg = self._resolve_palette()
        self._base_bg = bg
        self._base_border = border
        self._text_color = text_color
        self._apply_cell_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)

        # 顶行：日期数字 + 今日标记/次数角标
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        day_num = str(int(date_str.split("-")[-1]))
        day_lbl = QLabel(day_num)
        day_lbl.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
        day_lbl.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        top_row.addWidget(day_lbl)

        if is_today:
            today_tag = QLabel("今")
            today_tag.setFixedSize(16, 16)
            today_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
            today_tag.setFont(QFont("Microsoft YaHei UI", 7, QFont.Weight.Bold))
            if self.total_duration >= 120 * 60:
                today_tag.setStyleSheet(
                    "background-color: #ffffff; color: #eb4b38; border-radius: 8px; border: none;"
                )
            else:
                today_tag.setStyleSheet(
                    "background-color: #ff5b48; color: #ffffff; border-radius: 8px; border: none;"
                )
            top_row.addWidget(today_tag)

        top_row.addStretch()

        if self.session_count > 0:
            cnt_lbl = QLabel(f"{self.session_count}次")
            cnt_lbl.setFont(QFont("Microsoft YaHei UI", 8))
            cnt_lbl.setStyleSheet(
                f"color: {text_color}; background: transparent; border: none; opacity: 0.85;"
            )
            top_row.addWidget(cnt_lbl)

        layout.addLayout(top_row)

        if self.total_duration > 0:
            dur_text = _format_cell_duration(self.total_duration)
            dur_lbl = QLabel(dur_text)
            dur_lbl.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
            dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dur_lbl.setStyleSheet(f"""
                color: {text_color};
                background-color: {badge_bg};
                border-radius: 6px;
                padding: 2px 6px;
                border: none;
            """)
            layout.addWidget(dur_lbl)

            preview_text = self._get_task_preview()
            if preview_text:
                preview_lbl = QLabel(preview_text)
                preview_lbl.setFont(QFont("Microsoft YaHei UI", 8))
                preview_lbl.setStyleSheet(
                    f"color: {text_color}; background: transparent; border: none;"
                )
                preview_lbl.setWordWrap(False)
                layout.addWidget(preview_lbl)
            layout.addStretch()
        else:
            layout.addStretch()

    def _resolve_palette(self):
        if self.total_duration == 0:
            _, bg, border, text_color, badge_bg = self._HEAT_LEVELS[0]
            return bg, border, text_color, badge_bg
        minutes = self.total_duration / 60.0
        for max_m, bg, border, text_color, badge_bg in self._HEAT_LEVELS[1:]:
            if minutes < max_m:
                return bg, border, text_color, badge_bg
        _, bg, border, text_color, badge_bg = self._HEAT_LEVELS[-1]
        return bg, border, text_color, badge_bg

    def set_selected(self, selected: bool):
        if self.is_selected != selected:
            self.is_selected = selected
            self._apply_cell_style()

    def _apply_cell_style(self):
        if self.is_selected:
            border_rule = "2px solid #ff5b48"
        elif self.is_today:
            border_rule = "1.5px solid #ff8c7e"
        else:
            border_rule = f"1px solid {self._base_border}"

        hover_bg = "#faf6f4" if self.total_duration == 0 else self._base_bg
        self.setStyleSheet(f"""
            QFrame#calendarCell {{
                background-color: {self._base_bg};
                border: {border_rule};
                border-radius: 12px;
            }}
            QFrame#calendarCell:hover {{
                background-color: {hover_bg};
                border: 2px solid #ff7867;
            }}
        """)

    def _get_task_preview(self) -> str:
        if not self.unique_tasks:
            return ""
        first = self.unique_tasks[0]
        if len(first) > 7:
            first = first[:6] + "…"
        if len(self.unique_tasks) > 1:
            return f"{first} +{len(self.unique_tasks) - 1}"
        return first


class StatCard(QFrame):
    """通用统计卡片 - 严格使用 objectName 隔离样式"""

    def __init__(self, title, value, accent_hex="#ff5b48", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setStyleSheet("""
            QFrame#statCard {
                background-color: #ffffff;
                border: 1px solid #efe8e4;
                border-radius: 14px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        dot = QLabel()
        dot.setFixedSize(7, 7)
        dot.setStyleSheet(f"background-color: {accent_hex}; border-radius: 3px; border: none;")
        header.addWidget(dot)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.title_label.setStyleSheet("color: #8c827e; background: transparent; border: none;")
        header.addWidget(self.title_label, 1)
        layout.addLayout(header)

        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Microsoft YaHei UI", 15, QFont.Weight.Bold))
        self.value_label.setStyleSheet("color: #2b2523; background: transparent; border: none;")
        layout.addWidget(self.value_label)

    def update_value(self, value):
        self.value_label.setText(value)


class DetailPanel(QFrame):
    """右侧详情面板 - 当日概览、时间轴与时段明细"""

    PANEL_WIDTH = 430

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("detailPanel")
        self.setFixedWidth(self.PANEL_WIDTH)
        self.setStyleSheet("""
            QFrame#detailPanel {
                background-color: #ffffff;
                border-left: 1px solid #efe8e4;
            }
        """)

        self.date_str = ""
        self.day_data = []
        self.main_window = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 18)
        layout.setSpacing(14)

        # 1. 顶部日期栏 + 收起按钮
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        self.date_label = QLabel("选择日期查看详情")
        self.date_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        self.date_label.setStyleSheet("color: #2b2523; background: transparent; border: none;")
        title_col.addWidget(self.date_label)

        self.sub_label = QLabel("点击左侧日历中的任意日期")
        self.sub_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.sub_label.setStyleSheet("color: #8c827e; background: transparent; border: none;")
        title_col.addWidget(self.sub_label)

        header_row.addLayout(title_col, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("收起详情面板")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #faf6f4;
                color: #786e6a;
                border: 1px solid #efe8e4;
                border-radius: 15px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fdebed;
                color: #eb4b38;
                border-color: #f9c6c0;
            }
        """)
        close_btn.clicked.connect(self.hide_panel)
        header_row.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addLayout(header_row)

        # 2. 2×2 当日指标卡
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

        self.card_total_time = StatCard("总专注时长", "0m", "#ff5b48")
        self.card_sessions = StatCard("专注次数", "0 次", "#f59e0b")
        self.card_task_types = StatCard("任务种类", "0 种", "#3b82f6")
        self.card_efficiency = StatCard("平均 / 最长", "0m / 0m", "#10b981")

        # 右侧面板内部卡片使用微暖底色，在纯白面板上形成温柔层次
        for c in (self.card_total_time, self.card_sessions, self.card_task_types, self.card_efficiency):
            c.setStyleSheet("""
                QFrame#statCard {
                    background-color: #faf7f5;
                    border: 1px solid #f0e9e5;
                    border-radius: 12px;
                }
            """)
            c.value_label.setFont(QFont("Microsoft YaHei UI", 13, QFont.Weight.Bold))

        grid.addWidget(self.card_total_time, 0, 0)
        grid.addWidget(self.card_sessions, 0, 1)
        grid.addWidget(self.card_task_types, 1, 0)
        grid.addWidget(self.card_efficiency, 1, 1)
        layout.addLayout(grid)

        # 3. 时间轴视图
        tl_title = QLabel("时间轴分布")
        tl_title.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        tl_title.setStyleSheet("color: #2b2523; background: transparent; border: none;")
        layout.addWidget(tl_title)

        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)

        # 4. 当日专注记录明细列表
        list_title = QLabel("专注时段明细")
        list_title.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        list_title.setStyleSheet("color: #2b2523; background: transparent; border: none;")
        layout.addWidget(list_title)

        self.session_scroll = QScrollArea()
        self.session_scroll.setWidgetResizable(True)
        self.session_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 2px 0;
            }
            QScrollBar::handle:vertical {
                background: #e2d8d3;
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #c8bcb6;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        self.session_container = QWidget()
        self.session_container.setStyleSheet("background: transparent;")
        self.session_list_layout = QVBoxLayout(self.session_container)
        self.session_list_layout.setContentsMargins(0, 0, 4, 0)
        self.session_list_layout.setSpacing(6)
        self.session_scroll.setWidget(self.session_container)

        layout.addWidget(self.session_scroll, 1)

    def set_main_window(self, main_window):
        self.main_window = main_window

    def update_content(self, date_str, day_data):
        self.date_str = date_str
        self.day_data = day_data or []

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date_obj.weekday()]
            self.date_label.setText(f"{date_str} · {weekday}")
        except Exception:
            self.date_label.setText(date_str)

        focus_tasks = [
            t for t in self.day_data
            if t.get("mode") in (TimerMode.FOCUS, TimerMode.CANCELLED)
        ]
        total_duration = sum(t.get("duration", 0) for t in focus_tasks)
        unique_task_count = len(set(t.get("task-name", "未命名") for t in focus_tasks))
        record_count = len(focus_tasks)

        if record_count > 0:
            avg_duration = total_duration // record_count
            max_duration = max((t.get("duration", 0) for t in focus_tasks), default=0)
            self.card_total_time.update_value(format_duration_brief(total_duration))
            self.card_sessions.update_value(f"{record_count} 次")
            self.card_task_types.update_value(f"{unique_task_count} 种")
            self.card_efficiency.update_value(
                f"{format_duration_brief(avg_duration)} / {format_duration_brief(max_duration)}"
            )
            self.sub_label.setText(f"共完成 {len(self.day_data)} 条计时片段")
        else:
            self.card_total_time.update_value("0m")
            self.card_sessions.update_value("0 次")
            self.card_task_types.update_value("0 种")
            self.card_efficiency.update_value("0m / 0m")
            self.sub_label.setText("当天暂无专注记录")

        self.timeline.set_data(self.day_data, date_str)
        self._rebuild_session_list(self.day_data)

    def _rebuild_session_list(self, day_data):
        while self.session_list_layout.count():
            item = self.session_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not day_data:
            empty_lbl = QLabel("今天还没有开启番茄钟，去专注一会儿吧 🍅")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setFont(QFont("Microsoft YaHei UI", 9))
            empty_lbl.setStyleSheet(
                "color: #a89e9a; padding: 26px 10px; background-color: #faf7f5; border-radius: 10px;"
            )
            self.session_list_layout.addWidget(empty_lbl)
            self.session_list_layout.addStretch()
            return

        color_map = self.timeline.canvas.custom_task_colors
        for seg in day_data:
            task_name = seg.get("task-name", "未命名")
            mode = seg.get("mode", TimerMode.FOCUS)
            start = seg.get("start", "--:--:--")[:5]
            end = seg.get("end", "--:--:--")[:5]
            dur_str = format_duration_brief(seg.get("duration", 0))

            if mode == TimerMode.RELAX:
                dot_color = "#fb923c"
                mode_tag = "休息"
                tag_bg, tag_fg = "#fef3e6", "#d97706"
            elif mode == TimerMode.CANCELLED:
                dot_color = color_map.get(
                    task_name, TimelineCanvas.TASK_COLORS.get(task_name, QColor("#3b82f6"))
                ).name()
                mode_tag = "自由"
                tag_bg, tag_fg = "#e6f0fe", "#2563eb"
            else:
                dot_color = color_map.get(
                    task_name, TimelineCanvas.TASK_COLORS.get(task_name, QColor("#ff5b48"))
                ).name()
                mode_tag = "专注"
                tag_bg, tag_fg = "#fdebed", "#e13624"

            row = QFrame()
            row.setObjectName("sessionRow")
            row.setStyleSheet("""
                QFrame#sessionRow {
                    background-color: #faf7f5;
                    border: 1px solid #f0e9e5;
                    border-radius: 10px;
                }
            """)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(10, 7, 10, 7)
            r_layout.setSpacing(8)

            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 4px; border: none;")
            r_layout.addWidget(dot)

            time_lbl = QLabel(f"{start}-{end}")
            time_lbl.setFont(QFont("Microsoft YaHei UI", 8))
            time_lbl.setStyleSheet("color: #8c827e; background: transparent; border: none;")
            time_lbl.setFixedWidth(74)
            r_layout.addWidget(time_lbl)

            name_lbl = QLabel(task_name)
            name_lbl.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.DemiBold))
            name_lbl.setStyleSheet("color: #2b2523; background: transparent; border: none;")
            r_layout.addWidget(name_lbl, 1)

            badge = QLabel(mode_tag)
            badge.setFont(QFont("Microsoft YaHei UI", 8))
            badge.setStyleSheet(
                f"color: {tag_fg}; background-color: {tag_bg}; border-radius: 6px; padding: 1px 6px; border: none;"
            )
            r_layout.addWidget(badge)

            dur_lbl = QLabel(dur_str)
            dur_lbl.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))
            dur_lbl.setStyleSheet("color: #2b2523; background: transparent; border: none;")
            dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            dur_lbl.setFixedWidth(48)
            r_layout.addWidget(dur_lbl)

            self.session_list_layout.addWidget(row)

        self.session_list_layout.addStretch()

    def show_panel(self):
        """在现有窗口布局内平滑展开右侧面板，不拉伸外部窗口超出屏幕"""
        if self.width() >= self.PANEL_WIDTH:
            return
        self.setMinimumWidth(0)
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(220)
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(self.PANEL_WIDTH)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(lambda: self.setFixedWidth(self.PANEL_WIDTH))
        self.anim.start()

    def hide_panel(self):
        """平滑收起右侧详情面板"""
        if self.width() == 0:
            return
        self.setMinimumWidth(0)
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(220)
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(0)
        self.anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim.finished.connect(lambda: self.setFixedWidth(0))
        self.anim.start()


class CalendarTimelineWindow(QMainWindow):
    """主窗口 - 暖意番茄专注日历与时间轴面板"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("专注时间日历")
        self.resize(1240, 810)
        self.setMinimumSize(1040, 720)

        self.data = self._load_data()
        self.current_date = datetime.now()
        self.selected_date = None
        self._date_cells = {}

        self._init_ui()
        self._update_calendar()
        self._select_initial_date()

    def _load_data(self):
        try:
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载数据失败: {e}")
            return {}

    def _init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #faf6f5;
            }
            QWidget#centralWidget, QWidget#leftWidget {
                background: transparent;
            }
        """)

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧日历区域
        self.left_widget = QWidget()
        self.left_widget.setObjectName("leftWidget")
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(24, 20, 24, 18)
        self.left_layout.setSpacing(14)

        self._create_header_and_nav(self.left_layout)
        self._create_month_stats_bar(self.left_layout)
        self._create_calendar_grid(self.left_layout)
        self._create_heat_legend(self.left_layout)

        # 右侧详情面板
        self.detail_panel = DetailPanel()
        self.detail_panel.set_main_window(self)

        main_layout.addWidget(self.left_widget, 1)
        main_layout.addWidget(self.detail_panel, 0)

    def _create_header_and_nav(self, layout):
        """顶部标题与月份切换条"""
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("专注时间日历")
        title_lbl.setFont(QFont("Microsoft YaHei UI", 17, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #2b2523; background: transparent;")
        sub_lbl = QLabel("点击任意日期查看当日时间轴分布与记录明细")
        sub_lbl.setFont(QFont("Microsoft YaHei UI", 9))
        sub_lbl.setStyleSheet("color: #8c827e; background: transparent;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        bar.addLayout(title_col)
        bar.addStretch()

        nav_btn_css = """
            QPushButton {
                background-color: #ffffff;
                color: #4a423f;
                border: 1px solid #e8dfd9;
                border-radius: 17px;
                padding: 0 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #fdebed;
                color: #e13624;
                border-color: #f9c6c0;
            }
            QPushButton:pressed {
                background-color: #fad5d9;
            }
        """

        today_btn = QPushButton("本月")
        today_btn.setFixedHeight(34)
        today_btn.setFont(QFont("Microsoft YaHei UI", 9))
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.setStyleSheet(nav_btn_css)
        today_btn.clicked.connect(self._go_to_current_month)
        bar.addWidget(today_btn)

        prev_btn = QPushButton("◀")
        prev_btn.setFixedSize(34, 34)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet(nav_btn_css.replace("padding: 0 14px;", "padding: 0;"))
        prev_btn.clicked.connect(self._prev_month)
        bar.addWidget(prev_btn)

        self.month_label = QLabel()
        self.month_label.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_label.setFixedHeight(34)
        self.month_label.setMinimumWidth(116)
        self.month_label.setStyleSheet("""
            background-color: #ffffff;
            color: #2b2523;
            border: 1px solid #efe8e4;
            border-radius: 17px;
            padding: 0 14px;
        """)
        bar.addWidget(self.month_label)

        next_btn = QPushButton("▶")
        next_btn.setFixedSize(34, 34)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setStyleSheet(nav_btn_css.replace("padding: 0 14px;", "padding: 0;"))
        next_btn.clicked.connect(self._next_month)
        bar.addWidget(next_btn)

        layout.addLayout(bar)

    def _create_month_stats_bar(self, layout):
        """创建全宽四等分月度概览卡片"""
        if hasattr(self, 'stats_container') and self.stats_container is not None:
            idx = layout.indexOf(self.stats_container)
            layout.removeWidget(self.stats_container)
            self.stats_container.deleteLater()
        else:
            idx = 1

        self.stats_container = QWidget()
        self.stats_container.setStyleSheet("background: transparent;")
        stats_layout = QHBoxLayout(self.stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(12)

        month_key = self.current_date.strftime("%Y-%m")
        total_duration = 0
        days_with_data = 0
        total_sessions = 0

        for date_str, tasks in self.data.items():
            if date_str.startswith(month_key):
                focus_tasks = [
                    t for t in tasks
                    if t.get("mode") in (TimerMode.FOCUS, TimerMode.CANCELLED)
                ]
                if focus_tasks:
                    days_with_data += 1
                    total_sessions += len(focus_tasks)
                    total_duration += sum(t.get("duration", 0) for t in focus_tasks)

        avg_duration = int(total_duration / days_with_data) if days_with_data > 0 else 0

        cards = [
            ("本月专注时长", format_duration_brief(total_duration), "#ff5b48"),
            ("专注打卡天数", f"{days_with_data} 天", "#f59e0b"),
            ("累计专注次数", f"{total_sessions} 次", "#3b82f6"),
            ("日均专注时长", format_duration_brief(avg_duration), "#10b981"),
        ]
        for title, val, accent in cards:
            stats_layout.addWidget(StatCard(title, val, accent), 1)

        layout.insertWidget(idx, self.stats_container)

    def _create_calendar_grid(self, layout):
        """创建统一白底圆角日历卡片容器"""
        cal_card = QFrame()
        cal_card.setObjectName("calendarCard")
        cal_card.setStyleSheet("""
            QFrame#calendarCard {
                background-color: #ffffff;
                border: 1px solid #efe8e4;
                border-radius: 16px;
            }
        """)
        card_layout = QVBoxLayout(cal_card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(7)

        # 星期标题行
        week_layout = QGridLayout()
        week_layout.setSpacing(7)
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for i, day in enumerate(weekdays):
            lbl = QLabel(day)
            lbl.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            color = "#e05a47" if i >= 5 else "#8c827e"
            lbl.setStyleSheet(f"color: {color}; background: transparent; border: none; padding: 4px 0;")
            week_layout.addWidget(lbl, 0, i)
            week_layout.setColumnStretch(i, 1)
        card_layout.addLayout(week_layout)

        # 日历滚动区域（极简隐藏边框）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_area.viewport().setStyleSheet("background: transparent;")

        self.calendar_widget = QWidget()
        self.calendar_widget.setStyleSheet("background: transparent;")
        self.calendar_layout = QGridLayout(self.calendar_widget)
        self.calendar_layout.setContentsMargins(0, 0, 0, 0)
        self.calendar_layout.setSpacing(7)

        scroll_area.setWidget(self.calendar_widget)
        card_layout.addWidget(scroll_area, 1)

        layout.addWidget(cal_card, 1)

    def _create_heat_legend(self, layout):
        """底部热力图深浅说明"""
        row = QHBoxLayout()
        row.setContentsMargins(4, 0, 4, 0)
        row.setSpacing(6)
        row.addStretch()

        lbl_less = QLabel("少")
        lbl_less.setFont(QFont("Microsoft YaHei UI", 8))
        lbl_less.setStyleSheet("color: #8c827e; background: transparent;")
        row.addWidget(lbl_less)

        for _, bg, border, _, _ in CalendarCell._HEAT_LEVELS:
            swatch = QLabel()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(f"background-color: {bg}; border: 1px solid {border}; border-radius: 4px;")
            row.addWidget(swatch)

        lbl_more = QLabel("多 (3h+)")
        lbl_more.setFont(QFont("Microsoft YaHei UI", 8))
        lbl_more.setStyleSheet("color: #8c827e; background: transparent;")
        row.addWidget(lbl_more)

        layout.addLayout(row)

    def _update_calendar(self):
        while self.calendar_layout.count():
            item = self.calendar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._date_cells = {}

        self.month_label.setText(f"{self.current_date.year}年{self.current_date.month}月")
        today_str = datetime.now().strftime("%Y-%m-%d")

        first_day = self.current_date.replace(day=1)
        if self.current_date.month == 12:
            last_day = self.current_date.replace(year=self.current_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = self.current_date.replace(month=self.current_date.month + 1, day=1) - timedelta(days=1)

        row = 0
        col = first_day.weekday()

        for day in range(1, last_day.day + 1):
            date_str = self.current_date.strftime(f"%Y-%m-{day:02d}")
            day_data = self.data.get(date_str, [])
            is_today = (date_str == today_str)
            is_selected = (date_str == self.selected_date)

            cell = CalendarCell(date_str, day_data, is_today=is_today, is_selected=is_selected)
            cell.mousePressEvent = lambda event, ds=date_str, dd=day_data: self._on_date_clicked(ds, dd)

            self.calendar_layout.addWidget(cell, row, col)
            self._date_cells[date_str] = cell

            col += 1
            if col > 6:
                col = 0
                row += 1

        for c in range(7):
            self.calendar_layout.setColumnStretch(c, 1)
        for r in range(row + 1):
            self.calendar_layout.setRowStretch(r, 1)

    def _select_initial_date(self):
        """默认选中本月最近一个有记录的日期（若无则选中今天或本月1日）"""
        month_key = self.current_date.strftime("%Y-%m")
        today_str = datetime.now().strftime("%Y-%m-%d")

        if today_str.startswith(month_key) and self.data.get(today_str):
            target = today_str
        else:
            active_days = sorted(k for k in self.data.keys() if k.startswith(month_key) and self.data.get(k))
            if active_days:
                target = active_days[-1]
            elif today_str.startswith(month_key):
                target = today_str
            else:
                target = f"{month_key}-01"

        self._on_date_clicked(target, self.data.get(target, []))

    def _on_date_clicked(self, date_str, day_data):
        if self.selected_date and self.selected_date in self._date_cells:
            self._date_cells[self.selected_date].set_selected(False)
        self.selected_date = date_str
        if date_str in self._date_cells:
            self._date_cells[date_str].set_selected(True)

        self.detail_panel.update_content(date_str, day_data)
        self.detail_panel.show_panel()

    def _go_to_current_month(self):
        self.current_date = datetime.now()
        self._create_month_stats_bar(self.left_layout)
        self._update_calendar()
        self._select_initial_date()

    def _prev_month(self):
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        self._create_month_stats_bar(self.left_layout)
        self._update_calendar()
        self._select_initial_date()

    def _next_month(self):
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        self._create_month_stats_bar(self.left_layout)
        self._update_calendar()
        self._select_initial_date()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalendarTimelineWindow()
    window.show()
    sys.exit(app.exec())
