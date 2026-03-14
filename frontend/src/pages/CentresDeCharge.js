import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function CentresDeCharge() {
  const [centres, setCentres] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ id: '', nom: '', description: '' });

  useEffect(() => {
    fetchCentres();
  }, []);

  const fetchCentres = async () => {
    try {
      const response = await axios.get(`${API}/centres-de-charge`);
      setCentres(response.data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.id.trim() || !formData.nom.trim()) {
      toast.error('Le code et le nom sont obligatoires');
      return;
    }
    try {
      const response = await axios.post(`${API}/centres-de-charge`, formData);
      setCentres([...centres, response.data]);
      setFormData({ id: '', nom: '', description: '' });
      setShowForm(false);
      toast.success(`Centre de charge "${formData.id}" créé`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erreur lors de la création');
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold text-slate-800">Centres de Charge</h3>
          <p className="text-sm text-slate-500 mt-1">
            Définissez les centres de charge avec des codes métier lisibles (ex: PLI01, USI01)
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium"
        >
          <Plus size={16} />
          Nouveau Centre
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
          <h4 className="text-lg font-semibold text-slate-800 mb-4">Nouveau Centre de Charge</h4>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Code (ID) *
                </label>
                <input
                  type="text"
                  value={formData.id}
                  onChange={(e) => setFormData({ ...formData, id: e.target.value.toUpperCase() })}
                  placeholder="Ex: PLI01, USI01"
                  className="w-full h-9 rounded-sm border border-slate-300 px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-slate-900"
                  required
                />
                <p className="text-xs text-slate-500 mt-1">Code métier unique, utilisé pour les règles</p>
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Nom *
                </label>
                <input
                  type="text"
                  value={formData.nom}
                  onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                  placeholder="Ex: Centre de Pliage"
                  className="w-full h-9 rounded-sm border border-slate-300 px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-slate-900"
                  required
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Description
              </label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Description optionnelle"
                className="w-full h-9 rounded-sm border border-slate-300 px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-slate-900"
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium">
                Créer
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-sm px-4 py-2 text-sm font-medium">
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
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Code</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Description</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {centres.map((centre) => (
              <tr key={centre.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-3">
                  <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-sm font-mono font-semibold">
                    {centre.id}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-slate-900">{centre.nom || centre.name}</td>
                <td className="px-4 py-3 text-sm text-slate-500">{centre.description || '-'}</td>
                <td className="px-4 py-3">
                  <button onClick={() => handleDelete(centre.id)} className="text-red-600 hover:text-red-800 p-1" title="Supprimer">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {centres.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm text-slate-500">
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
