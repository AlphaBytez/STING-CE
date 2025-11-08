import apiClient from '../utils/apiClient';

// Report API endpoints
const REPORT_BASE_URL = '/api/reports';

class ReportApiService {
    // Get available report templates (requires authentication)
    async getTemplates(category = null) {
        try {
            const params = category ? { category } : {};
            const response = await apiClient.get(`${REPORT_BASE_URL}/templates`, {
                params,
                timeout: 5000  // 5 second timeout
            });

            // If authenticated but no templates in database, add demo templates
            if (response.data?.success && response.data?.data?.templates?.length === 0) {
                console.log('No templates in database, adding demo templates for authenticated user');
                response.data.data.templates = this.getDemoTemplates();
            }

            return response.data;
        } catch (error) {
            console.error('Failed to fetch templates:', error.response?.status, error.message);
            // Return error state for unauthorized users
            if (error.response?.status === 401 || error.response?.status === 403) {
                return {
                    success: false,
                    error: 'Authentication required',
                    data: {
                        templates: []
                    }
                };
            }
            throw error;
        }
    }

    // Create a new report
    async createReport(reportData) {
        try {
            const response = await apiClient.post(`${REPORT_BASE_URL}/`, reportData);
            return response.data;
        } catch (error) {
            console.error('Error creating report:', error);
            throw error;
        }
    }

    // List user's reports (requires authentication)
    async listReports(params = {}) {
        try {
            const { limit = 50, offset = 0, status, search } = params;
            const queryParams = { limit, offset };
            if (status) queryParams.status = status;
            if (search) queryParams.search = search;

            const response = await apiClient.get(`${REPORT_BASE_URL}/`, {
                params: queryParams,
                timeout: 15000
            });

            // If authenticated but no reports in database, add demo reports
            if (response.data?.success && response.data?.data?.reports?.length === 0) {
                console.log('No reports in database, adding demo reports for authenticated user');
                response.data.data.reports = this.getDemoReports();
                response.data.data.pagination = { total: response.data.data.reports.length };
            }

            return response.data;
        } catch (error) {
            console.error('Failed to fetch reports:', error.response?.status, error.message);
            // Return error state for unauthorized users
            if (error.response?.status === 401 || error.response?.status === 403) {
                return {
                    success: false,
                    error: 'Authentication required',
                    data: {
                        reports: [],
                        pagination: { total: 0 }
                    }
                };
            }
            throw error;
        }
    }

    // Get specific report details
    async getReport(reportId) {
        try {
            const response = await apiClient.get(`${REPORT_BASE_URL}/${reportId}`);
            return response.data;
        } catch (error) {
            console.error('Error fetching report:', error);
            throw error;
        }
    }

    // Get detailed report information (alias for consistency)
    async getReportDetails(reportId) {
        return this.getReport(reportId);
    }

