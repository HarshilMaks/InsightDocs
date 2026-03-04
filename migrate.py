import os
import sys
import psycopg
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment or .env file.")
    sys.exit(1)

def run_migration(file_path):
    print(f"Running migration: {file_path}")
    try:
        with open(file_path, "r") as f:
            sql = f.read()
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                conn.commit()
                print("Migration successfully applied!")
    except Exception as e:
        print(f"Error applying migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migration_file = "migrations/001_add_ocr_tts_to_documents.sql"
    if not os.path.exists(migration_file):
        print(f"Error: Migration file not found: {migration_file}")
        sys.exit(1)
    
    run_migration(migration_file)
