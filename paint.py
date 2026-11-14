import json
import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QMainWindow,
    QLabel, QFrame, QScrollArea, QPushButton
)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient
from PyQt6.QtCore import Qt, QTime, QRect, QPoint
from constants import TimerMode, DATA_FILE_FULL_PATH

# 使用 main.py 中的数据文件路径
DATA_PATH = DATA_FILE_FULL_PATH


def format_duration_brief(seconds: int) -> str:
    """将秒数格式化为简洁友好的时长字符串"""
    seconds = max(0, int(seconds))
    if seconds == 0:
        return "0m"
    if seconds < 60:
        return f"{seconds}s"
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


class CustomTooltip(QLabel):
    """自定义工具提示 - 暖意卡片风悬浮详情"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.hide()

    def show_tooltip(self, html_text, global_pos, border_color=None):
        """显示工具提示在指定全局位置"""
        color_hex = border_color.name() if border_color else "#ff5b48"
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #ffffff;
                color: #2b2523;
                border: 1.5px solid {color_hex};
                border-radius: 10px;
                padding: 10px 12px;
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
                font-size: 12px;
            }}
        """)
        self.setText(html_text)
        self.adjustSize()
        self.move(global_pos + QPoint(14, 14))
        self.show()


class TimelineCanvas(QWidget):
    """时间轴绘制区域 - 紧凑现代水平时间条与网格刻度"""

    DEFAULT_COLOR = QColor(59, 130, 246, 230)

    TASK_COLORS = {
        "做作业": QColor("#3b82f6"),  # 晴空蓝
        "项目": QColor("#ff5b48"),    # 番茄红
        "练习": QColor("#10b981"),    # 翡翠绿
        "阅读": QColor("#8b5cf6"),    # 薰衣草紫
        "运动": QColor("#f59e0b"),    # 琥珀橙
        "休息": QColor("#fb923c"),    # 蜜糖暖橙
    }

    _PALETTE_POOL = [
        QColor("#ff6b57"),  # 珊瑚红
        QColor("#3b82f6"),  # 晴空蓝
        QColor("#f59e0b"),  # 琥珀橙
        QColor("#10b981"),  # 翡翠绿
        QColor("#8b5cf6"),  # 薰衣草紫
        QColor("#ec4899"),  # 玫瑰粉
        QColor("#14b8a6"),  # 孔雀青
        QColor("#6366f1"),  # 靛蓝色
        QColor("#f97316"),  # 橘橙色
        QColor("#0ea5e9"),  # 天空蓝
        QColor("#a855f7"),  # 紫罗兰
        QColor("#84cc16"),  # 青柠绿
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments_data = []
        self.setFixedHeight(148)
        self.setMouseTracking(True)
        self.hovered_segment_index = -1
        self.segment_rects = []
        self.segment_data_indices = []
        self.custom_task_colors = {}
        self.current_date = ""

        self.setStyleSheet("background-color: transparent;")
        self.tooltip = CustomTooltip(self)

        self.start_hour = 0
        self.end_hour = 24
        self._zoom_to_active = True

    def set_data(self, daily_segments: list, date=""):
        self.segments_data = daily_segments or []
        self.current_date = date
        self.hovered_segment_index = -1
        self.segment_rects = []
        self.segment_data_indices = []

        self._assign_daily_colors(self.segments_data)
        if self._zoom_to_active:
            self.fit_active_range()
        else:
            self.set_time_range(0, 24)
        self.update()

    def set_zoom_mode(self, zoom_to_active: bool):
        """切换时间范围模式：True=聚焦活跃时段，False=全天24小时"""
        self._zoom_to_active = zoom_to_active
        if zoom_to_active:
            self.fit_active_range()
        else:
            self.set_time_range(0, 24)

    def fit_active_range(self):
        """自动收缩时间轴至当天存在记录的起止整点范围（至少保留 4 小时视野）"""
        if not self.segments_data:
            self.set_time_range(8, 22)
            return

        min_sec = 24 * 3600
        max_sec = 0
        for seg in self.segments_data:
            st = QTime.fromString(seg.get("start", "00:00:00"), "HH:mm:ss")
            et = QTime.fromString(seg.get("end", "00:00:00"), "HH:mm:ss")
            if st.isValid() and et.isValid():
                s_val = st.hour() * 3600 + st.minute() * 60 + st.second()
                e_val = et.hour() * 3600 + et.minute() * 60 + et.second()
                min_sec = min(min_sec, s_val)
                max_sec = max(max_sec, e_val)

        if min_sec >= max_sec:
            self.set_time_range(8, 22)
            return

        start_h = max(0, (min_sec // 3600) - 1)
        end_h = min(24, (max_sec // 3600) + 2)
        if end_h - start_h < 4:
            pad = 4 - (end_h - start_h)
            start_h = max(0, start_h - pad // 2)
            end_h = min(24, start_h + 4)
        self.set_time_range(start_h, end_h)

    def set_time_range(self, start_hour, end_hour):
        self.start_hour = max(0, min(23, int(start_hour)))
        self.end_hour = max(1, min(24, int(end_hour)))
        if self.start_hour >= self.end_hour:
            self.end_hour = min(24, self.start_hour + 1)
        self.update()

    def _assign_daily_colors(self, daily_segments: list):
        """为当天的任务分配唯一、清晰区分且协调的颜色"""
        self.custom_task_colors = {}
        used_colors = []
        task_names = set()
        for segment in daily_segments:
            task_name = segment.get("task-name", "未命名")
            if task_name in self.TASK_COLORS:
                used_colors.append(self.TASK_COLORS[task_name])
            else:
                task_names.add(task_name)

        def _is_distinct(candidate: QColor) -> bool:
            for existing in used_colors:
                dist = (
                    abs(candidate.red() - existing.red())
                    + abs(candidate.green() - existing.green())
                    + abs(candidate.blue() - existing.blue())
                )
                if dist < 110:
                    return False
            return True

        pool_idx = 0
        for task_name in sorted(task_names):
            chosen = None
            for candidate in self._PALETTE_POOL:
                if _is_distinct(candidate):
                    chosen = candidate
                    break
            if chosen is None:
                chosen = self._PALETTE_POOL[pool_idx % len(self._PALETTE_POOL)]
                pool_idx += 1
            self.custom_task_colors[task_name] = chosen
            used_colors.append(chosen)

    def _get_task_color(self, task_name):
        if task_name in self.TASK_COLORS:
            return self.TASK_COLORS[task_name]
        return self.custom_task_colors.get(task_name, self.DEFAULT_COLOR)

    def _get_gradient_colors(self, base_color):
        r, g, b, a = base_color.getRgb()
        top = QColor(min(255, int(r + (255 - r) * 0.16)),
                     min(255, int(g + (255 - g) * 0.16)),
                     min(255, int(b + (255 - b) * 0.16)), a)
        bot = QColor(max(0, int(r * 0.90)),
                     max(0, int(g * 0.90)),
                     max(0, int(b * 0.90)), a)
        return top, bot

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # 1. 纯白圆角底卡（融入暖意番茄风）
        card_rect = QRect(2, 2, width - 4, height - 4)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#efe8e4"), 1.2))
        painter.drawRoundedRect(card_rect, 12, 12)

        margin_left = 20
        margin_right = 20
        track_top = 26
        bar_height = 54
        track_rect = QRect(margin_left, track_top, max(100, width - margin_left - margin_right), bar_height)

        # 2. 时间轴底轨与垂直网格
        self._draw_track_and_grid(painter, track_rect)
        # 3. 任务片段条块
        self._draw_segments(painter, track_rect)
        # 4. 底部时间刻度轴
        self._draw_time_axis(painter, track_rect)

    def _draw_track_and_grid(self, painter, track_rect):
        """绘制柔和米白底轨与精细虚线网格"""
        painter.setBrush(QColor("#faf6f4"))
        painter.setPen(QPen(QColor("#ece3de"), 1))
        painter.drawRoundedRect(track_rect, 10, 10)

        hour_range = self.end_hour - self.start_hour
        if hour_range <= 0:
            return

        grid_pen = QPen(QColor("#ebe3df"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        for hour in range(self.start_hour + 1, self.end_hour):
            norm = (hour - self.start_hour) / hour_range
            x = track_rect.x() + int(norm * track_rect.width())
            painter.drawLine(x, track_rect.top() + 4, x, track_rect.bottom() - 4)

    def _draw_time_axis(self, painter, track_rect):
        """绘制紧凑清晰的时间刻度线"""
        axis_y = track_rect.bottom() + 14
        painter.setPen(QPen(QColor("#e2d8d3"), 1.2))
        painter.drawLine(track_rect.left(), axis_y, track_rect.right(), axis_y)

        hour_range = self.end_hour - self.start_hour
        if hour_range <= 0:
            return

        # 自适应主刻度步长，防止小宽幅下标签重叠
        if hour_range <= 6:
            step = 1
        elif hour_range <= 12:
            step = 2
        else:
            step = 4

        painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.Weight.DemiBold))
        end_x = track_rect.right()
        for hour in range(self.start_hour, self.end_hour + 1):
            norm = (hour - self.start_hour) / hour_range
            x = track_rect.x() + int(norm * track_rect.width())
            is_end = (hour == self.end_hour)
            is_start = (hour == self.start_hour)
            # 避免倒数第二个主刻度文字与终点标签 (如 23:00 和 24:00) 重叠
            too_close_to_end = (not is_end and not is_start and (end_x - x) < 42)
            is_major = is_start or is_end or ((hour - self.start_hour) % step == 0 and not too_close_to_end)

            if is_major:
                painter.setPen(QPen(QColor("#b8aba6"), 1.3))
                painter.drawLine(x, axis_y - 3, x, axis_y + 4)

                # 首尾标签往内对齐，避免裁切
                if is_start:
                    rect = QRect(x, axis_y + 6, 44, 18)
                    align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                elif is_end:
                    rect = QRect(x - 44, axis_y + 6, 44, 18)
                    align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                else:
                    rect = QRect(x - 22, axis_y + 6, 44, 18)
                    align = Qt.AlignmentFlag.AlignCenter

                painter.setPen(QColor("#786e6a"))
                painter.drawText(rect, align, f"{hour:02d}:00")
            else:
                painter.setPen(QPen(QColor("#dfd5d0"), 1))
                painter.drawLine(x, axis_y, x, axis_y + 3)

    def _draw_segments(self, painter, track_rect):
        self.segment_rects = []
        self.segment_data_indices = []

        hour_range = self.end_hour - self.start_hour
        if hour_range <= 0:
            return

        if not self.segments_data:
            painter.save()
            painter.setFont(QFont("Microsoft YaHei UI", 9))
            painter.setPen(QColor("#a89e9a"))
            painter.drawText(track_rect, Qt.AlignmentFlag.AlignCenter, "当日暂无时间轴记录")
            painter.restore()
            return

        bar_y = track_rect.top() + 7
        bar_h = track_rect.height() - 14

        for data_index, segment in enumerate(self.segments_data):
            start_time = QTime.fromString(segment.get("start", "00:00:00"), "HH:mm:ss")
            end_time = QTime.fromString(segment.get("end", "00:00:00"), "HH:mm:ss")
            if not start_time.isValid() or not end_time.isValid():
                continue

            start_sec = start_time.hour() * 3600 + start_time.minute() * 60 + start_time.second()
            end_sec = end_time.hour() * 3600 + end_time.minute() * 60 + end_time.second()
            if end_sec <= start_sec:
                continue

            norm_start = max(0.0, min(1.0, (start_sec - self.start_hour * 3600) / (hour_range * 3600)))
            norm_end = max(0.0, min(1.0, (end_sec - self.start_hour * 3600) / (hour_range * 3600)))
            if norm_end <= norm_start:
                continue

            x1 = track_rect.x() + int(norm_start * track_rect.width())
            x2 = track_rect.x() + int(norm_end * track_rect.width())
            # 确保短记录也可见、可悬停
            seg_w = max(5, x2 - x1)
            if x1 + seg_w > track_rect.right() - 2:
                x1 = max(track_rect.left() + 2, track_rect.right() - 2 - seg_w)

            seg_rect = QRect(x1, bar_y, seg_w, bar_h)
            self.segment_rects.append(seg_rect)
            self.segment_data_indices.append(data_index)

            task_name = segment.get("task-name", "未命名")
            mode = segment.get("mode", TimerMode.FOCUS)
            if mode == TimerMode.RELAX:
                base_color = QColor("#fb923c")
            else:
                base_color = QColor(self._get_task_color(task_name))

            is_hovered = (len(self.segment_rects) - 1 == self.hovered_segment_index)
            c1, c2 = self._get_gradient_colors(base_color)
            if is_hovered:
                c1 = c1.lighter(110)
                c2 = c2.lighter(108)

            grad = QLinearGradient(float(seg_rect.left()), float(seg_rect.top()),
                                   float(seg_rect.left()), float(seg_rect.bottom()))
            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            painter.setBrush(grad)

            if is_hovered:
                painter.setPen(QPen(base_color.darker(120), 2.0))
            else:
                painter.setPen(QPen(QColor(255, 255, 255, 190), 1))

            painter.drawRoundedRect(seg_rect, 6, 6)

            if seg_w >= 46:
                painter.save()
                painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.Weight.Bold))
                painter.setPen(QColor("#ffffff"))
                metrics = painter.fontMetrics()
                elided = metrics.elidedText(task_name, Qt.TextElideMode.ElideRight, seg_w - 10)
                painter.drawText(seg_rect, Qt.AlignmentFlag.AlignCenter, elided)
                painter.restore()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        self.hovered_segment_index = -1

        for i, rect in enumerate(self.segment_rects):
            # 稍微放宽上下命中区域方便悬停细短条块
            hit_rect = rect.adjusted(-2, -4, 2, 4)
            if hit_rect.contains(pos):
                self.hovered_segment_index = i
                data_index = self.segment_data_indices[i]
                segment = self.segments_data[data_index]

                task_name = segment.get("task-name", "未命名")
                mode = segment.get("mode", TimerMode.FOCUS)
                start = segment.get("start", "")
                end = segment.get("end", "")
                duration = segment.get("duration", 0)
                dur_str = format_duration_brief(duration)

                if mode == TimerMode.RELAX:
                    mode_icon, mode_color, mode_disp = "☕", "#d97706", "休息时间"
                    accent = QColor("#fb923c")
                elif mode == TimerMode.CANCELLED:
                    mode_icon, mode_color, mode_disp = "⏱️", "#2563eb", "自由模式"
                    accent = self._get_task_color(task_name)
                else:
                    mode_icon, mode_color, mode_disp = "🎯", "#eb4c39", "专注模式"
                    accent = self._get_task_color(task_name)

                tooltip_html = f"""
                <table style='border-spacing: 0px 4px; font-size: 12px;'>
                    <tr><td colspan='2' style='font-size: 13px; font-weight: bold; color: #2b2523; padding-bottom: 3px;'>{task_name}</td></tr>
                    <tr><td style='color: #8c827e; padding-right: 10px;'>模式</td><td style='color: {mode_color}; font-weight: 600;'>{mode_icon} {mode_disp}</td></tr>
                    <tr><td style='color: #8c827e;'>时段</td><td style='color: #2b2523; font-weight: 600;'>{start} - {end}</td></tr>
                    <tr><td style='color: #8c827e;'>时长</td><td style='color: #ff5b48; font-weight: 700;'>{dur_str}</td></tr>
                </table>
                """
                global_pos = event.globalPosition().toPoint()
                self.tooltip.show_tooltip(tooltip_html, global_pos, accent)
                break

        if self.hovered_segment_index == -1:
            self.tooltip.hide()

        self.update()

    def leaveEvent(self, event):
        self.hovered_segment_index = -1
        self.tooltip.hide()
        self.update()


class TaskLegendWidget(QFrame):
    """任务类型图例 - 干净圆角小药丸标签"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_types = set()
        self.custom_colors = {}
        self.setStyleSheet("QFrame { background-color: transparent; border: none; }")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 4, 2, 2)
        self.layout.setSpacing(6)

        self.legend_flow = QHBoxLayout()
        self.legend_flow.setSpacing(8)
        self.legend_flow.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.legend_flow)

    def update_legend(self, task_types, custom_colors=None):
        self.custom_colors = custom_colors or {}
        self.task_types = task_types or set()

        while self.legend_flow.count():
            item = self.legend_flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.task_types:
            return

        for task_name in sorted(self.task_types)[:6]:
            color = self._get_task_color(task_name)
            chip = QFrame()
            chip.setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    border: 1px solid #efe8e4;
                    border-radius: 11px;
                }
            """)
            c_layout = QHBoxLayout(chip)
            c_layout.setContentsMargins(8, 3, 9, 3)
            c_layout.setSpacing(5)

            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {color.name()}; border: none; border-radius: 4px;")
            c_layout.addWidget(dot)

            display_name = task_name if len(task_name) <= 8 else task_name[:7] + "…"
            lbl = QLabel(display_name)
            lbl.setFont(QFont("Microsoft YaHei UI", 8))
            lbl.setStyleSheet("color: #5c534f; border: none; background: transparent;")
            c_layout.addWidget(lbl)

            self.legend_flow.addWidget(chip)

        self.legend_flow.addStretch()

    def _get_task_color(self, task_name):
        if task_name in TimelineCanvas.TASK_COLORS:
            return TimelineCanvas.TASK_COLORS[task_name]
        if task_name in self.custom_colors:
            return self.custom_colors[task_name]
        return TimelineCanvas.DEFAULT_COLOR


class TimelineWidget(QWidget):
    """时间轴主控件 - 带视图缩放切换（聚焦时段 / 全天24h）与图例"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(8)

        # 顶部视图模式切换工具条
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        toolbar.setContentsMargins(0, 0, 0, 0)

        self.range_hint_lbl = QLabel("时段: 08:00 - 22:00")
        self.range_hint_lbl.setFont(QFont("Microsoft YaHei UI", 8))
        self.range_hint_lbl.setStyleSheet("color: #8c827e; background: transparent;")
        toolbar.addWidget(self.range_hint_lbl)
        toolbar.addStretch()

        self.btn_zoom_active = QPushButton("聚焦时段")
        self.btn_zoom_24h = QPushButton("全天 24h")
        for btn in (self.btn_zoom_active, self.btn_zoom_24h):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(24)
            btn.setFont(QFont("Microsoft YaHei UI", 8, QFont.Weight.DemiBold))

        self.btn_zoom_active.setChecked(True)
        self.btn_zoom_active.clicked.connect(lambda: self._switch_zoom(True))
        self.btn_zoom_24h.clicked.connect(lambda: self._switch_zoom(False))

        toolbar.addWidget(self.btn_zoom_active)
        toolbar.addWidget(self.btn_zoom_24h)
        self.main_layout.addLayout(toolbar)

        self.canvas = TimelineCanvas()
        self.main_layout.addWidget(self.canvas)

        self.legend = TaskLegendWidget()
        self.main_layout.addWidget(self.legend)

        self._refresh_zoom_btn_styles()
        self.setStyleSheet("background-color: transparent;")

    def _switch_zoom(self, zoom_active: bool):
        self.btn_zoom_active.setChecked(zoom_active)
        self.btn_zoom_24h.setChecked(not zoom_active)
        self.canvas.set_zoom_mode(zoom_active)
        self._update_range_label()
        self._refresh_zoom_btn_styles()

    def _update_range_label(self):
        self.range_hint_lbl.setText(f"时段: {self.canvas.start_hour:02d}:00 - {self.canvas.end_hour:02d}:00")

    def _refresh_zoom_btn_styles(self):
        active_css = """
            QPushButton {
                background-color: #fdebed;
                color: #e13624;
                border: 1px solid #f9c6c0;
                border-radius: 12px;
                padding: 0 10px;
            }
        """
        idle_css = """
            QPushButton {
                background-color: #f4efec;
                color: #786e6a;
                border: 1px solid transparent;
                border-radius: 12px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #ebe4e0;
                color: #2b2523;
            }
        """
        self.btn_zoom_active.setStyleSheet(active_css if self.btn_zoom_active.isChecked() else idle_css)
        self.btn_zoom_24h.setStyleSheet(active_css if self.btn_zoom_24h.isChecked() else idle_css)

    def set_data(self, daily_segments: list, date=""):
        self.canvas.set_data(daily_segments, date)
        self._update_range_label()
        all_tasks = set(seg.get("task-name", "未命名") for seg in (daily_segments or []))
        self.legend.update_legend(all_tasks, self.canvas.custom_task_colors)


# --- 独立演示入口 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("专注时间轴预览")
        self.setGeometry(100, 100, 820, 320)
        self.setStyleSheet("QMainWindow { background-color: #faf6f5; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)
        self.setCentralWidget(container)
        self._load_data()

    def _load_data(self):
        if not os.path.exists(DATA_PATH):
            return
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data:
            latest_date = sorted(data.keys())[-1]
            self.timeline.set_data(data[latest_date], latest_date)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