    // Download report file
    async downloadReport(reportId) {
        try {
            const response = await apiClient.get(`${REPORT_BASE_URL}/${reportId}/download`, {
                responseType: 'blob'
            });
            
            // Extract filename from Content-Disposition header if available
            const contentDisposition = response.headers['content-disposition'];
            let filename = `report_${reportId}.pdf`;
            
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }
            
            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            
            return { success: true, filename };
        } catch (error) {
            console.error('Error downloading report:', error);
            throw error;
        }
    }

    // Cancel a pending/processing report
    async cancelReport(reportId) {
        try {
            const response = await apiClient.post(`${REPORT_BASE_URL}/${reportId}/cancel`);
            return response.data;
        } catch (error) {
            console.error('Error cancelling report:', error);
            throw error;
        }
    }

    // Retry a failed report
    async retryReport(reportId) {
        try {
            const response = await apiClient.post(`${REPORT_BASE_URL}/${reportId}/retry`);
            return response.data;
        } catch (error) {
            console.error('Error retrying report:', error);
            throw error;
        }
    }

    // Get queue status (requires authentication)
    async getQueueStatus(queue = 'default') {
        try {
            const response = await apiClient.get(`${REPORT_BASE_URL}/queue/status`, {
                params: { queue }
            });

            // If authenticated but no queue data, add demo queue status
            if (response.data?.success && !response.data?.data?.queue_name) {
                console.log('No queue data, adding demo queue status for authenticated user');
                response.data.data = this.getDemoQueueStatus();
            }

            return response.data;
        } catch (error) {
            console.error('Failed to fetch queue status:', error.response?.status, error.message);
            // Return error state for unauthorized users
            if (error.response?.status === 401 || error.response?.status === 403) {
                return {
                    success: false,
                    error: 'Authentication required',
                    data: {}
                };
            }
            throw error;
        }
    }

    // Check report service health
    async checkHealth() {
        try {
            const response = await apiClient.get(`${REPORT_BASE_URL}/health`);
            return response.data;
        } catch (error) {
            console.error('Error checking report service health:', error);
            throw error;
        }
    }

    // Share a report
    async shareReport(reportId, shareOptions = {}) {
        try {
            const response = await apiClient.post(`${REPORT_BASE_URL}/${reportId}/share`, shareOptions);
            return response.data;
        } catch (error) {
            console.error('Error sharing report:', error);
            throw error;
        }
    }

    // Helper to generate report with template
    async generateReport(templateId, params = {}) {
        const reportData = {
            template_id: templateId,
            title: params.title || `Report - ${new Date().toLocaleString()}`,
            description: params.description || '',
            priority: params.priority || 'normal',
            parameters: params.parameters || {},
            output_format: params.output_format || 'pdf',
            honey_jar_id: params.honey_jar_id,
            scrambling_enabled: params.scrambling_enabled !== false
        };

        return this.createReport(reportData);
    }

    // Demo data helpers for authenticated users with empty databases
    getDemoTemplates() {
        return [
            {
                id: 'demo-1',
                name: 'System Health Report',
                description: 'Comprehensive system health and performance analysis',
                category: 'system',
                required_role: 'user',
                is_active: true,
                output_formats: ['pdf', 'html'],
                estimated_time: '2 minutes'
            },
            {
                id: 'demo-2',
                name: 'Security Audit Report',
                description: 'Authentication events and security metrics',
                category: 'security',
                required_role: 'admin',
                is_active: true,
                output_formats: ['pdf', 'csv'],
                estimated_time: '3 minutes'
            },
            {
                id: 'demo-3',
                name: 'User Activity Summary',
                description: 'Detailed breakdown of user interactions and engagement',
                category: 'analytics',
                required_role: 'user',
                is_active: true,
                output_formats: ['pdf', 'xlsx'],
                estimated_time: '1 minute'
            }
        ];
    }

    getDemoReports() {
        const now = new Date();
        return [
            {
                id: 'demo-report-1',
                title: 'Monthly System Health Analysis',
                template_name: 'System Health Report',
                status: 'completed',
                created_at: new Date(now - 86400000).toISOString(), // 1 day ago
                completed_at: new Date(now - 86300000).toISOString(),
                output_format: 'pdf',
                file_size: 2457600,
                user_id: 'demo-user'
            },
            {
                id: 'demo-report-2',
                title: 'Weekly Security Audit',
                template_name: 'Security Audit Report',
                status: 'processing',
                created_at: new Date(now - 600000).toISOString(), // 10 minutes ago
                output_format: 'pdf',
                progress: 45,
                user_id: 'demo-user'
            },
            {
                id: 'demo-report-3',
                title: 'User Engagement Metrics',
                template_name: 'User Activity Summary',
                status: 'completed',
                created_at: new Date(now - 172800000).toISOString(), // 2 days ago
                completed_at: new Date(now - 172700000).toISOString(),
                output_format: 'xlsx',
                file_size: 524288,
                user_id: 'demo-user'
            }
        ];
    }

    getDemoQueueStatus() {
        return {
            queue_name: 'default',
            pending_reports: 3,
            processing_reports: 1,
            completed_today: 8,
            failed_today: 0,
            average_processing_time: '2.3 minutes',
            user_active_reports: 2,
            estimated_wait_time: '5 minutes'
        };
    }
}

// Export singleton instance
const reportApi = new ReportApiService();
export default reportApi;