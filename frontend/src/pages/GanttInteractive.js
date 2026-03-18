import { useEffect, useState, useRef, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Download, ZoomIn, ZoomOut, AlertCircle, Clock, Package, Filter, Check, X, Layers, TrendingDown, Zap, FileText, Calendar, Search } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Formater une date en format complet français
const formatFullDate = (date) => {
  const days = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
  const months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  return `${days[date.getDay()]} ${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}`;
};

export default function GanttInteractive() {
  const { scenarioId } = useParams();
  const navigate = useNavigate();
  const [ganttData, setGanttData] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [loading, setLoading] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [hoveredTask, setHoveredTask] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [selectedCentres, setSelectedCentres] = useState([]);
  const containerRef = useRef(null);
  
  // Nouveaux filtres
  const [filterOrderId, setFilterOrderId] = useState('');
  const [filterArticleId, setFilterArticleId] = useState('');
  const [dateRangeStart, setDateRangeStart] = useState(null);
  const [dateRangeEnd, setDateRangeEnd] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  
  // État pour la section des erreurs collapsible
  const [errorsExpanded, setErrorsExpanded] = useState(false);
  const [diagnosticsExpanded, setDiagnosticsExpanded] = useState(false);

  useEffect(() => {
    fetchData();
  }, [scenarioId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [ganttRes, scenarioRes] = await Promise.all([
        axios.get(`${API}/gantt/data/${scenarioId}`),
        axios.get(`${API}/scenarios/${scenarioId}`)
      ]);
      setGanttData(ganttRes.data);
      setScenario(scenarioRes.data);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get(`${API}/export/schedule/${scenarioId}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `schedule_${scenarioId}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Export réussi');
    } catch (error) {
      toast.error("Erreur lors de l'export");
    }
  };

  // Formater le temps relatif
  const formatTime = (minutes) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h${mins.toString().padStart(2, '0')}`;
  };

  // Formater juste l'heure (HH:MM)
  const formatHourMinute = (date) => {
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Formater la date courte (DD/MM)
  const formatShortDate = (date) => {
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit'
    });
  };

  // Calculer l'intervalle basé sur le zoom
  const getTimeInterval = (zoomLevel) => {
    if (zoomLevel >= 2) return 15;      // Zoom fort: 15 minutes
    if (zoomLevel >= 1.5) return 30;    // Zoom moyen: 30 minutes  
    if (zoomLevel >= 1) return 60;       // Zoom standard: 1 heure
    return 120;                          // Zoom faible: 2 heures
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return '-';
    try {
      const date = new Date(isoString);
      return date.toLocaleString('fr-FR', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return isoString;
    }
  };

  // Toggle centre de charge dans le filtre
  const toggleCentre = (centreId) => {
    if (selectedCentres.includes(centreId)) {
      setSelectedCentres(selectedCentres.filter(c => c !== centreId));
    } else {
      setSelectedCentres([...selectedCentres, centreId]);
    }
  };

  // Extraire les listes uniques d'ordres et d'articles pour les filtres
  const { uniqueOrders, uniqueArticles, scenarioDateRange } = useMemo(() => {
    if (!ganttData?.machines) return { uniqueOrders: [], uniqueArticles: [], scenarioDateRange: { min: null, max: null } };
    
    const orders = new Set();
    const articles = new Set();
    let minDate = null;
    let maxDate = null;
    
    ganttData.machines.forEach(machine => {
      machine.tasks?.forEach(task => {
        if (task.order_id) orders.add(task.order_id);
        if (task.article_id) articles.add(task.article_id);
        
        // Calculer les dates min/max
        if (task.start_datetime) {
          const startDate = new Date(task.start_datetime);
          if (!minDate || startDate < minDate) minDate = startDate;
        }
        if (task.end_datetime) {
          const endDate = new Date(task.end_datetime);
          if (!maxDate || endDate > maxDate) maxDate = endDate;
        }
      });
    });
    
    return {
      uniqueOrders: Array.from(orders).sort(),
      uniqueArticles: Array.from(articles).sort(),
      scenarioDateRange: { min: minDate, max: maxDate }
    };
  }, [ganttData?.machines]);

  // Filtrer les machines avec tous les critères (centre, order_id, article_id, plage de dates)
  const filteredMachines = useMemo(() => {
    if (!ganttData?.machines) return [];
    
    return ganttData.machines.map(machine => {
      // Filtrer d'abord par centre de charge
      if (selectedCentres.length > 0 && !selectedCentres.includes(machine.centre_de_charge_id)) {
        return { ...machine, tasks: [] };
      }
      
      // Filtrer les tâches par order_id, article_id et plage de dates
      const filteredTasks = machine.tasks?.filter(task => {
        // Filtre par order_id (recherche partielle insensible à la casse)
        if (filterOrderId && !task.order_id?.toLowerCase().includes(filterOrderId.toLowerCase())) return false;
        
        // Filtre par article_id (recherche partielle insensible à la casse)
        if (filterArticleId && !task.article_id?.toLowerCase().includes(filterArticleId.toLowerCase())) return false;
        
        // Filtre par plage de dates
        if (dateRangeStart || dateRangeEnd) {
          const taskStart = task.start_datetime ? new Date(task.start_datetime) : null;
          const taskEnd = task.end_datetime ? new Date(task.end_datetime) : null;
          
          if (dateRangeStart && taskEnd) {
            const rangeStart = new Date(dateRangeStart);
            rangeStart.setHours(0, 0, 0, 0);
            if (taskEnd < rangeStart) return false;
          }
          
          if (dateRangeEnd && taskStart) {
            const rangeEnd = new Date(dateRangeEnd);
            rangeEnd.setHours(23, 59, 59, 999);
            if (taskStart > rangeEnd) return false;
          }
        }
        
        return true;
      }) || [];
      
      return { ...machine, tasks: filteredTasks };
    }).filter(m => m.tasks.length > 0 || selectedCentres.length === 0);
  }, [ganttData?.machines, selectedCentres, filterOrderId, filterArticleId, dateRangeStart, dateRangeEnd]);

  // Réinitialiser les filtres
  const resetFilters = () => {
    setFilterOrderId('');
    setFilterArticleId('');
    setDateRangeStart(null);
    setDateRangeEnd(null);
    setSelectedCentres([]);
  };

  // Vérifier si des filtres sont actifs
  const hasActiveFilters = filterOrderId || filterArticleId || dateRangeStart || dateRangeEnd || selectedCentres.length > 0;

  // Fonction pour calculer les zones de fermeture pour une machine spécifique
  // Les positions sont relatives au début visible du Gantt (pas au scheduling_start)
  const calculateClosurePeriods = (machineCalendar, schedulingStart, totalMinutes, minMinutes) => {
    if (!schedulingStart || !machineCalendar) return [];
    
    const periods = [];
    
    // Utiliser start_time/end_time (format HH:MM) si disponibles, sinon fallback sur start_hour/end_hour
    let workStartHour = 0;
    let workStartMinute = 0;
    let workEndHour = 24;
    let workEndMinute = 0;
    
    if (machineCalendar.start_time) {
      const [h, m] = machineCalendar.start_time.split(':').map(Number);
      workStartHour = h;
      workStartMinute = m || 0;
    } else {
      workStartHour = machineCalendar.start_hour ?? 0;
    }
    
    if (machineCalendar.end_time) {
      const [h, m] = machineCalendar.end_time.split(':').map(Number);
      workEndHour = h;
      workEndMinute = m || 0;
    } else {
      workEndHour = machineCalendar.end_hour ?? 24;
    }
    
    const workingDays = new Set(machineCalendar.working_days || [0, 1, 2, 3, 4, 5, 6]);
    
    // Si calendrier 24/7, pas de zones de fermeture
    const is24h7 = workStartHour === 0 && workStartMinute === 0 && workEndHour === 24 && workEndMinute === 0 && workingDays.size === 7;
    if (is24h7) {
      return [];
    }
    
    // Le scheduling_start est la référence absolue
    const schedStart = new Date(schedulingStart);
    
    // Le Gantt affiche à partir de (scheduling_start + min_minutes)
    // jusqu'à (scheduling_start + min_minutes + total_minutes)
    const ganttStartTime = new Date(schedStart.getTime() + minMinutes * 60000);
    const ganttEndTime = new Date(schedStart.getTime() + (minMinutes + totalMinutes) * 60000);
    
    // Nombre de jours à parcourir
    const totalDays = Math.ceil((totalMinutes + 24 * 60) / (24 * 60));
    
    for (let d = -1; d < totalDays + 1; d++) {
      // Date du jour courant (basée sur le début visible du Gantt)
      const dayDate = new Date(ganttStartTime);
      dayDate.setHours(0, 0, 0, 0);
      dayDate.setDate(dayDate.getDate() + d);
      
      const dayOfWeek = dayDate.getDay(); // 0=Dimanche, 1=Lundi, ... 6=Samedi
      // Convertir en format Python (0=Lundi, 6=Dimanche)
      const pythonDayOfWeek = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
      
      // Si jour non travaillé, tout le jour est fermé
      if (!workingDays.has(pythonDayOfWeek)) {
        // Position dans le Gantt = (heure absolue - gantt_start) en minutes
        const closureStartMin = Math.floor((dayDate - ganttStartTime) / 60000);
        const closureEndMin = closureStartMin + 24 * 60;
        
        if (closureEndMin > 0 && closureStartMin < totalMinutes) {
          periods.push({
            start: Math.max(0, closureStartMin),
            end: Math.min(totalMinutes, closureEndMin),
            reason: 'Jour non travaillé'
          });
        }
        continue;
      }
      
      // Zone de fermeture du matin (00:00 -> heure d'ouverture)
      if (workStartHour > 0 || workStartMinute > 0) {
        const closureStartDate = new Date(dayDate);
        const closureEndDate = new Date(dayDate);
        closureEndDate.setHours(workStartHour, workStartMinute, 0, 0);
        
        // Position dans le Gantt
        const closureStartMin = Math.floor((closureStartDate - ganttStartTime) / 60000);
        const closureEndMin = Math.floor((closureEndDate - ganttStartTime) / 60000);
        
        // Formater l'heure pour l'affichage
        const timeStr = workStartMinute > 0 ? `${workStartHour}h${workStartMinute.toString().padStart(2, '0')}` : `${workStartHour}h`;
        
        if (closureEndMin > 0 && closureStartMin < totalMinutes) {
          periods.push({
            start: Math.max(0, closureStartMin),
            end: Math.min(totalMinutes, closureEndMin),
            reason: `Avant ${timeStr}`
          });
        }
      }
      
      // Zone de fermeture du soir (heure de fermeture -> 24:00)
      if (workEndHour < 24 || (workEndHour === 24 && workEndMinute > 0)) {
        const closureStartDate = new Date(dayDate);
        closureStartDate.setHours(workEndHour, workEndMinute, 0, 0);
        const closureEndDate = new Date(dayDate);
        closureEndDate.setDate(closureEndDate.getDate() + 1); // Minuit du jour suivant
        closureEndDate.setHours(0, 0, 0, 0);
        
        // Position dans le Gantt
        const closureStartMin = Math.floor((closureStartDate - ganttStartTime) / 60000);
        const closureEndMin = Math.floor((closureEndDate - ganttStartTime) / 60000);
        
        // Formater l'heure pour l'affichage
        const timeStr = workEndMinute > 0 ? `${workEndHour}h${workEndMinute.toString().padStart(2, '0')}` : `${workEndHour}h`;
        
        if (closureEndMin > 0 && closureStartMin < totalMinutes) {
          periods.push({
            start: Math.max(0, closureStartMin),
            end: Math.min(totalMinutes, closureEndMin),
            reason: `Après ${timeStr}`
          });
        }
      }
    }
    
    // Fusionner les périodes qui se chevauchent
    if (periods.length > 0) {
      periods.sort((a, b) => a.start - b.start);
      const merged = [periods[0]];
      for (let i = 1; i < periods.length; i++) {
        const last = merged[merged.length - 1];
        if (periods[i].start <= last.end) {
          last.end = Math.max(last.end, periods[i].end);
        } else {
          merged.push(periods[i]);
        }
      }
      return merged;
    }
    
    return periods;
  };

  // Calcul des positions et dimensions
  const pixelsPerMinute = 2 * zoom;
  const rowHeight = 48;
  const headerHeight = 60;
  const sidebarWidth = 180;

  // Extraire les données du Gantt (avec valeurs par défaut)
  const time_range = ganttData?.time_range || {};
  const total_tasks = ganttData?.total_tasks || 0;
  const scheduling_start = ganttData?.scheduling_start;
  const centres_de_charge = ganttData?.centres_de_charge || [];
  const calendars = ganttData?.calendars || [];
  const totalWidth = (time_range?.total_minutes || 480) * pixelsPerMinute;

  // Générer les marqueurs de temps avec timeline continue par heures
  // Avec séparateurs de jour à minuit
  const timeMarkers = useMemo(() => {
    if (!scheduling_start || !time_range?.total_minutes) return [];
    
    const markers = [];
    const interval = getTimeInterval(zoom);
    const startDate = new Date(scheduling_start);
    const minMinutes = time_range.min_minutes || 0;
    const maxMinutes = time_range.total_minutes || 480;
    
    // Calculer la première minute alignée sur l'intervalle
    const startDateTime = new Date(startDate.getTime() + minMinutes * 60000);
    
    // Arrondir au prochain intervalle
    const startMin = startDateTime.getMinutes();
    const alignedMin = Math.ceil(startMin / interval) * interval;
    const alignedStartDate = new Date(startDateTime);
    alignedStartDate.setMinutes(alignedMin % 60);
    alignedStartDate.setSeconds(0);
    alignedStartDate.setMilliseconds(0);
    if (alignedMin >= 60) {
      alignedStartDate.setHours(alignedStartDate.getHours() + 1);
      alignedStartDate.setMinutes(0);
    }
    
    // Parcourir la timeline
    let currentDate = alignedStartDate;
    let lastDay = -1;
    
    while (true) {
      const minutesSinceStart = Math.round((currentDate.getTime() - startDate.getTime()) / 60000);
      const relativeMinutes = minutesSinceStart - minMinutes;
      
      if (relativeMinutes > maxMinutes) break;
      if (relativeMinutes >= 0) {
        const currentDay = currentDate.getDate();
        const isNewDay = lastDay !== -1 && currentDay !== lastDay;
        const isMidnight = currentDate.getHours() === 0 && currentDate.getMinutes() === 0;
        
        markers.push({
          minutes: relativeMinutes,
          label: formatHourMinute(currentDate),
          isNewDay: isNewDay || isMidnight,
          dayLabel: isNewDay || isMidnight ? formatShortDate(currentDate) : null,
          fullDate: currentDate.toISOString()
        });
        
        lastDay = currentDay;
      }
      
      // Avancer à l'intervalle suivant
      currentDate = new Date(currentDate.getTime() + interval * 60000);
    }
    
    return markers;
  }, [scheduling_start, time_range?.min_minutes, time_range?.total_minutes, zoom]);

  // Calculer les séparateurs de jour (lignes verticales à minuit) avec format complet
  const daySeparators = useMemo(() => {
    if (!scheduling_start || !time_range?.total_minutes) return [];
    
    const separators = [];
    const startDate = new Date(scheduling_start);
    const minMinutes = time_range.min_minutes || 0;
    const maxMinutes = time_range.total_minutes || 480;
    
    // Trouver le premier jour (début de journée)
    const firstDate = new Date(startDate.getTime() + minMinutes * 60000);
    let dayStart = new Date(firstDate);
    dayStart.setHours(0, 0, 0, 0);
    
    // Ajouter le premier jour s'il commence pendant les heures de travail
    const firstDayMinutes = Math.round((dayStart.getTime() - startDate.getTime()) / 60000);
    if (firstDayMinutes >= minMinutes - 24*60) {
      separators.push({
        minutes: Math.max(0, firstDayMinutes - minMinutes),
        label: formatFullDate(dayStart),
        date: new Date(dayStart)
      });
    }
    
    // Parcourir les jours suivants
    dayStart.setDate(dayStart.getDate() + 1);
    
    while (true) {
      const minutesSinceStart = Math.round((dayStart.getTime() - startDate.getTime()) / 60000);
      const relativeMinutes = minutesSinceStart - minMinutes;
      
      if (relativeMinutes > maxMinutes) break;
      if (relativeMinutes >= 0) {
        separators.push({
          minutes: relativeMinutes,
          label: formatFullDate(dayStart),
          date: new Date(dayStart)
        });
      }
      
      dayStart = new Date(dayStart.getTime() + 24 * 60 * 60000);
    }
    
    return separators;
  }, [scheduling_start, time_range?.min_minutes, time_range?.total_minutes]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--brand-primary)' }} />
      </div>
    );
  }

  if (!ganttData || !ganttData.machines) {
    return (
      <div className="flex items-center justify-center h-96" style={{ color: 'var(--text-muted)' }}>
        Données non disponibles
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="gantt-interactive">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/scenarios')}
            className="inline-flex items-center gap-2 transition-colors hover:opacity-80"
            style={{ color: 'var(--text-secondary)' }}
            data-testid="back-btn"
          >
            <ArrowLeft size={16} />
            Retour
          </button>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {ganttData.scenario_name || 'Planning Gantt'}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
            className="p-2 rounded-lg transition-colors"
            style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
            title="Zoom -"
            data-testid="zoom-out-btn"
          >
            <ZoomOut size={16} />
          </button>
          <div className="text-center min-w-[80px]">
            <span className="text-sm font-mono block" style={{ color: 'var(--text-secondary)' }}>
              {(zoom * 100).toFixed(0)}%
            </span>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {getTimeInterval(zoom) === 15 ? '15 min' : 
               getTimeInterval(zoom) === 30 ? '30 min' : 
               getTimeInterval(zoom) === 60 ? '1 heure' : '2 heures'}
            </span>
          </div>
          <button
            onClick={() => setZoom(Math.min(3, zoom + 0.25))}
            className="p-2 rounded-lg transition-colors"
            style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
            title="Zoom +"
            data-testid="zoom-in-btn"
          >
            <ZoomIn size={16} />
          </button>
          <button
            onClick={handleExport}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
            style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
            data-testid="export-btn"
          >
            <Download size={16} />
            Exporter
          </button>
          <Link
            to={`/diagnostic/${scenarioId}`}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
            style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}
            data-testid="diagnostic-btn"
          >
            <FileText size={16} />
            Diagnostic
          </Link>
          <Link
            to={`/projected-stock/${scenarioId}`}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
            style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}
            data-testid="stock-btn"
          >
            <TrendingDown size={16} />
            Stock Projeté
          </Link>
        </div>
      </div>

      {/* Panneau de filtres avancés */}
      <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <div className="flex items-center justify-between mb-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 text-sm font-medium"
            style={{ color: 'var(--text-secondary)' }}
            data-testid="toggle-filters-btn"
          >
            <Filter size={16} />
            Filtres avancés
            {hasActiveFilters && (
              <span className="px-2 py-0.5 rounded-full text-xs" style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}>
                Actifs
              </span>
            )}
          </button>
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors"
              style={{ color: 'var(--status-error)' }}
              data-testid="reset-filters-btn"
            >
              <X size={14} />
              Réinitialiser tout
            </button>
          )}
        </div>
        
        {showFilters && (
          <div className="space-y-4 pt-3 border-t" style={{ borderColor: 'var(--border-default)' }}>
            {/* Ligne 1: Filtres par OF et Article (saisie texte avec suggestions) */}
            <div className="grid grid-cols-2 gap-4">
              {/* Filtre par Ordre de Fabrication */}
              <div className="relative">
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-muted)' }}>
                  Ordre de Fabrication
                </label>
                <div className="relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    value={filterOrderId}
                    onChange={(e) => setFilterOrderId(e.target.value)}
                    placeholder="Rechercher un OF..."
                    className="w-full pl-9 pr-8 py-2 rounded-lg text-sm"
                    style={{ 
                      backgroundColor: 'var(--bg-sunken)', 
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-default)'
                    }}
                    list="order-suggestions"
                    data-testid="filter-order-input"
                  />
                  {filterOrderId && (
                    <button
                      onClick={() => setFilterOrderId('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-opacity-20"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>
                <datalist id="order-suggestions">
                  {uniqueOrders.map(orderId => (
                    <option key={orderId} value={orderId} />
                  ))}
                </datalist>
              </div>
              
              {/* Filtre par Article */}
              <div className="relative">
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-muted)' }}>
                  Article
                </label>
                <div className="relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    value={filterArticleId}
                    onChange={(e) => setFilterArticleId(e.target.value)}
                    placeholder="Rechercher un article..."
                    className="w-full pl-9 pr-8 py-2 rounded-lg text-sm"
                    style={{ 
                      backgroundColor: 'var(--bg-sunken)', 
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-default)'
                    }}
                    list="article-suggestions"
                    data-testid="filter-article-input"
                  />
                  {filterArticleId && (
                    <button
                      onClick={() => setFilterArticleId('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-opacity-20"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>
                <datalist id="article-suggestions">
                  {uniqueArticles.map(articleId => (
                    <option key={articleId} value={articleId} />
                  ))}
                </datalist>
              </div>
            </div>
            
            {/* Ligne 2: Plage de dates */}
            <div>
              <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-muted)' }}>
                Plage de dates
                {scenarioDateRange.min && scenarioDateRange.max && (
                  <span className="ml-2 font-normal" style={{ color: 'var(--text-muted)' }}>
                    (Scénario: {scenarioDateRange.min.toLocaleDateString('fr-FR')} - {scenarioDateRange.max.toLocaleDateString('fr-FR')})
                  </span>
                )}
              </label>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Du</span>
                  <input
                    type="date"
                    value={dateRangeStart || ''}
                    onChange={(e) => setDateRangeStart(e.target.value || null)}
                    className="px-3 py-2 rounded-lg text-sm"
                    style={{ 
                      backgroundColor: 'var(--bg-sunken)', 
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-default)'
                    }}
                    data-testid="date-range-start"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Au</span>
                  <input
                    type="date"
                    value={dateRangeEnd || ''}
                    onChange={(e) => setDateRangeEnd(e.target.value || null)}
                    className="px-3 py-2 rounded-lg text-sm"
                    style={{ 
                      backgroundColor: 'var(--bg-sunken)', 
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-default)'
                    }}
                    data-testid="date-range-end"
                  />
                </div>
              </div>
            </div>
            
            {/* Ligne 3: Centres de charge */}
            {centres_de_charge && centres_de_charge.length > 0 && (
              <div>
                <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
                  Centres de Charge
                </label>
                <div className="flex flex-wrap gap-2">
                  {centres_de_charge.map(centre => (
                    <button
                      key={centre.id}
                      onClick={() => toggleCentre(centre.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
                      style={{
                        backgroundColor: selectedCentres.includes(centre.id) ? 'var(--brand-primary)' : 'var(--bg-sunken)',
                        color: selectedCentres.includes(centre.id) ? 'white' : 'var(--text-secondary)',
                        border: `1px solid ${selectedCentres.includes(centre.id) ? 'transparent' : 'var(--border-default)'}`
                      }}
                      data-testid={`filter-centre-${centre.id}`}
                    >
                      {selectedCentres.includes(centre.id) && <Check size={14} />}
                      {centre.nom || centre.id}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Résumé des filtres actifs */}
        {hasActiveFilters && (
          <div className="mt-3 pt-3 border-t flex items-center gap-2 flex-wrap" style={{ borderColor: 'var(--border-default)' }}>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Filtres actifs:</span>
            {filterOrderId && (
              <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
                OF: {filterOrderId}
              </span>
            )}
            {filterArticleId && (
              <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
                Article: {filterArticleId}
              </span>
            )}
            {(dateRangeStart || dateRangeEnd) && (
              <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
                Dates: {dateRangeStart || '...'} → {dateRangeEnd || '...'}
              </span>
            )}
            {selectedCentres.length > 0 && (
              <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
                {selectedCentres.length} centre(s)
              </span>
            )}
            <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>
              ({filteredMachines.reduce((acc, m) => acc + m.tasks.length, 0)} opérations affichées)
            </span>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-6 gap-4">
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-2 mb-1">
            <Package size={16} style={{ color: 'var(--brand-primary)' }} />
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Opérations</span>
          </div>
          <p className="text-2xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
            {total_tasks}
            {ganttData?.operations_beyond_horizon > 0 && (
              <span className="text-sm font-normal ml-1" style={{ color: 'var(--text-muted)' }}>
                / {ganttData.total_operations_scheduled}
              </span>
            )}
          </p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-2 mb-1">
            <Clock size={16} style={{ color: 'var(--status-info)' }} />
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Durée totale</span>
          </div>
          <p className="text-2xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
            {formatTime(time_range?.total_minutes || 0)}
          </p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-2 mb-1">
            <Layers size={16} style={{ color: 'var(--status-success)' }} />
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Machines</span>
          </div>
          <p className="text-2xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
            {filteredMachines.length}
            {selectedCentres.length > 0 && (
              <span className="text-sm font-normal ml-1" style={{ color: 'var(--text-muted)' }}>
                / {ganttData.machines.length}
              </span>
            )}
          </p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-2 mb-1">
            <Calendar size={16} style={{ color: 'var(--accent-primary)' }} />
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Horizon Affiché</span>
          </div>
          <p className="text-xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
            {ganttData?.display_horizon_days > 0 ? `${ganttData.display_horizon_days} jours` : 'Tout'}
          </p>
          {ganttData?.operations_beyond_horizon > 0 && (
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
              +{ganttData.operations_beyond_horizon} ops au-delà
            </p>
          )}
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Statut</span>
          </div>
          <p className="text-lg font-bold" style={{ color: ganttData.status === 'OPTIMAL' ? 'var(--status-success)' : 'var(--status-info)' }}>
            {ganttData.status}
          </p>
        </div>
        {/* Badge Opérations Non Planifiées */}
        {scenario?.schedule_data?.unscheduled_count > 0 && (
          <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--status-error)' }}>
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle size={16} style={{ color: 'var(--status-error)' }} />
              <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--status-error)' }}>Non planifiées</span>
            </div>
            <p className="text-2xl font-bold font-mono" style={{ color: 'var(--status-error)' }}>
              {scenario.schedule_data.unscheduled_count}
            </p>
          </div>
        )}
      </div>

      {/* Gantt Chart */}
      <div 
        className="rounded-lg overflow-hidden"
        style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
        data-testid="gantt-chart"
      >
        <div className="overflow-x-auto" ref={containerRef}>
          <div style={{ minWidth: sidebarWidth + totalWidth + 40 }}>
            {/* Timeline Header avec heures continues et séparateurs de jour */}
            <div className="flex" style={{ height: headerHeight + 20, borderBottom: '1px solid var(--border-default)' }}>
              <div 
                className="flex-shrink-0 flex items-center justify-center font-semibold text-sm"
                style={{ width: sidebarWidth, backgroundColor: 'var(--bg-sunken)', color: 'var(--text-muted)', borderRight: '1px solid var(--border-default)' }}
              >
                Machine
              </div>
              <div className="relative flex-1" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                {/* Séparateurs de jour avec date complète */}
                {daySeparators.map((sep, idx) => (
                  <div
                    key={`sep-${idx}`}
                    className="absolute top-0 bottom-0"
                    style={{ 
                      left: sep.minutes * pixelsPerMinute,
                      borderLeft: '3px solid #1e40af',
                      zIndex: 10
                    }}
                  >
                    <div 
                      className="absolute top-0 left-2 py-1.5 px-3 rounded-lg shadow-md"
                      style={{ 
                        backgroundColor: '#1e40af',
                        color: '#ffffff',
                        fontSize: '12px',
                        fontWeight: '700',
                        whiteSpace: 'nowrap',
                        letterSpacing: '0.01em',
                        textShadow: '0 1px 2px rgba(0,0,0,0.2)'
                      }}
                    >
                      {sep.label}
                    </div>
                  </div>
                ))}
                
                {/* Marqueurs d'heures */}
                {timeMarkers.map((marker, idx) => (
                  <div
                    key={idx}
                    className="absolute flex flex-col justify-end pb-1"
                    style={{ 
                      left: marker.minutes * pixelsPerMinute,
                      top: 16,
                      bottom: 0,
                      borderLeft: marker.isNewDay ? '2px solid var(--accent-primary)' : '1px solid var(--border-default)'
                    }}
                  >
                    <span 
                      className="ml-1 text-xs font-mono whitespace-nowrap" 
                      style={{ color: marker.isNewDay ? 'var(--accent-primary)' : 'var(--text-muted)' }}
                    >
                      {marker.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Machine Rows */}
            {filteredMachines.map((machine, idx) => (
              <div 
                key={machine.machine_id}
                className="flex"
                style={{ 
                  height: rowHeight,
                  backgroundColor: idx % 2 === 0 ? 'var(--bg-elevated)' : 'var(--bg-sunken)',
                  borderBottom: '1px solid var(--border-default)'
                }}
              >
                {/* Machine Label */}
                <div 
                  className="flex-shrink-0 flex items-center px-3 gap-2"
                  style={{ 
                    width: sidebarWidth, 
                    borderRight: '1px solid var(--border-default)'
                  }}
                >
                  <div 
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: machine.color }}
                  />
                  <div className="overflow-hidden min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                      {machine.machine_id}
                    </p>
                    <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                      {machine.centre_de_charge_nom || machine.centre_de_charge_id} • {machine.tasks?.length || 0} ops
                    </p>
                  </div>
                </div>

                {/* Tasks */}
                <div className="relative flex-1">
                  {/* Closure periods (gray zones) - spécifiques à cette machine */}
                  {calculateClosurePeriods(
                    machine.calendar, 
                    scheduling_start, 
                    time_range?.total_minutes || 480,
                    time_range?.min_minutes || 0
                  ).map((period, pIdx) => (
                    <div
                      key={`closure-${machine.machine_id}-${pIdx}`}
                      className="absolute top-0 bottom-0"
                      style={{
                        left: period.start * pixelsPerMinute,
                        width: Math.max((period.end - period.start) * pixelsPerMinute, 1),
                        backgroundColor: 'rgba(100, 100, 100, 0.3)',
                        pointerEvents: 'none',
                        zIndex: 1
                      }}
                      title={period.reason}
                    />
                  ))}
                  
                  {/* Grid lines - avec séparateurs de jour plus marqués */}
                  {daySeparators.map((sep, sIdx) => (
                    <div
                      key={`grid-sep-${sIdx}`}
                      className="absolute top-0 bottom-0"
                      style={{ 
                        left: sep.minutes * pixelsPerMinute,
                        borderLeft: '2px solid var(--accent-primary)',
                        opacity: 0.5,
                        zIndex: 2
                      }}
                    />
                  ))}
                  {timeMarkers.map((marker, mIdx) => (
                    <div
                      key={mIdx}
                      className="absolute top-0 bottom-0"
                      style={{ 
                        left: marker.minutes * pixelsPerMinute,
                        borderLeft: marker.isNewDay ? '2px solid var(--accent-primary)' : '1px dashed var(--border-default)',
                        opacity: marker.isNewDay ? 0.5 : 0.3
                      }}
                    />
                  ))}
                  
                  {/* Task bars */}
                  {machine.tasks?.map(task => {
                    const left = (task.start_minutes - (time_range?.min_minutes || 0)) * pixelsPerMinute;
                    const width = Math.max(task.duration_minutes * pixelsPerMinute, 20);
                    
                    // Indicateur matières
                    const hasMaterialIssue = task.materials_count > 0 && !task.materials_ok;
                    
                    return (
                      <div
                        key={task.id}
                        className="absolute top-1 bottom-1 rounded cursor-pointer transition-all hover:brightness-110"
                        style={{
                          left: left,
                          width: width,
                          backgroundColor: task.is_urgent ? '#eab308' : task.is_late ? '#EF4444' : hasMaterialIssue ? '#F59E0B' : task.color,
                          border: task.is_urgent ? '2px solid #ca8a04' : task.is_late ? '2px solid #B91C1C' : hasMaterialIssue ? '2px solid #D97706' : 'none'
                        }}
                        onMouseEnter={(e) => {
                          setHoveredTask(task);
                          setTooltipPosition({ x: e.clientX, y: e.clientY });
                        }}
                        onMouseMove={(e) => {
                          setTooltipPosition({ x: e.clientX, y: e.clientY });
                        }}
                        onMouseLeave={() => setHoveredTask(null)}
                        data-testid={`task-${task.id}`}
                      >
                        <div className="px-1 py-0.5 text-white text-xs font-medium truncate h-full flex items-center gap-1">
                          {task.is_urgent && width > 40 && <Zap size={10} />}
                          {width > 60 ? task.operation_id : ''}
                        </div>
                        {task.is_urgent && (
                          <Zap size={12} className="absolute top-0.5 right-0.5 text-white" />
                        )}
                        {task.is_late && !task.is_urgent && (
                          <AlertCircle size={12} className="absolute top-0.5 right-0.5 text-white" />
                        )}
                        {hasMaterialIssue && !task.is_late && !task.is_urgent && (
                          <Package size={12} className="absolute top-0.5 right-0.5 text-white" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tooltip enrichi - suit le curseur */}
      {hoveredTask && (
        <div 
          className="fixed z-50 p-4 rounded-lg shadow-lg pointer-events-none"
          style={{ 
            backgroundColor: 'var(--bg-elevated)', 
            border: '1px solid var(--border-default)',
            left: Math.min(tooltipPosition.x + 15, window.innerWidth - 380),
            top: Math.min(tooltipPosition.y + 15, window.innerHeight - 400),
            maxWidth: 360
          }}
        >
          <div className="space-y-3 text-sm">
            {/* Header */}
            <div className="flex items-center gap-2 pb-2 flex-wrap" style={{ borderBottom: '1px solid var(--border-default)' }}>
              <div className="w-3 h-3 rounded" style={{ backgroundColor: hoveredTask.color }} />
              <span className="font-bold" style={{ color: 'var(--text-primary)' }}>
                {hoveredTask.operation_id}
              </span>
              {hoveredTask.is_urgent && (
                <span className="px-1.5 py-0.5 rounded text-xs font-medium flex items-center gap-1" style={{ backgroundColor: 'rgba(234, 179, 8, 0.2)', color: '#eab308' }}>
                  <Zap size={10} />
                  URGENT
                </span>
              )}
              {hoveredTask.is_late && (
                <span className="px-1.5 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: 'var(--status-error-bg)', color: 'var(--status-error)' }}>
                  EN RETARD
                </span>
              )}
              {!hoveredTask.materials_ok && hoveredTask.materials_count > 0 && (
                <span className="px-1.5 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: 'var(--status-warning-bg)', color: 'var(--status-warning)' }}>
                  MATIÈRE
                </span>
              )}
            </div>
            
            {/* Infos générales */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <span style={{ color: 'var(--text-muted)' }}>Ordre:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{hoveredTask.order_id}</span>
              
              <span style={{ color: 'var(--text-muted)' }}>Tâche:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>
                {hoveredTask.tache_description || hoveredTask.tache_id || '-'}
              </span>
              
              <span style={{ color: 'var(--text-muted)' }}>Article:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>
                {hoveredTask.article_id || '-'}
                {hoveredTask.article_description && (
                  <span className="block text-xs" style={{ color: 'var(--text-muted)' }}>
                    {hoveredTask.article_description}
                  </span>
                )}
              </span>
              
              {hoveredTask.order_quantity > 0 && (
                <>
                  <span style={{ color: 'var(--text-muted)' }}>Qté fabriquée:</span>
                  <span className="font-mono font-bold" style={{ color: 'var(--accent-primary)' }}>{hoveredTask.order_quantity}</span>
                </>
              )}
              
              <span style={{ color: 'var(--text-muted)' }}>Début:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{formatDateTime(hoveredTask.start)}</span>
              
              <span style={{ color: 'var(--text-muted)' }}>Fin:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{formatDateTime(hoveredTask.end)}</span>
              
              <span style={{ color: 'var(--text-muted)' }}>Durée:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{hoveredTask.duration_minutes} min</span>
              
              {hoveredTask.transfer_time_minutes > 0 && (
                <>
                  <span style={{ color: 'var(--text-muted)' }}>Transfert:</span>
                  <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>+{hoveredTask.transfer_time_minutes} min</span>
                </>
              )}
              
              {hoveredTask.due_date && (
                <>
                  <span style={{ color: 'var(--text-muted)' }}>Besoin:</span>
                  <span className="font-mono" style={{ color: hoveredTask.is_late ? 'var(--status-error)' : 'var(--text-primary)' }}>
                    {formatDateTime(hoveredTask.due_date)}
                  </span>
                </>
              )}
            </div>
            
            {/* Section Matières premières */}
            {hoveredTask.materials && hoveredTask.materials.length > 0 && (
              <div className="pt-2" style={{ borderTop: '1px solid var(--border-default)' }}>
                <div className="flex items-center gap-2 mb-2">
                  <Package size={14} style={{ color: 'var(--text-muted)' }} />
                  <span className="text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>
                    Matières premières ({hoveredTask.materials.length})
                  </span>
                </div>
                <div className="space-y-2">
                  {hoveredTask.materials.map((mat, idx) => (
                    <div key={idx} className="p-1.5 rounded" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {mat.article_id}
                        </span>
                        <span 
                          className="font-mono px-1.5 py-0.5 rounded"
                          style={{ 
                            backgroundColor: mat.available ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                            color: mat.available ? 'var(--status-success)' : 'var(--status-error)'
                          }}
                        >
                          {mat.available ? '✓ Dispo' : '✗ Manque'}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                        <div>
                          <span>Qté requise: </span>
                          <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{mat.needed}</span>
                        </div>
                        <div>
                          <span>En stock: </span>
                          <span className="font-mono" style={{ color: mat.in_stock >= mat.needed ? 'var(--status-success)' : 'var(--status-error)' }}>{mat.in_stock}</span>
                        </div>
                      </div>
                      {mat.magasin && (
                        <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                          Magasin: <span style={{ color: 'var(--text-secondary)' }}>{mat.magasin}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Légende */}
      <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Légende</h3>
        <div className="flex flex-wrap gap-4 text-sm">
          {filteredMachines.slice(0, 8).map(m => (
            <div key={m.machine_id} className="flex items-center gap-2">
              <div className="w-4 h-4 rounded" style={{ backgroundColor: m.color }} />
              <span style={{ color: 'var(--text-secondary)' }}>{m.machine_id}</span>
            </div>
          ))}
          {filteredMachines.length > 8 && (
            <span style={{ color: 'var(--text-muted)' }}>+{filteredMachines.length - 8} autres</span>
          )}
          <div className="flex items-center gap-4 ml-4 pl-4" style={{ borderLeft: '1px solid var(--border-default)' }}>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded" style={{ backgroundColor: '#eab308', border: '2px solid #ca8a04' }} />
              <span style={{ color: 'var(--text-secondary)' }}>Urgent</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-red-500 border-2 border-red-700" />
              <span style={{ color: 'var(--text-secondary)' }}>En retard</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded bg-amber-500 border-2 border-amber-700" />
              <span style={{ color: 'var(--text-secondary)' }}>Matière manquante</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded opacity-30" style={{ backgroundColor: 'var(--text-muted)' }} />
              <span style={{ color: 'var(--text-secondary)' }}>Hors horaires</span>
            </div>
          </div>
        </div>
      </div>

      {/* Conflicts Warning */}
      {scenario?.schedule_data?.conflicts?.length > 0 && (
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)' }}>
          <div className="flex items-start gap-3">
            <AlertCircle size={20} style={{ color: 'var(--status-warning)' }} />
            <div>
              <h4 className="font-semibold" style={{ color: 'var(--status-warning)' }}>
                {scenario.schedule_data.conflicts.length} Conflit(s) détecté(s)
              </h4>
              <ul className="mt-2 space-y-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
                {scenario.schedule_data.conflicts.slice(0, 5).map((c, idx) => (
                  <li key={idx} className="font-mono">
                    {c.operation_id ? `Op ${c.operation_id}: ${c.reason}` : JSON.stringify(c)}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* NOUVELLE SECTION: Opérations non planifiables (collapsible, agrégée) */}
      {scenario?.schedule_data?.unscheduled_operations?.length > 0 && (
        <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--status-error)' }}>
          {/* Résumé avec bouton pour déplier */}
          <button
            onClick={() => setErrorsExpanded(!errorsExpanded)}
            className="w-full p-4 flex items-center justify-between hover:bg-opacity-80 transition-colors"
            style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)' }}
            data-testid="errors-toggle"
          >
            <div className="flex items-center gap-3">
              <AlertCircle size={20} style={{ color: 'var(--status-error)' }} />
              <div className="text-left">
                <h4 className="font-semibold" style={{ color: 'var(--status-error)' }}>
                  {scenario.schedule_data.unscheduled_operations.length} opération(s) non planifiable(s)
                </h4>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  {(() => {
                    const ops = scenario.schedule_data.unscheduled_operations;
                    const uniqueOrders = [...new Set(ops.map(op => op.order_id))].length;
                    const reasons = {};
                    ops.forEach(op => {
                      const reason = op.reason?.includes('machine') ? 'Machine manquante' :
                                     op.reason?.includes('matière') ? 'Matière insuffisante' :
                                     op.reason?.includes('calendrier') ? 'Contrainte calendrier' :
                                     'Autre';
                      reasons[reason] = (reasons[reason] || 0) + 1;
                    });
                    const mainReason = Object.entries(reasons).sort((a, b) => b[1] - a[1])[0];
                    return `${uniqueOrders} OF(s) concerné(s) • Cause principale: ${mainReason?.[0] || 'Inconnue'} (${mainReason?.[1] || 0})`;
                  })()}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {errorsExpanded ? 'Masquer' : 'Voir le détail'}
              </span>
              <svg 
                className={`w-5 h-5 transition-transform ${errorsExpanded ? 'rotate-180' : ''}`}
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
                style={{ color: 'var(--text-muted)' }}
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>

          {/* Détail collapsible agrégé par OF */}
          {errorsExpanded && (
            <div className="p-4 space-y-3" style={{ borderTop: '1px solid var(--border-default)' }}>
              {(() => {
                // Agréger par OF
                const byOrder = {};
                scenario.schedule_data.unscheduled_operations.forEach(op => {
                  if (!byOrder[op.order_id]) {
                    byOrder[op.order_id] = { 
                      operations: [], 
                      reasons: new Set(),
                      article_id: op.article_id  // Récupérer l'article_id
                    };
                  }
                  byOrder[op.order_id].operations.push(op);
                  if (op.reason) byOrder[op.order_id].reasons.add(op.reason);
                  // Mettre à jour l'article_id si disponible
                  if (op.article_id && !byOrder[op.order_id].article_id) {
                    byOrder[op.order_id].article_id = op.article_id;
                  }
                });

                return Object.entries(byOrder).map(([orderId, data]) => (
                  <div 
                    key={orderId}
                    className="p-3 rounded-lg"
                    style={{ backgroundColor: 'var(--bg-sunken)' }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>
                          OF {orderId}
                        </span>
                        {data.article_id && (
                          <span className="text-xs px-2 py-0.5 rounded font-mono" style={{ backgroundColor: 'var(--accent-primary-bg)', color: 'var(--accent-primary)' }}>
                            {data.article_id}
                          </span>
                        )}
                      </div>
                      <span className="text-sm px-2 py-0.5 rounded" style={{ backgroundColor: 'var(--status-error)', color: 'white' }}>
                        {data.operations.length} opération(s)
                      </span>
                    </div>
                    <div className="text-sm space-y-1" style={{ color: 'var(--text-secondary)' }}>
                      {[...data.reasons].map((reason, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <span>•</span>
                          <span>{reason}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {data.operations.map((op, idx) => (
                        <span 
                          key={idx}
                          className="text-xs px-1.5 py-0.5 rounded font-mono"
                          style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-muted)' }}
                        >
                          {op.operation_id?.split('_')[1] || op.operation_id}
                        </span>
                      ))}
                    </div>
                  </div>
                ));
              })()}
            </div>
          )}
        </div>
      )}

      {/* SECTION DIAGNOSTIC détaillée */}
      {scenario?.schedule_data?.scheduling_stats && (
        <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <button
            onClick={() => setDiagnosticsExpanded(!diagnosticsExpanded)}
            className="w-full p-4 flex items-center justify-between hover:bg-opacity-80 transition-colors"
            data-testid="diagnostics-toggle"
          >
            <div className="flex items-center gap-3">
              <FileText size={20} style={{ color: 'var(--accent-primary)' }} />
              <div className="text-left">
                <h4 className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Diagnostic du calcul
                </h4>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  {scenario.schedule_data.scheduling_stats.operations_scheduled} planifiées sur {scenario.schedule_data.scheduling_stats.total_operations_input} • 
                  Taux remplissage: {scenario.schedule_data.scheduling_stats.global_utilization_percent}% •
                  Temps: {scenario.schedule_data.scheduling_stats.actual_solver_time}s / {scenario.schedule_data.scheduling_stats.max_solver_time_configured}s max
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {diagnosticsExpanded ? 'Masquer' : 'Voir le détail'}
              </span>
              <svg 
                className={`w-5 h-5 transition-transform ${diagnosticsExpanded ? 'rotate-180' : ''}`}
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
                style={{ color: 'var(--text-muted)' }}
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>

          {diagnosticsExpanded && (
            <div className="p-4 space-y-4" style={{ borderTop: '1px solid var(--border-default)' }}>
              {/* Stats principales */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                  <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Opérations candidates</p>
                  <p className="text-xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
                    {scenario.schedule_data.scheduling_stats.total_operations_input}
                  </p>
                </div>
                <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                  <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Planifiées</p>
                  <p className="text-xl font-bold font-mono" style={{ color: 'var(--status-success)' }}>
                    {scenario.schedule_data.scheduling_stats.operations_scheduled}
                  </p>
                </div>
                <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                  <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Bloquées</p>
                  <p className="text-xl font-bold font-mono" style={{ color: 'var(--status-error)' }}>
                    {scenario.schedule_data.scheduling_stats.operations_blocked}
                  </p>
                </div>
                <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                  <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Retardées (matière)</p>
                  <p className="text-xl font-bold font-mono" style={{ color: 'var(--status-warning)' }}>
                    {scenario.schedule_data.scheduling_stats.operations_material_delayed}
                  </p>
                </div>
              </div>

              {/* Statistiques d'horizon et de fractionnement */}
              {scenario.schedule_data.scheduling_stats.horizon_stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-3 rounded-lg" style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)' }}>
                    <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Horizon planification</p>
                    <p className="text-lg font-bold font-mono" style={{ color: '#3B82F6' }}>
                      {scenario.schedule_data.scheduling_stats.horizon_stats.horizon_days === 0 
                        ? 'Tous' 
                        : `J+${scenario.schedule_data.scheduling_stats.horizon_stats.horizon_days}j`}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg" style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)' }}>
                    <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Dans l'horizon</p>
                    <p className="text-lg font-bold font-mono" style={{ color: '#3B82F6' }}>
                      {scenario.schedule_data.scheduling_stats.horizon_stats.orders_in_horizon || 0}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)' }}>
                    <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>En retard</p>
                    <p className="text-lg font-bold font-mono" style={{ color: 'var(--status-error)' }}>
                      {scenario.schedule_data.scheduling_stats.horizon_stats.orders_late || 0}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg" style={{ backgroundColor: 'rgba(139, 92, 246, 0.1)' }}>
                    <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Par dépendance</p>
                    <p className="text-lg font-bold font-mono" style={{ color: '#8B5CF6' }}>
                      {scenario.schedule_data.scheduling_stats.horizon_stats.orders_dependency || 0}
                    </p>
                  </div>
                </div>
              )}

              {/* Statistiques de fractionnement */}
              {scenario.schedule_data.scheduling_stats.split_stats && 
               scenario.schedule_data.scheduling_stats.split_stats.operations_split > 0 && (
                <div className="p-3 rounded-lg" style={{ backgroundColor: 'rgba(139, 92, 246, 0.1)' }}>
                  <p className="text-sm font-semibold mb-2" style={{ color: '#8B5CF6' }}>Fractionnement des opérations longues</p>
                  <div className="flex gap-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                    <span>
                      <strong style={{ color: 'var(--text-primary)' }}>
                        {scenario.schedule_data.scheduling_stats.split_stats.operations_split}
                      </strong> opérations fractionnées
                    </span>
                    <span>→</span>
                    <span>
                      <strong style={{ color: 'var(--text-primary)' }}>
                        {scenario.schedule_data.scheduling_stats.split_stats.sub_operations_created}
                      </strong> sous-opérations créées
                    </span>
                  </div>
                </div>
              )}

              {/* Temps et performance */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                  <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Durée max configurée</p>
                  <p className="text-lg font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
                    {scenario.schedule_data.scheduling_stats.max_solver_time_configured}s
                  </p>
                </div>
                <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                  <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Durée réelle</p>
                  <p className="text-lg font-bold font-mono" style={{ color: 'var(--accent-primary)' }}>
                    {scenario.schedule_data.scheduling_stats.actual_solver_time}s
                  </p>
                </div>
                <div className="p-3 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                  <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Taux remplissage global</p>
                  <p className="text-lg font-bold font-mono" style={{ color: scenario.schedule_data.scheduling_stats.global_utilization_percent > 70 ? 'var(--status-success)' : 'var(--status-warning)' }}>
                    {scenario.schedule_data.scheduling_stats.global_utilization_percent}%
                  </p>
                </div>
              </div>

              {/* Raisons de blocage */}
              {scenario.schedule_data.scheduling_stats.blocked_reasons_summary && 
               Object.keys(scenario.schedule_data.scheduling_stats.blocked_reasons_summary).length > 0 && (
                <div>
                  <h5 className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Causes de blocage</h5>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(scenario.schedule_data.scheduling_stats.blocked_reasons_summary).map(([reason, count]) => (
                      <div 
                        key={reason}
                        className="px-3 py-1.5 rounded-full text-sm"
                        style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--status-error)' }}
                      >
                        {reason === 'machine_missing' ? 'Machine manquante' :
                         reason === 'material_shortage' ? 'Matière insuffisante' :
                         reason === 'calendar_constraint' ? 'Contrainte calendrier' :
                         reason === 'business_rule' ? 'Règle métier' : reason}: <strong>{count}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Options actives */}
              {scenario.schedule_data.active_options && (
                <div>
                  <h5 className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Options actives</h5>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(scenario.schedule_data.active_options).map(([option, value]) => (
                      <div 
                        key={option}
                        className="px-2 py-1 rounded text-xs font-mono"
                        style={{ 
                          backgroundColor: value ? 'rgba(34, 197, 94, 0.1)' : 'var(--bg-sunken)',
                          color: value ? 'var(--status-success)' : 'var(--text-muted)'
                        }}
                      >
                        {option}: {value ? 'OUI' : 'NON'}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Utilisation machine */}
              {scenario.schedule_data.scheduling_stats.machine_utilization && 
               Object.keys(scenario.schedule_data.scheduling_stats.machine_utilization).length > 0 && (
                <div>
                  <h5 className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Utilisation par machine</h5>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {Object.entries(scenario.schedule_data.scheduling_stats.machine_utilization)
                      .sort((a, b) => b[1].utilization_percent - a[1].utilization_percent)
                      .slice(0, 8)
                      .map(([machineId, stats]) => (
                        <div 
                          key={machineId}
                          className="p-2 rounded text-sm"
                          style={{ backgroundColor: 'var(--bg-sunken)' }}
                        >
                          <div className="font-mono font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                            {machineId}
                          </div>
                          <div className="flex justify-between text-xs" style={{ color: 'var(--text-muted)' }}>
                            <span>{stats.operations_count} ops</span>
                            <span style={{ color: stats.utilization_percent > 70 ? 'var(--status-success)' : 'var(--status-warning)' }}>
                              {stats.utilization_percent}%
                            </span>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
