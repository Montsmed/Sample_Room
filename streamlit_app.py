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
    "E": [4],
}
SHELF_ORDER = ["A", "B", "C", "D", "E"]
LAYER_ORDER = [4, 3, 2, 1]

LIGHT_SHELF_COLORS = {"A": "#ADD8E6", "B": "#90EE90", "C": "#FFFFE0", "D": "#F08080", "E": "#EE82EE"}
DARK_SHELF_COLORS = {"A": "#22577A", "B": "#38A3A5", "C": "#57CC99", "D": "#F3722C", "E": "#C44536"}
LIGHT_FONT_COLOR = "#222"
DARK_FONT_COLOR = "#F3F3F3"
LIGHT_GREY_DARK_MODE = '#D3D3D3'

def ensure_dataframe(val, columns):
    if isinstance(val, pd.DataFrame):
        return val
    if isinstance(val, list):
        if len(val) == 0:
            return pd.DataFrame(columns=columns)
        if all(isinstance(x, dict) for x in val):
            return pd.DataFrame(val)
        else:
            return pd.DataFrame(columns=columns)
    if isinstance(val, dict):
        lengths = [len(v) for v in val.values() if hasattr(v, '__len__')]
        if len(lengths) > 0 and len(set(lengths)) == 1:
            try:
                return pd.DataFrame(val)
            except Exception:
                return pd.DataFrame(columns=columns)
        else:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

@st.cache_data
def load_data(uploaded_file):
    in_mem_file = io.BytesIO(uploaded_file.read())
    df = pd.read_excel(in_mem_file, engine="openpyxl")
    df = df.iloc[:, :7]
    df.columns = ["Location", "Description", "Unit", "Model", "SN/Lot", "Remark", "Image_URL"]
    return df

st.set_page_config(page_title="Inventory Visual Manager", layout="wide")
st.title("📦 Visual Inventory Management System")

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

# --- Load Data ---
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

# --- Layer/Shelf selection logic with on_change callback ---
def save_edits_before_switch():
    prev_layer = st.session_state.get("selected_layer")
    if prev_layer:
        edited_key = f"edited_df_{prev_layer}"
        original_key = f"original_df_{prev_layer}"
        if edited_key in st.session_state:
            st.session_state[original_key] = st.session_state[edited_key].copy()

layer_labels = [f"{shelf}{layer}" for shelf in SHELF_ORDER for layer in LAYER_ORDER if layer in SHELVES[shelf]]
if "selected_layer" not in st.session_state:
    st.session_state["selected_layer"] = layer_labels[0]

selected_layer = st.selectbox(
    "Select Shelf Layer",
    options=layer_labels,
    index=layer_labels.index(st.session_state["selected_layer"]),
    key="layer_selector",
    on_change=save_edits_before_switch
)
st.session_state["selected_layer"] = selected_layer

# --- Editor initialization per shelf/layer ---
original_key = f"original_df_{selected_layer}"
edited_key = f"edited_df_{selected_layer}"

if original_key not in st.session_state:
    # Initialize from main data
    layer_data = data[data["Location"] == selected_layer].reset_index(drop=True)
    st.session_state[original_key] = layer_data.copy()
if edited_key not in st.session_state:
    st.session_state[edited_key] = st.session_state[original_key].copy()

# --- Data Editor ---
edited_df = st.data_editor(
    st.session_state[edited_key],
    num_rows="dynamic",
    use_container_width=True,
    key=edited_key
)
st.session_state[edited_key] = ensure_dataframe(edited_df, data.columns)

# --- Gallery ---
st.markdown("### Images in this shelf layer:")
images_per_row = 5
PLACEHOLDER_IMAGE = "https://github.com/Montsmed/Sample_Room/raw/main/No_Image.jpg"
img_rows = [
    st.session_state[edited_key].iloc[i:i+images_per_row]
    for i in range(0, len(st.session_state[edited_key]), images_per_row)
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
    # Write back to main DataFrame
    df_to_save = st.session_state[edited_key].copy()
    df_to_save["Location"] = selected_layer
    data = data[data["Location"] != selected_layer]
    if not df_to_save.empty:
        data = pd.concat([data, df_to_save], ignore_index=True)
        st.session_state[original_key] = df_to_save.copy()
        st.session_state[edited_key] = df_to_save.copy()
        st.success(f"Saved {len(df_to_save)} items for {selected_layer}!")
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
