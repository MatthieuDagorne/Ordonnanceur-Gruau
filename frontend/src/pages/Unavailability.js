import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2, Pencil, X, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Unavailability() {
  const [unavailabilities, setUnavailabilities] = useState([]);
  const [machines, setMachines] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingUnavailability, setEditingUnavailability] = useState(null);
  const [formData, setFormData] = useState({
    machine_id: '',
    start_date: '',
    end_date: '',
    reason: '',
  });

  useEffect(() => {
    fetchUnavailabilities();
    fetchMachines();
  }, []);

  const fetchUnavailabilities = async () => {
    try {
      const response = await axios.get(`${API}/unavailability`);
      setUnavailabilities(response.data);
    } catch (error) {
      console.error('Error fetching unavailabilities:', error);
    }
  };

  const fetchMachines = async () => {
    try {
      const response = await axios.get(`${API}/machines`);
      setMachines(response.data);
    } catch (error) {
      console.error('Error fetching machines:', error);
    }
  };

  const resetForm = () => {
    setFormData({ machine_id: '', start_date: '', end_date: '', reason: '' });
    setEditingUnavailability(null);
  };

  const handleEdit = (unavail) => {
    // Convertir les dates au format datetime-local si nécessaire
    let startDate = unavail.start_date || '';
    let endDate = unavail.end_date || '';
    
    // Si les dates sont au format ISO, les convertir
    if (startDate && startDate.includes('T')) {
      startDate = startDate.slice(0, 16); // Garder YYYY-MM-DDTHH:MM
    }
    if (endDate && endDate.includes('T')) {
      endDate = endDate.slice(0, 16);
    }
    
    setFormData({
      machine_id: unavail.machine_id || '',
      start_date: startDate,
      end_date: endDate,
      reason: unavail.reason || '',
    });
    setEditingUnavailability(unavail);
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.machine_id || !formData.start_date || !formData.end_date || !formData.reason.trim()) {
      toast.error('Tous les champs sont obligatoires');
      return;
    }
    
    if (formData.start_date >= formData.end_date) {
      toast.error('La date de début doit être avant la date de fin');
      return;
    }
    
    try {
      if (editingUnavailability) {
        // Mode édition
        await axios.put(`${API}/unavailability/${editingUnavailability.id}`, formData);
        toast.success('Indisponibilité modifiée');
      } else {
        // Mode création
        await axios.post(`${API}/unavailability`, formData);
        toast.success('Indisponibilité créée');
      }
      resetForm();
      setShowForm(false);
      fetchUnavailabilities();
    } catch (error) {
      toast.error(editingUnavailability ? 'Erreur lors de la modification' : 'Erreur lors de la création');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Confirmer la suppression ?')) return;
    try {
      await axios.delete(`${API}/unavailability/${id}`);
      toast.success('Indisponibilité supprimée');
      fetchUnavailabilities();
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const handleCancel = () => {
    resetForm();
    setShowForm(false);
  };

  const getMachineName = (machineId) => {
    const machine = machines.find(m => m.id === machineId);
    return machine ? (machine.nom || machine.name || machineId) : machineId;
  };

  // Formater la date pour l'affichage
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('fr-FR', { 
        day: '2-digit', 
        month: '2-digit', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6" data-testid="unavailability-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Indisponibilités Machines</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Planifiez les arrêts machines (maintenance, pannes prévues, etc.)
          </p>
        </div>
        <button
          data-testid="create-unavailability-btn"
          onClick={() => { resetForm(); setShowForm(true); }}
          className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
        >
          <Plus size={16} />
          Nouvelle Indisponibilité
        </button>
      </div>

      {showForm && (
        <div className="rounded-lg p-5" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              {editingUnavailability ? 'Modifier l\'indisponibilité' : 'Nouvelle Indisponibilité'}
            </h3>
            <button 
              onClick={handleCancel}
              className="p-1.5 rounded-lg transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <X size={18} style={{ color: 'var(--text-muted)' }} />
            </button>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                Machine *
              </label>
              <select
                data-testid="unavailability-machine-select"
                value={formData.machine_id}
                onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
                className="w-full h-10 rounded-lg border px-3 text-sm transition-colors focus:outline-none focus:ring-2"
                style={{ 
                  backgroundColor: 'var(--bg-elevated)', 
                  borderColor: 'var(--border-default)',
                  color: 'var(--text-primary)'
                }}
                required
              >
                <option value="">Sélectionner une machine</option>
                {machines.map((machine) => (
                  <option key={machine.id} value={machine.id}>
                    {machine.id} - {machine.nom || machine.name}
                  </option>
                ))}
              </select>
              {machines.length === 0 && (
                <p className="text-xs mt-1" style={{ color: 'var(--status-error)' }}>Créez d'abord une machine</p>
              )}
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                  Date/Heure début *
                </label>
                <input
                  data-testid="start-date-input"
                  type="datetime-local"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="w-full h-10 rounded-lg border px-3 text-sm font-mono transition-colors focus:outline-none focus:ring-2"
                  style={{ 
                    backgroundColor: 'var(--bg-elevated)', 
                    borderColor: 'var(--border-default)',
                    color: 'var(--text-primary)'
                  }}
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                  Date/Heure fin *
                </label>
                <input
                  data-testid="end-date-input"
                  type="datetime-local"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  className="w-full h-10 rounded-lg border px-3 text-sm font-mono transition-colors focus:outline-none focus:ring-2"
                  style={{ 
                    backgroundColor: 'var(--bg-elevated)', 
                    borderColor: 'var(--border-default)',
                    color: 'var(--text-primary)'
                  }}
                  required
                />
              </div>
            </div>
            
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                Raison *
              </label>
              <input
                data-testid="reason-input"
                type="text"
                value={formData.reason}
                onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                placeholder="Ex: Maintenance préventive, Panne électrique..."
                className="w-full h-10 rounded-lg border px-3 text-sm transition-colors focus:outline-none focus:ring-2"
                style={{ 
                  backgroundColor: 'var(--bg-elevated)', 
                  borderColor: 'var(--border-default)',
                  color: 'var(--text-primary)'
                }}
                required
              />
            </div>
            
            <div className="flex gap-2 pt-2">
              <button
                type="submit"
                data-testid="submit-unavailability-btn"
                className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
              >
                {editingUnavailability ? 'Enregistrer' : 'Créer'}
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

      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <table className="w-full">
          <thead style={{ backgroundColor: 'var(--bg-sunken)' }}>
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Machine</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Début</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Fin</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Raison</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {unavailabilities.map((unavail) => (
              <tr key={unavail.id} className="transition-colors hover:bg-opacity-50" style={{ borderBottom: '1px solid var(--border-default)' }} data-testid="unavailability-row">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={14} style={{ color: 'var(--status-warning)' }} />
                    <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                      {getMachineName(unavail.machine_id)}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>
                    {formatDate(unavail.start_date)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>
                    {formatDate(unavail.end_date)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 rounded-lg text-xs font-medium" style={{ backgroundColor: 'var(--status-warning-bg)', color: 'var(--status-warning)' }}>
                    {unavail.reason}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    <button
                      data-testid={`edit-unavailability-${unavail.id}`}
                      onClick={() => handleEdit(unavail)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                      title="Modifier"
                    >
                      <Pencil size={16} style={{ color: 'var(--text-secondary)' }} />
                    </button>
                    <button
                      data-testid={`delete-unavailability-${unavail.id}`}
                      onClick={() => handleDelete(unavail.id)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-red-100 dark:hover:bg-red-900/30"
                      title="Supprimer"
                    >
                      <Trash2 size={16} className="text-red-600" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {unavailabilities.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                  Aucune indisponibilité. Cliquez sur "Nouvelle Indisponibilité" pour en créer une.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
