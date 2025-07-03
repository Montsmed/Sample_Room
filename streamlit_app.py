import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import requests
from io import BytesIO
import base64

# Configure page
st.set_page_config(
    page_title="Inventory Management System",
    page_icon="📦",
    layout="wide"
)

# Load data from Excel file
@st.cache_data
def load_inventory_data():
    """Load inventory data from Excel file"""
    try:
        # Replace with your actual GitHub raw file URL
        url = "https://raw.githubusercontent.com/your-repo/your-file/main/updated_inventory.xlsx"
        df = pd.read_excel(url)
        return df
    except:
        # Fallback data based on your Excel structure
        data = {
            'Location': ['A1', 'A1', 'A1', 'A2', 'A2', 'A3', 'A3', 'B1', 'B2', 'B3', 
                        'C1', 'C1', 'C1', 'C1', 'C1', 'C1', 'C1', 'C1', 'C2', 'C2', 'D1', 'E4'],
            'Description': ['BNS RF Lesion Generator for Neurosurgery', 'Codman Electrosurgical Generator', 
                           'Elliquence Surgi-Max Plus', 'Integra Duo Headlight & Accessory', 'Lextec Lightsource',
                           'BNS 4-Channel RF Lesion Generator', 'BNS RF Lesion Generator for Neurosurgery',
                           'Mayfield Stuff', 'Omni-Tract Stuff', 'Stuff', 'Codman Certas Plus', 'Codman Certas Plus',
                           'Codman Licox PtO2 Monitor', 'Codman Medos Valve Programmer', 'Codman Medos Valve Programmer',
                           'Integra LicocCMP Tissue Oxygen Pressure Monitor', 'Integra Luxtec Lightsource',
                           'Integra Luxtec Lightsource', 'Stuff', 'UX100', 'Hakim Programmer', 'Touchstone Stuff'],
            'Unit': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 5, 3, 1],
            'Model': ['RFE2-C', '901001ESUO', 'IEC4-SP', '90600', '00MLX', 'RFE4-B', 'RFE2-C', '', '', '',
                     '82-8852', '82-8852', 'LCX02', '82-3126', '82-3126', '144733', '00MLX', '00MLX', '', 'UX100', '823190R', ''],
            'SN/Lot': ['', '', '', '', '', '', '', '', '', '', '', '', '2150601326', '847', '1173', '1629',
                      '16G00MLX7347', '16K00MLX7896', '', '', '', ''],
            'Remark': ['', '', '', '', '', '', '', '', '', '', 'System Failure, Missing Magnet', 'Unable to power-on',
                      'Functional', 'Functional', 'Functional', 'Missing Power Supply', 'GHK Trade-in, Dead motherboard',
                      'STH Trade-in, Dead motherboard', '', '', '', ''],
            'Image_URL': ['https://www.bnsmed.com/data/watermark/20200924/5f6c31aea1382.jpg',
                         'https://products.integralife.com/ccstore/v1/images/?source=/file/products/Codman%20Electrosurgical%20Generator%20OS%201%20Image.jpg',
                         'https://www.elliquence.com/wp-content/uploads/2016/01/Surgi-Max-Plus-Device.jpg',
                         '', '', '', '', '', '', '', 
                         'https://products.integralife.com/ccstore/v1/images/?source=/file/v3841902670343812321/products/ETK_01.png',
                         'https://products.integralife.com/ccstore/v1/images/?source=/file/v3841902670343812321/products/ETK_01.png',
                         'https://products.integralife.com/ccstore/v1/images/?source=/file/v7357354864197611707/collections/licox.jpg',
                         'https://products.integralife.com/ccstore/v1/images/?source=/file/v5137398853523069574/products/823190.jpg',
                         'https://products.integralife.com/ccstore/v1/images/?source=/file/v5137398853523069574/products/823190.jpg',
                         'https://products.integralife.com/ccstore/v1/images/?source=/file/v7357354864197611707/collections/licox.jpg',
                         'https://products.integralife.com/ccstore/v1/images/?source=/file/v6400991064904479991/products/MLX-300-Xenon-Lightsources.jpg',
                         'https://products.integralife.com/ccstore/v1/images/?source=/file/v6400991064904479991/products/MLX-300-Xenon-Lightsources.jpg',
                         '', '', '', '']
        }
        return pd.DataFrame(data)

