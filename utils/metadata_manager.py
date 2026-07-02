import json
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import hashlib

class MetadataManager:
    """
    Manages mapping metadata without storing actual user data.
    Only stores column mappings, transformations, and statistics.
    """
    
    def __init__(self):
        self.metadata = {
            'version': '1.0',
            'created_at': None,
            'last_updated': None,
            'mappings': {},
            'statistics': {},
            'validation_rules': {}
        }
    
    def create_metadata(self, 
                       raw_columns: List[str],
                       template_columns: List[str],
                       mappings: Dict[str, Tuple[Optional[str], float]],
                       raw_df_stats: Dict[str, Any],
                       template_df_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create metadata from mapping session without storing actual data.
        
        Args:
            raw_columns: List of raw data column names
            template_columns: List of template column names
            mappings: Column mappings {template_col: (raw_col, confidence)}
            raw_df_stats: Statistics about raw data (no actual values)
            template_df_stats: Statistics about template (no actual values)
        
        Returns:
            Metadata dictionary
        """
        timestamp = datetime.now().isoformat()
        
        self.metadata = {
            'version': '1.0',
            'created_at': timestamp,
            'last_updated': timestamp,
            'source_fingerprint': self._generate_fingerprint(raw_columns),
            'template_fingerprint': self._generate_fingerprint(template_columns),
            'mappings': self._serialize_mappings(mappings),
            'statistics': {
                'raw_data': raw_df_stats,
                'template': template_df_stats,
                'mapping_quality': self._calculate_mapping_quality(mappings)
            },
            'column_info': {
                'raw_columns': raw_columns,
                'template_columns': template_columns,
                'mapped_count': sum(1 for _, (col, _) in mappings.items() if col is not None),
                'unmapped_count': sum(1 for _, (col, _) in mappings.items() if col is None)
            }
        }
        
        return self.metadata
    
    def _generate_fingerprint(self, columns: List[str]) -> str:
        """Generate a unique fingerprint for column structure (not data)"""
        column_str = '|'.join(sorted(columns))
        return hashlib.md5(column_str.encode()).hexdigest()
    
    def _serialize_mappings(self, mappings: Dict[str, Tuple[Optional[str], float]]) -> Dict[str, Dict]:
        """Convert mappings to serializable format"""
        serialized = {}
        for template_col, (raw_col, confidence) in mappings.items():
            serialized[template_col] = {
                'source_column': raw_col,
                'confidence_score': float(confidence) if confidence else 0.0,
                'mapping_type': 'automatic' if confidence and confidence >= 80 else 'manual'
            }
        return serialized
    
    def _calculate_mapping_quality(self, mappings: Dict[str, Tuple[Optional[str], float]]) -> Dict[str, Any]:
        """Calculate overall mapping quality metrics"""
        total = len(mappings)
        if total == 0:
            return {'overall_score': 0, 'completeness': 0, 'confidence': 0}
        
        mapped = sum(1 for _, (col, _) in mappings.items() if col is not None)
        high_confidence = sum(1 for _, (col, conf) in mappings.items() if col and conf >= 80)
        avg_confidence = sum(conf for _, (col, conf) in mappings.items() if col) / mapped if mapped > 0 else 0
        
        return {
            'overall_score': (mapped / total) * 100,
            'completeness': (mapped / total) * 100,
            'average_confidence': avg_confidence,
            'high_confidence_mappings': high_confidence,
            'total_mappings': total,
            'successful_mappings': mapped
        }
    
    def export_metadata(self) -> str:
        """Export metadata as JSON string"""
        return json.dumps(self.metadata, indent=2)
    
    def import_metadata(self, metadata_json: str) -> Dict[str, Any]:
        """Import metadata from JSON string"""
        self.metadata = json.loads(metadata_json)
        return self.metadata
    
    def get_reusable_mappings(self) -> Dict[str, str]:
        """
        Extract reusable mappings that can be applied to similar data structures.
        Returns only the column name mappings, no data.
        """
        if 'mappings' not in self.metadata:
            return {}
        
        reusable = {}
        for template_col, mapping_info in self.metadata['mappings'].items():
            if mapping_info['source_column']:
                reusable[template_col] = mapping_info['source_column']
        
        return reusable
    
    def validate_compatibility(self, raw_columns: List[str], template_columns: List[str]) -> Dict[str, Any]:
        """
        Check if current metadata is compatible with new data structure.
        Returns compatibility report without accessing actual data.
        """
        current_raw_fp = self._generate_fingerprint(raw_columns)
        current_template_fp = self._generate_fingerprint(template_columns)
        
        stored_raw_fp = self.metadata.get('source_fingerprint', '')
        stored_template_fp = self.metadata.get('template_fingerprint', '')
        
        return {
            'is_compatible': (current_raw_fp == stored_raw_fp and 
                            current_template_fp == stored_template_fp),
            'raw_structure_match': current_raw_fp == stored_raw_fp,
            'template_structure_match': current_template_fp == stored_template_fp,
            'can_reuse_mappings': current_template_fp == stored_template_fp,
            'recommendation': self._get_compatibility_recommendation(
                current_raw_fp == stored_raw_fp,
                current_template_fp == stored_template_fp
            )
        }
    
    def _get_compatibility_recommendation(self, raw_match: bool, template_match: bool) -> str:
        """Provide recommendation based on compatibility"""
        if raw_match and template_match:
            return "Perfect match! You can reuse all mappings."
        elif template_match and not raw_match:
            return "Template matches. You can reuse mappings, but verify raw data compatibility."
        elif not template_match and raw_match:
            return "Raw data structure matches, but template is different. New mapping required."
        else:
            return "Different data structure detected. New mapping recommended."
    
    def get_mapping_summary(self) -> str:
        """Get human-readable summary of mappings"""
        if not self.metadata.get('mappings'):
            return "No mappings available."
        
        quality = self.metadata.get('statistics', {}).get('mapping_quality', {})
        col_info = self.metadata.get('column_info', {})
        
        summary = f"""
Mapping Summary:
================
Created: {self.metadata.get('created_at', 'Unknown')}
Last Updated: {self.metadata.get('last_updated', 'Unknown')}

Columns:
- Raw Data Columns: {len(col_info.get('raw_columns', []))}
- Template Columns: {len(col_info.get('template_columns', []))}
- Successfully Mapped: {col_info.get('mapped_count', 0)}
- Unmapped: {col_info.get('unmapped_count', 0)}

Quality Metrics:
- Completeness: {quality.get('completeness', 0):.1f}%
- Average Confidence: {quality.get('average_confidence', 0):.1f}%
- High Confidence Mappings: {quality.get('high_confidence_mappings', 0)}
        """
        
        return summary.strip()
