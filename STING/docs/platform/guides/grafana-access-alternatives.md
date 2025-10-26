# STING Grafana Access Alternatives for End Users

## 🎯 **Current Problem**

The existing Grafana integration has several limitations that prevent seamless end-user access:

### **Issues Identified:**
1. **Hardcoded localhost URLs** - Only works on local deployments
2. **Direct port access required** - Users must manually access `:3001` 
3. **iframe security restrictions** - Content Security Policy blocks embedded dashboards
4. **Separate authentication** - Grafana auth is disconnected from STING sessions
5. **Complex setup** - Requires observability services which often fail on constrained systems

## 🛠️ **Alternative Solutions**

### **Solution 1: STING Dashboard Proxy (Recommended)**

**Concept**: Create a backend proxy that fetches Grafana dashboard data and serves it through STING's own API.

#### **Architecture:**
```
STING Frontend → STING Backend → Grafana API → Dashboard Data
```

#### **Benefits:**
- ✅ Single authentication system
- ✅ Works behind corporate firewalls
- ✅ No iframe security issues
- ✅ Responsive design integration
- ✅ Custom styling to match STING themes

#### **Implementation:**
```python
# New route: /app/routes/dashboard_proxy_routes.py
@dashboard_proxy_bp.route('/api/dashboards/<dashboard_id>/data')
@require_auth
def get_dashboard_data(dashboard_id):
    """Proxy Grafana dashboard data through STING API"""
    grafana_url = current_app.config.get('GRAFANA_BASE_URL', 'http://grafana:3000')
    grafana_user = current_app.config.get('GRAFANA_API_USER', 'admin')
    grafana_pass = current_app.config.get('GRAFANA_API_PASSWORD', 'admin')
    
    try:
        # Fetch dashboard JSON from Grafana API
        response = requests.get(
            f"{grafana_url}/api/dashboards/uid/{dashboard_id}",
            auth=(grafana_user, grafana_pass),
            headers={'Accept': 'application/json'}
        )
        
        if response.status_code == 200:
            dashboard_data = response.json()
            # Transform data for STING frontend
            return jsonify({
                'status': 'success',
                'data': transform_dashboard_data(dashboard_data)
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': 'Dashboard not available'
            }), 404
            
    except Exception as e:
        logger.error(f"Dashboard proxy error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Observability service unavailable'
        }), 503
```

### **Solution 2: Native STING Dashboards**

**Concept**: Replace Grafana dependencies with native STING dashboard components using Chart.js/D3.

#### **Benefits:**
- ✅ No external dependencies
- ✅ Perfect theme integration  
- ✅ Mobile-responsive design
- ✅ Faster loading times
- ✅ Works without observability services

#### **Implementation:**
```jsx
// New component: /frontend/src/components/dashboard/NativeDashboard.jsx
import { Line, Bar, Doughnut } from 'react-chartjs-2';

const NativeDashboard = ({ dashboardType }) => {
  const [metrics, setMetrics] = useState({});
  
  useEffect(() => {
    // Fetch metrics from STING API instead of Grafana
    fetchSTINGMetrics(dashboardType);
  }, [dashboardType]);

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { labels: { color: '#f1f5f9' } },
      title: { color: '#fbbf24' }
    },
    scales: {
      x: { ticks: { color: '#94a3b8' } },
      y: { ticks: { color: '#94a3b8' } }
    }
  };

  switch (dashboardType) {
    case 'system-overview':
      return <SystemOverviewDashboard metrics={metrics} />;
    case 'auth-audit':  
      return <AuthAuditDashboard metrics={metrics} />;
    case 'pii-compliance':
      return <PIIComplianceDashboard metrics={metrics} />;
    default:
      return <GenericDashboard metrics={metrics} />;
  }
};
```

### **Solution 3: Hybrid Dashboard System**

**Concept**: Combine native STING dashboards for core metrics with optional Grafana integration for advanced users.

