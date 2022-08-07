from __future__ import annotations
import tkinter as tk
import ss_backend as ss
from ss_backend.resolve_fusion_api import ResolveFusionAPI
from ss_backend.protocols import ResolveAPI
from ss_backend.export import render_fusion_output
from ss_backend.style import fonts, colors
import pyperclip


# FUNCTIONS ======================================================
def is_within(coords: tuple[float, float], area: dict[tuple[float, float]]) -> bool:
    x, y = coords[0], coords[1]
    if x <= area["top_left"][0]:
        return False
    if x >= area["top_right"][0]:
        return False
    if y >= area["top_left"][1]:
        return False
    if y <= area["bottom_left"][1]:
        return False
    return True


def find_grid_block_within(
    coords: tuple[float, float], grid_blocks: list[GridBlock]
) -> GridBlock:
    return next(
        (block for block in grid_blocks if is_within(coords, block.grid_cell.corners)),
        None,
    )


def get_event_coords_normalized(event) -> tuple[float, float]:
    self: tk.Widget = event.widget
    coords = (event.x / self.winfo_width(), 1 - event.y / self.winfo_height())
    return coords


def btn_on_hover(event: tk.Event, foreground):
    self: tk.Widget = event.widget
    self.configure(foreground=foreground)


def set_hover_style(button: tk.Label):
    button.bind("<Enter>", lambda e: btn_on_hover(event=e, foreground=colors.TEXT))
    button.bind(
        "<Leave>", lambda e: btn_on_hover(event=e, foreground=colors.TEXT_DARKER)
    )
    button.bind("<Button-1>", lambda e: btn_on_hover(event=e, foreground="white"))
    button.bind(
        "<ButtonRelease-1>",
        lambda e: btn_on_hover(event=e, foreground=colors.TEXT_DARKER),
    )


# =========================================================================== #
#                               CLASSES                                       #
# =========================================================================== #


# ========================= BLOCKS
class ScreenBlock:
    screen_blocks: list[ScreenBlock] = None
    settings: dict[str, int | str] = None

    def __init__(
        self, tk_canvas: ScreenSplitter, ss_screen: ss.Screen, **config
    ) -> None:
        self.canvas = tk_canvas
        self.screen = ss_screen

        self.compute()
        if ScreenBlock.screen_blocks is None:
            ScreenBlock.grid_blocks = []

        ScreenBlock.grid_blocks.append(self)

        if ScreenBlock.settings is None:
            ScreenBlock.settings = {}
            for key, value in config.items():
                ScreenBlock.settings[key] = value

        self.status_text: tk.StringVar = None  # for announcing

    def draw(self) -> None:
        self.rect = self.canvas.create_rectangle(
            self.x0, self.y0, self.x1, self.y1, **self.settings
        )

    def compute(self):
        self.canvas.update()
        canvas_height = self.canvas.winfo_height()
        canvas_width = self.canvas.winfo_width()
        screen = self.screen
        y = 1 - screen.y

        self.x0 = (screen.x - screen.width / 2) * canvas_width
        self.y0 = (y - screen.height / 2) * canvas_height
        self.x1 = self.x0 + screen.width * canvas_width
        self.y1 = self.y0 + screen.height * canvas_height

    @classmethod
    def draw_all(cls):
        for block in cls.screen_blocks:
            block.compute()

        for block in cls.screen_blocks:
            block.draw()


class GridBlock:
    grid_blocks: list[GridBlock] = None
    settings = {}

    def __init__(self, tk_canvas: tk.Canvas, grid_cell: ss.GridCell, **config):
        self.canvas = tk_canvas
        self.grid_cell = grid_cell

        if grid_cell.index == 1:
            # GridBlock.settings = {}
            for key, value in config.items():
                self.settings[key] = value

        self.compute()
        if GridBlock.grid_blocks is None:
            GridBlock.grid_blocks = []
        GridBlock.grid_blocks.append(self)

    def compute(self):
        self.canvas.update()
        canvas_height = self.canvas.winfo_height()
        canvas_width = self.canvas.winfo_width()
        cell = self.grid_cell
        y = 1 - cell.y

        self.x0 = (cell.x - cell.width / 2) * canvas_width
        self.y0 = (y - cell.height / 2) * canvas_height
        self.x1 = self.x0 + cell.width * canvas_width
        self.y1 = self.y0 + cell.height * canvas_height

    def draw(self):
        self.rect = self.canvas.create_rectangle(
            self.x0, self.y0, self.x1, self.y1, **self.settings
        )

    def undraw(self, *opt):
        self.canvas.delete(self.rect)
        GridBlock.grid_blocks.remove(self)

    def config(self, **opts):
        self.canvas.itemconfig(self.rect, **opts)
        for key, value in opts.items():
            self.settings[key] = value

    @staticmethod
    def blocks_from_grid(grid: ss.Grid) -> list[ss.GridCell]:
        return ss.GridCell.generate_all(grid)

    @classmethod
    def draw_all(cls):
        for block in cls.grid_blocks:
            block.compute()

        for block in cls.grid_blocks:
            block.draw()

    @classmethod
    def create_all(cls, canvas: tk.Canvas, grid: ss.Grid, **config):
        if cls.grid_blocks is None:
            cls.grid_blocks = []
        cls.grid_blocks.clear()

        # creates grid cells from provided grid
        grid_block_screens = cls.blocks_from_grid(grid)

        # initializes grid block from generated cells
        for cell in grid_block_screens:
            GridBlock(canvas, cell, **config)

    def bind(self, event: str, function) -> None:
        self.canvas.tag_bind(self.tag, sequence=event, func=function)


