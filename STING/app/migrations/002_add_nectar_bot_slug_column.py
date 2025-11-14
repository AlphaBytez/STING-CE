"""
Add slug column to nectar_bots table

This migration adds the missing 'slug' column to the nectar_bots table.
The slug is a URL-friendly identifier for nectar bots.

Run with: python app/migrations/add_nectar_bot_slug_column.py
"""

import psycopg2
import os
import sys
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def slugify(text):
    """Convert text to URL-friendly slug"""
    text = str(text).lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def run_migration():
    """Add slug column to nectar_bots table"""

    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False

    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        logger.info("Connected to database")

        # Check if slug column already exists
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='nectar_bots' AND column_name='slug'
        """)

        if cur.fetchone():
            logger.info("✅ slug column already exists - nothing to do")
            conn.close()
            return True

        logger.info("Adding slug column to nectar_bots table...")

        # Step 1: Add slug column (nullable first, so we can populate it)
        cur.execute("""
            ALTER TABLE nectar_bots
            ADD COLUMN slug VARCHAR(255)
        """)
        conn.commit()
        logger.info("✅ Added slug column (nullable)")

        # Step 2: Generate slugs for existing bots based on name + id
        cur.execute("SELECT id, name FROM nectar_bots")
        bots = cur.fetchall()

        logger.info(f"Generating slugs for {len(bots)} existing nectar bots...")

        for bot_id, name in bots:
            # Create slug from name, fallback to bot_id if name is empty
            if name:
                base_slug = slugify(name)
            else:
                base_slug = str(bot_id)[:8]

            # Ensure uniqueness by appending part of UUID if needed
            slug = f"{base_slug}-{str(bot_id)[:8]}"

            cur.execute(
                "UPDATE nectar_bots SET slug = %s WHERE id = %s",
                (slug, bot_id)
            )

        conn.commit()
        logger.info(f"✅ Generated slugs for {len(bots)} bots")

        # Step 3: Make slug column NOT NULL and UNIQUE
        cur.execute("""
            ALTER TABLE nectar_bots
            ALTER COLUMN slug SET NOT NULL
        """)
        conn.commit()
        logger.info("✅ Made slug column NOT NULL")

        cur.execute("""
            CREATE UNIQUE INDEX idx_nectar_bots_slug
            ON nectar_bots(slug)
        """)
        conn.commit()
        logger.info("✅ Created unique index on slug column")

        logger.info("🎉 Migration completed successfully!")

        # Close connection
        cur.close()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
