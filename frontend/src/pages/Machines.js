import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Machines() {
  const [machines, setMachines] = useState([]);
  const [workCenters, setWorkCenters] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', work_center_id: '', description: '' });

  useEffect(() => {
    fetchMachines();
    fetchWorkCenters();
  }, []);

  const fetchMachines = async () => {
    try {
      const response = await axios.get(`${API}/machines`);
      setMachines(response.data);
    } catch (error) {
      console.error('Error fetching machines:', error);
    }
  };

  const fetchWorkCenters = async () => {
    try {
      const response = await axios.get(`${API}/work-centers`);
      setWorkCenters(response.data);
    } catch (error) {
      console.error('Error fetching work centers:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/machines`, formData);
      toast.success('Machine créée');
      setFormData({ name: '', work_center_id: '', description: '' });
      setShowForm(false);
      fetchMachines();
    } catch (error) {
      toast.error('Erreur lors de la création');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Confirmer la suppression ?')) return;
    try {
      await axios.delete(`${API}/machines/${id}`);
      toast.success('Machine supprimée');
      fetchMachines();
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-semibold text-slate-800">Machines</h3>
        <button
          data-testid="create-machine-btn"
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
        >
          <Plus size={16} />
          Nouvelle Machine
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Nom de la machine
              </label>
              <input
                data-testid="machine-name-input"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Poste de travail
              </label>
              <select
                data-testid="machine-work-center-select"
                value={formData.work_center_id}
                onChange={(e) => setFormData({ ...formData, work_center_id: e.target.value })}
                className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                required
              >
                <option value="">Sélectionner un poste</option>
                {workCenters.map((wc) => (
                  <option key={wc.id} value={wc.id}>
                    {wc.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Description
              </label>
              <textarea
                data-testid="machine-description-input"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full rounded-sm border border-slate-300 bg-transparent px-3 py-2 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                rows={3}
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                data-testid="submit-machine-btn"
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
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Poste</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Description</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            {machines.map((machine) => {
              const workCenter = workCenters.find((wc) => wc.id === machine.work_center_id);
              return (
                <tr key={machine.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors" data-testid="machine-row">
                  <td className="px-4 py-2 text-sm text-slate-700 font-mono">{machine.id.substring(0, 8)}</td>
                  <td className="px-4 py-2 text-sm text-slate-700 font-mono">{machine.name}</td>
                  <td className="px-4 py-2 text-sm text-slate-700">{workCenter?.name || '-'}</td>
                  <td className="px-4 py-2 text-sm text-slate-700">{machine.description || '-'}</td>
                  <td className="px-4 py-2">
                    <button
                      data-testid="delete-machine-btn"
                      onClick={() => handleDelete(machine.id)}
                      className="text-red-600 hover:text-red-800 transition-colors"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              );
            })}
            {machines.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-500">
                  Aucune machine. Cliquez sur "Nouvelle Machine" pour en créer une.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}