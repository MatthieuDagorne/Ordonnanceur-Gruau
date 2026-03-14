import { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, Trash2, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const importTypes = [
  { key: 'manufacturing-orders', label: 'Ordres de Fabrication', testId: 'import-orders' },
  { key: 'operations', label: 'Opérations', testId: 'import-operations' },
  { key: 'articles', label: 'Articles', testId: 'import-articles' },
  { key: 'stocks', label: 'Stocks', testId: 'import-stocks' },
];

export default function ImportData() {
  const [uploading, setUploading] = useState({});
  const [stats, setStats] = useState(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetting, setResetting] = useState(false);

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

  const handleFileUpload = async (type, file) => {
    if (!file) return;

    setUploading((prev) => ({ ...prev, [type]: true }));

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/import/${type}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.data.success) {
        const message = response.data.previous_records > 0
          ? `Import réussi: ${response.data.records_imported} enregistrements (${response.data.previous_records} anciens remplacés)`
          : `Import réussi: ${response.data.records_imported} enregistrements`;
        
        toast.success(message);
        fetchStats(); // Refresh stats
      } else {
        if (response.data.duplicates_found > 0) {
          toast.error(`${response.data.duplicates_found} ID(s) en double trouvés dans le fichier CSV`);
        } else {
          toast.error(`Erreur d'import: ${response.data.message}`);
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      toast.error(`Erreur d'import: ${error.message}`);
    } finally {
      setUploading((prev) => ({ ...prev, [type]: false }));
    }
  };

  const handleReset = async () => {
    setResetting(true);
    try {
      const response = await axios.post(`${API}/data/reset`);
      
      if (response.data.success) {
        toast.success(
          `Données supprimées: ${response.data.deleted.orders} ordres, ${response.data.deleted.operations} opérations, ${response.data.deleted.scenarios} scénarios`
        );
        setShowResetConfirm(false);
        fetchStats(); // Refresh stats
      } else {
        toast.error('Erreur lors du reset');
      }
    } catch (error) {
      console.error('Reset error:', error);
      toast.error(`Erreur: ${error.message}`);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Data Statistics */}
      {stats && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-slate-800">État des Données</h3>
            <button
              data-testid="reset-data-btn"
              onClick={() => setShowResetConfirm(true)}
              className="inline-flex items-center gap-2 bg-red-600 text-white hover:bg-red-700 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
            >
              <Trash2 size={16} />
              Reset Données ERP
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-50 p-4 rounded-sm border border-slate-200">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Ordres Fab.
              </p>
              <p className="text-2xl font-mono font-bold text-slate-900">{stats.manufacturing_orders}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-sm border border-slate-200">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Opérations
              </p>
              <p className="text-2xl font-mono font-bold text-slate-900">{stats.operations}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-sm border border-slate-200">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Articles
              </p>
              <p className="text-2xl font-mono font-bold text-slate-900">{stats.articles}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-sm border border-slate-200">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Stocks
              </p>
              <p className="text-2xl font-mono font-bold text-slate-900">{stats.stocks}</p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-3 rounded-sm border border-blue-200">
              <p className="text-xs text-blue-600 mb-1">Machines</p>
              <p className="text-lg font-mono font-semibold text-blue-900">{stats.machines}</p>
            </div>
            <div className="bg-blue-50 p-3 rounded-sm border border-blue-200">
              <p className="text-xs text-blue-600 mb-1">Postes</p>
              <p className="text-lg font-mono font-semibold text-blue-900">{stats.work_centers}</p>
            </div>
            <div className="bg-blue-50 p-3 rounded-sm border border-blue-200">
              <p className="text-xs text-blue-600 mb-1">Calendriers</p>
              <p className="text-lg font-mono font-semibold text-blue-900">{stats.calendars}</p>
            </div>
            <div className="bg-blue-50 p-3 rounded-sm border border-blue-200">
              <p className="text-xs text-blue-600 mb-1">Règles</p>
              <p className="text-lg font-mono font-semibold text-blue-900">{stats.rules}</p>
            </div>
          </div>
        </div>
      )}

      {/* Reset Confirmation Dialog */}
      {showResetConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-sm shadow-lg p-6 max-w-md mx-4">
            <div className="flex items-start gap-3 mb-4">
              <AlertTriangle size={24} className="text-red-600 mt-0.5" />
              <div>
                <h4 className="text-lg font-semibold text-slate-900 mb-2">
                  Confirmer la suppression
                </h4>
                <p className="text-sm text-slate-600">
                  Cette action va supprimer toutes les données opérationnelles :
                </p>
                <ul className="text-sm text-slate-600 mt-2 space-y-1 list-disc list-inside">
                  <li>Ordres de fabrication</li>
                  <li>Opérations</li>
                  <li>Articles et stocks</li>
                  <li>Scénarios de planification</li>
                </ul>
                <p className="text-sm text-slate-600 mt-2">
                  <strong>Les données de configuration seront conservées</strong> (machines, calendriers, règles).
                </p>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowResetConfirm(false)}
                disabled={resetting}
                className="bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-sm px-4 py-2 text-sm font-medium transition-colors"
              >
                Annuler
              </button>
              <button
                data-testid="confirm-reset-btn"
                onClick={handleReset}
                disabled={resetting}
                className="bg-red-600 text-white hover:bg-red-700 rounded-sm px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
              >
                {resetting ? 'Suppression...' : 'Supprimer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Mode Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-sm p-5">
        <div className="flex items-start gap-3">
          <Info size={20} className="text-blue-600 mt-0.5" />
          <div>
            <h4 className="text-lg font-semibold text-blue-900 mb-2">Mode Remplacement Complet</h4>
            <p className="text-sm text-blue-800 mb-2">
              Les imports fonctionnent en mode <strong>remplacement complet</strong> : 
              les anciennes données sont supprimées avant l'import des nouvelles.
            </p>
            <ul className="text-sm text-blue-800 space-y-1">
              <li className="flex items-start gap-2">
                <CheckCircle size={16} className="text-blue-600 mt-0.5" />
                <span>Aucun doublon possible</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle size={16} className="text-blue-600 mt-0.5" />
                <span>Vérification d'unicité des ID dans le fichier CSV</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle size={16} className="text-blue-600 mt-0.5" />
                <span>Import idempotent : vous pouvez relancer sans risque</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Import Section */}
      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
        <h3 className="text-xl font-semibold text-slate-800 mb-2">Import de données ERP</h3>
        <p className="text-sm text-slate-600 leading-normal mb-6">
          Importez vos fichiers CSV depuis l'ERP Infor LN. Chaque fichier doit respecter le format attendu.
        </p>

        <div className="space-y-4">
          {importTypes.map((type) => (
            <div
              key={type.key}
              className="border border-slate-200 rounded-sm p-4 hover:border-slate-300 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-900">{type.label}</p>
                  <p className="text-xs text-slate-500 mt-1">Format CSV requis</p>
                </div>
                <label
                  data-testid={type.testId}
                  className="cursor-pointer inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
                >
                  <Upload size={16} />
                  {uploading[type.key] ? 'Import...' : 'Choisir fichier'}
                  <input
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={(e) => handleFileUpload(type.key, e.target.files[0])}
                    disabled={uploading[type.key]}
                  />
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CSV Format Reference */}
      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">Format des fichiers</h3>
        <div className="space-y-3 text-sm text-slate-600">
          <div>
            <p className="font-medium text-slate-900">Ordres de Fabrication:</p>
            <code className="text-xs font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200">
              id, article_id, quantity, due_date, status
            </code>
          </div>
          <div>
            <p className="font-medium text-slate-900">Opérations:</p>
            <code className="text-xs font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200">
              id, order_id, article_id, operation_id, task_id, work_center_id, status, production_time_minutes, setup_time_minutes
            </code>
            <p className="text-xs text-blue-600 mt-1">
              ℹ️ <strong>task_id</strong> = type de tâche (ex: USINAGE, ASSEMBLAGE), <strong>work_center_id</strong> = centre de charge requis
            </p>
            <p className="text-xs text-green-600 mt-1">
              ✓ Le champ <strong>machine_id</strong> est automatiquement assigné par le moteur selon les règles métier
            </p>
          </div>
          <div>
            <p className="font-medium text-slate-900">Articles:</p>
            <code className="text-xs font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200">
              id, description
            </code>
          </div>
          <div>
            <p className="font-medium text-slate-900">Stocks:</p>
            <code className="text-xs font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200">
              article_id, quantity
            </code>
          </div>
        </div>
      </div>

      {/* Workflow Guide */}
      <div className="bg-slate-50 border border-slate-200 rounded-sm p-5">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">Workflow POC Recommandé</h3>
        <ol className="space-y-2 text-sm text-slate-700">
          <li className="flex items-start gap-2">
            <span className="font-mono font-semibold text-slate-900">1.</span>
            <span>Reset des données ERP (bouton rouge ci-dessus)</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-mono font-semibold text-slate-900">2.</span>
            <span>Import des fichiers CSV (ordres, opérations, articles, stocks)</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-mono font-semibold text-slate-900">3.</span>
            <span>Vérification du nombre d'OF et d'opérations dans la section "État des Données"</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-mono font-semibold text-slate-900">4.</span>
            <span>Lancement d'un scénario d'ordonnancement depuis la page Ordonnancement</span>
          </li>
        </ol>
      </div>
    </div>
  );
}
