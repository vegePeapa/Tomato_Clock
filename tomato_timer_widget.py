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
        """绘制精致自然的番茄身体（具有 3D 球体质感、环境反光和柔和阴影）"""
        # 1. 绘制底部软阴影，使番茄具有悬浮立体感
        shadow_path = QPainterPath()
        shadow_rect = QRectF(center.x() - radius * 0.95, center.y() + radius * 0.75,
                             radius * 1.9, radius * 0.25)
        shadow_path.addEllipse(shadow_rect)
        shadow_gradient = QRadialGradient(
            QPointF(center.x(), center.y() + radius * 0.87), radius * 0.9
        )
        shadow_gradient.setColorAt(0, QColor(0, 0, 0, 50))
        shadow_gradient.setColorAt(0.6, QColor(0, 0, 0, 18))
        shadow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillPath(shadow_path, shadow_gradient)

        # 2. 绘制番茄主轮廓（稍扁平的饱满椭圆）
        path = QPainterPath()
        rect = QRectF(center.x() - radius, center.y() - radius * 0.9,
                     radius * 2, radius * 1.8)
        path.addEllipse(rect)

        # 设置 3D 渐变色光源（位于左上方）
        grad_center = QPointF(center.x() - radius * 0.25, center.y() - radius * 0.25)
        
        if is_cancelled:
            # 灰色模式 3D 渐变
            gradient = QRadialGradient(grad_center, radius * 1.25)
            gradient.setColorAt(0, QColor(235, 235, 235))
            gradient.setColorAt(0.5, QColor(170, 170, 170))
            gradient.setColorAt(0.85, QColor(125, 125, 125))
            gradient.setColorAt(1, QColor(95, 95, 95))
        elif is_relax:
            # 橙色模式 3D 渐变（亮橙到红橙）
            gradient = QRadialGradient(grad_center, radius * 1.25)
            gradient.setColorAt(0, QColor(255, 220, 160))
            gradient.setColorAt(0.4, QColor(255, 150, 80))
            gradient.setColorAt(0.85, QColor(225, 95, 40))
            gradient.setColorAt(1, QColor(175, 65, 25))
        else:
            # 正常红色模式 3D 渐变（粉红到深红，根据运行状态调整亮度）
            bright = 0 if is_running else -15
            gradient = QRadialGradient(grad_center, radius * 1.25)
            gradient.setColorAt(0, QColor(255 + bright, 115 + bright, 105 + bright))
            gradient.setColorAt(0.4, QColor(235 + bright, 65 + bright, 55 + bright))
            gradient.setColorAt(0.85, QColor(190 + bright, 30 + bright, 25 + bright))
            gradient.setColorAt(1, QColor(145 + bright, 15 + bright, 15 + bright))

        painter.fillPath(path, gradient)

        # 3. 绘制右下侧的反光（Reflex Light），增加物体环境融合感
        reflex_path = QPainterPath()
        reflex_path.addEllipse(rect)
        reflex_gradient = QRadialGradient(
            QPointF(center.x() + radius * 0.6, center.y() + radius * 0.5), radius * 0.7
        )
        if is_cancelled:
            reflex_gradient.setColorAt(0, QColor(255, 255, 255, 35))
            reflex_gradient.setColorAt(1, QColor(255, 255, 255, 0))
        elif is_relax:
            reflex_gradient.setColorAt(0, QColor(255, 255, 180, 55))
            reflex_gradient.setColorAt(1, QColor(255, 255, 180, 0))
        else:
            reflex_gradient.setColorAt(0, QColor(255, 180, 180, 60))
            reflex_gradient.setColorAt(1, QColor(255, 180, 180, 0))
        painter.fillPath(reflex_path, reflex_gradient)

        # 4. 绘制主要柔和高光
        highlight1_path = QPainterPath()
        h1_rect = QRectF(center.x() - radius * 0.45, center.y() - radius * 0.65,
                         radius * 0.6, radius * 0.4)
        highlight1_path.addEllipse(h1_rect)
        h1_grad = QRadialGradient(
            QPointF(center.x() - radius * 0.25, center.y() - radius * 0.5), radius * 0.35
        )
        h1_grad.setColorAt(0, QColor(255, 255, 255, 140))
        h1_grad.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillPath(highlight1_path, h1_grad)

        # 5. 绘制次要晶莹亮斑，呈现质感光泽
        highlight2_path = QPainterPath()
        h2_rect = QRectF(center.x() - radius * 0.3, center.y() - radius * 0.55,
                         radius * 0.15, radius * 0.1)
        highlight2_path.addEllipse(h2_rect)
        painter.fillPath(highlight2_path, QColor(255, 255, 255, 190))

    def _draw_tomato_leaves(self, painter, center, radius, is_droopy=False, is_paused=False):
        """绘制精致自然的番茄顶部叶子与果蒂"""
        # 叶片底色与尖端颜色
        base_green = QColor(46, 125, 50) if (not self._is_running or is_paused) else QColor(56, 142, 60)
        tip_green = QColor(102, 187, 106) if (not self._is_running or is_paused) else QColor(129, 199, 132)
        
        # 1. 绘制果蒂（中心小木质茎，向上并略微向左弯曲）
        stem_path = QPainterPath()
        stem_base_y = center.y() - radius * 0.85
        stem_top_x = center.x() - radius * 0.12
        stem_top_y = center.y() - radius * 1.05
        
        stem_path.moveTo(center.x() - radius * 0.05, stem_base_y)
        stem_path.quadTo(QPointF(center.x() - radius * 0.04, stem_base_y - radius * 0.12),
                         QPointF(stem_top_x, stem_top_y))
        stem_path.lineTo(stem_top_x + radius * 0.08, stem_top_y - radius * 0.02)
        stem_path.quadTo(QPointF(center.x() + radius * 0.05, stem_base_y - radius * 0.1),
                         QPointF(center.x() + radius * 0.05, stem_base_y))
        stem_path.closeSubpath()
        
        stem_grad = QLinearGradient(QPointF(center.x(), stem_base_y), QPointF(stem_top_x, stem_top_y))
        stem_grad.setColorAt(0, QColor(78, 52, 46) if is_paused else QColor(93, 64, 55)) # 木质褐绿
        stem_grad.setColorAt(1, base_green.darker(110))
        painter.fillPath(stem_path, stem_grad)

        # 2. 绘制 5 片舒展有致的放射状叶片（果萼）
        num_leaves = 5
        leaf_angle_offset = self._leaf_wave
        
        for i in range(num_leaves):
            # 5 片叶的固定基本角度偏移
            base_angle = (2 * math.pi / num_leaves) * i - math.pi / 2
            
            # 加入微弱的呼吸/叶片微颤动画效果
            angle = base_angle + math.sin(leaf_angle_offset * 0.5 + i) * 0.05
            
            if is_droopy:
                droop = 0.45 if (is_paused or not self._is_running) else 0.12
                angle += math.sin(leaf_angle_offset + i) * droop

            leaf_len = radius * 0.46
            # 叶片尖端位置
            tip_x = center.x() + math.cos(angle) * (radius * 0.48 + leaf_len * 0.6)
            tip_y = center.y() - radius * 0.82 + math.sin(angle) * (radius * 0.38 + leaf_len * 0.5)
            
            # 叶片连接中心的左/右底角
            base_left_x = center.x() + math.cos(angle - 0.48) * radius * 0.12
            base_left_y = center.y() - radius * 0.85 + math.sin(angle - 0.48) * radius * 0.08
            
            base_right_x = center.x() + math.cos(angle + 0.48) * radius * 0.12
            base_right_y = center.y() - radius * 0.85 + math.sin(angle + 0.48) * radius * 0.08
            
            # 建立一片叶子的弧形边缘路径
            leaf_path = QPainterPath()
            leaf_path.moveTo(base_left_x, base_left_y)
            # 左侧控制点
            ctrl_left_x = center.x() + math.cos(angle - 0.28) * (radius * 0.2 + leaf_len * 0.5)
            ctrl_left_y = center.y() - radius * 0.82 + math.sin(angle - 0.28) * (radius * 0.15 + leaf_len * 0.4)
            leaf_path.quadTo(QPointF(ctrl_left_x, ctrl_left_y), QPointF(tip_x, tip_y))
            
            # 右侧控制点
            ctrl_right_x = center.x() + math.cos(angle + 0.28) * (radius * 0.2 + leaf_len * 0.5)
            ctrl_right_y = center.y() - radius * 0.82 + math.sin(angle + 0.28) * (radius * 0.15 + leaf_len * 0.4)
            leaf_path.quadTo(QPointF(ctrl_right_x, ctrl_right_y), QPointF(base_right_x, base_right_y))
            leaf_path.closeSubpath()
            
            # 叶子色泽渐变（内深外浅）
            leaf_grad = QRadialGradient(QPointF(center.x(), center.y() - radius * 0.85), radius * 0.8)
            leaf_grad.setColorAt(0, base_green)
            leaf_grad.setColorAt(1, tip_green)
            
            painter.fillPath(leaf_path, leaf_grad)

    def _draw_tomato_face(self, painter, center, radius,
                         is_relax=False, is_cancelled=False):
        """已删除番茄表情，保持番茄纯净高档质感"""
        pass

    def _draw_sleep_bubble(self, painter, center, radius):
        """已停用Zzz睡觉气泡"""
        pass

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
