import { useEffect, useState } from 'react';
import axios from 'axios';
import { 
  BarChart3, Clock, AlertTriangle, CheckCircle, TrendingUp, 
  Package, Factory, Calendar, RefreshCw, ChevronDown, ChevronUp
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function APSDashboard() {
  const [kpis, setKpis] = useState(null);
  const [capacity, setCapacity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedSection, setExpandedSection] = useState('all');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [kpisRes, capacityRes] = await Promise.all([
        axios.get(`${API}/aps/kpis`),
        axios.get(`${API}/aps/capacity?horizon_days=7`)
      ]);
      setKpis(kpisRes.data);
      setCapacity(capacityRes.data);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur lors du chargement des KPIs');
    } finally {
      setLoading(false);
    }
  };

  const getUtilizationColor = (rate) => {
    if (rate >= 90) return 'bg-red-500';
    if (rate >= 70) return 'bg-amber-500';
    return 'bg-green-500';
  };

  const getUtilizationBg = (rate) => {
    if (rate >= 90) return 'bg-red-100 text-red-700';
    if (rate >= 70) return 'bg-amber-100 text-amber-700';
    return 'bg-green-100 text-green-700';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin text-slate-400" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold text-slate-800">APS Dashboard</h3>
          <p className="text-sm text-slate-500 mt-1">
            Advanced Planning & Scheduling - KPIs et Capacité
          </p>
        </div>
        <button
          onClick={fetchData}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium"
          data-testid="refresh-btn"
        >
          <RefreshCw size={16} />
          Actualiser
        </button>
      </div>

      {/* KPIs Cards */}
      <div className="grid grid-cols-4 gap-4">
        {/* OTD */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4" data-testid="kpi-otd">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${kpis?.otd?.rate >= 90 ? 'bg-green-100' : 'bg-amber-100'}`}>
              <CheckCircle className={kpis?.otd?.rate >= 90 ? 'text-green-600' : 'text-amber-600'} size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-600">OTD (On-Time Delivery)</p>
              <p className="text-2xl font-bold text-slate-900">{kpis?.otd?.rate || 0}%</p>
              <p className="text-xs text-slate-500">{kpis?.otd?.on_time || 0} / {kpis?.otd?.total || 0} ordres</p>
            </div>
          </div>
        </div>

        {/* Retards */}
        <div className="bg-white rounded-lg shadow-sm border border-red-200 p-4" data-testid="kpi-late">
          <div className="flex items-center gap-3">
            <div className="bg-red-100 p-2 rounded-lg">
              <AlertTriangle className="text-red-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-red-600">Ordres en Retard</p>
              <p className="text-2xl font-bold text-red-700">{kpis?.late_orders?.count || 0}</p>
              <p className="text-xs text-slate-500">
                {kpis?.late_orders?.orders?.[0] 
                  ? `Max: ${kpis.late_orders.orders[0].delay_hours}h` 
                  : 'Aucun retard'}
              </p>
            </div>
          </div>
        </div>

        {/* Utilisation */}
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4" data-testid="kpi-utilization">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${getUtilizationBg(kpis?.utilization?.overall_rate || 0)}`}>
              <Factory className={kpis?.utilization?.overall_rate >= 70 ? 'text-amber-600' : 'text-green-600'} size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-600">Utilisation Machines</p>
              <p className="text-2xl font-bold text-slate-900">{kpis?.utilization?.overall_rate || 0}%</p>
              <p className="text-xs text-slate-500">
                {kpis?.utilization?.loaded_hours || 0}h / {kpis?.utilization?.capacity_hours || 0}h
              </p>
            </div>
          </div>
        </div>

        {/* WIP */}
        <div className="bg-white rounded-lg shadow-sm border border-blue-200 p-4" data-testid="kpi-wip">
          <div className="flex items-center gap-3">
            <div className="bg-blue-100 p-2 rounded-lg">
              <Package className="text-blue-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-blue-600">WIP (En-cours)</p>
              <p className="text-2xl font-bold text-blue-700">{kpis?.wip?.orders_count || 0}</p>
              <p className="text-xs text-slate-500">
                {kpis?.wip?.operations_scheduled || 0} / {kpis?.wip?.operations_total || 0} ops planifiées
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Ordres en retard */}
      {kpis?.late_orders?.count > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-red-200 overflow-hidden" data-testid="late-orders-table">
          <div 
            className="px-4 py-3 border-b border-red-100 bg-red-50 flex items-center justify-between cursor-pointer"
            onClick={() => setExpandedSection(expandedSection === 'late' ? 'all' : 'late')}
          >
            <h2 className="font-semibold text-red-800 flex items-center gap-2">
              <AlertTriangle size={16} />
              Ordres en Retard ({kpis.late_orders.count})
            </h2>
            {expandedSection === 'late' ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
          
          {expandedSection !== 'late' && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-red-100">
                <thead className="bg-red-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-red-600 uppercase">Ordre</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-red-600 uppercase">Article</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-red-600 uppercase">Date Due</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-red-600 uppercase">Retard</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-red-50">
                  {kpis.late_orders.orders.map((order, idx) => (
                    <tr key={idx} className="hover:bg-red-50">
                      <td className="px-4 py-2 font-mono text-sm text-slate-900">{order.order_id}</td>
                      <td className="px-4 py-2 font-mono text-sm text-slate-600">{order.article_id}</td>
                      <td className="px-4 py-2 text-sm text-slate-600">
                        {order.due_date?.substring(0, 16).replace('T', ' ')}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-700">
                          +{order.delay_hours}h
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Capacité par machine */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden" data-testid="capacity-table">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
          <h2 className="font-semibold text-slate-800 flex items-center gap-2">
            <BarChart3 size={16} />
            Capacité par Machine (7 jours)
          </h2>
        </div>
        
        <div className="p-4">
          <div className="space-y-4">
            {Object.entries(kpis?.utilization?.by_machine || {}).map(([machineId, data]) => (
              <div key={machineId} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-medium text-slate-700">{machineId}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getUtilizationBg(data.average_utilization)}`}>
                    {data.average_utilization}%
                  </span>
                </div>
                <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${getUtilizationColor(data.average_utilization)} transition-all`}
                    style={{ width: `${Math.min(100, data.average_utilization)}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-500">
                  <span>Charge: {data.total_loaded_hours}h</span>
                  <span>Capacité: {data.total_capacity_hours}h</span>
                  {data.overloaded_days > 0 && (
                    <span className="text-red-600 font-medium">{data.overloaded_days} jour(s) surchargé(s)</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Détail des créneaux de capacité */}
      {capacity?.capacity_slots && (
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden" data-testid="capacity-slots">
          <div 
            className="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between cursor-pointer"
            onClick={() => setExpandedSection(expandedSection === 'slots' ? 'all' : 'slots')}
          >
            <h2 className="font-semibold text-slate-800 flex items-center gap-2">
              <Calendar size={16} />
              Détail des Créneaux ({capacity.capacity_slots.length})
            </h2>
            {expandedSection === 'slots' ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
          
          {expandedSection !== 'slots' && (
            <div className="overflow-x-auto max-h-80">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Machine</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Date</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-slate-500 uppercase">Capacité</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-slate-500 uppercase">Charge</th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-slate-500 uppercase">Dispo</th>
                    <th className="px-4 py-2 text-center text-xs font-medium text-slate-500 uppercase">Taux</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-slate-200">
                  {capacity.capacity_slots.slice(0, 50).map((slot, idx) => (
                    <tr key={idx} className={`hover:bg-slate-50 ${slot.is_overloaded ? 'bg-red-50' : ''}`}>
                      <td className="px-4 py-2 font-mono text-sm text-slate-900">{slot.machine_id}</td>
                      <td className="px-4 py-2 text-sm text-slate-600">{slot.date}</td>
                      <td className="px-4 py-2 text-right text-sm text-slate-600">
                        {Math.round(slot.capacity_minutes / 60)}h
                      </td>
                      <td className="px-4 py-2 text-right text-sm font-medium text-slate-900">
                        {Math.round(slot.loaded_minutes / 60)}h
                      </td>
                      <td className="px-4 py-2 text-right text-sm text-green-600">
                        {Math.round(slot.available_minutes / 60)}h
                      </td>
                      <td className="px-4 py-2 text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getUtilizationBg(slot.utilization_rate)}`}>
                          {slot.utilization_rate}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Timestamp */}
      <div className="text-right text-xs text-slate-400">
        Dernière mise à jour: {kpis?.timestamp?.substring(0, 19).replace('T', ' ')}
      </div>
    </div>
  );
}
