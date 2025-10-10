# Scripts Directory Review - Developer Preview

## Current Status: 303 scripts (Too Many!)

The scripts directory contains a mix of useful utilities and legacy debug/test scripts from development.

## Recommended Actions

### ✅ KEEP - Essential Utilities (Move to `scripts/`)

**Installation & Setup (8 scripts)**
- `install_ollama.sh` - Install Ollama for local LLM
- `install_ollama_local.sh` - Local Ollama installation variant
- `check_and_install_ollama_wsl2.sh` - WSL2-specific Ollama setup
- `configure_ollama_endpoint.sh` - Configure Ollama endpoint
- `detect_ollama_host.sh` - Auto-detect Ollama host
- `wsl2_quick_setup.sh` - Quick WSL2 environment setup
- `wsl2_fix_certs.sh` - Fix certificate issues in WSL2
- `setup-grafana-dashboards.sh` - Set up monitoring dashboards

**Database & Migrations (2 scripts)**
- `apply-db-migrations.sh` - Apply database migrations
- `scripts/db_migrations/` - Keep entire directory

**Admin Management (4 scripts)**
- `create-new-admin.py` - Create admin users
- `create-service-api-key.py` - Generate service API keys
- `recover_admin_account.sh` - Emergency admin recovery
- `diagnose_admin_status.sh` - Check admin account status

**Maintenance & Operations (6 scripts)**
- `cleanup-docker.sh` - Clean up Docker resources
- `setup-docker-cleanup-cron.sh` - Automated cleanup
- `clear_sessions.sh` - Clear stale sessions
- `rotate-service-keys.sh` - Rotate API/service keys
- `recover_services.sh` - Service recovery utilities
- `dev_manager.sh` - Development management tool

**Demo & Testing (4 scripts)**
- `demo_complete_pipeline.sh` - Demo workflow
- `populate_knowledge_jar.sh` - Load sample knowledge
- `setup_default_honey_jars.py` - Create default jars
- `upload_sting_knowledge.py` - Upload STING docs

**Knowledge & Data (2 scripts)**
- `import_demo_data.sh` - Import demo datasets
- `generate_test_data.sh` - Generate test data

### 📁 ORGANIZE - Move to Subdirectories

**Create `scripts/admin/`** (Already exists - consolidate)
- All admin-related scripts

**Create `scripts/maintenance/`** (Already exists - consolidate)
- Maintenance and cleanup scripts

**Create `scripts/demo/`** (Already exists - consolidate)
- Demo and sample data scripts

**Create `scripts/utilities/`** (Already exists - consolidate)
- General utility scripts

**Create `scripts/troubleshooting/`** (Already exists - consolidate)
- Diagnostic and troubleshooting tools

### ❌ REMOVE - Development/Debug Scripts (Delete or Archive)

**Password/Auth Debug Scripts (30+ scripts) - OUTDATED**
Many of these relate to password authentication which was replaced by passwordless:
- `*password*.py` (15+ scripts)
- `fix_admin_password*.py`
- `reset_admin_password*.py`
- `*force_password*.py`
- `setup_admin_password.py`
- etc.

**Passkey Debug Scripts (20+ scripts) - TESTING ONLY**
Development testing scripts that aren't needed in production:
- `debug_passkey_*.py`
- `test-passkey-*.js`
- `test_passkey_*.py`
- `check_passkey_*.py`
- `debug_webauthn_*.py`
- `test_webauthn_*.py`

**Auth Flow Testing (30+ scripts) - TESTING ONLY**
- `test-auth-*.js` (10+ variants)
- `test-enrollment-*.js`
- `test-totp-*.js`
- `test-aal2-*.js`
- `test_login_*.py` (15+ variants)
- `test_browser_*.py`
- `test_kratos_*.py`

**UI/Frontend Testing (10+ scripts) - TESTING ONLY**
- `test-frontend-*.js`
- `test-sting-*.js`
- `verify-code-input.js`
- `capture-chat-screenshot.js`
- `test-sting-playwright.js`

**Theme/CSS Scripts (5+ scripts) - OUTDATED**
- `theme_consistency_*.py`
- `fix_theme_*.py`
- `README_THEME_TOOLS.md`

**Emergency/One-off Fixes (15+ scripts) - OBSOLETE**
- `emergency_*.py`
- `fix_csrf_*.sh/py`
- `fix_middleware_*.py`
- `quick_fix_*.py`

