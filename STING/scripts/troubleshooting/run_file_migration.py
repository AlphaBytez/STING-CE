#!/usr/bin/env python3
"""
Run file asset management database migration.
"""

import os
import sys
import psycopg2
from pathlib import Path

def run_migration():
    """Run the file tables migration."""
    
    # Get database connection details
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)
    
    # Parse database URL
    if database_url.startswith('postgresql://'):
        # Extract connection details from URL
        # Format: postgresql://user:password@host:port/database
        url_parts = database_url.replace('postgresql://', '').split('/')
        db_name = url_parts[-1].split('?')[0]  # Remove query parameters
        host_port_user = url_parts[0]
        
        if '@' in host_port_user:
            user_pass, host_port = host_port_user.split('@')
            if ':' in user_pass:
                user, password = user_pass.split(':', 1)
            else:
                user = user_pass
                password = ''
        else:
            host_port = host_port_user
            user = 'postgres'
            password = ''
        
        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host = host_port
            port = '5432'
    else:
        print("ERROR: Unsupported database URL format")
        sys.exit(1)
    
    # Read migration SQL
    migration_file = Path(__file__).parent / 'app' / 'migrations' / 'create_file_tables.sql'
    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        sys.exit(1)
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    # Connect to database and run migration
    try:
        print(f"Connecting to database: {host}:{port}/{db_name}")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=db_name,
            user=user,
            password=password
        )
        
        with conn.cursor() as cursor:
            print("Running file asset management migration...")
            cursor.execute(migration_sql)
            conn.commit()
            print("Migration completed successfully!")
            
            # Verify tables were created
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('file_assets', 'file_permissions', 'file_upload_sessions')
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            print(f"Created tables: {[table[0] for table in tables]}")
        
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_migration()