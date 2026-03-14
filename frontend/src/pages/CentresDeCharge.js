import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2, Calendar, Pencil, X } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function CentresDeCharge() {
  const [centres, setCentres] = useState([]);
  const [calendars, setCalendars] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingCentre, setEditingCentre] = useState(null);
  const [formData, setFormData] = useState({ id: '', nom: '', description: '', calendar_id: '' });

  useEffect(() => {
    fetchCentres();
    fetchCalendars();
  }, []);

  const fetchCentres = async () => {
    try {
      const response = await axios.get(`${API}/centres-de-charge`);
      setCentres(response.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const fetchCalendars = async () => {
    try {
      const response = await axios.get(`${API}/calendars`);
      setCalendars(response.data);
    } catch (error) {
      console.error('Error fetching calendars:', error);
    }
  };

  const resetForm = () => {
    setFormData({ id: '', nom: '', description: '', calendar_id: '' });
    setEditingCentre(null);
  };

  const handleEdit = (centre) => {
    setFormData({
      id: centre.id,
      nom: centre.nom || centre.name || '',
      description: centre.description || '',
      calendar_id: centre.calendar_id || '',
    });
    setEditingCentre(centre);
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.nom.trim()) {
      toast.error('Le nom est obligatoire');
      return;
    }
    
    try {
      if (editingCentre) {
        // Mode édition
        await axios.put(`${API}/centres-de-charge/${editingCentre.id}`, {
          nom: formData.nom,
          description: formData.description,
          calendar_id: formData.calendar_id || null,
        });
        toast.success(`Centre de charge "${editingCentre.id}" modifié`);
      } else {
        // Mode création
        if (!formData.id.trim()) {
          toast.error('Le code (ID) est obligatoire pour un nouveau centre');
          return;
        }
        await axios.post(`${API}/centres-de-charge`, formData);
        toast.success(`Centre de charge "${formData.id}" créé`);
      }
      resetForm();
      setShowForm(false);
      fetchCentres();
    } catch (error) {
      toast.error(error.response?.data?.detail || (editingCentre ? 'Erreur lors de la modification' : 'Erreur lors de la création'));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(`Supprimer le centre de charge "${id}" ?`)) return;
    try {
      await axios.delete(`${API}/centres-de-charge/${id}`);
      setCentres(centres.filter(c => c.id !== id));
      toast.success('Centre de charge supprimé');
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const handleCancel = () => {
    resetForm();
    setShowForm(false);
  };

  const handleCalendarChange = async (centreId, calendarId) => {
    try {
      await axios.put(`${API}/centres-de-charge/${centreId}`, { calendar_id: calendarId || null });
      setCentres(centres.map(c => c.id === centreId ? { ...c, calendar_id: calendarId || null } : c));
      toast.success('Calendrier mis à jour');
    } catch (error) {
      toast.error('Erreur lors de la mise à jour');
    }
  };

  const getCalendarName = (calendarId) => {
    const calendar = calendars.find(c => c.id === calendarId);
    return calendar ? calendar.name : '-';
  };

  return (
    <div className="space-y-6" data-testid="centres-de-charge-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Centres de Charge</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Définissez les centres de charge avec des codes métier et assignez-leur un calendrier
          </p>
        </div>
        <button
          data-testid="new-centre-btn"
          onClick={() => { resetForm(); setShowForm(true); }}
          className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
        >
          <Plus size={16} />
          Nouveau Centre
        </button>
      </div>

      {showForm && (
        <div className="rounded-lg p-5" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }} data-testid="centre-form">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              {editingCentre ? `Modifier: ${editingCentre.id}` : 'Nouveau Centre de Charge'}
            </h3>
            <button 
              onClick={handleCancel}
              className="p-1.5 rounded-lg transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <X size={18} style={{ color: 'var(--text-muted)' }} />
            </button>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                  Code (ID) {!editingCentre && '*'}
                </label>
                <input
                  data-testid="centre-id-input"
                  type="text"
                  value={formData.id}
                  onChange={(e) => setFormData({ ...formData, id: e.target.value.toUpperCase() })}
                  disabled={!!editingCentre}
                  placeholder="Ex: PLI01, USI01"
                  className="w-full h-10 rounded-lg border px-3 text-sm transition-colors focus:outline-none focus:ring-2"
                  style={{ 
                    backgroundColor: editingCentre ? 'var(--bg-sunken)' : 'var(--bg-elevated)', 
                    borderColor: 'var(--border-default)',
                    color: 'var(--text-primary)',
                    opacity: editingCentre ? 0.7 : 1
                  }}
                  required={!editingCentre}
                />
                {!editingCentre && (
                  <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Code métier unique, utilisé pour les règles</p>
                )}
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                  Nom *
                </label>
                <input
                  data-testid="centre-nom-input"
                  type="text"
                  value={formData.nom}
                  onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                  placeholder="Ex: Centre de Pliage"
                  className="w-full h-10 rounded-lg border px-3 text-sm transition-colors focus:outline-none focus:ring-2"
                  style={{ 
                    backgroundColor: 'var(--bg-elevated)', 
                    borderColor: 'var(--border-default)',
                    color: 'var(--text-primary)'
                  }}
                  required
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                  Description
                </label>
                <input
                  data-testid="centre-description-input"
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Description optionnelle"
                  className="w-full h-10 rounded-lg border px-3 text-sm transition-colors focus:outline-none focus:ring-2"
                  style={{ 
                    backgroundColor: 'var(--bg-elevated)', 
                    borderColor: 'var(--border-default)',
                    color: 'var(--text-primary)'
                  }}
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                  <Calendar size={12} className="inline mr-1" />
                  Calendrier
                </label>
                <select
                  data-testid="centre-calendar-select"
                  value={formData.calendar_id}
                  onChange={(e) => setFormData({ ...formData, calendar_id: e.target.value })}
                  className="w-full h-10 rounded-lg border px-3 text-sm transition-colors focus:outline-none focus:ring-2"
                  style={{ 
                    backgroundColor: 'var(--bg-elevated)', 
                    borderColor: 'var(--border-default)',
                    color: 'var(--text-primary)'
                  }}
                >
                  <option value="">-- Aucun calendrier --</option>
                  {calendars.map(cal => (
                    <option key={cal.id} value={cal.id}>{cal.name}</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="flex gap-2 pt-2">
              <button
                type="submit"
                data-testid="centre-submit-btn"
                className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
              >
                {editingCentre ? 'Enregistrer' : 'Créer'}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-primary)', border: '1px solid var(--border-default)' }}
              >
                Annuler
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }} data-testid="centres-table">
        <table className="w-full">
          <thead style={{ backgroundColor: 'var(--bg-sunken)' }}>
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Code</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Description</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Calendrier</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {centres.map((centre) => (
              <tr key={centre.id} className="transition-colors hover:bg-opacity-50" style={{ borderBottom: '1px solid var(--border-default)' }} data-testid={`centre-row-${centre.id}`}>
                <td className="px-4 py-3">
                  <span className="px-2 py-1 rounded-lg text-sm font-mono font-semibold" style={{ backgroundColor: 'var(--status-info-bg)', color: 'var(--status-info)' }}>
                    {centre.id}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{centre.nom || centre.name}</span>
                </td>
                <td className="px-4 py-3">
                  <span style={{ color: 'var(--text-secondary)' }}>{centre.description || '-'}</span>
                </td>
                <td className="px-4 py-3">
                  <select
                    value={centre.calendar_id || ''}
                    onChange={(e) => handleCalendarChange(centre.id, e.target.value)}
                    className="h-8 rounded-lg border px-2 text-sm transition-colors focus:outline-none focus:ring-2"
                    style={{ 
                      backgroundColor: 'var(--bg-elevated)', 
                      borderColor: 'var(--border-default)',
                      color: 'var(--text-primary)'
                    }}
                    data-testid={`calendar-select-${centre.id}`}
                  >
                    <option value="">-- Aucun --</option>
                    {calendars.map(cal => (
                      <option key={cal.id} value={cal.id}>{cal.name}</option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    <button
                      data-testid={`edit-btn-${centre.id}`}
                      onClick={() => handleEdit(centre)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                      title="Modifier"
                    >
                      <Pencil size={16} style={{ color: 'var(--text-secondary)' }} />
                    </button>
                    <button
                      data-testid={`delete-btn-${centre.id}`}
                      onClick={() => handleDelete(centre.id)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-red-100 dark:hover:bg-red-900/30"
                      title="Supprimer"
                    >
                      <Trash2 size={16} className="text-red-600" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {centres.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                  Aucun centre de charge. Créez-en un avec un code métier lisible.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
