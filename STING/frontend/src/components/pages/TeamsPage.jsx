import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Crown, 
  Hexagon,
  TrendingUp,
  MessageSquare,
  Shield,
  Activity,
  Plus,
  Search,
  Filter,
  Star,
  Clock,
  Database,
  Zap
} from 'lucide-react';
import ScrollToTopButton from '../common/ScrollToTopButton';

const Teams = () => {
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState('all');

  // Mock data - replace with actual API calls
  useEffect(() => {
    // Simulate API call
    const mockTeams = [
      {
        id: 1,
        name: "DevOps Swarm",
        description: "Infrastructure and deployment specialists",
        role: "queen", // queen, worker, drone
        members: 8,
        HoneyJars: 5,
        activity: 95,
        status: "active",
        lastActive: "2 hours ago",
        specialization: "Infrastructure",
        recentActivity: [
          "Updated STING deployment scripts",
          "Added new monitoring dashboards",
          "Optimized database performance"
        ],
        HoneyJarAccess: [
          { name: "STING Platform Knowledge", role: "admin" },
          { name: "DevOps Best Practices", role: "admin" },
          { name: "Security Protocols", role: "viewer" }
        ],
        members_list: [
          { name: "Alice Johnson", role: "Queen", status: "online", avatar: "👑" },
          { name: "Bob Smith", role: "Worker", status: "active", avatar: "🐝" },
          { name: "Carol Davis", role: "Worker", status: "away", avatar: "🐝" }
        ]
      },
      {
        id: 2,
        name: "AI Research Hive",
        description: "Machine learning and AI development team",
        role: "worker",
        members: 12,
        HoneyJars: 8,
        activity: 88,
        status: "active",
        lastActive: "30 minutes ago",
        specialization: "AI/ML",
        recentActivity: [
          "Trained new LLM models",
          "Updated knowledge embeddings",
          "Published research findings"
        ],
        HoneyJarAccess: [
          { name: "AI Research Papers", role: "admin" },
          { name: "Model Training Data", role: "admin" },
          { name: "STING Platform Knowledge", role: "viewer" }
        ],
        members_list: [
          { name: "Dr. Emma Wilson", role: "Queen", status: "online", avatar: "👑" },
          { name: "David Chen", role: "Worker", status: "active", avatar: "🐝" },
          { name: "Sarah Kumar", role: "Worker", status: "online", avatar: "🐝" }
        ]
      },
      {
        id: 3,
        name: "Security Guard Drones",
        description: "Cybersecurity and threat monitoring",
        role: "drone",
        members: 6,
        HoneyJars: 3,
        activity: 72,
        status: "monitoring",
        lastActive: "5 minutes ago",
        specialization: "Security",
        recentActivity: [
          "Conducted security audit",
          "Updated threat detection rules",
          "Implemented new encryption protocols"
        ],
        HoneyJarAccess: [
          { name: "Security Protocols", role: "admin" },
          { name: "Threat Intelligence", role: "admin" },
          { name: "Incident Reports", role: "admin" }
        ],
        members_list: [
          { name: "Mike Rodriguez", role: "Drone Commander", status: "active", avatar: "🛡️" },
          { name: "Lisa Park", role: "Security Analyst", status: "online", avatar: "🔍" }
        ]
      },
      {
        id: 4,
        name: "Frontend Pollinators",
        description: "UI/UX and frontend development",
        role: "worker",
        members: 5,
        HoneyJars: 4,
        activity: 91,
        status: "active",
        lastActive: "1 hour ago",
        specialization: "Frontend",
        recentActivity: [
          "Redesigned Teams page",
           "Added Honey Jar management UI",          "Improved mobile responsiveness"
        ],
        HoneyJarAccess: [
          { name: "Design System", role: "admin" },
          { name: "User Research", role: "admin" },
          { name: "Frontend Best Practices", role: "admin" }
        ],
        members_list: [
          { name: "Alex Thompson", role: "Lead Designer", status: "online", avatar: "🎨" },
          { name: "Jordan Lee", role: "Frontend Dev", status: "active", avatar: "💻" }
        ]
      }
    ];
    
    setTeams(mockTeams);
  }, []);

  const getRoleIcon = (role) => {
    switch (role) {
      case 'queen': return <Crown className="w-5 h-5 text-yellow-500" />;
      case 'worker': return <Hexagon className="w-5 h-5 text-blue-500" />;
      case 'drone': return <Shield className="w-5 h-5 text-purple-500" />;
      default: return <Users className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'bg-green-900 text-green-300';
      case 'monitoring': return 'bg-blue-900 text-blue-300';
      case 'away': return 'bg-yellow-900 text-yellow-300';
      default: return 'bg-gray-500 text-gray-300';
    }
  };

  const getActivityColor = (activity) => {
    if (activity >= 90) return 'text-green-400';
    if (activity >= 70) return 'text-yellow-400';
    return 'text-red-400';
  };

  const filteredTeams = teams.filter(team => {
    const matchesSearch = team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         team.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = filterRole === 'all' || team.role === filterRole;
    return matchesSearch && matchesRole;
  });

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Users className="w-8 h-8 text-blue-500" />
          <h1 className="text-3xl font-bold text-white">Hive Teams</h1>
        </div>
        <p className="text-gray-400">Manage your collaborative swarms and monitor team activity across the hive</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="standard-card rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="bg-blue-900 p-3 rounded-2xl">
              <Users className="w-6 h-6 text-blue-400" />
            </div>
            <span className="text-sm font-medium text-blue-600">+2 this week</span>
          </div>
          <h3 className="text-2xl font-bold text-gray-100">{teams.length}</h3>
          <p className="text-sm text-gray-400">Active Teams</p>
        </div>

        <div className="standard-card rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="bg-green-900 p-3 rounded-2xl">
              <Activity className="w-6 h-6 text-green-400" />
            </div>
            <span className="text-sm font-medium text-green-600">+5% this week</span>
          </div>
          <h3 className="text-2xl font-bold text-gray-100">
            {Math.round(teams.reduce((acc, team) => acc + team.activity, 0) / teams.length)}%
          </h3>
          <p className="text-sm text-gray-400">Avg Activity</p>
        </div>

        <div className="standard-card rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="bg-yellow-900 p-3 rounded-2xl">
              <Hexagon className="w-6 h-6 text-yellow-400" />
            </div>
            <span className="text-sm font-medium text-yellow-600">3 new today</span>
          </div>
          <h3 className="text-2xl font-bold text-gray-100">
            {teams.reduce((acc, team) => acc + team.HoneyJars, 0)}
          </h3>
           <p className="text-sm text-gray-400">Honey Jars</p>        </div>

        <div className="standard-card rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="bg-purple-900 p-3 rounded-2xl">
              <MessageSquare className="w-6 h-6 text-purple-400" />
            </div>
            <span className="text-sm font-medium text-purple-600">+12 today</span>
          </div>
          <h3 className="text-2xl font-bold text-gray-100">
            {teams.reduce((acc, team) => acc + team.members, 0)}
          </h3>
          <p className="text-sm text-gray-400">Total Members</p>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="standard-card rounded-2xl shadow-lg p-6 mb-8">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search teams..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-500 border border-gray-500 text-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <select
              value={filterRole}
              onChange={(e) => setFilterRole(e.target.value)}
              className="pl-10 pr-8 py-2 bg-gray-500 border border-gray-500 text-gray-100 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Roles</option>
              <option value="queen">Queens</option>
              <option value="worker">Workers</option>
              <option value="drone">Drones</option>
            </select>
          </div>
          <button className="bg-blue-600 text-white px-6 py-2 rounded-2xl hover:bg-blue-700 transition-colors flex items-center gap-2">
            <Plus className="w-5 h-5" />
            New Team
          </button>
        </div>
      </div>

      {/* Teams Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {filteredTeams.map((team) => (
          <div 
            key={team.id}
            className="standard-card rounded-2xl shadow-lg hover:shadow-xl transition-shadow cursor-pointer"
            onClick={() => setSelectedTeam(team)}          >
            <div className="p-6">
              {/* Team Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  {getRoleIcon(team.role)}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-100">{team.name}</h3>
                    <p className="text-sm text-gray-400">{team.specialization}</p>
                  </div>
                </div>
                <span className={`px-3 py-1 text-xs font-medium rounded-full ${getStatusColor(team.status)}`}>
                  {team.status}
                </span>
              </div>

              {/* Description */}
              <p className="text-gray-400 mb-4">{team.description}</p>

              {/* Metrics Row */}
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Users className="w-4 h-4 text-gray-400" />
                    <span className="text-lg font-semibold text-gray-100">{team.members}</span>
                  </div>
                  <span className="text-xs text-gray-400">Members</span>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Hexagon className="w-4 h-4 text-gray-400" />
                    <span className="text-lg font-semibold text-gray-100">{team.HoneyJars}</span>
                  </div>
                   <span className="text-xs text-gray-400">Honey Jars</span>                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Activity className="w-4 h-4 text-gray-400" />
                    <span className={`text-lg font-semibold ${getActivityColor(team.activity)}`}>
                      {team.activity}%
                    </span>
                  </div>
                  <span className="text-xs text-gray-400">Activity</span>
                </div>
              </div>

              {/* Recent Activity */}
              <div className="border-t pt-4">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-400">Last active: {team.lastActive}</span>
                </div>
                <div className="text-sm text-gray-400">
                  Latest: {team.recentActivity[0]}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Team Detail Modal */}
      {selectedTeam && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="standard-card-solid rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-500">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {getRoleIcon(selectedTeam.role)}
                  <div>
                    <h2 className="text-2xl font-bold text-gray-100">{selectedTeam.name}</h2>
                    <p className="text-gray-400">{selectedTeam.description}</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedTeam(null)}
                  className="text-gray-400 hover:text-gray-200 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Team Members */}
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-100">
                    <Users className="w-5 h-5" />
                    Team Members ({selectedTeam.members_list.length})
                  </h3>
                  <div className="space-y-3">
                    {selectedTeam.members_list.map((member, index) => (
                      <div key={index} className="flex items-center gap-3 p-3 bg-gray-500 rounded-2xl">
                        <span className="text-2xl">{member.avatar}</span>
                        <div className="flex-1">
                          <div className="font-medium text-gray-100">{member.name}</div>
                          <div className="text-sm text-gray-400">{member.role}</div>
                        </div>
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(member.status)}`}>
                          {member.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Honey Jar Access */}
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-100">
                    <Database className="w-5 h-5" />
                    Honey Jar Access
                  </h3>
                  <div className="space-y-3">
                    {selectedTeam.HoneyJarAccess.map((pot, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-500 rounded-2xl">
                        <div className="flex items-center gap-2">
                          <Hexagon className="w-4 h-4 text-yellow-500" />
                          <span className="font-medium text-gray-100">{pot.name}</span>
                        </div>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          pot.role === 'admin' ? 'bg-red-900 text-red-300' : 'bg-blue-900 text-blue-300'
                        }`}>
                          {pot.role}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Recent Activity */}
              <div className="mt-8">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-100">
                  <Zap className="w-5 h-5" />
                  Recent Activity
                </h3>
                <div className="space-y-2">
                  {selectedTeam.recentActivity.map((activity, index) => (
                    <div key={index} className="flex items-center gap-3 p-3 bg-gray-500 rounded-2xl">
                      <Activity className="w-4 h-4 text-green-400" />
                      <span className="text-gray-300">{activity}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {filteredTeams.length === 0 && (
        <div className="text-center py-12">
          <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-100 mb-2">No teams found</h3>
          <p className="text-gray-400 mb-4">Try adjusting your search or filter criteria</p>
          <button className="bg-blue-600 text-white px-6 py-2 rounded-2xl hover:bg-blue-700 transition-colors">
            Create First Team
          </button>
        </div>
      )}

      {/* Scroll to Top Button */}
      <ScrollToTopButton />
    </div>
  );
};

export default Teams;
