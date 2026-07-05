import pandas as pd
from typing import List, Dict, Optional, Union
import re
import os
from pathlib import Path
from config import settings
from analysis import ProteinAnalyzer
from fasta_parser import FASTAParser

class ProteinMatcher:
    def __init__(self):
        self.analyzer = ProteinAnalyzer()
        
    def is_uniprot_id(self, query: str) -> bool:
        """Check if query looks like a UniProt ID"""
        query = query.strip().upper()
        
        patterns = [
            r'^[OPQ][0-9][A-Z0-9]{3}[0-9]$',
            r'^[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9]$',
            r'^[A-NR-Z][0-9][A-Z][A-Z0-9]{3}[0-9]$',
            r'^[OPQ][0-9][A-Z0-9]{4}[0-9]$'
        ]
        
        return any(re.match(pattern, query) for pattern in patterns)
    
    def is_protein_sequence(self, query: str) -> bool:
        """Check if query looks like a protein sequence"""
        return self.analyzer.validate_sequence(query)
    
    def is_fasta_format(self, query: str) -> bool:
        """Check if input is in FASTA format"""
        lines = query.strip().split('\n')
        if not lines:
            return False
        
        for line in lines:
            if line.strip():
                return line.strip().startswith('>')
        
        return False
    
    def find_exact_sequence_match(self, query_seq: str, proteins_df: pd.DataFrame) -> pd.DataFrame:
        """Find exact sequence matches"""
        clean_query = self.analyzer.clean_sequence(query_seq)
        exact_matches = proteins_df[proteins_df['sequence'].str.contains(clean_query, na=False)]
        return exact_matches
    
    def find_subsequence_matches(self, query_seq: str, proteins_df: pd.DataFrame, 
                                min_length: int = 10) -> pd.DataFrame:
        """Find proteins containing the query as a subsequence"""
        clean_query = self.analyzer.clean_sequence(query_seq)
        
        if len(clean_query) < min_length:
            return pd.DataFrame()
        
        matches = []
        for idx, row in proteins_df.iterrows():
            if pd.notna(row.get('sequence')):
                if clean_query in row['sequence']:
                    matches.append(row)
        
        return pd.DataFrame(matches) if matches else pd.DataFrame()
    
    def calculate_sequence_similarity(self, seq1: str, seq2: str) -> float:
        """Calculate sequence similarity using mathematical scoring"""
        if not seq1 or not seq2:
            return 0.0
        
        match_score = 1
        mismatch_penalty = -1
        
        score = 0
        min_len = min(len(seq1), len(seq2))
        
        for i in range(min_len):
            if seq1[i] == seq2[i]:
                score += match_score
            else:
                score += mismatch_penalty
        
        max_possible = min_len * match_score
        return max(0, score / max_possible) if max_possible > 0 else 0
    
    def validate_and_clean_input(self, query: str) -> Dict:
        """Validate input and determine its type"""
        result = {
            'type': 'unknown',
            'clean_value': query.strip(),
            'is_valid': False,
            'warnings': [],
            'parsed_fasta': None
        }
        
        if not query or not query.strip():
            result['warnings'].append('Empty input')
            return result
        
        clean_query = query.strip()
        
        # Check if it's FASTA format
        if self.is_fasta_format(clean_query):
            try:
                parsed_proteins = FASTAParser.parse_fasta_string(clean_query)
                if parsed_proteins:
                    if len(parsed_proteins) == 1:
                        protein = parsed_proteins[0]
                        result['type'] = 'fasta_single'
                        result['is_valid'] = True
                        result['clean_value'] = protein['sequence']
                        result['parsed_fasta'] = protein
                        result['metadata'] = {
                            'protein_id': protein.get('protein_id'),
                            'protein_name': protein.get('protein_name'),
                            'organism': protein.get('organism')
                        }
                    else:
                        result['type'] = 'fasta_multiple'
                        result['is_valid'] = True
                        result['parsed_fasta'] = parsed_proteins
                        result['clean_value'] = clean_query
                else:
                    result['warnings'].append('FASTA format detected but no valid proteins found')
            except Exception as e:
                result['warnings'].append(f'Error parsing FASTA: {str(e)}')
            
            return result
        
        # Check if it's a UniProt ID
        if self.is_uniprot_id(clean_query):
            result['type'] = 'uniprot_id'
            result['is_valid'] = True
            result['clean_value'] = clean_query.upper()
            return result
        
        # Check if it's a protein sequence
        if self.is_protein_sequence(clean_query):
            result['type'] = 'sequence'
            result['is_valid'] = True
            result['clean_value'] = self.analyzer.clean_sequence(clean_query)
            
            if len(result['clean_value']) < 10:
                result['warnings'].append('Sequence is very short (<10 aa)')
            elif len(result['clean_value']) < 20:
                result['warnings'].append('Sequence is short (<20 aa)')
            
            composition = self.analyzer.calculate_amino_acid_composition(result['clean_value'])
            if composition.get('X', 0) > 5:
                result['warnings'].append('High percentage of unknown residues (X)')
            
            return result
        
        # Check if it might be a protein name
        if any(keyword in clean_query.lower() for keyword in 
               ['hemoglobin', 'lysozyme', 'albumin', 'kinase', 'protease', 'protein']):
            result['type'] = 'protein_name'
            result['is_valid'] = True
            return result
        
        result['warnings'].append('Input does not appear to be a valid UniProt ID, protein sequence, or FASTA format')
        return result

def load_fasta_files(file_paths: List[str]) -> pd.DataFrame:
    """Load multiple FASTA files into a DataFrame"""
    all_proteins = []
    
    for file_path in file_paths:
        try:
            proteins = FASTAParser.parse_fasta_file(file_path)
            all_proteins.extend(proteins)
        except Exception as e:
            print(f"Warning: Could not load {file_path}: {str(e)}")
    
    if not all_proteins:
        raise Exception("No valid proteins found in the provided FASTA files")
    
    return pd.DataFrame(all_proteins)

def load_dataset(source: Union[str, List[str]]) -> pd.DataFrame:
    """
    Load protein dataset from CSV or FASTA files
    """
    if isinstance(source, str) and source.endswith('.csv'):
        try:
            df = pd.read_csv(source)
            required_columns = ['protein_id', 'protein_name', 'domain', 'function']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
            
            if 'sequence' in df.columns:
                analyzer = ProteinAnalyzer()
                df['sequence'] = df['sequence'].apply(lambda x: analyzer.clean_sequence(str(x)) if pd.notna(x) else x)
                df['length'] = df['sequence'].apply(lambda x: len(x) if pd.notna(x) else 0)
            
            return df
        except Exception as e:
            raise Exception(f"Error loading CSV dataset: {str(e)}")
    
    elif isinstance(source, list) or (isinstance(source, str) and source.endswith('.fasta')):
        file_paths = source if isinstance(source, list) else [source]
        return load_fasta_files(file_paths)
    
    else:
        raise ValueError("Unsupported data source. Please provide CSV file or FASTA files")