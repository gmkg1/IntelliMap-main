import pandas as pd
import json
import os
from typing import Union, Dict, Any

class DataReader:
    """Handles reading different file formats (CSV, Excel, JSON)"""
    
    @staticmethod
    def read_file(file, filename_hint: str = None) -> pd.DataFrame:
        """
        Read uploaded file or file path and return as DataFrame.
        Supports: CSV (comma, semi, tab), Excel (.xlsx, .xls), and multi-structure JSON.
        """
        # Determine filename
        if isinstance(file, str):
            filename = file.lower()
            file_obj = open(file, 'rb')
            should_close = True
        else:
            filename = getattr(file, 'name', '') or filename_hint or ''
            filename = filename.lower()
            file_obj = file
            should_close = False

        try:
            if filename.endswith('.csv'):
                df = DataReader._read_csv(file_obj)
            elif filename.endswith(('.xlsx', '.xlsm')):
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                df = pd.read_excel(file_obj, engine='openpyxl')
            elif filename.endswith('.xls'):
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                try:
                    df = pd.read_excel(file_obj, engine='xlrd')
                except Exception:
                    # Fallback to default engine
                    if hasattr(file_obj, 'seek'):
                        file_obj.seek(0)
                    df = pd.read_excel(file_obj)
            elif filename.endswith('.json'):
                df = DataReader._read_json(file_obj)
            else:
                # Try auto-detecting by extension or content
                ext = os.path.splitext(filename)[1].lower() if filename else ''
                if ext in ['.csv', '.txt']:
                    df = DataReader._read_csv(file_obj)
                elif ext in ['.xlsx', '.xls', '.xlsm']:
                    if hasattr(file_obj, 'seek'):
                        file_obj.seek(0)
                    df = pd.read_excel(file_obj)
                elif ext == '.json':
                    df = DataReader._read_json(file_obj)
                else:
                    raise ValueError(f"Unsupported file format: '{filename}'. Please provide a .csv, .xlsx, .xls, or .json file.")

            # Ensure all column names are strings and stripped
            df.columns = [str(col).strip() for col in df.columns]
            return df
        finally:
            if should_close:
                file_obj.close()

    @staticmethod
    def _read_csv(file_obj) -> pd.DataFrame:
        """Read CSV with encoding detection and delimiter sniffing"""
        last_error = None
        encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']
        
        for encoding in encodings:
            try:
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                df = pd.read_csv(file_obj, encoding=encoding)
                
                # Check if entire row was packed into a single column due to non-comma delimiter (; or \t)
                if len(df.columns) == 1 and any(delim in str(df.columns[0]) for delim in [';', '\t', '|']):
                    if hasattr(file_obj, 'seek'):
                        file_obj.seek(0)
                    df = pd.read_csv(file_obj, sep=None, engine='python', encoding=encoding)
                return df
            except Exception as e:
                last_error = e
                continue
                
        # Try delimiter sniffer as final fallback
        for encoding in encodings:
            try:
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                return pd.read_csv(file_obj, sep=None, engine='python', encoding=encoding)
            except Exception:
                continue

        if last_error:
            raise last_error
        raise ValueError("Unable to parse CSV file with supported encodings.")

    @staticmethod
    def _read_json(file_obj) -> pd.DataFrame:
        """Read JSON supporting arrays, wrapped objects, NDJSON, and nested structures"""
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
            
        content = file_obj.read()
        if isinstance(content, bytes):
            for encoding in ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']:
                try:
                    content_str = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                content_str = content.decode('utf-8', errors='replace')
        else:
            content_str = str(content)

        content_str = content_str.strip()
        if not content_str:
            return pd.DataFrame()

        # 1. Try standard JSON parsing
        try:
            data = json.loads(content_str)
        except json.JSONDecodeError:
            # Try JSON Lines (NDJSON)
            lines = [line.strip() for line in content_str.splitlines() if line.strip()]
            try:
                records = [json.loads(line) for line in lines]
                return pd.json_normalize(records)
            except Exception as e:
                raise ValueError(f"Invalid JSON format: {str(e)}")

        # 2. Convert parsed JSON data to DataFrame based on structure
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                return pd.json_normalize(data)
            return pd.DataFrame(data)

        elif isinstance(data, dict):
            # Check for common wrapper keys like data, records, items, results, rows, etc.
            common_keys = [
                'data', 'records', 'items', 'results', 'rows', 
                'payload', 'elements', 'users', 'clients', 'customers', 
                'entities', 'list', 'entries'
            ]
            for key in common_keys:
                if key in data and isinstance(data[key], list) and len(data[key]) > 0 and isinstance(data[key][0], dict):
                    return pd.json_normalize(data[key])

            # Check if there is exactly one key whose value is a list of dicts
            list_of_dict_keys = [
                k for k, v in data.items() 
                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict)
            ]
            if len(list_of_dict_keys) == 1:
                return pd.json_normalize(data[list_of_dict_keys[0]])

            # Check if dict represents columnar data: {"col1": [1, 2], "col2": [3, 4]}
            if all(isinstance(v, list) for v in data.values()) and len(data.values()) > 0:
                return pd.DataFrame(data)

            # Single record object: {"id": 1, "name": "Alice"}
            return pd.json_normalize([data])

        else:
            raise ValueError("Unsupported JSON root structure (expected array or object).")

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

