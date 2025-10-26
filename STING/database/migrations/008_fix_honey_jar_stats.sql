-- Fix honey jar stats update trigger
-- Ensures document counts are properly maintained

-- Create function to recalculate honey jar stats
CREATE OR REPLACE FUNCTION update_honey_jar_stats(jar_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE honey_jars
    SET
        document_count = (
            SELECT COUNT(*)
            FROM documents
            WHERE honey_jar_id = jar_id AND status != 'deleted'
        ),
        embedding_count = (
            SELECT COALESCE(SUM(embedding_count), 0)
            FROM documents
            WHERE honey_jar_id = jar_id AND status != 'deleted'
        ),
        total_size_bytes = (
            SELECT COALESCE(SUM(size_bytes), 0)
            FROM documents
            WHERE honey_jar_id = jar_id AND status != 'deleted'
        ),
        last_updated = NOW()
    WHERE id = jar_id;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update stats when documents change
CREATE OR REPLACE FUNCTION trigger_update_honey_jar_stats()
RETURNS trigger AS $$
BEGIN
    -- Update stats for the affected honey jar
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        PERFORM update_honey_jar_stats(NEW.honey_jar_id);
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM update_honey_jar_stats(OLD.honey_jar_id);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS documents_stats_update ON documents;

-- Create new trigger
CREATE TRIGGER documents_stats_update
    AFTER INSERT OR UPDATE OR DELETE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_honey_jar_stats();

-- Fix existing honey jar stats by recalculating them
DO $$
DECLARE
    jar_record RECORD;
BEGIN
    FOR jar_record IN SELECT id FROM honey_jars LOOP
        PERFORM update_honey_jar_stats(jar_record.id);
    END LOOP;
END
$$;

-- Add comment
COMMENT ON FUNCTION update_honey_jar_stats(UUID) IS 'Recalculates honey jar statistics based on current documents';
COMMENT ON FUNCTION trigger_update_honey_jar_stats() IS 'Trigger function to auto-update honey jar stats when documents change';