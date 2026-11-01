"""Storage abstraction: MinIO (S3) OR local folder, auto-detected.

    STORAGE_MODE=local  -> always ./data/
    STORAGE_MODE=s3     -> always MinIO on localhost:9000
    STORAGE_MODE=auto   -> probe; S3 if reachable, else local  (default)

Use as:
    from pipeline._storage import read_parquet, write_parquet, mode
"""
from __future__ import annotations
import os, socket
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq

_MODE = None
_S3   = None


def _probe_s3() -> bool:
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    host, _, port = endpoint.partition(":")
    try:
        s = socket.create_connection((host or "localhost", int(port or 9000)), timeout=1)
        s.close(); return True
    except Exception:
        return False


def mode() -> str:
    global _MODE
    if _MODE is None:
        requested = os.getenv("STORAGE_MODE", "auto").lower()
        if requested in ("local", "s3"):
            _MODE = requested
        else:
            _MODE = "s3" if _probe_s3() else "local"
    return _MODE


def _s3_fs():
    global _S3
    if _S3 is None:
        import pyarrow.fs as pafs
        _S3 = pafs.S3FileSystem(
            endpoint_override=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
            scheme="http",
        )
    return _S3


def read_parquet(prefix: str):
    """prefix like 'silver/claim'. Returns DataFrame or None."""
    import pandas as pd
    if mode() == "s3":
        try:
            import pyarrow.dataset as ds
            tbl = ds.dataset(prefix, filesystem=_s3_fs(), format="parquet").to_table()
            return tbl.to_pandas() if tbl.num_rows else None
        except Exception:
            return None
    import pandas as pd
    candidates = [Path("data") / prefix]
    parts = prefix.split("/")
    if parts[0] == "bronze" and len(parts) > 1:
        tbl = parts[1]
        candidates += [
            Path("data/raw") / tbl,
            Path("data/raw") / f"{tbl}.parquet",
        ]
    if parts[0] == "silver" and len(parts) > 1:
        candidates.append(Path("data/silver") / parts[1])

    for root in candidates:
        if root.is_file() and root.suffix == ".parquet":
            return pd.read_parquet(root)
        if root.is_dir():
            files = list(root.rglob("*.parquet"))
            if files:
                return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    return None


def write_parquet(df, path: str):
    """path like 'gold/fact_claims/part-0.parquet'."""
    if df is None or len(df) == 0:
        print(f"[storage] skip empty -> {path}"); return
    if mode() == "s3":
        pq.write_table(pa.Table.from_pandas(df, preserve_index=False), path, filesystem=_s3_fs())
    else:
        target = Path("data") / path
        target.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(target, index=False)
    print(f"[storage] {len(df):>6} rows -> {path}  ({mode()})")
