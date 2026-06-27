import os
import sys
import shutil

DEFAULT_TASK_NAME = "未命名任务"
DATA_FILE = "main_data.json"
CONFIG_FILE = "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "focus_duration": 25,      # 专注时长(分钟)
    "relax_duration": 5,       # 休息时长(分钟)
    "cycle_count": 2,          # 循环次数
    "max_pause_time": 10,      # 最大暂停时间(分钟)
    "sound_enabled": True,     # 是否启用声音
    "sound_volume": 80,        # 音量(0-100)
    "auto_start_break": False,  # 自动开始休息
    "auto_start_focus": False,  # 自动开始专注
}


class TimerMode:
    FOCUS = "专注"
    RELAX = "休息"
    COMPLETED = "完成"
    CANCELLED = "专注(无番茄计时)"


def get_app_data_dir():
    r"""
    获取跨平台的应用数据目录
    Windows: C:\Users\<用户>\AppData\Local\tomato_clock\
    macOS: ~/Library/Application Support/tomato_clock/
    Linux: ~/.local/share/tomato_clock/
    """
    app_name = "tomato_clock"

    # Windows 系统
    if os.name == 'nt':
        appdata = os.environ.get('LOCALAPPDATA')
        if appdata:
            data_dir = os.path.join(appdata, app_name)
        else:
            data_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', app_name)
    # macOS 系统
    elif os.name == 'posix' and sys.platform == 'darwin':
        data_dir = os.path.expanduser(f'~/Library/Application Support/{app_name}')
    # Linux 系统
    else:
        data_dir = os.path.expanduser(f'~/.local/share/{app_name}')

    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir, exist_ok=True)
            print(f"✓ 创建数据目录: {data_dir}")
        except Exception as e:
            print(f"✗ 创建数据目录失败: {e}")
            data_dir = os.path.dirname(os.path.abspath(__file__))
            print(f"⚠️ 使用程序目录: {data_dir}")

    return data_dir


DATA_DIR = get_app_data_dir()
DATA_FILE_FULL_PATH = os.path.join(DATA_DIR, DATA_FILE)
CONFIG_FILE_FULL_PATH = os.path.join(DATA_DIR, CONFIG_FILE)


def migrate_data_to_user_dir():
    """检查程序目录是否有旧数据，如果有则迁移到用户目录"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    old_data_file = os.path.join(script_dir, DATA_FILE)
    old_config_file = os.path.join(script_dir, CONFIG_FILE)

    has_old_data = os.path.exists(old_data_file)
    has_old_config = os.path.exists(old_config_file)

    if not has_old_data and not has_old_config:
        return

    print("🔄 检测到旧数据，开始迁移...")
    try:
        if has_old_data and not os.path.exists(DATA_FILE_FULL_PATH):
            shutil.copy2(old_data_file, DATA_FILE_FULL_PATH)
            print(f"✓ 数据文件已迁移到: {DATA_FILE_FULL_PATH}")

        if has_old_config and not os.path.exists(CONFIG_FILE_FULL_PATH):
            shutil.copy2(old_config_file, CONFIG_FILE_FULL_PATH)
            print(f"✓ 配置文件已迁移到: {CONFIG_FILE_FULL_PATH}")

        # 备份旧文件
        if has_old_data:
            backup_file = old_data_file + ".bak"
            if not os.path.exists(backup_file):
                os.rename(old_data_file, backup_file)
                print(f"✓ 旧数据文件已备份: {backup_file}")

        if has_old_config:
            backup_file = old_config_file + ".bak"
            if not os.path.exists(backup_file):
                os.rename(old_config_file, backup_file)
                print(f"✓ 旧配置文件已备份: {backup_file}")

        print("✅ 数据迁移完成！")
    except Exception as e:
        print(f"⚠️ 数据迁移失败: {e}")
        print("💡 提示：旧数据仍保留在程序目录中")

# 加载模块时执行迁移
migrate_data_to_user_dir()
