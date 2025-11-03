import os
from PIL import Image
import numpy as np
import dearpygui.dearpygui as dpg
import base64

FOLDER_INPUT = "unitpng"
FOLDER_OUTPUT = "tweak_output"

# Global dict to track the toggle state of each button
# key = filename without .png
# value = (state, enabled_theme, disabled_theme)
button_states = {}

# Global tag for main window
main_window_tag = "main_window"


def base64_encode(data: str) -> str:
    """
    Encode a string to base64 and remove padding ('=').
    will add the bset command
    Returns a string.
    """
    encoded = base64.b64encode(data.encode("utf-8")).decode("ascii")
    encoded = "!bset tweakunits " + encoded

    return encoded.rstrip("=")  # remove any '=' padding



def base64_decode(data: str) -> str:
    """
    Decode a base64 string, adding '=' padding if needed.
    Returns a string.
    """
    #remove twek command
    data = data.replace("!bset tweakunits ","")

    # Add padding if missing
    padding = 4 - (len(data) % 4)
    if padding and padding != 4:
        data += "=" * padding
    decoded = base64.b64decode(data).decode("utf-8")
    return decoded

def export(filename: str = None):
    """
    Export Lua file and encoded base64 file.
    If filename is provided, files will be <filename>.lua and <filename>.txt
    Otherwise defaults to output.lua and output.txt
    """
    folder_out = os.path.join(os.path.dirname(__file__), FOLDER_OUTPUT)
    os.makedirs(folder_out, exist_ok=True)

    base_name = filename if filename else "output"
    lua_file_path = os.path.join(folder_out, f"{base_name}.lua")
    encoded_file_path = os.path.join(folder_out, f"{base_name}.txt")

    # --- Build Lua string in memory ---
    lua_content = "{\n"
    for key, (state, _, _) in button_states.items():
        if not state:  # only include toggled red
            lua_content += "  " + key + " = { maxThisUnit = 0 },\n"
    lua_content += "}\n"

    # Save Lua string to file
    with open(lua_file_path, "w") as f:
        f.write(lua_content)
    print("[INFO] Wrote " + lua_file_path)

    # Read list.txt and encode to base64 command
    encoded_data = base64_encode(lua_content)

    # Write encoded base64 string to paste_command.txt
    with open(encoded_file_path, "w") as f:
      f.write(encoded_data + "\n")
    print("[INFO] Wrote " + encoded_file_path)



def import_tweak(lua_file: str):
    """
    Import a Lua file with unit restrictions and update button_states.
    lua_file: path to the .lua file
    """
    if not os.path.isfile(lua_file):
        print(f"[ERROR] Lua file '{lua_file}' not found.")
        return

    # Read Lua content
    with open(lua_file, "r") as f:
        lines = f.readlines()

    # Extract keys (everything before '=' on lines that contain maxThisUnit = 0)
    keys_disabled = set()
    for line in lines:
        line = line.strip()
        if line.endswith(","):
            line = line[:-1].strip()
        if "= { maxThisUnit = 0 }" in line:
            key = line.split("=", 1)[0].strip()
            keys_disabled.add(key)

    # Update button_states
    for key in button_states:
        state, enabled_theme, disabled_theme = button_states[key]
        if key in keys_disabled:
            button_states[key] = (False, enabled_theme, disabled_theme)  # red
        else:
            button_states[key] = (True, enabled_theme, disabled_theme)   # green

    # --- Cache button tags once ---
    if not hasattr(import_tweak, "_button_cache"):
        import_tweak._button_cache = {}
        all_items = dpg.get_all_items()
        for item in all_items:
            try:
                ud = dpg.get_item_user_data(item)
                if isinstance(ud, tuple) and len(ud) >= 1:
                    key = ud[0]
                    import_tweak._button_cache[key] = item
            except Exception:
                continue

    # --- Update UI using cached tags ---
    for key, (state, enabled_theme, disabled_theme) in button_states.items():
        button_tag = import_tweak._button_cache.get(key)
        if button_tag:
            dpg.bind_item_theme(button_tag, enabled_theme if state else disabled_theme)
            dpg.set_item_user_data(button_tag, (key, state, enabled_theme, disabled_theme))
    print(f"[INFO] Imported Lua file '{lua_file}' and updated button states.")

def on_image_click(sender, app_data, user_data):
    # user_data = (key, state, enabled_theme, disabled_theme)
    key, state, enabled_theme, disabled_theme = user_data
    state = not state  # flip the state
    # Apply the appropriate theme
    dpg.bind_item_theme(sender, enabled_theme if state else disabled_theme)
    # Update the user_data for next click
    dpg.set_item_user_data(sender, (key, state, enabled_theme, disabled_theme))
    # Update global dict correctly
    button_states[key] = (state, enabled_theme, disabled_theme)
    print(f"[TOGGLE] {key} is now {'ON' if state else 'OFF'}")


def load_texture(path):
    im = Image.open(path).convert("RGBA")
    width, height = im.size
    data = np.array(im, dtype=np.float32) / 255.0
    data = data.flatten()
    return width, height, data


