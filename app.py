import streamlit as st
import pandas as pd
from utils.data_reader import DataReader
from utils.mapper import SmartMapper
from utils.transformer import DataTransformer
from utils.metadata_manager import MetadataManager
import io

# Page configuration
st.set_page_config(
    page_title="Smart Data Mapper",
    page_icon="🗺️",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    .mapping-box {
        padding: 1.5rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        margin: 1rem 0;
        color: white;
    }
    h1 {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'raw_df' not in st.session_state:
        st.session_state.raw_df = None
    if 'template_df' not in st.session_state:
        st.session_state.template_df = None
    if 'mappings' not in st.session_state:
        st.session_state.mappings = None
    if 'output_df' not in st.session_state:
        st.session_state.output_df = None
    if 'metadata_manager' not in st.session_state:
        st.session_state.metadata_manager = MetadataManager()

def main():
    initialize_session_state()
    
    # Header
    st.title("🗺️ Ethorx")
    st.markdown("### Transform messy data into perfect templates - automatically")
    st.caption("Privacy-first • No AI • No data storage • Industrial-grade accuracy")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Fixed threshold (hidden from user - optimal value)
        similarity_threshold = 70  # Optimal threshold for accurate matching
        
        output_format = st.selectbox(
            "Output Format",
            ["csv", "excel", "json"],
            index=1
        )
        
        st.markdown("---")
        
        # Privacy Notice
        st.markdown("### � Privacy First")
        st.info("""
        **Your data is NEVER stored!**
        - Only mapping metadata is saved
        - Raw data stays in your browser
        - No data sent to servers
        - Session-based processing only
        """)
        
        st.markdown("---")
        
        # Metadata Management
        st.markdown("### 💾 Save/Load Mappings")
        
        col_save, col_load = st.columns(2)
        
        with col_save:
            if st.button("📤 Export", help="Save mapping configuration"):
                if st.session_state.mappings:
                    # Create metadata without actual data
                    raw_stats = {
                        'row_count': len(st.session_state.raw_df),
                        'column_count': len(st.session_state.raw_df.columns),
                        'columns': list(st.session_state.raw_df.columns)
                    }
                    template_stats = {
                        'row_count': len(st.session_state.template_df),
                        'column_count': len(st.session_state.template_df.columns),
                        'columns': list(st.session_state.template_df.columns)
                    }
                    
                    metadata = st.session_state.metadata_manager.create_metadata(
                        list(st.session_state.raw_df.columns),
                        list(st.session_state.template_df.columns),
                        st.session_state.mappings,
                        raw_stats,
                        template_stats
                    )
                    
                    st.download_button(
                        "⬇️ Download Config",
                        data=st.session_state.metadata_manager.export_metadata(),
                        file_name="mapping_config.json",
                        mime="application/json"
                    )
        
        with col_load:
            uploaded_metadata = st.file_uploader(
                "📥 Import",
                type=['json'],
                key='metadata_upload',
                help="Load saved mapping configuration",
                label_visibility="collapsed"
            )
            
            if uploaded_metadata:
                try:
                    metadata_json = uploaded_metadata.read().decode('utf-8')
                    st.session_state.metadata_manager.import_metadata(metadata_json)
                    st.success("✅ Config loaded!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        st.markdown("---")
        st.markdown("### �📖 How to Use")
        st.markdown("""
        1. Upload your **raw data** file
        2. Upload your **template** file
        3. Click **Auto-Map Fields**
        4. Review automatic mappings
        5. Adjust if needed
        6. Transform & download
        
        💡 **Tip:** Save your mapping config to reuse it later!
        """)
    
    # Main content
    col1, col2 = st.columns(2)
    
    # File upload section
    with col1:
        st.subheader("📁 Upload Raw Data")
        raw_file = st.file_uploader(
            "Choose your raw data file",
            type=['csv', 'xlsx', 'xls', 'json'],
            key='raw',
            help="Upload messy/unstructured data"
        )
        
        if raw_file:
            try:
                reader = DataReader()
                st.session_state.raw_df = reader.read_file(raw_file)
                st.success(f"✅ Loaded {len(st.session_state.raw_df)} rows")
                
                with st.expander("Preview Raw Data"):
                    st.dataframe(st.session_state.raw_df.head(10))
                    st.write(f"**Columns:** {', '.join(st.session_state.raw_df.columns.tolist())}")
            except Exception as e:
                st.error(f"❌ Error loading raw data: {str(e)}")
    
    with col2:
        st.subheader("📋 Upload Template")
        template_file = st.file_uploader(
            "Choose your template file",
            type=['csv', 'xlsx', 'xls', 'json'],
            key='template',
            help="Upload template with desired structure"
        )
        
        if template_file:
            try:
                reader = DataReader()
                st.session_state.template_df = reader.read_file(template_file)
                st.success(f"✅ Template loaded with {len(st.session_state.template_df.columns)} columns")
                
                with st.expander("Preview Template"):
                    st.dataframe(st.session_state.template_df.head(10))
                    st.write(f"**Required Columns:** {', '.join(st.session_state.template_df.columns.tolist())}")
            except Exception as e:
                st.error(f"❌ Error loading template: {str(e)}")
    
    st.markdown("---")
    
    # Mapping section
    if st.session_state.raw_df is not None and st.session_state.template_df is not None:
        st.subheader("🔗 Field Mapping")
        
        # Create mapper instance for use throughout the mapping section
        mapper = SmartMapper(similarity_threshold=similarity_threshold)
        
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            if st.button("🚀 Auto-Map Fields", type="primary"):
                with st.spinner("Analyzing and mapping fields..."):
                    
                    # Initial fuzzy matching
                    st.session_state.mappings = mapper.fuzzy_match_headers(
                        st.session_state.raw_df.columns.tolist(),
                        st.session_state.template_df.columns.tolist()
                    )
                    
                    # Enhance with pattern matching
                    st.session_state.mappings = mapper.semantic_pattern_match(
                        st.session_state.raw_df,
                        st.session_state.template_df,
                        st.session_state.mappings
                    )
                    
                st.success("✅ Auto-mapping complete!")
        
        with col_right:
            if st.session_state.mappings:
                matched = sum(1 for _, (match, score) in st.session_state.mappings.items() 
                            if match is not None)
                total = len(st.session_state.mappings)
                percentage = int(matched/total*100) if total > 0 else 0
                st.metric("Mapped Fields", f"{matched}/{total}", 
                         f"{percentage}% complete")
        
        # Display and edit mappings
        if st.session_state.mappings:
            st.markdown("### Review and Adjust Mappings")
            
            # Initialize used_columns in session state if it doesn't exist
            if 'used_columns' not in st.session_state:
                st.session_state.used_columns = set()
            
            # Detect contamination issues
            contamination_info = mapper._detect_value_contamination(st.session_state.raw_df) 

            
            # Show contamination warning if detected
            if contamination_info:
                contaminated_cols = list(contamination_info.keys())
                st.warning(f"⚠️ **Data Quality Issue Detected**: {len(contaminated_cols)} column(s) have overlapping values with other columns. This may affect matching accuracy. Review mappings carefully.")
                with st.expander("View Contamination Details"):
                    for col, overlaps in contamination_info.items():
                        overlap_str = ", ".join(overlaps)
                        st.write(f"- **{col}** shares values with: {overlap_str}")
            
            # Add filter option
            col_filter, col_spacer = st.columns([1, 3])
            with col_filter:
                show_all = st.checkbox("Show all mappings", value=True)
            
            # Count auto-accepted mappings
            auto_accepted = sum(1 for _, (raw_col, conf) in st.session_state.mappings.items() 
                              if raw_col is not None and conf >= 0.8)
            
            if auto_accepted > 0 and not show_all:
                st.info(f"✅ {auto_accepted} high-confidence mapping(s) auto-accepted (≥80%). Check 'Show all mappings' to review them.")
            
            # Initialize used_columns in session state if it doesn't exist
            # Create a set of all currently used columns for quick lookup
            # We rebuild this from the mappings every time to ensure consistency
            used_columns_set = {
                r_col for _, (r_col, _) in st.session_state.mappings.items() 
                if r_col is not None
            }
            
            edited_mappings = {}
            
            # Second pass: process other mappings
            for i, (template_col, (raw_col, confidence)) in enumerate(st.session_state.mappings.items()):
                # Skip high-confidence matches if filter is enabled
                if not show_all and raw_col is not None and confidence >= 0.8:
                    continue
                    
                col_a, col_b, col_c, col_d = st.columns([3, 3, 1.2, 1.5], gap="medium")
                
                with col_a:
                    st.markdown(f"<div style='height: 42px; display: flex; align-items: center; font-weight: 500;'>{template_col}</div>", unsafe_allow_html=True)
                
                with col_b:
                    # Get available columns (not used by other mappings)
                    available_columns = ["<No Match>"] + [
                        col for col in st.session_state.raw_df.columns 
                        if col not in used_columns_set or col == raw_col
                    ]
                    
                    # Get current selection
                    current_selection = raw_col if raw_col in available_columns[1:] else "<No Match>"
                    
                    # Create the selectbox
                    selected = st.selectbox(
                        "Maps to Raw Column",
                        available_columns,
                        index=available_columns.index(current_selection) if current_selection in available_columns else 0,
                        key=f"map_{template_col}",
                        label_visibility="collapsed"
                    )
                    
                    # Update the used columns
                    # Update mappings
                    if selected != "<No Match>":
                        # If this is a manual selection that differs from auto-map, treat as 100% confidence manual match
                        # otherwise keep the calculated confidence
                        new_score = confidence if confidence > 0 else 1.0
                        edited_mappings[template_col] = (selected, new_score)
                    else:
                        edited_mappings[template_col] = (None, 0.0)
                
                with col_c:
                    if confidence > 0:
                        confidence_pct = int(confidence * 100)
                        color = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🟠"
                        st.markdown(f"{color} {confidence_pct}%")
                    else:
                        st.markdown("⚪ N/A")
                
                with col_d:
                    if selected and selected != "<No Match>":
                        # Show data pattern with contamination warning
                        pattern = mapper.detect_data_patterns(st.session_state.raw_df[selected])
                        
                        # Add warning icon if column is contaminated
                        if selected in contamination_info:
                            st.caption(f"⚠️ {pattern}")
                        else:
                            st.caption(f"({pattern})")
            
            st.session_state.mappings = edited_mappings
            
            st.markdown("---")
            
            # Transform and preview
            col_transform, col_download = st.columns(2)
            
            with col_transform:
                if st.button("✨ Transform Data", type="primary"):
                    with st.spinner("Transforming data..."):
                        transformer = DataTransformer()
                        st.session_state.output_df = transformer.apply_mappings(
                            st.session_state.raw_df,
                            st.session_state.mappings,
                            st.session_state.template_df
                        )
                    st.success("✅ Data transformed successfully!")
            
            # Preview output
            if st.session_state.output_df is not None:
                st.subheader("📊 Preview Transformed Data")
                
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                with col_stats1:
                    st.metric("Total Rows", len(st.session_state.output_df))
                with col_stats2:
                    st.metric("Total Columns", len(st.session_state.output_df.columns))
                with col_stats3:
                    completeness = (1 - st.session_state.output_df.isnull().sum().sum() / 
                                  (st.session_state.output_df.shape[0] * st.session_state.output_df.shape[1])) * 100
                    st.metric("Data Completeness", f"{completeness:.1f}%")
                
                st.dataframe(st.session_state.output_df.head(20))
                
                # Download section
                st.markdown("### 📥 Download Transformed Data")
                
                try:
                    transformer = DataTransformer()
                    file_data = transformer.export_data(
                        st.session_state.output_df,
                        output_format,
                        f"mapped_data.{output_format}"
                    )
                    
                    file_extension = output_format if output_format != "excel" else "xlsx"
                    mime_types = {
                        "csv": "text/csv",
                        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "json": "application/json"
                    }
                    
                    st.download_button(
                        label=f"⬇️ Download as {output_format.upper()}",
                        data=file_data,
                        file_name=f"mapped_data.{file_extension}",
                        mime=mime_types[output_format],
                        type="primary"
                    )
                except Exception as e:
                    st.error(f"❌ Error exporting data: {str(e)}")

if __name__ == "__main__":
    main()