#### **Benefits:**
- ✅ Works for all users (native fallback)
- ✅ Advanced features available when observability enabled
- ✅ Progressive enhancement approach
- ✅ Graceful degradation

#### **Implementation:**
```jsx
const HybridDashboard = ({ dashboardId, title }) => {
  const [grafanaAvailable, setGrafanaAvailable] = useState(false);
  const [useNative, setUseNative] = useState(true);

  useEffect(() => {
    checkGrafanaAvailability().then(setGrafanaAvailable);
  }, []);

  if (!grafanaAvailable || useNative) {
    return (
      <div>
        <NativeDashboard dashboardType={dashboardId} />
        {grafanaAvailable && (
          <button 
            onClick={() => setUseNative(false)}
            className="mt-4 text-amber-400 hover:text-amber-300"
          >
            Switch to Advanced Grafana View
          </button>
        )}
      </div>
    );
  }

  return (
    <div>
      <ProxyGrafanaDashboard dashboardId={dashboardId} />
      <button 
        onClick={() => setUseNative(true)}
        className="mt-4 text-amber-400 hover:text-amber-300"
      >
        Switch to Native View
      </button>
    </div>
  );
};
```

### **Solution 4: Metrics API Integration**

**Concept**: Create a standardized metrics collection system that works with or without Grafana.

#### **Benefits:**
- ✅ Consistent data regardless of backend
- ✅ Easy to extend with new metrics
- ✅ Database-backed for historical data
- ✅ API-first approach

#### **Implementation:**
```python
# New model: /app/models/metrics_models.py
class SystemMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # counter, gauge, histogram
    labels = db.Column(db.JSON)  # For grouping/filtering
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(50), default='sting')  # sting, grafana, custom

# New service: /app/services/metrics_service.py
class MetricsService:
    @staticmethod
    def collect_system_metrics():
        """Collect metrics from various sources"""
        metrics = {}
        
        # System health metrics
        metrics['system_uptime'] = get_system_uptime()
        metrics['memory_usage'] = get_memory_usage() 
        metrics['cpu_usage'] = get_cpu_usage()
        
        # Application metrics
        metrics['active_sessions'] = get_active_sessions()
        metrics['api_requests_total'] = get_api_request_count()
        metrics['database_connections'] = get_db_connections()
        
        # Security metrics
        metrics['auth_attempts'] = get_auth_attempts()
        metrics['pii_detections'] = get_pii_detection_count()
        metrics['failed_logins'] = get_failed_login_count()
        
        return metrics

    @staticmethod
    def get_dashboard_data(dashboard_type, time_range='24h'):
        """Get dashboard data for specific dashboard type"""
        query_map = {
            'system-overview': ['system_uptime', 'memory_usage', 'cpu_usage'],
            'auth-audit': ['auth_attempts', 'failed_logins', 'active_sessions'],
            'pii-compliance': ['pii_detections', 'sanitization_count']
        }
        
        metrics = query_map.get(dashboard_type, [])
        return SystemMetric.query.filter(
            SystemMetric.metric_name.in_(metrics),
            SystemMetric.timestamp >= get_time_range(time_range)
        ).all()
```

## 🎯 **Recommended Implementation Plan**

### **Phase 1: Native Dashboard Foundation (High Priority)**
1. **Create native dashboard components** using Chart.js
2. **Implement metrics collection API** for core STING metrics
3. **Replace hardcoded Grafana URLs** with native dashboards
4. **Add theme-aware styling** for dashboard components

### **Phase 2: Dashboard Proxy (Medium Priority)**  
1. **Implement Grafana proxy routes** for advanced users
2. **Add Grafana availability detection** 
3. **Create hybrid dashboard system** with graceful fallback
4. **Implement dashboard authentication integration**

### **Phase 3: Enhanced Features (Low Priority)**
1. **Add real-time updates** via WebSocket
2. **Implement custom dashboard builder**
3. **Add data export functionality**
4. **Create mobile-optimized dashboard views**

