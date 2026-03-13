import { useEffect, useState } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ManufacturingOrders() {
  const [orders, setOrders] = useState([]);
  const [operations, setOperations] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);

  useEffect(() => {
    fetchOrders();
    fetchOperations();
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${API}/manufacturing-orders`);
      setOrders(response.data);
    } catch (error) {
      console.error('Error fetching orders:', error);
    }
  };

  const fetchOperations = async () => {
    try {
      const response = await axios.get(`${API}/operations`);
      setOperations(response.data);
    } catch (error) {
      console.error('Error fetching operations:', error);
    }
  };

  const getOrderOperations = (orderId) => {
    return operations.filter((op) => op.order_id === orderId);
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'in_progress':
        return 'bg-blue-100 text-blue-700';
      case 'pending':
        return 'bg-amber-100 text-amber-700';
      default:
        return 'bg-slate-100 text-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      <h3 className="text-2xl font-semibold text-slate-800">Ordres de Fabrication</h3>

      <div className="bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Article</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Quantité</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Date Besoin</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Statut</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Opérations</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => {
              const orderOps = getOrderOperations(order.id);
              return (
                <tr
                  key={order.id}
                  className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer"
                  onClick={() => setSelectedOrder(order.id === selectedOrder ? null : order.id)}
                  data-testid="order-row"
                >
                  <td className="px-4 py-2 text-sm text-slate-700 font-mono">{order.id}</td>
                  <td className="px-4 py-2 text-sm text-slate-700 font-mono">{order.article}</td>
                  <td className="px-4 py-2 text-sm text-slate-700 font-mono">{order.quantity}</td>
                  <td className="px-4 py-2 text-sm text-slate-700 font-mono">{order.due_date}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs ${getStatusColor(order.status)}`}>
                      {order.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm text-slate-700 font-mono">{orderOps.length}</td>
                </tr>
              );
            })}
            {orders.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-500">
                  Aucun ordre de fabrication. Importez des données via la section Import CSV.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedOrder && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
          <h4 className="text-lg font-semibold text-slate-800 mb-4">Opérations de l'ordre {selectedOrder}</h4>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">N° Op</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Séquence</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Temps Prod (min)</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Temps Réglage (min)</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Machine</th>
                </tr>
              </thead>
              <tbody>
                {getOrderOperations(selectedOrder).map((op) => (
                  <tr key={op.id} className="border-b border-slate-100">
                    <td className="px-4 py-2 text-sm text-slate-700 font-mono">{op.operation_number}</td>
                    <td className="px-4 py-2 text-sm text-slate-700 font-mono">{op.sequence}</td>
                    <td className="px-4 py-2 text-sm text-slate-700 font-mono">{op.production_time_minutes}</td>
                    <td className="px-4 py-2 text-sm text-slate-700 font-mono">{op.setup_time_minutes}</td>
                    <td className="px-4 py-2 text-sm text-slate-700 font-mono">{op.machine_id || 'Non assigné'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}