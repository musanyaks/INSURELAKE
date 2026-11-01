"""Load data/raw/claims.csv into MinIO as silver parquet."""
import duckdb

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute("SET s3_endpoint='localhost:9000';")
con.execute("SET s3_use_ssl=false;")
con.execute("SET s3_url_style='path';")
con.execute("SET s3_access_key_id='minioadmin';")
con.execute("SET s3_secret_access_key='minioadmin';")
con.execute("""
    COPY (SELECT * FROM read_csv_auto('data/raw/claims.csv',  types={'claim_date': 'VARCHAR'}))
    TO 's3://warehouse/silver/claims/claims.parquet' (FORMAT parquet)
""")
print("loaded silver claims")