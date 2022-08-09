import ss_backend as ss
from ss_backend.style import colors, fonts
import tkinter as tk

app = ss.AppLayout()
app.make_layout()

# The Backend Components
ss_canvas = ss.Canvas((ss.DEFAULTS["width"], ss.DEFAULTS["height"]))
ss_margin = ss.Margin(
    ss_canvas,
    tlbr=tuple(
        ss.DEFAULTS[key]
        for key in ss.DEFAULTS
        if key in ("top", "left", "bottom", "right")
    ),
    gutter=ss.DEFAULTS["gutter"],
)
ss_grid = ss.Grid(ss_canvas, ss_margin)

# The Resolve API
resolve_api = ss.ResolveFusionAPI()
resolve_api.add_canvas(*ss_canvas.resolution)

# The GUI
gui = ss.ScreenSplitterUI(
    master=app.creator_frame, ss_grid=ss_grid, max_width=800, max_height=600
)
gui.draw_canvas()
gui.draw_grid()
gui.grid(row=1)


# The Boss
controller = ss.Controller(ss_grid, resolve_api, gui)

# The FrontEnd
handler = ss.EventHandler(controller, gui)
interface = ss.Interface(handler)

interface.make_left_frame_entries(ss.DEFAULTS, app.button_frame_left)
interface.bind_left_frame_entries()
interface.grid_entries(app.button_frame_left)

app.root.mainloop()
