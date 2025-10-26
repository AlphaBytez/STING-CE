# STING Admin Panel Documentation

## 📋 Overview

The STING Admin Panel provides centralized administrative controls for managing users, documents, compliance settings, and system recovery. This document outlines the current implementation status, dummy functions that need completion, and planned features.

## 🎯 Feature Status Matrix

| Feature | Status | Implementation | Priority |
|---------|--------|----------------|----------|
| **Pending Document Approval** | ✅ Complete | Fully functional honey jar document management | N/A |
| **Navigation Settings** | ✅ Complete | Customizable floating navigation system | N/A |
| **PII Configuration Manager** | ✅ Complete | Pattern management, compliance profiles | N/A |
| **Admin Recovery Tools** | ✅ Complete | Emergency access recovery system | N/A |
| **User Management** | ❌ Placeholder | Shows "Coming Soon" message | High |
| **Custom PII Rules Editor** | ❌ Placeholder | Shows "Feature Coming Soon" | Medium |
| **PII Detection Analytics** | ❌ Placeholder | Shows "View Analytics" button | Medium |
| **Add Custom Pattern Dialog** | ❌ Placeholder | Shows "Feature Coming Soon" | Low |

## 🏗️ Architecture Overview

### Frontend Components

```
AdminPanel.jsx (Main Container)
├── Pending Documents Tab ✅
├── User Management Tab ❌ (Placeholder)
├── Navigation Settings Tab ✅
├── PII Configuration Tab ✅
└── Admin Recovery Tab ✅

PII Configuration Manager
├── Pattern Management ✅
├── Compliance Profiles ✅  
├── Custom Rules ❌ (Placeholder)
└── Analytics ❌ (Placeholder)
```

### Backend Route Structure

```
/api/admin/
├── recovery/* ✅ (Complete)
├── setup/* ✅ (Complete)
└── registration/* ✅ (Complete)

/api/users/*
├── /stats ✅
├── /admins ✅
├── /promote ✅
├── /create-admin ✅
├── /profile ✅
└── / (list users) ✅

/api/pii/*
├── /patterns ✅
├── /frameworks ✅
├── /test ✅
├── /export ✅
└── /import ✅
```

## 🔧 Completed Features

### 1. Pending Document Approval System

**Location**: `/frontend/src/components/admin/AdminPanel.jsx` (lines 24-316)

**Functionality**:
- Honey jar selection dropdown
- Document list with metadata (filename, uploader, date, size, type)
- Approve/Reject actions with reason input
- Real-time document status updates
- Integration with Knowledge API

**API Endpoints**:
- `GET /api/knowledge/honey-jars` - List available honey jars
- `GET /api/knowledge/honey-jars/{id}/pending-documents` - Get pending docs
- `POST /api/knowledge/honey-jars/{id}/documents/{doc_id}/approve` - Approve
- `POST /api/knowledge/honey-jars/{id}/documents/{doc_id}/reject` - Reject with reason

### 2. Navigation Settings Manager

**Location**: `/frontend/src/components/admin/NavigationSettings.jsx`

**Functionality**:
- Persistent vs. Scrollable navigation item management
- Drag and drop reordering (move up/down/between sections)
- Enable/disable toggle for navigation items
- Real-time preview with custom event dispatch
- Local storage persistence with live updates

**Features**:
- Icon mapping for all navigation items
- Badge support (Enterprise, Admin Only)
- Reset to defaults functionality
- Visual feedback for unsaved changes

### 3. PII Configuration Manager

**Location**: `/frontend/src/components/admin/PIIConfigurationManager.jsx`

**Functionality**:
- **Pattern Management**: 9 default patterns (SSN, Medical Records, Case Numbers)
- **Compliance Profiles**: HIPAA, GDPR, Attorney-Client frameworks
- **Pattern Testing**: Live regex testing with sample text
- **Import/Export**: JSON configuration backup/restore
- **Risk Assessment**: High/Medium/Low risk categorization

**Backend Integration**:
- Pattern persistence with database storage TODOs
- Settings framework for advanced profile configuration
- Real-time pattern validation and testing

