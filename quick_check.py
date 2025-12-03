# quick_check.py
import os, pandas as pd, faiss, json

pq = "./data/aeat_corpus.parquet"
ix = "./data/aeat_faiss.index"
mj = "./data/aeat_artifacts.json"

print("parquet:", os.path.exists(pq), "index:", os.path.exists(ix), "meta_json:", os.path.exists(mj))
df = pd.read_parquet(pq)
index = faiss.read_index(ix)
print("df_len:", len(df), "index.ntotal:", index.ntotal)

if os.path.exists(mj):
    with open(mj, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print("meta.embedding_model:", meta.get("embedding_model"))
    print("meta.df_len:", meta.get("df_len"))