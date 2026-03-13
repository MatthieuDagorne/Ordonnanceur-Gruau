import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Play, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Scheduling() {
  const [calculating, setCalculating] = useState(false);
  const [scenarioName, setScenarioName] = useState('');
  const navigate = useNavigate();

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

      // Launch calculation
      const calcResponse = await axios.post(`${API}/scheduling/calculate`, {
        scenario_id: scenarioId,
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
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5"></div>
            <p>Séquence des opérations respectée</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5"></div>
            <p>Capacité finie des machines (pas de chevauchement)</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5"></div>
            <p>Calendriers machines respectés</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5"></div>
            <p>Compatibilité machine/opération vérifiée</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5"></div>
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
        </div>
      </div>
    </div>
  );
}