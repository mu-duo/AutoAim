import tkinter as tk
from tkinter import ttk
from collections import deque
import queue
from pynput import mouse


class Mouse:
    def __init__(self):
        self.x = 0
        self.y = 0

        # trail: deque of (type, cx, cy, extra...)
        # type: "move" | "click" | "scroll"
        self.event_queue = queue.Queue()
        self.listener = mouse.Listener(
            on_move=lambda x, y: self.event_queue.put(("move", x, y)),
            on_click=lambda x, y, b, p: self.event_queue.put(("click", x, y, str(b).split(".")[-1], p)),
            on_scroll=lambda x, y, dx, dy: self.event_queue.put(("scroll", x, y, dx, dy)),
        )
        self.listener.start()

    def getPosition(self):
        return (self.x, self.y)

    def move(self, x, y):
        self.x = x
        self.y = y
        mouse.Controller().position = (x, y)


class UIConfig:
    def __init__(self):
        self.bg_color = "#1a1a2e"
        self.fg_color = "#e0e0e0"
        self.trail_color = "#4fc3f7"
        self.click_color_down = "#ff5252"
        self.click_color_up = "#ffab40"
        self.scroll_color = "#69f0ae"
        self.font = ("Consolas", 10)


class MouseUI:
    def __init__(self, ui: tk.Tk):
        self.ui = ui
        self.mouse = Mouse()
        self.config = UIConfig()

        self.trail_en = False
        self.trail = deque(maxlen=1024)
        self.mouse_on_canvas = False

        self.config_ui()
        self.setup_ui()

        self.cursor = self.canvas.create_oval(0, 0, 0, 0, fill="", outline="#ffffff", width=2, tags="cursor")

        self.ui.protocol("WM_DELETE_WINDOW", self.on_close)
        self.ui.after(3, self.process_events)

    def on_canvas_enter(self, event):
        self.mouse_on_canvas = True
        self.lbl_on_canvas.config(text="On Canvas: Yes")

    def on_canvas_leave(self, event):
        self.mouse_on_canvas = False
        self.lbl_on_canvas.config(text="On Canvas: No")

    def config_ui(self):
        self.ui.title("Mouse Tracker")
        self.ui.geometry("900x600")
        self.ui.minsize(400, 300)
        self.ui.configure(bg=self.config.bg_color)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=self.config.bg_color)
        style.configure("TLabel", background=self.config.bg_color, foreground=self.config.fg_color, font=self.config.font)
        style.configure("TCheckbutton", background=self.config.bg_color, foreground=self.config.fg_color, font=self.config.font)

    def setup_ui(self):
        main = ttk.Frame(self.ui)
        main.pack(fill=tk.BOTH, expand=True)

        # info bar
        bar = ttk.Frame(main)
        bar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 4))

        self.lbl_screen = ttk.Label(bar, text="Screen: --")
        self.lbl_screen.pack(side=tk.LEFT, padx=(0, 16))

        self.lbl_on_canvas = ttk.Label(bar, text="On Canvas: --")
        self.lbl_on_canvas.pack(side=tk.LEFT, padx=(0, 16))

        self.lbl_event = ttk.Label(bar, text="Event: --")
        self.lbl_event.pack(side=tk.LEFT, padx=(0, 16))

        self.lbl_count = ttk.Label(bar, text="Trail: 0")
        self.lbl_count.pack(side=tk.RIGHT)

        # canvas
        self.canvas = tk.Canvas(main, bg=self.config.bg_color, highlightthickness=1, highlightbackground="#2a2a5a")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.canvas.bind("<Enter>", self.on_canvas_enter)
        self.canvas.bind("<Leave>", self.on_canvas_leave)

        # controls
        ctrl = ttk.Frame(main)
        ctrl.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(ctrl, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=(0, 5))

        # clipping info
        self.clip_var = tk.StringVar(value="")
        ttk.Label(ctrl, textvariable=self.clip_var, foreground="#ff7043").pack(side=tk.RIGHT, padx=(10, 0))

    def clear(self):
        self.trail.clear()
        self.trail_en = False
        self.canvas.delete("all")
        self.lbl_count.config(text="Trail: 0")

    def _to_canvas(self, sx, sy):
        cx = sx - self.canvas.winfo_rootx()
        cy = sy - self.canvas.winfo_rooty()
        return cx, cy

    def process_events(self):
        try:
            self.ui.after(3, self.process_events)
        except Exception:
            return

        dirty = False

        while not self.mouse.event_queue.empty():
            try:
                ev = self.mouse.event_queue.get_nowait()
            except queue.Empty:
                break

            etype = ev[0]

            if etype == "move":
                _, sx, sy = ev
                cx, cy = self._to_canvas(sx, sy)

                if self.trail_en:
                    if self.mouse_on_canvas:
                        self.trail.append(("move", cx, cy))
                    else:
                        self.trail.append(("outCanvas", sx, sy))

                self.lbl_event.config(text="Event: move")
                self.lbl_screen.config(text=f"Screen: ({sx}, {sy})")
                dirty = True

            elif etype == "click" and self.mouse_on_canvas:
                self.trail_en = True
                _, sx, sy, btn, pressed = ev

                if self.mouse_on_canvas:
                    state = "down" if pressed else "up"
                    self.lbl_event.config(text=f"Event: {btn} {state}")
                    self.lbl_screen.config(text=f"Screen: ({sx}, {sy})")
                else:
                    self.lbl_screen.config(text=f"Screen: ({sx}, {sy})")

                dirty = True

            elif etype == "scroll":
                _, sx, sy, dx, dy = ev

                if self.mouse_on_canvas:
                    self.lbl_event.config(text=f"Event: scroll ({dx:+d},{dy:+d})")
                    self.lbl_screen.config(text=f"Screen: ({sx}, {sy})")
                else:
                    self.lbl_screen.config(text=f"Screen: ({sx}, {sy})")

                dirty = True

        self.lbl_count.config(text=f"Trail: {len(self.trail)}")
        if dirty and self.trail_en:
            self.canvas.delete("trail", "marker", "cursor")
            self.draw()

    def draw(self):
        self.canvas.delete("all")
        trail = list(self.trail)
        if not trail:
            return

        prev_x, prev_y = trail[0][1], trail[0][2]
        # draw cursor and markers

        for ev in trail:
            if ev[0] == "move":
                _, x, y = ev
                self.canvas.create_line(prev_x, prev_y, x, y, fill=self.config.trail_color, width=1, tags="trail")
                prev_x, prev_y = x, y

            elif ev[0] == "click":
                # prev_x, prev_y = self.mouse.getPosition()

                _, x, y, btn, pressed = ev
                if pressed:
                    color = self.config.click_color_down
                    r = 5
                    self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="", tags="marker")
                    prev_x, prev_y = x, y

            elif ev[0] == "scroll":
                _, x, y, dx, dy = ev
                r = 3
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=self.config.scroll_color, outline="", tags="marker")
                prev_x, prev_y = x, y

            elif ev[0] == "outCanvas":
                _, sx, sy = ev
                prev_x, prev_y = sx, sy

    def on_close(self):
        self.trail_en = False
        self.mouse.listener.stop()
        self.ui.destroy()


def main():
    ui = tk.Tk()
    MouseUI(ui)
    ui.mainloop()


if __name__ == "__main__":
    main()
