# app.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import requests
from io import BytesIO
import xlsxwriter
import re

# Configure page
st.set_page_config(
    page_title="Inventory Management System",
    page_icon="📦",
    layout="wide"
)

# GitHub image URLs
SAMPLE_ROOM_IMAGE = "https://raw.githubusercontent.com/Montsmed/Sample_Room/main/Sampleroom.png"
PLACEHOLDER_IMAGE = "https://raw.githubusercontent.com/Montsmed/Sample_Room/main/No_Image.jpg"

# Load data from Excel file
@st.cache_data
def load_inventory_data():
    """Load inventory data - starts empty, user must upload Excel file"""
    # Return empty dataframe with correct column structure and proper data types
    return pd.DataFrame({
        'Location': pd.Series([], dtype='string'),
        'Description': pd.Series([], dtype='string'),
        'Unit': pd.Series([], dtype='int64'),
        'Model': pd.Series([], dtype='string'),
        'SN/Lot': pd.Series([], dtype='string'),
        'Remark': pd.Series([], dtype='string'),
        'Image_URL': pd.Series([], dtype='string')
    })

def clean_dataframe_types(df):
    """Clean and standardize DataFrame column types for Arrow compatibility"""
    df_clean = df.copy()
    
    # Convert all columns to appropriate types
    df_clean['Location'] = df_clean['Location'].astype('string')
    df_clean['Description'] = df_clean['Description'].astype('string')
    df_clean['Unit'] = pd.to_numeric(df_clean['Unit'], errors='coerce').fillna(0).astype('int64')
    df_clean['Model'] = df_clean['Model'].astype('string')
    df_clean['SN/Lot'] = df_clean['SN/Lot'].astype('string')
    df_clean['Remark'] = df_clean['Remark'].astype('string')
    df_clean['Image_URL'] = df_clean['Image_URL'].astype('string')
    
    # Replace NaN values with empty strings for string columns
    string_columns = ['Location', 'Description', 'Model', 'SN/Lot', 'Remark', 'Image_URL']
    for col in string_columns:
        df_clean[col] = df_clean[col].fillna('')
    
    return df_clean

