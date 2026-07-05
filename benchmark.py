# benchmark.py
import pandas as pd
import json
from typing import Dict, List, Tuple
from collections import defaultdict
from analysis import ProteinAnalyzer
from rules_engine import DomainRulesEngine

class SCOPEvaluator:
    def __init__(self):
        self.analyzer = ProteinAnalyzer()
        self.rules_engine = DomainRulesEngine()
    
    def load_scop_dataset(self, json_path: str) -> pd.DataFrame:
        """Load SCOP 2.06 dataset from JSON file."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        # Expected structure: list of domains with 'domain_id', 'sequence', 'fold'
        records = []
        for item in data:
            records.append({
                'domain_id': item.get('domain_id'),
                'sequence': item.get('sequence', ''),
                'fold': item.get('fold', 'Unknown'),
                'class': item.get('class', 'Unknown')
            })
        return pd.DataFrame(records)
    
    def map_fold_to_domain(self, fold: str) -> str:
        """Map SCOP fold to our domain prediction categories."""
        mapping = {
            'globin': 'Globin',
            'immunoglobulin': 'Immunoglobulin',
            'kinase': 'Kinase',
            'zinc finger': 'Zinc Finger',
            'transmembrane': 'Transmembrane',
            'serine protease': 'Serine Protease'
        }
        for key, domain in mapping.items():
            if key in fold.lower():
                return domain
        return "Other"
    
    def evaluate(self, scop_df: pd.DataFrame) -> Dict:
        """Run evaluation on SCOP dataset."""
        results = []
        y_true = []
        y_pred = []
        
        for _, row in scop_df.iterrows():
            sequence = row['sequence']
            true_fold = row['fold']
            true_domain = self.map_fold_to_domain(true_fold)
            
            # Get prediction from rule engine
            props = self.analyzer.calculate_physicochemical_properties(sequence)
            props_with_seq = {'sequence': sequence, 'length': len(sequence)}
            props_with_seq.update(props)
            predictions = self.rules_engine.predict_domain_by_rules(sequence, props_with_seq)
            
            predicted_domain = predictions[0]['domain'] if predictions else "Unknown"
            confidence = predictions[0]['confidence'] if predictions else 0
            
            results.append({
                'domain_id': row['domain_id'],
                'true_fold': true_fold,
                'true_domain': true_domain,
                'predicted_domain': predicted_domain,
                'confidence': confidence,
                'correct': true_domain.lower() == predicted_domain.lower()
            })
            y_true.append(true_domain)
            y_pred.append(predicted_domain)
        
        # Compute metrics
        from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
        labels = list(set(y_true + y_pred))
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        accuracy = accuracy_score(y_true, y_pred)
        
        return {
            'accuracy': accuracy,
            'confusion_matrix': cm.tolist(),
            'labels': labels,
            'classification_report': classification_report(y_true, y_pred, output_dict=True),
            'detailed_results': results,
            'total_domains': len(results),
            'correct_predictions': sum(r['correct'] for r in results)
        }