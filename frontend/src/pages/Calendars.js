import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Calendars() {
  const [calendars, setCalendars] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    working_days: [1, 2, 3, 4, 5],
    start_hour: 8,
    end_hour: 17,
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
    try {
      await axios.post(`${API}/calendars`, formData);
      toast.success('Calendrier créé');
      setFormData({ name: '', working_days: [1, 2, 3, 4, 5], start_hour: 8, end_hour: 17 });
      setShowForm(false);
      fetchCalendars();
    } catch (error) {
      toast.error('Erreur lors de la création');
    }
  };

  const daysOfWeek = [
    { value: 1, label: 'Lundi' },
    { value: 2, label: 'Mardi' },
    { value: 3, label: 'Mercredi' },
    { value: 4, label: 'Jeudi' },
    { value: 5, label: 'Vendredi' },
    { value: 6, label: 'Samedi' },
    { value: 7, label: 'Dimanche' },
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-semibold text-slate-800">Calendriers</h3>
        <button
          data-testid="create-calendar-btn"
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
        >
          <Plus size={16} />
          Nouveau Calendrier
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Nom du calendrier
              </label>
              <input
                data-testid="calendar-name-input"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Jours ouvrés
              </label>
              <div className="flex flex-wrap gap-2">
                {daysOfWeek.map((day) => (
                  <button
                    key={day.value}
                    type="button"
                    data-testid={`day-${day.value}-btn`}
                    onClick={() => toggleDay(day.value)}
                    className={`px-3 py-1 text-sm rounded-sm border transition-colors ${
                      formData.working_days.includes(day.value)
                        ? 'bg-slate-900 text-white border-slate-900'
                        : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    {day.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Heure début
                </label>
                <input
                  data-testid="start-hour-input"
                  type="number"
                  min="0"
                  max="23"
                  value={formData.start_hour}
                  onChange={(e) => setFormData({ ...formData, start_hour: parseInt(e.target.value) })}
                  className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Heure fin
                </label>
                <input
                  data-testid="end-hour-input"
                  type="number"
                  min="0"
                  max="23"
                  value={formData.end_hour}
                  onChange={(e) => setFormData({ ...formData, end_hour: parseInt(e.target.value) })}
                  className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                  required
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                data-testid="submit-calendar-btn"
                className="bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
              >
                Créer
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-sm px-4 py-2 text-sm font-medium transition-colors"
              >
                Annuler
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Jours ouvrés</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Horaires</th>
            </tr>
          </thead>
          <tbody>
            {calendars.map((calendar) => (
              <tr key={calendar.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors" data-testid="calendar-row">
                <td className="px-4 py-2 text-sm text-slate-700 font-mono">{calendar.name}</td>
                <td className="px-4 py-2 text-sm text-slate-700 font-mono">
                  {calendar.working_days.join(', ')}
                </td>
                <td className="px-4 py-2 text-sm text-slate-700 font-mono">
                  {calendar.start_hour}h - {calendar.end_hour}h
                </td>
              </tr>
            ))}
            {calendars.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-sm text-slate-500">
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