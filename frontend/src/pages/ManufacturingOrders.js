import { useEffect, useState } from 'react';
import axios from 'axios';
import { RefreshCw, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ManufacturingOrders() {
  const [operations, setOperations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('flat'); // 'flat' ou 'grouped'

  useEffect(() => {
    fetchEnrichedOperations();
  }, []);

  const fetchEnrichedOperations = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/operations-enrichies`);
      setOperations(response.data);
      toast.success(`${response.data.length} opérations chargées`);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  const isLate = (dateBesoin) => {
    if (!dateBesoin) return false;
    const due = new Date(dateBesoin);
    const today = new Date();
    return due < today;
  };

  const isUrgent = (dateBesoin) => {
    if (!dateBesoin) return false;
    const due = new Date(dateBesoin);
    const today = new Date();
    const daysUntil = Math.ceil((due - today) / (1000 * 60 * 60 * 24));
    return daysUntil <= 3 && daysUntil >= 0;
  };

  // Grouper par order_id pour la vue groupée
  const groupedByOrder = operations.reduce((acc, op) => {
    const orderId = op.order_id || 'SANS_ORDRE';
    if (!acc[orderId]) {
      acc[orderId] = {
        order_id: orderId,
        article_id: op.article_id,
        date_besoin: op.date_besoin,
        priority: op.priority,
        operations: []
      };
    }
    acc[orderId].operations.push(op);
    return acc;
  }, {});

  const ordersArray = Object.values(groupedByOrder);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold text-slate-800">Ordres de Fabrication</h3>
          <p className="text-sm text-slate-500 mt-1">
            Vue enrichie : jointure opérations + ordres via order_id
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-slate-100 rounded-sm p-0.5">
            <button
              onClick={() => setViewMode('flat')}
              className={`px-3 py-1 text-sm font-medium rounded-sm transition-colors ${
                viewMode === 'flat' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Vue à plat
            </button>
            <button
              onClick={() => setViewMode('grouped')}
              className={`px-3 py-1 text-sm font-medium rounded-sm transition-colors ${
                viewMode === 'grouped' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
              }`}
            >
              Par OF
            </button>
          </div>
          <button
            onClick={fetchEnrichedOperations}
            disabled={loading}
            className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Actualiser
          </button>
        </div>
      </div>

      {/* Statistiques */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-slate-800">{operations.length}</div>
          <div className="text-sm text-slate-500">Opérations</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-slate-800">{ordersArray.length}</div>
          <div className="text-sm text-slate-500">Ordres de Fab.</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-red-700">
            {operations.filter(op => isLate(op.date_besoin)).length}
          </div>
          <div className="text-sm text-red-600">En retard</div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
          <div className="text-3xl font-bold text-amber-700">
            {operations.filter(op => isUrgent(op.date_besoin)).length}
          </div>
          <div className="text-sm text-amber-600">Urgent (≤3j)</div>
        </div>
      </div>

      {/* Vue à plat */}
      {viewMode === 'flat' && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden">
          <div className="bg-slate-50 border-b border-slate-200 px-4 py-3">
            <h4 className="font-semibold text-slate-800">Opérations Enrichies (Vue à Plat)</h4>
            <p className="text-xs text-slate-500 mt-1">
              Chaque ligne montre une opération avec les données de son ordre (jointure sur order_id)
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 border-b border-slate-200">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Order ID</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Article</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Date Besoin</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Priorité</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Op. ID</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Tâche</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Centre</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Prod (min)</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Setup (min)</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Jointure</th>
                </tr>
              </thead>
              <tbody>
                {operations.map((op) => (
                  <tr 
                    key={op.id} 
                    className={`border-b border-slate-100 hover:bg-slate-50 ${
                      isLate(op.date_besoin) ? 'bg-red-50' : 
                      isUrgent(op.date_besoin) ? 'bg-amber-50' : ''
                    }`}
                  >
                    <td className="px-3 py-2 font-mono text-xs">{op.order_id}</td>
                    <td className="px-3 py-2">
                      {op.article_id ? (
                        <span className="bg-orange-100 text-orange-800 px-1.5 py-0.5 rounded text-xs font-mono">
                          {op.article_id}
                        </span>
                      ) : (
                        <span className="text-red-500 text-xs">NON TROUVE</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {op.date_besoin ? (
                        <span className={`text-xs font-mono ${
                          isLate(op.date_besoin) ? 'text-red-700 font-bold' :
                          isUrgent(op.date_besoin) ? 'text-amber-700 font-bold' : 'text-slate-600'
                        }`}>
                          {op.date_besoin}
                          {isLate(op.date_besoin) && ' (RETARD)'}
                          {isUrgent(op.date_besoin) && ' (URGENT)'}
                        </span>
                      ) : (
                        <span className="text-red-500 text-xs">NON TROUVE</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-xs text-center">{op.priority || 0}</td>
                    <td className="px-3 py-2">
                      <span className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded text-xs font-mono">
                        {op.operation_id}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded text-xs font-mono">
                        {op.tache_id || '-'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className="bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded text-xs font-mono">
                        {op.centre_de_charge_id || '-'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-right font-mono">{op.production_time_minutes}</td>
                    <td className="px-3 py-2 text-xs text-right font-mono">{op.setup_time_minutes}</td>
                    <td className="px-3 py-2">
                      {op.ordre_trouve ? (
                        <CheckCircle size={16} className="text-green-600" />
                      ) : (
                        <XCircle size={16} className="text-red-600" />
                      )}
                    </td>
                  </tr>
                ))}
                {operations.length === 0 && (
                  <tr>
                    <td colSpan={10} className="px-4 py-8 text-center text-sm text-slate-500">
                      Aucune opération. Importez des données via Import CSV.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Vue groupée par OF */}
      {viewMode === 'grouped' && (
        <div className="space-y-4">
          {ordersArray.map((order) => (
            <div key={order.order_id} className={`bg-white border rounded-sm shadow-sm overflow-hidden ${
              isLate(order.date_besoin) ? 'border-red-300' : 
              isUrgent(order.date_besoin) ? 'border-amber-300' : 'border-slate-200'
            }`}>
              <div className={`px-4 py-3 border-b ${
                isLate(order.date_besoin) ? 'bg-red-50 border-red-200' : 
                isUrgent(order.date_besoin) ? 'bg-amber-50 border-amber-200' : 'bg-slate-50 border-slate-200'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="font-mono font-bold text-slate-800">{order.order_id}</span>
                    {order.article_id && (
                      <span className="bg-orange-100 text-orange-800 px-2 py-0.5 rounded text-xs font-mono">
                        Article: {order.article_id}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4">
                    {order.date_besoin && (
                      <span className={`text-xs font-mono ${
                        isLate(order.date_besoin) ? 'text-red-700 font-bold' :
                        isUrgent(order.date_besoin) ? 'text-amber-700 font-bold' : 'text-slate-600'
                      }`}>
                        Besoin: {order.date_besoin}
                        {isLate(order.date_besoin) && (
                          <span className="ml-2 bg-red-200 text-red-800 px-1.5 py-0.5 rounded">RETARD</span>
                        )}
                        {isUrgent(order.date_besoin) && (
                          <span className="ml-2 bg-amber-200 text-amber-800 px-1.5 py-0.5 rounded">URGENT</span>
                        )}
                      </span>
                    )}
                    <span className="text-xs text-slate-500">{order.operations.length} opération(s)</span>
                  </div>
                </div>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-slate-100 border-b border-slate-200">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">N° Op</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Tâche</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Centre</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Prod (min)</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Setup (min)</th>
                  </tr>
                </thead>
                <tbody>
                  {order.operations
                    .sort((a, b) => (a.operation_id || 0) - (b.operation_id || 0))
                    .map((op) => (
                      <tr key={op.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="px-3 py-2 font-mono text-xs">{op.operation_id}</td>
                        <td className="px-3 py-2">
                          <span className="bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded text-xs font-mono">
                            {op.tache_id || '-'}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <span className="bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded text-xs font-mono">
                            {op.centre_de_charge_id || '-'}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-xs text-right font-mono">{op.production_time_minutes}</td>
                        <td className="px-3 py-2 text-xs text-right font-mono">{op.setup_time_minutes}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ))}
          {ordersArray.length === 0 && (
            <div className="bg-white border border-slate-200 rounded-sm p-8 text-center text-sm text-slate-500">
              Aucun ordre de fabrication. Importez des données via Import CSV.
            </div>
          )}
        </div>
      )}

      {/* Légende */}
      <div className="bg-slate-50 border border-slate-200 rounded-sm p-4">
        <h4 className="font-semibold text-slate-800 mb-2">Légende</h4>
        <div className="flex gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-100 border border-red-300 rounded"></div>
            <span className="text-slate-600">En retard (date_besoin dépassée)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-amber-100 border border-amber-300 rounded"></div>
            <span className="text-slate-600">Urgent (≤3 jours)</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle size={16} className="text-green-600" />
            <span className="text-slate-600">Jointure OK (ordre trouvé)</span>
          </div>
          <div className="flex items-center gap-2">
            <XCircle size={16} className="text-red-600" />
            <span className="text-slate-600">Jointure KO (ordre non trouvé)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
