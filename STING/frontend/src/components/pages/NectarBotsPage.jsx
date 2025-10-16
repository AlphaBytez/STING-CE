import React from 'react';
import {
  Bot,
  MessageCircle,
  Users,
  TrendingUp
} from 'lucide-react';
import NectarBotManager from '../admin/NectarBotManager';

const NectarBotsPage = () => {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Bot className="w-8 h-8 text-yellow-500" />
          <h1 className="text-3xl font-bold text-white">Nectar Bots</h1>
        </div>
        <p className="text-gray-400">Create and manage AI-powered conversation bots for your organization</p>
      </div>

      {/* Main Content - NectarBotManager Component */}
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl border border-slate-700">
        <NectarBotManager />
      </div>

      {/* Feature Cards */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-800/30 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-lg">
              <MessageCircle className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold mb-2">Smart Conversations</h3>
              <p className="text-gray-400 text-sm">
                AI-powered bots that understand context and provide intelligent responses to your users.
              </p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800/30 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-lg">
              <Users className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold mb-2">Human Handoff</h3>
              <p className="text-gray-400 text-sm">
                Seamlessly escalate complex queries to human agents when needed.
              </p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800/30 backdrop-blur-sm rounded-xl border border-gray-700 p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-gradient-to-br from-green-500/20 to-emerald-500/20 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold mb-2">Analytics & Insights</h3>
              <p className="text-gray-400 text-sm">
                Track performance, conversation metrics, and optimize your bot interactions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NectarBotsPage;