def convert_df_to_excel(df):
    """Convert dataframe to Excel format for download"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
        
        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Inventory']
        
        # Add some formatting
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Write the column headers with the defined format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            if len(df) > 0:  # Only if dataframe has data
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col))
                ) + 2
            else:
                max_length = len(str(col)) + 2
            worksheet.set_column(i, i, min(max_length, 50))
    
    processed_data = output.getvalue()
    return processed_data

# Initialize session state
if 'inventory_data' not in st.session_state:
    st.session_state.inventory_data = load_inventory_data()
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = None

def create_header():
    """Create header"""
    st.markdown("## 📦 Inventory Management System")

def create_search_bar():
    """Create search functionality for inventory items"""
    st.markdown("## 🔍 Search Inventory Items")
    
    if len(st.session_state.inventory_data) == 0:
        st.info("Upload an Excel file first to enable search functionality.")
        return
    
    search_query = st.text_input(
        "Enter search term (description, SN/Lot, model):",
        placeholder="Type to search items..."
    )
    
    if search_query:
        # Case-insensitive partial match in Description, SN/Lot, or Model
        pattern = re.compile(re.escape(search_query), re.IGNORECASE)
        filtered_data = st.session_state.inventory_data[
            st.session_state.inventory_data['Description'].str.contains(pattern, na=False) |
            st.session_state.inventory_data['SN/Lot'].str.contains(pattern, na=False) |
            st.session_state.inventory_data['Model'].str.contains(pattern, na=False)
        ]
        
        if len(filtered_data) > 0:
            st.markdown(f"### 🎯 Search Results: {len(filtered_data)} item(s) found")
            st.dataframe(filtered_data, use_container_width=True)
        else:
            st.warning(f"No items found matching '{search_query}'")
    else:
        st.info("Type in the search box to find items by description, SN/Lot, or model.")

def create_file_management():
    """Create file upload and download section - automatic import on upload"""
    st.markdown("## 📁 File Management")
    
    # Show initial message if no data
    if len(st.session_state.inventory_data) == 0:
        st.info("🚀 Welcome! Please upload an Excel file to get started with your inventory management.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📤 Upload Excel File")
        uploaded_file = st.file_uploader(
            "Choose an Excel file to load inventory data",
            type=['xlsx', 'xls'],
            help="Upload an Excel file with columns: Location, Description, Unit, Model, SN/Lot, Remark, Image_URL"
        )
        
        if uploaded_file is not None:
            try:
                # Read the uploaded Excel file
                new_data = pd.read_excel(uploaded_file)
                
                # Clean the data types
                new_data = clean_dataframe_types(new_data)
                
                # Validate required columns
                required_columns = ['Location', 'Description', 'Unit', 'Model', 'SN/Lot', 'Remark', 'Image_URL']
                missing_columns = [col for col in required_columns if col not in new_data.columns]
                
                if missing_columns:
                    st.error(f"Missing required columns: {', '.join(missing_columns)}")
                    st.info("Please ensure your Excel file has these columns: Location, Description, Unit, Model, SN/Lot, Remark, Image_URL")
                else:
                    # Automatically import the data
                    st.session_state.inventory_data = new_data
                    st.success(f"✅ File uploaded and imported successfully! {len(new_data)} items loaded.")
                    st.rerun()
                        
            except Exception as e:
                st.error(f"Error reading Excel file: {e}")
                st.info("Please make sure the file is a valid Excel file (.xlsx or .xls)")
    
    with col2:
        st.markdown("### 📥 Download Excel File")
        
        if len(st.session_state.inventory_data) > 0:
            st.write("Download the current inventory data as an Excel file")
            
            # Convert dataframe to Excel
            excel_data = convert_df_to_excel(st.session_state.inventory_data)
            
            # Create download button
            st.download_button(
                label="📥 Download Inventory Data",
                data=excel_data,
                file_name=f"inventory_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download the current inventory data as an Excel file"
            )
        else:
            st.info("No data available to download. Please upload an Excel file first.")
            
            # Provide template download
            template_data = load_inventory_data()
            template_excel = convert_df_to_excel(template_data)
            
            st.download_button(
                label="📋 Download Template",
                data=template_excel,
                file_name="inventory_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download an empty template to fill with your inventory data"
            )


def create_shelf_visualization():
    """Create interactive shelf visualization with resized sample room layout image"""
    # Room layout image from GitHub - resized to 1/3 width and height
    st.markdown("### 🏠 Sample Room Layout")
    try:
        st.image(SAMPLE_ROOM_IMAGE, caption="Sample Room Layout", width=400)
    except:
        st.error("Could not load sample room image from GitHub")
    
    st.markdown("### 🗄️ Shelf Layout (5×4 Grid)")
    st.markdown("**Layer arrangement: 4 (Top) → 3 → 2 → 1 (Bottom)**")
    
    if len(st.session_state.inventory_data) == 0:
        st.info("📤 Upload an Excel file to see inventory items in the shelf locations.")
        return
    
    st.markdown("Click on any shelf location to view and edit inventory items:")
    
    # Define shelf letters
    SHELF_LETTERS = ['A', 'B', 'C', 'D', 'E']
    
    # Create 4 rows for layers 4, 3, 2, 1 (top to bottom)
    for layer in [4, 3, 2, 1]:
        cols = st.columns(5)
        
        for i, shelf in enumerate(SHELF_LETTERS):
            with cols[i]:
                # Define valid layers for each shelf
                if shelf in ['A', 'B']:
                    valid_layers = [1, 2, 3]
                elif shelf in ['C', 'D']:
                    valid_layers = [1, 2, 3, 4]
                elif shelf == 'E':
                    valid_layers = [4]
                else:
                    valid_layers = []
                
                if layer in valid_layers:
                    location = f"{shelf}{layer}"
                    item_count = len(st.session_state.inventory_data[
                        st.session_state.inventory_data['Location'] == location
                    ])
                    
                    # Simple button text without visual indicators
                    button_text = f"{location}\n({item_count} items)"
                    
                    # Use secondary button type (blue)
                    if st.button(button_text, key=f"btn_{location}", type="secondary"):
                        st.session_state.selected_location = location
                        st.rerun()
                else:
                    # Empty space for shelves that don't have this layer
                    st.write("")

def create_inventory_editor():
    """Create inventory editor for selected location with improved delete functionality"""
    if len(st.session_state.inventory_data) == 0:
        st.info("📤 Please upload an Excel file first to start managing your inventory.")
        return
        
    if st.session_state.selected_location is None:
        st.info("👆 Please select a shelf location above to view and edit inventory items.")
        return
    
    location = st.session_state.selected_location
    layer_num = location[-1]
    layer_position = "Top" if layer_num == "4" else "Upper" if layer_num == "3" else "Lower" if layer_num == "2" else "Bottom"
    
    st.markdown(f"## 📝 Inventory Editor - Location {location} ({layer_position} Layer)")
    
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
            new_row = clean_dataframe_types(new_row)
            combined_data = pd.concat([st.session_state.inventory_data, new_row], ignore_index=True)
            st.session_state.inventory_data = clean_dataframe_types(combined_data)
            st.rerun()
        return
    
    # Clean data types before displaying
    location_data = clean_dataframe_types(location_data)
    location_data = location_data.reset_index(drop=True)
    
    # Configure grid options - Remove the extra Select column
    gb = GridOptionsBuilder.from_dataframe(location_data)
    gb.configure_default_column(
        editable=True,
        resizable=True,
        sortable=True,
        filter=True
    )
    gb.configure_column('Location', editable=False)
    gb.configure_column('Image_URL', width=200)
    
    # Configure selection - use only built-in row selection
    gb.configure_selection(
        selection_mode="multiple", 
        use_checkbox=True,
        rowMultiSelectWithClick=True,
        suppressRowDeselection=False
    )
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
        key=f"grid_{location}",
        enable_enterprise_modules=False
    )
    
    # Update session state with edited data
    if grid_response['data'] is not None:
        edited_data = grid_response['data']
        edited_data = clean_dataframe_types(edited_data)
        # Update the main dataframe
        mask = st.session_state.inventory_data['Location'] == location
        remaining_data = st.session_state.inventory_data[~mask]
        combined_data = pd.concat([remaining_data, edited_data], ignore_index=True)
        st.session_state.inventory_data = clean_dataframe_types(combined_data)
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    
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
            new_row = clean_dataframe_types(new_row)
            combined_data = pd.concat([st.session_state.inventory_data, new_row], ignore_index=True)
            st.session_state.inventory_data = clean_dataframe_types(combined_data)
            st.rerun()
    
    with col2:
        if st.button("🗑️ Delete Selected", key=f"delete_{location}"):
            # Improved delete function using selected_rows
            if grid_response['selected_rows'] is not None and len(grid_response['selected_rows']) > 0:
                selected_rows_df = pd.DataFrame(grid_response['selected_rows'])
                
                # Get current location data
                current_location_data = st.session_state.inventory_data[
                    st.session_state.inventory_data['Location'] == location
                ].copy()
                
                # Create a list to track which rows to keep
                rows_to_keep = []
                
                for idx, current_row in current_location_data.iterrows():
                    # Check if this row is in the selected rows
                    is_selected = False
                    for _, selected_row in selected_rows_df.iterrows():
                        # Compare key fields to identify the row
                        if (str(current_row['Description']) == str(selected_row['Description']) and 
                            str(current_row['Model']) == str(selected_row['Model']) and 
                            str(current_row['SN/Lot']) == str(selected_row['SN/Lot']) and
                            int(current_row['Unit']) == int(selected_row['Unit'])):
                            is_selected = True
                            break
                    
                    if not is_selected:
                        rows_to_keep.append(current_row)
                
                # Update the main dataframe
                mask = st.session_state.inventory_data['Location'] == location
                other_data = st.session_state.inventory_data[~mask]
                
                if rows_to_keep:
                    remaining_location_data = pd.DataFrame(rows_to_keep)
                    st.session_state.inventory_data = pd.concat([other_data, remaining_location_data], ignore_index=True)
                else:
                    st.session_state.inventory_data = other_data
                
                st.session_state.inventory_data = clean_dataframe_types(st.session_state.inventory_data)
                
                st.success(f"Deleted {len(selected_rows_df)} item(s)")
                st.rerun()
            else:
                st.warning("Please select rows to delete by clicking the checkboxes")
    
    with col3:
        if st.button("💾 Save Changes", key=f"save_{location}"):
            st.success("Changes saved successfully!")
    
    with col4:
        if st.button("🔄 Clear Location", key=f"clear_{location}"):
            if st.button("⚠️ Confirm Clear All", key=f"confirm_clear_{location}"):
                # Remove all items from this location
                mask = st.session_state.inventory_data['Location'] == location
                st.session_state.inventory_data = st.session_state.inventory_data[~mask]
                st.success(f"Cleared all items from location {location}")
                st.rerun()

def create_image_gallery():
    """Create simplified image gallery showing only description and units"""
    if len(st.session_state.inventory_data) == 0 or st.session_state.selected_location is None:
        return
    
    location = st.session_state.selected_location
    location_data = st.session_state.inventory_data[
        st.session_state.inventory_data['Location'] == location
    ]
    
    if location_data.empty:
        return
    
    layer_num = location[-1]
    layer_position = "Top" if layer_num == "4" else "Upper" if layer_num == "3" else "Lower" if layer_num == "2" else "Bottom"
    
    st.markdown(f"## 🖼️ Image Gallery - Location {location} ({layer_position} Layer)")
    
    # Create image gallery
    cols_per_row = 3
    rows = len(location_data) // cols_per_row + (1 if len(location_data) % cols_per_row > 0 else 0)
    
    for row in range(rows):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            item_idx = row * cols_per_row + col_idx
            if item_idx < len(location_data):
                item = location_data.iloc[item_idx]
                with cols[col_idx]:
                    try:
                        if item['Image_URL'] and str(item['Image_URL']).strip() and str(item['Image_URL']) != 'nan':
                            st.image(
                                item['Image_URL'],
                                use_container_width=True
                            )
                        else:
                            st.image(
                                PLACEHOLDER_IMAGE,
                                use_container_width=True
                            )
                    except:
                        st.image(
                            PLACEHOLDER_IMAGE,
                            use_container_width=True
                        )
                    
                    # Show only description and unit count
                    st.markdown(f"**{item['Description']}**")
                    st.markdown(f"Units: {item['Unit']}")

def create_statistics_sidebar():
    """Create statistics sidebar with layer information"""
    with st.sidebar:
        st.markdown("## 📊 Inventory Statistics")
        
        total_items = len(st.session_state.inventory_data)
        st.metric("Total Items", total_items)
        
        if total_items == 0:
            st.info("Upload an Excel file to see statistics")
            return
        
        # Items by shelf and layer
        st.markdown("### Items by Shelf & Layer")
        for shelf in ['A', 'B', 'C', 'D', 'E']:
            shelf_items = len(st.session_state.inventory_data[
                st.session_state.inventory_data['Location'].str.startswith(shelf)
            ])
            st.metric(f"Shelf {shelf}", shelf_items)
            
            # Show layer breakdown
            if shelf in ['A', 'B']:
                layers = [1, 2, 3]
            elif shelf in ['C', 'D']:
                layers = [1, 2, 3, 4]
            else:  # E
                layers = [4]
            
            layer_text = ""
            for layer in sorted(layers, reverse=True):  # Top to bottom
                layer_count = len(st.session_state.inventory_data[
                    st.session_state.inventory_data['Location'] == f"{shelf}{layer}"
                ])
                position = "Top" if layer == 4 else "Upper" if layer == 3 else "Lower" if layer == 2 else "Bottom"
                layer_text += f"  • L{layer} ({position}): {layer_count}\n"
            
            if layer_text:
                st.text(layer_text.strip())
        
        # Items with images
        items_with_images = len(st.session_state.inventory_data[
            (st.session_state.inventory_data['Image_URL'].notna()) & 
            (st.session_state.inventory_data['Image_URL'] != '') &
            (st.session_state.inventory_data['Image_URL'] != 'nan')
        ])
        st.metric("Items with Images", items_with_images)
        
        # Items by status
        functional_items = len(st.session_state.inventory_data[
            st.session_state.inventory_data['Remark'].str.contains('Functional', na=False)
        ])
        st.metric("Functional Items", functional_items)

# Main app
def main():
    create_header()
    create_statistics_sidebar()
    create_file_management()
    create_search_bar()
    create_shelf_visualization()
    create_inventory_editor()
    create_image_gallery()

if __name__ == "__main__":
    main()