### 4. Admin Recovery Tools

**Location**: `/frontend/src/components/admin/AdminRecovery.jsx`

**Functionality**:
- **Recovery Token Generation**: 15-minute temporary tokens
- **Master Recovery Secret**: Emergency password reset
- **TOTP Disable**: Remove 2FA for locked users
- **Secure Password Generation**: Auto-generated or custom passwords
- **Audit Logging**: All recovery actions are logged

**Security Features**:
- Token expiration management
- Multiple authentication methods
- Emergency access for locked accounts
- Copy-to-clipboard for secure credential sharing

## ❌ Placeholder Features (Need Implementation)

### 1. User Management Tab

**Current State**: 
```jsx
// AdminPanel.jsx lines 318-326
{activeTab === 'users' && (
  <div className="text-center py-12 standard-card rounded-2xl">
    <Users className="w-16 h-16 text-gray-500 mx-auto mb-4" />
    <h3 className="text-lg font-medium text-gray-300 mb-2">User Management Coming Soon</h3>
    <p className="text-gray-500">
      User management features including role assignment and permissions will be available in the next update.
    </p>
  </div>
)}
```

**Implementation Requirements**:
- User listing with pagination and search
- Role assignment (user, admin, super_admin)
- User activation/deactivation
- Password reset forcing
- Session management (view active sessions, force logout)
- User creation wizard
- Bulk operations

**Backend Support**: 
✅ Already exists in `/app/routes/user_routes.py`:
- `GET /api/users/` - List users with pagination
- `POST /api/users/{id}/promote` - Promote to admin
- `POST /api/users/create-admin` - Create admin user
- `GET /api/users/stats` - User statistics

### 2. Custom PII Rules Editor

**Current State**:
```jsx
// PIIConfigurationManager.jsx lines 630-641
{activeTab === 'custom' && (
  <div className="text-center py-12">
    <Edit className="w-8 h-8 text-gray-400 mx-auto mb-4" />
    <h3 className="text-lg font-semibold text-white mb-2">Custom Rules Editor</h3>
    <p className="text-gray-400 mb-4">Create organization-specific PII detection rules</p>
    <button className="px-6 py-2 bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 rounded-lg transition-colors">
      Create Custom Rule
    </button>
  </div>
)}
```

**Implementation Requirements**:
- Regex pattern builder with validation
- Category assignment and risk level setting
- Compliance framework mapping
- Pattern testing interface
- Custom rule versioning
- Export/import for custom rules

### 3. PII Detection Analytics

**Current State**:
```jsx
// PIIConfigurationManager.jsx lines 643-655
{activeTab === 'analytics' && (
  <div className="text-center py-12">
    <RefreshCw className="w-8 h-8 text-gray-400 mx-auto mb-4" />
    <h3 className="text-lg font-semibold text-white mb-2">Detection Analytics</h3>
    <p className="text-gray-400 mb-4">View PII detection statistics and trends</p>
    <button className="px-6 py-2 bg-blue-500/20 text-blue-400 hover:blue-500/30 rounded-lg transition-colors">
      View Analytics
    </button>
  </div>
)}
```

**Implementation Requirements**:
- Detection frequency charts
- Risk level distribution
- Compliance framework coverage
- Pattern effectiveness metrics
- Time-based trend analysis
- Export analytics reports

### 4. Add Custom Pattern Dialog

**Current State**:
```jsx
// PIIConfigurationManager.jsx lines 737-761
{showAddPatternDialog && (
  <div className="text-center py-8">
    <Plus className="w-8 h-8 text-amber-400 mx-auto mb-3" />
    <h3 className="text-lg font-semibold text-white mb-2">Feature Coming Soon</h3>
    <p className="text-gray-400 mb-4">Custom pattern creation is under development.</p>
    <p className="text-gray-400 text-sm">For now, use the Import feature to add patterns from JSON files.</p>
  </div>
)}
```

**Implementation Requirements**:
- Form-based pattern creation
- Regex builder with syntax highlighting
- Pattern validation and testing
- Category and compliance assignment
- Risk level assessment tools

