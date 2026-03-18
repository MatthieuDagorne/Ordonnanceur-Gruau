import { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import { Plus, Trash2, Pencil, X, Search, Filter } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Machines() {
  const [machines, setMachines] = useState([]);
  const [centres, setCentres] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingMachine, setEditingMachine] = useState(null);
  const [formData, setFormData] = useState({ id: '', nom: '', centre_de_charge_id: '', description: '' });
  
  // Filtres
  const [filterCentre, setFilterCentre] = useState('');
  const [filterMachine, setFilterMachine] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [machinesRes, centresRes] = await Promise.all([
        axios.get(`${API}/machines`),
        axios.get(`${API}/centres-de-charge`)
      ]);
      setMachines(machinesRes.data);
      // Trier les centres par ID croissant
      const sortedCentres = centresRes.data.sort((a, b) => {
        const idA = (a.id || '').toString().toLowerCase();
        const idB = (b.id || '').toString().toLowerCase();
        return idA.localeCompare(idB, 'fr', { numeric: true });
      });
      setCentres(sortedCentres);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  // Machines triées par centre de charge puis par ID machine
  const sortedAndFilteredMachines = useMemo(() => {
    let filtered = [...machines];
    
    // Appliquer les filtres
    if (filterCentre) {
      filtered = filtered.filter(m => 
        (m.centre_de_charge_id || m.work_center_id || '').toLowerCase().includes(filterCentre.toLowerCase())
      );
    }
    if (filterMachine) {
      filtered = filtered.filter(m => 
        (m.id || '').toLowerCase().includes(filterMachine.toLowerCase()) ||
        (m.nom || m.name || '').toLowerCase().includes(filterMachine.toLowerCase())
      );
    }
    
    // Trier par centre de charge puis par ID machine
    return filtered.sort((a, b) => {
      const centreA = (a.centre_de_charge_id || a.work_center_id || '').toString().toLowerCase();
      const centreB = (b.centre_de_charge_id || b.work_center_id || '').toString().toLowerCase();
      const centreCompare = centreA.localeCompare(centreB, 'fr', { numeric: true });
      
      if (centreCompare !== 0) return centreCompare;
      
      const idA = (a.id || '').toString().toLowerCase();
      const idB = (b.id || '').toString().toLowerCase();
      return idA.localeCompare(idB, 'fr', { numeric: true });
    });
  }, [machines, filterCentre, filterMachine]);

  const resetForm = () => {
    setFormData({ id: '', nom: '', centre_de_charge_id: '', description: '' });
    setEditingMachine(null);
  };

  const handleEdit = (machine) => {
    setFormData({
      id: machine.id,
      nom: machine.nom || machine.name || '',
      centre_de_charge_id: machine.centre_de_charge_id || machine.work_center_id || '',
      description: machine.description || '',
    });
    setEditingMachine(machine);
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.nom.trim() || !formData.centre_de_charge_id) {
      toast.error('Le nom et le centre de charge sont obligatoires');
      return;
    }
    
    try {
      if (editingMachine) {
        // Mode édition
        await axios.put(`${API}/machines/${editingMachine.id}`, {
          nom: formData.nom,
          centre_de_charge_id: formData.centre_de_charge_id,
          description: formData.description,
        });
        toast.success(`Machine "${editingMachine.id}" modifiée`);
      } else {
        // Mode création
        if (!formData.id.trim()) {
          toast.error('Le code (ID) est obligatoire pour une nouvelle machine');
          return;
        }
        await axios.post(`${API}/machines`, formData);
        toast.success(`Machine "${formData.id}" créée`);
      }
      resetForm();
      setShowForm(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || (editingMachine ? 'Erreur lors de la modification' : 'Erreur lors de la création'));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(`Supprimer la machine "${id}" ?`)) return;
    try {
      await axios.delete(`${API}/machines/${id}`);
      setMachines(machines.filter(m => m.id !== id));
      toast.success('Machine supprimée');
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const handleCancel = () => {
    resetForm();
    setShowForm(false);
  };

  const getCentreName = (centreId) => {
    const centre = centres.find(c => c.id === centreId);
    return centre ? `${centre.id} - ${centre.nom || centre.name}` : centreId;
  };

  return (
    <div className="space-y-6" data-testid="machines-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Machines</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Définissez les machines avec des codes métier lisibles (ex: PLIEUSE_01)
          </p>
        </div>
        <button
          data-testid="create-machine-btn"
          onClick={() => { resetForm(); setShowForm(true); }}
          className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
        >
          <Plus size={16} />
          Nouvelle Machine
        </button>
      </div>

      {/* Filtres */}
      <div className="flex gap-4 items-center p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <Filter size={16} style={{ color: 'var(--text-muted)' }} />
        <div className="flex-1 flex gap-4">
          <div className="flex-1 max-w-xs">
            <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>
              Centre de Charge
            </label>
            <select
              value={filterCentre}
              onChange={(e) => setFilterCentre(e.target.value)}
              className="w-full h-9 rounded-lg border px-3 text-sm"
              style={{ 
                backgroundColor: 'var(--bg-elevated)', 
                borderColor: 'var(--border-default)',
                color: 'var(--text-primary)'
              }}
              data-testid="filter-centre"
            >
              <option value="">Tous les centres</option>
              {centres.map((centre) => (
                <option key={centre.id} value={centre.id}>
                  {centre.id}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1 max-w-xs">
            <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>
              Machine
            </label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                value={filterMachine}
                onChange={(e) => setFilterMachine(e.target.value)}
                placeholder="Rechercher..."
                className="w-full h-9 rounded-lg border pl-9 pr-3 text-sm"
                style={{ 
                  backgroundColor: 'var(--bg-elevated)', 
                  borderColor: 'var(--border-default)',
                  color: 'var(--text-primary)'
                }}
                data-testid="filter-machine"
              />
            </div>
          </div>
        </div>
        {(filterCentre || filterMachine) && (
          <button
            onClick={() => { setFilterCentre(''); setFilterMachine(''); }}
            className="text-xs px-2 py-1 rounded transition-colors"
            style={{ color: 'var(--status-error)' }}
          >
            Effacer
          </button>
        )}
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          {sortedAndFilteredMachines.length} machine{sortedAndFilteredMachines.length > 1 ? 's' : ''}
        </span>
      </div>

      {showForm && (
        <div className="rounded-lg p-5" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              {editingMachine ? `Modifier: ${editingMachine.id}` : 'Nouvelle Machine'}
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
                  Code (ID) {!editingMachine && '*'}
                </label>
                <input
                  data-testid="machine-id-input"
                  type="text"
                  value={formData.id}
                  onChange={(e) => setFormData({ ...formData, id: e.target.value.toUpperCase() })}
                  disabled={!!editingMachine}
                  placeholder="Ex: PLIEUSE_01"
                  className="w-full h-10 rounded-lg border px-3 text-sm transition-colors focus:outline-none focus:ring-2"
                  style={{ 
                    backgroundColor: editingMachine ? 'var(--bg-sunken)' : 'var(--bg-elevated)', 
                    borderColor: 'var(--border-default)',
                    color: 'var(--text-primary)',
                    opacity: editingMachine ? 0.7 : 1
                  }}
                  required={!editingMachine}
                />
                {!editingMachine && (
                  <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Code métier unique, utilisé pour les règles</p>
                )}
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                  Nom *
                </label>
                <input
                  data-testid="machine-name-input"
                  type="text"
                  value={formData.nom}
                  onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                  placeholder="Ex: Plieuse hydraulique 01"
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
            
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                Centre de Charge *
              </label>
              <select
                data-testid="machine-centre-select"
                value={formData.centre_de_charge_id}
                onChange={(e) => setFormData({ ...formData, centre_de_charge_id: e.target.value })}
                className="w-full h-10 rounded-lg border px-3 text-sm transition-colors focus:outline-none focus:ring-2"
                style={{ 
                  backgroundColor: 'var(--bg-elevated)', 
                  borderColor: 'var(--border-default)',
                  color: 'var(--text-primary)'
                }}
                required
              >
                <option value="">-- Sélectionner un centre --</option>
                {centres.map((centre) => (
                  <option key={centre.id} value={centre.id}>
                    {centre.id} - {centre.nom || centre.name}
                  </option>
                ))}
              </select>
              {centres.length === 0 && (
                <p className="text-xs mt-1" style={{ color: 'var(--status-error)' }}>Créez d'abord un centre de charge</p>
              )}
            </div>
            
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: 'var(--text-muted)' }}>
                Description
              </label>
              <input
                data-testid="machine-description-input"
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
            
            <div className="flex gap-2 pt-2">
              <button
                type="submit"
                data-testid="submit-machine-btn"
                className="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
              >
                {editingMachine ? 'Enregistrer' : 'Créer'}
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
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Code</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Centre de Charge</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sortedAndFilteredMachines.map((machine) => (
              <tr key={machine.id} className="transition-colors hover:bg-opacity-50" style={{ borderBottom: '1px solid var(--border-default)' }} data-testid="machine-row">
                <td className="px-4 py-3">
                  <span className="px-2 py-1 rounded-lg text-sm font-mono font-semibold" style={{ backgroundColor: 'var(--status-info-bg)', color: 'var(--status-info)' }}>
                    {machine.id}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{machine.nom || machine.name}</span>
                </td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 rounded-lg text-xs font-mono" style={{ backgroundColor: 'var(--status-success-bg)', color: 'var(--status-success)' }}>
                    {machine.centre_de_charge_id || machine.work_center_id}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    <button
                      data-testid={`edit-machine-${machine.id}`}
                      onClick={() => handleEdit(machine)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                      title="Modifier"
                    >
                      <Pencil size={16} style={{ color: 'var(--text-secondary)' }} />
                    </button>
                    <button
                      data-testid={`delete-machine-${machine.id}`}
                      onClick={() => handleDelete(machine.id)}
                      className="p-1.5 rounded-lg transition-colors hover:bg-red-100 dark:hover:bg-red-900/30"
                      title="Supprimer"
                    >
                      <Trash2 size={16} className="text-red-600" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {sortedAndFilteredMachines.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                  {machines.length === 0 
                    ? "Aucune machine. Créez d'abord un centre de charge, puis une machine."
                    : "Aucune machine ne correspond aux filtres."
                  }
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
