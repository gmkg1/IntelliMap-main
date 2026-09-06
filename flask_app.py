import os
import sys
import uuid
import json
import logging
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
from utils.data_reader import DataReader
from utils.mapper import SmartMapper
from utils.transformer import DataTransformer
from utils.metadata_manager import MetadataManager

import tempfile

base_dir = os.path.dirname(os.path.abspath(__file__))
template_folder = os.path.join(base_dir, 'templates')
static_folder = os.path.join(base_dir, 'static')

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_for_session_management_replace_in_prod')

# In serverless environments like Vercel, the filesystem is read-only except for /tmp
is_serverless = bool(os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
if is_serverless:
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'temp_uploads')
else:
    UPLOAD_FOLDER = os.path.join(base_dir, 'temp_uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max file upload

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Audit Logging: Always log to console (visible in Vercel logs), plus file if writable
audit_logger = logging.getLogger('audit_logger')
audit_logger.setLevel(logging.INFO)
if not audit_logger.handlers:
    formatter = logging.Formatter('%(asctime)s - USER: [%(username)s] - ACTION: %(message)s')
    
    # Console output for Vercel/Cloud log stream
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    audit_logger.addHandler(console_handler)
    
    try:
        log_file = os.path.join(tempfile.gettempdir() if is_serverless else base_dir, 'audit_logs.txt')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        audit_logger.addHandler(file_handler)
    except Exception as e:
        pass

# Similarity threshold (optimal value for field matching)
SIMILARITY_THRESHOLD = 70

def get_safe_filename(filename: str, default_prefix: str = 'file') -> str:
    """Safely sanitize filename while preserving original extension and handling unicode."""
    if not filename:
        return f"{default_prefix}_{uuid.uuid4().hex[:8]}.csv"
    base, ext = os.path.splitext(filename)
    safe_base = secure_filename(base)
    safe_ext = ext.lower().strip()
    if not safe_base:
        safe_base = f"{default_prefix}_{uuid.uuid4().hex[:8]}"
    return f"{safe_base}{safe_ext}"

def get_session_dir():
    """Get or create a unique directory for the current user session's files."""
    if 'session_id' not in session or not session['session_id']:
        session['session_id'] = str(uuid.uuid4())
    
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
    os.makedirs(session_dir, exist_ok=True)
    return session_dir

def read_uploaded_file(file_path):
    """Read a file using the robust DataReader logic."""
    reader = DataReader()
    return reader.read_file(file_path)

@app.before_request
def ensure_session():
    """Ensure every user session has a unique session_id immediately."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

def process_mapped_files(raw_path, template_path, raw_filename, template_filename, username):
    # Audit Log
    try:
        audit_logger.info(
            f"Uploaded files '{raw_filename}' and '{template_filename}' for auto-mapping", 
            extra={'username': username}
        )
    except Exception:
        pass
    
    # Process the files
    try:
        raw_df = read_uploaded_file(raw_path)
        template_df = read_uploaded_file(template_path)
        
        if raw_df.empty and len(raw_df.columns) == 0:
            return jsonify({'error': 'Raw data file contains no columns or data.'}), 400
        if template_df.empty and len(template_df.columns) == 0:
            return jsonify({'error': 'Template file contains no columns or data.'}), 400

        mapper = SmartMapper(similarity_threshold=SIMILARITY_THRESHOLD)
        
        # Initial fuzzy & synonym matching with Hungarian Algorithm
        mappings = mapper.fuzzy_match_headers(
            raw_df.columns.tolist(),
            template_df.columns.tolist()
        )
        
        # Enhance with semantic pattern matching
        mappings = mapper.semantic_pattern_match(
            raw_df,
            template_df,
            mappings
        )
        
        # Detect value contamination safely
        contamination_info = mapper._detect_value_contamination(raw_df)
        
        # Detect data patterns for each raw column
        data_patterns = {col: mapper.detect_data_patterns(raw_df[col]) for col in raw_df.columns}

        return jsonify({
            'success': True,
            'mappings': mappings,
            'raw_columns': raw_df.columns.tolist(),
            'template_columns': template_df.columns.tolist(),
            'contamination_info': contamination_info,
            'data_patterns': data_patterns,
            'raw_filename': raw_filename,
            'template_filename': template_filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'raw_file' not in request.files or 'template_file' not in request.files:
        return jsonify({'error': 'Missing raw data or template file.'}), 400
        
    raw_file = request.files['raw_file']
    template_file = request.files['template_file']
    username = request.form.get('username', '').strip() or 'Pitch Demo'
    
    if raw_file.filename == '' or template_file.filename == '':
        return jsonify({'error': 'No file selected. Please select both files.'}), 400

    session_dir = get_session_dir()
    
    raw_filename = get_safe_filename(raw_file.filename, 'raw')
    template_filename = get_safe_filename(template_file.filename, 'template')
    
    raw_path = os.path.join(session_dir, 'raw_' + raw_filename)
    template_path = os.path.join(session_dir, 'template_' + template_filename)
    
    raw_file.save(raw_path)
    template_file.save(template_path)
    
    return process_mapped_files(raw_path, template_path, raw_filename, template_filename, username)

@app.route('/upload_native', methods=['POST'])
def upload_native():
    data = request.json or {}
    raw_filename = data.get('raw_filename')
    template_filename = data.get('template_filename')
    username = data.get('username', '').strip() or 'Pitch Demo'
    
    if not raw_filename or not template_filename:
        return jsonify({'error': 'Missing files'}), 400
        
    session_dir = get_session_dir()
    
    safe_raw = get_safe_filename(raw_filename, 'raw')
    safe_template = get_safe_filename(template_filename, 'template')
    
    raw_path = os.path.join(session_dir, 'raw_' + safe_raw)
    template_path = os.path.join(session_dir, 'template_' + safe_template)
    
    if not os.path.exists(raw_path) or not os.path.exists(template_path):
        return jsonify({'error': 'Selected files not found in session directory.'}), 404
        
    return process_mapped_files(raw_path, template_path, safe_raw, safe_template, username)

@app.route('/transform', methods=['POST'])
def transform_data():
    data = request.json or {}
    adjusted_mappings = data.get('mappings')
    output_format = str(data.get('output_format', 'excel')).lower().strip()
    raw_filename = data.get('raw_filename')
    template_filename = data.get('template_filename')
    username = data.get('username', '').strip() or 'Pitch Demo'
    
    if not adjusted_mappings or not raw_filename or not template_filename:
        return jsonify({'error': 'Missing required transformation parameters.'}), 400
        
    session_dir = get_session_dir()
    safe_raw = get_safe_filename(raw_filename, 'raw')
    safe_template = get_safe_filename(template_filename, 'template')
    
    raw_path = os.path.join(session_dir, 'raw_' + safe_raw)
    template_path = os.path.join(session_dir, 'template_' + safe_template)
    
    if not os.path.exists(raw_path) or not os.path.exists(template_path):
        return jsonify({'error': 'Uploaded files were not found for this session. Please re-upload.'}), 404
        
    try:
        raw_df = read_uploaded_file(raw_path)
        template_df = read_uploaded_file(template_path)
        
        transformer = DataTransformer()
        output_df = transformer.apply_mappings(
            raw_df,
            adjusted_mappings,
            template_df
        )
        
        # Determine extension based on chosen format
        if output_format in ['excel', 'xlsx', 'xls']:
            ext = 'xlsx'
            export_fmt = 'excel'
        elif output_format == 'json':
            ext = 'json'
            export_fmt = 'json'
        else:
            ext = 'csv'
            export_fmt = 'csv'

        output_filename = f"mapped_data.{ext}"
        output_path = os.path.join(session_dir, output_filename)
        
        file_data = transformer.export_data(
            output_df,
            export_fmt,
            output_filename
        )
        
        with open(output_path, 'wb') as f:
            f.write(file_data)
            
        # Audit Log
        try:
            audit_logger.info(
                f"Transformed data and exported as '{output_filename}'", 
                extra={'username': username}
            )
        except Exception:
            pass

        # Calculate completeness safely (guard against 0 cells)
        total_cells = output_df.shape[0] * output_df.shape[1]
        completeness = (1.0 - (output_df.isnull().sum().sum() / total_cells)) * 100.0 if total_cells > 0 else 100.0

        # Generate preview (first 5 rows converted to JSON-serializable records)
        preview_df = output_df.head(5).fillna('')
        preview_data = preview_df.to_dict(orient='records')
        preview_columns = output_df.columns.tolist()

        return jsonify({
            'success': True,
            'download_url': f'/download/{session["session_id"]}/{output_filename}',
            'stats': {
                'total_rows': int(len(output_df)),
                'total_columns': int(len(output_df.columns)),
                'completeness': round(completeness, 1)
            },
            'preview': {
                'columns': preview_columns,
                'rows': preview_data
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<session_id>/<filename>')
def download_file(session_id, filename):
    safe_session_id = secure_filename(session_id)
    safe_filename = secure_filename(filename)
    
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], safe_session_id)
    file_path = os.path.join(session_dir, safe_filename)
    
    # Path traversal protection
    real_path = os.path.realpath(file_path)
    real_upload = os.path.realpath(app.config['UPLOAD_FOLDER'])
    if not real_path.startswith(real_upload):
        return "Access denied", 403
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=safe_filename)
    return "File not found", 404

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1']
    app.run(host=host, port=port, debug=debug)