## 🚧 Backend TODOs (Need Implementation)

### 1. PII Pattern Persistence

**Location**: `/app/routes/pii_routes.py:282`
```python
# TODO: Save to database or configuration storage
```

**Required Implementation**:
- Database schema for PII patterns
- Pattern versioning system
- Configuration storage integration
- Pattern validation service

### 2. Email Service Integration

**Location**: `/app/routes/report_routes.py:697`
```python
# TODO: Implement email service integration
```

**Required Implementation**:
- SMTP configuration management
- Email template system
- Notification preferences
- Email queue and retry logic

### 3. Authentication Improvements

**Multiple Locations**:
- `/app/routes/llm_routes.py:34` - "TODO: Implement proper authentication check"
- `/app/routes/user_routes.py:26` - "TODO: Implement proper authentication check"

**Required Implementation**:
- Consistent auth middleware
- Role-based access control (RBAC)
- API key authentication integration
- Session validation improvements

### 4. TOTP and WebAuthn Integration

**Location**: `/app/routes/admin_setup_routes.py:405-406`
```python
# TODO: Set up TOTP credentials in Kratos
# TODO: Initialize WebAuthn/Passkey registration
```

**Required Implementation**:
- Kratos TOTP configuration
- WebAuthn enrollment flow
- Multi-factor authentication setup
- Recovery method configuration

### 5. WebAuthn Challenge Generation

**Location**: `/app/routes/aal2_routes.py:99`
```python
# TODO: Integrate with existing WebAuthn challenge generation
```

**Required Implementation**:
- Challenge generation service
- AAL2 verification flow
- WebAuthn credential validation
- Fallback authentication methods

## 🗺️ Development Roadmap

### Phase 1: High Priority (User Management)
1. **Complete User Management Tab**
   - Implement user listing component
   - Add role assignment interface
   - Create user management API integration
   - Add bulk operations support

2. **Enhance Authentication System**
   - Implement consistent auth middleware
   - Complete RBAC system
   - Integrate API key authentication
   - Add session management tools

### Phase 2: Medium Priority (PII Analytics)
1. **PII Detection Analytics**
   - Create analytics dashboard
   - Implement detection metrics
   - Add trend analysis charts
   - Build export functionality

2. **Custom PII Rules Editor**
   - Build pattern creation interface
   - Add regex validation tools
   - Implement pattern testing
   - Create custom rule storage

### Phase 3: Low Priority (Enhancements)
1. **Email Service Integration**
   - SMTP configuration system
   - Email template management
   - Notification preferences
   - Email queue implementation

2. **Enhanced Recovery Tools**
   - Multi-factor recovery options
   - Audit trail improvements
   - Recovery analytics
   - Policy-based recovery rules

## 🔌 Integration Points

### 1. Knowledge Service
- Honey jar document approval
- Document metadata management
- Upload validation and processing

### 2. Kratos Authentication
- Identity management
- Session validation
- TOTP/WebAuthn enrollment
- Password policy enforcement

### 3. Redis Session Store
- Session persistence
- Session invalidation
- Multi-service session sharing

### 4. PII Compliance Service
- Pattern detection engine
- Compliance framework validation
- Risk assessment algorithms
- Audit logging

## 📊 Metrics and Monitoring

### Current Metrics Available
- User statistics (total, admin, active)
- PII detection counts
- Document approval statistics
- Recovery action audit logs

### Planned Metrics
- User engagement analytics
- Pattern effectiveness scores
- Compliance coverage assessment
- System performance metrics

## 🔐 Security Considerations

### Authentication
- Multi-factor authentication required for admin actions
- Session timeout and invalidation
- API key-based service authentication
- Role-based access control

### Data Protection
- PII pattern encryption at rest
- Secure credential storage
- Audit logging for all admin actions
- Recovery action verification

### Compliance
- GDPR data handling compliance
- HIPAA security requirements
- SOC 2 audit trail maintenance
- Data retention policy enforcement

---

**Last Updated**: August 2025  
**Status**: Active Development  
**Next Review**: After User Management implementation