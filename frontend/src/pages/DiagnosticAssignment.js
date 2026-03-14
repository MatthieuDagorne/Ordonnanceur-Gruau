import { useEffect, useState } from 'react';
import axios from 'axios';
import { RefreshCw, CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function DiagnosticAssignment() {
  const [diagnostic, setDiagnostic] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedOps, setExpandedOps] = useState({});

  const fetchDiagnostic = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/diagnostic/assignment`);
      setDiagnostic(response.data);
      toast.success('Diagnostic chargé');
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostic();
  }, []);

  const toggleExpand = (opId) => {
    setExpandedOps(prev => ({ ...prev, [opId]: !prev[opId] }));
  };

  if (!diagnostic) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Chargement du diagnostic...</div>
      </div>
    );
  }

  const { summary, machines_par_centre, regles_chargees, diagnostics_table } = diagnostic;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold text-slate-800">Diagnostic d'Assignation</h3>
          <p className="text-sm text-slate-500 mt-1">
            Analyse détaillée par opération : tache_id, centre_de_charge_id, machines, règles
          </p>
        </div>
        <button
          onClick={fetchDiagnostic}
          disabled={loading}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Actualiser
        </button>
      </div>

      {/* Résumé */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-slate-800">{summary?.total_operations || 0}</div>
          <div className="text-sm text-slate-500">Total opérations</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-green-700">{summary?.assigned || 0}</div>
          <div className="text-sm text-green-600">Assignées</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-red-700">{summary?.unassigned || 0}</div>
          <div className="text-sm text-red-600">Non assignées</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-amber-700">{summary?.preferred || 0}</div>
          <div className="text-sm text-amber-600">Avec préférence</div>
        </div>
      </div>

      {/* Causes d'échec */}
      {summary?.failure_causes && Object.keys(summary.failure_causes).length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-sm p-4">
          <h4 className="font-semibold text-red-800 mb-2 flex items-center gap-2">
            <AlertTriangle size={18} />
            Causes d'échec
          </h4>
          <ul className="space-y-1">
            {Object.entries(summary.failure_causes).map(([cause, count]) => (
              <li key={cause} className="text-sm text-red-700">
                <span className="font-mono bg-red-100 px-1 rounded">{cause}</span>: {count} opération(s)
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Machines par Centre de Charge */}
      <div className="bg-blue-50 border border-blue-200 rounded-sm p-4">
        <h4 className="font-semibold text-blue-800 mb-3">Index des Machines par Centre de Charge</h4>
        {!machines_par_centre || Object.keys(machines_par_centre).length === 0 ? (
          <p className="text-red-600">⚠️ Aucune machine indexée ! Créez des machines avec un centre_de_charge_id.</p>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(machines_par_centre).map(([centre, machines]) => (
              <div key={centre} className="bg-white rounded-sm p-3 border border-blue-100">
                <div className="font-mono text-sm text-purple-600 font-semibold mb-1">{centre}</div>
                <div className="flex flex-wrap gap-1">
                  {machines.map(m => (
                    <span key={m.id} className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs font-mono">
                      {m.id}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Règles chargées */}
      <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
        <h4 className="font-semibold text-amber-800 mb-3">Règles Métier Chargées ({regles_chargees?.length || 0})</h4>
        {!regles_chargees || regles_chargees.length === 0 ? (
          <p className="text-slate-600">Aucune règle métier configurée.</p>
        ) : (
          <div className="space-y-2">
            {regles_chargees.map((rule, idx) => (
              <div key={idx} className="bg-white rounded-sm p-2 border border-amber-100 text-sm">
                <span className={`font-semibold ${
                  rule.type === 'FORBID' ? 'text-red-600' :
                  rule.type === 'PREFER' ? 'text-amber-600' : 'text-green-600'
                }`}>{rule.type}</span>
                {' '}<span className="text-slate-800">{rule.name}</span>
                <div className="text-xs text-slate-500 mt-1">
                  tache={rule.tache_id || '-'} | centre={rule.centre_de_charge_id || '-'} | machine={rule.machine_id}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tableau de diagnostic */}
      <div className="bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 px-4 py-3">
          <h4 className="font-semibold text-slate-800">Diagnostic par Opération</h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 border-b border-slate-200">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase"></th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Opération</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Tâche</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Centre</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Machines du Centre</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Règles</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Machine Choisie</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Statut</th>
              </tr>
            </thead>
            <tbody>
              {diagnostics_table?.map((row) => (
                <>
                  <tr 
                    key={row.operation_id} 
                    className={`border-b border-slate-100 hover:bg-slate-50 cursor-pointer ${!row.is_assigned ? 'bg-red-50' : ''}`}
                    onClick={() => toggleExpand(row.operation_id)}
                  >
                    <td className="px-3 py-2">
                      {expandedOps[row.operation_id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{row.operation_id}</td>
                    <td className="px-3 py-2">
                      <span className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded text-xs font-mono">
                        {row.tache_id || '-'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className="bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded text-xs font-mono">
                        {row.centre_de_charge_id || '-'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {row.machines_du_centre?.length > 0 ? (
                        <span className="text-xs text-slate-600">{row.machines_du_centre.join(', ')}</span>
                      ) : (
                        <span className="text-xs text-red-600 font-semibold">AUCUNE</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span className="text-xs text-slate-600">
                        {row.regles_applicables?.length || 0} règle(s)
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {row.machine_choisie ? (
                        <span className="bg-green-100 text-green-800 px-1.5 py-0.5 rounded text-xs font-mono font-semibold">
                          {row.machine_choisie}
                        </span>
                      ) : (
                        <span className="text-xs text-red-600">-</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {row.is_assigned ? (
                        <CheckCircle size={16} className="text-green-600" />
                      ) : (
                        <XCircle size={16} className="text-red-600" />
                      )}
                    </td>
                  </tr>
                  {expandedOps[row.operation_id] && (
                    <tr className="bg-slate-50">
                      <td colSpan={8} className="px-6 py-3">
                        <div className="grid grid-cols-2 gap-4 text-xs">
                          <div>
                            <div className="font-semibold text-slate-700 mb-1">Machines interdites (FORBID):</div>
                            {row.machines_interdites?.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {row.machines_interdites.map(m => (
                                  <span key={m} className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-mono">{m}</span>
                                ))}
                              </div>
                            ) : <span className="text-slate-400">Aucune</span>}
                          </div>
                          <div>
                            <div className="font-semibold text-slate-700 mb-1">Machines préférées (PREFER):</div>
                            {row.machines_preferees?.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {row.machines_preferees.map(m => (
                                  <span key={m} className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-mono">{m}</span>
                                ))}
                              </div>
                            ) : <span className="text-slate-400">Aucune</span>}
                          </div>
                          <div>
                            <div className="font-semibold text-slate-700 mb-1">Candidates finales:</div>
                            {row.candidates_finales?.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {row.candidates_finales.map(m => (
                                  <span key={m} className="bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-mono">{m}</span>
                                ))}
                              </div>
                            ) : <span className="text-red-500 font-semibold">AUCUNE</span>}
                          </div>
                          <div>
                            <div className="font-semibold text-slate-700 mb-1">Règles appliquées:</div>
                            {row.regles_applicables?.length > 0 ? (
                              <div className="space-y-0.5">
                                {row.regles_applicables.map((r, i) => (
                                  <div key={i} className="text-slate-600">{r}</div>
                                ))}
                              </div>
                            ) : <span className="text-slate-400">Aucune règle</span>}
                          </div>
                          {row.cause_echec && (
                            <div className="col-span-2">
                              <div className="font-semibold text-red-700 mb-1">CAUSE D'ÉCHEC:</div>
                              <span className="bg-red-100 text-red-800 px-2 py-1 rounded font-mono">{row.cause_echec}</span>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
              {(!diagnostics_table || diagnostics_table.length === 0) && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-sm text-slate-500">
                    Aucune opération. Importez des données pour voir le diagnostic.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
