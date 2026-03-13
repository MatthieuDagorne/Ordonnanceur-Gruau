import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Eye, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Scenarios() {
  const [scenarios, setScenarios] = useState([]);
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
      </div>

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