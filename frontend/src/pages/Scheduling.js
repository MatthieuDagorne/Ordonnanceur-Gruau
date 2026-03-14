import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Play, Loader2, AlertTriangle, CheckCircle, Settings2, 
  Clock, Package, Sliders, BarChart3, Zap, Calendar,
  ChevronDown, ChevronUp, Target, Scale, Timer
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PRIORITY_MODES = [
  { 
    value: 'due_date', 
    label: 'Priorité Date de Besoin', 
    description: 'Minimise les retards en priorisant les dates dues',
    icon: Calendar 
  },
  { 
    value: 'material_availability', 
    label: 'Priorité Disponibilité Matière', 
    description: 'Planifie dès que les composants sont disponibles',
    icon: Package 
  },
  { 
    value: 'balanced', 
    label: 'Mode Équilibré', 
    description: 'Optimise selon les poids définis ci-dessous',
    icon: Scale 
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
  const [priorityMode, setPriorityMode] = useState('due_date');
  
  // Poids de priorité (mode équilibré)
  const [dueDateWeight, setDueDateWeight] = useState(100);
  const [materialWeight, setMaterialWeight] = useState(50);
  const [setupTimeWeight, setSetupTimeWeight] = useState(20);
  
  // Contraintes
  const [ignoreRules, setIgnoreRules] = useState(false);
  const [ignoreMaterial, setIgnoreMaterial] = useState(false);
  const [ignoreCalendars, setIgnoreCalendars] = useState(false);
  
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
        priority_mode: priorityMode,
        due_date_weight: dueDateWeight,
        material_weight: materialWeight,
        setup_time_weight: setupTimeWeight,
        ignore_rules: ignoreRules,
        ignore_material: ignoreMaterial,
        ignore_calendars: ignoreCalendars,
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

  const selectedMode = PRIORITY_MODES.find(m => m.value === priorityMode);

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

      {/* Priority Mode Selection */}
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
            Mode de Priorité
          </h4>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          {PRIORITY_MODES.map((mode) => {
            const Icon = mode.icon;
            const isSelected = priorityMode === mode.value;
            return (
              <button
                key={mode.value}
                onClick={() => setPriorityMode(mode.value)}
                data-testid={`priority-mode-${mode.value}`}
                className="p-4 rounded-sm border-2 text-left transition-all hover-lift"
                style={{ 
                  backgroundColor: isSelected ? 'var(--bg-secondary)' : 'var(--surface)',
                  borderColor: isSelected ? 'var(--accent-blue)' : 'var(--border)'
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon size={18} style={{ color: isSelected ? 'var(--accent-blue)' : 'var(--text-muted)' }} />
                  <span 
                    className="font-medium"
                    style={{ color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                  >
                    {mode.label}
                  </span>
                </div>
                <p className="text-xs text-slate-500">{mode.description}</p>
              </button>
            );
          })}
        </div>

        {/* Weight sliders for balanced mode */}
        {priorityMode === 'balanced' && (
          <div className="mt-6 p-4 bg-slate-50 rounded-sm border border-slate-200">
            <h5 className="text-sm font-semibold text-slate-700 mb-4">Poids de Priorité</h5>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">Date de besoin</span>
                  <span className="font-mono font-medium text-slate-900">{dueDateWeight}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={dueDateWeight}
                  onChange={(e) => setDueDateWeight(parseInt(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                  data-testid="due-date-weight"
                />
              </div>
              
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">Disponibilité matière</span>
                  <span className="font-mono font-medium text-slate-900">{materialWeight}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={materialWeight}
                  onChange={(e) => setMaterialWeight(parseInt(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                  data-testid="material-weight"
                />
              </div>
              
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">Minimiser temps de setup</span>
                  <span className="font-mono font-medium text-slate-900">{setupTimeWeight}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={setupTimeWeight}
                  onChange={(e) => setSetupTimeWeight(parseInt(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                  data-testid="setup-weight"
                />
              </div>
            </div>
          </div>
        )}
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
              {/* Contraintes */}
              <div className="space-y-3">
                <h5 className="text-sm font-semibold text-slate-700">Contraintes à Ignorer</h5>
                <p className="text-xs text-slate-500 mb-3">
                  Utilisez ces options pour identifier les causes de blocage
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
                    checked={ignoreMaterial}
                    onChange={(e) => setIgnoreMaterial(e.target.checked)}
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
              
              {/* Options séquence */}
              <div className="space-y-3">
                <h5 className="text-sm font-semibold text-slate-700">Options de Planification</h5>
                
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
            <CheckCircle size={14} className={ignoreMaterial ? "text-slate-300" : "text-green-500"} />
            <span className={ignoreMaterial ? "text-slate-400 line-through" : ""}>Disponibilité matière</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={14} className={ignoreCalendars ? "text-slate-300" : "text-green-500"} />
            <span className={ignoreCalendars ? "text-slate-400 line-through" : ""}>Calendriers machines</span>
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
            <p className="text-slate-300 mb-1">Mode</p>
            <p>{selectedMode?.label}</p>
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
