# Bee Brain Versioning System

## Overview

The Bee Brain Versioning System provides intelligent, version-aware documentation management for STING's AI assistant. It automatically packages all documentation into versioned knowledge bases that match STING releases, ensuring Bee always has accurate, compatible information.

## Key Features

✅ **Version-Aware**: Automatically matches STING version for compatibility
✅ **Optimal LLM Format**: Structured JSON optimized for AI ingestion
✅ **Automatic Updates**: GitHub webhook support for instant documentation updates
✅ **Admin Control**: REST API for manual updates and management
✅ **Graceful Degradation**: Falls back to legacy system if needed
✅ **Rollback Support**: Keep multiple versions for safety

## Architecture

```
external_ai_service/
├── bee_brains/                        # Versioned knowledge bases
│   ├── bee_brain_v1.0.0.json         # STING 1.0.0 docs
│   ├── bee_brain_v1.0.1.json         # STING 1.0.1 docs
│   └── compatibility_matrix.json     # Version compatibility rules
├── bee_brain_generator.py             # Generator script
├── bee_brain_manager.py               # Dynamic version loader
├── bee_brain_admin_api.py             # Admin REST API
└── bee_context_manager.py             # Updated to use manager
```

## How It Works

### 1. Version Detection

When STING starts, `BeeBrainManager` reads the `VERSION` file and loads the appropriate bee_brain:

```python
STING 1.0.0 → bee_brain_v1.0.0.json
STING 1.5.2 → bee_brain_v1.5.2.json (or latest 1.x if not found)
STING 2.0.0 → bee_brain_v2.0.0.json
```

### 2. Compatibility Checking

Each bee_brain includes compatibility metadata:

```json
{
  "version": "1.0.0",
  "sting_version_compatibility": {
    "min": "1.0.0",
    "max": "1.999.999",
    "recommended": "1.0.0"
  }
}
```

**Rules**:
- Major version must match (1.x → 1.x, 2.x → 2.x)
- Falls back to latest compatible version if exact match not found
- Prevents loading 2.x docs on 1.x STING (breaking changes)

### 3. Automatic Fallback

```
1. Try exact version match (1.0.0 → bee_brain_v1.0.0.json)
2. Try latest compatible major version (1.x → latest 1.x bee_brain)
3. Check compatibility matrix
4. Fall back to legacy bee_brain_v2.0.0_phi4.md
```

## Usage

### Generate Bee Brain Manually

```bash
# Generate for current STING version (from VERSION file)
python3 external_ai_service/bee_brain_generator.py

# Generate for specific version
python3 external_ai_service/bee_brain_generator.py --version 1.0.1

# Custom output directory
python3 external_ai_service/bee_brain_generator.py --output /path/to/bee_brains/
```

### Admin API Endpoints

All endpoints require admin authentication (TODO: implement).

#### Check Status

```bash
GET /api/admin/bee-brain/status

Response:
{
  "success": true,
  "status": {
    "sting_version": "1.0.0",
    "loaded_brain_version": "1.0.0",
    "available_versions": ["1.0.0", "1.0.1"],
    "compatibility": {...},
    "metadata": {...}
  }
}
```

#### Generate New Version

```bash
POST /api/admin/bee-brain/generate
Content-Type: application/json

{
  "version": "1.0.1",  // optional
  "output_dir": "/custom/path"  // optional
}

Response:
{
  "success": true,
  "message": "Bee brain generated successfully",
  "output": "...",
  "reloaded": true
}
```

#### Reload Bee Brain

```bash
POST /api/admin/bee-brain/reload

Response:
{
  "success": true,
  "message": "Bee brain reloaded successfully",
  "loaded_version": "1.0.0",
  "metadata": {...}
}
```

#### Update (Generate + Reload)

```bash
POST /api/admin/bee-brain/update
Content-Type: application/json

{
  "version": "1.0.1",  // optional
  "force": false  // regenerate even if exists
}

Response:
{
  "success": true,
  "message": "Bee brain updated successfully",
  "loaded_version": "1.0.1",
  "reloaded": true
}
```

### GitHub Webhook

Automatically regenerate bee_brain when documentation changes.

#### Setup

1. **Set webhook secret** in STING:
   ```bash
   export GITHUB_WEBHOOK_SECRET="your-secret-key"
   ```

2. **Configure GitHub webhook**:
   - URL: `https://your-sting.com/api/admin/bee-brain/webhook/github`
   - Content type: `application/json`
   - Secret: Your secret key
   - Events: `release` and `push`

#### Behavior

**On Release** (tag created):
- Extracts version from tag (e.g., `v1.0.1` → `1.0.1`)
- Generates `bee_brain_v1.0.1.json`
- Reloads if compatible with current STING version

**On Push to main** (docs modified):
- Detects changes to `docs/`, `README.md`, `ARCHITECTURE.md`, etc.
- Regenerates current version's bee_brain
- Reloads immediately

## Bee Brain Format

### Structure

