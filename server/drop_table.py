import os
from dotenv import load_dotenv
load_dotenv('.env')
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv('DATABASE_URL_SYNC'))
with engine.begin() as conn:
    conn.execute(text('DROP TABLE IF EXISTS hub_providers CASCADE'))
    print("Table dropped successfully")
