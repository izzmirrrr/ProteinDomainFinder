import re
from typing import List, Dict, Generator, Tuple
from pathlib import Path
import pandas as pd
from io import StringIO
from analysis import ProteinAnalyzer

class FASTAParser:
    """Parser for FASTA format protein files"""
    
    @staticmethod
    def parse_fasta_file(file_path: str) -> List[Dict]:
        """
        Parse a FASTA file and extract protein information
        """
        proteins = []
        analyzer = ProteinAnalyzer()
        
        try:
            with open(file_path, 'r') as file:
                current_header = ""
                current_sequence = []
                
                for line in file:
                    line = line.strip()
                    
                    if line.startswith(">"):
                        if current_header and current_sequence:
                            protein_data = FASTAParser._create_protein_dict(
                                current_header, 
                                ''.join(current_sequence),
                                analyzer
                            )
                            if protein_data:
                                proteins.append(protein_data)
                        
                        current_header = line[1:].strip()
                        current_sequence = []
                    
                    elif line and not line.startswith(";"):
                        current_sequence.append(line)
                
                if current_header and current_sequence:
                    protein_data = FASTAParser._create_protein_dict(
                        current_header, 
                        ''.join(current_sequence),
                        analyzer
                    )
                    if protein_data:
                        proteins.append(protein_data)
                        
        except FileNotFoundError:
            raise FileNotFoundError(f"FASTA file not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error parsing FASTA file: {str(e)}")
        
        return proteins
    
    @staticmethod
    def parse_fasta_string(fasta_string: str) -> List[Dict]:
        """
        Parse FASTA format from a string
        """
        proteins = []
        analyzer = ProteinAnalyzer()
        
        lines = fasta_string.strip().split('\n')
        current_header = ""
        current_sequence = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith(">"):
                if current_header and current_sequence:
                    protein_data = FASTAParser._create_protein_dict(
                        current_header, 
                        ''.join(current_sequence),
                        analyzer
                    )
                    if protein_data:
                        proteins.append(protein_data)
                
                current_header = line[1:].strip()
                current_sequence = []
            
            elif line and not line.startswith(";"):
                current_sequence.append(line)
        
        if current_header and current_sequence:
            protein_data = FASTAParser._create_protein_dict(
                current_header, 
                ''.join(current_sequence),
                analyzer
            )
            if protein_data:
                proteins.append(protein_data)
        
        return proteins
    
    @staticmethod
    def _create_protein_dict(header: str, sequence: str, analyzer: ProteinAnalyzer) -> Dict:
        """
        Create a protein dictionary from header and sequence
        """
        clean_sequence = analyzer.clean_sequence(sequence.upper())
        
        if not clean_sequence:
            return None
        
        protein_id, protein_name, organism = FASTAParser._parse_header(header)
        
        protein_data = {
            'protein_id': protein_id,
            'protein_name': protein_name,
            'sequence': clean_sequence,
            'length': len(clean_sequence),
            'organism': organism,
            'header': header
        }
        
        return protein_data
    
    @staticmethod
    def _parse_header(header: str) -> Tuple[str, str, str]:
        """
        Parse FASTA header to extract ID, name, and organism
        """
        protein_id = ""
        protein_name = ""
        organism = ""
        
        header = header.strip()
        
        if header.startswith("sp|") or header.startswith("tr|"):
            parts = header.split("|")
            if len(parts) >= 3:
                protein_id = parts[1]
                protein_name = parts[2].split()[0]
                
                os_match = re.search(r'OS=([^=]+?)(?:\s+[A-Z]{2}=|$)', header)
                if os_match:
                    organism = os_match.group(1).strip()
        
        elif "|" in header and ("gi|" in header or "gb|" in header or "emb|" in header):
            parts = header.split("|")
            if len(parts) >= 4:
                description = parts[-1]
                protein_name = description.split()[0] if description else ""
                
                for i, part in enumerate(parts):
                    if part and not part.startswith(("gi", "gb", "emb", "ref", "dbj")):
                        if len(part) > 3 and not protein_id:
                            protein_id = part
        
        else:
            header_parts = header.split()
            if header_parts:
                protein_id = header_parts[0]
                protein_name = " ".join(header_parts[1:]) if len(header_parts) > 1 else protein_id
        
        if not organism:
            bracket_match = re.search(r'\[([^\]]+)\]', header)
            if bracket_match:
                organism = bracket_match.group(1).strip()
        
        if not protein_name:
            protein_name = header.split()[0] if header.split() else "Unknown"
        
        if not protein_id:
            protein_id = f"SEQ_{hash(header) % 1000000:06d}"
        
        protein_name = protein_name.replace("_", " ").title()
        
        return protein_id, protein_name, organism
    
    @staticmethod
    def load_multiple_fasta_files(file_paths: List[str]) -> List[Dict]:
        """
        Load multiple FASTA files
        """
        all_proteins = []
        
        for file_path in file_paths:
            try:
                proteins = FASTAParser.parse_fasta_file(file_path)
                all_proteins.extend(proteins)
                print(f"Loaded {len(proteins)} proteins from {file_path}")
            except Exception as e:
                print(f"Warning: Could not load {file_path}: {str(e)}")
        
        return all_proteins
    
    @staticmethod
    def fasta_to_dataframe(fasta_file_path: str) -> pd.DataFrame:
        """
        Convert FASTA file to pandas DataFrame
        """
        proteins = FASTAParser.parse_fasta_file(fasta_file_path)
        return pd.DataFrame(proteins)
    
    @staticmethod
    def export_to_fasta(proteins: List[Dict], output_file: str):
        """
        Export proteins to FASTA format
        """
        with open(output_file, 'w') as f:
            for protein in proteins:
                header = protein.get('header', '')
                if not header:
                    protein_id = protein.get('protein_id', '')
                    protein_name = protein.get('protein_name', '')
                    organism = protein.get('organism', '')
                    
                    if organism:
                        header = f"{protein_id} {protein_name} [{organism}]"
                    else:
                        header = f"{protein_id} {protein_name}"
                
                sequence = protein.get('sequence', '')
                
                if header and sequence:
                    f.write(f">{header}\n")
                    for i in range(0, len(sequence), 60):
                        f.write(sequence[i:i+60] + "\n")
    
    @staticmethod
    def validate_fasta_file(file_path: str) -> Dict:
        """
        Validate a FASTA file and return statistics
        """
        try:
            proteins = FASTAParser.parse_fasta_file(file_path)
            
            if not proteins:
                return {
                    'valid': False,
                    'message': 'No valid proteins found in file',
                    'protein_count': 0
                }
            
            total_proteins = len(proteins)
            sequence_lengths = [p['length'] for p in proteins]
            avg_length = sum(sequence_lengths) / total_proteins if total_proteins > 0 else 0
            
            issues = []
            
            short_seqs = [p for p in proteins if p['length'] < 10]
            if short_seqs:
                issues.append(f"{len(short_seqs)} sequences are very short (<10 aa)")
            
            analyzer = ProteinAnalyzer()
            invalid_seqs = []
            for protein in proteins:
                if not analyzer.validate_sequence(protein['sequence']):
                    invalid_seqs.append(protein['protein_id'])
            
            if invalid_seqs:
                issues.append(f"{len(invalid_seqs)} sequences contain invalid amino acids")
            
            return {
                'valid': True,
                'message': f'FASTA file is valid with {total_proteins} proteins',
                'protein_count': total_proteins,
                'avg_sequence_length': round(avg_length, 1),
                'min_length': min(sequence_lengths) if sequence_lengths else 0,
                'max_length': max(sequence_lengths) if sequence_lengths else 0,
                'issues': issues if issues else ['No issues found']
            }
            
        except Exception as e:
            return {
                'valid': False,
                'message': f'Error validating FASTA file: {str(e)}',
                'protein_count': 0
            }