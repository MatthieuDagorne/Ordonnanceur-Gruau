import { Outlet, Link, useLocation } from 'react-router-dom';
import { useTheme } from '@/contexts/ThemeContext';
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
  TrendingUp,
  Sun,
  Moon,
  Factory,
  ChevronRight,
  Grid3X3
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'APS Dashboard', path: '/aps', icon: TrendingUp },
  { name: 'Import CSV', path: '/import', icon: Upload },
  { name: 'Centres de Charge', path: '/centres-de-charge', icon: Building2 },
  { name: 'Machines', path: '/machines', icon: Cpu },
  { name: 'Calendriers', path: '/calendars', icon: Calendar },
  { name: 'Indisponibilités', path: '/unavailability', icon: AlertCircle },
  { name: 'Règles Métier', path: '/rules', icon: Shield },
  { name: 'Matrice Compat.', path: '/matrix', icon: Grid3X3 },
  { name: 'Ordres Fab.', path: '/orders', icon: ClipboardList },
  { name: 'Ordonnancement', path: '/scheduling', icon: BarChart3 },
  { name: 'Diagnostic', path: '/diagnostic', icon: Bug },
  { name: 'Scénarios', path: '/scenarios', icon: FolderKanban },
];

export default function Layout() {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Sidebar */}
      <aside 
        className="sidebar w-64 flex flex-col border-r animate-slide-in-left"
        style={{ 
          backgroundColor: 'var(--sidebar-bg)', 
          borderColor: 'var(--border)'
        }}
      >
        {/* Logo */}
        <div 
          className="h-16 flex items-center gap-3 px-4 border-b"
          style={{ borderColor: 'rgba(255,255,255,0.1)' }}
        >
          <div 
            className="w-10 h-10 rounded-sm flex items-center justify-center"
            style={{ backgroundColor: 'var(--accent-orange)' }}
          >
            <Factory size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>
              APS Pro
            </h1>
            <p className="text-xs" style={{ color: 'var(--sidebar-text)' }}>Scheduler v2.0</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4 px-2">
          <ul className="space-y-1">
            {navigation.map((item, index) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              
              return (
                <li key={item.path} className={`animate-fade-in-up stagger-${Math.min(index + 1, 5)}`}>
                  <Link
                    to={item.path}
                    className={`sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-sm text-sm font-medium transition-all ${
                      isActive ? 'active' : ''
                    }`}
                    data-testid={`nav-${item.path.replace('/', '') || 'home'}`}
                  >
                    <Icon size={18} />
                    <span className="flex-1">{item.name}</span>
                    {isActive && (
                      <ChevronRight size={14} className="opacity-50" />
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Theme Toggle */}
        <div 
          className="p-4 border-t"
          style={{ borderColor: 'rgba(255,255,255,0.1)' }}
        >
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-between px-3 py-2.5 rounded-sm transition-all hover-lift"
            style={{ 
              backgroundColor: 'var(--sidebar-hover)',
              color: 'var(--sidebar-text)'
            }}
            data-testid="theme-toggle"
          >
            <span className="flex items-center gap-3 text-sm font-medium">
              {theme === 'dark' ? <Moon size={18} /> : <Sun size={18} />}
              {theme === 'dark' ? 'Mode Sombre' : 'Mode Clair'}
            </span>
            <div 
              className="theme-toggle"
              role="switch"
              aria-checked={theme === 'dark'}
            />
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main 
        className="flex-1 overflow-auto"
        style={{ backgroundColor: 'var(--bg-primary)' }}
      >
        {/* Header Bar */}
        <header 
          className="h-14 flex items-center justify-between px-6 border-b sticky top-0 z-10 animate-fade-in-down"
          style={{ 
            backgroundColor: 'var(--surface)', 
            borderColor: 'var(--border)'
          }}
        >
          <div className="flex items-center gap-2">
            <span 
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: 'var(--text-muted)' }}
            >
              Industrial Scheduler Pro
            </span>
            <span style={{ color: 'var(--border-strong)' }}>/</span>
            <span 
              className="text-sm font-medium"
              style={{ color: 'var(--text-primary)' }}
            >
              {navigation.find(n => n.path === location.pathname)?.name || 'Page'}
            </span>
          </div>
          
          <div className="flex items-center gap-4">
            <div 
              className="flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs font-mono"
              style={{ 
                backgroundColor: 'var(--bg-secondary)',
                color: 'var(--text-secondary)'
              }}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse-slow" />
              OR-Tools Ready
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-6 animate-fade-in-up">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
