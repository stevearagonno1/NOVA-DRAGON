"""L0081 shared data cache — build the (deterministic) per-symbol arrays + fires frame ONCE
and pickle them so every phase reuses them instead of recomputing outcome arrays each run.
Cache lives in ~/l007x_4h/ (survives sandbox snapshot resets)."""
import os, sys, pickle
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import l0080_combo as C

CACHE = os.path.expanduser("~/l007x_4h/l0081_cache.pkl")


def get(rebuild=False):
    if os.path.exists(CACHE) and not rebuild:
        with open(CACHE, "rb") as f:
            d = pickle.load(f)
        return d["data"], d["FR"]
    data = C.load_all()
    FR = C.build_fires(data)
    with open(CACHE, "wb") as f:
        pickle.dump({"data": data, "FR": FR}, f, protocol=pickle.HIGHEST_PROTOCOL)
    return data, FR


if __name__ == "__main__":
    data, FR = get(rebuild=True)
    print("cache built:", CACHE, "| symbols:", len(data), "| fire rows:", len(FR))
