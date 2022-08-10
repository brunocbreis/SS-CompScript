import tkinter as tk
from ss_backend.style import colors, fonts
from ss_backend.core import Canvas, Margin, Grid
from ss_backend import (
    DEFAULTS,
    ScreenSplitterGUI,
    Controller,
    EventHandler,
    UserInput,
)
from ss_backend.fusion_alias import Comp, Fusion, Tool
from ss_backend.utils import find_first_missing

# FAKE FUSION FOR TESTING
def initialize_fake_fusion():
    print("Initializing fake Fusion.")
    global fusion, comp
    fusion = Fusion()
    comp = Comp()


try:
    print(fusion)
except NameError:
    initialize_fake_fusion()

# GLOBAL
IS_RESOLVE = True if fusion.GetResolve() else False


class App:
    def build_layout(self):
        self.root = tk.Tk()
        root = self.root

        # Configures root.  ===================================================
        # Window config
        root.attributes("-topmost", True)
        root.resizable(False, False)
        root.title("SplitScreener")

        # Bg config
        root.configure(bg=colors.ROOT_BG)
        root.option_add("*background", colors.ROOT_BG)

        # Text config
        root.option_add("*font", fonts.MAIN)
        root.option_add("*foreground", colors.TEXT)

        # Entry config
        root.option_add("*Entry.foreground", colors.TEXT)
        root.option_add("*Entry.background", colors.ENTRY_BG)
        root.option_add("*Entry.disabledbackground", colors.TEXT_DARKER)

        # Sets up the main window grid.  ======================================
        root.columnconfigure(index=1, weight=1, minsize=220)  # LEFT SIDEBAR
        root.columnconfigure(index=2, weight=1, minsize=820)  # MAIN SECTION
        root.columnconfigure(index=3, weight=1, minsize=150)  # RIGHT SIDEBAR
        root.rowconfigure(index=1, weight=3)  # HEADER
        root.rowconfigure(index=2, weight=1)  # MAIN SECTION
        root.rowconfigure(index=3, weight=1)  # THE RENDER BUTTON (deprecated)
        root.rowconfigure(index=4, weight=3)  # FOOTER

        # Creates and places frames for UI Widgets ============================
        self.header = tk.Frame(root)
        self.frame_left_entries = tk.Frame(root)
        self.frame_screen_creation = tk.Frame(root)
        self.frame_right_transformations = tk.Frame(root)
        self.footer = tk.Frame(root)

        # Adding to grid...
        self.header.grid(column=1, row=1, columnspan=3)
        self.frame_left_entries.grid(column=1, row=2)
        self.frame_screen_creation.grid(column=2, row=2, padx=10, pady=10)
        self.frame_right_transformations.grid(column=3, row=2, ipadx=20)
        self.footer.grid(column=1, row=3, columnspan=3)

    def initialize_splitscreener(self):
        canvas = Canvas((DEFAULTS["width"], DEFAULTS["height"]))
        margin = Margin(
            canvas,
            tlbr=tuple(
                DEFAULTS[key]
                for key in DEFAULTS
                if key in ("top", "left", "bottom", "right")
            ),
            gutter=DEFAULTS["gutter"],
        )
        self.grid = Grid(canvas, margin)

    def initialize_user_interface(self):
        # Resolve API
        self.api = ResolveFusionAPI()
        self.api.add_canvas(*self.grid.canvas.resolution)

        # Screen Creation UI
        self.gui = ScreenSplitterGUI(
            master=self.frame_screen_creation,
            ss_grid=self.grid,
            max_width=800,
            max_height=600,
        )
        self.gui.draw_canvas()
        self.gui.grid(row=1)
        self.gui.draw_grid()

        # Controller
        self.controller = Controller(self.grid, self.api, self.gui)

        # Handler
        self.handler = EventHandler(self.controller, self.gui)

        # Interface – Left Frame
        self.interface = UserInput(self.handler)
        self.interface.make_left_frame_entries(self.frame_left_entries)
        self.interface.bind_left_frame_entries()
        self.interface.grid_entries(self.frame_left_entries)
        self.interface.make_link_margins_button(self.frame_left_entries)

        # Interface – Transformation buttons
        frame = self.frame_right_transformations

        frame.columnconfigure(index=1, weight=1)
        for i in range(6):
            frame.rowconfigure(index=i + 1, weight=1)
        frame.option_add("*font", fonts.SMALL)

        self.interface.make_transformation_buttons(frame)

    def run(self):
        try:
            self.root.mainloop()
        except NameError:
            raise Exception("Please initialize a root tk window first.")


