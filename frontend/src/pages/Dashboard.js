import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { 
  Activity, AlertTriangle, Package, Cpu, ArrowRight,
  TrendingUp, Calendar, Shield, BarChart3, Zap
} from 'lucide-react';

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
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => (
            <div key={i} className="card p-5 animate-shimmer h-24" />
          ))}
        </div>
      </div>
    );
  }

  const cards = [
    {
      title: 'Ordres Total',
      value: stats?.total_orders || 0,
      icon: Package,
      gradient: 'from-blue-500 to-blue-600',
      testId: 'total-orders'
    },
    {
      title: 'En Attente',
      value: stats?.pending_orders || 0,
      icon: Activity,
      gradient: 'from-amber-500 to-orange-500',
      testId: 'pending-orders'
    },
    {
      title: 'En Retard',
      value: stats?.late_orders || 0,
      icon: AlertTriangle,
      gradient: 'from-red-500 to-rose-600',
      testId: 'late-orders'
    },
    {
      title: 'Machines',
      value: stats?.total_machines || 0,
      icon: Cpu,
      gradient: 'from-cyan-500 to-sky-600',
      testId: 'total-machines'
    },
  ];

  const quickActions = [
    { label: 'APS Dashboard', path: '/aps', icon: TrendingUp, description: 'KPIs et capacité' },
    { label: 'Ordonnancement', path: '/scheduling', icon: BarChart3, description: 'Lancer un calcul' },
    { label: 'Règles Métier', path: '/rules', icon: Shield, description: 'Configurer les règles' },
    { label: 'Calendriers', path: '/calendars', icon: Calendar, description: 'Plages horaires' },
  ];

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card, index) => {
          const Icon = card.icon;
          return (
            <div
              key={card.title}
              data-testid={card.testId}
              className={`kpi-card p-5 hover-lift animate-fade-in-up stagger-${index + 1}`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p 
                    className="kpi-label"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {card.title}
                  </p>
                  <p 
                    className="kpi-value mt-1"
                    style={{ color: 'var(--text-primary)', fontFamily: 'Chivo, sans-serif' }}
                  >
                    {card.value}
                  </p>
                </div>
                <div 
                  className={`w-12 h-12 rounded-sm flex items-center justify-center bg-gradient-to-br ${card.gradient}`}
                >
                  <Icon size={24} className="text-white" strokeWidth={1.5} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Actions rapides */}
        <div 
          className="card p-5 animate-fade-in-up stagger-3"
          style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Zap size={20} style={{ color: 'var(--accent-orange)' }} />
            <h3 
              className="text-lg font-semibold"
              style={{ color: 'var(--text-primary)', fontFamily: 'Chivo, sans-serif' }}
            >
              Actions Rapides
            </h3>
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            {quickActions.map((action, i) => {
              const Icon = action.icon;
              return (
                <Link
                  key={action.path}
                  to={action.path}
                  className={`p-4 rounded-sm border transition-all hover-lift animate-fade-in stagger-${i + 1}`}
                  style={{ 
                    backgroundColor: 'var(--bg-secondary)', 
                    borderColor: 'var(--border)' 
                  }}
                  data-testid={`quick-action-${action.path.replace('/', '')}`}
                >
                  <div className="flex items-center gap-3">
                    <Icon size={20} style={{ color: 'var(--accent-blue)' }} />
                    <div className="flex-1">
                      <p 
                        className="text-sm font-medium"
                        style={{ color: 'var(--text-primary)' }}
                      >
                        {action.label}
                      </p>
                      <p 
                        className="text-xs mt-0.5"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        {action.description}
                      </p>
                    </div>
                    <ArrowRight size={16} style={{ color: 'var(--text-muted)' }} />
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Guide de démarrage */}
        <div 
          className="card p-5 animate-fade-in-up stagger-4"
          style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}
        >
          <h3 
            className="text-lg font-semibold mb-4"
            style={{ color: 'var(--text-primary)', fontFamily: 'Chivo, sans-serif' }}
          >
            Guide de Démarrage
          </h3>
          
          <div className="space-y-3">
            {[
              { step: 1, text: 'Importez vos données ERP via', link: '/import', linkText: 'Import CSV' },
              { step: 2, text: 'Configurez votre atelier dans', link: '/centres-de-charge', linkText: 'Centres de Charge' },
              { step: 3, text: 'Définissez vos contraintes dans', link: '/rules', linkText: 'Règles Métier' },
              { step: 4, text: 'Lancez l\'optimisation depuis', link: '/scheduling', linkText: 'Ordonnancement' },
            ].map((item, i) => (
              <div 
                key={item.step} 
                className={`flex items-center gap-3 p-3 rounded-sm transition-colors animate-fade-in stagger-${i + 1}`}
                style={{ backgroundColor: 'var(--bg-secondary)' }}
              >
                <span 
                  className="w-6 h-6 rounded-sm flex items-center justify-center text-xs font-bold"
                  style={{ 
                    backgroundColor: 'var(--accent-blue)', 
                    color: 'white' 
                  }}
                >
                  {item.step}
                </span>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  {item.text}{' '}
                  <Link 
                    to={item.link} 
                    className="font-medium underline-offset-2 hover:underline"
                    style={{ color: 'var(--accent-blue)' }}
                  >
                    {item.linkText}
                  </Link>
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Moteur Info */}
      <div 
        className="rounded-sm p-5 animate-fade-in-up stagger-5"
        style={{ 
          background: 'linear-gradient(135deg, var(--sidebar-bg) 0%, #1E293B 100%)',
          border: '1px solid var(--border)'
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div 
              className="w-12 h-12 rounded-sm flex items-center justify-center"
              style={{ backgroundColor: 'rgba(249, 115, 22, 0.2)' }}
            >
              <BarChart3 size={24} className="text-orange-400" />
            </div>
            <div>
              <h4 
                className="text-white font-semibold"
                style={{ fontFamily: 'Chivo, sans-serif' }}
              >
                Moteur OR-Tools CP-SAT
              </h4>
              <p className="text-slate-400 text-sm">
                Optimisation par programmation par contraintes
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-6 text-xs font-mono text-slate-400">
            <div>
              <span className="text-slate-500">Ordres</span>
              <span className="ml-2 text-white">{stats?.total_orders || 0}</span>
            </div>
            <div>
              <span className="text-slate-500">Machines</span>
              <span className="ml-2 text-white">{stats?.total_machines || 0}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse-slow" />
              <span className="text-emerald-400">Prêt</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
