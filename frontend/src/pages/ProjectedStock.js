import React, { useEffect, useState, useMemo } from 'react';
import { Package, AlertTriangle, CheckCircle, TrendingDown, TrendingUp, Calendar, RefreshCw, Filter, Search } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function ProjectedStock() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filtres
  const [filters, setFilters] = useState({
    search: '',
    status: ''
  });
  const [showFilters, setShowFilters] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/projected-stock`);
      if (!response.ok) throw new Error('Erreur de chargement');
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Filtrage
  const filteredStock = useMemo(() => {
    if (!data?.projected_stock) return [];
    
    return data.projected_stock.filter(item => {
      // Recherche textuelle
      if (filters.search && !item.article_id?.toLowerCase().includes(filters.search.toLowerCase())) {
        return false;
      }
      
      // Filtre statut
      if (filters.status === 'shortage' && !item.has_shortage) return false;
      if (filters.status === 'ok' && item.has_shortage) return false;
      if (filters.status === 'low' && item.final_stock >= item.total_consumption * 0.2) return false;
      
      return true;
    });
  }, [data, filters]);

  const clearFilters = () => {
    setFilters({ search: '', status: '' });
  };

  const activeFiltersCount = Object.values(filters).filter(v => v !== '').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="loading">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--brand-primary)' }}></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg px-4 py-3" style={{ backgroundColor: 'var(--status-error-bg)', border: '1px solid var(--status-error-border)', color: 'var(--status-error)' }} data-testid="error">
        Erreur: {error}
      </div>
    );
  }

  const { consumption_details, summary } = data || {};

  return (
    <div className="space-y-6" data-testid="projected-stock-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Stock Projeté</h1>
          <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
            Vue du stock avec consommations et réceptions planifiées
          </p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 rounded-lg"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
          data-testid="refresh-btn"
        >
          <RefreshCw size={16} />
          Actualiser
        </button>
      </div>

      {/* Barre de filtres */}
      <div className="rounded-lg p-4" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Rechercher par article..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="w-full h-9 pl-9 pr-3 rounded-lg border text-sm"
              style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
              data-testid="filter-search"
            />
          </div>
          
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium"
            style={{ 
              backgroundColor: activeFiltersCount > 0 ? 'var(--status-info-bg)' : 'var(--bg-sunken)', 
              color: activeFiltersCount > 0 ? 'var(--status-info)' : 'var(--text-secondary)',
              border: '1px solid var(--border-default)'
            }}
            data-testid="toggle-filters"
          >
            <Filter size={16} />
            Filtres {activeFiltersCount > 0 && `(${activeFiltersCount})`}
          </button>
          
          {activeFiltersCount > 0 && (
            <button onClick={clearFilters} className="text-sm font-medium" style={{ color: 'var(--status-error)' }}>
              Réinitialiser
            </button>
          )}
        </div>
        
        {showFilters && (
          <div className="grid grid-cols-3 gap-4 mt-4 pt-4" style={{ borderTop: '1px solid var(--border-default)' }}>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>Statut stock</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-status"
              >
                <option value="">Tous</option>
                <option value="shortage">En rupture</option>
                <option value="ok">OK</option>
                <option value="low">Stock faible</option>
              </select>
            </div>
            <div></div>
            <div className="flex items-end">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {filteredStock.length} / {data?.projected_stock?.length || 0} articles
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Résumé */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4" data-testid="summary-total">
          <div className="flex items-center gap-3">
            <div className="bg-slate-100 p-2 rounded-lg">
              <Package className="text-slate-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-600">Total Articles</p>
              <p className="text-2xl font-bold text-slate-900">{summary?.total_articles || 0}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-sm border border-red-200 p-4" data-testid="summary-shortage">
          <div className="flex items-center gap-3">
            <div className="bg-red-100 p-2 rounded-lg">
              <AlertTriangle className="text-red-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-red-600">En Rupture</p>
              <p className="text-2xl font-bold text-red-700">{summary?.articles_with_shortage || 0}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-sm border border-green-200 p-4" data-testid="summary-ok">
          <div className="flex items-center gap-3">
            <div className="bg-green-100 p-2 rounded-lg">
              <CheckCircle className="text-green-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-green-600">Stock OK</p>
              <p className="text-2xl font-bold text-green-700">{summary?.articles_ok || 0}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-sm border border-blue-200 p-4" data-testid="summary-scheduled">
          <div className="flex items-center gap-3">
            <div className="bg-blue-100 p-2 rounded-lg">
              <Calendar className="text-blue-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-blue-600">Ordonnancées</p>
              <p className="text-lg font-bold text-blue-700">
                {summary?.scheduled_consumptions || 0} / {(summary?.scheduled_consumptions || 0) + (summary?.unscheduled_consumptions || 0)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tableau du stock projeté */}
      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }} data-testid="stock-table">
        <div className="px-4 py-3" style={{ backgroundColor: 'var(--bg-sunken)', borderBottom: '1px solid var(--border-default)' }}>
          <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>Projection par Article</h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead style={{ backgroundColor: 'var(--bg-sunken)' }}>
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase" style={{ color: 'var(--text-muted)' }}>Article</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase" style={{ color: 'var(--text-muted)' }}>Stock Initial</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase" style={{ color: 'var(--text-muted)' }}>Consommations</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase" style={{ color: 'var(--text-muted)' }}>Réceptions</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase" style={{ color: 'var(--text-muted)' }}>Stock Final</th>
                <th className="px-4 py-3 text-center text-xs font-medium uppercase" style={{ color: 'var(--text-muted)' }}>Statut</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase" style={{ color: 'var(--text-muted)' }}>Disponibilité</th>
              </tr>
            </thead>
            <tbody>
              {filteredStock.map((item) => (
                <tr 
                  key={item.article_id}
                  style={{ 
                    borderBottom: '1px solid var(--border-default)',
                    backgroundColor: item.has_shortage ? 'var(--status-error-bg)' : 'transparent'
                  }}
                  data-testid={`stock-row-${item.article_id}`}
                >
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{item.article_id}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{item.initial_stock}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="flex items-center justify-end gap-1 font-mono" style={{ color: 'var(--status-error)' }}>
                      <TrendingDown size={14} />
                      -{item.total_consumption}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="flex items-center justify-end gap-1 font-mono" style={{ color: 'var(--status-success)' }}>
                      <TrendingUp size={14} />
                      +{item.total_receipts}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono font-bold" style={{ color: item.final_stock < 0 ? 'var(--status-error)' : 'var(--text-primary)' }}>
                      {item.final_stock}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {item.has_shortage ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium" style={{ backgroundColor: 'var(--status-error-bg)', color: 'var(--status-error)' }}>
                        <AlertTriangle size={12} />
                        Rupture ({item.shortage_quantity})
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium" style={{ backgroundColor: 'var(--status-success-bg)', color: 'var(--status-success)' }}>
                        <CheckCircle size={12} />
                        OK
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {item.has_shortage && item.first_shortage_datetime ? (
                      <span className="flex items-center gap-1 text-xs font-medium" style={{ color: 'var(--status-error)' }}>
                        <AlertTriangle size={12} />
                        Rupture: {item.first_shortage_datetime?.substring(0, 16).replace('T', ' ')}
                      </span>
                    ) : item.has_shortage && item.availability_date ? (
                      <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--status-warning)' }}>
                        <Calendar size={12} />
                        Dispo: {item.availability_date?.substring(0, 16).replace('T', ' ')}
                      </span>
                    ) : item.has_shortage ? (
                      <span className="text-red-600 text-xs font-medium">Pas de réception prévue</span>
                    ) : (
                      <span className="text-green-600 text-xs">Disponible</span>
                    )}
                  </td>
                </tr>
              ))}
              {filteredStock.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center" style={{ color: 'var(--text-muted)' }}>
                    {data?.projected_stock?.length === 0 
                      ? 'Aucune donnée de stock disponible'
                      : 'Aucun article ne correspond aux filtres.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Détails des consommations */}
      {consumption_details && consumption_details.length > 0 && (
        <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }} data-testid="consumption-table">
          <div className="px-4 py-3" style={{ backgroundColor: 'var(--bg-sunken)', borderBottom: '1px solid var(--border-default)' }}>
            <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>Détail des Consommations par Opération</h2>
          </div>
          
          <div className="overflow-x-auto max-h-96">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Article</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-slate-500 uppercase">Quantité</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Opération</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Ordre</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Date Consommation</th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-slate-500 uppercase">Statut</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {consumption_details.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="px-4 py-2 font-mono text-sm text-slate-900">{item.article_id}</td>
                    <td className="px-4 py-2 text-right font-mono text-red-600">-{item.quantity}</td>
                    <td className="px-4 py-2 font-mono text-sm text-slate-600">{item.operation_id}</td>
                    <td className="px-4 py-2 font-mono text-sm text-slate-600">{item.order_id}</td>
                    <td className="px-4 py-2 text-xs text-slate-700">
                      {item.consumption_datetime?.substring(0, 16).replace('T', ' ') || item.due_date?.substring(0, 16).replace('T', ' ') || '-'}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {item.is_scheduled ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                          Ordonnancée
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                          Date besoin
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
