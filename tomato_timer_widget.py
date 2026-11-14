"""
可爱圆润番茄时钟组件 - Chibi Tomato Timer Widget
基于用户参考设计重构：
- 顶部活力射线与珊瑚红动态圆弧环
- 优雅纯白浮雕圆卡与柔和多层弥散阴影
- 上部可爱 3D 水灵小番茄（呼吸浮动、高光与绿叶）
- 中部清晰现代化大号数字倒计时
- 下部精致珊瑚红暂停胶囊指示
"""
import math
import os
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QFont, QRadialGradient,
    QPen, QBrush
)
from PyQt6.QtSvg import QSvgRenderer


class TomatoTimerWidget(QWidget):
    """可爱圆润番茄时钟显示组件"""
    clicked = pyqtSignal()

    _MODE_PALETTES = {
        "focus": {
            "ray": QColor(255, 120, 105, 210),
            "ring_bg": "#feebeb",
            "accent": "#ff6350",
            "pill_bg": "#fdeeed",
            "svg": "chibi_tomato.svg",
            "fallback": ("#ff7663", "#f44b36", "#d93826"),
        },
        "relax": {
            "ray": QColor(245, 158, 11, 210),
            "ring_bg": "#fef3e6",
            "accent": "#f59e0b",
            "pill_bg": "#fef3e6",
            "svg": "chibi_tomato_relax.svg",
            "fallback": ("#ffb665", "#f69438", "#dc7520"),
        },
        "cancelled": {
            "ray": QColor(59, 130, 246, 200),
            "ring_bg": "#e4effd",
            "accent": "#3b82f6",
            "pill_bg": "#eaf2fe",
            "svg": "chibi_tomato_free.svg",
            "fallback": ("#7bc2ff", "#4794f6", "#276ed8"),
        },
    }

    def _palette(self) -> dict:
        """获取当前模式对应的配色与资源映射"""
        return self._MODE_PALETTES.get(self._mode, self._MODE_PALETTES["focus"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)

        self._total_seconds = 25 * 60
        self._remaining_seconds = 25 * 60
        self._is_running = False
        self._mode = "focus"
        self._breath = 0.0
        self._breath_dir = 1
        self._pill_hovered = False
        self._pill_pressed = False

        # 呼吸与微动动画计时器 (~30 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def set_time(self, total_seconds: int, remaining_seconds: int):
        """设置总时间与当前剩余时间"""
        self._total_seconds = max(1, total_seconds)
        self._remaining_seconds = max(0, remaining_seconds)
        self.update()

    def set_mode(self, mode: str):
        """设置当前模式 ('focus', 'relax', 'cancelled', 'completed')"""
        self._mode = mode
        self.update()

    def set_running(self, is_running: bool):
        """设置运行状态"""
        self._is_running = is_running
        self.update()

    def _status_pill_rect(self) -> QRectF:
        """返回下方小状态胶囊的可点击区域"""
        w = self.width()
        h = self.height()
        inner_r = min(w, h) * 0.42 * 0.90
        cx = w / 2
        cy = h / 2 + inner_r * 0.54
        pw = inner_r * 0.42
        ph = inner_r * 0.24
        return QRectF(cx - pw / 2, cy - ph / 2, pw, ph)

    def mouseMoveEvent(self, event):
        hovered = self._status_pill_rect().contains(event.position())
        if hovered != self._pill_hovered:
            self._pill_hovered = hovered
            self.setCursor(
                Qt.CursorShape.PointingHandCursor if hovered else Qt.CursorShape.ArrowCursor
            )
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._pill_hovered or self._pill_pressed:
            self._pill_hovered = False
            self._pill_pressed = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """仅点击下方小胶囊区域时进入按下态，避免整个时钟区域误触"""
        if event.button() == Qt.MouseButton.LeftButton and self._status_pill_rect().contains(event.position()):
            self._pill_pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pill_pressed:
            self._pill_pressed = False
            if self._status_pill_rect().contains(event.position()):
                self.clicked.emit()
            self.update()
        super().mouseReleaseEvent(event)

    def _tick(self):
        """呼吸动画微动"""
        if self._is_running:
            self._breath += 0.02 * self._breath_dir
            if self._breath >= 1.0:
                self._breath = 1.0
                self._breath_dir = -1
            elif self._breath <= 0.0:
                self._breath = 0.0
                self._breath_dir = 1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        center = QPointF(w / 2, h / 2)
        radius = min(w, h) * 0.42

        # 1. 右上角活力射线
        self._draw_sun_rays(painter, center, radius)

        # 2. 外部进度环与起始圆钮
        if self._mode == "cancelled":
            progress = 1.0
        else:
            progress = self._remaining_seconds / max(1, self._total_seconds)
        self._draw_progress_ring(painter, center, radius, progress)

        # 3. 中央纯白圆形卡片（含多层柔和漫反射环境阴影）
        inner_r = radius * 0.90
        self._draw_white_card(painter, center, inner_r)

        # 4. 上半部 Q 版 3D 萌系小番茄
        breath_offset = self._breath * 2.5 if self._is_running else 0
        tomato_y = center.y() - inner_r * 0.43 + breath_offset
        tomato_center = QPointF(center.x(), tomato_y)
        self._draw_chibi_tomato(painter, tomato_center, inner_r * 0.40)

        # 5. 中间大号清晰数字倒计时 (例如 25:00)
        time_y = center.y() + inner_r * 0.10
        self._draw_digital_clock(painter, center.x(), time_y, inner_r)

        # 6. 下部状态药丸（暂停/播放指示胶囊）
        self._draw_status_pill(painter)

    def _draw_sun_rays(self, painter, center, radius):
        """绘制右上角两条跳跃的活力光芒"""
        painter.save()
        ray_color = self._palette()["ray"]
        pen = QPen(ray_color, 4.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # 射线 1
        r1 = radius * 1.09
        len1 = 13
        a1 = math.radians(-54)
        p1 = QPointF(center.x() + r1 * math.cos(a1), center.y() + r1 * math.sin(a1))
        p2 = QPointF(center.x() + (r1 + len1) * math.cos(a1), center.y() + (r1 + len1) * math.sin(a1))
        painter.drawLine(p1, p2)

        # 射线 2
        r2 = radius * 1.08
        len2 = 17
        a2 = math.radians(-32)
        p3 = QPointF(center.x() + r2 * math.cos(a2), center.y() + r2 * math.sin(a2))
        p4 = QPointF(center.x() + (r2 + len2) * math.cos(a2), center.y() + (r2 + len2) * math.sin(a2))
        painter.drawLine(p3, p4)
        painter.restore()

    def _draw_progress_ring(self, painter, center, radius, progress):
        """绘制环形进度条和 12 点钟同心圆起点按钮"""
        painter.save()
        ring_w = 9.0

        # 底环轨道
        pal = self._palette()
        bg_color = QColor(pal["ring_bg"])
        bg_pen = QPen(bg_color, ring_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

        # 激活的圆弧（珊瑚红 / 琥珀橙 / 晴空蓝）
        accent_color = QColor(pal["accent"])
        if progress > 0:
            arc_pen = QPen(accent_color, ring_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
            start_angle = 90 * 16
            span_angle = int(-progress * 360 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        # 12 点钟起点圆环小钮（精致同心红圈）
        knob_c = QPointF(center.x(), center.y() - radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent_color)
        painter.drawEllipse(knob_c, 7.0, 7.0)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(knob_c, 2.8, 2.8)

        painter.restore()

    def _draw_white_card(self, painter, center, radius):
        """绘制纯白浮动主卡片与扩散软阴影"""
        painter.save()
        for offset_y, alpha, spread in [(4, 18, 1.05), (7, 10, 1.10), (10, 5, 1.15)]:
            shadow_rect = QRectF(center.x() - radius * spread, center.y() - radius * spread + offset_y,
                                 radius * spread * 2, radius * spread * 2)
            shadow_grad = QRadialGradient(center.x(), center.y() + offset_y, radius * spread)
            shadow_grad.setColorAt(0.70, QColor(0, 0, 0, alpha))
            shadow_grad.setColorAt(0.95, QColor(0, 0, 0, alpha // 3))
            shadow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(shadow_grad)
            painter.drawEllipse(shadow_rect)

        # 纯白卡片圆盘
        painter.setPen(QPen(QColor(0, 0, 0, 8), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(center, radius, radius)
        painter.restore()

    def _draw_chibi_tomato(self, painter, center, size):
        """绘制饱满圆润的 3D 质感萌系小番茄 (加载紧密花萼与立体小蒂把的高清矢量 SVG)"""
        painter.save()
        tw = size * 1.50
        th = size * 1.12

        pal = self._palette()
        svg_name = pal["svg"]
        script_dir = os.path.dirname(os.path.abspath(__file__))
        svg_path = os.path.join(script_dir, "assets", svg_name)

        if os.path.exists(svg_path):
            renderer = QSvgRenderer(svg_path)
            if renderer.isValid():
                target_rect = QRectF(center.x() - tw / 2, center.y() - th / 2, tw, th)
                renderer.render(painter, target_rect)
                painter.restore()
                return

        # 备选软绘逻辑
        tw_fb = size * 1.48
        th_fb = size * 1.00
        fb = pal["fallback"]
        body_grad = QRadialGradient(center.x() - tw_fb * 0.18, center.y() - th_fb * 0.18, tw_fb * 0.72)
        body_grad.setColorAt(0.0, QColor(fb[0]))
        body_grad.setColorAt(0.58, QColor(fb[1]))
        body_grad.setColorAt(1.0, QColor(fb[2]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(body_grad)
        painter.drawEllipse(QRectF(center.x() - tw_fb / 2, center.y() - th_fb / 2, tw_fb, th_fb))
        painter.restore()

    def _draw_digital_clock(self, painter, cx, cy, inner_r):
        """绘制清晰的大号倒计时/正向计时数字 (例如 25:00)"""
        painter.save()
        total_sec = max(0, self._remaining_seconds)
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60 if hours > 0 else total_sec // 60
        seconds = total_sec % 60

        if hours > 0:
            text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            font_size = int(inner_r * 0.28)
        else:
            text = f"{minutes:02d}:{seconds:02d}"
            font_size = int(inner_r * 0.38)

        font = QFont("Microsoft YaHei UI", font_size, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -1.0)
        painter.setFont(font)
        painter.setPen(QColor("#2d2d2d"))

        text_rect = QRectF(cx - inner_r * 0.85, cy - inner_r * 0.22, inner_r * 1.7, inner_r * 0.44)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def _draw_status_pill(self, painter):
        """绘制下方可点击状态胶囊（未运行时显示 ▶，运行中显示 ||）"""
        painter.save()
        pill_rect = self._status_pill_rect()
        cx = pill_rect.center().x()
        cy = pill_rect.center().y()
        ph = pill_rect.height()

        pal = self._palette()
        pill_bg = QColor(pal["pill_bg"])
        accent = QColor(pal["accent"])
        if self._pill_pressed:
            pill_bg = pill_bg.darker(108)
        elif self._pill_hovered:
            pill_bg = pill_bg.darker(103)

        if self._pill_hovered or self._pill_pressed:
            border = QColor(accent)
            border.setAlpha(90)
            painter.setPen(QPen(border, 1.2))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(pill_bg)
        painter.drawRoundedRect(pill_rect, ph / 2, ph / 2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)

        if self._is_running:
            # 运行中显示暂停双竖棒 ||
            bar_w = 4.2
            bar_h = ph * 0.48
            bar_spacing = 7.0
            b1 = QRectF(cx - bar_spacing / 2 - bar_w, cy - bar_h / 2, bar_w, bar_h)
            b2 = QRectF(cx + bar_spacing / 2, cy - bar_h / 2, bar_w, bar_h)
            painter.drawRoundedRect(b1, 2, 2)
            painter.drawRoundedRect(b2, 2, 2)
        else:
            # 暂停/未开始时显示圆润播放三角 ▶
            tri_h = ph * 0.48
            tri_w = tri_h * 0.88
            offset_x = 1.2
            path = QPainterPath()
            p_top = QPointF(cx - tri_w / 2 + offset_x, cy - tri_h / 2)
            p_bot = QPointF(cx - tri_w / 2 + offset_x, cy + tri_h / 2)
            p_tip = QPointF(cx + tri_w / 2 + offset_x, cy)
            path.moveTo(p_top)
            path.lineTo(p_tip)
            path.lineTo(p_bot)
            path.closeSubpath()
            painter.setPen(QPen(accent, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)

        painter.restore()
