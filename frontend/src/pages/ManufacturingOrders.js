import { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import { RefreshCw, AlertTriangle, CheckCircle, XCircle, Filter, Search, Calendar } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ManufacturingOrders() {
  const [operations, setOperations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('flat');
  
  // Filtres
  const [filters, setFilters] = useState({
    search: '',
    article_id: '',
    status: '',
    dateFrom: '',
    dateTo: ''
  });
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchEnrichedOperations();
  }, []);

  const fetchEnrichedOperations = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/operations-enrichies`);
      setOperations(response.data);
      toast.success(`${response.data.length} opérations chargées`);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  const isLate = (dateBesoin) => {
    if (!dateBesoin) return false;
    const due = new Date(dateBesoin);
    const today = new Date();
    return due < today;
  };

  const isUrgent = (dateBesoin) => {
    if (!dateBesoin) return false;
    const due = new Date(dateBesoin);
    const today = new Date();
    const daysUntil = Math.ceil((due - today) / (1000 * 60 * 60 * 24));
    return daysUntil <= 3 && daysUntil >= 0;
  };

  // Filtrage
  const filteredOperations = useMemo(() => {
    return operations.filter(op => {
      // Recherche textuelle
      if (filters.search) {
        const s = filters.search.toLowerCase();
        const matchOrder = String(op.order_id || '').toLowerCase().includes(s);
        const matchArticle = String(op.article_id || '').toLowerCase().includes(s);
        const matchOp = String(op.operation_id || '').toLowerCase().includes(s);
        if (!matchOrder && !matchArticle && !matchOp) return false;
      }
      
      // Filtre article
      if (filters.article_id && !String(op.article_id || '').includes(filters.article_id)) return false;
      
      // Filtre statut
      if (filters.status === 'late' && !isLate(op.date_besoin)) return false;
      if (filters.status === 'urgent' && !isUrgent(op.date_besoin)) return false;
      if (filters.status === 'ok' && (isLate(op.date_besoin) || isUrgent(op.date_besoin))) return false;
      
      // Filtre dates
      if (filters.dateFrom && op.date_besoin) {
        if (new Date(op.date_besoin) < new Date(filters.dateFrom)) return false;
      }
      if (filters.dateTo && op.date_besoin) {
        if (new Date(op.date_besoin) > new Date(filters.dateTo)) return false;
      }
      
      return true;
    });
  }, [operations, filters]);

  // Articles uniques pour le filtre
  const uniqueArticles = useMemo(() => {
    const articles = [...new Set(operations.map(op => op.article_id).filter(Boolean))];
    return articles.sort();
  }, [operations]);

  const clearFilters = () => {
    setFilters({ search: '', article_id: '', status: '', dateFrom: '', dateTo: '' });
  };

  const activeFiltersCount = Object.values(filters).filter(v => v !== '').length;

  // Grouper par order_id pour la vue groupée
  const groupedByOrder = filteredOperations.reduce((acc, op) => {
    const orderId = op.order_id || 'SANS_ORDRE';
    if (!acc[orderId]) {
      acc[orderId] = {
        order_id: orderId,
        article_id: op.article_id,
        date_besoin: op.date_besoin,
        priority: op.priority,
        operations: []
      };
    }
    acc[orderId].operations.push(op);
    return acc;
  }, {});

  const ordersArray = Object.values(groupedByOrder);

  return (
    <div className="space-y-6" data-testid="manufacturing-orders-page">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Ordres de Fabrication</h3>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Vue enrichie : jointure opérations + ordres via order_id
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg p-0.5" style={{ backgroundColor: 'var(--bg-sunken)' }}>
            <button
              onClick={() => setViewMode('flat')}
              className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors`}
              style={{ 
                backgroundColor: viewMode === 'flat' ? 'var(--bg-elevated)' : 'transparent',
                color: viewMode === 'flat' ? 'var(--text-primary)' : 'var(--text-secondary)'
              }}
            >
              Vue à plat
            </button>
            <button
              onClick={() => setViewMode('grouped')}
              className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors`}
              style={{ 
                backgroundColor: viewMode === 'grouped' ? 'var(--bg-elevated)' : 'transparent',
                color: viewMode === 'grouped' ? 'var(--text-primary)' : 'var(--text-secondary)'
              }}
            >
              Par OF
            </button>
          </div>
          <button
            onClick={fetchEnrichedOperations}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50"
            style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Actualiser
          </button>
        </div>
      </div>

      {/* Barre de filtres */}
      <div className="rounded-lg p-4" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Rechercher par OF, article, opération..."
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
          <div className="grid grid-cols-5 gap-4 mt-4 pt-4" style={{ borderTop: '1px solid var(--border-default)' }}>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>Article</label>
              <select
                value={filters.article_id}
                onChange={(e) => setFilters({ ...filters, article_id: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-article"
              >
                <option value="">Tous</option>
                {uniqueArticles.map(a => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>Statut</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-status"
              >
                <option value="">Tous</option>
                <option value="late">En retard</option>
                <option value="urgent">Urgent (≤3j)</option>
                <option value="ok">OK</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>
                <Calendar size={12} className="inline mr-1" />Date début
              </label>
              <input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-date-from"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>
                <Calendar size={12} className="inline mr-1" />Date fin
              </label>
              <input
                type="date"
                value={filters.dateTo}
                onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-date-to"
              />
            </div>
            <div className="flex items-end">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {filteredOperations.length} / {operations.length} opérations
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Statistiques */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg p-4" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>{filteredOperations.length}</div>
          <div className="text-sm" style={{ color: 'var(--text-muted)' }}>Opérations</div>
        </div>
        <div className="rounded-lg p-4" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>{ordersArray.length}</div>
          <div className="text-sm" style={{ color: 'var(--text-muted)' }}>Ordres de Fab.</div>
        </div>
        <div className="rounded-lg p-4" style={{ backgroundColor: 'var(--status-error-bg)', border: '1px solid var(--status-error-border)' }}>
          <div className="text-3xl font-bold" style={{ color: 'var(--status-error)' }}>
            {filteredOperations.filter(op => isLate(op.date_besoin)).length}
          </div>
          <div className="text-sm" style={{ color: 'var(--status-error)' }}>En retard</div>
        </div>
        <div className="rounded-lg p-4" style={{ backgroundColor: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)' }}>
          <div className="text-3xl font-bold" style={{ color: 'var(--status-warning)' }}>
            {filteredOperations.filter(op => isUrgent(op.date_besoin)).length}
          </div>
          <div className="text-sm" style={{ color: 'var(--status-warning)' }}>Urgent (≤3j)</div>
        </div>
      </div>

      {/* Vue à plat */}
      {viewMode === 'flat' && (
        <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="px-4 py-3" style={{ backgroundColor: 'var(--bg-sunken)', borderBottom: '1px solid var(--border-default)' }}>
            <h4 className="font-semibold" style={{ color: 'var(--text-primary)' }}>Opérations Enrichies (Vue à Plat)</h4>
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
              Chaque ligne montre une opération avec les données de son ordre (jointure sur order_id)
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead style={{ backgroundColor: 'var(--bg-sunken)' }}>
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Order ID</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Article</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Date Besoin</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Priorité</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Op. ID</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Tâche</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Centre</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Prod (min)</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Setup (min)</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Jointure</th>
                </tr>
              </thead>
              <tbody>
                {filteredOperations.map((op) => (
                  <tr 
                    key={op.id} 
                    className="transition-colors"
                    style={{ 
                      borderBottom: '1px solid var(--border-default)',
                      backgroundColor: isLate(op.date_besoin) ? 'var(--status-error-bg)' : 
                                      isUrgent(op.date_besoin) ? 'var(--status-warning-bg)' : 'transparent'
                    }}
                  >
                    <td className="px-3 py-2 font-mono text-xs" style={{ color: 'var(--text-primary)' }}>{op.order_id}</td>
                    <td className="px-3 py-2">
                      {op.article_id ? (
                        <span className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: 'var(--status-warning-bg)', color: 'var(--status-warning)' }}>
                          {op.article_id}
                        </span>
                      ) : (
                        <span className="text-xs" style={{ color: 'var(--status-error)' }}>NON TROUVE</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {op.date_besoin ? (
                        <span className="text-xs font-mono" style={{ 
                          color: isLate(op.date_besoin) ? 'var(--status-error)' :
                                 isUrgent(op.date_besoin) ? 'var(--status-warning)' : 'var(--text-secondary)',
                          fontWeight: isLate(op.date_besoin) || isUrgent(op.date_besoin) ? 'bold' : 'normal'
                        }}>
                          {op.date_besoin?.substring(0, 10)}
                          {isLate(op.date_besoin) && ' (RETARD)'}
                          {isUrgent(op.date_besoin) && ' (URGENT)'}
                        </span>
                      ) : (
                        <span className="text-xs" style={{ color: 'var(--status-error)' }}>NON TROUVE</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-xs text-center" style={{ color: 'var(--text-secondary)' }}>{op.priority || 0}</td>
                    <td className="px-3 py-2">
                      <span className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: 'var(--status-info-bg)', color: 'var(--status-info)' }}>
                        {op.operation_id}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: 'var(--status-info-bg)', color: 'var(--status-info)' }}>
                        {op.tache_id || '-'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
                        {op.centre_de_charge_id || '-'}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>{op.production_time_minutes || 0}</td>
                    <td className="px-3 py-2 font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>{op.setup_time_minutes || 0}</td>
                    <td className="px-3 py-2">
                      {op.article_id ? (
                        <CheckCircle size={14} style={{ color: 'var(--status-success)' }} />
                      ) : (
                        <XCircle size={14} style={{ color: 'var(--status-error)' }} />
                      )}
                    </td>
                  </tr>
                ))}
                {filteredOperations.length === 0 && (
                  <tr>
                    <td colSpan={10} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                      {operations.length === 0 ? 'Aucune opération. Importez des données CSV.' : 'Aucune opération ne correspond aux filtres.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Vue groupée par OF */}
      {viewMode === 'grouped' && (
        <div className="space-y-4">
          {ordersArray.map((order) => (
            <div key={order.order_id} className={`bg-white border rounded-lg shadow-sm overflow-hidden ${
              isLate(order.date_besoin) ? 'border-red-300' : 
              isUrgent(order.date_besoin) ? 'border-amber-300' : 'border-slate-200'
            }`}>
              <div className={`px-4 py-3 border-b ${
                isLate(order.date_besoin) ? 'bg-red-50 border-red-200' : 
                isUrgent(order.date_besoin) ? 'bg-amber-50 border-amber-200' : 'bg-slate-50 border-slate-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="font-mono font-bold text-slate-800">{order.order_id}</span>
                    {order.article_id && (
                      <span className="bg-orange-100 text-orange-800 px-2 py-0.5 rounded text-xs font-mono">
                        Article: {order.article_id}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    {order.date_besoin && (
                      <span className={`text-xs font-mono ${
                        isLate(order.date_besoin) ? 'text-red-700 font-bold' :
                        isUrgent(order.date_besoin) ? 'text-amber-700 font-bold' : 'text-slate-600'
                      }`}>
                        Besoin: {order.date_besoin}
                        {isLate(order.date_besoin) && (
                          <span className="ml-2 bg-red-200 text-red-800 px-1.5 py-0.5 rounded">RETARD</span>
                        )}
                        {isUrgent(order.date_besoin) && (
                          <span className="ml-2 bg-amber-200 text-amber-800 px-1.5 py-0.5 rounded">URGENT</span>
                        )}
                      </span>
                    )}
                    <span className="text-xs text-slate-500">{order.operations.length} opération(s)</span>
                  </div>
                </div>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-slate-100 border-b border-slate-200">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">N° Op</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Tâche</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Centre</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Prod (min)</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Setup (min)</th>
                  </tr>
                </thead>
                <tbody>
                  {order.operations
                    .sort((a, b) => (a.operation_id || 0) - (b.operation_id || 0))
                    .map((op) => (
                      <tr key={op.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="px-3 py-2 font-mono text-xs">{op.operation_id}</td>
                        <td className="px-3 py-2">
                          <span className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded text-xs font-mono">
                            {op.tache_id || '-'}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <span className="bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded text-xs font-mono">
                            {op.centre_de_charge_id || '-'}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-xs text-right font-mono">{op.production_time_minutes}</td>
                        <td className="px-3 py-2 text-xs text-right font-mono">{op.setup_time_minutes}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ))}
          {ordersArray.length === 0 && (
            <div className="bg-white border border-slate-200 rounded-lg p-8 text-center text-sm text-slate-500">
              Aucun ordre de fabrication. Importez des données via Import CSV.
            </div>
          )}
        </div>
      )}

      {/* Légende */}
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
        <h4 className="font-semibold text-slate-800 mb-2">Légende</h4>
        <div className="flex gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-100 border border-red-300 rounded"></div>
            <span className="text-slate-600">En retard (date_besoin dépassée)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-amber-100 border border-amber-300 rounded"></div>
            <span className="text-slate-600">Urgent (≤3 jours)</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle size={16} className="text-green-600" />
            <span className="text-slate-600">Jointure OK (ordre trouvé)</span>
          </div>
          <div className="flex items-center gap-2">
            <XCircle size={16} className="text-red-600" />
            <span className="text-slate-600">Jointure KO (ordre non trouvé)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
