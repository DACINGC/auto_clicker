# Windows 连点器

一个轻量级的 Windows 自动连点器，使用 Python + Tkinter 构建，无需外部依赖。

## 功能

- **两种点击模式**
  - **鼠标跟随模式** — 在当前鼠标位置点击
  - **固定位置模式** — 每次在指定的屏幕坐标点击，支持准确坐标录入
- **可调节参数** — 点击间隔（毫秒）、点击次数（0 表示无限）、左键/右键
- **可自定义快捷键** — F1~F12 自由绑定开始/暂停/停止/获取坐标
- **悬浮球控件** — 屏幕右侧半透明悬浮球，展开后可快捷控制运行状态
- **后台热键监听** — 窗口未聚焦时快捷键依然生效
- **配置持久化** — 快捷键设置在 `config.json` 中保存
- **单文件可执行** — 可使用 PyInstaller 打包为独立 exe

## 快捷键

| 功能       | 默认键 | 说明       |
| ---------- | ------ | ---------- |
| 开始/继续   | F6     | 开始或继续连点 |
| 暂停       | F7     | 暂停连点     |
| 获取坐标   | F8     | 记录当前鼠标位置 |
| 停止       | F9     | 停止连点     |

快捷键可在设置页面中重映射，冲突时自动提示。

## 使用

### 直接运行

```bash
pip install pyinstaller    # 打包所需（可选）
python gui.py
```

### 打包 exe

```bash
pyinstaller --onefile --noconsole --name "Windows连点器" --distpath dist gui.py
```

生成的可执行文件位于 `dist\Windows连点器.exe`。

## 项目结构

```
auto_clicker/
├── auto_clicker.py      # 核心引擎 + Windows API 封装
├── gui.py               # Tkinter 主界面 + 热键监听 + 设置管理
├── floating.py           # 悬浮球控件（球体 + 展开面板）
├── config.json          # 快捷键配置（自动生成）
├── dist/
│   └── Windows连点器.exe # 预打包的可执行文件
└── README.md
```

## 技术要点

- 纯 `ctypes` 调用 Windows API，无第三方库
- 固定坐标点击使用 `MOUSEEVENTF_ABSOLUTE` 绕过 UIPI 限制
- 引擎线程与 GUI 分离，引擎回调通过 `root.after(0, ...)` 安全更新界面
- 悬浮球每 200ms 轮询引擎状态，主动更新显示