###################         SCREEN SPLITTER         ####################
class ScreenSplitter(tk.Canvas):
    # Fusion API
    api: ResolveAPI = None

    # Grid and Grid display
    ss_grid: ss.Grid = None
    grid_blocks: list[GridBlock] = None

    # Color Palette
    screen_color: str = None
    screen_color_pre_delete: str = None
    screen_color_hover: str = None

    # User Inputs
    vars: dict[str, tk.IntVar] = None
    entries: dict[str, tk.Entry] = None

    # CLICKING AND DRAGGING MECHANISM      ======================
    new_screen_coords: tuple[tuple[float, float], tuple[float, float]] = (
        (0.0, 0.0),
        (0.0, 0.0),
    )
    new_screen_indexes: tuple[int, int] = (0, 0)

    @classmethod
    def on_click(cls, event: tk.Event) -> None:
        self: tk.Canvas = event.widget

        item = self.find_closest(event.x, event.y)
        if self.itemcget(item, "fill") == cls.screen_color:
            print("clicked on screen")
            cls.new_screen_coords = None
            return

        coords = get_event_coords_normalized(event)
        cls.new_screen_coords = coords
        block = find_grid_block_within(coords, GridBlock.grid_blocks)

        if block is not None:
            index = block.grid_cell.index
            cls.new_screen_indexes = index
            return
        cls.new_screen_indexes = None

    @classmethod
    def on_release(cls, event: tk.Event) -> None:

        self: ScreenSplitter = event.widget

        if cls.new_screen_coords is None:
            return
        coords = get_event_coords_normalized(event)
        cls.new_screen_coords = (cls.new_screen_coords, coords)
        block = find_grid_block_within(coords, GridBlock.grid_blocks)

        if block is not None:
            index = block.grid_cell.index
            cls.new_screen_indexes = (cls.new_screen_indexes, index)
            self.create_screen()
            return
        cls.new_screen_indexes = None

    # SCREEN CREATION       =================================
    def create_screen(self) -> None:
        if ScreenSplitter.ss_grid is None:
            raise Exception("Please attach a grid first.")
        if ScreenSplitter.new_screen_indexes is None:
            return

        screen = ss.Screen.create_from_coords(
            ScreenSplitter.ss_grid, *ScreenSplitter.new_screen_indexes
        )

        self.draw_screen(screen)
        screen.merge, screen.mask, screen.media_in = self.api.add_screen(
            **screen.values
        )

    def draw_screen(self, screen: ss.Screen) -> None:
        self.clear_status_bar()
        new_screen_block = ScreenBlock(
            self,
            screen,
            fill=self.screen_color,
            outline=self.screen_color,
            tag="screen",
        )
        new_screen_block.draw()

        id = new_screen_block.rect
        screen.id = id

        self.tag_bind(id, "<Button-2>", self.pre_delete_screen)
        self.tag_bind(id, "<Button-2> <Leave>", lambda e: self.cancel_deletion(id=id))
        self.tag_bind(id, "<Button-2> <ButtonRelease-2>", self.delete_screen)

    # SCREEN DELETION       =================================
    user_wants_to_delete = True

    def pre_delete_screen(self, event: tk.Event) -> None:
        id = self.find_closest(event.x, event.y)[0]
        self.itemconfig(
            id, fill=self.screen_color_pre_delete, outline=self.screen_color_pre_delete
        )

    def cancel_deletion(self=None, event: tk.Event = None, id=None) -> None:
        self.user_wants_to_delete = False
        self.itemconfig(id, fill=self.screen_color, outline=self.screen_color)

    def delete_screen(self, event: tk.Event):
        if not self.user_wants_to_delete:
            self.user_wants_to_delete = True
            return "break"

        canvas: tk.Canvas = event.widget
        screen_rect_id = canvas.find_closest(event.x, event.y)[0]
        self.delete(screen_rect_id)

        screen_to_delete = [
            screen for screen in self.ss_grid.screens if screen.id == screen_rect_id
        ][0]

        merge, mask, media_in = (
            screen_to_delete.merge,
            screen_to_delete.mask,
            screen_to_delete.media_in,
        )

        merge.Delete()
        mask.Delete()
        media_in.Delete()

        self.api.merges.remove(merge)
        self.api.masks.remove(mask)
        self.api.media_ins.remove(media_in)
        self.api.set_input_media_out()

        self.ss_grid.screens.remove(screen_to_delete)
        self.user_wants_to_delete = True
        self.api.update_flow_position()

    # SCREEN BATCH DELETION =================================
    def delete_all_screens(self, event):
        if not self.undraw_screens():
            return
        self.ss_grid.screens.clear()
        for merge, mask, media_in in zip(
            self.api.merges, self.api.masks, self.api.media_ins
        ):
            merge.Delete()
            mask.Delete()
            media_in.Delete()
        self.api.masks.clear()
        self.api.merges.clear()
        self.api.media_ins.clear()
        self.api.media_out.SetInput("Input", self.api.canvas)

    def pre_delete_all_screens(self, event):
        if self.ss_grid.screens is None:
            return
        ids_to_delete = [screen.id for screen in self.ss_grid.screens]
        for id in ids_to_delete:
            self.itemconfig(
                id,
                fill=self.screen_color_pre_delete,
                outline=self.screen_color_pre_delete,
            )

    # SCREEN SELECTION (not implemented)
    selected_screen = None

    def select_screen(self, event: tk.Event):
        raise NotImplementedError()

    def mark_selected(self):
        raise NotImplementedError()

    def deselect_screen(self, event):
        raise NotImplementedError()

    # LINK OR UNLINK MARGIN CONTROL     ======================
    def link_margins(self, event: tk.Event):
        lbr = {k: self.entries[k][1] for k in ("left", "bottom", "right")}
        for mg in lbr.values():
            mg.configure(state="disabled")

        # rebind
        event.widget.unbind("<Button-1>")
        event.widget.bind("<Button-1>", self.unlink_margins)

        self.set_all_margins(self.vars["top"].get)

        # change labels
        self.entries["top"][0].configure(text="Margin")
        self.entries["left"][0].configure(foreground=colors.TEXT_DARKER)
        self.entries["bottom"][0].configure(foreground=colors.TEXT_DARKER)
        self.entries["right"][0].configure(foreground=colors.TEXT_DARKER)

        self.entries["top"][1].unbind("<Return>")
        self.entries["top"][1].unbind("<FocusOut>")
        self.entries["top"][1].unbind("<KP_Enter>")
        self.entries["top"][1].bind(
            "<Return>", lambda a: self.set_all_margins(self.vars["top"].get)
        )
        self.entries["top"][1].bind(
            "<FocusOut>", lambda a: self.set_all_margins(self.vars["top"].get)
        )
        self.entries["top"][1].bind(
            "<KP_Enter>", lambda a: self.set_all_margins(self.vars["top"].get)
        )
        # self.global_refresh()
        self.update_all_vars()

    def unlink_margins(self, event):
        lbr = {k: self.entries[k][1] for k in ("left", "bottom", "right")}
        for mg in lbr.values():
            mg.configure(state=tk.NORMAL)

        # rebind
        event.widget.unbind("<Button-1>")
        event.widget.bind("<Button-1>", self.link_margins)

        # change labels
        self.entries["top"][0].configure(text="Top")
        self.entries["left"][0].configure(foreground=colors.TEXT)
        self.entries["bottom"][0].configure(foreground=colors.TEXT)
        self.entries["right"][0].configure(foreground=colors.TEXT)

        self.entries["top"][1].unbind("<Return>")
        self.entries["top"][1].unbind("<FocusOut>")
        self.entries["top"][1].unbind("<KP_Enter>")

        self.entries["top"][1].bind(
            "<Return>", lambda a: self.set_top(self.vars["top"].get)
        )
        self.entries["top"][1].bind(
            "<FocusOut>", lambda a: self.set_top(self.vars["top"].get)
        )
        self.entries["top"][1].bind(
            "<KP_Enter>", lambda a: self.set_top(self.vars["top"].get)
        )

    # TRANSFORMATION METHODS
    def flip_h(self, event):
        if not self.ss_grid.flip_horizontally():
            return
        self.screens_only_refresh()

    def flip_v(self, event):
        if not self.ss_grid.flip_vertically():
            return
        self.screens_only_refresh()

    def rotate_cw(self, event):
        self.ss_grid.rotate_clockwise()
        if self.ss_grid.screens is not None:
            for screen in self.ss_grid.screens:
                screen.rotate_clockwise()

        self.global_refresh()
        self.update_all_vars()
        ...

    def rotate_ccw(self, event):
        self.ss_grid.rotate_counterclockwise()
        self.global_refresh()
        self.update_all_vars()
        ...

    # REFRESHING UI METHODS        =================================
    # GLOBAL
    def global_refresh(
        self, canvas_changed: tuple[bool, bool] = (False, False)
    ) -> None:
        if canvas_changed[0]:
            self.configure(width=self.ss_grid.canvas.width)
        if canvas_changed[1]:
            self.configure(height=self.ss_grid.canvas.height)

        self.draw_canvas()

        self.api.set_inputs_canvas(
            self.ss_grid.canvas.width, self.ss_grid.canvas.height
        )

        if self.ss_grid.screens:
            for screen in self.ss_grid.screens:
                self.api.set_inputs_screen(screen.merge, screen.mask, **screen.values)

        GridBlock.create_all(self, self.ss_grid)

        self.delete("all")
        GridBlock.draw_all()
        if self.ss_grid.screens is None:
            return
        for screen in self.ss_grid.screens:
            self.draw_screen(screen)

    # screens
    def screens_only_refresh(self):
        if not self.undraw_screens():
            return

        # redraw everything
        for screen in self.ss_grid.screens:
            self.draw_screen(screen)

    def undraw_screens(self) -> bool:
        # check if there are created screens
        if not self.ss_grid.screens:
            return False

        # delete actual rectangles by id
        ids_to_delete = [screen.id for screen in self.ss_grid.screens]
        for id in ids_to_delete:
            self.delete(id)

        return True

    # REFRESH VARS
    @classmethod
    def update_all_vars(cls):
        cls.vars["width"].set(cls.ss_grid.canvas.width)
        cls.vars["height"].set(cls.ss_grid.canvas.height)

        cls.vars["top"].set(cls.ss_grid.margin._top_px)
        cls.vars["left"].set(cls.ss_grid.margin._left_px)
        cls.vars["bottom"].set(cls.ss_grid.margin._bottom_px)
        cls.vars["right"].set(cls.ss_grid.margin._right_px)
        cls.vars["gutter"].set(cls.ss_grid.margin._gutter_px)

        cls.vars["cols"].set(cls.ss_grid.cols)
        cls.vars["rows"].set(cls.ss_grid.rows)

    # ====================================================================== #
    #                           USER SETTERS                                 #
    # ====================================================================== #
    # canvas
    def set_width(self, func: function):
        newset = func()
        oldset = self.ss_grid.canvas.width
        if oldset == newset:
            return

        self.ss_grid.canvas.width = newset
        self.global_refresh((True, False))

    def set_height(self, func: function):
        newset = func()
        oldset = self.ss_grid.canvas.height
        if oldset == newset:
            return

        self.ss_grid.canvas.height = newset
        self.global_refresh((False, True))

    # margin
    def set_all_margins(self, func: function):
        newset = func()

        top = self.ss_grid.margin._top_px
        left = self.ss_grid.margin._left_px
        bottom = self.ss_grid.margin._bottom_px
        right = self.ss_grid.margin._right_px

        if top == left == bottom == right == newset:
            return

        self.ss_grid.margin.all = newset
        self.global_refresh()
        self.update_all_vars()

    def set_top(self, func: function):
        newset = func()
        oldset = self.ss_grid.margin._top_px
        if oldset == newset:
            return

        self.ss_grid.margin.top = newset
        self.global_refresh()

    def set_left(self, func: function):
        newset = func()
        oldset = self.ss_grid.margin._left_px
        if oldset == newset:
            return

        self.ss_grid.margin.left = newset
        self.global_refresh()

    def set_bottom(self, func: function):
        newset = func()
        oldset = self.ss_grid.margin._bottom_px
        if oldset == newset:
            return

        self.ss_grid.margin.bottom = newset
        self.global_refresh()

    def set_right(self, func: function):
        newset = func()
        oldset = self.ss_grid.margin._right_px
        if oldset == newset:
            return

        self.ss_grid.margin.right = newset
        self.global_refresh()

    def set_gutter(self, func: function):
        newset = func()
        oldset = self.ss_grid.margin._gutter_px
        if oldset == newset:
            return

        self.ss_grid.margin.gutter = newset
        self.global_refresh()

    # grid
    def set_col(self, func: function):
        newset = func()
        oldset = self.ss_grid.cols
        if oldset == newset:
            return

        self.ss_grid.cols = newset
        self.global_refresh()

    def set_row(self, func: function):
        newset = func()
        oldset = self.ss_grid.rows
        if oldset == newset:
            return

        self.ss_grid.rows = newset
        self.global_refresh()

    # CANVAS DISPLAY METHODS ==========================================
    max_width = 750
    max_height = 550

    scale_var: tk.DoubleVar = None
    scale_text: tk.StringVar = None

    def compute_canvas_dimensions(self) -> tuple[int]:
        canvas = self.ss_grid.canvas
        aspect_ratio = canvas.aspect_ratio

        max_width = self.max_width
        max_height = self.max_height

        if aspect_ratio > 1:
            canvas_width = max_width
            canvas_height = canvas_width / aspect_ratio
        else:
            canvas_height = max_height
            canvas_width = canvas_height * aspect_ratio

        return canvas_width, canvas_height

    def draw_canvas(self) -> None:
        canvas_width, canvas_height = self.compute_canvas_dimensions()
        self.config(width=canvas_width, height=canvas_height)

        self.refresh_scale_text(canvas_width)

        self.api.add_canvas(self.ss_grid.canvas.width, self.ss_grid.canvas.height)

    def refresh_scale_text(self, new_width: int) -> None:
        self.preview_scale = new_width / self.ss_grid.canvas.width

        self.scale_var.set(value=self.preview_scale)
        self.scale_text.set(f"Preview scale: {self.scale_var.get()*100:.1f}%")

    # UPDATING STATUS BAR
    def announce(self, text: str, clear_after: int = 3500) -> None:
        if self.status_text is None:
            self.status_text = tk.StringVar()
        self.status_text.set(text)
        self.after(clear_after, self.clear_status_bar)

    def clear_status_bar(self, delay: int = 3500) -> None:
        if self.status_text is None:
            self.status_text = tk.StringVar()
        self.status_text.set("")

    # IO METHODS            ==========================================
    fusion_export: str = None  # for saving

    fusion_studio: tk.BooleanVar = None

    def export_for_fusion(self) -> None:
        if self.ss_grid.screens is None:
            return
        screen_values = []
        for screen in self.ss_grid.screens:
            screen_values.append(screen.get_values())
        self.fusion_export = render_fusion_output(
            screen_values, self.ss_grid.canvas.resolution, self.fusion_studio.get()
        )
        pyperclip.copy(self.fusion_export)
        self.announce("Node tree successfuly copied to clipboard.")

    def save_splitscreener_preset():
        ...

    def save_fusion_preset():
        ...

    def reset_defaults():
        ...

    def save_new_defaults():
        ...


