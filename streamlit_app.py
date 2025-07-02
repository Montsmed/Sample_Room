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
    # Read columns A-G (7 columns)
    df = df.iloc[:, :7]
    df.columns = ["Location", "Description", "Unit", "Model", "SN/Lot", "Remark", "Image_URL"]
    return df

st.set_page_config(page_title="Inventory Visual Manager", layout="wide")
st.title("📦 Visual Inventory Management System")

# --- Image Loading ---
def load_shelf_image():
    image_path = "Sampleroom.png"
    image_url = "https://github.com/Montsmed/Sample_Room/raw/main/Sampleroom.png"
    
    try:
        img = Image.open(image_path)
        w, h = img.size
        return img.resize((w // 2, h // 2))
    except:
        try:
            img = Image.open(urlopen(image_url))
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

# --- Search Functionality ---
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

st.markdown("### Click a shelf layer to view/edit its items:")

# --- Interactive Shelf Grid ---
if "selected_layer" not in st.session_state:
    st.session_state["selected_layer"] = None
if "selected_row" not in st.session_state:
    st.session_state["selected_row"] = None

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
                    st.session_state["selected_row"] = None  # Reset row selection
                    st.rerun()
        else:
            cols[idx + 1].markdown("")

selected_layer = st.session_state["selected_layer"]

# --- Show and Edit Items in Selected Layer ---
if selected_layer:
    st.markdown(f"## Items in **{selected_layer}**")
    layer_data = data[data["Location"] == selected_layer].reset_index(drop=True)
    
    if layer_data.empty:
        st.info("No items in this layer. Add new items below:")
        empty_df = pd.DataFrame(columns=data.columns)
        edited_data = st.data_editor(
            empty_df,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{selected_layer}"
        )
    else:
        # Display clickable table
        st.markdown("**Click on a description to view its image**")
        
        # Create a copy for display (to show clickable descriptions)
        display_df = layer_data.copy()
        display_df["Description"] = display_df["Description"].apply(
            lambda x: f"<a href='#' onclick='return false;'>{x}</a>"
        )
        
        # Display as HTML to make descriptions clickable
        st.markdown(
            display_df[["Description", "Unit", "Model", "SN/Lot", "Remark"]].to_html(escape=False, index=False),
            unsafe_allow_html=True
        )
        
        # Create a row selection widget
        row_idx = st.selectbox(
            "Select an item to view its image:",
            options=range(len(layer_data)),
            format_func=lambda x: layer_data.iloc[x]["Description"],
            key=f"row_select_{selected_layer}"
        )
        
        # Store selected row in session state
        if row_idx is not None:
            st.session_state["selected_row"] = row_idx
            
        # Show image for selected row
        if st.session_state["selected_row"] is not None:
            row = layer_data.iloc[st.session_state["selected_row"]]
            image_url = str(row["Image_URL"]).strip()
            st.write("Debug: Image_URL value is", image_url)  # For debugging
            if image_url and image_url.lower() != "nan":
                try:
                    st.image(image_url, caption=f"Image for {row['Description']}")
            except Exception as e:
                st.error(f"Could not load image: {e}")
            else:
                st.info("No image available for this item.")
        
        # Data editor for editing
        edited_data = st.data_editor(
            layer_data.drop(columns=["Image_URL"]),  # Hide image URL in editor
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{selected_layer}"
        )

    # --- Save Logic ---
    if st.button("Save Changes"):
        if layer_data.empty and not edited_data.empty:
            edited_data["Location"] = selected_layer
            data = pd.concat([data, edited_data], ignore_index=True)
            st.success(f"Added {len(edited_data)} new items to {selected_layer}!")
        else:
            data.update(edited_data)
            st.success("Changes saved!")
        
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
