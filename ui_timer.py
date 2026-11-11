"""
重构的 UI 布局 - 液体极简主义设计
Liquid Minimalism UI Layout
核心原则：视觉中心 + 清晰的交互层次
"""
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt


class Ui_Timer(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(480, 620)  # 更高的窗口以容纳时间显示区
        Dialog.setMinimumSize(420, 580)

        # ===== 主布局 =====
        self.mainLayout = QtWidgets.QVBoxLayout(Dialog)
        self.mainLayout.setContentsMargins(40, 40, 40, 40)
        self.mainLayout.setSpacing(24)

        # ===== 顶部状态栏 =====
        self.topBarLayout = QtWidgets.QHBoxLayout()
        self.topBarLayout.setSpacing(16)

        # 模式标签
        self.mode_label = QtWidgets.QLabel(parent=Dialog)
        self.mode_label.setObjectName("mode_label")
        self.mode_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.topBarLayout.addWidget(self.mode_label)

        self.topBarLayout.addStretch()

        # 设置按钮
        self.settingsButton = QtWidgets.QPushButton(parent=Dialog)
        self.settingsButton.setObjectName("settingsButton")
        self.settingsButton.setFixedSize(44, 44)
        self.settingsButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.settingsButton.setText("⚙")
        self.topBarLayout.addWidget(self.settingsButton)

        # 更多操作菜单按钮
        self.moreButton = QtWidgets.QPushButton(parent=Dialog)
        self.moreButton.setObjectName("moreButton")
        self.moreButton.setFixedSize(44, 44)
        self.moreButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.moreButton.setText("⋮")
        self.topBarLayout.addWidget(self.moreButton)

        self.mainLayout.addLayout(self.topBarLayout)

        # ===== 时间显示区域（核心视觉区）=====
        self.timerContainer = QtWidgets.QWidget(parent=Dialog)
        self.timerContainer.setObjectName("timerContainer")
        self.timerLayout = QtWidgets.QVBoxLayout(self.timerContainer)
        self.timerLayout.setContentsMargins(0, 0, 0, 0)
        self.timerLayout.setSpacing(12)

        # 时间显示容器（用于放置自定义组件）
        self.timerDisplayWidget = QtWidgets.QWidget(parent=Dialog)
        self.timerDisplayWidget.setObjectName("timerDisplayWidget")
        self.timerDisplayWidget.setMinimumSize(320, 320)

        # 信息标签行（今日专注 + 剩余循环）
        self.infoRowLayout = QtWidgets.QHBoxLayout()
        self.infoRowLayout.setSpacing(24)

        self.timer_duration_laber = QtWidgets.QLabel(parent=Dialog)
        self.timer_duration_laber.setObjectName("timer_duration_laber")
        self.timer_duration_laber.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.infoRowLayout.addWidget(self.timer_duration_laber)

        self.infoRowLayout.addStretch()

        self.cycle_label = QtWidgets.QLabel(parent=Dialog)
        self.cycle_label.setObjectName("cycle_label")
        self.cycle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.infoRowLayout.addWidget(self.cycle_label)

        self.timerLayout.addWidget(self.timerDisplayWidget)
        self.timerLayout.addLayout(self.infoRowLayout)

        self.mainLayout.addWidget(self.timerContainer, 1)  # 给予最大伸缩因子

        # ===== 弹性空间 =====
        self.mainLayout.addStretch(1)

        # ===== 核心按钮区域 =====
        self.coreButtonLayout = QtWidgets.QHBoxLayout()
        self.coreButtonLayout.setSpacing(20)

        # 开始/暂停按钮（主按钮）
        self.startButton = QtWidgets.QPushButton(parent=Dialog)
        self.startButton.setObjectName("startButton")
        self.startButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.startButton.setMinimumHeight(64)
        self.coreButtonLayout.addWidget(self.startButton, 2)  # 占2份宽度

        # 结束任务按钮（次主按钮）
        self.finishButton = QtWidgets.QPushButton(parent=Dialog)
        self.finishButton.setObjectName("finishButton")
        self.finishButton.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.finishButton.setMinimumHeight(64)
        self.coreButtonLayout.addWidget(self.finishButton, 1)  # 占1份宽度

        self.mainLayout.addLayout(self.coreButtonLayout)

        # ===== 次要操作提示 =====
        self.secondaryInfoLayout = QtWidgets.QHBoxLayout()
        self.secondaryInfoLabel = QtWidgets.QLabel(parent=Dialog)
        self.secondaryInfoLabel.setObjectName("secondaryInfoLabel")
        self.secondaryInfoLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.secondaryInfoLabel.setText("点击右上角 ⋮ 查看更多操作")
        self.secondaryInfoLayout.addWidget(self.secondaryInfoLabel)

        self.mainLayout.addLayout(self.secondaryInfoLayout)

        # ===== 创建更多操作菜单 =====
        self._create_more_menu()

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def _create_more_menu(self):
        """创建更多操作菜单（在主逻辑中连接）"""
        # 这个菜单将在 main.py 中创建和连接
        self.more_menu = None

    def retranslateUi(self, Dialog):
        """设置UI文本"""
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "番茄钟"))
        self.mode_label.setText(_translate("Dialog", "🎯 专注模式"))
        self.settingsButton.setToolTip(_translate("Dialog", "设置"))
        self.moreButton.setToolTip(_translate("Dialog", "更多操作"))
        self.timer_duration_laber.setText(_translate("Dialog", "今日专注: 00:00"))
        self.cycle_label.setText(_translate("Dialog", "剩余循环: 2"))
        self.startButton.setText(_translate("Dialog", "开始专注"))
        self.finishButton.setText(_translate("Dialog", "结束任务"))
        self.secondaryInfoLabel.setText(_translate("Dialog", "点击右上角 ⋮ 查看更多操作"))