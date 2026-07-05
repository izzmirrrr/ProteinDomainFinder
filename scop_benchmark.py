import requests
import pandas as pd

# Your backend endpoint
API_URL = "http://localhost:8000"

def run_benchmark():
    # Load your SCOP dataset (example format)
    scop_df = pd.read_csv("data/scop_2.06_dataset.csv")
    
    results = []
    for _, row in scop_df.iterrows():
        # Call your prediction API
        response = requests.post(f"{API_URL}/api/predict", json={
            "query": row['sequence'],
            "use_rule_based": True,
            "analyze_sequence": False
        })
        
        if response.status_code == 200:
            pred = response.json()
            top_pred = pred['rule_based_predictions'][0] if pred.get('rule_based_predictions') else {}
            results.append({
                'domain_id': row['domain_id'],
                'true_domain': row['scop_class'],
                'predicted_domain': top_pred.get('domain', 'Unknown'),
                'confidence': top_pred.get('confidence', 0),
                'match': top_pred.get('domain', '').lower() == row['scop_class'].lower()
            })
    
    # Save results
    pd.DataFrame(results).to_csv("benchmark_results.csv", index=False)
    print(f"Accuracy: {sum(r['match'] for r in results)/len(results):.2%}")

if __name__ == "__main__":
    run_benchmark()