```json
{
  "version": "1.0.0",
  "sting_version_compatibility": {
    "min": "1.0.0",
    "max": "1.999.999",
    "recommended": "1.0.0"
  },
  "created_at": "2025-10-20T19:00:00Z",
  "generated_by": "bee_brain_generator",
  "metadata": {
    "total_docs": 348,
    "total_size_kb": 2813.67,
    "checksum": "sha256:...",
    "format_version": "1.0"
  },
  "core_knowledge": {
    "identity": "## WHO AM I...",
    "platform": "## STING PLATFORM OVERVIEW...",
    "system_awareness": "## SYSTEM AWARENESS...",
    "technical_architecture": "## TECHNICAL ARCHITECTURE...",
    "security_features": "### Key Security Features..."
  },
  "documentation": {
    "README.md": "# STING Documentation...",
    "ARCHITECTURE.md": "# Architecture...",
    "api": {
      "auth.md": "# Authentication API...",
      "reports.md": "# Reports API..."
    },
    "deployment": {
      "docker.md": "# Docker Deployment...",
      "kubernetes.md": "# Kubernetes..."
    }
  },
  "version_notes": "Added hostname configuration docs"
}
```

### Why JSON?

- **Structured**: Easy to navigate programmatically
- **Hierarchical**: Preserves directory structure
- **Metadata**: Rich metadata for versioning
- **LLM-Friendly**: Can be easily chunked and embedded
- **Searchable**: Fast keyword and semantic search
- **Cacheable**: Efficient caching strategies

## Version Compatibility Example

| STING Version | Bee Brain Loaded | Reason |
|---------------|------------------|---------|
| 1.0.0 | bee_brain_v1.0.0.json | Exact match |
| 1.0.1 | bee_brain_v1.0.1.json | Exact match |
| 1.5.0 | bee_brain_v1.4.0.json | Latest 1.x available |
| 2.0.0 | bee_brain_v2.0.0.json | Major version must match |
| 2.1.0 | bee_brain_v2.0.0.json | Latest 2.x (2.1.0 not found) |

## Best Practices

### For Developers

1. **Generate on Release**: Always generate bee_brain when cutting a release
   ```bash
   ./manage_sting.sh release 1.0.1
   python3 external_ai_service/bee_brain_generator.py --version 1.0.1
   ```

2. **Test Locally**: Test with older bee_brain versions to ensure compatibility
   ```bash
   # Simulate older STING
   echo "0.9.0" > VERSION
   python3 -c "from external_ai_service.bee_brain_manager import BeeBrainManager; m = BeeBrainManager(); print(m.get_metadata())"
   ```

3. **Update on Docs Changes**: Regenerate when documentation changes significantly
   ```bash
   python3 external_ai_service/bee_brain_generator.py
   curl -X POST http://localhost:5050/api/admin/bee-brain/reload
   ```

### For Admins

1. **Monitor Status**: Check bee_brain status regularly
   ```bash
   curl http://localhost:5050/api/admin/bee-brain/status
   ```

2. **Set Up Webhook**: Enable automatic updates for documentation changes

3. **Keep Old Versions**: Don't delete old bee_brains (needed for rollbacks)
   ```bash
   ls -lh external_ai_service/bee_brains/
   # Keep at least last 3 major versions
   ```

4. **Update After Upgrade**: After upgrading STING, ensure bee_brain is compatible
   ```bash
   # After upgrading to 2.0.0
   python3 external_ai_service/bee_brain_generator.py --version 2.0.0
   ```

## Troubleshooting

### Bee brain not loading

```bash
# Check status
curl http://localhost:5050/api/admin/bee-brain/status

# Check files
ls -la external_ai_service/bee_brains/

# Check logs
docker logs sting-ce-external-ai | grep -i "bee brain"
```

### Wrong version loaded

```bash
# Check VERSION file
cat VERSION

# Check available versions
python3 -c "from external_ai_service.bee_brain_manager import BeeBrainManager; print(BeeBrainManager().list_available_versions())"

# Force reload
curl -X POST http://localhost:5050/api/admin/bee-brain/reload
```

### Generation fails

```bash
# Run generator with debug
python3 external_ai_service/bee_brain_generator.py --version 1.0.0

# Check STING root path
python3 -c "from pathlib import Path; print(Path('external_ai_service/bee_brain_generator.py').parent.parent)"

# Check docs exist
ls -la docs/
```

## Migration from Legacy

Existing systems will automatically use the new versioning system when available, with graceful fallback:

1. **First run**: Generates `bee_brain_v1.0.0.json` from current docs
2. **Loads versioned brain**: BeeBrainManager takes over
3. **Fallback**: If any issues, uses legacy `bee_brain_v2.0.0_phi4.md`

**No action required** - migration is automatic!

## Future Enhancements

- [ ] Embedding generation for semantic search
- [ ] Differential updates (only changed docs)
- [ ] Compression for large documentation sets
- [ ] CDN support for remote bee_brain hosting
- [ ] Multi-language support
- [ ] A/B testing different brain configurations

## Support

For issues or questions:
- Check logs: `docker logs sting-ce-external-ai`
- File issue: https://github.com/AlphaBytez/STING-CE-Public/issues
- Documentation: https://docs.sting.local