###################         RECT TRACKER            ####################
class RectTracker:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.item = None

    def draw(self, start: list[int, int], end: list[int, int], **opts):
        """Draw the rectangle"""
        return self.canvas.create_rectangle(*(list(start) + list(end)), **opts)

    def autodraw(self, **opts):
        """Setup automatic drawing; supports command option"""
        self.start = None
        self.canvas.bind("<Button-1>", self.__update, "+")
        self.canvas.bind("<B1-Motion>", self.__update, "+")
        self.canvas.bind("<ButtonRelease-1>", self.__stop, "+")

        self.rectopts = opts

    def __update(self, event: tk.Event):
        if not self.start:
            self.start = [event.x, event.y]
            return

        if self.item is not None:
            self.canvas.delete(self.item)
        self.item = self.draw(self.start, (event.x, event.y), **self.rectopts)
        # self._command(self.start, (event.x, event.y))

    def __stop(self, event: tk.Event):
        self.start = None
        self.canvas.delete(self.item)
        self.item = None


##################################################################################
#####################       SPLITSCREENER APP       ##############################
##################################################################################
def main():

    root = tk.Tk()

    # LOADING SPLITSCREENER DEFAULTS =========================================
    defaults = ss.defaults

    # SPLITSCREENER INITIALIZERS ======================================
    ss_canvas = ss.Canvas((defaults["width"], defaults["height"]))
    ss_margin = ss.Margin(
        ss_canvas,
        tlbr=(defaults["top"], defaults["left"], defaults["bottom"], defaults["right"]),
        gutter=defaults["gutter"],
    )
    ss_grid = ss.Grid(ss_canvas, ss_margin, (defaults["cols"], defaults["rows"]))

    ##################################################################################
    #####################       ROOT & SETUP      ####################################
    ##################################################################################

    # root.iconbitmap(ip.app_icon)

    # ROOT CONFIGS =========================================================
    root.configure(bg=colors.ROOT_BG)
    root.option_add("*font", fonts.MAIN)
    root.option_add("*foreground", colors.TEXT)
    root.option_add("*Entry.foreground", colors.TEXT)
    root.option_add("*Entry.background", colors.ENTRY_BG)
    root.option_add("*Entry.disabledbackground", colors.TEXT_DARKER)
    root.option_add("*background", colors.ROOT_BG)
    root.option_add("*Checkbutton.font", fonts.SMALL)
    root.attributes("-topmost", True)
    # root.minsize(1260, 740)
    root.title("SplitScreener 1.0")
    root.resizable(False, False)

    # SETTING UP THE MAIN TK GRID ======================================================
    root.columnconfigure(index=1, weight=1, minsize=220)  # LEFT SIDEBAR
    root.columnconfigure(index=2, weight=1, minsize=820)  # MAIN SECTION, THE CREATOR
    root.columnconfigure(
        index=3, weight=1, minsize=150
    )  # RIGHT SIDEBAR (nothing there yet)
    root.rowconfigure(index=1, weight=3)  # HEADER
    root.rowconfigure(index=2, weight=1)  # MAIN SECTION, THE CREATOR FRAME AND SETTINGS
    root.rowconfigure(index=3, weight=1)  # THE RENDER BUTTON FRAME
    root.rowconfigure(index=4, weight=3)  # FOOTER

    # CREATING THE FRAMES
    header = tk.Frame(root)
    button_frame_left = tk.Frame(root)
    creator_frame = tk.Frame(root)
    button_frame_right = tk.Frame(root)
    render_bttn_frame = tk.Frame(root)
    footer = tk.Frame(root)

    # adding them to the grid
    header.grid(column=1, row=1, columnspan=3)
    button_frame_left.grid(column=1, row=2)
    creator_frame.grid(column=2, row=2, padx=10, pady=10)
    button_frame_right.grid(column=3, row=2, ipadx=20)
    render_bttn_frame.grid(column=2, row=3)
    footer.grid(column=1, row=4, columnspan=3)

    ##################################################################################
    #####################       HEADER      ##########################################
    ##################################################################################

    # APP TITLE
    app_title = tk.Label(header, height=2, justify=tk.CENTER, text="SplitScreener")
    app_title.pack(anchor=tk.S, pady=20)

    ##################################################################################
    #####################       SCREEN SPLITTER  #####################################
    ##################################################################################
    screen_splitter = ScreenSplitter(
        creator_frame,
        background=colors.CANVAS_BG,
        bd=0,
        highlightthickness=0,
        relief="ridge",
    )
    ScreenSplitter.ss_grid = ss_grid
    ScreenSplitter.scale_var = tk.DoubleVar()
    ScreenSplitter.scale_text = tk.StringVar()
    ScreenSplitter.screen_color: str = colors.CANVAS_SCREEN
    ScreenSplitter.screen_color_pre_delete = colors.CANVAS_SCREEN_PRE_DELETE
    ScreenSplitter.screen_color_hover = colors.CANVAS_SCREEN_HOVER
    ScreenSplitter.fusion_studio: tk.BooleanVar = tk.BooleanVar()
    ScreenSplitter.api = ResolveFusionAPI()

    screen_splitter.draw_canvas()

    # BINDING FOR CLICK AND DRAG SCREEN ADD =======================
    screen_splitter.bind("<Button-1>", screen_splitter.on_click)
    screen_splitter.bind("<ButtonRelease-1>", screen_splitter.on_release)

    # SCALE LABEL ====================================================================
    scale_label = tk.Label(
        creator_frame,
        font=fonts.SMALL,
        textvariable=screen_splitter.scale_text,
        justify=tk.RIGHT,
        bg=colors.ROOT_BG,
        foreground=colors.TEXT_DARKER,
    )

    # instruction_label.grid( row=1,  sticky=tk.W)
    screen_splitter.grid(row=2, ipadx=20, pady=5)
    scale_label.grid(row=3, sticky=tk.NE)

    # RENDERING GRID BLOCKS ======================================================
    GridBlock.create_all(
        screen_splitter,
        ss_grid,
        fill=colors.CANVAS_BLOCK,
        activefill=colors.CANVAS_BLOCK_HOVER,
        outline=colors.CANVAS_BLOCK,
        activeoutline=colors.CANVAS_BLOCK,
        activewidth=1,
    )
    GridBlock.draw_all()

    # SELECTION RECTANGLE ==============================================
    rect = RectTracker(screen_splitter)
    rect.autodraw(fill="", width=0.5, outline=colors.TEXT_DARKER, dash=(4, 4))

    ##################################################################################
    ##################### BUTTON LEFT FRAME ##########################################
    ##################################################################################

    # TKINTER VARIABLES FOR USER GRID SETTINGS ========================================
    vars: dict[str, tk.IntVar] = {}

    # CANVAS =======================
    vars["width"] = tk.IntVar(value=defaults["width"])

    vars["height"] = tk.IntVar(value=defaults["height"])

    # MARGIN =======================
    vars["top"] = tk.IntVar(value=defaults["top"])

    vars["left"] = tk.IntVar(value=defaults["left"])

    vars["bottom"] = tk.IntVar(value=defaults["bottom"])

    vars["right"] = tk.IntVar(value=defaults["right"])

    vars["gutter"] = tk.IntVar(value=defaults["gutter"])

    # GRID =======================
    vars["cols"] = tk.IntVar(value=defaults["cols"])

    vars["rows"] = tk.IntVar(value=defaults["rows"])

    ScreenSplitter.vars = vars

    # LINK MARGINS ======================================================================

    # link button

    link_margins = tk.Label(button_frame_left, text="🔗", foreground=colors.TEXT_DARKER)
    link_margins.grid(column=2, row=5, rowspan=2, sticky=tk.W, padx=4)
    set_hover_style(link_margins)
    link_margins.bind("<Button-1>", screen_splitter.link_margins, add="+")

    tk.Frame(button_frame_left, width=10).grid(column=1)

    # ENTRIES FOR USER INPUT ==============================================
    def mk_entries(parent: tk.Frame, vars: dict[str, tk.IntVar]):
        var_entries = {}
        for key, var in vars.items():
            new_key = key
            if key == "cols" or key == "rows":
                new_key = f"# {key}"
            label = tk.Label(
                parent,
                text=new_key.title(),
                bg=colors.ROOT_BG,
                justify=tk.LEFT,
                padx=20,
            )

            entry = tk.Entry(
                parent,
                width=8,
                justify=tk.CENTER,
                textvariable=var,
                foreground=colors.TEXT,
                bd=0,
                relief="flat",
                bg=colors.ENTRY_BG,
                highlightthickness=1,
                highlightbackground=colors.CANVAS_BG,
                highlightcolor=colors.CANVAS_BG,
                disabledbackground=colors.CANVAS_BLOCK,
            )
            var_entries[key] = (label, entry)
        return var_entries

    def grid_entries(entries: dict[str, tuple[tk.Label, tk.Entry]]):
        i = 1
        for key, tuple in entries.items():
            tuple[0].grid(column=3, row=i, padx=0, pady=10, sticky=tk.W)
            tuple[1].grid(column=4, row=i, padx=10, ipady=5)
            if key == "height" or key == "gutter":
                i += 1
            i += 1

        # adds spacers
        tk.Label(button_frame_left, height=1, background=colors.ROOT_BG).grid(
            column=2, row=3, pady=3
        )
        tk.Label(button_frame_left, height=1, background=colors.ROOT_BG).grid(
            column=2, row=9, pady=3
        )
        tk.Label(button_frame_left, height=1, background=colors.ROOT_BG).grid(
            column=2, row=12, pady=3
        )

    entries: dict[str, tuple[tk.Label, tk.Entry]] = mk_entries(button_frame_left, vars)
    grid_entries(entries)

    ScreenSplitter.entries = entries

    # BINDING ENTRIES TO REFRESH FUNCS ======================================================================
    entries["width"][1].bind(
        "<Return>", lambda a: screen_splitter.set_width(vars["width"].get)
    )
    entries["width"][1].bind(
        "<FocusOut>", lambda a: screen_splitter.set_width(vars["width"].get)
    )
    entries["width"][1].bind(
        "<KP_Enter>", lambda a: screen_splitter.set_width(vars["width"].get)
    )

    entries["height"][1].bind(
        "<Return>", lambda a: screen_splitter.set_height(vars["height"].get)
    )
    entries["height"][1].bind(
        "<FocusOut>", lambda a: screen_splitter.set_height(vars["height"].get)
    )
    entries["height"][1].bind(
        "<KP_Enter>", lambda a: screen_splitter.set_height(vars["height"].get)
    )

    entries["top"][1].bind(
        "<Return>", lambda a: screen_splitter.set_top(vars["top"].get)
    )
    entries["top"][1].bind(
        "<FocusOut>", lambda a: screen_splitter.set_top(vars["top"].get)
    )
    entries["top"][1].bind(
        "<KP_Enter>", lambda a: screen_splitter.set_top(vars["top"].get)
    )

    entries["left"][1].bind(
        "<Return>", lambda a: screen_splitter.set_left(vars["left"].get)
    )
    entries["left"][1].bind(
        "<FocusOut>", lambda a: screen_splitter.set_left(vars["left"].get)
    )
    entries["left"][1].bind(
        "<KP_Enter>", lambda a: screen_splitter.set_left(vars["left"].get)
    )

    entries["bottom"][1].bind(
        "<Return>", lambda a: screen_splitter.set_bottom(vars["bottom"].get)
    )
    entries["bottom"][1].bind(
        "<FocusOut>", lambda a: screen_splitter.set_bottom(vars["bottom"].get)
    )
    entries["bottom"][1].bind(
        "<KP_Enter>", lambda a: screen_splitter.set_bottom(vars["bottom"].get)
    )

    entries["right"][1].bind(
        "<Return>", lambda a: screen_splitter.set_right(vars["right"].get)
    )
    entries["right"][1].bind(
        "<FocusOut>", lambda a: screen_splitter.set_right(vars["right"].get)
    )
    entries["right"][1].bind(
        "<KP_Enter>", lambda a: screen_splitter.set_right(vars["right"].get)
    )

    entries["gutter"][1].bind(
        "<Return>", lambda a: screen_splitter.set_gutter(vars["gutter"].get)
    )
    entries["gutter"][1].bind(
        "<FocusOut>", lambda a: screen_splitter.set_gutter(vars["gutter"].get)
    )
    entries["gutter"][1].bind(
        "<KP_Enter>", lambda a: screen_splitter.set_gutter(vars["gutter"].get)
    )

    entries["cols"][1].bind(
        "<Return>", lambda a: screen_splitter.set_col(vars["cols"].get)
    )
    entries["cols"][1].bind(
        "<FocusOut>", lambda a: screen_splitter.set_col(vars["cols"].get)
    )
    entries["cols"][1].bind(
        "<KP_Enter>", lambda a: screen_splitter.set_col(vars["cols"].get)
    )

    entries["rows"][1].bind(
        "<Return>", lambda a: screen_splitter.set_row(vars["rows"].get)
    )
    entries["rows"][1].bind(
        "<FocusOut>", lambda a: screen_splitter.set_row(vars["rows"].get)
    )
    entries["rows"][1].bind(
        "<KP_Enter>", lambda a: screen_splitter.set_row(vars["rows"].get)
    )

    ##################################################################################
    ##################### BUTTON RIGHT FRAME #########################################
    ##################################################################################

    button_frame_right.columnconfigure(index=1, weight=1)
    button_frame_right.rowconfigure(index=1, weight=1)
    button_frame_right.rowconfigure(index=2, weight=1)
    button_frame_right.rowconfigure(index=3, weight=1)
    button_frame_right.rowconfigure(index=4, weight=1)
    button_frame_right.rowconfigure(index=5, weight=1)
    button_frame_right.rowconfigure(index=6, weight=1)
    button_frame_right.option_add("*font", fonts.SMALL)

    # Rotate Clockwise
    # # rotate_cw_img = [ImageTk.PhotoImage(file=ip.icn_rotate_cw[x]) for x in range(3)]
    # # rotate_cw_icon = tk.Label(button_frame_right, image=rotate_cw_img[0])
    # rotate_cw_text = tk.Label(
    #     button_frame_right, text="Rotate Clockwise", justify=tk.LEFT
    # )
    # # set_hover_style(rotate_cw_icon, rotate_cw_img)

    # # rotate_cw_icon.bind("<Button-1>", screen_splitter.rotate_cw_img, add='+')
    # rotate_cw_icon.grid(column=1, row=1, padx=5, pady=20)
    # rotate_cw_text.grid(column=2, row=1, padx=10, sticky=tk.W)

    # # Rotate Counterclockwise
    # rotate_ccw_img = [ImageTk.PhotoImage(file=ip.icn_rotate_ccw[x]) for x in range(3)]
    # rotate_ccw_icon = tk.Label(button_frame_right, image=rotate_ccw_img[0])
    # rotate_ccw_text = tk.Label(
    #     button_frame_right, text="Rotate\nCounterclockwise", justify=tk.LEFT
    # )
    # # set_hover_style(rotate_ccw_icon, rotate_ccw_img)

    # # rotate_ccw_icon.bind("<Button-1>", screen_splitter.rotate_ccw, add='+')
    # rotate_ccw_icon.grid(column=1, row=2, padx=5, pady=20)
    # rotate_ccw_text.grid(column=2, row=2, padx=10, sticky=tk.W)

    # Flip Vertically
    flipv_text = tk.Label(
        button_frame_right,
        text="↕️ Flip Vertically",
        justify=tk.LEFT,
        foreground=colors.TEXT_DARKER,
    )

    set_hover_style(flipv_text)

    flipv_text.bind("<Button-1>", screen_splitter.flip_v, add="+")

    flipv_text.grid(column=1, row=3, padx=0, pady=20, sticky=tk.W)

    # Flip Horizontally
    fliph_text = tk.Label(
        button_frame_right,
        text="↔️ Flip Horizontally",
        justify=tk.LEFT,
        foreground=colors.TEXT_DARKER,
    )

    set_hover_style(fliph_text)

    fliph_text.bind("<Button-1>", screen_splitter.flip_h, add="+")

    fliph_text.grid(column=1, row=4, padx=0, pady=20, sticky=tk.W)

    # Delete all screens
    delete_text = tk.Label(
        button_frame_right,
        text="🗑 Delete all Screens",
        justify=tk.LEFT,
        foreground=colors.TEXT_DARKER,
    )
    set_hover_style(delete_text)

    delete_text.bind("<Button-1>", screen_splitter.pre_delete_all_screens, add="+")
    delete_text.bind("<ButtonRelease-1>", screen_splitter.delete_all_screens, add="+")

    delete_text.grid(column=1, row=5, padx=0, pady=20, sticky=tk.W)

    # spacer
    tk.Label(button_frame_right, height=1).grid(row=6, columnspan=1)

    ##################################################################################
    ##################### RENDER BUTTON AND FOOTER ###################################
    ##################################################################################

    # FOOTER FRAME ================================================
    screen_splitter.status_text = tk.StringVar(
        value="Draw a rectangle on the grid above to create your first Screen."
    )

    status_bar = tk.Label(
        footer,
        textvariable=screen_splitter.status_text,
        justify=tk.CENTER,
        foreground=colors.TEXT_DARKER,
    )

    status_bar.pack(pady=15)
    tk.Frame(footer, height=15).pack()

    root.mainloop()


if __name__ == "__main__":
    main()
