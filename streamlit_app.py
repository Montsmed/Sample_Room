import streamlit as st
import pandas as pd
import io
import requests
from PIL import Image
from urllib.request import urlopen

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
SHELF_COLORS = {
    "A": "#ADD8E6",  # light blue
    "B": "#90EE90",  # light green
    "C": "#FFFFE0",  # light yellow
    "D": "#F08080",  # light coral
    "E": "#EE82EE",  # violet
}

# --- Load Data ---
@st.cache_data
def load_data(uploaded_file):
    in_mem_file = io.BytesIO(uploaded_file.read())
    df = pd.read_excel(in_mem_file, engine="openpyxl")
    df = df.iloc[:, :6]
    df.columns = ["Location", "Description", "Unit", "Model", "SN/Lot", "Remark"]
    return df

st.set_page_config(page_title="Inventory Visual Manager", layout="wide")
st.title("📦 Visual Inventory Management System")

# --- Robust Image Loading from Local or GitHub ---
def load_shelf_image():
    image_path = "Sampleroom.png"
    image_url = "https://github.com/HowardChu/PyCharmMiscProject/raw/main/Sampleroom.png"
    
    try:
        # First try local file
        img = Image.open(image_path)
        w, h = img.size
        img_resized = img.resize((w // 2, h // 2))
        return img_resized
    except:
        try:
            # Fallback to GitHub URL
            img = Image.open(urlopen(image_url))
            w, h = img.size
            img_resized = img.resize((w // 2, h // 2))
            return img_resized
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

# --- Search Box ---
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
        st.dataframe(filtered_data[["Location", "Description", "Unit", "Model", "SN/Lot", "Remark"]])

# --- Interactive Shelf Grid with instant highlight ---
if "selected_layer" not in st.session_state:
    st.session_state["selected_layer"] = None

for layer_num in LAYER_ORDER:
    cols = st.columns(len(SHELF_ORDER) + 1)
    cols[0].markdown(
        f"<div style='height:60px;display:flex;align-items:center;font-weight:bold;'>Layer {layer_num}</div>",
        unsafe_allow_html=True
    )
    for idx, shelf in enumerate(SHELF_ORDER):
        if layer_num in SHELVES[shelf]:
            layer_label = f"{shelf}{layer_num}"
            color = SHELF_COLORS[shelf]
            highlight = (st.session_state["selected_layer"] == layer_label)
            btn_style = f"""
                height:60px;width:100px;font-size:1.5em;font-weight:bold;
                background-color:{'#FFD700' if highlight else color};
                border:3px solid {'#FFD700' if highlight else '#222'};
                border-radius:10px;
                margin:4px 0 4px 0;
            """
            with cols[idx + 1]:
                st.markdown(
                    f"<div style='{btn_style}'>{layer_label}</div>",
                    unsafe_allow_html=True
                )
                if st.button(f"Select {layer_label}", key=f"btn_{layer_label}"):
                    st.session_state["selected_layer"] = layer_label
                    st.rerun()  # Use st.rerun() for instant update
        else:
            cols[idx + 1].markdown("")

selected_layer = st.session_state["selected_layer"]

# --- Show and Edit Items in Selected Layer ---
if selected_layer:
    st.markdown(f"## Items in **{selected_layer}**")
    layer_data = data[data["Location"] == selected_layer].reset_index(drop=True)
    if layer_data.empty:
        st.info("No items in this layer. You can add new items below.")
        # Create an empty DataFrame with the same columns
        empty_df = pd.DataFrame(columns=data.columns)
        edited_data = st.data_editor(
            empty_df,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{selected_layer}"
        )
    else:
        edited_data = st.data_editor(
            layer_data,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{selected_layer}"
        )

    # --- Persist changes and offer download ---
    if st.button("Save Changes"):
        # For empty shelves, set the Location for new rows
        if layer_data.empty and not edited_data.empty:
            edited_data["Location"] = selected_layer
            data = pd.concat([data, edited_data], ignore_index=True)
        else:
            data.update(edited_data)
        st.success("Changes saved! You can now download the updated Excel file below.")

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

        # --- Persist changes and offer download ---
        if st.button("Save Changes"):
            data.update(edited_data)
            st.success("Changes saved! You can now download the updated Excel file below.")

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
