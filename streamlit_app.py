import streamlit as st
import pandas as pd
import io
import requests
from PIL import Image
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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

@st.cache_data
def load_data(uploaded_file):
    in_mem_file = io.BytesIO(uploaded_file.read())
    df = pd.read_excel(in_mem_file, engine="openpyxl")
    df = df.iloc[:, :7]
    df.columns = ["Location", "Description", "Unit", "Model", "SN/Lot", "Remark", "Image_URL"]
    return df

def configure_aggrid_options(df):
    """Configure AgGrid options for inventory data editing"""
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # Configure columns
    gb.configure_column("Location", editable=False, width=100)  # Location shouldn't be edited directly
    gb.configure_column("Description", editable=True, width=200)
    gb.configure_column("Unit", editable=True, width=100)
    gb.configure_column("Model", editable=True, width=150)
    gb.configure_column("SN/Lot", editable=True, width=150, header_name="SN/Lot")
    gb.configure_column("Remark", editable=True, width=200)
    gb.configure_column("Image_URL", editable=True, width=300, header_name="Image URL")
    
    # Configure grid options
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        filterable=True
    )
    
    # Enable pagination and selection
    gb.configure_pagination(enabled=True, paginationPageSize=10)
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    
    # Configure side panel for filters
    gb.configure_side_bar(filters_panel=True, defaultToolPanel='filters')
    
    return gb.build()

st.set_page_config(page_title="Inventory Visual Manager", layout="wide")
st.title("📦 Visual Inventory Management System")

# Initialize session state for data persistence
if "inventory_data" not in st.session_state:
    st.session_state["inventory_data"] = None

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

# Load data and store in session state
uploaded_file.seek(0)
if st.session_state["inventory_data"] is None:
    st.session_state["inventory_data"] = load_data(uploaded_file)

data = st.session_state["inventory_data"]

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
        
        # Configure AgGrid for search results
        search_grid_options = configure_aggrid_options(filtered_data)
        search_grid_response = AgGrid(
            filtered_data,
            gridOptions=search_grid_options,
            height=300,
            width='100%',
            theme='alpine',
            update_mode=GridUpdateMode.VALUE_CHANGED,
            allow_unsafe_jscode=True,
            key="search_grid"
        )

st.markdown("### Click a shelf layer to view/edit its items:")

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
        # Create empty dataframe with proper structure for new items
        empty_df = pd.DataFrame({
            "Location": [selected_layer],
            "Description": [""],
            "Unit": [""],
            "Model": [""],
            "SN/Lot": [""],
            "Remark": [""],
            "Image_URL": [""]
        })
        
        # Configure AgGrid for empty layer
        empty_grid_options = configure_aggrid_options(empty_df)
        grid_response = AgGrid(
            empty_df,
            gridOptions=empty_grid_options,
            height=200,
            width='100%',
            theme='alpine',
            update_mode=GridUpdateMode.VALUE_CHANGED,
            allow_unsafe_jscode=True,
            key=f"empty_grid_{selected_layer}"
        )
        edited_data = grid_response['data']
    else:
        # Configure AgGrid for existing data
        layer_grid_options = configure_aggrid_options(layer_data)
        
        st.markdown("**Features available:**")
        st.markdown("- ✏️ **Edit cells directly** by double-clicking")
        st.markdown("- 🔍 **Filter and sort** using column headers")
        st.markdown("- ☑️ **Select multiple rows** using checkboxes")
        st.markdown("- 📄 **Pagination** for large datasets")
        
        grid_response = AgGrid(
            layer_data,
            gridOptions=layer_grid_options,
            height=400,
            width='100%',
            theme='alpine',
            update_mode=GridUpdateMode.VALUE_CHANGED,
            allow_unsafe_jscode=True,
            key=f"layer_grid_{selected_layer}",
            fit_columns_on_grid_load=True
        )
        
        edited_data = grid_response['data']
        selected_rows = grid_response['selected_rows']
        
        # Show selected rows info
        if selected_rows:
            st.info(f"Selected {len(selected_rows)} row(s)")

    # --- Add New Item Button ---
    if st.button("➕ Add New Item", key=f"add_item_{selected_layer}"):
        new_row = pd.DataFrame({
            "Location": [selected_layer],
            "Description": ["New Item"],
            "Unit": [""],
            "Model": [""],
            "SN/Lot": [""],
            "Remark": [""],
            "Image_URL": [""]
        })
        st.session_state["inventory_data"] = pd.concat([st.session_state["inventory_data"], new_row], ignore_index=True)
        st.rerun()

    # --- Gallery: Multiple images per row, fixed width 200px ---
    if not layer_data.empty:
        st.markdown("### 🖼️ Image Gallery for this shelf layer:")
        images_per_row = 5  # Number of images per row
        PLACEHOLDER_IMAGE = "https://github.com/Montsmed/Sample_Room/raw/main/No_Image.jpg"
        
        img_rows = [
            layer_data.iloc[i:i+images_per_row]
            for i in range(0, len(layer_data), images_per_row)
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
                    with col:
                        st.image(img_resized, use_container_width=False)
                        st.markdown(
                            f"""
                            <div style='text-align:center; font-family: Arial, sans-serif; font-size: 1.1em;'>
                                <b>{row['Description']}</b><br>
                                Unit: <b>{row['Unit']}</b>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                except Exception:
                    with col:
                        st.image(PLACEHOLDER_IMAGE, use_container_width=False)
                        st.markdown(
                            f"""
                            <div style='text-align:center; font-family: Arial, sans-serif; font-size: 1.1em;'>
                                <b>{row['Description']}</b><br>
                                Unit: <b>{row['Unit']}</b>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

    # --- Save Logic ---
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("💾 Save Changes", key=f"save_{selected_layer}"):
            # Update the session state data with edited data
            if not edited_data.empty:
                # Remove existing data for this location
                st.session_state["inventory_data"] = st.session_state["inventory_data"][
                    st.session_state["inventory_data"]["Location"] != selected_layer
                ]
                
                # Add updated data
                edited_data["Location"] = selected_layer  # Ensure location is set correctly
                st.session_state["inventory_data"] = pd.concat([
                    st.session_state["inventory_data"], 
                    edited_data
                ], ignore_index=True)
                
                st.success(f"✅ Changes saved for {selected_layer}!")
                st.rerun()

    with col2:
        # --- Download Updated File ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state["inventory_data"].to_excel(writer, index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download Updated Excel File",
            data=output,
            file_name="updated_inventory.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_{selected_layer}"
        )

else:
    st.info("👆 Click a shelf layer above to view its items.")

# --- Summary Statistics ---
st.markdown("---")
st.markdown("### 📊 Inventory Summary")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Items", len(st.session_state["inventory_data"]))

with col2:
    unique_locations = st.session_state["inventory_data"]["Location"].nunique()
    st.metric("Active Locations", unique_locations)

with col3:
    unique_units = st.session_state["inventory_data"]["Unit"].nunique()
    st.metric("Unique Units", unique_units)

with col4:
    items_with_images = len(st.session_state["inventory_data"][
        (st.session_state["inventory_data"]["Image_URL"].notna()) & 
        (st.session_state["inventory_data"]["Image_URL"] != "")
    ])
    st.metric("Items with Images", items_with_images)