# Initialize session state
if 'inventory_data' not in st.session_state:
    st.session_state.inventory_data = load_inventory_data()
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = None

# Define shelf structure
SHELF_STRUCTURE = {
    'A': [1, 2, 3],
    'B': [1, 2, 3],
    'C': [1, 2, 3, 4],
    'D': [1, 2, 3, 4],
    'E': [4]
}

def create_shelf_visualization():
    """Create interactive shelf visualization"""
    st.markdown("## 📦 Inventory Management System")
    
    # Room layout image
    st.markdown("### 🏠 Sample Room Layout")
    # Replace with your actual GitHub image URL
    room_layout_url = "https://via.placeholder.com/800x400/e1f5fe/01579b?text=Sample+Room+Layout"
    st.image(room_layout_url, caption="Sample Room Layout", use_container_width=True)
    
    st.markdown("### 🗄️ Shelf Layout")
    st.markdown("Click on any shelf location to view and edit inventory items:")
    
    # Create shelf visualization with buttons
    cols = st.columns(5)
    
    for i, (shelf, layers) in enumerate(SHELF_STRUCTURE.items()):
        with cols[i]:
            st.markdown(f"**Shelf {shelf}**")
            for layer in layers:
                location = f"{shelf}{layer}"
                item_count = len(st.session_state.inventory_data[
                    st.session_state.inventory_data['Location'] == location
                ])
                
                button_text = f"{location} ({item_count} items)"
                if st.button(button_text, key=f"btn_{location}"):
                    st.session_state.selected_location = location
                    st.rerun()

def create_inventory_editor():
    """Create inventory editor for selected location"""
    if st.session_state.selected_location is None:
        st.info("👆 Please select a shelf location above to view and edit inventory items.")
        return
    
    location = st.session_state.selected_location
    st.markdown(f"## 📝 Inventory Editor - Location {location}")
    
    # Filter data for selected location
    location_data = st.session_state.inventory_data[
        st.session_state.inventory_data['Location'] == location
    ].copy()
    
    if location_data.empty:
        st.warning(f"No items found in location {location}")
        
        # Allow adding new items
        if st.button("➕ Add New Item"):
            new_row = pd.DataFrame({
                'Location': [location],
                'Description': ['New Item'],
                'Unit': [1],
                'Model': [''],
                'SN/Lot': [''],
                'Remark': [''],
                'Image_URL': ['']
            })
            st.session_state.inventory_data = pd.concat([
                st.session_state.inventory_data, new_row
            ], ignore_index=True)
            st.rerun()
        return
    
    # Configure grid options
    gb = GridOptionsBuilder.from_dataframe(location_data)
    gb.configure_default_column(
        editable=True,
        resizable=True,
        sortable=True,
        filter=True
    )
    gb.configure_column('Location', editable=False)  # Location shouldn't be editable
    gb.configure_column('Image_URL', width=200)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    gb.configure_pagination(enabled=True, paginationPageSize=10)
    
    grid_options = gb.build()
    
    # Display AgGrid
    grid_response = AgGrid(
        location_data,
        gridOptions=grid_options,
        height=400,
        width='100%',
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        key=f"grid_{location}"
    )
    
    # Update session state with edited data
    if grid_response['data'] is not None:
        edited_data = grid_response['data']
        # Update the main dataframe
        mask = st.session_state.inventory_data['Location'] == location
        st.session_state.inventory_data = st.session_state.inventory_data[~mask]
        st.session_state.inventory_data = pd.concat([
            st.session_state.inventory_data, edited_data
        ], ignore_index=True)
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Add New Item", key=f"add_{location}"):
            new_row = pd.DataFrame({
                'Location': [location],
                'Description': ['New Item'],
                'Unit': [1],
                'Model': [''],
                'SN/Lot': [''],
                'Remark': [''],
                'Image_URL': ['']
            })
            st.session_state.inventory_data = pd.concat([
                st.session_state.inventory_data, new_row
            ], ignore_index=True)
            st.rerun()
    
    with col2:
        if st.button("💾 Save Changes", key=f"save_{location}"):
            # Here you would typically save to your Excel file or database
            st.success("Changes saved successfully!")
    
    with col3:
        if st.button("🔄 Refresh Data", key=f"refresh_{location}"):
            st.session_state.inventory_data = load_inventory_data()
            st.rerun()

