import psycopg
import os
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get('SUPABASE_DB_URL')

if not url:
    print('ERROR: SUPABASE_DB_URL not set in .env')
    exit(1)

with open('sql/001_create_parsed_documents.sql', 'r') as f:
    sql = f.read()

try:
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print('✓ Migration applied successfully.')
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)
