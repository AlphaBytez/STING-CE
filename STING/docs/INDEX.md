# STING Documentation Index

## 📚 Documentation Structure

### Root Documentation
- [`CLAUDE.md`](../CLAUDE.md) - Active development guide for Claude Code
- [`README.md`](../README.md) - Project overview and getting started
- [`CREDITS.md`](../CREDITS.md) - Attribution and credits
- [`LICENSE-THIRD-PARTY.md`](../LICENSE-THIRD-PARTY.md) - Third-party licenses

### 📁 Documentation Categories

#### 🏗️ [Architecture](./architecture/)
System design and technical architecture documentation
- Module dependencies
- Database schema
- Implementation status
- QE Bee architecture ([qe-bee-architecture.md](./architecture/qe-bee-architecture.md))

#### 🚀 [Deployment](./deployment/)
Installation, deployment, and configuration guides
- Clean install checklist
- Post-reinstall procedures
- Vault configuration fixes

#### 🎨 [Features](./features/)
Feature-specific documentation
- Agents system
- Theme system
- Bee chat and honey jars
- Tiered authentication
- **QE Bee** - Output validation agent ([QE_BEE_REVIEW_SYSTEM.md](./features/QE_BEE_REVIEW_SYSTEM.md))

#### 🔧 [Troubleshooting](./troubleshooting/)
Debugging guides and issue resolution
- Authentication fixes (AAL2, passkeys, TOTP)
- Email configuration issues
- Session management problems
- WSL2-specific fixes
- Security fixes

#### 📖 [Guides](./guides/)
Step-by-step setup and usage guides
- **VirtualBox OVA Quick Start** - Importing and configuring the OVA ([VIRTUALBOX_OVA_QUICKSTART.md](./guides/VIRTUALBOX_OVA_QUICKSTART.md))
- Ollama setup
- Headscale community support
- Testing procedures

#### 🔒 [Security](./security/)
Security-related documentation
- Security policies
- Vulnerability reports
- Compliance information

#### 💻 [Technical](./technical/)
Technical specifications and API documentation
- API documentation
- Database schemas
- Protocol specifications

#### 🛠️ [Platform](./platform/)
Platform-specific requirements and configurations
- Service implementation checklist
- Configuration management
- Infrastructure setup

## 🔍 Quick Reference

### Most Important Documents
1. **Development**: [`CLAUDE.md`](../CLAUDE.md) - Essential for development with Claude Code
2. **Getting Started**: [`README.md`](../README.md) - Project overview
3. **Authentication**: [`troubleshooting/AUTH_FLOW_MAP.md`](./troubleshooting/AUTH_FLOW_MAP.md) - Complete auth flow documentation
4. **Testing**: [`TESTING.md`](./TESTING.md) - Test procedures and frameworks

### Recent Updates
- **QE Bee Review System** - Automated output validation agent (November 2025)
- Tiered Authentication System implementation
- Vault persistent storage configuration
- AAL2 passkey verification fixes
- Session synchronization improvements

## 📝 Documentation Maintenance

### Adding New Documentation
1. Place in appropriate category directory
2. Update this INDEX.md file
3. Add references in CLAUDE.md if relevant for development
4. Follow naming conventions: `FEATURE_NAME.md` or `feature-name.md`

### Documentation Standards
- Use clear, descriptive filenames
- Include creation/update dates in documents
- Add table of contents for long documents
- Use markdown formatting consistently
- Include code examples where relevant

---
*Last Updated: November 2025*