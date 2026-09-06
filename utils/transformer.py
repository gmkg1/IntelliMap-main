import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, Any, Union
import io
import re

class DataTransformer:
    """Handles data transformation, cleaning, and export"""
    
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize data while preserving original scalar types"""
        df_clean = df.copy()
        
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
                df_clean[col] = df_clean[col].replace(['', 'nan', 'None', 'null', 'NULL', 'N/A', 'n/a', 'NoneType'], np.nan)
        
        return df_clean

    @staticmethod
    def apply_mappings(raw_df: pd.DataFrame, 
                       mappings: Dict[str, Any],
                       template_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply mappings to create output DataFrame matching template structure.
        Preserves row counts and accurately casts data types (including currency/numeric).
        """
        # Ensure row index matches raw_df
        n_rows = len(raw_df)
        output_df = pd.DataFrame(index=range(n_rows))
        
        for template_col, mapping_val in mappings.items():
            # Extract raw column name whether mapping_val is (col, conf), [col, conf], or col
            if isinstance(mapping_val, (list, tuple)) and len(mapping_val) > 0:
                raw_col = mapping_val[0]
            else:
                raw_col = mapping_val

            if raw_col is not None and raw_col in raw_df.columns:
                # Handle potential duplicate column names in raw_df
                source = raw_df[raw_col]
                if isinstance(source, pd.DataFrame):
                    source = source.iloc[:, 0]
                
                output_series = source.copy().reset_index(drop=True)
                
                # Check target type from template
                if template_col in template_df.columns:
                    template_dtype = template_df[template_col].dtype
                    try:
                        if pd.api.types.is_numeric_dtype(template_dtype):
                            # First try direct conversion
                            converted = pd.to_numeric(output_series, errors='coerce')
                            # If conversion created many NaNs, clean currency, commas, percentages
                            if converted.isna().sum() > output_series.isna().sum():
                                cleaned_str = output_series.astype(str).str.replace(r'[$,£€%\s]', '', regex=True).str.replace(',', '')
                                cleaned_converted = pd.to_numeric(cleaned_str, errors='coerce')
                                if cleaned_converted.notna().sum() >= converted.notna().sum():
                                    converted = cleaned_converted
                            output_series = converted
                        elif pd.api.types.is_datetime64_any_dtype(template_dtype):
                            output_series = pd.to_datetime(output_series, errors='coerce')
                    except Exception:
                        pass

                output_df[template_col] = output_series
            else:
                # No mapping found - create empty column
                output_df[template_col] = np.nan
        
        # Clean and normalize the output
        output_df = DataTransformer.clean_data(output_df)
        return output_df
    
    @staticmethod
    def export_data(df: pd.DataFrame, output_format: str, filename: str = None) -> bytes:
        """Export DataFrame to specified format (CSV with BOM, Excel with auto-width, or clean JSON)"""
        fmt = str(output_format).lower().strip()
        
        if fmt in ["csv", "txt"]:
            # utf-8-sig includes the UTF-8 BOM so Excel opens international characters without mojibake
            return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        
        elif fmt in ["excel", "xlsx", "xls"]:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Mapped Data')
                
                # Auto-adjust column widths for presentation-grade Excel exports
                worksheet = writer.sheets['Mapped Data']
                for i, col in enumerate(df.columns):
                    col_str_len = max(
                        df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                        len(str(col))
                    )
                    worksheet.set_column(i, i, min(col_str_len + 4, 60))
            return output.getvalue()
        
        elif fmt == "json":
            return df.to_json(orient='records', indent=2, date_format='iso').encode('utf-8')
        
        else:
            raise ValueError(f"Unsupported output format: '{output_format}'. Supported formats: CSV, Excel, JSON.")

