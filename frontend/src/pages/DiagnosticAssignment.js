import React, { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import { RefreshCw, CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronRight, Clock, Filter, Search } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function DiagnosticAssignment() {
  const [diagnostic, setDiagnostic] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedOps, setExpandedOps] = useState({});
  
  // Filtres
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    centre: '',
    article: ''
  });
  const [showFilters, setShowFilters] = useState(false);

  const fetchDiagnostic = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/diagnostic/assignment`);
      setDiagnostic(response.data);
      toast.success('Diagnostic chargé');
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostic();
  }, []);

  const toggleExpand = (opId) => {
    setExpandedOps(prev => ({ ...prev, [opId]: !prev[opId] }));
  };

  // Filtrage
  const filteredDiagnostics = useMemo(() => {
    if (!diagnostic?.diagnostics_table) return [];
    
    return diagnostic.diagnostics_table.filter(op => {
      // Recherche textuelle
      if (filters.search) {
        const s = filters.search.toLowerCase();
        const matchOp = op.operation_id?.toLowerCase().includes(s);
        const matchOrder = op.order_id?.toLowerCase().includes(s);
        const matchArticle = op.article_id?.toLowerCase().includes(s);
        if (!matchOp && !matchOrder && !matchArticle) return false;
      }
      
      // Filtre statut
      if (filters.status === 'assigned' && !op.machine_assignee) return false;
      if (filters.status === 'unassigned' && op.machine_assignee) return false;
      if (filters.status === 'preferred' && !op.regle_appliquee) return false;
      
      // Filtre centre
      if (filters.centre && op.centre_de_charge_id !== filters.centre) return false;
      
      // Filtre article
      if (filters.article && op.article_id !== filters.article) return false;
      
      return true;
    });
  }, [diagnostic, filters]);

  // Valeurs uniques pour les filtres
  const uniqueCentres = useMemo(() => {
    if (!diagnostic?.diagnostics_table) return [];
    return [...new Set(diagnostic.diagnostics_table.map(op => op.centre_de_charge_id).filter(Boolean))].sort();
  }, [diagnostic]);

  const uniqueArticles = useMemo(() => {
    if (!diagnostic?.diagnostics_table) return [];
    return [...new Set(diagnostic.diagnostics_table.map(op => op.article_id).filter(Boolean))].sort();
  }, [diagnostic]);

  const clearFilters = () => {
    setFilters({ search: '', status: '', centre: '', article: '' });
  };

  const activeFiltersCount = Object.values(filters).filter(v => v !== '').length;

  if (!diagnostic) {
    return (
      <div className="flex items-center justify-center h-64">
        <div style={{ color: 'var(--text-muted)' }}>Chargement du diagnostic...</div>
      </div>
    );
  }

  const { summary, machines_par_centre, regles_chargees } = diagnostic;

  return (
    <div className="space-y-6" data-testid="diagnostic-page">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Diagnostic d'Assignation</h3>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Jointure order_id → article_id, date_besoin | Critères: tache_id, centre_de_charge_id
          </p>
        </div>
        <button
          onClick={fetchDiagnostic}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
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
              placeholder="Rechercher par opération, OF, article..."
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
          <div className="grid grid-cols-4 gap-4 mt-4 pt-4" style={{ borderTop: '1px solid var(--border-default)' }}>
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
                <option value="assigned">Assignées</option>
                <option value="unassigned">Non assignées</option>
                <option value="preferred">Avec règle</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>Centre de charge</label>
              <select
                value={filters.centre}
                onChange={(e) => setFilters({ ...filters, centre: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-centre"
              >
                <option value="">Tous</option>
                {uniqueCentres.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>Article</label>
              <select
                value={filters.article}
                onChange={(e) => setFilters({ ...filters, article: e.target.value })}
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
            <div className="flex items-end">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {filteredDiagnostics.length} / {diagnostic?.diagnostics_table?.length || 0} opérations
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Résumé */}
      <div className="grid grid-cols-5 gap-4">
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-slate-800">{summary?.total_operations || 0}</div>
          <div className="text-sm text-slate-500">Total</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-green-700">{summary?.assigned || 0}</div>
          <div className="text-sm text-green-600">Assignées</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-red-700">{summary?.unassigned || 0}</div>
          <div className="text-sm text-red-600">Non assignées</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-amber-700">{summary?.preferred || 0}</div>
          <div className="text-sm text-amber-600">Préférées</div>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-purple-700">{summary?.en_retard || 0}</div>
          <div className="text-sm text-purple-600">En retard</div>
        </div>
      </div>

      {/* Causes d'échec */}
      {summary?.failure_causes && Object.keys(summary.failure_causes).length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-sm p-4">
          <h4 className="font-semibold text-red-800 mb-2 flex items-center gap-2">
            <AlertTriangle size={18} />
            Causes d'échec
          </h4>
          <ul className="space-y-1">
            {Object.entries(summary.failure_causes).map(([cause, count]) => (
              <li key={cause} className="text-sm text-red-700">
                <span className="font-mono bg-red-100 px-1 rounded">{cause}</span>: {count} opération(s)
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Machines par Centre */}
      <div className="bg-blue-50 border border-blue-200 rounded-sm p-4">
        <h4 className="font-semibold text-blue-800 mb-3">Index Machines par Centre de Charge</h4>
        {!machines_par_centre || Object.keys(machines_par_centre).length === 0 ? (
          <p className="text-red-600">⚠️ Aucune machine indexée!</p>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(machines_par_centre).map(([centre, machines]) => (
              <div key={centre} className="bg-white rounded-sm p-3 border border-blue-100">
                <div className="font-mono text-sm text-purple-600 font-semibold mb-1">{centre}</div>
                <div className="flex flex-wrap gap-1">
                  {machines.map(m => (
                    <span key={m.id} className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs font-mono">
                      {m.id}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Règles */}
      <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
        <h4 className="font-semibold text-amber-800 mb-3">Règles Métier ({regles_chargees?.length || 0})</h4>
        {!regles_chargees || regles_chargees.length === 0 ? (
          <p className="text-slate-600">Aucune règle configurée.</p>
        ) : (
          <div className="space-y-2">
            {regles_chargees.map((rule, idx) => (
              <div key={idx} className="bg-white rounded-sm p-2 border border-amber-100 text-sm">
                <span className={`font-semibold ${
                  rule.type === 'FORBID' ? 'text-red-600' :
                  rule.type === 'PREFER' ? 'text-amber-600' : 'text-green-600'
                }`}>{rule.type}</span>
                {' '}<span className="text-slate-800">{rule.name}</span>
                <div className="text-xs text-slate-500 mt-1">
                  tache={rule.tache_id || '-'} | centre={rule.centre_de_charge_id || '-'} | article={rule.article_id || '-'} | machine={rule.machine_id}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tableau de diagnostic */}
      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <div className="px-4 py-3" style={{ backgroundColor: 'var(--bg-sunken)', borderBottom: '1px solid var(--border-default)' }}>
          <h4 className="font-semibold" style={{ color: 'var(--text-primary)' }}>Diagnostic par Opération</h4>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Triées par date_besoin (plus urgent en premier) | Jointure via order_id
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead style={{ backgroundColor: 'var(--bg-sunken)' }}>
              <tr>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}></th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Order</th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Article</th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Date Besoin</th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Tâche</th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Centre</th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Machines Centre</th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Règles</th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Machine</th>
                <th className="px-2 py-2 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>OK</th>
              </tr>
            </thead>
            <tbody>
              {filteredDiagnostics.map((row) => {
                const isLate = row.urgency >= 1000;
                const isUrgent = row.urgency >= 500 && row.urgency < 1000;
                return (
                  <React.Fragment key={row.operation_id}>
                    <tr 
                      className="cursor-pointer transition-colors"
                      style={{ 
                        borderBottom: '1px solid var(--border-default)',
                        backgroundColor: !row.is_assigned ? 'var(--status-error-bg)' : 
                                        isLate ? 'rgba(139, 92, 246, 0.1)' :
                                        isUrgent ? 'var(--status-warning-bg)' : 'transparent'
                      }}
                      onClick={() => toggleExpand(row.operation_id)}
                    >
                      <td className="px-2 py-2" style={{ color: 'var(--text-secondary)' }}>
                        {expandedOps[row.operation_id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </td>
                      <td className="px-2 py-2 font-mono text-xs" style={{ color: 'var(--text-primary)' }}>{row.order_id}</td>
                      <td className="px-2 py-2">
                        {row.article_id ? (
                          <span className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: 'var(--status-warning-bg)', color: 'var(--status-warning)' }}>
                            {row.article_id}
                          </span>
                        ) : (
                          <span className="text-xs" style={{ color: 'var(--status-error)' }}>-</span>
                        )}
                      </td>
                      <td className="px-2 py-2">
                        {row.date_besoin ? (
                          <span className="text-xs font-mono flex items-center gap-1" style={{ 
                            color: isLate ? '#8B5CF6' : isUrgent ? 'var(--status-warning)' : 'var(--text-secondary)',
                            fontWeight: isLate || isUrgent ? 'bold' : 'normal'
                          }}>
                            {row.date_besoin?.substring(0, 16).replace('T', ' ')}
                            {isLate && <Clock size={12} />}
                          </span>
                        ) : (
                          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>-</span>
                        )}
                      </td>
                      <td className="px-2 py-2">
                        <span className="px-1.5 py-0.5 rounded text-xs font-mono" style={{ backgroundColor: 'var(--status-info-bg)', color: 'var(--status-info)' }}>
                          {row.tache_id || '-'}
                        </span>
                      </td>
                      <td className="px-2 py-2">
                        <span className="bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded text-xs font-mono">
                          {row.centre_de_charge_id || '-'}
                        </span>
                      </td>
                      <td className="px-2 py-2">
                        {row.machines_du_centre?.length > 0 ? (
                          <span className="text-xs text-slate-600">{row.machines_du_centre.join(', ')}</span>
                        ) : (
                          <span className="text-xs text-red-600 font-semibold">AUCUNE</span>
                        )}
                      </td>
                      <td className="px-2 py-2">
                        <span className="text-xs text-slate-600">
                          {row.regles_applicables?.length || 0}
                        </span>
                      </td>
                      <td className="px-2 py-2">
                        {row.machine_choisie ? (
                          <span className="bg-green-100 text-green-800 px-1.5 py-0.5 rounded text-xs font-mono font-semibold">
                            {row.machine_choisie}
                          </span>
                        ) : (
                          <span className="text-xs text-red-600">-</span>
                        )}
                      </td>
                      <td className="px-2 py-2">
                        {row.is_assigned ? (
                          <CheckCircle size={16} className="text-green-600" />
                        ) : (
                          <XCircle size={16} className="text-red-600" />
                        )}
                      </td>
                    </tr>
                    {expandedOps[row.operation_id] && (
                      <tr className="bg-slate-50">
                        <td colSpan={10} className="px-6 py-3">
                          <div className="grid grid-cols-4 gap-4 text-xs">
                            <div>
                              <div className="font-semibold text-slate-700 mb-1">Jointure order_id:</div>
                              <div className="text-slate-600">
                                {row.ordre_trouve ? (
                                  <span className="text-green-600">✓ Ordre trouvé</span>
                                ) : (
                                  <span className="text-red-600">✗ Ordre non trouvé</span>
                                )}
                              </div>
                              <div className="mt-2 space-y-0.5">
                                <div>order_id: <span className="font-mono">{row.order_id}</span></div>
                                <div>article_id: <span className="font-mono">{row.article_id || '-'}</span></div>
                                <div>date_besoin: <span className="font-mono">{row.date_besoin || '-'}</span></div>
                              </div>
                            </div>
                            <div>
                              <div className="font-semibold text-slate-700 mb-1">Machines interdites (FORBID):</div>
                              {row.machines_interdites?.length > 0 ? (
                                <div className="flex flex-wrap gap-1">
                                  {row.machines_interdites.map(m => (
                                    <span key={m} className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-mono">{m}</span>
                                  ))}
                                </div>
                              ) : <span className="text-slate-400">Aucune</span>}
                              
                              <div className="font-semibold text-slate-700 mb-1 mt-2">Machines préférées (PREFER):</div>
                              {row.machines_preferees?.length > 0 ? (
                                <div className="flex flex-wrap gap-1">
                                  {row.machines_preferees.map(m => (
                                    <span key={m} className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-mono">{m}</span>
                                  ))}
                                </div>
                              ) : <span className="text-slate-400">Aucune</span>}
                            </div>
                            <div>
                              <div className="font-semibold text-slate-700 mb-1">Règles appliquées:</div>
                              {row.regles_applicables?.length > 0 ? (
                                <div className="space-y-0.5">
                                  {row.regles_applicables.map((r, i) => (
                                    <div key={i} className="text-slate-600">{r}</div>
                                  ))}
                                </div>
                              ) : <span className="text-slate-400">Aucune</span>}
                              
                              {row.cause_echec && (
                                <div className="mt-2">
                                  <div className="font-semibold text-red-700 mb-1">CAUSE D'ÉCHEC:</div>
                                  <span className="bg-red-100 text-red-800 px-2 py-1 rounded font-mono">{row.cause_echec}</span>
                                </div>
                              )}
                            </div>
                            <div>
                              <div className="font-semibold text-slate-700 mb-1">Diagnostic Matière:</div>
                              {row.material_status?.components?.length > 0 ? (
                                <div className="space-y-1">
                                  {row.material_status.components.map((comp, i) => (
                                    <div key={i} className={`flex items-center gap-1 ${
                                      comp.is_available ? 'text-green-600' : 'text-red-600'
                                    }`}>
                                      <span>{comp.is_available ? '✓' : '✗'}</span>
                                      <span className="font-mono">{comp.article_id}</span>
                                      <span>({comp.available}/{comp.required})</span>
                                    </div>
                                  ))}
                                  {!row.material_status.all_available && (
                                    <div className="mt-1 text-red-600 font-semibold">
                                      Bloqué: {row.material_status.blocking_components?.join(', ')}
                                    </div>
                                  )}
                                </div>
                              ) : <span className="text-slate-400">Pas de besoins définis</span>}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
              {filteredDiagnostics.length === 0 && (
                <tr>
                  <td colSpan={10} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                    {diagnostic?.diagnostics_table?.length === 0 
                      ? 'Aucune opération. Importez des données via Import CSV.'
                      : 'Aucune opération ne correspond aux filtres.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
