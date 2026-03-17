import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Eye, Trash2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Scenarios() {
  const [scenarios, setScenarios] = useState([]);
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false);
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

  const deleteScenario = async (id, name) => {
    if (!window.confirm(`Supprimer le scénario "${name}" ?`)) return;
    
    try {
      await axios.delete(`${API}/scenarios/${id}`);
      toast.success(`Scénario "${name}" supprimé`);
      fetchScenarios();
    } catch (error) {
      console.error('Error deleting scenario:', error);
      toast.error('Erreur lors de la suppression');
    }
  };

  const deleteAllScenarios = async () => {
    try {
      const response = await axios.delete(`${API}/scenarios`);
      toast.success(response.data.message || 'Tous les scénarios ont été supprimés');
      setShowDeleteAllConfirm(false);
      fetchScenarios();
    } catch (error) {
      console.error('Error deleting all scenarios:', error);
      toast.error('Erreur lors de la suppression');
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'calculating':
        return 'bg-blue-100 text-blue-700';
      case 'error':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-semibold text-slate-800">Scénarios</h3>
        {scenarios.length > 0 && (
          <button
            data-testid="delete-all-scenarios-btn"
            onClick={() => setShowDeleteAllConfirm(true)}
            className="flex items-center gap-2 px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors text-sm"
          >
            <Trash2 size={16} />
            Tout supprimer ({scenarios.length})
          </button>
        )}
      </div>

      {/* Modal de confirmation */}
      {showDeleteAllConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle size={24} className="text-red-600" />
              <h4 className="text-lg font-semibold text-slate-800">Confirmer la suppression</h4>
            </div>
            <p className="text-slate-600 mb-6">
              Êtes-vous sûr de vouloir supprimer <strong>tous les {scenarios.length} scénarios</strong> ? 
              Cette action est irréversible.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteAllConfirm(false)}
                className="px-4 py-2 border border-slate-300 rounded-md hover:bg-slate-50 transition-colors"
              >
                Annuler
              </button>
              <button
                data-testid="confirm-delete-all-btn"
                onClick={deleteAllScenarios}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
              >
                Supprimer tout
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
        <p className="text-sm text-slate-600 mb-4">
          Chaque scénario représente un calcul d'ordonnancement indépendant. Vous pouvez comparer plusieurs scénarios
          avant de valider celui qui vous convient.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Créé le</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Statut</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((scenario) => (
              <tr key={scenario.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors" data-testid="scenario-row">
                <td className="px-4 py-2 text-sm text-slate-700 font-mono">{scenario.name}</td>
                <td className="px-4 py-2 text-sm text-slate-700 font-mono">
                  {new Date(scenario.created_at).toLocaleString('fr-FR')}
                </td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(scenario.status)}`}>
                    {scenario.status}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <button
                      data-testid="view-scenario-btn"
                      onClick={() => navigate(`/gantt/${scenario.id}`)}
                      className="text-blue-600 hover:text-blue-800 transition-colors"
                      title="Voir le Gantt"
                    >
                      <Eye size={16} />
                    </button>
                    <button
                      data-testid="delete-scenario-btn"
                      onClick={() => deleteScenario(scenario.id, scenario.name)}
                      className="text-red-600 hover:text-red-800 transition-colors"
                      title="Supprimer"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {scenarios.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm text-slate-500">
                  Aucun scénario. Lancez un calcul depuis la section Ordonnancement.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}