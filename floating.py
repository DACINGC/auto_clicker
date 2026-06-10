import tkinter as tk


BALL_SIZE = 80
PANEL_W = 270
PANEL_H = 330

# Dark theme colors
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

        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", "#F0F0F0")

        self._build_ball()
        self._build_panel()
        self._show_ball()
        self._position()

        self.win.after(200, self._poll)

    # ── UI build ──────────────────────────────────────────────

    def _build_ball(self):
        self._ball_frame = tk.Frame(self.win, bg="#F0F0F0")
        self._ball_cv = tk.Canvas(self._ball_frame, width=BALL_SIZE, height=BALL_SIZE,
                                   bg="#F0F0F0", highlightthickness=0)
        self._ball_cv.pack()

        # Outer glow ring
        self._ball_cv.create_oval(1, 1, BALL_SIZE - 1, BALL_SIZE - 1,
                                   fill="", outline="#D0D0D0", width=4)

        # Main circle
        self._ball = self._ball_cv.create_oval(4, 4, BALL_SIZE - 4, BALL_SIZE - 4,
                                                fill="#9E9E9E", outline="#666666", width=1)

        # Inner highlight (top-left glossy reflection)
        self._ball_cv.create_oval(10, 7, BALL_SIZE - 22, 24,
                                   fill="", outline="#DDDDDD", width=1.5)

        # Status text centered in the ball
        self._ball_text = self._ball_cv.create_text(
            BALL_SIZE // 2, BALL_SIZE // 2,
            text="停止", fill="white",
            font=("Microsoft YaHei", 14, "bold")
        )

        self._ball_cv.tag_bind(self._ball, "<Button-1>", self._toggle)
        self._ball_cv.tag_bind(self._ball_text, "<Button-1>", self._toggle)
        self._ball_cv.bind("<ButtonPress-1>", self._drag_start)
        self._ball_cv.bind("<B1-Motion>", self._drag_move)

    def _build_panel(self):
        self._panel_frame = tk.Frame(self.win, bg=BG_DARK)

        # ── Title bar (fully draggable) ──
        title_frm = tk.Frame(self._panel_frame, bg=BG_TITLE, cursor="fleur")
        title_frm.pack(fill="x")
        title_frm.bind("<ButtonPress-1>", self._drag_start)
        title_frm.bind("<B1-Motion>", self._drag_move)

        tk.Label(title_frm, text="连点器", bg=BG_TITLE, fg=FG_TEXT,
                 font=("Microsoft YaHei", 10), cursor="fleur").pack(side="left", padx=10)
        for child in title_frm.winfo_children():
            child.bind("<ButtonPress-1>", self._drag_start)
            child.bind("<B1-Motion>", self._drag_move)

        hide_btn = tk.Label(title_frm, text="✕", bg=BG_TITLE, fg=FG_MUTED,
                             font=("Arial", 12), cursor="hand2")
        hide_btn.pack(side="right", padx=8)
        # Override drag on close button so it only hides
        hide_btn.unbind("<ButtonPress-1>")
        hide_btn.unbind("<B1-Motion>")
        hide_btn.bind("<Button-1>", lambda _: self.hide())

        # ── Status ──
        st_frm = tk.Frame(self._panel_frame, bg=BG_DARK)
        st_frm.pack(fill="x", padx=10, pady=(10, 4))

        dot_row = tk.Frame(st_frm, bg=BG_DARK)
        dot_row.pack(fill="x")
        self._status_cv = tk.Canvas(dot_row, width=14, height=14, bg=BG_DARK,
                                     highlightthickness=0)
        self._status_cv.pack(side="left")
        self._status_dot = self._status_cv.create_oval(1, 1, 13, 13, fill="#888", outline="")
        self._status_lbl = tk.Label(dot_row, text="未运行", bg=BG_DARK, fg="#AAA",
                                     font=("Microsoft YaHei", 9))
        self._status_lbl.pack(side="left", padx=(6, 0))

        self._click_lbl = tk.Label(st_frm, text="已点击: 0 次", bg=BG_DARK, fg=FG_MUTED,
                                    font=("Microsoft YaHei", 8))
        self._click_lbl.pack(fill="x", pady=(3, 0))
        self._mode_lbl = tk.Label(st_frm, text="模式: 跟随鼠标", bg=BG_DARK, fg=FG_MUTED,
                                   font=("Microsoft YaHei", 8))
        self._mode_lbl.pack(fill="x")
        self._hk_lbl = tk.Label(st_frm, text="", bg=BG_DARK, fg=FG_MUTED,
                                 font=("Microsoft YaHei", 7))
        self._hk_lbl.pack(fill="x")

        tk.Frame(self._panel_frame, height=1, bg=DIVIDER).pack(fill="x", padx=12, pady=6)

        # ── Controls ──
        ctrl_frm = tk.Frame(self._panel_frame, bg=BG_DARK)
        ctrl_frm.pack(fill="x", padx=10, pady=4)

        self._start_btn = self._btn(ctrl_frm, "▶  开始", "#4CAF50", self._on_start)
        self._start_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self._pause_btn = self._btn(ctrl_frm, "⏸  暂停", "#FF9800", self._on_pause)
        self._pause_btn.pack(side="left", fill="x", expand=True, padx=2)
        self._stop_btn = self._btn(ctrl_frm, "■  停止", "#F44336", self._on_stop)
        self._stop_btn.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # ── Collapse ──
        tk.Frame(self._panel_frame, height=4, bg=BG_DARK).pack()
        coll = tk.Label(self._panel_frame, text="▲  收起", bg=BG_DARK, fg="#666",
                         font=("Microsoft YaHei", 8), cursor="hand2")
        coll.pack(pady=(0, 6))
        coll.bind("<Button-1>", lambda _: self._toggle())

    def _btn(self, parent, text, color, cmd):
        btn = tk.Label(parent, text=text, bg=color, fg="white",
                        font=("Microsoft YaHei", 8, "bold"), padx=2, pady=5, cursor="hand2")
        btn.bind("<Button-1>", lambda _: cmd())
        return btn

    # ── Show / hide / toggle ──

    def _show_ball(self):
        self._panel_frame.pack_forget()
        self._ball_frame.pack()
        self.win.geometry(f"{BALL_SIZE}x{BALL_SIZE}")
        self._position()

    def _show_panel(self):
        self._ball_frame.pack_forget()
        self._panel_frame.pack(fill="both", expand=True)
        self.win.geometry(f"{PANEL_W}x{PANEL_H}")
        self._position()

    def _toggle(self, _=None):
        self.expanded = not self.expanded
        if self.expanded:
            self._show_panel()
        else:
            self._show_ball()

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

    # ── Positioning ──

    def _position(self):
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        w = PANEL_W if self.expanded else BALL_SIZE
        h = PANEL_H if self.expanded else BALL_SIZE
        off = 0 if self.expanded else -(BALL_SIZE - 24)
        self.win.geometry(f"+{sw - w + off}+{(sh - h) // 2}")

    def _drag_start(self, event):
        self._drag_data["x"] = event.x_root - self.win.winfo_x()
        self._drag_data["y"] = event.y_root - self.win.winfo_y()

    def _drag_move(self, event):
        ny = event.y_root - self._drag_data["y"]
        sw = self.win.winfo_screenwidth()
        w = PANEL_W if self.expanded else BALL_SIZE
        nx = sw - w if self.expanded else min(event.x_root - self._drag_data["x"], sw - 24)
        self.win.geometry(f"+{nx}+{ny}")

    # ── State polling ──

    def _poll(self):
        if not self._polling:
            return
        state = self.engine.state
        color = COLORS.get(state, "#9E9E9E")

        if hasattr(self, "_ball"):
            self._ball_cv.itemconfig(self._ball, fill=color)
            self._ball_cv.itemconfig(self._ball_text, text=STATUS_BALL_TEXT.get(state, "停止"))
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
        else:  # paused
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

    # ── Control actions ──

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
