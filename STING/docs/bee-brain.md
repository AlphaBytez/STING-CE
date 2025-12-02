# Bee Brain - AI-Powered Documentation System

## What is Bee Brain?

Bee Brain is STING's intelligent documentation system that powers the **Bee AI Assistant**. It automatically packages all STING documentation into optimized knowledge bases, ensuring Bee can answer questions accurately based on your specific STING version.

### Key Benefits

🧠 **Version-Aware Intelligence**
- Bee automatically knows which STING version you're running
- Answers are always accurate for your specific installation
- Major version compatibility prevents outdated advice

📚 **Always Up-to-Date**
- Documentation updates automatically via webhooks
- Admin-triggered manual updates available
- One-line command for quick updates

🎯 **Optimized for AI**
- Structured JSON format for fast retrieval
- Hierarchical documentation organization
- Instant keyword and semantic search

🔄 **Automatic Fallback**
- Gracefully handles missing versions
- Falls back to compatible documentation
- Never leaves you without help

## How It Works

When you ask Bee a question, it:
1. **Detects** your STING version from the `VERSION` file
2. **Loads** the matching bee_brain knowledge base
3. **Searches** documentation for relevant information
4. **Answers** using accurate, version-specific knowledge

### Version Compatibility

Bee Brain uses **semantic versioning** to ensure compatibility:

| Your STING Version | Bee Brain Used | Why |
|--------------------|----------------|-----|
| 1.0.0 | bee_brain_v1.0.0.json | Exact match |
| 1.2.5 | bee_brain_v1.2.5.json | Exact match (if available) |
| 1.2.5 | bee_brain_v1.2.0.json | Latest compatible 1.x (if 1.2.5 not found) |
| 2.0.0 | bee_brain_v2.0.0.json | Major version must match |

**Important:** Major version numbers must match to prevent incompatible documentation. STING 1.x will never load 2.x documentation and vice versa.

## Updating Bee Brain

### Quick Update (One-Liner)

Run this command as admin to update Bee Brain to the latest version:

```bash
curl -fsSL https://raw.githubusercontent.com/AlphaBytez/STING-CE/main/STING/scripts/update_bee_brain.sh | sudo bash
```

Or download and run locally:

```bash
sudo /opt/sting-ce/scripts/update_bee_brain.sh
```

### Manual Update via API

If you have admin access to the STING web interface:

```bash
# Check current status
curl -X GET http://localhost:5050/api/admin/bee-brain/status

# Update to latest version
curl -X POST http://localhost:5050/api/admin/bee-brain/update

# Force regeneration
curl -X POST http://localhost:5050/api/admin/bee-brain/update \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

### Generate Specific Version

Generate a bee_brain for a specific STING version:

```bash
cd /opt/sting-ce
python3 external_ai_service/bee_brain_generator.py --version 1.2.0
```

## Automatic Updates

### GitHub Webhook (Recommended)

Set up automatic bee_brain updates when documentation changes:

1. **Set webhook secret** in your STING environment:
   ```bash
   echo "GITHUB_WEBHOOK_SECRET=your-secret-key" >> /opt/sting-ce/.env
   ```

2. **Configure GitHub webhook** (if you maintain a fork):
   - URL: `https://your-sting.com/api/admin/bee-brain/webhook/github`
   - Content type: `application/json`
   - Secret: Your secret key
   - Events: `release` and `push`

3. **Behavior:**
   - **New releases**: Auto-generates bee_brain for that version
   - **Docs changes**: Auto-regenerates current version's bee_brain

## Admin Guide

### Check Bee Brain Status

```bash
# Via API
curl http://localhost:5050/api/admin/bee-brain/status | jq

# Via Python
python3 -c "
from external_ai_service.bee_brain_manager import BeeBrainManager
m = BeeBrainManager()
print(m.get_metadata())
"
```

### List Available Versions

```bash
ls -lh /opt/sting-ce/external_ai_service/bee_brains/
```

Output:
```
bee_brain_v1.0.0.json  (2.7 MB)
bee_brain_v1.1.0.json  (2.9 MB)
bee_brain_v2.0.0.json  (3.1 MB)
```

### Reload Without Regenerating

If you've manually updated documentation:

```bash
# Regenerate for current version
python3 /opt/sting-ce/external_ai_service/bee_brain_generator.py

# Reload in running service
curl -X POST http://localhost:5050/api/admin/bee-brain/reload
```

### Troubleshooting

#### Bee gives outdated answers

**Check loaded version:**
```bash
curl http://localhost:5050/api/admin/bee-brain/status | jq '.status.loaded_brain_version'
```

**Force update:**
```bash
curl -X POST http://localhost:5050/api/admin/bee-brain/update -H "Content-Type: application/json" -d '{"force": true}'
```

#### No bee_brain found for version

**Check STING version:**
```bash
cat /opt/sting-ce/VERSION
```

**Generate missing version:**
```bash
python3 /opt/sting-ce/external_ai_service/bee_brain_generator.py --version $(cat /opt/sting-ce/VERSION)
```

#### Bee Brain generation fails

