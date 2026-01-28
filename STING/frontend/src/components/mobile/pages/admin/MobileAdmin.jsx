import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import {
  TeamOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  SettingOutlined,
  ArrowRightOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useUnifiedAuth } from '../../../../auth/UnifiedAuthProvider';
import apiClient from '../../../../utils/apiClient';
import { resilientGet, fallbackGenerators } from '../../../../utils/resilientApiClient';
import MobileLoadingSpinner from '../../MobileLoadingSpinner';
import '../../../../styles/mobile.css';

/**
 * MobileAdmin - Mobile admin dashboard
 * Admin overview optimized for mobile
 */
const MobileAdmin = () => {
  const navigate = useNavigate();
  const { user } = useUnifiedAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalUsers: 0,
    pendingDocuments: 0,
    honeyJars: 0,
    totalDocuments: 0,
  });

  // Fetch admin dashboard stats
  const fetchDashboardStats = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch stats from multiple endpoints with fallbacks
      const [usersRes, pendingRes, honeyJarsRes] = await Promise.all([
        resilientGet('/api/admin/users/count', fallbackGenerators.profile(), { timeout: 5000 })
          .catch(() => ({ data: { count: 0 } })),
        resilientGet('/api/knowledge/pending-documents/count', { count: 0 }, { timeout: 5000 })
          .catch(() => ({ data: { count: 0 } })),
        apiClient.get('/api/knowledge/honey-jars').catch(() => ({ data: { items: [], total: 0 } })),
      ]);

      setStats({
        totalUsers: usersRes.data?.count || usersRes.data?.total || 0,
        pendingDocuments: pendingRes.data?.count || pendingRes.data?.total || 0,
        honeyJars: honeyJarsRes.data?.items?.length || honeyJarsRes.data?.total || 0,
        totalDocuments: honeyJarsRes.data?.items?.reduce((sum, jar) => sum + (jar.documentCount || 0), 0) || 0,
      });
    } catch (error) {
      console.error('Failed to fetch admin stats:', error);
      message.error('Failed to load admin dashboard');
      // Set fallback stats
      setStats({
        totalUsers: 0,
        pendingDocuments: 0,
        honeyJars: 0,
        totalDocuments: 0,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardStats();
  }, [fetchDashboardStats]);

  // Loading state
  if (loading) {
    return <MobileLoadingSpinner />;
  }

  return (
    <div className="mobile-page">
      {/* Header */}
      <div className="mobile-admin-header" style={{ marginBottom: 'var(--mobile-space-lg)' }}>
        <h1 className="mobile-page-title" style={{ marginBottom: 'var(--mobile-space-xs)' }}>
          Admin Control
        </h1>
        <p style={{ color: 'var(--mobile-text-secondary)', fontSize: 'var(--mobile-font-sm)' }}>
          Welcome back, {user?.name || user?.email || 'Admin'}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="mobile-section">
        <h2 className="mobile-section-title">Overview</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 'var(--mobile-space-sm)' }}>
          <div
            className="mobile-card mobile-stat-card"
            onClick={() => navigate('/m/admin/users')}
          >
            <TeamOutlined style={{ fontSize: 24, color: 'var(--mobile-primary)', marginBottom: 8 }} />
            <div style={{ fontSize: 'var(--mobile-font-2xl)', fontWeight: 600, color: 'var(--mobile-text-primary)' }}>
              {stats.totalUsers}
            </div>
            <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>Users</div>
          </div>

          <div
            className="mobile-card mobile-stat-card"
            onClick={() => navigate('/m/admin/pending')}
          >
            <FileTextOutlined style={{ fontSize: 24, color: 'var(--mobile-warning)', marginBottom: 8 }} />
            <div style={{ fontSize: 'var(--mobile-font-2xl)', fontWeight: 600, color: 'var(--mobile-text-primary)' }}>
              {stats.pendingDocuments}
            </div>
            <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>Pending</div>
          </div>

          <div
            className="mobile-card mobile-stat-card"
            onClick={() => navigate('/m/honey-jars')}
          >
            <DatabaseOutlined style={{ fontSize: 24, color: 'var(--mobile-success)', marginBottom: 8 }} />
            <div style={{ fontSize: 'var(--mobile-font-2xl)', fontWeight: 600, color: 'var(--mobile-text-primary)' }}>
              {stats.honeyJars}
            </div>
            <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>Honey Jars</div>
          </div>

          <div
            className="mobile-card mobile-stat-card"
            onClick={() => navigate('/m/honey-jars')}
          >
            <FileTextOutlined style={{ fontSize: 24, color: 'var(--mobile-info)', marginBottom: 8 }} />
            <div style={{ fontSize: 'var(--mobile-font-2xl)', fontWeight: 600, color: 'var(--mobile-text-primary)' }}>
              {stats.totalDocuments}
            </div>
            <div style={{ fontSize: 'var(--mobile-font-xs)', color: 'var(--mobile-text-tertiary)' }}>Documents</div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mobile-section">
        <h2 className="mobile-section-title">Quick Actions</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--mobile-space-sm)' }}>
          <div
            className="mobile-card mobile-admin-action-card"
            onClick={() => navigate('/m/admin/pending')}
            style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-md)' }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 'var(--mobile-radius-md, 8px)',
                background: 'rgba(234, 179, 8, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <FileTextOutlined style={{ fontSize: 20, color: 'var(--mobile-warning)' }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)', marginBottom: 2 }}>
                Pending Approvals
              </div>
              <div style={{ fontSize: 'var(--mobile-font-sm)', color: 'var(--mobile-text-secondary)' }}>
                {stats.pendingDocuments} documents waiting
              </div>
            </div>
            <ArrowRightOutlined style={{ color: 'var(--mobile-text-tertiary)' }} />
          </div>

          <div
            className="mobile-card mobile-admin-action-card"
            onClick={() => navigate('/m/admin/users')}
            style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-md)' }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 'var(--mobile-radius-md, 8px)',
                background: 'rgba(93, 155, 99, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <TeamOutlined style={{ fontSize: 20, color: 'var(--mobile-success)' }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)', marginBottom: 2 }}>
                User Management
              </div>
              <div style={{ fontSize: 'var(--mobile-font-sm)', color: 'var(--mobile-text-secondary)' }}>
                Manage users and roles
              </div>
            </div>
            <ArrowRightOutlined style={{ color: 'var(--mobile-text-tertiary)' }} />
          </div>

          <div
            className="mobile-card mobile-admin-action-card"
            onClick={() => navigate('/m/honey-jars')}
            style={{ display: 'flex', alignItems: 'center', gap: 'var(--mobile-space-md)' }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 'var(--mobile-radius-md, 8px)',
                background: 'rgba(6, 182, 212, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <DatabaseOutlined style={{ fontSize: 20, color: 'var(--mobile-info)' }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 500, color: 'var(--mobile-text-primary)', marginBottom: 2 }}>
                Honey Jars
              </div>
              <div style={{ fontSize: 'var(--mobile-font-sm)', color: 'var(--mobile-text-secondary)' }}>
                View all honey jars
              </div>
            </div>
            <ArrowRightOutlined style={{ color: 'var(--mobile-text-tertiary)' }} />
          </div>
        </div>
      </div>

      {/* Refresh Button */}
      <div style={{ marginTop: 'var(--mobile-space-lg)' }}>
        <button
          className="mobile-card"
          onClick={fetchDashboardStats}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--mobile-space-sm)',
            padding: 'var(--mobile-space-md)',
          }}
        >
          <ReloadOutlined style={{ color: 'var(--mobile-text-secondary)' }} />
          <span style={{ color: 'var(--mobile-text-secondary)' }}>Refresh Stats</span>
        </button>
      </div>
    </div>
  );
};

export default MobileAdmin;
