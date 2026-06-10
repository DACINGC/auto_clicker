import json
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from auto_clicker import (
    AutoClickerEngine,
    get_cursor_position,
    is_key_pressed,
    KEY_MAP,
    DEFAULT_HOTKEYS,
)
from floating import FloatingWidget


class AutoClickerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows 连点器")
        self.root.geometry("560x520")
        self.root.resizable(False, False)

        self._closing = threading.Event()
        self._hotkey_thread = None

        self.engine = AutoClickerEngine()
        self.engine.on_status = lambda msg: self.safe_after(
            0,
            self._set_status,
            msg
        )
        self.engine.on_stopped = lambda: self.safe_after(
            0,
            self._on_engine_stopped
        )

        self._config_path = self._get_config_path()
        self.hotkey_map = self._load_config()

        self.build_ui()
        self.start_hotkey_listener()

        self.floating = FloatingWidget(self.engine, self.root, self)
        self.floating.hide()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── Config ────────────────────────────────────────────

    @staticmethod
    def _get_config_path():
        return os.path.join(os.path.dirname(__file__), "config.json")

    def _load_config(self):
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            hotkeys = {}
            for action, info in data.items():
                name = info.get("name", DEFAULT_HOTKEYS[action]["name"])
                vk = KEY_MAP.get(name, DEFAULT_HOTKEYS[action]["vk"])
                hotkeys[action] = {"name": name, "vk": vk}
            return hotkeys
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return {k: dict(v) for k, v in DEFAULT_HOTKEYS.items()}

    def _save_config(self):
        data = {k: {"name": v["name"]} for k, v in self.hotkey_map.items()}
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _hotkey_label(self, action):
        return self.hotkey_map[action]["name"]

    def _refresh_tip(self):
        s = self._hotkey_label("start")
        p = self._hotkey_label("pause")
        c = self._hotkey_label("capture")
        t = self._hotkey_label("stop")
        self._tip_var.set(
            f"快捷键：{s} 开始/继续，{p} 暂停，{c} 获取坐标，{t} 停止"
        )

    def _refresh_button_labels(self):
        self.start_button.config(text=f"开始 {self._hotkey_label('start')}")
        self.pause_button.config(text=f"暂停 {self._hotkey_label('pause')}")
        self.stop_button.config(text=f"停止 {self._hotkey_label('stop')}")
        self.capture_btn.config(text=f"记录鼠标位置 {self._hotkey_label('capture')}")

    # ── UI ────────────────────────────────────────────────

    def build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=(5, 0))

        # ════════════════════════════════════════════════════
        # Tab 1: 主页面
        # ════════════════════════════════════════════════════
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="  主页面  ")

        title = tk.Label(
            main_tab,
            text="Windows 连点器",
            font=("Microsoft YaHei", 18, "bold")
        )
        title.pack(pady=(15, 10))

        content = ttk.Frame(main_tab)
        content.pack(fill="both", expand=True, padx=15)

        # ── 点击设置 ──
        interval_frame = ttk.LabelFrame(content, text="点击设置")
        interval_frame.pack(fill="x", pady=5)

        ttk.Label(
            interval_frame,
            text="点击间隔："
        ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

        self.interval_var = tk.StringVar(value="100")
        ttk.Entry(
            interval_frame,
            textvariable=self.interval_var,
            width=12
        ).grid(row=0, column=1, padx=5)

        ttk.Label(
            interval_frame,
            text="毫秒"
        ).grid(row=0, column=2, padx=5, sticky="w")

        ttk.Label(
            interval_frame,
            text="点击次数："
        ).grid(row=1, column=0, padx=10, pady=8, sticky="w")

        self.count_var = tk.StringVar(value="0")
        ttk.Entry(
            interval_frame,
            textvariable=self.count_var,
            width=12
        ).grid(row=1, column=1, padx=5)

        ttk.Label(
            interval_frame,
            text="0 表示无限"
        ).grid(row=1, column=2, padx=5, sticky="w")

        # ── 鼠标按键 ──
        button_frame = ttk.LabelFrame(content, text="鼠标按键")
        button_frame.pack(fill="x", pady=5)

        self.mouse_button_var = tk.StringVar(value="left")

        ttk.Radiobutton(
            button_frame,
            text="左键",
            variable=self.mouse_button_var,
            value="left"
        ).pack(side="left", padx=30, pady=8)

        ttk.Radiobutton(
            button_frame,
            text="右键",
            variable=self.mouse_button_var,
            value="right"
        ).pack(side="left", padx=30, pady=8)

        # ── 点击模式 ──
        position_frame = ttk.LabelFrame(content, text="点击模式")
        position_frame.pack(fill="x", pady=5)

        self.click_mode_var = tk.StringVar(value="cursor")

        self.mode_sel_frame = ttk.Frame(position_frame)
        self.mode_sel_frame.pack(fill="x", padx=10, pady=6)

        self.mode_follow_rb = ttk.Radiobutton(
            self.mode_sel_frame,
            text="鼠标跟随模式",
            variable=self.click_mode_var,
            value="cursor",
            command=self._on_mode_change
        )
        self.mode_follow_rb.pack(side="left", padx=(0, 20))

        self.mode_fixed_rb = ttk.Radiobutton(
            self.mode_sel_frame,
            text="固定位置模式",
            variable=self.click_mode_var,
            value="fixed",
            command=self._on_mode_change
        )
        self.mode_fixed_rb.pack(side="left")

        self.fixed_coord_frame = ttk.Frame(position_frame)

        ttk.Label(
            self.fixed_coord_frame,
            text="点击坐标："
        ).grid(row=0, column=0, padx=(15, 5), pady=6, sticky="w")

        ttk.Label(
            self.fixed_coord_frame,
            text="X："
        ).grid(row=0, column=1, padx=2, pady=6, sticky="e")

        self.x_var = tk.StringVar(value="0")
        self.x_entry = ttk.Entry(
            self.fixed_coord_frame,
            textvariable=self.x_var,
            width=8
        )
        self.x_entry.grid(row=0, column=2, padx=3, pady=6)

        ttk.Label(
            self.fixed_coord_frame,
            text="Y："
        ).grid(row=0, column=3, padx=2, pady=6, sticky="e")

        self.y_var = tk.StringVar(value="0")
        self.y_entry = ttk.Entry(
            self.fixed_coord_frame,
            textvariable=self.y_var,
            width=8
        )
        self.y_entry.grid(row=0, column=4, padx=3, pady=6)

        self.capture_btn = ttk.Button(
            self.fixed_coord_frame,
            text=f"记录鼠标位置 {self._hotkey_label('capture')}",
            command=self.capture_position
        )
        self.capture_btn.grid(row=0, column=5, padx=(10, 5), pady=6)

        self.mode_info_var = tk.StringVar(value="跟随鼠标位置，移动到哪点击到哪")
        self.mode_info_label = tk.Label(
            position_frame,
            textvariable=self.mode_info_var,
            fg="#555",
            font=("Microsoft YaHei", 9)
        )
        self.mode_info_label.pack(fill="x", padx=10, pady=(0, 2))

        self.mode_tip_var = tk.StringVar(value="提示：运行中不可切换模式，可先暂停再切换")
        mode_tip_label = tk.Label(
            position_frame,
            textvariable=self.mode_tip_var,
            fg="#999",
            font=("Microsoft YaHei", 8)
        )
        mode_tip_label.pack(fill="x", padx=10, pady=(0, 6))

        self._on_mode_change()

        # ── 控制按钮 ──
        control_frame = ttk.Frame(content)
        control_frame.pack(fill="x", pady=(12, 5))

        self.start_button = ttk.Button(
            control_frame,
            text=f"开始 {self._hotkey_label('start')}",
            command=self.start_or_resume
        )
        self.start_button.pack(side="left", expand=True, fill="x", padx=3)

        self.pause_button = ttk.Button(
            control_frame,
            text=f"暂停 {self._hotkey_label('pause')}",
            command=self.pause_clicking,
            state="disabled"
        )
        self.pause_button.pack(side="left", expand=True, fill="x", padx=3)

        self.stop_button = ttk.Button(
            control_frame,
            text=f"停止 {self._hotkey_label('stop')}",
            command=self.stop_clicking,
            state="disabled"
        )
        self.stop_button.pack(side="left", expand=True, fill="x", padx=3)

        # ════════════════════════════════════════════════════
        # Tab 2: 设置
        # ════════════════════════════════════════════════════
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="  设置  ")
        settings_content = ttk.Frame(settings_tab)
        settings_content.pack(fill="both", expand=True, padx=15, pady=15)

        # ── 快捷键设置 ──
        hotkey_frame = ttk.LabelFrame(settings_content, text="快捷键设置")
        hotkey_frame.pack(fill="x", pady=(0, 10))

        keys = sorted(KEY_MAP.keys(), key=lambda k: int(k[1:]))
        hotkey_labels = {
            "start":   "开始 / 继续",
            "pause":   "暂停",
            "capture": "获取坐标",
            "stop":    "停止",
        }
        self._hk_vars = {}
        for i, action in enumerate(("start", "pause", "capture", "stop")):
            ttk.Label(hotkey_frame, text=hotkey_labels[action]).grid(
                row=i, column=0, padx=(15, 10), pady=6, sticky="w"
            )
            var = tk.StringVar(value=self.hotkey_map[action]["name"])
            cb = ttk.Combobox(hotkey_frame, textvariable=var, values=keys,
                              state="readonly", width=8)
            cb.grid(row=i, column=1, padx=5, pady=6, sticky="w")
            self._hk_vars[action] = var

        save_hk_btn = ttk.Button(
            hotkey_frame, text="保存快捷键",
            command=self._save_hotkey_settings
        )
        save_hk_btn.grid(row=4, column=0, columnspan=2, pady=(8, 10))

        # ── 悬浮球 ──
        float_frame = ttk.LabelFrame(settings_content, text="悬浮球")
        float_frame.pack(fill="x")

        self.show_float_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            float_frame,
            text="显示悬浮球（右侧小圆球，快捷控制+状态）",
            variable=self.show_float_var,
            command=self._toggle_floating
        ).pack(padx=15, pady=12, anchor="w")

        # ── 底部状态和提示（在所有标签页下方） ──
        self.status_var = tk.StringVar(value="状态：未运行")
        status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            fg="blue",
            font=("Microsoft YaHei", 10)
        )
        status_label.pack(pady=(8, 2))

        self._tip_var = tk.StringVar()
        tip = tk.Label(
            self.root,
            textvariable=self._tip_var,
            fg="gray"
        )
        tip.pack(pady=(0, 5))
        self._refresh_tip()

    def _on_mode_change(self):
        mode = self.click_mode_var.get()
        if mode == "fixed":
            self.fixed_coord_frame.pack(fill="x", padx=5, before=self.mode_info_var)
        else:
            self.fixed_coord_frame.pack_forget()
        self._update_mode_info()

        if self.engine.state == "paused":
            self._apply_settings_to_engine()

    def _apply_settings_to_engine(self):
        settings = self._validate_settings_silent()
        if settings is not None:
            self.engine.reconfigure(settings)

    def _validate_settings_silent(self):
        try:
            interval = int(self.interval_var.get())
            if interval < 1:
                return None
        except ValueError:
            return None

        try:
            count = int(self.count_var.get())
            if count < 0:
                return None
        except ValueError:
            return None

        mode = self.click_mode_var.get()
        result = {
            "interval": interval / 1000.0,
            "count": count,
            "button": self.mouse_button_var.get(),
            "mode": mode,
        }

        if mode == "fixed":
            try:
                result["x"] = int(self.x_var.get())
                result["y"] = int(self.y_var.get())
            except ValueError:
                return None

        return result

    def _update_mode_info(self):
        mode = self.click_mode_var.get()
        if mode == "cursor":
            self.mode_info_var.set("跟随鼠标位置，移动到哪点击到哪")
            self.mode_info_label.config(fg="#555")
        elif mode == "fixed":
            try:
                x = int(self.x_var.get())
                y = int(self.y_var.get())
                if x == 0 and y == 0:
                    self.mode_info_var.set("⚠ 请点击「记录鼠标位置 F8」或手动输入坐标")
                    self.mode_info_label.config(fg="#c00")
                else:
                    self.mode_info_var.set(f"每次点击前移动鼠标到 ({x}, {y}) 再点击")
                    self.mode_info_label.config(fg="#555")
            except ValueError:
                self.mode_info_var.set("固定坐标无效，请输入整数")
                self.mode_info_label.config(fg="#c00")

    def validate_settings(self):
        try:
            interval = int(self.interval_var.get())
            if interval < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "点击间隔必须是大于 0 的整数")
            return None

        try:
            count = int(self.count_var.get())
            if count < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "点击次数必须是大于等于 0 的整数")
            return None

        mode = self.click_mode_var.get()
        result = {
            "interval": interval / 1000.0,
            "count": count,
            "button": self.mouse_button_var.get(),
            "mode": mode,
        }

        if mode == "fixed":
            try:
                result["x"] = int(self.x_var.get())
                result["y"] = int(self.y_var.get())
            except ValueError:
                messagebox.showerror("错误", "固定坐标必须是整数")
                return None
            if result["x"] == 0 and result["y"] == 0:
                messagebox.showwarning("提示", "请先按 F8 记录鼠标位置，或手动输入坐标")
                return None

        return result

    # ── Settings dialog ───────────────────────────────────
    # (removed – settings are now inline in the 设置 tab)
    # ──────────────────────────────────────────────────────

    # ── Hotkey save (settings tab) ────────────────────────

    def _save_hotkey_settings(self):
        used = {}
        labels_map = {
            "start": "开始 / 继续", "pause": "暂停",
            "capture": "获取坐标", "stop": "停止",
        }
        for action, var in self._hk_vars.items():
            name = var.get()
            if name in used:
                messagebox.showwarning(
                    "冲突",
                    f"{labels_map[action]} 与 {used[name]} 使用了相同的按键 {name}"
                )
                return
            used[name] = labels_map[action]
            self.hotkey_map[action] = {"name": name, "vk": KEY_MAP[name]}
        self._save_config()
        self._refresh_button_labels()
        self._refresh_tip()
        messagebox.showinfo("提示", "快捷键已保存并生效")

    def capture_position(self):
        try:
            x, y = get_cursor_position()
        except Exception as e:
            messagebox.showerror("错误", f"获取鼠标坐标失败：{e}")
            return

        self.x_var.set(str(x))
        self.y_var.set(str(y))
        self._set_status(f"状态：已记录坐标 ({x}, {y})")
        self._update_mode_info()

        if self.engine.state == "paused":
            self._apply_settings_to_engine()

    def start_or_resume(self):
        state = self.engine.state

        if state == "paused":
            self.engine.resume()
            self._update_buttons()
            return

        if state == "idle":
            settings = self.validate_settings()
            if settings is None:
                return

            started = self.engine.start(settings)
            if started:
                self._update_buttons()

    def pause_clicking(self):
        if self.engine.state == "running":
            self.engine.pause()
            self._update_buttons()

    def stop_clicking(self):
        if self.engine.state in ("running", "paused"):
            self.engine.stop(wait=True)

        self._set_status("状态：已停止")
        self._update_buttons()

    def _update_buttons(self):
        state = self.engine.state
        sl = self._hotkey_label("start")
        pl = self._hotkey_label("pause")
        tl = self._hotkey_label("stop")

        if state == "running":
            self.start_button.config(state="disabled", text=f"开始 {sl}")
            self.pause_button.config(state="normal", text=f"暂停 {pl}")
            self.stop_button.config(state="normal", text=f"停止 {tl}")

        elif state == "paused":
            self.start_button.config(state="normal", text=f"继续 {sl}")
            self.pause_button.config(state="disabled", text=f"暂停 {pl}")
            self.stop_button.config(state="normal", text=f"停止 {tl}")

        else:
            self.start_button.config(state="normal", text=f"开始 {sl}")
            self.pause_button.config(state="disabled", text=f"暂停 {pl}")
            self.stop_button.config(state="disabled", text=f"停止 {tl}")

        can_switch = state != "running"
        sw = "normal" if can_switch else "disabled"
        self.mode_follow_rb.config(state=sw)
        self.mode_fixed_rb.config(state=sw)
        self.x_entry.config(state=sw)
        self.y_entry.config(state=sw)
        self.capture_btn.config(state=sw)

        if state == "running":
            self.mode_tip_var.set("运行中不可切换模式，请先暂停")
        elif state == "paused":
            self.mode_tip_var.set("已暂停，可自由切换模式")
        else:
            self.mode_tip_var.set("提示：运行中不可切换模式，可先暂停再切换")

    def _on_engine_stopped(self):
        self._update_buttons()

    def _set_status(self, message):
        if not self._closing.is_set():
            self.status_var.set(message)

    def safe_after(self, delay, callback, *args):
        if self._closing.is_set():
            return

        try:
            self.root.after(delay, callback, *args)
        except tk.TclError:
            pass

    def start_hotkey_listener(self):
        self._hotkey_thread = threading.Thread(
            target=self._hotkey_loop,
            daemon=True
        )
        self._hotkey_thread.start()

    def _hotkey_loop(self):
        key_states = {action: False for action in self.hotkey_map}
        handlers = {
            "start":   lambda: self.start_or_resume(),
            "pause":   lambda: self.pause_clicking() if self.engine.state == "running" else None,
            "capture": lambda: self.capture_position(),
            "stop":    lambda: self.stop_clicking() if self.engine.state in ("running", "paused") else None,
        }

        while not self._closing.is_set():
            try:
                for action, info in self.hotkey_map.items():
                    pressed = is_key_pressed(info["vk"])
                    if pressed and not key_states[action]:
                        key_states[action] = True
                        fn = handlers.get(action)
                        if fn:
                            self.safe_after(0, fn)
                    elif not pressed:
                        key_states[action] = False
            except Exception:
                pass

            time.sleep(0.05)

    def _on_floating_hidden(self):
        self.show_float_var.set(False)

    def _toggle_floating(self):
        if self.show_float_var.get():
            self.floating.show()
        else:
            self.floating.hide()

    def on_close(self):
        if self._closing.is_set():
            return

        self._closing.set()
        self.engine.stop(wait=True)
        self.floating.destroy()

        try:
            self.root.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClickerGUI(root)
    root.mainloop()