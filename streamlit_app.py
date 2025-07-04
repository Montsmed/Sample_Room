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
import time
import threading
from datetime import datetime

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

# GitHub API Configuration
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = "Montsmed/Sample_Room"
EXCEL_FILE_PATH = "inventory_data.xlsx"

# Auto-save configuration
AUTO_SAVE_DELAY = 2  # seconds to wait before auto-saving after last change
MAX_SAVE_ATTEMPTS = 3  # maximum retry attempts for failed saves

# Load data from GitHub Excel file
@st.cache_data
def load_inventory_data():
    """Load inventory data from GitHub Excel file"""
    try:
        response = requests.get(EXCEL_FILE_URL)
        response.raise_for_status()
        
        excel_data = BytesIO(response.content)
        df = pd.read_excel(excel_data)
        
        return clean_dataframe_types(df)
        
    except Exception as e:
        st.error(f"Error loading data from GitHub: {e}")
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
    
    df_clean['Location'] = df_clean['Location'].astype('string')
    df_clean['Description'] = df_clean['Description'].astype('string')
    df_clean['Unit'] = pd.to_numeric(df_clean['Unit'], errors='coerce').fillna(0).astype('int64')
    df_clean['Model'] = df_clean['Model'].astype('string')
    df_clean['SN/Lot'] = df_clean['SN/Lot'].astype('string')
    df_clean['Remark'] = df_clean['Remark'].astype('string')
    df_clean['Image_URL'] = df_clean['Image_URL'].astype('string')
    
    string_columns = ['Location', 'Description', 'Model', 'SN/Lot', 'Remark', 'Image_URL']
    for col in string_columns:
        df_clean[col] = df_clean[col].fillna('')
    
    return df_clean

def convert_df_to_excel(df):
    """Convert dataframe to Excel format"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
        
        workbook = writer.book
        worksheet = writer.sheets['Inventory']
        
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        for i, col in enumerate(df.columns):
            if len(df) > 0:
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col))
                ) + 2
            else:
                max_length = len(str(col)) + 2
            worksheet.set_column(i, i, min(max_length, 50))
    
    return output.getvalue()

def auto_save_to_github(df, attempt=1):
    """Auto-save dataframe to GitHub repository with retry logic"""
    if not GITHUB_TOKEN:
        return False, "GitHub token not configured"
    
    try:
        excel_data = convert_df_to_excel(df)
        excel_b64 = base64.b64encode(excel_data).decode('utf-8')
        
        get_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{EXCEL_FILE_PATH}"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        get_response = requests.get(get_url, headers=headers)
        
        commit_data = {
            'message': f'Auto-save inventory data - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'content': excel_b64,
            'branch': 'main'
        }
        
        if get_response.status_code == 200:
            current_file = get_response.json()
            commit_data['sha'] = current_file['sha']
        
        put_response = requests.put(get_url, headers=headers, json=commit_data)
        
        if put_response.status_code in [200, 201]:
            return True, "Successfully auto-saved to GitHub"
        else:
            if attempt < MAX_SAVE_ATTEMPTS:
                time.sleep(1)  # Wait 1 second before retry
                return auto_save_to_github(df, attempt + 1)
            return False, f"Failed after {MAX_SAVE_ATTEMPTS} attempts: {put_response.status_code}"
            
    except Exception as e:
        if attempt < MAX_SAVE_ATTEMPTS:
            time.sleep(1)
            return auto_save_to_github(df, attempt + 1)
        return False, f"Error after {MAX_SAVE_ATTEMPTS} attempts: {str(e)}"

def trigger_auto_save():
    """Trigger auto-save after delay"""
    if 'auto_save_timer' in st.session_state:
        st.session_state.auto_save_timer = time.time()
    else:
        st.session_state.auto_save_timer = time.time()
    
    st.session_state.pending_save = True

def check_and_execute_auto_save():
    """Check if auto-save should be executed and do it"""
    if (st.session_state.get('pending_save', False) and 
        'auto_save_timer' in st.session_state and 
        time.time() - st.session_state.auto_save_timer >= AUTO_SAVE_DELAY):
        
        st.session_state.pending_save = False
        
        # Show saving indicator
        save_placeholder = st.empty()
        save_placeholder.info("🔄 Auto-saving changes...")
        
        success, message = auto_save_to_github(st.session_state.inventory_data)
        
        if success:
            save_placeholder.success("✅ Auto-saved successfully!")
            st.session_state.last_save_time = datetime.now()
            st.cache_data.clear()  # Clear cache to ensure fresh data on reload
        else:
            save_placeholder.error(f"❌ Auto-save failed: {message}")
        
        # Clear the message after 3 seconds
        time.sleep(3)
        save_placeholder.empty()

# Initialize session state
if 'inventory_data' not in st.session_state:
    st.session_state.inventory_data = load_inventory_data()
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = None
if 'pending_save' not in st.session_state:
    st.session_state.pending_save = False
if 'last_save_time' not in st.session_state:
    st.session_state.last_save_time = None

def create_header():
    """Create header with auto-save status"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("## 📦 Inventory Management System")
    
    with col2:
        if st.session_state.pending_save:
            st.markdown("🟡 **Auto-saving...**")
        elif st.session_state.last_save_time:
            st.markdown(f"🟢 **Last saved:** {st.session_state.last_save_time.strftime('%H:%M:%S')}")
        else:
            st.markdown("🔵 **Auto-save enabled**")

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
    """Create download section and manual save option"""
    st.markdown("## 📁 File Management")
    
    if len(st.session_state.inventory_data) > 0:
        st.success(f"✅ Inventory data loaded successfully! ({len(st.session_state.inventory_data)} items)")
    else:
        st.warning("⚠️ No inventory data available. Please check the GitHub file URL.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Force Save Now", help="Manually trigger immediate save to GitHub"):
            if GITHUB_TOKEN:
                with st.spinner("Saving to GitHub..."):
                    success, message = auto_save_to_github(st.session_state.inventory_data)
                    if success:
                        st.success("✅ Successfully saved to GitHub!")
                        st.session_state.last_save_time = datetime.now()
                        st.session_state.pending_save = False
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ Failed to save: {message}")
            else:
                st.error("GitHub token not configured.")
    
    with col2:
        if st.button("🔄 Refresh Data", help="Reload data from GitHub repository"):
            st.cache_data.clear()
            st.session_state.inventory_data = load_inventory_data()
            st.session_state.pending_save = False
            st.success("Data refreshed successfully!")
            st.rerun()
    
    with col3:
        if len(st.session_state.inventory_data) > 0:
            excel_data = convert_df_to_excel(st.session_state.inventory_data)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"inventory_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download the current inventory data as an Excel file"
            )

