import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Package, TrendingDown, TrendingUp, AlertTriangle, Check, Calendar, Filter, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ProjectedStockScenario() {
  const { scenarioId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [filterShortage, setFilterShortage] = useState(false);
  const [articleFilter, setArticleFilter] = useState('');

  useEffect(() => {
    fetchData();
  }, [scenarioId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/projected-stock/${scenarioId}`);
      setData(response.data);
      // Sélectionner automatiquement le premier article en rupture s'il y en a
      const firstShortage = response.data.projected_stock?.find(a => a.has_shortage);
      if (firstShortage) {
        setSelectedArticle(firstShortage.article_id);
        setFilterShortage(true);
      } else if (response.data.projected_stock?.length > 0) {
        setSelectedArticle(response.data.projected_stock[0].article_id);
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur de chargement des données');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--brand-primary)' }} />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4" style={{ color: 'var(--text-muted)' }}>
        <AlertTriangle size={48} />
        <p>Données non disponibles</p>
        <button
          onClick={() => navigate('/scenarios')}
          className="px-4 py-2 rounded-lg"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
        >
          Retour aux scénarios
        </button>
      </div>
    );
  }

  const { scenario_name, scenario_status, projected_stock, summary, scheduling_start } = data;

  // Filtrer les articles
  const filteredArticles = projected_stock.filter(a => {
    // Filtre rupture
    if (filterShortage && !a.has_shortage) return false;
    // Filtre texte
    if (articleFilter && !a.article_id.toLowerCase().includes(articleFilter.toLowerCase())) return false;
    return true;
  });

  // Article sélectionné
  const selectedArticleData = projected_stock.find(a => a.article_id === selectedArticle);

  return (
    <div className="space-y-6" data-testid="projected-stock-scenario">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/gantt/${scenarioId}`)}
            className="inline-flex items-center gap-2 transition-colors hover:opacity-80"
            style={{ color: 'var(--text-secondary)' }}
            data-testid="back-btn"
          >
            <ArrowLeft size={16} />
            Retour au Gantt
          </button>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Stock Projeté
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Scénario : {scenario_name} ({scenario_status})
            </p>
          </div>
        </div>
        <button
          onClick={fetchData}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
          style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
        >
          <RefreshCw size={16} />
          Actualiser
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-2 mb-1">
            <Package size={16} style={{ color: 'var(--brand-primary)' }} />
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Articles</span>
          </div>
          <p className="text-2xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
            {summary.total_articles}
          </p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-2 mb-1">
            <Check size={16} style={{ color: 'var(--status-success)' }} />
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>OK</span>
          </div>
          <p className="text-2xl font-bold font-mono" style={{ color: 'var(--status-success)' }}>
            {summary.articles_ok}
          </p>
        </div>
        <div className="p-4 rounded-lg" style={{ 
          backgroundColor: summary.articles_with_shortage > 0 ? 'rgba(239, 68, 68, 0.1)' : 'var(--bg-elevated)', 
          border: `1px solid ${summary.articles_with_shortage > 0 ? 'var(--status-error)' : 'var(--border-default)'}` 
        }}>
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={16} style={{ color: summary.articles_with_shortage > 0 ? 'var(--status-error)' : 'var(--text-muted)' }} />
            <span className="text-xs uppercase tracking-wide" style={{ color: summary.articles_with_shortage > 0 ? 'var(--status-error)' : 'var(--text-muted)' }}>Ruptures</span>
          </div>
          <p className="text-2xl font-bold font-mono" style={{ color: summary.articles_with_shortage > 0 ? 'var(--status-error)' : 'var(--text-primary)' }}>
            {summary.articles_with_shortage}
          </p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-2 mb-1">
            <Calendar size={16} style={{ color: 'var(--status-info)' }} />
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Événements</span>
          </div>
          <p className="text-2xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
            {summary.total_events}
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Liste des articles */}
        <div className="col-span-1 space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Articles</h2>
              <button
                onClick={() => setFilterShortage(!filterShortage)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors`}
                style={{
                  backgroundColor: filterShortage ? 'var(--status-error)' : 'var(--bg-elevated)',
                  color: filterShortage ? 'white' : 'var(--text-secondary)',
                  border: `1px solid ${filterShortage ? 'transparent' : 'var(--border-default)'}`
                }}
                data-testid="filter-shortage-btn"
              >
                <Filter size={14} />
                Ruptures
              </button>
            </div>
            {/* Filtre par article */}
            <div className="relative">
              <input
                type="text"
                placeholder="Filtrer par article..."
                value={articleFilter}
                onChange={(e) => setArticleFilter(e.target.value)}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{ 
                  backgroundColor: 'var(--bg-sunken)', 
                  border: '1px solid var(--border-default)',
                  color: 'var(--text-primary)'
                }}
                data-testid="article-filter-input"
              />
              {articleFilter && (
                <button
                  onClick={() => setArticleFilter('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-xs px-2 py-1 rounded"
                  style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-muted)' }}
                >
                  ✕
                </button>
              )}
            </div>
          </div>
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
            {filteredArticles.map(article => (
              <button
                key={article.article_id}
                onClick={() => setSelectedArticle(article.article_id)}
                className="w-full p-3 rounded-lg text-left transition-all"
                style={{
                  backgroundColor: selectedArticle === article.article_id ? 'var(--brand-primary)' : 'var(--bg-elevated)',
                  color: selectedArticle === article.article_id ? 'white' : 'var(--text-primary)',
                  border: `1px solid ${selectedArticle === article.article_id ? 'transparent' : 'var(--border-default)'}`
                }}
                data-testid={`article-${article.article_id}`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-semibold">{article.article_id}</span>
                  {article.has_shortage ? (
                    <AlertTriangle size={16} style={{ color: selectedArticle === article.article_id ? 'white' : 'var(--status-error)' }} />
                  ) : (
                    <Check size={16} style={{ color: selectedArticle === article.article_id ? 'white' : 'var(--status-success)' }} />
                  )}
                </div>
                <div className="flex items-center gap-4 mt-1 text-sm" style={{ opacity: 0.8 }}>
                  <span>Init: {article.initial_stock}</span>
                  <span>Final: {article.final_stock}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Détail de l'article sélectionné */}
        <div className="col-span-2">
          {selectedArticleData ? (
            <div className="space-y-4">
              {/* Header article */}
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
                      {selectedArticleData.article_id}
                    </h2>
                    <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                      {selectedArticleData.events_count} événements
                    </p>
                  </div>
                  {selectedArticleData.has_shortage ? (
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)' }}>
                      <AlertTriangle size={16} style={{ color: 'var(--status-error)' }} />
                      <span className="text-sm font-medium" style={{ color: 'var(--status-error)' }}>
                        Rupture à {selectedArticleData.first_shortage_datetime?.substring(0, 16).replace('T', ' ')}
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ backgroundColor: 'rgba(16, 185, 129, 0.1)' }}>
                      <Check size={16} style={{ color: 'var(--status-success)' }} />
                      <span className="text-sm font-medium" style={{ color: 'var(--status-success)' }}>Stock OK</span>
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center p-2 rounded" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Initial</p>
                    <p className="text-lg font-bold font-mono" style={{ color: 'var(--text-primary)' }}>{selectedArticleData.initial_stock}</p>
                  </div>
                  <div className="text-center p-2 rounded" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Réceptions</p>
                    <p className="text-lg font-bold font-mono" style={{ color: 'var(--status-success)' }}>+{selectedArticleData.total_receipts}</p>
                    {(selectedArticleData.total_receipts_production > 0 || selectedArticleData.total_receipts_supplier > 0) && (
                      <div className="flex justify-center gap-2 mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                        {selectedArticleData.total_receipts_supplier > 0 && <span>Fourn: {selectedArticleData.total_receipts_supplier}</span>}
                        {selectedArticleData.total_receipts_production > 0 && <span style={{ color: '#059669' }}>Fab: {selectedArticleData.total_receipts_production}</span>}
                      </div>
                    )}
                  </div>
                  <div className="text-center p-2 rounded" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Consommations</p>
                    <p className="text-lg font-bold font-mono" style={{ color: 'var(--status-error)' }}>-{selectedArticleData.total_consumptions}</p>
                  </div>
                  <div className="text-center p-2 rounded" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Final</p>
                    <p className="text-lg font-bold font-mono" style={{ color: selectedArticleData.final_stock >= 0 ? 'var(--text-primary)' : 'var(--status-error)' }}>
                      {selectedArticleData.final_stock}
                    </p>
                  </div>
                </div>
              </div>

              {/* Timeline des événements */}
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
                <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
                  Timeline des mouvements
                </h3>
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {/* Stock initial */}
                  <div className="flex items-center gap-4 p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                    <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}>
                      <Package size={18} />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium" style={{ color: 'var(--text-primary)' }}>Stock initial</p>
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Début de période</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
                        {selectedArticleData.initial_stock}
                      </p>
                    </div>
                  </div>
                  
                  {/* Événements */}
                  {selectedArticleData.timeline.map((evt, idx) => {
                    const isReceipt = evt.type === 'RECEIPT' || evt.type === 'PRODUCTION_RECEIPT';
                    const isProduction = evt.type === 'PRODUCTION_RECEIPT';
                    const eventLabel = isProduction 
                      ? evt.reference  // "Fabrication OF xxx"
                      : evt.type === 'RECEIPT' 
                        ? 'Réception fournisseur' 
                        : evt.reference;
                    
                    return (
                      <div 
                        key={idx}
                        className="flex items-center gap-4 p-3 rounded-lg transition-colors"
                        style={{ 
                          backgroundColor: evt.stock_after < 0 ? 'rgba(239, 68, 68, 0.1)' : 'var(--bg-sunken)',
                          border: evt.stock_after < 0 ? '1px solid var(--status-error)' : 'none'
                        }}
                      >
                        <div 
                          className="w-10 h-10 rounded-full flex items-center justify-center"
                          style={{ 
                            backgroundColor: isReceipt 
                              ? (isProduction ? '#059669' : 'var(--status-success)')  // Vert foncé pour production
                              : 'var(--status-error)',
                            color: 'white'
                          }}
                        >
                          {isReceipt ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                              {eventLabel}
                            </p>
                            {isProduction && (
                              <span className="px-2 py-0.5 rounded text-xs" style={{ backgroundColor: '#059669', color: 'white' }}>
                                Fabrication
                              </span>
                            )}
                            {!evt.is_scheduled && (
                              <span className="px-2 py-0.5 rounded text-xs" style={{ backgroundColor: 'var(--status-warning)', color: 'white' }}>
                                Non planifié
                              </span>
                            )}
                          </div>
                          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                            {evt.datetime ? evt.datetime.replace('T', ' ').substring(0, 16) : 'Date non définie'}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold font-mono" style={{ color: isReceipt ? 'var(--status-success)' : 'var(--status-error)' }}>
                            {evt.quantity_change > 0 ? '+' : ''}{evt.quantity_change}
                          </p>
                          <p className="text-xs" style={{ color: evt.stock_after < 0 ? 'var(--status-error)' : 'var(--text-muted)' }}>
                            Stock: {evt.stock_after}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64" style={{ backgroundColor: 'var(--bg-elevated)', borderRadius: '0.5rem' }}>
              <p style={{ color: 'var(--text-muted)' }}>Sélectionnez un article pour voir les détails</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
