# STING Module Dependencies

This document outlines the dependencies between modules in the refactored manage_sting.sh system.

## Module Overview

The STING management system consists of 15 specialized modules:

### Core Modules (Always Loaded)
- **bootstrap.sh** - Basic logging before full module system loads
- **core.sh** - Core utilities and system checks  
- **logging.sh** - Enhanced logging with file output and progress indicators
- **environment.sh** - Environment setup and variable management
- **configuration.sh** - Configuration file management and validation

### Feature Modules (Loaded on Demand)
- **interface.sh** - Command-line interface and main entry point
- **services.sh** - Docker service management and health monitoring
- **docker.sh** - Docker operations, networks, and containers
- **installation.sh** - Installation, uninstallation, and system setup
- **file_operations.sh** - File copying, syncing, and directory management
- **security.sh** - SSL certificates, Vault, and secret management
- **health.sh** - System health checks and monitoring
- **backup.sh** - Backup creation, restoration, and maintenance
- **development.sh** - Development tools and testing utilities
- **model_management.sh** - LLM model downloading and management
- **native_llm.sh** - Native LLM service management with MPS support

## Dependency Relationships

### bootstrap.sh
- **Dependencies**: None (standalone)
- **Provides**: Basic log_message() function
- **Used by**: manage_sting.sh (main script)

### core.sh  
- **Dependencies**: bootstrap.sh (for logging)
- **Provides**: System utilities, disk space checks, root verification
- **Used by**: All modules (provides safe_log function)

### logging.sh
- **Dependencies**: bootstrap.sh (enhances existing logging)
- **Provides**: Enhanced logging, progress indicators, log levels
- **Used by**: All modules that need advanced logging

### environment.sh
- **Dependencies**: core.sh, logging.sh
- **Provides**: Environment setup, variable loading, SSL certificate generation
- **Used by**: installation.sh, services.sh, configuration.sh

### configuration.sh
- **Dependencies**: core.sh, logging.sh
- **Provides**: Config file management, HF token handling, environment file generation
- **Used by**: installation.sh, interface.sh (update command)

### interface.sh
- **Dependencies**: core.sh, logging.sh
- **Loads on demand**: All other modules based on command
- **Provides**: Command parsing, help system, main() function
- **Used by**: manage_sting.sh (main entry point)

### services.sh
- **Dependencies**: core.sh, logging.sh, docker.sh, health.sh
- **Provides**: Service start/stop/restart, health monitoring
- **Used by**: interface.sh, installation.sh

### docker.sh
- **Dependencies**: core.sh, logging.sh
- **Provides**: Docker operations, network management, container utilities
- **Used by**: services.sh, installation.sh, interface.sh

### installation.sh
- **Dependencies**: core.sh, logging.sh, file_operations.sh, configuration.sh, services.sh
- **Provides**: Installation workflow, dependency checking, msting command setup
- **Used by**: interface.sh

### file_operations.sh
- **Dependencies**: core.sh, logging.sh
- **Provides**: File copying, directory management, service code syncing
- **Used by**: installation.sh, interface.sh (update command)

### security.sh
- **Dependencies**: core.sh, logging.sh, services.sh
- **Provides**: SSL certificates, Vault operations, secret management
- **Used by**: environment.sh, installation.sh, services.sh

### health.sh
- **Dependencies**: core.sh, logging.sh
- **Provides**: Health checks, system monitoring, model validation
- **Used by**: services.sh, interface.sh (status command)

### backup.sh
- **Dependencies**: core.sh, logging.sh, file_operations.sh
- **Provides**: Backup creation, restoration, encryption
- **Used by**: interface.sh

### development.sh
- **Dependencies**: core.sh, logging.sh, docker.sh
- **Provides**: Development tools, testing utilities, cleanup functions
- **Used by**: interface.sh

### model_management.sh
- **Dependencies**: core.sh, logging.sh, configuration.sh
- **Provides**: Model downloading, directory setup, cleanup
- **Used by**: interface.sh, installation.sh

### native_llm.sh
- **Dependencies**: core.sh, logging.sh, services.sh
- **Provides**: Native LLM service management, MPS support
- **Used by**: services.sh, interface.sh

## Loading Strategy

### Bootstrap Loading (manage_sting.sh)
1. **bootstrap.sh** - Always loaded first for basic logging
2. **Core modules** - Loaded in dependency order:
   - core.sh
   - logging.sh 
   - environment.sh
   - configuration.sh
3. **interface.sh** - Loaded to provide main() function

### On-Demand Loading (interface.sh)
Other modules are loaded only when needed by specific commands:

- **status**: services.sh, docker.sh, health.sh
- **install/reinstall**: installation.sh, environment.sh
- **start/stop/restart**: services.sh
- **build**: docker.sh
- **update**: file_operations.sh, services.sh
- **backup/restore**: backup.sh
- **uninstall**: installation.sh
- **cleanup**: development.sh

## Environment Variables

### Required by All Modules
- `INSTALL_DIR` - Installation directory
- `CONFIG_DIR` - Configuration directory  
- `LOG_DIR` - Log directory
- `SOURCE_DIR` - Source code directory
- `SCRIPT_DIR` - Script directory

### Module-Specific Variables
- **docker.sh**: Docker-related environment variables
- **services.sh**: Service ports and URLs
- **security.sh**: SSL and Vault configuration
- **model_management.sh**: Model directories and HF_TOKEN

## Error Handling

### Module Loading Failures
- Core modules: Script exits with error
- Feature modules: Graceful fallback with error message

### Function Dependencies
- Functions check for required modules and load them dynamically
- Safe fallbacks when optional dependencies aren't available

## Best Practices

1. **Load modules only when needed** to minimize startup time
2. **Check dependencies** before calling functions from other modules  
3. **Use safe_log()** in core functions that may be called before logging.sh loads
4. **Export required environment variables** for Docker compose operations
5. **Handle module loading failures** gracefully with appropriate error messages

## Testing Dependencies

Each module includes tests that verify:
- Required dependencies are available
- Functions work with missing optional dependencies
- Environment variables are properly set
- Inter-module communication works correctly