def create_shelf_visualization():
    """Create interactive shelf visualization"""
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
    
    SHELF_LETTERS = ['A', 'B', 'C', 'D', 'E']
    
    for layer in [4, 3, 2, 1]:
        cols = st.columns(5)
        
        for i, shelf in enumerate(SHELF_LETTERS):
            with cols[i]:
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
                    
                    button_text = f"{location}\n({item_count} items)"
                    
                    if st.button(button_text, key=f"btn_{location}", type="secondary"):
                        st.session_state.selected_location = location
                        st.rerun()
                else:
                    st.write("")

def create_inventory_editor():
    """Create inventory editor with auto-save functionality"""
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
    st.markdown("*Changes are automatically saved to GitHub*")
    
    location_data = st.session_state.inventory_data[
        st.session_state.inventory_data['Location'] == location
    ].copy()
    
    if location_data.empty:
        st.warning(f"No items found in location {location}")
        
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
            trigger_auto_save()
            st.rerun()
        return
    
    location_data = clean_dataframe_types(location_data)
    location_data = location_data.reset_index(drop=True)
    
    gb = GridOptionsBuilder.from_dataframe(location_data)
    gb.configure_default_column(
        editable=True,
        resizable=True,
        sortable=True,
        filter=True
    )
    gb.configure_column('Image_URL', width=200)
    gb.configure_selection(
        selection_mode="multiple", 
        use_checkbox=True,
        rowMultiSelectWithClick=True,
        suppressRowDeselection=False
    )
    gb.configure_pagination(enabled=True, paginationPageSize=10)
    
    grid_options = gb.build()
    
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
    
    # Check for data changes and trigger auto-save
    if grid_response['data'] is not None:
        edited_data = grid_response['data']
        edited_data = clean_dataframe_types(edited_data)
        
        # Check if data actually changed
        original_data = st.session_state.inventory_data[
            st.session_state.inventory_data['Location'] == location
        ].reset_index(drop=True)
        
        if not edited_data.equals(original_data):
            mask = st.session_state.inventory_data['Location'] == location
            remaining_data = st.session_state.inventory_data[~mask]
            combined_data = pd.concat([remaining_data, edited_data], ignore_index=True)
            st.session_state.inventory_data = clean_dataframe_types(combined_data)
            trigger_auto_save()
    
    col1, col2 = st.columns(2)
    
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
            trigger_auto_save()
            st.rerun()
    
    with col2:
        if st.button("🗑️ Delete Selected", key=f"delete_{location}"):
            if grid_response['selected_rows'] is not None and len(grid_response['selected_rows']) > 0:
                selected_rows_df = pd.DataFrame(grid_response['selected_rows'])
                
                current_location_data = st.session_state.inventory_data[
                    st.session_state.inventory_data['Location'] == location
                ].copy()
                
                rows_to_keep = []
                
                for idx, current_row in current_location_data.iterrows():
                    is_selected = False
                    for _, selected_row in selected_rows_df.iterrows():
                        if (str(current_row['Description']) == str(selected_row['Description']) and 
                            str(current_row['Model']) == str(selected_row['Model']) and 
                            str(current_row['SN/Lot']) == str(selected_row['SN/Lot']) and
                            int(current_row['Unit']) == int(selected_row['Unit'])):
                            is_selected = True
                            break
                    
                    if not is_selected:
                        rows_to_keep.append(current_row)
                
                mask = st.session_state.inventory_data['Location'] == location
                other_data = st.session_state.inventory_data[~mask]
                
                if rows_to_keep:
                    remaining_location_data = pd.DataFrame(rows_to_keep)
                    st.session_state.inventory_data = pd.concat([other_data, remaining_location_data], ignore_index=True)
                else:
                    st.session_state.inventory_data = other_data
                
                st.session_state.inventory_data = clean_dataframe_types(st.session_state.inventory_data)
                trigger_auto_save()
                
                st.success(f"Deleted {len(selected_rows_df)} item(s)")
                st.rerun()
            else:
                st.warning("Please select rows to delete by clicking the checkboxes")

