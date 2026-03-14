import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2, Clock } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Calendars() {
  const [calendars, setCalendars] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    working_days: [1, 2, 3, 4, 5],
    start_time: '08:00',
    end_time: '17:00',
  });

  useEffect(() => {
    fetchCalendars();
  }, []);

  const fetchCalendars = async () => {
    try {
      const response = await axios.get(`${API}/calendars`);
      setCalendars(response.data);
    } catch (error) {
      console.error('Error fetching calendars:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate time format
    if (formData.start_time >= formData.end_time) {
      toast.error("L'heure de début doit être avant l'heure de fin");
      return;
    }
    
    try {
      // Convert HH:MM to hours for backward compatibility
      const startParts = formData.start_time.split(':');
      const endParts = formData.end_time.split(':');
      
      const payload = {
        ...formData,
        start_hour: parseInt(startParts[0]),
        end_hour: parseInt(endParts[0]),
      };
      
      await axios.post(`${API}/calendars`, payload);
      toast.success('Calendrier créé');
      setFormData({ name: '', working_days: [1, 2, 3, 4, 5], start_time: '08:00', end_time: '17:00' });
      setShowForm(false);
      fetchCalendars();
    } catch (error) {
      toast.error('Erreur lors de la création');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Confirmer la suppression ?')) return;
    try {
      await axios.delete(`${API}/calendars/${id}`);
      toast.success('Calendrier supprimé');
      fetchCalendars();
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const daysOfWeek = [
    { value: 1, label: 'Lun' },
    { value: 2, label: 'Mar' },
    { value: 3, label: 'Mer' },
    { value: 4, label: 'Jeu' },
    { value: 5, label: 'Ven' },
    { value: 6, label: 'Sam' },
    { value: 7, label: 'Dim' },
  ];

  const toggleDay = (day) => {
    if (formData.working_days.includes(day)) {
      setFormData({
        ...formData,
        working_days: formData.working_days.filter((d) => d !== day),
      });
    } else {
      setFormData({
        ...formData,
        working_days: [...formData.working_days, day].sort(),
      });
    }
  };

  // Format display time from calendar data
  const formatTime = (calendar) => {
    // Use new format if available, fallback to old format
    const start = calendar.start_time || `${String(calendar.start_hour || 8).padStart(2, '0')}:00`;
    const end = calendar.end_time || `${String(calendar.end_hour || 17).padStart(2, '0')}:00`;
    return `${start} - ${end}`;
  };

  // Calculate working hours
  const calculateHours = (calendar) => {
    const start = calendar.start_time || `${String(calendar.start_hour || 8).padStart(2, '0')}:00`;
    const end = calendar.end_time || `${String(calendar.end_hour || 17).padStart(2, '0')}:00`;
    
    const [startH, startM] = start.split(':').map(Number);
    const [endH, endM] = end.split(':').map(Number);
    
    const totalMinutes = (endH * 60 + endM) - (startH * 60 + startM);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    
    return minutes > 0 ? `${hours}h${minutes}` : `${hours}h`;
  };

  const dayLabels = {
    1: 'Lun', 2: 'Mar', 3: 'Mer', 4: 'Jeu', 5: 'Ven', 6: 'Sam', 7: 'Dim'
  };

  return (
    <div className="space-y-6" data-testid="calendars-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Calendriers</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Définissez les horaires de travail par quarts d'heure
          </p>
        </div>
        <button
          data-testid="create-calendar-btn"
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
        >
          <Plus size={16} />
          Nouveau Calendrier
        </button>
      </div>

      {showForm && (
        <div className="rounded-lg p-5" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                Nom du calendrier
              </label>
              <input
                data-testid="calendar-name-input"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full h-10 rounded-lg border px-3 text-sm transition-colors focus:outline-none focus:ring-2"
                style={{ 
                  backgroundColor: 'var(--bg-sunken)', 
                  borderColor: 'var(--border-default)',
                  color: 'var(--text-primary)'
                }}
                placeholder="Ex: Standard 2x8, Équipe Matin..."
                required
              />
            </div>
            
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                Jours ouvrés
              </label>
              <div className="flex flex-wrap gap-2">
                {daysOfWeek.map((day) => (
                  <button
                    key={day.value}
                    type="button"
                    data-testid={`day-${day.value}-btn`}
                    onClick={() => toggleDay(day.value)}
                    className={`px-4 py-2 text-sm rounded-lg border font-medium transition-all ${
                      formData.working_days.includes(day.value)
                        ? 'border-transparent'
                        : ''
                    }`}
                    style={{
                      backgroundColor: formData.working_days.includes(day.value) 
                        ? 'var(--brand-primary)' 
                        : 'var(--bg-sunken)',
                      color: formData.working_days.includes(day.value) 
                        ? 'white' 
                        : 'var(--text-secondary)',
                      borderColor: formData.working_days.includes(day.value) 
                        ? 'transparent' 
                        : 'var(--border-default)'
                    }}
                  >
                    {day.label}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                  <Clock size={12} className="inline mr-1" />
                  Heure de début
                </label>
                <input
                  data-testid="start-time-input"
                  type="time"
                  value={formData.start_time}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                  className="w-full h-10 rounded-lg border px-3 text-sm font-mono transition-colors focus:outline-none focus:ring-2"
                  style={{ 
                    backgroundColor: 'var(--bg-sunken)', 
                    borderColor: 'var(--border-default)',
                    color: 'var(--text-primary)'
                  }}
                  step="900"
                  required
                />
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Ex: 07:45, 08:00, 06:30
                </p>
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                  <Clock size={12} className="inline mr-1" />
                  Heure de fin
                </label>
                <input
                  data-testid="end-time-input"
                  type="time"
                  value={formData.end_time}
                  onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                  className="w-full h-10 rounded-lg border px-3 text-sm font-mono transition-colors focus:outline-none focus:ring-2"
                  style={{ 
                    backgroundColor: 'var(--bg-sunken)', 
                    borderColor: 'var(--border-default)',
                    color: 'var(--text-primary)'
                  }}
                  step="900"
                  required
                />
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Ex: 16:45, 17:00, 22:30
                </p>
              </div>
            </div>
            
            <div className="flex gap-2 pt-2">
              <button
                type="submit"
                data-testid="submit-calendar-btn"
                className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
              >
                Créer
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-primary)', border: '1px solid var(--border-default)' }}
              >
                Annuler
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <table className="w-full">
          <thead style={{ backgroundColor: 'var(--bg-sunken)' }}>
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Jours ouvrés</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Horaires</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Durée/jour</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {calendars.map((calendar) => (
              <tr key={calendar.id} className="transition-colors hover:bg-opacity-50" style={{ borderBottom: '1px solid var(--border-default)' }} data-testid="calendar-row">
                <td className="px-4 py-3">
                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{calendar.name}</span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    {calendar.working_days.map(d => (
                      <span key={d} className="px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: 'var(--status-info-bg)', color: 'var(--status-info)' }}>
                        {dayLabels[d]}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>
                    {formatTime(calendar)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 rounded text-xs font-medium font-mono" style={{ backgroundColor: 'var(--status-success-bg)', color: 'var(--status-success)' }}>
                    {calculateHours(calendar)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    data-testid="delete-calendar-btn"
                    onClick={() => handleDelete(calendar.id)}
                    className="p-1.5 rounded-lg transition-colors hover:bg-red-100 dark:hover:bg-red-900/30"
                  >
                    <Trash2 size={16} className="text-red-600" />
                  </button>
                </td>
              </tr>
            ))}
            {calendars.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                  Aucun calendrier. Cliquez sur "Nouveau Calendrier" pour en créer un.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
