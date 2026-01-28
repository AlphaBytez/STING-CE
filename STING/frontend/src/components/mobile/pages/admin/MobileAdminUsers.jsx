import React, { useState, useEffect, useCallback } from 'react';
import { message, Modal, Tag } from 'antd';
import {
  TeamOutlined,
  UserOutlined,
  SearchOutlined,
  EditOutlined,
  StopOutlined,
  CheckOutlined,
  CloseOutlined,
  ReloadOutlined,
  CrownOutlined,
  UserSwitchOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useUnifiedAuth } from '../../../../auth/UnifiedAuthProvider';
import apiClient from '../../../../utils/apiClient';
import { resilientGet, resilientPut, resilientPost } from '../../../../utils/resilientApiClient';
import MobileLoadingSpinner from '../../MobileLoadingSpinner';
import '../../../../styles/mobile.css';

/**
 * MobileAdminUsers - Mobile user management page
 * User management optimized for mobile
 */
const MobileAdminUsers = () => {
  const { user: currentUser } = useUnifiedAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [users, setUsers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [newRole, setNewRole] = useState('');
  const [deactivateModalVisible, setDeactivateModalVisible] = useState(false);
  const [deactivatingUser, setDeactivatingUser] = useState(null);

  // Fetch users
  const fetchUsers = useCallback(async (showRefresh = false, searchPage = page) => {
    if (showRefresh) setRefreshing(true);
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: searchPage.toString(),
        limit: '10',
      });

      if (searchQuery) {
        params.append('search', searchQuery);
      }
      if (roleFilter !== 'all') {
        params.append('role', roleFilter);
      }

      const response = await resilientGet(
        `/api/admin/users?${params.toString()}`,
        {
          users: [
            {
              id: 'demo-1',
              email: 'admin@sting.local',
              name: 'Admin User',
              role: 'admin',
              status: 'active',
              createdAt: new Date().toISOString(),
              lastLogin: new Date().toISOString(),
            },
            {
              id: 'demo-2',
              email: 'demo@sting.local',
              name: 'Demo User',
              role: 'user',
              status: 'active',
              createdAt: new Date().toISOString(),
              lastLogin: new Date().toISOString(),
            },
          ],
          total: 2,
          page: 1,
          totalPages: 1,
        },
        { timeout: 5000 }
      );

      setUsers(response.users || response.data?.users || []);
      setTotalPages(response.totalPages || response.data?.totalPages || 1);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      message.error('Failed to load users');
      setUsers([]);
    } finally {
      setLoading(false);
      if (showRefresh) setRefreshing(false);
    }
  }, [page, searchQuery, roleFilter]);

  // Initial load
  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Handle search
  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  // Handle refresh
  const handleRefresh = () => {
    fetchUsers(true);
  };

  // Handle role change
  const showEditModal = (user) => {
    setEditingUser(user);
    setNewRole(user.role);
    setEditModalVisible(true);
  };

  const handleUpdateRole = async () => {
    if (!editingUser || !newRole) return;

    try {
      await resilientPut(`/api/admin/users/${editingUser.id}/role`, { role: newRole });
      message.success(`Role updated for ${editingUser.name || editingUser.email}`);
      setEditModalVisible(false);
      setEditingUser(null);
      setNewRole('');
      fetchUsers();
    } catch (error) {
      console.error('Failed to update role:', error);
      message.error('Failed to update role');
    }
  };

  // Handle deactivate/activate
  const showDeactivateModal = (user) => {
    setDeactivatingUser(user);
    setDeactivateModalVisible(true);
  };

  const handleToggleUserStatus = async () => {
    if (!deactivatingUser) return;

    const isDeactivating = deactivatingUser.status === 'active';
    const newStatus = isDeactivating ? 'deactivated' : 'active';

    try {
      await resilientPost(`/api/admin/users/${deactivatingUser.id}/status`, { status: newStatus });
      message.success(`User ${isDeactivating ? 'deactivated' : 'activated'} successfully`);
      setDeactivateModalVisible(false);
      setDeactivatingUser(null);
      fetchUsers();
    } catch (error) {
      console.error('Failed to toggle user status:', error);
      message.error('Failed to update user status');
    }
  };

  // Get role badge color
  const getRoleColor = (role) => {
    switch (role) {
      case 'admin':
      case 'super_admin':
        return { bg: 'rgba(234, 179, 8, 0.15)', color: 'var(--mobile-warning)' };
      case 'moderator':
        return { bg: 'rgba(93, 155, 99, 0.15)', color: 'var(--mobile-success)' };
      default:
        return { bg: 'rgba(148, 163, 184, 0.15)', color: 'var(--mobile-text-tertiary)' };
    }
  };

  // Get status badge color
  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'var(--mobile-success)';
      case 'deactivated':
        return 'var(--mobile-error)';
      case 'pending':
        return 'var(--mobile-warning)';
      default:
        return 'var(--mobile-text-tertiary)';
    }
  };

  // Format date
  const formatDate = (date) => {
    if (!date) return 'Never';
    return new Date(date).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Filtered users for display
  const filteredUsers = users;

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div className="mobile-page">
      {/* Header */}
      <div className="mobile-admin-header" style={{ marginBottom: 'var(--mobile-space-md)' }}>
        <h1 className="mobile-page-title" style={{ marginBottom: 'var(--mobile-space-xs)' }}>
          User Management
        </h1>
        <p style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
          Manage users and their roles
        </p>
      </div>

      {/* Search Bar */}
      <div className="mobile-section">
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 'var(--mobile-space-sm)', marginBottom: 'var(--mobile-space-sm)' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <SearchOutlined
              style={{
                position: 'absolute',
                left: 'var(--mobile-space-sm)',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--mobile-text-tertiary)',
              }}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search users..."
              style={{
                width: '100%',
                padding: 'var(--mobile-space-sm) var(--mobile-space-sm) var(--mobile-space-sm) 36px',
                background: 'var(--mobile-surface)',
                border: '1px solid var(--mobile-border)',
                borderRadius: 'var(--mobile-radius-md, 8px)',
                color: 'var(--mobile-text-primary)',
                fontSize: 'var(--mobile-font-md)',
                boxSizing: 'border-box',
              }}
            />
          </div>
          <button
            type="submit"
            style={{
              padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
              background: 'var(--mobile-primary)',
              border: 'none',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              color: '#fff',
              fontSize: 'var(--mobile-font-md)',
              cursor: 'pointer',
            }}
          >
            Search
          </button>
        </form>

        {/* Role Filter */}
        <div style={{ display: 'flex', gap: 'var(--mobile-space-xs)', overflowX: 'auto', paddingBottom: 'var(--mobile-space-xs)' }}>
          {['all', 'admin', 'user', 'moderator'].map((role) => (
            <button
              key={role}
              onClick={() => {
                setRoleFilter(role);
                setPage(1);
                fetchUsers();
              }}
              style={{
                padding: 'var(--mobile-space-xs) var(--mobile-space-md)',
                background: roleFilter === role ? 'var(--mobile-primary)' : 'var(--mobile-surface)',
                border: `1px solid ${roleFilter === role ? 'var(--mobile-primary)' : 'var(--mobile-border)'}`,
                borderRadius: 'var(--mobile-radius-lg, 20px)',
                color: roleFilter === role ? '#fff' : 'var(--mobile-text-secondary)',
                fontSize: 'var(--mobile-font-sm)',
                whiteSpace: 'nowrap',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {role === 'all' ? 'All Users' : role}
            </button>
          ))}
        </div>
      </div>

      {/* Users List Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--mobile-space-sm)' }}>
        <h2 className="mobile-section-title" style={{ marginBottom: 0 }}>
          Users ({filteredUsers.length})
        </h2>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--mobile-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--mobile-space-xs)',
          }}
        >
          <ReloadOutlined spin={refreshing} />
          Refresh
        </button>
      </div>

      {/* Users List */}
      {filteredUsers.length === 0 ? (
        <div className="mobile-empty-state">
          <TeamOutlined className="mobile-empty-state-icon" />
          <div className="mobile-empty-state-title">No Users Found</div>
          <div className="mobile-empty-state-description">
            {searchQuery ? 'Try adjusting your search criteria.' : 'No users match the current filter.'}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--mobile-space-sm)' }}>
          {filteredUsers.map((user) => {
            const roleColors = getRoleColor(user.role);
            return (
              <div
                key={user.id}
                className="mobile-card"
                style={{ display: 'flex', gap: 'var(--mobile-space-md)' }}
              >
                {/* Avatar */}
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: '50%',
                    background: 'var(--mobile-elevated)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <UserOutlined style={{ fontSize: 20, color: 'var(--mobile-text-secondary)' }} />
                </div>

                {/* User Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--mobile-space-xs)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-sm)' }}>
                      <span style={{ fontWeight: 500, color: 'var(--mobile-text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 150 }}>
                        {user.name || user.email?.split('@')[0] || 'Unknown User'}
                      </span>
                      {user.role === 'admin' && (
                        <CrownOutlined style={{ color: 'var(--mobile-warning)', fontSize: 14 }} />
                      )}
                    </div>
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: getStatusColor(user.status),
                        flexShrink: 0,
                      }}
                    />
                  </div>

                  <div style={{ fontSize: 'var(--mobile-font-sm)', color: 'var(--mobile-text-secondary)', marginBottom: 'var(--mobile-space-xs)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {user.email}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: 'var(--mobile-radius-sm, 4px)',
                        background: roleColors.bg,
                        color: roleColors.color,
                        fontSize: 'var(--mobile-font-xs)',
                        fontWeight: 500,
                        textTransform: 'capitalize',
                      }}
                    >
                      {user.role || 'user'}
                    </span>

                    <div style={{ display: 'flex', gap: 'var(--mobile-space-xs)' }}>
                      <button
                        onClick={() => showEditModal(user)}
                        disabled={user.id === currentUser?.id}
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: 'var(--mobile-radius-sm, 6px)',
                          background: 'rgba(6, 182, 212, 0.15)',
                          border: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: user.id === currentUser?.id ? 'not-allowed' : 'pointer',
                          opacity: user.id === currentUser?.id ? 0.5 : 1,
                        }}
                        title="Edit role"
                      >
                        <UserSwitchOutlined style={{ color: 'var(--mobile-info)', fontSize: 12 }} />
                      </button>
                      <button
                        onClick={() => showDeactivateModal(user)}
                        disabled={user.id === currentUser?.id}
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: 'var(--mobile-radius-sm, 6px)',
                          background: user.status === 'active' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(93, 155, 99, 0.15)',
                          border: 'none',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: user.id === currentUser?.id ? 'not-allowed' : 'pointer',
                          opacity: user.id === currentUser?.id ? 0.5 : 1,
                        }}
                        title={user.status === 'active' ? 'Deactivate' : 'Activate'}
                      >
                        {user.status === 'active' ? (
                          <StopOutlined style={{ color: 'var(--mobile-error)', fontSize: 12 }} />
                        ) : (
                          <CheckOutlined style={{ color: 'var(--mobile-success)', fontSize: 12 }} />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--mobile-space-sm)', marginTop: 'var(--mobile-space-lg)' }}>
          <button
            onClick={() => {
              setPage(p => Math.max(1, p - 1));
              fetchUsers(false, page - 1);
            }}
            disabled={page === 1}
            style={{
              padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
              background: page === 1 ? 'var(--mobile-surface)' : 'var(--mobile-primary)',
              border: '1px solid var(--mobile-border)',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              color: page === 1 ? 'var(--mobile-text-tertiary)' : '#fff',
              cursor: page === 1 ? 'not-allowed' : 'pointer',
            }}
          >
            Previous
          </button>
          <span style={{ display: 'flex', alignItems: 'center', color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
            {page} / {totalPages}
          </span>
          <button
            onClick={() => {
              setPage(p => Math.min(totalPages, p + 1));
              fetchUsers(false, page + 1);
            }}
            disabled={page === totalPages}
            style={{
              padding: 'var(--mobile-space-sm) var(--mobile-space-md)',
              background: page === totalPages ? 'var(--mobile-surface)' : 'var(--mobile-primary)',
              border: '1px solid var(--mobile-border)',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              color: page === totalPages ? 'var(--mobile-text-tertiary)' : '#fff',
              cursor: page === totalPages ? 'not-allowed' : 'pointer',
            }}
          >
            Next
          </button>
        </div>
      )}

      {/* Edit Role Modal */}
      <Modal
        title="Edit User Role"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingUser(null);
          setNewRole('');
        }}
        onOk={handleUpdateRole}
        okText="Save Changes"
        cancelText="Cancel"
      >
        {editingUser && (
          <div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--mobile-space-md)',
                padding: 'var(--mobile-space-md)',
                background: 'var(--mobile-surface)',
                borderRadius: 'var(--mobile-radius-md, 8px)',
                marginBottom: 'var(--mobile-space-md)',
              }}
            >
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  background: 'var(--mobile-elevated)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <UserOutlined style={{ color: 'var(--mobile-text-secondary)' }} />
              </div>
              <div>
                <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)' }}>
                  {editingUser.name || editingUser.email}
                </div>
                <div style={{ fontSize: 'var(--mobile-font-sm)', color: 'var(--mobile-text-secondary)' }}>
                  {editingUser.email}
                </div>
              </div>
            </div>

            <label
              style={{
                display: 'block',
                fontSize: 'var(--mobile-font-sm)',
                fontWeight: 500,
                color: 'var(--mobile-text-secondary)',
                marginBottom: 'var(--mobile-space-xs)',
              }}
            >
              Select Role
            </label>
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              style={{
                width: '100%',
                padding: 'var(--mobile-space-sm)',
                background: 'var(--mobile-surface)',
                border: '1px solid var(--mobile-border)',
                borderRadius: 'var(--mobile-radius-md, 8px)',
                color: 'var(--mobile-text-primary)',
                fontSize: 'var(--mobile-font-md)',
                cursor: 'pointer',
              }}
            >
              <option value="user">User</option>
              <option value="moderator">Moderator</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        )}
      </Modal>

      {/* Deactivate/Activate Modal */}
      <Modal
        title={deactivatingUser?.status === 'active' ? 'Deactivate User' : 'Activate User'}
        open={deactivateModalVisible}
        onCancel={() => {
          setDeactivateModalVisible(false);
          setDeactivatingUser(null);
        }}
        onOk={handleToggleUserStatus}
        okText={deactivatingUser?.status === 'active' ? 'Deactivate' : 'Activate'}
        okButtonProps={{ danger: deactivatingUser?.status === 'active' }}
        cancelText="Cancel"
      >
        {deactivatingUser && (
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 'var(--mobile-space-md)',
              padding: 'var(--mobile-space-md)',
              background: deactivatingUser.status === 'active' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(93, 155, 99, 0.1)',
              borderRadius: 'var(--mobile-radius-md, 8px)',
              border: `1px solid ${deactivatingUser.status === 'active' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(93, 155, 99, 0.3)'}`,
            }}
          >
            <ExclamationCircleOutlined
              style={{
                fontSize: 20,
                color: deactivatingUser.status === 'active' ? 'var(--mobile-error)' : 'var(--mobile-success)',
              }}
            />
            <div>
              <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)', marginBottom: 'var(--mobile-space-xs)' }}>
                {deactivatingUser.status === 'active' ? 'Deactivate User?' : 'Activate User?'}
              </div>
              <div style={{ fontSize: 'var(--mobile-font-sm)', color: 'var(--mobile-text-secondary)' }}>
                {deactivatingUser.status === 'active'
                  ? `Are you sure you want to deactivate ${deactivatingUser.name || deactivatingUser.email}? They will no longer be able to access the system.`
                  : `Are you sure you want to activate ${deactivatingUser.name || deactivatingUser.email}? They will regain access to the system.`}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default MobileAdminUsers;