**Check dependencies:**
```bash
pip3 install -r /opt/sting-ce/external_ai_service/requirements.txt
```

**Check docs directory exists:**
```bash
ls -la /opt/sting-ce/docs/
```

**Run with debug:**
```bash
python3 /opt/sting-ce/external_ai_service/bee_brain_generator.py --version 1.0.0
```

## For Developers

### Architecture

```
external_ai_service/
├── bee_brains/                    # Versioned knowledge bases
│   └── bee_brain_v1.0.0.json     # STING 1.0.0 docs (2.7 MB)
├── bee_brain_generator.py         # Generator script
├── bee_brain_manager.py           # Dynamic version loader
├── bee_brain_admin_api.py         # Admin REST API
└── bee_context_manager.py         # Context provider for Bee
```

### Bee Brain JSON Structure

```json
{
  "version": "1.0.0",
  "sting_version_compatibility": {
    "min": "1.0.0",
    "max": "1.999.999",
    "recommended": "1.0.0"
  },
  "created_at": "2025-10-20T19:00:00Z",
  "metadata": {
    "total_docs": 348,
    "total_size_kb": 2813.67,
    "checksum": "sha256:...",
    "format_version": "1.0"
  },
  "core_knowledge": {
    "identity": "## WHO AM I...",
    "platform": "## STING PLATFORM OVERVIEW...",
    "technical_architecture": "## TECHNICAL ARCHITECTURE..."
  },
  "documentation": {
    "README.md": "# STING Documentation...",
    "api": {
      "auth.md": "# Authentication API...",
      "reports.md": "# Reports API..."
    }
  }
}
```

### Adding Documentation

When you add new documentation to `docs/`:

1. **Regenerate bee_brain:**
   ```bash
   python3 external_ai_service/bee_brain_generator.py
   ```

2. **Reload in service:**
   ```bash
   curl -X POST http://localhost:5050/api/admin/bee-brain/reload
   ```

3. **Verify:**
   ```bash
   curl http://localhost:5050/api/admin/bee-brain/status | jq '.status.metadata'
   ```

## Best Practices

### For Admins

✅ **Update after STING upgrades**
```bash
sudo /opt/sting-ce/scripts/update_bee_brain.sh
```

✅ **Keep old versions** (for rollback)
```bash
# Don't delete old bee_brains - they're small and useful for debugging
ls -lh /opt/sting-ce/external_ai_service/bee_brains/
```

✅ **Monitor status regularly**
```bash
# Add to cron or monitoring
curl http://localhost:5050/api/admin/bee-brain/status
```

❌ **Don't manually edit bee_brain JSON files** - Always regenerate

### For Developers

✅ **Generate on release**
```bash
./manage_sting.sh release 1.2.0
python3 external_ai_service/bee_brain_generator.py --version 1.2.0
```

✅ **Test with older versions**
```bash
# Simulate older STING
echo "1.0.0" > VERSION
python3 -c "from external_ai_service.bee_brain_manager import BeeBrainManager; print(BeeBrainManager().get_metadata())"
```

✅ **Update on significant docs changes**
```bash
# After major documentation updates
python3 external_ai_service/bee_brain_generator.py
```

## FAQ

### Why JSON instead of Markdown?

- **Structured**: Easy to navigate programmatically
- **Hierarchical**: Preserves directory structure
- **Fast Search**: Instant keyword and semantic lookup
- **Metadata**: Rich versioning and compatibility info
- **LLM-Optimized**: Better for AI ingestion and chunking

### Does this work offline?

Yes! Bee Brain files are stored locally in `/opt/sting-ce/external_ai_service/bee_brains/`. Internet access is only needed for:
- Downloading updates via the 1-liner script
- GitHub webhook triggers (optional)

### Can I customize Bee's knowledge?

Yes! Add your own documentation to `/opt/sting-ce/docs/` and regenerate:

```bash
# Add your custom docs
echo "# Custom Guide" > /opt/sting-ce/docs/my-custom-guide.md

# Regenerate
python3 /opt/sting-ce/external_ai_service/bee_brain_generator.py

# Reload
curl -X POST http://localhost:5050/api/admin/bee-brain/reload
```

Bee will now know about your custom documentation!

### How big are bee_brain files?

Typical sizes:
- **STING 1.0.0**: ~2.7 MB (348 docs)
- **Future versions**: 2-5 MB depending on documentation

Storage is minimal - you can keep 10+ versions with <50 MB total.

### Does this affect performance?

No! Bee Brain files are:
- Loaded once at startup
- Cached in memory
- Indexed for fast search
- Typical load time: <1 second

## Support

- **Documentation**: See `/opt/sting-ce/external_ai_service/BEE_BRAIN_VERSIONING.md`
- **Logs**: `docker logs sting-ce-external-ai | grep -i "bee brain"`
- **Issues**: https://github.com/AlphaBytez/STING-CE/issues
- **Ask Bee**: Just ask the Bee AI Assistant! It knows how it works. 😊

---

**Pro Tip:** Bee Brain is part of what makes STING's AI assistant so accurate. Unlike generic chatbots, Bee knows your exact STING version and provides precise, tested guidance. Keep it updated for the best experience!
