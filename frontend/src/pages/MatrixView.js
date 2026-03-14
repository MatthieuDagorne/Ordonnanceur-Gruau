import { useEffect, useState } from 'react';
import axios from 'axios';
import { RefreshCw, CheckCircle, XCircle, Star, HelpCircle, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function MatrixView() {
  const [matrixData, setMatrixData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMatrix();
  }, []);

  const fetchMatrix = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/matrix/machine-task`);
      setMatrixData(response.data);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur lors du chargement de la matrice');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'allowed':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'forbidden':
        return <XCircle size={16} className="text-red-500" />;
      case 'preferred':
        return <Star size={16} className="text-amber-500" />;
      case 'compatible':
        return <CheckCircle size={14} className="text-blue-400" />;
      case 'incompatible':
        return <AlertTriangle size={14} className="text-slate-400" />;
      default:
        return <HelpCircle size={14} className="text-slate-300" />;
    }
  };

  const getStatusBg = (status) => {
    switch (status) {
      case 'allowed':
        return 'bg-green-100 dark:bg-green-900/30';
      case 'forbidden':
        return 'bg-red-100 dark:bg-red-900/30';
      case 'preferred':
        return 'bg-amber-100 dark:bg-amber-900/30';
      case 'compatible':
        return 'bg-blue-50 dark:bg-blue-900/20';
      case 'incompatible':
        return 'bg-slate-100 dark:bg-slate-800';
      default:
        return 'bg-slate-50 dark:bg-slate-800/50';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="loading">
        <RefreshCw className="animate-spin text-blue-500" size={32} />
      </div>
    );
  }

  if (!matrixData || !matrixData.matrix) {
    return (
      <div className="text-center py-12" data-testid="no-data">
        <p className="text-slate-500">Aucune donnée disponible</p>
        <button onClick={fetchMatrix} className="mt-4 text-blue-600 hover:underline">
          Actualiser
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="matrix-view">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Matrice Compatibilités
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Vue des compatibilités entre machines et tâches
          </p>
        </div>
        <button
          onClick={fetchMatrix}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
          data-testid="refresh-btn"
        >
          <RefreshCw size={16} />
          Actualiser
        </button>
      </div>

      {/* Légende */}
      <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Légende</h3>
        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <CheckCircle size={16} className="text-green-500" />
            <span style={{ color: 'var(--text-secondary)' }}>Autorisé (règle ALLOW)</span>
          </div>
          <div className="flex items-center gap-2">
            <XCircle size={16} className="text-red-500" />
            <span style={{ color: 'var(--text-secondary)' }}>Interdit (règle FORBID)</span>
          </div>
          <div className="flex items-center gap-2">
            <Star size={16} className="text-amber-500" />
            <span style={{ color: 'var(--text-secondary)' }}>Préféré (règle PREFER)</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle size={14} className="text-blue-400" />
            <span style={{ color: 'var(--text-secondary)' }}>Compatible (même centre)</span>
          </div>
          <div className="flex items-center gap-2">
            <AlertTriangle size={14} className="text-slate-400" />
            <span style={{ color: 'var(--text-secondary)' }}>Incompatible (centre différent)</span>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <p className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {matrixData.machines?.length || 0}
          </p>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Machines</p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <p className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {matrixData.taches?.length || 0}
          </p>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Tâches</p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <p className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {matrixData.rules_count || 0}
          </p>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Règles actives</p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <p className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {(matrixData.machines?.length || 0) * (matrixData.taches?.length || 0)}
          </p>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Combinaisons</p>
        </div>
      </div>

      {/* Matrice */}
      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <div className="overflow-x-auto">
          <table className="min-w-full" data-testid="matrix-table">
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-sunken)' }}>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider sticky left-0" 
                    style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-muted)' }}>
                  Machine / Tâche
                </th>
                {matrixData.taches?.map(tache => (
                  <th key={tache} className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-wider"
                      style={{ color: 'var(--text-muted)' }}>
                    {tache}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrixData.matrix?.map((row, idx) => (
                <tr key={row.machine_id} 
                    className={idx % 2 === 0 ? '' : ''}
                    style={{ borderBottom: '1px solid var(--border-default)' }}>
                  <td className="px-4 py-3 sticky left-0"
                      style={{ backgroundColor: 'var(--bg-elevated)' }}>
                    <div>
                      <span className="font-mono text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                        {row.machine_id}
                      </span>
                      <span className="ml-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                        ({row.centre_id})
                      </span>
                    </div>
                  </td>
                  {matrixData.taches?.map(tache => {
                    const compat = row.compatibilities?.[tache] || {};
                    return (
                      <td key={tache} className="px-3 py-3 text-center">
                        <div 
                          className={`inline-flex items-center justify-center w-8 h-8 rounded-lg ${getStatusBg(compat.status)}`}
                          title={compat.rule ? `Règle: ${compat.rule}` : compat.status}
                        >
                          {getStatusIcon(compat.status)}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {(!matrixData.machines?.length || !matrixData.taches?.length) && (
        <div className="text-center py-8 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <p style={{ color: 'var(--text-muted)' }}>
            Importez des données (machines, opérations) pour visualiser la matrice
          </p>
        </div>
      )}
    </div>
  );
}
