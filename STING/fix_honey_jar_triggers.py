#!/usr/bin/env python3
"""Fix conflicting honey jar statistics triggers"""

import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_statistics_triggers():
    """Remove conflicting triggers and create a single unified trigger"""
    conn = psycopg2.connect(
        host="localhost",
        port=5433,  # STING uses port 5433
        database="sting_app",
        user="postgres",
        password="postgres"
    )

    try:
        with conn.cursor() as cur:
            # First, check existing triggers
            logger.info("🔍 Checking existing triggers...")
            cur.execute("""
                SELECT tgname, tgrelid::regclass, tgtype
                FROM pg_trigger
                WHERE tgrelid::regclass::text IN ('documents', 'honey_jars')
                ORDER BY tgrelid::regclass, tgname;
            """)

            triggers = cur.fetchall()
            logger.info(f"Found {len(triggers)} triggers:")
            for trigger in triggers:
                logger.info(f"  - {trigger[0]} on {trigger[1]}")

            # Drop all conflicting triggers
            logger.info("🗑️ Removing conflicting triggers...")
            trigger_drops = [
                "DROP TRIGGER IF EXISTS documents_stats_update ON documents;",
                "DROP TRIGGER IF EXISTS update_honey_jar_stats_on_insert ON documents;",
                "DROP TRIGGER IF EXISTS update_honey_jar_stats_on_delete ON documents;",
                "DROP TRIGGER IF EXISTS update_honey_jar_stats_on_update ON documents;",
                "DROP TRIGGER IF EXISTS update_document_count_trigger ON documents;",
                "DROP TRIGGER IF EXISTS honey_jar_document_count_trigger ON documents;",
                "DROP TRIGGER IF EXISTS update_reports_updated_at ON reports;",
                "DROP TRIGGER IF EXISTS update_honey_jars_updated_at ON honey_jars;"
            ]

            for drop_sql in trigger_drops:
                try:
                    cur.execute(drop_sql)
                    logger.info(f"  ✅ {drop_sql}")
                except Exception as e:
                    logger.warning(f"  ⚠️ {drop_sql} - {e}")

            # Create unified trigger function for honey jar stats
            logger.info("🔧 Creating unified trigger function...")
            cur.execute("""
                CREATE OR REPLACE FUNCTION update_honey_jar_document_count()
                RETURNS TRIGGER AS $$
                BEGIN
                    -- For INSERT
                    IF TG_OP = 'INSERT' THEN
                        UPDATE honey_jars
                        SET document_count = COALESCE(document_count, 0) + 1,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE id = NEW.honey_jar_id;
                        RETURN NEW;

                    -- For DELETE
                    ELSIF TG_OP = 'DELETE' THEN
                        UPDATE honey_jars
                        SET document_count = GREATEST(COALESCE(document_count, 0) - 1, 0),
                            last_updated = CURRENT_TIMESTAMP
                        WHERE id = OLD.honey_jar_id;
                        RETURN OLD;

                    -- For UPDATE (if honey_jar_id changes)
                    ELSIF TG_OP = 'UPDATE' AND OLD.honey_jar_id IS DISTINCT FROM NEW.honey_jar_id THEN
                        -- Decrement old honey jar
                        IF OLD.honey_jar_id IS NOT NULL THEN
                            UPDATE honey_jars
                            SET document_count = GREATEST(COALESCE(document_count, 0) - 1, 0),
                                last_updated = CURRENT_TIMESTAMP
                            WHERE id = OLD.honey_jar_id;
                        END IF;

                        -- Increment new honey jar
                        IF NEW.honey_jar_id IS NOT NULL THEN
                            UPDATE honey_jars
                            SET document_count = COALESCE(document_count, 0) + 1,
                                last_updated = CURRENT_TIMESTAMP
                            WHERE id = NEW.honey_jar_id;
                        END IF;
                        RETURN NEW;
                    END IF;

                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            # Create single trigger for all operations
            logger.info("📌 Creating unified trigger...")
            cur.execute("""
                CREATE TRIGGER unified_honey_jar_stats_trigger
                AFTER INSERT OR DELETE OR UPDATE OF honey_jar_id ON documents
                FOR EACH ROW
                EXECUTE FUNCTION update_honey_jar_document_count();
            """)

            # Recalculate all document counts to fix current state
            logger.info("📊 Recalculating all honey jar statistics...")
            cur.execute("""
                UPDATE honey_jars
                SET document_count = (
                    SELECT COUNT(*)
                    FROM documents
                    WHERE documents.honey_jar_id = honey_jars.id
                    AND documents.status != 'deleted'
                ),
                last_updated = CURRENT_TIMESTAMP;
            """)

            # Show results
            cur.execute("""
                SELECT name, document_count
                FROM honey_jars
                WHERE name LIKE '%Demo%'
                ORDER BY document_count DESC;
            """)

            results = cur.fetchall()
            logger.info("📋 Updated honey jar statistics:")
            for result in results:
                logger.info(f"  - {result[0]}: {result[1]} documents")

            conn.commit()
            logger.info("✅ Successfully fixed honey jar statistics triggers!")

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error fixing triggers: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_statistics_triggers()