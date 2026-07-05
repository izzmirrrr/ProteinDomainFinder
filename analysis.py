import re
from typing import Dict, List, Tuple, Optional
import numpy as np
from Bio.SeqUtils.ProtParam import ProteinAnalysis

class ProteinAnalyzer:
    """Mathematical analysis of protein sequences"""
    
    AMINO_ACIDS = 'ACDEFGHIKLMNPQRSTVWY'
    
    @staticmethod
    def validate_sequence(sequence: str) -> bool:
        """Validate if input is a valid protein sequence"""
        if not sequence:
            return False
        
        clean_seq = ''.join(sequence.upper().split())
        return all(aa in ProteinAnalyzer.AMINO_ACIDS for aa in clean_seq)
    
    @staticmethod
    def clean_sequence(sequence: str) -> str:
        """Clean and standardize protein sequence"""
        clean_seq = ''.join([c.upper() for c in sequence if c.isalpha()])
        clean_seq = ''.join([c for c in clean_seq if c in ProteinAnalyzer.AMINO_ACIDS])
        return clean_seq
    
    @staticmethod
    def calculate_amino_acid_composition(sequence: str) -> Dict[str, float]:
        """Calculate percentage composition of each amino acid"""
        seq_len = len(sequence)
        if seq_len == 0:
            return {aa: 0.0 for aa in ProteinAnalyzer.AMINO_ACIDS}
        
        composition = {}
        for aa in ProteinAnalyzer.AMINO_ACIDS:
            count = sequence.count(aa)
            composition[aa] = (count / seq_len) * 100
        
        return composition
    
    @staticmethod
    def calculate_physicochemical_properties(sequence: str) -> Dict[str, float]:
        """Calculate various physicochemical properties"""
        if len(sequence) < 1:
            return {}
        
        analysis = ProteinAnalysis(sequence)
        
        properties = {
            'molecular_weight': analysis.molecular_weight(),
            'aromaticity': analysis.aromaticity(),
            'instability_index': analysis.instability_index(),
            'isoelectric_point': analysis.isoelectric_point(),
            'gravy': analysis.gravy(),
            'secondary_structure_fraction': analysis.secondary_structure_fraction()
        }
        
        properties['hydrophobic_ratio'] = ProteinAnalyzer._calculate_hydrophobic_ratio(sequence)
        properties['charge_density'] = ProteinAnalyzer._calculate_charge_density(sequence)
        
        return properties
    
    @staticmethod
    def _calculate_hydrophobic_ratio(sequence: str) -> float:
        """Calculate ratio of hydrophobic amino acids"""
        hydrophobic_aas = {'A', 'V', 'L', 'I', 'P', 'F', 'W', 'M'}
        hydrophobic_count = sum(1 for aa in sequence if aa in hydrophobic_aas)
        return hydrophobic_count / len(sequence) if sequence else 0
    
    @staticmethod
    def _calculate_charge_density(sequence: str) -> float:
        """Calculate charge density (basic - acidic amino acids)"""
        basic_aas = {'K', 'R', 'H'}
        acidic_aas = {'D', 'E'}
        
        basic_count = sum(1 for aa in sequence if aa in basic_aas)
        acidic_count = sum(1 for aa in sequence if aa in acidic_aas)
        
        return (basic_count - acidic_count) / len(sequence) if sequence else 0
    
    @staticmethod
    def find_motifs(sequence: str) -> Dict[str, List[int]]:
        """Find known protein motifs using regular expressions"""
        motifs = {
            'zinc_finger': r'C.{2,4}C.{3}[LIVMFYWC].{8}H.{3,5}H',
            'leucine_zipper': r'L.{6}L.{6}L.{6}L',
            'glycosylation_site': r'N[^P][ST][^P]',
            'phosphorylation_site': r'[ST]Q',
            'nuclear_localization': r'[KR]{4,}',
            'transmembrane': r'.{10,30}[LIVMFWSTAG][LIVMFYSTAG]{2,5}[LIVMFYWSTAG].{10,30}'
        }
        
        found_motifs = {}
        for motif_name, pattern in motifs.items():
            matches = list(re.finditer(pattern, sequence))
            if matches:
                found_motifs[motif_name] = [match.start() for match in matches]
        
        return found_motifs
    
    @staticmethod
    def calculate_sequence_complexity(sequence: str, window_size: int = 10) -> float:
        """Calculate sequence complexity using Shannon entropy"""
        from collections import Counter
        import math
        
        if len(sequence) < window_size:
            return 0
        
        complexities = []
        for i in range(0, len(sequence) - window_size + 1):
            window = sequence[i:i + window_size]
            counts = Counter(window)
            entropy = -sum((count/len(window)) * math.log2(count/len(window)) 
                          for count in counts.values())
            complexities.append(entropy)
        
        return np.mean(complexities) if complexities else 0
    
    @staticmethod
    def detect_domain_hints(sequence: str) -> Dict[str, any]:
        """Detect hints about possible domains based on sequence features"""
        hints = {}
        seq_len = len(sequence)
        
        # Length-based hints
        if seq_len < 50:
            hints['size_hint'] = 'Very small protein - possibly a peptide or fragment'
        elif seq_len < 100:
            hints['size_hint'] = 'Small protein'
        elif seq_len < 300:
            hints['size_hint'] = 'Medium-sized protein'
        elif seq_len < 500:
            hints['size_hint'] = 'Large protein'
        else:
            hints['size_hint'] = 'Very large protein - likely multi-domain'
        
        # Cysteine content hint
        cys_percent = (sequence.count('C') / seq_len) * 100 if seq_len > 0 else 0
        if cys_percent > 5:
            hints['cysteine_hint'] = f'High cysteine content ({cys_percent:.1f}%) - possible disulfide bonds'
        
        # Proline content hint
        pro_percent = (sequence.count('P') / seq_len) * 100 if seq_len > 0 else 0
        if pro_percent > 10:
            hints['proline_hint'] = f'High proline content ({pro_percent:.1f}%) - possible structural/connector regions'
        
        # Charge hint
        properties = ProteinAnalyzer.calculate_physicochemical_properties(sequence)
        if properties.get('isoelectric_point', 7) > 8.5:
            hints['charge_hint'] = 'Basic protein (pI > 8.5)'
        elif properties.get('isoelectric_point', 7) < 5.5:
            hints['charge_hint'] = 'Acidic protein (pI < 5.5)'
        
        return hints