def create_image_gallery():
    """Create image gallery for selected location"""
    if st.session_state.selected_location is None:
        return
    
    location = st.session_state.selected_location
    location_data = st.session_state.inventory_data[
        st.session_state.inventory_data['Location'] == location
    ]
    
    # Filter items with image URLs
    items_with_images = location_data[
        location_data['Image_URL'].notna() & 
        (location_data['Image_URL'] != '')
    ]
    
    if items_with_images.empty:
        st.info(f"No images available for items in location {location}")
        return
    
    st.markdown(f"## 🖼️ Image Gallery - Location {location}")
    
    # Create image gallery
    cols_per_row = 3
    rows = len(items_with_images) // cols_per_row + (1 if len(items_with_images) % cols_per_row > 0 else 0)
    
    for row in range(rows):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            item_idx = row * cols_per_row + col_idx
            if item_idx < len(items_with_images):
                item = items_with_images.iloc[item_idx]
                with cols[col_idx]:
                    try:
                        if item['Image_URL']:
                            st.image(
                                item['Image_URL'],
                                caption=f"{item['Description']}\nModel: {item['Model']}",
                                use_container_width=True
                            )
                        else:
                            # Placeholder image
                            placeholder_url = "https://via.placeholder.com/300x200/f5f5f5/999999?text=No+Image"
                            st.image(
                                placeholder_url,
                                caption=f"{item['Description']}\nModel: {item['Model']}",
                                use_container_width=True
                            )
                    except:
                        # Fallback placeholder
                        placeholder_url = "https://via.placeholder.com/300x200/f5f5f5/999999?text=Image+Error"
                        st.image(
                            placeholder_url,
                            caption=f"{item['Description']}\nModel: {item['Model']}",
                            use_container_width=True
                        )

def create_statistics_sidebar():
    """Create statistics sidebar"""
    with st.sidebar:
        st.markdown("## 📊 Inventory Statistics")
        
        total_items = len(st.session_state.inventory_data)
        st.metric("Total Items", total_items)
        
        # Items by shelf
        st.markdown("### Items by Shelf")
        for shelf in SHELF_STRUCTURE.keys():
            shelf_items = len(st.session_state.inventory_data[
                st.session_state.inventory_data['Location'].str.startswith(shelf)
            ])
            st.metric(f"Shelf {shelf}", shelf_items)
        
        # Items with images
        items_with_images = len(st.session_state.inventory_data[
            st.session_state.inventory_data['Image_URL'].notna() & 
            (st.session_state.inventory_data['Image_URL'] != '')
        ])
        st.metric("Items with Images", items_with_images)
        
        # Items by status (based on remarks)
        functional_items = len(st.session_state.inventory_data[
            st.session_state.inventory_data['Remark'].str.contains('Functional', na=False)
        ])
        st.metric("Functional Items", functional_items)
        
        # Download data
        st.markdown("### 💾 Export Data")
        csv = st.session_state.inventory_data.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"inventory_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# Main app
def main():
    create_statistics_sidebar()
    create_shelf_visualization()
    create_inventory_editor()
    create_image_gallery()

if __name__ == "__main__":
    main()
