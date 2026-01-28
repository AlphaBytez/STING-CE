-- Temporarily disable the problematic trigger that's preventing document uploads
-- This allows demo generation to work while we investigate the trigger issue

-- Disable the trigger that calls update_honey_jar_stats
DROP TRIGGER IF EXISTS trigger_update_honey_jar_stats ON documents;

-- Optionally, recreate a simpler version without the problematic function call
-- CREATE TRIGGER trigger_update_honey_jar_stats
--     AFTER INSERT OR UPDATE OR DELETE ON documents
--     FOR EACH ROW
--     EXECUTE FUNCTION update_honey_jar_stats_simple();

-- Note: Honey jar stats won't update automatically until trigger is fixed
-- Manual stats update can be done via:
-- UPDATE honey_jars SET document_count = (SELECT COUNT(*) FROM documents WHERE honey_jar_id = honey_jars.id);