## 📊 **Native Dashboard Specifications**

### **System Overview Dashboard**
```jsx
const SystemOverviewDashboard = () => (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <MetricCard 
      title="System Health"
      metrics={['uptime', 'memory_usage', 'cpu_usage']}
      chartType="gauge"
    />
    <MetricCard 
      title="Request Volume" 
      metrics={['api_requests', 'response_time']}
      chartType="line"
    />
    <MetricCard 
      title="Service Status"
      metrics={['service_health']}
      chartType="status-grid"
    />
    <MetricCard 
      title="Active Users"
      metrics={['active_sessions', 'new_registrations']}
      chartType="bar"
    />
  </div>
);
```

### **Authentication Audit Dashboard**
```jsx
const AuthAuditDashboard = () => (
  <div className="space-y-6">
    <MetricCard 
      title="Login Activity"
      metrics={['successful_logins', 'failed_logins']}
      chartType="timeline"
    />
    <MetricCard 
      title="Authentication Methods"
      metrics={['password_logins', 'webauthn_logins', 'magic_link_logins']}
      chartType="doughnut"
    />
    <MetricCard 
      title="Security Events"
      metrics={['suspicious_activity', 'blocked_ips', 'rate_limited']}
      chartType="alerts-table"
    />
  </div>
);
```

### **PII Compliance Dashboard**
```jsx
const PIIComplianceDashboard = () => (
  <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
    <MetricCard 
      title="PII Detection Rate"
      metrics={['pii_detected', 'false_positives']}
      chartType="line"
    />
    <MetricCard 
      title="Compliance Coverage"
      metrics={['gdpr_compliance', 'hipaa_compliance', 'ccpa_compliance']}
      chartType="compliance-gauge"
    />
    <MetricCard 
      title="Data Sanitization"
      metrics={['sanitized_logs', 'sanitized_files', 'sanitized_reports']}
      chartType="stacked-bar"
    />
  </div>
);
```

## 🔧 **Configuration Options**

### **Environment Variables**
```bash
# Grafana integration (optional)
GRAFANA_ENABLED=true
GRAFANA_BASE_URL=http://grafana:3000
GRAFANA_API_USER=admin
GRAFANA_API_PASSWORD=admin

# Native dashboards (always available)
NATIVE_DASHBOARDS_ENABLED=true
METRICS_COLLECTION_INTERVAL=30s
METRICS_RETENTION_DAYS=30

# Dashboard preferences
DEFAULT_DASHBOARD_TYPE=native  # native, grafana, hybrid
DASHBOARD_REFRESH_INTERVAL=30s
ENABLE_REAL_TIME_UPDATES=true
```

### **Configuration in config.yml**
```yaml
dashboards:
  type: hybrid  # native, grafana, hybrid
  grafana:
    enabled: true
    base_url: http://grafana:3000
    api_user: admin
    api_password: ${GRAFANA_PASSWORD}
  native:
    enabled: true
    refresh_interval: 30s
    chart_theme: auto  # auto, light, dark
  metrics:
    collection_interval: 30s
    retention_days: 30
    sources: [sting, grafana, custom]
```

## ✅ **Success Criteria**

1. **Universal Access**: All users can access dashboards regardless of observability service status
2. **Theme Integration**: Dashboards match STING theme system perfectly
3. **Mobile Responsive**: Dashboards work well on all device sizes
4. **Performance**: Native dashboards load faster than Grafana iframes
5. **Security**: All dashboard access respects STING authentication
6. **Graceful Degradation**: System works with or without Grafana
7. **User Choice**: Users can prefer native or Grafana views

---

**Recommended Start**: Implement **Solution 1 (Dashboard Proxy)** combined with **Solution 2 (Native Dashboards)** for a robust hybrid approach that ensures all users have access to monitoring capabilities.