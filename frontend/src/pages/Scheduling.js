import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Play, Loader2, AlertTriangle, CheckCircle, Database } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Scheduling() {
  const [calculating, setCalculating] = useState(false);
  const [scenarioName, setScenarioName] = useState('');
  const [ignoreRules, setIgnoreRules] = useState(false);
  const [ignoreMaterial, setIgnoreMaterial] = useState(false);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const navigate = useNavigate();

  const handleLoadDemo = async () => {
    setLoadingDemo(true);
    try {
      const response = await axios.post(`${API}/demo/load`);
      toast.success('Données de démonstration chargées');
      console.log('Demo data loaded:', response.data);
    } catch (error) {
      console.error('Demo load error:', error);
      toast.error('Erreur lors du chargement des données de démo');
    } finally {
      setLoadingDemo(false);
    }
  };

  const handleCalculate = async () => {
    if (!scenarioName.trim()) {
      toast.error('Veuillez saisir un nom de scénario');
      return;
    }

    setCalculating(true);

    try {
      // Create scenario
      const scenarioResponse = await axios.post(`${API}/scenarios`, {
        name: scenarioName,
        status: 'calculating',
      });

      const scenarioId = scenarioResponse.data.id;

      // Launch calculation with options
      const calcResponse = await axios.post(`${API}/scheduling/calculate`, {
        scenario_id: scenarioId,
        ignore_rules: ignoreRules,
        ignore_material: ignoreMaterial,
        debug_mode: true
      });

      toast.success('Ordonnancement calculé avec succès');
      
      // Navigate to Gantt view
      navigate(`/gantt/${scenarioId}`);
    } catch (error) {
      console.error('Calculation error:', error);
      toast.error(`Erreur de calcul: ${error.response?.data?.detail || error.message}`);
    } finally {
      setCalculating(false);
    }
  };

  return (
    <div className="space-y-6">
      <h3 className="text-2xl font-semibold text-slate-800">Ordonnancement</h3>

      {/* Demo Data Section */}
      <div className="bg-blue-50 border border-blue-200 rounded-sm p-5">
        <div className="flex items-start gap-3">
          <Database size={24} className="text-blue-600 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-lg font-semibold text-blue-900 mb-2">Données de Démonstration</h4>
            <p className="text-sm text-blue-800 mb-4">
              Testez le système avec un jeu de données minimal : 2 machines, 2 ordres, 3 opérations.
            </p>
            <button
              data-testid="load-demo-btn"
              onClick={handleLoadDemo}
              disabled={loadingDemo}
              className="inline-flex items-center gap-2 bg-blue-600 text-white hover:bg-blue-700 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loadingDemo ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Chargement...
                </>
              ) : (
                <>
                  <Database size={16} />
                  Charger Données Demo
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-6">
        <h4 className="text-xl font-semibold text-slate-800 mb-4">Lancer un Calcul</h4>
        <p className="text-sm text-slate-600 mb-6">
          Le moteur d'ordonnancement va analyser vos ordres de fabrication, vérifier la disponibilité des matériaux,
          appliquer les règles métier et générer un planning optimisé à capacité finie.
        </p>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
              Nom du scénario
            </label>
            <input
              data-testid="scenario-name-input"
              type="text"
              value={scenarioName}
              onChange={(e) => setScenarioName(e.target.value)}
              placeholder="Ex: Planning Semaine 12"
              className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
              disabled={calculating}
            />
          </div>

          {/* Debug Options */}
          <div className="bg-slate-50 border border-slate-200 rounded-sm p-4">
            <h5 className="text-sm font-semibold text-slate-700 mb-3">Options de Debug</h5>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={ignoreRules}
                  onChange={(e) => setIgnoreRules(e.target.checked)}
                  className="rounded border-slate-300"
                  data-testid="ignore-rules-checkbox"
                />
                Ignorer les règles métier
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={ignoreMaterial}
                  onChange={(e) => setIgnoreMaterial(e.target.checked)}
                  className="rounded border-slate-300"
                  data-testid="ignore-material-checkbox"
                />
                Ignorer la disponibilité matière
              </label>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Utilisez ces options pour identifier rapidement si le problème vient des règles ou des données.
            </p>
          </div>

          <button
            data-testid="calculate-schedule-btn"
            onClick={handleCalculate}
            disabled={calculating}
            className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-6 py-3 text-sm font-medium transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {calculating ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Calcul en cours...
              </>
            ) : (
              <>
                <Play size={16} />
                Lancer l'Ordonnancement
              </>
            )}
          </button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-6">
        <h4 className="text-lg font-semibold text-slate-800 mb-3">Contraintes appliquées</h4>
        <div className="space-y-2 text-sm text-slate-600">
          <div className="flex items-start gap-2">
            <CheckCircle size={16} className="text-green-500 mt-0.5" />
            <p>Séquence des opérations respectée</p>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={16} className="text-green-500 mt-0.5" />
            <p>Capacité finie des machines (pas de chevauchement)</p>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={16} className="text-green-500 mt-0.5" />
            <p>Calendriers machines respectés</p>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={16} className="text-green-500 mt-0.5" />
            <p>Compatibilité machine/opération vérifiée</p>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle size={16} className="text-green-500 mt-0.5" />
            <p>Disponibilité matière contrôlée</p>
          </div>
        </div>
      </div>

      <div className="bg-slate-900 text-white rounded-sm shadow-sm p-6">
        <h4 className="text-lg font-semibold mb-3 font-mono">Moteur d'Optimisation</h4>
        <p className="text-sm font-mono text-slate-300 mb-2">Google OR-Tools CP-SAT Solver</p>
        <div className="text-xs font-mono text-slate-400 space-y-1">
          <p>→ Constraint Programming</p>
          <p>→ Finite Capacity Scheduling</p>
          <p>→ Makespan Minimization</p>
          <p>→ Full Diagnostics Mode</p>
        </div>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-sm p-5">
        <div className="flex items-start gap-3">
          <AlertTriangle size={20} className="text-amber-600 mt-0.5" />
          <div>
            <h4 className="text-lg font-semibold text-amber-900 mb-2">Mode Diagnostic Activé</h4>
            <p className="text-sm text-amber-800">
              Le système génère maintenant des logs détaillés pour identifier pourquoi certaines opérations ne peuvent pas être planifiées.
              Consultez les logs backend et la vue Gantt pour voir les raisons de blocage.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}