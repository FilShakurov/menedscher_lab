import pandas as pd

def process_multiheader_column(col):
    if isinstance(col, tuple):
        clean_parts = []
        for part in col:
            if pd.isna(part):
                continue
            part_str = str(part)
            if part_str.startswith("Unnamed:"):
                continue
            if part_str.strip() and part_str != "nan":
                clean_parts.append(part_str.strip())
        return "_".join(clean_parts) if clean_parts else f"column_{hash(col) % 1000}"
    return str(col).strip()