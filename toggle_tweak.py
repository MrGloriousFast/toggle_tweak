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


def save_output():
  folder_out = os.path.join(os.path.dirname(__file__), FOLDER_OUTPUT)
  os.makedirs(folder_out, exist_ok=True)

  list_file_path = os.path.join(folder_out, "lua_json.txt")
  encoded_file_path = os.path.join(folder_out, "paste_command.txt")

  # Write lua_json
  with open(list_file_path, "w") as f:
    f.write("{\n")
    for key, (state, _, _) in button_states.items():
      if not state:  # only write if toggled red
        f.write("  " + key + " = { maxThisUnit = 0 },\n")
    f.write("}\n")
  print("[INFO] Wrote " + list_file_path)

  # Read list.txt and encode to base64
  with open(list_file_path, "rb") as f:
    encoded_data = base64.b64encode(f.read()).decode("ascii")

  # Remove padding (=) and prepend command
    encoded_data = "!bset tweakunits " + encoded_data.replace("=", "")


  # Write encoded base64 string to paste_command.txt
  with open(encoded_file_path, "w") as f:
    f.write(encoded_data + "\n")
  print("[INFO] Wrote " + encoded_file_path)


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


def create_image_grid(folder, columns=8, thumb_size=64):
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
        dpg.add_button(label="generate LUA", callback=save_output)

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

    width, height = 1920 // 2, 1080 // 2
    dpg.create_viewport(title="Disable Units", width=width, height=height)

    # Single top-level window filling viewport
    with dpg.window(label="Disable Units",
                    tag=main_window_tag,  # assign tag so we can resize
                    no_title_bar=True,
                    pos=(0, 0),
                    autosize=False,      # we control size manually
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
