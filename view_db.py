import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=== Database Tables ===")
for table in tables:
    table_name = table[0]
    print(f"\n📊 Table: {table_name}")
    
    # Get table info
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    print("   Columns:")
    for col in columns:
        print(f"   - {col[1]} ({col[2]})")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    print(f"   Rows: {count}")

# Close connection
conn.close()
print("\n✅ Database inspection complete!")
