# Kratos Authentication Refactor Plan

## Overview
Refactor STING authentication to use Kratos native flows and best practices, removing custom middleware and duplicate state management.

## Phase 1: Configuration Updates

### 1.1 Update Kratos Configuration
- Remove custom fields from identity schema (keep only standard fields)
- Configure proper cookie settings for cross-container access
- Enable native flows for password changes
- Set up webhooks for post-action events

### 1.2 Remove Custom Middleware
- Remove force_password_change middleware
- Remove custom password change endpoints
- Simplify auth middleware to only validate sessions

## Phase 2: Backend Simplification

### 2.1 Session Management
- Use Kratos as single source of truth
- Remove UserSettings table fields that duplicate Kratos data
- Trust Kratos session validation completely

### 2.2 API Changes
- Remove custom auth endpoints that duplicate Kratos
- Add webhook endpoints for Kratos events
- Simplify user service to work with Kratos identities

## Phase 3: Frontend Updates

### 3.1 Use Kratos SDK
- Install @ory/kratos-client
- Replace custom API calls with SDK methods
- Use Kratos UI nodes for forms

### 3.2 Simplify Auth Flow
- Remove custom enrollment components
- Use Kratos self-service UI or render UI nodes
- Handle Kratos redirects properly

## Phase 4: Migration

### 4.1 Data Migration
- Migrate any custom user data to Kratos metadata
- Clean up UserSettings table
- Update existing sessions

### 4.2 Testing
- Test login flow
- Test password change flow
- Test session management
- Test cross-service authentication

## Implementation Order

1. **Immediate**: Fix cookie configuration (enables cross-container auth)
2. **Next**: Implement webhooks (maintains data sync)
3. **Then**: Update frontend to use SDK
4. **Finally**: Remove custom middleware and endpoints

## Benefits

1. **Simplicity**: Remove thousands of lines of custom code
2. **Security**: Use battle-tested Kratos flows
3. **Maintainability**: Less custom code to maintain
4. **Standards**: Follow OAuth2/OIDC patterns
5. **Features**: Get MFA, account recovery, etc. for free