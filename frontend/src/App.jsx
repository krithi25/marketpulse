import { useEffect, useState } from "react";
import axios from "axios";
import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, CircleHelp, Plus, RefreshCw, Search, Trash2, X } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "";
const storedToken = localStorage.getItem("marketpulse_token");
if (storedToken) {
  axios.defaults.headers.common.Authorization = `Bearer ${storedToken}`;
}

function App() {
  const [token, setToken] = useState(storedToken);
  const [user, setUser] = useState(null);
  const [watchlistId, setWatchlistId] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [changes, setChanges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const [showAddModal, setShowAddModal] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [adding, setAdding] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [stockSuggestions, setStockSuggestions] = useState([]);
  const [searchingStocks, setSearchingStocks] = useState(false);
  const [portfolio, setPortfolio] = useState(null);
  const [showPortfolioModal, setShowPortfolioModal] = useState(false);
  const [savingHolding, setSavingHolding] = useState(false);

  const handleAuthenticated = (response) => {
    const accessToken = response.data.access_token;
    localStorage.setItem("marketpulse_token", accessToken);
    axios.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
    setToken(accessToken);
    setUser(response.data.user);
    setWatchlistId(response.data.watchlist.id);
  };

  const handleLogout = () => {
    localStorage.removeItem("marketpulse_token");
    delete axios.defaults.headers.common.Authorization;
    setToken(null);
    setUser(null);
    setWatchlistId(null);
    setDashboard(null);
    setPortfolio(null);
  };

  const fetchWatchlist = async () => {
    try {
      setError("");

      // Get changes BEFORE recording the new visit
      const changesResponse = await axios.get(
        `${API_URL}/api/watchlist/${watchlistId}/since-last-visit`
      );

      setChanges(changesResponse.data.changes || []);

      const response = await axios.get(`${API_URL}/api/dashboard/${watchlistId}`);
      setDashboard(response.data);
      const portfolioResponse = await axios.get(`${API_URL}/api/portfolio/${watchlistId}`);
      setPortfolio(portfolioResponse.data);

      // Record this visit
      await axios.post(
        `${API_URL}/api/watchlist/${watchlistId}/visit`
      );

    } catch (err) {
      console.error(err);
      setError("Unable to load market data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!token) return;
    axios.get(`${API_URL}/api/auth/me`).then((response) => {
      setUser(response.data.user);
      setWatchlistId(response.data.watchlist?.id || null);
    }).catch(handleLogout);
  }, [token]);

  useEffect(() => {
    if (!token || !watchlistId) return undefined;
    const refreshTimer = window.setInterval(fetchWatchlist, 60000);
    return () => window.clearInterval(refreshTimer);
  }, [token, watchlistId]);

  useEffect(() => {
    if (token && watchlistId) fetchWatchlist();
  }, [token, watchlistId]);

  useEffect(() => {
    const query = symbol.trim();
    if (query.length < 2 || !showAddModal) {
      setStockSuggestions([]);
      return undefined;
    }

    const searchTimer = window.setTimeout(async () => {
      try {
        setSearchingStocks(true);
        const response = await axios.get(`${API_URL}/api/market/search`, {
          params: { query },
        });
        setStockSuggestions(response.data.results || []);
      } catch (err) {
        console.error(err);
        setStockSuggestions([]);
      } finally {
        setSearchingStocks(false);
      }
    }, 350);

    return () => window.clearTimeout(searchTimer);
  }, [symbol, showAddModal]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchWatchlist();
  };

  const handleAddHolding = async (event, holdingData) => {
    event.preventDefault();
    try {
      setSavingHolding(true);
      await axios.post(`${API_URL}/api/portfolio/${watchlistId}/holdings`, {
        symbol: holdingData.symbol.trim().toUpperCase(),
        quantity: Number(holdingData.quantity),
        buy_price: Number(holdingData.buyPrice),
      });
      setShowPortfolioModal(false);
      await fetchWatchlist();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to add portfolio holding.");
    } finally {
      setSavingHolding(false);
    }
  };

  const handleRemoveHolding = async (symbolToRemove) => {
    if (!window.confirm(`Remove ${symbolToRemove} from your portfolio?`)) return;
    await axios.delete(`${API_URL}/api/portfolio/${watchlistId}/holdings/${symbolToRemove}`);
    await fetchWatchlist();
  };

  if (!token) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  // ADD STOCK
  const handleAddStock = async (e) => {
    e.preventDefault();

    const cleanSymbol = symbol.trim().toUpperCase();

    if (!cleanSymbol) {
      return;
    }

    try {
      setAdding(true);
      setError("");

      await axios.post(
        `${API_URL}/api/watchlist/${watchlistId}/stocks`,
        null,
        {
          params: {
            symbol: cleanSymbol,
          },
        }
      );

      setSymbol("");
      setStockSuggestions([]);
      setShowAddModal(false);

      // Reload dashboard
      await fetchWatchlist();

    } catch (err) {
      console.error(err);

      if (err.response?.status === 409) {
        setError(`${cleanSymbol} is already in your watchlist.`);
      } else if (err.response?.status === 422) {
        setError(err.response.data.detail || `${cleanSymbol} is not supported by the market data provider.`);
      } else {
        setError(`Unable to add ${cleanSymbol}.`);
      }
    } finally {
      setAdding(false);
    }
  };

  const normalizedSymbol = symbol.trim().toUpperCase();
  const alreadyTracked = dashboard?.stocks?.some(
    (stock) => stock.symbol === normalizedSymbol
  );

  // DELETE STOCK
  const handleDeleteStock = async (stockSymbol) => {
    const confirmed = window.confirm(
      `Remove ${stockSymbol} from your watchlist?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");

      await axios.delete(
        `${API_URL}/api/watchlist/${watchlistId}/stocks/${stockSymbol}`
      );

      await fetchWatchlist();

    } catch (err) {
      console.error(err);
      setError(`Unable to remove ${stockSymbol}.`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <Activity className="mx-auto mb-4 animate-pulse" size={38} />
          <p className="text-slate-600 font-medium">
            Loading MarketPulse...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-shell">
      <header className="dashboard-header">
        <div className="brand-lockup">
          <div className="brand-mark"><Activity size={21} /></div>
          <div><h1>MarketPulse</h1><p>{user?.email || "Smart market intelligence"}</p></div>
        </div>
        <div className="header-actions">
          <span className="live-dot"><i /> Live market view</span>
          <button onClick={handleLogout} className="refresh-button">Sign out</button>
          <button onClick={handleRefresh} disabled={refreshing} className="refresh-button">
            <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Updating" : "Refresh"}
          </button>
        </div>
      </header>

      <main className="dashboard-main">

        {/* ERROR */}
        {error && (
          <div className="mb-6 flex items-center gap-3 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700">
            <AlertTriangle size={19} />
            <p className="text-sm font-medium">
              {error}
            </p>

            <button
              onClick={() => setError("")}
              className="ml-auto"
            >
              <X size={17} />
            </button>
          </div>
        )}


        {/* SINCE LAST CHECKED */}
        <section className="dashboard-title-row">
          <div><p className="eyebrow">Overview / {new Date().toLocaleDateString()}</p><h2>{dashboard?.watchlist_name || "My Watchlist"}</h2><p className="muted">A focused view of what deserves your attention today.</p></div>
          <div className="title-actions"><button className="guide-button" onClick={() => document.getElementById("reading-guide")?.scrollIntoView({ behavior: "smooth" })}><CircleHelp size={15} /> How to read this</button><button onClick={() => setShowAddModal(true)} className="add-button"><Plus size={17} /> Add stock</button></div>
        </section>

        <section className="reading-guide" id="reading-guide">
          <div className="guide-title"><span className="guide-icon"><CircleHelp size={16} /></span><div><strong>New to stocks?</strong><p>Here is the quick version.</p></div></div>
          <div className="guide-item"><b>Price</b><span>What one share costs right now.</span></div>
          <div className="guide-item"><b>Move</b><span>How much the price changed.</span></div>
          <div className="guide-item"><b>Signal</b><span>How unusual that change is.</span></div>
        </section>

        <section className="metric-grid">
          <Metric label="Tracked stocks" value={dashboard?.overview?.tracked_count || 0} detail="stocks in your list" accent="blue" />
          <Metric label="Average move" value={`${formatSigned(dashboard?.overview?.average_change)}%`} detail="average price change" accent="violet" />
          <Metric label="Gainers" value={dashboard?.overview?.gainers || 0} detail="stocks up in price" accent="cyan" />
          <Metric label="Needs attention" value={dashboard?.overview?.attention_count || 0} detail="unusual price changes" accent="pink" />
        </section>

        <section className="content-grid">
          <Panel title="Market pulse" subtitle="Average price change over time" action="30 days" className="pulse-panel"><PulseChart points={dashboard?.trend || []} /></Panel>
          <Panel title="Attention mix" subtitle="How many stocks need a closer look" className="mix-panel"><AttentionMix distribution={dashboard?.distribution || {}} /></Panel>
          <Panel title="Since you last checked" subtitle="The changes worth a closer look" action={`${changes.length} signals`} className="changes-panel"><ChangeList changes={changes} /></Panel>
          <PortfolioPanel portfolio={portfolio} onAdd={() => setShowPortfolioModal(true)} onRemove={handleRemoveHolding} />
          <Panel title="Watchlist" subtitle="Latest prices and signal strength" action={<label className="search-field"><Search size={13} /><input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Find a stock" aria-label="Find a stock in your watchlist" />{searchTerm && <button type="button" className="search-clear" onClick={() => setSearchTerm("")} aria-label="Clear watchlist search"><X size={12} /></button>}</label>} className="stocks-panel"><StockTable stocks={dashboard?.stocks || []} searchTerm={searchTerm} onDelete={handleDeleteStock} /></Panel>
        </section>

      </main>

      {showPortfolioModal && <PortfolioModal saving={savingHolding} onSubmit={handleAddHolding} onClose={() => setShowPortfolioModal(false)} />}


      {/* ADD STOCK MODAL */}
      {showAddModal && (

        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">

          {/* Background */}
          <div
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
            onClick={() => setShowAddModal(false)}
          />

          {/* Modal */}
          <div className="add-stock-modal relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200">

            <div className="flex items-center justify-between px-6 py-5 border-b border-slate-200">

              <div>
                <h2 className="text-lg font-bold">
                  Add Stock
                </h2>

                <p className="text-sm text-slate-500 mt-1">
                  Enter a stock ticker symbol
                </p>
              </div>

              <button
                onClick={() => setShowAddModal(false)}
                className="w-9 h-9 rounded-lg hover:bg-slate-100 flex items-center justify-center"
              >
                <X size={19} />
              </button>

            </div>


            <form
              onSubmit={handleAddStock}
              className="p-6"
            >

              <label className="block text-sm font-semibold mb-2">
                Stock Symbol
              </label>

              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="e.g. AAPL"
                autoFocus
                className="w-full px-4 py-3 rounded-xl border border-slate-300 outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent uppercase"
              />

              {alreadyTracked && (
                <div className="duplicate-stock-warning" role="alert">
                  <AlertTriangle size={14} />
                  <span>{normalizedSymbol} is already in your watchlist.</span>
                </div>
              )}

              {searchingStocks && <p className="stock-search-status">Searching listed companies...</p>}
              {!searchingStocks && stockSuggestions.length > 0 && (
                <div className="stock-suggestions" role="listbox" aria-label="Stock suggestions">
                  {stockSuggestions.map((suggestion) => (
                    <button
                      type="button"
                      className="stock-suggestion"
                      key={`${suggestion.symbol}-${suggestion.description}`}
                      onClick={() => {
                        setSymbol(suggestion.symbol);
                        setStockSuggestions([]);
                      }}
                    >
                      <strong>{suggestion.symbol}</strong>
                      <span>{suggestion.description}</span>
                    </button>
                  ))}
                </div>
              )}

              {!searchingStocks && symbol.trim().length >= 2 && !stockSuggestions.length && (
                <p className="stock-search-status">No matching listed company found. Try a ticker or company name.</p>
              )}


              <div className="flex gap-3 mt-5">

                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-300 font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={adding || !symbol.trim() || alreadyTracked}
                  className="flex-1 px-4 py-3 rounded-xl bg-slate-900 text-white font-medium hover:bg-slate-800 disabled:opacity-50"
                >
                  {adding ? "Adding..." : "Add Stock"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  );
}


function PortfolioPanel({ portfolio, onAdd, onRemove }) {
  const money = (value = 0) => `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const signedMoney = (value = 0) => `${value >= 0 ? "+" : "-"}${money(Math.abs(value))}`;
  return <article className="dashboard-panel portfolio-panel"><div className="panel-heading"><div><h3>Portfolio</h3><p>What your holdings are worth today</p></div><button className="add-button portfolio-add" onClick={onAdd}><Plus size={14} /> Add holding</button></div><div className="portfolio-metrics"><div><span>Portfolio value</span><strong>{money(portfolio?.portfolio_value)}</strong></div><div><span>Today's P&amp;L</span><strong className={portfolio?.today_pnl >= 0 ? "positive" : "negative"}>{signedMoney(portfolio?.today_pnl)}</strong></div><div><span>Overall P&amp;L</span><strong className={portfolio?.overall_pnl >= 0 ? "positive" : "negative"}>{signedMoney(portfolio?.overall_pnl)}</strong></div></div>{portfolio?.main_contributor && <div className="portfolio-alert"><strong>⚠ Portfolio alert</strong><span>Main contributor: <b>{portfolio.main_contributor.symbol}</b> {signedMoney(portfolio.main_contributor.today_pnl)} today</span></div>}<div className="holding-list">{portfolio?.holdings?.length ? portfolio.holdings.map((holding) => <div className="holding-row" key={holding.id}><span><b>{holding.symbol}</b> · {holding.quantity} shares</span><span>{holding.status === "ok" ? money(holding.market_value) : "Unavailable"}</span><button onClick={() => onRemove(holding.symbol)} title={`Remove ${holding.symbol} holding`}><X size={13} /></button></div>) : <span className="portfolio-empty">Add your first holding to track its value and P&amp;L.</span>}</div></article>;
}

function PortfolioModal({ saving, onSubmit, onClose }) {
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [buyPrice, setBuyPrice] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [searching, setSearching] = useState(false);
  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);

  useEffect(() => {
    const query = symbol.trim();
    if (query.length < 2) {
      setSuggestions([]);
      setQuote(null);
      return undefined;
    }
    const timer = window.setTimeout(async () => {
      try {
        setSearching(true);
        const response = await axios.get(`${API_URL}/api/market/search`, { params: { query } });
        setSuggestions(response.data.results || []);
      } catch {
        setSuggestions([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => window.clearTimeout(timer);
  }, [symbol]);

  const selectSymbol = async (selectedSymbol) => {
    setSymbol(selectedSymbol);
    setSuggestions([]);
    setQuoteLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/market/${selectedSymbol}`);
      setQuote(response.data);
      if (!buyPrice && response.data.price) setBuyPrice(String(response.data.price));
    } catch {
      setQuote(null);
    } finally {
      setQuoteLoading(false);
    }
  };

  const submit = (event) => onSubmit(event, { symbol, quantity, buyPrice });
  return <div className="fixed inset-0 z-50 flex items-center justify-center p-4"><div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={onClose} /><form className="portfolio-modal relative" onSubmit={submit}><div className="modal-heading"><div><h2>Add portfolio holding</h2><p>Search a company, then enter what you own.</p></div><button type="button" onClick={onClose}><X size={18} /></button></div><label>Company or ticker<input required value={symbol} onChange={(event) => { setSymbol(event.target.value.toUpperCase()); setQuote(null); }} placeholder="Search AAPL or Apple" autoFocus /></label>{searching && <p className="portfolio-search-status">Searching live-listed companies...</p>}{suggestions.length > 0 && <div className="portfolio-suggestions">{suggestions.map((suggestion) => <button type="button" key={`${suggestion.symbol}-${suggestion.description}`} onClick={() => selectSymbol(suggestion.symbol)}><strong>{suggestion.symbol}</strong><span>{suggestion.description}</span></button>)}</div>}{quoteLoading && <p className="portfolio-search-status">Loading live quote...</p>}{quote && <div className="portfolio-quote"><span>Live price</span><strong>${quote.price.toFixed(2)}</strong><small>{quote.change_percent >= 0 ? "+" : ""}{quote.change_percent?.toFixed(2) || "0.00"}% today</small></div>}<label>Quantity<input required min="0.01" step="0.01" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="10" /></label><label>Buy price per share<input required min="0.01" step="0.01" type="number" value={buyPrice} onChange={(event) => setBuyPrice(event.target.value)} placeholder="Use your purchase price" /></label><button className="auth-submit" disabled={saving || quoteLoading || !quote}>{saving ? "Saving..." : "Add holding"}</button></form></div>;
}

function Metric({ label, value, detail, accent }) {
  return <article className={`metric-card ${accent}`}><div className="metric-label">{label}<span /></div><strong>{value}</strong><p>{detail}</p><div className="metric-spark" /></article>;
}

function Panel({ title, subtitle, action, className = "", children }) {
  return <article className={`dashboard-panel ${className}`}><div className="panel-heading"><div><h3>{title}</h3><p>{subtitle}</p></div>{action && <span className="panel-action">{action}</span>}</div>{children}</article>;
}

function PulseChart({ points }) {
  const values = points.length ? points.map((point) => point.average_change) : [0, 0, 0, 0, 0, 0];
  const min = Math.min(...values, -1);
  const max = Math.max(...values, 1);
  const coordinates = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${92 - ((value - min) / (max - min)) * 72}`).join(" ");
  return <div className="chart-wrap"><svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Watchlist movement chart"><defs><linearGradient id="pulse-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#63d7ff" stopOpacity=".34" /><stop offset="1" stopColor="#765cff" stopOpacity="0" /></linearGradient></defs><path d={`M 0,100 L ${coordinates} L 100,100 Z`} fill="url(#pulse-fill)" /><polyline points={coordinates} fill="none" stroke="#62d8ff" strokeWidth="1.5" vectorEffect="non-scaling-stroke" /></svg><div className="chart-labels"><span>30d ago</span><span>15d ago</span><span>Today</span></div></div>;
}

function AttentionMix({ distribution }) {
  const high = distribution.HIGH || 0;
  const medium = distribution.MEDIUM || 0;
  const normal = distribution.NORMAL || 0;
  const total = high + medium + normal || 1;
  return <div className="mix-layout"><div className="donut" style={{ background: `conic-gradient(#ff83b1 0 ${(high / total) * 100}%, #a277ff ${(high / total) * 100}% ${((high + medium) / total) * 100}%, #4fcff3 ${((high + medium) / total) * 100}% 100%)` }}><div><strong>{total}</strong><span>signals</span></div></div><div className="legend"><Legend color="pink" label="High" value={high} /><Legend color="violet" label="Medium" value={medium} /><Legend color="cyan" label="Normal" value={normal} /></div></div>;
}

function Legend({ color, label, value }) { return <div><i className={color} /> <span>{label}</span><b>{value}</b></div>; }

function ChangeList({ changes }) {
  if (!changes.length) return <div className="empty-module">No new movement since your last check.</div>;
  return <div className="change-list">{changes.slice(0, 5).map((change) => { const positive = change.change_percent >= 0; return <div className="change-row" key={change.symbol}><div className="ticker-badge">{change.symbol.slice(0, 1)}</div><div className="change-copy"><strong>{change.symbol}</strong><span>${change.previous_price.toFixed(2)} <em>to</em> ${change.current_price.toFixed(2)}</span><small>{change.reasons?.[0] || "Price changed since your last check"}</small></div><b className={positive ? "positive" : "negative"}>{positive ? <ArrowUpRight size={15} /> : <ArrowDownRight size={15} />}{positive ? "+" : ""}{change.change_percent.toFixed(2)}%</b></div>; })}</div>;
}

function StockTable({ stocks, searchTerm, onDelete }) {
  if (!stocks.length) return <div className="empty-module">Your watchlist is empty. Add a stock to start tracking.</div>;
  const filteredStocks = stocks.filter((stock) => stock.symbol.toLowerCase().includes(searchTerm.toLowerCase()));
  if (!filteredStocks.length) return <div className="empty-module">No stock matches “{searchTerm}”.</div>;
  return <div className="stock-table"><div className="stock-table-head"><span>Stock</span><span>Trend</span><span>Price</span><span>Move</span><span>Signal</span><span /></div>{filteredStocks.map((stock) => <div className="stock-row" key={stock.symbol}><div className="stock-name"><div className="ticker-badge">{stock.symbol.slice(0, 1)}</div><strong>{stock.symbol}</strong></div><Sparkline history={stock.history} positive={stock.change_percent >= 0} unavailable={stock.status !== "ok"} /><span className="price">{stock.price != null ? `$${stock.price.toFixed(2)}` : "Unavailable"}</span><span className={stock.change_percent >= 0 ? "positive" : "negative"}>{stock.change_percent != null ? `${stock.change_percent >= 0 ? "+" : ""}${stock.change_percent.toFixed(2)}%` : "Unavailable"}</span>{stock.status === "ok" ? <span className={`signal ${stock.severity?.toLowerCase()}`} title="Signal shows how unusual the change is">{stock.severity}</span> : <span className="signal unavailable-signal">Unavailable</span>}<button onClick={() => onDelete(stock.symbol)} title="Remove stock" className="delete-button"><Trash2 size={14} /></button>{stock.status === "ok" ? <div className="stock-insight"><div className="insight-heading"><strong>Why this matters</strong><b>{stock.score}/100 significance</b></div><div className="reason-list">{(stock.reasons?.length ? stock.reasons : ["No unusual market activity detected"]).map((reason, index) => <span key={`${stock.symbol}-reason-${index}`}>• {reason}</span>)}</div><div className="signal-breakdown"><span>Price <b>{stock.signals?.price_score || 0}</b></span><span>Volume <b>{stock.signals?.volume_score || 0}</b></span><span>Market <b>{stock.signals?.market_score || 0}</b></span><span>News <b>{stock.news_score || 0}</b></span>{stock.volume_ratio ? <span>Volume <b>{stock.volume_ratio}× normal</b></span> : <span className="data-note">Volume history unavailable</span>}{stock.market_change != null && <span>SPY <b>{stock.market_change >= 0 ? "+" : ""}{stock.market_change.toFixed(2)}%</b></span>}</div><div className="news-module"><div className="news-module-heading"><strong>Related news</strong><span className={`news-sentiment ${stock.news_sentiment?.toLowerCase()}`}>{stock.news_sentiment || "Unknown"} · {stock.news_impact || "None"} impact</span></div>{stock.news?.length ? stock.news.slice(0, 2).map((article, index) => <a className="news-headline" href={article.url} target="_blank" rel="noreferrer" key={`${stock.symbol}-news-${index}`}>{article.headline}<small>{article.source || "Market news"}</small></a>) : <span className="news-empty">No recent related headlines found.</span>}</div></div> : <div className="stock-insight stock-error"><strong>Market data unavailable</strong><span>This symbol is not currently supported by the market data provider.</span><small>Remove it and add a supported US-listed ticker such as AAPL, NVDA, or TSLA.</small></div>}</div>)}</div>;
}

function Sparkline({ history = [], positive, unavailable }) {
  const values = history.map((point) => point.price).filter((price) => Number.isFinite(price));
  if (unavailable) return <span className="sparkline-empty">Unavailable</span>;
  if (values.length < 2) return <span className="sparkline-empty">Collecting history</span>;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((value, index) => `${(index / (values.length - 1)) * 100},${92 - ((value - min) / range) * 78}`).join(" ");
  return <svg className={`sparkline ${positive ? "sparkline-positive" : "sparkline-negative"}`} viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Recent price history"><polyline points={points} fill="none" strokeWidth="2" vectorEffect="non-scaling-stroke" /></svg>;
}

function formatSigned(value = 0) { return `${value >= 0 ? "+" : ""}${Number(value).toFixed(2)}`; }

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setAuthError("");
    try {
      const response = await axios.post(`${API_URL}/api/auth/${mode}`, { email, password });
      onAuthenticated(response);
    } catch (error) {
      setAuthError(error.response?.data?.detail || "Unable to authenticate right now.");
    } finally {
      setSubmitting(false);
    }
  };

  return <div className="auth-shell"><div className="auth-card"><div className="brand-mark auth-mark"><Activity size={23} /></div><p className="eyebrow">Personal market intelligence</p><h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1><p className="auth-subtitle">{mode === "login" ? "Sign in to see your personal watchlist." : "Save your watchlist and return to it anywhere."}</p><form onSubmit={submit} className="auth-form"><label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label><label>Password<input type="password" required minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" /></label>{authError && <p className="auth-error">{authError}</p>}<button className="auth-submit" disabled={submitting}>{submitting ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}</button></form><button className="auth-switch" onClick={() => { setMode(mode === "login" ? "register" : "login"); setAuthError(""); }}>{mode === "login" ? "New here? Create an account" : "Already have an account? Sign in"}</button></div></div>;
}

export default App;