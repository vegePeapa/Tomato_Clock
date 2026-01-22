"""
可爱番茄时间显示组件 - Cute Tomato Timer Widget
创建一个Q版可爱的番茄倒计时动画
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QFont, QRadialGradient, QPen, QLinearGradient
import math


class TomatoTimerWidget(QWidget):
    """
    可爱番茄时间显示组件
    核心特性：
    - Q版圆润番茄造型
    - 表情随时间变化（手绘风格）
    - 呼吸和摇晃动画
    - 时间进度环形显示
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 状态变量
        self._total_seconds = 25 * 60  # 总时间（秒）
        self._remaining_seconds = 25 * 60  # 剩余时间（秒）
        self._is_running = False
        self._mode = "focus"  # focus, relax, cancelled

        # 动画变量
        self._breath_value = 0.0  # 呼吸值（0-1）
        self._breath_direction = 1  # 呼吸方向
        self._sway_angle = 0.0  # 摇晃角度
        self._leaf_wave = 0.0  # 叶子摆动

        # 设置最小尺寸
        self.setMinimumSize(300, 300)

        # 启动动画计时器（60 FPS）
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._update_animation)
        self._animation_timer.start(16)  # ~60 FPS

        # 启动呼吸计时器
        self._breath_timer = QTimer()
        self._breath_timer.timeout.connect(self._update_breath)
        self._breath_timer.start(30)  # 呼吸速度

    def set_time(self, total_seconds, remaining_seconds):
        """设置时间"""
        self._total_seconds = total_seconds
        self._remaining_seconds = remaining_seconds
        self.update()

    def set_mode(self, mode):
        """设置模式"""
        self._mode = mode
        self.update()

    def set_running(self, is_running):
        """设置运行状态"""
        self._is_running = is_running

    def _update_animation(self):
        """更新摇晃和叶子动画"""
        if self._is_running:
            # 运行时摇晃更快
            self._sway_angle += 0.03
            self._leaf_wave += 0.05
        else:
            # 暂停时摇晃缓慢
            self._sway_angle += 0.008
            self._leaf_wave += 0.02
        self.update()

    def _update_breath(self):
        """更新呼吸效果"""
        step = 0.008
        self._breath_value += step * self._breath_direction

        if self._breath_value >= 1.0:
            self._breath_value = 1.0
            self._breath_direction = -1
        elif self._breath_value <= 0.0:
            self._breath_value = 0.0
            self._breath_direction = 1

        self.update()

    def paintEvent(self, event):
        """绘制组件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取尺寸
        width = self.width()
        height = self.height()
        center = QPointF(width / 2, height / 2)

        # 根据模式绘制
        if self._mode == "focus":
            self._draw_focus_mode(painter, center)
        elif self._mode == "relax":
            self._draw_relax_mode(painter, center)
        else:  # cancelled
            self._draw_cancelled_mode(painter, center)

    def _draw_focus_mode(self, painter, center):
        """绘制专注模式 - 红色番茄"""
        # 计算基础半径（呼吸效果）
        base_radius = min(self.width(), self.height()) * 0.28
        breath_scale = 1.0 + self._breath_value * 0.05

        # 计算摇晃偏移（暂停时不摇晃）
        if not self._is_running:
            sway_offset = 0
        else:
            sway_offset = math.sin(self._sway_angle) * 3

        # 绘制番茄身体
        tomato_center = QPointF(center.x() + sway_offset, center.y())
        self._draw_tomato_body(painter, tomato_center, base_radius * breath_scale,
                              is_running=self._is_running)

        # 绘制叶子
        self._draw_tomato_leaves(painter, tomato_center, base_radius * breath_scale)

        # 绘制表情
        self._draw_tomato_face(painter, tomato_center, base_radius * breath_scale)

        # 绘制进度环
        if self._total_seconds > 0:
            progress = self._remaining_seconds / self._total_seconds
        else:
            progress = 1.0
        self._draw_progress_ring(painter, center, base_radius * 1.3, progress)

        # 暂停时添加半透明遮罩
        if not self._is_running:
            self._draw_pause_overlay(painter, center, base_radius)

    def _draw_relax_mode(self, painter, center):
        """绘制休息模式 - 橙色番茄"""
        base_radius = min(self.width(), self.height()) * 0.28
        breath_scale = 1.0 + self._breath_value * 0.03
        sway_offset = math.sin(self._sway_angle) * 2

        tomato_center = QPointF(center.x() + sway_offset, center.y())

        # 绘制橙色番茄
        self._draw_tomato_body(painter, tomato_center, base_radius * breath_scale,
                              is_running=self._is_running, is_relax=True)

        # 绘制叶子
        self._draw_tomato_leaves(painter, tomato_center, base_radius * breath_scale)

        # 绘制放松表情
        self._draw_tomato_face(painter, tomato_center, base_radius * breath_scale, is_relax=True)

        # 绘制进度环（绿色）
        if self._total_seconds > 0:
            progress = self._remaining_seconds / self._total_seconds
        else:
            progress = 1.0
        self._draw_progress_ring(painter, center, base_radius * 1.3, progress,
                                ring_color=QColor(102, 187, 106))

    def _draw_cancelled_mode(self, painter, center):
        """绘制取消模式 - 灰色番茄"""
        base_radius = min(self.width(), self.height()) * 0.25

        # 暂停时不摇晃
        if not self._is_running:
            sway_offset = 0
        else:
            sway_offset = math.sin(self._sway_angle) * 1.5

        tomato_center = QPointF(center.x() + sway_offset, center.y())

        # 绘制灰色番茄（暂停时更暗）
        self._draw_tomato_body(painter, tomato_center, base_radius,
                              is_running=self._is_running, is_cancelled=True)

        # 绘制叶子（暂停时更下垂）
        if not self._is_running:
            self._draw_tomato_leaves(painter, tomato_center, base_radius, is_droopy=True, is_paused=True)
        else:
            self._draw_tomato_leaves(painter, tomato_center, base_radius, is_droopy=True)

        # 绘制表情（运行时无聊，暂停时深度睡眠）
        self._draw_tomato_face(painter, tomato_center, base_radius, is_cancelled=True)

        # 虚线环
        pen = QPen(QColor(150, 150, 150, 100), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, base_radius * 1.3, base_radius * 1.3)

        # 暂停时添加半透明遮罩
        if not self._is_running:
            self._draw_pause_overlay(painter, center, base_radius)

    def _draw_tomato_body(self, painter, center, radius, is_running=True,
                         is_relax=False, is_cancelled=False):
        """绘制番茄身体"""
        # 创建番茄形状（稍微扁平的椭圆）
        path = QPainterPath()
        rect = QRectF(center.x() - radius, center.y() - radius * 0.9,
                     radius * 2, radius * 1.8)
        path.addEllipse(rect)

        # 设置渐变色
        if is_cancelled:
            # 灰色
            gradient = QRadialGradient(center, radius)
            gradient.setColorAt(0, QColor(200, 200, 200))
            gradient.setColorAt(0.7, QColor(160, 160, 160))
            gradient.setColorAt(1, QColor(140, 140, 140))
        elif is_relax:
            # 橙色
            gradient = QRadialGradient(center, radius)
            gradient.setColorAt(0, QColor(255, 200, 150))
            gradient.setColorAt(0.7, QColor(255, 160, 100))
            gradient.setColorAt(1, QColor(230, 140, 80))
        else:
            # 红色（根据是否运行调整亮度）
            if is_running:
                bright_offset = 20
            else:
                bright_offset = 0

            gradient = QRadialGradient(center, radius)
            gradient.setColorAt(0, QColor(255 - bright_offset, 100 - bright_offset, 100 - bright_offset))
            gradient.setColorAt(0.5, QColor(230 - bright_offset, 70 - bright_offset, 70 - bright_offset))
            gradient.setColorAt(1, QColor(200 - bright_offset, 50 - bright_offset, 50 - bright_offset))

        painter.fillPath(path, gradient)

        # 添加高光效果
        highlight_path = QPainterPath()
        highlight_rect = QRectF(center.x() - radius * 0.4, center.y() - radius * 0.6,
                               radius * 0.5, radius * 0.4)
        highlight_path.addEllipse(highlight_rect)

        highlight_gradient = QRadialGradient(
            QPointF(center.x() - radius * 0.2, center.y() - radius * 0.5), radius * 0.3
        )
        highlight_gradient.setColorAt(0, QColor(255, 255, 255, 180))
        highlight_gradient.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillPath(highlight_path, highlight_gradient)

    def _draw_tomato_leaves(self, painter, center, radius, is_droopy=False, is_paused=False):
        """绘制番茄顶部的叶子"""
        leaf_color = QColor(80, 180, 80)

        # 叶子数量和位置
        num_leaves = 5
        leaf_angle_offset = self._leaf_wave

        # 暂停时叶子变暗
        if not self._is_running or is_paused:
            leaf_color = QColor(50, 120, 50)

        for i in range(num_leaves):
            angle = (2 * math.pi / num_leaves) * i - math.pi / 2 + leaf_angle_offset * 0.1

            if is_droopy:
                # 下垂的叶子（暂停时下垂更严重）
                droop_amount = 0.6 if is_paused or not self._is_running else 0.15
                angle += math.sin(leaf_angle_offset + i) * droop_amount

            leaf_length = radius * 0.4

            # 叶子中心点
            leaf_center_x = center.x() + math.cos(angle) * radius * 0.6
            leaf_center_y = center.y() + math.sin(angle) * radius * 0.5

            # 绘制叶子
            leaf_path = QPainterPath()
            leaf_path.moveTo(leaf_center_x, leaf_center_y)

            # 叶子的波浪形状
            control1_x = leaf_center_x + math.cos(angle + 0.5) * leaf_length
            control1_y = leaf_center_y + math.sin(angle + 0.5) * leaf_length
            control2_x = leaf_center_x + math.cos(angle - 0.5) * leaf_length
            control2_y = leaf_center_y + math.sin(angle - 0.5) * leaf_length

            leaf_path.quadTo(QPointF(control1_x, control1_y),
                           QPointF(leaf_center_x + math.cos(angle) * leaf_length * 0.8,
                                  leaf_center_y + math.sin(angle) * leaf_length * 0.8))
            leaf_path.quadTo(QPointF(control2_x, control2_y),
                           QPointF(leaf_center_x, leaf_center_y))

            painter.fillPath(leaf_path, leaf_color)

    def _draw_tomato_face(self, painter, center, radius,
                         is_relax=False, is_cancelled=False):
        """绘制番茄表情（手绘风格）"""
        # 计算时间比例，决定表情
        if self._total_seconds > 0:
            time_ratio = self._remaining_seconds / self._total_seconds
        else:
            time_ratio = 1.0

        # 眼睛位置
        eye_y = center.y() - radius * 0.1
        left_eye_x = center.x() - radius * 0.25
        right_eye_x = center.x() + radius * 0.25
        eye_size = radius * 0.12

        # 根据时间比例和模式绘制表情
        if is_cancelled:
            # 取消模式表情
            if not self._is_running:
                # 暂停时：深度睡眠 - = = 眼睛 + o 嘴
                painter.setPen(QPen(QColor(60, 40, 40), 2.5))

                # 左眼：横线 =
                painter.drawLine(QPointF(left_eye_x - eye_size * 0.6, eye_y),
                               QPointF(left_eye_x + eye_size * 0.6, eye_y))
                # 右眼：横线 =
                painter.drawLine(QPointF(right_eye_x - eye_size * 0.6, eye_y),
                               QPointF(right_eye_x + eye_size * 0.6, eye_y))

                # 小圆点嘴 o
                mouth_y = center.y() + radius * 0.3
                painter.setBrush(QColor(60, 40, 40))
                painter.drawEllipse(QPointF(center.x(), mouth_y), eye_size * 0.4, eye_size * 0.3)
            else:
                # 运行时：无聊表情 - 小圆点眼睛，直线嘴
                painter.setPen(QPen(QColor(80, 50, 50), 3))
                painter.setBrush(QColor(80, 50, 50))
                painter.drawEllipse(QPointF(left_eye_x, eye_y), eye_size * 0.5, eye_size * 0.5)
                painter.drawEllipse(QPointF(right_eye_x, eye_y), eye_size * 0.5, eye_size * 0.5)

                # 直线嘴
                mouth_y = center.y() + radius * 0.3
                painter.setPen(QPen(QColor(80, 50, 50), 3))
                painter.drawLine(QPointF(left_eye_x, mouth_y), QPointF(right_eye_x, mouth_y))

        elif is_relax:
            # 放松表情 - 闭眼（弯弯的），微笑
            painter.setPen(QPen(QColor(80, 50, 50), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            # 闭眼（弯弯的弧线）
            painter.drawArc(QRectF(left_eye_x - eye_size, eye_y - eye_size * 0.5,
                                 eye_size * 2, eye_size), 0, 180 * 16)
            painter.drawArc(QRectF(right_eye_x - eye_size, eye_y - eye_size * 0.5,
                                 eye_size * 2, eye_size), 0, 180 * 16)

            # 微笑
            mouth_y = center.y() + radius * 0.3
            smile_path = QPainterPath()
            smile_path.moveTo(left_eye_x, mouth_y)
            smile_path.quadTo(QPointF(center.x(), mouth_y + radius * 0.15),
                             QPointF(right_eye_x, mouth_y))
            painter.drawPath(smile_path)

        # 暂停时的可爱睡觉表情
        elif not self._is_running and not is_cancelled and not is_relax:
            # 闭眼（弯弯的弧线，像睡觉一样）
            painter.setPen(QPen(QColor(60, 30, 30), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            # 左眼（弯弯的）
            painter.drawArc(QRectF(left_eye_x - eye_size, eye_y - eye_size * 0.5,
                                 eye_size * 2, eye_size), 0, 180 * 16)
            # 右眼（弯弯的）
            painter.drawArc(QRectF(right_eye_x - eye_size, eye_y - eye_size * 0.5,
                                 eye_size * 2, eye_size), 0, 180 * 16)

            # 温柔微笑
            mouth_y = center.y() + radius * 0.3
            smile_path = QPainterPath()
            smile_path.moveTo(left_eye_x + radius * 0.05, mouth_y)
            smile_path.quadTo(QPointF(center.x(), mouth_y + radius * 0.12),
                             QPointF(right_eye_x - radius * 0.05, mouth_y))
            painter.setPen(QPen(QColor(60, 30, 30), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(smile_path)

            # 绘制小巧精致的Zzz睡觉气泡
            self._draw_sleep_bubble(painter, center, radius)

        else:
            # 专注模式 - 根据时间比例变化
            painter.setPen(QPen(QColor(80, 50, 50), 3))
            painter.setBrush(QColor(80, 50, 50))

            if time_ratio > 0.7:
                # 时间充足 - 开心大眼睛
                painter.drawEllipse(QPointF(left_eye_x, eye_y), eye_size, eye_size * 1.2)
                painter.drawEllipse(QPointF(right_eye_x, eye_y), eye_size, eye_size * 1.2)

                # 眼睛高光
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255))
                painter.drawEllipse(QPointF(left_eye_x + eye_size * 0.3, eye_y - eye_size * 0.3),
                                  eye_size * 0.3, eye_size * 0.3)
                painter.drawEllipse(QPointF(right_eye_x + eye_size * 0.3, eye_y - eye_size * 0.3),
                                  eye_size * 0.3, eye_size * 0.3)

                # 微笑
                mouth_y = center.y() + radius * 0.35
                smile_path = QPainterPath()
                smile_path.moveTo(left_eye_x, mouth_y)
                smile_path.quadTo(QPointF(center.x(), mouth_y + radius * 0.1),
                                 QPointF(right_eye_x, mouth_y))
                painter.setPen(QPen(QColor(80, 50, 50), 3))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(smile_path)

            elif time_ratio > 0.3:
                # 时间过半 - 专注表情（眼睛变小）
                painter.setPen(QPen(QColor(80, 50, 50), 3))
                painter.setBrush(QColor(80, 50, 50))
                painter.drawEllipse(QPointF(left_eye_x, eye_y), eye_size * 0.7, eye_size * 0.9)
                painter.drawEllipse(QPointF(right_eye_x, eye_y), eye_size * 0.7, eye_size * 0.9)

                # 眼睛高光
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255))
                painter.drawEllipse(QPointF(left_eye_x + eye_size * 0.2, eye_y - eye_size * 0.2),
                                  eye_size * 0.25, eye_size * 0.25)
                painter.drawEllipse(QPointF(right_eye_x + eye_size * 0.2, eye_y - eye_size * 0.2),
                                  eye_size * 0.25, eye_size * 0.25)

                # 咬嘴表情
                mouth_y = center.y() + radius * 0.35
                painter.setPen(QPen(QColor(80, 50, 50), 3))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawLine(QPointF(left_eye_x + radius * 0.1, mouth_y),
                               QPointF(right_eye_x - radius * 0.1, mouth_y))

            else:
                # 时间快到了 - 紧张表情（眼睛很小，有汗水）
                painter.setPen(QPen(QColor(80, 50, 50), 3))
                painter.setBrush(QColor(80, 50, 50))
                painter.drawEllipse(QPointF(left_eye_x, eye_y), eye_size * 0.5, eye_size * 0.7)
                painter.drawEllipse(QPointF(right_eye_x, eye_y), eye_size * 0.5, eye_size * 0.7)

                # 汗水滴（在右边眼睛旁边）
                if self._is_running:
                    sweat_x = right_eye_x + eye_size * 1.5
                    sweat_y = eye_y - eye_size * 0.5
                    sweat_path = QPainterPath()
                    sweat_path.moveTo(sweat_x, sweat_y)
                    sweat_path.lineTo(sweat_x, sweat_y + eye_size)
                    sweat_path.quadTo(QPointF(sweat_x - eye_size * 0.3, sweat_y + eye_size * 1.3),
                                     QPointF(sweat_x - eye_size * 0.6, sweat_y + eye_size))
                    sweat_path.lineTo(sweat_x, sweat_y)
                    painter.setBrush(QColor(150, 200, 255))
                    painter.fillPath(sweat_path, QColor(150, 200, 255))

                # 波浪嘴（紧张）
                mouth_y = center.y() + radius * 0.35
                wave_path = QPainterPath()
                wave_path.moveTo(left_eye_x + radius * 0.05, mouth_y)
                wave_path.lineTo(left_eye_x + radius * 0.25, mouth_y - radius * 0.05)
                wave_path.lineTo(center.x(), mouth_y + radius * 0.05)
                wave_path.lineTo(right_eye_x - radius * 0.25, mouth_y - radius * 0.05)
                wave_path.lineTo(right_eye_x - radius * 0.05, mouth_y)
                painter.setPen(QPen(QColor(80, 50, 50), 2.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(wave_path)

    def _draw_sleep_bubble(self, painter, center, radius):
        """绘制Zzz睡觉气泡"""
        # 气泡位置（番茄右上角）
        bubble_x = center.x() + radius * 0.6
        bubble_y = center.y() - radius * 0.5

        # 绘制半透明气泡背景
        bubble_path = QPainterPath()
        bubble_rect = QRectF(bubble_x, bubble_y - radius * 0.3,
                            radius * 0.5, radius * 0.4)
        bubble_path.addRoundedRect(bubble_rect, 8, 8)

        bubble_color = QColor(200, 220, 255, 120)
        painter.fillPath(bubble_path, bubble_color)

        # 绘制Zzz文字
        painter.setPen(QColor(100, 100, 150))
        font = QFont("Microsoft YaHei", int(radius * 0.15), QFont.Weight.Bold)
        painter.setFont(font)

        # 第一个Z（大）
        z1_rect = QRectF(bubble_x + radius * 0.08, bubble_y - radius * 0.15,
                         radius * 0.15, radius * 0.15)
        painter.drawText(z1_rect, Qt.AlignmentFlag.AlignCenter, "Z")

        # 第二个Z（中）
        z2_rect = QRectF(bubble_x + radius * 0.18, bubble_y - radius * 0.22,
                         radius * 0.12, radius * 0.12)
        font2 = QFont("Microsoft YaHei", int(radius * 0.12), QFont.Weight.Bold)
        painter.setFont(font2)
        painter.drawText(z2_rect, Qt.AlignmentFlag.AlignCenter, "Z")

        # 第三个Z（小）
        z3_rect = QRectF(bubble_x + radius * 0.26, bubble_y - radius * 0.28,
                         radius * 0.1, radius * 0.1)
        font3 = QFont("Microsoft YaHei", int(radius * 0.1), QFont.Weight.Bold)
        painter.setFont(font3)
        painter.drawText(z3_rect, Qt.AlignmentFlag.AlignCenter, "z")

    def _draw_pause_overlay(self, painter, center, radius):
        """绘制通用的暂停半透明遮罩"""
        # 创建半透明遮罩层
        overlay_path = QPainterPath()
        overlay_rect = QRectF(center.x() - radius * 1.2, center.y() - radius * 1.2,
                             radius * 2.4, radius * 2.4)
        overlay_path.addEllipse(overlay_rect)

        # 半透明深色遮罩（让番茄看起来"睡着了"）
        overlay_color = QColor(0, 0, 0, 40)
        painter.fillPath(overlay_path, overlay_color)

        # 在番茄中央绘制暂停符号 ||
        pause_bar_width = radius * 0.15
        pause_bar_height = radius * 0.4
        pause_spacing = radius * 0.15

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 180))

        # 左边的竖线
        left_bar = QRectF(center.x() - pause_spacing/2 - pause_bar_width,
                         center.y() - pause_bar_height/2,
                         pause_bar_width, pause_bar_height)
        painter.drawRoundedRect(left_bar, 3, 3)

        # 右边的竖线
        right_bar = QRectF(center.x() + pause_spacing/2,
                          center.y() - pause_bar_height/2,
                          pause_bar_width, pause_bar_height)
        painter.drawRoundedRect(right_bar, 3, 3)

    def _draw_progress_ring(self, painter, center, radius, progress,
                           ring_color=None):
        """绘制进度环"""
        if ring_color is None:
            ring_color = QColor(78, 204, 163)

        # 环的宽度
        ring_width = 10

        # 背景环（半透明）
        background_pen = QPen(QColor(200, 200, 200, 60), ring_width)
        background_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(background_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

        # 进度环
        if progress > 0:
            progress_pen = QPen(ring_color, ring_width)
            progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(progress_pen)

            # 绘制弧形
            rect_x = center.x() - radius
            rect_y = center.y() - radius
            rect_size = radius * 2

            # 从12点方向开始（-90度）
            start_angle = 90 * 16  # PyQt6 使用 1/16 度为单位
            span_angle = int(-progress * 360 * 16)

            painter.drawArc(int(rect_x), int(rect_y), int(rect_size), int(rect_size),
                           start_angle, span_angle)