def create_image_gallery():
    """Create image gallery"""
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
                            st.image(item['Image_URL'], use_container_width=True)
                        else:
                            st.image(PLACEHOLDER_IMAGE, use_container_width=True)
                    except:
                        st.image(PLACEHOLDER_IMAGE, use_container_width=True)
                    
                    st.markdown(f"**{item['Description']}**")
                    st.markdown(f"Units: {item['Unit']}")

def create_statistics_sidebar():
    """Create statistics sidebar"""
    with st.sidebar:
        st.markdown("## 📊 Inventory Statistics")
        
        total_items = len(st.session_state.inventory_data)
        st.metric("Total Items", total_items)
        
        # Auto-save status
        if st.session_state.pending_save:
            st.warning("🟡 Auto-saving...")
        elif st.session_state.last_save_time:
            st.success(f"🟢 Last saved: {st.session_state.last_save_time.strftime('%H:%M:%S')}")
        else:
            st.info("🔵 Auto-save enabled")
        
        if total_items == 0:
            st.info("No inventory data available")
            return
        
        st.markdown("### Items by Shelf & Layer")
        for shelf in ['A', 'B', 'C', 'D', 'E']:
            shelf_items = len(st.session_state.inventory_data[
                st.session_state.inventory_data['Location'].str.startswith(shelf)
            ])
            st.metric(f"Shelf {shelf}", shelf_items)
            
            if shelf in ['A', 'B']:
                layers = [1, 2, 3]
            elif shelf in ['C', 'D']:
                layers = [1, 2, 3, 4]
            else:
                layers = [4]
            
            layer_text = ""
            for layer in sorted(layers, reverse=True):
                layer_count = len(st.session_state.inventory_data[
                    st.session_state.inventory_data['Location'] == f"{shelf}{layer}"
                ])
                position = "Top" if layer == 4 else "Upper" if layer == 3 else "Lower" if layer == 2 else "Bottom"
                layer_text += f"  • L{layer} ({position}): {layer_count}\n"
            
            if layer_text:
                st.text(layer_text.strip())
        
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
    
    # Check and execute auto-save
    check_and_execute_auto_save()

if __name__ == "__main__":
    main()
