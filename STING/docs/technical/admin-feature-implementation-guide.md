# Admin Panel Feature Implementation Guide

## 🎯 Quick Implementation Guide for Placeholder Features

This guide provides step-by-step instructions for implementing the placeholder/dummy features in the STING Admin Panel.

## 1. User Management Tab Implementation

### Frontend Implementation

**File**: `/frontend/src/components/admin/AdminPanel.jsx`

**Replace this placeholder (lines 318-326)**:
```jsx
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

**With this implementation**:
```jsx
{activeTab === 'users' && (
  <UserManagementTab />
)}
```

**Create new component**: `/frontend/src/components/admin/UserManagementTab.jsx`
```jsx
import React, { useState, useEffect } from 'react';
import { Users, UserPlus, Shield, Search, Settings, Trash2 } from 'lucide-react';

const UserManagementTab = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 20,
    total: 0,
    pages: 0
  });

  const loadUsers = async (page = 1, search = '') => {
    try {
      setLoading(true);
      const response = await fetch(`/api/users?page=${page}&per_page=20&search=${search}`, {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users);
        setPagination(data.pagination);
      }
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handlePromoteUser = async (userId, role) => {
    try {
      const response = await fetch(`/api/users/${userId}/promote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ role })
      });
      
      if (response.ok) {
        loadUsers(pagination.page, searchTerm);
        alert(`User promoted to ${role} successfully`);
      }
    } catch (error) {
      console.error('Failed to promote user:', error);
    }
  };

  return (
    <div>
      {/* Search and Controls */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex-1 relative max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              loadUsers(1, e.target.value);
            }}
            className="w-full pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400"
          />
        </div>
        <button className="ml-4 px-4 py-2 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded-lg transition-colors flex items-center space-x-2">
          <UserPlus className="w-4 h-4" />
          <span>Add User</span>
        </button>
      </div>

      {/* User Statistics */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="standard-card p-4">
          <div className="flex items-center space-x-3">
            <Users className="w-5 h-5 text-blue-400" />
            <div>
              <div className="text-xl font-bold text-white">{pagination.total}</div>
              <div className="text-gray-400 text-sm">Total Users</div>
            </div>
          </div>
        </div>
        <div className="standard-card p-4">
          <div className="flex items-center space-x-3">
            <Shield className="w-5 h-5 text-yellow-400" />
            <div>
              <div className="text-xl font-bold text-white">
                {users.filter(u => u.is_admin).length}
              </div>
              <div className="text-gray-400 text-sm">Admin Users</div>
            </div>
          </div>
        </div>
        <div className="standard-card p-4">
          <div className="flex items-center space-x-3">
            <Settings className="w-5 h-5 text-green-400" />
            <div>
              <div className="text-xl font-bold text-white">
                {users.filter(u => u.is_active).length}
              </div>
              <div className="text-gray-400 text-sm">Active Users</div>
            </div>
          </div>
        </div>
      </div>

      {/* User List */}
      <div className="standard-card rounded-2xl">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Users</h3>
          
          {loading ? (
            <div className="text-center py-8 text-gray-400">Loading users...</div>
          ) : users.length === 0 ? (
            <div className="text-center py-8 text-gray-400">No users found</div>
          ) : (
            <div className="space-y-3">
              {users.map(user => (
                <div key={user.id} className="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg">
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center">
                      <Users className="w-5 h-5 text-gray-300" />
                    </div>
                    <div>
                      <div className="text-white font-medium">{user.display_name || `${user.first_name} ${user.last_name}`}</div>
                      <div className="text-gray-400 text-sm">{user.email}</div>
                      <div className="flex items-center space-x-2 mt-1">
                        {user.is_super_admin && (
                          <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded">Super Admin</span>
                        )}
                        {user.is_admin && !user.is_super_admin && (
                          <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded">Admin</span>
                        )}
                        {!user.is_admin && (
                          <span className="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded">User</span>
                        )}
                        {!user.is_active && (
                          <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded">Inactive</span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {!user.is_admin && (
                      <button
                        onClick={() => handlePromoteUser(user.id, 'admin')}
                        className="px-3 py-1 bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30 rounded text-sm transition-colors"
                      >
                        Promote to Admin
                      </button>
                    )}
                    <button className="p-2 text-gray-400 hover:text-white transition-colors">
                      <Settings className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {/* Pagination */}
          {pagination.pages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-700">
              <div className="text-gray-400 text-sm">
                Page {pagination.page} of {pagination.pages} ({pagination.total} total)
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => loadUsers(pagination.page - 1, searchTerm)}
                  disabled={!pagination.has_prev}
                  className="px-3 py-1 bg-gray-700 text-gray-300 rounded disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => loadUsers(pagination.page + 1, searchTerm)}
                  disabled={!pagination.has_next}
                  className="px-3 py-1 bg-gray-700 text-gray-300 rounded disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserManagementTab;
```

## 2. Custom PII Rules Editor Implementation

**File**: `/frontend/src/components/admin/PIIConfigurationManager.jsx`

**Replace this placeholder (lines 630-641)**:
```jsx
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

**With this implementation**:
```jsx
{activeTab === 'custom' && (
  <CustomRulesTab 
    onRuleCreated={() => loadPIIConfiguration()}
    onTestPattern={(pattern) => openPatternTester(pattern)}
  />
)}
```

**Create new component**: `/frontend/src/components/admin/CustomRulesTab.jsx`
```jsx
import React, { useState, useEffect } from 'react';
import { Plus, Edit, Test, Save, Trash2, Copy } from 'lucide-react';

const CustomRulesTab = ({ onRuleCreated, onTestPattern }) => {
  const [customRules, setCustomRules] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    pattern: '',
    description: '',
    category: 'custom',
    risk_level: 'medium',
    compliance_frameworks: []
  });

  const handleCreateRule = async () => {
    try {
      const response = await fetch('/api/pii/patterns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ ...newRule, custom: true })
      });
      
      if (response.ok) {
        setShowCreateForm(false);
        setNewRule({
          name: '',
          pattern: '',
          description: '',
          category: 'custom',
          risk_level: 'medium',
          compliance_frameworks: []
        });
        onRuleCreated();
        alert('Custom rule created successfully!');
      }
    } catch (error) {
      console.error('Failed to create custom rule:', error);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">Custom PII Rules</h2>
          <p className="text-gray-400">Create organization-specific PII detection patterns</p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="px-4 py-2 bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 rounded-lg transition-colors flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>Create Custom Rule</span>
        </button>
      </div>

      {/* Create Form Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <h3 className="text-xl font-bold text-white mb-4">Create Custom PII Rule</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-gray-300 text-sm font-medium mb-2">Rule Name</label>
                <input
                  type="text"
                  value={newRule.name}
                  onChange={(e) => setNewRule({...newRule, name: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                  placeholder="e.g., Custom ID Pattern"
                />
              </div>
              
              <div>
                <label className="block text-gray-300 text-sm font-medium mb-2">Regular Expression Pattern</label>
                <textarea
                  value={newRule.pattern}
                  onChange={(e) => setNewRule({...newRule, pattern: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white font-mono"
                  rows="3"
                  placeholder="e.g., \\b[A-Z]{2}\\d{6}\\b"
                />
              </div>
              
              <div>
                <label className="block text-gray-300 text-sm font-medium mb-2">Description</label>
                <input
                  type="text"
                  value={newRule.description}
                  onChange={(e) => setNewRule({...newRule, description: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                  placeholder="Describe what this pattern detects"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">Category</label>
                  <select
                    value={newRule.category}
                    onChange={(e) => setNewRule({...newRule, category: e.target.value})}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                  >
                    <option value="custom">Custom</option>
                    <option value="personal">Personal</option>
                    <option value="medical">Medical</option>
                    <option value="legal">Legal</option>
                    <option value="financial">Financial</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">Risk Level</label>
                  <select
                    value={newRule.risk_level}
                    onChange={(e) => setNewRule({...newRule, risk_level: e.target.value})}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>
            </div>
            
            <div className="flex items-center justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 bg-gray-600 text-gray-300 rounded hover:bg-gray-500 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => onTestPattern(newRule)}
                className="px-4 py-2 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded transition-colors"
              >
                Test Pattern
              </button>
              <button
                onClick={handleCreateRule}
                disabled={!newRule.name || !newRule.pattern}
                className="px-4 py-2 bg-amber-500 text-black rounded hover:bg-amber-600 transition-colors disabled:opacity-50"
              >
                Create Rule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Custom Rules List */}
      <div className="space-y-4">
        {customRules.length === 0 ? (
          <div className="text-center py-12 standard-card rounded-2xl">
            <Edit className="w-16 h-16 text-gray-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300 mb-2">No Custom Rules</h3>
            <p className="text-gray-500">Create your first custom PII detection rule to get started.</p>
          </div>
        ) : (
          customRules.map(rule => (
            <div key={rule.id} className="dashboard-card p-4">
              {/* Rule display similar to PatternCard component */}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default CustomRulesTab;
```

## 3. PII Detection Analytics Implementation

**Replace this placeholder**:
```jsx
{activeTab === 'analytics' && (
  <div className="text-center py-12">
    <RefreshCw className="w-8 h-8 text-gray-400 mx-auto mb-4" />
    <h3 className="text-lg font-semibold text-white mb-2">Detection Analytics</h3>
    <p className="text-gray-400 mb-4">View PII detection statistics and trends</p>
    <button className="px-6 py-2 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded-lg transition-colors">
      View Analytics
    </button>
  </div>
)}
```

**With**:
```jsx
{activeTab === 'analytics' && (
  <PIIAnalyticsDashboard patterns={patterns} />
)}
```

## 4. Backend Implementation Requirements

### Complete PII Pattern Persistence

**File**: `/app/routes/pii_routes.py`

**Replace TODO at line 282**:
```python
# TODO: Save to database or configuration storage
```

**With**:
```python
# Save pattern to database
try:
    new_pattern = PIIPattern(
        name=pattern_data['name'],
        pattern=pattern_data['pattern'], 
        description=pattern_data['description'],
        category=pattern_data['category'],
        risk_level=pattern_data['risk_level'],
        compliance_frameworks=pattern_data['compliance_frameworks'],
        enabled=pattern_data.get('enabled', True),
        custom=pattern_data.get('custom', False),
        created_by=current_user.id if current_user else None
    )
    db.session.add(new_pattern)
    db.session.commit()
    logger.info(f"Saved PII pattern: {new_pattern.name}")
except Exception as e:
    db.session.rollback()
    logger.error(f"Failed to save PII pattern: {e}")
    raise
```

### Create PIIPattern Model

**File**: `/app/models/pii_models.py` (new file)
```python
from app.extensions import db
from datetime import datetime

class PIIPattern(db.Model):
    __tablename__ = 'pii_patterns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    pattern = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)
    compliance_frameworks = db.Column(db.JSON)
    enabled = db.Column(db.Boolean, default=True)
    custom = db.Column(db.Boolean, default=False)
    detection_count = db.Column(db.Integer, default=0)
    last_detected = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'pattern': self.pattern,
            'description': self.description,
            'category': self.category,
            'risk_level': self.risk_level,
            'compliance_frameworks': self.compliance_frameworks or [],
            'enabled': self.enabled,
            'custom': self.custom,
            'detection_count': self.detection_count,
            'last_detected': self.last_detected.isoformat() if self.last_detected else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
```

## 5. Database Migration

**Create migration file**: `/migrations/add_pii_patterns_table.sql`
```sql
-- Create PII patterns table
CREATE TABLE IF NOT EXISTS pii_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    pattern TEXT NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    compliance_frameworks JSON,
    enabled BOOLEAN DEFAULT TRUE,
    custom BOOLEAN DEFAULT FALSE,
    detection_count INTEGER DEFAULT 0,
    last_detected DATETIME,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Create index for faster queries
CREATE INDEX idx_pii_patterns_category ON pii_patterns(category);
CREATE INDEX idx_pii_patterns_enabled ON pii_patterns(enabled);
CREATE INDEX idx_pii_patterns_custom ON pii_patterns(custom);
```

## 6. Email Service Integration

**File**: `/app/services/email_service.py` (new file)
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_notification(to_email, subject, body, is_html=False):
        try:
            smtp_server = current_app.config.get('SMTP_SERVER')
            smtp_port = current_app.config.get('SMTP_PORT', 587)
            smtp_user = current_app.config.get('SMTP_USER')
            smtp_pass = current_app.config.get('SMTP_PASS')
            
            if not all([smtp_server, smtp_user, smtp_pass]):
                logger.warning("SMTP not configured, skipping email notification")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
```

## 7. Testing and Validation

### Frontend Tests
1. Test user management CRUD operations
2. Validate custom rule creation form
3. Test analytics dashboard data visualization
4. Verify proper error handling and loading states

### Backend Tests
1. Test PII pattern persistence
2. Validate email service integration
3. Test authentication middleware
4. Verify database migrations

### Integration Tests
1. End-to-end user management workflow
2. Custom PII rule creation and testing
3. Analytics data aggregation and display
4. Email notification delivery

---

**Implementation Priority**: 
1. User Management Tab (High)
2. Backend TODOs (High) 
3. Custom PII Rules (Medium)
4. Analytics Dashboard (Medium)
5. Email Integration (Low)