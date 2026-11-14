import sys
import os
import json
from functools import wraps
from PyQt6.QtWidgets import (
    QApplication, QDialog, QMessageBox, QSystemTrayIcon,
    QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QCheckBox, QPushButton,
    QMenu, QSlider, QWidget, QTabWidget
)
from PyQt6.QtCore import QTimer, Qt, QDateTime, QUrl, QEvent, QRectF, QSize
from PyQt6.QtGui import QCloseEvent, QIcon, QAction, QFont, QPainter, QPainterPath, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtMultimedia import QSoundEffect
from ui_timer import Ui_Timer
from tomato_timer_widget import TomatoTimerWidget

# 从 constants 模块导入共用常量
from constants import (
    TimerMode, DATA_FILE_FULL_PATH, CONFIG_FILE_FULL_PATH,
    DEFAULT_TASK_NAME, DEFAULT_CONFIG, DATA_FILE, ensure_ui_assets
)

# 确保必要的图标资源就绪
ensure_ui_assets()

def report(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f'当前执行{func.__name__}')
        result = func(*args, **kwargs)
        return result
    return wrapper


# 出现异常直接保存语法糖
def error_data_save(func):
    @wraps(func)
    def wrapper(self: 'TimerWindow', *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            print('发生错误，紧急报错数据')
            try:
                data_to_save = getattr(self, 'focus_log', {})
                self.save_time_data(data_to_save)
                print('紧急报错成功')
            except Exception as save_e:
                print(f'保存数据失败: {save_e}')
            print(f'发生错误{e}')
            raise
    return wrapper



# ============== 自定义输入对话框 ==============
class TaskInputDialog(QDialog):
    """自定义任务名输入对话框"""

    def __init__(self, title: str, prompt: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(420, 200)
        self.resize(420, 210)
        self.result_text = ""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fdfbf9, stop:1 #ffffff);
                border: 1px solid rgba(235, 94, 76, 0.3);
            }
        """)
        self._setup_ui(prompt)

    def _setup_ui(self, prompt: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 24)

        # 提示标签
        prompt_label = QLabel(prompt)
        prompt_label.setStyleSheet("""
            QLabel {
                color: #2b2523;
                font-size: 15px;
                font-weight: 700;
                background: transparent;
            }
        """)
        layout.addWidget(prompt_label)

        # 输入框
        from PyQt6.QtWidgets import QLineEdit
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("请输入任务名称（例如：背单词、写代码）...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 10px 14px;
                min-height: 22px;
                border: 2px solid #d0d7de;
                border-radius: 8px;
                background-color: #ffffff;
                color: #2b2523;
                font-size: 14px;
                font-weight: 500;
                selection-background-color: #eb5e4c;
                selection-color: #ffffff;
            }
            QLineEdit:hover {
                border-color: #b0b7be;
            }
            QLineEdit:focus {
                border-color: #eb5e4c;
                background-color: #ffffff;
            }
        """)
        layout.addWidget(self.input_field)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                background-color: #f6f8fa;
                color: #24292f;
                border: 1.5px solid #d0d7de;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #e8eaed;
                border-color: #afb8c1;
            }
            QPushButton:pressed {
                background-color: #d0d7de;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("确定")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 26px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #eb5e4c, stop:1 #d84532);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
                min-height: 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff7361, stop:1 #eb5e4c);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c43827, stop:1 #af2f20);
            }
        """)
        ok_btn.clicked.connect(self._accept)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)
        self.input_field.setFocus()
        self.input_field.returnPressed.connect(self._accept)

    def _accept(self):
        self.result_text = self.input_field.text().strip()
        if not self.result_text:
            self.result_text = DEFAULT_TASK_NAME
        self.accept()

    @staticmethod
    def getText(parent, title: str, prompt: str):
        """静态方法，模拟 QInputDialog.getText"""
        dialog = TaskInputDialog(title, prompt, parent)
        result = dialog.exec()
        return dialog.result_text, result == QDialog.DialogCode.Accepted


# ============== 设置对话框 ==============
class SettingsDialog(QDialog):
    """设置对话框 - 允许用户自定义番茄钟参数"""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsDialog")  # 设置对象名称匹配 QSS 选择器
        self.config = config.copy()  # 复制配置以便取消时不影响原配置
        self.setWindowTitle("设置")
        self.setFixedSize(520, 485)

        # 程序目录与音效试听初始化
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self._init_sound_preview()

        self._setup_ui()
        self._load_config()

        # 加载设置界面专用样式
        qss_path = os.path.join(self.script_dir, "settings.qss")
        if os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    qss_content = f.read().replace("{ASSET_DIR}", self.script_dir.replace("\\", "/"))
                    self.setStyleSheet(qss_content)
            except Exception as e:
                print(f"加载设置样式表失败: {e}")

    def _init_sound_preview(self):
        """初始化用于设置界面试听的音效"""
        self.preview_sound = None
        try:
            sound_paths = [
                os.path.join(self.script_dir, "notification.wav"),
                "C:/Windows/Media/Windows Notify System Generic.wav",
                "C:/Windows/Media/chimes.wav",
            ]
            for p in sound_paths:
                if os.path.exists(p):
                    self.preview_sound = QSoundEffect()
                    self.preview_sound.setSource(QUrl.fromLocalFile(p))
                    break
        except Exception:
            self.preview_sound = None

    def _setup_ui(self):
        """初始化设置界面 - 使用选项卡布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(18, 16, 18, 14)

        # 创建选项卡
        tab_widget = QTabWidget()
        tab_widget.setObjectName("settingsTabWidget")
        self.tab_widget = tab_widget

        # 添加各个选项卡
        time_tab = self._create_time_settings_tab()
        tab_widget.addTab(time_tab, "时间设置")

        sound_tab = self._create_sound_settings_tab()
        tab_widget.addTab(sound_tab, "声音设置")

        auto_tab = self._create_auto_settings_tab()
        tab_widget.addTab(auto_tab, "常规与自动化")

        main_layout.addWidget(tab_widget)

        # 添加底部分隔线和按钮区域
        line_widget = QWidget()
        line_widget.setFixedHeight(1)
        line_widget.setStyleSheet("background-color: #f0ece9;")
        main_layout.addWidget(line_widget)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.setContentsMargins(10, 12, 10, 4)
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.setFixedWidth(96)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setObjectName("saveButton")
        save_btn.setFixedWidth(96)
        save_btn.setDefault(True)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_and_accept)
        button_layout.addWidget(save_btn)

        main_layout.addLayout(button_layout)

    def _create_section_header(self, text: str) -> QLabel:
        """创建卡片区域的标题"""
        lbl = QLabel(text)
        lbl.setObjectName("sectionHeader")
        return lbl

    def _create_card(self) -> QWidget:
        """创建卡片容器"""
        card = QWidget()
        card.setObjectName("settingsCard")
        return card

    def _create_row(self, title: str, desc: str, control: QWidget) -> QWidget:
        """创建带标题、描述和控制组件的标准行"""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(12)

        t_layout = QVBoxLayout()
        t_layout.setSpacing(2)
        t_lbl = QLabel(title)
        t_lbl.setObjectName("rowTitle")
        t_layout.addWidget(t_lbl)
        if desc:
            d_lbl = QLabel(desc)
            d_lbl.setObjectName("rowDesc")
            t_layout.addWidget(d_lbl)
        layout.addLayout(t_layout)

        layout.addStretch()
        layout.addWidget(control, alignment=Qt.AlignmentFlag.AlignVCenter)
        return row

    def _create_checkbox_row(self, checkbox: QCheckBox, desc: str) -> QWidget:
        """创建带下属说明的复选框行"""
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)
        layout.addWidget(checkbox)
        if desc:
            d_lbl = QLabel(desc)
            d_lbl.setObjectName("rowDesc")
            d_lbl.setStyleSheet("margin-left: 30px;")
            layout.addWidget(d_lbl)
        return row

    def _create_inner_divider(self) -> QWidget:
        """创建卡片内的微细分隔线"""
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #f0ece9; margin: 4px 0;")
        return line

    def _create_time_settings_tab(self):
        """创建时间设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 区域 1：番茄节奏配置
        layout.addWidget(self._create_section_header("番茄节奏"))
        card1 = self._create_card()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(16, 12, 16, 12)
        c1_layout.setSpacing(6)

        # 专注时长
        self.focus_spin = QSpinBox()
        self.focus_spin.setRange(5, 90)
        self.focus_spin.setSingleStep(5)
        self.focus_spin.setSuffix(" 分钟")
        self.focus_spin.setFixedSize(118, 28)
        c1_layout.addWidget(self._create_row("专注时长", "单次番茄钟专注工作时长", self.focus_spin))

        c1_layout.addWidget(self._create_inner_divider())

        # 休息时长
        self.relax_spin = QSpinBox()
        self.relax_spin.setRange(1, 30)
        self.relax_spin.setSingleStep(1)
        self.relax_spin.setSuffix(" 分钟")
        self.relax_spin.setFixedSize(118, 28)
        c1_layout.addWidget(self._create_row("休息时长", "专注结束后的短休息时长", self.relax_spin))

        c1_layout.addWidget(self._create_inner_divider())

        # 循环次数
        self.cycle_spin = QSpinBox()
        self.cycle_spin.setRange(1, 10)
        self.cycle_spin.setSingleStep(1)
        self.cycle_spin.setSuffix(" 次")
        self.cycle_spin.setFixedSize(118, 28)
        c1_layout.addWidget(self._create_row("循环轮次", "一个完整大周期包含的专注次数", self.cycle_spin))

        layout.addWidget(card1)

        # 区域 2：超时机制
        layout.addWidget(self._create_section_header("超时保护"))
        card2 = self._create_card()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(16, 12, 16, 12)
        c2_layout.setSpacing(6)

        self.pause_spin = QSpinBox()
        self.pause_spin.setRange(1, 60)
        self.pause_spin.setSingleStep(1)
        self.pause_spin.setSuffix(" 分钟")
        self.pause_spin.setFixedSize(118, 28)
        c2_layout.addWidget(self._create_row("最大暂停时间", "暂停超过此时长将自动结算并重置", self.pause_spin))

        layout.addWidget(card2)
        layout.addStretch()

        return widget

    def _create_sound_settings_tab(self):
        """创建声音设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(self._create_section_header("提示音配置"))
        card = self._create_card()
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 12, 16, 12)
        c_layout.setSpacing(10)

        # 启用声音开关
        self.sound_checkbox = QCheckBox("启用提示音")
        self.sound_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sound_checkbox.setStyleSheet("font-size: 14px; font-weight: 700; color: #2b2523;")
        c_layout.addWidget(self._create_checkbox_row(
            self.sound_checkbox,
            "在专注完成、休息结束或计时提醒时播放提示音"
        ))

        c_layout.addWidget(self._create_inner_divider())

        # 音量控制行
        vol_row = QWidget()
        vol_layout = QHBoxLayout(vol_row)
        vol_layout.setContentsMargins(0, 4, 0, 4)
        vol_layout.setSpacing(12)

        vol_text_layout = QVBoxLayout()
        vol_text_layout.setSpacing(2)
        vol_title = QLabel("提示声音量")
        vol_title.setObjectName("rowTitle")
        vol_desc = QLabel("调整提示音播放音量大小")
        vol_desc.setObjectName("rowDesc")
        vol_text_layout.addWidget(vol_title)
        vol_text_layout.addWidget(vol_desc)
        vol_layout.addLayout(vol_text_layout)

        vol_layout.addStretch()

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        vol_layout.addWidget(self.volume_slider, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.volume_label = QLabel("80%")
        self.volume_label.setFixedWidth(38)
        self.volume_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #2b2523;")
        vol_layout.addWidget(self.volume_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.preview_btn = QPushButton("试听")
        self.preview_btn.setObjectName("previewSoundButton")
        self.preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_btn.clicked.connect(self._play_preview_sound)
        vol_layout.addWidget(self.preview_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        c_layout.addWidget(vol_row)

        self.sound_checkbox.toggled.connect(self._on_sound_toggled)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

        layout.addWidget(card)
        layout.addStretch()

        return widget

    def _on_sound_toggled(self, checked: bool):
        """启用/禁用声音开关时联动音量控件状态"""
        self.volume_slider.setEnabled(checked)
        self.volume_label.setEnabled(checked)
        if hasattr(self, 'preview_btn'):
            self.preview_btn.setEnabled(checked)

    def _on_volume_changed(self, val: int):
        """音量滑动更新文本与试听音量"""
        self.volume_label.setText(f"{val}%")
        if self.preview_sound:
            self.preview_sound.setVolume(val / 100.0)

    def _play_preview_sound(self):
        """试听当前设置的提示音效"""
        if self.preview_sound:
            self.preview_sound.setVolume(self.volume_slider.value() / 100.0)
            self.preview_sound.play()

    def _create_auto_settings_tab(self):
        """创建常规与自动化设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 分组 1：窗口与托盘
        layout.addWidget(self._create_section_header("窗口与系统托盘"))
        card1 = self._create_card()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(16, 10, 16, 10)
        c1_layout.setSpacing(8)

        self.minimize_to_tray_checkbox = QCheckBox("最小化时隐藏到系统托盘")
        self.minimize_to_tray_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        c1_layout.addWidget(self._create_checkbox_row(
            self.minimize_to_tray_checkbox,
            "点击标题栏最小化按钮时，隐入右下角托盘图标"
        ))

        c1_layout.addWidget(self._create_inner_divider())

        self.close_to_tray_checkbox = QCheckBox("关闭窗口时最小化到系统托盘（后台运行）")
        self.close_to_tray_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        c1_layout.addWidget(self._create_checkbox_row(
            self.close_to_tray_checkbox,
            "点击窗口 [×] 时不退出程序，保持后台计时；可通过托盘菜单彻底退出"
        ))

        layout.addWidget(card1)

        # 分组 2：流程自动化
        layout.addWidget(self._create_section_header("流程自动化"))
        card2 = self._create_card()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(16, 10, 16, 10)
        c2_layout.setSpacing(8)

        self.auto_break_checkbox = QCheckBox("专注结束后自动开始休息")
        self.auto_break_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        c2_layout.addWidget(self._create_checkbox_row(
            self.auto_break_checkbox,
            "专注时间归零时，无需手动操作即可直接进入休息阶段"
        ))

        c2_layout.addWidget(self._create_inner_divider())

        self.auto_focus_checkbox = QCheckBox("休息结束后自动开始专注")
        self.auto_focus_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        c2_layout.addWidget(self._create_checkbox_row(
            self.auto_focus_checkbox,
            "休息时间归零时，自动启动下一个番茄钟专注时段"
        ))

        layout.addWidget(card2)
        layout.addStretch()

        return widget

    def _create_spinbox_row(self, parent_layout, label_text, min_val, max_val,
                           step, suffix, tooltip=None):
        """兼容旧接口的 SpinBox 行创建方法"""
        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setSingleStep(step)
        spinbox.setSuffix(suffix)
        spinbox.setFixedSize(118, 28)
        if tooltip:
            spinbox.setToolTip(tooltip)
        parent_layout.addWidget(self._create_row(label_text, tooltip or "", spinbox))
        return spinbox

    def _load_config(self):
        """ 从配置字典加载到UI控件 """
        self.focus_spin.setValue(self.config.get("focus_duration", 25))
        self.relax_spin.setValue(self.config.get("relax_duration", 5))
        self.cycle_spin.setValue(self.config.get("cycle_count", 2))
        self.pause_spin.setValue(self.config.get("max_pause_time", 10))

        sound_enabled = self.config.get("sound_enabled", True)
        self.sound_checkbox.setChecked(sound_enabled)
        vol = self.config.get("sound_volume", 80)
        self.volume_slider.setValue(vol)
        self.volume_label.setText(f"{vol}%")
        self._on_sound_toggled(sound_enabled)

        self.minimize_to_tray_checkbox.setChecked(
            self.config.get("minimize_to_tray", False))
        self.close_to_tray_checkbox.setChecked(
            self.config.get("close_to_tray", False))
        self.auto_break_checkbox.setChecked(
            self.config.get("auto_start_break", False))
        self.auto_focus_checkbox.setChecked(
            self.config.get("auto_start_focus", False))

    def _save_and_accept(self):
        """ 保存配置并关闭对话框 """
        self.config["focus_duration"] = self.focus_spin.value()
        self.config["relax_duration"] = self.relax_spin.value()
        self.config["cycle_count"] = self.cycle_spin.value()
        self.config["max_pause_time"] = self.pause_spin.value()
        self.config["sound_enabled"] = self.sound_checkbox.isChecked()
        self.config["sound_volume"] = self.volume_slider.value()
        self.config["minimize_to_tray"] = self.minimize_to_tray_checkbox.isChecked()
        self.config["close_to_tray"] = self.close_to_tray_checkbox.isChecked()
        self.config["auto_start_break"] = self.auto_break_checkbox.isChecked()
        self.config["auto_start_focus"] = self.auto_focus_checkbox.isChecked()
        self.accept()

    def get_config(self) -> dict:
        """ 返回配置字典 """
        return self.config


class TimerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 目录与标记初始化
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self._force_quit = False

        # 设置窗口标志：允许任务栏最小化和关闭，但不显示最大化按钮
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        # 设置窗口图标
        icon_path = os.path.join(self.script_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # UI 初始化
        self.ui = Ui_Timer()
        self.ui.setupUi(self)

        self.setObjectName("TimerWindow")  # 设置对象名称以匹配 QSS 选择器 QDialog#TimerWindow

        # 设置窗口标题与尺寸
        self.setWindowTitle("番茄钟计时器")
        self.resize(450, 640)
        self.setMinimumSize(420, 600)


        # ===== 初始化液体时间组件 =====
        self._init_liquid_timer()

        # ===== 创建更多操作菜单 =====
        self._create_more_menu()

        # 逻辑初始化
        self._init_timer_state()
        self._connect_signals()

        # 应用样式
        self._apply_style()

    def _init_liquid_timer(self):
        """初始化液体时间显示组件"""
        self.liquid_timer = TomatoTimerWidget(self.ui.timerDisplayWidget)
        # 将液体组件放入容器的布局中
        layout = self.ui.timerDisplayWidget.layout()
        if layout is None:
            layout = QVBoxLayout(self.ui.timerDisplayWidget)
            layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.liquid_timer)

    def _create_more_menu(self):
        """创建更多操作菜单"""
        self.more_menu = QMenu(self)
        self.more_menu.setObjectName("more_menu")

        # 重置
        reset_action = QAction("重置计时器", self)
        reset_action.triggered.connect(self._reset_timer)
        self.more_menu.addAction(reset_action)

        # 模式切换
        self.cancel_action = QAction("切换至自由模式", self)
        self.cancel_action.triggered.connect(self._cancel_tomato_clock)
        self.more_menu.addAction(self.cancel_action)

        self.more_menu.addSeparator()

        # 最小化选项
        min_taskbar_action = QAction("最小化到任务栏", self)
        min_taskbar_action.triggered.connect(self.showMinimized)
        self.more_menu.addAction(min_taskbar_action)

        min_tray_action = QAction("最小化到系统托盘", self)
        min_tray_action.triggered.connect(self._minimize_to_tray)
        self.more_menu.addAction(min_tray_action)

        self.more_menu.addSeparator()

        # 查看时间轴
        timeline_action = QAction("查看时间轴", self)
        timeline_action.triggered.connect(self._view_timeline)
        self.more_menu.addAction(timeline_action)

        # 连接更多按钮到菜单
        self.ui.moreButton.setMenu(self.more_menu)

    def _init_timer_state(self):
        """初始化所有常量、变量、计时器并加载数据。"""
        # --- 文件路径定义 (使用全局定义的标准用户目录路径) ---
        self.DATA_FILE = DATA_FILE
        self.DATA_FILE_FULL_PATH = DATA_FILE_FULL_PATH
        self.CONFIG_FILE_FULL_PATH = CONFIG_FILE_FULL_PATH
        # 程序目录（用于音效文件等资源）
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # --- 加载配置 ---
        self.config = self._load_config()

        # --- 从配置初始化常量 ---
        self.DEFAULT_DURATION = self.config["focus_duration"] * 60  # 专注时长 (秒)
        self.DEFAULT_RELAX = self.config["relax_duration"] * 60     # 休息时长 (秒)
        self.DEFAULT_CYCLE_COUNT = self.config["cycle_count"]       # 总循环次数
        self.MAX_PAUSE_TIME = self.config["max_pause_time"] * 60    # 最大暂停时间(秒)

        # --- 动态变量 ---
        self.total_duration_time = 0  # 总专注时长
        self.is_running = False
        self.mode = TimerMode.FOCUS            # 当前模式：从专注开始
        self.free_seconds_elapsed = 0          # 自由模式已计秒数
        self.cycle_left = self.DEFAULT_CYCLE_COUNT  # 剩余循环次数
        self.mode_seconds_left = self.DEFAULT_DURATION  # 当前模式剩余时间 (秒)
        self.current_focus_start_time = QDateTime()  # 存储当前专注时段的开始时间
        self.duration_task_name = DEFAULT_TASK_NAME  # 当前时间段所做的任务
        self.task_completed_relax = True  # 任务完成是否选择休息
        self.task_choice_remember = False  # 是否记住上一次的选择
        self.pause_time = QDateTime.currentDateTime()

        # --- QTimer 设置 ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer_tick)

        # --- 音效设置 ---
        self._init_sound()

        # --- 系统托盘设置 ---
        self._init_tray_icon()

        # --- 初始化显示 ---
        self._update_display()
        self._update_total_duration_display()
        self._update_mode_label()
        self._update_cycle_label()

        # --- 加载历史数据 ---
        loaded_data = self._load_time_data()
        self.focus_log = loaded_data if loaded_data is not None else {}
        self._update_total_duration_display()

    def _init_sound(self):
        """初始化音效"""
        self.sound_effect = None
        try:
            # TODO尝试加载系统提示音，换一个更好的
            sound_paths = [
                os.path.join(self.script_dir, "notification.wav"),
                "C:/Windows/Media/Windows Notify System Generic.wav",
                "C:/Windows/Media/chimes.wav",
            ]

            for path in sound_paths:
                if os.path.exists(path):
                    self.sound_effect = QSoundEffect()
                    self.sound_effect.setSource(QUrl.fromLocalFile(path))
                    self._update_sound_volume()
                    print(f"音效加载成功: {path}")
                    break

            if not self.sound_effect:
                print("未找到音效文件，提示音已禁用")
        except Exception as e:
            print(f"音效初始化失败: {e}")
            self.sound_effect = None

    def _update_sound_volume(self):
        """更新音效音量"""
        if self.sound_effect:
            volume = self.config.get("sound_volume", 80) / 100.0
            self.sound_effect.setVolume(volume)

    def _play_notification_sound(self):
        """播放提示音"""
        if self.config.get("sound_enabled", True) and self.sound_effect:
            self.sound_effect.play()

    def _init_tray_icon(self):
        """初始化系统托盘图标和菜单"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            icon_path = os.path.join(self.script_dir, "icon.ico")
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
            else:
                self.tray_icon.setIcon(self.windowIcon())
            self.tray_icon.setToolTip("番茄钟计时器")

            # 创建托盘菜单
            tray_menu = QMenu()

            # 开始/暂停 操作
            self.tray_start_action = QAction("开始", self)
            self.tray_start_action.triggered.connect(self._toggle_timer)
            tray_menu.addAction(self.tray_start_action)

            # 重置操作
            reset_action = QAction("重置", self)
            reset_action.triggered.connect(self._reset_timer)
            tray_menu.addAction(reset_action)

            tray_menu.addSeparator()

            # 显示窗口
            show_action = QAction("显示窗口", self)
            show_action.triggered.connect(self._show_and_activate)
            tray_menu.addAction(show_action)

            # 最小化到托盘
            hide_action = QAction("最小化到托盘", self)
            hide_action.triggered.connect(self.hide)
            tray_menu.addAction(hide_action)

            # 设置
            settings_action = QAction("设置", self)
            settings_action.triggered.connect(self._open_settings)
            tray_menu.addAction(settings_action)

            tray_menu.addSeparator()

            # 退出
            quit_action = QAction("退出", self)
            quit_action.triggered.connect(self._quit_application)
            tray_menu.addAction(quit_action)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self._on_tray_activated)
            self.tray_icon.setVisible(True)
        else:
            self.tray_icon = None

    def _show_and_activate(self):
        """恢复并激活窗口"""
        self.showNormal()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        """托盘图标被点击时切换显示/隐藏窗口"""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self._show_and_activate()

    def _minimize_window(self):
        """顶部最小化按钮点击响应"""
        if self.config.get("minimize_to_tray", False):
            self._minimize_to_tray()
        else:
            self.showMinimized()

    def _minimize_to_tray(self):
        """最小化到系统托盘"""
        self.hide()
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "番茄钟计时器",
                "已最小化到系统托盘，点击托盘图标可恢复显示。",
                QSystemTrayIcon.MessageIcon.Information,
                1500
            )

    def _quit_application(self):
        """从托盘彻底退出程序"""
        self._force_quit = True
        self.close()
        QApplication.quit()

    def changeEvent(self, event):
        """监听窗口状态变化（例如标题栏最小化）"""
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized() and self.config.get("minimize_to_tray", False):
                QTimer.singleShot(0, self.hide)
        super().changeEvent(event)

    def paintEvent(self, event):
        """绘制参考图上的背景插画与植物叶片"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        # 按当前模式匹配四角柔和波浪装饰颜色
        if self.mode == TimerMode.RELAX:
            wave_color = QColor(255, 224, 185, 75)
        elif self.mode == TimerMode.CANCELLED:
            wave_color = QColor(198, 222, 255, 75)
        else:
            wave_color = QColor(255, 218, 218, 70)

        # 1. 左上角柔和波浪装饰
        top_wave = QPainterPath()
        top_wave.moveTo(0, 0)
        top_wave.lineTo(w * 0.28, 0)
        top_wave.cubicTo(w * 0.22, h * 0.08, w * 0.06, h * 0.14, 0, h * 0.16)
        top_wave.closeSubpath()
        painter.fillPath(top_wave, wave_color)

        # 2. 右下角柔和波浪装饰
        bot_wave = QPainterPath()
        bot_wave.moveTo(w, h)
        bot_wave.lineTo(w * 0.65, h)
        bot_wave.cubicTo(w * 0.70, h * 0.90, w * 0.88, h * 0.84, w, h * 0.82)
        bot_wave.closeSubpath()
        painter.fillPath(bot_wave, wave_color)

        # 3. 左下角绿色清新植物叶片插画
        leaf_path = os.path.join(self.script_dir, "assets", "leaf_deco.svg")
        if os.path.exists(leaf_path):
            renderer = QSvgRenderer(leaf_path)
            if renderer.isValid():
                target_rect = QRectF(-10, h - 110, 110, 110)
                renderer.render(painter, target_rect)

    def _toggle_mode_capsule(self):
        """点击顶部模式胶囊快速在专注模式与自由模式之间切换"""
        if not self.is_running:
            if self.mode == TimerMode.FOCUS:
                self.mode = TimerMode.CANCELLED
                self.free_seconds_elapsed = 0
            else:
                self.mode = TimerMode.FOCUS
                self.mode_seconds_left = self.DEFAULT_DURATION
            self._update_display()
            self._update_mode_label()
            self._update_cycle_label()
            self._apply_style()
        else:
            self._show_notification("提示", "当前计时进行中，请先暂停后再切换模式")

    def _update_tray_action_text(self):
        """更新托盘菜单中的开始/暂停文本"""
        if hasattr(self, 'tray_start_action'):
            self.tray_start_action.setText("暂停" if self.is_running else "开始")

    def _apply_style(self):
        """根据当前模式设置动态属性并加载应用对应的 QSS 样式表"""
        if self.mode == TimerMode.RELAX:
            self.setProperty("timerMode", "relax")
            qss_file = "relax.qss"
        elif self.mode == TimerMode.CANCELLED:
            self.setProperty("timerMode", "free")
            qss_file = "free.qss"
        else:
            self.setProperty("timerMode", "focus")
            qss_file = "focus.qss"
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        qss_path = os.path.join(script_dir, qss_file)
        if os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    qss_content = f.read().replace("{ASSET_DIR}", script_dir.replace("\\", "/"))
                    self.setStyleSheet(qss_content)
                print(f"✓ 已加载并应用模式样式表: {qss_file}")
            except Exception as e:
                print(f"✗ 无法加载模式样式表 {qss_file}: {e}")
        
        # 触发样式刷新
        self.style().unpolish(self)
        self.style().polish(self)


    def _update_mode_label(self):
        """更新模式标签显示"""
        mode_text = {
            TimerMode.FOCUS: "专注模式",
            TimerMode.RELAX: "休息时间",
            TimerMode.COMPLETED: "已完成",
            TimerMode.CANCELLED: "自由模式"
        }
        self.ui.mode_label.setText(mode_text.get(self.mode, "专注模式"))
        if self.mode == TimerMode.FOCUS:
            self.ui.mode_label.setToolTip("当前: 专注模式 (点击切换至自由模式)")
        elif self.mode == TimerMode.CANCELLED:
            self.ui.mode_label.setToolTip("当前: 自由模式 (点击切换至专注模式)")
        else:
            self.ui.mode_label.setToolTip("点击切换模式")

    def _update_cycle_label(self):
        """更新循环次数标签"""
        if self.mode == TimerMode.CANCELLED:
            self.ui.cycle_label.setText("∞")
        else:
            self.ui.cycle_label.setText(str(self.cycle_left))

    def _load_config(self) -> dict:
        """加载配置文件"""
        if os.path.exists(self.CONFIG_FILE_FULL_PATH):
            try:
                with open(self.CONFIG_FILE_FULL_PATH, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并默认配置和加载的配置
                    return {**DEFAULT_CONFIG, **loaded_config}
            except Exception as e:
                print(f"加载配置失败: {e}")
        return DEFAULT_CONFIG.copy()

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.CONFIG_FILE_FULL_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print(f"配置已保存到: {self.CONFIG_FILE_FULL_PATH}")
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = dialog.get_config()
            self._save_config()
            self._apply_config()
            QMessageBox.information(self, "设置", "设置已保存！下次重置后生效。")

    def _apply_config(self):
        """应用配置到当前实例"""
        self.DEFAULT_DURATION = self.config["focus_duration"] * 60
        self.DEFAULT_RELAX = self.config["relax_duration"] * 60
        self.DEFAULT_CYCLE_COUNT = self.config["cycle_count"]
        self.MAX_PAUSE_TIME = self.config["max_pause_time"] * 60
        self._update_sound_volume()

    def _connect_signals(self):
        # 连接开始/暂停按钮到控制函数
        self.ui.startButton.clicked.connect(self._toggle_timer)
        # 连接结束任务按钮到控制函数
        self.ui.finishButton.clicked.connect(self._task_complete)
        # 连接设置按钮
        self.ui.settingsButton.clicked.connect(self._open_settings)
        # 连接顶部模式切换胶囊
        self.ui.mode_label.clicked.connect(self._toggle_mode_capsule)
        # 连接时钟内部小胶囊点击快速开始/暂停
        self.liquid_timer.clicked.connect(self._toggle_timer)
        # 注意：重置、切换模式、查看时间轴已移至"更多"菜单中，在 _create_more_menu 中连接

    @report
    def _view_timeline(self, *args, **kwargs):
        """查看时间轴按钮点击事件处理函数"""
        try:
            # 因为打开时间轴时当前的时间可能没有记录 保存文件
            if self.is_running:
                self._recode_focus_log()  # 记录当前专注时段到内存
            self.save_time_data(self.focus_log)

            # 导入并启动日历时间轴窗口
            from calendar_timeline import CalendarTimelineWindow

            # 创建并显示日历时间轴窗口
            self.timeline_window = CalendarTimelineWindow()
            self.timeline_window.show()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开时间轴：{str(e)}")

    @report
    @error_data_save
    def _task_complete(self, *args, **kwargs):
        # 记录当前时间 暂停时结束任务不需要记录
        if self.is_running:
            self._recode_focus_log()
        # 只在专注模式下询问是否休息
        if self.mode == TimerMode.FOCUS:
            # 在专注时间段中是否休息
            if not self.task_choice_remember:
                # 没有记住选择 询问是否休息和用户是否记住
                reply = QMessageBox.question(
                    self, "休息吗", "是否休息？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

                # 保存用户的选择
                if reply == QMessageBox.StandardButton.Yes:
                    self.task_completed_relax = True
                else:
                    self.task_completed_relax = False

                # 询问是否记住选择
                remember_reply = QMessageBox.question(
                    self, "记住我的选择", "是否记住我的选择？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

                if remember_reply == QMessageBox.StandardButton.Yes:
                    self.task_choice_remember = True

            # 根据选择切换模式
            if self.task_completed_relax:
                self.mode = TimerMode.RELAX
                self.mode_seconds_left = self.DEFAULT_RELAX
            else:
                self.mode = TimerMode.FOCUS
                self.mode_seconds_left = self.DEFAULT_DURATION

            # 更新显示
            self._update_display()
        else:
            self.free_seconds_elapsed = 0
            self._update_display()

        # 询问下一个任务 - 使用图形界面输入对话框
        print('timer stop to ask task name')
        self.timer.stop()
        self.is_running = False
        text, ok = TaskInputDialog.getText(self, 
                                        "输入任务名",
                                        "请输入下一个任务名称："
                                        )
        # 记录新的专注时段的开始时间
        self.current_focus_start_time = QDateTime.currentDateTime()
        if ok and text.strip():
            self.duration_task_name = text.strip()
        else:
            self.duration_task_name = DEFAULT_TASK_NAME
        print('get task name, timer start')
        self.ui.startButton.setText(" 暂停专注")
        pause_icon = os.path.join(self.script_dir, "assets", "icon_pause.svg")
        if os.path.exists(pause_icon):
            self.ui.startButton.setIcon(QIcon(pause_icon))
        self.timer.start(1000)
        self.is_running = True

    @report
    @error_data_save
    def _toggle_timer(self, *args, **kwargs):
        """槽函数：开始、暂停计时器"""
        print(f'按下切换键当前：{self.is_running}')
        if not self.is_running:
            if self.mode == TimerMode.FOCUS or self.mode == TimerMode.CANCELLED:
                # 如果是第一次启动 询问用户当前所做的任务
                if self.duration_task_name == DEFAULT_TASK_NAME:
                    # 使用图形界面输入对话框询问当前任务
                    text, ok = TaskInputDialog.getText(
                        self, "输入任务名", "请输入当前任务名称：")
                    if ok and text.strip():
                        self.duration_task_name = text.strip()
                    else:
                        self.duration_task_name = DEFAULT_TASK_NAME

                # 如果大于了最大暂停阈值 重新设置当前专注时间
                current_time = QDateTime.currentDateTime()
                pause_duration_time = self.pause_time.secsTo(current_time)

                if self.mode != TimerMode.CANCELLED and pause_duration_time > self.MAX_PAUSE_TIME:
                    self.mode_seconds_left = self.DEFAULT_DURATION  # 直接重置当前剩余时间

                # 记录专注时段的开始时间
                self.current_focus_start_time = QDateTime.currentDateTime()
            if self.mode == TimerMode.COMPLETED:
                self._reset_timer()  # 完成后重新开始
            print('pressed start key, timer start')
            self.timer.start(1000)  # 每 1000ms (1秒) 触发一次
            self.is_running = True
            self.ui.startButton.setText(" 暂停专注")
            pause_icon = os.path.join(self.script_dir, "assets", "icon_pause.svg")
            if os.path.exists(pause_icon):
                self.ui.startButton.setIcon(QIcon(pause_icon))

            # 更新番茄组件显示
            self._update_display()
        else:
            print('pressed pause key, timer stop')
            self.timer.stop()  # 停止 QTimer，状态保持不变
            self.is_running = False
            self.pause_time = QDateTime.currentDateTime()  # 记录当前暂停时间
            # 如果当前是专注时间段 暂停后记于内存 精细化追踪
            if self.mode == TimerMode.FOCUS or self.mode == TimerMode.CANCELLED:
                self._recode_focus_log()
            self.ui.startButton.setText(" 继续专注")
            play_icon = os.path.join(self.script_dir, "assets", "icon_play.svg")
            if os.path.exists(play_icon):
                self.ui.startButton.setIcon(QIcon(play_icon))

            # 更新番茄组件显示（重要：让番茄进入暂停状态）
            self._update_display()

        # 更新托盘菜单文本
        self._update_tray_action_text()

    def _update_timer_tick(self):
        """QTimer 每秒触发的槽函数：倒数、切换模式、更新 UI、记录学习总时长"""

        if self.mode == TimerMode.CANCELLED:
            # 自由模式：正向计时，无时间上限
            self.total_duration_time += 1
            self.free_seconds_elapsed += 1
            self._update_total_duration_display()
            self._update_display()
        elif self.mode_seconds_left > 0:
            # 如果为专注段增加学习总时长
            if self.mode == TimerMode.FOCUS:
                self.total_duration_time += 1
                self._update_total_duration_display()
            self.mode_seconds_left -= 1
            self._update_display()
        else:
            # 当前模式时间结束，执行模式切换
            print(
                f'mode_seconds_left<=0开始切换模式,mode_seconds_left={self.mode_seconds_left}')
            print('switch mode, timer stop')
            self.timer.stop()
            self.is_running = False
            self._switch_mode()

    def _show_notification(self, title, message, icon=QSystemTrayIcon.MessageIcon.Warning):
        """使用系统托盘显示非阻塞通知，如果不可用则打印到控制台"""
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, 3000)  # 显示3秒
        else:
            print(f"通知: {title} - {message}")

    @report
    @error_data_save
    def _switch_mode(self, *args, **kwargs):
        """核心逻辑：根据当前模式切换到下一个模式"""
        if self.mode == TimerMode.FOCUS:
            # 专注 -> 休息 或 完成
            self._recode_focus_log()  # 记录当前专注时段到内存
            self._play_notification_sound()  # 播放提示音

            if self.cycle_left > 1:
                self._show_notification(
                    "休息时间到!", f"恭喜你完成了好好休息，还剩下{self.cycle_left-1}次专注")
                self.mode = TimerMode.RELAX
                self.mode_seconds_left = self.DEFAULT_RELAX
                self.cycle_left -= 1  # 完成一个专注时段，循环计数减 1
                self._apply_style()  # 应用休息模式样式
                self._update_mode_label()
                self._update_cycle_label()
            else:
                # 最后一个专注时段结束
                self.mode = TimerMode.COMPLETED
                self.mode_seconds_left = 0
                self.ui.startButton.setText("完成")
                self._show_notification(
                    "恭喜您", "所有的专注时间段均已完成", QSystemTrayIcon.MessageIcon.Information)
                self._update_mode_label()
                self.is_running = False
                return  # 退出，不再启动计时器

        elif self.mode == TimerMode.RELAX:
            # 休息 -> 专注
            self._play_notification_sound()  # 播放提示音
            self.mode = TimerMode.FOCUS
            self.mode_seconds_left = self.DEFAULT_DURATION
            # 记录新的专注时段的开始时间
            self.current_focus_start_time = QDateTime.currentDateTime()
            self._apply_style()  # 应用专注模式样式
            self._update_mode_label()

            self._show_notification(
                "休息结束，开始专注！", f"现在是新的专注时段，剩余 {self.DEFAULT_DURATION // 60} 分钟。")

        elif self.mode == TimerMode.CANCELLED:
            self.free_seconds_elapsed = 0
            self._update_mode_label()
            self._update_cycle_label()
            self._update_display()
            return

        print('switched model successfully , timer start')
        self.timer.start(1000)
        self.is_running = True
        self.ui.startButton.setText("暂停")
        self._update_tray_action_text()

    @report
    def _reset_timer(self, *args, **kwargs):
        """重置所有状态"""
        print('reset all , timer stop')
        self.timer.stop()
        self.is_running = False
        self.free_seconds_elapsed = 0
        self.mode = TimerMode.FOCUS
        self.cycle_left = self.DEFAULT_CYCLE_COUNT
        self.mode_seconds_left = self.DEFAULT_DURATION
        self.ui.startButton.setText(" 开始专注")
        play_icon = os.path.join(self.script_dir, "assets", "icon_play.svg")
        if os.path.exists(play_icon):
            self.ui.startButton.setIcon(QIcon(play_icon))
        self._apply_style()  # 应用专注模式样式
        self._update_mode_label()
        self._update_cycle_label()
        self._update_display()
        self._update_tray_action_text()

    def _load_time_data(self):
        """从 JSON 文件加载专注数据，如果文件不存在或损坏则返回 {}。"""
        file_path = self.DATA_FILE_FULL_PATH  # 使用完整路径
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # 初始化当前学习总时间
                    current_day = QDateTime.currentDateTime().toString("yyyy-MM-dd")

                    data = json.load(f)
                    current_day_data = data.get(current_day, [])
                    self.total_duration_time = sum(
                        [item["duration"] for item in current_day_data])

                    return data
            except json.JSONDecodeError:
                print(f"警告: 数据文件 {self.DATA_FILE} 损坏或格式错误。将使用空记录。")
                return {}
            except Exception as e:
                print(f"错误: 无法加载数据文件: {e}")
                return {}
        else:
            return {}

    def save_time_data(self, data):
        """程序结束最终保存数据（原子写入，防止写入中途崩溃导致文件损坏）"""
        file_path = self.DATA_FILE_FULL_PATH  # 使用完整路径
        temp_file_path = file_path + ".tmp"
        try:
            # 1. 先写入临时文件
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            # 2. 原子性替换原文件
            if os.path.exists(file_path):
                os.replace(temp_file_path, file_path)
            else:
                os.rename(temp_file_path, file_path)
                
            print(f"数据已成功原子保存到: {self.DATA_FILE},路径为{file_path}")
        except Exception as e:
            print(f"保存数据失败: {e}")
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass


    @report
    @error_data_save
    def _recode_focus_log(self, *args, **kwargs):
        """记录专注时段(临时存于内存)"""

        # 确保开始时间存在并且不要在暂停的时候记录
        if not self.current_focus_start_time.isValid() and not self.is_running:
            return
        # WARNING 需要注意start time是在外部一次记录好的而end time是当前时间 有多个地方调用函数导致出现重复记录的问题
        end_time = QDateTime.currentDateTime()
        start_time = self.current_focus_start_time

        # 记录实际运行时间（秒），即使中途被暂停，记录的也是该时段的总时长
        duration = start_time.secsTo(end_time)
        # 避免记录负值或无效记录
        if duration <= 0:
            return

        DATA_FORM = "yyyy-MM-dd"
        TIME_FORM = "HH:mm:ss"

        data_key = start_time.toString(DATA_FORM)

        new_log = {
            "mode": self.mode,  # FOCUS
            "task-name": self.duration_task_name,
            "start": start_time.toString(TIME_FORM),
            "end": end_time.toString(TIME_FORM),
            "duration": duration
        }

        # 仅更新内存中的 focus_log
        day_recode = self.focus_log.get(data_key, [])
        if day_recode:
            # 解决重复记录问题

            last_record = day_recode[-1]
            last_start = self.time_to_seconds(last_record["start"])
            last_end = self.time_to_seconds(last_record["end"])
            new_start = self.time_to_seconds(new_log["start"])
            new_end = self.time_to_seconds(new_log["end"])
            print(f'上次记录：{last_record}, 新记录：{new_log}')
            # 如果新纪录在开始时间上一条时间段内但结果更晚 则直接更新上一条的end时间和duration即可
            if last_start <= new_start <= last_end and new_end > last_end:
                # 覆盖最后一条记录
                last_record["end"] = new_log["end"]
                last_record["duration"] = self.time_to_seconds(
                    last_record["end"]) - self.time_to_seconds(last_record["start"])
                print(f"内存记录更新覆盖：{data_key}, 时长：{last_record['duration']}秒")
                return
        else:
            self.focus_log[data_key] = []
        # 新的时间段 在对应日期下直接添加新记录即可
        self.focus_log[data_key].append(new_log)
        print(f"内存记录新增：{data_key}, 时长：{duration}秒")

    # ✅ 修正：这是标准的 PyQt 退出事件处理函数
    def closeEvent(self, event: QCloseEvent):
        """
        重写 closeEvent，在用户关闭窗口时执行最终清理和数据保存。
        """
        # 如果开启了“关闭窗口时最小化到系统托盘”且不是强制退出，则隐藏到托盘
        if not getattr(self, '_force_quit', False) and self.config.get("close_to_tray", False):
            event.ignore()
            self.hide()
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    "番茄钟计时器",
                    "番茄钟已最小化到托盘并在后台运行。",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
            return

        print("程序退出事件触发：正在执行最终数据保存...")

        # 1. 停止计时器
        if self.is_running:
            self.timer.stop()
            self.is_running = False
        # 2. 执行最终保存
        self.save_time_data(self.focus_log)

        # 3. 允许窗口关闭
        event.accept()

    """更新显示"""

    def _update_total_duration_display(self):
        total_seconds = self.total_duration_time
        # 使用与当前计时器相同的格式化逻辑
        hours = total_seconds // 3600
        remaining_seconds = total_seconds % 3600
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        if hours > 0:
            time_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_text = f"{minutes:02d}:{seconds:02d}"

        # 更新卡片数值显示
        self.ui.timer_duration_laber.setText(time_text)

    def _update_display(self):
        """更新液体时间显示组件"""
        # 更新液体组件的时间
        mode_map = {
            TimerMode.FOCUS: "focus",
            TimerMode.RELAX: "relax",
            TimerMode.CANCELLED: "cancelled",
            TimerMode.COMPLETED: "focus"
        }

        liquid_mode = mode_map.get(self.mode, "focus")
        self.liquid_timer.set_mode(liquid_mode)
        self.liquid_timer.set_running(self.is_running)

        if self.mode == TimerMode.CANCELLED:
            self.liquid_timer.set_time(
                self.DEFAULT_DURATION,
                self.free_seconds_elapsed
            )
            if hasattr(self, 'cancel_action'):
                self.cancel_action.setText("切换至专注模式")
            elif len(self.more_menu.actions()) > 1:
                self.more_menu.actions()[1].setText("切换至专注模式")
        else:
            self.liquid_timer.set_time(
                self._get_current_total_duration(),
                self.mode_seconds_left
            )
            if hasattr(self, 'cancel_action'):
                self.cancel_action.setText("切换至自由模式")
            elif len(self.more_menu.actions()) > 1:
                self.more_menu.actions()[1].setText("切换至自由模式")
    def _get_current_total_duration(self):
        """获取当前模式的总时长"""
        if self.mode == TimerMode.FOCUS or self.mode == TimerMode.CANCELLED:
            return self.DEFAULT_DURATION
        elif self.mode == TimerMode.RELAX:
            return self.DEFAULT_RELAX
        else:
            return self.mode_seconds_left
    @report
    def _cancel_tomato_clock(self, *args, **kwargs):
        """通过更多菜单触发模式切换"""
        self._toggle_mode_capsule()

    def time_to_seconds(self, time_str):
        """接收 HH:MM:SS 或 MM:SS 格式的时间字符串，返回对应的秒数整数"""
        h, m, s = map(int, time_str.split(":"))
        return h*3600 + m*60 + s


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.main_window = TimerWindow()
    window = app.main_window
    window.show()
    print(f"我的 PID 是 → {os.getpid()}")
    sys.exit(app.exec())

