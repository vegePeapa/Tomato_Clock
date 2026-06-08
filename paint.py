import sys, json, os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QMainWindow, QLabel,
                             QToolTip, QFrame, QGridLayout, QScrollArea)
from PyQt6.QtGui import QPainter, QColor, QFont, QFontDatabase, QPen, QBrush, QLinearGradient
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
        self.hide()

    def show_tooltip(self, html_text, global_pos, border_color=None):
        """显示工具提示在指定全局位置"""
        color_hex = border_color.name() if border_color else "#4ecca3"
        self.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(255, 255, 255, 0.98);
                color: #2c3e50;
                border: 2px solid {color_hex};
                border-radius: 10px;
                padding: 12px;
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
                font-size: 12px;
            }}
        """)
        self.setText(html_text)
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
        "做作业": QColor(59, 130, 246, 220),    # 蓝色
        "项目": QColor(244, 63, 94, 220),       # 玫瑰红 (更现代)
        "练习": QColor(16, 185, 129, 220),      # 翡翠绿
        "阅读": QColor(139, 92, 246, 220),      # 紫色
        "运动": QColor(249, 115, 22, 220),      # 橙色
        "休息": QColor(45, 212, 191, 180)       # 舒适的淡青色
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
        self.segment_rects = []  # 存储绘制的矩形
        self.segment_data_indices = []  # 存储每个矩形对应的原始数据索引
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
        self.segment_data_indices = []  # 重置索引映射

        # 为当天的任务分配唯一颜色
        self._assign_daily_colors(daily_segments)

        self.update()

    def set_time_range(self, start_hour, end_hour):
        self.start_hour = max(0, min(24, start_hour))
        self.end_hour = max(1, min(24, end_hour))
        if self.start_hour >= self.end_hour:
            self.end_hour = min(24, self.start_hour + 1)
        self.update()

    def _update_active_task_types(self):
        pass  # 不再需要，任务类型由图例widget管理

    def _assign_daily_colors(self, daily_segments: list):
        """为当天的任务分配唯一颜色，避免同一天内颜色冲突"""
        # 清空之前的颜色映射（重新分配）
        self.custom_task_colors = {}

        # 收集当天所有唯一的任务名称
        task_names = set()
        for segment in daily_segments:
            task_name = segment.get("task-name", "未命名")
            if task_name not in self.TASK_COLORS:  # 跳过预定义颜色的任务
                task_names.add(task_name)

        # 为每个任务分配唯一的颜色索引
        colors = [
            QColor(6, 182, 212, 220),        # 青色
            QColor(236, 72, 153, 220),       # 粉色
            QColor(20, 184, 166, 220),       # 蓝绿色
            QColor(245, 158, 11, 220),       # 琥珀色
            QColor(139, 92, 246, 220),       # 靛蓝色
            QColor(234, 179, 8, 220),        # 黄色
            QColor(244, 63, 94, 220),        # 玫瑰红
            QColor(16, 185, 129, 220),       # 翡翠绿
            QColor(99, 102, 241, 220),       # 靛青色
            QColor(251, 146, 60, 220),       # 热橙色
            QColor(14, 165, 233, 220),       # 天蓝色
            QColor(168, 85, 247, 220),       # 紫色
            QColor(217, 70, 239, 220),       # 品红色
            QColor(34, 197, 94, 220),        # 鲜绿色
            QColor(251, 191, 36, 220),       # 金黄色
            QColor(45, 212, 191, 220),       # 青绿色
            QColor(251, 113, 133, 220),      # 粉红色
            QColor(167, 139, 250, 220),      # 淡紫色
            QColor(134, 239, 172, 220),      # 薄荷绿
            QColor(253, 186, 116, 220)       # 桃橙色
        ]

        # 按任务名称排序，确保分配顺序一致
        sorted_tasks = sorted(task_names)

        # 为每个任务分配颜色（如果任务数超过颜色数，循环使用）
        for i, task_name in enumerate(sorted_tasks):
            color_index = i % len(colors)
            self.custom_task_colors[task_name] = colors[color_index]

    def _get_task_color(self, task_name):
        """获取任务颜色 - 颜色已在 _assign_daily_colors 中分配"""
        if task_name in self.TASK_COLORS:
            return self.TASK_COLORS[task_name]
        # 返回已分配 of 颜色，如果不存在则返回默认颜色
        return self.custom_task_colors.get(task_name, self.DEFAULT_COLOR)

    def _get_task_hover_color(self, task_name):
        base_color = self._get_task_color(task_name)
        if task_name in self.HOVER_COLORS:
            return self.HOVER_COLORS[task_name]
        r, g, b, _ = base_color.getRgb()
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        return QColor(r, g, b, 255)

    def _get_gradient_colors(self, base_color):
        """生成柔和的双色微渐变"""
        r, g, b, a = base_color.getRgb()
        lr = min(255, int(r + (255 - r) * 0.22))
        lg = min(255, int(g + (255 - g) * 0.22))
        lb = min(255, int(b + (255 - b) * 0.22))
        dr = max(0, int(r * 0.88))
        dg = max(0, int(g * 0.88))
        db = max(0, int(b * 0.88))
        return QColor(lr, lg, lb, a), QColor(dr, dg, db, a)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 设置固定宽度，确保24小时有足够显示空间
        required_width = 960
        if self.width() < required_width:
            self.setFixedWidth(required_width)

        width = self.width()
        height = self.height()

        # 1. 绘制卡片背景板
        card_rect = QRect(10, 10, width - 20, height - 20)
        card_grad = QLinearGradient(
            float(card_rect.left()), float(card_rect.top()),
            float(card_rect.right()), float(card_rect.bottom())
        )
        card_grad.setColorAt(0.0, QColor("#ffffff"))
        card_grad.setColorAt(1.0, QColor("#f6faf7"))

        
        painter.setBrush(card_grad)
        painter.setPen(QPen(QColor("#dfeae2"), 1.5))
        painter.drawRoundedRect(card_rect, 12, 12)

        margin_left = 50
        margin_right = 20
        margin_top = 35
        margin_bottom = 45
        bar_height = 70

        content_rect = QRect(margin_left, margin_top,
                            width - margin_left - margin_right,
                            height - margin_top - margin_bottom - bar_height)

        # 2. 绘制时间轴轨道背景
        self._draw_track_background(painter, content_rect, bar_height, margin_bottom)
        # 3. 绘制垂直网格辅助线
        self._draw_grid_lines(painter, content_rect, bar_height, margin_bottom)
        # 4. 绘制任务段色块
        self._draw_segments(painter, content_rect, bar_height, margin_bottom)
        # 5. 绘制底部时间刻度轴
        self._draw_time_axis(painter, content_rect, margin_bottom)

    def _draw_track_background(self, painter, content_rect, bar_height, margin_bottom):
        """绘制贯穿 24 小时的精美底轨"""
        bar_y = content_rect.bottom() + margin_bottom - bar_height - 10
        track_rect = QRect(content_rect.x(), bar_y, content_rect.width(), bar_height)
        
        track_grad = QLinearGradient(
            float(track_rect.left()), float(track_rect.top()),
            float(track_rect.left()), float(track_rect.bottom())
        )
        track_grad.setColorAt(0.0, QColor("#eef4f0"))
        track_grad.setColorAt(1.0, QColor("#f4f9f6"))

        
        painter.setBrush(track_grad)
        painter.setPen(QPen(QColor("#d4e4db"), 1, Qt.PenStyle.SolidLine))
        painter.drawRoundedRect(track_rect, 8, 8)

    def _draw_time_axis(self, painter, content_rect, margin_bottom):
        axis_x = content_rect.left()
        axis_y = content_rect.bottom() + margin_bottom

        # 绘制主轴线
        painter.setPen(QPen(QColor("#b5c8be"), 1.8))
        painter.drawLine(axis_x, axis_y, content_rect.right(), axis_y)

        hour_range = self.end_hour - self.start_hour
        if hour_range <= 0:
            return

        # 刻度图标映射
        icons = {
            0: "🌙",
            4: "🌌",
            8: "🌅",
            12: "☀️",
            16: "🌇",
            20: "🌃",
            24: "🌙"
        }

        content_width = content_rect.width()
        for hour in range(self.start_hour, self.end_hour + 1):
            normalized_time = (hour - self.start_hour) / hour_range
            x = content_rect.x() + int(normalized_time * content_width)

            is_major = (hour % 4 == 0)
            
            if is_major:
                # 绘制主刻度线
                painter.setPen(QPen(QColor("#8fae9e"), 1.5))
                painter.drawLine(x, axis_y, x, axis_y + 6)

                # 绘制时间与精美图标
                painter.setPen(QColor("#406050"))
                painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))
                
                icon = icons.get(hour, "")
                label_text = f"{icon} {hour:02d}:00" if icon else f"{hour:02d}:00"
                
                rect = QRect(x - 35, axis_y + 8, 70, 20)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label_text)
            else:
                # 绘制次要刻度线
                painter.setPen(QPen(QColor("#c2d5cb"), 1))
                painter.drawLine(x, axis_y, x, axis_y + 3)

    def _draw_segments(self, painter, content_rect, bar_height, margin_bottom):
        self.segment_rects = []
        self.segment_data_indices = []  # 重置索引映射
        bar_y = content_rect.bottom() + margin_bottom - bar_height - 10

        hour_range = self.end_hour - self.start_hour
        if hour_range <= 0:
            return

        content_width = content_rect.width()

        # 绘制所有模式的片段
        for data_index, segment in enumerate(self.segments_data):
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
                self.segment_data_indices.append(data_index)  # 记录原始数据索引

                task_name = segment.get("task-name", "未命名")
                mode = segment.get("mode", "专注")

                # 根据模式调整颜色显示
                base_color = self._get_task_color(task_name)

                if mode == TimerMode.FOCUS or mode == TimerMode.CANCELLED:
                    # 专注模式：使用任务特定分配色
                    color = QColor(base_color)
                    color.setAlpha(220)
                elif mode == TimerMode.RELAX:
                    # 休息模式：使用清新的薄荷浅绿
                    color = QColor(162, 217, 206)
                    color.setAlpha(180)
                else:
                    # 其他模式：默认半透明
                    color = QColor(base_color)
                    color.setAlpha(160)

                is_hovered = (self.segment_rects.index(segment_rect) == self.hovered_segment_index)

                # 线性渐变填充
                grad = QLinearGradient(
                    float(segment_rect.left()), float(segment_rect.top()),
                    float(segment_rect.left()), float(segment_rect.bottom())
                )
                c1, c2 = self._get_gradient_colors(color)

                
                if is_hovered:
                    # 悬浮时色块轻微提亮
                    c1 = QColor(min(255, int(c1.red() * 1.12)), min(255, int(c1.green() * 1.12)), min(255, int(c1.blue() * 1.12)), 255)
                    c2 = QColor(min(255, int(c2.red() * 1.12)), min(255, int(c2.green() * 1.12)), min(255, int(c2.blue() * 1.12)), 255)
                
                grad.setColorAt(0.0, c1)
                grad.setColorAt(1.0, c2)
                painter.setBrush(grad)

                # 边框绘制
                if is_hovered:
                    # 发光轮廓笔触
                    painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 255), 2.2, Qt.PenStyle.SolidLine))
                else:
                    # 默认精致白色微透细边框
                    painter.setPen(QPen(QColor(255, 255, 255, 170), 1))

                painter.drawRoundedRect(segment_rect, 6, 6)

                # 当宽度足够时在内部绘制任务名
                if segment_width > 55:
                    painter.save()
                    painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.Weight.Bold))
                    painter.setPen(QColor(255, 255, 255))
                    
                    metrics = painter.fontMetrics()
                    elided_text = metrics.elidedText(task_name, Qt.TextElideMode.ElideRight, segment_width - 10)
                    painter.drawText(segment_rect, Qt.AlignmentFlag.AlignCenter, elided_text)
                    painter.restore()

    def _draw_grid_lines(self, painter, content_rect, bar_height, margin_bottom):
        bar_y = content_rect.bottom() + margin_bottom - bar_height - 10

        hour_range = self.end_hour - self.start_hour
        if hour_range <= 0:
            return

        content_width = content_rect.width()
        
        # 极浅网格线
        painter.setPen(QPen(QColor("#dbe5df"), 1, Qt.PenStyle.SolidLine))

        for hour in range(self.start_hour, self.end_hour + 1):
            normalized_time = (hour - self.start_hour) / hour_range
            x = content_rect.x() + int(normalized_time * content_width)
            
            # 只在轨道范围及其上下微微延展绘制精细垂直虚线
            painter.drawLine(x, bar_y - 8, x, bar_y + bar_height + 8)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        self.hovered_segment_index = -1

        for i, rect in enumerate(self.segment_rects):
            if rect.contains(pos):
                self.hovered_segment_index = i
                # 使用索引映射获取正确的原始数据索引
                data_index = self.segment_data_indices[i]
                segment = self.segments_data[data_index]  # 使用正确的索引

                task_name = segment.get("task-name", "未命名")
                mode = segment.get("mode", "专注")
                start = segment.get("start", "")
                end = segment.get("end", "")
                duration = segment.get("duration", 0)
                minutes = duration // 60

                # 提取模式类型及样式设定
                is_focus = "专注" in mode
                mode_icon = "🎯" if is_focus else "☕"
                mode_color = "#2e7d32" if is_focus else "#148f77"
                
                # HTML 富文本排版
                tooltip_html = f"""
                <table style='border-spacing: 0px 4px; font-size: 11px;'>
                    <tr><td colspan='2' style='font-size: 13px; font-weight: bold; color: #1b4332; padding-bottom: 4px;'>🏷️ {task_name}</td></tr>
                    <tr><td style='color: #7f8c8d; font-weight: bold; padding-right: 6px;'>🧭 模式:</td><td style='color: {mode_color}; font-weight: bold;'>{mode_icon} {mode}</td></tr>
                    <tr><td style='color: #7f8c8d; font-weight: bold;'>⏰ 时间:</td><td style='color: #2c3e50;'>{start} - {end}</td></tr>
                    <tr><td style='color: #7f8c8d; font-weight: bold;'>⏳ 时长:</td><td style='color: #2e7d32; font-weight: bold;'>{minutes} 分钟</td></tr>
                </table>
                """

                # 获取对应的色块边框颜色
                task_color = self._get_task_color(task_name)
                if mode == TimerMode.RELAX:
                    task_color = QColor(162, 217, 206)

                # 使用自定义工具提示，传递全局坐标和主题颜色
                global_pos = event.globalPosition().toPoint()
                self.tooltip.show_tooltip(tooltip_html, global_pos, task_color)
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

    def update_legend(self, task_types, custom_colors=None):
        """更新图例内容

        Args:
            task_types: 任务类型集合
            custom_colors: 来自 TimelineCanvas 的自定义颜色映射字典
        """
        # 保存颜色映射
        self.custom_colors = custom_colors or {}

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

            # 颜色块 - 优先使用传入的颜色映射
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
        """获取任务颜色 - 优先使用 TimelineCanvas 分配的颜色"""
        # 1. 优先检查预定义颜色
        if task_name in TimelineCanvas.TASK_COLORS:
            return TimelineCanvas.TASK_COLORS[task_name]

        # 2. 使用传入的颜色映射
        if task_name in self.custom_colors:
            return self.custom_colors[task_name]

        # 3. 后备方案：使用哈希分配（应该不会到达这里）
        colors = [
            QColor(6, 182, 212, 230), QColor(236, 72, 153, 230),
            QColor(20, 184, 166, 230), QColor(245, 158, 11, 230),
            QColor(139, 92, 246, 230), QColor(234, 179, 8, 230),
            QColor(244, 63, 94, 230), QColor(16, 185, 129, 230),
            QColor(99, 102, 241, 230), QColor(251, 146, 60, 230),
            QColor(14, 165, 233, 230), QColor(168, 85, 247, 230),
            QColor(217, 70, 239, 230), QColor(34, 197, 94, 230),
            QColor(251, 191, 36, 230)
        ]
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
                background-color: #eef3f0;
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background-color: #a5d6a7;
                border-radius: 4px;
                min-width: 40px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #81c784;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
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
        # 传递 canvas 的颜色映射给 legend，确保颜色一致
        self.legend.update_legend(all_tasks, self.canvas.custom_task_colors)



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
