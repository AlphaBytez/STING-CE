import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  TrendingUp,
  Activity,
  FileText,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  Sparkles,
  Shield,
  BarChart3,
  Percent
} from 'lucide-react';
import { resilientGet, resilientPost } from '../../utils/resilientApiClient';

/**
 * QA Bee Quality Dashboard
 *
 * Admin dashboard for monitoring automated quality assurance for reports.
 * Shows pass rates, processing status, and allows reviewing flagged content.
 */
const QABeeReviewDashboard = () => {
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
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [selectedReview, setSelectedReview] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [showOnlyFailed, setShowOnlyFailed] = useState(false);

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
        resilientGet('/api/qe-bee/admin/history?limit=25', { reviews: [] })
      ]);

      setStats(statsData);
      setRecentReviews(historyData.reviews || []);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch quality dashboard data:', err);
      setError('Failed to load quality data. The service may be starting up.');
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
    if (showOnlyFailed && review.result_code?.startsWith('PASS')) return false;
    if (filterStatus !== 'all') {
      if (filterStatus === 'passed' && !review.result_code?.startsWith('PASS')) return false;
      if (filterStatus === 'failed' && review.result_code?.startsWith('PASS')) return false;
      if (filterStatus === 'pending' && review.status !== 'pending') return false;
    }
    return true;
  });

  // Get status badge color
  const getStatusBadge = (status, resultCode) => {
    if (status === 'pending') return { bg: 'bg-yellow-500/20', text: 'text-yellow-300', border: 'border-yellow-500/30' };
    if (status === 'reviewing') return { bg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/30' };
    if (resultCode?.startsWith('PASS')) return { bg: 'bg-green-500/20', text: 'text-green-300', border: 'border-green-500/30' };
    return { bg: 'bg-red-500/20', text: 'text-red-300', border: 'border-red-500/30' };
  };

  // Get friendly result description
  const getResultDescription = (code) => {
    const descriptions = {
      'PASS': 'Passed all quality checks',
      'PASS_WITH_WARNINGS': 'Passed with minor issues',
      'PII_TOKENS_REMAINING': 'Contains unresolved privacy tokens',
      'PII_DESERIALIZATION_INCOMPLETE': 'Privacy restoration incomplete',
      'OUTPUT_TRUNCATED': 'Content appears incomplete',
      'OUTPUT_EMPTY': 'No content generated',
      'OUTPUT_MALFORMED': 'Invalid format detected',
      'QUALITY_LOW': 'Below quality threshold',
      'CONTENT_INCOHERENT': 'Content quality issues'
    };
    return descriptions[code] || code;
  };

  // Format timestamp
  const formatTimestamp = (ts) => {
    if (!ts) return '-';
    const date = new Date(ts);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  // Calculate additional metrics
  const failedCount = stats.failed || 0;
  const warningsCount = stats.passed_with_warnings || 0;
  const activeCount = (stats.pending || 0) + (stats.reviewing || 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <div className="relative">
            <RefreshCw className="w-8 h-8 animate-spin text-cyan-400 mx-auto mb-4" />
            <Sparkles className="w-4 h-4 text-yellow-300 absolute -top-1 -right-1 animate-pulse" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Loading Quality Dashboard</h3>
          <p className="text-gray-400">Fetching review data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-green-500/20 p-2 rounded-xl">
            <Shield className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Quality Assurance</h2>
            <p className="text-gray-400 text-sm">Automated content review monitoring</p>
          </div>
        </div>
        <button
          onClick={() => fetchDashboardData(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600/50 text-gray-300 rounded-xl transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-yellow-500/20 border border-yellow-500/30 rounded-2xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
          <p className="text-yellow-300">{error}</p>
        </div>
      )}

      {/* Key Metrics - Simplified */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Pass Rate - Primary Metric */}
        <div className="bg-gradient-to-br from-green-500/20 to-emerald-500/10 backdrop-blur-sm rounded-2xl p-5 border border-green-500/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-4xl font-bold text-white">{stats.pass_rate?.toFixed(0) || 0}%</p>
              <p className="text-sm text-green-300 mt-1">Pass Rate</p>
            </div>
            <div className="bg-green-500/20 p-3 rounded-xl">
              <Percent className="w-6 h-6 text-green-400" />
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
            <TrendingUp className="w-3 h-3" />
            <span>{stats.passed + warningsCount} of {stats.total_reviews} passed</span>
          </div>
        </div>

        {/* Currently Active */}
        <div className="bg-slate-700/50 backdrop-blur-sm rounded-2xl p-5 border border-slate-600/50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-4xl font-bold text-white">{activeCount}</p>
              <p className="text-sm text-gray-400 mt-1">In Progress</p>
            </div>
            <div className="bg-blue-500/20 p-3 rounded-xl">
              <Activity className="w-6 h-6 text-blue-400" />
            </div>
          </div>
          {activeCount > 0 && (
            <div className="mt-3 flex items-center gap-2 text-xs text-blue-300">
              <Clock className="w-3 h-3" />
              <span>{stats.pending} queued • {stats.reviewing} reviewing</span>
            </div>
          )}
        </div>

        {/* Total Processed */}
        <div className="bg-slate-700/50 backdrop-blur-sm rounded-2xl p-5 border border-slate-600/50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-4xl font-bold text-white">{stats.total_reviews}</p>
              <p className="text-sm text-gray-400 mt-1">Total Reviewed</p>
            </div>
            <div className="bg-cyan-500/20 p-3 rounded-xl">
              <BarChart3 className="w-6 h-6 text-cyan-400" />
            </div>
          </div>
        </div>

        {/* Issues Found */}
        <div className={`backdrop-blur-sm rounded-2xl p-5 border ${
          failedCount > 0 
            ? 'bg-red-500/10 border-red-500/30' 
            : 'bg-slate-700/50 border-slate-600/50'
        }`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-4xl font-bold text-white">{failedCount}</p>
              <p className={`text-sm mt-1 ${failedCount > 0 ? 'text-red-300' : 'text-gray-400'}`}>
                Issues Found
              </p>
            </div>
            <div className={`p-3 rounded-xl ${failedCount > 0 ? 'bg-red-500/20' : 'bg-slate-600/50'}`}>
              <XCircle className={`w-6 h-6 ${failedCount > 0 ? 'text-red-400' : 'text-gray-500'}`} />
            </div>
          </div>
          {warningsCount > 0 && (
            <div className="mt-3 flex items-center gap-2 text-xs text-yellow-300">
              <AlertTriangle className="w-3 h-3" />
              <span>{warningsCount} passed with warnings</span>
            </div>
          )}
        </div>
      </div>

      {/* Recent Reviews Section */}
      <div className="bg-slate-800/30 rounded-2xl border border-slate-700/50 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-700/50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-white">Recent Reviews</h3>
            <span className="text-xs text-gray-500 bg-slate-700/50 px-2 py-1 rounded-full">
              Last 25
            </span>
          </div>
          
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={showOnlyFailed}
                onChange={(e) => setShowOnlyFailed(e.target.checked)}
                className="rounded border-slate-600 bg-slate-700 text-red-500 focus:ring-red-500"
              />
              Show only issues
            </label>
            
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-1.5 bg-slate-700/80 border border-slate-600/50 text-white rounded-lg text-sm focus:ring-2 focus:ring-cyan-400"
            >
              <option value="all">All Status</option>
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
            </select>
          </div>
        </div>

        {/* Reviews List */}
        <div className="divide-y divide-slate-700/30">
          {filteredReviews.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="w-12 h-12 text-green-500/50 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-white mb-1">
                {recentReviews.length === 0 ? 'No Reviews Yet' : 'All Clear!'}
              </h3>
              <p className="text-gray-400 text-sm">
                {recentReviews.length === 0
                  ? 'Quality reviews will appear here as reports are generated.'
                  : 'No reviews match your current filter.'}
              </p>
            </div>
          ) : (
            filteredReviews.map((review) => {
              const statusStyle = getStatusBadge(review.status, review.result_code);
              const isExpanded = selectedReview === review.id;
              const isPassed = review.result_code?.startsWith('PASS');
              const isWarning = review.result_code === 'PASS_WITH_WARNINGS';

              return (
                <div
                  key={review.id}
                  className={`transition-colors ${isExpanded ? 'bg-slate-700/30' : 'hover:bg-slate-700/20'}`}
                >
                  <div
                    className="px-5 py-3 cursor-pointer"
                    onClick={() => setSelectedReview(isExpanded ? null : review.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {/* Status Icon */}
                        <div className={`${statusStyle.bg} p-1.5 rounded-lg`}>
                          {review.status === 'pending' && <Clock className={`w-4 h-4 ${statusStyle.text}`} />}
                          {review.status === 'reviewing' && <Activity className={`w-4 h-4 ${statusStyle.text}`} />}
                          {isPassed && <CheckCircle className={`w-4 h-4 ${statusStyle.text}`} />}
                          {!isPassed && review.status !== 'pending' && review.status !== 'reviewing' && (
                            <XCircle className={`w-4 h-4 ${statusStyle.text}`} />
                          )}
                        </div>

                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`text-sm font-medium ${statusStyle.text}`}>
                              {isPassed ? (isWarning ? 'Passed with warnings' : 'Passed') : 
                               review.status === 'pending' ? 'Pending' :
                               review.status === 'reviewing' ? 'Reviewing' : 'Failed'}
                            </span>
                            <span className="text-xs text-gray-500">
                              {review.target_type || 'report'}
                            </span>
                          </div>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {formatTimestamp(review.created_at)}
                            {review.result_code && !isPassed && (
                              <span className="text-red-300/70 ml-2">
                                • {getResultDescription(review.result_code)}
                              </span>
                            )}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {review.confidence_score !== null && review.confidence_score !== undefined && (
                          <span className="text-xs text-gray-400 bg-slate-700/50 px-2 py-1 rounded">
                            {review.confidence_score}% confidence
                          </span>
                        )}

                        {!isPassed && review.status !== 'pending' && review.status !== 'reviewing' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRetryReview(review.id);
                            }}
                            className="p-1.5 bg-yellow-500/20 hover:bg-yellow-500/30 border border-yellow-500/30 rounded-lg text-yellow-300 transition-all"
                            title="Retry Review"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>
                        )}

                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4 text-gray-500" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-500" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="px-5 pb-4 pt-1 border-t border-slate-700/30">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                        <div className="bg-slate-800/50 rounded-lg p-2.5">
                          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Review ID</p>
                          <p className="text-white font-mono text-xs truncate mt-0.5" title={review.id}>
                            {review.id?.slice(0, 12)}...
                          </p>
                        </div>
                        <div className="bg-slate-800/50 rounded-lg p-2.5">
                          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Target ID</p>
                          <p className="text-white font-mono text-xs truncate mt-0.5" title={review.target_id}>
                            {review.target_id?.slice(0, 12) || '-'}...
                          </p>
                        </div>
                        <div className="bg-slate-800/50 rounded-lg p-2.5">
                          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Type</p>
                          <p className="text-white text-xs mt-0.5">{review.review_type || '-'}</p>
                        </div>
                        <div className="bg-slate-800/50 rounded-lg p-2.5">
                          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Result Code</p>
                          <p className={`text-xs mt-0.5 font-mono ${isPassed ? 'text-green-300' : 'text-red-300'}`}>
                            {review.result_code || '-'}
                          </p>
                        </div>
                      </div>

                      {review.result_message && (
                        <div className="mt-3 bg-slate-800/50 rounded-lg p-3">
                          <p className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Message</p>
                          <p className="text-white text-sm">{review.result_message}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Info Footer */}
      <div className="bg-slate-700/30 border border-slate-600/30 rounded-xl p-4 flex items-start gap-3">
        <Shield className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-gray-300 font-medium text-sm">About Quality Assurance</p>
          <p className="text-gray-500 text-sm mt-1">
            All AI-generated content is automatically reviewed before delivery. Checks include 
            privacy token validation, content completeness, format verification, and quality assessment.
            Failed reviews are logged here for admin review.
          </p>
        </div>
      </div>
    </div>
  );
};

export default QABeeReviewDashboard;
