/**
 * Enterprise Feature Placeholder Component
 * Displays a professional placeholder for enterprise-only features in CE
 * 
 * Copyright 2025 STING-CE Contributors
 * Licensed under the Apache License, Version 2.0
 */

import React from 'react';
import { 
  Lock, 
  Sparkles, 
  ArrowRight, 
  Building2,
  Shield,
  Zap,
  Users,
  ShoppingBag,
  Network
} from 'lucide-react';
import { 
  getEnterprisePlaceholderText, 
  getEnterprisePlaceholderLink 
} from '../../utils/editionConfig';

// Feature-specific icons
const featureIcons = {
  marketplace: ShoppingBag,
  teams: Users,
  swarm: Network,
  'advanced-pii': Shield,
  'nectar-bot': Zap,
  default: Sparkles
};

// Feature descriptions
const featureDescriptions = {
  marketplace: 'Access the Hive Marketplace to discover and deploy pre-built AI agents, integrations, and workflows created by the community and certified partners.',
  teams: 'Collaborate with your organization using advanced team management, role-based access control, and shared workspaces.',
  swarm: 'Orchestrate distributed AI workloads across multiple nodes with intelligent load balancing and resource optimization.',
  'advanced-pii': 'Ensure compliance with advanced PII detection, automated redaction, and comprehensive audit trails for HIPAA, GDPR, and other regulations.',
  'nectar-bot': 'Deploy and manage intelligent bot assistants with custom training, multi-channel integration, and enterprise-grade performance.',
  default: 'Unlock advanced features and capabilities designed for enterprise-scale deployments and compliance requirements.'
};

// Feature benefits
const featureBenefits = {
  marketplace: [
    'Pre-built AI agents and workflows',
    'Certified partner integrations',
    'One-click deployment',
    'Community contributions'
  ],
  teams: [
    'Role-based access control',
    'Team workspaces',
    'Collaborative workflows',
    'Centralized management'
  ],
  swarm: [
    'Distributed processing',
    'Auto-scaling',
    'Load balancing',
    'Resource optimization'
  ],
  'advanced-pii': [
    'HIPAA compliance',
    'GDPR compliance',
    'Automated redaction',
    'Audit trails'
  ],
  'nectar-bot': [
    'Custom bot training',
    'Multi-channel support',
    'Analytics dashboard',
    'Enterprise SLA'
  ],
  default: [
    'Enterprise support',
    'Advanced features',
    'Priority updates',
    'Dedicated resources'
  ]
};

const EnterpriseFeaturePlaceholder = ({ 
  feature = 'default',
  title,
  customDescription,
  showBenefits = true,
  className = ''
}) => {
  const Icon = featureIcons[feature] || featureIcons.default;
  const description = customDescription || featureDescriptions[feature] || featureDescriptions.default;
  const benefits = featureBenefits[feature] || featureBenefits.default;
  const placeholderText = getEnterprisePlaceholderText();
  const learnMoreLink = getEnterprisePlaceholderLink();
  
  // Determine feature title if not provided
  const displayTitle = title || {
    marketplace: 'Marketplace',
    teams: 'Teams Management',
    swarm: 'Swarm Orchestration',
    'advanced-pii': 'Advanced PII Compliance',
    'nectar-bot': 'Nectar Bot Manager',
    default: 'Enterprise Feature'
  }[feature];

  return (
    <div className={`min-h-screen bg-gray-900 flex items-center justify-center p-8 ${className}`}>
      <div className="max-w-4xl w-full">
        {/* Main Card */}
        <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-2xl p-8 md:p-12">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-yellow-400/20 to-orange-500/20 rounded-2xl mb-6">
              <Icon className="w-10 h-10 text-yellow-400" />
            </div>
            
            <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
              {displayTitle}
            </h1>
            
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-gradient-to-r from-yellow-400/10 to-orange-500/10 border border-yellow-400/30 rounded-full mt-3">
              <Building2 className="w-4 h-4 text-yellow-400" />
              <span className="text-sm font-medium text-yellow-400">Enterprise Edition</span>
            </div>
          </div>

          {/* Description */}
          <p className="text-gray-300 text-lg text-center mb-8 max-w-2xl mx-auto leading-relaxed">
            {description}
          </p>

          {/* Benefits Grid */}
          {showBenefits && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              {benefits.map((benefit, index) => (
                <div key={index} className="flex items-start gap-3 p-4 bg-gray-800/30 rounded-lg border border-gray-700/50">
                  <div className="w-2 h-2 bg-yellow-400 rounded-full mt-2 flex-shrink-0" />
                  <span className="text-gray-300">{benefit}</span>
                </div>
              ))}
            </div>
          )}

          {/* CTA Section */}
          <div className="bg-gradient-to-r from-yellow-400/10 to-orange-500/10 border border-yellow-400/30 rounded-xl p-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <Lock className="w-5 h-5 text-yellow-400 mt-1 flex-shrink-0" />
                <div>
                  <p className="text-white font-medium mb-1">
                    {placeholderText}
                  </p>
                  <p className="text-gray-400 text-sm">
                    Upgrade to unlock this feature and more
                  </p>
                </div>
              </div>
              
              <a
                href={learnMoreLink}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-yellow-400 to-orange-500 text-gray-900 font-semibold rounded-lg hover:shadow-lg hover:shadow-yellow-400/25 transition-all duration-200 whitespace-nowrap"
              >
                Learn More
                <ArrowRight className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Additional Info */}
          <div className="mt-8 pt-8 border-t border-gray-700">
            <div className="flex flex-col md:flex-row items-center justify-center gap-6 text-sm text-gray-400">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4" />
                <span>Enterprise-grade security</span>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4" />
                <span>Priority support</span>
              </div>
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                <span>Dedicated account management</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Navigation Helper */}
        <div className="mt-6 text-center">
          <button
            onClick={() => window.history.back()}
            className="text-gray-400 hover:text-white transition-colors duration-200"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

export default EnterpriseFeaturePlaceholder;