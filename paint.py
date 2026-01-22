import sys, json, os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QMainWindow, QLabel,
                             QToolTip, QFrame, QGridLayout, QScrollArea)
from PyQt6.QtGui import QPainter, QColor, QFont, QFontDatabase, QPen
from PyQt6.QtCore import Qt, QTime, QRect, QPoint
from main import TimerMode, DATA_FILE_FULL_PATH

# 使用 main.py 中的数据文件路径
DATA_PATH = DATA_FILE_FULL_PATH

class CustomTooltip(QLabel):
    """自定义工具提示 - 完全控制样式"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置为顶层窗口，不会被父控件裁剪
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            QLabel {
                background-color: rgb(255, 255, 255);
                color: rgb(51, 51, 51);
                border: 1px solid rgb(204, 204, 204);
                border-radius: 4px;
                padding: 6px;
                font-family: "Microsoft YaHei";
                font-size: 11px;
            }
        """)
        self.hide()

    def show_tooltip(self, text, global_pos):
        """显示工具提示在指定全局位置"""
        self.setText(text)
        self.adjustSize()
        self.move(global_pos + QPoint(15, 15))
        self.show()


class TimelineCanvas(QWidget):
    """
    时间轴绘制区域 - 只负责绘制时间轴和条块，固定高度，支持横向滚动
    """
    # 颜色常量
    DEFAULT_COLOR = QColor(64, 158, 255, 230)
    AXIS_COLOR = QColor(150, 150, 150)
    BG_COLOR = QColor(245, 245, 245)
    BORDER_COLOR = QColor(200, 200, 200)
    TEXT_COLOR = QColor(50, 50, 50)
    GRID_COLOR = QColor(220, 220, 220)

    TASK_COLORS = {
        "做作业": QColor(64, 158, 255, 230),
        "项目": QColor(255, 102, 102, 230),
        "练习英语": QColor(72, 187, 120, 230),
        "阅读": QColor(165, 105, 189, 230),
        "运动": QColor(255, 165, 0, 230),
        "休息": QColor(204, 204, 204, 230)
    }

    HOVER_COLORS = {}
    for task, color in TASK_COLORS.items():
        r, g, b, a = color.getRgb()
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        HOVER_COLORS[task] = QColor(r, g, b, 255)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments_data = []
        self.setMinimumHeight(300)  # 改为最小高度，允许更大
        self.day_seconds = 24 * 60 * 60
        self.setMouseTracking(True)
        self.hovered_segment_index = -1
        self.segment_rects = []
        self.custom_task_colors = {}
        self.color_index = 0
        self.current_date = ""

        self.setStyleSheet("background-color: transparent;")

        # 创建自定义工具提示
        self.tooltip = CustomTooltip(self)

        self.start_hour = 0
        self.end_hour = 24

    def set_data(self, daily_segments: list, date=""):
        self.segments_data = daily_segments
        self.current_date = date
        self.hovered_segment_index = -1
        self.segment_rects = []
        self.update()

    def set_time_range(self, start_hour, end_hour):
        self.start_hour = max(0, min(24, start_hour))
        self.end_hour = max(1, min(24, end_hour))
        if self.start_hour >= self.end_hour:
            self.end_hour = min(24, self.start_hour + 1)
        self.update()

    def _update_active_task_types(self):
        pass  # 不再需要，任务类型由图例widget管理

    def _get_task_color(self, task_name):
        if task_name in self.TASK_COLORS:
            return self.TASK_COLORS[task_name]
        if task_name not in self.custom_task_colors:
            colors = [
                QColor(102, 177, 255, 230), QColor(230, 162, 60, 230),
                QColor(103, 194, 58, 230), QColor(245, 108, 108, 230),
                QColor(163, 53, 238, 230), QColor(255, 230, 0, 230),
                QColor(79, 195, 247, 230), QColor(149, 117, 205, 230),
                QColor(255, 112, 67, 230), QColor(38, 198, 218, 230)
            ]
            # 使用任务名称的哈希值来保证颜色一致性（与图例同步）
            color_index = hash(task_name) % len(colors)
            self.custom_task_colors[task_name] = colors[color_index]
        return self.custom_task_colors[task_name]

    def _get_task_hover_color(self, task_name):
        base_color = self._get_task_color(task_name)
        if task_name in self.HOVER_COLORS:
            return self.HOVER_COLORS[task_name]
        r, g, b, _ = base_color.getRgb()
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        return QColor(r, g, b, 255)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 设置固定宽度，确保24小时有足够显示空间
        # 每小时至少需要40px，所以24小时需要960px
        required_width = 960
        if self.width() < required_width:
            self.setFixedWidth(required_width)

        width = self.width()
        height = self.height()

        margin_left = 45
        margin_right = 10
        margin_top = 30
        margin_bottom = 40
        bar_height = 70

        content_rect = QRect(margin_left, margin_top,
                            width - margin_left - margin_right,
                            height - margin_top - margin_bottom - bar_height)

        painter.fillRect(self.rect(), self.BG_COLOR)

        self._draw_time_axis(painter, content_rect, margin_bottom)
        self._draw_segments(painter, content_rect, bar_height, margin_bottom)
        self._draw_grid_lines(painter, content_rect, bar_height, margin_bottom)

    def _draw_time_axis(self, painter, content_rect, margin_bottom):
        axis_x = content_rect.left()
        axis_y = content_rect.bottom() + margin_bottom

        painter.setPen(QPen(self.AXIS_COLOR, 2))
        painter.drawLine(axis_x, axis_y, content_rect.right(), axis_y)

        hour_range = self.end_hour - self.start_hour
        if hour_range <= 0:
            return

        content_width = content_rect.width()
        for hour in range(self.start_hour, self.end_hour + 1):
            normalized_time = (hour - self.start_hour) / hour_range
            x = content_rect.x() + int(normalized_time * content_width)

            painter.setPen(QPen(self.AXIS_COLOR, 1))
            painter.drawLine(x, axis_y, x, axis_y + 5)

            painter.setPen(self.TEXT_COLOR)
            painter.setFont(QFont("Microsoft YaHei", 8))  # 减小字体
            painter.drawText(x - 12, axis_y + 18, f"{hour}:00")  # 调整位置

    def _draw_segments(self, painter, content_rect, bar_height, margin_bottom):
        self.segment_rects = []
        bar_y = content_rect.bottom() + margin_bottom - bar_height - 10

        hour_range = self.end_hour - self.start_hour
        if hour_range <= 0:
            return

        content_width = content_rect.width()

        # 绘制所有模式的片段
        for segment in self.segments_data:
            start_time = QTime.fromString(segment.get("start", "00:00:00"), "HH:mm:ss")
            end_time = QTime.fromString(segment.get("end", "00:00:00"), "HH:mm:ss")

            start_seconds = start_time.hour() * 3600 + start_time.minute() * 60 + start_time.second()
            end_seconds = end_time.hour() * 3600 + end_time.minute() * 60 + end_time.second()

            normalized_start = (start_seconds - self.start_hour * 3600) / (hour_range * 3600)
            normalized_end = (end_seconds - self.start_hour * 3600) / (hour_range * 3600)

            x1 = content_rect.x() + int(normalized_start * content_width)
            x2 = content_rect.x() + int(normalized_end * content_width)

            if x2 > x1:
                segment_width = x2 - x1
                segment_rect = QRect(x1, bar_y, segment_width, bar_height)
                self.segment_rects.append(segment_rect)

                task_name = segment.get("task-name", "未命名")
                mode = segment.get("mode", "专注")

                # 根据模式调整颜色显示
                base_color = self._get_task_color(task_name)

                if mode == TimerMode.FOCUS or mode == TimerMode.CANCELLED:
                    # 专注模式：正常颜色，完全不透明
                    color = QColor(base_color)
                    color.setAlpha(230)
                elif mode == TimerMode.RELAX:
                    # 休息模式：使用灰色
                    color = QColor(204, 204, 204, 180)
                
                else:
                    # 其他模式：默认半透明
                    color = QColor(base_color)
                    color.setAlpha(150)

                if self.segment_rects.index(segment_rect) == self.hovered_segment_index:
                    # 悬停时变亮
                    r, g, b, _ = color.getRgb()
                    r = min(255, int(r * 1.2))
                    g = min(255, int(g * 1.2))
                    b = min(255, int(b * 1.2))
                    color = QColor(r, g, b, 255)

                painter.setBrush(color)
                painter.setPen(QPen(QColor(200, 200, 200), 0.5))
                painter.drawRoundedRect(segment_rect, 5, 5)

    def _draw_grid_lines(self, painter, content_rect, bar_height, margin_bottom):
        bar_y = content_rect.bottom() + margin_bottom - bar_height - 10

        hour_range = self.end_hour - self.start_hour
        if hour_range <= 0:
            return

        content_width = content_rect.width()
        painter.setPen(QPen(self.GRID_COLOR, 0.5, Qt.PenStyle.DashLine))

        for hour in range(self.start_hour, self.end_hour + 1):
            normalized_time = (hour - self.start_hour) / hour_range
            x = content_rect.x() + int(normalized_time * content_width)
            painter.drawLine(x, content_rect.y() + 40, x, bar_y)

        painter.setPen(QPen(self.GRID_COLOR, 0.5, Qt.PenStyle.DashLine))
        painter.drawLine(content_rect.x(), bar_y - 5, content_rect.right(), bar_y - 5)
        painter.drawLine(content_rect.x(), bar_y + bar_height // 2,
                        content_rect.right(), bar_y + bar_height // 2)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        self.hovered_segment_index = -1

        for i, rect in enumerate(self.segment_rects):
            if rect.contains(pos):
                self.hovered_segment_index = i
                segment = self.segments_data[i]  # 直接使用所有模式的数据

                task_name = segment.get("task-name", "未命名")
                mode = segment.get("mode", "专注")
                start = segment.get("start", "")
                end = segment.get("end", "")
                duration = segment.get("duration", 0)
                minutes = duration // 60

                tooltip_text = f"任务: {task_name}\n模式: {mode}\n开始: {start}\n结束: {end}\n时长: {minutes} 分钟"
                # 使用自定义工具提示，传递全局坐标
                global_pos = event.globalPosition().toPoint()
                self.tooltip.show_tooltip(tooltip_text, global_pos)
                break

        if self.hovered_segment_index == -1:
            self.tooltip.hide()

        self.update()

    def leaveEvent(self, event):
        self.hovered_segment_index = -1
        self.tooltip.hide()
        self.update()


class TaskLegendWidget(QFrame):
    """
    任务类型图例 - 自动扩展高度
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_types = set()

        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)

        # 标题
        title_label = QLabel("任务类型：")
        title_label.setFont(QFont("SimHei", 9, QFont.Weight.Medium))
        title_label.setStyleSheet("color: #333333;")
        self.layout.addWidget(title_label)

        # 图例容器（使用网格布局）
        self.legend_layout = QGridLayout()
        self.legend_layout.setSpacing(8)
        self.layout.addLayout(self.legend_layout)

    def update_legend(self, task_types):
        """更新图例内容"""
        # 清空现有图例项
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.task_types = task_types

        # 添加新图例项，每行5个
        items_per_row = 5
        for i, task_name in enumerate(sorted(task_types)):
            row = i // items_per_row
            col = i % items_per_row

            # 颜色块
            color = self._get_task_color(task_name)
            color_label = QLabel()
            color_label.setFixedSize(14, 14)
            color_label.setStyleSheet(f"""
                background-color: {color.name()};
                border: 1px solid rgb(200, 200, 200);
                border-radius: 3px;
            """)
            self.legend_layout.addWidget(color_label, row, col * 2)

            # 任务名称
            display_name = task_name if len(task_name) <= 8 else task_name[:7] + "..."
            name_label = QLabel(display_name)
            name_label.setFont(QFont("SimHei", 8))
            name_label.setStyleSheet("color: #333333;")
            self.legend_layout.addWidget(name_label, row, col * 2 + 1)

    def _get_task_color(self, task_name):
        """获取任务颜色（与TimelineCanvas相同的逻辑）"""
        if task_name in TimelineCanvas.TASK_COLORS:
            return TimelineCanvas.TASK_COLORS[task_name]
        # 为未预定义的任务生成颜色（需要与TimelineCanvas同步）
        colors = [
            QColor(102, 177, 255, 230), QColor(230, 162, 60, 230),
            QColor(103, 194, 58, 230), QColor(245, 108, 108, 230),
            QColor(163, 53, 238, 230), QColor(255, 230, 0, 230),
            QColor(79, 195, 247, 230), QColor(149, 117, 205, 230),
            QColor(255, 112, 67, 230), QColor(38, 198, 218, 230)
        ]
        # 使用任务名称的哈希值来保证颜色一致性
        color_index = hash(task_name) % len(colors)
        return colors[color_index]


class TimelineWidget(QWidget):
    """
    时间轴主控件 - 组合时间轴画布和任务图例，支持滚动
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        # 时间轴滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFixedHeight(320)  # 固定高度，只显示横向滚动条
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:horizontal {
                background-color: #e0e0e0;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4caf50;
                border-radius: 6px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #43a047;
            }
        """)

        # 时间轴画布（可滚动）
        self.canvas = TimelineCanvas()
        self.scroll_area.setWidget(self.canvas)
        self.main_layout.addWidget(self.scroll_area)

        # 任务图例（自动扩展）
        self.legend = TaskLegendWidget()
        self.main_layout.addWidget(self.legend)

        self.setStyleSheet("background-color: transparent;")

    def set_data(self, daily_segments: list, date=""):
        """设置数据"""
        self.canvas.set_data(daily_segments, date)

        # 收集所有任务类型（包括所有模式）
        all_tasks = set(seg.get("task-name", "未命名") for seg in daily_segments)
        self.legend.update_legend(all_tasks)


# --- 演示集成 ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("专注时间轴 - 重构版")
        self.setGeometry(100, 100, 800, 400)

        self.timeline = TimelineWidget()
        self.setCentralWidget(self.timeline)

        # 加载数据
        self._load_data()

    def _load_data(self):
        if not os.path.exists(DATA_PATH):
            return

        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 加载最近一天的数据
        if data:
            latest_date = sorted(data.keys())[-1]
            daily_segments = data[latest_date]
            self.timeline.set_data(daily_segments, latest_date)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
