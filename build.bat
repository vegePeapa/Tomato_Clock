@echo off
echo ==================================================
echo         番茄钟 (TomatoClock) 一键打包工具
echo ==================================================
echo.

:: 检查并定位虚拟环境
set "VENV_DIR=C:\Users\86177\codeFile\pycharmProjects\GUI-pyQt\venv"
if not exist "%VENV_DIR%\Scripts\python.exe" set "VENV_DIR=..\venv"
if not exist "%VENV_DIR%\Scripts\python.exe" set "VENV_DIR=venv"

if exist "%VENV_DIR%\Scripts\python.exe" (
    set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
    set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"
    set "VENV_PYINSTALLER=%VENV_DIR%\Scripts\pyinstaller.exe"
) else (
    echo [警告] 未检测到虚拟环境，将使用系统全局 Python 环境进行打包。
    set "VENV_PYTHON=python"
    set "VENV_PIP=pip"
    set "VENV_PYINSTALLER=pyinstaller"
)

:: 检查是否安装了 PyInstaller
echo [1/3] 正在检查依赖环境...
"%VENV_PYTHON%" -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo [信息] 正在安装 PyInstaller 打包依赖...
    "%VENV_PIP%" install pyinstaller
) else (
    echo [OK] PyInstaller 依赖检测通过。
)

:: 执行打包
echo.
echo [2/3] 正在开始打包 (这可能需要 1 到 2 分钟)...
"%VENV_PYINSTALLER%" TomatoClock.spec

if %errorlevel% equ 0 (
    echo.
    echo ==================================================
    echo [3/3] [OK] 打包完成！
    echo 可执行程序已输出至: dist\TomatoClock.exe
    echo ==================================================
) else (
    echo.
    echo [错误] 打包失败，请检查上方日志错误信息！
)

echo.
pause
