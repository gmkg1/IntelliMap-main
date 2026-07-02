import pandas as pd
import json
from typing import Union, Dict, Any

class DataReader:
    """Handles reading different file formats"""
    
    @staticmethod
    def read_file(file) -> pd.DataFrame:
        """
        Read uploaded file and return as DataFrame
        Supports: CSV, Excel (xlsx, xls), JSON
        """
        filename = file.name.lower()
        
        try:
            if filename.endswith('.csv'):
                last_error = None
                for encoding in ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']:
                    try:
                        file.seek(0)
                        df = pd.read_csv(file, encoding=encoding)
                        break
                    except Exception as e:
                        last_error = e
                        continue
                else:
                    if last_error:
                        raise last_error
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file, engine='openpyxl' if filename.endswith('.xlsx') else None)
            elif filename.endswith('.json'):
                file.seek(0)
                content = file.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8-sig', errors='replace')
                data = json.loads(content)
                # Handle different JSON structures
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                elif isinstance(data, dict):
                    # If dict has list values, convert to DataFrame
                    if any(isinstance(v, list) for v in data.values()):
                        df = pd.DataFrame(data)
                    else:
                        # Single record
                        df = pd.DataFrame([data])
                else:
                    raise ValueError("Unsupported JSON structure")
            else:
                raise ValueError(f"Unsupported file format: {filename}")
            
            return df
        except Exception as e:
            raise Exception(f"Error reading file {filename}: {str(e)}")
    
    @staticmethod
    def get_schema(df: pd.DataFrame) -> Dict[str, Any]:
        """Extract schema information from DataFrame"""
        schema = {}
        for col in df.columns:
            schema[col] = {
                'dtype': str(df[col].dtype),
                'null_count': int(df[col].isnull().sum()),
                'sample_values': df[col].dropna().head(3).tolist()
            }
        return schema
