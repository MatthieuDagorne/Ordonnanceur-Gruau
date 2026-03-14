import { Outlet, Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Upload, 
  Building2, 
  Cpu, 
  Calendar, 
  AlertCircle, 
  Shield, 
  ClipboardList, 
  BarChart3, 
  FolderKanban,
  Bug,
  Package
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Import CSV', path: '/import', icon: Upload },
  { name: 'Centres de Charge', path: '/centres-de-charge', icon: Building2 },
  { name: 'Machines', path: '/machines', icon: Cpu },
  { name: 'Calendriers', path: '/calendars', icon: Calendar },
  { name: 'Indisponibilités', path: '/unavailability', icon: AlertCircle },
  { name: 'Règles Métier', path: '/rules', icon: Shield },
  { name: 'Ordres Fab.', path: '/orders', icon: ClipboardList },
  { name: 'Stock Projeté', path: '/projected-stock', icon: Package },
  { name: 'Ordonnancement', path: '/scheduling', icon: BarChart3 },
  { name: 'Diagnostic', path: '/diagnostic', icon: Bug },
  { name: 'Scénarios', path: '/scenarios', icon: FolderKanban },
];

export default function Layout() {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="h-14 border-b border-slate-200 flex items-center px-5">
          <h1 className="text-xl font-bold text-slate-900" data-testid="app-title">Scheduler Pro</h1>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
                className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <Icon size={16} strokeWidth={1.5} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 bg-white border-b border-slate-200 flex items-center px-6">
          <div className="flex items-center justify-between w-full">
            <h2 className="text-lg font-semibold text-slate-800">
              {navigation.find((item) => item.path === location.pathname)?.name || 'Dashboard'}
            </h2>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}