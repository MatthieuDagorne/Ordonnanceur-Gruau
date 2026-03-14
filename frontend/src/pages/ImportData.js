import { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, Trash2, AlertTriangle, CheckCircle, Info, Package, Database, Settings, Calendar } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const importTypes = [
  { key: 'manufacturing-orders', label: 'Ordres de Fabrication', testId: 'import-orders' },
  { key: 'operations', label: 'Opérations', testId: 'import-operations' },
  { key: 'articles', label: 'Articles', testId: 'import-articles' },
  { key: 'stocks', label: 'Stocks', testId: 'import-stocks' },
  { key: 'operation-materials', label: 'Matières par Opération', testId: 'import-operation-materials' },
  { key: 'planned-supplier-receipts', label: 'Réceptions Fournisseurs', testId: 'import-planned-receipts' },
  { key: 'bom', label: 'Nomenclatures (BOM)', testId: 'import-bom' },
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
        fetchStats();
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
        fetchStats();
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
    <div className="space-y-6" data-testid="import-page">
      {/* Data Statistics - Main */}
      {stats && (
        <div className="rounded-lg p-5" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Database size={20} style={{ color: 'var(--brand-primary)' }} />
              <h3 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>État des Données</h3>
            </div>
            <button
              data-testid="reset-data-btn"
              onClick={() => setShowResetConfirm(true)}
              className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
              style={{ backgroundColor: 'var(--status-error)', color: 'white' }}
            >
              <Trash2 size={16} />
              Reset Données ERP
            </button>
          </div>

          {/* Données Principales (ERP) */}
          <div className="mb-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
              <Package size={14} />
              Données ERP
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
                <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                  Ordres Fab.
                </p>
                <p className="text-2xl font-mono font-bold" style={{ color: 'var(--text-primary)' }}>{stats.manufacturing_orders}</p>
              </div>
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
                <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                  Opérations
                </p>
                <p className="text-2xl font-mono font-bold" style={{ color: 'var(--text-primary)' }}>{stats.operations}</p>
              </div>
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
                <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                  Articles
                </p>
                <p className="text-2xl font-mono font-bold" style={{ color: 'var(--text-primary)' }}>{stats.articles}</p>
              </div>
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
                <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                  Stocks
                </p>
                <p className="text-2xl font-mono font-bold" style={{ color: 'var(--text-primary)' }}>{stats.stocks}</p>
              </div>
            </div>
          </div>

          {/* Données Complémentaires (Supply Chain) */}
          <div className="mb-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-2" style={{ color: 'var(--status-info)' }}>
              <Package size={14} />
              Supply Chain
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--status-info-bg)', border: '1px solid var(--status-info-border)' }}>
                <p className="text-xs mb-1" style={{ color: 'var(--status-info)' }}>Matières/Op.</p>
                <p className="text-lg font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.operation_materials || 0}</p>
              </div>
              <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--status-info-bg)', border: '1px solid var(--status-info-border)' }}>
                <p className="text-xs mb-1" style={{ color: 'var(--status-info)' }}>Réceptions Prévues</p>
                <p className="text-lg font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.planned_receipts || 0}</p>
              </div>
              <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--status-info-bg)', border: '1px solid var(--status-info-border)' }}>
                <p className="text-xs mb-1" style={{ color: 'var(--status-info)' }}>Nomenclatures (BOM)</p>
                <p className="text-lg font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.bom_lines || 0}</p>
              </div>
              <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--status-info-bg)', border: '1px solid var(--status-info-border)' }}>
                <p className="text-xs mb-1" style={{ color: 'var(--status-info)' }}>Indisponibilités</p>
                <p className="text-lg font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.unavailabilities || 0}</p>
              </div>
            </div>
          </div>

          {/* Configuration */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-2" style={{ color: 'var(--status-warning)' }}>
              <Settings size={14} />
              Configuration
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)' }}>
                <p className="text-xs mb-1" style={{ color: 'var(--status-warning)' }}>Machines</p>
                <p className="text-lg font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.machines}</p>
              </div>
              <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)' }}>
                <p className="text-xs mb-1" style={{ color: 'var(--status-warning)' }}>Centres Charge</p>
                <p className="text-lg font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.work_centers}</p>
              </div>
              <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)' }}>
                <p className="text-xs mb-1" style={{ color: 'var(--status-warning)' }}>Calendriers</p>
                <p className="text-lg font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.calendars}</p>
              </div>
              <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)' }}>
                <p className="text-xs mb-1" style={{ color: 'var(--status-warning)' }}>Règles Métier</p>
                <p className="text-lg font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.rules}</p>
              </div>
              <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--status-success-bg)', border: '1px solid var(--status-success-border)' }}>
                <p className="text-xs mb-1" style={{ color: 'var(--status-success)' }}>Scénarios</p>
                <p className="text-lg font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{stats.scenarios}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reset Confirmation Dialog */}
      {showResetConfirm && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="rounded-lg shadow-lg p-6 max-w-md mx-4" style={{ backgroundColor: 'var(--bg-elevated)' }}>
            <div className="flex items-start gap-3 mb-4">
              <AlertTriangle size={24} style={{ color: 'var(--status-error)' }} className="mt-0.5" />
              <div>
                <h4 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                  Confirmer la suppression
                </h4>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Cette action va supprimer toutes les données opérationnelles :
                </p>
                <ul className="text-sm mt-2 space-y-1 list-disc list-inside" style={{ color: 'var(--text-secondary)' }}>
                  <li>Ordres de fabrication</li>
                  <li>Opérations</li>
                  <li>Articles et stocks</li>
                  <li>Scénarios de planification</li>
                </ul>
                <p className="text-sm mt-2" style={{ color: 'var(--text-secondary)' }}>
                  <strong>Les données de configuration seront conservées</strong> (machines, calendriers, règles).
                </p>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowResetConfirm(false)}
                disabled={resetting}
                className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-primary)', border: '1px solid var(--border-default)' }}
              >
                Annuler
              </button>
              <button
                data-testid="confirm-reset-btn"
                onClick={handleReset}
                disabled={resetting}
                className="rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
                style={{ backgroundColor: 'var(--status-error)', color: 'white' }}
              >
                {resetting ? 'Suppression...' : 'Supprimer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Mode Notice */}
      <div className="rounded-lg p-5" style={{ backgroundColor: 'var(--status-info-bg)', border: '1px solid var(--status-info-border)' }}>
        <div className="flex items-start gap-3">
          <Info size={20} style={{ color: 'var(--status-info)' }} className="mt-0.5" />
          <div>
            <h4 className="text-lg font-semibold mb-2" style={{ color: 'var(--status-info)' }}>Mode Remplacement Complet</h4>
            <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>
              Les imports fonctionnent en mode <strong>remplacement complet</strong> : 
              les anciennes données sont supprimées avant l'import des nouvelles.
            </p>
            <ul className="text-sm space-y-1" style={{ color: 'var(--text-secondary)' }}>
              <li className="flex items-start gap-2">
                <CheckCircle size={16} style={{ color: 'var(--status-info)' }} className="mt-0.5" />
                <span>Aucun doublon possible</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle size={16} style={{ color: 'var(--status-info)' }} className="mt-0.5" />
                <span>Vérification d'unicité des ID dans le fichier CSV</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle size={16} style={{ color: 'var(--status-info)' }} className="mt-0.5" />
                <span>Import idempotent : vous pouvez relancer sans risque</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Import Section */}
      <div className="rounded-lg p-5" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Import de données ERP</h3>
        <p className="text-sm leading-normal mb-6" style={{ color: 'var(--text-secondary)' }}>
          Importez vos fichiers CSV depuis l'ERP Infor LN. Chaque fichier doit respecter le format attendu.
        </p>

        <div className="space-y-4">
          {importTypes.map((type) => (
            <div
              key={type.key}
              className="rounded-lg p-4 transition-colors"
              style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{type.label}</p>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Format CSV requis</p>
                </div>
                <label
                  data-testid={type.testId}
                  className="cursor-pointer inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                  style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
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
      <div className="rounded-lg p-5" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <h3 className="text-lg font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Format des fichiers</h3>
        <div className="space-y-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
          <div>
            <p className="font-medium" style={{ color: 'var(--text-primary)' }}>Ordres de Fabrication:</p>
            <code className="text-xs font-mono px-2 py-1 rounded" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
              id, article_id, quantity, due_date, status
            </code>
          </div>
          <div>
            <p className="font-medium" style={{ color: 'var(--text-primary)' }}>Opérations:</p>
            <code className="text-xs font-mono px-2 py-1 rounded" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
              id, order_id, article_id, operation_id, task_id, work_center_id, status, production_time_minutes, setup_time_minutes
            </code>
          </div>
          <div>
            <p className="font-medium" style={{ color: 'var(--text-primary)' }}>Articles:</p>
            <code className="text-xs font-mono px-2 py-1 rounded" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
              id, description, type_matiere, epaisseur, couleur, largeur, longueur
            </code>
          </div>
          <div>
            <p className="font-medium" style={{ color: 'var(--text-primary)' }}>Stocks:</p>
            <code className="text-xs font-mono px-2 py-1 rounded" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
              article_id, quantity
            </code>
          </div>
          <div className="pt-3 mt-3" style={{ borderTop: '1px solid var(--border-default)' }}>
            <p className="font-medium" style={{ color: 'var(--status-info)' }}>Matières par Opération:</p>
            <code className="text-xs font-mono px-2 py-1 rounded" style={{ backgroundColor: 'var(--status-info-bg)', border: '1px solid var(--status-info-border)' }}>
              id, order_id, operation_id, article_composant_id, quantity
            </code>
          </div>
          <div>
            <p className="font-medium" style={{ color: 'var(--status-info)' }}>Réceptions Fournisseurs:</p>
            <code className="text-xs font-mono px-2 py-1 rounded" style={{ backgroundColor: 'var(--status-info-bg)', border: '1px solid var(--status-info-border)' }}>
              article_id, quantity, planned_date
            </code>
          </div>
          <div>
            <p className="font-medium" style={{ color: 'var(--brand-primary)' }}>Nomenclatures BOM:</p>
            <code className="text-xs font-mono px-2 py-1 rounded" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
              parent_article_id, child_article_id, quantity, level, unit, scrap_rate
            </code>
          </div>
        </div>
      </div>

      {/* Workflow Guide */}
      <div className="rounded-lg p-5" style={{ backgroundColor: 'var(--bg-sunken)', border: '1px solid var(--border-default)' }}>
        <h3 className="text-lg font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Workflow POC Recommandé</h3>
        <ol className="space-y-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
          <li className="flex items-start gap-2">
            <span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>1.</span>
            <span>Reset des données ERP (bouton rouge ci-dessus)</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>2.</span>
            <span>Import des fichiers CSV (ordres, opérations, articles, stocks)</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>3.</span>
            <span>Vérification du nombre d'OF et d'opérations dans la section "État des Données"</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>4.</span>
            <span>Lancement d'un scénario d'ordonnancement depuis la page Ordonnancement</span>
          </li>
        </ol>
      </div>
    </div>
  );
}
