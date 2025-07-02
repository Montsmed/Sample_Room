import streamlit as st
import pandas as pd
import io
import requests
from PIL import Image
from io import BytesIO
import base64

# --- Shelf and Layer Definitions ---
SHELVES = {
    "A": [1, 2, 3],
    "B": [1, 2, 3],
    "C": [1, 2, 3, 4],
    "D": [1, 2, 3, 4],
    "E": [4],  # Only layer 4 for E
}
SHELF_ORDER = ["A", "B", "C", "D", "E"]
LAYER_ORDER = [4, 3, 2, 1]  # Top to bottom

# Color schemes
LIGHT_SHELF_COLORS = {
    "A": "#ADD8E6",
    "B": "#90EE90",
    "C": "#FFFFE0",
    "D": "#F08080",
    "E": "#EE82EE",
}
LIGHT_FONT_COLOR = "#222"

DARK_SHELF_COLORS = {
    "A": "#22577A",
    "B": "#38A3A5",
    "C": "#57CC99",
    "D": "#F3722C",
    "E": "#C44536",
}
DARK_FONT_COLOR = "#F3F3F3"
LIGHT_GREY_DARK_MODE = '#D3D3D3'

@st.cache_data
def load_data(uploaded_file):
    in_mem_file = io.BytesIO(uploaded_file.read())
    df = pd.read_excel(in_mem_file, engine="openpyxl")
    df = df.iloc[:, :7]
    df.columns = ["Location", "Description", "Unit", "Model", "SN/Lot", "Remark", "Image_URL"]
    return df

st.set_page_config(page_title="Inventory Visual Manager", layout="wide")
st.title("📦 Visual Inventory Management System")