def create_image_grid(folder, columns=9, thumb_size=64):
    # --- Create themes (enabled/green, disabled/red) ---
    with dpg.theme() as enabled_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 200, 0, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 200, 0, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 200, 0, 255), category=dpg.mvThemeCat_Core)

    with dpg.theme() as disabled_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (200, 0, 0, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (200, 0, 0, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (200, 0, 0, 255), category=dpg.mvThemeCat_Core)

    # --- Register textures ---
    files = []
    for root, dirs, filenames in os.walk(folder):
        for f in filenames:
            if f.lower().endswith(".png"):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, folder)
                files.append((rel_path, full_path))
    files.sort(key=lambda x: x[0])

    with dpg.texture_registry(show=False):
        for rel_path, full_path in files:
            try:
                width, height, data = load_texture(full_path)
                tex_tag = "tex_" + rel_path.replace(os.sep, "_")
                dpg.add_static_texture(width, height, data, tag=tex_tag)
            except Exception as e:
                print("[FAIL] Could not load texture:", rel_path, "-", e)

    # --- Top buttons stay fixed ---
    with dpg.group(horizontal=True):
        # Input field for filename
        filename_input = dpg.add_input_text(default_value="output", width=200)

        # Button calls a lambda that reads the input text and passes it to export()
        dpg.add_button(
            label="Generate LUA",
            callback=lambda: export(dpg.get_value(filename_input))
        )

        # Load LUA button (just shows the dialog)
        def load_lua_callback():
            # Prevent re-opening if already visible
            if not dpg.is_item_shown("load_lua_dialog"):
                dpg.show_item("load_lua_dialog")

        dpg.add_button(label="Load LUA", callback=load_lua_callback)


    dpg.add_spacing(count=1)

    # --- Scrollable area for image grid ---
    with dpg.child_window(width=-1, height=-1, autosize_x=True, autosize_y=True, border=False, horizontal_scrollbar=True):
        # Group buttons by folder
        folder_dict = {}
        for rel_path, full_path in files:
            folder_name = os.path.dirname(rel_path)
            folder_dict.setdefault(folder_name, []).append((rel_path, full_path))

        for folder_name in sorted(folder_dict.keys()):
            display_name = folder_name if folder_name != '.' else "Root"
            indent = "    " * (folder_name.count(os.sep))
            with dpg.tree_node(label=indent + display_name, default_open=True):
                files_in_folder = sorted(folder_dict[folder_name])
                # create rows of buttons
                for i in range(0, len(files_in_folder), columns):
                    with dpg.group(horizontal=True):  # row of buttons
                        for j in range(columns):
                            if i + j >= len(files_in_folder):
                                break
                            rel_path, full_path = files_in_folder[i + j]
                            tex_tag = "tex_" + rel_path.replace(os.sep, "_")
                            key = os.path.splitext(os.path.basename(rel_path))[0]

                            button_tag = dpg.add_image_button(
                                tex_tag,
                                width=thumb_size,
                                height=thumb_size,
                                callback=on_image_click,
                                user_data=(key, True, enabled_theme, disabled_theme)
                            )
                            dpg.bind_item_theme(button_tag, enabled_theme)

                            with dpg.tooltip(parent=button_tag):
                                dpg.add_text(rel_path)

                            button_states[key] = (True, enabled_theme, disabled_theme)
                    print("[UI] Added button with toggle for:", rel_path)

def resize_main_window(sender, app_data):
    new_width = dpg.get_viewport_width()
    new_height = dpg.get_viewport_height()
    # Resize the main window to fill the viewport
    dpg.configure_item(main_window_tag, width=new_width, height=new_height)





def main():
    folder = os.path.join(os.path.dirname(__file__), FOLDER_INPUT)
    if not os.path.isdir(folder):
        print(f"[ERROR] Folder '{FOLDER_INPUT}' not found next to the script.")
        return

    dpg.create_context()

    with dpg.file_dialog(
        directory_selector=False,
        show=False,
        callback=lambda s, a: import_tweak(a["file_path_name"]),
        tag="load_lua_dialog",
        width=500,
        height=500,
        modal=True,
        default_path=os.path.join(os.path.dirname(__file__), FOLDER_OUTPUT)
    ):
        dpg.add_file_extension("Lua files (*.lua){.lua}", color=(150, 150, 255, 255))
        dpg.add_file_extension(".*")



    width, height = 1920 // 2, 1080 // 2
    dpg.create_viewport(title="Disable Units", width=width, height=height)

    # Single top-level window filling viewport
    with dpg.window(label="Disable Units",
                    tag=main_window_tag,  # assign tag so we can resize
                    no_title_bar=True,
                    pos=(0, 0),
                    autosize=True,      # we control size manually
                    width=width,
                    height=height,
                    no_move=True):

        # Scrollable child window for image grid
        with dpg.child_window(width=-1, height=-1, autosize_x=True, autosize_y=True, border=False):
            create_image_grid(folder)  # your existing function

    dpg.set_viewport_resize_callback(resize_main_window)  # set callback AFTER window exists
    dpg.setup_dearpygui()
    dpg.show_viewport()
    print("[INFO] GUI running — close the window to exit")
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
