import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Play, Loader2, AlertTriangle, CheckCircle, Settings2, 
  Clock, Package, Sliders, BarChart3, Zap, Calendar,
  ChevronDown, ChevronUp, Target, Scale, Timer, FastForward, Rewind
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Nouvelle configuration: 2 stratégies de planification
const SCHEDULING_STRATEGIES = [
  { 
    value: 'ASAP', 
    label: 'Au plus tôt', 
    description: 'Planifie les opérations dès que possible, en respectant les contraintes',
    icon: FastForward,
    color: '#3B82F6'  // blue
  },
  { 
    value: 'JIT', 
    label: 'Au plus tard (Juste-à-temps)', 
    description: 'Planifie le plus tard possible tout en respectant les dates de besoin',
    icon: Rewind,
    color: '#8B5CF6'  // purple
  }
];

const SOLVER_TIMES = [
  { value: 30, label: '30 secondes' },
  { value: 60, label: '1 minute' },
  { value: 120, label: '2 minutes' },
  { value: 300, label: '5 minutes' },
  { value: 600, label: '10 minutes' },
];

export default function Scheduling() {
  const [calculating, setCalculating] = useState(false);
  const [stats, setStats] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const navigate = useNavigate();

  // Paramètres du scénario
  const [scenarioName, setScenarioName] = useState('');
  const [schedulingStrategy, setSchedulingStrategy] = useState('ASAP');
  
  // Contraintes - Options d'ignorance
  const [ignoreRules, setIgnoreRules] = useState(false);
  const [ignoreMaterial, setIgnoreMaterial] = useState(false);
  const [ignoreCalendars, setIgnoreCalendars] = useState(false);
  const [ignorePriorities, setIgnorePriorities] = useState(false);
  
  // Propagations
  const [ignoreMaterialPropagation, setIgnoreMaterialPropagation] = useState(false);
  const [ignorePriorityPropagation, setIgnorePriorityPropagation] = useState(false);
  
  // Paramètres solveur
  const [maxSolverTime, setMaxSolverTime] = useState(60);
  const [optimizationGap, setOptimizationGap] = useState(5);
  
  // Options avancées
  const [respectSequence, setRespectSequence] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/data/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleCalculate = async () => {
    if (!scenarioName.trim()) {
      toast.error('Veuillez saisir un nom de scénario');
      return;
    }

    if (stats?.operations === 0) {
      toast.error('Aucune opération à planifier. Importez des données.');
      return;
    }

    setCalculating(true);

    try {
      // Lancer le calcul avec toutes les options
      const response = await axios.post(`${API}/scheduling/calculate`, {
        scenario_name: scenarioName,
        scheduling_strategy: schedulingStrategy,
        // Options d'ignorance
        ignore_rules: ignoreRules,
        ignore_material: ignoreMaterial,
        ignore_calendars: ignoreCalendars,
        ignore_priorities: ignorePriorities,
        // Propagations (désactivées si option parente ignorée)
        ignore_material_propagation: ignoreMaterial ? true : ignoreMaterialPropagation,
        ignore_priority_propagation: ignorePriorities ? true : ignorePriorityPropagation,
        // Paramètres solveur
        max_solver_time_seconds: maxSolverTime,
        optimization_gap: optimizationGap / 100,
        respect_sequence: respectSequence,
        debug_mode: true,
        auto_assign_machines: true
      });

      const result = response.data.result;
      const scenarioId = response.data.scenario_id;
      
      if (result?.status === 'OPTIMAL' || result?.status === 'FEASIBLE') {
        toast.success(`Ordonnancement ${result.status}: ${result.operations?.length || 0} opérations planifiées`);
        navigate(`/gantt/${scenarioId}`);
      } else {
        toast.warning(`Résultat: ${result?.status || 'Inconnu'}`);
        navigate(`/scenarios`);
      }
    } catch (error) {
      console.error('Calculation error:', error);
      toast.error(`Erreur de calcul: ${error.response?.data?.detail || error.message}`);
    } finally {
      setCalculating(false);
    }
  };

  const selectedStrategy = SCHEDULING_STRATEGIES.find(s => s.value === schedulingStrategy);

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 
            className="text-2xl font-semibold"
            style={{ color: 'var(--text-primary)', fontFamily: 'Chivo, sans-serif' }}
          >
            Ordonnancement APS
          </h3>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Advanced Planning & Scheduling - Capacité finie
          </p>
        </div>
        {stats && (
          <div className="flex gap-4 text-sm">
            <div 
              className="px-3 py-1.5 rounded-sm"
              style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
            >
              <span style={{ color: 'var(--text-muted)' }}>Ordres:</span>{' '}
              <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.manufacturing_orders}</span>
            </div>
            <div 
              className="px-3 py-1.5 rounded-sm"
              style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
            >
              <span style={{ color: 'var(--text-muted)' }}>Opérations:</span>{' '}
              <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.operations}</span>
            </div>
          </div>
        )}
      </div>

      {/* Scénario Name */}
      <div 
        className="card p-5 animate-fade-in-up stagger-1"
        style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}
      >
        <label 
          className="text-xs font-semibold uppercase tracking-wider block mb-2"
          style={{ color: 'var(--text-muted)' }}
        >
          Nom du Scénario *
        </label>
        <input
          data-testid="scenario-name-input"
          type="text"
          value={scenarioName}
          onChange={(e) => setScenarioName(e.target.value)}
          placeholder="Ex: Planning Semaine 12 - Priorité dates"
          className="input w-full h-10 rounded-sm px-3 py-1 text-sm transition-colors"
          style={{ 
            backgroundColor: 'var(--surface)', 
            borderColor: 'var(--border)',
            color: 'var(--text-primary)'
          }}
          disabled={calculating}
        />
      </div>

      {/* Stratégie de Planification */}
      <div 
        className="card p-5 animate-fade-in-up stagger-2"
        style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-2 mb-4">
          <Target size={18} style={{ color: 'var(--text-secondary)' }} />
          <h4 
            className="text-lg font-semibold"
            style={{ color: 'var(--text-primary)', fontFamily: 'Chivo, sans-serif' }}
          >
            Stratégie de Planification
          </h4>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          {SCHEDULING_STRATEGIES.map((strategy) => {
            const Icon = strategy.icon;
            const isSelected = schedulingStrategy === strategy.value;
            return (
              <button
                key={strategy.value}
                onClick={() => setSchedulingStrategy(strategy.value)}
                data-testid={`strategy-${strategy.value}`}
                className="p-4 rounded-lg border-2 text-left transition-all hover:scale-[1.02]"
                style={{ 
                  backgroundColor: isSelected ? 'var(--bg-secondary)' : 'var(--surface)',
                  borderColor: isSelected ? strategy.color : 'var(--border)'
                }}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div 
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: isSelected ? strategy.color : 'var(--bg-elevated)' }}
                  >
                    <Icon size={20} style={{ color: isSelected ? 'white' : 'var(--text-muted)' }} />
                  </div>
                  <span 
                    className="font-semibold text-base"
                    style={{ color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                  >
                    {strategy.label}
                  </span>
                </div>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{strategy.description}</p>
                
                {/* Info supplémentaire pour JIT */}
                {strategy.value === 'JIT' && (
                  <div className="mt-3 p-2 rounded text-xs" style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-muted)' }}>
                    <strong>Avantages :</strong> Limite les encours, réduit les entrées en stock anticipées
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Solver Settings */}
      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <Timer size={18} className="text-slate-700" />
          <h4 className="text-lg font-semibold text-slate-800">Paramètres du Solveur</h4>
        </div>
        
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
              Durée Maximum d'Optimisation
            </label>
            <select
              value={maxSolverTime}
              onChange={(e) => setMaxSolverTime(parseInt(e.target.value))}
              className="w-full h-10 rounded-sm border border-slate-300 bg-white px-3 py-1 text-sm"
              data-testid="max-solver-time"
            >
              {SOLVER_TIMES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <p className="text-xs text-slate-500 mt-1">
              Le solveur retourne la meilleure solution trouvée dans ce délai
            </p>
          </div>
          
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
              Gap d'Optimalité Acceptable
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="1"
                max="20"
                value={optimizationGap}
                onChange={(e) => setOptimizationGap(parseInt(e.target.value))}
                className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                data-testid="optimization-gap"
              />
              <span className="font-mono font-medium text-slate-900 w-12 text-right">{optimizationGap}%</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Arrête si la solution est à moins de {optimizationGap}% de l'optimum
            </p>
          </div>
        </div>
      </div>

      {/* Advanced Options Toggle */}
      <div className="bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full px-5 py-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
          data-testid="advanced-options-toggle"
        >
          <div className="flex items-center gap-2">
            <Settings2 size={18} className="text-slate-700" />
            <span className="font-semibold text-slate-800">Options Avancées</span>
          </div>
          {showAdvanced ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        
        {showAdvanced && (
          <div className="px-5 pb-5 border-t border-slate-200 pt-4">
            <div className="grid grid-cols-2 gap-6">
              {/* Contraintes à ignorer */}
              <div className="space-y-3">
                <h5 className="text-sm font-semibold text-slate-700">Contraintes à Ignorer</h5>
                <p className="text-xs text-slate-500 mb-3">
                  Désactivez ces contraintes pour identifier les causes de blocage
                </p>
                
                <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={ignoreRules}
                    onChange={(e) => setIgnoreRules(e.target.checked)}
                    className="rounded border-slate-300"
                    data-testid="ignore-rules-checkbox"
                  />
                  Ignorer les règles métier
                </label>
                
                <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={ignorePriorities}
                    onChange={(e) => {
                      setIgnorePriorities(e.target.checked);
                      // Si on ignore les priorités, on désactive aussi la propagation
                      if (e.target.checked) setIgnorePriorityPropagation(true);
                    }}
                    className="rounded border-slate-300"
                    data-testid="ignore-priorities-checkbox"
                  />
                  Ignorer les priorités des OF
                </label>
                
                <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={ignoreMaterial}
                    onChange={(e) => {
                      setIgnoreMaterial(e.target.checked);
                      // Si on ignore la matière, on désactive aussi la propagation
                      if (e.target.checked) setIgnoreMaterialPropagation(true);
                    }}
                    className="rounded border-slate-300"
                    data-testid="ignore-material-checkbox"
                  />
                  Ignorer la disponibilité matière
                </label>
                
                <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={ignoreCalendars}
                    onChange={(e) => setIgnoreCalendars(e.target.checked)}
                    className="rounded border-slate-300"
                    data-testid="ignore-calendars-checkbox"
                  />
                  Ignorer les calendriers machines
                </label>
              </div>
              
              {/* Propagations et Options */}
              <div className="space-y-3">
                <h5 className="text-sm font-semibold text-slate-700">Propagations</h5>
                <p className="text-xs text-slate-500 mb-3">
                  Ces propagations créent des dépendances entre ordres de fabrication
                </p>
                
                <label className={`flex items-center gap-2 text-sm cursor-pointer ${ignorePriorities ? 'text-slate-400' : 'text-slate-600'}`}>
                  <input
                    type="checkbox"
                    checked={ignorePriorityPropagation}
                    onChange={(e) => setIgnorePriorityPropagation(e.target.checked)}
                    disabled={ignorePriorities}
                    className="rounded border-slate-300 disabled:opacity-50"
                    data-testid="ignore-priority-propagation-checkbox"
                  />
                  Ignorer la propagation de priorité vers fournisseurs
                  {ignorePriorities && <span className="text-xs text-slate-400 ml-1">(désactivé)</span>}
                </label>
                
                <label className={`flex items-center gap-2 text-sm cursor-pointer ${ignoreMaterial ? 'text-slate-400' : 'text-slate-600'}`}>
                  <input
                    type="checkbox"
                    checked={ignoreMaterialPropagation}
                    onChange={(e) => setIgnoreMaterialPropagation(e.target.checked)}
                    disabled={ignoreMaterial}
                    className="rounded border-slate-300 disabled:opacity-50"
                    data-testid="ignore-material-propagation-checkbox"
                  />
                  Ignorer la propagation matière (dépendances)
                  {ignoreMaterial && <span className="text-xs text-slate-400 ml-1">(désactivé)</span>}
                </label>
                
                <div className="border-t border-slate-200 pt-3 mt-3">
                  <h5 className="text-sm font-semibold text-slate-700 mb-2">Options de Planification</h5>
                  <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={respectSequence}
                      onChange={(e) => setRespectSequence(e.target.checked)}
                      className="rounded border-slate-300"
                      data-testid="respect-sequence-checkbox"
                    />
                    Respecter l'ordre des opérations dans l'OF
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Contraintes appliquées */}
      <div className="bg-slate-50 border border-slate-200 rounded-sm p-5">
        <h4 className="text-sm font-semibold text-slate-700 mb-3">Contraintes Appliquées</h4>
        <div className="grid grid-cols-2 gap-3 text-sm text-slate-600">
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className={ignoreRules ? "text-slate-300" : "text-green-500"} />
            <span className={ignoreRules ? "text-slate-400 line-through" : ""}>Règles métier d'affectation</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className={ignorePriorities ? "text-slate-300" : "text-green-500"} />
            <span className={ignorePriorities ? "text-slate-400 line-through" : ""}>Priorités des OF</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className={ignoreMaterial ? "text-slate-300" : "text-green-500"} />
            <span className={ignoreMaterial ? "text-slate-400 line-through" : ""}>Disponibilité matière</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className={ignoreCalendars ? "text-slate-300" : "text-green-500"} />
            <span className={ignoreCalendars ? "text-slate-400 line-through" : ""}>Calendriers machines</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className={(ignorePriorities || ignorePriorityPropagation) ? "text-slate-300" : "text-green-500"} />
            <span className={(ignorePriorities || ignorePriorityPropagation) ? "text-slate-400 line-through" : ""}>Propagation priorité</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className={(ignoreMaterial || ignoreMaterialPropagation) ? "text-slate-300" : "text-green-500"} />
            <span className={(ignoreMaterial || ignoreMaterialPropagation) ? "text-slate-400 line-through" : ""}>Propagation matière</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className="text-green-500" />
            <span>Capacité finie (non-chevauchement)</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className={respectSequence ? "text-green-500" : "text-slate-300"} />
            <span className={!respectSequence ? "text-slate-400 line-through" : ""}>Séquence des gammes</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className="text-green-500" />
            <span>production_time + setup_time</span>
          </div>
        </div>
      </div>

      {/* Launch Button */}
      <div className="flex items-center gap-4">
        <button
          data-testid="calculate-schedule-btn"
          onClick={handleCalculate}
          disabled={calculating || !scenarioName.trim()}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-8 py-3 text-sm font-medium transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {calculating ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Calcul en cours...
            </>
          ) : (
            <>
              <Zap size={18} />
              Lancer l'Ordonnancement
            </>
          )}
        </button>
        
        {calculating && (
          <div className="text-sm text-slate-500">
            Durée max: {SOLVER_TIMES.find(t => t.value === maxSolverTime)?.label}
          </div>
        )}
      </div>

      {/* Engine Info */}
      <div className="bg-slate-900 text-white rounded-sm shadow-sm p-5">
        <div className="flex items-center gap-3 mb-3">
          <BarChart3 size={20} />
          <h4 className="text-lg font-semibold font-mono">Moteur OR-Tools CP-SAT</h4>
        </div>
        <div className="grid grid-cols-4 gap-4 text-xs font-mono text-slate-400">
          <div>
            <p className="text-slate-300 mb-1">Stratégie</p>
            <p>{selectedStrategy?.label || 'Au plus tôt'}</p>
          </div>
          <div>
            <p className="text-slate-300 mb-1">Temps max</p>
            <p>{maxSolverTime}s</p>
          </div>
          <div>
            <p className="text-slate-300 mb-1">Gap</p>
            <p>{optimizationGap}%</p>
          </div>
          <div>
            <p className="text-slate-300 mb-1">Opérations</p>
            <p>{stats?.operations || 0}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