# --- Shelf overview image ---
def load_shelf_image():
    image_path = "Sampleroom.png"
    image_url = "https://github.com/Montsmed/Sample_Room/raw/main/Sampleroom.png"
    try:
        img = Image.open(image_path)
        w, h = img.size
        return img.resize((w // 2, h // 2))
    except:
        try:
            img = Image.open(requests.get(image_url, stream=True).raw)
            w, h = img.size
            return img.resize((w // 2, h // 2))
        except:
            return None

img_resized = load_shelf_image()
if img_resized:
    st.image(img_resized, caption="Shelf Image", use_container_width=False)
else:
    st.info("Shelf image not available")

uploaded_file = st.file_uploader("Upload your Excel Inventory File", type=["xlsx"])
if not uploaded_file:
    st.info("Please upload your Excel file to begin.")
    st.stop()

uploaded_file.seek(0)
data = load_data(uploaded_file)

# --- Search ---
search_query = st.text_input("🔎 Search items by Description, Unit, Model, or SN/Lot (partial match):")

if search_query:
    filtered_data = data[
        data["Description"].astype(str).str.contains(search_query, case=False, na=False) |
        data["Unit"].astype(str).str.contains(search_query, case=False, na=False) |
        data["Model"].astype(str).str.contains(search_query, case=False, na=False) |
        data["SN/Lot"].astype(str).str.contains(search_query, case=False, na=False)
    ]
    if filtered_data.empty:
        st.info("No items found matching your search.")
    else:
        st.markdown(f"### Search Results for '{search_query}':")
        st.dataframe(filtered_data[["Location", "Description", "Unit", "Model", "SN/Lot", "Remark", "Image_URL"]])

st.markdown("### Click a shelf layer to view/edit its items:")

# --- Detect theme and set color scheme ---
def get_color_scheme():
    try:
        theme_base = st.get_option("theme.base")
    except Exception:
        theme_base = "Light"
    if theme_base and theme_base.lower() == "dark":
        return DARK_SHELF_COLORS, DARK_FONT_COLOR
    else:
        return LIGHT_SHELF_COLORS, LIGHT_FONT_COLOR

def get_layer_label_color():
    try:
        theme_base = st.get_option("theme.base")
    except Exception:
        theme_base = "Light"
    if theme_base and theme_base.lower() == "dark":
        return LIGHT_GREY_DARK_MODE
    else:
        return "#222"

SHELF_COLORS, FONT_COLOR = get_color_scheme()
LAYER_LABEL_COLOR = get_layer_label_color()

# --- Interactive Shelf Grid with instant highlight and edit persistence ---
if "selected_layer" not in st.session_state:
    st.session_state["selected_layer"] = None
if "last_selected_layer" not in st.session_state:
    st.session_state["last_selected_layer"] = None

for layer_num in LAYER_ORDER:
    cols = st.columns(len(SHELF_ORDER) + 1)
    with cols[0]:
        st.markdown(
            f"""
            <div style='height:60px;width:100%;display:flex;align-items:center;justify-content:center;font-weight:bold;color:{LAYER_LABEL_COLOR};font-size:1.25em;text-align:center;background:transparent;border-radius:10px;'>
                Layer {layer_num}
            </div>
            """,
            unsafe_allow_html=True
        )
    for idx, shelf in enumerate(SHELF_ORDER):
        if layer_num in SHELVES[shelf]:
            layer_label = f"{shelf}{layer_num}"
            color = SHELF_COLORS[shelf]
            highlight = (st.session_state["selected_layer"] == layer_label)
            box_bg = "#FFD700" if highlight else color
            box_font = "#222" if highlight else FONT_COLOR
            btn_style = f"""
                height:60px;width:100px;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:1.5em;font-weight:bold;
                background-color:{box_bg};
                color:{box_font};
                border:3px solid {'#FFD700' if highlight else '#444'};
                border-radius:10px;
                margin:4px 0 4px 0;
                text-align:center;
            """
            with cols[idx + 1]:
                st.markdown(
                    f"<div style='{btn_style}'>{layer_label}</div>",
                    unsafe_allow_html=True
                )
                if st.button(f"Select {layer_label}", key=f"btn_{layer_label}"):
                    # Save current edits before switching
                    if st.session_state["selected_layer"]:
                        prev_layer = st.session_state["selected_layer"]
                        persist_key = f"persisted_{prev_layer}"
                        editor_key = f"editor_{prev_layer}"
                        if editor_key in st.session_state:
                            # Always ensure DataFrame
                            val = st.session_state[editor_key]
                                if isinstance(val, pd.DataFrame):
                                    st.session_state[persist_key] = val
                                elif isinstance(val, list):
                                    # If it's a list of dicts, convert
                                    if len(val) > 0 and isinstance(val[0], dict):
                                        st.session_state[persist_key] = pd.DataFrame(val)
                                    else:
                                        # Empty or invalid, create empty DataFrame with correct columns
                                        st.session_state[persist_key] = pd.DataFrame(columns=data.columns)
                                elif isinstance(val, dict):
                                    # If it's a dict of columns, convert
                                    st.session_state[persist_key] = pd.DataFrame(val)
                                else:
                                    # Fallback: create empty DataFrame
                                    st.session_state[persist_key] = pd.DataFrame(columns=data.columns)
                    st.session_state["last_selected_layer"] = st.session_state["selected_layer"]
                    st.session_state["selected_layer"] = layer_label
                    st.rerun()
        else:
            cols[idx + 1].markdown("")

selected_layer = st.session_state["selected_layer"]

# --- Show and Edit Items in Selected Layer ---
if selected_layer:
    layer_data = data[data["Location"] == selected_layer].reset_index(drop=True)
    st.markdown(f"## Items in **{selected_layer}**")
    
    if layer_data.empty:
        st.info("No items in this layer. Add new items below:")
        editor_initial = pd.DataFrame(columns=data.columns)
    else:
        editor_initial = layer_data.copy()

    persist_key = f"persisted_{selected_layer}"
    editor_key = f"editor_{selected_layer}"

    # --- Robust DataFrame check for editor_value ---
    if persist_key in st.session_state:
        editor_value = st.session_state[persist_key]
        if not isinstance(editor_value, pd.DataFrame):
            editor_value = pd.DataFrame(editor_value)
    else:
        editor_value = editor_initial

    edited_data = st.data_editor(
        editor_value,
        num_rows="dynamic",
        use_container_width=True,
        key=editor_key
    )

    # --- Gallery: Multiple images per row, fixed width 200px ---
    st.markdown("### Images in this shelf layer:")
    images_per_row = 5
    PLACEHOLDER_IMAGE = "https://github.com/Montsmed/Sample_Room/raw/main/No_Image.jpg"
    img_rows = [
        edited_data.iloc[i:i+images_per_row]
        for i in range(0, len(edited_data), images_per_row)
    ]
    for img_row in img_rows:
        cols = st.columns(len(img_row))
        for col, (_, row) in zip(cols, img_row.iterrows()):
            image_url = str(row["Image_URL"]).strip()
            if not image_url or image_url.lower() == "nan":
                image_url = PLACEHOLDER_IMAGE
            try:
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content))
                w, h = img.size
                new_width = 200
                new_height = int(h * (new_width / w))
                img_resized = img.resize((new_width, new_height))
                buf = BytesIO()
                img_resized.save(buf, format="PNG")
                img_base64 = base64.b64encode(buf.getvalue()).decode()
                img_html = f"""
                    <div style='text-align:center;'>
                        <img src='data:image/png;base64,{img_base64}' width='200'/><br>
                        <div style='font-family: Arial, sans-serif; font-size: 1.1em; color:{FONT_COLOR};'>
                            <b>{row['Description']}</b><br>
                            Unit: <b>{row['Unit']}</b>
                        </div>
                    </div>
                """
                with col:
                    st.markdown(img_html, unsafe_allow_html=True)
            except Exception:
                with col:
                    st.markdown(
                        f"""
                        <div style='text-align:center;'>
                            <img src='{PLACEHOLDER_IMAGE}' width='200'/><br>
                            <div style='font-family: Arial, sans-serif; font-size: 1.1em; color:{FONT_COLOR};'>
                                <b>{row['Description']}</b><br>
                                Unit: <b>{row['Unit']}</b>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    # --- Save Logic ---
    if st.button("Save Changes", key=f"save_{selected_layer}"):
        st.session_state[persist_key] = edited_data
        data = data[data["Location"] != selected_layer]
        if not edited_data.empty:
            edited_data["Location"] = selected_layer
            data = pd.concat([data, edited_data], ignore_index=True)
            st.success(f"Saved {len(edited_data)} items for {selected_layer}!")
        else:
            st.success("No items to save for this shelf.")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            data.to_excel(writer, index=False)
        output.seek(0)
        st.download_button(
            label="Download Updated Excel File",
            data=output,
            file_name="updated_inventory.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Click a shelf layer above to view its items.")
