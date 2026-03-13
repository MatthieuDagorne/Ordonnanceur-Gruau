import { useEffect, useState } from 'react';
import axios from 'axios';
import { Activity, AlertTriangle, Package, Cpu } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-slate-600">Chargement...</div>;
  }

  const cards = [
    {
      title: 'Ordres Total',
      value: stats?.total_orders || 0,
      icon: Package,
      color: 'text-blue-600',
      testId: 'total-orders'
    },
    {
      title: 'En Attente',
      value: stats?.pending_orders || 0,
      icon: Activity,
      color: 'text-amber-600',
      testId: 'pending-orders'
    },
    {
      title: 'En Retard',
      value: stats?.late_orders || 0,
      icon: AlertTriangle,
      color: 'text-red-600',
      testId: 'late-orders'
    },
    {
      title: 'Machines',
      value: stats?.total_machines || 0,
      icon: Cpu,
      color: 'text-sky-600',
      testId: 'total-machines'
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.title}
              data-testid={card.testId}
              className="bg-white border border-slate-200 rounded-sm shadow-sm p-5"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    {card.title}
                  </p>
                  <p className="mt-2 text-3xl font-bold font-mono text-slate-900">
                    {card.value}
                  </p>
                </div>
                <div className={`${card.color}`}>
                  <Icon size={32} strokeWidth={1.5} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
        <h3 className="text-xl font-semibold text-slate-800 mb-4">Vue d'ensemble</h3>
        <p className="text-sm text-slate-600 leading-normal">
          Bienvenue dans l'application d'ordonnancement industriel. Utilisez le menu de gauche pour naviguer entre les différentes sections.
        </p>
        <div className="mt-6 space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-slate-900 mt-1.5"></div>
            <p className="text-sm text-slate-600">Importez vos données ERP via la section <strong>Import CSV</strong></p>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-slate-900 mt-1.5"></div>
            <p className="text-sm text-slate-600">Configurez votre atelier dans <strong>Postes</strong>, <strong>Machines</strong> et <strong>Calendriers</strong></p>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-slate-900 mt-1.5"></div>
            <p className="text-sm text-slate-600">Définissez vos règles métier dans <strong>Règles Métier</strong></p>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-slate-900 mt-1.5"></div>
            <p className="text-sm text-slate-600">Lancez l'ordonnancement depuis <strong>Ordonnancement</strong></p>
          </div>
        </div>
      </div>
    </div>
  );
}