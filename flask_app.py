import os
import sys
import uuid
import json
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import logging
from utils.data_reader import DataReader
from utils.mapper import SmartMapper
from utils.transformer import DataTransformer
from utils.metadata_manager import MetadataManager

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session_management_replace_in_prod'
UPLOAD_FOLDER = 'temp_uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Audit Logging
audit_logger = logging.getLogger('audit_logger')
audit_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('audit_logs.txt')
formatter = logging.Formatter('%(asctime)s - USER: [%(username)s] - ACTION: %(message)s')
file_handler.setFormatter(formatter)
audit_logger.addHandler(file_handler)

# Similarity threshold (optimal value from Streamlit app)
SIMILARITY_THRESHOLD = 70

def get_session_dir():
    """Get or create a unique directory for the current user session's files."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session['session_id'])
    os.makedirs(session_dir, exist_ok=True)
    return session_dir

def read_uploaded_file(file_path):
    """Utility to read a file using the existing DataReader logic."""
    reader = DataReader()
    # The file object returned by open() has a .name attribute (the file path),
    # which DataReader uses to determine the file type.
    with open(file_path, 'rb') as f:
        return reader.read_file(f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

def process_mapped_files(raw_path, template_path, raw_filename, template_filename, username):
    # Audit Log
    audit_logger.info(f"Uploaded files '{raw_filename}' and '{template_filename}' for auto-mapping", extra={'username': username})
    
    # Process the files
    try:
        raw_df = read_uploaded_file(raw_path)
        template_df = read_uploaded_file(template_path)
        
        mapper = SmartMapper(similarity_threshold=SIMILARITY_THRESHOLD)
        
        # Initial fuzzy matching
        mappings = mapper.fuzzy_match_headers(
            raw_df.columns.tolist(),
            template_df.columns.tolist()
        )
        
        # Enhance with pattern matching
        mappings = mapper.semantic_pattern_match(
            raw_df,
            template_df,
            mappings
        )
        
        contamination_info = mapper._detect_value_contamination(raw_df)
        
        # Get data patterns for each column
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
        return jsonify({'error': 'Missing files'}), 400
        
    raw_file = request.files['raw_file']
    template_file = request.files['template_file']
    username = request.form.get('username', 'Unknown')
    
    if raw_file.filename == '' or template_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    session_dir = get_session_dir()
    
    raw_filename = secure_filename(raw_file.filename)
    template_filename = secure_filename(template_file.filename)
    
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
    username = data.get('username', 'Unknown')
    
    if not raw_filename or not template_filename:
        return jsonify({'error': 'Missing files'}), 400
        
    session_dir = get_session_dir()
    
    raw_path = os.path.join(session_dir, 'raw_' + secure_filename(raw_filename))
    template_path = os.path.join(session_dir, 'template_' + secure_filename(template_filename))
    
    if not os.path.exists(raw_path) or not os.path.exists(template_path):
        return jsonify({'error': 'Selected files not found on server session directory'}), 404
        
    return process_mapped_files(raw_path, template_path, raw_filename, template_filename, username)

@app.route('/transform', methods=['POST'])
def transform_data():
    data = request.json
    adjusted_mappings = data.get('mappings')
    output_format = data.get('output_format', 'csv')
    raw_filename = data.get('raw_filename')
    template_filename = data.get('template_filename')
    username = data.get('username', 'Unknown')
    
    if not adjusted_mappings or not raw_filename or not template_filename:
        return jsonify({'error': 'Missing data for transformation'}), 400
        
    session_dir = get_session_dir()
    raw_path = os.path.join(session_dir, 'raw_' + secure_filename(raw_filename))
    template_path = os.path.join(session_dir, 'template_' + secure_filename(template_filename))
    
    try:
        raw_df = read_uploaded_file(raw_path)
        template_df = read_uploaded_file(template_path)
        
        transformer = DataTransformer()
        output_df = transformer.apply_mappings(
            raw_df,
            adjusted_mappings,
            template_df
        )
        
        # Export the file
        output_filename = f"mapped_data.{output_format if output_format != 'excel' else 'xlsx'}"
        output_path = os.path.join(session_dir, output_filename)
        
        file_data = transformer.export_data(
            output_df,
            output_format,
            output_filename
        )
        
        # transformer.export_data returns bytes. We need to save it to a file to send it, 
        # or we can send it directly from memory. Let's write to file since Flask's send_file works well with files.
        with open(output_path, 'wb') as f:
            f.write(file_data)
            
        # Audit Log
        audit_logger.info(f"Transformed data and exported as '{output_filename}'", extra={'username': username})
            
        return jsonify({
            'success': True,
            'download_url': f'/download/{session["session_id"]}/{output_filename}',
            'stats': {
                'total_rows': len(output_df),
                'total_columns': len(output_df.columns),
                'completeness': (1 - output_df.isnull().sum().sum() / (output_df.shape[0] * output_df.shape[1])) * 100
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<session_id>/<filename>')
def download_file(session_id, filename):
    # Ensure we use a safe version of session_id and filename
    safe_session_id = secure_filename(session_id)
    safe_filename = secure_filename(filename)
    
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], safe_session_id)
    file_path = os.path.join(session_dir, safe_filename)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True)
