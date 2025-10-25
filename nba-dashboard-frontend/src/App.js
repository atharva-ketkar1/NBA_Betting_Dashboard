import React, { useState, useEffect, useMemo } from 'react';
import { Search, TrendingUp, AlertCircle, Filter, DollarSign, BarChart3, Activity, ArrowUpDown, Clock, Zap, Star, RefreshCw } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:5000/api';

const NBAPropsDashboard = () => {
  const [activeTab, setActiveTab] = useState('all');
  // Start with an empty date
  const [selectedDate, setSelectedDate] = useState(''); 
  const [allProps, setAllProps] = useState([]);
  const [arbitrage, setArbitrage] = useState([]);
  const [discrepancies, setDiscrepancies] = useState([]);
  const [bestOdds, setBestOdds] = useState([]);
  // Start loading as true since we're fetching the date
  const [loading, setLoading] = useState(true); 
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPropType, setSelectedPropType] = useState('all');
  const [sortBy, setSortBy] = useState('profit');
  const [showFavorites, setShowFavorites] = useState(false);
  const [favorites, setFavorites] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [error, setError] = useState(null);

  // NEW: Effect to fetch today's date on initial load
  useEffect(() => {
    fetch(`${API_BASE}/today`)
      .then(res => {
        if (!res.ok) {
          throw new Error('API not responding');
        }
        return res.json();
      })
      .then(data => {
        if (data.date) {
          setSelectedDate(data.date);
        } else {
          // Fallback if API response is weird
          throw new Error('Invalid date from API');
        }
      })
      .catch(err => {
        console.error('Error fetching today\'s date:', err);
        setError('Could not connect to API. Is it running?');
        // Fallback to browser's date
        setSelectedDate(new Date().toISOString().split('T')[0]);
      });
    
    const savedFavorites = localStorage.getItem('favorites');
    if (savedFavorites) {
      setFavorites(JSON.parse(savedFavorites));
    }
  }, []); // Runs only once on mount

  // MODIFIED: This effect now waits for selectedDate to be set
  useEffect(() => {
    // Don't fetch data until we have a date
    if (!selectedDate) {
      return; 
    }
    fetchAllData();
  }, [selectedDate]);

  useEffect(() => {
    if (autoRefresh && selectedDate) {
      const interval = setInterval(fetchAllData, 60000); // Refresh every minute
      return () => clearInterval(interval);
    }
  }, [autoRefresh, selectedDate]);

  const fetchAllData = async () => {
    setLoading(true);
    setError(null); // Clear previous errors
    try {
      const [propsRes, arbRes, discRes, oddsRes] = await Promise.all([
        fetch(`${API_BASE}/props/${selectedDate}`),
        fetch(`${API_BASE}/arbitrage/${selectedDate}`),
        fetch(`${API_BASE}/discrepancies/${selectedDate}`),
        fetch(`${API_BASE}/best-odds/${selectedDate}`)
      ]);

      // Check for bad responses
      if (!propsRes.ok || !arbRes.ok || !discRes.ok || !oddsRes.ok) {
        throw new Error('One or more API endpoints failed');
      }

      const propsData = await propsRes.json();
      const arbData = await arbRes.json();
      const discData = await discRes.json();
      const oddsData = await oddsRes.json();

      setAllProps(propsData);
      setArbitrage(arbData);
      setDiscrepancies(discData);
      setBestOdds(oddsData);
    } catch (error) {
      console.error('Error fetching data:', error);
      setError(`Failed to fetch prop data. (${error.message})`);
      setAllProps([]);
      setArbitrage([]);
      setDiscrepancies([]);
      setBestOdds([]);
    }
    setLoading(false);
  };

  const toggleFavorite = (player, propType) => {
    const key = `${player}-${propType}`;
    const newFavorites = favorites.includes(key)
      ? favorites.filter(f => f !== key)
      : [...favorites, key];
    setFavorites(newFavorites);
    localStorage.setItem('favorites', JSON.stringify(newFavorites));
  };

  const isFavorite = (player, propType) => {
    return favorites.includes(`${player}-${propType}`);
  };

  // Group props by player and prop type for comparison view
  const groupedProps = useMemo(() => {
    const grouped = {};
    allProps.forEach(prop => {
      const key = `${prop.player}-${prop.prop_type}`;
      if (!grouped[key]) {
        grouped[key] = {
          player: prop.player,
          propType: prop.prop_type,
          game: prop.game,
          team: prop.team,
          books: {}
        };
      }
      grouped[key].books[prop.sportsbook.toLowerCase()] = {
        line: prop.line,
        overOdds: prop.over_odds,
        underOdds: prop.under_odds
      };
    });
    return Object.values(grouped);
  }, [allProps]);

  // Filter and sort data
  const filteredData = useMemo(() => {
    let data = activeTab === 'all' ? groupedProps :
                activeTab === 'arbitrage' ? arbitrage :
                activeTab === 'discrepancies' ? discrepancies :
                bestOdds;

    // Search filter
    if (searchQuery) {
      data = data.filter(item => 
        item.player.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Prop type filter
    if (selectedPropType !== 'all') {
      data = data.filter(item => {
        const propType = item.propType || item.prop_type;
        return propType === selectedPropType;
      });
    }

    // Favorites filter
    if (showFavorites) {
      data = data.filter(item => {
        const propType = item.propType || item.prop_type;
        return isFavorite(item.player, propType);
      });
    }

    // Sort
    if (activeTab === 'arbitrage') {
      data = [...data].sort((a, b) => 
        sortBy === 'profit' ? b.profit_percent - a.profit_percent :
        a.player.localeCompare(b.player)
      );
    } else if (activeTab === 'best-odds') {
      data = [...data].sort((a, b) => 
        sortBy === 'profit' ? b.odds_difference - a.odds_difference :
        a.player.localeCompare(b.player)
      );
    } else if (activeTab === 'discrepancies') {
      data = [...data].sort((a, b) => 
        sortBy === 'profit' ? b.line_difference - a.line_difference :
        a.player.localeCompare(b.player)
      );
    }

    return data;
  }, [activeTab, groupedProps, arbitrage, discrepancies, bestOdds, searchQuery, selectedPropType, sortBy, showFavorites, favorites]);

  const propTypes = useMemo(() => {
    const types = new Set();
    allProps.forEach(prop => types.add(prop.prop_type));
    return ['all', ...Array.from(types).sort()];
  }, [allProps]);

  const formatOdds = (odds) => {
    if (odds === null || odds === undefined) return '-';
    return odds > 0 ? `+${odds}` : odds;
  };

  const getOddsColor = (odds) => {
    if (odds === null || odds === undefined) return 'text-gray-400';
    return odds > 0 ? 'text-green-400' : 'text-red-400';
  };

  const calculateStakes = (overOdds, underOdds, totalStake = 100) => {
    if (overOdds === null || underOdds === null) return { stakeOver: 0, stakeUnder: 0, profit: 0 };
    const decOver = overOdds > 0 ? (overOdds / 100) + 1 : (100 / Math.abs(overOdds)) + 1;
    const decUnder = underOdds > 0 ? (underOdds / 100) + 1 : (100 / Math.abs(underOdds)) + 1;
    
    const stakeOver = totalStake / (1 + (decOver / decUnder));
    const stakeUnder = totalStake - stakeOver;
    const profit = (stakeOver * decOver) - totalStake;
    
    return { stakeOver, stakeUnder, profit };
  };

  // MODIFIED: Handle loading state while date is being fetched
  if (loading && !selectedDate) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-500 mx-auto"></div>
          <p className="text-white mt-4 text-lg">Connecting to API...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white font-inter">
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-md border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-orange-500 to-purple-600 p-2 rounded-xl">
                <Activity className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-orange-400 to-purple-400 bg-clip-text text-transparent">
                  NBA Props Dashboard
                </h1>
                <p className="text-sm text-gray-400">Real-time betting intelligence</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-slate-800 border border-purple-500/30 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
              />
              <button
                onClick={fetchAllData}
                disabled={loading}
                className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg flex items-center gap-2 transition-all disabled:opacity-50"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                {loading ? 'Loading...' : 'Refresh'}
              </button>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
                  autoRefresh ? 'bg-green-600 hover:bg-green-700' : 'bg-slate-700 hover:bg-slate-600'
                }`}
              >
                <Clock className="w-4 h-4" />
                Auto {autoRefresh ? 'On' : 'Off'}
              </button>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="bg-gradient-to-br from-green-500/20 to-green-600/20 border border-green-500/30 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-green-400 mb-1">Arbitrage</p>
                  <p className="text-2xl font-bold">{arbitrage.length}</p>
                </div>
                <Zap className="w-8 h-8 text-green-400" />
              </div>
            </div>
            <div className="bg-gradient-to-br from-orange-500/20 to-orange-600/20 border border-orange-500/30 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-orange-400 mb-1">Line Mismatches</p>
                  <p className="text-2xl font-bold">{discrepancies.length}</p>
                </div>
                <TrendingUp className="w-8 h-8 text-orange-400" />
              </div>
            </div>
            <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/20 border border-blue-500/30 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-blue-400 mb-1">Best Odds</p>
                  <p className="text-2xl font-bold">{bestOdds.length}</p>
                </div>
                <DollarSign className="w-8 h-8 text-blue-400" />
              </div>
            </div>
            <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/20 border border-purple-500/30 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-purple-400 mb-1">Total Props</p>
                  <p className="text-2xl font-bold">{allProps.length}</p>
                </div>
                <BarChart3 className="w-8 h-8 text-purple-400" />
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {[
              { id: 'arbitrage', label: 'Arbitrage', icon: Zap, color: 'green' },
              { id: 'discrepancies', label: 'Line Mismatches', icon: TrendingUp, color: 'orange' },
              { id: 'best-odds', label: 'Best Odds', icon: DollarSign, color: 'blue' },
              { id: 'all', label: 'All Props', icon: BarChart3, color: 'purple' }
            ].map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all whitespace-nowrap ${
                    activeTab === tab.id
                      ? `bg-${tab.color}-600 shadow-lg shadow-${tab.color}-500/50`
                      : 'bg-slate-800/50 hover:bg-slate-700/50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* Filters */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/20 rounded-lg p-4 mb-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search player..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-900 border border-purple-500/30 rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
              />
            </div>

            <select
              value={selectedPropType}
              onChange={(e) => setSelectedPropType(e.target.value)}
              className="bg-slate-900 border border-purple-500/30 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
            >
              {propTypes.map(type => (
                <option key={type} value={type}>
                  {type === 'all' ? 'All Prop Types' : type.toUpperCase()}
                </option>
              ))}
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-slate-900 border border-purple-500/30 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-purple-500 outline-none"
            >
              <option value="profit">Sort by Value</option>
              <option value="player">Sort by Player</option>
            </select>

            <button
              onClick={() => setShowFavorites(!showFavorites)}
              className={`flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition-all ${
                showFavorites
                  ? 'bg-yellow-600 hover:bg-yellow-700'
                  : 'bg-slate-900 hover:bg-slate-700 border border-purple-500/30'
              }`}
            >
              <Star className={`w-4 h-4 ${showFavorites ? 'fill-current' : ''}`} />
              Favorites
            </button>
          </div>
        </div>
        
        {/* NEW: Error Message Display */}
        {error && (
          <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 text-center mb-4">
            <div className="flex items-center justify-center gap-3">
              <AlertCircle className="w-8 h-8 text-red-400" />
              <div>
                <h3 className="text-xl font-semibold text-red-400">Connection Error</h3>
                <p className="text-red-300">{error}</p>
                <p className="text-red-300 text-sm">Please ensure your Python API server is running on `http://localhost:5000`</p>
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="space-y-3">
          {loading && filteredData.length === 0 ? (
             <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/20 rounded-lg p-12 text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-500 mx-auto mb-4"></div>
              <h3 className="text-xl font-semibold mb-2">Loading Prop Data...</h3>
              <p className="text-gray-400">Fetching data for {selectedDate}</p>
            </div>
          ) : !loading && filteredData.length === 0 ? (
            <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/20 rounded-lg p-12 text-center">
              <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">No Results Found</h3>
              <p className="text-gray-400">Try adjusting your filters or search query.</p>
              <p className="text-gray-500 text-sm mt-2">
                (Or, try running your scraper scripts to populate the database for {selectedDate})
              </p>
            </div>
          ) : activeTab === 'arbitrage' ? (
            // Arbitrage View
            filteredData.map((arb, idx) => {
              const stakes = calculateStakes(arb.over_odds, arb.under_odds);
              return (
                <div key={idx} className="bg-gradient-to-br from-green-500/10 to-green-600/10 border-2 border-green-500/30 rounded-xl p-4 hover:border-green-500/50 transition-all">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <button
                          onClick={() => toggleFavorite(arb.player, arb.prop_type)}
                          className="text-yellow-400 hover:scale-110 transition-transform"
                        >
                          <Star className={`w-5 h-5 ${isFavorite(arb.player, arb.prop_type) ? 'fill-current' : ''}`} />
                        </button>
                        <h3 className="text-xl font-bold capitalize">{arb.player}</h3>
                        <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-xs font-semibold">
                          {arb.prop_type.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-400 mb-1">{arb.game}</p>
                      <p className="text-xs text-gray-500">{arb.team}</p>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-2 mb-1">
                        <Zap className="w-5 h-5 text-green-400" />
                        <span className="text-2xl font-bold text-green-400">
                          {arb.profit_percent.toFixed(2)}%
                        </span>
                      </div>
                      <p className="text-xs text-gray-400">Guaranteed Profit</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-slate-900/50 rounded-lg p-3 border border-purple-500/20">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-gray-400">BET OVER {arb.line}</span>
                        <span className="text-xs font-semibold text-purple-400">{arb.bet_over}</span>
                      </div>
                      <p className={`text-2xl font-bold ${getOddsColor(arb.over_odds)}`}>
                        {formatOdds(arb.over_odds)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">Stake: ${stakes.stakeOver.toFixed(2)}</p>
                    </div>

                    <div className="bg-slate-900/50 rounded-lg p-3 border border-purple-500/20">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-gray-400">BET UNDER {arb.line}</span>
                        <span className="text-xs font-semibold text-purple-400">{arb.bet_under}</span>
                      </div>
                      <p className={`text-2xl font-bold ${getOddsColor(arb.under_odds)}`}>
                        {formatOdds(arb.under_odds)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">Stake: ${stakes.stakeUnder.toFixed(2)}</p>
                    </div>
                  </div>

                  <div className="bg-green-500/20 border border-green-500/30 rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-green-400">Total Stake: $100</span>
                      <span className="text-lg font-bold text-green-400">Profit: ${stakes.profit.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              );
            })
          ) : activeTab === 'discrepancies' ? (
            // Line Discrepancies View
            filteredData.map((disc, idx) => (
              <div key={idx} className="bg-gradient-to-br from-orange-500/10 to-orange-600/10 border-2 border-orange-500/30 rounded-xl p-4 hover:border-orange-500/50 transition-all">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <button
                        onClick={() => toggleFavorite(disc.player, disc.prop_type)}
                        className="text-yellow-400 hover:scale-110 transition-transform"
                      >
                        <Star className={`w-5 h-5 ${isFavorite(disc.player, disc.prop_type) ? 'fill-current' : ''}`} />
                      </button>
                      <h3 className="text-xl font-bold capitalize">{disc.player}</h3>
                      <span className="bg-orange-500/20 text-orange-400 px-3 py-1 rounded-full text-xs font-semibold">
                        {disc.prop_type.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400">{disc.game}</p>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-2 mb-1">
                      <TrendingUp className="w-5 h-5 text-orange-400" />
                      <span className="text-2xl font-bold text-orange-400">
                        {disc.line_difference.toFixed(1)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">Line Difference</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-slate-900/50 rounded-lg p-3 border border-purple-500/20">
                    <p className="text-xs text-gray-400 mb-2">DraftKings</p>
                    <p className="text-3xl font-bold text-purple-400 mb-2">{disc.dk_line}</p>
                    <div className="flex items-center justify-between text-xs">
                      <span className={getOddsColor(disc.dk_over)}>O: {formatOdds(disc.dk_over)}</span>
                      <span className={getOddsColor(disc.dk_under)}>U: {formatOdds(disc.dk_under)}</span>
                    </div>
                  </div>

                  <div className="bg-slate-900/50 rounded-lg p-3 border border-purple-500/20">
                    <p className="text-xs text-gray-400 mb-2">FanDuel</p>
                    <p className="text-3xl font-bold text-blue-400 mb-2">{disc.fd_line}</p>
                    <div className="flex items-center justify-between text-xs">
                      <span className={getOddsColor(disc.fd_over)}>O: {formatOdds(disc.fd_over)}</span>
                      <span className={getOddsColor(disc.fd_under)}>U: {formatOdds(disc.fd_under)}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 bg-orange-500/20 border border-orange-500/30 rounded-lg p-2">
                  <p className="text-xs text-orange-400">
                    💡 {disc.dk_line < disc.fd_line 
                      ? `Consider DK OVER ${disc.dk_line} or FD UNDER ${disc.fd_line}`
                      : `Consider FD OVER ${disc.fd_line} or DK UNDER ${disc.dk_line}`}
                  </p>
                </div>
              </div>
            ))
          ) : activeTab === 'best-odds' ? (
            // Best Odds View
            filteredData.map((odds, idx) => (
              <div key={idx} className="bg-gradient-to-br from-blue-500/10 to-blue-600/10 border-2 border-blue-500/30 rounded-xl p-4 hover:border-blue-500/50 transition-all">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <button
                        onClick={() => toggleFavorite(odds.player, odds.prop_type)}
                        className="text-yellow-400 hover:scale-110 transition-transform"
                      >
                        <Star className={`w-5 h-5 ${isFavorite(odds.player, odds.prop_type) ? 'fill-current' : ''}`} />
                      </button>
                      <h3 className="text-xl font-bold capitalize">{odds.player}</h3>
                      <span className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded-full text-xs font-semibold">
                        {odds.prop_type.toUpperCase()} {odds.side}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400">{odds.game}</p>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-2 mb-1">
                      <DollarSign className="w-5 h-5 text-blue-400" />
                      <span className="text-2xl font-bold text-blue-400">
                        +{odds.odds_difference}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">Better Odds</p>
                  </div>
                </div>

                <div className="bg-slate-900/50 rounded-lg p-4 border border-purple-500/20">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-gray-400">Line: {odds.line}</span>
                    <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded">
                      {odds.side}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <p className="text-xs text-gray-400 mb-1">✅ {odds.best_book}</p>
                      <p className={`text-3xl font-bold ${getOddsColor(odds.best_odds)}`}>
                        {formatOdds(odds.best_odds)}
                      </p>
                    </div>
                    <div className="text-center opacity-60">
                      <p className="text-xs text-gray-400 mb-1">Other</p>
                      <p className={`text-xl font-bold ${getOddsColor(odds.other_odds)}`}>
                        {formatOdds(odds.other_odds)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            // All Props View
            filteredData.map((prop, idx) => {
              const hasBothBooks = prop.books.draftkings && prop.books.fanduel;
              const dkLine = prop.books.draftkings?.line;
              const fdLine = prop.books.fanduel?.line;
              const lineMismatch = hasBothBooks && dkLine !== fdLine;

              return (
                <div key={idx} className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/20 rounded-xl p-4 hover:border-purple-500/50 transition-all">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <button
                          onClick={() => toggleFavorite(prop.player, prop.propType)}
                          className="text-yellow-400 hover:scale-110 transition-transform"
                        >
                          <Star className={`w-5 h-5 ${isFavorite(prop.player, prop.propType) ? 'fill-current' : ''}`} />
                        </button>
                        <h3 className="text-lg font-bold capitalize">{prop.player}</h3>
                        <span className="bg-purple-500/20 text-purple-400 px-2 py-1 rounded text-xs font-semibold">
                          {prop.propType.toUpperCase()}
                        </span>
                        {lineMismatch && (
                          <span className="bg-orange-500/20 text-orange-400 px-2 py-1 rounded text-xs font-semibold flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            LINE MISMATCH
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-400">{prop.game}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* DraftKings Card */}
                    <div className={`bg-slate-900/50 rounded-lg p-3 border ${prop.books.draftkings ? 'border-purple-500/20' : 'border-slate-700/50 opacity-50'}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-purple-400">DraftKings</span>
                        <span className="text-lg font-bold text-white">{prop.books.draftkings?.line ?? '-'}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="text-center bg-slate-800/50 rounded p-2">
                          <p className="text-xs text-gray-400 mb-1">Over</p>
                          <p className={`text-lg font-bold ${getOddsColor(prop.books.draftkings?.overOdds)}`}>
                            {formatOdds(prop.books.draftkings?.overOdds)}
                          </p>
                        </div>
                        <div className="text-center bg-slate-800/50 rounded p-2">
                          <p className="text-xs text-gray-400 mb-1">Under</p>
                          <p className={`text-lg font-bold ${getOddsColor(prop.books.draftkings?.underOdds)}`}>
                            {formatOdds(prop.books.draftkings?.underOdds)}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* FanDuel Card */}
                    <div className={`bg-slate-900/50 rounded-lg p-3 border ${prop.books.fanduel ? 'border-blue-500/20' : 'border-slate-700/50 opacity-50'}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-blue-400">FanDuel</span>
                        <span className="text-lg font-bold text-white">{prop.books.fanduel?.line ?? '-'}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="text-center bg-slate-800/50 rounded p-2">
                          <p className="text-xs text-gray-400 mb-1">Over</p>
                          <p className={`text-lg font-bold ${getOddsColor(prop.books.fanduel?.overOdds)}`}>
                            {formatOdds(prop.books.fanduel?.overOdds)}
                          </p>
                        </div>
                        <div className="text-center bg-slate-800/50 rounded p-2">
                          <p className="text-xs text-gray-400 mb-1">Under</p>
                          <p className={`text-lg font-bold ${getOddsColor(prop.books.fanduel?.underOdds)}`}>
                            {formatOdds(prop.books.fanduel?.underOdds)}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {hasBothBooks && (
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                      {(() => {
                        const dkOver = prop.books.draftkings.overOdds;
                        const fdOver = prop.books.fanduel.overOdds;
                        const dkUnder = prop.books.draftkings.underOdds;
                        const fdUnder = prop.books.fanduel.underOdds;
                        
                        // Check if odds exist before comparing
                        const overDiff = (dkOver && fdOver) ? Math.abs(dkOver - fdOver) : 0;
                        const underDiff = (dkUnder && fdUnder) ? Math.abs(dkUnder - fdUnder) : 0;

                        const bestOverBook = (dkOver && fdOver) ? (dkOver > fdOver ? 'DK' : 'FD') : null;
                        const bestUnderBook = (dkUnder && fdUnder) ? (dkUnder > fdUnder ? 'DK' : 'FD') : null;

                        return (
                          <>
                            {overDiff >= 5 && bestOverBook && (
                              <div className="bg-green-500/10 border border-green-500/30 rounded px-2 py-1">
                                <span className="text-green-400">
                                  ⬆ Best Over on {bestOverBook === 'DK' ? 'DraftKings' : 'FanDuel'} (+{overDiff})
                                </span>
                              </div>
                            )}
                            {underDiff >= 5 && bestUnderBook && (
                              <div className="bg-blue-500/10 border border-blue-500/30 rounded px-2 py-1">
                                <span className="text-blue-400">
                                  ⬇ Best Under on {bestUnderBook === 'DK' ? 'DraftKings' : 'FanDuel'} (+{underDiff})
                                </span>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer Stats */}
        <div className="mt-8 bg-slate-800/50 backdrop-blur-sm border border-purple-500/20 rounded-lg p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-purple-400">{filteredData.length}</p>
              <p className="text-xs text-gray-400 mt-1">Displayed Results</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-400">{favorites.length}</p>
              <p className="text-xs text-gray-400 mt-1">Favorites</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-orange-400">
                {arbitrage.reduce((sum, arb) => sum + arb.profit_percent, 0).toFixed(2)}%
              </p>
              <p className="text-xs text-gray-400 mt-1">Total Arb Profit</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-400">
                {new Set(allProps.map(p => p.player)).size}
              </p>
              <p className="text-xs text-gray-400 mt-1">Unique Players</p>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="mt-4 bg-slate-800/30 backdrop-blur-sm border border-purple-500/10 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-400 mb-3">Legend & Tips</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="flex items-start gap-2">
              <Zap className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-green-400 font-semibold">Arbitrage</p>
                <p className="text-gray-400">Guaranteed profit by betting both sides across different books</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <TrendingUp className="w-4 h-4 text-orange-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-orange-400 font-semibold">Line Mismatch</p>
                <p className="text-gray-400">Different lines suggest value - bet the more favorable side</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <DollarSign className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-blue-400 font-semibold">Best Odds</p>
                <p className="text-gray-400">Same line, better odds - always bet at the better book</p>
              </div>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-purple-500/10">
            <p className="text-gray-500 text-xs">
              💡 <span className="text-gray-400">Pro Tip:</span> Green odds (+150) mean you profit that amount on $100 bet. 
              Red odds (-150) mean you need to bet that amount to profit $100. Always shop for the best lines!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NBAPropsDashboard;
