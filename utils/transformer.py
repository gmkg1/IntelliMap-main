import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import re

class DataTransformer:
    """Handles data transformation and cleaning"""
    
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize data"""
        df_clean = df.copy()
        
        for col in df_clean.columns:
            # Remove leading/trailing whitespaces
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].astype(str).str.strip()
                # Replace empty strings with NaN
                df_clean[col] = df_clean[col].replace(['', 'nan', 'None', 'null'], np.nan)
        
        return df_clean
    

    
    @staticmethod
    def apply_mappings(raw_df: pd.DataFrame, 
                      mappings: Dict[str, Tuple[str, int]],
                      template_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply mappings to create output DataFrame matching template structure
        """
        output_df = pd.DataFrame()
        
        for template_col, (raw_col, confidence) in mappings.items():
            if raw_col is not None and raw_col in raw_df.columns:
                # Copy data from raw to output
                output_df[template_col] = raw_df[raw_col].copy()
                
                # Try to match data type of template
                if template_col in template_df.columns:
                    template_dtype = template_df[template_col].dtype
                    try:
                        if pd.api.types.is_numeric_dtype(template_dtype):
                            output_df[template_col] = pd.to_numeric(
                                output_df[template_col], errors='coerce'
                            )
                        elif pd.api.types.is_datetime64_any_dtype(template_dtype):
                            output_df[template_col] = pd.to_datetime(
                                output_df[template_col], errors='coerce'
                            )
                    except:
                        pass
            else:
                # No mapping found - create empty column
                output_df[template_col] = np.nan
        
        # Clean the output
        output_df = DataTransformer.clean_data(output_df)
        
        return output_df
    
    @staticmethod
    def export_data(df: pd.DataFrame, output_format: str, filename: str) -> bytes:
        """Export DataFrame to specified format"""
        if output_format == "csv":
            return df.to_csv(index=False).encode('utf-8')
        
        elif output_format == "excel":
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Mapped Data')
            return output.getvalue()
        
        elif output_format == "json":
            return df.to_json(orient='records', indent=2).encode('utf-8')
        
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
