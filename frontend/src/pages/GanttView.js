import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Download, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function GanttView() {
  const { scenarioId } = useParams();
  const navigate = useNavigate();
  const [scenario, setScenario] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [viewMode, setViewMode] = useState('Day');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchScenario();
  }, [scenarioId]);

  const fetchScenario = async () => {
    try {
      const response = await axios.get(`${API}/scenarios/${scenarioId}`);
      setScenario(response.data);

      if (response.data.schedule_data && response.data.schedule_data.operations) {
        const ganttTasks = convertToGanttTasks(response.data.schedule_data.operations);
        setTasks(ganttTasks);
      }
    } catch (error) {
      console.error('Error fetching scenario:', error);
      toast.error('Erreur de chargement du scénario');
    } finally {
      setLoading(false);
    }
  };

  const convertToGanttTasks = (operations) => {
    const now = new Date();
    
    return operations.map((op) => {
      const startDate = op.start_date ? new Date(op.start_date) : new Date(now.getTime() + op.start_time * 60000);
      const endDate = op.end_date ? new Date(op.end_date) : new Date(now.getTime() + op.end_time * 60000);

      return {
        id: op.operation_id,
        name: `OP ${op.operation_id}`,
        order_id: op.order_id,
        machine_id: op.machine_id,
        start: startDate,
        end: endDate,
        duration: (endDate - startDate) / (1000 * 60), // minutes
        styles: {
          backgroundColor: getColorByMachine(op.machine_id)
        }
      };
    });
  };

  const getColorByMachine = (machineId) => {
    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];
    const hash = machineId ? machineId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) : 0;
    return colors[hash % colors.length];
  };

  const handleExport = async () => {
    try {
      const response = await axios.get(`${API}/export/schedule/${scenarioId}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `schedule_${scenarioId}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      toast.success('Export réussi');
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Erreur lors de l\'export');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-slate-600">Chargement...</p>
      </div>
    );
  }

  if (!scenario) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-slate-600">Scénario introuvable</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            data-testid="back-btn"
            onClick={() => navigate('/scenarios')}
            className="inline-flex items-center gap-2 text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft size={16} />
            Retour
          </button>
          <h3 className="text-2xl font-semibold text-slate-800">{scenario.name}</h3>
        </div>
        <button
          data-testid="export-schedule-btn"
          onClick={handleExport}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
        >
          <Download size={16} />
          Exporter
        </button>
      </div>

      {/* Diagnostic Section */}
      {scenario.schedule_data && scenario.schedule_data.diagnostics && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
          <h4 className="text-lg font-semibold text-slate-800 mb-4">📊 Diagnostic d'Ordonnancement</h4>
          
          {/* Pre-validation */}
          {scenario.schedule_data.diagnostics.pre_validation && (
            <div className="mb-4">
              <h5 className="text-sm font-semibold text-slate-700 mb-2">Validation des Données</h5>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-slate-50 p-3 rounded-sm">
                  <p className="text-xs text-slate-500 mb-1">Ordres</p>
                  <p className="text-lg font-mono font-semibold text-slate-900">
                    {scenario.schedule_data.diagnostics.pre_validation.orders_count}
                  </p>
                </div>
                <div className="bg-slate-50 p-3 rounded-sm">
                  <p className="text-xs text-slate-500 mb-1">Opérations</p>
                  <p className="text-lg font-mono font-semibold text-slate-900">
                    {scenario.schedule_data.diagnostics.pre_validation.operations_count}
                  </p>
                </div>
                <div className="bg-slate-50 p-3 rounded-sm">
                  <p className="text-xs text-slate-500 mb-1">Machines</p>
                  <p className="text-lg font-mono font-semibold text-slate-900">
                    {scenario.schedule_data.diagnostics.pre_validation.machines_count}
                  </p>
                </div>
                <div className="bg-slate-50 p-3 rounded-sm">
                  <p className="text-xs text-slate-500 mb-1">Règles</p>
                  <p className="text-lg font-mono font-semibold text-slate-900">
                    {scenario.schedule_data.diagnostics.pre_validation.rules_count}
                  </p>
                </div>
              </div>
              {scenario.schedule_data.diagnostics.pre_validation.feasible_operations !== undefined && (
                <div className="mt-3 flex gap-4">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-green-600 font-semibold">
                      ✓ {scenario.schedule_data.diagnostics.pre_validation.feasible_operations} planifiables
                    </span>
                  </div>
                  {scenario.schedule_data.diagnostics.pre_validation.blocked_operations > 0 && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-red-600 font-semibold">
                        ✗ {scenario.schedule_data.diagnostics.pre_validation.blocked_operations} bloquées
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Blocking Reasons */}
          {scenario.schedule_data.diagnostics.blocking_reasons && 
           scenario.schedule_data.diagnostics.blocking_reasons.length > 0 && (
            <div className="mb-4">
              <h5 className="text-sm font-semibold text-slate-700 mb-2">⚠️ Causes de Blocage</h5>
              <div className="space-y-2">
                {scenario.schedule_data.diagnostics.blocking_reasons.slice(0, 5).map((reason, idx) => (
                  <div key={idx} className="bg-red-50 border border-red-200 rounded-sm p-3 text-sm">
                    <p className="font-mono text-red-900">
                      {reason.type === 'OPERATION_BLOCKED' && reason.operation_id ? (
                        <>
                          <span className="font-semibold">Op {reason.operation_id}:</span>{' '}
                          {reason.reasons?.join(', ')}
                        </>
                      ) : (
                        <>
                          <span className="font-semibold">{reason.type}:</span> {reason.reason}
                          {reason.solution && <><br /><span className="text-red-700">→ {reason.solution}</span></>}
                        </>
                      )}
                    </p>
                  </div>
                ))}
                {scenario.schedule_data.diagnostics.blocking_reasons.length > 5 && (
                  <p className="text-xs text-slate-500">
                    ... et {scenario.schedule_data.diagnostics.blocking_reasons.length - 5} autre(s) blocage(s)
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Solver Info */}
          {scenario.schedule_data.diagnostics.solver_info && (
            <div>
              <h5 className="text-sm font-semibold text-slate-700 mb-2">🔧 Informations Solveur</h5>
              <div className="bg-slate-50 p-3 rounded-sm font-mono text-xs space-y-1">
                <p>→ Opérations envoyées au solveur: {scenario.schedule_data.diagnostics.solver_info.operations_sent}</p>
                <p>→ Machines utilisées: {scenario.schedule_data.diagnostics.solver_info.machines_used}</p>
                <p>→ Horizon: {scenario.schedule_data.diagnostics.solver_info.horizon_days?.toFixed(1)} jours</p>
                <p>→ Statut: <span className={`font-semibold ${
                  scenario.schedule_data.diagnostics.solver_info.status === 'OPTIMAL' ? 'text-green-600' :
                  scenario.schedule_data.diagnostics.solver_info.status === 'FEASIBLE' ? 'text-blue-600' :
                  'text-red-600'
                }`}>{scenario.schedule_data.diagnostics.solver_info.status}</span></p>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold text-slate-800">Planning Gantt</h4>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('Hour')}
              className={`px-3 py-1 text-sm rounded-sm border transition-colors ${
                viewMode === 'Hour'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
              }`}
            >
              Heure
            </button>
            <button
              onClick={() => setViewMode('Day')}
              className={`px-3 py-1 text-sm rounded-sm border transition-colors ${
                viewMode === 'Day'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
              }`}
            >
              Jour
            </button>
            <button
              onClick={() => setViewMode('Week')}
              className={`px-3 py-1 text-sm rounded-sm border transition-colors ${
                viewMode === 'Week'
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
              }`}
            >
              Semaine
            </button>
          </div>
        </div>

        {tasks.length > 0 ? (
          <div className="gantt-container" data-testid="gantt-chart">
            <div className="space-y-2">
              {tasks.map((task) => (
                <div key={task.id} className="flex items-center gap-4 p-3 bg-slate-50 rounded-sm border border-slate-200">
                  <div className="w-32 font-mono text-sm text-slate-700 flex flex-col">
                    <span className="font-semibold">{task.name}</span>
                    <span className="text-xs text-slate-500">{task.machine_id?.substring(0, 8)}</span>
                  </div>
                  <div className="flex-1 relative h-8 bg-white rounded-sm border border-slate-200 overflow-hidden">
                    <div
                      className="absolute h-full rounded-sm"
                      style={{
                        backgroundColor: task.styles.backgroundColor,
                        left: '10%',
                        width: '30%'
                      }}
                    />
                  </div>
                  <div className="w-48 text-xs font-mono text-slate-600">
                    <div>{task.start.toLocaleString('fr-FR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
                    <div className="text-slate-400">{Math.round(task.duration)} min</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-slate-500">
            <p>Aucune opération planifiée</p>
          </div>
        )}
      </div>

      {scenario.schedule_data && scenario.schedule_data.conflicts && scenario.schedule_data.conflicts.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-5">
          <div className="flex items-start gap-3">
            <AlertCircle size={20} className="text-amber-600 mt-0.5" />
            <div>
              <h4 className="text-lg font-semibold text-amber-900 mb-2">Conflits Détectés</h4>
              <ul className="space-y-1 text-sm text-amber-800">
                {scenario.schedule_data.conflicts.map((conflict, idx) => (
                  <li key={idx} className="font-mono">
                    {conflict.operation_id ? `Op ${conflict.operation_id}: ${conflict.reason}` : JSON.stringify(conflict)}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {scenario.schedule_data && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
          <h4 className="text-lg font-semibold text-slate-800 mb-4">Résultats du Calcul</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Statut</p>
              <p className="text-lg font-mono text-slate-900">{scenario.schedule_data.status}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Opérations planifiées</p>
              <p className="text-lg font-mono text-slate-900">{scenario.schedule_data.operations?.length || 0}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Temps de calcul</p>
              <p className="text-lg font-mono text-slate-900">{scenario.schedule_data.solver_time?.toFixed(2)}s</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
