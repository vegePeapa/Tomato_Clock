"""
番茄钟 UI 界面布局定义 - 还原精致手绘 Q 版番茄设计风格
包含：
- ModeCapsuleButton: 顶部模式胶囊切换按钮 (Target / Coffee 图标 + 模式名 + 下拉箭头)
- 顶部双圆形白底投影按钮 (设置 ⚙、更多操作 ⋮)
- 核心时间显示容器 (挂载 TomatoTimerWidget)
- 并列双白色数据卡片 (总专注时长卡片、剩余循环卡片)
- 底部胶囊核心操作按钮 (开始专注大红渐变胶囊、结束任务白底旗帜胶囊)
- 底部微光小提示
"""
import os
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class ModeCapsuleButton(QtWidgets.QPushButton):
    """顶部模式切换胶囊按钮，左标、文字、右箭头完美呈现"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modeCapsule")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        # 左侧 Target 图标
        self.icon_lbl = QtWidgets.QLabel()
        self.icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        target_icon_path = os.path.join(ASSETS_DIR, "icon_target.svg")
        if os.path.exists(target_icon_path):
            self.icon_lbl.setPixmap(QIcon(target_icon_path).pixmap(18, 18))
        layout.addWidget(self.icon_lbl)

        # 中间模式文字
        self.text_lbl = QtWidgets.QLabel("专注模式")
        self.text_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.text_lbl.setStyleSheet("color: #333333; font-size: 14px; font-weight: 700; background: transparent;")
        layout.addWidget(self.text_lbl)

        # 右侧向下小箭头
        self.arrow_lbl = QtWidgets.QLabel()
        self.arrow_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        chevron_path = os.path.join(ASSETS_DIR, "icon_chevron_down.svg")
        if os.path.exists(chevron_path):
            self.arrow_lbl.setPixmap(QIcon(chevron_path).pixmap(12, 12))
        layout.addWidget(self.arrow_lbl)

    def sizeHint(self):
        s = self.layout().sizeHint()
        return QSize(max(130, s.width() + 10), 38)

    def setText(self, text: str):
        clean_text = text.replace("🎯", "").replace("☕", "").replace("✅", "").replace("⚠️", "").replace("⏱️", "").strip()
        self.text_lbl.setText(clean_text)
        if "自由" in clean_text:
            free_path = os.path.join(ASSETS_DIR, "icon_free.svg")
            if os.path.exists(free_path):
                self.icon_lbl.setPixmap(QIcon(free_path).pixmap(18, 18))
            else:
                target_path = os.path.join(ASSETS_DIR, "icon_target.svg")
                if os.path.exists(target_path):
                    self.icon_lbl.setPixmap(QIcon(target_path).pixmap(18, 18))
        elif "休息" in clean_text:
            coffee_path = os.path.join(ASSETS_DIR, "icon_coffee.svg")
            if os.path.exists(coffee_path):
                self.icon_lbl.setPixmap(QIcon(coffee_path).pixmap(18, 18))
        else:
            target_path = os.path.join(ASSETS_DIR, "icon_target.svg")
            if os.path.exists(target_path):
                self.icon_lbl.setPixmap(QIcon(target_path).pixmap(18, 18))

    def text(self) -> str:
        return self.text_lbl.text()


class Ui_Timer(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(450, 640)
        Dialog.setMinimumSize(420, 600)

        # ===== 主垂直布局 =====
        self.mainLayout = QtWidgets.QVBoxLayout(Dialog)
        self.mainLayout.setContentsMargins(28, 24, 28, 22)
        self.mainLayout.setSpacing(18)

        # ===== 1. 顶部状态栏 =====
        self.topBarLayout = QtWidgets.QHBoxLayout()
        self.topBarLayout.setSpacing(12)

        # 模式切换胶囊
        self.mode_label = ModeCapsuleButton(parent=Dialog)
        self.topBarLayout.addWidget(self.mode_label)

        self.topBarLayout.addStretch()

        # 设置按钮（圆形白底）
        self.settingsButton = QtWidgets.QPushButton(parent=Dialog)
        self.settingsButton.setObjectName("settingsButton")
        self.settingsButton.setFixedSize(44, 44)
        self.settingsButton.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        gear_path = os.path.join(ASSETS_DIR, "icon_gear.svg")
        if os.path.exists(gear_path):
            self.settingsButton.setIcon(QIcon(gear_path))
            self.settingsButton.setIconSize(QSize(22, 22))
        self.topBarLayout.addWidget(self.settingsButton)

        # 更多操作菜单按钮（圆形白底）
        self.moreButton = QtWidgets.QPushButton(parent=Dialog)
        self.moreButton.setObjectName("moreButton")
        self.moreButton.setFixedSize(44, 44)
        self.moreButton.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        dots_path = os.path.join(ASSETS_DIR, "icon_dots.svg")
        if os.path.exists(dots_path):
            self.moreButton.setIcon(QIcon(dots_path))
            self.moreButton.setIconSize(QSize(20, 20))
        self.topBarLayout.addWidget(self.moreButton)

        self.mainLayout.addLayout(self.topBarLayout)

        # ===== 2. 时间显示区域（核心视觉区）=====
        self.timerContainer = QtWidgets.QWidget(parent=Dialog)
        self.timerContainer.setObjectName("timerContainer")
        self.timerLayout = QtWidgets.QVBoxLayout(self.timerContainer)
        self.timerLayout.setContentsMargins(0, 0, 0, 0)
        self.timerLayout.setSpacing(0)

        # 时间显示容器（挂载 TomatoTimerWidget）
        self.timerDisplayWidget = QtWidgets.QWidget(self.timerContainer)
        self.timerDisplayWidget.setObjectName("timerDisplayWidget")
        self.timerDisplayWidget.setMinimumSize(320, 320)
        self.timerLayout.addWidget(self.timerDisplayWidget, alignment=Qt.AlignmentFlag.AlignCenter)

        self.mainLayout.addWidget(self.timerContainer, 1)

        # ===== 3. 中部两个并列白底信息卡片 =====
        self.infoRowLayout = QtWidgets.QHBoxLayout()
        self.infoRowLayout.setSpacing(16)

        # 卡片 1：总专注时长
        self.card1, self.timer_duration_laber = self._create_info_card(
            "icon_clock.svg", "总专注时长", "00:00", Dialog
        )
        self.infoRowLayout.addWidget(self.card1)

        # 卡片 2：剩余循环
        self.card2, self.cycle_label = self._create_info_card(
            "icon_coffee.svg", "剩余循环", "2", Dialog
        )
        self.infoRowLayout.addWidget(self.card2)

        self.mainLayout.addLayout(self.infoRowLayout)

        # ===== 4. 底部核心操作按钮 =====
        self.coreButtonLayout = QtWidgets.QHBoxLayout()
        self.coreButtonLayout.setSpacing(16)

        # 开始/暂停按钮（大红胶囊主按钮）
        self.startButton = QtWidgets.QPushButton(" 开始专注", parent=Dialog)
        self.startButton.setObjectName("startButton")
        self.startButton.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        self.startButton.setMinimumHeight(56)
        play_path = os.path.join(ASSETS_DIR, "icon_play.svg")
        if os.path.exists(play_path):
            self.startButton.setIcon(QIcon(play_path))
            self.startButton.setIconSize(QSize(18, 18))
        self.coreButtonLayout.addWidget(self.startButton, 3)

        # 结束任务按钮（白底旗帜次主按钮）
        self.finishButton = QtWidgets.QPushButton(" 结束任务", parent=Dialog)
        self.finishButton.setObjectName("finishButton")
        self.finishButton.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        self.finishButton.setMinimumHeight(56)
        flag_path = os.path.join(ASSETS_DIR, "icon_flag.svg")
        if os.path.exists(flag_path):
            self.finishButton.setIcon(QIcon(flag_path))
            self.finishButton.setIconSize(QSize(20, 20))
        self.coreButtonLayout.addWidget(self.finishButton, 2)

        self.mainLayout.addLayout(self.coreButtonLayout)

        # ===== 5. 底部次要操作微提示 =====
        self.secondaryInfoLayout = QtWidgets.QHBoxLayout()
        self.secondaryInfoLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.secondaryInfoLayout.setSpacing(6)

        self.bulb_icon_label = QtWidgets.QLabel(parent=Dialog)
        bulb_path = os.path.join(ASSETS_DIR, "icon_bulb.svg")
        if os.path.exists(bulb_path):
            self.bulb_icon_label.setPixmap(QIcon(bulb_path).pixmap(15, 15))
        self.secondaryInfoLayout.addWidget(self.bulb_icon_label)

        self.secondaryInfoLabel = QtWidgets.QLabel("点击右上角 · 查看更多操作", parent=Dialog)
        self.secondaryInfoLabel.setObjectName("secondaryInfoLabel")
        self.secondaryInfoLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.secondaryInfoLayout.addWidget(self.secondaryInfoLabel)

        self.mainLayout.addLayout(self.secondaryInfoLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def _create_info_card(self, icon_filename: str, title: str, default_val: str, parent):
        """创建精致白底数据卡片"""
        card = QtWidgets.QWidget(parent)
        card.setObjectName("infoCard")
        layout = QtWidgets.QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        icon_lbl = QtWidgets.QLabel(card)
        icon_path = os.path.join(ASSETS_DIR, icon_filename)
        if os.path.exists(icon_path):
            icon_lbl.setPixmap(QIcon(icon_path).pixmap(26, 26))
        layout.addWidget(icon_lbl)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_lbl = QtWidgets.QLabel(title, card)
        title_lbl.setObjectName("cardTitleLabel")
        title_lbl.setStyleSheet("color: #7a7575; font-size: 12px; font-weight: 500; background: transparent;")
        text_layout.addWidget(title_lbl)

        val_lbl = QtWidgets.QLabel(default_val, card)
        val_lbl.setObjectName("cardValLabel")
        val_lbl.setStyleSheet("color: #222222; font-size: 18px; font-weight: 800; background: transparent;")
        text_layout.addWidget(val_lbl)

        layout.addLayout(text_layout)
        layout.addStretch()
        return card, val_lbl

    def retranslateUi(self, Dialog):
        """设置UI国际化文本"""
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "番茄钟"))
        self.settingsButton.setToolTip(_translate("Dialog", "设置"))
        self.moreButton.setToolTip(_translate("Dialog", "更多操作"))
        self.secondaryInfoLabel.setText(_translate("Dialog", "点击右上角 · 查看更多操作"))
