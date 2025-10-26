import React, { useState } from 'react';
import { 
  Network,
  Cpu,
  Globe,
  Shield,
  Users,
  Server,
  Zap,
  GitBranch,
  Activity,
  Lock,
  Sparkles,
  AlertTriangle,
  ChevronRight,
  Settings,
  Cloud,
  HardDrive,
  UserCheck,
  Building,
  Key
} from 'lucide-react';

const SwarmOrchestrationPage = () => {
  const [selectedDemo, setSelectedDemo] = useState('overview');

  const demoNodes = [
    {
      id: 1,
      name: "Queen Bee - Primary",
      type: "controller",
      status: "active",
      location: "US-East",
      resources: { cpu: 8, memory: 32, gpu: 2 },
      connections: 3
    },
    {
      id: 2,
      name: "Worker Bee Node 1",
      type: "worker",
      status: "active",
      location: "US-West",
      resources: { cpu: 16, memory: 64, gpu: 4 },
      connections: 1
    },
    {
      id: 3,
      name: "Worker Bee Node 2",
      type: "worker",
      status: "active",
      location: "EU-Central",
      resources: { cpu: 12, memory: 48, gpu: 2 },
      connections: 1
    },
    {
      id: 4,
      name: "Worker Bee Node 3",
      type: "worker",
      status: "pending",
      location: "Asia-Pacific",
      resources: { cpu: 8, memory: 32, gpu: 1 },
      connections: 0
    }
  ];

  const enterpriseFeatures = [
    {
      icon: Network,
      title: "Distributed Processing",
      description: "Spread Bee's workload across multiple nodes for faster response times"
    },
    {
      icon: Shield,
      title: "Enterprise Security",
      description: "LDAP, SAML, and OIDC integration for seamless authentication"
    },
    {
      icon: Users,
      title: "Team Resource Allocation",
      description: "Assign dedicated compute resources to specific teams or departments"
    },
    {
      icon: GitBranch,
      title: "Honey Jar Federation",
      description: "Share knowledge bases across nodes while maintaining security"
    },
    {
      icon: Cpu,
      title: "GPU Resource Pooling",
      description: "Dynamically allocate GPU resources based on demand"
    },
    {
      icon: Activity,
      title: "Real-time Monitoring",
      description: "Track performance, usage, and health across your entire swarm"
    }
  ];

  const configExample = `# swarm-config.yaml
swarm:
  name: "Enterprise Hive"
  controller:
    node: "queen-bee-primary"
    port: 8443
  
  authentication:
    providers:
      - type: "ldap"
        server: "ldap.company.com"
        base_dn: "dc=company,dc=com"
      - type: "saml"
        idp_url: "https://sso.company.com"
        
  worker_nodes:
    - name: "worker-bee-1"
      location: "us-west"
      resources:
        cpu: 16
        memory: "64GB"
        gpu: 4
      teams: ["engineering", "research"]
      
    - name: "worker-bee-2"
      location: "eu-central"
      resources:
        cpu: 12
        memory: "48GB"
        gpu: 2
      teams: ["support", "sales"]
      
  honey_jars:
    federation:
      enabled: true
      sync_interval: "5m"
      permissions:
        - pot: "platform-knowledge"
          nodes: ["all"]
        - pot: "customer-data"
          nodes: ["worker-bee-2"]`;

  return (
    <div className="dark-theme">
      <div className="p-6 max-w-7xl mx-auto">
      {/* Enterprise Banner */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-6 mb-8 text-white">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Network className="w-10 h-10" />
              <h1 className="text-3xl font-bold">Swarm Orchestration</h1>
              <span className="px-3 py-1 bg-white/20 rounded-full text-sm font-semibold flex items-center">
                ENTERPRISE
              </span>
            </div>
            <p className="text-white/90 text-lg">
              Scale Bee across your organization with distributed clustering
            </p>
          </div>
          <div className="hidden lg:block">
            <Sparkles className="w-24 h-24 text-white/20" />
          </div>
        </div>
      </div>

      {/* Alert Banner */}
      <div className="backdrop-blur-md bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 mb-8">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-amber-300 mb-1">Enterprise Feature Demo</h3>
            <p className="text-sm text-gray-200">
              This is a demonstration of STING's enterprise capabilities. Swarm Orchestration allows you to 
              create distributed Bee clusters, manage resources across teams, and integrate with enterprise 
              authentication systems. Contact sales to enable this feature for your organization.
            </p>
          </div>
          <button className="px-4 py-2 backdrop-blur-md bg-amber-500/20 border border-amber-400/30 text-amber-200 rounded-2xl hover:bg-amber-500/30 transition-colors text-sm font-medium">
            Contact Sales
          </button>
        </div>
      </div>

      {/* Feature Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {enterpriseFeatures.map((feature, index) => (
          <div key={index} className="backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl shadow p-6 hover:bg-white/10 hover:border-white/20 transition-all duration-300">
            <div className="flex items-start gap-4">
              <div className="p-3 backdrop-blur-md bg-purple-500/20 border border-purple-400/30 rounded-2xl">
                <feature.icon className="w-6 h-6 text-purple-300" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-100 mb-1">{feature.title}</h3>
                <p className="text-sm text-gray-300">{feature.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Demo Tabs */}
      <div className="backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl shadow">
        <div className="border-b border-white/10">
          <nav className="flex">
            <button
              onClick={() => setSelectedDemo('overview')}
              className={`px-6 py-3 font-medium text-sm transition-colors ${
                selectedDemo === 'overview'
                  ? 'border-b-2 border-purple-400 text-purple-300'
                  : 'text-gray-300 hover:text-gray-100'
              }`}
            >
              Cluster Overview
            </button>
            <button
              onClick={() => setSelectedDemo('configuration')}
              className={`px-6 py-3 font-medium text-sm transition-colors ${
                selectedDemo === 'configuration'
                  ? 'border-b-2 border-purple-400 text-purple-300'
                  : 'text-gray-300 hover:text-gray-100'
              }`}
            >
              Configuration
            </button>
            <button
              onClick={() => setSelectedDemo('monitoring')}
              className={`px-6 py-3 font-medium text-sm transition-colors ${
                selectedDemo === 'monitoring'
                  ? 'border-b-2 border-purple-400 text-purple-300'
                  : 'text-gray-300 hover:text-gray-100'
              }`}
            >
              Monitoring
            </button>
          </nav>
        </div>

        <div className="p-6">
          {selectedDemo === 'overview' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Distributed Bee Cluster</h3>
              
              {/* Cluster Visualization */}
              <div className="backdrop-blur-md bg-gray-800/50 border border-white/10 rounded-2xl p-6 mb-6">
                <div className="relative">
                  {/* Queen Node */}
                  <div className="flex justify-center mb-8">
                    <div className="backdrop-blur-md bg-gradient-to-br from-purple-500/80 to-indigo-500/80 border border-purple-400/30 text-white rounded-2xl p-4 shadow-lg">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 backdrop-blur-md bg-white/20 border border-white/30 rounded">
                          <Server className="w-6 h-6" />
                        </div>
                        <div>
                          <h4 className="font-semibold">Queen Bee - Primary</h4>
                          <p className="text-sm text-white/80">Controller Node</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded p-1 text-center">
                          <p className="text-white/70">CPU</p>
                          <p className="font-semibold">8 cores</p>
                        </div>
                        <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded p-1 text-center">
                          <p className="text-white/70">Memory</p>
                          <p className="font-semibold">32 GB</p>
                        </div>
                        <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded p-1 text-center">
                          <p className="text-white/70">GPU</p>
                          <p className="font-semibold">2x</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Connection Lines (visual representation) */}
                  <div className="absolute top-24 left-1/2 transform -translate-x-1/2 w-0.5 h-16 bg-gray-600"></div>

                  {/* Worker Nodes */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {demoNodes.filter(node => node.type === 'worker').map((node) => (
                      <div key={node.id} className={`backdrop-blur-md rounded-2xl p-4 shadow ${
                        node.status === 'active' 
                          ? 'bg-gray-700/60 border-2 border-green-400/50' 
                          : 'bg-gray-600/60 border-2 border-gray-400/50'
                      }`}>
                        <div className="flex items-center gap-3 mb-2">
                          <div className={`p-2 backdrop-blur-md rounded border ${
                            node.status === 'active' ? 'bg-green-500/20 border-green-400/30' : 'bg-gray-500/20 border-gray-400/30'
                          }`}>
                            <Server className={`w-5 h-5 ${
                              node.status === 'active' ? 'text-green-300' : 'text-gray-300'
                            }`} />
                          </div>
                          <div>
                            <h4 className="font-semibold text-gray-100">{node.name}</h4>
                            <p className="text-sm text-gray-300">{node.location}</p>
                          </div>
                        </div>
                          <div className="grid grid-cols-3 gap-2 text-xs">
                            <div className="backdrop-blur-md bg-gray-800/60 border border-white/10 rounded p-1 text-center">
                              <p className="text-gray-300">CPU</p>
                              <p className="font-semibold text-gray-100">{node.resources.cpu}</p>
                            </div>
                            <div className="backdrop-blur-md bg-gray-800/60 border border-white/10 rounded p-1 text-center">
                              <p className="text-gray-300">RAM</p>
                              <p className="font-semibold text-gray-100">{node.resources.memory}GB</p>
                            </div>
                            <div className="backdrop-blur-md bg-gray-800/60 border border-white/10 rounded p-1 text-center">
                              <p className="text-gray-300">GPU</p>
                              <p className="font-semibold text-gray-100">{node.resources.gpu}x</p>
                            </div>
                          </div>                        <div className="mt-2 text-xs">
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full backdrop-blur-md border ${
                            node.status === 'active' 
                              ? 'bg-green-500/20 border-green-400/30 text-green-300' 
                              : 'bg-gray-500/20 border-gray-400/30 text-gray-300'
                          }`}>
                            <Zap className="w-3 h-3" />
                            {node.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Resource Summary */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="backdrop-blur-md bg-purple-500/20 border border-purple-400/30 rounded-2xl p-4">
                  <div className="flex items-center gap-2 text-purple-300 mb-1">
                    <Server className="w-4 h-4" />
                    <p className="text-sm font-medium">Total Nodes</p>
                  </div>
                  <p className="text-2xl font-bold text-gray-100">4</p>
                </div>
                <div className="backdrop-blur-md bg-blue-500/20 border border-blue-400/30 rounded-2xl p-4">
                  <div className="flex items-center gap-2 text-blue-300 mb-1">
                    <Cpu className="w-4 h-4" />
                    <p className="text-sm font-medium">Total CPUs</p>
                  </div>
                  <p className="text-2xl font-bold text-gray-100">44 cores</p>
                </div>
                <div className="backdrop-blur-md bg-green-500/20 border border-green-400/30 rounded-2xl p-4">
                  <div className="flex items-center gap-2 text-green-300 mb-1">
                    <HardDrive className="w-4 h-4" />
                    <p className="text-sm font-medium">Total Memory</p>
                  </div>
                  <p className="text-2xl font-bold text-gray-100">176 GB</p>
                </div>
                <div className="backdrop-blur-md bg-orange-500/20 border border-orange-400/30 rounded-2xl p-4">
                  <div className="flex items-center gap-2 text-orange-300 mb-1">
                    <Zap className="w-4 h-4" />
                    <p className="text-sm font-medium">Total GPUs</p>
                  </div>
                  <p className="text-2xl font-bold text-gray-100">9</p>
                </div>
              </div>
            </div>
          )}

          {selectedDemo === 'configuration' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Simple Text-Based Configuration</h3>
              <p className="text-gray-400 mb-4">
                Swarm Orchestration uses simple, readable YAML configuration files. No complex UI needed - 
                just define your cluster, authentication, and resource allocation in plain text.
              </p>
              
              <div className="backdrop-blur-md bg-gray-900/60 border border-white/10 rounded-2xl p-6 overflow-x-auto">
                <pre className="text-sm text-gray-100 font-mono whitespace-pre">
                  <code>{configExample}</code>
                </pre>
              </div>

              <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="backdrop-blur-md bg-blue-500/20 border border-blue-400/30 rounded-2xl p-4">
                  <h4 className="font-semibold text-blue-200 mb-2 flex items-center gap-2">
                    <UserCheck className="w-5 h-5" />
                    Authentication Integration
                  </h4>
                  <ul className="text-sm text-blue-100 space-y-1">
                    <li>• LDAP/Active Directory support</li>
                    <li>• SAML 2.0 compatibility</li>
                    <li>• OIDC/OAuth2 integration</li>
                    <li>• Multi-factor authentication</li>
                  </ul>
                </div>
                <div className="backdrop-blur-md bg-green-500/20 border border-green-400/30 rounded-2xl p-4">
                  <h4 className="font-semibold text-green-200 mb-2 flex items-center gap-2">
                    <Building className="w-5 h-5" />
                    Resource Management
                  </h4>
                  <ul className="text-sm text-green-100 space-y-1">
                    <li>• Team-based resource allocation</li>
                    <li>• Dynamic GPU assignment</li>
                     <li>• Honey Jar federation</li>
                    <li>• Priority-based scheduling</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {selectedDemo === 'monitoring' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Real-time Swarm Monitoring</h3>
              
              {/* Mock Monitoring Dashboard */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="backdrop-blur-md bg-gray-800/50 border border-white/10 rounded-2xl p-6">
                  <h4 className="font-medium text-gray-100 mb-4">Cluster Health</h4>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Queen Bee Status</span>
                      <span className="flex items-center gap-1 text-green-300 text-sm font-medium">
                        <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                        Healthy
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Worker Nodes</span>
                      <span className="text-sm font-medium text-gray-100">3/4 Active</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Network Latency</span>
                      <span className="text-sm font-medium text-gray-100">12ms avg</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Sync Status</span>
                      <span className="text-sm font-medium text-green-300">Synchronized</span>
                    </div>
                  </div>
                </div>

                <div className="backdrop-blur-md bg-gray-800/50 border border-white/10 rounded-2xl p-6">
                  <h4 className="font-medium text-gray-100 mb-4">Resource Utilization</h4>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-300">CPU Usage</span>
                        <span className="font-medium text-gray-100">68%</span>
                      </div>
                      <div className="w-full backdrop-blur-md bg-gray-600/50 border border-white/10 rounded-full h-2">
                        <div className="bg-purple-500 h-2 rounded-full" style={{width: '68%'}}></div>
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-300">Memory Usage</span>
                        <span className="font-medium text-gray-100">45%</span>
                      </div>
                      <div className="w-full backdrop-blur-md bg-gray-600/50 border border-white/10 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full" style={{width: '45%'}}></div>
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-300">GPU Utilization</span>
                        <span className="font-medium text-gray-100">82%</span>
                      </div>
                      <div className="w-full backdrop-blur-md bg-gray-600/50 border border-white/10 rounded-full h-2">
                        <div className="bg-orange-500 h-2 rounded-full" style={{width: '82%'}}></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 backdrop-blur-md bg-yellow-500/20 border border-yellow-400/30 rounded-2xl p-4">
                <div className="flex items-start gap-3">
                  <Activity className="w-5 h-5 text-yellow-300 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-yellow-200 mb-1">Monitoring Benefits</h4>
                    <p className="text-sm text-yellow-100">
                      Track resource usage across your swarm, identify bottlenecks, and optimize 
                      performance. Get alerts for node failures, resource constraints, and security events.
                      All metrics are exportable to your existing monitoring infrastructure.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* CTA Section */}
      <div className="mt-8 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl p-8 text-center text-white">
        <h3 className="text-2xl font-bold mb-2">Ready to Scale Your Hive?</h3>
        <p className="text-white/90 mb-6 max-w-2xl mx-auto">
          Swarm Orchestration transforms STING into an enterprise-grade platform. Contact our sales team 
          to discuss how distributed Bee clusters can enhance your organization's AI capabilities.
        </p>
        <div className="flex gap-4 justify-center">
          <button className="px-6 py-3 bg-white text-purple-600 rounded-2xl hover:bg-gray-100 transition-colors font-semibold">
            Schedule Demo
          </button>
          <button className="px-6 py-3 bg-purple-700 text-white rounded-2xl hover:bg-purple-800 transition-colors font-semibold">
            Contact Sales
          </button>
        </div>
      </div>
    </div>
    </div>
  );
};

export default SwarmOrchestrationPage;