**Report System Testing (5+ scripts) - TESTING ONLY**
- `test_report_*.py`
- `clear-reports.sh`
- `clear-stuck-reports.py`

**Email/Mailpit Testing (10+ scripts) - TESTING ONLY**
- `test_email_*.py`
- `test_mailpit_*.py`
- `fix_mailpit_*.py`
- `fix_wsl2_mailpit.sh` (Keep for troubleshooting)

### 📋 Recommended Script Organization

```
scripts/
├── README.md                          # Script documentation
│
├── setup/                             # Installation & setup
│   ├── install_ollama.sh
│   ├── install_ollama_local.sh
│   ├── check_and_install_ollama_wsl2.sh
│   ├── configure_ollama_endpoint.sh
│   ├── detect_ollama_host.sh
│   ├── wsl2_quick_setup.sh
│   ├── wsl2_fix_certs.sh
│   └── setup-grafana-dashboards.sh
│
├── admin/                             # Admin management
│   ├── create-new-admin.py
│   ├── create-service-api-key.py
│   ├── recover_admin_account.sh
│   └── diagnose_admin_status.sh
│
├── database/                          # Database operations
│   ├── apply-db-migrations.sh
│   └── migrations/
│
├── maintenance/                       # System maintenance
│   ├── cleanup-docker.sh
│   ├── setup-docker-cleanup-cron.sh
│   ├── clear_sessions.sh
│   ├── rotate-service-keys.sh
│   ├── recover_services.sh
│   └── dev_manager.sh
│
├── demo/                              # Demo & sample data
│   ├── demo_complete_pipeline.sh
│   ├── populate_knowledge_jar.sh
│   ├── setup_default_honey_jars.py
│   ├── upload_sting_knowledge.py
│   ├── import_demo_data.sh
│   └── generate_test_data.sh
│
├── troubleshooting/                   # Diagnostic tools
│   ├── diagnose_admin_status.sh
│   ├── fix_wsl2_mailpit.sh
│   └── (other diagnostic scripts)
│
└── utilities/                         # General utilities
    └── (general utility scripts)
```

## Summary

### Current State
- **Total Scripts**: 303
- **Useful for Production**: ~30 (10%)
- **Development/Testing**: ~200 (66%)
- **Obsolete/Duplicates**: ~73 (24%)

### Recommended Action Plan

1. **Keep**: 30 essential scripts
2. **Move to subdirectories**: Organize kept scripts into logical categories
3. **Archive**: Move 200+ debug/test scripts to `scripts/archive/` or delete
4. **Document**: Create `scripts/README.md` explaining each useful script

### Benefits of Cleanup

- ✅ Easier to find useful scripts
- ✅ Cleaner repository
- ✅ Better developer onboarding
- ✅ Reduced confusion
- ✅ Smaller git clone size

## Essential Scripts List (30 scripts)

### Setup & Installation (8)
1. install_ollama.sh
2. install_ollama_local.sh
3. check_and_install_ollama_wsl2.sh
4. configure_ollama_endpoint.sh
5. detect_ollama_host.sh
6. wsl2_quick_setup.sh
7. wsl2_fix_certs.sh
8. setup-grafana-dashboards.sh

### Admin Management (4)
9. create-new-admin.py
10. create-service-api-key.py
11. recover_admin_account.sh
12. diagnose_admin_status.sh

### Database (2)
13. apply-db-migrations.sh
14. db_migrations/ (directory)

### Maintenance (6)
15. cleanup-docker.sh
16. setup-docker-cleanup-cron.sh
17. clear_sessions.sh
18. rotate-service-keys.sh
19. recover_services.sh
20. dev_manager.sh

### Demo & Data (6)
21. demo_complete_pipeline.sh
22. populate_knowledge_jar.sh
23. setup_default_honey_jars.py
24. upload_sting_knowledge.py
25. import_demo_data.sh
26. generate_test_data.sh

### Troubleshooting (4)
27. diagnose_admin_status.sh
28. fix_wsl2_mailpit.sh
29. troubleshooting/ (directory)
30. utilities/ (directory)

---

**Recommendation**: Create a new `scripts/` directory with only the 30 essential scripts, properly organized. Archive or delete the rest.
