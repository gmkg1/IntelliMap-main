import pandas as pd
from rapidfuzz import fuzz, process
from typing import Dict, List, Tuple, Optional, Set
import re
import numpy as np
from scipy.optimize import linear_sum_assignment

class SmartMapper:
    """Intelligent field mapping using fuzzy matching and pattern detection"""
    
    # Common field synonyms for better matching
    FIELD_SYNONYMS = {
        'email': ['email', 'e-mail', 'mail', 'email address', 'electronic mail', 'e mail'],
        'phone': ['phone', 'telephone', 'mobile', 'cell', 'contact number', 'phone number', 'tel', 'contact', 'phone no'],
        'name': ['name', 'full name', 'fullname', 'customer name', 'person name', 'client name'],
        'first_name': ['first name', 'firstname', 'given name', 'fname', 'first'],
        'last_name': ['last name', 'lastname', 'surname', 'family name', 'lname', 'last'],
        'address': ['address', 'street address', 'location', 'addr', 'street', 'address line'],
        'city': ['city', 'town', 'municipality'],
        'state': ['state', 'province', 'region'],
        'zip': ['zip', 'zipcode', 'postal code', 'postcode', 'zip code', 'postal'],
        'country': ['country', 'nation'],
        'date': ['date', 'dt', 'timestamp', 'time', 'datetime'],
        'id': ['id', 'identifier', 'uid', 'unique id', 'record id', 'customer id', 'user id'],
        'amount': ['amount', 'total', 'sum', 'value', 'price', 'cost', 'amt'],
        'quantity': ['quantity', 'qty', 'count', 'number', 'num'],
        'description': ['description', 'desc', 'details', 'notes', 'comments'],
        'status': ['status', 'state', 'condition'],
        'company': ['company', 'organization', 'org', 'business', 'company name'],
        'title': ['title', 'job title', 'position', 'role'],
        'department': ['department', 'dept', 'division'],
        'salary': ['salary', 'wage', 'pay', 'compensation'],
        'age': ['age', 'years old', 'yrs'],
        'gender': ['gender', 'sex'],
        'website': ['website', 'url', 'web', 'site'],
    }
    
    # Common abbreviations
    ABBREVIATIONS = {
        'addr': 'address',
        'qty': 'quantity',
        'desc': 'description',
        'num': 'number',
        'amt': 'amount',
        'dt': 'date',
        'tel': 'telephone',
        'mob': 'mobile',
        'fname': 'first name',
        'lname': 'last name',
        'dob': 'date of birth',
        'ssn': 'social security number',
        'ein': 'employer identification number',
        'org': 'organization',
        'dept': 'department',
        'mgr': 'manager',
        'emp': 'employee',
        'cust': 'customer',
        'prod': 'product',
        'cat': 'category',
        'ref': 'reference',
        'no': 'number',
        'st': 'street',
        'ave': 'avenue',
        'blvd': 'boulevard',
        'dr': 'drive',
        'ln': 'lane',
        'rd': 'road',
        'ct': 'court',
        'pl': 'place',
    }
    
    def __init__(self, similarity_threshold: int = 70):
        self.similarity_threshold = similarity_threshold
    
    def normalize_header(self, header: str) -> str:
        """Normalize header names for better matching"""
        # Convert to lowercase first
        normalized = str(header).lower()
        
        # Convert underscores, hyphens, and dots to spaces (common separators in column names)
        normalized = normalized.replace('_', ' ').replace('-', ' ').replace('.', ' ')
        
        # Remove other special characters
        normalized = re.sub(r'[^a-zA-Z0-9\s]', '', normalized)
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        # Expand abbreviations
        words = normalized.split()
        expanded_words = [self.ABBREVIATIONS.get(word, word) for word in words]
        normalized = ' '.join(expanded_words)
        
        return normalized
    
    def fuzzy_match_headers(self, raw_columns: List[str], 
                           template_columns: List[str]) -> Dict[str, Tuple[str, float]]:
        """
        Match raw data columns to template columns using optimal assignment (Hungarian algorithm)
        This ensures ONE-TO-ONE matching - each raw column maps to at most one template column
        Returns: {template_col: (raw_col, confidence_score)}
        """
        if not raw_columns or not template_columns:
            return {col: (None, 0.0) for col in template_columns}
        
        # Create cost matrix (negative scores for minimization)
        n_template = len(template_columns)
        n_raw = len(raw_columns)
        
        # Initialize cost matrix with very high costs (low scores)
        cost_matrix = np.full((n_template, n_raw), 100.0)
        
        # Calculate match scores for all pairs
        for i, template_col in enumerate(template_columns):
            for j, raw_col in enumerate(raw_columns):
                score = self._calculate_match_score(template_col, raw_col)
                # Convert score to cost (100 - score, so high score = low cost)
                cost_matrix[i, j] = 100.0 - score
        
        # Use Hungarian algorithm for optimal assignment
        template_indices, raw_indices = linear_sum_assignment(cost_matrix)
        
        # Build mappings from assignment
        mappings = {}
        for i, template_col in enumerate(template_columns):
            if i in template_indices:
                # Find which raw column was assigned
                idx = np.where(template_indices == i)[0][0]
                raw_idx = raw_indices[idx]
                raw_col = raw_columns[raw_idx]
                
                # Get the actual score (not cost)
                score = 100.0 - cost_matrix[i, raw_idx]
                
                # Only accept if score meets threshold
                if score >= self.similarity_threshold:
                    mappings[template_col] = (raw_col, score / 100.0)
                else:
                    mappings[template_col] = (None, 0.0)
            else:
                mappings[template_col] = (None, 0.0)
        
        return mappings
    
    def _calculate_match_score(self, template_col: str, raw_col: str) -> float:
        """
        Calculate comprehensive match score between two column names
        Returns score from 0-100
        """
        # Normalize both
        norm_template = self.normalize_header(template_col)
        norm_raw = self.normalize_header(raw_col)
        
        # Exact match after normalization
        if norm_template == norm_raw:
            return 100.0
        
        # Check synonym match FIRST (most reliable)
        synonym_score = self._check_synonym_match(norm_template, norm_raw)
        if synonym_score > 0:
            return synonym_score
        
        # Word-level analysis
        template_words = set(norm_template.split())
        raw_words = set(norm_raw.split())
        
        # STRICT: Both must have words
        if not template_words or not raw_words:
            return 0.0
        
        # Check for exact word matches
        common_words = template_words & raw_words
        
        # If they share ALL words from the shorter name, high confidence
        if template_words and raw_words:
            shorter_set = template_words if len(template_words) <= len(raw_words) else raw_words
            longer_set = raw_words if len(template_words) <= len(raw_words) else template_words
            
            if shorter_set.issubset(longer_set):
                # All words from shorter are in longer
                return 95.0
        
        # Calculate word overlap percentage
        if common_words:
            # Use the MAXIMUM of both sets for denominator (more conservative)
            word_overlap = len(common_words) / max(len(template_words), len(raw_words))
            
            # Require MORE THAN 50% word overlap for any match
            # This prevents "customer id" matching "customer name" (which is exactly 0.5)
            if word_overlap > 0.5:
                # Scale from 70-90 based on overlap
                base_score = 70 + (word_overlap * 20)
                return base_score
        
        # Fuzzy string matching (only if no word overlap)
        # Use token-based matching (better for column names)
        token_sort_score = fuzz.token_sort_ratio(norm_template, norm_raw)
        token_set_score = fuzz.token_set_ratio(norm_template, norm_raw)
        
        # Average of token-based scores
        token_score = (token_sort_score + token_set_score) / 2
        
        # Only return fuzzy score if it's reasonably high (>= 70)
        if token_score >= 70:
            return token_score
        
        # No good match found
        return 0.0
    
    def _check_synonym_match(self, term1: str, term2: str) -> float:
        """Check if two terms are synonyms and return confidence score"""
        # Split terms into words for partial matching
        term1_words = set(term1.split())
        term2_words = set(term2.split())
        
        # Check if both terms appear in the same synonym group
        for category, synonyms in self.FIELD_SYNONYMS.items():
            # Check for exact matches in the synonym list
            term1_exact_match = any(term1 == syn for syn in synonyms)
            term2_exact_match = any(term2 == syn for syn in synonyms)
            
            # If both are exact matches, highest confidence
            if term1_exact_match and term2_exact_match:
                return 95.0
            
            # Check if any word from term1 or term2 matches a synonym
            term1_word_match = any(word in synonyms for word in term1_words)
            term2_word_match = any(word in synonyms for word in term2_words)
            
            # If both contain words from the same synonym group, good match
            # Example: "customer_email" and "email" both contain "email" from email synonyms
            if term1_word_match and term2_word_match:
                # Check if they share the key synonym word
                term1_syn_words = {word for word in term1_words if word in synonyms}
                term2_syn_words = {word for word in term2_words if word in synonyms}
                
                if term1_syn_words & term2_syn_words:  # If they share synonym words
                    return 90.0  # High confidence for partial synonym matches
        
        return 0.0
    
    def detect_data_patterns(self, series: pd.Series) -> str:
        """Detect data type patterns in a column"""
        # Drop empty values first
        sample = series.dropna().astype(str)
        if len(sample) == 0:
            return "text"
            
        sample = sample.head(10)
        
        # Check for email match logic first (most specific)
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if sample.apply(lambda x: bool(re.match(email_pattern, str(x)))).all():
            return "email"
            
        # Check for numeric (including currency)
        # Remove currency symbols and separators
        numeric_clean = sample.apply(lambda x: re.sub(r'[$,£€]', '', str(x)).replace(',', ''))
        try:
            pd.to_numeric(numeric_clean)
            return "numeric"
        except:
            pass
        
        # Check for dates - STRICT CHECK
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # Must actually produce valid dates, not just NaT
                dates = pd.to_datetime(sample, errors='coerce')
            
            # If more than 50% are valid dates, it's a date column
            if dates.notna().sum() > (len(sample) / 2):
                return "date"
        except:
            pass
            
        return "text"
    
    def semantic_pattern_match(self, raw_df: pd.DataFrame, 
                              template_df: pd.DataFrame,
                              mappings: Dict[str, Tuple[str, float]]) -> Dict[str, Tuple[str, float]]:
        """
        Enhance mappings using data pattern detection
        """
        enhanced_mappings = mappings.copy()
        
        # Get patterns for all columns
        raw_patterns = {col: self.detect_data_patterns(raw_df[col]) for col in raw_df.columns}
        template_patterns = {col: self.detect_data_patterns(template_df[col]) 
                           for col in template_df.columns if col in template_df.columns}
        
        # Find unmapped template columns (score < 0.8 means < 80%)
        unmapped_template = [col for col, (match, score) in mappings.items() 
                            if match is None or score < 0.8]
        
        # Find unused raw columns
        mapped_raw = {match for match, score in mappings.values() if match is not None}
        unused_raw = [col for col in raw_df.columns if col not in mapped_raw]
        
        # Try to match based on patterns
        for template_col in unmapped_template:
            if template_col not in template_patterns:
                continue
                
            template_pattern = template_patterns[template_col]
            
            # Skip generic text matches to avoid bad guesses
            if template_pattern == "text":
                continue
            
            for i, raw_col in enumerate(unused_raw):
                raw_pattern = raw_patterns[raw_col]
                
                # Strict pattern matching
                if template_pattern == raw_pattern:
                    # Found a match!
                    current_score = enhanced_mappings[template_col][1]
                    
                    # Only override if we are sure (same pattern)
                    if current_score < 0.6:
                        enhanced_mappings[template_col] = (raw_col, 0.6)  # 60% confidence
                        
                        # CRITICAL: Mark this raw column as used so it isn't used again!
                        unused_raw.pop(i)
                        break
        
        return enhanced_mappings
        
    def _detect_value_contamination(self, df: pd.DataFrame, sample_size: int = 100) -> Dict[str, List[str]]:
        """
        Detect if values from one column appear in other columns, which could indicate data quality issues.
        
        Args:
            df: Input DataFrame to analyze
            sample_size: Number of values to sample from each column (for performance)
            
        Returns:
            Dictionary mapping column names to lists of other columns that share values with it
        """
        contamination = {}
            
        # Convert all values to strings and take a sample for comparison
        str_samples = {}
        for col in df.columns:
            # Skip columns with too many unique values (like IDs)
            if df[col].nunique() > len(df) * 0.9:  # Skip if >90% unique
                continue
                
            # Convert to string and take sample
            sample = df[col].dropna().astype(str).sample(min(sample_size, len(df[col])))
            if len(sample) > 0:
                str_samples[col] = set(sample)
        
        # Compare all pairs of columns
        columns = list(str_samples.keys())
        for i, col1 in enumerate(columns):
            for col2 in columns[i+1:]:
                # Check for overlapping values
                common = str_samples[col1] & str_samples[col2]
                if len(common) > 0:
                    # Calculate overlap percentage (of the smaller column)
                    overlap_pct = len(common) / min(len(str_samples[col1]), len(str_samples[col2]))
                    
                    # Only report significant overlaps (>10%)
                    if overlap_pct > 0.1:
                        if col1 not in contamination:
                            contamination[col1] = []
                        contamination[col1].append(f"{col2} ({int(overlap_pct*100)}% overlap)")
                        
                        if col2 not in contamination:
                            contamination[col2] = []
                        contamination[col2].append(f"{col1} ({int(overlap_pct*100)}% overlap)")
        
        return contamination
        

