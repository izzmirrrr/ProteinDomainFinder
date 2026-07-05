from typing import Dict, List, Tuple, Optional
from analysis import ProteinAnalyzer

class DomainRulesEngine:
    """Rule-based engine for predicting protein domains"""
    
    DOMAIN_RULES = {
        'globin': {
            'conditions': [
                lambda props: 140 <= props.get('length', 0) <= 160,
                lambda props: 7.0 <= props.get('isoelectric_point', 0) <= 8.5,
                lambda props: props.get('hydrophobic_ratio', 0) > 0.45,
                lambda seq: 'H' in seq and 'F' in seq and 'L' in seq,
            ],
            'confidence_factor': 0.9,
            'description': 'Heme-binding oxygen transport proteins'
        },
        'immunoglobulin': {
            'conditions': [
                lambda props: 90 <= props.get('length', 0) <= 110,
                lambda props: 'C' in props.get('sequence', '') * 2,
                lambda seq: seq.count('C') >= 2,
                lambda props: 4.5 <= props.get('isoelectric_point', 0) <= 6.5,
            ],
            'confidence_factor': 0.85,
            'description': 'Antigen recognition domains'
        },
        'kinase': {
            'conditions': [
                lambda props: 250 <= props.get('length', 0) <= 300,
                lambda seq: 'DFG' in seq or 'APE' in seq,
                lambda props: props.get('instability_index', 0) < 40,
                lambda seq: seq.count('S') + seq.count('T') > 0.1 * len(seq),
            ],
            'confidence_factor': 0.8,
            'description': 'Protein kinase catalytic domains'
        },
        'zinc_finger': {
            'conditions': [
                lambda props: 20 <= props.get('length', 0) <= 40,
                lambda seq: seq.count('C') >= 2 and seq.count('H') >= 2,
                lambda props: 'zinc_finger' in ProteinAnalyzer.find_motifs(props.get('sequence', '')),
                lambda props: props.get('molecular_weight', 0) < 10000,
            ],
            'confidence_factor': 0.9,
            'description': 'Zinc-coordinating DNA-binding domains'
        },
        'transmembrane': {
            'conditions': [
                lambda props: 7.0 <= props.get('gravy', 0) <= 2.0,
                lambda seq: 'transmembrane' in ProteinAnalyzer.find_motifs(seq),
                lambda props: props.get('hydrophobic_ratio', 0) > 0.6,
                lambda props: 0.4 <= props.get('secondary_structure_fraction', [0, 0, 0])[1] <= 0.7,
            ],
            'confidence_factor': 0.75,
            'description': 'Transmembrane helical domains'
        },
        'serine_protease': {
            'conditions': [
                lambda props: 220 <= props.get('length', 0) <= 260,
                lambda seq: 'H' in seq and 'D' in seq and 'S' in seq,
                lambda seq: 'GDSGG' in seq or 'GXSG' in seq,
                lambda props: 8.0 <= props.get('isoelectric_point', 0) <= 10.0,
            ],
            'confidence_factor': 0.85,
            'description': 'Serine protease catalytic domains'
        }
    }
    
    @staticmethod
    def predict_domain_by_rules(sequence: str, protein_props: Dict) -> List[Dict]:
        """Predict domain based on mathematical rules and sequence characteristics"""
        predictions = []
        
        for domain_name, rules in DomainRulesEngine.DOMAIN_RULES.items():
            score = 0
            satisfied_conditions = []
            
            for i, condition in enumerate(rules['conditions']):
                try:
                    if condition.__code__.co_varnames[0] == 'seq':
                        is_satisfied = condition(sequence)
                    else:
                        is_satisfied = condition(protein_props)
                    
                    if is_satisfied:
                        score += 1
                        satisfied_conditions.append(f"Condition {i+1}")
                except Exception:
                    continue
            
            if score >= 2:
                confidence = (score / len(rules['conditions'])) * rules['confidence_factor']
                
                prediction = {
                    'domain': domain_name.replace('_', ' ').title(),
                    'confidence': round(confidence, 3),
                    'satisfied_conditions': satisfied_conditions,
                    'description': rules['description'],
                    'score': f"{score}/{len(rules['conditions'])}"
                }
                predictions.append(prediction)
        
        predictions.sort(key=lambda x: x['confidence'], reverse=True)
        return predictions
    
    @staticmethod
    def predict_by_pattern_matching(sequence: str) -> List[Dict]:
        """Predict domain based on sequence pattern matching"""
        patterns = {
            'homeobox': r'R[RK][RK][A-Z]{2}[A-Z][A-Z][A-Z]Y',
            'atp_binding': r'G[A-Z]{4}GK[ST]',
            'calcium_binding': r'D[DN][A-Z]{2}[DN][A-Z]{2}[FL]',
            'sh3': r'.[VL][A-Z][A-Z].[VL]P..[FYWLVA]',
            'pdZ': r'.[GV][A-Z][A-Z].[GV].[A-Z][A-Z][A-Z]',
        }
        
        predictions = []
        import re
        
        for domain, pattern in patterns.items():
            matches = re.findall(pattern, sequence)
            if matches:
                predictions.append({
                    'domain': domain.replace('_', ' ').upper(),
                    'confidence': min(0.3 + (len(matches) * 0.1), 0.8),
                    'evidence': f"Found {len(matches)} pattern match(es)",
                    'description': f"Pattern-based prediction"
                })
        
        return predictions
    
    @staticmethod
    def calculate_rule_based_confidence(sequence: str, matched_domain: str = None) -> float:
        """Calculate confidence score based on sequence properties"""
        if not sequence or len(sequence) < 10:
            return 0.0
        
        analyzer = ProteinAnalyzer()
        props = analyzer.calculate_physicochemical_properties(sequence)
        
        confidence_factors = []
        
        # Length factor
        optimal_length = 150
        length_factor = 1.0 - min(abs(len(sequence) - optimal_length) / optimal_length, 1.0)
        confidence_factors.append(length_factor * 0.3)
        
        # Complexity factor
        complexity = analyzer.calculate_sequence_complexity(sequence)
        complexity_factor = min(complexity / 2.0, 1.0)
        confidence_factors.append(complexity_factor * 0.2)
        
        # Instability factor
        instability = props.get('instability_index', 40)
        instability_factor = 1.0 if instability < 40 else max(0, 1.0 - (instability - 40) / 60)
        confidence_factors.append(instability_factor * 0.2)
        
        # Motif factor
        motifs = analyzer.find_motifs(sequence)
        motif_factor = min(len(motifs) * 0.15, 0.3)
        confidence_factors.append(motif_factor)
        
        return sum(confidence_factors)
