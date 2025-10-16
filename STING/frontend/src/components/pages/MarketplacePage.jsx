import React, { useState, useEffect } from 'react';
import { 
  ShoppingBag, 
  Star, 
  Download, 
  Shield, 
  Hexagon,
  TrendingUp,
  Filter,
  Search,
  Grid,
  List,
  Eye,
  DollarSign,
  Users,
  Award,
  Lock,
  Unlock,
  Globe,
  Heart,
  MessageSquare,
  ExternalLink,
  Sparkles,
  AlertTriangle,
  Package,
  Zap,
  Building,
  Settings,
  Play,
  CheckCircle
} from 'lucide-react';
import { marketplaceApi } from '../../services/knowledgeApi';

const MarketplacePage = () => {
  const [HoneyJars, setHoneyJars] = useState([]);
  const [viewMode, setViewMode] = useState('grid'); // grid or list
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterType, setFilterType] = useState('all'); // free, premium, enterprise
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('popular'); // popular, rating, price, newest
  const [selectedPot, setSelectedPot] = useState(null);
  const [selectedDemo, setSelectedDemo] = useState('browse');

  // Load marketplace data from API
  useEffect(() => {
    loadMarketplaceListings();
  }, [searchTerm, filterCategory, filterType, sortBy]);

  const loadMarketplaceListings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const searchOptions = {
        query: searchTerm || undefined,
        tags: filterCategory !== 'all' ? [filterCategory] : undefined,
        sortBy: sortBy === 'popular' ? 'downloads' : sortBy,
        page: 1,
        pageSize: 50
      };
      
      if (filterType !== 'all') {
        // Map frontend filter to API license type
        const licenseTypeMap = {
          'free': 'Creative Commons',
          'premium': 'Commercial',
          'enterprise': 'Enterprise'
        };
        searchOptions.license_type = licenseTypeMap[filterType];
      }
      
      const response = await marketplaceApi.searchMarketplace(searchOptions);
      
      if (response && response.listings) {
        // Transform API response to match frontend format
        const transformedListings = response.listings.map(listing => ({
          id: listing.id,
          name: listing.honey_jar_name,
          description: listing.description,
          category: extractCategoryFromTags(listing.tags),
          type: mapLicenseToType(listing.license_type),
          price: listing.price,
          rating: listing.rating,
          downloads: listing.downloads,
          size: formatSize(listing.stats?.total_size_bytes || 0),
          documents: listing.stats?.document_count || 0,
          embeddings: listing.stats?.embedding_count || 0,
          author: listing.seller_name,
          authorAvatar: getAuthorAvatar(listing.seller_name),
          verified: true, // Assume verified for marketplace listings
          tags: listing.tags || [],
          lastUpdated: calculateTimeAgo(new Date(listing.created_date)),
          preview: listing.description.substring(0, 100) + '...',
          encryption: listing.license_type === 'Enterprise' ? 'AES-256' : 'none',
          license: listing.license_type,
          featured: listing.downloads > 1000, // Mark high-download items as featured
          trending: listing.downloads > 500 && new Date(listing.created_date) > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
        }));
        
        setHoneyJars(transformedListings);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (err) {
      console.warn('Failed to load marketplace listings, using mock data:', err.message);
      // Fallback to mock data
      const mockMarketplaceData = [
      {
        id: 1,
        name: "AI Research Papers Collection",
        description: "Comprehensive collection of cutting-edge AI research papers from top conferences including NeurIPS, ICML, and ICLR",
        category: "Research",
        type: "free",
        price: 0,
        rating: 4.8,
        downloads: 2341,
        size: "1.2 GB",
        documents: 5000,
        embeddings: 150000,
        author: "AI Research Hub",
        authorAvatar: "🎓",
        verified: true,
        tags: ["AI", "Research", "Machine Learning", "Deep Learning"],
        lastUpdated: "2 days ago",
        preview: "Contains papers on transformer architectures, computer vision, NLP, and reinforcement learning...",
        encryption: "none",
        license: "Creative Commons",
        featured: true,
        trending: true
      },
      {
        id: 2,
        name: "Enterprise Security Playbook",
        description: "Complete cybersecurity knowledge base with incident response procedures, threat intelligence, and best practices",
        category: "Security",
        type: "premium",
        price: 299,
        rating: 4.9,
        downloads: 156,
        size: "800 MB",
        documents: 1200,
        embeddings: 45000,
        author: "CyberSec Solutions",
        authorAvatar: "🛡️",
        verified: true,
        tags: ["Security", "Enterprise", "Compliance", "GDPR"],
        lastUpdated: "1 week ago",
        preview: "Comprehensive security framework including NIST guidelines, ISO 27001 compliance...",
        encryption: "AES-256",
        license: "Commercial",
        featured: false,
        trending: false
      },
      {
        id: 3,
        name: "Medical Diagnosis Assistant",
        description: "Medical knowledge base with symptoms, treatments, and diagnostic procedures for healthcare professionals",
        category: "Healthcare",
        type: "enterprise",
        price: 1299,
        rating: 4.7,
        downloads: 89,
        size: "2.1 GB",
        documents: 8500,
        embeddings: 280000,
        author: "MedTech Innovations",
        authorAvatar: "⚕️", 
        verified: true,
        tags: ["Healthcare", "Diagnosis", "Medical", "Clinical"],
        lastUpdated: "3 days ago",
        preview: "Evidence-based medical knowledge including ICD-10 codes, treatment protocols...",
        encryption: "HIPAA-compliant",
        license: "Enterprise",
        featured: true,
        trending: false
      },
      {
        id: 4,
        name: "Legal Document Templates",
        description: "Professional legal document templates and contract examples for business use",
        category: "Legal",
        type: "premium",
        price: 199,
        rating: 4.6,
        downloads: 445,
        size: "350 MB",
        documents: 850,
        embeddings: 25000,
        author: "LegalTech Pro",
        authorAvatar: "⚖️",
        verified: true,
        tags: ["Legal", "Contracts", "Business", "Templates"],
        lastUpdated: "1 day ago",
        preview: "Contract templates, NDAs, employment agreements, and legal precedents...",
        encryption: "client-side",
        license: "Commercial",
        featured: false,
        trending: true
      },
      {
        id: 5,
        name: "Software Development Best Practices",
        description: "Comprehensive guide to modern software development practices, patterns, and methodologies",
        category: "Technology",
        type: "free",
        price: 0,
        rating: 4.5,
        downloads: 1876,
        size: "650 MB",
        documents: 2200,
        embeddings: 75000,
        author: "DevCommunity",
        authorAvatar: "👨‍💻",
        verified: false,
        tags: ["Software", "Development", "Best Practices", "Patterns"],
        lastUpdated: "5 days ago",
        preview: "Clean code principles, design patterns, testing strategies, and CI/CD practices...",
        encryption: "none",
        license: "MIT",
        featured: false,
        trending: false
      },
      {
        id: 6,
        name: "Financial Markets Intelligence",
        description: "Real-time financial data, market analysis, and trading strategies for investment professionals",
        category: "Finance",
        type: "enterprise",
        price: 2499,
        rating: 4.9,
        downloads: 34,
        size: "3.2 GB",
        documents: 12000,
        embeddings: 400000,
        author: "FinanceAI Corp",
        authorAvatar: "📊",
        verified: true,
        tags: ["Finance", "Trading", "Investment", "Markets"],
        lastUpdated: "6 hours ago",
        preview: "Market data, SEC filings, earnings reports, and quantitative analysis models...",
        encryption: "bank-grade",
        license: "Enterprise",
        featured: true,
        trending: true
      }
    ];
    
    setHoneyJars(mockMarketplaceData);
    setError(null);
    } finally {
      setLoading(false);
    }
  };

  // Helper functions for API response transformation
  const extractCategoryFromTags = (tags) => {
    const categoryMap = {
      'ai': 'Research',
      'research': 'Research',
      'security': 'Security',
      'healthcare': 'Healthcare',
      'legal': 'Legal',
      'technology': 'Technology',
      'finance': 'Finance'
    };
    
    const foundCategory = tags?.find(tag => 
      Object.keys(categoryMap).includes(tag.toLowerCase())
    );
    
    return foundCategory ? categoryMap[foundCategory.toLowerCase()] : 'Technology';
  };

  const mapLicenseToType = (licenseType) => {
    if (!licenseType) return 'free';
    const license = licenseType.toLowerCase();
    if (license.includes('creative') || license.includes('free')) return 'free';
    if (license.includes('enterprise')) return 'enterprise';
    return 'premium';
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const calculateTimeAgo = (date) => {
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return '1 day ago';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
  };

  const getAuthorAvatar = (authorName) => {
    const avatars = ['🎓', '🛡️', '⚕️', '⚖️', '👨‍💻', '📊', '🏢', '🔬'];
    const index = authorName?.length || 0;
    return avatars[index % avatars.length];
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'free': return 'bg-green-100 text-green-800';
      case 'premium': return 'bg-blue-100 text-blue-800';
      case 'enterprise': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'Research': return '🎓';
      case 'Security': return '🛡️';
      case 'Healthcare': return '⚕️';
      case 'Legal': return '⚖️';
      case 'Technology': return '👨‍💻';
      case 'Finance': return '📊';
      default: return '📁';
    }
  };

  const filteredHoneyJars = HoneyJars.filter(pot => {
    const matchesSearch = pot.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         pot.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         pot.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesCategory = filterCategory === 'all' || pot.category === filterCategory;
    const matchesType = filterType === 'all' || pot.type === filterType;
    return matchesSearch && matchesCategory && matchesType;
  });

  const sortedHoneyJars = [...filteredHoneyJars].sort((a, b) => {
    switch (sortBy) {
      case 'rating': return b.rating - a.rating;
      case 'price': return a.price - b.price;
      case 'newest': return new Date(b.lastUpdated) - new Date(a.lastUpdated);
      case 'popular':
      default: return b.downloads - a.downloads;
    }
  });

  const featuredPots = HoneyJars.filter(pot => pot.featured);
  const trendingPots = HoneyJars.filter(pot => pot.trending);

  return (
    <div className="dark-theme">
      <div className="p-6 max-w-7xl mx-auto">
      {/* Enterprise Banner */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-6 mb-8 text-white">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <ShoppingBag className="w-10 h-10" />
              <h1 className="text-3xl font-bold">Security Marketplace</h1>
              <span className="px-3 py-1 bg-white/20 rounded-full text-sm font-semibold flex items-center">
                ENTERPRISE
              </span>
            </div>
            <p className="text-white/90 text-lg">
              Deploy pre-configured security templates and honeypot configurations
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
            <h3 className="font-semibold text-amber-300 mb-1">Enterprise Marketplace Demo</h3>
            <p className="text-sm text-gray-200">
              This is a demonstration of STING's enterprise marketplace capabilities. Deploy security templates,
              honeypot configurations, and detection rules from verified security vendors and the community.
              Contact sales to enable marketplace features for your organization.
            </p>
          </div>
          <button className="px-4 py-2 backdrop-blur-md bg-amber-500/20 border border-amber-400/30 text-amber-200 rounded-2xl hover:bg-amber-500/30 transition-colors text-sm font-medium">
            Contact Sales
          </button>
        </div>
      </div>

      {/* Marketplace Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="glass-subtle rounded-2xl p-6 hover:glass-medium transition-all duration-300">
          <div className="flex items-start gap-4">
            <div className="p-3 glass-medium rounded-2xl">
              <Shield className="w-6 h-6 text-blue-300" />
            </div>
            <div>
              <h3 className="font-semibold text-white mb-1">Verified Templates</h3>
              <p className="text-sm text-slate-300">Security-tested honeypot configurations from certified vendors</p>
            </div>
          </div>
        </div>
        <div className="glass-subtle rounded-2xl p-6 hover:glass-medium transition-all duration-300">
          <div className="flex items-start gap-4">
            <div className="p-3 glass-medium rounded-2xl">
              <Zap className="w-6 h-6 text-green-300" />
            </div>
            <div>
              <h3 className="font-semibold text-white mb-1">One-Click Deploy</h3>
              <p className="text-sm text-slate-300">Instantly deploy security templates with automated configuration</p>
            </div>
          </div>
        </div>
        <div className="glass-subtle rounded-2xl p-6 hover:glass-medium transition-all duration-300">
          <div className="flex items-start gap-4">
            <div className="p-3 glass-medium rounded-2xl">
              <Building className="w-6 h-6 text-purple-300" />
            </div>
            <div>
              <h3 className="font-semibold text-white mb-1">Enterprise Integration</h3>
              <p className="text-sm text-slate-300">Seamless integration with SIEM platforms and security tools</p>
            </div>
          </div>
        </div>
        <div className="glass-subtle rounded-2xl p-6 hover:glass-medium transition-all duration-300">
          <div className="flex items-start gap-4">
            <div className="p-3 glass-medium rounded-2xl">
              <Users className="w-6 h-6 text-orange-300" />
            </div>
            <div>
              <h3 className="font-semibold text-white mb-1">Community Driven</h3>
              <p className="text-sm text-slate-300">Crowdsourced security templates from the cybersecurity community</p>
            </div>
          </div>
        </div>
        <div className="glass-subtle rounded-2xl p-6 hover:glass-medium transition-all duration-300">
          <div className="flex items-start gap-4">
            <div className="p-3 glass-medium rounded-2xl">
              <TrendingUp className="w-6 h-6 text-red-300" />
            </div>
            <div>
              <h3 className="font-semibold text-white mb-1">Threat Intelligence</h3>
              <p className="text-sm text-slate-300">Real-time threat feeds integrated into honeypot configurations</p>
            </div>
          </div>
        </div>
        <div className="glass-subtle rounded-2xl p-6 hover:glass-medium transition-all duration-300">
          <div className="flex items-start gap-4">
            <div className="p-3 glass-medium rounded-2xl">
              <Settings className="w-6 h-6 text-yellow-300" />
            </div>
            <div>
              <h3 className="font-semibold text-white mb-1">Custom Templates</h3>
              <p className="text-sm text-slate-300">Create and share your own security templates with the community</p>
            </div>
          </div>
        </div>
      </div>

      {/* Demo Tabs */}
      <div className="glass-card rounded-2xl mb-8">
        <div className="border-b border-white/10">
          <nav className="flex">
            <button
              onClick={() => setSelectedDemo('browse')}
              className={`px-6 py-3 font-medium text-sm transition-colors ${
                selectedDemo === 'browse'
                  ? 'border-b-2 border-indigo-400 text-indigo-300'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Browse Templates
            </button>
            <button
              onClick={() => setSelectedDemo('deploy')}
              className={`px-6 py-3 font-medium text-sm transition-colors ${
                selectedDemo === 'deploy'
                  ? 'border-b-2 border-indigo-400 text-indigo-300'  
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Deploy Demo
            </button>
            <button
              onClick={() => setSelectedDemo('analytics')}
              className={`px-6 py-3 font-medium text-sm transition-colors ${
                selectedDemo === 'analytics'
                  ? 'border-b-2 border-indigo-400 text-indigo-300'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              Analytics
            </button>
          </nav>
        </div>

        <div className="p-6">
          {selectedDemo === 'browse' && (
            <div>
              {/* Loading and error states */}
              {error && (
                <div className="mb-4 p-3 backdrop-blur-md bg-orange-500/20 border border-orange-400/30 rounded-2xl">
                  <p className="text-orange-200 text-sm">⚠️ {error}</p>
                </div>
              )}
              {loading && (
                <div className="mb-4 flex items-center gap-2 text-sm text-gray-400">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                  Loading marketplace...
                </div>
              )}

              {/* Stats Row */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="glass-medium rounded-2xl p-4">
                  <div className="flex items-center gap-2 text-blue-300 mb-1">
                    <Package className="w-4 h-4" />
                    <p className="text-sm font-medium">Available Templates</p>
                  </div>
                  <p className="text-2xl font-bold text-white">{HoneyJars.length}</p>
                  <p className="text-xs text-blue-200">+12 this week</p>
                </div>
                <div className="glass-medium rounded-2xl p-4">
                  <div className="flex items-center gap-2 text-green-300 mb-1">
                    <Download className="w-4 h-4" />
                    <p className="text-sm font-medium">Total Downloads</p>
                  </div>
                  <p className="text-2xl font-bold text-white">
                    {HoneyJars.reduce((acc, pot) => acc + pot.downloads, 0).toLocaleString()}
                  </p>
                  <p className="text-xs text-green-200">+234 today</p>
                </div>
                <div className="glass-medium rounded-2xl p-4">
                  <div className="flex items-center gap-2 text-yellow-300 mb-1">
                    <Star className="w-4 h-4" />
                    <p className="text-sm font-medium">Verified Vendors</p>
                  </div>
                  <p className="text-2xl font-bold text-white">{HoneyJars.filter(pot => pot.verified).length}</p>
                  <p className="text-xs text-yellow-200">4.7 avg rating</p>
                </div>
                <div className="glass-medium rounded-2xl p-4">
                  <div className="flex items-center gap-2 text-purple-300 mb-1">
                    <Award className="w-4 h-4" />
                    <p className="text-sm font-medium">Featured</p>
                  </div>
                  <p className="text-2xl font-bold text-white">{featuredPots.length}</p>
                  <p className="text-xs text-purple-200">Enterprise ready</p>
                </div>
              </div>

              {/* Search and Filter */}
              <div className="glass-strong rounded-2xl p-6 mb-8">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-slate-300" />
            <input
              type="text"
              placeholder="Search honey jars, tags, or authors..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 glass-subtle rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 text-white placeholder-slate-300 focus:glass-medium"
            />
          </div>
          
          <div className="flex gap-4">
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}  
              className="px-4 py-2 glass-subtle rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 text-white focus:glass-medium"
            >
              <option value="all" className="bg-slate-800 text-white">All Categories</option>
              <option value="Research" className="bg-slate-800 text-white">Research</option>
              <option value="Security" className="bg-slate-800 text-white">Security</option>
              <option value="Healthcare" className="bg-slate-800 text-white">Healthcare</option>
              <option value="Legal" className="bg-slate-800 text-white">Legal</option>
              <option value="Technology" className="bg-slate-800 text-white">Technology</option>
              <option value="Finance" className="bg-slate-800 text-white">Finance</option>
            </select>

            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-4 py-2 glass-subtle rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 text-white focus:glass-medium"
            >
              <option value="all" className="bg-slate-800 text-white">All Types</option>
              <option value="free" className="bg-slate-800 text-white">Free</option>
              <option value="premium" className="bg-slate-800 text-white">Premium</option>
              <option value="enterprise" className="bg-slate-800 text-white">Enterprise</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-4 py-2 glass-subtle rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 text-white focus:glass-medium"
            >
              <option value="popular" className="bg-slate-800 text-white">Most Popular</option>
              <option value="rating" className="bg-slate-800 text-white">Highest Rated</option>
              <option value="price" className="bg-slate-800 text-white">Price</option>
              <option value="newest" className="bg-slate-800 text-white">Newest</option>
            </select>

            <div className="flex glass-subtle rounded-2xl">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-2 rounded-l-2xl transition-colors ${viewMode === 'grid' ? 'bg-blue-500 text-white' : 'text-slate-300 hover:text-white hover:bg-white/10'}`}
              >
                <Grid className="w-5 h-5" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`px-3 py-2 rounded-r-2xl transition-colors ${viewMode === 'list' ? 'bg-blue-500 text-white' : 'text-slate-300 hover:text-white hover:bg-white/10'}`}
              >
                <List className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Results Count */}
      <div className="mb-6">
        <p className="text-slate-400">
           Showing {sortedHoneyJars.length} of {HoneyJars.length} honey jars
          {searchTerm && ` for "${searchTerm}"`}
        </p>
      </div>

      {/* Honey Jars Grid/List */}
      <div className={`${viewMode === 'grid' 
        ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' 
        : 'space-y-4'
      }`}>
        {sortedHoneyJars.map((pot) => (
          <div
            key={pot.id}
            className={`standard-card rounded-2xl hover:glass-medium transition-all duration-300 cursor-pointer ${
              viewMode === 'list' ? 'flex gap-6 p-6' : 'p-6'
            }`}
            onClick={() => setSelectedPot(pot)}
          >
            {viewMode === 'grid' ? (
              <>
                {/* Grid View */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="text-2xl">{getCategoryIcon(pot.category)}</div>
                    <div>
                      <h3 className="font-semibold text-white">{pot.name}</h3>
                      <p className="text-sm text-slate-300">{pot.author}</p>
                    </div>
                  </div>
                  {pot.trending && <TrendingUp className="w-5 h-5 text-green-500" />}
                </div>

                <p className="text-slate-300 text-sm mb-4 line-clamp-3">{pot.description}</p>

                <div className="flex items-center gap-2 mb-4">
                  {pot.tags.slice(0, 3).map((tag, index) => (
                    <span key={index} className="px-2 py-1 glass-subtle text-slate-300 text-xs rounded-2xl">
                      {tag}
                    </span>
                  ))}
                  {pot.tags.length > 3 && (
                    <span className="text-xs text-slate-400">+{pot.tags.length - 3} more</span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                  <div className="flex items-center gap-1 text-slate-400">
                    <Download className="w-4 h-4" />
                    {pot.downloads.toLocaleString()}
                  </div>
                  <div className="flex items-center gap-1 text-slate-400">
                    <Star className="w-4 h-4 text-yellow-400" />
                    {pot.rating}
                  </div>
                  <div className="flex items-center gap-1 text-slate-400">
                    <Hexagon className="w-4 h-4" />
                    {pot.documents.toLocaleString()}
                  </div>
                  <div className="flex items-center gap-1 text-slate-400">
                    {pot.encryption !== 'none' ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                    {pot.encryption !== 'none' ? 'Encrypted' : 'Open'}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-white/10">
                  <span className={`px-3 py-1 text-sm font-medium rounded-full ${getTypeColor(pot.type)}`}>
                    {pot.type === 'free' ? 'FREE' : `$${pot.price}`}
                  </span>
                  <button className="bg-blue-600 text-white px-4 py-2 rounded-2xl hover:bg-blue-700 transition-colors text-sm">
                    {pot.type === 'free' ? 'Download' : 'Purchase'}
                  </button>
                </div>
              </>
            ) : (
              <>
                {/* List View */}
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <div className="text-2xl">{getCategoryIcon(pot.category)}</div>
                      <div>
                        <h3 className="font-semibold text-white">{pot.name}</h3>
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-slate-300">{pot.author}</span>
                          {pot.verified && <Shield className="w-4 h-4 text-blue-500" />}
                          {pot.trending && <TrendingUp className="w-4 h-4 text-green-500" />}
                        </div>
                      </div>
                    </div>
                    <span className={`px-3 py-1 text-sm font-medium rounded-full ${getTypeColor(pot.type)}`}>
                      {pot.type === 'free' ? 'FREE' : `$${pot.price}`}
                    </span>
                  </div>

                  <p className="text-slate-300 text-sm mb-3 line-clamp-2">{pot.description}</p>

                  <div className="flex items-center gap-6 text-sm text-slate-400 mb-3">
                    <div className="flex items-center gap-1">
                      <Star className="w-4 h-4 text-yellow-400" />
                      {pot.rating}
                    </div>
                    <div className="flex items-center gap-1">
                      <Download className="w-4 h-4" />
                      {pot.downloads.toLocaleString()}
                    </div>
                    <div className="flex items-center gap-1">
                      <Hexagon className="w-4 h-4" />
                      {pot.documents.toLocaleString()} docs
                    </div>
                    <div className="flex items-center gap-1">
                      {pot.encryption !== 'none' ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                      {pot.encryption !== 'none' ? 'Encrypted' : 'Open'}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {pot.tags.slice(0, 4).map((tag, index) => (
                      <span key={index} className="px-2 py-1 glass-subtle text-slate-300 text-xs rounded-2xl">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col justify-between">
                  <button className="bg-blue-600 text-white px-6 py-2 rounded-2xl hover:bg-blue-700 transition-colors mb-2">
                    {pot.type === 'free' ? 'Download' : 'Purchase'}
                  </button>
                  <button className="text-slate-400 hover:text-white text-sm flex items-center gap-1">
                    <Eye className="w-4 h-4" />
                    Preview
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
              </div>

              {/* Empty State */}
              {sortedHoneyJars.length === 0 && (
                <div className="text-center py-12">
                  <ShoppingBag className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-white mb-2">No templates found</h3>
                  <p className="text-slate-400 mb-4">Try adjusting your search or filter criteria</p>
                  <button className="bg-indigo-600 text-white px-6 py-2 rounded-2xl hover:bg-indigo-700 transition-colors">
                    Browse All Categories
                  </button>
                </div>
              )}
            </div>
          )}

          {selectedDemo === 'deploy' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Interactive Deployment Demo</h3>
              <p className="text-gray-400 mb-6">
                Experience how easy it is to deploy security templates with STING's one-click deployment system.
              </p>
              
              {/* Mock Deployment Interface */}
              <div className="glass-subtle rounded-2xl p-6 mb-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Template Selection */}
                  <div>
                    <h4 className="font-medium text-gray-100 mb-4">Selected Template</h4>
                    <div className="backdrop-blur-md bg-blue-500/20 border border-blue-400/30 rounded-2xl p-4">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="text-2xl">🛡️</div>
                        <div>
                          <h5 className="font-semibold text-gray-100">Enterprise Security Playbook</h5>
                          <p className="text-sm text-gray-300">CyberSec Solutions</p>
                        </div>
                        <Shield className="w-5 h-5 text-blue-400" />
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded p-2 text-center">
                          <p className="text-gray-300">Size</p>
                          <p className="font-semibold text-gray-100">800 MB</p>
                        </div>
                        <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded p-2 text-center">
                          <p className="text-gray-300">Rules</p>
                          <p className="font-semibold text-gray-100">1,200</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Deployment Options */}
                  <div>
                    <h4 className="font-medium text-gray-100 mb-4">Deployment Configuration</h4>
                    <div className="space-y-3">
                      <div className="glass-medium rounded-2xl p-3">
                        <label className="text-sm text-slate-300 mb-1 block">Target Environment</label>
                        <select className="w-full glass-subtle border border-white/20 rounded text-white p-2 text-sm">
                          <option>Production Cluster</option>
                          <option>Staging Environment</option>
                          <option>Development Sandbox</option>
                        </select>
                      </div>
                      <div className="glass-medium rounded-2xl p-3">
                        <label className="text-sm text-slate-300 mb-1 block">Integration</label>
                        <div className="flex items-center gap-2 text-sm">
                          <input type="checkbox" className="rounded" defaultChecked />
                          <span className="text-gray-200">Auto-configure SIEM integration</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm mt-1">
                          <input type="checkbox" className="rounded" defaultChecked />
                          <span className="text-gray-200">Enable threat intelligence feeds</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Deployment Button */}
                <div className="mt-6 text-center">
                  <button className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-8 py-3 rounded-2xl hover:from-green-600 hover:to-emerald-600 transition-all duration-300 font-semibold flex items-center gap-2 mx-auto">
                    <Play className="w-5 h-5" />
                    Deploy Template
                  </button>
                  <p className="text-xs text-gray-400 mt-2">Estimated deployment time: 2-3 minutes</p>
                </div>
              </div>

              {/* Deployment Benefits */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="backdrop-blur-md bg-green-500/20 border border-green-400/30 rounded-2xl p-4">
                  <h4 className="font-semibold text-green-200 mb-2 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5" />
                    Automated Configuration
                  </h4>
                  <ul className="text-sm text-green-100 space-y-1">
                    <li>• Zero manual configuration required</li>
                    <li>• Automatic network discovery</li>
                    <li>• SIEM integration setup</li>
                    <li>• Baseline security policies</li>
                  </ul>
                </div>
                <div className="backdrop-blur-md bg-blue-500/20 border border-blue-400/30 rounded-2xl p-4">
                  <h4 className="font-semibold text-blue-200 mb-2 flex items-center gap-2">
                    <Zap className="w-5 h-5" />
                    Enterprise Ready
                  </h4>
                  <ul className="text-sm text-blue-100 space-y-1">
                    <li>• Compliance-tested configurations</li>
                    <li>• Role-based access controls</li>
                    <li>• Audit logging enabled</li>
                    <li>• High availability setup</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {selectedDemo === 'analytics' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Marketplace Analytics</h3>
              
              {/* Mock Analytics Dashboard */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="glass-subtle rounded-2xl p-6">
                  <h4 className="font-medium text-white mb-4">Popular Templates</h4>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-300">AI Research Papers</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-slate-600 rounded-full h-2">
                          <div className="bg-blue-400 h-2 rounded-full" style={{width: '85%'}}></div>
                        </div>
                        <span className="text-sm font-medium text-white">2,341</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-300">Dev Best Practices</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-slate-600 rounded-full h-2">
                          <div className="bg-green-400 h-2 rounded-full" style={{width: '72%'}}></div>
                        </div>
                        <span className="text-sm font-medium text-white">1,876</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-300">Legal Templates</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-slate-600 rounded-full h-2">
                          <div className="bg-yellow-400 h-2 rounded-full" style={{width: '43%'}}></div>
                        </div>
                        <span className="text-sm font-medium text-white">445</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="glass-subtle rounded-2xl p-6">
                  <h4 className="font-medium text-white mb-4">Revenue Metrics</h4>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-300">Monthly Revenue</span>
                      <span className="text-2xl font-bold text-white">$24,567</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-300">Active Subscriptions</span>
                      <span className="text-lg font-semibold text-green-300">+12.5%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-300">Avg. Template Price</span>
                      <span className="text-lg font-medium text-white">$299</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 backdrop-blur-md bg-indigo-500/20 border border-indigo-400/30 rounded-2xl p-4">
                <div className="flex items-start gap-3">
                  <TrendingUp className="w-5 h-5 text-indigo-300 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-indigo-200 mb-1">Analytics Benefits</h4>
                    <p className="text-sm text-indigo-100">
                      Track template performance, user engagement, and revenue metrics. Identify trending 
                      security patterns and optimize your marketplace strategy with detailed analytics.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* CTA Section */}
      <div className="mt-8 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-8 text-center text-white">
        <h3 className="text-2xl font-bold mb-2">Ready to Deploy Enterprise Security?</h3>
        <p className="text-white/90 mb-6 max-w-2xl mx-auto">
          Access verified security templates, honeypot configurations, and detection rules from our 
          enterprise marketplace. Transform your security posture with one-click deployments.
        </p>
        <div className="flex gap-4 justify-center">
          <button className="px-6 py-3 bg-white text-indigo-600 rounded-2xl hover:bg-gray-100 transition-colors font-semibold">
            Schedule Demo
          </button>
          <button className="px-6 py-3 bg-indigo-700 text-white rounded-2xl hover:bg-indigo-800 transition-colors font-semibold">
            Contact Sales
          </button>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedPot && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="standard-card rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="text-3xl">{getCategoryIcon(selectedPot.category)}</div>
                  <div>
                    <h2 className="text-2xl font-bold text-white">{selectedPot.name}</h2>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-300">{selectedPot.author}</span>
                      {selectedPot.verified && <Shield className="w-5 h-5 text-blue-500" />}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedPot(null)}
                  className="text-slate-400 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2">
                  <p className="text-slate-300 mb-6">{selectedPot.description}</p>
                  
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-3">Preview</h3>
                    <div className="glass-subtle p-4 rounded-2xl">
                      <p className="text-slate-300">{selectedPot.preview}</p>
                    </div>
                  </div>

                  <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-3">Tags</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedPot.tags.map((tag, index) => (
                        <span key={index} className="px-3 py-1 glass-medium text-blue-300 text-sm rounded-2xl">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div>
                  <div className="glass-subtle rounded-2xl p-6 mb-6">
                    <div className="text-center mb-4">
                      <span className={`px-4 py-2 text-lg font-semibold rounded-full ${getTypeColor(selectedPot.type)}`}>
                        {selectedPot.type === 'free' ? 'FREE' : `$${selectedPot.price}`}
                      </span>
                    </div>
                    
                    <div className="space-y-3 mb-6">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Rating:</span>
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 text-yellow-500" />
                          <span className="font-medium text-white">{selectedPot.rating}</span>
                        </div>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Downloads:</span>
                        <span className="font-medium text-white">{selectedPot.downloads.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Size:</span>
                        <span className="font-medium text-white">{selectedPot.size}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Documents:</span>
                        <span className="font-medium text-white">{selectedPot.documents.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Embeddings:</span>
                        <span className="font-medium text-white">{selectedPot.embeddings.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Encryption:</span>
                        <span className="font-medium text-white">{selectedPot.encryption}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">License:</span>
                        <span className="font-medium text-white">{selectedPot.license}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Updated:</span>
                        <span className="font-medium text-white">{selectedPot.lastUpdated}</span>
                      </div>
                    </div>

                    <button className="w-full bg-blue-600 text-white py-3 px-4 rounded-2xl hover:bg-blue-700 transition-colors mb-3">
                      {selectedPot.type === 'free' ? 'Download Now' : 'Purchase & Download'}
                    </button>
                    
                    <div className="grid grid-cols-2 gap-2">
                      <button className="text-slate-300 hover:text-white py-2 px-3 border border-white/20 rounded-2xl text-sm flex items-center justify-center gap-1 hover:border-white/40">
                        <Heart className="w-4 h-4" />
                        Favorite
                      </button>
                      <button className="text-slate-300 hover:text-white py-2 px-3 border border-white/20 rounded-2xl text-sm flex items-center justify-center gap-1 hover:border-white/40">
                        <MessageSquare className="w-4 h-4" />
                        Review
                      </button>
                    </div>
                  </div>

                  <div className="text-center">
                    <button className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1 mx-auto">
                      <ExternalLink className="w-4 h-4" />
                      View Publisher Profile
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      </div>
    </div>
  );
};

export default MarketplacePage;