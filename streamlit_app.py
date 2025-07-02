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

def get_all_edited_data():
    # Aggregate all temp edits from session state
    edited_layers = []
    for shelf in SHELF_ORDER:
        for layer in SHELVES[shelf]:
            layer_label = f"{shelf}{layer}"
            key = f"data_{layer_label}"
            if key in st.session_state:
                df = st.session_state[key]
                if not df.empty:
                    df = df.copy()
                    df["Location"] = layer_label
                    edited_layers.append(df)
    if edited_layers:
        return pd.concat(edited_layers, ignore_index=True)
    else:
        return pd.DataFrame(columns=["Location", "Description", "Unit", "Model", "SN/Lot", "Remark", "Image_URL"])

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

# --- Initialize session state for all layers with data from Excel ---
for shelf in SHELF_ORDER:
    for layer in SHELVES[shelf]:
        layer_label = f"{shelf}{layer}"
        key = f"data_{layer_label}"
        if key not in st.session_state:
            layer_data = data[data["Location"] == layer_label].reset_index(drop=True)
            st.session_state[key] = layer_data.copy()

# --- Search ---
search_query = st.text_input("🔎 Search items by Description, Unit, Model, or SN/Lot (partial match):")
if search_query:
    all_data = get_all_edited_data()
    filtered_data = all_data[
        all_data["Description"].astype(str).str.contains(search_query, case=False, na=False) |
        all_data["Unit"].astype(str).str.contains(search_query, case=False, na=False) |
        all_data["Model"].astype(str).str.contains(search_query, case=False, na=False) |
        all_data["SN/Lot"].astype(str).str.contains(search_query, case=False, na=False)
    ]
    if filtered_data.empty:
        st.info("No items found matching your search.")
    else:
        st.markdown(f"### Search Results for '{search_query}':")
        st.dataframe(filtered_data[["Location", "Description", "Unit", "Model", "SN/Lot", "Remark", "Image_URL"]])

st.markdown("### Click a shelf layer to view/edit its items:")

# --- Layer selection state ---
if "selected_layer" not in st.session_state:
    # Default to first available layer
    st.session_state["selected_layer"] = SHELF_ORDER[0] + str(SHELVES[SHELF_ORDER[0]][0])

# --- Layer selection grid ---
selected_layer = st.session_state["selected_layer"]
layer_buttons = {}

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
            highlight = (selected_layer == layer_label)
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
                # Store button references for later use
                layer_buttons[layer_label] = st.form_submit_button if highlight else st.button
                if st.button(f"Select {layer_label}", key=f"btn_{layer_label}"):
                    # Temp save current edits before switching
                    st.session_state[f"data_{selected_layer}"] = st.session_state.get("edited_df", st.session_state[f"data_{selected_layer}"])
                    st.session_state["selected_layer"] = layer_label
                    st.session_state["edited_df"] = st.session_state[f"data_{layer_label}"].copy()
                    st.rerun()
        else:
            cols[idx + 1].markdown("")

# --- Editor form for the selected layer ---
layer_key = f"data_{st.session_state['selected_layer']}"
if "edited_df" not in st.session_state:
    st.session_state["edited_df"] = st.session_state[layer_key].copy()

with st.form("editor_form"):
    st.markdown(f"## Items in **{st.session_state['selected_layer']}**")
    edited_df = st.data_editor(
        st.session_state["edited_df"],
        num_rows="dynamic",
        use_container_width=True,
        key=f"editor_{st.session_state['selected_layer']}"
    )
    save = st.form_submit_button("Temp Save (this layer)")
    if save:
        st.session_state["edited_df"] = ensure_dataframe(edited_df, data.columns)
        st.session_state[layer_key] = st.session_state["edited_df"].copy()
        st.success(f"Temp saved for {st.session_state['selected_layer']}!")

# --- Gallery: Multiple images per row, fixed width 200px ---
st.markdown("### Images in this shelf layer:")
images_per_row = 5
PLACEHOLDER_IMAGE = "https://github.com/Montsmed/Sample_Room/raw/main/No_Image.jpg"
img_rows = [
    st.session_state["edited_df"].iloc[i:i+images_per_row]
    for i in range(0, len(st.session_state["edited_df"]), images_per_row)
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

# --- GLOBAL DOWNLOAD BUTTON ---
st.markdown("---")
st.markdown("### 📥 Download Inventory Including All Temp-Saved Edits")

all_data = get_all_edited_data()
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    all_data.to_excel(writer, index=False)
output.seek(0)

st.download_button(
    label="Download All Inventory Data (with Temp-Saved Edits)",
    data=output,
    file_name="inventory_with_all_edits.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
