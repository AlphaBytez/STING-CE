import React, { useState, useEffect, useCallback } from 'react';
import {
  Eye,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
  TrendingUp,
  Activity,
  FileText,
  MessageSquare,
  Zap,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  Sparkles,
  Shield,
  BarChart3
} from 'lucide-react';
import { resilientGet, resilientPost } from '../../utils/resilientApiClient';

/**
 * QE Bee Review Dashboard
 *
 * Admin dashboard for monitoring and managing QE Bee automated quality reviews.
 * Displays review queue status, statistics, and allows manual review management.
 */
const QEBeeReviewDashboard = () => {
  // State
  const [stats, setStats] = useState({
    total_reviews: 0,
    passed: 0,
    passed_with_warnings: 0,
    failed: 0,
    pending: 0,
    reviewing: 0,
    pass_rate: 0
  });
  const [recentReviews, setRecentReviews] = useState([]);
  const [failureBreakdown, setFailureBreakdown] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [selectedReview, setSelectedReview] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterTargetType, setFilterTargetType] = useState('all');

  // Fetch dashboard data
  const fetchDashboardData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      // Fetch stats and history in parallel
      const [statsData, historyData] = await Promise.all([
        resilientGet('/api/qe-bee/admin/stats', {
          total_reviews: 0, passed: 0, failed: 0, pending: 0, reviewing: 0, pass_rate: 0
        }),
        resilientGet('/api/qe-bee/admin/history?limit=50', { reviews: [] })
      ]);

      setStats(statsData);
      setRecentReviews(historyData.reviews || []);

      // Calculate failure breakdown from recent reviews
      const failures = (historyData.reviews || []).filter(r =>
        r.result_code && !r.result_code.startsWith('PASS')
      );
      const breakdown = failures.reduce((acc, r) => {
        acc[r.result_code] = (acc[r.result_code] || 0) + 1;
        return acc;
      }, {});
      setFailureBreakdown(breakdown);

      setError(null);
    } catch (err) {
      console.error('Failed to fetch QE Bee dashboard data:', err);
      setError('Failed to load QE Bee data. Please check if the service is running.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchDashboardData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => fetchDashboardData(true), 30000);
    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  // Retry failed review
  const handleRetryReview = async (reviewId) => {
    try {
      await resilientPost(`/api/qe-bee/admin/reviews/${reviewId}/retry`, {}, { critical: true });
      fetchDashboardData(true);
    } catch (err) {
      console.error('Failed to retry review:', err);
      alert('Failed to retry review. Please try again.');
    }
  };

  // Filter reviews
  const filteredReviews = recentReviews.filter(review => {
    if (filterStatus !== 'all') {
      if (filterStatus === 'passed' && !review.result_code?.startsWith('PASS')) return false;
      if (filterStatus === 'failed' && review.result_code?.startsWith('PASS')) return false;
      if (filterStatus === 'pending' && review.status !== 'pending') return false;
    }
    if (filterTargetType !== 'all' && review.target_type !== filterTargetType) return false;
    return true;
  });

  // Get status badge color
  const getStatusBadge = (status, resultCode) => {
    if (status === 'pending') return { bg: 'bg-yellow-500/20', text: 'text-yellow-300', border: 'border-yellow-500/30' };
    if (status === 'reviewing') return { bg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/30' };
    if (resultCode?.startsWith('PASS')) return { bg: 'bg-green-500/20', text: 'text-green-300', border: 'border-green-500/30' };
    return { bg: 'bg-red-500/20', text: 'text-red-300', border: 'border-red-500/30' };
  };

  // Get result code description
  const getResultCodeDescription = (code) => {
    const descriptions = {
      'PASS': 'All checks passed successfully',
      'PASS_WITH_WARNINGS': 'Passed with minor issues noted',
      'PII_TOKENS_REMAINING': 'Unresolved [PII_*] tokens detected',
      'PII_DESERIALIZATION_INCOMPLETE': 'PII restore failed',
      'OUTPUT_TRUNCATED': 'Content appears cut off',
      'OUTPUT_EMPTY': 'Content is empty or too short',
      'OUTPUT_MALFORMED': 'Invalid structure detected',
      'QUALITY_LOW': 'LLM quality score below threshold',
      'CONTENT_INCOHERENT': 'Content lacks coherence'
    };
    return descriptions[code] || code;
  };

  // Format timestamp
  const formatTimestamp = (ts) => {
    if (!ts) return 'N/A';
    return new Date(ts).toLocaleString();
  };

  // Format target type icon
  const getTargetTypeIcon = (type) => {
    switch (type) {
      case 'report': return <FileText className="w-4 h-4" />;
      case 'message': return <MessageSquare className="w-4 h-4" />;
      case 'document': return <FileText className="w-4 h-4" />;
      default: return <Zap className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="relative">
            <RefreshCw className="w-8 h-8 animate-spin text-cyan-400 mx-auto mb-4" />
            <Sparkles className="w-4 h-4 text-yellow-300 absolute -top-1 -right-1 animate-pulse" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Loading QE Bee Dashboard</h3>
          <p className="text-gray-400">Fetching review queue data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-cyan-500/20 p-2 rounded-xl">
            <Eye className="w-6 h-6 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">QE Bee Review Dashboard</h2>
            <p className="text-gray-400 text-sm">Automated quality assurance monitoring</p>
          </div>
        </div>
        <button
          onClick={() => fetchDashboardData(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-300 rounded-xl transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-500/20 border border-red-500/30 rounded-2xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <p className="text-red-300">{error}</p>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-slate-700/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-3">
            <div className="bg-cyan-500/20 p-2 rounded-xl">
              <BarChart3 className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total_reviews}</p>
              <p className="text-xs text-gray-400">Total Reviews</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-700/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-3">
            <div className="bg-yellow-500/20 p-2 rounded-xl">
              <Clock className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.pending}</p>
              <p className="text-xs text-gray-400">Pending</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-700/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-3">
            <div className="bg-blue-500/20 p-2 rounded-xl">
              <Activity className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.reviewing}</p>
              <p className="text-xs text-gray-400">Reviewing</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-700/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-3">
            <div className="bg-green-500/20 p-2 rounded-xl">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.passed}</p>
              <p className="text-xs text-gray-400">Passed</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-700/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-3">
            <div className="bg-red-500/20 p-2 rounded-xl">
              <XCircle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.failed}</p>
              <p className="text-xs text-gray-400">Failed</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-700/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-600/50">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500/20 p-2 rounded-xl">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.pass_rate?.toFixed(1) || 0}%</p>
              <p className="text-xs text-gray-400">Pass Rate</p>
            </div>
          </div>
        </div>
      </div>

      {/* Failure Breakdown */}
      {Object.keys(failureBreakdown).length > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-red-300 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Failure Breakdown
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(failureBreakdown).map(([code, count]) => (
              <div key={code} className="bg-red-500/10 rounded-xl p-3 border border-red-500/20">
                <p className="text-red-300 font-mono text-sm">{code}</p>
                <p className="text-white font-bold text-lg">{count}</p>
                <p className="text-red-200/60 text-xs truncate" title={getResultCodeDescription(code)}>
                  {getResultCodeDescription(code)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-gray-400 text-sm">Filters:</span>
        </div>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 bg-slate-700/80 border border-slate-600/50 text-white rounded-xl text-sm focus:ring-2 focus:ring-cyan-400"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="passed">Passed</option>
          <option value="failed">Failed</option>
        </select>

        <select
          value={filterTargetType}
          onChange={(e) => setFilterTargetType(e.target.value)}
          className="px-3 py-2 bg-slate-700/80 border border-slate-600/50 text-white rounded-xl text-sm focus:ring-2 focus:ring-cyan-400"
        >
          <option value="all">All Types</option>
          <option value="report">Reports</option>
          <option value="message">Messages</option>
          <option value="document">Documents</option>
        </select>

        <span className="text-gray-400 text-sm ml-auto">
          Showing {filteredReviews.length} of {recentReviews.length} reviews
        </span>
      </div>

      {/* Reviews List */}
      <div className="space-y-3">
        {filteredReviews.length === 0 ? (
          <div className="text-center py-12 bg-slate-700/30 rounded-2xl border border-slate-600/30">
            <Eye className="w-16 h-16 text-slate-500 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Reviews Found</h3>
            <p className="text-gray-400">
              {recentReviews.length === 0
                ? 'QE Bee has not processed any reviews yet. Reviews will appear here as content is generated.'
                : 'No reviews match your current filters.'}
            </p>
          </div>
        ) : (
          filteredReviews.map((review) => {
            const statusStyle = getStatusBadge(review.status, review.result_code);
            const isExpanded = selectedReview === review.id;

            return (
              <div
                key={review.id}
                className={`bg-slate-700/30 backdrop-blur-sm rounded-2xl border transition-all duration-200 ${
                  isExpanded ? 'border-cyan-500/50' : 'border-slate-600/50 hover:border-slate-500/50'
                }`}
              >
                <div
                  className="p-4 cursor-pointer"
                  onClick={() => setSelectedReview(isExpanded ? null : review.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`${statusStyle.bg} p-2 rounded-xl`}>
                        {review.status === 'pending' && <Clock className={`w-5 h-5 ${statusStyle.text}`} />}
                        {review.status === 'reviewing' && <Activity className={`w-5 h-5 ${statusStyle.text}`} />}
                        {review.status === 'passed' && <CheckCircle className={`w-5 h-5 ${statusStyle.text}`} />}
                        {review.status === 'failed' && <XCircle className={`w-5 h-5 ${statusStyle.text}`} />}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-gray-500">{review.id?.slice(0, 8)}...</span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusStyle.bg} ${statusStyle.text} border ${statusStyle.border}`}>
                            {review.result_code || review.status?.toUpperCase()}
                          </span>
                          <span className="flex items-center gap-1 px-2 py-0.5 bg-slate-600/50 rounded-full text-xs text-gray-300">
                            {getTargetTypeIcon(review.target_type)}
                            {review.target_type}
                          </span>
                        </div>
                        <p className="text-gray-400 text-sm mt-1">
                          {review.review_type} • {formatTimestamp(review.created_at)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {review.confidence_score !== null && (
                        <div className="text-right">
                          <p className="text-white font-bold">{review.confidence_score}%</p>
                          <p className="text-xs text-gray-400">Confidence</p>
                        </div>
                      )}

                      {review.status === 'failed' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRetryReview(review.id);
                          }}
                          className="p-2 bg-yellow-500/20 hover:bg-yellow-500/30 border border-yellow-500/30 rounded-xl text-yellow-300 transition-all"
                          title="Retry Review"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </button>
                      )}

                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-0 border-t border-slate-600/50 mt-2">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
                      <div className="bg-slate-800/50 rounded-xl p-3">
                        <p className="text-xs text-gray-400 mb-1">Target ID</p>
                        <p className="text-white font-mono text-sm truncate" title={review.target_id}>
                          {review.target_id || 'N/A'}
                        </p>
                      </div>
                      <div className="bg-slate-800/50 rounded-xl p-3">
                        <p className="text-xs text-gray-400 mb-1">Review Type</p>
                        <p className="text-white text-sm">{review.review_type || 'N/A'}</p>
                      </div>
                      <div className="bg-slate-800/50 rounded-xl p-3">
                        <p className="text-xs text-gray-400 mb-1">Priority</p>
                        <p className="text-white text-sm">{review.priority || 5}</p>
                      </div>
                      <div className="bg-slate-800/50 rounded-xl p-3">
                        <p className="text-xs text-gray-400 mb-1">Completed</p>
                        <p className="text-white text-sm">{formatTimestamp(review.completed_at)}</p>
                      </div>
                    </div>

                    {review.result_message && (
                      <div className="mt-4 bg-slate-800/50 rounded-xl p-4">
                        <p className="text-xs text-gray-400 mb-2">Result Message</p>
                        <p className="text-white text-sm">{review.result_message}</p>
                      </div>
                    )}

                    {review.review_details && Object.keys(review.review_details).length > 0 && (
                      <div className="mt-4 bg-slate-800/50 rounded-xl p-4">
                        <p className="text-xs text-gray-400 mb-2">Review Details</p>
                        <pre className="text-white text-xs font-mono overflow-x-auto">
                          {JSON.stringify(review.review_details, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Info Footer */}
      <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-2xl p-4 flex items-start gap-3">
        <Shield className="w-5 h-5 text-cyan-400 mt-0.5" />
        <div>
          <p className="text-cyan-300 font-medium">About QE Bee</p>
          <p className="text-cyan-200/70 text-sm">
            QE Bee automatically reviews AI-generated content before delivery. It checks for PII tokens,
            output completeness, format validation, and optional LLM-powered quality assessment.
            Failed reviews prevent potentially problematic content from reaching users.
          </p>
        </div>
      </div>
    </div>
  );
};

export default QEBeeReviewDashboard;
