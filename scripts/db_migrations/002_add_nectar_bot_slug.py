#!/usr/bin/env python3
"""
Database migration: Add slug field to nectar_bots table
Migration: 002
Date: 2025-10-01
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import db
from app.models.nectar_bot_models import NectarBot
from sqlalchemy import text
import re
import secrets


def slugify(name):
    """Generate a URL-friendly slug from bot name"""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    random_suffix = secrets.token_hex(4)
    return f"{slug}-{random_suffix}"


def upgrade():
    """Add slug column to nectar_bots table"""
    print("🔄 Starting migration 002: Add slug field to nectar_bots")

    try:
        # Add slug column (nullable first)
        print("  ➜ Adding slug column...")
        db.session.execute(text("""
            ALTER TABLE nectar_bots
            ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
        """))
        db.session.commit()
        print("  ✅ Slug column added")

        # Generate slugs for existing bots
        print("  ➜ Generating slugs for existing bots...")
        bots = NectarBot.query.all()

        for bot in bots:
            if not bot.slug:
                bot.slug = slugify(bot.name)
                print(f"    • {bot.name} -> {bot.slug}")

        db.session.commit()
        print(f"  ✅ Generated slugs for {len(bots)} bots")

        # Make slug NOT NULL
        print("  ➜ Making slug column NOT NULL...")
        db.session.execute(text("""
            ALTER TABLE nectar_bots
            ALTER COLUMN slug SET NOT NULL;
        """))
        db.session.commit()
        print("  ✅ Slug column set to NOT NULL")

        # Add unique constraint
        print("  ➜ Adding unique constraint on slug...")
        db.session.execute(text("""
            ALTER TABLE nectar_bots
            ADD CONSTRAINT IF NOT EXISTS nectar_bots_slug_unique
            UNIQUE (slug);
        """))
        db.session.commit()
        print("  ✅ Unique constraint added")

        # Add index for faster lookups
        print("  ➜ Adding index on slug...")
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_nectar_bots_slug
            ON nectar_bots(slug);
        """))
        db.session.commit()
        print("  ✅ Index created")

        print("✅ Migration 002 completed successfully!")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Migration failed: {str(e)}")
        raise


def downgrade():
    """Remove slug column from nectar_bots table"""
    print("🔄 Starting downgrade 002: Remove slug field from nectar_bots")

    try:
        # Drop index
        print("  ➜ Dropping index...")
        db.session.execute(text("""
            DROP INDEX IF EXISTS idx_nectar_bots_slug;
        """))
        db.session.commit()
        print("  ✅ Index dropped")

        # Drop unique constraint
        print("  ➜ Dropping unique constraint...")
        db.session.execute(text("""
            ALTER TABLE nectar_bots
            DROP CONSTRAINT IF EXISTS nectar_bots_slug_unique;
        """))
        db.session.commit()
        print("  ✅ Constraint dropped")

        # Drop column
        print("  ➜ Dropping slug column...")
        db.session.execute(text("""
            ALTER TABLE nectar_bots
            DROP COLUMN IF EXISTS slug;
        """))
        db.session.commit()
        print("  ✅ Column dropped")

        print("✅ Downgrade 002 completed successfully!")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Downgrade failed: {str(e)}")
        raise


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Nectar Bot slug migration')
    parser.add_argument('--downgrade', action='store_true', help='Downgrade instead of upgrade')
    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()
