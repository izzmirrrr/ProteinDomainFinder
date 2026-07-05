from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Union

from pymongo import UpdateOne

from database import proteins_collection
from fasta_parser import FASTAParser

DATA_DIR = Path(__file__).resolve().parent / "Data"

CURATED_ANNOTATIONS = {
    "P04637": {
        "domain": "P53 DNA-Binding Domain",
        "domain_family": "Tumor Suppressor / Transcription Factor",
        "function": "Cellular tumor antigen p53 regulates DNA damage response, cell-cycle arrest, apoptosis, and tumor suppression.",
    },
    "P07900": {
        "domain": "HSP90 Chaperone ATPase",
        "domain_family": "Heat Shock Protein 90",
        "function": "HSP90-alpha is a molecular chaperone that helps fold, stabilize, and regulate client proteins using ATP.",
    },
    "P31749": {
        "domain": "Protein Kinase",
        "domain_family": "AGC Serine/Threonine Kinase",
        "function": "AKT1 is a serine/threonine kinase involved in growth, survival, metabolism, and PI3K-AKT signaling.",
    },
}


def iter_fasta_files(data_dir: Path = DATA_DIR) -> List[Path]:
    """Return plain FASTA files from Data. Gz copies are skipped to avoid duplicates."""
    patterns = ("*.fasta", "*.fa", "*.faa")
    files: List[Path] = []
    for pattern in patterns:
        files.extend(data_dir.glob(pattern))
    return sorted(set(files))


def prepare_protein_doc(protein: Dict, source_file: Union[Path, str]) -> Dict:
    doc = dict(protein)
    doc.setdefault("domain", "Unknown")
    doc.setdefault("function", "To be predicted by rule engine.")
    doc.setdefault("domain_family", "Prediction Pending")
    doc.setdefault("organism", "Unknown")
    doc.update(CURATED_ANNOTATIONS.get(doc.get("protein_id"), {}))
    doc["source_file"] = Path(source_file).name
    doc["imported_at"] = datetime.utcnow()
    return doc


def import_fasta_files(files: Iterable[Path] = None) -> Dict:
    files = list(files) if files is not None else iter_fasta_files()
    inserted = 0
    updated = 0
    parsed = 0
    errors = []

    for file_path in files:
        try:
            proteins = FASTAParser.parse_fasta_file(str(file_path))
            parsed += len(proteins)
            operations = []

            for protein in proteins:
                doc = prepare_protein_doc(protein, file_path)
                operations.append(
                    UpdateOne(
                        {"protein_id": doc["protein_id"]},
                        {
                            "$set": doc,
                            "$setOnInsert": {"created_at": datetime.utcnow()},
                        },
                        upsert=True,
                    )
                )

            if operations:
                result = proteins_collection.bulk_write(operations, ordered=False)
                inserted += result.upserted_count
                updated += result.modified_count
        except Exception as exc:
            errors.append(f"{file_path.name}: {exc}")

    return {
        "files": [file.name for file in files],
        "parsed": parsed,
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
    }


if __name__ == "__main__":
    summary = import_fasta_files()
    print("FASTA import summary:")
    for key, value in summary.items():
        print(f"{key}: {value}")
