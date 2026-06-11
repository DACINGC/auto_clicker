import tkinter as tk

BALL_SIZE = 60
DOCK_SIZE = 40
DOCK_THRESHOLD = 30
PANEL_W = 270
PANEL_H = 330

BG_DARK = "#2D2D2D"
BG_TITLE = "#1E1E1E"
FG_MUTED = "#888"
FG_TEXT = "#CCC"
DIVIDER = "#444"

COLORS = {"idle": "#9E9E9E", "running": "#4CAF50", "paused": "#FF9800"}
STATUS_LABELS = {"idle": "未运行", "running": "运行中", "paused": "已暂停"}
STATUS_BALL_TEXT = {"idle": "停止", "running": "运行", "paused": "暂停"}


class FloatingWidget:
    def __init__(self, engine, root, parent_gui=None):
        self.engine = engine
        self.root = root
        self.parent_gui = parent_gui
        self.expanded = False
        self._visible = True
        self._polling = True
        self._drag_data = {}
        self._docked = False
        self._dock_edge = None
        self._dock_offset = 0
        self._animating = False

        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", "#F0F0F0")

        self._build_ball()
        self._build_dock()
        self._build_panel()
        self._show_ball()
        self._position_default()

        self.win.after(200, self._poll)

    # ── UI build ──────────────────────────────────────────────

    def _build_ball(self):
        self._ball_frame = tk.Frame(self.win, bg="#F0F0F0")
        self._ball_cv = tk.Canvas(
            self._ball_frame,
            width=BALL_SIZE,
            height=BALL_SIZE,
            bg="#F0F0F0",
            highlightthickness=0,
        )
        self._ball_cv.pack()

        # Shadow
        self._ball_cv.create_oval(
            4, 6, BALL_SIZE - 2, BALL_SIZE,
            fill="#AAAAAA", outline="#F0F0F0", width=2,
        )

        # Outer ring
        self._ball_cv.create_oval(
            2, 2, BALL_SIZE - 2, BALL_SIZE - 2,
            fill="", outline="#C0C0C0", width=3,
        )

        # Main circle
        self._ball = self._ball_cv.create_oval(
            5, 5, BALL_SIZE - 5, BALL_SIZE - 5,
            fill="#9E9E9E", outline="#707070", width=1,
        )

        # Glossy highlight
        self._ball_cv.create_oval(
            12, 8, BALL_SIZE - 16, 26,
            fill="", outline="#DDDDDD", width=1.5,
        )

        self._ball_text = self._ball_cv.create_text(
            BALL_SIZE // 2, BALL_SIZE // 2,
            text="停止", fill="white",
            font=("Microsoft YaHei", 12, "bold"),
        )

        self._ball_cv.bind("<ButtonPress-1>", self._drag_start)
        self._ball_cv.bind("<B1-Motion>", self._drag_move)
        self._ball_cv.bind("<ButtonRelease-1>", self._drag_end)
        self._ball_cv.bind("<Button-3>", self._on_right_click)

    def _build_dock(self):
        self._dock_frame = tk.Frame(self.win, bg="#F0F0F0")
        self._dock_cv = tk.Canvas(
            self._dock_frame,
            width=DOCK_SIZE,
            height=DOCK_SIZE,
            bg="#F0F0F0",
            highlightthickness=0,
        )
        self._dock_cv.pack()

        self._dock_triangle = self._dock_cv.create_polygon(
            0, DOCK_SIZE // 2,
            DOCK_SIZE - 8, 5,
            DOCK_SIZE - 8, DOCK_SIZE - 5,
            fill="#9E9E9E", outline="#666", width=1,
        )

        self._dock_cv.bind("<Button-1>", self._on_dock_click)
        self._dock_cv.bind("<Button-3>", self._on_right_click)

    def _build_panel(self):
        self._panel_frame = tk.Frame(self.win, bg=BG_DARK)

        # Title bar
        title_frm = tk.Frame(self._panel_frame, bg=BG_TITLE, cursor="fleur")
        title_frm.pack(fill="x")
        title_frm.bind("<ButtonPress-1>", self._drag_start)
        title_frm.bind("<B1-Motion>", self._drag_move)

        tk.Label(
            title_frm, text="连点器", bg=BG_TITLE, fg=FG_TEXT,
            font=("Microsoft YaHei", 10), cursor="fleur",
        ).pack(side="left", padx=10)
        for child in title_frm.winfo_children():
            child.bind("<ButtonPress-1>", self._drag_start)
            child.bind("<B1-Motion>", self._drag_move)

        hide_btn = tk.Label(
            title_frm, text="✕ 关闭弹窗/显示悬浮球", bg=BG_TITLE, fg=FG_MUTED,
            font=("Microsoft YaHei", 9), cursor="hand2",
        )
        hide_btn.pack(side="right", padx=8)
        hide_btn.unbind("<ButtonPress-1>")
        hide_btn.unbind("<B1-Motion>")
        hide_btn.bind("<Button-1>", lambda _: self._toggle())

        # Status
        st_frm = tk.Frame(self._panel_frame, bg=BG_DARK)
        st_frm.pack(fill="x", padx=10, pady=(10, 4))

        dot_row = tk.Frame(st_frm, bg=BG_DARK)
        dot_row.pack(fill="x")
        self._status_cv = tk.Canvas(
            dot_row, width=14, height=14, bg=BG_DARK, highlightthickness=0,
        )
        self._status_cv.pack(side="left")
        self._status_dot = self._status_cv.create_oval(
            1, 1, 13, 13, fill="#888", outline="",
        )
        self._status_lbl = tk.Label(
            dot_row, text="未运行", bg=BG_DARK, fg="#AAA",
            font=("Microsoft YaHei", 9),
        )
        self._status_lbl.pack(side="left", padx=(6, 0))

        self._click_lbl = tk.Label(
            st_frm, text="已点击: 0 次", bg=BG_DARK, fg=FG_MUTED,
            font=("Microsoft YaHei", 8),
        )
        self._click_lbl.pack(fill="x", pady=(3, 0))
        self._mode_lbl = tk.Label(
            st_frm, text="模式: 跟随鼠标", bg=BG_DARK, fg=FG_MUTED,
            font=("Microsoft YaHei", 8),
        )
        self._mode_lbl.pack(fill="x")
        self._hk_lbl = tk.Label(
            st_frm, text="", bg=BG_DARK, fg=FG_MUTED,
            font=("Microsoft YaHei", 7),
        )
        self._hk_lbl.pack(fill="x")

        tk.Frame(self._panel_frame, height=1, bg=DIVIDER).pack(fill="x", padx=12, pady=6)

        # Controls
        ctrl_frm = tk.Frame(self._panel_frame, bg=BG_DARK)
        ctrl_frm.pack(fill="x", padx=10, pady=4)

        self._start_btn = self._btn(ctrl_frm, "▶  开始", "#4CAF50", self._on_start)
        self._start_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self._pause_btn = self._btn(ctrl_frm, "⏸  暂停", "#FF9800", self._on_pause)
        self._pause_btn.pack(side="left", fill="x", expand=True, padx=2)
        self._stop_btn = self._btn(ctrl_frm, "■  停止", "#F44336", self._on_stop)
        self._stop_btn.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # Collapse
        tk.Frame(self._panel_frame, height=4, bg=BG_DARK).pack()
        coll = tk.Label(
            self._panel_frame, text="▲  收起", bg=BG_DARK, fg="#666",
            font=("Microsoft YaHei", 8), cursor="hand2",
        )
        coll.pack(pady=(0, 6))
        coll.bind("<Button-1>", lambda _: self._toggle())

    def _btn(self, parent, text, color, cmd):
        btn = tk.Label(
            parent, text=text, bg=color, fg="white",
            font=("Microsoft YaHei", 8, "bold"), padx=2, pady=5, cursor="hand2",
        )
        btn.bind("<Button-1>", lambda _: cmd())
        return btn

    # ── Show / hide / toggle ──────────────────────────────────

    def _show_ball(self):
        x, y = self._ball_pos if hasattr(self, '_ball_pos') else self._get_current_pos()
        self._panel_frame.pack_forget()
        self._ball_frame.pack()
        self.win.geometry(f"{BALL_SIZE}x{BALL_SIZE}+{x}+{y}")

    def _show_panel(self):
        x, y = self._get_current_pos()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x = max(0, min(x, sw - PANEL_W))
        y = max(0, min(y, sh - PANEL_H))
        self._ball_frame.pack_forget()
        self._panel_frame.pack(fill="both", expand=True)
        self.win.geometry(f"{PANEL_W}x{PANEL_H}+{x}+{y}")

    def _toggle(self, _=None):
        if not self.expanded:
            self._ball_pos = self._get_current_pos()
        self.expanded = not self.expanded
        if self.expanded:
            self._show_panel()
        else:
            self._show_ball()

    def _on_right_click(self, event):
        if self._docked:
            self._undock()
            return

        menu = tk.Toplevel(self.win)
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        menu.configure(bg="#333")

        bx, by = self._get_current_pos()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        menu_w, menu_h = 120, 70
        mx = bx + BALL_SIZE + 5
        my = by
        mx = max(0, min(mx, sw - menu_w))
        my = max(0, min(my, sh - menu_h))
        menu.geometry(f"+{mx}+{my}")

        def close_menu(_=None):
            menu.destroy()

        menu.bind("<FocusOut>", close_menu)

        def on_close_ball():
            menu.destroy()
            self.hide()

        def on_open_panel():
            menu.destroy()
            if not self.expanded:
                self._toggle()

        lbl_close = tk.Label(
            menu, text="关闭悬浮球", bg="#333", fg="white",
            font=("Microsoft YaHei", 9), padx=20, pady=6, cursor="hand2",
        )
        lbl_close.pack(fill="x")
        lbl_close.bind("<Button-1>", lambda _: on_close_ball())
        lbl_close.bind("<Enter>", lambda _: lbl_close.config(bg="#555"))
        lbl_close.bind("<Leave>", lambda _: lbl_close.config(bg="#333"))

        lbl_open = tk.Label(
            menu, text="打开悬浮弹窗", bg="#333", fg="white",
            font=("Microsoft YaHei", 9), padx=20, pady=6, cursor="hand2",
        )
        lbl_open.pack(fill="x")
        lbl_open.bind("<Button-1>", lambda _: on_open_panel())
        lbl_open.bind("<Enter>", lambda _: lbl_open.config(bg="#555"))
        lbl_open.bind("<Leave>", lambda _: lbl_open.config(bg="#333"))

        menu.focus_set()

    def _on_dock_click(self, event):
        self._undock()

    def show(self):
        self._visible = True
        self.win.deiconify()

    def hide(self):
        self._visible = False
        self.win.withdraw()
        if self.parent_gui and hasattr(self.parent_gui, "_on_floating_hidden"):
            self.parent_gui._on_floating_hidden()

    def destroy(self):
        self._polling = False
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    # ── Positioning ───────────────────────────────────────────

    def _position_default(self):
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x = sw - BALL_SIZE - 10
        y = (sh - BALL_SIZE) // 2
        self.win.geometry(f"+{x}+{y}")

    def _get_current_pos(self):
        geo = self.win.geometry()
        parts = geo.split("+")
        if len(parts) == 3:
            return int(parts[1]), int(parts[2])
        return 0, 0

    # ── Drag handling ─────────────────────────────────────────

    def _drag_start(self, event):
        if self._animating:
            return
        self._drag_data["x"] = event.x_root - self.win.winfo_x()
        self._drag_data["y"] = event.y_root - self.win.winfo_y()
        self._drag_data["dragged"] = False

    def _drag_move(self, event):
        if self._animating:
            return
        self._drag_data["dragged"] = True
        nx = event.x_root - self._drag_data["x"]
        ny = event.y_root - self._drag_data["y"]
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()

        if self.expanded:
            nx = max(0, min(nx, sw - PANEL_W))
            ny = max(0, min(ny, sh - PANEL_H))
            self.win.geometry(f"+{nx}+{ny}")
        else:
            if not self._docked:
                nx = max(0, min(nx, sw - BALL_SIZE))
                ny = max(0, min(ny, sh - BALL_SIZE))
                self.win.geometry(f"+{nx}+{ny}")

    def _drag_end(self, event):
        if not self._drag_data.get("dragged"):
            if self._docked:
                self._undock()
            return

        if self.expanded or self._docked:
            return

        nx = event.x_root - self._drag_data["x"]
        ny = event.y_root - self._drag_data["y"]
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()

        if nx <= DOCK_THRESHOLD:
            self._dock_to_edge("left", nx, ny)
        elif nx + BALL_SIZE >= sw - DOCK_THRESHOLD:
            self._dock_to_edge("right", nx, ny)
        elif ny <= DOCK_THRESHOLD:
            self._dock_to_edge("top", nx, ny)
        elif ny + BALL_SIZE >= sh - DOCK_THRESHOLD:
            self._dock_to_edge("bottom", nx, ny)

    # ── Edge snapping ─────────────────────────────────────────

    def _dock_to_edge(self, edge, x, y):
        if self._docked or self._animating:
            return
        self._docked = True
        self._dock_edge = edge
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()

        self._ball_frame.pack_forget()
        self._dock_frame.pack()

        if edge == "left":
            target_x = -(BALL_SIZE - DOCK_SIZE)
            target_y = max(0, min(y, sh - DOCK_SIZE))
            self._dock_cv.coords(self._dock_triangle,
                DOCK_SIZE - 3, DOCK_SIZE // 2,
                0, 3,
                0, DOCK_SIZE - 3)
        elif edge == "right":
            target_x = sw - DOCK_SIZE
            target_y = max(0, min(y, sh - DOCK_SIZE))
            self._dock_cv.coords(self._dock_triangle,
                3, DOCK_SIZE // 2,
                DOCK_SIZE, 3,
                DOCK_SIZE, DOCK_SIZE - 3)
        elif edge == "top":
            target_x = max(0, min(x, sw - DOCK_SIZE))
            target_y = -(BALL_SIZE - DOCK_SIZE)
            self._dock_cv.coords(self._dock_triangle,
                DOCK_SIZE // 2, DOCK_SIZE - 3,
                3, 0,
                DOCK_SIZE - 3, 0)
        else:
            target_x = max(0, min(x, sw - DOCK_SIZE))
            target_y = sh - DOCK_SIZE
            self._dock_cv.coords(self._dock_triangle,
                DOCK_SIZE // 2, 3,
                3, DOCK_SIZE,
                DOCK_SIZE - 3, DOCK_SIZE)

        self._dock_offset = target_y if edge in ("left", "right") else target_x
        self.win.geometry(f"{DOCK_SIZE}x{DOCK_SIZE}")
        self._animate_to(target_x, target_y)

    def _undock(self):
        if not self._docked or self._animating:
            return
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()

        edge = self._dock_edge
        offset = self._dock_offset

        if edge == "left":
            target_x = 10
            target_y = offset
        elif edge == "right":
            target_x = sw - BALL_SIZE - 10
            target_y = offset
        elif edge == "top":
            target_x = offset
            target_y = 10
        else:
            target_x = offset
            target_y = sh - BALL_SIZE - 10

        self._docked = False
        self._dock_edge = None
        self._dock_frame.pack_forget()
        self._ball_frame.pack()
        self.win.geometry(f"{BALL_SIZE}x{BALL_SIZE}")
        self._animate_to(target_x, target_y)

    # ── Animation ─────────────────────────────────────────────

    def _animate_to(self, target_x, target_y):
        if self._animating:
            return
        self._animating = True
        sx, sy = self._get_current_pos()
        steps = 12

        def step(i):
            if i > steps:
                self.win.geometry(f"+{target_x}+{target_y}")
                self._animating = False
                return
            t = i / steps
            cx = int(sx + (target_x - sx) * t)
            cy = int(sy + (target_y - sy) * t)
            self.win.geometry(f"+{cx}+{cy}")
            self.win.after(15, lambda: step(i + 1))

        step(0)

    # ── State polling ─────────────────────────────────────────

    def _poll(self):
        if not self._polling:
            return
        state = self.engine.state
        color = COLORS.get(state, "#9E9E9E")

        if hasattr(self, "_ball"):
            self._ball_cv.itemconfig(self._ball, fill=color)
            self._ball_cv.itemconfig(self._ball_text, text=STATUS_BALL_TEXT.get(state, "停止"))
        if hasattr(self, "_dock_triangle"):
            self._dock_cv.itemconfig(self._dock_triangle, fill=color)
        if hasattr(self, "_status_dot"):
            self._status_cv.itemconfig(self._status_dot, fill=color)
        if hasattr(self, "_status_lbl"):
            self._status_lbl.config(text=STATUS_LABELS.get(state, "未知"))

        self._update_btns(state)
        self._update_info()

        try:
            self.win.after(200, self._poll)
        except tk.TclError:
            self._polling = False

    def _update_btns(self, state):
        if state == "idle":
            self._start_btn.config(bg="#4CAF50")
            self._pause_btn.config(bg="#555")
            self._stop_btn.config(bg="#555")
        elif state == "running":
            self._start_btn.config(bg="#555")
            self._pause_btn.config(bg="#FF9800")
            self._stop_btn.config(bg="#F44336")
        else:
            self._start_btn.config(bg="#4CAF50")
            self._pause_btn.config(bg="#555")
            self._stop_btn.config(bg="#F44336")

    def _update_info(self):
        if self.parent_gui:
            status = self.parent_gui.status_var.get()
            self._click_lbl.config(text=status)
            mode_text = self.parent_gui.mode_info_var.get()
            self._mode_lbl.config(text=mode_text)
            hk = self.parent_gui.hotkey_map
            self._hk_lbl.config(
                text=f"开始 {hk['start']['name']} · 暂停 {hk['pause']['name']} · 停止 {hk['stop']['name']}"
            )
            s = self.engine.state
            self._start_btn.config(
                text=f"▶  {'开始' if s == 'idle' else '继续'} {hk['start']['name']}"
            )
            self._pause_btn.config(text=f"⏸  暂停 {hk['pause']['name']}")
            self._stop_btn.config(text=f"■  停止 {hk['stop']['name']}")

    # ── Control actions ───────────────────────────────────────

    def _on_start(self):
        state = self.engine.state
        if state == "paused":
            self.engine.resume()
        elif state == "idle":
            if self.parent_gui and hasattr(self.parent_gui, "validate_settings"):
                s = self.parent_gui.validate_settings()
                if s is not None:
                    self.engine.start(s)

    def _on_pause(self):
        if self.engine.state == "running":
            self.engine.pause()

    def _on_stop(self):
        if self.engine.state in ("running", "paused"):
            self.engine.stop(wait=True)
