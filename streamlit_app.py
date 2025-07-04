# app.py
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
import requests
from io import BytesIO
import xlsxwriter
import re
import base64
import json

# Configure page
st.set_page_config(
    page_title="Inventory Management System",
    page_icon="📦",
    layout="wide"
)

# GitHub URLs and Configuration
SAMPLE_ROOM_IMAGE = "https://raw.githubusercontent.com/Montsmed/Sample_Room/main/Sampleroom.png"
PLACEHOLDER_IMAGE = "https://raw.githubusercontent.com/Montsmed/Sample_Room/main/No_Image.jpg"
EXCEL_FILE_URL = "https://raw.githubusercontent.com/Montsmed/Sample_Room/main/inventory_data.xlsx"

# GitHub API Configuration - Add these to your Streamlit secrets
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")  # Your GitHub Personal Access Token
GITHUB_REPO = "Montsmed/Sample_Room"  # Your repository
EXCEL_FILE_PATH = "inventory_data.xlsx"  # Path to Excel file in repo

# Load data from GitHub Excel file
@st.cache_data
def load_inventory_data():
    """Load inventory data from GitHub Excel file"""
    try:
        # Download Excel file from GitHub
        response = requests.get(EXCEL_FILE_URL)
        response.raise_for_status()
        
        # Read Excel file from bytes
        excel_data = BytesIO(response.content)
        df = pd.read_excel(excel_data)
        
        # Clean and standardize data types
        return clean_dataframe_types(df)
        
    except Exception as e:
        st.error(f"Error loading data from GitHub: {e}")
        # Return empty dataframe with correct structure if loading fails
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

def save_to_github(df):
    """Save dataframe to GitHub repository as Excel file"""
    if not GITHUB_TOKEN:
        st.error("GitHub token not configured. Please add GITHUB_TOKEN to your Streamlit secrets.")
        return False
    
    try:
        # Convert dataframe to Excel bytes
        excel_data = convert_df_to_excel(df)
        
        # Encode to base64 for GitHub API
        excel_b64 = base64.b64encode(excel_data).decode('utf-8')
        
        # Get current file SHA (required for updating)
        get_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{EXCEL_FILE_PATH}"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        get_response = requests.get(get_url, headers=headers)
        
        # Prepare commit data
        commit_data = {
            'message': f'Update inventory data - {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'content': excel_b64,
            'branch': 'main'  # or your default branch
        }
        
        # If file exists, add SHA for update
        if get_response.status_code == 200:
            current_file = get_response.json()
            commit_data['sha'] = current_file['sha']
        
        # Update/create file
        put_response = requests.put(get_url, headers=headers, json=commit_data)
        
        if put_response.status_code in [200, 201]:
            return True
        else:
            st.error(f"Failed to save to GitHub: {put_response.status_code} - {put_response.text}")
            return False
            
    except Exception as e:
        st.error(f"Error saving to GitHub: {e}")
        return False

# Initialize session state
if 'inventory_data' not in st.session_state:
    st.session_state.inventory_data = load_inventory_data()
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = None
if 'data_changed' not in st.session_state:
    st.session_state.data_changed = False

def create_header():
    """Create header"""
    st.markdown("## 📦 Inventory Management System")
    
    # Show save status
    if st.session_state.data_changed:
        st.warning("⚠️ You have unsaved changes!")

