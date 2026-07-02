import webview
import os
import shutil
from pathlib import Path
from flask_app import app

class Api:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def select_file_native(self, session_id, file_type):
        """Opens a native open file dialog, copies the file to session_dir, and returns the filename."""
        from werkzeug.utils import secure_filename
        safe_session_id = secure_filename(session_id)
        
        file_types = (
            'Supported files (*.xlsx;*.xls;*.csv;*.json)',
            'Excel files (*.xlsx;*.xls)',
            'CSV files (*.csv)',
            'JSON files (*.json)',
            'All files (*.*)'
        )
        
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=file_types
        )
        
        if result:
            file_path = result[0] if isinstance(result, (tuple, list)) else result
            if file_path and os.path.exists(file_path):
                original_filename = os.path.basename(file_path)
                safe_filename = secure_filename(original_filename)
                
                # Copy to the session directory
                session_dir = os.path.join('temp_uploads', safe_session_id)
                os.makedirs(session_dir, exist_ok=True)
                
                prefix = 'raw_' if file_type == 'raw' else 'template_'
                dest_filename = prefix + safe_filename
                dest_path = os.path.join(session_dir, dest_filename)
                
                try:
                    shutil.copy(file_path, dest_path)
                    return {
                        "success": True,
                        "filename": original_filename,
                        "saved_name": dest_filename
                    }
                except Exception as e:
                    return {"success": False, "error": str(e)}
                    
        return {"success": False, "error": "User cancelled the file dialog"}

    def save_file_native(self, session_id, filename):
        """Opens a native save dialog and copies the file to the chosen location."""
        # Clean session_id and filename to avoid path traversal
        from werkzeug.utils import secure_filename
        safe_session_id = secure_filename(session_id)
        safe_filename = secure_filename(filename)
        
        source_path = os.path.join('temp_uploads', safe_session_id, safe_filename)
        if not os.path.exists(source_path):
            return {"success": False, "error": f"File not found: {source_path}"}
        
        # Suggested location: Downloads folder
        downloads_path = str(Path.home() / "Downloads")
        
        # Set file_types based on extension
        ext = os.path.splitext(safe_filename)[1].lower()
        if ext == '.csv':
            file_types = ('CSV files (*.csv)', 'All files (*.*)')
        elif ext == '.json':
            file_types = ('JSON files (*.json)', 'All files (*.*)')
        elif ext in ('.xlsx', '.xls'):
            file_types = ('Excel files (*.xlsx;*.xls)', 'All files (*.*)')
        else:
            file_types = ('All files (*.*)',)
            
        # Open the native save dialog
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG, 
            directory=downloads_path, 
            save_filename=safe_filename,
            file_types=file_types
        )
        
        if result:
            # result is a tuple, unpack it
            save_path = result[0] if isinstance(result, (tuple, list)) else result
            try:
                shutil.copy(source_path, save_path)
                return {"success": True, "path": save_path}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "User cancelled the save dialog"}

if __name__ == '__main__':
    api = Api()
    
    # Create a native window pointing to the local Flask application
    window = webview.create_window(
        'IntelliMap Workspace', 
        app,
        js_api=api,
        width=1280,
        height=800,
        min_size=(800, 600)
    )
    
    api.set_window(window)
    
    # Start the PyWebView event loop
    webview.start()
