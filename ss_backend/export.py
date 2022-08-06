import pickle
import json
import os
import pysion


# Specifically SplitScreener Functions
def create_canvas(resolution: tuple[int, int]) -> str:
    return pysion.add_tool(
        "Background",
        "SSCanvas",
        pysion.add_inputs(Width=resolution[0], Height=resolution[1]),
        (0, -1),
    )


def create_screen(
    last_tool_name: str,
    resolution: tuple[int, int],
    index: int = 0,
    fusion_studio: bool = False,
    **inputs,
) -> str:
    """Expects a dictionary of SplitScreener generated Screen Values
    and returns a string compatible with DaVinci Resolve or Fusion
    """

    # Fusion Studio doesn't support MediaIns or Outs, so we bypass them in this case
    media_in = ""
    media_in_as_input_to_merge = ""
    if not fusion_studio:
        media_in = pysion.add_tool(
            "MediaIn",
            f"SSScreen{index+1}",
            pysion.add_inputs(Layer=f'"{index}"'),
            (-1, index),
        )
        media_in_as_input_to_merge = pysion.add_source_input(
            "Foreground", f"SSScreen{index+1}", "Output"
        )

    merge = pysion.add_tool(
        "Merge",
        f"SSMerge{index+1}",
        pysion.add_inputs(
            Center=f"{{ {inputs['CenterX']}, {inputs['CenterY']} }}",
            Size=inputs["Size"],
        )
        + pysion.add_source_input("Background", last_tool_name, "Output")
        + media_in_as_input_to_merge
        + pysion.add_source_input("EffectMask", f"SSMask{index+1}", "Mask"),
        (0, index),
    )

    mask = pysion.add_tool(
        "RectangleMask",
        f"SSMask{index+1}",
        pysion.add_inputs(
            Center=f"{{ {inputs['CenterX']}, {inputs['CenterY']} }}",
            Width=inputs["Width"],
            Height=inputs["Height"],
            MaskWidth=resolution[0],
            MaskHeight=resolution[1],
        ),
        (1, index),
    )

    return merge + media_in + mask


def create_media_out(position: tuple[int, int], last_tool_name: str) -> str:
    return pysion.add_tool(
        "MediaOut",
        "MediaOut1",
        pysion.add_source_input("Input", last_tool_name, "Output"),
        position,
    )


def render_fusion_output(
    screen_values: list[dict[str, int]],
    resolution: tuple[int, int],
    fusion_studio: bool = False,
) -> str:

    fusion_canvas = create_canvas(resolution)

    fusion_screens = ""
    last_tool_name = "SSCanvas"
    i = 0
    for screen in screen_values:
        fusion_screen = create_screen(
            last_tool_name,
            resolution,
            i,
            fusion_studio,
            Width=screen["Width"],
            Height=screen["Height"],
            CenterX=screen["Center.X"],
            CenterY=screen["Center.Y"],
            Size=screen["Size"],
        )
        i += 1
        last_tool_name = f"SSMerge{i}"
        fusion_screens += fusion_screen

    fusion_media_out = ""
    if not fusion_studio:
        fusion_media_out = create_media_out((0, len(screen_values)), last_tool_name)

    fusion_output = pysion.wrap_for_fusion(
        fusion_canvas + fusion_screens + fusion_media_out
    )

    return fusion_output


# defaults and presets
def load_defaults_pickle(defaults_directory: str) -> tuple[dict, str, int]:
    defaults_files = os.listdir(defaults_directory)
    defaults_files.sort()

    defaults = []
    for file in defaults_files:
        with open(os.path.join("defaults", file), "rb") as file:
            dict = pickle.load(file)
            defaults.append(dict)

    canvas_defaults, grid_defaults, margin_defaults = [default for default in defaults]
    return (canvas_defaults, grid_defaults, margin_defaults)


def load_defaults(defaults_file: str | os.PathLike) -> dict[dict[str, int]]:
    try:
        with open(defaults_file, "r") as _:
            defaults = json.load(_)
        return defaults
    except FileNotFoundError:
        print("Defaults file not found.")
        return


def save_preset_for_fusion(
    presets_directory: str | os.PathLike,
    fusion_output: str,
    preset_name: str = "SplitScreenerPreset",
) -> None:

    presets_directory = presets_directory
    preset_files = [
        f
        for f in os.listdir(presets_directory)
        if os.path.isfile(os.path.join(presets_directory, f))
    ]
    preset_file_name = f"{preset_name}.setting"
    i = 0
    while preset_file_name in preset_files:
        i += 1
        preset_file_name = f"{preset_name}_{i}.setting"

    with open(
        os.path.join(presets_directory, preset_file_name), "w"
    ) as new_preset_file:
        new_preset_file.write(fusion_output)


def save_preset_for_splitscreener(
    presets_directory: str | os.PathLike,
    splitscreener_values: dict[dict[str, int]],
    preset_name: str = "",
) -> None:

    if not preset_name:
        if "screens" in splitscreener_values:
            screen_amt = splitscreener_values["screens"]
            preset_name += f"_{len(screen_amt)}Screen{'s' if screen_amt > 1 else ''}"
    ...


# testing area
def test():
    bg = pysion.add_tool(
        "Background",
        "Background1",
        pysion.add_inputs(Width=1920, Height=1080, TopLeftRed=1),
        (0, 1),
    )
    bg2 = pysion.add_tool(
        "Background", "Background2", pysion.add_inputs(Width=1920, Height=1080), (1, 0)
    )
    merge = pysion.add_tool(
        "Merge",
        "Merge1",
        pysion.add_inputs(Size="1.5", Center="{.5,.5}")
        + pysion.add_source_input("Background", "Background1", "Output")
        + "\n"
        + pysion.add_source_input("Foreground", "Background2", "Output"),
        (0, 0),
    )

    tools = bg + bg2 + merge
    tools = pysion.wrap_for_fusion(tools)

    print(tools)


if __name__ == "__main__":
    print("You're not supposed to run this file. Get out of here!")
