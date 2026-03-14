import { useEffect, useState, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Download, ZoomIn, ZoomOut, AlertCircle, Clock, Package, Filter, Check, X, Layers } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function GanttInteractive() {
  const { scenarioId } = useParams();
  const navigate = useNavigate();
  const [ganttData, setGanttData] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [loading, setLoading] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [hoveredTask, setHoveredTask] = useState(null);
  const [selectedCentres, setSelectedCentres] = useState([]);
  const containerRef = useRef(null);

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

  // Formater la date/heure absolue à partir du scheduling_start
  const formatAbsoluteTime = (minutes, schedulingStart) => {
    if (!schedulingStart) return formatTime(minutes);
    try {
      const start = new Date(schedulingStart);
      const targetDate = new Date(start.getTime() + minutes * 60000);
      return targetDate.toLocaleString('fr-FR', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return formatTime(minutes);
    }
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

  // Filtrer les machines par centres de charge sélectionnés
  const filteredMachines = useMemo(() => {
    if (!ganttData?.machines) return [];
    if (selectedCentres.length === 0) return ganttData.machines;
    return ganttData.machines.filter(m => selectedCentres.includes(m.centre_de_charge_id));
  }, [ganttData?.machines, selectedCentres]);

  // Calculer les zones de fermeture (simplifié: nuits)
  const closurePeriods = useMemo(() => {
    if (!ganttData) return [];
    const { scheduling_start, calendars, time_range } = ganttData;
    if (!scheduling_start || !calendars || calendars.length === 0) return [];
    
    const periods = [];
    const cal = calendars[0];
    if (!cal) return [];
    
    const startTime = cal.start_time || '08:00';
    const endTime = cal.end_time || '17:00';
    const [startH, startM] = startTime.split(':').map(Number);
    const [endH, endM] = endTime.split(':').map(Number);
    const workStartMinutes = startH * 60 + startM;
    const workEndMinutes = endH * 60 + endM;
    
    const totalDays = Math.ceil((time_range?.total_minutes || 480) / (24 * 60)) + 1;
    
    for (let d = 0; d < totalDays; d++) {
      const dayStart = d * 24 * 60;
      
      if (workStartMinutes > 0) {
        const closureStart = dayStart;
        const closureEnd = dayStart + workStartMinutes;
        if (closureEnd > (time_range?.min_minutes || 0) && closureStart < (time_range?.max_minutes || 0)) {
          periods.push({
            start: Math.max(closureStart - (time_range?.min_minutes || 0), 0),
            end: Math.max(closureEnd - (time_range?.min_minutes || 0), 0),
            reason: 'Hors horaires'
          });
        }
      }
      
      if (workEndMinutes < 24 * 60) {
        const closureStart = dayStart + workEndMinutes;
        const closureEnd = dayStart + 24 * 60;
        if (closureEnd > (time_range?.min_minutes || 0) && closureStart < (time_range?.max_minutes || 0)) {
          periods.push({
            start: Math.max(closureStart - (time_range?.min_minutes || 0), 0),
            end: Math.min(closureEnd - (time_range?.min_minutes || 0), time_range?.total_minutes || 0),
            reason: 'Hors horaires'
          });
        }
      }
    }
    
    return periods;
  }, [ganttData]);

  // Calcul des positions et dimensions
  const pixelsPerMinute = 2 * zoom;
  const rowHeight = 48;
  const headerHeight = 60;
  const sidebarWidth = 180;

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

  const { time_range, total_tasks, scheduling_start, centres_de_charge, calendars } = ganttData;
  const totalWidth = (time_range?.total_minutes || 480) * pixelsPerMinute;

  // Générer les marqueurs de temps avec dates réelles
  const timeMarkers = [];
  const markerInterval = zoom >= 1 ? 60 : 120;
  for (let m = 0; m <= (time_range?.total_minutes || 480); m += markerInterval) {
    timeMarkers.push({
      minutes: m,
      label: formatAbsoluteTime(m + (time_range?.min_minutes || 0), scheduling_start)
    });
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
          >
            <ZoomOut size={16} />
          </button>
          <span className="text-sm font-mono px-2" style={{ color: 'var(--text-secondary)' }}>
            {(zoom * 100).toFixed(0)}%
          </span>
          <button
            onClick={() => setZoom(Math.min(3, zoom + 0.25))}
            className="p-2 rounded-lg transition-colors"
            style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
            title="Zoom +"
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
        </div>
      </div>

      {/* Filtre par Centre de Charge */}
      {centres_de_charge && centres_de_charge.length > 0 && (
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <Filter size={16} style={{ color: 'var(--text-muted)' }} />
              <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                Filtrer par Centre de Charge :
              </span>
            </div>
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
              {selectedCentres.length > 0 && (
                <button
                  onClick={() => setSelectedCentres([])}
                  className="inline-flex items-center gap-1 px-2 py-1.5 rounded-lg text-sm transition-colors"
                  style={{ color: 'var(--text-muted)' }}
                >
                  <X size={14} />
                  Réinitialiser
                </button>
              )}
            </div>
            {selectedCentres.length > 0 && (
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                ({filteredMachines.length} / {ganttData.machines.length} machines)
              </span>
            )}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center gap-2 mb-1">
            <Package size={16} style={{ color: 'var(--brand-primary)' }} />
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Opérations</span>
          </div>
          <p className="text-2xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>{total_tasks}</p>
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
            <span className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Statut</span>
          </div>
          <p className="text-lg font-bold" style={{ color: ganttData.status === 'OPTIMAL' ? 'var(--status-success)' : 'var(--status-info)' }}>
            {ganttData.status}
          </p>
        </div>
      </div>

      {/* Gantt Chart */}
      <div 
        className="rounded-lg overflow-hidden"
        style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}
        data-testid="gantt-chart"
      >
        <div className="overflow-x-auto" ref={containerRef}>
          <div style={{ minWidth: sidebarWidth + totalWidth + 40 }}>
            {/* Timeline Header */}
            <div className="flex" style={{ height: headerHeight, borderBottom: '1px solid var(--border-default)' }}>
              <div 
                className="flex-shrink-0 flex items-center justify-center font-semibold text-sm"
                style={{ width: sidebarWidth, backgroundColor: 'var(--bg-sunken)', color: 'var(--text-muted)', borderRight: '1px solid var(--border-default)' }}
              >
                Machine
              </div>
              <div className="relative flex-1" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                {timeMarkers.map((marker, idx) => (
                  <div
                    key={idx}
                    className="absolute top-0 bottom-0 flex flex-col justify-center"
                    style={{ 
                      left: marker.minutes * pixelsPerMinute,
                      borderLeft: '1px solid var(--border-default)'
                    }}
                  >
                    <span className="ml-1 text-xs font-mono whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
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
                  {/* Closure periods (gray zones) */}
                  {closurePeriods.map((period, pIdx) => (
                    <div
                      key={pIdx}
                      className="absolute top-0 bottom-0 opacity-30"
                      style={{
                        left: period.start * pixelsPerMinute,
                        width: (period.end - period.start) * pixelsPerMinute,
                        backgroundColor: 'var(--text-muted)'
                      }}
                      title={period.reason}
                    />
                  ))}
                  
                  {/* Grid lines */}
                  {timeMarkers.map((marker, mIdx) => (
                    <div
                      key={mIdx}
                      className="absolute top-0 bottom-0"
                      style={{ 
                        left: marker.minutes * pixelsPerMinute,
                        borderLeft: '1px dashed var(--border-default)',
                        opacity: 0.5
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
                          backgroundColor: task.is_late ? '#EF4444' : hasMaterialIssue ? '#F59E0B' : task.color,
                          border: task.is_late ? '2px solid #B91C1C' : hasMaterialIssue ? '2px solid #D97706' : 'none'
                        }}
                        onMouseEnter={() => setHoveredTask(task)}
                        onMouseLeave={() => setHoveredTask(null)}
                        data-testid={`task-${task.id}`}
                      >
                        <div className="px-1 py-0.5 text-white text-xs font-medium truncate h-full flex items-center">
                          {width > 60 ? task.operation_id : ''}
                        </div>
                        {task.is_late && (
                          <AlertCircle size={12} className="absolute top-0.5 right-0.5 text-white" />
                        )}
                        {hasMaterialIssue && !task.is_late && (
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

      {/* Tooltip enrichi */}
      {hoveredTask && (
        <div 
          className="fixed z-50 p-4 rounded-lg shadow-lg"
          style={{ 
            backgroundColor: 'var(--bg-elevated)', 
            border: '1px solid var(--border-default)',
            top: '50%',
            right: 20,
            transform: 'translateY(-50%)',
            maxWidth: 360
          }}
        >
          <div className="space-y-3 text-sm">
            {/* Header */}
            <div className="flex items-center gap-2 pb-2" style={{ borderBottom: '1px solid var(--border-default)' }}>
              <div className="w-3 h-3 rounded" style={{ backgroundColor: hoveredTask.color }} />
              <span className="font-bold" style={{ color: 'var(--text-primary)' }}>
                {hoveredTask.operation_id}
              </span>
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
              
              <span style={{ color: 'var(--text-muted)' }}>Article:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{hoveredTask.article_id || '-'}</span>
              
              <span style={{ color: 'var(--text-muted)' }}>Centre:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{hoveredTask.centre_de_charge_nom || '-'}</span>
              
              <span style={{ color: 'var(--text-muted)' }}>Début:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{formatDateTime(hoveredTask.start)}</span>
              
              <span style={{ color: 'var(--text-muted)' }}>Fin:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{formatDateTime(hoveredTask.end)}</span>
              
              <span style={{ color: 'var(--text-muted)' }}>Durée:</span>
              <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{hoveredTask.duration_minutes} min</span>
              
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
                    Matières premières
                  </span>
                </div>
                <div className="space-y-1.5">
                  {hoveredTask.materials.map((mat, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                        {mat.article_id}
                      </span>
                      <span 
                        className="font-mono px-1.5 py-0.5 rounded"
                        style={{ 
                          backgroundColor: mat.available ? 'var(--status-success-bg)' : 'var(--status-error-bg)',
                          color: mat.available ? 'var(--status-success)' : 'var(--status-error)'
                        }}
                      >
                        {mat.in_stock} / {mat.needed}
                        {mat.available ? ' ✓' : ' ✗'}
                      </span>
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
    </div>
  );
}
