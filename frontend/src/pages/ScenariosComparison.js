import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Eye, Trash2, GitCompare, CheckCircle, Trophy, Clock, AlertTriangle, X } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ScenariosComparison() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [showComparison, setShowComparison] = useState(false);
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchScenarios();
  }, []);

  const fetchScenarios = async () => {
    try {
      const response = await axios.get(`${API}/scenarios`);
      setScenarios(response.data);
    } catch (error) {
      console.error('Error fetching scenarios:', error);
      toast.error('Erreur lors du chargement des scénarios');
    }
  };

  const handleSelect = (scenarioId) => {
    if (selectedIds.includes(scenarioId)) {
      setSelectedIds(selectedIds.filter(id => id !== scenarioId));
    } else {
      setSelectedIds([...selectedIds, scenarioId]);
    }
  };

  const handleCompare = async () => {
    if (selectedIds.length < 2) {
      toast.error('Sélectionnez au moins 2 scénarios');
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.get(`${API}/scenarios/compare`, {
        params: { ids: selectedIds.join(',') }
      });
      setComparison(response.data);
      setShowComparison(true);
    } catch (error) {
      console.error('Error comparing:', error);
      toast.error('Erreur lors de la comparaison');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (scenarioId) => {
    if (!window.confirm('Supprimer ce scénario ?')) return;
    
    try {
      await axios.delete(`${API}/scenarios/${scenarioId}`);
      setScenarios(scenarios.filter(s => s.id !== scenarioId));
      setSelectedIds(selectedIds.filter(id => id !== scenarioId));
      toast.success('Scénario supprimé');
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const handleDeleteAll = async () => {
    try {
      const response = await axios.delete(`${API}/scenarios`);
      toast.success(response.data.message || 'Tous les scénarios ont été supprimés');
      setShowDeleteAllConfirm(false);
      setScenarios([]);
      setSelectedIds([]);
    } catch (error) {
      console.error('Error deleting all scenarios:', error);
      toast.error('Erreur lors de la suppression');
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'optimal':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'feasible':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
      case 'completed':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
      case 'error':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400';
    }
  };

  const isBest = (scenarioId, criterion) => {
    return comparison?.best?.[criterion] === scenarioId;
  };

  return (
    <div className="space-y-6" data-testid="scenarios-page">
      {/* Modal de confirmation suppression */}
      {showDeleteAllConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="rounded-lg p-6 max-w-md w-full mx-4 shadow-xl" style={{ backgroundColor: 'var(--bg-elevated)' }}>
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle size={24} className="text-red-500" />
              <h4 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Confirmer la suppression</h4>
            </div>
            <p style={{ color: 'var(--text-secondary)' }} className="mb-6">
              Êtes-vous sûr de vouloir supprimer <strong>tous les {scenarios.length} scénarios</strong> ? 
              Cette action est irréversible.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteAllConfirm(false)}
                className="px-4 py-2 rounded-lg transition-colors"
                style={{ border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}
              >
                Annuler
              </button>
              <button
                data-testid="confirm-delete-all-btn"
                onClick={handleDeleteAll}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Supprimer tout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Scénarios d'Ordonnancement
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Comparez plusieurs scénarios pour choisir le meilleur
          </p>
        </div>
        <div className="flex items-center gap-3">
          {scenarios.length > 0 && (
            <button
              data-testid="delete-all-scenarios-btn"
              onClick={() => setShowDeleteAllConfirm(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
            >
              <Trash2 size={16} />
              Tout supprimer ({scenarios.length})
            </button>
          )}
          {selectedIds.length >= 2 && (
            <button
              onClick={handleCompare}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
              style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
              data-testid="compare-btn"
            >
              <GitCompare size={16} />
              Comparer ({selectedIds.length})
            </button>
          )}
        </div>
      </div>

      {/* Info Card */}
      <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Chaque scénario représente un calcul d'ordonnancement indépendant. 
          Sélectionnez plusieurs scénarios pour les comparer et identifier le meilleur.
        </p>
      </div>

      {/* Scenarios List */}
      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <table className="w-full">
          <thead style={{ backgroundColor: 'var(--bg-sunken)' }}>
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                <input
                  type="checkbox"
                  onChange={() => {
                    if (selectedIds.length === scenarios.length) {
                      setSelectedIds([]);
                    } else {
                      setSelectedIds(scenarios.map(s => s.id));
                    }
                  }}
                  checked={selectedIds.length === scenarios.length && scenarios.length > 0}
                  className="rounded"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Créé le</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Statut</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Opérations</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((scenario) => (
              <tr key={scenario.id} 
                  className={`transition-colors ${selectedIds.includes(scenario.id) ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                  style={{ borderBottom: '1px solid var(--border-default)' }}
                  data-testid="scenario-row">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(scenario.id)}
                    onChange={() => handleSelect(scenario.id)}
                    className="rounded"
                    data-testid={`select-${scenario.id}`}
                  />
                </td>
                <td className="px-4 py-3">
                  <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>
                    {scenario.name}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>
                    {new Date(scenario.created_at).toLocaleString('fr-FR')}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-lg text-xs font-medium ${getStatusColor(scenario.status || scenario.schedule_data?.status)}`}>
                    {scenario.status || scenario.schedule_data?.status || 'N/A'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>
                    {scenario.schedule_data?.operations?.length || 0}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/gantt/${scenario.id}`)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-blue-100 dark:hover:bg-blue-900/30"
                      title="Voir le Gantt"
                      data-testid={`view-${scenario.id}`}
                    >
                      <Eye size={16} className="text-blue-600" />
                    </button>
                    <button
                      onClick={() => handleDelete(scenario.id)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-red-100 dark:hover:bg-red-900/30"
                      title="Supprimer"
                      data-testid={`delete-${scenario.id}`}
                    >
                      <Trash2 size={16} className="text-red-600" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {scenarios.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                  Aucun scénario. Lancez un calcul depuis la section Ordonnancement.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Comparison Modal */}
      {showComparison && comparison && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="w-full max-w-4xl max-h-[80vh] overflow-auto rounded-lg p-6" 
               style={{ backgroundColor: 'var(--bg-elevated)' }}
               data-testid="comparison-modal">
            {/* Modal Header */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
                Comparaison de {comparison.comparison_count} Scénarios
              </h2>
              <button
                onClick={() => setShowComparison(false)}
                className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X size={20} />
              </button>
            </div>

            {/* Best Indicators */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="p-3 rounded-lg text-center" style={{ backgroundColor: 'var(--status-success-bg)', border: '1px solid var(--status-success-border)' }}>
                <Trophy size={20} className="mx-auto mb-1" style={{ color: 'var(--status-success)' }} />
                <p className="text-xs font-medium" style={{ color: 'var(--status-success)' }}>Moins de conflits</p>
                <p className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                  {scenarios.find(s => s.id === comparison.best?.least_conflicts)?.name || '-'}
                </p>
              </div>
              <div className="p-3 rounded-lg text-center" style={{ backgroundColor: 'var(--status-info-bg)', border: '1px solid var(--status-info-border)' }}>
                <Clock size={20} className="mx-auto mb-1" style={{ color: 'var(--status-info)' }} />
                <p className="text-xs font-medium" style={{ color: 'var(--status-info)' }}>Plus court</p>
                <p className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                  {scenarios.find(s => s.id === comparison.best?.shortest_makespan)?.name || '-'}
                </p>
              </div>
              <div className="p-3 rounded-lg text-center" style={{ backgroundColor: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)' }}>
                <AlertTriangle size={20} className="mx-auto mb-1" style={{ color: 'var(--status-warning)' }} />
                <p className="text-xs font-medium" style={{ color: 'var(--status-warning)' }}>Moins de retards</p>
                <p className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                  {scenarios.find(s => s.id === comparison.best?.least_late)?.name || '-'}
                </p>
              </div>
              <div className="p-3 rounded-lg text-center" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
                <CheckCircle size={20} className="mx-auto mb-1" style={{ color: 'var(--brand-primary)' }} />
                <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Plus rapide</p>
                <p className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                  {scenarios.find(s => s.id === comparison.best?.fastest_solve)?.name || '-'}
                </p>
              </div>
            </div>

            {/* Comparison Table */}
            <div className="rounded-lg overflow-hidden" style={{ border: '1px solid var(--border-default)' }}>
              <table className="w-full">
                <thead style={{ backgroundColor: 'var(--bg-sunken)' }}>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Métrique</th>
                    {comparison.scenarios?.map(s => (
                      <th key={s.scenario_id} className="px-4 py-3 text-center text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>
                        {s.scenario_name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                    <td className="px-4 py-3 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Opérations planifiées</td>
                    {comparison.scenarios?.map(s => (
                      <td key={s.scenario_id} className="px-4 py-3 text-center font-mono">
                        {s.metrics?.operations_scheduled}
                      </td>
                    ))}
                  </tr>
                  <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                    <td className="px-4 py-3 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Conflits</td>
                    {comparison.scenarios?.map(s => (
                      <td key={s.scenario_id} className={`px-4 py-3 text-center font-mono ${isBest(s.scenario_id, 'least_conflicts') ? 'text-green-600 font-bold' : ''}`}>
                        {s.metrics?.conflicts}
                        {isBest(s.scenario_id, 'least_conflicts') && <Trophy size={14} className="inline ml-1" />}
                      </td>
                    ))}
                  </tr>
                  <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                    <td className="px-4 py-3 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Makespan (heures)</td>
                    {comparison.scenarios?.map(s => (
                      <td key={s.scenario_id} className={`px-4 py-3 text-center font-mono ${isBest(s.scenario_id, 'shortest_makespan') ? 'text-blue-600 font-bold' : ''}`}>
                        {s.metrics?.makespan_hours}h
                        {isBest(s.scenario_id, 'shortest_makespan') && <Trophy size={14} className="inline ml-1" />}
                      </td>
                    ))}
                  </tr>
                  <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                    <td className="px-4 py-3 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Retards</td>
                    {comparison.scenarios?.map(s => (
                      <td key={s.scenario_id} className={`px-4 py-3 text-center font-mono ${isBest(s.scenario_id, 'least_late') ? 'text-amber-600 font-bold' : ''}`}>
                        {s.metrics?.late_operations}
                        {isBest(s.scenario_id, 'least_late') && <Trophy size={14} className="inline ml-1" />}
                      </td>
                    ))}
                  </tr>
                  <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                    <td className="px-4 py-3 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Machines utilisées</td>
                    {comparison.scenarios?.map(s => (
                      <td key={s.scenario_id} className="px-4 py-3 text-center font-mono">
                        {s.metrics?.machines_used}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Temps de calcul</td>
                    {comparison.scenarios?.map(s => (
                      <td key={s.scenario_id} className={`px-4 py-3 text-center font-mono ${isBest(s.scenario_id, 'fastest_solve') ? 'text-purple-600 font-bold' : ''}`}>
                        {s.metrics?.solver_time?.toFixed(2)}s
                        {isBest(s.scenario_id, 'fastest_solve') && <Trophy size={14} className="inline ml-1" />}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Close Button */}
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowComparison(false)}
                className="px-4 py-2 rounded-lg font-medium"
                style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-primary)' }}
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
