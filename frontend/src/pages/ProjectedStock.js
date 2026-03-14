import React, { useEffect, useState } from 'react';
import { Package, AlertTriangle, CheckCircle, TrendingDown, TrendingUp, Calendar, RefreshCw } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function ProjectedStock() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/projected-stock`);
      if (!response.ok) throw new Error('Erreur de chargement');
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="loading">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded" data-testid="error">
        Erreur: {error}
      </div>
    );
  }

  const { projected_stock, consumption_details, summary } = data || {};

  return (
    <div className="space-y-6" data-testid="projected-stock-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Stock Projeté</h1>
          <p className="text-slate-600 mt-1">
            Vue du stock avec consommations et réceptions planifiées
          </p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          data-testid="refresh-btn"
        >
          <RefreshCw size={16} />
          Actualiser
        </button>
      </div>

      {/* Résumé */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4" data-testid="summary-total">
          <div className="flex items-center gap-3">
            <div className="bg-slate-100 p-2 rounded-lg">
              <Package className="text-slate-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-slate-600">Total Articles</p>
              <p className="text-2xl font-bold text-slate-900">{summary?.total_articles || 0}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-sm border border-red-200 p-4" data-testid="summary-shortage">
          <div className="flex items-center gap-3">
            <div className="bg-red-100 p-2 rounded-lg">
              <AlertTriangle className="text-red-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-red-600">En Rupture</p>
              <p className="text-2xl font-bold text-red-700">{summary?.articles_with_shortage || 0}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-sm border border-green-200 p-4" data-testid="summary-ok">
          <div className="flex items-center gap-3">
            <div className="bg-green-100 p-2 rounded-lg">
              <CheckCircle className="text-green-600" size={20} />
            </div>
            <div>
              <p className="text-sm text-green-600">Stock OK</p>
              <p className="text-2xl font-bold text-green-700">{summary?.articles_ok || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tableau du stock projeté */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden" data-testid="stock-table">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
          <h2 className="font-semibold text-slate-900">Projection par Article</h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Article</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Stock Initial</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Consommations</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Réceptions</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Stock Final</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Statut</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Disponibilité</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-slate-200">
              {projected_stock?.map((item) => (
                <tr 
                  key={item.article_id} 
                  className={item.has_shortage ? 'bg-red-50' : ''}
                  data-testid={`stock-row-${item.article_id}`}
                >
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm font-medium text-slate-900">{item.article_id}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-mono text-slate-700">{item.initial_stock}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="flex items-center justify-end gap-1 text-red-600 font-mono">
                      <TrendingDown size={14} />
                      -{item.total_consumption}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="flex items-center justify-end gap-1 text-green-600 font-mono">
                      <TrendingUp size={14} />
                      +{item.total_receipts}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className={`font-mono font-bold ${item.final_stock < 0 ? 'text-red-700' : 'text-slate-900'}`}>
                      {item.final_stock}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {item.has_shortage ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                        <AlertTriangle size={12} />
                        Rupture ({item.shortage_quantity})
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                        <CheckCircle size={12} />
                        OK
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {item.has_shortage && item.availability_date ? (
                      <span className="flex items-center gap-1 text-amber-700 text-xs">
                        <Calendar size={12} />
                        {item.availability_date?.substring(0, 16).replace('T', ' ')}
                      </span>
                    ) : item.has_shortage ? (
                      <span className="text-red-600 text-xs font-medium">Pas de réception prévue</span>
                    ) : (
                      <span className="text-green-600 text-xs">Disponible</span>
                    )}
                  </td>
                </tr>
              ))}
              {(!projected_stock || projected_stock.length === 0) && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    Aucune donnée de stock disponible
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Détails des consommations */}
      {consumption_details && consumption_details.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden" data-testid="consumption-table">
          <div className="px-4 py-3 border-b border-slate-200 bg-slate-50">
            <h2 className="font-semibold text-slate-900">Détail des Consommations par Opération</h2>
          </div>
          
          <div className="overflow-x-auto max-h-96">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Article</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-slate-500 uppercase">Quantité</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Opération</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Ordre</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Date Besoin</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {consumption_details.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="px-4 py-2 font-mono text-sm text-slate-900">{item.article_id}</td>
                    <td className="px-4 py-2 text-right font-mono text-red-600">-{item.quantity}</td>
                    <td className="px-4 py-2 font-mono text-sm text-slate-600">{item.operation_id}</td>
                    <td className="px-4 py-2 font-mono text-sm text-slate-600">{item.order_id}</td>
                    <td className="px-4 py-2 text-xs text-slate-500">
                      {item.due_date?.substring(0, 16).replace('T', ' ') || '-'}
                    </td>
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