def create_search_bar():
    """Create search functionality for inventory items"""
    st.markdown("## 🔍 Search Inventory Items")
    
    if len(st.session_state.inventory_data) == 0:
        st.info("No inventory data available. Please check the GitHub file URL.")
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
    """Create download section and global save functionality"""
    st.markdown("## 📁 File Management")
    
    # Show data status
    if len(st.session_state.inventory_data) > 0:
        st.success(f"✅ Inventory data loaded successfully! ({len(st.session_state.inventory_data)} items)")
    else:
        st.warning("⚠️ No inventory data available. Please check the GitHub file URL.")
    
    # Global save and refresh buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save All Changes to GitHub", type="primary", help="Save all changes to the GitHub repository"):
            if GITHUB_TOKEN:
                with st.spinner("Saving to GitHub..."):
                    if save_to_github(st.session_state.inventory_data):
                        st.success("✅ Successfully saved to GitHub!")
                        st.session_state.data_changed = False
                        # Clear cache to reload fresh data
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("❌ Failed to save to GitHub. Please check your configuration.")
            else:
                st.error("GitHub token not configured. Please add GITHUB_TOKEN to your Streamlit secrets.")
    
    with col2:
        if st.button("🔄 Refresh Data from GitHub", help="Reload data from the GitHub repository"):
            st.cache_data.clear()
            st.session_state.inventory_data = load_inventory_data()
            st.session_state.data_changed = False
            st.success("Data refreshed successfully!")
            st.rerun()
    
    with col3:
        # Download section
        if len(st.session_state.inventory_data) > 0:
            # Convert dataframe to Excel
            excel_data = convert_df_to_excel(st.session_state.inventory_data)
            
            # Create download button
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"inventory_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download the current inventory data as an Excel file"
            )

def create_shelf_visualization():
    """Create interactive shelf visualization with resized sample room layout image"""
    # Room layout image from GitHub - resized to 1/3 width and height
    st.markdown("### 🏠 Sample Room Layout")
    try:
        st.image(SAMPLE_ROOM_IMAGE, caption="Sample Room Layout", width=400)
    except:
        st.error("Could not load sample room image from GitHub")
    
    st.markdown("### 🗄️ Shelf Layout")
    st.markdown("**Layer arrangement: 4 (Top) → 3 → 2 → 1 (Bottom)**")
    
    if len(st.session_state.inventory_data) == 0:
        st.info("📊 No inventory data available. Please check the GitHub file URL.")
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
    """Create inventory editor for selected location with GitHub save integration"""
    if len(st.session_state.inventory_data) == 0:
        st.info("📊 No inventory data available. Please check the GitHub file URL.")
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
            st.session_state.data_changed = True
            st.rerun()
        return
    
    # Clean data types before displaying
    location_data = clean_dataframe_types(location_data)
    location_data = location_data.reset_index(drop=True)
    
    # Configure grid options - Location column is now editable
    gb = GridOptionsBuilder.from_dataframe(location_data)
    gb.configure_default_column(
        editable=True,
        resizable=True,
        sortable=True,
        filter=True
    )
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
        st.session_state.data_changed = True
    
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
            st.session_state.data_changed = True
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
                st.session_state.data_changed = True
                
                st.success(f"Deleted {len(selected_rows_df)} item(s)")
                st.rerun()
            else:
                st.warning("Please select rows to delete by clicking the checkboxes")
    
    with col3:
        if st.button("💾 Save to GitHub", key=f"save_{location}", type="primary"):
            if GITHUB_TOKEN:
                with st.spinner("Saving to GitHub..."):
                    if save_to_github(st.session_state.inventory_data):
                        st.success("✅ Successfully saved to GitHub!")
                        st.session_state.data_changed = False
                        # Clear cache to reload fresh data
                        st.cache_data.clear()
                    else:
                        st.error("❌ Failed to save to GitHub. Please check your configuration.")
            else:
                st.error("GitHub token not configured. Please add GITHUB_TOKEN to your Streamlit secrets.")
    
    with col4:
        if st.button("🔄 Refresh", key=f"refresh_{location}"):
            st.cache_data.clear()
            st.session_state.inventory_data = load_inventory_data()
            st.session_state.data_changed = False
            st.success("Data refreshed!")
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
        
        # Show unsaved changes indicator
        if st.session_state.data_changed:
            st.warning("⚠️ Unsaved changes")
        else:
            st.success("✅ All changes saved")
        
        if total_items == 0:
            st.info("No inventory data available")
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