class ResolveFusionAPI:
    def __init__(self) -> None:
        self.merges: list[Tool] = []
        self.masks: list[Tool] = []
        self.media_ins: list[Tool] = []
        self.screens: list[set[Tool, Tool, Tool]] = []

    # PROTOCOL METHODS  =======================================================
    def refresh_global(
        self,
        resolution: tuple[int, int],
        screen_tools: list[tuple[Tool, Tool]] | None = None,
        screen_values: list[dict[str, float]] | None = None,
    ):
        """Calls all necessary methods for when user changes settings."""
        if not (
            self.canvas.GetInput("Width") == resolution[0]
            and self.canvas.GetInput("Height") == resolution[1]
        ):
            self.set_inputs_canvas(*resolution)

        if not screen_tools:
            return

        for tools, values in zip(screen_tools, screen_values):
            merge, mask = tools
            self.set_inputs_screen(merge, mask, **values)

    def add_canvas(self, width: int, height: int):
        canvas = comp.AddTool("Background", 0, 0)
        canvas.SetAttrs({"TOOLS_Name": "SSCanvas"})
        canvas.SetInput("UseFrameFormatSettings", 0)

        self.canvas = canvas
        self.set_inputs_canvas(width, height)

        self.add_media_out()

    def add_screen(self, **kwargs) -> tuple[Tool, Tool, Tool]:
        node_y = len(self.merges) + 1

        merge = comp.AddTool("Merge", 0, node_y)
        mask = comp.AddTool("RectangleMask", 1, node_y)
        media_in = comp.AddTool("MediaIn", -1, node_y)

        mask_inps = {key: kwargs[key] for key in ("Width", "Height", "Center")}
        mrg_inps = {key: kwargs[key] for key in ("Center", "Size")}
        media_in.SetInput("Layer", f"{self.next_media_in_layer}")

        mrg_inps["EffectMask"] = mask
        mrg_inps["Foreground"] = media_in
        if self.merges:
            mrg_inps["Background"] = self.merges[-1]
        else:
            mrg_inps["Background"] = self.canvas

        self.set_inputs(merge, **mrg_inps)
        self.set_inputs(mask, **mask_inps)

        self.merges.append(merge)
        self.masks.append(mask)
        self.media_ins.append(media_in)

        self.set_position_media_out()
        self.set_inputs_media_out()

        return merge, mask, media_in

    def delete_screen(self, screen: list[Tool, Tool, Tool]) -> None:
        self.delete_tool_batch(*screen)

        self.merges.remove(screen[0])
        self.masks.remove(screen[1])
        self.media_ins.remove(screen[2])

        self.refresh_positions()

    def delete_all_screens(self) -> None:
        self.delete_tool_batch(*self.masks)
        self.delete_tool_batch(*self.merges)
        self.delete_tool_batch(*self.media_ins)

        self.masks.clear()
        self.merges.clear()
        self.media_ins.clear()

    # POSITIONING NODES ON FLOW
    def refresh_positions(self):
        flow = comp.CurrentFrame.FlowView
        flow.QueueSetPos(self.canvas, 0, 0)
        if self.merges:
            for index, merge in enumerate(self.merges):
                flow.QueueSetPos(merge, 0, index + 1)
            for index, mask in enumerate(self.masks):
                flow.QueueSetPos(mask, 1, index + 1)
            for index, media_in in enumerate(self.media_ins):
                flow.QueueSetPos(media_in, -1, index + 1)
        else:
            index = 0
        flow.QueueSetPos(self.media_out, 0, index + 2)

        flow.FlushSetPosQueue()

    def set_position_media_out(self) -> None:
        flow = comp.CurrentFrame.FlowView
        flow.SetPos(self.media_out, 0, len(self.media_ins) + 1)

    # DEALING WITH REGULAR INPUTS
    def set_inputs(self, tool: Tool, **kwargs) -> None:
        for key, value in kwargs.items():
            tool.SetInput(key, value)

    def set_inputs_batch(self, tools: list[Tool], **kwargs) -> None:
        for tool in tools:
            self.set_inputs(tool, **kwargs)

    def set_inputs_screen(self, merge: Tool, mask: Tool, **kwargs) -> None:
        mask_inps = {key: kwargs[key] for key in ("Width", "Height", "Center")}
        mrg_inps = {key: kwargs[key] for key in ("Center", "Size")}
        self.set_inputs(merge, **mrg_inps)
        self.set_inputs(mask, **mask_inps)

    def set_inputs_canvas(self, width: int, height: int) -> None:
        if self.canvas:
            self.set_inputs(
                self.canvas,
                Width=width,
                Height=height,
            )

    def set_inputs_media_out(self) -> None:
        if self.merges:
            self.media_out.SetInput("Input", self.merges[-1])
        else:
            self.media_out.SetInput("Input", self.canvas)

    # CREATING TOOLS
    def add_media_out(self):
        media_out = comp.AddTool("MediaOut", 0, 2)
        media_out.SetInput("Input", self.canvas)
        comp.CurrentFrame.ViewOn(media_out, 2)
        self.media_out = media_out

    # DELETING TOOLS
    def delete_tool(self, tool: Tool) -> None:
        tool.Delete()

    def delete_tool_batch(self, *tools: Tool) -> None:
        for tool in tools:
            tool.Delete()

    # UTILS
    @property
    def next_media_in_layer(self):
        if not self.media_ins:
            return 0
        return find_first_missing(
            sorted([int(media_in.GetInput("Layer")) for media_in in self.media_ins])
        )


def main():
    app = App()

    app.build_layout()

    app.initialize_splitscreener()

    app.initialize_user_interface()

    app.run()


if __name__ == "__main__":
    main()
